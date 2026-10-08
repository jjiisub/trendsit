"""media_process(): 영상 처리 지시 하나 → MediaResult. 전사(GPU)와 프레임 1차 추출(CPU)을 동시에(스킬 방식).

LLM 판독은 여기서 하지 않는다(전사가 끝난 뒤 파이프라인이. 로컬 모델 전환 때 메모리 순서 유지).
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ...core.artifacts_video import MediaEnv, MediaResult, VideoQueueItem
from ...core.config_video import ModeSettings, VideoConfig
from . import cues, ff, source
from . import transcribe as tr
from .frames import FrameEngine, FrameError
from .workspace import Workspace


class MediaSkipped(RuntimeError):
    """처리하지 않고 넘어감(예: captions인데 수동 자막 없음). 실패가 아니다."""


class MediaFailed(RuntimeError):
    """받기나 전사가 재시도 뒤에도 실패."""


@dataclass
class Deps:
    """바깥 의존(네트워크, GPU). 테스트는 가짜로 바꾼다."""

    fetch_info: Callable[[str], dict[str, Any]] = source.fetch_info
    download: Callable[..., dict[str, Any]] = source.download
    download_captions: Callable[[str, str, Path], Path] = source.download_manual_captions
    transcribe: Callable[..., dict[str, Any]] = tr.transcribe
    to_wav: Callable[..., Path] = tr.to_wav
    tail_check: bool = True
    sleep: Callable[[float], None] = field(default=time.sleep)


@dataclass
class Overrides:
    """영상별로 사람이 고르는 설정(mode 안에서만. mode를 올리지는 않는다)."""

    frames: str | None = None  # auto | full
    frames_res: int | None = None
    lang: str | None = None


def resolve_span(start_sec: int | None, end_sec: int | None, duration: float, max_span: int
                 ) -> tuple[float, float, str | None]:
    """처리 구간과 이유. 지정이 없으면 처음부터, 끝은 최대 max_span(60분) 뒤까지(V4)."""
    lo = float(start_sec or 0)
    if lo >= duration:
        raise MediaFailed(f"start_sec({lo:.0f})가 영상 길이({duration:.0f}초) 이상")
    hi = min(float(end_sec), duration) if end_sec is not None else duration
    note = None
    if hi - lo > max_span:
        hi = lo + max_span
        note = (f"{duration / 60:.0f}분 영상 중 {lo / 60:.0f}~{hi / 60:.0f}분만 처리(상한 {max_span // 60}분)"
                if end_sec is None else f"지정 구간이 {max_span // 60}분을 넘어 {hi / 60:.0f}분까지로 자름")
    elif start_sec is not None or end_sec is not None:
        note = f"지정 구간 {lo:.0f}~{hi:.0f}초 처리"
    return lo, hi, note


def media_process(item: VideoQueueItem, cfg: VideoConfig, media_root: Path, *, deps: Deps | None = None,
                  overrides: Overrides | None = None) -> MediaResult:
    if item.mode == "skip":
        raise MediaSkipped(f"mode skip: {item.reason}")
    deps, ov = deps or Deps(), overrides or Overrides()
    settings = cfg.modes.get(item.mode)
    if settings.transcript == "manual":
        return _captions(item, cfg, media_root, deps)
    return _whisper(item, cfg, settings, media_root, deps, ov)


def _env(cfg: VideoConfig, timings: dict[str, float], whisper: bool) -> MediaEnv:
    return MediaEnv(device=ff.device() if whisper else "none", whisper_model=cfg.whisper_model if whisper else None,
                    versions=ff.versions(), timings_sec={k: round(v, 2) for k, v in timings.items()})


# ---------- captions: 업로더 수동 자막만 ----------
def _captions(item: VideoQueueItem, cfg: VideoConfig, media_root: Path, deps: Deps) -> MediaResult:
    started = time.monotonic()
    info = deps.fetch_info(item.video_id)
    lang = source.manual_caption_lang(info, cfg.caption_langs)
    if lang is None:
        # whisper로 올리지 않는다(CONTRACTS 1장). 자동 자막은 있어도 쓰지 않는다
        raise MediaSkipped(f"captions: 수동 자막({', '.join(cfg.caption_langs)}) 없음. whisper로 바꾸지 않고 건너뜀")
    duration = float(info.get("duration") or 0)
    if duration <= 0:
        raise MediaFailed("영상 길이를 알 수 없음")
    lo, hi, note = resolve_span(item.start_sec, item.end_sec, duration, cfg.max_span_sec)
    ws = Workspace(media_root, item.video_id)
    staging = ws.reset_staging()
    try:
        vtt = deps.download_captions(item.video_id, lang, staging)
        raw = source.parse_vtt(vtt.read_text(encoding="utf-8"))
    finally:
        ws.clear_staging()
    segments, _fixes = tr.normalize_segments(raw, 0.0, lo, hi)
    sig = tr.quality_signals(segments, None)
    quality, reasons = tr.judge_quality(sig)
    warnings = [note] if note else []
    if quality != "ok":
        warnings.append(f"자막 품질 {quality}: {' / '.join(reasons)}")
    return MediaResult(
        video_id=item.video_id, mode=item.mode, title=(info.get("title") or "").strip() or item.video_id,
        duration_sec=ff.ceil_sec(duration), span={"start": lo, "end": hi}, language=lang,
        transcript_source="manual", transcript_quality=quality, quality_signals=sig,
        segments=[{"start": round(s["start"], 3), "end": round(s["end"], 3), "text": s["text"]} for s in segments],
        warnings=warnings, work_dir=str(ws.dir), env=_env(cfg, {"total": time.monotonic() - started}, False))


# ---------- whisper, whisper+slides ----------
def _acquire(item: VideoQueueItem, cfg: VideoConfig, ws: Workspace, need_video: bool, deps: Deps
             ) -> tuple[Path, str]:
    cached = ws.cached_media(need_video, tail_check=deps.tail_check)
    if cached is not None:
        ws.touch()
        return cached, ws.load_meta().get("title") or item.video_id
    staging = ws.reset_staging()
    try:
        dl = deps.download(item.video_id, staging, need_video=need_video, max_height=cfg.download_max_height)
        probe = ff.probe_media(dl["path"])
        final = ws.commit_media(Path(dl["path"]), probe["duration"] or dl.get("declared_duration") or 0,
                                probe["kind"], {"title": dl.get("title") or item.video_id, "video_id": item.video_id})
        return final, dl.get("title") or item.video_id
    except Exception as e:
        ws.clear_staging()
        ws.discard_if_empty()
        raise MediaFailed(f"받기 실패: {e}") from e


def _whisper(item: VideoQueueItem, cfg: VideoConfig, settings: ModeSettings, media_root: Path, deps: Deps,
             ov: Overrides) -> MediaResult:
    timings: dict[str, float] = {}
    started = time.monotonic()
    ws = Workspace(media_root, item.video_id)
    need_video = settings.frames != "off"
    media, title = _acquire(item, cfg, ws, need_video, deps)
    timings["download"] = time.monotonic() - started
    probe = ff.probe_media(media)
    duration = float(probe["duration"])
    if duration <= 0:
        raise MediaFailed("받은 파일의 길이를 확인할 수 없음")
    lo, hi, note = resolve_span(item.start_sec, item.end_sec, duration, cfg.max_span_sec)
    warnings = [note] if note else []
    if not probe["has_audio"]:
        raise MediaFailed("오디오 스트림 없음(전사 불가)")

    engine: FrameEngine | None = None
    frames_error: str | None = None
    if need_video and probe["kind"] != "video":
        frames_error = "영상 스트림 없음(프레임 생략)"
    elif need_video:
        engine = FrameEngine(media, ws.new_frames_dir(), duration, width=probe["width"], height=probe["height"],
                             tier=ov.frames or settings.frames, cap=settings.frames_cap,
                             res=ov.frames_res or settings.frames_res, lo=lo, hi=hi)

    thread_error: dict[str, str] = {}
    frames_started = time.monotonic()

    def pass1() -> None:
        try:
            engine.pass1()  # type: ignore[union-attr]
        except BaseException as e:  # noqa: BLE001 - 스레드 밖으로 새지 않게
            thread_error["err"] = f"프레임 추출 실패: {e}"
        timings["frames_pass1"] = time.monotonic() - frames_started

    thread = threading.Thread(target=pass1, name="frames-pass1", daemon=True) if engine else None
    if thread:
        thread.start()

    t0 = time.monotonic()
    tdata, last_error = None, None
    try:
        for _attempt in range(2):  # 전사 1회 재시도
            try:
                wav = deps.to_wav(media, ws.audio_path, lo, hi)
                tdata = deps.transcribe(wav, model=cfg.whisper_model, lo=lo, hi=hi, lang=ov.lang)
                break
            except Exception as e:  # noqa: BLE001
                last_error = e
    finally:
        ws.drop_audio()
    timings["transcribe"] = time.monotonic() - t0
    if thread:
        thread.join()
    if tdata is None:
        if engine:
            engine.discard()
        raise MediaFailed(f"전사 실패(2회): {last_error}")
    if "err" in thread_error and engine:
        frames_error = thread_error["err"]
        engine.discard()
        engine = None

    segments = tdata["segments"]
    quality = tdata["transcript_quality"]
    warnings += tdata["warnings"]
    frames: list[dict[str, Any]] = []
    frames_meta = None
    if engine is not None:
        t1 = time.monotonic()
        try:
            if quality != "ok" and engine.bump_for_low_quality():
                warnings.append(f"전사 품질 {quality} → 프레임 예산 상향(cap={engine.cap}). 정보가 화면에만 있을 수 있음")
            budget = max(0, engine.cap - len(engine.frames))
            if segments and budget > 0:
                times, w = cues.select_cues(segments, tdata["language"], budget=budget, lo=lo, hi=hi)
                warnings += w
                engine.add_times([(t, "transcript-cue") for t in times])
            engine.topup()
            frames, frames_meta = engine.result()
            frames = cues.attach_spoken(frames, segments)
            for f in frames:
                f["path"] = ws.rel(f["path"])
            warnings += engine.warnings
        except (FrameError, OSError, RuntimeError) as e:
            frames_error, frames, frames_meta = f"프레임 후처리 실패: {e}", [], None
            engine.discard()
        timings["frames_post"] = time.monotonic() - t1
    timings["total"] = time.monotonic() - started

    return MediaResult(
        video_id=item.video_id, mode=item.mode, title=title, duration_sec=ff.ceil_sec(duration),
        span={"start": lo, "end": hi}, language=tdata["language"], transcript_source="whisper",
        transcript_quality=quality, quality_signals=tdata["quality_signals"], segments=segments, frames=frames,
        frames_meta=frames_meta, frames_error=frames_error, warnings=warnings, work_dir=str(ws.dir),
        env=_env(cfg, timings, True))
