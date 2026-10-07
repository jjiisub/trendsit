"""채점기. 코드 채점(셀 수 있는 것) → 코드 채점을 통과한 것만 LLM 채점(의미 판단)."""

from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path
from typing import Any

from trendsit.core.artifacts import JudgeInput, JudgeResult
from trendsit.core.config import ROOT
from trendsit.core.context import Ctx
from trendsit.core.role import load_role, run_role

RUBRICS = ROOT / "eval" / "rubrics"
JUDGE_ROLE = "eval/judge.md"

# 공통 문체 검사 (skills/style_ko.md)
HAEYO = re.compile(r"(요|세요|어요|아요|에요|예요|해요|죠)[.!?…]*$")
EVAL_ENDINGS = ("눈에 띈다", "핵심이다", "주목할 만하다", "공통 교훈이다", "주목할 만한", "눈여겨볼")
# 평가어(근거 없는 수식). 레포 설명, 포인트에서 쓰지 않는다
EVAL_WORDS = ("혁신적", "강력한", "놀라운", "최고의", "획기적", "뛰어난", "완벽한", "최첨단", "차세대", "혁명적",
              "압도적", "탁월한", "손쉬운", "쉽고 빠르게", "간편한", "똑똑한")
# 명사형이 아닌 문장 끝: "~다", "~요", "~까", 마침표 등
SENTENCE_END = re.compile(r"(다|요|까|죠|니다|네)[.!?…]*$|[.!?]$")

# 관문 B 문턱값 (S0_TASK 7장). 채점표 항목 이름 기준
THRESHOLDS: dict[str, dict[str, Any]] = {
    "repo_oneliner": {"primary": "정확성", "primary_avg": 4.5, "primary_ones": 0, "others_avg": 4.0,
                      "below3": 0, "code_pass_all": True},
    "lookup_agent": {"code_pass_all": True},
}


def _strings(obj: Any) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, str):
                out.append((k, v))
            else:
                out.extend(_strings(v))
    elif isinstance(obj, list):
        for v in obj:
            out.extend(_strings(v))
    return out


def check(name: str, ok: bool, detail: str = "") -> dict[str, Any]:
    return {"name": name, "passed": bool(ok), "detail": detail}


def style_checks(output: dict[str, Any]) -> list[dict[str, Any]]:
    checks = []
    for key, text in _strings(output):
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n", text) if s.strip()]
        bad = [s for s in sentences if HAEYO.search(s)]
        checks.append(check(f"해요체 없음({key})", not bad, "; ".join(bad)[:120]))
        ev = [e for e in EVAL_ENDINGS if e in text]
        checks.append(check(f"평가형 마무리 없음({key})", not ev, ", ".join(ev)))
    return checks


def code_repo_oneliner(inp: dict[str, Any], out: dict[str, Any], expect: dict[str, Any]) -> list[dict[str, Any]]:
    line = out["oneliner"].strip()
    checks = [
        check("길이 상한", len(line) <= expect.get("max_len", 60), f"{len(line)}자"),
        check("명사형 끝", not SENTENCE_END.search(line), line[-8:]),
        check("평가어 없음", not [w for w in EVAL_WORDS if w in line],
              ", ".join(w for w in EVAL_WORDS if w in line)),
    ]
    must = expect.get("must_include_any")
    if must:
        hit = [m for m in must if m.lower() in line.lower()]
        checks.append(check("핵심어 포함", bool(hit), f"후보 {must}"))
    if "attention" in expect:
        checks.append(check("attention", out["attention"] == expect["attention"],
                            f"기대 {expect['attention']}, 출력 {out['attention']}"))
    return checks


def code_lookup_agent(inp: dict[str, Any], out: dict[str, Any], expect: dict[str, Any]) -> list[dict[str, Any]]:
    checks = [check("doc_id", out["doc_id"] == expect["doc_id"], f"기대 {expect['doc_id']}, 출력 {out['doc_id']}")]
    if "attention" in expect:
        checks.append(check("attention", out["attention"] == expect["attention"],
                            f"기대 {expect['attention']}, 출력 {out['attention']}"))
    return checks


ROLE_CHECKS = {"repo_oneliner": code_repo_oneliner, "lookup_agent": code_lookup_agent}


