"""Public price-free OpenDART projections: ``dart-disclosures.json`` and ``dart-financials.json``.

Disclosures mirror the SEC 8-K ``sec-disclosures.json`` record shape (channel
DISCLOSURE '공시·확정', ``score_effect: NONE``, company_id / filing_date /
link / classification / group_id / occurrence / first_seen_at) with
``source: 'DART'``. Only title (OpenDART report name), link, date and a fixed
classification are stored -- never body text, filer names, prices or scores.
OpenDART's list gives a KST receipt date only, so ``accepted_at`` is null and
``time_precision`` is ``DATE_KST``. Classification is a pure function of
(title, publication type) so validators recompute it:

- '(잠정)실적' + '공정공시' in the title -> ``RESULTS`` (same class as SEC 8-K Item 2.02)
- type A -> ``PERIODIC`` (사업·반기·분기보고서), B -> ``MAJOR_EVENT`` (주요사항보고서),
  I with '공정공시' -> ``FAIR_DISCLOSURE``, other I -> ``EXCHANGE``, anything else -> ``OTHER``.

Grouping mirrors the 8-K rule: an original report starts its own group (NEW);
a correction ([기재정정] etc.) joins the single original of the same title
family filed no later, else its own group, and is always REPEAT.

Financials are the reported KRW inputs of the latest 사업보고서 (fiscal year,
used for Q·G exactly as the US 10-K path) and of the latest newer interim
report (year to date, display only), CFS preferred and OFS fallback labelled.
Q·G factor scores reuse ``qgv.raw_map.map_raw`` unchanged; a missing input
stays null (NOT_AVAILABLE), never 0. No currency conversion, no price.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import json
import math
import re

DISCLOSURES_FILENAME = 'dart-disclosures.json'
FINANCIALS_FILENAME = 'dart-financials.json'
FILENAMES = (DISCLOSURES_FILENAME, FINANCIALS_FILENAME)
DISCLOSURES_KIND = 'DART_DISCLOSURES'
FINANCIALS_KIND = 'DART_FINANCIALS'
MAX_BYTES = 1024 * 1024
WINDOW_DAYS = 90
STALE_AFTER = timedelta(hours=48)  # daily cadence plus one missed run (same as SEC 8-K)
MAX_EVENTS = 300
SOURCE = 'DART'
LINK_PREFIX = 'https://dart.fss.or.kr/dsaf001/main.do?rcpNo='
KST = timezone(timedelta(hours=9))
COMPANIES = {'hanmi': '042700'}
STATES = ('LIVE', 'STALE', 'NOT_AVAILABLE')
CLASSIFICATIONS = ('RESULTS', 'PERIODIC', 'MAJOR_EVENT', 'FAIR_DISCLOSURE', 'EXCHANGE', 'OTHER')
REPORT_TYPES = ('A', 'B', 'I')
EVENT_KEYS = ('company_id', 'source', 'rcept_no', 'report_type', 'title', 'filing_date', 'accepted_at', 'time_precision',
              'classification', 'amended', 'link', 'group_id', 'occurrence', 'first_seen_at')
DISCLOSURE_TOP_KEYS = ('schema_version', 'kind', 'source', 'as_of', 'state', 'reason_codes', 'freshness_basis',
                       'stale_after_seconds', 'window_days', 'channel', 'score_effect', 'collection', 'companies', 'events')
COMPANY_KEYS = ('state', 'acquired_at', 'reason_code', 'stock_code', 'corp_code', 'corp_code_basis', 'truncated')
FIN_TOP_KEYS = ('schema_version', 'kind', 'source', 'as_of', 'state', 'reason_codes', 'freshness_basis', 'stale_after_seconds',
                'role', 'currency', 'method_status', 'availability_basis', 'companies')
FIN_COMPANY_KEYS = ('stock_code', 'corp_code', 'state', 'reason_codes', 'acquired_at', 'annual', 'latest_interim', 'qg')
REPORT_KEYS = ('state', 'reason_codes', 'rcept_no', 'report_name', 'bsns_year', 'reprt_code', 'period', 'fs_div', 'fs_label',
               'filed_at', 'basis', 'inputs', 'concepts', 'missing', 'source_sha256')
INPUT_NAMES = ('revenue', 'revenue_prev', 'operating_income', 'operating_income_prev', 'net_income', 'eps', 'eps_prev',
               'operating_cash_flow', 'capex', 'cash_and_equivalents', 'equity', 'total_debt', 'shares')
MISSING_REASONS = ('MISSING', 'AMBIGUOUS', 'UNPARSEABLE', 'NOT_IN_INTERIM_SCOPE', 'NOT_COLLECTED')
PERIODS = {'11011': 'ANNUAL', '11012': 'HALF', '11013': 'Q1', '11014': 'Q3'}
TOP_REASONS = ('STALE_INPUT', 'NO_ELIGIBLE_INPUT')
REASONS = (
    'NOT_COLLECTED', 'DART_API_KEY_MISSING', 'DART_API_KEY_INVALID_FORMAT', 'DART_CALL_BUDGET_EXCEEDED',
    'DART_KEY_NOT_REGISTERED', 'DART_KEY_DISABLED', 'DART_IP_NOT_ALLOWED', 'DART_NO_DATA', 'DART_FILE_NOT_FOUND',
    'DART_LIMIT_EXCEEDED', 'DART_COMPANY_LIMIT_EXCEEDED', 'DART_INVALID_FIELD', 'DART_INVALID_ACCESS', 'DART_MAINTENANCE',
    'DART_UNDEFINED_ERROR', 'DART_KEY_EXPIRED', 'DART_UNKNOWN_STATUS', 'DART_TRANSPORT_FAILED', 'DART_REDIRECT_REJECTED',
    'DART_HTTP_ERROR', 'DART_RESPONSE_TOO_LARGE', 'DART_JSON_INVALID', 'DART_ZIP_INVALID', 'DART_CONFIG_INVALID',
    'DART_IDENTITY_MISMATCH', 'DART_LIST_INVALID', 'DART_LIST_TRUNCATED', 'DART_FINANCIALS_INVALID',
    'CORP_CODE_UNCONFIRMED', 'NO_PERIODIC_REPORT', 'NO_NEWER_INTERIM_REPORT', 'SEPARATE_STATEMENTS_FALLBACK',
    'SHARES_NOT_AVAILABLE', 'QG_INPUTS_NOT_AVAILABLE', 'RECORDS_DROPPED_INVALID', 'STALE_INPUT',
)
_TAG = r'(?:\[[^\]]{1,20}\]\s*)'
_INSTANT = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\+00:00')


class DartPublicError(ValueError):
    pass


def _need(condition):
    if not condition:
        raise DartPublicError('DART_PUBLIC_INVALID')


def instant(moment):
    """UTC, whole seconds, '+00:00' (same format as sec-disclosures.json)."""
    _need(isinstance(moment, datetime) and moment.utcoffset() is not None)
    return moment.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def _clock(value):
    _need(type(value) is str and _INSTANT.fullmatch(value) is not None)
    return datetime.fromisoformat(value)


def _day(value):
    _need(type(value) is str and re.fullmatch(r'\d{4}-\d{2}-\d{2}', value) is not None)
    return date.fromisoformat(value)


def _hash(value):
    return type(value) is str and re.fullmatch(r'[0-9a-f]{64}', value) is not None


def fresh(acquired, as_of):
    return 'STALE' if as_of - acquired > STALE_AFTER else 'LIVE'


def _top(states):
    state = 'LIVE' if 'LIVE' in states else 'STALE' if 'STALE' in states else 'NOT_AVAILABLE'
    return state, [] if state == 'LIVE' else ['STALE_INPUT'] if state == 'STALE' else ['NO_ELIGIBLE_INPUT']


def _reasons(value):
    _need(type(value) is list and len(value) <= 8 and len(set(value)) == len(value) and all(x in REASONS for x in value))
    return value


def valid_title(value):
    return (type(value) is str and 0 < len(value) <= 200 and value == re.sub(r'\s+', ' ', value).strip()
            and not any(ord(ch) < 32 or ch in '<>' for ch in value))


def title_family(title):
    """Bracket tags such as [기재정정] and a trailing (YYYY.MM) period removed."""
    key = re.sub(r'^' + _TAG + '+', '', title)
    key = re.sub(r'\s*\(\d{4}\.\d{2}\)$', '', key)
    return re.sub(r'\s+', ' ', key).strip() or title


def is_amended(title):
    """A leading bracket tag containing '정정' ([기재정정], [첨부정정], ...)."""
    return re.match(r'^' + _TAG + r'*\[[^\]]{0,18}정정[^\]]{0,18}\]', title) is not None


def classify(title, report_type):
    if re.search(r'\(잠정\)\s*실적', title) and '공정공시' in title:
        return 'RESULTS'
    return {'A': 'PERIODIC', 'B': 'MAJOR_EVENT'}.get(report_type) or (
        ('FAIR_DISCLOSURE' if '공정공시' in title else 'EXCHANGE') if report_type == 'I' else 'OTHER')


def link(rcept_no):
    return LINK_PREFIX + rcept_no


def order(events):
    return sorted(events, key=lambda e: (e['filing_date'], e['rcept_no']), reverse=True)


def assign_groups(events):
    """Set group_id/occurrence in place (mirrors dart-disclosures.js groups())."""
    originals = {}
    for e in events:
        if not e['amended']:
            originals.setdefault((e['company_id'], title_family(e['title'])), []).append(e)
    for e in events:
        own = e['company_id'] + ':' + e['rcept_no']
        if not e['amended']:
            e['group_id'], e['occurrence'] = own, 'NEW'
            continue
        matches = [o for o in originals.get((e['company_id'], title_family(e['title'])), [])
                   if (o['filing_date'], o['rcept_no']) <= (e['filing_date'], e['rcept_no'])]
        e['group_id'] = matches[0]['company_id'] + ':' + matches[0]['rcept_no'] if len(matches) == 1 else own
        e['occurrence'] = 'REPEAT'
    return events


def build_events(company_id, rows, *, as_of, previous_events=()):
    """rows: [{'rcept_no','rcept_dt'(YYYYMMDD),'title','report_type'}] -> (events, dropped). Window-trimmed, grouped."""
    as_of = _clock(instant(as_of))
    cutoff = (as_of.astimezone(KST).date() - timedelta(days=WINDOW_DAYS)).isoformat()
    seen_before = {e['rcept_no']: e['first_seen_at'] for e in previous_events if e.get('company_id') == company_id}
    by_no, dropped = {}, 0
    for row in rows:
        rcept_no, rcept_dt, title, kind = row.get('rcept_no'), row.get('rcept_dt'), row.get('title'), row.get('report_type')
        if (type(rcept_no) is not str or not re.fullmatch(r'\d{14}', rcept_no) or type(rcept_dt) is not str
                or not re.fullmatch(r'\d{8}', rcept_dt) or not valid_title(title) or kind not in (*REPORT_TYPES, None)):
            dropped += 1
            continue
        try:
            filed = date(int(rcept_dt[:4]), int(rcept_dt[4:6]), int(rcept_dt[6:])).isoformat()
        except ValueError:
            dropped += 1
            continue
        if filed < cutoff or filed > as_of.astimezone(KST).date().isoformat():
            continue
        known = by_no.get(rcept_no)
        if known is not None:
            # The same receipt in a typed and the untyped list: the typed row decides the classification.
            if known['report_type'] is None and kind is not None:
                known.update(report_type=kind, classification=classify(known['title'], kind))
            continue
        by_no[rcept_no] = {'company_id': company_id, 'source': SOURCE, 'rcept_no': rcept_no, 'report_type': kind, 'title': title,
                           'filing_date': filed, 'accepted_at': None, 'time_precision': 'DATE_KST',
                           'classification': classify(title, kind), 'amended': is_amended(title), 'link': link(rcept_no),
                           'group_id': None, 'occurrence': None, 'first_seen_at': seen_before.get(rcept_no) or instant(as_of)}
    events = order(by_no.values())[:MAX_EVENTS]
    return order(assign_groups(events)), dropped


def empty_company(stock_code, reason='NOT_COLLECTED'):
    return {'state': 'NOT_AVAILABLE', 'acquired_at': None, 'reason_code': reason, 'stock_code': stock_code, 'corp_code': None,
            'corp_code_basis': None, 'truncated': False}


def disclosures_payload(*, as_of, companies, events, api_calls=0, api_call_budget=0):
    as_of = _clock(instant(as_of))
    for company in companies.values():
        if company['acquired_at'] is not None:
            company['state'] = fresh(_clock(company['acquired_at']), as_of)
    state, reasons = _top([c['state'] for c in companies.values()])
    payload = {'schema_version': 1, 'kind': DISCLOSURES_KIND, 'source': SOURCE, 'as_of': instant(as_of), 'state': state,
               'reason_codes': reasons, 'freshness_basis': 'SOURCE_ACQUISITION',
               'stale_after_seconds': int(STALE_AFTER.total_seconds()), 'window_days': WINDOW_DAYS, 'channel': 'DISCLOSURE',
               'score_effect': 'NONE', 'collection': {'api_calls': api_calls, 'api_call_budget': api_call_budget},
               'companies': companies, 'events': order(assign_groups(list(events)))}
    return require_disclosures(payload)


def empty_disclosures(as_of, reason='NOT_COLLECTED'):
    return disclosures_payload(as_of=as_of, companies={c: empty_company(s, reason) for c, s in COMPANIES.items()}, events=[])


def _require_disclosures(p):
    _need(type(p) is dict and set(p) == set(DISCLOSURE_TOP_KEYS))
    _need(type(p['schema_version']) is int and p['schema_version'] == 1 and p['kind'] == DISCLOSURES_KIND and p['source'] == SOURCE)
    _need(p['freshness_basis'] == 'SOURCE_ACQUISITION' and p['channel'] == 'DISCLOSURE' and p['score_effect'] == 'NONE')
    _need(type(p['stale_after_seconds']) is int and p['stale_after_seconds'] == int(STALE_AFTER.total_seconds()))
    _need(type(p['window_days']) is int and p['window_days'] == WINDOW_DAYS)
    cut = _clock(p['as_of'])
    collection = p['collection']
    _need(type(collection) is dict and set(collection) == {'api_calls', 'api_call_budget'})
    _need(all(type(collection[k]) is int and 0 <= collection[k] <= 50 for k in collection))
    _need(collection['api_calls'] <= collection['api_call_budget'])
    companies = p['companies']
    _need(type(companies) is dict and set(companies) == set(COMPANIES))
    acquired = {}
    for cid, c in companies.items():
        _need(type(c) is dict and set(c) == set(COMPANY_KEYS) and c['stock_code'] == COMPANIES[cid] and type(c['truncated']) is bool)
        if c['acquired_at'] is None:
            _need(c['state'] == 'NOT_AVAILABLE' and c['reason_code'] in REASONS and c['reason_code'] != 'STALE_INPUT')
            _need(c['corp_code'] is None and c['corp_code_basis'] is None and not c['truncated'])
        else:
            at = _clock(c['acquired_at'])
            _need(at <= cut and c['state'] == fresh(at, cut))
            _need(c['reason_code'] in (None, 'DART_LIST_TRUNCATED', 'RECORDS_DROPPED_INVALID'))
            _need(c['truncated'] == (c['reason_code'] == 'DART_LIST_TRUNCATED'))
            _need(type(c['corp_code']) is str and re.fullmatch(r'\d{8}', c['corp_code']) is not None and c['corp_code_basis'] == 'CORPCODE_XML')
            acquired[cid] = at
    state, reasons = _top([c['state'] for c in companies.values()])
    _need(p['state'] == state and p['reason_codes'] == reasons)
    events = p['events']
    _need(type(events) is list and len(events) <= MAX_EVENTS)
    cutoff = cut.astimezone(KST).date() - timedelta(days=WINDOW_DAYS)
    seen = set()
    for e in events:
        _need(type(e) is dict and set(e) == set(EVENT_KEYS) and e['company_id'] in acquired and e['source'] == SOURCE)
        _need(type(e['rcept_no']) is str and re.fullmatch(r'\d{14}', e['rcept_no']) is not None and e['rcept_no'] not in seen)
        seen.add(e['rcept_no'])
        _need(e['report_type'] in (*REPORT_TYPES, None) and valid_title(e['title']))
        filed = _day(e['filing_date'])
        _need(cutoff <= filed <= acquired[e['company_id']].astimezone(KST).date())
        _need(e['accepted_at'] is None and e['time_precision'] == 'DATE_KST')
        _need(e['classification'] in CLASSIFICATIONS and e['classification'] == classify(e['title'], e['report_type']))
        _need(type(e['amended']) is bool and e['amended'] == is_amended(e['title']) and e['link'] == link(e['rcept_no']))
        seen_at = _clock(e['first_seen_at'])
        _need(seen_at <= cut and seen_at.astimezone(KST).date() >= filed)
    _need(events == order(events))
    expected = assign_groups([dict(e) for e in events])
    _need(all(a['group_id'] == b['group_id'] and a['occurrence'] == b['occurrence'] for a, b in zip(events, expected)))
    return p


def require_disclosures(payload):
    """Strict public validator (writer, preserve, Pages guard). Fixed error only."""
    try:
        return _require_disclosures(payload)
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError):
        raise DartPublicError('DART_PUBLIC_INVALID') from None


def timeline_rows(payload, company_ids=None):
    """Rows in the sec-disclosures.js timeline shape ({channel, time, company_id, event}); time = KST filing day start."""
    rows = []
    for e in (payload or {}).get('events', []):
        if company_ids is None or e['company_id'] in company_ids:
            start = datetime.fromisoformat(e['filing_date'] + 'T00:00:00+09:00')
            rows.append({'channel': 'DISCLOSURE', 'source': SOURCE, 'time': instant(start), 'company_id': e['company_id'], 'event': e})
    return rows


# ---------------------------------------------------------------- financials


def _number(value):
    return value is None or (type(value) in (int, float) and math.isfinite(value) and abs(value) < 1e17)


def empty_report(reasons=('NOT_COLLECTED',)):
    return {'state': 'NOT_AVAILABLE', 'reason_codes': list(reasons), 'rcept_no': None, 'report_name': None, 'bsns_year': None,
            'reprt_code': None, 'period': None, 'fs_div': None, 'fs_label': None, 'filed_at': None, 'basis': None,
            'inputs': dict.fromkeys(INPUT_NAMES), 'concepts': dict.fromkeys(INPUT_NAMES),
            'missing': dict.fromkeys(INPUT_NAMES, 'NOT_COLLECTED'), 'source_sha256': {'statements': None, 'shares': None}}


def _factors():
    from ..qgv.factors import G_WEIGHTS, Q_WEIGHTS
    return sorted(set(Q_WEIGHTS) | set(G_WEIGHTS))


def empty_qg(reasons=('NOT_COLLECTED',)):
    return {'state': 'NOT_AVAILABLE', 'basis': 'ANNUAL_REPORT', 'reason_codes': list(reasons),
            'factors': {fid: {'score': None, 'state': 'NOT_AVAILABLE'} for fid in _factors()}}


def empty_financial_company(stock_code, reasons=('NOT_COLLECTED',)):
    return {'stock_code': stock_code, 'corp_code': None, 'state': 'NOT_AVAILABLE', 'reason_codes': list(reasons),
            'acquired_at': None, 'annual': empty_report(reasons), 'latest_interim': empty_report(reasons), 'qg': empty_qg(reasons)}


def raw_inputs(inputs):
    """Annual inputs -> the same normalized RawFundamentals fields the SEC 10-K converter produces.

    fcf = operating cash flow - |capex| only when both exist; invested_capital = equity + debt, or equity when
    debt is missing (same rule as providers.sec_companyfacts.facts_to_raw)."""
    ocf, capex = inputs['operating_cash_flow'], inputs['capex']
    equity, debt = inputs['equity'], inputs['total_debt']
    return {'revenue': inputs['revenue'], 'revenue_prev': inputs['revenue_prev'], 'ebit': inputs['operating_income'],
            'ebit_prev': inputs['operating_income_prev'], 'fcf': ocf - abs(capex) if ocf is not None and capex is not None else None,
            'net_income': inputs['net_income'], 'equity': equity,
            'invested_capital': (equity + debt) if equity is not None and debt is not None else equity,
            'cash': inputs['cash_and_equivalents'], 'total_debt': debt, 'shares': inputs['shares'],
            'eps': inputs['eps'], 'eps_prev': inputs['eps_prev']}


def compute_qg(company_id, annual, state='LIVE'):
    """Unchanged map_raw factor scores from an annual report block. Factor state mirrors acquisition freshness."""
    if annual['state'] != 'LIVE' or state == 'NOT_AVAILABLE':
        return empty_qg(['QG_INPUTS_NOT_AVAILABLE'])
    from ..qgv.raw_map import map_raw
    from ..qgv.sec_m2 import _mapping_view
    normalized = {**raw_inputs(annual['inputs']), 'profile_kind': 'GENERAL_CORPORATE', 'period_quality': 'FORM_ALIGNED',
                  'reporting_currency': 'KRW', 'stamp': {'data_stamp_id': f"dart_{company_id}_{annual['rcept_no']}_{annual['fs_div']}"}}
    observations = map_raw(_mapping_view(company_id, normalized, False))
    factors = {}
    for fid in _factors():
        score = observations[fid].score_0_100
        factors[fid] = {'score': score, 'state': state} if score is not None else {'score': None, 'state': 'NOT_AVAILABLE'}
    live = any(f['state'] != 'NOT_AVAILABLE' for f in factors.values())
    return {'state': state if live else 'NOT_AVAILABLE', 'basis': 'ANNUAL_REPORT',
            'reason_codes': [] if live else ['QG_INPUTS_NOT_AVAILABLE'], 'factors': factors}


def restate_company(company_id, company, as_of):
    """Freshness from the company's own acquisition time; values unchanged."""
    if company['acquired_at'] is None:
        return company
    state = fresh(_clock(company['acquired_at']), as_of)
    reasons = [r for r in company['reason_codes'] if r != 'STALE_INPUT'] + (['STALE_INPUT'] if state == 'STALE' else [])
    return {**company, 'state': state, 'reason_codes': reasons, 'qg': compute_qg(company_id, company['annual'], state)}


