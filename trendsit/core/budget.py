"""예산 장치. 2달러 단계 상한과 스펙별 상한은 코드가 지킨다.

- 단계 기준값: 처음 실행할 때 /api/v1/key 의 usage(누적)를 data/budget_state.json에 저장
- 단계 사용액 = 현재 key usage - 기준값. 실행 시작마다 refresh()로 다시 조회
- 키 usage는 늦게 반영될 수 있어 실행 기록 합(전체 스펙)과 비교해 큰 쪽을 쓴다
- 그 사이에는 이번 프로세스에서 기록한 비용(add)을 더해 추적
- 호출 직전 예상 비용으로 스펙 상한, 단계 상한, 키 limit_remaining 초과를 막는다
"""

from __future__ import annotations

import json
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx

from .config import BudgetConfig, ConfigError, ModelSpec
from .db import DB, now_kst

PRICE_TTL_S = 24 * 3600


class BudgetExceeded(Exception):
    pass


class PriceUnknown(Exception):
    pass


def estimate_tokens(obj: Any) -> int:
    """입력 토큰 추정. 한국어는 글자당 토큰이 많아 보수적으로 2글자당 1토큰."""
    text = obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False)
    return len(text) // 2 + 1


def fetch_endpoints(model_id: str) -> list[dict[str, Any]]:
    url = f"https://openrouter.ai/api/v1/models/{model_id}/endpoints"
    r = httpx.get(url, timeout=20)
    r.raise_for_status()
    return r.json()["data"]["endpoints"]


class PriceBook:
    """모델(+제공사)의 토큰당 단가(달러). OpenRouter 공개 목록에서 읽고 하루 캐시."""

    def __init__(self, path: Path, fetch: Callable[[str], list[dict[str, Any]]] = fetch_endpoints):
        self.path = path
        self.fetch = fetch
        self.data: dict[str, Any] = json.loads(path.read_text()) if path.exists() else {}

    def price(self, spec: ModelSpec, base_url: str) -> tuple[float, float]:
        if "openrouter.ai" not in base_url or spec.id.endswith(":free"):
            return 0.0, 0.0  # 로컬(Ollama)과 무료 모델
        order = (spec.provider.order or []) if spec.provider else []
        quants = (spec.provider.quantizations or []) if spec.provider else []
        key = f"{spec.id}|{','.join(order)}|{','.join(quants)}"
        hit = self.data.get(key)
        if hit and time.time() - hit["at"] < PRICE_TTL_S:
            return hit["in"], hit["out"]
        try:
            endpoints = self.fetch(spec.id)
        except Exception as e:  # noqa: BLE001 - 네트워크 실패면 저장값이라도 쓴다
            if hit:
                return hit["in"], hit["out"]
            raise PriceUnknown(f"{spec.id}: 단가 조회 실패 ({e})") from e
        chosen = self._choose(endpoints, order, quants)
        pin, pout = float(chosen["pricing"]["prompt"]), float(chosen["pricing"]["completion"])
        self.data[key] = {"in": pin, "out": pout, "at": time.time()}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=1))
        return pin, pout

    @staticmethod
    def _choose(endpoints: list[dict[str, Any]], order: list[str], quants: list[str]) -> dict[str, Any]:
        """고정 제공사의 단가. 태그가 정확히 같은 행 → 같은 제공사 행 중 가장 비싼 것 → 전체 중 가장 비싼 것."""
        if not endpoints:
            raise PriceUnknown("제공사 목록이 비어 있음")

        def price(e: dict[str, Any]) -> float:
            return float(e["pricing"]["completion"])

        def quant_ok(e: dict[str, Any]) -> bool:
            return not quants or (e.get("quantization") or "") in quants

        if order:
            want = order[0].lower().replace(" ", "")
            exact = [e for e in endpoints if (e.get("tag") or "").lower() == want and quant_ok(e)]
            if exact:
                return exact[0]
            if "/" not in want:
                same = [e for e in endpoints if quant_ok(e) and (
                    (e.get("tag") or "").lower().split("/")[0] == want
                    or (e.get("provider_name") or "").lower().replace(" ", "") == want)]
                if same:
                    return max(same, key=price)
        # 고정 제공사를 못 찾으면 가장 비싼 단가로 보수적으로 잡는다
        return max(endpoints, key=price)


