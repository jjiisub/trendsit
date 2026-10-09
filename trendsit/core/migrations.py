"""DB 마이그레이션 등록(번호 키 방식, S1 리뷰 M1).

번호 → SQL. 적용 기록은 schema_migrations 표에 남기고, 등록된 번호 중 기록에 없는 것을 오름차순으로 하나씩 적용한다.
빈 번호를 허용하므로 두 브랜치가 각자 대역에 추가해도 병합 때 겹치지 않는다.

번호 대역(COMMON 9장): 1~9 = S0~S1, 10~19 = S2~S3, 20~29 = S4, 30~39 = S5. 다른 대역끼리는 서로 의존하지 않는다.
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

# 13: S3 3a 편집장 계획(날짜별, 모델 계획 또는 규칙 기반 대체 계획)
register(13, """
    CREATE TABLE IF NOT EXISTS plans (
        id INTEGER PRIMARY KEY, day TEXT NOT NULL, run_id TEXT,
        source TEXT NOT NULL CHECK(source IN ('model','fallback')), plan_json TEXT NOT NULL, created_at TEXT
    );
    CREATE INDEX IF NOT EXISTS plans_day ON plans(day, id);
    """)

# ---------- S4 (20~29) ----------
# 20: 영상 분석가. 영상마다 처리 기록 1행(다시 처리하면 새 행), 전사 segments(8주 뒤 텍스트 삭제), 프레임 판독(텍스트만),
# VideoDigest. 영상 파일과 프레임 이미지는 DB에 두지 않는다(data/media, 7일 뒤 정리). S1 videos는 읽기만
register(20, """
    CREATE TABLE IF NOT EXISTS video_runs (
        id INTEGER PRIMARY KEY, item_id INTEGER, video_id TEXT NOT NULL,
        mode TEXT NOT NULL CHECK(mode IN ('skip','captions','whisper','whisper+slides')),
        start_sec INTEGER, end_sec INTEGER, reason TEXT, transcript_source TEXT, transcript_quality TEXT,
        status TEXT NOT NULL CHECK(status IN ('ok','partial','skipped','failed')), note TEXT,
        run_id TEXT, created_at TEXT
    );
    CREATE INDEX IF NOT EXISTS video_runs_video ON video_runs(video_id);
    CREATE TABLE IF NOT EXISTS video_segments (
        video_id TEXT NOT NULL, idx INTEGER NOT NULL, start REAL NOT NULL, "end" REAL NOT NULL, text TEXT,
        expires_at TEXT, PRIMARY KEY(video_id, idx)
    );
    CREATE TABLE IF NOT EXISTS video_frames (
        video_id TEXT NOT NULL, t REAL NOT NULL, reason TEXT, spoken_text TEXT, reading_json TEXT,
        PRIMARY KEY(video_id, t)
    );
    CREATE TABLE IF NOT EXISTS video_digests (
        video_id TEXT PRIMARY KEY, item_id INTEGER, digest_json TEXT NOT NULL, model TEXT, run_id TEXT, created_at TEXT
    );
    """)


# ---------- S5 (30~39) ----------
# 원칙(S5_TASK 5.9): weekly가 만드는 모든 행에 run_id. 그 주 현재판은 weeks.current_run_id, 지우는 행 없음
# 30: 표기 정규화 별칭 표
register(30, """
    CREATE TABLE IF NOT EXISTS aliases (
        id INTEGER PRIMARY KEY, canonical TEXT NOT NULL, alias TEXT NOT NULL, keyword_id TEXT, reason TEXT,
        evidence_json TEXT, origin TEXT NOT NULL CHECK(origin IN ('normalizer','editor')),
        status TEXT NOT NULL CHECK(status IN ('candidate','approved','rejected')), seen INTEGER NOT NULL DEFAULT 1,
        run_id TEXT, updated_at TEXT, UNIQUE(canonical, alias)
    );
    """)
# 31: 주차, 묶음, 묶음 구성원, 판정한 쌍. member_embeddings는 영상(digest 요약)·레포(oneliner + description)처럼
# item_embeddings(글 본문)에 없는 구성원의 묶기용 임베딩
register(31, """
    CREATE TABLE IF NOT EXISTS weeks (
        week TEXT PRIMARY KEY, start_day TEXT NOT NULL, end_day TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('open','clustered','selected','written','done','failed')),
        current_run_id TEXT
    );
    CREATE TABLE IF NOT EXISTS clusters (
        id INTEGER PRIMARY KEY, run_id TEXT NOT NULL, week TEXT NOT NULL, label TEXT, channels_json TEXT,
        n_items INTEGER NOT NULL, score REAL, body_json TEXT
    );
    CREATE INDEX IF NOT EXISTS clusters_run ON clusters(run_id);
    CREATE TABLE IF NOT EXISTS cluster_items (
        cluster_id INTEGER NOT NULL, member TEXT NOT NULL, channel TEXT NOT NULL,
        joined_by TEXT NOT NULL CHECK(joined_by IN ('seed','embed','keyword','alias','decide','same_url')),
        sim REAL, PRIMARY KEY(cluster_id, member)
    );
    CREATE TABLE IF NOT EXISTS cluster_pairs (
        id INTEGER PRIMARY KEY, run_id TEXT NOT NULL, a TEXT NOT NULL, b TEXT NOT NULL, sim REAL,
        cross_channel INTEGER NOT NULL, decided INTEGER NOT NULL DEFAULT 0, answer INTEGER, confidence REAL,
        reason TEXT, step_id INTEGER
    );
    CREATE INDEX IF NOT EXISTS cluster_pairs_run ON cluster_pairs(run_id);
    CREATE TABLE IF NOT EXISTS member_embeddings (
        member TEXT NOT NULL, model TEXT NOT NULL, dim INTEGER NOT NULL, vec BLOB NOT NULL, text_hash TEXT,
        created_at TEXT, PRIMARY KEY(member, model)
    );
    """)
# 32: 선별 계획, 토픽, 토픽 페이지(라운드별), 판정, 토픽 ↔ 근거
register(32, """
    CREATE TABLE IF NOT EXISTS briefing_plans (
        id INTEGER PRIMARY KEY, run_id TEXT NOT NULL, week TEXT NOT NULL,
        source TEXT NOT NULL CHECK(source IN ('model','fallback')), plan_json TEXT NOT NULL, created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS topics (
        run_id TEXT NOT NULL, topic_id TEXT NOT NULL, week TEXT NOT NULL, cluster_ids_json TEXT NOT NULL,
        rank INTEGER NOT NULL, lead INTEGER NOT NULL, relation_type TEXT, relation_topic_id TEXT,
        status TEXT NOT NULL CHECK(status IN ('selected','passed','checked','failed')), final_round INTEGER,
        title TEXT, summary TEXT, angle TEXT, PRIMARY KEY(run_id, topic_id)
    );
    CREATE TABLE IF NOT EXISTS topic_pages (
        id INTEGER PRIMARY KEY, run_id TEXT NOT NULL, topic_id TEXT NOT NULL, round INTEGER NOT NULL,
        page_json TEXT NOT NULL, raw_json TEXT, step_id INTEGER, UNIQUE(run_id, topic_id, round)
    );
    CREATE TABLE IF NOT EXISTS verdicts (
        id INTEGER PRIMARY KEY, run_id TEXT NOT NULL, topic_id TEXT NOT NULL, round INTEGER NOT NULL,
        checker TEXT NOT NULL CHECK(checker IN ('code','critic')), status TEXT NOT NULL CHECK(status IN ('pass','reject')),
        issues_json TEXT, autofix_json TEXT, step_id INTEGER
    );
    CREATE TABLE IF NOT EXISTS topic_evidence (
        run_id TEXT NOT NULL, topic_id TEXT NOT NULL, evidence_id TEXT NOT NULL, member TEXT NOT NULL,
        field TEXT NOT NULL CHECK(field IN ('point','number','event','context','contribution')), idx INTEGER NOT NULL
    );
    CREATE INDEX IF NOT EXISTS topic_evidence_topic ON topic_evidence(run_id, topic_id);
    """)
# 33: 과거 대조용 토픽 임베딩, 실행 요약
register(33, """
    CREATE TABLE IF NOT EXISTS topic_embeddings (
        topic_id TEXT NOT NULL, run_id TEXT NOT NULL, model TEXT NOT NULL, dim INTEGER NOT NULL, vec BLOB NOT NULL,
        text_hash TEXT, PRIMARY KEY(topic_id, run_id, model)
    );
    ALTER TABLE runs ADD COLUMN week TEXT;
    ALTER TABLE runs ADD COLUMN summary_json TEXT;
    """)
# 34: 토픽의 관계 문장(코드 문장틀 "N월 N주차 '제목' 토픽의 후속", S5_TASK 5.5 "topics에 저장")
register(34, """
    ALTER TABLE topics ADD COLUMN relation_label TEXT;
    """)


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
