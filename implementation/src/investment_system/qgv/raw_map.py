"""Map raw fundamentals to factor observations. NEW IMPLEMENTATION.

Decision D-09: explicit, fail-closed, no silent zero-fill.
Decision D-10: growth/margin mapping is a linear clip heuristic, PROVISIONAL.
Synthetic raw is tagged SYNTHETIC and is not real evidence.
"""

from __future__ import annotations

from ..contracts.enums import ProfileKind, QualityState
from ..contracts.models import FactorObservation
from ..contracts.raw import RawFundamentals
from .factors import G_WEIGHTS, Q_WEIGHTS, V_FACTORS


def _clip_score(value: float) -> float:
    return max(0.0, min(100.0, value))


def _obs(fid: str, score: float | None, quality: QualityState, stamp_id: str | None, notes: str) -> FactorObservation:
    return FactorObservation(
        factor_id=fid,
        raw_value=score,
        score_0_100=score if quality not in {QualityState.MISSING_DATA, QualityState.BLOCKED_DEPENDENCY, QualityState.PIT_UNAVAILABLE} else None,
        quality=quality,
        stamp_id=stamp_id,
        notes=notes,
    )


def _ratio(num: float | None, den: float | None) -> float | None:
    if num is None or den is None or den == 0:
        return None
    return num / den


def _yoy(cur: float | None, prev: float | None) -> float | None:
    if cur is None or prev is None or prev == 0:
        return None
    return cur / prev - 1.0


def _growth_to_score(yoy: float | None) -> float | None:
    if yoy is None:
        return None
    # 0% growth → 50, +25% → 100, -25% → 0. PROVISIONAL.
    return _clip_score(50.0 + yoy / 0.25 * 50.0)


def _spread_to_score(spread: float | None) -> float | None:
    if spread is None:
        return None
    # ROIC-WACC 0 → 50, +10pp → 100. PROVISIONAL.
    return _clip_score(50.0 + spread / 0.10 * 50.0)


def _central_value_score(raw) -> float | None:
    if raw.dcf_value and raw.price:
        return _clip_score(50.0 + ((raw.dcf_value / raw.price) - 1.0) / 0.4 * 50.0)
    if raw.price and raw.eps and raw.eps > 0:
        pe = raw.price / raw.eps
        return _clip_score(50.0 + (20.0 - pe) / 20.0 * 50.0)
    return None


def _mos_score(raw) -> float | None:
    if raw.dcf_value and raw.price:
        conservative = 0.75 * raw.dcf_value
        return _clip_score(50.0 + ((conservative / raw.price) - 1.0) / 0.3 * 50.0)
    if raw.price and raw.eps and raw.eps > 0:
        conservative = 12.0 * raw.eps
        return _clip_score(50.0 + ((conservative / raw.price) - 1.0) / 0.3 * 50.0)
    return None


def _reverse_dcf_score(raw) -> float | None:
    implied = raw.reverse_dcf_implied_growth
    if implied is None and raw.price and raw.eps and raw.eps > 0:
        pe = raw.price / raw.eps
        implied = max(-0.2, min(0.4, (pe - 15.0) / 100.0))
    realized = _yoy(raw.revenue, raw.revenue_prev)
    if implied is None or realized is None:
        return None
    return _clip_score(50.0 + (realized - implied) / 0.15 * 50.0)


