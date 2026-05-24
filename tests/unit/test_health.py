from fastapi.testclient import TestClient


def test_health_returns_200(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200


def test_health_status_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.json()["status"] == "ok"


def test_health_service_name(client: TestClient) -> None:
    response = client.get("/health")
    assert response.json()["service"] == "radio-music-intelligence"


def test_health_includes_version(client: TestClient) -> None:
    response = client.get("/health")
    assert "version" in response.json()
