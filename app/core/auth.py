"""API key authentication dependency.

Set API_KEY in the environment to enable auth. If API_KEY is empty (default),
auth is disabled and all requests pass through — intended for local development only.

Usage:
    @router.post("/endpoint", dependencies=[Depends(require_api_key)])
"""

from __future__ import annotations

import secrets

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from app.core.settings import settings

_header_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(api_key: str | None = Security(_header_scheme)) -> None:
    """FastAPI dependency — raises HTTP 401 if API_KEY is set and the header is wrong."""
    configured = settings.api_key
    if not configured:
        return  # auth disabled in development

    if not api_key:
        raise HTTPException(status_code=401, detail="X-API-Key header is required")

    if not secrets.compare_digest(api_key, configured):
        raise HTTPException(status_code=401, detail="Invalid API key")
