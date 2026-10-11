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
from ..core.budget import BudgetExceeded, PriceUnknown
from ..core.config_brief import BriefConfig
from ..core.context import Ctx
from ..core.db import DB
from ..filter.embed import embed_interests, to_blob
from . import aliases as al
from . import cluster as cl
from . import select as sel
from . import write as wr
from .evidence import WeekEvidence, week_evidence
from .weekly import set_run_week, stage_cluster

STEPS = ("cluster", "select", "write", "review")
ROLES = ("decide", "editor_select", "writer", "writer_revise", "critic")


def _cluster_phase(week: str, ctx: Ctx, cfg: BriefConfig, embedder: Any, interests: list[tuple[str, list[float]]],
                   from_step: str, src: str | None, dur: dict[str, float]) -> tuple[WeekEvidence, al.AliasTable, str]:
    """묶기 단계. cluster부터면 새로 묶고, 아니면 src run의 근거·묶음을 이어 받는다. 반환: (근거, 별칭 표, 묶음이 든 run)."""
    db = ctx.db
    if from_step == "cluster":
        from .report import write_cluster_report, write_label_sheets

        stage = stage_cluster(week, ctx, cfg, embedder, set_current=False, interests=interests)
        write_cluster_report(stage, cfg, note="weekly 실행의 묶기 단계")
        if not ctx.stopped:  # 멈춘 run은 그 주 라벨 시트 행을 덮지 않음(판정 못 한 쌍의 줄이 빠지지 않게)
            write_label_sheets(stage)
        dur |= {"evidence": stage.seconds["evidence"] + stage.seconds["normalize"], "cluster": stage.seconds["cluster"]}
        return stage.evidence, stage.aliases, stage.run_id
    ev = week_evidence(db, week)
    table = al.decided_table(db, list(ev.members.values()), cfg)
    cl.score_video_relevance(ev, embedder, interests, cfg)
    r = db.conn.execute("SELECT summary_json FROM runs WHERE id=?", (src,)).fetchone()
    return ev, table, (json.loads(r["summary_json"]) if r and r["summary_json"] else {}).get("cluster_run") or src


def _select_phase(ctx: Ctx, week: str, ev: WeekEvidence, cfg: BriefConfig, embedder: Any,
                  interests: list[tuple[str, list[float]]], cluster_run: str, from_step: str,
                  src: str | None) -> list[sel.Applied] | None:
    """선별 단계. write·review부터면 src run의 계획을 이어 받는다. 선별 중 예산 초과면 None(대체 계획을 저장하지 않고 멈춤)."""
    db, tr = ctx.db, ctx.tracer
    assert tr is not None
    sims = cl.interest_similarity(db, list(ev.members.values()), embedder, interests)
    cands = sel.load_candidates(db, cluster_run, ev, cfg.select.max_candidates, sims)
    if from_step not in ("cluster", "select"):
        row = db.conn.execute("SELECT plan_json, source FROM briefing_plans WHERE run_id=? ORDER BY id DESC LIMIT 1",
                              (src,)).fetchone()
        topics = sel.apply(BriefingPlan.model_validate_json(row["plan_json"]), cands, week, db)
        sel.save_plan(db, tr.run_id, week, row["source"], row["plan_json"], topics)
        return topics
    sres = sel.select(ctx, cands, ev, cfg, [r["name"] for r in db.conn.execute("SELECT name FROM sources") if r["name"]])
    if ctx.stopped:
        return None
    sel.save(db, sres, tr.run_id, week)
    tr.step(kind="code", role="editor_select",
            text=f"후보 {len(cands)}개 중 {len(sres.topics)}개 선정, 후속 {sum(t.relation_type == 'follow_up' for t in sres.topics)}"
                 + (" (대체 계획)" if sres.source == "fallback" else ""),
            attention=sres.source == "fallback" or bool(sres.reason_mismatch),
            detail={"errors_by_try": sres.errors_by_try, "reason_mismatch": sres.reason_mismatch,
                    "source": sres.source, "reconciled": sres.reconciled})
    return sres.topics


