"""S6b 자동 실행: 매일 밤 분석(nightly), 월요일 브리핑·발행(weekly), 발행(publish).

- 단계는 하위 프로세스(`uv run python -m trendsit ...`)로 돌린다. 한 단계가 실패해도 다음 단계는 계속(C-6)
- 같은 시각에 ops 실행은 1개(flock, C-2). 로그는 data/logs/ops/<날짜>-<job>.log, 실행 기록은 runs 표
- 따라잡기: 직전 nightly가 시도한 날 다음부터 어제까지. 실패한 날은 다시 넣지 않는다(NG-3)
"""

from __future__ import annotations

import fcntl
import json
import subprocess
import sys
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from .collect.text import iso_week
from .core.config import ROOT, OpsConfig
from .core.db import DB, KST, now_kst
from .core.trace import Tracer

# 명령 하나를 실행해 (종료 코드, 표준 출력, 표준 오류)를 돌려준다. 테스트는 이 자리에 가짜 실행기를 넣는다
Runner = Callable[[list[str]], tuple[int, str, str]]
BUILD_CMD = ["python3", "site_src/build.py"]


def run_subprocess(cmd: list[str]) -> tuple[int, str, str]:
    try:
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    except OSError as e:  # 실행 파일이 없는 경우 등
        return 127, "", f"{type(e).__name__}: {e}"
    return p.returncode, p.stdout, p.stderr


def publish(db: DB, week: str, runner: Runner = run_subprocess) -> int:
    """사이트 빌드 → weeks.status 'published', published_at. 0 성공, 1 빌드 실패, 2 대상 아님."""
    row = db.conn.execute("SELECT status FROM weeks WHERE week=?", (week,)).fetchone()
    if row is None or row["status"] not in ("done", "published"):
        print(f"발행 불가: {week} 상태 {row['status'] if row else '없음'} (done 또는 published만)", file=sys.stderr)
        return 2
    code, out, err = runner(BUILD_CMD)
    if code != 0:
        last = next((x for x in reversed((err or out).strip().splitlines()) if x.strip()), "")
        print(f"사이트 빌드 실패(종료 코드 {code}): {last[:200]}", file=sys.stderr)
        return 1
    with db.conn:
        db.conn.execute("UPDATE weeks SET status='published', published_at=? WHERE week=?", (now_kst(), week))
    print(f"발행: {week}")
    return 0


# ---------- 잠금, 실행 기록 ----------
LOCK_POLL_SEC = 5.0
LOCK_NOTE = "잠금: 다른 ops 실행 중"


@contextmanager
def ops_lock(data_dir: Path, wait_sec: float = 0.0) -> Iterator[bool]:
    """data/locks/ops.lock에 flock. wait_sec까지 기다려 못 얻으면 False. 프로세스가 죽으면 OS가 풀어 준다."""
    path = data_dir / "locks" / "ops.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + wait_sec
    with open(path, "a") as f:
        got = False
        while not got:
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                got = True
            except BlockingIOError:
                left = deadline - time.monotonic()
                if left <= 0:
                    break
                time.sleep(min(LOCK_POLL_SEC, left))
        yield got


def _close_run(db: DB, tr: Tracer, status: str, summary: dict[str, Any]) -> None:
    tr.finish(status)
    with db.conn:
        db.conn.execute("UPDATE runs SET summary_json=? WHERE id=?", (json.dumps(summary, ensure_ascii=False), tr.run_id))


def _skipped(db: DB, kind: str, spec: str, summary: dict[str, Any]) -> int:
    _close_run(db, Tracer(db, kind, spec, LOCK_NOTE), "skipped", summary)
    print(LOCK_NOTE, file=sys.stderr)
    return 3


def _error_line(out: str, err: str) -> str:
    """실패 이유 한 줄(200자). 예산 초과 줄은 명령이 stdout에 쓸 수도 있어 둘 다에서 먼저 찾고, 없으면 stderr(없으면 stdout)의 마지막 줄."""
    lines = [x.strip() for x in (err + "\n" + out).splitlines() if x.strip()]
    hit = next((x for x in lines if "BudgetExceeded" in x or "상한 초과" in x), None)
    if hit is None:
        tail = [x.strip() for x in (err or out).splitlines() if x.strip()]
        hit = tail[-1] if tail else ""
    return hit[:200]


