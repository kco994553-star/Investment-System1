"""Offline connection of the three approved SEC responses; private evidence and PIT row.

No price collection, score calculation, currency inference, or diluted-share
substitution for point-in-time shares outstanding. Existing artifacts stay intact.
"""
import argparse
from datetime import date
import html
import json
from pathlib import Path
import re

from audit_existing_archives import archive, artifact, digest, write
from investment_system.research.exp_deciles import pit, schedule

CIK = '0000002488'
S = '2018-02-16'


def plain(text):
    return ' '.join(html.unescape(re.sub('<[^>]+>', ' ', text)).split())


def documents(text):
    return {re.search(r'<TYPE>([^\n]+)', d)[1].strip(): plain(re.search(r'<TEXT>(.*?)</TEXT>', d, re.S)[1])
            for d in re.findall(r'<DOCUMENT>(.*?)</DOCUMENT>', text, re.S)
            if re.search(r'<TYPE>([^\n]+)', d) and re.search(r'<TEXT>(.*?)</TEXT>', d, re.S)}


def header(text, source):
    h = text.split('</SEC-HEADER>', 1)[0]
    cik = re.search(r'CENTRAL INDEX KEY:\s*(\d+)', h)[1]
    if cik != CIK:
        raise ValueError('SOURCE_CIK_MISMATCH')
    filed = date.fromisoformat(re.search(r'FILED AS OF DATE:\s*(\d{8})', h)[1]).isoformat()
    return dict(cik=cik, accn=re.search(r'ACCESSION NUMBER:\s*([^\s]+)', h)[1],
                sic=re.search(r'STANDARD INDUSTRIAL CLASSIFICATION:[^\n]+\[(\d{4})\]', h)[1],
                filed=filed, accepted_ny_raw=re.search(r'<ACCEPTANCE-DATETIME>(\d+)', h)[1],
                usable_from=schedule.usable_from(filed).isoformat(), source=source)


