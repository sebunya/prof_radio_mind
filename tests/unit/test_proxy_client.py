"""Tests for proxy pool and HTTP client factory."""

from __future__ import annotations

import pytest

from app.infrastructure.http.client import ProxyPool, build_client


def test_proxy_pool_empty_returns_none_url() -> None:
    pool = ProxyPool([])
    assert not pool.has_proxies
    assert len(pool) == 0


@pytest.mark.anyio
async def test_proxy_pool_next_url_none_when_empty() -> None:
    pool = ProxyPool([])
    assert await pool.next_url() is None


@pytest.mark.anyio
async def test_proxy_pool_round_robins() -> None:
    pool = ProxyPool(["http://proxy1:8080", "http://proxy2:8080"])
    first = await pool.next_url()
    second = await pool.next_url()
    third = await pool.next_url()
    assert first == "http://proxy1:8080"
    assert second == "http://proxy2:8080"
    assert third == "http://proxy1:8080"  # wraps back


def test_proxy_pool_strips_whitespace() -> None:
    pool = ProxyPool(["  http://proxy1:8080  ", " http://proxy2:8080"])
    assert len(pool) == 2


@pytest.mark.anyio
async def test_build_client_returns_httpx_client() -> None:
    import httpx

    client = await build_client(timeout=5.0)
    assert isinstance(client, httpx.AsyncClient)
    await client.aclose()


@pytest.mark.anyio
async def test_build_client_adds_user_agent() -> None:
    client = await build_client()
    # User-Agent is set in the default headers
    assert "User-Agent" in client.headers
    assert "Mozilla" in client.headers["User-Agent"]
    await client.aclose()
