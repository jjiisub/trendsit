"""슬라이드 후보·배치·프레임(S6-1 5.6, D-30·D-34·D-39). ffmpeg는 외부 실행 파일(subprocess)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

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
    cands = [(i, max(s for s in secs if s <= sec)) for i, secs in enumerate(section_video_secs)
             if i not in taken and any(s <= sec for s in secs)]
    if cands:
        return max(cands, key=lambda x: x[1])[0]
    return next((i for i, has in enumerate(section_has_video) if has and i not in taken), None)


def frame_path(video_id: str, sec: int) -> Path:
    return SLIDES_DIR / f"{video_id}_{sec}.jpg"


def ensure_frame(video_id: str, sec: int, timeout: int = 60) -> str | None:
    """프레임 jpg를 만들고(이미 있으면 그대로) 경로를 돌려준다. 영상 파일·ffmpeg 없거나 실패하면 None."""
    out = frame_path(video_id, sec)
    if out.is_file():
        return str(out)
    media = next(iter((MEDIA_ROOT / video_id).glob("media.*")), None)
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
        return None
    return str(out) if r.returncode == 0 and out.is_file() else None
