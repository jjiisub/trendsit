"""작업 폴더 data/media/<video_id>: 받은 영상, 프레임 이미지. git 제외, 7일 뒤 정리(V9).

스킬 workspace.py에서 옮김: 원자적 커밋(임시 폴더에 받고 성공한 뒤에만 최종 이름으로), 재사용 전 검사,
작업 폴더 루트 밖은 지우지 않는 방어. DB에는 텍스트만 남으므로 이 폴더는 언제 지워도 된다.
"""

from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path
from typing import Any

from .ff import ProbeError, ffprobe_json

META = "meta.json"
STAGING = ".staging"
PARTIAL_SUFFIXES = (".part", ".ytdl", ".temp")


class Workspace:
    def __init__(self, root: Path, video_id: str):
        if not video_id or "/" in video_id or video_id in (".", ".."):
            raise ValueError(f"작업 폴더 키가 올바르지 않음: {video_id!r}")
        self.root = root.resolve()
        self.dir = self.root / video_id
        self.meta_path = self.dir / META
        self.staging: Path | None = None

    # ---------- 메타 ----------
    def load_meta(self) -> dict[str, Any]:
        try:
            data = json.loads(self.meta_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def save_meta(self, meta: dict[str, Any]) -> None:
        """임시 파일 → 이름 바꾸기. 임시 이름에 pid를 넣어 동시 실행끼리 덮어쓰지 않게."""
        self.dir.mkdir(parents=True, exist_ok=True)
        tmp = self.meta_path.with_name(f"{META}.{os.getpid()}.tmp")
        tmp.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, self.meta_path)

    def touch(self) -> None:
        meta = self.load_meta()
        if meta:
            meta["last_used_at"] = time.time()
            self.save_meta(meta)

    # ---------- 경로 ----------
    @property
    def audio_path(self) -> Path:
        return self.dir / "audio.wav"

    def new_frames_dir(self) -> Path:
        """실행마다 따로(frames/<run>). 같은 영상을 다시 처리해도 앞 결과의 프레임 경로가 살아 있게."""
        path = self.dir / "frames" / f"{int(time.time())}-{os.getpid()}"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def rel(self, path: Path | str) -> str:
        p = Path(path).resolve()
        self.assert_inside(p)
        return p.relative_to(self.dir.resolve()).as_posix()

    def assert_inside(self, path: Path | str) -> None:
        """루트 밖 경로는 만들지도 지우지도 않는다(심볼릭 링크 우회 포함)."""
        target = Path(os.path.realpath(path))
        root = Path(os.path.realpath(self.root))
        if target != root and root not in target.parents:
            raise RuntimeError(f"작업 폴더 루트 밖 경로: {path}")

    # ---------- 재사용 ----------
    def cached_media(self, need_video: bool, tail_check: bool = True) -> Path | None:
        """싼 검사부터: 미완료 파일 → 완료 표시 → 크기 → 끝부분 읽기. 하나라도 어긋나면 다시 받는다."""
        meta = self.load_meta()
        name = meta.get("media_file")
        if not name or not meta.get("complete"):
            return None
        if self.dir.exists() and any(p.name.endswith(PARTIAL_SUFFIXES) for p in self.dir.iterdir()):
            return None
        media = self.dir / name
        if not media.is_file() or (need_video and meta.get("media_kind") != "video"):
            return None
        if media.stat().st_size != meta.get("size"):
            return None
        duration = float(meta.get("duration") or 0)
        if tail_check and duration > 0 and not _tail_readable(media, duration, meta.get("media_kind")):
            return None  # faststart mp4는 반만 받아도 길이를 그대로 보고하므로 끝을 직접 읽어 본다
        return media

    # ---------- 원자적 커밋 ----------
    def reset_staging(self) -> Path:
        path = self.dir / STAGING / f"{os.getpid()}-{int(time.time() * 1000)}"
        self.assert_inside(path.parent.parent)
        shutil.rmtree(path, ignore_errors=True)
        path.mkdir(parents=True)
        self.staging = path
        return path

    def clear_staging(self) -> None:
        if self.staging is not None:
            self.assert_inside(self.staging)
            shutil.rmtree(self.staging, ignore_errors=True)
            self.staging = None

    def commit_media(self, staged: Path, duration: float, media_kind: str, extra: dict[str, Any]) -> Path:
        """이름 바꾸기 → 완료 표시 순서. 반대로 하면 '완료인데 파일 없음' 상태가 생긴다."""
        if not staged.is_file():
            raise RuntimeError(f"커밋할 파일 없음: {staged}")
        final = self.dir / ("media" + (staged.suffix.lower() or ".bin"))
        self.assert_inside(final)
        meta = self.load_meta()
        prev = meta.get("media_file")
        if meta.get("complete"):
            meta["complete"] = False
            self.save_meta(meta)
        os.replace(staged, final)
        if prev and prev != final.name:
            (self.dir / prev).unlink(missing_ok=True)
        now = time.time()
        meta.update({"media_file": final.name, "media_kind": media_kind, "size": final.stat().st_size,
                     "duration": float(duration), "committed_at": now, "last_used_at": now, "complete": True,
                     **extra})
        self.save_meta(meta)
        self.clear_staging()
        return final

    def drop_audio(self) -> None:
        self.audio_path.unlink(missing_ok=True)

    def discard_if_empty(self) -> None:
        """받기에 실패해 아무것도 남지 않은 폴더는 지운다(빈 폴더가 쌓이지 않게)."""
        if not self.dir.is_dir() or self.load_meta().get("complete"):
            return
        if any(p.suffix == ".jpg" or p.name.startswith("media.") for p in self.dir.rglob("*")):
            return
        self.assert_inside(self.dir)
        shutil.rmtree(self.dir, ignore_errors=True)


def _tail_readable(path: Path, duration: float, media_kind: str | None) -> bool:
    stream = "a:0" if media_kind == "audio" else "v:0"
    try:
        data = ffprobe_json(path, ["-select_streams", stream, "-read_intervals",
                                   f"{max(0.0, duration - 1.5):.3f}%+#8", "-show_packets"], timeout=30)
    except ProbeError:
        return False
    return bool(data.get("packets"))


def entry_time(path: Path) -> float:
    """마지막 사용 시각: meta.json의 last_used_at → committed_at → 폴더 수정 시각."""
    try:
        meta = json.loads((path / META).read_text(encoding="utf-8"))
        for k in ("last_used_at", "committed_at"):
            if isinstance(meta.get(k), int | float):
                return float(meta[k])
    except (OSError, json.JSONDecodeError, AttributeError):
        pass
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def purge(root: Path, older_than_days: float, now: float | None = None) -> dict[str, Any]:
    """older_than_days보다 오래 쓰지 않은 작업 폴더만 지운다. DB는 건드리지 않는다."""
    root = root.resolve()
    result: dict[str, Any] = {"root": str(root), "removed": [], "kept": [], "freed_bytes": 0}
    if not root.is_dir():
        return result
    cutoff = (now if now is not None else time.time()) - older_than_days * 86400
    real_root = Path(os.path.realpath(root))
    for path in sorted(p for p in root.iterdir() if p.is_dir()):
        if entry_time(path) >= cutoff:
            result["kept"].append(path.name)
            continue
        if real_root not in Path(os.path.realpath(path)).parents:
            continue  # 루트 밖을 가리키는 링크
        result["freed_bytes"] += sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
        shutil.rmtree(path, ignore_errors=True)
        result["removed"].append(path.name)
    return result
