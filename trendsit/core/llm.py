"""LLM 호출 층. OpenAI 호환 /v1 한 가지 방식(개발은 OpenRouter, 이후 Ollama).

제공사 고정, 추론 설정은 models.yaml에서 읽어 요청 본문에 넣는다. 캐시와 예산은 호출 직전에 확인한다.
"""

from __future__ import annotations

import copy
import json
import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import httpx
from pydantic import BaseModel, ValidationError

from . import images
from .budget import Budget
from .cache import Cache, cache_key
from .config import ModelsConfig, get_secret
from .errors import LLMError

# 요청 본문 중 OpenAI SDK의 정식 인자. 나머지(provider, reasoning, usage)는 extra_body
SDK_FIELDS = ("model", "messages", "max_tokens", "temperature", "response_format", "tools", "tool_choice")
# strict 구조화 출력에서 제공사마다 지원이 갈리는 키워드. 이 조건은 pydantic 검증(코드)이 지킨다
_DROP_KEYS = {"title", "default", "maxLength", "minLength", "pattern", "format", "maxItems", "minItems",
              "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum"}
_TAIL_FIELDS = ("log", "attention")


@dataclass
class LLMResult:
    content: str | None
    parsed: Any = None
    parse_error: str | None = None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    tokens_in: int | None = None
    tokens_out: int | None = None
    reasoning_tokens: int | None = None
    cached_tokens: int | None = None
    cost_usd: float = 0.0
    cost_estimated: bool = False
    latency_ms: int = 0
    provider: str | None = None
    model: str | None = None
    cache_hit: bool = False
    alias: str = ""
    request: dict[str, Any] = field(default_factory=dict)
    response: dict[str, Any] = field(default_factory=dict)
    assistant_message: dict[str, Any] = field(default_factory=dict)


# ---------- 스키마 ----------
def strict_json_schema(model: type[BaseModel]) -> dict[str, Any]:
    """pydantic 스키마 → strict 구조화 출력용: $ref 펼침, 모든 칸 required, 추가 칸 금지, log/attention은 뒤로."""
    raw = model.model_json_schema()
    defs = raw.pop("$defs", {})

    def walk(node: Any) -> Any:
        if isinstance(node, list):
            return [walk(x) for x in node]
        if not isinstance(node, dict):
            return node
        if "$ref" in node:
            return walk(copy.deepcopy(defs[node["$ref"].split("/")[-1]]))
        # 키워드만 거른다. properties 안의 키는 필드 이름이라(title, format 등) 그대로 둔다
        out = {k: walk(v) for k, v in node.items() if k not in _DROP_KEYS and k != "properties"}
        if "properties" in node:
            out["properties"] = {name: walk(sub) for name, sub in node["properties"].items()}
        if out.get("type") == "object" and "properties" in out:
            props = out["properties"]
            order = [k for k in props if k not in _TAIL_FIELDS] + [k for k in _TAIL_FIELDS if k in props]
            out["properties"] = {k: props[k] for k in order}
            out["required"] = order
            out["additionalProperties"] = False
        return out

    return walk(raw)


def response_format_for(model: type[BaseModel]) -> dict[str, Any]:
    return {"type": "json_schema",
            "json_schema": {"name": model.__name__, "strict": True, "schema": strict_json_schema(model)}}


_FENCE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.S)


def parse_json_output(content: str | None, model: type[BaseModel]) -> tuple[Any, str | None]:
    if content is None:
        return None, "응답 내용 없음"
    text = content.strip()
    m = _FENCE.match(text)
    if m:
        text = m.group(1)
    try:
        return model.model_validate_json(text), None
    except ValidationError as e:
        return None, _short_validation(e)


