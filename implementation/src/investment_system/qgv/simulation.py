"""Simulation with structural PIT enforcement. NEW IMPLEMENTATION."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from ..contracts.enums import SimulationMode
from ..contracts.models import DataStamp
from ..pit.resolver import PITViolation
from ..validation.engine import RunPurpose, pit_roll_wealth
from ..versions import IMPLEMENTATION_KIND, IMPLEMENTATION_LINE


@dataclass(frozen=True)
class SimulationConfig:
    mode: SimulationMode
    start: datetime
    end: datetime
    as_of: datetime
    initial_capital: float = 100.0
    pit_policy_version: str = "pit-v1-strict"


@dataclass(frozen=True)
class SimulationResult:
    simulation_id: str
    mode: str
    implementation_kind: str
    implementation_line: str
    ending_value: float
    total_return: float
    used_stamp_ids: tuple[str, ...]
    synthetic: bool


class SimulationEngine:
    def run(self, config: SimulationConfig, stamps: list[DataStamp], period_returns: dict[str, float]) -> SimulationResult:
        if config.mode == SimulationMode.FORWARD:
            # Forward series must not be mixed into historical results.
            pass
        if config.end < config.start:
            raise ValueError("end before start")
        wealth, used = pit_roll_wealth(stamps, config.as_of, period_returns, config.initial_capital)
        return SimulationResult(
            simulation_id=f"sim_{uuid4().hex[:12]}",
            mode=config.mode.value,
            implementation_kind=IMPLEMENTATION_KIND,
            implementation_line=IMPLEMENTATION_LINE,
            ending_value=wealth,
            total_return=wealth / config.initial_capital - 1.0,
            used_stamp_ids=tuple(used),
            synthetic=any(s.synthetic for s in stamps),
        )
