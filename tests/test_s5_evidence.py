"""S5 2단계(관문 A5·A6): 근거 자격, 근거 id 형식, 입력 상한과 뺀 근거, 표기 정규화."""

from __future__ import annotations

import json
import re

import pytest

from tests.conftest import FakeTransport, make_ctx, response
from trendsit.brief import aliases as al
from trendsit.brief import fulltext
from trendsit.brief.evidence import EvidenceItem, Member, cap_pack, week_evidence
from trendsit.brief.select import Applied
from trendsit.brief.write import evidence_docs
from trendsit.brief import write as wr
from trendsit.core import config
from trendsit.core.db import DB

ID = re.compile(r"^(it:\d+(#q\d+)?|og:\d+#q\d+|vd:\d+(@\d+|#ctx)?|sl:\d+@\d+|rp:[\w.-]+/[\w.-]+(#f\d+)?)$")


def _card(n_quotes: int = 2, relevance: str = "high", entities=("OpenAI",)) -> str:
    quotes = [{"n": i, "text": f"문장 {i} 수치 {i}0%"} for i in range(1, n_quotes + 1)]
    return json.dumps({"quotes": quotes, "numbers": [{"quote_n": 1, "value": "10%", "unit": "", "what": "x"}],
                       "claims": [{"quote_ns": [1, 2], "text": "주장"}], "summary": "요약이다.", "entities": list(entities),
                       "keywords": ["agent"], "relevance": relevance})


@pytest.fixture
def db(tmp_path):
    d = DB(tmp_path / "t.db")
    c = d.conn
    c.execute("INSERT INTO sources(id, channel, name) VALUES ('openai','text','OpenAI'), ('techbridge','video','TB')")
    for i, (ch, src) in enumerate([("text", "openai")] * 3 + [("video", "techbridge")] * 2, start=1):
        c.execute("INSERT INTO items(id, source_id, channel, external_id, title, url, day, week) VALUES (?,?,?,?,?,?,?,?)",
                  (i, src, ch, f"e{i}", f"제목 {i}", f"https://x/{i}", "2026-10-06", "2026-W41"))
    c.execute("INSERT INTO item_cards(item_id, version, card_json) VALUES (1, 1, ?), (2, 1, ?)", (_card(), _card()))
    c.execute("INSERT INTO item_same_as(item_id, canonical_id) VALUES (2, 1)")  # 같은 URL: 1이 기준
    for i, vid in ((4, "AAAAAAAAAAA"), (5, "BBBBBBBBBBB")):
        c.execute("INSERT INTO videos(item_id, video_id) VALUES (?,?)", (i, vid))
    digest = {"slide_only_facts": [{"fact": "pass rate", "value": "61%", "unit": "%", "sec": 30, "evidence": "vd:4@30",
                                    "confidence": "high"}],
              "key_points": [{"text": "포인트", "evidence": ["vd:4@30", "vd:4@60"]}],
              "timeline": [{"sec": 0, "label": "시작", "slide": False}], "summary": "영상 요약이다.",
              "name_pairs": [{"spoken": "Sweebench", "screen": "SWE-Bench", "sec": 30}]}
    c.execute("INSERT INTO video_digests(video_id, item_id, digest_json) VALUES ('AAAAAAAAAAA', 4, ?)", (json.dumps(digest),))
    for name, rel in (("a/good", True), ("b/off", False)):
        c.execute("INSERT INTO repo_cards(week, full_name, card_json) VALUES ('2026-W41', ?, ?)",
                  (name, json.dumps({"relevant": rel, "signal": "trending", "why_trending": "", "release": None})))
        c.execute("INSERT INTO repo_trending(week, full_name, stars_this_week) VALUES ('2026-W41', ?, 1200)", (name,))
    c.commit()
    return d


