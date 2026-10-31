"""Offline actual-byte replay and KIS/Alpaca comparison; prints aggregates only."""
import argparse
from decimal import Decimal
import json
from pathlib import Path

from github_kis_probe import (RawDatasetStore, digest, encoded, kis_normalize, alpaca_normalize,
                              FIXED, FIELDS, PRIMARY_DAYS, RECENT)


def replay(root):
    store = RawDatasetStore(root / "store")
    for aid in store.list_ids():
        assert digest(store.get_bytes(aid)) == store.get_manifest(aid)["sha256"]
    numeric, series, normalized, rejected = 0, {}, 0, []
    for receipt_file in sorted((root / "requests").glob("*.json")):
        receipt = json.loads(receipt_file.read_bytes())
        manifest = receipt.get("receipt")
        if not manifest or not manifest.get("sha256"):
            continue
        body = store.get_bytes(manifest["artifact_id"])
        assert digest(body) == manifest["sha256"]
        source = json.loads(body, parse_float=Decimal)
        if manifest["source_kind"] == "KIS_DAILYPRICE_JSON":
            if source.get("rt_cd") != "0":
                continue
            params = receipt["request"]
            try:
                rows = kis_normalize(body, params["SYMB"], params["MODP"], params["BYMD"])
            except ValueError:
                rejected.append({"symbol": params["SYMB"], "bymd": params["BYMD"], "modp": params["MODP"]})
                continue
            key = digest(encoded({"raw": digest(body), "params": params}))
            originals = {r["xymd"][:4]+"-"+r["xymd"][4:6]+"-"+r["xymd"][6:]: r for r in source["output2"]}
            provider, symbol, adjustment = "KIS", params["SYMB"], params["MODP"]
            columns = ("open", "high", "low", "clos", "tvol")
        else:
            request = receipt["request"]
            rows = alpaca_normalize(body, request)
            key = digest(encoded({"raw": digest(body), "request": request}))
            originals = {r["t"][:10]: r for r in source["bars"] or []}
            provider, symbol, adjustment = "ALPACA", request["symbol"], "0"
            columns = ("o", "h", "l", "c", "v")
        saved = root / "normalized" / (key + ".json")
        assert saved.read_bytes() == encoded(rows), "replay differs from saved normalized bytes"
        normalized += len(rows)
        for row in rows:
            assert row["known_at"] is None and row["ledger_ready"] is False
            values = row["raw"] if adjustment == "0" else row["observed"]
            for field, original in zip(FIELDS, columns):
                value = originals[row["session_date"]].get(original)
                if value in (None, ""):
                    assert values[field] is None
                else:
                    assert Decimal(str(values[field])) == Decimal(str(value))
                numeric += 1
            series_key = (provider, symbol, adjustment, row["session_date"])
            if series_key in series:
                assert series[series_key] == values, "conflicting overlapping page"
            series[series_key] = values
    return series, {"actual_raw_hashes_verified": len(store.list_ids()),
                    "normalized_rows_replayed": normalized, "numeric_cells_verified": numeric,
                    "quality_rejected_pages": rejected}


