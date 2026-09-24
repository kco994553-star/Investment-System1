"""Point-in-Time resolver. NEW IMPLEMENTATION.

Look-ahead is rejected when available_at > as_of.
"""

from __future__ import annotations

from datetime import datetime
from typing import Iterable, Optional, TypeVar

from ..contracts.enums import QualityState
from ..contracts.models import DataStamp

T = TypeVar("T")


class PITViolation(ValueError):
    pass


def is_available(stamp: DataStamp, as_of: datetime) -> bool:
    return stamp.available_at <= as_of and stamp.published_at <= as_of


def require_available(stamp: DataStamp, as_of: datetime) -> DataStamp:
    if not is_available(stamp, as_of):
        raise PITViolation(
            f"PIT_UNAVAILABLE: stamp {stamp.data_stamp_id} available_at="
            f"{stamp.available_at.isoformat()} as_of={as_of.isoformat()}"
        )
    return stamp


def select_latest(stamps: Iterable[DataStamp], as_of: datetime) -> Optional[DataStamp]:
    eligible = [s for s in stamps if is_available(s, as_of)]
    if not eligible:
        return None
    return max(eligible, key=lambda s: (s.available_at, s.published_at, s.observed_at))


def pit_state(stamp: Optional[DataStamp], as_of: datetime) -> QualityState:
    if stamp is None:
        return QualityState.MISSING_DATA
    if not is_available(stamp, as_of):
        return QualityState.PIT_UNAVAILABLE
    if stamp.synthetic:
        return QualityState.SYNTHETIC
    if stamp.estimated:
        return QualityState.ESTIMATED_DATA
    return QualityState.OK