def test_eligibility_and_ids(db):
    ev = week_evidence(db, "2026-W41")
    assert sorted(ev.members) == ["it:1", "rp:a/good", "vd:AAAAAAAAAAA"]
    # 카드 없는 글 1건(3), digest 없는 영상 1건(5), 관련 없는 레포 1건. 같은 URL로 묶인 글(2)은 기준 항목(1)만
    assert ev.excluded == {"no_card": 1, "no_digest": 1, "irrelevant_repo": 1}
    ids = [it.id for m in ev.members.values() for it in m.items]
    assert ids and all(ID.match(i) for i in ids), [i for i in ids if not ID.match(i)]
    assert ev.members["vd:AAAAAAAAAAA"].corrections == {"Sweebench": "SWE-Bench"}  # 영상 안에서만


def test_v2_with_origin_puts_origin_quotes_first(db):
    v2 = {"quotes": [{"n": 1, "url": "https://arxiv.org/abs/1", "text": "origin sentence"}], "numbers": [], "claims": [],
          "summary": "원본 요약이다.", "origin": {"url": "https://arxiv.org/abs/1", "kind": "paper"}}
    db.conn.execute("INSERT INTO item_cards(item_id, version, card_json) VALUES (1, 2, ?)", (json.dumps(v2),))
    m = week_evidence(db, "2026-W41").members["it:1"]
    assert m.items[0].id == "og:1#q1" and m.summary == "원본 요약이다."
    assert any(i.id == "it:1#q1" for i in m.items)


def _member(key: str, channel: str, relevance: str, n: int) -> Member:
    items = [EvidenceItem(f"{key}#q{i}", key, channel, "quote", "가" * 200, {"site": key}) for i in range(n)]
    return Member(key, channel, key, "", "", relevance, [], [], {}, items)


def test_cap_pack_keeps_relevance_then_channel_diversity_and_records_dropped():
    ms = [_member("it:1", "text", "high", 10), _member("it:2", "text", "high", 10), _member("vd:3", "video", "mid", 3),
          _member("it:4", "text", "low", 3)]
    kept, dropped = cap_pack(ms, max_tokens=1500)
    keys = [k.member for k in kept]
    assert "vd:3" in keys  # 관련성이 낮아도 다른 채널이면 첫 바퀴에 들어감
    assert keys.count("it:1") >= 1 and keys.count("it:2") >= 1  # 한 출처가 상한을 다 쓰지 않음
    assert dropped and not set(dropped) & {k.id for k in kept}
    assert sum(len(json.dumps(k.as_dict(), ensure_ascii=False)) for k in kept) > 0
    kept_all, none = cap_pack(ms, max_tokens=10**6)
    assert none == [] and len(kept_all) == 26


@pytest.mark.parametrize("a,b", [("Qwen3", "Qwen3.5"), ("GPT-5", "GPT-5 mini"), ("Claude 4", "Claude 4.1"),
                                 ("Gemini Flash", "Gemini Pro")])
def test_version_or_size_difference_is_never_a_candidate(a, b):
    assert al.differs_in_version(a, b)
    ms = [Member(f"it:{i}", "text", "", "", "", "high", [n], [], {}) for i, n in enumerate((a, b))]
    rows = al.build(ms, config.KeywordsConfig(keywords=[], exclude=[]), fuzz_min=0).rows
    assert not [r for r in rows if {r.canonical, r.alias} == {a, b}]


def test_spelling_only_difference_is_auto_approved():
    ms = [Member("it:1", "text", "", "", "", "high", ["Claude Code"], [], {}),
          Member("it:2", "text", "", "", "", "high", ["Claude Code"], [], {}),
          Member("it:3", "text", "", "", "", "high", ["claude-code"], [], {}),
          Member("it:4", "text", "", "", "", "high", ["FrontierCode"], [], {}),
          Member("it:5", "text", "", "", "", "high", ["Frontier Code"], [], {})]
    t = al.build(ms, config.KeywordsConfig(keywords=[], exclude=[]), fuzz_min=90)
    amap = t.approved()
    assert amap["claude-code"] == "Claude Code"
    assert {"FrontierCode", "Frontier Code"} & set(amap)
    assert t.counts()["auto_approved"] == 2


