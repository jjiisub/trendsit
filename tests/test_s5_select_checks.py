"""S5 관문 A8(선별 검증)·A9(코드 검사, 모의 출력)."""

from __future__ import annotations

import pytest

from trendsit.brief import checks
from trendsit.brief import select as sel
from trendsit.brief.evidence import EvidenceItem, Member, WeekEvidence
from trendsit.core import config
from trendsit.core.artifacts_brief import (
    BriefingPlan,
    Decision,
    EventGroup,
    EventItem,
    NumberGroup,
    NumberItem,
    PlannedTopic,
    Point,
    Relation,
    Split,
    TopicPage,
)

CFG = config.load("brief.yaml")


def cand(cid: int, members: list[str], past: list[dict] | None = None, score: float = 3000) -> sel.Candidate:
    return sel.Candidate(cid, f"후보 {cid}", members, {"text": len(members)}, score, past or [], len(members))


CANDS = [cand(1, ["it:1", "it:2"]), cand(2, ["it:3"], past=[{"topic_id": "w40-x", "title": "X", "similarity": 0.8}]),
         cand(3, ["it:4"]), cand(4, ["it:5"]), cand(5, ["vd:A"])]


def topic(cids, rank, lead=False, rel="new", tid=None) -> PlannedTopic:
    return PlannedTopic(cluster_ids=cids, rank=rank, lead=lead, relation=Relation(type=rel, topic_id=tid),
                        relation_reason="r", angle="a", slug_hint="s")


def plan(topics, decisions=None, splits=None) -> BriefingPlan:
    chosen = {c for t in topics for c in t.cluster_ids}
    decisions = decisions or [Decision(cluster_id=c.cluster_id, reason="글 2", action="select" if c.cluster_id in chosen
                                       else "drop", drop_reason=None if c.cluster_id in chosen else "thin") for c in CANDS]
    return BriefingPlan(decisions=decisions, splits=splits or [], topics=topics, featured_repos=[], log="l")


def good() -> BriefingPlan:
    return plan([topic([1], 1, True), topic([2], 2, rel="follow_up", tid="w40-x"), topic([3], 3), topic([4], 4)])


def test_valid_plan_passes():
    assert sel.validate(good(), CANDS, CFG) == []


@pytest.mark.parametrize("p,needle", [
    (plan([topic([1], 1, True), topic([2], 2, True), topic([3], 3), topic([4], 4)]), "lead가 2개"),
    (plan([topic([1], 1, True), topic([2], 2)]), "topics 개수 2개"),
    (plan([topic([1], 1, True), topic([2], 3), topic([3], 4), topic([4], 5)]), "rank"),
    (plan([topic([1, 9], 1, True), topic([2], 2), topic([3], 3), topic([4], 4)]), "cluster_id 9"),
    (plan([topic([1], 1, True), topic([1, 2], 2), topic([3], 3), topic([4], 4)]), "토픽 2개에"),
    (plan([topic([1], 1, True), topic([3], 2, rel="follow_up", tid="w40-x"), topic([2], 3), topic([4], 4)]),
     "과거 대조 후보에 없음"),
    (plan([topic([1], 1, True), topic([2], 2), topic([3], 3), topic([4], 4)],
          splits=[Split(cluster_id=1, groups=[["it:1"], ["it:9"]], reason="r")]), "그 후보의 항목이 아님"),
    (plan([topic([1], 1, True), topic([2], 2), topic([3], 3), topic([4], 4)],
          decisions=[Decision(cluster_id=1, reason="r", action="select", drop_reason=None)]), "decisions에 빠진 후보"),
])
def test_validation_rejects(p, needle):
    errs = sel.validate(p, CANDS, CFG)
    assert any(needle in e for e in errs), errs


def test_max_topics_is_cap_not_target():
    many = [cand(i, [f"it:{i}"]) for i in range(1, 15)]
    p = BriefingPlan(decisions=[Decision(cluster_id=c.cluster_id, reason="r", action="select", drop_reason=None) for c in many],
                     splits=[], topics=[topic([c.cluster_id], i, i == 1) for i, c in enumerate(many[:11], 1)],
                     featured_repos=[], log="l")
    assert any("topics 개수 11개" in e for e in sel.validate(p, many, CFG))


