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


# ---------- writer(관문 B: 근거 충실성은 원자 사실 judge, 나머지 Q1~Q4 judge + 코드 검사) ----------
def _pack_from_docs(inp: dict[str, Any]) -> dict[str, list[Any]]:
    """작성자 입력의 근거 문서 → 코드 검사용 근거 목록. 원문 기준(리뷰 R2): 글 카드의 주장·요약 줄은 빼고 quote·수치 줄만."""
    from trendsit.brief.evidence import EvidenceItem

    out = {}
    for d in inp["evidence"]:
        ch = "video" if d["id"].startswith("vd:") else "github" if d["id"].startswith("rp:") else "text"
        text = d["text"]
        if ch == "text":  # 지금 작성자 입력에는 주장·요약 줄이 없음. 이전 픽스처의 "주장: "·"요약: " 줄을 뺌
            text = "\n".join(ln for ln in text.splitlines() if not ln.startswith(("(카드 주장", "주장: ", "요약: ")))
        out[d["id"]] = [EvidenceItem(d["id"], d["id"].split("#")[0].split("@")[0], ch, "quote", text,
                                     {"site": d.get("source"), "title": d.get("title")})]
    return out


def code_writer(inp: dict[str, Any], out: dict[str, Any], expect: dict[str, Any]) -> list[dict[str, Any]]:
    """원래 출력에 S5 코드 검사(5.7)를 그대로. 반려 사유 0이면 통과. 자동 수정은 실패가 아님."""
    from trendsit.brief.checks import run_checks
    from trendsit.core.artifacts_brief import TopicPage

    cfg = config.load("brief.yaml")
    pack = _pack_from_docs(inp)
    n_sources = len({k.split("#")[0].split("@")[0] for k in pack})
    r = run_checks(TopicPage.model_validate(out), pack, n_sources, cfg, {})
    by_type: dict[str, list[str]] = {}
    for i in r.issues:
        by_type.setdefault("문체(금지어·명사형)" if "금지 표현" in i.comment or "끝남" in i.comment or "'~다'" in i.comment
                           else i.type, []).append(i.comment)
    checks = [check("코드 검사 반려 없음", not r.issues, "; ".join(i.comment for i in r.issues)[:200])]
    checks.append(check("문체 위반 0(코드 정규식)", "문체(금지어·명사형)" not in by_type,
                        "; ".join(by_type.get("문체(금지어·명사형)", []))[:160]))
    return checks


def aggregate_writer(results: list[dict[str, Any]]) -> tuple[dict[str, Any], list[str]]:
    """근거 충실성: 모든 토픽 원자 사실 지지율 100%(judge_facts). 문체 위반 0."""
    facts = [(r["id"], r["llm"]["facts"]) for r in results if r.get("llm") and r["llm"].get("facts")]
    low = [(i, f) for i, f in facts if f["supported"] < f["total"]]
    style = [r["id"] for r in results if r.get("code") and any("문체" in x for x in r["code"]["failed"])]
    total = sum(f["total"] for _, f in facts)
    sup = sum(f["supported"] for _, f in facts)
    reasons = []
    if low:
        reasons.append(f"근거 충실성 100% 미달 토픽 {len(low)}/{len(facts)}")
    if style:
        reasons.append(f"문체 위반 {len(style)}건")
    return {"근거 충실성(토픽 100%)": f"{len(facts) - len(low)}/{len(facts)}",
            "원자 사실 지지": f"{sup}/{total}" + (f" ({sup / total:.1%})" if total else ""),
            "문체 위반": len(style)}, reasons


graders.ROLE_CHECKS["writer"] = code_writer
graders.ROLE_STYLE_FIELDS["writer"] = ("log",)  # 칸별 문체는 code_writer(S5 코드 검사)가 봄
graders.AGGREGATES["writer"] = aggregate_writer
graders.FACT_JUDGES["writer"] = "eval/judge_facts.md"
# 코드 검사 반려가 있어도 그 출력은 라운드에서 고쳐지므로 코드 전부 통과는 요구하지 않음. 질문 90%, 충실성 100%
graders.THRESHOLDS["writer"] = {"questions": {"Q1": 0.9, "Q2": 0.9, "Q3": 0.9, "Q4": 0.9}, "code_pass_all": False}


# ---------- critic(심은 오류·깨끗한 초안 픽스처: 반려해야 할 것을 반려, 깨끗한 것은 통과) ----------
def code_critic(inp: dict[str, Any], out: dict[str, Any], expect: dict[str, Any]) -> list[dict[str, Any]]:
    want = expect["status"]
    checks = [check("판정이 기대와 같음", out["status"] == want, f"기대 {want}, 출력 {out['status']}")]
    if want == "reject" and expect.get("loc"):
        hit = [i for i in out["issues"] if i["loc"].split(".")[0].replace(" ", "") == expect["loc"]]
        checks.append(check("심은 오류 위치를 짚음", bool(hit), f"기대 {expect['loc']}, 출력 {[i['loc'] for i in out['issues']]}"))
    return checks


