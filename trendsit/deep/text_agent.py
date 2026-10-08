"""S3 3b 글 분석가: 확인할 것 추출(v1의 수치·주장), 입력 조립, 실행(계획의 text_queue 또는 한 항목), 저장(v2), 추적 경로 산출물."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..core.artifacts_text import ArticleLink, CheckItem, ItemCardV1, ItemCardV2, TextAnalystInput, norm_url
from ..core.db import DB
from ..summarize import load_card, save_card


def checks_from_v1(card: ItemCardV1) -> list[CheckItem]:
    """확인할 것: 수치 먼저, 그다음 주장. 번호는 1부터(verified.check_n)."""
    quotes = {q.n: q.text for q in card.quotes}
    out = [CheckItem(n=0, kind="number", text=f"{x.what}: {x.value}{x.unit}", quote=quotes.get(x.quote_n, ""))
           for x in card.numbers]
    out += [CheckItem(n=0, kind="claim", text=c.text, quote=" / ".join(quotes.get(n, "") for n in c.quote_ns))
            for c in card.claims]
    return [c.model_copy(update={"n": i}) for i, c in enumerate(out, 1)]


def build_input(db: DB, item_id: int, max_depth: int, tool_calls: int | None = None) -> TextAnalystInput:
    row = db.conn.execute("SELECT i.id, i.title, i.url, i.source_id, s.name FROM items i "
                          "LEFT JOIN sources s ON s.id=i.source_id WHERE i.id=?", (item_id,)).fetchone()
    raw = load_card(db, item_id, 1)
    if row is None or raw is None:
        raise KeyError(f"항목 {item_id}의 1차 요약(v1)이 없음")
    card = ItemCardV1.model_validate(raw)
    cand = set(card.origin_candidates)
    links = [ArticleLink(n=n, url=r["url"], kind=r["kind"], anchor=r["anchor"] or None,
                         candidate=n in cand or r["role"] == "origin_candidate")
             for n, r in enumerate(db.conn.execute("SELECT url, kind, anchor, role FROM links WHERE item_id=? ORDER BY id",
                                                   (item_id,)), 1)]
    return TextAnalystInput(item_id=row["id"], title=row["title"] or "", source_name=row["name"] or row["source_id"],
                            url=row["url"] or "", max_depth=max_depth, card_v1=card, links=links,
                            checks=checks_from_v1(card), tool_calls=tool_calls)


@dataclass
class TextRunResult:
    run_id: str
    n: int = 0
    done: int = 0
    origin_found: int = 0
    depths: dict[int, int] = field(default_factory=dict)  # 원본을 찾은 깊이 분포
    statuses: dict[str, int] = field(default_factory=dict)
    stopped: str | None = None
    traces: list[dict[str, Any]] = field(default_factory=list)

    def summary(self) -> str:
        st = ", ".join(f"{k} {v}" for k, v in sorted(self.statuses.items()))
        dp = ", ".join(f"깊이 {k}: {v}" for k, v in sorted(self.depths.items()))
        return (f"글 {self.n}건 중 {self.done}건, 원본 확보 {self.origin_found}건 [{dp}], 대조 [{st}]"
                + (f", 중단: {self.stopped}" if self.stopped else ""))


def run_text_analysis(ctx: Any, queue: list[tuple[int, int]]) -> TextRunResult:
    """queue = [(item_id, max_depth)]. 항목마다 가져온 페이지 기록을 비우고 시작(enforce 대조 범위 = 이번 실행)."""
    from ..core import config
    from ..core.budget import BudgetExceeded, PriceUnknown
    from ..core.llm import LLMError
    from ..core.role import RoleFailed, load_role, run
    from .repo_agent import tool_path

    role = load_role("text_analyst", ctx.models)
    calls = config.load("deep.yaml").text_tool_calls_per_item
    res = TextRunResult(ctx.tracer.run_id, n=len(queue))
    for item_id, depth in queue:
        inp = build_input(ctx.db, item_id, depth, calls)
        ctx.resources["fetched_pages"], ctx.resources["page_depth"] = {}, {}
        mark = ctx.db.conn.execute("SELECT COALESCE(MAX(id), 0) FROM steps").fetchone()[0]
        try:
            card: ItemCardV2 = run(role, inp, ctx)  # type: ignore[assignment]
        except RoleFailed as e:
            card = ItemCardV2.fallback(str(e)[:60], inp)
        except (BudgetExceeded, LLMError, PriceUnknown) as e:
            res.stopped = f"{type(e).__name__}: {e}"
            break
        if ctx.stopped:
            res.stopped = ctx.stopped
            break
        save_card(ctx.db, item_id, 2, card, ctx.models.models[ctx.model or role.spec.model].id, ctx.tracer.run_id,
                  fallback=card.origin is None and not card.trail)
        res.done += 1
        if card.origin is not None:
            res.origin_found += 1
            d = next((t.depth for t in card.trail if norm_url(t.url) == norm_url(card.origin.url)), None) or 0
            res.depths[d] = res.depths.get(d, 0) + 1
        for v in card.verified:
            res.statuses[v.status] = res.statuses.get(v.status, 0) + 1
        res.traces.append({"input": inp.model_dump(), "card": card.model_dump(), "enforced": card.enforced,
                           "steps": tool_path(ctx.db, ctx.tracer.run_id, mark)})
    return res


def write_traces(traces: list[dict[str, Any]], out_dir: Path, command: str) -> list[Path]:
    """항목별 추적 경로(방문 URL, 깊이, 링크 종류, 멈춘 이유, 도구 호출 수)와 v1 ↔ v2 비교(COMMON 10장)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for t in traces:
        inp, card = t["input"], t["card"]
        v1 = inp["card_v1"]
        calls = [s for s in t["steps"] if not s["text"].startswith("finish")]
        L = [f"# it:{inp['item_id']} {inp['title']}", "", f"- 원래 글: {inp['url']} ({inp['source_name']})",
             f"- max_depth {inp['max_depth']}, 도구 호출 {len(calls)}회, 멈춘 이유: {card['log']}", "",
             "## 추적 경로", "", "| # | 도구 | 인자 | 깊이 | 결과 |", "|---|---|---|---|---|"]
        for i, s in enumerate(t["steps"], 1):
            name, _, args = s["text"].partition(": ")
            depth = (s["detail"] or {}).get("depth")
            L.append(f"| {i} | {name} | {args.replace('|', '/')[:100]} | {depth or '-'} | "
                     f"{(s['error'] or 'ok').replace('|', '/')[:100]} |")
        L += ["", "## 원래 글의 링크(종류)", ""] + [f"- [{'후보' if x['candidate'] else ' '}] {x['n']}. {x['kind']} {x['url']}"
                                                  for x in inp["links"]]
        L += ["", "## v1 ↔ v2", "", f"- v1 요약: {v1['summary']}", f"- v2 요약: {card['summary']}",
              f"- origin: {card['origin']}", "", "| 확인할 것 | v2 판정 | 원본 인용 |", "|---|---|---|"]
        quotes = {q["n"]: q["text"] for q in card["quotes"]}
        for c in inp["checks"]:
            v = next((x for x in card["verified"] if x["check_n"] == c["n"]), None)
            q = quotes.get(v["quote_n"], "") if v and v["quote_n"] else ""
            L.append(f"| {c['n']}. {c['text'].replace('|', '/')} | {v['status'] if v else '(빠짐)'} | {q.replace('|', '/')[:100]} |")
        if card["differences"]:
            L += ["", "## 다른 점", ""] + [f"- {d}" for d in card["differences"]]
        if t["enforced"]:
            L += ["", "## enforce(코드 규칙)", ""] + [f"- {e['field']}: {e['rule']}" for e in t["enforced"]]
        L += ["", f"재현: `{command}`", ""]
        p = out_dir / f"it{inp['item_id']}.md"
        p.write_text("\n".join(L), encoding="utf-8")
        paths.append(p)
    return paths


def queue_from_plan(plan: dict[str, Any]) -> list[tuple[int, int]]:
    return [(t["item_id"], t["max_depth"]) for t in plan.get("text_queue", [])]
