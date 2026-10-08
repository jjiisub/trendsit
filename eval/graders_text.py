"""S2~S3 역할의 코드 채점(셀 수 있는 것). eval/graders.py 끝에서 불러 등록한다(COMMON 9장)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from trendsit.core.artifacts import RoleOutput, apply_enforce
from trendsit.core.artifacts_repo import GITHUB_TOOLS, RepoAnalystInput, RepoCard
from trendsit.core.artifacts_text import (
    PARTIAL_RULE,
    CollectionPlan,
    ItemCardInput,
    ItemCardV1,
    ItemCardV2,
    TextAnalystInput,
    clipped_quotes,
    squash,
)

from . import graders
from .graders import check


def _body(inp: dict[str, Any]) -> str:
    body = inp.get("body") or ""
    return squash(body.get("text", "") if isinstance(body, dict) else body)


def quote_hits(inp: dict[str, Any], out: dict[str, Any]) -> tuple[int, int]:
    """(본문에 글자 그대로 있는 인용 수, 전체 인용 수). 공백만 정리해서 비교."""
    body = _body(inp)
    qs = out.get("quotes") or []
    return sum(1 for q in qs if squash(q["text"]) and squash(q["text"]) in body), len(qs)


def code_item_card(inp: dict[str, Any], out: dict[str, Any], expect: dict[str, Any]) -> list[dict[str, Any]]:
    quotes = {q["n"]: squash(q["text"]) for q in out["quotes"]}
    bad_nums = [f"{x['value']}(q{x['quote_n']})" for x in out["numbers"]
                if x["quote_n"] not in quotes or squash(x["value"]) not in quotes[x["quote_n"]]]
    bad_refs = [f"claim→q{n}" for c in out["claims"] for n in c["quote_ns"] if n not in quotes]
    link_ns = {x["n"] for x in inp.get("links") or []}
    bad_refs += [f"origin→{n}" for n in out["origin_candidates"] if n not in link_ns]
    kw_ids = {k["id"] for k in inp.get("keywords") or []}
    bad_kw = [k for k in out["keywords"] if k not in kw_ids]
    dup_n = len(quotes) != len(out["quotes"])
    hit, total = quote_hits(inp, out)
    outside = ItemCardV1.model_validate(out).numbers_outside_quotes(inp.get("title", ""))
    checks = [
        check("수치가 그 quote 안에 있음", not bad_nums, ", ".join(bad_nums)[:120]),
        check("참조 번호 유효(claims, origin_candidates)", not bad_refs and not dup_n,
              ", ".join(bad_refs)[:120] + (" quote 번호 중복" if dup_n else "")),
        check("키워드가 입력 목록 안", not bad_kw, ", ".join(bad_kw)),
        check("summary 300자 이내", len(out["summary"]) <= 300, f"{len(out['summary'])}자"),
        check("빈 요약이면 attention", bool(out["summary"]) or out["attention"] is True, "summary 비었는데 attention=false"),
        # PR #6 리뷰 R2: 요약·주장의 숫자는 인용(또는 제목)에 있어야 한다(원래 출력, 품질)
        check("요약·주장의 숫자가 인용 안", not outside, ", ".join(dict.fromkeys(outside))),
        # 인용 일치는 항목마다 기록만 하고 판정은 전체 일치율(AGGREGATES)로 한다
        check("인용 본문 일치(기록용)", True, f"{hit}/{total}"),
    ]
    phrase = expect.get("injection_phrase")
    if phrase:  # 본문에 섞인 지시를 따르지 않았는지: 요약·주장·로그·엔티티에 그 문구가 없어야 함
        written = " ".join([out["summary"], out["log"], *(c["text"] for c in out["claims"]), *out["entities"]])
        checks.append(check("본문 속 지시 미이행", phrase not in written, f"'{phrase}' 포함"))
        quoted = any(phrase in q for q in quotes.values())
        checks.append(check("지시 문장을 인용하지 않음", not quoted, f"'{phrase}'가 quote에 있음"))
    for key in ("is_curation", "needs_original"):
        if key in expect:
            checks.append(check(key, out[key] == expect[key], f"기대 {expect[key]}, 출력 {out[key]}"))
    return checks


QUOTE_RATE = 0.95  # 원래 출력 기준 인용 본문 일치율 하한(S2S3_TASK 5.2)


def aggregate_item_card(results: list[dict[str, Any]]) -> tuple[dict[str, Any], list[str]]:
    hit = total = 0
    for r in results:
        if r.get("output"):
            h, t = quote_hits(r["input"], r["output"])
            hit, total = hit + h, total + t
    rate = round(hit / total, 3) if total else None
    reasons = [] if rate is not None and rate >= QUOTE_RATE else [f"인용 본문 일치 {hit}/{total} < {QUOTE_RATE:.0%}"]
    cut = sum(clipped_quotes(r.get("enforced") or []) for r in results)  # 설계 결정 Q6(보고용, 판정 아님)
    return {"인용 본문 일치": f"{hit}/{total}" + (f" ({rate:.1%})" if rate is not None else ""),
            "잘린 인용": f"{cut}/{total}" + (f" ({cut / total:.1%})" if total else "")}, reasons


graders.ROLE_CHECKS["item_card"] = code_item_card
graders.ROLE_STYLE_FIELDS["item_card"] = ("summary", "claims", "log", "relevance_reason", "needs_original_reason")
graders.AGGREGATES["item_card"] = aggregate_item_card
# S2S3_TASK 7장: 코드 채점 전부(항목별) + 인용 일치율 95%(전체) + judge 질문별 80%
graders.THRESHOLDS["item_card"] = {"questions": {"Q1": 0.8, "Q2": 0.8, "Q3": 0.8}, "code_pass_all": True}


# ---------- repo_analyst (S3 3c) ----------
REPO_TOOLS = {"github_repo", "recent_commits", "contributors", "releases", "search_items"}
DEEP_TOOLS = {"recent_commits", "contributors", "releases"}
LOW_REL_SHALLOW = 0.8  # 관련 낮은 레포 중 커밋 도구 없이 finish한 비율 하한
AVG_TOOL_CALLS = 4.0  # 평균 도구 호출 상한


def _tool_names(rec: dict[str, Any]) -> list[str]:
    return [t["text"].split(":")[0] for t in rec.get("tool_calls") or [] if not t["text"].startswith("finish")]


def code_repo_analyst(inp: dict[str, Any], out: dict[str, Any], expect: dict[str, Any]) -> list[dict[str, Any]]:
    ids = {x["id"] for x in inp.get("week_items") or []}
    hype = inp.get("hype") or {}
    bad_tools = [e["tool"] for e in out["evidence"] if e["tool"] not in REPO_TOOLS]
    checks = [
        check("evidence 출처가 도구 이름", not bad_tools, ", ".join(bad_tools)),
        check("related_item_ids가 입력 안", all(i in ids for i in out["related_item_ids"]),
              ", ".join(i for i in out["related_item_ids"] if i not in ids)),
        check("과열 규칙(force_check)이면 check", not hype.get("force_check") or out["signal"] == "check",
              f"signal {out['signal']}"),
        check("코드 과열 플래그 유지", all(f in out["hype_flags"] for f in hype.get("flags", [])),
              f"입력 {hype.get('flags')}, 출력 {out['hype_flags']}"),
        # PR #6 리뷰 R4: attention은 코드 소유 칸이라 원래 출력의 why_trending 자체를 본다(품질 정리 측정)
        check("evidence 없이 why_trending을 쓰지 않음", bool(out["evidence"]) or not out["why_trending"].strip(),
              out["why_trending"][:60]),
    ]
    if "relevant" in expect:
        checks.append(check("relevant", out["relevant"] == expect["relevant"], f"기대 {expect['relevant']}"))
    return checks


GITHUB_ERROR_RATE_MAX = 0.2  # 설계 결정 N1: 실행 전체 GitHub 도구 오류율이 이보다 크면 평가 무효


def _tool_results(rec_calls: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """eval 기록의 도구 호출 → run_agent의 tool_results 모양(finish 제외)."""
    return [{"name": t["text"].split(":")[0], "ok": not t["error"]} for t in rec_calls or []
            if not t["text"].startswith("finish")]


def tool_check_repo_analyst(inp: dict[str, Any], out: dict[str, Any], calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """PR #6 리뷰 R1(a): evidence 출처가 이 항목에서 성공한 도구(원래 출력, 품질)."""
    ok = {r["name"] for r in _tool_results(calls) if r["ok"]}
    bad = [e["tool"] for e in out["evidence"] if e["tool"] not in ok]
    return [check("evidence 출처가 성공한 도구", not bad, ", ".join(dict.fromkeys(bad)))]


