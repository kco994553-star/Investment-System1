"""Price store v1: Python reference of the pure logic of web_assets/price-store.js.

The device keeps daily and month-end closes in the user's own Google Sheet (tabs Prices_D and Prices_M, append-only,
drive.file session) so a close fetched once is not fetched again. This module mirrors the device's pure part on the
shared SYNTHETIC vectors (tests/fixtures/price_store_v1.json): tab parsing (fixed header, malformed rows skipped and
counted, first stored row wins), the Worker payload → final closes rule (the virtual-trading runner's own rule), the
month-end selection from daily bars, the next Worker range (only ranges the Worker supports: 1mo … 5y), the append plan
(dedupe by symbol + date for daily and symbol + month for month-end rows; a provider revision of a stored close is
ignored and only counted as PRICE_REVISED_IGNORED), the merged month-end view and the runner payload window.
No price is read, written or logged here: inputs are synthetic in tests and RAM-only on the device.
"""
from __future__ import annotations

from datetime import date, timedelta
import calendar
import json
import re

from . import virtual_ledger_sheets as vls
from . import virtual_trading_inputs as vi

SCHEMA = 'price-store/1'
TAB_DAILY = 'Prices_D'
TAB_MONTHLY = 'Prices_M'
TABS = {'1d': TAB_DAILY, '1mo': TAB_MONTHLY}
HEAD = ('symbol', 'date', 'close', 'source', 'fetched_at')
RANGES = (('1mo', 1), ('3mo', 3), ('6mo', 6), ('1y', 12), ('2y', 24), ('5y', 60))
RUNNER_RANGE = '2y'
MAX_BARS = 1500
SOURCES = {'Yahoo Finance(비공식)': 'YAHOO', 'Tiingo EOD': 'TIINGO', 'KRX OPEN API': 'KRX'}
SYMBOL = re.compile(r'[A-Z0-9][A-Z0-9.=\-]{0,15}')
SOURCE = re.compile(r'[A-Z][A-Z0-9_]{0,31}')
NUMBER_TEXT = vls.NUMBER_TEXT
DAY = re.compile(r'\d{4}-\d{2}-\d{2}')
MONTH = re.compile(r'\d{4}-\d{2}')
CLOCK = re.compile(r'\d{2}:\d{2}')
# Regular-session close (local time) after which today's daily bar can be final. FX pairs: never the same day.
CLOSE_TIMES = (('.KS', '15:30'), ('.T', '15:30'), ('=X', None))
US_CLOSE = '16:00'
UNIVERSE_CODE = re.compile(r'(?:NYSE|NASDAQ|BATS):([A-Z][A-Z0-9.]{0,15})')


class StoreError(ValueError):
    pass


def _fail(code):
    raise StoreError(code)


def is_day(v):
    if not (isinstance(v, str) and DAY.fullmatch(v) and v >= '1900-01-01'):
        return False
    try:
        return date.fromisoformat(v).isoformat() == v
    except ValueError:
        return False


def _ok_symbol(v):
    return isinstance(v, str) and SYMBOL.fullmatch(v) is not None


def currency_for(symbol):
    if symbol.endswith('.KS') or symbol.endswith('=X'):
        return 'KRW'
    if symbol.endswith('.T'):
        return 'JPY'
    return 'USD'


def timezone_for(symbol):
    if symbol.endswith('.KS'):
        return 'Asia/Seoul'
    if symbol.endswith('.T'):
        return 'Asia/Tokyo'
    if symbol.endswith('=X'):
        return 'Europe/London'
    return 'America/New_York'


def universe_symbol(code):
    """Public Universe504 code → Worker/Yahoo symbol ('NYSE:BRK.B' → 'BRK-B'); anything else → None."""
    m = UNIVERSE_CODE.fullmatch(code) if isinstance(code, str) else None
    return m.group(1).replace('.', '-') if m else None


# ---------- tab parsing ----------

def parse_tab(values, interval):
    """values = [header, row, ...] as read (rows: at least symbol, date, close). A header other than HEAD fails with
    SHEET_HEADER_MISMATCH (nothing is written). Empty rows are skipped; malformed rows are skipped and counted."""
    if interval not in TABS:
        _fail('INVALID')
    if not isinstance(values, list):
        _fail('SHEET_ROWS_INVALID')
    if not values:
        return {'header': False, 'rows': [], 'invalid': 0}
    first = values[0]
    if not isinstance(first, list) or len(first) != len(HEAD) or any(c != h for c, h in zip(first, HEAD)):
        _fail('SHEET_HEADER_MISMATCH')
    rows, invalid = [], 0
    for raw in values[1:]:
        if not isinstance(raw, list) or not any(c not in ('', None) for c in raw):
            continue
        cells = list(raw[:3]) + [''] * max(0, 3 - len(raw))
        symbol, day, text = cells
        if not (_ok_symbol(symbol) and is_day(day) and isinstance(text, str) and NUMBER_TEXT.fullmatch(text)):
            invalid += 1
            continue
        close = float(text)
        if not close > 0 or close == float('inf'):
            invalid += 1
            continue
        rows.append([symbol, day, close])
    return {'header': True, 'rows': rows, 'invalid': invalid}


def index_rows(rows, interval):
    """Stored rows (sheet order) → {symbol: {key: close}} with key = date (1d) or month (1mo). First row wins."""
    series, duplicates = {}, 0
    for symbol, day, close in rows:
        key = day if interval == '1d' else day[:7]
        s = series.setdefault(symbol, {})
        if key in s:
            duplicates += 1
            continue
        s[key] = close
    return {'series': {k: dict(sorted(v.items())) for k, v in sorted(series.items())}, 'duplicates': duplicates}


