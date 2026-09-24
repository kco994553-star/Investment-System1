"""Synthetic N-company builders for universe/incremental tests and the 500 benchmark.

SYNTHETIC only. Values are deterministic functions of the index, not market data.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from investment_system.contracts.models import DataStamp
from investment_system.contracts.raw import RawFundamentals
from investment_system.contracts.universe import UniverseMember


def cid(i: int) -> str:
    return f"syn{i:03d}"


def roster(n: int) -> tuple[UniverseMember, ...]:
    return tuple(UniverseMember(cid(i), f"S{i:03d}", entered_on="2015-01-01", cik=f"{9000000 + i:010d}") for i in range(n))


def stamp(company_id: str, available_at: datetime, tag: str = "a") -> DataStamp:
    return DataStamp(
        data_stamp_id=f"st_{company_id}_{tag}",
        source_provider="synthetic",
        source_type="fundamentals",
        source_reference=company_id,
        published_at=available_at,
        available_at=available_at,
        observed_at=available_at,
        synthetic=True,
    )


def raw(i: int, available_at: datetime, tag: str = "a", bump: float = 1.0) -> RawFundamentals:
    c = cid(i)
    rev = (100.0 + i) * bump
    return RawFundamentals(
        company_id=c,
        stamp=stamp(c, available_at, tag),
        revenue=rev,
        revenue_prev=rev / (1.05 + (i % 7) / 100),
        ebit=rev * (0.10 + (i % 11) / 100),
        ebit_prev=rev * 0.09,
        fcf=rev * 0.08,
        net_income=rev * 0.07,
        equity=rev * 0.6,
        invested_capital=rev * 0.9,
        cash=rev * 0.2,
        total_debt=rev * 0.3,
        shares=10.0 + i,
        eps=1.0 + (i % 13) / 10,
        eps_prev=1.0,
        price=20.0 + (i % 17),
        source_kind="SYNTHETIC",
    )


def companyfacts(i: int, base_year: int = 2023, full: bool = False) -> dict:
    """Minimal SEC-companyfacts-shaped payload for the PIT historical path.

    full=True adds balance-sheet / income concepts so Q can be scored.
    """
    rows = []
    eps = []
    for k, y in enumerate((base_year, base_year + 1)):
        filed = f"{y + 1}-02-15"
        rows.append({"end": f"{y}-12-31", "val": (100 + i) * (1 + 0.05 * k), "filed": filed, "form": "10-K", "fy": y, "fp": "FY", "accn": f"a{i}{y}"})
        eps.append({"end": f"{y}-12-31", "val": 1.0 + 0.1 * k + (i % 5) / 10, "filed": filed, "form": "10-K", "fy": y, "fp": "FY", "accn": f"a{i}{y}"})
    gaap = {
        "RevenueFromContractWithCustomerExcludingAssessedTax": {"units": {"USD": rows}},
        "EarningsPerShareDiluted": {"units": {"USD/shares": eps}},
    }
    if full:
        def scaled(f):
            return [{**r, "val": r["val"] * f} for r in rows]
        gaap.update({
            "NetIncomeLoss": {"units": {"USD": scaled(0.08 + (i % 7) / 100)}},
            "OperatingIncomeLoss": {"units": {"USD": scaled(0.12 + (i % 9) / 100)}},
            "StockholdersEquity": {"units": {"USD": scaled(0.7)}},
            "CashAndCashEquivalentsAtCarryingValue": {"units": {"USD": scaled(0.2)}},
            "LongTermDebt": {"units": {"USD": scaled(0.3 + (i % 5) / 10)}},
            "NetCashProvidedByUsedInOperatingActivities": {"units": {"USD": scaled(0.15)}},
            "PaymentsToAcquirePropertyPlantAndEquipment": {"units": {"USD": scaled(0.05)}},
        })
    return {"facts": {"us-gaap": gaap}}


def bars(i: int, start: datetime, days: int, step: int = 7) -> list[dict]:
    out = []
    for k in range(0, days, step):
        out.append({
            "price": 20.0 + (i % 17) + k * 0.01 * (1 + i % 3),
            "observed_at": start + timedelta(days=k),
            "adjusted": True,
        })
    return out


UTC = timezone.utc
