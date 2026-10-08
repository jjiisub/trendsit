"""영상 분석가의 DB 읽기·쓰기(video_* 표, 마이그레이션 20). S1 items·videos는 읽기만. 오케스트레이터(pipeline)만 부른다."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any

from ..core.artifacts_video import Frame, Segment, SlideReading, VideoDigest
from ..core.db import DB, KST, now_kst


def video_item(db: DB, video_id: str) -> dict[str, Any] | None:
    """S1이 수집한 영상: item_id(근거 id의 번호), 제목, 길이, 업로더 챕터, 소스."""
    row = db.conn.execute(
        "SELECT i.id, i.title, i.source_id, i.url, v.duration_sec, v.chapters_json, v.manual_sub_langs "
        "FROM videos v JOIN items i ON i.id = v.item_id WHERE v.video_id = ? ORDER BY i.id DESC LIMIT 1",
        (video_id,)).fetchone()
    if row is None:
        return None
    chapters = [{"sec": int(c["start"] or 0), "title": c.get("title") or ""}
                for c in json.loads(row["chapters_json"] or "[]") if c.get("start") is not None]
    return {"item_id": row["id"], "title": row["title"], "source_id": row["source_id"], "url": row["url"],
            "duration_sec": row["duration_sec"], "chapters": chapters}


def save_run(db: DB, *, item_id: int | None, video_id: str, mode: str, start_sec: int | None, end_sec: int | None,
             reason: str, status: str, run_id: str, transcript_source: str | None = None,
             transcript_quality: str | None = None, note: str | None = None) -> int:
    with db.conn:
        cur = db.conn.execute(
            "INSERT INTO video_runs(item_id, video_id, mode, start_sec, end_sec, reason, transcript_source, "
            "transcript_quality, status, note, run_id, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (item_id, video_id, mode, start_sec, end_sec, reason, transcript_source, transcript_quality, status,
             note, run_id, now_kst()))
    return int(cur.lastrowid)


def save_segments(db: DB, video_id: str, segments: list[Segment], ttl_weeks: int) -> None:
    """같은 영상을 다시 처리하면 바꾼다. 텍스트는 ttl_weeks 뒤 지움(item_texts와 같은 원칙)."""
    expires = (datetime.now(KST) + timedelta(weeks=ttl_weeks)).isoformat(timespec="seconds")
    with db.conn:
        db.conn.execute("DELETE FROM video_segments WHERE video_id = ?", (video_id,))
        db.conn.executemany(
            'INSERT INTO video_segments(video_id, idx, start, "end", text, expires_at) VALUES (?,?,?,?,?,?)',
            [(video_id, i, s.start, s.end, s.text, expires) for i, s in enumerate(segments)])


def save_frames(db: DB, video_id: str, frames: list[tuple[Frame, SlideReading | None]]) -> int:
    """프레임 판독은 텍스트만(이미지 경로는 7일 뒤 사라지므로 저장하지 않음). 같은 시각이 둘이면 판독이 있는 쪽 하나만.
    겹쳐서 빠진 프레임 수를 돌려준다(조용히 덮어쓰지 않게)."""
    by_t: dict[float, tuple[Frame, SlideReading | None]] = {}
    for f, r in frames:
        if f.t not in by_t or (by_t[f.t][1] is None and r is not None):
            by_t[f.t] = (f, r)
    with db.conn:
        db.conn.execute("DELETE FROM video_frames WHERE video_id = ?", (video_id,))
        db.conn.executemany(
            "INSERT INTO video_frames(video_id, t, reason, spoken_text, reading_json) VALUES (?,?,?,?,?)",
            [(video_id, f.t, f.reason, f.spoken_text, r.model_dump_json() if r else None) for f, r in by_t.values()])
    return len(frames) - len(by_t)


def save_digest(db: DB, digest: VideoDigest, *, model: str | None, run_id: str) -> None:
    with db.conn:
        db.conn.execute(
            "INSERT OR REPLACE INTO video_digests(video_id, item_id, digest_json, model, run_id, created_at) "
            "VALUES (?,?,?,?,?,?)",
            (digest.video_id, digest.item_id, digest.model_dump_json(), model, run_id, now_kst()))


def digest(db: DB, video_id: str) -> VideoDigest | None:
    row = db.conn.execute("SELECT digest_json FROM video_digests WHERE video_id = ?", (video_id,)).fetchone()
    return VideoDigest.model_validate_json(row["digest_json"]) if row else None


def expire_segment_text(db: DB, now: datetime | None = None) -> int:
    """보관 기한이 지난 segments 텍스트만 지운다(시각과 행은 남김)."""
    cutoff = (now or datetime.now(KST)).isoformat(timespec="seconds")
    with db.conn:
        cur = db.conn.execute("UPDATE video_segments SET text = NULL WHERE expires_at < ? AND text IS NOT NULL",
                              (cutoff,))
    return cur.rowcount


def runs(db: DB, since: str | None = None, until: str | None = None) -> list[dict[str, Any]]:
    sql = ("SELECT r.*, d.digest_json FROM video_runs r LEFT JOIN video_digests d ON d.video_id = r.video_id "
           "AND d.run_id = r.run_id WHERE 1=1")
    args: list[Any] = []
    if since:
        sql += " AND substr(r.created_at, 1, 10) >= ?"
        args.append(since)
    if until:
        sql += " AND substr(r.created_at, 1, 10) <= ?"
        args.append(until)
    return [dict(r) for r in db.conn.execute(sql + " ORDER BY r.id", args)]
