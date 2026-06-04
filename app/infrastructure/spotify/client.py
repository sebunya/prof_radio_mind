from __future__ import annotations

import asyncio
import base64
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from app.core.settings import settings

logger = logging.getLogger(__name__)


class SpotifyAuthError(Exception):
    """Exception raised when Spotify authentication fails."""
    pass


class SpotifyRateLimitError(Exception):
    """Exception raised when Spotify rate limit is exceeded."""
    pass


class SpotifyClient:
    """Client for interacting with the Spotify Web API."""

    def __init__(self) -> None:
        self._access_token: str | None = None
        self._token_expires_at: datetime | None = None
        self._lock = asyncio.Lock()

    async def get_access_token(self) -> str:
        """Retrieve a valid cached or new Spotify access token."""
        async with self._lock:
            now = datetime.now(UTC)
            if (
                self._access_token
                and self._token_expires_at
                and self._token_expires_at > now
            ):
                return self._access_token

            client_id = settings.spotify_client_id
            client_secret = settings.spotify_client_secret

            if not client_id or not client_secret:
                raise SpotifyAuthError("Spotify client credentials are not configured")

            auth_bytes = f"{client_id}:{client_secret}".encode()
            auth_b64 = base64.b64encode(auth_bytes).decode("utf-8")

            headers = {
                "Authorization": f"Basic {auth_b64}",
                "Content-Type": "application/x-www-form-urlencoded",
            }
            data = {"grant_type": "client_credentials"}

            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        settings.spotify_token_url,
                        headers=headers,
                        data=data,
                        timeout=settings.spotify_request_timeout_seconds,
                    )
                    if response.status_code != 200:
                        logger.error(
                            "Spotify token request failed status=%d body=%s",
                            response.status_code,
                            response.text,
                        )
                        raise SpotifyAuthError(
                            f"Token request failed status_code={response.status_code}"
                        )

                    res_json = response.json()
                    access_token = res_json.get("access_token")
                    expires_in = res_json.get("expires_in", 3600)

                    if not access_token:
                        raise SpotifyAuthError("No access token returned in response")

                    self._access_token = access_token
                    # Calculate safe cache expiry
                    cache_seconds = min(expires_in, settings.spotify_token_cache_seconds)
                    self._token_expires_at = datetime.now(UTC) + timedelta(
                        seconds=cache_seconds
                    )

                    logger.info("Successfully fetched new Spotify access token")
                    return access_token
            except Exception as e:
                if not isinstance(e, SpotifyAuthError):
                    logger.exception("Unexpected error fetching Spotify token")
                raise SpotifyAuthError(f"Authentication error: {e}") from e

    async def search_track(
        self, title: str, artist: str, isrc: str | None = None
    ) -> list[dict[str, Any]]:
        """Search for a track in Spotify catalog by ISRC or title/artist names."""
        token = await self.get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

        # Try queries: ISRC first if provided, then title + artist
        queries = []
        if isrc:
            queries.append(f"isrc:{isrc}")

        # Clean query strings to avoid Spotify search parser errors
        clean_title = title.replace('"', '').replace("'", "")
        clean_artist = artist.replace('"', '').replace("'", "")
        queries.append(f"track:\"{clean_title}\" artist:\"{clean_artist}\"")
        queries.append(f"\"{clean_title}\" \"{clean_artist}\"")

        last_err: Exception | str | None = None
        for query_str in queries:
            params: dict[str, str | int] = {
                "q": query_str,
                "type": "track",
                "limit": 10,
            }

            retries = 0
            max_retries = settings.spotify_max_retries
            while retries <= max_retries:
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.get(
                            f"{settings.spotify_api_base_url}/search",
                            headers=headers,
                            params=params,
                            timeout=settings.spotify_request_timeout_seconds,
                        )

                        if response.status_code == 429:
                            retry_after = int(response.headers.get("Retry-After", 3))
                            logger.warning(
                                "Spotify API rate limit hit. Sleeping for %d seconds",
                                retry_after,
                            )
                            await asyncio.sleep(retry_after)
                            retries += 1
                            continue

                        if response.status_code != 200:
                            logger.error(
                                "Spotify search API error status=%d body=%s",
                                response.status_code,
                                response.text,
                            )
                            last_err = f"API error status_code={response.status_code}"
                            break

                        items = response.json().get("tracks", {}).get("items", [])
                        if items:
                            return items

                        # No results for this query variation, try next query variant
                        break
                except Exception as e:
                    logger.warning("Spotify API search connection error: %s", e)
                    last_err = e
                    retries += 1
                    if retries <= max_retries:
                        await asyncio.sleep(1)

        if last_err:
            logger.error("Spotify search query failed: %s", last_err)
        return []
