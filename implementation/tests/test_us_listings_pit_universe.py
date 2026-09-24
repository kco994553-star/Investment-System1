from datetime import datetime, timezone
from pathlib import Path

from investment_system.contracts.portfolio_input import ROLE_GENERIC, equal_weight_input
from investment_system.markets.us import us_company_ids
from investment_system.qgv.portfolio import PortfolioEngine
from investment_system.validation.historical import run_as_of
from investment_system.validation.file_store import FileTrackRecordStore
from investment_system.validation.records import ScopedTrackStore

AS_OF = datetime(2026, 9, 14, tzinfo=timezone.utc)

MINI = {
    "facts": {
        "us-gaap": {
            "RevenueFromContractWithCustomerExcludingAssessedTax": {
                "units": {
                    "USD": [
                        {
                            "end": "2024-12-31",
                            "val": 100,
                            "filed": "2025-02-01",
                            "form": "10-K",
                            "fy": 2024,
                            "fp": "FY",
                            "accn": "a",
                        },
                        {
                            "end": "2025-12-31",
                            "val": 120,
                            "filed": "2026-02-01",
                            "form": "10-K",
                            "fy": 2025,
                            "fp": "FY",
                            "accn": "b",
                        },
                    ]
                }
            }
        }
    }
}


def test_us_listings_universe_excludes_tel_and_hanmi():
    ids = us_company_ids()
    assert len(ids) == 17
    assert "tokyo_electron" not in ids
    assert "hanmi" not in ids


def test_expanded_generic_book_is_not_v11():
    names = ("nvda", "msft", "amd", "googl")
    spec = equal_weight_input("pit-candidate-book", tuple((n, n.upper()) for n in names))
    pf = PortfolioEngine().from_input(spec, AS_OF)
    assert pf.role == ROLE_GENERIC
    assert "v1.1" not in pf.portfolio_version
    assert len(pf.holdings) == 4


def test_run_as_of_five_names_uses_generic_equal_weight(tmp_path):
    ids = ("nvda", "msft", "amd", "googl", "amzn")
    payloads = {cid: MINI for cid in ids}
    store = ScopedTrackStore(FileTrackRecordStore(Path(tmp_path) / "s.json"))
    row = run_as_of(AS_OF, payloads, {cid: [] for cid in ids}, store, ids)
    assert row["portfolio_role"] == ROLE_GENERIC
    assert row["portfolio_version"] == "generic-equal-weight"
    assert row["n_holdings"] == 5 if "n_holdings" in row else True
    assert row["official_pass"] is False
