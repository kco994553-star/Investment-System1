#!/usr/bin/env python3
"""Read-only, score-neutral task selector. No API, subprocess or mutation.

Input: STATE.continuation_plan.tasks and append-only receipt JSON objects.
This is control evidence, not a QGV evaluator or approval engine.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def canonical_hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _contained_path(repo: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ValueError("Input/output must be an explicit repository-relative path")
    path = (repo / relative).resolve()
    if not path.is_relative_to(repo.resolve()):
        raise ValueError("Input/output escapes repository")
    return path


def _is_control_noise(relative: str) -> bool:
    parts = Path(relative).parts
    return ("automation" in parts and
            ("receipts" in parts or Path(relative).name in {"STATE.json", "CONTROL.md"}))


def _refs(task: dict) -> list[dict]:
    return (task.get("semantic_inputs", []) + task.get("method_policy_refs", []) +
            task.get("approval_dependencies", []) + [task.get("acceptance_ref", {})])


def task_fingerprint(repository: str, task: dict) -> str:
    """Only explicit immutable task semantics; no owner HEAD/time/lease noise."""
    refs = {}
    for key in ("semantic_inputs", "method_policy_refs", "approval_dependencies"):
        refs[key] = sorted(task.get(key, []), key=lambda x: (x.get("path", ""),
                                                          x.get("id", "")))
    payload = {
        "protocol": "QGV_STATE_CONTINUATION_V2",
        "repository": repository,
        "id": task["id"], "version": task["version"],
        "classification": task["classification"], "work_spec": task["work_spec"],
        **refs,
        "dependencies": sorted(task.get("dependencies", []),
                               key=lambda x: x.get("task_id", "")),
        "output_contract": task["output_contract"],
        "acceptance_ref": task["acceptance_ref"],
        "replan": task.get("replan"),
    }
    return canonical_hash(payload)


def validate_inputs(repo: Path, task: dict) -> list[str]:
    failures = []
    for key in ("semantic_inputs", "method_policy_refs", "approval_dependencies", "acceptance_ref"):
        refs = [task.get(key, {})] if key == "acceptance_ref" else task.get(key, [])
        for ref in refs:
            relative = ref.get("path", "")
            try:
                path = _contained_path(repo, relative)
            except (ValueError, TypeError) as exc:
                failures.append(f"INVALID_INPUT:{relative}:{exc}")
                continue
            if _is_control_noise(relative):
                failures.append(f"CONTROL_NOISE_NOT_SEMANTIC_INPUT:{relative}")
            if not isinstance(ref.get("sha256"), str) or len(ref["sha256"]) != 64:
                failures.append(f"UNPINNED_INPUT:{relative}")
            elif not path.is_file():
                failures.append(f"MISSING_INPUT:{relative}")
            elif file_hash(path) != ref["sha256"]:
                failures.append(f"INPUT_HASH_CHANGED:{relative}")
            if key == "approval_dependencies" and not ref.get("scope"):
                failures.append(f"UNPINNED_APPROVAL_SCOPE:{relative}")
    # A task with no exact semantic input is not a source-based continuation.
    if not task.get("semantic_inputs"):
        failures.append("MISSING_SEMANTIC_INPUT_PINS")
    if not task.get("approval_dependencies"):
        failures.append("MISSING_APPROVAL_DEPENDENCY_PINS")
    return failures


def accepted_completion(repo: Path, task: dict, fp: str, receipts: list[dict]) -> dict | None:
    """Wait/intake/failure dispositions cannot finish a task."""
    if (task.get("classification") not in {"D1", "D2"} or
            task.get("authority_scope") != "EXPLICIT_AUTHORIZED_AUDIT_DESIGN_ONLY" or
            validate_inputs(repo, task)):
        return None
    expected_paths = sorted(task["output_contract"]["paths"])
    for receipt in receipts:
        if (receipt.get("task_id") != task["id"] or
                receipt.get("task_fingerprint") != fp or
                receipt.get("disposition") != "COMPLETED"):
            continue
        acceptance = receipt.get("acceptance", {})
        if (acceptance.get("status") != "ACCEPTED" or
                acceptance.get("validator_ref") != task["acceptance_ref"]):
            continue
        outputs = receipt.get("outputs", [])
        if sorted(o.get("path", "") for o in outputs) != expected_paths:
            continue
        ok = True
        for output in outputs:
            try:
                path = _contained_path(repo, output["path"])
                if not path.is_file() or file_hash(path) != output.get("sha256"):
                    ok = False
            except (ValueError, KeyError, TypeError):
                ok = False
        if ok:
            return receipt
    return None


def output_digest(receipt: dict) -> str:
    return canonical_hash(sorted(receipt["outputs"], key=lambda o: o["path"]))


def _dependency_cycles(tasks: list[dict]) -> set[str]:
    edges = {t["id"]: [d["task_id"] for d in t.get("dependencies", [])] for t in tasks}
    bad, visiting, visited = set(), [], set()

    def visit(node: str) -> None:
        if node in visiting:
            bad.update(visiting[visiting.index(node):])
            return
        if node in visited or node not in edges:
            return
        visiting.append(node)
        for dep in edges[node]:
            visit(dep)
        visiting.pop()
        visited.add(node)

    for node in edges:
        visit(node)
    return bad


def _replan_failure(task: dict, fp: str, receipts: list[dict]) -> str | None:
    """Changing version alone must not turn failure into endless fresh attempts."""
    failed = [r for r in receipts if r.get("task_id") == task["id"] and
              r.get("disposition") == "FAILED"]
    if any(r.get("task_fingerprint") == fp for r in failed):
        return "FAILED_REPLAN_REQUIRED"
    if not failed:
        return None
    replan = task.get("replan") or {}
    parent = replan.get("parent_failed_fingerprint")
    if (not any(r.get("task_fingerprint") == parent for r in failed) or
            not isinstance(replan.get("action"), str) or not replan["action"].strip() or
            not replan.get("evidence_hashes") or
            any(not isinstance(h, str) or len(h) != 64 for h in replan["evidence_hashes"])):
        return "EXPLICIT_ACTIONABLE_REPLAN_REQUIRED"
    # Require a new task version and changed pinned evidence, not a new timestamp.
    parent_receipt = next(r for r in failed if r.get("task_fingerprint") == parent)
    if (not parent_receipt.get("task_version") or task.get("version") == parent_receipt["task_version"] or
            not parent_receipt.get("input_digest") or
            canonical_hash(_refs(task)) == parent_receipt["input_digest"]):
        return "REPLAN_NEW_VERSION_AND_CHANGED_INPUTS_REQUIRED"
    return None


def select(repo: Path, state: dict, receipts: list[dict], events: list[dict] | None = None,
           own_lease_token: str | None = None) -> dict:
    """Plan one finite next task, independent of whether an external event is new.

    An own token enables read-only preview only, not authorization to mutate.
    No expiry, time comparison or stale lease takeover is implemented.
    """
    plan = state.get("continuation_plan", {})
    tasks = plan.get("tasks", [])
    repository = state["repository"]
    if len({t["id"] for t in tasks}) != len(tasks):
        return {"status": "INVALID_PLAN_DUPLICATE_TASK_IDS", "next_task": None}
    cycles = _dependency_cycles(tasks)
    by_id = {t["id"]: t for t in tasks}
    fingerprints = {t["id"]: task_fingerprint(repository, t) for t in tasks}
    completed = {t["id"]: accepted_completion(repo, t, fingerprints[t["id"]], receipts)
                 for t in tasks}
    lease = state.get("lease")
    lease_conflict = bool(lease and lease.get("token") != own_lease_token)
    results = []
    for task in tasks:
        task_id, fp = task["id"], fingerprints[task["id"]]
        record = {"task_id": task_id, "fingerprint": fp}
        matching = [r for r in receipts if r.get("task_id") == task_id and
                    r.get("task_fingerprint") == fp]
        replan_failure = _replan_failure(task, fp, receipts)
        failures = validate_inputs(repo, task)
        if task_id in cycles:
            record["status"] = "DEPENDENCY_CYCLE"
        elif task["classification"] not in {"D1", "D2"}:
            record["status"] = "PENDING_D3"
        elif task.get("authority_scope") != "EXPLICIT_AUTHORIZED_AUDIT_DESIGN_ONLY":
            record["status"] = "AUTHORITY_SCOPE_UNRESOLVED"
        elif failures:
            record.update(status="WAITING_EXACT_INPUTS", reasons=failures)
        elif completed[task_id]:
            record["status"] = "COMPLETED_ACCEPTED_OUTPUTS"
        elif replan_failure:
            record["status"] = replan_failure
        elif any(r.get("disposition") == "COMPLETED" for r in matching):
            record["status"] = "RECEIPT_VALIDATION_REQUIRED"
        elif task.get("state") == "WAITING_EXTERNAL":
            record["status"] = "WAITING_EXTERNAL"
        else:
            unmet = []
            for dep in task.get("dependencies", []):
                target = dep.get("task_id")
                receipt = completed.get(target)
                if (target not in by_id or receipt is None or
                        dep.get("task_fingerprint") != fingerprints.get(target) or
                        dep.get("output_digest") != output_digest(receipt)):
                    unmet.append(target)
            if unmet:
                record.update(status="WAITING_DEPENDENCY", dependencies=unmet)
            elif lease_conflict:
                record["status"] = "BLOCKED_ACTIVE_LEASE_NO_TAKEOVER"
            else:
                record["status"] = "EXECUTABLE_D1_D2"
        results.append(record)
    eligible = [r for r in results if r["status"] == "EXECUTABLE_D1_D2"]
    material = [e for e in (events or []) if e.get("material") and
                not e.get("self_control_only") and not e.get("already_disposed")]
    finite_ids = plan.get("finite_task_ids", plan.get("two_hop_task_ids", [t["id"] for t in tasks]))
    statuses = {r["task_id"]: r["status"] for r in results}
    terminal = bool(finite_ids) and all(statuses.get(i) == "COMPLETED_ACCEPTED_OUTPUTS"
                                      for i in finite_ids)
    unbound = [i for i in finite_ids if i not in by_id]
    return {
        "status": ("EXECUTABLE_STATE_WORK" if eligible else
                   "TERMINAL_D1_D2_COMPLETE_AWAITING_D3" if terminal else
                   "WAITING_NEXT_TASK_BINDING" if unbound else "NO_EXECUTABLE_TASK"),
        "next_task": eligible[0] if eligible else None,
        "tasks": results,
        "event_input_status": "MATERIAL_EVENTS_TO_REVIEW" if material else "NO_NEW_MATERIAL_EVENT",
        "state_input_status": "ELIGIBLE" if eligible else "WAIT_OR_TERMINAL",
        "unbound_finite_task_ids": unbound,
        "mutation_performed": False,
        "scheduler_execution_verified": False,
    }


def two_hop_receipt_readiness(repo: Path, state: dict, receipts: list[dict]) -> dict:
    """Checks structural evidence only; cannot authenticate scheduler readback.

    Deliberately never returns AUTONOMOUS_CONTINUATION_VERIFIED. The owner must
    independently verify two actual distinct platform scheduler executions.
    """
    plan = state.get("continuation_plan", {})
    ids = plan.get("two_hop_task_ids", [])
    tasks = {t["id"]: t for t in plan.get("tasks", [])}
    if len(ids) != 2 or any(i not in tasks for i in ids):
        return {"status": "TWO_HOP_PLAN_NOT_BOUND", "verified": False}
    accepted = []
    for task_id in ids:
        task = tasks[task_id]
        receipt = accepted_completion(repo, task, task_fingerprint(state["repository"], task), receipts)
        if receipt is None:
            return {"status": "REAL_EXECUTION_NOT_VERIFIED", "verified": False}
        execution = receipt.get("execution", {})
        if (execution.get("kind") != "PLATFORM_SCHEDULED" or
                not execution.get("automation_id") or not execution.get("platform_execution_id") or
                not execution.get("platform_readback_ref") or
                not execution.get("fresh_read_ref") or not execution.get("lease_evidence_ref")):
            return {"status": "REAL_EXECUTION_EVIDENCE_REQUIRED", "verified": False}
        accepted.append(receipt)
    run_ids = [r["execution"]["platform_execution_id"] for r in accepted]
    hop1 = accepted[0]
    if run_ids[0] == run_ids[1]:
        return {"status": "DISTINCT_SCHEDULER_EXECUTIONS_REQUIRED", "verified": False}
    expected_dep = {"task_id": ids[0], "task_fingerprint": hop1["task_fingerprint"],
                    "output_digest": output_digest(hop1)}
    if expected_dep not in tasks[ids[1]].get("dependencies", []):
        return {"status": "HOP2_EXACT_HOP1_BINDING_REQUIRED", "verified": False}
    return {"status": "TWO_HOP_RECEIPTS_READY_FOR_PLATFORM_VERIFICATION", "verified": False,
            "platform_execution_ids": run_ids,
            "limitation": "Read-only local probe cannot authenticate actual scheduler executions"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--receipts", type=Path, required=True)
    parser.add_argument("--events", type=Path)
    parser.add_argument("--lease-token", help="Read-only preview of own lease; never claims ownership")
    args = parser.parse_args()
    state = json.loads(args.state.read_text())
    receipts = [json.loads(p.read_text()) for p in sorted(args.receipts.glob("*.json"))]
    events = json.loads(args.events.read_text()) if args.events else []
    result = select(args.repo.resolve(), state, receipts, events, args.lease_token)
    result["two_hop"] = two_hop_receipt_readiness(args.repo.resolve(), state, receipts)
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