def financials_payload(*, as_of, companies):
    as_of = _clock(instant(as_of))
    companies = {cid: restate_company(cid, c, as_of) for cid, c in companies.items()}
    state, reasons = _top([c['state'] for c in companies.values()])
    payload = {'schema_version': 1, 'kind': FINANCIALS_KIND, 'source': SOURCE, 'as_of': instant(as_of), 'state': state,
               'reason_codes': reasons, 'freshness_basis': 'SOURCE_ACQUISITION',
               'stale_after_seconds': int(STALE_AFTER.total_seconds()), 'role': 'PRICE_FREE_REPORTED_INPUTS',
               'currency': 'KRW', 'method_status': 'PROVISIONAL_UNCALIBRATED', 'availability_basis': 'OBSERVED_CAPTURE_ONLY',
               'companies': companies}
    return require_financials(payload)


def empty_financials(as_of, reasons=('NOT_COLLECTED',)):
    return financials_payload(as_of=as_of, companies={cid: empty_financial_company(code, reasons) for cid, code in COMPANIES.items()})


def _report(block, *, annual, acquired_day):
    _need(type(block) is dict and set(block) == set(REPORT_KEYS))
    reasons = _reasons(block['reason_codes'])
    inputs, concepts, missing = block['inputs'], block['concepts'], block['missing']
    _need(all(type(x) is dict and set(x) == set(INPUT_NAMES) for x in (inputs, concepts, missing)))
    _need(type(block['source_sha256']) is dict and set(block['source_sha256']) == {'statements', 'shares'})
    if block['state'] == 'NOT_AVAILABLE':
        _need(reasons and all(block[k] is None for k in REPORT_KEYS[2:11]))
        _need(all(v is None for v in inputs.values()) and all(v is None for v in concepts.values()))
        _need(all(v in MISSING_REASONS for v in missing.values()) and all(v is None for v in block['source_sha256'].values()))
        return
    _need(block['state'] == 'LIVE' and acquired_day is not None)
    _need(type(block['rcept_no']) is str and re.fullmatch(r'\d{14}', block['rcept_no']) is not None and valid_title(block['report_name']))
    _need(type(block['bsns_year']) is str and re.fullmatch(r'\d{4}', block['bsns_year']) is not None)
    _need(block['reprt_code'] in PERIODS and block['period'] == PERIODS[block['reprt_code']])
    _need((block['reprt_code'] == '11011') == annual and block['basis'] == ('FISCAL_YEAR' if annual else 'YEAR_TO_DATE'))
    _need((block['fs_div'], block['fs_label']) in (('CFS', 'CONSOLIDATED'), ('OFS', 'SEPARATE_FALLBACK')))
    _need((block['fs_div'] == 'OFS') == ('SEPARATE_STATEMENTS_FALLBACK' in reasons))
    _need(_day(block['filed_at']) <= acquired_day and _hash(block['source_sha256']['statements']))
    _need(block['source_sha256']['shares'] is None or _hash(block['source_sha256']['shares']))
    for name in INPUT_NAMES:
        value, concept = inputs[name], concepts[name]
        _need(_number(value) and type(value) is not bool)
        if value is None:
            _need(missing[name] in MISSING_REASONS and (concept is None or missing[name] in ('AMBIGUOUS', 'UNPARSEABLE')))
        else:
            _need(missing[name] is None and concept is not None)
        if name == 'shares':
            _need(concept in (None, 'stockTotqySttus.distb_stock_co') and (value is None or (type(value) is int and value > 0)))
            _need((concept is None) == (value is None))
        else:
            _need(concept is None or type(concept) is str and re.fullmatch(r'(?:ifrs-full|dart)_[A-Za-z]{1,100}', concept) is not None)
        if name.endswith('_prev') and not annual:
            _need(value is None and missing[name] == 'NOT_IN_INTERIM_SCOPE')
    _need(('SHARES_NOT_AVAILABLE' in reasons) == (inputs['shares'] is None))


