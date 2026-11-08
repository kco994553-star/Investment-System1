"""Owner 2026-11-01: CPI-U NSA cap thresholds in 2025 purchasing power.

Pure offline evaluation, no downloader and no guessed CPI constant. The release calendar identifies the latest
announced observation month; its then-available vintage is required (never silently use an older month). A supplied
signal timestamp avoids inventing an intraday cutoff. The 2025 annual average is a fixed numeraire, deliberately not
subject to the historical signal cutoff. Evidence attestations are input claims, not an independent source audit.
"""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, localcontext
from fractions import Fraction
import hashlib
import json
import re
from zoneinfo import ZoneInfo

NOMINAL = 'nominal-v1'
CPI2025 = 'cpi-2025-v1'
C2 = 'C2'
BASE_AMOUNTS = dict(c2_min_usd=Decimal('200000000'), u_a_entry_usd=Decimal('250000000'),
                    u_a_stay_usd=Decimal('200000000'), u_b_min_usd=Decimal('10000000000'))
NY = ZoneInfo('America/New_York')


def _time(value):
    try:
        at = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if at.tzinfo is None or at.utcoffset() is None:
            raise ValueError()
        return at
    except (ValueError, TypeError, AttributeError):
        raise ValueError('CPI_TIMESTAMP_INVALID') from None


def _number(value):
    try:
        if isinstance(value, (bool, float)):
            raise ValueError()
        number = Decimal(value)
        if not number.is_finite() or number <= 0:
            raise ValueError()
        return number
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError('CPI_VALUE_INVALID') from None


def _evidence(row):
    return (isinstance(row, dict) and row.get('evidence_status') in ('VERIFIED', 'SYNTHETIC')
            and all(isinstance(row.get(k), str) and row[k].strip() for k in ('source', 'data_version'))
            and isinstance(row.get('source_sha256'), str) and re.fullmatch('[0-9a-f]{64}', row['source_sha256']))


def _month(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9]{4}-[0-9]{2}', value):
        raise ValueError('CPI_MONTH_INVALID')
    try:
        date.fromisoformat(value + '-01')
    except ValueError:
        raise ValueError('CPI_MONTH_INVALID') from None
    return value


def _digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                                    allow_nan=False, default=str).encode('ascii')).hexdigest()


