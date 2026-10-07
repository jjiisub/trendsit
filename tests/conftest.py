"""테스트 공통: 네트워크 없이 도는 가짜 전송, 가짜 키 조회, 실행 맥락."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from trendsit.core import config
from trendsit.core.budget import Budget, PriceBook
from trendsit.core.cache import Cache
from trendsit.core.context import Ctx
from trendsit.core.db import DB
from trendsit.core.llm import LLMClient
from trendsit.core.trace import Tracer

ENDPOINTS = [
    {"provider_name": "DeepInfra", "tag": "deepinfra/bf16", "quantization": "bf16",
     "pricing": {"prompt": "0.00000015", "completion": "0.000001875"}},
    {"provider_name": "Cerebras", "tag": "cerebras/fp16", "quantization": "fp16",
     "pricing": {"prompt": "0.00000099", "completion": "0.000005"}},
]


def response(content: str | None = None, tool_calls: list[tuple[str, str, dict[str, Any]]] | None = None,
             cost: float | None = 0.0001, tokens: tuple[int, int] = (100, 20)) -> dict[str, Any]:
    msg: dict[str, Any] = {"role": "assistant", "content": content}
    if tool_calls:
        msg["tool_calls"] = [{"id": cid, "type": "function",
                              "function": {"name": name, "arguments": json.dumps(args, ensure_ascii=False)}}
                             for cid, name, args in tool_calls]
    usage: dict[str, Any] = {"prompt_tokens": tokens[0], "completion_tokens": tokens[1]}
    if cost is not None:
        usage["cost"] = cost
    return {"id": "gen-test", "model": "test/model", "provider": "TestProvider",
            "choices": [{"message": msg, "finish_reason": "stop"}], "usage": usage}


class FakeTransport:
    """미리 정한 응답을 순서대로 돌려주고, 받은 요청 본문을 기록한다."""

    def __init__(self, responses: list[dict[str, Any]] | None = None):
        self.responses = list(responses or [])
        self.bodies: list[dict[str, Any]] = []

    def __call__(self, body: dict[str, Any], base_url: str, api_key: str) -> dict[str, Any]:
        self.bodies.append(body)
        if not self.responses:
            raise AssertionError("예상보다 많은 네트워크 호출")
        return self.responses.pop(0)

    @property
    def calls(self) -> int:
        return len(self.bodies)


class FakeKey:
    def __init__(self, usage: float = 1.0, limit_remaining: float | None = 4.0):
        self.usage, self.limit_remaining, self.fail = usage, limit_remaining, False

    def __call__(self) -> dict[str, Any]:
        if self.fail:
            raise RuntimeError("network down")
        return {"usage": self.usage, "limit": 5.0, "limit_remaining": self.limit_remaining, "usage_daily": 0}


@pytest.fixture
def models() -> config.ModelsConfig:
    return config.load("models.yaml")


def make_ctx(tmp_path: Path, transport: FakeTransport, *, key: FakeKey | None = None, spec_cap: float = 0.15,
             phase_total: float = 2.0, model: str | None = None, generation_cost: Any = None) -> Ctx:
    models = config.load("models.yaml")
    budget_cfg = config.BudgetConfig(phase="mvp", phase_total_usd=phase_total, specs={"S0": spec_cap})
    db = DB(tmp_path / "trendsit.db")
    llm = LLMClient(models, cache=Cache(tmp_path / "cache"), transport=transport,
                    generation_cost=generation_cost or (lambda *a: None), secret=lambda _name: "test-key")
    budget = Budget(budget_cfg, "S0", db, tmp_path / "budget_state.json", key_status=key,
                    prices=PriceBook(tmp_path / "prices.json", fetch=lambda _id: ENDPOINTS))
    llm.budget = budget
    budget.refresh()
    return Ctx(llm=llm, tracer=Tracer(db, "test", "S0"), budget=budget, db=db, models=models, spec="S0",
               model=model)
