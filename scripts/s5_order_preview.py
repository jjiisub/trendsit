"""선별 순서 비교(LLM 0원): 지금 현재판 묶음으로 수정안(점수 + 유사도 동점 깨기), 이전(점수 + cluster_id), C-21 원안을 나란히.

재실행 전에 영상·경험담 글 위치, 큰 발표 뉴스가 밀리지 않는지 보는 표(PR #9 리뷰 C-21, 수정 2026-10-10).
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


def c21_original_key(c: sel.Candidate, ev, up: set[str], band: float = 0.05) -> tuple:
    """C-21 원안(취소, 비교용): 유사도 구간 → 출처 수 → 수치 유무 → 키워드 추세, relevance low뿐이면 맨 아래."""
    ms = [ev.members[k] for k in c.members]
    low = all(m.relevance == "low" for m in ms)
    nums = any(it.kind in ("number", "slide_fact") for m in ms for it in m.items)
    trend = len({k for m in ms for k in m.keywords} & up)
    b = -1 if low else int((c.sim or 0) / band + 1e-9)
    return (-b, -len(c.members), -int(nums), -trend, c.cluster_id)


def preview(db: DB, week: str, embedder, cfg) -> Path:
    run = db.conn.execute("SELECT current_run_id FROM weeks WHERE week=?", (week,)).fetchone()[0]
    summ = json.loads(db.conn.execute("SELECT summary_json FROM runs WHERE id=?", (run,)).fetchone()[0] or "{}")
    cluster_run = summ.get("cluster_run") or run
    ev = week_evidence(db, week)
    flt = config.load("filter.yaml")
    sims = cl.interest_similarity(db, list(ev.members.values()), embedder, [(x.keyword_id, x.text) for x in flt.interests])
    allc = sel.load_candidates(db, cluster_run, ev, 10**6, sims)
    up = {k.keyword for k in sel.keyword_trend(db, week) if k.this_week > k.last_week}
    pos = {name: {c.cluster_id: i for i, c in enumerate(sorted(allc, key=f), 1)} for name, f in (
        ("new", sel.score_key), ("old", lambda c: (-c.score, c.cluster_id)), ("c21", lambda c: c21_original_key(c, ev, up)))}
    plan = json.loads(db.conn.execute("SELECT plan_json FROM briefing_plans WHERE run_id=? ORDER BY id DESC LIMIT 1",
                                      (run,)).fetchone()[0])
    dec = {d["cluster_id"]: d for d in plan.get("decisions", [])}
    top = cfg.select.max_candidates
    slot = set(sel.video_slot_ids(allc, cfg))
    lines = [f"# 선별 순서 비교 {week} (LLM 0원)", "",
             f"> 묶기 run `{cluster_run}`, 이전 선별 run `{run}`. 편집장 입력은 상위 {top}개(굵게).",
             "> - 수정안(적용, 설계 결정 C-21 수정 2026-10-10): 묶기 점수 그대로, 동점이면 관심 유사도 높은 순",
             "> - 이전: 묶기 점수, 동점이면 cluster_id",
             "> - C-21 원안(취소): 유사도 구간(0.05) → 출처 수 → 수치 → 추세",
             f"> 영상 자리(C-20) 후보: {', '.join(f'c{i}' for i in sorted(slot)) or '없음'}"
             f"(영상 관련성 {cfg.select.video_slot.relevance_min} 이상)", "",
             "| 수정안 | 이전 | C-21 원안 | 후보 | 채널 | 출처 | 점수 | 유사도 | 이전 결정 | 이름 |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    mark = lambda r: f"**{r}**" if r <= top else str(r)  # noqa: E731
    for c in sorted(allc, key=sel.score_key):
        if min(pos[k][c.cluster_id] for k in pos) > top:
            continue
        d = dec.get(c.cluster_id)
        prev = "-" if d is None else (d["action"] + (f"({d['drop_reason']})" if d.get("drop_reason") else ""))
        ch = "+".join(f"{k}{v}" for k, v in c.channels.items()) + (" 🎬" if c.cluster_id in slot else "")
        lines.append(f"| {mark(pos['new'][c.cluster_id])} | {mark(pos['old'][c.cluster_id])} | {mark(pos['c21'][c.cluster_id])} | "
                     f"c{c.cluster_id} | {ch} | {len(c.members)} | {c.score} | {c.sim} | {prev} | {c.label[:50]} |")
    chosen = [cid for t in plan.get("topics", []) for cid in t["cluster_ids"]]
    lines += [""] + [f"- {name}: 이전 선정 {len(chosen)}개 중 상위 {top} 안 {sum(pos[k][x] <= top for x in chosen)}개, "
                     f"영상 든 후보 상위 {top} 안 {sum(1 for c in allc if 'video' in c.channels and pos[k][c.cluster_id] <= top)}개"
                     for k, name in (("new", "수정안"), ("old", "이전"), ("c21", "C-21 원안"))]
    newin = {c.cluster_id for c in allc if pos["new"][c.cluster_id] <= top}
    oldin = {c.cluster_id for c in allc if pos["old"][c.cluster_id] <= top}
    lines += [f"- 수정안 ↔ 이전 상위 {top} 차이: 들어옴 {', '.join(f'c{i}' for i in sorted(newin - oldin)) or '없음'} / "
              f"빠짐 {', '.join(f'c{i}' for i in sorted(oldin - newin)) or '없음'}", ""]
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
