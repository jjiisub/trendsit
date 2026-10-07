"""도구 등록. 함수 + pydantic 인자 모델 + 설명(docstring, 모델이 읽음)."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from ..core.llm import strict_json_schema


class ToolOutput(BaseModel):
    content: Any
    links: list[str] = []  # 이 결과에서 이어지는 문서 id (깊이 추적용)
    roots: list[str] = []  # 깊이 1로 시작할 수 있는 문서 id


class ToolRejected(Exception):
    """허용 밖 호출, 깊이 초과 등. 오류 내용을 모델에게 결과로 돌려준다."""


@dataclass
class Tool:
    name: str
    fn: Callable[[Any, Any], ToolOutput]
    args: type[BaseModel]
    description: str
    depth_target: str | None  # 이 인자가 가리키는 문서를 parent에서 한 단계 더 들어간 것으로 센다

    def schema(self) -> dict[str, Any]:
        return {"type": "function",
                "function": {"name": self.name, "description": self.description,
                             "parameters": strict_json_schema(self.args)}}


TOOLS: dict[str, Tool] = {}


def tool(args: type[BaseModel], depth_target: str | None = None) -> Callable[[Callable], Callable]:
    def register(fn: Callable) -> Callable:
        TOOLS[fn.__name__] = Tool(fn.__name__, fn, args, inspect.getdoc(fn) or "", depth_target)
        return fn

    return register
