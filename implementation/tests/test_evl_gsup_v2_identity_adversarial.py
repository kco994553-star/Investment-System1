"""Independent synthetic-only adversarial source-identity review.

The trusted coordinator creates and injects one pinned authority. Attempt callers
may change campaign, local root, labels and value representation, but cannot issue
descriptors, replace the injected authority or erase trusted consumption history.
Privileged coordinator reset is outside this bounded local threat model.
No real CAL_VERIFY/Holdout provider, numeric default or statistical convention is
introduced by these tests.
"""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from threading import Barrier, Lock

import pytest

from investment_system.evl import superiority as v1
from investment_system.evl import gsup_source_identity as S
from investment_system.evl.calibration_contracts import IntegrityFailure, MissingPrerequisite
from investment_system.evl.walkforward import digest


# Exact original bytes at approved base 8230007f5edb86aec949166e25fd62a680db3ae2.
# Both the new identity protocol and a future numerical v2 must retain these.
PROTECTED = {
    "superiority.py": "c61268921e5a9147e90810747e9ab6cd2896dd2fab89cb314d390dc0ff760498",
    "calibration_ledger.py": "84985b798701abadfc7ea7cec82203d3c9716218588e8dabec03d55ab0c54ad0",
    "statistical_kernels.py": "61f70937456d8a54cb027a7522f2a2d1c890bccc92f9f19de28082a2001e12d1",
    "calibration_contracts.py": "9579a74ac2da688d0b3a2a09a28deed026a0ea82f565e1099791a285ce9fbb16",
}


@pytest.mark.parametrize("name,expected", PROTECTED.items())
def test_identity_protocol_retains_exact_v1_kernel_and_foundation_bytes(name, expected):
    path = Path(v1.__file__).parent / name
    assert sha256(path.read_bytes()).hexdigest() == expected


BOOT_AT = "2030-01-01T00:00:00+00:00"
DESCRIPTOR_AT = "2030-01-02T00:00:00+00:00"
REGISTRATION_AT = "2030-01-03T00:00:00+00:00"
ACCESS_AT = "2030-02-01T00:00:00+00:00"
REFUSAL = (IntegrityFailure, MissingPrerequisite)
COHORTS = tuple(f"{m}-{v}" for m in ("ROLLING", "EXPANDING")
                for v in ("PRIMARY", "REBALANCE_GAP_STRESS"))
CONTROLS = ("EQUAL_SIMPLE", "MARKET_CAP")


def descriptor(*, prefix="sample", profile="Balanced", role="CHAMPION", role_id="candidate-one"):
    """Identity-only literal fixture; periods are labels, never target returns."""
    periods = ["synthetic-period-001", "synthetic-period-002", "synthetic-period-003"]
    def rows(name):
        return {"period_ids": list(periods),
                "sample_ids": [f"{prefix}:{name}:{period}" for period in periods]}
    return {
        "schema": "C8_GSUP_SOURCE_IDENTITY_v1",
        "scope": "SYNTHETIC_SOFTWARE_VALIDATION",
        "configuration_scope": "SYNTHETIC_SOFTWARE_VALIDATION_ONLY",
        "temporal_origin": "SIMULATED", "synthetic": True,
        "registered_at": DESCRIPTOR_AT, "source_id": "synthetic-reviewed-source",
        "vintage": "synthetic-immutable-vintage", "profile": profile, "role": role,
        "role_id": role_id, "role_designation_ref": "SYNTHETIC_FIXTURE_ROLE",
        "period_ids": periods,
        "cohorts": {c: {"role": rows(c + ":ROLE"),
                        "controls": {name: rows(c + ":" + name) for name in CONTROLS}}
                    for c in COHORTS},
    }


