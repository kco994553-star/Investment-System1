"""PIT / time contract (PIL §17). Locked invariant: available_at <= decision_time. No time is ever generated here."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


class TimeContractError(ValueError):
    """A timestamp is missing, naive, or would allow look-ahead."""


def _aware(name: str, t: Optional[datetime]) -> None:
    if t is not None and (t.tzinfo is None or t.utcoffset() is None):
        raise TimeContractError(f"{name} must be timezone-aware")


@dataclass(frozen=True)
class TimeStamps:
    """observed_at: when the fact refers to; available_at: when it became knowable; decision_time: when it is used;
    calculated_at: when a result was computed. as_of is NOT assumed equal to available_at."""

    observed_at: Optional[datetime]
    available_at: Optional[datetime]
    decision_time: datetime
    calculated_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        for n in ("observed_at", "available_at", "decision_time", "calculated_at"):
            _aware(n, getattr(self, n))
        if self.available_at is None:
            raise TimeContractError("available_at is required (PIL does not create times; see C-28 for Technical)")
        if self.available_at > self.decision_time:
            raise TimeContractError("available_at > decision_time (look-ahead)")
        if self.observed_at is not None and self.observed_at > self.available_at:
            raise TimeContractError("observed_at > available_at")


def usable_at(available_at: Optional[datetime], decision_time: datetime) -> bool:
    """True only when a value is known (available_at present) no later than decision_time. Missing -> False."""
    _aware("available_at", available_at)
    _aware("decision_time", decision_time)
    return available_at is not None and available_at <= decision_time
