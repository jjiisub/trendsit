import json

import pytest

from tests.conftest import FakeKey, FakeTransport, make_ctx, response
from trendsit.core.artifacts import RepoOnelinerInput
from trendsit.core.budget import BudgetExceeded
from trendsit.core.cache import cache_key
from trendsit.core.role import load_role, run_role

INPUT = RepoOnelinerInput(full_name="a/b", readme_head="# B")
GOOD = json.dumps({"oneliner": "테스트용 도구", "log": "README 근거", "attention": False}, ensure_ascii=False)
MSG = [{"role": "user", "content": "hi"}]


# ---------- 캐시 키 ----------
def base_body():
    return {"model": "m", "provider": {"order": ["x"]}, "messages": MSG, "response_format": {"a": 1},
            "tools": None, "max_tokens": 10, "temperature": 0.2, "reasoning": {"enabled": False},
            "usage": {"include": True}}


def test_cache_key_stable_and_sensitive():
    k = cache_key(base_body())
    assert k == cache_key(base_body())
    for field, value in [("model", "m2"), ("provider", {"order": ["y"]}), ("messages", MSG * 2),
                         ("response_format", {"a": 2}), ("tools", [{"t": 1}]), ("max_tokens", 11),
                         ("temperature", 0.3), ("reasoning", {"effort": "low"})]:
        assert cache_key({**base_body(), field: value}) != k, field
    assert cache_key({**base_body(), "usage": None}) == k  # 회계용 칸은 키에 안 들어감


# ---------- A5: 캐시 적중이면 네트워크 0 ----------
def test_cache_hit_makes_no_network_call(tmp_path, models):
    t = FakeTransport([response(GOOD, cost=0.0005)])
    ctx = make_ctx(tmp_path, t)
    role = load_role("repo_oneliner", models)
    first = run_role(role, INPUT, ctx)
    second = run_role(role, INPUT, ctx)
    assert first == second and t.calls == 1
    s = ctx.db.steps_of(ctx.tracer.run_id)
    assert (s[0]["cache_hit"], s[0]["cost_usd"]) == (0, 0.0005)
    assert (s[1]["cache_hit"], s[1]["cost_usd"]) == (1, 0)


def test_no_cache_skips_read_but_refreshes(tmp_path, models):
    t = FakeTransport([response(GOOD), response(GOOD)])
    ctx = make_ctx(tmp_path, t)
    role = load_role("repo_oneliner", models)
    run_role(role, INPUT, ctx)
    ctx.no_cache = True
    run_role(role, INPUT, ctx)
    assert t.calls == 2


# ---------- A7: 예산 ----------
def test_spec_cap_blocks_before_call(tmp_path, models):
    t = FakeTransport([response(GOOD)])
    ctx = make_ctx(tmp_path, t, spec_cap=0.00001)
    with pytest.raises(BudgetExceeded, match="스펙 S0 상한"):
        run_role(load_role("repo_oneliner", models), INPUT, ctx)
    assert t.calls == 0


