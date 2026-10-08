"""S4 대조(V8, A8): 판독 수치 ↔ 발화. 표기가 달라도 같은 수치면 대조, 30초 밖이면 slide_only, check는 따로."""

from __future__ import annotations

import pytest

from trendsit.core.artifacts_video import Frame, Segment, SlideNumber, SlideReading
from trendsit.video.align import align, number_values, reading_value


def frame(t: float, spoken: str = "", idx: int | None = None) -> Frame:
    return Frame(t=t, path=f"frames/r/frame_{int(t):04d}.jpg", reason="scene-change", segment_index=idx,
                 spoken_text=spoken)


def reading(*nums: tuple[str, str, str, str]) -> SlideReading:
    return SlideReading(frame_kind="slide", ocr_text=" ".join(n[1] + n[2] for n in nums),
                        numbers=[SlideNumber(confidence=c, value=v, unit=u, what=w) for c, v, u, w in nums],
                        table=None, title="", log="판독", attention=False)


@pytest.mark.parametrize("value,unit,expected", [
    ("1.2M", "", 1.2e6), ("1,200,000", "", 1.2e6), ("35%", "%", 35), ("3x", "", 3), ("3", "배", 3),
    ("$4.5B", "", 4.5e9), ("1.2", "M", 1.2e6), ("12", "억", 1.2e9), ("40", "ms", 40), ("0.75", "", 0.75),
])
def test_reading_value(value, unit, expected):
    assert reading_value(value, unit) == pytest.approx(expected)


@pytest.mark.parametrize("text,expected", [
    ("one point two million users", 1.2e6), ("thirty-five percent", 35), ("twenty five", 25),
    ("two hundred and fifty", 250), ("1.2 million", 1.2e6), ("2,000 PRs", 2000), ("three times faster", 3),
    ("a billion tokens", 1e9), ("40ms", 40),
])
def test_number_values_finds(text, expected):
    assert any(abs(v - expected) < 1e-6 * max(1, expected) for v in number_values(text)), number_values(text)


def test_same_number_spoken_differently_is_matched():
    segs = [Segment(start=95, end=100, text="we now serve one point two million developers"),
            Segment(start=100, end=104, text="and thirty-five percent of them use agents")]
    r = reading(("high", "1.2M", "", "developers"), ("high", "35%", "%", "agent users"))
    res = align([(frame(110, "and thirty-five percent of them use agents", 1), r)], segs, item_id=905)
    assert res.slide_only == [] and len(res.matched) == 2


def test_outside_window_is_slide_only_with_evidence_id():
    segs = [Segment(start=10, end=14, text="latency went down to 40 ms"),
            Segment(start=200, end=205, text="now the roadmap")]
    r = reading(("high", "40", "ms", "p95 latency"), ("low", "2,000", "", "PRs per month"))
    res = align([(frame(200.4, "now the roadmap", 1), r)], segs, item_id=905, window=30)
    assert [(f.value, f.sec, f.evidence, f.confidence) for f in res.slide_only] == [
        ("40", 200, "vd:905@200", "high"), ("2,000", 200, "vd:905@200", "low")]


def test_inside_window_is_matched():
    segs = [Segment(start=175, end=180, text="latency went down to 40 ms")]
    res = align([(frame(200, "", None), reading(("high", "40", "ms", "p95 latency")))], segs, item_id=1)
    assert res.slide_only == [] and res.matched


def test_check_numbers_go_to_separate_list_and_duplicates_once():
    r = reading(("check", "1?8", "%", "흐린 수치"), ("high", "42", "%", "share"))
    res = align([(frame(50), r), (frame(55), r)], [], item_id=7)
    assert len(res.checks) == 2 and all(c.value == "1?8" for c in res.checks)
    assert [f.sec for f in res.slide_only] == [50]  # 같은 슬라이드를 두 번 잡아도 한 번


def test_unparsed_values_are_not_facts():
    res = align([(frame(5), reading(("high", "GPT", "", "모델 이름")))], [], item_id=7)
    assert res.slide_only == [] and res.unparsed


@pytest.mark.parametrize("value,unit,what,why", [
    ("2026", "", "Retrieval Harness", "연도"), ("4.6", "", "Opus 4.6", "이름에 붙은 버전"),
    ("4.5", "", "Haku 4.5 (think)", "이름에 붙은 버전"), ("18", "", "contact (슬라이드 번호)", "슬라이드 번호"),
    ("10", "", "BrowseComp-Plus query workload (slide number)", "슬라이드 번호"),
])
def test_non_facts_are_excluded(value, unit, what, why):
    res = align([(frame(5), reading(("high", value, unit, what)))], [], item_id=7)
    assert res.slide_only == [] and res.excluded[0]["why"] == why


@pytest.mark.parametrize("value,unit,what", [
    ("1M", "docs per day", "Low Cost Regime require 1M docs per day"), ("16", "page(s)", "Paste 16 page(s) in 0.03s"),
    ("2,000", "", "PRs per month"), ("73.3%", "%", "DR-DCI on BrowseComp-Plus"), ("4.6", "", "average rating"),
])
def test_real_facts_are_kept(value, unit, what):
    res = align([(frame(5), reading(("high", value, unit, what)))], [], item_id=7)
    assert len(res.slide_only) == 1 and res.excluded == []


@pytest.mark.parametrize("text,expected", [
    ("between five and ten percent", [5, 10]), ("two three", [2, 3]), ("twenty twenty six", [20, 26]),
    ("point three five", [0.35]), ("one thousand two hundred", [1200]), ("5천만 원", [5e7]), ("2만큼", [2]),
    ("5m walk", [5]),
])
def test_number_values_exact(text, expected):
    assert number_values(text) == pytest.approx(expected)


@pytest.mark.parametrize("value,unit,expected", [("5", "m", 5), ("7", "km", 7), ("5m", "", 5), ("2", "Million", 2e6)])
def test_units_are_not_magnitudes(value, unit, expected):
    assert reading_value(value, unit) == pytest.approx(expected)


def test_unusable_transcript_ignores_frame_spoken_text():
    """전사 품질 미달이면 프레임 spoken_text(같은 환각 전사)로도 대조하지 않는다."""
    f = frame(100, "we hit 41 percent of teams", 0)
    r = reading(("high", "41%", "%", "of teams"))
    assert align([(f, r)], [], item_id=1).matched
    res = align([(f, r)], [], item_id=1, spoken_usable=False)
    assert res.matched == [] and [x.value for x in res.slide_only] == ["41%"]
