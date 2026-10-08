"""S3 3c 레포 분석가: 규칙 기반 큐, 입력 조립(트렌딩 수치, 한 줄 설명, 과열 규칙), 실행, 저장.

과열 규칙은 코드가 입력 조립 때 계산하고 RepoCard.enforce가 고정한다(기준 숫자는 아래 상수, 리포트에 적음).
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from ..core import config
from ..core.artifacts import RepoOnelinerInput
from ..core.artifacts_repo import HypeCheck, ItemTitle, RepoAnalystInput, RepoCard, TrendingStats
from ..core.db import DB, now_kst

HYPE_STARS_WEEK = 1000  # 7일 별 증가가 이 이상이면 "급증"으로 보고 커밋 수를 확인한다
HYPE_COMMITS_7D = 0  # 급증인데 최근 7일 커밋이 이 수 이하면 no_commits → signal=check
SINGLE_CONTRIBUTOR = 1  # 기여자가 이 수 이하면 single_contributor
WEEK_ITEMS = 30  # 입력에 넣는 이번 주 글 제목 수 상한
AWESOME = re.compile(r"(^|[/_-])awesome([_-]|$)|\bcurated list\b|^#?\s*awesome\b", re.I | re.M)


@dataclass
class QueueItem:
    full_name: str
    max_depth: int
    reason: str


def rule_queue(db: DB, week: str, top: int) -> list[QueueItem]:
    """3a 계획 전 규칙 기반 큐: 키워드에 걸린 트렌딩 레포(이번 주 별 순) + 추적 레포 릴리스, 앞 top개."""
    out: list[QueueItem] = []
    for r in db.conn.execute(
            "SELECT full_name, stars_this_week, keywords FROM repo_trending WHERE week=? AND filter_status='pass' "
            "ORDER BY COALESCE(stars_this_week, 0) DESC, rank", (week,)):
        kws = ", ".join(json.loads(r["keywords"] or "{}")) or "키워드"
        out.append(QueueItem(r["full_name"], 2, f"트렌딩 이번 주 별 {r['stars_this_week']}, 키워드 {kws}"))
    seen = {q.full_name for q in out}
    for r in db.conn.execute("SELECT title FROM items WHERE source_id='github_releases' AND week=? ORDER BY published_at DESC",
                             (week,)):
        name = (r["title"] or "").split(" ")[0]
        if name and name not in seen:
            seen.add(name)
            out.append(QueueItem(name, 2, f"추적 레포 릴리스: {r['title'][:60]}"))
    return out[:top]


def trending_stats(db: DB, week: str, full_name: str) -> TrendingStats | None:
    r = db.conn.execute(
        "SELECT t.rank, t.stars_total, t.stars_this_week, t.forks, p.language, p.description FROM repo_trending t "
        "LEFT JOIN repos p ON p.full_name=t.full_name WHERE t.week=? AND t.full_name=?", (week, full_name)).fetchone()
    if r is None:
        return None
    return TrendingStats(week=week, **{k: r[k] for k in ("rank", "stars_total", "stars_this_week", "forks",
                                                         "language", "description")})


def hype_check(ctx: Any, full_name: str, stats: TrendingStats | None, readme: str | None) -> HypeCheck:
    """코드 과열 규칙. 급증일 때만 커밋을 세고(API 1회), 기여자 수는 항상 센다(API 1회)."""
    from ..tools.github import api_get, today

    state = SimpleNamespace(ctx=ctx)
    flags, notes = [], []
    commits = contributors = None
    if AWESOME.search(full_name.split("/")[-1]) or AWESOME.search((readme or "")[:300]):
        flags.append("awesome_list")
    stars = (stats.stars_this_week if stats else None) or 0
    force = False
    try:
        if stars >= HYPE_STARS_WEEK:
            since = (datetime.combine(today(state), datetime.min.time(), UTC) - timedelta(days=7)).strftime(
                "%Y-%m-%dT%H:%M:%SZ")
            _, data = api_get(state, f"/repos/{full_name}/commits?since={since}&per_page=100")
            commits = len(data or [])
            if commits <= HYPE_COMMITS_7D:
                flags.append("no_commits")
                force = True
            notes.append(f"7일 별 +{stars}, 커밋 {commits}")
        _, data = api_get(state, f"/repos/{full_name}/contributors?per_page=100&anon=1")
        contributors = len(data or [])
        if contributors <= SINGLE_CONTRIBUTOR:
            flags.append("single_contributor")
    except Exception as e:  # noqa: BLE001 - API 실패는 규칙 미적용으로 두고 이유를 남긴다
        notes.append(f"과열 규칙 API 실패: {str(e)[:80]}")
    return HypeCheck(flags=flags, force_check=force, commits_7d=commits, contributors=contributors,
                     note="; ".join(notes))


def week_items(db: DB, week: str) -> list[ItemTitle]:
    rows = db.conn.execute(
        "SELECT i.id, i.title, c.card_json FROM items i JOIN item_cards c ON c.item_id=i.id AND c.version=1 "
        "WHERE i.week=? ORDER BY i.id", (week,)).fetchall()
    order = {"high": 0, "mid": 1, "low": 2}
    rows = sorted(rows, key=lambda r: (order.get(json.loads(r["card_json"]).get("relevance"), 3), r["id"]))
    return [ItemTitle(id=f"it:{r['id']}", title=r["title"] or "") for r in rows[:WEEK_ITEMS]]


def oneliner_for(ctx: Any, full_name: str) -> str:
    """저장된 repo_oneliner 결과(같은 입력이면 재사용). 없으면 repo_oneliner를 실행해 저장한다."""
    from ..core.role import RoleFailed, load_role, run

    r = ctx.db.conn.execute("SELECT description, topics_json, readme_head FROM repos WHERE full_name=?",
                            (full_name,)).fetchone()
    raw = {"full_name": full_name, "description": r["description"] if r else None,
           "topics": json.loads(r["topics_json"]) if r and r["topics_json"] else [],
           "readme_head": (r["readme_head"] if r else None) or ""}
    h = hashlib.sha256(json.dumps(raw, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]
    have = ctx.db.conn.execute("SELECT input_hash, output_json FROM repo_oneliners WHERE full_name=?",
                               (full_name,)).fetchone()
    if have and have["input_hash"] == h:
        return json.loads(have["output_json"])["oneliner"]
    role = load_role("repo_oneliner", ctx.models)
    inp = RepoOnelinerInput.model_validate(raw)
    try:
        out = run(role, inp, ctx)
    except RoleFailed as e:
        out = role.output_cls.fallback(str(e)[:60], inp)
    with ctx.db.conn:
        ctx.db.conn.execute("INSERT OR REPLACE INTO repo_oneliners VALUES (?,?,?,?,?)",
                            (full_name, h, json.dumps(out.model_dump(), ensure_ascii=False),
                             ctx.models.models[ctx.model or role.spec.model].id, now_kst()))
    return out.oneliner


def build_input(ctx: Any, q: QueueItem, week: str, keywords: config.KeywordsConfig,
                items: list[ItemTitle] | None = None) -> RepoAnalystInput:
    stats = trending_stats(ctx.db, week, q.full_name)
    r = ctx.db.conn.execute("SELECT readme_head FROM repos WHERE full_name=?", (q.full_name,)).fetchone()
    return RepoAnalystInput(
        full_name=q.full_name, max_depth=q.max_depth, reason=q.reason, trending=stats,
        oneliner=oneliner_for(ctx, q.full_name), keywords=[k.canonical for k in keywords.keywords],
        week_items=items if items is not None else week_items(ctx.db, week),
        hype=hype_check(ctx, q.full_name, stats, r["readme_head"] if r else None))


@dataclass
class RepoRunResult:
    run_id: str
    n: int = 0
    done: int = 0
    fallback: int = 0
    signals: dict[str, int] = field(default_factory=dict)
    relevant: int = 0
    tool_calls: list[int] = field(default_factory=list)
    stopped: str | None = None
    traces: list[dict[str, Any]] = field(default_factory=list)  # 검증 산출물(reports/S3_traces/repo/)

    def summary(self) -> str:
        sig = ", ".join(f"{k} {v}" for k, v in sorted(self.signals.items()))
        avg = sum(self.tool_calls) / len(self.tool_calls) if self.tool_calls else 0
        return (f"레포 {self.n}개 중 {self.done}개 카드(대체 {self.fallback}), 관련 {self.relevant}, 신호 [{sig}], "
                f"평균 도구 호출 {avg:.1f}" + (f", 중단: {self.stopped}" if self.stopped else ""))


def save_card(db: DB, week: str, full_name: str, card: RepoCard, oneliner: str, model: str, run_id: str,
              fallback: bool) -> None:
    data = {**card.model_dump(), "oneliner": oneliner}  # 한 줄은 코드가 붙인다(모델이 다시 쓰지 않음)
    with db.conn:
        db.conn.execute("INSERT OR REPLACE INTO repo_cards VALUES (?,?,?,?,?,?,?)",
                        (week, full_name, json.dumps(data, ensure_ascii=False), model, run_id, now_kst(), int(fallback)))


def count_tool_calls(db: DB, run_id: str, since_step: int) -> int:
    return db.conn.execute("SELECT COUNT(*) FROM steps WHERE run_id=? AND kind='tool' AND id>? AND text NOT LIKE 'finish:%'",
                           (run_id, since_step)).fetchone()[0]


def tool_path(db: DB, run_id: str, since_step: int) -> list[dict[str, Any]]:
    """도구 호출 경로: 도구, 인자, 깊이, 결과 요약(오류), 순서대로."""
    return [{"text": r["text"], "error": r["error"], "detail": json.loads(r["detail"]) if r["detail"] else None}
            for r in db.conn.execute("SELECT text, error, detail FROM steps WHERE run_id=? AND kind='tool' AND id>? "
                                     "ORDER BY id", (run_id, since_step))]


def write_traces(traces: list[dict[str, Any]], out_dir: Path, command: str) -> list[Path]:
    """레포별 입력 수치 + 도구 호출 경로 + 출력 카드(COMMON 10장)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for t in traces:
        inp, card = t["input"], t["card"]
        tr = inp.get("trending") or {}
        lines = [f"# {inp['full_name']}", "", f"- 큐 이유: {inp['reason']} / max_depth {inp['max_depth']}",
                 f"- 트렌딩: 순위 {tr.get('rank')}, 전체 별 {tr.get('stars_total')}, 이번 주 별 {tr.get('stars_this_week')}, "
                 f"포크 {tr.get('forks')}, 언어 {tr.get('language')}",
                 f"- 과열 규칙(코드): {inp['hype']}", f"- 한 줄 설명(repo_oneliner): {inp['oneliner']}", "",
                 "## 도구 호출 경로", "", "| # | 도구 | 인자 | 결과 |", "|---|---|---|---|"]
        for i, s in enumerate(t["steps"], 1):
            name, _, args = s["text"].partition(": ")
            lines.append(f"| {i} | {name} | {args.replace('|', '/')} | {(s['error'] or 'ok').replace('|', '/')[:120]} |")
        lines += ["", "## 출력 카드", "", "```json", json.dumps(card, ensure_ascii=False, indent=1), "```"]
        if t["enforced"]:
            lines += ["", "## enforce(코드 규칙)", ""] + [f"- {e['field']}: {e['before']} → {e['after']} ({e['rule']})"
                                                        for e in t["enforced"]]
        lines += ["", f"재현: `{command}`", ""]
        p = out_dir / f"{inp['full_name'].replace('/', '__')}.md"
        p.write_text("\n".join(lines), encoding="utf-8")
        paths.append(p)
    return paths


