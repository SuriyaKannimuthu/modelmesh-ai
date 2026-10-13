from typing import Any

from app.config import Settings
from app.providers.registry import build_registry


def make_settings(**values: Any) -> Settings:
    return Settings(_env_file=None, **values)


def model_ids(settings: Settings) -> list[str]:
    return [route.id for route in build_registry(settings).routes()]


def test_only_mock_is_enabled_by_default() -> None:
    assert model_ids(make_settings()) == ["mock/echo"]


def test_blank_api_key_counts_as_unset() -> None:
    settings = make_settings(anthropic_api_key="  ")

    assert settings.anthropic_api_key is None
    assert model_ids(settings) == ["mock/echo"]


def test_anthropic_is_enabled_by_api_key() -> None:
    ids = model_ids(
        make_settings(anthropic_api_key="sk-test", anthropic_models=["claude-opus-5-5"])
    )

    assert ids == ["anthropic/claude-opus-5-5", "mock/echo"]


def test_openai_needs_models_as_well_as_a_key() -> None:
    assert model_ids(make_settings(openai_api_key="sk-test")) == ["mock/echo"]


def test_ollama_and_mock_can_be_configured_together() -> None:
    ids = model_ids(
        make_settings(ollama_base_url="http://localhost:11434/v1", ollama_models=["llama3.2"])
    )

    assert ids == ["ollama/llama3.2", "mock/echo"]


def test_mock_can_be_disabled() -> None:
    assert model_ids(make_settings(enable_mock_provider=False)) == []
