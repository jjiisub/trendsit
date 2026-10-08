"""video report: 영상 처리 기록을 markdown 표로(검증 산출물과 사람 확인용)."""

from __future__ import annotations

import json

from ..core.db import DB
from . import store


def runs_markdown(db: DB, since: str | None = None, until: str | None = None) -> str:
    rows = store.runs(db, since, until)
    lines = ["| # | 영상 | mode | 상태 | 전사 품질 | 판독 | 슬라이드 전용 | 확인 필요 | log |", "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        d = json.loads(r["digest_json"]) if r.get("digest_json") else {}
        read = f"{d['frames_read']}/{d['frames_total']}" if d else ""
        log = (d.get("log") or r.get("note") or "").replace("|", "/")
        lines.append(f"| {r['id']} | {r['video_id']} | {r['mode']} | {r['status']} | {r['transcript_quality'] or ''} "
                     f"| {read} | {len(d.get('slide_only_facts', [])) if d else ''} "
                     f"| {len(d.get('check_numbers', [])) if d else ''} | {log} |")
    return "\n".join(lines) + f"\n\n{len(rows)}건\n"