def authority_at(path, *, authority_id="trusted-synthetic-authority"):
    legacy = path / "legacy-v1-shared"
    legacy.mkdir(parents=True)
    anchor = S.initialize_synthetic_authority(
        path / "authority", authority_id=authority_id, registered_at=BOOT_AT,
        legacy_registry=legacy,
    )
    # This pin is injected by the trusted coordinator, never taken from an attempt.
    pinned = anchor.authority_ref
    return anchor, S.SourceAuthority(anchor, expected_authority_ref=pinned), legacy


def resolved(authority, metadata, registration=None):
    registration = registration or authority.register_descriptor(metadata)
    return authority.resolve(
        registration["registration_ref"], registration["descriptor_hash"],
        profile=metadata["profile"], role=metadata["role"], role_id=metadata["role_id"],
        verify_periods=len(metadata["period_ids"]), cohorts=list(COHORTS),
        controls=list(CONTROLS), registered_at=REGISTRATION_AT,
    )


class Spy:
    def __init__(self, *, role_value=2.0, control_value=0.0, mutate=None):
        self.calls = []
        self.role_value, self.control_value, self.mutate = role_value, control_value, mutate

    def __call__(self, target, metadata):
        self.calls.append("SYNTHETIC_OUTCOME_READ")
        data = {
            "dataset_role": "CAL_VERIFY", "dataset_id": "synthetic-display-label",
            "role_id": metadata["role_id"], "synthetic": True,
            "source_identity": S.response_identity(target),
            "cohorts": {c: {"role": [self.role_value] * len(metadata["period_ids"]),
                            "controls": {name: [self.control_value] * len(metadata["period_ids"])
                                         for name in CONTROLS}}
                        for c in COHORTS},
        }
        if self.mutate:
            self.mutate(data)
        return data


def attempt(authority, metadata, spy, *, registration=None, attempt_identity="first"):
    target = resolved(authority, metadata, registration)
    claim = authority.claim(target, registration_hash=digest(attempt_identity), at=REGISTRATION_AT)
    authority.begin_access(claim, at=ACCESS_AT)
    data = spy(target, metadata)
    authority.validate_response(target, data)
    return data, claim


def test_missing_descriptor_and_unresolved_lineage_never_reach_outcome(tmp_path):
    _, authority, _ = authority_at(tmp_path)
    metadata, spy = descriptor(), Spy()
    with pytest.raises(REFUSAL):
        attempt(authority, metadata, spy,
                registration={"registration_ref": "unknown-registration", "descriptor_hash": "ab" * 32})
    assert spy.calls == []


@pytest.mark.parametrize("change", [
    {"source_id": ""}, {"vintage": ""}, {"period_ids": []},
    {"scope": "REAL_PIT_RESEARCH_VALIDATION"}, {"synthetic": False},
    {"configuration_scope": "REAL"}, {"temporal_origin": "ACTUAL"},
    {"outcome_values": [1.0, 2.0, 3.0]},
])
def test_untrusted_or_incomplete_descriptor_admission_is_pre_access(tmp_path, change):
    _, authority, _ = authority_at(tmp_path)
    metadata, spy = descriptor(), Spy()
    metadata.update(change)
    with pytest.raises(REFUSAL):
        attempt(authority, metadata, spy)
    assert spy.calls == []


@pytest.mark.parametrize("defect", ["missing_control", "duplicate_sample", "period_reorder"])
def test_incomplete_or_ambiguous_alignment_is_pre_access(tmp_path, defect):
    _, authority, _ = authority_at(tmp_path)
    metadata, spy = descriptor(), Spy()
    rows = metadata["cohorts"][COHORTS[0]]
    if defect == "missing_control":
        del rows["controls"][CONTROLS[0]]
    elif defect == "duplicate_sample":
        rows["role"]["sample_ids"][1] = rows["role"]["sample_ids"][0]
    else:
        rows["role"]["period_ids"] = list(reversed(rows["role"]["period_ids"]))
    with pytest.raises(REFUSAL):
        attempt(authority, metadata, spy)
    assert spy.calls == []


