"""실행 맥락: 설정, LLM 클라이언트, 예산, 실행 기록을 한 번에 묶는다."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import config
from .budget import Budget, PriceBook
from .cache import Cache
from .db import DB
from .llm import LLMClient, Transport
from .trace import Tracer


@dataclass
class Ctx:
    llm: LLMClient
    tracer: Tracer | None  # 조회 명령(cost)은 실행 기록을 만들지 않음
    budget: Budget
    db: DB
    models: config.ModelsConfig
    spec: str
    no_cache: bool = False
    model: str | None = None  # 별칭 덮어쓰기(--model)
    last_step_id: int | None = None


def open_ctx(kind: str | None, *, spec: str | None = None, no_cache: bool = False, model: str | None = None,
             note: str | None = None, data_dir: Path | None = None, transport: Transport | None = None,
             key_status: bool = True) -> Ctx:
    data_dir = data_dir or config.ROOT / "data"
    spec = config.current_spec(spec)
    models = config.load("models.yaml")
    budget_cfg = config.load("budget.yaml")
    db = DB(data_dir / "trendsit.db")
    llm = LLMClient(models, cache=Cache(data_dir / "cache"), transport=transport)
    budget = Budget(budget_cfg, spec, db, data_dir / "budget_state.json",
                    key_status=llm.key_status if key_status else None,
                    prices=PriceBook(data_dir / "prices.json"))
    llm.budget = budget
    budget.refresh()
    if model is not None and model not in models.models:
        raise config.ConfigError("models.yaml", "models", f"없는 별칭 '{model}'")
    tracer = Tracer(db, kind, spec, note) if kind else None
    return Ctx(llm=llm, tracer=tracer, budget=budget, db=db, models=models, spec=spec,
               no_cache=no_cache, model=model)
