"""S3 공통 코어(agent.py): 입력별 허용 도구·깊이 상한, 항목당 도구 호출 상한(A10의 바탕). lookup_agent와 모의 전송으로."""

import json

from tests.conftest import FakeTransport, make_ctx, response
from trendsit.core.agent import run_agent
from trendsit.core.artifacts import LookupInput
from trendsit.core.role import load_role


def call(name, **args):
    return response(tool_calls=[(f"c-{name}-{json.dumps(args, sort_keys=True)}", name, args)])


def finish(doc_id=None):
    return call("finish", doc_id=doc_id, log="끝", attention=False)


class OnlyList(LookupInput):
    def tool_names(self, names):
        return [n for n in names if n == "list_docs"]


class Shallow(LookupInput):
    def depth_limit(self, default):
        return 1


def tool_steps(ctx):
    return [s for s in ctx.db.steps_of(ctx.tracer.run_id) if s["kind"] == "tool"]


def test_input_narrows_allowed_tools(tmp_path, models):
    role = load_role("lookup_agent", models)
    t = FakeTransport([call("read_doc", id="r1", parent=None), finish()])
    ctx = make_ctx(tmp_path, t)
    run_agent(role, OnlyList(question="q"), ctx)
    names = [x["function"]["name"] for x in t.bodies[0]["tools"]]
    assert names == ["list_docs", "finish"]  # 모델에게 보이는 도구도 좁아짐
    assert "허용되지 않은 도구 'read_doc'" in tool_steps(ctx)[0]["error"]


def test_input_depth_limit(tmp_path, models):
    role = load_role("lookup_agent", models)
    t = FakeTransport([call("list_docs", parent=None), call("read_doc", id="r1", parent=None),
                       call("read_doc", id="a2", parent="r1"), finish()])
    ctx = make_ctx(tmp_path, t)
    run_agent(role, Shallow(question="q"), ctx)
    assert "깊이 상한 초과" in tool_steps(ctx)[2]["error"]  # md는 3이지만 입력이 1로


def test_tool_call_cap_rejects_and_counts_down(tmp_path, models):
    role = load_role("lookup_agent", models)
    role.spec = role.spec.model_copy(update={"max_tool_calls": 2})
    t = FakeTransport([call("list_docs", parent=None), call("read_doc", id="r1", parent=None),
                       call("read_doc", id="r2", parent=None), finish("r1")])
    ctx = make_ctx(tmp_path, t)
    out = run_agent(role, LookupInput(question="q"), ctx)
    steps = tool_steps(ctx)
    assert steps[2]["text"] == "read_doc: 상한으로 거부" and "상한 2회" in steps[2]["error"]
    last_tool = [m for m in t.bodies[2]["messages"] if m["role"] == "tool"][-1]["content"]
    assert last_tool.endswith("[남은 도구 호출 0회]")
    assert out.doc_id == "r1"
