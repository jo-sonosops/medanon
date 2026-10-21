import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.synthetic import build_sample


@pytest.fixture
def sample() -> bytes:
    return build_sample()


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c
