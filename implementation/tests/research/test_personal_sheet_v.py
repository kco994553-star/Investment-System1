"""Only public synthetic quotes; current personal scope never restores historical inputs."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import json
import pytest
from investment_system.research.qgv_555 import fixture as base_fixture, configuration, identity, run
from investment_system.research.sector_qgv import digest

MODULE='investment_system.research.personal_sheet_v'

def fixture(n=23):
    e,r=base_fixture(n);day='2026-11-13';cutoff=day+'T21:02:00Z'
    financial={};prices=[]
    for s in (e,r):
        s.update(evaluation_day=day,input_cutoff=cutoff,population_version='current-synthetic/1')
        for row in s['rows']:
            row['gate'].update(evaluation_day=day)
            row.update(classification_status='VERIFIED',classification_record_id='synthetic-current-class',
                classification_mapping=dict(common_record_id='synthetic-current-class',evidence_refs=['SYNTHETIC_CURRENT_CLASS'],
                    common_dictionary_version='common-industry-dictionary/2',common_mapping_version='common-classification-map/2',
                    common_classification_hash='a'*64,valid_from=day,valid_to='2026-11-14',knowledge_as_of=day+'T12:00:00Z'))
    for i,row in enumerate(e['rows']):
        def flow(v):return dict(fy_value=v,fy_end='2025-12-31',ttm_value=v,ttm_end='2026-09-30')
        record=dict(cik=row['issuer_id'],profile='GENERAL',currency='USD',fiscal_year_end='2025-12-31',
            acquired_at=day+'T12:00:00Z',calc_version='qgv2-calc/2026-10-23.1',
            v_inputs_v2=dict(currency='USD',ebit=flow(200+i*10),fcf=flow(120+i*3),revenue=flow(1000),
                total_debt=dict(value=50,period_end='2026-09-30'),cash_and_equivalents=dict(value=20,period_end='2026-09-30'),
                diluted_shares=dict(value=100,period_end='2026-09-30'),revenue_cagr_3y=.1,
                ebit_per_share_history=[dict(fiscal_year_end=f'{y}-12-31',value=x) for y,x in [(2023,1),(2024,2),(2025,3)]]))
        common=dict(status='VERIFIED',available_at=day+'T12:00:00Z',source_refs=['SYNTHETIC_BASIS_ONLY'])
        basis=dict(mapping=dict(common,record_id='synthetic-mapping-'+str(i),company_id=row['company_id'],
                    issuer_id=row['issuer_id'],security_id=row['security_id'],share_class_id='SYN_COMMON',
                    provider_symbol='SYN'+str(i),security_type='COMMON_STOCK',valid_from='2026-09-30',valid_to=None),
            share_basis=dict(common,definition='WEIGHTED_AVERAGE_DILUTED',period_end='2026-09-30',
                share_class_id='SYN_COMMON',unit='COMMON_SHARES'),
            corporate_actions=dict(common,from_day='2026-09-30',through_day=day,basis='ALREADY_NORMALIZED'))
        financial[row['company_id']]=dict(record=record,source_refs=['SYNTHETIC_FINANCIAL_ONLY'],basis_evidence=basis)
        context=dict(record_hash=digest(record),**{k:record[k] for k in ('acquired_at','fiscal_year_end','currency','calc_version')})
        for s in (e,r):s['rows'][i]['owner_source_context']=deepcopy(context)
        prices.append(dict(company_id=row['company_id'],issuer_id=row['issuer_id'],provider_symbol='SYN'+str(i),
            status='AVAILABLE',provider='GOOGLEFINANCE',price_definition='GOOGLEFINANCE_CURRENT',
            adjustment_status='AS_TRADED',currency='USD',price=10+i,trade_day=day,
            price_timestamp=day+'T20:59:00Z',time_status='CONFIRMED',query_started_at=day+'T21:00:00Z',
            received_at=day+'T21:01:00Z',source_refs=['SYNTHETIC_QUOTE_ONLY']))
    request=dict(schema_version='personal-sheet-v-request/1',
        context=dict(context_id='synthetic-current-session',evaluation_day=day,evaluated_at=cutoff,input_cutoff=cutoff,
            provider='GOOGLEFINANCE',price_definition='GOOGLEFINANCE_CURRENT'),configuration=configuration('U1-555',version='0.4.0'))
    return request,e,r,financial,prices


def prepare(case=None):
    from investment_system.research.personal_sheet_v import prepare_personal
    req,e,r,f,p=fixture() if case is None else case
    return prepare_personal(req,e,r,f,p,expected_evaluation=identity(e),expected_reference=identity(r))


def view(case=None):
    from investment_system.research.personal_sheet_v import personal_result
    return personal_result(prepare(case))


def test_owner_contract_has_executable_personal_adapter():
    assert importlib.util.find_spec(MODULE) is not None


def test_hand_ratio_full_roster_roles_and_personal_boundaries():
    case=fixture();before=deepcopy(case);out=view(case)
    assert out['namespace']=='PERSONAL_SHEET_V' and out['storage']=='EPHEMERAL_ONLY'
    assert out['rows'][0]['raw']['central::ebit_yield']==pytest.approx(200/1030)
    assert out['rows'][0]['raw']['central::fcf_yield']==pytest.approx(120/1030)
    assert out['rows'][0]['raw']['central::own_history'] is None
    assert out['counts']['price_available']==23 and out['counts']['raw_any']==23
    assert out['counts']['V_axis']==23 and out['counts']['personal_eligible_total']==23
    assert out['denominator']==dict(code_rows=23,issuers=23)
    assert 'target' not in out and 'coverage' not in out
    assert '"price":' not in json.dumps(out) and case==before
    assert all(r['roles']['v_vs_own_history']['score'] is None for r in out['rows'])


@pytest.mark.parametrize('change,reason',[
    ({'adjustment_status':'UNKNOWN'},'PRICE_ADJUSTMENT_UNCONFIRMED'),
    ({'trade_day':None},'PRICE_DAY_UNCONFIRMED'),
    ({'currency':'EUR'},'CURRENCY_BASIS_UNCONFIRMED'),
    ({'price':0},'INVALID_PRICE'),
    ({'status':'READ_FAILED','price':None},'READ_FAILED'),
    ({'trade_day':'2026-11-16'},'FUTURE_PRICE_DAY')])
def test_price_failures_keep_the_original_denominator(change,reason):
    case=fixture();case[4][0].update(change);out=view(case)
    assert out['denominator']['issuers']==23 and len(out['rows'])==23
    assert out['rows'][0]['raw']['central::ebit_yield'] is None
    assert reason in out['rows'][0]['price_metadata']['reasons']


def test_unconfirmed_time_is_not_receipt_time_or_measured_delay():
    case=fixture();case[4][0].update(time_status='UNCONFIRMED',price_timestamp=None)
    m=view(case)['rows'][0]['price_metadata']
    assert m['price_timestamp'] is None and m['actual_delay_seconds'] is None
    assert m['freshness']=='UNDETERMINED' and m['provider_delay_notice']=='UP_TO_20_MINUTES'
    case=fixture();case[4][0]['price_timestamp']='2026-11-13T20:00:00Z'
    m=view(case)['rows'][0]['price_metadata']
    assert m['freshness']=='DELAYED' and m['actual_delay_seconds']==3660


@pytest.mark.parametrize('part,field,value,reason',[
    ('mapping','issuer_id','wrong','IDENTITY_UNCONFIRMED'),
    ('mapping','valid_to','2026-11-12','IDENTITY_PERIOD_UNCONFIRMED'),
    ('share_basis','definition','ACTUAL_CLASS_SHARES','SHARE_BASIS_UNCONFIRMED'),
    ('share_basis','period_end','2026-10-30','SHARE_PERIOD_UNCONFIRMED'),
    ('corporate_actions','through_day','2026-11-04','CORPORATE_ACTION_BASIS_UNCONFIRMED')])
def test_price_does_not_prove_nonprice_basis(part,field,value,reason):
    case=fixture();cid=case[1]['rows'][0]['company_id'];case[3][cid]['basis_evidence'][part][field]=value
    out=view(case);assert out['counts']['price_available']==23
    assert reason in out['rows'][0]['price_metadata']['reasons']
    assert out['rows'][0]['raw']['central::ebit_yield'] is None


def test_cash_missing_only_blocks_ev_variants_without_zero_fill():
    case=fixture();cid=case[1]['rows'][0]['company_id'];record=case[3][cid]['record']
    record['v_inputs_v2']['cash_and_equivalents']['value']=None
    for s in case[1:3]:s['rows'][0]['owner_source_context']['record_hash']=digest(record)
    row=view(case)['rows'][0]
    assert row['raw']['central::ebit_yield'] is None and row['raw']['central::fcf_yield'] is None
    assert row['raw']['central::gap'] is not None


def test_future_current_quote_cannot_relabel_old_snapshot_or_independent_anchor():
    case=fixture();case[0]['context']['evaluation_day']='2026-11-04'
    with pytest.raises(ValueError,match='CURRENT_EVALUATION_CONTEXT'):prepare(case)
    from investment_system.research.personal_sheet_v import prepare_personal
    req,e,r,f,p=fixture();wrong=identity(r)
    with pytest.raises(ValueError,match='EVALUATION_ANCHOR'):
        prepare_personal(req,e,r,f,p,expected_evaluation=wrong,expected_reference=identity(r))


def test_personal_inputs_and_results_are_rejected_by_research_entrypoints():
    from investment_system.research.qgv_555_delivery import artifacts
    prepared=prepare()
    with pytest.raises(ValueError,match='PERSONAL_SCOPE'):
        run(prepared['configuration'],prepared['evaluation'],prepared['reference'])
    with pytest.raises(ValueError,match='PERSONAL_RESULT'):
        artifacts({'U1-555':prepared['core_result']},data_kind='PRIVATE')


def test_all_deciles_missing_members_and_filter_projection_are_fixed():
    from investment_system.research.personal_sheet_v import personal_group_page,personal_page
    out=view();group=next(g for g in out['groups'] if g['kind']=='roles' and g['key']=='v_earnings_yield')
    assert sum(x['count'] for x in group['bins'])==23
    members=[]
    for d in range(1,11):members+=personal_group_page(out,group['group_id'],decile=d)['rows']
    assert len(members)==23 and len({r['company_id'] for r in members})==23
    filtered=personal_page(out,company_ids=[out['rows'][10]['company_id']])
    assert filtered['rows'][0]['roles']==out['rows'][10]['roles']
    assert filtered['denominator']==out['denominator'] and not filtered['filter_recalculates']
    case=fixture();case[0]['context']['context_id']='another-synthetic-session'
    assert view(case)['groups'][0]['group_id']!=out['groups'][0]['group_id']


@pytest.mark.parametrize('n',[7,8,10])
def test_factor_minimum_and_decile_minimum_are_separate(n):
    out=view(fixture(n));r=out['rows'][0]
    assert (r['axes']['V'] is not None)==(n>=8)
    assert (r['roles']['v_earnings_yield']['decile'] is not None)==(n>=10)


def test_duplicate_price_input_is_not_silently_merged():
    case=fixture();case[4].append(deepcopy(case[4][0]))
    with pytest.raises(ValueError,match='DUPLICATE_PRICE'):prepare(case)


def test_future_balance_period_blocks_only_ev_roles():
    case=fixture();cid=case[1]['rows'][0]['company_id'];record=case[3][cid]['record']
    record['v_inputs_v2']['total_debt']['period_end']='2026-12-31'
    for s in case[1:3]:s['rows'][0]['owner_source_context']['record_hash']=digest(record)
    row=view(case)['rows'][0]
    assert row['raw']['central::ebit_yield'] is None
    assert row['raw']['central::fcf_yield'] is None
    assert row['raw']['central::gap'] is not None
    assert row['metrics']['v_earnings_yield|central::ebit_yield']['reason']=='EV_COMPONENT_PERIOD_UNCONFIRMED'


def test_s1_current_context_requires_current_classification_evidence():
    case=fixture();case[0]['configuration']=configuration('S1-555',version='0.4.0')
    for s in case[1:3]:
        for row in s['rows']:row['classification_mapping']['valid_to']='2026-11-12'
    out=view(case)
    assert out['counts']['raw_any']==23
    assert out['counts']['V_axis']==0
    assert all(r['roles']['v_earnings_yield']['score'] is None for r in out['rows'])


def test_adr_ratio_never_silently_converts_an_underlying_share_count():
    case=fixture();cid=case[1]['rows'][0]['company_id'];basis=case[3][cid]['basis_evidence']
    basis['mapping']['security_type']='ADR'
    assert 'ADR_RATIO_UNCONFIRMED' in view(case)['rows'][0]['price_metadata']['reasons']


def test_reference_membership_cannot_be_an_incomplete_row_intersection():
    case=fixture();case[2]['rows'].pop()
    with pytest.raises(ValueError,match='POPULATION_MEMBERS'):prepare(case)


def test_unlinked_financial_record_never_qualifies_a_quote_basis():
    case=fixture();del case[3][case[1]['rows'][0]['company_id']]
    row=view(case)['rows'][0]
    assert row['price_metadata']['price_available']
    assert not row['price_metadata']['qualified']
    assert all(x is None for x in row['raw'].values())


def test_bad_history_only_withholds_history_role():
    case=fixture();q=case[4][0]
    q.update(month_closes={'2026-12':10},history_basis_status='VERIFIED',
        history_share_basis='WEIGHTED_AVERAGE_DILUTED',history_source_refs=['SYNTHETIC'])
    row=view(case)['rows'][0]
    assert row['raw']['central::own_history'] is None
    assert row['raw']['central::ebit_yield'] is not None


def test_quote_mapping_covers_the_observation_day_too():
    case=fixture();q=case[4][0];q.update(trade_day='2026-09-01',price_timestamp='2026-09-01T20:00:00Z')
    assert 'IDENTITY_PERIOD_UNCONFIRMED' in view(case)['rows'][0]['price_metadata']['reasons']


def test_row_provenance_retains_basis_clocks_without_echoing_price_values():
    case=fixture();cid=case[1]['rows'][0]['company_id'];out=view(case);row=out['rows'][0]
    assert row['price_metadata']['currency']=='USD'
    assert row['price_metadata']['query_started_at']!=row['price_metadata']['price_timestamp']
    assert row['price_metadata']['source_refs']==case[4][0]['source_refs']
    assert row['provenance']['financial']['record_hash']==case[1]['rows'][0]['owner_source_context']['record_hash']
    assert row['provenance']['financial']['acquired_at']==case[3][cid]['record']['acquired_at']
    assert row['provenance']['basis']['mapping']['record_id'].startswith('synthetic-mapping-')
    assert 'personal_sheet_v.js' in out['engine_source_sha256']


def test_old_receipt_never_looks_fresh_at_a_new_current_evaluation():
    case=fixture();case[4][0].update(trade_day='2026-11-04',price_timestamp='2026-11-04T20:59:00Z',
        query_started_at='2026-11-04T21:00:00Z',received_at='2026-11-04T21:01:00Z')
    m=view(case)['rows'][0]['price_metadata']
    assert m['actual_delay_seconds']==120
    assert m['price_age_at_evaluation_seconds']>8*86400 and m['freshness']=='DELAYED'


def test_nonstring_issuer_is_rejected_without_ticker_or_id_coercion():
    case=fixture()
    for s in case[1:3]:s['rows'][0]['issuer_id']=123
    with pytest.raises(ValueError,match='PERSONAL_ISSUER_ID'):prepare(case)


def test_empty_context_or_removed_namespace_cannot_enter_research():
    from investment_system.research.qgv_555_delivery import artifacts
    prepared=prepare();e=deepcopy(prepared['evaluation']);r=deepcopy(prepared['reference'])
    e['personal_sheet_context']={};r['personal_sheet_context']={}
    with pytest.raises(ValueError,match='PERSONAL_SCOPE'):run(prepared['configuration'],e,r)
    board=deepcopy(prepared['core_result']);board.pop('namespace')
    board['result_hash']=digest({k:v for k,v in board.items() if k!='result_hash'})
    with pytest.raises(ValueError,match='PERSONAL_RESULT|RESEARCH_RESULT_SCHEMA'):
        artifacts({'U1-555':board},data_kind='PRIVATE')


def test_adr_period_must_be_a_real_date_and_cover_the_price_day():
    case=fixture();cid=case[1]['rows'][0]['company_id'];b=case[3][cid]['basis_evidence']
    b['mapping']['security_type']='ADR';b['share_basis']['unit']='ADR_RECEIPTS'
    b['adr']=dict(status='VERIFIED',source_refs=['SYNTHETIC_ADR'],available_at='2026-11-13T12:00:00Z',
        underlying_per_receipt=2,normalized_share_unit='ADR_RECEIPTS',valid_from='2026-09-30',valid_to='zzzz')
    assert 'ADR_RATIO_UNCONFIRMED' in view(case)['rows'][0]['price_metadata']['reasons']


def test_history_uses_the_same_quote_basis_and_requires_explicit_class_link():
    case=fixture();cid=case[1]['rows'][0]['company_id'];q=case[4][0]
    q['basis_evidence']=case[3][cid].pop('basis_evidence')
    q.update(month_closes={'2023-12':10,'2024-12':20,'2025-12':30},history_basis_status='VERIFIED',
        history_share_basis='WEIGHTED_AVERAGE_DILUTED',history_source_refs=['SYNTHETIC'])
    q['history_basis_evidence']=dict(status='VERIFIED',source_refs=['SYNTHETIC_HISTORY'],
        available_at='2026-11-13T12:00:00Z',share_basis='WEIGHTED_AVERAGE_DILUTED',currency='USD',
        basis='ALREADY_COMMON_SHARE_BASIS',from_day='2023-01-01',through_day='2026-11-13')
    assert view(case)['rows'][0]['raw']['central::own_history'] is None
    q['history_basis_evidence']['share_class_id']='SYN_COMMON'
    assert view(case)['rows'][0]['raw']['central::own_history'] is not None


def test_public_synthetic_wire_examples_match_schema_and_recorded_bytes():
    import jsonschema
    root=Path(__file__).resolve().parents[2]
    schema=json.loads((root/'docs/research/sector_qgv/personal-sheet-v-contract.json').read_bytes())
    folder=root/'tests/fixtures/personal-sheet-v';manifest=json.loads((folder/'manifest.json').read_bytes())
    import hashlib
    for item in manifest['files']:
        raw=(folder/item['path']).read_bytes()
        assert len(raw)==item['size'] and hashlib.sha256(raw).hexdigest()==item['sha256']
        assert len(raw)<=1_800_000
    for model in ('u1-555','s1-555'):
        req=json.loads((folder/(model+'-request.json')).read_bytes())
        out=json.loads((folder/(model+'-result.json')).read_bytes())
        jsonschema.Draft202012Validator(dict(schema,**{'$ref':'#/$defs/request'})).validate(req)
        jsonschema.Draft202012Validator(dict(schema,**{'$ref':'#/$defs/result'})).validate(out)
        assert out['context']['context_id'].startswith('synthetic-')
        assert all(row['company_id'].startswith('SYN:') for row in out['rows'])
    for quote in json.loads((folder/'input-prices.json').read_bytes()):
        jsonschema.Draft202012Validator(dict(schema,**{'$ref':'#/$defs/price_row'})).validate(quote)
