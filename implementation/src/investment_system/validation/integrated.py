"""Integrated pipeline backtest skeleton. Does not emit module-level orders."""

from __future__ import annotations

from datetime import datetime

from ..integration.engine import IntegrationEngine
from ..qgv.portfolio import PortfolioEngine
from .adapters import MacroAdapter, TechnicalAdapter
from .engine import RunPurpose


def run_integrated_session(as_of: datetime, portfolio, tech_by_id: dict, macro_indicators: dict, profile=None) -> dict:
    tech = {cid: snap for cid, snap in tech_by_id.items()}
    mac = MacroAdapter().snapshot(as_of, macro_indicators)
    integ = IntegrationEngine().run(
        as_of,
        portfolio,
        tech,
        mac,
        profile_id=None if profile is None else profile.profile_id,
        parameter_set_hash=None if profile is None else profile.parameter_set_hash(),
    )
    return {
        "purpose": RunPurpose.VALIDATION_BACKTEST.value,
        "layer": "integrated_backtest",
        "gate": integ.gate.value,
        "policy_status": integ.policy_status,
        "orders_from_modules": False,
        "decision_source": "integration",
        "official_pass": False,
        "real_data_verified": False,
        "synthetic": True,
        "profile_id": integ.profile_id,
        "parameter_set_hash": integ.parameter_set_hash,
    }
