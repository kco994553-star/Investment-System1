"""C3 explicit Pre-Tax metrics; no calibrated gates or Official promotion.

Returns are decimal, regular-period simple returns in one currency. Trading cost
is a fraction of opening equity (net = gross - cost). Frequency is supplied by
registration, never guessed from a sparse series. Undefined ratios return None.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import math
from statistics import mean, stdev

from .contracts import TAX_MODE
from .pit import PITGuard, PITObservation, PITViolation
from .splits import aware

METRIC_VERSION = 'EVL_METRICS_v1'


def _finite(value: float) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('metrics require finite numeric inputs')


def _growth(returns: tuple[float, ...]) -> float:
    if any(r == -1 for r in returns):
        return 0.0
    try:
        value = math.exp(math.fsum(math.log1p(r) for r in returns))
    except OverflowError as exc:
        raise ValueError('wealth growth overflow') from exc
    return value


def summarize(returns: tuple[float, ...], *, periods_per_year: float,
              excess: tuple[float, ...] | None = None) -> dict:
    """Ratios use arithmetic excess; drawdowns use compounded wealth from 1."""
    if not returns:
        raise ValueError('empty return series')
    _finite(periods_per_year)
    if periods_per_year <= 0:
        raise ValueError('annualization must be positive')
    for value in returns:
        _finite(value)
        if value < -1:
            raise ValueError('returns below -100% unsupported')
    excess = returns if excess is None else excess
    if len(excess) != len(returns):
        raise ValueError('excess return alignment mismatch')
    for value in excess:
        _finite(value)
    total = _growth(returns) - 1
    try:
        cagr = (1 + total) ** (periods_per_year / len(returns)) - 1
    except OverflowError as exc:
        raise ValueError('annualized growth overflow') from exc
    wealth, peak, drawdown, duration, max_duration = 1.0, 1.0, 0.0, 0, 0
    for value in returns:
        wealth *= 1 + value
        if wealth >= peak or math.isclose(wealth, peak, rel_tol=1e-12, abs_tol=0):
            peak, duration = max(wealth, peak), 0
        else:
            duration += 1
            max_duration = max(max_duration, duration)
            drawdown = max(drawdown, 1 - wealth / peak)
    volatility = stdev(excess) if len(excess) > 1 else None
    downside = math.sqrt(mean(min(value, 0) ** 2 for value in excess))
    ratios = {
        'sharpe': None if volatility in (None, 0) else mean(excess) / volatility * math.sqrt(periods_per_year),
        'sortino': None if downside == 0 else mean(excess) / downside * math.sqrt(periods_per_year),
        'calmar': None if drawdown == 0 else cagr / drawdown,
    }
    out = {
        'n': len(returns), 'total_return': total, 'cagr': cagr, 'mdd': drawdown,
        'annualized_volatility': None if volatility is None else volatility * math.sqrt(periods_per_year),
        **ratios, 'longest_drawdown_periods': max_duration,
        'unrecovered_drawdown': duration > 0,
        'undefined': tuple(name for name, value in ratios.items() if value is None),
    }
    for key in ('total_return', 'cagr', 'mdd', 'annualized_volatility', *ratios):
        if out[key] is not None:
            _finite(out[key])
    return out


@dataclass(frozen=True)
class ReturnPeriod:
    start: datetime
    end: datetime
    gross_return: float
    trading_cost: float
    risk_free_return: float
    inflation_return: float
    benchmark_return: float
    turnover: float
    currency: str
    risk_free_stamp: PITObservation
    outcome_stamp: PITObservation
    inflation_stamp: PITObservation

    def validate(self, evaluation_time: datetime) -> None:
        aware(self.start)
        aware(self.end)
        if self.start >= self.end or not self.currency:
            raise ValueError('invalid return period/currency')
        for value in (self.gross_return, self.trading_cost, self.risk_free_return,
                      self.inflation_return, self.benchmark_return, self.turnover):
            _finite(value)
        if self.trading_cost < 0 or self.turnover < 0:
            raise ValueError('cost/turnover cannot be negative')
        if min(self.gross_return, self.gross_return-self.trading_cost, self.benchmark_return) < -1:
            raise ValueError('insolvent returns below -100% unsupported')
        if min(self.risk_free_return, self.inflation_return) <= -1:
            raise ValueError('invalid deflator')
        for stamp in (self.risk_free_stamp, self.outcome_stamp, self.inflation_stamp):
            aware(stamp.available_at)
            if not stamp.observation_id:
                raise PITViolation('missing metric provenance identity')
        PITGuard.enforce(self.start, (self.risk_free_stamp,))
        PITGuard.enforce(evaluation_time, (self.outcome_stamp, self.inflation_stamp))
        if self.end > evaluation_time or self.outcome_stamp.available_at < self.end:
            raise PITViolation('outcome not yet realized/published')


def evaluate_metrics(periods: tuple[ReturnPeriod, ...], *, evaluation_time: datetime,
                     periods_per_year: float, tail_fraction: float) -> dict:
    """Real inflation is ex-post attribution only, never a predictor.

    Risk-free rates must be known at period start. Outcome and realized inflation
    must be published by evaluation_time. All vintage references are returned.
    """
    aware(evaluation_time)
    if not periods:
        raise ValueError('empty performance history')
    _finite(tail_fraction)
    if not 0 < tail_fraction <= 1:
        raise ValueError('tail fraction must be in (0,1]')
    for i, period in enumerate(periods):
        period.validate(evaluation_time)
        if period.currency != periods[0].currency:
            raise ValueError('mixed currency requires an upstream FX contract')
        if i and period.start != periods[i-1].end:
            raise ValueError('periods must be chronological, contiguous and non-overlapping')
    gross = tuple(p.gross_return for p in periods)
    net = tuple(p.gross_return-p.trading_cost for p in periods)
    rf = tuple(p.risk_free_return for p in periods)
    real = tuple((1+n)/(1+p.inflation_return)-1 for n, p in zip(net, periods))
    relative_rf = tuple((1+n)/(1+r)-1 for n, r in zip(net, rf))
    benchmark = tuple(p.benchmark_return for p in periods)
    arithmetic_excess = tuple(n-r for n, r in zip(net, rf))
    views = {
        'GROSS_PRE_TAX': summarize(gross, periods_per_year=periods_per_year,
                                  excess=tuple(g-r for g, r in zip(gross, rf))),
        'NET_OF_TRADING_COST_PRE_TAX': summarize(net, periods_per_year=periods_per_year, excess=arithmetic_excess),
        'REAL_PRE_TAX': summarize(real, periods_per_year=periods_per_year),
        'RISK_FREE_EXCESS_PRE_TAX': summarize(relative_rf, periods_per_year=periods_per_year),
    }
    down = tuple((n, b) for n, b in zip(net, benchmark) if b < 0)
    down_capture = None
    if down:
        strategy_down = summarize(tuple(n for n, _ in down), periods_per_year=periods_per_year)['cagr']
        benchmark_down = summarize(tuple(b for _, b in down), periods_per_year=periods_per_year)['cagr']
        if benchmark_down != 0:
            down_capture = strategy_down / benchmark_down
    tail_count = max(1, math.ceil(len(net)*tail_fraction))
    return {
        'metric_version': METRIC_VERSION, 'tax_mode': TAX_MODE,
        'currency': periods[0].currency, 'periods_per_year': periods_per_year,
        'evaluation_time': evaluation_time.isoformat(), 'views': views,
        'benchmark': summarize(benchmark, periods_per_year=periods_per_year),
        'risk_free': summarize(rf, periods_per_year=periods_per_year),
        'net_minus_benchmark_total_return': _growth(net)-_growth(benchmark),
        'downside_capture': down_capture, 'tail_fraction': tail_fraction,
        'tail_count': tail_count, 'tail_mean_return': mean(sorted(net)[:tail_count]),
        'turnover_sum': sum(p.turnover for p in periods),
        'mean_period_turnover': mean(p.turnover for p in periods),
        'provenance': [
            {name: {**asdict(getattr(p, name)), 'available_at': getattr(p, name).available_at.isoformat()}
             for name in ('risk_free_stamp', 'outcome_stamp', 'inflation_stamp')}
            for p in periods],
        'official': False,
    }
