"""ONE-TIME MEASUREMENT (owner 2026-10-30 supplementary instruction 3), second pass. Not part of any pipeline; the branch
is deleted after. Prints, per exchange-listed CIK in SEC's company_tickers_exchange.json, the latest dei:EntityPublicFloat
(public SEC cover fact, USD) and its date, plus the public SEC fund-ticker list (company_tickers_mf.json), so size buckets
can be formed without any market price. Output: 'FLOATPACK <i> <base64 gzip TSV>' and 'MFPACK <i> <base64 gzip>' lines."""
import json, sys, time, zipfile, gzip, base64

T0 = time.time()
tick = json.load(open(sys.argv[1])); fields = tick['fields']
rows = [dict(zip(fields, r)) for r in tick['data']]
mf = json.load(open(sys.argv[2])); mfi = mf['fields'].index('symbol')
mf_tickers = sorted({r[mfi] for r in mf['data'] if r[mfi]})
facts_zip = zipfile.ZipFile(sys.argv[3]); names = set(facts_zip.namelist())
LISTED = {'Nasdaq', 'NYSE', 'CBOE', 'NYSE American', 'NYSE Arca', 'NYSE MKT', 'BATS'}
ciks = sorted({str(r['cik']).zfill(10) for r in rows if r.get('exchange') in LISTED})
out = []
for cik in ciks:
    name = f'CIK{cik}.json'
    if name not in names:
        out.append(f'{cik}\tNone\tNone'); continue
    dei = ((json.loads(facts_zip.read(name)).get('facts') or {}).get('dei') or {}).get('EntityPublicFloat') or {}
    vals = [v for v in (dei.get('units') or {}).get('USD', []) if isinstance(v.get('val'), (int, float))]
    if not vals:
        out.append(f'{cik}\tNone\tNone'); continue
    last = max(v['end'] for v in vals)
    out.append(f'{cik}\t{max(v["val"] for v in vals if v["end"] == last)}\t{last}')
for tag, payload in (('FLOATPACK', '\n'.join(out)), ('MFPACK', '\n'.join(mf_tickers))):
    blob = base64.b64encode(gzip.compress(payload.encode())).decode()
    for i in range(0, len(blob), 50000):
        print(tag, i // 50000, blob[i:i + 50000])
print('FLOATSUM ciks', len(ciks), 'with_float', sum(1 for o in out if not o.endswith('None')), 'mf_tickers', len(mf_tickers),
      'total_s', round(time.time() - T0, 1), flush=True)