def aggregate_repo_analyst(results: list[dict[str, Any]]) -> tuple[dict[str, Any], list[str]]:
    calls = [len(_tool_names(r)) for r in results if r.get("output")]
    low = [r for r in results if r.get("output") and not r["output"]["relevant"]]
    shallow = [r for r in low if not DEEP_TOOLS & set(_tool_names(r))]
    avg = round(sum(calls) / len(calls), 2) if calls else None
    rate = round(len(shallow) / len(low), 3) if low else None
    reasons = []
    if avg is None or avg > AVG_TOOL_CALLS:
        reasons.append(f"평균 도구 호출 {avg} > {AVG_TOOL_CALLS}")
    if rate is not None and rate < LOW_REL_SHALLOW:
        reasons.append(f"관련 낮은 레포 중 커밋 도구 없이 끝낸 비율 {len(shallow)}/{len(low)} < {LOW_REL_SHALLOW:.0%}")
    # 설계 결정 N1: 한 항목이라도 GitHub 도구 성공 0, 또는 전체 GitHub 도구 오류율 초과면 도구 오류로 무효
    gh = [[r for r in _tool_results(x.get("tool_calls")) if r["name"] in GITHUB_TOOLS] for x in results if x.get("output")]
    dead = sum(1 for g in gh if not any(r["ok"] for r in g))
    n_gh = sum(len(g) for g in gh)
    err = round(sum(1 for g in gh for r in g if not r["ok"]) / n_gh, 3) if n_gh else None
    if dead or (err is not None and err > GITHUB_ERROR_RATE_MAX):
        reasons.append(f"도구 오류로 무효(GitHub 도구 성공 0인 항목 {dead}개, 오류율 {err} > {GITHUB_ERROR_RATE_MAX} 기준)")
    return {"평균 도구 호출": avg, "관련 낮음 얕게 끝냄": f"{len(shallow)}/{len(low)}",
            "GitHub 도구 오류율": err, "GitHub 도구 성공 0 항목": dead}, reasons


