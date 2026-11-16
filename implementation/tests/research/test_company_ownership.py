"""Ownership adapter: synthetic inputs only; never legal ownership inferred from numbers."""
from copy import deepcopy
from decimal import Decimal
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path

import pytest


def api():
    name='investment_system.research.company_ownership'
    assert importlib.util.find_spec(name) is not None, 'ownership observation adapter is not implemented'
    return importlib.import_module(name)


def encoded(v):
    return (json.dumps(v,ensure_ascii=False,sort_keys=True)+'\n').encode()


def time(value=None,precision=None):
    return {'value':value,'precision':precision or ('DATETIME' if value and 'T' in value else 'DATE' if value else 'UNKNOWN')}


def fixture():
    text=b'<p>Synthetic Parent owns approximately 60 percent of Class A shares of Synthetic Child. Synthetic Child is a direct subsidiary.</p>'
    sha=hashlib.sha256(text).hexdigest()
    registry=encoded({'schema_version':'sector-qgv-input/1','rows':[
        {'issuer_id':'SYN-A','company_id':'SYN:A','security_id':'SYN-SEC-A'},
        {'issuer_id':'SYN-A','company_id':'SYN:A2','security_id':'SYN-SEC-A2'},
        {'issuer_id':'SYN-B','company_id':'SYN:B','security_id':'SYN-SEC-B'},
        {'issuer_id':'SYN-C','company_id':'SYN:C','security_id':None}]})
    ev={'evidence_id':'e1','source_kind':'PRIMARY_DISCLOSURE','url':'https://example.org/synthetic',
        'document_id':'SYN-DOC-1','locator':'paragraph1','artifact_hash':sha,
        'excerpt':'Synthetic Child is a direct subsidiary.',
        'published':time('2026-01-02'),'available':time('2026-01-02'),
        'acquired':time('2026-01-03T09:00:00Z'),'source_period':'2025-12-31',
        'publication':'PUBLIC_APPROVED'}
    temporal={'valid_from':None,'valid_to':None,'observed_on':'2025-12-31',
        'system_known_at':'2026-01-03T09:00:00Z','reviewed_at':'2026-01-04T10:00:00Z'}
    observation={'observation_id':'o1','metric':'SHARE_CAPITAL','value':'60','lower':None,'upper':None,
        'qualifier':'APPROX','unit':'PERCENT','denominator_basis':'CLASS_OUTSTANDING',
        'security_id':'SYN-SEC-B','share_class':'Class A','observed_as_of':'2025-12-31','missing_reason':None}
    assertion={'assertion_id':'a1','version':1,'previous_version':None,'source_entity_id':'SYN-A',
        'target_entity_id':'SYN-B','source_mention_id':None,'target_mention_id':None,
        'type':'OWNERSHIP','directness':'DIRECT','capacity':'CORPORATE_INVESTMENT','status':'VERIFIED',
        'statement':'Synthetic reviewed economic investment; no control inference from percentage.',
        'evidence_ids':['e1'],'observations':[observation],'temporal':temporal,'publication':'PUBLIC_APPROVED'}
    control=deepcopy(assertion);control.update(assertion_id='c1',type='PARENT_SUBSIDIARY',statement='Synthetic Child is a direct subsidiary.',observations=[])
    packet={'schema_version':'company-ownership-input/1','dataset_id':'SYN-OWN','version':'1','data_kind':'SYNTHETIC',
        'identity_context':{'namespace':'COMMON_ISSUER','version':'synthetic1','registry_hash':hashlib.sha256(registry).hexdigest()},
        'entities':[{'entity_id':i,'display_name':name,'kind':'LEGAL_ENTITY','company_ids':codes,
            'identity_ref':{'issuer_id':i,'security_id':None,'listing_id':None},'publication':'PUBLIC_APPROVED'}
            for i,name,codes in [('SYN-A','합성 모회사',['SYN:A','SYN:A2']),('SYN-B','합성 자회사',['SYN:B']),('SYN-C','같은 이름',['SYN:C'])]],
        'mentions':[],'evidence':[ev],'assertions':[assertion,control],'paths':[],
        'collection':{'target_entity_ids':['SYN-A'],'reviewed_entity_ids':['SYN-A'],'scope':'synthetic disclosure paragraph',
            'completeness':'PARTIAL','last_success_at':'2026-01-04T10:00:00Z','last_failure':None},
        'publication':'PUBLIC_APPROVED'}
    return packet,registry,{sha:text}


