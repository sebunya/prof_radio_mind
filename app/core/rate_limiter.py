"""Tiered in-memory sliding-window rate limiter + Starlette middleware.

Two tiers, keyed by client IP:
  WRITE   — all non-exempt endpoints             (settings.rate_limit_rpm, default 30)
  STRICT  — heavy ingest/import POST endpoints   (rate_limit_rpm // 3, min 5)

Exempt (never rate-limited):
  GET /health          — liveness probes
  /admin/*             — static assets
  /docs, /redoc, /openapi.json
  OPTIONS              — CORS preflight
  GET|POST /email-reports/unsubscribe   — public, time-sensitive

MVP: in-process only.  Swap for slowapi + Redis before horizontal scaling.
"""

from __future__ import annotations

import time
from collections import defaultdict

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

# ── Core limiter ─────────────────────────────────────────────────────────────


class InMemoryRateLimiter:
    """Sliding-window counter keyed by an arbitrary string (e.g., client IP)."""

    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._buckets: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str) -> bool:
        """Return True if key is within the limit, False if exceeded."""
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


# ── Singleton factories ───────────────────────────────────────────────────────

_limiter: InMemoryRateLimiter | None = None
_strict_limiter: InMemoryRateLimiter | None = None


def _build_default() -> InMemoryRateLimiter:
    from app.core.settings import settings

    return InMemoryRateLimiter(
        max_requests=settings.rate_limit_rpm,
        window_seconds=60,
    )


def _build_strict() -> InMemoryRateLimiter:
    from app.core.settings import settings

    limit = max(5, settings.rate_limit_rpm // 3)
    return InMemoryRateLimiter(max_requests=limit, window_seconds=60)


def get_limiter() -> InMemoryRateLimiter:
    global _limiter
    if _limiter is None:
        _limiter = _build_default()
    return _limiter


def get_strict_limiter() -> InMemoryRateLimiter:
    global _strict_limiter
    if _strict_limiter is None:
        _strict_limiter = _build_strict()
    return _strict_limiter


# ── Path config ───────────────────────────────────────────────────────────────

# Never rate-limited
_EXEMPT_PREFIXES = (
    "/health",
    "/admin",
    "/docs",
    "/redoc",
    "/openapi.json",
)
_EXEMPT_PATHS = frozenset({
    "/email-reports/unsubscribe",
})

# POST to these paths uses the strict (tighter) limiter
_STRICT_PREFIXES = (
    "/backfill/",
    "/manual-imports/",
    "/charts/aria/ingest",
    "/playlist/",
)


def _is_exempt(path: str, method: str) -> bool:
    if method == "OPTIONS":
        return True
    if any(path.startswith(p) for p in _EXEMPT_PREFIXES):
        return True
    return path in _EXEMPT_PATHS


def _is_strict(path: str, method: str) -> bool:
    return method == "POST" and any(
        path.startswith(p) or path == p.rstrip("/")
        for p in _STRICT_PREFIXES
    )


# ── Middleware ────────────────────────────────────────────────────────────────


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Global sliding-window rate limiter.

    Runs before route handlers.  Exempt paths pass through unconditionally.
    Heavy ingest POST endpoints use the strict tier; everything else uses the
    standard write tier.
    """

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        path = request.url.path
        method = request.method

        if _is_exempt(path, method):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        limiter = get_strict_limiter() if _is_strict(path, method) else get_limiter()

        if not limiter.is_allowed(client_ip):
            return JSONResponse(
                {"detail": "Rate limit exceeded — please slow down"},
                status_code=429,
                headers={"Retry-After": "60"},
            )

        return await call_next(request)


# ── Per-endpoint dependency (legacy / explicit use) ───────────────────────────


def require_not_rate_limited(request: Request) -> None:
    """FastAPI dependency — raises HTTP 429 if the client IP is over the limit.

    The global RateLimitMiddleware now handles most endpoints; this remains
    for routes that want an explicit per-endpoint check (e.g., manual imports).
    """
    client_ip = request.client.host if request.client else "unknown"
    if not get_limiter().is_allowed(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded — please slow down",
        )