def _log_topic(tr: Any, t: sel.Applied, res: wr.TopicResult) -> None:
    tr.step(kind="code", role="writer",
            text=f"{t.topic_id}: {res.status}, {res.final_round}라운드" + (f", 확인 필요 {res.attention[0]}" if res.attention else ""),
            attention=res.status != "passed" or bool(res.attention),
            detail={"topic_id": t.topic_id, "evidence": res.evidence_ids, "dropped_evidence": res.dropped_ids,
                    "no_visuals": res.no_visuals, "dropped_diagrams": res.dropped_diagrams, "checks": res.checks,
                    "n_sources": res.n_sources, "costs": res.costs, "rounds": [
                        {"round": lg.round, "checker": lg.checker, "status": lg.status, "issues": lg.issues,
                         "reverts": lg.reverts, "autofix": len(lg.autofix)} for lg in res.rounds]})


def _write_phase(ctx: Ctx, topics: list[sel.Applied], ev: WeekEvidence, table: al.AliasTable, cfg: BriefConfig,
                 from_step: str, src: str | None, only_topic: str | None, until: str | None) -> list[wr.TopicResult]:
    """토픽마다 작성 + 검수 + 저장. 예산 초과로 멈추면 거기서 끝낸다."""
    db = ctx.db
    results = []
    for t in topics:
        if only_topic and t.topic_id != only_topic:
            continue
        draft = None
        if from_step == "review":
            r = db.conn.execute("SELECT page_json FROM topic_pages WHERE run_id=? AND topic_id=? AND round=1", (src, t.topic_id)
                                ).fetchone()
            draft = TopicPage.model_validate_json(r["page_json"]) if r else None
        try:
            res = wr.write_topic(ctx, t, ev.members, table, cfg, review=until != "write", draft=draft)
        except Exception as e:  # noqa: BLE001 - 한 토픽의 예상 밖 오류가 주 전체를 멈추지 않게(기록 후 failed). 예산 초과만 전체 중단
            if isinstance(e, (BudgetExceeded, PriceUnknown)):
                ctx.stopped = f"{type(e).__name__}: {e}"
            res = wr.TopicResult(t, "failed", None, [], [], [], [], 0, attention=[f"작성 중 오류: {type(e).__name__}: {e}"[:300]])
        wr.save(db, res, ctx.tracer.run_id)  # type: ignore[union-attr]
        results.append(res)
        _log_topic(ctx.tracer, t, res)
        if ctx.stopped:
            break
    return results


def run_weekly(week: str, ctx: Ctx, from_step: str = "cluster", only_topic: str | None = None,
               embedder: Any = None, cfg: BriefConfig | None = None, until: str | None = None) -> dict[str, Any]:
    """from_step부터 until까지(없으면 끝까지). until=select면 선별까지, write면 초안 + 코드 검사까지(검수자 없음)."""
    from ..filter.embed import make_embedder

    cfg = cfg or config.load("brief.yaml")
    db, tr = ctx.db, ctx.tracer
    assert tr is not None
    flt = config.load("filter.yaml")
    embedder = embedder or make_embedder("real", flt)
    interests = embed_interests(embedder, flt)
    dur: dict[str, float] = {}
    t0 = time.monotonic()
    src = (db.conn.execute("SELECT current_run_id FROM weeks WHERE week=?", (week,)).fetchone() or [None])[0]
    if from_step != "cluster" and not src:
        raise ValueError(f"{week}: 이어 갈 현재판 run이 없음(--from-step cluster부터)")
    if from_step != "cluster":  # cluster부터면 stage_cluster가 한다
        set_run_week(db, tr.run_id, week)
    ev, table, cluster_run = _cluster_phase(week, ctx, cfg, embedder, interests, from_step, src, dur)
    tr.step(kind="code", role="weekly", text=f"{week} weekly 시작: {from_step}부터", detail={
        "from_step": from_step, "source_run": src, "cluster_run": cluster_run})
    if ctx.stopped:  # 묶기 중 예산 초과: 현재판은 그대로, 선별부터는 시작하지 않음
        return _close(ctx, week, t0, dur)
    t1 = time.monotonic()
    topics = _select_phase(ctx, week, ev, cfg, embedder, interests, cluster_run, from_step, src)
    if topics is None:
        return _close(ctx, week, t0, dur)
    dur["select"] = round(time.monotonic() - t1, 1)
    t2 = time.monotonic()
    results = _write_phase(ctx, [] if until == "select" else topics, ev, table, cfg, from_step, src, only_topic, until)
    dur["write_review"] = round(time.monotonic() - t2, 1)
    if ctx.stopped:
        return _close(ctx, week, t0, dur, len(results))
    if only_topic and from_step != "cluster":  # 묶기부터 새로 했으면 원본 토픽과 맞지 않아 이어 오지 않음
        carry_over(db, src, tr.run_id, keep={only_topic})
    save_topic_embeddings(db, tr.run_id, embedder, results)
    return _close(ctx, week, t0, dur, len(results), until)


