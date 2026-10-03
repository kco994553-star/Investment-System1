"""Persist Technical company records. Replay reads those bytes only. No network."""

from __future__ import annotations

import json
from pathlib import Path

from .codec import canonical_bytes, semantic_hash
from .errors import TechnicalProducerError

def write_batch(batch: dict, directory: Path | str) -> Path:
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    records = batch.get("records") or []
    files = []
    for record in records:
        name = f"{record['company_id']}.json"
        path = root / name
        path.write_bytes(canonical_bytes(record) + b"\n")
        files.append({"company_id": record["company_id"], "file": name, "semantic_hash": record["semantic_hash"]})
    manifest = {
        "contract": batch["contract"],
        "schema_version": batch["schema_version"],
        "requested": batch["requested"],
        "input_pass": batch["input_pass"],
        "input_fail": batch["input_fail"],
        "partial": batch["partial"],
        "complete": batch["complete"],
        "coverage": batch["coverage"],
        "universe_claim": False,
        "failures": batch["failures"],
        "files": files,
    }
    (root / "batch_manifest.json").write_bytes(canonical_bytes(manifest) + b"\n")
    return root


def read_batch(directory: Path | str) -> dict:
    root = Path(directory)
    manifest = json.loads((root / "batch_manifest.json").read_text(encoding="utf-8"))
    records = []
    for item in manifest["files"]:
        record = json.loads((root / item["file"]).read_text(encoding="utf-8"))
        if record["company_id"] != item["company_id"]:
            raise TechnicalProducerError("persisted company_id does not match the manifest")
        if semantic_hash(record) != record["semantic_hash"]:
            raise TechnicalProducerError("persisted record semantic hash mismatch")
        if record["semantic_hash"] != item["semantic_hash"]:
            raise TechnicalProducerError("manifest semantic hash mismatch")
        records.append(record)
    manifest["records"] = records
    return manifest