def run_repo_analysis(ctx: Any, queue: list[QueueItem], week: str, keywords: config.KeywordsConfig) -> RepoRunResult:
    from ..core.budget import BudgetExceeded, PriceUnknown
    from ..core.llm import LLMError
    from ..core.role import RoleFailed, load_role, run

    role = load_role("repo_analyst", ctx.models)
    res = RepoRunResult(ctx.tracer.run_id, n=len(queue))
    items = week_items(ctx.db, week)
    for q in queue:
        try:
            inp = build_input(ctx, q, week, keywords, items)
            mark = ctx.db.conn.execute("SELECT COALESCE(MAX(id), 0) FROM steps").fetchone()[0]
            try:
                card, fb = run(role, inp, ctx), False
            except RoleFailed as e:
                card, fb = RepoCard.fallback(str(e)[:60], inp), True
            if ctx.stopped:
                res.stopped = ctx.stopped
                break
        except (BudgetExceeded, LLMError, PriceUnknown) as e:
            res.stopped = f"{type(e).__name__}: {e}"
            break
        res.tool_calls.append(count_tool_calls(ctx.db, ctx.tracer.run_id, mark))
        res.traces.append({"input": inp.model_dump(), "card": {**card.model_dump(), "oneliner": inp.oneliner},
                           "enforced": card.enforced, "steps": tool_path(ctx.db, ctx.tracer.run_id, mark)})
        fb = fb or card.relevant_reason.startswith("대체 출력")  # 걸음 상한·예산으로 run_agent가 낸 대체 출력
        save_card(ctx.db, week, q.full_name, card, inp.oneliner, ctx.models.models[ctx.model or role.spec.model].id,
                  ctx.tracer.run_id, fb)
        res.done += 1
        res.fallback += int(fb)
        res.relevant += int(card.relevant)
        res.signals[card.signal] = res.signals.get(card.signal, 0) + 1
    return res
