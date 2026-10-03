"""Synthetic metadata admission, durable consumption and unchanged numerical inputs."""
from copy import deepcopy
from dataclasses import replace
import json
import multiprocessing
from pathlib import Path

import pytest

from investment_system.evl import gsup_source_identity as source
from investment_system.evl.calibration_contracts import IntegrityFailure, MissingPrerequisite
from investment_system.evl.superiority import studentized_cbb

T0 = "2030-01-01T00:00:00+00:00"
T1 = "2030-01-01T00:00:01+00:00"
T2 = "2030-01-01T00:00:02+00:00"
T3 = "2030-01-01T00:00:03+00:00"


def metadata(prefix="sample", *, profile="Balanced", role="CHAMPION", role_id="role-a"):
    periods = ["period-" + str(i) for i in range(6)]
    def stream(label):
        return {"sample_ids": [f"{prefix}-{label}-{i}" for i in range(6)], "period_ids": list(periods)}
    return {"schema": source.PROTOCOL, "scope": source.SCOPE, "configuration_scope": source.FIXTURE_SCOPE,
            "temporal_origin": "SIMULATED", "synthetic": True, "registered_at": T1,
            "source_id": "explicit-synthetic-source", "vintage": "explicit-synthetic-vintage",
            "profile": profile, "role": role, "role_id": role_id,
            "role_designation_ref": "SYNTHETIC_FIXTURE_ROLE", "period_ids": periods,
            "cohorts": {cohort: {"role": stream("role"),
                        "controls": {control: stream(control) for control in source.CONTROLS}}
                        for cohort in source.COHORTS}}


def open_authority(tmp_path, name="authority"):
    legacy = tmp_path / (name + "-legacy")
    legacy.mkdir()
    anchor = source.initialize_synthetic_authority(tmp_path / name, authority_id="fixture-coordinator",
                                                  registered_at=T0, legacy_registry=legacy)
    return source.SourceAuthority(anchor, expected_authority_ref=anchor.authority_ref)


def resolve(authority, data):
    binding = authority.register_descriptor(data)
    return authority.resolve(binding["registration_ref"], binding["descriptor_hash"],
                             profile=data["profile"], role=data["role"], role_id=data["role_id"],
                             verify_periods=len(data["period_ids"]), cohorts=source.COHORTS,
                             controls=source.CONTROLS, registered_at=T2)


def response(resolved):
    return {"dataset_role": "CAL_VERIFY", "dataset_id": "arbitrary-fixture-label", "synthetic": True,
            "role_id": resolved.descriptor["role_id"], "source_identity": source.response_identity(resolved),
            "cohorts": {cohort: {"role": [2.0, 3.0, 2.0, 1.0, 4.0, 3.0],
                         "controls": {control: [1, 1, 0, 0, 1, 0] for control in source.CONTROLS}}
                         for cohort in source.COHORTS}}


def test_metadata_is_immutable_and_resolved_before_outcomes(tmp_path):
    authority = open_authority(tmp_path)
    d = metadata()
    resolved = resolve(authority, d)
    d["source_id"] = "later-caller-mutation"
    returned = resolved.descriptor
    returned["source_id"] = "later-return-mutation"
    assert resolved.descriptor["source_id"] == "explicit-synthetic-source"
    with pytest.raises(IntegrityFailure, match="immutable"):
        authority.register_descriptor(metadata())
    with pytest.raises(IntegrityFailure):
        authority.resolve("unknown", "untrusted-hash", profile="Balanced", role="CHAMPION", role_id="role-a",
                          verify_periods=6, controls=source.CONTROLS, cohorts=source.COHORTS, registered_at=T2)


@pytest.mark.parametrize("attack", ["outcome", "real", "missing-samples", "missing-control", "reorder-periods",
                                  "different-role-designation", "sample-period-conflict", "duplicate-period"])