def bundle():
    p,r,a=fixture();return api().normalize_packet(p,r,a)


def view(b=None,**kwargs):
    return api().company_view(b or bundle(),entity_id='SYN-A',valid_on='2025-12-31',
        knowledge_at='2026-01-05T12:00:00Z',generated_at='2026-01-05T12:00:00Z',**kwargs)


def test_separate_ownership_control_reverse_same_fact_and_no_duplicate_issuer():
    b=bundle();v=view(b)
    assert len(v['relationships'])==2
    assert {r['type'] for r in v['relationships']}=={'OWNERSHIP','PARENT_SUBSIDIARY'}
    reverse=api().company_view(b,entity_id='SYN-B',valid_on='2025-12-31',knowledge_at='2026-01-05T12:00:00Z',generated_at='2026-01-05T12:00:00Z')
    assert {r['relationship_id'] for r in v['relationships']}=={r['relationship_id'] for r in reverse['relationships']}
    assert all(r['relative_direction']=='INCOMING' for r in reverse['relationships'])
    assert v['counts']['legal_entities']==2 and v['counts']['code_rows']==3
    assert v['relationship_coverage'] is None


def test_minority_and_zero_never_infer_control_or_end_date():
    p,r,a=fixture();p['assertions']=p['assertions'][:1];p['assertions'][0]['observations'][0]['value']='0'
    v=view(api().normalize_packet(p,r,a));x=v['relationships'][0]
    assert x['positive_ownership'] is False and x['temporal']['valid_to'] is None
    assert x['type']=='OWNERSHIP' and x['observations'][0]['value']=='0'
    p['assertions'][0]['observations'][0]['value']='99.99'
    assert len(view(api().normalize_packet(p,r,a))['relationships'])==1


@pytest.mark.parametrize('value',['NaN','Infinity','-1','100.0001',True,0.5])
def test_percent_rejects_invalid_or_implicit_float(value):
    p,r,a=fixture();p['assertions'][0]['observations'][0]['value']=value
    with pytest.raises(ValueError,match='PERCENT'):api().normalize_packet(p,r,a)


def test_null_range_and_class_denominator_preserved():
    p,r,a=fixture();o=p['assertions'][0]['observations'][0]
    o.update(value=None,qualifier='NOT_DISCLOSED',missing_reason='NOT_DISCLOSED')
    assert view(api().normalize_packet(p,r,a))['relationships'][0]['observations'][0]['value'] is None
    o.update(qualifier='RANGE',lower='20.01',upper='20.99',missing_reason=None)
    b=api().normalize_packet(p,r,a);assert b['assertions'][0]['observations'][0]['upper']=='20.99'
    other=deepcopy(o);other.update(observation_id='o2',metric='VOTING_POWER',denominator_basis='VOTING_RIGHTS',value='80',lower=None,upper=None,qualifier='EXACT')
    p['assertions'][0]['observations'].append(other)
    assert view(api().normalize_packet(p,r,a))['relationships'][0]['state']!='CONFLICT'


def test_same_basis_conflict_not_silently_last_wins():
    p,r,a=fixture();o=deepcopy(p['assertions'][0]['observations'][0]);o.update(observation_id='o2',value='30')
    p['assertions'][0]['observations'].append(o)
    rel=view(api().normalize_packet(p,r,a))['relationships'][0]
    assert rel['state']=='CONFLICT' and len(rel['observations'])==2


def test_13f_is_not_corporate_investment_or_parent_evidence():
    p,r,a=fixture();p['evidence'][0]['source_kind']='FORM_13F'
    with pytest.raises(ValueError,match='13F'):api().normalize_packet(p,r,a)
    p['assertions']=p['assertions'][:1];p['assertions'][0]['capacity']='INVESTMENT_DISCRETION'
    p['assertions'][0]['observations'][0]['metric']='MANAGED_HOLDINGS'
    assert view(api().normalize_packet(p,r,a))['relationships'][0]['capacity']=='INVESTMENT_DISCRETION'


