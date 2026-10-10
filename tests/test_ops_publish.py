"""S6b B6(비용 꼬리표), B8(publish), B9(published 주 weekly 거부)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from tests.conftest import ENDPOINTS
from trendsit import cli, ops
from trendsit.core import config
from trendsit.core.budget import Budget, BudgetExceeded, PriceBook
from trendsit.core.config import ConfigError
from trendsit.core.db import DB
from trendsit.core.trace import Tracer


def budget_for(tmp_path, db, spec):
    cfg = config.BudgetConfig(phase="mvp", phase_total_usd=20.0, specs={"S5": 6.0, "RUN": 1.50})
    return Budget(cfg, spec, db, tmp_path / "state.json", key_status=None,
                  prices=PriceBook(tmp_path / "prices.json", fetch=lambda _id: ENDPOINTS))


def spend(db, spec, cost):
    tr = Tracer(db, "nightly", spec)
    tr.step(kind="llm", role="x", cost_usd=cost)
    tr.finish("ok")


def test_b6_run_tag_cap_per_week(tmp_path):
    db = DB(tmp_path / "t.db")
    spend(db, "RUN-2026-W42", 1.49)
    spend(db, "RUN-2026-W41", 1.40)
    b = budget_for(tmp_path, db, "RUN-2026-W42")
    b.refresh()
    assert b.spec_cap == 1.50 and b.spec_spent == pytest.approx(1.49)  # 사용액은 그 꼬리표만
    b.check(0.005, "작은 호출")
    with pytest.raises(BudgetExceeded, match="RUN-2026-W42"):
        b.check(0.02, "큰 호출")
    other = budget_for(tmp_path, db, "RUN-2026-W43")  # 다른 주 꼬리표는 따로 센다
    other.refresh()
    other.check(1.4, "다른 주")


@pytest.mark.parametrize("spec", ["RUN-x", "RUN-2026-W4", "RUN-2026-W42x", "S9", "run-2026-W42"])
def test_b6_bad_tag_or_unknown_spec_rejected(tmp_path, spec):
    db = DB(tmp_path / "t.db")
    with pytest.raises(ConfigError, match="상한이 없음"):
        budget_for(tmp_path, db, spec)


def test_b6_listed_spec_still_works(tmp_path):
    assert budget_for(tmp_path, DB(tmp_path / "t.db"), "S5").spec_cap == 6.0


def weeks_db(tmp_path, status):
    db = DB(tmp_path / "t.db")
    db.conn.execute("INSERT INTO weeks(week, start_day, end_day, status, current_run_id) "
                    "VALUES ('2026-W41','2026-10-05','2026-10-11',?, 'r1')", (status,))
    db.conn.commit()
    return db


def week_row(db):
    return db.conn.execute("SELECT status, published_at FROM weeks WHERE week='2026-W41'").fetchone()


def test_b8_publish_success_and_build_failure_and_not_ready(tmp_path):
    calls = []

    def build(code):
        def runner(cmd):
            calls.append(cmd)
            return code, "", "빌드 오류 한 줄" if code else ""
        return runner

    db = weeks_db(tmp_path, "done")
    assert ops.publish(db, "2026-W41", build(1)) == 1  # 빌드 실패: 상태 그대로
    assert tuple(week_row(db)) == ("done", None)
    assert ops.publish(db, "2026-W41", build(0)) == 0
    status, at = week_row(db)
    assert status == "published" and at and "T" in at
    assert calls[0] == ["python3", "site_src/build.py"]

    first = at
    assert ops.publish(db, "2026-W41", build(0)) == 0  # 다시 발행: published_at만 갱신
    assert week_row(db)["status"] == "published" and week_row(db)["published_at"] >= first
    assert ops.publish(db, "2026-W41", build(1)) == 1  # 빌드 실패여도 발행본 유지
    assert week_row(db)["status"] == "published"

    for status in ("open", "written", "failed"):
        (tmp_path / status).mkdir()
        db2 = weeks_db(tmp_path / status, status)
        n = len(calls)
        assert ops.publish(db2, "2026-W41", build(0)) == 2
        assert len(calls) == n and week_row(db2)["status"] == status  # 빌드도 안 부름
    assert ops.publish(DB(tmp_path / "empty.db"), "2026-W41", build(0)) == 2  # 없는 주


def counts(db):
    return {t: db.conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ("runs", "weeks", "topics")}


def test_b9_weekly_refuses_published_week(tmp_path, monkeypatch, capsys):
    db = weeks_db(tmp_path, "published")
    monkeypatch.setattr("trendsit.core.db.open_db", lambda *a, **k: db)
    before = counts(db)
    assert cli.main(["weekly", "--week", "2026-W41"]) == 2
    assert cli.main(["weekly", "--week", "2026-W41", "--from-step", "write"]) == 2
    assert cli.main(["write", "--week", "2026-W41"]) == 2
    assert "발행된 주: --force로 다시 실행" in capsys.readouterr().err
    assert counts(db) == before


def test_b9_weekly_force_runs(tmp_path, monkeypatch):
    db = weeks_db(tmp_path, "published")
    seen = []
    ctx = SimpleNamespace(tracer=Tracer(db, "weekly", "S5"), stopped=None, db=db)
    summary = {"week": "2026-W41", "status": "done", "select": {}, "write": {}, "review": {}, "cost_usd": 0, "duration_sec": 1}
    monkeypatch.setattr("trendsit.core.db.open_db", lambda *a, **k: db)
    monkeypatch.setattr("trendsit.core.context.open_ctx", lambda *a, **k: ctx)
    monkeypatch.setattr("trendsit.brief.pipeline.run_weekly", lambda week, c, **k: seen.append(week) or summary)
    monkeypatch.setattr("trendsit.brief.briefing.write_briefing_md", lambda *a, **k: "읽기본.md")
    assert cli.main(["weekly", "--week", "2026-W41", "--force"]) == 0
    assert seen == ["2026-W41"]


def test_b9_cluster_refuses_published_and_force_unpublishes(tmp_path, monkeypatch):
    db = weeks_db(tmp_path, "published")
    db.conn.execute("UPDATE weeks SET published_at='2026-10-12T07:10:00+09:00'")
    db.conn.commit()
    monkeypatch.setattr("trendsit.core.db.open_db", lambda *a, **k: db)
    assert cli.main(["cluster", "--week", "2026-W41"]) == 2
    assert tuple(week_row(db)) == ("published", "2026-10-12T07:10:00+09:00")

    def stop(*a, **k):  # --force는 발행을 풀고 진행(여기서는 진입 직후 멈춤)
        raise RuntimeError("stop")

    monkeypatch.setattr("trendsit.core.context.open_ctx", stop)
    with pytest.raises(RuntimeError):
        cli.main(["cluster", "--week", "2026-W41", "--force"])
    assert tuple(week_row(db)) == ("done", None)  # C-3: published가 아니면 published_at도 없음


def test_b9_weekly_force_clears_published_at(tmp_path, monkeypatch):
    db = weeks_db(tmp_path, "published")
    db.conn.execute("UPDATE weeks SET published_at='2026-10-12T07:10:00+09:00'")
    db.conn.commit()
    monkeypatch.setattr("trendsit.core.db.open_db", lambda *a, **k: db)
    monkeypatch.setattr("trendsit.core.context.open_ctx", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("stop")))
    with pytest.raises(RuntimeError):
        cli.main(["weekly", "--week", "2026-W41", "--force"])
    assert tuple(week_row(db)) == ("done", None)
