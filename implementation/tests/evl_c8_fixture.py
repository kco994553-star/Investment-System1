"""Explicit simulated C8 foundation fixture; never actual research/Forward evidence."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from dataclasses import replace
from unittest.mock import patch
from tests import evl_c6_fixture as c6_fixture
import shutil

from investment_system.evl.calibration_contracts import (APPROVAL_BLOB, POLICY, METHOD, SCOPE,
    FIXTURE_SCOPE, CONTROLS, ECONOMIC_ORDER, code_hash, metric_identity)
from investment_system.evl.calibration_ledger import AccessRegistry, CalibrationLedger
from investment_system.evl.calibration_protocol import (describe_upstream, register_calibration,
    read_partition, record_fixture_threshold_choice)
from investment_system.evl.calibration_evidence import (record_control_evidence,
    record_economic_evidence, software_artifact, resolve_software_artifact)
from investment_system.evl.experiments import ExperimentLedger
from investment_system.evl.metrics import ReturnPeriod, evaluate_metrics
from investment_system.evl.pit import PITObservation
from investment_system.evl.profile_selection import register_selection, run_selection
from investment_system.evl.walkforward import digest
from tests.evl_c7_fixture import prepare, T

REGISTERED_AT = datetime(2026, 10, 3, tzinfo=timezone.utc)
FIT_AT = datetime(2030, 2, 1, tzinfo=timezone.utc)
VERIFY_AT = datetime(2030, 4, 1, tzinfo=timezone.utc)


def prepare_source(path):
    # Configure only this new synthetic source chain, before source registration.
    # Preserve the frozen fixture helpers/files and actual Holdout allocation.
    original_contract = c6_fixture.contract
    with patch.object(c6_fixture, "contract", lambda: replace(original_contract(),
                      holdout_start=datetime(2031, 1, 1, tzinfo=timezone.utc))):
        ledger, cohorts, plan = prepare(path)
    register_selection(ledger, cohorts, plan)
    assert run_selection(ledger, cohorts, recorded_at=T)["status"] == "PASS"
    return ledger, cohorts


def clone_source(root, source, path):
    shutil.copytree(root, path)
    selection, cohorts = source

    def clone(original):
        return ExperimentLedger(path / original.directory.relative_to(root))
    copied = {}
    for key, (diagnostic, split, experiment, bundles, drift) in cohorts.items():
        copied_bundles = {
            i: {**deepcopy({k: v for k, v in bundle.items() if k != "c4_ledger"}),
                "c4_ledger": clone(bundle["c4_ledger"])}
            for i, bundle in bundles.items()}
        copied[key] = (clone(diagnostic), split, clone(experiment), copied_bundles, deepcopy(drift))
    return clone(selection), copied


class SyntheticProvider:
    scope = SCOPE
    synthetic = True

    def __init__(self, metadata, bodies):
        self.metadata = deepcopy(metadata)
        self.bodies = deepcopy(bodies)
        self.reads = []
        self.before_read = None
        self.fail = None

    def describe(self, role):
        return deepcopy(self.metadata[role])

    def read(self, role):
        if self.before_read:
            self.before_read(role)
        self.reads.append(role)
        if self.fail:
            raise self.fail
        return deepcopy(self.bodies[role])


def _partition(role, current):
    month = 1 if role == "CAL_FIT" else 3
    evaluation = datetime(2030, month, 31, tzinfo=timezone.utc)
    source_id, vintage = "SYNTHETIC_C8_LABELS", "C8_FIXTURE_V1"
    samples = []
    for start_day, end_day in ((5, 10), (10, 15)):
        start = datetime(2030, month, start_day, tzinfo=timezone.utc)
        end = datetime(2030, month, end_day, tzinfo=timezone.utc)
        samples.append({"sample_id": role + "-sample-" + str(start_day),
                        "decision_time": start.isoformat(), "label_end": end.isoformat(),
                        "label_available_at": (end + timedelta(days=1)).isoformat(),
                        "observations": [{"observation_id": "known-feature-" + role + str(start_day),
                                          "available_at": start.isoformat(),
                                          "source_id": "SYNTHETIC_C8_FEATURES", "vintage": vintage}]})

    def metrics(returns):
        periods = []
        for sample, ret in zip(samples, returns):
            start = datetime.fromisoformat(sample["decision_time"])
            end = datetime.fromisoformat(sample["label_end"])
            available = datetime.fromisoformat(sample["label_available_at"])
            periods.append(ReturnPeriod(
                start, end, ret, .0001, .0002, .0003, .001, .1, "USD",
                PITObservation("rf-" + sample["sample_id"], start, "SYNTHETIC_RF", vintage),
                PITObservation("out-" + sample["sample_id"], available, source_id, vintage),
                PITObservation("cpi-" + sample["sample_id"], available, "SYNTHETIC_CPI", vintage)))
        # All values here, including calendar and risk/tail choices, are fixture-only.
        return evaluate_metrics(tuple(periods), evaluation_time=evaluation,
                                periods_per_year=73, tail_fraction=.5)

    meta = {"dataset_id": "SYNTHETIC-" + role, "role": role, "scope": SCOPE, "synthetic": True,
            "source_role": "OUTER_C8_CALIBRATION", "source_id": source_id, "vintage": vintage,
            "lineage_ids": ["SYNTHETIC-C8-" + role, "SYNTHETIC-C8-BENCHMARK-" + role],
            "available_at": evaluation.isoformat(),
            "window": {"start": datetime(2030, month, 1, tzinfo=timezone.utc).isoformat(),
                       "end": datetime(2030, month + 1, 1, tzinfo=timezone.utc).isoformat()},
            "samples": samples}
    meta["manifest_hash"] = digest(meta)
    body = {"dataset_id": meta["dataset_id"], "scope": SCOPE, "synthetic": True,
            "temporal_origin": "SIMULATED", "tax_mode": "EXCLUDED",
            "source_id": source_id, "vintage": vintage, "lineage_ids": meta["lineage_ids"],
            "manifest_hash": meta["manifest_hash"], "samples": samples, "cohorts": {}}
    for cohort in current["cohort_metadata"]:
        body["cohorts"][cohort] = {}
        for index, candidate in enumerate(current["family_members"]):
            body["cohorts"][cohort][candidate] = {
                "frozen_instance": deepcopy(current["model_instances"][cohort][candidate]),
                "metric_report": metrics((.004 + index * .001, -.001 + index * .0001)),
                "controls": {control: metrics((.001, -.002)) for control in CONTROLS}}
    meta["content_hash"] = digest(body)
    return meta, body


def plan_and_provider(source):
    current = describe_upstream(*source)
    datasets, bodies = {}, {}
    for role in ("CAL_FIT", "CAL_VERIFY"):
        datasets[role], bodies[role] = _partition(role, current)
    net = metric_identity("net_cagr", "NET_OF_TRADING_COST_PRE_TAX", "cagr", "max")
    real = metric_identity("real_cagr", "REAL_PRE_TAX", "cagr", "max")
    rf = metric_identity("rf_cagr", "RISK_FREE_EXCESS_PRE_TAX", "cagr", "max")
    opportunity = metric_identity("opportunity", None, "net_minus_benchmark_total_return", "max")
    risk = metric_identity("risk_adjusted", "NET_OF_TRADING_COST_PRE_TAX", "sharpe", "max")
    identities = (net, real, rf, None, opportunity, risk)
    plan = {"schema": METHOD, "policy": POLICY, "approval_blob": APPROVAL_BLOB,
            "scope": SCOPE, "configuration_scope": FIXTURE_SCOPE, "temporal_origin": "SIMULATED",
            "registered_at": REGISTERED_AT.isoformat(), "ledger_id": "C8-FIXTURE-LEDGER",
            "campaign_id": "C8-FIXTURE-CAMPAIGN", "access_registry_id": "C8-FIXTURE-ACCESS",
            "code_hash": code_hash(), "dataset_vintage": "C8_FIXTURE_V1",
            "upstream_snapshot_hash": current["snapshot_hash"],
            **{k: deepcopy(current[k]) for k in ("family_members", "representative_ties",
                "cohort_metadata", "model_instances", "used_outcomes", "horizon_contracts")},
            "datasets": datasets, "holdout_boundary": current["holdout_boundary"],
            "rebalance_schedule": ["2030-01-01T00:00:00+00:00", "2030-02-01T00:00:00+00:00",
                                   "2030-03-01T00:00:00+00:00"],
            "budget": {"max_attempts": 8, "unit": "ONE_REGISTERED_COMPLETE_FAMILY_PROTOCOL_ATTEMPT"},
            "tax_mode": "EXCLUDED",
            "threshold_registration": {
                "configuration_scope": FIXTURE_SCOPE, "version": "SYNTHETIC_REGISTRY_FIXTURE_v1",
                "range": "EXPLICIT_FIXTURE_ONLY", "grid": ["fixture-a", "fixture-b"],
                "sensitivity": "DECLARATION_ONLY_NOT_EXECUTED",
                "plateau": "DECLARATION_ONLY_NO_VALIDITY_CLAIM",
                "graph_universe": ["fixture-a", "fixture-b"],
                "adjacency": [["fixture-a", "fixture-b"]], "tolerance": {"fixture": .1},
                "rounding_rule": "FIXTURE_PREREGISTERED_LOOKUP_NOT_RESEARCH_ROUNDING",
                "rounding_support": "FIXTURE_EXPLICIT_SUPPORT_NOT_REAL_ELIGIBILITY",
                "vectors": {"fixture-a": {"fixture_only_threshold": .4},
                            "fixture-b": {"fixture_only_threshold": .5}},
                "fixture_fit_support": {
                    "fixture-a": {"rounded_vector": {"fixture_only_threshold": .4}, "support_ref": "FIT-FIXTURE-a"},
                    "fixture-b": {"rounded_vector": {"fixture_only_threshold": .5}, "support_ref": "FIT-FIXTURE-b"}}},
            "controls": [{"control_id": c, "construction_ref": "SYNTHETIC-" + c,
                          "seed": 7, "direction": "max", "metric": deepcopy(net), "effect_limit": None}
                         for c in CONTROLS],
            "economic_gates": [{"stage": stage, "metric": deepcopy(metric), "limit": None,
                               "comparator": ">", "configuration_scope": FIXTURE_SCOPE,
                               "authority_ref": "STRUCTURE_ONLY_NO_RESEARCH_NUMERIC"}
                              for stage, metric in zip(ECONOMIC_ORDER, identities)]}
    return plan, SyntheticProvider(datasets, bodies)


def setup(path, source):
    plan, provider = plan_and_provider(source)
    registry = AccessRegistry(path / "shared-access", plan["access_registry_id"])
    ledger = CalibrationLedger(path / "c8", registry)
    return {"ledger": ledger, "source": source, "plan": plan, "provider": provider}


def register(rig):
    return register_calibration(rig["ledger"], *rig["source"], rig["plan"])


def fit(rig, attempt_id="fit", at=FIT_AT):
    return read_partition(rig["ledger"], *rig["source"], rig["provider"],
                          role="CAL_FIT", attempt_id=attempt_id, at=at)


def choose(rig, attempt_id="choice", vector_id="fixture-a", fit_id="fit", at=FIT_AT):
    plan, ledger = rig["plan"], rig["ledger"]
    event = {"event_id": "choice-event-" + attempt_id, "actor_id": "SOFTWARE_FIXTURE_APPROVER",
             "kind": "EXPLICIT_SOFTWARE_FIXTURE_CHOICE", "at": at.isoformat(),
             "registration_hash": ledger.registration()["sha256"], "approval_blob": APPROVAL_BLOB}
    return record_fixture_threshold_choice(ledger, *rig["source"], fit_attempt_id=fit_id,
        vector_id=vector_id, rounded_vector=plan["threshold_registration"]["fixture_fit_support"][vector_id]["rounded_vector"],
        approval_event=event, attempt_id=attempt_id, at=at)


def verify(rig, attempt_id="verify", at=VERIFY_AT):
    return read_partition(rig["ledger"], *rig["source"], rig["provider"],
        role="CAL_VERIFY", attempt_id=attempt_id, at=at,
        fit_attempt_id="fit", choice_attempt_id="choice")


def complete(rig):
    register(rig)
    assert fit(rig)["status"] == "PASS"
    assert choose(rig)["status"] == "PASS"
    assert verify(rig)["status"] == "PASS"
    assert record_control_evidence(rig["ledger"], *rig["source"], source_attempt_id="verify",
        attempt_id="controls", at=VERIFY_AT)["status"] == "PASS"
    assert record_economic_evidence(rig["ledger"], *rig["source"], source_attempt_id="verify",
        attempt_id="economic", at=VERIFY_AT)["status"] == "PASS"
    ids = {"CAL_FIT": "fit", "THRESHOLD_CHOICE": "choice", "CAL_VERIFY": "verify",
           "CONTROL_EVIDENCE": "controls", "ECONOMIC_EVIDENCE": "economic"}
    artifact = software_artifact(rig["ledger"], *rig["source"], ids)
    assert resolve_software_artifact(artifact, rig["ledger"], *rig["source"]) == artifact
    return artifact


def full_acceptance(path):
    source = prepare_source(path / "source")
    rig = setup(path, source)
    artifact = complete(rig)
    return {"scope": SCOPE, "configuration_scope": FIXTURE_SCOPE,
            "status": "APPROVED_FOUNDATION_PROTOCOL_PASS",
            "artifact": artifact, "C8_SOFTWARE_FROZEN": False,
            "full_C8_acceptance": "NOT_RUN_UNAPPROVED_A6_A8_A10_AND_REAL_CONFIGURATION",
            "frozen_phase_count": "8/11 = 72.7% SOFTWARE_PHASE_COUNT_ONLY",
            "holdout_state": "UNCONSUMED", "real_pit_research_validated": False,
            "official": False, "Investor_QGV": "FUTURE_TRACK_C_INPUT"}


import pytest

@pytest.fixture(scope="session")
def c8_source(tmp_path_factory):
    root = tmp_path_factory.mktemp("c8-frozen-source")
    return root, prepare_source(root)


@pytest.fixture
def c8_rig(tmp_path, c8_source):
    root, source = c8_source
    copied = clone_source(root, source, tmp_path / "source")
    return setup(tmp_path, copied)


def refresh_partition(rig, role):
    """Fixture setup only, before registration; synchronize declared commitments."""
    data = rig["plan"]["datasets"][role]
    body = rig["provider"].bodies[role]
    for key in ("dataset_id", "scope", "synthetic", "source_id", "vintage", "lineage_ids", "samples"):
        body[key] = deepcopy(data[key])
    data["manifest_hash"] = digest({k: v for k, v in data.items() if k not in ("manifest_hash", "content_hash")})
    body["manifest_hash"] = data["manifest_hash"]
    data["content_hash"] = digest(body)
    rig["provider"].metadata[role] = deepcopy(data)
