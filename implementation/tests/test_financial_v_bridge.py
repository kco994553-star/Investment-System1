"""Held evidence connects to the existing evaluator; never invent price/basis."""
from copy import deepcopy
import hashlib
import importlib
import json
from pathlib import Path
import subprocess
import sys

import pytest


def fixture():
    accession = '0000000001-26-000001'
    annual = {'start': '2025-01-01', 'end': '2025-12-31', 'filed': '2026-02-01',
              'form': '10-K', 'accn': accession}
    def fact(value, unit='USD', instant=False):
        row = dict(annual, val=value)
        if instant: row.pop('start')
        return {'units': {unit: [row]}}
    payload = {'cik': 1, 'facts': {'us-gaap': {
        'NetIncomeLoss': fact(40), 'EarningsPerShareDiluted': fact(4, 'USD/shares'),
        'WeightedAverageNumberOfDilutedSharesOutstanding': fact(10, 'shares'),
        'CommonStockholdersEquity': fact(120, instant=True),
        'CommonStockSharesOutstanding': fact(10, 'shares', True),
        'MinorityInterest': fact(0, instant=True),
        'GoodwillAndIntangibleAssetsNet': fact(20, instant=True)}}}
    body = json.dumps(payload).encode()
    cover = b'''<xbrl xmlns="http://www.xbrl.org/2003/instance" xmlns:dei="http://xbrl.sec.gov/dei/2026">
      <context id="c"><entity><identifier scheme="http://www.sec.gov/CIK">0000000001</identifier></entity>
      <period><instant>2026-01-20</instant></period></context>
      <dei:TradingSymbol contextRef="c">TEST</dei:TradingSymbol></xbrl>'''
    record = {'code': 'NYSE:TEST', 'cik': '0000000001', 'sic': '6021',
              'calc_version': 'qgv2-calc/2026-10-23.1', 'acquired_at': '2026-10-31T12:00:00Z',
              'source_sha256': {'companyfacts': hashlib.sha256(body).hexdigest()}}
    shares = {'cik': '0000000001', 'share_class_basis': 'SINGLE_CLASS_CONFIRMED',
              'acquired_at': '2026-10-31T12:00:00Z',
              'measurement_date': '2026-01-20', 'filed': '2026-02-01',
              'source_sha256': {'cover': hashlib.sha256(cover).hexdigest()}}
    return {'record': record, 'companyfacts_bytes': body, 'shares': shares, 'cover_bytes': cover,
            'valuation_date': '2026-11-02', 'input_vintage': '2026-11-04T12:00:00Z'}


def connect(**kwargs):
    try: module = importlib.import_module('investment_system.research.financial_v_bridge')
    except ModuleNotFoundError: pytest.fail('held-evidence candidate bridge is not implemented')
    return module.connect(**kwargs)


def price(basis, date='2026-11-02'):
    return {'code': 'NYSE:TEST', 'cik': '0000000001', 'value': 40, 'date': date,
            'currency': 'USD', 'unit': 'USD/share', 'share_basis': basis,
            'source': {'sha256': 'a'*64, 'json_pointer': '/synthetic/trade'},
            'basis_source': {'sha256': 'b'*64, 'json_pointer': '/synthetic/basis'}}


def test_held_fact_extraction_computes_each_metric_on_its_own_documented_price_basis():
    x = fixture()
    x['prices'] = {
        'earnings_yield': price('FY0:0000000001-26-000001:2026-02-01'),
        'book_yield': price('BALANCE_COMMON:0000000001-26-000001'),
        'tangible_book_yield': price('BALANCE_COMMON:0000000001-26-000001')}
    result = connect(**x)
    assert [result['result']['metrics'][m]['value'] for m in
            ('earnings_yield', 'book_yield', 'tangible_book_yield')] == [0.1, 0.3, 0.25]
    assert result['result']['primary_available']
    assert result['result']['score'] is None and result['result']['rank'] is None
    assert result['inputs']['earnings_yield']['source']['companyfacts_sha256'] == x['record']['source_sha256']['companyfacts']


def test_missing_prices_preserve_real_numerators_and_emit_no_ratios():
    r = connect(**fixture())
    assert r['inputs']['earnings_yield']['value'] == 4
    assert r['inputs']['book_yield']['value'] == 12
    assert all(m['value'] is None for m in r['result']['metrics'].values())
    assert not r['result']['primary_available']
    assert 'PRICE_UNAVAILABLE' in r['result']['metrics']['earnings_yield']['reasons']


@pytest.mark.parametrize('change,reason', [
    ({'date': '2025-12-31'}, 'PRICE_DATE_MISMATCH'),
    ({'share_basis': 'unproven'}, 'SHARE_BASIS_UNCONFIRMED'),
    ({'basis_source': None}, 'PRICE_BASIS_SOURCE_UNCONFIRMED'),
    ({'cik': '0000000002'}, 'PRICE_IDENTITY_MISMATCH')])
