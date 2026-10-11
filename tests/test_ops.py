"""S6b B1~B5(nightly 범위·단계·부분 실패·잠금·이미 처리한 항목), B10(ops weekly). 가짜 실행기와 임시 DB, 네트워크·LLM 0."""

from __future__ import annotations

import json
import time
from datetime import date, datetime
from types import SimpleNamespace

import pytest

from trendsit import ops
from trendsit.core.config import OpsConfig
from trendsit.core.db import DB, KST
from trendsit.core.trace import Tracer
from trendsit.deep.plan import repo_candidates, video_candidates

CFG = OpsConfig(start_day=date(2026, 10, 12), max_catchup_days=7, weekly_lock_wait_min=1, step_timeout_min=60,
                video_timeout_min=240, weekly_timeout_min=120)
NO_CATCHUP = CFG.model_copy(update={"start_day": date(2030, 1, 1)})  # 따라잡을 날이 없는 설정(weekly만 보는 테스트)
PREFIX = ["uv", "run", "python", "-m", "trendsit"]
REPO_Q = [{"full_name": "o/fresh", "max_depth": 2, "reason": "계획"}]
VIDEO_Q = [{"video_id": "VIDEO000001", "mode": "captions", "start_sec": None, "end_sec": None, "reason": "r"}]


def tail(cmd):
    return cmd[cmd.index("trendsit") + 1:] if "trendsit" in cmd else cmd


def at(y, m, d, h=2) -> datetime:
    return datetime(y, m, d, h, 0, tzinfo=KST)


class Fake:
    """단계 명령을 기록하고 정해진 종료 코드를 돌려주는 실행기. fail에 든 이름(plan, video, collect...)의 단계는 1."""

    def __init__(self, db=None, fail=(), queue=None, weekly_status="done", cost=0.0, repos=None):
        self.db, self.fail, self.queue, self.weekly_status, self.cost = db, set(fail), queue or {}, weekly_status, cost
        self.repos = repos or {}  # 날 -> 계획의 repo_queue
        self.cmds: list[list[str]] = []
        self.timeouts: list[float | None] = []

    def __call__(self, cmd, timeout=None):
        self.cmds.append(cmd)
        self.timeouts.append(timeout)
        args = cmd[cmd.index("trendsit") + 1:] if "trendsit" in cmd else cmd
        name = args[0] if args[0] != "plan" else f"plan {args[1]}"
        name = {"plan run": "plan", "deep": "deep_text", "repo-analyze": "repo_analyze"}.get(name, name)
        spec = args[args.index("--spec") + 1] if "--spec" in args else None
        if name == "plan show":
            day = args[args.index("--day") + 1]
            if "--video-queue" in args:
                return 0, json.dumps(self.queue.get(day, [])), ""
            return 0, json.dumps({"video_queue": [], "repo_queue": self.repos.get(day, []), "_source": "model"}), ""
        if name in self.fail:
            return 1, "일부 출력\n", "Traceback\nBudgetExceeded: 상한 초과 " + "x" * 300
        if name == "plan" and self.cost:  # 하위 프로세스가 남기는 실행 기록(비용)을 흉내
            tr = Tracer(self.db, "plan", spec)
            tr.step(kind="llm", role="editor_plan", cost_usd=self.cost)
            tr.finish("ok")
        if name == "weekly":
            self.db.conn.execute("INSERT INTO weeks(week, start_day, end_day, status) VALUES (?,?,?,?) "
                                 "ON CONFLICT(week) DO UPDATE SET status=excluded.status",
                                 (args[args.index("--week") + 1], "2026-10-12", "2026-10-18", self.weekly_status))
            self.db.conn.commit()
        return 0, "", ""

    def names(self):
        """단계 이름: plan·deep·video는 두 낱말(plan run), 나머지는 첫 낱말."""
        return [" ".join(t[:2]) if t[0] in ("plan", "deep", "video") else t[0] for t in map(tail, self.cmds)]


@pytest.fixture
def db(tmp_path):
    return DB(tmp_path / "t.db")


