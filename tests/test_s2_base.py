"""0단계 병행 개발 자리(COMMON 9장): 스펙별 스키마·명령 모듈 합치기. 없는 모듈은 건너뛰고, 모듈 안의 import 오류는 숨기지 않는다."""

import argparse
import sys
import types

import pytest

from trendsit import cli
from trendsit.core import artifacts


def test_missing_spec_modules_are_skipped():
    artifacts._merge("artifacts_no_such_spec")
    sub = argparse.ArgumentParser().add_subparsers()
    cli._register(sub, "cli_no_such_spec")


def test_spec_module_is_merged(monkeypatch):
    class FakeIn(artifacts.RoleInput):
        x: int

    mod = types.ModuleType("trendsit.core.artifacts_fake")
    mod.INPUTS = (FakeIn,)
    monkeypatch.setitem(sys.modules, "trendsit.core.artifacts_fake", mod)
    monkeypatch.setattr(artifacts, "INPUTS", dict(artifacts.INPUTS))
    artifacts._merge("artifacts_fake")
    assert artifacts.INPUTS["FakeIn"] is FakeIn


def test_broken_import_inside_module_is_not_hidden(monkeypatch):
    def boom(name, *a, **k):
        raise ModuleNotFoundError("No module named 'torch'", name="torch")

    monkeypatch.setattr("importlib.import_module", boom)
    with pytest.raises(ModuleNotFoundError):
        cli._register(argparse.ArgumentParser().add_subparsers(), "cli_text")


def test_same_name_from_two_modules_is_an_error(monkeypatch):
    class LookupInput(artifacts.RoleInput):  # 기존 이름과 겹치는 다른 클래스
        y: int

    mod = types.ModuleType("trendsit.core.artifacts_clash")
    mod.INPUTS = (LookupInput,)
    monkeypatch.setitem(sys.modules, "trendsit.core.artifacts_clash", mod)
    monkeypatch.setattr(artifacts, "INPUTS", dict(artifacts.INPUTS))
    with pytest.raises(ValueError, match="LookupInput"):
        artifacts._merge("artifacts_clash")


@pytest.mark.parametrize("module", ["trendsit.core.artifacts_text", "trendsit.core.artifacts_repo", "trendsit.deep.plan",
                                    "trendsit.deep.text_agent", "eval.graders_text", "trendsit.tools.web"])
def test_spec_modules_import_first(module):
    """진입점이 스키마 모듈부터 읽어도(순환 import) 모든 스키마가 등록된다."""
    import subprocess

    code = (f"import {module}\nfrom trendsit.core.artifacts import INPUTS, OUTPUTS\n"
            "assert {'ItemCardInput','PlanInput','TextAnalystInput','RepoAnalystInput'} <= set(INPUTS)\n"
            "assert {'ItemCardV1','ItemCardV2','RepoCard','CollectionPlan'} <= set(OUTPUTS)")
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-400:]
