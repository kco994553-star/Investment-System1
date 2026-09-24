"""Build 10-Q point series for G quarterly_monitor. NEW IMPLEMENTATION.

Not a Frozen G input. Empty when no 10-Q rows exist.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from ..providers.sec_vintage import FactVintage, resolve_vintages
from .g_horizon import GHorizonConfig, QuarterlyFundamentalPoint, assess_horizon, quarterly_monitor


def _end_date(v: FactVintage) -> date | None:
    if not v.end:
        return None
    try:
        return date.fromisoformat(v.end[:10])
    except ValueError:
        return None


def _is_quarter_span(v: FactVintage) -> bool:
    if not v.start or not v.end:
        return v.fp.upper().startswith("Q")
    try:
        a = date.fromisoformat(v.start[:10])
        b = date.fromisoformat(v.end[:10])
    except ValueError:
        return v.fp.upper().startswith("Q")
    days = (b - a).days
    return 70 <= days <= 110


def _latest_by_end(vintages: list[FactVintage]) -> dict[date, FactVintage]:
    out: dict[date, FactVintage] = {}
    for v in vintages:
        if not _is_quarter_span(v):
            continue
        end = _end_date(v)
        if end is None:
            continue
        prev = out.get(end)
        if prev is None or (v.filed, v.accn) > (prev.filed, prev.accn):
            out[end] = v
    return out


def collect_10q(
    payload: dict[str, Any],
    as_of: datetime,
    concepts: tuple[tuple[str, str, str], ...],
) -> dict[date, float]:
    merged: dict[date, FactVintage] = {}
    for tax, concept, unit in concepts:
        rows = resolve_vintages(payload, tax, concept, unit, as_of, "10-Q")
        rows = [r for r in rows if str(r.form).upper().startswith("10-Q")]
        for end, v in _latest_by_end(rows).items():
            prev = merged.get(end)
            if prev is None or (v.end, v.filed) > (prev.end, prev.filed):
                merged[end] = v
    return {end: v.value for end, v in merged.items()}


REV_CONCEPTS = (
    ("us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax", "USD"),
    ("us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax", "EUR"),
    ("us-gaap", "Revenues", "USD"),
)
EPS_CONCEPTS = (
    ("us-gaap", "EarningsPerShareDiluted", "USD/shares"),
    ("us-gaap", "EarningsPerShareDiluted", "EUR/shares"),
    ("us-gaap", "EarningsPerShareBasic", "USD/shares"),
    ("us-gaap", "EarningsPerShareBasic", "EUR/shares"),
)
FCF_CONCEPTS = (
    ("us-gaap", "FreeCashFlow", "USD"),
    ("us-gaap", "FreeCashFlow", "EUR"),
)


def quarterly_points_from_facts(payload: dict[str, Any], as_of: datetime) -> list[QuarterlyFundamentalPoint]:
    rev = collect_10q(payload, as_of, REV_CONCEPTS)
    eps = collect_10q(payload, as_of, EPS_CONCEPTS)
    fcf = collect_10q(payload, as_of, FCF_CONCEPTS)
    ends = sorted(set(rev) | set(eps) | set(fcf))
    return [
        QuarterlyFundamentalPoint(period_end=end, revenue=rev.get(end), eps=eps.get(end), fcf_per_share=fcf.get(end))
        for end in ends
    ]


def window_points(points: list[QuarterlyFundamentalPoint], config: GHorizonConfig | None = None) -> list[QuarterlyFundamentalPoint]:
    cfg = config or GHorizonConfig()
    rows = sorted(points, key=lambda p: p.period_end)
    n = cfg.requested_quarters
    if n <= 0:
        return []
    return rows[-n:]


def monitor_from_facts(payload: dict[str, Any], as_of: datetime, config: GHorizonConfig | None = None) -> dict:
    cfg = config or GHorizonConfig()
    points = quarterly_points_from_facts(payload, as_of)
    if not points:
        cov = assess_horizon(cfg, 0)
        return {
            "status": "MISSING",
            "quarter_count": 0,
            "note": "NO_10Q_ROWS; not a Frozen G input",
            "horizon": cfg.requested_horizon,
            "coverage_state": cov.coverage_state,
        }
    windowed = window_points(points, cfg)
    cov = assess_horizon(cfg, len(points))
    mon = quarterly_monitor(windowed)
    mon["note"] = "RAW_EVIDENCE_ONLY; does not mutate Frozen G score"
    mon["source_form"] = "10-Q"
    mon["horizon"] = cfg.requested_horizon
    mon["window_quarters"] = len(windowed)
    mon["available_quarters_total"] = len(points)
    mon["coverage_state"] = cov.coverage_state
    mon["fallback_used"] = cov.fallback_used
    return mon
