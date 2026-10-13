from app.providers.base import FinishReason, GenerationRequest, GenerationResult


class MockProvider:
    """Deterministic, offline provider for local development and tests.

    Echoes the last user message. Token counts are whitespace-separated words, and
    `max_tokens` truncates the reply so length handling can be exercised.
    """

    name = "mock"
    models: tuple[str, ...] = ("echo",)

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        last_user = next((m.content for m in reversed(request.messages) if m.role == "user"), "")
        words = f"Echo: {last_user}".split()

        finish_reason: FinishReason = "stop"
        if request.max_tokens is not None and len(words) > request.max_tokens:
            words = words[: request.max_tokens]
            finish_reason = "length"

        return GenerationResult(
            content=" ".join(words),
            finish_reason=finish_reason,
            input_tokens=sum(len(m.content.split()) for m in request.messages),
            output_tokens=len(words),
            model=request.model,
        )

    async def health_check(self) -> bool:
        return True

    async def aclose(self) -> None:
        return None
