"""Immutable offline M1 generations, using RawDatasetStore only while staging.

A single same-filesystem directory rename publishes the whole generation.
Local POSIX flock serializes writers; readers verify committed files and rerun
the strict audit. No mutable latest pointer, network transport, or replay hook.
"""
from __future__ import annotations

import fcntl
import os
import tempfile
from datetime import datetime
from pathlib import Path

from ..providers.sec_m1_strict import (MAX_INPUT_BYTES, TARGET_US17, M1Artifact, M1Audit, M1Error, M1ObservationReceipt,
    M1Request, SHA_RE, VERSION, audit_sec_m1, aware_datetime, canonical_json, canonical_source_url, sha256, strict_json)
from .raw_store import RawDatasetStore

RECEIPT_SCHEMA = "SEC_M1_RECEIPT/1"
COMMIT_SCHEMA = "SEC_M1_COMMIT/1"
MAX_RECEIPT_BYTES = 128 * 1024 * 1024


def validate_runtime_path(value: Path | str) -> Path:
    """Reject symlinks, traversal, Pages paths, and both forms of Git checkout."""
    path = Path(value)
    if not path.is_absolute() or ".." in path.parts or any(p.lower() in {"pages", "gh-pages", "public"} for p in path.parts):
        raise M1Error("UNSAFE_RUNTIME_PATH")
    for parent in (path, *path.parents):
        if parent.is_symlink() or (parent / ".git").exists() or (parent / ".git").is_symlink():
            raise M1Error("UNSAFE_RUNTIME_PATH")
        # Filename existence only: never inspect a public data/price body.
        if (parent / "index.html").exists() and (parent / "data.json").exists():
            raise M1Error("UNSAFE_RUNTIME_PATH")
        if parent.exists() and not parent.is_dir():
            raise M1Error("UNSAFE_RUNTIME_PATH")
    return path


def _safe_tree(directory):
    if directory.is_symlink():
        raise M1Error("UNSAFE_RUNTIME_PATH")
    if directory.exists():
        for path in directory.rglob("*"):
            if path.name == ".git" or path.is_symlink() or (not path.is_file() and not path.is_dir()):
                raise M1Error("UNSAFE_RUNTIME_PATH")


def _file(path, *, max_bytes=MAX_RECEIPT_BYTES):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > max_bytes:
        raise M1Error("GENERATION_INTEGRITY_FAILED")
    return path.read_bytes()


def _expected_entry(role, issuer_id, cik, input_kind, source_url, digest, size, http_status):
    # All untrusted semantic fields are checked before they can form a path.
    if (any(not isinstance(v, str) for v in (role, issuer_id, cik, input_kind, source_url, digest))
            or role not in {"INPUT", "OBSERVATION"} or input_kind not in {"SEC_SUBMISSIONS", "SEC_COMPANYFACTS"}
            or len(cik) != 10 or not cik.isascii() or not cik.isdigit() or not SHA_RE.fullmatch(digest)
            or type(size) is not int or not 0 < size <= MAX_INPUT_BYTES
            or (http_status is not None and (type(http_status) is not int or http_status != 200))):
        raise M1Error("GENERATION_INTEGRITY_FAILED")
    identity = next((i for i in TARGET_US17 if i.company_id == issuer_id), None)
    if identity is None or cik != identity.cik or source_url != canonical_source_url(input_kind, cik):
        raise M1Error("GENERATION_INTEGRITY_FAILED")
    artifact_id = (f"sec_m1_{input_kind.lower()}_{cik}_{digest}" if role == "INPUT"
                   else "sec_m1_observation_" + digest)
    if Path(artifact_id).name != artifact_id:
        raise M1Error("GENERATION_INTEGRITY_FAILED")
    return {"artifact_id": artifact_id, "role": role, "issuer_id": issuer_id, "cik": cik,
            "input_kind": input_kind, "source_url": source_url, "sha256": digest, "bytes": size,
            "source_kind": input_kind if role == "INPUT" else "SEC_OBSERVATION_RECEIPT",
            "http_status": http_status}


def _write_raw(store, entry, body):
    store.put(entry["artifact_id"], body, entry["source_url"], entry["source_kind"],
              "application/json", VERSION, entry["http_status"], "offline manual import")
    raw_manifest = (store.root / "manifests" / (entry["artifact_id"] + ".json")).read_bytes()
    return dict(entry, manifest_sha256=sha256(raw_manifest), manifest_bytes=len(raw_manifest))


