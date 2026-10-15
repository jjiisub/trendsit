"""S5 관문 A10(라운드)·A11(저장)·A12(실행 요약)·A13(예시 JSON 매핑): 모의 LLM으로 weekly 끝까지(S6-1 v2)."""

from __future__ import annotations

import json

import pytest

from tests.conftest import FakeTransport, make_ctx, response
from trendsit import export
from trendsit.brief import briefing, pipeline, report
from trendsit.brief.weekly import stage_cluster
from trendsit.core import config
from trendsit.core.trace import Tracer
from trendsit.filter.embed import HashEmbedder

CFG = config.load("brief.yaml")
TITLES = {1: "Gemini 4 Argon launch", 2: "Mistral Large 4 release", 3: "Claude Haiku 5.5 pricing", 4: "EmbeddingGemma 2 open"}
QUOTES = {1: "Argon scores 77.9% on DeepSWE.", 2: "Large 4 has 1T parameters and 68% on CWE-bench.",
          3: "Haiku 5.5 costs $1 per million tokens.", 4: "EmbeddingGemma 2 tops MTEB with 71.2%."}


def _sec(heading: str, text: str, refs: list[str], **over) -> dict:
    base = {"heading": heading, "paragraphs": [{"text": text, "refs": refs}], "visual": "none", "bars": None,
            "table": None, "tiles": [], "events": None, "slide": None, "slide_caption": "", "video_secs": [],
            "check": False}
    base.update(over)
    return base


def page(i: int, text: str, summary: str = "모델이 공개됐다. 쟁점이 있다.", n_sections: int = 3) -> str:
    """단일 소스 토픽(sections [3,5]): 첫 절에 text, 나머지는 채우기용 절."""
    sections = [_sec(f"{TITLES[i]} 핵심 사실", text, [f"it:{i}#q1"])]
    for j in range(2, n_sections + 1):
        sections.append(_sec(f"{TITLES[i]} 관련 {j}번째 사실", f"{TITLES[i]} 관련 {j}번째 사실 정리했다.", [f"it:{i}#q1"]))
    return json.dumps({"head_tiles": [], "sections": sections, "summary": summary, "title": TITLES[i],
                       "log": "l", "attention": False}, ensure_ascii=False)


def verdict(issues: list[dict]) -> str:
    return json.dumps({"atoms": [{"loc": "sections[0]", "fact": "f", "evidence_id": "it:1#q1", "supported": not issues}],
                       "fact_support": {"total": 9, "supported": 9}, "issues": issues,
                       "status": "reject" if issues else "pass", "log": "l", "attention": bool(issues)}, ensure_ascii=False)


def revision(changes: list[dict]) -> str:
    return json.dumps({"changed": changes, "log": "l", "attention": False}, ensure_ascii=False)


@pytest.fixture
def week(tmp_path, monkeypatch):
    monkeypatch.setattr(report, "OUT", tmp_path / "out")  # 읽기본·묶기 리포트 모두 이 폴더
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
    bad = "Argon이 DeepSWE에서 88.0% 기록했다"  # 근거는 77.9%
    responses = [
        plan(cids),
        # 토픽 1: 초안(코드 반려) → 수정(지적 안 된 summary도 바꿈 → 되돌림) → 검수 반려(sections[1]) → 수정 → 같은 이슈 다시 → check
        page(1, bad),
        revision([{"issue_idx": 0, "loc": "sections[0].paragraphs[0]", "action": "edit",
                   "value": {"text": "Argon이 DeepSWE에서 77.9% 기록했다", "refs": ["it:1#q1"]}},
                  {"issue_idx": 0, "loc": "summary", "action": "edit", "value": "몰래 바꾼 요약이다."}]),
        verdict([{"loc": "sections[1].paragraphs[0]", "type": "unsupported", "evidence_id": "it:1#q1",
                  "comment": "근거에 없음", "hint": "삭제"}]),
        revision([{"issue_idx": 0, "loc": "sections[1].paragraphs[0]", "action": "edit",
                   "value": {"text": "Gemini 4 Argon 관련 다른 서술로 바꿨다", "refs": ["it:1#q1"]}}]),
        verdict([{"loc": "sections[1].paragraphs[0]", "type": "unsupported", "evidence_id": "it:1#q1",
                  "comment": "여전히 없음", "hint": "삭제"}]),
    ]
    for i in (2, 3, 4):
        responses += [page(i, f"{TITLES[i]} 근거 문장 요약 정리했다"), verdict([])]
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
    assert final["summary"] == "모델이 공개됐다. 쟁점이 있다." and "77.9%" in final["sections"][0]["paragraphs"][0]["text"]
    assert final["sections"][1]["check"] is True
    assert summary["review"]["reverts"] == 1 and summary["review"]["code_rejects"] == 1
    assert summary["review"]["critic_rejects"] == 2 and summary["review"]["check_points"] == 1
    # A11: 마이그레이션 대역, topic_evidence = 최종판 refs
    from trendsit.core.migrations import MIGRATIONS

    assert {30, 31, 32, 33, 34, 35} <= set(MIGRATIONS)
    assert json.loads(t1["checks_json"]) == ["sections[1]"] and summary["review"]["check_topics"] == 1
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
    # A13: 저장값만으로 사이트 데이터 토픽 v2 칸
    srcs = briefing.sources_index(ctx.db, "2026-W41")
    ex = briefing.export_topic(ctx.db, run_id, t1["topic_id"], srcs)
    assert set(ex) >= {"id", "week", "rank", "lead", "title", "summary", "relation", "head_tiles", "sections",
                       "sources", "channels", "has_check"}
    assert ex["week"] == "2026-w41" and ex["has_check"] and ex["checks"] == ["sections[1]"]
    assert ex["sections"][0]["paragraphs"][0]["refs"] == ["s1"]
    assert ex["sources"][0]["title"] == TITLES[1]
    # 재실행: 새 run, 이전 행 보존, current_run_id 갱신
    ctx.llm.transport.responses = [response(r) for r in [plan(cids)] + [x for i in TITLES for x in
                                                                        (page(i, f"{TITLES[i]} 근거 문장 요약 정리했다"), verdict([]))]]
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
        response(x) for i in TITLES for x in (page(i, f"{TITLES[i]} 근거 문장 요약 정리했다"), verdict([]))]
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
    """시각 요소 위치의 이슈가 두 번 남으면 그 절의 visual을 none으로 비우고(단락은 남김) 토픽은 checked."""
    ctx, cids = week
    p1 = json.loads(page(1, "Argon이 DeepSWE에서 77.9% 기록했다"))
    p1["sections"][0]["visual"] = "bars"
    p1["sections"][0]["bars"] = {"title": "점수", "context": "같은 벤치 [it:1#q1]", "unit": "ms",
                                 "items": [{"label": lab, "value": v, "ref": "it:1#q1", "baseline": False, "emphasis": False}
                                           for lab, v in (("a", "77.9"), ("b", "77.9"), ("c", "12.3"))]}  # 12.3은 근거에 없는 값
    # 코드 반려만 이어지면 끝에서 검수자가 한 번 봄(리뷰 지적 2) → verdict 응답 하나
    responses = [plan(cids), json.dumps(p1, ensure_ascii=False), revision([]), verdict([])]
    for i in (2, 3, 4):
        responses += [page(i, f"{TITLES[i]} 근거 문장 요약 정리했다"), verdict([])]
    ctx.llm.transport.responses = [response(r) for r in responses]
    ctx.tracer = Tracer(ctx.db, "weekly", "S0")
    pipeline.run_weekly("2026-W41", ctx, from_step="select", embedder=HashEmbedder(), cfg=CFG)
    run_id = ctx.tracer.run_id
    t1 = ctx.db.conn.execute("SELECT status FROM topics WHERE run_id=? AND rank=1", (run_id,)).fetchone()
    final = json.loads(ctx.db.conn.execute("SELECT page_json FROM topic_pages WHERE run_id=? AND topic_id='w41-model-1' "
                                           "ORDER BY round DESC, id DESC", (run_id,)).fetchone()[0])
    assert t1["status"] == "checked" and final["sections"][0]["visual"] == "none" and final["sections"][0]["bars"] is None
    assert "77.9%" in final["sections"][0]["paragraphs"][0]["text"]
    checks_json = ctx.db.conn.execute("SELECT checks_json FROM topics WHERE run_id=? AND rank=1", (run_id,)).fetchone()[0]
    assert json.loads(checks_json) == ["sections[0]"]
    checkers = [r[0] for r in ctx.db.conn.execute("SELECT checker FROM verdicts WHERE run_id=? AND topic_id='w41-model-1' "
                                                  "ORDER BY id", (run_id,))]
    assert checkers == ["code", "code", "critic"]


