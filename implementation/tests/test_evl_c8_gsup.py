"""C8 G-SUP (A6 S1-S8, Q1-Q6): contract, oracle, feasibility gate and one-shot negatives.

Every numeric value here is SYNTHETIC_SOFTWARE_VALIDATION_ONLY fixture data, never a
research default. No real CAL_VERIFY or Holdout reader exists.
"""
from copy import deepcopy
import math
import pytest

from investment_system.evl import superiority as G
from investment_system.evl.calibration_contracts import IntegrityFailure, MissingPrerequisite
from investment_system.evl.statistical_kernels import MissingStatisticalEvidence
from tests.evl_c8_gsup_oracle import (oracle_indices, oracle_studentized, oracle_unstudentized,
                                      synthetic_delta)


def spec(**over):
    s = {"schema": G.METHOD, "policy": G.POLICY, "scope": G.SCOPE,
         "configuration_scope": G.FIXTURE_SCOPE, "temporal_origin": "SIMULATED",
         "registered_at": "2030-01-01T00:00:00+00:00", "campaign_id": "fixture-campaign",
         "profile": "Balanced", "role": "CHAMPION", "role_id": "cand-fixture-1",
         "role_designation_ref": "SYNTHETIC_FIXTURE_ROLE", "verify_dataset_id": "fixture-verify-1",
         "verify_periods": 48, "controls": ["EQUAL_SIMPLE", "MARKET_CAP"],
         "cohorts": list(G.REQUIRED_COHORTS), "evidence_kind": G.EVIDENCE_KIND,
         "comparison_evidence": [G.COMPARISON_ONLY], "alpha": 0.1, "replicates": 99,
         "block_rule": {"kind": "FIXED", "block_length": 3}, "seed": 7, "minimum_support": 24,
         "feasibility": {"size_tolerance": 0.05, "conservative_envelope": [{"kind": "AR1_GAUSSIAN", "phi": 0.0}],
                         "margin": 0.0, "dependence_estimator": G.ESTIMATORS[0],
                         "replications": 200, "seed": 11},
         "effect_floor": dict(G.EFFECT_FLOOR)}
    s.update(over)
    return s


def dev_estimate(phi=0.0, seed=3):
    return G.development_dependence_estimate(synthetic_delta(seed, 60, 0.0, phi), dataset_role="DEVELOPMENT",
                                             dataset_id="fixture-dev", estimator=G.ESTIMATORS[0])


class Provider:
    def __init__(self, mu, n=48, phi=0.0, role_id="cand-fixture-1", fail_control=None, synthetic=True):
        self.calls, self.mu, self.n, self.phi = [], mu, n, phi
        self.role_id, self.fail_control, self.synthetic = role_id, fail_control, synthetic

    def __call__(self, dataset_id):
        self.calls.append(dataset_id)
        cohorts = {}
        for i, cohort in enumerate(G.REQUIRED_COHORTS):
            control = {}
            for j, name in enumerate(G.SUPPORTED_CONTROLS):
                control[name] = synthetic_delta(100 + 10 * i + j, self.n, 0.0)
            mu = {name: (-0.5 if name == self.fail_control else self.mu) for name in G.SUPPORTED_CONTROLS}
            base = synthetic_delta(500 + i, self.n, 0.0, self.phi)
            role = tuple(b + mu[G.SUPPORTED_CONTROLS[0]] for b in base)
            control[G.SUPPORTED_CONTROLS[1]] = tuple(r - mu[G.SUPPORTED_CONTROLS[1]] - e for r, e in
                                                     zip(role, synthetic_delta(900 + i, self.n, 0.0)))
            control[G.SUPPORTED_CONTROLS[0]] = tuple(r - mu[G.SUPPORTED_CONTROLS[0]] - e for r, e in
                                                     zip(role, synthetic_delta(700 + i, self.n, 0.0)))
            cohorts[cohort] = {"role": role, "controls": control}
        return {"dataset_role": "CAL_VERIFY", "dataset_id": dataset_id, "role_id": self.role_id,
                "synthetic": self.synthetic, "cohorts": cohorts}


