from collections.abc import Sequence
from typing import Any, Literal

import anthropic
from anthropic.types.beta import BetaMessageParam

from app.providers.base import FinishReason, GenerationRequest, GenerationResult, Message
from app.providers.errors import (
    ProviderAuthError,
    ProviderBadRequestError,
    ProviderError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    parse_retry_after,
)

DEFAULT_MODELS = ("claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-5-5")

# Models that accept server-side refusal fallback in its `"default"` form. When a safety
# classifier declines the request, the API re-runs it on Anthropic's recommended fallback
# model within the same call. Claude Haiku 5.5 has no server-side fallback.
SERVER_SIDE_FALLBACK_MODELS = frozenset(
    {"claude-fable-5-1", "claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5"}
)
SERVER_SIDE_FALLBACK_BETA = "server-side-fallback-2026-07-01"

_FINISH_REASONS: dict[str, FinishReason] = {
    "end_turn": "stop",
    "stop_sequence": "stop",
    "max_tokens": "length",
    "refusal": "content_filter",
    "tool_use": "tool_calls",
}


class AnthropicProvider:
    """Adapter for the Claude Messages API via the official async SDK."""

    name = "anthropic"

    def __init__(
        self,
        client: anthropic.AsyncAnthropic,
        models: Sequence[str] = DEFAULT_MODELS,
        default_max_tokens: int = 16_000,
    ) -> None:
        self._client = client
        self.models = tuple(models)
        self._default_max_tokens = default_max_tokens

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        # Current Claude models reject sampling parameters and the SDK no longer accepts them.
        # Fail clearly rather than silently ignoring a setting the caller asked for.
        if request.temperature is not None:
            raise ProviderBadRequestError(
                self.name, "temperature is not supported by Anthropic models; omit it."
            )

        system = "\n\n".join(m.content for m in request.messages if m.role == "system")
        messages = [_to_message_param(m) for m in request.messages if m.role != "system"]

        options: dict[str, Any] = {}
        if system:
            options["system"] = system
        if request.model in SERVER_SIDE_FALLBACK_MODELS:
            options["betas"] = [SERVER_SIDE_FALLBACK_BETA]
            options["fallbacks"] = "default"

        try:
            response = await self._client.beta.messages.create(
                model=request.model,
                max_tokens=request.max_tokens or self._default_max_tokens,
                messages=messages,
                **options,
            )
        except anthropic.APITimeoutError as exc:
            raise ProviderTimeoutError(self.name, "Request to Anthropic timed out.") from exc
        except anthropic.APIConnectionError as exc:
            raise ProviderUnavailableError(self.name, "Could not connect to Anthropic.") from exc
        except anthropic.RateLimitError as exc:
            raise ProviderRateLimitError(
                self.name,
                exc.message,
                retry_after=parse_retry_after(exc.response.headers.get("retry-after")),
            ) from exc
        except (anthropic.AuthenticationError, anthropic.PermissionDeniedError) as exc:
            raise ProviderAuthError(self.name, exc.message) from exc
        except (
            anthropic.BadRequestError,
            anthropic.NotFoundError,
            anthropic.RequestTooLargeError,
            anthropic.UnprocessableEntityError,
        ) as exc:
            raise ProviderBadRequestError(self.name, exc.message) from exc
        except anthropic.APIStatusError as exc:
            if exc.status_code >= 500:
                raise ProviderUnavailableError(self.name, exc.message) from exc
            raise ProviderError(self.name, exc.message) from exc

        # Thinking and fallback blocks are not part of the chat reply; keep only text.
        text = "".join(block.text for block in response.content if block.type == "text")
        usage = response.usage
        input_tokens = (
            usage.input_tokens
            + (usage.cache_creation_input_tokens or 0)
            + (usage.cache_read_input_tokens or 0)
        )

        return GenerationResult(
            content=text,
            finish_reason=_FINISH_REASONS.get(response.stop_reason or "", "other"),
            input_tokens=input_tokens,
            output_tokens=usage.output_tokens,
            model=response.model,
        )

    async def health_check(self) -> bool:
        try:
            await self._client.models.list(limit=1)
        except anthropic.APIError:
            return False
        return True

    async def aclose(self) -> None:
        await self._client.close()


def _to_message_param(message: Message) -> BetaMessageParam:
    role: Literal["user", "assistant"] = "assistant" if message.role == "assistant" else "user"
    return {"role": role, "content": message.content}