def code_grade(role: str, inp: dict[str, Any], out: dict[str, Any] | None, error: str | None,
               expect: dict[str, Any]) -> dict[str, Any]:
    if out is None:
        checks = [check("스키마", False, error or "출력 없음")]
    else:
        checks = [check("스키마", True)] + ROLE_CHECKS[role](inp, out, expect) + style_checks(out)
    return {"passed": all(c["passed"] for c in checks), "checks": checks,
            "failed": [f"{c['name']}: {c['detail']}" for c in checks if not c["passed"]]}


# ---------- LLM 채점 ----------
def rubric_path(role: str) -> Path:
    return RUBRICS / f"{role}.md"


def rubric_criteria(role: str) -> list[str]:
    """채점표 표의 첫 칸(항목 이름)."""
    names = []
    for line in rubric_path(role).read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if line.strip().startswith("|") and cells and cells[0] not in ("항목", "") and not set(cells[0]) <= {"-"}:
            names.append(cells[0])
    return names


def llm_grade(role: str, inp: dict[str, Any], out: dict[str, Any], ctx: Ctx) -> dict[str, Any]:
    """채점표를 시스템 프롬프트에 그대로 넣은 채점자 역할(judge)을 1회 실행."""
    judge = load_role(JUDGE_ROLE, ctx.models, extra_includes=(str(rubric_path(role).relative_to(ROOT)),))
    judge_ctx = replace(ctx, model=None)  # 채점자는 항상 judge 별칭
    shown = {k: v for k, v in out.items() if k not in ("log", "attention")}
    result: JudgeResult = run_role(judge, JudgeInput(task_input=inp, output=shown), judge_ctx)  # type: ignore[assignment]
    ctx.last_step_id = judge_ctx.last_step_id
    criteria = rubric_criteria(role)
    scores = {s.criterion: {"score": s.score, "reason": s.reason} for s in result.scores}
    missing = [c for c in criteria if c not in scores]
    return {"scores": {c: scores[c] for c in criteria if c in scores}, "missing": missing,
            "judge_prompt_hash": judge.prompt_hash, "judge_step_id": judge_ctx.last_step_id}


def summarize(role: str, results: list[dict[str, Any]]) -> dict[str, Any]:
    th = THRESHOLDS.get(role, {"code_pass_all": True})
    n = len(results)
    code_pass = sum(1 for r in results if r["code"]["passed"])
    summary: dict[str, Any] = {"n": n, "code_pass": code_pass, "criteria": {}}
    criteria = rubric_criteria(role) if rubric_path(role).exists() else []
    below3 = 0
    for c in criteria:
        vals = [r["llm"]["scores"][c]["score"] for r in results if r.get("llm") and c in r["llm"]["scores"]]
        summary["criteria"][c] = {"avg": round(sum(vals) / len(vals), 2) if vals else None,
                                  "ones": sum(1 for v in vals if v == 1), "n": len(vals)}
        below3 += sum(1 for v in vals if v < 3)
    summary["below3"] = below3
    reasons = []
    missing = sum(1 for r in results if r.get("llm") and r["llm"].get("missing"))
    if missing:  # 채점자가 항목을 빠뜨리면 그 항목 평균이 적은 표본으로 계산되므로 미달
        reasons.append(f"채점 항목 누락 {missing}건")
    if th.get("code_pass_all") and code_pass < n:
        reasons.append(f"코드 채점 통과 {code_pass}/{n}")
    if criteria:
        missing_llm = sum(1 for r in results if r["code"]["passed"] and not r.get("llm"))
        if missing_llm:
            reasons.append(f"LLM 채점 누락 {missing_llm}건")
        p = th.get("primary")
        if p:
            pc = summary["criteria"].get(p, {})
            if pc.get("avg") is None or pc["avg"] < th["primary_avg"]:
                reasons.append(f"{p} 평균 {pc.get('avg')} < {th['primary_avg']}")
            if pc.get("ones", 0) > th["primary_ones"]:
                reasons.append(f"{p} 1점 {pc['ones']}개")
            for c in criteria:
                if c != p:
                    a = summary["criteria"][c]["avg"]
                    if a is None or a < th["others_avg"]:
                        reasons.append(f"{c} 평균 {a} < {th['others_avg']}")
        if below3 > th.get("below3", 0):
            reasons.append(f"3점 미만 항목 {below3}개")
    summary["passed"] = not reasons
    summary["fail_reasons"] = reasons
    return summary