# ---- authority / scope -------------------------------------------------------------------

def test_authority_is_pinned_and_conditional():
    a = G.authority()
    assert a["A6_METHOD"]["approval_recorded_at_kst"] == "2026-10-02T20:43:44+09:00"
    assert a["A6_METHOD"]["Q"]["Q1"]["C_batch_means_t"] == "INACTIVE_NO_FALLBACK"
    assert set(a["A6_METHOD"]["not_approved_numeric"]) >= {"alpha", "B", "L_or_rule", "seed", "effect_floor"}
    assert a["A6_METHOD"]["status"]["A8"] == a["A6_METHOD"]["status"]["A10"] == "NOT_APPROVED"


@pytest.mark.parametrize("kind", G.NOT_SUPERIORITY_EVIDENCE)
def test_existing_c6_outputs_never_establish_superiority(kind):
    with pytest.raises(IntegrityFailure):
        G.reject_superiority_substitute(kind)
    with pytest.raises(IntegrityFailure):
        G.validate_registration(spec(evidence_kind=kind))


@pytest.mark.parametrize("field,value", [("scope", "REAL_PIT_RESEARCH_VALIDATION"),
                                         ("configuration_scope", "REAL"), ("temporal_origin", "ACTUAL")])
def test_real_scope_is_not_run(field, value):
    with pytest.raises(MissingPrerequisite):
        G.validate_registration(spec(**{field: value}))


@pytest.mark.parametrize("field", ["alpha", "replicates", "block_rule", "seed", "minimum_support", "feasibility"])
def test_missing_numeric_configuration_is_never_defaulted(field):
    with pytest.raises(MissingPrerequisite):
        G.validate_registration(spec(**{field: None}))


@pytest.mark.parametrize("key", ["size_tolerance", "conservative_envelope", "margin", "replications", "seed"])
def test_missing_feasibility_values_are_never_defaulted(key):
    s = spec()
    s["feasibility"][key] = None
    with pytest.raises(MissingPrerequisite):
        G.validate_registration(s)


@pytest.mark.parametrize("floor", [{"convention": "DEFERRED_A6_S7", "value": 0},
                                   {"convention": "DEFERRED_A6_S7", "value": 0.0},
                                   {"convention": "SHIFTED_TEST", "value": 0.01}, None])
def test_effect_floor_deferred_without_zero_default(floor):
    with pytest.raises(IntegrityFailure):
        G.validate_registration(spec(effect_floor=floor))


# ---- controls / conjunction ---------------------------------------------------------------

@pytest.mark.parametrize("control", sorted(G.UNSUPPORTED_CONTROLS))
def test_random_controls_unsupported_single_draw(control):
    with pytest.raises(G.UnsupportedControl, match="UNSUPPORTED_SINGLE_DRAW"):
        G.validate_registration(spec(controls=["EQUAL_SIMPLE", "MARKET_CAP", control]))


@pytest.mark.parametrize("controls", [["EQUAL_SIMPLE"], ["MARKET_CAP"], ["EQUAL_SIMPLE", "EQUAL_SIMPLE"],
                                      ["EQUAL_SIMPLE", "MARKET_CAP", "BENCHMARK_X"]])
def test_conjunction_needs_exactly_all_approved_controls(controls):
    with pytest.raises(IntegrityFailure):
        G.validate_registration(spec(controls=controls))


def test_conjunction_needs_every_required_cohort():
    with pytest.raises(MissingPrerequisite):
        G.validate_registration(spec(cohorts=list(G.REQUIRED_COHORTS)[:3]))


# ---- method / block convention -------------------------------------------------------------

@pytest.mark.parametrize("method", ["C8_GSUP_U_v1", "C8_GSUP_BATCH_MEANS_T_v1", "ANY_OTHER"])
def test_only_approved_method_no_fallback(method):
    with pytest.raises(IntegrityFailure):
        G.validate_registration(spec(schema=method))