def nightly_rows(db):
    return [dict(r) | {"summary": json.loads(r["summary_json"])} for r in
            db.conn.execute("SELECT * FROM runs WHERE kind='nightly' ORDER BY started_at, rowid")]


def run_night(db, tmp_path, now, fake=None, **kw):
    fake = fake or Fake(db)
    code = ops.nightly(db, CFG, now=now, runner=fake, data_dir=tmp_path, **kw)
    return code, fake


def assert_c1(db, today, cfg=CFG):
    """C-1: 연속한 날짜, start_day 이상, 어제 이하, max_catchup_days 이하, 이전 행과 겹치지 않음."""
    seen: set[str] = set()
    for row in nightly_rows(db):
        days = [date.fromisoformat(d) for d in row["summary"]["days"]]
        assert len(days) <= cfg.max_catchup_days
        assert all((b - a).days == 1 for a, b in zip(days, days[1:], strict=False))
        if days:
            assert days[0] >= cfg.start_day and days[-1] < today
        assert not seen & {d.isoformat() for d in days}
        seen |= {d.isoformat() for d in days}


# ---------- B1 ----------
def test_b1_no_previous_row(db, tmp_path):
    code, _ = run_night(db, tmp_path, at(2026, 10, 15))
    assert code == 0 and nightly_rows(db)[-1]["summary"]["days"] == ["2026-10-12", "2026-10-13", "2026-10-14"]
    assert_c1(db, date(2026, 10, 15))


def test_b1_continues_after_last_day(db, tmp_path):
    run_night(db, tmp_path, at(2026, 10, 14))  # 12, 13
    assert nightly_rows(db)[-1]["summary"]["days"] == ["2026-10-12", "2026-10-13"]
    run_night(db, tmp_path, at(2026, 10, 16))
    assert nightly_rows(db)[-1]["summary"]["days"] == ["2026-10-14", "2026-10-15"]
    assert_c1(db, date(2026, 10, 16))


def test_b1_ten_days_behind_is_capped_then_resumed(db, tmp_path):
    run_night(db, tmp_path, at(2026, 10, 22))
    assert nightly_rows(db)[-1]["summary"]["days"] == [f"2026-10-{d}" for d in range(12, 19)]
    run_night(db, tmp_path, at(2026, 10, 22))  # 같은 밤 다시: 남은 날을 이어서
    assert nightly_rows(db)[-1]["summary"]["days"] == ["2026-10-19", "2026-10-20", "2026-10-21"]
    assert_c1(db, date(2026, 10, 22))


def test_b1_empty_range_records_row_without_commands(db, tmp_path):
    run_night(db, tmp_path, at(2026, 10, 14))
    code, fake = run_night(db, tmp_path, at(2026, 10, 14))  # 어제(13)까지 이미 시도함
    last = nightly_rows(db)[-1]
    assert code == 0 and fake.cmds == [] and last["status"] == "ok"
    assert last["summary"] == {"days": [], "steps": [], "cost_usd": 0.0}
    assert_c1(db, date(2026, 10, 14))


def test_b1_start_day_floor(db, tmp_path):
    code, fake = run_night(db, tmp_path, at(2026, 10, 12))  # 어제(11) < start_day
    assert code == 0 and fake.cmds == [] and nightly_rows(db)[-1]["summary"]["days"] == []


def test_b1_day_option_runs_only_that_day(db, tmp_path):
    run_night(db, tmp_path, at(2026, 10, 14))
    code, fake = run_night(db, tmp_path, at(2026, 10, 20), day=date(2026, 10, 12))
    assert code == 0 and nightly_rows(db)[-1]["summary"]["days"] == ["2026-10-12"]
    assert ["plan run", "deep text", "plan show", "plan show"] == [n for n in fake.names() if n.startswith(("plan", "deep"))]
    assert fake.names()[0] == "collect" and fake.cmds[0][fake.cmds[0].index("--since") + 1] == "2026-10-11"


