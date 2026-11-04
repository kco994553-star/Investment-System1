import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest
from investment_system.research.financial_v import evaluate, candidate_coverage


def row():
    fact = {'value': 4, 'unit': 'USD/share', 'currency': 'USD', 'period_start': '2025-01-01',
            'period_end': '2025-12-31', 'filed': '2026-02-02', 'source': 'synthetic:filing', 'share_basis': 'basis-1'}
    book = {k: v for k, v in fact.items() if k != 'period_start'}
    book.update(equity_basis='COMMON_EXCLUDING_PREFERRED_NCI', share_count_basis='POINT_IN_TIME')
    return {'code': 'TEST:BANK', 'cik': '0000000001', 'sic': '6021', 'valuation_date': '2026-11-02',
            'input_vintage': '2026-11-04', 'identity_status': 'DOCUMENT_LINKED',
            'result_kind': 'OPERATIONAL_CANDIDATE_RAW',
            'price': {'value': 40, 'unit': 'USD/share', 'currency': 'USD', 'date': '2026-11-02',
                      'source': 'synthetic:trade', 'share_basis': 'basis-1'},
            'inputs': {'earnings_yield': fact, 'book_yield': {**book, 'value': 12},
                       'tangible_book_yield': {**book, 'value': 8, 'equity_basis': 'COMMON_TANGIBLE_EXCLUDING_GOODWILL_INTANGIBLES'}}}


def test_business_model_routes_primary_without_manufacturing_scores():
    r = evaluate(row())
    assert r['primary_metric'] == 'tangible_book_yield'
    assert [r['metrics'][k]['value'] for k in ('earnings_yield','book_yield','tangible_book_yield')] == [0.1, 0.3, 0.2]
    assert r['primary_available'] and r['score'] is None and r['rank'] is None
    x = row(); x['sic'] = '6282'
    assert evaluate(x)['primary_metric'] == 'earnings_yield'
    x['sic'] = '6200'
    assert evaluate(x)['primary_metric'] is None and not evaluate(x)['primary_available']

@pytest.mark.parametrize('change,reason', [
    ({'value': -1}, 'NONPOSITIVE_NUMERATOR'), ({'value': None}, 'INPUT_UNAVAILABLE'),
    ({'currency': 'EUR'}, 'CURRENCY_OR_UNIT_MISMATCH'), ({'share_basis': 'other'}, 'SHARE_BASIS_UNCONFIRMED'),
    ({'filed': '2026-11-03'}, 'FILING_AFTER_VALUATION'), ({'period_end': '2027-01-01'}, 'PERIOD_NOT_ELIGIBLE'),
    ({'period_start': '2025-10-01'}, 'ANNUAL_SPAN_REQUIRED'), ({'source': None}, 'SOURCE_UNCONFIRMED'),
])
def test_invalid_earnings_input_is_null_with_reason(change, reason):
    x = row(); x['inputs']['earnings_yield'].update(change)
    r = evaluate(x)['metrics']['earnings_yield']
    assert r['value'] is None and reason in r['reasons']


def test_diagnostic_future_filing_is_isolated_from_same_date_coverage():
    x = row(); x['result_kind'] = 'EX_POST_FISCAL_DIAGNOSTIC'; x['valuation_date'] = '2025-12-31'
    x['price']['date'] = '2025-12-31'
    r = evaluate(x)
    assert r['metrics']['earnings_yield']['value'] == 0.1
    assert not r['primary_available'] and not r['pit_eligible']
    official = {'TEST:BANK': {'axes': {'Q': {'score': 50}, 'G': {'score': 50}, 'V': {'score': None}}}}
    c = candidate_coverage(official, [r], '2026-11-02')
    assert c['same_date_primary_raw_valid'] == 0 and c['potential_joint_input_valid'] == 0
    assert c['scored_joint_valid'] is None and c['denominator'] == 1


