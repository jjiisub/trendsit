"""S6b 자동 실행: 매일 밤 분석(nightly), 월요일 브리핑·발행(weekly), 발행(publish).

- 단계는 하위 프로세스(`uv run python -m trendsit ...`)로 돌린다. 한 단계가 실패해도 다음 단계는 계속(C-6)
- 같은 시각에 ops 실행은 1개(flock, C-2). 로그는 data/logs/ops/<날짜>-<job>.log, 실행 기록은 runs 표
- 따라잡기: 직전 nightly가 시도한 날 다음부터 어제까지. 실패한 날은 다시 넣지 않는다(NG-3)
"""

from __future__ import annotations

import fcntl
import json
import os
import signal
import subprocess
import sys
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager, suppress
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from .collect.text import iso_week
from .core.config import ROOT, OpsConfig
from .core.db import DB, KST, now_kst
from .core.trace import Tracer
from .export import export as export_site

# 명령 하나를 (종료 코드, 표준 출력, 표준 오류)로. 테스트는 이 자리에 가짜 실행기를 넣는다. timeout(초)을 넘기면 종료 코드 124
Runner = Callable[[list[str], float | None], tuple[int, str, str]]
Build = Callable[[list[str]], tuple[int, str, str]]
BUILD_CMD = [sys.executable, "site_src/build.py"]  # trendsit을 부른 python(uv의 venv, 3.12). 최소 PATH의 /usr/bin/python3(3.9)로는 build.py 문법이 안 맞음
TIMEOUT_CODE = 124


def run_subprocess(cmd: list[str], timeout: float | None = None) -> tuple[int, str, str]:
    try:
        # 새 세션으로 띄워 시간 초과 때 uv 아래 자식(python)까지 한 번에 끝낸다
        p = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
    except OSError as e:  # 실행 파일이 없는 경우 등
        return 127, "", f"{type(e).__name__}: {e}"
    try:
        out, err = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        with suppress(ProcessLookupError, PermissionError):
            os.killpg(p.pid, signal.SIGKILL)
        out, err = p.communicate()
        return TIMEOUT_CODE, out or "", f"{err or ''}\n시간 초과: {timeout:g}초 넘겨 끝냄"
    except BaseException:  # SIGTERM(on_sigterm의 SystemExit)·Ctrl-C: 하위 프로세스 그룹을 남기지 않고 올려 보냄(잠금·runs 마감은 호출한 쪽 finally)
        with suppress(ProcessLookupError, PermissionError):
            os.killpg(p.pid, signal.SIGKILL)
        p.wait()
        raise
    return p.returncode, out, err


def on_sigterm(signum: int, frame: Any) -> None:
    raise SystemExit(128 + signal.SIGTERM)


def rebuild_site(db: DB, runner: Build = run_subprocess, with_week: str | None = None) -> int:
    """export → 사이트 빌드 → data/site.json 교체. 0 성공, 1 export·빌드 실패(stderr 한 줄). weeks 행은 읽기만 한다.

    결과는 임시 파일로 받아 그 파일로 빌드하고, 성공했을 때만 data/site.json으로 바꾼다(실패하면 미발행 주가 site.json에 남지 않음).
    with_week: 아직 done인 그 주도 담는다(publish가 상태를 바꾸기 전에 export·build를 돌리기 위한 것).
    """
    final = db.path.parent / "site.json"
    tmp = final.with_name(f"{final.name}.{os.getpid()}.new")  # 프로세스마다 다른 임시 이름(nightly 재생성과 손 실행이 겹쳐도 서로 안 지움)
    try:
        try:
            export_site(db, tmp, with_week)
        except Exception as e:  # noqa: BLE001 - export가 무엇으로 죽든 상태는 그대로 두고 1 + 이유 한 줄(C-3)
            print(f"사이트 재생성 실패: export {type(e).__name__}: {e}"[:300].replace("\n", " "), file=sys.stderr)
            return 1
        code, out, err = runner([*BUILD_CMD, "--data", str(tmp)])
        if code != 0:
            last = next((x for x in reversed((err or out).strip().splitlines()) if x.strip()), "")
            print(f"사이트 재생성 실패: 빌드 종료 코드 {code}: {last[:200]}", file=sys.stderr)
            return 1
        os.replace(tmp, final)
    finally:
        tmp.unlink(missing_ok=True)
    return 0