# ---------- B2 ----------
def test_b2_step_order_and_args(db, tmp_path):
    repo_q = REPO_Q
    fake = Fake(db, queue={"2026-10-12": VIDEO_Q}, repos={"2026-10-12": repo_q})  # 13일은 빈 큐
    code, _ = run_night(db, tmp_path, at(2026, 10, 14), fake)
    w = "RUN-2026-W42"
    q = str(tmp_path / "tmp" / "video-queue-2026-10-12.json")
    rq = str(tmp_path / "tmp" / "repo-queue-2026-10-12.json")
    assert code == 0
    assert [tail(c) for c in fake.cmds] == [
        ["collect", "--since", "2026-10-11", "--until", "2026-10-14", "--spec", w],
        ["filter", "--since", "2026-10-12", "--until", "2026-10-13", "--spec", w],
        ["summarize", "--since", "2026-10-12", "--until", "2026-10-13", "--spec", w],
        ["plan", "run", "--day", "2026-10-12", "--spec", w],
        ["deep", "text", "--day", "2026-10-12", "--spec", w],
        ["plan", "show", "--day", "2026-10-12", "--video-queue"],
        ["video", "run", "--queue", q, "--spec", w],
        ["plan", "show", "--day", "2026-10-12"],
        ["repo-analyze", "--week", "2026-W42", "--queue", rq, "--spec", w],
        ["plan", "run", "--day", "2026-10-13", "--spec", w],
        ["deep", "text", "--day", "2026-10-13", "--spec", w],
        ["plan", "show", "--day", "2026-10-13", "--video-queue"],  # 빈 큐: video 명령 없음
        ["plan", "show", "--day", "2026-10-13"],  # 빈 레포 큐: repo-analyze 없음
    ]
    assert json.loads(open(rq).read()) == repo_q  # 계획의 레포 큐만(이미 카드 있는 레포는 계획이 뺌)
    video = next(c for c in fake.cmds if "video" in tail(c)[:1])
    assert video[:5] == ["uv", "run", "--extra", "video", "python"]  # video만 --extra video
    assert all(c[:5] == PREFIX for c in fake.cmds if "video" not in tail(c)[:1])
    assert json.loads(open(q).read()) == VIDEO_Q
    assert (tmp_path / "logs" / "ops" / "2026-10-14-nightly.log").exists()


def test_b2_week_tag_follows_each_day(db, tmp_path):
    cfg = CFG.model_copy(update={"start_day": date(2026, 10, 18)})  # 일(W42), 월(W43)
    fake = Fake(db)
    ops.nightly(db, cfg, now=at(2026, 10, 20), runner=fake, data_dir=tmp_path)
    specs = [(tail(c)[0], c[c.index("--spec") + 1], c[c.index("--week") + 1] if "--week" in c else None)
             for c in fake.cmds if "--spec" in c]
    assert specs[0] == ("collect", "RUN-2026-W43", None)  # 수집·필터·요약: 범위 마지막 날(월) 주차
    assert ("plan", "RUN-2026-W42", None) in specs and ("plan", "RUN-2026-W43", None) in specs
    assert nightly_rows(db)[-1]["spec"] == "RUN-2026-W43"


# ---------- B3 ----------
def test_b3_partial_failure_continues(db, tmp_path):
    fake = Fake(db, fail={"collect", "video"}, queue={"2026-10-12": VIDEO_Q, "2026-10-13": VIDEO_Q},
                repos={"2026-10-12": REPO_Q, "2026-10-13": REPO_Q}, cost=0.21)
    code, _ = run_night(db, tmp_path, at(2026, 10, 14), fake)
    assert code == 1
    assert fake.names().count("repo-analyze") == 2 and fake.names()[:3] == ["collect", "filter", "summarize"]  # 나머지 단계 모두 실행
    row = nightly_rows(db)[-1]
    assert row["status"] == "partial" and row["spec"] == "RUN-2026-W42"
    s = row["summary"]
    assert set(s) == {"days", "steps", "cost_usd"} and s["days"] == ["2026-10-12", "2026-10-13"]
    assert s["cost_usd"] == pytest.approx(0.42)  # plan 두 번 0.21씩
    assert all(set(x) >= {"name", "day", "exit", "sec"} for x in s["steps"])
    bad = [x for x in s["steps"] if x["exit"] != 0]
    assert [(x["name"], x["day"]) for x in bad] == [("collect", None), ("video", "2026-10-12"), ("video", "2026-10-13")]
    assert all(x["error"].startswith("BudgetExceeded: 상한 초과") and len(x["error"]) <= 200 for x in bad)
    assert [x["name"] for x in s["steps"] if x["day"] == "2026-10-12"] == ["plan", "deep_text", "video", "repo_analyze"]
    assert all("error" not in x for x in s["steps"] if x["exit"] == 0)


