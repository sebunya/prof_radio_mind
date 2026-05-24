"""Artist and title normalisation.

Produces a normalised string for fuzzy matching and deduplication.
Normalised strings are used for:
  - Artist entity lookup / creation (artists.name_normalised)
  - Song entity lookup / creation (songs.title_normalised)
  - Deduplication fingerprint generation

No database calls in this module — pure transformation functions.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata

from rapidfuzz import fuzz

# Minimum similarity score (0–100) to consider two strings a match
MATCH_THRESHOLD = 88

# Patterns for stripping common label suffixes from artist fields
_LABEL_BRACKET_RE = re.compile(r"\s*\[.*?\]\s*$")
_PARENS_FEAT_RE = re.compile(r"\s*\(feat\.?.*?\)\s*$", re.IGNORECASE)
_PARENS_FT_RE = re.compile(r"\s*\bft\.?\s+.*$", re.IGNORECASE)
_FEAT_RE = re.compile(r"\s*feat\.?\s+.*$", re.IGNORECASE)


def normalise_text(text: str) -> str:
    """Produce a canonical form of a text string for matching.

    Steps:
      1. Unicode normalise (NFKD → ASCII where possible)
      2. Lowercase
      3. Strip leading/trailing whitespace
      4. Collapse internal whitespace
      5. Remove punctuation except hyphens and apostrophes
    """
    normalised = unicodedata.normalize("NFKD", text)
    ascii_text = normalised.encode("ascii", "ignore").decode("ascii")
    lower = ascii_text.lower().strip()
    collapsed = re.sub(r"\s+", " ", lower)
    stripped = re.sub(r"[^\w\s\-']", "", collapsed)
    return stripped.strip()


def strip_label_from_artist(artist: str) -> str:
    """Remove label annotations appended to an artist field.

    Handles:
      'Tame Impala [Island Records]' → 'Tame Impala'
      'Drake (feat. Rihanna)'        → 'Drake'
      'The Weeknd ft. Daft Punk'     → 'The Weeknd'
    """
    result = _LABEL_BRACKET_RE.sub("", artist)
    result = _PARENS_FEAT_RE.sub("", result)
    result = _PARENS_FT_RE.sub("", result)
    result = _FEAT_RE.sub("", result)
    return result.strip()


def fuzzy_match(a: str, b: str) -> float:
    """Return token sort ratio similarity (0–100) between two normalised strings."""
    return fuzz.token_sort_ratio(a, b)


def is_match(a: str, b: str, threshold: float = MATCH_THRESHOLD) -> bool:
    """Return True if two normalised strings are similar enough to be considered the same."""
    return fuzzy_match(a, b) >= threshold


def compute_fingerprint(artist: str, title: str) -> str:
    """SHA-256 fingerprint of (normalised_artist, normalised_title) for deduplication.

    Used when source_event_id is not available (e.g. manual CSV imports).
    """
    key = f"{normalise_text(artist)}|{normalise_text(title)}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()
