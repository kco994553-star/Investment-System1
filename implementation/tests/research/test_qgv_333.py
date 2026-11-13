"""New nine-factor policy on the existing kernels; synthetic only."""
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import pytest
from investment_system.research import dual_qgv as dual
from investment_system.research import sector_qgv as sector

FIX = Path(__file__).resolve().parents[2]/'docs/research/sector_qgv/synthetic-input.json'

def candidates():
    from investment_system.research.qgv_333 import candidate_configs
    return candidate_configs()

def snapshots(n=20, template='GENERAL'):
    s=json.loads(FIX.read_text());s['rows']=s['rows'][:n];s['members']=s['members'][:n]
    for i,r in enumerate(s['rows']):
        r['sector_id']='INFORMATION_TECHNOLOGY';r['accounting_template']=template
        for v in sector.CATALOG:
            f=sector.CATALOG[v];o=deepcopy(r['observations']['operating_margin_ttm'])
            o.update(variant_id=v,formula_version=f['formula_version'],unit=f['unit'],value=i+1,
                     security_id=r['security_id'],corporate_action_basis='SYN:unchanged-split-class-basis')
            o['fiscal_period']['kind']=f['period'];o['price_asof']=s['valuation_date'] if f['axis']=='V' else None
            r['observations'][v]=o
    ev=deepcopy(s);ev['rows']=ev['rows'][:3];ev['members']=ev['members'][:3]
    ev['universe_id']='SYN333-EVAL';s['universe_id']='SYN333-REFERENCE'
    return ev,s

def run(key='U2-333',n=20,template='GENERAL'):
    e,r=snapshots(n,template)
    return dual.run_board(candidates()[key],e,r,request_id='synthetic333')

def test_fixed_nine_and_single_G_substitution():
    cs=candidates();assert set(cs)=={'U1-333','U2-333','S1-333'}
    assert cs['U2-333']['model_id']=='unified-333-eps/0.1.0'
    assert cs['U1-333']['model_id']=='unified-333-persistence/0.1.0'
    for c in cs.values():dual.validate_model(c)
    p=cs['U2-333']['uniform_preset'];q=cs['U1-333']['uniform_preset']
    assert p['axis_weights']==q['axis_weights']==dict.fromkeys('QGV',1)
    assert p['axes']['Q']==q['axes']['Q'] and p['axes']['V']==q['axes']['V']
    for c in cs.values():
        for p in ([c['uniform_preset']] if c['kind']=='COMMON' else c['scoped_presets'].values()):
            assert all(sum(len(r['factors']) for r in rs.values())==3 for rs in p['axes'].values())
    assert set(dual.candidate_configs())=={'U1','U2','S1'}

def test_exact_thirds_at_role_factor_and_gate_levels():
    p=candidates()['U2-333']['uniform_preset'];scores={v:{'score':float(9*(i+1))} for i,v in enumerate(sector.effective_weights(p))}
    gate={'calc_version':'qgv2-calc/2026-10-23.1','as_of':'2026-11-04','q_industry_percentile':80,'provenance':['SYN']}
    a=sector.aggregate(p,scores,gate,'2026-11-04')
    assert list(a['nominal_effective_weights'].values())==[1/9]*9
    assert a['axes']=={'Q':18,'G':45,'V':72}
    assert a['total']==45
    gate['q_industry_percentile']=0;b=sector.aggregate(p,scores,gate,'2026-11-04')
    assert b['post_gate_axis_weights']=={'Q':.5,'G':.5,'V':0}
    assert sorted(b['post_gate_effective_weights'].values())==[0]*3+[1/6]*6
    assert b['total']==31.5

def test_strict_missing_additional_zero_and_unknown_gate():
    e,r=snapshots();a=dual.run_board(candidates()['U2-333'],e,r,request_id='a')
    for s in (e,r):
        s['rows'][0]['observations'].pop('net_debt_assets')
    only_additional=dual.run_board(candidates()['U2-333'],e,r,request_id='additional')
    assert a['rows'][0]['total']==only_additional['rows'][0]['total']
    for s in (e,r):
        s['rows'][1]['observations'].pop('cfo_mcap')
        s['rows'][2]['gate']=None
    b=dual.run_board(candidates()['U2-333'],e,r,request_id='b')
    assert b['rows'][1]['axes']['V'] is None and b['rows'][1]['total'] is None
    assert b['rows'][2]['total'] is None
    assert b['rows'][2]['gate_status']=='UNKNOWN'
    assert b['coverage']['stages']['gate_known']['code_rows']==2