def test_video_name_pairs_not_global(db):
    ev = week_evidence(db, "2026-W41")
    t = al.build(list(ev.members.values()), config.KeywordsConfig(keywords=[], exclude=[]), fuzz_min=90)
    assert not [r for r in t.rows if "Sweebench" in (r.alias, r.canonical)]


def test_save_keeps_decided_status(db):
    t = al.AliasTable([al.AliasRow("Claude", "클로드", "candidate", "x")])
    al.save(db, t, "r1")
    db.conn.execute("UPDATE aliases SET status='approved'")
    al.save(db, t, "r2")
    row = db.conn.execute("SELECT status, seen FROM aliases").fetchone()
    assert (row["status"], row["seen"]) == ("approved", 2)
    assert al.load_decided(db, al.AliasTable([al.AliasRow("Claude", "클로드", "candidate", "x")])).rows[0].status == "approved"


def test_numbers_inside_names_block_spelling_only_approval():
    ms = [Member(f"it:{i}", "text", "", "", "", "high", [n], [], {}) for i, n in enumerate(("Llama 3 8B", "Llama 38B"))]
    t = al.build(ms, config.KeywordsConfig(keywords=[], exclude=[]), fuzz_min=90)
    assert not t.approved()


def _v2_page(text: str, summary: str = "s다."):
    from trendsit.core.artifacts_brief import Para, Section, TopicPage

    return TopicPage(head_tiles=[], sections=[Section(heading="h", paragraphs=[Para(text=text, refs=["it:1#q1"])],
                                                      visual="none")], summary=summary, title="t", log="l")


def test_alias_replacement_respects_word_boundaries():
    from trendsit.brief import checks

    p = _v2_page("Aider와 AI 도구 비교 정리 내용")
    fixed, _ = checks.autofix(p, config.load("brief.yaml"), {"AI": "인공지능"}, [], set(), 10)
    assert fixed.sections[0].paragraphs[0].text == "Aider와 인공지능 도구 비교 정리 내용"


def test_r11_transliteration_aliases_and_autofix():
    from trendsit.brief import checks

    tr = {"Luna": "루나", "Flash": "플래시", "DeepSeek": "딥시크"}
    ms = [Member(f"it:{i}", "text", "", "", "", "high", [n], [], {})
          for i, n in enumerate(("GPT-6 Luna", "GPT-6 루나", "GPT-7 루나"))]
    rows = al.build(ms, config.KeywordsConfig(keywords=[], exclude=[]), fuzz_min=90, translit=tr).rows
    got = {(r.canonical, r.alias, r.status) for r in rows if r.reason.startswith("음차")}
    assert got == {("GPT-6 Luna", "GPT-6 루나", "approved")}  # 숫자가 다른 GPT-7 루나는 아님
    pat = al.translit_pattern("DeepSeek V4.1 Flash", tr)
    canon_pat = [(pat, "DeepSeek V4.1 Flash")]
    for text in ("딥시크-V4.1 플래시", "DeepSeek-V4.1 플래시", "딥시크 V4.1 Flash"):
        assert pat.sub("X", f"{text}가 나왔다") == "X가 나왔다"
    assert al.translit_pattern("Sol", {"Sol": "솔"}).sub("X", "솔루션과 솔은") == "솔루션과 X은"  # 낱말 안은 아님
    assert al.to_original("클로드 소네트 5.5", {"Claude": "클로드", "Sonnet": "소넷|소네트"}) == "Claude Sonnet 5.5"
    page = _v2_page("딥시크-V4.1 플래시 공개, 가격 인하함", "딥시크-V4.1 플래시가 나왔다.")
    fixed, _ = checks.autofix(page, config.load("brief.yaml"), {}, [], set(), 10, translit=canon_pat)
    assert fixed.summary == "DeepSeek V4.1 Flash가 나왔다." and fixed.sections[0].paragraphs[0].text.startswith("DeepSeek V4.1 Flash")


