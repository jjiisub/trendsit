"""작성자(1단) + 코드 검사 + 검수자 + 작성자 수정 루프(S6-1 5.5~5.6).

라운드: 초안(1) → 반려 → 수정(2) → 반려 → 수정(3). 최대 max_rounds, 코드 반려도 셈.
- 코드 검사가 반려하면 그 라운드는 검수자를 부르지 않는다(LLM 0원)
- 같은 이슈(위치 + 유형)가 두 라운드 남으면 그 이슈는 더 돌리지 않고 해당 절(또는 summary) check=true로 확정
- 마지막 라운드 뒤 남은 이슈의 절은 check=true, 토픽 status=checked
- writer_revise는 고친 칸만 낸다. 지적되지 않은 위치를 바꾸면 코드가 되돌리고 횟수를 센다
- 잘림(D-42): run_role이 1회 재시도 뒤에도 잘리면 같은 입력에 no_visuals=true로 1회 더(최대 호출 4회)
대체: writer 실패 → 그 토픽 제외(failed) / critic 실패 → 코드 검사만 통과한 판 + attention / revise 실패 → 이전 판 유지
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

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
from . import checks, fulltext, slides
from .aliases import AliasTable, to_original, translit_pattern
from .evidence import EvidenceItem, Member, cap_pack, evidence_docs, pack_index
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
    pages: list[tuple[int, TopicPage, dict[str, Any] | None, int | None]]
    rounds: list[RoundLog]
    evidence_ids: list[str]
    dropped_ids: list[str]
    n_sources: int
    attention: list[str] = field(default_factory=list)
    final_round: int = 0
    costs: dict[str, float] = field(default_factory=dict)
    member_by_id: dict[str, str] = field(default_factory=dict)
    checks: list[str] = field(default_factory=list)
    dropped_diagrams: list[dict[str, Any]] = field(default_factory=list)  # 코드가 visual을 none으로 되돌린 절
    no_visuals: bool = False  # D-42: 잘림 뒤 no_visuals=true로 재시도해 회복한 토픽


# ---------- 입력 조립 ----------
def previous_topic(db: DB, topic_id: str | None) -> PreviousTopic | None:
    if not topic_id:
        return None
    r = db.conn.execute(
        "SELECT t.topic_id, t.title, t.summary, p.page_json FROM topics t JOIN weeks w ON w.week=t.week AND "
        "w.current_run_id=t.run_id LEFT JOIN topic_pages p ON p.run_id=t.run_id AND p.topic_id=t.topic_id AND "
        "p.round=t.final_round WHERE t.topic_id=?", (topic_id,)).fetchone()
    if r is None:
        return None
    heads = [s["heading"] for s in json.loads(r["page_json"]).get("sections", [])] if r["page_json"] else []
    return PreviousTopic(topic_id=r["topic_id"], title=r["title"] or "", summary=r["summary"] or "", headings=heads)


def writer_limits(cfg: BriefConfig, n_sources: int) -> WriterLimits:
    w = cfg.write
    return WriterLimits(sections=w.sections_for(n_sources), paragraphs_per_section=w.paragraphs.per_section,
                        paragraph_sentences_max=w.paragraphs.sentences_max, paragraph_chars_max=w.paragraphs.chars_max,
                        summary_sentences=w.summary.sentences, summary_chars_max=w.summary.chars_max,
                        heading_chars_max=w.heading_chars_max, head_tiles_max=w.head_tiles_max,
                        tiles_per_section=w.tiles_per_section, visuals_max=w.visuals_max, bars_items=w.bars_items,
                        table_rows=w.table.rows, table_cols=w.table.cols, slides_max=w.slides_max,
                        video_secs_max=w.video_secs_max, max_refs_per_paragraph=cfg.evidence.max_refs_per_paragraph)


def alias_lines(table: AliasTable, members: list[Member]) -> list[AliasLine]:
    names = {n for m in members for n in m.entities}
    by: dict[str, list[str]] = {}
    for r in table.rows:
        if r.status == "approved" and r.keyword_id is None and (r.alias in names or r.canonical in names):
            by.setdefault(r.canonical, []).append(r.alias)
    return [AliasLine(canonical=c, aliases=sorted(a)) for c, a in sorted(by.items())]


def topic_slide_info(ms: list[Member], used_members: set[str], cfg: BriefConfig) -> tuple[list[str], set[int]]:
    """이 토픽 근거에 실제로 쓰인 영상 구성원에서 slide_candidates(최대 slides_max)와 허용 video_secs(타임라인 sec)를 모은다."""
    cands: list[str] = []
    secs: set[int] = set()
    for m in ms:
        if m.channel != "video" or m.key not in used_members:
            continue
        cands += m.slide_candidates
        secs |= {t["sec"] for t in m.timeline}
    return cands[: cfg.write.slides_max], secs


def refs_of(page: TopicPage) -> list[str]:
    order = ("point", "number", "event", "context")
    slots = sorted(checks.page_refs(page), key=lambda s: order.index(s.field))
    return list(dict.fromkeys(r for s in slots for r in s.refs))


# ---------- 루프 ----------
def _call(role: Any, inp: Any, ctx: Ctx, costs: dict[str, float], key: str) -> tuple[Any | None, str | None, int | None]:
    before = ctx.budget.session_cost
    try:
        out, err = run_role(role, inp, ctx), None
    except (RoleFailed, LLMError) as e:
        out, err = None, f"{type(e).__name__}: {e}"[:300]
    costs[key] = round(costs.get(key, 0) + ctx.budget.session_cost - before, 6)
    return out, err, ctx.last_step_id


def _canon_translit(table: AliasTable, ms: list[Member], cfg: BriefConfig) -> tuple[dict[str, str], list[tuple[re.Pattern[str], str]]]:
    tl = cfg.aliases.transliteration
    translit = []
    for name in sorted({n for m in ms for n in m.entities if n.strip()}):
        target = to_original(table.canonical(name), tl)
        if (pat := translit_pattern(target, tl)) is not None:
            translit.append((pat, target))
    return {a: c.canonical for c in alias_lines(table, ms) for a in c.aliases}, translit


def _run_critic(ctx: Ctx, res: TopicResult, topic: Applied, winp: WriterInput, pack: dict[str, list[EvidenceItem]],
                pg: TopicPage, rnd: int, warns: list[str]) -> tuple[Any, str | None, int | None]:
    raw_ids = [e for e in pack if not all(it.kind in ("summary", "context") for it in pack[e])]
    order = [e for e in refs_of(pg) if e in raw_ids] + [e for e in raw_ids if e not in refs_of(pg)]
    evid = [Document(id=e, source=pack[e][0].source.get("site") or pack[e][0].channel,
                     title=pack[e][0].source.get("title"), text=fulltext.raw_evidence(ctx.db, e, pack[e])) for e in order]
    cinp = CriticInput(loc_lines=loc_lines(pg), page=pg, evidence=evid, angle=topic.angle, previous=winp.previous,
                       code_warnings=warns, round=rnd)
    critic = load_role("critic", ctx.models)
    out = _call(critic, cinp, ctx, res.costs, "critic")
    if out[0] is not None and not out[0].atoms and pg.sections:
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


def _loc_refs(page: TopicPage, loc: str) -> list[str]:
    m = LOC.match(loc)
    if not m or m.group(1):
        return refs_of(page)
    return [r for slot in checks.page_refs(page) if top_loc(slot.loc) == top_loc(loc) for r in slot.refs]


def _revise(ctx: Ctx, res: TopicResult, reviser: Any, aliases: list[AliasLine], page: TopicPage, live: list[Any],
            flagged: set[str], pack: dict[str, list[EvidenceItem]]) -> tuple[TopicPage, dict[str, Any], int | None] | None:
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
            cfg: BriefConfig, fixers: tuple[Any, Any], slide_candidates: list[str], timeline_secs: set[int],
            page: TopicPage, sid: int | None, review: bool) -> tuple[TopicPage, set[str], dict[str, str]]:
    seen: dict[tuple[str, str], int] = {}
    check_locs: set[str] = set()
    last_issue: dict[str, str] = {}
    reviser = load_role("writer_revise", ctx.models)
    raw_page: dict[str, Any] | None = page.raw_dump()
    for rnd in range(1, cfg.review.max_rounds + 1):
        cr = checks.run_checks(page, pack, res.n_sources, cfg, *fixers, slide_candidates, timeline_secs)
        page = cr.page
        res.pages.append((rnd, page, raw_page, sid))
        issues = cr.issues
        log = RoundLog(rnd, "code", "reject" if issues else "pass", [i.model_dump() for i in issues], cr.autofix, cr.warnings, sid)
        if not issues and review:
            res.rounds.append(log)
            verdict, err, vsid = _run_critic(ctx, res, topic, winp, pack, page, rnd, cr.warnings)
            if verdict is None:
                res.attention.append(f"검수 실패: {err}")
                res.status, res.page, res.final_round = "passed", page, rnd
                break
            log = _critic_log(rnd, verdict, vsid)
            issues = verdict.issues if verdict.status == "reject" else []
        res.rounds.append(log)
        if not issues:
            res.status, res.page, res.final_round = "passed", page, rnd
            break
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
    rnd = res.final_round or cfg.review.max_rounds
    verdict, _err, vsid = _run_critic(ctx, res, topic, winp, pack, final, rnd, [])
    if verdict is not None:
        res.rounds.append(_critic_log(rnd, verdict, vsid))
        if verdict.status == "reject":
            check_locs |= {top_loc(normalize_loc(final, i.loc)) for i in verdict.issues}


def _drop_code_bad_sections(res: TopicResult, final: TopicPage, pack: dict[str, list[EvidenceItem]], cfg: BriefConfig,
                            last_issue: dict[str, str], check_locs: set[str]) -> TopicPage:
    """형식·수치 오류가 최종판에도 남은 절은 visual만 none으로 비우고 단락은 둔다(의미 지적만 남으면 그대로 두고 ⚠)."""
    bad_secs = {int(m.group(1)) for i in checks.check(final, pack, res.n_sources, cfg)
               if (m := re.match(r"^sections\[(\d+)\]", i.loc)) and ".paragraphs" not in i.loc and ".heading" not in i.loc}
    if not bad_secs:
        return final
    secs = list(final.sections)
    for idx in bad_secs:
        loc = f"sections[{idx}]"
        res.dropped_diagrams.append({"section": loc, "heading": secs[idx].heading, "issue": last_issue.get(loc, "")})
        check_locs.add(loc)
        secs[idx] = secs[idx].model_copy(update={"visual": "none", "bars": None, "table": None, "tiles": [], "events": None,
                                                  "slide": None, "slide_caption": ""})
    res.attention.append(f"형식·수치 오류가 남은 시각 요소 {len(bad_secs)}개 뺌(절 단락은 유지)")
    return final.model_copy(update={"sections": secs})


def _scrub_pack_refs(res: TopicResult, final: TopicPage, pack: dict[str, list[EvidenceItem]]) -> tuple[TopicPage, set[str]]:
    """최종판 저장 직전 안전망(C-1): 라운드를 다 거친 뒤에도 pack 밖 refs가 남으면 지운다(남은 지적만으로는 이미
    못 고쳤으므로, 가짜 출처로 발행되는 것보다 그 칸을 비우는 쪽을 택한다)."""
    secs = list(final.sections)
    touched: set[str] = set()
    for i, s in enumerate(secs):
        upd: dict[str, Any] = {}
        paras = [p.model_copy(update={"refs": kept}) if (kept := [r for r in p.refs if r in pack]) != p.refs else p
                 for p in s.paragraphs]
        if paras != list(s.paragraphs):
            upd["paragraphs"] = paras
        if s.tiles:
            tiles = [t.model_copy(update={"refs": kept}) if (kept := [r for r in t.refs if r in pack]) != t.refs else t
                     for t in s.tiles]
            if tiles != list(s.tiles):
                upd["tiles"] = tiles
        if s.table is not None and (kept := [r for r in s.table.refs if r in pack]) != s.table.refs:
            upd["table"] = s.table.model_copy(update={"refs": kept})
        if s.bars is not None and any(it.ref not in pack for it in s.bars.items):
            upd["visual"], upd["bars"] = "none", None
        if s.events is not None:
            items = [it for it in s.events.items if it.ref is None or it.ref in pack]
            if len(items) != len(s.events.items):
                upd["visual"], upd["events"] = ("none", None) if len(items) < 2 else (s.visual, s.events.model_copy(update={"items": items}))
        if s.slide and s.slide not in pack:
            upd["slide"], upd["slide_caption"] = None, ""
        if upd:
            secs[i] = s.model_copy(update=upd)
            touched.add(f"sections[{i}]")
    tiles = [t for t in final.head_tiles if all(r in pack for r in t.refs)]
    if touched or len(tiles) != len(final.head_tiles):
        res.attention.append("pack 밖 근거 id를 최종판에서 지움(C-1)")
        return final.model_copy(update={"sections": secs, "head_tiles": tiles}), touched
    return final, touched


def _finalize_page(res: TopicResult, final: TopicPage, pack: dict[str, list[EvidenceItem]], cfg: BriefConfig,
                   last_issue: dict[str, str], check_locs: set[str], ms: list[Member], slide_candidates: list[str],
                   timeline_secs: set[int]) -> tuple[TopicPage, set[str]]:
    """저장 전 마지막 손질: 코드 확인 오류가 남은 시각 요소 빼기 → 미배치 슬라이드 배치 → 프레임 생성 → pack 밖 refs 제거."""
    final = _drop_code_bad_sections(res, final, pack, cfg, last_issue, check_locs)
    final = slides.place_unassigned(final, slide_candidates, timeline_secs, cfg.write.slides_max)
    final = slides.render_frames(final, {m.key: m for m in ms}, res.attention)
    final, scrubbed_locs = _scrub_pack_refs(res, final, pack)
    return final, check_locs | scrubbed_locs


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
    used_members = {it.member for v in pack.values() for it in v}
    for m in ms:
        if m.corrections.get("_no_text") and m.key in used_members:
            res.attention.append(f"원문 없음: {m.key}")
    slide_candidates, timeline_secs = topic_slide_info(ms, used_members, cfg)
    winp = WriterInput(plan=PlanBrief(rank=topic.rank, angle=topic.angle,
                                      relation=Relation(type=topic.relation_type, topic_id=topic.relation_topic_id)),
                       evidence=evidence_docs(pack), previous=previous_topic(ctx.db, topic.relation_topic_id),
                       aliases=alias_lines(table, ms), limits=writer_limits(cfg, n_sources),
                       slide_candidates=slide_candidates, no_visuals=False)
    if draft is not None:
        draft = draft.model_copy(update={"sections": [s.model_copy(update={"check": False}) for s in draft.sections]})
        page, err, sid = draft, None, None
    else:
        page, err, sid = _call(load_role("writer", ctx.models), winp, ctx, res.costs, "writer")
        if page is None and err and "출력 잘림" in err:  # D-42: no_visuals로 1회 더
            res.attention.append("작성 잘림, no_visuals로 재시도")
            winp2 = winp.model_copy(update={"no_visuals": True})
            page, err2, sid = _call(load_role("writer", ctx.models), winp2, ctx, res.costs, "writer")
            if page is not None:
                winp = winp2
                res.no_visuals = True
            err = err2 if page is None else err
    if page is None or not page.sections:
        # pipeline._log_topic이 토픽마다 steps(writer,code) 행을 하나 남긴다(D-37 counts.written). 여기서 또
        # 남기면 실패 토픽이 두 번 세이므로(006-A1-24) attention에만 적고 트레이스는 _log_topic에 맡긴다
        msg = "작성 실패: 잘림" if err and "출력 잘림" in err else f"작성 실패: {err or '절 없음'}"
        res.attention.append(msg)
        return res
    page, check_locs, last_issue = _rounds(ctx, res, topic, winp, pack, cfg, _canon_translit(table, ms, cfg),
                                           slide_candidates, timeline_secs, page, sid, review)
    final = res.page or page
    if review and not any(lg.checker == "critic" for lg in res.rounds) and res.status != "passed":
        _critic_unseen_pages(ctx, res, topic, winp, pack, final, check_locs, cfg)
    final, check_locs = _finalize_page(res, final, pack, cfg, last_issue, check_locs, ms, slide_candidates, timeline_secs)
    secs = [s.model_copy(update={"check": f"sections[{i}]" in check_locs}) for i, s in enumerate(final.sections)]
    final = final.model_copy(update={"sections": secs})
    if check_locs:
        res.checks = sorted(check_locs)
        res.status = "checked"
    elif res.status != "passed":
        res.status = "checked"
    res.page = final
    if res.pages and res.pages[-1][1] != final:
        res.pages.append((res.final_round, final, None, None))
    return res


# ---------- 저장 ----------
def save(db: DB, res: TopicResult, run_id: str) -> None:
    t = res.topic
    with db.conn:
        seen_rounds = set()
        for rnd, page, raw, step_id in res.pages:
            if rnd in seen_rounds:
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
                [(run_id, t.topic_id, eid, res.member_by_id[eid], slot.field, 0)
                 for slot in checks.page_refs(page) for eid in slot.refs if eid in res.member_by_id])
        db.conn.execute("UPDATE topics SET status=?, final_round=?, title=?, summary=?, checks_json=? "
                        "WHERE run_id=? AND topic_id=?",
                        (res.status, res.final_round, page.title if page else None, page.summary if page else None,
                         json.dumps(res.checks, ensure_ascii=False), run_id, t.topic_id))
