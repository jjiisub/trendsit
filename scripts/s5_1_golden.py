"""골든 회귀(S5-1a 5.1): 저장된 W40·W41 현재판의 모든 토픽 × 모든 라운드 판에 코드 검사를 다시 돌려 JSON으로 남긴다.

실행: uv run python scripts/s5_1_golden.py --out <path> [--db data/trendsit.db]
DB는 읽기 전용으로 연다. LLM·임베딩 호출 없음. 종료 코드: 0 성공, 2 DB·run 없음.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from trendsit.brief import aliases as al  # noqa: E402
from trendsit.brief import checks  # noqa: E402
from trendsit.brief.evidence import cap_pack, week_evidence  # noqa: E402
from trendsit.brief.write import alias_lines, pack_index  # noqa: E402
from trendsit.core import config  # noqa: E402
from trendsit.core.artifacts_brief import TopicPage  # noqa: E402

WEEKS = ("2026-W40", "2026-W41")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--db", default=str(ROOT / "data" / "trendsit.db"))
    args = ap.parse_args()
    if not Path(args.db).exists():
        print(f"DB 없음: {args.db}", file=sys.stderr)
        return 2
    conn = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    db = SimpleNamespace(conn=conn)
    runs = {}
    for w in WEEKS:
        r = conn.execute("SELECT current_run_id FROM weeks WHERE week=?", (w,)).fetchone()
        if r is None or not r[0]:
            print(f"run 없음: {w}", file=sys.stderr)
            return 2
        runs[w] = r[0]
    cfg = config.load("brief.yaml")
    keywords = config.load("keywords.yaml")
    tl = cfg.aliases.transliteration
    pages = []
    for week, run in runs.items():
        ev = week_evidence(db, week)  # type: ignore[arg-type]
        table = al.load_decided(db, al.build(list(ev.members.values()), keywords, cfg.aliases.fuzz_min_score, tl))  # type: ignore[arg-type]
        for t in conn.execute("SELECT topic_id, cluster_ids_json, angle FROM topics WHERE run_id=? ORDER BY rank, topic_id", (run,)):
            cids = json.loads(t["cluster_ids_json"])
            members = list(dict.fromkeys(
                r["member"] for cid in cids for r in conn.execute(
                    "SELECT member FROM cluster_items WHERE cluster_id=? ORDER BY rowid", (cid,))))
            ms = [ev.members[k] for k in members if k in ev.members]
            kept, _ = cap_pack(ms, cfg.evidence.max_tokens_per_topic)
            pack = pack_index(kept)
            n_sources = len({it.member for it in kept})
            canon = {a: c.canonical for c in alias_lines(table, ms) for a in c.aliases}
            translit = []
            for name in sorted({n for m in ms for n in m.entities if n.strip()}):
                target = al.to_original(table.canonical(name), tl)
                if (pat := al.translit_pattern(target, tl)) is not None:
                    translit.append((pat, target))
            for p in conn.execute("SELECT round, page_json, raw_json FROM topic_pages WHERE run_id=? AND topic_id=? ORDER BY round",
                                  (run, t["topic_id"])):
                page = TopicPage.model_validate_json(p["raw_json"] if p["round"] == 1 and p["raw_json"] else p["page_json"])
                cr = checks.run_checks(page, pack, n_sources, cfg, canon, translit, t["angle"] or "")
                pages.append({
                    "topic_id": t["topic_id"], "round": p["round"],
                    "issues": [{"loc": i.loc, "type": i.type, "comment": i.comment} for i in cr.issues],
                    "autofix": [{"loc": f["loc"], "rule": f["rule"]} for f in cr.autofix],
                    "warnings": cr.warnings})
    Path(args.out).write_text(json.dumps({"runs": runs, "pages": pages}, ensure_ascii=False, sort_keys=True, indent=1) + "\n",
                              encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
