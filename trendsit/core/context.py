"""실행 맥락: 설정, LLM 클라이언트, 예산, 실행 기록을 한 번에 묶는다."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

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
    stopped: str | None = None  # 예산 초과 등으로 대체 출력을 내고 멈춘 이유(실행 상태 stopped)
    resources: dict[str, Any] = field(default_factory=dict)  # 도구가 쓰는 자원(fetcher 등). 파이프라인이 넣는다


def budget_state_path(data_dir: Path | None) -> Path:
    """예산 기준값 파일. 기본 data 폴더를 쓰면 작업 폴더 밖 공용 위치(~/.config/trendsit/)에 둔다(S5 5.1-3).
    worktree나 다른 작업 폴더도 같은 기준값을 본다. 처음 옮길 때 기존 data/budget_state.json(10/7 기준값)을 그대로 복사."""
    if data_dir is not None:  # 테스트·임시 폴더는 그 안에
        return data_dir / "budget_state.json"
    shared = config.SECRET_FILE.parent / "budget_state.json"
    old = config.ROOT / "data" / "budget_state.json"
    if not shared.exists() and old.exists():
        shared.parent.mkdir(parents=True, exist_ok=True)
        shared.write_text(old.read_text())
    return shared


def open_ctx(kind: str | None, *, spec: str | None = None, no_cache: bool = False, model: str | None = None,
             note: str | None = None, data_dir: Path | None = None, transport: Transport | None = None,
             key_status: bool = True) -> Ctx:
    state_path = budget_state_path(data_dir)
    data_dir = data_dir or config.ROOT / "data"
    spec = config.current_spec(spec)
    models = config.load("models.yaml")
    budget_cfg = config.load("budget.yaml")
    db = DB(data_dir / "trendsit.db")
    llm = LLMClient(models, cache=Cache(data_dir / "cache"), transport=transport)
    budget = Budget(budget_cfg, spec, db, state_path,
                    key_status=llm.key_status if key_status else None,
                    prices=PriceBook(data_dir / "prices.json"))
    llm.budget = budget
    budget.refresh()
    if model is not None and model not in models.models:
        raise config.ConfigError("models.yaml", "models", f"없는 별칭 '{model}'")
    tracer = Tracer(db, kind, spec, note) if kind else None
    return Ctx(llm=llm, tracer=tracer, budget=budget, db=db, models=models, spec=spec,
               no_cache=no_cache, model=model)
