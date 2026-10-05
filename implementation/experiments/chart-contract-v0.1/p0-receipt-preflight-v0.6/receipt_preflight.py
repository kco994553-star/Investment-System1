#!/usr/bin/env python3
"""Inspect a returned v0.5 Target packet offline; never admit or publish it.

This tool checks an existing request, not a new production receipt schema.
Owner strings are untrusted claims. Actual receipt authentication, subject hash
preimage, Product applicability and owner acceptance remain separate gates.
"""
from __future__ import annotations

import argparse
from datetime import datetime
from decimal import Decimal, InvalidOperation
from fractions import Fraction
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess

SOURCE_COMMIT = "a89ac6dd4336027ddab52b145ab87e3bc5edb3e5"
REQUEST_PATH = ("implementation/experiments/chart-contract-v0.1/"
                "p0-slice-owner-closure-v0.5/lane-a/TARGET_OWNER_ADMISSION_REQUEST.json")
GATES = ["A-S1", "A-S2", "A-S3", "A-G1", "A-G2", "A-G3"]


def strict_json(raw: str | bytes) -> dict:
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError(f"duplicate JSON key: {key}")
            out[key] = value
        return out

    def constant(value):
        raise ValueError(f"nonfinite JSON constant: {value}")

    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


def git_bytes(repo: Path, commit: str, path: str) -> bytes:
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("source commit must be an exact 40-hex SHA")
    if (not isinstance(path, str) or not path or PurePosixPath(path).is_absolute()
            or ".." in PurePosixPath(path).parts or "\x00" in path):
        raise ValueError("unsafe source path")
    return subprocess.check_output(["git", "-C", str(repo), "show", f"{commit}:{path}"],
                                   stderr=subprocess.DEVNULL)


