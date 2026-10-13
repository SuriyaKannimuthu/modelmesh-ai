from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.routes import chat, health, models
from app.config import get_settings
from app.gateway.error_mapping import install_exception_handlers
from app.providers.registry import ProviderRegistry, build_registry


def create_app(registry: ProviderRegistry | None = None) -> FastAPI:
    """Build the application. Pass `registry` to override provider configuration (tests)."""
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.registry = registry if registry is not None else build_registry(settings)
        try:
            yield
        finally:
            await app.state.registry.aclose()

    app = FastAPI(title=settings.app_name, version=__version__, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    install_exception_handlers(app)

    app.include_router(health.router, prefix="/v1")
    app.include_router(models.router, prefix="/v1")
    app.include_router(chat.router, prefix="/v1")

    return app


app = create_app()
