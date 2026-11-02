"""Private arithmetic diagnostics over shared Alpaca normalization; no collection, rankings or book-rule claims."""
from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from .adapters.alpaca_bars import session_date
from . import schedule


def _number(value, *, positive=False):
    if isinstance(value, (bool, float)) or value is None:
        return None
    try:
        n = Decimal(value)
    except (ValueError, TypeError, InvalidOperation):
        return None
    return n if n.is_finite() and (n > 0 if positive else n >= 0) else None


def summarize(rows, *, signal_day, symbol):
    """Six calendar months (S-6m,S], observed-day and complete-window means separately.

    VWAP*volume uses provider-rounded aggregates, not an exact sum of every market trade.
    close*volume is a separately named proxy. The normalized row's unknown identity/currency is not upgraded.
    A missing/invalid day is not zero. Only an explicitly observed zero volume produces zero value.
    Never join historical/current symbols here. Caller groups by original request identity/asof and stores hashes.
    """
    end = date.fromisoformat(signal_day)
    year, month = divmod(end.year * 12 + end.month - 1 - 6, 12)
    start = date(year, month + 1, min(end.day, monthrange(year, month + 1)[1]))
    sessions = []
    day = start + timedelta(days=1)
    while day <= end:
        if schedule.is_session(day):
            sessions.append(day.isoformat())
        day += timedelta(days=1)
    by_day, duplicates = {}, 0
    for row in rows:
        day = date.fromisoformat(row['date'])
        if not start < day <= end:
            continue
        if row.get('returned_symbol') != symbol:
            raise ValueError('SYMBOL_MISMATCH')
        if row.get('price_basis') != 'RAW':
            raise ValueError('RAW_BASIS_REQUIRED')
        actual, problem = session_date(row.get('source_timestamp'))
        if problem or actual != day:
            raise ValueError(problem or 'SESSION_DATE_MISMATCH')
        key = day.isoformat()
        # Preserve every raw source, but do not count identical overlapping responses twice.
        values = {k: row.get(k) for k in ('volume', 'vwap', 'close')}
        digest = row.get('source_sha256')
        if not isinstance(digest, str) or len(digest) != 64:
            raise ValueError('SOURCE_HASH_REQUIRED')
        if key in by_day:
            if by_day[key]['values'] != values:
                raise ValueError('CONFLICTING_DAY')
            duplicates += 1
            by_day[key]['source_hashes'].add(digest)
        else:
            by_day[key] = dict(values=values, source_hashes={digest})
    daily = []
    for key in sessions:
        source = by_day.get(key)
        values = source['values'] if source else {}
        volume = _number(values.get('volume'))
        vwap, close = (_number(values.get(k), positive=True) for k in ('vwap', 'close'))
        daily.append(dict(date=key, observed=source is not None,
                          vwap_volume=None if volume is None or vwap is None else str(volume * vwap),
                          close_volume_proxy=None if volume is None or close is None else str(volume * close),
                          source_hashes=sorted(source['source_hashes']) if source else []))
    def mean(field):
        available = [Decimal(r[field]) for r in daily if r[field] is not None]
        value = str(sum(available) / len(available)) if available else None
        return dict(valid_days=len(available), mean_observed=value,
                    mean_complete=value if len(available) == len(sessions) and sessions else None,
                    invalid_dates=[r['date'] for r in daily if r['observed'] and r[field] is None],
                    reason=None if len(available) == len(sessions) and sessions else 'INCOMPLETE_WINDOW')
    return dict(schema='exp-liquidity-diagnostic/1', symbol=symbol, security_id=None,
                identity_status='UNVERIFIED', currency=None, currency_status='NOT_VERIFIED',
                numeric_unit='QUOTE_CURRENCY_PER_DAY; USD only after currency confirmation',
                signal_day=signal_day, window_start_exclusive=start.isoformat(), window_end_inclusive=signal_day,
                expected_sessions=len(sessions), observed_sessions=len(by_day), duplicates_removed=duplicates,
                missing_dates=[r['date'] for r in daily if not r['observed']],
                vwap_volume=mean('vwap_volume'), close_volume_proxy=mean('close_volume_proxy'), daily=daily,
                source_hashes=sorted({s for r in daily for s in r['source_hashes']}),
                market_percentile=None, price_volatility_6m=None,
                reasons=['BOOK_EXACT_UNCONFIRMED', 'FULL_POPULATION_NOT_SUPPLIED',
                         'VWAP_VOLUME_PROVIDER_AGGREGATE_APPROXIMATION', 'VOLATILITY_FORMULA_AND_ACTION_BASIS_UNCONFIRMED'])
