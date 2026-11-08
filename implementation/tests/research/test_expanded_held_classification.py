"""Synthetic issuer-cohort linkage; no private data or invented securities."""
from copy import deepcopy
import pytest
from investment_system.research.expanded_held_classification import issuer_members, reuse_issuer_reviews
from investment_system.research.common_classification.records import from_sector_snapshot, resolve
from test_classification_held_review import fixture
from investment_system.research.sector_qgv_classification import extend_held_classification

AT='2026-11-04T02:00:00Z'; KNOW='2026-11-08T05:00:00Z'

def test_issuer_cohort_preserves_all_observations_without_security_representative():
    rows=[{'cik_str':1,'ticker':'A'},{'cik_str':1,'ticker':'A.B'},{'cik_str':2,'ticker':'C'}]
    members,links=issuer_members(rows)
    assert members==['ISSUER:0000000001','ISSUER:0000000002']
    assert len(links)==3 and all(x['security_id'] is None and x['representative'] is None for x in links)
    assert issuer_members(list(reversed(rows)))==(members,links)
    with pytest.raises(ValueError,match='CATALOG_ISSUER'):issuer_members([{'cik_str':None,'ticker':'C'}])

def stores():
    s,e=fixture();s,_=extend_held_classification(s,e,rule_version='held-sec-book-correspondence/0.3.0')
    a=from_sector_snapshot(s,e,source_sha256='c'*64,recorded_at=KNOW,data_kind='SYNTHETIC')
    b=deepcopy(a);b['universe_id']='EXPANDED';b['universe_version']='1';b['members']=['ISSUER:0000000001']
    b['records'][0].update(company_id=b['members'][0],record_id='new:1')
    return s,a,b

def test_reuse_same_issuer_date_source_preserves_partial_components_and_input():
    s,a,b=stores();v=resolve(a,valuation_date='2026-11-04',knowledge_as_of=KNOW);old=deepcopy(b)
    out,audit=reuse_issuer_reviews(b,v,s,{'0000000001':{'sic':'6200','profile':'FINANCIAL'}},as_of=AT)
    r=out['records'][0]
    assert audit['reused_issuers']==1 and r['sector']['id']=='FINANCIALS' and r['accounting']['id'] is None
    assert r['upstream_record_ids']==[v['rows'][0]['record_id']] and b==old
    assert r['company_id']=='ISSUER:0000000001' and r['issuer_id']=='0000000001'

@pytest.mark.parametrize('change',['date','sic','profile','future_source','future_publication','multiple_codes'])
def test_review_reuse_never_erases_conflicts_or_applies_other_date(change):
    s,a,b=stores();v=resolve(a,valuation_date='2026-11-04',knowledge_as_of=KNOW)
    financial={'0000000001':{'sic':'6200','profile':'FINANCIAL'}}
    if change=='date':v['valuation_date']='2026-11-03'
    if change=='sic':financial['0000000001']['sic']='7372'
    if change=='profile':financial['0000000001']['profile']='GENERAL'
    if change=='future_source':v['sources'][0]['acquired_at']='2026-11-05T00:00:00Z'
    if change=='future_publication':v['sources'][0]['published_date']='2026-11-05'
    if change=='multiple_codes':
        extra=deepcopy(v['rows'][0]);extra['company_id']='OTHER';extra['record_id']='other';v['rows'].append(extra)
        s['rows'].append(dict(s['rows'][0],company_id='OTHER'))
    if change=='date':
        with pytest.raises(ValueError,match='VALUATION'):reuse_issuer_reviews(b,v,s,financial,as_of=AT)
    else:
        out,audit=reuse_issuer_reviews(b,v,s,financial,as_of=AT)
        if change=='multiple_codes':
            assert audit['reused_issuers']==1 and len(out['records'])==1 and len(out['records'][0]['upstream_record_ids'])==2
        else:
            assert audit['reused_issuers']==0 and out['records'][0]['sector']['id'] is None


