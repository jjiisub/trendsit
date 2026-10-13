"""S6-1 v1.3(리뷰 반영): 낱말 단위 음차 정리, 식별자 보호, 시각 요소 글자 정리, 절 영상 구간 채우기, 도식 목표·형광 limits."""

from __future__ import annotations

from types import SimpleNamespace

from trendsit.brief import checks
from trendsit.brief.aliases import word_patterns
from trendsit.brief.briefing import _section_secs
from trendsit.brief.write import writer_limits
from trendsit.core import config
from trendsit.core.artifacts_brief import BarGroup, NumberItem, Para, Section, Table, Tile, TopicPage

CFG = config.load("brief.yaml")
WORDS = word_patterns(CFG.aliases.transliteration)


def sec(text="문장이다.", refs=("it:1#s1",), **over):
    base = dict(heading="절 제목", paragraphs=[Para(text=text, refs=list(refs))], visual="none", bars=None, table=None,
                tiles=[], events=None, slide=None, slide_caption="", video_secs=[], check=False)
    return Section(**(base | over))


def page(sections, head_tiles=()):
    return TopicPage(head_tiles=list(head_tiles), sections=sections, summary="사건이다. 쟁점이다.", title="제목", log="l",
                     attention=False)


def fix(p, canon=None):
    return checks.autofix(p, CFG, canon or {}, [], set(), 10, WORDS)[0]


def test_word_level_transliteration_in_paragraphs():
    out = fix(page([sec("제미나이는 앤트로픽의 클로드 오퍼스 5와 하이쿠 모델을 비교했다.")]))
    assert out.sections[0].paragraphs[0].text == "Gemini는 Anthropic의 Claude Opus 5와 Haiku 모델을 비교했다."


def test_word_level_transliteration_keeps_ordinary_words():
    text = "솔루션과 라마단, 구글링 결과를 비교했다."
    assert fix(page([sec(text)])).sections[0].paragraphs[0].text == text


def test_visual_text_gets_names_normalized():
    tbl = Table(title="제미나이 플랫폼 모델", note="", columns=["모델", "소속"],
                rows=[["제미나이 4 아르곤", "구글"], ["Claude Opus 5", "앤트로픽"]], refs=["it:1#s1"])
    tile = Tile(value="38점", label="미스트랄 라지 4", note="", refs=["it:1#s1"])
    bars = BarGroup(title="비교", context="", unit="점",
                    items=[NumberItem(label="딥시크", value="39", ref="it:1#s1"), NumberItem(label="키미", value="38", ref="it:1#s1")])
    out = fix(page([sec(visual="table", table=tbl), sec(visual="bars", bars=bars)], head_tiles=[tile]))
    assert out.sections[0].table.rows == [["Gemini 4 Argon", "Google"], ["Claude Opus 5", "Anthropic"]]
    assert out.sections[0].table.title == "Gemini 플랫폼 모델"
    assert out.head_tiles[0].label == "Mistral Large 4" and out.head_tiles[0].value == "38점"
    assert [it.label for it in out.sections[1].bars.items] == ["DeepSeek", "Kimi"]
    assert out.sections[0].table.refs == ["it:1#s1"]  # refs는 건드리지 않음


def test_canonical_names_do_not_touch_identifiers():
    """v1.3: 정본 치환이 @scope/pkg·계정 이름 안을 바꾸지 않는다(W41 OpenRig '@OpenRig/cli')."""
    text = "openrig는 @openrig/cli로 설치하고 상위 기여자는 v-openrig-build다."
    out = fix(page([sec(text)]), canon={"openrig": "OpenRig"})
    assert out.sections[0].paragraphs[0].text == "OpenRig는 @openrig/cli로 설치하고 상위 기여자는 v-openrig-build다."


def test_section_secs_derived_from_refs_in_time_order():
    s = SimpleNamespace(video_secs=[], paragraphs=[SimpleNamespace(refs=["vd:5@330", "sl:5@130", "it:1#s1"]),
                                                   SimpleNamespace(refs=["vd:5@150"])])
    assert _section_secs(s, [0, 100, 300], cap=3) == [100, 300]


def test_section_secs_keeps_writer_choice_and_caps():
    s = SimpleNamespace(video_secs=[0, 999], paragraphs=[SimpleNamespace(refs=["vd:5@120", "vd:5@310", "vd:5@420"])])
    assert _section_secs(s, [0, 100, 300, 400], cap=3) == [0, 100, 300]  # 999는 타임라인에 없어 버림


def test_overuse_warning_uses_visuals_target():
    tiles = [Tile(value=f"{v}%", label="l", note="", refs=["it:1#s1"]) for v in (1, 2)]
    hi = CFG.write.visuals_target[1]
    ok = page([sec(visual="tiles", tiles=tiles) for _ in range(hi)] + [sec()])
    many = page([sec(visual="tiles", tiles=tiles) for _ in range(hi + 1)])
    assert not any("남발" in w for w in checks.warnings(ok, {}, CFG))
    assert any("남발" in w for w in checks.warnings(many, {}, CFG))


def test_writer_limits_carry_visuals_target_and_highlights():
    lim = writer_limits(CFG, 2)
    assert lim.visuals_target == tuple(CFG.write.visuals_target) and lim.highlights_page == tuple(CFG.write.highlights.page)


def test_name_and_word_patterns_keep_identifiers_and_short_words():
    """R3 #1·#2: 이름 패턴도 @scope/pkg·URL 안은 안 바꾸고, 2글자 낱말은 조사가 붙으면 안 바꾼다. 병기 중복은 정리."""
    canon_tl = [*WORDS]
    from trendsit.brief.aliases import translit_pattern
    tl = CFG.aliases.transliteration
    canon_tl = [(translit_pattern("DeepSeek", tl), "DeepSeek"), (translit_pattern("Claude Code", tl), "Claude Code"), *WORDS]
    text = ("@deepseek-ai/dsh와 @anthropic-ai/claude-code, github.com/deepseek-ai/x를 썼다. 혼자 솔로 했고 크다 라지만 "
            "Anthropic(앤트로픽)과 다마 솔라 4를 비교했다.")
    out = checks.autofix(page([sec(text)]), CFG, {}, [], set(), 10, canon_tl)[0].sections[0].paragraphs[0].text
    assert "@deepseek-ai/dsh" in out and "@anthropic-ai/claude-code" in out and "github.com/deepseek-ai/x" in out
    assert "솔로 했고" in out and "라지만" in out and "Anthropic과" in out and "Solar 4" in out


def test_section_secs_no_derivation_for_multi_video():
    s = SimpleNamespace(video_secs=[0], paragraphs=[SimpleNamespace(refs=["vd:5@330"])])
    assert _section_secs(s, [0, 300], cap=3, derive=False) == [0]
