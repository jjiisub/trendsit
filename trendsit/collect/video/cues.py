"""발화 → 프레임 시각("이 화면", "this slide" 같은 화면 지시 표현) + 프레임마다 그 시각의 발화(spoken_text).

스킬 frame_cues.py에서 옮김. 발표자가 슬라이드를 가리키며 말할 때는 화면 변화가 오히려 작아서
화면 변화 기반 후보가 놓치는 프레임을 전사로 되찾는다.
"""

from __future__ import annotations

import bisect
import re
from typing import Any

MIN_CUE_INTERVAL = 5.0
CUE_OFFSET = 1.5  # 화면은 발화보다 조금 늦게 바뀐다
GAP_MIN = 2.0  # 이보다 긴 발화 공백은 장면 전환 신호
GAP_OFFSET = 0.5
CUE_SCORE_THRESHOLD = 2.0
# 전사 segment는 2~3초 조각이라 "여기 이 부분을 / 보시면"처럼 지시어와 동사가 갈린다. 인접 segment를 함께 본다
WINDOW_SEC = 4.0
WINDOW_MAX_SEGMENTS = 3
SPOKEN_TOLERANCE = 2.0  # 프레임 시각에서 이 안에 발화가 없으면 spoken_text 없음

# 한국어: 형태소 분석 없이 토큰 앞부분 일치(조사가 붙는다). '이런'은 추상 용법이 흔해 넣지 않음
KO_DEICTIC_PREFIX = ("여기", "여길", "요기", "저기", "저길", "이거", "이걸", "이게", "이쪽", "저쪽")
KO_DEICTIC_PHRASE = ("이 부분", "이 화면", "그 부분", "이 표", "이 그래프", "이 코드")
KO_VISUAL_NOUN = ("화면", "슬라이드", "표", "그래프", "차트", "그림", "사진", "코드", "왼쪽", "오른쪽", "위쪽",
                  "아래쪽", "도표", "다이어그램")
KO_VISUAL_VERB = ("보시면", "보시는", "보이시죠", "보이시", "보세요", "봐주세요", "보시죠", "나와있", "나와 있",
                  "표시된", "표시돼", "적혀", "써있", "써 있", "나타나", "보십시오", "확인하시면", "확인해보시면",
                  "확인해 보시면", "보이는")
KO_UI_VERB = ("클릭", "누르", "눌러", "선택하", "입력하", "입력해", "실행하", "실행해", "열어", "열면", "들어가",
              "복사", "붙여", "드래그", "체크")
KO_EXCLUDE = ("아시겠지만", "아시다시피", "보시면 아시", "말씀드리면", "생각해보면", "여기저기", "이거 좀",
              "이런 거 아니", "저기요")
EN_DEICTIC = ("here", "this", "these", "that")
EN_VISUAL_PHRASE = ("look at", "as you can see", "you can see", "take a look", "notice", "on the screen",
                    "on screen", "shown", "highlighted", "displayed", "pay attention to", "check out")
EN_VISUAL_NOUN = ("chart", "graph", "table", "diagram", "slide", "code", "figure", "image", "screen", "left side",
                  "right side", "top left", "bottom right", "column", "axis")
EN_EXCLUDE = ("look, the", "the point is", "this is important", "that said", "in other words", "this means",
              "look, i", "that's why")


def _has(text: str, needles: tuple[str, ...]) -> bool:
    return any(n in text for n in needles)


def _word(text: str, words: tuple[str, ...]) -> bool:
    return any(re.search(rf"\b{re.escape(w)}\b", text) for w in words)


def _ko_score(t: str) -> float:
    if _has(t, KO_EXCLUDE):
        return 0.0
    deictic = any(tok.startswith(p) for tok in t.split() for p in KO_DEICTIC_PREFIX) or _has(t, KO_DEICTIC_PHRASE)
    noun, visual, ui = _has(t, KO_VISUAL_NOUN), _has(t, KO_VISUAL_VERB), _has(t, KO_UI_VERB)
    verb = visual or ui
    return (deictic * 1.0 + noun * 1.0 + (1.2 if visual else 0.8 if ui else 0.0)
            + (1.5 if deictic and verb else 0.0) + (0.5 if noun and verb else 0.0))


