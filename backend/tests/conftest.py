import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_root(client):
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["name"] == "DockWatch"


def test_health(client):
    """Test health endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_liveness(client):
    """Test liveness probe."""
    response = client.get("/api/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


def test_ready(client):
    """Test readiness probe."""
    response = client.get("/api/health/ready")
    assert response.status_code in [200, 503]