def test_unresolved_names_and_group_list_are_not_invented_entities_or_direct_edges():
    p,r,a=fixture();p['mentions']=[{'mention_id':'m1','name':'Same name foreign unlisted subsidiary','evidence_ids':['e1']}]
    x=p['assertions'][1];x.update(target_entity_id=None,target_mention_id='m1',directness='UNKNOWN')
    p['assertions']=[x];v=view(api().normalize_packet(p,r,a))
    assert v['relationships']==[] and len(v['unresolved_assertions'])==1
    assert v['unresolved_assertions'][0]['directness']=='UNKNOWN'


def test_issuer_registry_hash_security_and_unknown_entity_fail_closed():
    for change,code in [(lambda p:p['identity_context'].update(registry_hash='0'*64),'IDENTITY_HASH'),
        (lambda p:p['entities'][0].update(entity_id='invented'),'IDENTITY'),
        (lambda p:p['assertions'][0]['observations'][0].update(security_id='SYN-SEC-A'),'SECURITY')]:
        p,r,a=fixture();change(p)
        with pytest.raises(ValueError,match=code):api().normalize_packet(p,r,a)


def test_source_hash_locator_excerpt_and_reference_must_be_verified():
    for change,code in [(lambda p:p['evidence'][0].update(artifact_hash='0'*64),'ARTIFACT'),
        (lambda p:p['evidence'][0].update(excerpt='not in retained document'),'EXCERPT'),
        (lambda p:p['evidence'][0].update(locator=''),'LOCATOR'),
        (lambda p:p['assertions'][0].update(evidence_ids=['missing']),'REFERENCE')]:
        p,r,a=fixture();change(p)
        with pytest.raises(ValueError,match=code):api().normalize_packet(p,r,a)


def test_date_precision_no_backfill_future_and_late_acquisition():
    b=bundle();v=view(b)
    assert v['evidence'][0]['published']==time('2026-01-02')
    assert all(x['temporal']['valid_from'] is None for x in v['relationships'])
    old=api().company_view(b,entity_id='SYN-A',valid_on='2025-12-31',knowledge_at='2026-01-03T08:00:00Z',generated_at='2026-01-05T12:00:00Z')
    assert old['relationships']==[] and old['diagnostics']['not_available_assertions']==2
    current=api().company_view(b,entity_id='SYN-A',valid_on='2026-02-01',knowledge_at='2026-02-02T12:00:00Z',generated_at='2026-02-02T12:00:00Z')
    assert all(x['state']=='REVIEW_REQUIRED' for x in current['relationships'])


def test_unknown_or_same_day_availability_not_imputed():
    p,r,a=fixture();p['evidence'][0]['available']=time()
    v=view(api().normalize_packet(p,r,a));assert not v['relationships']
    p['evidence'][0]['available']=time('2026-01-05')
    assert not view(api().normalize_packet(p,r,a))['relationships']


def test_version_history_planned_completed_disposed_and_future_versions():
    p,r,a=fixture();p['assertions']=p['assertions'][1:];x=p['assertions'][0];x['status']='PLANNED'
    b=api().normalize_packet(p,r,a);v=view(b);assert v['relationships'][0]['state']=='PLANNED'
    y=deepcopy(x);y.update(version=2,previous_version=1,status='COMPLETED');y['temporal'].update(system_known_at='2026-01-06T12:00:00Z',reviewed_at='2026-01-06T12:00:00Z')
    p['assertions'].append(y);b2=api().normalize_packet(p,r,a);merged=api().merge_update(b,b2,outcome='SUCCESS',attempted_at='2026-01-06T12:00:00Z')
    assert len(merged['dataset']['assertions'])==2 and view(merged['dataset'])['relationships'][0]['state']=='PLANNED'
    z=deepcopy(y);z.update(version=3,previous_version=2,status='DISPOSED');z['temporal'].update(valid_to='2026-01-07',system_known_at='2026-01-08T12:00:00Z',reviewed_at='2026-01-08T12:00:00Z')
    p['assertions'].append(z);v=api().company_view(api().normalize_packet(p,r,a),entity_id='SYN-A',valid_on='2026-01-09',knowledge_at='2026-01-10T12:00:00Z',generated_at='2026-01-10T12:00:00Z')
    assert v['relationships'][0]['state']=='DISPOSED'


