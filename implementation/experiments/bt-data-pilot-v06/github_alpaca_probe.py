"""Bounded GitHub-secret Alpaca probe. Raw data goes only to a private release.

No trading API, secret extraction, public artifacts, factor calculation or BT.
Transport, raw store, numeric validation and private release helpers are reused.
"""
from __future__ import annotations

import argparse
from datetime import datetime, time
import json
import os
from pathlib import Path
import sys
import time as clock
from urllib.parse import urlencode
import zipfile
from zoneinfo import ZoneInfo

from pilot import private_dir, encoded, digest, put_once, normalize_tiingo, acquire, RawDatasetStore, ROOT
sys.path.insert(0, str(ROOT / "tools"))
import raw_store_release as release

RAW_REPO = "kco994553-star/investment-system1-raw"
NY = ZoneInfo("America/New_York")
PRIMARY_DAYS = ["2016-03-28", "2016-03-29", "2016-03-30", "2016-03-31", "2016-04-01"]
EVENT_DAYS = ["2024-06-07", "2024-06-10", "2024-06-11", "2024-06-12"]


def plan():
    # Four user-added diagnostics do not replace the original fixed ten companies.
    requests = [dict(symbol=symbol, feed=feed, adjustment="raw", days=PRIMARY_DAYS,
                     cohort="FIXED10_STAGE_A" if symbol == "ABT" else "USER_ADDITIONAL4")
                for symbol in ("ABT", "AAPL", "MSFT", "NVDA", "ASML") for feed in ("iex", "sip")]
    requests += [dict(symbol="NVDA", feed=feed, adjustment=adjustment, days=EVENT_DAYS,
                      cohort="SPLIT_WINDOW_DIAGNOSTIC")
                 for feed in ("iex", "sip") for adjustment in ("raw", "split")]
    return requests


def normalize(body, request):
    data = json.loads(body)
    if (data.get("symbol") != request["symbol"] or "bars" not in data
            or (data["bars"] is not None and not isinstance(data["bars"], list))):
        raise ValueError("SYMBOL_OR_SCHEMA")
    if data.get("next_page_token"):
        raise ValueError("UNEXPECTED_PAGINATION_IN_BOUNDED_PROBE")
    mapped, originals = [], {}
    # Alpaca returns bars:null for a valid, authenticated window with no data.
    # Keep the original bytes; normalize this explicit empty response to zero rows.
    for row in data["bars"] or []:
        at = datetime.fromisoformat(row["t"].replace("Z", "+00:00"))
        if at.tzinfo is None:
            raise ValueError("NAIVE_BAR_TIMESTAMP")
        day = at.astimezone(NY).date().isoformat()
        if day not in request["days"]:
            raise ValueError("UNEXPECTED_SESSION")
        originals[day] = row
        mapped.append({"date": day, **{name: row.get(key) for name, key in
                       zip(("open", "high", "low", "close", "volume"), ("o", "h", "l", "c", "v"))}})
    rows = normalize_tiingo(encoded(mapped), request["symbol"], "USD")
    for row in rows:
        observed = row["raw"]
        row.update(provider="ALPACA", feed=request["feed"], provider_payload=originals[row["session_date"]],
                   currency_evidence="US_EQUITY_ENDPOINT_SCOPE_NOT_RESPONSE_FIELD",
                   timestamp_semantics="BAR_PERIOD_START_NOT_PUBLICATION_TIME",
                   corporate_actions_verified=False, execution_open_verified=False,
                   historical_security_identity_verified=False, v_input_ready=False)
        if request["adjustment"] == "split":
            row.update(price_basis="SPLIT_ADJUSTED", observed=observed,
                       raw={k: None for k in observed},
                       adjusted={"adj" + k.title(): v for k, v in observed.items()})
    return rows


