import logging

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.gateway.schemas import ErrorDetail, ErrorResponse
from app.providers.errors import (
    ProviderAuthError,
    ProviderBadRequestError,
    ProviderError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)

logger = logging.getLogger(__name__)


class GatewayError(Exception):
    """An error raised by the gateway itself, rendered in the normalized error format."""

    def __init__(self, status_code: int, error_type: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_type = error_type
        self.message = message


def provider_error_response(exc: ProviderError) -> JSONResponse:
    headers: dict[str, str] = {}

    if isinstance(exc, ProviderBadRequestError):
        status, error_type, message = 400, "invalid_request", exc.message
    elif isinstance(exc, ProviderRateLimitError):
        status, error_type, message = 429, "rate_limited", exc.message
        if exc.retry_after is not None:
            headers["Retry-After"] = str(round(exc.retry_after))
    elif isinstance(exc, ProviderAuthError):
        # The client did nothing wrong; the gateway's provider credentials are misconfigured.
        # Don't echo the provider's message, which can describe the credential.
        status, error_type = 502, "provider_authentication_error"
        message = "The provider rejected the gateway's credentials."
    elif isinstance(exc, ProviderTimeoutError):
        status, error_type, message = 504, "provider_timeout", exc.message
    elif isinstance(exc, ProviderUnavailableError):
        status, error_type, message = 503, "provider_unavailable", exc.message
    else:
        status, error_type, message = 502, "provider_error", exc.message

    return _error_response(status, error_type, message, provider=exc.provider, headers=headers)


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(GatewayError)
    async def handle_gateway_error(_: Request, exc: GatewayError) -> JSONResponse:
        return _error_response(exc.status_code, exc.error_type, exc.message)

    @app.exception_handler(ProviderError)
    async def handle_provider_error(_: Request, exc: ProviderError) -> JSONResponse:
        logger.warning(
            "Provider call failed",
            extra={"provider": exc.provider, "error_class": type(exc).__name__},
        )
        return provider_error_response(exc)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        errors = exc.errors()
        message = "Invalid request."
        if errors:
            location = ".".join(str(part) for part in errors[0]["loc"] if part != "body")
            message = f"{location}: {errors[0]['msg']}" if location else str(errors[0]["msg"])
        return _error_response(422, "invalid_request", message)


def _error_response(
    status_code: int,
    error_type: str,
    message: str,
    provider: str | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    body = ErrorResponse(error=ErrorDetail(type=error_type, message=message, provider=provider))
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(body, exclude_none=True),
        headers=headers,
    )
