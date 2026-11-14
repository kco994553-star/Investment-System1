"""Synthetic explicit-debt bridge and versioned review clocks."""
from copy import deepcopy
import pytest
from investment_system.research import sector_qgv_held as held
from investment_system.research import sector_qgv_held_repair as repair
from investment_system.research.sector_qgv import digest


def source(tag='DebtLongtermAndShorttermCombinedAmount', value=30):
    def stock(v):return dict(val=v,end='2025-12-31',filed='2026-02-01',form='10-K',accn='SYN:annual')
    p={'cik':1,'facts':{'us-gaap':{'Assets':{'units':{'USD':[stock(100),dict(stock(80),end='2024-12-31')]}},
       tag:{'units':{'USD':[stock(value)]}},
       'NetIncomeLoss':{'units':{'USD':[dict(stock(9),start='2025-01-01')]}},
       'NetCashProvidedByUsedInOperatingActivities':{'units':{'USD':[dict(stock(18),start='2025-01-01')]}}}}}
    r=dict(cik='0000000001',acquired_at='2026-02-02T12:00:00Z',fiscal_year_end='2025-12-31',state='LIVE',sic='3571',profile='GENERAL')
    return p,r


def execute(p,r,template='GENERAL'):
    return held.held_q_observations(p,r,'SYN:source#sha256='+'a'*64,as_of='2026-02-03T00:00:00Z',valuation_date='2026-02-02',accounting_template=template)


@pytest.mark.parametrize('tag',['DebtLongtermAndShorttermCombinedAmount','DebtAndCapitalLeaseObligations'])
def test_explicit_total_debt_is_connected_without_adding_partial_lines(tag):
    p,r=source(tag);o,d,f=execute(p,r)
    assert f['debt']['value']==30 and o['debt_assets']['value']==.3
    assert o['roa_ttm']['value']==.1 and o['accruals_assets_ttm']['value']==-.1
    assert f['debt']['source_detail']['json_pointers']
    assert f['debt']['source_detail']['filed']=='2026-02-01'


@pytest.mark.parametrize('mutation',['absent','liabilities','wrong_unit','future','conflict','period','negative'])
def test_no_debt_invention_or_stale_fallback(mutation):
    p,r=source();tax=p['facts']['us-gaap'];node=tax['DebtLongtermAndShorttermCombinedAmount'];row=node['units']['USD'][0]
    if mutation=='absent':del tax['DebtLongtermAndShorttermCombinedAmount']
    elif mutation=='liabilities':tax['Liabilities']=tax.pop('DebtLongtermAndShorttermCombinedAmount')
    elif mutation=='wrong_unit':node['units']['shares']=node['units'].pop('USD')
    elif mutation=='future':row['filed']='2027-02-01'
    elif mutation=='period':row['end']='2025-09-30'
    elif mutation=='negative':row['val']=-30
    else:
        node['units']['USD'] += [dict(row,val=31),dict(row,filed='2026-01-01',accn='SYN:older')]
    o,d,f=execute(p,r)
    assert 'debt' not in f and o['debt_assets']['value'] is None


def test_explicit_zero_and_nonapplicability_are_separate():
    p,r=source(value=0);o,d,f=execute(p,r)
    assert o['debt_assets']['value']==0 and o['debt_assets']['status']=='VALID_ZERO'
    assert execute(p,r,'BANK')[0]['debt_assets']['status']=='NOT_APPLICABLE'
    assert execute(p,r,None)[0]['debt_assets']['value']==0


def context_fixture():
    s=dict(snapshot_id='SYN:old',input_version='old',as_of='2026-02-02T12:00:00Z',valuation_date='2026-02-02',rows=[{'observations':{'v':{'retrieved_at':'2026-02-02T11:00:00Z'}}}])
    c=dict(schema_version='sector-qgv-review-context/1',original_snapshot_hash=digest(s),valuation_date=s['valuation_date'],
        input_cutoff='2026-02-04T12:00:00Z',reviewed_at='2026-02-04T11:00:00Z',
        reviews=[dict(claim_id='SYN:debt',claim_type='INTEREST_BEARING_DEBT',subject_id='0000000001',
          status='VERIFIED',source_ref='SYN:doc#sha256='+'a'*64,source_sha256='a'*64,
          source_published='2026-02-01',source_published_precision='DATE',retrieved_at='2026-02-02T11:00:00Z',
          reviewed_at='2026-02-04T11:00:00Z',valid_from='2025-12-31',valid_to='2025-12-31',locator='/facts/us-gaap/debt')])
    return s,c


