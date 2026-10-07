"""run_agent: 도구 루프. 허용 도구, 걸음 상한, 깊이 상한, 예산은 코드가 지킨다."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from ..tools import TOOLS, ToolOutput, ToolRejected
from .artifacts import RoleInput, RoleOutput
from .budget import BudgetExceeded
from .llm import parse_json_output, strict_json_schema
from .role import Role, initial_messages, record_llm, wrap_data

if TYPE_CHECKING:
    from .context import Ctx

TOOL_RESULT_LIMIT = 3000
FINISH = "finish"


class DepthTracker:
    """문서마다 깊이를 기록한다. 시작 문서 = 1, 읽은 문서가 링크한 문서 = 출발 문서 + 1.

    모델이 준 parent만 믿지 않는다. parent를 실제로 읽었고 그 문서에 target 링크가 있을 때만 이어진 것으로 센다.
    """

    def __init__(self, max_depth: int | None):
        self.max_depth = max_depth
        self.roots: set[str] = set()
        self.depth: dict[str, int] = {}
        self.links: dict[str, set[str]] = {}

    def resolve(self, target: str, parent: str | None) -> int:
        if target in self.roots:
            return 1
        if parent is None:
            raise ToolRejected(f"'{target}'는 시작 문서가 아님. 링크를 따라갈 때는 parent에 출발 문서 id를 넣을 것")
        if parent not in self.depth:
            raise ToolRejected(f"parent '{parent}'를 아직 읽지 않음")
        if target not in self.links.get(parent, set()):
            raise ToolRejected(f"'{parent}'에 '{target}'로 가는 링크 없음")
        d = self.depth[parent] + 1
        if self.max_depth is not None and d > self.max_depth:
            raise ToolRejected(f"깊이 상한 초과: '{target}'는 깊이 {d}, 상한 {self.max_depth}. 더 따라가지 말 것")
        return d

    def visited(self, target: str, depth: int, links: list[str]) -> None:
        self.depth[target] = min(depth, self.depth.get(target, depth))
        self.links.setdefault(target, set()).update(links)


@dataclass
class AgentState:
    depth: DepthTracker
    tool_calls: int = 0
    rejected: list[str] = field(default_factory=list)


def _args_summary(args: dict[str, Any]) -> str:
    return ", ".join(f"{k}={v}" for k, v in args.items())[:200]


def _tool_message(call_id: str, content: str) -> dict[str, Any]:
    return {"role": "tool", "tool_call_id": call_id, "content": content}


def execute_tool(name: str, raw_args: str, allowed: set[str], state: AgentState) -> tuple[str, dict[str, Any]]:
    """도구 하나 실행. 결과 문자열(모델에게 줄 것)과 기록용 정보를 돌려준다. 거부도 결과로 돌려준다."""
    info: dict[str, Any] = {"name": name, "args": None, "error": None, "depth": None, "truncated": False}
    try:
        if name not in allowed:
            raise ToolRejected(f"허용되지 않은 도구 '{name}'. 사용 가능: {', '.join(sorted(allowed))}, {FINISH}")
        tool = TOOLS[name]
        try:
            args_dict = json.loads(raw_args or "{}")
            args = tool.args.model_validate(args_dict)
        except (json.JSONDecodeError, ValidationError) as e:
            raise ToolRejected(f"인자 형식 오류: {str(e)[:300]}") from e
        info["args"] = args.model_dump()
        depth = None
        if tool.depth_target:
            depth = state.depth.resolve(getattr(args, tool.depth_target), getattr(args, "parent", None))
            info["depth"] = depth
        out: ToolOutput = tool.fn(args, state)
        state.depth.roots.update(out.roots)
        if tool.depth_target and depth is not None:
            state.depth.visited(getattr(args, tool.depth_target), depth, out.links)
        text = out.content if isinstance(out.content, str) else json.dumps(out.content, ensure_ascii=False)
        if len(text) > TOOL_RESULT_LIMIT:
            info["truncated"] = True
            text = text[:TOOL_RESULT_LIMIT] + f"\n[잘림: 전체 {len(text)}자 중 앞 {TOOL_RESULT_LIMIT}자]"
        return wrap_data(text), info
    except ToolRejected as e:
        info["error"] = str(e)
        state.rejected.append(str(e))
        return f"오류: {e}", info


def run_agent(role: Role, inp: RoleInput, ctx: Ctx) -> RoleOutput:
    """종료: finish로 최종 답 제출 / max_steps 도달 / 예산 초과. 상한에 걸리면 역할의 대체 출력(attention=true)."""
    alias = ctx.model or role.spec.model
    allowed = set(role.spec.tools)
    finish_schema = {"type": "function", "function": {
        "name": FINISH,
        "description": "최종 답 제출. 답이 정해졌거나 더 볼 것이 없을 때 마지막에 한 번 호출한다.",
        "parameters": strict_json_schema(role.output_cls)}}
    tools = [TOOLS[n].schema() for n in role.spec.tools] + [finish_schema]
    messages = initial_messages(role, inp)
    state = AgentState(depth=DepthTracker(role.spec.max_depth))

    def finish_with(out: RoleOutput, how: str) -> RoleOutput:
        ctx.last_step_id = ctx.tracer.step(kind="code", role=role.name, text=out.log, attention=out.attention,
                                           output=out.model_dump(), detail={"end": how, "steps": step + 1})
        return out

    step = 0
    for step in range(role.spec.max_steps):
        try:
            res = ctx.llm.chat(alias, messages, tools=tools, max_tokens=role.spec.max_tokens,
                               temperature=role.spec.temperature, no_cache=ctx.no_cache)
        except BudgetExceeded as e:
            ctx.tracer.step(kind="code", role=role.name, text="예산 초과로 중단", attention=True, error=str(e))
            return finish_with(role.output_cls.fallback("예산 초과", inp), "budget")
        messages.append(res.assistant_message)

        if not res.tool_calls:
            parsed, err = parse_json_output(res.content, role.output_cls)
            record_llm(ctx, role, res, text="도구 호출 없이 응답", error=err, detail={"step": step + 1})
            if parsed is not None:
                return finish_with(parsed, "text")
            messages.append({"role": "user", "content": f"도구를 호출하거나 {FINISH}로 최종 답을 제출할 것."})
            continue

        names = ", ".join(tc["name"] or "?" for tc in res.tool_calls)
        record_llm(ctx, role, res, text=f"도구 호출: {names}", detail={"step": step + 1})
        final: RoleOutput | None = None
        for tc in res.tool_calls:
            if tc["name"] == FINISH:
                try:
                    final = role.output_cls.model_validate_json(tc["arguments"])
                    content = "제출 완료"
                except ValidationError as e:
                    content = f"오류: 최종 답이 스키마에 맞지 않음: {str(e)[:300]}"
                ctx.tracer.step(kind="tool", role=role.name, text=f"{FINISH}: 최종 답 제출",
                                error=None if final else content)
                messages.append(_tool_message(tc["id"], content))
                continue
            state.tool_calls += 1
            content, info = execute_tool(tc["name"] or "", tc["arguments"], allowed, state)
            ctx.tracer.step(kind="tool", role=role.name,
                            text=f"{tc['name']}: {_args_summary(info['args'] or {})}",
                            error=info["error"], attention=bool(info["error"]),
                            detail={k: info[k] for k in ("args", "depth", "truncated")})
            messages.append(_tool_message(tc["id"], content))
        if final is not None:
            return finish_with(final, "finish")

    return finish_with(role.output_cls.fallback(f"걸음 상한 {role.spec.max_steps} 도달", inp), "max_steps")
