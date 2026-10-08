"""S2 2b 글 1차 요약: 입력 조립(ItemCardInput), 대상 고르기, 실행, 저장(item_cards version 1)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from .core import config
from .core.artifacts import Document
from .core.artifacts_text import ItemCardInput, ItemCardV1, KeywordRef, LinkRef, clipped_quotes
from .core.db import DB, now_kst

BODY_LIMIT = 6000  # 본문 상한(자). 문단 경계에서 자른다


def cut_body(text: str, limit: int = BODY_LIMIT) -> str:
    """limit자 안에서 문단 경계로 자른다. 첫 문단이 limit보다 길면 문장 끝(. ! ? 다.)에서, 그것도 없으면 limit에서."""
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    out = ""
    for para in re.split(r"\n\s*\n|\n", text):
        cand = f"{out}\n\n{para}" if out else para
        if len(cand) > limit:
            break
        out = cand
    if out:
        return out
    head = text[:limit]
    ends = [m.end() for m in re.finditer(r"[.!?。](\s|$)", head)]
    return head[:ends[-1]].strip() if ends else head


def build_input(db: DB, item_id: int, keywords: config.KeywordsConfig) -> ItemCardInput:
    row = db.conn.execute(
        "SELECT i.id, i.title, i.url, i.source_id, s.name AS source_name, s.kind AS source_kind, t.text AS body "
        "FROM items i LEFT JOIN sources s ON s.id = i.source_id LEFT JOIN item_texts t ON t.item_id = i.id "
        "WHERE i.id = ?", (item_id,)).fetchone()
    if row is None:
        raise KeyError(f"없는 항목 {item_id}")
    links = [LinkRef(n=n, url=r["url"], kind=r["kind"], anchor=(r["anchor"] or None), role=r["role"])
             for n, r in enumerate(db.conn.execute(
                 "SELECT url, kind, anchor, role FROM links WHERE item_id = ? ORDER BY id", (item_id,)), 1)]
    name = row["source_name"] or row["source_id"]
    return ItemCardInput(
        item_id=row["id"], title=row["title"] or "", source_name=name, source_kind=row["source_kind"] or "unknown",
        url=row["url"], body=Document(id=f"it:{row['id']}", source=name, title=row["title"], url=row["url"],
                                      text=cut_body(row["body"] or "")),
        links=links, keywords=[KeywordRef(id=k.id, name=k.canonical) for k in keywords.keywords])


def targets(db: DB, since: date | None, until: date | None, *, redo: bool = False, limit: int | None = None) -> list[int]:
    """임베딩 필터 keep이고 같은 URL 묶음의 대표인 글(기준 항목, 기준이 drop이면 keep 경유 항목 하나). 이미 v1이 있으면 건너뜀."""
    # 같은 URL 묶음은 keep인 멤버 하나만: 기준 항목이 keep이면 그것, 아니면 keep 경유 항목 중 id가 가장 작은 것
    sql = ("SELECT i.id FROM items i JOIN item_relevance r ON r.item_id = i.id AND r.decision = 'keep' "
           "WHERE i.channel = 'text' AND (i.id NOT IN (SELECT item_id FROM item_same_as) OR i.id = ("
           " SELECT MIN(s2.item_id) FROM item_same_as s2 JOIN item_relevance r2 ON r2.item_id = s2.item_id "
           " AND r2.decision = 'keep' WHERE s2.canonical_id = (SELECT canonical_id FROM item_same_as WHERE item_id = i.id)"
           " AND NOT EXISTS (SELECT 1 FROM item_relevance r3 WHERE r3.item_id = s2.canonical_id AND r3.decision = 'keep')))")
    args: list[Any] = []
    if since:
        sql += " AND i.day >= ?"
        args.append(since.isoformat())
    if until:
        sql += " AND i.day <= ?"
        args.append(until.isoformat())
    if not redo:
        sql += " AND i.id NOT IN (SELECT item_id FROM item_cards WHERE version = 1)"
    sql += " ORDER BY i.id"
    ids = [r[0] for r in db.conn.execute(sql, args)]
    return ids[:limit] if limit else ids


def save_card(db: DB, item_id: int, version: int, card: Any, model: str | None, run_id: str | None,
              fallback: bool = False) -> None:
    data = card.model_dump() if hasattr(card, "model_dump") else card
    with db.conn:
        db.conn.execute(
            "INSERT OR REPLACE INTO item_cards(item_id, version, card_json, model, run_id, created_at, fallback) "
            "VALUES (?,?,?,?,?,?,?)", (item_id, version, json.dumps(data, ensure_ascii=False), model, run_id,
                                       now_kst(), int(fallback)))


def load_card(db: DB, item_id: int, version: int = 1) -> dict[str, Any] | None:
    row = db.conn.execute("SELECT card_json FROM item_cards WHERE item_id=? AND version=?", (item_id, version)).fetchone()
    return json.loads(row[0]) if row else None


@dataclass
class SummarizeResult:
    run_id: str
    n: int = 0
    done: int = 0
    fallback: int = 0
    stopped: str | None = None
    relevance: dict[str, int] = field(default_factory=dict)
    needs_original: int = 0
    quotes: int = 0
    clipped: int = 0  # 설계 결정 Q6: 코드가 자른 인용 수(다시 볼 조건: 5% 초과)
    cost_usd: float = 0.0

    def summary(self) -> str:
        rel = ", ".join(f"{k} {v}" for k, v in sorted(self.relevance.items()))
        return (f"대상 {self.n}건 중 {self.done}건 요약(대체 {self.fallback}), relevance [{rel}], "
                f"원본 확인 필요 {self.needs_original}건, 잘린 인용 {self.clipped}/{self.quotes}"
                + (f"({self.clipped / self.quotes:.1%})" if self.quotes else "") + f", ${self.cost_usd:.4f}"
                + (f", 중단: {self.stopped}" if self.stopped else ""))


def run_summarize(ctx: Any, ids: list[int], keywords: config.KeywordsConfig) -> SummarizeResult:
    """대상마다 item_card 1회. 스키마 3회 실패면 대체 출력을 저장, 예산·제공사 오류면 멈춘다."""
    from .core.budget import BudgetExceeded, PriceUnknown
    from .core.llm import LLMError
    from .core.role import RoleFailed, load_role, run

    role = load_role("item_card", ctx.models)
    res = SummarizeResult(ctx.tracer.run_id, n=len(ids))
    before = ctx.budget.session_cost
    for item_id in ids:
        inp = build_input(ctx.db, item_id, keywords)
        try:
            card: ItemCardV1 = run(role, inp, ctx)  # type: ignore[assignment]
            fb = False
        except RoleFailed as e:
            card, fb = ItemCardV1.fallback(str(e)[:80], inp), True
            ctx.tracer.step(kind="code", role="item_card", text=card.log, attention=True, error=str(e))
        except (BudgetExceeded, LLMError, PriceUnknown) as e:
            res.stopped = f"{type(e).__name__}: {e}"
            break
        alias = ctx.model or role.spec.model
        save_card(ctx.db, item_id, 1, card, ctx.models.models[alias].id, ctx.tracer.run_id, fb)
        res.done += 1
        res.fallback += int(fb)
        res.relevance[card.relevance] = res.relevance.get(card.relevance, 0) + 1
        res.needs_original += int(card.needs_original)
        res.quotes += len(card.quotes)
        res.clipped += clipped_quotes(card.enforced)
    res.cost_usd = round(ctx.budget.session_cost - before, 6)
    return res
