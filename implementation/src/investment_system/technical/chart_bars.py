"""Chart bar model (TECHNICAL_PATTERN_CHART_V1_DESIGN §7, P1-1 and the client half of P1-W).

Python reference for web_assets/chart-bars.js (vectors: tests/fixtures/chart_bars_reference_v1.json).
Pure functions on RAM values. No network, no storage, no price repair:
- Input is a `private-history/1` response already checked by PrivateHistory.validateHistory.
- Missing values stay None with a reason code. Nothing is filled with 0 or interpolated.
- A reported volume of 0 is a real zero; a missing volume is None (`VOLUME_MISSING`).
- Weekly bars follow rule W1 (§7.4) without an exchange calendar.
- Price-basis continuity (§7.3, owner decision Q3) never re-adjusts prices. Without split events every
  window is `PRICE_BASIS_CONTINUITY_UNCONFIRMED`; a window that crosses a split is `CORPORATE_ACTION_IN_WINDOW`.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import re
from zoneinfo import ZoneInfo

SCHEMA = 'chart-bars/1'
SOURCE_SCHEMA = 'private-history/1'
FALLBACK_PROVIDERS = ('Tiingo EOD', 'KRX OPEN API')
STATUSES = ('COMPLETE', 'IN_PROGRESS', 'UNKNOWN')
OHLC = ('open', 'high', 'low', 'close')
COMPARED = ('open', 'high', 'low', 'close', 'volume')
_DAY = re.compile(r'^\d{4}-\d{2}-\d{2}$')


class ChartBarsError(ValueError):
    """Carries a fixed reason code only; never a price or a symbol."""


def _fail(code):
    raise ChartBarsError(code)


def _day(value):
    if not isinstance(value, str) or not _DAY.match(value):
        return None
    try:
        return date.fromisoformat(value).isoformat() == value and value
    except ValueError:
        return None


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value == value and value not in (float('inf'), float('-inf'))


def session_date(timestamp, tz):
    """Exchange-local calendar date of a provider timestamp (same rule as PrivateTrades/WorkerQuoteFallback)."""
    return datetime.fromtimestamp(timestamp, timezone.utc).astimezone(ZoneInfo(tz)).date().isoformat()


def _ohlc_consistent(bar):
    o, h, l, c = (bar[k] for k in OHLC)
    return l <= h and l <= o <= h and l <= c <= h


def _quality(bars, header_codes):
    counts = {}
    for code in header_codes:
        counts[code] = counts.get(code, 0) + 1
    for bar in bars:
        for code in bar['codes']:
            counts[code] = counts.get(code, 0) + 1
    return {'codes': sorted(counts), 'counts': {k: counts[k] for k in sorted(counts)}}


def _header_codes(series):
    codes = []
    if series['delay_status'] == 'UNKNOWN':
        codes.append('DELAY_UNKNOWN')
    if series['provider'] in FALLBACK_PROVIDERS:
        codes.append('PROVIDER_FALLBACK')
    return codes


def _finish(bars):
    """Marks non-complete bars that sit before a later complete bar, then re-indexes."""
    last_complete = max((i for i, b in enumerate(bars) if b['session_status'] == 'COMPLETE'), default=-1)
    for i, bar in enumerate(bars):
        bar['index'] = i
        codes = [c for c in bar['codes'] if c != 'NON_COMPLETE_IN_HISTORY']
        if bar['state'] == 'PROVISIONAL' and i < last_complete:
            codes.append('NON_COMPLETE_IN_HISTORY')
        bar['codes'] = sorted(set(codes))
    return bars


def normalize(history):
    """private-history/1 (validated) -> chart-bars/1 daily series."""
    if not isinstance(history, dict) or history.get('schema') != SOURCE_SCHEMA or history.get('interval') != '1d' \
            or history.get('basis') != 'RAW_CLOSE' or not isinstance(history.get('bars'), list) \
            or not isinstance(history.get('timezone'), str) or not isinstance(history.get('symbol'), str):
        _fail('CHART_BARS_INPUT_INVALID')
    try:
        ZoneInfo(history['timezone'])
    except Exception:  # noqa: BLE001 - any zone failure is the same fixed code
        _fail('CHART_BARS_INPUT_INVALID')
    bars, previous = [], 0
    for raw in history['bars']:
        if not isinstance(raw, dict) or not isinstance(raw.get('timestamp'), int) or isinstance(raw.get('timestamp'), bool) \
                or raw['timestamp'] <= previous or raw.get('session_status') not in STATUSES:
            _fail('CHART_BARS_INPUT_INVALID')
        previous = raw['timestamp']
        for key in ('open', 'high', 'low', 'close', 'adjusted_close', 'volume'):
            value = raw.get(key)
            if value is not None and (not _number(value) or (value < 0 if key == 'volume' else value <= 0)):
                _fail('CHART_BARS_INPUT_INVALID')
        day = raw.get('session_date')
        if day is not None and not _day(day):
            _fail('CHART_BARS_INPUT_INVALID')
        day = day or session_date(raw['timestamp'], history['timezone'])
        codes = []
        complete = raw['session_status'] == 'COMPLETE'
        if not complete:
            codes.append('PROVISIONAL_SESSION')
        present = all(raw.get(k) is not None for k in OHLC)
        if not present:
            codes.append('OHLC_MISSING')
        elif not _ohlc_consistent(raw):
            present = False
            codes.append('OHLC_INCONSISTENT')
        volume_reported = raw.get('volume') is not None
        if not volume_reported:
            codes.append('VOLUME_MISSING')
        bars.append({
            'index': 0, 'session_date': day, 'timestamp': raw['timestamp'],
            'open': raw.get('open'), 'high': raw.get('high'), 'low': raw.get('low'), 'close': raw.get('close'),
            'adjusted_close': raw.get('adjusted_close'), 'volume': raw.get('volume'),
            'session_status': raw['session_status'], 'state': 'COMPLETE' if complete else 'PROVISIONAL',
            'ohlc': 'PRESENT' if present else 'MISSING', 'volume_state': 'REPORTED' if volume_reported else 'MISSING',
            'codes': codes,
        })
    seen = {}
    for bar in bars:
        seen[bar['session_date']] = seen.get(bar['session_date'], 0) + 1
    for bar in bars:
        if seen[bar['session_date']] > 1:
            bar['ohlc'], bar['volume_state'] = 'MISSING', 'MISSING'
            bar['codes'].append('DUPLICATE_SESSION_DATE')
    if any(b['session_date'] > n['session_date'] for b, n in zip(bars, bars[1:])):
        _fail('CHART_BARS_INPUT_INVALID')
    series = {
        'schema': SCHEMA, 'source_schema': SOURCE_SCHEMA, 'timeframe': 'D',
        'symbol': history['symbol'], 'provider': history.get('provider'), 'exchange': history.get('exchange'),
        'currency': history.get('currency'), 'timezone': history['timezone'], 'read_at': history.get('read_at'),
        'delay_status': history.get('delay_status'), 'interval': '1d', 'basis': 'RAW_CLOSE',
        'bars': _finish(bars),
    }
    series['quality'] = _quality(series['bars'], _header_codes(series))
    return series


def _js_sum(values):
    # Plain left-to-right addition like Array.reduce; builtin sum() compensates float error since Python 3.12.
    total = 0
    for value in values:
        total = total + value
    return total


def _weekday(day):
    return date.fromisoformat(day).weekday()


def _week_start(day):
    d = date.fromisoformat(day)
    return (d - timedelta(days=d.weekday())).isoformat()


def corporate_actions(value):
    """Normalizes the client-side corporate-action input. Unknown or malformed input never counts as 'no events'.

    Accepted shape (G1 field names are an open owner decision; nothing is sent by the Worker today):
      None / {'status': 'NOT_PROVIDED'}            -> no event data was supplied
      {'status': 'LOOKUP_FAILED'}                   -> the lookup was attempted and failed
      {'status': 'AVAILABLE', 'covered_from': d, 'covered_to': d, 'events': [{'kind': 'SPLIT'|'DIVIDEND', 'effective_date': d}]}
    """
    if value is None:
        return {'status': 'NOT_PROVIDED', 'splits': []}
    if not isinstance(value, dict) or value.get('status') not in ('NOT_PROVIDED', 'LOOKUP_FAILED', 'AVAILABLE'):
        return {'status': 'INVALID', 'splits': []}
    if value['status'] != 'AVAILABLE':
        return {'status': value['status'], 'splits': []}
    start, end, events = _day(value.get('covered_from')), _day(value.get('covered_to')), value.get('events')
    if not start or not end or start > end or not isinstance(events, list):
        return {'status': 'INVALID', 'splits': []}
    splits = []
    for event in events:
        if not isinstance(event, dict) or event.get('kind') not in ('SPLIT', 'DIVIDEND') or not _day(event.get('effective_date')):
            return {'status': 'INVALID', 'splits': []}
        if event['kind'] == 'SPLIT':
            splits.append(event['effective_date'])
    return {'status': 'AVAILABLE', 'covered_from': start, 'covered_to': end, 'splits': sorted(set(splits))}


def _actions(value):
    return value if isinstance(value, dict) and 'splits' in value and 'status' in value else corporate_actions(value)


def continuity(actions, start, end):
    """Price-basis continuity of a window [start, end] (session dates). Never re-adjusts prices.

    A window crosses a split when start < effective_date <= end (the effective date is the first session on the
    new basis). Dividends do not change the raw OHLC basis and are not judged.
    """
    actions = _actions(actions)
    status = actions['status']
    if status != 'AVAILABLE':
        sub = {'NOT_PROVIDED': 'CORPORATE_ACTION_EVENTS_NOT_PROVIDED', 'LOOKUP_FAILED': 'CORPORATE_ACTION_LOOKUP_FAILED'}
        return {'state': 'NOT_JUDGEABLE', 'reason_codes': ['PRICE_BASIS_CONTINUITY_UNCONFIRMED', sub.get(status, 'CORPORATE_ACTION_EVENTS_INVALID')]}
    if start < actions['covered_from'] or end > actions['covered_to']:
        return {'state': 'NOT_JUDGEABLE', 'reason_codes': ['PRICE_BASIS_CONTINUITY_UNCONFIRMED', 'CORPORATE_ACTION_COVERAGE_GAP']}
    if any(start < d <= end for d in actions['splits']):
        return {'state': 'NOT_JUDGEABLE', 'reason_codes': ['CORPORATE_ACTION_IN_WINDOW']}
    return {'state': 'CONFIRMED', 'reason_codes': []}


def weekly(series, actions=None):
    """Daily chart-bars/1 -> weekly bars under rule W1 (§7.4).

    A week (ISO Monday-Sunday of the session date) is complete when its Friday session is COMPLETE, otherwise when
    the first COMPLETE daily bar of a later week appears; its known_at is that session date. A week holding a
    non-complete daily bar stays provisional. Any missing OHLC (volume) inside the week makes the weekly OHLC
    (volume) None; partial sums are never used. A week that straddles a split effective date is NA as well.
    """
    if not isinstance(series, dict) or series.get('schema') != SCHEMA or series.get('timeframe') != 'D':
        _fail('CHART_BARS_INPUT_INVALID')
    splits = _actions(actions)['splits']
    groups = {}
    for bar in series['bars']:
        groups.setdefault(_week_start(bar['session_date']), []).append(bar)
    keys = sorted(groups)
    out = []
    for n, key in enumerate(keys):
        days = groups[key]
        codes = []
        later = next((b for k in keys[n + 1:] for b in groups[k] if b['state'] == 'COMPLETE'), None)
        weekend = any(_weekday(b['session_date']) >= 5 for b in days)
        friday = next((b for b in days if _weekday(b['session_date']) == 4), None)
        if any(b['state'] != 'COMPLETE' for b in days):
            state, known_at = 'PROVISIONAL', None
            codes.append('PROVISIONAL_DAILY_IN_WEEK')
        elif friday is not None and not weekend:
            state, known_at = 'COMPLETE', friday['session_date']
        elif later is not None:
            state, known_at = 'COMPLETE', later['session_date']
        else:
            state, known_at = 'PROVISIONAL', None
            codes.append('WEEK_NOT_CLOSED')
        if weekend:
            codes.append('WEEKEND_SESSION')
        first, last = days[0]['session_date'], days[-1]['session_date']
        straddles = any(first < d <= last for d in splits)
        ohlc_ok = all(b['ohlc'] == 'PRESENT' for b in days) and not weekend and not straddles
        volume_ok = all(b['volume_state'] == 'REPORTED' for b in days) and not straddles
        if not all(b['ohlc'] == 'PRESENT' for b in days):
            codes.append('OHLC_MISSING_IN_WEEK')
        if not all(b['volume_state'] == 'REPORTED' for b in days):
            codes.append('VOLUME_MISSING_IN_WEEK')
        if straddles:
            codes.append('CORPORATE_ACTION_IN_BAR')
        out.append({
            'index': n, 'week_start': key, 'first_session': first, 'last_session': last, 'session_count': len(days),
            'timestamp': days[-1]['timestamp'],
            'open': days[0]['open'] if ohlc_ok else None,
            'high': max(b['high'] for b in days) if ohlc_ok else None,
            'low': min(b['low'] for b in days) if ohlc_ok else None,
            'close': days[-1]['close'] if ohlc_ok else None,
            'volume': _js_sum(b['volume'] for b in days) if volume_ok else None,
            'state': state, 'known_at': known_at,
            'ohlc': 'PRESENT' if ohlc_ok else 'MISSING', 'volume_state': 'REPORTED' if volume_ok else 'MISSING',
            'codes': sorted(set(codes)),
        })
    result = {k: v for k, v in series.items() if k not in ('bars', 'quality', 'timeframe')}
    result['timeframe'] = 'W'
    result['bars'] = out
    result['quality'] = _quality(out, _header_codes(series))
    return result


def merge(previous, incoming, prefer='PREVIOUS'):
    """Merges a newer response (e.g. 1mo refresh) into a held daily series by session date (§6.3).

    A date that was COMPLETE before and now differs in raw OHLCV (or is no longer COMPLETE) keeps the earlier
    values and gains `PRICE_REVISED`; the date is listed in `revised`. Provisional bars are replaced.
    prefer='INCOMING' builds the separate "revised data" view (§8.6): revised dates take the new values, still
    marked `PRICE_REVISED`. The official history keeps running on the default view.
    """
    if prefer not in ('PREVIOUS', 'INCOMING'):
        _fail('CHART_BARS_INPUT_INVALID')
    for s in (previous, incoming):
        if not isinstance(s, dict) or s.get('schema') != SCHEMA or s.get('timeframe') != 'D':
            _fail('CHART_BARS_INPUT_INVALID')
    if previous['symbol'] != incoming['symbol'] or previous['timezone'] != incoming['timezone']:
        _fail('CHART_BARS_MERGE_MISMATCH')
    held = {b['session_date']: b for b in previous['bars']}
    revised = []
    for bar in incoming['bars']:
        old = held.get(bar['session_date'])
        if old is None or old['state'] != 'COMPLETE':
            held[bar['session_date']] = {**bar, 'codes': [c for c in bar['codes'] if c != 'PRICE_REVISED']}
            continue
        if bar['state'] != 'COMPLETE' or any(old[k] != bar[k] for k in COMPARED):
            revised.append(bar['session_date'])
            kept = bar if prefer == 'INCOMING' else old
            held[bar['session_date']] = {**kept, 'codes': sorted(set(kept['codes']) | {'PRICE_REVISED'})}
    bars = [dict(held[d]) for d in sorted(held)]
    merged = {k: v for k, v in previous.items() if k not in ('bars', 'quality')}
    merged['read_at'] = incoming['read_at']
    merged['bars'] = _finish(bars)
    header = _header_codes(merged) + (['PROVIDER_MIXED'] if previous['provider'] != incoming['provider'] else [])
    merged['quality'] = _quality(merged['bars'], header)
    return {'series': merged, 'revised': sorted(revised)}


def session_set_mismatch(series, store_dates):
    """Compares COMPLETE session dates with a close-store date set over the overlapping range (§7.5)."""
    days = sorted({b['session_date'] for b in series['bars'] if b['state'] == 'COMPLETE'})
    store = sorted({d for d in store_dates if _day(d)})
    if not days or not store:
        return {'state': 'NOT_AVAILABLE', 'reason_codes': ['NO_OVERLAP'], 'missing_in_bars': 0, 'missing_in_store': 0}
    lo, hi = max(days[0], store[0]), min(days[-1], store[-1])
    a, b = {d for d in days if lo <= d <= hi}, {d for d in store if lo <= d <= hi}
    if lo > hi:
        return {'state': 'NOT_AVAILABLE', 'reason_codes': ['NO_OVERLAP'], 'missing_in_bars': 0, 'missing_in_store': 0}
    missing_in_bars, missing_in_store = len(b - a), len(a - b)
    mismatch = bool(missing_in_bars or missing_in_store)
    return {'state': 'MISMATCH' if mismatch else 'MATCH', 'reason_codes': ['SESSION_SET_MISMATCH'] if mismatch else [],
            'missing_in_bars': missing_in_bars, 'missing_in_store': missing_in_store}
