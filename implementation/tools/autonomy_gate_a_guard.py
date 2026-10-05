#!/usr/bin/env python3
"""Fail-closed repository guard for Autonomous Execution SSoT v1.1 Gate A.

This guard does not grant autonomy by itself. It enforces:
- immutable Frozen artifacts cannot be modified/deleted/renamed;
- append-only records cannot rewrite or delete existing bytes;
- AUTONOMY_MODE is a single explicit state;
- operating values stay within the adopted CDR-024 configuration.

HG-02 still requires GitHub-side branch/ruleset enforcement.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
IMPLEMENTATION_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = IMPLEMENTATION_ROOT / "docs/coordination/governance/AUTONOMY_GUARD_CONFIG.v1.json"


class GuardError(RuntimeError):
    pass


def load_config(path: Path = CONFIG_PATH) -> dict:
    cfg = json.loads(path.read_text(encoding="utf-8"))
    expected = {"cycle_max_tasks": 5, "lease_ttl_seconds": 7200, "repair_round_cap": 3}
    if cfg.get("operating_values") != expected:
        raise GuardError(f"operating values drift: {cfg.get('operating_values')!r}")
    return cfg


def parse_name_status(raw: str) -> list[tuple[str, list[str]]]:
    out: list[tuple[str, list[str]]] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0]
        paths = parts[1:]
        if not paths:
            raise GuardError(f"invalid diff record: {line!r}")
        out.append((status, paths))
    return out


def _touches(path: str, cfg: dict) -> bool:
    if path in cfg["immutable_exact_paths"]:
        return True
    if path in cfg["append_only_exact_paths"]:
        return True
    return any(path.startswith(prefix) for prefix in cfg["append_only_prefixes"])


def classify_diff(records: list[tuple[str, list[str]]], cfg: dict) -> list[str]:
    violations: list[str] = []
    immutable = set(cfg["immutable_exact_paths"])
    append_files = set(cfg["append_only_exact_paths"])
    prefixes = tuple(cfg["append_only_prefixes"])

    for status, paths in records:
        code = status[0]
        old_path = paths[0]
        new_path = paths[-1]

        if old_path in immutable or new_path in immutable:
            if code in {"M", "D", "R", "C", "T"}:
                violations.append(f"immutable path changed: {status} {paths}")
            continue

        append_hit = (
            old_path in append_files
            or new_path in append_files
            or old_path.startswith(prefixes)
            or new_path.startswith(prefixes)
        )
        if append_hit and code in {"M", "D", "R", "C", "T"}:
            violations.append(f"append-only existing content changed: {status} {paths}")

    return violations


def git_name_status(base: str) -> str:
    proc = subprocess.run(
        ["git", "diff", "--name-status", f"{base}...HEAD"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode:
        raise GuardError(proc.stderr.strip() or "git diff failed")
    return proc.stdout


def validate_mode(cfg: dict) -> str:
    p = REPO_ROOT / cfg["autonomy_mode_file"]
    mode = p.read_text(encoding="utf-8").strip()
    if mode not in cfg["allowed_modes"]:
        raise GuardError(f"invalid AUTONOMY_MODE={mode!r}")
    return mode


def cmd_diff(base: str) -> int:
    cfg = load_config()
    mode = validate_mode(cfg)
    records = parse_name_status(git_name_status(base))
    violations = classify_diff(records, cfg)
    print(json.dumps({
        "mode": mode,
        "records": len(records),
        "violations": violations,
        "gate_a_repository_guard": "PASS" if not violations else "FAIL",
    }, ensure_ascii=False, indent=2))
    return 1 if violations else 0


def cmd_mode() -> int:
    cfg = load_config()
    mode = validate_mode(cfg)
    print(mode)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_diff = sub.add_parser("diff")
    p_diff.add_argument("--base", required=True)
    sub.add_parser("mode")
    args = parser.parse_args()
    try:
        if args.cmd == "diff":
            return cmd_diff(args.base)
        return cmd_mode()
    except (GuardError, OSError, json.JSONDecodeError) as exc:
        print(f"AUTONOMY_GUARD_FAIL: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
