"""New adapter and affected CLI integration only; synthetic source receipts."""
from copy import deepcopy
from hashlib import sha256
import importlib
import json
from pathlib import Path
import subprocess
import sys

import pytest
def held_fixture():
    spec=importlib.util.spec_from_file_location('held_test_fixture',Path(__file__).with_name('test_financial_v_bridge.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.fixture()


def blob(v):return json.dumps(v,sort_keys=True,allow_nan=False).encode()
def sha(v):return sha256(v).hexdigest()


def sample():
    row=dict(row_index=12,code='NYSE:TEST',iex_symbol='TEST',state='PRICE',reason='REGULAR_SESSION_ROUND_LOT_LAST_TRADE',
             parser_status='ROUND',price='40.0000',last_trade_ns=1793653140123456789,
             last_trade_utc='2026-11-02T20:59:00.123456789Z',basis_date='2026-11-02',
             source='IEX_HIST TOPS 1.6 last regular-session trade',parser_source_sha256='a'*64)
    derived=dict(schema_version='iex-day-financial11-last-trade/1',basis_date='2026-11-02',source=row['source'],
                 basis_kind='IEX_LAST_REGULAR_SESSION_TRADE',currency='USD',unit='USD/share',adjustment_basis='AS_TRADED',
                 acquired_at_utc='2026-11-03T01:00:00Z',generated_at_utc='2026-11-03T01:01:00Z',manifest='manifest-r1a1.json',
                 release_tag='current-iex-20261102',original={'sha256':'b'*64,'md5':'c'*32,'bytes':100},
                 input={'commit':'d'*40,'path':'synthetic/input.json','file_sha256':'e'*64,'row_indexes':[12]},
                 session_window_ns=[1793629800000000000,1793653200000000000],parser_source_sha256='a'*64,
                 parser_git_commit='d'*40,rows=[row],states={'PRICE':1,'NO_TRADE':0,'NOT_IN_FILE':0,'PRICE_INVALID':0})
    manifest=dict(schema_version='iex-day-preserve-once/2',state='COMPLETE',day='2026-11-02',manifest_name='manifest-r1a1.json',
                  release_tag=derived['release_tag'],parser={'source_sha256':'a'*64,'git_commit':'d'*40},
                  received={**derived['original'],'started_at_utc':'2026-11-03T00:50:00Z','completed_at_utc':derived['acquired_at_utc'],'exit_codes':[0,0,0]},
                  reassembly={'mode':'STREAMING_NO_FILE','bytes':100,'chunks':1,'sha256_match':True,'md5_match':True,'gzip_test_ok':True,'verified_at_utc':'2026-11-03T01:00:30Z'},
                  chunks=[{'name':'part-01','size':100,'sha256':'f'*64}],
                  completeness=dict(size_match=True,md5_match=True,gzip_exit_0=True,parser_exit_0=True,curl_exit_0=True,all_chunks_verified=True,reassembly_streaming_verified=True,derived_rows=1,derived_rows_expected=1),
                  input=deepcopy(derived['input']),session_window_ns=derived['session_window_ns'],written_at_utc='2026-11-03T01:02:00Z')
    request=dict(schema='financial-v-pending-price-requests/1',records=[dict(row_index=12,code='NYSE:TEST',cik='0000000001',primary_metric='earnings_yield',valuation_date='2026-11-02',required_share_basis='FY0:0000000001-26-000001:2026-02-01')])
    basis=dict(records={'NYSE:TEST':{'earnings_yield':dict(code='NYSE:TEST',cik='0000000001',iex_symbol='TEST',currency='USD',
               share_basis=request['records'][0]['required_share_basis'],identity_status='DOCUMENT_LINKED',
               action_status='MATCHED_TO_NUMERATOR',valid_from='2026-11-02',valid_to='2026-11-02',
               evidence_refs=[{'sha256':'9'*64,'locator':'synthetic-reviewed-class-and-actions'}])}})
    return manifest,derived,request,basis


def call(m,d,r,b):
    spec=importlib.util.find_spec('investment_system.research.financial_v_iex')
    assert spec is not None,'IEX financial input adapter missing'
    mod=importlib.import_module(spec.name)
    raw=blob(d)
    m=deepcopy(m);m['derived']=dict(name='derived-r1a1.json',schema_version=d['schema_version'],sha256=sha(raw),bytes=len(raw),rows=len(d['rows']),states=d['states'],generated_at_utc=d['generated_at_utc'])
    return mod.adapt(blob(m),raw,blob(r),blob(b),valuation_date='2026-11-02',input_vintage='2026-11-04T12:00:00Z')


def test_price_normalization_preserves_all_three_clocks_and_original_decimal():
    a=call(*sample());q=a['prices']['records']['NYSE:TEST']['earnings_yield']
    assert q['value']==40 and q['currency']=='USD' and q['unit']=='USD/share'
    assert q['traded_at']=='2026-11-02T20:59:00.123456789Z'
    assert q['acquired_at']=='2026-11-03T01:00:00Z'
    assert a['generated_at']=='2026-11-03T01:01:00Z'
    assert a['trade_evidence']['records']['NYSE:TEST']['original_price_text']=='40.0000'
    assert a['summary']['price_available_codes']==1 and a['summary']['price_ready_codes']==1


@pytest.mark.parametrize('state,reason',[('NO_TRADE','ODD_LOT_ONLY'),('NOT_IN_FILE','SYMBOL_NOT_IN_FILE'),('PRICE_INVALID','PRICE_OUT_OF_RANGE')])
def test_nonprice_states_are_preserved_not_zero_filled(state,reason):
    m,d,r,b=sample();d['rows'][0].update(state=state,reason=reason,price=None,last_trade_ns=None,last_trade_utc=None,parser_status='NO_TRADE')
    d['states']={s:int(s==state) for s in d['states']}
    a=call(m,d,r,b)
    assert a['prices']['records']['NYSE:TEST']['earnings_yield'] is None
    assert a['rows'][0]['source_state']==state and reason in a['rows'][0]['reasons']
    assert a['summary']['price_available_codes']==0


@pytest.mark.parametrize('change,reason',[
    ('date','DATE_MISMATCH'),('acquisition','ACQUISITION_COMPLETED_REQUIRED'),
    ('original_hash','ORIGINAL_RECEIPT_MISMATCH'),('reassembly','ORIGINAL_REASSEMBLY_UNVERIFIED'),
    ('future_acquisition','CAPTURE_AFTER_VINTAGE'),('duplicate','REQUEST_MEMBERSHIP_MISMATCH'),
])
def test_handoff_integrity_and_time_fail_closed(change,reason):
    m,d,r,b=sample()
    if change=='date':d['basis_date']='2026-11-01'
    if change=='acquisition':m['received'].pop('completed_at_utc')
    if change=='original_hash':d['original']['sha256']='0'*64
    if change=='reassembly':m['reassembly']['sha256_match']=False
    if change=='future_acquisition':m['received']['completed_at_utc']=d['acquired_at_utc']='2026-11-05T00:00:00Z'
    if change=='duplicate':d['rows']*=2
    with pytest.raises(ValueError,match=reason):call(m,d,r,b)


@pytest.mark.parametrize('change,reason',[
    ('missing','PRICE_BASIS_UNCONFIRMED'),('identity','PRICE_IDENTITY_UNCONFIRMED'),
    ('actions','PRICE_ACTIONS_UNCONFIRMED'),('currency','PRICE_CURRENCY_MISMATCH'),
    ('basis','PRICE_SHARE_BASIS_MISMATCH'),('timestamp','PRICE_TIMESTAMP_NS_MISMATCH'),
    ('nonfinite','PRICE_INVALID_VALUE'),
])
def test_price_can_arrive_without_becoming_an_adoptable_input(change,reason):
    m,d,r,b=sample();proof=b['records']['NYSE:TEST']['earnings_yield']
    if change=='missing':b['records']={}
    if change=='identity':proof['identity_status']='SYMBOL_ONLY'
    if change=='actions':proof['action_status']='UNCONFIRMED'
    if change=='currency':proof['currency']='CAD'
    if change=='basis':proof['share_basis']='OTHER_CLASS'
    if change=='timestamp':d['rows'][0]['last_trade_ns']+=1
    if change=='nonfinite':d['rows'][0]['price']='NaN'
    a=call(m,d,r,b)
    assert a['prices']['records']['NYSE:TEST']['earnings_yield'] is None
    assert reason in a['rows'][0]['reasons']


def test_derived_hash_mismatch_is_rejected_before_conversion():
    m,d,r,b=sample();raw=blob(d)
    m['derived']=dict(name='derived.json',sha256='0'*64,bytes=len(raw))
    spec=importlib.util.find_spec('investment_system.research.financial_v_iex');assert spec
    with pytest.raises(ValueError,match='DERIVED_HASH_MISMATCH'):
        importlib.import_module(spec.name).adapt(blob(m),raw,blob(r),blob(b),valuation_date='2026-11-02',input_vintage='2026-11-04T12:00:00Z')


@pytest.mark.parametrize('sic,adopted',[('6021',0),('6282',1)])
def test_existing_cli_runs_adapter_then_existing_ratio_engine(tmp_path,sic,adopted):
    x=held_fixture();m,d,r,b=sample()
    x['record']['sic']=sic
    b['records']['NYSE:TEST']['earnings_yield']['evidence_refs']=[{'sha256':sha(x['cover_bytes']),'locator':'synthetic-reviewed-class-and-actions'}]
    # call() produces the exact Main manifest digest attached to the result.
    def save(n,data):
        raw=data if isinstance(data,bytes) else blob(data);(tmp_path/n).write_bytes(raw)
        return {'path':n,'sha256':sha(raw)}
    raw=blob(d);m['derived']=dict(name='derived-r1a1.json',schema_version=d['schema_version'],sha256=sha(raw),bytes=len(raw),rows=1,states=d['states'],generated_at_utc=d['generated_at_utc'])
    records={'NYSE:TEST':{**x['record'],'profile':'FINANCIAL'}}
    records.update({f'SYNTHETIC:{i}':{'profile':'GENERAL'} for i in range(503)})
    job=dict(valuation_date=x['valuation_date'],input_vintage=x['input_vintage'],
        universe=save('universe.json',{'records':records}),shares=save('shares.json',{'records':{'NYSE:TEST':x['shares']}}),
        issuers=[dict(code='NYSE:TEST',companyfacts=save('facts.json',x['companyfacts_bytes']),cover=save('cover.xml',x['cover_bytes']))],
        iex_handoff=dict(manifest=save('manifest-r1a1.json',m),derived=save('derived-r1a1.json',d),requests=save('request.json',r),basis=save('basis.json',b),basis_evidence=[save('proof.xml',x['cover_bytes'])]))
    save('job.json',job)
    script=Path(__file__).parents[1]/'tools/financial_v_connect.py'
    cmd=[sys.executable,str(script),'--manifest',str(tmp_path/'job.json'),'--output',str(tmp_path/'out.json')]
    run=subprocess.run(cmd,capture_output=True,text=True);assert run.returncode==0,run.stderr
    out=json.loads((tmp_path/'out.json').read_text())
    assert out['rows'][0]['result']['metrics']['earnings_yield']['value']==0.1
    assert out['iex_handoff']['summary']['raw_ratio_metrics']==1
    # Bank primary is TB/P, so the available EPS ratio does not adopt the primary.
    assert out['iex_handoff']['summary']['primary_adopted_codes']==adopted
    assert out['rows'][0]['result']['score'] is None


def test_manifest_input_receipt_cannot_be_swapped_and_failed_parser_cannot_complete():
    m,d,r,b=sample();m['input']['file_sha256']='0'*64
    with pytest.raises(ValueError,match='INPUT_RECEIPT_MISMATCH'):call(m,d,r,b)
    m,d,r,b=sample();m['received']['exit_codes']=[0,0,1]
    with pytest.raises(ValueError,match='ORIGINAL_REASSEMBLY_UNVERIFIED'):call(m,d,r,b)


@pytest.mark.parametrize('symbol',[None,'',123,'BAD SYMBOL'])
def test_two_missing_or_invalid_symbols_do_not_prove_identity(symbol):
    m,d,r,b=sample();d['rows'][0]['iex_symbol']=symbol
    b['records']['NYSE:TEST']['earnings_yield']['iex_symbol']=symbol
    out=call(m,d,r,b)
    assert out['summary']['price_ready_codes']==0
    assert 'PRICE_IDENTITY_UNCONFIRMED' in out['rows'][0]['reasons']


def test_manifest_written_after_vintage_is_not_available_input():
    m,d,r,b=sample();m['written_at_utc']='2026-11-05T00:00:00Z'
    with pytest.raises(ValueError,match='HANDOFF_CLOCK_MISMATCH'):call(m,d,r,b)


def test_preclose_null_row_does_not_claim_final_session_absence():
    m,d,r,b=sample()
    d['rows'][0].update(state='NO_TRADE',reason='ODD_LOT_ONLY',parser_status='ODD_ONLY',price=None,last_trade_ns=None,last_trade_utc=None)
    d['states']={s:int(s=='NO_TRADE') for s in d['states']}
    m['received']['started_at_utc']='2026-11-02T15:00:00Z'
    m['received']['completed_at_utc']=d['acquired_at_utc']='2026-11-02T15:01:00Z'
    m['reassembly']['verified_at_utc']='2026-11-02T15:02:00Z'
    d['generated_at_utc']='2026-11-02T15:03:00Z';m['written_at_utc']='2026-11-02T15:04:00Z'
    with pytest.raises(ValueError,match='CAPTURE_BEFORE_SESSION_COMPLETE'):call(m,d,r,b)
