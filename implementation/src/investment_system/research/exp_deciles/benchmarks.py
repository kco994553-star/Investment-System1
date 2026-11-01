"""Benchmarks for EXP-STOCK-INDICATOR-DECILES-v1.

Ported from research/qgv_backtest @ 56a0e8ce (#417/#430) and changed for EXP-STOCK-INDICATOR-DECILES-v1: the external
total-return consumer follows runner._references / _semantic_audit (caller-supplied daily TR index, entry at the T open,
optional one-sided entry cost, USD only). The group equal-weight benchmark is new.

(a) Group equal weight: the same ledger (exp_deciles.ledger.run_ledger) with selected = every eligible name of the
    group on each rebalance, the same S/T schedule, the same costs, both termination scenarios.
(b) External total-return index: a caller-supplied daily series with a label. An ETF (for example SPY) is marked
    is_etf=True and its name never says S&P 500. A French / Fama-French market series is refused as an S&P 500 series.

Pure functions: no data provider, file or network access.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_DOWN, localcontext
import re
from typing import Mapping, Sequence

from .ledger import (
    DEFAULT_COST_BPS, DEFAULT_INITIAL_CAPITAL, SCENARIOS, Rebalance, run_ledger,
)


class BenchmarkError(ValueError):
    """Refused benchmark input. The message is an UPPER_SNAKE reason code."""


GROUP_EQUAL_WEIGHT = 'GROUP_EQUAL_WEIGHT'
CLAIM_SP500_TR = 'SP500_TR'
CLAIM_OTHER_TR = 'OTHER_TR'
CLAIMS = (CLAIM_SP500_TR, CLAIM_OTHER_TR)
ENTRY_OPEN = 'OPEN'
ENTRY_PREVIOUS_CLOSE = 'PREVIOUS_CLOSE'

# Tickers of exchange-traded funds that track the S&P 500. They are never the index itself.
ETF_TICKERS = frozenset({'SPY', 'IVV', 'VOO', 'SPLG', 'RSP'})
# Normalized labels (upper-case letters and digits only) accepted as the S&P 500 total-return index.
SP500_TR_INDEX_LABELS = frozenset({'SP500TR', 'SP500TRINDEX', 'SP500TOTALRETURN', 'SP500TOTALRETURNINDEX',
                                   'SPXT', 'SPXTR'})
FRENCH_MARKERS = ('FRENCH', 'FAMA', 'MKTRF')
_TR_SUFFIXES = ('TOTALRETURNINDEX', 'TOTALRETURN', 'TRINDEX', 'TR')


def _norm(text: str) -> str:
    return re.sub(r'[^A-Z0-9]', '', text.upper())


# -- (a) group equal weight -------------------------------------------------------------------------------------
def group_equal_weight_rebalances(schedule: Sequence, eligible_by_signal: Mapping[date, Sequence[str]]
                                  ) -> tuple[Rebalance, ...]:
    """Same S/T schedule, selected = every eligible name of the group (sorted by security ID)."""
    rows = []
    for item in schedule:
        signal, execution = ((item.signal_date, item.execution_date) if isinstance(item, Rebalance)
                             else tuple(item))
        if signal not in eligible_by_signal:
            raise BenchmarkError('MISSING_ELIGIBLE_SET')
        eligible = eligible_by_signal[signal]
        if isinstance(eligible, str):
            raise BenchmarkError('ELIGIBLE_SET_MUST_BE_A_SEQUENCE')
        rows.append(Rebalance(signal, execution, tuple(sorted(set(eligible)))))
    if not rows:
        raise BenchmarkError('EMPTY_SCHEDULE')
    return tuple(rows)


def group_equal_weight_benchmark(sessions: Sequence[date], schedule: Sequence,
                                 eligible_by_signal: Mapping[date, Sequence[str]], prices, events=(), *,
                                 group: str, cost_bps=DEFAULT_COST_BPS, initial_capital=DEFAULT_INITIAL_CAPITAL,
                                 scenarios: Sequence[str] = SCENARIOS, end: date | None = None,
                                 daily_positions: bool = True) -> dict:
    """Run the experiment ledger on all eligible names of one group (U-A or U-B), per scenario."""
    if not isinstance(group, str) or not group.strip():
        raise BenchmarkError('INVALID_GROUP_LABEL')
    rebalances = group_equal_weight_rebalances(schedule, eligible_by_signal)
    prices, events = tuple(prices), tuple(events)
    runs = {scenario: run_ledger(sessions, rebalances, prices, events, scenario=scenario, cost_bps=cost_bps,
                                 initial_capital=initial_capital, end=end, daily_positions=daily_positions)
            for scenario in scenarios}
    return dict(benchmark_id=GROUP_EQUAL_WEIGHT, group=group, name=f'{group} eligible names, equal weight',
                is_etf=False, is_sp500_index=False, cost_bps=Decimal(str(cost_bps)),
                eligible_counts={row.signal_date: len(row.selected) for row in rebalances},
                rebalances=rebalances, runs=runs)


# -- (b) external total-return index ----------------------------------------------------------------------------
def classify_tr_label(label: str, *, is_etf: bool | None = None, source: str | None = None) -> dict:
    """Identify an external series from its label: ETF, French market factor, or the S&P 500 TR index."""
    if not isinstance(label, str) or not label.strip():
        raise BenchmarkError('INVALID_BENCHMARK_LABEL')
    if is_etf is not None and type(is_etf) is not bool:
        raise BenchmarkError('INVALID_IS_ETF_FLAG')
    norm = _norm(label)
    base = norm
    for suffix in _TR_SUFFIXES:
        if norm.endswith(suffix) and len(norm) > len(suffix):
            base = norm[:-len(suffix)]
            break
    french = any(marker in _norm(f'{label} {source or ""}') for marker in FRENCH_MARKERS)
    etf_label = base in ETF_TICKERS or 'ETF' in norm
    if is_etf is False and etf_label:
        raise BenchmarkError('ETF_LABEL_DECLARED_NOT_ETF')
    etf = bool(is_etf) or etf_label
    return dict(label=label, normalized=norm, ticker=base, is_etf=etf, is_french_market=french,
                is_sp500_index=(not etf and not french and norm in SP500_TR_INDEX_LABELS))


def _level(value, name):
    if isinstance(value, bool):
        raise BenchmarkError(f'INVALID_{name}')
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise BenchmarkError(f'INVALID_{name}') from exc
    if not result.is_finite() or result <= 0:
        raise BenchmarkError(f'INVALID_{name}')
    return result


def _index_rows(rows):
    index = {}
    for row in rows:
        day = row.get('date')
        if type(day) is not date:
            raise BenchmarkError('INDEX_DATE_MUST_BE_DATE')
        if day in index:
            raise BenchmarkError('DUPLICATE_INDEX_DATE')
        if row.get('currency') != 'USD':
            raise BenchmarkError('BENCHMARK_CURRENCY_NOT_USD')
        close = row.get('total_return_index')
        opening = row.get('open_total_return_index')
        index[day] = (None if close is None else _level(close, 'TOTAL_RETURN_INDEX'),
                      None if opening is None else _level(opening, 'OPEN_TOTAL_RETURN_INDEX'))
    return index


def external_tr_benchmark(index_rows, *, label: str, claim: str, entry_date: date, end: date | None = None,
                          sessions: Sequence[date] | None = None, entry_basis: str = ENTRY_OPEN,
                          is_etf: bool | None = None, source: str | None = None,
                          initial_capital=DEFAULT_INITIAL_CAPITAL, entry_cost_bps=0) -> dict:
    """Value a caller-supplied daily total-return index from entry_date (normally the first T) to end.

    index_rows: mappings {date, total_return_index, open_total_return_index?, currency='USD'}.
    claim: SP500_TR (the experiment's S&P 500 total-return slot) or OTHER_TR.
    entry_basis: OPEN uses the entry date's open level; PREVIOUS_CLOSE uses the last close level before the entry
    date and is flagged ENTRY_AT_PREVIOUS_CLOSE. NAV = capital x level / entry level / (1 + entry cost).
    A missing daily level is None with MISSING_INDEX_LEVEL, never carried or filled.
    """
    if claim not in CLAIMS:
        raise BenchmarkError('UNKNOWN_BENCHMARK_CLAIM')
    if entry_basis not in (ENTRY_OPEN, ENTRY_PREVIOUS_CLOSE):
        raise BenchmarkError('UNKNOWN_ENTRY_BASIS')
    if type(entry_date) is not date or (end is not None and type(end) is not date):
        raise BenchmarkError('ENTRY_AND_END_MUST_BE_DATES')
    info = classify_tr_label(label, is_etf=is_etf, source=source)
    flags = []
    if claim == CLAIM_SP500_TR and info['is_french_market']:
        raise BenchmarkError('FRENCH_MARKET_NOT_SP500')
    if info['is_etf']:
        benchmark_id, name = f'ETF_TR:{info["ticker"]}', f'{info["ticker"]} total return (ETF)'
        if claim == CLAIM_SP500_TR:
            flags.append('ETF_SUBSTITUTE_NOT_INDEX')
    elif claim == CLAIM_SP500_TR:
        if not info['is_sp500_index']:
            raise BenchmarkError('LABEL_NOT_SP500_TR_INDEX')
        benchmark_id, name = 'SP500_TR_INDEX', 'S&P 500 total return index'
    elif info['is_french_market']:
        benchmark_id, name = f'OTHER_TR:{info["normalized"]}', f'{label.strip()} (French market series, not S&P 500)'
    else:
        benchmark_id, name = f'OTHER_TR:{info["normalized"]}', f'{label.strip()} total return'
    capital = _level(initial_capital, 'INITIAL_CAPITAL')
    cost = Decimal(str(entry_cost_bps))
    if not cost.is_finite() or cost < 0 or cost >= 10000:
        raise BenchmarkError('INVALID_ENTRY_COST_BPS')
    index = _index_rows(index_rows)
    result = dict(benchmark_id=benchmark_id, label=label, name=name, claim=claim, is_etf=info['is_etf'],
                  is_sp500_index=info['is_sp500_index'], is_french_market=info['is_french_market'],
                  substitute_for=CLAIM_SP500_TR if claim == CLAIM_SP500_TR and info['is_etf'] else None,
                  currency='USD', source=source, entry_date=entry_date, entry_basis=entry_basis,
                  entry_cost_bps=cost, initial_capital=capital, flags=flags)
    if entry_basis == ENTRY_OPEN:
        entry = index.get(entry_date, (None, None))[1]
        missing = 'MISSING_ENTRY_OPEN_LEVEL'
    else:
        earlier = [day for day, (close, _) in index.items() if day < entry_date and close is not None]
        entry = index[max(earlier)][0] if earlier else None
        missing = 'MISSING_PREVIOUS_CLOSE_LEVEL'
        flags.append('ENTRY_AT_PREVIOUS_CLOSE')
    if entry is None:
        result.update(status='BLOCKED', reasons=(missing,), entry_level=None, daily=[])
        return result
    days = sorted(sessions) if sessions is not None else sorted(index)
    last = end if end is not None else (days[-1] if days else entry_date)
    daily, reasons = [], set()
    with localcontext() as context:
        context.prec = 50
        context.rounding = ROUND_DOWN
        scale = capital / entry / (1 + cost / Decimal(10000))
        for day in days:
            if not entry_date <= day <= last:
                continue
            level = index.get(day, (None, None))[0]
            if level is None:
                reasons.add('MISSING_INDEX_LEVEL')
            daily.append(dict(date=day, level=level, nav=None if level is None else scale * level,
                              reason=None if level is not None else 'MISSING_INDEX_LEVEL'))
    result.update(status='INCOMPLETE' if reasons else 'COMPLETE', reasons=tuple(sorted(reasons)), entry_level=entry,
                  daily=daily)
    return result


def tr_nav_points(result: Mapping):
    """(NavPoint list, started_at, initial capital) for exp_deciles.metrics.series_metrics."""
    from .metrics import NavPoint
    points = [NavPoint(row['date'], None if row['nav'] is None else float(row['nav'])) for row in result['daily']]
    return points, result['entry_date'], float(result['initial_capital'])