def test_section_delete_resets_stale_check_tracking_for_shifted_sections(week):
    """006-A1-22: 절 하나가 delete로 빠지면 뒤 절들의 번호가 밀린다. 삭제된 절의 (위치,유형) 카운트가 새로 그
    번호를 받은 다른 절에 잘못 합쳐지면 한 번만 재등장해도 바로 check=true가 됨(오염). 번호가 바뀌면 카운트를
    리셋해 그 절도 자기 몫의 2번 기회를 받아야 한다(round 2가 아니라 round 3에서 check)."""
    ctx, cids = week
    long = "매우 긴 제목" * 15  # heading_chars_max(70자) 초과
    p1 = json.loads(page(1, "Argon이 DeepSWE에서 77.9% 기록했다", n_sections=4))
    p1["sections"][0]["heading"] = long + " A"  # 삭제될 절(content A)
    p1["sections"][1]["heading"] = long + " B"  # 살아남아 번호가 0으로 밀릴 절(content B)
    responses = [plan(cids), json.dumps(p1, ensure_ascii=False),
                 revision([{"issue_idx": 0, "loc": "sections[0]", "action": "delete", "value": None}]),
                 revision([]), verdict([])]
    for i in (2, 3, 4):
        responses += [page(i, f"{TITLES[i]} 근거 문장 요약 정리했다"), verdict([])]
    ctx.llm.transport.responses = [response(r) for r in responses]
    ctx.tracer = Tracer(ctx.db, "weekly", "S0")
    pipeline.run_weekly("2026-W41", ctx, from_step="select", embedder=HashEmbedder(), cfg=CFG)
    run_id = ctx.tracer.run_id
    t1 = ctx.db.conn.execute("SELECT status, final_round FROM topics WHERE run_id=? AND rank=1", (run_id,)).fetchone()
    assert tuple(t1) == ("checked", 3)  # round 2에서 바로 check가 되면(=오염) final_round는 2
    checks_json = json.loads(ctx.db.conn.execute("SELECT checks_json FROM topics WHERE run_id=? AND rank=1",
                                                  (run_id,)).fetchone()[0])
    assert checks_json == ["sections[0]"]  # content B가 밀려 받은 번호(삭제된 content A의 옛 번호와 같음)


def test_same_issue_twice_within_one_round_is_not_repeat(week):
    """같은 라운드에 같은 (위치, 유형) 이슈가 2건이어도 한 번으로 센다(리뷰 지적 1): 고친 뒤 통과하면 passed."""
    ctx, cids = week
    two = [{"loc": "sections[1].paragraphs[0]", "type": "unsupported", "evidence_id": "it:1#q1", "comment": c, "hint": "h"}
           for c in ("근거 없음 1", "근거 없음 2")]
    responses = [plan(cids), page(1, "Argon이 DeepSWE에서 77.9% 기록했다"), verdict(two),
                 revision([{"issue_idx": 0, "loc": "sections[1].paragraphs[0]", "action": "edit",
                            "value": {"text": "Gemini 4 Argon 근거 문장 요약 정리했다", "refs": ["it:1#q1"]}}]),
                 verdict([])]
    for i in (2, 3, 4):
        responses += [page(i, f"{TITLES[i]} 근거 문장 요약 정리했다"), verdict([])]
    ctx.llm.transport.responses = [response(r) for r in responses]
    ctx.tracer = Tracer(ctx.db, "weekly", "S0")
    pipeline.run_weekly("2026-W41", ctx, from_step="select", embedder=HashEmbedder(), cfg=CFG)
    t1 = ctx.db.conn.execute("SELECT status, final_round FROM topics WHERE run_id=? AND rank=1",
                             (ctx.tracer.run_id,)).fetchone()
    assert tuple(t1) == ("passed", 2)


def test_revision_with_wrong_sub_value_keeps_previous():
    from trendsit.brief.revision import apply_revision
    from trendsit.core.artifacts_brief import (
        BarGroup,
        Change,
        NumberItem,
        Para,
        Section,
        TopicPage,
        TopicPageRevision,
    )

    g = BarGroup(title="t", context="c", unit="%", items=[NumberItem(label=x, value="1", ref="r") for x in "abc"])
    p = TopicPage(head_tiles=[], sections=[Section(heading="h", paragraphs=[Para(text="문장 하나 둘 셋 넷", refs=["r"])],
                                                   visual="bars", bars=g)], summary="s다.", title="t", log="l")
    rev = TopicPageRevision(changed=[Change(issue_idx=0, loc="sections[0].bars.items[1]", action="edit",
                                            value=Para(text="x", refs=["r"]))], log="l")
    new, _, notes = apply_revision(p, rev, {"sections[0]"})
    assert new.sections[0].bars.items[1].value == "1" and notes
    whole = TopicPageRevision(changed=[Change(issue_idx=0, loc="sections[0]", action="delete", value=None)], log="l")
    assert apply_revision(p, whole, {"sections[0]"})[0].sections  # 전체 절 하나만 있으면 삭제는 받지 않음


def test_export_bars_events_og_and_checks(tmp_path):
    """A13: 시각 요소(막대·사건), og: 근거의 원본 URL, 토픽 수준 확인 필요가 사이트 데이터 칸으로."""
    ctx = make_ctx(tmp_path, FakeTransport([]), spec_cap=1.0)
    db = ctx.db.conn
    page_json = {"head_tiles": [], "sections": [
        {"heading": "정확도 비교", "paragraphs": [{"text": "정확도 B 93.5%로 가장 높음", "refs": ["og:5#q1"]}],
         "visual": "bars", "bars": {"title": "B 정확도 93.5%로 최고", "context": "같은 벤치 [og:5#q1]", "unit": "%",
                                    "items": [{"label": x, "value": v, "ref": "og:5#q1", "baseline": False,
                                              "emphasis": x == "B"} for x, v in (("A", "86.6"), ("B", "93.5"), ("C", "81.2"))]},
         "table": None, "tiles": [], "events": None, "slide": None, "slide_caption": "", "video_secs": [], "check": False},
        {"heading": "공개 흐름", "paragraphs": [{"text": "발표 일정 정리", "refs": ["it:5#q1"]}], "visual": "events",
         "bars": None, "table": None, "tiles": [],
         "events": {"title": "공개 흐름", "context": "발표 순서", "flow_is_point": False,
                    "items": [{"date": f"2026-10-0{d}", "text": f"사건 {d}", "ref": "it:5#q1", "topic_id": None}
                              for d in (5, 6, 7)]},
         "slide": None, "slide_caption": "", "video_secs": [], "check": False}],
        "summary": "요약이다.", "title": "제목", "log": "l", "attention": False}
    db.execute("INSERT INTO topics(run_id, topic_id, week, cluster_ids_json, rank, lead, relation_type, status, final_round,"
               " angle, checks_json) VALUES ('r','w41-x','2026-W41','[]',1,1,'new','checked',2,'a','[\"summary\"]')")
    db.execute("INSERT INTO topic_pages(run_id, topic_id, round, page_json) VALUES ('r','w41-x',2,?)", (json.dumps(page_json),))
    db.executemany("INSERT INTO topic_evidence(run_id, topic_id, evidence_id, member, field, idx) VALUES ('r','w41-x',?,?,?,?)",
                   [("og:5#q1", "it:5", "point", 0), ("it:5#q1", "it:5", "point", 1), ("og:5#q1", "it:5", "number", 0)])
    db.commit()
    srcs = {"og:5#q1": {"channel": "text", "site": "S", "title": "T", "date": "2026-10-06", "url": "https://s/5",
                        "origin": {"url": "https://origin/5", "kind": "blog"}},
            "it:5#q1": {"channel": "text", "site": "S", "title": "T", "date": "2026-10-06", "url": "https://s/5"}}
    ex = briefing.export_topic(ctx.db, "r", "w41-x", srcs)
    bars = ex["sections"][0]["visual"]
    events = ex["sections"][1]["visual"]
    assert bars["type"] == "bars" and bars["ref"] == "s1" and bars["items"][1]["emphasis"]
    assert events["type"] == "events" and [i["ref"] for i in events["items"]] == ["s1"] * 3
    assert ex["sources"] == [{"id": "s1", "channel": "text", "site": "S", "title": "T", "date": "2026-10-06",
                              "url": "https://s/5", "origin": "https://origin/5"}]
    assert ex["checks"] == ["summary"] and ex["has_check"]


