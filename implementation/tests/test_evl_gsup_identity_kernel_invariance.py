"""Independent synthetic identity wiring checks; v1 numerical semantics stay fixed.

The identity wrapper is a compatibility path, never authoritative M-B v2 or a
real CAL_VERIFY reader. All numbers below are explicit software fixtures.
"""
from copy import deepcopy
import json

import pytest

from investment_system.evl import superiority as G
from investment_system.evl.calibration_contracts import IntegrityFailure, MissingPrerequisite
from investment_system.evl.gsup_source_identity import (
    PROTOCOL, SourceAuthority, initialize_synthetic_authority, response_identity,
)
from investment_system.evl.superiority_source_identity import IdentityBoundGsupRegistry
from tests.test_evl_c8_gsup import DEV, Provider, bound


REGISTERED_AT = "2030-01-01T00:00:00+00:00"
ACCESSED_AT = "2030-02-01T00:00:00+00:00"


class IdentityProvider:
    synthetic = True
    scope = G.SCOPE

    def __init__(self, numerical_provider, identity):
        self.numerical_provider = numerical_provider
        self.identity = deepcopy(identity)
        self.calls = []

    def __call__(self, dataset_id):
        self.calls.append(dataset_id)
        result = self.numerical_provider(dataset_id)
        result["source_identity"] = deepcopy(self.identity)
        return result


def fixture_spec(provider):
    return bound(
        provider, verify_periods=12, alpha=0.2, replicates=19, minimum_support=3,
        block_rule={"kind": "FIXED", "block_length": 2}, seed=7,
        feasibility={"size_tolerance": 1.0,
                     "conservative_envelope": [{"kind": "AR1_GAUSSIAN", "phi": 0.0}],
                     "margin": 0.0, "dependence_estimator": G.ESTIMATORS[0],
                     "replications": 4, "seed": 11},
    )


def metadata(spec):
    periods = [f"period-{i}" for i in range(spec["verify_periods"])]
    def stream(name):
        return {"period_ids": list(periods),
                "sample_ids": [f"{name}-sample-{i}" for i in range(len(periods))]}
    return {"schema": PROTOCOL, "scope": G.SCOPE,
            "configuration_scope": G.FIXTURE_SCOPE, "temporal_origin": "SIMULATED",
            "synthetic": True, "registered_at": REGISTERED_AT,
            "source_id": "independent-synthetic-fixture-source",
            "vintage": "independent-synthetic-fixture-vintage",
            "profile": spec["profile"], "role": spec["role"], "role_id": spec["role_id"],
            "role_designation_ref": "SYNTHETIC_FIXTURE_ROLE", "period_ids": periods,
            "cohorts": {cohort: {"role": stream(cohort + "-role"),
                                  "controls": {control: stream(cohort + "-" + control)
                                               for control in spec["controls"]}}
                        for cohort in spec["cohorts"]}}


def source_fixture(tmp_path, numerical_provider):
    spec = fixture_spec(numerical_provider)
    legacy = tmp_path / "unspent-historical-v1-store"
    legacy.mkdir()
    anchor = initialize_synthetic_authority(
        tmp_path / "coordinator-authority", authority_id="independent-fixture-authority",
        registered_at=REGISTERED_AT, legacy_registry=legacy,
    )
    authority = SourceAuthority(anchor, expected_authority_ref=anchor.authority_ref)
    binding = authority.register_descriptor(metadata(spec))
    resolved = authority.resolve(
        binding["registration_ref"], binding["descriptor_hash"],
        profile=spec["profile"], role=spec["role"], role_id=spec["role_id"],
        verify_periods=spec["verify_periods"], cohorts=spec["cohorts"],
        controls=spec["controls"], registered_at=spec["registered_at"],
    )
    provider = IdentityProvider(numerical_provider, response_identity(resolved))
    registry = IdentityBoundGsupRegistry(tmp_path / "bound-attempt", authority)
    return spec, authority, binding, provider, registry


def feasibility(registry, key):
    return registry.record_feasibility(key, DEV, dataset_role="DEVELOPMENT", dataset_id="fixture-dev")


def claims(authority):
    rows = [json.loads(line) for line in (authority.anchor.root / "claims.jsonl").read_text().splitlines()]
    return [row["record"] for row in rows if row["record"]["kind"] == "CLAIM"]


def v1_globals():
    return {name: value for name, value in vars(G).items() if not name.startswith("__")}


