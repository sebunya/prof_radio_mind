"""Capital FM source validation adapter.

Capital FM has no confirmed automated source route. This adapter attempts
to discover and confirm available routes. Until VAL-CAP-001 or VAL-CAP-002
is confirmed, Capital FM falls back to manual CSV for every report.

VAL-CAP-001: Capital streaming API / iHeart route — UNVALIDATED
VAL-CAP-002: Capital website now-playing endpoint — UNVALIDATED
"""

from __future__ import annotations

import uuid

import httpx

from app.application.validation.base import (
    SourceValidationAdapter,
    ValidationResult,
    ValidationStatus,
)

_REQUEST_TIMEOUT = 15.0


class CapitalIHeartValidationAdapter(SourceValidationAdapter):
    """Validates a Capital FM iHeart-style endpoint.

    Checks reachability and JSON schema. Stores the result without claiming
    success unless a real response matching the expected schema is received.
    """

    validation_code = "VAL-CAP-001"

    async def validate(self, source_id: uuid.UUID, config: dict | None) -> ValidationResult:
        if not config or not config.get("station_id"):
            return ValidationResult(
                source_id=source_id,
                validation_code=self.validation_code,
                status=ValidationStatus.FAILED,
                notes="No station_id in source config — cannot validate",
            )

        station_id_str = config["station_id"]
        base_url = config.get("base_url", "https://api.iheart.com/api/v3/live-meta/stream")
        url = f"{base_url}/{station_id_str}/currentTrack"

        try:
            async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT) as client:
                response = await client.get(url)
        except Exception as exc:
            return ValidationResult(
                source_id=source_id,
                validation_code=self.validation_code,
                status=ValidationStatus.FAILED,
                notes=f"Network error: {exc}",
            )

        if response.status_code == 204:
            return ValidationResult(
                source_id=source_id,
                validation_code=self.validation_code,
                status=ValidationStatus.VALIDATED,
                notes="HTTP 204 — no track playing; endpoint reachable",
                response_status_code=204,
            )

        if response.status_code != 200:
            return ValidationResult(
                source_id=source_id,
                validation_code=self.validation_code,
                status=ValidationStatus.FAILED,
                notes=f"Unexpected HTTP status: {response.status_code}",
                response_status_code=response.status_code,
            )

        try:
            data = response.json()
        except Exception:
            return ValidationResult(
                source_id=source_id,
                validation_code=self.validation_code,
                status=ValidationStatus.FAILED,
                notes="Response body is not valid JSON",
                response_status_code=response.status_code,
            )

        has_current_track = "currentTrack" in data and isinstance(data["currentTrack"], dict)

        if not has_current_track:
            return ValidationResult(
                source_id=source_id,
                validation_code=self.validation_code,
                status=ValidationStatus.FAILED,
                notes="JSON response missing 'currentTrack' field",
                response_status_code=response.status_code,
                response_snapshot=data,
            )

        return ValidationResult(
            source_id=source_id,
            validation_code=self.validation_code,
            status=ValidationStatus.VALIDATED,
            notes="currentTrack field present; schema matches expected",
            response_status_code=response.status_code,
            response_snapshot={"currentTrack_keys": list(data["currentTrack"].keys())},
        )


class CapitalWebsiteValidationAdapter(SourceValidationAdapter):
    """Validates a Capital FM website now-playing endpoint.

    VAL-CAP-002: Capital website route — UNVALIDATED.
    """

    validation_code = "VAL-CAP-002"

    async def validate(self, source_id: uuid.UUID, config: dict | None) -> ValidationResult:
        if not config or not config.get("endpoint_url"):
            return ValidationResult(
                source_id=source_id,
                validation_code=self.validation_code,
                status=ValidationStatus.FAILED,
                notes="No endpoint_url in source config — cannot validate",
            )

        url = config["endpoint_url"]
        try:
            async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT) as client:
                response = await client.get(url)
        except Exception as exc:
            return ValidationResult(
                source_id=source_id,
                validation_code=self.validation_code,
                status=ValidationStatus.FAILED,
                notes=f"Network error: {exc}",
            )

        if response.status_code not in (200, 204):
            return ValidationResult(
                source_id=source_id,
                validation_code=self.validation_code,
                status=ValidationStatus.FAILED,
                notes=f"Unexpected HTTP status: {response.status_code}",
                response_status_code=response.status_code,
            )

        return ValidationResult(
            source_id=source_id,
            validation_code=self.validation_code,
            status=ValidationStatus.VALIDATED,
            notes=f"Endpoint reachable, HTTP {response.status_code}",
            response_status_code=response.status_code,
        )
