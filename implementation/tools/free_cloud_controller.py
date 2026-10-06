#!/usr/bin/env python3
"""Zero-paid-resource GitHub Actions controller for Investment-System1.

Purpose:
- PC 없이 GitHub-hosted Actions에서 실행
- 유료 AI/API 호출 없음
- AUTONOMY_MODE, Gate A, runtime state를 fail-closed 판정
- 현재 단계에서는 deterministic control-plane only
- Gate A OPEN 전에는 mutation 실행을 절대 허용하지 않음

This module intentionally does not call network APIs itself. GitHub event/workflow
provides fresh repository contents and this controller emits a machine-readable
decision for later bounded executor jobs.
"""

from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GOV = ROOT / "implementation/docs/coordination/governance"
MODE = GOV / "AUTONOMY_MODE"
GAPS = GOV / "AUTONOMY_HARD_GUARD_GAPS_v1.1.md"
STATE = GOV / "AUTONOMY_RUNTIME_STATE.json"


def read_mode() -> str:
    mode = MODE.read_text(encoding="utf-8").strip()
    if mode not in {"RUN", "PAUSE", "READ_ONLY"}:
        return "INVALID"
    return mode


def gate_a_open() -> bool:
    text = GAPS.read_text(encoding="utf-8")
    # Fail closed: only an explicit OPEN marker is accepted.
    return "Gate A: **OPEN" in text


def runtime_idle() -> bool:
    raw = json.loads(STATE.read_text(encoding="utf-8"))
    return raw.get("status") == "IDLE"


def decision() -> dict:
    mode = read_mode()
    gate_open = gate_a_open()
    idle = runtime_idle()

    if mode != "RUN":
        return {
            "allow_mutation": False,
            "reason": f"AUTONOMY_MODE_{mode}",
            "mode": mode,
            "gate_a_open": gate_open,
            "runtime_idle": idle,
            "execution_class": "READ_ONLY_CONTROL_PLANE",
        }
    if not gate_open:
        return {
            "allow_mutation": False,
            "reason": "GATE_A_CLOSED",
            "mode": mode,
            "gate_a_open": gate_open,
            "runtime_idle": idle,
            "execution_class": "READ_ONLY_CONTROL_PLANE",
        }
    if not idle:
        return {
            "allow_mutation": False,
            "reason": "ACTIVE_RUNTIME_STATE",
            "mode": mode,
            "gate_a_open": gate_open,
            "runtime_idle": idle,
            "execution_class": "READ_ONLY_CONTROL_PLANE",
        }

    return {
        "allow_mutation": True,
        "reason": "BOUNDED_EXECUTOR_ELIGIBLE",
        "mode": mode,
        "gate_a_open": gate_open,
        "runtime_idle": idle,
        "execution_class": "DETERMINISTIC_D1_D2_D3A_ONLY",
    }


if __name__ == "__main__":
    print(json.dumps(decision(), ensure_ascii=False, sort_keys=True))