def _short_validation(e: ValidationError) -> str:
    parts = []
    for err in e.errors()[:5]:
        loc = ".".join(str(p) for p in err["loc"]) or "(전체)"
        if err["type"] == "string_too_long":  # 모델이 무엇을 고칠지 알 수 있게 길이를 함께 알린다
            limit, now = err["ctx"]["max_length"], len(err["input"])
            parts.append(f"{loc}: {limit}자 이하여야 함(지금 {now}자). 같은 내용을 {limit}자 안으로 줄일 것")
        else:
            parts.append(f"{loc}: {err['msg']}")
    return "; ".join(parts)


DEFAULT_RETRY_WAITS_SEC = [30, 120]


def _retryable_status(status_code: int) -> bool:
    return status_code == 429 or status_code >= 500


# ---------- 전송 ----------
class OpenAITransport:
    """공식 openai SDK로 보낸다. 429, 5xx, 연결 오류는 SDK가 지수 백오프로 3회 재시도, 그 밖의 4xx는 재시도 없음.

    SDK 재시도 소진 뒤에도 429·5xx·연결 오류면 retry_waits_sec만큼 더 대기하고 다시 보낸다(S9 FR-2·FR-3)."""

    def __init__(self, retry_waits_sec: list[int] | None = None) -> None:
        self._clients: dict[tuple[str, str], Any] = {}
        self.retry_waits_sec = retry_waits_sec if retry_waits_sec is not None else DEFAULT_RETRY_WAITS_SEC

    def __call__(self, body: dict[str, Any], base_url: str, api_key: str) -> dict[str, Any]:
        import openai

        client = self._clients.get((base_url, api_key))
        if client is None:
            client = openai.OpenAI(base_url=base_url, api_key=api_key, max_retries=3, timeout=120)
            self._clients[(base_url, api_key)] = client
        kwargs = {k: body[k] for k in SDK_FIELDS if body.get(k) is not None}
        extra = {k: v for k, v in body.items() if k not in SDK_FIELDS}
        attempts = 1 + len(self.retry_waits_sec)
        for attempt in range(attempts):
            try:
                resp = client.chat.completions.create(**kwargs, extra_body=extra or None)
                return resp.model_dump()
            except openai.APIStatusError as e:
                exc: LLMError = LLMError(f"HTTP {e.status_code}: {_error_text(e)}")
                if not _retryable_status(e.status_code) or attempt == attempts - 1:
                    raise exc from e
            except openai.APIConnectionError as e:
                exc = LLMError(f"연결 실패: {e}")
                if attempt == attempts - 1:
                    raise exc from e
            time.sleep(self.retry_waits_sec[attempt])
        raise exc  # pragma: no cover - 루프가 항상 return/raise로 끝남


def _error_text(e: Any) -> str:
    body = getattr(e, "body", None)
    if isinstance(body, dict):
        err = body.get("error", body)
        meta = err.get("metadata") if isinstance(err, dict) else None
        msg = err.get("message") if isinstance(err, dict) else str(err)
        return f"{msg}" + (f" ({json.dumps(meta, ensure_ascii=False)[:300]})" if meta else "")
    return str(e)[:500]


def openrouter_get(base_url: str, api_key: str, path: str, params: dict[str, Any] | None = None) -> Any:
    r = httpx.get(f"{base_url.rstrip('/')}/{path}", params=params,
                  headers={"Authorization": f"Bearer {api_key}"}, timeout=20)
    r.raise_for_status()
    return r.json()["data"]


Transport = Callable[[dict[str, Any], str, str], dict[str, Any]]