def test_b3_all_ok_is_status_ok(db, tmp_path):
    code, _ = run_night(db, tmp_path, at(2026, 10, 13))
    assert code == 0 and nightly_rows(db)[-1]["status"] == "ok"
    assert all(x["exit"] == 0 for x in nightly_rows(db)[-1]["summary"]["steps"])


# ---------- B4 ----------
def test_b4_nightly_skips_when_locked(db, tmp_path):
    fake = Fake(db)
    with ops.ops_lock(tmp_path) as held:
        assert held
        code = ops.nightly(db, CFG, now=at(2026, 10, 15), runner=fake, data_dir=tmp_path)
    assert code == 3 and fake.cmds == []
    row = nightly_rows(db)[-1]
    assert row["status"] == "skipped" and row["note"] == "잠금: 다른 ops 실행 중" and row["summary"]["days"] == []
    run_night(db, tmp_path, at(2026, 10, 15))  # 잠금이 풀리면 건너뛴 날들을 다시 범위에 넣음
    assert nightly_rows(db)[-1]["summary"]["days"] == ["2026-10-12", "2026-10-13", "2026-10-14"]


def test_b4_weekly_waits_then_gives_up(db, tmp_path, monkeypatch):
    monkeypatch.setattr(ops, "LOCK_POLL_SEC", 0.1)
    fake = Fake(db)
    with ops.ops_lock(tmp_path):
        t0 = time.monotonic()
        code = ops.weekly(db, NO_CATCHUP, now=at(2026, 10, 19, 7), runner=fake, data_dir=tmp_path, wait_sec=1)
        waited = time.monotonic() - t0
    assert code == 3 and fake.cmds == [] and 0.9 <= waited < 3
    row = db.conn.execute("SELECT status, note FROM runs WHERE kind='ops-weekly'").fetchone()
    assert tuple(row) == ("skipped", "잠금: 다른 ops 실행 중")


def test_b4_weekly_gets_lock_released_while_waiting(db, tmp_path, monkeypatch):
    import threading

    monkeypatch.setattr(ops, "LOCK_POLL_SEC", 0.05)
    started = threading.Event()

    def hold():
        with ops.ops_lock(tmp_path):
            started.set()
            time.sleep(0.3)

    t = threading.Thread(target=hold)
    t.start()
    started.wait()
    code = ops.weekly(db, NO_CATCHUP, now=at(2026, 10, 19, 7), runner=Fake(db), data_dir=tmp_path, wait_sec=3)
    t.join()
    assert code == 0


# ---------- B5 ----------
def add_video(db, i, day="2026-10-06", digest=False):
    cur = db.conn.execute("INSERT INTO items(source_id, channel, external_id, title, published_at, day, week) "
                          "VALUES ('yt','video',?,?,?,?,'2026-W41')", (f"v{i}", f"영상 {i}", f"{day}T10:00:00+09:00", day))
    db.conn.execute("INSERT INTO videos(item_id, video_id, duration_sec) VALUES (?,?,600)", (cur.lastrowid, f"VIDEO{i:06d}"))
    if digest:
        db.conn.execute("INSERT INTO video_digests(video_id, item_id, digest_json) VALUES (?,?,'{}')",
                        (f"VIDEO{i:06d}", cur.lastrowid))
    db.conn.commit()


