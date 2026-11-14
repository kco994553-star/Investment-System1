from copy import deepcopy
import json
import pytest
from investment_system.research.qgv_555 import configuration, fixture, identity, run
from investment_system.research.qgv_555_preview import preview, selectable_metrics, top500_view
from investment_system.research.sector_qgv import digest


def request():
    c=configuration('U1-555')
    return dict(schema_version='qgv-555-preview-request/1',request_id='synthetic-preview',before=c,after=deepcopy(c))


def test_preview_matches_engine_and_weight_stages():
    e,r=fixture();q=request();q['after']['axis_weights']=dict(Q=50,G=25,V=25)
    e['rows'][0]['gate']['percentile']=10
    out=preview(q,e,r,expected_evaluation=identity(e),expected_reference=identity(r))
    expected=run(q['after'],e,r)
    assert out['after_result']['rows']==expected['rows']
    w=out['rows'][0]['after']['weights']
    assert sum(x['missing_redistributed_before_gate'] for x in w)==pytest.approx(1)
    assert sum(x['after_gate'] for x in w)==pytest.approx(1)
    assert sum(x['after_gate'] for x in w if x['axis']=='V')==0
    assert sum(x['missing_redistributed_before_gate'] for x in w if x['axis']=='V')==pytest.approx(.25)
    assert out['population_effect']=='NOT_EVALUATED'


def test_missing_gate_and_missing_score_are_not_zero():
    e,r=fixture();q=request();e['rows'][0]['gate']=None
    for m in list(e['rows'][0]['metrics']):e['rows'][0]['metrics'].pop(m)
    out=preview(q,e,r,expected_evaluation=identity(e),expected_reference=identity(r))
    assert out['rows'][0]['after']['total'] is None
    assert out['rows'][0]['axes']['Q']['difference'] is None


def test_saved_before_reused_and_independent_anchors_required(monkeypatch):
    e,r=fixture();q=request();saved=run(q['before'],e,r)
    monkeypatch.setattr('investment_system.research.qgv_555_preview.run',lambda *a,**k:pytest.fail('unchanged recomputation'))
    preview(q,e,r,expected_evaluation=identity(e),expected_reference=identity(r),saved_before=saved)
    bad=identity(r);bad['input_hash']='0'*64
    with pytest.raises(ValueError,match='ANCHOR'):preview(q,e,r,expected_evaluation=identity(e),expected_reference=bad,saved_before=saved)
    damaged=deepcopy(saved);damaged['configuration']['axis_weights']['Q']=99
    with pytest.raises(ValueError):preview(q,e,r,expected_evaluation=identity(e),expected_reference=identity(r),saved_before=damaged)


def test_optional_sector_variant_selectable_without_default_role():
    assert 'sector::roa_ttm' in selectable_metrics('q_profitability','GENERAL')
    assert 'sector::ep_ttm_diluted' not in selectable_metrics('q_profitability','GENERAL')


def test_main_compact_saved_requires_replay_before_preview(monkeypatch):
    from investment_system.research.qgv_555 import replay
    e,r=fixture();q=request();full=run(q['before'],e,r)
    keys=('configuration','evaluation','reference','bindings','calculated_at','result_hash')
    compact=dict(schema_version='qgv-555-saved/1',**{k:deepcopy(full[k]) for k in keys})
    with pytest.raises(ValueError,match='RESULT_HASH'):
        preview(q,e,r,expected_evaluation=identity(e),expected_reference=identity(r),saved_before=compact)
    restored=replay(compact,e,r)
    assert restored['result_hash']==compact['result_hash']
    monkeypatch.setattr('investment_system.research.qgv_555_preview.run',lambda *a,**k:pytest.fail('same input rerun'))
    result=preview(q,e,r,expected_evaluation=identity(e),expected_reference=identity(r),saved_before=restored)
    assert result['before_result_hash']==full['result_hash']


def test_page_keeps_full_population_and_bounds():
    from investment_system.research.qgv_555_preview import preview_page
    e,r=fixture();out=preview(request(),e,r,expected_evaluation=identity(e),expected_reference=identity(r))
    page=preview_page(out,limit=1)
    assert page['row_count']==21 and len(page['rows'])==1 and page['next_offset']==1
    assert page['evaluation']==out['evaluation'] and page['after_coverage']==out['after_coverage']
    with pytest.raises(ValueError):preview_page(out,limit=True)


def test_top500_allowlist_does_not_leak_source_or_previous_prices():
    r=dict(schema_version='top500-selection/1',population_id='SYN',population_version='1',evaluation_day='2026-11-04',input_cutoff='2026-11-04T22:00:00Z',apply_at='2026-11-05T14:30:00Z',status='UNCONFIRMED_CANDIDATE',denominator=None,target_count=475,selected_count=1,boundary_uncertain=True,reasons=['COVERAGE_UNPROVEN'],ranked=[dict(issuer_id='synthetic-issuer')],members=[dict(issuer_id='synthetic-issuer',representative_security_id='synthetic-security',economic_classes=['class1'],market_cap_usd='private-value',selection_evidence=['private-evidence'])],retained_confirmed=dict(price='secret-value'))
    r['result_hash']=digest(r);view=top500_view(r)
    assert view['members'][0]['selection_rank']==1 and view['retained_confirmed_available']
    assert all(x not in json.dumps(view) for x in ['private-value','private-evidence','secret-value','market_cap_usd'])
    r['status']='VALIDATED_RESEARCH_CANDIDATE'
    with pytest.raises(ValueError):top500_view(r)
