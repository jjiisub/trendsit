"""대조(V8): 판독한 수치가 그 프레임의 발화와 앞뒤 30초 segments에 있는지. 없으면 slide_only_facts.

수치 정규화는 공통 모듈 core/numbers.py. "1.2M"이 화면에 있고 발화가 "one point two million"이면 같은 수치다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from ..core.artifacts_video import CheckNumber, Frame, Segment, SlideOnlyFact, SlideReading
from ..core.numbers import number_values, reading_value, same

# 수치가 아닌 판독(md가 금지해도 모델이 넣는 것): 단위 없는 연도, 이름에 붙은 버전(Opus 4.6), 슬라이드·쪽 번호
_YEAR = re.compile(r"^(19|20)\d{2}$")
_BARE = re.compile(r"^\d+(\.\d+)?$")
PAGE_WORDS = ("slide number", "slide no", "page number", "슬라이드 번호", "쪽 번호", "페이지 번호")


def not_a_fact(value: str, unit: str, what: str) -> str | None:
    """대조 전에 걸러 낼 이유. 판독은 그대로 두고 slide_only_facts에만 넣지 않는다(excluded로 기록)."""
    v, w = value.strip(), what.strip()
    if unit.strip() == "" and _YEAR.match(v):
        return "연도"
    if unit.strip() == "" and _BARE.match(v) and re.search(rf"[A-Za-z][\w.]*[\s-]{re.escape(v)}(?![\d.])", w):
        return "이름에 붙은 버전"
    if any(k in w.lower() for k in PAGE_WORDS):
        return "슬라이드 번호"
    return None


@dataclass
class AlignResult:
    slide_only: list[SlideOnlyFact] = field(default_factory=list)
    checks: list[CheckNumber] = field(default_factory=list)
    matched: list[dict[str, Any]] = field(default_factory=list)  # 발화에서 찾은 수치(리포트용)
    unparsed: list[dict[str, Any]] = field(default_factory=list)  # 수로 읽히지 않는 값
    excluded: list[dict[str, Any]] = field(default_factory=list)  # 수치가 아닌 판독(연도, 버전, 슬라이드 번호)


def spoken_window(frame: Frame, segments: list[Segment], window: float) -> str:
    near = [s.text for s in segments if s.end >= frame.t - window and s.start <= frame.t + window]
    return " ".join([frame.spoken_text, *near])


def align(readings: list[tuple[Frame, SlideReading]], segments: list[Segment], item_id: int,
          window: float = 30, spoken_usable: bool = True) -> AlignResult:
    """같은 수치가 여러 프레임에 나오면(같은 슬라이드를 두 번 잡음) 처음 시각 하나만 남긴다.
    spoken_usable=False(전사 품질 미달)면 발화(segments, 프레임 spoken_text 모두)에 있는 수치도 없는 것으로 본다."""
    res = AlignResult()
    seen: set[tuple[float, str, str]] = set()
    for frame, reading in readings:
        sec = round(frame.t)
        spoken = number_values(spoken_window(frame, segments, window)) if spoken_usable else []
        for n in reading.numbers:
            if n.confidence == "check":
                res.checks.append(CheckNumber(sec=sec, value=n.value, unit=n.unit, what=n.what, frame=frame.path))
                continue
            why = not_a_fact(n.value, n.unit, n.what)
            if why:
                res.excluded.append({"sec": sec, "value": n.value, "unit": n.unit, "what": n.what, "why": why})
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