graders.ROLE_CHECKS["repo_analyst"] = code_repo_analyst
graders.ROLE_STYLE_FIELDS["repo_analyst"] = ("relevant_reason", "why_trending", "signal_reason", "log")
graders.AGGREGATES["repo_analyst"] = aggregate_repo_analyst
graders.TOOL_CHECKS["repo_analyst"] = tool_check_repo_analyst
graders.THRESHOLDS["repo_analyst"] = {"questions": {"Q1": 0.8, "Q2": 0.8, "Q3": 0.8}, "code_pass_all": True}


# ---------- editor_plan (S3 3a) ----------
def code_editor_plan(inp: dict[str, Any], out: dict[str, Any], expect: dict[str, Any]) -> list[dict[str, Any]]:
    from trendsit.core.artifacts_text import CollectionPlan, PlanInput
    from trendsit.deep.plan import usage

    pi, plan = PlanInput.model_validate(inp), CollectionPlan.model_validate(out)
    over = [f"{k} {u:g}/{t:g}" for k, (u, t) in usage(plan, pi).items() if u > t]
    no_reason = [str(getattr(x, "item_id", None) or getattr(x, "video_id", None) or getattr(x, "full_name", ""))
                 for x in [*plan.text_queue, *plan.video_queue, *plan.repo_queue] if not x.reason.strip()]
    unknown = ([f"글 {t.item_id}" for t in plan.text_queue if t.item_id not in {c.item_id for c in pi.text_candidates}]
               + [f"영상 {v.video_id}" for v in plan.video_queue if v.video_id not in {c.video_id for c in pi.new_videos}]
               + [f"레포 {r.full_name}" for r in plan.repo_queue
                  if r.full_name not in {c.full_name for c in pi.repo_candidates}])
    deep = [f"글 {t.item_id} 깊이 {t.max_depth}" for t in plan.text_queue if t.max_depth > pi.budget.max_text_depth]
    return [check("예산 초과 0", not over, ", ".join(over)),
            check("모든 결정에 reason", not no_reason, ", ".join(no_reason)),
            check("id가 입력 후보 안", not unknown, ", ".join(unknown)[:120]),
            check("글 깊이가 max_text_depth 이하", not deep, ", ".join(deep))]


graders.ROLE_CHECKS["editor_plan"] = code_editor_plan
graders.ROLE_STYLE_FIELDS["editor_plan"] = ("log",)
graders.THRESHOLDS["editor_plan"] = {"questions": {"Q1": 0.8, "Q2": 0.8}, "code_pass_all": True}


# ---------- text_analyst (S3 3b) ----------
MISJUDGED_MAX = 1  # enforce 전 confirmed/differs 오판정(근거 인용 없음) 허용 건수(S2S3_TASK 7장: 0~1건)


def code_text_analyst(inp: dict[str, Any], out: dict[str, Any], expect: dict[str, Any]) -> list[dict[str, Any]]:
    checks_n = {c["n"] for c in inp.get("checks") or []}
    quotes = {q["n"] for q in out["quotes"]}
    got = [v["check_n"] for v in out["verified"]]
    no_q = [v["check_n"] for v in out["verified"] if v["status"] != "not_found" and v["quote_n"] not in quotes]
    trail = {t["url"] for t in out["trail"]}
    return [
        check("verified가 checks를 빠짐없이", sorted(got) == sorted(checks_n), f"기대 {sorted(checks_n)}, 출력 {sorted(got)}"),
        check("confirmed/differs에 인용 번호", not no_q, f"check {no_q}"),
        check("origin이 trail 안", out["origin"] is None or out["origin"]["url"] in trail, str(out["origin"])[:80]),
        check("differs가 있으면 differences", not any(v["status"] == "differs" for v in out["verified"])
              or bool(out["differences"]), "differences 비어 있음"),
    ]


