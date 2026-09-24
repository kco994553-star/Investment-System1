"""Raw input contracts. NEW IMPLEMENTATION. Not original schema files."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .models import DataStamp


@dataclass(frozen=True)
class RawFundamentals:
    company_id: str
    stamp: DataStamp
    revenue: Optional[float] = None
    revenue_prev: Optional[float] = None
    ebit: Optional[float] = None
    ebit_prev: Optional[float] = None
    fcf: Optional[float] = None
    net_income: Optional[float] = None
    equity: Optional[float] = None
    invested_capital: Optional[float] = None
    cash: Optional[float] = None
    total_debt: Optional[float] = None
    shares: Optional[float] = None
    eps: Optional[float] = None
    eps_prev: Optional[float] = None
    industry_revenue_growth: Optional[float] = None
    market_share: Optional[float] = None
    peer_median_market_share: Optional[float] = None
    wacc: Optional[float] = None
    # Rubric inputs stay optional. Missing ≠ 0.
    competitive_advantage_rubric: Optional[float] = None
    management_quality_rubric: Optional[float] = None
    growth_durability_rubric: Optional[float] = None
    # Valuation raw
    dcf_value: Optional[float] = None
    price: Optional[float] = None
    peer_median_multiple: Optional[float] = None
    own_multiple: Optional[float] = None
    hist_valuation_percentile: Optional[float] = None
    sector_context_score: Optional[float] = None
    theme_premium_score: Optional[float] = None
    reverse_dcf_implied_growth: Optional[float] = None
    # FINANCIAL profile extensions (v1.7.6 §18.7). Do not invent a second Q model.
    rotce: Optional[float] = None
    cet1: Optional[float] = None
    nim: Optional[float] = None
    credit_quality: Optional[float] = None
    capital_return: Optional[float] = None
    deposit_funding: Optional[float] = None
    profile_kind: str = "GENERAL_CORPORATE"
    source_kind: str = "SYNTHETIC"
    period_quality: str = "UNKNOWN"
    reporting_currency: str = "USD"


@dataclass(frozen=True)
class PricePoint:
    company_id: str
    stamp: DataStamp
    price: float
    currency: str = "USD"


@dataclass
class ProviderRecord:
    available_at: datetime
    payload: object
    stamp: DataStamp
    tags: dict = field(default_factory=dict)
