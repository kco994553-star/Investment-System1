from copy import deepcopy
import pytest
from investment_system.research.top500_selection import select_top500


def job(n=501):
    day = '2026-11-04'
    ts = day+'T22:00:00Z'
    issuers = []
    for i in range(n):
        sid = f'security-{i}'
        issuers.append(dict(issuer_id=f'issuer-{i:04}', ticker=f'SYN{i}',
            eligibility='ELIGIBLE', classes_complete=True, representative_security_id=sid,
            representative_evidence=['synthetic-primary-listing'], classes=[dict(
                economic_class_id=f'class-{i}', security_id=sid, security_kind='COMMON',exchange='NYSE',
                identity_status='VERIFIED', identity_evidence=['synthetic-identity'],
                valid_from=day, valid_to=None, observed_on=day, available_at=ts,
                corporate_action_status='VERIFIED', corporate_action_evidence=['synthetic-action-ledger'],
                shares_basis='ACTUAL_CLASS_OUTSTANDING', shares=1000,
                price=1000-i, price_basis='RAW_CLOSE', currency='USD', fx_to_usd=1,
                price_security_id=sid, price_day=day, shares_day=day,
                evidence=['synthetic-price-and-shares'])]))
    return dict(schema_version='top500-input/1', evaluation_day=day, input_cutoff=ts,
        apply_at='2026-11-05T14:30:00Z', population_id='synthetic-us-candidates',
        population_version='1', policy=dict(version='top500-research/0.1.0',
        status='RESEARCH_PROPOSAL', markets=['NYSE','NASDAQ','NYSE_AMERICAN','BATS'],
        included_kinds=['COMMON','ADR','FOREIGN_COMMON','REIT'], cadence='DAILY_CLOSE'),
        coverage=dict(status='COMPLETE', evidence=['synthetic-roster-audit'],
                      expected_issuers=[r['issuer_id'] for r in issuers]), issuers=issuers)


def test_complete_and_deterministic():
    a=job(); r=select_top500(a)
    assert r['status']=='VALIDATED_RESEARCH_CANDIDATE' and len(r['members'])==500
    a['issuers'].reverse()
    assert select_top500(a)['members_hash']==r['members_hash']
    assert r['official'] is False and r['target_count']==475


@pytest.mark.parametrize('defect',['missing','duplicate','coverage','future','shares','price_day','identity','class_price','actions'])
def test_uncertainty_retains_prior(defect):
    a=job(); previous={'opaque':'previous bytes reference'}
    c=a['issuers'][0]['classes'][0]
    if defect=='missing': a['issuers'].pop()
    elif defect=='duplicate': a['issuers'].append(deepcopy(a['issuers'][0]))
    elif defect=='coverage': a['coverage']['status']='UNKNOWN'
    elif defect=='future': c['available_at']='2026-11-05T00:00:00Z'
    elif defect=='shares': c['shares_basis']='WEIGHTED_AVERAGE_DILUTED'
    elif defect=='price_day': c['price_day']='2026-11-02'
    elif defect=='identity': c['identity_status']='UNKNOWN'
    elif defect=='class_price': c['price_security_id']='other-class'
    elif defect=='actions': c['corporate_action_status']='UNKNOWN'
    r=select_top500(a,previous=previous)
    assert r['status']=='UNCONFIRMED_CANDIDATE'
    assert r['retained_confirmed']==previous and r['boundary_uncertain']


def test_adr_underlying_counted_once_and_ratio_applied():
    a=job(); c=a['issuers'][0]['classes'][0]
    c.update(security_kind='ADR', shares=2000, price=100, underlying_per_receipt=2,
             shares_basis='ACTUAL_UNDERLYING_CLASS_OUTSTANDING', adr_evidence=['synthetic-deposit-agreement'])
    r=select_top500(a); assert next(x for x in r['ranked'] if x['issuer_id']=='issuer-0000')['market_cap_usd']=='100000'
    a['issuers'][0]['classes'].append(deepcopy(c))
    assert select_top500(a)['status']=='UNCONFIRMED_CANDIDATE'


@pytest.mark.parametrize('value',[float('nan'),float('inf'),0,-1,True])
def test_invalid_monetary_input_never_ranked(value):
    a=job();a['issuers'][0]['classes'][0]['price']=value
    if isinstance(value,float) and not __import__('math').isfinite(value):
        with pytest.raises(ValueError): select_top500(a)
    else:
        assert all(r['issuer_id']!='issuer-0000' for r in select_top500(a)['ranked'])