def test_block_rule_not_approved_and_data_driven_forbidden():
    with pytest.raises(MissingPrerequisite):
        G.validate_registration(spec(block_rule={"kind": "DETERMINISTIC_RULE", "rule": "cube_root"}))
    with pytest.raises(IntegrityFailure):
        G.validate_registration(spec(block_rule={"kind": "DATA_DRIVEN"}))


def test_role_designation_requires_a10():
    with pytest.raises(MissingPrerequisite):
        G.validate_registration(spec(role_designation_ref="human-approval-event-1"))


# ---- kernel vs independent oracle -------------------------------------------------------------

@pytest.mark.parametrize("n,L,B,seed,mu,phi", [(12, 2, 49, 1, 0.3, 0.0), (24, 3, 99, 2, 0.0, 0.3),
                                               (37, 5, 101, 3, 0.2, 0.5), (60, 4, 199, 4, -0.1, 0.0),
                                               (48, 6, 99, 5, 0.6, 0.2)])
def test_studentized_kernel_matches_independent_oracle(n, L, B, seed, mu, phi):
    delta = synthetic_delta(seed, n, mu, phi)
    k = G.studentized_cbb(delta, block_length=L, replicates=B, seed=seed)
    o = oracle_studentized(delta, L, B, seed)
    assert math.isclose(k["statistic"], o["statistic"], rel_tol=1e-12, abs_tol=1e-12)
    assert k["exceedances"] == o["exceedances"] and k["p_value"] == o["p_value"]
    assert k["p_value"] == (k["exceedances"] + 1) / (B + 1)
    u = G.comparison_unstudentized(delta, block_length=L, replicates=B, seed=seed)
    ou = oracle_unstudentized(delta, L, B, seed)
    assert u["p_value_plus_one"] == ou["p_value"]
    assert u["role"] == "COMPARISON_EVIDENCE_ONLY_NOT_DECISION"


def test_oracle_indices_equal_frozen_c6_convention():
    from investment_system.evl.statistical_kernels import circular_block_indices
    assert [list(i) for i in circular_block_indices(n=17, block_length=4, replicates=30, seed=9)] \
        == oracle_indices(17, 4, 30, 9)


def test_kernel_is_deterministic_and_one_sided():
    up = synthetic_delta(8, 48, 0.8)
    down = tuple(-v for v in up)
    a = G.studentized_cbb(up, block_length=3, replicates=99, seed=1)
    assert a == G.studentized_cbb(up, block_length=3, replicates=99, seed=1)
    assert a["p_value"] == 1 / 100
    assert G.studentized_cbb(down, block_length=3, replicates=99, seed=1)["p_value"] > 0.9


@pytest.mark.parametrize("delta,L", [((0.1,) * 20, 2), (synthetic_delta(1, 5, 0.0), 3),
                                     (synthetic_delta(1, 3, 0.0), 2)])
def test_undefined_statistic_is_not_run(delta, L):
    with pytest.raises(MissingStatisticalEvidence):
        G.studentized_cbb(delta, block_length=L, replicates=19, seed=1)


def test_nonfinite_input_fails():
    with pytest.raises(ValueError):
        G.studentized_cbb((0.1, float("nan"), 0.2, 0.3), block_length=1, replicates=9, seed=1)


# ---- Development-only dependence / feasibility -------------------------------------------------

@pytest.mark.parametrize("role", ["CAL_VERIFY", "HOLDOUT", "CAL_FIT"])
def test_dependence_estimate_is_development_only(role):
    with pytest.raises(IntegrityFailure):
        G.development_dependence_estimate(synthetic_delta(1, 30, 0.0), dataset_role=role,
                                          dataset_id="x", estimator=G.ESTIMATORS[0])


