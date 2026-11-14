from copy import deepcopy
import pytest
from investment_system.research.retained_coverage import saved_axis_losses


def run(a,b,day='2026-11-04'):
    return saved_axis_losses(a,b,official_day=day,evaluation_day='2026-11-04',
                             reason_priority=['PREPARING','SHARE_BASIS','RAW_MISSING'])


def rows():
    a=[dict(company_id=c,issuer_id=i,score=s) for c,i,s in
       [('SYN:A','issuer1',10),('SYN:B','issuer1',10),('SYN:C','issuer2',0),('SYN:D','issuer3',None)]]
    b=deepcopy(a)
    for r in b:r['score']=None
    b[0]['reasons']=['SHARE_BASIS','RAW_MISSING'];b[1]['reasons']=['SHARE_BASIS']
    b[2]['reasons']=['PREPARING']
    return a,b


def test_unique_issuer_losses_overlap_zero_score_and_original_denominator():
    a,b=rows();out=run(a,b)
    assert out['denominator']==3 and out['code_rows']==4 and out['official_valid']==2
    assert out['comparable_loss_count']==2
    assert out['representative']=={'SHARE_BASIS':1,'PREPARING':1}
    assert out['multiple']=={'SHARE_BASIS':1,'RAW_MISSING':1,'PREPARING':1}
    b[1]['score']=20
    assert run(a,b)['comparable_loss_count']==1  # other valid code of issuer1 preserved


def test_different_price_day_is_not_a_same_day_loss_measurement():
    a,b=rows();out=run(a,b,'2026-11-02')
    assert out['comparable_loss_count'] is None and out['observed_official_only']==2
    assert out['comparison_status']=='NOT_MEASURED_SAME_DAY'


@pytest.mark.parametrize('case',['duplicate','missing','issuer','nan'])
def test_rejects_changed_population_identity_or_invalid_score(case):
    a,b=rows()
    if case=='duplicate':b.append(deepcopy(b[0]))
    elif case=='missing':b.pop()
    elif case=='issuer':b[0]['issuer_id']='wrong-issuer'
    else:b[0]['score']=float('nan')
    with pytest.raises(ValueError):run(a,b)


def test_missing_cause_is_unassessed_instead_of_a_fabricated_input_failure():
    a,b=rows();b[0].pop('reasons');b[1].pop('reasons')
    out=run(a,b)
    assert out['unassessed_issuers']==1 and out['representative']['UNASSESSED']==1
