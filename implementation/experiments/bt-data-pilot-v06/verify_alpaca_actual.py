"""Offline verification of the approved run; never calls Alpaca or prints prices."""
import argparse
from decimal import Decimal, ROUND_HALF_UP
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path

import github_alpaca_probe as probe


def verify(root, fiscal, reviewed_src):
    store = root / "restored/store"
    results, series, numeric_checks, source_hashes = [], {}, 0, []
    for request in probe.plan():
        aid = ":".join(("alpaca_v06", request["symbol"], request["feed"], request["adjustment"],
                        request["days"][0], request["days"][-1]))
        manifest = json.loads((store / "manifests" / (aid.replace(":", "__") + ".json")).read_text())
        body = (store / "blobs" / aid.replace(":", "__")).read_bytes()
        assert hashlib.sha256(body).hexdigest() == manifest["sha256"]
        assert manifest["http_status"] == 200
        source_hashes.append({"artifact_id": aid, "sha256": manifest["sha256"]})
        rows = probe.normalize(body, request)
        source = json.loads(body, parse_float=Decimal)
        original = {r["t"][:10]: r for r in source["bars"] or []}
        for row in rows:
            values = row["raw"] if request["adjustment"] == "raw" else row["observed"]
            for field, api in zip(("open", "high", "low", "close", "volume"), ("o", "h", "l", "c", "v")):
                assert Decimal(str(values[field])) == Decimal(original[row["session_date"]][api])
                numeric_checks += 1
            assert row["known_at"] is None and row["ledger_ready"] is False
        results.append({"status": "ACQUIRED" if rows else "REQUESTED_DATA_ABSENT",
                        "http_status": 200, **probe.summary_for(rows, request)})
        series[(request["symbol"], request["feed"], request["adjustment"], request["days"][0])] = rows
    assert len(results) == 14 and numeric_checks == 205
    assert sum(r["rows"] for r in results) == 41
    # Source statement is saved with a verified raw-store manifest.
    source_dir = root / "sources"
    event_path = source_dir / "blobs/nvidia_split_newsroom_2024"
    event_manifest = json.loads((source_dir / "manifests/nvidia_split_newsroom_2024.json").read_text())
    assert hashlib.sha256(event_path.read_bytes()).hexdigest() == event_manifest["sha256"]
    class Text(HTMLParser):
        def __init__(self): super().__init__(); self.parts = []
        def handle_data(self, value): self.parts.append(value)
    parser = Text(); parser.feed(event_path.read_text())
    text = " ".join(" ".join(parser.parts).split())
    assert "ten-for-one forward stock split" in text
    assert "market open on Monday, June 10, 2024" in text
    assert "after the close of market on Friday, June 7, 2024" in text
    assert "paid on Friday, June 28, 2024" in text
    exact, rounded, volume = 0, 0, 0
    for feed in ("iex", "sip"):
        raw = series[("NVDA", feed, "raw", "2024-06-07")]
        adjusted = series[("NVDA", feed, "split", "2024-06-07")]
        for r, a in zip(raw, adjusted):
            assert r["session_date"] == a["session_date"]
            factor = Decimal(10 if r["session_date"] == "2024-06-07" else 1)
            for field in ("open", "high", "low", "close"):
                expected = Decimal(str(r["raw"][field])) / factor
                observed = Decimal(str(a["observed"][field]))
                exact += expected == observed
                # Only transformed, pre-split prices show the two-decimal behavior.
                # Do not round unchanged post-split bars, which can have more precision.
                adjusted_expected = expected.quantize(Decimal(".01"), rounding=ROUND_HALF_UP) if factor != 1 else expected
                rounded += adjusted_expected == observed
            volume += Decimal(str(r["raw"]["volume"])) * factor == Decimal(str(a["observed"]["volume"]))
    assert (exact, rounded, volume) == (26, 32, 8)
    # Different feeds are not independent providers; record coverage differences.
    iex = {r["session_date"]: r["raw"] for r in series[("NVDA", "iex", "raw", "2024-06-07")]}
    sip = {r["session_date"]: r["raw"] for r in series[("NVDA", "sip", "raw", "2024-06-07")]}
    feed_differences = {k: sum(iex[d][k] != sip[d][k] for d in iex) for k in ("open", "high", "low", "close", "volume")}
    fiscal_data = json.loads(fiscal.read_text())["response"]["structuredContent"]["data"]["alexandria"][0]["data"]
    assert fiscal_data["ticker"] == "ABT"
    fp = {r["date"]: r for r in fiscal_data["prices"]}
    abt = series[("ABT", "sip", "raw", "2016-03-28")]
    provider_matches = {k: sum(Decimal(str(r["raw"][k])) == Decimal(str(fp[r["session_date"]][key])) for r in abt)
                        for k, key in (("open", "openPrice"), ("close", "closePrice"), ("volume", "volume"))}
    import investment_system, investment_system.research
    investment_system.__path__.append(str(reviewed_src / "investment_system"))
    investment_system.research.__path__.append(str(reviewed_src / "investment_system/research"))
    from investment_system.research.qgv_backtest.pit_adapter import quotes_as_of
    candidates = [{"security_id": "UNVERIFIED_ALPACA:" + symbol, "date": r["session_date"],
                   "currency": "USD", "close": r["raw"]["close"], "price_basis": "RAW",
                   "shares_basis": None, "known_at": None} for symbol in ("ABT", "AAPL", "MSFT", "NVDA", "ASML")
                  for r in series[(symbol, "sip", "raw", "2016-03-28")]]
    # These names are audit placeholders, NOT permanent security IDs or a universe.
    accepted = quotes_as_of(candidates, "2016-04-01")
    assert accepted == {}
    summary = {"version": "BT-DATA-PILOT v0.6", "run_id": 41152748825,
               "real_responses_verified": 14, "normalized_rows": 41, "numeric_fields_verified": numeric_checks,
               "raw_rows": 33, "split_adjusted_rows": 8, "unique_security_dates": 29,
               "results": results, "additional4_success": 4, "fixed10_success": 1,
               "split": {"issuer_ratio_and_trading_date_verified": True, "price_exact_matches": exact,
                         "price_checks": 32, "two_decimal_rounding_matches": rounded,
                         "volume_matches": volume, "volume_checks": 8,
                         "provider_rounding_policy_verified": False,
                         "dividend_pay_date": "2024-06-28", "dividend_ex_date": None,
                         "cash_or_split_ledger_executed": False},
               "iex_sip_different_sessions_by_field": feed_differences,
               "fiscal_alpaca_abt_matching_sessions_by_field": provider_matches,
               "v_input_accepted": len(accepted), "v_input_tested_companies": 5,
               "additional_alpaca_requests": 0, "formal_backtests": 0}
    (root / "verified-results.json").write_text(json.dumps(summary, indent=2))
    (root / "verified-source-hashes.json").write_text(json.dumps(source_hashes, indent=2))
    return summary


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--private-dir", type=Path, required=True)
    p.add_argument("--fiscal-original", type=Path, required=True)
    p.add_argument("--reviewed-src", type=Path, required=True)
    args = p.parse_args()
    # Treat the same private-path guard as the acquisition adapter.
    root = probe.private_dir(args.private_dir)
    result = verify(root, args.fiscal_original, args.reviewed_src)
    for file in (root / "verified-results.json", root / "verified-source-hashes.json"):
        file.chmod(0o600)
    print(json.dumps({k: v for k, v in result.items() if k != "results"}, sort_keys=True))
