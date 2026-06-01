import pytest
from fastapi.testclient import TestClient

from smart_ingestion.main import app
from smart_ingestion.session import session_store


@pytest.fixture
def client():
    session_store._sessions.clear()
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_sessions():
    session_store._sessions.clear()
    yield
    session_store._sessions.clear()
