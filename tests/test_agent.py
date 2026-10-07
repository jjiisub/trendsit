"""A8: lookup_agent 모의 테스트. 걸음 상한, 깊이 상한, 허용 밖 도구, 도구 호출 기록."""

import json

import pytest

from tests.conftest import FakeTransport, make_ctx, response
from trendsit.core import agent as agent_mod
from trendsit.core.agent import run_agent
from trendsit.core.artifacts import LookupInput
from trendsit.core.role import load_role

Q = LookupInput(question="숫자 4172가 처음 나오는 문서 id를 찾아라.")


def call(name, **args):
    return response(tool_calls=[(f"c-{name}-{json.dumps(args, sort_keys=True)}", name, args)])


def finish(doc_id, attention=False):
    return call("finish", doc_id=doc_id, log=f"{doc_id} 확인", attention=attention)


@pytest.fixture
def role(models):
    return load_role("lookup_agent", models)


def tool_steps(ctx):
    return [s for s in ctx.db.steps_of(ctx.tracer.run_id) if s["kind"] == "tool"]


def tool_messages(t, i):
    return [m for m in t.bodies[i]["messages"] if m["role"] == "tool"]


def test_finds_answer_within_depth(tmp_path, role):
    t = FakeTransport([call("list_docs", parent=None), call("read_doc", id="r1", parent=None),
                       call("read_doc", id="a2", parent="r1"), call("read_doc", id="a3", parent="a2"),
                       finish("a3")])
    ctx = make_ctx(tmp_path, t)
    out = run_agent(role, Q, ctx)
    assert out.doc_id == "a3" and out.attention is False
    steps = tool_steps(ctx)
    assert [s["text"].split(":")[0] for s in steps] == ["list_docs", "read_doc", "read_doc", "read_doc", "finish"]
    assert json.loads(steps[3]["detail"])["depth"] == 3
    last = ctx.db.steps_of(ctx.tracer.run_id)[-1]
    assert last["kind"] == "code" and last["text"] == "a3 확인"
    # 도구 결과는 <data>로 감싸 전달
    assert tool_messages(t, 2)[-1]["content"].startswith("<data>")
    # 기록된 요청은 호출 시점의 메시지만 담는다(재생용)
    call3 = ctx.db.llm_call(ctx.db.steps_of(ctx.tracer.run_id)[0]["id"])
    assert len(call3["request"]["body"]["messages"]) == 2


def test_depth_four_is_rejected(tmp_path, role):
    t = FakeTransport([call("list_docs", parent=None), call("read_doc", id="r1", parent=None),
                       call("read_doc", id="a2", parent="r1"), call("read_doc", id="a3", parent="a2"),
                       call("read_doc", id="a4", parent="a3"), finish(None, attention=True)])
    ctx = make_ctx(tmp_path, t)
    out = run_agent(role, Q, ctx)
    assert out.doc_id is None
    rejected = tool_steps(ctx)[4]
    assert "깊이 상한 초과" in rejected["error"] and rejected["attention"] == 1
    assert "9051" not in json.dumps(t.bodies[5]["messages"], ensure_ascii=False)  # a4 본문은 전달되지 않음
    assert tool_messages(t, 5)[-1]["content"].startswith("오류: 깊이 상한 초과")


def test_depth_cannot_be_bypassed_without_parent(tmp_path, role):
    t = FakeTransport([call("read_doc", id="a4", parent=None), call("read_doc", id="a4", parent="r1"),
                       finish(None, attention=True)])
    ctx = make_ctx(tmp_path, t)
    run_agent(role, Q, ctx)
    errors = [s["error"] for s in tool_steps(ctx)[:2]]
    assert "시작 문서가 아님" in errors[0]
    assert "아직 읽지 않음" in errors[1]


def test_disallowed_tool_is_rejected(tmp_path, role):
    t = FakeTransport([call("delete_all_docs"), call("fetch_page", url="http://127.0.0.1"), finish("r1")])
    ctx = make_ctx(tmp_path, t)
    run_agent(role, Q, ctx)
    steps = tool_steps(ctx)
    assert "허용되지 않은 도구 'delete_all_docs'" in steps[0]["error"]
    assert "허용되지 않은 도구 'fetch_page'" in steps[1]["error"]
    assert all(s["kind"] == "tool" for s in steps)
    # 모델에게 보이는 도구는 역할 md의 tools + finish 뿐
    names = [x["function"]["name"] for x in t.bodies[0]["tools"]]
    assert names == ["list_docs", "read_doc", "finish"]


def test_max_steps_returns_fallback(tmp_path, role):
    t = FakeTransport([call("list_docs", parent=None) for _ in range(role.spec.max_steps)])
    ctx = make_ctx(tmp_path, t)
    out = run_agent(role, Q, ctx)
    assert out.doc_id is None and out.attention is True and "걸음 상한" in out.log
    assert t.calls == role.spec.max_steps
    assert len(tool_steps(ctx)) == role.spec.max_steps


def test_long_tool_result_is_truncated(tmp_path, role, monkeypatch):
    monkeypatch.setattr(agent_mod, "TOOL_RESULT_LIMIT", 30)
    t = FakeTransport([call("list_docs", parent=None), call("read_doc", id="r1", parent=None), finish("r1")])
    ctx = make_ctx(tmp_path, t)
    run_agent(role, Q, ctx)
    assert "[잘림: 전체" in tool_messages(t, 2)[-1]["content"]
    assert json.loads(tool_steps(ctx)[1]["detail"])["truncated"] is True


def test_invalid_finish_is_returned_as_error(tmp_path, role):
    t = FakeTransport([call("finish", doc_id="r1"), finish("r1")])  # log 빠짐
    ctx = make_ctx(tmp_path, t)
    out = run_agent(role, Q, ctx)
    assert out.doc_id == "r1"
    assert tool_steps(ctx)[0]["error"].startswith("오류: 최종 답이 스키마")


def test_budget_exceeded_returns_fallback_without_call(tmp_path, role, models):
    pricey = load_role("lookup_agent", models)
    ctx = make_ctx(tmp_path, FakeTransport(), spec_cap=0.0000001, model="generate")
    out = run_agent(pricey, Q, ctx)
    assert out.attention is True and "예산 초과" in out.log
    assert ctx.llm.network_calls == 0
