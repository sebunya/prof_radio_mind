"""Tests for structured logging and enhanced /health endpoint."""

from __future__ import annotations

import json
import logging

import pytest
from fastapi.testclient import TestClient

from app.core.logging_config import _JsonFormatter, configure_logging

# --- JSON formatter ---

def test_json_formatter_produces_valid_json() -> None:
    formatter = _JsonFormatter()
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="hello world",
        args=(),
        exc_info=None,
    )
    output = formatter.format(record)
    parsed = json.loads(output)
    assert parsed["level"] == "INFO"
    assert parsed["logger"] == "test.logger"
    assert parsed["msg"] == "hello world"
    assert "ts" in parsed


def test_json_formatter_includes_ts_field() -> None:
    formatter = _JsonFormatter()
    record = logging.LogRecord(
        name="rmias",
        level=logging.WARNING,
        pathname="",
        lineno=0,
        msg="warn message",
        args=(),
        exc_info=None,
    )
    parsed = json.loads(formatter.format(record))
    # ts must be ISO-8601 UTC
    assert parsed["ts"].endswith("Z")
    assert "T" in parsed["ts"]


def test_json_formatter_includes_exception() -> None:
    formatter = _JsonFormatter()
    try:
        raise ValueError("boom")
    except ValueError:
        import sys

        exc_info = sys.exc_info()

    record = logging.LogRecord(
        name="rmias",
        level=logging.ERROR,
        pathname="",
        lineno=0,
        msg="error occurred",
        args=(),
        exc_info=exc_info,
    )
    parsed = json.loads(formatter.format(record))
    assert "exc" in parsed
    assert "ValueError" in parsed["exc"]


def test_configure_logging_sets_handler() -> None:
    configure_logging(level="WARNING")
    root = logging.getLogger()
    assert len(root.handlers) >= 1
    assert isinstance(root.handlers[0].formatter, _JsonFormatter)
    assert root.level == logging.WARNING
    # Restore to avoid polluting other tests
    configure_logging(level="INFO")


# --- Enhanced /health endpoint ---

@pytest.fixture
def client() -> TestClient:
    from app.main import app

    return TestClient(app)


def test_health_has_status_ok(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_health_has_components_field(client: TestClient) -> None:
    r = client.get("/health")
    body = r.json()
    assert "components" in body


def test_health_components_has_scheduler(client: TestClient) -> None:
    r = client.get("/health")
    components = r.json()["components"]
    assert "scheduler" in components
    # TestClient does NOT run the lifespan by default; scheduler is "stopped"
    assert components["scheduler"] in ("running", "stopped")


def test_health_components_has_review_queue_pending(client: TestClient) -> None:
    r = client.get("/health")
    components = r.json()["components"]
    assert "review_queue_pending" in components
    assert isinstance(components["review_queue_pending"], int)


def test_health_scheduler_running_with_lifespan() -> None:
    from app.main import app

    with TestClient(app, raise_server_exceptions=True) as lifespan_client:
        r = lifespan_client.get("/health")
        assert r.status_code == 200
        assert r.json()["components"]["scheduler"] == "running"
