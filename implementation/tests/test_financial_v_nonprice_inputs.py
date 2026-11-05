"""Synthetic balance observations remain distinct from candidate eligibility."""
from copy import deepcopy
from datetime import date
import json
import hashlib
import importlib.util
from pathlib import Path

import pytest

from investment_system.research import financial_v as fv
from investment_system.research.financial_v_bridge import connect
from .test_financial_v_bridge import fixture, price


def facts():
    def item(value, unit='USD'):
        return {'units': {unit: [{'val': value, 'end': '2026-06-30',
            'filed': '2026-08-01', 'form': '10-Q', 'accn': 'synthetic-a'}]}}
    return {'cik': 1, 'facts': {'us-gaap': {
        'CommonStockholdersEquity': item(120),
        'CommonStockSharesOutstanding': item(10, 'shares'),
        'MinorityInterest': item(0),
        'IntangibleAssetsNetIncludingGoodwill': item(20)}}}


def proof():
    return dict(status='SINGLE_CLASS_CONFIRMED', cik='0000000001',
                date='2026-08-01', source='synthetic:cover')


def test_standard_combined_intangibles_tag_connects_without_changing_formula():
    result = fv.common_book_inputs(facts(), date(2026, 11, 2), proof())
    assert result['book_yield']['value'] == 12
    assert result['tangible_book_yield']['value'] == 10


def test_conflicting_combined_intangible_aliases_fail_closed():
    f = facts(); tax = f['facts']['us-gaap']
    tax['GoodwillAndIntangibleAssetsNet'] = deepcopy(tax['IntangibleAssetsNetIncludingGoodwill'])
    tax['GoodwillAndIntangibleAssetsNet']['units']['USD'][0]['val'] = 30
    assert fv.common_book_inputs(f, date(2026, 11, 2), proof())['tangible_book_yield'] is None


def test_conflict_cannot_fall_back_to_a_different_intangible_composition():
    f = facts(); t = f['facts']['us-gaap']
    rows = t['IntangibleAssetsNetIncludingGoodwill']['units']['USD']
    rows.append(dict(rows[0], val=30))
    for tag, value in [('Goodwill', 10), ('IntangibleAssetsNetExcludingGoodwill', 10)]:
        t[tag] = {'units': {'USD': [dict(rows[0], val=value)]}}
    assert fv.common_book_inputs(f, date(2026, 11, 2), proof())['tangible_book_yield'] is None


def test_components_connect_before_class_gate_but_do_not_become_common_equity():
    f = facts(); tax = f['facts']['us-gaap']
    tax['StockholdersEquity'] = tax.pop('CommonStockholdersEquity')
    p = proof(); p['status'] = 'BASIS_UNCONFIRMED'
    audit = fv.balance_input_audit(f, date(2026, 11, 2), p, 'tangible_book_yield')
    assert audit['components']['parent_equity']['value'] == 120
    assert audit['components']['parent_equity']['status'] == 'ELIGIBLE_OBSERVATION'
    assert audit['components']['parent_equity']['source']['json_pointers'] == ['/facts/us-gaap/StockholdersEquity/units/USD/0']
    assert audit['components']['preferred_shares']['value'] is None
    assert audit['components']['preferred_shares']['status'] == 'NOT_PRESENT_IN_HELD_SOURCE'
    assert audit['class_status'] == 'BASIS_UNCONFIRMED'
    assert fv.common_book_inputs(f, date(2026, 11, 2), p)['book_yield'] is None


@pytest.mark.parametrize('change,reason', [
    ({'filed': '2026-11-03'}, 'FILED_AFTER_CUTOFF'),
    ({'end': '2024-01-01'}, 'PERIOD_NOT_ELIGIBLE'),
    ({'start': '2026-01-01'}, 'INSTANT_REQUIRED'),
    ({'accn': 'another'}, 'ANCHOR_MISMATCH'),
    ({'val': float('nan')}, 'NONFINITE_VALUE')])
def test_bad_observations_are_classified_without_filling(change, reason):
    f = facts(); f['facts']['us-gaap']['MinorityInterest']['units']['USD'][0].update(change)
    a = fv.balance_input_audit(f, date(2026, 11, 2), proof(), 'tangible_book_yield')
    c = a['components']['nci']
    assert c['value'] is None and c['status'] == 'PRESENT_BUT_INELIGIBLE'
    assert reason in c['reasons']


def test_wrong_unit_and_primary_not_applicable_are_separate():
    f = facts(); t = f['facts']['us-gaap']['MinorityInterest']
    t['units']['shares'] = t['units'].pop('USD')
    a = fv.balance_input_audit(f, date(2026, 11, 2), proof(), 'earnings_yield')
    assert a['components']['nci']['status'] == 'PRESENT_BUT_INELIGIBLE'
    assert 'UNIT_MISMATCH' in a['components']['nci']['reasons']
    assert all(c['primary_applicability'] == 'NOT_APPLICABLE' for c in a['components'].values())