def test_update_failure_preserves_original_bytes_times_history_and_absence_not_delete():
    b=bundle();before=encoded(b)
    for outcome in ('FAILED','PARTIAL','PARSE_FAILED'):
        out=api().merge_update(b,None,outcome=outcome,attempted_at='2026-01-06T12:00:00Z')
        assert encoded(out['dataset'])==before and out['attempt']['outcome']==outcome
    empty=deepcopy(b);empty['assertions']=[]
    assert len(api().merge_update(b,empty,outcome='SUCCESS',attempted_at='2026-01-06T12:00:00Z')['dataset']['assertions'])==2
    changed=deepcopy(b);changed['assertions'][0]['statement']='Changed existing version'
    with pytest.raises(ValueError,match='IMMUTABLE'):api().merge_update(b,changed,outcome='SUCCESS',attempted_at='2026-01-06T12:00:00Z')


def test_paths_do_not_compute_lookthrough_and_cycles_not_duplicate_facts():
    p,r,a=fixture();child=deepcopy(p['assertions'][1]);child.update(assertion_id='c2',source_entity_id='SYN-B',target_entity_id='SYN-C')
    back=deepcopy(child);back.update(assertion_id='c3',source_entity_id='SYN-C',target_entity_id='SYN-A')
    p['assertions'] += [child,back];p['paths']=[['c1','c2'],['c1','c2'],['c1','c2','c3']]
    v=view(api().normalize_packet(p,r,a));assert len(v['confirmed_paths'])==1
    assert v['diagnostics']['cyclic_paths']==1 and v['diagnostics']['duplicate_paths']==1
    assert v['confirmed_paths'][0]['economic_ownership_percent'] is None


def test_partial_not_collected_reviewed_zero_and_filter_zero_are_distinct():
    p,r,a=fixture();assert view()['collection_state']=='PARTIAL_REVIEW'
    assert view(relationship_type='PARENT_SUBSIDIARY')['counts']['filtered_relationships']==1
    p['assertions']=p['assertions'][:1]
    assert view(api().normalize_packet(p,r,a),relationship_type='PARENT_SUBSIDIARY')['collection_state']=='FILTER_EMPTY'
    p['assertions']=[]
    assert view(api().normalize_packet(p,r,a))['collection_state']=='NOT_FOUND_IN_REVIEWED_SCOPE'
    p['collection']['reviewed_entity_ids']=[]
    assert view(api().normalize_packet(p,r,a))['collection_state']=='NOT_COLLECTED'


def test_public_is_explicit_whitelist_and_private_failure_is_not_empty_success():
    p,r,a=fixture();p['private_note']='sensitive';p['evidence'][0]['private_path']='/private/raw/source';
    b=api().normalize_packet(p,r,a);v=view(b,public=True);s=json.dumps(v)
    assert 'private_note' not in s and '/private/raw' not in s and 'excerpt' not in s
    b['publication']='UNKNOWN'
    with pytest.raises(ValueError,match='PUBLIC'):view(b,public=True)


def test_determinism_filter_rank_no_mutation_and_size_limit():
    p,r,a=fixture();b=api().normalize_packet(p,r,a);original=deepcopy(b)
    v=view(b);p['entities'].reverse();p['assertions'].reverse();b2=api().normalize_packet(p,r,a)
    assert view(b2)==v and b==original
    with pytest.raises(ValueError,match='SIZE'):view(b,max_bytes=100)
    assert not any(k in v for k in ('qgv','score','rank','macro_gate','selection'))


