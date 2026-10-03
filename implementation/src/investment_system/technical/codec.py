"""Canonical JSON for Technical records. No network. No engine import."""

from __future__ import annotations

import hashlib
import json
from typing import Any

SEMANTIC_EXCLUDE = frozenset({"generated_at", "record_id", "semantic_hash", "engine_snapshot_id"})


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def semantic_body(record: dict) -> dict:
    return {k: v for k, v in record.items() if k not in SEMANTIC_EXCLUDE}


def semantic_hash(record: dict) -> str:
    return sha256_hex(canonical_bytes(semantic_body(record)))
