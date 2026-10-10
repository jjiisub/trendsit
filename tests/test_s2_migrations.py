"""M1: 마이그레이션 번호 키 등록(S1 리뷰). 기존 DB 보존, 대역 순서 무관, 늦게 추가된 번호, 실패 재시도."""

import sqlite3

import pytest

from trendsit.core.db import DB
from trendsit.core.migrations import MIGRATIONS, split_sql


def versions(db: DB) -> list[int]:
    return [r[0] for r in db.conn.execute("SELECT version FROM schema_migrations ORDER BY version")]


def tables(db: DB) -> set[str]:
    return {r[0] for r in db.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def legacy_db(path) -> None:
    """번호 키 방식 이전(user_version 방식)으로 1, 2번까지 적용된 DB."""
    conn = sqlite3.connect(path)
    for n in (1, 2):
        conn.executescript(MIGRATIONS[n])
    conn.execute("PRAGMA user_version = 2")
    conn.execute("INSERT INTO items(source_id, channel, external_id, title) VALUES ('s', 'text', 'e1', '보존')")
    conn.commit()
    conn.close()


def test_existing_user_version_db_is_not_reapplied(tmp_path):
    path = tmp_path / "t.db"
    legacy_db(path)
    db = DB(path, migrations={1: MIGRATIONS[1], 2: MIGRATIONS[2]})
    # 2번(ALTER TABLE ADD COLUMN)을 다시 돌렸다면 duplicate column으로 실패했을 것
    assert versions(db) == [1, 2]
    assert db.conn.execute("SELECT title FROM items").fetchone()[0] == "보존"
    rows = db.conn.execute("SELECT applied_at FROM schema_migrations").fetchall()
    assert all(r[0] == "legacy user_version" for r in rows)


@pytest.mark.parametrize("order", [(10, 20), (20, 10)])
def test_bands_apply_in_any_registration_order(tmp_path, order):
    sql = {10: "CREATE TABLE s2_t(x INTEGER);", 20: "CREATE TABLE video_t(y INTEGER);"}
    registry = {1: MIGRATIONS[1], 2: MIGRATIONS[2]}
    for n in order:  # dict 등록 순서가 달라도
        registry[n] = sql[n]
    db = DB(tmp_path / "t.db", migrations=registry)
    assert versions(db) == [1, 2, 10, 20]
    assert {"s2_t", "video_t"} <= tables(db)
    assert db.conn.execute("PRAGMA user_version").fetchone()[0] == 20


def test_lower_number_added_after_higher_is_applied(tmp_path):
    path = tmp_path / "t.db"
    base = {1: MIGRATIONS[1], 2: MIGRATIONS[2]}
    DB(path, migrations={**base, 20: "CREATE TABLE video_t(y INTEGER);"}).close()
    db = DB(path, migrations={**base, 10: "CREATE TABLE s2_t(x INTEGER);", 20: "CREATE TABLE video_t(y INTEGER);"})
    assert versions(db) == [1, 2, 10, 20]
    assert "s2_t" in tables(db)


def test_failed_migration_is_not_recorded_and_retried(tmp_path):
    path = tmp_path / "t.db"
    base = {1: MIGRATIONS[1], 2: MIGRATIONS[2]}
    # 두 번째 문장이 실패: 첫 문장도 되돌려져야 한다(한 트랜잭션)
    bad = "CREATE TABLE half_t(x INTEGER); INSERT INTO no_such_table VALUES (1);"
    with pytest.raises(sqlite3.OperationalError):
        DB(path, migrations={**base, 11: bad})
    conn = sqlite3.connect(path)
    assert [r[0] for r in conn.execute("SELECT version FROM schema_migrations ORDER BY version")] == [1, 2]
    assert not conn.execute("SELECT 1 FROM sqlite_master WHERE name='half_t'").fetchone()
    conn.close()
    db = DB(path, migrations={**base, 11: "CREATE TABLE half_t(x INTEGER);"})
    assert versions(db) == [1, 2, 11]
    assert "half_t" in tables(db)


def test_fresh_db_and_rerun_apply_nothing_twice(tmp_path):
    path = tmp_path / "t.db"
    db = DB(path)
    assert versions(db) == sorted(MIGRATIONS)
    db.close()
    db = DB(path)
    assert db.migrate() == []
    # 마이그레이션 동안 바꾼 트랜잭션 모드는 원래대로(다른 쓰기의 with conn: 트랜잭션 유지)
    assert db.conn.isolation_level == ""


def test_split_sql_keeps_semicolons_in_strings():
    stmts = split_sql("CREATE TABLE a(x TEXT DEFAULT 'p;q');\nINSERT INTO a VALUES ('1;2');\n")
    assert len(stmts) == 2 and "'p;q'" in stmts[0] and "'1;2'" in stmts[1]


def test_registered_numbers_are_unique_and_banded():
    assert all(1 <= n <= 49 for n in MIGRATIONS)  # S5 대역 30~39, S6 대역 40~49(COMMON 9장)
