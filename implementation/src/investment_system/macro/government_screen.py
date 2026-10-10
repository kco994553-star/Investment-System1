"""Government raw-evidence presentation; no adopted provider-to-regime mapping.

Returns fresh JSON-safe containers in memory. Nothing writes them or connects
them to a public producer, app, QGV, Model, or historical validation.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from math import isfinite

from .engine import MacroEngine
from .primary_contract import AXES, DIMENSIONS, SOURCE_REGISTRY, aware, utc
from .primary_input import build_evidence_grid
from ..versions import MACRO_CONFIRMED


def _unavailable_regime(reason: str) -> dict:
    return {"state": "NOT_AVAILABLE", "macro_state": None, "regime": None,
            "macro_version": MACRO_CONFIRMED, "model_status": "NOT_APPLIED",
            "reason_codes": [reason]}


def evaluate_synthetic_macro_inputs(indicators: object, as_of: datetime) -> dict:
    """Check the unchanged engine using explicitly synthetic normalized inputs.

    This is deliberately separate from government observations: neither GDP
    levels nor CPI indexes have an approved normalization in the source spec.
    Missing keys must never reach the engine's implicit zero defaults.
    """
    if not aware(as_of):
        return _unavailable_regime("INVALID_TIMESTAMP")
    if not isinstance(indicators, Mapping) or set(indicators) != {"growth", "inflation"}:
        return _unavailable_regime("INVALID_ENGINE_INPUT")
    copied = {}
    for name in ("growth", "inflation"):
        value = indicators[name]
        if type(value) not in (int, float):
            return _unavailable_regime("INVALID_ENGINE_INPUT")
        try:
            if not isfinite(value):
                return _unavailable_regime("INVALID_ENGINE_INPUT")
        except (OverflowError, ValueError):
            return _unavailable_regime("INVALID_ENGINE_INPUT")
        copied[name] = value
    snapshot = MacroEngine().evaluate(utc(as_of), copied, synthetic=True)
    return {"state": "SYNTHETIC_CHECK", "macro_state": snapshot.state.value,
            "regime": snapshot.regime, "macro_version": snapshot.macro_version,
            "synthetic": True, "model_status": "NOT_APPLIED", "reason_codes": []}


def build_government_macro_screen(primary_results: tuple, as_of: datetime,
                                  remaining_results: tuple = ()) -> dict:
    """Present eligible captures in an unscored 8x6 grid, as exact decimal text.

    Source notes, provider request parameters, arbitrary URLs and credentials
    are excluded. FX statistical observations remain RAM-only in this module.
    Raw evidence is never a state score or a confirmed historical PIT vintage.
    """
    valid_time = aware(as_of)
    grid = build_evidence_grid(primary_results, as_of)
    observations = []
    for obs in grid.observations:
        observations.append({
            "observation_id": obs.observation_id, "source_id": obs.source_id,
            "axis": obs.axis, "provider": SOURCE_REGISTRY[obs.source_id].provider,
            "observation_period": obs.observation_period, "value": str(obs.value),
            "unit": obs.unit, "unit_multiplier": obs.unit_multiplier, "frequency": obs.frequency,
            "seasonal_adjustment": obs.seasonal_adjustment,
            "available_at": utc(obs.available_at).isoformat(),
            "vintage_at": utc(obs.vintage_at).isoformat(),
            "ingested_at": utc(obs.ingested_at).isoformat(),
            "availability_basis": obs.availability_basis,
            "source_response_sha256": obs.source_response_sha256,
            "synthetic": obs.synthetic,
        })
    cells = [{"axis": c.axis, "dimension": c.dimension, "state": c.state,
              "evidence_ids": list(c.evidence_ids), "value": None,
              "reason_codes": list(c.reason_codes)} for c in grid.cells]
    reasons = list(grid.reason_codes)
    if remaining_results != ():
        from ..providers.macro_remaining import select_remaining_observed
        selected = select_remaining_observed(remaining_results, as_of)
        primary_flags = {o["synthetic"] for o in observations}
        if ("MIXED_SYNTHETIC_INPUT" in reasons
                or "MIXED_SYNTHETIC_INPUT" in selected.reason_codes
                or (selected.observations and primary_flags and selected.synthetic not in primary_flags)):
            reasons.append("MIXED_SYNTHETIC_INPUT")
            # A mixed package is not an eligible combined presentation.
            observations = []
            for cell in cells:
                cell.update(state="NOT_AVAILABLE", evidence_ids=[], value=None,
                            reason_codes=["MIXED_SYNTHETIC_INPUT"])
        else:
            reasons.extend(selected.reason_codes)
            for obs in selected.observations:
                observations.append({
                    "observation_id": obs.observation_id, "source_id": obs.source_id,
                    "axis": obs.axis, "provider": obs.provider,
                    "observation_period": obs.observation_period, "value": str(obs.value),
                    "unit": obs.unit, "frequency": obs.frequency,
                    "source_frequency": obs.source_frequency,
                    "unit_multiplier": str(obs.unit_multiplier) if obs.unit_multiplier is not None else None,
                    "seasonal_adjustment": obs.seasonal_adjustment, "basis": obs.basis,
                    "available_at": utc(obs.available_at).isoformat(),
                    "vintage_at": utc(obs.vintage_at).isoformat(),
                    "ingested_at": utc(obs.ingested_at).isoformat(),
                    "availability_basis": "OBSERVED_CAPTURE_UPPER_BOUND",
                    "source_response_sha256": obs.source_response_sha256,
                    "synthetic": obs.synthetic,
                })
            for cell in cells:
                if cell["axis"] in ("Liquidity", "Credit", "Fiscal", "FX"):
                    ids = [o.observation_id for o in selected.observations if o.axis == cell["axis"]]
                    if cell["dimension"] == "Level" and ids:
                        cell.update(state="RAW_EVIDENCE", evidence_ids=ids, reason_codes=[])
                    else:
                        cell["reason_codes"] = ["UNADOPTED_INPUT_SELECTION"] if not ids else ["NO_APPROVED_STATE_RULE"]
    # The 4 raw source levels do not define the engine's fractional inputs.
    return {"contract": "GOVERNMENT_MACRO_SCREEN/1", "role": "RESEARCH_EVIDENCE_ONLY",
            "as_of": utc(as_of).isoformat() if valid_time else None,
            "axes": list(AXES), "dimensions": list(DIMENSIONS),
            "state": "RAW_EVIDENCE" if observations else "NOT_AVAILABLE",
            "cells": cells, "observations": observations,
            "pit_status": "OBSERVED_BOUND_ONLY" if observations else "NOT_VERIFIED",
            "model_status": "NOT_APPLIED", "public_route_connected": False,
            "regime": _unavailable_regime("UNAPPROVED_ENGINE_INPUT_MAPPING"),
            "reason_codes": list(dict.fromkeys(reasons))}