def test_price_date_basis_and_issuer_fail_closed(change, reason):
    x = fixture(); quote = price('FY0:0000000001-26-000001:2026-02-01'); quote.update(change)
    x['prices'] = {'earnings_yield': quote}
    r = connect(**x)
    assert r['result']['metrics']['earnings_yield']['value'] is None
    assert reason in r['result']['metrics']['earnings_yield']['reasons']


def test_hash_mismatch_and_foreign_companyfacts_are_not_consumed():
    x = fixture(); x['companyfacts_bytes'] += b' '
    with pytest.raises(ValueError, match='COMPANYFACTS_HASH'): connect(**x)
    x = fixture(); body = json.loads(x['companyfacts_bytes']); body['cik'] = 2
    x['companyfacts_bytes'] = json.dumps(body).encode()
    x['record']['source_sha256']['companyfacts'] = hashlib.sha256(x['companyfacts_bytes']).hexdigest()
    with pytest.raises(ValueError, match='COMPANYFACTS_CIK'): connect(**x)


def test_foreign_cover_and_future_class_proof_do_not_confirm_security():
    for foreign in (True, False):
        x = fixture()
        if foreign:
            x['cover_bytes'] = x['cover_bytes'].replace(b'0000000001', b'0000000002')
            x['shares']['source_sha256']['cover'] = hashlib.sha256(x['cover_bytes']).hexdigest()
        else: x['shares']['measurement_date'] = '2026-11-03'
        x['prices'] = {'earnings_yield': price('FY0:0000000001-26-000001:2026-02-01')}
        r = connect(**x)
        assert r['result']['metrics']['earnings_yield']['value'] is None
        assert r['result']['security_basis']['status'] != 'SINGLE_CLASS_CONFIRMED'


def test_post_valuation_filing_does_not_replace_the_available_annual_eps():
    x = fixture(); facts = json.loads(x['companyfacts_bytes'])
    rows = facts['facts']['us-gaap']['EarningsPerShareDiluted']['units']['USD/shares']
    rows.append(dict(rows[0], val=9, filed='2026-11-03', accn='0000000001-26-000002'))
    x['companyfacts_bytes'] = json.dumps(facts).encode()
    x['record']['source_sha256']['companyfacts'] = hashlib.sha256(x['companyfacts_bytes']).hexdigest()
    x['record']['acquired_at'] = '2026-11-04T00:00:00Z'
    assert connect(**x)['inputs']['earnings_yield']['value'] == 4


@pytest.mark.parametrize('source', ['record', 'shares'])
def test_capture_after_input_vintage_on_same_day_is_rejected(source):
    x = fixture()
    x[source]['acquired_at'] = '2026-11-04T12:00:01Z'
    with pytest.raises(ValueError, match='INPUT_VINTAGE_NOT_ELIGIBLE'):
        connect(**x)


@pytest.mark.parametrize('stamp', [None, '2026-10-31', '2026-10-31T12:00:00'])
def test_missing_or_timezone_unknown_capture_is_rejected(stamp):
    x = fixture(); x['shares']['acquired_at'] = stamp
    with pytest.raises(ValueError, match='CAPTURE_TIMESTAMP_REQUIRED'):
        connect(**x)


def test_cli_hash_pins_sources_writes_private_output_and_rejects_duplicate_codes(tmp_path):
    x = fixture()
    def save(name, body):
        (tmp_path/name).write_bytes(body)
        return {'path': name, 'sha256': hashlib.sha256(body).hexdigest()}
    records = {'NYSE:TEST': {k:v for k,v in x['record'].items() if k!='code'}}
    records['NYSE:TEST']['profile'] = 'FINANCIAL'
    records.update({f'SYNTHETIC:{i}': {'profile': 'GENERAL'} for i in range(503)})
    manifest = {'valuation_date': x['valuation_date'], 'input_vintage': x['input_vintage'],
                'universe': save('universe.json', json.dumps({'records': records}).encode()),
                'shares': save('shares.json', json.dumps({'records': {'NYSE:TEST': x['shares']}}).encode()),
                'issuers': [{'code': 'NYSE:TEST', 'companyfacts': save('facts.json', x['companyfacts_bytes']),
                             'cover': save('cover.xml', x['cover_bytes'])}]}
    (tmp_path/'manifest.json').write_text(json.dumps(manifest))
    script = Path(__file__).resolve().parents[1]/'tools/financial_v_connect.py'
    command = [sys.executable, str(script), '--manifest', str(tmp_path/'manifest.json'), '--output', str(tmp_path/'out.json')]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    output = json.loads((tmp_path/'out.json').read_text())
    assert output['summary']['operational_denominator'] == 504
    assert output['summary']['financial_codes'] == 1
    assert output['rows'][0]['inputs']['earnings_yield']['value'] == 4
    assert (tmp_path/'out.json').stat().st_mode & 0o777 == 0o600
    assert subprocess.run(command, capture_output=True).returncode != 0
    manifest['issuers'] *= 2; (tmp_path/'manifest.json').write_text(json.dumps(manifest))
    command[-1] = str(tmp_path/'bad.json')
    assert subprocess.run(command, capture_output=True).returncode != 0
    assert not (tmp_path/'bad.json').exists()
