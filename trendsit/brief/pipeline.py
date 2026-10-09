"""weekly 명령(S5_TASK 5.10): cluster → select → write(+review) → 저장 → 실행 요약 → 브리핑 읽기본.

- 모든 행에 이번 run_id. 그 주 현재판은 weeks.current_run_id 하나로 가리키고 지우는 행은 없다
- --from-step select|write|review: 앞 단계 결과는 weeks.current_run_id(원본 run)에서 읽고, 새 run_id로 이어서 쓴다
- 실행 요약은 끝에 표들에서 계산해 runs.summary_json에 한 번 저장(compute_summary로 다시 계산 가능, 관문 A12)
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from ..core import config
from ..core.artifacts_brief import BriefingPlan, TopicPage
from ..core.config_brief import BriefConfig
from ..core.context import Ctx
from ..core.db import DB, now_kst
from ..filter.embed import to_blob
from . import aliases as al
from . import cluster as cl
from . import select as sel
from . import write as wr
from .evidence import week_evidence
from .weekly import stage_cluster

STEPS = ("cluster", "select", "write", "review")
ROLES = ("decide", "editor_select", "writer", "writer_revise", "critic")


def _summary_src(db: DB, run_id: str) -> dict[str, Any]:
    r = db.conn.execute("SELECT summary_json FROM runs WHERE id=?", (run_id,)).fetchone()
    return json.loads(r["summary_json"]) if r and r["summary_json"] else {}


def run_weekly(week: str, ctx: Ctx, from_step: str = "cluster", only_topic: str | None = None,
               embedder: Any = None, cfg: BriefConfig | None = None, until: str | None = None) -> dict[str, Any]:
    """from_step부터 until까지(없으면 끝까지). until=select면 선별까지, write면 초안 + 코드 검사까지(검수자 없음)."""
    from ..filter.embed import make_embedder

    cfg = cfg or config.load("brief.yaml")
    db, tr = ctx.db, ctx.tracer
    assert tr is not None
    run_id = tr.run_id
    with db.conn:  # 바로 커밋(열린 쓰기 트랜잭션이 LLM 호출 내내 DB를 잠그지 않게)
        db.conn.execute("UPDATE runs SET week=? WHERE id=?", (week, run_id))
    flt = config.load("filter.yaml")
    embedder = embedder or make_embedder("real", flt)
    dur: dict[str, float] = {}
    t0 = time.monotonic()
    src = (db.conn.execute("SELECT current_run_id FROM weeks WHERE week=?", (week,)).fetchone() or [None])[0]
    if from_step != "cluster" and not src:
        raise ValueError(f"{week}: 이어 갈 현재판 run이 없음(--from-step cluster부터)")
    if from_step == "cluster":
        stage = stage_cluster(week, ctx, cfg, embedder)
        ev, table, cluster_run = stage.evidence, stage.aliases, run_id
        from .report import write_cluster_report, write_label_sheets

        write_cluster_report(stage, cfg, note="weekly 실행의 묶기 단계")
        write_label_sheets(stage)
        dur |= {"evidence": stage.seconds["evidence"] + stage.seconds["normalize"], "cluster": stage.seconds["cluster"]}
    else:
        ev = week_evidence(db, week)
        table = al.load_decided(db, al.build(list(ev.members.values()), config.load("keywords.yaml"),
                                             cfg.aliases.fuzz_min_score))
        cl.score_video_relevance(list(ev.members.values()), embedder, [(x.keyword_id, x.text) for x in flt.interests],
                                 cfg.evidence.video_relevance_high)
        cluster_run = _summary_src(db, src).get("cluster_run") or src
    tr.step(kind="code", role="weekly", text=f"{week} weekly 시작: {from_step}부터", detail={
        "from_step": from_step, "source_run": src, "cluster_run": cluster_run})
    # ---------- select ----------
    t1 = time.monotonic()
    cands = sel.load_candidates(db, cluster_run, ev, cfg.select.max_candidates)
    sites = [r["name"] for r in db.conn.execute("SELECT name FROM sources") if r["name"]]
    if from_step in ("cluster", "select"):
        sres = sel.select(ctx, cands, ev, cfg, sites)
        sel.save(db, sres, run_id, week)
        plan = sres.plan
        topics = sres.topics
        tr.step(kind="code", role="editor_select",
                text=f"후보 {len(cands)}개 중 {len(topics)}개 선정, 후속 {sum(t.relation_type == 'follow_up' for t in topics)}"
                     + (" (대체 계획)" if sres.source == "fallback" else ""),
                attention=sres.source == "fallback" or bool(sres.reason_mismatch),
                detail={"errors_by_try": sres.errors_by_try, "reason_mismatch": sres.reason_mismatch,
                        "source": sres.source, "reconciled": sres.reconciled})
    else:
        row = db.conn.execute("SELECT plan_json, source FROM briefing_plans WHERE run_id=? ORDER BY id DESC LIMIT 1",
                              (src,)).fetchone()
        plan = BriefingPlan.model_validate_json(row["plan_json"])
        topics = sel.apply(plan, cands, week, db)
        with db.conn:
            db.conn.execute("INSERT INTO briefing_plans(run_id, week, source, plan_json, created_at) VALUES (?,?,?,?,?)",
                            (run_id, week, row["source"], row["plan_json"], now_kst()))
            for t in topics:
                db.conn.execute(
                    "INSERT INTO topics(run_id, topic_id, week, cluster_ids_json, rank, lead, relation_type, "
                    "relation_topic_id, status, angle) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (run_id, t.topic_id, week, json.dumps(t.cluster_ids), t.rank, int(t.lead), t.relation_type,
                     t.relation_topic_id, "selected", t.angle))
    dur["select"] = round(time.monotonic() - t1, 1)
    if until == "select":
        topics = []
    # ---------- write + review ----------
    t2 = time.monotonic()
    results = []
    for t in topics:
        if only_topic and t.topic_id != only_topic:
            continue
        draft = None
        if from_step == "review":
            r = db.conn.execute("SELECT page_json FROM topic_pages WHERE run_id=? AND topic_id=? AND round=1", (src, t.topic_id)
                                ).fetchone()
            draft = TopicPage.model_validate_json(r["page_json"]) if r else None
        res = wr.write_topic(ctx, t, ev.members, table, cfg, review=until != "write", draft=draft)
        wr.save(db, res, run_id)
        results.append(res)
        tr.step(kind="code", role="writer",
                text=f"{t.topic_id}: {res.status}, {res.final_round}라운드" + (f", 확인 필요 {res.attention[0]}" if res.attention else ""),
                attention=res.status != "passed" or bool(res.attention),
                detail={"topic_id": t.topic_id, "evidence": res.evidence_ids, "truncated": res.dropped_ids,
                        "n_sources": res.n_sources, "costs": res.costs, "rounds": [
                            {"round": lg.round, "checker": lg.checker, "status": lg.status, "issues": lg.issues,
                             "reverts": lg.reverts, "autofix": len(lg.autofix)} for lg in res.rounds]})
    dur["write_review"] = round(time.monotonic() - t2, 1)
    if only_topic and src:
        carry_over(db, src, run_id, keep={only_topic})
    save_topic_embeddings(db, run_id, embedder, results)
    if until == "select":
        status = "selected"
    elif until == "write":
        status = "written"
    else:
        status = "done" if results and all(r.status != "failed" for r in results) else ("failed" if not results else "written")
    with db.conn:
        db.conn.execute("UPDATE weeks SET status=?, current_run_id=? WHERE week=?", (status, run_id, week))
    dur["total"] = round(time.monotonic() - t0, 1)
    tr.step(kind="code", role="weekly", text=f"{week} weekly 끝: 토픽 {len(results)}개", detail={"duration_sec": dur})
    summary = compute_summary(db, run_id)
    with db.conn:
        db.conn.execute("UPDATE runs SET summary_json=? WHERE id=?", (json.dumps(summary, ensure_ascii=False), run_id))
    return summary


def carry_over(db: DB, src: str, run_id: str, keep: set[str]) -> None:
    """토픽 하나만 다시 돌린 run에 나머지 토픽의 결과(상태, 최종판, 판정, 근거 연결, 임베딩)를 원본 run에서 복사한다.
    그래야 그 run이 그 주 현재판이 되어도 토픽이 빠지지 않는다. 복사한 행도 이 run_id로 쌓인다(원본은 그대로)."""
    rows = db.conn.execute("SELECT topic_id, status, final_round, title, summary FROM topics WHERE run_id=?", (src,)).fetchall()
    with db.conn:
        for r in rows:
            if r["topic_id"] in keep:
                continue
            db.conn.execute("UPDATE topics SET status=?, final_round=?, title=?, summary=? WHERE run_id=? AND topic_id=?",
                            (r["status"], r["final_round"], r["title"], r["summary"], run_id, r["topic_id"]))
            for tbl, cols in (("topic_pages", "topic_id, round, page_json, raw_json, step_id"),
                              ("verdicts", "topic_id, round, checker, status, issues_json, autofix_json, step_id"),
                              ("topic_evidence", "topic_id, evidence_id, member, field, idx"),
                              ("topic_embeddings", "topic_id, model, dim, vec, text_hash")):
                db.conn.execute(f"INSERT INTO {tbl}(run_id, {cols}) SELECT ?, {cols} FROM {tbl} WHERE run_id=? AND topic_id=?",
                                (run_id, src, r["topic_id"]))


def save_topic_embeddings(db: DB, run_id: str, embedder: Any, results: list[wr.TopicResult]) -> None:
    """과거 대조용: 제목 + 요약 임베딩(passed·checked 토픽)."""
    done = [r for r in results if r.status in ("passed", "checked") and r.page]
    if not done:
        return
    texts = [f"{r.page.title}\n{r.page.summary}" for r in done]  # type: ignore[union-attr]
    vecs = embedder.embed_docs(texts)
    with db.conn:
        db.conn.executemany(
            "INSERT OR REPLACE INTO topic_embeddings(topic_id, run_id, model, dim, vec, text_hash) VALUES (?,?,?,?,?,?)",
            [(r.topic.topic_id, run_id, embedder.model_id, len(v), to_blob(v), hashlib.sha256(t.encode()).hexdigest()[:16])
             for r, v, t in zip(done, vecs, texts, strict=True)])


# ---------- 실행 요약 ----------
def _detail(db: DB, run_id: str, role: str, prefix: str = "") -> list[dict[str, Any]]:
    return [json.loads(r["detail"]) for r in db.conn.execute(
        "SELECT detail FROM steps WHERE run_id=? AND role=? AND kind='code' AND detail IS NOT NULL AND text LIKE ? ORDER BY id",
        (run_id, role, prefix + "%"))]


def compute_summary(db: DB, run_id: str) -> dict[str, Any]:
    """표(clusters, cluster_pairs, briefing_plans, topics, topic_pages, verdicts, steps)에서 실행 요약을 다시 계산한다."""
    run = db.conn.execute("SELECT week, started_at FROM runs WHERE id=?", (run_id,)).fetchone()
    week = run["week"]
    start = next(iter(_detail(db, run_id, "weekly", f"{week} weekly 시작")), {})
    cluster_run = start.get("cluster_run") or run_id
    ev = next(iter(_detail(db, cluster_run, "evidence", "근거 자격")), {})
    norm = next(iter(_detail(db, cluster_run, "normalize")), {})
    clusters = db.conn.execute("SELECT channels_json, n_items, body_json FROM clusters WHERE run_id=?", (cluster_run,)).fetchall()
    cands = [c for c in clusters if not json.loads(c["body_json"] or "{}").get("repo_only")]
    chans = [json.loads(c["channels_json"]) for c in cands]
    pairs = db.conn.execute("SELECT decided, answer, confidence FROM cluster_pairs WHERE run_id=?", (cluster_run,)).fetchall()
    plan_row = db.conn.execute("SELECT plan_json FROM briefing_plans WHERE run_id=? ORDER BY id DESC LIMIT 1",
                               (run_id,)).fetchone()
    plan = json.loads(plan_row["plan_json"]) if plan_row else {"decisions": [], "topics": [], "splits": []}
    topics = db.conn.execute("SELECT topic_id, status, final_round FROM topics WHERE run_id=?", (run_id,)).fetchall()
    verdicts = db.conn.execute("SELECT checker, status, issues_json, autofix_json FROM verdicts WHERE run_id=?",
                               (run_id,)).fetchall()
    drops = {k: 0 for k in ("duplicate", "low_relevance", "thin", "other")}
    for d in plan.get("decisions", []):
        if d.get("action") == "drop":
            drops[d.get("drop_reason") or "other"] = drops.get(d.get("drop_reason") or "other", 0) + 1
    issue_types = {k: 0 for k in ("unsupported", "number_mismatch", "overclaim", "missing_key", "wrong_ref", "overuse",
                                  "missing_diagram")}
    autofixes = reverts = 0
    for v in verdicts:
        for it in json.loads(v["issues_json"] or "[]"):
            if v["checker"] == "critic" and it["type"] in issue_types:
                issue_types[it["type"]] += 1
        a = json.loads(v["autofix_json"] or "{}")
        autofixes += len(a.get("autofix") or [])
        reverts += a.get("reverts") or 0
    check_points = 0
    for t in topics:
        r = db.conn.execute("SELECT page_json FROM topic_pages WHERE run_id=? AND topic_id=? ORDER BY round DESC LIMIT 1",
                            (run_id, t["topic_id"])).fetchone()
        if r:
            check_points += sum(1 for p in json.loads(r["page_json"]).get("points", []) if p.get("check"))
    writers = _detail(db, run_id, "writer")
    cost = {k: round(float(db.conn.execute("SELECT COALESCE(SUM(cost_usd),0) FROM steps WHERE run_id=? AND role=?",
                                           (run_id, k)).fetchone()[0] or 0), 6) for k in ROLES}
    cost["total"] = round(sum(cost.values()), 6)
    end = next(iter(_detail(db, run_id, "weekly", f"{week} weekly 끝")), {})
    rel_types = [t.get("relation", {}).get("type") for t in plan.get("topics", [])]
    status = "ok"
    if any(t["status"] == "failed" for t in topics) or not topics:
        status = "partial" if topics else "failed"
    return {
        "week": week, "model": _model(db, run_id), "status": status,
        "cluster_run": cluster_run,
        "evidence": {"items": ev.get("counts", {"text": 0, "video": 0, "github": 0}),
                     "excluded": ev.get("excluded", {"no_card": 0, "no_digest": 0, "irrelevant_repo": 0}),
                     "truncated_topics": sum(1 for w in writers if w.get("truncated"))},
        "aliases": {"candidates": norm.get("counts", {}).get("candidates", 0),
                    "auto_approved": norm.get("counts", {}).get("auto_approved", 0),
                    "decide_calls": len(norm.get("decide", []))},
        "cluster": {"clusters": len(clusters), "single_item": sum(c["n_items"] == 1 for c in cands),
                    "multi_channel": sum(len(c) >= 2 for c in chans), "three_channel": sum(len(c) >= 3 for c in chans),
                    "decide_calls": sum(p["decided"] for p in pairs),
                    "decide_merged": sum(1 for p in pairs if p["decided"] and p["answer"] and (p["confidence"] or 0) >= 0.6),
                    "past": {"new": rel_types.count("new"), "follow_up": rel_types.count("follow_up"),
                             "duplicate": drops["duplicate"]}},
        "select": {"candidates": len(plan.get("decisions", [])), "selected": len(plan.get("topics", [])),
                   "merges": sum(1 for t in plan.get("topics", []) if len(t.get("cluster_ids", [])) > 1),
                   "splits": len(plan.get("splits", [])), "drops": drops},
        "write": {"topics": len(topics), "failed": sum(t["status"] == "failed" for t in topics)},
        "review": {"rounds": {str(k): sum(1 for t in topics if t["final_round"] == k) for k in (1, 2, 3)},
                   "code_rejects": sum(1 for v in verdicts if v["checker"] == "code" and v["status"] == "reject"),
                   "critic_rejects": sum(1 for v in verdicts if v["checker"] == "critic" and v["status"] == "reject"),
                   "autofixes": autofixes, "reverts": reverts, "issues": issue_types, "check_points": check_points},
        "cost_usd": cost,
        "duration_sec": {k: end.get("duration_sec", {}).get(k, 0) for k in ("evidence", "cluster", "select", "write_review",
                                                                            "total")},
    }


def _model(db: DB, run_id: str) -> str:
    r = db.conn.execute("SELECT model FROM steps WHERE run_id=? AND kind='llm' AND role IN ('writer','editor_select') "
                        "AND model IS NOT NULL LIMIT 1", (run_id,)).fetchone()
    return r["model"] if r else ""