def test_public_nested_fields_are_whitelisted_and_unresolved_mentions_are_readable():
    p,r,a=fixture();x=p['assertions'][0]
    x['observations'][0]['private_token']='DO_NOT_EMIT';x['temporal']['private_path']='DO_NOT_EMIT'
    p['collection']['last_failure']={'outcome':'FAILED','reason':'DO_NOT_EMIT','private_path':'DO_NOT_EMIT'}
    v=view(api().normalize_packet(p,r,a),public=True)
    assert 'DO_NOT_EMIT' not in json.dumps(v)
    p,r,a=fixture();p['mentions']=[{'mention_id':'m1','name':'Unresolved synthetic investee','evidence_ids':['e1']}]
    p['assertions'][0].update(target_entity_id=None,target_mention_id='m1')
    p['assertions'][0]['observations']=[]
    v=view(api().normalize_packet(p,r,a))
    assert v['mentions'][0]['name']=='Unresolved synthetic investee'


def test_review_clock_history_and_planned_future_effective_date():
    p,r,a=fixture();p['assertions']=p['assertions'][:1];p['assertions'][0]['status']='PLANNED'
    p['assertions'][0]['temporal'].update(valid_from='2026-03-01',observed_on='2025-12-31')
    assert view(api().normalize_packet(p,r,a))['relationships'][0]['state']=='PLANNED'
    p,r,a=fixture();p['collection']['last_success_at']='2026-03-01T12:00:00Z'
    v=view(api().normalize_packet(p,r,a))
    assert v['collection']['reviewed_entity_ids']==[] and v['collection']['last_success_at'] is None
    assert v['historical_system_pit'] is False


def test_conflicting_edge_cannot_be_used_in_confirmed_path():
    p,r,a=fixture();child=deepcopy(p['assertions'][1]);child.update(assertion_id='c2',source_entity_id='SYN-B',target_entity_id='SYN-C')
    conflict=deepcopy(child);conflict.update(assertion_id='c4',directness='INDIRECT')
    p['assertions'] += [child,conflict];p['paths']=[['c1','c2']]
    assert view(api().normalize_packet(p,r,a))['confirmed_paths']==[]


def test_cli_hash_pins_offline_output_and_no_overwrite(tmp_path):
    import subprocess,sys
    root=Path(__file__).resolve().parents[2]
    cli=root/'tools/company_ownership.py'
    assert cli.exists(),'offline ownership CLI is not implemented'
    p,r,a=fixture();packet=tmp_path/'input.json';packet.write_bytes(encoded(p))
    identity=tmp_path/'identity.json';identity.write_bytes(r)
    artifacts=tmp_path/'artifacts';artifacts.mkdir()
    for sha,body in a.items():(artifacts/sha).write_bytes(body)
    out=tmp_path/'out'
    cmd=[sys.executable,str(cli),'--input',str(packet),'--input-sha256',hashlib.sha256(packet.read_bytes()).hexdigest(),
        '--identity',str(identity),'--artifacts',str(artifacts),'--entity-id','SYN-A',
        '--valid-on','2025-12-31','--knowledge-at','2026-01-05T12:00:00Z','--generated-at','2026-01-05T12:00:00Z',
        '--output-dir',str(out),'--synthetic']
    success=subprocess.run(cmd,capture_output=True,text=True)
    assert success.returncode==0,success.stderr
    result=json.loads((out/'view.json').read_text());manifest=json.loads((out/'manifest.json').read_text())
    assert result['counts']['relationships']==2
    assert manifest['files']['view.json']['sha256']==hashlib.sha256((out/'view.json').read_bytes()).hexdigest()
    original=(out/'view.json').read_bytes()
    repeated=subprocess.run(cmd,capture_output=True,text=True)
    assert repeated.returncode!=0 and (out/'view.json').read_bytes()==original
    cmd[cmd.index('--input-sha256')+1]='0'*64
    assert subprocess.run(cmd,capture_output=True,text=True).returncode!=0

