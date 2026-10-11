"""S5 주간 브리핑 명령(COMMON 9장: 스펙별 파일의 register): cluster, weekly, select, write, review."""

from __future__ import annotations

import argparse
import re
import sys
from typing import Any

from .core.trace import Tracer

WEEK = re.compile(r"^\d{4}-W\d{2}$")


def _week(v: str) -> str:
    if not WEEK.match(v):
        raise argparse.ArgumentTypeError("주차 형식 YYYY-Www(예: 2026-W42)")
    return v


def _guard_published(db: Any, week: str, force: bool) -> int | None:
    """발행된 주는 --force 없이 다시 쓰지 않는다(종료 코드 2). --force면 발행을 푼다(status done, published_at NULL: C-3)."""
    if not db.conn.execute("SELECT 1 FROM weeks WHERE week=? AND status='published'", (week,)).fetchone():
        return None
    if not force:
        print("발행된 주: --force로 다시 실행", file=sys.stderr)
        return 2
    with db.conn:
        db.conn.execute("UPDATE weeks SET status='done', published_at=NULL WHERE week=?", (week,))
    return None


def cmd_cluster(args: argparse.Namespace) -> int:
    from .brief.report import write_cluster_report, write_label_sheets
    from .brief.weekly import stage_cluster
    from .core import config
    from .core.context import open_ctx

    # 발행 검사는 명령이 쓰는 DB 연결로. 거부하면 runs 행을 만들지 않도록 실행 기록은 검사 뒤에 연다
    ctx = open_ctx(None, spec=config.current_spec(args.spec, "S5"), no_cache=args.no_cache)
    if (refused := _guard_published(ctx.db, args.week, getattr(args, "force", False))) is not None:
        return refused
    if ctx.tracer is None:
        ctx.tracer = Tracer(ctx.db, "weekly", ctx.spec, f"cluster {args.week}")
    status = "ok"
    try:
        stage = stage_cluster(args.week, ctx, use_llm=not args.no_llm)
        path = write_cluster_report(stage, config.load("brief.yaml"),
                                    note=args.note or "")
        if ctx.stopped:
            status = "stopped"
        else:  # 멈춘 run은 그 주 라벨 시트 행을 덮지 않음
            write_label_sheets(stage)
    except Exception:
        status = "failed"
        raise
    finally:
        ctx.tracer.finish(status)
    res = stage.result
    print(f"run {stage.run_id}: 묶음 {len(res.clusters)}(토픽 후보 {len(res.candidates())}), decide {res.decide_calls}회, "
          f"리포트 {path}")
    if ctx.stopped:
        print(ctx.stopped, file=sys.stderr)
        return 1
    return 0


def cmd_weekly(args: argparse.Namespace) -> int:
    import json

    from .brief.briefing import write_briefing_md
    from .brief.pipeline import run_weekly
    from .core import config
    from .core.context import open_ctx

    until = getattr(args, "step", None)  # select/write/review 단계 명령
    until = until if until in ("select", "write") else None
    from_step = args.from_step
    ctx = open_ctx(None, spec=config.current_spec(args.spec, "S5"), no_cache=args.no_cache)
    if (refused := _guard_published(ctx.db, args.week, getattr(args, "force", False))) is not None:
        return refused
    if ctx.tracer is None:
        ctx.tracer = Tracer(ctx.db, "weekly", ctx.spec, f"weekly {args.week} from {from_step}" + (f" until {until}" if until else "")
                            + (f" topic {args.topic}" if getattr(args, "topic", None) else ""))
    status = "ok"
    try:
        summary = run_weekly(args.week, ctx, from_step=from_step, only_topic=getattr(args, "topic", None), until=until)
        status = "ok" if summary["status"] == "done" else summary["status"]
        all_failed = not until and summary["status"] == "failed"  # 현재판이 바뀌지 않음(pipeline._close)
        if not ctx.stopped and not all_failed:  # 멈추거나 전부 실패한 run의 읽기본이 직전 현재판의 읽기본을 덮지 않게
            path = write_briefing_md(ctx.db, args.week, ctx.tracer.run_id)
    except Exception:
        status = "failed"
        raise
    finally:
        ctx.tracer.finish(status)
    print(json.dumps({k: summary[k] for k in ("week", "status", "select", "write", "review", "cost_usd", "duration_sec")},
                     ensure_ascii=False))
    if ctx.stopped:
        print(f"run {ctx.tracer.run_id}, {ctx.stopped}", file=sys.stderr)
        return 1
    if all_failed:
        print(f"run {ctx.tracer.run_id}, 토픽 전부 실패(0개 포함): 현재판 그대로", file=sys.stderr)
        return 1
    print(f"run {ctx.tracer.run_id}, 브리핑 읽기본 {path}")
    return 0


def register(sub: Any) -> None:
    w = sub.add_parser("weekly", help="주간 브리핑(S5): 묶기 → 선별 → 작성 ⇄ 검수 → 저장 → 실행 요약 → 브리핑 읽기본")
    w.add_argument("--week", type=_week, required=True)
    w.add_argument("--from-step", choices=["cluster", "select", "write", "review"], default="cluster",
                   help="앞 단계는 이 주의 현재판 run에서 읽고 새 run으로 이어서")
    w.add_argument("--topic", help="한 토픽만(write·review)")
    w.add_argument("--no-cache", action="store_true")
    w.add_argument("--force", action="store_true", help="발행된 주도 다시 실행(발행은 publish로 따로)")
    w.add_argument("--spec")
    w.set_defaults(fn=cmd_weekly)
    for step, help_ in (("select", "편집장 선별까지(현재판 묶기에서)"), ("write", "작성자 초안 + 코드 검사까지(검수자 없음)"),
                        ("review", "현재판 초안부터 검사 ⇄ 검수 ⇄ 수정")):
        sp = sub.add_parser(step, help=f"주간 브리핑 단계(S5): {help_}")
        sp.add_argument("--week", type=_week, required=True)
        sp.add_argument("--topic")
        sp.add_argument("--no-cache", action="store_true")
        sp.add_argument("--force", action="store_true", help="발행된 주도 다시 실행")
        sp.add_argument("--spec")
        sp.set_defaults(fn=cmd_weekly, step=step, from_step=step)
    c = sub.add_parser("cluster", help="주간 묶기(S5): 근거 목록 → 표기 정규화 → 묶기 → 과거 대조 → 묶기 리포트")
    c.add_argument("--week", type=_week, required=True, help="ISO 주차(예: 2026-W42)")
    c.add_argument("--no-llm", action="store_true", help="decide를 부르지 않음(경계 쌍은 묶지 않음, 0원)")
    c.add_argument("--note", help="리포트 머리에 남길 메모(예: 수집 범위)")
    c.add_argument("--no-cache", action="store_true")
    c.add_argument("--force", action="store_true", help="발행된 주도 다시 실행(발행은 publish로 따로)")
    c.add_argument("--spec")
    c.set_defaults(fn=cmd_cluster)
