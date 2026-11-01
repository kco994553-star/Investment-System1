"""PIT universe and raw-factor tests contain no real securities or prices."""
import copy
import importlib
from datetime import date

import pytest

from investment_system.research.qgv_backtest.runner import _calendar
from test_qgv_backtest_runner import bundle


def api():
    try:
        return importlib.import_module('investment_system.research.qgv_backtest.universe')
    except ModuleNotFoundError:
        pytest.fail('PIT research universe adapter missing')


def inputs():
    data = bundle()
    data['universe_coverage'] = dict(complete=True, delistings_included=True, source='SYNTHETIC',
        receipt='HAND_AUDIT', start='2000-01-01', end='2016-12-31')
    data['security_master'] = [dict(row, issuer_id=f'I{i}', security_type='COMMON', known_at='2015-01-01T12:00:00Z', source='SYNTHETIC', receipt='HAND_AUDIT') for i,row in enumerate(data['membership'])]
    data['capitalization'] = [dict(issuer_id=f'I{i}', effective_date='2016-02-01', known_at='2016-02-01T12:00:00Z', source='SYNTHETIC', receipt='HAND_AUDIT',
        components=[dict(security_id=f'SYN{i:02}', issued_shares=30000000, share_basis='ISSUED_ORDINARY')]) for i in range(11)]
    data['cpi'] = [dict(period_end='2016-01-31', known_at='2016-02-01T12:00:00Z', value=200, source='SYNTHETIC',receipt='HAND_AUDIT')]
    data['cpi_2009_annual'] = dict(value=200, source='SYNTHETIC', receipt='FIXED_RESEARCH_UNIT')
    data['adr_bridges'] = []
    return data


def test_book200_includes_reit_adr_and_uses_issued_share_cap_not_diluted_eps_shares():
    module = api()
    data = inputs()
    data['security_master'][0]['security_type'] = 'REIT'
    data['security_master'][1]['security_type'] = 'ADR'
    data['adr_bridges'] = [dict(security_id='SYN01', effective_date='2000-01-01', known_at='2015-01-01T12:00:00Z',
        ordinary_per_adr=2, financial_currency='USD', usd_per_financial_unit=1, source='SYNTHETIC', receipt='HAND_BRIDGE')]
    view = module.build_universe_view(data, 'U-BOOK200', date(2016,2,12), _calendar(data))
    assert 'SYN00' in view.identities  # REIT retained.
    assert 'SYN01' not in view.identities  # 10.7 USD ADR / 2 * 30m = 160.5m: below floor.
    assert view.exclusions['SYN01'] == 'BELOW_REAL_CAP_FLOOR'
    assert view.identities['SYN02']['market_cap_usd'] == pytest.approx(351000000)
    assert view.floor_usd == 200000000


def test_future_cpi_identity_and_capitalization_cannot_change_past_universe():
    module = api()
    data = inputs()
    cal = _calendar(data)
    first = module.build_universe_view(data, 'U-BOOK200', date(2016,2,12), cal)
    changed = copy.deepcopy(data)
    changed['cpi'].append(dict(changed['cpi'][0], known_at='2016-02-16T12:00:00Z',value=100000))
    changed['capitalization'].append(dict(changed['capitalization'][0], known_at='2016-02-16T12:00:00Z',components=[]))
    changed['security_master'].append(dict(changed['security_master'][0], known_at='2016-02-16T12:00:00Z',security_type='ETF'))
    assert module.build_universe_view(changed, 'U-BOOK200', date(2016,2,12), cal) == first


def test_unknown_adr_ratio_blocks_cap_instead_of_assuming_one():
    module = api()
    data = inputs()
    data['security_master'][0]['security_type'] = 'ADR'
    with pytest.raises(ValueError, match='ADR_BRIDGE_UNVERIFIED'):
        module.build_universe_view(data, 'U-BOOK200', date(2016,2,12), _calendar(data))


def test_spx_uses_actual_membership_without_book_cap_filter():
    module = api()
    data = inputs()
    data['membership'] = [dict(data['membership'][0], end='2016-02-01'), data['membership'][1]]
    data['capitalization'][1]['components'][0]['issued_shares'] = 1
    view = module.build_universe_view(data, 'U-SPX-HIST', date(2016,2,12), _calendar(data))
    assert set(view.identities) == {'SYN01'}


def test_same_economic_issuer_under_different_ciks_is_one_liquidity_selected_company():
    module = api()
    data = inputs()
    data['security_master'][1]['issuer_id'] = 'I0'
    view = module.build_universe_view(data, 'U-SPX-HIST', date(2016,2,12), _calendar(data))
    assert len(view.identities) == 10
    assert 'SYN01' in view.identities and 'SYN00' not in view.identities