def test_verified_zero_requires_explicit_source_and_preserves_unknown_denominator():
    p,r,a=fixture();p['assertions']=[]
    p['collection']['zero_relationships_evidence_ids']=['missing']
    with pytest.raises(ValueError,match='REFERENCE'):api().normalize_packet(p,r,a)
    body=b'<p>Synthetic entity had no subsidiaries at 2025-12-31.</p>'
    sha=hashlib.sha256(body).hexdigest();a={sha:body}
    p['evidence'][0].update(artifact_hash=sha,excerpt='Synthetic entity had no subsidiaries at 2025-12-31.')
    p['collection'].update(zero_relationships_evidence_ids=['e1'],zero_observed_on='2025-12-31',completeness='COMPLETE')
    v=view(api().normalize_packet(p,r,a))
    assert v['collection_state']=='VERIFIED_ZERO_IN_SCOPE' and v['relationship_denominator'] is None
    p['collection']['zero_observed_on']='2025-01-01'
    assert view(api().normalize_packet(p,r,a))['collection_state']=='NOT_FOUND_IN_REVIEWED_SCOPE'


def test_future_ownership_observation_not_exposed_in_past_query():
    p,r,a=fixture();p['assertions'][0]['observations'][0]['observed_as_of']='2026-01-04'
    v=view(api().normalize_packet(p,r,a))
    assert not any(x['type']=='OWNERSHIP' for x in v['relationships'])


def test_adapter_isolated_from_qgv_classification_macro_and_selection_engines():
    import ast
    tree=ast.parse(Path(api().__file__).read_text())
    imports={n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)}
    assert {n for n in imports if n and n.startswith('investment_system.')} == {
        'investment_system.rig.model','investment_system.providers.sec_classification_inputs'}
    assert not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id in ('open','exec','eval') for n in ast.walk(tree))

def test_main_shared_synthetic_views_and_hashes():
    data=json.loads((Path(__file__).resolve().parents[2]/'docs/research/company_ownership/synthetic.json').read_text())
    for case in data['cases']:
        if 'expected_error' in case:
            with pytest.raises(ValueError,match=case['expected_error']):
                b=api().normalize_packet(case['input'],data['identity_document_utf8'].encode(),{h:s.encode() for h,s in data['artifacts_utf8'].items()})
                api().company_view(b,**case['query'])
        else:
            b=api().normalize_packet(case['input'],data['identity_document_utf8'].encode(),{h:s.encode() for h,s in data['artifacts_utf8'].items()})
            result=api().company_view(b,**case['query'])
            assert result==case['expected_view'],case['case_id']
            assert hashlib.sha256(api().json_bytes(result)).hexdigest()==case['expected_view_sha256']

def test_review_private_update_cannot_inherit_publication_approval():
    p,r,a=fixture();previous=api().normalize_packet(p,r,a)
    p['version']='2';p['publication']='PRIVATE';p['collection']['scope']='PRIVATE_REVIEW_SCOPE'
    incoming=api().normalize_packet(p,r,a)
    merged=api().merge_update(previous,incoming,outcome='SUCCESS',attempted_at='2026-01-06T12:00:00Z')['dataset']
    with pytest.raises(ValueError,match='PUBLIC'):view(merged,public=True)


def test_review_later_observation_does_not_erase_earlier_valid_version():
    p,r,a=fixture();p['assertions']=p['assertions'][:1]
    later=deepcopy(p['assertions'][0]);later.update(version=2,previous_version=1)
    later['temporal'].update(observed_on='2026-01-31',system_known_at='2026-02-01T10:00:00Z',reviewed_at='2026-02-01T10:00:00Z')
    later['observations'][0].update(observed_as_of='2026-01-31',value='40')
    p['assertions'].append(later)
    b=api().normalize_packet(p,r,a)
    result=api().company_view(b,entity_id='SYN-A',valid_on='2025-12-31',knowledge_at='2026-02-01T12:00:00Z',generated_at='2026-02-01T12:00:00Z')
    assert len(result['relationships'])==1
    assert result['relationships'][0]['observations'][0]['value']=='60'
    assert [h['version'] for h in result['relationships'][0]['history']]==[1]


