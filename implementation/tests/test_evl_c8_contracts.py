"""Preregistration/authority and true missing configuration, not research defaults."""
from copy import deepcopy
import pytest
from investment_system.evl.calibration_contracts import (validate_plan, authority, BLOCKED,
    IntegrityFailure, MissingPrerequisite)
from tests.evl_c8_fixture import c8_source, c8_rig, register, refresh_partition


def test_partial_authority_never_whole_package(c8_rig):
    record = authority()
    assert record["approval_recorded_at_kst"] == "2026-10-02T17:47:51.000+09:00"
    assert record["clauses"]["A6"]["status"] == "PROPOSED_NOT_APPROVED_NOT_ACTIVE"
    assert record["clauses"]["A8"]["status"] == record["clauses"]["A10"]["status"]
    assert record["package_status"] != "APPROVED"
    assert validate_plan(c8_rig["plan"]) == c8_rig["plan"]
    assert all(g["limit"] is None for g in c8_rig["plan"]["economic_gates"])
    assert c8_rig["plan"]["economic_gates"][3]["metric"] is None
    assert c8_rig["provider"].reads == []


@pytest.mark.parametrize("field,value", [
    ("scope", "REAL_PIT_RESEARCH_VALIDATION"), ("configuration_scope", "REAL_DEFAULT"),
    ("temporal_origin", "ACTUAL"), ("schema", "UNAPPROVED_METHOD"),
    ("policy", "WHOLE_PACKAGE_A"), ("approval_blob", "forged"), ("code_hash", "stale"),
    ("tax_mode", "INCLUDED"), ("registered_at", "2020-01-01T00:00:00+00:00"),
    ("registered_at", "2026-10-03T00:00:00"), ("family_members", []),
    ("access_registry_id", "foreign")])
def test_wrong_scope_authority_code_tax_or_registration_never_reads(c8_rig, field, value):
    c8_rig["plan"][field] = value
    with pytest.raises((ValueError, KeyError, TypeError)):
        register(c8_rig)
    assert not c8_rig["ledger"].registration_path.exists()
    assert c8_rig["provider"].reads == []


@pytest.mark.parametrize("mutation", ["subset", "model", "ties", "outcomes", "horizon", "cohort"])
def test_registration_binds_actual_full_frozen_source(c8_rig, mutation):
    p = c8_rig["plan"]
    cohort = next(iter(p["cohort_metadata"]))
    candidate = p["family_members"][0]
    if mutation == "subset":
        p["family_members"] = p["family_members"][:1]
    elif mutation == "model":
        p["model_instances"][cohort][candidate]["model_hash"] = "new-fit"
    elif mutation == "ties":
        p["representative_ties"]["Balanced"] = []
    elif mutation == "outcomes":
        p["used_outcomes"]["sample_ids"] = []
    elif mutation == "horizon":
        p["horizon_contracts"][cohort]["max_label_horizon_microseconds"] += 1
    else:
        p["cohort_metadata"].pop(cohort)
    with pytest.raises((ValueError, KeyError, TypeError)):
        register(c8_rig)
    assert c8_rig["provider"].reads == []


@pytest.mark.parametrize("field", ["range", "grid", "sensitivity", "plateau", "graph_universe",
                                  "adjacency", "tolerance", "rounding_rule", "rounding_support"])
def test_threshold_definitions_must_be_pre_result(c8_rig, field):
    c8_rig["plan"]["threshold_registration"][field] = None
    with pytest.raises(MissingPrerequisite):
        register(c8_rig)
    assert c8_rig["provider"].reads == []


@pytest.mark.parametrize("field", ["alpha", "PSR_default", "PBO_threshold", "roles", "distinctness_rule"])
def test_unapproved_policy_is_not_hidden_in_placeholder_config(c8_rig, field):
    c8_rig["plan"][field] = .5
    with pytest.raises(IntegrityFailure):
        register(c8_rig)
    assert c8_rig["provider"].reads == []


@pytest.mark.parametrize("mutation", ["holdout_role", "development_role", "overlap", "reuse_id",
                                    "same_data", "bad_lineage", "bad_metric", "economic_order"])
def test_calibration_boundary_and_identity_fail_closed(c8_rig, mutation):
    p = c8_rig["plan"]
    if mutation in ("holdout_role", "development_role"):
        p["datasets"]["CAL_FIT"]["source_role"] = "HOLDOUT" if mutation == "holdout_role" else "C7_OOS"
        refresh_partition(c8_rig, "CAL_FIT")
    elif mutation == "overlap":
        p["datasets"]["CAL_VERIFY"]["window"]["start"] = p["datasets"]["CAL_FIT"]["window"]["start"]
        refresh_partition(c8_rig, "CAL_VERIFY")
    elif mutation == "reuse_id":
        p["datasets"]["CAL_VERIFY"]["samples"][0]["sample_id"] = p["used_outcomes"]["sample_ids"][0]
        refresh_partition(c8_rig, "CAL_VERIFY")
    elif mutation == "same_data":
        p["datasets"]["CAL_VERIFY"]["dataset_id"] = p["datasets"]["CAL_FIT"]["dataset_id"]
        refresh_partition(c8_rig, "CAL_VERIFY")
    elif mutation == "bad_lineage":
        p["datasets"]["CAL_FIT"]["lineage_ids"] = []
        refresh_partition(c8_rig, "CAL_FIT")
    elif mutation == "bad_metric":
        p["economic_gates"][0]["metric"]["formula_id"] = "NEW_PREMIUM_FORMULA"
    else:
        p["economic_gates"] = list(reversed(p["economic_gates"]))
    with pytest.raises((ValueError, KeyError)):
        register(c8_rig)
    assert c8_rig["provider"].reads == []


def test_no_threshold_search_is_a_declared_missing_prerequisite(c8_rig):
    c8_rig["plan"]["threshold_registration"] = None
    assert register(c8_rig)
    assert c8_rig["ledger"].registration()["body"]["plan"]["threshold_registration"] is None
    assert c8_rig["provider"].reads == []


def test_core_scores_and_predictive_thresholds_not_redefined(c8_rig):
    p = c8_rig["plan"]
    models = deepcopy(p["model_instances"])
    register(c8_rig)
    assert c8_rig["ledger"].registration()["body"]["plan"]["model_instances"] == models
    assert p["threshold_registration"]["version"].startswith("SYNTHETIC")