def test_raw_factor_recipes_have_directional_values_and_future_revision_is_ignored():
    module = api()
    data = inputs()
    data['factor_inputs'] = [dict(security_id='SYN00', effective_date='2016-02-01', filed='2016-02-01', known_at='2016-02-01T12:00:00Z',
        source='SYNTHETIC', receipt='HAND_PIT', currency='USD', period_start='2015-01-01', period_end='2015-12-31',
        eps_share_basis='ORDINARY_USD_ASOF_SIGNAL',eps_price_basis_receipt='HAND',
        values=dict(trailing_eps=1, net_income_ttm=10, sales_ttm=100, equity=50, ebitda_ttm=20, debt=10, cash=5,
                    preferred_equity=0, minority_interest=0, cash_dividends_ttm=2, buybacks_ttm=4, issuance_ttm=1))]
    identities = {'SYN00': dict(market_cap_usd=100, ordinary_price_usd=10, currency='USD')}
    day = date(2016,2,12)
    values, reasons = module.factor_values(data, identities, day)
    assert values['F03']['SYN00'] == 10
    assert values['F07']['SYN00'] == 2
    assert values['F06']['SYN00'] == 1
    assert values['F04']['SYN00'] == pytest.approx(20/105)
    assert values['F10']['SYN00'] == .05
    data['factor_inputs'].append(dict(data['factor_inputs'][0], known_at='2016-02-16T12:00:00Z',values=dict(net_income_ttm=100000)))
    assert module.factor_values(data, identities, day)[0] == values
    assert reasons['F14']['SYN00'] == 'MISSING_253_VERIFIED_TOTAL_RETURN_CLOSES'


def test_missing_raw_input_never_becomes_zero_or_bottom_decile():
    module = api()
    data = inputs()
    values, reasons = module.factor_values(data, {'SYN00': dict(market_cap_usd=100)}, date(2016,2,12))
    assert all(not v for v in values.values())
    assert reasons['F03']['SYN00'] == 'MISSING_PIT_FACTOR_INPUT'


def test_pe_uses_aligned_positive_trailing_eps_not_issued_cap_divided_by_net_income():
    module=api()
    data=inputs()
    data['factor_inputs']=[dict(security_id='SYN00',effective_date='2016-02-01',filed='2016-02-01',
        known_at='2016-02-01T12:00:00Z',source='SYNTHETIC',receipt='HAND',currency='USD',
        period_start='2015-01-01',period_end='2015-12-31',eps_share_basis='ORDINARY_USD_ASOF_SIGNAL',eps_price_basis_receipt='HAND',
        values=dict(net_income_ttm=10,trailing_eps=-1))]
    identity={'SYN00':dict(market_cap_usd=100,ordinary_price_usd=10)}
    values,reasons=module.factor_values(data,identity,date(2016,2,12))
    assert 'SYN00' not in values['F03']
    data['factor_inputs'][0]['values']['trailing_eps']=2
    values,_=module.factor_values(data,identity,date(2016,2,12))
    assert values['F03']['SYN00']==5


@pytest.mark.parametrize('missing',['receipt','source','known_at','security_type'])
def test_active_book_listing_with_missing_identity_evidence_blocks_instead_of_shrinking_pool(missing):
    data=inputs()
    del data['security_master'][0][missing]
    with pytest.raises(ValueError,match='IDENTITY_PIT_COVERAGE_UNVERIFIED'):
        api().build_universe_view(data,'U-BOOK200',date(2016,2,12),_calendar(data))


@pytest.mark.parametrize('filed,known,end',[('2016-02-01','2016-02-01T12:00:00Z','2016-02-10'),
    ('2016-02-11','2016-02-01T12:00:00Z','2016-01-31')])
def test_financial_period_end_filing_and_availability_must_be_chronologically_possible(filed,known,end):
    data=inputs()
    data['factor_inputs']=[dict(security_id='SYN00',effective_date='2016-02-01',filed=filed,known_at=known,
        source='SYNTHETIC',receipt='HAND',currency='USD',period_start='2015-02-11',period_end=end,
        eps_share_basis='ORDINARY_USD_ASOF_SIGNAL',eps_price_basis_receipt='HAND',
        values=dict(trailing_eps=2,net_income_ttm=10,equity=50,sales_ttm=100))]
    values,reasons=api().factor_values(data,{'SYN00':dict(market_cap_usd=100,ordinary_price_usd=10)},date(2016,2,12))
    assert not values['F03'] and not values['F07'] and not values['F06']
    assert reasons['F03']['SYN00']=='INVALID_FACTOR_CHRONOLOGY'
