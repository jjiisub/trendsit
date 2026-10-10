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
    Concept,
    Contribution,
    CriticInput,
    EventGroup,
    EventItem,
    IndexedIssue,
    NumberGroup,
    NumberItem,
    PlanBrief,
    Point,
    PreviousTopic,
    Relation,
    ReviewVerdict,
    TopicPage,
    TopicPageRevision,
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
from .select import Applied

LOC = re.compile(r"^(title|summary|overview)$|^(points|numbers|events|contributions|concepts)\[(\d+)\]")
LIST_LOC = re.compile(r"^(points|numbers|events|contributions|concepts)$")
SUB_LOC = re.compile(r"^(numbers|events)\[(\d+)\]\.(items|context|title|unit)(?:\[(\d+)\])?$")
FIELD_TYPES: dict[str, type] = {"points": Point, "numbers": NumberGroup, "events": EventGroup,
                                "contributions": Contribution, "concepts": Concept}


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


# ---------- 수정 합치기 ----------
def top_loc(loc: str) -> str:
    m = LOC.match(loc.strip())
    if not m:
        return loc.strip()
    return m.group(1) or f"{m.group(2)}[{m.group(3)}]"


def normalize_loc(page: TopicPage, loc: str) -> str:
    """모델이 위치를 1부터 세면(마지막 다음 번호, 예: 항목 2개인데 [2]) 0부터로 바로잡는다. 그 밖은 그대로."""
    m = LOC.match(loc.strip())
    if not m or m.group(1):
        return loc
    name, idx = m.group(2), int(m.group(3))
    n = len(getattr(page, name))
    if n and idx == n:
        return loc.replace(f"{name}[{idx}]", f"{name}[{idx - 1}]", 1)
    return loc


