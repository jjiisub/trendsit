"""C-21 선별 순서 미리보기(LLM 0원): 지금 현재판 묶음으로 새 코드 순서와 이전 순서(묶기 점수)를 나란히.

재실행 전에 영상·경험담 글 위치, 큰 발표 뉴스가 지나치게 밀리지 않는지 보는 표(PR #9 리뷰 4장 C-21).
실행: uv run --extra embed python scripts/s5_order_preview.py --weeks 2026-W40 2026-W41
출력: reports/S5_brief/select_order_<week>.md
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from trendsit.brief import cluster as cl  # noqa: E402
from trendsit.brief import select as sel  # noqa: E402
from trendsit.brief.evidence import week_evidence  # noqa: E402
from trendsit.core import config  # noqa: E402
from trendsit.core.db import DB  # noqa: E402
from trendsit.filter.embed import make_embedder  # noqa: E402


def preview(db: DB, week: str, embedder, cfg) -> Path:
    run = db.conn.execute("SELECT current_run_id FROM weeks WHERE week=?", (week,)).fetchone()[0]
    summ = json.loads(db.conn.execute("SELECT summary_json FROM runs WHERE id=?", (run,)).fetchone()[0] or "{}")
    cluster_run = summ.get("cluster_run") or run
    ev = week_evidence(db, week)
    flt = config.load("filter.yaml")
    sims = cl.interest_similarity(db, list(ev.members.values()), embedder, [(x.keyword_id, x.text) for x in flt.interests])
    allc = sel.load_candidates(db, cluster_run, ev, 10**6, sims, cfg)
    old = sorted(allc, key=lambda c: (-c.score, c.cluster_id))
    old_rank = {c.cluster_id: i for i, c in enumerate(old, 1)}
    plan = json.loads(db.conn.execute("SELECT plan_json FROM briefing_plans WHERE run_id=? ORDER BY id DESC LIMIT 1",
                                      (run,)).fetchone()[0])
    dec = {d["cluster_id"]: d for d in plan.get("decisions", [])}
    top = cfg.select.max_candidates
    slot = set(sel.video_slot_ids(allc, cfg))
    lines = [f"# 선별 순서 미리보기 {week} (C-21, LLM 0원)", "",
             f"> 묶기 run `{cluster_run}`, 이전 선별 run `{run}`. 새 순서 = 관심 유사도 구간({cfg.select.order.sim_band}) → 출처 수 → "
             f"수치 유무 → 키워드 추세(relevance low뿐이면 맨 아래). 이전 순서 = 묶기 점수. 편집장 입력은 상위 {top}개.",
             f"> 영상 자리(C-20) 후보: {', '.join(f'c{i}' for i in sorted(slot)) or '없음'}"
             f"(영상 관련성 {cfg.select.video_slot.relevance_min} 이상)", "",
             "| 새 순서 | 이전 순서 | 후보 | 채널 | 출처 | 유사도 | 수치 | 추세↑ | 이전 결정 | 이름 |", "|---|---|---|---|---|---|---|---|---|---|"]
    for c in sorted(allc, key=lambda c: c.order):
        if c.order > top and old_rank[c.cluster_id] > top:
            continue
        d = dec.get(c.cluster_id)
        prev = "-" if d is None else (d["action"] + (f"({d['drop_reason']})" if d.get("drop_reason") else ""))
        ch = "+".join(f"{k}{v}" for k, v in c.channels.items()) + (" 🎬" if c.cluster_id in slot else "")
        mark = lambda r: f"**{r}**" if r <= top else str(r)  # noqa: E731
        lines.append(f"| {mark(c.order)} | {mark(old_rank[c.cluster_id])} | c{c.cluster_id} | {ch} | {len(c.members)} | "
                     f"{c.sim} | {'O' if c.has_numbers else '-'} | {c.trend_up} | {prev} | {c.label[:50]} |")
    newin = {c.cluster_id for c in allc if c.order <= top}
    oldin = {c.cluster_id for c in allc if old_rank[c.cluster_id] <= top}
    vids = [c for c in allc if "video" in c.channels]
    lines += ["", f"- 상위 {top} 들어옴: {', '.join(f'c{i}' for i in sorted(newin - oldin)) or '없음'} / "
              f"빠짐: {', '.join(f'c{i}' for i in sorted(oldin - newin)) or '없음'}",
              f"- 영상 든 후보 {len(vids)}개의 새 순서: " + ", ".join(f"c{c.cluster_id} {c.order}위(유사도 {c.sim})"
                                                      for c in sorted(vids, key=lambda c: c.order)), ""]
    path = ROOT / "reports" / "S5_brief" / f"select_order_{week}.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--weeks", nargs="+", required=True)
    args = ap.parse_args()
    db = DB(ROOT / "data" / "trendsit.db")
    cfg = config.load("brief.yaml")
    emb = make_embedder("real", config.load("filter.yaml"))
    for w in args.weeks:
        print(preview(db, w, emb, cfg))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
