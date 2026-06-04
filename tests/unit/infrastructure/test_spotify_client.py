from __future__ import annotations

import asyncio
import base64
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.settings import settings
from app.infrastructure.spotify.client import SpotifyAuthError, SpotifyClient


@pytest.fixture(autouse=True)
def mock_spotify_settings():
    with patch.object(settings, "spotify_client_id", "test_id"), \
         patch.object(settings, "spotify_client_secret", "test_secret"):
        yield


def test_get_access_token_success() -> None:
    client = SpotifyClient()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "access_token": "mock_token_123",
        "expires_in": 3600,
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        # Fetch token first time
        token = asyncio.run(client.get_access_token())
        assert token == "mock_token_123"

        # Verify Basic Auth credentials formatting and headers
        assert mock_post.call_count == 1
        call_kwargs = mock_post.call_args[1]
        headers = call_kwargs["headers"]
        data = call_kwargs["data"]

        expected_auth_str = f"{settings.spotify_client_id}:{settings.spotify_client_secret}"
        expected_auth_b64 = base64.b64encode(expected_auth_str.encode()).decode()
        assert headers["Authorization"] == f"Basic {expected_auth_b64}"
        assert data["grant_type"] == "client_credentials"

        # Fetch token second time (should hit cache)
        token2 = asyncio.run(client.get_access_token())
        assert token2 == "mock_token_123"
        assert mock_post.call_count == 1  # No additional API call


def test_get_access_token_expired_cache() -> None:
    client = SpotifyClient()
    client._access_token = "old_token"
    # Set expiration in the past
    client._token_expires_at = datetime.now(UTC) - timedelta(seconds=1)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "access_token": "new_token",
        "expires_in": 3600,
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        token = asyncio.run(client.get_access_token())
        assert token == "new_token"
        assert mock_post.call_count == 1


def test_get_access_token_error_handling() -> None:
    client = SpotifyClient()

    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        with pytest.raises(SpotifyAuthError) as exc_info:
            asyncio.run(client.get_access_token())
        assert "Token request failed" in str(exc_info.value)


def test_search_track_success() -> None:
    client = SpotifyClient()
    client._access_token = "valid_token"
    client._token_expires_at = datetime.now(UTC) + timedelta(hours=1)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "tracks": {
            "items": [
                {
                    "id": "track_1",
                    "name": "Levitating",
                    "artists": [{"name": "Dua Lipa"}],
                    "album": {"name": "Future Nostalgia"},
                    "popularity": 90,
                }
            ]
        }
    }

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response

        items = asyncio.run(client.search_track("Levitating", "Dua Lipa"))
        assert len(items) == 1
        assert items[0]["id"] == "track_1"

        # Verify correct headers and query parameters
        assert mock_get.call_count == 1
        call_kwargs = mock_get.call_args[1]
        assert call_kwargs["headers"]["Authorization"] == "Bearer valid_token"
        assert call_kwargs["params"]["q"] == 'track:"Levitating" artist:"Dua Lipa"'


def test_search_track_rate_limiting() -> None:
    client = SpotifyClient()
    client._access_token = "valid_token"
    client._token_expires_at = datetime.now(UTC) + timedelta(hours=1)

    mock_429 = MagicMock()
    mock_429.status_code = 429
    mock_429.headers = {"Retry-After": "1"}

    mock_200 = MagicMock()
    mock_200.status_code = 200
    mock_200.json.return_value = {
        "tracks": {"items": [{"id": "track_ok", "name": "Physical"}]}
    }

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = [mock_429, mock_200]

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            items = asyncio.run(client.search_track("Physical", "Dua Lipa"))
            assert len(items) == 1
            assert items[0]["id"] == "track_ok"

            # Check that rate limiter triggered a sleep and retried
            assert mock_sleep.call_count == 1
            assert mock_sleep.call_args[0][0] == 1
            assert mock_get.call_count == 2
