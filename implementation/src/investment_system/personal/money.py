"""Currency / FX boundary (PIL §19). Original currency is kept; conversion is explicit and never uses FX that is not
known at decision_time or older than the caller's stated limit."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from .quality import DataQuality
from .timecontract import TimeContractError, usable_at


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal):
            raise TypeError("Money.amount must be Decimal")
        if len(self.currency) != 3 or not self.currency.isupper():
            raise ValueError("currency must be an ISO 4217 code")


@dataclass(frozen=True)
class FxRate:
    fx_pair: str  # "USDKRW": 1 USD = rate KRW
    rate: Decimal
    fx_as_of: datetime
    available_at: datetime

    @property
    def base(self) -> str:
        return self.fx_pair[:3]

    @property
    def quote(self) -> str:
        return self.fx_pair[3:]


@dataclass(frozen=True)
class ConvertedMoney:
    original: Money
    converted: Money
    fx: FxRate
    base_currency: str
    quality: DataQuality


def convert(m: Money, fx: FxRate, base_currency: str, decision_time: datetime, max_age: timedelta) -> ConvertedMoney:
    """Convert m into base_currency with an explicit FX quote. FX not yet available -> error (look-ahead);
    FX older than max_age -> result marked STALE (not silently treated as current)."""
    if not usable_at(fx.available_at, decision_time):
        raise TimeContractError("FX quote not available at decision_time")
    if m.currency == fx.base and base_currency == fx.quote:
        amt = m.amount * fx.rate
    elif m.currency == fx.quote and base_currency == fx.base:
        amt = m.amount / fx.rate
    else:
        raise ValueError(f"FX pair {fx.fx_pair} does not convert {m.currency} -> {base_currency}")
    q = DataQuality.STALE if decision_time - fx.fx_as_of > max_age else DataQuality.VALID
    return ConvertedMoney(original=m, converted=Money(amt, base_currency), fx=fx, base_currency=base_currency, quality=q)
