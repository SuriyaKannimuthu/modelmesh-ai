import json
from collections.abc import Callable
from typing import Any

import httpx2
import pytest

from app.providers.base import GenerationRequest, Message
from app.providers.errors import (
    ProviderAuthError,
    ProviderBadRequestError,
    ProviderError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.providers.openai_compatible import OpenAICompatibleProvider

Handler = Callable[[httpx2.Request], httpx2.Response]

REQUEST = GenerationRequest(
    model="llama3.2",
    messages=[Message("system", "Be brief."), Message("user", "Hi")],
)


def make_provider(handler: Handler, **kwargs: Any) -> OpenAICompatibleProvider:
    client = httpx2.AsyncClient(
        base_url="http://llm.test/v1", transport=httpx2.MockTransport(handler)
    )
    return OpenAICompatibleProvider(name="ollama", client=client, models=["llama3.2"], **kwargs)


def completion(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "id": "chatcmpl-1",
        "object": "chat.completion",
        "model": "llama3.2",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "Hello"},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 7, "completion_tokens": 2, "total_tokens": 9},
    }
    body.update(overrides)
    return body


async def test_builds_request_and_normalizes_response() -> None:
    captured: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        captured.append(request)
        return httpx2.Response(200, json=completion())

    result = await make_provider(handler).generate(REQUEST)

    request = captured[0]
    assert str(request.url) == "http://llm.test/v1/chat/completions"
    assert json.loads(request.content) == {
        "model": "llama3.2",
        "messages": [
            {"role": "system", "content": "Be brief."},
            {"role": "user", "content": "Hi"},
        ],
    }
    assert result.content == "Hello"
    assert result.finish_reason == "stop"
    assert (result.input_tokens, result.output_tokens) == (7, 2)
    assert result.model == "llama3.2"


async def test_uses_configured_max_tokens_field() -> None:
    captured: list[dict[str, Any]] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        captured.append(json.loads(request.content))
        return httpx2.Response(200, json=completion())

    provider = make_provider(handler, max_tokens_field="max_completion_tokens")
    request = GenerationRequest(
        model="llama3.2", messages=[Message("user", "Hi")], max_tokens=64, temperature=0.5
    )
    await provider.generate(request)

    assert captured[0]["max_completion_tokens"] == 64
    assert "max_tokens" not in captured[0]
    assert captured[0]["temperature"] == 0.5


async def test_tolerates_missing_usage_and_null_content() -> None:
    def handler(_: httpx2.Request) -> httpx2.Response:
        body = completion(usage=None)
        body["choices"][0]["message"]["content"] = None
        body["choices"][0]["finish_reason"] = "length"
        return httpx2.Response(200, json=body)

    result = await make_provider(handler).generate(REQUEST)

    assert result.content == ""
    assert result.finish_reason == "length"
    assert (result.input_tokens, result.output_tokens) == (0, 0)


async def test_malformed_response_is_provider_error() -> None:
    def handler(_: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, json={"choices": []})

    with pytest.raises(ProviderError, match="Unexpected response format"):
        await make_provider(handler).generate(REQUEST)


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (400, ProviderBadRequestError),
        (404, ProviderBadRequestError),
        (401, ProviderAuthError),
        (403, ProviderAuthError),
        (429, ProviderRateLimitError),
        (500, ProviderUnavailableError),
        (503, ProviderUnavailableError),
        (409, ProviderError),
    ],
)
async def test_classifies_status_errors(status: int, expected: type[ProviderError]) -> None:
    def handler(_: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            status, headers={"retry-after": "3"}, json={"error": {"message": "nope"}}
        )

    with pytest.raises(expected) as info:
        await make_provider(handler).generate(REQUEST)

    assert type(info.value) is expected
    assert info.value.message == "nope"
    if isinstance(info.value, ProviderRateLimitError):
        assert info.value.retry_after == 3


async def test_timeout_is_classified() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ReadTimeout("slow", request=request)

    with pytest.raises(ProviderTimeoutError):
        await make_provider(handler).generate(REQUEST)


async def test_connection_failure_is_unavailable() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("refused", request=request)

    with pytest.raises(ProviderUnavailableError):
        await make_provider(handler).generate(REQUEST)
