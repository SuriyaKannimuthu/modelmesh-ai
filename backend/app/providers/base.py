from dataclasses import dataclass
from typing import Literal, Protocol

Role = Literal["system", "user", "assistant"]
FinishReason = Literal["stop", "length", "content_filter", "tool_calls", "other"]


@dataclass(frozen=True)
class Message:
    role: Role
    content: str


@dataclass(frozen=True)
class GenerationRequest:
    """A provider-neutral generation request. `model` is the provider's own model ID."""

    model: str
    messages: list[Message]
    max_tokens: int | None = None
    temperature: float | None = None


@dataclass(frozen=True)
class GenerationResult:
    content: str
    finish_reason: FinishReason
    input_tokens: int
    output_tokens: int
    model: str
    """The model that actually served the request (may differ from the one requested)."""


class ModelProvider(Protocol):
    """Common interface implemented by every LLM provider adapter."""

    name: str
    models: tuple[str, ...]

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        """Generate a normalized model response. Raises `ProviderError` on failure."""
        ...

    async def health_check(self) -> bool:
        """Report whether the provider is currently usable."""
        ...

    async def aclose(self) -> None:
        """Release network resources held by the adapter."""
        ...