def test_envelope_is_stricter_union():
    s = G.validate_registration(spec(feasibility={**spec()["feasibility"], "margin": 0.1,
                                                  "conservative_envelope": [{"kind": "AR1_GAUSSIAN", "phi": 0.4}]}))
    est = dev_estimate(phi=0.0)
    phis = sorted(p["phi"] for p in G.combined_envelope(s, est))
    assert phis[-1] == 0.4 and len(phis) == 2
    assert math.isclose(phis[0], max(est["phi"], 0) + 0.1)


def test_alpha_reachability_and_support_are_pre_access_infeasible():
    r = G.assess_feasibility(spec(alpha=0.005, replicates=99), dev_estimate())
    assert r["status"] == "NOT_RUN_INFEASIBLE" and "ALPHA_UNREACHABLE_AT_B" in r["reasons"]
    r = G.assess_feasibility(spec(verify_periods=12, minimum_support=24), dev_estimate())
    assert "BELOW_MINIMUM_SUPPORT" in r["reasons"] and r["sizes"] == []
    r = G.assess_feasibility(spec(verify_periods=5, minimum_support=1,
                                  block_rule={"kind": "FIXED", "block_length": 3}), dev_estimate())
    assert "FEWER_THAN_TWO_FULL_BLOCKS" in r["reasons"] and not r["cal_verify_read"]


def test_strong_dependence_envelope_is_infeasible_before_access():
    f = {**spec()["feasibility"], "size_tolerance": 0.0,
         "conservative_envelope": [{"kind": "AR1_GAUSSIAN", "phi": 0.9}]}
    r = G.assess_feasibility(spec(verify_periods=24, block_rule={"kind": "FIXED", "block_length": 2},
                                  feasibility=f), dev_estimate())
    assert r["status"] == "NOT_RUN_INFEASIBLE"
    assert "EMPIRICAL_SIZE_EXCEEDS_TOLERANCE" in r["reasons"]
    assert max(x["empirical_size"] for x in r["sizes"]) > 0.1


def test_feasible_record_is_deterministic():
    a = G.assess_feasibility(spec(), dev_estimate())
    assert a == G.assess_feasibility(spec(), dev_estimate())
    assert a["status"] == "FEASIBLE", a["sizes"]
    assert all(x["within_tolerance"] for x in a["sizes"]) and a["cal_verify_read"] is False


# ---- registry: preregistration, one-shot, no retry ---------------------------------------------

def run(tmp_path, provider, s=None, est=None):
    reg = G.GsupRegistry(tmp_path)
    key = reg.register(s or spec())
    reg.record_feasibility(key, est or dev_estimate())
    return reg, key, reg.assess(key, provider, accessed_at="2030-02-01T00:00:00+00:00")


def test_superior_role_is_stat_pass_but_decision_waits_for_effect_floor(tmp_path):
    p = Provider(mu=0.9)
    _, _, result = run(tmp_path, p)
    assert p.calls == ["fixture-verify-1"]
    assert result["statistical_status"] == "STAT_PASS"
    assert result["decision"] == "NOT_RUN_EFFECT_FLOOR_DEFERRED"
    assert len(result["cells"]) == 8 and all(c["status"] == "REJECT_H0" for c in result["cells"].values())
    assert all(c["comparison"]["role"] == "COMPARISON_EVIDENCE_ONLY_NOT_DECISION" for c in result["cells"].values())
    assert result["official"] is False and result["promotion_authority"] is None


def test_one_failing_control_fails_conjunction(tmp_path):
    _, _, result = run(tmp_path, Provider(mu=0.9, fail_control="MARKET_CAP"))
    assert result["statistical_status"] == "STAT_FAIL"
    assert any(c["status"] == "NOT_REJECTED" for k, c in result["cells"].items() if k.endswith("MARKET_CAP"))


def test_no_superiority_under_null(tmp_path):
    _, _, result = run(tmp_path, Provider(mu=-0.2))
    assert result["statistical_status"] == "STAT_FAIL"


