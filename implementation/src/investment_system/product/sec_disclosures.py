"""Public `sec-disclosures.json`: SEC 8-K current-report metadata for the US TARGET companies.

Display principle (queue 2.2 d): disclosures are labelled '공시·확정' (channel DISCLOSURE),
later news '뉴스·신호'. Only title, link, time, company and classification are stored; no
filing or exhibit body text, no prices, no personal data. Same accession folds to one row;
an 8-K/A joins its original 8-K (same company and event date) as a REPEAT of that group.
Neither disclosures nor news change any score (`score_effect: NONE`).

Pure functions: no network, credentials or clock. The tool `tools/sec_disclosures.py`
collects and carries the previous Pages copy forward (rolling window).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import re

from ..markets.us import US_LISTINGS
from ..providers.sec_8k_disclosures import (ARCHIVE_URL, CLASSIFICATIONS, FORMS, ITEMS, TITLE_MAX, classify_report, quarterly_earnings_title,
              index_url)

FILENAME = 'sec-disclosures.json'
KIND = 'SEC_DISCLOSURES'
WINDOW_DAYS = 90
STALE_AFTER = timedelta(hours=48)  # daily cadence plus one missed run
MAX_BYTES = 2 * 1024 * 1024  # Pages guard and device reader limit
SIZE_BUDGET = 1_900_000
MAX_EVENTS = 3000
STATES = ('LIVE', 'STALE', 'NOT_AVAILABLE')
TOP_REASONS = ('STALE_INPUT', 'NO_ELIGIBLE_INPUT')
COMPANY_REASONS = ('NOT_COLLECTED',)
EXHIBIT_REASONS = ('NOT_COLLECTED', 'INDEX_UNAVAILABLE', 'INDEX_INVALID', 'NO_EXHIBIT_99_1',
                   'EXHIBIT_LINK_INVALID', 'EXHIBIT_TITLE_INVALID')
# Retried on the next run; the others are definitive for that accession.
RETRY_EXHIBIT_REASONS = ('NOT_COLLECTED', 'INDEX_UNAVAILABLE')
TOP_KEYS = ('schema_version', 'kind', 'as_of', 'state', 'reason_codes', 'freshness_basis', 'stale_after_seconds',
            'window_days', 'channel', 'score_effect', 'companies', 'events')
COMPANY_KEYS = ('state', 'acquired_at', 'reason_code')
EVENT_KEYS = ('company_id', 'accession', 'form', 'filing_date', 'event_date', 'accepted_at', 'items',
              'classification', 'link', 'group_id', 'occurrence', 'first_seen_at', 'exhibit_99_1')
_INSTANT = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\+00:00')
_DAY = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}')
_ACCESSION = re.compile(r'[0-9]{10}-[0-9]{2}-[0-9]{6}')
_DOCUMENT = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]{0,120}\.(?:htm|html|txt|pdf|xml|jpg|gif)', re.I)


def _need(condition):
    if not condition:
        raise ValueError('SEC_DISCLOSURES_INVALID')


def instant(value: datetime) -> str:
    """UTC, whole seconds, '+00:00': string order equals time order."""
    _need(isinstance(value, datetime) and value.utcoffset() is not None)
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def _clock(value):
    _need(isinstance(value, str) and _INSTANT.fullmatch(value) is not None)
    return datetime.fromisoformat(value)


def _date(value):
    _need(isinstance(value, str) and _DAY.fullmatch(value) is not None)
    return datetime.fromisoformat(value + 'T00:00:00+00:00').date()


def _fresh(acquired, as_of):
    return 'STALE' if as_of - acquired > STALE_AFTER else 'LIVE'


def assign_groups(events):
    """Set group_id/occurrence in place (mirrors sec-disclosures.js groups()).

    An original 8-K starts its own group (NEW). An 8-K/A joins the single original 8-K of the
    same company with the same event date accepted no later than it; otherwise it keeps its own
    group. Every 8-K/A is a REPEAT (update of an earlier report).
    """
    originals = {}
    for e in events:
        if e['form'] in ('8-K', '6-K') and e['event_date'] is not None:
            originals.setdefault((e['company_id'], e['event_date'], e['form']), []).append(e)
    for e in events:
        own = e['company_id'] + ':' + e['accession']
        if e['form'] in ('8-K', '6-K'):
            e['group_id'], e['occurrence'] = own, 'NEW'
            continue
        matches = [o for o in originals.get((e['company_id'], e['event_date'], e['form'].removesuffix('/A')), []) if o['accepted_at'] <= e['accepted_at']] \
            if e['event_date'] is not None else []
        e['group_id'] = matches[0]['company_id'] + ':' + matches[0]['accession'] if len(matches) == 1 else own
        e['occurrence'] = 'REPEAT'
    return events


def _order(events):
    return sorted(events, key=lambda e: (e['accepted_at'], e['accession']), reverse=True)


def pending_exhibits(previous, collected):
    """(company_id, accession) whose Exhibit 99.1 lookup is due this run: new accessions and retryable reasons."""
    known = {}
    if previous is not None:
        for e in previous['events']:
            known[e['accession']] = e['exhibit_99_1']
    due = []
    for cid in sorted(collected):
        for row in sorted(collected[cid]['rows'], key=lambda r: (r['accepted_at'], r['accession']), reverse=True):
            exhibit = known.get(row['accession'])
            if exhibit is None or exhibit['state'] == 'NOT_AVAILABLE' and exhibit['reason_code'] in RETRY_EXHIBIT_REASONS:
                due.append((cid, row['accession']))
    return due


def merge(previous, collected, *, as_of, exhibits=None):
    """Build the next public payload.

    previous: validated payload or None. collected: {company_id: {'acquired_at': datetime, 'rows': [...]}} for
    companies collected this run (rows from providers.sec_8k_disclosures.current_reports). exhibits:
    {accession: {'title','url'} | reason_code} looked up this run. Companies not collected keep their
    previous rows and acquisition time. Rows older than the rolling window are dropped.
    """
    exhibits = exhibits or {}
    as_of = datetime.fromisoformat(instant(as_of))
    cutoff = (as_of - timedelta(days=WINDOW_DAYS)).date().isoformat()
    previous_events = {e['accession']: e for e in previous['events']} if previous is not None else {}
    companies, events = {}, []
    for cid in sorted(US_LISTINGS):
        if cid in collected:
            acquired = instant(collected[cid]['acquired_at'])
            _need(_clock(acquired) <= as_of)
            rows = []
            for row in collected[cid]['rows']:
                _need(set(row) == {'accession', 'form', 'filing_date', 'event_date', 'accepted_at', 'items'})
                old = previous_events.get(row['accession'])
                if old is not None and old['company_id'] != cid:
                    continue
                accepted = instant(datetime.fromisoformat(row['accepted_at']))
                found = exhibits.get(row['accession'])
                if isinstance(found, dict):
                    exhibit = {'state': 'AVAILABLE', 'title': found['title'], 'url': found['url'], 'released_at': accepted}
                elif isinstance(found, str):
                    exhibit = {'state': 'NOT_AVAILABLE', 'reason_code': found}
                elif old is not None:
                    exhibit = dict(old['exhibit_99_1'])
                else:
                    exhibit = {'state': 'NOT_AVAILABLE', 'reason_code': 'NOT_COLLECTED'}
                rows.append({'company_id': cid, 'accession': row['accession'], 'form': row['form'],
                             'filing_date': row['filing_date'], 'event_date': row['event_date'], 'accepted_at': accepted,
                             'items': list(row['items']), 'classification': classify_report(row['form'], row['items']),
                             'link': index_url(cid, row['accession']), 'group_id': None, 'occurrence': None,
                             'first_seen_at': old['first_seen_at'] if old is not None else instant(as_of),
                             'exhibit_99_1': exhibit})
        elif previous is not None and previous['companies'][cid]['acquired_at'] is not None:
            acquired = previous['companies'][cid]['acquired_at']
            rows = [dict(e, exhibit_99_1=dict(e['exhibit_99_1']), items=list(e['items']))
                    for e in previous['events'] if e['company_id'] == cid]
        else:
            companies[cid] = {'state': 'NOT_AVAILABLE', 'acquired_at': None, 'reason_code': 'NOT_COLLECTED'}
            continue
        companies[cid] = {'state': _fresh(_clock(acquired), as_of), 'acquired_at': acquired, 'reason_code': None}
        events.extend(r for r in rows if r['filing_date'] >= cutoff)
    events = _order(assign_groups(events))[:MAX_EVENTS]
    events = _order(assign_groups(events))
    states = [c['state'] for c in companies.values()]
    state = 'LIVE' if 'LIVE' in states else 'STALE' if 'STALE' in states else 'NOT_AVAILABLE'
    payload = {'schema_version': 1, 'kind': KIND, 'as_of': instant(as_of), 'state': state,
               'reason_codes': [] if state == 'LIVE' else ['STALE_INPUT'] if state == 'STALE' else ['NO_ELIGIBLE_INPUT'],
               'freshness_basis': 'SOURCE_ACQUISITION', 'stale_after_seconds': int(STALE_AFTER.total_seconds()),
               'window_days': WINDOW_DAYS, 'channel': 'DISCLOSURE', 'score_effect': 'NONE',
               'companies': companies, 'events': events}
    while len(encode(payload)) > SIZE_BUDGET and payload['events']:
        # Withhold the oldest rows explicitly instead of truncating fields.
        payload['events'] = _order(assign_groups(payload['events'][:-1]))
    return require_sec_disclosures(payload)


def _exhibit(e):
    x = e['exhibit_99_1']
    _need(isinstance(x, dict))
    if x.get('state') == 'AVAILABLE':
        _need(set(x) == {'state', 'title', 'url', 'released_at'} and x['released_at'] == e['accepted_at'])
        title = x['title']
        # Same rule as sec-disclosures.js: one line, no markup, single ASCII spaces, no padding.
        _need(isinstance(title, str) and 0 < len(title) <= TITLE_MAX and not any(ord(ch) < 32 or ch in '<>' for ch in title)
              and not title.startswith(' ') and not title.endswith(' ') and '  ' not in title)
        prefix = ARCHIVE_URL.format(cik=int(US_LISTINGS[e['company_id']]['cik']), folder=e['accession'].replace('-', ''), name='')
        _need(isinstance(x['url'], str) and x['url'].startswith(prefix) and _DOCUMENT.fullmatch(x['url'][len(prefix):]) is not None)
    else:
        _need(set(x) == {'state', 'reason_code'} and x['state'] == 'NOT_AVAILABLE' and x['reason_code'] in EXHIBIT_REASONS)


def _require(p):
    _need(isinstance(p, dict) and set(p) == set(TOP_KEYS))
    _need(type(p['schema_version']) is int and p['schema_version'] == 1 and p['kind'] == KIND)
    cut = _clock(p['as_of'])
    _need(p['freshness_basis'] == 'SOURCE_ACQUISITION' and p['channel'] == 'DISCLOSURE' and p['score_effect'] == 'NONE')
    _need(type(p['stale_after_seconds']) is int and p['stale_after_seconds'] == int(STALE_AFTER.total_seconds()))
    _need(type(p['window_days']) is int and p['window_days'] == WINDOW_DAYS)
    companies = p['companies']
    _need(isinstance(companies, dict) and set(companies) == set(US_LISTINGS))
    acquired = {}
    for cid, c in companies.items():
        _need(isinstance(c, dict) and set(c) == set(COMPANY_KEYS))
        if c['acquired_at'] is None:
            _need(c['state'] == 'NOT_AVAILABLE' and c['reason_code'] in COMPANY_REASONS)
        else:
            at = _clock(c['acquired_at'])
            _need(at <= cut and c['reason_code'] is None and c['state'] == _fresh(at, cut))
            acquired[cid] = c['acquired_at']
    states = [c['state'] for c in companies.values()]
    state = 'LIVE' if 'LIVE' in states else 'STALE' if 'STALE' in states else 'NOT_AVAILABLE'
    _need(p['state'] == state)
    _need(p['reason_codes'] == ([] if state == 'LIVE' else ['STALE_INPUT'] if state == 'STALE' else ['NO_ELIGIBLE_INPUT']))
    events = p['events']
    _need(isinstance(events, list) and len(events) <= MAX_EVENTS)
    cutoff = (cut - timedelta(days=WINDOW_DAYS)).date()
    seen = set()
    for e in events:
        _need(isinstance(e, dict) and set(e) == set(EVENT_KEYS))
        _need(e['company_id'] in acquired and isinstance(e['accession'], str) and _ACCESSION.fullmatch(e['accession']) is not None)
        _need(e['accession'] not in seen and e['form'] in FORMS)
        seen.add(e['accession'])
        filed = _date(e['filing_date'])
        accepted = _clock(e['accepted_at'])
        _need(cutoff <= filed <= cut.date() and accepted <= _clock(acquired[e['company_id']]))
        # EDGAR filing date is the Eastern business day: at most one UTC day before acceptance, a few after.
        _need(-1 <= (filed - accepted.date()).days <= 5)
        _need(e['event_date'] is None or _date(e['event_date']) <= filed)
        items = e['items']
        _need(isinstance(items, list) and len(items) <= len(ITEMS) and all(isinstance(i, str) and i in ITEMS for i in items)
              and items == sorted(set(items)))
        _need(e['classification'] in CLASSIFICATIONS and e['classification'] == classify_report(e['form'], items))
        _need(e['link'] == index_url(e['company_id'], e['accession']))
        seen_at = _clock(e['first_seen_at'])
        _need(accepted <= seen_at <= cut)
        _exhibit(e)
        if e['form'] in ('6-K', '6-K/A'):
            _need(e['company_id'] == 'asml' and items == [] and e['exhibit_99_1']['state'] == 'AVAILABLE'
                  and quarterly_earnings_title(e['exhibit_99_1']['title']))
    _need(events == _order(events))
    expected = assign_groups([dict(e) for e in events])
    _need(all(a['group_id'] == b['group_id'] and a['occurrence'] == b['occurrence'] for a, b in zip(events, expected)))
    return p


def require_sec_disclosures(payload):
    try:
        return _require(payload)
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError):
        raise ValueError('SEC_DISCLOSURES_INVALID') from None


def encode(payload):
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode('utf-8')


def parse_json(body):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError('SEC_DISCLOSURES_INVALID')
            out[key] = value
        return out

    def constant(_value):
        raise ValueError('SEC_DISCLOSURES_INVALID')
    try:
        if not isinstance(body, bytes) or len(body) > MAX_BYTES:
            raise ValueError
        return json.loads(body.decode('utf-8'), object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, UnicodeError, RecursionError):
        raise ValueError('SEC_DISCLOSURES_INVALID') from None
