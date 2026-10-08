"""평가 실행: 픽스처 → 역할 실행 → 코드 채점 → LLM 채점 → reports/eval/*.json + reports/<스펙>_quality.md."""

from __future__ import annotations

import csv
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
        out, error, inp = None, None, None
        final = None
        try:
            inp = role.input_cls.model_validate(fx["input"])
            final = run(role, inp, ctx)
            out = final.raw_dump()  # 통과 판정은 enforce 전 원래 출력(모델 품질을 숨기지 않게, S1 리뷰 M2)
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
        if final is not None and final.enforced:  # enforce 후 출력(저장되는 것)도 함께 기록
            rec["enforced"] = final.enforced
            rec["enforced_output"] = final.model_dump()
            rec["code_enforced"] = graders.code_grade(role_name, fx["input"], rec["enforced_output"], None,
                                                      fx["expect"])
        if with_llm and rec["code"]["passed"]:
            try:
                rec["llm"] = graders.llm_grade(role_name, inp, out, ctx)  # type: ignore[arg-type]
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
    """코드 채점 실패 → fail 판정이 많은 것 → 보고용 점수가 낮은 것 순."""
    def badness(r: dict[str, Any]) -> tuple[int, int, int]:
        if not r["code"]["passed"]:
            return (0, 0, 0)
        llm = r.get("llm") or {}
        fails = sum(1 for v in (llm.get("verdicts") or {}).values() if v["verdict"] == "fail")
        scores = [v["score"] for v in (llm.get("scores") or {}).values()] or [0]
        return (1, -fails, sum(scores))

    return sorted(results, key=badness)[:k]


