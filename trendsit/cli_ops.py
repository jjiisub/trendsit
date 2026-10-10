"""S6b 명령(COMMON 9장: 스펙별 파일의 register): publish, ops nightly, ops weekly."""

from __future__ import annotations

import argparse
from datetime import date
from typing import Any

from .cli_brief import _week


def _day(v: str) -> date:
    try:
        return date.fromisoformat(v)
    except ValueError:
        raise argparse.ArgumentTypeError("날짜 형식 YYYY-MM-DD") from None


def cmd_publish(args: argparse.Namespace) -> int:
    from .core.db import open_db
    from .ops import publish

    return publish(open_db(), args.week)


def cmd_ops(args: argparse.Namespace) -> int:
    from .core import config
    from .core.db import open_db
    from .ops import nightly, weekly

    cfg = config.load("ops.yaml")
    if args.ops_cmd == "nightly":
        return nightly(open_db(), cfg, day=args.day)
    return weekly(open_db(), cfg, week=args.week)


def register(sub: Any) -> None:
    p = sub.add_parser("publish", help="주간 브리핑 발행(S6b): 사이트 빌드 후 weeks.status published")
    p.add_argument("--week", type=_week, required=True)
    p.set_defaults(fn=cmd_publish)

    o = sub.add_parser("ops", help="자동 실행(S6b): launchd가 부르는 nightly, weekly")
    os_ = o.add_subparsers(dest="ops_cmd", required=True)
    n = os_.add_parser("nightly", help="따라잡기 범위의 날마다 수집 → 분석(없으면 --day 하루). 종료 코드 0/1/3")
    n.add_argument("--day", type=_day, help="그날 하나만(범위 계산 생략, 손 실행용)")
    w = os_.add_parser("weekly", help="지난 ISO 주차 브리핑 → 성공하면 발행. 이미 발행이면 아무것도 안 함")
    w.add_argument("--week", type=_week, help="기본: 지난 ISO 주차")
    o.set_defaults(fn=cmd_ops)
