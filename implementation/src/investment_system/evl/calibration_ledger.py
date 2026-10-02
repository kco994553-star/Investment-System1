"""C8 dedicated durable protocol attempts, access events and current checkpoints.

Local POSIX locks/checkpoints are software mechanisms, not external proof of
human non-access. The shared registry must not be reset between experiments.
No real provider or research authorization is supplied by this storage layer.
"""
from contextlib import contextmanager
from copy import deepcopy
import fcntl
from hashlib import sha256
import json
import os
from pathlib import Path

from .calibration_contracts import (METHOD, OPERATIONS, IntegrityFailure,
                                   MissingPrerequisite, instant, identity, validate_plan)
from .ledger import canonical_json
from .walkforward import digest


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def create_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as f:
        f.write(canonical_json(value) + "\n")
        f.flush()
        os.fsync(f.fileno())
    sync_directory(path.parent)


class _Chain:
    def __init__(self, path):
        self.path = Path(path)

    def rows(self):
        if not self.path.exists():
            return []
        raw = self.path.read_text()
        if raw and not raw.endswith("\n"):
            raise IntegrityFailure("incomplete event tail: no automatic truncation")
        result = []
        try:
            for line in raw.splitlines():
                row = json.loads(line)
                body = row["body"]
                if (set(row) != {"sha256", "body"} or digest(body) != row["sha256"]
                        or set(body) != {"sequence", "previous", "at", "event"}
                        or type(body["sequence"]) is not int or body["sequence"] != len(result)
                        or body["previous"] != (result[-1]["sha256"] if result else None)):
                    raise IntegrityFailure("event sequence/hash/prefix changed")
                at = instant(body["at"])
                if result and at < instant(result[-1]["body"]["at"]):
                    raise IntegrityFailure("event time cannot be reset/backdated")
                result.append(row)
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise IntegrityFailure("malformed event chain") from exc
        return result

    def append(self, event, at):
        rows = self.rows()
        time = instant(at)
        if rows and time < instant(rows[-1]["body"]["at"]):
            raise IntegrityFailure("nonmonotone event")
        body = {"sequence": len(rows), "previous": rows[-1]["sha256"] if rows else None,
                "at": time.isoformat(), "event": deepcopy(event)}
        row = {"sha256": digest(body), "body": body}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(canonical_json(row) + "\n")
            f.flush()
            os.fsync(f.fileno())
        sync_directory(self.path.parent)
        return row


