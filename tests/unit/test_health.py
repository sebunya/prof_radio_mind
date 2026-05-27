"""Tests for GET /health.

In the unit-test environment there is no real database, so the endpoint may return
200 (ok) or 503 (degraded) depending on whether a DB connection is available.
We validate the response shape is always correct regardless of DB state.
"""

from fastapi.testclient import TestClient


def test_health_status_code(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code in (200, 503)


def test_health_status_field(client: TestClient) -> None:
    response = client.get("/health")
    assert response.json()["status"] in ("ok", "degraded")


def test_health_service_name(client: TestClient) -> None:
    response = client.get("/health")
    assert response.json()["service"] == "radio-music-intelligence"


def test_health_includes_version(client: TestClient) -> None:
    response = client.get("/health")
    assert "version" in response.json()


def test_health_includes_database_component(client: TestClient) -> None:
    response = client.get("/health")
    body = response.json()
    assert "components" in body
    assert "database" in body["components"]