def test_export_has_check_ignores_locs_without_a_chk_anchor(tmp_path):
    """006-A1-7: head_tiles[i] 같은 check 위치는 .chk가 안 그려지므로 has_check에 안 들어가야 함(C-9)."""
    ctx = make_ctx(tmp_path, FakeTransport([]), spec_cap=1.0)
    db = ctx.db.conn
    page_json = {"head_tiles": [{"value": "1", "label": "l", "note": "", "refs": ["it:5#q1"]}],
                 "sections": [{"heading": "h", "paragraphs": [{"text": "문장이다.", "refs": ["it:5#q1"]}], "visual": "none",
                              "bars": None, "table": None, "tiles": [], "events": None, "slide": None,
                              "slide_caption": "", "video_secs": [], "check": False}],
                 "summary": "요약이다.", "title": "제목", "log": "l", "attention": False}
    db.execute("INSERT INTO topics(run_id, topic_id, week, cluster_ids_json, rank, lead, relation_type, status, final_round,"
               " angle, checks_json) VALUES ('r','w41-x','2026-W41','[]',1,1,'new','checked',2,'a','[\"head_tiles[0]\"]')")
    db.execute("INSERT INTO topic_pages(run_id, topic_id, round, page_json) VALUES ('r','w41-x',2,?)", (json.dumps(page_json),))
    db.execute("INSERT INTO topic_evidence(run_id, topic_id, evidence_id, member, field, idx) VALUES ('r','w41-x','it:5#q1','it:5','point',0)")
    db.commit()
    srcs = {"it:5#q1": {"channel": "text", "site": "S", "title": "T", "date": "2026-10-06", "url": "https://s/5"}}
    ex = briefing.export_topic(ctx.db, "r", "w41-x", srcs)
    assert ex["checks"] == ["head_tiles[0]"] and not ex["has_check"]
    assert ex["sections"][0]["visual"] == {"type": "none"}  # 006-A1-28: null이 아니라 {"type":"none"}
    assert ex["sections"][0]["video_secs"] == []


def test_export_video_sources_timeline_video_id_and_slide_only_if_file_exists(tmp_path, monkeypatch):
    """006-A3-5(A2-review #5 재발): sources[].timeline·video_id, section.video_secs 라벨, slide.image는
    파일이 있을 때만 나온다(C-7 둘째 절)."""
    monkeypatch.setattr(briefing, "ROOT", tmp_path)
    ctx = make_ctx(tmp_path, FakeTransport([]), spec_cap=1.0)
    db = ctx.db.conn
    db.execute("INSERT INTO items(id, source_id, channel, external_id, url, title, day, week) VALUES "
               "(9,'yt','video','e9','https://youtu.be/VID1','영상 제목','2026-10-06','2026-W41')")
    db.execute("INSERT INTO videos(item_id, video_id) VALUES (9, 'VID1')")
    digest = {"timeline": [{"sec": 10, "label": "시작", "slide": False}, {"sec": 60, "label": "슬라이드 등장", "slide": True}]}
    db.execute("INSERT INTO video_digests(video_id, item_id, digest_json) VALUES ('VID1', 9, ?)", (json.dumps(digest),))
    page_json = {"head_tiles": [], "sections": [
        {"heading": "h1", "paragraphs": [{"text": "문장이다.", "refs": ["vd:9@10"]}], "visual": "none",
         "bars": None, "table": None, "tiles": [], "events": None, "slide": "sl:9@60", "slide_caption": "캡션",
         "video_secs": [10, 60], "check": False},
        {"heading": "h2", "paragraphs": [{"text": "문장이다.", "refs": ["vd:9@10"]}], "visual": "none",
         "bars": None, "table": None, "tiles": [], "events": None, "slide": None, "slide_caption": "",
         "video_secs": [], "check": False}],
        "summary": "요약이다.", "title": "제목", "log": "l", "attention": False}
    db.execute("INSERT INTO topics(run_id, topic_id, week, cluster_ids_json, rank, lead, relation_type, status, final_round,"
               " angle, checks_json) VALUES ('r','w41-v','2026-W41','[]',1,1,'new','checked',1,'a','[]')")
    db.execute("INSERT INTO topic_pages(run_id, topic_id, round, page_json) VALUES ('r','w41-v',1,?)", (json.dumps(page_json),))
    db.execute("INSERT INTO topic_evidence(run_id, topic_id, evidence_id, member, field, idx) VALUES "
               "('r','w41-v','vd:9@10','vd:VID1','point',0)")
    db.commit()
    srcs = {"vd:9@10": {"channel": "video", "site": "YouTube", "title": "영상 제목", "date": "2026-10-06",
                        "url": "https://youtu.be/VID1"}}

    ex1 = briefing.export_topic(ctx.db, "r", "w41-v", srcs)
    assert ex1["sources"][0]["video_id"] == "VID1"
    assert ex1["sources"][0]["timeline"] == [{"sec": 10, "label": "시작", "slide": False},
                                             {"sec": 60, "label": "슬라이드 등장", "slide": True}]
    assert ex1["sections"][0]["video_secs"] == [{"sec": 10, "label": "시작", "slide": False},
                                                {"sec": 60, "label": "슬라이드 등장", "slide": True}]
    # v1.3(5.14-2): 작성자가 비운 video_secs도 단락 근거 vd:9@10이 든 타임라인 구간(10초)으로 채운다
    assert ex1["sections"][1]["video_secs"] == [{"sec": 10, "label": "시작", "slide": False}]
    assert ex1["sections"][0]["slide"] is None  # 파일 없음 → null(C-7)

    (tmp_path / "data" / "slides").mkdir(parents=True, exist_ok=True)
    (tmp_path / "data" / "slides" / "VID1_60.jpg").write_bytes(b"x")
    ex2 = briefing.export_topic(ctx.db, "r", "w41-v", srcs)
    assert ex2["sections"][0]["slide"] == {"sec": 60, "title": "", "caption": "캡션", "image": "slides/VID1_60.jpg"}


def test_critic_empty_atoms_is_not_a_pass(week):
    """원자 사실 0개 통과는 대조를 건너뛴 판정: 한 번 다시 부르고, 또 비면 검수 실패(5.15-2: summary check=true+attention,
    실패 자체도 critic 판정으로 기록)."""
    ctx, cids = week
    empty = json.dumps({"atoms": [], "fact_support": {"total": 0, "supported": 0}, "issues": [], "status": "pass",
                        "log": "원자 사실 0개", "attention": False})
    responses = [plan(cids), page(1, "Argon이 DeepSWE에서 77.9% 기록했다"), empty, empty]
    for i in (2, 3, 4):
        responses += [page(i, f"{TITLES[i]} 근거 문장 요약 정리했다"), verdict([])]
    ctx.llm.transport.responses = [response(r) for r in responses]
    ctx.tracer = Tracer(ctx.db, "weekly", "S0")
    pipeline.run_weekly("2026-W41", ctx, from_step="select", embedder=HashEmbedder(), cfg=CFG)
    run_id = ctx.tracer.run_id
    checkers = [r[0] for r in ctx.db.conn.execute(
        "SELECT checker FROM verdicts WHERE run_id=? AND topic_id='w41-model-1' ORDER BY id", (run_id,))]
    assert checkers == ["code", "critic"]  # 빈 판정 두 번 → 검수 실패도 critic 판정으로 기록(5.15-2)
    checks_json = ctx.db.conn.execute(
        "SELECT checks_json FROM topics WHERE run_id=? AND topic_id='w41-model-1'", (run_id,)).fetchone()[0]
    assert "summary" in json.loads(checks_json)  # 검수 실패는 summary check=true(⚠)로, 통과가 아니다


