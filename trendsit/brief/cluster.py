"""묶기와 과거 대조(S5_TASK 5.4). 주 1회, weekly 시작 때. 결과는 run_id로 쌓고 지우지 않는다.

규칙
- 같은 채널 쌍: 유사도 auto 이상은 자동, border~auto는 decide
- 채널을 넘는 쌍: 이름(별칭)이나 구체 키워드를 공유하고 border 이상일 때만 후보, 후보는 전부 decide(자동 묶음 없음)
- decide가 다르다고 한 쌍(confidence 0.6 이상)은 같은 묶음에 넣지 않는다(cannot-link)
- 평균 연결: 두 묶음을 합칠 때 구성원 사이 유사도 평균이 border 이상이어야 한다(decide가 같다고 한 쌍은 auto로 셈).
  사슬처럼 A-B, B-C만 가깝고 A-C가 먼 경우 C는 붙지 않는다
- 묶음 최대 max_cluster_size. 넘는 합치기는 하지 않고 리포트에 표시
- 레포만 있는 묶음은 토픽 후보가 아니다(홈 레포 목록). 항목 1개짜리 글·영상 묶음은 후보
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

from ..core.artifacts import Document
from ..core.artifacts_brief import DecideAnswer, DecideInput, PairShared
from ..core.config_brief import BriefConfig
from ..core.db import DB, now_kst
from ..filter.embed import Embedder, cosine, from_blob, to_blob
from .aliases import AliasTable, norm_key
from .evidence import RELEVANCE_RANK, Member, WeekEvidence

Decider = Callable[[DecideInput], tuple[DecideAnswer, int | None] | None]  # (판정, step_id), None = 예산 초과로 멈춤


@dataclass
class Pair:
    a: str
    b: str
    sim: float
    cross: bool
    shared_kw: list[str] = field(default_factory=list)
    shared_names: list[str] = field(default_factory=list)
    specific_names: list[str] = field(default_factory=list)  # 회사·기관 이름을 뺀 공유 이름(제품·모델·프로젝트)
    route: str = "none"  # auto / decide / none
    via: str = ""  # decide로 간 경로: border(유사도) / name(구체적 이름 공유 + name_border)
    decided: bool = False
    same: bool | None = None
    confidence: float | None = None
    reason: str = ""
    step_id: int | None = None


@dataclass
class Cluster:
    members: list[str]
    joined: dict[str, tuple[str, float | None]]  # member → (joined_by, sim)
    score: float = 0.0
    label: str = ""
    channels: dict[str, int] = field(default_factory=dict)
    repo_only: bool = False
    past: list[dict[str, Any]] = field(default_factory=list)
    shared: dict[str, list[str]] = field(default_factory=dict)
    id: int | None = None


@dataclass
class ClusterResult:
    week: str
    clusters: list[Cluster]
    pairs: list[Pair]
    sims: dict[tuple[str, str], float]
    blocked_size: list[tuple[str, str, float]]
    decide_calls: int
    alias_decide_calls: int
    capped_decides: int
    members: dict[str, Member]

    def candidates(self) -> list[Cluster]:
        return [c for c in self.clusters if not c.repo_only]


# ---------- 임베딩 ----------
def member_text(m: Member) -> str:
    return "\n".join(x for x in (m.title, m.summary) if x).strip()


def member_vectors(db: DB, members: Sequence[Member], embedder: Embedder, mode: str = "card") -> dict[str, list[float]]:
    """mode card(멈춤 지점 결정): 모든 채널을 "제목 + 요약"(글은 카드 summary, 영상은 digest 요약, 레포는 oneliner)으로
    임베딩해 member_embeddings에 저장(같은 모델·같은 입력 해시면 재사용). mode body: 글은 관련성 필터의 본문 임베딩
    (item_embeddings)을 재사용하고 나머지만 새로."""
    vecs: dict[str, list[float]] = {}
    text_ids = {m.item_id: m.key for m in members if m.channel == "text" and m.item_id is not None}
    if text_ids and mode == "body":
        marks = ",".join("?" * len(text_ids))
        for r in db.conn.execute(f"SELECT item_id, vec FROM item_embeddings WHERE model=? AND item_id IN ({marks})",
                                 (embedder.model_id, *text_ids)):
            vecs[text_ids[r["item_id"]]] = from_blob(r["vec"])
    todo = [m for m in members if m.key not in vecs]
    texts = {m.key: member_text(m) for m in todo}
    hashes = {k: hashlib.sha256(t.encode()).hexdigest()[:16] for k, t in texts.items()}
    have = {r["member"]: (r["text_hash"], r["vec"]) for r in db.conn.execute(
        "SELECT member, text_hash, vec FROM member_embeddings WHERE model=?", (embedder.model_id,))}
    need = []
    for k in texts:
        if k in have and have[k][0] == hashes[k]:
            vecs[k] = from_blob(have[k][1])
        else:
            need.append(k)
    if need:
        for k, v in zip(need, embedder.embed_docs([texts[k] for k in need]), strict=True):
            vecs[k] = v
        with db.conn:
            db.conn.executemany(
                "INSERT OR REPLACE INTO member_embeddings(member, model, dim, vec, text_hash, created_at) VALUES (?,?,?,?,?,?)",
                [(k, embedder.model_id, len(vecs[k]), to_blob(vecs[k]), hashes[k], now_kst()) for k in need])
    return vecs


def score_video_relevance(ev: WeekEvidence, embedder: Embedder, interests: list[tuple[str, list[float]]],
                          cfg: BriefConfig) -> dict[str, float]:
    """영상 relevance(멈춤 지점 결정 4): digest 요약을 S2 관련성 필터와 같은 방식(관심사 설명 쿼리와의 코사인 최댓값)으로
    점수 매겨 high 이상이면 high, 아래면 mid. Member.relevance를 바꾸고 점수를 돌려준다."""
    high = cfg.evidence.video_relevance_high
    vids = [m for m in ev.members.values() if m.channel == "video"]
    if not vids:
        return {}
    docs = embedder.embed_docs([member_text(m) for m in vids])
    out = {}
    for m, v in zip(vids, docs, strict=True):
        s = round(max(cosine(v, q) for _k, q in interests), 4)
        m.relevance = "high" if s >= high else "mid"
        out[m.key] = s
    return out


def interest_similarity(db: DB, members: Sequence[Member], embedder: Embedder,
                        interests: list[tuple[str, list[float]]]) -> dict[str, float]:
    """선별 순서(C-21): 모든 채널을 같은 재료("제목 + 요약": 글 카드 summary, 영상 digest 요약, 레포 oneliner)로 임베딩해
    관심사 쿼리와의 코사인 최댓값(S2 관련성 필터 방식). 임베딩은 member_embeddings 캐시(card 모드)를 쓴다."""
    if not members:
        return {}
    vecs = member_vectors(db, members, embedder, mode="card")
    return {k: round(max(cosine(v, q) for _k, q in interests), 4) for k, v in vecs.items()}


# ---------- 쌍 ----------
def build_pairs(members: dict[str, Member], vecs: dict[str, list[float]], aliases: AliasTable,
                cfg: BriefConfig) -> tuple[list[Pair], dict[tuple[str, str], float]]:
    th = cfg.cluster.thresholds
    keys = sorted(members)
    names = {k: aliases.entity_keys(members[k].entities) for k in keys}
    generic = {norm_key(n) for n in cfg.cluster.generic_names}
    broad = set(cfg.cluster.broad_keywords)  # 넓은 1차 그물 키워드: 거의 모든 글이 가져 같은 대상 신호가 되지 않음
    kws = {k: set(members[k].keywords) - broad for k in keys}
    sims: dict[tuple[str, str], float] = {}
    pairs = []
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            s = round(cosine(vecs[a], vecs[b]), 4)
            sims[(a, b)] = sims[(b, a)] = s
            ma, mb = members[a], members[b]
            cross = ma.channel != mb.channel
            shared = sorted(names[a] & names[b])
            p = Pair(a, b, s, cross, sorted(kws[a] & kws[b]), shared, [n for n in shared if n not in generic])
            if ma.channel == mb.channel == "github":
                p.route = "none"  # 레포끼리는 묶지 않음(agglomerate의 cannot-link와 같은 규칙)
            elif cross:
                if (p.shared_kw or p.specific_names) and s >= th.border:
                    p.route, p.via = "decide", "border"
            elif s >= th.auto:
                p.route = "auto"
            elif s >= th.border:
                p.route, p.via = "decide", "border"
            if p.route == "none" and p.specific_names and s >= cfg.cluster.name_border and not (
                    ma.channel == mb.channel == "github"):
                p.route, p.via = "decide", "name"
            pairs.append(p)
    return pairs, sims


def _doc(m: Member) -> Document:
    text = "\n".join([f"요약: {m.summary or m.line}", f"등장 이름: {', '.join(m.entities[:12])}",
                      f"키워드: {', '.join(m.keywords)}"])
    return Document(id=m.key, source=m.channel, title=m.title, text=text)


def decide_input(pair: Pair, members: dict[str, Member]) -> DecideInput:
    return DecideInput(a=_doc(members[pair.a]), b=_doc(members[pair.b]),
                       shared=PairShared(keywords=pair.shared_kw, aliases=pair.shared_names, similarity=pair.sim))


def run_decides(pairs: list[Pair], members: dict[str, Member], decider: Decider | None, cap: int) -> tuple[int, int]:
    """decide 후보를 유사도 높은 순으로 cap개까지. 못 부른 것은 묶지 않는다(실패 대체와 같음)."""
    todo = sorted([p for p in pairs if p.route == "decide"], key=lambda p: -p.sim)
    calls = 0
    for p in todo[:cap]:
        if decider is None:
            break
        res = decider(decide_input(p, members))
        if res is None:
            break
        ans, step_id = res
        p.decided, p.same, p.confidence, p.reason, p.step_id = True, ans.same, ans.confidence, ans.reason, step_id
        calls += 1
    return calls, max(0, len(todo) - cap)


# ---------- 합치기(평균 연결) ----------
def agglomerate(members: dict[str, Member], pairs: list[Pair], sims: dict[tuple[str, str], float],
                cfg: BriefConfig) -> tuple[list[Cluster], list[tuple[str, str, float]]]:
    th, min_conf, cap = cfg.cluster.thresholds, cfg.cluster.decide.min_confidence, cfg.cluster.max_cluster_size
    same = {(p.a, p.b) for p in pairs if p.decided and p.same and (p.confidence or 0) >= min_conf}
    cannot = {(p.a, p.b) for p in pairs if p.decided and not p.same and (p.confidence or 0) >= min_conf}
    # 레포끼리는 이름(full_name)이 다르면 다른 대상이다. 임베딩이 가까워도 묶지 않는다(W41 첫 실행 오병합: openrig ↔ claude-mem)
    cannot |= {(p.a, p.b) for p in pairs if members[p.a].channel == members[p.b].channel == "github"}
    same |= {(b, a) for a, b in same}
    cannot |= {(b, a) for a, b in cannot}

    def link(a: str, b: str) -> float:
        return max(sims[(a, b)], th.auto) if (a, b) in same else sims[(a, b)]

    edges = [(p, "embed") for p in pairs if p.route == "auto"] + [(p, "decide") for p in pairs if (p.a, p.b) in same]
    edges.sort(key=lambda e: -e[0].sim)
    owner = {k: k for k in members}
    groups: dict[str, Cluster] = {k: Cluster([k], {k: ("seed", None)}) for k in members}
    blocked = []
    for p, how in edges:
        ga, gb = owner[p.a], owner[p.b]
        if ga == gb:
            continue
        A, B = groups[ga], groups[gb]
        if any((x, y) in cannot for x in A.members for y in B.members):
            continue
        # 채널을 넘는 구성원 쌍은 모두 decide가 같다고 한 것이어야 한다(자동·전이 묶음 금지, 리뷰 지적 6)
        if any(members[x].channel != members[y].channel and (x, y) not in same for x in A.members for y in B.members):
            continue
        avg = sum(link(x, y) for x in A.members for y in B.members) / (len(A.members) * len(B.members))
        if avg < th.border:
            continue
        if len(A.members) + len(B.members) > cap:
            blocked.append((p.a, p.b, p.sim))
            continue
        (gbig, big), (gsmall, small) = sorted(((ga, A), (gb, B)), key=lambda g: -len(g[1].members))
        for k in small.members:
            sim_k = round(sum(sims[(k, x)] for x in big.members) / len(big.members), 4)
            big.joined[k] = (how if k in (p.a, p.b) else small.joined[k][0], sim_k)
            owner[k] = gbig
        big.members += small.members
        del groups[gsmall]
    return list(groups.values()), blocked


# ---------- 점수, 이름 ----------
def score(c: Cluster, members: dict[str, Member]) -> float:
    """관련성이 먼저(묶음 안 relevance 최댓값, 그 등급의 항목 수). 채널 수·근거 수는 같은 관련성 안 순서만."""
    ms = [members[k] for k in c.members]
    best = min(RELEVANCE_RANK.get(m.relevance, 3) for m in ms)
    n_best = sum(RELEVANCE_RANK.get(m.relevance, 3) == best for m in ms)
    channels = len({m.channel for m in ms})
    evidence = len({it.id for m in ms for it in m.items})
    return round((3 - best) * 1000 + min(n_best, 9) * 100 + channels * 10 + min(evidence, 9), 2)


def finalize(clusters: list[Cluster], members: dict[str, Member], aliases: AliasTable,
             broad: set[str] | None = None) -> list[Cluster]:
    for c in clusters:
        ms = [members[k] for k in c.members]
        c.channels = {ch: sum(m.channel == ch for m in ms) for ch in ("text", "video", "github") if any(m.channel == ch for m in ms)}
        c.repo_only = set(c.channels) == {"github"}
        lead = sorted(ms, key=lambda m: (RELEVANCE_RANK.get(m.relevance, 3), m.channel != "text", m.key))[0]
        c.label = lead.title[:80]
        kw = [set(m.keywords) - (broad or set()) for m in ms]
        names = [aliases.entity_keys(m.entities) for m in ms]
        c.shared = {"keywords": sorted(set.intersection(*kw)) if len(ms) > 1 else [],
                    "names": sorted(set.intersection(*names)) if len(ms) > 1 else []}
        c.score = score(c, members)
    # 저장 순서 = cluster_id 순서는 점수와 무관하게 첫 구성원 키 순(편집장 입력이 id 순서라 위치 편향 방지, 리뷰 지적 7)
    clusters.sort(key=lambda c: sorted(c.members)[0])
    return clusters


# ---------- 과거 대조 ----------
def past_topics(db: DB, week: str, weeks_back: int, model: str) -> list[dict[str, Any]]:
    """지난 주들(현재판 run)의 토픽 제목·요약 임베딩."""
    rows = db.conn.execute(
        "SELECT t.topic_id, t.week, t.title, t.summary, e.vec FROM topics t JOIN weeks w ON w.week=t.week "
        "AND w.current_run_id=t.run_id JOIN topic_embeddings e ON e.topic_id=t.topic_id AND e.run_id=t.run_id "
        "AND e.model=? WHERE t.week<? AND t.status IN ('passed','checked') ORDER BY t.week DESC", (model, week)).fetchall()
    weeks = sorted({r["week"] for r in rows}, reverse=True)[:weeks_back]
    return [{"topic_id": r["topic_id"], "week": r["week"], "title": r["title"], "summary": r["summary"],
             "vec": from_blob(r["vec"])} for r in rows if r["week"] in weeks]


def match_past(clusters: list[Cluster], members: dict[str, Member], vecs: dict[str, list[float]],
               past: list[dict[str, Any]], top_k: int) -> None:
    """묶음 중심(구성원 벡터 평균)과 지난 토픽의 유사도 상위 k. 확정(new/follow_up/duplicate)은 편집장 선별."""
    for c in clusters:
        if not past or c.repo_only:
            c.past = []
            continue
        dim = len(vecs[c.members[0]])
        center = [sum(vecs[k][i] for k in c.members) / len(c.members) for i in range(dim)]
        scored = sorted(((round(cosine(center, p["vec"]), 4), p) for p in past), key=lambda x: -x[0])[:top_k]
        c.past = [{"topic_id": p["topic_id"], "week": p["week"], "title": p["title"], "similarity": s} for s, p in scored]


# ---------- 전체 ----------
def cluster_week(db: DB, ev: WeekEvidence, aliases: AliasTable, cfg: BriefConfig, embedder: Embedder,
                 decider: Decider | None, alias_decide_calls: int = 0) -> ClusterResult:
    members = ev.members
    vecs = member_vectors(db, list(members.values()), embedder, cfg.cluster.embed_text)
    pairs, sims = build_pairs(members, vecs, aliases, cfg)
    cap = max(0, cfg.cluster.decide.max_calls_per_week - alias_decide_calls)
    calls, capped = run_decides(pairs, members, decider, cap)
    clusters, blocked = agglomerate(members, pairs, sims, cfg)
    clusters = finalize(clusters, members, aliases, set(cfg.cluster.broad_keywords))
    match_past(clusters, members, vecs, past_topics(db, ev.week, cfg.cluster.past.weeks_back, embedder.model_id),
               cfg.cluster.past.top_k)
    return ClusterResult(ev.week, clusters, pairs, sims, blocked, calls, alias_decide_calls, capped, members)


def save(db: DB, res: ClusterResult, run_id: str) -> None:
    """clusters, cluster_items, cluster_pairs(판정한 쌍과 후보 쌍만, 전부는 아님)에 run_id로 쌓는다."""
    with db.conn:
        for c in res.clusters:
            body = {"shared": c.shared, "past": c.past, "repo_only": c.repo_only}
            cur = db.conn.execute(
                "INSERT INTO clusters(run_id, week, label, channels_json, n_items, score, body_json) VALUES (?,?,?,?,?,?,?)",
                (run_id, res.week, c.label, json.dumps(c.channels), len(c.members), c.score,
                 json.dumps(body, ensure_ascii=False)))
            c.id = cur.lastrowid
            db.conn.executemany(
                "INSERT INTO cluster_items(cluster_id, member, channel, joined_by, sim) VALUES (?,?,?,?,?)",
                [(c.id, k, res.members[k].channel, c.joined[k][0], c.joined[k][1]) for k in c.members])
        db.conn.executemany(
            "INSERT INTO cluster_pairs(run_id, a, b, sim, cross_channel, decided, answer, confidence, reason, step_id) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            [(run_id, p.a, p.b, p.sim, int(p.cross), int(p.decided), None if p.same is None else int(p.same),
              p.confidence, p.reason or None, p.step_id) for p in res.pairs if p.route != "none"])
