"""Synthetic checks for the isolated proposal, never official scoring changes."""
import pytest


def api():
    from investment_system.research import financial_qg_proposal
    return financial_qg_proposal


def rows(group, count, start=0):
    return [dict(company_id=f'{group}:{i}', issuer_id=f'{group}-{i}',
                 financial_calculation_profile='FINANCIAL', financial_peer_template=group,
                 owner_source_context=dict(sic='6021' if group=='BANK' else '6331'),
                 metrics={'financial::roe':start+i, 'financial::equity_to_assets':start+i,
                          'financial::moat_proxy':start+i}) for i in range(count)]


def test_same_type_only_and_minimum_eight():
    m=api();data=rows('BANK',8)+rows('INSURANCE',8,1000)
    out=m.score_financial(data,data)
    assert out['BANK:0']['roles']['q_profitability']['score']==0
    assert out['INSURANCE:0']['roles']['q_profitability']['score']==0
    assert out['BANK:0']['axes']['Q']['score'] is not None
    small=m.score_financial(rows('BANK',7),rows('BANK',7))
    assert small['BANK:0']['axes']['Q']['score'] is None
    assert small['BANK:0']['roles']['q_profitability']['metrics'][0]['reason']=='PEER_SAMPLE_SMALL'


def test_quality_stays_undefined_not_low_credit_losses():
    m=api();data=rows('BANK',8)
    for r in data:r['metrics']['financial::loan_loss_expense']=0
    out=m.score_financial(data,data)['BANK:0']
    assert out['roles']['q_earnings_quality']['score'] is None
    assert out['roles']['q_earnings_quality']['reason']=='DEFINITION_NOT_COMPLETED'
    assert out['axes']['Q']['weight_available']==.65
    assert out['roles']['q_profitability']['nominal_weight']==25


def test_duplicate_codes_do_not_add_a_peer_and_conflicts_fail():
    m=api();data=rows('BANK',7);alias=dict(data[0],company_id='BANK:alias')
    assert m.score_financial([alias],data+[alias])['BANK:alias']['axes']['Q']['score'] is None
    bad=dict(alias,metrics={'financial::roe':99})
    with pytest.raises(ValueError,match='ISSUER_REFERENCE_CONFLICT'):
        m.score_financial([alias],data+[bad])


def test_no_interest_margin_for_insurance_and_no_general_reclassification():
    m=api();data=rows('INSURANCE',8)
    for r in data:r['metrics']['financial::net_interest_income_to_assets']=999
    out=m.score_financial(data,data)['INSURANCE:0']
    assert all(i['metric']!='net_interest_income_to_assets' for i in out['roles']['q_profitability']['metrics'])
    with pytest.raises(ValueError,match='NOT_FINANCIAL_INPUT'):
        m.peer_group(dict(data[0],financial_calculation_profile=None))


def test_brokers_are_not_silently_pooled_with_managers_to_reach_eight():
    m=api();data=rows('BROKER',7)+rows('ASSET_MANAGER',8)
    primary=m.score_financial(data,data)
    assert primary['BROKER:0']['axes']['Q']['score'] is None
    assert primary['ASSET_MANAGER:0']['axes']['Q']['score'] is not None
    broad=m.score_financial(data,data,peer_policy='BROAD_THREE_TYPES_DIAGNOSTIC')
    assert broad['BROKER:0']['axes']['Q']['score'] is not None
    assert broad['BROKER:0']['peer_policy']!='MATCH_ACCOUNTING_SUBTYPE'
