"""Tests for the /api/admin/overview endpoint.

Verifies read-only operational state is returned correctly and that
no secrets are exposed in the response payload.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_overview_returns_200(client: TestClient) -> None:
    resp = client.get("/api/admin/overview")
    assert resp.status_code == 200


def test_overview_environment_key_present(client: TestClient) -> None:
    resp = client.get("/api/admin/overview")
    assert "environment" in resp.json()


def test_overview_scheduler_disabled_by_default(client: TestClient) -> None:
    resp = client.get("/api/admin/overview")
    assert resp.json()["scheduler_enabled"] is False


def test_overview_dedup_always_enabled(client: TestClient) -> None:
    resp = client.get("/api/admin/overview")
    assert resp.json()["dedup_enabled"] is True


def test_overview_docs_exposed_in_development(client: TestClient) -> None:
    resp = client.get("/api/admin/overview")
    body = resp.json()
    if body["environment"] == "development":
        assert body["docs_exposed"] is True


def test_overview_admin_auth_disabled_by_default(client: TestClient) -> None:
    resp = client.get("/api/admin/overview")
    assert resp.json()["admin_auth_enabled"] is False


def test_overview_retention_disabled_by_default(client: TestClient) -> None:
    resp = client.get("/api/admin/overview")
    assert resp.json()["retention_enabled"] is False
    assert resp.json()["raw_payload_retention_days"] == 0


def test_overview_collector_flags_present(client: TestClient) -> None:
    resp = client.get("/api/admin/overview")
    flags = resp.json()["collector_flags"]
    assert "capital" in flags
    assert "nova" in flags
    assert "kiis" in flags
    assert "nightly_reconciliation" in flags


def test_overview_all_collectors_disabled_by_default(client: TestClient) -> None:
    resp = client.get("/api/admin/overview")
    flags = resp.json()["collector_flags"]
    assert not any(flags.values()), "All collectors should be disabled by default"


def test_overview_no_secret_fields(client: TestClient) -> None:
    """Response must never contain sensitive configuration values."""
    resp = client.get("/api/admin/overview")
    body_str = resp.text
    forbidden = [
        "database_url",
        "api_key",
        "admin_basic_auth_password",
        "smtp_password",
        "s3_secret_access_key",
        "admin_basic_auth_user",
        "postgresql",
        "smtp_",
    ]
    for field in forbidden:
        assert field not in body_str.lower(), (
            f"Potentially sensitive field '{field}' found in response"
        )


def test_overview_is_production_false_by_default(client: TestClient) -> None:
    resp = client.get("/api/admin/overview")
    assert resp.json()["is_production"] is False
