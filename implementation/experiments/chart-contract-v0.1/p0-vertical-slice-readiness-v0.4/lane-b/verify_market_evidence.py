"""Read-only offline replay of the existing 19-symbol evidence, not production tests.

No network, package import, raw repair, timestamp substitution, or file writes.
Exact provider numeric tokens are retained; Decimal is only used for comparisons.
"""

# GSQ-010: this historical entrypoint is retired even if old paths reappear.
# Original algorithms remain below for provenance; no replay is authorized here.
import json as _cleanup_json
import sys as _cleanup_sys
print(_cleanup_json.dumps({"status": "NOT_AVAILABLE", "reason": "GSQ-010: archived inputs removed"}))
_cleanup_sys.exit(2)


from collections import Counter
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import subprocess


BASELINE = "581c61c4af859f6cbdc3418209bba9be7bbc76a3"
ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".git").exists())
BASE = "implementation/experiments/chart-contract-v0.1/"
IDENTITY = BASE + "p0-classification-review-v0.3/market-identity-time/"
BASIS = BASE + "p0-classification-review-v0.3/market-basis-anomalies/"
PREREQ = BASE + "p0-prerequisites/market/"
FIELDS = ("open", "high", "low", "close", "volume")
VERIFIED = {}


def read_json(path, tokens=False):
    options = {"parse_int": str, "parse_float": str} if tokens else {}
    return json.loads((ROOT / path).read_bytes(), **options)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check_bytes(path, expected_hash=None, expected_size=None):
    body = (ROOT / path).read_bytes()
    digest = hashlib.sha256(body).hexdigest()
    baseline = subprocess.run(
        ["git", "show", f"{BASELINE}:{path}"], cwd=ROOT,
        check=True, capture_output=True,
    ).stdout
    require(body == baseline, f"existing evidence differs from baseline: {path}")
    if expected_hash is not None:
        require(digest == expected_hash, f"hash mismatch: {path}")
    if expected_size is not None:
        require(len(body) == expected_size, f"byte-count mismatch: {path}")
    VERIFIED[path] = {"sha256": digest, "bytes": len(body), "baseline_bytes_match": True}


def number(token):
    return None if token is None else Decimal(token)