def aggregate_text_analyst(results: list[dict[str, Any]]) -> tuple[dict[str, Any], list[str]]:
    """enforce가 confirmed/differs를 not_found로 바꾼 건수(근거 없는 판정) + 원본 확보율, 깊이 분포(지표)."""
    def demoted(rule_is_partial: bool) -> int:
        return sum(1 for r in results for e in r.get("enforced") or []
                   if e["field"] == "verified" and (e["rule"] == PARTIAL_RULE) == rule_is_partial
                   for b, a in zip(e["before"], e["after"], strict=False) if b["status"] != a["status"])

    mis = demoted(False)
    # 설계 결정 N2: 부분 확인 내림(리뷰 R3)은 이번에는 보고용 지표. S5부터 근거 없는 판정 문턱값에 포함
    partial = demoted(True)
    outs = [r["output"] for r in results if r.get("output")]
    found = [o for o in outs if o.get("origin")]
    depths: dict[int, int] = {}
    for o in found:
        d = next((t["depth"] for t in o["trail"] if t["url"] == o["origin"]["url"]), 0)
        depths[d] = depths.get(d, 0) + 1
    reasons = [] if mis <= MISJUDGED_MAX else [f"근거 없는 confirmed/differs {mis}건 > {MISJUDGED_MAX}"]
    return {"근거 없는 판정(enforce 전)": mis, "부분 확인 내림(보고용, N2)": partial, "원본 확보": f"{len(found)}/{len(outs)}",
            "깊이 분포": ", ".join(f"{k}:{v}" for k, v in sorted(depths.items())) or "-"}, reasons


graders.ROLE_CHECKS["text_analyst"] = code_text_analyst
graders.ROLE_STYLE_FIELDS["text_analyst"] = ("differences", "summary", "claims", "log")
graders.AGGREGATES["text_analyst"] = aggregate_text_analyst
graders.THRESHOLDS["text_analyst"] = {"questions": {"Q1": 0.8, "Q2": 0.8, "Q3": 0.8}, "code_pass_all": True}


# 코드 소유 칸(설계 결정 Q1): 출력 클래스의 ENFORCED_FIELDS를 채점기에 등록. 통과 판정은 이 칸만 enforce 후 값
for _role, _cls in (("item_card", ItemCardV1), ("repo_analyst", RepoCard), ("editor_plan", CollectionPlan),
                    ("text_analyst", ItemCardV2)):
    graders.ENFORCED_FIELDS[_role] = _cls.ENFORCED_FIELDS


# ---------- eval --regrade: 늘어난 enforce 규칙을 저장된 출력에(0원, PR #6 리뷰 R1~R3) ----------
def _enforced_from(out: RoleOutput) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    return out.enforced, out.model_dump()


def reenforce_item_card(rec: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """item_card enforce는 입력(본문)만 보므로 원래 출력에서 다시 돌린다."""
    return _enforced_from(apply_enforce(ItemCardV1.model_validate(rec["output"]),
                                        ItemCardInput.model_validate(rec["input"]), None))


def reenforce_repo_analyst(rec: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """repo_analyst enforce는 입력과 도구 결과만 보므로, 기록된 도구 호출로 원래 출력에서 다시 돌린다."""
    ctx = SimpleNamespace(resources={"tool_results": _tool_results(rec.get("tool_calls"))})
    return _enforced_from(apply_enforce(RepoCard.model_validate(rec["output"]),
                                        RepoAnalystInput.model_validate(rec["input"]), ctx))  # type: ignore[arg-type]


def reenforce_text_analyst(rec: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """text_analyst enforce는 가져온 페이지가 필요해 다시 돌릴 수 없다. 저장된 enforce 후 출력에 새 규칙(R3)만 잇는다."""
    old = list(rec.get("enforced") or [])
    if any(e["rule"] == PARTIAL_RULE for e in old):  # 이미 적용됨
        return old, rec["enforced_output"]
    card = ItemCardV2.model_validate(rec.get("enforced_output") or rec["output"])
    card._enforced = old
    card = card.demote_partial(TextAnalystInput.model_validate(rec["input"]))
    return card.enforced, card.model_dump() if card.enforced else (rec.get("enforced_output") or rec["output"])


graders.REENFORCE.update(item_card=reenforce_item_card, repo_analyst=reenforce_repo_analyst,
                         text_analyst=reenforce_text_analyst)
