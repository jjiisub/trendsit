"""W40 트렌딩 재구성(S5, 이번 한 번만, LLM 0원). 트렌딩 주간 목록은 지난 주를 받을 수 없어(P1) W40을 근사한다.

방법
1. 후보: 지금 GitHub 트렌딩 월별(since=monthly) + 주별(since=weekly) 목록의 레포
2. 레포마다 stargazers API(`application/vnd.github.star+json`, starred_at)를 마지막 쪽부터 거꾸로 읽어
   대상 주(KST 월 00:00 ~ 다음 월 00:00)에 받은 별 수를 센다
3. 그 수로 순위를 매겨 상위 N개를 repo_trending(대상 주)에 저장. stars_this_week = 그 주 별 수.
   키워드 판정·README는 수집기와 같은 경로(GithubCollector)
한계
- 실제 트렌딩 순위는 별 수만으로 정해지지 않는다(GitHub 비공개 기준). 이 목록은 "그 주 별을 많이 받은 레포" 근사
- 후보가 지금(10월 둘째 주) 목록에서 오므로 W40에 떴다가 사라진 레포는 빠질 수 있다
- stargazers API는 400쪽(4만 개)까지만 준다. 별이 그보다 많은 레포는 최근 쪽을 읽을 수 없어 셀 수 없음으로 둔다
재구성분 표시: 실행 기록(runs.note)에 'reconstructed', 리포트 reports/S5_brief/trending_reconstructed_<week>.md

실행: uv run python scripts/reconstruct_trending.py --week 2026-W40 [--top 25]
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from trendsit.collect.fetch import Fetcher  # noqa: E402
from trendsit.collect.github import API, GithubCollector, GithubStats, parse_trending  # noqa: E402
from trendsit.collect.sites.common import KST  # noqa: E402
from trendsit.core import config  # noqa: E402
from trendsit.core.db import DB  # noqa: E402
from trendsit.core.trace import Tracer  # noqa: E402

MAX_PAGES = 400
STAR_JSON = {"Accept": "application/vnd.github.star+json"}


def week_window(week: str) -> tuple[datetime, datetime]:
    y, w = week.split("-W")
    start = datetime.combine(date.fromisocalendar(int(y), int(w), 1), time(0), KST)
    return start, start + timedelta(days=7)


def count_week_stars(fetcher: Fetcher, headers: dict[str, str], full_name: str, total: int,
                     start: datetime, end: datetime) -> tuple[int | None, int, str]:
    """(그 주 별 수 또는 None, 읽은 쪽 수, 메모). 마지막 쪽부터 거꾸로 읽고 시작 시각 이전이 나오면 멈춘다."""
    last = max(1, math.ceil(total / 100))
    if last > MAX_PAGES:
        return None, 0, f"별 {total:,}개: API 400쪽 제한으로 최근 별을 읽을 수 없음"
    n, pages = 0, 0
    for page in range(last, 0, -1):
        res = fetcher.fetch(f"{API}/repos/{full_name}/stargazers?per_page=100&page={page}", kind="api",
                            headers=headers | STAR_JSON)
        pages += 1
        if not res.ok or not res.text:
            return None, pages, f"stargazers {page}쪽 실패: {res.error or res.status}"
        rows = json.loads(res.text)
        times = [datetime.fromisoformat(r["starred_at"].replace("Z", "+00:00")) for r in rows if r.get("starred_at")]
        n += sum(1 for t in times if start <= t < end)
        if times and min(times) < start:
            break
    return n, pages, ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", required=True)
    ap.add_argument("--top", type=int, default=25, help="저장할 레포 수(주간 페이지 크기와 비슷하게)")
    args = ap.parse_args()
    start, end = week_window(args.week)
    sources = config.load("sources.yaml")
    db = DB(ROOT / "data" / "trendsit.db")
    if db.conn.execute("SELECT 1 FROM repo_trending WHERE week=?", (args.week,)).fetchone():
        print(f"{args.week} 트렌딩이 이미 있음(실제 수집분일 수 있어 덮어쓰지 않음)", file=sys.stderr)
        return 2
    fetcher = Fetcher(ROOT / "data" / "http_cache", use_cache=False)
    tracer = Tracer(db, "collect", "S5", note=f"trending reconstructed {args.week} (stargazers 기준 근사)")
    gh = GithubCollector(db, fetcher, sources.github, config.load("keywords.yaml"), config.load("link_kinds.yaml"),
                         run_id=tracer.run_id)
    cands: dict[str, dict] = {}
    for since in ("monthly", "weekly"):
        res = fetcher.fetch(f"https://github.com/trending?since={since}", kind="page")
        for row in parse_trending(res.text or "") if res.ok else []:
            cands.setdefault(row["full_name"], row | {"from": since})
    rows, notes = [], []
    for name, row in cands.items():
        meta = fetcher.fetch(f"{API}/repos/{name}", kind="api", headers=gh.api_headers)
        if not meta.ok or not meta.text:
            notes.append(f"{name}: 저장소 정보 실패")
            continue
        info = json.loads(meta.text)
        total = info.get("stargazers_count") or 0
        n, pages, note = count_week_stars(fetcher, gh.api_headers, name, total, start, end)
        print(f"{name}: 별 {total:,}, {args.week} {n}, {pages}쪽 {note}", file=sys.stderr)
        if note:
            notes.append(f"{name}: {note}")
        rows.append({"full_name": name, "description": info.get("description") or row.get("description"),
                     "language": info.get("language"), "stars_total": total, "forks": info.get("forks_count"),
                     "stars_this_week": n, "from": row["from"], "pages": pages})
    ranked = sorted([r for r in rows if r["stars_this_week"]], key=lambda r: -r["stars_this_week"])[: args.top]
    st = GithubStats()
    for rank, r in enumerate(ranked, start=1):
        m = gh.matcher.match(r["description"], None)
        readme = None
        if m.filter_status == "pass":
            meta = gh.readme(r["full_name"], st)
            readme = meta.get("readme_head")
            m = gh.matcher.match(r["description"], " ".join(meta.get("topics", [])), readme)
        db.upsert_repo(r["full_name"], description=r["description"], language=r["language"], readme_head=readme)
        db.save_trending(args.week, r | {"rank": rank, "score": m.score, "filter_status": m.filter_status,
                                         "filter_reason": m.filter_reason, "keywords": m.keywords}, tracer.run_id)
        r |= {"rank": rank, "filter_status": m.filter_status}
    tracer.step(kind="code", role="collect", text=f"{args.week} 트렌딩 재구성: 후보 {len(cands)}개 중 {len(ranked)}개 저장",
                attention=bool(notes), detail={"window": [start.isoformat(), end.isoformat()], "notes": notes,
                                               "candidates": len(cands)})
    tracer.finish("ok")
    out = ROOT / "reports" / "S5_brief" / f"trending_reconstructed_{args.week}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {args.week} 트렌딩 재구성 (근사)", "",
             f"- run `{tracer.run_id}`(runs.note에 reconstructed). 재현: `uv run python scripts/reconstruct_trending.py --week {args.week}`",
             f"- 기간(KST): {start:%Y-%m-%d %H:%M} ~ {end:%Y-%m-%d %H:%M}",
             f"- 후보: {datetime.now(KST):%Y-%m-%d} 기준 트렌딩 월별 + 주별 목록 {len(cands)}개",
             "- 순위: 그 주 받은 별 수(stargazers API starred_at). stars_this_week = 그 주 별 수",
             "- 한계: 실제 트렌딩 순위는 별 수만으로 정해지지 않는다. 지금 목록에 없는 W40 레포는 빠질 수 있다. "
             "별 4만 개 넘는 레포는 API 400쪽 제한으로 셀 수 없다", "",
             "| 순위 | 레포 | 그 주 별 | 전체 별 | 후보 출처 | 키워드 | 읽은 쪽 |", "|---|---|---|---|---|---|---|"]
    for r in ranked:
        lines.append(f"| {r['rank']} | {r['full_name']} | {r['stars_this_week']:,} | {r['stars_total']:,} | {r['from']} | "
                     f"{r['filter_status']} | {r['pages']} |")
    lines += ["", "## 셀 수 없었던 레포·실패", ""] + [f"- {x}" for x in notes] + ([] if notes else ["- 없음"])
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