def _close(ctx: Ctx, week: str, t0: float, dur: dict[str, float], n_topics: int = 0, until: str | None = None) -> dict[str, Any]:
    """실행 요약을 계산해 저장하고, 멈추지 않았고 전부 실패도 아니면(until 단계 명령은 그대로) 이 run을 그 주 현재판으로
    올린다. weeks.status는 요약 상태에서 따온다."""
    db, tr = ctx.db, ctx.tracer
    assert tr is not None
    run_id = tr.run_id
    dur["total"] = round(time.monotonic() - t0, 1)
    tr.step(kind="code", role="weekly", text=f"{week} weekly 끝: 토픽 {n_topics}개" + (f", 예산 중단 {ctx.stopped}" if ctx.stopped else ""),
            attention=bool(ctx.stopped), detail={"duration_sec": dur, "stopped": ctx.stopped})
    summary = compute_summary(db, run_id)
    with db.conn:
        db.conn.execute("UPDATE runs SET summary_json=? WHERE id=?", (json.dumps(summary, ensure_ascii=False), run_id))
        if not ctx.stopped and (until or summary["status"] != "failed"):
            status = ({"select": "selected", "write": "written"}[until] if until
                      else {"done": "done", "partial": "written"}[summary["status"]])
            db.conn.execute("UPDATE weeks SET status=?, current_run_id=? WHERE week=?", (status, run_id, week))
    return summary


def carry_over(db: DB, src: str, run_id: str, keep: set[str]) -> None:
    """토픽 하나만 다시 돌린 run에 나머지 토픽의 결과(상태, 최종판, 판정, 근거 연결, 임베딩)를 원본 run에서 복사한다.
    그래야 그 run이 그 주 현재판이 되어도 토픽이 빠지지 않는다. 복사한 행도 이 run_id로 쌓인다(원본은 그대로)."""
    rows = db.conn.execute("SELECT topic_id, status, final_round, title, summary, checks_json FROM topics WHERE run_id=?",
                           (src,)).fetchall()
    with db.conn:
        for r in rows:
            if r["topic_id"] in keep:
                continue
            db.conn.execute("UPDATE topics SET status=?, final_round=?, title=?, summary=?, checks_json=? "
                            "WHERE run_id=? AND topic_id=?",
                            (r["status"], r["final_round"], r["title"], r["summary"], r["checks_json"], run_id, r["topic_id"]))
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


def _drop_counts(plan: dict[str, Any], fallback: bool) -> tuple[dict[str, int], dict[str, int]]:
    """누가 뺐나(리뷰 R8): 모델이 직접 / 코드 정리(reconcile) / 대체 계획(점수 순)."""
    drops = {k: 0 for k in ("duplicate", "low_relevance", "thin", "other")}
    drops_by = {"model": 0, "code": 0, "fallback": 0}
    for d in plan.get("decisions", []):
        if d.get("action") == "drop":
            drops[d.get("drop_reason") or "other"] = drops.get(d.get("drop_reason") or "other", 0) + 1
            by = "fallback" if fallback else "code" if sel.RECONCILE_MARK in (d.get("reason") or "") else "model"
            drops_by[by] += 1
    return drops, drops_by


def _review_counts(db: DB, run_id: str, verdicts: list[Any]) -> tuple[dict[str, int], int, int]:
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
    return issue_types, autofixes, reverts


