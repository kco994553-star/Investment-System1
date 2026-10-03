"""C1 preregistration and experiment-bound trial accounting.

No optimizer or promotion is performed here. Every attempted trial, including a
failure outside the parameter domain, is retained; only a registered, complete,
successful in-budget trial can be returned as supporting evidence.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from hashlib import sha256
import fcntl
import json
import os
from pathlib import Path

from .contracts import EVL_CONTRACT_ID, TAX_MODE, ExperimentSpec, TrialRecord, TrialStatus
from .ledger import TrialLedger, canonical_json


def _spec_payload(spec: ExperimentSpec) -> dict:
    payload = asdict(spec)
    payload["registered_at"] = spec.registered_at.isoformat()
    payload["decision_time"] = spec.decision_time.isoformat()
    for key, value in payload["dataset_split"].items():
        if isinstance(value, datetime):
            payload["dataset_split"][key] = value.isoformat()
    # Round-trip snapshots mutable mappings and rejects unsupported/NaN values.
    return json.loads(canonical_json(payload))


class ExperimentLedger:
    """Single experiment, immutable registration, terminal trial ledger.

    Append-only INVALIDATED records reference the original via parent_trial_id.
    They revoke its eligibility without rewriting historical trial outcomes.
    """
    def __init__(self, directory: str | Path):
        self.directory = Path(directory)
        self.registration_path = self.directory / "experiment.json"
        self.trials = TrialLedger(self.directory / "trials.jsonl")

    def register(self, spec: ExperimentSpec) -> str:
        payload = _spec_payload(spec)
        if payload["contract_id"] != EVL_CONTRACT_ID:
            raise ValueError("wrong experiment contract")
        digest = sha256(canonical_json(payload).encode()).hexdigest()
        self.directory.mkdir(parents=True, exist_ok=True)
        with (self.directory / "experiment.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if self.trials.records():
                raise ValueError("cannot register after trial results exist")
            with self.registration_path.open("x", encoding="utf-8") as stream:
                stream.write(canonical_json({"sha256": digest, "spec": payload}) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
        return digest

    def registration(self) -> dict:
        try:
            envelope = json.loads(self.registration_path.read_text(encoding="utf-8"))
            spec = envelope["spec"]
            if sha256(canonical_json(spec).encode()).hexdigest() != envelope["sha256"]:
                raise ValueError("registration digest mismatch")
            if spec["contract_id"] != EVL_CONTRACT_ID or spec["tax_mode"] != TAX_MODE:
                raise ValueError("registration contract/tax mismatch")
            return spec
        except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise ValueError("missing or malformed preregistration") from exc

    def append(self, record: TrialRecord) -> str:
        spec = self.registration()
        if record.experiment_id != spec["experiment_id"]:
            raise ValueError("trial experiment mismatch")
        if record.recorded_at < datetime.fromisoformat(spec["registered_at"]):
            raise ValueError("trial precedes preregistration")
        # Accounting is serialized separately from the raw ledger's write lock.
        with (self.directory / "experiment.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            rows = [row["trial"] for row in self.trials.records()]
            if record.status == TrialStatus.INVALIDATED:
                parents = [r for r in rows if r["trial_id"] == record.parent_trial_id
                           and r["experiment_id"] == record.experiment_id
                           and r["status"] != TrialStatus.INVALIDATED.value]
                if not parents:
                    raise ValueError("invalidation requires an existing trial")
            return self.trials.append(record)

    def supporting_trial(self, trial_id: str) -> dict:
        """Resolve evidence only; never declares VALIDATED/FROZEN/OFFICIAL."""
        spec = self.registration()
        rows = [row["trial"] for row in self.trials.records()]
        if any(row["experiment_id"] != spec["experiment_id"] for row in rows):
            raise ValueError("foreign experiment in ledger")
        if any(datetime.fromisoformat(row["recorded_at"]) <
               datetime.fromisoformat(spec["registered_at"]) for row in rows):
            raise ValueError("unregistered historical trials")
        attempts = [r for r in rows if r["status"] != TrialStatus.INVALIDATED.value]
        if len(attempts) > spec["search_budget"]["max_trials"]:
            raise ValueError("registered search budget exceeded")
        if any(row["status"] == TrialStatus.INVALIDATED.value and
               row["parent_trial_id"] == trial_id for row in rows):
            raise ValueError("trial invalidated")
        matches = [r for r in rows if r["trial_id"] == trial_id]
        if not matches or matches[0]["status"] != TrialStatus.SUCCESS.value:
            raise ValueError("unlogged or unsuccessful trial")
        trial = matches[0]
        domains = spec["parameter_space"]["values"]
        if set(trial["parameters"]) != set(domains) or any(
            trial["parameters"][key] not in values for key, values in domains.items()
        ):
            raise ValueError("parameters outside registered space")
        if set(trial["metrics"]) != set(spec["metric_set"]["metric_ids"]):
            raise ValueError("metrics differ from registered set")
        return trial
