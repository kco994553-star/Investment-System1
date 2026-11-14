from copy import deepcopy
import pytest
from investment_system.research.qgv_555_share_review import review_share_history


def source(split=1,eps_consistent=True):
    tax={};dates={2022:('old','2023-02-01'),2023:('middle','2024-02-01'),2024:('new','2025-02-01'),2025:('basis','2026-02-01')}
    def put(tag,unit,year,value,filing):
        accn,filed=dates[filing]
        tax.setdefault(tag,{'units':{}})['units'].setdefault(unit,[]).append(dict(val=value,start=f'{year}-01-01',end=f'{year}-12-31',filed=filed,accn=accn,form='10-K'))
    for filing in range(2022,2026):
        for year in range(max(2022,filing-1),filing+1):
            factor=split if filing>=2024 else 1
            put('EarningsPerShareDiluted','USD/shares',year,(year-2020)/factor if eps_consistent or filing<2024 else year-2020,filing)
            put('WeightedAverageNumberOfDilutedSharesOutstanding','shares',year,100*factor,filing)
            put('NetIncomeLoss','USD',year,100*(year-2020),filing)
            put('NetCashProvidedByUsedInOperatingActivities','USD',year,200*(year-2020),filing)
            put('PaymentsToAcquirePropertyPlantAndEquipment','USD',year,20,filing)
    rec=dict(cik='0000000001',acquired_at='2026-02-03T00:00:00Z',fiscal_year_end='2025-12-31',currency='USD',profile='GENERAL')
    return dict(cik=1,facts={'us-gaap':tax}),rec


def test_same_basis_requires_real_cross_filing_overlap():
    p,r=source();out=review_share_history(p,r,'SYNTHETIC')
    assert out['status']=='VERIFIED'
    assert out['metrics']['eps_cagr_3y']['value']==pytest.approx(0.357209)
    assert out['metrics']['dilution_3y']['value']==0
    assert out['metrics']['fcf_per_share_cagr_3y']['value'] is not None
    p['facts']['us-gaap']['EarningsPerShareDiluted']['units']['USD/shares']=[x for x in p['facts']['us-gaap']['EarningsPerShareDiluted']['units']['USD/shares'] if x['accn']=='basis' or x['accn']=='old']
    assert review_share_history(p,r,'SYNTHETIC')['metrics']['eps_cagr_3y']['basis_status']=='UNKNOWN'


@pytest.mark.parametrize('factor',[2,0.5])
def test_integer_and_inverse_split_normalizes_share_history(factor):
    p,r=source(factor);out=review_share_history(p,r,'SYNTHETIC')
    assert out['status']=='ADJUSTED'
    # Original EPS2022=2, after-restatement EPS2025=5/factor.
    assert out['metrics']['eps_cagr_3y']['value']==pytest.approx(0.357209)
    assert out['metrics']['dilution_3y']['value']==0
    assert any(e['status']=='ADJUSTED' for e in out['accepted_edges'])


@pytest.mark.parametrize('case',['inverse_mismatch','noninteger','unit','future','annual_ytd','conflict'])
def test_unconfirmed_restatement_or_bad_period_is_not_adopted(case):
    p,r=source(2 if case=='inverse_mismatch' else 1,eps_consistent=case!='inverse_mismatch')
    tax=p['facts']['us-gaap'];rows=tax['EarningsPerShareDiluted']['units']['USD/shares']
    if case=='noninteger':
        for x in tax['WeightedAverageNumberOfDilutedSharesOutstanding']['units']['shares']:
            if x['accn']=='middle':x['val']=101
    elif case=='unit':tax['EarningsPerShareDiluted']['units']['EUR/shares']=tax['EarningsPerShareDiluted']['units'].pop('USD/shares')
    elif case=='future':
        for x in rows:
            if x['accn']=='middle':x['filed']='2027-01-01'
    elif case=='annual_ytd':
        for x in rows:
            if x['accn']=='middle':x['start']=x['end'][:4]+'-07-01';x['form']='10-Q'
    elif case=='conflict':
        x=next(x for x in rows if x['accn']=='basis' and x['end']=='2025-12-31');rows.append(dict(x,val=999))
    out=review_share_history(p,r,'SYNTHETIC')
    assert out['metrics']['eps_cagr_3y']['value'] is None
    assert out['metrics']['eps_cagr_3y']['basis_status']=='UNKNOWN'


def test_zero_or_negative_eps_keeps_verified_basis_but_no_cagr():
    p,r=source()
    for x in p['facts']['us-gaap']['EarningsPerShareDiluted']['units']['USD/shares']:
        if x['end']=='2022-12-31':x['val']=0
    out=review_share_history(p,r,'SYNTHETIC')
    assert out['metrics']['eps_cagr_3y']['basis_status']=='VERIFIED'
    assert out['metrics']['eps_cagr_3y']['value'] is None
    assert out['metrics']['dilution_3y']['value']==0


def test_same_accession_with_different_filed_dates_is_not_distinct_filings():
    p,r=source()
    for tag in ('EarningsPerShareDiluted','WeightedAverageNumberOfDilutedSharesOutstanding'):
        for rs in p['facts']['us-gaap'][tag]['units'].values():
            for x in rs:x['accn']='SAME-ACCESSION'
    out=review_share_history(p,r,'SYNTHETIC')
    assert out['status']=='UNKNOWN' and not out['accepted_edges']
    assert any(e['reason']=='SAME_ACCESSION_IS_NOT_DISTINCT_FILINGS' for e in out['rejected_edges'])
