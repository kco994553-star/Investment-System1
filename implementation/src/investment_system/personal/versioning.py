"""Version / hash / provenance / result namespaces (PIL §20, §21, Locked Rules)."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional


class ResultNamespace(str, Enum):
    """Results never cross namespaces: a PREVIEW or SANDBOX result is not an OFFICIAL or ACTUAL result."""

    OFFICIAL = "OFFICIAL"
    CUSTOM_ACTIVE = "CUSTOM_ACTIVE"
    SANDBOX = "SANDBOX"
    PREVIEW = "PREVIEW"
    BACKTEST = "BACKTEST"
    FORWARD = "FORWARD"


def _canon(obj: Any) -> Any:
    if is_dataclass(obj) and not isinstance(obj, type):
        return _canon(asdict(obj))
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, float):
        if obj != obj or obj in (float("inf"), float("-inf")):
            raise ValueError("non-finite float cannot be hashed canonically")
        return repr(obj)
    if isinstance(obj, dict):
        return {str(k): _canon(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_canon(v) for v in obj]
    return obj


def content_hash(obj: Any) -> str:
    """sha256 of canonical JSON (sorted keys, floats by repr, datetimes ISO). Same content -> same hash."""
    blob = json.dumps(_canon(obj), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Provenance:
    """Where a value came from. source_ref points at the upstream object (e.g. a snapshot id); no value is copied in."""

    source_system: str
    source_ref: str
    source_version: str
    content_hash: str
    namespace: ResultNamespace
    retrieved_at: Optional[datetime] = None
