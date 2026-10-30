"""ONE-TIME MEASUREMENT (owner 2026-10-30 supplementary instruction 3). Not part of any pipeline; the branch is deleted after.
Reads SEC bulk files (public; downloaded by the workflow with the declared User-Agent) and prints, per exchange-listed
ticker in SEC's company_tickers_exchange.json, public SEC facts only (no prices): SIC, latest annual form, taxonomy,
cover share count and date, and whether the repository's Q and G axes can be scored in an expanded cross-section.
Output lines: 'SECROW\t...' (one per ticker) and 'SECSUM ...' summaries."""
import io, json, sys, time, zipfile, collections, datetime as dt, gzip, base64, os
sys.path.insert(0, 'implementation/src')
from investment_system.universe import sec_qgv2
from investment_system.qgv import v2_scoring

T0 = time.time()
tick = json.load(open(sys.argv[1]))
fields = tick['fields']; rows = [dict(zip(fields, r)) for r in tick['data']]
mf = json.load(open(sys.argv[2]))
mf_tickers = {r[mf['fields'].index('symbol')] for r in mf['data']} if 'data' in mf else set()
subs_zip = zipfile.ZipFile(sys.argv[3]); facts_zip = zipfile.ZipFile(sys.argv[4])
subs_names = set(subs_zip.namelist()); facts_names = set(facts_zip.namelist())
ex_count = collections.Counter(r.get('exchange') for r in rows)
print('SECSUM exchanges', json.dumps(ex_count), 'mf_tickers', len(mf_tickers), 'load_s', round(time.time() - T0, 1), flush=True)
LISTED = {'Nasdaq', 'NYSE', 'CBOE', 'NYSE American', 'NYSE Arca', 'NYSE MKT', 'BATS'}
by_cik = collections.defaultdict(list)
for r in rows:
    if r.get('exchange') in LISTED:
        by_cik[str(r['cik']).zfill(10)].append(r)
ANNUAL = ('10-K', '10-K/A', '10-KT', '20-F', '20-F/A', '40-F', '40-F/A', 'N-CSR', 'N-CSRS', '1-K')
acquired = dt.datetime(2026, 10, 30, 12, 0, tzinfo=dt.timezone.utc)
universe, meta = {}, {}
t_parse = time.time(); n = 0
for cik, trs in sorted(by_cik.items()):
    n += 1
    sname, fname = f'CIK{cik}.json', f'CIK{cik}.json'
    sb = subs_zip.read(sname) if sname in subs_names else None
    fb = facts_zip.read(fname) if fname in facts_names else None
    sub = json.loads(sb) if sb else {}
    recent = (sub.get('filings') or {}).get('recent') or {}
    forms = recent.get('form') or []
    annual = next((f for f in forms if f in ANNUAL), None)
    shares, shares_date, taxonomy = None, None, None
    if fb:
        facts = json.loads(fb)
        dei = ((facts.get('facts') or {}).get('dei') or {}).get('EntityCommonStockSharesOutstanding') or {}
        vals = [v for v in (dei.get('units') or {}).get('shares', []) if isinstance(v.get('val'), (int, float))]
        if vals:
            last_end = max(v['end'] for v in vals)
            same = [v for v in vals if v['end'] == last_end]
            shares, shares_date = max(v['val'] for v in same), last_end
        taxonomy = 'ifrs-full' if 'ifrs-full' in (facts.get('facts') or {}) else ('us-gaap' if 'us-gaap' in (facts.get('facts') or {}) else None)
    row = sec_qgv2.build_row(cik=cik, companyfacts_body=fb, submissions_body=sb, acquired_at=acquired) if (sb and fb) else sec_qgv2.empty_record(cik=cik, reasons=('NO_SEC_FILES',))
    key = 'X:' + cik
    universe[key] = {'cik': cik, 'state': row.get('state'), 'profile': row.get('profile'), 'industry_group': row.get('industry_group'),
                     'metrics': row.get('metrics') or {}, 'calc_version': row.get('calc_version')}
    meta[key] = dict(sic=sub.get('sic'), entity=sub.get('entityType'), annual=annual, taxonomy=taxonomy, shares=shares,
                     shares_date=shares_date, state=row.get('state'), reason=','.join(row.get('reason_codes') or []),
                     profile=row.get('profile'), fye=row.get('fiscal_year_end'), tickers=trs)
    if n % 500 == 0:
        print('SECSUM progress', n, 'elapsed_s', round(time.time() - t_parse, 1), flush=True)
parse_s = time.time() - t_parse
scores, summary = v2_scoring.score_rows(universe, calc_version=None)
out_rows = []
for key, m in meta.items():
    sc = scores.get(('universe', key)) or {}
    axes = sc.get('axes') or {}
    q = axes.get('Q', {}).get('score'); g = axes.get('G', {}).get('score')
    for t in m['tickers']:
        out_rows.append('\t'.join(str(x) for x in (t['ticker'], t['exchange'], key[2:], m['sic'], m['entity'], m['annual'], m['taxonomy'], m['profile'],
              m['state'], m['reason'] or '-', m['shares'], m['shares_date'], int(q is not None), int(g is not None), m['fye'],
              int(t['ticker'] in mf_tickers))))
blob = base64.b64encode(gzip.compress('\n'.join(out_rows).encode())).decode()
for i in range(0, len(blob), 50000):
    print('SECPACK', i // 50000, blob[i:i + 50000])
print('SECSUM rows', len(out_rows), 'packed_chars', len(blob))
if os.path.exists(os.environ.get('DL_TIMES', '/nonexistent')):
    print('SECSUM downloads', open(os.environ['DL_TIMES']).read().replace('\n', ' | '))
print('SECSUM issuers', len(meta), 'parse_s', round(parse_s, 1), 'per_issuer_ms', round(1000 * parse_s / max(1, len(meta)), 1),
      'cross_section', json.dumps(summary), 'total_s', round(time.time() - T0, 1), flush=True)
