"""PIW-D003/D005 read-only execution coverage guard for TRACK_C_FPIA/2.

Usage: --evidence fpia.json --subject <exact commit> --result-sha256 <external anchor>

Bind the raw result to an independently selected subject and result digest before
reporting its execution limitations. V2 explicitly does not cover constructed
invocations, external code or descendant module provenance. A raw PASS, empty
inventory or caller-supplied completion label cannot close these limitations.
No exception/allowlist/noninterference assertion is accepted by this consumer.

Exit 1 = bound evidence with unresolved coverage; 2 = unavailable/malformed or
substituted evidence. There is deliberately no acceptance-success exit in this
schema. Integrity is not authentication: verifier authority, receipt execution
binding, external bytes/noninterference and final exact merge-result acceptance
remain separate obligations. This does not modify historical FPIA results or
their raw status composition and does not execute code named in the evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re


SCHEMA = "TRACK_C_FPIA/2"


def _result():
    return {"status": "COVERAGE_UNAVAILABLE", "authentication": "NOT_VERIFIED",
            "integration_acceptance": "BLOCKED", "blockers": [], "errors": [],
            "scope": "RAW_RESULT_EXECUTION_LIMITATIONS_ONLY"}


def _hex(value, length):
    return (type(value) is str and re.fullmatch("[0-9a-f]{%d}" % length, value) is not None
            and value != "0" * length)


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def assess_coverage(document, expected_subject, expected_result_sha256):
    """Fail closed on v2 gaps without mutating, authenticating or executing input.

    Expected values must come from the actual source/CI evidence, not the same
    untrusted document. Equal self-rehashed inputs prove consistency only.
    """
    out = _result()
    if not _hex(expected_subject, 40) or not _hex(expected_result_sha256, 64):
        out["errors"].append("Expected subject/result anchor missing or malformed")
        return out
    if type(document) is not dict or document.get("schema") != SCHEMA:
        out["errors"].append("Unsupported or unavailable document schema")
        return out
    raw = document.get("result")
    if type(raw) is not dict or raw.get("schema") != SCHEMA:
        out["errors"].append("Unsupported or unavailable result schema")
        return out
    try:
        actual_hash = _digest(raw)
    except (ValueError, TypeError, RecursionError):
        out["errors"].append("Result cannot be represented as finite protocol JSON")
        return out
    if document.get("result_sha256") != actual_hash or actual_hash != expected_result_sha256:
        out["errors"].append("Result digest does not match both document and external anchor")
        return out
    subject = raw.get("subject")
    if type(subject) is not dict or subject.get("tree") != expected_subject:
        out["errors"].append("Exact subject does not match expected commit")
        return out
    fpia = raw.get("fpia")
    if type(fpia) is not dict or fpia.get("status") not in ("FPIA_PASS", "FPIA_FAIL", "FPIA_NOT_RUN"):
        out["errors"].append("Raw FPIA status missing or malformed")
        return out
    interference = raw.get("integration_interference")
    if type(interference) is not dict:
        out["errors"].append("Execution coverage section unavailable")
        return out
    workflow = interference.get("workflow_analysis")
    if type(workflow) is not dict:
        out["errors"].append("Workflow execution inventory unavailable")
        return out
    for section in (interference, workflow):
        for field in ("dynamic_invocation_detection", "out_of_tree_code_analysis"):
            if type(section.get(field)) is not str or not section[field]:
                out["errors"].append("Execution limitation field missing or malformed: " + field)
    references, spawns = workflow.get("out_of_tree_references"), interference.get("spawns")
    for label, records in (("external references", references), ("spawn records", spawns)):
        if type(records) is not list or any(type(record) is not dict or not record for record in records):
            out["errors"].append("Missing or malformed " + label)
    if out["errors"]:
        return out
    out.update(status="COVERAGE_BLOCKED", subject_sha=expected_subject,
               result_sha256=actual_hash, raw_fpia_status=fpia["status"],
               external_reference_count=len(references), external_inventory_sha256=_digest(references),
               spawn_count=len(spawns), spawn_inventory_sha256=_digest(spawns))
    out["blockers"] = [
        {"code": "DYNAMIC_EXECUTION_UNCOVERED", "decision": "PIW-D003",
         "observed": [interference["dynamic_invocation_detection"], workflow["dynamic_invocation_detection"]],
         "next_action": "Resolve acceptance-relevant executed bytes or independently verify enforced noninterference"},
        {"code": "EXTERNAL_EXECUTION_UNANALYSED", "decision": "PIW-D005",
         "observed": [interference["out_of_tree_code_analysis"], workflow["out_of_tree_code_analysis"]],
         "next_action": "Bind immutable external execution inventory to analysed bytes or verified noninterference"},
    ]
    if spawns:
        out["blockers"].append({"code": "DESCENDANT_EXECUTION_UNCOVERED", "decision": "PIW-D003",
                                "next_action": "Close descendant module provenance; spawn records alone are insufficient"})
    return out


def _unique_object(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("Duplicate JSON key")
        out[key] = value
    return out


def _reject_constant(value):
    raise ValueError("Nonfinite JSON constant")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--result-sha256", required=True)
    args = parser.parse_args(argv)
    try:
        document = json.loads(Path(args.evidence).read_text(encoding="utf-8"),
                              object_pairs_hook=_unique_object, parse_constant=_reject_constant)
        out = assess_coverage(document, args.subject, args.result_sha256)
    except (OSError, ValueError, RecursionError) as exc:
        out = _result()
        out["errors"].append(str(exc))
    print(json.dumps(out, sort_keys=True, ensure_ascii=True))
    return 1 if out["status"] == "COVERAGE_BLOCKED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