def test_shared_applicability_and_reit_pending_does_not_reduce_to_two():
    b=run(template='BANK');assert b['rows'][0]['factors']['accruals_assets_ttm']['raw_status']=='NOT_APPLICABLE'
    assert b['rows'][0]['axes']['Q'] is None
    reit=run('S1-333',template='EQUITY_REIT');row=reit['rows'][0]
    assert row['axes']['Q'] is not None and row['axes']['V'] is not None
    assert row['axes']['G'] is None and row['total'] is None
    assert 'ffo_per_share_growth' in row['selected_variants'] and len(row['selected_variants'])==9
    assert row['factors']['ffo_per_share_growth']['score_status']=='CALCULATOR_PENDING'
    assert reit['coverage']['denominator']['issuers']==3

@pytest.mark.parametrize('n',[19,20])
def test_minimum20_only_at_factor_scoring(n):
    b=run(n=n);f=b['rows'][0]['factors']['eps_diluted_cagr_3y']
    assert f['raw_value']==1
    assert (f['score'] is not None)==(n==20)

def test_per_share_G_observation_requires_security_and_action_basis():
    e,r=snapshots()
    for s in (e,r):s['rows'][0]['observations']['eps_diluted_cagr_3y']['corporate_action_basis']=None
    b=dual.run_board(candidates()['U2-333'],e,r,request_id='bad-share')
    assert b['rows'][0]['factors']['eps_diluted_cagr_3y']['raw_status']=='SCOPE_MISMATCH'
    assert b['rows'][0]['axes']['G'] is None

def test_fixed_configuration_rejects_hidden_factor_or_weight_change():
    c=candidates()['U2-333'];c['uniform_preset']['axes']['Q']['profitability']['weight']=2
    with pytest.raises(ValueError,match='333'):dual.validate_model(c)

def test_save_replay_versions_filters_and_original_missing_input():
    e,r=snapshots();c=candidates()['U2-333'];a=dual.run_board(c,e,r,request_id='a')
    saved=dual.save_board(c,a);b=dual.replay_board(saved,e,r,'b')
    assert a['rows']==b['rows'] and a['result_hash']==b['result_hash']
    assert a['adapter_version']!=dual.VERSION
    filtered=dual.project_board(a,[a['rows'][1]['company_id']])
    assert filtered['rows'][0]==a['rows'][1] and filtered['reference_population']==a['reference_population']
    r['rows'][-1]['observations']['roa_ttm']['value']=99
    with pytest.raises(ValueError,match='REPLAY'):dual.replay_board(saved,e,r,'bad')

def test_legacy_config_results_unchanged_and_333_count_not_cross_class_union():
    e,r=snapshots();old=dual.run_board(dual.candidate_configs()['U1'],e,r,request_id='old')
    dual.run_board(candidates()['U2-333'],e,r,request_id='new')
    assert dual.run_board(dual.candidate_configs()['U1'],e,r,request_id='old')==old
    c=run()['coverage'];assert c['target95']['issuers']==3 and c['stages']['nine_core_scores']['issuers']==3
    assert c['whole_market_coverage'] is None

def test_three_candidates_distribution_reuses_all_bins_without_relabeling():
    from investment_system.research.dual_qgv_distribution import distribution_artifacts,STORED
    e,r=snapshots();e=deepcopy(r)
    boards={k:dual.run_board(c,e,r,request_id=k) for k,c in candidates().items()}
    out=distribution_artifacts(boards,scope='operating504',data_kind='SYNTHETIC',display_policy=STORED)
    idx=out['distribution-index.json']
    assert set(idx['boards'])==set(candidates()) and len(idx['bands'])==10
    assert all(g['ranking_scope'].startswith('SECTOR|') for g in idx['groups'] if g['board']=='S1-333')
    assert all(sum(b['count'] for b in g['bins'])==g['evaluation_valid_n'] for g in idx['groups'])
    from investment_system.research.dual_qgv_distribution_index import bin_index_artifacts
    import hashlib
    files={k:dual.json_bytes(v) for k,v in out.items()}
    bins=bin_index_artifacts(files,expected_manifest_sha256=hashlib.sha256(files['distribution-manifest.json']).hexdigest())
    assert len(bins['bin-index.json']['groups'])==len(idx['groups'])