def test_b5_plan_candidates_skip_already_processed(db):
    from trendsit.core import config

    add_video(db, 1, digest=True)
    add_video(db, 2)
    add_video(db, 3)
    for name, stars in (("o/done", 500), ("o/fresh", 300), ("o/other-week", 100)):
        db.save_trending("2026-W41", {"full_name": name, "rank": 1, "stars_this_week": stars, "filter_status": "pass"}, "r")
    db.conn.execute("INSERT INTO repo_cards(week, full_name, card_json) VALUES ('2026-W41','o/done','{}')")
    db.conn.execute("INSERT INTO repo_cards(week, full_name, card_json) VALUES ('2026-W40','o/other-week','{}')")  # 다른 주 카드
    db.conn.commit()
    videos = video_candidates(db, date(2026, 10, 6), config.load("deep.yaml"))
    assert [v.video_id for v in videos] == ["VIDEO000002", "VIDEO000003"]  # digest 있는 1번만 빠짐
    repos = repo_candidates(SimpleNamespace(db=db), date(2026, 10, 6), hype=False)
    assert [r.full_name for r in repos] == ["o/fresh", "o/other-week"]  # 그 주 카드가 있는 레포만 빠짐


def test_b5_removed_repos_do_not_take_candidate_slots(db):
    from trendsit.deep.plan import REPO_CANDIDATES

    n = REPO_CANDIDATES + 5
    for i in range(n):
        db.save_trending("2026-W41", {"full_name": f"o/r{i:02d}", "rank": i, "stars_this_week": 1000 - i,
                                      "filter_status": "pass"}, "r")
    for i in range(5):  # 별 상위 5개는 이미 카드 있음
        db.conn.execute("INSERT INTO repo_cards(week, full_name, card_json) VALUES ('2026-W41',?, '{}')", (f"o/r{i:02d}",))
    db.conn.commit()
    names = [r.full_name for r in repo_candidates(SimpleNamespace(db=db), date(2026, 10, 6), hype=False)]
    assert len(names) == REPO_CANDIDATES and names[0] == "o/r05"


# ---------- B10 ----------
@pytest.mark.parametrize("now,week", [
    (at(2026, 10, 19, 7), "2026-W42"),
    (at(2027, 1, 4, 7), "2026-W53"),   # 53주 있는 해의 마지막 주
    (at(2025, 1, 6, 7), "2025-W01"),   # 전년 12월 말 날짜가 속한 다음 해 1주
])
def test_b10_previous_iso_week(db, tmp_path, now, week):
    fake = Fake(db)
    assert ops.weekly(db, NO_CATCHUP, now=now, runner=fake, data_dir=tmp_path) == 0
    assert tail(fake.cmds[0]) == ["weekly", "--week", week, "--spec", f"RUN-{week}"]
    assert fake.cmds[1] == ["python3", "site_src/build.py"]
    assert db.conn.execute("SELECT status FROM weeks WHERE week=?", (week,)).fetchone()[0] == "published"
    assert not any("--force" in c for c in fake.cmds)  # C-8


def test_b10_weekly_failure_does_not_publish(db, tmp_path):
    fake = Fake(db, fail={"weekly"})
    assert ops.weekly(db, NO_CATCHUP, now=at(2026, 10, 19, 7), runner=fake, data_dir=tmp_path) == 1
    assert [tail(c)[0] for c in fake.cmds] == ["weekly"]  # 빌드 호출 없음
    row = db.conn.execute("SELECT status, summary_json FROM runs WHERE kind='ops-weekly'").fetchone()
    assert row[0] == "failed" and json.loads(row[1])["steps"][0]["exit"] == 1


def test_b10_unfinished_week_is_not_published(db, tmp_path):
    fake = Fake(db, weekly_status="written")  # 일부 토픽만 끝난 주
    assert ops.weekly(db, NO_CATCHUP, now=at(2026, 10, 19, 7), runner=fake, data_dir=tmp_path) == 1
    assert fake.cmds[-1] != ["python3", "site_src/build.py"]
    assert db.conn.execute("SELECT status FROM weeks").fetchone()[0] == "written"


def test_b10_build_failure_returns_1(db, tmp_path):
    class BuildFails(Fake):
        def __call__(self, cmd, timeout=None):
            return (1, "", "빌드 실패") if cmd[0] == "python3" else super().__call__(cmd, timeout)

    fake = BuildFails(db)
    assert ops.weekly(db, NO_CATCHUP, now=at(2026, 10, 19, 7), runner=fake, data_dir=tmp_path) == 1
    assert db.conn.execute("SELECT status FROM weeks").fetchone()[0] == "done"


