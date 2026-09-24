"""SEC companyfacts adapter. NEW TOOLING.

Does not store API secrets. Uses the public companyfacts JSON shape.
Live fetch is optional and fail-closed. A successful live pull is LIVE_FETCH,
not Stage 2 PASS and not ORIGINAL artifact recovery.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from ..contracts.models import DataStamp
from ..contracts.raw import RawFundamentals
from ..pit.resolver import is_available


SEC_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
USER_AGENT = "InvestmentSystem1Research contact@example.invalid"


def _parse_iso(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _form_ok(row: dict[str, Any], form_filter: str | None) -> bool:
    if not form_filter:
        return True
    form = str(row.get("form") or "").upper()
    if not form:
        return True
    if form_filter == "10-K":
        return form in {"10-K", "10-K/A", "20-F", "20-F/A", "40-F"}
    if form_filter == "10-Q":
        return form.startswith("10-Q") or form in {"6-K"}
    return form == form_filter


def _ranked_unit_facts(
    facts: dict[str, Any],
    taxonomy: str,
    concept: str,
    unit: str,
    as_of: datetime,
    form_filter: str | None = "10-K",
) -> list[tuple[float, datetime]]:
    node = facts.get("facts", {}).get(taxonomy, {}).get(concept, {})
    units = node.get("units", {}).get(unit, [])
    eligible = []
    for row in units:
        if not _form_ok(row, form_filter):
            continue
        filed = row.get("filed") or row.get("end")
        if not filed:
            continue
        try:
            filed_dt = _parse_iso(str(filed) + ("T00:00:00+00:00" if "T" not in str(filed) else ""))
        except ValueError:
            continue
        if filed_dt <= as_of and row.get("val") is not None:
            labeled = bool(str(row.get("form") or "").strip())
            eligible.append((float(row["val"]), filed_dt, labeled))
    eligible.sort(key=lambda x: x[1])
    return eligible


def _latest_unit_fact(facts: dict[str, Any], taxonomy: str, concept: str, unit: str, as_of: datetime, form_filter: str | None = "10-K") -> tuple[float, datetime, bool] | None:
    from .sec_vintage import resolve_vintages, select_latest

    hit = select_latest(resolve_vintages(facts, taxonomy, concept, unit, as_of, form_filter))
    if hit is None:
        ranked = _ranked_unit_facts(facts, taxonomy, concept, unit, as_of, form_filter)
        return ranked[-1] if ranked else None
    return hit.value, hit.filed, hit.labeled


def _previous_unit_fact(facts: dict[str, Any], taxonomy: str, concept: str, unit: str, as_of: datetime, form_filter: str | None = "10-K") -> tuple[float, datetime, bool] | None:
    from .sec_vintage import resolve_vintages, select_latest, select_previous

    vintages = resolve_vintages(facts, taxonomy, concept, unit, as_of, form_filter)
    prev = select_previous(vintages, select_latest(vintages))
    if prev is None:
        ranked = _ranked_unit_facts(facts, taxonomy, concept, unit, as_of, form_filter)
        return ranked[-2] if len(ranked) >= 2 else None
    return prev.value, prev.filed, prev.labeled


REVENUE_CONCEPTS = (
    ("us-gaap", "Revenues", "USD"),
    ("us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax", "USD"),
    ("us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax", "EUR"),
    ("ifrs-full", "Revenue", "EUR"),
    ("ifrs-full", "Revenue", "USD"),
)


def facts_to_raw(company_id: str, cik: str, payload: dict[str, Any], as_of: datetime, *, synthetic: bool = False, form_filter: str | None = "10-K") -> RawFundamentals:
    filed_dates: list[datetime] = []
    labels: list[bool] = []
    units_used: list[str] = []

    def grab(*concepts: tuple[str, str, str]) -> float | None:
        for tax, concept, unit in concepts:
            hit = _latest_unit_fact(payload, tax, concept, unit, as_of, form_filter)
            if hit:
                filed_dates.append(hit[1])
                labels.append(hit[2])
                units_used.append(unit)
                return hit[0]
        return None

    def grab_prev(*concepts: tuple[str, str, str]) -> float | None:
        for tax, concept, unit in concepts:
            hit = _previous_unit_fact(payload, tax, concept, unit, as_of, form_filter)
            if hit:
                filed_dates.append(hit[1])
                labels.append(hit[2])
                return hit[0]
        return None

    from .sec_vintage import resolve_vintages, select_across_concepts, select_previous

    rev_hit = select_across_concepts(payload, REVENUE_CONCEPTS, as_of, form_filter)
    if rev_hit:
        revenue = rev_hit.value
        filed_dates.append(rev_hit.filed)
        labels.append(rev_hit.labeled)
        units_used.append(rev_hit.unit)
        prev_hit = select_previous(
            resolve_vintages(payload, rev_hit.taxonomy, rev_hit.concept, rev_hit.unit, as_of, form_filter),
            rev_hit,
        )
        if prev_hit:
            revenue_prev = prev_hit.value
            filed_dates.append(prev_hit.filed)
            labels.append(prev_hit.labeled)
        else:
            revenue_prev = None
    else:
        revenue = grab(*REVENUE_CONCEPTS)
        revenue_prev = grab_prev(*REVENUE_CONCEPTS)

    def pick(concepts: tuple[tuple[str, str, str], ...]) -> float | None:
        hit = select_across_concepts(payload, concepts, as_of, form_filter)
        if hit is None:
            return grab(*concepts)
        filed_dates.append(hit.filed)
        labels.append(hit.labeled)
        units_used.append(hit.unit)
        return hit.value

    def pick_series(concepts: tuple[tuple[str, str, str], ...]) -> tuple[float | None, float | None]:
        hit = select_across_concepts(payload, concepts, as_of, form_filter)
        if hit is None:
            return grab(*concepts), grab_prev(*concepts)
        filed_dates.append(hit.filed)
        labels.append(hit.labeled)
        units_used.append(hit.unit)
        prev = select_previous(
            resolve_vintages(payload, hit.taxonomy, hit.concept, hit.unit, as_of, form_filter),
            hit,
        )
        if prev:
            filed_dates.append(prev.filed)
            labels.append(prev.labeled)
            return hit.value, prev.value
        return hit.value, None

    net_income = pick(
        (
            ("us-gaap", "NetIncomeLoss", "USD"),
            ("us-gaap", "NetIncomeLoss", "EUR"),
            ("ifrs-full", "ProfitLoss", "EUR"),
            ("ifrs-full", "ProfitLoss", "USD"),
        )
    )
    cash = pick(
        (
            ("us-gaap", "CashAndCashEquivalentsAtCarryingValue", "USD"),
            ("us-gaap", "CashAndCashEquivalentsAtCarryingValue", "EUR"),
        )
    )
    debt = pick(
        (
            ("us-gaap", "LongTermDebt", "USD"),
            ("us-gaap", "LongTermDebt", "EUR"),
            ("us-gaap", "LongTermDebtNoncurrent", "USD"),
            ("us-gaap", "LongTermDebtNoncurrent", "EUR"),
        )
    )
    equity = pick(
        (
            ("us-gaap", "StockholdersEquity", "USD"),
            ("us-gaap", "StockholdersEquity", "EUR"),
            ("us-gaap", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest", "USD"),
            ("us-gaap", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest", "EUR"),
        )
    )
    shares = grab(
        ("us-gaap", "CommonStockSharesOutstanding", "shares"),
        ("us-gaap", "CommonStockSharesOutstanding", "Shares"),
    )
    ebit = pick(
        (
            ("us-gaap", "OperatingIncomeLoss", "USD"),
            ("us-gaap", "OperatingIncomeLoss", "EUR"),
        )
    )
    fcf, fcf_prev = pick_series(
        (
            ("us-gaap", "FreeCashFlow", "USD"),
            ("us-gaap", "FreeCashFlow", "EUR"),
        )
    )
    if fcf is None:
        cfo = pick(
            (
                ("us-gaap", "NetCashProvidedByUsedInOperatingActivities", "USD"),
                ("us-gaap", "NetCashProvidedByUsedInOperatingActivities", "EUR"),
            )
        )
        capex = pick(
            (
                ("us-gaap", "PaymentsToAcquirePropertyPlantAndEquipment", "USD"),
                ("us-gaap", "PaymentsToAcquirePropertyPlantAndEquipment", "EUR"),
            )
        )
        if cfo is not None and capex is not None:
            fcf = cfo - abs(capex)
    eps, eps_prev = pick_series(
        (
            ("us-gaap", "EarningsPerShareDiluted", "USD/shares"),
            ("us-gaap", "EarningsPerShareDiluted", "EUR/shares"),
            ("us-gaap", "EarningsPerShareDiluted", "USD-per-shares"),
            ("us-gaap", "EarningsPerShareBasic", "USD/shares"),
            ("us-gaap", "EarningsPerShareBasic", "EUR/shares"),
            ("us-gaap", "EarningsPerShareDiluted", "pure"),
        )
    )
    published = max(filed_dates) if filed_dates else as_of
    unlabeled = bool(labels) and not all(labels)
    period_quality = "PARTIAL" if unlabeled or not labels else "FORM_ALIGNED"
    flags = ("UNLABELED_SEC_FORM",) if unlabeled or (labels and not all(labels)) else ()
    if not labels:
        flags = ("UNLABELED_SEC_FORM",)
        period_quality = "PARTIAL"
    currency = "EUR" if units_used and units_used[0] == "EUR" else "USD"
    if currency != "USD":
        flags = tuple(flags) + ("CURRENCY_NON_USD",)
    stamp = DataStamp(
        data_stamp_id=f"sec_{company_id}_{as_of.date().isoformat()}",
        source_provider="sec-companyfacts",
        source_type="fundamentals",
        source_reference=f"CIK{cik}",
        published_at=published,
        available_at=published,
        observed_at=published,
        estimated=False,
        quality_flags=flags,
        synthetic=synthetic,
    )
    if not is_available(stamp, as_of):
        raise RuntimeError("SEC stamp failed PIT")
    kind = "SYNTHETIC" if synthetic else "LIVE_FETCH"
    return RawFundamentals(
        company_id=company_id,
        stamp=stamp,
        revenue=revenue,
        revenue_prev=revenue_prev,
        ebit=ebit,
        fcf=fcf,
        eps=eps,
        eps_prev=eps_prev,
        net_income=net_income,
        cash=cash,
        total_debt=debt,
        equity=equity,
        shares=shares,
        invested_capital=(equity + debt) if (equity is not None and debt is not None) else equity,
        source_kind=kind,
        period_quality=period_quality,
        reporting_currency=currency,
    )


def load_facts_file(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def try_fetch_companyfacts(cik: str, timeout: float = 8.0) -> dict[str, Any] | None:
    padded = cik.zfill(10)
    url = SEC_FACTS_URL.format(cik=padded)
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (URLError, TimeoutError, ValueError, OSError):
        return None