def summary_for(rows, request):
    values = [r["raw"] if request["adjustment"] == "raw" else r["observed"] for r in rows]
    missing = {k: sum(v[k] is None for v in values) for k in ("open", "high", "low", "close", "volume")}
    missing_dates = sorted(set(request["days"]) - {r["session_date"] for r in rows})
    return {"symbol": request["symbol"], "cohort": request["cohort"], "feed": request["feed"],
            "adjustment": request["adjustment"], "rows": len(rows), "expected_sessions": len(request["days"]),
            "date_min": min((r["session_date"] for r in rows), default=None),
            "date_max": max((r["session_date"] for r in rows), default=None),
            "missing_dates": missing_dates, "missing_day_rate": len(missing_dates) / len(request["days"]),
            "missing_fields": missing, "complete_ohlcv": bool(rows) and not missing_dates and not any(missing.values()),
            "ledger_ready": False, "v_input_ready": False}


def collect(output):
    names = ("APCA_API_KEY_ID", "APCA_API_SECRET_KEY", "RAW_REPO_TOKEN")
    presence = {name: bool(os.environ.get(name)) for name in names}
    if not all(presence.values()):
        return {"status": "SECRET_BINDING_MISSING", "configured": presence, "market_data_requests": 0}
    if os.environ.get("GITHUB_ACTIONS") != "true":
        return {"status": "GITHUB_RUNNER_REQUIRED", "market_data_requests": 0}
    # Never collect data if its designated destination cannot be verified private.
    status, _, body = release.http("GET", f"{release.API}/repos/{RAW_REPO}")
    if status != 200 or json.loads(body).get("private") is not True:
        return {"status": "PRIVATE_STORAGE_PREFLIGHT_FAILED", "http_status": status, "market_data_requests": 0}
    root = private_dir(output)
    store = RawDatasetStore(root / "store")
    (root / "normalized").mkdir(exist_ok=True, mode=0o700)
    (root / "requests").mkdir(exist_ok=True, mode=0o700)
    headers = {"APCA-API-KEY-ID": os.environ["APCA_API_KEY_ID"],
               "APCA-API-SECRET-KEY": os.environ["APCA_API_SECRET_KEY"]}
    results, comparison_rows, attempted = [], {}, 0
    for request in plan():
        start = datetime.combine(datetime.fromisoformat(request["days"][0]).date(), time.min, NY)
        end = datetime.combine(datetime.fromisoformat(request["days"][-1]).date(), time.max, NY)
        params = dict(timeframe="1Day", start=start.isoformat(), end=end.isoformat(),
                      feed=request["feed"], adjustment=request["adjustment"], asof="-", sort="asc", limit=1000)
        aid = ":".join(("alpaca_v06", request["symbol"], request["feed"], request["adjustment"],
                        request["days"][0], request["days"][-1]))
        url = "https://data.alpaca.markets/v2/stocks/" + request["symbol"] + "/bars?" + urlencode(params)
        attempted += int(not store.has(aid))
        body, receipt = acquire(store, aid, url, "ALPACA_STOCK_BARS_JSON", headers)
        put_once(root / "requests" / (aid.replace(":", "_") + ".json"), encoded({
            "request": request, "arguments": params, "receipt": receipt,
            "provider_published_at": None, "assumed_available_at": None}))
        if body is None:
            code = receipt.get("http_status")
            results.append({"symbol": request["symbol"], "feed": request["feed"],
                "cohort": request["cohort"], "adjustment": request["adjustment"], "http_status": code,
                "status": {401: "AUTHENTICATION_REJECTED", 403: "ENTITLEMENT_OR_PERMISSION_REJECTED",
                           429: "RATE_LIMITED"}.get(code, "HTTP_REQUEST_FAILED" if code else "NETWORK_REQUEST_FAILED"),
                "missing_day_rate": None})
            if code in (401, 429):
                break
        else:
            try:
                rows = normalize(body, request)
                # Same raw bytes from two feeds must retain different provenance.
                normalized_key = digest(encoded({"raw_sha256": digest(body), "request": request}))
                put_once(root / "normalized" / (normalized_key + ".json"), encoded(rows))
                results.append({"status": "ACQUIRED" if rows else "REQUESTED_DATA_ABSENT",
                                "http_status": receipt.get("http_status"), **summary_for(rows, request)})
                comparison_rows[(request["symbol"], request["feed"], request["adjustment"], request["days"][0])] = rows
            except (ValueError, KeyError, TypeError):
                # No provider body or exception text can enter the public log.
                results.append({"symbol": request["symbol"], "feed": request["feed"],
                                "adjustment": request["adjustment"], "status": "RESPONSE_QUALITY_FAILED",
                                "missing_day_rate": None})
        clock.sleep(0.35)  # <= 172 calls/minute before network time; no paid rate tier.
    # Preserve raw and adjusted independently; ratios are NOT authoritative event records.
    comparisons = []
    for feed in ("iex", "sip"):
        raw = comparison_rows.get(("NVDA", feed, "raw", EVENT_DAYS[0]), [])
        adjusted = comparison_rows.get(("NVDA", feed, "split", EVENT_DAYS[0]), [])
        by_day = {r["session_date"]: r for r in adjusted}
        paired = [r for r in raw if r["session_date"] in by_day]
        comparisons.append({"feed": feed, "paired_sessions": len(paired),
            "raw_differs_from_split_adjusted_sessions": sum(
                r["raw"]["close"] != by_day[r["session_date"]]["observed"]["close"] for r in paired),
            "event_validated": False, "reason": "REQUIRES_INDEPENDENT_EVENT_RECORD"})
    report = {"version": "BT-DATA-PILOT v0.6", "status": "COLLECTED_PENDING_PRIVATE_ARCHIVE",
              "market_data_requests": attempted, "maximum_planned_requests": len(plan()),
              "plan_entitlement": "USER_REPORTED_BASIC_TESTED_BY_FEED_NOT_ACCOUNT_BILLING_QUERY",
              "results": results, "adjustment_comparison": comparisons,
              "additional4_complete_symbols": sorted({r["symbol"] for r in results
                  if r.get("cohort") == "USER_ADDITIONAL4" and r.get("complete_ohlcv")}),
              "additional4_denominator": 4, "formal_backtests": 0}
    (root / "aggregate.json").write_bytes(encoded(report))
    # Retain all raw/error receipts only in the existing private raw repository.
    archive = root.parent / (root.name + ".zip")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zipped:
        for path in sorted(root.rglob("*")):
            if path.is_file(): zipped.write(path, path.relative_to(root))
    tag = "bt-data-pilot-v06-alpaca-" + os.environ.get("GITHUB_RUN_ID", "local") + "-" + os.environ.get("GITHUB_RUN_ATTEMPT", "1")
    sha = release.file_sha(archive)
    try:
        release.upload(RAW_REPO, tag, archive, "private-inputs.zip", sha)
        release.download(RAW_REPO, tag, "private-inputs.zip", root.parent / (root.name + "-roundtrip.zip"), sha)
    except release.ReleaseError:
        report.update(status="PRIVATE_ARCHIVE_ROUNDTRIP_FAILED", private_storage_verified=False)
        return report
    report.update(status="PRIVATE_ARCHIVE_ROUNDTRIP_VERIFIED", private_release_tag=tag)
    # Printed output contains aggregate counts and dates only, no prices/secret/hash.
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--private-dir", type=Path)
    args = parser.parse_args()
    if args.plan:
        print(json.dumps({"requests": plan(), "maximum_requests": len(plan()), "network_calls": 0}))
        return
    if not args.private_dir:
        parser.error("--private-dir required")
    try:
        result = collect(args.private_dir)
        print(json.dumps(result, sort_keys=True))
        if result["status"] != "PRIVATE_ARCHIVE_ROUNDTRIP_VERIFIED":
            raise SystemExit(2)
    except (release.ReleaseError, OSError, ValueError, KeyError, TypeError):
        print('{"status":"PROBE_OR_PRIVATE_ARCHIVE_FAILED","formal_backtests":0}')
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
