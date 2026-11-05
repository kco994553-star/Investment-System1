"""Synthetic evidence: never treat SEC observations as a complete tradable universe."""
from copy import deepcopy
import importlib
import importlib.util
from pathlib import Path
import pytest

MODULE = 'investment_system.research.current_expansion'

def api():
    assert importlib.util.find_spec(MODULE) is not None, 'current expansion execution path is missing'
    return importlib.import_module(MODULE)


def inputs(n=12):
    from investment_system.universe import sec_qgv2 as sec
    from investment_system.qgv import v2_factors as vf, v2_scoring as vs
    source = {'source_ref': 'SYNTHETIC:complete-iex-list', 'observed_at': '2026-11-02T21:00:00Z',
              'scope': 'IEX_TRADABLE', 'complete': True, 'basis_date': '2026-11-02'}
    candidates=[]; evidence={}; financials={}
    for i in range(n):
        cik=str(i+1).zfill(10); ticker=f'T{i}'
        candidates.append({'cik_str': i+1, 'ticker': ticker, 'title': f'Synthetic {i}'})
        e={'cik':cik,'security_id':f'SYNTHETIC-SEC-{i}', 'issuer_id':f'SYNTHETIC-ISSUER-{i}',
           'ticker':ticker,'exchange':'NASDAQ','security_type':'COMMON','representative':True,
           'listed':True,'iex_tradable':True,'shell_or_spac':False,'valid_from':'2026-01-01', 'valid_to':None,
           'basis_date':'2026-11-02','source_ref':'SYNTHETIC:identity-and-eligibility',
           'issuer_market_cap_usd':300e6,'market_cap_basis':'ALL_CLASSES',
           'price':10.0,'price_currency':'USD','price_basis':'RAW','price_date':'2026-11-02',
           'quote_security_id':f'SYNTHETIC-SEC-{i}', 'price_source_ref':'SYNTHETIC:regular-trade'}
        evidence[str(i)]=e
        r=sec.empty_record(cik=cik);r.update(state='LIVE',calc_version=vf.CALC_VERSION,profile='GENERAL',
            industry_group='TECHNOLOGY',currency='USD',fiscal_year_end='2025-12-31',
            acquired_at='2026-11-01T01:00:00Z',reason_codes=[],
            metrics={m:float(i+1) for specs in vs.SUBMETRICS['GENERAL'].values() for m,_ in specs})
        financials[cik]=r
    return candidates,evidence,financials,source


def run(*, n=12, mutate=None):
    a=api();c,e,f,s=inputs(n)
    if mutate:mutate(c,e,f,s)
    return a.evaluate(c, financials=f,evidence=e,source=s,basis_date='2026-11-02')


def test_partial_roster_keeps_denominator_and_blocks_relative_scores():
    def mutate(c,e,f,s):
        s.update(complete=False,scope='SEC_TICKER_OBSERVATIONS');e.clear();f.pop('0000000001')
    out=run(mutate=mutate)
    assert out['counts']['candidate_rows']==12
    assert out['counts']['financial_rows']==11
    assert out['full_market_denominator'] is None
    assert out['counts']['unknown']==12 and out['counts']['scored']==0
    assert all(r['score'] is None and r['rank'] is None for r in out['rows'])


def test_complete_group_runs_shared_engine_without_changing_fixed_504():
    out=run()
    assert out['universe_version']=='U-US-EXPANDED-CURRENT/1'
    assert out['counts']['eligible']==12 and out['counts']['scored']==12
    assert out['coverage']['denominator']==12
    assert out['coverage']['Q']==12 and out['coverage']['G']==12
    assert out['coverage']['V']==0 and out['coverage']['ranked']==0
    assert out['calc_version']=='qgv2-calc/2026-10-23.1'


def test_missing_input_stays_in_complete_population_denominator():
    def mutate(c,e,f,s):f.pop('0000000001')
    out=run(mutate=mutate)
    assert out['counts']['eligible']==12 and out['coverage']['denominator']==12
    assert out['counts']['financial_rows']==11
    assert out['coverage']['Q']==11