def test_missing_price_and_unknown_identity_never_count_as_candidate():
    x = row(); x['price'] = None; x['identity_status'] = 'SYMBOL_ONLY'
    r = evaluate(x)
    assert all(m['value'] is None for m in r['metrics'].values()) and not r['primary_available']
    assert 'PRICE_UNAVAILABLE' in r['metrics']['earnings_yield']['reasons']


def test_potential_coverage_is_not_actual_v_score_or_total():
    x = row(); r = evaluate(x)
    official = {'TEST:BANK': {'axes': {'Q': {'score': 50}, 'G': {'score': 50}, 'V': {'score': None}}}}
    c = candidate_coverage(official, [r], '2026-11-02')
    assert c['potential_joint_input_valid'] == 1 and c['scored_joint_valid'] is None
    with pytest.raises(ValueError): candidate_coverage(official, [r,r], '2026-11-02')


def test_cli_writes_private_results_and_refuses_overwrite(tmp_path):
    source=tmp_path/'input.json'; output=tmp_path/'result.json'; source.write_text(json.dumps({'rows':[row()]}))
    script=Path(__file__).resolve().parents[1]/'tools/financial_v_research.py'
    cmd=[sys.executable,str(script),'--input',str(source),'--output',str(output)]
    result=subprocess.run(cmd,capture_output=True,text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(output.read_text())['rows'][0]['metrics']['earnings_yield']['value']==0.1
    assert output.stat().st_mode & 0o777 == 0o600
    assert subprocess.run(cmd,capture_output=True).returncode != 0


def test_book_metric_requires_common_equity_and_point_in_time_share_evidence():
    x = row(); x['inputs']['book_yield'].pop('equity_basis')
    r = evaluate(x)
    assert r['metrics']['book_yield']['value'] is None
    assert 'COMMON_EQUITY_BASIS_UNCONFIRMED' in r['metrics']['book_yield']['reasons']


def test_common_book_subtracts_preferred_and_uses_instant_shares_without_zero_fill():
    from investment_system.research.financial_v import common_book_inputs
    from datetime import date
    def item(value, unit='USD', end='2026-06-30'):
        return {'units': {unit: [{'val': value, 'end': end, 'filed': '2026-08-01',
                                 'form': '10-Q', 'accn': 'synthetic-acc'}]}}
    facts = {'cik': 1, 'facts': {'us-gaap': {
        'StockholdersEquity': item(120), 'PreferredStockValue': item(20),
        'CommonStockSharesOutstanding': item(10, 'shares'), 'MinorityInterest': item(0),
        'GoodwillAndIntangibleAssetsNet': item(30)}}}
    proof = {'status': 'SINGLE_CLASS_CONFIRMED', 'source': 'synthetic:cover',
             'cik': '0000000001', 'date': '2026-08-01'}
    r = common_book_inputs(facts, date(2026,11,2), proof)
    assert r['book_yield']['value'] == 10 and r['tangible_book_yield']['value'] == 7
    assert r['book_yield']['share_count_basis'] == 'POINT_IN_TIME'
    facts['facts']['us-gaap'].pop('PreferredStockValue')
    r = common_book_inputs(facts, date(2026,11,2), proof)
    assert r['book_yield'] is None  # no silently assumed zero preferred equity
    proof['status'] = 'BASIS_UNCONFIRMED'
    assert common_book_inputs(facts,date(2026,11,2),proof)['book_yield'] is None


def test_book_never_combines_different_filing_or_balance_dates():
    from investment_system.research.financial_v import common_book_inputs
    from datetime import date
    def item(v,unit='USD',acc='a'):
        return {'units': {unit: [{'val':v,'end':'2026-06-30','filed':'2026-08-01','form':'10-Q','accn':acc}]}}
    f={'cik':1,'facts':{'us-gaap':{'StockholdersEquity':item(120),'PreferredStockValue':item(20,acc='b'),
                                  'CommonStockSharesOutstanding':item(10,'shares')}}}
    proof={'status':'SINGLE_CLASS_CONFIRMED','source':'synthetic:cover','cik':'0000000001','date':'2026-08-01'}
    assert common_book_inputs(f,date(2026,11,2),proof)['book_yield'] is None