def apply_revision(prev: TopicPage, rev: TopicPageRevision, allowed: set[str]) -> tuple[TopicPage, int, list[str]]:
    """지적된 위치(최상위 칸 기준)만 합친다. 그 밖의 변경은 되돌림(세어 반환). 삭제는 뒤 번호부터."""
    data = prev.model_dump()
    reverts, notes, deletes = 0, [], []
    for ch in rev.changed:
        loc = top_loc(ch.loc if ch.action == "add" else normalize_loc(prev, ch.loc))
        whole = {a for a in allowed if LIST_LOC.match(a)}  # 목록 전체가 지적되면 그 목록의 항목 변경은 허용
        if loc not in allowed and loc.split("[")[0] not in whole and not (
                ch.action == "add" and loc.split("[")[0] in {a.split("[")[0] for a in allowed}):
            reverts += 1
            notes.append(f"지적 안 된 위치 {ch.loc} 변경 되돌림")
            continue
        if LIST_LOC.match(loc) and ch.action == "add":  # 목록 위치에 더하기(번호 없이 "contributions"): 끝에 붙임(G6)
            loc = f"{loc}[{len(data[loc])}]"
        m = LOC.match(loc)
        if not m and LIST_LOC.match(loc) and ch.action == "delete":
            if loc == "points":  # 포인트 전체 삭제는 받지 않음(필수 칸)
                notes.append("points 전체 삭제는 받지 않음")
                continue
            data[loc] = []  # 칸 전체 비우기(예: numbers 그룹을 문장으로 옮길 때)
            continue
        if not m:
            notes.append(f"알 수 없는 위치 {ch.loc}")
            continue
        sub = SUB_LOC.match(normalize_loc(prev, ch.loc).strip())
        if sub and not m.group(1):  # 하위 위치: numbers[i].items[j] / numbers[i].context·title / events[i].items[j]
            name, i, field_, j = sub.group(1), int(sub.group(2)), sub.group(3), sub.group(4)
            if i >= len(data[name]):
                notes.append(f"{ch.loc}: 위치 없음")
                continue
            group = data[name][i]
            if j is not None and field_ == "items":
                k = int(j)
                if ch.action == "delete" and k < len(group["items"]):
                    group["items"].pop(k)
                elif isinstance(ch.value, NumberItem if name == "numbers" else EventItem) and k < len(group["items"]):
                    group["items"][k] = ch.value.model_dump()
                else:
                    notes.append(f"{ch.loc}: 값 형식이 항목이 아님")
            elif j is None and field_ in ("context", "title", "unit") and isinstance(ch.value, str):
                group[field_] = ch.value
            else:
                notes.append(f"{ch.loc}: 바꿀 수 없는 하위 위치")
            continue
        if m.group(1):
            if ch.action == "edit" and isinstance(ch.value, str):
                data[m.group(1)] = ch.value
            continue
        name, idx = m.group(2), int(m.group(3))
        if ch.action == "delete":
            deletes.append((name, idx))
            continue
        val = ch.value
        if isinstance(val, str) and name == "points":
            val = Point(text=val, refs=data[name][idx]["refs"] if idx < len(data[name]) else [])
        if name == "contributions" and isinstance(val, Point):
            # 채널 없이 낸 기여 문장(OpenRig 재실행: 두 채널을 한 문장에, 반영 확인 리뷰 G6). refs가 한 채널이면 그 채널로
            chans = {"video" if r.startswith("vd:") else "github" if r.startswith("rp:") else "text" for r in val.refs}
            if len(chans) == 1:
                val = Contribution(channel=chans.pop(), text=val.text, refs=val.refs)  # type: ignore[arg-type]
            else:
                notes.append(f"{ch.loc}: 기여 문장이 채널 {sorted(chans)}를 한 문장에 섞음(채널마다 1문장)")
                continue
        if not isinstance(val, FIELD_TYPES[name]):
            notes.append(f"{ch.loc}: 값 형식이 {FIELD_TYPES[name].__name__}가 아님")
            continue
        if ch.action == "edit" and idx < len(data[name]):
            data[name][idx] = val.model_dump()
        else:
            data[name].append(val.model_dump())
    for name, idx in sorted(deletes, key=lambda x: -x[1]):
        if idx < len(data[name]):
            data[name].pop(idx)
    try:
        return TopicPage.model_validate(data), reverts, notes
    except ValueError as e:  # 하위 위치에 형식이 다른 값: 이 수정은 버림
        return prev, reverts, [*notes, f"합친 판이 스키마에 맞지 않아 이 수정 버림: {str(e)[:100]}"]


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