def map_raw(raw: RawFundamentals) -> dict[str, FactorObservation]:
    stamp_id = raw.stamp.data_stamp_id
    syn = "SYNTHETIC" if raw.source_kind == "SYNTHETIC" or raw.stamp.synthetic else "MAPPED"
    quality_ok = QualityState.SYNTHETIC if raw.stamp.synthetic or raw.source_kind == "SYNTHETIC" else QualityState.OK

    revenue_yoy = _yoy(raw.revenue, raw.revenue_prev)
    eps_yoy = _yoy(raw.eps, raw.eps_prev)
    ebit_margin = _ratio(raw.ebit, raw.revenue)
    fcf_margin = _ratio(raw.fcf, raw.revenue)
    roic = _ratio(raw.net_income, raw.invested_capital) if raw.invested_capital else None
    roic_wacc = (roic - raw.wacc) if (roic is not None and raw.wacc is not None) else None
    net_cash = None
    if raw.cash is not None and raw.total_debt is not None:
        net_cash = raw.cash - raw.total_debt
    health = None
    if net_cash is not None and raw.revenue:
        health = _clip_score(50.0 + (net_cash / raw.revenue) / 0.4 * 50.0)
    financial = raw.profile_kind == ProfileKind.FINANCIAL.value or raw.profile_kind == "FINANCIAL"
    if financial and raw.cet1 is not None:
        health = _clip_score(50.0 + (raw.cet1 - 0.12) / 0.04 * 50.0)

    fcf_quality = None
    if fcf_margin is not None:
        fcf_quality = _clip_score(50.0 + fcf_margin / 0.15 * 50.0)
    margin_quality = None
    if ebit_margin is not None:
        margin_quality = _clip_score(50.0 + ebit_margin / 0.25 * 50.0)
    if financial and raw.nim is not None:
        margin_quality = _clip_score(50.0 + (raw.nim - 0.025) / 0.015 * 50.0)

    market_pos = None
    if raw.market_share is not None and raw.peer_median_market_share:
        market_pos = _clip_score(50.0 + (raw.market_share - raw.peer_median_market_share) / 0.10 * 50.0)
    elif raw.market_share is not None:
        market_pos = _clip_score(raw.market_share * 400.0)  # 25% share → 100

    growth_eff = None
    if revenue_yoy is not None and raw.invested_capital and raw.revenue:
        growth_eff = _clip_score(50.0 + revenue_yoy / max(raw.invested_capital / raw.revenue, 0.05) * 20.0)

    excess = None
    if revenue_yoy is not None and raw.industry_revenue_growth is not None:
        excess = _clip_score(50.0 + (revenue_yoy - raw.industry_revenue_growth) / 0.15 * 50.0)

    values: dict[str, tuple[float | None, str]] = {
        "competitive_advantage": (raw.competitive_advantage_rubric, "rubric"),
        "roic_wacc": ( _spread_to_score(roic_wacc), "roic-wacc spread"),
        "market_position": (market_pos, "share vs peer"),
        "fcf_quality": (fcf_quality, "fcf margin"),
        "margin_quality": (margin_quality, "ebit margin"),
        "financial_health": (health, "net cash / revenue"),
        "management_quality": (raw.management_quality_rubric, "rubric C-03"),
        "next_3_5y_growth": (_growth_to_score(revenue_yoy), "proxy: last yoy; not a 3-5y forecast"),
        "growth_efficiency": (growth_eff, "yoy / capital intensity"),
        "revenue_growth": (_growth_to_score(revenue_yoy), "revenue yoy"),
        "eps_fcf_per_share_growth": (_growth_to_score(eps_yoy if eps_yoy is not None else _yoy(raw.fcf, raw.revenue_prev)), "eps or fcf yoy"),
        "growth_durability": (raw.growth_durability_rubric, "rubric"),
        "excess_growth_vs_industry": (excess, "yoy minus industry"),
        "fundamental_value": (_central_value_score(raw), "central intrinsic; not MOS"),
        "peer_relative_value": (
            _clip_score(50.0 + ((raw.peer_median_multiple - raw.own_multiple) / raw.peer_median_multiple) / 0.3 * 50.0)
            if raw.peer_median_multiple and raw.own_multiple
            else None,
            "vs peer multiple only",
        ),
        "historical_valuation": (raw.hist_valuation_percentile, "own history percentile; not peer"),
        "sector_context": (raw.sector_context_score, "sector regime context; not theme"),
        "theme_premium_discount": (raw.theme_premium_score, "theme overlay; not sector"),
        "reverse_dcf": (_reverse_dcf_score(raw), "implied growth vs realized yoy; does not write G"),
        "margin_of_safety": (_mos_score(raw), "conservative value vs price; not central FV"),
    }

    out: dict[str, FactorObservation] = {}
    wanted = set(Q_WEIGHTS) | set(G_WEIGHTS) | set(V_FACTORS)
    for fid in wanted:
        score, note = values.get(fid, (None, "unmapped"))
        if financial and fid == "roic_wacc":
            out[fid] = _obs(fid, None, QualityState.NOT_APPLICABLE, stamp_id, f"{syn};FINANCIAL ROIC N/A")
            continue
        if score is None:
            out[fid] = _obs(fid, None, QualityState.MISSING_DATA, stamp_id, f"{syn};{note};missing")
        else:
            out[fid] = _obs(fid, float(score), quality_ok, stamp_id, f"{syn};{note}")
    return out
