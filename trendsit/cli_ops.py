"""S6b 명령(COMMON 9장: 스펙별 파일의 register): publish, ops nightly, ops weekly."""

from __future__ import annotations

import argparse
from typing import Any

from .cli_brief import _week


def cmd_publish(args: argparse.Namespace) -> int:
    from .core.db import open_db
    from .ops import publish

    return publish(open_db(), args.week)


def register(sub: Any) -> None:
    p = sub.add_parser("publish", help="주간 브리핑 발행(S6b): 사이트 빌드 후 weeks.status published")
    p.add_argument("--week", type=_week, required=True)
    p.set_defaults(fn=cmd_publish)
