"""Shared PIT wealth engine. Product simulation and validation backtest both call this.

Purpose is labeled separately. Sharing code does not merge product and validation.
"""

from __future__ import annotations

from enum import Enum

from ..contracts.models import DataStamp
from ..pit.resolver import PITViolation, require_available


class RunPurpose(str, Enum):
    PRODUCT_SIMULATION = "PRODUCT_SIMULATION"
    VALIDATION_BACKTEST = "VALIDATION_BACKTEST"


def pit_roll_wealth(
    stamps: list[DataStamp],
    as_of,
    period_returns: dict[str, float],
    initial: float = 100.0,
) -> tuple[float, tuple[str, ...]]:
    used = []
    wealth = initial
    for stamp in stamps:
        require_available(stamp, as_of)
        used.append(stamp.data_stamp_id)
        wealth *= 1.0 + period_returns.get(stamp.data_stamp_id, 0.0)
    for stamp in stamps:
        if stamp.available_at > as_of:
            raise PITViolation("lookahead leaked")
    return wealth, tuple(used)