def test_incomplete_unapproved_or_outcome_descriptor_is_rejected(tmp_path, attack):
    authority = open_authority(tmp_path)
    d = metadata()
    cohort = source.COHORTS[0]
    if attack == "outcome":
        d["outcomes"] = [2.0] * 6
    elif attack == "real":
        d["synthetic"] = False
    elif attack == "missing-samples":
        d["cohorts"][cohort]["role"]["sample_ids"].pop()
    elif attack == "missing-control":
        d["cohorts"][cohort]["controls"].pop(source.CONTROLS[0])
    elif attack == "reorder-periods":
        d["cohorts"][cohort]["role"]["period_ids"].reverse()
    elif attack == "different-role-designation":
        d["role_designation_ref"] = "actual-production-role"
    elif attack == "sample-period-conflict":
        d["cohorts"][cohort]["role"]["sample_ids"].reverse()
    else:
        d["period_ids"][0] = d["period_ids"][1]
    with pytest.raises((IntegrityFailure, MissingPrerequisite)):
        authority.register_descriptor(d)
    assert not list((authority.anchor.root / "descriptors").iterdir())


def test_full_profile_role_and_time_alignment_precedes_claim(tmp_path):
    authority = open_authority(tmp_path)
    binding = authority.register_descriptor(metadata())
    args = dict(profile="Balanced", role="CHAMPION", role_id="role-a", verify_periods=6,
                controls=source.CONTROLS, cohorts=source.COHORTS, registered_at=T2)
    for change in ({"profile": "Defensive"}, {"role": "CHALLENGER"}, {"role_id": "other"},
                   {"verify_periods": 5}, {"cohorts": source.COHORTS[:-1]},
                   {"controls": source.CONTROLS[:1]}, {"registered_at": T0}):
        with pytest.raises(IntegrityFailure):
            authority.resolve(binding["registration_ref"], binding["descriptor_hash"], **(args | change))
    assert len((authority.anchor.root / "claims.jsonl").read_text().splitlines()) == 1


def test_external_pin_blocks_fresh_same_id_authority_and_copied_root(tmp_path):
    authority = open_authority(tmp_path)
    alternative = open_authority(tmp_path, "alternative")
    resolve(authority, metadata())
    resolve(alternative, metadata())
    with pytest.raises(IntegrityFailure, match="substitute"):
        source.SourceAuthority(alternative.anchor, expected_authority_ref=authority.anchor.authority_ref)
    import shutil
    copy = tmp_path / "copied"
    shutil.copytree(authority.anchor.root, copy)
    with pytest.raises(IntegrityFailure, match="manifest"):
        source.SourceAuthority(replace(authority.anchor, root=copy),
                               expected_authority_ref=authority.anchor.authority_ref)
    assert source.SourceAnchor.from_dict(authority.anchor.to_dict()) == authority.anchor


def test_relabels_local_root_campaign_or_int_float_encoding_cannot_reopen(tmp_path):
    authority = open_authority(tmp_path)
    first = resolve(authority, metadata())
    receipt = authority.claim(first, registration_hash="campaign-local-root-1", at=T2)
    relabeled = resolve(authority, metadata(role_id="renamed-role-label"))
    with pytest.raises(IntegrityFailure, match="stable samples"):
        authority.claim(relabeled, registration_hash="campaign-local-root-2", at=T2)
    data = response(first)
    before = deepcopy(data)
    assert authority.validate_response(first, data) is data and data == before
    for block in data["cohorts"].values():
        block["role"] = [int(x) for x in block["role"]]
    assert authority.validate_response(first, data) is data
    with pytest.raises(IntegrityFailure, match="stable samples"):
        authority.claim(first, registration_hash="same-values-new-serialization", at=T3)
    assert authority.load_claim(receipt.claim_id) == receipt