def aggregate_critic(results: list[dict[str, Any]]) -> tuple[dict[str, Any], list[str]]:
    rows = [r for r in results if r.get("output")]
    agree = sum(1 for r in rows if r["output"]["status"] == r["expect"]["status"])
    clean = [r for r in rows if r["expect"]["status"] == "pass"]
    over = sum(1 for r in clean if r["output"]["status"] == "reject")
    planted = [r for r in rows if r["expect"]["status"] == "reject"]
    caught = sum(1 for r in planted if r["output"]["status"] == "reject")
    rate = agree / len(rows) if rows else 0
    reasons = [] if rate >= 0.8 else [f"판정 일치 {agree}/{len(rows)} < 80%"]
    return {"판정 일치": f"{agree}/{len(rows)} ({rate:.0%})", "심은 오류 반려": f"{caught}/{len(planted)}",
            "깨끗한 초안 과잉 반려": f"{over}/{len(clean)}"}, reasons


graders.ROLE_CHECKS["critic"] = code_critic
graders.ROLE_STYLE_FIELDS["critic"] = ("log",)
graders.AGGREGATES["critic"] = aggregate_critic
graders.THRESHOLDS["critic"] = {"code_pass_all": False}


# ---------- editor_select(코드 검증 100%, drop 이유 라벨 일치는 리뷰 라벨로) ----------
def code_editor_select(inp: dict[str, Any], out: dict[str, Any], expect: dict[str, Any]) -> list[dict[str, Any]]:
    from trendsit.brief.select import Candidate, reason_mismatches, reconcile, validate
    from trendsit.core.artifacts_brief import BriefingPlan, EditorSelectInput

    cands = [Candidate(c["cluster_id"], "", c["members"], {}, 0, c.get("past", [])) for c in expect["candidates"]]
    raw = BriefingPlan.model_validate(out)
    plan, _notes = reconcile(raw)  # decisions↔topics 맞춤은 코드 소유(pipeline과 같음). 원래 출력 어긋남은 aggregate에 기록
    errs = validate(plan, cands, config.load("brief.yaml"))
    mism = reason_mismatches(plan, EditorSelectInput.model_validate(inp), expect.get("sites", []))
    checks = [check("코드 검증 통과", not errs, "; ".join(errs)[:200]),
              check("reason 속 값이 입력과 맞음", not mism, "; ".join(mism)[:160])]
    for cid, reason in (expect.get("drops") or {}).items():
        d = next((x for x in out["decisions"] if str(x["cluster_id"]) == str(cid)), None)
        checks.append(check(f"c{cid} drop {reason}", d is not None and d["action"] == "drop" and d["drop_reason"] == reason,
                            str(d)[:120]))
    if "max_topics" in expect:
        checks.append(check("토픽 수 상한 안", len(out["topics"]) <= expect["max_topics"], str(len(out["topics"]))))
    return checks


def aggregate_editor_select(results: list[dict[str, Any]]) -> tuple[dict[str, Any], list[str]]:
    from trendsit.brief.select import reconcile
    from trendsit.core.artifacts_brief import BriefingPlan

    rows = [r for r in results if r.get("output")]
    raw_bad = sum(1 for r in rows if reconcile(BriefingPlan.model_validate(r["output"]))[1])
    return {"decisions·topics 어긋남(원래 출력, 코드가 맞춤)": f"{raw_bad}/{len(rows)}"}, []


graders.ROLE_CHECKS["editor_select"] = code_editor_select
graders.AGGREGATES["editor_select"] = aggregate_editor_select
graders.ROLE_STYLE_FIELDS["editor_select"] = ("log",)
graders.THRESHOLDS["editor_select"] = {"code_pass_all": True}


# ---------- writer_revise(지적된 칸만 바꿈, 이슈 위치를 고침) ----------
def code_writer_revise(inp: dict[str, Any], out: dict[str, Any], expect: dict[str, Any]) -> list[dict[str, Any]]:
    from trendsit.brief.write import top_loc

    flagged = {top_loc(i["loc"]) for i in inp["issues"]}
    locs = [top_loc(c["loc"]) for c in out["changed"]]
    stray = [x for x in locs if x not in flagged and x.split("[")[0] not in {f.split("[")[0] for f in flagged}]
    checks = [check("지적 안 된 칸을 바꾸지 않음", not stray, str(stray)),
              check("지적된 위치를 모두 다룸(또는 attention)", set(flagged) <= set(locs) or out["attention"],
                    f"지적 {sorted(flagged)}, 변경 {locs}")]
    if expect.get("action"):
        acts = {c["action"] for c in out["changed"]}
        checks.append(check(f"기대 동작 {expect['action']}", expect["action"] in acts, str(acts)))
    return checks


def aggregate_writer_revise(results: list[dict[str, Any]]) -> tuple[dict[str, Any], list[str]]:
    rows = [r for r in results if r.get("output")]
    changed = sum(len(r["output"]["changed"]) for r in rows)
    stray = sum(1 for r in rows for c in r["code"]["checks"] if c["name"].startswith("지적 안 된") and not c["passed"])
    return {"지적 안 된 칸 변경(되돌림 전 원래 출력)": f"{stray}/{len(rows)} 픽스처", "변경 수": changed}, []


graders.ROLE_CHECKS["writer_revise"] = code_writer_revise
graders.ROLE_STYLE_FIELDS["writer_revise"] = ("log",)
graders.AGGREGATES["writer_revise"] = aggregate_writer_revise
graders.THRESHOLDS["writer_revise"] = {"code_pass_all": True}
