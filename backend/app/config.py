from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and `.env`."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ModelMesh AI"
    app_env: Literal["development", "test", "staging", "production"] = "development"

    database_url: str = "postgresql+psycopg://modelmesh:modelmesh@localhost:5432/modelmesh"
    redis_url: str = "redis://localhost:6379/0"

    cors_origins: list[str] = ["http://localhost:3000"]

    provider_timeout_seconds: float = 120.0
    enable_mock_provider: bool = True

    anthropic_api_key: SecretStr | None = None
    anthropic_models: list[str] = ["claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-5-5"]
    anthropic_max_tokens: int = 16_000

    openai_api_key: SecretStr | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_models: list[str] = []

    ollama_base_url: str | None = None
    ollama_models: list[str] = []

    otel_service_name: str = "modelmesh-ai"
    otel_exporter_otlp_endpoint: str | None = None

    @field_validator(
        "anthropic_api_key",
        "openai_api_key",
        "ollama_base_url",
        "otel_exporter_otlp_endpoint",
        mode="before",
    )
    @classmethod
    def _blank_as_unset(cls, value: object) -> object:
        # `KEY=` in .env means "not configured", not an empty credential.
        return None if isinstance(value, str) and not value.strip() else value


@lru_cache
def get_settings() -> Settings:
    return Settings()
