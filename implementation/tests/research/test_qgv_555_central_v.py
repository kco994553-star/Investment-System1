"""Public synthetic prices only; raw expectations and parity to the existing kernel."""
from copy import deepcopy
import math
import pytest

from investment_system.qgv import qgv_v2, qgv2_inputs
from investment_system.qgv.dcf_parameters import load_default_dcf_parameters
from investment_system.research.sector_qgv import digest
from investment_system.research.qgv_555_central_v import bind_central_prices


def fixture():
    def flow(value):return dict(fy_value=value,fy_end='2025-12-31',ttm_value=value,ttm_end='2026-09-30')
    record=dict(cik='synthetic-issuer',profile='GENERAL',currency='USD',
        fiscal_year_end='2025-12-31',acquired_at='2026-11-04T02:00:00Z',
        calc_version='qgv2-calc/2026-10-23.1',
        v_inputs_v2=dict(currency='USD',ebit=flow(200),fcf=flow(120),revenue=flow(1000),
            total_debt=dict(value=50,period_end='2026-09-30'),
            cash_and_equivalents=dict(value=20,period_end='2026-09-30'),
            diluted_shares=dict(value=100,period_end='2026-09-30'),
            revenue_cagr_3y=.1,
            ebit_per_share_history=[dict(fiscal_year_end=f'{y}-12-31',value=i) for y,i in [(2023,1),(2024,2),(2025,3)]]))
    context=dict(record_hash=digest(record),**{k:record[k] for k in ('acquired_at','fiscal_year_end','currency','calc_version')})
    row=dict(company_id='SYN:ONE',issuer_id='synthetic-issuer',owner_source_context=context,
             metrics={},metric_evidence={})
    snapshot=dict(evaluation_day='2026-11-04',input_cutoff='2026-11-13T00:00:00Z',
                  members=['SYN:ONE'],rows=[row],population_id='synthetic',population_version='1')
    financial={'SYN:ONE':dict(record=record,source_refs=['SYNTHETIC_FINANCIAL_PIN'])}
    quote=dict(company_id='SYN:ONE',issuer_id='synthetic-issuer',status='TRADED',trade_day='2026-11-04',
        traded_at='2026-11-04T20:59:00Z',retrieved_at='2026-11-05T03:00:00Z',price=10,currency='USD',
        provider='IEX_HIST',price_definition='IEX_LAST_REGULAR_SESSION_TRADE',price_basis='AS_TRADED',
        source_refs=['SYNTHETIC_IEX_RECEIPT'],security_basis_status='VERIFIED',
        corporate_action_basis_status='VERIFIED',basis_evidence_refs=['SYNTHETIC_CLASS_ACTIONS_REVIEW'])
    return snapshot,financial,quote


def bind(s,f,quotes):
    return bind_central_prices(s,f,quotes,'2026-11-14T01:00:00Z','2026-11-14T01:00:00Z')


def test_normal_price_existing_kernel_and_exact_weighted_share_basis():
    s,f,q=fixture();old=deepcopy((s,f,q));out,audit=bind(s,f,[q]);r=out['rows'][0]
    assert r['metrics']['central::ebit_yield']==pytest.approx(200/1030)
    assert r['metrics']['central::fcf_yield']==pytest.approx(120/1030)
    assert 'central::own_history' not in r['metrics']
    p=r['metric_evidence']['central::ebit_yield']
    assert p['share_basis']=='WEIGHTED_AVERAGE_DILUTED' and p['earnings_basis']=='REPORTED'
    assert p['valuation_day']=='2026-11-04' and p['available_at']==out['input_cutoff']
    assert p['price_trade_at']!=p['price_acquired_at']
    assert p['normalized_periods']['diluted_shares']=='2026-09-30'
    assert p['source_record_hash']==s['rows'][0]['owner_source_context']['record_hash']
    assert not out['central_v_context']['historical_system_pit_complete']
    assert out['central_v_context']['dcf_parameters_hash']==digest(load_default_dcf_parameters())
    assert (s,f,q)==old and out['members']==s['members']
    # Documentary mapping can be validated without inventing a fixed security id.
    assert 'security_id' not in q and len(audit[0]['adopted_metrics'])>=2