def _en_score(t: str) -> float:
    if _has(t, EN_EXCLUDE):
        return 0.0
    deictic, phrase, noun = _word(t, EN_DEICTIC), _has(t, EN_VISUAL_PHRASE), _word(t, EN_VISUAL_NOUN)
    # this/that은 매우 흔해 단독 가중치를 낮춘다
    return (deictic * 0.8 + noun * 1.0 + phrase * 1.4 + (1.5 if deictic and phrase else 0.0)
            + (0.5 if noun and phrase else 0.0))


def segment_score(text: str, language: str) -> float:
    t = (text or "").strip().lower()
    if not t:
        return 0.0
    lang = (language or "").split("-")[0].lower()
    return _ko_score(t) if lang == "ko" else _en_score(t) if lang == "en" else 0.0


def window_text(segments: list[dict[str, Any]], i: int) -> str:
    base, parts = float(segments[i]["start"]), []
    for j in range(i, min(len(segments), i + WINDOW_MAX_SEGMENTS)):
        if j > i and float(segments[j]["start"]) - base > WINDOW_SEC:
            break
        parts.append(segments[j].get("text") or "")
    return " ".join(parts)


def select_cues(segments: list[dict[str, Any]], language: str, *, budget: int, lo: float, hi: float
                ) -> tuple[list[float], list[str]]:
    """화면 지시 표현과 발화 공백으로 프레임 시각을 고른다(점수 높은 순, 5초 간격). 둘 다 reason=transcript-cue."""
    warnings = []
    lang = (language or "").split("-")[0].lower()
    if lang not in ("ko", "en"):
        warnings.append(f"{language} 영상은 화면 지시 표현 목록이 없어 발화 공백 신호만 사용")
    if budget <= 0 or not segments:
        return [], warnings
    cands: list[tuple[float, float]] = []  # (score, t)
    if lang in ("ko", "en"):
        for i, seg in enumerate(segments):
            score = segment_score(window_text(segments, i), lang)
            if score >= CUE_SCORE_THRESHOLD:
                cands.append((score, min(float(seg["start"]) + CUE_OFFSET, float(seg["end"]))))
    for i in range(1, len(segments)):
        gap = float(segments[i]["start"]) - float(segments[i - 1]["end"])
        if gap >= GAP_MIN:
            cands.append((1.5 + min(gap, 10.0) / 10.0, float(segments[i - 1]["end"]) + GAP_OFFSET))
    cands = [(s, t) for s, t in cands if lo <= t <= hi]
    cands.sort(key=lambda c: (-c[0], c[1]))
    chosen: list[float] = []
    for _score, t in cands:
        if len(chosen) >= budget:
            break
        if all(abs(t - k) >= MIN_CUE_INTERVAL for k in chosen):
            chosen.append(t)
    return sorted(round(t, 3) for t in chosen), warnings


def attach_spoken(frames: list[dict[str, Any]], segments: list[dict[str, Any]],
                  tolerance: float = SPOKEN_TOLERANCE) -> list[dict[str, Any]]:
    """모든 프레임에 segment_index, spoken_text를 붙인다. 프레임 시각을 품은 segment, 없으면 2초 안의 가장 가까운 것."""
    starts = [float(s["start"]) for s in segments]
    for f in frames:
        f["segment_index"], f["spoken_text"] = None, ""
        if not segments:
            continue
        t = float(f["t"])
        idx = bisect.bisect_right(starts, t) - 1
        near = range(max(0, idx - 1), min(len(segments), idx + 2))
        best = next((j for j in near if float(segments[j]["start"]) <= t <= float(segments[j]["end"])), None)
        if best is None:
            dist = {j: min(abs(t - float(segments[j]["start"])), abs(t - float(segments[j]["end"]))) for j in near}
            j = min(dist, key=lambda k: dist[k])
            best = j if dist[j] <= tolerance else None
        if best is not None and (segments[best].get("text") or "").strip():
            f["segment_index"], f["spoken_text"] = best, segments[best]["text"]
    return frames
