"""Tests for the optional /admin HTTP Basic auth middleware and docs gating."""

from __future__ import annotations

import base64

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.admin_auth import AdminBasicAuthMiddleware


def _make_app() -> FastAPI:
    app = FastAPI()

    @app.get("/admin/thing")
    async def admin_thing() -> dict[str, str]:
        return {"ok": "admin"}

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"ok": "health"}

    app.add_middleware(AdminBasicAuthMiddleware)
    return app


def _basic(user: str, password: str) -> dict[str, str]:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def test_admin_open_when_no_credentials_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default: both creds empty → /admin stays open (live route never broken)."""
    from app.core.settings import settings

    monkeypatch.setattr(settings, "admin_basic_auth_user", "")
    monkeypatch.setattr(settings, "admin_basic_auth_password", "")

    client = TestClient(_make_app())
    assert client.get("/admin/thing").status_code == 200


def test_admin_requires_auth_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.settings import settings

    monkeypatch.setattr(settings, "admin_basic_auth_user", "ops")
    monkeypatch.setattr(settings, "admin_basic_auth_password", "s3cret")

    client = TestClient(_make_app())
    r = client.get("/admin/thing")
    assert r.status_code == 401
    assert "WWW-Authenticate" in r.headers


def test_admin_allows_correct_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.settings import settings

    monkeypatch.setattr(settings, "admin_basic_auth_user", "ops")
    monkeypatch.setattr(settings, "admin_basic_auth_password", "s3cret")

    client = TestClient(_make_app())
    r = client.get("/admin/thing", headers=_basic("ops", "s3cret"))
    assert r.status_code == 200


def test_admin_rejects_wrong_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.settings import settings

    monkeypatch.setattr(settings, "admin_basic_auth_user", "ops")
    monkeypatch.setattr(settings, "admin_basic_auth_password", "s3cret")

    client = TestClient(_make_app())
    assert client.get("/admin/thing", headers=_basic("ops", "wrong")).status_code == 401


def test_non_admin_paths_never_require_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.settings import settings

    monkeypatch.setattr(settings, "admin_basic_auth_user", "ops")
    monkeypatch.setattr(settings, "admin_basic_auth_password", "s3cret")

    client = TestClient(_make_app())
    # /health is outside /admin → unaffected even when auth is enabled
    assert client.get("/health").status_code == 200