def test_copied_manifest_and_fresh_bootstrap_cannot_replace_injected_authority(tmp_path):
    anchor, authority, _ = authority_at(tmp_path / "trusted")
    expected_ref = anchor.authority_ref
    copied = tmp_path / "copied-authority"
    shutil.copytree(anchor.root, copied)
    copied_anchor = S.SourceAnchor.from_dict({**anchor.to_dict(), "root": str(copied)})
    with pytest.raises(REFUSAL):
        S.SourceAuthority(copied_anchor, expected_authority_ref=expected_ref)
    fresh_anchor, _, _ = authority_at(tmp_path / "fresh")
    assert fresh_anchor.authority_ref != expected_ref
    with pytest.raises(REFUSAL):
        S.SourceAuthority(fresh_anchor, expected_authority_ref=expected_ref)
    assert authority.anchor == anchor  # Original coordinator pin is retained.


def test_missing_authority_store_is_not_implicitly_bootstrapped(tmp_path):
    anchor, _, _ = authority_at(tmp_path / "trusted")
    missing = tmp_path / "missing"
    alias = S.SourceAnchor.from_dict({**anchor.to_dict(), "root": str(missing)})
    with pytest.raises(REFUSAL):
        S.SourceAuthority(alias, expected_authority_ref=anchor.authority_ref)
    assert not missing.exists()


@pytest.mark.parametrize("first,second", [(2.0, 2), (0.0, -0.0), (-0.0, 0)])
def test_reencoding_campaign_local_root_label_and_candidate_do_not_reopen(tmp_path, first, second):
    anchor, authority, _ = authority_at(tmp_path)
    metadata = descriptor()
    one = Spy(role_value=first)
    attempt(authority, metadata, one, attempt_identity={"campaign": "one", "root": "one", "raw": first})
    assert digest([first]) != digest([second]), "raw encoding commitments differ in this adversarial fixture"
    relabelled = descriptor(role_id="candidate-renamed")
    reopened = S.SourceAuthority(anchor, expected_authority_ref=anchor.authority_ref)
    two = Spy(role_value=second)
    with pytest.raises(REFUSAL):
        attempt(reopened, relabelled, two,
                attempt_identity={"campaign": "two", "root": "another-local-root", "label": "renamed", "raw": second})
    assert one.calls == ["SYNTHETIC_OUTCOME_READ"] and two.calls == []


def test_any_sample_overlap_is_blocked_before_a_second_outcome_read(tmp_path):
    _, authority, _ = authority_at(tmp_path)
    first = descriptor(prefix="original")
    attempt(authority, first, Spy())
    overlapping = descriptor(prefix="mostly-disjoint", role_id="other-candidate")
    overlapping["cohorts"][COHORTS[-1]]["controls"][CONTROLS[-1]]["sample_ids"][-1] = (
        first["cohorts"][COHORTS[0]]["role"]["sample_ids"][-1])
    spy = Spy()
    with pytest.raises(REFUSAL):
        attempt(authority, overlapping, spy, attempt_identity="overlapping registration")
    assert spy.calls == []


def test_disjoint_samples_and_existing_profile_role_groups_remain_independent(tmp_path):
    _, authority, _ = authority_at(tmp_path)
    for i, metadata in enumerate([
        descriptor(), descriptor(role="CHALLENGER"),
        descriptor(profile="Defensive"), descriptor(prefix="disjoint"),
    ]):
        spy = Spy()
        attempt(authority, metadata, spy, attempt_identity=f"independent-{i}")
        assert spy.calls == ["SYNTHETIC_OUTCOME_READ"]


