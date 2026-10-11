"""Public price-free classification sidecar: SEC SIC industry group v0 and strategy theme v0.

company-classification.json holds only group/theme ids and names, per-company memberships with their
evidence kind (ETF / KEYWORD) and holding-ETF ticker list, as-of dates, reason codes and source hashes.
No ETF weights, prices, market values, share quantities, 10-K text or keyword counts. Missing evidence is
NOT_AVAILABLE (null), never 0. Cyclical/defensive memberships stay NOT_AVAILABLE (rule undecided).
"""
from datetime import datetime, timedelta, timezone
import math
import re

from ..markets.us import US_LISTINGS
from ..qgv.portfolio import OFFICIAL_V11_TARGETS
from ..qgv.sic_industry import load_sic_config, classify_sic, CANDIDATES
from ..qgv.theme_membership import load_theme_config_v0, theme_memberships, basket_tickers, EVIDENCE

FILENAME = 'company-classification.json'
KIND = 'COMPANY_CLASSIFICATION'
STATES = ('LIVE', 'STALE', 'NOT_AVAILABLE')
AGENCIES = ('SEC_SUBMISSIONS', 'SEC_10K', 'SEC_NPORT', 'SEC_MF_TICKERS')
REASONS = ('NO_ELIGIBLE_INPUT', 'SOURCE_NOT_AVAILABLE', 'STALE_INPUT', 'PARTIAL_INPUT', 'CYCLICAL_DEFENSIVE_RULE_UNDECIDED')
INDUSTRY_REASONS = ('SIC_NOT_AVAILABLE', 'SIC_UNMATCHED', 'SOURCE_NOT_AVAILABLE', 'NOT_SEC_REGISTRANT')
KEYWORD_STATES = ('AVAILABLE', 'TEN_K_NOT_FILED', 'NOT_AVAILABLE')
KEYWORD_REASONS = ('TEN_K_NOT_FILED', 'ITEM1_NOT_FOUND', 'SOURCE_NOT_AVAILABLE', 'NOT_SEC_REGISTRANT')
ETF_REASONS = ('SOURCE_NOT_AVAILABLE', 'ETF_SERIES_BINDING_NOT_AVAILABLE', 'ETF_SERIES_UNBOUND', 'NPORT_FILING_LIST_NOT_AVAILABLE',
               'NPORT_NOT_FOUND', 'NPORT_INVALID', 'NPORT_SERIES_MISMATCH')
CALIBRATION = 'V0_UNCALIBRATED_DEFAULT'
_HASH = re.compile(r'[0-9a-f]{64}')
_DAY = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}')
_TICKER_FOR = {'tokyo_electron': '8035', 'hanmi': '042700'}


def _need(condition):
    if not condition:
        raise ValueError('PUBLIC_CLASSIFICATION_INVALID')


def company_identity():
    """{company_id: {'cik': CIK10 | None, 'securities': frozenset | None}} for the 19 TARGET companies.

    Identifiers come from the reviewed public identity catalog (ISIN; CUSIP derived only from US ISINs).
    Exchange-code-only listings (TSE/KRX) have no exact ETF join and stay NOT_AVAILABLE.
    """
    from .device_actual_catalog import public_actual_catalog
    from ..providers.sec_classification_inputs import security_identifiers
    by_ticker = {i['ticker']: i['security_reference'] for i in public_actual_catalog()['instruments']}
    out = {}
    for cid in OFFICIAL_V11_TARGETS:
        listing = US_LISTINGS.get(cid)
        ref = by_ticker.get(listing['yahoo'] if listing else _TICKER_FOR.get(cid))
        securities = security_identifiers(isin=ref.get('value')) if isinstance(ref, dict) and ref.get('scheme') == 'ISIN' else frozenset()
        out[cid] = {'cik': listing['cik'] if listing else None, 'securities': securities or None}
    return out


def _fresh(acquired, as_of, stale_after):
    return 'STALE' if as_of - acquired > stale_after else 'LIVE'


def _aggregate(states):
    return 'LIVE' if 'LIVE' in states else 'STALE' if 'STALE' in states else 'NOT_AVAILABLE'


def _utc(value):
    _need(isinstance(value, datetime) and value.utcoffset() is not None)
    return value.astimezone(timezone.utc)


