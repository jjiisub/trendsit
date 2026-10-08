"""코드 소유 칸(ENFORCED_FIELDS, S4 설계 결정 D2-1): 그 칸만 enforce 후 값으로 통과 판정, 원래 출력 점수는 따로."""

from __future__ import annotations

import pytest

from eval import graders


@pytest.fixture
def fake_role(monkeypatch):
    role = "fake_owned"
    monkeypatch.setitem(graders.ENFORCED_FIELDS, role, ("pairs",))
    monkeypatch.setitem(graders.THRESHOLDS, role, {"code_pass_all": True})
    monkeypatch.setitem(graders.ROLE_CHECKS, role,
                        lambda inp, out, expect: [graders.check("쌍 2개 이하", len(out["pairs"]) <= 2),
                                                  graders.check("근거 3개 이하", len(out["ev"]) <= 3)])
    return role


def test_basis_output_swaps_only_owned_fields(fake_role):
    raw = {"pairs": [1, 2, 3], "ev": [1, 2, 3, 4], "log": "x"}
    enforced = {"pairs": [1], "ev": [1, 2, 3], "log": "x"}
    assert graders.basis_output(fake_role, raw, enforced) == {"pairs": [1], "ev": [1, 2, 3, 4], "log": "x"}
    assert graders.basis_output(fake_role, raw, None) == raw
    assert graders.basis_output("repo_oneliner", raw, enforced) == raw  # 선언 없는 역할은 그대로


def _rec(raw_ok: bool, basis_ok: bool, enforced_ok: bool) -> dict:
    return {"code": {"passed": raw_ok}, "code_basis": {"passed": basis_ok}, "code_enforced": {"passed": enforced_ok}}


def test_summary_uses_basis_for_verdict_and_keeps_raw_score(fake_role):
    results = [_rec(True, True, True), _rec(False, True, True), _rec(False, False, True)]
    s = graders.summarize(fake_role, results)
    assert (s["code_pass"], s["code_pass_basis"], s["code_pass_enforced"]) == (1, 2, 3)
    assert s["fail_reasons"] == ["코드 채점 통과 2/3(코드 소유 칸 pairs은 enforce 후)"]


def test_roles_without_owned_fields_unchanged():
    s = graders.summarize("lookup_agent", [{"code": {"passed": True}}, {"code": {"passed": False}}])
    assert s["code_pass_basis"] == s["code_pass"] == 1 and not s["passed"]