def test_review_context_preserves_original_and_does_not_verify_other_claims():
    s,c=context_fixture();old=deepcopy(s);n=repair.apply_review_context(s,c)
    assert s==old and n['rows']==s['rows'] and n['as_of']==c['input_cutoff']
    assert n['valuation_date']==s['valuation_date'] and n['snapshot_id']!=s['snapshot_id']
    assert n['review_context']['historical_system_pit_complete'] is False
    assert n['review_context']['reviews'][0]['source_published']=='2026-02-01'


@pytest.mark.parametrize('mutation',['hash','evaluation','future_review','backdate','future_acquisition','no_locator'])
def test_review_context_rejects_mixed_or_unproved_clocks(mutation):
    s,c=context_fixture()
    if mutation=='hash':c['original_snapshot_hash']='b'*64
    elif mutation=='evaluation':c['valuation_date']='2026-02-01'
    elif mutation=='future_review':c['reviews'][0]['reviewed_at']='2026-02-05T00:00:00Z'
    elif mutation=='backdate':c['input_cutoff']='2026-02-01T00:00:00Z'
    elif mutation=='future_acquisition':c['reviews'][0]['retrieved_at']='2026-02-05T00:00:00Z'
    else:c['reviews'][0]['locator']=None
    with pytest.raises(ValueError):repair.apply_review_context(s,c)


def test_new_eps_review_cannot_be_backdated_into_original_cutoff():
    from test_eps_history_connection import fixture,execute,proof
    p,r=fixture();_,_,f=execute(p,r);r['historical_share_basis']=proof(f)
    r['historical_share_basis']['reviewed_at']='2026-02-04T11:00:00Z'
    assert execute(p,r)[0]['value'] is None
    o,_,_=held.held_eps_observation(p,r,'SYN:source',as_of='2026-02-04T12:00:00Z',
        valuation_date='2026-02-02',accounting_template='GENERAL')
    assert o['value']==1


def test_q_only_repair_cli_preserves_other_axes_and_gates(tmp_path):
    import hashlib,json,zipfile,runpy
    from pathlib import Path
    p,r=source();raw=json.dumps(p).encode();sha=hashlib.sha256(raw).hexdigest();ref='SYN:source#sha256='+sha
    r['source_sha256']={'companyfacts':sha};arc=tmp_path/'facts.zip'
    with zipfile.ZipFile(arc,'w') as z:z.writestr('facts',raw)
    spec=lambda p:dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    s,c=context_fixture();s['members']=['SYN:A'];s['rows']=[dict(company_id='SYN:A',issuer_id=r['cik'],
        accounting_template='GENERAL',observations={'eps_diluted_cagr_3y':{'value':None,'provenance':[ref]}},gate={'unchanged':True})]
    c['original_snapshot_hash']=digest(s)
    plan=dict(schema_version='sector-qgv-held-repair/1',projection='UNIFIED_Q_ONLY',snapshot_hash=digest(s),review_context=c,
        archives={'x':{**spec(arc),'format':'ZIP'}},rows=[dict(company_id='SYN:A',record=r,archive_id='x',member='facts',sha256=sha,reference=ref)])
    a=tmp_path/'snapshot.json';a.write_text(json.dumps(s));b=tmp_path/'plan.json';b.write_text(json.dumps(plan))
    run=runpy.run_path(str(Path(__file__).resolve().parents[2]/'tools/sector_qgv.py'))['run'];out=tmp_path/'out'
    run(dict(mode='held-input-repair',data_kind='SYNTHETIC',transform_only=True,request_id='SYN:q',snapshot=spec(a),repair_plan=spec(b)),out,synthetic=True)
    n=json.loads((out/'snapshot.json').read_text());rr=n['rows'][0]
    assert rr['observations']['debt_assets']['value']==.3 and rr['gate']==s['rows'][0]['gate']
    assert rr['observations']['eps_diluted_cagr_3y']==s['rows'][0]['observations']['eps_diluted_cagr_3y']
    assert n['as_of']==c['input_cutoff'] and not (out/'preview.json').exists()
