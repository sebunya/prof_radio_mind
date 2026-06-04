"""Optional HTTP Basic auth gate for the /admin SPA and /api/admin routes.

Disabled by default. The live /admin route stays open unless BOTH
ADMIN_BASIC_AUTH_USER and ADMIN_BASIC_AUTH_PASSWORD are configured, so a
partial / empty configuration can never lock operators out by accident.

When enabled, paths under /admin AND /api/admin require credentials;
the public root, /health and all other API routes are unaffected.

The guard is boundary-safe: it requires either an exact path match or a
'/' separator immediately after the prefix, so paths such as /administrator
or /api/administer are never accidentally protected.
"""

from __future__ import annotations

import base64
import binascii
import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.core.settings import settings

_REALM = 'Basic realm="RMIAS Admin", charset="UTF-8"'


def _is_protected_admin_path(path: str) -> bool:
    """Return True for paths that require Basic auth credentials.

    Guards both the /admin SPA and the /api/admin JSON routes.
    Boundary-safe: requires an exact match or an immediately following '/'
    so that paths like /administrator or /api/administer are never matched.
    """
    return (
        path == "/admin"
        or path.startswith("/admin/")
        or path == "/api/admin"
        or path.startswith("/api/admin/")
    )


class AdminBasicAuthMiddleware(BaseHTTPMiddleware):
    """Require HTTP Basic auth for /admin paths when credentials are configured."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self._user = settings.admin_basic_auth_user
        self._password = settings.admin_basic_auth_password
        # Enabled only when both halves of the credential are present.
        self._enabled = bool(self._user and self._password)

    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        if not self._enabled or not _is_protected_admin_path(request.url.path):
            return await call_next(request)

        if self._is_authorized(request.headers.get("Authorization")):
            return await call_next(request)

        return Response(
            status_code=401,
            headers={"WWW-Authenticate": _REALM},
            content="Authentication required",
        )

    def _is_authorized(self, header: str | None) -> bool:
        if not header or not header.startswith("Basic "):
            return False
        try:
            decoded = base64.b64decode(header[6:]).decode("utf-8")
        except (binascii.Error, UnicodeDecodeError):
            return False
        user, _, password = decoded.partition(":")
        # constant-time comparison on both halves
        user_ok = secrets.compare_digest(user, self._user)
        pass_ok = secrets.compare_digest(password, self._password)
        return user_ok and pass_ok
