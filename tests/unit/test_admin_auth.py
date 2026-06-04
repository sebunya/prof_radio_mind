"""Tests for the optional /admin and /api/admin HTTP Basic auth middleware."""

from __future__ import annotations

import base64

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.admin_auth import AdminBasicAuthMiddleware, _is_protected_admin_path

# ---------------------------------------------------------------------------
# Boundary-safe path helper tests
# ---------------------------------------------------------------------------


class TestIsProtectedAdminPath:
    """Unit tests for the _is_protected_admin_path boundary-safe helper."""

    def test_admin_exact(self) -> None:
        assert _is_protected_admin_path("/admin") is True

    def test_admin_root(self) -> None:
        assert _is_protected_admin_path("/admin/") is True

    def test_admin_static_asset(self) -> None:
        assert _is_protected_admin_path("/admin/js/app.js") is True

    def test_api_admin_exact(self) -> None:
        assert _is_protected_admin_path("/api/admin") is True

    def test_api_admin_metadata_readiness(self) -> None:
        assert _is_protected_admin_path("/api/admin/metadata-readiness") is True

    def test_api_admin_overview(self) -> None:
        assert _is_protected_admin_path("/api/admin/overview") is True

    def test_api_admin_source_health(self) -> None:
        assert _is_protected_admin_path("/api/admin/source-health") is True

    def test_root_not_protected(self) -> None:
        assert _is_protected_admin_path("/") is False

    def test_health_not_protected(self) -> None:
        assert _is_protected_admin_path("/health") is False

    def test_api_stations_not_protected(self) -> None:
        assert _is_protected_admin_path("/api/stations") is False

    def test_administrator_not_protected(self) -> None:
        """Boundary check: /administrator must NOT be caught by /admin guard."""
        assert _is_protected_admin_path("/administrator") is False

    def test_administrator_path_not_protected(self) -> None:
        assert _is_protected_admin_path("/administrator/settings") is False

    def test_api_administrator_not_protected(self) -> None:
        """Boundary check: /api/administrator must NOT be caught by /api/admin guard."""
        assert _is_protected_admin_path("/api/administrator") is False

    def test_api_administer_not_protected(self) -> None:
        assert _is_protected_admin_path("/api/administer") is False


# ---------------------------------------------------------------------------
# Middleware integration tests
# ---------------------------------------------------------------------------


def _make_app() -> FastAPI:
    """Create a minimal FastAPI app with all four protected path types registered."""
    app = FastAPI()

    @app.get("/admin/thing")
    async def admin_thing() -> dict[str, str]:
        return {"ok": "admin"}

    @app.get("/admin/js/app.js")
    async def admin_static() -> dict[str, str]:
        return {"ok": "admin_static"}

    @app.get("/api/admin/metadata-readiness")
    async def metadata_readiness() -> dict[str, str]:
        return {"ok": "metadata_readiness"}

    @app.get("/api/admin/overview")
    async def overview() -> dict[str, str]:
        return {"ok": "overview"}

    @app.get("/")
    async def root() -> dict[str, str]:
        return {"ok": "root"}

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"ok": "health"}

    @app.get("/api/stations")
    async def stations() -> dict[str, str]:
        return {"ok": "stations"}

    app.add_middleware(AdminBasicAuthMiddleware)
    return app


def _basic(user: str, password: str) -> dict[str, str]:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


# --- Open by default (no credentials configured) ---


def test_admin_open_when_no_credentials_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default: both creds empty → /admin stays open (live route never broken)."""
    from app.core.settings import settings

    monkeypatch.setattr(settings, "admin_basic_auth_user", "")
    monkeypatch.setattr(settings, "admin_basic_auth_password", "")

    client = TestClient(_make_app())
    assert client.get("/admin/thing").status_code == 200


def test_api_admin_open_when_no_credentials_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default: both creds empty → /api/admin stays open for backward compat."""
    from app.core.settings import settings

    monkeypatch.setattr(settings, "admin_basic_auth_user", "")
    monkeypatch.setattr(settings, "admin_basic_auth_password", "")

    client = TestClient(_make_app())
    assert client.get("/api/admin/metadata-readiness").status_code == 200


# --- Unauthenticated when credentials configured ---


