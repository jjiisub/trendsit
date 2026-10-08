"""M2: RoleOutput.enforce 훅(step detail, eval 전·후 기록, repo_oneliner 200자 규칙). M4: 도구 인자 거부 메시지의 칸 경로."""

import json
from typing import Literal

import pytest
from pydantic import BaseModel, ConfigDict

from tests.conftest import FakeTransport, make_ctx, response
from trendsit.core.agent import AgentState, DepthTracker, execute_tool
from trendsit.core.artifacts import (
    README_THIN_CHARS,
    LookupAnswer,
    RepoOneliner,
    RepoOnelinerInput,
    apply_enforce,
)
from trendsit.core.role import load_role, run_role
from trendsit.tools import TOOLS, ToolOutput
from trendsit.tools.registry import tool

THIN = {"full_name": "Python3WebSpider/Images360", "description": "Download Images From 360 Using Scrapy",
        "readme_head": "# Images360\n\nDownload Images From 360 Using Scrapy"}
RICH = {"full_name": "encode/httpx", "description": "HTTP client",
        "readme_head": "HTTPX is a fully featured HTTP client library for Python 3. " * 6}


def oneliner(attention=False):
    return RepoOneliner(basis="Download Images From 360 Using Scrapy", oneliner="Scrapy 기반 360 이미지 수집 스크립트",
                        log="README 근거", attention=attention)


def test_base_enforce_is_identity():
    out = LookupAnswer(doc_id=None, log="x", attention=True)
    assert out.enforce(None, None) is out and out.enforced == [] and out.raw_dump() == out.model_dump()


def test_repo_oneliner_thin_readme_forces_attention():
    inp = RepoOnelinerInput.model_validate(THIN)
    assert len(inp.readme_head.text) < README_THIN_CHARS
    fixed = apply_enforce(oneliner(attention=False), inp, None)
    assert fixed.attention is True
    assert fixed.enforced == [{"field": "attention", "before": False, "after": True,
                               "rule": f"README 본문 {README_THIN_CHARS}자 미만", "owned": True}]
    assert fixed.raw_dump()["attention"] is False  # 원래 출력 보존
    # 이미 true면 바꾼 것이 없음
    assert apply_enforce(oneliner(attention=True), inp, None).enforced == []
    # README가 충분히 길면 모델 판단 그대로
    rich = RepoOnelinerInput.model_validate(RICH)
    assert apply_enforce(oneliner(attention=False), rich, None).attention is False


def test_run_role_records_enforced_in_step_detail(tmp_path, models):
    role = load_role("repo_oneliner", models)
    raw = oneliner(attention=False).model_dump()
    ctx = make_ctx(tmp_path, FakeTransport([response(json.dumps(raw, ensure_ascii=False))]))
    out = run_role(role, RepoOnelinerInput.model_validate(THIN), ctx)
    assert out.attention is True
    step = ctx.db.step(ctx.last_step_id)
    detail = json.loads(step["detail"])
    assert detail["enforced"][0]["field"] == "attention" and step["attention"] == 1
    assert json.loads(step["output"])["attention"] is True  # 저장되는 것은 enforce 후


def test_eval_records_raw_and_enforced(tmp_path, monkeypatch):
    from eval import run_eval

    fx_dir = tmp_path / "fixtures" / "repo_oneliner"
    fx_dir.mkdir(parents=True)
    expect = {"max_len": 60, "must_include_any": ["이미지"], "attention": True}
    (fx_dir / "Images360.json").write_text(json.dumps({"input": THIN, "expect": expect}), encoding="utf-8")
    monkeypatch.setattr(run_eval, "FIXTURES", tmp_path / "fixtures")
    monkeypatch.setattr(run_eval, "REPORTS", tmp_path / "reports")
    monkeypatch.setattr(run_eval, "ROOT", tmp_path)
    raw = oneliner(attention=False).model_dump()
    ctx = make_ctx(tmp_path, FakeTransport([response(json.dumps(raw, ensure_ascii=False))]))
    monkeypatch.setattr(run_eval.graders, "llm_grade", lambda *a: {"verdicts": {}, "scores": {}, "missing": []})
    report = run_eval._evaluate(ctx, "repo_oneliner", None, None, "test")
    rec = report["results"][0]
    assert rec["output"]["attention"] is False and rec["enforced_output"]["attention"] is True
    # 설계 결정 Q1: attention은 코드 소유 칸이라 통과 판정은 enforce 후 값, 모델 일치율은 따로
    assert rec["graded_output"]["attention"] is True and rec["code"]["passed"] is True
    assert rec["code_enforced"]["passed"] is True
    assert report["summary"]["code_pass"] == 1 and report["summary"]["code_pass_enforced"] == 1
    assert report["summary"]["model_agreement"] == {"attention": "0/1"}


