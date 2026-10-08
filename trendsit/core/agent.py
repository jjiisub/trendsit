"""run_agent: 도구 루프. 허용 도구, 걸음 상한, 깊이 상한, 예산은 코드가 지킨다."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ValidationError

from ..tools import TOOLS, ToolOutput, ToolRejected
from .artifacts import RoleInput, RoleOutput, apply_enforce
from .budget import BudgetExceeded
from .llm import LLMError, parse_json_output, strict_json_schema
from .render import render_data
from .role import Role, enforce_detail, initial_messages, record_llm

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
    ctx: Any = None  # 도구가 ctx.resources, ctx.db를 쓴다
    inp: Any = None
    extras: dict[str, Any] = field(default_factory=dict)  # 도구끼리 주고받는 실행 중 상태(가져온 페이지 등)


def _args_summary(args: dict[str, Any]) -> str:
    return ", ".join(f"{k}={v}" for k, v in args.items())[:200]


def _tool_message(call_id: str, content: str) -> dict[str, Any]:
    return {"role": "tool", "tool_call_id": call_id, "content": content}


NULL_STRINGS = {"None", "none", "null", "NULL", "Null", ""}


def nullable_fields(model: type[BaseModel]) -> set[str]:
    """스키마상 null을 허용하는 칸."""
    out = set()
    for name, f in model.model_fields.items():
        if f.annotation is None or type(None) in getattr(f.annotation, "__args__", ()):
            out.add(name)
    return out


def normalize_nulls(model: type[BaseModel], args: dict[str, Any]) -> list[str]:
    """null을 허용하는 칸에 들어온 "None", "null", ""를 null로 바꾼다(소형 모델의 흔한 실수). 바꾼 칸 이름을 돌려준다."""
    changed = []
    for name in nullable_fields(model):
        if isinstance(args.get(name), str) and args[name].strip() in NULL_STRINGS:
            args[name] = None
            changed.append(name)
    return sorted(changed)


ERROR_KO = {  # pydantic 오류 종류 → 모델에게 줄 짧은 설명
    "missing": "필수 칸 없음",
    "extra_forbidden": "없는 칸(스키마에 없는 이름)",
    "literal_error": "허용 값 아님",
    "enum": "허용 값 아님",
    "string_type": "문자열이어야 함",
    "int_type": "정수여야 함",
    "int_parsing": "정수여야 함",
    "bool_type": "true/false여야 함",
    "bool_parsing": "true/false여야 함",
    "list_type": "배열이어야 함",
    "dict_type": "객체여야 함",
    "model_type": "객체여야 함",
    "model_attributes_type": "객체여야 함",
    "greater_than_equal": "값이 너무 작음",
    "less_than_equal": "값이 너무 큼",
    "string_too_long": "문자열이 너무 김",
    "too_long": "항목이 너무 많음",
}


def _loc(loc: tuple[Any, ...]) -> str:
    """('origin', 'items', 0, 'kind') → origin.items[0].kind"""
    out = ""
    for part in loc:
        out += f"[{part}]" if isinstance(part, int) else (f".{part}" if out else str(part))
    return out or "(최상위)"


def validation_paths(e: ValidationError, limit: int = 5) -> str:
    """도구 인자 검증 오류를 칸 경로와 함께 한 줄씩(S1 리뷰 M4). 작은 모델이 중첩 인자를 고칠 수 있게."""
    parts = []
    for err in e.errors()[:limit]:
        reason = ERROR_KO.get(err["type"], err["msg"])
        ctx = err.get("ctx") or {}
        if "expected" in ctx:
            reason += f" (허용: {ctx['expected']})"
        elif err["type"] not in ("missing", "extra_forbidden") and "input" in err:
            reason += f" (받은 값: {json.dumps(err['input'], ensure_ascii=False, default=str)[:60]})"
        parts.append(f"{_loc(err['loc'])}: {reason}")
    more = len(e.errors()) - limit
    return "; ".join(parts) + (f" 외 {more}건" if more > 0 else "")


def execute_tool(name: str, raw_args: str, allowed: set[str], state: AgentState) -> tuple[str, dict[str, Any]]:
    """도구 하나 실행. 결과 문자열(모델에게 줄 것)과 기록용 정보를 돌려준다. 거부와 도구 실패도 결과로 돌려준다."""
    info: dict[str, Any] = {"name": name, "args": None, "error": None, "depth": None, "truncated": False,
                            "normalized": []}
    try:
        if name not in allowed:
            raise ToolRejected(f"허용되지 않은 도구 '{name}'. 사용 가능: {', '.join(sorted(allowed))}, {FINISH}")
        tool = TOOLS[name]
        try:
            args_dict = json.loads(raw_args or "{}")
            if isinstance(args_dict, dict):
                info["normalized"] = normalize_nulls(tool.args, args_dict)
            args = tool.args.model_validate(args_dict)
        except json.JSONDecodeError as e:
            raise ToolRejected(f"인자 형식 오류: JSON이 아님({e.msg}, {e.pos}번째 글자)") from e
        except ValidationError as e:
            raise ToolRejected(f"인자 형식 오류: {validation_paths(e)}") from e
        info["args"] = args.model_dump()
        depth = None
        if tool.depth_target:
            depth = state.depth.resolve(getattr(args, tool.depth_target), getattr(args, "parent", None))
            info["depth"] = depth
        try:
            out: ToolOutput = tool.fn(args, state)
        except (ToolRejected, BudgetExceeded):
            raise
        except Exception as e:  # noqa: BLE001 - 네트워크 오류 등은 루프를 멈추지 않고 모델에게 결과로 알린다
            raise ToolRejected(f"도구 실패({type(e).__name__}): {str(e)[:200]}") from e
        state.depth.roots.update(out.roots)
        if tool.depth_target and depth is not None:
            state.depth.visited(getattr(args, tool.depth_target), depth, out.links)
        text = out.content if isinstance(out.content, str) else json.dumps(out.content, ensure_ascii=False)
        if len(text) > TOOL_RESULT_LIMIT:
            info["truncated"] = True
            text = text[:TOOL_RESULT_LIMIT] + f"\n[잘림: 전체 {len(text)}자 중 앞 {TOOL_RESULT_LIMIT}자]"
        return render_data(text), info
    except ToolRejected as e:
        info["error"] = str(e)
        state.rejected.append(str(e))
        return f"오류: {e}", info


def run_agent(role: Role, inp: RoleInput, ctx: Ctx) -> RoleOutput:
    """종료: finish로 최종 답 제출 / max_steps 도달 / 예산 초과. 상한에 걸리면 역할의 대체 출력(attention=true)."""
    alias = ctx.model or role.spec.model
    names = [n for n in inp.tool_names(list(role.spec.tools)) if n in role.spec.tools]  # 입력별로 좁히기만
    allowed = set(names)
    cap = role.spec.max_tool_calls
    finish_schema = {"type": "function", "function": {
        "name": FINISH,
        "description": "최종 답 제출. 답이 정해졌거나 더 볼 것이 없을 때 마지막에 한 번 호출한다.",
        "parameters": strict_json_schema(role.output_cls)}}
    tools = [TOOLS[n].schema() for n in names] + [finish_schema]
    messages = initial_messages(role, inp)
    state = AgentState(depth=DepthTracker(inp.depth_limit(role.spec.max_depth)), ctx=ctx, inp=inp)

    def finish_with(out: RoleOutput, how: str) -> RoleOutput:
        out = apply_enforce(out, inp, ctx)  # 코드 규칙은 스키마 검증 뒤, 저장 전(대체 출력에도)
        ctx.last_step_id = ctx.tracer.step(kind="code", role=role.name, text=out.log, attention=out.attention,
                                           output=out.model_dump(),
                                           detail=enforce_detail(out, {"end": how, "steps": step + 1}))
        return out

    step = 0
    for step in range(role.spec.max_steps):
        try:
            res = ctx.llm.chat(alias, messages, tools=tools, max_tokens=role.spec.max_tokens,
                               temperature=role.spec.temperature, no_cache=ctx.no_cache)
        except BudgetExceeded as e:
            ctx.tracer.step(kind="code", role=role.name, text="예산 초과로 중단", attention=True, error=str(e))
            ctx.stopped = f"BudgetExceeded: {e}"
            return finish_with(role.output_cls.fallback("예산 초과", inp), "budget")
        except LLMError as e:
            ctx.tracer.step(kind="code", role=role.name, text="LLM 호출 실패", attention=True, error=str(e))
            raise
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
                    content = f"오류: 최종 답이 스키마에 맞지 않음: {validation_paths(e)}"
                ctx.tracer.step(kind="tool", role=role.name, text=f"{FINISH}: 최종 답 제출",
                                error=None if final else content)
                messages.append(_tool_message(tc["id"], content))
                continue
            if cap is not None and state.tool_calls >= cap:  # 항목당 도구 호출 상한(코드)
                content = f"오류: 도구 호출 상한 {cap}회 도달. 지금까지 본 것으로 {FINISH}를 호출할 것"
                state.rejected.append(content)
                ctx.tracer.step(kind="tool", role=role.name, text=f"{tc['name']}: 상한으로 거부", error=content,
                                attention=True, detail={"cap": cap})
                messages.append(_tool_message(tc["id"], content))
                continue
            state.tool_calls += 1
            content, info = execute_tool(tc["name"] or "", tc["arguments"], allowed, state)
            if cap is not None:  # 남은 횟수를 알려 일찍 멈출 수 있게
                content += f"\n[남은 도구 호출 {cap - state.tool_calls}회]"
            ctx.tracer.step(kind="tool", role=role.name,
                            text=f"{tc['name']}: {_args_summary(info['args'] or {})}",
                            error=info["error"], attention=bool(info["error"]),
                            detail={k: info[k] for k in ("args", "depth", "truncated", "normalized")})
            messages.append(_tool_message(tc["id"], content))
        if final is not None:
            return finish_with(final, "finish")

    return finish_with(role.output_cls.fallback(f"걸음 상한 {role.spec.max_steps} 도달", inp), "max_steps")