@pytest.mark.parametrize('change,reason', [
    ({'traded_at': None}, 'PRICE_TRADE_TIME_UNCONFIRMED'),
    ({'traded_at': '2026-11-02T09:29:59-05:00'}, 'PRICE_OUTSIDE_REGULAR_SESSION'),
    ({'traded_at': '2026-11-03T15:59:00-05:00'}, 'PRICE_OUTSIDE_REGULAR_SESSION'),
    ({'acquired_at': '2026-11-04T12:00:01Z'}, 'PRICE_CAPTURE_AFTER_VINTAGE'),
    ({'price_basis': 'SPLIT_ADJUSTED'}, 'PRICE_RAW_BASIS_REQUIRED'),
    ({'trade_validation': 'UNCONFIRMED'}, 'PRICE_TRADE_VALIDATION_UNCONFIRMED')])
def test_main_price_handoff_rejects_ineligible_evidence(change, reason):
    x = fixture(); q = price('FY0:0000000001-26-000001:2026-02-01')
    q.update(price_type='IEX_LAST_REGULAR_TRADE', price_basis='RAW',
             traded_at='2026-11-02T15:59:00-05:00', acquired_at='2026-11-03T01:00:00Z',
             trade_validation='ELIGIBLE')
    q.update(change); x['prices'] = {'earnings_yield': q}
    r = connect(**x)['result']['metrics']['earnings_yield']
    assert r['value'] is None and reason in r['reasons']


def test_existing_cli_consumes_pinned_price_and_basis_evidence(tmp_path):
    spec = importlib.util.spec_from_file_location('financial_v_cli', Path(__file__).parents[1] / 'tools/financial_v_connect.py')
    cli = importlib.util.module_from_spec(spec); spec.loader.exec_module(cli)
    x = fixture(); q = price('FY0:0000000001-26-000001:2026-02-01')
    def save(name, value):
        body = value if isinstance(value, bytes) else json.dumps(value).encode()
        (tmp_path/name).write_bytes(body)
        return {'path': name, 'sha256': hashlib.sha256(body).hexdigest()}
    source = save('trades.json', {'records': [{k:v for k,v in q.items() if k not in ('source', 'basis_source')}]})
    basis = save('basis.json', {'records': [dict(code=q['code'], cik=q['cik'], share_basis=q['share_basis'],
        valid_from='2026-02-01', valid_to='2026-11-02', action_status='MATCHED_TO_NUMERATOR')]})
    q['source'] = dict(sha256=source['sha256'], json_pointer='/records/0')
    q['basis_source'] = dict(sha256=basis['sha256'], json_pointer='/records/0')
    prices = save('prices.json', {'schema_version': 'financial-v-price-input/1', 'valuation_date': x['valuation_date'],
                               'records': {'NYSE:TEST': {'earnings_yield': q}}})
    records = {'NYSE:TEST': {**x['record'], 'profile': 'FINANCIAL'}}
    records.update({f'SYNTHETIC:{i}': {'profile': 'GENERAL'} for i in range(503)})
    job = dict(valuation_date=x['valuation_date'], input_vintage=x['input_vintage'],
               universe=save('universe.json', {'records': records}),
               shares=save('shares.json', {'records': {'NYSE:TEST': x['shares']}}),
               issuers=[dict(code='NYSE:TEST', companyfacts=save('facts.json', x['companyfacts_bytes']),
                             cover=save('cover.xml', x['cover_bytes']))], prices=prices, price_evidence=[source, basis])
    path = tmp_path/'job.json'; path.write_text(json.dumps(job))
    result = cli.run(path)
    assert result['rows'][0]['result']['metrics']['earnings_yield']['value'] == 0.1
    assert len(result['source_receipts']) == 7
    (tmp_path/'trades.json').write_text('{}')
    with pytest.raises(ValueError, match='SOURCE_HASH_MISMATCH'): cli.run(path)


@pytest.mark.parametrize('fault,reason', [('value', 'PRICE_SOURCE_FIELD_MISMATCH'),
    ('date', 'PRICE_BASIS_EVIDENCE_MISMATCH'), ('missing', 'PRICE_EVIDENCE_FILE_REQUIRED')])
