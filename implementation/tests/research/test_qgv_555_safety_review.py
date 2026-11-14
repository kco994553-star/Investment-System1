from copy import deepcopy
import pytest
from investment_system.research.qgv_555_safety_review import inspect_safety


def source():
    tax={}
    for tag,val in [('Assets',100),('StockholdersEquity',40),('StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest',45),('Liabilities',55),('LongTermDebtCurrent',0),('CashAndCashEquivalentsAtCarryingValue',20)]:
        tax[tag]={'units':{'USD':[dict(val=val,end='2025-12-31',filed='2026-02-01',accn='SYN',form='10-K')]}}
    for tag,val in [('NetIncomeLoss',10),('OperatingIncomeLoss',10),('InterestExpense',0),('DepreciationDepletionAndAmortization',5)]:
        tax[tag]={'units':{'USD':[dict(val=val,start='2025-01-01',end='2025-12-31',filed='2026-02-01',accn='SYN',form='10-K')]}}
    return dict(cik=1,facts={'us-gaap':tax}),dict(cik='0000000001',acquired_at='2026-02-03T00:00:00Z',fiscal_year_end='2025-12-31',profile='GENERAL')


def test_derived_uses_total_equity_not_parent_equity():
    p,r=source();out=inspect_safety(p,r,'SYN')
    assert out['derived_liabilities_arithmetic_candidate']==60
    assert out['derived_liabilities_verified']==55
    assert out['derived_matches_direct'] is True
    assert out['no_debt_verified'] and out['explicit_interest_zero']
    assert not out['highest_counterfactual_adopted']


def test_parent_only_does_not_invent_zero_nci():
    p,r=source();del p['facts']['us-gaap']['StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest']
    out=inspect_safety(p,r,'SYN')
    assert out['derived_liabilities_arithmetic_candidate']==60
    assert out['derived_liabilities_verified'] is None
    p['facts']['us-gaap']['MinorityInterest']=deepcopy(p['facts']['us-gaap']['StockholdersEquity'])
    p['facts']['us-gaap']['MinorityInterest']['units']['USD'][0]['val']=0
    p['facts']['us-gaap']['Liabilities']['units']['USD'][0]['val']=60
    assert inspect_safety(p,r,'SYN')['derived_liabilities_verified']==60


def test_zero_joint_venture_minority_is_not_total_group_nci_zero():
    p,r=source();t=p['facts']['us-gaap'];del t['StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest']
    t['MinorityInterestInJointVentures']=deepcopy(t['StockholdersEquity'])
    t['MinorityInterestInJointVentures']['units']['USD'][0]['val']=0
    assert inspect_safety(p,r,'SYN')['derived_liabilities_verified'] is None


def test_derived_requires_same_actual_instant_not_just_same_target_fy():
    p,r=source();p['facts']['us-gaap']['Assets']['units']['USD'][0]['end']='2025-12-30'
    out=inspect_safety(p,r,'SYN')
    assert out['components']['assets_legacy']==100
    assert out['derived_liabilities_arithmetic_candidate'] is None
    assert not out['derived_any_period_arithmetic_present']


@pytest.mark.parametrize('case',['unit','conflict','filing','equation'])
def test_derived_invalid_evidence_not_adopted(case):
    p,r=source();t=p['facts']['us-gaap']['StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest'];x=t['units']['USD'][0]
    if case=='unit':t['units']['EUR']=t['units'].pop('USD')
    elif case=='conflict':t['units']['USD'].append(dict(x,val=46))
    elif case=='filing':x['accn']='OTHER'
    else:p['facts']['us-gaap']['Liabilities']['units']['USD'][0]['val']=54
    assert inspect_safety(p,r,'SYN')['derived_liabilities_verified'] is None


def test_interest_missing_is_not_zero_and_losses_remain_visible():
    p,r=source();del p['facts']['us-gaap']['InterestExpense']
    out=inspect_safety(p,r,'SYN');assert not out['explicit_interest_zero']
    p['facts']['us-gaap']['OperatingIncomeLoss']['units']['USD'][0]['val']=-20
    out=inspect_safety(p,r,'SYN')
    assert out['components']['ebitda']==-15
    assert out['raw_safety_unavailable'] and out['no_debt_verified']
    assert out['highest_counterfactual_role_recovery'] and not out['highest_counterfactual_adopted']


def test_positive_finance_lease_prevents_whole_debt_zero_claim():
    p,r=source();p['facts']['us-gaap']['FinanceLeaseLiability']=deepcopy(p['facts']['us-gaap']['Assets'])
    p['facts']['us-gaap']['FinanceLeaseLiability']['units']['USD'][0]['val']=5
    out=inspect_safety(p,r,'SYN')
    assert not out['no_debt_verified']
