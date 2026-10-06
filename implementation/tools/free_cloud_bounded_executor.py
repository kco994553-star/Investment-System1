#!/usr/bin/env python3
"""Bounded deterministic executor for zero-paid GitHub-hosted automation.

This executor deliberately has no LLM. It may only produce a deterministic
action plan from repository state. Repository mutation is performed by the
workflow only after this process returns allow_mutation=true, and the workflow
itself constrains writes to one dedicated automation path/branch.

This is a control-plane executor, not a replacement for Main GPT reasoning.
"""

from __future__ import annotations
import json
from pathlib import Path
import importlib.util
import sys

ROOT = Path(__file__).resolve().parents[2]
CTRL_PATH = ROOT / "implementation/tools/free_cloud_controller.py"
OUT = ROOT / "implementation/docs/coordination/automation_free/FREE_CLOUD_STATUS.json"

def _load_controller():
    spec=importlib.util.spec_from_file_location("free_cloud_controller", CTRL_PATH)
    mod=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod

def build_plan() -> dict:
    ctl=_load_controller()
    d=ctl.decision()
    plan={
        "schema":"free-cloud-bounded-executor-plan-v1",
        "allow_mutation":bool(d["allow_mutation"]),
        "reason":d["reason"],
        "execution_class":d["execution_class"],
        "allowed_branch":"automation/free-cloud-state-v1",
        "allowed_paths":[
            "implementation/docs/coordination/automation_free/FREE_CLOUD_STATUS.json"
        ],
        "forbidden":[
            "canonical",
            "integration/global-handoff-v1",
            "Official/LIVE",
            "Holdout",
            "paid API",
            "financial credentials",
            "trade/order/fund movement",
            "methodology/numeric policy"
        ],
    }
    return plan

if __name__=="__main__":
    print(json.dumps(build_plan(),ensure_ascii=False,sort_keys=True))
