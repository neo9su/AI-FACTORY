import pytest
from fastapi.testclient import TestClient

from app.main import app, storage, storage_lock


@pytest.fixture(autouse=True)
def clear_storage():
    """Clear storage before each test to ensure isolation."""
    with storage_lock:
        storage.clear()
    yield


@pytest.fixture
def client():
    return TestClient(app)
