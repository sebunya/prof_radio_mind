"""Tests for Alembic migrations/env.py URL handling.

The critical invariant: % characters in DATABASE_URL (common when openssl-generated
passwords are URL-encoded) must be escaped as %% before being passed to
configparser via config.set_main_option, otherwise configparser raises
InterpolationSyntaxError.
"""

from __future__ import annotations


def _build_sync_url(raw: str) -> str:
    """Replicate the env.py URL transformation logic."""
    sync_url = raw.replace("postgresql+asyncpg://", "postgresql://")
    return sync_url.replace("%", "%%")


def test_plain_url_unchanged() -> None:
    raw = "postgresql+asyncpg://rmias:simplepassword@db:5432/rmias"
    result = _build_sync_url(raw)
    assert result == "postgresql://rmias:simplepassword@db:5432/rmias"


def test_asyncpg_prefix_replaced() -> None:
    raw = "postgresql+asyncpg://user:pass@localhost:5432/mydb"
    result = _build_sync_url(raw)
    assert result.startswith("postgresql://")
    assert "asyncpg" not in result


def test_percent_in_password_escaped() -> None:
    """A URL-encoded special char in the password must become %% for configparser."""
    raw = "postgresql+asyncpg://rmias:p%40ss%25word@db:5432/rmias"
    result = _build_sync_url(raw)
    assert "%%" in result
    assert "%" not in result.replace("%%", "")


def test_percent_escaping_survives_configparser() -> None:
    """configparser must not raise InterpolationSyntaxError on the escaped URL."""
    import configparser

    raw = "postgresql+asyncpg://rmias:p%40ssw%25rd@db:5432/rmias"
    escaped = _build_sync_url(raw)

    cfg = configparser.ConfigParser()
    cfg.read_dict({"section": {"sqlalchemy.url": escaped}})
    # Should not raise; interpolated value has single % restored
    value = cfg.get("section", "sqlalchemy.url")
    assert "postgresql://" in value


def test_url_with_multiple_percent_chars() -> None:
    """Multiple % chars in a password are all escaped."""
    raw = "postgresql+asyncpg://rmias:p%40ss%25%26@db:5432/rmias"
    result = _build_sync_url(raw)
    # Count double-percent occurrences
    assert result.count("%%") == 3
