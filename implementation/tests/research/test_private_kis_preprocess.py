"""Synthetic saved-artifact projection; no data source calls or private inputs."""
from copy import deepcopy
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import runpy

import pytest

from investment_system.research._private_artifacts import digest,MAX_BYTES
from investment_system.research.kis_price_bridge import normalize_page
from investment_system.research.technical_handoff import prepare_technical

ROOT=Path(__file__).resolve().parents[2]


def api():
    name='investment_system.research.private_kis_preprocess'
    assert importlib.util.find_spec(name) is not None,'SAVED_PRIVATE_PROJECTION_NOT_IMPLEMENTED'
    return importlib.import_module(name)


def case():
    c=runpy.run_path(str(ROOT/'tools/kis_contract_fixture.py'))['fixtures']()['synthetic-raw.json']
    h=prepare_technical(c,evaluation_day='2026-10-23',series_id='SYNTHETIC:SERIES',include_split_assessment=True)
    return c,h


def project(c,h):
    return api().project_technical(c,h,expected_contract_hash=digest(c),expected_handoff_hash=digest(h))


def repin_inner(h):
    h['result_sha256']=digest({k:v for k,v in h.items() if k!='result_sha256'})


def test_saved_projection_keeps_exact_values_and_never_calls_calculation(monkeypatch):
    c,h=case();before=deepcopy((c,h));m=api()
    def forbidden(*args,**kwargs):raise AssertionError('SAVED_PROJECTION_RECALCULATED')
    monkeypatch.setattr(m,'prepare_technical',forbidden)
    files=project(c,h)
    assert (c,h)==before
    assert set(files)=={'chart/S/SYN.json','technical/S/SYN.json','measures/S/SYN.json','manifests/S/SYN.json'}
    chart=json.loads(files['chart/S/SYN.json'])
    assert chart==c and chart['publication_scope']=='OWNER_PRIVATE_ONLY'
    assert json.loads(files['technical/S/SYN.json'])==h['components']
    assert json.loads(files['measures/S/SYN.json'])==h['measures']
    manifest=json.loads(files['manifests/S/SYN.json'])
    assert manifest['qgv']==dict(state='NOT_PRODUCED_555_DEPENDENCY',retain_previous=True,files_written=[])
    assert manifest['source_contract_hash']==digest(c) and manifest['source_handoff_hash']==digest(h)
    assert manifest['generated_at'] is None and manifest['generated_at_reason']=='NOT_RECORDED'
    assert manifest['projection_recalculated_metrics'] is False
    for item in manifest['files']:
        raw=files[item['path']]
        assert len(raw)==item['bytes']<=MAX_BYTES
        assert hashlib.sha256(raw).hexdigest()==item['sha256']
    assert 'qgv/latest.json' not in files


@pytest.mark.parametrize('pin',['contract','handoff'])
def test_saved_projection_requires_independently_supplied_pins(pin):
    c,h=case();kw=dict(expected_contract_hash=digest(c),expected_handoff_hash=digest(h))
    kw['expected_'+pin+'_hash']='0'*64
    with pytest.raises(ValueError,match=pin.upper()+'_HASH_MISMATCH'):
        api().project_technical(c,h,**kw)


def test_saved_projection_checks_inner_hash_even_if_outer_pin_matches():
    c,h=case();h['components']['raw_count']=999
    with pytest.raises(ValueError,match='HANDOFF_RESULT_HASH_MISMATCH'):project(c,h)


@pytest.mark.parametrize('change,reason',[
    ('query','HANDOFF_PROVENANCE_MISMATCH'),('contract_pin','HANDOFF_PROVENANCE_MISMATCH'),
    ('symbol','HANDOFF_SYMBOL_MISMATCH'),('day','HANDOFF_EVALUATION_MISMATCH'),
    ('scope','PRIVATE_HANDOFF_REQUIRED'),('chart_future','FUTURE_CHART_ROW'),
    ('basis','HANDOFF_CHART_BASIS_MISMATCH'),
])
def test_rehashed_saved_corruption_is_rejected_by_context_not_only_internal_agreement(change,reason):
    c,h=case()
    if change=='query':h['provenance']['source_query']['SYMB']='OTHER'
    elif change=='contract_pin':h['provenance']['contract_hash']='1'*64
    elif change=='symbol':h['components']['symbol']='OTHER'
    elif change=='day':h['measures']['evaluation_day']='2026-10-22'
    elif change=='scope':h['publication_scope']='PUBLIC'
    elif change=='chart_future':h['chart']['bars'].append(dict(h['chart']['bars'][-1],date='2026-10-26'))
    elif change=='basis':h['chart']['basis']='SPLIT_ADJUSTED'
    repin_inner(h)
    with pytest.raises(ValueError,match=reason):project(c,h)