def test_b10_already_published_does_nothing(db, tmp_path):
    db.conn.execute("INSERT INTO weeks(week, start_day, end_day, status, published_at) "
                    "VALUES ('2026-W42','2026-10-12','2026-10-18','published','2026-10-19T07:10:00+09:00')")
    db.conn.commit()
    fake = Fake(db)
    assert ops.weekly(db, NO_CATCHUP, now=at(2026, 10, 19, 7), runner=fake, data_dir=tmp_path) == 0
    assert fake.cmds == []
    assert "이미 발행" in (tmp_path / "logs" / "ops" / "2026-10-19-weekly.log").read_text()


# ---------- CLI 연결 ----------
def test_cli_dispatch_and_exit_codes(db, monkeypatch):
    from trendsit import cli

    seen = []
    monkeypatch.setattr("trendsit.core.db.open_db", lambda *a, **k: db)
    monkeypatch.setattr(ops, "nightly", lambda d, cfg, day=None: seen.append(("nightly", day)) or 3)
    monkeypatch.setattr(ops, "weekly", lambda d, cfg, week=None: seen.append(("weekly", week)) or 0)
    assert cli.main(["ops", "nightly", "--day", "2026-10-12"]) == 3  # 종료 코드는 ops의 것 그대로
    assert cli.main(["ops", "weekly", "--week", "2026-W42"]) == 0
    assert cli.main(["ops", "weekly"]) == 0
    assert seen == [("nightly", date(2026, 10, 12)), ("weekly", "2026-W42"), ("weekly", None)]
    with pytest.raises(SystemExit):  # ops weekly는 --force를 받지 않는다(C-8)
        cli.main(["ops", "weekly", "--force"])


# ---------- 실패 이유(5.11): 예산 초과 메시지 ----------
def test_b3_error_finds_budget_message_on_stdout(db, tmp_path):
    class Real(Fake):
        """실제 하위 명령처럼: 예산 초과는 stdout 요약 줄(또는 stderr 중간)에, stderr 끝은 다른 줄."""

        def __call__(self, cmd, timeout=None):
            name = tail(cmd)[0]
            if name == "summarize":
                return 1, "요약 3건\nstopped: BudgetExceeded: 스펙 RUN-2026-W42 상한 초과: 누적 $1.4900\n", "경고: 다른 줄\n"
            if name == "collect":
                return 1, "", "BudgetExceeded: 단계 상한 초과\nuv 종료 안내 줄\n"
            if name == "filter":
                return 1, "", "Traceback\nValueError: 다른 오류\n"
            return super().__call__(cmd, timeout)

    run_night(db, tmp_path, at(2026, 10, 13), Real(db))
    err = {x["name"]: x["error"] for x in nightly_rows(db)[-1]["summary"]["steps"] if x["exit"]}
    assert "상한 초과" in err["summarize"] and "BudgetExceeded" in err["collect"]
    assert err["filter"] == "ValueError: 다른 오류"  # 예산 줄이 없으면 stderr 마지막 줄


# ---------- --day 손 실행: 범위 계산에서 빠지고, 어제 이후는 거부 ----------
def test_b1_manual_day_does_not_move_catchup_and_future_day_refused(db, tmp_path, capsys):
    code, fake = run_night(db, tmp_path, at(2026, 10, 20), day=date(2026, 10, 19))  # 어제 = 19
    assert code == 0 and nightly_rows(db)[-1]["summary"]["manual"] is True
    run_night(db, tmp_path, at(2026, 10, 20))  # 손 실행이 가장 늦은 날이어도 사이 날(12~)을 이어서 따라잡음
    assert nightly_rows(db)[-1]["summary"]["days"][0] == "2026-10-12"
    for bad in (date(2026, 10, 20), date(2026, 10, 25)):  # 오늘, 미래
        n = len(nightly_rows(db))
        code, fake = run_night(db, tmp_path, at(2026, 10, 20), day=bad)
        assert code == 2 and fake.cmds == [] and len(nightly_rows(db)) == n
    assert "이후 날은 돌리지 않음" in capsys.readouterr().err


