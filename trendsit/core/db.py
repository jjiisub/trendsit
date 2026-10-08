"""SQLite 접근은 이 파일 한 곳에서만. 실행 기록(runs, steps, llm_calls)."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

KST = timezone(timedelta(hours=9))

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    spec TEXT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL DEFAULT 'running',
    cost_usd REAL NOT NULL DEFAULT 0,
    note TEXT
);
CREATE TABLE IF NOT EXISTS steps (
    id INTEGER PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(id),
    seq INTEGER NOT NULL,
    t TEXT NOT NULL,
    role TEXT,
    kind TEXT NOT NULL CHECK(kind IN ('llm','tool','code')),
    text TEXT,
    attention INTEGER NOT NULL DEFAULT 0,
    detail TEXT,
    prompt_hash TEXT,
    model TEXT,
    provider TEXT,
    tokens_in INTEGER,
    tokens_out INTEGER,
    cost_usd REAL,
    cost_estimated INTEGER NOT NULL DEFAULT 0,
    latency_ms INTEGER,
    cache_hit INTEGER NOT NULL DEFAULT 0,
    error TEXT,
    output TEXT,
    reasoning_tokens INTEGER,
    cached_tokens INTEGER
);
CREATE INDEX IF NOT EXISTS steps_run ON steps(run_id, seq);
CREATE TABLE IF NOT EXISTS llm_calls (
    step_id INTEGER PRIMARY KEY REFERENCES steps(id),
    request TEXT NOT NULL,
    response TEXT
);
"""

STEP_COLUMNS = (
    "run_id", "seq", "t", "role", "kind", "text", "attention", "detail", "prompt_hash", "model",
    "provider", "tokens_in", "tokens_out", "cost_usd", "cost_estimated", "latency_ms", "cache_hit",
    "error", "output", "reasoning_tokens", "cached_tokens",
)
# 스키마를 늘릴 때 기존 DB에 붙일 칸(칸 이름, 타입)
ADDED_STEP_COLUMNS = (("reasoning_tokens", "INTEGER"), ("cached_tokens", "INTEGER"))


def now_kst() -> str:
    return datetime.now(KST).isoformat(timespec="seconds")


def _json(v: Any) -> str | None:
    if v is None or isinstance(v, str):
        return v
    return json.dumps(v, ensure_ascii=False)


