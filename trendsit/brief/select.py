"""편집장 선별(S5_TASK 5.5, roles/editor_select.md, LLM 1회 + 코드 검증·재시도 2회·대체).

입력: 묶음(토픽 후보, 레포만 묶음 제외) 중 점수 상위 max_candidates를 cluster_id 순서로(위치 편향 방지).
검증(어기면 오류 메시지로 재시도): 리드 정확히 1, 토픽 수 min~max(후보가 min보다 적으면 후보 수까지), rank 1부터 연속,
cluster_ids·splits는 입력 후보와 그 항목 안, 한 후보는 한 토픽에만, relation.topic_id는 그 후보의 과거 대조 후보 안,
decisions가 모든 후보를 덮음. reason 속 숫자·출처 이름은 입력과 대조해 어긋나면 attention(거부하지 않음).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from ..core.artifacts import Document
from ..core.artifacts_brief import (
    BriefingPlan,
    EditorSelectInput,
    KeywordTrend,
    PlannedTopic,
    RecentTopic,
    Relation,
    RepoLine,
    SelectLimits,
)
from ..core.budget import BudgetExceeded
from ..core.config_brief import BriefConfig
from ..core.context import Ctx
from ..core.db import DB, now_kst
from ..core.errors import LLMError
from ..core.role import RoleFailed, load_role, run_role
from .evidence import Member, WeekEvidence

SELECT_RETRIES = 2
_NUM = re.compile(r"\d+(?:\.\d+)?")


@dataclass
class Candidate:
    cluster_id: int
    label: str
    members: list[str]
    channels: dict[str, int]
    score: float
    past: list[dict[str, Any]]
    n_evidence: int = 0


@dataclass
class Applied:
    """확정된 토픽 하나(저장·작성 입력)."""

    topic_id: str
    rank: int
    lead: bool
    cluster_ids: list[int]
    members: list[str]
    relation_type: str
    relation_topic_id: str | None
    relation_label: str
    angle: str


@dataclass
class SelectResult:
    plan: BriefingPlan | None
    source: str  # model / fallback
    topics: list[Applied]
    candidates: list[Candidate]
    errors_by_try: list[list[str]] = field(default_factory=list)
    reason_mismatch: list[str] = field(default_factory=list)
    step_id: int | None = None


# ---------- 입력 ----------
def load_candidates(db: DB, run_id: str, ev: WeekEvidence, limit: int) -> list[Candidate]:
    """그 run의 묶음 중 토픽 후보(레포만 묶음 제외), 점수 상위 limit개를 cluster_id 순서로."""
    rows = db.conn.execute("SELECT id, label, channels_json, score, body_json FROM clusters WHERE run_id=? ORDER BY id",
                           (run_id,)).fetchall()
    cands = []
    for r in rows:
        body = json.loads(r["body_json"] or "{}")
        if body.get("repo_only"):
            continue
        members = [x["member"] for x in db.conn.execute(
            "SELECT member FROM cluster_items WHERE cluster_id=? ORDER BY rowid", (r["id"],))]
        members = [k for k in members if k in ev.members]
        n_ev = len({it.id for k in members for it in ev.members[k].items})
        cands.append(Candidate(r["id"], r["label"] or "", members, json.loads(r["channels_json"] or "{}"), r["score"] or 0,
                               body.get("past") or [], n_ev))
    top = sorted(cands, key=lambda c: (-c.score, c.cluster_id))[:limit]
    return sorted(top, key=lambda c: c.cluster_id)


def candidate_doc(c: Candidate, members: dict[str, Member]) -> Document:
    lines = [f"임시 이름: {c.label}",
             "채널별 수: " + ", ".join(f"{k} {v}" for k, v in c.channels.items()),
             f"근거 수: {c.n_evidence}", f"점수: {c.score}", "항목:"]
    for k in c.members:
        m = members[k]
        lines.append(f"- {k} [{m.channel}] {m.title} | {m.line} | relevance {m.relevance}")
    if c.past:
        lines.append("과거 대조 후보: " + "; ".join(f"{p['topic_id']} '{p['title']}' {p['similarity']}" for p in c.past))
    else:
        lines.append("과거 대조 후보: 없음")
    return Document(id=f"c{c.cluster_id}", source="cluster", title=c.label, text="\n".join(lines))


def recent_topics(db: DB, week: str, weeks_back: int = 4) -> list[RecentTopic]:
    rows = db.conn.execute(
        "SELECT t.topic_id, t.week, t.title, t.summary FROM topics t JOIN weeks w ON w.week=t.week "
        "AND w.current_run_id=t.run_id WHERE t.week<? AND t.status IN ('passed','checked') ORDER BY t.week DESC, t.rank",
        (week,)).fetchall()
    weeks = sorted({r["week"] for r in rows}, reverse=True)[:weeks_back]
    return [RecentTopic(topic_id=r["topic_id"], week=r["week"], title=r["title"] or "", summary=r["summary"] or "")
            for r in rows if r["week"] in weeks]


def prev_week(week: str) -> str:
    y, w = week.split("-W")
    d = date.fromisocalendar(int(y), int(w), 1).toordinal() - 7
    iso = date.fromordinal(d).isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def keyword_trend(db: DB, week: str) -> list[KeywordTrend]:
    """키워드별 이번 주·지난주 통과 항목 수(item_keywords, filter_status=pass)."""
    def counts(w: str) -> dict[str, int]:
        return {r["keyword_id"]: r["n"] for r in db.conn.execute(
            "SELECT k.keyword_id, COUNT(*) AS n FROM item_keywords k JOIN items i ON i.id=k.item_id "
            "WHERE i.week=? AND i.filter_status='pass' GROUP BY 1", (w,))}
    now, before = counts(week), counts(prev_week(week))
    return [KeywordTrend(keyword=k, this_week=now.get(k, 0), last_week=before.get(k, 0))
            for k in sorted(set(now) | set(before))]


def repo_lines(ev: WeekEvidence) -> list[RepoLine]:
    out = []
    for m in ev.members.values():
        if m.channel != "github":
            continue
        signal = next((it.text.split(": ", 1)[1] for it in m.items if it.text.startswith("신호: ")), "")
        stars = next((int(it.value.replace(",", "")) for it in m.items if it.text == "이번 주 별" and it.value), None)
        out.append(RepoLine(full_name=m.title, oneliner=m.line, signal=signal, stars_this_week=stars))
    return out


def build_input(cands: list[Candidate], ev: WeekEvidence, db: DB, cfg: BriefConfig) -> EditorSelectInput:
    return EditorSelectInput(candidates=[candidate_doc(c, ev.members) for c in cands],
                             recent_topics=recent_topics(db, ev.week, cfg.cluster.past.weeks_back),
                             keyword_trend=keyword_trend(db, ev.week), repo_cards=repo_lines(ev),
                             limits=SelectLimits(min_topics=cfg.select.topics.min, max_topics=cfg.select.topics.max,
                                                 lead=cfg.select.lead))


# ---------- 검증 ----------
def validate(plan: BriefingPlan, cands: list[Candidate], cfg: BriefConfig) -> list[str]:
    """코드가 지키는 규칙. 어기면 오류 문장(재시도 입력)."""
    errs = []
    by_id = {c.cluster_id: c for c in cands}
    lo = min(cfg.select.topics.min, len(cands))
    hi = cfg.select.topics.max
    n = len(plan.topics)
    if not lo <= n <= hi:
        errs.append(f"topics 개수 {n}개: {lo}~{hi}개여야 함(최대는 채울 목표가 아님)")
    leads = [t for t in plan.topics if t.lead]
    if n and len(leads) != 1:
        errs.append(f"lead가 {len(leads)}개: 정확히 1개여야 함")
    ranks = sorted(t.rank for t in plan.topics)
    if ranks != list(range(1, n + 1)):
        errs.append(f"rank {ranks}: 1부터 빠짐없이 연속이어야 함")
    if leads and leads[0].rank != 1:
        errs.append("lead 토픽의 rank가 1이 아님")
    used: dict[int, int] = {}
    for t in plan.topics:
        for cid in t.cluster_ids:
            if cid not in by_id:
                errs.append(f"topics의 cluster_id {cid}: 입력 후보에 없음")
            used[cid] = used.get(cid, 0) + 1
        if t.relation.type == "follow_up":
            allowed = {p["topic_id"] for cid in t.cluster_ids if cid in by_id for p in by_id[cid].past}
            if t.relation.topic_id not in allowed:
                errs.append(f"rank {t.rank} relation.topic_id {t.relation.topic_id}: 그 후보의 과거 대조 후보에 없음"
                            f"(있는 것: {sorted(allowed) or '없음'})")
        elif t.relation.topic_id:
            errs.append(f"rank {t.rank}: relation new인데 topic_id가 있음")
    errs += [f"cluster_id {cid}가 토픽 {k}개에 들어감: 한 후보는 한 토픽에만" for cid, k in used.items() if k > 1]
    for sp in plan.splits:
        if sp.cluster_id not in by_id:
            errs.append(f"splits cluster_id {sp.cluster_id}: 입력 후보에 없음")
            continue
        inside = set(by_id[sp.cluster_id].members)
        bad = [k for g in sp.groups for k in g if k not in inside]
        if bad:
            errs.append(f"splits c{sp.cluster_id}의 {bad}: 그 후보의 항목이 아님")
    missing = sorted(set(by_id) - {d.cluster_id for d in plan.decisions})
    if missing:
        errs.append(f"decisions에 빠진 후보: {missing}(모든 후보마다 하나)")
    for d in plan.decisions:
        if d.action == "drop" and d.drop_reason is None:
            errs.append(f"decisions c{d.cluster_id}: drop인데 drop_reason 없음")
    selected = {d.cluster_id for d in plan.decisions if d.action == "select"}
    in_topics = {cid for t in plan.topics for cid in t.cluster_ids}
    if in_topics - selected:
        errs.append(f"topics에 있는데 decisions가 select가 아닌 후보: {sorted(in_topics - selected)}")
    return errs


def reason_mismatches(plan: BriefingPlan, inp: EditorSelectInput, site_names: list[str]) -> list[str]:
    """reason 속 숫자·출처 이름이 그 후보 문서(또는 전체 입력)에 있는지(S3 editor_plan 교훈). 어긋나면 기록만."""
    docs = {d.id: d.text + " " + (d.title or "") for d in inp.candidates}
    whole = " ".join(docs.values())
    out = []
    for d in plan.decisions:
        doc = docs.get(f"c{d.cluster_id}", "")
        for n in _NUM.findall(d.reason):
            if n not in doc and n not in whole:
                out.append(f"c{d.cluster_id} reason의 숫자 {n}이 입력에 없음: {d.reason[:80]}")
        for s in site_names:
            if s and s in d.reason and s not in doc:
                out.append(f"c{d.cluster_id} reason의 출처 '{s}'가 그 후보에 없음: {d.reason[:80]}")
    return out


# ---------- 적용 ----------
def slugify(hint: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", hint.lower()).strip("-")
    return "-".join(s.split("-")[:4]) or "topic"


def week_num(week: str) -> int:
    return int(week.split("-W")[1])


def relation_label(db: DB, topic_id: str | None) -> str:
    if not topic_id:
        return ""
    r = db.conn.execute("SELECT t.week, t.title FROM topics t JOIN weeks w ON w.week=t.week AND w.current_run_id=t.run_id "
                        "WHERE t.topic_id=?", (topic_id,)).fetchone()
    if r is None:
        return ""
    y, w = r["week"].split("-W")
    monday = date.fromisocalendar(int(y), int(w), 1)
    nth = (monday.day + monday.replace(day=1).weekday() - 1) // 7 + 1  # 달력 줄 기준(1일이 든 주가 1주차)
    return f"{monday.month}월 {nth}주차 '{r['title']}' 토픽의 후속"


def apply(plan: BriefingPlan, cands: list[Candidate], week: str, db: DB) -> list[Applied]:
    by_id = {c.cluster_id: c for c in cands}
    first_group = {sp.cluster_id: sp.groups[0] for sp in plan.splits if sp.groups}
    used: set[str] = set()
    out = []
    for t in sorted(plan.topics, key=lambda t: t.rank):
        base = f"w{week_num(week)}-{slugify(t.slug_hint)}"
        tid, k = base, 2
        while tid in used:
            tid, k = f"{base}-{k}", k + 1
        used.add(tid)
        members = []
        for cid in t.cluster_ids:
            group = first_group.get(cid)
            members += [m for m in by_id[cid].members if group is None or m in group]
        rel_id = t.relation.topic_id if t.relation.type == "follow_up" else None
        out.append(Applied(tid, t.rank, t.lead, list(t.cluster_ids), list(dict.fromkeys(members)), t.relation.type,
                           rel_id, relation_label(db, rel_id), t.angle))
    return out


def fallback_plan(cands: list[Candidate], cfg: BriefConfig, reason: str) -> BriefingPlan:
    """점수 순 상위 N(min과 후보 수 중 작은 값), 1위 리드."""
    n = min(cfg.select.topics.min, len(cands))
    top = sorted(cands, key=lambda c: (-c.score, c.cluster_id))[:n]
    from ..core.artifacts_brief import Decision

    chosen = {c.cluster_id for c in top}
    return BriefingPlan(
        decisions=[Decision(cluster_id=c.cluster_id, reason="대체: 점수 순", action="select" if c.cluster_id in chosen else "drop",
                            drop_reason=None if c.cluster_id in chosen else "other") for c in cands],
        splits=[],
        topics=[PlannedTopic(cluster_ids=[c.cluster_id], rank=i, lead=i == 1, relation=Relation(type="new", topic_id=None),
                             relation_reason="대체 계획", angle="", slug_hint=re.sub(r"[^a-z0-9]+", "-", c.label.lower())[:30]
                             or f"c{c.cluster_id}")
                for i, c in enumerate(top, 1)],
        featured_repos=[], log=f"대체 계획: 점수 순 상위 {n}개 ({reason})", attention=True)


def select(ctx: Ctx, cands: list[Candidate], ev: WeekEvidence, cfg: BriefConfig, site_names: list[str]) -> SelectResult:
    role = load_role("editor_select", ctx.models)
    inp = build_input(cands, ev, ctx.db, cfg)
    errors_by_try: list[list[str]] = []
    plan: BriefingPlan | None = None
    source = "model"
    for _ in range(SELECT_RETRIES + 1):
        try:
            out = run_role(role, inp, ctx)
        except (RoleFailed, LLMError, BudgetExceeded) as e:
            errors_by_try.append([f"{type(e).__name__}: {e}"])
            break
        errs = validate(out, cands, cfg)  # type: ignore[arg-type]
        errors_by_try.append(errs)
        if not errs:
            plan = out  # type: ignore[assignment]
            break
        inp = inp.model_copy(update={"previous_errors": errs})
    if plan is None:
        plan, source = fallback_plan(cands, cfg, "검증 실패" if errors_by_try else "호출 실패"), "fallback"
    mism = reason_mismatches(plan, inp, site_names) if source == "model" else []
    if mism and not plan.attention:
        plan = plan.model_copy(update={"attention": True})
    plan = plan.model_copy(update={"featured_repos": [r for r in plan.featured_repos
                                                      if r in {x.full_name for x in inp.repo_cards}]
                                   [: cfg.select.featured_repos_max]})
    return SelectResult(plan, source, apply(plan, cands, ev.week, ctx.db), cands, errors_by_try, mism, ctx.last_step_id)


def save(db: DB, res: SelectResult, run_id: str, week: str) -> None:
    with db.conn:
        db.conn.execute("INSERT INTO briefing_plans(run_id, week, source, plan_json, created_at) VALUES (?,?,?,?,?)",
                        (run_id, week, res.source, res.plan.model_dump_json() if res.plan else "{}", now_kst()))
        for t in res.topics:
            db.conn.execute(
                "INSERT INTO topics(run_id, topic_id, week, cluster_ids_json, rank, lead, relation_type, relation_topic_id, "
                "status, angle) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (run_id, t.topic_id, week, json.dumps(t.cluster_ids), t.rank, int(t.lead), t.relation_type,
                 t.relation_topic_id, "selected", t.angle))
        db.conn.execute("UPDATE weeks SET status='selected' WHERE week=?", (week,))
