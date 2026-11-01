"""Benchmarks for EXP-STOCK-INDICATOR-DECILES-v1.

Ported from research/qgv_backtest @ 56a0e8ce (#417/#430) and changed for EXP-STOCK-INDICATOR-DECILES-v1: the external
total-return consumer follows runner._references / _semantic_audit (caller-supplied daily TR index, entry at the T open,
optional one-sided entry cost, USD only). The group equal-weight benchmark is new.

(a) Group equal weight: the same ledger (exp_deciles.ledger.run_ledger) with selected = every eligible name of the
    group on each rebalance, the same S/T schedule, the same costs, both termination scenarios.
(b) External total-return series: a caller-supplied daily series with a label. Owner 11/01 decision 3 (settings.BENCHMARKS
    = SPY_TOTAL_RETURN_ETF_AUXILIARY): SPY total return is an ETF auxiliary comparison only and no S&P 500 index total
    return is ever claimed (review R2 / SYN-1). So:
    - claim SPY_TOTAL_RETURN_ETF_AUXILIARY (the experiment's external slot) accepts only an ETF series whose ticker is SPY
      (TR_SERIES_NOT_SPY_ETF otherwise; a French / Fama-French series FRENCH_MARKET_NOT_SPY_ETF); it is named
      'SPY total return (ETF auxiliary comparison)', never S&P 500, and is no substitute for any index slot;
    - claim OTHER_TR names any other series by its label (an ETF by its known ticker only, else 'ETF total return
      (ticker not identified)'; a label base is never turned into an ETF name);
    - claim SP500_TR, and any series labelled as the S&P 500 total-return index (SP500TR, SPXT, 'S&P 500 Total
      Return', ...), is refused with SP500_INDEX_TR_NOT_USED whatever its claim or source.
    French markers and ETF markers (an S&P 500 ETF ticker, the word ETF, or a fund-family / fund word such as SPDR,
    iShares, Vanguard, Trust, Fund, NAV) are looked for in the label AND the source text (review F8).
    Previous-close fallbacks (review M3): an entry at PREVIOUS_CLOSE and an end-day open replaced by a close use only the
    immediately preceding session's close (the session calendar, else the rule calendar); otherwise the level is missing
    (MISSING_PREVIOUS_CLOSE_LEVEL blocks the series, MISSING_END_LEVEL leaves the end null). With PREVIOUS_CLOSE entry the
    start anchor for annualization is that close's date (entry_level_date, review R7).

Pure functions: no data provider, file or network access.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_DOWN, localcontext
import re
from typing import Mapping, Sequence

from . import schedule
from .ledger import (
    DEFAULT_COST_BPS, DEFAULT_INITIAL_CAPITAL, SCENARIOS, VALUATION_CLOSE, VALUATION_OPEN, VALUATIONS, Rebalance,
    run_ledger,
)


class BenchmarkError(ValueError):
    """Refused benchmark input. The message is an UPPER_SNAKE reason code."""


GROUP_EQUAL_WEIGHT = 'GROUP_EQUAL_WEIGHT'
CLAIM_SP500_TR = 'SP500_TR'                     # refused: no S&P 500 index total return is claimed (owner 11/01)
CLAIM_SPY_ETF_AUXILIARY = 'SPY_TOTAL_RETURN_ETF_AUXILIARY'   # the experiment's external slot (settings.BENCHMARKS)
CLAIM_OTHER_TR = 'OTHER_TR'
CLAIMS = (CLAIM_SPY_ETF_AUXILIARY, CLAIM_OTHER_TR)
SP500_INDEX_TR_NOT_USED = 'SP500_INDEX_TR_NOT_USED'
SPY_TICKER = 'SPY'
ENTRY_OPEN = 'OPEN'
ENTRY_PREVIOUS_CLOSE = 'PREVIOUS_CLOSE'

# Tickers of exchange-traded funds that track the S&P 500. They are never the index itself.
ETF_TICKERS = frozenset({'SPY', 'IVV', 'VOO', 'SPLG', 'RSP'})
# Normalized labels (upper-case letters and digits only) accepted as the S&P 500 total-return index.
SP500_TR_INDEX_LABELS = frozenset({'SP500TR', 'SP500TRINDEX', 'SP500TOTALRETURN', 'SP500TOTALRETURNINDEX',
                                   'SPXT', 'SPXTR'})
FRENCH_MARKERS = ('FRENCH', 'FAMA', 'MKTRF')
# Fund-family and fund words: a description carrying one describes a fund, never the index (review R2).
FUND_MARKERS = frozenset({'SPDR', 'ISHARES', 'VANGUARD', 'INVESCO', 'SCHWAB', 'TRUST', 'FUND', 'NAV'})
_TR_SUFFIXES = ('TOTALRETURNINDEX', 'TOTALRETURN', 'TRINDEX', 'TR')


def _norm(text: str) -> str:
    return re.sub(r'[^A-Z0-9]', '', text.upper())


def _tokens(text: str | None) -> list[str]:
    return re.findall(r'[A-Z0-9]+', (text or '').upper())


def _etf_marked(tokens) -> bool:
    return any(token in ('ETF', 'ETFS') or token in ETF_TICKERS or token in FUND_MARKERS for token in tokens)


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
                                 end_valuation: str = VALUATION_CLOSE, daily_positions: bool = True) -> dict:
    """Run the experiment ledger on all eligible names of one group (U-A or U-B), per scenario (same end and end
    valuation as the strategies)."""
    if not isinstance(group, str) or not group.strip():
        raise BenchmarkError('INVALID_GROUP_LABEL')
    rebalances = group_equal_weight_rebalances(schedule, eligible_by_signal)
    prices, events = tuple(prices), tuple(events)
    runs = {scenario: run_ledger(sessions, rebalances, prices, events, scenario=scenario, cost_bps=cost_bps,
                                 initial_capital=initial_capital, end=end, end_valuation=end_valuation,
                                 daily_positions=daily_positions)
            for scenario in scenarios}
    return dict(benchmark_id=GROUP_EQUAL_WEIGHT, group=group, name=f'{group} eligible names, equal weight',
                is_etf=False, is_sp500_index=False, cost_bps=Decimal(str(cost_bps)),
                eligible_counts={row.signal_date: len(row.selected) for row in rebalances},
                rebalances=rebalances, runs=runs)


# -- (b) external total-return index ----------------------------------------------------------------------------
def classify_tr_label(label: str, *, is_etf: bool | None = None, source: str | None = None) -> dict:
    """Identify an external series from its label and source: ETF (with its known ticker or None), French market
    factor, or a label of the S&P 500 TR index (sp500_index_label: always refused by external_tr_benchmark)."""
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
    etf_label = base in ETF_TICKERS or 'ETF' in norm or _etf_marked(_tokens(label))
    etf_source = _etf_marked(_tokens(source))
    if is_etf is False and etf_label:
        raise BenchmarkError('ETF_LABEL_DECLARED_NOT_ETF')
    if is_etf is False and etf_source:
        raise BenchmarkError('ETF_SOURCE_DECLARED_NOT_ETF')
    etf = bool(is_etf) or etf_label or etf_source
    tickers = [t for t in _tokens(label) + _tokens(source) if t in ETF_TICKERS]
    ticker = base if base in ETF_TICKERS else (tickers[0] if tickers else None)
    return dict(label=label, normalized=norm, ticker=ticker if etf else None, is_etf=etf, is_french_market=french,
                etf_named_in_source=etf_source and not etf_label,
                sp500_index_label=norm in SP500_TR_INDEX_LABELS, is_sp500_index=False)


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


def _previous_session(day, days):
    """The session immediately before `day`: from the supplied session calendar, else the rule calendar."""
    if days:
        earlier = [d for d in days if d < day]
        return earlier[-1] if earlier else None
    try:
        return schedule.previous_session(day)
    except Exception:  # noqa: BLE001 - outside the rule calendar: no previous session is known
        return None


def external_tr_benchmark(index_rows, *, label: str, claim: str, entry_date: date, end: date | None = None,
                          sessions: Sequence[date] | None = None, entry_basis: str = ENTRY_OPEN,
                          is_etf: bool | None = None, source: str | None = None,
                          initial_capital=DEFAULT_INITIAL_CAPITAL, entry_cost_bps=0,
                          end_valuation: str = VALUATION_CLOSE, cycle_dates: Sequence[date] = ()) -> dict:
    """Value a caller-supplied daily total-return series from entry_date (normally the first T) to end.

    index_rows: mappings {date, total_return_index, open_total_return_index?, currency='USD'}.
    claim: SPY_TOTAL_RETURN_ETF_AUXILIARY (the experiment's external slot: SPY ETF only) or OTHER_TR; SP500_TR and any
    S&P 500 index label are refused (SP500_INDEX_TR_NOT_USED; module doc).
    entry_basis: OPEN uses the entry date's open level; PREVIOUS_CLOSE uses the close of the session immediately before
    the entry date (entry_level_date) and is flagged ENTRY_AT_PREVIOUS_CLOSE. NAV = capital x level / entry level /
    (1 + entry cost). A missing daily level is None with MISSING_INDEX_LEVEL, never carried or filled.
    end_valuation OPEN (the strategies' terminal valuation at the next T open, review F4): the end day uses its open
    level; without one the immediately preceding session's close, flagged END_AT_PREVIOUS_CLOSE (valuation
    PREVIOUS_CLOSE); without that either the end level is missing (MISSING_END_LEVEL; review M3).
    cycle_dates: later reselection T dates; cycle_boundaries lists the NAV at each of their opens (open level, else the
    immediately preceding close, else None) between the start anchor and the terminal open (review R5).
    """
    if claim == CLAIM_SP500_TR:
        raise BenchmarkError(SP500_INDEX_TR_NOT_USED)
    if claim not in CLAIMS:
        raise BenchmarkError('UNKNOWN_BENCHMARK_CLAIM')
    if entry_basis not in (ENTRY_OPEN, ENTRY_PREVIOUS_CLOSE):
        raise BenchmarkError('UNKNOWN_ENTRY_BASIS')
    if end_valuation not in VALUATIONS:
        raise BenchmarkError('UNKNOWN_END_VALUATION')
    if type(entry_date) is not date or (end is not None and type(end) is not date):
        raise BenchmarkError('ENTRY_AND_END_MUST_BE_DATES')
    info = classify_tr_label(label, is_etf=is_etf, source=source)
    if info['sp500_index_label']:
        raise BenchmarkError(SP500_INDEX_TR_NOT_USED)
    flags = []
    if claim == CLAIM_SPY_ETF_AUXILIARY:
        if info['is_french_market']:
            raise BenchmarkError('FRENCH_MARKET_NOT_SPY_ETF')
        if not info['is_etf'] or info['ticker'] != SPY_TICKER:
            raise BenchmarkError('TR_SERIES_NOT_SPY_ETF')
        benchmark_id, name = CLAIM_SPY_ETF_AUXILIARY, 'SPY total return (ETF auxiliary comparison)'
        role = 'ETF_AUXILIARY_COMPARISON'
    elif info['is_etf']:
        ticker = info['ticker']
        benchmark_id = f'ETF_TR:{ticker or "UNIDENTIFIED"}'
        name = f'{ticker} total return (ETF)' if ticker else 'ETF total return (ticker not identified)'
        role = 'OTHER_SERIES'
    elif info['is_french_market']:
        benchmark_id, name = f'OTHER_TR:{info["normalized"]}', f'{label.strip()} (French market series, not S&P 500)'
        role = 'OTHER_SERIES'
    else:
        benchmark_id, name = f'OTHER_TR:{info["normalized"]}', f'{label.strip()} total return'
        role = 'OTHER_SERIES'
    if info['is_etf'] and info['etf_named_in_source']:
        flags.append('ETF_NAMED_IN_SOURCE')
    capital = _level(initial_capital, 'INITIAL_CAPITAL')
    cost = Decimal(str(entry_cost_bps))
    if not cost.is_finite() or cost < 0 or cost >= 10000:
        raise BenchmarkError('INVALID_ENTRY_COST_BPS')
    index = _index_rows(index_rows)
    days = sorted(sessions) if sessions is not None else sorted(index)
    result = dict(benchmark_id=benchmark_id, label=label, name=name, claim=claim, role=role, is_etf=info['is_etf'],
                  ticker=info['ticker'], is_sp500_index=False, is_french_market=info['is_french_market'],
                  currency='USD', source=source, entry_date=entry_date, entry_basis=entry_basis,
                  entry_cost_bps=cost, initial_capital=capital, end_valuation=end_valuation, flags=flags)
    if entry_basis == ENTRY_OPEN:
        entry, entry_level_date = index.get(entry_date, (None, None))[1], entry_date
        missing = 'MISSING_ENTRY_OPEN_LEVEL'
    else:
        entry_level_date = _previous_session(entry_date, days if sessions is not None else None)
        entry = index.get(entry_level_date, (None, None))[0] if entry_level_date is not None else None
        missing = 'MISSING_PREVIOUS_CLOSE_LEVEL'
        flags.append('ENTRY_AT_PREVIOUS_CLOSE')
    result['entry_level_date'] = entry_level_date
    if entry is None:
        result.update(status='BLOCKED', reasons=(missing,), entry_level=None, daily=[], cycle_boundaries=[])
        return result
    last = end if end is not None else (days[-1] if days else entry_date)
    calendar = days if sessions is not None else None
    daily, reasons = [], set()
    with localcontext() as context:
        context.prec = 50
        context.rounding = ROUND_DOWN
        scale = capital / entry / (1 + cost / Decimal(10000))

        def open_or_previous_close(day):
            level = index.get(day, (None, None))[1]
            if level is not None:
                return level, VALUATION_OPEN
            previous = _previous_session(day, calendar)
            close = index.get(previous, (None, None))[0] if previous is not None else None
            return (close, ENTRY_PREVIOUS_CLOSE) if close is not None else (None, None)

        for day in days:
            if not entry_date <= day <= last:
                continue
            level, valuation, reason = index.get(day, (None, None))[0], VALUATION_CLOSE, 'MISSING_INDEX_LEVEL'
            if end_valuation == VALUATION_OPEN and day == last:
                level, valuation = open_or_previous_close(day)
                if valuation == ENTRY_PREVIOUS_CLOSE:
                    flags.append('END_AT_PREVIOUS_CLOSE')
                elif valuation is None:
                    valuation, reason = VALUATION_OPEN, 'MISSING_END_LEVEL'
            if level is None:
                reasons.add(reason)
            daily.append(dict(date=day, valuation=valuation, level=level, nav=None if level is None else scale * level,
                              reason=None if level is not None else reason))
        boundaries = [dict(date=entry_level_date, nav=capital, valuation='START')]
        for day in sorted(set(cycle_dates)):
            if entry_date < day < last or (day == last and end_valuation != VALUATION_OPEN):
                level, valuation = open_or_previous_close(day)
                boundaries.append(dict(date=day, nav=None if level is None else scale * level, valuation=valuation))
        if end_valuation == VALUATION_OPEN and daily and daily[-1]['date'] == last:
            boundaries.append(dict(date=last, nav=daily[-1]['nav'], valuation=daily[-1]['valuation']))
    result.update(status='INCOMPLETE' if reasons else 'COMPLETE', reasons=tuple(sorted(reasons)), entry_level=entry,
                  daily=daily, cycle_boundaries=boundaries)
    return result


def tr_nav_points(result: Mapping):
    """(NavPoint list, started_at, initial capital) for exp_deciles.metrics.series_metrics. started_at is the date of
    the entry level: the entry date for an OPEN entry, the previous session's close for PREVIOUS_CLOSE (review R7)."""
    from .metrics import NavPoint
    points = [NavPoint(row['date'], None if row['nav'] is None else float(row['nav'])) for row in result['daily']]
    return points, result.get('entry_level_date') or result['entry_date'], float(result['initial_capital'])


def tr_cycle_boundaries(result: Mapping):
    """[(date, nav float | None)] of result['cycle_boundaries'] for metrics.series_metrics (review R5)."""
    return [(row['date'], None if row['nav'] is None else float(row['nav'])) for row in result.get('cycle_boundaries')
            or ()]
