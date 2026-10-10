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
                       "featured_repos": [], "log": "후보 4개 중 4개 선정",
                       "attention": False}, ensure_ascii=False)


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

    assert {30, 31, 32, 33, 34, 35} <= set(MIGRATIONS)
    assert json.loads(t1["checks_json"]) == ["points[1]"] and summary["review"]["check_topics"] == 1  # 토픽 수준 확인 필요(R4)
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
                                 "drops": {"duplicate": 0, "low_relevance": 0, "thin": 0, "other": 0},
                                 "drops_by": {"model": 0, "code": 0, "fallback": 0}}
    assert summary["write"] == {"topics": 4, "failed": 0}
    # A13: 저장값만으로 예시 JSON 토픽 칸
    srcs, _ = briefing.sources_index(ctx.db, "2026-W41")
    ex = briefing.export_topic(ctx.db, run_id, t1["topic_id"], srcs)
    assert set(ex) >= {"id", "week", "rank", "lead", "title", "summary", "relation", "overview", "points", "diagrams",
                       "concepts", "contributions", "sources", "channels", "has_check"}
    assert ex["week"] == "2026-w41" and ex["has_check"] and ex["checks"] == ["points[1]"]
    assert ex["points"][0]["refs"] == ["s1"]
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


def test_unresolved_diagram_issue_drops_the_group(week):
    """도식 위치의 이슈가 두 번 남으면 그 그룹을 빼고(포인트 문장은 남김) 토픽은 checked."""
    ctx, cids = week
    p1 = json.loads(page(1, "Argon이 DeepSWE에서 77.9% 기록"))
    p1["numbers"] = [{"anchor": 1, "group": "g", "title": "점수", "context": "같은 벤치 [it:1#q1]", "unit": "ms",
                      "items": [{"label": lab, "value": "77.9", "ref": "it:1#q1", "baseline": False, "emphasis": False}
                                for lab in ("a", "b", "c")]}]
    # 코드 반려만 이어지면 끝에서 검수자가 한 번 봄(리뷰 지적 2) → verdict 응답 하나
    responses = [plan(cids), json.dumps(p1, ensure_ascii=False), revision([]), verdict([])]
    for i in (2, 3, 4):
        responses += [page(i, f"{TITLES[i]} 근거 문장 요약 정리"), verdict([])]
    ctx.llm.transport.responses = [response(r) for r in responses]
    ctx.tracer = Tracer(ctx.db, "weekly", "S0")
    pipeline.run_weekly("2026-W41", ctx, from_step="select", embedder=HashEmbedder(), cfg=CFG)
    run_id = ctx.tracer.run_id
    t1 = ctx.db.conn.execute("SELECT status FROM topics WHERE run_id=? AND rank=1", (run_id,)).fetchone()
    final = json.loads(ctx.db.conn.execute("SELECT page_json FROM topic_pages WHERE run_id=? AND topic_id='w41-model-1' "
                                           "ORDER BY round DESC, id DESC", (run_id,)).fetchone()[0])
    assert t1["status"] == "checked" and final["numbers"] == [] and "77.9%" in final["points"][0]["text"]
    checks_json = ctx.db.conn.execute("SELECT checks_json FROM topics WHERE run_id=? AND rank=1", (run_id,)).fetchone()[0]
    assert "빠진 도식: 점수" in json.loads(checks_json)  # ⚠가 빠진 도식을 가리키면 제목으로(F2-c)
    checkers = [r[0] for r in ctx.db.conn.execute("SELECT checker FROM verdicts WHERE run_id=? AND topic_id='w41-model-1' "
                                                  "ORDER BY id", (run_id,))]
    assert checkers == ["code", "code", "critic"]



def test_same_issue_twice_within_one_round_is_not_repeat(week):
    """같은 라운드에 같은 (위치, 유형) 이슈가 2건이어도 한 번으로 센다(리뷰 지적 1): 고친 뒤 통과하면 passed."""
    ctx, cids = week
    two = [{"loc": "points[1]", "type": "unsupported", "evidence_id": "it:1#q1", "comment": c, "hint": "h"}
           for c in ("근거 없음 1", "근거 없음 2")]
    responses = [plan(cids), page(1, "Argon이 DeepSWE에서 77.9% 기록"), verdict(two),
                 revision([{"issue_idx": 0, "loc": "points[1]", "action": "edit",
                            "value": {"text": "Gemini 4 Argon 근거 문장 요약 정리", "refs": ["it:1#q1"], "check": False}}]),
                 verdict([])]
    for i in (2, 3, 4):
        responses += [page(i, f"{TITLES[i]} 근거 문장 요약 정리"), verdict([])]
    ctx.llm.transport.responses = [response(r) for r in responses]
    ctx.tracer = Tracer(ctx.db, "weekly", "S0")
    pipeline.run_weekly("2026-W41", ctx, from_step="select", embedder=HashEmbedder(), cfg=CFG)
    t1 = ctx.db.conn.execute("SELECT status, final_round FROM topics WHERE run_id=? AND rank=1",
                             (ctx.tracer.run_id,)).fetchone()
    assert tuple(t1) == ("passed", 2)