def test_admin_requires_auth_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.settings import settings

    monkeypatch.setattr(settings, "admin_basic_auth_user", "ops")
    monkeypatch.setattr(settings, "admin_basic_auth_password", "s3cret")

    client = TestClient(_make_app())
    r = client.get("/admin/thing")
    assert r.status_code == 401
    assert "WWW-Authenticate" in r.headers


def test_admin_static_requires_auth_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.settings import settings

    monkeypatch.setattr(settings, "admin_basic_auth_user", "ops")
    monkeypatch.setattr(settings, "admin_basic_auth_password", "s3cret")

    client = TestClient(_make_app())
    assert client.get("/admin/js/app.js").status_code == 401


def test_api_admin_metadata_readiness_requires_auth_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.settings import settings

    monkeypatch.setattr(settings, "admin_basic_auth_user", "ops")
    monkeypatch.setattr(settings, "admin_basic_auth_password", "s3cret")

    client = TestClient(_make_app())
    assert client.get("/api/admin/metadata-readiness").status_code == 401


def test_api_admin_overview_requires_auth_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.settings import settings

    monkeypatch.setattr(settings, "admin_basic_auth_user", "ops")
    monkeypatch.setattr(settings, "admin_basic_auth_password", "s3cret")

    client = TestClient(_make_app())
    assert client.get("/api/admin/overview").status_code == 401


# --- Authenticated access ---


def test_admin_allows_correct_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.settings import settings

    monkeypatch.setattr(settings, "admin_basic_auth_user", "ops")
    monkeypatch.setattr(settings, "admin_basic_auth_password", "s3cret")

    client = TestClient(_make_app())
    r = client.get("/admin/thing", headers=_basic("ops", "s3cret"))
    assert r.status_code == 200


def test_api_admin_allows_correct_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.settings import settings

    monkeypatch.setattr(settings, "admin_basic_auth_user", "ops")
    monkeypatch.setattr(settings, "admin_basic_auth_password", "s3cret")

    client = TestClient(_make_app())
    r = client.get("/api/admin/metadata-readiness", headers=_basic("ops", "s3cret"))
    assert r.status_code == 200


def test_api_admin_overview_allows_correct_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.settings import settings

    monkeypatch.setattr(settings, "admin_basic_auth_user", "ops")
    monkeypatch.setattr(settings, "admin_basic_auth_password", "s3cret")

    client = TestClient(_make_app())
    r = client.get("/api/admin/overview", headers=_basic("ops", "s3cret"))
    assert r.status_code == 200


# --- Reject wrong credentials ---


def test_admin_rejects_wrong_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.settings import settings

    monkeypatch.setattr(settings, "admin_basic_auth_user", "ops")
    monkeypatch.setattr(settings, "admin_basic_auth_password", "s3cret")

    client = TestClient(_make_app())
    assert client.get("/admin/thing", headers=_basic("ops", "wrong")).status_code == 401


def test_api_admin_rejects_wrong_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.settings import settings

    monkeypatch.setattr(settings, "admin_basic_auth_user", "ops")
    monkeypatch.setattr(settings, "admin_basic_auth_password", "s3cret")

    client = TestClient(_make_app())
    assert (
        client.get("/api/admin/metadata-readiness", headers=_basic("ops", "wrong")).status_code
        == 401
    )


# --- Public routes remain public ---


def test_non_admin_paths_never_require_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.settings import settings

    monkeypatch.setattr(settings, "admin_basic_auth_user", "ops")
    monkeypatch.setattr(settings, "admin_basic_auth_password", "s3cret")

    client = TestClient(_make_app())
    # /health is outside /admin → unaffected even when auth is enabled
    assert client.get("/health").status_code == 200


def test_root_remains_public_when_auth_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.settings import settings

    monkeypatch.setattr(settings, "admin_basic_auth_user", "ops")
    monkeypatch.setattr(settings, "admin_basic_auth_password", "s3cret")

    client = TestClient(_make_app())
    assert client.get("/").status_code == 200


def test_api_stations_remains_public_when_auth_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.settings import settings

    monkeypatch.setattr(settings, "admin_basic_auth_user", "ops")
    monkeypatch.setattr(settings, "admin_basic_auth_password", "s3cret")

    client = TestClient(_make_app())
    assert client.get("/api/stations").status_code == 200
