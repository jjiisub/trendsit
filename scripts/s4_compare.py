"""관문 B 비교(S4_TASK 7장): 슬라이드 발표를 whisper만 vs whisper+slides로 요약해 나란히.

    TRENDSIT_SPEC=S4 uv run --extra video python scripts/s4_compare.py <video_id> [<video_id> ...]

같은 1차 처리 결과(data/media/<id>/media_result.json)에서 프레임만 뺀 사본으로 whisper 요약을 만든다(전사가 같아
슬라이드가 더한 것만 차이). 그다음 whisper+slides를 같은 결과로 다시 돌려(판독·요약은 캐시) 저장된 digest를 되돌린다.
결과: reports/S4_video/compare_<id>.json
"""

from __future__ import annotations

import json
import sys

from trendsit.core import config
from trendsit.core.artifacts_video import MediaResult, VideoQueueItem
from trendsit.core.config import ROOT
from trendsit.core.context import open_ctx
from trendsit.core.trace import Tracer
from trendsit.video.pipeline import analyze

OUT = ROOT / "reports/S4_video"


def main(ids: list[str]) -> int:
    cfg = config.load("video.yaml")
    ctx = open_ctx(None, spec="S4")
    for vid in ids:
        media = MediaResult.model_validate_json((ROOT / "data/media" / vid / "media_result.json").read_text())
        only = media.model_copy(update={"mode": "whisper", "frames": [], "frames_meta": None, "frames_error": None})
        row = ctx.db.conn.execute("SELECT reason FROM video_runs WHERE video_id=? AND mode='whisper+slides' "
                                  "ORDER BY id DESC LIMIT 1", (vid,)).fetchone()
        reason = row["reason"] if row else "비교"
        result = {}
        for label, m in (("whisper", only), ("whisper+slides", media)):
            ctx.tracer = Tracer(ctx.db, "video", ctx.spec, f"compare {vid} {label}")
            # whisper+slides는 마지막에 같은 이유로 다시 저장(관문 B digest를 되돌림)
            out = analyze(VideoQueueItem(video_id=vid, mode=m.mode, reason=reason if m is media else f"비교: {label}"),
                          ctx, cfg, ROOT / "data/media", media=m)
            ctx.tracer.finish("ok" if out.status in ("ok", "partial") else "failed")
            d = out.digest
            result[label] = {"key_points": [k.model_dump() for k in d.key_points],
                             "summary": d.summary, "timeline": [t.model_dump() for t in d.timeline],
                             "name_pairs": [p.model_dump() for p in d.name_pairs],
                             "slide_only_facts": [f.model_dump() for f in d.slide_only_facts]}
        (OUT / f"compare_{vid}.json").write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n",
                                                 encoding="utf-8")
        print(vid, {k: len(v["key_points"]) for k, v in result.items()})
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
