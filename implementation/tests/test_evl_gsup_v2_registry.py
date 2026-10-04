"""V2 wiring and cross-version one-shot gates; explicit synthetic fixtures only."""
from copy import deepcopy

import pytest

from investment_system.evl import superiority as v1, superiority_v2 as v2
from investment_system.evl.calibration_contracts import IntegrityFailure, MissingPrerequisite
from investment_system.evl.walkforward import digest
from tests.test_evl_c8_gsup import DEV, Provider
from tests.test_evl_gsup_identity_kernel_invariance import (
    ACCESSED_AT, claims, feasibility, source_fixture,
)

REFUSAL = (IntegrityFailure, MissingPrerequisite, ValueError)


def fixture(tmp_path):
    spec, authority, binding, provider, old = source_fixture(tmp_path, Provider(mu=4., n=12))
    spec = {**spec, "schema": v2.METHOD, "policy": v2.POLICY}
    registry = v2.GsupV2Registry(tmp_path / "v2-attempt", authority)
    return spec, authority, binding, provider, registry, old


def test_actual_v2_feasibility_and_assessment_use_v2_without_mutating_v1(tmp_path):
    spec, authority, binding, provider, registry, _ = fixture(tmp_path)
    before = {k: v for k, v in vars(v1).items() if not k.startswith("__")}
    key = registry.register(spec, source_binding=binding)
    gate = feasibility(registry, key)
    assert gate["method"] == v2.METHOD and gate["cal_verify_read"] is False
    assert gate["status"] == "FEASIBLE" and provider.calls == []
    result = registry.assess(key, provider, accessed_at=ACCESSED_AT)
    assert result["method"] == v2.METHOD
    assert result["validation_mode"] == "SYNTHETIC_M_B_V2_ONLY"
    assert result["decision"] == "NOT_RUN_EFFECT_FLOOR_DEFERRED"
    assert result["official"] is False and result["promotion_authority"] is None
    assert result["real_holdout_eligible"] is False
    data = provider.numerical_provider(spec["verify_dataset_id"])
    for name, cell in result["cells"].items():
        cohort, control = name.split("|")
        b = data["cohorts"][cohort]
        expected = v2.studentized_cbb(tuple(a - c for a, c in zip(b["role"], b["controls"][control])),
                                     block_length=2, replicates=19, seed=7)
        assert cell["method"] == v2.METHOD
        assert cell["p_value"].hex() == expected["p_value"].hex()
        assert cell["draws_hash"] == digest(expected["draws"])
        assert cell["traces_hash"] == digest(expected["traces"])
    assert provider.calls == [spec["verify_dataset_id"]] and len(claims(authority)) == 1
    assert {k: v for k, v in vars(v1).items() if not k.startswith("__")} == before


@pytest.mark.parametrize("first_version", ["v1", "v2"])
def test_method_version_campaign_label_or_root_change_cannot_reconsume(tmp_path, first_version):
    spec, authority, binding, provider, current, old = fixture(tmp_path)
    old_spec = {**spec, "schema": v1.METHOD, "policy": v1.POLICY}
    first, second = (old, current) if first_version == "v1" else (current, old)
    initial, retry = (old_spec, spec) if first_version == "v1" else (spec, old_spec)
    key = first.register(initial, source_binding=binding)
    feasibility(first, key)
    first.assess(key, provider, accessed_at=ACCESSED_AT)
    retry = {**retry, "campaign_id": "renamed-campaign", "verify_dataset_id": "renamed-label",
             "verify_content_hash": digest([2])}
    key = second.register(retry, source_binding=binding)
    with pytest.raises(REFUSAL):
        feasibility(second, key)
    assert provider.calls == [initial["verify_dataset_id"]] and len(claims(authority)) == 1


