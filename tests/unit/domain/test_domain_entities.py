"""Domain entity and value object unit tests — no DB, no network."""

import hashlib
import uuid
from datetime import UTC, datetime

from app.domain.entities.collector_run import CollectorRun, CollectorStatus
from app.domain.entities.no_track_event import NoTrackEvent, NoTrackReason
from app.domain.entities.play_event import PlayEvent
from app.domain.entities.source import Source, SourceType
from app.domain.entities.station import Station
from app.domain.value_objects.raw_payload import RawPayload


def test_station_create_assigns_uuid() -> None:
    s = Station.create("Nova 96.9", "NOVA969", frequency="96.9", city="Sydney")
    assert isinstance(s.id, uuid.UUID)
    assert s.call_sign == "NOVA969"
    assert s.country_code == "AU"


def test_source_type_enum_values() -> None:
    assert SourceType.RADIOWAVE == "radiowave"
    assert SourceType.IHEART == "iheart"
    assert SourceType.MANUAL_CSV == "manual_csv"


def test_source_create() -> None:
    station_id = uuid.uuid4()
    src = Source.create(
        station_id, SourceType.RADIOWAVE, "Nova Radiowave", config={"idds": "11129"}
    )
    assert src.station_id == station_id
    assert src.source_type == SourceType.RADIOWAVE
    assert src.config == {"idds": "11129"}


def test_collector_run_status_transition() -> None:
    run = CollectorRun.create(uuid.uuid4(), uuid.uuid4())
    assert run.status == CollectorStatus.SCHEDULED
    run.transition(CollectorStatus.FETCHING)
    assert run.status == CollectorStatus.FETCHING


def test_collector_run_fail_sets_message() -> None:
    run = CollectorRun.create(uuid.uuid4(), uuid.uuid4())
    run.fail("connection refused")
    assert run.status == CollectorStatus.FAILED
    assert run.error_message == "connection refused"


def test_play_event_create() -> None:
    now = datetime.now(tz=UTC)
    ev = PlayEvent.create(
        uuid.uuid4(),
        uuid.uuid4(),
        uuid.uuid4(),
        played_at=now,
        raw_artist="Tame Impala",
        raw_title="The Less I Know The Better",
        source_event_id="abc123",
    )
    assert ev.raw_artist == "Tame Impala"
    assert ev.source_event_id == "abc123"


def test_no_track_event_http_204() -> None:
    now = datetime.now(tz=UTC)
    ev = NoTrackEvent.create(
        uuid.uuid4(),
        uuid.uuid4(),
        uuid.uuid4(),
        observed_at=now,
        reason=NoTrackReason.SOURCE_HTTP_204,
        raw_http_status=204,
    )
    assert ev.reason == NoTrackReason.SOURCE_HTTP_204
    assert ev.raw_http_status == 204


def test_raw_payload_sha256() -> None:
    data = b"<html>test fixture</html>"
    payload = RawPayload.create(
        uuid.uuid4(),
        uuid.uuid4(),
        data,
        "/data/raw_payloads/test.html",
        content_type="text/html",
        http_status=200,
    )
    assert payload.sha256 == hashlib.sha256(data).hexdigest()
    assert payload.byte_size == len(data)
    assert payload.http_status == 200


def test_raw_payload_is_frozen() -> None:
    data = b"immutable"
    payload = RawPayload.create(uuid.uuid4(), uuid.uuid4(), data, "/tmp/x.html")
    try:
        payload.sha256 = "tampered"  # type: ignore[misc]
        assert False, "should have raised"
    except Exception:
        pass


def test_collector_status_all_values_present() -> None:
    expected = {
        "scheduled", "validating", "fetching", "raw_stored", "parsed",
        "normalized", "persisted", "completed", "partial_success", "failed",
        "no_content", "timeout", "blocked", "rate_limited", "schema_changed",
        "auth_required", "manual_review_required", "degraded", "fallback_used",
    }
    actual = {s.value for s in CollectorStatus}
    assert actual == expected
