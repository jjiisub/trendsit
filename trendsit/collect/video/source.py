"""yt-dlp로 받기. 영상 하나만(재생목록·채널 URL 거부), 1080p 이하, 실패하면 1회 재시도(스킬 media_source.py 참고).

자막은 업로더가 올린 수동 자막 트랙(info["subtitles"])만 쓴다. 자동 자막(automatic_captions)은 읽지도 받지도 않는다(V2).
"""

from __future__ import annotations

import re
import shutil
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from ...core.artifacts_video import VIDEO_ID
from ..youtube import WATCH

YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be", "www.youtu.be"}
# 재생목록, 채널, 검색은 조용히 첫 영상만 받는 대신 거부한다
COLLECTION_PATH = re.compile(r"^/(playlist|channel/|c/|user/|@|feed/|results$|shorts/?$)", re.IGNORECASE)
JS_RUNTIMES = ("deno", "node", "bun")  # yt-dlp가 서명을 풀 때 필요. 없으면 영상 포맷이 403
NOT_CAPTION_TRACKS = {"live_chat"}


class SourceError(RuntimeError):
    pass


def parse_video_ref(ref: str) -> str:
    """11자 id 또는 개별 영상 URL → video_id. 재생목록·채널 URL은 거부."""
    s = ref.strip()
    if re.match(VIDEO_ID, s):
        return s
    u = urlparse(s if "://" in s else "https://" + s)
    host = (u.hostname or "").lower()
    if host not in YOUTUBE_HOSTS:
        raise SourceError(f"유튜브 영상 id나 URL이 아님: {ref!r}")
    if COLLECTION_PATH.match(u.path or "/"):
        raise SourceError("재생목록·채널 URL은 받지 않음(영상 하나의 URL이나 id)")
    vid = ""
    if host.endswith("youtu.be"):
        vid = u.path.strip("/").split("/")[0]
    else:
        vid = parse_qs(u.query).get("v", [""])[0]
        m = re.match(r"^/(shorts|embed|live|v)/([^/?#]+)", u.path or "")
        vid = vid or (m.group(2) if m else "")
    if not re.match(VIDEO_ID, vid):
        raise SourceError(f"URL에서 영상 id를 찾지 못함: {ref!r}")
    return vid


def js_runtimes() -> dict[str, dict[str, str]] | None:
    found = {name: {"path": p} for name in JS_RUNTIMES if (p := shutil.which(name))}
    return found or None


def format_selectors(need_video: bool, max_height: int) -> list[str]:
    """두 번째는 재시도용. 일시적 403이 많고, 코덱 제약이면 avc1 강제로 넘어간다."""
    if not need_video:
        return ["bestaudio/best", "bestaudio/best"]
    h = int(max_height)
    return [f"bestvideo[height<={h}]+bestaudio/best[height<={h}]",
            f"bestvideo[vcodec^=avc1][height<={h}]+bestaudio/best[height<={h}]/best"]


class _QuietLogger:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def debug(self, msg: str) -> None:
        pass

    def info(self, msg: str) -> None:
        pass

    def warning(self, msg: str) -> None:
        self.messages.append(msg)

    def error(self, msg: str) -> None:
        self.messages.append(msg)


YdlFactory = Callable[[dict[str, Any]], Any]


def _ydl(opts: dict[str, Any]) -> Any:
    import yt_dlp  # type: ignore[import-untyped]

    return yt_dlp.YoutubeDL(opts)


def _base_opts() -> dict[str, Any]:
    opts: dict[str, Any] = {"quiet": True, "no_warnings": True, "noprogress": True, "noplaylist": True,
                            "logger": _QuietLogger(), "retries": 5, "extractor_retries": 3}
    if runtimes := js_runtimes():
        opts["js_runtimes"] = runtimes
    return opts


def fetch_info(video_id: str, ydl: YdlFactory = _ydl) -> dict[str, Any]:
    """메타데이터만(다운로드 없음): 제목, 길이, 챕터, 수동 자막 트랙."""
    with ydl(_base_opts() | {"skip_download": True}) as y:
        info = y.extract_info(WATCH.format(id=video_id), download=False)
    if not info or info.get("_type") == "playlist":
        raise SourceError("영상 하나로 해석되지 않음")
    return info