def _check_points(db: DB, run_id: str, topics: list[Any]) -> int:
    n = 0
    for t in topics:
        r = db.conn.execute("SELECT page_json FROM topic_pages WHERE run_id=? AND topic_id=? ORDER BY round DESC LIMIT 1",
                            (run_id, t["topic_id"])).fetchone()
        if r:
            n += sum(1 for s in json.loads(r["page_json"]).get("sections", []) if s.get("check"))
    return n


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
    plan_row = db.conn.execute("SELECT plan_json, source FROM briefing_plans WHERE run_id=? ORDER BY id DESC LIMIT 1",
                               (run_id,)).fetchone()
    plan = json.loads(plan_row["plan_json"]) if plan_row else {"decisions": [], "topics": [], "splits": []}
    topics = db.conn.execute("SELECT topic_id, status, final_round, checks_json FROM topics WHERE run_id=?", (run_id,)).fetchall()
    verdicts = db.conn.execute("SELECT checker, status, issues_json, autofix_json FROM verdicts WHERE run_id=?",
                               (run_id,)).fetchall()
    fallback = bool(plan_row) and plan_row["source"] == "fallback"
    drops, drops_by = _drop_counts(plan, fallback)
    issue_types, autofixes, reverts = _review_counts(db, run_id, verdicts)
    check_points = _check_points(db, run_id, topics)
    cost = {k: round(float(db.conn.execute("SELECT COALESCE(SUM(cost_usd),0) FROM steps WHERE run_id=? AND role=?",
                                           (run_id, k)).fetchone()[0] or 0), 6) for k in ROLES}
    cost["total"] = round(sum(cost.values()), 6)
    end = next(iter(_detail(db, run_id, "weekly", f"{week} weekly 끝")), {})
    rel_types = [t.get("relation", {}).get("type") for t in plan.get("topics", [])]
    return {
        "week": week, "model": _model(db, run_id), "status": "stopped" if end.get("stopped") else run_status(topics),
        "cluster_run": cluster_run,
        "evidence": {"items": ev.get("counts", {"text": 0, "video": 0, "github": 0}),
                     "excluded": ev.get("excluded", {"no_card": 0, "no_digest": 0, "irrelevant_repo": 0})},
        "aliases": {"candidates": norm.get("counts", {}).get("candidates", 0),
                    "auto_approved": norm.get("counts", {}).get("auto_approved", 0),
                    "decide_calls": len(norm.get("decide", []))},
        "cluster": {"clusters": len(clusters), "single_item": sum(c["n_items"] == 1 for c in cands),
                    "multi_channel": sum(len(c) >= 2 for c in chans), "three_channel": sum(len(c) >= 3 for c in chans),
                    "decide_calls": sum(p["decided"] for p in pairs),
                    "decide_merged": sum(1 for p in pairs if p["decided"] and p["answer"]
                                         and (p["confidence"] or 0) >= config.load("brief.yaml").cluster.decide.min_confidence),
                    "past": {"new": rel_types.count("new"), "follow_up": rel_types.count("follow_up"),
                             "duplicate": drops["duplicate"]}},
        "select": {"candidates": len(plan.get("decisions", [])), "selected": len(plan.get("topics", [])),
                   "merges": sum(1 for t in plan.get("topics", []) if len(t.get("cluster_ids", [])) > 1),
                   "splits": len(plan.get("splits", [])), "drops": drops, "drops_by": drops_by},
        "write": {"topics": len(topics), "failed": sum(t["status"] == "failed" for t in topics)},
        "review": {"rounds": {str(k): sum(1 for t in topics if t["final_round"] == k) for k in (1, 2, 3)},
                   "code_rejects": sum(1 for v in verdicts if v["checker"] == "code" and v["status"] == "reject"),
                   "critic_rejects": sum(1 for v in verdicts if v["checker"] == "critic" and v["status"] == "reject"),
                   "autofixes": autofixes, "reverts": reverts, "issues": issue_types, "check_points": check_points,
                   "check_topics": sum(1 for t in topics if json.loads(t["checks_json"] or "[]"))},
        "cost_usd": cost,
        "duration_sec": {k: end.get("duration_sec", {}).get(k, 0) for k in ("evidence", "cluster", "select", "write_review",
                                                                            "total")},
    }


def run_status(topics: list[Any]) -> str:
    """토픽 상태들 → done(실패 없음) / partial(일부 실패) / failed(전부 실패, 토픽 없음 포함). weeks.status도 이 결과에서 따온다."""
    failed = sum(t["status"] == "failed" for t in topics)
    return "failed" if failed == len(topics) else "partial" if failed else "done"


def _model(db: DB, run_id: str) -> str:
    r = db.conn.execute("SELECT model FROM steps WHERE run_id=? AND kind='llm' AND role IN ('writer','editor_select') "
                        "AND model IS NOT NULL LIMIT 1", (run_id,)).fetchone()
    return r["model"] if r else ""
