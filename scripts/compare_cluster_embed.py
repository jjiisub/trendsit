"""묶기 임베딩 비교(S5 멈춤 지점 결정 2): body(글은 관련성 필터 본문 임베딩) vs card(모든 채널 제목 + 요약).

같은 주를 두 방식으로 묶고(저장하지 않음) 기준으로 비교한다.
- decide 라벨 쌍(eval/labels/decide.csv의 label 칸): 같은 묶음에 들어갔는지 vs 라벨. 오병합 = 라벨 diff인데 같은 묶음
- 지정한 같은 대상 묶음(예: EmbeddingGemma 2 글 3건)이 한 묶음에 모였는지
- decide 호출 수(상한 60), 상한으로 못 부른 후보 수, 묶음 수·1개짜리 비율·2채널 이상
결과: reports/S5_brief/embed_compare_<week>.md. decide는 같은 쌍이면 캐시(0원)

실행: uv run --extra embed python scripts/compare_cluster_embed.py --week 2026-W41 --group it:1045,it:1111,it:1132
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from trendsit.brief import aliases as al  # noqa: E402
from trendsit.brief import cluster as cl  # noqa: E402
from trendsit.brief.evidence import week_evidence  # noqa: E402
from trendsit.brief.weekly import make_decider  # noqa: E402
from trendsit.core import config  # noqa: E402
from trendsit.core.context import open_ctx  # noqa: E402
from trendsit.filter.embed import embed_interests, make_embedder  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", required=True)
    ap.add_argument("--group", action="append", default=[], help="같은 대상이어야 하는 구성원 키(쉼표). 여러 번")
    args = ap.parse_args()
    ctx = open_ctx("weekly", spec="S5", note=f"cluster embed compare {args.week}")
    base = config.load("brief.yaml")
    flt = config.load("filter.yaml")
    embedder = make_embedder("real", flt)
    labels = [r for r in csv.DictReader((ROOT / "eval/labels/decide.csv").open(encoding="utf-8"))
              if r["label"] in ("same", "diff") and r["week"] == args.week]
    groups = [g.split(",") for g in args.group]
    rows, merged_lists = {}, {}
    for mode in ("body", "card"):
        cfg = base.model_copy(deep=True)
        cfg.cluster.embed_text = mode
        ev = week_evidence(ctx.db, args.week)
        table = al.decided_table(ctx.db, list(ev.members.values()), cfg)
        cl.score_video_relevance(list(ev.members.values()), embedder, embed_interests(embedder, flt),
                                 cfg.evidence.video_relevance_high)
        res = cl.cluster_week(ctx.db, ev, table, cfg, embedder, make_decider(ctx))
        owner = {k: i for i, c in enumerate(res.clusters) for k in c.members}
        tp = fp = fn = tn = 0
        wrong = []
        for r in labels:
            together = r["a"] in owner and r["b"] in owner and owner[r["a"]] == owner[r["b"]]
            if r["label"] == "same":
                tp, fn = tp + together, fn + (not together)
            else:
                fp, tn = fp + together, tn + (not together)
                if together:
                    wrong.append(f"{r['a']}↔{r['b']}")
        cands = res.candidates()
        rows[mode] = {
            "라벨 쌍 일치": f"{tp + tn}/{len(labels)}",
            "같은 대상 묶음(라벨 same, 같은 묶음)": f"{tp}/{tp + fn}",
            "오병합(라벨 diff인데 같은 묶음)": f"{fp}" + (f" ({', '.join(wrong)})" if wrong else ""),
            **{f"지정 묶음 {','.join(g)}": "모임" if len({owner.get(k) for k in g}) == 1 else
               f"흩어짐({len({owner.get(k) for k in g})}개 묶음)" for g in groups},
            "decide 호출": f"{res.decide_calls}(경로 border {sum(p.via == 'border' and p.decided for p in res.pairs)}, "
                         f"name {sum(p.via == 'name' and p.decided for p in res.pairs)})",
            "상한으로 못 부른 후보": res.capped_decides,
            "묶음 / 토픽 후보": f"{len(res.clusters)} / {len(cands)}",
            "1개짜리 비율": f"{sum(len(c.members) == 1 for c in cands) / max(1, len(cands)):.0%}",
            "2채널 이상": sum(len(c.channels) >= 2 for c in cands),
        }
        merged_lists[mode] = [[(k, res.members[k].title[:60], c.joined[k][0]) for k in c.members]
                              for c in cands if len(c.members) > 1]
    ctx.tracer.finish("ok")
    out = ROOT / "reports" / "S5_brief" / f"embed_compare_{args.week}.md"
    keys = list(rows["body"])
    lines = [f"# 묶기 임베딩 비교 {args.week}: body vs card", "",
             f"- 라벨: `eval/labels/decide.csv`의 {len(labels)}쌍(labeler opus-5.5-code, 잠정)",
             "- body: 글은 관련성 필터 본문 임베딩(제목 + 피드 요약 + 본문 앞 1,000자), 영상·레포는 제목 + 요약",
             "- card: 모든 채널 제목 + 요약(글 카드 summary, 영상 digest 요약, 레포 oneliner)",
             f"- 문턱값 auto {base.cluster.thresholds.auto} / border {base.cluster.thresholds.border} / "
             f"name_border {base.cluster.name_border}(두 방식 같음)", "",
             "| 기준 | body | card |", "|---|---|---|"]
    lines += [f"| {k} | {rows['body'][k]} | {rows['card'][k]} |" for k in keys]
    for mode in ("body", "card"):
        lines += ["", f"## {mode}: 2개 이상 묶음", ""]
        for i, g in enumerate(merged_lists[mode], 1):
            lines.append(f"{i}. " + " / ".join(f"{k} {t} ({how})" for k, t, how in g))
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
