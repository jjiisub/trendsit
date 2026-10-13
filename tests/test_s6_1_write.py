"""S6-1 S-2: TopicPage v2 스키마·코드 검사·수정 합치기·근거 조립(5.2~5.6). A3~A7."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from trendsit.brief import checks, fulltext, revision, slides
from trendsit.brief.evidence import EvidenceItem, pack_index
from trendsit.brief.write import refs_of
from trendsit.core import config
from trendsit.core.artifacts_brief import (
    BarGroup,
    Change,
    EventGroup,
    EventItem,
    NumberItem,
    Para,
    Section,
    Table,
    Tile,
    TopicPage,
    TopicPageRevision,
)
from trendsit.core.db import DB

CFG = config.load("brief.yaml")


def para(text="문장이다.", refs=("it:1#s1",)):
    return Para(text=text, refs=list(refs))


def section(**over):
    base = dict(heading="절 제목", paragraphs=[para()], visual="none", bars=None, table=None, tiles=[], events=None,
               slide=None, slide_caption="", video_secs=[], check=False)
    base.update(over)
    return Section(**base)


def page(**over):
    base = dict(head_tiles=[], sections=[section()], summary="사건이다. 쟁점이다.", title="제목", log="l", attention=False)
    base.update(over)
    return TopicPage(**base)


def pack(**extra):
    src = {"site": "GeekNews", "title": "t", "date": "2026-10-06"}
    base = {"it:1#s1": [EvidenceItem("it:1#s1", "it:1", "text", "sentence", "원문 문장이다. 비율은 20%다.", src)]}
    base.update(extra)
    return base


def three_sections(**over_first):
    return [section(**over_first), section(heading="둘째 절"), section(heading="셋째 절")]


# ---------- A3: 스키마 ----------
def test_topic_page_v2_schema_matches_spec_example():
    p = page(head_tiles=[Tile(value="90%", label="가격 인하율", note="기준", refs=["it:1#s1"])],
             sections=[section(heading="제목", paragraphs=[para()], visual="table",
                               table=Table(title="표", note="", columns=["a", "b"], rows=[["1", "2"], ["3", "4"]],
                                          refs=["it:1#s1"]))])
    assert p.sections[0].visual == "table" and p.sections[0].table.columns == ["a", "b"]
    with pytest.raises(ValidationError):
        Section(heading="x", paragraphs=[para()], visual="none", extra_field=1)  # extra=forbid


def test_table_rows_accepts_numbers_and_normalizes_to_text():
    """006-A2-11: NumberItem처럼 표 셀도 숫자를 받아 문자열로 바꾼다(모델이 숫자를 쓰려다 잘리는 것 방지)."""
    tbl = Table(title="t", note="", columns=["a", "b"], rows=[["구분", 1], [2.5, "원"]], refs=["it:1#s1"])
    assert tbl.rows == [["구분", "1"], ["2.5", "원"]]


def test_enforce_clears_writer_check_true():
    p = page(sections=[section(check=True)])
    out = p.enforce(None, None)
    assert out.sections[0].check is False
    assert out.enforced and out.enforced[0]["owned"] is True


# ---------- A5: 코드 검사 ----------
def test_sentences_does_not_split_on_comparison_particle_da():
    """006-A3-2: "보다 " 같은 문장 중간 "다"+공백에서 쪼개지 않는다(fulltext.sentences와 같은 경계)."""
    text = "GPT-6는 이전 모델보다 빠르다. 비용은 Haiku보다 낮다."
    assert checks.sentences(text) == ["GPT-6는 이전 모델보다 빠르다.", "비용은 Haiku보다 낮다."]


def test_check_passes_good_page():
    p = page(sections=three_sections())
    assert checks.check(p, pack(), 1, CFG) == []


def test_check_accepts_comparison_sentence_within_limit():
    """006-A3-2 회귀: 비교문 2개짜리 단락이 문장 분리 버그로 4문장으로 세여 거짓 반려되지 않는다."""
    text = "GPT-6는 이전 모델보다 빠르다. 비용은 Haiku보다 낮다."
    p = page(summary=text, sections=three_sections(paragraphs=[para(text=text)]))
    issues = checks.check(p, pack(), 1, CFG)
    assert not any("문장" in i.comment and i.loc in ("summary", "sections[0]") for i in issues)


def test_check_rejects_wrong_ref():
    p = page(sections=[section(paragraphs=[para(refs=["it:99#s1"])])])
    issues = checks.check(p, pack(), 1, CFG)
    assert any(i.type == "wrong_ref" for i in issues)


def test_check_rejects_summary_only_id_as_ref():
    """006-C1-11: pack에 있어도 kind가 summary·context뿐인 id(예: Document id와 겹치는 카드 요약)는 refs로
    쓸 수 없다 — 줄 머리에 안 붙어 작성자에게 참고용으로만 보이고 검수자 원문 대조에서도 빠진다."""
    summary_pack = pack(**{"it:1": [EvidenceItem("it:1", "it:1", "text", "summary", "카드 요약이다.", {"site": "x"})]})
    p = page(sections=[section(paragraphs=[para(refs=["it:1"])])])
    issues = checks.check(p, summary_pack, 1, CFG)
    assert any(i.type == "wrong_ref" and "요약" in i.comment for i in issues)


def test_check_rejects_number_mismatch():
    p = page(sections=three_sections(paragraphs=[para(text="비율은 90%다.")]))
    issues = checks.check(p, pack(), 1, CFG)
    assert any(i.type == "number_mismatch" for i in issues)


def test_check_rejects_number_mismatch_with_currency_ms_and_k_suffix():
    """006-C1-2: 5.5 ① 전체 — $·ms·K 표기가 타일 value·표 셀·단락·heading에서도 대조된다(근거는 $30·120ms·8K)."""
    unit_pack = pack(**{"it:1#s2": [EvidenceItem("it:1#s2", "it:1", "text", "sentence", "월 $30, 120ms, 8K 컨텍스트다.", {"site": "x"})]})
    p = page(head_tiles=[Tile(value="$20", label="가격", refs=["it:1#s2"])],
             sections=three_sections(paragraphs=[para(text="지연은 300ms다.", refs=["it:1#s2"])],
                                     heading="16K 컨텍스트 지원",
                                     visual="table", table=Table(title="t", note="", columns=["구분", "값"],
                                                                 rows=[["가격", "$45"], ["기간", "월간"]], refs=["it:1#s2"])))
    issues = checks.check(p, unit_pack, 1, CFG)
    locs = {i.loc for i in issues if i.type == "number_mismatch"}
    assert "head_tiles[0]" in locs  # $20 ≠ $30
    assert "sections[0].paragraphs[0]" in locs  # 300ms ≠ 120ms
    assert "sections[0].heading" in locs  # 16K ≠ 8K
    assert "sections[0].table.rows[0]" in locs  # $45 ≠ $30


def test_check_accepts_matching_currency_ms_and_k_suffix():
    """근거와 같은 $·ms·K 값은 반려되지 않는다(위 반려 테스트의 짝)."""
    unit_pack = pack(**{"it:1#s2": [EvidenceItem("it:1#s2", "it:1", "text", "sentence", "월 $30, 120ms, 8K 컨텍스트다.", {"site": "x"})]})
    p = page(head_tiles=[Tile(value="$30", label="가격", refs=["it:1#s2"])],
             sections=three_sections(paragraphs=[para(text="지연은 120ms다.", refs=["it:1#s2"])],
                                     heading="8K 컨텍스트 지원",
                                     visual="table", table=Table(title="t", note="", columns=["구분", "값"],
                                                                 rows=[["가격", "$30"], ["기간", "월간"]], refs=["it:1#s2"])))
    assert [i for i in checks.check(p, unit_pack, 1, CFG) if i.type == "number_mismatch"] == []


def test_check_accepts_korean_compound_magnitude_number_as_false_positive():
    """006-C1-2 회귀: "16만2000개"의 "2000"은 "16만"과 합쳐진 값(162000)이지 독립된 수가 아니다. 단락·근거가
    같은 표기를 그대로 쓰면 반려되지 않아야 한다(실데이터 w41-claude-haiku-5-5 사례로 재현)."""
    unit_pack = pack(**{"it:1#s2": [EvidenceItem("it:1#s2", "it:1", "text", "sentence",
                                                 "작업당 약 16만2000개의 출력 토큰을 소모했다.", {"site": "x"})]})
    p = page(sections=three_sections(paragraphs=[para(text="작업당 약 16만2000개의 토큰을 썼다.", refs=["it:1#s2"])]))
    assert [i for i in checks.check(p, unit_pack, 1, CFG) if i.type == "number_mismatch"] == []


def test_check_rejects_visual_bars_without_bars_field():
    p = page(sections=three_sections(visual="bars", bars=None))
    issues = checks.check(p, pack(), 1, CFG)
    assert any(i.type == "format" and "visual" in i.comment for i in issues)


def test_run_checks_rejects_initial_draft_with_empty_visual_instead_of_autofixing():
    """007-A1-3/A2-1: 5.3 "revise 적용 뒤"만 visual=none 자동 수정 대상. 초안(after_revise=False, 라운드 1)은
    5.3 이상 예시대로 반려돼야 한다(조용히 none으로 넘어가면 안 됨)."""
    p = page(sections=three_sections(visual="bars", bars=None))
    cr = checks.run_checks(p, pack(), 1, CFG, {}, [], set())
    assert any(i.type == "format" and "visual" in i.comment for i in cr.issues)
    assert cr.page.sections[0].visual == "bars"  # autofix로 none이 되지 않음


def test_run_checks_autofixes_empty_visual_after_revise():
    p = page(sections=three_sections(visual="bars", bars=None))
    cr = checks.run_checks(p, pack(), 1, CFG, {}, [], set(), after_revise=True)
    assert cr.page.sections[0].visual == "none"
    assert cr.issues == []


def test_check_accepts_valid_bars_group():
    bars_pack = pack(**{"it:1#s2": [EvidenceItem("it:1#s2", "it:1", "text", "sentence", "A는 10%, B는 20%.", {"site": "x"})]})
    p = page(sections=three_sections(visual="bars", paragraphs=[para(refs=["it:1#s2"])],
                                     bars=BarGroup(title="A vs B", context="비교", unit="%",
                                                  items=[NumberItem(label="A", value="10%", ref="it:1#s2"),
                                                         NumberItem(label="B", value="20%", ref="it:1#s2")])))
    assert checks.check(p, bars_pack, 1, CFG) == []


def test_autofix_fixes_slide_candidates_and_video_secs():
    p = page(sections=[section(slide="sl:1@999", video_secs=[1, 2, 3])])
    fixed, fixes = checks.autofix(p, CFG, {}, ["sl:1@50"], {1, 2}, 10)
    assert fixed.sections[0].slide is None and fixed.sections[0].video_secs == [1, 2]
    assert any("slide_candidates" in f["rule"] for f in fixes)


def test_autofix_cuts_sections_from_the_end():
    p = page(sections=[section(heading="a"), section(heading="b"), section(heading="c")])
    fixed, fixes = checks.autofix(p, CFG, {}, [], set(), 2)
    assert [s.heading for s in fixed.sections] == ["a", "b"]
    assert any("sections" in f["loc"] for f in fixes)


def test_page_refs_covers_head_tiles_and_section_kinds():
    p = page(head_tiles=[Tile(value="1", label="l", refs=["it:1#s1"])],
             sections=[section(visual="events", paragraphs=[para()],
                               events=EventGroup(title="t", context="c", items=[
                                   EventItem(date="2026-10-01", text="a", ref="it:1#s1"),
                                   EventItem(date="2026-10-02", text="b", ref=None, topic_id="w40-x")]))])
    slots = checks.page_refs(p)
    locs = {s.loc for s in slots}
    assert "head_tiles[0]" in locs and "sections[0].events.items[0]" in locs
    assert any(s.loc == "sections[0].events.items[1]" and s.refs == [] for s in slots)


def test_refs_of_order_point_before_number():
    p = page(sections=[section(visual="bars", paragraphs=[para(refs=["it:1#s1"])],
                               bars=BarGroup(title="t", context="", unit="%",
                                            items=[NumberItem(label="a", value="1%", ref="it:1#s2"),
                                                   NumberItem(label="b", value="2%", ref="it:1#s3")]))])
    assert refs_of(p) == ["it:1#s1", "it:1#s2", "it:1#s3"]


# ---------- A6: 라운드·수정 ----------
def test_apply_revision_only_touches_flagged_loc():
    prev = page(sections=[section(heading="원래"), section(heading="둘째")])
    rev = TopicPageRevision(changed=[
        Change(issue_idx=0, loc="sections[0].heading", action="edit", value="고침"),
        Change(issue_idx=0, loc="sections[1].heading", action="edit", value="몰래 바꿈"),
    ], log="l")
    new, reverts, notes = revision.apply_revision(prev, rev, {"sections[0]"})
    assert new.sections[0].heading == "고침" and new.sections[1].heading == "둘째"
    assert reverts == 1 and "지적 안 된" in notes[0]


def test_apply_revision_section_add_and_delete():
    prev = page(sections=[section(heading="a"), section(heading="b")])
    rev = TopicPageRevision(changed=[Change(issue_idx=0, loc="sections[1]", action="delete", value=None)], log="l")
    new, reverts, notes = revision.apply_revision(prev, rev, {"sections[1]"})
    assert len(new.sections) == 1 and reverts == 0, notes


def test_apply_revision_rejects_deleting_all_sections():
    prev = page(sections=[section(heading="only")])
    rev = TopicPageRevision(changed=[Change(issue_idx=0, loc="sections[0]", action="delete", value=None)], log="l")
    new, _reverts, notes = revision.apply_revision(prev, rev, {"sections[0]"})
    assert len(new.sections) == 1 and any("전체 삭제는 받지 않음" in n for n in notes)


def test_apply_revision_bars_item_edit():
    prev = page(sections=[section(visual="bars", bars=BarGroup(title="t", context="", unit="%",
                                                                items=[NumberItem(label="a", value="1%", ref="it:1#s1"),
                                                                      NumberItem(label="b", value="2%", ref="it:1#s1")]))])
    rev = TopicPageRevision(changed=[Change(issue_idx=0, loc="sections[0].bars.items[0]", action="edit",
                                            value=NumberItem(label="a", value="10%", ref="it:1#s1"))], log="l")
    new, reverts, notes = revision.apply_revision(prev, rev, {"sections[0]"})
    assert new.sections[0].bars.items[0].value == "10%" and reverts == 0, notes


def test_normalize_loc_fixes_one_based_index():
    p = page(sections=[section(heading="a")])
    assert revision.normalize_loc(p, "sections[1]") == "sections[0]"


def test_apply_revision_add_does_not_leak_into_unflagged_section():
    prev = page(sections=three_sections())  # 3절
    rev = TopicPageRevision(changed=[
        Change(issue_idx=0, loc="sections[2].paragraphs[1]", action="add", value=para(text="몰래 끼움."))], log="l")
    new, reverts, notes = revision.apply_revision(prev, rev, {"sections[0]"})
    assert len(new.sections[2].paragraphs) == 1 and reverts == 1, notes


def test_apply_revision_allows_adding_a_brand_new_section():
    prev = page(sections=three_sections())  # 0,1,2
    rev = TopicPageRevision(changed=[
        Change(issue_idx=0, loc="sections[3]", action="add", value=section(heading="새 절"))], log="l")
    new, reverts, notes = revision.apply_revision(prev, rev, {"sections[0]"})
    assert len(new.sections) == 4 and new.sections[3].heading == "새 절" and reverts == 0, notes


def test_change_value_accepts_numeric_table_row_and_normalizes_to_text():
    """R2-04: Change.value의 table.rows[k] 수정도 writer처럼 숫자 셀을 받는다(문자열만이면 구조화 출력이 막혀
    revision 전체가 버려짐, 007-C1-8)."""
    ch = Change(issue_idx=0, loc="sections[0].table.rows[0]", action="edit", value=["Haiku", 1620])
    assert ch.value == ["Haiku", "1620"]


def test_apply_revision_rejects_deleting_all_sections_via_multiple_deletes():
    prev = page(sections=three_sections())
    rev = TopicPageRevision(changed=[
        Change(issue_idx=0, loc="sections[0]", action="delete", value=None),
        Change(issue_idx=0, loc="sections[1]", action="delete", value=None),
        Change(issue_idx=0, loc="sections[2]", action="delete", value=None),
    ], log="l")
    new, _reverts, notes = revision.apply_revision(prev, rev, {"sections[0]", "sections[1]", "sections[2]"})
    assert len(new.sections) >= 1
    assert any("전체 삭제는 받지 않음" in n for n in notes)


def test_apply_revision_slide_caption_and_table_rows_delete():
    tbl = Table(title="t", note="", columns=["a", "b"], rows=[["1", "2"], ["3", "4"], ["5", "6"]], refs=["it:1#s1"])
    prev = page(sections=[section(visual="table", table=tbl, slide="sl:1@10", slide_caption="옛 캡션")])
    rev = TopicPageRevision(changed=[
        Change(issue_idx=0, loc="sections[0].slide_caption", action="edit", value="새 캡션"),
        Change(issue_idx=0, loc="sections[0].table.rows[1]", action="delete", value=None),
    ], log="l")
    new, reverts, notes = revision.apply_revision(prev, rev, {"sections[0]"})
    assert new.sections[0].slide_caption == "새 캡션" and len(new.sections[0].table.rows) == 2 and reverts == 0, notes


def test_apply_revision_discards_only_the_change_that_breaks_schema():
    """007-A1-5: 한 절뿐인 단락을 delete하면(min_length=1 위반) 그 변경만 되돌리고, 같은 revision의 다른
    절·칸 수정은 그대로 적용된다(전체 revision을 버리던 버그 수정)."""
    prev = page(sections=[section(heading="원래", paragraphs=[para(text="하나뿐")]), section(heading="둘째")])
    rev = TopicPageRevision(changed=[
        Change(issue_idx=0, loc="sections[0].paragraphs[0]", action="delete", value=None),
        Change(issue_idx=0, loc="sections[1].heading", action="edit", value="고침"),
    ], log="l")
    new, reverts, notes = revision.apply_revision(prev, rev, {"sections[0]", "sections[1]"})
    assert len(new.sections[0].paragraphs) == 1  # 단락 delete는 스키마를 깨 되돌려짐
    assert new.sections[1].heading == "고침"  # 다른 절 수정은 살아남음
    assert reverts == 0 and any("스키마가 깨져" in n for n in notes)


def test_apply_revision_section_add_inserts_at_index_not_appended():
    """007-A1-6/A2-27: sections[1] add는 절 순서를 지키려고 그 위치에 끼워 넣는다(맨 뒤에 붙이면 안 됨)."""
    prev = page(sections=three_sections())  # 0,1,2
    rev = TopicPageRevision(changed=[
        Change(issue_idx=0, loc="sections[1]", action="add", value=section(heading="끼워 넣을 절"))], log="l")
    new, reverts, notes = revision.apply_revision(prev, rev, {"sections[1]"})
    assert len(new.sections) == 4 and new.sections[1].heading == "끼워 넣을 절" and reverts == 0, notes


def test_apply_revision_add_does_not_shift_a_later_delete():
    """007-C1-1: add sections[0]과 delete sections[2]가 같은 revision에 섞이면, delete는 원래 번호(C)를
    지워야 한다 — add가 먼저 insert돼 번호가 밀려 B가 지워지면 안 된다."""
    prev = page(sections=[section(heading="A"), section(heading="B"), section(heading="C")])
    rev = TopicPageRevision(changed=[
        Change(issue_idx=0, loc="sections[0]", action="add", value=section(heading="NEW")),
        Change(issue_idx=0, loc="sections[2]", action="delete", value=None),
    ], log="l")
    new, reverts, notes = revision.apply_revision(prev, rev, {"sections[2]"})
    assert [s.heading for s in new.sections] == ["NEW", "A", "B"] and reverts == 0, notes


def test_apply_revision_add_does_not_shift_a_later_sub_edit():
    """007-C1-1: add sections[0]과 sections[1].heading edit가 같은 revision에 섞이면, edit는 원래
    번호(B)에 적용돼야 한다 — add가 먼저 insert돼 밀리면 지적 안 된 A가 바뀌면 안 된다."""
    prev = page(sections=[section(heading="A"), section(heading="B"), section(heading="C")])
    rev = TopicPageRevision(changed=[
        Change(issue_idx=0, loc="sections[0]", action="add", value=section(heading="NEW")),
        Change(issue_idx=0, loc="sections[1].heading", action="edit", value="B2"),
    ], log="l")
    new, reverts, notes = revision.apply_revision(prev, rev, {"sections[1]"})
    assert [s.heading for s in new.sections] == ["NEW", "A", "B2", "C"] and reverts == 0, notes


# ---------- A7: 슬라이드 ----------
def test_slide_candidates_short_lines_with_numbers():
    slide = {"sec": 100, "frame_kind": "slide", "title": "t", "ocr_text": "\n".join(f"line{i}" for i in range(20)),
            "numbers": [{"value": "1"}], "table": None}
    assert slides.candidates(7, [slide], 2) == ["sl:7@100"]


def test_slide_candidates_table_qualifies():
    slide = {"sec": 50, "frame_kind": "slide", "title": "", "ocr_text": "", "numbers": [], "table": [["a"]]}
    assert slides.candidates(7, [slide], 2) == ["sl:7@50"]


def test_slide_candidates_excludes_non_slide_and_duplicate_titles():
    s1 = {"sec": 10, "frame_kind": "slide", "title": "같은 제목", "ocr_text": "", "numbers": [], "table": [["a"]]}
    s2 = {"sec": 20, "frame_kind": "slide", "title": "같은 제목", "ocr_text": "", "numbers": [], "table": [["a"]]}
    s3 = {"sec": 5, "frame_kind": "demo", "title": "", "ocr_text": "", "numbers": [], "table": [["a"]]}
    assert slides.candidates(7, [s1, s2, s3], 2) == ["sl:7@10"]


def test_slide_candidates_respects_max():
    many = [{"sec": i, "frame_kind": "slide", "title": str(i), "ocr_text": "", "numbers": [], "table": [["a"]]}
           for i in range(5)]
    assert len(slides.candidates(7, many, 2)) == 2


def test_slide_candidates_on_llamaindex_digest_fixture():
    """A7: LlamaIndex 영상(20장 사본, 실DB에서 뽑음) 후보 = 873·900초 2장."""
    digest = json.loads((Path(__file__).resolve().parent / "fixtures/s6_1/digest_llamaindex.json").read_text())
    assert len(digest["slides"]) == 20
    assert slides.candidates(digest["item_id"], digest["slides"], 2) == ["sl:274@873", "sl:274@900"]


def test_place_candidate_prefers_preceding_timeline_section():
    placed = slides.place_candidate(sec=100, timeline_secs=[0, 90, 200], section_video_secs=[[0], [90]],
                                    section_has_video=[True, True], taken=set())
    assert placed == 1


def test_write_places_unassigned_slide_candidates_into_preceding_section():
    p = page(sections=[section(heading="a", video_secs=[0]), section(heading="b", video_secs=[90])])
    final = slides.place_unassigned(p, ["sl:1@100"], {0, 90}, 2)
    assert final.sections[1].slide == "sl:1@100" and final.sections[0].slide is None


def test_place_candidate_falls_back_to_first_video_section():
    placed = slides.place_candidate(sec=5, timeline_secs=[], section_video_secs=[[], []],
                                    section_has_video=[False, True], taken=set())
    assert placed == 1


def test_topic_slide_info_does_not_truncate_before_pack_filter():
    """006-C1-21: topic_slide_info는 slides_max로 자르지 않는다(호출부인 write_topic이 pack 필터 뒤에 자른다).
    여기서 자르면 cap_pack이 앞선 후보를 빼도(pack 밖) 자격 있는 다음 후보를 돌려줄 기회가 없다."""
    from trendsit.brief.evidence import Member
    from trendsit.brief.write import topic_slide_info

    m = Member("vd:v1", "video", "t", "", "", "high", [], [], {}, slide_candidates=["sl:1@10", "sl:1@20", "sl:1@30"])
    cands, _secs = topic_slide_info([m], {"vd:v1"}, CFG)
    assert cands == ["sl:1@10", "sl:1@20", "sl:1@30"]  # 전부 돌려줌(slides_max=2라도 안 자름)
    only_third_in_pack = {"sl:1@30": []}
    filtered = [c for c in cands if c in only_third_in_pack][: CFG.write.slides_max]
    assert filtered == ["sl:1@30"]  # pack 필터를 먼저 거친 뒤 자르면 세 번째 후보가 살아남음


def test_place_candidate_2nd_stage_requires_section_max_secs_not_exceed_sec():
    """006-C1-12: 5.6 2단계는 video_secs의 '최댓값'이 sec 이하인 절만 후보다. 절 0은 [100, 1000](최댓값이
    873보다 큼) → 제외, 절 1은 [50](최댓값 50 ≤ 873) → 선택돼야 한다."""
    placed = slides.place_candidate(sec=873, timeline_secs=[], section_video_secs=[[100, 1000], [50]],
                                    section_has_video=[True, True], taken=set())
    assert placed == 1


def test_slide_read_lines_sec_matches_rounded_candidate_sec(tmp_path):
    """후보 id(digest 반올림 sec)와 판독 줄 id(video_frames.t)가 같은 초로 만들어져야 한다(006-A1-1)."""
    db = DB(tmp_path / "t.db")
    db.conn.execute("INSERT INTO items(id, source_id, channel, external_id, url, title, day, week) VALUES "
                    "(1,'s','video','e','http://x','t','2026-10-06','2026-W41')")
    db.conn.execute("INSERT INTO videos(item_id, video_id) VALUES (1, 'v1')")
    db.conn.execute("INSERT INTO video_frames(video_id, t, reading_json) VALUES ('v1', 872.867, ?)",
                    ('{"frame_kind":"slide","title":"t","ocr_text":"' + "\\n".join(f"l{i}" for i in range(20)) +
                     '","numbers":[{"value":"1"}]}',))
    [(eid, _text)] = fulltext.slide_read_lines(db, 1, "v1")
    digest_slide = {"sec": round(872.867), "frame_kind": "slide", "title": "t",
                    "ocr_text": "\n".join(f"l{i}" for i in range(20)), "numbers": [{"value": "1"}], "table": None}
    assert slides.candidates(1, [digest_slide], 2) == [eid]


# ---------- 006-A1-2: 최종판 저장 전 pack 밖 refs 제거(C-1) ----------
def test_scrub_pack_refs_clears_invalid_slide_and_keeps_section():
    from trendsit.brief.write import _scrub_pack_refs

    p = page(sections=[section(visual="none", slide="sl:1@999", slide_caption="캡션")])
    final, touched, remap = _scrub_pack_refs(_result_stub(), p, pack())
    assert final.sections[0].slide is None and final.sections[0].slide_caption == ""
    assert touched == {"sections[0]"} and remap == {0: 0}


def test_scrub_pack_refs_drops_tile_refs_outside_pack():
    from trendsit.brief.write import _scrub_pack_refs

    p = page(head_tiles=[Tile(value="1", label="l", refs=["it:1#s1", "it:99#s1"])])
    final, _touched, _remap = _scrub_pack_refs(_result_stub(), p, pack())
    assert final.head_tiles == []


def test_scrub_pack_refs_drop_shifts_later_section_numbers():
    """006-A3-10: 첫 절이 빠지면 둘째 절은 새 번호 0으로 당겨지고, check_locs도 새 번호로 맞춰진다."""
    from trendsit.brief.write import _scrub_pack_refs

    empty = section(paragraphs=[para(refs=["it:99#s1"])])  # pack 밖 refs뿐 → 절째 빠짐
    kept = section(heading="둘째", paragraphs=[para()])
    p = page(sections=[empty, kept])
    final, touched, remap = _scrub_pack_refs(_result_stub(), p, pack())
    assert len(final.sections) == 1 and final.sections[0].heading == "둘째"
    assert remap == {1: 0} and touched == set()  # 둘째 절은 안 건드렸으니 touched는 아니고 번호만 당겨짐


def test_place_unassigned_does_not_reattach_slide_to_section_dropped_for_bad_content():
    """006-C1-20: _drop_code_bad_sections가 형식 오류로 시각 요소를 통째로 비운 절에는 place_unassigned가
    슬라이드를 다시 붙이지 않는다(exclude=bad_secs). 대신 다른 자격 있는 절로 간다(render_frames 앞 단계만 본다,
    실제 프레임 파일 없이도 배치 로직만 확인)."""
    from trendsit.brief.write import _drop_code_bad_sections

    bad = section(heading="나쁜 절", visual="bars", bars=None, slide="sl:1@50", slide_caption="c", video_secs=[50],
                  paragraphs=[para(refs=["vd:1@50"])])
    good = section(heading="좋은 절", video_secs=[200], paragraphs=[para(refs=["vd:1@200"])])
    p = page(sections=[bad, good])
    vid_pack = pack(**{"vd:1@50": [EvidenceItem("vd:1@50", "vd:v1", "video", "transcript", "전사", {"site": "x"})],
                       "vd:1@200": [EvidenceItem("vd:1@200", "vd:v1", "video", "transcript", "전사", {"site": "x"})],
                       "sl:1@50": [EvidenceItem("sl:1@50", "vd:v1", "video", "slide_read", "판독", {"site": "x"})]})
    dropped, bad_secs = _drop_code_bad_sections(_result_stub(), p, vid_pack, CFG, {}, set())
    assert bad_secs == {0} and dropped.sections[0].slide is None  # 형식 오류 절(0)의 slide는 코드가 먼저 비움
    final = slides.place_unassigned(dropped, ["sl:1@50"], {50, 200}, CFG.write.slides_max, exclude=bad_secs)
    assert final.sections[0].slide is None  # exclude라 재부착 안 됨
    assert final.sections[1].slide == "sl:1@50"  # 대신 자격 있는 다른 절로

    without_exclude = slides.place_unassigned(dropped, ["sl:1@50"], {50, 200}, CFG.write.slides_max)
    assert without_exclude.sections[0].slide == "sl:1@50"  # exclude 없으면(옛 버그) 같은 절로 돌아감


def test_finalize_page_remaps_check_locs_when_section_drops():
    """006-A3-10: _finalize_page가 _scrub_pack_refs의 절 번호 대응표로 남은 check_locs도 새 번호로 맞춘다
    (예전 _remap_section_locs를 _finalize_page 안으로 합침, 006-C1-7)."""
    from trendsit.brief.write import _finalize_page

    empty = section(paragraphs=[para(refs=["it:99#s1"])])  # pack 밖 refs뿐 → 절째 빠짐
    kept = section(heading="둘째", paragraphs=[para()])
    p = page(sections=[empty, kept])
    old_check_locs = {"sections[0]", "sections[1]", "summary"}  # 1라운드 때 빠진 절·남은 절에 붙은 ⚠
    final, remapped = _finalize_page(_result_stub(), p, pack(), CFG, {}, old_check_locs, [], [], set())
    assert len(final.sections) == 1 and final.sections[0].heading == "둘째"
    assert remapped == {"sections[0]", "summary"}  # 빠진 절 표시는 버려지고, 남은 절 표시는 새 번호로


def test_finalize_page_maps_page_wide_sections_check_to_summary():
    """007-A1-4/A2-6: 페이지 상한(visuals_max·slides_max 등) 이슈는 loc이 "sections"(절 번호 없음)로 남는데,
    어느 절에도 안 붙고 summary·title도 아니면 화면에 ⚠가 전혀 안 뜬다. summary로 올려 표시되게 한다."""
    from trendsit.brief.write import _finalize_page

    p = page(sections=[section(), section(heading="둘째")])
    final, remapped = _finalize_page(_result_stub(), p, pack(), CFG, {}, {"sections"}, [], [], set())
    assert remapped == {"summary"}


def _result_stub():
    from trendsit.brief.write import TopicResult

    class _T:
        topic_id = "t1"

    return TopicResult(_T(), "checked", None, [], [], [], [], 1)


# ---------- B8: writer_limits ----------
def test_writer_limits_follow_source_count_and_brief_yaml():
    from trendsit.brief.write import writer_limits

    assert writer_limits(CFG, 1).sections == (3, 5) and writer_limits(CFG, 2).sections == (4, 7)
    full = writer_limits(CFG, 2)
    assert full.summary_sentences == (1, 2) and full.summary_chars_max == 200
    assert full.head_tiles_max == 4 and full.visuals_max == 4 and full.slides_max == 2
    tuned = CFG.model_copy(deep=True)  # 값이 md가 아니라 brief.yaml에서 옴
    tuned.write.sections.single_source = (1, 2)
    assert writer_limits(tuned, 1).sections == (1, 2)


def test_writer_limits_required_in_writer_input():
    from pydantic import ValidationError

    from trendsit.core.artifacts_brief import PlanBrief, Relation, WriterInput

    plan_ = PlanBrief(rank=1, angle="a", relation=Relation(type="new", topic_id=None))
    with pytest.raises(ValidationError, match="limits"):
        WriterInput(plan=plan_, evidence=[], previous=None, aliases=[])


# ---------- B9: loc_lines 렌더에 중복 없음 ----------
def test_writer_input_renders_no_visuals_as_plain_bool():
    """006-C2-4: no_visuals 전용 분기는 공통 코어(core/render.py)에서 되돌림(3.4 예산). 의미 설명은 writer.md가
    이미 정적으로 담고 있어, <data>는 다른 bool 칸과 같은 범용 렌더(true/false)로 충분하다."""
    from trendsit.brief.write import writer_limits
    from trendsit.core.artifacts_brief import PlanBrief, Relation, WriterInput
    from trendsit.core.render import render_data

    plan_ = PlanBrief(rank=1, angle="a", relation=Relation(type="new", topic_id=None))
    winp = WriterInput(plan=plan_, evidence=[], previous=None, aliases=[], limits=writer_limits(CFG, 1), no_visuals=True)
    assert "no_visuals: true" in render_data(winp)


def test_render_no_page_dup():
    """검수자·수정 입력에 같은 단락 문장이 loc_lines로 한 번만(page·previous는 코드만 씀)."""
    from trendsit.core.artifacts_brief import CriticInput, IndexedIssue, WriterReviseInput, loc_lines
    from trendsit.core.render import render_data

    p = page()
    sentence = p.sections[0].paragraphs[0].text
    critic = CriticInput(loc_lines=loc_lines(p), page=p, evidence=[], angle="a", code_warnings=[], round=1)
    revise = WriterReviseInput(loc_lines=loc_lines(p), previous=p, evidence=[], aliases=[],
                               issues=[IndexedIssue(idx=0, loc="sections[0].paragraphs[0]", type="format",
                                                    evidence_id=None, comment="c", hint="h")])
    assert render_data(critic).count(sentence) == 1 and render_data(revise).count(sentence) == 1
    assert critic.page is p and revise.previous is p


def test_ensure_frame_generates_960x540_and_skips_if_exists(tmp_path, monkeypatch):
    import subprocess

    monkeypatch.setattr(slides, "SLIDES_DIR", tmp_path / "slides")
    monkeypatch.setattr(slides, "MEDIA_ROOT", tmp_path / "media")
    media_dir = tmp_path / "media" / "V1xxxxxxxxx"
    media_dir.mkdir(parents=True)
    media = media_dir / "media.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=10:size=320x240:rate=5", media], check=True,
                   capture_output=True)
    path = slides.ensure_frame("V1xxxxxxxxx", 3)
    assert path is not None and Path(path).is_file()
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                          "-of", "csv=p=0", path], capture_output=True, text=True)
    assert out.stdout.strip() == "960,540"
    mtime_before = Path(path).stat().st_mtime
    path2 = slides.ensure_frame("V1xxxxxxxxx", 3)
    assert path2 == path and Path(path).stat().st_mtime == mtime_before  # 재실행 시 재생성 안 함


def test_ensure_frame_missing_media_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr(slides, "SLIDES_DIR", tmp_path / "slides")
    monkeypatch.setattr(slides, "MEDIA_ROOT", tmp_path / "media")
    assert slides.ensure_frame("no-such-video", 5) is None


def test_pack_index_groups_by_exact_id():
    items = [EvidenceItem("it:1#s1", "it:1", "text", "sentence", "a", {}), EvidenceItem("it:1#s2", "it:1", "text", "sentence", "b", {})]
    idx = pack_index(items)
    assert set(idx) == {"it:1#s1", "it:1#s2"}


# ---------- 006-A2-2: 머리 타일·페이지 상한 초과가 최종판에서 지워짐(C-2·C-3) ----------
def test_drop_code_bad_sections_strips_excess_visual_sections_and_flags_check():
    from trendsit.brief.write import _drop_code_bad_sections

    secs = [section(heading=f"절{i}", visual="tiles", tiles=[Tile(value="20", label="l", refs=["it:1#s1"])] * 2)
            for i in range(6)]
    check_locs: set[str] = set()
    out, _bad_secs = _drop_code_bad_sections(_result_stub(), page(sections=secs), pack(), CFG, {}, check_locs)
    assert sum(1 for s in out.sections if s.visual != "none") == CFG.write.visuals_max
    assert check_locs == {f"sections[{i}]" for i in range(CFG.write.visuals_max, 6)}


def test_drop_code_bad_sections_strips_excess_slides():
    from trendsit.brief.write import _drop_code_bad_sections

    src = {"site": "GeekNews", "title": "t", "date": "2026-10-06"}
    slide_pack = pack(**{f"sl:1@{i}": [EvidenceItem(f"sl:1@{i}", "it:1", "video", "slide_read", "판독", src)]
                         for i in range(3)})
    secs = [section(heading=f"절{i}", slide=f"sl:1@{i}", slide_caption="c") for i in range(3)]
    out, _bad_secs = _drop_code_bad_sections(_result_stub(), page(sections=secs), slide_pack, CFG, {}, set())
    assert sum(1 for s in out.sections if s.slide) == CFG.write.slides_max


def test_drop_code_bad_sections_removes_mismatched_head_tile():
    from trendsit.brief.write import _drop_code_bad_sections

    p = page(head_tiles=[Tile(value="8192 토큰", label="컨텍스트", refs=["it:1#s1"])])
    res = _result_stub()
    out, _bad_secs = _drop_code_bad_sections(res, p, pack(), CFG, {}, set())
    assert out.head_tiles == []
    assert any("타일" in a for a in res.attention)


def test_drop_code_bad_sections_removes_head_tile_left_checked_by_critic():
    """007-A1-4/A2-6: 검수자가 head_tiles[0]을 지적해 check_locs에 남으면(코드 재검사로는 안 잡히는 unsupported·overuse
    류), ⚠ 표시 없이 발행되지 않도록 그 타일을 뺀다."""
    from trendsit.brief.write import _drop_code_bad_sections

    p = page(head_tiles=[Tile(value="1점", label="의미 없는 수치", refs=["it:1#s1"])])
    out, _bad_secs = _drop_code_bad_sections(_result_stub(), p, pack(), CFG, {}, {"head_tiles[0]"})
    assert out.head_tiles == []


def test_initial_page_keeps_success_when_total_calls_reach_c5_cap(tmp_path):
    """v1.2 C-5: 1차 호출 2회(둘 다 잘림) 뒤 2차 호출이 3회째(스키마 실패+잘림 뒤 성공)에 성공하면 합이 5회라
    상한에 닿지만, 성공한 판은 횟수 때문에 버리지 않는다(사후 폐기 분기 삭제)."""
    from tests.conftest import FakeTransport, make_ctx, response
    from trendsit.brief.write import TopicResult, _initial_page, writer_limits
    from trendsit.core.artifacts_brief import PlanBrief, Relation, WriterInput

    cut = response('{"bad": 1}', tokens=(100, 4500))
    bad = response('{"bad": 1}', tokens=(100, 50))
    sec = {"heading": "h", "paragraphs": [{"text": "t", "refs": ["it:1#q1"]}], "visual": "none", "bars": None,
          "table": None, "tiles": [], "events": None, "slide": None, "slide_caption": "", "video_secs": [],
          "check": False}
    ok = response(json.dumps({"head_tiles": [], "sections": [sec], "summary": "s", "title": "t",
                              "log": "l", "attention": False}, ensure_ascii=False))
    ctx = make_ctx(tmp_path, FakeTransport([cut, cut, bad, cut, ok]), spec_cap=1.0)
    ctx.no_cache = True
    plan_ = PlanBrief(rank=1, angle="a", relation=Relation(type="new", topic_id=None))
    winp = WriterInput(plan=plan_, evidence=[], previous=None, aliases=[],
                       limits=writer_limits(CFG, 1), slide_candidates=[], no_visuals=False)
    res = TopicResult(None, "failed", None, [], [], [], [], 1)
    page, _err, _sid, winp2 = _initial_page(ctx, winp, res, None)
    assert page is not None and page.sections  # 성공한 판을 그대로 돌려줌(호출 상한 초과로 버리지 않음)
    assert winp2.no_visuals is True