def _tag(x: dict[str, Any]) -> str:
    if not x["code"]["passed"]:
        return "코드 실패"
    vs = (x.get("llm") or {}).get("verdicts") or {}
    return " ".join(f"{q}{'○' if v['verdict'] == 'pass' else '×'}" for q, v in vs.items())


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
        has_rubric = graders.rubric_path(role).exists()
        questions = graders.rubric_questions(role) if has_rubric else {}
        criteria = graders.rubric_criteria(role) if has_rubric else []
        th = graders.THRESHOLDS.get(role, {})
        lines += [f"## {role}", ""]
        if th.get("questions"):
            need = ", ".join(f"{q} {v:.0%}" for q, v in th["questions"].items())
            lines += [f"문턱값(generate 기준, 코드 채점 통과분의 질문별 통과율): {need} 이상 + 코드 채점 전부 통과", ""]
            for q, text in questions.items():
                lines.append(f"- {q}: {text}")
            lines.append("")
        elif th:
            lines += ["문턱값: 코드 채점 전부 통과", ""]
        agree = agreement(role, spec) if questions else None
        if questions:
            lines += ["judge 판정: " + ("사람 라벨과 일치율 확인됨(아래)" if agree and agree["n_rows"] else
                                         "**잠정**(사람 라벨 없음. `eval/labels/" + role + ".csv`를 채우면 일치율을 잰다)"), ""]
        head = (["모델", "코드 통과", "enforce 후 코드 통과"] + [f"{q} 통과" for q in questions] + [f"{c} 평균" for c in criteria]
                + ["문턱값", "비용", "프롬프트"])
        lines += ["### 모델별 최신 결과 (전체 실행만, 점수는 보고용)", "",
                  "| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
        for alias, r in latest.items():
            s = r["summary"]
            row = [f"{alias} (`{r['model_id']}`)", f"{s['code_pass']}/{s['n']}",
                   f"{s['code_pass_enforced']}/{s['n']}" if "code_pass_enforced" in s else "-"]
            row += [f"{s.get('questions', {}).get(q, {}).get('pass', '-')}/{s.get('questions', {}).get(q, {}).get('n', '-')}"
                    for q in questions]
            row += [str(s.get("criteria", {}).get(c, {}).get("avg", "-")) for c in criteria]
            row += ["통과" if s["passed"] else "미달", f"${r['cost_usd']:.4f}", f"`{r['prompt_hash']}`"]
            lines.append("| " + " | ".join(row) + " |")
        lines.append("")
        for alias, r in latest.items():
            if r["summary"]["fail_reasons"]:
                lines.append(f"- {alias} 미달 이유: {'; '.join(r['summary']['fail_reasons'])}")
        if "judge" in latest and questions:
            lines += ["- judge 행은 상한선 측정용. 생성과 채점이 같은 모델이라 자기 출력 채점 편향 가능성이 있음"]
        lines.append("")

        # 마지막 전체 실행보다 새 부분 실행(중단, --limit)이 있으면 그것을 따로 보여 준다(기준이 바뀐 재측정 등)
        newest = rr[-1]
        if not _is_full(newest) and newest is not latest.get(newest["model_alias"]):
            s2 = newest["summary"]
            qs = ", ".join(f"{q} {v['pass']}/{v['n']}" for q, v in s2.get("questions", {}).items())
            lines += [f"### 가장 최근 실행(부분, {newest['at']}, 프롬프트 `{newest['prompt_hash']}`)", "",
                      f"- {newest.get('note') or ''}",
                      f"- 픽스처 {s2['n']}개까지 진행, 코드 통과 {s2['code_pass']}/{s2['n']}" + (f", {qs}" if qs else ""),
                      f"- 멈춘 이유: {_cell(newest.get('stopped') or '부분 실행(--limit)')}", ""]
            lines += ["| 픽스처 | 출력 | 판정 |", "|---|---|---|"]
            for x in newest["results"]:
                val = (x["output"] or {}).get("oneliner" if role == "repo_oneliner" else "doc_id", x.get("error"))
                lines.append(f"| {x['id']} | {_cell(val)} | {_tag(x) or '채점 전'} "
                             + (f"({_cell('; '.join(x['code']['failed']))})" if x["code"]["failed"] else "") + " |")
            lines.append("")

        if agree and agree["n_rows"]:
            lines += [f"### judge·사람 일치율 (라벨 {agree['n_rows']}건, {agree['report']})", "",
                      "| 질문 | 일치 | 비교 수 | 일치율 |", "|---|---|---|---|"]
            for q, v in agree["questions"].items():
                lines.append(f"| {q} | {v['agree']} | {v['n']} | {v['rate']} |")
            t = agree["total"]
            lines += [f"| 전체 | {t['agree']} | {t['n']} | {t['rate']} |", ""]

        field = {"repo_oneliner": "oneliner", "lookup_agent": "doc_id"}.get(role)
        if field and (len(latest) > 1 or questions):
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
                    tag = _tag(x)
                    cells.append(_cell(f"{val} [{tag}]" if tag else val))
                lines.append(f"| {fid} | " + " | ".join(cells) + " |")
            lines.append("")

        gen = latest.get("generate") or next(iter(latest.values()))
        if not _is_full(newest) and newest["model_alias"] == gen["model_alias"] and newest["at"] > gen["at"]:
            gen = newest  # 가장 최근 기준(부분 실행이라도)의 사례를 보여 준다
        lines += [f"### 가장 나쁜 사례 3개 ({gen['model_alias']}, {gen['at']}{', 부분 실행' if not _is_full(gen) else ''})", ""]
        for i, x in enumerate(_worst(gen["results"]), 1):
            brief = {k: (_brief(v)) for k, v in x["input"].items()}
            lines += [f"{i}. **{x['id']}**",
                      f"   - 입력: `{_cell(json.dumps(brief, ensure_ascii=False))}`",
                      f"   - 출력: `{_cell(json.dumps(x['output'], ensure_ascii=False) if x['output'] else x['error'])}`"]
            if x["code"]["failed"]:
                lines.append(f"   - 코드 채점 실패: {_cell('; '.join(x['code']['failed']))}")
            for c in x.get("enforced") or []:
                lines.append(f"   - enforce: {c['field']} {_cell(c['before'])} → {_cell(c['after'])} ({_cell(c['rule'])})")
            for q, v in ((x.get("llm") or {}).get("verdicts") or {}).items():
                lines.append(f"   - {q} {v['verdict']}: {_cell(v['critique'])}")
        lines.append("")

        lines += ["### 반복 기록", "", "| 시각 | 모델 | 프롬프트 | 결과 | 비용 | 메모(바꾼 것) |", "|---|---|---|---|---|---|"]
        for r in rr:
            s = r["summary"]
            qs = ", ".join(f"{q} {v['pass']}/{v['n']}" for q, v in s.get("questions", {}).items())
            crit = ", ".join(f"{c} {v['avg']}" for c, v in s.get("criteria", {}).items())
            res = f"코드 {s['code_pass']}/{s['n']}" + (f", {qs}" if qs else "") + (f", {crit}" if crit and not qs else "") + (
                ", 통과" if s["passed"] else ", 미달") + ("" if _is_full(r) else " (부분 실행)")
            lines.append(f"| {r['at']} | {r['model_alias']} | `{r['prompt_hash']}` | {_cell(res)} | "
                         f"${r['cost_usd']:.4f} | {_cell(r.get('note') or '')} |")
        lines.append("")
    path = REPORTS / f"{spec}_quality.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _brief(v: Any) -> Any:
    if isinstance(v, str) and len(v) > 300:
        return v[:300] + "…"
    return v


# ---------- judge 맞추기: 사람 라벨 ----------
LABELS = ROOT / "eval" / "labels"
TRUE_WORDS = {"pass", "p", "y", "yes", "1", "o", "예", "통과", "true"}
FALSE_WORDS = {"fail", "f", "n", "no", "0", "x", "아니오", "실패", "false"}


def _latest_full(role: str, spec: str | None, alias: str = "generate") -> dict[str, Any] | None:
    reps = [r for r in (_all_reports(spec) if spec else []) if r["role"] == role and _is_full(r)]
    pick = [r for r in reps if r["model_alias"] == alias] or reps
    return pick[-1] if pick else None


def _input_summary(inp: dict[str, Any]) -> str:
    parts = [f"{k}: {_brief(v)}" for k, v in inp.items() if not isinstance(v, dict | list) and k != "readme_head"]
    return " / ".join(parts)[:300]


def make_labels(role: str, spec: str) -> Path:
    """최근 전체 eval 결과로 라벨 CSV를 만든다. 출력이 이전 CSV와 같은 행만 채운 라벨을 보존하고, 바뀐 행은 비운다."""
    rep = _latest_full(role, spec)
    if rep is None:
        raise SystemExit(f"{role}: 전체 eval 결과가 없음. 먼저 eval {role}을 돌릴 것")
    questions = list(graders.rubric_questions(role))
    cols = ["id", "input_summary", "output"] + [c for q in questions for c in (f"{q}_pass", f"{q}_critique")] + ["eval_report"]
    path = LABELS / f"{role}.csv"
    old: dict[str, dict[str, str]] = {}
    if path.exists():
        with path.open(encoding="utf-8") as f:
            old = {row["id"]: row for row in csv.DictReader(f)}
    LABELS.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for x in rep["results"]:
            shown = {k: v for k, v in (x["output"] or {}).items() if k not in ("log", "attention")}
            row = {"id": x["id"], "input_summary": _input_summary(x["input"]),
                   "output": json.dumps(shown, ensure_ascii=False) if x["output"] else f"(오류) {x.get('error')}",
                   "eval_report": rep["path"]}
            prev = old.get(x["id"], {})
            same = prev.get("output") == row["output"]  # 출력이 이전과 같을 때만 사람 라벨을 이어 쓴다
            for q in questions:
                row[f"{q}_pass"] = prev.get(f"{q}_pass", "") if same else ""
                row[f"{q}_critique"] = prev.get(f"{q}_critique", "") if same else ""
            w.writerow(row)
    return path


def _label_value(text: str) -> bool | None:
    t = (text or "").strip().lower()
    if t in TRUE_WORDS:
        return True
    if t in FALSE_WORDS:
        return False
    return None


def agreement(role: str, spec: str | None = None, path: Path | None = None) -> dict[str, Any] | None:
    """사람 라벨과 judge 판정의 질문별·전체 일치율. 라벨 빈칸은 제외. 라벨이 가리키는 eval 결과와 비교한다."""
    path = path or LABELS / f"{role}.csv"
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    questions = list(graders.rubric_questions(role))
    reports: dict[str, dict[str, Any]] = {}
    stats = {q: {"agree": 0, "n": 0} for q in questions}
    labeled_rows = 0
    for row in rows:
        rp = row.get("eval_report")
        if rp not in reports:
            reports[rp] = json.loads((ROOT / rp).read_text(encoding="utf-8")) if rp and (ROOT / rp).exists() else {}
        x = next((x for x in reports[rp].get("results", []) if x["id"] == row["id"]), None)
        verdicts = ((x or {}).get("llm") or {}).get("verdicts") or {}
        any_label = False
        for q in questions:
            human = _label_value(row.get(f"{q}_pass", ""))
            if human is None or q not in verdicts:
                continue
            any_label = True
            stats[q]["n"] += 1
            stats[q]["agree"] += int(human == (verdicts[q]["verdict"] == "pass"))
        labeled_rows += int(any_label)
    for v in stats.values():
        v["rate"] = round(v["agree"] / v["n"], 3) if v["n"] else None
    total_n = sum(v["n"] for v in stats.values())
    total_a = sum(v["agree"] for v in stats.values())
    return {"questions": stats, "n_rows": labeled_rows, "report": ", ".join(k for k in reports if k),
            "total": {"agree": total_a, "n": total_n, "rate": round(total_a / total_n, 3) if total_n else None}}
