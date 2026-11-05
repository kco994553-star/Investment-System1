"""BT-DATA-PILOT v0.6: bounded private price verification, never strategy returns.

Reuse v0.5 byte storage, transport and numeric validation. The Fiscal.ai MCP
envelope is the original tool response, not a claim to upstream HTTP wire bytes.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import date, datetime, timedelta
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlencode

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "bt-data-pilot-v05"))
from manual_ingest import digest, encoded, put_once, no_credentials
from price_adapter import normalize_tiingo, internal_rights_allowed, ROOT
from collect_free import acquire, RawDatasetStore

VERSION = "BT-DATA-PILOT v0.6"
START, END = "2016-03-28", "2016-04-01"
FIELDS = ("open", "high", "low", "close", "volume")
CSV_SHA = "b2f4fe2f2e4dce8eaf0eb4fbd3946a32a20c1ddfe69687dfca3b6b59a0b71f9f"
EXHIBIT_SHA = "0ecc02e84b08922c9693eaa725fdb6375dc49cae9f8af530169b5f3efe6204aa"
SOURCE_COMMIT = "a2430f2af0c79ddf0748e91de11bdeb1616ab5a7"


def private_dir(path):
    path = Path(path).resolve()
    if path.is_relative_to(ROOT.parent) or ROOT.parent.is_relative_to(path):
        raise ValueError("choose a private directory outside the repository")
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.chmod(0o700)
    return path


def tool_payload(envelope, capability):
    if envelope["tool_name"] != "mcp__codex_apps__firecrawl_firecrawl_scrape":
        raise ValueError("unexpected tool")
    for k in ("requested_at", "received_at"):
        if datetime.fromisoformat(envelope[k].replace("Z", "+00:00")).tzinfo is None:
            raise ValueError("timezone required for collection timestamp")
    args = envelope["arguments"]["alexandria"]
    no_credentials(envelope["arguments"])
    if args["provider"] != "fiscal-ai" or args["capability"] != capability:
        raise ValueError("request mismatch")
    response = envelope["response"]
    if response.get("isError"):
        raise ValueError("tool returned an error")
    result = response.get("structuredContent")
    if not result:
        result = json.loads(response["content"][0]["text"])
    if result.get("success") is not True:
        raise ValueError("provider call failed")
    items = result["data"]["alexandria"]
    if len(items) != 1:
        raise ValueError("ambiguous provider response")
    item = items[0]
    if (item["provider"], item["capability"], item["upstreamStatus"]) != ("fiscal-ai", capability, 200):
        raise ValueError("provider identity/status mismatch")
    return item["data"], result["data"].get("creditsCost")


def fiscal_rows(envelope):
    data, _ = tool_payload(envelope, "prices/daily")
    opts = envelope["arguments"]["alexandria"]["options"]
    if opts != {"cik": "0000001800", "startDate": START, "endDate": END}:
        raise ValueError("frozen stage A request mismatch")
    if data["ticker"] != "ABT" or data["tradingCurrency"] != "USD" or data["operatingMic"] != "XNYS":
        raise ValueError("listing mismatch")
    # Only the shared numeric/date validator sees this temporary field mapping.
    mapped = [{"date": r["date"], "open": r.get("openPrice"),
               "close": r.get("closePrice"), "volume": r.get("volume")} for r in data["prices"]]
    validated = normalize_tiingo(encoded(mapped), "ABT", "USD")
    original = {r["date"]: r for r in data["prices"]}
    for row in validated:
        if not START <= row["session_date"] <= END:
            raise ValueError("response outside frozen window")
        observed = row.pop("raw")
        row.update(provider="FISCAL_AI", access_method="PLUGIN_MCP", observed=observed,
                   raw={k: None for k in FIELDS}, price_basis="SPLIT_ADJUSTED",
                   adjusted={"adjOpen": observed["open"], "adjHigh": None, "adjLow": None,
                             "adjClose": observed["close"], "adjVolume": None},
                   volume_basis="PROVIDER_UNSPECIFIED", provider_payload=original[row["session_date"]],
                   provider_listing_id=data["listingFiscalIdentifier"],
                   operating_mic="XNYS", timezone=None,
                   calendar_timezone_candidate="America/New_York", timezone_evidence="MIC_MAPPING_ONLY",
                   provider_published_at=None, assumed_available_at=None,
                   retrieved_at=envelope["received_at"], ledger_ready=False)
        row["missing_fields"] = [k for k in FIELDS if observed[k] is None]
    return validated


def fiscal_replay(input_path, splits_path, output):
    output = private_dir(output)
    for name in ("originals", "normalized", "manifests"):
        (output / name).mkdir(exist_ok=True, mode=0o700)
    body = input_path.read_bytes()
    envelope = json.loads(body)
    rows = fiscal_rows(envelope)
    # Existing content-addressed writer rejects altered bytes at the same path.
    put_once(output / "originals" / (digest(body) + ".json"), body)
    put_once(output / "normalized" / (digest(body) + ".json"), encoded(rows))
    manifest = {"version": VERSION, "provider": "Fiscal.ai", "access_method": "PLUGIN_MCP",
                "tool_name": envelope["tool_name"], "arguments": envelope["arguments"],
                "requested_at": envelope["requested_at"], "retrieved_at": envelope["received_at"],
                "raw_sha256": digest(body), "representation": "FULL_TOOL_RESPONSE_JSON_NOT_HTTP_WIRE",
                "request_start": START, "request_end": END,
                "rights_source": "https://www.firecrawl.dev/terms/third-party-data/fiscal-ai/D-1.0.0",
                "rights_scope": "D.2,D.3(b),D.9: bounded own-application private research storage",
                "provider_publication_time": None, "price_basis": "SPLIT_ADJUSTED"}
    put_once(output / "manifests" / (digest(body) + ".json"), encoded(manifest))
    split_body = splits_path.read_bytes()
    splits, _ = tool_payload(json.loads(split_body), "prices/splits")
    if json.loads(split_body)["arguments"]["alexandria"]["options"] != {"cik": "0000001800"}:
        raise ValueError("split request identity mismatch")
    put_once(output / "originals" / (digest(split_body) + ".json"), split_body)
    # Actual existing PIT adapter rejects these observed split-adjusted closes.
    from investment_system.research.qgv_backtest.pit_adapter import quotes_as_of
    candidate = [{"security_id": r["provider_listing_id"], "date": r["session_date"],
                  "close": r["observed"]["close"], "currency": r["currency"],
                  "price_basis": r["price_basis"], "shares_basis": None,
                  "known_at": None} for r in rows]
    accepted = quotes_as_of(candidate, END)
    result = {"version": VERSION, "actual_price_companies": int(bool(rows)), "fixed_companies": 10,
              "stage_a_rows": len(rows), "date_min": min((r["session_date"] for r in rows), default=None),
              "date_max": max((r["session_date"] for r in rows), default=None),
              "complete_ohlcv_companies": int(bool(rows) and all(not r["missing_fields"] for r in rows)),
              "missing_by_field": {k: sum(r["observed"][k] is None for r in rows) for k in FIELDS},
              "price_basis": "SPLIT_ADJUSTED", "duplicate_dates": 0,
              "stage_b_c": "NOT_EXECUTED_STAGE_A_INCOMPLETE_OHLCV",
              "split_records": len(splits), "split_validation": "UNVERIFIED_EMPTY_RESPONSE" if not splits else "NEEDS_EVENT_MATCH",
              "dividend_validation": "NOT_ACQUIRED", "v_input_accepted": len(accepted),
              "v_input_tested_companies": int(bool(rows)), "v_factor_complete": 0, "v_factor_slots": 50,
              "ledger_ready": False, "formal_backtests": 0}
    put_once(output / "summary.json", encoded(result))
    return result


def alpaca_stage_a(output, rights):
    """Only fixed ABT/5 sessions; SIP entitlement is tested, never silently switched."""
    no_credentials(rights)
    if not internal_rights_allowed(rights) or not rights.get("evidence"):
        raise ValueError("free personal internal rights must be established")
    key, secret = os.environ.get("APCA_API_KEY_ID"), os.environ.get("APCA_API_SECRET_KEY")
    if not key or not secret:
        return {"status": "AUTHENTICATION_MISSING", "network_calls": 0,
                "key_configured": bool(key), "secret_configured": bool(secret)}
    output = private_dir(output)
    for name in ("normalized", "requests"):
        (output / name).mkdir(exist_ok=True, mode=0o700)
    store = RawDatasetStore(output / "store")
    params = {"timeframe": "1Day", "start": START + "T00:00:00-04:00",
              "end": "2016-04-02T00:00:00-04:00", "adjustment": "raw", "feed": "sip",
              "sort": "asc", "limit": 1000, "asof": "-"}
    # asof '-' prevents current-ticker remapping; no assumption that current names
    # identify past securities. Full cohort expansion requires dated mappings.
    url = "https://data.alpaca.markets/v2/stocks/ABT/bars?" + urlencode(params)
    body, receipt = acquire(store, "alpaca:ABT:20160328:20160401:sip:raw:asof-none", url,
                            "ALPACA_STOCK_BARS_JSON",
                            {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret})
    if body is None:
        return {"status": "API_CALL_FAILED" if receipt.get("http_status") else "NETWORK_REQUEST_FAILED",
                "http_status": receipt.get("http_status"), "network_policy_block_proven": False}
    data = json.loads(body)
    if (data.get("symbol") != "ABT" or "bars" not in data
            or (data["bars"] is not None and not isinstance(data.get("bars"), list))):
        return {"status": "RESPONSE_QUALITY_FAILED", "reason": "SYMBOL_OR_SCHEMA"}
    if data.get("next_page_token"):
        return {"status": "RESPONSE_INCOMPLETE", "reason": "UNEXPECTED_PAGINATION_FOR_FIVE_DAY_PROBE"}
    data["bars"] = data["bars"] or []
    mapped = []
    for row in data["bars"]:
        timestamp = datetime.fromisoformat(row["t"].replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            raise ValueError("bar timestamp missing offset")
        from zoneinfo import ZoneInfo
        day = timestamp.astimezone(ZoneInfo("America/New_York")).date().isoformat()
        if not START <= day <= END:
            raise ValueError("bar outside bounded request")
        mapped.append({"date": day, **{k: row.get(v) for k, v in
                      zip(FIELDS, ("o", "h", "l", "c", "v"))}})
    rows = normalize_tiingo(encoded(mapped), "ABT", "USD")
    for row, original in zip(rows, sorted(data["bars"], key=lambda r: r["t"])):
        row.update(provider="ALPACA", feed="sip", provider_payload=original,
                   currency_evidence="US_STOCKS_ENDPOINT_SCOPE_NOT_RESPONSE_FIELD",
                   bar_timestamp_semantics="PERIOD_START_NOT_PUBLICATION_TIME")
    raw_hash = digest(body)
    put_once(output / "normalized" / (raw_hash + ".json"), encoded(rows))
    put_once(output / "requests" / (raw_hash + ".json"), encoded({"version": VERSION,
             "arguments": params, "source_url": url, "raw_sha256": raw_hash, "rights": rights,
             "retrieved_at": receipt["fetched_at"] if "fetched_at" in receipt else receipt.get("retrieved_at"),
             "provider_publication_time": None}))
    missing = {k: sum(r["raw"][k] is None for r in rows) for k in FIELDS}
    expected = {"2016-03-28", "2016-03-29", "2016-03-30", "2016-03-31", "2016-04-01"}
    complete = {r["session_date"] for r in rows} == expected and not any(missing.values())
    return {"status": "ACQUIRED" if rows else "REQUESTED_DATA_ABSENT", "rows": len(rows),
            "complete_stage_a_ohlcv": complete, "missing_by_field": missing,
            "date_min": min((r["session_date"] for r in rows), default=None),
            "date_max": max((r["session_date"] for r in rows), default=None),
            "ledger_ready": False, "corporate_actions": "NOT_ACQUIRED", "formal_backtests": 0}


def meta_overlay(csv_bytes, exhibit_bytes):
    """Case-specific overlay; preserve default inclusive interpretation elsewhere."""
    if digest(csv_bytes) != CSV_SHA or digest(exhibit_bytes) != EXHIBIT_SHA:
        raise ValueError("unreviewed source vintage; do not generalize interval correction")
    from investment_system.universe.sources import parse_ticker_intervals_csv
    parsed = parse_ticker_intervals_csv(csv_bytes.decode())
    original = parsed["roster"]
    affected = [m for m in original if m.ticker in {"FB", "META"}]
    if {(m.ticker, m.entered_on, m.exited_on) for m in affected} != {
        ("FB", "2013-12-23", "2022-06-10"), ("META", "2022-06-09", None)}:
        raise ValueError("unexpected source intervals")
    # Local research identifier, NOT an invented CUSIP or universal security ID.
    sid = "research:SEC-1326801:Class-A"
    parsed["roster"] = tuple(replace(m, company_id=sid,
        exited_on="2022-06-09" if m.ticker == "FB" else m.exited_on)
        if m.ticker in {"FB", "META"} else m for m in original)
    parsed["case_overlay"] = {"source_commit": SOURCE_COMMIT, "case": "FB_META_ONLY",
        "effective_before_open": "2022-06-09", "issuer_cik": 1326801,
        "security_continuity": "SEC_EXHIBIT_CLASS_A_CUSIP_UNCHANGED",
        "security_id_scope": "LOCAL_RESEARCH_IDENTIFIER", "original_csv_unchanged": True}
    return parsed


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    f = sub.add_parser("replay-fiscal")
    f.add_argument("--input", type=Path, required=True)
    f.add_argument("--splits", type=Path, required=True)
    f.add_argument("--private-dir", type=Path, required=True)
    a = sub.add_parser("alpaca-stage-a")
    a.add_argument("--private-dir", type=Path, required=True)
    a.add_argument("--rights", type=Path, default=HERE / "alpaca-personal-rights.json")
    m = sub.add_parser("meta-check")
    m.add_argument("--csv", type=Path, required=True)
    m.add_argument("--exhibit", type=Path, required=True)
    args = p.parse_args()
    if args.command == "replay-fiscal":
        result = fiscal_replay(args.input, args.splits, args.private_dir)
    elif args.command == "alpaca-stage-a":
        result = alpaca_stage_a(args.private_dir, json.loads(args.rights.read_text()))
    else:
        result = meta_overlay(args.csv.read_bytes(), args.exhibit.read_bytes())["case_overlay"]
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