def write_topic(ctx: Ctx, topic: Applied, members: dict[str, Member], table: AliasTable, cfg: BriefConfig,
                review: bool = True, draft: TopicPage | None = None) -> TopicResult:
    """draft를 주면 작성자를 부르지 않고 그 초안부터 검사·검수(--from-step review)."""
    ms = [members[k] for k in topic.members if k in members]
    kept, dropped = cap_pack(ms, cfg.evidence.max_tokens_per_topic)
    pack = pack_index(kept)
    n_sources = len({it.member for it in kept})
    canon = {a: c.canonical for c in alias_lines(table, ms) for a in c.aliases}
    # 이 토픽 이름의 한글 음차 표기(GPT-6 루나, 딥시크-V4.1 플래시)도 정본으로 고친다(리뷰 R11, F10). 근거가 모두 한글
    # 음차뿐인 이름(클로드 소네트 5.5)도 사전으로 되돌린 영문 표기가 정본
    tl = cfg.aliases.transliteration
    translit = []
    for name in sorted({n for m in ms for n in m.entities if n.strip()}):
        target = to_original(table.canonical(name), tl)
        if (pat := translit_pattern(target, tl)) is not None:
            translit.append((pat, target))
    res = TopicResult(topic, "failed", None, [], [], list(pack), dropped, n_sources, costs={},
                      member_by_id={i: v[0].member for i, v in pack.items()})
    if not pack:
        res.attention.append("근거 없음")
        return res
    winp = WriterInput(plan=PlanBrief(rank=topic.rank, angle=topic.angle,
                                      relation=Relation(type=topic.relation_type, topic_id=topic.relation_topic_id)),
                       evidence=evidence_docs(pack), previous=previous_topic(ctx.db, topic.relation_topic_id),
                       aliases=alias_lines(table, ms), limits=writer_limits(cfg, n_sources))
    if draft is None:
        writer = load_role("writer", ctx.models)
        page, err, sid = _call(writer, winp, ctx, res.costs, "writer")
    else:
        page, err, sid = draft, None, None
    if page is None or not page.points:
        res.attention.append(f"작성 실패: {err or '포인트 없음'}")
        ctx.tracer.step(kind="code", role="writer", text=f"{topic.topic_id}: 작성 실패", attention=True, error=err)
        return res
    critic = load_role("critic", ctx.models)
    window_sec = config.load("video.yaml").align_window_sec
    reviser = load_role("writer_revise", ctx.models)
    seen: dict[tuple[str, str], int] = {}
    check_locs: set[str] = set()
    last_issue: dict[str, str] = {}  # 위치 → 마지막 이슈 원문(뺀 도식 표)
    critic_seen = False

    def run_critic(pg: TopicPage, rnd: int, warns: list[str]) -> tuple[Any, str | None, int | None]:
        """refs 근거를 앞에, 나머지 토픽 근거를 뒤에(근거 원문). overview·summary·title은 토픽 근거 전체가 기준이다."""
        nonlocal critic_seen
        # 요약만 있는 id(카드 summary)는 원문이 아니라 빼고 준다(리뷰 R1: 요약·개요가 요약과 대조되던 문제)
        raw_ids = [e for e in pack if not all(it.kind == "summary" for it in pack[e])]
        order = [e for e in refs_of(pg) if e in raw_ids] + [e for e in raw_ids if e not in refs_of(pg)]
        evid = [Document(id=e, source=pack[e][0].source.get("site") or pack[e][0].channel,
                         title=pack[e][0].source.get("title"), text=raw_evidence(ctx.db, e, pack[e], window_sec)) for e in order]
        cinp = CriticInput(loc_lines=loc_lines(pg), page=pg, evidence=evid, angle=topic.angle, previous=winp.previous,
                           code_warnings=warns, round=rnd)
        out = _call(critic, cinp, ctx, res.costs, "critic")
        # 원자 사실 0개로 통과 = 대조를 건너뛴 판정(W40 재실행 3토픽, 출력 49토큰). 한 번 다시 부르고, 또 비면 검수 실패
        if out[0] is not None and not out[0].atoms and pg.points:
            res.attention.append("검수자가 원자 사실 0개로 판정(대조 건너뜀), 다시 부름")
            again = cinp.model_copy(update={"code_warnings": [*warns, "직전 판정이 원자 사실 0개: 모든 문장을 원자 사실로 나눠 대조"]})
            out = _call(critic, again, ctx, res.costs, "critic")
            if out[0] is not None and not out[0].atoms:
                out = (None, "원자 사실 0개 판정 반복", out[2])
        critic_seen = critic_seen or out[0] is not None
        return out
    raw_page: dict[str, Any] | None = page.raw_dump()
    for rnd in range(1, cfg.review.max_rounds + 1):
        cr = checks.run_checks(page, pack, n_sources, cfg, canon, translit)
        page = cr.page
        res.pages.append((rnd, page, raw_page, sid))
        issues = cr.issues
        log = RoundLog(rnd, "code", "reject" if issues else "pass", [i.model_dump() for i in issues], cr.autofix,
                       cr.warnings, sid)
        if not issues and review:
            res.rounds.append(log)
            verdict, err, vsid = run_critic(page, rnd, cr.warnings)
            if verdict is None:  # 검수 실패: 코드 검사만 통과한 판 + attention(검수 판정은 기록하지 않음)
                res.attention.append(f"검수 실패: {err}")
                res.status, res.page, res.final_round = "passed", page, rnd
                break
            v: ReviewVerdict = verdict
            log = RoundLog(rnd, "critic", v.status, [i.model_dump() for i in v.issues], step_id=vsid,
                           fact_support=v.fact_support.model_dump())
            issues = v.issues if v.status == "reject" else []
        res.rounds.append(log)
        if not issues:
            res.status, res.page, res.final_round = "passed", page, rnd
            break
        # 위치 번호를 1부터 센 이슈는 0부터로(검수자가 contributions[2]로 두 번째 항목을 가리킨 사례)
        issues = [i.model_copy(update={"loc": normalize_loc(page, i.loc)}) for i in issues]
        for it in issues:
            last_issue[top_loc(it.loc)] = f"{log.checker} {it.type}: {it.comment}"
        # 같은 위치·같은 유형이 두 번 남으면 확정(check) 후 제외
        # 라운드 사이 반복만 센다(같은 라운드 안의 중복 이슈는 한 번으로, 리뷰 지적 1)
        live = []
        for key in dict.fromkeys((top_loc(it.loc), it.type) for it in issues):
            seen[key] = seen.get(key, 0) + 1
        for it in issues:
            key = (top_loc(it.loc), it.type)
            if seen[key] >= cfg.review.same_issue_repeat_to_check:
                check_locs.add(key[0])
            else:
                live.append(it)
        if rnd == cfg.review.max_rounds or not live:
            check_locs |= {top_loc(i.loc) for i in live}
            res.final_round = rnd
            break
        flagged = {top_loc(i.loc) for i in live}
        rinp = WriterReviseInput(loc_lines=loc_lines(page), previous=page, issues=[IndexedIssue(idx=i, **x.model_dump()) for i, x in enumerate(live)],
                                 evidence=[d for d in evidence_docs({k: v for k, v in pack.items()
                                                                     if k in {x.evidence_id for x in live} | set(
                                     r for loc in flagged for r in _loc_refs(page, loc))})],
                                 aliases=winp.aliases)
        rev, err, rsid = _call(reviser, rinp, ctx, res.costs, "writer_revise")
        if rev is None:
            res.attention.append(f"수정 실패: {err}")
            check_locs |= flagged
            res.final_round = rnd
            break
        raw_page = rev.model_dump()
        page, reverts, notes = apply_revision(page, rev, flagged)
        res.rounds[-1].reverts = reverts
        if notes:
            res.attention += notes[:3]
        sid = rsid
    else:
        res.final_round = cfg.review.max_rounds
    final = res.page or page
    if review and not critic_seen and res.status != "passed":
        # 코드 반려만 이어져 검수자가 한 번도 보지 않고 끝난 판(리뷰 지적 2): 발행 전 한 번 검수, 이슈 위치는 check
        verdict, _err, vsid = run_critic(final, res.final_round or cfg.review.max_rounds, [])
        if verdict is not None:
            res.rounds.append(RoundLog(res.final_round or cfg.review.max_rounds, "critic", verdict.status,
                                       [i.model_dump() for i in verdict.issues], step_id=vsid,
                                       fact_support=verdict.fact_support.model_dump()))
            if verdict.status == "reject":
                check_locs |= {top_loc(normalize_loc(final, i.loc)) for i in verdict.issues}
    # 도식을 빼는 것은 코드가 최종판에서 확인한 형식·수치 오류(단위 섞임, 값 불일치, 빈 단위)일 때만(반영 확인 리뷰 F2:
    # 검수자의 의미 지적만 남은 맞는 도식까지 지워 Haiku 구간 가격·textGrain 탐지율이 빠졌음). 의미 지적만 남으면 두고 ⚠
    code_bad = {(m.group(1), int(m.group(2))) for i in checks.check(final, pack, n_sources, cfg)
                if (m := re.match(r"^(numbers|events)\[(\d+)\]", i.loc))}
    renamed: dict[str, str] = {}
    if code_bad:
        upd: dict[str, Any] = {}
        for name in ("numbers", "events"):
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
        final = final.model_copy(update=upd)
    if check_locs:
        pts = [p.model_copy(update={"check": True}) if f"points[{i}]" in check_locs else p for i, p in enumerate(final.points)]
        final = final.model_copy(update={"points": pts})
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

