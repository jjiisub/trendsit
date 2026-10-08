"""수집 리포트(reports/S1_collection.md): 소스별 표, 백필 확인, GitHub, 유튜브, 사람 확인용 샘플, 링크 분포, 문턱값."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from ..core import config
from ..core.db import DB
from .links import normalize_url

# handoff(S1) 묶음의 백필 후보(GeekNews는 설계 결정 Q1·Q5로 정한 실제 방식). 실제로 열어 확인한 결과와 나란히 보여 준다
HANDOFF_CANDIDATES = {
    "openai": "rss_only",
    "anthropic": "list_pages https://www.anthropic.com/news",
    "deepmind": "rss_only",
    "geeknews": "day_archive https://news.hada.io/past?day={date} (날짜당 1페이지)",
    "simonw": "day_archive https://simonwillison.net/{yyyy}/{Mon}/{d}/",
    "aitimes": "list_pages https://www.aitimes.com/news/articleList.html?page={page}&view_type=sm",
    "techbridge": "channel_listing (yt-dlp)",
}
CHECK_NOTES = {
    "geeknews": "설계 결정(Q1, Q5): RSS·상세 페이지·메인 화면을 쓰지 않음. 매일 수집과 백필 모두 날짜별 목록 past?day=에서 날짜당 pages_per_day페이지(기본 1 = 그날 점수 상위 약 20건). 본문은 원문 링크에서",
    "aitimes": "목록의 page 값이 무시됨(더보기는 JS) → 1페이지는 sc_sdate/sc_edate로 거른 HTML, 2페이지부터 ajaxArticlePaging.php(JSON)",
    "anthropic": "목록은 최신 10건 안팎, 페이지 넘김 없음. 커뮤니티 피드가 2021년부터 담고 있어 대체 수단으로만",
    "simonw": "후보 그대로 동작(조각마다 고유 주소, 시각)",
    "techbridge": "yt-dlp 채널 목록(flat, approximate_date) 동작. 정확한 시각은 영상별 메타데이터",
}
THRESHOLDS = {"body_rate": 0.9, "origin_rate": 0.95}
SKIP = {"skip_robots": "robots 차단", "skip_type": "허용 밖 형식(PDF 등)", "skip_video": "영상"}


def _pct(a: int, b: int) -> str:
    return f"{a / b:.0%} ({a}/{b})" if b else "-"


def _latest_logs(db: DB, since: date, until: date) -> dict[str, dict[str, Any]]:
    """소스마다 같은 기간(--since, --until)을 수집한 가장 최근 기록. 다른 기간의 기록은 섞지 않는다."""
    rows = db.conn.execute("SELECT * FROM fetch_log ORDER BY id").fetchall()
    out: dict[str, dict[str, Any]] = {}
    for r in rows:
        detail = json.loads(r["detail"]) if r["detail"] else {}
        if detail.get("since") == since.isoformat() and detail.get("until") == until.isoformat():
            out[r["source_id"]] = dict(r) | {"detail": detail}
    return out


def build(since: date, until: date, *, data_dir: Path | None = None, out: Path | None = None) -> tuple[Path, dict]:
    data_dir = data_dir or config.ROOT / "data"
    sources = config.load("sources.yaml")
    db = DB(data_dir / "trendsit.db")
    logs = _latest_logs(db, since, until)
    rng = (since.isoformat(), until.isoformat())
    q = db.conn.execute
    verdict: dict[str, Any] = {}
    L = [f"# S1 수집 리포트 ({since} ~ {until})", "",
         "> `python -m trendsit report collection`이 생성한다. 기간은 한국 시간 게시일 기준. "
         "GitHub 트렌딩은 과거 기록이 없어 실행 시점의 주간 목록이다(기간과 다름).", ""]

    # 1. 소스별 표
    L += ["## 1. 소스별", "",
          "본문 추출 성공률의 분모는 원문 링크가 있는 글에서 의도적으로 건너뛴 것(robots 차단, PDF 등 허용 밖 형식, 영상)을 뺀 수. "
          "403 같은 실패는 실패로 센다(설계 결정 Q1).", "",
          "| 소스 | 받는 방식 | RSS 가장 오래된 날 | 기간 덮음 | 백필(방법, 페이지) | 기간 안 항목 | 백필로 얻음 | "
          "본문 추출 성공 | 의도적 건너뜀 | 키워드 통과 | 실패, 메모 |", "|" + "---|" * 11]
    body_fail = []
    for s in [*sources.text, *sources.video]:
        lg = logs.get(s.id, {})
        d = lg.get("detail", {})
        n = q("SELECT COUNT(*) FROM items WHERE source_id=? AND day BETWEEN ? AND ?", (s.id, *rng)).fetchone()[0]
        nb = q("SELECT COUNT(*) FROM items WHERE source_id=? AND via='backfill' AND day BETWEEN ? AND ?",
               (s.id, *rng)).fetchone()[0]
        ok = q("SELECT COUNT(*) FROM items WHERE source_id=? AND body_status='ok' AND day BETWEEN ? AND ?",
               (s.id, *rng)).fetchone()[0]
        skips = {k: q("SELECT COUNT(*) FROM items WHERE source_id=? AND body_status=? AND day BETWEEN ? AND ?",
                      (s.id, k, *rng)).fetchone()[0] for k in SKIP}
        n_skip = sum(skips.values())
        n_noattempt = q("SELECT COUNT(*) FROM items WHERE source_id=? AND body_status='skipped' AND day BETWEEN ? AND ?",
                        (s.id, *rng)).fetchone()[0]  # --no-body로 시도하지 않은 것도 분모에서 뺀다
        npass = q("SELECT COUNT(*) FROM items WHERE source_id=? AND filter_status='pass' AND day BETWEEN ? AND ?",
                  (s.id, *rng)).fetchone()[0]
        fetch_mode = getattr(s, "fetch", "rss + yt-dlp")
        method = s.backfill.method
        pages = d.get("backfill_pages", 0)
        covered = bool(lg) and lg.get("status") != "failed" and d.get("covered", False)  # 이 기간 기록이 없으면 아니오
        per_day = d.get("pages_per_day")
        covered_txt = (f"예(날짜당 {per_day}페이지)" if per_day else "예") if covered else "아니오"
        reasons = d.get("fetch_errors") or {}
        memo = "; ".join([*(d.get("notes") or []), *(d.get("errors") or [])[:3],
                          *(f"실패: {k} {v}건" for k, v in sorted(reasons.items(), key=lambda kv: -kv[1])[:5])])
        memo = memo or (lg.get("error") or "")
        denom = n - n_skip - n_noattempt
        rate = ok / denom if denom else 0
        if fetch_mode in ("feed_summary", "feed_title", "list_origin") and denom and rate < THRESHOLDS["body_rate"]:
            body_fail.append(f"{s.id} {rate:.0%}")
        skip_txt = ", ".join(f"{SKIP[k]} {v}" for k, v in skips.items() if v) or "-"
        if d.get("n_self_excluded"):
            memo = f"자기 글(Show GN 등) {d['n_self_excluded']}건 제외; " + memo
        pages_txt = f"{method}, {pages}"
        L.append(f"| {s.id} | {fetch_mode} | {d.get('rss_oldest') or '-'} | {covered_txt} | "
                 f"{pages_txt} | {n} | {nb} | {_pct(ok, denom)} | {skip_txt} | {_pct(npass, n)} | {memo[:220] or '-'} |")
        verdict.setdefault("covered", {})[s.id] = bool(covered) and lg.get("status") != "failed"
    L.append("")

    # 1-1. 하루 신규 건수(게시일 기준). 페이지 수나 방식을 조정할 근거
    days = [r["day"] for r in q("SELECT DISTINCT day FROM items WHERE day BETWEEN ? AND ? ORDER BY day", rng)]
    L += ["### 하루 신규 건수(게시일, 한국 시간)", "",
          "| 소스 | " + " | ".join(d[5:] for d in days) + " | 하루 평균 |", "|---|" + "---|" * (len(days) + 1)]
    for s in [*sources.text, *sources.video]:
        cnt = {r["day"]: r["n"] for r in q("SELECT day, COUNT(*) n FROM items WHERE source_id=? AND day BETWEEN ? AND ? "
                                            "GROUP BY day", (s.id, *rng))}
        span = (until - since).days + 1
        L.append(f"| {s.id} | " + " | ".join(str(cnt.get(d, 0)) for d in days)
                 + f" | {sum(cnt.values()) / span:.1f} |")
    L.append("")

    # 2. 백필 확인
    L += ["## 2. 백필 URL 확인 (2026-10-07 실제로 열어 봄)", "", "| 소스 | handoff 후보 | 지금 설정 | 확인 결과 |",
          "|---|---|---|---|"]
    for s in sources.text:
        cur = f"{s.backfill.method} {s.backfill.url_template or ''}".strip()
        if s.backfill.page_template:
            cur += f" / 2페이지부터 {s.backfill.page_template}"
        L.append(f"| {s.id} | `{HANDOFF_CANDIDATES.get(s.id, '-')}` | `{cur}` | {CHECK_NOTES.get(s.id, '후보 그대로')} |")
    for v in sources.video:
        L.append(f"| {v.id} | `{HANDOFF_CANDIDATES.get(v.id, '-')}` | `{v.backfill.method}` | {CHECK_NOTES.get(v.id, '-')} |")
    L.append("")

    # 3. GitHub
    week = q("SELECT MAX(week) FROM repo_trending").fetchone()[0]
    tr = q("SELECT * FROM repo_trending WHERE week=? ORDER BY rank", (week,)).fetchall() if week else []
    missing = sum(1 for r in tr if r["stars_this_week"] is None)
    page_rows = logs.get("github_trending", {}).get("detail", {}).get("page_rows")
    rel = q("SELECT title, day FROM items WHERE source_id='github_releases' AND day BETWEEN ? AND ? ORDER BY day",
            rng).fetchall()
    L += ["## 3. GitHub", "",
          f"- 트렌딩(주간 페이지, 실행 주차 {week or '-'}): 페이지에 보인 {page_rows if page_rows is not None else '-'}개 중 "
          f"{len(tr)}개 저장, 키워드 통과 "
          f"{sum(1 for r in tr if r['filter_status'] == 'pass')}개, 이번 주 별 누락 {missing}개",
          f"- 추적 레포 릴리스(기간 안): {len(rel)}건" + (" — " + ", ".join(f"{r['title']}({r['day']})" for r in rel[:12])
                                                     if rel else ""), ""]
    if tr:
        L += ["| 순위 | 레포 | 이번 주 별 | 전체 별 | 키워드 | 상태 |", "|---|---|---|---|---|---|"]
        for r in tr:
            kws = ", ".join(json.loads(r["keywords"] or "{}").keys())
            L.append(f"| {r['rank']} | {r['full_name']} | {r['stars_this_week']} | {r['stars_total']} | {kws or '-'} | "
                     f"{r['filter_status']} |")
        L.append("")
    verdict["trending"] = len(tr)
    verdict["trending_missing"] = missing
    verdict["trending_page_rows"] = page_rows

    # 4. 유튜브
    for v in sources.video:
        vids = q("SELECT i.title, i.day, i.via, v.duration_sec, v.manual_sub_langs, v.has_auto_sub, v.meta_status, "
                 "v.chapters_json FROM items i LEFT JOIN videos v ON v.item_id=i.id WHERE i.source_id=? AND "
                 "i.day BETWEEN ? AND ? ORDER BY i.day", (v.id, *rng)).fetchall()
        meta_ok = sum(1 for x in vids if x["meta_status"] == "ok")
        L += [f"## 4. 유튜브 ({v.name})", "", f"- 영상 {len(vids)}편, 메타데이터 성공 {_pct(meta_ok, len(vids))}", ""]
        if vids:
            L += ["| 날짜 | 제목 | 길이(초) | 수동 자막 | 자동 자막 | 챕터 수 | 얻은 곳 |", "|---|---|---|---|---|---|---|"]
            for x in vids:
                ch = len(json.loads(x["chapters_json"])) if x["chapters_json"] else 0
                L.append(f"| {x['day']} | {(x['title'] or '')[:50]} | {x['duration_sec']} | {x['manual_sub_langs'] or '-'} | "
                         f"{'있음' if x['has_auto_sub'] else '없음'} | {ch} | {x['via']} |")
            L.append("")

    # 5. 사람 확인용 샘플
    L += ["## 5. 사람 확인용 샘플", "", "걸러진 글 중 놓친 것, 통과한 글 중 잘못 통과한 것에 체크한다.", ""]
    for s in [*sources.text, *sources.video]:
        L.append(f"### {s.id}")
        for status, label, box in (("filtered", "걸러진 글", "놓침"), ("pass", "통과한 글", "잘못 통과")):
            rows = q("SELECT title, filter_reason, score FROM items WHERE source_id=? AND filter_status=? AND day "
                     "BETWEEN ? AND ? ORDER BY RANDOM() LIMIT 5", (s.id, status, *rng)).fetchall()
            L.append(f"- {label}")
            for r in rows:
                why = r["filter_reason"] or f"점수 {r['score']}"
                L.append(f"  - [ ] {box} · {(r['title'] or '')[:80]} ({why})")
            if not rows:
                L.append("  - (없음)")
        L.append("")

    # 6. 링크
    dist = q("SELECT l.kind, COUNT(*) n FROM links l JOIN items i ON i.id=l.item_id WHERE i.day BETWEEN ? AND ? "
             "GROUP BY l.kind ORDER BY n DESC", rng).fetchall()
    gn = q("SELECT i.id, i.title, (SELECT COUNT(*) FROM links l WHERE l.item_id=i.id AND l.role='origin_candidate') o "
           "FROM items i WHERE i.source_id='geeknews' AND i.day BETWEEN ? AND ?", rng).fetchall()
    n_self = logs.get("geeknews", {}).get("detail", {}).get("n_self_excluded", 0)  # 수집에서 뺀 자기 글
    denom = len(gn)
    got = sum(1 for r in gn if r["o"])
    L += ["## 6. 링크", "", "| 종류 | 링크 수 |", "|---|---|", *[f"| {r['kind']} | {r['n']} |" for r in dist], "",
          f"- GeekNews 원문 링크 확보율: {_pct(got, denom)} (원문 링크가 GeekNews 자신인 글 {n_self}건은 수집에서 뺌. "
          "목록에서 원문 링크가 있는 글만 수집하므로 구조상 100%이고, 실제 확인은 자기 글 판정이 맞는지)",
          "- 원문이 Hacker News 토론 페이지인 GeekNews 글은 토론 속 링크가 많이 잡힘(curation 링크 대부분). "
          "S3 원본 추적에서 거를 대상", ""]
    verdict["origin_rate"] = got / denom if denom else None

    # 중복: 정규화한 URL(추적 파라미터, 끝 슬래시, 대소문자) 기준. UNIQUE(source_id, external_id)와 별개로 확인
    seen: dict[tuple[str, str], int] = {}
    for r in q("SELECT source_id, url FROM items WHERE day BETWEEN ? AND ?", rng):
        k = (r["source_id"], normalize_url(r["url"] or ""))
        seen[k] = seen.get(k, 0) + 1
    dup = sum(1 for v in seen.values() if v > 1)
    verdict["duplicates"] = dup
    verdict["body_fail"] = body_fail

    # 문턱값
    uncovered = [k for k, v in verdict.get("covered", {}).items() if not v]
    L += ["## 7. 문턱값 (S1_TASK 7장)", "", "| 항목 | 기준 | 결과 | 판정 |", "|---|---|---|---|",
          f"| 글 소스 6곳 기간 덮음 | RSS 또는 백필 | 못 덮음: {', '.join(uncovered) or '없음'} | {'통과' if not uncovered else '미달'} |",
          f"| 본문 추출 성공률 | 소스별 90% 이상(feed_full 제외) | 미달: {', '.join(body_fail) or '없음'} | "
          f"{'통과' if not body_fail else '미달'} |",
          f"| GeekNews 원문 링크 확보율 | 95% 이상 | {_pct(got, denom)} | "
          f"{'통과' if denom and got / denom >= THRESHOLDS['origin_rate'] else '미달'} |",
          f"| 트렌딩 | 주간 페이지에 보이는 전부, stars_this_week 누락 0, 0개면 실패(설계 결정 Q2) | "
          f"페이지 {page_rows if page_rows is not None else '-'}개 중 {len(tr)}개, 누락 {missing} | "
          f"{'통과' if tr and page_rows == len(tr) and missing == 0 else '미달'} |",
          f"| 중복 | 0 | {dup} | {'통과' if dup == 0 else '미달'} |", ""]
    out = out or config.ROOT / "reports" / "S1_collection.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(L), encoding="utf-8")
    db.close()
    return out, verdict
