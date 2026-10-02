from datetime import datetime, timedelta

import pytest

from investment_system.evl import (
    DatasetSplit, ExperimentSpec, FreezeManifest, HoldoutState, MetricSet,
    ParameterSpace, PITGuard, PITViolation, SearchBudget, TAX_MODE,
    TrialLedger, TrialRecord, TrialStatus,
)
from investment_system.evl.pit import PITObservation

def _dt(day):
    return datetime(2020, 1, 1) + timedelta(days=day)

def test_c0_experiment_preregistration_and_pretax_lock():
    split = DatasetSplit(_dt(0), _dt(10), _dt(11), _dt(12), _dt(13), _dt(14))
    spec = ExperimentSpec(
        "exp-1", _dt(0), _dt(10), "dataset", "vintage", "datahash", "codehash", 7,
        ParameterSpace({"qgv_weight": [0.4, 0.5]}, 3, 2),
        SearchBudget(10), split, MetricSet(("cagr", "sharpe")),
    )
    assert spec.tax_mode == TAX_MODE
    with pytest.raises(ValueError):
        ExperimentSpec(
            "exp-2", _dt(0), _dt(10), "dataset", "vintage", "datahash", "codehash", 7,
            ParameterSpace({"x": [1]}, 1, 1), SearchBudget(1), split, MetricSet(("cagr",)),
            tax_mode="INCLUDED",
        )

def test_c0_trial_ledger_logs_all_terminal_statuses_append_only(tmp_path):
    ledger = TrialLedger(tmp_path / "trials.jsonl")
    statuses = [
        TrialStatus.SUCCESS, TrialStatus.REJECTED, TrialStatus.EARLY_STOPPED,
        TrialStatus.FAILED, TrialStatus.INVALIDATED,
    ]
    for i, status in enumerate(statuses):
        ledger.append(TrialRecord(
            f"t{i}", "exp", i, _dt(i), status, {"x": i},
            {"score": float(i)} if status == TrialStatus.SUCCESS else {},
            None if status == TrialStatus.SUCCESS else "recorded reason",
        ))
    assert len(ledger.records()) == 5
    assert ledger.verify()
    with pytest.raises(ValueError):
        ledger.append(TrialRecord("t0", "exp", 5, _dt(6), TrialStatus.SUCCESS, {}))

def test_c0_pit_guard_blocks_lookahead_and_missing_provenance():
    ok = PITObservation("a", _dt(1), "sec", "v1")
    assert PITGuard.enforce(_dt(2), [ok]) == (ok,)
    with pytest.raises(PITViolation):
        PITGuard.enforce(_dt(2), [PITObservation("future", _dt(3), "sec", "v1")])
    with pytest.raises(PITViolation):
        PITGuard.enforce(_dt(2), [PITObservation("unknown", _dt(1), "", "v1")])

def test_c0_freeze_manifest_binds_spec_lineage_and_pretax():
    m = FreezeManifest(
        "artifact", "Balanced", "exp", "candidate", "EVL_SPEC_v0.1",
        "code", "data", "vintage", {"w": .5}, {"gate": 1},
        HoldoutState.UNCONSUMED, "FROZEN", ("dataset", "experiment", "walkforward", "robustness"),
    )
    assert m.tax_mode == "EXCLUDED"
    with pytest.raises(ValueError):
        FreezeManifest(
            "artifact", "Balanced", "exp", "candidate", "OTHER",
            "code", "data", "vintage", {}, {}, HoldoutState.UNCONSUMED, "FROZEN", ("x",),
        )
