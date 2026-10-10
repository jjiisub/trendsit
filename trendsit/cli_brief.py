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


def cmd_weekly(args: argparse.Namespace) -> int:
    import json

    from .brief.briefing import write_briefing_md
    from .brief.pipeline import run_weekly
    from .core.context import open_ctx

    step = getattr(args, "step", None)  # select/write/review 단계 명령
    from_step = args.from_step if step is None else ("select" if step == "select" else step)
    until = step if step in ("select", "write") else None
    ctx = open_ctx("weekly", spec=args.spec or "S5", no_cache=args.no_cache,
                   note=f"weekly {args.week} from {from_step}" + (f" until {until}" if until else "")
                   + (f" topic {args.topic}" if getattr(args, "topic", None) else ""))
    status = "ok"
    try:
        summary = run_weekly(args.week, ctx, from_step=from_step, only_topic=getattr(args, "topic", None), until=until)
        status = {"ok": "ok", "partial": "partial"}.get(summary["status"], "failed")
        path = write_briefing_md(ctx.db, args.week, ctx.tracer.run_id)
    except Exception:
        status = "failed"
        raise
    finally:
        ctx.tracer.finish(status)
    print(json.dumps({k: summary[k] for k in ("week", "status", "select", "write", "review", "cost_usd", "duration_sec")},
                     ensure_ascii=False))
    print(f"run {ctx.tracer.run_id}, 브리핑 읽기본 {path}")
    return 0


def register(sub: Any) -> None:
    w = sub.add_parser("weekly", help="주간 브리핑(S5): 묶기 → 선별 → 작성 ⇄ 검수 → 저장 → 실행 요약 → 브리핑 읽기본")
    w.add_argument("--week", type=_week, required=True)
    w.add_argument("--from-step", choices=["cluster", "select", "write", "review"], default="cluster",
                   help="앞 단계는 이 주의 현재판 run에서 읽고 새 run으로 이어서")
    w.add_argument("--topic", help="한 토픽만(write·review)")
    w.add_argument("--no-cache", action="store_true")
    w.add_argument("--spec")
    w.set_defaults(fn=cmd_weekly)
    for step, help_ in (("select", "편집장 선별까지(현재판 묶기에서)"), ("write", "작성자 초안 + 코드 검사까지(검수자 없음)"),
                        ("review", "현재판 초안부터 검사 ⇄ 검수 ⇄ 수정")):
        sp = sub.add_parser(step, help=f"주간 브리핑 단계(S5): {help_}")
        sp.add_argument("--week", type=_week, required=True)
        sp.add_argument("--topic")
        sp.add_argument("--no-cache", action="store_true")
        sp.add_argument("--spec")
        sp.set_defaults(fn=cmd_weekly, step=step, from_step=step)
    c = sub.add_parser("cluster", help="주간 묶기(S5): 근거 목록 → 표기 정규화 → 묶기 → 과거 대조 → 묶기 리포트")
    c.add_argument("--week", type=_week, required=True, help="ISO 주차(예: 2026-W42)")
    c.add_argument("--no-llm", action="store_true", help="decide를 부르지 않음(경계 쌍은 묶지 않음, 0원)")
    c.add_argument("--note", help="리포트 머리에 남길 메모(예: 수집 범위)")
    c.add_argument("--no-cache", action="store_true")
    c.add_argument("--spec")
    c.set_defaults(fn=cmd_cluster)
