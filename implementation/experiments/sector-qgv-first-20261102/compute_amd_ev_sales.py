"""One-company raw EV/sales from preserved inputs and reviewed official documents.

Offline only. No provider/security-master promotion, percentile score, or price fetch.
Uses point-in-time outstanding shares, never weighted-average diluted shares.
"""
import argparse
import csv
from datetime import date, timedelta, datetime
from decimal import Decimal, localcontext
from fractions import Fraction
import json
from pathlib import Path
import re
from urllib.parse import urlparse, parse_qs
import zipfile
from zoneinfo import ZoneInfo

from audit_existing_archives import digest, write
from investment_system.qgv.qgv2_inputs import normalize

S = '2018-02-16'


def read_verified_results(directory):
    manifest = json.loads((directory / 'manifest.json').read_text())
    for name, expected in manifest['outputs'].items():
        if Path(name).name != name or digest((directory / name).read_bytes()) != expected:
            raise ValueError('CONNECTED_RESULT_HASH_MISMATCH')


def run(root, docs, out):
    out = out.resolve()
    if out.exists() or any((p / '.git').exists() for p in (out, *out.parents)):
        raise ValueError('NEW_PRIVATE_OUTPUT_REQUIRED')
    doc_manifest = json.loads((docs / 'manifest.json').read_text())
    pages = {}
    for source in doc_manifest['sources']:
        path = docs / source['file']
        if Path(source['file']).name != source['file'] or digest(path.read_bytes()) != source['sha256']:
            raise ValueError('DOCUMENT_SNAPSHOT_HASH_MISMATCH')
        pages[source['source_url']] = path.read_text()
    single = 'https://docs.alpaca.markets/us/reference/stockbarsingle-1'
    faq = 'https://ir.amd.com/contacts-faq/faq'
    splits = 'https://ir.amd.com/stock-data/stock-split-history'
    move = 'https://ir.amd.com/news-events/press-releases/detail/585/amd-announces-move-to-nasdaq'
    if not all(x in pages[single] for x in ('Default: USD.', 'raw`: no adjustments',
                                           'symbol mapping is skipped', 'https://data.alpaca.markets/v2/stocks/{symbol}/bars')):
        raise ValueError('REVIEWED_PROVIDER_CONTRACT_CHANGED')
    if 'On 8/21/2000, AMD had a 2-for-1 stock split.' not in pages[faq] or 'all historical stock splits' not in pages[faq]:
        raise ValueError('SPLIT_COVERAGE_NOT_ESTABLISHED')
    if 'January 2, 2015' not in pages[move] or 'continue to trade under the symbol AMD' not in pages[move]:
        raise ValueError('DATED_LISTING_EVIDENCE_CHANGED')
    payment_dates = [datetime.strptime(d, '%m/%d/%y').date() for d in
                     re.findall(r'\| \d{2}/\d{2}/\d{2} \| (\d{2}/\d{2}/\d{2}) \|', pages[splits])]
    if len(payment_dates) != 6 or max(payment_dates) != date(2000, 8, 21):
        raise ValueError('REVIEW_SPLIT_HISTORY')
    connected = root / 'sec-connected-v1'
    read_verified_results(connected)
    evidence = json.loads((connected / 'classification-security-shares.json').read_text())
    shares = evidence['cover_shares']
    if any(date.fromisoformat(shares['period_end']) < d <= date.fromisoformat(S) for d in payment_dates):
        raise ValueError('SPLIT_REQUIRES_REVIEW')
    if shares['security_type'] != 'COMMON' or evidence['listing_observation']['symbol'] != 'AMD':
        raise ValueError('SEC_SECURITY_EVIDENCE_CHANGED')
    financial = json.loads((connected / 'pit-row-with-asfiled-sic.json').read_text())
    normalized = normalize(financial['row'], False)
    v = normalized['v_inputs']
    if v['currency'] != 'USD' or shares['usable_from'] > S:
        raise ValueError('CURRENCY_OR_SHARES_AVAILABILITY')
    amd = root / 'downloads/bt-data-pilot-v06-long-41168930483-1/AMD.zip'
    # Read only the already identified member; no archive inventory/search or network.
    with zipfile.ZipFile(amd) as z:
        stem = 'sip__AMD__2018-01-01__2018-12-31__0__0'
        body = z.read('store/blobs/' + stem)
        price_source = json.loads(z.read('store/manifests/' + stem + '.json'))
        if digest(body) != price_source['sha256']:
            raise ValueError('PRICE_SOURCE_HASH_MISMATCH')
        payload = json.loads(body, parse_float=Decimal)
        request = json.loads(z.read('requests/sip_AMD_2018-01-01_2018-12-31_0_0.json'))['arguments']
    query = parse_qs(urlparse(price_source['source_url']).query)
    for key, expected in (('adjustment', 'raw'), ('feed', 'sip'), ('asof', '-'), ('timeframe', '1Day')):
        if request.get(key) != expected or query.get(key) != [expected]:
            raise ValueError('PRICE_REQUEST_CONTRACT_MISMATCH')
    if 'currency' in query or 'currency' in request or payload.get('currency') not in (None, 'USD'):
        raise ValueError('NONDEFAULT_CURRENCY_REQUIRES_REVIEW')
    if payload['symbol'] != 'AMD' or urlparse(price_source['source_url']).path != '/v2/stocks/AMD/bars':
        raise ValueError('HISTORICAL_DIRECT_SYMBOL_MISMATCH')
    bars = [b for b in payload['bars'] if datetime.fromisoformat(b['t'].replace('Z', '+00:00')).astimezone(
            ZoneInfo('America/New_York')).date().isoformat() == S]
    if len(bars) != 1:
        raise ValueError('SIGNAL_BAR_NOT_UNIQUE')
    close = Decimal(str(bars[0]['c']))
    outstanding = Decimal(shares['value'])
    debt, cash, revenue = (Decimal(str(v[k])) for k in ('total_debt', 'cash', 'revenue'))
    if min(close, outstanding, revenue) <= 0 or outstanding == Decimal(str(v['diluted_shares'])):
        raise ValueError('INVALID_INPUT_OR_SHARE_SUBSTITUTION')
    facts_path = root / 'financial-originals/companyfacts__0000002488'
    if digest(facts_path.read_bytes()) != financial['source']['sha256']:
        raise ValueError('FINANCIAL_SOURCE_HASH_MISMATCH')
    facts = json.loads(facts_path.read_text())['facts']['us-gaap']['SalesRevenueNet']['units']['USD']
    periods = [('2015-12-27', '2016-12-31'), ('2017-01-01', '2017-09-30'), ('2015-12-27', '2016-09-24')]
    lineage = [max((r for r in facts if (r.get('start'), r.get('end')) == span and r['filed'] <= '2018-02-08'),
                   key=lambda r: (r['filed'], r['accn'])) for span in periods]
    if Decimal(lineage[0]['val'] + lineage[1]['val'] - lineage[2]['val']) != revenue:
        raise ValueError('REVENUE_LINEAGE_MISMATCH')
    period_start = (date.fromisoformat(lineage[2]['end']) + timedelta(days=1)).isoformat()
    with localcontext() as ctx:
        ctx.prec = 50
        market_cap = close * outstanding
        ev = market_cap + debt - cash
        multiple = ev / revenue
    # Separate exact rational arithmetic checks the decimal multiply/add path.
    reference = (Fraction(close) * int(outstanding) + Fraction(debt) - Fraction(cash)) / Fraction(revenue)
    if reference != Fraction(ev) / Fraction(revenue):
        raise ValueError('EXACT_ARITHMETIC_MISMATCH')
    row = dict(signal_day=S, issuer_cik='0000002488', security_class='COMMON', provider_symbol='AMD',
               currency='USD', close_usd=str(close), outstanding_shares=str(outstanding),
               shares_as_of=shares['period_end'], shares_filed=shares['filed'], shares_usable_from=shares['usable_from'],
               split_factor='1', market_cap_usd=str(market_cap), debt_usd=str(debt), cash_usd=str(cash),
               ev_usd=str(ev), sales_usd=str(revenue), sales_period_start=period_start,
               sales_period_end=lineage[1]['end'], sales_basis='EXISTING_CALC_23_1_TTM_FY_PLUS_YTD_MINUS_PRIOR_YTD',
               balance_date=normalized['periods']['total_debt'], ev_sales=str(multiple),
               ev_sales_rounded_6dp=str(multiple.quantize(Decimal('0.000001'))),
               ratio_status='COMPUTED_RECONSTRUCTED_ONE_COMPANY', score=None, rank=None,
               c2_status='SEPARATE_BLOCKER_EXISTING_GENERATION_UNCONFIRMED')
    out.mkdir(parents=True, mode=0o700)
    out.chmod(0o700)
    write(out, 'ev-sales-row.json', row)
    with (out / 'ev-sales-row.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(row)); writer.writeheader(); writer.writerow(row)
    (out / 'ev-sales-row.csv').chmod(0o600)
    write(out, 'evidence-and-checks.json', dict(
        official_documents=doc_manifest, price_source=price_source, price_request=request,
        sec_evidence=evidence, financial_source=financial['source'], revenue_components=lineage,
        currency_basis='Official exact endpoint default USD; currency omitted in preserved request',
        identity_basis='Dated 2014 listing transfer + 2017 SEC COMMON cover + 2018-01-30 NASDAQ AMD + documented direct-symbol asof=-',
        identity_scope='RECONSTRUCTED_SAMPLE_JOIN_NOT_GLOBAL_SECURITY_MASTER_OR_ASSET_API_ID',
        split_basis='Issuer FAQ last split 2000-08-21 plus all historical splits table; covers share date to signal',
        current_cusip_not_backdated=True, historical_vendor_delivery_vintage_verified=False,
        financial_basis='Existing calc23.1 PIT inputs retained; later announced 2017 FY earnings numbers not substituted',
        exact_ratio_numerator=reference.numerator, exact_ratio_denominator=reference.denominator,
        fractional_arithmetic_agrees=True, new_price_api_calls=0, new_sec_api_calls=0,
        score_engine_invoked=False, computed_companies=1))
    write(out, 'manifest.json', dict(
        input_hashes={str(p): digest(p.read_bytes()) for p in
                      (connected / 'manifest.json', docs / 'manifest.json', facts_path)},
        output_hashes={p.name: digest(p.read_bytes()) for p in sorted(out.iterdir())}))
    print(json.dumps(dict(computed_companies=1, currency='USD', split_factor=1,
                          sales_period=[period_start, lineage[1]['end']], ev_sales_6dp=row['ev_sales_rounded_6dp'],
                          exact_arithmetic_agrees=True, scores=0)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('root', 'docs', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    run(args.root, args.docs, args.out)