def _qg(block, annual, company_id, state):
    _need(type(block) is dict and set(block) == {'state', 'basis', 'reason_codes', 'factors'} and block['basis'] == 'ANNUAL_REPORT')
    _reasons(block['reason_codes'])
    factors = block['factors']
    _need(type(factors) is dict and set(factors) == set(_factors()))
    for factor in factors.values():
        _need(type(factor) is dict and set(factor) == {'score', 'state'})
        if factor['state'] == 'NOT_AVAILABLE':
            _need(factor['score'] is None)
        else:
            _need(factor['state'] == state and type(factor['score']) in (int, float) and type(factor['score']) is not bool
                  and math.isfinite(factor['score']) and 0 <= factor['score'] <= 100)
    if annual['state'] != 'LIVE' or state == 'NOT_AVAILABLE':
        _need(block['state'] == 'NOT_AVAILABLE' and all(f['state'] == 'NOT_AVAILABLE' for f in factors.values()))
    else:
        # Scores must be exactly the unchanged engine applied to the published inputs.
        _need(block == compute_qg(company_id, annual, state))


def _require_financials(p):
    _need(type(p) is dict and set(p) == set(FIN_TOP_KEYS))
    _need(type(p['schema_version']) is int and p['schema_version'] == 1 and p['kind'] == FINANCIALS_KIND and p['source'] == SOURCE)
    _need(p['role'] == 'PRICE_FREE_REPORTED_INPUTS' and p['currency'] == 'KRW' and p['freshness_basis'] == 'SOURCE_ACQUISITION')
    _need(p['method_status'] == 'PROVISIONAL_UNCALIBRATED' and p['availability_basis'] == 'OBSERVED_CAPTURE_ONLY')
    _need(type(p['stale_after_seconds']) is int and p['stale_after_seconds'] == int(STALE_AFTER.total_seconds()))
    cut = _clock(p['as_of'])
    companies = p['companies']
    _need(type(companies) is dict and set(companies) == set(COMPANIES))
    for cid, c in companies.items():
        _need(type(c) is dict and set(c) == set(FIN_COMPANY_KEYS) and c['stock_code'] == COMPANIES[cid])
        reasons = _reasons(c['reason_codes'])
        acquired = _clock(c['acquired_at']) if c['acquired_at'] is not None else None
        acquired_day = acquired.astimezone(KST).date() if acquired is not None else None
        _report(c['annual'], annual=True, acquired_day=acquired_day)
        _report(c['latest_interim'], annual=False, acquired_day=acquired_day)
        live = c['annual']['state'] == 'LIVE' or c['latest_interim']['state'] == 'LIVE'
        if live:
            _need(acquired is not None and acquired <= cut and c['state'] == fresh(acquired, cut))
            _need(type(c['corp_code']) is str and re.fullmatch(r'\d{8}', c['corp_code']) is not None)
            _need(reasons == (['STALE_INPUT'] if c['state'] == 'STALE' else []))
            if c['annual']['state'] == 'LIVE' and c['latest_interim']['state'] == 'LIVE':
                _need(c['latest_interim']['bsns_year'] > c['annual']['bsns_year'])
        else:
            _need(c['state'] == 'NOT_AVAILABLE' and reasons and 'STALE_INPUT' not in reasons)
            _need(acquired is None and c['corp_code'] is None)
        _qg(c['qg'], c['annual'], cid, c['state'])
    state, top = _top([c['state'] for c in companies.values()])
    _need(p['state'] == state and p['reason_codes'] == top)
    return p


def require_financials(payload):
    try:
        return _require_financials(payload)
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError):
        raise DartPublicError('DART_PUBLIC_INVALID') from None


def require_public(name, payload):
    _need(name in FILENAMES)
    return require_disclosures(payload) if name == DISCLOSURES_FILENAME else require_financials(payload)


def parse_json(body):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise DartPublicError('DART_PUBLIC_INVALID')
            out[key] = value
        return out

    def constant(_):
        raise DartPublicError('DART_PUBLIC_INVALID')
    try:
        if type(body) is not bytes or len(body) > MAX_BYTES:
            raise ValueError
        return json.loads(body.decode('utf-8', errors='strict'), object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, UnicodeError, RecursionError):
        raise DartPublicError('DART_PUBLIC_INVALID') from None


def encode(name, payload):
    require_public(name, payload)
    body = json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(',', ':'), allow_nan=False).encode()
    _need(len(body) <= MAX_BYTES)
    return body