def publish(db: DB, week: str, runner: Build = run_subprocess) -> int:
    """rebuild_site(그 주 포함) → weeks.status 'published', published_at. 0 성공, 1 export·빌드 실패, 2 대상 아님."""
    row = db.conn.execute("SELECT status FROM weeks WHERE week=?", (week,)).fetchone()
    if row is None or row["status"] not in ("done", "published"):
        print(f"발행 불가: {week} 상태 {row['status'] if row else '없음'} (done 또는 published만)", file=sys.stderr)
        return 2
    if rebuild_site(db, runner, week):
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

    def __init__(self, runner: Runner, path: Path, cfg: OpsConfig):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.runner, self.path, self.cfg, self.steps = runner, path, cfg, []

    def timeout(self, name: str) -> float:
        """단계별 상한(초). 영상은 구간 하나가 15분 안팎이라 길게, 주간 브리핑은 그다음, 나머지는 기본."""
        minutes = {"video": self.cfg.video_timeout_min, "weekly": self.cfg.weekly_timeout_min}.get(name, self.cfg.step_timeout_min)
        return minutes * 60

    def run(self, cmd: list[str], name: str = "") -> tuple[int, str, str, float]:
        t0 = time.monotonic()
        code, out, err = self.runner(cmd, self.timeout(name))
        sec = round(time.monotonic() - t0, 1)
        text = out + err
        if text and not text.endswith("\n"):
            text += "\n"
        with self.path.open("a", encoding="utf-8") as f:
            f.write(f"== {now_kst()} {' '.join(cmd)}\n{text}== 종료 코드 {code}, {sec}초\n")
        return code, out, err, sec

    def note(self, text: str) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(f"== {now_kst()} {text}\n")

    def add(self, name: str, day: date | None, code: int, sec: float, out: str = "", err: str = "") -> None:
        step: dict[str, Any] = {"name": name, "day": day.isoformat() if day else None, "exit": code, "sec": sec}
        if code != 0:
            step["error"] = _error_line(out, err)
        self.steps.append(step)

    def skip(self, name: str, day: date, reason: str) -> None:
        """실행하지 않은 단계를 실패로 기록(이후 단계가 앞 단계 결과에 기대는 경우)."""
        self.steps.append({"name": name, "day": day.isoformat(), "exit": 1, "sec": 0.0, "error": reason})
        self.note(f"{name} {day}: {reason}")

    def step(self, name: str, day: date | None, args: list[str], extra: tuple[str, ...] = ()) -> tuple[int, str]:
        code, out, err, sec = self.run(["uv", "run", *extra, "python", "-m", "trendsit", *args], name)
        self.add(name, day, code, sec, out, err)
        return code, out


# ---------- nightly ----------
def _tag(d: date) -> str:
    """비용 꼬리표: 그날의 ISO 주차(RUN-2026-W42)."""
    return f"RUN-{iso_week(d)}"


def catchup_days(db: DB, cfg: OpsConfig, today: date) -> list[date]:
    """직전 nightly가 시도한 마지막 날 다음(없거나 start_day 앞이면 start_day)부터 어제까지, 앞에서 max_catchup_days일."""
    rows = [json.loads(raw) for (raw,) in db.conn.execute(
        "SELECT summary_json FROM runs WHERE kind='nightly' AND summary_json IS NOT NULL")]
    done = [date.fromisoformat(d) for r in rows if not r.get("manual") for d in r.get("days", [])]  # --day 손 실행은 범위 계산에서 뺌
    first = max(max(done, default=cfg.start_day - timedelta(days=1)) + timedelta(days=1), cfg.start_day)
    n = min((today - timedelta(days=1) - first).days + 1, cfg.max_catchup_days)
    return [first + timedelta(days=i) for i in range(max(n, 0))]


def nightly(db: DB, cfg: OpsConfig, *, day: date | None = None, now: datetime | None = None,
            runner: Runner = run_subprocess, data_dir: Path | None = None) -> int:
    """따라잡기 범위(또는 --day 하루)의 단계를 순서대로. 0 모두 성공(범위 빔 포함), 1 단계 실패, 3 잠금 못 얻음."""
    now = (now or datetime.now(KST)).astimezone(KST)
    data_dir = data_dir or ROOT / "data"
    today = now.date()
    if day and day > today - timedelta(days=1):
        print(f"--day {day}: 어제({today - timedelta(days=1)}) 이후 날은 돌리지 않음", file=sys.stderr)
        return 2
    with ops_lock(data_dir) as got:
        if not got:
            return _skipped(db, "nightly", _tag(today - timedelta(days=1)),
                            {"days": [], "steps": [], "cost_usd": 0.0})
        return _nightly_locked(db, cfg, day, now, runner, data_dir, rebuild=True)