# ---------- 단계 timeout ----------
def test_b3_timeouts_per_step_and_timeout_is_a_failed_step(db, tmp_path):
    class Slow(Fake):
        def __call__(self, cmd, timeout=None):
            super().__call__(cmd, timeout)
            if tail(cmd)[0] == "deep":
                return 124, "", "시간 초과: 3600초 넘겨 끝냄"
            return 0, json.dumps(VIDEO_Q) if "--video-queue" in cmd else json.dumps({"repo_queue": REPO_Q}), ""

    fake = Slow(db)
    code, _ = run_night(db, tmp_path, at(2026, 10, 13), fake)
    assert code == 1
    by_name = {" ".join(tail(c)[:2]): t for c, t in zip(fake.cmds, fake.timeouts, strict=True)}
    assert by_name["collect --since"] == 3600 and by_name["video run"] == 240 * 60 and by_name["repo-analyze --week"] == 3600
    steps = nightly_rows(db)[-1]["summary"]["steps"]
    assert [(x["name"], x["exit"]) for x in steps if x["exit"]] == [("deep_text", 124)]
    assert "시간 초과" in next(x for x in steps if x["exit"])["error"]
    assert [x["name"] for x in steps][-2:] == ["video", "repo_analyze"]  # 다음 단계는 계속(C-6)


def test_b10_weekly_timeout_value(db, tmp_path):
    fake = Fake(db)
    ops.weekly(db, NO_CATCHUP, now=at(2026, 10, 19, 7), runner=fake, data_dir=tmp_path)
    assert fake.timeouts[0] == 120 * 60


def test_run_subprocess_kills_process_group_on_timeout():
    t0 = time.monotonic()
    code, out, err = ops.run_subprocess(["bash", "-c", "echo 시작; sleep 30 & wait"], timeout=0.5)
    assert code == 124 and "시작" in out and "시간 초과" in err and time.monotonic() - t0 < 5
    assert ops.run_subprocess(["bash", "-c", "echo ok; exit 3"], timeout=5)[:2] == (3, "ok\n")


# ---------- git pull 실패는 runs 행에 남김 ----------
def test_pull_failure_is_recorded(db, tmp_path, monkeypatch):
    run_night(db, tmp_path, at(2026, 10, 13))
    assert "pull_failed" not in nightly_rows(db)[-1]["summary"] and "pull" not in (nightly_rows(db)[-1]["note"] or "")
    monkeypatch.setenv("TRENDSIT_PULL_FAILED", "1")
    run_night(db, tmp_path, at(2026, 10, 14))
    row = nightly_rows(db)[-1]
    assert row["summary"]["pull_failed"] is True and "git pull 실패" in row["note"]
    ops.weekly(db, NO_CATCHUP, now=at(2026, 10, 19, 7), runner=Fake(db), data_dir=tmp_path)
    w = db.conn.execute("SELECT note, summary_json FROM runs WHERE kind='ops-weekly'").fetchone()
    assert "git pull 실패" in w[0] and json.loads(w[1])["pull_failed"] is True


def test_repo_step_failure_when_plan_show_fails(db, tmp_path):
    class NoPlan(Fake):
        def __call__(self, cmd, timeout=None):
            if tail(cmd)[:2] == ["plan", "show"]:
                return 1, "", "2026-10-12 계획 없음"
            return super().__call__(cmd, timeout)

    code, fake = run_night(db, tmp_path, at(2026, 10, 13), NoPlan(db))
    steps = nightly_rows(db)[-1]["summary"]["steps"]
    assert code == 1 and [x["name"] for x in steps if x["exit"]] == ["video", "repo_analyze"]
    assert not any(tail(c)[0] in ("video", "repo-analyze") for c in fake.cmds)


