from fastapi.testclient import TestClient
from app.main import app
from app.config import get_settings

client = TestClient(app)


def test_health_check_endpoint():
    settings = get_settings()
    response = client.get("/api/ai/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == settings.app_name
    assert data["version"] == settings.app_version
    assert "environment" in data
    assert "database" in data


def test_root_endpoint():
    settings = get_settings()
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "is running" in data["message"]
    assert data["health"] == "/api/ai/health"
    assert data["version"] == settings.app_version
