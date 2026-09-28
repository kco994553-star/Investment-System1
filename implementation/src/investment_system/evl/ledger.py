"""Append-only Trial Ledger for Track C."""
from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
from typing import Iterable

from .contracts import TrialRecord

class TrialLedger:
    """Append-only JSONL ledger.

    Existing bytes are never rewritten by this class. Sequence and trial IDs are
    checked against the current file before every append. Failed/rejected/
    early-stopped/invalidated trials are first-class records.
    """
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def records(self) -> list[dict]:
        if not self.path.exists():
            return []
        out = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                out.append(json.loads(line))
        return out

    def append(self, record: TrialRecord) -> str:
        rows = self.records()
        if any(row["trial_id"] == record.trial_id for row in rows):
            raise ValueError("trial_id already logged")
        expected = 0 if not rows else rows[-1]["sequence"] + 1
        if record.sequence != expected:
            raise ValueError(f"sequence must be {expected}")
        payload = asdict(record)
        payload["recorded_at"] = record.recorded_at.isoformat()
        payload["status"] = record.status.value
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        digest = sha256(canonical.encode()).hexdigest()
        envelope = json.dumps({"sha256": digest, "trial": payload}, sort_keys=True, default=str)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(envelope + "\n")
        return digest

    def verify(self) -> bool:
        rows = self.records()
        for i, row in enumerate(rows):
            trial = row.get("trial", {})
            if trial.get("sequence") != i:
                return False
            canonical = json.dumps(trial, sort_keys=True, separators=(",", ":"), default=str)
            if sha256(canonical.encode()).hexdigest() != row.get("sha256"):
                return False
        return True
