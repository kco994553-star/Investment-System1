"""Offline read-only audit; no package imports, workflows or production checks.

Run from the repository root. The generated verification uses exclusive create;
it cannot replace a previous receipt. Captured sources are never rewritten.
"""

# GSQ-010: retained historical algorithm; removed inputs cannot be replayed.
from pathlib import Path as _CleanupPath
import json as _cleanup_json
import sys as _cleanup_sys
_cleanup_root = next(p for p in _CleanupPath(__file__).resolve().parents if p.name == "implementation").parent
_cleanup_removed_inputs = ['implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-basis-anomalies/IMMUTABLE_RAW_ANOMALIES_v0.3.json']
if any(not (_cleanup_root / p).is_file() for p in _cleanup_removed_inputs):
    print(_cleanup_json.dumps({"status": "NOT_AVAILABLE", "reason": "GSQ-010: archived inputs removed"}))
    _cleanup_sys.exit(2)

import hashlib
import json
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path.cwd()
BASE = "54ee25446ccf6cfa32ddf164a8ed31b7e1036b9a"
AREA = Path("implementation/experiments/chart-contract-v0.1/p0-classification-review-v0.3")
checks = {}


def check(name, value):
    checks[name] = bool(value)
    if not value:
        raise AssertionError(name)


def read(name):
    return json.loads((AREA / name).read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args):
    return subprocess.check_output(["git", *args])


identity = read("market-identity-time/MARKET19_IDENTITY_TIME_READINESS.json")
basis = read("market-basis-anomalies/MARKET_BASIS_READINESS_19_v0.3.json")
anomalies = read("market-basis-anomalies/IMMUTABLE_RAW_ANOMALIES_v0.3.json")
comparison = read("market-basis-anomalies/TWO_OBSERVATIONS_COMPARISON_v0.3.json")
actions = read("market-basis-anomalies/CURRENT_ACTION_EVENT_CANDIDATES_v0.3.json")
portfolio = read("portfolio-architecture/EVIDENCE.json")
check("no_existing_tracked_file_changed", not git("diff", BASE, "--"))
untracked = [p.decode() for p in git("ls-files", "--others", "--exclude-standard", "-z").split(b"\0") if p]
check("only_authorized_new_folder", all(p.startswith(AREA.as_posix() + "/") for p in untracked))
check("nineteen_same_unique_symbols", len(identity["rows"]) == len(basis["rows"]) == 19 and
      {r["provider_symbol"] for r in identity["rows"]} == {r["provider_symbol"] for r in basis["rows"]})
check("identity_raw_hashes_19", all(sha(ROOT / r["raw_path"]) == r["raw_sha256"] for r in identity["rows"]))
check("basis_original_hashes_19", all(sha(ROOT / r["original_raw_path"]) == r["original_raw_sha256"] for r in basis["rows"]))
check("all_production_admission_blocked", all(r["production_admission"] == "BLOCKED" for r in identity["rows"]) and
      all(r["production_ready"] == "BLOCKED" for r in basis["rows"]))
check("source_structure_17_ready_2_partial", Counter(r["source_ohlcv_state"] for r in basis["rows"]) == {"READY": 17, "PARTIAL": 2})
check("no_certified_historical_availability_or_quote_state", all(r["historical_price_available_at"] == "NOT_AVAILABLE" and
      r["quote_state"] == "UNKNOWN" for r in basis["rows"]))

# Recalculate all original raw row facts, using exact JSON decimal tokens.
row_count = missing = envelope_failures = 0
raw_by_path = {}
for r in basis["rows"]:
    p = r["original_raw_path"]
    raw = json.loads((ROOT / p).read_text(), parse_float=Decimal, parse_int=Decimal)
    raw_by_path[p] = raw
    result = raw["chart"]["result"][0]
    quote = result["indicators"]["quote"][0]
    times = result["timestamp"]
    check("equal_array_lengths_" + r["provider_symbol"], all(len(quote[k]) == len(times) for k in ("open", "high", "low", "close", "volume")))
    row_count += len(times)
    for i in range(len(times)):
        o, h, l, c, v = (quote[k][i] for k in ("open", "high", "low", "close", "volume"))
        if any(x is None for x in (o, h, l, c, v)):
            missing += 1
        else:
            check("finite_nonnegative_volume_" + r["provider_symbol"], all(x.is_finite() for x in (o, h, l, c, v)) and v >= 0)
            if not (l <= o <= h and l <= c <= h):
                envelope_failures += 1
