"""Only new owner-price profile and affected engine boundary cases; public synthetic inputs."""
from copy import deepcopy
from pathlib import Path
import runpy
import pytest

from investment_system.research.personal_sheet_v import prepare_owner,owner_result,owner_group_page,owner_page
from investment_system.research.qgv_555 import identity,run
from investment_system.research.sector_qgv import digest

_HELPERS=runpy.run_path(str(Path(__file__).resolve().parents[2]/'tools/owner_price_v_fixture.py'))
fixture=_HELPERS['fixture']
prepared=_HELPERS['prepared']


def test_kis_hand_ratio_same_raw_kernel_and_private_scope():
    case=fixture();before=deepcopy(case);p=prepared(case);out=owner_result(p)
    assert case==before
    assert out['schema_version']=='owner-price-v-result/1'
    assert out['namespace']=='OWNER_PRIVATE_KIS_V' and out['storage']=='EPHEMERAL_ONLY'
    assert out['rows'][0]['raw']['central::ebit_yield']==pytest.approx(200/1030)
    assert out['rows'][0]['raw']['central::fcf_yield']==pytest.approx(120/1030)
    assert out['counts']['raw_any']==23 and out['counts']['V_axis']==23
    assert out['counts']['owner_eligible_total']==23
    assert out['counts']['V_roles_complete']==0 and out['counts']['three_axes']==23
    assert out['counts']['gate_judgeable']==23 and out['counts']['gate_pass']==23
    assert out['denominator']==dict(code_rows=23,issuers=23)
    assert 'personal_eligible_total' not in out['counts']
    assert not out['research_coverage_claim'] and not out['official']
    assert not out['availability_context']['historical_pit_proven']
    assert 'target' not in out
    import json
    assert '"price":' not in json.dumps(out)
    for row in out['rows']:
        m=row['price_metadata'];b=row['capitalization_basis']
        assert m['trade_day']=='2026-11-13' and m['price_timestamp'] is None
        assert m['time_status']=='DATE_ONLY' and m['actual_delay_seconds'] is None
        assert m['query_started_at'] is None and m['query_time_status']=='UNRECORDED'
        assert m['provider_delay_notice'] is None
        assert b['capital_basis']=='WEIGHTED_AVERAGE_DILUTED_PROXY'
        assert b['actual_class_outstanding_status']=='NOT_CONNECTED'
        assert not b['actual_all_class_market_cap'] and not b['actual_all_class_ev']


def test_kis_explicit_eod_is_not_google_current_or_silent_snapshot_relabel():
    case=fixture();req,e,r,f,c,pins=case
    for s in (e,r):s['input_cutoff']='2026-11-15T04:02:00Z'
    req['context'].update(input_cutoff=e['input_cutoff'],evaluated_at=e['input_cutoff'])
    assert owner_result(prepared(case))['counts']['raw_any']==23
    req['context'].update(provider='GOOGLEFINANCE',price_definition='GOOGLEFINANCE_CURRENT',evaluation_mode='CURRENT')
    req['namespace']='PERSONAL_SHEET_V'
    with pytest.raises(ValueError,match='CURRENT_EVALUATION_CONTEXT'):
        prepare_owner(req,e,r,f,[],expected_evaluation=identity(e),expected_reference=identity(r))
    case=fixture();case[0]['context']['evaluation_day']='2026-11-12'
    with pytest.raises(ValueError,match='CURRENT_EVALUATION_CONTEXT'):
        prepared(case)


@pytest.mark.parametrize('model',['U1-555','S1-555'])
def test_partial_kis_prices_keep_full_rosters_and_all_deciles(model):
    case=fixture(model=model);cid=case[1]['rows'][0]['company_id'];del case[4][cid];del case[5][cid]
    out=owner_result(prepared(case))
    assert out['denominator']['issuers']==23 and len(out['rows'])==23
    assert out['counts']['price_available']==22
    missing=next(r for r in out['rows'] if r['company_id']==cid)
    assert all(v is None for v in missing['raw'].values())
    group=next(g for g in out['groups'] if g['kind']=='roles' and g['key']=='v_earnings_yield')
    members=sum((owner_group_page(out,group['group_id'],decile=d)['rows'] for d in range(1,11)),[])
    assert len(members)==22 and len({r['company_id'] for r in members})==22
    one=owner_page(out,company_ids=[out['rows'][1]['company_id']])
    assert one['namespace']=='OWNER_PRIVATE_KIS_V' and one['denominator']==out['denominator']
    assert one['rows'][0]['roles']==out['rows'][1]['roles']


def test_kis_cannot_enter_research_scope_or_delivery_after_namespace_removal():
    from investment_system.research.qgv_555_delivery import artifacts
    p=prepared()
    with pytest.raises(ValueError,match='PERSONAL_SCOPE'):
        run(p['configuration'],p['evaluation'],p['reference'])
    with pytest.raises(ValueError,match='PERSONAL_SCOPE'):
        run(p['configuration'],p['evaluation'],p['reference'],calculation_scope='PERSONAL_SHEET_V')
    for board in (p['core_result'],owner_result(p)):
        with pytest.raises(ValueError,match='PERSONAL_RESULT|RESEARCH_RESULT_SCHEMA'):
            artifacts({'U1-555':board},data_kind='PRIVATE')
        removed=deepcopy(board);removed.pop('namespace')
        with pytest.raises(ValueError,match='RESEARCH_RESULT_SCHEMA'):
            artifacts({'U1-555':removed},data_kind='PRIVATE')