def test_graded_output_overrides_owned_fields_only():
    """코드 소유 변경만 덮고 품질 정리는 원래 출력 그대로(설계 결정 Q1). owned 없는 옛 기록은 ENFORCED_FIELDS로."""
    raw = {"oneliner": "x", "basis": "", "log": "l", "attention": False}
    enforced = [{"field": "attention", "before": False, "after": True, "rule": "r"},
                {"field": "basis", "before": "", "after": "b", "rule": "q", "owned": False},
                {"field": "oneliner", "before": "x", "after": "y", "rule": "o", "owned": True}]
    graded = RepoOneliner.graded_output(raw, enforced)
    assert graded == {"oneliner": "y", "basis": "", "log": "l", "attention": True}
    assert raw["attention"] is False  # 원래 출력은 건드리지 않음


def test_regrade_saved_report(tmp_path, monkeypatch):
    """저장된 결과를 다시 채점: 새로 통과한 항목만 judge를 부르고 새 리포트를 쓴다."""
    from eval import graders, run_eval

    monkeypatch.setattr(run_eval, "FIXTURES", tmp_path / "fixtures")
    monkeypatch.setattr(run_eval, "REPORTS", tmp_path / "reports")
    monkeypatch.setattr(run_eval, "ROOT", tmp_path)
    (tmp_path / "fixtures" / "repo_oneliner").mkdir(parents=True)
    (tmp_path / "fixtures" / "repo_oneliner" / "Images360.json").write_text("{}", encoding="utf-8")
    (tmp_path / "reports" / "eval").mkdir(parents=True)
    expect = {"max_len": 60, "attention": True}
    raw = oneliner(attention=False).model_dump()
    old = {"role": "repo_oneliner", "model_alias": "generate", "model_id": "m", "prompt_hash": "h", "spec": "S2",
           "run_id": 1, "at": "2026-10-08T10:00:00+09:00", "note": None, "stopped": None, "limit": None,
           "cost_usd": 0.01, "summary": {}, "results": [{
               "id": "Images360", "input": THIN, "expect": expect, "output": raw, "error": None,
               "code": {"passed": False}, "enforced": [{"field": "attention", "before": False, "after": True,
                                                         "rule": "README 본문 200자 미만"}]}]}
    src = tmp_path / "old.json"
    src.write_text(json.dumps(old, ensure_ascii=False), encoding="utf-8")
    calls = []

    def fake_llm(role, inp, out, ctx):
        calls.append(out["attention"])
        return {"verdicts": {q: {"verdict": "pass", "critique": "c"} for q in ("Q1", "Q2", "Q3")},
                "scores": {}, "missing": []}

    monkeypatch.setattr(graders, "llm_grade", fake_llm)
    monkeypatch.setattr(run_eval, "open_ctx", lambda *a, **k: make_ctx(tmp_path, FakeTransport([])))
    rep = run_eval.regrade(src)
    assert calls == [True]  # judge는 채점 보기(enforce 후 attention)를 본다
    assert rep["summary"]["code_pass"] == 1 and rep["summary"]["passed"] is True
    assert rep["summary"]["model_agreement"] == {"attention": "0/1"}
    assert rep["regraded_from"] and rep["prompt_hash"] == "h"


# ---------- M4 ----------
class Origin(BaseModel):
    kind: Literal["paper", "blog"]
    url: str


class NestedArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    origin: Origin
    pages: list[int]


@pytest.fixture
def nested_tool():
    @tool(NestedArgs)
    def nested_probe(args: NestedArgs, state) -> ToolOutput:
        """테스트용 중첩 인자 도구."""
        return ToolOutput(content="ok")

    yield "nested_probe"
    TOOLS.pop("nested_probe", None)


def run_tool(name, args):
    state = AgentState(depth=DepthTracker(None))
    return execute_tool(name, json.dumps(args), {name}, state)


def test_nested_arg_error_names_field_path(nested_tool):
    content, info = run_tool(nested_tool, {"origin": {"kind": "news", "url": "x"}, "pages": [1, "a"]})
    assert content.startswith("오류: 인자 형식 오류")
    assert "origin.kind: 허용 값 아님" in content and "'paper'" in content
    assert "pages[1]: 정수여야 함" in content
    content, _ = run_tool(nested_tool, {"origin": {"url": "x"}, "pages": [], "extra": 1})
    assert "origin.kind: 필수 칸 없음" in content and "extra: 없는 칸" in content


def test_bad_json_args_rejected(nested_tool):
    state = AgentState(depth=DepthTracker(None))
    content, info = execute_tool(nested_tool, "{not json", {nested_tool}, state)
    assert content.startswith("오류: 인자 형식 오류: JSON이 아님") and info["error"]
