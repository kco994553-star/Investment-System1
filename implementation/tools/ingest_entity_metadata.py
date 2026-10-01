"""Entity search metadata ingestion (network runner) + deterministic registry build.

  python tools/ingest_entity_metadata.py fetch   # network: SEC, Wikidata, KIS masters -> sources/*.json
  python tools/ingest_entity_metadata.py build   # offline: sources + Frozen Universe -> registry + coverage

The Claude cloud container denies sec.gov / wikidata.org egress, so `fetch` runs on a
GitHub-hosted runner (.github/workflows/entity-metadata-ingest.yml), the same pattern as
c21-real-data. Only small extracts with per-response URL/sha256/fetched_at (and Wikidata
item revision ids) are committed. Raw responses are kept in the workflow artifact.
Nothing here is an input to QGV/Technical/Macro/Portfolio/Leaderboard.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from investment_system.product import entity_metadata as em  # noqa: E402

FETCHER = 'tools/ingest_entity_metadata.py v1'
SEC_UA = os.environ.get('INVESTMENT_SYSTEM_SEC_UA', '')
WD_UA = 'Investment-System1-entity-metadata/1.0 (https://github.com/kco994553-star/Investment-System1)'
SEC_SUBMISSIONS = 'https://data.sec.gov/submissions/CIK{cik}.json'
SEC_TICKERS = 'https://www.sec.gov/files/company_tickers.json'
WD_SPARQL = 'https://query.wikidata.org/sparql'
KIS_MASTERS = {ex: f'https://new.real.download.dws.co.kr/common/master/{ex.lower()}mst.cod.zip' for ex in ('NAS', 'NYS', 'AMS')}
# KIS overseas master (tab separated, cp949): column order of the KIS open-trading-api sample loader.
KIS_COLS = ('national_code', 'exchange_id', 'exchange_code', 'exchange_name', 'symbol', 'realtime_symbol',
            'ko_name', 'en_name', 'security_type')


def now():
    return datetime.now(timezone.utc).isoformat()


def get(url, headers, data=None, tries=4):
    for i in range(tries):
        try:
            req = Request(url, data=data, headers=headers)
            with urlopen(req, timeout=60) as r:
                return r.read(), r.status
        except Exception as e:  # noqa: BLE001 - recorded, retried, then surfaced
            err = e
            time.sleep(2 ** i)
    raise err


def write(raw_dir, name, body):
    if raw_dir:
        p = Path(raw_dir) / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(body)


def fetch_sec(ciks, raw_dir):
    if not SEC_UA:
        raise SystemExit('INVESTMENT_SYSTEM_SEC_UA is required (SEC fair-access policy)')
    h = {'User-Agent': SEC_UA, 'Accept': 'application/json'}
    records, failures = {}, []
    for cik in ciks:
        url = SEC_SUBMISSIONS.format(cik=cik)
        try:
            body, status = get(url, h)
        except Exception as e:  # noqa: BLE001
            failures.append({'cik': cik, 'error': type(e).__name__ + ': ' + str(e)[:200]})
            continue
        write(raw_dir, f'sec_submissions/CIK{cik}.json', body)
        d = json.loads(body)
        if str(d.get('cik', '')).zfill(10) != cik:
            failures.append({'cik': cik, 'error': 'CIK_MISMATCH'})
            continue
        records[cik] = {'source_url': url, 'sha256': hashlib.sha256(body).hexdigest(), 'fetched_at': now(),
                        'http_status': status, 'name': d.get('name'), 'tickers': d.get('tickers') or [],
                        'exchanges': d.get('exchanges') or [], 'formerNames': d.get('formerNames') or []}
        time.sleep(0.15)  # < 10 req/s
    body, status = get(SEC_TICKERS, h)
    write(raw_dir, 'sec_company_tickers.json', body)
    want = set(ciks)
    rows = sorted(({'cik': str(r['cik_str']).zfill(10), 'ticker': r['ticker'], 'title': r['title']}
                   for r in json.loads(body).values() if str(r['cik_str']).zfill(10) in want),
                  key=lambda r: (r['cik'], r['ticker']))
    sub = {'source_kind': 'SEC_SUBMISSIONS', 'url_template': SEC_SUBMISSIONS, 'fetcher': FETCHER,
           'license': 'U.S. SEC EDGAR public data', 'n_requested': len(ciks), 'failures': failures, 'records': records}
    tick = {'source_kind': 'SEC_COMPANY_TICKERS', 'source_url': SEC_TICKERS, 'fetcher': FETCHER, 'fetched_at': now(),
            'sha256': hashlib.sha256(body).hexdigest(), 'http_status': status,
            'license': 'U.S. SEC EDGAR public data', 'rows': rows}
    return sub, tick


def sparql(query, raw_dir, name):
    body, status = get(WD_SPARQL, {'User-Agent': WD_UA, 'Accept': 'application/sparql-results+json',
                                   'Content-Type': 'application/x-www-form-urlencoded'},
                       data=urlencode({'query': query}).encode())
    write(raw_dir, f'wikidata/{name}.json', body)
    return json.loads(body)['results']['bindings'], {'sha256': hashlib.sha256(body).hexdigest(), 'http_status': status,
                                                     'fetched_at': now(), 'query': query}


def fetch_wikidata(ciks, raw_dir):
    # P5531 = SEC Central Index Key. Both padded and unpadded literal forms are matched.
    values = ' '.join(f'"{c}" "{int(c)}"' for c in ciks)
    v = lambda b, k: b[k]['value'] if k in b else None  # noqa: E731
    q_items = f'''SELECT ?item ?cik ?en ?ko ?rev WHERE {{ VALUES ?cik {{ {values} }} ?item wdt:P5531 ?cik .
      OPTIONAL {{ ?item rdfs:label ?en FILTER(LANG(?en)="en") }} OPTIONAL {{ ?item rdfs:label ?ko FILTER(LANG(?ko)="ko") }}
      OPTIONAL {{ ?item schema:version ?rev }} }}'''
    q_alias = f'''SELECT ?item ?alias WHERE {{ VALUES ?cik {{ {values} }} ?item wdt:P5531 ?cik .
      ?item skos:altLabel ?alias FILTER(LANG(?alias) IN ("en","ko")) }}'''
    q_tick = f'''SELECT ?item ?exchange ?symbol ?start ?end WHERE {{ VALUES ?cik {{ {values} }} ?item wdt:P5531 ?cik .
      ?item p:P414 ?st . ?st ps:P414 ?exchange . ?st pq:P249 ?symbol .
      OPTIONAL {{ ?st pq:P580 ?start }} OPTIONAL {{ ?st pq:P582 ?end }} }}'''
    meta, items = {}, {}
    rows, meta['items'] = sparql(q_items, raw_dir, 'items')
    for b in rows:
        qid = v(b, 'item').rsplit('/', 1)[-1]
        r = items.setdefault(qid, {'item': qid, 'cik': str(int(v(b, 'cik'))).zfill(10), 'en_label': v(b, 'en'),
                                   'ko_label': v(b, 'ko'), 'revision': v(b, 'rev'), 'en_aliases': [], 'ko_aliases': [],
                                   'tickers': []})
    rows, meta['aliases'] = sparql(q_alias, raw_dir, 'aliases')
    for b in rows:
        qid = v(b, 'item').rsplit('/', 1)[-1]
        lang = b['alias'].get('xml:lang')
        if qid in items and lang in ('en', 'ko'):
            items[qid][lang + '_aliases'].append(v(b, 'alias'))
    rows, meta['tickers'] = sparql(q_tick, raw_dir, 'tickers')
    for b in rows:
        qid = v(b, 'item').rsplit('/', 1)[-1]
        if qid in items:
            items[qid]['tickers'].append({'exchange': v(b, 'exchange').rsplit('/', 1)[-1], 'symbol': v(b, 'symbol'),
                                          'start': v(b, 'start'), 'end': v(b, 'end')})
    for r in items.values():
        r['en_aliases'] = sorted(set(r['en_aliases']))
        r['ko_aliases'] = sorted(set(r['ko_aliases']))
        r['tickers'] = sorted({json.dumps(t, sort_keys=True) for t in r['tickers']})
        r['tickers'] = [json.loads(t) for t in r['tickers']]
        r['revision_url'] = f"https://www.wikidata.org/w/index.php?title={r['item']}&oldid={r['revision']}" if r['revision'] else None
    return {'source_kind': 'WIKIDATA_SPARQL', 'endpoint': WD_SPARQL, 'fetcher': FETCHER, 'license': 'CC0 1.0',
            'match_property': 'P5531 (SEC CIK)', 'queries': meta,
            'rows': sorted(items.values(), key=lambda r: (r['cik'], r['item']))}


def fetch_kis(symbols, raw_dir):
    files, rows, failures = [], [], []
    want = {em.ticker_key(s) for s in symbols}
    for ex, url in KIS_MASTERS.items():
        try:
            body, status = get(url, {'User-Agent': WD_UA})
        except Exception as e:  # noqa: BLE001
            failures.append({'url': url, 'error': type(e).__name__ + ': ' + str(e)[:200]})
            continue
        write(raw_dir, f'kis/{ex}.zip', body)
        files.append({'exchange': ex, 'source_url': url, 'sha256': hashlib.sha256(body).hexdigest(),
                      'fetched_at': now(), 'http_status': status})
        with zipfile.ZipFile(io.BytesIO(body)) as z:
            text = z.read(z.namelist()[0]).decode('cp949', errors='strict')
        for line in text.splitlines():
            cols = line.split('\t')
            if len(cols) < len(KIS_COLS):
                continue
            r = dict(zip(KIS_COLS, (c.strip() for c in cols)))
            if em.ticker_key(r['symbol']) in want:
                rows.append({'exchange': ex, 'symbol': r['symbol'], 'ko_name': r['ko_name'], 'en_name': r['en_name'],
                             'security_type': r['security_type']})
    return {'source_kind': 'KIS_OVERSEAS_STOCK_MASTER', 'fetcher': FETCHER, 'columns': list(KIS_COLS),
            'note': 'Korea Investment & Securities public overseas master files; matched only on SEC-issued tickers '
                    'of the Universe CIK and English-name cross-check.',
            'files': files, 'failures': failures, 'rows': sorted(rows, key=lambda r: (r['symbol'], r['exchange']))}


def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=True) + '\n', encoding='utf-8')


def cmd_fetch(a):
    u, _, _ = em.frozen_universe()
    ciks = sorted({m['cik'] for m in u['members']})
    out = em.SOURCES_DIR
    status = {}
    sub, tick = fetch_sec(ciks, a.raw_dir)
    dump(out / em.SOURCE_FILES['sec_submissions'], sub)
    dump(out / em.SOURCE_FILES['sec_company_tickers'], tick)
    status['sec'] = {'ok': len(sub['records']), 'failed': len(sub['failures'])}
    for key, fn, arg in (('wikidata', fetch_wikidata, ciks),
                         ('kis_master', fetch_kis, sorted({t for r in sub['records'].values() for t in r['tickers']}
                                                          | {r['ticker'] for r in tick['rows']}))):
        try:
            res = fn(arg, a.raw_dir)
            dump(out / em.SOURCE_FILES[key], res)
            status[key] = {'rows': len(res['rows'])}
        except Exception as e:  # noqa: BLE001 - optional source; recorded, never faked
            status[key] = {'error': type(e).__name__ + ': ' + str(e)[:300]}
    print(json.dumps(status, indent=1))


def cmd_build(a):
    from investment_system.product.entity_catalog import NAV_ENTITIES
    u, sha, prior = em.frozen_universe()
    reserved = [x for e in NAV_ENTITIES for x in [e['canonical_label'], *e.get('localized_names', {}).values(),
                *(v for vs in e.get('aliases', {}).values() for v in vs)]]
    reg = em.build_registry(u, em.load_sources(), sha, prior, reserved)
    dump(em.METADATA_DIR / em.REGISTRY_NAME, reg)
    from investment_system.product.entity_catalog import entity_catalog
    from investment_system.product.web_mvp import repository_bundle
    cov = em.coverage(entity_catalog(repository_bundle()), u)
    cov['n_rejections'] = len(reg['rejections'])
    dump(em.METADATA_DIR / 'coverage_2024-12-31.json', cov)
    print(json.dumps(cov, indent=1))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('command', choices=('fetch', 'build'))
    p.add_argument('--raw-dir', help='optional directory for raw response bytes (workflow artifact)')
    a = p.parse_args()
    {'fetch': cmd_fetch, 'build': cmd_build}[a.command](a)


if __name__ == '__main__':
    main()
