import time
import uuid

from app.gateway.error_mapping import GatewayError
from app.gateway.schemas import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    Choice,
    Usage,
)
from app.providers.base import GenerationRequest, Message
from app.providers.registry import ProviderRegistry


async def create_chat_completion(
    request: ChatCompletionRequest,
    registry: ProviderRegistry,
) -> ChatCompletionResponse:
    """Resolve the requested model, call its provider, and normalize the result.

    Provider failures propagate as `ProviderError` and are rendered by the exception handlers.
    """
    if request.stream:
        raise GatewayError(400, "unsupported_feature", "Streaming is not supported yet.")

    route = registry.get(request.model)
    if route is None:
        raise GatewayError(
            404,
            "model_not_found",
            f"Model '{request.model}' is not available. See GET /v1/models.",
        )

    generation_request = GenerationRequest(
        model=route.upstream_model,
        messages=[Message(role=m.role, content=m.content) for m in request.messages],
        max_tokens=request.max_tokens,
        temperature=request.temperature,
    )

    started = time.perf_counter()
    result = await route.provider.generate(generation_request)
    latency_ms = round((time.perf_counter() - started) * 1000)

    return ChatCompletionResponse(
        id=f"chatcmpl-{uuid.uuid4().hex}",
        created=int(time.time()),
        model=f"{route.provider.name}/{result.model}",
        provider=route.provider.name,
        choices=[
            Choice(
                index=0,
                message=ChatMessage(role="assistant", content=result.content),
                finish_reason=result.finish_reason,
            )
        ],
        usage=Usage(
            prompt_tokens=result.input_tokens,
            completion_tokens=result.output_tokens,
            total_tokens=result.input_tokens + result.output_tokens,
        ),
        latency_ms=latency_ms,
    )
