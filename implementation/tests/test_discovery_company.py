"""Synthetic behavior regressions; no actual company observations."""
from copy import deepcopy
from hashlib import sha256
import importlib
import json
from pathlib import Path
import subprocess
import sys

import pytest


def engine():
    spec = importlib.util.find_spec('investment_system.research.discovery_company')
    assert spec is not None, 'discovery producer is not implemented'
    return importlib.import_module(spec.name)


def package():
    body = b'{"business":"Synthetic replacement filters","risk":"One customer"}'
    receipt = dict(artifact_id='synthetic:filing', source_url='https://example.invalid/filing',
                   sha256=sha256(body).hexdigest(), bytes=len(body), fetched_at='2026-11-01T12:00:00Z')
    fact = engine().extract_fact(body, receipt, {'json_pointer': '/business'}, 'SYNTH:001',
                                dict(published_on='2026-10-31', period={'start':'2026-01-01','end':'2026-09-30'},
                                     unit='text', region=None, region_basis=None))
    counter = engine().extract_fact(body, receipt, {'json_pointer': '/risk'}, 'SYNTH:001',
                                   dict(published_on='2026-10-31', period={'start':'2026-01-01','end':'2026-09-30'},
                                        unit='text', region=None, region_basis=None))
    statements = {
        'IDENTITY': '합성 기업의 기존 식별자와 원문을 대조했다.',
        'BUSINESS': '합성 교체 필터를 판매한다.',
        'DISCOVERY': '교체 필터의 반복 수요를 조사할 이유가 있다.',
        'ATTRACTIVENESS': '합성 원문의 반복 구매 근거를 검토했다.',
        'COUNTER_REVIEW': '단일 고객 위험을 검토했으며 핵심 주장을 반증하지 않는다.',
        'CURRENTNESS': '이 검토일의 주장 범위에 자료가 유효함을 검토했다.',
    }
    judgments = [dict(judgment_id=k.lower(), category=k, topic=None, claim=v,
                      evidence_ids=[fact['evidence_id']], counterevidence_ids=[counter['evidence_id']],
                      status='CONFIRMED', reason='합성 수작업 대조', reviewed_by='synthetic-reviewer',
                      rule_version='discovery-rules/1', core=True, material=False)
                 for k,v in statements.items()]
    return dict(company_id='SYNTH:001', registry={'SYNTH:001':{'issuer_id':'SYNTH:issuer-1','name':'아주 긴 합성 기업 이름 주식회사','country_code':'ZZ'}},
                as_of='2026-11-06T12:00:00Z', population='synthetic-1', review_scope='single-company source review',
                evidence=[fact,counter], judgments=judgments, unknowns=['시장 인지도 미측정', '지역 수익성 미확인'],
                awareness={'consumer_contact':None,'market_attention':None}, requested_state=None,
                transition_reason=None, reviewer=None, events=[])


def selected():
    p=package(); c=engine().evaluate(p)
    p.update(requested_state='IN_REVIEW', reviewer='reviewer', transition_reason='review starts')
    r=engine().evaluate(p,c)
    p.update(requested_state='SELECTED', transition_reason='source comparison complete')
    return p,engine().evaluate(p,r)


def test_automatic_candidate_and_unmeasured_awareness_is_not_rejection():
    p=package(); r=engine().evaluate(p)
    assert r['selection_ready'] is True
    assert r['state']=='CANDIDATE' and r['first_selected_at'] is None
    assert r['awareness']['market_attention'] is None
    assert r['qgv_ref']=={'company_id':'SYNTH:001'}
    assert not r['display']['list_eligible'] and not r['publication_approved']


def test_selection_requires_sources_and_preserves_counterevidence_in_summary():
    p,r=selected()
    assert r['display']['list_eligible'] and r['display']['mark']=='SELECTED'
    assert r['display']['risks'][0]['evidence_id']==p['evidence'][1]['evidence_id']
    assert r['display']['risks'][0]['value']=='One customer'
    p['judgments'][3]['evidence_ids']=[]
    r=engine().evaluate(p,r)
    assert r['state']=='REVIEW_REQUIRED' and not r['selection_ready']
    assert 'ATTRACTIVENESS' in r['blocked_gates']


@pytest.mark.parametrize('kind,state,visible,mark',[
    ('EVIDENCE_AGED','REVIEW_REQUIRED',True,'REVIEW_REQUIRED'),
    ('CORE_EVIDENCE_ERROR','SUSPENDED',False,None),
    ('IDENTITY_ERROR','SUSPENDED',False,None),
    ('MATERIAL_REFUTATION','SUSPENDED',False,None),
])
def test_events_update_list_and_mark_together_without_rewriting_history(kind,state,visible,mark):
    p,r=selected(); old=deepcopy(r); p['requested_state']=None
    p['events']=[dict(event_id='event-1',kind=kind,at='2026-11-06T12:00:00Z',reason='new evidence',
                      document_id='synthetic:filing',sha256='b'*64,evidence_ids=[p['evidence'][0]['evidence_id']])]
    out=engine().evaluate(p,r)
    assert out['state']==state and out['display']['list_eligible'] is visible
    assert out['display']['mark']==mark and out['first_selected_at']==r['first_selected_at']
    assert r==old and out['previous_record_hash']==r['record_hash']
    assert out['history'][:len(r['history'])]==r['history']
    assert engine().evaluate(p,out)==out


