"""W40 트렌딩 근사 목록(S6a 5.7). 주간 트렌딩은 지난 주를 받을 수 없어(stargazers API 404) 월간 페이지로 대신한다.

방법: github.com/trending?since=monthly를 1회 받아 → parse_trending → repo_trending에 이미 있는 그 뒤 주(week > 대상)의 레포를 빼고 →
남은 순서대로 상위 10개를 repo_trending(대상 주, stars_this_week NULL)에 저장, runs 행 kind='collect' note='trending monthly approx'
→ repo_oneliners에 없는 레포는 repo_oneliner(--spec S6a, 10개 약 $0.01).
이미 근사 행이 있으면 행은 다시 넣지 않고(멱등) oneliner 없는 레포만 채운다. 받기·파싱 실패는 DB를 건드리지 않고 1. 월간 창이 그 주를 포함할 때(약 10/28까지) 1회만.

실행: uv run python scripts/trending_monthly.py --week 2026-W40
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from trendsit.collect.github import parse_trending  # noqa: E402
from trendsit.core.db import DB, now_kst  # noqa: E402
from trendsit.core.trace import new_run_id  # noqa: E402
from trendsit.export import APPROX_NOTE  # noqa: E402

URL = "https://github.com/trending?since=monthly"
TOP = 10


def run(db: DB, week: str, fetch: Callable[[str], tuple[str | None, str | None]]) -> tuple[int, list[str]]:
    """(종료 코드, repo_oneliner가 필요한 레포 이름). fetch(url) → (html, 오류).

    이미 근사 행이 있으면 받지 않고, oneliner가 아직 없는 레포만 돌려준다(중간에 실패한 실행을 다시 돌려 채움).
    받기·파싱이 성공한 뒤에만 DB를 바꾸고, runs 행과 레포 행은 한 트랜잭션이다.
    """
    have = [r[0] for r in db.conn.execute("SELECT t.full_name FROM repo_trending t JOIN runs r ON r.id=t.run_id WHERE t.week=? AND r.note=? ORDER BY t.rank",
                                          (week, APPROX_NOTE))]
    if have:
        print(f"이미 있음: {week} 근사 목록 {len(have)}개")
        return 0, _missing_oneliners(db, have)
    html, error = fetch(URL)
    rows = parse_trending(html or "") if html else []
    if not rows:
        print(f"월간 트렌딩 실패: {error or '파싱 0건(페이지 구조 변경 의심)'}", file=sys.stderr)
        return 1, []
    later = {r[0] for r in db.conn.execute("SELECT full_name FROM repo_trending WHERE week>?", (week,))}  # 월간 창에 함께 든 그 뒤 주의 레포는 W40이 아님
    picked = [r for r in rows if r["full_name"] not in later][:TOP]
    if not picked:
        print("월간 목록이 모두 그 뒤 주 레포라 근사 목록을 만들 수 없음", file=sys.stderr)
        return 1, []
    run_id, now = new_run_id("collect"), now_kst()
    with db.conn:
        db.conn.execute("INSERT INTO runs(id, kind, spec, started_at, finished_at, status, note) VALUES (?,?,?,?,?,?,?)",
                        (run_id, "collect", "S6a", now, now, "ok", APPROX_NOTE))
        for rank, row in enumerate(picked, start=1):
            db.conn.execute("INSERT INTO repos(full_name, description, language, first_seen) VALUES (?,?,?,?) ON CONFLICT(full_name) DO UPDATE SET "
                            "description=COALESCE(excluded.description, description), language=COALESCE(excluded.language, language)",
                            (row["full_name"], row["description"], row["language"], now))
            # 월간 별 수는 주간 값이 아니라 저장하지 않는다(stars_this_week NULL)
            db.conn.execute("INSERT INTO repo_trending(week, full_name, rank, stars_total, stars_this_week, forks, run_id) VALUES (?,?,?,?,NULL,?,?)",
                            (week, row["full_name"], rank, row["stars_total"], row["forks"], run_id))
    print(f"{week} 근사 목록 {len(picked)}개 저장(월간 {len(rows)}개 중 뒤 주 레포 제외 뒤 상위)")
    return 0, _missing_oneliners(db, [r["full_name"] for r in picked])


def _missing_oneliners(db: DB, names: list[str]) -> list[str]:
    have = {r[0] for r in db.conn.execute("SELECT full_name FROM repo_oneliners")}
    return [n for n in names if n not in have]


def main(argv: list[str] | None = None, fetch: Callable[[str], tuple[str | None, str | None]] | None = None) -> int:
    from trendsit.cli_brief import _week
    from trendsit.core.context import open_ctx
    from trendsit.core.db import open_db
    from trendsit.deep.repo_agent import oneliner_for

    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--week", type=_week, required=True)
    week = ap.parse_args(argv).week
    if fetch is None:
        from trendsit.collect.fetch import Fetcher

        fetcher = Fetcher(None, use_cache=False)

        def fetch(url: str) -> tuple[str | None, str | None]:
            res = fetcher.fetch(url, kind="page")
            return (res.text, None) if res.ok else (None, res.error)

    code, names = run(open_db(), week, fetch)  # 여기까지는 LLM 실행 기록(runs 행)을 만들지 않는다
    if not names:
        return code
    ctx = open_ctx("role", spec="S6a", note=f"trending monthly oneliners {week}")
    status = "failed"
    try:
        for name in names:
            oneliner_for(ctx, name)
        status = "ok"
    finally:
        ctx.tracer.finish(status)
    return code


if __name__ == "__main__":
    sys.exit(main())
