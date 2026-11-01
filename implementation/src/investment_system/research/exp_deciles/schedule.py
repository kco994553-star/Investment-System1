"""Annual signal day S, execution day T and SEC filing cutoff on the canonical NYSE rule calendar.

Ported from research/qgv_backtest @ 56a0e8ce (#417/#430) and changed for EXP-STOCK-INDICATOR-DECILES-v1:
calendar_adapter.rebalance_schedule (rebalance='ANNUAL_FEBRUARY': third Monday of February -> T = first session on/after it,
S = the session before T). Changed: sessions come from research.pit_filings.is_session (canonical rule calendar 2009-2028,
special closures included) instead of a caller-supplied VerifiedSessionCalendar; only dates are produced here (S close /
T open instants belong to the ledger part); the 6th-session filing rule and the frozen list were added.

Filing rule (settings doc section 1, owner 2026-11-01): a SEC filing whose New York filing date is F becomes usable on the
next session after 5 full NYSE sessions following F, i.e. on usable_from(F) = the 6th session strictly after F. The signal
at S uses a filing iff usable_from(F) <= S.

- filing_cutoff(S) = the 6th session strictly before S: the last SESSION date F with usable_from(F) <= S
  (usable_from(filing_cutoff(S)) == S). This is the "공시 마감 F" column of the settings doc and of schedule_v1.json.
- compute_cutoff(S) = (the 5th session strictly before S) - 1 calendar day: the last CALENDAR date F with
  usable_from(F) <= S. A filing date on a non-session day (weekend, NYSE-only holiday such as Good Friday) lying between
  the 6th and the 5th session before S is still usable at S, so this is the value handed to v2_factors.compute, whose rule
  is `filed <= cutoff`. For every frozen year 2017-2026 compute_cutoff(S) == filing_cutoff(S) (verify_frozen checks it).

Outside 2009..2028 the calendar fails closed (pit_filings.CalendarNotConfigured); dates are never synthesized.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
import hashlib
import json
from pathlib import Path

from .. import pit_filings
from . import settings

FROZEN_FILE = Path(__file__).with_name('schedule_v1.json')
SCHEDULE_SCHEMA = 'exp-deciles-schedule/1'
ROW_KEYS = ('year', 'third_monday', 'S', 'T', 'filing_cutoff')
RULE_TEXT = ('third Monday of February -> T = first NYSE session on/after it; S = the session before T; '
             'filing_cutoff = 6th NYSE session before S (filing usable on the 6th session after its NY filing date)')


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


def session_on_or_after(day):
    day = _day(day)
    return day if pit_filings.is_session(day) else next_session(day)


def sessions_after(day, n):
    """The n-th session strictly after `day` (n >= 1)."""
    if type(n) is not int or n < 1:
        raise ValueError('SESSION_COUNT_INVALID')
    day = _day(day)
    for _ in range(n):
        day = next_session(day)
    return day


def sessions_before(day, n):
    """The n-th session strictly before `day` (n >= 1)."""
    if type(n) is not int or n < 1:
        raise ValueError('SESSION_COUNT_INVALID')
    day = _day(day)
    for _ in range(n):
        day = previous_session(day)
    return day


def third_monday_of_february(year):
    if type(year) is not int:
        raise TypeError('YEAR_MUST_BE_INT')
    first = date(year, 2, 1)
    return first + timedelta(days=(-first.weekday()) % 7 + 14)


def _signal(signal_day):
    signal_day = _day(signal_day)
    if not pit_filings.is_session(signal_day):
        raise ValueError('SIGNAL_DAY_NOT_A_SESSION')
    return signal_day


def usable_from(filing_date):
    """First session on which a filing with New York filing date `filing_date` may be used (6th session after it)."""
    return sessions_after(filing_date, settings.PIT_USABLE_SESSION)


def is_usable(filing_date, signal_day):
    return usable_from(filing_date) <= _signal(signal_day)


def filing_cutoff(signal_day):
    """Last session date F with usable_from(F) <= S: the 6th session strictly before S."""
    return sessions_before(_signal(signal_day), settings.PIT_USABLE_SESSION)


def compute_cutoff(signal_day):
    """Last calendar date F with usable_from(F) <= S, for v2_factors.compute (`filed <= cutoff`)."""
    return sessions_before(_signal(signal_day), settings.PIT_LAG_FULL_SESSIONS) - timedelta(days=1)


def execution_day_for(signal_day):
    """T for a signal day S: the next session."""
    return next_session(_signal(signal_day))


def annual_dates(year):
    """One frozen-list row: {'year', 'third_monday', 'S', 'T', 'filing_cutoff'} (ISO dates)."""
    nominal = third_monday_of_february(year)
    execution = session_on_or_after(nominal)
    signal = previous_session(execution)
    return {'year': year, 'third_monday': nominal.isoformat(), 'S': signal.isoformat(), 'T': execution.isoformat(),
            'filing_cutoff': filing_cutoff(signal).isoformat()}


def build_schedule(years=settings.SCHEDULE_YEARS):
    return [annual_dates(year) for year in years]


def frozen_payload(years=settings.SCHEDULE_YEARS):
    """The exact JSON object written to schedule_v1.json."""
    return {'schema': SCHEDULE_SCHEMA, 'experiment_id': settings.EXPERIMENT_ID, 'calendar': settings.CALENDAR,
            'rule': RULE_TEXT, 'rows': build_schedule(years)}


def dumps(payload):
    return json.dumps(payload, indent=2, ensure_ascii=True) + '\n'


def load_frozen(path=FROZEN_FILE):
    """Read the frozen list (the one stated file read of this part)."""
    return json.loads(Path(path).read_text(encoding='ascii'))


def _row_invariants(row):
    """Rule checks that do not depend on the generator: [reason codes]."""
    problems = []
    nominal, signal, execution, cutoff = (date.fromisoformat(row[k]) for k in ('third_monday', 'S', 'T', 'filing_cutoff'))
    if nominal.month != 2 or nominal.weekday() != 0 or not 15 <= nominal.day <= 21:
        problems.append('THIRD_MONDAY_INVALID')
    if not pit_filings.is_session(execution) or execution < nominal or any(
            pit_filings.is_session(nominal + timedelta(days=i)) for i in range((execution - nominal).days)):
        problems.append('T_NOT_FIRST_SESSION_ON_OR_AFTER_THIRD_MONDAY')
    if not pit_filings.is_session(signal) or signal >= execution or any(
            pit_filings.is_session(signal + timedelta(days=i)) for i in range(1, (execution - signal).days)):
        problems.append('S_NOT_SESSION_BEFORE_T')
    if not pit_filings.is_session(cutoff) or usable_from(cutoff) != signal or usable_from(next_session(cutoff)) <= signal:
        problems.append('FILING_CUTOFF_NOT_6TH_SESSION_BEFORE_S')
    if compute_cutoff(signal) != cutoff:
        problems.append('COMPUTE_CUTOFF_DIFFERS_FROM_FILING_CUTOFF')
    return problems


def verify_frozen(path=FROZEN_FILE):
    """Recompute the schedule and compare it with the frozen file.

    Returns {'ok', 'mismatches': [{'year', 'field', 'frozen', 'computed'} | {'year', 'reason'}], 'rows', 'sha256'}."""
    raw = Path(path).read_bytes()
    frozen = json.loads(raw.decode('ascii'))
    mismatches = []
    expected = frozen_payload()
    for key in ('schema', 'experiment_id', 'calendar', 'rule'):
        if frozen.get(key) != expected[key]:
            mismatches.append({'year': None, 'field': key, 'frozen': frozen.get(key), 'computed': expected[key]})
    rows = frozen.get('rows') if isinstance(frozen.get('rows'), list) else []
    if [r.get('year') for r in rows if isinstance(r, dict)] != list(settings.SCHEDULE_YEARS):
        mismatches.append({'year': None, 'field': 'years', 'frozen': [r.get('year') for r in rows if isinstance(r, dict)],
                           'computed': list(settings.SCHEDULE_YEARS)})
    for row in rows:
        if not isinstance(row, dict) or tuple(row) != ROW_KEYS:
            mismatches.append({'year': row.get('year') if isinstance(row, dict) else None, 'reason': 'ROW_KEYS_INVALID'})
            continue
        try:
            computed = annual_dates(row['year'])
            for key in ROW_KEYS:
                if row[key] != computed[key]:
                    mismatches.append({'year': row['year'], 'field': key, 'frozen': row[key], 'computed': computed[key]})
            mismatches.extend({'year': row['year'], 'reason': reason} for reason in _row_invariants(row))
        except (TypeError, ValueError):   # includes pit_filings.CalendarNotConfigured
            mismatches.append({'year': row.get('year'), 'reason': 'ROW_NOT_VERIFIABLE'})
    return {'ok': not mismatches, 'mismatches': mismatches, 'rows': rows, 'sha256': hashlib.sha256(raw).hexdigest()}


def frozen_row(signal_day=None, *, year=None, path=FROZEN_FILE):
    """The frozen row for a signal day S or a year; ValueError('NOT_A_FROZEN_SIGNAL_DAY') when absent."""
    rows = load_frozen(path)['rows']
    for row in rows:
        if (year is not None and row['year'] == year) or (signal_day is not None and row['S'] == _day(signal_day).isoformat()):
            return dict(row)
    raise ValueError('NOT_A_FROZEN_SIGNAL_DAY')
