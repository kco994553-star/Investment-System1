"""Canonical JSON. Same settings as Producer Infrastructure v1 serialization (sorted, compact, no NaN)."""

from __future__ import annotations

import dataclasses
import hashlib
import json
import math
from datetime import date, datetime
from enum import Enum
from typing import Any, Mapping

from .errors import LeaderboardProducerError


def to_jsonable(value: Any) -> Any:
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {f.name: to_jsonable(getattr(value, f.name)) for f in dataclasses.fields(value)}
    if isinstance(value, Enum):
        return to_jsonable(value.value)
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise LeaderboardProducerError("SERIALIZATION", "naive datetime")
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Mapping):
        out = {}
        for k, v in value.items():
            if not isinstance(k, str):
                raise LeaderboardProducerError("SERIALIZATION", f"non-string key {k!r}")
            out[k] = to_jsonable(v)
        return out
    if isinstance(value, (list, tuple)):
        return [to_jsonable(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        raise LeaderboardProducerError("SERIALIZATION", "NaN/Infinity is not valid JSON")
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise LeaderboardProducerError("SERIALIZATION", f"unsupported type {type(value).__name__}")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        to_jsonable(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_sha256(value: Any) -> str:
    return sha256_hex(canonical_bytes(value))
