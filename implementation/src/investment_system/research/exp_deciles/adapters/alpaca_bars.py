"""Alpaca SIP raw daily-bar pages -> EXP-STOCK-INDICATOR-DECILES-v1 ledger price rows. Offline, read only.

Source format (Codex release bt-data-pilot-v06-long-* and PR #459's tools/measure_once/alpaca_sample_once.py
build_archive): one directory per series, raw/<series>/page-NN.json (NN = 00, 01, ... in request order), each file the
exact response body of GET /v2/stocks/{symbol}/bars with timeframe=1Day, adjustment=raw, feed=sip:
  {"bars": [{"t": "<RFC 3339 time>", "o", "h", "l", "c", "v", ...}, ...] | null, "symbol": "<symbol>",
   "next_page_token": "<token>" | null}

Reading a series (`read_series`) refuses the whole series (status REFUSED with one fixed code, no bars) on: no page files
(PAGES_MISSING), a gap in NN (PAGE_SEQUENCE_GAP), a page that is not JSON or not that shape (PAGE_NOT_JSON /
PAGE_SCHEMA_INVALID), different symbols across pages or not the expected one (SYMBOL_MISMATCH), a token on the last page or
none on an earlier one (PAGINATION_INCOMPLETE / PAGINATION_INCONSISTENT), a bar time without a zone or not parseable
(BAR_TIME_INVALID), a bar time that is not 00:00 New York (BAR_TIME_NOT_NY_MIDNIGHT), a New York date that is not an NYSE
session of the rule calendar (NON_SESSION_DATE; OUTSIDE_RULE_CALENDAR outside 2009..2028) and dates not strictly ascending
(BAR_ORDER_INVALID).

Session date: a daily bar's `t` is the start of the bar, 00:00 New York (05:00Z in winter, 04:00Z in summer); the
session date is the New York date of `t`. A UTC-midnight stamp (00:00Z = 19:00 / 20:00 New York of the day before) is not
reinterpreted: it is refused, because its New York date is the previous calendar day and could silently shift every price
by one session.

Price rows (`price_rows`): {date, security_id, open, close, suspended: False (a bar exists only for a day with trades),
price_basis: 'RAW', currency: 'USD', source: SOURCE} for every bar of the series inside [start, end] and the caller's
security span. `open` comes only from `o` and `close` only from `c` (kept separate; an invalid one is None while the other
stays); a bar with neither is left out; a day without a bar has no row: nothing is filled from another day, the T open is
never taken from a close or from an IEX last trade. The SIP daily open is the consolidated open candidate for T
(OPEN_ROLE). Volumes, highs and lows are not used.

`coverage` reports, per series, the S close, the T open, the next reselection T open, each month-end mark and the holding
period's sessions as SUPPLIED or a fixed missing code, so a missing T bar shows up as T_OPEN_BAR_MISSING (the engine then
records the order unfilled) and never as a filled price.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, time
from pathlib import Path
import re
from zoneinfo import ZoneInfo

from ... import pit_filings
from .. import schedule
from .common import SUPPLIED, AdapterError, iso_day, json_exact, positive_decimal, sha256_bytes

SOURCE = 'ALPACA_SIP_DAILY_BAR_RAW'
SOURCE_NAME = 'Alpaca market data v2 historical daily bars, feed=sip, adjustment=raw'
OPEN_ROLE = 'CONSOLIDATED_OPEN_CANDIDATE_FOR_T'
RIGHTS_NOTE = ('Alpaca market data: personal, non-commercial use; public posting or distribution needs prior written '
               'consent; private research input only')
NY = ZoneInfo('America/New_York')
OK, REFUSED = 'OK', 'REFUSED'
PAGE_FILE = re.compile(r'page-([0-9]{2,3})\.json')

# series refusal codes
PAGES_MISSING = 'PAGES_MISSING'
PAGE_SEQUENCE_GAP = 'PAGE_SEQUENCE_GAP'
PAGE_NOT_JSON = 'PAGE_NOT_JSON'
PAGE_SCHEMA_INVALID = 'PAGE_SCHEMA_INVALID'
SYMBOL_MISMATCH = 'SYMBOL_MISMATCH'
PAGINATION_INCOMPLETE = 'PAGINATION_INCOMPLETE'
PAGINATION_INCONSISTENT = 'PAGINATION_INCONSISTENT'
BAR_TIME_INVALID = 'BAR_TIME_INVALID'
BAR_TIME_NOT_NY_MIDNIGHT = 'BAR_TIME_NOT_NY_MIDNIGHT'
NON_SESSION_DATE = 'NON_SESSION_DATE'
OUTSIDE_RULE_CALENDAR = 'OUTSIDE_RULE_CALENDAR'
BAR_ORDER_INVALID = 'BAR_ORDER_INVALID'
# coverage codes
SERIES_NOT_SUPPLIED = 'SERIES_NOT_SUPPLIED'
SERIES_REFUSED = 'SERIES_REFUSED'
S_BAR_MISSING = 'S_BAR_MISSING'
S_CLOSE_INVALID = 'S_CLOSE_INVALID'
T_OPEN_BAR_MISSING = 'T_OPEN_BAR_MISSING'
T_OPEN_INVALID = 'T_OPEN_INVALID'
NEXT_T_OPEN_BAR_MISSING = 'NEXT_T_OPEN_BAR_MISSING'
NEXT_T_OPEN_INVALID = 'NEXT_T_OPEN_INVALID'
MONTH_END_BAR_MISSING = 'MONTH_END_BAR_MISSING'
MONTH_END_CLOSE_INVALID = 'MONTH_END_CLOSE_INVALID'
OUTSIDE_SECURITY_SPAN = 'OUTSIDE_SECURITY_SPAN'


def _refused(reason, pages, counts=None):
    return {'symbol': None, 'status': REFUSED, 'reason': reason, 'bars': {}, 'pages': pages,
            'counts': dict(sorted((counts or Counter()).items()))}


def session_date(text):
    """(New York session date, None) of a bar time, or (None, refusal code)."""
    if not isinstance(text, str):
        return None, BAR_TIME_INVALID
    try:
        at = datetime.fromisoformat(text.replace('Z', '+00:00'))
    except ValueError:
        return None, BAR_TIME_INVALID
    if at.tzinfo is None:
        return None, BAR_TIME_INVALID
    local = at.astimezone(NY)
    if local.time() != time(0, 0):
        return None, BAR_TIME_NOT_NY_MIDNIGHT
    day = local.date()
    try:
        if not pit_filings.is_session(day):
            return None, NON_SESSION_DATE
    except pit_filings.CalendarNotConfigured:
        return None, OUTSIDE_RULE_CALENDAR
    return day, None


def page_files(series_dir):
    """[(NN, path)] of the page-NN.json files of one series directory, sorted by NN."""
    folder = Path(series_dir)
    if not folder.is_dir():
        return []
    found = []
    for path in folder.iterdir():
        match = PAGE_FILE.fullmatch(path.name)
        if match and path.is_file() and not path.is_symlink():
            found.append((int(match.group(1)), path))
    return sorted(found)


def read_series(series_dir, *, expected_symbol=None):
    """{'symbol', 'status' OK | REFUSED, 'reason', 'bars': {date: {'open', 'close'}}, 'pages': [{'file', 'sha256'}],
    'counts'} of one series directory (module doc)."""
    files = page_files(series_dir)
    pages, counts = [], Counter()
    if not files:
        return _refused(PAGES_MISSING, pages)
    if [n for n, _ in files] != list(range(len(files))):
        return _refused(PAGE_SEQUENCE_GAP, pages)
    symbol, bars, last = None, {}, None
    for position, (n, path) in enumerate(files):
        try:
            data = path.read_bytes()
        except OSError:
            raise AdapterError('ALPACA_PAGE_NOT_READABLE') from None
        pages.append({'file': path.name, 'sha256': sha256_bytes(data)})
        try:
            body = json_exact(data)
        except AdapterError:
            return _refused(PAGE_NOT_JSON, pages)
        if not isinstance(body, dict) or not isinstance(body.get('symbol'), str) or not body['symbol']:
            return _refused(PAGE_SCHEMA_INVALID, pages)
        rows = body.get('bars')
        rows = [] if rows is None else rows
        token = body.get('next_page_token')
        if not isinstance(rows, list) or (token is not None and not isinstance(token, str)):
            return _refused(PAGE_SCHEMA_INVALID, pages)
        if symbol is None:
            symbol = body['symbol']
        if body['symbol'] != symbol or (expected_symbol is not None and symbol != expected_symbol):
            return _refused(SYMBOL_MISMATCH, pages)
        final = position == len(files) - 1
        if final and token:
            return _refused(PAGINATION_INCOMPLETE, pages)
        if not final and not token:
            return _refused(PAGINATION_INCONSISTENT, pages)
        for bar in rows:
            if not isinstance(bar, dict):
                return _refused(PAGE_SCHEMA_INVALID, pages)
            day, problem = session_date(bar.get('t'))
            if problem is not None:
                counts[problem] += 1
                return _refused(problem, pages, counts)
            if last is not None and day <= last:
                return _refused(BAR_ORDER_INVALID, pages)
            opening, closing = positive_decimal(bar.get('o')), positive_decimal(bar.get('c'))
            counts['bars'] += 1
            counts['open_invalid'] += opening is None
            counts['close_invalid'] += closing is None
            bars[day], last = {'open': opening, 'close': closing}, day
    return {'symbol': symbol, 'status': OK, 'reason': None, 'bars': bars, 'pages': pages,
            'counts': dict(sorted(counts.items()))}


def _in_span(day, span):
    if span is None:
        return True
    first, end = span
    return (first is None or day >= iso_day(first)) and (end is None or day < iso_day(end))


def price_rows(series, security_id, *, start, end, span=None):
    """Engine ledger price rows of one read series for one security (module doc). span = (first session under the
    symbol, first day no longer under it; None = open) clips bars of a reused symbol away."""
    if not isinstance(security_id, str) or not security_id.strip():
        raise AdapterError('SECURITY_ID_INVALID')
    if series is None or series['status'] != OK:
        return []
    first, last = iso_day(start), iso_day(end)
    rows = []
    for day in sorted(series['bars']):
        bar = series['bars'][day]
        if not first <= day <= last or not _in_span(day, span):
            continue
        if bar['open'] is None and bar['close'] is None:
            continue
        rows.append({'date': day.isoformat(), 'security_id': security_id, 'open': bar['open'], 'close': bar['close'],
                     'suspended': False, 'price_basis': 'RAW', 'currency': 'USD', 'source': SOURCE})
    return rows


def _sessions(first, last):
    out, day = [], schedule.session_on_or_after(first)
    while day <= last:
        out.append(day)
        day = schedule.next_session(day)
    return out


def coverage(series, *, signal_day, execution_day, end, span=None):
    """{'s_close', 't_open', 'next_t_open', 'month_ends': {YYYY-MM: code}, 'holding_sessions', 'holding_bars',
    'holding_sessions_without_bar', 'bars_outside_span'} for one series; codes SUPPLIED or the fixed missing codes."""
    signal, execution, last = iso_day(signal_day), iso_day(execution_day), iso_day(end)
    holding = _sessions(execution, last)
    month_ends = [d for d in holding[:-1] if schedule.next_session(d).month != d.month]
    if series is None or series['status'] != OK:
        code = SERIES_NOT_SUPPLIED if series is None else SERIES_REFUSED
        return {'s_close': code, 't_open': code, 'next_t_open': code,
                'month_ends': {d.strftime('%Y-%m'): code for d in month_ends}, 'holding_sessions': len(holding),
                'holding_bars': 0, 'holding_sessions_without_bar': len(holding), 'bars_outside_span': 0}
    bars = {d: b for d, b in series['bars'].items() if _in_span(d, span)}

    def field(day, name, missing, invalid):
        if day not in bars:
            return missing
        return SUPPLIED if bars[day][name] is not None else invalid

    present = sum(1 for d in holding if d in bars)
    return {'s_close': field(signal, 'close', S_BAR_MISSING, S_CLOSE_INVALID),
            't_open': field(execution, 'open', T_OPEN_BAR_MISSING, T_OPEN_INVALID),
            'next_t_open': field(last, 'open', NEXT_T_OPEN_BAR_MISSING, NEXT_T_OPEN_INVALID),
            'month_ends': {d.strftime('%Y-%m'): field(d, 'close', MONTH_END_BAR_MISSING, MONTH_END_CLOSE_INVALID)
                           for d in month_ends},
            'holding_sessions': len(holding), 'holding_bars': present,
            'holding_sessions_without_bar': len(holding) - present,
            'bars_outside_span': len(series['bars']) - len(bars)}
