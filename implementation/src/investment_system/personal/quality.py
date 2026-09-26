"""Data quality / freshness (PIL §18). Quality and confidence are separate; a critical component that is stale or
unresolved lowers the dependent result."""
from __future__ import annotations

from enum import Enum


class DataQuality(str, Enum):
    VALID = "VALID"
    PARTIAL = "PARTIAL"
    STALE = "STALE"
    UNRESOLVED = "UNRESOLVED"
    INVALID = "INVALID"


_SEVERITY = {DataQuality.VALID: 0, DataQuality.PARTIAL: 1, DataQuality.STALE: 2, DataQuality.UNRESOLVED: 3, DataQuality.INVALID: 4}


def worst(*qualities: DataQuality) -> DataQuality:
    """Combined quality of components = the worst one. No components -> UNRESOLVED (missing is not VALID)."""
    if not qualities:
        return DataQuality.UNRESOLVED
    return max(qualities, key=lambda q: _SEVERITY[DataQuality(q)])


def is_actionable(q: DataQuality) -> bool:
    """Only VALID and PARTIAL results may be shown without a restriction state."""
    return DataQuality(q) in (DataQuality.VALID, DataQuality.PARTIAL)