class Budget:
    def __init__(self, cfg: BudgetConfig, spec: str, db: DB, state_path: Path,
                 key_status: Callable[[], dict[str, Any]] | None, prices: PriceBook):
        self.cfg, self.spec, self.db, self.state_path = cfg, spec, db, state_path
        self.key_status = key_status
        self.prices = prices
        if spec not in cfg.specs:  # 상한 없는 스펙(오타 포함)으로는 실행하지 않는다
            raise ConfigError("budget.yaml", "specs", f"스펙 '{spec}'의 상한이 없음 (있는 스펙: {', '.join(cfg.specs)})")
        self.spec_cap: float = cfg.specs[spec]
        self.session_cost = 0.0
        self.phase_used_at_refresh = 0.0
        self.spec_spent_at_refresh = 0.0
        self.limit_remaining: float | None = None
        self.key_phase_used: float | None = None
        self.source = "none"
        self.warnings: list[str] = []

    # ---------- 상태 ----------
    def _state(self) -> dict[str, Any]:
        return json.loads(self.state_path.read_text()) if self.state_path.exists() else {}

    def _save_state(self, state: dict[str, Any]) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(state, ensure_ascii=False, indent=1))

    @property
    def baseline(self) -> float | None:
        return self._state().get("phase_baseline_usd")

    def refresh(self) -> dict[str, Any]:
        """실행 시작, eval 시작, 큰 실행 전에 부른다. 키 사용량으로 단계 사용액을 다시 맞춘다."""
        self.spec_spent_at_refresh = self.db.spent(self.spec)
        self.session_cost = 0.0
        status: dict[str, Any] | None = None
        if self.key_status is not None:
            try:
                status = self.key_status()
            except Exception as e:  # noqa: BLE001
                self.warnings.append(f"키 사용량 조회 실패, 실행 기록 합으로 추적: {e}")
        state = self._state()
        if status is not None:
            if "phase_baseline_usd" not in state:
                state.update(phase=self.cfg.phase, phase_baseline_usd=float(status["usage"]),
                             recorded_at=now_kst(), limit_remaining_at_baseline=status.get("limit_remaining"))
                self._save_state(state)
            # 키 usage는 몇 분 늦게 반영된다. 실행 기록 합보다 작으면 기록 합을 쓴다(보수적)
            self.key_phase_used = float(status["usage"]) - state["phase_baseline_usd"]
            self.phase_used_at_refresh = max(self.key_phase_used, self.db.spent())
            self.limit_remaining = status.get("limit_remaining")
            self.source = "key"
        else:
            self.phase_used_at_refresh = self.db.spent()
            self.limit_remaining = None
            self.source = "records"
            if self.key_status is not None and not self.warnings:
                self.warnings.append("키 사용량 조회 불가, 실행 기록 합으로 추적")
        for w in self.warnings:
            print(f"[budget] 경고: {w}", file=sys.stderr)
        return {"phase_used": self.phase_used_at_refresh, "limit_remaining": self.limit_remaining,
                "baseline": state.get("phase_baseline_usd"), "source": self.source}

    @property
    def spec_spent(self) -> float:
        return self.spec_spent_at_refresh + self.session_cost

    @property
    def phase_used(self) -> float:
        return self.phase_used_at_refresh + self.session_cost

    # ---------- 호출 전후 ----------
    def estimate(self, spec: ModelSpec, base_url: str, body: dict[str, Any]) -> float:
        pin, pout = self.prices.price(spec, base_url)
        tokens_in = estimate_tokens(body.get("messages")) + estimate_tokens(body.get("tools") or "")
        tokens_in += estimate_tokens(body.get("response_format") or "")
        tokens_out = int(body.get("max_tokens") or 0)
        reasoning = body.get("reasoning") or {}
        tokens_out += int(reasoning.get("max_tokens") or 0)
        return tokens_in * pin + tokens_out * pout

    def check(self, estimate: float, attempted: str) -> None:
        if self.spec_spent + estimate > self.spec_cap:
            raise BudgetExceeded(
                f"스펙 {self.spec} 상한 초과: 누적 ${self.spec_spent:.4f} + 예상 ${estimate:.4f} "
                f"> 상한 ${self.spec_cap:.2f} (시도: {attempted})")
        if self.phase_used + estimate > self.cfg.phase_total_usd:
            raise BudgetExceeded(
                f"단계 상한 초과: 사용 ${self.phase_used:.4f} + 예상 ${estimate:.4f} "
                f"> 상한 ${self.cfg.phase_total_usd:.2f} (시도: {attempted})")
        if self.limit_remaining is not None and self.limit_remaining - self.session_cost < estimate:
            raise BudgetExceeded(
                f"키 남은 한도 부족: 남음 ${self.limit_remaining - self.session_cost:.4f} "
                f"< 예상 ${estimate:.4f} (시도: {attempted})")

    def add(self, cost: float) -> None:
        self.session_cost += cost
