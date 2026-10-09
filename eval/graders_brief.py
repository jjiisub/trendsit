"""S5 채점: 주간 브리핑 역할의 코드 채점과 관문 B 문턱값(S5_TASK 7장). graders.py 끝의 _load가 읽는다."""

from __future__ import annotations

from typing import Any

from trendsit.core import config

from . import graders
from .graders import check


def _merged(out: dict[str, Any], min_conf: float) -> bool:
    """코드가 실제로 묶는지: same이고 confidence가 문턱 이상."""
    return bool(out["same"]) and out["confidence"] >= min_conf


def code_decide(inp: dict[str, Any], out: dict[str, Any], expect: dict[str, Any]) -> list[dict[str, Any]]:
    min_conf = config.load("brief.yaml").cluster.decide.min_confidence
    merged = _merged(out, min_conf)
    return [
        check("묶기 판정이 기대와 같음", merged == expect["same"],
              f"기대 {'묶음' if expect['same'] else '안 묶음'}, 출력 same={out['same']} conf={out['confidence']}"),
        check("reason 있음", bool(out["reason"].strip()), "reason 비어 있음"),
    ]


def aggregate_decide(results: list[dict[str, Any]]) -> tuple[dict[str, Any], list[str]]:
    """오병합(기대 false인데 실제로 묶임) 0이 문턱값. 정확도는 보고용."""
    min_conf = config.load("brief.yaml").cluster.decide.min_confidence
    rows = [r for r in results if r.get("output")]
    wrong_merge = [r["id"] for r in rows if not r["expect"]["same"] and _merged(r["output"], min_conf)]
    missed = [r["id"] for r in rows if r["expect"]["same"] and not _merged(r["output"], min_conf)]
    acc = sum(1 for r in rows if _merged(r["output"], min_conf) == r["expect"]["same"])
    reasons = [f"오병합 {len(wrong_merge)}건: {', '.join(wrong_merge)}"] if wrong_merge else []
    return {"정확도": f"{acc}/{len(rows)}", "오병합": len(wrong_merge), "놓친 묶음": ", ".join(missed) or "-"}, reasons


graders.ROLE_CHECKS["decide"] = code_decide
graders.ROLE_STYLE_FIELDS["decide"] = ("log",)
graders.AGGREGATES["decide"] = aggregate_decide
# 오병합 0이 기준. 놓친 묶음(기대 true인데 안 묶음)은 오병합보다 덜 위험해 코드 채점 전부 통과를 요구하지 않는다
graders.THRESHOLDS["decide"] = {"code_pass_all": False}
