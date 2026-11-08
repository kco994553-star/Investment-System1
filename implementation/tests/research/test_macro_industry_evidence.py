from copy import deepcopy
import pytest
from test_common_classification_technical_macro import fixture
from investment_system.research.sector_qgv import digest
from investment_system.research.common_classification.catalog import dictionary
from investment_system.research.common_classification.macro_evidence import query_industry_evidence, current_taxonomy


def sample():
    view,_,_=fixture(2)
    view['rows'][1]['industry']['id']='software'
    context={k:view[k] for k in ('valuation_date','classification_hash','dictionary_version','mapping_version')}
    evidence={'evidence_id':'SYN:DEFINITION','sha256':'b'*64,'ref':'https://example.invalid/source-definition',
        'locator':'table 1','published_at':'2017-01-04','available_at':'2017-01-05T12:00:00Z',
        'acquired_at':'2017-01-05T13:00:00Z','status':'VERIFIED'}
    mapping={'mapping_id':'SYN:MAP','revision_id':'1','supersedes':None,'status':'CONFIRMED',
        'source':{'system':'SYN_STAT','code':'S01','name':'Synthetic source industry','version':'2017'},
        'relation':'MULTIPLE','targets':[
            {'sector_id':'INFORMATION_TECHNOLOGY','industry_id':'semiconductors','scope_relation':'OVERLAP'},
            {'sector_id':'INFORMATION_TECHNOLOGY','industry_id':'software','scope_relation':'OVERLAP'}],
        'includes':['Published source scope'],'excludes':['Other source activities'],
        'valid_from':'2017-01-01','valid_to':'2018-01-01','reviewed_at':'2017-01-06T20:00:00Z',
        'available_at':'2017-01-05T12:00:00Z','acquired_at':'2017-01-05T13:00:00Z',
        'evidence_refs':['SYN:DEFINITION'],'series_ids':['SYN:SERIES'],'unknown_reasons':[], 'allocation_weights':None}
    links={'schema_version':'macro-industry-evidence/1','data_kind':'SYNTHETIC','classification_context':context,
        'evidence':[evidence],'mappings':[mapping]}
    evidence['source_definition']=deepcopy(mapping['source'])
    evidence['series_ids']=['SYN:SERIES']
    cache={'schema_version':'macro-current-query/1','query_at':'2017-01-06T21:00:00Z','cache_asof':'2017-01-06T19:00:00Z',
        'series':{'SYN:SERIES':{'source_id':'SYN:SERIES','value':0,'unit':'hours','frequency':'M','seasonal_adjustment':'SA',
        'observation_period':'2016-12','query_usable':True,'stale':False,'available_at':'2017-01-05T13:00:00Z',
        'official_release_at':None,'source_version_id':None,'archive_version_id':'SYN:ARCHIVE',
        'first_acquired_at':'2017-01-05T13:00:00Z','last_successful_update_at':'2017-01-05T13:00:00Z',
        'historical_pit_eligible':False,'historical_pit_reason':'RELEASE_NOT_PROVEN'}}}
    return view,links,cache


def test_multiple_scope_evidence_query_preserves_zero_and_single_observation_no_weights():
    v,l,c=sample();before=deepcopy((v,l,c));out=query_industry_evidence(v,l,c)
    assert len(out['observations'])==1 and len(out['companies'])==2
    assert all(r['related_series_ids']==['SYN:SERIES'] for r in out['companies'])
    assert out['observations']['SYN:SERIES']['value']==0
    assert out['observations']['SYN:SERIES']['official_release_at'] is None
    assert out['aggregate_value'] is None and out['probabilities'] is None
    assert out['historical_pit_certified'] is False and (v,l,c)==before
    assert out['counts']=={'company_rows':2,'linked_companies':2,'active_mappings':1,'unique_series':1}


@pytest.mark.parametrize('fault', ['version','hash','evidence_missing','source_version','definition_version','series_definition','target_parent','duplicate','weights'])
def test_invalid_contract_rejected(fault):
    v,l,c=sample();m=l['mappings'][0]
    if fault=='version':l['classification_context']['mapping_version']='OTHER'
    if fault=='hash':l['classification_context']['classification_hash']='f'*64
    if fault=='evidence_missing':m['evidence_refs']=['MISSING']
    if fault=='source_version':m['source']['version']=None
    if fault=='definition_version':m['source']['version']='2018'
    if fault=='series_definition':m['series_ids']=['UNSUPPORTED_SERIES']
    if fault=='target_parent':m['targets'][0]['sector_id']='FINANCIALS'
    if fault=='duplicate':l['mappings'].append(deepcopy(m))
    if fault=='weights':m['allocation_weights']=[.5,.5]
    with pytest.raises(ValueError):query_industry_evidence(v,l,c)