def test_unrelated_updates_do_not_reopen_selection_and_conflicting_event_is_rejected():
    p,r=selected();p['requested_state']=None
    p['events']=[dict(event_id='unrelated',kind='DOCUMENT_CHANGED',at=p['as_of'],reason='other document',
                      document_id='other',sha256='a'*64,evidence_ids=[])]
    out=engine().evaluate(p,r); assert out['state']=='SELECTED'
    p['events'][0]['reason']='altered'
    with pytest.raises(ValueError,match='event'):engine().evaluate(p,out)


def test_edited_core_judgment_needs_new_review_not_old_selected_status():
    p,r=selected();p['requested_state']=None
    p['judgments'][3]['claim']='Changed economic claim'
    out=engine().evaluate(p,r)
    assert out['state']=='REVIEW_REQUIRED'
    p['requested_state']='SELECTED';p['reviewer']=None
    with pytest.raises(ValueError,match='reviewer'):engine().evaluate(p,out)


def test_missing_unknown_and_refuted_are_distinct():
    p=package();p['judgments'][3]['status']='UNCONFIRMED'
    r=engine().evaluate(p);assert r['state']=='CANDIDATE' and not r['selection_ready']
    assert '시장 인지도 미측정' in r['unknowns']
    p['judgments'][3].update(status='REFUTED',material=True)
    assert engine().evaluate(p)['material_refutations']==['attractiveness']


def test_source_hash_identity_future_and_ai_fact_injection_fail_closed():
    p=package();p['evidence'][0]['company_id']='SYNTH:other'
    with pytest.raises(ValueError,match='company'):engine().evaluate(p)
    body=b'{"x":null}'; receipt=dict(artifact_id='doc',source_url='https://example.invalid',sha256='0'*64,bytes=len(body),fetched_at='2026-01-01T00:00:00Z')
    meta=dict(published_on='2025-12-31',period={'start':None,'end':None},unit=None,region=None,region_basis=None)
    with pytest.raises(ValueError,match='hash'):engine().extract_fact(body,receipt,{'json_pointer':'/x'},'SYNTH:001',meta)
    receipt['sha256']=sha256(body).hexdigest()
    f=engine().extract_fact(body,receipt,{'json_pointer':'/x'},'SYNTH:001',meta)
    assert f['value'] is None
    with pytest.raises(ValueError):engine().extract_fact(body,receipt,{'generated_text':'AI claim'},'SYNTH:001',meta)
    p=package();p['evidence'][0]['published_on']='2026-11-07'
    with pytest.raises(ValueError,match='future'):engine().evaluate(p)


def test_xml_source_element_and_dedup_ids_include_revision_and_locator():
    body=b'<root><f id="one">reported business</f><f id="two">risk</f></root>'
    receipt=dict(artifact_id='doc',source_url='https://example.invalid',sha256=sha256(body).hexdigest(),bytes=len(body),fetched_at='2026-01-01T00:00:00Z')
    meta=dict(published_on='2025-12-31',period={'start':None,'end':None},unit='text',region=None,region_basis=None)
    a=engine().extract_fact(body,receipt,{'xml_id':'one'},'SYNTH:001',meta)
    b=engine().extract_fact(body,receipt,{'xml_id':'two'},'SYNTH:001',meta)
    assert a['value']=='reported business' and a['evidence_id']!=b['evidence_id']


def test_reproducible_order_and_imported_snapshot_tampering_rejected():
    p=package();a=engine().evaluate(p);p['evidence'].reverse();p['judgments'].reverse()
    assert engine().evaluate(p)==a
    a['state']='SELECTED'
    with pytest.raises(ValueError,match='hash'):engine().evaluate(p,a)


def test_terminal_transition_and_first_selection_null_until_selected():
    p,r=selected();p.update(requested_state='REVIEW_REQUIRED',transition_reason='age')
    r=engine().evaluate(p,r);p['requested_state']='REMOVED';out=engine().evaluate(p,r)
    assert not out['display']['list_eligible'] and out['display']['mark'] is None
    assert out['first_selected_at']==r['first_selected_at']
    assert out['history_ref'].startswith('discovery_history_')


