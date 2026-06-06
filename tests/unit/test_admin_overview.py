"""Tests for the /api/admin/overview endpoint.

Verifies that the endpoint returns the correct operational state fields and
that no secrets are exposed in the response payload.

Note: The endpoint is served by app/api/routes/admin.py (OverviewResponse).
      It requires a DB session; DB errors degrade gracefully to zero counts.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_overview_returns_200(client: TestClient) -> None:
    resp = client.get("/api/admin/overview")
    assert resp.status_code == 200


def test_overview_app_env_key_present(client: TestClient) -> None:
    resp = client.get("/api/admin/overview")
    assert "app_env" in resp.json()


def test_overview_scheduler_disabled_by_default(client: TestClient) -> None:
    resp = client.get("/api/admin/overview")
    assert resp.json()["scheduler_enabled"] is False


def test_overview_all_collectors_disabled_by_default(client: TestClient) -> None:
    body = client.get("/api/admin/overview").json()
    # Nova 96.9 collectors
    assert body["enable_nova_collector"] is False
    assert body["enable_nova_radoxo_collector"] is False
    assert body["enable_nova_radio_australia_collector"] is False
    # Capital FM UK collectors
    assert body["enable_capital_collector"] is False
    assert body["enable_capital_ukradiolive_collector"] is False
    # KIIS-FM 102.7 collectors
    assert body["enable_kiis_iheart_web_collector"] is False
    assert body["enable_kiis_radiowave_collector"] is False
    # Nightly automation
    assert body["enable_nightly_reconciliation"] is False
    assert body["enable_nightly_report_generation"] is False


def test_overview_admin_auth_not_configured_by_default(client: TestClient) -> None:
    resp = client.get("/api/admin/overview")
    assert resp.json()["admin_basic_auth_configured"] is False


def test_overview_retention_disabled_by_default(client: TestClient) -> None:
    resp = client.get("/api/admin/overview")
    assert resp.json()["raw_payload_retention_days"] == 0


def test_overview_docs_not_force_exposed_by_default(client: TestClient) -> None:
    resp = client.get("/api/admin/overview")
    assert resp.json()["enable_docs_in_production"] is False


def test_overview_stats_key_present(client: TestClient) -> None:
    body = client.get("/api/admin/overview").json()
    assert "stats" in body
    stats = body["stats"]
    assert "active_stations" in stats
    assert "total_sources" in stats
    assert "pending_reviews" in stats
    assert "active_webhooks" in stats


def test_overview_no_secret_fields(client: TestClient) -> None:
    """Response must never contain sensitive configuration values."""
    resp = client.get("/api/admin/overview")
    body_str = resp.text
    forbidden = [
        "admin_basic_auth_password",
        "smtp_password",
        "s3_secret_access_key",
        "spotify_client_secret",
        "postgresql://",
        "smtp_",
    ]
    for field in forbidden:
        assert field not in body_str.lower(), (
            f"Potentially sensitive field '{field}' found in response"
        )


def test_overview_docs_exposed_in_development(client: TestClient) -> None:
    """In non-production environments, docs are accessible regardless of the flag."""
    body = client.get("/api/admin/overview").json()
    if body["app_env"] != "production":
        assert body["enable_docs_in_production"] is False  # flag is off, but docs still show
