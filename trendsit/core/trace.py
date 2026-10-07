"""실행 기록. 실행(run) 하나에 걸음(step)을 순서대로 남긴다."""

from __future__ import annotations

import secrets
from datetime import datetime
from typing import Any

from .db import DB, KST


def new_run_id(kind: str) -> str:
    return f"{datetime.now(KST):%Y%m%d-%H%M%S}-{kind}-{secrets.token_hex(2)}"


class Tracer:
    def __init__(self, db: DB, kind: str, spec: str | None, note: str | None = None):
        self.db = db
        self.run_id = new_run_id(kind)
        db.insert_run(self.run_id, kind, spec, note)

    def step(self, *, kind: str, role: str | None = None, request: Any = None, response: Any = None,
             **fields: Any) -> int:
        step_id = self.db.insert_step(run_id=self.run_id, kind=kind, role=role, **fields)
        if request is not None:
            self.db.insert_llm_call(step_id, request, response)
        return step_id

    def finish(self, status: str = "ok") -> None:
        self.db.finish_run(self.run_id, status)
