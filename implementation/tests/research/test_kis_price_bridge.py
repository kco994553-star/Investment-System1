import json, hashlib
from copy import deepcopy
from decimal import Decimal
import pytest
from investment_system.research.kis_price_bridge import normalize_page, analyze, value_positions, compare, merge_update, SCHEMA


def fixture():
    days=['2026-10-19','2026-10-20','2026-10-21','2026-10-22','2026-10-23']
    data={'rt_cd':'0','output1':{'rsym':'DNASSYN'},'output2':[dict(xymd=d.replace('-',''),open='10',high='12',low='9',clos='11',tvol='0' if i==0 else '100',tamt='1100') for i,d in enumerate(days)]}
    body=json.dumps(data).encode()
    receipt={'sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body),'fetched_at':'2026-10-24T04:00:00Z','http_status':200}
    request={'SYMB':'SYN','EXCD':'NAS','MODP':'0','GUBN':'0','BYMD':'20261023'}
    evidence={'price_scope_status':'CONFIRMED','currency':'USD','currency_reference':'synthetic currency','identity_status':'CONFIRMED','identity_reference':'synthetic listing','identity_start':days[0],'identity_end':days[-1],'security_id':'SYN-SEC-1','confirmed_ranges':[{'from':days[0],'to':days[-1],'evidence':'synthetic no split'}],'held_ranges':[],'splits':[]}
    return body,receipt,request,evidence


def make():
    a,b,c,d=fixture();return normalize_page(a,receipt=b,request=c,evidence=d)


def test_decimal_contract_calendar_zero_and_unknown_correction():
    c=make()
    assert c['schema']==SCHEMA and c['bars'][0]['volume']=='0'
    assert c['bars'][0]['close']=='11' and c['corrected_at'] is None
    assert c['historical_available_at'] is None
    assert analyze(c,evaluation_day='2026-10-23')['metrics']['SMA_5']['value']==11


def test_body_hash_mismatch_and_modp1_fail_closed():
    a,b,c,d=fixture();b['sha256']='0'*64
    with pytest.raises(ValueError,match='HASH'):normalize_page(a,receipt=b,request=c,evidence=d)
    a,b,c,d=fixture();c['MODP']='1'
    with pytest.raises(ValueError,match='RAW'):normalize_page(a,receipt=b,request=c,evidence=d)


def test_held_window_never_adopts_but_keeps_raw_and_stale_visible():
    c=make();c['held_ranges']=[{'from':'2026-10-21','to':'2026-10-21','reason':'UNCONFIRMED_EVENT'}]
    r=analyze(c,evaluation_day='2026-10-26')
    assert r['metrics']['SMA_5']['raw_value']==11 and r['metrics']['SMA_5']['value'] is None
    assert r['status']=='STALE' and r['data_asof']=='2026-10-23'


def test_confirmed_split_adjusts_only_before_event_and_keeps_raw_amount():
    a,b,c,d=fixture();d['splits']=[{'date':'2026-10-22','ratio':'2','evidence':'synthetic confirmed split','status':'CONFIRMED'}]
    x=normalize_page(a,receipt=b,request=c,evidence=d,basis='SPLIT_ADJUSTED')
    assert x['bars'][1]['close']=='5.5' and x['bars'][1]['volume']=='200'
    assert x['bars'][3]['close']=='11' and x['bars'][1]['amount']=='1100'
    assert x['raw_bars'][1]['close']=='11'
    assert analyze(x,evaluation_day='2026-10-23')['adopted_count']==0


def test_portfolio_uses_existing_ledger_raw_mark_and_matching_identity():
    c=make();p=[{'security_id':'SYN-SEC-1','quantity':'3','currency':'USD','quantity_basis_date':'2026-10-23'}]
    r=value_positions([c],p,evaluation_day='2026-10-23',cash='7',currency='USD')
    assert r['state']=='CALCULATED' and r['snapshot']['nav']==Decimal('40')
    assert r['orders_created']==0
    c['security_id']=None
    assert value_positions([c],p,evaluation_day='2026-10-23',cash='7',currency='USD')['snapshot'] is None


def test_same_window_comparison_does_not_claim_qgv_change():
    c=make();r=compare(c,deepcopy(c),start='2026-10-19',end='2026-10-23')
    assert r['left']['valid_close_sessions']==r['right']['valid_close_sessions']==5
    assert r['same_security_confirmed'] is True and r['QGV_coverage_change'] is None
    c2=deepcopy(c);c2['symbol']='OTHER'
    with pytest.raises(ValueError,match='COMPARISON'):compare(c,c2,start='2026-10-19',end='2026-10-23')


def test_failed_update_preserves_last_success_and_revision_is_explicit():
    c=make();r=merge_update(c,None,evaluation_day='2026-10-26',failure='SOURCE_FAILED')
    assert r['data']['bars']==c['bars'] and r['status']=='STALE' and r['failure']=='SOURCE_FAILED'
    nxt=deepcopy(c);nxt['bars'][-1]['close']='10';nxt['raw_bars'][-1]['close']='10'
    nxt['collected_at']='2026-10-25T04:00:00Z'
    r=merge_update(c,nxt,evaluation_day='2026-10-26')
    assert r['revised_dates']==['2026-10-23'] and r['data']['bars'][-1]['close']=='10'


def test_private_qgv_uses_public_calculator_without_new_quote_rules(monkeypatch):
    from investment_system.research.private_layer_qgv import compute_private_qgv
    from investment_system.qgv import qgv_official as common
    from investment_system.qgv import v2_factors
    from investment_system.universe import sec_qgv2
    from investment_system.universe.sec_universe_shares import universe_codes
    from pathlib import Path
    payload=json.loads((Path(__file__).parents[1]/'fixtures/sec_qgv2_vectors_v1.json').read_text())['base']
    payload['records']={c:payload['records'].get(c) or sec_qgv2.empty_record() for c in universe_codes()}
    before=deepcopy(payload)
    result=compute_private_qgv(payload,{},price_basis_date='2026-10-13',calculated_at='2026-10-13T22:40:00Z')
    assert result['coverage']['codes']==504 and result['coverage']['V']==0
    from datetime import datetime
    expected=common.score(common.prepare(payload,datetime.fromisoformat('2026-10-13T22:40:00+00:00')), {})
    assert result['rows']=={k:common.projection(v) for k,v in expected.items()}
    assert payload==before and result['official_publication_replaced'] is False
    bad=deepcopy(payload);bad['calc_version']='old'
    with pytest.raises(ValueError,match='VERSION'):compute_private_qgv(bad,{},price_basis_date='2026-10-13',calculated_at='2026-10-13T22:40:00Z')


def test_unknown_source_scope_is_metadata_not_a_different_formula_or_gate():
    c=make();a=analyze(c,evaluation_day='2026-10-23')
    c['price_scope_status']='UNCONFIRMED'
    b=analyze(c,evaluation_day='2026-10-23')
    assert a['metrics']==b['metrics']


def test_invalid_ohlc_loaded_contract_is_rejected():
    c=make();c['raw_bars'][0]['low']='100'
    with pytest.raises(ValueError,match='OHLC'):analyze(c,evaluation_day='2026-10-23')


def test_missing_and_zero_volume_are_distinct_and_off_calendar_is_not_a_bar():
    a,b,c,d=fixture();obj=json.loads(a);obj['output2'][1]['tvol']=''
    obj['output2'].append({**obj['output2'][0],'xymd':'20261018'})
    a=json.dumps(obj).encode();b.update(sha256=hashlib.sha256(a).hexdigest(),bytes=len(a))
    x=normalize_page(a,receipt=b,request=c,evidence=d)
    assert x['bars'][0]['volume']=='0' and x['bars'][1]['volume'] is None
    assert len(x['bars'])==5 and x['rejected_rows']==[{'date':'2026-10-18','reason':'REFERENCE_CALENDAR_CLOSED'}]


def test_private_qgv_rejects_unconfirmed_source_identity_before_supply():
    from investment_system.research.private_layer_qgv import compute_private_qgv
    from investment_system.universe import sec_qgv2
    from investment_system.universe.sec_universe_shares import universe_codes
    from pathlib import Path
    payload=json.loads((Path(__file__).parents[1]/'fixtures/sec_qgv2_vectors_v1.json').read_text())['base']
    payload['records']={c:payload['records'].get(c) or sec_qgv2.empty_record() for c in universe_codes()}
    c=make();c['symbol']='AAPL';c['identity']['identity_status']='UNKNOWN'
    r=compute_private_qgv(payload,{'NASDAQ:AAPL':c},price_basis_date='2026-10-23',calculated_at='2026-10-24T10:00:00Z')
    assert r['price_rows_supplied']==0
    assert r['price_status']['NASDAQ:AAPL']=='SOURCE_SECURITY_UNCONFIRMED'


def test_intraday_capture_cannot_be_labeled_daily_complete():
    a,b,c,d=fixture();b['fetched_at']='2026-10-23T15:00:00Z'
    with pytest.raises(ValueError,match='INCOMPLETE_SESSION'):normalize_page(a,receipt=b,request=c,evidence=d)


def test_provider_split_evidence_preserves_common_share_count_gate():
    from investment_system.research.private_layer_qgv import compute_private_qgv
    from investment_system.universe import sec_qgv2
    from investment_system.universe.sec_universe_shares import universe_codes
    from pathlib import Path
    payload=json.loads((Path(__file__).parents[1]/'fixtures/sec_qgv2_vectors_v1.json').read_text())['base']
    payload['records']={c:payload['records'].get(c) or sec_qgv2.empty_record() for c in universe_codes()}
    code='NASDAQ:ABNB';payload['records'][code]['v_inputs_v2']['diluted_shares']['period_end']='2026-06-30'
    c=make();c['symbol']='ABNB';c['splits']=[{'date':'2026-10-22','ratio':'2','evidence':'synthetic confirmed split','status':'CONFIRMED'}]
    r=compute_private_qgv(payload,{code:c},price_basis_date='2026-10-23',calculated_at='2026-10-24T10:00:00Z')
    assert r['price_rows_supplied']==0 and r['price_status'][code]=='SPLIT_AFTER_SHARE_COUNT'


def test_rejected_refresh_retains_original_row_provenance_and_reports_failure():
    c=make();a,b,q,e=fixture();d=json.loads(a);d['output2'][-1]['clos']='invalid'
    a=json.dumps(d).encode();b.update(sha256=hashlib.sha256(a).hexdigest(),bytes=len(a),fetched_at='2026-10-25T04:00:00Z')
    incoming=normalize_page(a,receipt=b,request=q,evidence=e)
    r=merge_update(c,incoming,evaluation_day='2026-10-23')
    assert r['update_state']=='PARTIAL' and r['failure']=='REJECTED_INCOMING_ROWS'
    assert r['data']['raw_bars'][-1]['source_sha256']==c['source_sha256']
    assert r['data']['raw_bars'][-1]['collected_at']==c['collected_at']
    assert analyze(r['data'],evaluation_day='2026-10-23')['status']=='STALE'


def test_later_capture_without_value_change_is_not_a_revision():
    c=make();a,b,q,e=fixture();b['fetched_at']='2026-10-25T04:00:00Z'
    r=merge_update(c,normalize_page(a,receipt=b,request=q,evidence=e),evaluation_day='2026-10-23')
    assert r['revised_dates']==[] and r['update_state']=='UPDATED'


def test_omitted_requested_last_session_is_not_a_successful_update():
    c=make();a,b,q,e=fixture();d=json.loads(a);d['output2'].pop()
    a=json.dumps(d).encode();b.update(sha256=hashlib.sha256(a).hexdigest(),bytes=len(a),fetched_at='2026-10-25T04:00:00Z')
    r=merge_update(c,normalize_page(a,receipt=b,request=q,evidence=e),evaluation_day='2026-10-23')
    assert r['status']=='STALE' and r['failure']=='REQUESTED_SESSION_MISSING'
    assert r['data']['last_success_at']==c['collected_at']


def test_nonempty_private_quote_matches_the_common_public_calculation_path():
    from investment_system.research.private_layer_qgv import compute_private_qgv
    from investment_system.qgv import qgv_official as common
    from investment_system.universe import sec_qgv2
    from investment_system.universe.sec_universe_shares import universe_codes
    from pathlib import Path
    from datetime import datetime
    from types import SimpleNamespace
    payload=json.loads((Path(__file__).parents[1]/'fixtures/sec_qgv2_vectors_v1.json').read_text())['base']
    payload['records']={c:payload['records'].get(c) or sec_qgv2.empty_record() for c in universe_codes()}
    c=make();c['symbol']='AAPL';now='2026-10-24T10:00:00Z';day='2026-10-23'
    actual=compute_private_qgv(payload,{'NASDAQ:AAPL':c},price_basis_date=day,calculated_at=now)
    ctx=common.prepare(payload,datetime.fromisoformat(now.replace('Z','+00:00')))
    quotes={key:{'price':11.0,'currency':'USD'} for key,code in ctx['keys'].items() if code=='NASDAQ:AAPL'}
    d=SimpleNamespace(day=day,quotes=quotes,status={k:'SUPPLIED' for k in quotes})
    statuses=common.price_status(ctx,d,{})
    qs,_=common.engine_quotes(ctx,d,statuses,{})
    expected=common.score(ctx,qs)
    assert actual['price_rows_supplied']>=1
    assert actual['rows']=={k:common.projection(v) for k,v in expected.items()}


def test_cli_writes_private_result_without_price_or_exception_output(tmp_path):
    import subprocess,sys,os
    from pathlib import Path
    tool=Path(__file__).parents[2]/'tools/kis_retained_calculate.py'
    job=tmp_path/'job.json';out=tmp_path/'result.json'
    job.write_text(json.dumps({'mode':'analyze','arguments':{'c':make(),'evaluation_day':'2026-10-23'}}))
    r=subprocess.run([sys.executable,str(tool),'--job',str(job),'--output',str(out)],capture_output=True,text=True)
    assert r.returncode==0 and r.stdout=='OFFLINE_PRIVATE_JOB_WRITTEN\n' and r.stderr==''
    assert os.stat(out).st_mode&0o777==0o600
    assert json.loads(out.read_text())['metrics']['SMA_5']['value']==11
    original=out.read_bytes()
    r=subprocess.run([sys.executable,str(tool),'--job',str(job),'--output',str(out)],capture_output=True,text=True)
    assert r.returncode==1 and r.stdout=='' and r.stderr=='OFFLINE_PRIVATE_JOB_FAILED\n'
    assert out.read_bytes()==original
