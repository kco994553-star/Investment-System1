"""Generic portfolio input. NEW IMPLEMENTATION.

Official v1.1 and US-working books are REFERENCE_FIXTURE only.
They are not the default engine portfolio and not the implicit PIT book.
"""

from __future__ import annotations

from dataclasses import dataclass


ROLE_GENERIC = "GENERIC_INPUT"
ROLE_FIXTURE = "REFERENCE_FIXTURE"


@dataclass(frozen=True)
class HoldingInput:
    company_id: str
    ticker: str
    target_weight: float


@dataclass(frozen=True)
class PortfolioInput:
    name: str
    holdings: tuple[HoldingInput, ...]
    cash_weight: float = 0.0
    base_currency: str = "USD"
    role: str = ROLE_GENERIC
    version: str = "generic-input"

    def weight_sum(self) -> float:
        return sum(h.target_weight for h in self.holdings) + self.cash_weight


def equal_weight_input(name: str, pairs: tuple[tuple[str, str], ...], cash_weight: float = 0.0) -> PortfolioInput:
    n = len(pairs)
    if n == 0:
        raise ValueError("empty portfolio input")
    w = (1.0 - cash_weight) / n
    holdings = tuple(HoldingInput(cid, ticker, w) for cid, ticker in pairs)
    return PortfolioInput(name=name, holdings=holdings, cash_weight=cash_weight, role=ROLE_GENERIC, version="generic-equal-weight")
