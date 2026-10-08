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
                               "rule": f"README 본문 {README_THIN_CHARS}자 미만"}]
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
    report = run_eval._evaluate(ctx, "repo_oneliner", None, None, "test")
    rec = report["results"][0]
    assert rec["output"]["attention"] is False and rec["enforced_output"]["attention"] is True
    assert rec["code"]["passed"] is False  # 통과 판정은 원래 출력
    assert rec["code_enforced"]["passed"] is True
    assert report["summary"]["code_pass"] == 0 and report["summary"]["code_pass_enforced"] == 1


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