class StepLog:
    """단계 실행 + 로그 파일 + steps 기록. summary_json.steps의 한 칸을 만든다."""

    def __init__(self, runner: Runner, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.runner, self.path, self.steps = runner, path, []

    def run(self, cmd: list[str]) -> tuple[int, str, str, float]:
        t0 = time.monotonic()
        code, out, err = self.runner(cmd)
        sec = round(time.monotonic() - t0, 1)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(f"== {now_kst()} {' '.join(cmd)}\n{out}{err}== 종료 코드 {code}, {sec}초\n")
        return code, out, err, sec

    def note(self, text: str) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(f"== {now_kst()} {text}\n")

    def add(self, name: str, day: date | None, code: int, sec: float, out: str = "", err: str = "") -> None:
        step: dict[str, Any] = {"name": name, "day": day.isoformat() if day else None, "exit": code, "sec": sec}
        if code != 0:
            step["error"] = _error_line(out, err)
        self.steps.append(step)

    def step(self, name: str, day: date | None, args: list[str], extra: tuple[str, ...] = ()) -> tuple[int, str]:
        code, out, err, sec = self.run(["uv", "run", *extra, "python", "-m", "trendsit", *args])
        self.add(name, day, code, sec, out, err)
        return code, out


# ---------- nightly ----------
def _tag(d: date) -> str:
    """비용 꼬리표: 그날의 ISO 주차(RUN-2026-W42)."""
    return f"RUN-{iso_week(d)}"


def catchup_days(db: DB, cfg: OpsConfig, today: date) -> list[date]:
    """직전 nightly가 시도한 마지막 날 다음(없거나 start_day 앞이면 start_day)부터 어제까지, 앞에서 max_catchup_days일."""
    done = [date.fromisoformat(d) for (raw,) in db.conn.execute(
        "SELECT summary_json FROM runs WHERE kind='nightly' AND summary_json IS NOT NULL") for d in json.loads(raw).get("days", [])]
    first = max(max(done, default=cfg.start_day - timedelta(days=1)) + timedelta(days=1), cfg.start_day)
    n = min((today - timedelta(days=1) - first).days + 1, cfg.max_catchup_days)
    return [first + timedelta(days=i) for i in range(max(n, 0))]


def nightly(db: DB, cfg: OpsConfig, *, day: date | None = None, now: datetime | None = None,
            runner: Runner = run_subprocess, data_dir: Path | None = None) -> int:
    """따라잡기 범위(또는 --day 하루)의 단계를 순서대로. 0 모두 성공(범위 빔 포함), 1 단계 실패, 3 잠금 못 얻음."""
    now = (now or datetime.now(KST)).astimezone(KST)
    data_dir = data_dir or ROOT / "data"
    today = now.date()
    with ops_lock(data_dir) as got:
        if not got:
            return _skipped(db, "nightly", _tag(today - timedelta(days=1)),
                            {"days": [], "steps": [], "cost_usd": 0.0})
        days = [day] if day else catchup_days(db, cfg, today)
        tr = Tracer(db, "nightly", _tag(days[-1] if days else today - timedelta(days=1)),
                    f"nightly {days[0]}~{days[-1]}" if days else "nightly 범위 없음")
        log = StepLog(runner, data_dir / "logs" / "ops" / f"{today.isoformat()}-nightly.log")
        status = "failed"
        try:
            if days:
                first, last = days[0], days[-1]
                shared = ["--spec", _tag(last)]
                log.step("collect", None, ["collect", "--since", str(first - timedelta(days=1)), "--until", str(today), *shared])
                log.step("filter", None, ["filter", "--since", str(first), "--until", str(last), *shared])
                log.step("summarize", None, ["summarize", "--since", str(first), "--until", str(last), *shared])
            for d in days:
                tag = ["--spec", _tag(d)]
                log.step("plan", d, ["plan", "run", "--day", str(d), *tag])
                log.step("deep_text", d, ["deep", "text", "--day", str(d), *tag])
                _video(log, d, tag, data_dir)
                log.step("repo_analyze", d, ["repo-analyze", "--week", iso_week(d), *tag])
            status = "ok" if all(s["exit"] == 0 for s in log.steps) else "partial"
        finally:
            started = db.conn.execute("SELECT started_at FROM runs WHERE id=?", (tr.run_id,)).fetchone()[0]
            cost = db.conn.execute("SELECT COALESCE(SUM(cost_usd),0) FROM runs WHERE spec LIKE 'RUN-%' AND started_at>=?",
                                   (started,)).fetchone()[0]
            _close_run(db, tr, status, {"days": [d.isoformat() for d in days], "steps": log.steps, "cost_usd": round(cost, 4)})
    bad = [s for s in log.steps if s["exit"] != 0]
    print(f"nightly {status}: 날 {len(days)}개, 단계 {len(log.steps)}개 중 실패 {len(bad)}개")
    for s in bad:
        print(f"  실패 {s['name']} {s['day'] or ''}: {s['error']}", file=sys.stderr)
    return 0 if status == "ok" else 1


def _video(log: StepLog, d: date, tag: list[str], data_dir: Path) -> None:
    """계획의 영상 큐를 파일로 받아 video run. 큐가 비면 건너뜀(성공). plan show 실패는 영상 단계 실패."""
    code, out, err, sec = log.run(["uv", "run", "python", "-m", "trendsit", "plan", "show", "--day", str(d), "--video-queue"])
    queue: Any = []
    if code == 0:
        try:
            queue = json.loads(out)
        except ValueError:
            code, err = 1, "plan show 출력이 JSON이 아님"
    if code != 0:
        log.add("video", d, code, sec, out, err)
    elif not queue:
        log.add("video", d, 0, sec)
    else:
        path = data_dir / "tmp" / f"video-queue-{d}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(queue, ensure_ascii=False), encoding="utf-8")
        log.step("video", d, ["video", "run", "--queue", str(path), *tag], extra=("--extra", "video"))


# ---------- weekly ----------
def weekly(db: DB, cfg: OpsConfig, *, week: str | None = None, now: datetime | None = None,
           runner: Runner = run_subprocess, data_dir: Path | None = None, wait_sec: float | None = None) -> int:
    """지난 ISO 주차 weekly → 성공하면 publish. --force는 쓰지 않는다(C-8). 0 성공·이미 발행, 1 실패, 3 잠금 못 얻음."""
    now = (now or datetime.now(KST)).astimezone(KST)
    data_dir = data_dir or ROOT / "data"
    week = week or iso_week(now.date() - timedelta(days=7))
    spec = f"RUN-{week}"
    wait = cfg.weekly_lock_wait_min * 60 if wait_sec is None else wait_sec
    with ops_lock(data_dir, wait) as got:
        if not got:
            return _skipped(db, "ops-weekly", spec, {"week": week, "steps": []})
        tr = Tracer(db, "ops-weekly", spec, f"ops weekly {week}")
        log = StepLog(runner, data_dir / "logs" / "ops" / f"{now.date().isoformat()}-weekly.log")
        status, code = "failed", 1
        try:
            row = db.conn.execute("SELECT status FROM weeks WHERE week=?", (week,)).fetchone()
            if row and row["status"] == "published":
                print(f"이미 발행: {week}")
                log.note(f"이미 발행: {week}")
                status, code = "ok", 0
            else:
                wk, _ = log.step("weekly", None, ["weekly", "--week", week, "--spec", spec])
                if wk == 0:
                    t0 = time.monotonic()
                    pub = publish(db, week, lambda cmd: _logged(log, cmd))
                    log.add("publish", None, pub, round(time.monotonic() - t0, 1), err="빌드 실패 또는 발행 불가(로그 참고)")
                    status, code = ("ok", 0) if pub == 0 else ("failed", 1)
        finally:
            _close_run(db, tr, status, {"week": week, "steps": log.steps})
    return code


def _logged(log: StepLog, cmd: list[str]) -> tuple[int, str, str]:
    code, out, err, _ = log.run(cmd)
    return code, out, err
