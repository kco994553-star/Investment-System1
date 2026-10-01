"""Search/presentation entity metadata registry. No scores, ranks or PIT claims.

Deterministic, offline builder: committed source extracts (fetched by
tools/ingest_entity_metadata.py on a network-enabled runner) + the Frozen Top-500
Universe -> one registry keyed by the EXISTING company_id. Identity comes only
from the Universe member's CIK; tickers and names never create or merge entities.
Every kept value carries its source id; rejected values are recorded with a reason.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import unicodedata

ROOT = Path(__file__).resolve().parents[3]
METADATA_DIR = ROOT / 'reports/entity_metadata'
SOURCES_DIR = METADATA_DIR / 'sources'
REGISTRY_NAME = 'top500_entity_metadata_2024-12-31.json'
ROLE = 'SEARCH_PRESENTATION_ONLY'
BUILDER = 'product/entity_metadata.py build_registry v1'
# Wikidata ticker qualifiers are used only on these primary US listing venues.
US_EXCHANGES = {'Q13677': 'NYSE', 'Q82059': 'Nasdaq'}
SOURCE_FILES = {
    'sec_submissions': 'sec_submissions_extract.json',
    'sec_company_tickers': 'sec_company_tickers_extract.json',
    'wikidata': 'wikidata_cik_extract.json',
    'kis_master': 'kis_overseas_master_extract.json',
}
HANGUL = re.compile('[가-힣]')
LATIN = re.compile('[A-Za-z]')
PAREN = re.compile(r'\s*\([^()]*\)\s*$')


def normalize(text):
    """Python twin of web_assets/entity-search.js normalize()."""
    s = unicodedata.normalize('NFKC', str(text or '')).lower()
    s = re.sub('[’‘]', "'", s)
    s = re.sub('[‐‑‒–—−]', '-', s)
    s = ''.join(ch if unicodedata.category(ch)[0] in 'LN' else ' ' for ch in s)
    return ' '.join(s.split())


def ticker_key(text):
    return normalize(text).replace(' ', '')


def clean(text):
    return ' '.join(str(text or '').split())


def name_tokens(text):
    return [t for t in normalize(text).split() if t not in {'the', 'inc', 'corp', 'co', 'ltd', 'plc', 'company',
            'corporation', 'incorporated', 'holdings', 'holding', 'group', 'class', 'common', 'stock', 'shares', 'sa', 'nv', 'ag'}]


def names_agree(a, b):
    """Conservative English cross-check for listing-level sources (first significant token)."""
    ta, tb = name_tokens(a), name_tokens(b)
    return bool(ta and tb) and (ta[0] == tb[0] or ''.join(ta).startswith(''.join(tb)) or ''.join(tb).startswith(''.join(ta)))


def load_sources(folder=SOURCES_DIR):
    folder = Path(folder)
    out = {}
    for key, name in SOURCE_FILES.items():
        p = folder / name
        if p.exists():
            raw = p.read_bytes()
            out[key] = json.loads(raw)
            out[key]['_extract_sha256'] = hashlib.sha256(raw).hexdigest()
    return out


def _wikidata_items(rows, cik, tickers):
    items = sorted({r['item'] for r in rows})
    if len(items) <= 1:
        return items, None
    keys = {ticker_key(t) for t in tickers}
    hit = sorted({r['item'] for r in rows if any(ticker_key(t['symbol']) in keys for t in r.get('tickers', []))})
    if len(hit) == 1:
        return hit, None
    return [], {'field': 'wikidata_item', 'value': items, 'source': 'wikidata', 'reason': 'AMBIGUOUS_CIK_ITEMS'}


def build_registry(universe, sources, universe_sha256, prior_universes=(), reserved_labels=()):
    """Pure function. Same inputs -> byte-identical registry (sorted, no clocks)."""
    members = universe['members']
    sec = (sources.get('sec_submissions') or {}).get('records', {})
    sec_tickers = defaultdict(list)
    for r in (sources.get('sec_company_tickers') or {}).get('rows', []):
        sec_tickers[str(r['cik']).zfill(10)].append(r)
    wd = defaultdict(list)
    for r in (sources.get('wikidata') or {}).get('rows', []):
        wd[str(r['cik']).zfill(10)].append(r)
    kis = defaultdict(list)
    for r in (sources.get('kis_master') or {}).get('rows', []):
        kis[ticker_key(r['symbol'])].append(r)
    prior = defaultdict(list)
    for name, pu in prior_universes:
        for m in pu['members']:
            prior[m['company_id']].append((name, m))

    rejections, cands = [], {}
    for m in members:
        cid, cik, ticker = m['company_id'], m['cik'], m['ticker']
        c = cands[cid] = []
        def add(field, value, locale, source, **extra):
            value = clean(value)
            if value:
                c.append(dict(field=field, value=value, locale=locale, source=source, **extra))
        def reject(field, value, source, reason):
            rejections.append({'company_id': cid, 'field': field, 'value': value, 'source': source, 'reason': reason})
        s = sec.get(cik)
        listed = []
        if s:
            add('official_name', s.get('name'), None, 'sec_submissions')
            listed += list(s.get('tickers') or [])
            for f in s.get('formerNames') or []:
                add('historical_name', f.get('name'), None, 'sec_submissions',
                    valid_from=(f.get('from') or '')[:10] or None, valid_to=(f.get('to') or '')[:10] or None)
        for r in sec_tickers.get(cik, []):
            listed.append(r['ticker'])
            add('alias', r.get('title'), 'en-US', 'sec_company_tickers')
        for t in sorted(set(listed), key=lambda x: (ticker_key(x), x)):
            add('listing_ticker', t, 'und', 'sec_submissions' if s and t in (s.get('tickers') or []) else 'sec_company_tickers')
        for name, pm in prior[cid]:
            if pm['cik'] == cik and ticker_key(pm['ticker']) != ticker_key(ticker):
                add('historical_ticker', pm['ticker'], None, 'track_a_frozen_universe', evidence=name)
        items, amb = _wikidata_items(wd.get(cik, []), cik, [ticker, *listed])
        if amb:
            reject(**amb)
        for r in sorted((r for r in wd.get(cik, []) if r['item'] in items), key=lambda r: r['item']):
            src = 'wikidata:' + r['item']
            add('common_name', r.get('en_label'), 'en-US', src)
            for a in sorted(r.get('en_aliases') or []):
                add('alias', a, 'en-US', src)
            for kind, values in (('common_name', [r.get('ko_label')] if r.get('ko_label') else []),
                                 ('alias', sorted(r.get('ko_aliases') or []))):
                for v in values:
                    if not HANGUL.search(v or ''):
                        reject('ko-KR', v, src, 'NO_HANGUL')
                        continue
                    add(kind, v, 'ko-KR', src)
                    stripped = PAREN.sub('', v)
                    if stripped != v and HANGUL.search(stripped):
                        add('alias', stripped, 'ko-KR', src, normalization='STRIP_DISAMBIGUATOR')
            for t in sorted(r.get('tickers') or [], key=lambda t: (t['symbol'], t.get('end') or '')):
                if t.get('exchange') not in US_EXCHANGES:
                    continue
                if t.get('end'):
                    add('historical_ticker', t['symbol'], None, src, evidence='P414/P249 end ' + t['end'][:10])
        for t in sorted({ticker_key(x) for x in listed}):
            for r in sorted(kis.get(t, []), key=lambda r: (r.get('exchange', ''), r['symbol'])):
                src = 'kis_master:' + r.get('exchange', '')
                if str(r.get('security_type')) != '2':
                    reject('ko-KR', r.get('ko_name'), src, 'NOT_STOCK_LISTING')
                elif not HANGUL.search(r.get('ko_name') or ''):
                    reject('ko-KR', r.get('ko_name'), src, 'NO_HANGUL')
                elif not s or not names_agree(r.get('en_name'), s.get('name')):
                    reject('ko-KR', r.get('ko_name'), src, 'LISTING_NAME_MISMATCH')
                else:
                    add('listing_name', r['ko_name'], 'ko-KR', src, symbol=r['symbol'])

    # Cross-entity false-positive protection. Primary tickers/official names are reserved
    # for their owner; any other label claimed by more than one entity is dropped everywhere.
    primary_ticker = {ticker_key(m['ticker']): m['company_id'] for m in members}
    reserved = {normalize(x) for x in reserved_labels} | {ticker_key(x) for x in reserved_labels}
    owners = {True: defaultdict(set), False: defaultdict(set)}
    for cid, c in cands.items():
        for v in c:
            tick = v['field'] in ('historical_ticker', 'listing_ticker')
            owners[tick][ticker_key(v['value']) if tick else normalize(v['value'])].add(cid)
    official_owner = defaultdict(set)
    for cid, c in cands.items():
        for v in c:
            if v['field'] == 'official_name':
                official_owner[normalize(v['value'])].add(cid)

    records = {}
    for m in members:
        cid = m['company_id']
        rec = {'company_id': cid, 'cik': m['cik'], 'ticker': m['ticker'], 'official_name': None,
               'common_names': {}, 'aliases': {}, 'historical_names': [], 'historical_tickers': []}
        seen = {ticker_key(m['ticker'])}
        for v in cands[cid]:
            tick = v['field'] in ('historical_ticker', 'listing_ticker')
            key = ticker_key(v['value']) if tick else normalize(v['value'])
            why = None
            if len(key.replace(' ', '')) < (1 if tick else 2):
                why = 'TOO_SHORT'
            elif key in reserved or (not tick and ticker_key(v['value']) in reserved):
                why = 'RESERVED_NAVIGATION_LABEL'
            elif primary_ticker.get(key if tick else ticker_key(v['value']), cid) != cid:
                why = 'OTHER_ENTITY_TICKER'
            elif not tick and key in official_owner and cid not in official_owner[key]:
                why = 'OTHER_ENTITY_OFFICIAL_NAME'
            elif len(owners[tick][key]) > 1 and (tick or cid not in official_owner.get(key, set())):
                why = 'AMBIGUOUS_ACROSS_ENTITIES'
            if why:
                rejections.append({'company_id': cid, 'field': v['field'], 'value': v['value'],
                                   'source': v['source'], 'reason': why})
                continue
            prov = {k: x for k, x in v.items() if k not in ('field', 'locale')}
            if v['field'] == 'official_name':
                rec['official_name'] = prov
                seen.add(key)
            elif v['field'] == 'common_name' and v['locale'] not in rec['common_names']:
                rec['common_names'][v['locale']] = prov
                seen.add(key)
            elif v['field'] == 'historical_name':
                if key not in seen:
                    rec['historical_names'].append(prov)
                    seen.add(key)
            elif v['field'] == 'historical_ticker':
                if key not in seen:
                    rec['historical_tickers'].append(prov)
                    seen.add(key)
            elif key not in seen:
                rec['aliases'].setdefault(v['locale'], []).append(prov)
                seen.add(key)
        records[cid] = rec
    rejections.sort(key=lambda r: (r['company_id'], r['field'], json.dumps(r['value'], ensure_ascii=False), r['source'], r['reason']))
    src_meta = {k: {x: y for x, y in v.items() if x not in ('records', 'rows')} for k, v in sorted(sources.items())}
    return {
        'kind': 'ENTITY_SEARCH_METADATA_REGISTRY', 'schema_version': 1, 'role': ROLE, 'builder': BUILDER,
        'universe_id': universe['universe_id'], 'universe_as_of': universe['as_of'], 'universe_sha256': universe_sha256,
        'note': 'Search/presentation labels only. Not PIT assertions; never inputs to QGV, Technical, Macro, '
                'Portfolio or Leaderboard. Identity = existing company_id bound by Universe CIK.',
        'sources': src_meta, 'records': records, 'rejections': rejections,
    }


def frozen_universe(root=ROOT):
    folder = Path(root) / 'reports/gate_evidence'
    manifest = json.loads((folder / 'track_a_freeze_readiness_2026-09-27.json').read_text())
    name = 'official_snapshot_2024-12-31.json'
    raw = (folder / name).read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    if sha != manifest['evidence_sha256'][name]:
        raise ValueError('frozen Universe hash mismatch')
    prior = [(p.name, json.loads(p.read_text())) for p in sorted(folder.glob('official_snapshot_*.json')) if p.name != name]
    return json.loads(raw), sha, prior


def load_registry(path=None):
    path = Path(path) if path else METADATA_DIR / REGISTRY_NAME
    if not path.exists():
        return None
    reg = json.loads(path.read_text(encoding='utf-8'))
    if reg.get('kind') != 'ENTITY_SEARCH_METADATA_REGISTRY' or reg.get('schema_version') != 1 or reg.get('role') != ROLE:
        raise ValueError('unsupported entity metadata registry')
    return reg


def catalog_fields(registry, company_id, universe):
    """Registry record -> entity_catalog company fields, bound by Universe identity + CIK."""
    if not registry or not universe or universe.get('universe_id') != registry['universe_id']:
        return None
    rec = registry['records'].get(company_id)
    member = next((m for m in universe.get('members', []) if m['company_id'] == company_id), None)
    if not rec or not member or member['cik'] != rec['cik'] or member['ticker'] != rec['ticker']:
        return None
    aliases = {}
    for locale, prov in sorted(rec['common_names'].items()):
        aliases.setdefault(locale, []).append(prov['value'])
    for locale, values in sorted(rec['aliases'].items()):
        aliases.setdefault(locale, []).extend(v['value'] for v in values)
    sources = sorted({p['source'].split(':')[0] for p in [rec['official_name'] or {'source': ''}, *rec['common_names'].values(),
                      *(v for vs in rec['aliases'].values() for v in vs), *rec['historical_names'], *rec['historical_tickers']] if p['source']})
    if not sources:
        return None
    return {
        'official_name': (rec['official_name'] or {}).get('value'),
        'localized_names': {k: v['value'] for k, v in sorted(rec['common_names'].items())},
        'aliases': aliases,
        'historical_names': [v['value'] for v in rec['historical_names']],
        'historical_tickers': [v['value'] for v in rec['historical_tickers']],
        'metadata_provenance': {'registry': REGISTRY_NAME, 'sources': sources},
    }


def coverage(catalog, universe):
    """Field coverage over the Frozen Universe members (counts of 500)."""
    ents = {e['canonical_id']: e for e in catalog['entities'] if e['entity_type'] == 'COMPANY'}
    ids = [m['company_id'] for m in universe['members']]
    def has_name(e):
        return bool(e.get('canonical_label')) and ticker_key(e['canonical_label']) not in {ticker_key(e.get('ticker')), ticker_key(e['canonical_id'])}
    def loc(e, locale):
        return bool(e.get('localized_names', {}).get(locale) or any(
            (HANGUL.search(a) if locale == 'ko-KR' else LATIN.search(a)) for a in e.get('aliases', {}).get(locale, [])))
    checks = {
        'ticker': lambda e: bool(e.get('ticker')),
        'canonical_company_name': has_name,
        'common_english_name': lambda e: loc(e, 'en-US'),
        'ko_KR_company_name': lambda e: bool(HANGUL.search(e.get('localized_names', {}).get('ko-KR') or '')) or any(
            HANGUL.search(a) for a in e.get('aliases', {}).get('ko-KR', [])),
        'aliases': lambda e: any(e.get('aliases', {}).get(l) for l in ('en-US', 'ko-KR')),
        'additional_listing_tickers': lambda e: bool(e.get('aliases', {}).get('und')),
        'historical_names': lambda e: bool(e.get('historical_names')),
        'historical_tickers': lambda e: bool(e.get('historical_tickers')),
        'with_registry_provenance': lambda e: bool(e.get('metadata_provenance')),
    }
    out = {'universe_id': universe['universe_id'], 'n_members': len(ids),
           'n_company_entities': len(ents), 'missing_entities': sorted(set(ids) - set(ents))}
    for k, f in checks.items():
        out[k] = sum(1 for i in ids if i in ents and f(ents[i]))
    return out
