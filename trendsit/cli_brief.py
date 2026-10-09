"""S5 주간 브리핑 명령(COMMON 9장: 스펙별 파일의 register). 지금은 cluster 단계."""

from __future__ import annotations

import argparse
import re
from typing import Any

WEEK = re.compile(r"^\d{4}-W\d{2}$")


def _week(v: str) -> str:
    if not WEEK.match(v):
        raise argparse.ArgumentTypeError("주차 형식 YYYY-Www(예: 2026-W42)")
    return v


def cmd_cluster(args: argparse.Namespace) -> int:
    from .brief.report import write_cluster_report, write_label_sheets
    from .brief.weekly import stage_cluster
    from .core import config
    from .core.context import open_ctx

    ctx = open_ctx("weekly", spec=args.spec or "S5", no_cache=args.no_cache, note=f"cluster {args.week}")
    status = "ok"
    try:
        stage = stage_cluster(args.week, ctx, use_llm=not args.no_llm)
        path = write_cluster_report(stage, config.load("brief.yaml"),
                                    note=args.note or "")
        write_label_sheets(stage)
    except Exception:
        status = "failed"
        raise
    finally:
        ctx.tracer.finish(status)
    res = stage.result
    print(f"run {stage.run_id}: 묶음 {len(res.clusters)}(토픽 후보 {len(res.candidates())}), decide {res.decide_calls}회, "
          f"리포트 {path}")
    return 0


def register(sub: Any) -> None:
    c = sub.add_parser("cluster", help="주간 묶기(S5): 근거 목록 → 표기 정규화 → 묶기 → 과거 대조 → 묶기 리포트")
    c.add_argument("--week", type=_week, required=True, help="ISO 주차(예: 2026-W42)")
    c.add_argument("--no-llm", action="store_true", help="decide를 부르지 않음(경계 쌍은 묶지 않음, 0원)")
    c.add_argument("--note", help="리포트 머리에 남길 메모(예: 수집 범위)")
    c.add_argument("--no-cache", action="store_true")
    c.add_argument("--spec")
    c.set_defaults(fn=cmd_cluster)
