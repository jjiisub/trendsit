"""S5 관문 A8(선별 검증). 코드 검사(v1 A9)는 S6-1 tests/test_s6_1_write.py로 옮김(D-31, 5.11)."""

from __future__ import annotations

import pytest

from trendsit.brief import select as sel
from trendsit.brief.evidence import EvidenceItem, Member, WeekEvidence
from trendsit.core import config
from trendsit.core.artifacts_brief import (
    BriefingPlan,
    Decision,
    PlannedTopic,
    Relation,
    Split,
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
    res = sel.SelectResult(good(), "model", applied, CANDS)
    sel.save(db, res, "r1", "2026-W42")
    assert db.conn.execute("SELECT relation_label FROM topics WHERE run_id='r1' AND topic_id=?",
                           (applied[1].topic_id,)).fetchone()[0] == "9월 5주차 '지난 제목' 토픽의 후속"


def test_selected_but_not_in_topics_is_rejected():
    p = good()
    p = p.model_copy(update={"decisions": [d.model_copy(update={"action": "select", "drop_reason": None}) for d in p.decisions]})
    assert any("select인데 topics에 없는" in e for e in sel.validate(p, CANDS, CFG))


def test_reconcile_decisions_to_topics():
    p = good()
    bad = p.model_copy(update={"decisions": [d.model_copy(update={"action": "drop", "drop_reason": "thin"}) if d.cluster_id == 1
                                             else d.model_copy(update={"action": "select", "drop_reason": None})
                                             for d in p.decisions]})
    assert sel.validate(bad, CANDS, CFG)  # 원래 출력은 어긋남(기록)
    fixed, notes = sel.reconcile(bad)
    assert sel.validate(fixed, CANDS, CFG) == [] and len(notes) == 2
    assert next(d for d in fixed.decisions if d.cluster_id == 5).drop_reason == "other"