@pytest.mark.parametrize('field,value,reason',[
    ('security_id',None,'SECURITY_ID_UNCONFIRMED'),('representative',None,'REPRESENTATIVE_UNCONFIRMED'),
    ('price_date','2026-10-30','PRICE_DATE_MISMATCH'),('quote_security_id','WRONG','PRICE_IDENTITY_MISMATCH'),
    ('issuer_market_cap_usd',None,'ISSUER_MARKET_CAP_UNCONFIRMED'),('market_cap_basis','ONE_CLASS','ISSUER_MARKET_CAP_UNCONFIRMED'),
    ('valid_to','2026-11-01','IDENTITY_DATE_UNCONFIRMED'),('basis_date','2026-10-30','EVIDENCE_DATE_MISMATCH'),
])
def test_evidence_gates_prevent_partial_population_ranks(field,value,reason):
    out=run(mutate=lambda c,e,f,s:e['0'].__setitem__(field,value))
    assert reason in out['rows'][0]['reasons']
    assert out['counts']['scored']==0 and out['coverage']['Q'] is None


def test_exclusions_and_retention_need_prior_membership_evidence():
    def mutate(c,e,f,s):
        e['0'].update(security_type='ETF');e['1'].update(issuer_market_cap_usd=220e6,price=4)
        e['2'].update(issuer_market_cap_usd=220e6,price=4,previous_member=True,
                      previous_membership_ref='SYNTHETIC:2026-10-30-approved-membership', previous_membership_date='2026-10-30')
    out=run(mutate=mutate)
    assert out['counts']['excluded']==2 and out['counts']['eligible']==10
    assert out['rows'][2]['eligibility']=='ELIGIBLE'


def test_duplicate_security_or_representative_blocks_population():
    def mutate(c,e,f,s):e['1'].update(security_id=e['0']['security_id'],quote_security_id=e['0']['security_id'])
    out=run(mutate=mutate)
    assert 'DUPLICATE_SECURITY_ID' in out['population_reasons'] and out['counts']['scored']==0


def test_invalid_cik_not_invented_from_ticker():
    out=run(mutate=lambda c,e,f,s:c[0].update(cik_str=None))
    assert out['rows'][0]['cik'] is None and out['rows'][0]['security_id'] is None
    assert 'ISSUER_LINK_UNCONFIRMED' in out['rows'][0]['reasons']


def test_held_zip_receipts_and_missing_files_keep_observed_rows(tmp_path):
    import json,hashlib,zipfile
    a=api();assert hasattr(a,'read_held_archive'), 'held archive adapter missing'
    path=tmp_path/'held.zip'
    entries={'sec_tickers':{'0':{'cik_str':1,'ticker':'AAA','title':'Synthetic'},'1':{'cik_str':2,'ticker':'BBB','title':'Absent'}},
             'companyfacts__0000000001':{'cik':1,'facts':{}},'submissions__0000000001':{'cik':1,'sic':'3674'}}
    with zipfile.ZipFile(path,'w') as z:
        for key,value in entries.items():
            b=json.dumps(value).encode();z.writestr('data/raw/blobs/'+key,b)
            z.writestr('data/raw/manifests/'+key+'.json',json.dumps({'sha256':hashlib.sha256(b).hexdigest(),
                'bytes':len(b),'fetched_at':'2026-09-25T01:00:00Z','source_url':'https://www.sec.gov/SYNTHETIC'}))
    held=a.read_held_archive(path,basis_date='2026-11-02')
    assert len(held['candidates'])==2 and len(held['financials'])==1
    assert held['financials']['0000000001']['reason_codes']==['NO_ANNUAL_SEC_FINANCIALS']
    assert held['source']['complete'] is False and len(held['receipts'])==3
    with pytest.warns(UserWarning,match='Duplicate name'):
        with zipfile.ZipFile(path,'a') as z:z.writestr('data/raw/blobs/sec_tickers',b'{}')
    with pytest.raises(ValueError,match='DUPLICATE_ARCHIVE_MEMBER'):a.read_held_archive(path,basis_date='2026-11-02')


