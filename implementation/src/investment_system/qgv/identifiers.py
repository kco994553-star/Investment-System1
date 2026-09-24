"""Identifier registry. NEW IMPLEMENTATION.

C-08 TEL is isolated: Tokyo Electron is company_id=tokyo_electron.
Bare ticker TEL is AMBIGUOUS and never silently mapped to US TE Connectivity.
Conflict is not closed.
"""

from __future__ import annotations

from ..contracts.enums import QualityState
from ..contracts.models import Identifier


OFFICIAL_PORTFOLIO_V11 = (
    Identifier("asml", "ASML Holding", "ASML", "ASML", "NASDAQ", sector="Semicap"),
    Identifier("lrcx", "Lam Research", "LRCX", "LRCX", "NASDAQ", sector="Semicap"),
    Identifier("klac", "KLA Corporation", "KLAC", "KLAC", "NASDAQ", sector="Semicap"),
    Identifier(
        "tokyo_electron",
        "Tokyo Electron Limited",
        "Tokyo Electron",
        "TEL",
        exchange=None,
        country="JP",
        sector="Semicap",
        ambiguity_flags=("C-08_TEL_MARKET_ID_UNFIXED",),
    ),
    Identifier("hanmi", "Hanmi Semiconductor", "한미반도체", "042700", "KRX", country="KR", sector="Semicap"),
    Identifier("nvda", "NVIDIA Corporation", "NVDA", "NVDA", "NASDAQ", sector="AI"),
    Identifier("amd", "Advanced Micro Devices", "AMD", "AMD", "NASDAQ", sector="AI"),
    Identifier("avgo", "Broadcom", "AVGO", "AVGO", "NASDAQ", sector="AI"),
    Identifier("qcom", "Qualcomm", "QCOM", "QCOM", "NASDAQ", sector="AI"),
    Identifier("intc", "Intel", "INTC", "INTC", "NASDAQ", sector="AI"),
    Identifier("msft", "Microsoft", "MSFT", "MSFT", "NASDAQ", sector="BigTech"),
    Identifier("googl", "Alphabet", "GOOGL", "GOOGL", "NASDAQ", sector="BigTech"),
    Identifier("amzn", "Amazon", "AMZN", "AMZN", "NASDAQ", sector="BigTech"),
    Identifier("rtx", "RTX Corporation", "RTX", "RTX", "NYSE", sector="Other"),
    Identifier("stry", "Stryker", "Stryker", "SYK", "NYSE", sector="Other"),
    Identifier("etn", "Eaton", "Eaton", "ETN", "NYSE", sector="Other"),
    Identifier("hubb", "Hubbell", "Hubbell", "HUBB", "NYSE", sector="Other"),
    Identifier("gev", "GE Vernova", "GE Vernova", "GEV", "NYSE", sector="Other"),
    Identifier("rok", "Rockwell Automation", "Rockwell", "ROK", "NYSE", sector="Other"),
)

# Ambiguous bare tickers that must not auto-resolve.
AMBIGUOUS_TICKERS = {
    "TEL": QualityState.IDENTIFIER_AMBIGUOUS,
}


class IdentifierRegistry:
    def __init__(self, records: tuple[Identifier, ...] = OFFICIAL_PORTFOLIO_V11):
        self._by_id = {r.company_id: r for r in records}
        self._by_ticker: dict[str, list[Identifier]] = {}
        for r in records:
            self._by_ticker.setdefault(r.ticker.upper(), []).append(r)

    def get(self, company_id: str) -> Identifier:
        if company_id not in self._by_id:
            raise KeyError(f"unknown company_id={company_id}")
        return self._by_id[company_id]

    def resolve_ticker(self, ticker: str) -> Identifier | QualityState:
        key = ticker.upper()
        if key in AMBIGUOUS_TICKERS:
            return QualityState.IDENTIFIER_AMBIGUOUS
        hits = self._by_ticker.get(key, [])
        if len(hits) == 1:
            return hits[0]
        if not hits:
            raise KeyError(f"unknown ticker={ticker}")
        return QualityState.IDENTIFIER_AMBIGUOUS
