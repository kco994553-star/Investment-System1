"""Append-only Trial Ledger for Track C; local POSIX file storage."""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from hashlib import sha256
import fcntl
import json
import math
import os
from pathlib import Path

from .contracts import TrialRecord, TrialStatus


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _validate_trial(trial: dict) -> None:
    record = TrialRecord(**{
        **trial, "status": TrialStatus(trial["status"]),
        "recorded_at": datetime.fromisoformat(trial["recorded_at"]),
    })
    if not isinstance(record.sequence, int) or isinstance(record.sequence, bool):
        raise ValueError("sequence must be an integer")
    if not isinstance(record.parameters, dict) or not isinstance(record.metrics, dict):
        raise ValueError("parameters and metrics must be mappings")
    if any(not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v)
           for v in record.metrics.values()):
        raise ValueError("metrics must be finite numbers")
    canonical_json(trial)


class TrialLedger:
    """Append-only JSONL, preserving C0 envelopes and public API.

    A separate advisory lock serializes writers using this class. Hash checks
    detect accidental corruption; they are not a substitute for access control
    or an externally retained checkpoint against malicious file replacement.
    """
    def __init__(self, path: str | Path):
        self.path = Path(path)

    @staticmethod
    def _read_verified(raw: str) -> list[dict]:
        if raw and not raw.endswith("\n"):
            raise ValueError("incomplete ledger tail")
        out, ids = [], set()
        for i, line in enumerate(raw.splitlines()):
            row = json.loads(line)
            trial = row["trial"]
            _validate_trial(trial)
            if trial["sequence"] != i or trial["trial_id"] in ids:
                raise ValueError("invalid sequence or duplicate trial_id")
            if sha256(canonical_json(trial).encode()).hexdigest() != row["sha256"]:
                raise ValueError("trial digest mismatch")
            # C0 rows have no predecessor field; new rows bind the prefix.
            if "previous_sha256" in row:
                expected = out[-1]["sha256"] if out else None
                if row["previous_sha256"] != expected:
                    raise ValueError("ledger predecessor mismatch")
            ids.add(trial["trial_id"])
            out.append(row)
        return out

    def records(self) -> list[dict]:
        if not self.path.exists():
            return []
        try:
            return self._read_verified(self.path.read_text(encoding="utf-8"))
        except (KeyError, TypeError, json.JSONDecodeError, UnicodeError) as exc:
            raise ValueError("malformed ledger") from exc

    def append(self, record: TrialRecord) -> str:
        payload = asdict(record)
        payload["recorded_at"] = record.recorded_at.isoformat()
        payload["status"] = record.status.value
        _validate_trial(payload)
        digest = sha256(canonical_json(payload).encode()).hexdigest()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.with_name(self.path.name + ".lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            rows = self.records()
            if any(row["trial"]["trial_id"] == record.trial_id for row in rows):
                raise ValueError("trial_id already logged")
            if record.sequence != len(rows):
                raise ValueError(f"sequence must be {len(rows)}")
            envelope = canonical_json({
                "sha256": digest, "trial": payload,
                "previous_sha256": rows[-1]["sha256"] if rows else None,
            })
            with self.path.open("a", encoding="utf-8") as stream:
                stream.write(envelope + "\n")
                stream.flush()
                os.fsync(stream.fileno())
        return digest

    def verify(self) -> bool:
        try:
            self.records()
        except (ValueError, OSError):
            return False
        return True
