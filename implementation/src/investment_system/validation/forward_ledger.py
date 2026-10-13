"""Public, price-free, append-only forward validation ledger (user decision 2026-10-11).

Forward validation starts 2026-10-19 (Mon) on the TARGET v0 portfolio with the
QGV standard v1 strategy. All defaults are v1 UNCALIBRATED. One record per
completed US (NYSE) session date, written only on that session date after the
close, from that run's published ``sec-qg-factors.json`` (Q and G only, no V)
and the public TARGET v0 weights in ``actual-catalog.json``.

Records are immutable: earlier records are carried byte-identically, never
rewritten, deleted or backfilled, and no date before the start is recorded.
Missing inputs give a NOT_AVAILABLE record with reasons, never zeros. A
V-bearing version is a separate, append-only array that stays empty here
(V_REQUIRES_DEVICE_PRICES). Holdout is never used. No price, return or
personal value is ever part of this file.
"""
from __future__ import annotations

from datetime import date, datetime, time, timezone
import hashlib
import json
import math
import re
from zoneinfo import ZoneInfo

from ..contracts.enums import QualityState
from ..contracts.models import FactorObservation
from ..qgv.factors import G_WEIGHTS, Q_WEIGHTS
from ..qgv.portfolio import OFFICIAL_V11_TARGETS
from ..qgv.strategy_preview import recalculate_strategy_preview

FILENAME = 'forward-validation-ledger.json'
KIND = 'FORWARD_VALIDATION_LEDGER'
START_DATE = date(2026, 10, 19)
STRATEGY = 'QGV_STANDARD_V1'
VERSION = 'forward_validation/v1'
V_VERSION = 'forward_validation/v1+dcf_v1_default'
V2_VERSION = 'forward_validation/v2'
V2_STRATEGY = 'QGV_STANDARD_V2'
LEGACY_VERSIONS = (VERSION, V_VERSION)
VERSIONS = LEGACY_VERSIONS + (V2_VERSION,)
CALIBRATION = 'UNCALIBRATED'
HOLDOUT = 'UNCONFIRMED_NOT_USED'
TARGET_ID, TARGET_VERSION = 'TARGET', 'v0'
TOTAL_UNITS = 10000
MAX_BYTES = 2 * 1024 * 1024
LEDGER_STATES = ('NOT_STARTED', 'ACTIVE')
RECORD_STATES = ('RECORDED', 'NOT_AVAILABLE')
STATES = ('LIVE', 'STALE', 'NOT_AVAILABLE')
COVERAGE = ('READY', 'PARTIAL', 'BLOCKED')
REASONS = ('SEC_QG_FACTORS_MISSING', 'SEC_QG_FACTORS_INVALID', 'SEC_QG_FACTORS_NOT_SAME_SESSION',
           'SEC_QG_FACTORS_NOT_AVAILABLE', 'TARGET_CATALOG_MISSING', 'TARGET_CATALOG_INVALID')
V_REASON = 'V_REQUIRES_DEVICE_PRICES'
SOURCES = ('sec-qg-factors.json', 'actual-catalog.json')
V2_SOURCES = ('sec-qgv2.json', 'actual-catalog.json')
V2_REASONS = tuple(x.replace('SEC_QG_FACTORS', 'SEC_QGV2') for x in REASONS)
IDS = tuple(OFFICIAL_V11_TARGETS)
UNITS = {cid: round(weight * TOTAL_UNITS) for cid, weight in OFFICIAL_V11_TARGETS.items()}
AXIS_SIZE = {'Q': len(Q_WEIGHTS), 'G': len(G_WEIGHTS)}
ET = ZoneInfo('America/New_York')
CLOSE = time(16, 0)
# NYSE full-day closures, as published by NYSE. A date past CALENDAR_END is never recorded (fail closed).
NYSE_HOLIDAYS = frozenset(date.fromisoformat(d) for d in (
    '2026-01-01', '2026-01-19', '2026-02-16', '2026-04-03', '2026-05-25', '2026-06-19', '2026-07-03', '2026-09-07',
    '2026-11-26', '2026-12-25',
    '2027-01-01', '2027-01-18', '2027-02-15', '2027-03-26', '2027-05-31', '2027-06-18', '2027-07-05', '2027-09-06',
    '2027-11-25', '2027-12-24',
    '2028-01-17', '2028-02-21', '2028-04-14', '2028-05-29', '2028-06-19', '2028-07-04', '2028-09-04', '2028-11-23',
    '2028-12-25',
))
CALENDAR_END = date(2028, 12, 31)
TOP_KEYS = ('schema_version', 'kind', 'start_date', 'status', 'as_of', 'strategy', 'calibration', 'holdout',
            'price_free', 'target', 'versions', 'version_status')
