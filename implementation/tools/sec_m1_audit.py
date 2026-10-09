"""Explicit offline SEC M1 import. No network option or automatic issuer subset."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from investment_system.ingestion.sec_m1_receipts import persist_m1_generation, validate_runtime_path
from investment_system.providers.sec_m1_strict import (MAX_INPUT_BYTES, M1Artifact, M1Error,
    M1ObservationReceipt, M1Request, audit_sec_m1, aware_datetime, load_target_identities, strict_json,
    validate_expected_binding, validate_m1_input_bindings, validate_m1_request)


class _SafeParser(argparse.ArgumentParser):
    def error(self, _message):
        raise M1Error("CLI_ARGUMENTS")


def _read_file(path, *, max_bytes=MAX_INPUT_BYTES):
    path = Path(path)
    validate_runtime_path(path.parent)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > max_bytes:
        raise M1Error("UNSAFE_INPUT_PATH")
    return path.read_bytes()


def _sibling_path(parent, filename):
    if (not isinstance(filename, str) or not filename or Path(filename).name != filename
            or filename in {".", ".."}):
        raise M1Error("UNSAFE_INPUT_PATH")
    path = parent / filename
    if path.is_symlink():
        raise M1Error("UNSAFE_INPUT_PATH")
    return path


def _manifest(path, as_of, now):
    path = Path(path)
    if not path.is_absolute() or ".." in path.parts:
        raise M1Error("UNSAFE_INPUT_PATH")
    payload = strict_json(_read_file(path, max_bytes=64 * 1024), max_bytes=64 * 1024)
    required = {"schema", "issuer_ids", "synthetic", "artifacts"}
    if (not required.issubset(payload) or set(payload) - required - {"observation_receipts"}
            or payload["schema"] != "SEC_M1_OFFLINE_IMPORT/1"
            or not isinstance(payload["issuer_ids"], list) or type(payload["synthetic"]) is not bool
            or not isinstance(payload["artifacts"], list) or not isinstance(payload.get("observation_receipts", []), list)):
        raise M1Error("INVALID_INPUT_MANIFEST")
    if len(payload["artifacts"]) > 6 or len(payload.get("observation_receipts", [])) > 6:
        raise M1Error("INPUT_ARTIFACT_LIMIT")
    request = validate_m1_request(M1Request(tuple(payload["issuer_ids"]), as_of, now, payload["synthetic"]))
    artifact_fields = {"issuer_id", "cik", "source_kind", "source_url", "path", "sha256", "bytes"}
    artifacts = []
    for item in payload["artifacts"]:
        if not isinstance(item, dict) or set(item) != artifact_fields:
            raise M1Error("INVALID_INPUT_MANIFEST")
        _sibling_path(path.parent, item["path"])
        artifacts.append(M1Artifact(item["issuer_id"], item["cik"], item["source_kind"], item["source_url"],
                                    b"", item["sha256"], item["bytes"]))
    validate_m1_input_bindings(request, tuple(artifacts))
    for item in payload.get("observation_receipts", []):
        if not isinstance(item, dict) or set(item) != {"path", "sha256", "bytes"}:
            raise M1Error("INVALID_INPUT_MANIFEST")
        _sibling_path(path.parent, item["path"])
        validate_expected_binding(item["sha256"], item["bytes"], prefix="OBSERVATION", max_bytes=16_384)
    # All declarations, clocks, identity scope, and basenames passed before any body read.
    artifacts = tuple(replace(artifact, body=_read_file(_sibling_path(path.parent, item["path"])))
                      for artifact, item in zip(artifacts, payload["artifacts"]))
    proofs = tuple(M1ObservationReceipt(_read_file(_sibling_path(path.parent, item["path"]), max_bytes=16_384),
                                        item["sha256"], item["bytes"]) for item in payload.get("observation_receipts", []))
    return request, artifacts, proofs


def main(argv=None) -> int:
    parser = _SafeParser(description="Audit explicitly supplied SEC bytes offline; no fetch or scoring.")
    for flag in ("--input-manifest", "--as-of", "--now", "--output"):
        parser.add_argument(flag, required=True)
    try:
        args = parser.parse_args(argv)
        as_of, now = aware_datetime(args.as_of), aware_datetime(args.now)
        validate_runtime_path(Path(args.output))
        load_target_identities()
        request, artifacts, proofs = _manifest(args.input_manifest, as_of, now)
        result = audit_sec_m1(request, artifacts, proofs)
        receipt = persist_m1_generation(result, output_root=Path(args.output), imported_at=now)
        summary = {"status": "PASS", "generation_id": receipt["generation_id"],
                   "artifact_count": len(result.artifacts), "observation_receipt_count": len(result.observation_receipts),
                   "fact_counts": dict(sorted(Counter(f.status for f in result.facts).items())),
                   "codes": result.counts, "synthetic": result.request.synthetic,
                   "full_pit_pass": False, "real_data_verified": False, "publication_approved": False}
        print(json.dumps(summary, sort_keys=True))
        return 0
    except M1Error as error:
        print(json.dumps({"status": "FAIL", "code": error.code}, sort_keys=True))
        return 2
    except Exception:
        print(json.dumps({"status": "FAIL", "code": "OFFLINE_AUDIT_FAILED"}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