class LLMClient:
    def __init__(self, models: ModelsConfig, cache: Cache | None = None, budget: Budget | None = None,
                 transport: Transport | None = None,
                 generation_cost: Callable[[str, str, str], float | None] | None = None,
                 secret: Callable[[str], str | None] = get_secret):
        self.models = models
        self.cache = cache
        self.budget = budget
        self.transport = transport or OpenAITransport(models.retry_waits_sec)
        self.generation_cost = generation_cost or _generation_cost
        self.secret = secret
        self.network_calls = 0

    # ---------- 본문 ----------
    def is_openrouter(self, alias: str) -> bool:
        return "openrouter.ai" in self.models.base_url(alias)

    def build_body(self, alias: str, messages: list[dict[str, Any]], *, schema: type[BaseModel] | None = None,
                   tools: list[dict[str, Any]] | None = None, tool_choice: Any = None,
                   max_tokens: int, temperature: float | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {"model": "", "messages": copy.deepcopy(messages), "max_tokens": max_tokens}
        if temperature is not None:
            body["temperature"] = temperature
        if schema is not None:
            body["response_format"] = response_format_for(schema)
        if tools:
            body["tools"] = tools
            if tool_choice is not None:
                body["tool_choice"] = tool_choice
        return self.retarget(body, alias)

    def retarget(self, body: dict[str, Any], alias: str) -> dict[str, Any]:
        """본문의 모델 관련 칸을 별칭 설정으로 채운다. 재생에서 --model로 모델을 바꿀 때도 쓴다."""
        if alias not in self.models.models:
            raise LLMError(f"models.yaml에 없는 별칭: {alias}")
        spec = self.models.models[alias]
        body = {k: v for k, v in body.items() if k not in ("model", "provider", "reasoning", "usage")}
        body["model"] = spec.id
        if self.is_openrouter(alias):
            if spec.provider is not None:
                body["provider"] = spec.provider.model_dump(exclude_none=True)
            if spec.reasoning is False or spec.reasoning is None:
                body["reasoning"] = {"enabled": False}
            else:
                body["reasoning"] = spec.reasoning.model_dump(exclude_none=True)
            body["usage"] = {"include": True}
        return body

    # ---------- 호출 ----------
    def chat(self, alias: str, messages: list[dict[str, Any]], *, schema: type[BaseModel] | None = None,
             tools: list[dict[str, Any]] | None = None, tool_choice: Any = None, max_tokens: int,
             temperature: float | None = None, no_cache: bool = False) -> LLMResult:
        body = self.build_body(alias, messages, schema=schema, tools=tools, tool_choice=tool_choice,
                               max_tokens=max_tokens, temperature=temperature)
        return self.send(alias, body, schema=schema, no_cache=no_cache)

    def send(self, alias: str, body: dict[str, Any], *, schema: type[BaseModel] | None = None,
             no_cache: bool = False) -> LLMResult:
        """완성된 본문을 보낸다. no_cache는 읽기만 끄고, 새 응답은 캐시에 저장한다."""
        key = cache_key(body)
        request = {"alias": alias, "body": body}
        if self.cache is not None and not no_cache:
            cached = self.cache.get(key)
            if cached is not None:
                return self._result(alias, request, cached["response"], latency_ms=0, cache_hit=True,
                                    schema=schema)

        spec = self.models.models[alias]
        base_url = self.models.base_url(alias)
        if self.budget is not None:
            estimate = self.budget.estimate(spec, base_url, body)
            if n_images := images.count(body):  # 자리표시 문자열 대신 장당 추정 토큰으로
                estimate += n_images * images.IMAGE_TOKENS_EST * self.budget.prices.price(spec, base_url)[0]
            self.budget.check(estimate, f"{alias}({spec.id}) max_tokens={body.get('max_tokens')}")
        api_key = self.secret(spec.api_key_env)
        if not api_key and self.is_openrouter(alias):
            raise LLMError(f"{spec.api_key_env} 없음 (환경 변수 또는 ~/.config/trendsit/.env)")

        started = time.monotonic()
        self.network_calls += 1
        response = self.transport(images.materialize(body), base_url, api_key or "ollama")
        latency = int((time.monotonic() - started) * 1000)
        if response.get("error") or not response.get("choices"):
            # 실패 응답에도 청구액이 있으면 예산에 더한다(키 usage로도 나중에 맞춰짐)
            if self.budget is not None:
                self.budget.add(float((response.get("usage") or {}).get("cost") or 0))
            detail = json.dumps(response.get("error"), ensure_ascii=False)[:500] if response.get("error") else ""
            raise LLMError(f"제공사 오류: {detail}" if detail else "응답에 choices 없음")

        result = self._result(alias, request, response, latency_ms=latency, cache_hit=False, schema=schema)
        if result.cost_usd == 0 and not self._free(alias):
            cost = None
            if response.get("id") and api_key and self.is_openrouter(alias):
                try:
                    cost = self.generation_cost(base_url, api_key, response["id"])
                except Exception:  # noqa: BLE001 - 조회 실패면 단가 계산으로
                    cost = None
            if cost is None and self.budget is not None:
                pin, pout = self.budget.prices.price(spec, base_url)
                cost = (result.tokens_in or 0) * pin + (result.tokens_out or 0) * pout
                result.cost_estimated = True
            result.cost_usd = float(cost or 0)
        if self.budget is not None:
            self.budget.add(result.cost_usd)
        if self.cache is not None:
            self.cache.put(key, {"request": request, "response": response})
        return result

    def _free(self, alias: str) -> bool:
        return self.models.models[alias].id.endswith(":free") or not self.is_openrouter(alias)

    def _result(self, alias: str, request: dict[str, Any], response: dict[str, Any], *, latency_ms: int,
                cache_hit: bool, schema: type[BaseModel] | None) -> LLMResult:
        choice = response["choices"][0]
        message = choice.get("message") or {}
        usage = response.get("usage") or {}
        tool_calls = [
            {"id": tc.get("id"), "name": (tc.get("function") or {}).get("name"),
             "arguments": (tc.get("function") or {}).get("arguments") or "{}"}
            for tc in (message.get("tool_calls") or [])
        ]
        assistant: dict[str, Any] = {"role": "assistant", "content": message.get("content")}
        if message.get("tool_calls"):
            assistant["tool_calls"] = [
                {"id": tc["id"], "type": "function",
                 "function": {"name": tc["name"], "arguments": tc["arguments"]}} for tc in tool_calls
            ]
        result = LLMResult(
            content=message.get("content"),
            tool_calls=tool_calls,
            tokens_in=usage.get("prompt_tokens"),
            tokens_out=usage.get("completion_tokens"),
            reasoning_tokens=(usage.get("completion_tokens_details") or {}).get("reasoning_tokens"),
            cached_tokens=(usage.get("prompt_tokens_details") or {}).get("cached_tokens"),
            cost_usd=0.0 if cache_hit else float(usage.get("cost") or 0),
            latency_ms=latency_ms,
            provider=response.get("provider"),
            model=response.get("model") or request["body"].get("model"),
            cache_hit=cache_hit,
            alias=alias,
            request=request,
            response=response,
            assistant_message=assistant,
        )
        if schema is not None and not tool_calls:
            result.parsed, result.parse_error = parse_json_output(result.content, schema)
        return result

    # ---------- 키 ----------
    def key_status(self, alias: str = "generate") -> dict[str, Any]:
        """GET /api/v1/key → usage(누적), limit, limit_remaining, usage_daily."""
        spec = self.models.models[alias]
        api_key = self.secret(spec.api_key_env)
        if not api_key:
            raise LLMError(f"{spec.api_key_env} 없음")
        data = openrouter_get(self.models.base_url(alias), api_key, "key")
        return {k: data.get(k) for k in ("usage", "limit", "limit_remaining", "usage_daily")}


def _generation_cost(base_url: str, api_key: str, generation_id: str) -> float | None:
    for _ in range(3):  # 생성 기록은 응답 직후 잠깐 없을 수 있다
        try:
            data = openrouter_get(base_url, api_key, "generation", {"id": generation_id})
            return float(data.get("total_cost"))
        except Exception:  # noqa: BLE001
            time.sleep(1)
    return None