def _sync_tree(directory):
    for path in directory.rglob("*"):
        if path.is_file():
            with path.open("rb") as stream:
                os.fsync(stream.fileno())
    directories = [p for p in directory.rglob("*") if p.is_dir()]
    for path in sorted(directories, key=lambda p: len(p.parts), reverse=True) + [directory]:
        _sync_directory(path)


def _sync_directory(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _make_runtime_root(root):
    missing, ancestor = [], root
    while not ancestor.exists():
        missing.append(ancestor)
        ancestor = ancestor.parent
    for directory in reversed(missing):
        directory.mkdir(mode=0o700, exist_ok=True)
        validate_runtime_path(directory)
        _sync_directory(directory.parent)


def _promote_generation(staging, destination):
    # Writers hold the common root lock; never replace an existing generation.
    if destination.exists() or destination.is_symlink():
        raise M1Error("GENERATION_CONFLICT")
    os.rename(staging, destination)
    _sync_directory(destination.parent)


def _verify_generation(directory, generation_id):
    validate_runtime_path(directory)
    _safe_tree(directory)
    marker_body = _file(directory / "COMMITTED.json", max_bytes=4096)
    marker = strict_json(marker_body, max_bytes=4096)
    if set(marker) != {"schema", "generation_id", "receipt_sha256", "receipt_bytes"} or marker["schema"] != COMMIT_SCHEMA:
        raise M1Error("GENERATION_INTEGRITY_FAILED")
    body = _file(directory / "receipt.json")
    if (marker["generation_id"] != generation_id or marker["receipt_sha256"] != sha256(body)
            or type(marker["receipt_bytes"]) is not int or marker["receipt_bytes"] != len(body)):
        raise M1Error("GENERATION_INTEGRITY_FAILED")
    receipt = strict_json(body, max_bytes=MAX_RECEIPT_BYTES)
    if set(receipt) != {"schema", "generation_id", "semantic_binding", "result_sha256", "evaluated_at",
                         "imported_at", "raw_entries"} or receipt["schema"] != RECEIPT_SCHEMA:
        raise M1Error("GENERATION_INTEGRITY_FAILED")
    binding = receipt["semantic_binding"]
    if (receipt["generation_id"] != generation_id or sha256(canonical_json(binding)) != generation_id
            or receipt["result_sha256"] != sha256(canonical_json(binding["result"]))):
        raise M1Error("GENERATION_INTEGRITY_FAILED")
    entries = receipt["raw_entries"]
    if not isinstance(entries, list) or not 2 <= len(entries) <= 12:
        raise M1Error("GENERATION_INTEGRITY_FAILED")
    expected_inputs = {(a["issuer_id"], a["source_kind"]): a for a in binding["artifacts"]}
    expected_proofs = {p["sha256"]: p for p in binding["observation_receipts"]}
    if len(expected_inputs) != len(binding["artifacts"]) or len(expected_proofs) != len(binding["observation_receipts"]):
        raise M1Error("GENERATION_INTEGRITY_FAILED")
    artifacts, proofs, expected_files, seen = [], [], {"receipt.json", "COMMITTED.json"}, set()
    entry_fields = {"artifact_id", "role", "issuer_id", "cik", "input_kind", "source_url", "sha256", "bytes",
                    "source_kind", "http_status", "manifest_sha256", "manifest_bytes"}
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != entry_fields:
            raise M1Error("GENERATION_INTEGRITY_FAILED")
        digest = entry["sha256"]
        if not isinstance(digest, str) or not SHA_RE.fullmatch(digest):
            raise M1Error("GENERATION_INTEGRITY_FAILED")
        if entry["role"] == "INPUT":
            spec = expected_inputs.get((entry["issuer_id"], entry["input_kind"]))
            if spec is None:
                raise M1Error("GENERATION_INTEGRITY_FAILED")
            expected = _expected_entry("INPUT", spec["issuer_id"], spec["cik"], spec["source_kind"],
                                       spec["source_url"], spec["sha256"], spec["bytes"], entry["http_status"])
        elif entry["role"] == "OBSERVATION":
            spec = expected_proofs.get(digest)
            if spec is None or entry["bytes"] != spec["bytes"]:
                raise M1Error("GENERATION_INTEGRITY_FAILED")
            expected = _expected_entry("OBSERVATION", entry["issuer_id"], entry["cik"], entry["input_kind"],
                                       entry["source_url"], digest, spec["bytes"], None)
        else:
            raise M1Error("GENERATION_INTEGRITY_FAILED")
        if any(entry[k] != v for k, v in expected.items()) or expected["artifact_id"] in seen:
            raise M1Error("GENERATION_INTEGRITY_FAILED")
        artifact_id = expected["artifact_id"]
        seen.add(artifact_id)
        blob_path = directory / "raw" / "blobs" / artifact_id
        manifest_path = directory / "raw" / "manifests" / (artifact_id + ".json")
        expected_files.update({str(blob_path.relative_to(directory)), str(manifest_path.relative_to(directory))})
        raw_body = _file(blob_path)
        manifest_body = _file(manifest_path, max_bytes=16_384)
        if (sha256(raw_body) != digest or type(entry["bytes"]) is not int or len(raw_body) != entry["bytes"]
                or sha256(manifest_body) != entry["manifest_sha256"] or len(manifest_body) != entry["manifest_bytes"]):
            raise M1Error("GENERATION_INTEGRITY_FAILED")
        manifest = strict_json(manifest_body, max_bytes=16_384)
        expected_manifest = {"artifact_id": artifact_id, "source_url": entry["source_url"],
                             "source_kind": entry["source_kind"], "sha256": digest, "bytes": len(raw_body),
                             "content_type": "application/json", "fetcher": VERSION,
                             "http_status": entry["http_status"], "notes": "offline manual import"}
        if set(manifest) != set(expected_manifest) | {"fetched_at"} or any(manifest[k] != v for k, v in expected_manifest.items()):
            raise M1Error("GENERATION_INTEGRITY_FAILED")
        aware_datetime(manifest["fetched_at"])
        if entry["role"] == "INPUT":
            artifacts.append(M1Artifact(entry["issuer_id"], entry["cik"], entry["input_kind"], entry["source_url"],
                                         raw_body, digest, len(raw_body)))
        else:
            proof_payload = strict_json(raw_body, max_bytes=16_384)
            if any(entry[k] != proof_payload[p] for k, p in (("issuer_id", "issuer_id"), ("cik", "cik"),
                           ("input_kind", "source_kind"), ("source_url", "source_url"))):
                raise M1Error("GENERATION_INTEGRITY_FAILED")
            proofs.append(M1ObservationReceipt(raw_body, digest, len(raw_body)))
    files = {str(p.relative_to(directory)) for p in directory.rglob("*") if p.is_file()}
    directories = {str(p.relative_to(directory)) for p in directory.rglob("*") if p.is_dir()}
    if files != expected_files or directories != {"raw", "raw/blobs", "raw/manifests", "raw/history"}:
        raise M1Error("GENERATION_INTEGRITY_FAILED")
    spec = binding["request"]
    evaluated = aware_datetime(receipt["evaluated_at"])
    imported = aware_datetime(receipt["imported_at"])
    if imported < evaluated:
        raise M1Error("IMPORT_BEFORE_EVALUATION")
    recomputed = audit_sec_m1(M1Request(tuple(spec["issuer_ids"]), aware_datetime(spec["as_of"]), evaluated,
                                       spec["synthetic"]), tuple(artifacts), tuple(proofs))
    if recomputed.semantic_dict() != binding or recomputed.semantic_sha256 != generation_id:
        raise M1Error("GENERATION_INTEGRITY_FAILED")
    proved = {(strict_json(p.body)["issuer_id"], strict_json(p.body)["source_kind"]) for p in proofs}
    for entry in entries:
        expected_status = 200 if entry["role"] == "INPUT" and (entry["issuer_id"], entry["input_kind"]) in proved else None
        if entry["http_status"] != expected_status:
            raise M1Error("GENERATION_INTEGRITY_FAILED")
    return receipt


def read_m1_generation(output_root: Path | str, generation_id: str) -> dict:
    try:
        root = validate_runtime_path(output_root)
        if not isinstance(generation_id, str) or not SHA_RE.fullmatch(generation_id):
            raise M1Error("INVALID_GENERATION_ID")
        if (root / "generations").is_symlink():
            raise M1Error("UNSAFE_RUNTIME_PATH")
        return _verify_generation(root / "generations" / generation_id, generation_id)
    except M1Error:
        raise
    except (OSError, KeyError, TypeError, ValueError, RecursionError):
        raise M1Error("GENERATION_INTEGRITY_FAILED") from None


def list_m1_generations(output_root: Path | str) -> tuple[str, ...]:
    try:
        root = validate_runtime_path(output_root)
        parent = root / "generations"
        if parent.is_symlink():
            raise M1Error("UNSAFE_RUNTIME_PATH")
        if not parent.exists():
            return ()
        result = []
        for directory in sorted(parent.iterdir()):
            if directory.is_symlink() or not directory.is_dir() or not SHA_RE.fullmatch(directory.name):
                raise M1Error("GENERATION_INTEGRITY_FAILED")
            read_m1_generation(root, directory.name)
            result.append(directory.name)
        return tuple(result)
    except M1Error:
        raise
    except OSError:
        raise M1Error("GENERATION_INTEGRITY_FAILED") from None


def persist_m1_generation(audit: M1Audit, *, output_root: Path | str, imported_at: datetime) -> dict:
    """Revalidate before writes; retries return the original verified receipt."""
    try:
        if not isinstance(audit, M1Audit):
            raise M1Error("INVALID_AUDIT")
        validated = audit_sec_m1(audit.request, audit.artifacts, audit.observation_receipts)
        if audit != validated:
            raise M1Error("AUDIT_BINDING_MISMATCH")
        imported = aware_datetime(imported_at)
        if imported < validated.request.now:
            raise M1Error("IMPORT_BEFORE_EVALUATION")
        root = validate_runtime_path(output_root)
        for name in ("generations", ".staging"):
            _safe_tree(root / name)
        if (root / ".writer.lock").is_symlink():
            raise M1Error("UNSAFE_RUNTIME_PATH")
        generation_id = validated.semantic_sha256
        _make_runtime_root(root)
        descriptor = os.open(root / ".writer.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            # Repeat path checks after serializing writers.
            validate_runtime_path(root)
            for name in ("generations", ".staging"):
                _safe_tree(root / name)
                (root / name).mkdir(mode=0o700, exist_ok=True)
            _sync_directory(root)
            destination = root / "generations" / generation_id
            if destination.exists() or destination.is_symlink():
                previous = read_m1_generation(root, generation_id)
                if previous["semantic_binding"] != validated.semantic_dict():
                    raise M1Error("GENERATION_CONFLICT")
                _sync_directory(destination.parent)
                return previous
            staging = Path(tempfile.mkdtemp(prefix="generation-", dir=root / ".staging"))
            validate_runtime_path(staging)
            _sync_directory(staging.parent)
            raw_store = RawDatasetStore(staging / "raw")
            entries, proved = [], {}
            for proof in validated.observation_receipts:
                payload = strict_json(proof.body, max_bytes=16_384)
                proved[payload["issuer_id"], payload["source_kind"]] = True
            for artifact in validated.artifacts:
                entry = _expected_entry("INPUT", artifact.issuer_id, artifact.cik, artifact.source_kind,
                    artifact.source_url, artifact.expected_sha256, artifact.expected_bytes,
                    200 if (artifact.issuer_id, artifact.source_kind) in proved else None)
                entries.append(_write_raw(raw_store, entry, artifact.body))
            for proof in validated.observation_receipts:
                payload = strict_json(proof.body, max_bytes=16_384)
                entry = _expected_entry("OBSERVATION", payload["issuer_id"], payload["cik"], payload["source_kind"],
                                        payload["source_url"], proof.expected_sha256, proof.expected_bytes, None)
                entries.append(_write_raw(raw_store, entry, proof.body))
            receipt = {"schema": RECEIPT_SCHEMA, "generation_id": generation_id,
                       "semantic_binding": validated.semantic_dict(), "result_sha256": sha256(canonical_json(validated.to_dict())),
                       "evaluated_at": validated.request.now.isoformat(), "imported_at": imported.isoformat(),
                       "raw_entries": sorted(entries, key=lambda e: e["artifact_id"])}
            receipt_body = canonical_json(receipt)
            (staging / "receipt.json").write_bytes(receipt_body)
            marker = {"schema": COMMIT_SCHEMA, "generation_id": generation_id,
                      "receipt_sha256": sha256(receipt_body), "receipt_bytes": len(receipt_body)}
            (staging / "COMMITTED.json").write_bytes(canonical_json(marker))
            verified = _verify_generation(staging, generation_id)
            _sync_tree(staging)
            validate_runtime_path(staging)
            _promote_generation(staging, destination)
            return verified
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)
    except M1Error:
        raise
    except (OSError, KeyError, TypeError, ValueError, RecursionError, OverflowError):
        raise M1Error("PERSISTENCE_FAILED") from None
