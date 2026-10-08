"""채점기. 코드 채점(셀 수 있는 것) → 코드 채점을 통과한 것만 LLM 채점(의미 판단)."""

from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from trendsit.core.artifacts import Document, JudgeInput, JudgeResult, RepoOneliner, RoleInput
from trendsit.core.config import ROOT
from trendsit.core.context import Ctx
from trendsit.core.role import load_role, run_role
from trendsit.core.textclean import clean_markdown

RUBRICS = ROOT / "eval" / "rubrics"
JUDGE_ROLE = "eval/judge.md"

# 공통 문체 검사 (skills/style_ko.md)
HAEYO = re.compile(r"(요|세요|어요|아요|에요|예요|해요|죠)[.!?…]*$")
# "요"로 끝나는 명사(명사형 끝말이라 해요체가 아님). "필요해요"처럼 뒤에 어미가 붙으면 HAEYO가 그대로 잡는다
NOUN_YO = re.compile(r"(필요|중요|주요|개요|수요|강요|소요)[.!?…]*$")
EVAL_ENDINGS = ("눈에 띈다", "핵심이다", "주목할 만하다", "공통 교훈이다", "주목할 만한", "눈여겨볼")
# 평가어(근거 없는 수식). 레포 설명, 포인트에서 쓰지 않는다
EVAL_WORDS = ("혁신적", "강력한", "놀라운", "최고의", "획기적", "뛰어난", "완벽한", "최첨단", "차세대", "혁명적",
              "압도적", "탁월한", "손쉬운", "쉽고 빠르게", "간편한", "똑똑한")
# 명사형이 아닌 문장 끝: "~다", "~요", "~까", 마침표 등
SENTENCE_END = re.compile(r"(다|요|까|죠|니다|네)[.!?…]*$|[.!?]$")

