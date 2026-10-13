from typing import Annotated, cast

from fastapi import Depends, Request

from app.config import Settings, get_settings
from app.providers.registry import ProviderRegistry

SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_registry(request: Request) -> ProviderRegistry:
    return cast(ProviderRegistry, request.app.state.registry)


RegistryDep = Annotated[ProviderRegistry, Depends(get_registry)]