@pytest.mark.parametrize('fault,reason', [('outside','OUTSIDE_APPLICABILITY'),('future','EVIDENCE_NOT_AVAILABLE'),('same_day','EVIDENCE_TIME_UNKNOWN'),('query_future','CACHE_FROM_FUTURE')])
def test_unavailable_mapping_preserves_unknown_without_new_observation(fault,reason):
    v,l,c=sample()
    if fault=='outside':l['mappings'][0]['valid_to']='2017-01-06'
    if fault=='future':l['evidence'][0]['acquired_at']='2017-01-07T00:00:00Z'
    if fault=='same_day':l['evidence'][0]['available_at']='2017-01-06'
    if fault=='query_future':c['query_at']='2017-01-07T00:00:00Z'
    out=query_industry_evidence(v,l,c)
    assert out['counts']['linked_companies']==0
    assert reason in out['diagnostics'][0]['reasons']
    assert out['aggregate_value'] is None


def test_future_observation_is_not_exposed_as_usable_value():
    v,l,c=sample();c['series']['SYN:SERIES']['available_at']='2017-01-07T00:00:00Z'
    out=query_industry_evidence(v,l,c)
    assert out['counts']['linked_companies']==2
    assert out['observations']['SYN:SERIES']['value'] is None
    assert all(not r['query_usable_series_ids'] for r in out['companies'])


def test_partial_and_unknown_source_scope_not_promoted_to_exact():
    v,l,c=sample();m=l['mappings'][0];m['relation']='PARTIAL';m['targets']=m['targets'][:1]
    out=query_industry_evidence(v,l,c)
    assert out['mappings'][0]['relation']=='PARTIAL' and out['counts']['linked_companies']==1
    m.update(status='UNKNOWN',relation='UNKNOWN',targets=[],evidence_refs=[],unknown_reasons=['OFFICIAL_DEFINITION_NOT_HELD'])
    m['source']['version']=None
    out=query_industry_evidence(v,l,c)
    assert out['counts']['linked_companies']==0 and out['mappings'][0]['unknown_reasons']==['OFFICIAL_DEFINITION_NOT_HELD']


def test_legacy_dictionary_hashes_preserved_current_taxonomy_uses_stable_ids_and_scopes():
    assert digest(dictionary('common-industry-dictionary/1'))=='fa764a4d520cd2817ff8c8e3f55f4de6ad0b767f739d311f4c1b5665564bb44e'
    assert digest(dictionary('common-industry-dictionary/2'))=='2ad03d247c30ce335612b69e70d69bab26959273b1e893cc8f71c8991634d861'
    current=current_taxonomy();by={r['id']:r for r in current['sectors']}
    assert current['name']=='투자시스템 공통 10섹터'
    assert set(by)==set(dictionary()['sectors'])
    assert by['TELECOMMUNICATIONS']['name']=='통신서비스'
    assert all(r['definition'] and r['includes'] and r['excludes'] and r['evidence_refs'] for r in by.values())
    assert current['classification_effect']=='NONE_DISPLAY_DEFINITION_ONLY'


def test_offline_cli_reuses_hash_pinned_inputs_and_refuses_existing_output(tmp_path):
    import importlib.util,json
    from pathlib import Path
    from test_classification_counts import pin
    spec=importlib.util.spec_from_file_location('macro_query_cli',Path(__file__).parents[2]/'tools/macro_industry_evidence.py')
    cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
    v,l,c=sample();job={'schema_version':'macro-industry-query-job/1','data_kind':'SYNTHETIC'}
    for key,data in [('view',v),('mappings',l),('macro_cache',c)]:job[key]=pin(tmp_path,key+'.json',data)
    out=tmp_path/'out';report=cli.run(job,out,synthetic=True)
    assert report['counts']['linked_companies']==2
    assert json.loads((out/'manifest.json').read_text())['source_files']['view']['sha256']==job['view']['sha256']
    with pytest.raises(ValueError,match='OUTPUT_ALREADY_EXISTS'):cli.run(job,out,synthetic=True)