class AccessRegistry:
    """Shared across ledger directories; first-read intents survive crashes."""
    def __init__(self, directory, registry_id):
        self.directory = Path(directory)
        self.registry_id = identity(registry_id)
        self.chain = _Chain(self.directory / "access.jsonl")

    @contextmanager
    def lock(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        with (self.directory / "registry.lock").open("a") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            yield

    def rows(self):
        rows = self.chain.rows()
        if any(r["body"]["event"]["registry_id"] != self.registry_id for r in rows):
            raise IntegrityFailure("foreign access registry")
        return rows

    def _append(self, event, at):
        return self.chain.append({**event, "registry_id": self.registry_id}, at)

    @staticmethod
    def keys(data):
        # Independent of ledger, campaign, directory and dataset-role labels.
        return sorted({"content:" + data["content_hash"]} | {
            "outcome:" + digest([data["source_id"], data["vintage"], s["sample_id"]])
            for s in data["samples"]})

    def enrolled(self, ledger_id, registration_hash):
        rows = self.rows()
        matches = [r for r in rows if r["body"]["event"]["kind"] == "REGISTER"
                   and r["body"]["event"]["ledger_id"] == ledger_id]
        if len(matches) != 1 or matches[0]["body"]["event"]["registration_hash"] != registration_hash:
            raise IntegrityFailure("missing/replaced registration access checkpoint")
        return matches[0]

    def spent(self, data):
        keys = set(self.keys(data))
        return any(keys & set(r["body"]["event"]["keys"])
                   for r in self.rows() if r["body"]["event"]["kind"] == "ACCESS_INTENT")

    def enroll(self, plan, registration_hash):
        with self.lock():
            if any(r["body"]["event"].get("ledger_id") == plan["ledger_id"] for r in self.rows()):
                raise IntegrityFailure("registry ledger identity already used")
            if any(self.spent(d) for d in plan["datasets"].values()):
                raise IntegrityFailure("already accessed targets cannot be registered as unseen")
            return self._append({"kind": "REGISTER", "ledger_id": plan["ledger_id"],
                                 "registration_hash": registration_hash,
                                 "campaign_id": plan["campaign_id"],
                                 "dataset_keys": {k: self.keys(d) for k, d in plan["datasets"].items()}},
                                plan["registered_at"])

    def checkpoint(self, ledger_id, registration_hash, row):
        with self.lock():
            self.enrolled(ledger_id, registration_hash)
            return self._append({"kind": "CHECKPOINT", "ledger_id": ledger_id,
                                 "registration_hash": registration_hash,
                                 "sequence": row["body"]["sequence"], "ledger_hash": row["sha256"]},
                                row["body"]["at"])

    def latest_checkpoint(self, ledger_id):
        rows = [r for r in self.rows() if r["body"]["event"]["kind"] == "CHECKPOINT"
                and r["body"]["event"]["ledger_id"] == ledger_id]
        return rows[-1]["body"]["event"] if rows else None

    def claim(self, plan, registration_hash, role, attempt_id, pending_hash, at):
        with self.lock():
            self.enrolled(plan["ledger_id"], registration_hash)
            prior = [r["body"]["event"] for r in self.rows() if r["body"]["event"]["kind"] == "ACCESS_INTENT"
                     and set(r["body"]["event"]["keys"]) & set(self.keys(plan["datasets"][role]))]
            if prior and (role == "CAL_VERIFY" or any(e["role"] != role or e["ledger_id"] != plan["ledger_id"] for e in prior)):
                raise MissingPrerequisite("one-shot dataset access already registered; no retry/relabel")
            return self._append({"kind": "ACCESS_INTENT", "ledger_id": plan["ledger_id"],
                                 "registration_hash": registration_hash, "role": role,
                                 "attempt_id": attempt_id, "pending_hash": pending_hash,
                                 "keys": self.keys(plan["datasets"][role])}, at)


class CalibrationLedger:
    def __init__(self, directory, registry):
        self.directory = Path(directory)
        self.registry = registry
        self.chain = _Chain(self.directory / "events.jsonl")
        self.registration_path = self.directory / "calibration.json"

    @contextmanager
    def lock(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        with (self.directory / "calibration.lock").open("a") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            yield

    def register(self, plan):
        p = validate_plan(plan)
        if p["access_registry_id"] != self.registry.registry_id:
            raise IntegrityFailure("registered access service identity mismatch")
        body = {"method": METHOD, "plan": p}
        with self.lock():
            if self.chain.rows():
                raise IntegrityFailure("registration cannot follow attempts or access")
            create_json(self.registration_path, {"sha256": digest(body), "body": body})
            self.registry.enroll(p, digest(body))
            self._append({"kind": "REGISTRATION", "registration_hash": digest(body)}, p["registered_at"])
        return digest(body)

    def registration(self):
        try:
            envelope = json.loads(self.registration_path.read_text())
            if (digest(envelope["body"]) != envelope["sha256"]
                    or envelope["body"]["method"] != METHOD):
                raise IntegrityFailure("immutable registration altered")
            plan = envelope["body"]["plan"]
            self.registry.enrolled(plan["ledger_id"], envelope["sha256"])
            if plan["access_registry_id"] != self.registry.registry_id:
                raise IntegrityFailure("wrong current access registry")
            return deepcopy(envelope)
        except (KeyError, TypeError, OSError, json.JSONDecodeError) as exc:
            raise IntegrityFailure("missing/malformed registration") from exc

    def events(self):
        registration = self.registration()
        rows = self.chain.rows()
        pin = self.registry.latest_checkpoint(registration["body"]["plan"]["ledger_id"])
        if pin and (len(rows) <= pin["sequence"] or rows[pin["sequence"]]["sha256"] != pin["ledger_hash"]):
            raise IntegrityFailure("deleted/replaced event prefix disagrees with access checkpoint")
        pending, terminal, ids = {}, set(), set()
        for row in rows:
            e = row["body"]["event"]
            kind = e["kind"]
            if kind in ("PENDING", "BLOCKED_NOT_RUN"):
                if e["attempt_id"] in ids or e["operation"] not in OPERATIONS:
                    raise IntegrityFailure("duplicate/unregistered attempt")
                ids.add(e["attempt_id"])
                if kind == "PENDING":
                    pending[e["attempt_id"]] = row
            elif kind == "TERMINAL":
                if e["attempt_id"] not in pending or e["attempt_id"] in terminal or e["status"] not in ("PASS", "FAIL", "NOT_RUN", "CRASH"):
                    raise IntegrityFailure("terminal without unique durable pending attempt")
                terminal.add(e["attempt_id"])
            elif kind == "INVALIDATION":
                if e["parent_attempt_id"] is not None and e["parent_attempt_id"] not in pending:
                    raise IntegrityFailure("invalidation parent absent")
            elif kind == "ACCESS_INTENT":
                if e["attempt_id"] not in pending:
                    raise IntegrityFailure("access precedes attempt")
            elif kind != "REGISTRATION":
                raise IntegrityFailure("unknown protocol event")
            if instant(row["body"]["at"]) < instant(registration["body"]["plan"]["registered_at"]):
                raise IntegrityFailure("event before preregistration")
        return rows

    def _append(self, event, at):
        self.events()
        row = self.chain.append(event, at)
        r = self.registration()
        self.registry.checkpoint(r["body"]["plan"]["ledger_id"], r["sha256"], row)
        return row

    def accounting(self):
        events = [r["body"]["event"] for r in self.events()]
        return {"charged_attempts": sum(e["kind"] == "PENDING" for e in events),
                "all_attempt_ids": [e["attempt_id"] for e in events if e["kind"] in ("PENDING", "BLOCKED_NOT_RUN")],
                "pending": [e["attempt_id"] for e in events if e["kind"] == "PENDING"
                            and not any(t["kind"] == "TERMINAL" and t["attempt_id"] == e["attempt_id"] for t in events)],
                "events": deepcopy(events)}

    def active(self, attempt_id=None):
        return not any(r["body"]["event"]["kind"] == "INVALIDATION"
                       and r["body"]["event"]["parent_attempt_id"] in (None, attempt_id)
                       for r in self.events())

    def _recover(self, at):
        for attempt_id in self.accounting()["pending"]:
            self._append({"kind": "TERMINAL", "attempt_id": attempt_id, "status": "CRASH",
                          "reason": "INTERRUPTED_DURABLE_ATTEMPT_NO_REEXECUTION", "report_hash": None}, at)

    def recover(self, at):
        with self.lock():
            self._recover(at)

    def _begin(self, attempt_id, operation, at):
        identity(attempt_id)
        if operation not in OPERATIONS:
            raise IntegrityFailure("unregistered operation cannot be attempted")
        if attempt_id in self.accounting()["all_attempt_ids"]:
            raise IntegrityFailure("attempt identity already consumed")
        plan = self.registration()["body"]["plan"]
        if instant(at) < instant(plan["registered_at"]):
            raise IntegrityFailure("attempt before registration")
        if not self.active() or self.accounting()["charged_attempts"] >= plan["budget"]["max_attempts"]:
            reason = "CURRENT_INVALIDATION" if not self.active() else "REGISTERED_BUDGET_EXHAUSTED"
            self._append({"kind": "BLOCKED_NOT_RUN", "attempt_id": attempt_id, "operation": operation,
                          "reason": reason, "charged": False}, at)
            raise MissingPrerequisite(reason)
        return self._append({"kind": "PENDING", "attempt_id": attempt_id, "operation": operation,
                             "registration_hash": self.registration()["sha256"],
                             "full_family": deepcopy(plan["family_members"])}, at)

    def begin(self, attempt_id, operation, at):
        with self.lock():
            self._recover(at)
            return self._begin(attempt_id, operation, at)

    def mark_access(self, pending, role, at):
        r = self.registration()
        claim = self.registry.claim(r["body"]["plan"], r["sha256"], role,
                                    pending["body"]["event"]["attempt_id"], pending["sha256"], at)
        return self._append({"kind": "ACCESS_INTENT", "attempt_id": pending["body"]["event"]["attempt_id"],
                             "role": role, "registry_event_hash": claim["sha256"],
                             "pending_hash": pending["sha256"]}, at)

    def report_path(self, attempt_id):
        return self.directory / ("report-" + sha256(attempt_id.encode()).hexdigest() + ".json")

    def execute(self, attempt_id, operation, at, producer):
        """Pending is durable before producer entry. BaseException leaves a crash."""
        with self.lock():
            self._recover(at)
            try:
                pending = self._begin(attempt_id, operation, at)
            except MissingPrerequisite as exc:
                return {"status": "NOT_RUN", "reason": str(exc), "attempt_id": attempt_id}
            status, reason, output = "PASS", None, None
            try:
                output = producer(pending)
                digest(output)
            except MissingPrerequisite as exc:
                status, reason = "NOT_RUN", str(exc)
            except Exception as exc:
                status, reason = "FAIL", type(exc).__name__ + ": " + str(exc)
            report = {"method": METHOD, "registration_hash": self.registration()["sha256"],
                      "attempt_id": attempt_id, "operation": operation, "pending_hash": pending["sha256"],
                      "status": status, "reason": reason, "output": output,
                      "scope": "SYNTHETIC_SOFTWARE_VALIDATION", "research_state": None,
                      "official": False, "holdout_state": "UNCONSUMED"}
            create_json(self.report_path(attempt_id), report)
            self._append({"kind": "TERMINAL", "attempt_id": attempt_id, "status": status,
                          "reason": reason, "report_hash": digest(report)}, at)
            return deepcopy(report)

    def invalidate(self, event_id, parent_attempt_id, reason, at):
        identity(event_id)
        identity(reason)
        with self.lock():
            rows = self.events()
            if any(r["body"]["event"].get("event_id") == event_id for r in rows):
                raise IntegrityFailure("duplicate invalidation event")
            if parent_attempt_id is not None and parent_attempt_id not in [r["body"]["event"]["attempt_id"] for r in rows if r["body"]["event"]["kind"] == "PENDING"]:
                raise IntegrityFailure("missing invalidation parent")
            return self._append({"kind": "INVALIDATION", "event_id": event_id,
                                 "parent_attempt_id": parent_attempt_id, "reason": reason}, at)

    def receipt(self, attempt_id):
        if not self.active(attempt_id):
            raise IntegrityFailure("current invalidation revokes receipt eligibility")
        rows = self.events()
        pending = [r for r in rows if r["body"]["event"]["kind"] == "PENDING"
                   and r["body"]["event"]["attempt_id"] == attempt_id]
        terminal = [r for r in rows if r["body"]["event"]["kind"] == "TERMINAL"
                    and r["body"]["event"]["attempt_id"] == attempt_id]
        if len(pending) != 1 or len(terminal) != 1 or terminal[0]["body"]["event"]["status"] != "PASS":
            raise MissingPrerequisite("missing/failed/crashed protocol receipt")
        try:
            report = json.loads(self.report_path(attempt_id).read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise IntegrityFailure("terminal report missing") from exc
        if (report["registration_hash"] != self.registration()["sha256"]
                or report["attempt_id"] != attempt_id or report["pending_hash"] != pending[0]["sha256"]
                or report["operation"] != pending[0]["body"]["event"]["operation"]
                or report["status"] != "PASS" or digest(report) != terminal[0]["body"]["event"]["report_hash"]
                or report["scope"] != "SYNTHETIC_SOFTWARE_VALIDATION"
                or report["research_state"] is not None or report["official"] is not False
                or report["holdout_state"] != "UNCONSUMED"):
            raise IntegrityFailure("current terminal identity/hash/scope mismatch")
        return deepcopy(report)
