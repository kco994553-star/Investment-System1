#!/usr/bin/env python3
"""Validate the only admissible future zero-paid automation write surface.

This is a pure validator. It never writes GitHub.
"""

from __future__ import annotations
import argparse
import json

ALLOWED_BRANCH="automation/free-cloud-state-v1"
ALLOWED_PATHS={"implementation/docs/coordination/automation_free/FREE_CLOUD_STATUS.json"}
FORBIDDEN_PREFIXES=(
    "implementation/docs/coordination/COORDINATION_DECISION_REGISTER.md",
    "implementation/docs/coordination/GLOBAL_CURRENT_HANDOFF.md",
    "implementation/docs/coordination/GLOBAL_STATUS_INDEX.md",
    "implementation/docs/coordination/governance/",
)
FORBIDDEN_BRANCHES={
    "integration/global-handoff-v1",
    "claude/investment-system-top500-validation-alrugm",
}

def validate(branch:str, paths:list[str])->dict:
    reasons=[]
    if branch != ALLOWED_BRANCH:
        reasons.append("branch_not_allowed")
    if branch in FORBIDDEN_BRANCHES:
        reasons.append("protected_branch")
    if not paths:
        reasons.append("empty_write_set")
    for p in paths:
        if p not in ALLOWED_PATHS:
            reasons.append(f"path_not_allowed:{p}")
        if any(p.startswith(x) for x in FORBIDDEN_PREFIXES):
            reasons.append(f"protected_path:{p}")
    return {
        "allowed": not reasons,
        "branch": branch,
        "paths": paths,
        "reasons": reasons,
    }

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--branch",required=True)
    ap.add_argument("--path",action="append",dest="paths",required=True)
    ns=ap.parse_args()
    result=validate(ns.branch,ns.paths)
    print(json.dumps(result,ensure_ascii=False,sort_keys=True))
    return 0 if result["allowed"] else 2

if __name__=="__main__":
    raise SystemExit(main())