def test_input_order_is_cluster_id_not_score(tmp_path):
    from trendsit.core.db import DB

    db = DB(tmp_path / "t.db")
    ms = {k: Member(k, "text", k, "", "", "high", [], [], {}, [EvidenceItem(k + "#q1", k, "text", "quote", "x", {})])
          for k in ("it:1", "it:2", "it:3")}
    for cid, (member, score) in enumerate([("it:1", 1000), ("it:2", 3000), ("it:3", 2000)], start=1):
        db.conn.execute("INSERT INTO clusters(id, run_id, week, label, channels_json, n_items, score, body_json) "
                        "VALUES (?,?,?,?,?,?,?,?)", (cid, "r", "2026-W41", member, '{"text": 1}', 1, score, "{}"))
        db.conn.execute("INSERT INTO cluster_items(cluster_id, member, channel, joined_by) VALUES (?,?,?,?)",
                        (cid, member, "text", "seed"))
    ev = WeekEvidence("2026-W41", ms, {})
    cands = sel.load_candidates(db, "r", ev, limit=2)
    assert [c.cluster_id for c in cands] == [2, 3]  # 점수 상위 2개(2, 3)를 cluster_id 순서로
    inp = sel.build_input(cands, ev, db, CFG)
    assert [d.id for d in inp.candidates] == ["c2", "c3"]


def test_reason_values_checked_against_input():
    inp = sel.EditorSelectInput(candidates=[sel.candidate_doc(cand(1, ["it:1"]), {"it:1": Member(
        "it:1", "text", "제목", "줄", "", "high", [], [], {})})], recent_topics=[], keyword_trend=[], repo_cards=[],
        limits=sel.SelectLimits(min_topics=4, max_topics=10))
    p = plan([topic([1], 1, True)], decisions=[Decision(cluster_id=1, reason="글 7건, OpenAI 공식 글", action="select",
                                                        drop_reason=None)])
    out = sel.reason_mismatches(p, inp, ["OpenAI", "GeekNews"])
    assert any("숫자 7" in x for x in out) and any("OpenAI" in x for x in out)


def test_slug_and_relation_label(tmp_path):
    from trendsit.core.db import DB

    db = DB(tmp_path / "t.db")
    db.conn.execute("INSERT INTO weeks(week, start_day, end_day, status, current_run_id) VALUES "
                    "('2026-W40','2026-09-28','2026-10-04','done','r0')")
    db.conn.execute("INSERT INTO topics(run_id, topic_id, week, cluster_ids_json, rank, lead, status, title) VALUES "
                    "('r0','w40-x','2026-W40','[1]',1,1,'passed','지난 제목')")
    assert sel.slugify("Jev Local!") == "jev-local"
    applied = sel.apply(good(), CANDS, "2026-W42", db)
    assert applied[0].topic_id == "w42-s" and applied[1].topic_id == "w42-s-2"
    assert applied[1].relation_label == "9월 5주차 '지난 제목' 토픽의 후속"


# ---------- 코드 검사(A9) ----------
def pack() -> dict[str, list[EvidenceItem]]:
    src = {"site": "OpenAI", "title": "t", "date": "2026-10-06"}
    return {"it:1#q1": [EvidenceItem("it:1#q1", "it:1", "text", "quote", "Price is $2 per million input tokens, 15% cheaper.", src)],
            "it:1#q2": [EvidenceItem("it:1#q2", "it:1", "text", "quote", "Accuracy: A 86.6%, B 93.5%, C 81.2%", src)],
            "vd:5@30": [EvidenceItem("vd:5@30", "vd:X", "video", "slide_fact", "p50 latency", src, value="150ms", sec=30)]}


def page(**over) -> TopicPage:
    base = dict(points=[Point(text="입력 100만 토큰당 $2로 이전보다 15% 저렴함", refs=["it:1#q1"]),
                        Point(text="정확도 B 93.5%로 세 모델 중 가장 높음", refs=["it:1#q2"]),
                        Point(text="발표 슬라이드 기준 p50 지연 150ms", refs=["vd:5@30"])],
                numbers=[], events=[], contributions=[], concepts=[],
                overview="OpenAI가 새 가격을 발표했다. 정확도 비교도 함께 나왔다.", summary="OpenAI가 가격을 15% 내렸다.",
                title="새 가격과 정확도", log="l", attention=False)
    return TopicPage(**(base | over))