def test_concurrent_overlapping_claims_admit_exactly_one_outcome_reader(tmp_path):
    anchor, _, _ = authority_at(tmp_path)
    gate, lock, calls = Barrier(2), Lock(), []
    def worker(i):
        authority = S.SourceAuthority(anchor, expected_authority_ref=anchor.authority_ref)
        metadata = descriptor(role_id=f"candidate-{i}")
        target = resolved(authority, metadata)
        gate.wait(timeout=10)
        try:
            claim = authority.claim(target, registration_hash=digest(f"concurrent-{i}"), at=REGISTRATION_AT)
            authority.begin_access(claim, at=ACCESS_AT)
            with lock:
                calls.append(i)
            data = Spy()(target, metadata)
            authority.validate_response(target, data)
            return "ADMITTED"
        except REFUSAL:
            return "BLOCKED_BEFORE_OUTCOME"
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(worker, [1, 2]))
    assert sorted(outcomes) == ["ADMITTED", "BLOCKED_BEFORE_OUTCOME"]
    assert len(calls) == 1


def test_process_death_after_claim_keeps_consumption_spent(tmp_path):
    anchor, authority, _ = authority_at(tmp_path)
    metadata = descriptor()
    registration = authority.register_descriptor(metadata)
    script = """
import json, os, sys
from investment_system.evl import gsup_source_identity as S
x=json.load(sys.stdin)
a=S.SourceAuthority(S.SourceAnchor.from_dict(x['anchor']), expected_authority_ref=x['expected_ref'])
m=x['metadata']; r=x['registration']
d=a.resolve(r['registration_ref'], r['descriptor_hash'], profile=m['profile'], role=m['role'],
            role_id=m['role_id'], verify_periods=len(m['period_ids']), cohorts=list(m['cohorts']),
            controls=['EQUAL_SIMPLE','MARKET_CAP'], registered_at=x['at'])
a.claim(d, registration_hash='ab'*32, at=x['at'])
os._exit(73)
"""
    env = dict(os.environ, PYTHONPATH=str(Path(S.__file__).parents[2]))
    process = subprocess.run([sys.executable, "-c", script], input=json.dumps({
        "anchor": anchor.to_dict(), "expected_ref": anchor.authority_ref, "metadata": metadata,
        "registration": registration, "at": REGISTRATION_AT,
    }), text=True, capture_output=True, env=env, timeout=15)
    assert process.returncode == 73, process.stderr
    reopened = S.SourceAuthority(anchor, expected_authority_ref=anchor.authority_ref)
    spy = Spy()
    with pytest.raises(REFUSAL):
        attempt(reopened, descriptor(role_id="new-candidate"), spy, attempt_identity="after process crash")
    assert spy.calls == []


def test_access_marker_prevents_retry_after_provider_crash_and_restart(tmp_path):
    anchor, authority, _ = authority_at(tmp_path)
    metadata = descriptor()
    target = resolved(authority, metadata)
    claim = authority.claim(target, registration_hash=digest("crashing-provider"), at=REGISTRATION_AT)
    authority.begin_access(claim, at=ACCESS_AT)
    calls = []
    def crashing_provider():
        calls.append("SYNTHETIC_OUTCOME_READ")
        raise RuntimeError("synthetic provider process failed")
    with pytest.raises(RuntimeError):
        crashing_provider()
    reopened = S.SourceAuthority(anchor, expected_authority_ref=anchor.authority_ref)
    with pytest.raises(REFUSAL):
        reopened.begin_access(reopened.load_claim(claim.claim_id), at=ACCESS_AT)
    assert calls == ["SYNTHETIC_OUTCOME_READ"]


@pytest.mark.parametrize("mutate", [
    lambda data: data["source_identity"].update(source_id="forged-source"),
    lambda data: data["source_identity"]["period_ids"].reverse(),
    lambda data: data.update(synthetic=False),
    lambda data: data["cohorts"][COHORTS[0]]["role"].pop(),
])
def test_response_identity_or_alignment_failure_keeps_charge_without_retry(tmp_path, mutate):
    anchor, authority, _ = authority_at(tmp_path)
    metadata, first = descriptor(), Spy(mutate=mutate)
    with pytest.raises(REFUSAL):
        attempt(authority, metadata, first)
    assert first.calls == ["SYNTHETIC_OUTCOME_READ"]
    second = Spy()
    with pytest.raises(REFUSAL):
        attempt(S.SourceAuthority(anchor, expected_authority_ref=anchor.authority_ref),
                descriptor(role_id="another-candidate"), second, attempt_identity="after integrity failure")
    assert second.calls == []


