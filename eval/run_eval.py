"""평가 실행: 픽스처 → 역할 실행 → 코드 채점 → LLM 채점 → reports/eval/*.json + reports/<스펙>_quality.md."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from trendsit.core.budget import BudgetExceeded, PriceUnknown
from trendsit.core.config import ROOT
from trendsit.core.context import open_ctx
from trendsit.core.db import KST
from trendsit.core.llm import LLMError
from trendsit.core.role import RoleFailed, load_role, run

from . import graders

FIXTURES = ROOT / "eval" / "fixtures"
REPORTS = ROOT / "reports"


def load_fixtures(role: str, limit: int | None = None) -> list[tuple[str, dict[str, Any]]]:
    paths = sorted((FIXTURES / role).glob("*.json"))
    if limit:
        paths = paths[:limit]
    return [(p.stem, json.loads(p.read_text(encoding="utf-8"))) for p in paths]


def run_eval(role_name: str, model: str | None = None, limit: int | None = None, spec: str | None = None,
             no_cache: bool = False, note: str | None = None) -> dict[str, Any]:
    ctx = open_ctx("eval", spec=spec, model=model, no_cache=no_cache, note=f"eval {role_name} {model or ''}")
    status = "failed"  # 어떤 예외로 끝나도 run을 닫는다
    try:
        report = _evaluate(ctx, role_name, model, limit, note)
        status = "stopped" if report["stopped"] else "ok"
    finally:
        ctx.tracer.finish(status)
    write_quality(ctx.spec)
    return report


def _evaluate(ctx: Any, role_name: str, model: str | None, limit: int | None, note: str | None) -> dict[str, Any]:
    role = load_role(role_name, ctx.models)
    alias = model or role.spec.model
    with_llm = graders.rubric_path(role_name).exists()
    results: list[dict[str, Any]] = []
    stopped = None
    for fid, fx in load_fixtures(role_name, limit):
        rec: dict[str, Any] = {"id": fid, "input": fx["input"], "expect": fx["expect"], "note": fx.get("note")}
        before = ctx.budget.session_cost
        out, error = None, None
        try:
            out = run(role, role.input_cls.model_validate(fx["input"]), ctx).model_dump()
            rec["step_id"] = ctx.last_step_id
        except (RoleFailed, ValidationError) as e:  # 출력 검증 실패, 픽스처 입력 형식 오류는 그 항목의 실패
            error = f"{type(e).__name__}: {e}"
        except (BudgetExceeded, LLMError, PriceUnknown) as e:
            stopped = f"{type(e).__name__}: {e}"
            print(f"[eval] 중단: {stopped}", file=sys.stderr)
            break
        if ctx.stopped:  # 에이전트가 예산 초과로 대체 출력을 내고 멈춤
            stopped = ctx.stopped
            print(f"[eval] 중단: {stopped}", file=sys.stderr)
            break
        rec["output"], rec["error"] = out, error
        rec["code"] = graders.code_grade(role_name, fx["input"], out, error, fx["expect"])
        if with_llm and rec["code"]["passed"]:
            try:
                rec["llm"] = graders.llm_grade(role_name, fx["input"], out, ctx)  # type: ignore[arg-type]
            except (BudgetExceeded, LLMError, PriceUnknown, RoleFailed) as e:
                stopped = f"채점 {type(e).__name__}: {e}"
                print(f"[eval] 채점 중단: {stopped}", file=sys.stderr)
                results.append(rec)
                break
        rec["cost_usd"] = round(ctx.budget.session_cost - before, 6)
        results.append(rec)
        mark = "통과" if rec["code"]["passed"] else "실패"
        print(f"[eval] {fid}: 코드 {mark} {json.dumps(out, ensure_ascii=False)[:120] if out else error}",
              file=sys.stderr)

    summary = graders.summarize(role_name, results)
    if stopped:
        summary["passed"] = False
        summary["fail_reasons"].append(f"중단: {stopped}")
    now = datetime.now(KST)
    report = {
        "role": role_name, "model_alias": alias, "model_id": ctx.models.models[alias].id,
        "prompt_hash": role.prompt_hash, "spec": ctx.spec, "run_id": ctx.tracer.run_id,
        "at": now.isoformat(timespec="seconds"), "note": note, "stopped": stopped, "limit": limit,
        "cost_usd": round(ctx.budget.session_cost, 6), "summary": summary, "results": results,
    }
    out_dir = REPORTS / "eval"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{role_name}_{alias}_{now:%Y%m%d-%H%M%S}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    report["path"] = str(path.relative_to(ROOT))
    return report


def _is_full(r: dict[str, Any]) -> bool:
    """픽스처 전체를 돈 실행인지(--limit 부분 실행, 중단된 실행 제외)."""
    total = len(list((FIXTURES / r["role"]).glob("*.json")))
    return not r.get("limit") and not r.get("stopped") and r["summary"]["n"] == total


# ---------- 사람이 읽는 리포트 ----------
def _all_reports(spec: str) -> list[dict[str, Any]]:
    reps = []
    for p in sorted((REPORTS / "eval").glob("*.json")):
        r = json.loads(p.read_text(encoding="utf-8"))
        if r.get("spec") == spec:
            r["path"] = str(p.relative_to(ROOT))
            reps.append(r)
    return sorted(reps, key=lambda r: r["at"])


def _cell(text: Any) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def _worst(results: list[dict[str, Any]], k: int = 3) -> list[dict[str, Any]]:
    def badness(r: dict[str, Any]) -> tuple[int, int, int]:
        if not r["code"]["passed"]:
            return (0, 0, 0)
        scores = [v["score"] for v in (r.get("llm") or {}).get("scores", {}).values()] or [0]
        return (1, min(scores), sum(scores))

    return sorted(results, key=badness)[:k]


def write_quality(spec: str) -> Path:
    reps = _all_reports(spec)
    lines = [f"# {spec} 품질 리포트 (관문 B)", "",
             "> `python -m trendsit eval`이 자동 생성한다. 원자료는 `reports/eval/*.json`.", ""]
    for role in dict.fromkeys(r["role"] for r in reps):
        rr = [r for r in reps if r["role"] == role]
        latest: dict[str, dict[str, Any]] = {}  # 모델별 가장 최근의 전체 실행
        for r in rr:
            if _is_full(r):
                latest[r["model_alias"]] = r
        if not latest:
            lines += [f"## {role}", "", "전체 픽스처를 돈 실행 없음(부분 실행만 있음)", ""]
            continue
        criteria = graders.rubric_criteria(role) if graders.rubric_path(role).exists() else []
        th = graders.THRESHOLDS.get(role, {})
        lines += [f"## {role}", ""]
        if th.get("primary"):
            lines += [f"문턱값(generate 기준): {th['primary']} 평균 {th['primary_avg']} 이상이고 1점 0개, "
                      f"나머지 평균 {th['others_avg']} 이상, 3점 미만 항목 0개, 코드 채점 전부 통과", ""]
        elif th:
            lines += ["문턱값: 코드 채점 전부 통과", ""]
        head = ["모델", "코드 통과"] + [f"{c} 평균(1점)" for c in criteria] + ["3점 미만", "문턱값", "비용", "프롬프트"]
        lines += ["### 모델별 최신 결과 (전체 실행만)", "", "| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
        for alias, r in latest.items():
            s = r["summary"]
            row = [f"{alias} (`{r['model_id']}`)", f"{s['code_pass']}/{s['n']}"]
            row += [f"{s['criteria'][c]['avg']} ({s['criteria'][c]['ones']})" for c in criteria]
            row += [str(s.get("below3", "-")) if criteria else "-", "통과" if s["passed"] else "미달",
                    f"${r['cost_usd']:.4f}", f"`{r['prompt_hash']}`"]
            lines.append("| " + " | ".join(row) + " |")
        lines.append("")
        for alias, r in latest.items():
            if r["summary"]["fail_reasons"]:
                lines.append(f"- {alias} 미달 이유: {'; '.join(r['summary']['fail_reasons'])}")
        if "judge" in latest and criteria:
            lines += ["- judge 행은 상한선 측정용. 생성과 채점이 같은 모델이라 자기 출력 채점 편향 가능성이 있음"]
        lines.append("")

        if len(latest) > 1 or role == "repo_oneliner":
            field = "oneliner" if role == "repo_oneliner" else "doc_id"
            aliases = list(latest)
            lines += ["### 출력 나란히", "", "| 픽스처 | " + " | ".join(aliases) + " |",
                      "|---|" + "---|" * len(aliases)]
            ids = list(dict.fromkeys(x["id"] for r in latest.values() for x in r["results"]))
            for fid in ids:
                cells = []
                for a in aliases:
                    x = next((x for x in latest[a]["results"] if x["id"] == fid), None)
                    if x is None:
                        cells.append("-")
                        continue
                    val = (x["output"] or {}).get(field, x.get("error"))
                    sc = (x.get("llm") or {}).get("scores", {})
                    tag = "/".join(str(v["score"]) for v in sc.values()) if sc else (
                        "코드 실패" if not x["code"]["passed"] else "")
                    cells.append(_cell(f"{val} [{tag}]" if tag else val))
                lines.append(f"| {fid} | " + " | ".join(cells) + " |")
            lines.append("")

        gen = latest.get("generate") or next(iter(latest.values()))
        lines += [f"### 가장 나쁜 사례 3개 ({gen['model_alias']}, {gen['at']})", ""]
        for i, x in enumerate(_worst(gen["results"]), 1):
            inp = x["input"]
            brief = {k: (v[:300] + "…" if isinstance(v, str) and len(v) > 300 else v) for k, v in inp.items()}
            lines += [f"{i}. **{x['id']}**",
                      f"   - 입력: `{_cell(json.dumps(brief, ensure_ascii=False))}`",
                      f"   - 출력: `{_cell(json.dumps(x['output'], ensure_ascii=False) if x['output'] else x['error'])}`"]
            if x["code"]["failed"]:
                lines.append(f"   - 코드 채점 실패: {_cell('; '.join(x['code']['failed']))}")
            for c, v in ((x.get("llm") or {}).get("scores") or {}).items():
                lines.append(f"   - {c} {v['score']}점: {_cell(v['reason'])}")
        lines.append("")

        lines += ["### 반복 기록", "", "| 시각 | 모델 | 프롬프트 | 결과 | 비용 | 메모 |", "|---|---|---|---|---|---|"]
        for r in rr:
            s = r["summary"]
            crit = ", ".join(f"{c} {s['criteria'][c]['avg']}" for c in criteria)
            res = f"코드 {s['code_pass']}/{s['n']}" + (f", {crit}" if crit else "") + (
                ", 통과" if s["passed"] else ", 미달") + ("" if _is_full(r) else " (부분 실행)")
            lines.append(f"| {r['at']} | {r['model_alias']} | `{r['prompt_hash']}` | {_cell(res)} | "
                         f"${r['cost_usd']:.4f} | {_cell(r.get('note') or '')} |")
        lines.append("")
    path = REPORTS / f"{spec}_quality.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