def test_revision_with_wrong_sub_value_keeps_previous():
    from trendsit.brief.write import apply_revision
    from trendsit.core.artifacts_brief import (
        Change,
        NumberGroup,
        NumberItem,
        Point,
        TopicPage,
        TopicPageRevision,
    )

    g = NumberGroup(anchor=1, group="g", title="t", context="c", unit="%",
                    items=[NumberItem(label=x, value="1", ref="r") for x in "abc"])
    p = TopicPage(points=[Point(text="문장 하나 둘 셋 넷", refs=["r"])], numbers=[g], events=[], contributions=[],
                  concepts=[], overview="o다.", summary="s다.", title="t", log="l")
    rev = TopicPageRevision(changed=[Change(issue_idx=0, loc="numbers[0].items[1]", action="edit",
                                            value=Point(text="x", refs=[]))], log="l")
    new, _, notes = apply_revision(p, rev, {"numbers[0]"})
    assert new.numbers[0].items[1].value == "1" and notes
    whole = TopicPageRevision(changed=[Change(issue_idx=0, loc="points", action="delete", value=None)], log="l")
    assert apply_revision(p, whole, {"points"})[0].points  # 포인트 전체 삭제는 받지 않음


def test_export_numbers_events_og_and_checks(tmp_path):
    """A13: 도식(수치·사건), og: 근거의 원본 URL, 토픽 수준 확인 필요가 예시 JSON 칸으로."""
    ctx = make_ctx(tmp_path, FakeTransport([]), spec_cap=1.0)
    db = ctx.db.conn
    page = {"points": [{"text": "정확도 B 93.5%로 가장 높음", "refs": ["og:5#q1"], "check": False},
                       {"text": "발표 일정 정리", "refs": ["it:5#q1"], "check": False}],
            "numbers": [{"anchor": 1, "group": "g", "title": "B 정확도 93.5%로 최고", "context": "같은 벤치 [og:5#q1]",
                         "unit": "%", "items": [{"label": x, "value": v, "ref": "og:5#q1", "baseline": False,
                                                 "emphasis": x == "B"} for x, v in (("A", "86.6"), ("B", "93.5"), ("C", "81.2"))]}],
            "events": [{"anchor": 2, "title": "공개 흐름", "context": "발표 순서", "flow_is_point": False,
                        "items": [{"date": f"2026-10-0{d}", "text": f"사건 {d}", "ref": "it:5#q1", "topic_id": None}
                                  for d in (5, 6, 7)]}],
            "contributions": [], "concepts": [], "overview": "a다. b다.", "summary": "요약이다.", "title": "제목",
            "log": "l", "attention": False}
    db.execute("INSERT INTO topics(run_id, topic_id, week, cluster_ids_json, rank, lead, relation_type, status, final_round,"
               " angle, checks_json) VALUES ('r','w41-x','2026-W41','[]',1,1,'new','checked',2,'a','[\"summary\"]')")
    db.execute("INSERT INTO topic_pages(run_id, topic_id, round, page_json) VALUES ('r','w41-x',2,?)", (json.dumps(page),))
    db.executemany("INSERT INTO topic_evidence(run_id, topic_id, evidence_id, member, field, idx) VALUES ('r','w41-x',?,?,?,?)",
                   [("og:5#q1", "it:5", "point", 0), ("it:5#q1", "it:5", "point", 1), ("og:5#q1", "it:5", "number", 0)])
    db.commit()
    srcs = {"og:5#q1": {"channel": "text", "site": "S", "title": "T", "date": "2026-10-06", "url": "https://s/5",
                        "origin": {"url": "https://origin/5", "kind": "blog"}},
            "it:5#q1": {"channel": "text", "site": "S", "title": "T", "date": "2026-10-06", "url": "https://s/5"}}
    ex = briefing.export_topic(ctx.db, "r", "w41-x", srcs)
    bars, events = ex["diagrams"]
    assert bars["type"] == "bars" and bars["anchor"] == 1 and bars["ref"] == "s1" and bars["items"][1]["emphasis"]
    assert events["type"] == "events" and [i["ref"] for i in events["items"]] == ["s1"] * 3
    assert ex["sources"] == [{"id": "s1", "channel": "text", "site": "S", "title": "T", "date": "2026-10-06",
                              "url": "https://s/5", "origin": "https://origin/5"}]
    assert ex["checks"] == ["summary"] and ex["has_check"]


