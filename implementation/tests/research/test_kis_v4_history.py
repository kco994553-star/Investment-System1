"""Synthetic KIS/F_k histories only; prices and issuers are fabricated."""
from copy import deepcopy
import importlib
import importlib.util
import json
from pathlib import Path
import runpy
import pytest
from investment_system.research._private_artifacts import digest


def api():
    name='investment_system.research.kis_v4_history'
    assert importlib.util.find_spec(name) is not None,'KIS_V4_HISTORY_ADAPTER_MISSING'
    return importlib.import_module(name)


def contract():
    c=runpy.run_path(str(Path(__file__).parents[2]/'tools/kis_contract_fixture.py'))['fixtures']()['synthetic-raw.json']
    base=c['raw_bars'][0];rows=[]
    for day in ['2022-12-30','2023-12-29','2024-12-31','2026-10-23']:
        r=deepcopy(base);r.update(date=day,open='20',high='20',low='20',close='20');rows.append(r)
    c.update(raw_bars=rows,bars=deepcopy(rows),price_basis_date='2026-10-23')
    return c


def history():
    return [dict(fiscal_year_end=f'{y}-12-31',value=1,share_basis_factor=2) for y in [2022,2023,2024]]


def call(c,h=None,day='2026-10-23',**kw):
    return api().kis_month_closes(c,history() if h is None else h,company_code='SYNTHETIC:CODE',
        evaluation_day=day,expected_contract_hash=digest(c),expected_query=dict(symb='SYN',excd='NAS'),**kw)


def test_exact_month_end_raw_divided_by_existing_factor_is_provider_truthful():
    c=contract();old=deepcopy(c);closes,audit=call(c)
    assert closes=={'2022-12':10,'2023-12':10,'2024-12':10}
    assert c==old
    assert audit['provider']=='KIS' and audit['price_basis']=='RAW_MODP0'
    assert audit['source_contract_hash']==digest(c)
    assert audit['rule']=='EXISTING_CALC23_1_RAW_DIVIDED_BY_SHARE_BASIS_FACTOR'
    assert [r['trade_day'] for r in audit['observations']]==['2022-12-30','2023-12-29','2024-12-31']
    assert not any('ROUND' in str(r) for r in audit['observations'])


def test_missing_factor_and_exact_month_end_are_not_filled():
    c=contract();h=history();h[0].update(share_basis_factor=None,share_basis_factor_reason='SHARE_BASIS_UNCONFIRMED')
    c['raw_bars'].pop(1);c['bars'].pop(1)
    closes,a=call(c,h)
    assert closes=={'2024-12':10}
    assert [r['reason'] for r in a['observations']][:2]==['SHARE_BASIS_UNCONFIRMED','EXACT_MONTH_END_SESSION_NOT_RETAINED']


@pytest.mark.parametrize('h',[
    [dict(fiscal_year_end='2026-10-31',value=1,share_basis_factor=1)],
    [dict(fiscal_year_end='2026-12-31',value=1,share_basis_factor=1)]])
def test_current_or_future_month_never_enters_history(h):
    closes,audit=call(contract(),h)
    assert not closes and audit['observations'][0]['reason']=='INCOMPLETE_OR_FUTURE_MONTH'


def test_source_query_modp_and_pin_are_checked():
    c=contract()
    with pytest.raises(ValueError,match='CONTRACT_PIN'):
        api().kis_month_closes(c,history(),company_code='SYNTHETIC:CODE',evaluation_day='2026-10-23',
            expected_contract_hash='0'*64,expected_query=dict(symb='SYN',excd='NAS'))
    c['source_query']['MODP']='1'
    with pytest.raises(ValueError,match='RAW_MODP0'):call(c)
    c=contract();c['source_query']['SYMB']='OTHER'
    with pytest.raises(ValueError,match='QUERY_IDENTITY'):call(c)


def test_after_cutoff_or_held_historical_month_is_withheld():
    c=contract()
    c['held_ranges']=[{'from':'2023-12-29','to':'2023-12-29','reason':'SYNTHETIC_HOLD'}]
    closes,audit=call(c)
    assert '2023-12' not in closes and audit['observations'][1]['reason']=='HISTORICAL_PRICE_HELD'
    c=contract();c['collected_at']='2026-10-25T04:00:00Z'
    with pytest.raises(ValueError,match='NOT_YET_AVAILABLE'):
        call(c,available_at='2026-10-24T04:00:00Z')


def test_official_reference_requires_explicit_opt_in_and_preserves_other_roles():
    api()  # missing feature must fail as an assertion before the call boundary
    from investment_system.research.private_kis_reference import official_reference
    from investment_system.universe.sec_universe_shares import universe_codes
    from investment_system.universe.sec_qgv2 import empty_record
    p=json.loads((Path(__file__).parents[1]/'fixtures/sec_qgv2_vectors_v1.json').read_text())['base']
    p['records']={code:p['records'].get(code) or empty_record() for code in universe_codes()}
    code='NASDAQ:ABNB';p['records'][code]['v_inputs_v2']['ebit_per_share_history']=history()
    c=contract();links={code:dict(symb='SYN',excd='NAS')};contracts={code:c}
    args=dict(day='2026-10-23',calculated_at='2026-10-24T04:00:00Z',expected_payload_hash=digest(p),
              expected_links_hash=digest(links),expected_contract_hashes={code:digest(c)})
    before=official_reference(p,contracts,links,**args)
    audits=[]
    after=official_reference(p,contracts,links,**args,kis_v4_history=True,v4_audit_sink=audits.append)
    assert before['rows'][code]['factors']['v_vs_own_history']['score'] is None
    assert after['rows'][code]['factors']['v_vs_own_history']['score'] is not None
    assert 'v4_history' not in before and after['v4_history']['enabled'] is True
    assert 'rows' not in after['v4_history'] and after['v4_history']['evaluated_rows']==1
    assert digest(audits[0])==after['v4_history']['diagnostics_hash']
    for axis in ['Q','G']:assert before['rows'][code]['axes'][axis]==after['rows'][code]['axes'][axis]
    for role in ['v_earnings_yield','v_fcf_yield','v_vs_industry','v_expectation_check']:
        assert before['rows'][code]['factors'][role]==after['rows'][code]['factors'][role]
    assert after['display']==before['display'] and after['rank'] is None
    assert after['official_publication_replaced'] is False
    with pytest.raises(ValueError,match='HISTORY_SOURCE_CONFLICT'):
        official_reference(p,contracts,links,**args,kis_v4_history=True,monthends={'synthetic':'conflict'})


def test_conflicting_fiscal_factors_in_same_calendar_month_are_withheld():
    h=[dict(fiscal_year_end='2023-12-15',value=1,share_basis_factor=1),
       dict(fiscal_year_end='2023-12-31',value=2,share_basis_factor=2)]
    closes,audit=call(contract(),h)
    assert not closes
    assert {r['reason'] for r in audit['observations']}=={'CONFLICTING_FISCAL_MONTH_BASIS'}


def test_unknown_and_known_factors_in_shared_month_do_not_cross_fill():
    h=[dict(fiscal_year_end='2023-12-15',value=1,share_basis_factor=None,
            share_basis_factor_reason='SHARE_BASIS_UNCONFIRMED'),
       dict(fiscal_year_end='2023-12-31',value=2,share_basis_factor=2)]
    closes,audit=call(contract(),h)
    assert not closes
    assert all(r['reason']=='CONFLICTING_FISCAL_MONTH_BASIS' for r in audit['observations'])