def test_future_archive_event_is_not_applied_to_earlier_chart_projection():
    days=['2026-10-22','2026-10-23','2026-10-26']
    body=json.dumps(dict(rt_cd='0',output1=dict(rsym='DNASSYN'),output2=[dict(
        xymd=d.replace('-',''),open='10',high='12',low='9',clos='11',tvol='100',tamt='1100') for d in days])).encode()
    receipt=dict(sha256=hashlib.sha256(body).hexdigest(),bytes=len(body),http_status=200,fetched_at='2026-10-27T04:00:00Z')
    request=dict(SYMB='SYN',EXCD='NAS',MODP='0',GUBN='0',BYMD='20261026')
    evidence=dict(currency='USD',currency_reference='SYNTHETIC',identity_status='CONFIRMED',
        identity_reference='SYNTHETIC',identity_start=days[0],identity_end=days[-1],
        security_id='SYNTHETIC_SECURITY',confirmed_ranges=[dict(**{'from':days[0],'to':days[-1]},evidence='SYNTHETIC')],
        held_ranges=[],splits=[dict(date=days[-1],ratio='2',status='CONFIRMED',evidence='SYNTHETIC_SPLIT')])
    c=normalize_page(body,receipt=receipt,request=request,evidence=evidence,basis='SPLIT_ADJUSTED')
    h=prepare_technical(c,evaluation_day=days[1],series_id='SYNTHETIC:SERIES',include_split_assessment=True)
    files=project(c,h);out=json.loads(files['chart/S/SYN.json'])
    assert len(out['bars'])==2 and out['bars'][0]['close']=='11'
    assert c['bars'][0]['close']=='5.5' and len(c['bars'])==3
    assert out['splits']==[] and out['price_basis_date']=='2026-10-23'
    assert out['collected_at']==c['collected_at'] and out['source_query']==c['source_query']


@pytest.mark.parametrize('change,reason',[
    ('modp','RAW_DAILY_SOURCE_REQUIRED'),('split','SPLIT_RATIO_CONFLICT'),
    ('duplicate_adjustment','ADJUSTED_ROWS_DO_NOT_MATCH_CONFIRMED_SPLITS')])
def test_saved_source_adjustment_and_event_conflicts_remain_blocked(change,reason):
    fixtures=runpy.run_path(str(ROOT/'tools/kis_contract_fixture.py'))['fixtures']()
    c=fixtures['synthetic-split-held.json'];c['held_ranges']=[]
    h=prepare_technical(c,evaluation_day='2026-10-23',series_id='SYNTHETIC:SERIES',include_split_assessment=True)
    if change=='modp':c['source_query']['MODP']='1'
    elif change=='split':c['splits'][0]['source_record']=dict(ratio='3')
    else:c['bars'][0].update(open='2.5',high='3',low='2.25',close='2.75')
    with pytest.raises(ValueError,match=reason):project(c,h)


def test_slash_filename_encoding_is_not_a_worker_route_alias():
    c,h=case();c['symbol']='SYN/A';c['source_query']['SYMB']='SYN/A'
    h=prepare_technical(c,evaluation_day='2026-10-23',series_id='SYNTHETIC:SERIES',include_split_assessment=True)
    files=project(c,h);manifest=json.loads(files['manifests/S/SYN_A.json'])
    assert manifest['symbol']=='SYN/A' and manifest['storage_symbol']=='SYN_A'
    assert manifest['delivery_state']=='BLOCKED_ROUTE_MAPPING_REQUIRED'
    assert json.loads(files['chart/S/SYN_A.json'])['symbol']=='SYN/A'


def test_fresh_calculation_is_explicit_and_uses_existing_split_aware_handoff(monkeypatch):
    c,h=case();m=api();calls=[]
    def existing(*args,**kw):calls.append(kw);return h
    monkeypatch.setattr(m,'prepare_technical',existing)
    files=m.calculate_and_project(c,evaluation_day='2026-10-23',series_id='SYNTHETIC:SERIES',expected_contract_hash=digest(c))
    assert calls==[dict(evaluation_day='2026-10-23',series_id='SYNTHETIC:SERIES',include_split_assessment=True)]
    assert json.loads(files['technical/S/SYN.json'])==h['components']


