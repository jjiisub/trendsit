"""weekly 단계 실행(S5_TASK 5.10). 지금은 cluster 단계(근거 목록 → 표기 정규화 → 묶기 → 과거 대조 → 저장 → 리포트)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from ..core import config
from ..core.artifacts import Document
from ..core.artifacts_brief import DecideAnswer, DecideInput, PairShared
from ..core.budget import BudgetExceeded
from ..core.config_brief import BriefConfig
from ..core.context import Ctx
from ..core.errors import LLMError
from ..core.role import RoleFailed, load_role, run_role
from . import aliases as al
from . import cluster as cl
from .evidence import WeekEvidence, week_days, week_evidence


@dataclass
class ClusterStage:
    run_id: str
    evidence: WeekEvidence
    aliases: al.AliasTable
    result: cl.ClusterResult
    seconds: dict[str, float]
    alias_decisions: list[dict[str, Any]]
    video_relevance: dict[str, float] = field(default_factory=dict)


def make_decider(ctx: Ctx) -> cl.Decider:
    role = load_role("decide", ctx.models)

    def decide(inp: DecideInput) -> tuple[DecideAnswer, int | None]:
        try:
            out = run_role(role, inp, ctx)
        except (RoleFailed, LLMError) as e:  # 실패하면 묶지 않음(s5_role_notes 0.4)
            return DecideAnswer.fallback(type(e).__name__, inp), ctx.last_step_id
        return out, ctx.last_step_id  # type: ignore[return-value]

    return decide


def decide_aliases(table: al.AliasTable, ev: WeekEvidence, decider: cl.Decider | None, min_conf: float,
                   limit: int = 10) -> list[dict[str, Any]]:
    """rapidfuzz 후보(애매한 것)만 decide. 같다(confidence 이상)면 approved, 다르다면 rejected, 낮으면 candidate 그대로."""
    out = []
    todo = [r for r in table.rows if r.status == "candidate" and r.keyword_id is None][:limit]
    for r in todo:
        if decider is None:
            break

        def doc(name: str, tag: str, where: list[str] = r.evidence) -> Document:
            titles = [ev.members[k].title for k in where if k in ev.members and name in ev.members[k].entities]
            return Document(id=f"name:{tag}", source="name", title=name,
                            text=f"이름: {name}\n나온 글·영상: " + " / ".join(titles[:4]))

        ans, step_id = decider(DecideInput(a=doc(r.canonical, "a"), b=doc(r.alias, "b"),
                                           shared=PairShared(keywords=[], aliases=[], similarity=0.0)))
        if ans.confidence >= min_conf:
            r.status = "approved" if ans.same else "rejected"
        r.reason += f" / decide: {ans.reason}"
        out.append({"canonical": r.canonical, "alias": r.alias, "same": ans.same, "confidence": ans.confidence,
                    "reason": ans.reason, "status": r.status, "step_id": step_id})
    return out


def stage_cluster(week: str, ctx: Ctx, cfg: BriefConfig | None = None, embedder: Any = None,
                  use_llm: bool = True, set_current: bool = True) -> ClusterStage:
    """cluster 단계. ctx.tracer의 run_id로 모든 행을 쌓는다. set_current면 weeks.current_run_id를 이 실행으로
    (cluster 명령 단독). weekly는 끝까지 마친 뒤에만 바꾼다(중간에 멈춘 run이 현재판이 되지 않게, 리뷰 지적 4)."""
    from ..filter.embed import make_embedder

    cfg = cfg or config.load("brief.yaml")
    keywords = config.load("keywords.yaml")
    db, tr = ctx.db, ctx.tracer
    assert tr is not None
    run_id = tr.run_id
    with db.conn:  # 바로 커밋(열린 쓰기 트랜잭션이 LLM 호출 내내 DB를 잠그지 않게)
        db.conn.execute("UPDATE runs SET week=? WHERE id=?", (week, run_id))
    t0 = time.monotonic()
    ev = week_evidence(db, week)
    n = ev.counts()
    tr.step(kind="code", role="evidence",
            text=f"근거 자격 글 {n['text']}, 영상 {n['video']}, 레포 {n['github']} / 제외 카드 없음 {ev.excluded['no_card']}, "
                 f"digest 없음 {ev.excluded['no_digest']}, 관련 없는 레포 {ev.excluded['irrelevant_repo']}",
            detail={"counts": n, "excluded": ev.excluded})
    t1 = time.monotonic()
    table = al.load_decided(db, al.build(list(ev.members.values()), keywords, cfg.aliases.fuzz_min_score,
                                         cfg.aliases.transliteration))
    decider = make_decider(ctx) if use_llm else None
    try:
        alias_dec = decide_aliases(table, ev, decider, cfg.cluster.decide.min_confidence, cfg.cluster.alias_decide_max)
    except BudgetExceeded:
        alias_dec, decider = [], None
    al.save(db, table, run_id)
    c = table.counts()
    tr.step(kind="code", role="normalize",
            text=f"별칭 자동 승인 {c['auto_approved']}, 후보 {c['candidates']}, decide {len(alias_dec)}",
            detail={"counts": c, "decide": alias_dec})
    t2 = time.monotonic()
    flt = config.load("filter.yaml")
    embedder = embedder or make_embedder("real", flt)
    vrel = cl.score_video_relevance(list(ev.members.values()), embedder,
                                    [(x.keyword_id, x.text) for x in flt.interests], cfg.evidence.video_relevance_high)
    if vrel:
        tr.step(kind="code", role="evidence",
                text=f"영상 관련성 점수: high {sum(v >= cfg.evidence.video_relevance_high for v in vrel.values())}, "
                     f"mid {sum(v < cfg.evidence.video_relevance_high for v in vrel.values())}", detail=vrel)
    try:
        res = cl.cluster_week(db, ev, table, cfg, embedder, decider, alias_decide_calls=len(alias_dec))
    except BudgetExceeded as e:
        tr.step(kind="code", role="cluster", text="예산 상한으로 decide 중단, 판정 없이 묶기", attention=True, error=str(e))
        res = cl.cluster_week(db, ev, table, cfg, embedder, None, alias_decide_calls=len(alias_dec))
    cl.save(db, res, run_id)
    cands = res.candidates()
    multi = [x for x in cands if len(x.channels) >= 2]
    tr.step(kind="code", role="cluster",
            text=f"묶음 {len(res.clusters)}개(토픽 후보 {len(cands)}, 레포만 {len(res.clusters) - len(cands)}), "
                 f"2채널 이상 {len(multi)}, decide {res.decide_calls}회",
            attention=bool(res.blocked_size or res.capped_decides),
            detail={"clusters": len(res.clusters), "candidates": len(cands), "multi_channel": len(multi),
                    "decide_calls": res.decide_calls, "capped": res.capped_decides, "blocked_size": len(res.blocked_size)})
    start, end = week_days(week)
    with db.conn:
        db.conn.execute(
            "INSERT INTO weeks(week, start_day, end_day, status, current_run_id) VALUES (?,?,?,?,?) "
            "ON CONFLICT(week) DO UPDATE SET status=excluded.status, current_run_id=COALESCE(?, weeks.current_run_id)",
            (week, start.isoformat(), end.isoformat(), "clustered", run_id if set_current else None,
             run_id if set_current else None))
    t3 = time.monotonic()
    return ClusterStage(run_id, ev, table, res, {"evidence": round(t1 - t0, 1), "normalize": round(t2 - t1, 1),
                                                 "cluster": round(t3 - t2, 1)}, alias_dec, vrel)
