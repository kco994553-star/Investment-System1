"""v1.2 PROVISIONAL policy as experiment config. Not official constants."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProvisionalPolicy:
    status: str = "PROVISIONAL"
    deadband_pp: float = 0.50
    staged_entry: tuple[float, ...] = (0.50, 0.75, 1.00)
    om_default: float = 1.0
    tm_default: float = 1.0
    mm_default: float = 1.0
    rm_default: float = 1.0


DEFAULT_PROVISIONAL_POLICY = ProvisionalPolicy()
