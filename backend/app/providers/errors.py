"""Provider-neutral error classification.

Adapters translate SDK and HTTP failures into these types so the gateway can decide
on retries, fallbacks, and client-facing status codes without knowing provider details.
"""

from typing import ClassVar


class ProviderError(Exception):
    """A provider call failed in a way that does not fit a more specific category."""

    retryable: ClassVar[bool] = False

    def __init__(self, provider: str, message: str) -> None:
        super().__init__(message)
        self.provider = provider
        self.message = message


class ProviderBadRequestError(ProviderError):
    """The provider rejected the request itself (invalid parameters, unknown model, too large)."""


class ProviderAuthError(ProviderError):
    """The provider rejected the gateway's credentials or permissions."""


class ProviderRateLimitError(ProviderError):
    retryable = True

    def __init__(self, provider: str, message: str, retry_after: float | None = None) -> None:
        super().__init__(provider, message)
        self.retry_after = retry_after


class ProviderTimeoutError(ProviderError):
    """No response within the configured timeout. The provider may still have processed it."""

    retryable = True


class ProviderUnavailableError(ProviderError):
    """Connection failure, overload, or a 5xx from the provider."""

    retryable = True


def parse_retry_after(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return max(float(value), 0.0)
    except ValueError:
        return None