def json_bytes(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def aware(value) -> datetime:
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("explicit timezone-aware time required")
    return value


def exact_decimal(value) -> Fraction:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError("weight must be a lexical Decimal string")
    number = Decimal(value)
    if not number.is_finite() or number < 0:
        raise ValueError("weight must be finite and nonnegative")
    return Fraction(number)


def inspect_packet(packet, baseline, repo, decision_time) -> dict:
    """Return diagnostics, including six OPEN gates even for complete claims."""
    findings = []
    report = {
        "scope": "OFFLINE_OWNER_RETURN_DIAGNOSTIC_NOT_A_PRODUCTION_CONTRACT",
        "production_readiness": "IMPLEMENTATION_NOT_READY",
        "open_gate_ids": GATES.copy(), "open_count": 6, "closed_count": 0,
        "source_inspection": "INCOMPLETE", "findings": findings,
        "owner_receipts_authentication": "NOT_PERFORMED_NO_ADOPTED_RECEIPT_ROUTE",
        "claimed_snapshot_hash_verification": "NOT_RUN_ADOPTED_PREIMAGE_MISSING",
        "owner_action_required": GATES.copy(),
        "actual": {"status": "NOT_AVAILABLE", "root": None, "fallback_to_target": False},
        "production_payload": None, "reference_diagnostic": None,
        "production_L5": "NOT_RUN", "chart_merge_result_fpia": "NOT_RUN",
        "qgv_dependency": "INACTIVE_SPEC_ONLY",
    }

    def issue(code, path, message, severity="ERROR"):
        findings.append({"code": code, "path": path, "message": message,
                         "severity": severity})

    def finish():
        levels = {x["severity"] for x in findings}
        report["source_inspection"] = ("INVALID" if "ERROR" in levels else
                                      "INCOMPLETE" if "MISSING" in levels else
                                      "INPUT_COMPLETE_UNAUTHENTICATED")
        return report

    try:
        clock = aware(decision_time)
        report["decision_time"] = clock.isoformat()
    except (ValueError, TypeError, OverflowError) as exc:
        issue("INVALID_DECISION_TIME", "/decision_time", str(exc))
        return finish()
    if not isinstance(packet, dict) or not isinstance(baseline, dict):
        issue("INVALID_PACKET", "/", "packet and pinned baseline must be objects")
        return finish()

    # Compare every immutable field, including typed values, with the trusted
    # original request. Only existing owner_return slots may be filled.
    try:
        left = {k: v for k, v in packet.items() if k not in {"root_owner_return", "constituents"}}
        right = {k: v for k, v in baseline.items() if k not in {"root_owner_return", "constituents"}}
        if json_bytes(left) != json_bytes(right):
            issue("REQUEST_METADATA_CHANGED", "/", "preserved request metadata differs")
    except (TypeError, ValueError, OverflowError) as exc:
        issue("INVALID_JSON_VALUE", "/", str(exc))

    rows = packet.get("constituents")
    original = baseline.get("constituents")
    if not isinstance(rows, list) or not isinstance(original, list):
        issue("INVALID_ROWS", "/constituents", "complete source row list required")
        return finish()
    expected = {r["source_row_key"]: r for r in original}
    seen = set()
    if len(rows) != len(original):
        issue("ROW_COMPLETENESS", "/constituents", "row count differs from pinned request")
    for i, row in enumerate(rows):
        path = f"/constituents/{i}"
        if not isinstance(row, dict):
            issue("INVALID_ROW", path, "source row must be an object")
            continue
        key = row.get("source_row_key")
        if not isinstance(key, str) or key not in expected:
            issue("UNKNOWN_ROW", path, "row key is absent from original request")
            continue
        if key in seen:
            issue("DUPLICATE_ROW", path, "source row must occur exactly once")
        seen.add(key)
        preserved = {k: v for k, v in row.items() if k != "owner_return"}
        source = {k: v for k, v in expected[key].items() if k != "owner_return"}
        try:
            if json_bytes(preserved) != json_bytes(source):
                issue("IMMUTABLE_ROW_CHANGED", path, "observed source/provenance must not be rewritten")
        except (TypeError, ValueError, OverflowError) as exc:
            issue("INVALID_JSON_VALUE", path, str(exc))
    if seen != set(expected):
        issue("ROW_COMPLETENESS", "/constituents", "missing original source row keys")

    # Verify original immutable source objects, not candidate self-declarations.
    pins = {}
    for row in original:
        for pin in row["source_refs"]:
            key = (pin["commit"], pin["path"])
            if key in pins:
                if pins[key] != (pin["git_blob"], pin["sha256"]):
                    issue("CONFLICTING_SOURCE_PIN", "/source_refs", "original pins disagree")
                continue
            pins[key] = (pin["git_blob"], pin["sha256"])
            try:
                raw = git_bytes(Path(repo), *key)
                blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
                if (hashlib.sha256(raw).hexdigest() != pin["sha256"] or blob != pin["git_blob"]):
                    issue("SOURCE_HASH_MISMATCH", pin["path"], "exact Git source bytes differ")
            except (ValueError, OSError, subprocess.CalledProcessError) as exc:
                issue("SOURCE_PIN_UNRESOLVED", pin["path"], str(exc))
    report["source_objects_checked"] = len(pins)

    # Exact rational replay is diagnostic only. It is not the domain calculator
    # and does not choose a production Decimal context or rounding policy.
    try:
        if any(x["severity"] == "ERROR" for x in findings):
            raise ValueError("immutable source checks failed; untrusted allocation is not evaluated")
        totals = {}
        total = Fraction(0)
        for row in original:
            weight = row["observed_target_weight"]
            ratio = exact_decimal(weight["decimal_ratio"])
            percent = exact_decimal(weight["percent"])
            if not isinstance(weight["exact_fraction"], str):
                raise ValueError("exact fraction must be a string")
            if ratio > 1 or ratio * 100 != percent or ratio != Fraction(weight["exact_fraction"]):
                raise ValueError("ratio, percent and exact fraction disagree")
            theme = row["observed_theme_name"]
            totals[theme] = totals.get(theme, Fraction(0)) + ratio
            total += ratio
        allocation = baseline["observed_candidate_allocation"]
        cash = exact_decimal(allocation["cash_target_percent"]) / 100
        expected_totals = {name: exact_decimal(n) / 100
                           for name, n in allocation["reference_theme_total_percent"].items()}
        if total + cash != 1 or totals != expected_totals:
            raise ValueError("exact total/Theme partition differs from original request")
        report["reference_diagnostic"] = {
            "weight_basis": "TARGET_AUTHORED_REFERENCE_ONLY",
            "constituent_count": len(rows), "total_exact_fraction": str(total + cash),
            "theme_total_exact_fraction": {k: str(v) for k, v in totals.items()},
            "is_renderable_production_data": False,
        }
    except (ValueError, InvalidOperation, ZeroDivisionError, KeyError, TypeError, OverflowError) as exc:
        issue("INVALID_REFERENCE_ALLOCATION", "/constituents", str(exc))

    def owner_fields(value, template, path):
        if not isinstance(value, dict):
            issue("OWNER_FIELDS_MISSING" if value is None else "INVALID_OWNER_OBJECT", path,
                  "existing owner slots must be an object", "MISSING" if value is None else "ERROR")
            return {}
        if set(value) != set(template):
            issue("OWNER_FIELD_SET_CHANGED", path, "only existing v0.5 slots are inspected")
        for key in template:
            if key == "effective_to":
                if key not in value:
                    issue("OPEN_END_UNSPECIFIED", path + "/" + key,
                          "use explicit null for an open-ended interval", "MISSING")
                elif value[key] is not None and (not isinstance(value[key], str) or not value[key].strip()):
                    issue("INVALID_OWNER_FIELD", path + "/" + key, "end must be explicit null or an aware time string")
                continue
            item = value.get(key)
            if item is None or isinstance(item, str) and not item.strip():
                issue("OWNER_FIELD_MISSING", path + "/" + key,
                      "owner receipt not returned", "MISSING")
            elif not isinstance(item, str) or not item.strip() or item != item.strip():
                issue("INVALID_OWNER_FIELD", path + "/" + key, "nonempty exact string required")
        return value

    def interval(value, path):
        try:
            start = aware(value["effective_from"]) if value.get("effective_from") else None
            end = aware(value["effective_to"]) if value.get("effective_to") else None
            available = aware(value["available_at"]) if value.get("available_at") else None
            if (start and start > clock) or (end and clock >= end) or (start and end and start >= end):
                raise ValueError("half-open effective interval does not contain decision time")
            if available and available > clock:
                raise ValueError("available_at is after explicit decision time")
            return start, end
        except (ValueError, TypeError, OverflowError) as exc:
            issue("INVALID_OWNER_TIME", path, str(exc))
            return None, None

    root = owner_fields(packet.get("root_owner_return"), baseline["root_owner_return"], "/root_owner_return")
    root_interval = interval(root, "/root_owner_return")
    snapshot = root.get("snapshot_hash")
    if snapshot and (not isinstance(snapshot, str) or not re.fullmatch(r"[0-9a-f]{64}", snapshot)):
        issue("INVALID_SNAPSHOT_HASH", "/root_owner_return/snapshot_hash", "64-hex claimed hash required")
    security_keys, row_ids, catalog_keys, assignments = set(), set(), set(), set()
    concept_to_theme, theme_to_concept = {}, {}
    for i, row in enumerate(rows):
        if (not isinstance(row, dict) or not isinstance(row.get("source_row_key"), str)
                or row.get("source_row_key") not in expected):
            continue
        path = f"/constituents/{i}/owner_return"
        value = owner_fields(row.get("owner_return"), expected[row["source_row_key"]]["owner_return"], path)
        window = interval(value, path)
        if (root_interval[0] and window[0] and
                (window[0] > root_interval[0] or
                 window[1] and (root_interval[1] is None or window[1] < root_interval[1]))):
            issue("ASSIGNMENT_INTERVAL_INCOMPLETE", path, "assignment does not cover claimed root interval")
        for key, keys in [("admitted_target_row_id", row_ids)]:
            item = value.get(key)
            if isinstance(item, str) and item:
                if item in keys:
                    issue("DUPLICATE_ADMITTED_ROW", path + "/" + key, "admitted row id is not unique")
                keys.add(item)
        security = (value.get("security_namespace"), value.get("security_id"))
        if all(isinstance(x, str) and x for x in security):
            if security in security_keys:
                issue("DUPLICATE_SECURITY", path, "security pair must bind one source row")
            security_keys.add(security)
        catalog = tuple(value.get(k) for k in ["taxonomy_id", "taxonomy_version", "catalog_revision_id"])
        if all(isinstance(x, str) and x for x in catalog):
            catalog_keys.add(catalog)
        revision = value.get("assignment_revision_id")
        if isinstance(revision, str) and revision:
            assignments.add(revision)
        concept, theme = value.get("theme_concept_id"), row.get("observed_theme_name")
        if isinstance(concept, str) and concept and isinstance(theme, str):
            if (concept in concept_to_theme and concept_to_theme[concept] != theme
                    or theme in theme_to_concept and theme_to_concept[theme] != concept):
                issue("THEME_JOIN_CONFLICT", path, "Theme names and concepts do not form one partition")
            concept_to_theme[concept] = theme
            theme_to_concept[theme] = concept
    if len(catalog_keys) > 1:
        issue("CATALOG_REVISION_CONFLICT", "/constituents", "one exact Theme catalog required for this request")
    if len(assignments) > 1:
        issue("ASSIGNMENT_REVISION_CONFLICT", "/constituents", "one complete assignment revision required")
    issue("OWNER_RECEIPTS_UNAUTHENTICATED", "/owner_return",
          "Filled claims cannot authenticate adopted roots, identities, Theme or current authority. "
          "A-G1/A-G2/A-G3 remain separate owner prerequisites.", "WARNING")
    if any(x["severity"] == "ERROR" for x in findings):
        report["reference_diagnostic"] = None
    return finish()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--decision-time", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        original = git_bytes(args.repo, SOURCE_COMMIT, REQUEST_PATH)
        baseline = strict_json(original)
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        result = inspect_packet(None, {}, args.repo, args.decision_time)
        result["findings"].append({"code": "PINNED_BASELINE_UNAVAILABLE", "path": REQUEST_PATH,
                                   "severity": "ERROR", "message": str(exc)})
        result["pinned_request"] = {"commit": SOURCE_COMMIT, "path": REQUEST_PATH,
                                    "sha256": None, "status": "UNRESOLVED_NO_FALLBACK"}
    else:
        try:
            candidate_bytes = args.packet.read_bytes()
            packet = strict_json(candidate_bytes)
        except (ValueError, OSError) as exc:
            result = inspect_packet(None, baseline, args.repo, args.decision_time)
            result["findings"].append({"code": "PACKET_READ_FAILED", "path": str(args.packet),
                                       "severity": "ERROR", "message": str(exc)})
        else:
            result = inspect_packet(packet, baseline, args.repo, args.decision_time)
            result["inspected_packet_sha256"] = hashlib.sha256(candidate_bytes).hexdigest()
        result["pinned_request"] = {"commit": SOURCE_COMMIT, "path": REQUEST_PATH,
                                    "sha256": hashlib.sha256(original).hexdigest()}
    raw = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if args.output:
        # Never overwrite an input, prior audit, evidence or source file.
        with args.output.open("x", encoding="utf-8") as handle:
            handle.write(raw)
    print(raw, end="")
    return 2 if result["source_inspection"] == "INVALID" else 3 if result["source_inspection"] == "INCOMPLETE" else 0


if __name__ == "__main__":
    raise SystemExit(main())