def build_classification(*, as_of, stale_after, companies_input=None, etfs_input=None, mf_source=None,
                         identity=None, sic_config=None, theme_config=None):
    """Build and validate the public payload from RAM evidence (see sec_classification_collection)."""
    as_of = _utc(as_of)
    _need(isinstance(stale_after, timedelta) and stale_after.total_seconds() > 0)
    sic_cfg = sic_config or load_sic_config()
    theme_cfg = theme_config or load_theme_config_v0()
    identity = identity if identity is not None else company_identity()
    companies_input = companies_input or {}
    etfs_input = etfs_input or {}
    sources, states = {}, []

    def source(agency, sha, acquired):
        acquired = _utc(acquired)
        _need(acquired <= as_of and _HASH.fullmatch(sha or '') is not None)
        sources[(agency, sha)] = acquired
        return acquired

    etfs, etf_sets, etf_acquired = {}, {}, {}
    for ticker in basket_tickers(theme_cfg):
        row = etfs_input.get(ticker)
        if isinstance(row, dict) and row.get('state') == 'AVAILABLE':
            acquired = source('SEC_NPORT', row['sha256'], row['acquired_at'])
            _need(isinstance(row['securities'], frozenset) and _DAY.fullmatch(row.get('report_date') or '') is not None)
            etf_sets[ticker], etf_acquired[ticker] = row['securities'], acquired
            etfs[ticker] = {'state': _fresh(acquired, as_of, stale_after), 'report_date': row['report_date'],
                            'reason_code': None, 'source_sha256': row['sha256']}
        else:
            reason = row.get('reason_code') if isinstance(row, dict) and row.get('reason_code') in ETF_REASONS else 'SOURCE_NOT_AVAILABLE'
            etf_sets[ticker] = None
            etfs[ticker] = {'state': 'NOT_AVAILABLE', 'report_date': None, 'reason_code': reason, 'source_sha256': None}
        states.append(etfs[ticker]['state'])
    if mf_source and etf_acquired:
        source('SEC_MF_TICKERS', mf_source['sha256'], mf_source['acquired_at'])

    companies = {}
    for cid in OFFICIAL_V11_TARGETS:
        ident = identity.get(cid) or {'cik': None, 'securities': None}
        registrant = ident['cik'] is not None
        row = companies_input.get(cid) if registrant else None
        subs = row.get('submissions') if isinstance(row, dict) else None
        industry = {'state': 'NOT_AVAILABLE', 'sic': None, 'group': None, 'subgroup': None, 'cyclical_defensive_candidate': None,
                    'reason_code': 'SOURCE_NOT_AVAILABLE' if registrant else 'NOT_SEC_REGISTRANT', 'source_hashes': {}}
        if isinstance(subs, dict):
            acquired = source('SEC_SUBMISSIONS', subs['sha256'], subs['acquired_at'])
            result = classify_sic(subs.get('sic'), sic_cfg)
            industry.update(sic=result['sic'], group=result['group'], subgroup=result['subgroup'],
                            cyclical_defensive_candidate=result['cyclical_defensive_candidate'], reason_code=result['reason_code'],
                            source_hashes={'submissions': subs['sha256']})
            if result['group'] is not None:
                industry['state'] = _fresh(acquired, as_of, stale_after)
        ten_k = row.get('ten_k') if isinstance(row, dict) else None
        keyword_state, item1, keyword = 'NOT_AVAILABLE', None, {'state': 'NOT_AVAILABLE', 'reason_code': 'SOURCE_NOT_AVAILABLE' if registrant else 'NOT_SEC_REGISTRANT', 'report_date': None}
        theme_hashes, used = {}, []
        if isinstance(ten_k, dict) and ten_k.get('state') == 'AVAILABLE' and isinstance(subs, dict):
            used.append(source('SEC_10K', ten_k['sha256'], ten_k['acquired_at']))
            keyword_state, item1 = 'AVAILABLE', ten_k['item1_text']
            keyword = {'state': 'AVAILABLE', 'reason_code': None, 'report_date': ten_k.get('report_date') if _DAY.fullmatch(ten_k.get('report_date') or '') else None}
            theme_hashes['ten_k'] = ten_k['sha256']
        elif isinstance(ten_k, dict) and ten_k.get('state') == 'TEN_K_NOT_FILED' and isinstance(subs, dict):
            keyword_state, keyword = 'TEN_K_NOT_FILED', {'state': 'TEN_K_NOT_FILED', 'reason_code': 'TEN_K_NOT_FILED', 'report_date': None}
            used.append(_utc(subs['acquired_at']))
            theme_hashes['submissions'] = subs['sha256']
        elif isinstance(ten_k, dict) and ten_k.get('reason_code') in KEYWORD_REASONS:
            keyword['reason_code'] = ten_k['reason_code']
        members = theme_memberships(theme_cfg, etf_securities=etf_sets, company_securities=ident['securities'],
                                    keyword_state=keyword_state, item1_text=item1)
        for t in theme_cfg['themes']:
            if members[t['id']]['member'] is not None:
                used.extend(etf_acquired[e['ticker']] for e in t['etfs'] if e['ticker'] in etf_acquired)
        known = any(m['member'] is not None for m in members.values())
        themes = {'state': _fresh(min(used), as_of, stale_after) if known and used else 'NOT_AVAILABLE',
                  'keyword_evidence': keyword, 'etf_join': 'EXACT_IDENTIFIER' if ident['securities'] else 'NOT_AVAILABLE',
                  'memberships': members, 'source_hashes': theme_hashes}
        states.extend((industry['state'], themes['state']))
        companies[cid] = {'industry': industry, 'themes': themes}

    state = _aggregate(states)
    reasons = ['CYCLICAL_DEFENSIVE_RULE_UNDECIDED']
    if state == 'NOT_AVAILABLE':
        reasons += ['NO_ELIGIBLE_INPUT', 'SOURCE_NOT_AVAILABLE']
    elif state == 'STALE':
        reasons.append('STALE_INPUT')
    if state != 'NOT_AVAILABLE' and 'NOT_AVAILABLE' in states:
        reasons.append('PARTIAL_INPUT')
    payload = {'schema_version': 1, 'kind': KIND, 'as_of': as_of.isoformat(), 'state': state,
               'freshness_basis': 'SOURCE_ACQUISITION', 'stale_after_seconds': stale_after.total_seconds(), 'reason_codes': reasons,
               'sources': [{'agency': a, 'sha256': s, 'acquired_at': t.isoformat()} for (a, s), t in sorted(sources.items())],
               'data': {'calibration': CALIBRATION,
                        'industry_config': {'config_version': sic_cfg['config_version'], 'decided_at': sic_cfg['decided_at'],
                                            'groups': [{'id': g['id'], 'name': g['name'], 'name_en': g['name_en']} for g in sic_cfg['groups']],
                                            'subgroups': [{'id': s['id'], 'group': s['group'], 'name': s['name'], 'name_en': s['name_en']} for s in sic_cfg['subgroups']]},
                        'theme_config': {'config_version': theme_cfg['config_version'], 'decided_at': theme_cfg['decided_at'],
                                         'membership_rule': theme_cfg['membership_rule']['kind'],
                                         'themes': [{'id': t['id'], 'name': t['name'], 'name_en': t['name_en'], 'etfs': [e['ticker'] for e in t['etfs']],
                                                     'evidence_strength': t['evidence_strength']} for t in theme_cfg['themes']]},
                        'etfs': etfs, 'companies': companies}}
    return require_public_classification(payload)