def test_critic_llm_error_retries_once_then_flags_summary_check(week, monkeypatch):
    """5.15-2: 검수자 호출이 LLMError(429 등)면 30초 뒤 1회 재시도. 재시도도 실패하면 검수 없이 통과시키지
    않고 summary check=true(⚠)+attention '검수 실패'로 남긴다(5.13의 'critic 실패 → 코드 통과판'을 대체)."""
    from trendsit.brief import write as wr
    from trendsit.core.errors import LLMError

    ctx, cids = week
    responses = [plan(cids), page(1, "Argon이 DeepSWE에서 77.9% 기록했다")]
    for i in (2, 3, 4):
        responses += [page(i, f"{TITLES[i]} 근거 문장 요약 정리했다"), verdict([])]
    ctx.llm.transport.responses = [response(r) for r in responses]
    monkeypatch.setattr(wr.time, "sleep", lambda s: None)
    calls = stub_run_role(monkeypatch, wr, lambda n, role: LLMError("HTTP 429") if n in (2, 3) else None)
    ctx.tracer = Tracer(ctx.db, "weekly", "S0")
    pipeline.run_weekly("2026-W41", ctx, from_step="select", embedder=HashEmbedder(), cfg=CFG)
    run_id = ctx.tracer.run_id
    t1 = ctx.db.conn.execute("SELECT status, checks_json FROM topics WHERE run_id=? AND rank=1", (run_id,)).fetchone()
    assert t1["status"] == "checked" and "summary" in json.loads(t1["checks_json"])
    assert calls[:3] == ["writer", "critic", "critic"]  # 1회 실패 + 30초 뒤 재시도 1회(그래도 실패)


def test_critic_call_failure_is_not_counted_as_a_review_reject(week, monkeypatch):
    """A1-11/A3-10: 검수 호출 실패(LLMError)는 verdicts에 reject로 남지만 실제 반려가 아니므로 실행 요약
    critic_rejects에는 안 셈(fact_support 없음으로 구분)."""
    from trendsit.brief import write as wr
    from trendsit.core.errors import LLMError

    ctx, cids = week
    responses = [plan(cids), page(1, "Argon이 DeepSWE에서 77.9% 기록했다")]
    for i in (2, 3, 4):
        responses += [page(i, f"{TITLES[i]} 근거 문장 요약 정리했다"), verdict([])]
    ctx.llm.transport.responses = [response(r) for r in responses]
    monkeypatch.setattr(wr.time, "sleep", lambda s: None)
    stub_run_role(monkeypatch, wr, lambda n, role: LLMError("HTTP 429") if n in (2, 3) else None)
    ctx.tracer = Tracer(ctx.db, "weekly", "S0")
    summary = pipeline.run_weekly("2026-W41", ctx, from_step="select", embedder=HashEmbedder(), cfg=CFG)
    assert summary["review"]["critic_rejects"] == 0


def test_critic_unseen_pages_failure_flags_summary_check(week, monkeypatch):
    """A1-3/A2-2/A3-1: 매 라운드 코드가 반려해 critic을 한 번도 못 부른 토픽도, 사후(_critic_unseen_pages)
    검수가 재시도까지 실패하면 summary check=true(⚠)+attention '검수 실패'로 남긴다(전엔 아무 표시가 없었음)."""
    from trendsit.brief import write as wr
    from trendsit.core.errors import LLMError

    ctx, cids = week
    p1 = json.loads(page(1, "Argon이 DeepSWE에서 77.9% 기록했다"))
    p1["sections"][0]["heading"] = ""  # 필수 칸 비어 있음 → 코드가 매 라운드 반려(critic은 안 부름)
    responses = [plan(cids), json.dumps(p1, ensure_ascii=False), revision([])]
    for i in (2, 3, 4):
        responses += [page(i, f"{TITLES[i]} 근거 문장 요약 정리했다"), verdict([])]
    ctx.llm.transport.responses = [response(r) for r in responses]
    monkeypatch.setattr(wr.time, "sleep", lambda s: None)
    calls = stub_run_role(monkeypatch, wr, lambda n, role: LLMError("HTTP 429") if n in (3, 4) else None)
    ctx.tracer = Tracer(ctx.db, "weekly", "S0")
    pipeline.run_weekly("2026-W41", ctx, from_step="select", embedder=HashEmbedder(), cfg=CFG)
    run_id = ctx.tracer.run_id
    t1 = ctx.db.conn.execute("SELECT status, checks_json FROM topics WHERE run_id=? AND rank=1", (run_id,)).fetchone()
    assert calls[:4] == ["writer", "writer_revise", "critic", "critic"]  # critic은 _critic_unseen_pages에서만
    assert t1["status"] == "checked" and "summary" in json.loads(t1["checks_json"])


def test_f2_diagram_with_only_critic_issue_is_kept_with_check(week):
    """시각 요소는 코드가 확인한 형식·수치 오류일 때만 뺀다. 검수자 의미 지적만 두 번 남으면 두고 ⚠(반영 확인 리뷰 F2)."""
    ctx, cids = week
    p1 = json.loads(page(1, "Argon이 DeepSWE에서 77.9% 기록했다"))
    p1["sections"][0]["visual"] = "bars"
    p1["sections"][0]["bars"] = {"title": "Argon DeepSWE 77.9%", "context": "같은 벤치 [it:1#q1]", "unit": "%",
                                 "items": [{"label": lab, "value": "77.9", "ref": "it:1#q1", "baseline": False, "emphasis": False}
                                           for lab in ("a", "b", "c")]}
    over = [{"loc": "sections[0]", "type": "overuse", "evidence_id": "it:1#q1", "comment": "같은 값 셋", "hint": "h"}]
    responses = [plan(cids), json.dumps(p1, ensure_ascii=False), verdict(over),
                 revision([{"issue_idx": 0, "loc": "sections[0].heading", "action": "edit", "value": "Argon 점수"}]), verdict(over)]
    for i in (2, 3, 4):
        responses += [page(i, f"{TITLES[i]} 근거 문장 요약 정리했다"), verdict([])]
    ctx.llm.transport.responses = [response(r) for r in responses]
    ctx.tracer = Tracer(ctx.db, "weekly", "S0")
    pipeline.run_weekly("2026-W41", ctx, from_step="select", embedder=HashEmbedder(), cfg=CFG)
    run_id = ctx.tracer.run_id
    t = ctx.db.conn.execute("SELECT status, checks_json FROM topics WHERE run_id=? AND topic_id='w41-model-1'", (run_id,)).fetchone()
    final = json.loads(ctx.db.conn.execute("SELECT page_json FROM topic_pages WHERE run_id=? AND topic_id='w41-model-1' "
                                           "ORDER BY round DESC, id DESC", (run_id,)).fetchone()[0])
    assert t["status"] == "checked" and json.loads(t["checks_json"]) == ["sections[0]"]
    assert final["sections"][0]["visual"] == "bars" and final["sections"][0]["bars"] is not None


def test_f2c_check_pointing_to_removed_section_is_labeled():
    from trendsit.core.artifacts_brief import TopicPage

    p = TopicPage.model_validate(json.loads(page(1, "Argon이 DeepSWE에서 77.9% 기록했다")))
    assert briefing.visible_checks(["sections[9]", "summary"], p) == ["빠진 시각 요소(sections[9])", "summary"]


# ---------- 예산 초과 멈춤(F-1·F-7, C-6)과 실행 요약 상태(F-27) ----------
def stub_run_role(monkeypatch, module, fail):
    """module.run_role을 감싸 n번째 호출(1부터)에 fail(n, role)이 돌려준 예외를 던진다. 나머지는 진짜 호출."""
    real, calls = module.run_role, []

    def fake(role, inp, ctx):
        calls.append(role.name)
        if (exc := fail(len(calls), role)) is not None:
            raise exc
        return real(role, inp, ctx)

    monkeypatch.setattr(module, "run_role", fake)
    return calls


def run_cmd(ctx, monkeypatch, tmp_path, from_step="select", cfg=None) -> int:
    """cmd_weekly를 그대로(종료 코드, runs.status까지). 임베더·출력 폴더는 모의/임시."""
    import argparse

    from trendsit.cli_brief import cmd_weekly

    ctx.tracer = Tracer(ctx.db, "weekly", "S0")
    monkeypatch.setattr("trendsit.core.context.open_ctx", lambda *a, **k: ctx)
    monkeypatch.setattr("trendsit.filter.embed.make_embedder", lambda *a, **k: HashEmbedder())
    monkeypatch.setattr(report, "LABELS", tmp_path / "labels")
    if cfg is not None:
        orig = config.load
        monkeypatch.setattr(config, "load", lambda name, *a, **k: cfg if name == "brief.yaml" else orig(name, *a, **k))
    args = argparse.Namespace(week="2026-W41", from_step=from_step, step=None, topic=None, no_cache=True, spec=None)
    return cmd_weekly(args)