# ---------- 근거 공급(fulltext.py, S6-1 5.2, 파일을 옮김: test_s6_1_write.py 500줄 상한) ----------
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
    src = {"site": "GeekNews", "title": "t"}
    p = {"it:1#s1": [EvidenceItem("it:1#s1", "it:1", "text", "sentence", "첫 문장.", src)],
         "it:1#s2": [EvidenceItem("it:1#s2", "it:1", "text", "sentence", "둘째 문장.", src)]}
    docs = evidence_docs(p)
    assert len(docs) == 1 and docs[0].id == "it:1"
    assert "[it:1#s1]" in docs[0].text and "[it:1#s2]" in docs[0].text


def test_evidence_docs_skips_summary_and_claim_kinds():
    p = {"vd:1": [EvidenceItem("vd:1", "vd:X", "video", "summary", "요약", {})]}
    assert evidence_docs(p) == []


# ---------- 006-A3-1: write.py가 checks.run_checks를 키워드 인자로 불러야 함(영상·음차 토픽이 끝까지 돌아야 함) ----------
def _sec_v2(heading: str, text: str, refs: list[str], video_secs: list[int] | None = None) -> dict:
    return {"heading": heading, "paragraphs": [{"text": text, "refs": refs}], "visual": "none", "bars": None,
            "table": None, "tiles": [], "events": None, "slide": None, "slide_caption": "",
            "video_secs": video_secs or [], "check": False}


def test_write_topic_video_and_transliteration_runs_to_completion(tmp_path):
    """006-A3-1: run_checks 위치 인자가 어긋나면 영상 토픽(timeline_secs 있음)에서 TypeError로 실패하고,
    음차(클로드→Claude) 자동 수정도 적용되지 않는다. write_topic이 끝까지 돌고 두 가지가 모두 고쳐짐을 확인한다."""
    src = {"site": "YouTube", "title": "발표", "date": "2026-10-06"}
    member = Member("vd:v1", "video", "발표", "", "", "high", ["Claude"], [], src,
                     items=[EvidenceItem("vd:v1@10", "vd:v1", "video", "transcript", "발표 전사 묶음이다.", src)],
                     timeline=[{"sec": 10, "label": "시작", "slide": False}])
    topic = Applied("t1", 1, True, [1], ["vd:v1"], "new", None, "", "출시")
    page_json = json.dumps({
        "head_tiles": [],
        "sections": [
            _sec_v2("클로드 발표 핵심", "클로드가 발표했다.", ["vd:v1@10"], video_secs=[10]),
            _sec_v2("둘째 요점", "영상에서 다룬 내용이다.", ["vd:v1@10"]),
            _sec_v2("셋째 요점", "전사 묶음을 근거로 정리했다.", ["vd:v1@10"]),
        ],
        "summary": "클로드가 발표했다. 전사 내용을 다뤘다.",
        "title": "클로드 발표 정리", "log": "l", "attention": False,
    }, ensure_ascii=False)
    verdict_json = json.dumps({"atoms": [{"loc": "sections[0]", "fact": "f", "evidence_id": "vd:v1@10", "supported": True}],
                               "fact_support": {"total": 1, "supported": 1}, "issues": [],
                               "status": "pass", "log": "l", "attention": False}, ensure_ascii=False)
    ctx = make_ctx(tmp_path, FakeTransport([response(page_json), response(verdict_json)]), spec_cap=1.0)
    ctx.no_cache = True
    res = wr.write_topic(ctx, topic, {"vd:v1": member}, al.AliasTable([]), config.load("brief.yaml"))
    assert res.status in ("passed", "checked"), res.attention
    assert res.page is not None and res.page.sections[0].video_secs == [10]  # C-4: 실제 타임라인 sec은 지워지지 않음
    assert "Claude" in res.page.summary and "클로드" not in res.page.summary  # 음차 → 정본 자동 수정 적용