@pytest.mark.parametrize("mu,failed_control", [(4.0, None), (-2.0, None), (4.0, "MARKET_CAP")])
def test_identity_wiring_preserves_every_existing_result_field(tmp_path, mu, failed_control):
    numerical = Provider(mu=mu, n=12, fail_control=failed_control)
    spec, authority, binding, provider, wrapped = source_fixture(tmp_path, numerical)
    original_globals = v1_globals()
    before_registry = G.GsupRegistry(tmp_path / "reference-attempt", tmp_path / "reference-shared")
    before_key = before_registry.register(spec)
    before_feasibility = feasibility(before_registry, before_key)
    before = before_registry.assess(before_key, numerical, accessed_at=ACCESSED_AT)

    after_key = wrapped.register(spec, source_binding=binding)
    after_feasibility = feasibility(wrapped, after_key)
    after = wrapped.assess(after_key, provider, accessed_at=ACCESSED_AT)
    assert after_key == before_key
    # Only the feasibility envelope hash changes because source provenance is additive.
    assert {key: after_feasibility[key] for key in before_feasibility if key != "record_hash"} == {
        key: value for key, value in before_feasibility.items() if key != "record_hash"}
    assert {key: after[key] for key in before} == before
    assert after["method"] == G.METHOD
    assert after["decision"] == "NOT_RUN_EFFECT_FLOOR_DEFERRED"
    assert after["official"] is False and after["promotion_authority"] is None
    assert after["validation_mode"] == "SYNTHETIC_IDENTITY_COMPATIBILITY_ONLY"
    assert len(claims(authority)) == 1
    assert len(list((authority.anchor.root / "accesses").iterdir())) == 1
    assert provider.calls == [spec["verify_dataset_id"]]
    assert v1_globals() == original_globals
    assert IdentityBoundGsupRegistry._evaluate.__globals__["legacy"] is G


@pytest.mark.parametrize("binding_kind", ["missing", "incomplete", "wrong-authority", "unresolved"])
def test_binding_admission_failure_never_reads_or_charges(tmp_path, binding_kind):
    spec, authority, binding, provider, registry = source_fixture(tmp_path, Provider(mu=4.0, n=12))
    altered = deepcopy(binding)
    if binding_kind == "missing":
        altered = None
    elif binding_kind == "incomplete":
        altered.pop("descriptor_hash")
    elif binding_kind == "wrong-authority":
        altered["authority_ref"] = "untrusted-authority"
    else:
        altered["registration_ref"] = "unresolved-descriptor"
    with pytest.raises((IntegrityFailure, MissingPrerequisite)):
        registry.register(spec, source_binding=altered)
    assert claims(authority) == [] and provider.calls == []
    assert not list((authority.anchor.root / "accesses").iterdir())


def test_wrong_development_evidence_keeps_irreversible_reservation_without_outcome(tmp_path):
    spec, authority, binding, provider, registry = source_fixture(tmp_path, Provider(mu=4.0, n=12))
    key = registry.register(spec, source_binding=binding)
    with pytest.raises(IntegrityFailure, match="Development"):
        registry.record_feasibility(key, DEV, dataset_role="CAL_VERIFY", dataset_id="fixture-dev")
    assert len(claims(authority)) == 1 and provider.calls == []
    assert not list((authority.anchor.root / "accesses").iterdir())
    with pytest.raises(IntegrityFailure, match="already reserved"):
        feasibility(registry, key)
    assert len(claims(authority)) == 1 and provider.calls == []


def test_real_provider_refused_before_call_with_existing_charge_retained(tmp_path):
    spec, authority, binding, provider, registry = source_fixture(tmp_path, Provider(mu=4.0, n=12))
    key = registry.register(spec, source_binding=binding)
    feasibility(registry, key)
    provider.synthetic = False
    with pytest.raises(MissingPrerequisite, match="synthetic outcome provider"):
        registry.assess(key, provider, accessed_at=ACCESSED_AT)
    assert provider.calls == [] and len(claims(authority)) == 1
    assert not list((authority.anchor.root / "accesses").iterdir())


def test_mismatched_response_is_spent_before_failure_and_cannot_retry(tmp_path):
    spec, authority, binding, provider, registry = source_fixture(tmp_path, Provider(mu=4.0, n=12))
    key = registry.register(spec, source_binding=binding)
    feasibility(registry, key)
    provider.identity["vintage"] = "different-vintage"
    with pytest.raises(IntegrityFailure, match="source/vintage"):
        registry.assess(key, provider, accessed_at=ACCESSED_AT)
    assert provider.calls == [spec["verify_dataset_id"]]
    assert len(claims(authority)) == 1
    assert len(list((authority.anchor.root / "accesses").iterdir())) == 1
    record_key = registry._record_key(binding, spec)
    result = registry._load(registry.shared, "result", record_key)
    assert result["statistical_status"] == "NOT_RUN" and result["decision"] == "CRASH_NO_RETRY"
    with pytest.raises(IntegrityFailure, match="one-shot"):
        registry.assess(key, provider, accessed_at="2030-03-01T00:00:00+00:00")
    assert provider.calls == [spec["verify_dataset_id"]]


def test_changed_campaign_cannot_reuse_the_charged_source_under_another_root(tmp_path):
    spec, authority, binding, provider, registry = source_fixture(tmp_path, Provider(mu=4.0, n=12))
    key = registry.register(spec, source_binding=binding)
    feasibility(registry, key)
    changed = deepcopy(spec)
    changed.update(campaign_id="another-campaign", seed=17)
    other = IdentityBoundGsupRegistry(tmp_path / "another-attempt-root", authority)
    other_key = other.register(changed, source_binding=binding)
    with pytest.raises(IntegrityFailure, match="already reserved"):
        feasibility(other, other_key)
    assert len(claims(authority)) == 1 and provider.calls == []
    assert not list((authority.anchor.root / "accesses").iterdir())
