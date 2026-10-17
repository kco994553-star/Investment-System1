"""Point-in-time SEC filing facts for the QGV backtest research. RESEARCH ONLY, NOT OPERATIONS.

Owner supplement 2026-10-17 items 3 and 7. Design: docs/backtest/BACKTEST_RESEARCH_PLAN.md (BT-11, BT-12, cases S1-S4) and
BACKTEST_DATA_AUDIT.md (D3, D10, D11). This adapter only CALLS qgv.v2_factors.compute and reads the published NYSE table of
validation.forward_ledger (read-only reuse). It never imports or changes a shared operating selection path (v2_scoring,
qgv_v2.score_universe, universe.sec_universe_*, public pipelines). No network, no file access, no price, no ranking.

Public time of one fact, never earlier than the evidence allows:
- acceptance time of its filing known (FSDS sub.accepted or submissions acceptanceDateTime, joined by accession) and
  consistent with the filing date -> that instant;
- only the filing DATE known -> the open (09:30 New York) of the first NYSE session strictly AFTER that date, so a filing
  dated on a session day is never used on that same day;
- no filing date -> the fact is dropped and counted (MISSING_FILED). Never the period end (unlike providers/sec_vintage.py,
  whose _row_filed falls back to `end`).
A fact is public at decision time t when its public time <= t AND its filing date <= t's New York date; with the second
condition the operating `filed <= cutoff` filter of v2_factors.compute (cutoff = t's New York date) never removes a kept fact.
With date-only facts and t = close of session S (BT-11 A), "public at t" is exactly "filed <= S - 1 calendar day".

Decision time t (BT-11 A) = the actual close of S, returned in UTC: 16:00 New York, 13:00 on an NYSE early-close day (table
NYSE_EARLY_CLOSES 2009-2028: day after Thanksgiving, Christmas Eve and July 3 on Monday-Thursday). Daylight saving comes from
zoneinfo, never a fixed offset (16:00 = 20:00 UTC in summer, 21:00 UTC in winter). Weekends, holidays and unscheduled closures
have no decision time (NoDecisionTime with the reason); so does a session whose closing hour is not confirmed
(EARLY_CLOSE_UNVERIFIED), instead of an assumed 13:00 or 16:00. A filing accepted after a 13:00 close is not public at that
close; it first counts at the next session's close. The table is checked only against the standing rules and a secondary
open-source calendar: unverified against real data, and 2026-2028 is the NYSE-announced schedule.

Each companyfacts row is one filing's report of one period. An amendment (10-K/A) or a later comparative (a prior year
restated inside a later 10-K) is its own row with its own accession and filing date, so it becomes visible only at its own
public time while the original row stays the visible value before that. The companyfacts `frame` tag is hindsight: SEC
attaches it to the LATEST filing of a period (private raw shard 2026-10-17 #6, 57 issuers: on the latest filing in 316,625 of
316,662 tagged multi-filing periods). It is removed from every row and never used to choose a value.

Acceptance clock: submissions `acceptanceDateTime` carries a 'Z' label. The same raw shard is consistent with true UTC
(10-K/10-Q/8-K: peaks at 20-21Z = 16-17 New York, 10 of 8,711 rows at 06-09Z; next-day filing dates start at 21:30Z =
17:30 EDT), but a few rows do not fit. FSDS `accepted` has no zone (EDGAR runs on New York time; not verified here, sec.gov is blocked). The
default reading 'conservative' takes the LATER of "as labeled" and "same wall clock in New York", so an ambiguous label can
only delay a fact, never advance it. 'as_labeled' trusts the label (sensitivity only).

As-filed SIC (BT-12, audit D10): submissions JSON has only the CURRENT `sic` (no per-filing column; checked on the raw
shard). The as-filed SIC comes from FSDS `sub` (adsh = companyfacts accn, cik, sic, form, period, fy, fp, filed yyyymmdd,
accepted). A missing as-filed SIC stays missing: never filled from the current SIC. FSDS `prevrpt` ("later amended") is
hindsight and ignored.

Percentile scores and selection need the historical investable universe (audit D1), which does not exist yet:
cross_section_as_of always answers NOT_AVAILABLE / NEEDS_HISTORICAL_UNIVERSE. V needs prices: not prepared here.
Shares: values pass through unchanged (no split re-adjustment here); a split-ratio fact obeys its own public time like any
other fact. Split handling of per-share histories stays the v2 SPLIT rule; the price-side split cases (plan S7, S8) belong
to the price adapter, which does not exist yet.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
import math
import re
from zoneinfo import ZoneInfo

from ..qgv import v2_factors
from ..validation import forward_ledger

ET = ZoneInfo('America/New_York')
SESSION_OPEN = time(9, 30)
SESSION_CLOSE = time(16, 0)
EARLY_CLOSE_TIME = time(13, 0)
UTC = timezone.utc

# ---------------- NYSE session calendar (research range) ----------------
CALENDAR_START = date(2009, 1, 1)
CALENDAR_END = forward_ledger.CALENDAR_END
# Years covered by the published NYSE table in validation.forward_ledger (reused as is). Earlier years are generated by the
# rules below; the rules reproduce the published years exactly (tests), which is their only check inside the repo.
PUBLISHED_FIRST_YEAR = min(day.year for day in forward_ledger.NYSE_HOLIDAYS)
# Unscheduled full-day closures 2009-2025: Hurricane Sandy (2012-10-29/30), national days of mourning for G. H. W. Bush
# (2018-12-05) and J. Carter (2025-01-09).
SPECIAL_CLOSURES = frozenset({date(2012, 10, 29), date(2012, 10, 30), date(2018, 12, 5), date(2025, 1, 9)})
JUNETEENTH_FIRST_YEAR = 2022


class CalendarNotConfigured(ValueError):
    pass


def _nth_weekday(year, month, weekday, n):
    first = date(year, month, 1)
    return first + timedelta(days=(weekday - first.weekday()) % 7 + 7 * (n - 1))


def _last_weekday(year, month, weekday):
    last = date(year + (month == 12), month % 12 + 1, 1) - timedelta(days=1)
    return last - timedelta(days=(last.weekday() - weekday) % 7)


def _easter(year):
    """Gregorian Easter Sunday (anonymous Gregorian algorithm)."""
    a, (b, c) = year % 19, divmod(year, 100)
    d, e = divmod(b, 4)
    g = (b - (b + 8) // 25 + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return date(year, month, day + 1)


def _observed(day):
    """Saturday holiday -> Friday, Sunday holiday -> Monday."""
    return day - timedelta(days=1) if day.weekday() == 5 else day + timedelta(days=1) if day.weekday() == 6 else day


def rule_holidays(year):
    """NYSE full-day holidays of `year` by the exchange's standing rules (no unscheduled closures). New Year's Day on a
    Saturday is not observed on the preceding Friday (year-end business day); other Saturday holidays move to Friday."""
    days = {_nth_weekday(year, 1, 0, 3), _nth_weekday(year, 2, 0, 3), _easter(year) - timedelta(days=2),
            _last_weekday(year, 5, 0), _observed(date(year, 7, 4)), _nth_weekday(year, 9, 0, 1),
            _nth_weekday(year, 11, 3, 4), _observed(date(year, 12, 25))}
    new_year = date(year, 1, 1)
    if new_year.weekday() == 6:
        days.add(new_year + timedelta(days=1))
    elif new_year.weekday() < 5:
        days.add(new_year)
    if year >= JUNETEENTH_FIRST_YEAR:
        days.add(_observed(date(year, 6, 19)))
    return frozenset(days)


NYSE_FULL_CLOSURES = frozenset(
    {day for year in range(CALENDAR_START.year, PUBLISHED_FIRST_YEAR) for day in rule_holidays(year)}
    | SPECIAL_CLOSURES | forward_ledger.NYSE_HOLIDAYS)


def is_session(day):
    """NYSE full trading session on `day`. Fails closed outside CALENDAR_START..CALENDAR_END."""
    if not isinstance(day, date) or isinstance(day, datetime):
        raise TypeError('SESSION_DAY_MUST_BE_DATE')
    if not CALENDAR_START <= day <= CALENDAR_END:
        raise CalendarNotConfigured('RESEARCH_CALENDAR_NOT_CONFIGURED')
    return day.weekday() < 5 and day not in NYSE_FULL_CLOSURES


def next_session(day):
    """The first NYSE session strictly after `day`."""
    nxt = day + timedelta(days=1)
    while not is_session(nxt):
        nxt += timedelta(days=1)
    return nxt


def session_open(day):
    if not is_session(day):
        raise ValueError('NOT_A_SESSION')
    return datetime.combine(day, SESSION_OPEN, ET)


# ---------------- session close: regular, early close, no close ----------------
# NYSE early closes at 13:00 New York (equities), listed date by date. Source kind: the NYSE published holiday and early-close
# calendar of each year, as known to the author; nyse.com is not reachable from this container, so they were not re-read
# here. Cross-check 2026-10-17: the same 41 dates follow from the XNYS rules of the open-source exchange_calendars package
# (secondary source). Pattern in this range: the day after Thanksgiving; Christmas Eve on Monday-Thursday (a Friday Christmas
# Eve is the observed Christmas holiday); July 3 on Monday-Thursday (a Friday July 3 is the observed Independence Day, and
# July 2 is then a full day). Not checked against real price or trade data.
# Comments: T+1 = day after Thanksgiving, XE = Christmas Eve, J3 = July 3; in brackets, why a candidate day is not listed.
NYSE_EARLY_CLOSES_HISTORICAL = frozenset(date.fromisoformat(d) for d in (
    '2009-11-27', '2009-12-24',                  # T+1, XE Thu        [J3 Fri = observed holiday]
    '2010-11-26',                                # T+1                [J3 Sat; XE Fri = observed holiday]
    '2011-11-25',                                # T+1                [J3 Sun; XE Sat]
    '2012-07-03', '2012-11-23', '2012-12-24',    # J3 Tue, T+1, XE Mon
    '2013-07-03', '2013-11-29', '2013-12-24',    # J3 Wed, T+1, XE Tue
    '2014-07-03', '2014-11-28', '2014-12-24',    # J3 Thu, T+1, XE Wed
    '2015-11-27', '2015-12-24',                  # T+1, XE Thu        [J3 Fri = observed holiday]
    '2016-11-25',                                # T+1                [J3 Sun; XE Sat]
    '2017-07-03', '2017-11-24',                  # J3 Mon, T+1        [XE Sun]
    '2018-07-03', '2018-11-23', '2018-12-24',    # J3 Tue, T+1, XE Mon
    '2019-07-03', '2019-11-29', '2019-12-24',    # J3 Wed, T+1, XE Tue
    '2020-11-27', '2020-12-24',                  # T+1, XE Thu        [J3 Fri = observed holiday]
    '2021-11-26',                                # T+1                [J3 Sat; XE Fri = observed holiday]
    '2022-11-25',                                # T+1                [J3 Sun; XE Sat]
    '2023-07-03', '2023-11-24',                  # J3 Mon, T+1        [XE Sun]
    '2024-07-03', '2024-11-29', '2024-12-24',    # J3 Wed, T+1, XE Tue
    '2025-07-03', '2025-11-28', '2025-12-24',    # J3 Thu, T+1, XE Wed
))
# 2026-2028: the NYSE-announced schedule (subject to change by the exchange), like forward_ledger.NYSE_HOLIDAYS.
NYSE_EARLY_CLOSES_SCHEDULED = frozenset(date.fromisoformat(d) for d in (
    '2026-11-27', '2026-12-24',                  # T+1, XE Thu        [J3 Fri = observed holiday]
    '2027-11-26',                                # T+1                [J3 Sat; XE Fri = observed holiday]
    '2028-07-03', '2028-11-24',                  # J3 Mon, T+1        [XE Sun]
))
NYSE_EARLY_CLOSES = NYSE_EARLY_CLOSES_HISTORICAL | NYSE_EARLY_CLOSES_SCHEDULED
# Sessions whose closing hour is not confirmed by the sources above: no decision time (fail closed), never an assumed 13:00
# or 16:00. 2025-12-26 is a Friday after a Thursday Christmas: the secondary source lists 13:00 closes on such days in 1997
# and 2003, full days in 2008 and 2014, and leaves 2025 to be checked.
EARLY_CLOSE_UNVERIFIED = frozenset({date(2025, 12, 26)})

REGULAR_CLOSE, EARLY_CLOSE = 'REGULAR_CLOSE', 'EARLY_CLOSE'
WEEKEND, HOLIDAY, UNSCHEDULED_CLOSURE = 'WEEKEND', 'HOLIDAY', 'UNSCHEDULED_CLOSURE'
CLOSE_TIME_UNVERIFIED = 'CLOSE_TIME_UNVERIFIED'


class NoDecisionTime(ValueError):
    """No BT-11 A decision instant on that day. `reason`: WEEKEND, HOLIDAY, UNSCHEDULED_CLOSURE or CLOSE_TIME_UNVERIFIED."""

    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class SessionClose:
    day: date
    kind: str                        # REGULAR_CLOSE, EARLY_CLOSE, or the no-close reason
    close_at: datetime | None        # the close in UTC; None when there is no usable close
    new_york_close: time | None      # 16:00 or 13:00 New York wall clock
    daylight_saving: bool | None     # New York on daylight saving time at the close (zoneinfo)
    schedule_based: bool             # 2026-2028: NYSE-announced schedule, subject to change
    reason: str | None = None        # set when close_at is None


def session_close(day):
    """The close of NYSE day `day`, told apart as regular close, early close, weekend, holiday, unscheduled closure or
    unverified close time. The instant comes from the New York wall clock through zoneinfo (no fixed offset), in UTC.
    Fails closed outside CALENDAR_START..CALENDAR_END (CalendarNotConfigured)."""
    trading = is_session(day)
    scheduled = day.year >= PUBLISHED_FIRST_YEAR
    if not trading or day in EARLY_CLOSE_UNVERIFIED:
        reason = (CLOSE_TIME_UNVERIFIED if trading else WEEKEND if day.weekday() >= 5
                  else UNSCHEDULED_CLOSURE if day in SPECIAL_CLOSURES else HOLIDAY)
        return SessionClose(day, reason, None, None, None, scheduled, reason)
    early = day in NYSE_EARLY_CLOSES
    wall = datetime.combine(day, EARLY_CLOSE_TIME if early else SESSION_CLOSE, ET)
    return SessionClose(day, EARLY_CLOSE if early else REGULAR_CLOSE, wall.astimezone(UTC), wall.time(),
                        bool(wall.dst()), scheduled)


def signal_decision_time(day):
    """BT-11 A decision instant: the actual close of the signal session S, in UTC (16:00 New York, 13:00 on an early-close
    day). Scores use only what was public then. Raises NoDecisionTime(reason) when S has no usable close (weekend, holiday,
    unscheduled closure, unverified close time) and CalendarNotConfigured outside the calendar range."""
    close = session_close(day)
    if close.close_at is None:
        raise NoDecisionTime(close.reason)
    return close.close_at


# ---------------- public time of one filing ----------------
ACCEPTED_TIME = 'ACCEPTED_TIME'
FILED_DATE_NEXT_SESSION = 'FILED_DATE_NEXT_SESSION'
ACCEPTANCE_READINGS = ('conservative', 'as_labeled')
# filing date minus acceptance New York date, in days: after-hours acceptances get the next business day (up to 4 days over
# a weekend plus a federal holiday); -1 allows the conservative wall-clock reading of a UTC-labeled evening acceptance.
ACCEPT_FILED_WINDOW = (-1, 4)

MISSING_FILED, INVALID_FILED = 'MISSING_FILED', 'INVALID_FILED'
MISSING_ACCN, MISSING_PERIOD_END, NON_NUMERIC_VALUE, INVALID_ROW = 'MISSING_ACCN', 'MISSING_PERIOD_END', 'NON_NUMERIC_VALUE', 'INVALID_ROW'
CALENDAR_NOT_CONFIGURED = 'CALENDAR_NOT_CONFIGURED'
ACCEPTED_INVALID, ACCEPTED_FILED_INCONSISTENT = 'ACCEPTED_INVALID', 'ACCEPTED_FILED_INCONSISTENT'
FILED_BEFORE_CALENDAR, FRAME_TAG_REMOVED = 'FILED_BEFORE_CALENDAR', 'FRAME_TAG_REMOVED'

_DAY = re.compile(r'(\d{4})-?(\d{2})-?(\d{2})')
_ACCEPTED = re.compile(r'(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}:\d{2})(?:\.(\d{1,6}))?(Z|[+-]\d{2}:\d{2})?')


def _parse_day(value):
    """'YYYY-MM-DD' (companyfacts) or 'YYYYMMDD' (FSDS) -> date; anything else -> None."""
    if type(value) is int:
        value = str(value)
    if not isinstance(value, str):
        return None
    match = _DAY.fullmatch(value.strip())
    if match is None:
        return None
    try:
        return date(*(int(part) for part in match.groups()))
    except ValueError:
        return None


def _aware(moment):
    if not isinstance(moment, datetime) or moment.utcoffset() is None:
        raise ValueError('DECISION_TIME_MUST_BE_TIMEZONE_AWARE')
    return moment


def _reading(reading):
    if reading not in ACCEPTANCE_READINGS:
        raise ValueError('ACCEPTANCE_READING_INVALID')
    return reading


def parse_accepted(value, *, reading='conservative'):
    """Acceptance instant. No zone (FSDS) -> New York wall clock. A zone label -> 'as_labeled' trusts it; 'conservative'
    returns the later of the labeled instant and the same wall clock read in New York. Raises ValueError when invalid."""
    _reading(reading)
    if isinstance(value, datetime):
        wall = value.replace(tzinfo=None)
        labeled = value if value.utcoffset() is not None else None
    elif isinstance(value, str) and (match := _ACCEPTED.fullmatch(value.strip())) is not None:
        day, clock, fraction, zone = match.groups()
        wall = datetime.fromisoformat(f'{day}T{clock}.{(fraction or "0").ljust(6, "0")}')
        labeled = None if zone is None else datetime.fromisoformat(wall.isoformat() + ('+00:00' if zone == 'Z' else zone))
    else:
        raise ValueError(ACCEPTED_INVALID)
    in_new_york = wall.replace(tzinfo=ET)
    if labeled is None:
        return in_new_york
    return labeled if reading == 'as_labeled' else max(labeled, in_new_york)


@dataclass(frozen=True)
class PublicTime:
    at: datetime | None          # None: not usable (see reason)
    basis: str | None            # ACCEPTED_TIME or FILED_DATE_NEXT_SESSION
    filed: date | None
    reason: str | None = None    # drop reason when `at` is None
    notes: tuple = ()            # informational codes (counted, never a drop)


def public_time(filed, accepted=None, *, reading='conservative'):
    """When a filing dated `filed` (optionally accepted at `accepted`) became public. See the module docstring."""
    _reading(reading)
    if filed is None or filed == '':
        return PublicTime(None, None, None, MISSING_FILED)
    day = _parse_day(filed)
    if day is None:
        return PublicTime(None, None, None, INVALID_FILED)
    notes = []
    try:
        if day < CALENDAR_START:
            # Before the calendar: the next session is on or before the first session of CALENDAR_START (conservative).
            notes.append(FILED_BEFORE_CALENDAR)
            fallback = session_open(next_session(CALENDAR_START - timedelta(days=1)))
        else:
            fallback = session_open(next_session(day))
    except CalendarNotConfigured:
        return PublicTime(None, None, day, CALENDAR_NOT_CONFIGURED)
    if accepted is None or accepted == '':
        return PublicTime(fallback, FILED_DATE_NEXT_SESSION, day, None, tuple(notes))
    try:
        at = parse_accepted(accepted, reading=reading)
    except ValueError:
        return PublicTime(fallback, FILED_DATE_NEXT_SESSION, day, None, tuple(notes + [ACCEPTED_INVALID]))
    if ACCEPT_FILED_WINDOW[0] <= (day - at.astimezone(ET).date()).days <= ACCEPT_FILED_WINDOW[1]:
        return PublicTime(at, ACCEPTED_TIME, day, None, tuple(notes))
    return PublicTime(max(at, fallback), FILED_DATE_NEXT_SESSION, day, None, tuple(notes + [ACCEPTED_FILED_INCONSISTENT]))


def _accn_key(value):
    return value.replace('-', '').strip() if isinstance(value, str) and value.strip() else None


# ---------------- companyfacts filter ----------------
@dataclass
class Accounting:
    """Row accounting of one filter call. input_rows == kept + not_yet_public + sum(dropped). One drop reason per row, checked
    in this order: INVALID_ROW, MISSING_ACCN, MISSING_PERIOD_END, NON_NUMERIC_VALUE, MISSING_FILED, INVALID_FILED,
    CALENDAR_NOT_CONFIGURED. `notes` are informational counts of kept rows (never a drop)."""
    input_rows: int = 0
    kept: int = 0
    not_yet_public: int = 0
    dropped: Counter = field(default_factory=Counter)
    notes: Counter = field(default_factory=Counter)

    def balanced(self):
        return self.input_rows == self.kept + self.not_yet_public + sum(self.dropped.values())

    def as_dict(self):
        return {'input_rows': self.input_rows, 'kept': self.kept, 'not_yet_public': self.not_yet_public,
                'dropped': dict(sorted(self.dropped.items())), 'notes': dict(sorted(self.notes.items()))}


@dataclass(frozen=True)
class PitFact:
    taxonomy: str
    concept: str
    unit: str
    accn: str
    form: str
    filed: date
    public_at: datetime
    basis: str
    start: str | None
    end: str
    value: float


@dataclass(frozen=True)
class PitView:
    payload: dict           # companyfacts-shaped, only rows public at decision time, `frame` removed
    facts: tuple            # PitFact rows of `payload`, deterministic order
    accounting: Accounting
    decision_at: datetime


def _finite_number(value):
    return type(value) in (int, float) and math.isfinite(value)


def _row_order(row):
    return (str(row.get('end')), str(row.get('start') or ''), str(row.get('filed')), str(row.get('accn')),
            str(row.get('form') or ''), repr(row.get('val')))


def pit_filter_companyfacts(companyfacts, decision_at, *, acceptance=None, reading='conservative'):
    """The rows of a companyfacts payload that were public at `decision_at` (timezone-aware), plus row accounting.

    `acceptance`: optional {accession: acceptance time} (FSDS sub.accepted or submissions acceptanceDateTime); accessions
    match with or without dashes. Output rows keep their own values and keys (minus `frame`) and are sorted deterministically,
    so the result does not depend on input order. Input is not modified."""
    decision = _aware(decision_at)
    _reading(reading)
    decision_day = decision.astimezone(ET).date()
    accepted_by = {_accn_key(k): v for k, v in (acceptance or {}).items() if _accn_key(k)}
    accounting, facts_out, pit = Accounting(), {}, []
    groups = companyfacts.get('facts') if isinstance(companyfacts, dict) else None
    for taxonomy, concepts in sorted((groups or {}).items()) if isinstance(groups, dict) else ():
        for concept, node in sorted(concepts.items()) if isinstance(concepts, dict) else ():
            units = node.get('units') if isinstance(node, dict) else None
            for unit, rows in sorted(units.items()) if isinstance(units, dict) else ():
                kept_rows = []
                for row in rows if isinstance(rows, list) else ():
                    accounting.input_rows += 1
                    reason = None
                    if not isinstance(row, dict):
                        reason = INVALID_ROW
                    elif _accn_key(row.get('accn')) is None:
                        reason = MISSING_ACCN
                    elif _parse_day(row.get('end')) is None:
                        reason = MISSING_PERIOD_END
                    elif not _finite_number(row.get('val')):
                        reason = NON_NUMERIC_VALUE
                    elif row.get('filed') is None or row.get('filed') == '':
                        reason = MISSING_FILED
                    elif _parse_day(row.get('filed')) is None:
                        reason = INVALID_FILED
                    if reason is not None:
                        accounting.dropped[reason] += 1
                        continue
                    if _parse_day(row['filed']) > decision_day:
                        accounting.not_yet_public += 1
                        continue
                    when = public_time(row['filed'], accepted_by.get(_accn_key(row['accn'])), reading=reading)
                    if when.at is None:
                        accounting.dropped[when.reason] += 1
                        continue
                    if when.at > decision:
                        accounting.not_yet_public += 1
                        continue
                    accounting.kept += 1
                    accounting.notes[when.basis] += 1
                    for note in when.notes:
                        accounting.notes[note] += 1
                    if 'frame' in row:
                        accounting.notes[FRAME_TAG_REMOVED] += 1
                    clean = {key: value for key, value in row.items() if key != 'frame'}
                    kept_rows.append(clean)
                    pit.append(PitFact(taxonomy, concept, unit, str(clean['accn']), str(clean.get('form') or ''), when.filed,
                                       when.at, when.basis, clean.get('start'), clean['end'], clean['val']))
                if kept_rows:
                    target = facts_out.setdefault(taxonomy, {}).setdefault(
                        concept, {key: value for key, value in node.items() if key != 'units'} | {'units': {}})
                    target['units'][unit] = sorted(kept_rows, key=_row_order)
    payload = {key: value for key, value in companyfacts.items() if key != 'facts'} if isinstance(companyfacts, dict) else {}
    payload['facts'] = facts_out
    pit.sort(key=lambda f: (f.taxonomy, f.concept, f.unit, str(f.end), str(f.start or ''), f.public_at, f.filed, f.accn, f.form,
                            repr(f.value)))
    return PitView(payload, tuple(pit), accounting, decision)


# ---------------- latest public value per period ----------------
SUPERSEDED, SAME_TIME_DUPLICATE, AMBIGUOUS_SAME_TIME = 'SUPERSEDED', 'SAME_TIME_DUPLICATE', 'AMBIGUOUS_SAME_TIME'


@dataclass(frozen=True)
class Resolution:
    values: dict    # (taxonomy, concept, unit, start, end) -> PitFact
    counts: dict    # SUPERSEDED rows, SAME_TIME_DUPLICATE rows, AMBIGUOUS_SAME_TIME periods (dropped)


def resolve_as_of(facts):
    """One value per (taxonomy, concept, unit, start, end) among public facts: the latest (public time, filing date) wins
    (an amendment or later comparative replaces the original only once it is public). Same latest time and date with equal
    values -> the smallest accession (deterministic); with different values -> the period is dropped (as v2_factors does
    for one filing date reporting two values), never averaged."""
    groups, values, counts = defaultdict(list), {}, Counter()
    for fact in facts:
        groups[(fact.taxonomy, fact.concept, fact.unit, fact.start, fact.end)].append(fact)
    for key in sorted(groups, key=lambda k: tuple(str(part) for part in k)):
        rows = groups[key]
        latest = max((row.public_at, row.filed) for row in rows)
        top = [row for row in rows if (row.public_at, row.filed) == latest]
        counts[SUPERSEDED] += len(rows) - len(top)
        if len({row.value for row in top}) > 1:
            counts[AMBIGUOUS_SAME_TIME] += 1
            continue
        counts[SAME_TIME_DUPLICATE] += len(top) - 1
        values[key] = min(top, key=lambda row: (row.accn, row.form))
    return Resolution(values, dict(sorted((+counts).items())))


# ---------------- as-filed SIC (FSDS sub) ----------------
SIC_SOURCE = 'FSDS_SUB_AS_FILED'
NO_FSDS_FILING, NO_PUBLIC_FILING_WITH_SIC, SIC_AMBIGUOUS = 'NO_FSDS_FILING', 'NO_PUBLIC_FILING_WITH_SIC', 'SIC_AMBIGUOUS'
NOT_YET_PUBLIC, SIC_MISSING_ON_FILING = 'NOT_YET_PUBLIC', 'SIC_MISSING_ON_FILING'


@dataclass(frozen=True)
class SicAsOf:
    sic: str | None             # 4 digits, or None (never the current SIC)
    adsh: str | None            # accession of the filing that stated it
    public_at: datetime | None
    reason: str | None          # None when found
    source: str = SIC_SOURCE


def _cik_key(value):
    text = str(value).strip() if type(value) in (int, str) else ''
    if not text.isdigit():
        return None
    return text.lstrip('0') or None


def _sic(value):
    text = str(value).strip() if type(value) in (int, str) else ''
    if not text.isdigit() or len(text) > 4:
        return None
    text = text.zfill(4)
    return None if text == '0000' else text


def as_filed_sic(sub_rows, cik, decision_at, *, reading='conservative'):
    """(SicAsOf, counts): the SIC stated on the latest FSDS `sub` filing of `cik` public at `decision_at`.

    Rows: FSDS sub dicts (adsh, cik, sic, filed 'YYYYMMDD', accepted 'YYYY-MM-DD HH:MM:SS.f' New York, form, ...). A filing
    with a blank or 0000 SIC is skipped (counted); `prevrpt` is hindsight and ignored. No public filing with a SIC -> sic None
    with a reason; this function has no current-SIC input and never substitutes one."""
    decision = _aware(decision_at)
    want, counts, candidates = _cik_key(cik), Counter(), []
    decision_day = decision.astimezone(ET).date()
    for row in sub_rows:
        if not isinstance(row, dict) or want is None or _cik_key(row.get('cik')) != want:
            continue
        counts['ROWS'] += 1
        when = public_time(row.get('filed'), row.get('accepted'), reading=reading)
        if when.at is None:
            counts[when.reason] += 1
            continue
        if when.at > decision or when.filed > decision_day:
            counts[NOT_YET_PUBLIC] += 1
            continue
        sic = _sic(row.get('sic'))
        if sic is None:
            counts[SIC_MISSING_ON_FILING] += 1
            continue
        candidates.append((when.at, when.filed, str(row.get('adsh') or ''), sic))
    if not counts['ROWS']:
        return SicAsOf(None, None, None, NO_FSDS_FILING), dict(counts)
    if not candidates:
        return SicAsOf(None, None, None, NO_PUBLIC_FILING_WITH_SIC), dict(sorted(counts.items()))
    latest = max((c[0], c[1]) for c in candidates)
    top = [c for c in candidates if (c[0], c[1]) == latest]
    if len({c[3] for c in top}) > 1:
        return SicAsOf(None, None, latest[0], SIC_AMBIGUOUS), dict(sorted(counts.items()))
    best = min(top, key=lambda c: c[2])
    return SicAsOf(best[3], best[2], best[0], None), dict(sorted(counts.items()))


# ---------------- price-free per-company Q·G raw metrics ----------------
NEEDS_HISTORICAL_UNIVERSE = 'NEEDS_HISTORICAL_UNIVERSE'


def qg_raw_metrics_as_of(companyfacts, decision_at, *, sic_as_of, acceptance=None, reading='conservative'):
    """Per-company raw Q·G metrics from the facts public at `decision_at`, via v2_factors.compute (called, not changed).

    `sic_as_of` must be a SicAsOf (as_filed_sic): a bare SIC string is refused so a current SIC cannot slip in. Missing
    as-filed SIC -> NOT_AVAILABLE (the profile depends on it). No universe, no percentile, no V, no price."""
    if not isinstance(sic_as_of, SicAsOf) or sic_as_of.source != SIC_SOURCE:
        raise TypeError('SIC_MUST_BE_AS_FILED')
    view = pit_filter_companyfacts(companyfacts, decision_at, acceptance=acceptance, reading=reading)
    out = {'decision_at': view.decision_at.isoformat(), 'calc_version': v2_factors.CALC_VERSION,
           'sic': {'value': sic_as_of.sic, 'adsh': sic_as_of.adsh, 'source': sic_as_of.source, 'reason': sic_as_of.reason},
           'accounting': view.accounting.as_dict(), 'universe': None, 'percentile': None}
    if sic_as_of.sic is None:
        return out | {'status': 'NOT_AVAILABLE', 'reason_codes': ['SIC_AS_FILED_' + str(sic_as_of.reason)], 'profile': None,
                      'fiscal_year_end': None, 'currency': None, 'metrics': None}
    profile, fy_end, currency, metrics, _v_inputs = v2_factors.compute(
        view.payload, sic=sic_as_of.sic, cutoff=view.decision_at.astimezone(ET).date())
    status = 'OK' if fy_end is not None else 'NOT_AVAILABLE'
    return out | {'status': status, 'reason_codes': [] if fy_end is not None else ['NO_PUBLIC_ANNUAL_FACTS'], 'profile': profile,
                  'fiscal_year_end': fy_end, 'currency': currency, 'metrics': metrics}


def cross_section_as_of(rows, decision_at):
    """Percentile scores and top-N selection at `decision_at`: NOT PROVIDED. They need the investable universe as it was at
    that time (audit D1), which the repository does not have; ranking against today's Universe504 would be survivorship
    look-ahead. Always NOT_AVAILABLE, whatever `rows` holds."""
    return {'status': 'NOT_AVAILABLE', 'reason_codes': [NEEDS_HISTORICAL_UNIVERSE],
            'decision_at': _aware(decision_at).isoformat(), 'input_rows': len(rows), 'scores': None, 'selection': None}
