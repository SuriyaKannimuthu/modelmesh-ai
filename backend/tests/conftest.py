from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.providers.mock import MockProvider
from app.providers.registry import ProviderRegistry
from tests.fakes import FailingProvider


@pytest.fixture
def failing_provider() -> FailingProvider:
    return FailingProvider()


@pytest.fixture
def client(failing_provider: FailingProvider) -> Iterator[TestClient]:
    registry = ProviderRegistry([MockProvider(), failing_provider])
    with TestClient(create_app(registry=registry)) as test_client:
        yield test_client