def unavailable_classification(as_of=None, stale_after=timedelta(hours=24)):
    """Offline/Pages build without SEC access: every value NOT_AVAILABLE with reason codes."""
    return build_classification(as_of=as_of or datetime.now(timezone.utc), stale_after=stale_after)


# ---------------- validator (mirrors classification-screens.js) ----------------

def _keys(value, keys):
    _need(isinstance(value, dict) and set(value) == set(keys))


def _clock(value):
    _need(isinstance(value, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})', value) is not None)
    d = datetime.fromisoformat(value.replace('Z', '+00:00'))
    _need(d.utcoffset() is not None)
    return d.astimezone(timezone.utc)


def _day(value):
    _need(value is None or isinstance(value, str) and _DAY.fullmatch(value) is not None)
    if value is not None:
        datetime.strptime(value, '%Y-%m-%d')


def _name(value):
    _need(isinstance(value, str) and 0 < len(value.strip()) and len(value) <= 80)


def _require(p):
    _keys(p, ('schema_version', 'kind', 'as_of', 'state', 'freshness_basis', 'stale_after_seconds', 'reason_codes', 'sources', 'data'))
    _need(type(p['schema_version']) is int and p['schema_version'] == 1 and p['kind'] == KIND and p['state'] in STATES)
    _need(p['freshness_basis'] == 'SOURCE_ACQUISITION' and type(p['stale_after_seconds']) in (int, float)
          and math.isfinite(p['stale_after_seconds']) and p['stale_after_seconds'] > 0)
    cut = _clock(p['as_of'])
    stale = timedelta(seconds=p['stale_after_seconds'])
    _need(isinstance(p['reason_codes'], list) and all(r in REASONS for r in p['reason_codes']) and len(set(p['reason_codes'])) == len(p['reason_codes']))
    _need(isinstance(p['sources'], list) and len(p['sources']) <= 1000)
    sources = {}
    for s in p['sources']:
        _keys(s, ('agency', 'sha256', 'acquired_at'))
        _need(s['agency'] in AGENCIES and isinstance(s['sha256'], str) and _HASH.fullmatch(s['sha256']) is not None)
        at = _clock(s['acquired_at'])
        _need(at <= cut and (s['agency'], s['sha256']) not in sources)
        sources[(s['agency'], s['sha256'])] = at
    d = p['data']
    _keys(d, ('calibration', 'industry_config', 'theme_config', 'etfs', 'companies'))
    _need(d['calibration'] == CALIBRATION)
    ic = d['industry_config']
    _keys(ic, ('config_version', 'decided_at', 'groups', 'subgroups'))
    _need(ic['config_version'] == 'sic_industry_groups/v0' and ic['decided_at'] == '2026-10-11')
    _need(isinstance(ic['groups'], list) and 0 < len(ic['groups']) <= 64 and isinstance(ic['subgroups'], list) and len(ic['subgroups']) <= 128)
    groups = set()
    for g in ic['groups']:
        _keys(g, ('id', 'name', 'name_en'))
        _need(isinstance(g['id'], str) and re.fullmatch(r'[a-z][a-z0-9_]{0,63}', g['id']) is not None and g['id'] not in groups)
        _name(g['name']); _name(g['name_en']); groups.add(g['id'])
    subgroups = {}
    for s in ic['subgroups']:
        _keys(s, ('id', 'group', 'name', 'name_en'))
        _need(isinstance(s['id'], str) and re.fullmatch(r'[a-z][a-z0-9_]{0,63}', s['id']) is not None and s['id'] not in subgroups and s['group'] in groups)
        _name(s['name']); _name(s['name_en']); subgroups[s['id']] = s['group']
    tc = d['theme_config']
    _keys(tc, ('config_version', 'decided_at', 'membership_rule', 'themes'))
    _need(tc['config_version'] == 'theme_config/v0' and tc['decided_at'] == '2026-10-11' and tc['membership_rule'] == 'ETF_HELD_OR_10K_ITEM1_KEYWORD')
    _need(isinstance(tc['themes'], list) and 0 < len(tc['themes']) <= 128)
    themes, tickers = {}, []
    for t in tc['themes']:
        _keys(t, ('id', 'name', 'name_en', 'etfs', 'evidence_strength'))
        _need(isinstance(t['id'], str) and re.fullmatch(r'[a-z][a-z0-9_]{0,63}', t['id']) is not None and t['id'] not in themes)
        _name(t['name']); _name(t['name_en'])
        _need(t['evidence_strength'] in ('STANDARD', 'WEAK') and isinstance(t['etfs'], list) and 0 < len(t['etfs']) <= 16)
        _need(all(isinstance(x, str) and re.fullmatch(r'[A-Z][A-Z0-9.]{0,15}', x) for x in t['etfs']) and len(set(t['etfs'])) == len(t['etfs']))
        themes[t['id']] = t['etfs']
        tickers.extend(x for x in t['etfs'] if x not in tickers)
    states = []
    _need(isinstance(d['etfs'], dict) and set(d['etfs']) == set(tickers))
    for e in d['etfs'].values():
        _keys(e, ('state', 'report_date', 'reason_code', 'source_sha256'))
        _need(e['state'] in STATES)
        _day(e['report_date'])
        if e['state'] == 'NOT_AVAILABLE':
            _need(e['report_date'] is None and e['source_sha256'] is None and e['reason_code'] in ETF_REASONS)
        else:
            _need(e['reason_code'] is None and e['report_date'] is not None and e['report_date'] <= cut.date().isoformat())
            _need(('SEC_NPORT', e['source_sha256']) in sources and e['state'] == _fresh(sources[('SEC_NPORT', e['source_sha256'])], cut, stale))
        states.append(e['state'])
    _need(isinstance(d['companies'], dict) and set(d['companies']) == set(OFFICIAL_V11_TARGETS))
    for row in d['companies'].values():
        _keys(row, ('industry', 'themes'))
        ind = row['industry']
        _keys(ind, ('state', 'sic', 'group', 'subgroup', 'cyclical_defensive_candidate', 'reason_code', 'source_hashes'))
        _need(ind['state'] in STATES and (ind['sic'] is None or isinstance(ind['sic'], str) and re.fullmatch(r'[0-9]{4}', ind['sic']) and ind['sic'] != '0000'))
        _need(ind['cyclical_defensive_candidate'] in (None,) + CANDIDATES and isinstance(ind['source_hashes'], dict) and set(ind['source_hashes']) <= {'submissions'})
        for sha in ind['source_hashes'].values():
            _need(('SEC_SUBMISSIONS', sha) in sources)
        if ind['state'] == 'NOT_AVAILABLE':
            _need(ind['group'] is None and ind['subgroup'] is None and ind['cyclical_defensive_candidate'] is None and ind['reason_code'] in INDUSTRY_REASONS)
            _need(ind['reason_code'] not in ('SIC_UNMATCHED',) or ind['sic'] is not None)
        else:
            _need(ind['group'] in groups and ind['reason_code'] is None and ind['sic'] is not None and 'submissions' in ind['source_hashes'])
            _need(ind['subgroup'] is None or subgroups.get(ind['subgroup']) == ind['group'])
            _need(ind['state'] == _fresh(sources[('SEC_SUBMISSIONS', ind['source_hashes']['submissions'])], cut, stale))
        th = row['themes']
        _keys(th, ('state', 'keyword_evidence', 'etf_join', 'memberships', 'source_hashes'))
        _need(th['state'] in STATES and th['etf_join'] in ('EXACT_IDENTIFIER', 'NOT_AVAILABLE'))
        kw = th['keyword_evidence']
        _keys(kw, ('state', 'reason_code', 'report_date'))
        _need(kw['state'] in KEYWORD_STATES)
        _day(kw['report_date'])
        _need((kw['state'] == 'AVAILABLE') == (kw['reason_code'] is None) and (kw['reason_code'] is None or kw['reason_code'] in KEYWORD_REASONS))
        _need(kw['state'] != 'TEN_K_NOT_FILED' or kw['reason_code'] == 'TEN_K_NOT_FILED')
        _need(kw['state'] == 'AVAILABLE' or kw['report_date'] is None)
        _need(isinstance(th['source_hashes'], dict) and set(th['source_hashes']) <= {'ten_k', 'submissions'})
        _need(('ten_k' in th['source_hashes']) == (kw['state'] == 'AVAILABLE') and ('submissions' in th['source_hashes']) == (kw['state'] == 'TEN_K_NOT_FILED'))
        for key, sha in th['source_hashes'].items():
            _need(({'ten_k': 'SEC_10K', 'submissions': 'SEC_SUBMISSIONS'}[key], sha) in sources)
        _need(isinstance(th['memberships'], dict) and set(th['memberships']) == set(themes))
        for tid, m in th['memberships'].items():
            _keys(m, ('member', 'evidence', 'etfs'))
            _need(m['member'] in (True, False, None) and isinstance(m['evidence'], list) and isinstance(m['etfs'], list))
            _need(m['evidence'] == [k for k in EVIDENCE if k in m['evidence']] and len(set(m['evidence'])) == len(m['evidence']))
            _need(m['etfs'] == [x for x in themes[tid] if x in m['etfs']] and len(set(m['etfs'])) == len(m['etfs']))
            _need(all(d['etfs'][x]['state'] != 'NOT_AVAILABLE' for x in m['etfs']) and ('ETF' in m['evidence']) == bool(m['etfs']))
            _need(m['etfs'] == [] or th['etf_join'] == 'EXACT_IDENTIFIER')
            _need('KEYWORD' not in m['evidence'] or kw['state'] == 'AVAILABLE')
            _need((m['member'] is True) == bool(m['evidence']))
            if m['member'] is False:
                _need(th['etf_join'] == 'EXACT_IDENTIFIER' and kw['state'] in ('AVAILABLE', 'TEN_K_NOT_FILED')
                      and all(d['etfs'][x]['state'] != 'NOT_AVAILABLE' for x in themes[tid]))
        _need((th['state'] == 'NOT_AVAILABLE') == all(m['member'] is None for m in th['memberships'].values()))
        states.extend((ind['state'], th['state']))
    _need(p['state'] == _aggregate(states))
    return p


def require_public_classification(payload):
    try:
        return _require(payload)
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError):
        raise ValueError('PUBLIC_CLASSIFICATION_INVALID') from None