def test_estimate_uses_pinned_provider_price(tmp_path, models):
    ctx = make_ctx(tmp_path, FakeTransport())
    spec = models.models["generate"]
    body = ctx.llm.build_body("generate", MSG, max_tokens=1000)
    est = ctx.budget.estimate(spec, models.base_url("generate"), body)
    assert est == pytest.approx(1000 * 0.000001875 + (len(json.dumps(MSG)) // 2 + 1 + 1 + 1) * 0.00000015,
                                rel=0.05)
    assert ctx.budget.estimate(models.models["smoke"], models.base_url("smoke"), body) == 0


def test_phase_usage_from_key_baseline(tmp_path, models):
    key = FakeKey(usage=1.0)
    ctx = make_ctx(tmp_path, FakeTransport(), key=key)
    assert ctx.budget.baseline == 1.0 and ctx.budget.phase_used == 0
    key.usage = 1.5  # 다른 곳에서 쓴 사용량까지 반영
    info = ctx.budget.refresh()
    assert info["phase_used"] == pytest.approx(0.5) and ctx.budget.baseline == 1.0
    key.usage = 2.99
    ctx.budget.refresh()
    with pytest.raises(BudgetExceeded, match="단계 상한"):
        ctx.budget.check(0.02, "test")


def test_limit_remaining_blocks(tmp_path, models):
    t = FakeTransport([response(GOOD)])
    ctx = make_ctx(tmp_path, t, key=FakeKey(usage=0.1, limit_remaining=0.00001))
    with pytest.raises(BudgetExceeded, match="키 남은 한도"):
        run_role(load_role("repo_oneliner", models), INPUT, ctx)
    assert t.calls == 0


def test_key_failure_falls_back_to_records(tmp_path, models):
    key = FakeKey()
    key.fail = True
    ctx = make_ctx(tmp_path, FakeTransport(), key=key)
    assert ctx.budget.source == "records" and ctx.budget.limit_remaining is None
    assert ctx.budget.warnings


def test_session_cost_accumulates_into_spec_spent(tmp_path, models):
    t = FakeTransport([response(GOOD, cost=0.06), response(GOOD.replace("도구", "앱"), cost=0.06)])
    ctx = make_ctx(tmp_path, t, spec_cap=0.12)
    role = load_role("repo_oneliner", models)
    run_role(role, INPUT, ctx)
    run_role(role, RepoOnelinerInput(full_name="c/d", readme_head="# D"), ctx)
    assert ctx.budget.spec_spent == pytest.approx(0.12)
    with pytest.raises(BudgetExceeded):
        run_role(role, RepoOnelinerInput(full_name="e/f", readme_head="# F"), ctx)


# ---------- 비용 수집 ----------
def test_cost_falls_back_to_generation_lookup_then_estimate(tmp_path, models):
    role = load_role("repo_oneliner", models)
    t = FakeTransport([response(GOOD, cost=None)])
    ctx = make_ctx(tmp_path, t, generation_cost=lambda *a: 0.0042)
    run_role(role, INPUT, ctx)
    s = ctx.db.steps_of(ctx.tracer.run_id)[-1]
    assert (s["cost_usd"], s["cost_estimated"]) == (0.0042, 0)

    t2 = FakeTransport([response(GOOD, cost=None, tokens=(1000, 100))])
    ctx2 = make_ctx(tmp_path / "b", t2)
    run_role(role, INPUT, ctx2)
    s2 = ctx2.db.steps_of(ctx2.tracer.run_id)[-1]
    assert s2["cost_estimated"] == 1
    assert s2["cost_usd"] == pytest.approx(1000 * 0.00000015 + 100 * 0.000001875)


def test_price_matches_pinned_tier(tmp_path):
    from trendsit.core.budget import PriceBook
    from trendsit.core.config import ModelSpec

    eps = [{"provider_name": "Google AI Studio", "tag": "google-ai-studio", "pricing": {"prompt": "2", "completion": "2"}},
           {"provider_name": "Google AI Studio", "tag": "google-ai-studio/flex", "pricing": {"prompt": "1", "completion": "1"}}]
    book = PriceBook(tmp_path / "p.json", fetch=lambda _id: eps)
    flex = ModelSpec(id="g/x", provider={"order": ["google-ai-studio/flex"]})
    std = ModelSpec(id="g/y", provider={"order": ["google-ai-studio"]})
    unknown = ModelSpec(id="g/z", provider={"order": ["nobody"]})
    base = "https://openrouter.ai/api/v1"
    assert book.price(flex, base) == (1.0, 1.0)
    assert book.price(std, base) == (2.0, 2.0)
    assert book.price(unknown, base) == (2.0, 2.0)  # 못 찾으면 가장 비싼 단가


def test_lagging_key_usage_uses_records(tmp_path, models):
    key = FakeKey(usage=1.0)
    t = FakeTransport([response(GOOD, cost=0.05)])
    ctx = make_ctx(tmp_path, t, key=key)
    run_role(load_role("repo_oneliner", models), INPUT, ctx)
    ctx.budget.refresh()  # 키 usage는 아직 1.0 그대로(반영 지연)
    assert ctx.budget.key_phase_used == 0 and ctx.budget.phase_used == pytest.approx(0.05)


def test_unknown_spec_is_refused(tmp_path):
    from trendsit.core.budget import Budget, PriceBook
    from trendsit.core.config import BudgetConfig, ConfigError
    from trendsit.core.db import DB

    cfg = BudgetConfig(phase="mvp", phase_total_usd=20, specs={"S0": 0.15})
    for spec in ("S1", "s0"):
        with pytest.raises(ConfigError, match="상한이 없음"):
            Budget(cfg, spec, DB(tmp_path / "t.db"), tmp_path / "b.json", None, PriceBook(tmp_path / "p.json"))