# 관문 B 문턱값 (S0_TASK 7장). 채점표 항목 이름 기준
# 관문 B 문턱값. 질문별 통과율(코드 채점 통과분 중). repo_oneliner: S0_ADDENDUM 1.7 (Q1 10/10, Q2·Q3 9/10 이상)
THRESHOLDS: dict[str, dict[str, Any]] = {
    "repo_oneliner": {"questions": {"Q1": 1.0, "Q2": 0.9, "Q3": 0.9}, "code_pass_all": True},
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
        bad = [s for s in sentences if HAEYO.search(s) and not NOUN_YO.search(s)]
        checks.append(check(f"해요체 없음({key})", not bad, "; ".join(bad)[:120]))
        ev = [e for e in EVAL_ENDINGS if e in text]
        checks.append(check(f"평가형 마무리 없음({key})", not ev, ", ".join(ev)))
    return checks


def _norm(text: str) -> str:
    return " ".join(text.replace("&lt;", "<").split())


def code_repo_oneliner(inp: dict[str, Any], out: dict[str, Any], expect: dict[str, Any]) -> list[dict[str, Any]]:
    line = out["oneliner"].strip()
    basis = out.get("basis", "").strip()
    readme = inp.get("readme_head") or ""
    readme = readme.get("text", "") if isinstance(readme, dict) else clean_markdown(readme)
    # basis 검사 기준(설계 결정 S1 Q3): 기호를 걷어 낸 README 본문, 또는 description(둘에 걸친 구절은 안 됨)
    in_source = _norm(basis) in _norm(readme) or _norm(basis) in _norm(inp.get("description") or "")
    checks = [
        check("길이 상한", len(line) <= expect.get("max_len", 60), f"{len(line)}자"),
        check("명사형 끝", not SENTENCE_END.search(line), line[-8:]),
        check("평가어 없음", not [w for w in EVAL_WORDS if w in line],
              ", ".join(w for w in EVAL_WORDS if w in line)),
        # basis는 README에 있는 구절 그대로여야 한다(공백 정규화 후 부분 문자열)
        check("basis가 README 본문이나 description 안에 있음", in_source, basis[:60]),
        check("문장이 있으면 basis도 있음", not line or bool(basis), "basis 비어 있음"),
        check("빈 문장이면 attention", bool(line) or out["attention"] is True, "oneliner 비었는데 attention=false"),
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
# 문체 검사를 할 칸(없으면 출력 전체). 본문을 그대로 옮긴 인용 칸은 원문 문체라 검사하지 않는다
ROLE_STYLE_FIELDS: dict[str, tuple[str, ...]] = {}
# 픽스처 전체를 모아 보는 기준(예: 인용 일치율 95%). role → results → (지표, 미달 이유 목록)
AGGREGATES: dict[str, Any] = {}
# 코드 소유 칸(S4 설계 결정 D2-1, S2~S3 결정 Q1): 규칙이 문자열로 확정 판정되어 enforce가 고친 값이 곧 정답인 칸.
# 통과 판정은 이 칸만 enforce 후 값으로 바꾼 출력으로 한다. 원래 출력 점수는 모델 품질로 따로 기록. role → 칸 목록
ENFORCED_FIELDS: dict[str, tuple[str, ...]] = {}
# S2~S3 역할은 칸 목록을 출력 클래스의 ENFORCED_FIELDS(ClassVar)에 선언하고 여기에 등록한다(한 곳에서만 정함)
ENFORCED_FIELDS["repo_oneliner"] = RepoOneliner.ENFORCED_FIELDS


def basis_output(role: str, raw: dict[str, Any], enforced: dict[str, Any] | None) -> dict[str, Any]:
    """통과 판정용 출력: 원래 출력에서 코드 소유 칸만 enforce 후 값으로."""
    fields = ENFORCED_FIELDS.get(role, ())
    if not fields or enforced is None:
        return raw
    return {**raw, **{k: enforced[k] for k in fields if k in enforced}}


def code_grade(role: str, inp: dict[str, Any], out: dict[str, Any] | None, error: str | None,
               expect: dict[str, Any]) -> dict[str, Any]:
    if out is None:
        checks = [check("스키마", False, error or "출력 없음")]
    else:
        fields = ROLE_STYLE_FIELDS.get(role)
        styled = {k: out[k] for k in fields if k in out} if fields else out
        checks = [check("스키마", True)] + ROLE_CHECKS[role](inp, out, expect) + style_checks(styled)
    return {"passed": all(c["passed"] for c in checks), "checks": checks,
            "failed": [f"{c['name']}: {c['detail']}" for c in checks if not c["passed"]]}


# ---------- LLM 채점 ----------
def rubric_path(role: str) -> Path:
    return RUBRICS / f"{role}.md"


def _table_rows(role: str) -> list[list[str]]:
    rows = []
    for line in rubric_path(role).read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if cells and cells[0] not in ("id", "항목", "") and not set(cells[0]) <= {"-"}:
                rows.append(cells)
    return rows


def rubric_questions(role: str) -> dict[str, str]:
    """통과 질문 표: id → 질문."""
    return {r[0]: r[1] for r in _table_rows(role) if re.fullmatch(r"Q\d+", r[0])}


def rubric_criteria(role: str) -> list[str]:
    """보고용 점수표의 항목 이름."""
    return [r[0] for r in _table_rows(role) if not re.fullmatch(r"Q\d+", r[0])]


def judge_input(inp: RoleInput, out: dict[str, Any]) -> JudgeInput:
    """채점 대상 역할의 입력을 근거 문서와 짧은 칸으로 나눈다(역할 무관)."""
    docs: list[Document] = []
    fields: dict[str, Any] = {}
    for name in type(inp).model_fields:
        v = getattr(inp, name)
        if isinstance(v, Document):
            docs.append(v)
        elif isinstance(v, list) and v and all(isinstance(x, Document) for x in v):
            docs.extend(v)
        else:
            fields[name] = v.model_dump() if isinstance(v, BaseModel) else v
    shown = {k: v for k, v in out.items() if k not in ("log", "attention")}
    return JudgeInput(source_documents=docs, source_fields=fields, output=shown)


def llm_grade(role: str, inp: RoleInput, out: dict[str, Any], ctx: Ctx) -> dict[str, Any]:
    """역할 무관한 채점자(eval/judge.md) + 역할별 채점표(includes)를 1회 실행."""
    judge = load_role(JUDGE_ROLE, ctx.models, extra_includes=(str(rubric_path(role).relative_to(ROOT)),))
    judge_ctx = replace(ctx, model=None)  # 채점자는 항상 judge 별칭
    result: JudgeResult = run_role(judge, judge_input(inp, out), judge_ctx)  # type: ignore[assignment]
    ctx.last_step_id = judge_ctx.last_step_id
    questions, criteria = rubric_questions(role), rubric_criteria(role)
    verdicts = {v.question: {"verdict": v.verdict, "critique": v.critique} for v in result.verdicts}
    scores = {s.criterion: {"score": s.score, "reason": s.reason} for s in result.scores}
    missing = [q for q in questions if q not in verdicts]
    return {"verdicts": {q: verdicts[q] for q in questions if q in verdicts},
            "scores": {c: scores[c] for c in criteria if c in scores}, "missing": missing,
            "judge_prompt_hash": judge.prompt_hash, "judge_step_id": judge_ctx.last_step_id}


def model_agreement(results: list[dict[str, Any]], owned_fields: tuple[str, ...] = ()) -> dict[str, str]:
    """코드 소유 칸별 모델 일치율(설계 결정 Q1, 보고용): 원래 출력이 코드가 정한 값과 같았던 건수/출력 수.

    칸 일부만 코드 소유인 규칙(fix(owned=True), 예: 긴 인용 자르기)도 그 칸 이름으로 센다.
    """
    outs = [r for r in results if r.get("output")]
    changed: dict[str, int] = dict.fromkeys(owned_fields, 0)
    for r in outs:
        fields = {c["field"] for c in r.get("enforced") or [] if c.get("owned", c["field"] in owned_fields)}
        for f in fields:
            changed[f] = changed.get(f, 0) + 1
    return {f: f"{len(outs) - k}/{len(outs)}" for f, k in changed.items()}


def summarize(role: str, results: list[dict[str, Any]]) -> dict[str, Any]:
    th = THRESHOLDS.get(role, {"code_pass_all": True})
    n = len(results)
    code_pass = sum(1 for r in results if r["code"]["passed"])  # 원래 출력(모델 품질)
    # 보고용: enforce 전부 적용한 출력(저장되는 것) 기준 코드 통과
    code_pass_enforced = sum(1 for r in results if r.get("code_enforced", r["code"])["passed"])
    # 통과 판정: 코드 소유 칸(ENFORCED_FIELDS)만 enforce 후 값으로 채점한 결과. 칸 선언이 없으면 원래 출력 판정과 같다
    code_pass_basis = sum(1 for r in results if r.get("code_basis", r["code"])["passed"])
    summary: dict[str, Any] = {"n": n, "code_pass": code_pass, "code_pass_enforced": code_pass_enforced,
                               "code_pass_basis": code_pass_basis,
                               "model_agreement": model_agreement(results, ENFORCED_FIELDS.get(role, ())),
                               "questions": {}, "criteria": {}}
    has_rubric = rubric_path(role).exists()
    questions = rubric_questions(role) if has_rubric else {}
    judged = [r for r in results if r.get("llm")]
    for q in questions:
        vals = [r["llm"]["verdicts"][q]["verdict"] == "pass" for r in judged if q in r["llm"]["verdicts"]]
        summary["questions"][q] = {"pass": sum(vals), "n": len(vals),
                                   "rate": round(sum(vals) / len(vals), 3) if vals else None}
    for c in rubric_criteria(role) if has_rubric else []:  # 보고용
        vals = [r["llm"]["scores"][c]["score"] for r in judged if c in r["llm"]["scores"]]
        summary["criteria"][c] = {"avg": round(sum(vals) / len(vals), 2) if vals else None, "n": len(vals)}
    reasons = []
    if th.get("code_pass_all") and code_pass_basis < n:
        owned = ENFORCED_FIELDS.get(role)
        reasons.append(f"코드 채점 통과 {code_pass_basis}/{n}" + (f"(코드 소유 칸 {', '.join(owned)}은 enforce 후)" if owned else ""))
    if questions:
        # judge 대상: 원래 출력이 통과한 것. 코드 소유 칸을 선언한 역할은 enforce 후 출력이 통과한 것도(그 출력을 채점)
        owned = role in ENFORCED_FIELDS
        missing_llm = sum(1 for r in results if (r["code"]["passed"] or (owned and r.get("code_enforced", r["code"])["passed"]))
                          and not r.get("llm"))
        if missing_llm:
            reasons.append(f"LLM 채점 누락 {missing_llm}건")
        missing = sum(1 for r in judged if r["llm"].get("missing"))
        if missing:  # 채점자가 질문을 빠뜨리면 그 질문 통과율이 적은 표본으로 계산되므로 미달
            reasons.append(f"채점 질문 누락 {missing}건")
        for q, need in th.get("questions", {}).items():
            st = summary["questions"].get(q, {})
            if st.get("rate") is None or st["rate"] < need:
                reasons.append(f"{q} 통과 {st.get('pass')}/{st.get('n')} < {need:.0%}")
    if role in AGGREGATES:
        summary["aggregate"], more = AGGREGATES[role](results)
        reasons += more
    summary["passed"] = not reasons
    summary["fail_reasons"] = reasons
    return summary


# ---------- 스펙별 채점 모듈(COMMON 9장): ROLE_CHECKS, ROLE_STYLE_FIELDS, THRESHOLDS, AGGREGATES에 등록 ----------
def _load(module: str) -> None:
    import importlib

    try:
        importlib.import_module(f"eval.{module}")
    except ModuleNotFoundError as e:
        if e.name != f"eval.{module}":
            raise


_load("graders_text")  # S2~S3
_load("graders_video")  # S4