def assert_stopped(ctx, tmp_path, capsys, before, needle):
    """C-6: 현재판 포인터·상태 그대로, run은 stopped, 요약 상태 stopped, 종료 코드는 호출한 쪽이 1로 확인, 읽기본은 쓰지 않음."""
    run_id = ctx.tracer.run_id
    db = ctx.db.conn
    assert tuple(db.execute("SELECT status, current_run_id FROM weeks").fetchone()) == before
    assert db.execute("SELECT status FROM runs WHERE id=?", (run_id,)).fetchone()[0] == "stopped"
    assert json.loads(db.execute("SELECT summary_json FROM runs WHERE id=?", (run_id,)).fetchone()[0])["status"] == "stopped"
    assert needle in capsys.readouterr().err
    assert not (tmp_path / "out" / "briefing_2026-W41.md").exists()


def test_budget_stop_write(week, monkeypatch, tmp_path, capsys):
    from trendsit.brief import write as wr
    from trendsit.core.budget import BudgetExceeded

    ctx, cids = week
    before = tuple(ctx.db.conn.execute("SELECT status, current_run_id FROM weeks").fetchone())
    ctx.llm.transport.responses = [response(r) for r in [plan(cids), page(1, "Argon이 DeepSWE에서 77.9% 기록했다"), verdict([])]]
    calls = stub_run_role(monkeypatch, wr, lambda n, role: BudgetExceeded("상한") if n == 3 else None)
    assert run_cmd(ctx, monkeypatch, tmp_path) == 1
    assert_stopped(ctx, tmp_path, capsys, before, "BudgetExceeded: 상한")
    st = {r["rank"]: r["status"] for r in ctx.db.conn.execute("SELECT rank, status FROM topics WHERE run_id=?", (ctx.tracer.run_id,))}
    assert st == {1: "passed", 2: "failed", 3: "selected", 4: "selected"}  # 3·4번째는 시작하지 않음
    assert calls == ["writer", "critic", "writer"]


@pytest.mark.parametrize("exc", ["BudgetExceeded", "PriceUnknown"])
def test_budget_stop_select(week, monkeypatch, tmp_path, capsys, exc):
    from trendsit.brief import select as sel
    from trendsit.core import budget

    ctx, _ = week
    before = tuple(ctx.db.conn.execute("SELECT status, current_run_id FROM weeks").fetchone())
    calls = stub_run_role(monkeypatch, sel, lambda n, role: getattr(budget, exc)("상한"))
    assert run_cmd(ctx, monkeypatch, tmp_path) == 1
    assert_stopped(ctx, tmp_path, capsys, before, f"{exc}: 상한")
    assert calls == ["editor_select"] and ctx.llm.transport.calls == 0
    assert ctx.db.conn.execute("SELECT COUNT(*) FROM topics WHERE run_id=?", (ctx.tracer.run_id,)).fetchone()[0] == 0


def test_budget_stop_cluster(week, monkeypatch, tmp_path, capsys):
    """decide 두 번째 호출에서 초과: 이미 받은 첫 판정은 저장, 이후 쌍은 판정 없음, 선별은 시작하지 않음."""
    from trendsit.brief import weekly
    from trendsit.core.budget import BudgetExceeded

    ctx, _ = week
    before = tuple(ctx.db.conn.execute("SELECT status, current_run_id FROM weeks").fetchone())
    tuned = CFG.model_copy(deep=True)
    tuned.cluster.thresholds.auto, tuned.cluster.thresholds.border = 2.0, -1.0  # 같은 채널 쌍이 모두 decide로
    answer = json.dumps({"reason": "다른 글", "same": False, "confidence": 0.9, "log": "다름", "attention": False})
    ctx.llm.transport.responses = [response(answer)]
    calls = stub_run_role(monkeypatch, weekly, lambda n, role: BudgetExceeded("상한") if n == 2 else None)
    assert run_cmd(ctx, monkeypatch, tmp_path, from_step="cluster", cfg=tuned) == 1
    assert_stopped(ctx, tmp_path, capsys, before, "BudgetExceeded: 상한")
    run_id = ctx.tracer.run_id
    assert calls == ["decide", "decide"] and ctx.llm.transport.calls == 1
    assert ctx.db.conn.execute("SELECT COUNT(*) FROM cluster_pairs WHERE run_id=? AND decided=1", (run_id,)).fetchone()[0] == 1
    assert ctx.db.conn.execute("SELECT COUNT(*) FROM topics WHERE run_id=?", (run_id,)).fetchone()[0] == 0
    assert not (tmp_path / "labels").exists()  # 멈춘 run은 라벨 시트를 쓰지 않음


def _status_of(ctx, cids, monkeypatch, fail) -> dict:
    from trendsit.brief import write as wr

    ctx.llm.transport.responses = [response(r) for r in [plan(cids)] + [x for i in TITLES for x in
                                                                        (page(i, f"{TITLES[i]} 근거 문장 요약 정리했다"), verdict([]))]]
    stub_run_role(monkeypatch, wr, fail)
    ctx.tracer = Tracer(ctx.db, "weekly", "S0")
    summary = pipeline.run_weekly("2026-W41", ctx, from_step="select", embedder=HashEmbedder(), cfg=CFG)
    assert summary == pipeline.compute_summary(ctx.db, ctx.tracer.run_id)  # 표에서 다시 계산해도 같음
    return summary


def test_summary_status_failed(week, monkeypatch):
    from trendsit.core.role import RoleFailed

    ctx, cids = week
    before = tuple(ctx.db.conn.execute("SELECT status, current_run_id FROM weeks").fetchone())
    summary = _status_of(ctx, cids, monkeypatch, lambda n, role: RoleFailed("출력 검증 실패"))
    assert summary["status"] == "failed" and summary["write"] == {"topics": 4, "failed": 4}
    assert tuple(ctx.db.conn.execute("SELECT status, current_run_id FROM weeks").fetchone()) == before  # 현재판 그대로


def test_summary_status_partial(week, monkeypatch):
    from trendsit.core.role import RoleFailed

    ctx, cids = week
    summary = _status_of(ctx, cids, monkeypatch, lambda n, role: RoleFailed("출력 검증 실패") if n == 7 else None)
    assert summary["status"] == "partial" and summary["write"] == {"topics": 4, "failed": 1}
    # v1.2 5.13: 예산 중단이 아니고 성공 토픽 ≥1이면 weeks는 done(runs.status·summary는 partial 그대로, publish가 막히지 않게)
    assert ctx.db.conn.execute("SELECT status FROM weeks").fetchone()[0] == "done"


def test_partial_week_still_publishes_without_failed_topic(week, monkeypatch):
    """v1.2 5.13: 토픽 1개 failed인 run도 weeks가 done이라 ops.publish가 그대로 성공(0)하고, 사이트에 그 토픽은 없음."""
    from trendsit import ops
    from trendsit.core.role import RoleFailed

    ctx, cids = week
    summary = _status_of(ctx, cids, monkeypatch, lambda n, role: RoleFailed("출력 검증 실패") if n == 7 else None)
    assert summary["status"] == "partial"
    assert ctx.db.conn.execute("SELECT status FROM weeks").fetchone()[0] == "done"
    run_id = ctx.tracer.run_id
    failed_id = ctx.db.conn.execute("SELECT topic_id FROM topics WHERE run_id=? AND status='failed'", (run_id,)).fetchone()[0]
    assert ops.publish(ctx.db, "2026-W41", lambda cmd: (0, "", "")) == 0
    assert ctx.db.conn.execute("SELECT status FROM weeks").fetchone()[0] == "published"
    site = json.loads((ctx.db.path.parent / "site.json").read_text())
    assert failed_id not in {t["id"] for t in site["topics"]}
    assert len(site["topics"]) == 3


def test_summary_status_stopped(week, monkeypatch):
    from trendsit.core.budget import BudgetExceeded

    ctx, cids = week
    before = tuple(ctx.db.conn.execute("SELECT status, current_run_id FROM weeks").fetchone())
    summary = _status_of(ctx, cids, monkeypatch, lambda n, role: BudgetExceeded("상한") if n == 3 else None)
    assert summary["status"] == "stopped" and ctx.stopped == "BudgetExceeded: 상한"
    assert tuple(ctx.db.conn.execute("SELECT status, current_run_id FROM weeks").fetchone()) == before