def _nightly_locked(db: DB, cfg: OpsConfig, day: date | None, now: datetime, runner: Runner, data_dir: Path,
                    rebuild: bool = False) -> int:
    """잠금을 쥔 채로 부른다(nightly, ops weekly의 앞 단계). rebuild: 끝에 사이트만 다시 만든다(weekly는 publish가 빌드하므로 안 씀)."""
    today = now.date()
    days = [day] if day else catchup_days(db, cfg, today)
    tr = Tracer(db, "nightly", _tag(days[-1] if days else today - timedelta(days=1)),
                (f"nightly {days[0]}~{days[-1]}" if days else "nightly 범위 없음") + _pull_note())
    log = StepLog(runner, data_dir / "logs" / "ops" / f"{today.isoformat()}-nightly.log", cfg)
    status = "failed"
    tried: list[date] = []  # 실제로 단계를 시작한 날. 중간에 끊기면 시작 못 한 날은 다음 밤 범위에 남는다
    try:
        if days:
            first, last = days[0], days[-1]
            shared = ["--spec", _tag(last)]
            log.step("collect", None, ["collect", "--since", str(first - timedelta(days=1)), "--until", str(today), *shared])
            log.step("filter", None, ["filter", "--since", str(first), "--until", str(last), *shared])
            log.step("summarize", None, ["summarize", "--since", str(first), "--until", str(last), *shared])
        for d in days:
            tried.append(d)
            tag = ["--spec", _tag(d)]
            plan_code, _ = log.step("plan", d, ["plan", "run", "--day", str(d), *tag])
            log.step("deep_text", d, ["deep", "text", "--day", str(d), *tag])
            for name in ("video", "repo_analyze"):
                if plan_code != 0:  # 계획이 없거나 옛 계획이면 이전 큐를 다시 쓰게 되므로 건너뜀
                    log.skip(name, d, "plan 실패로 건너뜀")
                else:
                    _queue_step(log, d, tag, data_dir, name)
        status = "ok" if all(s["exit"] == 0 for s in log.steps) else "partial"
    finally:
        started = db.conn.execute("SELECT started_at FROM runs WHERE id=?", (tr.run_id,)).fetchone()[0]
        # 호출 단위(steps) 기준: timeout으로 끝나지 못한 run의 비용도 잡고, 이 nightly의 시작~끝 구간만 센다
        cost = db.conn.execute("SELECT COALESCE(SUM(s.cost_usd),0) FROM steps s JOIN runs r ON r.id=s.run_id "
                               "WHERE r.spec LIKE 'RUN-%' AND s.t>=? AND s.t<=?", (started, now_kst())).fetchone()[0]
        summary: dict[str, Any] = {"days": [d.isoformat() for d in tried], "steps": log.steps, "cost_usd": round(cost, 4)}
        if day:
            summary["manual"] = True
        _close_run(db, tr, status, summary | _pull_summary())
    bad = [s for s in log.steps if s["exit"] != 0]
    print(f"nightly {status}: 날 {len(tried)}개, 단계 {len(log.steps)}개 중 실패 {len(bad)}개")
    for s in bad:
        print(f"  실패 {s['name']} {s['day'] or ''}: {s['error']}", file=sys.stderr)
    if rebuild and days:  # 범위 없는 nightly는 사이트가 바뀔 일이 없다. SIGTERM·예외로 나가는 경로(finally 뒤)에서는 부르지 않는다
        _rebuild_after(db, tr.run_id, log)
    return 0 if status == "ok" else 1


def _rebuild_after(db: DB, run_id: str, log: StepLog) -> None:
    """nightly 끝에 사이트만 다시 만들고(export → build → site.json), 결과를 그 nightly 행의 summary_json.site로만 남긴다.
    실패해도 nightly status·종료 코드·steps는 그대로(C-8). 이 nightly 자신의 export + build 단계는 다음 재생성부터 화면에 나온다."""
    codes: list[int] = []

    def run(cmd: list[str]) -> tuple[int, str, str]:
        res = _logged(log, cmd)
        codes.append(res[0])
        return res

    t0 = time.monotonic()
    try:
        code = rebuild_site(db, run)
        if code and codes:
            code = codes[-1]  # 빌드가 실패했으면 그 종료 코드(시간 초과 124)
    except Exception as e:  # noqa: BLE001 - 끝 단계는 nightly 결과를 바꾸지 않는다
        print(f"사이트 재생성 실패: {type(e).__name__}: {e}"[:300].replace("\n", " "), file=sys.stderr)
        code = 1
    site = {"exit": code, "sec": round(time.monotonic() - t0, 1)}
    with db.conn:
        db.conn.execute("UPDATE runs SET summary_json=json_set(summary_json, '$.site', json(?)) WHERE id=?",
                        (json.dumps(site), run_id))