def test_new_distribution_key_and_model_cannot_be_mixed_or_relabelled():
    from investment_system.research.dual_qgv_distribution import distribution_artifacts,STORED
    b=run();kw=dict(scope='operating504',data_kind='SYNTHETIC',display_policy=STORED)
    with pytest.raises(ValueError,match='BOARD_KEYS'):distribution_artifacts({'U2-333':b,'U1':b},**kw)
    with pytest.raises(ValueError,match='BOARD_MODEL_ID'):distribution_artifacts({'U1-333':b},**kw)


def test_eps_cagr_components_loss_zero_basis_and_persistence_boundaries():
    def component(value,*,period,end):
        return dict(value=value,period_kind=period,period_end=end,unit='USD/share',currency='USD',
            issuer_id='SYN-issuer',security_id='SYN-security',share_basis='diluted-common',
            corporate_action_basis='SYN-split-consistent',scope='CONSOLIDATED',
            available_at='2026-10-01T00:00:00Z',retrieved_at='2026-10-02T00:00:00Z',provenance=['SYN'])
    ctx=dict(as_of='2026-11-02T23:59:59Z',valuation_date='2026-11-02',accounting_template='GENERAL',issuer_id='SYN-issuer',security_id='SYN-security');fields=['eps_diluted_fy','eps_diluted_fy1','eps_diluted_fy2','eps_diluted_fy3']
    values=[8,4,2,1]
    parts={k:component(v,period='FY' if i==0 else f'FY_MINUS_{i}',end=f'{2025-i}-12-31') for i,(k,v) in enumerate(zip(fields,values))}
    assert sector.calculate_factor('eps_diluted_cagr_3y',parts,ctx)['value']==1
    for oldest in (0,-1):
        bad=deepcopy(parts);bad[fields[-1]]['value']=oldest
        assert sector.calculate_factor('eps_diluted_cagr_3y',bad,ctx)['status']=='DOMAIN_INVALID'
    for field,value,reason in [('share_basis','ADR-2:1','SCOPE_MISMATCH'),('period_end','2023-09-30','PERIOD_MISMATCH'),('available_at','2026-11-03T00:00:00Z','NOT_YET_AVAILABLE')]:
        bad=deepcopy(parts);bad[fields[2]][field]=value
        assert sector.calculate_factor('eps_diluted_cagr_3y',bad,ctx)['status']==reason
    rev={k.replace('eps_diluted','revenue'):dict(v,unit='USD',value=n) for (k,v),n in zip(parts.items(),[110,110,90,100])}
    assert sector.calculate_factor('revenue_growth_consistency_3y',rev,ctx)['value']==1/3


def test_same_issuer_axes_are_not_assembled_across_code_rows():
    from investment_system.research.qgv_333 import extend_coverage
    b=run();r=deepcopy(b['rows'][0]);r['company_id']='SYN-SECOND-CLASS'
    b['rows']=[b['rows'][0],r]
    b['rows'][0]['axes']['Q']=None;r['axes']['G']=None
    for row in b['rows']:row['total']=None
    b['coverage']=dual._coverage(b['rows'],{})
    extend_coverage(b)
    assert b['coverage']['denominator']['issuers']==1
    assert b['coverage']['stages']['joint']['issuers']==0
    assert b['coverage']['stages']['total']['issuers']==0


def test_new_candidate_lynch_tags_and_input_order_do_not_change_results():
    e,r=snapshots();c=candidates()['U2-333'];a=dual.run_board(c,e,r,request_id='same')
    for s in (e,r):
        s['rows'].reverse()
        for row in s['rows']:row['lynch_tags']=['SYNTHETIC:changed']
    assert dual.run_board(c,e,r,request_id='same')==a


def test_absent_observation_is_not_confused_with_accounting_or_definition_block():
    for template,key,variant,reason in [('BANK','U2-333','accruals_assets_ttm','NOT_APPLICABLE'),('EQUITY_REIT','S1-333','ffo_per_share_growth','CALCULATOR_PENDING')]:
        e,r=snapshots(template=template)
        for s in (e,r):
            for row in s['rows']:row['observations'].pop(variant,None)
        b=dual.run_board(candidates()[key],e,r,request_id='missing-scope')
        assert b['rows'][0]['factors'][variant]['raw_status']==reason
        if template=='BANK':assert b['coverage']['applicability_only_upper_bound']['optimistic_issuers']==0
