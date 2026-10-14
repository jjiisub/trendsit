"""슬라이드 후보·배치·프레임(S6-1 5.6, D-30·D-34·D-39). ffmpeg는 외부 실행 파일(subprocess)."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from ..core.artifacts_brief import TopicPage
from ..core.config import ROOT

SLIDES_DIR = ROOT / "data" / "slides"
MEDIA_ROOT = ROOT / "data" / "media"
SHORT_LINE_MAX = 25
SHORT_LINES_MIN = 20


def _is_candidate(slide: dict[str, Any]) -> bool:
    """후보 조건: ① 25자 이하 짧은 줄 20개 이상 + 수치 1개 이상, 또는 ② 표가 있음."""
    if slide.get("table"):
        return True
    lines = [ln for ln in (slide.get("ocr_text") or "").splitlines() if ln.strip()]
    short = sum(1 for ln in lines if len(ln.strip()) <= SHORT_LINE_MAX)
    return short >= SHORT_LINES_MIN and bool(slide.get("numbers"))


def candidates(item_id: int, digest_slides: list[dict[str, Any]], max_candidates: int) -> list[str]:
    """영상 digest의 slides[](frame_kind=="slide"만) → sl:{item_id}@{sec} 후보(같은 제목은 첫 장만, sec 오름차순)."""
    seen_titles: set[str] = set()
    out: list[tuple[int, str]] = []
    for s in sorted((s for s in digest_slides if s.get("frame_kind") == "slide"), key=lambda s: s["sec"]):
        if not _is_candidate(s):
            continue
        title = (s.get("title") or "").strip()
        if title and title in seen_titles:
            continue
        seen_titles.add(title)
        out.append((s["sec"], f"sl:{item_id}@{s['sec']}"))
    return [eid for _sec, eid in out[:max_candidates]]


def place_candidate(sec: int, timeline_secs: list[int], section_video_secs: list[list[int]],
                    section_has_video: list[bool], taken: set[int]) -> int | None:
    """후보 하나를 둘 절(0부터). 5.6: 그 sec 직전 타임라인 구간 시작 초를 video_secs에 가진 절 → 없으면 video_secs
    최댓값이 sec 이하인 가장 가까운 절 → 없으면 첫 영상 근거를 인용한 절. 이미 슬라이드가 있는 절은 뺀다(taken)."""
    before = [t for t in timeline_secs if t <= sec]
    prev_start = max(before) if before else None
    if prev_start is not None:
        hit = next((i for i, secs in enumerate(section_video_secs) if i not in taken and prev_start in secs), None)
        if hit is not None:
            return hit
    # 5.6 2단계: video_secs의 **최댓값**이 sec 이하인 절만(006-C1-12 — "하나라도 sec 이하"가 아니라 그 절
    # 전체가 sec보다 앞선 구간이어야 한다. [100,1000]짜리 절은 sec=873에 포함되지 않음)
    cands = [(i, max(secs)) for i, secs in enumerate(section_video_secs) if i not in taken and secs and max(secs) <= sec]
    if cands:
        return max(cands, key=lambda x: x[1])[0]
    return next((i for i, has in enumerate(section_has_video) if has and i not in taken), None)


def place_unassigned(final: TopicPage, slide_candidates: list[str], timeline_secs: set[int],
                     slides_max: int, exclude: frozenset[int] = frozenset()) -> TopicPage:
    """작성자가 두지 않은 슬라이드 후보를 코드가 붙인다(5.6, D-30·D-34): 직전 구간 절 → 가까운 절 → 첫 영상 근거 절.
    exclude는 코드가 형식·수치 오류로 시각 요소를 통째로 비운 절(006-C1-20): 그 절은 후보로 다시 고르지 않는다."""
    secs = list(final.sections)
    placed = {int(m[1]) for s in secs if s.slide and (m := re.match(r"^sl:\d+@(\d+)$", s.slide))}
    taken = {i for i, s in enumerate(secs) if s.slide} | set(exclude)
    if len(placed) >= slides_max:
        return final
    section_video_secs = [s.video_secs for s in secs]
    section_has_video = [bool(s.video_secs) or any((r.startswith("vd:") or r.startswith("sl:"))
                         for p in s.paragraphs for r in p.refs) for s in secs]
    changed = False
    for cand in slide_candidates:
        if len(placed) >= slides_max:
            break
        m = re.match(r"^sl:\d+@(\d+)$", cand)
        if not m or int(m[1]) in placed:
            continue
        idx = place_candidate(int(m[1]), sorted(timeline_secs), section_video_secs, section_has_video, taken)
        if idx is None:
            continue
        secs[idx] = secs[idx].model_copy(update={"slide": cand})
        taken.add(idx)
        placed.add(int(m[1]))
        changed = True
    return final.model_copy(update={"sections": secs}) if changed else final


def render_frames(final: TopicPage, ms: dict[str, Any], attention: list[str]) -> TopicPage:
    """최종판 저장 직전에 슬라이드가 붙은 절마다 프레임을 만든다(5.6, D-34·D-39). 실패하면 slide=null + attention."""
    secs = list(final.sections)
    changed = False
    for i, s in enumerate(secs):
        if not s.slide:
            continue
        m = re.match(r"^sl:(\d+)@(\d+)$", s.slide)
        if not m:
            continue
        video_id = next((mm.key[3:] for mm in ms.values() if mm.item_id == int(m[1])), None)
        if video_id and ensure_frame(video_id, int(m[2])) is not None:
            continue
        attention.append(f"슬라이드 프레임 없음: {video_id or '?'}@{m[2]}")
        secs[i] = s.model_copy(update={"slide": None, "slide_caption": ""})
        changed = True
    return final.model_copy(update={"sections": secs}) if changed else final


def frame_path(video_id: str, sec: int) -> Path:
    return SLIDES_DIR / f"{video_id}_{sec}.jpg"


def ensure_frame(video_id: str, sec: int, timeout: int = 60) -> str | None:
    """프레임 jpg를 만들고(이미 있으면 그대로) 경로를 돌려준다. 영상 파일·ffmpeg 없거나 실패하면 None."""
    out = frame_path(video_id, sec)
    if out.is_file():
        return str(out)
    media = next(iter(sorted((MEDIA_ROOT / video_id).glob("media.*"))), None)  # 확장자가 여럿이면 이름 순 고정
    ffmpeg = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
    if media is None or not Path(ffmpeg).exists():
        return None
    SLIDES_DIR.mkdir(parents=True, exist_ok=True)
    try:
        r = subprocess.run(
            [ffmpeg, "-y", "-ss", str(sec), "-i", str(media), "-frames:v", "1",
             "-vf", "scale=960:540:force_original_aspect_ratio=decrease,pad=960:540:-1:-1:color=white",
             "-q:v", "4", str(out)],
            capture_output=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        out.unlink(missing_ok=True)  # 시간 초과로 죽었을 때 남은 부분 파일을 다음 실행이 정상 프레임으로 쓰지 않게
        return None
    if r.returncode == 0 and out.is_file():
        return str(out)
    out.unlink(missing_ok=True)
    return None