def verify(root, previous, reviewed_src, additional=None):
    series, result = replay(root)
    if additional:
        extra_series, extra_result = replay(additional)
        for key, values in extra_series.items():
            if key in series:
                assert series[key] == values
            series[key] = values
        for key in ("actual_raw_hashes_verified", "normalized_rows_replayed", "numeric_cells_verified"):
            result[key] += extra_result[key]
        result["quality_rejected_pages"] += extra_result["quality_rejected_pages"]
    # Reuse previous successful ABT 2016 and NVDA 2024 SIP requests, no new download.
    old = RawDatasetStore(previous / "store")
    for symbol, days in (("ABT", PRIMARY_DAYS), ("NVDA", ["2024-06-07", "2024-06-10", "2024-06-11", "2024-06-12"])):
        aid = ":".join(("alpaca_v06", symbol, "sip", "raw", days[0], days[-1]))
        body = old.get_bytes(aid)
        assert digest(body) == old.get_manifest(aid)["sha256"]
        for row in alpaca_normalize(body, {"symbol": symbol, "days": days, "feed": "sip", "adjustment": "raw"}):
            series[("ALPACA", symbol, "0", row["session_date"])] = row["raw"]
    comparisons = []
    for _, symbol, _, historical in FIXED + [(1045810, "NVDA", "NAS", "NVDA")]:
        paired = [(key, values) for key, values in series.items() if key[0] == "KIS" and key[1] in (symbol, historical)
                  and key[2] == "0" and ("ALPACA", key[1], "0", key[3]) in series]
        comparisons.append({"symbol": symbol, "paired_sessions": len(paired),
            "equal_by_field": {field: sum(values[field] == series[("ALPACA", key[1], "0", key[3])][field]
                                          for key, values in paired) for field in FIELDS}})
    coverage = []
    for cik, symbol, _, historical in FIXED:
        row = {"cik": cik, "symbol": symbol, "historical_query_symbol": historical}
        for label, days, ticker in (("recent", RECENT, symbol), ("2016", PRIMARY_DAYS, historical)):
            for provider in ("KIS", "ALPACA"):
                dates = [day for day in days if (provider, ticker, "0", day) in series
                         and all(v is not None for v in series[(provider, ticker, "0", day)].values())]
                row[label + "_" + provider] = {"rows": len(dates), "date_min": min(dates, default=None),
                    "date_max": max(dates, default=None), "missing_dates": sorted(set(days)-set(dates)),
                    "missing_day_rate": (len(days)-len(dates))/len(days)}
        coverage.append(row)
    event_days = ["2024-06-07", "2024-06-10", "2024-06-11", "2024-06-12"]
    event = {"paired_sessions": 0, "price_exact_matches": 0, "price_checks": 0,
             "volume_unchanged": 0, "volume_split_scaled": 0, "ledger_executed": False}
    for day in event_days:
        raw, adj = series.get(("KIS", "NVDA", "0", day)), series.get(("KIS", "NVDA", "1", day))
        if raw is None or adj is None:
            continue
        event["paired_sessions"] += 1
        ratio = Decimal(10) if day < "2024-06-10" else Decimal(1)
        for field in FIELDS[:4]:
            if raw[field] is not None and adj[field] is not None:
                event["price_checks"] += 1
                event["price_exact_matches"] += Decimal(str(raw[field])) / ratio == Decimal(str(adj[field]))
        if raw["volume"] is not None and adj["volume"] is not None:
            event["volume_unchanged"] += raw["volume"] == adj["volume"]
            event["volume_split_scaled"] += Decimal(str(raw["volume"])) * ratio == Decimal(str(adj["volume"]))
    import investment_system, investment_system.research
    investment_system.__path__.append(str(reviewed_src / "investment_system"))
    investment_system.research.__path__.append(str(reviewed_src / "investment_system/research"))
    from investment_system.research.qgv_backtest.pit_adapter import quotes_as_of
    candidates = [{"security_id": "UNVERIFIED:" + ticker, "date": day, "currency": "USD",
                   "close": values["close"], "price_basis": "RAW", "shares_basis": None, "known_at": None}
                  for (provider, ticker, adjustment, day), values in series.items()
                  if provider == "ALPACA" and adjustment == "0" and day in PRIMARY_DAYS
                  and ticker in {entry[3] for entry in FIXED}]
    accepted = quotes_as_of(candidates, PRIMARY_DAYS[-1])
    assert not accepted
    result.update(coverage=coverage, provider_comparisons=comparisons, nvda_split=event,
                  v_quote_candidates=len(candidates), v_companies_tested=len({r["security_id"] for r in candidates}),
                  v_companies_accepted=0, v_factor_slots_complete=0, v_factor_slots_denominator=50,
                  formal_backtests=0, synthetic_data_included=False, new_network_requests=0)
    (root.parent / "verified-results.json").write_bytes(encoded(result))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--restored", type=Path, required=True)
    parser.add_argument("--previous-restored", type=Path, required=True)
    parser.add_argument("--reviewed-src", type=Path, required=True)
    parser.add_argument("--additional-restored", type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.restored, args.previous_restored, args.reviewed_src, args.additional_restored), sort_keys=True))