def test_kis_raw_quote_injection_and_independent_pin_mismatch_are_rejected():
    case=fixture();req,e,r,f,c,pins=case
    with pytest.raises(ValueError,match='KIS_RETAINED_CONTRACT_REQUIRED'):
        prepare_owner(req,e,r,f,[],expected_evaluation=identity(e),expected_reference=identity(r),contracts=c,expected_contract_hashes=pins)
    wrong=identity(e);wrong['population_hash']='0'*64
    with pytest.raises(ValueError,match='EVALUATION_ANCHOR'):
        prepare_owner(req,e,r,f,expected_evaluation=wrong,expected_reference=identity(r),contracts=c,expected_contract_hashes=pins)
    for key,value in [('namespace','PERSONAL_SHEET_V'),('schema_version','personal-sheet-v-request/1')]:
        case=fixture();case[0][key]=value
        with pytest.raises(ValueError,match='OWNER_'):prepared(case)


def test_ev_input_missing_does_not_require_ev_for_independent_growth_gap():
    case=fixture();cid=case[1]['rows'][0]['company_id'];record=case[3][cid]['record']
    record['v_inputs_v2']['cash_and_equivalents']['value']=None
    for s in case[1:3]:s['rows'][0]['owner_source_context']['record_hash']=digest(record)
    row=owner_result(prepared(case))['rows'][0]
    assert row['raw']['central::ebit_yield'] is None and row['raw']['central::fcf_yield'] is None
    assert row['raw']['central::gap'] is not None
    assert row['raw']['central::own_history'] is None


def test_actual_share_input_cannot_replace_wad_without_new_variant():
    case=fixture();cid=case[1]['rows'][0]['company_id']
    case[3][cid]['actual_class_outstanding']=dict(value=500000,unit='COMMON_SHARES',period_end='2026-11-13')
    row=owner_result(prepared(case))['rows'][0]
    assert row['raw']['central::ebit_yield']==pytest.approx(200/1030)
    assert row['capitalization_basis']['actual_class_outstanding_status']=='NOT_CONNECTED'


def test_raw_ratio_precedes_reference_minimum_and_unknown_gate_blocks_only_total():
    out=owner_result(prepared(fixture(7)))
    assert out['counts']['raw_any']==7 and out['counts']['V_axis']==0
    case=fixture();case[1]['rows'][0]['gate']=None
    row=owner_result(prepared(case))['rows'][0]
    assert row['axes']['V'] is not None and row['gate_status']=='UNKNOWN' and row['total'] is None


def test_kis_split_hold_is_not_reported_as_nonprice_completion():
    case=fixture();cid=case[1]['rows'][0]['company_id'];c=case[4][cid]
    c['splits']=[dict(date='2026-10-15',ratio='2',status='CONFIRMED',evidence='SYNTHETIC_SPLIT')]
    case[3][cid]['basis_evidence']['corporate_actions']['basis']='ALREADY_NORMALIZED'
    case[5][cid]=digest(c)
    out=owner_result(prepared(case));row=out['rows'][0]
    assert out['counts']['price_available']==23
    assert out['counts']['nonprice_any']==22 and out['counts']['raw_any']==22
    assert out['variants']['central::ebit_yield']['nonprice_complete']==22
    assert row['raw']['central::ebit_yield'] is None
    assert 'SHARE_NORMALIZATION_UNCONFIRMED' in row['price_metadata']['reasons']
    assert row['price_metadata']['reasons'].count('SHARE_NORMALIZATION_UNCONFIRMED')==1


def test_missing_exact_day_reason_survives_common_result_projection():
    case=fixture();cid=case[1]['rows'][0]['company_id'];c=case[4][cid]
    for key in ('raw_bars','bars'):c[key][0]['date']='2026-11-12'
    c['price_basis_date']='2026-11-12';case[5][cid]=digest(c)
    row=owner_result(prepared(case))['rows'][0]
    assert row['raw']['central::ebit_yield'] is None
    assert 'EXACT_TRADE_DAY_NOT_RETAINED' in row['price_metadata']['reasons']


def test_owner_request_result_and_capitalization_schema_and_profile_mismatch():
    import json,jsonschema
    root=Path(__file__).resolve().parents[2]
    schema=json.loads((root/'docs/research/sector_qgv/owner-price-v-contract.json').read_bytes())
    case=fixture();out=owner_result(prepared(case))
    for key,value in [('request',case[0]),('result',out),('capitalization_basis',out['rows'][0]['capitalization_basis'])]:
        jsonschema.Draft202012Validator(dict(schema,**{'$ref':'#/$defs/'+key})).validate(value)
    wrong=deepcopy(case[0]);wrong['namespace']='PERSONAL_SHEET_V'
    assert list(jsonschema.Draft202012Validator(dict(schema,**{'$ref':'#/$defs/request'})).iter_errors(wrong))


def test_synthetic_memory_examples_match_frozen_manifest_and_all_deciles():
    import json,hashlib
    root=Path(__file__).resolve().parents[2]
    files=_HELPERS['wire_files']()
    manifest=json.loads((root/'tests/fixtures/owner-price-v/memory-manifest.json').read_bytes())
    assert set(files)=={x['path'] for x in manifest['files']}
    for item in manifest['files']:
        raw=files[item['path']]
        assert len(raw)==item['size']<=1_800_000
        assert hashlib.sha256(raw).hexdigest()==item['sha256']
    deciles=[json.loads(files['decile-'+str(d)+'.json']) for d in range(1,11)]
    assert sum(len(x['rows']) for x in deciles)==23
    assert all(x['denominator']['issuers']==23 for x in deciles)
