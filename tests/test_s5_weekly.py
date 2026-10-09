"""S5 관문 A10(라운드)·A11(저장)·A12(실행 요약)·A13(예시 JSON 매핑): 모의 LLM으로 weekly 끝까지."""

from __future__ import annotations

import json

import pytest

from tests.conftest import FakeTransport, make_ctx, response
from trendsit.brief import briefing, pipeline
from trendsit.brief.weekly import stage_cluster
from trendsit.core import config
from trendsit.core.trace import Tracer
from trendsit.filter.embed import HashEmbedder

CFG = config.load("brief.yaml")
TITLES = {1: "Gemini 4 Argon launch", 2: "Mistral Large 4 release", 3: "Claude Haiku 5.5 pricing", 4: "EmbeddingGemma 2 open"}
QUOTES = {1: "Argon scores 77.9% on DeepSWE.", 2: "Large 4 has 1T parameters and 68% on CWE-bench.",
          3: "Haiku 5.5 costs $1 per million tokens.", 4: "EmbeddingGemma 2 tops MTEB with 71.2%."}


def page(i: int, text: str, summary: str = "모델이 공개됐다.") -> str:
    return json.dumps({"points": [{"text": text, "refs": [f"it:{i}#q1"], "check": False},
                                  {"text": f"{TITLES[i]} 관련 두 번째 사실 정리", "refs": [f"it:{i}#q1"], "check": False}],
                       "numbers": [], "events": [], "contributions": [], "concepts": [],
                       "overview": "새 모델이 나왔다. 근거 문장 하나가 있다.", "summary": summary, "title": TITLES[i],
                       "log": "l", "attention": False}, ensure_ascii=False)


def verdict(issues: list[dict]) -> str:
    return json.dumps({"atoms": [{"loc": "points[0]", "fact": "f", "evidence_id": "it:1#q1", "supported": not issues}],
                       "fact_support": {"total": 9, "supported": 9}, "issues": issues,
                       "status": "reject" if issues else "pass", "log": "l", "attention": bool(issues)}, ensure_ascii=False)


def revision(changes: list[dict]) -> str:
    return json.dumps({"changed": changes, "log": "l", "attention": False}, ensure_ascii=False)


@pytest.fixture
def week(tmp_path, monkeypatch):
    monkeypatch.setattr(briefing, "OUT", tmp_path / "out")
    ctx = make_ctx(tmp_path, FakeTransport([]), spec_cap=1.0)
    c = ctx.db.conn
    c.execute("INSERT INTO sources(id, channel, name) VALUES ('openai','text','OpenAI')")
    for i in TITLES:
        c.execute("INSERT INTO items(id, source_id, channel, external_id, title, url, day, week) VALUES (?,?,?,?,?,?,?,?)",
                  (i, "openai", "text", f"e{i}", TITLES[i], f"https://x/{i}", "2026-10-06", "2026-W41"))
        card = {"quotes": [{"n": 1, "text": QUOTES[i]}], "numbers": [], "claims": [], "summary": QUOTES[i],
                "entities": [TITLES[i].split()[0] + f"{i}"], "keywords": ["frontier-release"], "relevance": "high"}
        c.execute("INSERT INTO item_cards(item_id, version, card_json) VALUES (?, 1, ?)", (i, json.dumps(card)))
    c.commit()
    ctx.no_cache = True  # 같은 요청이 캐시로 답하면 모의 응답 순서가 어긋남
    stage = stage_cluster("2026-W41", ctx, CFG, HashEmbedder(), use_llm=False)
    ctx.tracer.finish("ok")
    cids = {r["member"]: r["cluster_id"] for r in c.execute(
        "SELECT ci.member, ci.cluster_id FROM cluster_items ci JOIN clusters k ON k.id=ci.cluster_id WHERE k.run_id=?",
        (stage.run_id,))}
    return ctx, cids


def plan(cids: dict[str, int]) -> str:
    ids = [cids[f"it:{i}"] for i in TITLES]
    return json.dumps({"decisions": [{"cluster_id": x, "reason": "글 1", "action": "select", "drop_reason": None} for x in ids],
                       "splits": [], "topics": [{"cluster_ids": [x], "rank": r, "lead": r == 1,
                                                 "relation": {"type": "new", "topic_id": None}, "relation_reason": "새",
                                                 "angle": "출시", "slug_hint": f"model {r}"} for r, x in enumerate(ids, 1)],
                       "featured_repos": [], "log": "후보 4개 중 4개 선정", "attention": False}, ensure_ascii=False)


