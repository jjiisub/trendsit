"""S6b 명령(COMMON 9장: 스펙별 파일의 register): publish, ops nightly, ops weekly. S6a: export."""

from __future__ import annotations

import argparse
import signal
import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path
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


def cmd_export(args: argparse.Namespace) -> int:
    from .core.config import ROOT
    from .core.db import open_db
    from .export import ExportError, export

    try:
        export(open_db(), Path(args.out) if args.out else ROOT / "data" / "site.json")
    except (ExportError, sqlite3.Error) as e:
        print(f"export 실패: {e}", file=sys.stderr)
        return 1
    return 0


def cmd_backup(args: argparse.Namespace) -> int:
    from .core.config import ROOT
    from .core.db import KST, open_db

    dest = ROOT / "data" / "backup" / (datetime.now(KST).strftime("%Y%m%d-%H%M") + (f"-{args.tag}" if args.tag else "") + ".db")
    if dest.exists():
        print(f"backup: 같은 이름이 있음 ({dest})", file=sys.stderr)
        return 1
    try:
        open_db().backup(dest)
    except (OSError, sqlite3.Error) as e:
        print(f"backup: {e}", file=sys.stderr)
        return 1
    print(str(dest))
    return 0


def cmd_ops(args: argparse.Namespace) -> int:
    from .core import config
    from .core.db import open_db
    from .ops import nightly, on_sigterm, weekly

    signal.signal(signal.SIGTERM, on_sigterm)  # launchd 종료·kill에도 잠금 해제와 runs 행 마감이 돌게
    cfg = config.load("ops.yaml")
    if args.ops_cmd == "nightly":
        return nightly(open_db(), cfg, day=args.day)
    return weekly(open_db(), cfg, week=args.week)


def register(sub: Any) -> None:
    p = sub.add_parser("publish", help="주간 브리핑 발행(S6b): 사이트 빌드 후 weeks.status published")
    p.add_argument("--week", type=_week, required=True)
    p.set_defaults(fn=cmd_publish)

    e = sub.add_parser("export", help="사이트 데이터(S6a): DB → data/site.json(발행된 주만). 실패하면 기존 파일을 그대로 둔다")
    e.add_argument("--out", help="기본: data/site.json")
    e.set_defaults(fn=cmd_export)

    b = sub.add_parser("backup", help="DB 수동 백업(S6-1): data/backup/<시각>[-<tag>].db")
    b.add_argument("--tag")
    b.set_defaults(fn=cmd_backup)

    o = sub.add_parser("ops", help="자동 실행(S6b): launchd가 부르는 nightly, weekly")
    os_ = o.add_subparsers(dest="ops_cmd", required=True)
    n = os_.add_parser("nightly", help="따라잡기 범위의 날마다 수집 → 분석(없으면 --day 하루). 종료 코드 0/1/3")
    n.add_argument("--day", type=_day, help="그날 하나만(범위 계산 생략, 손 실행용)")
    w = os_.add_parser("weekly", help="지난 ISO 주차 브리핑 → 성공하면 발행. 이미 발행이면 아무것도 안 함")
    w.add_argument("--week", type=_week, help="기본: 지난 ISO 주차")
    o.set_defaults(fn=cmd_ops)
