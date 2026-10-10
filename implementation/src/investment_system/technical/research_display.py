"""GSQ-015 display-only calculations on validated synthetic daily sessions.

Pure RAM results. No model, TSV, QGV, provider, persistence or serializer wiring.
Periods and display defaults are fixed to the user's display-only approval.
"""
from dataclasses import dataclass, field, replace
from datetime import date, datetime, timezone
import math
from typing import Literal

from .daily_input import DailyInputSeries, PreparedDailyReturns, prepare_daily_returns


ROLE = "RESEARCH_DISPLAY_ONLY"


@dataclass(frozen=True)
class ResearchIndicatorSeries:
    indicator_id: str
    values: tuple[float | None, ...] = field(repr=False)
    unavailable_reasons: tuple[str | None, ...] = field(repr=False)
    default_visible: bool | None = None
    role: Literal["RESEARCH_DISPLAY_ONLY"] = field(default=ROLE, init=False)

    @property
    def latest_state(self) -> Literal["AVAILABLE", "NOT_AVAILABLE"]:
        return "AVAILABLE" if self.values and self.values[-1] is not None else "NOT_AVAILABLE"


@dataclass(frozen=True)
class ResearchDisplayData:
    sessions: tuple[date, ...]
    indicators: tuple[ResearchIndicatorSeries, ...] = field(repr=False)
    company_id: str = field(repr=False)
    listing_id: str = field(repr=False)
    currency: str
    price_basis: str
    role: Literal["RESEARCH_DISPLAY_ONLY"] = field(default=ROLE, init=False)


@dataclass(frozen=True)
class ResearchDisplayResult:
    state: Literal["DEMO", "NOT_AVAILABLE"]
    data: ResearchDisplayData | None = field(repr=False)
    prepared: PreparedDailyReturns
    role: Literal["RESEARCH_DISPLAY_ONLY"] = field(default=ROLE, init=False)


def _mean(values):
    try:
        return math.fsum(v/len(values) for v in values)
    except OverflowError:
        # Rounding can overflow even max-float constant prices; normalize first.
        scale = max(abs(v) for v in values)
        return math.fsum(v/scale for v in values)/len(values)*scale if scale else 0.0


def _finite(function):
    try:
        value = function()
        return value if math.isfinite(value) else None
    except ArithmeticError:
        return None


def _item(name, values, reasons, visible=None):
    return ResearchIndicatorSeries(name, tuple(values), tuple(reasons), visible)


def _sma(prices, period):
    values, reasons = [], []
    for i in range(len(prices)):
        value = _finite(lambda: _mean(prices[i-period+1:i+1])) if i >= period-1 else None
        values.append(value)
        reasons.append(None if value is not None else "WARMUP" if i < period-1 else "CALCULATION_ERROR")
    return values, reasons


def _ema(prices, period):
    values, reasons, seed, previous = [], [], [], None
    alpha = 2/(period+1)
    for price in prices:
        if price is None:
            previous, seed = None, []
            value, reason = None, "WARMUP"
        elif previous is None:
            seed.append(price)
            value = _finite(lambda: _mean(seed)) if len(seed) == period else None
            reason = None if value is not None else "WARMUP" if len(seed) < period else "CALCULATION_ERROR"
            if len(seed) == period:
                seed = []
            previous = value
        else:
            value = _finite(lambda: previous+(price-previous)*alpha)
            reason = None if value is not None else "CALCULATION_ERROR"
            previous = value
        values.append(value)
        reasons.append(reason)
    return values, reasons


def _rsi(prices):
    values, reasons = [None], ["WARMUP"]
    gains, losses, avg_gain, avg_loss = [], [], None, None
    for previous, price in zip(prices, prices[1:]):
        change = price-previous
        gain, loss = max(change, 0), max(-change, 0)
        if avg_gain is None:
            gains.append(gain)
            losses.append(loss)
            if len(gains) < 14:
                values.append(None)
                reasons.append("WARMUP")
                continue
            avg_gain, avg_loss = _mean(gains), _mean(losses)
        else:
            avg_gain += (gain-avg_gain)/14
            avg_loss += (loss-avg_loss)/14
        scale = max(avg_gain, avg_loss)
        # Both zero is undefined; do not manufacture a neutral or zero reading.
        value = _finite(lambda: 100*(avg_gain/scale)/(avg_gain/scale+avg_loss/scale)) if scale else None
        values.append(value)
        reasons.append(None if value is not None else "ZERO_TOTAL_CHANGE" if scale == 0 else "CALCULATION_ERROR")
    return values, reasons


