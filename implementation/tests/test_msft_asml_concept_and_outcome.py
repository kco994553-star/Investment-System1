from datetime import datetime, timezone

from investment_system.contracts.enums import TrackScope
from investment_system.providers.sec_companyfacts import facts_to_raw
from investment_system.validation.file_store import FileTrackRecordStore
from investment_system.validation.historical import attach_price_outcome
from investment_system.validation.records import ScopedTrackStore

AS_A = datetime(2024, 6, 30, tzinfo=timezone.utc)
AS_B = datetime(2025, 6, 30, tzinfo=timezone.utc)

MSFT_LIKE = {
    "facts": {
        "us-gaap": {
            "Revenues": {
                "units": {
                    "USD": [
                        {"end": "2010-06-30", "val": 16039000000, "filed": "2010-07-30", "form": "10-K", "fy": 2010, "fp": "FY", "accn": "old"}
                    ]
                }
            },
            "RevenueFromContractWithCustomerExcludingAssessedTax": {
                "units": {
                    "USD": [
                        {"end": "2023-06-30", "val": 211915000000, "filed": "2023-07-27", "form": "10-K", "fy": 2023, "fp": "FY", "accn": "a"},
                        {"end": "2024-06-30", "val": 245122000000, "filed": "2024-07-30", "form": "10-K", "fy": 2024, "fp": "FY", "accn": "b"},
                    ]
                }
            }
        }
    }
}

ASML_EUR = {
    "facts": {
        "us-gaap": {
            "RevenueFromContractWithCustomerExcludingAssessedTax": {
                "units": {
                    "EUR": [
                        {"end": "2024-12-31", "val": 28262000000, "filed": "2025-03-05", "form": "20-F", "fy": 2024, "fp": "FY", "accn": "a"}
                    ]
                }
            }
        }
    }
}


def test_prefers_contract_revenue_over_stale_revenues():
    raw_a = facts_to_raw("msft", "0000789019", MSFT_LIKE, AS_A, synthetic=True)
    raw_b = facts_to_raw("msft", "0000789019", MSFT_LIKE, AS_B, synthetic=True)
    assert raw_a.revenue == 211915000000
    assert raw_b.revenue == 245122000000
    assert raw_a.revenue != 16039000000


def test_asml_eur_20f_without_fx_conversion():
    raw = facts_to_raw("asml", "0000937966", ASML_EUR, datetime(2025, 6, 30, tzinfo=timezone.utc), synthetic=True)
    assert raw.revenue == 28262000000
    assert raw.reporting_currency == "EUR"
    assert "CURRENCY_NON_USD" in raw.stamp.quality_flags


def test_outcome_prices_do_not_enter_prediction(tmp_path):
    store = ScopedTrackStore(FileTrackRecordStore(tmp_path / "t.json"))
    rec = store.record(
        TrackScope.INTEGRATED,
        "nvda",
        AS_A,
        ("s1",),
        {"prediction": {"expected_return": 0.0}, "decision": {"source": "integration"}, "evaluation_horizon": "20d"},
    )
    bars = [
        {"price": 100.0, "observed_at": AS_A},
        {"price": 110.0, "observed_at": AS_B},
    ]
    child = attach_price_outcome(store, rec.track_record_id, AS_A, AS_B, bars)
    parent = store.store.get(rec.track_record_id)
    assert "110" not in str(parent.payload.get("prediction"))
    assert abs(child.outcome_metrics["realized"]["realized_return"] - 0.1) < 1e-9