def test_archive_cli_has_no_network_and_private_output_guard(tmp_path):
    import json,hashlib,zipfile,subprocess,sys
    tool=Path(__file__).resolve().parents[2]/'tools/current_expansion.py'
    path=tmp_path/'held.zip';body=b'{"0":{"cik_str":1,"ticker":"SYN","title":"Synthetic"}}'
    with zipfile.ZipFile(path,'w') as z:
        z.writestr('data/raw/blobs/sec_tickers',body)
        z.writestr('data/raw/manifests/sec_tickers.json',json.dumps({'sha256':hashlib.sha256(body).hexdigest(),
            'bytes':len(body),'fetched_at':'2026-09-25T01:00:00Z','source_url':'https://www.sec.gov/SYNTHETIC'}))
    args=[sys.executable,str(tool),'--archive',str(path),'--basis-date','2026-11-02','--output-dir',str(tmp_path/'out')]
    proc=subprocess.run(args,capture_output=True,text=True)
    assert proc.returncode==0 and proc.stdout.strip()=='CURRENT_EXPANSION_PRIVATE_OUTPUT_WRITTEN'
    out=json.loads((tmp_path/'out/current-expansion.json').read_bytes())
    assert out['counts']['candidate_rows']==1 and out['counts']['unknown']==1
    assert (tmp_path/'out/current-expansion.json').stat().st_mode & 0o777 == 0o600
    again=subprocess.run(args,capture_output=True,text=True)
    assert again.returncode==1 and 'SYN' not in again.stderr
    args[-1]=str(tool.parent/'forbidden-output')
    denied=subprocess.run(args,capture_output=True,text=True)
    assert denied.returncode!=0 and 'OUTPUT_MUST_BE_OUTSIDE_GIT' in denied.stderr


@pytest.mark.parametrize('change',[
    {'price':4,'price_date':'2026-10-30'},
    {'price':4,'quote_security_id':'OTHER-SECURITY'},
    {'security_type':'ETF','valid_to':'2026-11-01'},
    {'issuer_market_cap_usd':100e6,'basis_date':'2026-10-30'},
])
def test_unconfirmed_exclusion_cannot_shrink_scoring_population(change):
    out=run(mutate=lambda c,e,f,s:e['0'].update(change))
    assert out['rows'][0]['eligibility']=='UNKNOWN'
    assert out['counts']['scored']==0 and out['coverage']['denominator'] is None


def test_confirmed_type_exclusion_does_not_require_irrelevant_price():
    out=run(mutate=lambda c,e,f,s:e['0'].update(security_type='ETF',price=None,price_date=None))
    assert out['rows'][0]['eligibility']=='EXCLUDED' and out['counts']['scored']==11


def test_complete_financial_fixture_reaches_v_and_existing_official_rank():
    import json
    from datetime import datetime,timezone
    from investment_system.universe import sec_qgv2 as sec
    fixture=Path(__file__).resolve().parents[1]/'test_sec_qgv2.py'
    spec=importlib.util.spec_from_file_location('synthetic_sec_facts',fixture)
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    def mutate(c,e,f,s):
        for cik in f:
            facts=helper.simple_company();facts['cik']=int(cik)
            f[cik]=sec.build_row(cik=cik,companyfacts_body=json.dumps(facts).encode(),
                submissions_body=json.dumps({'cik':int(cik),'sic':'3674'}).encode(),
                acquired_at=datetime(2026,11,1,tzinfo=timezone.utc))
    out=run(mutate=mutate)
    assert out['coverage']['simultaneous']==12 and out['coverage']['ranked']==12
    assert sorted(r['rank'] for r in out['rows'])==list(range(1,13))
    assert out['coverage']['preset_actual_total']==12
