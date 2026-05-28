import os

# Disable Sentry before any app module is imported so the init block is skipped.
# This prevents test runs from sending spurious events to the real Sentry project.
os.environ.setdefault("SENTRY_DSN", "")

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_rate_limiters() -> None:
    """Clear rate-limiter buckets before every test so tests don't interfere."""
    from app.core.rate_limiter import get_limiter, get_strict_limiter

    get_limiter().reset_all()
    get_strict_limiter().reset_all()
    yield  # type: ignore[misc]
    get_limiter().reset_all()
    get_strict_limiter().reset_all()
