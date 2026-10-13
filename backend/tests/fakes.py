from app.providers.base import GenerationRequest, GenerationResult


class FailingProvider:
    """Test double that raises a configured `ProviderError` from `generate`."""

    name = "failing"
    models: tuple[str, ...] = ("model",)

    def __init__(self) -> None:
        self.error: Exception | None = None

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        assert self.error is not None
        raise self.error

    async def health_check(self) -> bool:
        return False

    async def aclose(self) -> None:
        return None
