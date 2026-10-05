"""PIW-D002 compound evidence identity consistency consumer (stdlib only).

This additive utility does not change raw FPIA semantics or any acceptance gate.
``compare_identity(expected, observed)`` compares an independently selected
expected identity with one observed receipt or a list of candidate receipts.
Selecting and authenticating the expected identity is the caller's responsibility;
copying the receipt into both arguments proves no trust. No network, source hash,
signature, execution, or authorization is verified here. Even IDENTITY_MATCH keeps
authentication NOT_VERIFIED and integration_acceptance BLOCKED. Verifier approval,
runtime provenance, external execution/coverage and integration acceptance remain
separate gates. No verified actual receipt is bundled with this utility.

Normalized JSON input schema (all fields required except diagnostic job_name):
  repository: owner/repository, ASCII GitHub slug (no URL or ref)
  workflow_path: .github/workflows/<file>.yml or .yaml
  workflow_blob, workflow_source_commit, subject_sha: full lowercase nonzero SHA-1
  run_id, run_attempt, job_id: positive JSON integers, at most 2**64-1
  verifier: {repository: owner/repository, path: repository-relative source path,
             commit: full lowercase SHA-1, blob: full lowercase SHA-1}
  job_name: optional printable ASCII label, excluded from identity matching

The verifier describes one nominated source, not its transitive dependencies or
an authorized launcher. Commit/blob strings are compared, never independently
resolved. Repository comparison is exact and case-sensitive; collision detection
also recognizes GitHub's case-insensitive repository namespace. GitHub job IDs
are repository-scoped execution identifiers: reusing one in the same repository
is duplicate/ambiguous, including conflicting run IDs, attempts or workflow data.
Different repositories' common labels are NOTE diagnostics only.

CLI examples:
  python track_c_fpia_evidence_identity.py compare --expected expected.json \\
      --observed observed.json
  python track_c_fpia_evidence_identity.py diagnose --receipts receipts.json

Compare exits 0/1/2 for MATCH/MISMATCH/UNAVAILABLE. Diagnose takes a nonempty
receipt list and exits 0 for a structurally consistent unambiguous set, 2 for an
unavailable/ambiguous set; it does not perform an expected identity comparison.
Both commands emit stdout JSON, read input files only, and reject duplicate JSON
keys (including nested objects), nonfinite constants and malformed identities.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re


_BASE_FIELDS = (
    "repository", "workflow_path", "workflow_blob", "workflow_source_commit",
    "run_id", "run_attempt", "job_id", "subject_sha", "verifier",
)
_VERIFIER_FIELDS = ("repository", "path", "commit", "blob")
_IDENTITY_FIELDS = _BASE_FIELDS[:-1] + tuple("verifier." + field for field in _VERIFIER_FIELDS)
_SHA = re.compile(r"[0-9a-f]{40}")
_REPOSITORY = re.compile(
    r"[A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38}/[A-Za-z0-9][A-Za-z0-9_.-]{0,99}"
)
_PATH = re.compile(r"[A-Za-z0-9_.\-/]+")
_WORKFLOW = re.compile(r"\.github/workflows/[A-Za-z0-9][A-Za-z0-9_.-]*\.ya?ml")


def _base_result():
    return {
        "authentication": "NOT_VERIFIED",
        "integration_acceptance": "BLOCKED",
        "comparison_scope": "IDENTITY_CONSISTENCY_ONLY",
        "expected_identity_selection": "CALLER_RESPONSIBILITY",
        "diagnostics": [],
        "errors": [],
    }


def _valid_sha(value):
    return type(value) is str and _SHA.fullmatch(value) is not None and value != "0" * 40


def _valid_repository(value):
    return type(value) is str and _REPOSITORY.fullmatch(value) is not None


def _valid_path(value):
    return (type(value) is str and 0 < len(value) <= 512 and _PATH.fullmatch(value) is not None
            and all(part not in ("", ".", "..") for part in value.split("/")))


def _valid_workflow(value):
    return _valid_path(value) and _WORKFLOW.fullmatch(value) is not None


def _valid_id(value):
    # bool is an int subclass, but not an execution identifier.
    return type(value) is int and 0 < value < 2 ** 64


def _valid_label(value):
    return (type(value) is str and 0 < len(value) <= 256 and value.strip() == value
            and all(32 <= ord(char) <= 126 for char in value))


def _validate_identity(value, source):
    if type(value) is not dict:
        return [source + " must be an identity object"]
    errors = []
    if set(value) - set(_BASE_FIELDS) - {"job_name"}:
        errors.append(source + " contains unrecognized fields")
    validators = {
        "repository": _valid_repository, "workflow_path": _valid_workflow,
        "workflow_blob": _valid_sha, "workflow_source_commit": _valid_sha,
        "run_id": _valid_id, "run_attempt": _valid_id, "job_id": _valid_id,
        "subject_sha": _valid_sha,
    }
    for field, validator in validators.items():
        if field not in value or not validator(value[field]):
            errors.append(source + "." + field + " is missing or malformed")
    if "job_name" in value and not _valid_label(value["job_name"]):
        errors.append(source + ".job_name is malformed")
    verifier = value.get("verifier")
    if type(verifier) is not dict:
        errors.append(source + ".verifier must be a complete identity object")
    else:
        if set(verifier) - set(_VERIFIER_FIELDS):
            errors.append(source + ".verifier contains unrecognized fields")
        validators = {"repository": _valid_repository, "path": _valid_path,
                      "commit": _valid_sha, "blob": _valid_sha}
        for field, validator in validators.items():
            if field not in verifier or not validator(verifier[field]):
                errors.append(source + ".verifier." + field + " is missing or malformed")
    return errors


def _validate_receipts(receipts):
    if type(receipts) is not list or not receipts:
        return ["observed receipts must be a nonempty list of complete identity objects"]
    return [error for index, receipt in enumerate(receipts)
            for error in _validate_identity(receipt, "observed[%d]" % index)]


def _field(identity, field):
    if field.startswith("verifier."):
        return identity["verifier"][field.split(".")[1]]
    return identity[field]


def _compound(identity):
    return tuple(_field(identity, field) for field in _IDENTITY_FIELDS)


def _differences(left, right):
    return [field for field in _IDENTITY_FIELDS if _field(left, field) != _field(right, field)]


def _collision_diagnostics(receipts):
    executions, labels = {}, {}
    for index, receipt in enumerate(receipts):
        key = (receipt["repository"].lower(), receipt["job_id"])
        executions.setdefault(key, []).append(index)
        if "job_name" in receipt:
            labels.setdefault(receipt["job_name"], []).append(index)
    diagnostics = []
    for indices in executions.values():
        if len(indices) < 2:
            continue
        first = receipts[indices[0]]
        fields = {field for index in indices[1:] for field in _differences(first, receipts[index])}
        if fields:
            diagnostics.append({"code": "CONFLICTING_EXECUTION_RECEIPTS", "severity": "ERROR",
                                "receipt_indices": indices,
                                "fields": [field for field in _IDENTITY_FIELDS if field in fields]})
        else:
            diagnostics.append({"code": "DUPLICATE_EXECUTION_RECEIPT", "severity": "ERROR",
                                "receipt_indices": indices})
    for name, indices in labels.items():
        if len({_compound(receipts[index]) for index in indices}) > 1:
            diagnostics.append({"code": "GENERIC_JOB_LABEL_COLLISION", "severity": "NOTE",
                                "job_name": name, "receipt_indices": indices})
    return diagnostics


def diagnose_collisions(receipts):
    """Return receipt-set diagnostics without selecting or authenticating evidence.

    Input must be a nonempty list of complete receipts. Any malformed receipt,
    duplicate repository job ID or conflicting repository job ID fails closed.
    A shared generic label across distinct identities is informational only.
    """
    result = _base_result()
    result.update(comparison_performed=False, receipt_set_status="UNAVAILABLE")
    result["errors"] = _validate_receipts(receipts)
    if result["errors"]:
        return result
    result["diagnostics"] = _collision_diagnostics(receipts)
    result["receipt_set_status"] = (
        "AMBIGUOUS" if any(d["severity"] == "ERROR" for d in result["diagnostics"]) else "CONSISTENT"
    )
    return result


def compare_identity(expected, observed):
    """Compare externally selected expected identity to observed receipt(s).

    Return IDENTITY_MATCH, IDENTITY_MISMATCH or IDENTITY_UNAVAILABLE. Labels never
    select evidence. An invalid or ambiguous candidate makes the entire supplied
    receipt set unavailable, even if another candidate exactly matches expected.
    This function reads/mutates no files and does not mutate either input.
    """
    result = _base_result()
    result.update(status="IDENTITY_UNAVAILABLE", comparison_performed=False,
                  matched_receipt_index=None, mismatches=[])
    result["errors"] = _validate_identity(expected, "expected")
    if result["errors"]:
        result["reason"] = "INVALID_EXPECTED_IDENTITY"
        return result
    receipts = [observed] if type(observed) is dict else observed
    diagnosis = diagnose_collisions(receipts)
    result["diagnostics"] = diagnosis["diagnostics"]
    result["errors"] = diagnosis["errors"]
    if diagnosis["receipt_set_status"] != "CONSISTENT":
        result["reason"] = ("AMBIGUOUS_EXECUTION_RECEIPTS"
                            if diagnosis["receipt_set_status"] == "AMBIGUOUS"
                            else "INVALID_OR_UNAVAILABLE_OBSERVED_RECEIPTS")
        return result
    result["comparison_performed"] = True
    for index, receipt in enumerate(receipts):
        fields = _differences(expected, receipt)
        if not fields:
            result.update(status="IDENTITY_MATCH", matched_receipt_index=index,
                          reason="EXACT_COMPOUND_IDENTITY_MATCH")
            result["mismatches"] = []
            return result
        result["mismatches"].append({"receipt_index": index, "fields": fields})
    result.update(status="IDENTITY_MISMATCH", reason="NO_EXACT_COMPOUND_IDENTITY_MATCH")
    return result


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON object key")
        value[key] = item
    return value


def _reject_constant(value):
    raise ValueError("nonfinite JSON numeric constant")


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=_unique_object,
                      parse_constant=_reject_constant)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    compare = commands.add_parser("compare", help="compare expected identity and observed receipt JSON")
    compare.add_argument("--expected", required=True, help="independently selected expected identity JSON")
    compare.add_argument("--observed", required=True, help="observed receipt object or receipt list JSON")
    diagnose = commands.add_parser("diagnose", help="diagnose a receipt list without selecting evidence")
    diagnose.add_argument("--receipts", required=True, help="observed receipt list JSON")
    args = parser.parse_args(argv)
    try:
        if args.command == "compare":
            result = compare_identity(_read_json(args.expected), _read_json(args.observed))
            exit_code = {"IDENTITY_MATCH": 0, "IDENTITY_MISMATCH": 1, "IDENTITY_UNAVAILABLE": 2}[result["status"]]
        else:
            result = diagnose_collisions(_read_json(args.receipts))
            exit_code = 0 if result["receipt_set_status"] == "CONSISTENT" else 2
    except (OSError, ValueError, RecursionError) as exc:
        result = _base_result()
        result.update(comparison_performed=False, reason="INPUT_JSON_UNAVAILABLE", errors=[str(exc)])
        if args.command == "compare":
            result["status"] = "IDENTITY_UNAVAILABLE"
        else:
            result["receipt_set_status"] = "UNAVAILABLE"
        exit_code = 2
    print(json.dumps(result, sort_keys=True, ensure_ascii=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