@pytest.mark.parametrize("kind", ["registration", "feasibility", "access", "result"])
def test_unresolved_historical_v1_record_is_fail_closed_and_unchanged(tmp_path, kind):
    _, authority, legacy = authority_at(tmp_path)
    path = legacy / f"{kind}-opaque-v1-target.json"
    original = b'{"historical_opaque_commitment":"no-source-sample-resolution"}\n'
    path.write_bytes(original)
    spy = Spy()
    with pytest.raises(REFUSAL):
        attempt(authority, descriptor(), spy)
    assert spy.calls == [] and path.read_bytes() == original


def test_partial_durable_journal_tail_is_preserved_and_refused_pre_access(tmp_path):
    anchor, authority, _ = authority_at(tmp_path)
    attempt(authority, descriptor(), Spy())
    journal = anchor.root / "claims.jsonl"
    with journal.open("ab") as handle:
        handle.write(b'{"interrupted-claim":')
        handle.flush()
        os.fsync(handle.fileno())
    broken = journal.read_bytes()
    spy = Spy()
    with pytest.raises(REFUSAL):
        attempt(authority, descriptor(prefix="disjoint-after-crash"), spy, attempt_identity="partial tail")
    assert spy.calls == [] and journal.read_bytes() == broken


def test_interrupt_after_durable_intent_before_journal_append_closes_authority(tmp_path, monkeypatch):
    anchor, authority, _ = authority_at(tmp_path)
    target = resolved(authority, descriptor())
    create = S._create
    def stop_after_intent(path, value):
        create(path, value)
        if path.parent.name == "claim-intents":
            raise RuntimeError("synthetic crash immediately after durable reservation intent")
    monkeypatch.setattr(S, "_create", stop_after_intent)
    with pytest.raises(RuntimeError):
        authority.claim(target, registration_hash=digest("pre-append-crash"), at=REGISTRATION_AT)
    intents = list((anchor.root / "claim-intents").iterdir())
    assert len(intents) == 1
    original_intent = intents[0].read_bytes()
    monkeypatch.setattr(S, "_create", create)
    spy = Spy()
    with pytest.raises(REFUSAL):
        attempt(authority, descriptor(prefix="disjoint-after-intent"), spy)
    with pytest.raises(REFUSAL):
        S.SourceAuthority(anchor, expected_authority_ref=anchor.authority_ref)
    assert spy.calls == [] and intents[0].read_bytes() == original_intent


def test_descriptor_changed_between_resolution_and_claim_refuses_outcome(tmp_path):
    anchor, authority, _ = authority_at(tmp_path)
    metadata, spy = descriptor(), Spy()
    registration = authority.register_descriptor(metadata)
    target = resolved(authority, metadata, registration)
    path = anchor.root / "descriptors" / (registration["registration_ref"] + ".json")
    record = json.loads(path.read_text())
    record["descriptor"]["source_id"] = "unexpected-substitute-source"
    path.chmod(0o600)
    path.write_text(json.dumps(record) + "\n")
    with pytest.raises(REFUSAL):
        authority.claim(target, registration_hash=digest("changed-descriptor"), at=REGISTRATION_AT)
    assert spy.calls == [] and len((anchor.root / "claims.jsonl").read_text().splitlines()) == 1


