from datetime import datetime, timezone

from investment_system.providers.sec_companyfacts import facts_to_raw
from investment_system.providers.sec_vintage import resolve_vintages, select_latest
from investment_system.validation.file_store import FileTrackRecordStore
from investment_system.validation.historical import bars_to_returns, run_as_of
from investment_system.validation.records import ScopedTrackStore


AS_A = datetime(2024, 6, 30, tzinfo=timezone.utc)
AS_B = datetime(2025, 3, 15, tzinfo=timezone.utc)
AS_C = datetime(2025, 9, 1, tzinfo=timezone.utc)

PAYLOAD = {
    "facts": {
        "us-gaap": {
            "Revenues": {
                "units": {
                    "USD": [
                        {"end": "2024-01-28", "val": 60, "filed": "2024-02-21", "form": "10-K", "fy": 2024, "fp": "FY", "accn": "a"},
                        {"end": "2025-01-26", "val": 130, "filed": "2025-02-26", "form": "10-K", "fy": 2025, "fp": "FY", "accn": "b"},
                        {"end": "2025-01-26", "val": 131, "filed": "2025-08-01", "form": "10-K/A", "fy": 2025, "fp": "FY", "accn": "c"},
                    ]
                }
            },
            "RevenueFromContractWithCustomerExcludingAssessedTax": {"units": {"USD": []}},
            "NetIncomeLoss": {"units": {"USD": []}},
            "CashAndCashEquivalentsAtCarryingValue": {"units": {"USD": []}},
            "LongTermDebt": {"units": {"USD": []}},
            "StockholdersEquity": {"units": {"USD": []}},
        }
    }
}

BARS = [
    {"price": 100.0, "observed_at": datetime(2025, 2, 1, tzinfo=timezone.utc)},
    {"price": 110.0, "observed_at": datetime(2025, 3, 1, tzinfo=timezone.utc)},
    {"price": 200.0, "observed_at": datetime(2025, 8, 15, tzinfo=timezone.utc)},
]


def test_vintage_as_of_a_vs_b_and_future_amendment():
    a = select_latest(resolve_vintages(PAYLOAD, "us-gaap", "Revenues", "USD", AS_A))
    b = select_latest(resolve_vintages(PAYLOAD, "us-gaap", "Revenues", "USD", AS_B))
    c = select_latest(resolve_vintages(PAYLOAD, "us-gaap", "Revenues", "USD", AS_C))
    assert a and a.value == 60
    assert b and b.value == 130
    assert c and c.value == 131
    assert a.value != b.value
    raw_b = facts_to_raw("nvda", "0001045810", PAYLOAD, AS_B, synthetic=True)
    raw_c = facts_to_raw("nvda", "0001045810", PAYLOAD, AS_C, synthetic=True)
    assert raw_b.revenue == 130
    assert raw_c.revenue == 131
    assert raw_b.revenue_prev == 60


def test_historical_bars_and_as_of_pipeline(tmp_path):
    rets = bars_to_returns(BARS, AS_B)
    assert len(rets) == 1 and abs(rets[0] - 0.1) < 1e-9
    assert 200.0 not in [BARS[0]["price"] * (1 + r) for r in bars_to_returns(BARS, AS_B)]
    store = ScopedTrackStore(FileTrackRecordStore(tmp_path / "t.json"))
    payloads = {"nvda": PAYLOAD, "msft": PAYLOAD, "asml": PAYLOAD}
    bars = {"nvda": BARS, "msft": BARS, "asml": BARS}
    early = run_as_of(AS_A, payloads, bars, store)
    later = run_as_of(AS_B, payloads, bars, store)
    assert early["official_pass"] is False
    assert early["full_pit_pass"] is False
    assert early["macro"] == "UNAVAILABLE"
    assert later["quality"]["nvda"]["coverage"] in {"PARTIAL", "BLOCKED", "SYNTHETIC", "READY"}
    assert early["as_of"] != later["as_of"]
    assert early["quality"]["nvda"]["revenue"] == 60
    assert later["quality"]["nvda"]["revenue"] == 130
    assert later["lookahead"]["future_bars"] >= 1
    assert later["decision_source"] == "integration"
    assert len(store.store) >= 2