# ---------- Worker payload ----------

def closes_from_history(payload, symbol):
    """Worker private-history/1 payload → (final closes {date: close}, None) or ({}, code): the runner's rule."""
    return vi.series_from_history(payload, symbol, currency_for(symbol))


def source_of(payload):
    provider = payload.get('provider') if isinstance(payload, dict) else None
    return SOURCES.get(provider, 'UNKNOWN') if isinstance(provider, str) else 'UNKNOWN'


def month_ends(closes, as_of):
    """Daily closes → {month: [last session date, close]} for complete months only (month before as_of's month)."""
    current = as_of[:7]
    out = {}
    for day in sorted(closes):
        if day[:7] < current:
            out[day[:7]] = [day, closes[day]]
    return out


# ---------- incremental plan ----------

def _months_back(today, n):
    y, m = today.year, today.month - n
    while m <= 0:
        y, m = y - 1, m + 12
    return date(y, m, min(today.day, calendar.monthrange(y, m)[1]))


def due_date(symbol, local_day, local_time):
    """Latest session date whose close can be final at local_day local_time (weekends → Friday; holidays are not known,
    a holiday only costs one extra request)."""
    if not is_day(local_day) or not (isinstance(local_time, str) and CLOCK.fullmatch(local_time)):
        _fail('INVALID')
    close = US_CLOSE
    for suffix, at in CLOSE_TIMES:
        if symbol.endswith(suffix):
            close = at
    d = date.fromisoformat(local_day)
    if not (d.weekday() < 5 and close is not None and local_time >= close):
        d -= timedelta(days=1)
        while d.weekday() >= 5:
            d -= timedelta(days=1)
    return d.isoformat()


def next_range(last, due, today):
    """Daily: None when the last stored date reaches the due date, else the smallest Worker range whose window starts on
    or before the last stored date (overlap), '5y' without stored rows or for a longer gap."""
    if last is not None and last >= due:
        return None
    if last is None:
        return '5y'
    t, stop = date.fromisoformat(today), date.fromisoformat(last)
    for name, months in RANGES:
        if _months_back(t, months) <= stop:
            return name
    return '5y'


def month_due(today):
    """The last complete month at today ('YYYY-MM')."""
    d = date.fromisoformat(today)
    y, m = (d.year, d.month - 1) if d.month > 1 else (d.year - 1, 12)
    return '%04d-%02d' % (y, m)


def next_month_range(last_month, today):
    """Month-end rows: None when the last stored month reaches the last complete month, else the smallest Worker range
    whose window starts on or before the last stored month's last day; '5y' without stored rows (first backfill)."""
    if last_month is not None and last_month >= month_due(today):
        return None
    if last_month is None:
        return '5y'
    y, m = int(last_month[:4]), int(last_month[5:7])
    return next_range(date(y, m, calendar.monthrange(y, m)[1]).isoformat(), '9999-12-31', today)


def append_plan(stored, fetched, interval):
    """stored {key: close}; fetched daily {date: close} or month-ends {month: [date, close]} → rows to append
    [[date, close]] (keys not stored, date order) and how many stored keys the provider now reports differently."""
    out, revised = [], 0
    for key in sorted(fetched):
        item = fetched[key]
        day, close = (key, item) if interval == '1d' else (item[0], item[1])
        if key in stored:
            if stored[key] != close:
                revised += 1
            continue
        out.append([day, close])
    out.sort(key=lambda r: r[0])
    return {'append': out, 'revised_ignored': revised}


def sheet_rows(symbol, plan_rows, source, fetched_at):
    return [[symbol, day, vls.num_str(close), source, fetched_at] for day, close in plan_rows]


# ---------- reads ----------

def month_end_closes(daily, monthly, as_of):
    """{month: close}: stored month-end rows first; complete months missing there come from the stored daily closes."""
    out = dict(monthly or {})
    for month, (_, close) in month_ends(daily or {}, as_of).items():
        out.setdefault(month, close)
    return dict(sorted(out.items()))


def daily_closes(daily, from_date=None):
    return {d: c for d, c in sorted((daily or {}).items()) if from_date is None or d >= from_date}


def runner_payload(closes, symbol, today, read_at):
    """Stored daily closes → a private-history/1 payload the runner reads exactly like a Worker answer: the runner's
    2y window (dates on or after today minus 24 months), at most MAX_BARS bars, every bar COMPLETE."""
    cutoff = _months_back(date.fromisoformat(today), 24).isoformat()
    days = [d for d in sorted(closes) if d >= cutoff][-MAX_BARS:]
    bars = []
    for d in days:
        y, m, dd = int(d[:4]), int(d[5:7]), int(d[8:])
        ts = calendar.timegm((y, m, dd, 12, 0, 0))
        bars.append({'timestamp': ts, 'session_date': d, 'session_status': 'COMPLETE', 'close': closes[d]})
    return {'schema': 'private-history/1', 'provider': 'PRICE_STORE', 'symbol': symbol, 'range': RUNNER_RANGE,
            'currency': currency_for(symbol), 'exchange': 'PRICE_STORE', 'timezone': timezone_for(symbol), 'interval': '1d',
            'basis': 'RAW_CLOSE', 'delay_status': 'UNKNOWN', 'read_at': read_at, 'bars': bars}


def chunk_rows(rows, max_bytes):
    """Append chunks whose JSON text stays within max_bytes (each row alone always fits)."""
    out, cur, size = [], [], 0
    for r in rows:
        n = len(json.dumps(r, ensure_ascii=False, separators=(',', ':'))) + 1
        if cur and size + n > max_bytes:
            out.append(cur)
            cur, size = [], 0
        cur.append(r)
        size += n
    if cur:
        out.append(cur)
    return out
