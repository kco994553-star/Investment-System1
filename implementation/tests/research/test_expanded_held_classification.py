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
