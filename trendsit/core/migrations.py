"""DB 마이그레이션 등록(번호 키 방식, S1 리뷰 M1).

번호 → SQL. 적용 기록은 schema_migrations 표에 남기고, 등록된 번호 중 기록에 없는 것을 오름차순으로 하나씩 적용한다.
빈 번호를 허용하므로 두 브랜치가 각자 대역에 추가해도 병합 때 겹치지 않는다.

번호 대역(COMMON 9장): 1~9 = S0~S1, 10~19 = S2~S3, 20~29 = S4. 다른 대역끼리는 서로 의존하지 않는다.
대역별 등록은 아래 각 묶음 자리에. S4 몫은 S4 브랜치가 자기 자리에 추가한다.
"""

from __future__ import annotations

import sqlite3

MIGRATIONS: dict[int, str] = {}


def register(number: int, sql: str) -> None:
    if number in MIGRATIONS:
        raise ValueError(f"마이그레이션 번호 {number}이 이미 등록됨")
    MIGRATIONS[number] = sql


# ---------- S1 (1~9) ----------
# 1: 칠판(수집)
register(1, """
    CREATE TABLE IF NOT EXISTS sources (
        id TEXT PRIMARY KEY, channel TEXT NOT NULL, kind TEXT, name TEXT, feed TEXT,
        enabled INTEGER NOT NULL DEFAULT 1, config_json TEXT
    );
    CREATE TABLE IF NOT EXISTS fetch_log (
        id INTEGER PRIMARY KEY, run_id TEXT, source_id TEXT, day TEXT,
        status TEXT NOT NULL CHECK(status IN ('ok','failed','partial')),
        n_new INTEGER NOT NULL DEFAULT 0, n_backfilled INTEGER NOT NULL DEFAULT 0, error TEXT,
        n_seen INTEGER NOT NULL DEFAULT 0, detail TEXT, t TEXT
    );
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY, source_id TEXT NOT NULL,
        channel TEXT NOT NULL CHECK(channel IN ('text','video','github')), kind TEXT,
        external_id TEXT NOT NULL, url TEXT, title TEXT, published_at TEXT,
        published_estimated INTEGER NOT NULL DEFAULT 0, day TEXT, week TEXT, summary_feed TEXT,
        body_status TEXT, filter_status TEXT CHECK(filter_status IN ('pass','filtered')),
        filter_reason TEXT, score INTEGER, run_id TEXT, created_at TEXT,
        via TEXT,
        UNIQUE(source_id, external_id)
    );
    CREATE INDEX IF NOT EXISTS items_day ON items(day);
    CREATE INDEX IF NOT EXISTS items_week ON items(week);
    CREATE TABLE IF NOT EXISTS item_texts (
        item_id INTEGER PRIMARY KEY REFERENCES items(id), text TEXT, origin_summary TEXT, expires_at TEXT
    );
    CREATE TABLE IF NOT EXISTS item_keywords (
        item_id INTEGER NOT NULL, keyword_id TEXT NOT NULL, where_matched TEXT,
        PRIMARY KEY(item_id, keyword_id)
    );
    CREATE TABLE IF NOT EXISTS links (
        id INTEGER PRIMARY KEY, item_id INTEGER NOT NULL, url TEXT NOT NULL, anchor TEXT, kind TEXT,
        role TEXT NOT NULL CHECK(role IN ('body','origin_candidate')), UNIQUE(item_id, url)
    );
    CREATE TABLE IF NOT EXISTS videos (
        item_id INTEGER PRIMARY KEY, video_id TEXT, duration_sec INTEGER, manual_sub_langs TEXT,
        has_auto_sub INTEGER, chapters_json TEXT, meta_status TEXT
    );
    CREATE TABLE IF NOT EXISTS repos (
        full_name TEXT PRIMARY KEY, description TEXT, language TEXT, topics_json TEXT, readme_head TEXT,
        first_seen TEXT
    );
    CREATE TABLE IF NOT EXISTS repo_trending (
        week TEXT NOT NULL, full_name TEXT NOT NULL, rank INTEGER, stars_total INTEGER,
        stars_this_week INTEGER, forks INTEGER, run_id TEXT,
        score INTEGER, filter_status TEXT, filter_reason TEXT, keywords TEXT,
        PRIMARY KEY(week, full_name)
    );
    """)
# 2: 소스별 부가 정보(GeekNews 점수, 댓글 수, topic id 등). 받은 시점의 값
register(2, """
    ALTER TABLE items ADD COLUMN meta_json TEXT;
    """)

