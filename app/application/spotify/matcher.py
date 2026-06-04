from __future__ import annotations

import difflib
import logging
from typing import Any

from app.core.settings import settings

logger = logging.getLogger(__name__)


class SpotifyMatcher:
    """Matcher service to calculate track similarity and select best match."""

    @staticmethod
    def normalize_text(text: str) -> str:
        if not text:
            return ""
        import re
        t = text.lower()
        # Split on common featuring / collaborator boundaries
        t = re.split(r"\b(feat\.?|featuring|with|pres\.?|vs\.?)\b", t)[0]
        # Remove parenthetical info about features/producers/vocals
        t = re.sub(
            r"\([^\)]*(?:feat\.?|featuring|with|prod\.?|produced|vocals|mix)\b[^\)]*\)",
            "",
            t,
        )
        # Convert non-alphanumeric to spaces
        t = re.sub(r"[^a-z0-9\s]", " ", t)
        return " ".join(t.split())

    def calculate_similarity(
        self, db_title: str, db_artist: str, sp_title: str, sp_artists: list[str]
    ) -> float:
        """Calculate weighted similarity score between DB record and Spotify track."""
        norm_db_title = self.normalize_text(db_title)
        norm_db_artist = self.normalize_text(db_artist)
        norm_sp_title = self.normalize_text(sp_title)

        # Title similarity
        title_sim = difflib.SequenceMatcher(None, norm_db_title, norm_sp_title).ratio()

        # Artist similarity: take the best match among all track artists
        best_artist_sim = 0.0
        for sp_art in sp_artists:
            norm_sp_art = self.normalize_text(sp_art)
            sim = difflib.SequenceMatcher(None, norm_db_artist, norm_sp_art).ratio()
            if sim > best_artist_sim:
                best_artist_sim = sim

        # Also check against combined artist string
        combined_sp_artists = " ".join([self.normalize_text(a) for a in sp_artists])
        comb_sim = difflib.SequenceMatcher(
            None, norm_db_artist, combined_sp_artists
        ).ratio()
        best_artist_sim = max(best_artist_sim, comb_sim)

        # Weighted calculation: 55% Title, 45% Artist
        confidence = (title_sim * 0.55) + (best_artist_sim * 0.45)
        return confidence

    def find_best_match(
        self, db_title: str, db_artist: str, spotify_tracks: list[dict[str, Any]]
    ) -> tuple[dict[str, Any] | None, float]:
        """Find the best track match that meets confidence thresholds."""
        best_track = None
        best_confidence = 0.0

        for track in spotify_tracks:
            sp_title = track.get("name", "")
            sp_artists = [a.get("name", "") for a in track.get("artists", [])]

            confidence = self.calculate_similarity(
                db_title, db_artist, sp_title, sp_artists
            )
            if confidence > best_confidence:
                best_confidence = confidence
                best_track = track

        threshold = settings.spotify_match_confidence_threshold
        if best_track and best_confidence >= threshold:
            return best_track, best_confidence

        return None, best_confidence