def test_critic_empty_atoms_is_not_a_pass(week):
    """원자 사실 0개 통과는 대조를 건너뛴 판정: 한 번 다시 부르고, 또 비면 검수 실패(attention), 판정은 기록하지 않음."""
    ctx, cids = week
    empty = json.dumps({"atoms": [], "fact_support": {"total": 0, "supported": 0}, "issues": [], "status": "pass",
                        "log": "원자 사실 0개", "attention": False})
    responses = [plan(cids), page(1, "Argon이 DeepSWE에서 77.9% 기록"), empty, empty]
    for i in (2, 3, 4):
        responses += [page(i, f"{TITLES[i]} 근거 문장 요약 정리"), verdict([])]
    ctx.llm.transport.responses = [response(r) for r in responses]
    ctx.tracer = Tracer(ctx.db, "weekly", "S0")
    pipeline.run_weekly("2026-W41", ctx, from_step="select", embedder=HashEmbedder(), cfg=CFG)
    run_id = ctx.tracer.run_id
    checkers = [r[0] for r in ctx.db.conn.execute(
        "SELECT checker FROM verdicts WHERE run_id=? AND topic_id='w41-model-1' ORDER BY id", (run_id,))]
    assert checkers == ["code"]  # 빈 판정 두 번 → 검수 실패, critic 판정 기록 없음
    att = [json.loads(r[0]) for r in ctx.db.conn.execute(
        "SELECT detail FROM steps WHERE run_id=? AND role='writer' AND kind='code' AND text LIKE 'w41-model-1%'", (run_id,))]
    assert att and att[0]["topic_id"] == "w41-model-1"


def test_f2_diagram_with_only_critic_issue_is_kept_with_check(week):
    """도식은 코드가 확인한 형식·수치 오류일 때만 뺀다. 검수자 의미 지적만 두 번 남으면 도식은 두고 ⚠(반영 확인 리뷰 F2)."""
    ctx, cids = week
    p1 = json.loads(page(1, "Argon이 DeepSWE에서 77.9% 기록"))
    p1["numbers"] = [{"anchor": 1, "group": "g", "title": "Argon DeepSWE 77.9%", "context": "같은 벤치 [it:1#q1]", "unit": "%",
                      "items": [{"label": lab, "value": "77.9", "ref": "it:1#q1", "baseline": False, "emphasis": False}
                                for lab in ("a", "b", "c")]}]
    over = [{"loc": "numbers[0]", "type": "overuse", "evidence_id": "it:1#q1", "comment": "같은 값 셋", "hint": "h"}]
    responses = [plan(cids), json.dumps(p1, ensure_ascii=False), verdict(over),
                 revision([{"issue_idx": 0, "loc": "numbers[0].title", "action": "edit", "value": "Argon 점수"}]), verdict(over)]
    for i in (2, 3, 4):
        responses += [page(i, f"{TITLES[i]} 근거 문장 요약 정리"), verdict([])]
    ctx.llm.transport.responses = [response(r) for r in responses]
    ctx.tracer = Tracer(ctx.db, "weekly", "S0")
    pipeline.run_weekly("2026-W41", ctx, from_step="select", embedder=HashEmbedder(), cfg=CFG)
    run_id = ctx.tracer.run_id
    t = ctx.db.conn.execute("SELECT status, checks_json FROM topics WHERE run_id=? AND topic_id='w41-model-1'", (run_id,)).fetchone()
    final = json.loads(ctx.db.conn.execute("SELECT page_json FROM topic_pages WHERE run_id=? AND topic_id='w41-model-1' "
                                           "ORDER BY round DESC, id DESC", (run_id,)).fetchone()[0])
    assert t["status"] == "checked" and json.loads(t["checks_json"]) == ["numbers[0]"] and len(final["numbers"]) == 1


def test_f2c_check_pointing_to_removed_diagram_is_labeled():
    from trendsit.core.artifacts_brief import TopicPage

    p = TopicPage.model_validate(json.loads(page(1, "Argon이 DeepSWE에서 77.9% 기록")))
    assert briefing.visible_checks(["numbers[1]", "points[0]"], p) == ["빠진 도식(numbers[1])", "points[0]"]
