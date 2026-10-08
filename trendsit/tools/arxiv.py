"""arxiv 도구(글 분석가): export.arxiv.org API로 논문 메타데이터와 초록. safe_fetch(api)로만."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote

import feedparser
from pydantic import BaseModel, ConfigDict, Field

from .registry import ToolOutput, ToolRejected, tool
from .web import remember, resources

API = "https://export.arxiv.org/api/query"
ARXIV_ID = re.compile(r"(\d{4}\.\d{4,5})(v\d+)?")


class ArxivArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=3, description="arXiv id(예: 2501.01234) 또는 논문 제목")


@tool(ArxivArgs)
def arxiv(args: ArxivArgs, state: Any) -> ToolOutput:
    """arXiv 논문: 제목, 저자, 날짜, 초록, abs 링크(최대 3건). 초록 문장은 인용 근거로 쓸 수 있다.
    언제 쓰나: 글이 논문을 언급하거나 arxiv.org 링크가 있을 때(링크를 fetch_page로 여는 것보다 정확).
    언제 쓰지 않나: 논문이 아닌 블로그·보도자료.
    인자 예: {"query": "2501.01234"} 또는 {"query": "Scaling test-time compute"}"""
    m = ARXIV_ID.search(args.query)
    url = f"{API}?id_list={m.group(1)}" if m else f"{API}?search_query=ti:%22{quote(args.query)}%22&max_results=3"
    r = resources(state)["fetcher"].fetch(url, kind="api")
    if not r.ok or not r.text:
        raise ToolRejected(f"arXiv API 실패: {r.error or '빈 응답'}")
    feed = feedparser.parse(r.text)
    out = []
    for e in feed.entries[:3]:
        abs_url = e.get("id", "")
        abstract = " ".join((e.get("summary") or "").split())
        remember(state, abs_url, f"{e.get('title', '')}\n{abstract}")
        out.append({"title": " ".join((e.get("title") or "").split()), "authors": [a.get("name") for a in e.get("authors", [])][:8],
                    "published": (e.get("published") or "")[:10], "abs_url": abs_url, "abstract": abstract[:2000]})
    if not out:
        return ToolOutput(content={"query": args.query, "results": [], "note": "찾지 못함"})
    return ToolOutput(content={"query": args.query, "results": out})
