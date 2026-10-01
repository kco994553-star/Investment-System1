"""QGV exporter: validate → persist → serialize. Nothing else.

It does not call the engine, rescore, normalize or re-rank. Records are written exactly as given (canonical
JSON, one record per line, sorted by company_id). Every file is written to a temp file, fsynced, then moved
into place with os.replace, so a failed export leaves the previous files untouched.

Layout under <out_dir>:
  qgv_company_snapshots_<as_of>.jsonl   one QGV_COMPANY_RESULT v1 per line (PASS, FAIL and NOT_RUN alike)
  qgv_batch_manifest_<as_of>.json       QGV_PRODUCER_BATCH_MANIFEST v1 (+ operational.files sha256)
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .batch import MANIFEST_KIND, MANIFEST_VERSION
from .record import STATUSES, QGVProducerError, canonical_bytes, canonical_sha256, sha256_hex, validate_record


def _date(as_of: str) -> str:
    return as_of[:10]


def snapshots_name(as_of: str) -> str:
    return f"qgv_company_snapshots_{_date(as_of)}.jsonl"


def manifest_name(as_of: str) -> str:
    return f"qgv_batch_manifest_{_date(as_of)}.json"


def validate_manifest(manifest: Any, records: list[dict]) -> dict:
    if not isinstance(manifest, dict) or manifest.get("manifest_kind") != MANIFEST_KIND \
            or manifest.get("manifest_version") != MANIFEST_VERSION:
        raise QGVProducerError("SCHEMA", f"manifest must be {MANIFEST_KIND} v{MANIFEST_VERSION}")
    sem = manifest["semantic"]
    if manifest.get("semantic_sha256") != canonical_sha256(sem):
        raise QGVProducerError("SEMANTIC_HASH", "manifest semantic_sha256 does not match")
    rows = [{"company_id": r["semantic"]["company_id"], "status": r["semantic"]["status"],
             "status_reasons": r["semantic"]["status_reasons"], "semantic_sha256": r["semantic_sha256"]} for r in records]
    if rows != sem["records"] or canonical_sha256(rows) != sem["records_sha256"]:
        raise QGVProducerError("MANIFEST_MISMATCH", "manifest rows differ from the records")
    ids = [r["company_id"] for r in rows]
    if ids != sorted(set(ids)):
        raise QGVProducerError("IDENTITY", "records must be unique and sorted by company_id")
    counts = {s: sum(1 for r in rows if r["status"] == s) for s in STATUSES}
    if counts != sem["counts"] or sum(counts.values()) != sem["persisted_count"]:
        raise QGVProducerError("MANIFEST_MISMATCH", "status counts do not add up")
    if sem["persisted_count"] != sem["expected_count"]:
        raise QGVProducerError("PARTIAL_BATCH_HIDDEN", f"expected {sem['expected_count']} records, have {sem['persisted_count']}")
    if sem["complete"] != (counts["PASS"] == sem["expected_count"]):
        raise QGVProducerError("MANIFEST_MISMATCH", "complete flag inconsistent with PASS count")
    for r in records:
        if r["semantic"]["as_of"] != sem["as_of"] or r["semantic"]["universe"]["universe_id"] != sem["universe"]["universe_id"]:
            raise QGVProducerError("IDENTITY", f"{r['semantic']['company_id']}: as_of/universe differ from the manifest")
    return manifest


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def serialize_records(records: list[dict]) -> bytes:
    return b"".join(canonical_bytes(r) + b"\n" for r in records)


def export_batch(records: list[dict], manifest: dict, out_dir: Path | str, *, require_real: bool = True) -> dict:
    """Validate every record and the manifest, then write both files. Returns the written manifest."""
    for r in records:
        validate_record(r, require_real=require_real)
    validate_manifest(manifest, records)
    out = Path(out_dir)
    body = serialize_records(records)
    as_of = manifest["semantic"]["as_of"]
    written = dict(manifest)
    written["operational"] = {**manifest["operational"],
                              "files": {snapshots_name(as_of): {"sha256": sha256_hex(body), "bytes": len(body)}}}
    _atomic_write(out / snapshots_name(as_of), body)
    _atomic_write(out / manifest_name(as_of), (json.dumps(written, indent=1, sort_keys=True, ensure_ascii=False) + "\n").encode())
    return written


def load_export(out_dir: Path | str, as_of: str, *, require_real: bool = True) -> tuple[list[dict], dict]:
    """Read back and re-validate: file sha256, every record hash, manifest rows and counts."""
    out = Path(out_dir)
    manifest = json.loads((out / manifest_name(as_of)).read_text(encoding="utf-8"))
    body = (out / snapshots_name(as_of)).read_bytes()
    f = (manifest.get("operational") or {}).get("files", {}).get(snapshots_name(as_of))
    if not f or f.get("sha256") != sha256_hex(body):
        raise QGVProducerError("SOURCE_HASH", "snapshot file sha256 does not match the manifest")
    records = [json.loads(line) for line in body.decode("utf-8").splitlines() if line]
    for r in records:
        validate_record(r, require_real=require_real)
    validate_manifest(manifest, records)
    return records, manifest