def test_provider_validation_preserves_exact_numerical_objects_without_reduction(tmp_path):
    _, authority, _ = authority_at(tmp_path)
    metadata = descriptor()
    target = resolved(authority, metadata)
    class NoNumericConversion:
        def __float__(self):
            raise AssertionError("identity protocol must not choose numerical conversion")
        def __add__(self, other):
            raise AssertionError("identity protocol must not choose arithmetic reduction")
    value = NoNumericConversion()
    data = Spy(role_value=value, control_value=value)(target, metadata)
    before = {c: (id(b["role"]), tuple(id(x) for x in b["role"]))
              for c, b in data["cohorts"].items()}
    assert authority.validate_response(target, data) is data
    assert {c: (id(b["role"]), tuple(id(x) for x in b["role"]))
            for c, b in data["cohorts"].items()} == before


def wrapper_spec(**changes):
    """Explicit existing-v1 synthetic fixture, never a v2 convention/default."""
    spec = {
        "schema": v1.METHOD, "policy": v1.POLICY, "scope": v1.SCOPE,
        "configuration_scope": v1.FIXTURE_SCOPE, "temporal_origin": "SIMULATED",
        "registered_at": REGISTRATION_AT, "campaign_id": "identity-review-campaign",
        "profile": "Balanced", "role": "CHAMPION", "role_id": "candidate-one",
        "role_designation_ref": "SYNTHETIC_FIXTURE_ROLE",
        "verify_dataset_id": "synthetic-review-label",
        "verify_content_hash": digest({c: {"role": [2.0] * 3,
                                           "controls": {name: [0.0] * 3 for name in CONTROLS}}
                                       for c in COHORTS}),
        "development_dataset_id": "synthetic-development-label",
        "development_content_hash": digest([1.0, 2.0, 3.0]),
        "development_lineage_ref": v1.DEVELOPMENT_FIXTURE_LINEAGE,
        "verify_periods": 3, "controls": list(CONTROLS), "cohorts": list(COHORTS),
        "evidence_kind": v1.EVIDENCE_KIND, "comparison_evidence": [],
        "alpha": 0.1, "replicates": 7, "block_rule": {"kind": "FIXED", "block_length": 1},
        "seed": 7, "minimum_support": 3,
        "feasibility": {"size_tolerance": 0.05,
                        "conservative_envelope": [{"kind": "AR1_GAUSSIAN", "phi": 0.0}],
                        "margin": 0.0, "dependence_estimator": v1.ESTIMATORS[0],
                        "replications": 2, "seed": 11},
        "effect_floor": dict(v1.EFFECT_FLOOR),
    }
    spec.update(changes)
    return spec


def wrapper_registry(path, authority, monkeypatch, *, verdict="FEASIBLE"):
    from investment_system.evl.superiority_source_identity import IdentityBoundGsupRegistry
    # These tests are identity/gate negatives, not feasibility-size simulations.
    # The gate is an independent declared synthetic fixture to reach assess.
    def fixed_gate(spec, estimate):
        return {"registration_hash": digest(spec), "status": verdict,
                "reasons": ["INDEPENDENT_SYNTHETIC_GATE_FIXTURE"]}
    monkeypatch.setattr(IdentityBoundGsupRegistry, "_feasibility", staticmethod(fixed_gate))
    return IdentityBoundGsupRegistry(path, authority)


class DeclaredSyntheticProvider:
    synthetic = True
    scope = v1.SCOPE

    def __init__(self, target, metadata):
        self.target, self.metadata, self.spy = target, metadata, Spy()

    @property
    def calls(self):
        return self.spy.calls

    def __call__(self, dataset_id):
        data = self.spy(self.target, self.metadata)
        data["dataset_id"] = dataset_id
        return data


def prepare_wrapper(registry, authority, metadata, *, spec=None):
    spec = spec or wrapper_spec(role_id=metadata["role_id"], profile=metadata["profile"], role=metadata["role"])
    binding = authority.register_descriptor(metadata)
    target = resolved(authority, metadata, binding)
    key = registry.register(spec, source_binding=binding)
    feasibility = registry.record_feasibility(
        key, [1.0, 2.0, 3.0], dataset_role="DEVELOPMENT", dataset_id=spec["development_dataset_id"])
    return spec, binding, target, key, feasibility


