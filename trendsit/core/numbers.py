"""수치 정규화(공통, S5 5.1-9): S4 영상 대조(video/align)와 S5 코드 검사(brief)가 같이 쓴다.

값으로 정규화해 비교한다(쉼표, K/M/B, %, x/배, 소수점, 한국어 큰 단위, 영어 수사 one~ninety·hundred·thousand·
million·billion). "1.2M"과 "one point two million"은 같은 값이다. 단위 환산(토큰당 ↔ 100만 토큰당)은 하지 않는다.
"""

from __future__ import annotations

import re

# 크기 단위. 한 글자는 대문자(K는 소문자도)만: 소문자 m·b·t는 미터·바이트·톤일 수 있다
MAGNITUDE = {"k": 1e3, "K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12, "bn": 1e9, "BN": 1e9, "mn": 1e6, "MN": 1e6,
             "thousand": 1e3, "million": 1e6, "billion": 1e9, "trillion": 1e12,
             "천": 1e3, "만": 1e4, "억": 1e8, "조": 1e12, "천만": 1e7, "백만": 1e6, "천억": 1e11}
# 숫자 + 선택 크기 단위. 한 글자 단위는 뒤에 글자가 이어지면 단위가 아님(5ms, 3Mbps). '2만큼'의 만은 크기가 아님
_NUM = re.compile(
    r"(?<![\w.])(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?"
    r"(?:\s*((?i:thousand|million|billion|trillion))\b|(bn|mn|BN|MN|[KMBT]|k)(?![A-Za-z])|\s*(천만|백만|천억|[천만억조])(?!큼))?")
SMALL = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen "
    "seventeen eighteen nineteen".split())}
TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}
SCALES = {"thousand": 1e3, "million": 1e6, "billion": 1e9, "trillion": 1e12}
TOL = 1e-6
DECIMAL = re.compile(r"\d+(?:\.\d+)?")  # 이름·문장 속 수(쉼표·크기 단위 없이 숫자 그대로): 별칭의 버전 숫자, 선별 reason 대조


def _digits(text: str) -> list[tuple[float, bool]]:
    """(값, 크기 단위가 붙었는지)."""
    out = []
    for m in _NUM.finditer(text):
        whole, frac, word, letter, ko = m.groups()
        v = float(whole.replace(",", "") + (f".{frac}" if frac else ""))
        suffix = (word.lower() if word else None) or letter or ko
        out.append((v * MAGNITUDE.get(suffix, 1), bool(suffix)))
    return out


def _digits_values(text: str) -> list[float]:
    return [v for v, _s in _digits(text)]


def _word_cat(w: str) -> str | None:
    if w in SMALL:
        return "unit"
    if w in TENS:
        return "tens"
    if w == "hundred":
        return "hundred"
    if w in SCALES:
        return "scale"
    return "and" if w == "and" else None


def _follows(prev: str | None, cat: str, w: str) -> bool:
    """수사 묶음이 이어지는지. 'two three', 'twenty twenty', 'five and ten'은 따로 센다."""
    if prev is None:
        return True
    if prev == "unit":
        return cat in ("hundred", "scale")
    if prev == "tens":
        return (cat == "unit" and 1 <= SMALL[w] <= 9) or cat == "scale"
    if prev == "hundred":
        return cat in ("unit", "tens", "scale")
    return cat in ("unit", "tens")  # scale, and 다음


def _word_values(text: str) -> list[float]:
    """영어 수사 → 값. 'one point two million' = 1.2e6, 'twenty five' = 25, 'two hundred and fifty' = 250,
    'point three five' = 0.35. 'and'는 hundred·thousand 뒤에서만 잇는다."""
    toks = re.findall(r"[a-z]+", text.lower())
    out: list[float] = []
    total = current = 0.0
    prev: str | None = None

    def flush() -> None:
        nonlocal total, current, prev
        if prev is not None:
            out.append(total + current)
        total = current = 0.0
        prev = None

    i = 0
    while i < len(toks):
        w = toks[i]
        if w == "point" and i + 1 < len(toks) and SMALL.get(toks[i + 1], 10) < 10:
            value = total + current if prev is not None else 0.0
            i += 1
            digits = ""
            while i < len(toks) and SMALL.get(toks[i], 10) < 10:
                digits += str(SMALL[toks[i]])
                i += 1
            value += float(f"0.{digits}")
            if i < len(toks) and toks[i] in SCALES:
                value *= SCALES[toks[i]]
                i += 1
            out.append(value)
            total = current = 0.0
            prev = None
            continue
        cat = _word_cat(w)
        if cat is None or (cat == "and" and prev not in ("hundred", "scale")):
            flush()
            i += 1
            continue
        if cat == "and":
            prev = "and"
            i += 1
            continue
        if not _follows(prev, cat, w):
            flush()
        if cat == "unit":
            current += SMALL[w]
        elif cat == "tens":
            current += TENS[w]
        elif cat == "hundred":
            current = (current or 1) * 100
        else:
            total += (current or 1) * SCALES[w]
            current = 0.0
        prev = cat
        i += 1
    flush()
    return out


def number_values(text: str) -> list[float]:
    """글 안의 모든 수치 값(숫자 표기 + 영어 수사)."""
    return _digits_values(text) + _word_values(text)


def reading_value(value: str, unit: str) -> float | None:
    """판독 값 하나 → 수. 값에 크기 단위가 없고 unit이 크기 단위(K, M, B, million, 만, 억 등)면 곱한다."""
    nums = _digits(value)
    if nums:
        v, has_suffix = nums[0]
    else:
        words = _word_values(value)
        if not words:
            return None
        v, has_suffix = words[0], False
    head = (unit or "").strip().split(" ")[0]
    head = head.lower() if head.lower() in SCALES else head
    if not has_suffix and head in MAGNITUDE:
        v *= MAGNITUDE[head]
    return v


def same(a: float, b: float) -> bool:
    return abs(a - b) <= TOL * max(1.0, abs(a), abs(b))
