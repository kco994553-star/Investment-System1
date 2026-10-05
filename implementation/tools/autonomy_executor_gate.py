#!/usr/bin/env python3
"""HG-03 executor admission guard for CDR-024.

This is a fail-closed local runtime gate. It does not grant GitHub authority.
Any unattended executor must call:
  start-cycle -> before-task -> before-repair -> before-publish -> end-cycle

The user-owned AUTONOMY_MODE file is read at start and again before publish.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG = REPO_ROOT / "implementation/docs/coordination/governance/AUTONOMY_GUARD_CONFIG.v1.json"
MODE_FILE = REPO_ROOT / "implementation/docs/coordination/governance/AUTONOMY_MODE"
STATE_FILE = REPO_ROOT / "implementation/docs/coordination/governance/AUTONOMY_RUNTIME_STATE.json"


class GateError(RuntimeError):
    pass


@dataclass
class RuntimeState:
    schema: str = "autonomy-runtime-state-v1"
    cycle_id: str | None = None
    holder: str | None = None
    branch: str | None = None
    started_at_epoch: int | None = None
    lease_expires_at_epoch: int | None = None
    tasks_used: int = 0
    repair_rounds: dict[str, int] | None = None
    status: str = "IDLE"

    def to_json(self) -> dict:
        d = asdict(self)
        d["repair_rounds"] = d["repair_rounds"] or {}
        return d


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_config() -> dict:
    cfg = _load_json(CONFIG)
    values = cfg["operating_values"]
    if values != {
        "cycle_max_tasks": 5,
        "lease_ttl_seconds": 7200,
        "repair_round_cap": 3,
    }:
        raise GateError(f"operating values drift: {values!r}")
    return cfg


def read_mode() -> str:
    mode = MODE_FILE.read_text(encoding="utf-8").strip()
    if mode not in {"RUN", "PAUSE", "READ_ONLY"}:
        raise GateError(f"invalid AUTONOMY_MODE={mode!r}")
    return mode


def load_state() -> RuntimeState:
    if not STATE_FILE.exists():
        return RuntimeState(repair_rounds={})
    raw = _load_json(STATE_FILE)
    return RuntimeState(
        schema=raw.get("schema", "autonomy-runtime-state-v1"),
        cycle_id=raw.get("cycle_id"),
        holder=raw.get("holder"),
        branch=raw.get("branch"),
        started_at_epoch=raw.get("started_at_epoch"),
        lease_expires_at_epoch=raw.get("lease_expires_at_epoch"),
        tasks_used=int(raw.get("tasks_used", 0)),
        repair_rounds=dict(raw.get("repair_rounds") or {}),
        status=raw.get("status", "IDLE"),
    )


def save_state(state: RuntimeState) -> None:
    tmp = STATE_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state.to_json(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, STATE_FILE)


def require_run_mode() -> None:
    mode = read_mode()
    if mode == "PAUSE":
        raise GateError("AUTONOMY_MODE=PAUSE")
    if mode == "READ_ONLY":
        raise GateError("AUTONOMY_MODE=READ_ONLY blocks mutation")


def start_cycle(holder: str, branch: str, cycle_id: str, now: int) -> RuntimeState:
    cfg = load_config()
    require_run_mode()
    s = load_state()
    if s.status == "RUNNING":
        if s.lease_expires_at_epoch is None:
            raise GateError("active lease has no expiry; fail closed")
        if now <= s.lease_expires_at_epoch:
            raise GateError(f"active lease held by {s.holder}")
        # TTL expiry alone is never enough to reclaim.
        raise GateError("lease expired but stale-recovery evidence/CAS is required; no automatic reclaim")
    s = RuntimeState(
        cycle_id=cycle_id,
        holder=holder,
        branch=branch,
        started_at_epoch=now,
        lease_expires_at_epoch=now + int(cfg["operating_values"]["lease_ttl_seconds"]),
        tasks_used=0,
        repair_rounds={},
        status="RUNNING",
    )
    save_state(s)
    return s


def require_owner(s: RuntimeState, holder: str, cycle_id: str, now: int) -> None:
    if s.status != "RUNNING":
        raise GateError("no active cycle")
    if s.holder != holder or s.cycle_id != cycle_id:
        raise GateError("lease owner/cycle mismatch")
    if s.lease_expires_at_epoch is None or now > s.lease_expires_at_epoch:
        raise GateError("lease expired; publish/mutation denied")


def before_task(holder: str, cycle_id: str, now: int) -> RuntimeState:
    cfg = load_config()
    require_run_mode()
    s = load_state()
    require_owner(s, holder, cycle_id, now)
    cap = int(cfg["operating_values"]["cycle_max_tasks"])
    if s.tasks_used >= cap:
        raise GateError(f"cycle task cap reached: {cap}")
    s.tasks_used += 1
    save_state(s)
    return s


def before_repair(holder: str, cycle_id: str, failure_key: str, now: int) -> RuntimeState:
    cfg = load_config()
    require_run_mode()
    s = load_state()
    require_owner(s, holder, cycle_id, now)
    rounds = s.repair_rounds or {}
    n = int(rounds.get(failure_key, 0))
    cap = int(cfg["operating_values"]["repair_round_cap"])
    if n >= cap:
        raise GateError(f"repair cap reached for {failure_key}: {cap}; REPLAN required")
    rounds[failure_key] = n + 1
    s.repair_rounds = rounds
    save_state(s)
    return s


def before_publish(holder: str, cycle_id: str, now: int) -> RuntimeState:
    # Mandatory second Kill Switch read immediately before any publication.
    require_run_mode()
    s = load_state()
    require_owner(s, holder, cycle_id, now)
    return s


def end_cycle(holder: str, cycle_id: str, now: int) -> RuntimeState:
    s = load_state()
    require_owner(s, holder, cycle_id, now)
    s.status = "IDLE"
    s.lease_expires_at_epoch = None
    save_state(s)
    return s


def cli() -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("start-cycle", "before-task", "before-publish", "end-cycle"):
        sp = sub.add_parser(name)
        sp.add_argument("--holder", required=True)
        sp.add_argument("--cycle-id", required=True)
        if name == "start-cycle":
            sp.add_argument("--branch", required=True)
    sp = sub.add_parser("before-repair")
    sp.add_argument("--holder", required=True)
    sp.add_argument("--cycle-id", required=True)
    sp.add_argument("--failure-key", required=True)
    sub.add_parser("mode")

    a = p.parse_args()
    now = int(time.time())
    try:
        if a.cmd == "mode":
            print(read_mode())
            return 0
        if a.cmd == "start-cycle":
            result = start_cycle(a.holder, a.branch, a.cycle_id, now)
        elif a.cmd == "before-task":
            result = before_task(a.holder, a.cycle_id, now)
        elif a.cmd == "before-repair":
            result = before_repair(a.holder, a.cycle_id, a.failure_key, now)
        elif a.cmd == "before-publish":
            result = before_publish(a.holder, a.cycle_id, now)
        else:
            result = end_cycle(a.holder, a.cycle_id, now)
        print(json.dumps(result.to_json(), ensure_ascii=False, indent=2))
        return 0
    except (GateError, OSError, json.JSONDecodeError) as exc:
        print(f"AUTONOMY_EXECUTOR_DENY: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(cli())