def _queue_step(log: StepLog, d: date, tag: list[str], data_dir: Path, name: str) -> None:
    """계획의 큐(video: 영상 큐, repo_analyze: 레포 큐)를 파일로 받아 실행. 큐가 비면 건너뜀(성공). plan show 실패는 그 단계 실패.
    레포는 계획이 이미 그 주 카드가 있는 레포를 뺀 큐(C-7)라 같은 레포를 매일 다시 분석하지 않는다."""
    video = name == "video"
    code, out, err, sec = log.run(["uv", "run", "python", "-m", "trendsit", "plan", "show", "--day", str(d),
                                   *(["--video-queue"] if video else [])])
    queue: Any = []
    if code == 0:
        try:
            data = json.loads(out)
            queue = data if video else data["repo_queue"]
        except (ValueError, KeyError, TypeError):
            code, err = 1, "plan show 출력 형식 오류"
    if code != 0:
        log.add(name, d, code, sec, out, err)
    elif not queue:
        log.add(name, d, 0, sec)
    else:
        path = data_dir / "tmp" / f"{'video' if video else 'repo'}-queue-{d}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(queue, ensure_ascii=False), encoding="utf-8")
        args = ["video", "run", "--queue", str(path), *tag] if video else ["repo-analyze", "--week", iso_week(d), "--queue", str(path), *tag]
        log.step(name, d, args, extra=("--extra", "video") if video else ())


def _pull_failed() -> bool:
    return os.environ.get("TRENDSIT_PULL_FAILED") == "1"  # run_ops.sh가 git pull 실패 때 세움


def _pull_note() -> str:
    return " / git pull 실패: 옛 코드로 실행(실행 폴더 확인)" if _pull_failed() else ""


def _pull_summary() -> dict[str, Any]:
    return {"pull_failed": True} if _pull_failed() else {}


# ---------- weekly ----------
def weekly(db: DB, cfg: OpsConfig, *, week: str | None = None, now: datetime | None = None,
           runner: Runner = run_subprocess, data_dir: Path | None = None, wait_sec: float | None = None) -> int:
    """nightly 따라잡기 → 지난 ISO 주차 weekly → 성공하면 publish. --force는 쓰지 않는다(C-8). 0 성공·이미 발행, 1 실패, 3 잠금 못 얻음."""
    now = (now or datetime.now(KST)).astimezone(KST)
    data_dir = data_dir or ROOT / "data"
    week = week or iso_week(now.date() - timedelta(days=7))
    spec = f"RUN-{week}"
    wait = cfg.weekly_lock_wait_min * 60 if wait_sec is None else wait_sec
    with ops_lock(data_dir, wait) as got:
        if not got:
            return _skipped(db, "ops-weekly", spec, {"week": week, "steps": []})
        tr = Tracer(db, "ops-weekly", spec, f"ops weekly {week}" + _pull_note())
        log = StepLog(runner, data_dir / "logs" / "ops" / f"{now.date().isoformat()}-weekly.log", cfg)
        status, code = "failed", 1
        try:
            row = db.conn.execute("SELECT status FROM weeks WHERE week=?", (week,)).fetchone()
            if row and row["status"] == "published":
                print(f"이미 발행: {week}")
                log.note(f"이미 발행: {week}")
                status, code = "ok", 0
            else:
                # 일요일 분처럼 아직 안 돈 날을 먼저 따라잡는다(같은 잠금 안). 단계 실패가 있어도 weekly는 진행
                _nightly_locked(db, cfg, None, now, runner, data_dir)
                wk, _ = log.step("weekly", None, ["weekly", "--week", week, "--spec", spec])
                if wk == 0:
                    t0 = time.monotonic()
                    pub = publish(db, week, lambda cmd: _logged(log, cmd))
                    log.add("publish", None, pub, round(time.monotonic() - t0, 1), err="빌드 실패 또는 발행 불가(로그 참고)")
                    status, code = ("ok", 0) if pub == 0 else ("failed", 1)
        finally:
            _close_run(db, tr, status, {"week": week, "steps": log.steps} | _pull_summary())
    return code


def _logged(log: StepLog, cmd: list[str]) -> tuple[int, str, str]:
    code, out, err, _ = log.run(cmd, "publish")
    return code, out, err
