import json
from collections.abc import Callable
from typing import Any

import anthropic
import httpx2
import pytest

from app.providers.anthropic_provider import SERVER_SIDE_FALLBACK_BETA, AnthropicProvider
from app.providers.base import GenerationRequest, Message
from app.providers.errors import (
    ProviderAuthError,
    ProviderBadRequestError,
    ProviderError,
    ProviderRateLimitError,
    ProviderUnavailableError,
)

Handler = Callable[[httpx2.Request], httpx2.Response]


def make_provider(handler: Handler) -> AnthropicProvider:
    client = anthropic.AsyncAnthropic(
        api_key="test-key",
        max_retries=0,
        http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(handler)),
    )
    return AnthropicProvider(client, default_max_tokens=1000)


def message_response(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "id": "msg_1",
        "type": "message",
        "role": "assistant",
        "model": "claude-opus-5-5",
        "content": [
            {"type": "thinking", "thinking": "", "signature": "sig"},
            {"type": "text", "text": "Hello"},
            {"type": "text", "text": " world"},
        ],
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "usage": {
            "input_tokens": 10,
            "output_tokens": 5,
            "cache_creation_input_tokens": 2,
            "cache_read_input_tokens": 3,
        },
    }
    body.update(overrides)
    return body


def error_response(status: int, error_type: str, headers: dict[str, str] | None = None) -> Handler:
    def handler(_: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            status,
            headers=headers,
            json={"type": "error", "error": {"type": error_type, "message": f"{error_type} msg"}},
        )

    return handler


REQUEST = GenerationRequest(
    model="claude-opus-5-5",
    messages=[
        Message("system", "Be brief."),
        Message("user", "Hi"),
        Message("assistant", "Hello"),
        Message("user", "How are you?"),
    ],
)


async def test_builds_messages_request_and_normalizes_response() -> None:
    captured: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        captured.append(request)
        return httpx2.Response(200, json=message_response())

    result = await make_provider(handler).generate(REQUEST)

    request = captured[0]
    assert request.url.path == "/v1/messages"
    assert request.headers["x-api-key"] == "test-key"
    assert SERVER_SIDE_FALLBACK_BETA in request.headers["anthropic-beta"]
    body = json.loads(request.content)
    assert body["model"] == "claude-opus-5-5"
    assert body["system"] == "Be brief."
    assert body["max_tokens"] == 1000
    assert body["fallbacks"] == "default"
    assert "temperature" not in body
    assert body["messages"] == [
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello"},
        {"role": "user", "content": "How are you?"},
    ]

    assert result.content == "Hello world"
    assert result.finish_reason == "stop"
    assert result.input_tokens == 15
    assert result.output_tokens == 5
    assert result.model == "claude-opus-5-5"


async def test_sends_optional_params_only_when_set() -> None:
    captured: list[dict[str, Any]] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        captured.append(json.loads(request.content))
        return httpx2.Response(200, json=message_response(model="claude-haiku-5-5"))

    request = GenerationRequest(
        model="claude-haiku-5-5", messages=[Message("user", "Hi")], max_tokens=50
    )
    await make_provider(handler).generate(request)

    body = captured[0]
    assert body["max_tokens"] == 50
    assert "system" not in body
    # Claude Haiku 5.5 has no server-side fallback.
    assert "fallbacks" not in body


async def test_rejects_temperature_without_calling_the_api() -> None:
    def handler(_: httpx2.Request) -> httpx2.Response:
        raise AssertionError("API should not be called")

    request = GenerationRequest(
        model="claude-opus-5-5", messages=[Message("user", "Hi")], temperature=0.2
    )

    with pytest.raises(ProviderBadRequestError, match="temperature"):
        await make_provider(handler).generate(request)


async def test_refusal_maps_to_content_filter() -> None:
    def handler(_: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, json=message_response(content=[], stop_reason="refusal"))

    result = await make_provider(handler).generate(REQUEST)

    assert result.content == ""
    assert result.finish_reason == "content_filter"


async def test_reports_the_model_that_served_a_fallback() -> None:
    def handler(_: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, json=message_response(model="claude-opus-4-8"))

    result = await make_provider(handler).generate(REQUEST)

    assert result.model == "claude-opus-4-8"


@pytest.mark.parametrize(
    ("handler", "expected"),
    [
        (error_response(400, "invalid_request_error"), ProviderBadRequestError),
        (error_response(404, "not_found_error"), ProviderBadRequestError),
        (error_response(401, "authentication_error"), ProviderAuthError),
        (error_response(403, "permission_error"), ProviderAuthError),
        (error_response(500, "api_error"), ProviderUnavailableError),
        (error_response(529, "overloaded_error"), ProviderUnavailableError),
        (error_response(402, "billing_error"), ProviderError),
    ],
)
async def test_classifies_api_errors(handler: Handler, expected: type[ProviderError]) -> None:
    with pytest.raises(expected) as info:
        await make_provider(handler).generate(REQUEST)

    assert type(info.value) is expected
    assert info.value.provider == "anthropic"


async def test_rate_limit_carries_retry_after() -> None:
    handler = error_response(429, "rate_limit_error", headers={"retry-after": "12"})

    with pytest.raises(ProviderRateLimitError) as info:
        await make_provider(handler).generate(REQUEST)

    assert info.value.retry_after == 12
    assert info.value.retryable


async def test_connection_failure_is_unavailable() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("refused", request=request)

    with pytest.raises(ProviderUnavailableError):
        await make_provider(handler).generate(REQUEST)
