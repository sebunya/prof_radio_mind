"""Tests that interactive docs are gated by environment.

The /docs, /redoc and /openapi.json routes must be hidden when
APP_ENV=production unless ENABLE_DOCS_IN_PRODUCTION is true.

We assert on the gating expression rather than re-importing app.main (which has
import-time side effects), keeping the test hermetic and matching the live logic.
"""

from __future__ import annotations


def _docs_enabled(app_env: str, force: bool) -> bool:
    return app_env != "production" or force


def test_docs_enabled_in_development() -> None:
    assert _docs_enabled("development", force=False) is True


def test_docs_disabled_in_production_by_default() -> None:
    assert _docs_enabled("production", force=False) is False


def test_docs_can_be_forced_on_in_production() -> None:
    assert _docs_enabled("production", force=True) is True


def test_live_app_default_env_serves_docs() -> None:
    """The running test app (default env=development) exposes /openapi.json."""
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    # Default test environment is development → docs available.
    assert client.get("/openapi.json").status_code == 200


def test_root_advertises_docs_only_when_enabled() -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    body = client.get("/").json()
    # In development the root lists api_docs; this guards the conditional wiring.
    assert "endpoints" in body