def synthetic_job(tmp):
    import json,hashlib,zipfile
    from investment_system.research.sector_qgv import default_config
    def pin(name,value):
        p=tmp/name;p.write_text(json.dumps(value));return {'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
    facts={}
    for tag,mult in [('Revenues',100),('NetIncomeLoss',5),('NetCashProvidedByUsedInOperatingActivities',7),('OperatingIncomeLoss',8)]:
        facts[tag]={'units':{'USD':[{'val':mult*(year-2020),'start':f'{year}-01-01','end':f'{year}-12-31',
            'filed':f'{year+1}-02-15','form':'10-K','accn':f'{year}-synthetic'} for year in range(2020,2026)]}}
    facts['Assets']={'units':{'USD':[{'val':1000,'end':f'{year}-12-31','filed':f'{year+1}-02-15','form':'10-K','accn':f'{year}-synthetic'} for year in range(2019,2026)]}}
    catalog={str(i):{'cik_str':i,'ticker':'SYN'+str(i)} for i in range(1,23)}
    catalog['extra']={'cik_str':1,'ticker':'SYN1.B'}
    receipts=[];financial={};z=tmp/'synthetic.zip'
    acquired='2026-02-16T12:00:00Z'
    with zipfile.ZipFile(z,'w') as a:
        def add(key,value):
            body=json.dumps(value).encode();member='raw/'+key;receipt_member='receipts/'+key
            receipt={'artifact_id':key,'sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body),'source_url':'https://example.invalid/'+key,'fetched_at':acquired,'http_status':200}
            a.writestr(member,body);a.writestr(receipt_member,json.dumps(receipt));receipts.append(dict(receipt,member=member,receipt_member=receipt_member));return receipt['sha256']
        catalogsha=add('sec_tickers',catalog)
        for i in range(1,22):
            cik=str(i).zfill(10);cf=add('companyfacts:'+cik,{'cik':i,'facts':{'us-gaap':facts}})
            sub=add('submissions:'+cik,{'cik':i,'sic':'3571','sicDescription':'Electronic Computers'})
            financial[cik]={'cik':cik,'sic':'3571','profile':'GENERAL','state':'LIVE','reason_codes':[],
                'fiscal_year_end':'2025-12-31','acquired_at':acquired,'calc_version':'qgv2-calc/2026-10-23.1',
                'source_sha256':{'companyfacts':cf,'submissions':sub}}
    s,a,_=stores();s['rows']=[];s['members']=[];a['members']=[];a['records']=[];a['sources']=[]
    held={'candidates':list(catalog.values()),'financials':financial,'receipts':receipts,
          'source':{'complete':False,'observed_at':acquired,'sha256':catalogsha}}
    return {'schema_version':'held-expanded-classification-job/1','data_kind':'SYNTHETIC','as_of':AT,'recorded_at':KNOW,'request_id':'synthetic',
        'held':pin('held.json',held),'config':pin('config.json',default_config()),'upstream_snapshot':pin('upstream.json',s),
        'upstream_store':pin('store.json',a),'archive':{'path':str(z),'sha256':hashlib.sha256(z.read_bytes()).hexdigest()}}


def test_full_cli_preserves_missing_issuer_class_observations_and_uses_shared_raw_formula(tmp_path):
    import importlib.util,json,hashlib
    from pathlib import Path
    sp=importlib.util.spec_from_file_location('expanded_cli',Path(__file__).parents[2]/'tools/expanded_held_classification.py')
    cli=importlib.util.module_from_spec(sp);sp.loader.exec_module(cli)
    job=synthetic_job(tmp_path);out=tmp_path/'result';summary=cli.run(job,out,synthetic=True)
    assert summary['catalog']['issuers']==22 and summary['catalog']['ticker_observations']==23
    assert summary['catalog']['sector']==21 and summary['missing_financial_pairs']==1
    assert summary['catalog']['factor_score']==21 and summary['full_market_coverage'] is None
    preview=json.loads((out/'preview.json').read_text());rows=preview['result_rows']
    assert all(r['security_id'] is None and r['total'] is None and r['rank'] is None for r in rows)
    f=rows[0]['factors']['revenue_cagr_3y']
    assert f['raw_value']==pytest.approx((500/200)**(1/3)-1) and f['valid_n']==21
    assert rows[-1]['axes']=={'Q':None,'G':None,'V':None}
    assert all(v['denominator']==22 for v in preview['coverage']['factors'].values())
    for spec in json.loads((out/'manifest.json').read_text())['files']:
        assert hashlib.sha256((out/spec['path']).read_bytes()).hexdigest()==spec['sha256']
    assert (out/'classification-summary.csv').exists()
    with pytest.raises(ValueError,match='OUTPUT_ALREADY_EXISTS'):cli.run(job,out,synthetic=True)


def test_archive_and_cached_receipt_mismatch_fail_closed(tmp_path):
    import json,hashlib
    from investment_system.research.expanded_held_classification import build
    job=synthetic_job(tmp_path);job['archive']['sha256']='0'*64
    with pytest.raises(ValueError,match='INPUT_HASH_MISMATCH'):build(job)
    job=synthetic_job(tmp_path);p=__import__('pathlib').Path(job['held']['path']);h=json.loads(p.read_text())
    h['receipts'][0]['fetched_at']='2020-01-01T00:00:00Z';p.write_text(json.dumps(h));job['held']['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
    with pytest.raises(ValueError,match='ARCHIVE_RECEIPT_MISMATCH'):build(job)


def test_changed_classification_reuses_pinned_raw_transform_without_reopening_archive(tmp_path,monkeypatch):
    import json,hashlib,importlib.util
    from pathlib import Path
    import investment_system.research.expanded_held_classification as module
    spec=importlib.util.spec_from_file_location('expanded_cache_cli',Path(__file__).parents[2]/'tools/expanded_held_classification.py')
    cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
    job=synthetic_job(tmp_path);out=tmp_path/'first';cli.run(job,out,synthetic=True)
    pin=lambda name:{'path':str(out/name),'sha256':hashlib.sha256((out/name).read_bytes()).hexdigest()}
    job['retained_transform']={k:pin(n) for k,n in [('manifest','manifest.json'),('snapshot','snapshot.json'),('source_evidence','source-evidence.json')]}
    monkeypatch.setattr(module,'_normalize_sources',lambda *a:pytest.fail('unchanged raw transformation repeated'))
    result=module.build(job)
    assert result['summary.json']['audit']['sector_raw_reconstructed']==0
    assert result['summary.json']['audit']['sector_raw_reused']==21
    assert result['preview.json']['result_rows']==json.loads((out/'preview.json').read_text())['result_rows']
    job['archive']['sha256']='0'*64
    with pytest.raises(ValueError,match='TRANSFORM_SOURCE_MISMATCH'):module.build(job)


def gate_fixture():
    s={'as_of':AT,'valuation_date':AT[:10],'rows':[{'company_id':'ISSUER:0000000001','issuer_id':'0000000001','gate':None}]}
    raw={'cik':'0000000001','source_sha256':{'companyfacts':'c'*64},'metrics':{'roa':0.1},
         'acquired_at':'2026-11-03T00:00:00Z','profile':'GENERAL','sic':'3571','currency':'USD',
         'fiscal_year_end':'2025-12-31','calc_version':'qgv2-calc/2026-10-23.1'}
    gate={'q_industry_percentile':42.0,'calc_version':raw['calc_version'],'as_of':AT[:10],'source_as_of':AT,
          'derivation':'OFFICIAL_Q_ONLY_REPLAY','provenance':['sec-qgv2.json#sha256='+'a'*64]}
    up={**deepcopy(s),'universe_id':'Universe504','universe_version':'fixed','rows':[{'company_id':'ROW:A','issuer_id':raw['cik'],'gate':gate}]}
    sec={'as_of':AT,'calc_version':raw['calc_version'],'records':{'ROW:A':deepcopy(raw)}}
    sec['records']['ROW:A']['metrics']['revenue_volatility_5y_rank_pct']=75.0
    return s,{raw['cik']:raw},up,sec


def test_gate_reuses_same_raw_period_and_original_population_without_rescoring():
    from investment_system.research.expanded_held_classification import reuse_official_gates
    s,f,u,sec=gate_fixture();before=deepcopy(s)
    out,a=reuse_official_gates(s,f,u,sec,source_sha256='a'*64)
    assert out['rows'][0]['gate']==u['rows'][0]['gate'] and a['connected']==1 and s==before
    assert a['rows'][0]['gate_universe_id']=='Universe504'
    u['rows'].append(dict(u['rows'][0],company_id='ROW:B'));sec['records']['ROW:B']=deepcopy(sec['records']['ROW:A'])
    out,a=reuse_official_gates(s,f,u,sec,source_sha256='a'*64)
    assert a['connected']==1 and a['rows'][0]['upstream_codes']==['ROW:A','ROW:B']
    u['rows'][1]['gate']={**u['rows'][1]['gate'],'q_industry_percentile':5.0}
    assert reuse_official_gates(s,f,u,sec,source_sha256='a'*64)[1]['connected']==0


@pytest.mark.parametrize('change',['hash','period','metric','gate_date','gate_source','new_sector_q','null','future','issuer','industry_group'])
def test_gate_rejects_source_context_mismatch_and_never_uses_new_q(change):
    from investment_system.research.expanded_held_classification import reuse_official_gates
    s,f,u,sec=gate_fixture();r=f['0000000001'];g=u['rows'][0]['gate']
    if change=='hash':r['source_sha256']['companyfacts']='b'*64
    if change=='period':r['fiscal_year_end']='2024-12-31'
    if change=='metric':r['metrics']['roa']=0.2
    if change=='gate_date':g['as_of']='2026-11-02'
    if change=='gate_source':g['provenance']=[]
    if change=='new_sector_q':g['derivation']='SECTOR_Q_SCORE'
    if change=='null':g['q_industry_percentile']=None
    if change=='future':r['acquired_at']='2026-11-05T00:00:00Z'
    if change=='issuer':sec['records']['ROW:A']['cik']='0000000002'
    if change=='industry_group':r['industry_group']='DIFFERENT'
    out,a=reuse_official_gates(s,f,u,sec,source_sha256='a'*64)
    assert a['connected']==0 and out['rows'][0]['gate'] is None and a['rows'][0]['reason']


def test_gap_contract_separates_missing_connection_from_absent_data(tmp_path):
    from investment_system.research.expanded_held_classification import build
    result=build(synthetic_job(tmp_path));gaps=result['input-gaps.json']['rows']
    assert len(gaps)==22
    connected=next(r for r in gaps if r['classification']['sector']['status']=='CONFIRMED')
    assert connected['financial_period_inputs'] and connected['price']['status']=='NOT_CONNECTED'
    assert connected['evaluation_security']['status']=='UNCONFIRMED'
    assert connected['official_q_gate']['status']=='UNAVAILABLE' and not connected['official_q_gate']['new_sector_q_substituted']
    assert connected['ev_components']['missing_components_are_zero'] is False
    missing=next(r for r in gaps if r['classification']['sector']['status']=='UNKNOWN')
    assert missing['price']['status']=='VARIANT_SCOPE_UNRESOLVED'
    assert 'NOT_HELD' not in missing['price']['status']


def test_rejected_relink_cannot_retain_previously_connected_gate():
    from investment_system.research.expanded_held_classification import reuse_official_gates
    s,f,u,sec=gate_fixture();s['rows'][0]['gate']=deepcopy(u['rows'][0]['gate'])
    f['0000000001']['source_sha256']['companyfacts']='b'*64
    result,a=reuse_official_gates(s,f,u,sec,source_sha256='a'*64)
    assert a['connected']==0 and result['rows'][0]['gate'] is None
    assert s['rows'][0]['gate'] is not None


def refresh_fixture():
    s,f,u,sec=gate_fixture()
    old=f['0000000001'];old['source_sha256']['companyfacts']='b'*64
    s['rows'][0]['observations']={'roa_ttm':{'old':True},'earnings_yield_ttm':{'retained_v':True}}
    s['rows'][0]['gate']={'retained_gate':True}
    obs={'issuer_id':old['cik'],'security_id':None,'price_asof':None,
         'validation_basis':'VERIFIED_COMPONENTS','raw_components_available':True,'currency':'USD',
         'source_available_at':'2026-11-03T00:00:00Z','provenance':['facts#sha256='+'c'*64],
         'fiscal_period':{'kind':'TTM','end':'2025-12-31'},'value':0.1,
         'variant_id':'roa_ttm','formula_version':'1','status':'VALID','unit':'decimal',
         'scope':'CONSOLIDATED','retrieved_at':'2026-11-03T00:00:00Z'}
    u['rows'][0]['observations']={'roa_ttm':obs,'earnings_yield_ttm':{'must_not_copy':True}}
    return s,f,u,sec


def test_refresh_uses_retained_raw_only_without_mutating_old_input():
    from investment_system.research.expanded_held_classification import refresh_retained_financials
    s,f,u,sec=refresh_fixture();old=deepcopy((s,f,u,sec))
    out,e,a=refresh_retained_financials(s,f,u,sec)
    assert a['statuses']=={'REFRESHED':1}
    assert out['rows'][0]['observations']['roa_ttm']==u['rows'][0]['observations']['roa_ttm']
    assert out['rows'][0]['observations']['earnings_yield_ttm']=={'retained_v':True}
    assert out['rows'][0]['gate']=={'retained_gate':True}
    assert (s,f,u,sec)==old and e['0000000001']['source_sha256']['companyfacts']=='c'*64
    assert refresh_retained_financials(out,e,u,sec)[2]['statuses']=={'UNCHANGED':1}


@pytest.mark.parametrize('change',['currency','future','period','hash','issuer','security','price','class_conflict'])
def test_refresh_keeps_old_inputs_when_new_evidence_is_ineligible(change):
    from investment_system.research.expanded_held_classification import refresh_retained_financials
    s,f,u,sec=refresh_fixture();o=u['rows'][0]['observations']['roa_ttm']
    if change=='currency':o['currency']='KRW'
    if change=='future':o['source_available_at']='2026-11-05T00:00:00Z'
    if change=='period':o['fiscal_period']['end']='2026-12-31'
    if change=='hash':o['provenance']=[]
    if change=='issuer':o['issuer_id']='OTHER'
    if change=='security':o['security_id']='invented'
    if change=='price':o['price_asof']='2026-11-04'
    if change=='class_conflict':
        r=deepcopy(u['rows'][0]);r['company_id']='ROW:B';r['observations']['roa_ttm']['value']=0.2;u['rows'].append(r)
        sec['records']['ROW:B']=deepcopy(sec['records']['ROW:A'])
    out,e,a=refresh_retained_financials(s,f,u,sec)
    assert out==s and e==f and a['statuses']=={'UNAVAILABLE':1} and a['rows'][0]['reason']


def test_refresh_identical_class_rows_is_deterministic():
    from investment_system.research.expanded_held_classification import refresh_retained_financials
    s,f,u,sec=refresh_fixture();r=deepcopy(u['rows'][0]);r['company_id']='ROW:B';u['rows'].append(r)
    sec['records']['ROW:B']=deepcopy(sec['records']['ROW:A'])
    first=refresh_retained_financials(s,f,u,sec);u['rows'].reverse()
    assert refresh_retained_financials(s,f,u,sec)==first


def test_refresh_keeps_documented_missing_value_null_without_blocking_valid_factors():
    from investment_system.research.expanded_held_classification import refresh_retained_financials
    s,f,u,sec=refresh_fixture();o=u['rows'][0]['observations']['roa_ttm']
    o.update(value=None,status='MISSING_INPUT',raw_components_available=False,currency=None)
    out,e,a=refresh_retained_financials(s,f,u,sec)
    assert a['statuses']=={'REFRESHED':1} and out['rows'][0]['observations']['roa_ttm']==o
    o['value']=0
    assert refresh_retained_financials(s,f,u,sec)[2]['statuses']=={'UNAVAILABLE':1}


def test_refresh_does_not_confuse_raw_evidence_with_accounting_applicability():
    from investment_system.research.expanded_held_classification import refresh_retained_financials
    s,f,u,sec=refresh_fixture();u['rows'][0]['accounting_template']='EQUITY_REIT'
    out,e,a=refresh_retained_financials(s,f,u,sec)
    assert a['statuses']=={'REFRESHED':1}
    assert out['rows'][0]['observations']['roa_ttm']['value']==0.1