def test_partial_overlap_blocks_whole_set_but_disjoint_profile_role_groups_remain_allowed(tmp_path):
    authority = open_authority(tmp_path)
    first = resolve(authority, metadata())
    authority.claim(first, registration_hash="first", at=T2)
    overlap = metadata("second")
    for block in overlap["cohorts"].values():
        block["role"]["sample_ids"][0] = "sample-role-0"
    with pytest.raises(IntegrityFailure, match="stable samples"):
        authority.claim(resolve(authority, overlap), registration_hash="partially-overlapping", at=T2)
    authority.claim(resolve(authority, metadata("second")), registration_hash="disjoint", at=T2)
    authority.claim(resolve(authority, metadata(profile="Defensive")), registration_hash="different-profile", at=T2)
    authority.claim(resolve(authority, metadata(role="CHALLENGER")), registration_hash="different-role", at=T2)


def test_reserved_infeasible_or_crashed_attempt_stays_spent_without_access(tmp_path):
    authority = open_authority(tmp_path)
    resolved = resolve(authority, metadata())
    claim = authority.claim(resolved, registration_hash="infeasible-no-provider", at=T2)
    restart = source.SourceAuthority(authority.anchor, expected_authority_ref=authority.anchor.authority_ref)
    assert restart.load_claim(claim.claim_id) == claim
    assert not list((authority.anchor.root / "accesses").iterdir())
    with pytest.raises(IntegrityFailure):
        restart.claim(resolved, registration_hash="new-attempt-after-infeasible", at=T3)


def test_access_intent_is_durable_and_one_shot_before_provider(tmp_path):
    authority = open_authority(tmp_path)
    resolved = resolve(authority, metadata())
    claim = authority.claim(resolved, registration_hash="attempt", at=T2)
    intent = authority.begin_access(claim, at=T3)
    assert intent["claim"] == claim.to_dict()
    assert (authority.anchor.root / "accesses" / (claim.claim_id + ".json")).read_text().endswith("\n")
    restart = source.SourceAuthority(authority.anchor, expected_authority_ref=authority.anchor.authority_ref)
    with pytest.raises(IntegrityFailure, match="no retry"):
        restart.begin_access(restart.load_claim(claim.claim_id), at=T3)
    with pytest.raises(IntegrityFailure, match="receipt"):
        restart.begin_access(replace(claim, registration_hash="forged-attempt"), at=T3)


@pytest.mark.parametrize("failure", ["torn-journal", "missing-journal", "pending-intent", "fsync-failure"])
def test_interrupted_reservation_never_reopens_on_restart(tmp_path, monkeypatch, failure):
    authority = open_authority(tmp_path)
    resolved = resolve(authority, metadata())
    if failure == "torn-journal":
        with (authority.anchor.root / "claims.jsonl").open("a") as handle:
            handle.write('{"partial":')
    elif failure == "missing-journal":
        (authority.anchor.root / "claims.jsonl").unlink()
    elif failure == "pending-intent":
        (authority.anchor.root / "claim-intents" / "crash.json").write_text('{"partial":')
    else:
        original = source.os.fsync
        def failed(_fd):
            raise OSError("injected fsync failure")
        monkeypatch.setattr(source.os, "fsync", failed)
        with pytest.raises(OSError):
            authority.claim(resolved, registration_hash="interrupted", at=T2)
        monkeypatch.setattr(source.os, "fsync", original)
    with pytest.raises(IntegrityFailure):
        source.SourceAuthority(authority.anchor, expected_authority_ref=authority.anchor.authority_ref)


@pytest.mark.parametrize("kind", ["registration", "feasibility", "access", "result", "partial"])
def test_unknown_historical_records_are_not_treated_as_unseen(tmp_path, kind):
    authority = open_authority(tmp_path)
    legacy = tmp_path / "authority-legacy"
    (legacy / (kind + "-opaque.json")).write_text('{"no_source_identity":true}\n')
    with pytest.raises(MissingPrerequisite, match="unresolved historical"):
        source.SourceAuthority(authority.anchor, expected_authority_ref=authority.anchor.authority_ref)


