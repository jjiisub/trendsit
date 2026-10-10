"""영상 분석가 파이프라인: 단계는 고정(1차 처리 → 계약 검사 → 판독 → 대조 → 요약 → 저장), 판단 지점만 LLM.

mode는 편집장 계획이 정하고 여기서 올리지 않는다. 대체 동작(CONTRACTS 1장, S4_TASK 5장):
- 슬라이드 판독이 전부 실패 → 전사 결과만으로 요약(status partial)
- 받기·전사 실패 → 영상 건너뜀 + fetch_log 실패 기록
- 전사를 쓸 수 없고 판독도 없음 → LLM을 부르지 않고 "내용 없음" + attention
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from ..collect.video import contract
from ..collect.video.process import Deps, MediaFailed, MediaSkipped, Overrides, media_process, resolve_span
from ..core.artifacts import Document
from ..core.artifacts_video import (
    FRAME_PRIORITY,
    NO_CONTENT,
    DigestSlide,
    Frame,
    MediaResult,
    SlideInput,
    SlideReading,
    VideoDigest,
    VideoQueueItem,
    VideoSummary,
    VideoSummaryInput,
)
from ..core.budget import BudgetExceeded, PriceUnknown
from ..core.config_video import VideoConfig
from ..core.context import Ctx
from ..core.db import KST
from ..core.images import ImageFile
from ..core.llm import LLMError
from ..core.role import RoleFailed, load_role, run_role
from . import store
from .align import AlignResult, align

SLIDE_DOC_CHARS = 800  # 요약 입력에 넣는 판독 글자 상한(프레임당)


@dataclass
class VideoOutcome:
    video_id: str
    status: str  # ok / partial / skipped / failed
    note: str = ""
    digest: VideoDigest | None = None
    media: MediaResult | None = None
    readings: list[tuple[Frame, SlideReading | None]] = field(default_factory=list)
    aligned: AlignResult | None = None
    summary: VideoSummary | None = None


def _step(ctx: Ctx, text: str, *, attention: bool = False, error: str | None = None, detail: Any = None,
          role: str = "video_analyst") -> None:
    ctx.tracer.step(kind="code", role=role, text=text, attention=attention, error=error, detail=detail)


def transcript_document(media: MediaResult, item_id: int, usable: bool) -> Document:
    text = "\n".join(f"[{round(s.start)}] {s.text}" for s in media.segments) if usable else ""
    return Document(id=f"vd:{item_id}@{round(media.span.start)}", source=f"전사({media.transcript_source})",
                    text=text)


def slide_documents(readings: list[tuple[Frame, SlideReading | None]], item_id: int) -> list[Document]:
    """글자가 있는 판독만, 같은 슬라이드를 여러 번 잡았으면 처음 하나만."""
    docs, seen = [], set()
    for f, r in sorted(readings, key=lambda x: x[0].t):
        if r is None or not r.ocr_text.strip():
            continue
        key = " ".join(r.ocr_text.lower().split())
        if key in seen:
            continue
        seen.add(key)
        docs.append(Document(id=f"vd:{item_id}@{round(f.t)}", source="슬라이드 판독", title=r.title or None,
                             text=r.ocr_text[:SLIDE_DOC_CHARS]))
    return docs


def summary_input(media: MediaResult, readings: list[tuple[Frame, SlideReading | None]], aligned: AlignResult,
                  info: dict[str, Any]) -> VideoSummaryInput:
    """요약 입력 조립(평가 픽스처도 이 함수로 같은 입력을 다시 만든다)."""
    item_id, usable = info["item_id"], media.transcript_quality == "ok"
    span_hi = round(media.span.end)
    return VideoSummaryInput(
        item_id=item_id, transcript=transcript_document(media, item_id, usable),
        transcript_quality=media.transcript_quality, slides=slide_documents(readings, item_id),
        slide_only_facts=aligned.slide_only, title=info["title"] or media.title, duration_sec=media.duration_sec,
        span_start=round(media.span.start), span_end=span_hi,
        chapters=[c for c in info["chapters"] if c["sec"] <= span_hi], mode=media.mode)


def read_slides(media: MediaResult, ctx: Ctx) -> tuple[list[tuple[Frame, SlideReading | None]], dict[str, int]]:
    """프레임마다 판독 1회. 우선순위 transcript-cue → scene-change → first-frame → uniform(V6)."""
    role = load_role("video_slide", ctx.models)
    stats = {"read": 0, "failed": 0, "missing": 0}
    out: list[tuple[Frame, SlideReading | None]] = []
    for f in sorted(media.frames, key=lambda f: (FRAME_PRIORITY[f.reason], f.t)):
        path = Path(media.work_dir) / f.path
        if not path.is_file():  # 7일 정리로 사라졌거나 픽스처에 없는 프레임
            stats["missing"] += 1
            out.append((f, None))
            continue
        try:
            r = run_role(role, SlideInput(image=ImageFile(path=str(path)), sec=round(f.t),
                                          spoken_text=f.spoken_text), ctx)
        except (RoleFailed, LLMError) as e:  # ImageError는 LLMError 계열
            stats["failed"] += 1
            _step(ctx, f"{round(f.t)}초 판독 실패", attention=True, error=str(e), role="video_slide")
            out.append((f, None))
            continue
        stats["read"] += 1
        out.append((f, r))
    return sorted(out, key=lambda x: x[0].t), stats


def analyze(item: VideoQueueItem, ctx: Ctx, cfg: VideoConfig, media_root: Path, *, deps: Deps | None = None,
            overrides: Overrides | None = None, media: MediaResult | None = None) -> VideoOutcome:
    """영상 처리 지시 하나. ctx.tracer는 이 영상 전용 run(영상마다 run 1개)."""
    db, run_id = ctx.db, ctx.tracer.run_id
    info = store.video_item(db, item.video_id)
    base = {"video_id": item.video_id, "mode": item.mode, "start_sec": item.start_sec, "end_sec": item.end_sec,
            "reason": item.reason, "run_id": run_id}
    if info is None:
        note = "S1 videos에 없는 영상(trendsit collect 먼저)"
        _step(ctx, note, attention=True)
        store.save_run(db, item_id=None, status="failed", note=note, **base)
        return VideoOutcome(item.video_id, "failed", note)
    item_id = info["item_id"]
    if item.mode == "skip":
        _step(ctx, f"건너뜀(mode skip): {item.reason}")
        store.save_run(db, item_id=item_id, status="skipped", note=item.reason, **base)
        return VideoOutcome(item.video_id, "skipped", item.reason)
    if media is not None and media.mode != item.mode:  # 저장한 결과로 mode를 올리거나 바꾸지 않는다(CONTRACTS 1장)
        note = f"저장한 1차 처리 결과의 mode({media.mode})가 처리 지시({item.mode})와 다름"
        _step(ctx, note, attention=True)
        store.save_run(db, item_id=item_id, status="failed", note=note, **base)
        return VideoOutcome(item.video_id, "failed", note)
    try:
        return _analyze(item, ctx, cfg, media_root, info, base, deps, overrides, media)
    except (BudgetExceeded, PriceUnknown) as e:
        _step(ctx, "예산 상한으로 중단", attention=True, error=str(e))
        store.save_run(db, item_id=item_id, status="failed", note=f"예산 상한: {e}", **base)
        raise


def _analyze(item: VideoQueueItem, ctx: Ctx, cfg: VideoConfig, media_root: Path, info: dict[str, Any],
             base: dict[str, Any], deps: Deps | None, overrides: Overrides | None,
             media: MediaResult | None) -> VideoOutcome:
    db, run_id, item_id = ctx.db, ctx.tracer.run_id, info["item_id"]
    live = media is None
    # ---------- 1차 처리 ----------
    if media is None:
        try:
            media = media_process(item, cfg, media_root, deps=deps, overrides=overrides)
        except MediaSkipped as e:
            _step(ctx, f"건너뜀: {e}")
            store.save_run(db, item_id=item_id, status="skipped", note=str(e), **base)
            return VideoOutcome(item.video_id, "skipped", str(e))
        except MediaFailed as e:
            _step(ctx, "1차 처리 실패, 영상 건너뜀", attention=True, error=str(e))
            db.log_fetch(run_id, info["source_id"], datetime.now(KST).date().isoformat(), "failed",
                         error=str(e)[:500], detail={"video_id": item.video_id, "stage": "video_analyst"})
            store.save_run(db, item_id=item_id, status="failed", note=str(e)[:500], **base)
            return VideoOutcome(item.video_id, "failed", str(e))
        # 작업 폴더에 1차 처리 결과를 남겨 판독 이후만 다시 돌릴 수 있게(video run --from-json, 7일 정리와 함께 지워짐)
        (Path(media.work_dir) / "media_result.json").write_text(media.model_dump_json(indent=1), encoding="utf-8")
    t = media.env.timings_sec
    _step(ctx, f"받기 {t.get('download', 0):.0f}초", detail={"title": media.title, "duration_sec": media.duration_sec,
                                                          "span": media.span.model_dump()})
    usable = media.transcript_quality == "ok"
    _step(ctx, f"전사 {media.transcript_source} {media.language}, segment {len(media.segments)}개, "
               f"품질 {media.transcript_quality}", attention=not usable,
          detail={"quality_signals": media.quality_signals, "warnings": media.warnings,
                  "seconds": t.get("transcribe"), "device": media.env.device})
    if media.mode == "whisper+slides":
        _step(ctx, f"프레임 {len(media.frames)}장" + (f", 오류: {media.frames_error}" if media.frames_error else ""),
              attention=bool(media.frames_error),
              detail={"frames_meta": media.frames_meta.model_dump() if media.frames_meta else None})
    problems = contract.check(media, check_files=live)
    if problems:
        _step(ctx, f"1차 처리 결과 계약 위반 {len(problems)}건", attention=True, detail=problems[:20])
        store.save_run(db, item_id=item_id, status="failed", note="계약 위반: " + "; ".join(problems[:3]),
                       transcript_source=media.transcript_source, transcript_quality=media.transcript_quality,
                       **base)
        return VideoOutcome(item.video_id, "failed", "계약 위반", media=media)

    # ---------- 판독 (전사가 끝난 뒤. 메모리 순서) ----------
    readings: list[tuple[Frame, SlideReading | None]] = [(f, None) for f in media.frames]
    stats = {"read": 0, "failed": 0, "missing": 0}
    if media.mode == "whisper+slides" and media.frames:
        readings, stats = read_slides(media, ctx)
    slides_failed = media.mode == "whisper+slides" and stats["read"] == 0
    notes = []
    if slides_failed:
        notes.append("슬라이드 판독 없음 → 전사 결과만" + (f"({media.frames_error})" if media.frames_error else ""))
        _step(ctx, notes[-1], attention=True, detail=stats)

    # ---------- 대조 (전사를 쓸 수 없으면 발화에 있는 수치도 없는 것으로) ----------
    done = [(f, r) for f, r in readings if r is not None]
    aligned = align(done, media.segments, item_id, cfg.align_window_sec, spoken_usable=usable)
    _step(ctx, f"대조: 슬라이드 전용 수치 {len(aligned.slide_only)}개, 발화와 일치 {len(aligned.matched)}개, "
               f"확인 필요 {len(aligned.checks)}개", attention=bool(aligned.checks),
          detail={"unparsed": aligned.unparsed, "excluded": aligned.excluded})

    # ---------- 요약 ----------
    span_lo, span_hi = round(media.span.start), round(media.span.end)
    sinp = summary_input(media, readings, aligned, info)
    model = None
    if not usable and not sinp.slides:
        summary = VideoSummary(name_pairs=[], key_points=[], timeline=[], chapters=sinp.chapters,
                               summary=NO_CONTENT, log="전사·판독 근거 없음", attention=True)
        _step(ctx, "요약 생략: 전사 품질 미달, 판독 없음 → 내용 없음", attention=True)
    else:
        role = load_role("video_summary", ctx.models)
        model = ctx.models.models[ctx.model or role.spec.model].id
        try:
            summary = run_role(role, sinp, ctx)
        except (RoleFailed, LLMError) as e:
            summary = VideoSummary.fallback(str(e)[:120], sinp)
            _step(ctx, "요약 실패, 대체 출력", attention=True, error=str(e), role="video_summary")

    # ---------- 저장 ----------
    # 길이는 올림 정수라 끝이 1초 안쪽이면 전체 처리로 본다
    span_note = ""
    if span_lo > 0 or span_hi < media.duration_sec - 1:  # 구간을 정한 이유(V4). 60분 상한이면 그 문구
        why = resolve_span(item.start_sec, item.end_sec, media.duration_sec, cfg.max_span_sec)[2]
        span_note = why or f"구간 {span_lo}~{span_hi}초"
    log = " / ".join(x for x in [
        item.reason, span_note, f"전사 {media.transcript_quality}",
        f"판독 {stats['read']}/{len(media.frames)}장" if media.mode == "whisper+slides" else "",
        f"슬라이드 전용 수치 {len(aligned.slide_only)}개" if media.mode == "whisper+slides" else "", *notes] if x)
    attention = (summary.attention or not usable or slides_failed or bool(aligned.checks)
                 or any(r.attention for _f, r in done))
    digest = VideoDigest(
        video_id=item.video_id, item_id=item_id, mode=media.mode, span=media.span,
        transcript_source=media.transcript_source, transcript_quality=media.transcript_quality,
        segments_count=len(media.segments), name_pairs=summary.name_pairs, key_points=summary.key_points,
        slides=[DigestSlide(sec=round(f.t), frame_kind=r.frame_kind, title=r.title, ocr_text=r.ocr_text,
                            numbers=r.numbers, table=r.table) for f, r in done],
        slide_only_facts=aligned.slide_only, check_numbers=aligned.checks, timeline=summary.timeline,
        chapters=summary.chapters, summary=summary.summary, frames_total=len(media.frames),
        frames_read=stats["read"], log=log, attention=attention)
    status = "partial" if slides_failed else "ok"
    store.save_segments(db, item.video_id, media.segments, cfg.segment_ttl_weeks)
    if dup := store.save_frames(db, item.video_id, readings):
        _step(ctx, f"같은 시각 프레임 {dup}장은 판독 하나만 저장", attention=True)
    store.save_digest(db, digest, model=model, run_id=run_id)
    store.save_run(db, item_id=item_id, status=status, note="; ".join(notes) or None,
                   transcript_source=media.transcript_source, transcript_quality=media.transcript_quality, **base)
    _step(ctx, log, attention=attention)
    return VideoOutcome(item.video_id, status, "; ".join(notes), digest, media, readings, aligned, summary)