RECORD_KEYS = ('date', 'version', 'strategy', 'calibration', 'state', 'reason_codes', 'target', 'qg_as_of',
               'qg_screen_state', 'companies', 'source_sha256', 'created_at')


class CalendarNotConfigured(ValueError):
    pass


def _need(condition):
    if not condition:
        raise ValueError('FORWARD_LEDGER_INVALID')


def _clock(value):
    _need(isinstance(value, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})', value) is not None)
    moment = datetime.fromisoformat(value.replace('Z', '+00:00'))
    _need(moment.utcoffset() is not None)
    return moment.astimezone(timezone.utc)


def _day(value):
    _need(isinstance(value, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', value) is not None)
    return date.fromisoformat(value)


def _hash(value, nullable=False):
    _need((nullable and value is None) or isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None)


def _keys(value, expected):
    _need(isinstance(value, dict) and set(value) == set(expected))


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def eastern(moment):
    return moment.astimezone(ET)


def is_session_day(day):
    if day > CALENDAR_END:
        raise CalendarNotConfigured('FORWARD_LEDGER_CALENDAR_NOT_CONFIGURED')
    return day.weekday() < 5 and day not in NYSE_HOLIDAYS


def completed_session(now):
    """The NYSE session date completed on `now`'s own New York calendar day, else None (never an earlier day)."""
    local = eastern(now)
    if not is_session_day(local.date()) or local.time() < CLOSE:
        return None
    return local.date()


def _target(catalog):
    """TARGET v0 weights from the published catalog; reused, never invented."""
    instruments = catalog['instruments']
    _need(catalog.get('target_root_version') == TARGET_VERSION and catalog.get('total_units') == TOTAL_UNITS)
    _need(isinstance(instruments, list) and len(instruments) == len(IDS))
    weights = {}
    for index, (cid, row) in enumerate(zip(IDS, instruments)):
        _need(row['row_index'] == index and row['target_units'] == UNITS[cid])
        weights[cid] = row['target_units']
    _hash(catalog['target_root_sha256'])
    return {'portfolio_id': TARGET_ID, 'version': TARGET_VERSION, 'root_sha256': catalog['target_root_sha256'],
            'total_units': TOTAL_UNITS, 'weights_units': weights}


def company_axes(row):
    """Q and G of one sec-qg-factors row under the QGV standard v1 weights (no V); LIVE->OK, STALE->STALE_DATA."""
    if row['state'] == 'NOT_AVAILABLE':
        return {'state': 'NOT_AVAILABLE', **{axis: {'score': None, 'coverage': 'BLOCKED', 'missing_factor_count': n}
                                             for axis, n in AXIS_SIZE.items()}}
    observations = {}
    for factor, value in row['factors'].items():
        if value['score'] is not None and value['state'] != 'NOT_AVAILABLE':
            quality = QualityState.OK if value['state'] == 'LIVE' else QualityState.STALE_DATA
            observations[factor] = FactorObservation(factor, value['score'], value['score'], quality, 'public-sec-qg-factors')
    result = recalculate_strategy_preview(observations)
    out = {'state': row['state']}
    for axis in ('Q', 'G'):
        a = result.axes[axis]
        out[axis] = {'score': None if a.score is None else round(a.score, 4), 'coverage': a.coverage.value,
                     'missing_factor_count': a.missing_factor_count}
    return out


def build_record(*, now, session, qg_body, catalog_body):
    """One immutable record for `session`. Missing or invalid inputs give NOT_AVAILABLE with reasons."""
    from ..product.public_engine_screens import parse_json as parse_screen, require_public_screen
    from ..public_price_boundary import require_public_catalog
    reasons, target, companies, qg_as_of, qg_state = [], None, None, None, None
    if catalog_body is None:
        reasons.append('TARGET_CATALOG_MISSING')
    else:
        try:
            catalog = parse_screen(catalog_body)
            require_public_catalog('actual-catalog.json', catalog)
            target = _target(catalog)
        except Exception:
            reasons.append('TARGET_CATALOG_INVALID')
    if qg_body is None:
        reasons.append('SEC_QG_FACTORS_MISSING')
    else:
        try:
            screen = require_public_screen('sec-qg-factors.json', parse_screen(qg_body))
        except Exception:
            screen = None
            reasons.append('SEC_QG_FACTORS_INVALID')
        if screen is not None:
            as_of = _clock(screen['as_of'])
            if eastern(as_of).date() != session or as_of > now:
                reasons.append('SEC_QG_FACTORS_NOT_SAME_SESSION')
            elif screen['state'] == 'NOT_AVAILABLE':
                reasons.append('SEC_QG_FACTORS_NOT_AVAILABLE')
            else:
                qg_as_of, qg_state = screen['as_of'], screen['state']
                companies = {cid: company_axes(screen['data']['companies'][cid]) for cid in IDS}
    if reasons:
        companies = qg_as_of = qg_state = None
    sha = lambda body: None if body is None else hashlib.sha256(body).hexdigest()
    return {'date': session.isoformat(), 'version': VERSION, 'strategy': STRATEGY, 'calibration': CALIBRATION,
            'state': 'NOT_AVAILABLE' if reasons else 'RECORDED', 'reason_codes': reasons, 'target': target,
            'qg_as_of': qg_as_of, 'qg_screen_state': qg_state, 'companies': companies,
            'source_sha256': {'sec-qg-factors.json': sha(qg_body), 'actual-catalog.json': sha(catalog_body)},
            'created_at': now.astimezone(timezone.utc).isoformat(timespec='seconds')}


def build_v2_record(*, now, session, qgv2_body, catalog_body):
    """The same-session published QGV v2 Q/G, without V or synthetic reconstruction."""
    from ..universe.sec_qgv2 import require_qgv2, parse_json as parse_qgv2
    # Reuse the immutable TARGET check; QGV v2 has a separate source and failure tokens.
    base = build_record(now=now, session=session, qg_body=None, catalog_body=catalog_body)
    reasons = [r for r in base['reason_codes'] if r.startswith('TARGET_')]
    companies, acquired, screen_state = None, None, None
    if qgv2_body is None:
        reasons.append('SEC_QGV2_MISSING')
    else:
        try:
            screen = require_qgv2(parse_qgv2(qgv2_body))
        except Exception:
            screen = None
            reasons.append('SEC_QGV2_INVALID')
        if screen is not None:
            at = _clock(screen['as_of'])
            if eastern(at).date() != session or at > now:
                reasons.append('SEC_QGV2_NOT_SAME_SESSION')
            else:
                states = [screen['target'][cid]['state'] for cid in IDS]
                screen_state = 'LIVE' if 'LIVE' in states else 'STALE' if 'STALE' in states else None
                if screen_state is None:
                    reasons.append('SEC_QGV2_NOT_AVAILABLE')
                else:
                    acquired = screen['as_of']
                    companies = {}
                    for cid in IDS:
                        row = screen['target'][cid]
                        axes = {}
                        for axis in ('Q', 'G'):
                            a = row['axes'][axis]
                            n = int(a['factors_available'].split('/')[0])
                            score = a['score']
                            axes[axis] = {'score': score, 'coverage': 'BLOCKED' if score is None else 'READY' if n == 5 else 'PARTIAL',
                                          'missing_factor_count': 5 - n}
                        companies[cid] = {'state': row['state'], **axes}
    if reasons:
        companies = acquired = screen_state = None
    return {**base, 'version': V2_VERSION, 'strategy': V2_STRATEGY,
            'state': 'NOT_AVAILABLE' if reasons else 'RECORDED', 'reason_codes': reasons,
            'companies': companies, 'qg_as_of': acquired, 'qg_screen_state': screen_state,
            'source_sha256': {'sec-qgv2.json': None if qgv2_body is None else hashlib.sha256(qgv2_body).hexdigest(),
                              'actual-catalog.json': base['source_sha256']['actual-catalog.json']}}


def new_ledger(now):
    return finalize({'schema_version': 2, 'kind': KIND, 'start_date': START_DATE.isoformat(), 'status': 'NOT_STARTED',
                     'as_of': None, 'strategy': V2_STRATEGY, 'calibration': CALIBRATION, 'holdout': HOLDOUT,
                     'price_free': True, 'target': {'portfolio_id': TARGET_ID, 'version': TARGET_VERSION},
                     'versions': {VERSION: [], V_VERSION: [], V2_VERSION: []}, 'version_status': {}}, now)


def finalize(ledger, now):
    ledger = dict(ledger)
    ledger['schema_version'], ledger['strategy'] = 2, V2_STRATEGY
    ledger['versions'] = dict(ledger['versions'])
    ledger['versions'].setdefault(V2_VERSION, [])
    ledger['as_of'] = now.astimezone(timezone.utc).isoformat(timespec='seconds')
    status = 'ACTIVE' if eastern(now).date() >= START_DATE or ledger['versions'][VERSION] else 'NOT_STARTED'
    ledger['status'] = status
    ledger['version_status'] = {
        VERSION: {'state': status, 'v_included': False, 'reason_codes': []},
        V_VERSION: {'state': 'NOT_AVAILABLE', 'v_included': True, 'reason_codes': [V_REASON]},
        V2_VERSION: {'state': status, 'v_included': False, 'reason_codes': []},
    }
    return ledger


def append(previous, record, now):
    """Previous records unchanged, one new later-dated record appended. Never rewrites or reorders."""
    ledger = json.loads(encode(previous))
    rows = ledger['versions'].setdefault(record['version'], [])
    _need(record['version'] in (VERSION, V2_VERSION))
    _need(not rows or rows[-1]['date'] < record['date'])
    rows.append(record)
    return finalize(ledger, now)


def _axis(value, axis, company_state, axis_size=None):
    _keys(value, ('score', 'coverage', 'missing_factor_count'))
    _need(value['score'] is None or _finite(value['score']) and 0 <= value['score'] <= 100)
    _need(value['coverage'] in COVERAGE and (value['score'] is None) == (value['coverage'] == 'BLOCKED'))
    n = value['missing_factor_count']
    _need(type(n) is int and 0 <= n <= (axis_size or AXIS_SIZE)[axis] and (value['coverage'] != 'READY' or n == 0))
    _need(company_state != 'NOT_AVAILABLE' or value['score'] is None)


def _record(r, previous_day, cut, version=VERSION):
    is_v2 = version == V2_VERSION
    sources = V2_SOURCES if is_v2 else SOURCES
    prefix = 'SEC_QGV2' if is_v2 else 'SEC_QG_FACTORS'
    _keys(r, RECORD_KEYS)
    day = _day(r['date'])
    _need(day >= START_DATE and is_session_day(day) and (previous_day is None or day > previous_day))
    created = _clock(r['created_at'])
    _need(created <= cut and eastern(created).date() == day and eastern(created).time() >= CLOSE)
    _need(r['version'] == version and r['strategy'] == (V2_STRATEGY if is_v2 else STRATEGY) and r['calibration'] == CALIBRATION)
    _need(r['state'] in RECORD_STATES and isinstance(r['reason_codes'], list))
    _need(all(c in (V2_REASONS if is_v2 else REASONS) for c in r['reason_codes']) and len(set(r['reason_codes'])) == len(r['reason_codes']))
    _keys(r['source_sha256'], sources)
    for value in r['source_sha256'].values():
        _hash(value, nullable=True)
    if r['target'] is not None:
        _keys(r['target'], ('portfolio_id', 'version', 'root_sha256', 'total_units', 'weights_units'))
        _need(r['target']['portfolio_id'] == TARGET_ID and r['target']['version'] == TARGET_VERSION)
        _hash(r['target']['root_sha256'])
        _need(type(r['target']['total_units']) is int and r['target']['total_units'] == TOTAL_UNITS)
        weights = r['target']['weights_units']
        _keys(weights, IDS)
        _need(all(type(weights[c]) is int and weights[c] == UNITS[c] for c in IDS))
        _need(r['source_sha256']['actual-catalog.json'] is not None)
    if r['state'] == 'RECORDED':
        _need(r['reason_codes'] == [] and r['target'] is not None and all(r['source_sha256'].values()))
        qg_at = _clock(r['qg_as_of'])
        _need(eastern(qg_at).date() == day and qg_at <= created and r['qg_screen_state'] in ('LIVE', 'STALE'))
        _keys(r['companies'], IDS)
        states = []
        for row in r['companies'].values():
            _keys(row, ('state', 'Q', 'G'))
            _need(row['state'] in STATES)
            states.append(row['state'])
            for axis in ('Q', 'G'):
                _axis(row[axis], axis, row['state'], {'Q': 5, 'G': 5} if is_v2 else None)
        _need(r['qg_screen_state'] == ('LIVE' if 'LIVE' in states else 'STALE' if 'STALE' in states else None))
    else:
        _need(r['reason_codes'] and r['companies'] is None and r['qg_as_of'] is None and r['qg_screen_state'] is None)
        _need(('TARGET_CATALOG_MISSING' in r['reason_codes'] or 'TARGET_CATALOG_INVALID' in r['reason_codes']) == (r['target'] is None))
        _need((prefix + '_MISSING' in r['reason_codes']) == (r['source_sha256'][sources[0]] is None))
        _need(('TARGET_CATALOG_MISSING' in r['reason_codes']) == (r['source_sha256']['actual-catalog.json'] is None))
    return day


def _require(p):
    _keys(p, TOP_KEYS)
    _need(type(p['schema_version']) is int and p['schema_version'] in (1, 2) and p['kind'] == KIND)
    _need(p['start_date'] == START_DATE.isoformat() and p['strategy'] == (STRATEGY if p['schema_version'] == 1 else V2_STRATEGY) and p['calibration'] == CALIBRATION)
    _need(p['holdout'] == HOLDOUT and p['price_free'] is True and p['target'] == {'portfolio_id': TARGET_ID, 'version': TARGET_VERSION})
    cut = _clock(p['as_of'])
    versions = LEGACY_VERSIONS if p['schema_version'] == 1 else VERSIONS
    _keys(p['versions'], versions)
    rows = p['versions'][VERSION]
    _need(isinstance(rows, list) and len(rows) <= 5000)
    # The V-bearing version is append-only too and has no producer yet: it stays empty.
    _need(p['versions'][V_VERSION] == [])
    previous = None
    for version in (v for v in versions if v != V_VERSION):
        values = p['versions'][version]
        _need(isinstance(values, list) and len(values) <= 5000)
        previous = None
        for r in values:
            previous = _record(r, previous, cut, version)
    status = 'ACTIVE' if eastern(cut).date() >= START_DATE or rows else 'NOT_STARTED'
    _need(p['status'] == status and (status == 'ACTIVE' or not rows))
    expected = {
        VERSION: {'state': status, 'v_included': False, 'reason_codes': []},
        V_VERSION: {'state': 'NOT_AVAILABLE', 'v_included': True, 'reason_codes': [V_REASON]},
        V2_VERSION: {'state': status, 'v_included': False, 'reason_codes': []},
    }
    if p['schema_version'] == 1:
        expected.pop(V2_VERSION)
    _need(p['version_status'] == expected)
    _need(previous is None or previous <= eastern(cut).date())
    return p


def require_ledger(payload):
    try:
        return _require(payload)
    except CalendarNotConfigured:
        raise ValueError('FORWARD_LEDGER_INVALID') from None
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError):
        raise ValueError('FORWARD_LEDGER_INVALID') from None


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':'), allow_nan=False)


