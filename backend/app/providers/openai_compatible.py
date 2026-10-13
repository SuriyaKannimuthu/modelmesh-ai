from collections.abc import Sequence
from typing import Any, Literal

import httpx2

from app.providers.base import FinishReason, GenerationRequest, GenerationResult
from app.providers.errors import (
    ProviderAuthError,
    ProviderBadRequestError,
    ProviderError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    parse_retry_after,
)

_FINISH_REASONS: dict[str, FinishReason] = {
    "stop": "stop",
    "length": "length",
    "content_filter": "content_filter",
    "tool_calls": "tool_calls",
    "function_call": "tool_calls",
}


class OpenAICompatibleProvider:
    """Adapter for any server exposing an OpenAI-style `/chat/completions` endpoint.

    Covers OpenAI itself and compatible servers such as Ollama, vLLM, and LM Studio.
    """

    def __init__(
        self,
        name: str,
        client: httpx2.AsyncClient,
        models: Sequence[str],
        max_tokens_field: Literal["max_tokens", "max_completion_tokens"] = "max_tokens",
    ) -> None:
        self.name = name
        self.models = tuple(models)
        self._client = client
        self._max_tokens_field = max_tokens_field

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        body: dict[str, Any] = {
            "model": request.model,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
        }
        if request.max_tokens is not None:
            body[self._max_tokens_field] = request.max_tokens
        if request.temperature is not None:
            body["temperature"] = request.temperature

        try:
            response = await self._client.post("chat/completions", json=body)
        except httpx2.TimeoutException as exc:
            raise ProviderTimeoutError(self.name, f"Request to {self.name} timed out.") from exc
        except httpx2.TransportError as exc:
            raise ProviderUnavailableError(self.name, f"Could not connect to {self.name}.") from exc

        if response.status_code >= 400:
            raise self._status_error(response)

        try:
            data = response.json()
            choice = data["choices"][0]
            usage = data.get("usage") or {}
            return GenerationResult(
                content=choice["message"].get("content") or "",
                finish_reason=_FINISH_REASONS.get(choice.get("finish_reason") or "", "other"),
                input_tokens=int(usage.get("prompt_tokens", 0)),
                output_tokens=int(usage.get("completion_tokens", 0)),
                model=data.get("model") or request.model,
            )
        except (ValueError, KeyError, IndexError, TypeError, AttributeError) as exc:
            raise ProviderError(self.name, f"Unexpected response format from {self.name}.") from exc

    async def health_check(self) -> bool:
        try:
            response = await self._client.get("models")
        except httpx2.HTTPError:
            return False
        return response.status_code == 200

    async def aclose(self) -> None:
        await self._client.aclose()

    def _status_error(self, response: httpx2.Response) -> ProviderError:
        message = _error_message(response)
        status = response.status_code
        if status == 429:
            return ProviderRateLimitError(
                self.name,
                message,
                retry_after=parse_retry_after(response.headers.get("retry-after")),
            )
        if status in (401, 403):
            return ProviderAuthError(self.name, message)
        if status in (400, 404, 413, 422):
            return ProviderBadRequestError(self.name, message)
        if status >= 500:
            return ProviderUnavailableError(self.name, message)
        return ProviderError(self.name, message)


def _error_message(response: httpx2.Response) -> str:
    try:
        error = response.json().get("error")
    except ValueError:
        error = None
    if isinstance(error, dict) and isinstance(error.get("message"), str):
        return str(error["message"])
    if isinstance(error, str):
        return error
    return f"Provider returned HTTP {response.status_code}."