def test_source_unknown_publication_blocks_confirmation_and_xml_duplicate_id_rejected():
    p=package();p['evidence'][0]['published_on']=None
    assert not engine().evaluate(p)['selection_ready']
    body=b'<r><x id="a">one</x><x id="a">two</x></r>'
    receipt=dict(artifact_id='doc',source_url='https://example.invalid',sha256=sha256(body).hexdigest(),bytes=len(body),fetched_at='2026-01-01T00:00:00Z')
    with pytest.raises(ValueError,match='unique'):
        engine().extract_fact(body,receipt,{'xml_id':'a'},'SYNTH:001',{})


def test_fixture_contract_and_literal_expected_display():
    import jsonschema
    root=Path(__file__).parents[1]/'docs/research/discovery_company'
    assert (root/'schema.json').exists(), 'output schema missing'
    schema=json.loads((root/'schema.json').read_text())
    vectors=json.loads((root/'synthetic.json').read_text())
    assert len(vectors['cases'])==6
    for case in vectors['cases']:
        jsonschema.validate(case['record'],schema)
        assert case['record']['state']==case['expected']['state']
        for k in ('list_eligible','mark'):
            assert case['record']['display'][k]==case['expected'][k]


def test_cli_replay_is_content_addressed_and_does_not_print_company_values(tmp_path):
    p=package();job=tmp_path/'job.json';job.write_text(json.dumps({'packages':[p]}))
    tool=Path(__file__).parents[1]/'tools/discovery_company.py'
    assert tool.exists(), 'offline CLI missing'
    args=[sys.executable,str(tool),'--job',str(job),'--output-dir',str(tmp_path/'results')]
    a=subprocess.run(args,capture_output=True,text=True);assert a.returncode==0,a.stderr
    paths=list((tmp_path/'results').glob('record-*.json'));assert len(paths)==1
    before=paths[0].read_bytes()
    b=subprocess.run(args,capture_output=True,text=True);assert b.returncode==0,b.stderr
    assert paths[0].read_bytes()==before and 'Synthetic replacement' not in a.stdout+b.stdout


def test_rehashed_snapshot_cannot_skip_selection_history():
    p=package();r=engine().evaluate(p)
    r['state']='SELECTED';r['display'].update(list_eligible=True,mark='SELECTED')
    r['record_hash']=engine().digest({k:v for k,v in r.items() if k!='record_hash'})
    with pytest.raises(ValueError,match='history'):engine().evaluate(p,r)


def test_material_refutation_from_review_suspends_and_keeps_opposition():
    p,r=selected();p['requested_state']=None
    p['judgments'][3].update(status='REFUTED',material=True)
    out=engine().evaluate(p,r)
    assert out['state']=='SUSPENDED' and not out['display']['list_eligible']


def test_removing_counter_links_does_not_hide_previous_opposition():
    p,r=selected();p['requested_state']=None
    for j in p['judgments']:j['counterevidence_ids']=[]
    out=engine().evaluate(p,r)
    assert out['state']=='REVIEW_REQUIRED'
    assert [f['value'] for f in out['display']['risks']]==['One customer']
    assert out['counterevidence_history'][0]['disposition']=='RETAINED_FOR_REVIEW'


def test_duplicate_event_remains_idempotent_after_processing_clock_advances():
    p,r=selected();p['requested_state']=None
    p['events']=[dict(event_id='repeat',kind='NEW_FILING',at=p['as_of'],reason='review new filing',
                      document_id='doc',sha256='a'*64,evidence_ids=[])]
    r=engine().evaluate(p,r)
    for day in (7,8):
        p['as_of']=f'2026-11-{day:02d}T12:00:00Z';r=engine().evaluate(p,r)
    assert len(r['events'])==1 and r['state']=='SELECTED'


def test_corrected_provenance_gets_new_evidence_version_retaining_old():
    p=package();f=p['evidence'][0]
    body=b'{"business":"Synthetic replacement filters","risk":"One customer"}'
    receipt=dict(artifact_id=f['document_id'],source_url=f['source_url'],sha256=f['sha256'],bytes=len(body),fetched_at=f['acquired_at'])
    meta=dict(published_on=f['published_on'],period=f['period'],unit=f['unit'],region=f['region'],region_basis=f['region_basis'])
    old=engine().extract_fact(body,receipt,f['locator'],p['company_id'],{**meta,'published_on':None})
    assert old['evidence_id']!=f['evidence_id']
    p['evidence'].append(old);r=engine().evaluate(p)
    p['evidence'].remove(old);out=engine().evaluate(p,r)
    assert old in out['evidence'] and f in out['evidence']


def test_cli_real_job_requires_explicit_private_location_even_outside_git(tmp_path):
    import importlib.util
    tool=Path(__file__).parents[1]/'tools/discovery_company.py'
    spec=importlib.util.spec_from_file_location('discovery_cli',tool)
    cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
    p=package();p['company_id']='REAL:001'
    with pytest.raises(ValueError,match='private'):
        cli.run({'packages':[p]},tmp_path/'public_html')
