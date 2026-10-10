"""S6b 자동 실행: 발행(publish)과 단계 실행기. nightly·weekly 흐름은 이 파일 아래쪽(S-2)."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable

from .core.config import ROOT
from .core.db import DB, now_kst

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
