"""Canonical artifact bytes and existing private delivery ceiling; no scoring."""
import hashlib
import json

MAX_BYTES = 1_800_000


def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def json_bytes(value):
    return canonical_bytes(value) + b'\n'
