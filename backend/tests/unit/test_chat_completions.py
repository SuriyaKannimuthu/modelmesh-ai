import pytest
from fastapi.testclient import TestClient

from app.providers.errors import (
    ProviderAuthError,
    ProviderBadRequestError,
    ProviderError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from tests.fakes import FailingProvider


def chat(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "model": "mock/echo",
        "messages": [{"role": "user", "content": "hello there"}],
    }
    body.update(overrides)
    return body


def test_returns_normalized_completion(client: TestClient) -> None:
    response = client.post("/v1/chat/completions", json=chat())

    assert response.status_code == 200
    body = response.json()
    assert body["object"] == "chat.completion"
    assert body["id"].startswith("chatcmpl-")
    assert body["model"] == "mock/echo"
    assert body["provider"] == "mock"
    assert body["choices"] == [
        {
            "index": 0,
            "message": {"role": "assistant", "content": "Echo: hello there"},
            "finish_reason": "stop",
        }
    ]
    assert body["usage"] == {"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5}
    assert body["latency_ms"] >= 0


def test_passes_max_tokens_to_provider(client: TestClient) -> None:
    response = client.post("/v1/chat/completions", json=chat(max_tokens=2))

    body = response.json()
    assert body["choices"][0]["message"]["content"] == "Echo: hello"
    assert body["choices"][0]["finish_reason"] == "length"


def test_unknown_model_returns_404(client: TestClient) -> None:
    response = client.post("/v1/chat/completions", json=chat(model="mock/nope"))

    assert response.status_code == 404
    assert response.json()["error"]["type"] == "model_not_found"


def test_model_without_provider_prefix_returns_404(client: TestClient) -> None:
    response = client.post("/v1/chat/completions", json=chat(model="echo"))

    assert response.status_code == 404


def test_streaming_is_rejected(client: TestClient) -> None:
    response = client.post("/v1/chat/completions", json=chat(stream=True))

    assert response.status_code == 400
    assert response.json()["error"]["type"] == "unsupported_feature"


def test_empty_messages_returns_normalized_validation_error(client: TestClient) -> None:
    response = client.post("/v1/chat/completions", json=chat(messages=[]))

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["type"] == "invalid_request"
    assert error["message"].startswith("messages:")


@pytest.mark.parametrize(
    ("error", "status", "error_type"),
    [
        (ProviderBadRequestError("failing", "bad"), 400, "invalid_request"),
        (ProviderRateLimitError("failing", "slow down"), 429, "rate_limited"),
        (ProviderAuthError("failing", "key sk-123 revoked"), 502, "provider_authentication_error"),
        (ProviderTimeoutError("failing", "timeout"), 504, "provider_timeout"),
        (ProviderUnavailableError("failing", "down"), 503, "provider_unavailable"),
        (ProviderError("failing", "odd"), 502, "provider_error"),
    ],
)
def test_provider_errors_are_mapped(
    client: TestClient,
    failing_provider: FailingProvider,
    error: Exception,
    status: int,
    error_type: str,
) -> None:
    failing_provider.error = error

    response = client.post("/v1/chat/completions", json=chat(model="failing/model"))

    assert response.status_code == status
    body = response.json()["error"]
    assert body["type"] == error_type
    assert body["provider"] == "failing"


def test_auth_error_does_not_leak_provider_message(
    client: TestClient, failing_provider: FailingProvider
) -> None:
    failing_provider.error = ProviderAuthError("failing", "key sk-123 revoked")

    response = client.post("/v1/chat/completions", json=chat(model="failing/model"))

    assert "sk-123" not in response.text


def test_rate_limit_sets_retry_after(client: TestClient, failing_provider: FailingProvider) -> None:
    failing_provider.error = ProviderRateLimitError("failing", "slow down", retry_after=7)

    response = client.post("/v1/chat/completions", json=chat(model="failing/model"))

    assert response.headers["Retry-After"] == "7"


def test_lists_configured_models(client: TestClient) -> None:
    response = client.get("/v1/models")

    assert response.status_code == 200
    assert response.json() == {
        "object": "list",
        "data": [
            {"id": "mock/echo", "object": "model", "owned_by": "mock"},
            {"id": "failing/model", "object": "model", "owned_by": "failing"},
        ],
    }