# ---------- S2~S3 (10~19) ----------
# 10: S2 2a 임베딩 관련성 필터와 URL 중복 연결. S1 items.filter_status(키워드 판정)는 건드리지 않고 따로 저장
register(10, """
    CREATE TABLE IF NOT EXISTS item_embeddings (
        item_id INTEGER NOT NULL, model TEXT NOT NULL, dim INTEGER NOT NULL, vec BLOB NOT NULL,
        text_hash TEXT, created_at TEXT, PRIMARY KEY(item_id, model)
    );
    CREATE TABLE IF NOT EXISTS item_relevance (
        item_id INTEGER PRIMARY KEY, model TEXT NOT NULL, score REAL NOT NULL, keyword_id TEXT,
        decision TEXT NOT NULL CHECK(decision IN ('keep','drop')), reason TEXT, run_id TEXT
    );
    CREATE TABLE IF NOT EXISTS item_same_as (
        item_id INTEGER PRIMARY KEY, canonical_id INTEGER NOT NULL, reason TEXT
    );
    """)

# 11: S2 2b 글 카드. version 1 = 1차 요약(item_card), 2 = 글 분석가(S3 3b). v2가 v1을 덮지 않음
register(11, """
    CREATE TABLE IF NOT EXISTS item_cards (
        item_id INTEGER NOT NULL, version INTEGER NOT NULL CHECK(version IN (1, 2)), card_json TEXT NOT NULL,
        model TEXT, run_id TEXT, created_at TEXT, fallback INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY(item_id, version)
    );
    """)

# 12: S3 3c 레포 분석가 카드(주차별)와 레포 한 줄(repo_oneliner 결과, 입력 해시가 같으면 재사용)
register(12, """
    CREATE TABLE IF NOT EXISTS repo_cards (
        week TEXT NOT NULL, full_name TEXT NOT NULL, card_json TEXT NOT NULL, model TEXT, run_id TEXT,
        created_at TEXT, fallback INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(week, full_name)
    );
    CREATE TABLE IF NOT EXISTS repo_oneliners (
        full_name TEXT PRIMARY KEY, input_hash TEXT NOT NULL, output_json TEXT NOT NULL, model TEXT, created_at TEXT
    );
    """)

# ---------- S4 (20~29) ----------


# ---------- 적용 ----------
def split_sql(script: str) -> list[str]:
    """SQL 묶음을 문장 단위로 나눈다(문자열 안의 ;는 나누지 않음)."""
    out, buf = [], ""
    for part in script.split(";"):
        buf += part + ";"
        if sqlite3.complete_statement(buf):
            if buf.strip(" \n\t;"):
                out.append(buf.strip())
            buf = ""
    if buf.strip(" \n\t;"):
        out.append(buf.strip())
    return out


def applied(conn: sqlite3.Connection) -> set[int]:
    return {r[0] for r in conn.execute("SELECT version FROM schema_migrations")}


def apply_all(conn: sqlite3.Connection, registry: dict[int, str] | None = None) -> list[int]:
    """등록된 번호 중 기록에 없는 것을 오름차순으로 하나씩, 번호마다 한 트랜잭션으로 적용한다. 적용한 번호를 돌려준다.

    executescript는 먼저 커밋해 버려 트랜잭션이 되지 않으므로, 이 동안만 자동 커밋 모드(isolation_level=None)로 두고
    BEGIN → 문장을 하나씩 → schema_migrations 기록 → COMMIT. 실패하면 ROLLBACK하고 예외를 그대로 올린다(기록 없음,
    다음 실행 때 다시 시도). user_version은 적용된 최대 번호로 맞춰 두되 판단에는 쓰지 않는다.
    """
    from .db import now_kst

    registry = MIGRATIONS if registry is None else registry
    saved = conn.isolation_level
    conn.isolation_level = None
    done: list[int] = []
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT)")
        have = applied(conn)
        if not have:
            # 번호 키 방식 이전 DB: user_version N이면 1..N은 이미 적용된 것으로 기록(다시 실행하지 않음)
            legacy = conn.execute("PRAGMA user_version").fetchone()[0]
            if legacy:
                conn.execute("BEGIN")
                conn.executemany("INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                                 [(v, "legacy user_version") for v in range(1, legacy + 1)])
                conn.execute("COMMIT")
                have = applied(conn)
        for number in sorted(set(registry) - have):
            conn.execute("BEGIN")
            try:
                for stmt in split_sql(registry[number]):
                    conn.execute(stmt)
                conn.execute("INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)", (number, now_kst()))
                conn.execute("COMMIT")
            except Exception:
                if conn.in_transaction:  # SQLite가 이미 되돌린 경우(디스크 가득 등) 원래 오류를 가리지 않게
                    conn.execute("ROLLBACK")
                raise
            done.append(number)
        top = conn.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0] or 0
        conn.execute(f"PRAGMA user_version = {int(top)}")
    finally:
        conn.isolation_level = saved
    return done
