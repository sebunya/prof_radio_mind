"""Deduplication logic for play events.

Deduplication order:
  1. Exact source_event_id match (preferred — most reliable)
  2. Fingerprint match within a time window (fallback)

Returns True if the event is a duplicate (should be skipped or flagged).
No DB calls — takes pre-loaded sets of known IDs/fingerprints.
"""

from __future__ import annotations

from app.application.normalization.normalizer import compute_fingerprint


def is_duplicate_by_source_event_id(
    source_event_id: str,
    known_source_event_ids: set[str],
) -> bool:
    """Returns True if this source_event_id has already been seen."""
    return source_event_id in known_source_event_ids


def is_duplicate_by_fingerprint(
    artist: str,
    title: str,
    known_fingerprints: set[str],
) -> bool:
    """Returns True if a matching (artist, title) fingerprint has already been seen."""
    fp = compute_fingerprint(artist, title)
    return fp in known_fingerprints


def compute_event_fingerprint(artist: str, title: str) -> str:
    """Compute the deduplication fingerprint for a play event."""
    return compute_fingerprint(artist, title)
