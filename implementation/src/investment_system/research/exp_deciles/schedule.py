"""Existing session helpers, extracted without EXP strategy configuration."""
from datetime import date, datetime, timedelta
from .. import pit_filings

def _day(value):
    if isinstance(value, datetime):
        raise TypeError('SESSION_DAY_MUST_BE_DATE')
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    raise TypeError('SESSION_DAY_MUST_BE_DATE')

def is_session(day):
    return pit_filings.is_session(_day(day))

def next_session(day):
    """First session strictly after `day`."""
    day = _day(day) + timedelta(days=1)
    while not pit_filings.is_session(day):
        day += timedelta(days=1)
    return day

def previous_session(day):
    """Last session strictly before `day`."""
    day = _day(day) - timedelta(days=1)
    while not pit_filings.is_session(day):
        day -= timedelta(days=1)
    return day
