"""칠판 검색 도구(레포 분석가): 이번 주 글 카드 중 질의어가 나온 것."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .registry import ToolOutput, ToolRejected, tool

MAX_HITS = 5


class SearchArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=2, description="레포 이름, 제품 이름, 키워드. 예: ollama")


@tool(SearchArgs)
def search_items(args: SearchArgs, state: Any) -> ToolOutput:
    """이번 주 글 카드(입력 week_items) 중 제목, 요약, 엔티티에 질의어가 나온 글: id(it:), 제목, 요약 앞부분. 최대 5건.
    언제 쓰나: 이 레포를 다룬 글이 이번 주에 있는지(why_trending, related_item_ids 근거) 확인할 때.
    언제 쓰지 않나: 같은 질의어로 이미 찾았을 때.
    인자 예: {"query": "hermes-agent"}"""
    inp = getattr(state, "inp", None)
    items = getattr(inp, "week_items", None)
    if items is None:
        raise ToolRejected("이 역할에는 이번 주 글 목록이 없음")
    db = getattr(getattr(state, "ctx", None), "db", None)
    q = args.query.strip().lower()
    hits = []
    for it in items:
        card = {}
        if db is not None and it.id.startswith("it:"):
            row = db.conn.execute("SELECT card_json FROM item_cards WHERE item_id=? ORDER BY version DESC LIMIT 1",
                                  (int(it.id[3:]),)).fetchone()
            card = json.loads(row[0]) if row else {}
        hay = " ".join([it.title, card.get("summary", ""), *card.get("entities", [])]).lower()
        if q in hay:
            hits.append({"id": it.id, "title": it.title, "summary_head": card.get("summary", "")[:120]})
        if len(hits) >= MAX_HITS:
            break
    return ToolOutput(content={"query": args.query, "hits": hits} if hits else {"query": args.query, "hits": [],
                                                                               "note": "이번 주 글에 없음"})