def test_wrapper_authentic_claim_for_another_descriptor_is_refused_before_provider(tmp_path, monkeypatch):
    anchor, authority, _ = authority_at(tmp_path)
    registry_a = wrapper_registry(tmp_path / "attempt-a", authority, monkeypatch)
    registry_b = wrapper_registry(tmp_path / "attempt-b", authority, monkeypatch)
    metadata_a, metadata_b = descriptor(prefix="source-a"), descriptor(prefix="source-b")
    spec_a, _, _, _, feasibility_a = prepare_wrapper(registry_a, authority, metadata_a)
    spec_b, binding_b, target_b, key_b, feasibility_b = prepare_wrapper(registry_b, authority, metadata_b)
    assert digest(spec_a) == digest(spec_b), "same spec can bind distinct trusted sample descriptors"
    changed = deepcopy(feasibility_b)
    changed["claim_receipt"] = deepcopy(feasibility_a["claim_receipt"])
    changed["record_hash"] = digest({k: v for k, v in changed.items() if k != "record_hash"})
    path = registry_b.shared / ("feasibility-" + registry_b._record_key(binding_b, spec_b) + ".json")
    path.chmod(0o600)
    path.write_text(json.dumps(changed) + "\n")
    provider = DeclaredSyntheticProvider(target_b, metadata_b)
    with pytest.raises(REFUSAL):
        registry_b.assess(key_b, provider, accessed_at=ACCESS_AT)
    assert provider.calls == [] and not list((anchor.root / "accesses").iterdir())


@pytest.mark.parametrize("binding_kind", ["missing", "fresh_authority"])
def test_wrapper_attempt_cannot_supply_or_replace_trusted_authority(tmp_path, monkeypatch, binding_kind):
    _, authority, _ = authority_at(tmp_path / "trusted")
    registry = wrapper_registry(tmp_path / "attempt", authority, monkeypatch)
    binding = None
    if binding_kind == "fresh_authority":
        _, untrusted_fresh, _ = authority_at(tmp_path / "attempt-controlled-fresh")
        binding = untrusted_fresh.register_descriptor(descriptor())
    with pytest.raises(REFUSAL):
        registry.register(wrapper_spec(), source_binding=binding)
    assert not list(registry.root.iterdir())


@pytest.mark.parametrize("provider_kind", ["undeclared", "wrong_scope", "not_synthetic"])
def test_wrapper_provider_declaration_is_checked_before_any_outcome_read(tmp_path, monkeypatch, provider_kind):
    anchor, authority, _ = authority_at(tmp_path)
    registry = wrapper_registry(tmp_path / "attempt", authority, monkeypatch)
    metadata = descriptor()
    _, _, target, key, _ = prepare_wrapper(registry, authority, metadata)
    provider = DeclaredSyntheticProvider(target, metadata)
    if provider_kind == "undeclared":
        original = provider
        provider = lambda dataset_id: original(dataset_id)
    elif provider_kind == "wrong_scope":
        provider.scope = "REAL_PIT_RESEARCH_VALIDATION"
    else:
        provider.synthetic = False
    with pytest.raises(REFUSAL):
        registry.assess(key, provider, accessed_at=ACCESS_AT)
    checked = original if provider_kind == "undeclared" else provider
    assert checked.calls == [] and not list((anchor.root / "accesses").iterdir())


def test_wrapper_missing_preaccess_feasibility_has_zero_provider_reads(tmp_path, monkeypatch):
    anchor, authority, _ = authority_at(tmp_path)
    registry = wrapper_registry(tmp_path / "attempt", authority, monkeypatch)
    metadata = descriptor()
    binding = authority.register_descriptor(metadata)
    target = resolved(authority, metadata, binding)
    key = registry.register(wrapper_spec(), source_binding=binding)
    provider = DeclaredSyntheticProvider(target, metadata)
    with pytest.raises(REFUSAL):
        registry.assess(key, provider, accessed_at=ACCESS_AT)
    assert provider.calls == [] and not list((anchor.root / "accesses").iterdir())


