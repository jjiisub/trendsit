"""S6-1 S-2: TopicPage v2 스키마·코드 검사·수정 합치기·근거 조립(5.2~5.6). A3~A7."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from trendsit.brief import checks, fulltext, revision, slides
from trendsit.brief.evidence import EvidenceItem, pack_index
from trendsit.brief.write import evidence_docs, refs_of
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


# ---------- A4: 근거 공급 ----------
def test_fulltext_sentences_split_on_newline_and_terminal_punct():
    text = "첫 문장이다. 둘째 문장이다!\n새 줄 문장이다?"
    assert fulltext.sentences(text) == ["첫 문장이다.", "둘째 문장이다!", "새 줄 문장이다?"]


def test_fulltext_cap_sentences_keeps_at_least_one():
    assert fulltext.cap_sentences(["가" * 100], 10) == ["가" * 100]
    assert fulltext.cap_sentences(["가" * 10, "나" * 10], 15) == ["가" * 10]


def test_article_lines_builds_sentence_ids_and_missing_text_flag(tmp_path):
    db = DB(tmp_path / "t.db")
    db.conn.execute("INSERT INTO items(id, source_id, channel, external_id, url, title, day, week) VALUES "
                    "(1,'s','text','e','http://x','t','2026-10-06','2026-W41')")
    db.conn.execute("INSERT INTO item_texts(item_id, text) VALUES (1, '첫 문장이다. 둘째 문장이다.')")
    lines, no_text = fulltext.article_lines(db, 1, 10000)
    assert lines == [("it:1#s1", "첫 문장이다."), ("it:1#s2", "둘째 문장이다.")] and not no_text
    lines2, no_text2 = fulltext.article_lines(db, 99, 10000)
    assert lines2 == [] and no_text2


def test_raw_evidence_sl_falls_back_to_given_line_when_ocr_empty(tmp_path):
    """006-A2-20: OCR 글자가 비어도(수치만 있는 슬라이드) raw_evidence가 빈 글자 대신 작성자가 받은 판독 줄을 돌려준다."""
    db = DB(tmp_path / "t.db")
    db.conn.execute("INSERT INTO items(id, source_id, channel, external_id, url, title, day, week) VALUES "
                    "(1,'s','video','e','http://x','t','2026-10-06','2026-W41')")
    db.conn.execute("INSERT INTO videos(item_id, video_id) VALUES (1, 'v1')")
    db.conn.execute("INSERT INTO video_frames(video_id, t, reading_json) VALUES ('v1', 100, ?)",
                    ('{"frame_kind":"slide","title":"제목","ocr_text":"","numbers":[{"value":"1"}],"table":null}',))
    [(eid, text)] = fulltext.slide_read_lines(db, 1, "v1")
    item = EvidenceItem(eid, "vd:v1", "video", "slide_read", text, {})
    out = fulltext.raw_evidence(db, eid, [item])
    assert out == text and out != ""


def test_raw_evidence_keeps_both_sides_when_slide_fact_and_transcript_id_collide(tmp_path):
    """006-A2-8: slide_fact vd:{id}@{sec}가 전사 묶음과 같은 sec(25의 배수)면 id가 겹친다. raw_evidence가
    ±30초 창(slide_fact)뿐 아니라 겹친 전사 묶음 원문(items[1:])도 잃지 않고 이어 붙인다."""
    db = DB(tmp_path / "t.db")
    db.conn.execute("INSERT INTO items(id, source_id, channel, external_id, url, title, day, week) VALUES "
                    "(1,'s','video','e','http://x','t','2026-10-06','2026-W41')")
    db.conn.execute("INSERT INTO videos(item_id, video_id) VALUES (1, 'v1')")
    db.conn.execute('INSERT INTO video_segments(video_id, idx, start, "end", text) VALUES '
                    "('v1', 0, 510, 525, '창 안 발화다.')")
    src = {"site": "GeekNews", "title": "t"}
    slide_fact = EvidenceItem("vd:1@525", "vd:v1", "video", "slide_fact", "발표 슬라이드 수치: 1위", src, value="1", unit="위")
    transcript = EvidenceItem("vd:1@525", "vd:v1", "video", "transcript", "전사 묶음 원문이다.", src)
    out = fulltext.raw_evidence(db, "vd:1@525", [slide_fact, transcript])
    assert "창 안 발화다." in out and "전사 묶음 원문이다." in out


def test_repo_fact_lines_order_fact_then_trending_then_release():
    card = {"evidence": [{"fact": "하는 일"}, {"fact": "별 1.6k"}], "why_trending": "릴리스 때문",
            "release": {"tag": "v1", "date": "2026-10-01", "line": "첫 출시"}}
    out = fulltext.repo_fact_lines("a/b", card)
    assert [eid for eid, _ in out] == ["rp:a/b#f1", "rp:a/b#f2", "rp:a/b#f3", "rp:a/b#f4"]
    assert "뜨는 이유" in out[2][1] and "릴리스 v1" in out[3][1]


def test_evidence_docs_groups_by_member_one_document():
    p = pack()
    p["it:1#s2"] = [EvidenceItem("it:1#s2", "it:1", "text", "sentence", "둘째 문장.", {"site": "GeekNews", "title": "t"})]
    docs = evidence_docs(p)
    assert len(docs) == 1 and docs[0].id == "it:1"
    assert "[it:1#s1]" in docs[0].text and "[it:1#s2]" in docs[0].text


def test_evidence_docs_skips_summary_and_claim_kinds():
    p = {"vd:1": [EvidenceItem("vd:1", "vd:X", "video", "summary", "요약", {})]}
    assert evidence_docs(p) == []


# ---------- A5: 코드 검사 ----------
def test_check_passes_good_page():
    p = page(sections=three_sections())
    assert checks.check(p, pack(), 1, CFG) == []


def test_check_rejects_wrong_ref():
    p = page(sections=[section(paragraphs=[para(refs=["it:99#s1"])])])
    issues = checks.check(p, pack(), 1, CFG)
    assert any(i.type == "wrong_ref" for i in issues)


def test_check_rejects_number_mismatch():
    p = page(sections=three_sections(paragraphs=[para(text="비율은 90%다.")]))
    issues = checks.check(p, pack(), 1, CFG)
    assert any(i.type == "number_mismatch" for i in issues)


def test_check_rejects_visual_bars_without_bars_field():
    p = page(sections=three_sections(visual="bars", bars=None))
    issues = checks.check(p, pack(), 1, CFG)
    assert any(i.type == "format" and "visual" in i.comment for i in issues)


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
    final, touched = _scrub_pack_refs(_result_stub(), p, pack())
    assert final.sections[0].slide is None and final.sections[0].slide_caption == ""
    assert touched == {"sections[0]"}


def test_scrub_pack_refs_drops_tile_refs_outside_pack():
    from trendsit.brief.write import _scrub_pack_refs

    p = page(head_tiles=[Tile(value="1", label="l", refs=["it:1#s1", "it:99#s1"])])
    final, _touched = _scrub_pack_refs(_result_stub(), p, pack())
    assert final.head_tiles == []


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
def test_writer_input_renders_no_visuals_as_spec_sentence():
    """006-A2-32: no_visuals=true면 'no_visuals: true'가 아니라 5.2가 정한 뜻 문장이 렌더된다."""
    from trendsit.brief.write import writer_limits
    from trendsit.core.artifacts_brief import PlanBrief, Relation, WriterInput
    from trendsit.core.render import render_data

    plan_ = PlanBrief(rank=1, angle="a", relation=Relation(type="new", topic_id=None))
    winp = WriterInput(plan=plan_, evidence=[], previous=None, aliases=[], limits=writer_limits(CFG, 1), no_visuals=True)
    text = render_data(winp)
    assert "no_visuals: 모든 절의 visual을 none, head_tiles만" in text and "no_visuals: true" not in text


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
    out = _drop_code_bad_sections(_result_stub(), page(sections=secs), pack(), CFG, {}, check_locs)
    assert sum(1 for s in out.sections if s.visual != "none") == CFG.write.visuals_max
    assert check_locs == {f"sections[{i}]" for i in range(CFG.write.visuals_max, 6)}


def test_drop_code_bad_sections_strips_excess_slides():
    from trendsit.brief.write import _drop_code_bad_sections

    src = {"site": "GeekNews", "title": "t", "date": "2026-10-06"}
    slide_pack = pack(**{f"sl:1@{i}": [EvidenceItem(f"sl:1@{i}", "it:1", "video", "slide_read", "판독", src)]
                         for i in range(3)})
    secs = [section(heading=f"절{i}", slide=f"sl:1@{i}", slide_caption="c") for i in range(3)]
    out = _drop_code_bad_sections(_result_stub(), page(sections=secs), slide_pack, CFG, {}, set())
    assert sum(1 for s in out.sections if s.slide) == CFG.write.slides_max


def test_drop_code_bad_sections_removes_mismatched_head_tile():
    from trendsit.brief.write import _drop_code_bad_sections

    p = page(head_tiles=[Tile(value="8192 토큰", label="컨텍스트", refs=["it:1#s1"])])
    res = _result_stub()
    out = _drop_code_bad_sections(res, p, pack(), CFG, {}, set())
    assert out.head_tiles == []
    assert any("타일" in a for a in res.attention)
