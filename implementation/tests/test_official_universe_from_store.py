"""Official Default Universe built directly from the ingested raw store."""

import json
from datetime import datetime, timezone
from pathlib import Path

from investment_system.contracts.universe import UniverseKind, UniversePolicyStatus
from investment_system.ingestion.raw_store import RawDatasetStore
from investment_system.universe.sources import official_mcap500_snapshot_from_store
from investment_system.validation.vertical_slice import run_vertical_slice

UTC = timezone.utc
T0 = datetime(2025, 3, 31, tzinfo=UTC)


def _chart(symbol, prices):
    ts = [1_700_000_000 + i * 86400 for i in range(len(prices))]
    return {"chart": {"result": [{"meta": {"symbol": symbol, "currency": "USD"}, "timestamp": ts,
            "indicators": {"quote": [{"close": prices}], "adjclose": [{"adjclose": prices}]}}]}}


def _facts(shares, rev):
    return {"facts": {"us-gaap": {
        "EntityCommonStockSharesOutstanding" if False else "CommonStockSharesOutstanding": {"units": {"shares": [
            {"end": "2025-01-01", "val": shares, "filed": "2025-02-01", "form": "10-Q"}]}},
        "RevenueFromContractWithCustomerExcludingAssessedTax": {"units": {"USD": [
            {"end": "2024-12-31", "val": rev, "filed": "2025-02-01", "form": "10-K", "fy": 2024, "fp": "FY", "accn": "a"}]}},
        "EarningsPerShareDiluted": {"units": {"USD/shares": [
            {"end": "2024-12-31", "val": rev / 1000, "filed": "2025-02-01", "form": "10-K", "fy": 2024, "fp": "FY", "accn": "a"}]}},
        "NetIncomeLoss": {"units": {"USD": [{"end": "2024-12-31", "val": rev * 0.1, "filed": "2025-02-01", "form": "10-K"}]}},
        "OperatingIncomeLoss": {"units": {"USD": [{"end": "2024-12-31", "val": rev * 0.12, "filed": "2025-02-01", "form": "10-K"}]}},
        "StockholdersEquity": {"units": {"USD": [{"end": "2024-12-31", "val": rev * 0.6, "filed": "2025-02-01", "form": "10-K"}]}},
    }}}


def test_official_top500_ranked_from_stored_real_shaped_data(tmp_path):
    store = RawDatasetStore(Path(tmp_path))
    n = 520
    listings = {}
    for i in range(n):
        cid, cik, sym = f"co{i:04d}", f"{i + 1:010d}", f"T{i:04d}"
        mcap_rank_price = 100.0 + (i * 37 % 400)  # non-monotonic in i, deliberately
        store.put(f"companyfacts:{cik}", json.dumps(_facts(1_000_000 + i, 5_000_000 + i)).encode(),
                   "u", "SEC_COMPANYFACTS", "application/json", "test")
        store.put(f"yahoo_chart:{sym}:5y", json.dumps(_chart(sym, [mcap_rank_price])).encode(),
                   "u", "YAHOO_CHART", "application/json", "test")
        listings[cid] = {"yahoo": sym, "cik": cik}

    snap, rep = official_mcap500_snapshot_from_store(store, listings, T0, chart_range="5y")
    assert snap.universe_kind is UniverseKind.US_MCAP_TOP500_OFFICIAL
    assert snap.policy_status is UniversePolicyStatus.OFFICIAL
    assert len(snap.members) == 500
    assert rep["n_ranked"] == 520

    res = run_vertical_slice(T0, datetime(2025, 9, 30, tzinfo=UTC), *_load_payloads_bars(store, listings), store_path=Path(tmp_path) / "s.json", universe=snap)
    assert res["official_universe"] is True
    assert len(res["universe"]) == 500


def _load_payloads_bars(store, listings):
    from investment_system.ingestion.replay import build_payloads_and_bars
    return build_payloads_and_bars(store, listings, chart_range="5y")
