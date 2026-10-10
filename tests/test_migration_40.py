"""S6b B7: 마이그레이션 40(weeks에 published, published_at). 39까지 적용된 DB의 행 보존."""

import sqlite3

import pytest

from trendsit.core.db import DB
from trendsit.core.migrations import MIGRATIONS


def test_b7_weeks_published_keeps_rows(tmp_path):
    db = DB(tmp_path / "t.db", migrations={n: s for n, s in MIGRATIONS.items() if n < 40})
    assert 40 not in {r[0] for r in db.conn.execute("SELECT version FROM schema_migrations")}
    db.conn.execute("INSERT INTO weeks(week, start_day, end_day, status, current_run_id) VALUES "
                    "('2026-W40','2026-09-28','2026-10-04','done','run-a'), "
                    "('2026-W41','2026-10-05','2026-10-11','written','run-b')")
    db.conn.commit()
    with pytest.raises(sqlite3.IntegrityError):  # 40 전에는 published를 넣을 수 없다
        db.conn.execute("UPDATE weeks SET status='published' WHERE week='2026-W40'")
    db.conn.rollback()

    assert db.migrate() == [40]
    rows = {r["week"]: dict(r) for r in db.conn.execute("SELECT * FROM weeks")}
    assert rows["2026-W40"] == {"week": "2026-W40", "start_day": "2026-09-28", "end_day": "2026-10-04",
                                "status": "done", "current_run_id": "run-a", "published_at": None}
    assert rows["2026-W41"]["status"] == "written" and rows["2026-W41"]["current_run_id"] == "run-b"

    db.conn.execute("UPDATE weeks SET status='published', published_at='2026-10-12T07:10:00+09:00' WHERE week='2026-W40'")
    assert db.conn.execute("SELECT status, published_at FROM weeks WHERE week='2026-W40'").fetchone()[0] == "published"
    with pytest.raises(sqlite3.IntegrityError):
        db.conn.execute("UPDATE weeks SET status='archived' WHERE week='2026-W41'")
    db.conn.rollback()
    assert db.migrate() == []  # 다시 적용하지 않음
