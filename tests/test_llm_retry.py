"""S9 S-1 관문: generate 제공사 fallback 설정(AC-1) + llm.py 전송 재시도(AC-3~AC-5, C-1·C-2). 0원, 가짜 전송만."""

from __future__ import annotations

import httpx
import openai
import pytest

from trendsit.core import config
from trendsit.core.errors import LLMError
from trendsit.core.llm import LLMClient, OpenAITransport


def test_generate_provider_allows_fallback_bf16_fp8():
    """AC-1: generate 별칭 provider가 §4와 같다. retry_waits_sec 기본값도 확인."""
    models = config.load("models.yaml")
    spec = models.models["generate"]
    assert spec.provider.order == ["deepinfra"]
    assert spec.provider.allow_fallbacks is True
    assert spec.provider.require_parameters is True
    assert spec.provider.quantizations == ["bf16", "fp8"]
    assert models.retry_waits_sec == [30, 120]


def test_llmclient_wires_models_retry_waits_sec_into_transport():
    """010-F16: models.yaml의 retry_waits_sec이 LLMClient를 거쳐 실제 전송(OpenAITransport)까지 간다.
    LLMClient.__init__의 연결 줄(transport.retry_waits_sec = models.retry_waits_sec)이 없으면 실패한다."""
    models = config.load("models.yaml").model_copy(update={"retry_waits_sec": [7, 13]})
    client = LLMClient(models, secret=lambda _name: "test-key")
    assert isinstance(client.transport, OpenAITransport)
    assert client.transport.retry_waits_sec == [7, 13]


def _status_error(code: int, message: str = "err") -> openai.APIStatusError:
    req = httpx.Request("POST", "https://x/v1/chat/completions")
    resp = httpx.Response(code, request=req, json={"error": {"message": message}})
    return openai.APIStatusError(message, response=resp, body={"error": {"message": message}})


def _conn_error(message: str = "timeout") -> openai.APIConnectionError:
    req = httpx.Request("POST", "https://x/v1/chat/completions")
    return openai.APIConnectionError(message=message, request=req)


class _FakeCompletions:
    def __init__(self, effects: list):
        self.effects = list(effects)
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        effect = self.effects.pop(0)
        if isinstance(effect, Exception):
            raise effect
        return effect


class _Resp:
    def __init__(self, provider: str):
        self._provider = provider

    def model_dump(self) -> dict:
        return {"id": "g1", "model": "m", "provider": self._provider,
                "choices": [{"message": {"role": "assistant", "content": "{}"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1}}


def _make_transport(monkeypatch, effects: list, waits: list[int]) -> tuple[OpenAITransport, _FakeCompletions]:
    completions = _FakeCompletions(effects)

    class _FakeChat:
        pass

    chat = _FakeChat()
    chat.completions = completions

    class _FakeClient:
        pass

    client = _FakeClient()
    client.chat = chat
    monkeypatch.setattr(openai, "OpenAI", lambda **kw: client)
    transport = OpenAITransport()
    transport.retry_waits_sec = waits
    return transport, completions


def test_retries_429_twice_then_succeeds(monkeypatch):
    """AC-3·C-1: 429 두 번 뒤 성공하면 전송 3회, 대기 [30,120] 순서로 sleep."""
    waits_seen: list[int] = []
    monkeypatch.setattr("trendsit.core.llm.time.sleep", lambda s: waits_seen.append(s))
    transport, completions = _make_transport(
        monkeypatch, [_status_error(429), _status_error(429), _Resp("Chutes")], [30, 120])
    result = transport({"model": "m", "messages": []}, "https://openrouter.ai/api/v1", "k")
    assert completions.calls == 3
    assert waits_seen == [30, 120]
    assert result["provider"] == "Chutes"


def test_400_is_not_retried(monkeypatch):
    """AC-4·C-2: 그 밖의 4xx(400)는 대기 재시도하지 않는다. 전송 1회, sleep 0회."""
    waits_seen: list[int] = []
    monkeypatch.setattr("trendsit.core.llm.time.sleep", lambda s: waits_seen.append(s))
    transport, completions = _make_transport(monkeypatch, [_status_error(400, "bad request")], [30, 120])
    with pytest.raises(LLMError) as exc:
        transport({"model": "m", "messages": []}, "https://openrouter.ai/api/v1", "k")
    assert completions.calls == 1
    assert waits_seen == []
    assert str(exc.value).startswith("HTTP 400")


def test_exhausted_429_raises_llm_error_in_existing_format(monkeypatch):
    """AC-5·C-1: 429 ×3(추가 재시도 소진) → 전송 3회, 'HTTP 429:'로 시작하는 LLMError."""
    monkeypatch.setattr("trendsit.core.llm.time.sleep", lambda s: None)
    transport, completions = _make_transport(
        monkeypatch, [_status_error(429), _status_error(429), _status_error(429)], [30, 120])
    with pytest.raises(LLMError) as exc:
        transport({"model": "m", "messages": []}, "https://openrouter.ai/api/v1", "k")
    assert completions.calls == 3
    assert str(exc.value).startswith("HTTP 429:")


def test_exhausted_connection_error_raises_llm_error_in_existing_format(monkeypatch):
    """AC-5·C-1: 연결 오류 ×3(소진) → 전송 3회, '연결 실패:'로 시작하는 LLMError."""
    monkeypatch.setattr("trendsit.core.llm.time.sleep", lambda s: None)
    transport, completions = _make_transport(
        monkeypatch, [_conn_error(), _conn_error(), _conn_error()], [30, 120])
    with pytest.raises(LLMError) as exc:
        transport({"model": "m", "messages": []}, "https://openrouter.ai/api/v1", "k")
    assert completions.calls == 3
    assert str(exc.value).startswith("연결 실패:")
