"""실제 영상의 1차 처리 결과를 픽스처로 저장(S4_TASK 5.1). 맥 전용(mlx-whisper, ffmpeg).

    uv run python scripts/save_video_fixture.py <video_id> <mode> [--frames full] [--res 1024]

저장: tests/fixtures/video/<video_id>.json(work_dir를 tests/fixtures/video/<video_id>로 바꿈)과
프레임 썸네일 최대 5장(가로 320px, 같은 상대 경로). segments가 40KB를 넘으면 앞부분만 + truncated_segments.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from trendsit.collect.video import contract
from trendsit.collect.video.process import Overrides, media_process
from trendsit.collect.video.settings import load_video_config
from trendsit.core.artifacts_video import FRAME_PRIORITY, VideoQueueItem
from trendsit.core.config import ROOT

OUT = ROOT / "tests/fixtures/video"
SEGMENTS_MAX_BYTES = 40_000
THUMBS = 5
THUMB_WIDTH = 320


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("video_id")
    ap.add_argument("mode", choices=["whisper", "whisper+slides"])
    ap.add_argument("--frames", choices=["auto", "full"])
    ap.add_argument("--res", type=int)
    args = ap.parse_args()
    item = VideoQueueItem(video_id=args.video_id, mode=args.mode, reason="픽스처 저장")
    r = media_process(item, load_video_config(), ROOT / "data/media",
                      overrides=Overrides(frames=args.frames, frames_res=args.res))
    problems = contract.check(r, check_files=True)
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    data = r.model_dump(mode="json")
    work = Path(r.work_dir)
    dest = OUT / r.video_id
    data["work_dir"] = dest.relative_to(ROOT).as_posix()
    while len(json.dumps(data["segments"], ensure_ascii=False).encode()) > SEGMENTS_MAX_BYTES:
        data["segments"] = data["segments"][: int(len(data["segments"]) * 0.8)]
        data["truncated_segments"] = True
    # 판독 우선순위가 높은 프레임부터 썸네일
    picked = sorted(r.frames, key=lambda f: (FRAME_PRIORITY[f.reason], f.t))[:THUMBS]
    shutil.rmtree(dest, ignore_errors=True)  # 앞 실행의 썸네일을 남기지 않음
    for f in picked:
        target = dest / f.path
        target.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(work / f.path), "-vf",
                        f"scale={THUMB_WIDTH}:-2", "-q:v", "5", str(target)], check=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{r.video_id}.json").write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"video_id": r.video_id, "segments": len(data["segments"]), "frames": len(r.frames),
                      "thumbs": len(picked), "quality": r.transcript_quality, "timings": r.env.timings_sec},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