def resolve(data, signal_day):
    """Threshold context with provenance or BLOCKED + null thresholds; malformed/ambiguous inputs are refused.

    cpi-input/1: CUUR0000SA0 (US city average/all urban/all items/NSA), 1982-84=100. `base` has year=2025,
    aggregation=ANNUAL_AVERAGE, value, vintage_at and evidence. `calendar` has coverage_start/end, evidence and
    releases[{month,released_at}]. `observations` has month,value,vintage_at and evidence for every retained version.
    Evidence: source, source_sha256, data_version, evidence_status VERIFIED|SYNTHETIC|UNVERIFIED.
    `signal_cutoffs`: {S date: timezone-aware actual signal timestamp}. No SEC five-session lag is applied to CPI.
    """
    signal_day = date.fromisoformat(str(signal_day))
    result = dict(version=CPI2025, signal_day=signal_day.isoformat(), status='BLOCKED', reasons=[], thresholds=None)
    def blocked(reason):
        result['reasons'] = [reason]
        return result
    if data is None:
        return blocked('CPI_INPUT_MISSING')
    if (not isinstance(data, dict) or data.get('schema') != 'exp-deciles-cpi-input/1'
            or data.get('series_id') != 'CUUR0000SA0' or data.get('index_base') != '1982-84=100'):
        raise ValueError('CPI_SERIES_INVALID')
    result.update(input_sha256=_digest(data), series_id=data['series_id'], index_base=data['index_base'])
    signal_text = data.get('signal_cutoffs', {}).get(str(signal_day))
    if signal_text is None:
        return blocked('CPI_SIGNAL_TIME_MISSING')
    signal_at = _time(signal_text)
    if signal_at.astimezone(NY).date() != signal_day:
        raise ValueError('CPI_SIGNAL_DATE_MISMATCH')
    result['signal_at'] = signal_text
    base = data.get('base')
    if not isinstance(base, dict) or base.get('year') != 2025 or base.get('aggregation') != 'ANNUAL_AVERAGE':
        return blocked('CPI_BASE_UNAVAILABLE')
    base_value = _number(base.get('value'))
    if _time(base.get('vintage_at')).astimezone(NY).date() < date(2026, 1, 1):
        raise ValueError('CPI_BASE_BEFORE_YEAR_END')
    # Fixed 2025 currency unit; NOT a historical signal input.
    calendar = data.get('calendar')
    if not isinstance(calendar, dict):
        return blocked('CPI_CALENDAR_COVERAGE_MISSING')
    try:
        covered = date.fromisoformat(calendar['coverage_start']) <= signal_day <= date.fromisoformat(calendar['coverage_end'])
    except (KeyError, ValueError, TypeError):
        covered = False
    if not covered:
        return blocked('CPI_CALENDAR_COVERAGE_MISSING')
    if not _evidence(base) or not _evidence(calendar):
        return blocked('CPI_EVIDENCE_UNVERIFIED')
    releases = {}
    if not isinstance(calendar.get('releases'), list) or not isinstance(data.get('observations'), list):
        raise ValueError('CPI_INPUT_SCHEMA_INVALID')
    for row in calendar['releases']:
        month, released = _month(row['month']), _time(row['released_at'])
        if month in releases:
            raise ValueError('CPI_RELEASE_DUPLICATE')
        if released.astimezone(NY).date().strftime('%Y-%m') <= month:
            raise ValueError('CPI_RELEASE_BEFORE_OBSERVATION_END')
        releases[month] = row
    known = [m for m,r in releases.items() if _time(r['released_at']) <= signal_at]
    if not known:
        return blocked('CPI_RELEASE_UNAVAILABLE')
    month = max(known)
    released = releases[month]['released_at']
    result.update(observation_month=month, released_at=released, base_cpi=base_value,
                  base_source=dict(base), calendar_source={k:v for k,v in calendar.items() if k!='releases'})
    candidates, seen = [], set()
    for row in data['observations']:
        obs_month = _month(row['month'])
        at = _time(row['vintage_at'])
        key = (obs_month, at)
        if key in seen:
            raise ValueError('CPI_VINTAGE_DUPLICATE')
        seen.add(key)
        if obs_month not in releases or at < _time(releases[obs_month]['released_at']):
            raise ValueError('CPI_VINTAGE_BEFORE_RELEASE')
        if obs_month == month and at <= signal_at:
            candidates.append((at, row))
    if not candidates:
        return blocked('CPI_VINTAGE_UNAVAILABLE')
    row = max(candidates, key=lambda x:x[0])[1]
    result.update(vintage_at=row['vintage_at'], monthly_source=dict(row))
    if not _evidence(row):
        return blocked('CPI_EVIDENCE_UNVERIFIED')
    monthly = _number(row.get('value'))
    with localcontext() as ctx:
        ctx.prec = 40
        thresholds = {k:v*monthly/base_value for k,v in BASE_AMOUNTS.items()}
    result.update(status='SYNTHETIC' if any(r['evidence_status']=='SYNTHETIC' for r in (base,calendar,row)) else 'VERIFIED',
                  monthly_cpi=monthly, thresholds=thresholds, base_role='FIXED_2025_NUMERAIRE_NOT_SIGNAL_INPUT',
                  comparison='EXACT_RATIONAL_IN_2025_USD', display_decimal_precision=40)
    return result


def comparison_cap(nominal_cap, context):
    """Exact rational for threshold comparison; the recorded/valuation market cap remains nominal USD."""
    if nominal_cap is None:
        return None
    return Fraction(nominal_cap) * Fraction(context['base_cpi']) / Fraction(context['monthly_cpi'])