@pytest.mark.parametrize("field,value", [
    ("schema", v1.METHOD), ("policy", v1.POLICY),
    ("scope", "REAL_PIT_RESEARCH_VALIDATION"), ("temporal_origin", "ACTUAL"),
    ("configuration_scope", "REAL"), ("alpha", None), ("seed", None),
    ("effect_floor", {"value": 0.}),
])
def test_no_implicit_method_numeric_default_or_real_scope(tmp_path, field, value):
    spec, authority, binding, provider, registry, _ = fixture(tmp_path)
    with pytest.raises(REFUSAL):
        registry.register({**spec, field: value}, source_binding=binding)
    assert provider.calls == [] and claims(authority) == []


@pytest.mark.parametrize("kind", ["missing", "incomplete", "wrong-authority"])
def test_v2_requires_trusted_complete_source_before_access(tmp_path, kind):
    spec, authority, binding, provider, registry, _ = fixture(tmp_path)
    binding = deepcopy(binding)
    if kind == "missing":
        binding = None
    elif kind == "incomplete":
        binding.pop("descriptor_hash")
    else:
        binding["authority_ref"] = "substituted-authority"
    with pytest.raises(REFUSAL):
        registry.register(spec, source_binding=binding)
    assert provider.calls == [] and claims(authority) == []


def test_v2_infeasible_mb_blocks_charge_without_outcome_or_v1_retry(tmp_path):
    spec, authority, binding, provider, registry, old = fixture(tmp_path)
    spec["block_rule"] = {"kind": "FIXED", "block_length": 6}
    key = registry.register(spec, source_binding=binding)
    gate = feasibility(registry, key)
    assert gate["status"] == "NOT_RUN_INFEASIBLE"
    assert gate["reasons"] == ["FEWER_THAN_TWO_VARIANCE_BLOCKS"]
    assert registry.assess(key, provider, accessed_at=ACCESSED_AT)["decision"] == "NOT_RUN_INFEASIBLE"
    key = old.register({**spec, "schema": v1.METHOD, "policy": v1.POLICY}, source_binding=binding)
    with pytest.raises(REFUSAL):
        feasibility(old, key)
    assert provider.calls == [] and len(claims(authority)) == 1


def test_v2_requires_development_content_and_lineage_not_a_role_label(tmp_path):
    spec, authority, binding, provider, registry, _ = fixture(tmp_path)
    key = registry.register(spec, source_binding=binding)
    with pytest.raises(REFUSAL):
        registry.record_feasibility(key, [0., 1., 2.], dataset_role="DEVELOPMENT", dataset_id="fixture-dev")
    assert provider.calls == [] and len(claims(authority)) == 1


@pytest.mark.parametrize("kind", ["missing", "tampered"])
def test_v2_arithmetic_authority_is_pinned_before_registration(tmp_path, monkeypatch, kind):
    spec, authority, binding, provider, registry, _ = fixture(tmp_path)
    path = tmp_path / "untrusted-approval.json"
    if kind == "tampered":
        path.write_bytes(v2.APPROVAL_PATH.read_bytes().replace(b"MATH_FSUM", b"BUILTIN_SUM"))
    monkeypatch.setattr(v2, "APPROVAL_PATH", path)
    with pytest.raises((IntegrityFailure, FileNotFoundError)):
        registry.register(spec, source_binding=binding)
    assert provider.calls == [] and claims(authority) == []


@pytest.mark.parametrize("kind", ["real-provider", "missing-feasibility", "response-substitution"])
def test_v2_provider_and_response_gates_preserve_no_retry(tmp_path, kind):
    spec, authority, binding, provider, registry, _ = fixture(tmp_path)
    key = registry.register(spec, source_binding=binding)
    if kind != "missing-feasibility":
        feasibility(registry, key)
    if kind == "real-provider":
        provider.synthetic = False
    if kind == "response-substitution":
        provider.identity["source_id"] = "substituted-source"
    with pytest.raises(REFUSAL):
        registry.assess(key, provider, accessed_at=ACCESSED_AT)
    assert len(provider.calls) == (1 if kind == "response-substitution" else 0)
    if kind == "response-substitution":
        with pytest.raises(REFUSAL):
            registry.assess(key, provider, accessed_at=ACCESSED_AT)
        assert len(provider.calls) == 1