def test_infeasible_never_reads_cal_verify_and_cannot_retest(tmp_path):
    f = {**spec()["feasibility"], "size_tolerance": 0.0, "conservative_envelope": [{"kind": "AR1_GAUSSIAN", "phi": 0.9}]}
    s = spec(verify_periods=24, block_rule={"kind": "FIXED", "block_length": 2}, feasibility=f)
    p = Provider(mu=0.9, n=24)
    reg, key, result = run(tmp_path, p, s)
    assert result["decision"] == result["statistical_status"] == "NOT_RUN_INFEASIBLE"
    assert p.calls == []
    with pytest.raises(IntegrityFailure):
        reg.assess(key, p, accessed_at="2030-03-01T00:00:00+00:00")
    for change in ({"alpha": 0.2}, {"seed": 8}, {"replicates": 199},
                   {"block_rule": {"kind": "FIXED", "block_length": 6}}):
        with pytest.raises(IntegrityFailure, match="already recorded"):
            reg.register(spec(verify_periods=24, feasibility=f, **change))
    assert p.calls == []


def test_cal_verify_is_one_shot(tmp_path):
    p = Provider(mu=0.9)
    reg, key, _ = run(tmp_path, p)
    with pytest.raises(IntegrityFailure, match="one-shot"):
        reg.assess(key, p, accessed_at="2030-03-01T00:00:00+00:00")
    assert p.calls == ["fixture-verify-1"]


def test_provider_crash_is_recorded_without_retry(tmp_path):
    reg = G.GsupRegistry(tmp_path)
    key = reg.register(spec())
    reg.record_feasibility(key, dev_estimate())

    def crash(_):
        raise RuntimeError("synthetic crash")
    with pytest.raises(RuntimeError):
        reg.assess(key, crash, accessed_at="2030-02-01T00:00:00+00:00")
    p = Provider(mu=0.9)
    with pytest.raises(IntegrityFailure):
        reg.assess(key, p, accessed_at="2030-03-01T00:00:00+00:00")
    assert p.calls == []


@pytest.mark.parametrize("provider", [Provider(mu=0.9, role_id="next-best"), Provider(mu=0.9, n=40),
                                      Provider(mu=0.9, synthetic=False)])
def test_provider_must_return_registered_target_only(tmp_path, provider):
    reg = G.GsupRegistry(tmp_path)
    key = reg.register(spec())
    reg.record_feasibility(key, dev_estimate())
    with pytest.raises((IntegrityFailure, MissingPrerequisite)):
        reg.assess(key, provider, accessed_at="2030-02-01T00:00:00+00:00")


def test_access_must_follow_registration_and_feasibility(tmp_path):
    reg = G.GsupRegistry(tmp_path)
    key = reg.register(spec())
    p = Provider(mu=0.9)
    with pytest.raises(MissingPrerequisite):
        reg.assess(key, p, accessed_at="2030-02-01T00:00:00+00:00")
    reg.record_feasibility(key, dev_estimate())
    with pytest.raises(IntegrityFailure):
        reg.assess(key, p, accessed_at="2029-12-31T00:00:00+00:00")
    assert p.calls == []


def test_tampered_registration_or_feasibility_fails(tmp_path):
    reg = G.GsupRegistry(tmp_path)
    key = reg.register(spec())
    record = reg.record_feasibility(key, dev_estimate())
    path = tmp_path / f"feasibility-{key}.json"
    path.chmod(0o644)
    import json
    body = json.loads(path.read_text())
    body["status"] = "FEASIBLE" if record["status"] != "FEASIBLE" else "NOT_RUN_INFEASIBLE"
    path.write_text(json.dumps(body) + "\n")
    with pytest.raises(IntegrityFailure):
        reg.assess(key, Provider(mu=0.9), accessed_at="2030-02-01T00:00:00+00:00")


def test_feasibility_cannot_follow_access(tmp_path):
    reg, key, _ = run(tmp_path, Provider(mu=0.9))
    with pytest.raises(IntegrityFailure):
        reg.record_feasibility(key, dev_estimate())