def test_wrapper_infeasible_attempt_keeps_claim_spent_without_provider(tmp_path, monkeypatch):
    _, authority, _ = authority_at(tmp_path)
    registry = wrapper_registry(tmp_path / "first-attempt", authority, monkeypatch, verdict="NOT_FEASIBLE")
    metadata = descriptor()
    _, _, target, key, _ = prepare_wrapper(registry, authority, metadata)
    provider = DeclaredSyntheticProvider(target, metadata)
    result = registry.assess(key, provider, accessed_at=ACCESS_AT)
    assert result["decision"] == "NOT_RUN_INFEASIBLE" and provider.calls == []
    retry = wrapper_registry(tmp_path / "different-attempt", authority, monkeypatch)
    new_metadata = descriptor(role_id="renamed-after-infeasibility")
    with pytest.raises(REFUSAL):
        prepare_wrapper(retry, authority, new_metadata,
                        spec=wrapper_spec(campaign_id="new-campaign", role_id=new_metadata["role_id"],
                                          verify_dataset_id="new-label", verify_content_hash="new-encoding"))
    assert provider.calls == []


def test_wrapper_failed_development_gate_claim_cannot_be_released_by_new_labels(tmp_path, monkeypatch):
    _, authority, _ = authority_at(tmp_path)
    registry = wrapper_registry(tmp_path / "first-attempt", authority, monkeypatch)
    metadata = descriptor()
    binding = authority.register_descriptor(metadata)
    key = registry.register(wrapper_spec(), source_binding=binding)
    with pytest.raises(REFUSAL):
        registry.record_feasibility(key, [1.0, 2.0, 3.0], dataset_role="INVALID_ROLE",
                                    dataset_id="synthetic-development-label")
    assert not list((authority.anchor.root / "accesses").iterdir())
    retry = wrapper_registry(tmp_path / "different-attempt", authority, monkeypatch)
    with pytest.raises(REFUSAL):
        prepare_wrapper(retry, authority, descriptor(role_id="renamed-after-gate-failure"))


def test_wrapper_read_once_then_reencoded_label_campaign_root_retry_has_zero_reads(tmp_path, monkeypatch):
    _, authority, _ = authority_at(tmp_path)
    registry = wrapper_registry(tmp_path / "first-attempt", authority, monkeypatch)
    metadata = descriptor()
    _, _, target, key, _ = prepare_wrapper(registry, authority, metadata)
    first = DeclaredSyntheticProvider(target, metadata)
    result = registry.assess(key, first, accessed_at=ACCESS_AT)
    assert first.calls == ["SYNTHETIC_OUTCOME_READ"]
    assert result["method"] == v1.METHOD and result["official"] is False
    assert result["validation_mode"] == "SYNTHETIC_IDENTITY_COMPATIBILITY_ONLY"
    retry = wrapper_registry(tmp_path / "different-attempt", authority, monkeypatch)
    new_metadata = descriptor(role_id="renamed-after-access")
    binding = authority.register_descriptor(new_metadata)
    changed_spec = wrapper_spec(campaign_id="new-campaign", role_id=new_metadata["role_id"],
                                verify_dataset_id="new-label", verify_content_hash=digest([2]))
    retry_key = retry.register(changed_spec, source_binding=binding)
    second = DeclaredSyntheticProvider(resolved(authority, new_metadata, binding), new_metadata)
    with pytest.raises(REFUSAL):
        retry.record_feasibility(retry_key, [1.0, 2.0, 3.0], dataset_role="DEVELOPMENT",
                                 dataset_id=changed_spec["development_dataset_id"])
    assert second.calls == []
