"""Synthetic, memory-only Node checks for the personal V adapter boundary."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from investment_system.research.qgv_555 import configuration
from investment_system.research.sector_qgv import digest


pytestmark = pytest.mark.skipif(shutil.which('node') is None, reason='Node runtime required')
ADAPTER = Path(__file__).resolve().parents[2] / 'src/investment_system/research/personal_sheet_v.js'
NODE = r"""
const fs = require('node:fs');
const request = JSON.parse(fs.readFileSync(0, 'utf8'));
(async () => {
  try {
    let adapter;
    if (request.browser) {
      const vm = require('node:vm');
      const path = require('node:path');
      const scope = vm.createContext({
        QgvV2: require(path.join(path.dirname(process.argv[1]), '../product/web_assets/qgv-v2.js')),
        crypto: require('node:crypto').webcrypto, TextEncoder,
      });
      vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), scope);
      adapter = scope.PersonalSheetV;
    } else adapter = require(process.argv[1]);
    const result = await adapter.calculate(request.text, request.options);
    const response = {result};
    if (request.reference_parameters) {
      const path = require('node:path');
      const V2 = require(path.join(path.dirname(process.argv[1]), '../product/web_assets/qgv-v2.js'));
      const packet = JSON.parse(request.text), entry = packet.evaluation[0];
      const reference = V2.scoreUniverse({synthetic: entry.company}, {synthetic: entry.quote},
        {typeWeights: false, parameters: packet.parameters});
      response.reference_gap = reference.synthetic.detail.expectation_gap;
    }
    process.stdout.write(JSON.stringify(response));
  } catch (error) {
    process.stdout.write(JSON.stringify({error: error.code || error.message}));
  }
})();
"""


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def packet(n=10, candidate='U1-555'):
    config = configuration(candidate, version='0.2.0')
    rows = []
    for i in range(n):
        code = f'SYN:{i:03d}'
        rows.append(dict(company_id=code, issuer_id=f'issuer-{i}',
            industry_group='synthetic', sector_id='synthetic-sector', accounting_template='GENERAL',
            ranking_scope='COMMON' if candidate=='U1-555' else 'SECTOR|synthetic-sector|GENERAL',
            supported=True, reference_included=True,
            company=dict(profile='GENERAL', v_inputs=dict(currency='USD', ebit=200+i,
                fcf=120+i, diluted_shares=100, total_debt=50, cash=20,
                revenue_cagr_3y=.1, ebit_per_share_history=[])),
            quote=dict(price=10, currency='USD'), raw_reasons={}, price_metadata={},
            base_axes=dict(Q=60, G=70), gate_status='PASS', axis_weights=dict(Q=34, G=33, V=33),
            roles={k:deepcopy(v) for k,v in config['roles'].items() if v['axis']=='V'}))
    original = dict(population_id='합성 평가', population_version='current/1',
        evaluation_day='2026-11-14', input_cutoff='2026-11-14T20:00:00Z',
        members_hash='a'*64, input_hash='b'*64, code_rows=n, issuers=n)
    reference = dict(original, population_id='합성 참조', input_hash='c'*64)
    return dict(schema_version='personal-sheet-v-packet/1', namespace='PERSONAL_SHEET_V',
        context=dict(context_id='synthetic-current', evaluation_day='2026-11-14'),
        configuration=config, configuration_hash=digest(config), evaluation_original=original,
        reference_original=reference, evaluation_effective=dict(original, input_hash='d'*64),
        reference_effective=dict(reference, input_hash='e'*64), evaluation=deepcopy(rows), reference=rows)


def options(p, text):
    return dict(expected_payload_sha256=hashlib.sha256(text.encode()).hexdigest(),
        expected_evaluation=deepcopy(p['evaluation_original']),
        expected_reference=deepcopy(p['reference_original']),
        expected_configuration_hash=p['configuration_hash'])


def calculate(p, *, override=None, text=None, browser=False, reference_parameters=False):
    text = encode(p) if text is None else text
    pins = options(p, text)
    if override:
        pins.update(override)
    run = subprocess.run(['node', '-e', NODE, str(ADAPTER)],
        input=encode(dict(text=text, options=pins, browser=browser,
            reference_parameters=reference_parameters)), text=True, capture_output=True, check=False)
    assert run.returncode == 0, 'PERSONAL_V_NODE_EXECUTION_FAILED'
    return json.loads(run.stdout)


def result(p):
    response = calculate(p)
    assert 'result' in response, response
    return response['result']


def test_existing_js_raw_kernel_and_personal_v_roles_preserve_full_population():
    p=packet();before=deepcopy(p);out=result(p)
    assert out['schema_version']=='personal-sheet-v-js-result/1'
    assert out['namespace']=='PERSONAL_SHEET_V'
    assert out['evaluation_original']==p['evaluation_original']
    assert out['reference_original']==p['reference_original']
    assert len(out['rows'])==10
    first,last=out['rows'][0],out['rows'][-1]
    assert first['raw']['central::ebit_yield']==pytest.approx(200/1030)
    assert first['raw']['central::fcf_yield']==pytest.approx(120/1030)
    assert first['raw']['central::own_history'] is None
    assert first['roles']['v_earnings_yield']['score']==0
    assert last['roles']['v_earnings_yield']['score']==100
    assert first['axes']==dict(Q=60,G=70,V=0)
    assert last['axes']==dict(Q=60,G=70,V=100)
    assert first['total']==pytest.approx(43.5)
    assert last['total']==pytest.approx(76.5)
    assert first['roles']['v_earnings_yield']['decile']==1
    assert last['roles']['v_earnings_yield']['decile']==10
    assert first['rank']==10 and last['rank']==1
    assert p==before
    assert all('quote' not in r and 'company' not in r for r in out['rows'])


@pytest.mark.parametrize('pin,error',[
    ('expected_payload_sha256','PERSONAL_PAYLOAD_HASH'),
    ('expected_evaluation','PERSONAL_EVALUATION_ANCHOR'),
    ('expected_reference','PERSONAL_REFERENCE_ANCHOR'),
    ('expected_configuration_hash','PERSONAL_CONFIGURATION_ANCHOR'),
])
def test_external_payload_and_independent_anchors_cannot_be_replaced(pin,error):
    p=packet();replacement='f'*64 if pin.endswith('sha256') or pin.endswith('hash') else dict(input_hash='f'*64)
    assert calculate(p,override={pin:replacement})==dict(error=error)
    if pin=='expected_payload_sha256':
        original=encode(p)
        assert calculate(p,text=original+' ',override={pin:hashlib.sha256(original.encode()).hexdigest()})==dict(error=error)


@pytest.mark.parametrize('n,score,decile_status',[(7,None,'NO_VALID_SCORE'),(8,0,'SAMPLE_LT_10'),(10,0,'VALID'),(23,0,'VALID')])
def test_valid_reference_minimum_and_existing_ordinal_decile_rule(n,score,decile_status):
    out=result(packet(n));rows=out['rows'];role=rows[0]['roles']['v_earnings_yield']
    assert len(rows)==n and role['score']==score
    assert role['metrics'][0]['reference_n']==n
    assert role['decile_status']==decile_status
    if n==23:
        assert [r['roles']['v_earnings_yield']['decile'] for r in reversed(rows)]==[
            10,10,9,9,9,8,8,8,7,7,7,6,6,5,5,4,4,3,3,2,2,1,1]


def test_u1_industry_fallback_and_s1_no_fallback_use_valid_metric_counts():
    unified=packet(10)
    for side in ('evaluation','reference'):
        for i,r in enumerate(unified[side]):
            r['industry_group']='small' if i<2 else 'large'
    out=result(unified);role=out['rows'][0]['roles']['v_vs_industry']['metrics'][0]
    assert role['reference_n']==10 and role['reference_scope']=='all'
    sector=packet(10,'S1-555')
    for side in ('evaluation','reference'):
        for i,r in enumerate(sector[side]):
            r['sector_id']='small' if i<2 else 'large'
            r['ranking_scope']='SECTOR|'+r['sector_id']+'|GENERAL'
    rows=result(sector)['rows']
    assert rows[0]['roles']['v_earnings_yield']['score'] is None
    assert rows[0]['roles']['v_earnings_yield']['metrics'][0]['reference_n']==2
    assert rows[-1]['roles']['v_earnings_yield']['metrics'][0]['reference_n']==8


def test_issuer_point_replaced_and_duplicate_reference_codes_do_not_inflate_n():
    p=packet(8);duplicate=deepcopy(p['reference'][0]);duplicate['company_id']='SYN:SECOND'
    p['reference'].append(duplicate)
    target=p['evaluation'][0];target['company_id']='SYN:TARGET';target['company']['v_inputs']['ebit']=500
    rows=result(p)['rows'];target=next(r for r in rows if r['company_id']=='SYN:TARGET')
    metric=target['roles']['v_earnings_yield']['metrics'][0]
    assert metric['reference_n']==8 and metric['score']==100


def test_duplicate_issuer_conflicting_raw_or_scope_is_rejected_before_deduplication():
    for changed in ('raw','industry_group','sector_id','accounting_template','ranking_scope'):
        p=packet(8);duplicate=deepcopy(p['reference'][0]);duplicate['company_id']='SYN:SECOND'
        if changed=='raw':duplicate['company']['v_inputs']['ebit']=999
        else:duplicate[changed]='SYNTHETIC_DIFFERENT_SCOPE'
        p['reference'].append(duplicate)
        assert calculate(p)==dict(error='PERSONAL_ISSUER_POINT_CONFLICT'),changed


def test_explicit_packet_parameters_reach_the_existing_js_reverse_dcf_kernel():
    from investment_system.qgv.dcf_parameters import load_default_dcf_parameters
    p=packet(8);p['parameters']=load_default_dcf_parameters()
    p['parameters']['discount_rate']=.2  # Synthetic sensitivity; adopted defaults stay unchanged.
    response=calculate(p,reference_parameters=True)
    assert 'result' in response,response
    assert response['reference_gap'] is not None
    assert response['result']['rows'][0]['raw']['central::gap']==pytest.approx(response['reference_gap'])


def test_own_history_keeps_existing_direct_score_and_metric_reasons_are_independent():
    p=packet(10)
    for side in ('evaluation','reference'):
        for r in p[side]:
            r['company']['v_inputs']['ebit_per_share_history']=[
                dict(period_end=f'{y}-12-31',value=v) for y,v in [(2023,1),(2024,2),(2025,3)]]
            r['quote']['month_closes']={f'{y}-12':10 for y in (2023,2024,2025)}
    row=result(p)['rows'][0]
    assert row['raw']['central::own_history']==50
    assert row['roles']['v_vs_own_history']['score']==50
    history=row['roles']['v_vs_own_history']['metrics'][0]
    assert history['reference_n']==0 and history['reference_scope']=='OWN_HISTORY'
    p['evaluation'][0]['raw_reasons']={'central::ebit_yield':'SYNTHETIC_EARNINGS_BASIS_MISSING'}
    row=result(p)['rows'][0]
    assert row['raw']['central::ebit_yield'] is None
    assert row['roles']['v_earnings_yield']['metrics'][0]['reason']=='SYNTHETIC_EARNINGS_BASIS_MISSING'
    assert row['raw']['central::fcf_yield']==pytest.approx(120/1030)


@pytest.mark.parametrize('history_n,expected,reason',[(2,None,'HISTORY_TOO_SHORT'),(3,50,None)])
def test_own_history_uses_three_past_values_without_cross_section_minimum(history_n,expected,reason):
    p=packet(1)
    for side in ('evaluation','reference'):
        row=p[side][0]
        row['company']['v_inputs']['ebit_per_share_history']=[
            dict(period_end=f'{2023+i}-12-31',value=i+1) for i in range(history_n)]
        row['quote']['month_closes']={f'{2023+i}-12':10 for i in range(history_n)}
    row=result(p)['rows'][0]
    metric=row['roles']['v_vs_own_history']['metrics'][0]
    assert metric['score']==expected and metric['reason']==reason
    assert metric['reference_n']==0


def test_missing_price_gate_financial_and_unconnected_variant_stay_explicit():
    p=packet(10);p['evaluation'][0]['quote']=None
    p['evaluation'][1]['gate_status']='UNKNOWN';p['evaluation'][2]['gate_status']='VALUE_EXCLUDED'
    p['evaluation'][3]['company']['profile']='FINANCIAL'
    for role in p['evaluation'][3]['roles'].values():role['metrics']={}
    p['evaluation'][4]['roles']['v_fcf_yield']['metrics']={'sector::fcf_ev':1}
    rows=result(p)['rows']
    assert all(v is None for v in rows[0]['raw'].values())
    assert rows[0]['partial_total'] is True and rows[0]['rank'] is None
    assert rows[1]['total'] is None
    assert rows[2]['total']==pytest.approx(43.5/.67)
    assert all(v is None for v in rows[3]['raw'].values())
    assert all(r['score'] is None for r in rows[3]['roles'].values())
    assert rows[4]['roles']['v_fcf_yield']['metrics'][0]['reason']=='PERSONAL_VARIANT_NOT_CONNECTED'


def test_browser_webcrypto_uses_the_same_real_engine_and_utf8_packet_as_node():
    p=packet(8);p['configuration']['roles']['v_fcf_yield']['weight']=25.0
    p['configuration_hash']=digest(p['configuration'])
    assert calculate(p,browser=True)==calculate(p)
    wrong=dict(expected_evaluation=dict(p['evaluation_original'],input_hash='f'*64))
    assert calculate(p,browser=True,override=wrong)==dict(error='PERSONAL_EVALUATION_ANCHOR')


def test_tied_roles_and_metrics_keep_code_order_and_complete_personal_deciles():
    p=packet(10)
    for side in ('evaluation','reference'):
        for entry in p[side]:
            entry['company']['v_inputs']['ebit']=200
    p['evaluation'].reverse();p['reference'].reverse()
    rows=result(p)['rows']
    assert [r['company_id'] for r in rows]==[f'SYN:{i:03d}' for i in range(10)]
    for i,row in enumerate(rows):
        role=row['roles']['v_earnings_yield']
        metric=row['metrics']['v_earnings_yield|central::ebit_yield']
        assert role['score']==metric['score']==50
        assert role['rank']==metric['rank']==i+1
        assert role['decile']==metric['decile']==10-i
        assert role['metrics'][0]['rank']==i+1
        assert role['metrics'][0]['decile']==10-i


def test_axis_fifty_percent_boundary_and_debt_missing_are_separate_from_price_failure():
    p=packet(10)
    for row in p['evaluation']:
        row['roles']['v_vs_industry']['metrics']={'sector::ebit_ev':1}
        row['roles']['v_expectation_check']['metrics']={'sector::ep_ttm_diluted':1}
    assert result(p)['rows'][0]['axes']['V']==0  # 25+25 of 100 is available.
    p['evaluation'][0]['roles']['v_earnings_yield']['weight']=24
    p['evaluation'][1]['company']['v_inputs']['total_debt']=None
    p['evaluation'][2].update(supported=False,support_reason='SECTOR_CLASSIFICATION_UNCONFIRMED')
    rows=result(p)['rows']
    assert rows[0]['axes']['V'] is None
    assert rows[1]['raw']['central::ebit_yield'] is None
    assert rows[1]['raw']['central::fcf_yield'] is None
    assert rows[1]['raw']['central::gap'] is not None
    assert rows[1]['roles']['v_earnings_yield']['metrics'][0]['reason']=='DEBT_CASH_NOT_AVAILABLE'
    assert rows[2]['raw']['central::ebit_yield'] is not None
    assert rows[2]['roles']['v_earnings_yield']['metrics'][0]['reason']=='SECTOR_CLASSIFICATION_UNCONFIRMED'


def assert_numeric_contract(actual,expected,at='$'):
    if type(expected) in (float,int):
        assert type(actual) in (float,int),at
        assert actual==pytest.approx(expected,rel=1e-9,abs=1e-9),at
    elif isinstance(expected,dict):
        assert set(actual)==set(expected),at
        for key,value in expected.items():assert_numeric_contract(actual[key],value,at+'.'+key)
    elif isinstance(expected,list):
        assert len(actual)==len(expected),at
        for i,value in enumerate(expected):assert_numeric_contract(actual[i],value,at+f'[{i}]')
    else:assert actual==expected,at


def row_projection(row):
    keys=('company_id','issuer_id','ranking_scope','raw','metrics','axes','gate_status',
          'total','partial_total','rank','rank_n')
    out={key:deepcopy(row[key]) for key in keys}
    fields=('metric','raw','score','reason','reference_n','reference_scope','weight')
    out['roles']={key:{**{k:deepcopy(value[k]) for k in ('score','rank','rank_n','decile','decile_status')},
        'metrics':[{k:item[k] for k in fields} for item in value['metrics']]} for key,value in row['roles'].items()}
    return out


@pytest.mark.parametrize('n,candidate',[(7,'U1-555'),(8,'U1-555'),(10,'U1-555'),(23,'U1-555'),(10,'S1-555')])
def test_real_python_preparer_packet_matches_existing_node_engine_and_555_rows(n,candidate):
    from test_personal_sheet_v import fixture,prepare
    from investment_system.research.personal_sheet_v import personal_result
    case=fixture(n);case[0]['configuration']=configuration(candidate,version='0.4.0')
    prepared=prepare(case);wanted=personal_result(prepared)
    response=calculate(prepared['packet'],text=prepared['packet_text'],
        override={'expected_payload_sha256':prepared['payload_sha256']})
    assert 'result' in response,response
    actual=response['result']
    assert actual['evaluation_original']==prepared['packet']['evaluation_original']
    assert actual['reference_original']==prepared['packet']['reference_original']
    if candidate=='S1-555':
        assert all(entry['supported'] for entry in prepared['packet']['evaluation'])
        assert all(row['axes']['V'] is not None for row in actual['rows'])
    assert_numeric_contract([row_projection(r) for r in actual['rows']],
                            [row_projection(r) for r in wanted['rows']])


@pytest.mark.parametrize('mode',['missing_price','missing_financial','cash_missing','history','history_unverified','adjustment_unknown','financial_source','custom_weights','unsupported_row','sector_unconfirmed','financial_temporary'])
def test_real_python_preparer_failure_history_and_weight_contracts_match_node(mode):
    from test_personal_sheet_v import fixture,prepare
    from investment_system.research.personal_sheet_v import personal_result
    case=fixture(10);req,e,ref,financial,prices=case;cid=e['rows'][0]['company_id']
    if mode=='missing_price':prices.pop(0)
    if mode=='missing_financial':financial.pop(cid)
    if mode=='cash_missing':financial[cid]['record']['v_inputs_v2']['cash_and_equivalents']['value']=None
    if mode=='adjustment_unknown':prices[0]['adjustment_status']='UNKNOWN'
    if mode=='financial_source':financial[cid]['record']['profile']='FINANCIAL'
    if mode=='unsupported_row':
        for s in (e,ref):s['rows'][0]['accounting_template']='BANK'
    if mode=='sector_unconfirmed':
        req['configuration']=configuration('S1-555',version='0.4.0')
        for s in (e,ref):s['rows'][0]['sector_id']=None
    if mode=='financial_temporary':
        from investment_system.research.qgv_555 import FINANCIAL_TEMP_POLICY
        req['configuration']=configuration('U1-555',version='0.5.0')
        financial[cid]['record']['profile']='FINANCIAL'
        for s in (e,ref):
            s['rows'][0].update(accounting_template='BANK',financial_peer_template='BANK',
                financial_calculation_profile='FINANCIAL',financial_temporary_policy=FINANCIAL_TEMP_POLICY,
                financial_temporary_source_refs=['SYNTHETIC_FINANCIAL_TEMPORARY'])
            s['rows'][0]['owner_source_context']['profile']='FINANCIAL'
    if mode in ('history','history_unverified'):
        for quote in prices:
            quote.update(month_closes={f'{y}-12':10 for y in (2023,2024,2025)},
                history_basis_status='VERIFIED',history_share_basis='WEIGHTED_AVERAGE_DILUTED',
                history_source_refs=['SYNTHETIC_CURRENT_HISTORY_REVIEW'])
            if mode=='history':
                quote['history_basis_evidence']=dict(status='VERIFIED',available_at=req['context']['input_cutoff'],
                    source_refs=['SYNTHETIC_FULL_USED_HISTORY_BASIS'],share_class_id='SYN_COMMON',
                    share_basis='WEIGHTED_AVERAGE_DILUTED',currency='USD',basis='ALREADY_COMMON_SHARE_BASIS',
                    from_day='2023-12-31',through_day=req['context']['evaluation_day'])
    if mode=='custom_weights':
        req['configuration']['axis_weights']=dict(Q=50.0,G=20,V=30)
        for role,weight in zip(('v_earnings_yield','v_fcf_yield','v_vs_industry','v_vs_own_history','v_expectation_check'),(40,10,30,10,10)):
            req['configuration']['roles'][role]['weight']=weight
    if mode in ('cash_missing','financial_source','financial_temporary'):
        for s in (e,ref):
            context=s['rows'][0]['owner_source_context'];record=financial[cid]['record']
            context['record_hash']=digest(record)
            context.update({k:record[k] for k in ('acquired_at','fiscal_year_end','currency','calc_version')})
    prepared=prepare(case);wanted=personal_result(prepared)
    response=calculate(prepared['packet'],text=prepared['packet_text'],
        override={'expected_payload_sha256':prepared['payload_sha256']})
    assert 'result' in response,response
    assert_numeric_contract([row_projection(r) for r in response['result']['rows']],
                            [row_projection(r) for r in wanted['rows']])
    if mode=='unsupported_row':
        row=response['result']['rows'][0]
        assert row['raw']['central::ebit_yield'] is not None
        assert row['roles']['v_earnings_yield']['metrics'][0]['raw'] is None
    if mode=='sector_unconfirmed':
        row=response['result']['rows'][0]
        assert row['roles']['v_earnings_yield']['metrics'][0]['raw'] is not None
        assert row['roles']['v_earnings_yield']['metrics'][0]['reason']==prepared['packet']['evaluation'][0]['support_reason']
    if mode=='history':
        row=response['result']['rows'][0]
        assert row['raw']['central::own_history']==50
        assert row['roles']['v_vs_own_history']['score']==50
    if mode=='history_unverified':
        row=response['result']['rows'][0]
        assert row['raw']['central::own_history'] is None
        assert row['roles']['v_vs_own_history']['metrics'][0]['reason']=='HISTORY_PRICE_SHARE_BASIS_UNVERIFIED'
        assert row['raw']['central::ebit_yield'] is not None
