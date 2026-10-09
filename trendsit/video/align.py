"""대조(V8): 판독한 수치가 그 프레임의 발화와 앞뒤 30초 segments에 있는지. 없으면 slide_only_facts.

수치 정규화는 공통 모듈 core/numbers.py. "1.2M"이 화면에 있고 발화가 "one point two million"이면 같은 수치다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from ..core.artifacts_video import SLIDE_KINDS_FACT, CheckNumber, Frame, Segment, SlideOnlyFact, SlideReading
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


DENSE_FRAME = 10  # 한 프레임 수치가 이만큼 이상이면 표·대시보드로 보고 낮은 순위(S5 P4-1)
_TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9.\-]{3,}")


def _squash(word: str) -> str:
    return re.sub(r"[^a-z0-9]", "", word.lower())


def _unit_kind(text: str) -> str:
    t = text.strip().lower()
    if "%" in t or "퍼센트" in t or "percent" in t:
        return "%"
    if t.endswith(("x", "×", "배")) or "times" in t:
        return "x"
    if "$" in t or "달러" in t or "dollar" in t:
        return "$"
    return ""


def _spoken_numbers(text: str) -> list[tuple[str, str]]:
    """발화 속 (값 표기, 단위 종류). 숫자 표기와 바로 뒤 단위만 본다(수사는 값만 있어 교정 후보로 쓰지 않음)."""
    out = []
    for m in re.finditer(r"\$?\d+(?:[.,]\d+)*\s*(%|퍼센트|percent|x|배|times|달러|dollars?)?", text):
        out.append((m.group().strip(), _unit_kind(m.group())))
    return out


def spoken_variant(what: str, value: str, unit: str, spoken: str) -> str:
    """같은 대상을 발화가 다른 값으로 말했는지(잘못 들음, 예: 'Sweebench Pro 88%' ↔ 화면 SWE-Bench Pro 80.3%).
    what의 이름 토큰(4자 이상 영문)이 발화 토큰과 비슷하고(rapidfuzz 85 이상, 기호 무시), 그 뒤 60자 안에 단위 종류가
    같은 다른 숫자가 있으면 그 값을 돌려준다. 없으면 빈 문자열."""
    from rapidfuzz import fuzz

    kind = _unit_kind(f"{value}{unit}")
    if not kind:
        return ""
    names = [_squash(t) for t in _TOKEN.findall(what)]
    names = [n for n in names if len(n) >= 4]
    for m in _TOKEN.finditer(spoken):
        w = _squash(m.group())
        if len(w) < 4 or not any(fuzz.ratio(w, n) >= 85 for n in names):
            continue
        for v, k in _spoken_numbers(spoken[m.end():m.end() + 60]):
            if k == kind and not any(same(a, b) for a in number_values(v) for b in number_values(value)):
                return v
    return ""


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
        window_text = spoken_window(frame, segments, window) if spoken_usable else ""
        spoken = number_values(window_text) if spoken_usable else []
        dense = len(reading.numbers) >= DENSE_FRAME
        for n in reading.numbers:
            if n.confidence == "check":
                res.checks.append(CheckNumber(sec=sec, value=n.value, unit=n.unit, what=n.what, frame=frame.path))
                continue
            why = (f"kind={n.kind}" if n.kind not in SLIDE_KINDS_FACT else None) or not_a_fact(n.value, n.unit, n.what)
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
                                                evidence=f"vd:{item_id}@{sec}", confidence=n.confidence, dense=dense,
                                                spoken_value=spoken_variant(n.what, n.value, n.unit, window_text)))
    # 표·대시보드 프레임의 수치는 뒤로(같은 무리 안에서는 시각 순서 유지)
    res.slide_only.sort(key=lambda f: f.dense)
    return res