def test_review_nested_source_period_is_not_a_public_metadata_channel():
    p,r,a=fixture();p['evidence'][0]['source_period']={'value':'2025-12-31','private_path':'PRIVATE_SENTINEL'}
    with pytest.raises(ValueError,match='SOURCE_PERIOD'):api().normalize_packet(p,r,a)


def test_review_zero_update_conflicts_with_retained_relations():
    p,r,a=fixture();previous=api().normalize_packet(p,r,a)
    body=b'<p>Synthetic entity had no subsidiaries at 2025-12-31.</p>';sha=hashlib.sha256(body).hexdigest()
    p['assertions']=[];p['evidence'][0].update(evidence_id='zero',artifact_hash=sha,excerpt='Synthetic entity had no subsidiaries at 2025-12-31.')
    p['collection'].update(zero_relationships_evidence_ids=['zero'],zero_observed_on='2025-12-31',completeness='COMPLETE')
    incoming=api().normalize_packet(p,r,{sha:body})
    with pytest.raises(ValueError,match='ZERO_SCOPE_CONFLICT'):
        api().merge_update(previous,incoming,outcome='SUCCESS',attempted_at='2026-01-06T12:00:00Z')


def test_review_equivalent_assertion_paths_do_not_duplicate_relationship_paths():
    p,r,a=fixture();other=deepcopy(p['assertions'][1]);other['assertion_id']='c1b'
    child=deepcopy(other);child.update(assertion_id='c2',source_entity_id='SYN-B',target_entity_id='SYN-C')
    p['assertions'] += [other,child];p['paths']=[['c1','c2'],['c1b','c2']]
    v=view(api().normalize_packet(p,r,a))
    assert len(v['confirmed_paths'])==1 and v['diagnostics']['duplicate_paths']==1
    assert {a['assertion_id'] for a in v['confirmed_paths'][0]['assertions']}=={'c1','c1b','c2'}

@pytest.mark.parametrize('kind',['NEWS','OTHER'])
def test_review_non_primary_text_cannot_confirm_ownership(kind):
    p,r,a=fixture();p['evidence'][0]['source_kind']=kind
    with pytest.raises(ValueError,match='PRIMARY_EVIDENCE_REQUIRED'):api().normalize_packet(p,r,a)

def test_main_fixture_numeric_observations_match_its_fictional_source():
    data=json.loads((Path(__file__).resolve().parents[2]/'docs/research/company_ownership/synthetic.json').read_text())
    for case in data['cases']:
        if 'expected_error' in case:continue
        for claim in case['input']['assertions']:
            sources=[e for e in case['input']['evidence'] if e['evidence_id'] in claim['evidence_ids']]
            text=' '.join(data['artifacts_utf8'][e['artifact_hash']] for e in sources)
            for observation in claim['observations']:
                if observation['value'] is not None:
                    assert observation['value']+' percent' in text,case['case_id']

def test_retained_cli_rejects_another_git_checkout(tmp_path):
    import subprocess,sys
    p,r,a=fixture();p['data_kind']='RETAINED'
    packet=tmp_path/'input.json';packet.write_bytes(encoded(p))
    identity=tmp_path/'identity.json';identity.write_bytes(r)
    artifacts=tmp_path/'artifacts';artifacts.mkdir()
    for sha,body in a.items():(artifacts/sha).write_bytes(body)
    checkout=tmp_path/'other-checkout';checkout.mkdir();(checkout/'.git').write_text('gitdir: synthetic')
    cli=Path(__file__).resolve().parents[2]/'tools/company_ownership.py'
    cmd=[sys.executable,str(cli),'--input',str(packet),'--input-sha256',hashlib.sha256(packet.read_bytes()).hexdigest(),
        '--identity',str(identity),'--artifacts',str(artifacts),'--entity-id','SYN-A','--valid-on','2025-12-31',
        '--knowledge-at','2026-01-05T12:00:00Z','--generated-at','2026-01-05T12:00:00Z','--output-dir',str(checkout/'out')]
    result=subprocess.run(cmd,capture_output=True,text=True)
    assert result.returncode!=0 and 'PRIVATE_OUTPUT_INSIDE_CHECKOUT' in result.stderr
    assert not (checkout/'out').exists()