check("raw_rows_missing_envelope_counts", (row_count, missing, envelope_failures) == (23155, 1, 4))
check("five_exact_anomaly_records", len(anomalies["rows"]) == 5 and all(r["cause"] == "UNKNOWN" for r in anomalies["rows"]))
for r in anomalies["rows"]:
    q = raw_by_path[r["original_raw_path"]]["chart"]["result"][0]["indicators"]["quote"][0]
    check("anomaly_exact_tokens_" + r["anomaly_id"], all(
        q[k][r["original_row_index"]] is None if token is None else
        q[k][r["original_row_index"]] == Decimal(token)
        for k, token in r["raw_numeric_tokens"].items()))
check("comparison_ohlcv_unchanged", all(all(r["different_field_counts"][k] == 0 for k in ("open", "high", "low", "close", "volume")) for r in comparison["rows"]))
check("adjclose_10862_exact_differences", sum(r["different_field_counts"]["adjclose"] for r in comparison["rows"]) == 10862)
check("actions_283_dividend_9_split_candidates", (actions["dividend_count"], actions["split_count"]) == (283, 9))

reference = json.loads(Path("implementation/experiments/chart-contract-v0.1/portfolio_reference.json").read_text())
units = Counter()
for r in reference["holdings"]:
    units[r["industry"]] += r["weight_units"]
check("preserved_19_reference_rows_theme_partition", len(reference["holdings"]) == 19 and
      dict(units) == {"반도체 장비": 3000, "AI·반도체": 2500, "Big Tech": 2000, "기타산업": 2500})
check("reference_no_inferred_security_or_types", all(r["security_id"] is None and r["types"] is None for r in reference["holdings"]))
check("requirements_81_24_8", portfolio["scope_counts"] == {"core": 81, "extended": 24, "research_candidate": 8})
check("all_pinned_source_bytes_match", all(hashlib.sha256(git("show", r["head"] + ":" + r["path"])).hexdigest() == r["sha256"] for r in portfolio["source_pins"]))

files = sorted(p for p in AREA.rglob("*") if p.is_file())
check("no_compiled_python_artifacts", not any("__pycache__" in p.parts or p.suffix == ".pyc" for p in files))
check("new_python_only_nonpackage_audit", all(not str(p).startswith("implementation/src/") for p in files if p.suffix == ".py"))
for p in files:
    if p.suffix == ".json":
        json.loads(p.read_text())
check("all_new_json_parses", True)
for p in (AREA / "P0_MARKET_AND_PORTFOLIO_CLASSIFICATION_REVIEW_v0.3.md", AREA / "CHARTDOCUMENT_v0.2_PROPOSAL.md"):
    for target in re.findall(r"\]\(([^)]+)\)", p.read_text()):
        if not target.startswith(("https:", "http:")):
            check("relative_link_" + target, (p.parent / target).exists())

receipt = {
    "kind": "OFFLINE_AUDIT_REPLAY_NOT_PRODUCTION_CERTIFICATION",
    "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    "source_head": BASE,
    "checks": checks,
    "summary": {"raw_rows": row_count, "missing": missing, "ohlc_envelope_failures": envelope_failures,
                "adjclose_exact_cross_request_differences": 10862, "requirements": portfolio["scope_counts"]},
    "immutable_new_artifact_manifest": [{"path": p.as_posix(), "bytes": p.stat().st_size, "sha256": sha(p)} for p in files],
    "manifest_scope": "All completed checkpoint artifacts except this newly created receipt itself; no self-hash.",
    "production_tests": "NOT_RUN", "chart_fpia": "NOT_RUN", "runtime_imports": False,
    "canonical_merge": False, "grant": False, "official_live_promotion": False,
}
with (AREA / "CHECKPOINT_VERIFICATION.json").open("x", encoding="utf-8") as f:
    json.dump(receipt, f, ensure_ascii=False, indent=2)
    f.write("\n")
print(json.dumps({"checks_passed": len(checks), "artifacts": len(files), "bytes": sum(p.stat().st_size for p in files), "summary": receipt["summary"]}, ensure_ascii=False))
