"""trendsit video <run|purge|report> (S4 영상 분석가). cli.py의 _register가 register(sub)를 부른다."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .core.config import ROOT
from .core.trace import Tracer

MEDIA_ROOT = ROOT / "data" / "media"
SPEC = "S4"  # --spec도 TRENDSIT_SPEC도 없으면 S4로 기록(기본값 S0에 잡히지 않게)


def _spec(args: argparse.Namespace) -> str:
    return args.spec or os.environ.get("TRENDSIT_SPEC") or SPEC


def _queue(args: argparse.Namespace) -> list[Any]:
    from .core.artifacts_video import VideoQueueItem

    if args.queue:
        raw = sys.stdin.read() if args.queue == "-" else Path(args.queue).read_text(encoding="utf-8")
        data = json.loads(raw)
        if not isinstance(data, list):
            raise ValueError("--queue는 영상 처리 지시의 JSON 배열(CONTRACTS 1장)")
        return [VideoQueueItem.model_validate(x) for x in data]
    if not (args.video_id and args.mode):
        raise ValueError("--queue, 또는 --video-id와 --mode가 필요함")
    from .collect.video.source import parse_video_ref

    return [VideoQueueItem(video_id=parse_video_ref(args.video_id), mode=args.mode, start_sec=args.start,
                           end_sec=args.end, reason=args.reason)]


def cmd_run(args: argparse.Namespace) -> int:
    from .collect.video.process import Overrides
    from .core import config
    from .core.artifacts_video import MediaResult
    from .core.budget import BudgetExceeded, PriceUnknown
    from .core.context import open_ctx
    from .video.pipeline import analyze
    from .video.store import save_run

    try:
        items = _queue(args)
    except (ValueError, ValidationError, OSError) as e:
        print(f"입력 오류: {e}", file=sys.stderr)
        return 2
    media = MediaResult.model_validate_json(Path(args.from_json).read_text(encoding="utf-8")) if args.from_json else None
    if media is not None and (len(items) != 1 or items[0].video_id != media.video_id or items[0].mode != media.mode):
        print("--from-json은 같은 영상, 같은 mode 하나에만", file=sys.stderr)
        return 2
    cfg = config.load("video.yaml")
    ctx = open_ctx(None, spec=_spec(args), no_cache=args.no_cache, model=args.model)
    overrides = Overrides(frames=args.frames, frames_res=args.res, lang=args.lang)
    results, code = [], 0
    for item in items:
        ctx.tracer = Tracer(ctx.db, "video", ctx.spec, f"video {item.video_id} {item.mode}")
        status = "failed"
        reuse = MEDIA_ROOT / item.video_id / "media_result.json"
        this_media = media
        if this_media is None and args.reuse_media and reuse.exists():
            saved = MediaResult.model_validate_json(reuse.read_text(encoding="utf-8"))
            # 작업 폴더는 지금 위치로(P1에서 worktree를 지워 옛 절대 경로가 남은 결과가 있음. 프레임 경로는 work_dir 기준 상대)
            saved = saved.model_copy(update={"work_dir": str(reuse.parent)})
            this_media = saved if saved.mode == item.mode else None  # mode가 다르면 처음부터
        try:
            out = analyze(item, ctx, cfg, MEDIA_ROOT, overrides=overrides, media=this_media)
            status = {"ok": "ok", "partial": "ok", "skipped": "ok"}.get(out.status, "failed")
            results.append({"video_id": item.video_id, "status": out.status, "note": out.note,
                            "log": out.digest.log if out.digest else None, "run_id": ctx.tracer.run_id})
            code = code or (1 if out.status == "failed" else 0)
        except (BudgetExceeded, PriceUnknown) as e:
            status = "stopped"
            print(f"{type(e).__name__}: {e}", file=sys.stderr)
            results.append({"video_id": item.video_id, "status": "stopped", "note": str(e)})
            code = 1
            break
        except Exception as e:  # noqa: BLE001 - 한 영상의 예상 밖 오류가 큐 전체를 멈추지 않게. 기록하고 다음 영상
            note = f"{type(e).__name__}: {e}"[:500]
            ctx.tracer.step(kind="code", role="video_analyst", text="예상 밖 오류, 영상 건너뜀", attention=True, error=note)
            save_run(ctx.db, item_id=None, video_id=item.video_id, mode=item.mode, start_sec=item.start_sec,
                     end_sec=item.end_sec, reason=item.reason, status="failed", run_id=ctx.tracer.run_id, note=note)
            results.append({"video_id": item.video_id, "status": "failed", "note": note})
            code = 1
        finally:
            ctx.tracer.finish(status)
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return code


def cmd_purge(args: argparse.Namespace) -> int:
    from .collect.video.workspace import purge
    from .core import config
    from .core.db import DB
    from .video.store import expire_segment_text

    older = args.older_than if args.older_than is not None else config.load("video.yaml").retention_days
    res = purge(MEDIA_ROOT, older)
    db = DB(ROOT / "data" / "trendsit.db")
    n = expire_segment_text(db)
    print(json.dumps({"removed": res["removed"], "kept": len(res["kept"]),
                      "freed_mb": round(res["freed_bytes"] / 1024 ** 2, 1), "segments_text_expired": n},
                     ensure_ascii=False))
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    from .core.db import DB
    from .video.report import runs_markdown

    text = runs_markdown(DB(ROOT / "data" / "trendsit.db"), args.since, args.until)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(args.out)
    else:
        print(text)
    return 0


def register(sub: Any) -> None:
    vp = sub.add_parser("video", help="영상 분석가(S4): 받기, 전사, 슬라이드 판독, 요약")
    vs = vp.add_subparsers(dest="video_cmd", required=True)
    r = vs.add_parser("run", help="영상 처리 지시(큐 JSON) 또는 영상 하나")
    r.add_argument("--queue", help="CONTRACTS 1장 JSON 배열 파일, -면 표준 입력")
    r.add_argument("--video-id", help="11자 id 또는 영상 URL")
    r.add_argument("--mode", choices=["skip", "captions", "whisper", "whisper+slides"])
    r.add_argument("--start", type=int, help="처리 구간 시작(초)")
    r.add_argument("--end", type=int, help="처리 구간 끝(초)")
    r.add_argument("--reason", default="수동 실행", help="처리 이유 한 줄(log에 이어 씀)")
    r.add_argument("--frames", choices=["auto", "full"], help="whisper+slides 프레임 후보 방식(장면 전환이 많은 슬라이드 발표는 full)")
    r.add_argument("--res", type=int, help="프레임 가로 픽셀(수치 많은 발표는 1024)")
    r.add_argument("--lang", help="전사 언어 강제(기본: 다지점 자동 감지)")
    r.add_argument("--from-json", help="저장한 1차 처리 결과(MediaResult)로 판독 이후만")
    r.add_argument("--reuse-media", action="store_true",
                   help="영상마다 data/media/<id>/media_result.json이 있고 mode가 같으면 전사 없이 판독 이후만")
    r.add_argument("--model", help="역할 모델 별칭 덮어쓰기")
    r.add_argument("--no-cache", action="store_true")
    r.add_argument("--spec")
    r.set_defaults(fn=cmd_run)
    p = vs.add_parser("purge", help="오래된 작업 폴더(영상, 프레임)와 보관 기한 지난 segments 텍스트 정리")
    p.add_argument("--older-than", type=float, help="일 수(기본 7)")
    p.set_defaults(fn=cmd_purge)
    rp = vs.add_parser("report", help="영상 처리 기록 요약(markdown)")
    rp.add_argument("--since")
    rp.add_argument("--until")
    rp.add_argument("--out")
    rp.set_defaults(fn=cmd_report)
