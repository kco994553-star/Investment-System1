"""Offline verification of new evidence sidecars against existing immutable bytes.

No acquisition, source writes, production admission or production test claim.
Run from anywhere: python -B <this file>. The receipt is printed to stdout.
"""
from __future__ import annotations

# GSQ-010: retained historical algorithm; removed inputs cannot be replayed.
from pathlib import Path as _CleanupPath
import json as _cleanup_json
import sys as _cleanup_sys
_cleanup_root = next(p for p in _CleanupPath(__file__).resolve().parents if p.name == "implementation").parent
_cleanup_removed_inputs = ['implementation/experiments/chart-contract-v0.1/p0-slice-owner-closure-v0.5/lane-b/IMMUTABLE_MARKET_ADMISSION_CASES_v0.5.json', 'implementation/reports/gate_evidence/ca_unit_policy_v1.json']
if any(not (_cleanup_root / p).is_file() for p in _cleanup_removed_inputs):
    print(_cleanup_json.dumps({"status": "NOT_AVAILABLE", "reason": "GSQ-010: archived inputs removed"}))
    _cleanup_sys.exit(2)


import ast
from collections import Counter
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
CHECKS = []


def check(ok, label):
    if not ok:
        raise AssertionError(label)
    CHECKS.append(label)


def sha(body):
    return hashlib.sha256(body).hexdigest()


def read(name):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def git_bytes(commit, path):
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)


def declared_symbols(body):
    tree = ast.parse(body.decode("utf-8"))
    names = set()
    for node in tree.body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            names.add(node.name)
        if isinstance(node, ast.ClassDef):
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    names.add(f"{node.name}.{child.name}")
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            names.update(target.id for target in targets if isinstance(target, ast.Name))
    return names


