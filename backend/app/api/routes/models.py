from fastapi import APIRouter

from app.api.dependencies import RegistryDep
from app.gateway.schemas import ModelInfo, ModelList

router = APIRouter(tags=["models"])


@router.get("/models", response_model=ModelList)
async def list_models(registry: RegistryDep) -> ModelList:
    """List the models the gateway is configured to serve."""
    return ModelList(
        data=[ModelInfo(id=route.id, owned_by=route.provider.name) for route in registry.routes()]
    )