# ---------- S9 FR-4·FR-5(015 흡수): weekly 작성 단계 뒤 LLMError failed 토픽 재시도 ----------
def test_weekly_retries_llm_error_failed_topics_then_succeeds(week, monkeypatch):
    """AC-6: 토픽 4개 중 2개(1,2)가 첫 시도 LLMError. 1라운드에 1개(1) 성공·1개(2) 계속 LLMError, 2라운드에 성공.
    run done, write.failed 0, 라운드마다 code 단계 한 줄(429 재시도 n회차) + attention, runs 행 수 변화 0."""
    from trendsit.brief import write as wr
    from trendsit.core.errors import LLMError

    ctx, cids = week
    responses = [plan(cids)]
    for i in (3, 4, 1, 2):
        responses += [page(i, f"{TITLES[i]} 근거 문장 요약 정리했다"), verdict([])]
    ctx.llm.transport.responses = [response(r) for r in responses]
    waits_seen: list[int] = []
    monkeypatch.setattr(pipeline.time, "sleep", lambda s: waits_seen.append(s))
    calls = stub_run_role(monkeypatch, wr, lambda n, role: LLMError("HTTP 429") if n in (1, 2, 9) else None)
    ctx.tracer = Tracer(ctx.db, "weekly", "S0")
    runs_before = ctx.db.conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
    summary = pipeline.run_weekly("2026-W41", ctx, from_step="select", embedder=HashEmbedder(), cfg=CFG)
    run_id = ctx.tracer.run_id
    runs_after = ctx.db.conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
    assert summary["status"] == "done" and summary["write"]["failed"] == 0
    assert runs_after == runs_before  # C-6: 새 run 행을 만들지 않음
    assert waits_seen == [300, 600]  # §4: 라운드 n의 대기 = wait_sec * n(5분, 10분), 순서대로
    rounds = ctx.db.conn.execute(
        "SELECT text, attention FROM steps WHERE run_id=? AND role='weekly' AND text LIKE '429 재시도%' ORDER BY id",
        (run_id,)).fetchall()
    assert [tuple(r) for r in rounds] == [("429 재시도 1회차: 토픽 2개", 1), ("429 재시도 2회차: 토픽 1개", 0)]
    assert calls == ["writer", "writer", "writer", "critic", "writer", "critic",
                     "writer", "critic", "writer", "writer", "critic"]  # C-4: 재시도 2라운드 안


def test_weekly_retry_export_does_not_merge_topics_under_dash(week, monkeypatch):
    """FR-5·FR-7(AC-13): 재시도 호출도 writer code 경계 행을 남기고, 실행 기록 export(export_runs.py)에서
    재시도한 토픽은 topic_id '-'(중단·진행 중) 블록으로 새지 않고, 같은 topic_id의 여러 시도가 블록 하나로
    합쳐진다(C-9): 시도 사이에 chain ["code", "재시도"] 한 칸, tokens·cost는 합, status·rank·title은 최종."""
    from trendsit import export_runs as er
    from trendsit.brief import write as wr
    from trendsit.core.errors import LLMError

    ctx, cids = week
    responses = [plan(cids)]
    for i in (3, 4, 1, 2):
        responses += [page(i, f"{TITLES[i]} 근거 문장 요약 정리했다"), verdict([])]
    ctx.llm.transport.responses = [response(r) for r in responses]
    monkeypatch.setattr(pipeline.time, "sleep", lambda s: None)
    stub_run_role(monkeypatch, wr, lambda n, role: LLMError("HTTP 429") if n in (1, 2, 9) else None)
    ctx.tracer = Tracer(ctx.db, "weekly", "S0")
    summary = pipeline.run_weekly("2026-W41", ctx, from_step="select", embedder=HashEmbedder(), cfg=CFG)
    run_id = ctx.tracer.run_id
    r = dict(ctx.db.conn.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone())
    d = er._weekly(ctx.db, r, summary, current=None)
    _, steps = er._weekly_detail(ctx.db, d, {})
    wr_step = next(s for s in steps if s["name"] == "writer ⇄ critic")
    topics = wr_step["detail"][0]["items"]
    ids = [t["topic_id"] for t in topics]
    assert "-" not in ids  # 재시도 호출이 경계 없는 '-' 블록으로 새지 않음
    distinct_ids = {t["topic_id"] for t in topics}
    assert len(distinct_ids) == len(ids) == 4  # C-9: topic_id마다 블록 수 == 1
    assert wr_step["line"].split(" / ")[0] == f"topics {len(distinct_ids)}"  # C-9: topics N == 서로 다른 topic_id 수

    final_topics = {t["topic_id"]: dict(t) for t in ctx.db.conn.execute(
        "SELECT topic_id, status, rank, title FROM topics WHERE run_id=?", (run_id,))}
    retried = next(t for t in topics if t["topic_id"] == "w41-model-2")  # 초기 실패 + 1라운드 LLMError + 2라운드 성공
    assert sum(c == ["code", "재시도"] for c in retried["chain"]) == 2  # 시도 세 번 → 경계 2개
    assert retried["chain"][-1] != ["code", "재시도"]  # 경계는 시도 사이, 체인 끝이 아님
    bi = [i for i, c in enumerate(retried["chain"]) if c == ["code", "재시도"]]
    assert all(retried["chain"][i - 1] == ["code", "failed"] for i in bi)  # 011-F01: 앞 시도 끝 칸은 failed
    assert any(c[0] in ("writer", "critic") for c in retried["chain"])  # 재시도의 실제 호출을 담는다
    ft = final_topics["w41-model-2"]
    assert (retried["status"], retried["rank"], retried["title"]) == (ft["status"], ft["rank"], ft["title"])  # 최종값

    not_retried = next(t for t in topics if t["topic_id"] == "w41-model-3")
    assert ["code", "재시도"] not in not_retried["chain"]  # 재시도 안 한 토픽은 경계 칸이 생기지 않음


def test_merge_retry_attempts_sums_tokens_cost_and_keeps_final_fields():
    """C-9·AC-13 단위 테스트: 같은 topic_id의 시도 2개(실패 + 재시도 성공)를 블록 하나로.
    chain은 시도 순서대로 이어 붙이고 사이에 ["code", "재시도"] 한 칸, tokens·cost는 합, status·rank·title은 최종(2번째)."""
    from trendsit import export_runs as er

    first = {"rank": 1, "title": "구 제목", "topic_id": "w41-x", "status": "failed", "final_round": 1,
            "tokens_in": 100, "tokens_out": 10, "cost_usd": 0.001,
            "chain": [["writer", "실패"], ["code", "failed"]], "issues": [["loc1", "t", "c", "-"]]}
    second = {"rank": 1, "title": "최종 제목", "topic_id": "w41-x", "status": "passed", "final_round": 1,
             "tokens_in": 200, "tokens_out": 20, "cost_usd": 0.002,
             "chain": [["writer", "재작성"], ["code", "passed"]], "issues": []}
    other = {"rank": 2, "title": "다른 토픽", "topic_id": "w41-y", "status": "passed", "final_round": 1,
            "tokens_in": 5, "tokens_out": 5, "cost_usd": 0.0005, "chain": [["code", "passed"]], "issues": []}
    merged = er._merge_retry_attempts([first, second, other])
    assert [m["topic_id"] for m in merged] == ["w41-x", "w41-y"]  # 블록 수 == distinct topic_id 수
    m = merged[0]
    assert m["chain"] == [["writer", "실패"], ["code", "failed"], ["code", "재시도"], ["writer", "재작성"], ["code", "passed"]]
    assert (m["tokens_in"], m["tokens_out"], m["cost_usd"]) == (300, 30, 0.003)
    assert (m["status"], m["rank"], m["title"]) == ("passed", 1, "최종 제목")  # 최종(마지막 시도) 값
    assert m["issues"] == [["loc1", "t", "c", "-"]]
    assert merged[1] == other  # 재시도 없는 토픽은 그대로


