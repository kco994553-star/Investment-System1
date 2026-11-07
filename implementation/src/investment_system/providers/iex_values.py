"""Pure IEX TOPS value rules shared by the price adapter and its offline readers (no network, no files, no subprocess).

The IEX HIST price adapter (the one module the price-source guard lists) owns every request to the price source. A reader that
only checks rows the adapter or a preservation tool already wrote (e.g. a research converter of a private derived file) needs the
same three rules without importing that adapter: the regular-session window in New York, the IEX symbol shape and the per-share
ceiling of the parser's integer price (price * 10^4). The adapter re-exports these names unchanged, so its behaviour and callers
do not change. Nothing here may reach the price source: test_qgv_official_guards.test_iex_values_stays_pure checks it.
"""
from __future__ import annotations

import datetime as dt
import re
from zoneinfo import ZoneInfo

NY = ZoneInfo('America/New_York')
SESSION = (dt.time(9, 30), dt.time(16, 0))
MAX_PRICE_E4 = 10**11   # $10M per share: anything above is a parser/format fault, never a price


def iso_day(day: str) -> str:
    """YYYYMMDD or YYYY-MM-DD -> YYYY-MM-DD."""
    return day if '-' in day else f'{day[:4]}-{day[4:6]}-{day[6:]}'


def valid_symbol(symbol) -> bool:
    return isinstance(symbol, str) and re.fullmatch(r'[A-Z0-9][A-Z0-9.\-+=^]{0,7}', symbol) is not None


def session_ns(day: str) -> tuple[int, int]:
    """Regular session [09:30, 16:00) New York of day YYYYMMDD / YYYY-MM-DD in Unix nanoseconds."""
    d = dt.date.fromisoformat(iso_day(day))
    start = dt.datetime.combine(d, SESSION[0], NY)
    end = dt.datetime.combine(d, SESSION[1], NY)
    return int(start.timestamp()) * 10**9, int(end.timestamp()) * 10**9
