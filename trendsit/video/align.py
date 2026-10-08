"""대조(V8): 판독한 수치가 그 프레임의 발화와 앞뒤 30초 segments에 있는지. 없으면 slide_only_facts.

수치는 값으로 정규화해 비교한다(쉼표, K/M/B, %, x/배, 소수점, 영어 수사 one~ninety·hundred·thousand·million·billion).
"1.2M"이 화면에 있고 발화가 "one point two million"이면 같은 수치다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from ..core.artifacts_video import CheckNumber, Frame, Segment, SlideOnlyFact, SlideReading

MAGNITUDE = {"k": 1e3, "thousand": 1e3, "m": 1e6, "mn": 1e6, "million": 1e6, "b": 1e9, "bn": 1e9,
             "billion": 1e9, "t": 1e12, "trillion": 1e12, "천": 1e3, "만": 1e4, "억": 1e8, "조": 1e12}
# 숫자 + 선택 크기 단위. 한 글자 단위(k, m, b)는 뒤에 글자가 이어지면 단위가 아님(5ms, 3min)
_NUM = re.compile(
    r"(?<![\w.])(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?"
    r"(?:\s*(thousand|million|billion|trillion)\b|(bn|mn|k|m|b|t)(?![a-z])|\s*(천|만|억|조))?",
    re.IGNORECASE)
SMALL = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen "
    "seventeen eighteen nineteen".split())}
SMALL |= {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80,
          "ninety": 90}
SCALES = {"thousand": 1e3, "million": 1e6, "billion": 1e9, "trillion": 1e12}
NUM_WORDS = set(SMALL) | set(SCALES) | {"hundred"}
TOL = 1e-6


def _digits_values(text: str) -> list[float]:
    out = []
    for m in _NUM.finditer(text):
        whole, frac, word, letter, ko = m.groups()
        v = float(whole.replace(",", "") + (f".{frac}" if frac else ""))
        suffix = (word or letter or ko or "").lower()
        out.append(v * MAGNITUDE.get(suffix, 1))
    return out


def _word_values(text: str) -> list[float]:
    """영어 수사 묶음 → 값. 'one point two million' = 1.2e6, 'twenty five' = 25, 'two hundred' = 200."""
    toks = re.findall(r"[a-z]+", text.lower())
    out, i = [], 0
    while i < len(toks):
        if toks[i] not in NUM_WORDS:
            i += 1
            continue
        total, current, seen = 0.0, 0.0, False
        while i < len(toks) and (toks[i] in NUM_WORDS or (toks[i] == "and" and seen)):
            w = toks[i]
            if w in SMALL:
                current += SMALL[w]
            elif w == "hundred":
                current = (current or 1) * 100
            elif w in SCALES:
                total += (current or 1) * SCALES[w]
                current = 0
            seen = True
            i += 1
        value = total + current
        if i < len(toks) - 1 and toks[i] == "point" and toks[i + 1] in SMALL and SMALL[toks[i + 1]] < 10:
            i += 1
            digits = ""
            while i < len(toks) and toks[i] in SMALL and SMALL[toks[i]] < 10:
                digits += str(SMALL[toks[i]])
                i += 1
            value += float(f"0.{digits}")
            if i < len(toks) and toks[i] in SCALES:
                value *= SCALES[toks[i]]
                i += 1
        if seen:
            out.append(value)
    return out


def number_values(text: str) -> list[float]:
    """글 안의 모든 수치 값(숫자 표기 + 영어 수사)."""
    return _digits_values(text) + _word_values(text)


def reading_value(value: str, unit: str) -> float | None:
    """판독 값 하나 → 수. 값에 크기 단위가 없고 unit이 크기 단위(M, 억 등)로 시작하면 곱한다."""
    nums = _digits_values(value) or _word_values(value)
    if not nums:
        return None
    v = nums[0]
    head = (unit or "").strip().lower().split(" ")[0]
    if not re.search(r"\d\s*(thousand|million|billion|trillion|bn|mn|[kmbt천만억조])", value, re.IGNORECASE) \
            and head in MAGNITUDE:
        v *= MAGNITUDE[head]
    return v


def same(a: float, b: float) -> bool:
    return abs(a - b) <= TOL * max(1.0, abs(a), abs(b))


@dataclass
class AlignResult:
    slide_only: list[SlideOnlyFact] = field(default_factory=list)
    checks: list[CheckNumber] = field(default_factory=list)
    matched: list[dict[str, Any]] = field(default_factory=list)  # 발화에서 찾은 수치(리포트용)
    unparsed: list[dict[str, Any]] = field(default_factory=list)  # 수로 읽히지 않는 값


def spoken_window(frame: Frame, segments: list[Segment], window: float) -> str:
    near = [s.text for s in segments if s.end >= frame.t - window and s.start <= frame.t + window]
    return " ".join([frame.spoken_text, *near])


def align(readings: list[tuple[Frame, SlideReading]], segments: list[Segment], item_id: int,
          window: float = 30) -> AlignResult:
    """같은 수치가 여러 프레임에 나오면(같은 슬라이드를 두 번 잡음) 처음 시각 하나만 남긴다."""
    res = AlignResult()
    seen: set[tuple[float, str, str]] = set()
    for frame, reading in readings:
        sec = round(frame.t)
        spoken = number_values(spoken_window(frame, segments, window))
        for n in reading.numbers:
            if n.confidence == "check":
                res.checks.append(CheckNumber(sec=sec, value=n.value, unit=n.unit, what=n.what, frame=frame.path))
                continue
            v = reading_value(n.value, n.unit)
            if v is None:
                res.unparsed.append({"sec": sec, "value": n.value, "unit": n.unit, "what": n.what})
                continue
            key = (round(v, 6), n.unit.strip().lower(), n.what.strip().lower())
            if key in seen:
                continue
            seen.add(key)
            if any(same(v, s) for s in spoken):
                res.matched.append({"sec": sec, "value": n.value, "unit": n.unit, "what": n.what})
                continue
            res.slide_only.append(SlideOnlyFact(fact=n.what, value=n.value, unit=n.unit, sec=sec,
                                                evidence=f"vd:{item_id}@{sec}", confidence=n.confidence))
    return res
