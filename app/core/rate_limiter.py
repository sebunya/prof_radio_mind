"""In-memory sliding-window rate limiter.

MVP implementation — single process only. Replace with a Redis-backed limiter
(e.g., slowapi + redis) before horizontal scaling.
"""

from __future__ import annotations

import time
from collections import defaultdict

from fastapi import HTTPException, Request


class InMemoryRateLimiter:
    """Sliding-window counter keyed by an arbitrary string (e.g., client IP)."""

    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._buckets: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str) -> bool:
        """Return True if the key is within the rate limit, False if exceeded."""
        now = time.monotonic()
        cutoff = now - self._window_seconds
        self._buckets[key] = [t for t in self._buckets[key] if t > cutoff]
        if len(self._buckets[key]) >= self._max_requests:
            return False
        self._buckets[key].append(now)
        return True

    def reset(self, key: str) -> None:
        """Clear counters for a key — used in tests."""
        self._buckets.pop(key, None)

    def reset_all(self) -> None:
        """Clear all counters — used in tests."""
        self._buckets.clear()


# Module-level singleton — configured from settings at first import.
def _build_default() -> InMemoryRateLimiter:
    from app.core.settings import settings

    return InMemoryRateLimiter(
        max_requests=settings.rate_limit_rpm,
        window_seconds=60,
    )


_limiter: InMemoryRateLimiter | None = None


def get_limiter() -> InMemoryRateLimiter:
    global _limiter
    if _limiter is None:
        _limiter = _build_default()
    return _limiter


def require_not_rate_limited(request: Request) -> None:
    """FastAPI dependency — raises HTTP 429 if the client IP is over the limit."""
    client_ip = request.client.host if request.client else "unknown"
    if not get_limiter().is_allowed(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded — please slow down",
        )
