"""A supplied, verified exchange-session table; never synthesizes historical sessions.

The caller supplies a complete table over the declared coverage, including early
closes and unscheduled closures. Synthetic hand tables are used by unit tests;
their existence is not evidence that a historical exchange calendar was verified.
"""
from __future__ import annotations

from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo


def day(value):
    if isinstance(value, datetime):
        raise ValueError('SESSION_DATE_REQUIRED')
    return value if isinstance(value, date) else date.fromisoformat(value)


def aware(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00')) if isinstance(value, str) else value
    if not isinstance(result, datetime) or result.utcoffset() is None:
        raise ValueError('TIMEZONE_AWARE_INSTANT_REQUIRED')
    return result.astimezone(timezone.utc)


@dataclass(frozen=True)
class Session:
    day: date
    open_at: datetime
    close_at: datetime

    def __post_init__(self):
        object.__setattr__(self, 'day', day(self.day))
        object.__setattr__(self, 'open_at', aware(self.open_at))
        object.__setattr__(self, 'close_at', aware(self.close_at))
        if self.open_at >= self.close_at:
            raise ValueError('SESSION_OPEN_MUST_PRECEDE_CLOSE')
        if any(moment.astimezone(ZoneInfo('America/New_York')).date() != self.day
               for moment in (self.open_at, self.close_at)):
            raise ValueError('SESSION_DATE_INSTANT_MISMATCH')


class VerifiedSessionCalendar:
    """No missing-table-day fallback to weekday or holiday rules is permitted."""

    def __init__(self, sessions, *, coverage_start, coverage_end, source, verified=True):
        if verified is not True or not isinstance(source, str) or not source.strip():
            raise ValueError('CALENDAR_NOT_VERIFIED')
        self.sessions = tuple(sorted(sessions, key=lambda s: s.day))
        self.coverage_start, self.coverage_end = day(coverage_start), day(coverage_end)
        self.source = source
        self._days = tuple(s.day for s in self.sessions)
        if (not self.sessions or len(set(self._days)) != len(self._days)
                or self.coverage_start > self._days[0] or self.coverage_end < self._days[-1]):
            raise ValueError('CALENDAR_COVERAGE_INVALID')
        if any(a.close_at >= b.open_at for a, b in zip(self.sessions, self.sessions[1:])):
            raise ValueError('CALENDAR_SESSIONS_OVERLAP')

    def _check(self, value):
        value = day(value)
        if not self.coverage_start <= value <= self.coverage_end:
            raise ValueError('CALENDAR_COVERAGE_MISSING')
        return value

    def is_session(self, value):
        value = self._check(value)
        i = bisect_left(self._days, value)
        return i < len(self._days) and self._days[i] == value

    def session(self, value):
        value = self._check(value)
        i = bisect_left(self._days, value)
        if i == len(self._days) or self._days[i] != value:
            raise ValueError('NOT_A_VERIFIED_SESSION')
        return self.sessions[i]

    def on_or_after(self, value):
        value = self._check(value)
        i = bisect_left(self._days, value)
        if i == len(self._days):
            raise ValueError('CALENDAR_COVERAGE_MISSING')
        return self.sessions[i]

    def next_session(self, value):
        value = self._check(value)
        i = bisect_right(self._days, value)
        if i == len(self._days):
            raise ValueError('CALENDAR_COVERAGE_MISSING')
        return self.sessions[i]

    def previous_session(self, value):
        value = self._check(value)
        i = bisect_left(self._days, value) - 1
        if i < 0:
            raise ValueError('CALENDAR_COVERAGE_MISSING')
        return self.sessions[i]

    def completed_sessions(self, value, count=60):
        value = self._check(value)
        if type(count) is not int or count <= 0:
            raise ValueError('SESSION_COUNT_INVALID')
        end = bisect_right(self._days, value)
        return self.sessions[max(0, end - count):end]


@dataclass(frozen=True)
class RebalanceDate:
    nominal_day: date
    signal_day: date
    execution_day: date
    decision_at: datetime
    execute_at: datetime


def rebalance_schedule(calendar, start, end, rebalance='QUARTERLY'):
    """Third Monday in Feb/May/Aug/Nov (or February), rolled to a verified T.

    Only execution dates within start..end are returned. The table must also
    contain S, the session immediately preceding each T.
    """
    start, end = day(start), day(end)
    if start > end:
        raise ValueError('SCHEDULE_RANGE_INVALID')
    calendar._check(start)
    calendar._check(end)
    if rebalance not in ('QUARTERLY', 'ANNUAL_FEBRUARY'):
        raise ValueError('REBALANCE_INVALID')
    months = (2, 5, 8, 11) if rebalance == 'QUARTERLY' else (2,)
    out = []
    for year in range(start.year, end.year + 1):
        for month in months:
            first = date(year, month, 1)
            nominal = first + timedelta(days=(-first.weekday()) % 7 + 14)
            if nominal > end or nominal < calendar.coverage_start:
                continue
            execution = calendar.on_or_after(nominal)
            if start <= execution.day <= end:
                signal = calendar.previous_session(execution.day)
                out.append(RebalanceDate(nominal, signal.day, execution.day, signal.close_at, execution.open_at))
    return tuple(out)
