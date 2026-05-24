"""Report confidence scoring.

Confidence is a float 0.0–1.0 computed from:
  - Source coverage (which sources contributed to the report)
  - Proportion of plays that are manual imports (penalised)
  - Whether the primary automated source was available

Confidence levels:
  High:   >= 0.85
  Medium: >= 0.65
  Low:    < 0.65

A Low-confidence report must be labelled as such in the UI and export.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ConfidenceLevel(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# Confidence level thresholds
_HIGH_THRESHOLD = 0.85
_MEDIUM_THRESHOLD = 0.65

# Per-source weight contributions (must sum to <= 1.0 for a fully covered report)
_SOURCE_WEIGHTS = {
    "radiowave": 0.50,
    "iheart": 0.50,
    "manual_csv": 0.20,
}

# Maximum score reduction when 100% of plays are manual imports
# 0.40 → all-manual = 0.60 (Low), 50% manual = 0.80 (Medium/High boundary)
_MANUAL_IMPORT_PENALTY_PER_FRACTION = 0.40


@dataclass
class SourceCoverage:
    radiowave_plays: int = 0
    iheart_plays: int = 0
    manual_csv_plays: int = 0
    total_plays: int = 0

    @property
    def manual_fraction(self) -> float:
        if self.total_plays == 0:
            return 0.0
        return self.manual_csv_plays / self.total_plays

    @property
    def automated_fraction(self) -> float:
        return 1.0 - self.manual_fraction

    def to_dict(self) -> dict:
        return {
            "radiowave_plays": self.radiowave_plays,
            "iheart_plays": self.iheart_plays,
            "manual_csv_plays": self.manual_csv_plays,
            "total_plays": self.total_plays,
        }


def compute_confidence(
    coverage: SourceCoverage,
    primary_source_available: bool = True,
) -> tuple[float, ConfidenceLevel]:
    """Compute a confidence score and level for a daily report.

    Args:
        coverage: Source coverage breakdown for this report
        primary_source_available: Was the primary automated source reachable?

    Returns:
        (score, level) where score is 0.0–1.0
    """
    if coverage.total_plays == 0:
        return 0.0, ConfidenceLevel.LOW

    score = 1.0

    # Penalty for manual imports
    score -= coverage.manual_fraction * _MANUAL_IMPORT_PENALTY_PER_FRACTION

    # Penalty if primary automated source was unavailable
    if not primary_source_available:
        score -= 0.20

    # Clamp to [0, 1]
    score = max(0.0, min(1.0, score))

    if score >= _HIGH_THRESHOLD:
        level = ConfidenceLevel.HIGH
    elif score >= _MEDIUM_THRESHOLD:
        level = ConfidenceLevel.MEDIUM
    else:
        level = ConfidenceLevel.LOW

    return round(score, 4), level