def test_b3_cost_counts_unfinished_runs_within_window_only(db, tmp_path):
    old = Tracer(db, "plan", "RUN-2026-W42")  # 이 nightly 시작 전(손 실행): 세지 않음
    old.step(kind="llm", role="x", cost_usd=5.0)
    db.conn.execute("UPDATE steps SET t='2026-01-01T00:00:00+09:00'")
    db.conn.commit()

    class Killed(Fake):
        def __call__(self, cmd, timeout=None):
            if tail(cmd)[:2] == ["plan", "run"]:  # timeout으로 죽어 finish되지 못한 run: runs.cost_usd는 0이지만 호출은 기록됨
                Tracer(db, "plan", "RUN-2026-W42").step(kind="llm", role="editor_plan", cost_usd=0.3)
                return 124, "", "시간 초과"
            return super().__call__(cmd, timeout)

    run_night(db, tmp_path, at(2026, 10, 13), Killed(db))
    assert nightly_rows(db)[-1]["summary"]["cost_usd"] == pytest.approx(0.3)


# ---------- ops weekly: nightly 따라잡기를 먼저 ----------
def test_b10_weekly_catches_up_nightly_first_then_weekly(db, tmp_path):
    fake = Fake(db, fail={"collect"})  # nightly 단계가 실패해도 weekly는 진행
    code = ops.weekly(db, CFG, now=at(2026, 10, 19, 7), runner=fake, data_dir=tmp_path)  # 일요일(18) 미처리
    names = fake.names()
    assert code == 0 and names.index("collect") < names.index("plan run") < names.index("weekly")
    assert names[-2:] == ["weekly", "python3"] or names[-1] == "python3"
    assert nightly_rows(db)[-1]["summary"]["days"][-1] == "2026-10-18" and nightly_rows(db)[-1]["status"] == "partial"
    assert db.conn.execute("SELECT status FROM weeks").fetchone()[0] == "published"
    # 범위가 비면 바로 weekly
    fake2 = Fake(db)
    ops.weekly(db, CFG, week="2026-W43", now=at(2026, 10, 19, 7), runner=fake2, data_dir=tmp_path)
    assert fake2.names()[0] == "weekly"


# ---------- SIGTERM ----------
def test_sigterm_kills_child_group_and_cleans_up(db, tmp_path):
    import os
    import signal
    import threading

    class Hang(Fake):
        def __call__(self, cmd, timeout=None):
            if tail(cmd)[:2] == ["plan", "run"]:
                threading.Timer(0.3, os.kill, (os.getpid(), signal.SIGTERM)).start()
                return ops.run_subprocess(["bash", "-c", "echo $$ >%s; sleep 30 & wait" % (tmp_path / "pid")], timeout=20)
            return super().__call__(cmd, timeout)

    old = signal.signal(signal.SIGTERM, ops.on_sigterm)
    try:
        t0 = time.monotonic()
        with pytest.raises(SystemExit) as e:
            run_night(db, tmp_path, at(2026, 10, 13), Hang(db))
    finally:
        signal.signal(signal.SIGTERM, old)
    assert e.value.code == 143 and time.monotonic() - t0 < 10
    assert nightly_rows(db)[-1]["status"] == "failed"  # runs 행 마감
    with ops.ops_lock(tmp_path) as got:  # 잠금 해제
        assert got
    pid = int((tmp_path / "pid").read_text())
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)  # 하위 프로세스 그룹도 끝남


# ---------- ops.yaml 엄격 검증 ----------
@pytest.mark.parametrize("field,bad", [
    ("max_catchup_days", True), ("max_catchup_days", 0), ("max_catchup_days", -1), ("max_catchup_days", 1.5),
    ("max_catchup_days", "7"), ("step_timeout_min", False), ("weekly_lock_wait_min", 0),
    ("start_day", 20261012), ("start_day", "10/12"), ("start_day", None),
])
def test_ops_config_strict(field, bad):
    import yaml
    from pydantic import ValidationError

    ok = {"start_day": "2026-10-12", "max_catchup_days": 7, "weekly_lock_wait_min": 240, "step_timeout_min": 60,
          "video_timeout_min": 240, "weekly_timeout_min": 120}
    OpsConfig.model_validate(ok)
    OpsConfig.model_validate(yaml.safe_load("start_day: 2026-10-12\n") | ok | {"start_day": date(2026, 10, 12)})  # YAML 날짜
    with pytest.raises(ValidationError):
        OpsConfig.model_validate(ok | {field: bad})