def main():
    pins = read("EXISTING_CAPABILITY_PINS_v0.5.json")
    actions = read("MARKET_OWNER_ACTIONS_v0.5.json")
    cases = read("IMMUTABLE_MARKET_ADMISSION_CASES_v0.5.json")
    check(len(pins["capabilities"]) == 18 and len(pins["evidence_sources"]) == 11,
          "18 capability pins and11 existing evidence pins")
    for entry in pins["capabilities"]:
        src = entry["source"]
        body = git_bytes(src["commit"], src["path"])
        check(sha(body) == src["sha256"] and len(body) == src["bytes"],
              f"pinned capability bytes:{entry['capability_id']}")
        check(set(entry["symbols_or_scope"]) <= declared_symbols(body),
              f"exact existing symbols:{entry['capability_id']}")
        for role, head in pins["baselines"].items():
            result = subprocess.run(["git", "show", f"{head}:{src['path']}"], cwd=ROOT, capture_output=True)
            expected = entry["tree_presence"][role]
            check((result.returncode == 0) == expected["present"] and
                  (sha(result.stdout) if result.returncode == 0 else None) == expected["sha256"],
                  f"presence/hash:{entry['capability_id']}:{role}")
    for src in pins["evidence_sources"]:
        body = git_bytes(src["commit"], src["path"])
        check(sha(body) == src["sha256"] and len(body) == src["bytes"],
              f"pinned existing source:{src['path']}")
    by_id = {entry["capability_id"]: entry for entry in pins["capabilities"]}
    for cid in ["I01", "I03", "P01"]:
        check(len({v["sha256"] for v in by_id[cid]["tree_presence"].values()}) == 1,
              f"unchanged canonical/common capability:{cid}")
    for cid in ["S01", "S02", "S03", "S04"]:
        present = by_id[cid]["tree_presence"]
        check(not present["chart"]["present"] and not present["canonical"]["present"] and
              present["session_pr18"]["sha256"] == present["integration_pr42"]["sha256"],
              f"session exists only in owner/integration tree, exact parity:{cid}")
    guard = git_bytes(pins["baselines"]["session_pr18"], by_id["S04"]["source"]["path"]).decode()
    binder = git_bytes(pins["baselines"]["session_pr18"], by_id["S03"]["source"]["path"]).decode()
    check('"provider_publication_timestamp": False' in guard and
          '"observed_at_overwritten": False' in guard and
          '"CANONICAL_SESSION_CLOSE_LOWER_BOUND"' in guard and
          "eligible=decision_time >= row.close_utc" in binder,
          "owner guard explicitly lower bound, not provider publication")
    matrix_ref = actions["prior_matrix_ref"]
    matrix_bytes = (ROOT / matrix_ref["path"]).read_bytes()
    check(sha(matrix_bytes) == matrix_ref["sha256"], "prior matrix unchanged")
    matrix = json.loads(matrix_bytes)
    expected = [{"provider_symbol": x["provider_symbol"], "row_count": x["row_count"],
                 "raw_source": {"path": x["raw_path"], "sha256": x["raw_sha256"]},
                 "fields": {k: v["status"] for k, v in x["fields"].items()},
                 "production_admission": x["production_admission"]} for x in matrix["rows"]]
    check(actions["unchanged_field_states"] == expected, "all19×8 statuses unchanged")
    check(len(actions["actions"]) == 8 and len(expected) == 19 and
          sum(x["row_count"] for x in expected) == 23155 and
          actions["shared_evidence_gap_families"] == 8 and actions["non_ready_field_cells"] == 152,
          "19symbols/23155rows/8families/152nonready scope")
    raw = {}
    for record in matrix["rows"]:
        body = (ROOT / record["raw_path"]).read_bytes()
        check(sha(body) == record["raw_sha256"] and body == git_bytes(actions["baseline"], record["raw_path"]),
              f"original raw bytes unchanged:{record['provider_symbol']}")
        data = json.loads(body, parse_float=Decimal)["chart"]["result"][0]
        check(len(data["timestamp"]) == record["row_count"], f"raw count:{record['provider_symbol']}")
        raw[record["provider_symbol"]] = data
    check(all(action["status"] == "OWNER_ACTION_REQUIRED" and action["promotions_this_stage"] == 0
              for action in actions["actions"]), "no source admission authority generated")
    check(len(cases["cases"]) == 6 and sum(len(x["points"]) for x in cases["cases"]) == 10,
          "six bounded raw-reference cases, ten points")
    for case in cases["cases"]:
        data = raw[case["provider_symbol"]]
        body = (ROOT / case["source"]["path"]).read_bytes()
        check(sha(body) == case["source"]["sha256"] and len(body) == case["source"]["bytes"],
              f"reference-case source hash:{case['case_id']}")
        quote = data["indicators"]["quote"][0]
        adj = data["indicators"]["adjclose"][0]["adjclose"]
        for point in case["points"]:
            idx = point["index"]
            values = {key: None if quote[key][idx] is None else str(quote[key][idx])
                      for key in ["open", "high", "low", "close", "volume"]}
            check(data["timestamp"][idx] == point["bar_timestamp"] and values == point["decimal_text"] and
                  (None if adj[idx] is None else str(adj[idx])) == point["adjclose_decimal_text"],
                  f"case exact point:{case['case_id']}:{idx}")
        binding = case["required_owner_binding"]
        check(all(binding[k] is None for k in ["issuer_id", "security_id", "listing_id", "calendar_id", "historical_available_at"])
              and binding["quote_state"] == "UNKNOWN" and binding["admission"] == "BLOCKED",
              f"case retains unadmitted inputs:{case['case_id']}")
    policy = json.loads((ROOT / "implementation/reports/gate_evidence/ca_unit_policy_v1.json").read_text())
    event = next(e for e in policy["events"] if e["symbols"] == ["NVDA"])
    document = event["documents"][0]
    check(sha((ROOT / "implementation/reports/gate_evidence" / document["bundled_path"]).read_bytes()) == document["sha256"],
          "existing NVDA primary source matches approved event pin")
    replay = ROOT / "implementation/experiments/chart-contract-v0.1/p0-vertical-slice-readiness-v0.4/lane-b/verify_market_evidence.py"
    result = subprocess.run([sys.executable, "-B", str(replay)], cwd=ROOT, capture_output=True, text=True, check=True)
    prior = json.loads(result.stdout)
    check(prior["result"] == "PASS" and prior["summary"]["anomalies"] == 5 and
          prior["summary"]["rows"] == 23155 and len(prior["verified_existing_files"]) == 68,
          "prior68-file replay PASS incl5 original anomalies")
    return {"kind": "LANE_B_EXISTING_CAPABILITY_EVIDENCE_VERIFICATION_V05", "result": "PASS",
            "baseline": actions["baseline"], "check_count": len(CHECKS), "checks": CHECKS,
            "network_requests": 0, "source_file_writes": 0, "admission_promotions": 0,
            "production_tests": "NOT_RUN", "chart_merge_result_fpia": "NOT_RUN",
            "prior_replay_summary": prior["summary"], "prior_verified_existing_file_count": 68,
            "production_admission": {"READY": 0, "BLOCKED": 19},
            "shared_gap_families": 8, "non_ready_field_cells": 152}


if __name__ == "__main__":
    print(json.dumps(main(), ensure_ascii=False, indent=2))