def main():
    inputs = [
        IDENTITY + "MARKET19_IDENTITY_TIME_READINESS.json",
        IDENTITY + "TIMESTAMP_AND_LISTING_COUNTEREXAMPLES.json",
        IDENTITY + "SOURCE_PIN_REPLAY.json",
        BASIS + "MARKET_BASIS_READINESS_19_v0.3.json",
        BASIS + "IMMUTABLE_RAW_ANOMALIES_v0.3.json",
        BASIS + "ACTION_ACQUISITION_PROBES_v0.3.json",
        BASIS + "TWO_OBSERVATIONS_COMPARISON_v0.3.json",
        PREREQ + "MARKET_REFERENCE_COVERAGE.json",
    ]
    for path in inputs:
        check_bytes(path)
    identity = read_json(inputs[0])
    cases = read_json(inputs[1])["cases"]
    basis = read_json(inputs[3])["rows"]
    anomalies = read_json(inputs[4])["rows"]
    action_map = {r["provider_symbol"]: r for r in read_json(inputs[5])["rows"]}
    comparison_map = {r["provider_symbol"]: r for r in read_json(inputs[6])["rows"]}
    coverage_map = {r["provider_symbol"]: r for r in read_json(inputs[7])["rows"]}
    identity_map = {r["provider_symbol"]: r for r in identity["rows"]}
    require(len(basis) == len(action_map) == len(identity_map) == 19, "19-symbol scope mismatch")
    for source in identity["sources"]:
        if source.get("status") == "CAPTURED":
            check_bytes(source["path"], source["sha256"], source["bytes"])

    originals, later, symbols, derived_anomalies = {}, {}, [], []
    total_differences = Counter()
    total_events = Counter()
    for record in basis:
        symbol = record["provider_symbol"]
        action = action_map[symbol]
        check_bytes(record["original_raw_path"], record["original_raw_sha256"])
        check_bytes(action["raw_path"], action["sha256"], action["bytes"])
        require(record["original_raw_sha256"] == identity_map[symbol]["raw_sha256"]
                == coverage_map[symbol]["raw_sha256"], f"cross-record hash mismatch: {symbol}")
        old = read_json(record["original_raw_path"], tokens=True)["chart"]["result"][0]
        new = read_json(action["raw_path"], tokens=True)["chart"]["result"][0]
        originals[symbol], later[symbol] = old, new
        stamps = old["timestamp"]
        require(stamps == new["timestamp"], f"timestamp changes: {symbol}")
        require(len(stamps) == record["prior_rows"] == coverage_map[symbol]["point_count"],
                f"row-count mismatch: {symbol}")
        require(list(map(int, stamps)) == sorted(set(map(int, stamps))), f"timestamp order: {symbol}")
        quote = old["indicators"]["quote"][0]
        new_quote = new["indicators"]["quote"][0]
        adjclose = old["indicators"]["adjclose"][0]["adjclose"]
        new_adjclose = new["indicators"]["adjclose"][0]["adjclose"]
        require(all(len(quote[field]) == len(stamps) == len(new_quote[field]) for field in FIELDS)
                and len(adjclose) == len(stamps) == len(new_adjclose), f"array lengths: {symbol}")
        missing, invalid, zero_volume = [], [], 0
        for index, timestamp in enumerate(stamps):
            values = {field: number(quote[field][index]) for field in FIELDS}
            if any(value is None for value in values.values()):
                missing.append(index)
                derived_anomalies.append((symbol, index, "SOURCE_NULL_OHLCV"))
                require(all(value is None for value in values.values()), f"unexpected partial-null row: {symbol}/{index}")
                continue
            require(all(value.is_finite() for value in values.values()) and values["volume"] >= 0,
                    f"non-finite/negative-volume row: {symbol}/{index}")
            zero_volume += values["volume"] == 0
            low, high = values["low"], values["high"]
            require(low <= values["open"] <= high, f"unexpected open-envelope failure: {symbol}/{index}")
            if not low <= values["close"] <= high:
                invalid.append(index)
                kind = "CLOSE_GT_HIGH" if values["close"] > high else "CLOSE_LT_LOW"
                derived_anomalies.append((symbol, index, kind))
        differences = {}
        for field in (*FIELDS, "adjclose"):
            before = adjclose if field == "adjclose" else quote[field]
            after = new_adjclose if field == "adjclose" else new_quote[field]
            differences[field] = sum(number(a) != number(b) for a, b in zip(before, after))
            total_differences[field] += differences[field]
        require(differences == comparison_map[symbol]["different_field_counts"], f"comparison replay: {symbol}")
        require(len(missing) == record["missing_ohlcv_rows"] and len(invalid) == record["exact_envelope_failure_rows"],
                f"structural replay: {symbol}")
        require(not any(field in old["meta"] for field in ("marketState", "exchangeDataDelayedBy", "quoteType")),
                f"quote-state premise changed: {symbol}")
        event_counts = {key: len(value) for key, value in (new.get("events") or {}).items()}
        require(event_counts == action.get("event_counts", {}), f"action count: {symbol}")
        total_events.update(event_counts)
        symbols.append({"provider_symbol": symbol, "rows": len(stamps),
                        "structural_ohlcv": "PARTIAL" if missing or invalid else "READY",
                        "missing_indices": missing, "invalid_ohlc_indices": invalid,
                        "zero_volume_rows": zero_volume, "adjclose_differences": differences["adjclose"],
                        "production_admission": "BLOCKED"})

    expected_anomalies = sorted((r["provider_symbol"], r["original_row_index"], r["anomaly_types"][0]) for r in anomalies)
    require(sorted(derived_anomalies) == expected_anomalies and len(anomalies) == 5, "exact anomaly set mismatch")
    for anomaly in anomalies:
        symbol, index = anomaly["provider_symbol"], anomaly["original_row_index"]
        original, comparison = originals[symbol], later[symbol]
        require(int(original["timestamp"][index]) == anomaly["bar_timestamp_numeric"], "anomaly timestamp mismatch")
        require({field: original["indicators"]["quote"][0][field][index] for field in FIELDS}
                == anomaly["raw_numeric_tokens"], "anomaly token mismatch")
        require(original["indicators"]["adjclose"][0]["adjclose"][index] == anomaly["raw_adjclose_token"],
                "anomaly adjclose token mismatch")
        require({field: comparison["indicators"]["quote"][0][field][index] for field in FIELDS}
                == anomaly["latest_comparison_values"], "comparison anomaly token mismatch")
        require(anomaly["cause"] == "UNKNOWN" and anomaly["raw_preservation"] == "UNCHANGED"
                and anomaly["production_rule_adoption"] is False, "anomaly semantics changed")
    for case in cases:
        if case["kind"] == "BAR_LABEL_NOT_ACTUAL_SESSION_OPEN":
            require(int(originals[case["symbol"]]["timestamp"][case["raw_index"]]) == case["raw_timestamp"],
                    "KRX dated-session counterexample mismatch")
        else:
            for row in case["pre_regular_way_rows"]:
                require(int(originals[case["symbol"]]["timestamp"][row["raw_index"]]) == row["timestamp"],
                        "GEV when-issued candidate mismatch")

    require(sum(row["rows"] for row in symbols) == 23155, "preserved row scope mismatch")
    require(total_differences["adjclose"] == 10862 and sum(total_differences[f] for f in FIELDS) == 0,
            "cross-observation scope mismatch")
    return {"kind": "LANE_B_OFFLINE_IMMUTABLE_EVIDENCE_REPLAY_V04", "baseline": BASELINE,
            "result": "PASS", "network_requests": 0, "source_file_writes": 0,
            "production_tests": "NOT_RUN", "chart_fpia": "NOT_RUN",
            "summary": {"symbols": 19, "rows": 23155,
                        "source_structural_ohlcv": dict(Counter(r["structural_ohlcv"] for r in symbols)),
                        "production_admission": {"BLOCKED": 19, "READY": 0},
                        "anomalies": 5, "original_and_actions_payload_hashes": 38,
                        "captured_identity_session_source_hashes": 22,
                        "input_record_hashes": len(inputs), "different_field_counts": dict(total_differences),
                        "provider_action_candidates": dict(total_events)},
            "symbols": symbols, "verified_existing_files": VERIFIED}


if __name__ == "__main__":
    print(json.dumps(main(), ensure_ascii=False, indent=2))