def test_weekly_rounds_storage_summary_export(week):
    ctx, cids = week
    bad = "Argon이 DeepSWE에서 88.0% 기록"  # 근거는 77.9%
    responses = [
        plan(cids),
        # 토픽 1: 초안(코드 반려) → 수정(지적 안 된 summary도 바꿈 → 되돌림) → 검수 반려(points[1]) → 수정 → 같은 이슈 다시 → check
        page(1, bad),
        revision([{"issue_idx": 0, "loc": "points[0]", "action": "edit",
                   "value": {"text": "Argon이 DeepSWE에서 77.9% 기록", "refs": ["it:1#q1"], "check": False}},
                  {"issue_idx": 0, "loc": "summary", "action": "edit", "value": "몰래 바꾼 요약이다."}]),
        verdict([{"loc": "points[1]", "type": "unsupported", "evidence_id": "it:1#q1", "comment": "근거에 없음", "hint": "삭제"}]),
        revision([{"issue_idx": 0, "loc": "points[1]", "action": "edit",
                   "value": {"text": "Gemini 4 Argon 관련 다른 서술로 바꿈", "refs": ["it:1#q1"], "check": False}}]),
        verdict([{"loc": "points[1]", "type": "unsupported", "evidence_id": "it:1#q1", "comment": "여전히 없음", "hint": "삭제"}]),
    ]
    for i in (2, 3, 4):
        responses += [page(i, f"{TITLES[i]} 근거 문장 요약 정리"), verdict([])]
    ctx.llm.transport.responses = [response(r) for r in responses]
    ctx.tracer = Tracer(ctx.db, "weekly", "S0")
    summary = pipeline.run_weekly("2026-W41", ctx, from_step="select", embedder=HashEmbedder(), cfg=CFG)
    run_id = ctx.tracer.run_id
    db = ctx.db.conn
    t1 = db.execute("SELECT * FROM topics WHERE run_id=? AND rank=1", (run_id,)).fetchone()
    # A10: 3라운드 상한, 코드 반려도 셈, 같은 이슈 2회면 check, 지적 안 된 칸 되돌림
    assert t1["status"] == "checked" and t1["final_round"] == 3 and t1["topic_id"] == "w41-model-1"
    rounds = db.execute("SELECT round, checker, status FROM verdicts WHERE run_id=? AND topic_id=? ORDER BY id",
                        (run_id, t1["topic_id"])).fetchall()
    assert [tuple(r) for r in rounds] == [(1, "code", "reject"), (2, "code", "pass"), (2, "critic", "reject"),
                                          (3, "code", "pass"), (3, "critic", "reject")]
    final = json.loads(db.execute("SELECT page_json FROM topic_pages WHERE run_id=? AND topic_id=? ORDER BY round DESC, id DESC",
                                  (run_id, t1["topic_id"])).fetchone()[0])
    assert final["summary"] == "모델이 공개됐다." and "77.9%" in final["points"][0]["text"]
    assert final["points"][1]["check"] is True
    assert summary["review"]["reverts"] == 1 and summary["review"]["code_rejects"] == 1
    assert summary["review"]["critic_rejects"] == 2 and summary["review"]["check_points"] == 1
    # A11: 마이그레이션 대역, topic_evidence = 최종판 refs
    from trendsit.core.migrations import MIGRATIONS

    assert {30, 31, 32, 33} <= set(MIGRATIONS)
    refs = {(r["evidence_id"], r["field"]) for r in db.execute(
        "SELECT evidence_id, field FROM topic_evidence WHERE run_id=? AND topic_id=?", (run_id, t1["topic_id"]))}
    assert refs == {("it:1#q1", "point")}
    assert db.execute("SELECT current_run_id, status FROM weeks").fetchone()[:] == (run_id, "done")
    # A12: 형식(스펙 5.10 칸)과 표에서 다시 계산한 값이 같음
    assert set(summary) >= {"week", "model", "status", "evidence", "aliases", "cluster", "select", "write", "review",
                            "cost_usd", "duration_sec"}
    assert set(summary["review"]["issues"]) == {"unsupported", "number_mismatch", "overclaim", "missing_key", "wrong_ref",
                                                "overuse", "missing_diagram"}
    stored = json.loads(db.execute("SELECT summary_json FROM runs WHERE id=?", (run_id,)).fetchone()[0])
    assert stored == pipeline.compute_summary(ctx.db, run_id) == summary
    assert summary["select"] == {"candidates": 4, "selected": 4, "merges": 0, "splits": 0,
                                 "drops": {"duplicate": 0, "low_relevance": 0, "thin": 0, "other": 0}}
    assert summary["write"] == {"topics": 4, "failed": 0}
    # A13: 저장값만으로 예시 JSON 토픽 칸
    srcs, _ = briefing.sources_index(ctx.db, "2026-W41")
    ex = briefing.export_topic(ctx.db, run_id, t1["topic_id"], srcs)
    assert set(ex) >= {"id", "week", "rank", "lead", "title", "summary", "relation", "overview", "points", "diagrams",
                       "concepts", "contributions", "sources", "channels", "has_check"}
    assert ex["week"] == "2026-w41" and ex["has_check"] and ex["points"][0]["refs"] == ["s1"]
    assert ex["sources"][0]["title"] == TITLES[1]
    # 재실행: 새 run, 이전 행 보존, current_run_id 갱신
    ctx.llm.transport.responses = [response(r) for r in [plan(cids)] + [x for i in TITLES for x in
                                                                        (page(i, f"{TITLES[i]} 근거 문장 요약 정리"), verdict([]))]]
    ctx.tracer = Tracer(ctx.db, "weekly", "S0")
    pipeline.run_weekly("2026-W41", ctx, from_step="select", embedder=HashEmbedder(), cfg=CFG)
    assert db.execute("SELECT COUNT(DISTINCT run_id) FROM topics").fetchone()[0] == 2
    assert db.execute("SELECT current_run_id FROM weeks").fetchone()[0] == ctx.tracer.run_id
    path = briefing.write_briefing_md(ctx.db, "2026-W41")
    assert "## 1. 리드 · " in path.read_text()