def _claim_process(anchor_dict, resolved, queue):
    try:
        anchor = source.SourceAnchor.from_dict(anchor_dict)
        authority = source.SourceAuthority(anchor, expected_authority_ref=anchor.authority_ref)
        authority.claim(resolved, registration_hash="parallel", at=T2)
        queue.put("admitted")
    except IntegrityFailure:
        queue.put("blocked")


def test_cross_process_overlap_has_exactly_one_atomic_admission(tmp_path):
    authority = open_authority(tmp_path)
    resolved = resolve(authority, metadata())
    context = multiprocessing.get_context("fork")
    queue = context.Queue()
    workers = [context.Process(target=_claim_process, args=(authority.anchor.to_dict(), resolved, queue)) for _ in range(2)]
    for worker in workers:
        worker.start()
    results = [queue.get(timeout=15) for _ in workers]
    for worker in workers:
        worker.join(timeout=15)
        assert worker.exitcode == 0
    assert sorted(results) == ["admitted", "blocked"]
    assert len((authority.anchor.root / "claims.jsonl").read_text().splitlines()) == 2


@pytest.mark.parametrize("attack", ["reordered-samples", "source", "vintage", "missing-control", "missing-period", "real"])
def test_provider_alignment_failures_remain_spent(tmp_path, attack):
    authority = open_authority(tmp_path)
    resolved = resolve(authority, metadata())
    claim = authority.claim(resolved, registration_hash="attempt", at=T2)
    authority.begin_access(claim, at=T3)
    data = response(resolved)
    if attack == "reordered-samples":
        data["source_identity"]["cohorts"][source.COHORTS[0]]["role"]["sample_ids"].reverse()
    elif attack in ("source", "vintage"):
        data["source_identity"]["source_id" if attack == "source" else "vintage"] = "different"
    elif attack == "missing-control":
        data["cohorts"][source.COHORTS[0]]["controls"].pop(source.CONTROLS[0])
    elif attack == "missing-period":
        data["cohorts"][source.COHORTS[0]]["role"].pop()
    else:
        data["synthetic"] = False
    with pytest.raises(IntegrityFailure):
        authority.validate_response(resolved, data)
    with pytest.raises(IntegrityFailure):
        authority.begin_access(claim, at=T3)


def test_descriptor_tampering_after_reservation_blocks_access(tmp_path):
    authority = open_authority(tmp_path)
    resolved = resolve(authority, metadata())
    claim = authority.claim(resolved, registration_hash="attempt", at=T2)
    path = authority.anchor.root / "descriptors" / (resolved.registration_ref + ".json")
    stored = json.loads(path.read_text())
    stored["descriptor"]["vintage"] = "post-reservation-change"
    path.chmod(0o644)
    path.write_text(json.dumps(stored) + "\n")
    with pytest.raises(IntegrityFailure, match="changed"):
        authority.begin_access(claim, at=T3)
    assert not list((authority.anchor.root / "accesses").iterdir())
    assert authority.load_claim(claim.claim_id) == claim


def test_identity_validation_preserves_exact_fixture_numbers_and_legacy_kernel_result(tmp_path):
    authority = open_authority(tmp_path)
    resolved = resolve(authority, metadata())
    data = response(resolved)
    block = data["cohorts"][source.COHORTS[0]]
    numbers = block["role"]
    delta = tuple(a - b for a, b in zip(numbers, block["controls"][source.CONTROLS[0]]))
    before = studentized_cbb(delta, block_length=2, replicates=7, seed=13)
    authority.validate_response(resolved, data)
    assert block["role"] is numbers
    assert tuple(a - b for a, b in zip(numbers, block["controls"][source.CONTROLS[0]])) == delta
    assert studentized_cbb(delta, block_length=2, replicates=7, seed=13) == before
