"""작성자 + 코드 검사 + 검수자 + 작성자 수정 루프(S5_TASK 5.6~5.8).

라운드: 초안(1) → 반려 → 수정(2) → 반려 → 수정(3). 최대 max_rounds, 코드 반려도 셈.
- 코드 검사가 반려하면 그 라운드는 검수자를 부르지 않는다(LLM 0원)
- 같은 이슈(위치 + 유형)가 두 라운드 남으면 그 이슈는 더 돌리지 않고 해당 포인트 check=true로 확정
- 마지막 라운드 뒤 남은 이슈의 포인트는 check=true, 토픽 status=checked
- writer_revise는 고친 칸만 낸다. 지적되지 않은 위치를 바꾸면 코드가 되돌리고 횟수를 센다(되돌림 전 원래 출력도 저장)
대체: writer 실패 → 그 토픽 제외(failed) / critic 실패 → 코드 검사만 통과한 판 + attention / revise 실패 → 이전 판 유지
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from ..core import config
from ..core.artifacts import Document
from ..core.artifacts_brief import (
    AliasLine,
    CriticInput,
    IndexedIssue,
    PlanBrief,
    PreviousTopic,
    Relation,
    ReviewVerdict,
    TopicPage,
    WriterInput,
    WriterLimits,
    WriterReviseInput,
    loc_lines,
)
from ..core.config_brief import BriefConfig
from ..core.context import Ctx
from ..core.db import DB
from ..core.errors import LLMError
from ..core.role import RoleFailed, load_role, run_role
from . import checks
from .aliases import AliasTable, to_original, translit_pattern
from .evidence import EvidenceItem, Member, cap_pack, pack_index
from .revision import LOC, apply_revision, normalize_loc, top_loc
from .select import Applied


@dataclass
class RoundLog:
    round: int
    checker: str  # code / critic
    status: str  # pass / reject
    issues: list[dict[str, Any]]
    autofix: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    step_id: int | None = None
    reverts: int = 0
    fact_support: dict[str, int] | None = None


@dataclass
class TopicResult:
    topic: Applied
    status: str  # passed / checked / failed
    page: TopicPage | None
    pages: list[tuple[int, TopicPage, dict[str, Any] | None, int | None]]  # (round, page, raw, step_id)
    rounds: list[RoundLog]
    evidence_ids: list[str]
    dropped_ids: list[str]
    n_sources: int
    attention: list[str] = field(default_factory=list)
    final_round: int = 0
    costs: dict[str, float] = field(default_factory=dict)
    member_by_id: dict[str, str] = field(default_factory=dict)
    checks: list[str] = field(default_factory=list)  # 이슈가 남은 채 발행된 위치(토픽 수준 확인 필요, 리뷰 R4)
    dropped_diagrams: list[dict[str, Any]] = field(default_factory=list)  # 코드가 뺀 도식과 남은 이슈(반영 확인 리뷰 F2)


# ---------- 입력 조립 ----------
def evidence_docs(pack: dict[str, list[EvidenceItem]]) -> list[Document]:
    """근거 id마다 문서 하나. 글은 quote 문장 + 그 quote의 수치·주장, 영상은 시각의 수치·포인트·라벨, 레포는 필드.
    요약 id(it:{n}, vd:{n})는 CONTRACTS 근거 id가 아니고 원문도 아니라 작성자에게 주지 않는다(리뷰 지적 8).
    글 카드의 주장 줄은 quote와 같은 id에 붙지만 원문이 아니라 카드 요약이라 넣지 않는다(PR #9 리뷰 R2: Haiku "토크나이저 →
    숨겨진 가격 인상"이 주장 줄에서 나옴. "원문 아님" 표시만으로는 재실행에서도 개요에 남음). 수치 줄은 원문에서 뽑은 값이라 둔다."""
    docs = []
    for eid, items in pack.items():
        if all(it.kind == "summary" for it in items):
            continue
        lines = []
        for it in items:
            if it.channel == "text" and it.kind in ("claim", "summary"):
                continue
            v = f" [{it.value}{(' ' + it.unit) if it.unit else ''}]" if it.value else ""
            if it.channel == "text":
                label = {"quote": "원문: ", "number": "(카드 수치, 위 원문에서 뽑음) "}.get(it.kind, "")
            else:
                label = {"claim": "핵심 포인트: ", "slide_fact": "발표 슬라이드 수치: ", "timeline": "구간: ",
                         "repo_field": ""}.get(it.kind, "")
            lines.append(f"{label}{it.text}{v}")
        src = items[0].source
        docs.append(Document(id=eid, source=src.get("site") or items[0].channel, title=src.get("title"),
                             url=src.get("url"), text="\n".join(lines)))
    return docs


def previous_topic(db: DB, topic_id: str | None) -> PreviousTopic | None:
    if not topic_id:
        return None
    r = db.conn.execute(
        "SELECT t.topic_id, t.title, t.summary, p.page_json FROM topics t JOIN weeks w ON w.week=t.week AND "
        "w.current_run_id=t.run_id LEFT JOIN topic_pages p ON p.run_id=t.run_id AND p.topic_id=t.topic_id AND "
        "p.round=t.final_round WHERE t.topic_id=?", (topic_id,)).fetchone()
    if r is None:
        return None
    pts = [p["text"] for p in json.loads(r["page_json"]).get("points", [])] if r["page_json"] else []
    return PreviousTopic(topic_id=r["topic_id"], title=r["title"] or "", summary=r["summary"] or "", points=pts)


def writer_limits(cfg: BriefConfig, n_sources: int) -> WriterLimits:
    w = cfg.write
    return WriterLimits(points=w.points_for(n_sources), overview_sentences=w.overview_sentences,
                        summary_sentences=w.summary_sentences, highlights_page=w.highlights.page,
                        numbers_groups_max=w.diagrams.numbers_groups_max, events_groups_max=w.diagrams.events_groups_max,
                        concepts_max=w.concepts_max)


def alias_lines(table: AliasTable, members: list[Member]) -> list[AliasLine]:
    names = {n for m in members for n in m.entities}
    by: dict[str, list[str]] = {}
    for r in table.rows:
        if r.status == "approved" and r.keyword_id is None and (r.alias in names or r.canonical in names):
            by.setdefault(r.canonical, []).append(r.alias)
    return [AliasLine(canonical=c, aliases=sorted(a)) for c, a in sorted(by.items())]


def raw_evidence(db: DB, eid: str, items: list[EvidenceItem], window_sec: int) -> str:
    """검수자용 근거 원문(요약 칸이 아님): 글 quote 문장, 영상 그 시각 앞뒤 window_sec초 전사와 판독 글자, 레포 필드."""
    if eid.startswith("vd:") and "@" in eid:
        item_id, sec = eid[3:].split("@")
        sec_i = int(sec)
        vid = db.conn.execute("SELECT video_id FROM videos WHERE item_id=?", (int(item_id),)).fetchone()
        parts = []
        if vid:
            segs = db.conn.execute('SELECT text FROM video_segments WHERE video_id=? AND "end">=? AND start<=? ORDER BY idx',
                                   (vid["video_id"], sec_i - window_sec, sec_i + window_sec)).fetchall()
            if any(s["text"] for s in segs):
                parts.append(f"전사(앞뒤 {window_sec}초): " + " ".join(s["text"] for s in segs if s["text"]))
            fr = db.conn.execute("SELECT reading_json FROM video_frames WHERE video_id=? ORDER BY ABS(t-?) LIMIT 1",
                                 (vid["video_id"], sec_i)).fetchone()
            if fr and fr["reading_json"]:
                ocr = json.loads(fr["reading_json"]).get("ocr_text") or ""
                if ocr:
                    parts.append("화면 판독: " + ocr)
        parts += [f"{it.text} {it.value or ''}{it.unit or ''}".strip() for it in items if it.kind == "slide_fact"]
        # 작성자에게 준 영상 핵심 포인트·구간 이름도 검수·judge 입력에(반영 확인 리뷰 3차 질문 2: LlamaIndex "ParseBench
        # 3가지 처리 영역"은 vd:274@816 핵심 포인트에 있었으나 앞뒤 30초 전사에 없어 근거 밖으로 판정됨)
        parts += [f"영상 핵심 포인트: {it.text}" for it in items if it.kind == "claim"]
        parts += [f"영상 구간: {it.text}" for it in items if it.kind == "timeline"]
        return "\n".join(parts)
    quotes = [it.text for it in items if it.kind in ("quote", "repo_field")]
    if quotes:
        return "\n".join(quotes + [f"{it.text}: {it.value}{it.unit or ''}" for it in items if it.kind == "repo_field" and it.value])
    # 요약 id(it:{n}, vd:{n})는 원문이 아니다(리뷰 R1). 그 밖(영상 구간 등 원문 없는 칸)은 그 글자
    return "\n".join(it.text for it in items if it.kind != "summary")


def refs_of(page: TopicPage) -> list[str]:
    order = ("point", "number", "event", "contribution", "context")  # 칸 종류 순(같은 종류는 페이지 순서)
    slots = sorted(checks.page_refs(page), key=lambda s: order.index(s[2]))
    return list(dict.fromkeys(r for *_, refs in slots for r in refs))


# ---------- 루프 ----------
def _call(role: Any, inp: Any, ctx: Ctx, costs: dict[str, float], key: str) -> tuple[Any | None, str | None, int | None]:
    """역할 1회. 실패는 (None, 이유). 사용액은 이 호출 동안 늘어난 session_cost로 역할별 합산."""
    before = ctx.budget.session_cost
    try:
        out, err = run_role(role, inp, ctx), None
    except (RoleFailed, LLMError) as e:
        out, err = None, f"{type(e).__name__}: {e}"[:300]
    costs[key] = round(costs.get(key, 0) + ctx.budget.session_cost - before, 6)
    return out, err, ctx.last_step_id


def _canon_translit(table: AliasTable, ms: list[Member], cfg: BriefConfig) -> tuple[dict[str, str], list[tuple[re.Pattern[str], str]]]:
    """코드가 고칠 정본 표기: 별칭 → 정본, 이 토픽 이름의 한글 음차 표기(GPT-6 루나, 딥시크-V4.1 플래시)도 정본으로(리뷰 R11, F10).
    근거가 모두 한글 음차뿐인 이름(클로드 소네트 5.5)도 사전으로 되돌린 영문 표기가 정본."""
    tl = cfg.aliases.transliteration
    translit = []
    for name in sorted({n for m in ms for n in m.entities if n.strip()}):
        target = to_original(table.canonical(name), tl)
        if (pat := translit_pattern(target, tl)) is not None:
            translit.append((pat, target))
    return {a: c.canonical for c in alias_lines(table, ms) for a in c.aliases}, translit


def _run_critic(ctx: Ctx, res: TopicResult, topic: Applied, winp: WriterInput, pack: dict[str, list[EvidenceItem]],
                pg: TopicPage, rnd: int, warns: list[str]) -> tuple[Any, str | None, int | None]:
    """refs 근거를 앞에, 나머지 토픽 근거를 뒤에(근거 원문). overview·summary·title은 토픽 근거 전체가 기준이다."""
    # 요약만 있는 id(카드 summary)는 원문이 아니라 빼고 준다(리뷰 R1: 요약·개요가 요약과 대조되던 문제)
    raw_ids = [e for e in pack if not all(it.kind == "summary" for it in pack[e])]
    order = [e for e in refs_of(pg) if e in raw_ids] + [e for e in raw_ids if e not in refs_of(pg)]
    window_sec = config.load("video.yaml").align_window_sec
    evid = [Document(id=e, source=pack[e][0].source.get("site") or pack[e][0].channel,
                     title=pack[e][0].source.get("title"), text=raw_evidence(ctx.db, e, pack[e], window_sec)) for e in order]
    cinp = CriticInput(loc_lines=loc_lines(pg), page=pg, evidence=evid, angle=topic.angle, previous=winp.previous,
                       code_warnings=warns, round=rnd)
    critic = load_role("critic", ctx.models)
    out = _call(critic, cinp, ctx, res.costs, "critic")
    # 원자 사실 0개로 통과 = 대조를 건너뛴 판정(W40 재실행 3토픽, 출력 49토큰). 한 번 다시 부르고, 또 비면 검수 실패
    if out[0] is not None and not out[0].atoms and pg.points:
        res.attention.append("검수자가 원자 사실 0개로 판정(대조 건너뜀), 다시 부름")
        again = cinp.model_copy(update={"code_warnings": [*warns, "직전 판정이 원자 사실 0개: 모든 문장을 원자 사실로 나눠 대조"]})
        out = _call(critic, again, ctx, res.costs, "critic")
        if out[0] is not None and not out[0].atoms:
            out = (None, "원자 사실 0개 판정 반복", out[2])
    return out


def _critic_log(rnd: int, v: ReviewVerdict, step_id: int | None) -> RoundLog:
    return RoundLog(rnd, "critic", v.status, [i.model_dump() for i in v.issues], step_id=step_id,
                    fact_support=v.fact_support.model_dump())


def _live_issues(issues: list[Any], seen: dict[tuple[str, str], int], check_locs: set[str], repeat: int) -> list[Any]:
    """같은 위치·같은 유형이 두 번 남으면 확정(check) 후 제외. 라운드 사이 반복만 센다(같은 라운드 안의 중복 이슈는 한 번으로, 리뷰 지적 1)."""
    for key in dict.fromkeys((top_loc(it.loc), it.type) for it in issues):
        seen[key] = seen.get(key, 0) + 1
    live = []
    for it in issues:
        key = (top_loc(it.loc), it.type)
        if seen[key] >= repeat:
            check_locs.add(key[0])
        else:
            live.append(it)
    return live


def _revise(ctx: Ctx, res: TopicResult, reviser: Any, aliases: list[AliasLine], page: TopicPage, live: list[Any],
            flagged: set[str], pack: dict[str, list[EvidenceItem]]) -> tuple[TopicPage, dict[str, Any], int | None] | None:
    """지적된 칸만 고친 새 판과 그 원래 출력·step_id. 수정 호출이 실패하면 None."""
    ids = {x.evidence_id for x in live} | {r for loc in flagged for r in _loc_refs(page, loc)}
    rinp = WriterReviseInput(loc_lines=loc_lines(page), previous=page,
                             issues=[IndexedIssue(idx=i, **x.model_dump()) for i, x in enumerate(live)],
                             evidence=evidence_docs({k: v for k, v in pack.items() if k in ids}), aliases=aliases)
    rev, err, rsid = _call(reviser, rinp, ctx, res.costs, "writer_revise")
    if rev is None:
        res.attention.append(f"수정 실패: {err}")
        return None
    new, reverts, notes = apply_revision(page, rev, flagged)
    res.rounds[-1].reverts = reverts
    res.attention += notes[:3]
    return new, rev.model_dump(), rsid


def _rounds(ctx: Ctx, res: TopicResult, topic: Applied, winp: WriterInput, pack: dict[str, list[EvidenceItem]],
            cfg: BriefConfig, fixers: tuple[Any, Any], page: TopicPage, sid: int | None,
            review: bool) -> tuple[TopicPage, set[str], dict[str, str]]:
    """초안 → 코드 검사 → 검수 → 수정을 max_rounds까지. 반환: (마지막 판, 확인 필요 위치, 위치별 마지막 이슈)."""
    seen: dict[tuple[str, str], int] = {}
    check_locs: set[str] = set()
    last_issue: dict[str, str] = {}  # 위치 → 마지막 이슈 원문(뺀 도식 표)
    reviser = load_role("writer_revise", ctx.models)
    raw_page: dict[str, Any] | None = page.raw_dump()
    for rnd in range(1, cfg.review.max_rounds + 1):
        cr = checks.run_checks(page, pack, res.n_sources, cfg, *fixers)
        page = cr.page
        res.pages.append((rnd, page, raw_page, sid))
        issues = cr.issues
        log = RoundLog(rnd, "code", "reject" if issues else "pass", [i.model_dump() for i in issues], cr.autofix, cr.warnings, sid)
        if not issues and review:
            res.rounds.append(log)
            verdict, err, vsid = _run_critic(ctx, res, topic, winp, pack, page, rnd, cr.warnings)
            if verdict is None:  # 검수 실패: 코드 검사만 통과한 판 + attention(검수 판정은 기록하지 않음)
                res.attention.append(f"검수 실패: {err}")
                res.status, res.page, res.final_round = "passed", page, rnd
                break
            log = _critic_log(rnd, verdict, vsid)
            issues = verdict.issues if verdict.status == "reject" else []
        res.rounds.append(log)
        if not issues:
            res.status, res.page, res.final_round = "passed", page, rnd
            break
        # 위치 번호를 1부터 센 이슈는 0부터로(검수자가 contributions[2]로 두 번째 항목을 가리킨 사례)
        issues = [i.model_copy(update={"loc": normalize_loc(page, i.loc)}) for i in issues]
        last_issue |= {top_loc(it.loc): f"{log.checker} {it.type}: {it.comment}" for it in issues}
        live = _live_issues(issues, seen, check_locs, cfg.review.same_issue_repeat_to_check)
        flagged = {top_loc(i.loc) for i in live}
        revised = None if rnd == cfg.review.max_rounds or not live else _revise(ctx, res, reviser, winp.aliases, page, live,
                                                                               flagged, pack)
        if revised is None:
            check_locs |= flagged
            res.final_round = rnd
            break
        page, raw_page, sid = revised
    else:
        res.final_round = cfg.review.max_rounds
    return page, check_locs, last_issue


def _critic_unseen_pages(ctx: Ctx, res: TopicResult, topic: Applied, winp: WriterInput, pack: dict[str, list[EvidenceItem]],
                         final: TopicPage, check_locs: set[str], cfg: BriefConfig) -> None:
    """코드 반려만 이어져 검수자가 한 번도 보지 않고 끝난 판(리뷰 지적 2): 발행 전 한 번 검수, 이슈 위치는 check."""
    rnd = res.final_round or cfg.review.max_rounds
    verdict, _err, vsid = _run_critic(ctx, res, topic, winp, pack, final, rnd, [])
    if verdict is not None:
        res.rounds.append(_critic_log(rnd, verdict, vsid))
        if verdict.status == "reject":
            check_locs |= {top_loc(normalize_loc(final, i.loc)) for i in verdict.issues}


def _drop_code_bad_diagrams(res: TopicResult, final: TopicPage, pack: dict[str, list[EvidenceItem]], cfg: BriefConfig,
                            last_issue: dict[str, str], check_locs: set[str]) -> tuple[TopicPage, dict[str, str]]:
    """도식을 빼는 것은 코드가 최종판에서 확인한 형식·수치 오류(단위 섞임, 값 불일치, 빈 단위)일 때만(반영 확인 리뷰 F2: 검수자의
    의미 지적만 남은 맞는 도식까지 지워 Haiku 구간 가격·textGrain 탐지율이 빠졌음). 의미 지적만 남으면 두고 ⚠.
    반환: (도식을 뺀 판, 위치 → 뺀 뒤의 위치 이름)."""
    code_bad = {(m.group(1), int(m.group(2))) for i in checks.check(final, pack, res.n_sources, cfg)
                if (m := re.match(r"^(numbers|events)\[(\d+)\]", i.loc))}
    renamed: dict[str, str] = {}
    upd: dict[str, Any] = {}
    for name in ("numbers", "events") if code_bad else ():
        keep = []
        for i, g in enumerate(getattr(final, name)):
            loc = f"{name}[{i}]"
            if (name, i) in code_bad:
                renamed[loc] = f"빠진 도식: {g.title}"
                res.dropped_diagrams.append({"group": loc, "title": g.title, "issue": last_issue.get(loc, "")})
                check_locs.add(loc)
            else:
                renamed[loc] = f"{name}[{len(keep)}]"
                keep.append(g)
        if len(keep) != len(getattr(final, name)):
            upd[name] = keep
            res.attention.append(f"형식·수치 오류가 남은 {name} 도식 {len(getattr(final, name)) - len(keep)}개 뺌")
    return (final.model_copy(update=upd) if upd else final), renamed


def write_topic(ctx: Ctx, topic: Applied, members: dict[str, Member], table: AliasTable, cfg: BriefConfig,
                review: bool = True, draft: TopicPage | None = None) -> TopicResult:
    """draft를 주면 작성자를 부르지 않고 그 초안부터 검사·검수(--from-step review)."""
    ms = [members[k] for k in topic.members if k in members]
    kept, dropped = cap_pack(ms, cfg.evidence.max_tokens_per_topic)
    pack = pack_index(kept)
    n_sources = len({it.member for it in kept})
    res = TopicResult(topic, "failed", None, [], [], list(pack), dropped, n_sources, costs={},
                      member_by_id={i: v[0].member for i, v in pack.items()})
    if not pack:
        res.attention.append("근거 없음")
        return res
    winp = WriterInput(plan=PlanBrief(rank=topic.rank, angle=topic.angle,
                                      relation=Relation(type=topic.relation_type, topic_id=topic.relation_topic_id)),
                       evidence=evidence_docs(pack), previous=previous_topic(ctx.db, topic.relation_topic_id),
                       aliases=alias_lines(table, ms), limits=writer_limits(cfg, n_sources))
    if draft is not None:  # check는 코드 소유: 이어 온 초안의 옛 true가 중간 라운드 저장·검수자 입력에 남지 않게
        draft = draft.model_copy(update={"points": [p.model_copy(update={"check": False}) for p in draft.points]})
    page, err, sid = (draft, None, None) if draft is not None else _call(load_role("writer", ctx.models), winp, ctx, res.costs, "writer")
    if page is None or not page.points:
        res.attention.append(f"작성 실패: {err or '포인트 없음'}")
        ctx.tracer.step(kind="code", role="writer", text=f"{topic.topic_id}: 작성 실패", attention=True, error=err)
        return res
    page, check_locs, last_issue = _rounds(ctx, res, topic, winp, pack, cfg, _canon_translit(table, ms, cfg), page, sid, review)
    final = res.page or page
    if review and not any(lg.checker == "critic" for lg in res.rounds) and res.status != "passed":
        _critic_unseen_pages(ctx, res, topic, winp, pack, final, check_locs, cfg)
    final, renamed = _drop_code_bad_diagrams(res, final, pack, cfg, last_issue, check_locs)
    pts = [p.model_copy(update={"check": f"points[{i}]" in check_locs}) for i, p in enumerate(final.points)]
    final = final.model_copy(update={"points": pts})  # check는 코드 소유: 이어 온 초안의 옛 true도 여기서 덮어씀
    if check_locs:
        # ⚠가 빠진 도식을 가리키면 "빠진 도식: 제목", 남은 도식은 뺀 뒤의 번호로
        res.checks = sorted({renamed.get(loc, loc) for loc in check_locs})
        res.status = "checked"
    elif res.status != "passed":
        res.status = "checked"
    res.page = final
    if res.pages and res.pages[-1][1] != final:
        res.pages.append((res.final_round, final, None, None))
    return res


def _loc_refs(page: TopicPage, loc: str) -> list[str]:
    m = LOC.match(loc)
    if not m or m.group(1):
        return refs_of(page)
    name, idx = m.group(2), int(m.group(3))
    return [r for n, i, _f, refs in checks.page_refs(page) if (n, i) == (name, idx) for r in refs]


# ---------- 저장 ----------
def save(db: DB, res: TopicResult, run_id: str) -> None:
    t = res.topic
    with db.conn:
        seen_rounds = set()
        for rnd, page, raw, step_id in res.pages:
            if rnd in seen_rounds:  # 같은 라운드의 최종판(check 표시)은 마지막 것으로
                db.conn.execute("UPDATE topic_pages SET page_json=? WHERE run_id=? AND topic_id=? AND round=?",
                                (page.model_dump_json(), run_id, t.topic_id, rnd))
                continue
            seen_rounds.add(rnd)
            db.conn.execute("INSERT INTO topic_pages(run_id, topic_id, round, page_json, raw_json, step_id) VALUES (?,?,?,?,?,?)",
                            (run_id, t.topic_id, rnd, page.model_dump_json(),
                             json.dumps(raw, ensure_ascii=False) if raw else None, step_id))
        for lg in res.rounds:
            db.conn.execute(
                "INSERT INTO verdicts(run_id, topic_id, round, checker, status, issues_json, autofix_json, step_id) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (run_id, t.topic_id, lg.round, lg.checker, lg.status, json.dumps(lg.issues, ensure_ascii=False),
                 json.dumps({"autofix": lg.autofix, "warnings": lg.warnings, "reverts": lg.reverts,
                             "fact_support": lg.fact_support}, ensure_ascii=False), lg.step_id))
        page = res.page
        if page is not None and res.status != "failed":
            db.conn.executemany(
                "INSERT INTO topic_evidence(run_id, topic_id, evidence_id, member, field, idx) VALUES (?,?,?,?,?,?)",
                [(run_id, t.topic_id, eid, res.member_by_id.get(eid, eid), f, i)
                 for _n, i, f, refs in checks.page_refs(page) for eid in refs])
        db.conn.execute("UPDATE topics SET status=?, final_round=?, title=?, summary=?, checks_json=? "
                        "WHERE run_id=? AND topic_id=?",
                        (res.status, res.final_round, page.title if page else None, page.summary if page else None,
                         json.dumps(res.checks, ensure_ascii=False), run_id, t.topic_id))