def require_append_only(previous, current):
    """Every earlier record of every version is carried byte-identically, in order, at the front."""
    if previous is None:
        return current
    try:
        _need(previous['start_date'] == current['start_date'])
        for version in VERSIONS:
            old, new = previous['versions'].get(version, []), current['versions'].get(version, [])
            _need(len(new) >= len(old))
            _need(all(canonical(a) == canonical(b) for a, b in zip(old, new)))
    except (ValueError, TypeError, KeyError):
        raise ValueError('FORWARD_LEDGER_NOT_APPEND_ONLY') from None
    return current


def encode(payload):
    body = (canonical(payload) + '\n').encode('ascii')
    _need(len(body) <= MAX_BYTES)
    return body


def parse_json(body):
    def unique(pairs):
        out = {}
        for key, value in pairs:
            _need(key not in out)
            out[key] = value
        return out

    def invalid(_):
        raise ValueError('FORWARD_LEDGER_INVALID')
    try:
        _need(isinstance(body, (bytes, bytearray)) and len(body) <= MAX_BYTES)
        return json.loads(body.decode('utf-8', errors='strict'), object_pairs_hook=unique, parse_constant=invalid)
    except (ValueError, UnicodeError, RecursionError):
        raise ValueError('FORWARD_LEDGER_INVALID') from None