def test_role_failed_topics_are_not_retried(week, monkeypatch):
    """C-3·AC-7: 잘림·스키마 실패(RoleFailed)로 failed인 토픽은 LLMError가 아니므로 재시도 대상이 아니다(라운드 0)."""
    from trendsit.core.role import RoleFailed

    ctx, cids = week
    summary = _status_of(ctx, cids, monkeypatch, lambda n, role: RoleFailed("출력 검증 실패") if n == 7 else None)
    run_id = ctx.tracer.run_id
    assert summary["status"] == "partial" and summary["write"] == {"topics": 4, "failed": 1}
    n_rounds = ctx.db.conn.execute("SELECT COUNT(*) FROM steps WHERE run_id=? AND text LIKE '429 재시도%'",
                                   (run_id,)).fetchone()[0]
    assert n_rounds == 0


def test_budget_stopped_skips_retry_rounds(week, monkeypatch):
    """C-5·AC-8: 첫 작성에서 LLMError failed 토픽(topic 1)이 있어도, 그 뒤 BudgetExceeded로
    run이 stopped면 재시도 라운드를 하지 않는다. 가드(`if not ctx.stopped ...`)를 지우면 재시도 대상
    (topic 1)이 있으므로 이 테스트가 실패해야 한다."""
    from trendsit.core.budget import BudgetExceeded
    from trendsit.core.errors import LLMError

    ctx, cids = week
    summary = _status_of(ctx, cids, monkeypatch,
                         lambda n, role: LLMError("HTTP 429") if n == 1 else (BudgetExceeded("상한") if n == 2 else None))
    run_id = ctx.tracer.run_id
    assert summary["status"] == "stopped" and ctx.stopped == "BudgetExceeded: 상한"
    n_rounds = ctx.db.conn.execute("SELECT COUNT(*) FROM steps WHERE run_id=? AND text LIKE '429 재시도%'",
                                   (run_id,)).fetchone()[0]
    assert n_rounds == 0


def test_budget_stopped_during_retry_round_skips_remaining_rounds(week, monkeypatch):
    """§6: 재시도 1라운드 중(토픽 1의 재시도 호출) 예산 중단이 나면 그 라운드에서 바로 멈추고
    남은 라운드(2회차)를 하지 않는다. 라운드 텍스트의 '토픽 k개'는 실제로 다시 쓴 수(0, 중단된 토픽은
    저장되지 않아 0)여야 한다."""
    from trendsit.brief import write as wr
    from trendsit.core.budget import BudgetExceeded
    from trendsit.core.errors import LLMError

    ctx, cids = week
    responses = [plan(cids)]
    for i in (3, 4):
        responses += [page(i, f"{TITLES[i]} 근거 문장 요약 정리했다"), verdict([])]
    ctx.llm.transport.responses = [response(r) for r in responses]
    monkeypatch.setattr(pipeline.time, "sleep", lambda s: None)
    stub_run_role(monkeypatch, wr, lambda n, role: LLMError("HTTP 429") if n in (1, 2) else
                  (BudgetExceeded("상한") if n == 7 else None))
    ctx.tracer = Tracer(ctx.db, "weekly", "S0")
    summary = pipeline.run_weekly("2026-W41", ctx, from_step="select", embedder=HashEmbedder(), cfg=CFG)
    run_id = ctx.tracer.run_id
    assert summary["status"] == "stopped" and ctx.stopped == "BudgetExceeded: 상한"
    rounds = ctx.db.conn.execute(
        "SELECT text, attention FROM steps WHERE run_id=? AND role='weekly' AND text LIKE '429 재시도%' ORDER BY id",
        (run_id,)).fetchall()
    assert [tuple(r) for r in rounds] == [("429 재시도 1회차: 토픽 0개", 1)]  # 2회차 없음, retried=0(실제로 못 씀)


def test_editor_select_fallback_reason_tells_call_failure_from_validation(week, monkeypatch):
    """대체 계획 이유: 마지막 시도가 예외면 호출 실패, 검증이 계속 실패하면 검증 실패(F-17)."""
    from trendsit.brief import select as sel
    from trendsit.core.errors import LLMError

    ctx, cids = week
    stub_run_role(monkeypatch, sel, lambda n, role: LLMError("제공사 오류"))
    ctx.tracer = Tracer(ctx.db, "weekly", "S0")
    ctx.llm.transport.responses = [response(x) for i in TITLES for x in (page(i, f"{TITLES[i]} 근거 문장 요약 정리했다"), verdict([]))]
    pipeline.run_weekly("2026-W41", ctx, from_step="select", embedder=HashEmbedder(), cfg=CFG)
    log = json.loads(ctx.db.conn.execute("SELECT plan_json FROM briefing_plans WHERE run_id=?", (ctx.tracer.run_id,)).fetchone()[0])["log"]
    assert "호출 실패" in log and "검증 실패" not in log


# ---------- A6: 잘림(D-42) → no_visuals 재시도 ----------
def test_writer_truncation_retries_with_no_visuals(week, monkeypatch):
    from trendsit.brief import write as wr
    from trendsit.core.role import RoleFailed

    ctx, cids = week
    responses = [plan(cids), page(1, "Argon이 DeepSWE에서 77.9% 기록했다"), verdict([])]
    for i in (2, 3, 4):
        responses += [page(i, f"{TITLES[i]} 근거 문장 요약 정리했다"), verdict([])]
    ctx.llm.transport.responses = [response(r) for r in responses]
    calls = stub_run_role(monkeypatch, wr, lambda n, role: RoleFailed("writer: 스키마 검증 실패 (출력 잘림(max_tokens 4500 도달): x)")
                          if n == 1 else None)
    ctx.tracer = Tracer(ctx.db, "weekly", "S0")
    pipeline.run_weekly("2026-W41", ctx, from_step="select", embedder=HashEmbedder(), cfg=CFG)
    run_id = ctx.tracer.run_id
    t1 = ctx.db.conn.execute("SELECT status FROM topics WHERE run_id=? AND rank=1", (run_id,)).fetchone()
    assert t1["status"] in ("passed", "checked")  # 잘림 뒤 no_visuals 재시도로 회복(C-5: 토픽당 호출 ≤4)
    assert calls[0] == "writer" and calls[1] == "writer"  # 1회 실패(잘림) + 1회 성공(no_visuals), 토픽 1


def test_writer_truncation_retry_survives_a_real_code_step_in_between(week):
    """006-C1-1: 실제 weekly 경로 재현. topic1이 끝나면 pipeline._log_topic이 role='writer' kind='code'인
    step을 남긴다(step id는 전역 autoincrement). 그 바로 다음 토픽(topic2)의 writer 호출이 진짜로(스텁 없이,
    run_role·record_llm을 그대로 거쳐) 잘리면, 전역 step id 차이로 세면 code step 하나가 끼어 used=3이 되어
    no_visuals 재시도가 걸러진다(이 테스트가 재현하는 버그). writer LLM step 수로 세면 used=2로 정확해 재시도가
    돌고 topic2가 회복한다."""
    ctx, cids = week
    trunc = response("{", tokens=(100, 4500))  # max_tokens 4500 도달 + 스키마 파싱 실패 → "출력 잘림"
    responses = [
        response(plan(cids)),
        response(page(1, "Argon이 DeepSWE에서 77.9% 기록했다")), response(verdict([])),  # topic1: 정상 완료 → _log_topic code step
        trunc, trunc,  # topic2: 1차 호출이 run_role 내부에서 2번 다 잘려 RoleFailed("출력 잘림…")
        response(page(2, f"{TITLES[2]} 근거 문장 요약 정리했다")), response(verdict([])),  # topic2: no_visuals 재시도로 회복
        response(page(3, f"{TITLES[3]} 근거 문장 요약 정리했다")), response(verdict([])),
        response(page(4, f"{TITLES[4]} 근거 문장 요약 정리했다")), response(verdict([])),
    ]
    ctx.llm.transport.responses = responses
    ctx.tracer = Tracer(ctx.db, "weekly", "S0")
    pipeline.run_weekly("2026-W41", ctx, from_step="select", embedder=HashEmbedder(), cfg=CFG)
    run_id = ctx.tracer.run_id
    db = ctx.db.conn
    code_step = db.execute("SELECT kind, role FROM steps WHERE run_id=? AND kind='code' AND role='writer' ORDER BY id LIMIT 1",
                           (run_id,)).fetchone()
    assert code_step is not None  # topic1의 _log_topic code step이 실제로 끼었음을 확인(재현 전제)
    t2 = db.execute("SELECT status FROM topics WHERE run_id=? AND rank=2", (run_id,)).fetchone()
    assert t2["status"] in ("passed", "checked")  # no_visuals 재시도가 걸러지지 않고 돌아 회복해야 함
    n2 = db.execute("SELECT detail FROM steps WHERE run_id=? AND kind='code' AND role='writer' AND "
                   "json_extract(detail,'$.topic_id')=?", (run_id, "w41-model-2")).fetchone()
    assert json.loads(n2["detail"])["no_visuals"] is True  # detail.no_visuals로 재시도가 실제로 일어났음을 확인


