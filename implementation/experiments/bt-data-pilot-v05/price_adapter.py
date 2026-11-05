"""BT-DATA-PILOT v0.5 lossless private Tiingo research adapter.

Reuse fetch_tiingo_prices' symbol convention and the existing raw store. Do not
route research through its legacy close-only to_chart conversion. This module
does not alter production fetching or the execution/corporate-action ledger.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime
import importlib.util
import json
import math
import os
import re
from pathlib import Path
from urllib.parse import quote
import hashlib

ROOT = Path(__file__).resolve().parents[2]
RAW = ("open", "high", "low", "close", "volume")
ADJUSTED = ("adjOpen", "adjHigh", "adjLow", "adjClose", "adjVolume")
EVENTS = ("divCash", "splitFactor")


def legacy_collector():
    spec = importlib.util.spec_from_file_location("pilot_tiingo", ROOT / "tools/fetch_tiingo_prices.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def internal_rights_allowed(rights):
    """Publication permission is deliberately NOT an internal-research gate."""
    return (type(rights.get("data_fee")) in (int, float) and rights["data_fee"] == 0
            and rights.get("time_limited_trial") is False
            and all(rights.get(k) is True for k in ("internal_research", "raw_storage", "cloud_processing")))


def normalize_tiingo(body: bytes, symbol: str, currency: str | None = None):
    rows = json.loads(body)
    if not isinstance(rows, list):
        raise ValueError("expected price array, not an error response")
    result, seen = [], set()
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("date"), str):
            raise ValueError("missing provider date")
        datetime.fromisoformat(row["date"].replace("Z", "+00:00"))
        day = date.fromisoformat(row["date"][:10]).isoformat()
        if day in seen:
            raise ValueError("duplicate session; refuse duplicate corporate-action application")
        seen.add(day)
        values = {}
        for name in RAW + ADJUSTED + EVENTS:
            value = row.get(name)
            if value is not None:
                if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
                    raise ValueError(f"invalid numeric field: {name}")
                if name == "splitFactor" and value <= 0:
                    raise ValueError("nonpositive split factor")
                if name != "divCash" and value < 0:
                    raise ValueError(f"negative field: {name}")
                if name in ("open", "high", "low", "close") and value == 0:
                    raise ValueError("zero raw OHLC")
            values[name] = value
        o, h, l, c = (values[k] for k in ("open", "high", "low", "close"))
        if all(v is not None for v in (o, h, l, c)) and not l <= min(o, c) <= max(o, c) <= h:
            raise ValueError("OHLC range mismatch")
        result.append({"provider": "TIINGO", "symbol": symbol, "session_date": day,
                       "currency": currency, "raw": {k: values[k] for k in RAW},
                       "adjusted": {k: values[k] for k in ADJUSTED},
                       "events": {k: values[k] for k in EVENTS},
                       "missing_fields": [k for k, v in values.items() if v is None],
                       "provider_payload": row, "price_basis": "RAW_UNADJUSTED",
                       "known_at": None, "session_open_at": None, "session_close_at": None,
                       "dividend_ex_date": None, "dividend_pay_date": None,
                       "permanent_security_id": None, "ledger_ready": False})
    return sorted(result, key=lambda r: r["session_date"])


def execution_prices(row):
    """Never use adjusted bars as execution prices; never manufacture missing values."""
    if row["price_basis"] != "RAW_UNADJUSTED":
        raise ValueError("corporate-action double-count risk")
    return {k: row["raw"][k] for k in ("open", "close")}


def fetch_window(store_dir, symbol, start, end, rights):
    """One private research fetch; reuse raw store and symbol rules, no public route."""
    if store_dir.resolve().is_relative_to(ROOT.parent):
        raise ValueError("private store must be outside repository")
    if date.fromisoformat(start) > date.fromisoformat(end):
        raise ValueError("reversed window")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]{0,31}", symbol):
        raise ValueError("invalid provider symbol")
    if not internal_rights_allowed(rights) or not rights.get("evidence"):
        raise ValueError("free internal rights evidence required; publication is separate")
    collector = legacy_collector()
    # The legacy transport unconditionally withholds prices under its public-route
    # policy. Keep that guard untouched; the authorized private pilot uses its own
    # bounded acquire helper, shared with the accountless SEC/KIS downloads.
    from collect_free import acquire
    token = os.environ.get("TIINGO_API_KEY")
    if not token:
        return {"status": "ACCOUNT_ACCESS_REQUIRED", "network_calls": 0}
    store_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    store_dir.chmod(0o700)
    store = collector.RawDatasetStore(store_dir)
    sym = collector.tiingo_symbol(symbol)
    aid = f"tiingo_research:{sym}:{start}:{end}"
    url = f"https://api.tiingo.com/tiingo/daily/{quote(sym, safe='')}/prices?startDate={start}&endDate={end}&format=json"
    cached = store.has(aid)
    if cached and hashlib.sha256(store.get_bytes(aid)).hexdigest() != store.get_manifest(aid)["sha256"]:
        raise ValueError("cached raw response checksum mismatch")
    body, receipt = acquire(store, aid, url, "TIINGO_EOD_JSON",
                            headers={"Authorization": f"Token {token}", "Content-Type": "application/json"})
    if body is None:
        return {"status": receipt["status"], "http_status": receipt.get("http_status"),
                "request_started": not cached}
    rows = normalize_tiingo(store.get_bytes(aid), sym)
    if any(not start <= row["session_date"] <= end for row in rows):
        raise ValueError("provider response outside bounded request")
    return {"status": "CACHED" if cached else "ACQUIRED", "rows": len(rows),
            "ledger_ready": False, "raw_artifact_id": aid}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--fetch-store", type=Path)
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--currency")
    parser.add_argument("--rights", type=Path, required=True,
                        help="Private rights record; publication may remain unverified")
    args = parser.parse_args()
    if args.fetch_store:
        if not args.start or not args.end or args.input or args.output:
            parser.error("fetch mode requires --start/--end and no input/output")
        print(json.dumps(fetch_window(args.fetch_store, args.symbol, args.start, args.end,
                                     json.loads(args.rights.read_text()))))
        return
    if not args.input or not args.output:
        parser.error("offline mode requires --input/--output")
    if args.output.resolve().is_relative_to(ROOT.parent):
        parser.error("raw normalized prices must remain outside the repository")
    if not internal_rights_allowed(json.loads(args.rights.read_text())):
        parser.error("free internal research/storage/cloud rights must be established")
    collector = legacy_collector()
    normalized = normalize_tiingo(args.input.read_bytes(), collector.tiingo_symbol(args.symbol), args.currency)
    args.output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    args.output.write_text(json.dumps(normalized, allow_nan=False))
    args.output.chmod(0o600)
    print(json.dumps({"version": "BT-DATA-PILOT v0.5", "rows": len(normalized),
                      "ledger_ready": False, "formal_backtests": 0}))


if __name__ == "__main__":
    main()
