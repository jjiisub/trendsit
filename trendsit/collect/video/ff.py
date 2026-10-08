"""ffmpeg/ffprobe 호출과 미디어 조회. 받기, 전사, 프레임, 작업 폴더가 함께 쓴다(스킬 media_util.py에서 옮김)."""

from __future__ import annotations

import json
import math
import platform
import re
import shutil
import subprocess
from importlib import metadata
from pathlib import Path
from typing import Any


class ProbeError(RuntimeError):
    pass


def run(cmd: list[str], timeout: float | None = None) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(cmd, capture_output=True, timeout=timeout)


def ffprobe_json(path: Path | str, extra_args: list[str] | None = None, timeout: float = 60) -> dict[str, Any]:
    cmd = ["ffprobe", "-v", "error", "-of", "json", *(extra_args or ["-show_format", "-show_streams"]), str(path)]
    try:
        proc = run(cmd, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        raise ProbeError(f"ffprobe 시간 초과: {path}") from e
    except FileNotFoundError as e:
        raise ProbeError("ffprobe 없음 (brew install ffmpeg)") from e
    if proc.returncode != 0:
        raise ProbeError(f"ffprobe 실패(exit {proc.returncode}): {proc.stderr.decode(errors='replace')[-300:]}")
    try:
        return json.loads(proc.stdout.decode(errors="replace") or "{}")
    except json.JSONDecodeError as e:
        raise ProbeError(f"ffprobe 출력 해석 실패: {e}") from e


def probe_media(path: Path | str) -> dict[str, Any]:
    """길이, 해상도, 오디오 유무. kind는 확장자가 아니라 실제 스트림으로(앨범아트는 영상으로 세지 않음)."""
    data = ffprobe_json(path)
    streams = data.get("streams") or []
    fmt = data.get("format") or {}
    video = [s for s in streams if s.get("codec_type") == "video"
             and not (s.get("disposition") or {}).get("attached_pic")]
    durations = []
    for d in [fmt.get("duration"), *(s.get("duration") for s in streams)]:
        try:
            durations.append(float(d))
        except (TypeError, ValueError):
            pass
    v0 = video[0] if video else {}
    return {"kind": "video" if video else "audio", "duration": max([d for d in durations if d > 0], default=0.0),
            "has_audio": any(s.get("codec_type") == "audio" for s in streams),
            "width": int(v0["width"]) if v0.get("width") else None,
            "height": int(v0["height"]) if v0.get("height") else None}


def ceil_sec(seconds: float) -> int:
    """길이는 올림 정수(프레임 t ≤ duration_sec 계약이 마지막 프레임에서 깨지지 않게)."""
    return int(math.ceil(seconds - 1e-6)) if seconds > 0 else 0


def have_tools() -> list[str]:
    """없는 시스템 도구 이름."""
    return [t for t in ("ffmpeg", "ffprobe") if shutil.which(t) is None]


def versions() -> dict[str, str]:
    out: dict[str, str] = {"python": platform.python_version(), "platform": f"{platform.system()}-{platform.machine()}"}
    for pkg in ("mlx-whisper", "mlx", "yt-dlp"):
        try:
            out[pkg] = metadata.version(pkg)
        except metadata.PackageNotFoundError:
            pass
    if shutil.which("ffmpeg"):
        first = run(["ffmpeg", "-version"], timeout=10).stdout.decode(errors="replace").split("\n")[0]
        m = re.search(r"version (\S+)", first)
        out["ffmpeg"] = m.group(1) if m else first[:40]
    return out


def device() -> str:
    """전사 장치. mlx가 있으면 그 기본 장치(맥 GPU = Metal/MPS), 없으면 cpu."""
    try:
        import mlx.core as mx  # type: ignore[import-not-found]

        return str(mx.default_device())
    except Exception:  # noqa: BLE001 - mlx가 없거나 맥이 아니면 cpu로 표시만
        return "cpu"
