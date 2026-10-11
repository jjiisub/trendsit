"""W40 트렌딩 근사 목록(S6a 5.7). 주간 트렌딩은 지난 주를 받을 수 없어(stargazers API 404) 월간 페이지로 대신한다.

방법: github.com/trending?since=monthly를 1회 받아 → parse_trending → repo_trending에 이미 있는 다른 주 레포를 빼고 →
남은 순서대로 상위 10개를 repo_trending(대상 주, stars_this_week NULL)에 저장, runs 행 kind='collect' note='trending monthly approx'
→ repo_oneliners에 없는 레포는 repo_oneliner(--spec S6a, 10개 약 $0.01).
이미 근사 행이 있으면 아무것도 안 하고 0(멱등). 받기·파싱 실패는 DB를 건드리지 않고 1. 월간 창이 그 주를 포함할 때(약 10/28까지) 1회만.

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
from trendsit.core.db import DB  # noqa: E402
from trendsit.core.trace import Tracer  # noqa: E402
from trendsit.export import APPROX_NOTE  # noqa: E402

URL = "https://github.com/trending?since=monthly"
TOP = 10


def run(db: DB, week: str, fetch: Callable[[str], tuple[str | None, str | None]]) -> tuple[int, list[str]]:
    """(종료 코드, 저장한 레포 이름). fetch(url) → (html, 오류)."""
    done = db.conn.execute("SELECT 1 FROM repo_trending t JOIN runs r ON r.id=t.run_id WHERE t.week=? AND r.note=?", (week, APPROX_NOTE)).fetchone()
    if done:
        print(f"이미 있음: {week} 근사 목록")
        return 0, []
    html, error = fetch(URL)
    rows = parse_trending(html or "") if html else []
    if not rows:
        print(f"월간 트렌딩 실패: {error or '파싱 0건(페이지 구조 변경 의심)'}", file=sys.stderr)
        return 1, []
    other = {r[0] for r in db.conn.execute("SELECT full_name FROM repo_trending WHERE week!=?", (week,))}
    picked = [r for r in rows if r["full_name"] not in other][:TOP]
    tr = Tracer(db, "collect", "S6a", note=APPROX_NOTE)
    for rank, row in enumerate(picked, start=1):
        db.upsert_repo(row["full_name"], description=row["description"], language=row["language"])
        db.save_trending(week, row | {"rank": rank, "stars_this_week": None}, tr.run_id)  # 월간 별 수는 주간 값이 아니라 저장하지 않음
    tr.finish("ok")
    print(f"{week} 근사 목록 {len(picked)}개 저장(월간 {len(rows)}개 중 다른 주 레포 제외 뒤 상위)")
    return 0, [r["full_name"] for r in picked]


def main() -> int:
    from trendsit.cli_brief import _week
    from trendsit.collect.fetch import Fetcher
    from trendsit.core.context import open_ctx
    from trendsit.deep.repo_agent import oneliner_for

    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--week", type=_week, required=True)
    week = ap.parse_args().week
    ctx = open_ctx("role", spec="S6a", note=f"trending monthly oneliners {week}")
    status = "failed"
    try:
        fetcher = Fetcher(None, use_cache=False)

        def fetch(url: str) -> tuple[str | None, str | None]:
            res = fetcher.fetch(url, kind="page")
            return (res.text, None) if res.ok else (None, res.error)

        code, names = run(ctx.db, week, fetch)
        have = {r[0] for r in ctx.db.conn.execute("SELECT full_name FROM repo_oneliners")}
        for name in names:
            if name not in have:
                oneliner_for(ctx, name)
        status = "ok" if code == 0 else "failed"
        return code
    finally:
        ctx.tracer.finish(status)


if __name__ == "__main__":
    sys.exit(main())
