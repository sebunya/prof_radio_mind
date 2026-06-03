"""Proxy-aware httpx client factory with User-Agent rotation.

Reads PROXY_URLS from settings (comma-separated list of http:// or socks5:// URLs).
Each call to build_client() advances the round-robin index so successive
collector runs cycle through all available IPs.

When PROXY_URLS is empty the client connects directly (development default).

Setting up cheap Hetzner proxy nodes:
  1. Spin up a CX11 (2 EUR/month) in a different Hetzner datacenter.
  2. Install dante-server (SOCKS5) or tinyproxy (HTTP).
  3. Add the server's IP to PROXY_URLS as socks5://user:pass@<ip>:1080
  4. Hetzner Additional IPs (1 EUR/month each) can be added to a single server
     so you can rotate IPs without additional compute cost.
"""

from __future__ import annotations

import asyncio
import random

import httpx

from app.core.settings import settings

# Browser User-Agent pool — rotate so requests vary the User-Agent header
_USER_AGENTS: list[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]


class ProxyPool:
    """Thread-safe round-robin proxy pool.

    Supports http://, https://, socks5:// and socks5h:// URLs.
    Falls back to direct (no proxy) when the pool is empty.
    """

    def __init__(self, proxy_urls: list[str]) -> None:
        self._urls = [u.strip() for u in proxy_urls if u.strip()]
        self._index = 0
        self._lock = asyncio.Lock()

    @property
    def has_proxies(self) -> bool:
        return bool(self._urls)

    async def next_url(self) -> str | None:
        if not self._urls:
            return None
        async with self._lock:
            url = self._urls[self._index % len(self._urls)]
            self._index += 1
            return url

    def __len__(self) -> int:
        return len(self._urls)


def _parse_proxy_urls() -> list[str]:
    raw = settings.proxy_urls
    if not raw:
        return []
    return [u.strip() for u in raw.split(",") if u.strip()]


# Module-level singleton — rebuilt if settings change (tests only)
_pool: ProxyPool | None = None


def get_proxy_pool() -> ProxyPool:
    global _pool
    if _pool is None:
        _pool = ProxyPool(_parse_proxy_urls())
    return _pool


async def build_client(timeout: float = 30.0) -> httpx.AsyncClient:
    """Return an httpx.AsyncClient configured with the next proxy and a rotated User-Agent."""
    proxy_url = await get_proxy_pool().next_url()
    headers = {"User-Agent": random.choice(_USER_AGENTS)}

    if proxy_url:
        return httpx.AsyncClient(proxy=proxy_url, timeout=timeout, headers=headers)
    return httpx.AsyncClient(timeout=timeout, headers=headers)
