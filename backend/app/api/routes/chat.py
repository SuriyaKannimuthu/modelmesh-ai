from fastapi import APIRouter

from app.api.dependencies import RegistryDep
from app.gateway.request_handler import create_chat_completion
from app.gateway.schemas import ChatCompletionRequest, ChatCompletionResponse, ErrorResponse

router = APIRouter(tags=["chat"])


@router.post(
    "/chat/completions",
    response_model=ChatCompletionResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
        504: {"model": ErrorResponse},
    },
)
async def chat_completions(
    request: ChatCompletionRequest, registry: RegistryDep
) -> ChatCompletionResponse:
    """Submit a chat request to the model named in `model` (`provider/model`)."""
    return await create_chat_completion(request, registry)