class DB:
    def __init__(self, path: Path, migrations: dict[int, str] | None = None):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA busy_timeout=5000")
        self.conn.executescript(SCHEMA)
        have = {r["name"] for r in self.conn.execute("PRAGMA table_info(steps)")}
        for name, kind in ADDED_STEP_COLUMNS:
            if name not in have:
                self.conn.execute(f"ALTER TABLE steps ADD COLUMN {name} {kind}")
        self.migrate(migrations)

    def migrate(self, migrations: dict[int, str] | None = None) -> list[int]:
        """등록된 마이그레이션 중 아직 적용하지 않은 것을 적용한다(core/migrations.py). 적용한 번호를 돌려준다."""
        from .migrations import apply_all

        return apply_all(self.conn, migrations)

    def close(self) -> None:
        self.conn.close()

    # ---------- 쓰기 ----------
    def insert_run(self, run_id: str, kind: str, spec: str | None, note: str | None = None) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT INTO runs(id, kind, spec, started_at, note) VALUES (?,?,?,?,?)",
                (run_id, kind, spec, now_kst(), note),
            )

    def finish_run(self, run_id: str, status: str) -> None:
        with self.conn:
            self.conn.execute(
                "UPDATE runs SET finished_at=?, status=?, "
                "cost_usd=(SELECT COALESCE(SUM(cost_usd),0) FROM steps WHERE run_id=?) WHERE id=?",
                (now_kst(), status, run_id, run_id),
            )

    def insert_step(self, **fields: Any) -> int:
        row = {k: fields.get(k) for k in STEP_COLUMNS}
        for k in ("detail", "output"):
            row[k] = _json(row[k])
        for k in ("attention", "cost_estimated", "cache_hit"):
            row[k] = int(bool(row[k]))
        with self.conn:
            seq = self.conn.execute(
                "SELECT COALESCE(MAX(seq),0)+1 FROM steps WHERE run_id=?", (row["run_id"],)
            ).fetchone()[0]
            row["seq"], row["t"] = seq, now_kst()
            cur = self.conn.execute(
                f"INSERT INTO steps({','.join(STEP_COLUMNS)}) VALUES ({','.join('?' * len(STEP_COLUMNS))})",
                tuple(row[k] for k in STEP_COLUMNS),
            )
            return int(cur.lastrowid)

    def insert_llm_call(self, step_id: int, request: Any, response: Any) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT INTO llm_calls(step_id, request, response) VALUES (?,?,?)",
                (step_id, _json(request), _json(response)),
            )

    # ---------- 읽기 ----------
    def step(self, step_id: int) -> sqlite3.Row | None:
        return self.conn.execute("SELECT * FROM steps WHERE id=?", (step_id,)).fetchone()

    def llm_call(self, step_id: int) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT * FROM llm_calls WHERE step_id=?", (step_id,)).fetchone()
        if row is None:
            return None
        return {"request": json.loads(row["request"]),
                "response": json.loads(row["response"]) if row["response"] else None}

    def steps_of(self, run_id: str) -> list[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM steps WHERE run_id=? ORDER BY seq", (run_id,)).fetchall()

    def run(self, run_id: str) -> sqlite3.Row | None:
        return self.conn.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()

    def spent(self, spec: str | None = None) -> float:
        """실행 기록 기준 사용액. spec이 없으면 전체."""
        sql = "SELECT COALESCE(SUM(s.cost_usd),0) FROM steps s JOIN runs r ON r.id=s.run_id"
        args: tuple[Any, ...] = ()
        if spec:
            sql += " WHERE r.spec=?"
            args = (spec,)
        return float(self.conn.execute(sql, args).fetchone()[0])

    def cost_by_model(self, spec: str | None = None) -> list[sqlite3.Row]:
        sql = (
            "SELECT r.spec, s.model, COUNT(*) AS calls, SUM(s.cache_hit) AS cache_hits, "
            "COALESCE(SUM(s.tokens_in),0) AS tokens_in, COALESCE(SUM(s.tokens_out),0) AS tokens_out, "
            "COALESCE(SUM(s.cost_usd),0) AS cost, MAX(s.cost_estimated) AS estimated "
            "FROM steps s JOIN runs r ON r.id=s.run_id WHERE s.kind='llm'"
        )
        args: tuple[Any, ...] = ()
        if spec:
            sql += " AND r.spec=?"
            args = (spec,)
        sql += " GROUP BY r.spec, s.model ORDER BY r.spec, cost DESC"
        return self.conn.execute(sql, args).fetchall()

    # ---------- 칠판: 수집 (S1) ----------
    def upsert_source(self, sid: str, channel: str, kind: str | None, name: str, feed: str | None,
                      config_json: Any) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT INTO sources(id, channel, kind, name, feed, config_json) VALUES (?,?,?,?,?,?) "
                "ON CONFLICT(id) DO UPDATE SET channel=excluded.channel, kind=excluded.kind, name=excluded.name, "
                "feed=excluded.feed, config_json=excluded.config_json",
                (sid, channel, kind, name, feed, _json(config_json)))

    def item_by_external(self, source_id: str, external_id: str) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT i.*, t.text AS body FROM items i LEFT JOIN item_texts t ON t.item_id=i.id "
            "WHERE i.source_id=? AND i.external_id=?", (source_id, external_id)).fetchone()

    def save_item(self, item: dict[str, Any], *, text: str | None, origin_summary: str | None,
                  expires_at: str | None, links: list[dict[str, Any]], keywords: dict[str, str],
                  video: dict[str, Any] | None = None, replace_id: int | None = None) -> int:
        """항목 하나와 딸린 행을 한 트랜잭션으로. replace_id가 있으면(본문이 비었던 항목 재시도) 그 행을 갱신."""
        cols = ("source_id", "channel", "kind", "external_id", "url", "title", "published_at",
                "published_estimated", "day", "week", "summary_feed", "body_status", "filter_status",
                "filter_reason", "score", "run_id", "via", "meta_json")
        item = {**item, "meta_json": _json(item.get("meta_json"))}
        with self.conn:
            if replace_id is None:
                cur = self.conn.execute(
                    f"INSERT INTO items({','.join(cols)}, created_at) VALUES ({','.join('?' * len(cols))}, ?)",
                    (*(item.get(c) for c in cols), now_kst()))
                item_id = int(cur.lastrowid)
            else:
                item_id = replace_id
                self.conn.execute(
                    f"UPDATE items SET {', '.join(f'{c}=?' for c in cols)} WHERE id=?",
                    (*(item.get(c) for c in cols), item_id))
                for t in ("item_texts", "item_keywords", "links", "videos"):
                    self.conn.execute(f"DELETE FROM {t} WHERE item_id=?", (item_id,))
            self.conn.execute("INSERT INTO item_texts(item_id, text, origin_summary, expires_at) VALUES (?,?,?,?)",
                              (item_id, text, origin_summary, expires_at))
            self.conn.executemany(
                "INSERT OR IGNORE INTO item_keywords(item_id, keyword_id, where_matched) VALUES (?,?,?)",
                [(item_id, k, w) for k, w in keywords.items()])
            self.conn.executemany(
                "INSERT OR IGNORE INTO links(item_id, url, anchor, kind, role) VALUES (?,?,?,?,?)",
                [(item_id, x["url"], x.get("anchor"), x.get("kind"), x.get("role", "body")) for x in links])
            if video is not None:
                self.conn.execute(
                    "INSERT INTO videos(item_id, video_id, duration_sec, manual_sub_langs, has_auto_sub, "
                    "chapters_json, meta_status) VALUES (?,?,?,?,?,?,?)",
                    (item_id, video.get("video_id"), video.get("duration_sec"),
                     _json(video.get("manual_sub_langs")), video.get("has_auto_sub"),
                     _json(video.get("chapters")), video.get("meta_status")))
        return item_id

    def video_meta_status(self, item_id: int) -> str | None:
        row = self.conn.execute("SELECT meta_status FROM videos WHERE item_id=?", (item_id,)).fetchone()
        return row["meta_status"] if row else None

    def log_fetch(self, run_id: str, source_id: str, day: str, status: str, *, n_new: int = 0,
                  n_backfilled: int = 0, n_seen: int = 0, error: str | None = None, detail: Any = None) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT INTO fetch_log(run_id, source_id, day, status, n_new, n_backfilled, n_seen, error, detail, t) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (run_id, source_id, day, status, n_new, n_backfilled, n_seen, error, _json(detail), now_kst()))

    def upsert_repo(self, full_name: str, *, description: str | None = None, language: str | None = None,
                    topics: list[str] | None = None, readme_head: str | None = None) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT INTO repos(full_name, description, language, topics_json, readme_head, first_seen) "
                "VALUES (?,?,?,?,?,?) ON CONFLICT(full_name) DO UPDATE SET "
                "description=COALESCE(excluded.description, description), language=COALESCE(excluded.language, language), "
                "topics_json=COALESCE(excluded.topics_json, topics_json), readme_head=COALESCE(excluded.readme_head, readme_head)",
                (full_name, description, language, _json(topics) if topics is not None else None, readme_head,
                 now_kst()))

    def clear_trending(self, week: str) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM repo_trending WHERE week=?", (week,))

    def save_trending(self, week: str, row: dict[str, Any], run_id: str) -> bool:
        """주차별 트렌딩 1행. 같은 주에 이미 있으면 수치만 갱신하고 False."""
        with self.conn:
            exists = self.conn.execute("SELECT 1 FROM repo_trending WHERE week=? AND full_name=?",
                                       (week, row["full_name"])).fetchone()
            self.conn.execute(
                "INSERT INTO repo_trending(week, full_name, rank, stars_total, stars_this_week, forks, run_id, "
                "score, filter_status, filter_reason, keywords) VALUES (?,?,?,?,?,?,?,?,?,?,?) "
                "ON CONFLICT(week, full_name) DO UPDATE SET rank=excluded.rank, stars_total=excluded.stars_total, "
                "stars_this_week=excluded.stars_this_week, forks=excluded.forks, score=excluded.score, "
                "filter_status=excluded.filter_status, filter_reason=excluded.filter_reason, keywords=excluded.keywords",
                (week, row["full_name"], row["rank"], row.get("stars_total"), row.get("stars_this_week"),
                 row.get("forks"), run_id, row.get("score"), row.get("filter_status"), row.get("filter_reason"),
                 _json(row.get("keywords"))))
        return exists is None