def test_price_source_pointer_must_match_the_value_and_basis(fault, reason):
    spec = importlib.util.spec_from_file_location('financial_v_cli', Path(__file__).parents[1] / 'tools/financial_v_connect.py')
    cli = importlib.util.module_from_spec(spec); spec.loader.exec_module(cli)
    q = price('basis'); q['source']['json_pointer'] = q['basis_source']['json_pointer'] = '/row'
    trade = {k:v for k,v in q.items() if k not in ('source','basis_source')}
    basis = dict(code=q['code'], cik=q['cik'], share_basis='basis', valid_from='2026-01-01',
                 valid_to='2026-11-02', action_status='MATCHED_TO_NUMERATOR')
    sources = {'a'*64: {'row':trade}, 'b'*64: {'row':basis}}
    if fault == 'value': trade['value'] = 41
    elif fault == 'date': basis['valid_to'] = '2026-10-30'
    else: sources.pop('a'*64)
    with pytest.raises(ValueError, match=reason): cli._verify_price_sources({'NYSE:TEST': {'earnings_yield':q}}, sources, '2026-11-02')


def instance_fixture(*, wrong_unit=False, dimension=False):
    x = fixture(); p = json.loads(x['companyfacts_bytes'])
    p['facts']['us-gaap'].pop('CommonStockSharesOutstanding')
    x['companyfacts_bytes'] = json.dumps(p).encode()
    x['record']['source_sha256']['companyfacts'] = hashlib.sha256(x['companyfacts_bytes']).hexdigest()
    segment = '<segment><dimension>business</dimension></segment>' if dimension else ''
    unit = 'i:USD' if wrong_unit else 'x:shares'
    extra = f'''<context id="b"><entity><identifier scheme="http://www.sec.gov/CIK">0000000001</identifier>{segment}</entity><period><instant>2025-12-31</instant></period></context>
      <unit id="shares"><measure>{unit}</measure></unit>
      <g:CommonStockSharesOutstanding contextRef="b" unitRef="shares">10</g:CommonStockSharesOutstanding>'''
    body=x['cover_bytes'].replace(b'<xbrl ', b'<xbrl xmlns:g="http://fasb.org/us-gaap/2026" xmlns:x="http://www.xbrl.org/2003/instance" xmlns:i="http://www.xbrl.org/2003/iso4217" ')
    x['cover_bytes']=body.replace(b'</xbrl>',extra.encode()+b'</xbrl>')
    x['shares'].update(accn='0000000001-26-000001',form='10-K')
    x['shares']['source_sha256']['cover']=hashlib.sha256(x['cover_bytes']).hexdigest()
    return x


def test_held_instance_fills_exact_missing_balance_fact_through_existing_parser():
    x=instance_fixture(); before=x['companyfacts_bytes']; result=connect(**x)
    assert result['inputs']['book_yield']['value']==12
    assert result['balance_supplement']['added']==1
    assert result['balance_supplement']['source_sha256']==x['shares']['source_sha256']['cover']
    source=result['balance_inputs']['components']['common_shares']['source']
    assert source['payload_kind']=='RESEARCH_INSTANCE_SUPPLEMENTED'
    assert source['instance_sha256']==x['shares']['source_sha256']['cover']
    assert x['companyfacts_bytes']==before
    assert result['result']['primary_available'] is False


@pytest.mark.parametrize('fault',[{'wrong_unit':True},{'dimension':True}])
def test_held_ineligible_instance_is_distinct_from_missing_source(fault):
    result=connect(**instance_fixture(**fault))
    c=result['balance_inputs']['components']['common_shares']
    assert c['value'] is None and c['status']=='PRESENT_BUT_INELIGIBLE'
    assert 'INSTANCE_CONTEXT_OR_UNIT_NOT_ELIGIBLE' in c['reasons']
    assert result['inputs']['book_yield'] is None


def test_instance_filing_after_cutoff_cannot_supply_balance_input():
    x=instance_fixture();x['shares']['filed']='2026-11-03'
    result=connect(**x)
    assert result['balance_supplement']['reason']=='FILING_NOT_ELIGIBLE'
    assert result['balance_supplement']['added']==0
    assert result['balance_inputs']['components']['common_shares']['value'] is None


def test_instance_companyfacts_conflict_blocks_selected_component_and_book():
    x=instance_fixture();p=json.loads(x['companyfacts_bytes'])
    p['facts']['us-gaap']['CommonStockSharesOutstanding']={'units':{'shares':[dict(
        val=11,end='2025-12-31',filed='2026-02-01',accn='0000000001-26-000001',form='10-K')]}}
    x['companyfacts_bytes']=json.dumps(p).encode()
    x['record']['source_sha256']['companyfacts']=hashlib.sha256(x['companyfacts_bytes']).hexdigest()
    result=connect(**x)
    assert result['inputs']['book_yield'] is None
    assert result['inputs']['tangible_book_yield'] is None
    assert result['inputs']['earnings_yield']['value']==4
    c=result['balance_inputs']['components']['common_shares']
    assert c['value'] is None and c['status']=='PRESENT_BUT_INELIGIBLE'
    assert 'INSTANCE_COMPANYFACTS_CONFLICT' in c['reasons']