def run(sec, prior, facts_path, amd, out):
    out = out.resolve()
    if out.exists() or any((p / '.git').exists() for p in (out, *out.parents)):
        raise ValueError('NEW_PRIVATE_OUTPUT_REQUIRED')
    receipts, bodies = {}, {}
    for key in ('submission', 'history', 'identity'):
        receipt = json.loads((sec / (key + '.receipt.json')).read_text())
        body = (sec / (key + '.response')).read_bytes()
        if receipt['http_status'] != 200 or digest(body) != receipt['sha256']:
            raise ValueError('SEC_RESPONSE_HASH_OR_STATUS_INVALID')
        receipts[key], bodies[key] = receipt, body
    old = json.loads((prior / 'manifest.json').read_text())
    for name, expected in old['outputs'].items():
        if Path(name).name != name or digest((prior / name).read_bytes()) != expected:
            raise ValueError('PRIOR_OUTPUT_HASH_MISMATCH')
    old_financial = json.loads((prior / 'pit-financial-rows.json').read_text())[CIK]
    if digest(facts_path.read_bytes()) != old_financial['source']['sha256']:
        raise ValueError('COMPANYFACTS_HASH_MISMATCH')
    headers = [header(bodies[k].decode(), receipts[k]) for k in ('submission', 'identity')]
    docs = {k: documents(bodies[k].decode()) for k in ('submission', 'identity')}
    cover = docs['submission']['10-Q'].split('INDEX Page No.', 1)[0]
    match = re.search(r'common stock, \$0\.01 par value, as of (October 27, 2017)\s*:\s*([\d,]+)', cover)
    if not match or 'NASDAQ:AMD' not in docs['identity']['EX-99.1']:
        raise ValueError('REVIEWED_COVER_OR_TICKER_EVIDENCE_CHANGED')
    shares = dict(value=int(match[2].replace(',', '')), unit='shares', security_type='COMMON',
                  par_value_usd='0.01', period_end='2017-10-27', filed=headers[0]['filed'],
                  usable_from=headers[0]['usable_from'], source=receipts['submission'],
                  basis='POINT_IN_TIME_OUTSTANDING_NOT_WEIGHTED_AVERAGE',
                  status='COVER_VERIFIED_PRICE_BASIS_UNCONFIRMED')
    sic = pit.as_filed_sic(headers, S, CIK)
    row = pit.compute_row(json.loads(facts_path.read_text()), sic_record=sic, signal_day=S, cik=CIK, security_id=None)
    history = json.loads(bodies['history'])
    historical_rows = [{k: history[k][i] for k in ('accessionNumber', 'filingDate', 'form', 'items', 'primaryDocument')}
                       for i, d in enumerate(history['filingDate']) if '2017-09-30' <= d <= S]
    recent = json.loads((sec.parent / 'target-accession-v1/stored-submissions-coverage.json').read_text())
    filings = sorted(historical_rows + recent['filings'], key=lambda r: (r['filingDate'], r['accessionNumber']))
    with archive(amd) as z:
        body, price_source = artifact(z, 'store', 'sip:AMD:2018-01-01:2018-12-31:0:0')
        payload = json.loads(body)
        request = json.loads(z.read('requests/sip_AMD_2018-01-01_2018-12-31_0_0.json'))['arguments']
        bars = [b for b in payload['bars'] if b['t'][:10] == S]
        if len(bars) != 1 or payload['symbol'] != 'AMD' or request['adjustment'] != 'raw':
            raise ValueError('REVIEWED_PRICE_INPUT_CHANGED')
    out.mkdir(parents=True, mode=0o700)
    out.chmod(0o700)
    classification = dict(fixed_issuer_id='SEC-CIK:' + CIK, security_id=None, observations=headers,
                          source_system='SEC_SIC', source_code=sic['sic'], selected_observation=sic,
                          effective_start=None, effective_start_status='UNKNOWN_NOT_IN_SOURCE',
                          book_sector='INFORMATION_TECHNOLOGY', mapping_status='RESEARCH_CORRESPONDENCE',
                          mapping_version='book10-sic-observed-evidence-v2-20261102',
                          mapping_basis='SIC 3674 semiconductors and related devices; chapter 24 information technology description',
                          book_reference='Previously verified Table 24.19; EV/sales is NEW_FACTOR_ADDITION',
                          cover_shares=shares,
                          listing_observation=dict(exchange='NASDAQ', symbol='AMD', filed=headers[1]['filed'],
                                                   usable_from=headers[1]['usable_from'], source=receipts['identity']),
                          historical_provider_security_binding='NOT_CONFIRMED_THROUGH_SIGNAL_DAY')
    price = dict(source=price_source, request=request, bars=bars,
                 adjustment_status='RAW_REQUEST_AND_MANIFEST_CONFIRMED',
                 currency=None, currency_status='NOT_IN_REQUEST_RESPONSE_OR_MANIFEST',
                 code_default_usd='ADAPTER_AND_OLD_PILOT_LITERAL_NOT_SOURCE_CONFIRMATION',
                 share_price_basis='UNCONFIRMED')
    event_scan = dict(window=['2017-09-30', S], metadata_filings=filings,
                      full_originals_read=[headers[0]['accn'], headers[1]['accn']],
                      searched_terms=['stock split', 'reverse split', 'merger', 'trading symbol', 'NASDAQ'],
                      conclusion='확인 범위에서 분할·신원 변경 공시가 발견되지 않음',
                      completeness='LIMITED_REVIEW_NOT_PROOF_OF_NO_EVENTS_OR_COMPLETE_PRICE_BASIS')
    readiness = dict(signal_day=S, target_issuers=1, market_cap=None, ev_sales=None, ev_fcf=None,
                     market_cap_shares=shares, diluted_shares_substituted=False,
                     intended_ev_formula='S close * point-in-time shares outstanding + debt - cash',
                     verified_ratio_count=0, scores_computed=0, score_engine_invoked=False,
                     stages=dict(classification=1, security_valid_at_signal=0, price_financial_join=0,
                                 raw_ratio=0, baseline_candidate_scores=0),
                     remaining=['QUOTE_CURRENCY_SOURCE_MISSING', 'SECURITY_PROVIDER_INTERVAL_UNCONFIRMED',
                                'SHARE_PRICE_BASIS_UNCONFIRMED'],
                     separate_score_blocker='COMPLETE_C2_MANIFEST_EXISTING_GENERATION_UNCONFIRMED')
    write(out, 'classification-security-shares.json', classification)
    write(out, 'price-basis-audit.json', price)
    write(out, 'filing-window-review.json', event_scan)
    write(out, 'pit-row-with-asfiled-sic.json', dict(source=old_financial['source'], row=row))
    write(out, 'ratio-readiness.json', readiness)
    write(out, 'manifest.json', dict(
        inputs={str(p): digest(p.read_bytes()) for p in (facts_path, amd, prior / 'manifest.json',
                sec / 'submission.response', sec / 'history.response', sec / 'identity.response',
                sec.parent / 'target-accession-v1/stored-submissions-coverage.json')},
        outputs={p.name: digest(p.read_bytes()) for p in sorted(out.glob('*.json'))}))
    print(json.dumps(dict(stages=readiness['stages'], source_sic=sic['sic'],
                         pit_reason_codes=row['reason_codes'], metadata_filings=len(filings),
                         successful_gets=3, score_engine_invoked=False)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('sec', 'prior', 'facts', 'amd', 'out'):
        parser.add_argument('--' + key, type=Path, required=True)
    args = parser.parse_args()
    run(args.sec, args.prior, args.facts, args.amd, args.out)
