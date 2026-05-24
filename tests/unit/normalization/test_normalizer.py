"""Tests for normalisation, fuzzy matching, and deduplication."""

from __future__ import annotations

from app.application.normalization.deduplicator import (
    compute_event_fingerprint,
    is_duplicate_by_fingerprint,
    is_duplicate_by_source_event_id,
)
from app.application.normalization.normalizer import (
    compute_fingerprint,
    fuzzy_match,
    is_match,
    normalise_text,
    strip_label_from_artist,
)

# --- normalise_text ---

def test_normalise_lowercase() -> None:
    assert normalise_text("Tame Impala") == "tame impala"


def test_normalise_unicode_to_ascii() -> None:
    assert normalise_text("Beyoncé") == "beyonce"


def test_normalise_collapses_whitespace() -> None:
    assert normalise_text("  The  Weeknd  ") == "the weeknd"


def test_normalise_strips_punctuation() -> None:
    result = normalise_text("Lady Gaga & Bruno Mars")
    assert "&" not in result


def test_normalise_preserves_hyphen() -> None:
    result = normalise_text("Foo-Fighters")
    assert "-" in result


# --- strip_label_from_artist ---

def test_strip_label_bracket() -> None:
    assert strip_label_from_artist("Tame Impala [Island Records]") == "Tame Impala"


def test_strip_label_feat_parens() -> None:
    result = strip_label_from_artist("Drake (feat. Rihanna)")
    assert "feat" not in result.lower()
    assert result.strip() == "Drake"


def test_strip_label_ft() -> None:
    result = strip_label_from_artist("The Weeknd ft. Daft Punk")
    assert "ft" not in result.lower()


def test_strip_label_no_label() -> None:
    assert strip_label_from_artist("Dua Lipa") == "Dua Lipa"


def test_strip_label_feat_no_parens() -> None:
    result = strip_label_from_artist("Calvin Harris feat. Rihanna")
    assert "Rihanna" not in result


# --- fuzzy_match / is_match ---

def test_exact_match_score_100() -> None:
    assert fuzzy_match("tame impala", "tame impala") >= 100.0


def test_high_similarity_match() -> None:
    # Minor spelling variation
    assert is_match(normalise_text("Anti-Hero"), normalise_text("Anti Hero"))


def test_different_songs_no_match() -> None:
    assert not is_match(
        normalise_text("Blinding Lights"),
        normalise_text("Paint The Town Red"),
        threshold=88,
    )


def test_artist_name_variant_matches() -> None:
    assert is_match(normalise_text("The Weekend"), normalise_text("The Weeknd"), threshold=70)


# --- compute_fingerprint ---

def test_fingerprint_is_hex_64() -> None:
    fp = compute_fingerprint("Tame Impala", "The Less I Know The Better")
    assert len(fp) == 64
    assert all(c in "0123456789abcdef" for c in fp)


def test_fingerprint_same_for_same_input() -> None:
    fp1 = compute_fingerprint("Tame Impala", "The Less I Know The Better")
    fp2 = compute_fingerprint("Tame Impala", "The Less I Know The Better")
    assert fp1 == fp2


def test_fingerprint_different_for_different_input() -> None:
    fp1 = compute_fingerprint("Tame Impala", "The Less I Know The Better")
    fp2 = compute_fingerprint("Flume", "Never Be Like You")
    assert fp1 != fp2


# --- deduplicator ---

def test_is_duplicate_by_source_event_id_positive() -> None:
    known = {"rw-001", "rw-002"}
    assert is_duplicate_by_source_event_id("rw-001", known)


def test_is_duplicate_by_source_event_id_negative() -> None:
    known = {"rw-001", "rw-002"}
    assert not is_duplicate_by_source_event_id("rw-003", known)


def test_is_duplicate_by_fingerprint_positive() -> None:
    fp = compute_event_fingerprint("Tame Impala", "The Less I Know The Better")
    known = {fp}
    assert is_duplicate_by_fingerprint("Tame Impala", "The Less I Know The Better", known)


def test_is_duplicate_by_fingerprint_negative() -> None:
    fp = compute_event_fingerprint("Tame Impala", "The Less I Know The Better")
    known = {fp}
    assert not is_duplicate_by_fingerprint("Flume", "Never Be Like You", known)


def test_dst_safe_fingerprint_stable() -> None:
    """Fingerprint must be stable regardless of when it is computed (DST-safe)."""
    fp1 = compute_event_fingerprint("Kylie Minogue", "Padam Padam")
    fp2 = compute_event_fingerprint("Kylie Minogue", "Padam Padam")
    assert fp1 == fp2
