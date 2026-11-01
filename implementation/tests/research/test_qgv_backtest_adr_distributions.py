from datetime import date
from decimal import Decimal

import pytest

from investment_system.research.qgv_backtest.ledger import Dividend, Ledger, LedgerError


def test_adr_fee_is_separate_from_withholding_and_reduces_entitlement_exactly_once():
    ledger=Ledger(1000,cost_bps=0)
    ledger.rebalance(date(2020,1,1),['SYN_ADR'],1,{'SYN_ADR':10})
    ledger.execute_open(date(2020,1,2),{'SYN_ADR':10})
    try:
        dividend=Dividend('synthetic-div',date(2020,1,3),'SYN_ADR',Decimal('1'),date(2020,1,6),depositary_fee_per_share=Decimal('.02'))
    except TypeError:
        pytest.fail('explicit depositary fee accounting missing')
    ledger.apply_event(dividend,date(2020,1,3))
    ledger.apply_event(dividend,date(2020,1,3))
    assert ledger.nav(date(2020,1,3),{'SYN_ADR':10}).receivables==Decimal('98')
    ledger.settle_events(date(2020,1,6))
    assert ledger.cash==Decimal('98')
    assert ledger.nav(date(2020,1,6),{'SYN_ADR':10}).nav==Decimal('1098')
    assert len(ledger.instrument_fees)==1
    assert ledger.instrument_fees[0]['fee']==Decimal('2')


def test_standalone_adr_fee_cannot_silently_create_unfunded_cash():
    try:
        dividend=Dividend('fee',date(2020,1,3),'SYN_ADR',Decimal('0'),date(2020,1,6),depositary_fee_per_share=Decimal('.02'))
    except TypeError:
        pytest.fail('standalone fee guard missing')
    with pytest.raises(LedgerError,match='ADR_FEE_EXCEEDS_DIVIDEND'):
        Ledger().apply_event(dividend,date(2020,1,3))


def test_annual_adr_distribution_requires_explicit_fee_and_gross_basis_evidence():
    from test_qgv_backtest_reuse_runner import large_bundle
    from test_qgv_backtest_runner import spec
    from investment_system.research.qgv_backtest.annual import annual_extension
    from investment_system.research.qgv_backtest.extensions import selected_cells
    from investment_system.research.qgv_backtest.runner import replay_bundle
    data=large_bundle()
    data['security_master'][0]['security_type']='ADR'
    data['adr_bridges']=[dict(security_id='SYN00',effective_date='2000-01-01',known_at='2015-01-01T12:00:00Z',
        ordinary_per_adr=1,financial_currency='USD',usd_per_financial_unit=1,source='SYNTHETIC',receipt='HAND')]
    data['events']=[dict(type='DIVIDEND',event_id='synthetic-adr',security_id='SYN00',
        effective_date='2016-02-19',pay_date='2016-02-20',cash_per_share=1)]
    extension=annual_extension()
    cells=selected_cells(extension,'primary',['DEC-SPX-W0-Y-D1'])
    rejected=replay_bundle(spec(),data,'TARGET_QGV_V2',cells=cells,extension=extension)
    assert rejected['status']=='INCOMPLETE_REPLAY'
    assert 'ADR_DISTRIBUTION_EVIDENCE_UNVERIFIED' in rejected['blockers']
    assert rejected['runs'][0]['metrics'] is None
    data['events'][0].update(depositary_fee_per_share=0,depositary_fee_receipt='HAND_VERIFIED_ZERO',
        cash_amount_basis='GROSS_BEFORE_WITHHOLDING',distribution_receipt='HAND_GROSS')
    accepted=replay_bundle(spec(),data,'TARGET_QGV_V2',cells=cells,extension=extension)
    assert accepted['status']=='REPLAY_COMPLETE'
