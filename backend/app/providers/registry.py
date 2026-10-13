from collections.abc import Iterable
from dataclasses import dataclass

import anthropic
import httpx2

from app.config import Settings
from app.providers.anthropic_provider import AnthropicProvider
from app.providers.base import ModelProvider
from app.providers.mock import MockProvider
from app.providers.openai_compatible import OpenAICompatibleProvider


@dataclass(frozen=True)
class ModelRoute:
    id: str
    """Public model ID in `provider/model` form, e.g. `anthropic/claude-opus-5-5`."""
    provider: ModelProvider
    upstream_model: str


class ProviderRegistry:
    """Maps public `provider/model` IDs to the adapter that serves them."""

    def __init__(self, providers: Iterable[ModelProvider]) -> None:
        self._providers = {p.name: p for p in providers}

    def get(self, model_id: str) -> ModelRoute | None:
        provider_name, sep, upstream_model = model_id.partition("/")
        provider = self._providers.get(provider_name)
        if not sep or provider is None or upstream_model not in provider.models:
            return None
        return ModelRoute(id=model_id, provider=provider, upstream_model=upstream_model)

    def routes(self) -> list[ModelRoute]:
        return [
            ModelRoute(id=f"{provider.name}/{model}", provider=provider, upstream_model=model)
            for provider in self._providers.values()
            for model in provider.models
        ]

    async def aclose(self) -> None:
        for provider in self._providers.values():
            await provider.aclose()


def build_registry(settings: Settings) -> ProviderRegistry:
    """Create adapters for every provider that has the configuration it needs."""
    providers: list[ModelProvider] = []
    timeout = httpx2.Timeout(settings.provider_timeout_seconds, connect=5.0)

    if settings.anthropic_api_key is not None:
        providers.append(
            AnthropicProvider(
                anthropic.AsyncAnthropic(
                    api_key=settings.anthropic_api_key.get_secret_value(),
                    timeout=timeout,
                    # Retries belong to the gateway's resilience layer so behaviour is the
                    # same for every provider and retry storms can be bounded centrally.
                    max_retries=0,
                ),
                models=settings.anthropic_models,
                default_max_tokens=settings.anthropic_max_tokens,
            )
        )

    if settings.openai_api_key is not None and settings.openai_models:
        providers.append(
            OpenAICompatibleProvider(
                name="openai",
                client=httpx2.AsyncClient(
                    base_url=settings.openai_base_url,
                    headers={
                        "Authorization": f"Bearer {settings.openai_api_key.get_secret_value()}"
                    },
                    timeout=timeout,
                ),
                models=settings.openai_models,
                max_tokens_field="max_completion_tokens",
            )
        )

    if settings.ollama_base_url and settings.ollama_models:
        providers.append(
            OpenAICompatibleProvider(
                name="ollama",
                client=httpx2.AsyncClient(base_url=settings.ollama_base_url, timeout=timeout),
                models=settings.ollama_models,
            )
        )

    if settings.enable_mock_provider:
        providers.append(MockProvider())

    return ProviderRegistry(providers)