def test_clean_page_passes():
    r = checks.run_checks(page(), pack(), 2, CFG, {})
    assert r.passed, [i.comment for i in r.issues]


def test_number_mismatch_with_hint_and_no_unit_conversion():
    p = page(points=[Point(text="입력 토큰당 $0.000002, 이전보다 1.5% 저렴함", refs=["it:1#q1"]),
                     *page().points[1:]])
    issues = checks.run_checks(p, pack(), 2, CFG, {}).issues
    msgs = [i.comment for i in issues if i.type == "number_mismatch"]
    assert any("points[0]의 '1.5'" in m and "it:1#q1" in m and "15" in m for m in msgs)  # 위치·근거·가까운 값
    assert any("0.000002" in m for m in msgs)  # 토큰당 ↔ 100만 토큰당 환산은 같은 값으로 보지 않음


def test_anchor_and_diagram_caps():
    g = NumberGroup(anchor=9, group="g", title="B가 가장 높음", context="같은 벤치 [it:1#q2]", unit="%",
                    items=[NumberItem(label="A", value="86.6%", ref="it:1#q2"), NumberItem(label="B", value="93.5%", ref="it:1#q2"),
                           NumberItem(label="C", value="81.2%", ref="it:1#q2")])
    ev = EventGroup(anchor=2, title="t", context="c", items=[EventItem(date="10/6", text="x", ref="it:1#q1", topic_id=None)])
    issues = checks.run_checks(page(numbers=[g, g.model_copy(update={"anchor": 2}), g.model_copy(update={"anchor": 3})],
                                    events=[ev]), pack(), 2, CFG, {}).issues
    text = " ".join(i.comment for i in issues)
    assert "anchor 9" in text and "numbers 3그룹" in text and "YYYY-MM-DD" in text and "도식 둘 이상" in text


def test_forbidden_words_reject_but_highlights_are_autofixed():
    p = page(summary="==OpenAI==가 ==가격==을 내렸다.", overview="최근 AI 업계에서는 가격 경쟁이 핵심이다. 정확도도 나왔어요.")
    r = checks.run_checks(p, pack(), 2, CFG, {})
    assert r.page.summary.count("==") == 2  # 형광 2개 → 1개(뒤쪽 제거), 반려 아님
    assert any(f["rule"].startswith("형광") for f in r.autofix)
    text = " ".join(i.comment for i in r.issues)
    assert "해요체" in text and "핵심이다" in text and "일반론 시작" in text
    assert not any("summary" == i.loc for i in r.issues)


def test_alias_is_replaced_by_canonical():
    p = page(summary="오픈AI가 가격을 15% 내렸다.")
    r = checks.run_checks(p, pack(), 2, CFG, {"오픈AI": "OpenAI"})
    assert r.page.summary.startswith("OpenAI") and r.passed


def test_unknown_ref_and_single_source_contributions():
    from trendsit.core.artifacts_brief import Contribution

    p = page(points=[Point(text="근거 목록에 없는 id를 단 문장입니다 정말로", refs=["it:9#q1"]), *page().points[1:]],
             contributions=[Contribution(channel="text", text="x", refs=["it:1#q1"])])
    issues = checks.run_checks(p, pack(), 1, CFG, {}).issues
    assert any(i.type == "wrong_ref" and "it:9#q1" in i.comment for i in issues)
    assert any("contributions" in i.comment for i in issues)


def test_diagram_warnings():
    w = checks.run_checks(page(), pack(), 2, CFG, {}).warnings
    assert any("누락 의심" in x for x in w) is False  # % 값 1개(수치 3개는 quote 안이라 kind=number 아님)
    two = NumberGroup(anchor=2, group="g", title="t", context="c [it:1#q2]", unit="%",
                      items=[NumberItem(label="A", value="86.6%", ref="it:1#q2"), NumberItem(label="B", value="93.5%", ref="it:1#q2")])
    w2 = checks.run_checks(page(numbers=[two]), pack(), 2, CFG, {}).warnings
    assert any("남발 의심" in x for x in w2)