def download(video_id: str, staging: Path, *, need_video: bool, max_height: int,
             ydl: YdlFactory = _ydl) -> dict[str, Any]:
    """staging 폴더에 받는다(최종 이름 바꾸기는 Workspace.commit_media). 실패하면 1회 재시도."""
    errors: list[str] = []
    for selector in format_selectors(need_video, max_height):
        for leftover in staging.iterdir():
            leftover.unlink(missing_ok=True)  # 실패한 부분 파일을 다음 시도로 넘기지 않음
        opts = _base_opts() | {"format": selector, "outtmpl": str(staging / f"dl_{uuid.uuid4().hex[:8]}.%(ext)s"),
                               "overwrites": True}
        if need_video:
            opts["merge_output_format"] = "mp4"
        try:
            with ydl(opts) as y:
                info = y.extract_info(WATCH.format(id=video_id), download=True)
            path = _locate(info, staging)
            if path is None:
                raise SourceError("받은 파일을 찾지 못함")
            return {"path": path, "title": (info.get("title") or "").strip(), "info": info,
                    "declared_duration": float(info.get("duration") or 0)}
        except Exception as e:  # noqa: BLE001 - yt-dlp 오류 종류가 많다. 이유를 모아 두고 재시도
            errors.append(str(e).strip()[:200])
    raise SourceError(f"받기 실패(2회): {' / '.join(errors)}")


def _locate(info: dict[str, Any], staging: Path) -> Path | None:
    for d in info.get("requested_downloads") or []:
        for k in ("filepath", "_filename"):
            if d.get(k) and Path(d[k]).is_file():
                return Path(d[k])
    files = [p for p in staging.iterdir() if p.is_file() and not p.name.endswith((".part", ".ytdl", ".temp"))]
    return max(files, key=lambda p: p.stat().st_size) if files else None


# ---------- 수동 자막 (captions mode) ----------
def manual_caption_lang(info: dict[str, Any], langs: list[str]) -> str | None:
    """업로더 자막 트랙 중 원하는 언어(앞이 우선). 'ko-KR'처럼 지역이 붙은 것도 언어로 맞춘다."""
    tracks = [k for k in (info.get("subtitles") or {}) if k not in NOT_CAPTION_TRACKS]
    for want in langs:
        for k in tracks:
            if k == want or k.split("-")[0] == want:
                return k
    return None


def download_manual_captions(video_id: str, lang: str, staging: Path, ydl: YdlFactory = _ydl) -> Path:
    opts = _base_opts() | {"skip_download": True, "writesubtitles": True, "writeautomaticsub": False,
                           "subtitleslangs": [lang], "subtitlesformat": "vtt",
                           "outtmpl": str(staging / "sub.%(ext)s")}
    with ydl(opts) as y:
        y.extract_info(WATCH.format(id=video_id), download=True)
    found = sorted(staging.glob("sub*.vtt"))
    if not found:
        raise SourceError(f"수동 자막({lang})을 받지 못함")
    return found[0]


_CUE_TIME = re.compile(r"(?:(\d+):)?(\d{1,2}):(\d{2})[.,](\d{3})")


def _vtt_time(s: str) -> float:
    m = _CUE_TIME.match(s.strip())
    if not m:
        raise ValueError(s)
    h, mnt, sec, ms = m.groups()
    return int(h or 0) * 3600 + int(mnt) * 60 + int(sec) + int(ms) / 1000


def parse_vtt(text: str) -> list[dict[str, Any]]:
    """WebVTT → segments(start, end, text). 태그를 걷고, 같은 문장이 이어 나오는 롤업 중복은 합친다."""
    out: list[dict[str, Any]] = []
    for block in re.split(r"\n\s*\n", text.replace("\r\n", "\n")):
        lines = [ln for ln in block.strip().split("\n") if ln.strip()]
        idx = next((i for i, ln in enumerate(lines) if "-->" in ln), None)
        if idx is None:
            continue
        a, _, b = lines[idx].partition("-->")
        try:
            start, end = _vtt_time(a), _vtt_time(b.split()[0])
        except (ValueError, IndexError):
            continue
        body = " ".join(re.sub(r"<[^>]+>", "", ln).strip() for ln in lines[idx + 1:]).strip()
        if not body:
            continue
        if out and out[-1]["text"] == body:
            out[-1]["end"] = max(out[-1]["end"], end)
            continue
        out.append({"start": start, "end": max(start, end), "text": body})
    return out
