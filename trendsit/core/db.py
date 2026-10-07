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
    def __init__(self, path: Path):
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
