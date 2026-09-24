"""Combination / ablation comparison. NEW IMPLEMENTATION. Not official PASS."""

from __future__ import annotations

from datetime import datetime

from .backtest import COMBINATION_SETS, BacktestSpec
from .engine import RunPurpose, pit_roll_wealth
from ..contracts.enums import ValidationLayer
from ..contracts.models import DataStamp


def pit_ablation_dataset(predict_row: dict, outcome_row: dict) -> dict:
    """Build 7-arm PIT dataset. Does not mutate parent predictions. Not Full PIT."""
    q0 = predict_row.get("quality") or {}
    q1 = outcome_row.get("quality") or {}
    names = [cid for cid in q0 if cid in q1 and q0[cid].get("pit_price") and q1[cid].get("pit_price")]
    rets = {}
    for cid in names:
        p0 = q0[cid]["pit_price"]
        p1 = q1[cid]["pit_price"]
        if p0:
            rets[cid] = p1 / p0 - 1.0

    def pick(arm: str) -> list[str]:
        if arm == "qgv":
            hit = [c for c in names if q0[c].get("Q") is not None and q0[c].get("G") is not None]
        elif arm == "technical":
            hit = [c for c in names if q0[c].get("technical_regime") == "TREND_UP"]
        elif arm == "macro":
            hit = list(names) if predict_row.get("macro_regime") not in {"UNAVAILABLE", "INFLATION_SHOCK"} else []
        elif arm == "qgv+technical":
            hit = [c for c in pick("qgv") if c in pick("technical")]
        elif arm == "qgv+macro":
            hit = pick("qgv") if pick("macro") else []
        elif arm == "technical+macro":
            hit = pick("technical") if pick("macro") else []
        else:
            qg = set(pick("qgv"))
            ta = set(pick("technical"))
            hit = [c for c in names if c in qg and c in ta] if pick("macro") else []
        return hit or list(names)

    arms = (
        "qgv",
        "technical",
        "macro",
        "qgv+technical",
        "qgv+macro",
        "technical+macro",
        "qgv+technical+macro",
    )
    rows = {}
    for arm in arms:
        held = pick(arm)
        arm_ret = sum(rets[c] for c in held) / len(held) if held else 0.0
        rows[arm] = {
            "held": held,
            "n": len(held),
            "period_return": arm_ret,
            "snapshot_ids": (predict_row.get("snapshot_ids") or {}),
            "mutates_inputs": False,
            "official_pass": False,
        }
    return {
        "kind": "ABLATION_PIT_DATASET",
        "official_pass": False,
        "real_data_verified": False,
        "full_pit_pass": False,
        "predict_as_of": predict_row.get("as_of"),
        "outcome_as_of": outcome_row.get("as_of"),
        "n_names": len(names),
        "rows": rows,
        "provenance": {
            "price": "yahoo_adjclose_pit",
            "qgv": "qgv_snapshot_id",
            "technical": "technical_snapshot_id",
            "macro": "macro_snapshot_id",
        },
    }


def run_ablation(
    stamps: list[DataStamp],
    as_of: datetime,
    module_returns: dict[str, dict[str, float]],
    initial: float = 100.0,
) -> dict:
    """module_returns maps module name -> stamp_id -> period return."""
    rows = {}
    for combo in COMBINATION_SETS:
        period = {}
        for sid in [s.data_stamp_id for s in stamps]:
            vals = [module_returns.get(mod, {}).get(sid, 0.0) for mod in combo]
            period[sid] = sum(vals) / len(vals)
        spec = BacktestSpec(
            spec_id="ablation-" + "+".join(combo),
            layer=ValidationLayer.COMBINATION_BACKTEST if len(combo) > 1 else ValidationLayer.MODULE_BACKTEST,
            modules=combo,
            start=as_of,
            end=as_of,
            as_of=as_of,
        )
        wealth, used = pit_roll_wealth(stamps, as_of, period, initial)
        rows["+".join(combo)] = {
            "spec_id": spec.spec_id,
            "ending_value": wealth,
            "used": list(used),
            "purpose": RunPurpose.VALIDATION_BACKTEST.value,
            "official_pass": False,
            "synthetic": True,
        }
    q_only = rows["qgv"]["ending_value"]
    incremental = {key: rows[key]["ending_value"] - q_only for key in rows if key != "qgv"}
    return {
        "kind": "ABLATION_SYNTHETIC",
        "official_pass": False,
        "real_data_verified": False,
        "rows": rows,
        "incremental_vs_qgv": incremental,
    }
