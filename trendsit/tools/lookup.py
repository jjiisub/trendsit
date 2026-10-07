"""lookup_agent(테스트용)의 가짜 도구. 로컬 문서 묶음에서 링크를 따라 읽는다."""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .registry import ToolOutput, ToolRejected, tool

DOCS_PATH = Path(__file__).with_name("lookup_docs.json")


@cache
def corpus() -> dict[str, Any]:
    return json.loads(DOCS_PATH.read_text(encoding="utf-8"))


class ListDocsArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    parent: str | None = Field(description="링크 목록을 볼 문서 id. null이면 시작 문서 목록")


class ReadDocArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(description="읽을 문서 id")
    parent: str | None = Field(description="이 문서로 이어지는 링크가 있던 문서 id. 시작 문서를 읽을 때는 null")


@tool(ListDocsArgs)
def list_docs(args: ListDocsArgs, state: Any) -> ToolOutput:
    """문서 id와 제목 목록. parent가 null이면 시작 문서들, 문서 id를 주면 그 문서가 링크한 문서들. 본문은 read_doc으로 읽는다."""
    c = corpus()
    if args.parent is None:
        ids = c["roots"]
        return ToolOutput(content=[{"id": i, "title": c["docs"][i]["title"]} for i in ids], roots=ids)
    if args.parent not in state.depth.depth:
        raise ToolRejected(f"'{args.parent}'를 아직 읽지 않음. read_doc으로 먼저 읽을 것")
    ids = c["docs"][args.parent]["links"]
    return ToolOutput(content=[{"id": i, "title": c["docs"][i]["title"]} for i in ids])


@tool(ReadDocArgs, depth_target="id")
def read_doc(args: ReadDocArgs, state: Any) -> ToolOutput:
    """문서 하나의 본문과 다음 링크(문서 id 목록). 링크를 따라갈 때는 parent에 지금 문서 id를 넣는다."""
    doc = corpus()["docs"].get(args.id)
    if doc is None:
        raise ToolRejected(f"없는 문서 id: {args.id}")
    return ToolOutput(content={"id": args.id, "title": doc["title"], "body": doc["body"], "links": doc["links"]},
                      links=doc["links"])
