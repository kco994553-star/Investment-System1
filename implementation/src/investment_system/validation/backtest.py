"""Backtest contracts. Distinct from Track Record. NEW IMPLEMENTATION."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ..contracts.enums import SimulationMode, ValidationLayer
from .engine import RunPurpose, pit_roll_wealth


COMBINATION_SETS = (
    ("qgv",),
    ("technical",),
    ("macro",),
    ("qgv", "technical"),
    ("qgv", "macro"),
    ("technical", "macro"),
    ("qgv", "technical", "macro"),
)


@dataclass(frozen=True)
class BacktestSpec:
    spec_id: str
    layer: ValidationLayer
    modules: tuple[str, ...]
    start: datetime
    end: datetime
    as_of: datetime
    synthetic: bool = True
    notes: str = "PROVISIONAL harness. Not official validation PASS."


def incremental_sets() -> tuple[tuple[str, ...], ...]:
    return COMBINATION_SETS


def run_toy_module_backtest(spec: BacktestSpec, stamps: list, period_returns: dict[str, float], initial: float = 100.0) -> dict:
    """PIT-safe toy path. Does not claim official backtest PASS."""
    if spec.end < spec.start:
        raise ValueError("end before start")
    wealth, used = pit_roll_wealth(stamps, spec.as_of, period_returns, initial)
    return {
        "spec_id": spec.spec_id,
        "layer": spec.layer.value,
        "modules": list(spec.modules),
        "ending_value": wealth,
        "used": list(used),
        "mode": SimulationMode.HISTORICAL.value,
        "purpose": RunPurpose.VALIDATION_BACKTEST.value,
        "not_product_simulation": True,
        "synthetic": spec.synthetic,
        "official_pass": False,
    }
