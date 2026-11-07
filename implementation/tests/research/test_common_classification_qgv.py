"""Common projection changes classification only, never the saved engine policy."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from investment_system.research.sector_qgv import default_config, preview_qgv
from investment_system.research.common_classification.qgv import project_qgv, gate_comparison
from investment_system.research.common_classification.records import resolve
from test_common_classification_records import store, component


def inputs():
    snapshot = json.loads((Path(__file__).parents[2] / 'docs/research/sector_qgv/synthetic-input.json').read_text())
    s = store(); s['members'] = snapshot['members'][:]
    s.update(universe_id=snapshot['universe_id'], universe_version=snapshot['universe_version'])
    template = s['records'][0]; s['records'] = []
    for row in snapshot['rows']:
        r = deepcopy(template)
        r.update(company_id=row['company_id'], issuer_id=row['issuer_id'], record_id='record:'+row['company_id'])
        r['applicability']['evaluation_date'] = snapshot['valuation_date']
        r['sector'] = component(row['sector_id']); r['accounting'] = component(row['accounting_template'])
        s['records'].append(r)
        # Explicit independently supplied official-Q evidence; not sector Q.
        row['gate']['source_q_score'] = float(len(s['records']))
    v = resolve(s, valuation_date=snapshot['valuation_date'], knowledge_as_of='2026-11-07T00:00:00Z')
    return snapshot, s, v


def test_projection_preserves_prices_factors_gate_members_saved_configuration():
    snapshot, _, view = inputs(); before = deepcopy(snapshot)
    projected = project_qgv(snapshot, view)
    assert snapshot == before
    assert projected['members'] == snapshot['members']
    for old, new in zip(snapshot['rows'], projected['rows']):
        for key in ('observations','gate','security_id','issuer_id'):
            assert new.get(key) == old.get(key)
    config = default_config()
    old = preview_qgv(config,snapshot,'synthetic-old')
    new = preview_qgv(config,projected,'synthetic-new')
    assert old['coverage'] == new['coverage']
    assert old['result_rows'] == new['result_rows']
    assert old['cache_key'] != new['cache_key']
    assert new['config_hash'] == old['config_hash']


def test_unknown_subindustry_does_not_suppress_qgv_but_missing_sector_does():
    snapshot, s, view = inputs()
    assert all(r['industry']['status']=='UNKNOWN' for r in view['rows'])
    first = snapshot['rows'][0]['company_id']
    s['records'][0]['sector'] = component()
    changed = resolve(s, valuation_date=snapshot['valuation_date'],knowledge_as_of=view['knowledge_as_of'])
    p = project_qgv(snapshot, changed)
    row = next(r for r in p['rows'] if r['company_id']==first)
    assert row['mapping'] is None and row['observations'] == snapshot['rows'][0]['observations']
    result = preview_qgv(default_config(),p,'unknown')
    assert result['coverage']['denominator']['count'] == len(s['members'])
    assert next(r for r in result['result_rows'] if r['company_id']==first)['status']=='MAPPING_UNRESOLVED'
    assert all(f['score'] is None for r in result['result_rows'] for f in r['factors'].values())
    assert any(f['score_status']=='PEER_SAMPLE_SMALL' and f['valid_n']==19 for r in result['result_rows'] for f in r['factors'].values())


@pytest.mark.parametrize('field', ['valuation_date','universe_version','members'])
def test_context_mismatch_rejected(field):
    snapshot, _, view=inputs()
    view[field] = [] if field=='members' else 'WRONG'
    with pytest.raises(ValueError, match='PROJECTION_CONTEXT_MISMATCH'): project_qgv(snapshot,view)


def test_tags_have_no_qgv_or_gate_effect_and_gate_is_diagnostic_only():
    snapshot, s, view = inputs(); original = deepcopy(snapshot)
    a = project_qgv(snapshot,view); ga=gate_comparison(snapshot,view)
    for row in s['records']: row['tags']={'lynch':['FAST_GROWER'],'policy':['X'],'cyclical':['DEFENSIVE']}
    changed=resolve(s,valuation_date=snapshot['valuation_date'],knowledge_as_of=view['knowledge_as_of'])
    assert project_qgv(snapshot,changed)==a
    assert gate_comparison(snapshot,changed)==ga
    assert snapshot == original
    assert ga['adoption_state']=='DIAGNOSTIC_ONLY_NOT_APPLIED'
    assert ga['minimum_valid_n']==20 and ga['cutoff']==30


def test_candidate_gate_uses_official_q_and_keeps_small_groups_unknown():
    snapshot, _, view=inputs()
    rows=gate_comparison(snapshot,view)['rows']
    valid=[r for r in rows if r['candidate_percentile'] is not None]
    assert len(valid)==20
    group=[r for r in valid if r['group']==valid[0]['group']]
    lo=min(group,key=lambda r:r['source_q_score']); hi=max(group,key=lambda r:r['source_q_score'])
    assert lo['candidate_percentile']==0 and hi['candidate_percentile']==100
    # Keep the original denominator; invalidate official evidence for every row.
    for row in snapshot['rows']: row['gate']['calc_version']='UNSUPPORTED'
    result=gate_comparison(snapshot,view)
    assert len(result['rows'])==len(snapshot['members'])
    assert all(r['candidate_percentile'] is None for r in result['rows'])
    assert all(r['reason']=='OFFICIAL_Q_INPUT_UNVERIFIED' for r in result['rows'])


def test_missing_classification_keeps_original_issuer_and_does_not_abort_batch():
    snapshot,s,v=inputs();missing=s['records'].pop(0)['company_id']
    view=resolve(s,valuation_date=v['valuation_date'],knowledge_as_of=v['knowledge_as_of'])
    projected=project_qgv(snapshot,view)
    row=next(r for r in projected['rows'] if r['company_id']==missing)
    assert row['issuer_id']==snapshot['rows'][0]['issuer_id'] and row['mapping'] is None
    assert len(projected['members'])==20


def test_gate_diagnostic_keeps_verified_old_percentile_when_candidate_source_q_missing():
    snapshot,_,view=inputs();key=snapshot['rows'][0]['company_id']
    gate=snapshot['rows'][0]['gate'];gate['q_industry_percentile']=80
    del gate['source_q_score']
    row=next(r for r in gate_comparison(snapshot,view)['rows'] if r['company_id']==key)
    assert row['baseline_percentile']==80 and row['baseline_status']=='PASS'
    assert row['candidate_percentile'] is None and row['reason']=='OFFICIAL_Q_INPUT_UNVERIFIED'