def test_editor_select_retries_then_falls_back(week):
    ctx, cids = week
    bad = json.loads(plan(cids))
    bad["topics"][1]["lead"] = True  # 리드 2개 → 거부
    ctx.llm.transport.responses = [response(json.dumps(bad, ensure_ascii=False))] * 3 + [
        response(x) for i in TITLES for x in (page(i, f"{TITLES[i]} 근거 문장 요약 정리"), verdict([]))]
    ctx.tracer = Tracer(ctx.db, "weekly", "S0")
    summary = pipeline.run_weekly("2026-W41", ctx, from_step="select", embedder=HashEmbedder(), cfg=CFG)
    row = ctx.db.conn.execute("SELECT source FROM briefing_plans WHERE run_id=?", (ctx.tracer.run_id,)).fetchone()
    assert row["source"] == "fallback" and summary["select"]["selected"] == 4
    sent = [b["messages"][-1]["content"] for b in ctx.llm.transport.bodies[1:3]]
    assert all("lead가 2개" in s for s in sent)  # 재시도 입력에 거부 이유


def test_single_topic_rerun_carries_other_topics(tmp_path):
    """토픽 하나만 다시 돌린 run도 그 주 현재판이 될 수 있게 나머지 토픽 결과를 원본 run에서 복사."""
    from trendsit.core.db import DB

    db = DB(tmp_path / "t.db")
    c = db.conn
    for run in ("old", "new"):
        for tid in ("a", "b"):
            c.execute("INSERT INTO topics(run_id, topic_id, week, cluster_ids_json, rank, lead, status) VALUES (?,?,?,?,?,?,?)",
                      (run, tid, "2026-W41", "[1]", 1, 0, "selected"))
    c.execute("UPDATE topics SET status='passed', final_round=2, title='B 제목' WHERE run_id='old' AND topic_id='b'")
    c.execute("INSERT INTO topic_pages(run_id, topic_id, round, page_json) VALUES ('old','b',2,'{}'), ('old','a',1,'{}')")
    c.execute("INSERT INTO topic_evidence(run_id, topic_id, evidence_id, member, field, idx) VALUES ('old','b','it:1#q1','it:1','point',0)")
    c.commit()
    pipeline.carry_over(db, "old", "new", keep={"a"})
    b = c.execute("SELECT status, final_round, title FROM topics WHERE run_id='new' AND topic_id='b'").fetchone()
    assert tuple(b) == ("passed", 2, "B 제목")
    assert c.execute("SELECT COUNT(*) FROM topic_pages WHERE run_id='new'").fetchone()[0] == 1  # a는 다시 쓴 것만
    assert c.execute("SELECT COUNT(*) FROM topic_evidence WHERE run_id='new' AND topic_id='b'").fetchone()[0] == 1
    assert c.execute("SELECT COUNT(*) FROM topic_pages WHERE run_id='old'").fetchone()[0] == 2  # 원본 보존