def test_saved_projection_rejects_oversized_output_before_any_write(monkeypatch):
    c,h=case();monkeypatch.setattr(api(),'MAX_BYTES',100)
    with pytest.raises(ValueError,match='PRIVATE_ARTIFACT_TOO_LARGE'):project(c,h)


def test_cli_preserves_outside_git_guard_and_exclusive_output(tmp_path,monkeypatch,capsys):
    tool=ROOT/'tools/kis_preprocess_private.py'
    assert tool.exists(),'SAVED_PRIVATE_CLI_NOT_IMPLEMENTED'
    module=runpy.run_path(str(tool));c,h=case()
    src=tmp_path/'contract.json';src.write_text(json.dumps(c));saved=tmp_path/'handoff.json';saved.write_text(json.dumps(h))
    out=tmp_path/'new-private'
    args=['--contract',str(src),'--handoff',str(saved),'--expected-contract-hash',digest(c),
        '--expected-handoff-hash',digest(h),'--output-dir',str(out)]
    (tmp_path/'.git').mkdir()
    with pytest.raises(SystemExit):module['main'](args)
    assert not out.exists()
    capsys.readouterr()


def test_cli_writer_keeps_previous_directory_and_price_values_out_of_logs(tmp_path,capsys):
    tool=ROOT/'tools/kis_preprocess_private.py';assert tool.exists(),'SAVED_PRIVATE_CLI_NOT_IMPLEMENTED'
    module=runpy.run_path(str(tool));out=tmp_path/'existing';out.mkdir();(out/'keep.txt').write_text('unchanged')
    with pytest.raises(FileExistsError):module['write_new_directory'](out,{'chart/S/SYN.json':b'{}\n'})
    assert (out/'keep.txt').read_text()=='unchanged'
    assert capsys.readouterr().out==''


@pytest.mark.parametrize('reason,expected',[
    ('HANDOFF_HASH_MISMATCH','OFFLINE_PRIVATE_PROJECTION_FAILED HANDOFF_HASH_MISMATCH\n'),
    ('synthetic price=999999','OFFLINE_PRIVATE_PROJECTION_FAILED INVALID_PRIVATE_INPUT\n')])
def test_cli_emits_only_safe_fixed_error_codes(tmp_path,monkeypatch,capsys,reason,expected):
    tool=ROOT/'tools/kis_preprocess_private.py';assert tool.exists()
    module=runpy.run_path(str(tool));main=module['main']
    # Simulate an approved outside-Git location without changing the production
    # guard, to exercise only the exception-to-diagnostic boundary.
    monkeypatch.setitem(main.__globals__,'_inside_git',lambda path:False)
    def failed(*args,**kw):raise ValueError(reason)
    monkeypatch.setitem(main.__globals__,'project_technical',failed)
    contract=tmp_path/'contract.json';contract.write_text('{}')
    handoff=tmp_path/'handoff.json';handoff.write_text('{}')
    out=tmp_path/'result'
    assert main(['--contract',str(contract),'--handoff',str(handoff),
        '--expected-contract-hash','0'*64,'--expected-handoff-hash','0'*64,'--output-dir',str(out)])==1
    logs=capsys.readouterr()
    assert logs.out=='' and logs.err==expected and not out.exists()


def test_cli_writer_private_bytes_permissions_and_manifest_last(tmp_path,monkeypatch,capsys):
    import os
    tool=ROOT/'tools/kis_preprocess_private.py';module=runpy.run_path(str(tool))
    writer=module['write_new_directory']
    # The real sandbox's roots are Git ancestors. Isolate the writer here while
    # the separate guard test proves that production CLI still rejects them.
    monkeypatch.setitem(writer.__globals__,'_inside_git',lambda path:False)
    opened=[];real_open=os.open
    def observe(path,flags,mode):opened.append(str(path));return real_open(path,flags,mode)
    monkeypatch.setattr(os,'open',observe)
    c,h=case();files=project(c,h);out=tmp_path/'approved-private-synthetic'
    writer(out,files)
    assert opened[-1].endswith('/manifests/S/SYN.json') and len(opened)==4
    assert out.stat().st_mode&0o777==0o700
    for name,raw in files.items():
        target=out/name
        assert target.read_bytes()==raw and target.stat().st_mode&0o777==0o600
    with pytest.raises(FileExistsError):writer(out,files)
    assert all((out/name).read_bytes()==raw for name,raw in files.items())
    assert capsys.readouterr().out==''