def test_writer_skips_no_visuals_retry_if_first_call_already_used_3_attempts(week, monkeypatch):
    """006-A2-7: role.py 내부에서 스키마 실패+잘림이 섞여 한 번의 run_role 호출이 LLM을 3번 썼으면(role.py는
    건드리지 않을 파일이라 write.py가 호출 수를 세어) no_visuals 재시도를 하지 않는다(합쳐도 C-5 ≤4 넘지 않음)."""
    from trendsit.brief import write as wr
    from trendsit.core.role import RoleFailed

    ctx, cids = week
    responses = [plan(cids)]
    for i in (2, 3, 4):
        responses += [page(i, f"{TITLES[i]} 근거 문장 요약 정리했다"), verdict([])]
    ctx.llm.transport.responses = [response(r) for r in responses]
    real, calls = wr.run_role, []

    def fake(role, inp, ctx_):
        calls.append(role.name)
        if len(calls) == 1:
            for _ in range(3):  # 혼합 실패(스키마 2회 + 잘림)로 실제 LLM 호출이 3번 일어난 것처럼(role.py가 매 시도 기록)
                ctx_.last_step_id = ctx_.tracer.step(kind="llm", role="writer", text="시도")
            raise RoleFailed("writer: 스키마 검증 실패 (출력 잘림(max_tokens 4500 도달): x)")
        return real(role, inp, ctx_)

    monkeypatch.setattr(wr, "run_role", fake)
    ctx.tracer = Tracer(ctx.db, "weekly", "S0")
    pipeline.run_weekly("2026-W41", ctx, from_step="select", embedder=HashEmbedder(), cfg=CFG)
    run_id = ctx.tracer.run_id
    t1 = ctx.db.conn.execute("SELECT status FROM topics WHERE run_id=? AND rank=1", (run_id,)).fetchone()
    assert t1["status"] == "failed"  # no_visuals 재시도를 안 했으므로 그대로 실패
    assert calls.count("writer") == 4  # 토픽마다 1회(토픽 1은 재시도 없이 실패, 나머지 3개는 정상 1회씩. 재시도였으면 5)


def test_writer_total_failure_logs_one_step_not_two(week, monkeypatch):
    """006-A1-24: 작성 실패 토픽도 steps(writer,code) 행이 하나만(counts.written 이중 계산 방지)."""
    from trendsit.brief import write as wr
    from trendsit.core.role import RoleFailed

    ctx, cids = week
    responses = [plan(cids)]
    for i in (2, 3, 4):
        responses += [page(i, f"{TITLES[i]} 근거 문장 요약 정리했다"), verdict([])]
    ctx.llm.transport.responses = [response(r) for r in responses]
    stub_run_role(monkeypatch, wr, lambda n, role: RoleFailed("writer: 스키마 검증 실패 (사유)") if n == 1 else None)
    ctx.tracer = Tracer(ctx.db, "weekly", "S0")
    pipeline.run_weekly("2026-W41", ctx, from_step="select", embedder=HashEmbedder(), cfg=CFG)
    run_id = ctx.tracer.run_id
    t1 = ctx.db.conn.execute("SELECT status FROM topics WHERE run_id=? AND rank=1", (run_id,)).fetchone()
    assert t1["status"] == "failed"
    n = ctx.db.conn.execute("SELECT COUNT(*) FROM steps WHERE run_id=? AND role='writer' AND kind='code'",
                            (run_id,)).fetchone()[0]
    assert n == 4  # 토픽 4개, 실패해도 _log_topic 한 번씩만(두 번 세지 않음)


def test_briefing_md_untitled_source(week, monkeypatch):
    """제목이 NULL인 근거가 있어도 읽기본이 멈추지 않고 '?'로 적는다(F-33)."""
    ctx, cids = week
    summary = _status_of(ctx, cids, monkeypatch, lambda n, role: None)
    assert summary["status"] == "done"
    ctx.db.conn.execute("UPDATE items SET title=NULL WHERE id=1")
    text = briefing.write_briefing_md(ctx.db, "2026-W41").read_text()
    assert "`it:1#q1` ?" in text


def test_briefing_md_includes_section_tiles_and_table_refs(week):
    """007-A1-12: 읽기본에 절 안 타일(visual=tiles)과 표 refs도 나온다(런 뒤 ④ 훑어보기·관문 B 라벨 작업에 필요)."""
    ctx, _cids = week
    sec = {"heading": "절", "paragraphs": [{"text": "문장이다.", "refs": ["it:1#s1"]}], "visual": "tiles",
          "bars": None, "table": None, "tiles": [{"value": "77.9%", "label": "지표", "note": "", "refs": ["it:1#s1"]}],
          "events": None, "slide": None, "slide_caption": "", "video_secs": [], "check": False}
    sec2 = {**sec, "heading": "표 절", "visual": "table", "tiles": [],
           "table": {"title": "표", "note": "", "columns": ["a", "b"], "rows": [["1", "2"], ["3", "4"]], "refs": ["it:1#s1", "it:1#q1"]}}
    page_json = {"head_tiles": [], "sections": [sec, sec2], "summary": "s", "title": "t", "log": "l", "attention": False}
    ctx.db.conn.execute("INSERT INTO topic_pages(run_id, topic_id, round, page_json) VALUES ('r','t1',1,?)",
                        (json.dumps(page_json, ensure_ascii=False),))
    ctx.db.conn.commit()
    t = {"topic_id": "t1", "rank": 1, "lead": False, "status": "passed", "final_round": 1, "angle": "a",
        "relation_topic_id": None, "checks_json": "[]"}
    lines = briefing._topic_md_lines(ctx.db, "r", t, {})
    text = "\n".join(lines)
    assert "타일: 77.9% — 지표" in text
    assert "근거: it:1#s1, it:1#q1" in text


def test_scrub_empties_topic_isolates_failure_not_whole_export(week):
    """006-A2-3: refs가 전부 pack 밖이라 수정으로도 못 고치면 그 토픽만 failed(export C-2 전체 중단 방지), 나머지는 계속."""
    sections = [{"heading": f"{TITLES[1]} {n}번째 절", "paragraphs": [{"text": f"{TITLES[1]} 관련 사실 {n}이다.",
                "refs": ["it:999#q1"]}], "visual": "none", "bars": None, "table": None, "tiles": [], "events": None,
                "slide": None, "slide_caption": "", "video_secs": [], "check": False} for n in range(1, 4)]
    bad_page = json.dumps({"head_tiles": [], "sections": sections, "summary": "모델이 공개됐다. 쟁점이 있다.",
                           "title": TITLES[1], "log": "l", "attention": False}, ensure_ascii=False)
    ctx, cids = week
    responses = [plan(cids), bad_page, revision([]), verdict([])]
    for i in (2, 3, 4):
        responses += [page(i, f"{TITLES[i]} 근거 문장 요약 정리했다"), verdict([])]
    ctx.llm.transport.responses = [response(r) for r in responses]
    ctx.tracer = Tracer(ctx.db, "weekly", "S0")
    summary = pipeline.run_weekly("2026-W41", ctx, from_step="select", embedder=HashEmbedder(), cfg=CFG)
    run_id = ctx.tracer.run_id
    t1 = ctx.db.conn.execute("SELECT status FROM topics WHERE run_id=? AND rank=1", (run_id,)).fetchone()
    assert t1["status"] == "failed"
    assert summary["status"] == "partial" and summary["write"]["failed"] == 1
    site = export.build(ctx.db, with_week="2026-W41")
    assert all(t["id"] != "w41-model-1" for t in site["topics"])  # 실패 토픽은 export에 없음(격리)
    assert any(t["title"] == TITLES[2] for t in site["topics"])  # 다른 토픽은 그대로 발행


