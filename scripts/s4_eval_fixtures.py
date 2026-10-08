"""관문 B: 실제 실행의 video_summary 입력을 평가 픽스처로(eval/fixtures/video_summary). 맥에서 video run 뒤에.

    uv run python scripts/s4_eval_fixtures.py reports/S4_video/queue_gateB.json

입력은 파이프라인과 같은 함수(summary_input)로 다시 만든다(같은 메시지 → eval 재실행은 캐시, 0원).
전사 품질 분기(A7)를 judge Q3로 재려고 파생 픽스처 2개를 더한다: 슬라이드 발표의 전사를 suspect_hallucination으로,
대담의 전사를 empty로(판독 없음). 파생 픽스처는 이름이 derived_로 시작하고 리포트에 표시한다.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from trendsit.collect.video.settings import load_video_config
from trendsit.core.artifacts_video import MediaResult, SlideReading, VideoQueueItem
from trendsit.core.config import ROOT
from trendsit.core.db import DB
from trendsit.video import store
from trendsit.video.align import align
from trendsit.video.pipeline import summary_input

OUT = ROOT / "eval/fixtures/video_summary"


def readings_of(db: DB, media: MediaResult) -> list:
    rows = {round(r["t"], 3): r["reading_json"] for r in
            db.conn.execute("SELECT t, reading_json FROM video_frames WHERE video_id = ?", (media.video_id,))}
    return [(f, SlideReading.model_validate_json(rows[round(f.t, 3)]) if rows.get(round(f.t, 3)) else None)
            for f in media.frames]


def build(db: DB, media: MediaResult, readings: list, window: int) -> dict:
    info = store.video_item(db, media.video_id)
    done = [(f, r) for f, r in readings if r is not None]
    aligned = align(done, media.segments, info["item_id"], window, spoken_usable=media.transcript_quality == "ok")
    return summary_input(media, readings, aligned, info).model_dump(mode="json")


def main(queue_path: str) -> int:
    cfg = load_video_config()
    db = DB(ROOT / "data/trendsit.db")
    OUT.mkdir(parents=True, exist_ok=True)
    items = [VideoQueueItem.model_validate(x) for x in json.loads(Path(queue_path).read_text(encoding="utf-8"))]
    medias = {}
    for it in items:
        path = ROOT / "data/media" / it.video_id / "media_result.json"
        if not path.exists() or store.digest(db, it.video_id) is None:
            print(f"건너뜀 {it.video_id}: 처리 결과 없음", file=sys.stderr)
            continue
        media = MediaResult.model_validate_json(path.read_text(encoding="utf-8"))
        medias[it.video_id] = media
        fx = {"input": build(db, media, readings_of(db, media), cfg.align_window_sec), "expect": {},
              "note": f"관문 B 실제 실행: {it.reason} ({media.mode})"}
        (OUT / f"{it.video_id}.json").write_text(json.dumps(fx, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    slides = next((m for m in medias.values() if m.mode == "whisper+slides" and m.frames), None)
    talk = next((m for m in medias.values() if m.mode == "whisper"), None)
    for base, quality, keep_frames in ((slides, "suspect_hallucination", True), (talk, "empty", False)):
        if base is None:
            continue
        m = base.model_copy(update={"transcript_quality": quality})
        rd = readings_of(db, base) if keep_frames else []
        fx = {"input": build(db, m, rd, cfg.align_window_sec), "expect": {},
              "note": f"파생(A7): {base.video_id}의 전사 품질을 {quality}로" + ("" if keep_frames else ", 판독 없음")}
        (OUT / f"derived_{quality}_{base.video_id}.json").write_text(
            json.dumps(fx, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(list(OUT.glob('*.json')))}개 → {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
