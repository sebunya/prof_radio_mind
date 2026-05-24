"""Tests for local and S3 storage backends."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.infrastructure.storage.backend import LocalBackend, get_storage_backend


@pytest.mark.anyio
async def test_local_backend_write_and_read() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        backend = LocalBackend(tmpdir)
        data = b"hello raw payload"
        path = await backend.write("2026/05/24/test.bin", data)
        assert Path(path).exists()
        result = await backend.read("2026/05/24/test.bin")
        assert result == data


@pytest.mark.anyio
async def test_local_backend_exists_true() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        backend = LocalBackend(tmpdir)
        await backend.write("file.bin", b"data")
        assert await backend.exists("file.bin") is True


@pytest.mark.anyio
async def test_local_backend_exists_false() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        backend = LocalBackend(tmpdir)
        assert await backend.exists("missing.bin") is False


@pytest.mark.anyio
async def test_local_backend_creates_parent_dirs() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        backend = LocalBackend(tmpdir)
        await backend.write("deep/nested/dir/file.bin", b"nested")
        assert (Path(tmpdir) / "deep/nested/dir/file.bin").exists()


def test_get_storage_backend_returns_local_when_no_s3_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.core.settings.settings.s3_endpoint_url", "")
    backend = get_storage_backend()
    assert isinstance(backend, LocalBackend)


def test_get_storage_backend_returns_s3_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.infrastructure.storage.backend import S3Backend

    monkeypatch.setattr("app.core.settings.settings.s3_endpoint_url", "https://fsn1.your-objectstorage.com")
    monkeypatch.setattr("app.core.settings.settings.s3_access_key_id", "key")
    monkeypatch.setattr("app.core.settings.settings.s3_secret_access_key", "secret")
    backend = get_storage_backend()
    assert isinstance(backend, S3Backend)