def _bollinger(prices):
    middle, reasons = _sma(prices, 20)
    upper, lower, band_reasons = [], [], []
    for i, mean in enumerate(middle):
        if mean is None:
            u, l, reason = None, None, reasons[i]
        else:
            sigma = _finite(lambda: math.sqrt(math.fsum((v-mean)**2/20 for v in prices[i-19:i+1])))
            u = _finite(lambda: mean+2*sigma) if sigma is not None else None
            l = _finite(lambda: mean-2*sigma) if sigma is not None else None
            reason = None if u is not None and l is not None else "CALCULATION_ERROR"
            if reason is not None:
                u, l = None, None
        upper.append(u)
        lower.append(l)
        band_reasons.append(reason)
    return middle, reasons, upper, lower, band_reasons


def _atr(bars, basis):
    if basis != "RAW_CLOSE":
        return [None]*len(bars), ["OHLC_BASIS_UNCONFIRMED"]*len(bars)
    values, reasons, seed, previous = [], [], [], None
    for i, bar in enumerate(bars):
        if bar.high is None or bar.low is None:
            value, reason, previous, seed = None, "OHLC_MISSING", None, []
        elif i == 0:
            value, reason = None, "WARMUP"
        else:
            tr = _finite(lambda: max(bar.high-bar.low, abs(bar.high-bars[i-1].close), abs(bar.low-bars[i-1].close)))
            if tr is None:
                value, reason, previous, seed = None, "CALCULATION_ERROR", None, []
            elif previous is None:
                seed.append(tr)
                value = _finite(lambda: _mean(seed)) if len(seed) == 14 else None
                reason = None if value is not None else "WARMUP" if len(seed) < 14 else "CALCULATION_ERROR"
                if len(seed) == 14:
                    seed = []
                previous = value
            else:
                value = _finite(lambda: previous+(tr-previous)/14)
                reason = None if value is not None else "CALCULATION_ERROR"
                previous = value
        values.append(value)
        reasons.append(reason)
    return values, reasons


def calculate_research_display(series: DailyInputSeries, as_of: datetime, *,
                               include_sma240: bool = False) -> ResearchDisplayResult:
    """Return aligned display arrays; None always means NOT_AVAILABLE, never zero.

    The #105 gate validates all eligible bars. Its last-20 returns remain gate
    metadata; display indicators use the full validated eligible price history.
    """
    prepared = prepare_daily_returns(series, as_of)
    if prepared.state != "READY":
        return ResearchDisplayResult("NOT_AVAILABLE", None, prepared)
    if type(include_sma240) is not bool:
        prepared = replace(prepared, state="NOT_AVAILABLE", returns=None, return_count=0,
                           reason_codes=("INVALID_DISPLAY_CONFIG",))
        return ResearchDisplayResult("NOT_AVAILABLE", None, prepared)
    cutoff = as_of.astimezone(timezone.utc)
    bars = tuple(b for b in series.bars if b.observed_at.astimezone(timezone.utc) <= cutoff)
    prices = tuple(b.adjclose if series.price_basis == "PROVIDER_ADJUSTED_CLOSE" else b.close for b in bars)
    items = []
    for period in (5, 20, 60, 120) + ((240,) if include_sma240 else ()):
        items.append(_item(f"SMA_{period}", *_sma(prices, period), period != 240))
    items.append(_item("EMA_20", *_ema(prices, 20)))
    items.append(_item("RSI_14", *_rsi(prices)))
    fast, fast_reasons = _ema(prices, 12)
    slow, slow_reasons = _ema(prices, 26)
    line, line_reasons = [], []
    for a, b, ar, br in zip(fast, slow, fast_reasons, slow_reasons):
        value = _finite(lambda: a-b) if a is not None and b is not None else None
        line.append(value)
        line_reasons.append(None if value is not None else "CALCULATION_ERROR" if "CALCULATION_ERROR" in (ar, br) or a is not None and b is not None else "WARMUP")
    signal, signal_reasons = _ema(line, 9)
    histogram, histogram_reasons = [], []
    for a, b, ar, br in zip(line, signal, line_reasons, signal_reasons):
        value = _finite(lambda: a-b) if a is not None and b is not None else None
        histogram.append(value)
        histogram_reasons.append(None if value is not None else "CALCULATION_ERROR" if "CALCULATION_ERROR" in (ar, br) or a is not None and b is not None else "WARMUP")
    items.extend((_item("MACD_12_26", line, line_reasons),
                  _item("MACD_SIGNAL_9", signal, signal_reasons),
                  _item("MACD_HISTOGRAM_12_26_9", histogram, histogram_reasons)))
    middle, middle_reasons, upper, lower, band_reasons = _bollinger(prices)
    items.extend((_item("BOLL_MIDDLE_20", middle, middle_reasons),
                  _item("BOLL_UPPER_20_2", upper, band_reasons),
                  _item("BOLL_LOWER_20_2", lower, band_reasons),
                  _item("ATR_14", *_atr(bars, series.price_basis))))
    data = ResearchDisplayData(tuple(b.session for b in bars), tuple(items), series.company_id,
                               series.listing_id, series.currency, series.price_basis)
    return ResearchDisplayResult("DEMO", data, prepared)
