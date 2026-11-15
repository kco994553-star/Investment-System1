"""Existing NY-midnight session check; no provider collection or price conversion."""
from datetime import datetime, time
from zoneinfo import ZoneInfo
from .. import pit_filings

NY = ZoneInfo("America/New_York")
BAR_TIME_INVALID = "BAR_TIME_INVALID"
BAR_TIME_NOT_NY_MIDNIGHT = "BAR_TIME_NOT_NY_MIDNIGHT"
NON_SESSION_DATE = "NON_SESSION_DATE"
OUTSIDE_RULE_CALENDAR = "OUTSIDE_RULE_CALENDAR"

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
