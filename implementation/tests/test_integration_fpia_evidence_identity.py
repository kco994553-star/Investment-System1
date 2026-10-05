"""PIW-D002: exercise identity binding without claiming receipt authentication.

These tests catch omitted identity fields, name-based selection, ambiguous
execution receipts, malformed input accepted as evidence, and false acceptance.
The consumer import is deliberately lazy so the initial red run is a clear
assertion failure inside tests rather than a collection failure.
"""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest


TOOL = Path(__file__).resolve().parents[1] / "tools/integration/track_c_fpia_evidence_identity.py"


def consumer():
    assert TOOL.is_file(), "PIW-D002 compound evidence identity consumer is not implemented"
    spec = importlib.util.spec_from_file_location("fpia_evidence_identity_under_test", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def identity():
    # Synthetic, hand-selected identifiers; this is NOT an actual verified receipt.
    return {
        "repository": "example/Investment-System1",
        "workflow_path": ".github/workflows/track-c-fpia.yml",
        "workflow_blob": "1111111111111111111111111111111111111111",
        "workflow_source_commit": "2222222222222222222222222222222222222222",
        "run_id": 101,
        "run_attempt": 1,
        "job_id": 201,
        "subject_sha": "3333333333333333333333333333333333333333",
        "verifier": {
            "repository": "example/Investment-System1",
            "path": "implementation/tools/integration/track_c_fpia.py",
            "commit": "4444444444444444444444444444444444444444",
            "blob": "5555555555555555555555555555555555555555",
        },
        "job_name": "verify",
    }


def set_field(value, field, replacement):
    parts = field.split(".")
    target = value
    for part in parts[:-1]:
        target = target[part]
    target[parts[-1]] = replacement


def assert_blocked(result):
    assert result["authentication"] == "NOT_VERIFIED"
    assert result["integration_acceptance"] == "BLOCKED"


def test_complete_exact_identity_matches_but_does_not_authenticate_or_accept():
    result = consumer().compare_identity(identity(), identity())
    assert result["status"] == "IDENTITY_MATCH"
    assert result["matched_receipt_index"] == 0
    assert_blocked(result)


@pytest.mark.parametrize("field,replacement", [
    ("repository", "other/Investment-System1"),
    ("workflow_path", ".github/workflows/unrelated.yml"),
    ("workflow_blob", "6666666666666666666666666666666666666666"),
    ("workflow_source_commit", "7777777777777777777777777777777777777777"),
    ("run_id", 102), ("run_attempt", 2), ("job_id", 202),
    ("subject_sha", "8888888888888888888888888888888888888888"),
    ("verifier.repository", "other/verifier"),
    ("verifier.path", "implementation/tools/other_verifier.py"),
    ("verifier.commit", "9999999999999999999999999999999999999999"),
    ("verifier.blob", "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"),
])
def test_substitution_of_each_compound_field_mismatches(field, replacement):
    observed = identity()
    set_field(observed, field, replacement)
    result = consumer().compare_identity(identity(), observed)
    assert result["status"] == "IDENTITY_MISMATCH"
    assert result["mismatches"] == [{"receipt_index": 0, "fields": [field]}]
    assert_blocked(result)


def test_job_label_is_not_part_of_identity_and_is_never_selection_authority():
    observed = identity()
    observed["job_name"] = "a renamed job"
    assert consumer().compare_identity(identity(), observed)["status"] == "IDENTITY_MATCH"
    observed["subject_sha"] = "6666666666666666666666666666666666666666"
    observed["job_name"] = "verify"
    assert consumer().compare_identity(identity(), observed)["status"] == "IDENTITY_MISMATCH"


def test_same_generic_label_for_other_compound_identity_is_diagnostic_only():
    other = identity()
    other.update(repository="unrelated/project", run_id=301, job_id=401,
                 workflow_path=".github/workflows/other.yml")
    result = consumer().compare_identity(identity(), [other, identity()])
    assert result["status"] == "IDENTITY_MATCH"
    assert result["matched_receipt_index"] == 1
    notes = [d for d in result["diagnostics"] if d["code"] == "GENERIC_JOB_LABEL_COLLISION"]
    assert notes == [{"code": "GENERIC_JOB_LABEL_COLLISION", "severity": "NOTE",
                      "job_name": "verify", "receipt_indices": [0, 1]}]
    assert_blocked(result)


def test_standalone_collision_diagnostic_does_not_require_an_expected_identity():
    other = identity()
    other.update(repository="unrelated/project", job_id=401)
    result = consumer().diagnose_collisions([identity(), other])
    assert result["receipt_set_status"] == "CONSISTENT"
    assert any(d["code"] == "GENERIC_JOB_LABEL_COLLISION" for d in result["diagnostics"])
    assert_blocked(result)


def test_repeated_execution_receipt_is_ambiguous_even_when_bytes_agree():
    result = consumer().compare_identity(identity(), [identity(), identity()])
    assert result["status"] == "IDENTITY_UNAVAILABLE"
    assert any(d["code"] == "DUPLICATE_EXECUTION_RECEIPT" for d in result["diagnostics"])
    assert_blocked(result)


@pytest.mark.parametrize("field,replacement", [
    ("workflow_path", ".github/workflows/substituted.yml"),
    ("workflow_blob", "6666666666666666666666666666666666666666"),
    ("workflow_source_commit", "7777777777777777777777777777777777777777"),
    ("run_id", 102), ("run_attempt", 2),
    ("subject_sha", "8888888888888888888888888888888888888888"),
    ("verifier.commit", "9999999999999999999999999999999999999999"),
])
def test_one_repository_job_id_with_conflicting_execution_fields_fails_closed(field, replacement):
    other = identity()
    set_field(other, field, replacement)
    result = consumer().compare_identity(identity(), [identity(), other])
    assert result["status"] == "IDENTITY_UNAVAILABLE"
    conflict = next(d for d in result["diagnostics"] if d["code"] == "CONFLICTING_EXECUTION_RECEIPTS")
    assert field in conflict["fields"]


def test_repository_case_alias_cannot_hide_conflicting_job_id():
    other = identity()
    other["repository"] = "Example/investment-system1"
    other["subject_sha"] = "6666666666666666666666666666666666666666"
    assert consumer().compare_identity(identity(), [identity(), other])["status"] == "IDENTITY_UNAVAILABLE"


def test_missing_job_label_still_supports_exact_selection():
    expected, observed = identity(), identity()
    del expected["job_name"]
    del observed["job_name"]
    assert consumer().compare_identity(expected, observed)["status"] == "IDENTITY_MATCH"


@pytest.mark.parametrize("missing", [
    "repository", "workflow_path", "workflow_blob", "workflow_source_commit",
    "run_id", "run_attempt", "job_id", "subject_sha", "verifier",
    "verifier.repository", "verifier.path", "verifier.commit", "verifier.blob",
])
@pytest.mark.parametrize("side", ["expected", "observed"])
def test_each_missing_identity_field_is_unavailable(missing, side):
    expected, observed = identity(), identity()
    value = expected if side == "expected" else observed
    parts = missing.split(".")
    target = value if len(parts) == 1 else value[parts[0]]
    del target[parts[-1]]
    result = consumer().compare_identity(expected, observed)
    assert result["status"] == "IDENTITY_UNAVAILABLE"
    assert_blocked(result)


@pytest.mark.parametrize("field,bad", [
    ("repository", "https://github.com/example/project"),
    ("repository", "owner-/project"), ("repository", "owner--name/project"),
    ("repository", "example/project/extra"),
    ("repository", "../project"), ("repository", "exampl\u0435/project"),
    ("repository", "example/project\n"),
    ("workflow_path", "/.github/workflows/verify.yml"),
    ("workflow_path", ".github/workflows/../verify.yml"),
    ("workflow_path", ".github/workflows//verify.yml"),
    ("workflow_path", ".github/workflows/nested/verify.yml"),
    ("workflow_path", ".github/workflows/verify.yml\x00"),
    ("workflow_path", ".github/workflows/verify\u202e.yml"),
    ("workflow_path", ".github\\workflows\\verify.yml"),
    ("workflow_blob", "A" * 40), ("workflow_source_commit", "b" * 39),
    ("subject_sha", "c" * 41), ("subject_sha", "g" * 40),
    ("subject_sha", "0" * 40), ("subject_sha", 123),
    ("run_id", True), ("run_id", "101"), ("run_id", 0),
    ("run_id", -1), ("run_id", 101.0), ("run_id", 2 ** 64),
    ("run_attempt", False), ("run_attempt", 0), ("job_id", True),
    ("verifier", "trusted"), ("verifier.repository", "example/../verifier"),
    ("verifier.repository", "owner-/verifier"),
    ("verifier.repository", "owner--name/verifier"),
    ("verifier.path", "../track_c_fpia.py"),
    ("verifier.path", "implementation/./track_c_fpia.py"),
    ("verifier.path", "implementation/%2e%2e/track_c_fpia.py"),
    ("verifier.path", "implementation/\u00e9.py"),
    ("verifier.path", "C:\\tools\\verifier.py"),
    ("verifier.commit", None), ("verifier.blob", "trusted"),
    ("job_name", "verify\n"), ("job_name", "verif\u0443"), ("job_name", " verify"),
])
@pytest.mark.parametrize("side", ["expected", "observed"])
def test_malformed_identity_values_fail_closed(field, bad, side):
    expected, observed = identity(), identity()
    set_field(expected if side == "expected" else observed, field, bad)
    result = consumer().compare_identity(expected, observed)
    assert result["status"] == "IDENTITY_UNAVAILABLE"
    assert_blocked(result)


@pytest.mark.parametrize("observed", [None, [], "verify", {"job_name": "verify"}, ["verify"]])
def test_unavailable_or_bare_name_observations_cannot_match(observed):
    result = consumer().compare_identity(identity(), observed)
    assert result["status"] == "IDENTITY_UNAVAILABLE"
    assert_blocked(result)


def test_malformed_extra_receipt_cannot_be_ignored_even_beside_exact_match():
    result = consumer().compare_identity(identity(), [identity(), {"job_name": "verify"}])
    assert result["status"] == "IDENTITY_UNAVAILABLE"


@pytest.mark.parametrize("claim", ["authentication", "trusted", "self_hash", "integration_acceptance"])
def test_unrecognized_caller_claims_do_not_create_authenticated_evidence(claim):
    observed = identity()
    observed[claim] = "VERIFIED"
    result = consumer().compare_identity(identity(), observed)
    assert result["status"] == "IDENTITY_UNAVAILABLE"
    assert_blocked(result)


def test_consumer_does_not_modify_expected_or_observed_inputs():
    expected, observed = identity(), [identity()]
    before = copy.deepcopy((expected, observed))
    consumer().compare_identity(expected, observed)
    assert (expected, observed) == before


def run_cli(tmp_path, *arguments):
    consumer()
    return subprocess.run([sys.executable, str(TOOL), *arguments], cwd=tmp_path,
                          capture_output=True, text=True, check=False)


def write_json(tmp_path, name, value):
    path = tmp_path / name
    path.write_text(json.dumps(value), encoding="utf-8")
    return str(path)


@pytest.mark.parametrize("status,exit_code,change", [
    ("IDENTITY_MATCH", 0, None),
    ("IDENTITY_MISMATCH", 1, "6666666666666666666666666666666666666666"),
    ("IDENTITY_UNAVAILABLE", 2, "missing"),
])
def test_cli_reads_json_and_exits_by_consistency_status(tmp_path, status, exit_code, change):
    expected = write_json(tmp_path, "expected.json", identity())
    observed_value = identity()
    if change == "missing":
        observed_value = None
    elif change is not None:
        observed_value["subject_sha"] = change
    observed = write_json(tmp_path, "observed.json", observed_value)
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    result = run_cli(tmp_path, "compare", "--expected", expected, "--observed", observed)
    assert result.returncode == exit_code
    assert result.stderr == ""
    output = json.loads(result.stdout)
    assert output["status"] == status
    assert_blocked(output)
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == before


@pytest.mark.parametrize("source", ["expected", "observed"])
@pytest.mark.parametrize("bad_text", [
    '{"job_id":201,"job_id":202}',
    '{"verifier":{"commit":"one","commit":"two"}}',
    '{"run_id":NaN}', '{"run_id":Infinity}', '{"run_id":101,}',
])
def test_cli_duplicate_keys_and_malformed_json_fail_closed(tmp_path, source, bad_text):
    paths = {side: write_json(tmp_path, side + ".json", identity())
             for side in ("expected", "observed")}
    Path(paths[source]).write_text(bad_text, encoding="utf-8")
    result = run_cli(tmp_path, "compare", "--expected", paths["expected"], "--observed", paths["observed"])
    assert result.returncode == 2
    output = json.loads(result.stdout)
    assert output["status"] == "IDENTITY_UNAVAILABLE"
    assert_blocked(output)


def test_cli_absent_receipt_file_returns_unavailable_json(tmp_path):
    expected = write_json(tmp_path, "expected.json", identity())
    result = run_cli(tmp_path, "compare", "--expected", expected,
                     "--observed", str(tmp_path / "absent.json"))
    assert result.returncode == 2
    assert json.loads(result.stdout)["status"] == "IDENTITY_UNAVAILABLE"


def test_cli_standalone_diagnostics_reports_conflicting_execution(tmp_path):
    other = identity()
    other["subject_sha"] = "6666666666666666666666666666666666666666"
    receipts = write_json(tmp_path, "receipts.json", [identity(), other])
    result = run_cli(tmp_path, "diagnose", "--receipts", receipts)
    assert result.returncode == 2
    output = json.loads(result.stdout)
    assert output["receipt_set_status"] == "AMBIGUOUS"
    assert any(d["code"] == "CONFLICTING_EXECUTION_RECEIPTS" for d in output["diagnostics"])
    assert_blocked(output)


def test_cli_standalone_generic_name_collision_is_a_note(tmp_path):
    other = identity()
    other.update(repository="other/project", job_id=401)
    receipts = write_json(tmp_path, "receipts.json", [identity(), other])
    result = run_cli(tmp_path, "diagnose", "--receipts", receipts)
    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert output["receipt_set_status"] == "CONSISTENT"
    assert output["comparison_performed"] is False
    assert_blocked(output)