def test_parity_with_existing_kernel_and_validated_history_only():
    s,f,q=fixture();q.update(month_closes={'2023-12':10,'2024-12':20,'2025-12':30},
        history_basis_status='VERIFIED',history_share_basis='WEIGHTED_AVERAGE_DILUTED',
        history_source_refs=['SYNTHETIC_EXISTING_FK_HISTORY'])
    out,audit=bind(s,f,[q])
    normalized,_=qgv2_inputs._v_inputs(f['SYN:ONE']['record']['v_inputs_v2'])
    expected=qgv_v2._metrics(dict(profile='GENERAL',v_inputs=normalized),
        dict(price=q['price'],currency='USD',month_closes=q['month_closes']),load_default_dcf_parameters(),cyclical_years=None)
    for key in ('ebit_yield','fcf_yield','own_history','gap'):
        assert audit[0]['raw_values'][key]==expected[key]
    assert 'central::own_history' in out['rows'][0]['metrics']
    del q['history_basis_status']
    out,audit=bind(s,f,[q])
    assert 'central::own_history' not in out['rows'][0]['metrics']
    assert audit[0]['history_connection_reason']=='HISTORY_PRICE_SHARE_BASIS_UNVERIFIED'
    assert 'central::ebit_yield' in out['rows'][0]['metrics']


@pytest.mark.parametrize('status',['NO_TRADE','NOT_IN_FILE','INELIGIBLE'])
def test_no_trade_missing_and_ineligible_are_distinct_not_zero(status):
    s,f,q=fixture();q.update(status=status,price=None);q.pop('traded_at')
    out,audit=bind(s,f,[q])
    assert not out['rows'][0]['metrics']
    assert audit[0]['price_status']==status
    assert audit[0]['price_record_hash']==digest(q)
    assert audit[0]['price_source_refs']==q['source_refs']
    assert all(v==status for v in audit[0]['reasons'].values())


@pytest.mark.parametrize('change',[
    {'trade_day':'2026-11-02'}, {'traded_at':'2026-11-03T20:59:00Z'},
    {'retrieved_at':None},{'retrieved_at':'2026-11-15T00:00:00Z'},
    {'traded_at':'2026-11-06T20:59:00Z'}, {'currency':'EUR'},
    {'security_basis_status':'UNKNOWN'}, {'corporate_action_basis_status':'UNKNOWN'},
    {'basis_evidence_refs':[]}, {'share_basis':'ACTUAL_SHARES_OUTSTANDING'},
    {'price_basis':'SPLIT_ADJUSTED'}, {'issuer_id':'different-issuer'},
    {'price':0},{'price':float('nan')},{'price':float('inf')},
    {'provider':'OTHER'}, {'price_definition':'OFFICIAL_CLOSE'}])
def test_invalid_price_or_unverified_basis_is_rejected(change):
    s,f,q=fixture();q.update(change)
    with pytest.raises(ValueError):bind(s,f,[q])


def test_source_context_future_history_and_missing_record():
    s,f,q=fixture();f['SYN:ONE']['record']['currency']='EUR'
    with pytest.raises(ValueError,match='SOURCE_CONTEXT'):bind(s,f,[q])
    s,f,q=fixture();q.update(month_closes={'2026-12':12},history_basis_status='VERIFIED',
        history_share_basis='WEIGHTED_AVERAGE_DILUTED',history_source_refs=['SYNTHETIC'])
    with pytest.raises(ValueError,match='HISTORY_FUTURE'):bind(s,f,[q])
    out,audit=bind(s,{},[q])
    assert audit[0]['source_state']=='RETAINED_FINANCIAL_NOT_LINKED'
    assert audit[0]['price_status']=='TRADED'  # price receipt is independent from raw V calculation
    s,f,q=fixture();out,audit=bind(s,f,[])
    assert audit[0]['price_status']=='NOT_IN_FILE' and not out['rows'][0]['metrics']


def test_snapshot_update_clears_previous_price_metrics_without_inventing_a_trade():
    s,f,q=fixture();out,_=bind(s,f,[q]);q.update(status='NO_TRADE',price=None)
    again,audit=bind(out,f,[q])
    assert not again['rows'][0]['metrics'] and audit[0]['price_status']=='NO_TRADE'


def test_financial_source_is_not_silently_reclassified_as_general_V():
    s,f,q=fixture();record=f['SYN:ONE']['record'];record['profile']='FINANCIAL'
    s['rows'][0]['owner_source_context']['record_hash']=digest(record)
    out,audit=bind(s,f,[q])
    assert not out['rows'][0]['metrics']
    assert all(v=='FINANCIAL_PROFILE_V_NOT_DEFINED' for v in audit[0]['reasons'].values())


@pytest.mark.parametrize('month',['2026-11','2026-12'])
def test_monthend_without_exact_day_cannot_enter_incomplete_current_month(month):
    s,f,q=fixture()
    q.update(month_closes={month:12},history_basis_status='VERIFIED',
        history_share_basis='WEIGHTED_AVERAGE_DILUTED',history_source_refs=['SYNTHETIC'])
    with pytest.raises(ValueError,match='HISTORY_FUTURE'):bind(s,f,[q])
