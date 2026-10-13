"""Public request and response schemas.

The chat shapes follow the OpenAI chat-completions format so existing OpenAI clients can
point at the gateway. `provider` and `latency_ms` are ModelMesh additions.
"""

from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = Field(
        min_length=1, description="Public model ID, e.g. `anthropic/claude-opus-5-5`."
    )
    messages: list[ChatMessage] = Field(min_length=1)
    max_tokens: int | None = Field(default=None, ge=1, le=128_000)
    temperature: float | None = Field(default=None, ge=0, le=2)
    stream: bool = False


class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class Choice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: str


class ChatCompletionResponse(BaseModel):
    id: str
    object: Literal["chat.completion"] = "chat.completion"
    created: int
    model: str = Field(description="The model that served the request, in `provider/model` form.")
    provider: str
    choices: list[Choice]
    usage: Usage
    latency_ms: int


class ModelInfo(BaseModel):
    id: str
    object: Literal["model"] = "model"
    owned_by: str


class ModelList(BaseModel):
    object: Literal["list"] = "list"
    data: list[ModelInfo]


class ErrorDetail(BaseModel):
    type: str
    message: str
    provider: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail
