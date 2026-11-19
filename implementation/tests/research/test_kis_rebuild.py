"""Offline rebuild: synthetic data only, unchanged canonical engines."""
from copy import deepcopy
import hashlib
import importlib
import json
from pathlib import Path
import subprocess
import sys
import os

import pytest

from investment_system.research._private_artifacts import canonical_bytes, digest, json_bytes
from investment_system.research.kis_price_bridge import normalize_page
from investment_system.research.monthly_price_store import ingest
from investment_system.universe.sec_universe_shares import universe_codes
from investment_system.universe.sec_qgv2 import empty_record


def sha(b): return hashlib.sha256(b).hexdigest()
def api(): return importlib.import_module('investment_system.research.kis_rebuild')


def inputs(root):
    root.mkdir(exist_ok=True)
    request=dict(SYMB='SYN',EXCD='NAS',MODP='0',GUBN='0',BYMD='20261023')
    body=json_bytes(dict(rt_cd='0',output1=dict(rsym='DNASSYN'),output2=[
        dict(xymd=d,open='10',high='12',low='9',clos='11',tvol='100',tamt='1100')
        for d in ['20261019','20261020','20261021','20261022','20261023']]))
    receipt=dict(sha256=sha(body),bytes=len(body),http_status=200,fetched_at='2026-10-24T04:00:00Z',request=request)
    c=normalize_page(body,receipt=receipt,request=request,evidence=dict(currency='USD',currency_reference='SYNTHETIC_NOT_A_COMPANY'))
    cb=json_bytes(c);rb=json_bytes(receipt)
    stored=ingest(root/'store',contract_bytes=cb,body=body,receipt_bytes=rb,
                  expected_contract_sha256=sha(cb),expected_receipt_sha256=sha(rb))
    code=universe_codes()[0]
    index=dict(files=[dict(code=code,symbol='SYN',series_id=stored['series_id'],
                           store_manifest_sha256=stored['manifest_sha256'],source_contract_sha256=sha(cb))])
    base=json.loads((Path(__file__).parents[1]/'fixtures/sec_qgv2_vectors_v1.json').read_bytes())['base']
    payload=deepcopy(base);payload['records']={k:base['records'].get(k) or empty_record() for k in universe_codes()}
    links={code:dict(symb='SYN',excd='NAS')}
    for name,obj in [('series.json',index),('financial.json',payload),('symbols.json',links)]:
        (root/name).write_bytes(json_bytes(obj))
    config=dict(schema='kis-offline-rebuild/1',publication_scope='OWNER_PRIVATE_ONLY',
                evaluation_day='2026-10-23',calculated_at='2026-10-24T04:00:00Z',
                series_id_prefix='OWNER_KIS:',store='store',
                series_index=dict(path='series.json',sha256=sha((root/'series.json').read_bytes())),
                financial=dict(path='financial.json',sha256=sha((root/'financial.json').read_bytes())),
                symbols=dict(path='symbols.json',sha256=sha((root/'symbols.json').read_bytes())))
    (root/'request.json').write_bytes(json_bytes(config))
    return root/'request.json',c


def test_rebuild_matches_canonical_functions_and_is_deterministic(tmp_path):
    request,c=inputs(tmp_path/'in')
    from investment_system.research.private_kis_preprocess import calculate_and_project
    from investment_system.research.private_kis_reference import reference_files
    code=universe_codes()[0]
    expected=reference_files(calculate_and_project(c,evaluation_day='2026-10-23',
        series_id='OWNER_KIS:'+code,expected_contract_hash=digest(c)),c,'2026-10-23')
    first=dict(api().rebuild(request,expected_request_sha256=sha(request.read_bytes())))
    second=dict(api().rebuild(request,expected_request_sha256=sha(request.read_bytes())))
    assert first==second and len(first)==5
    assert all(first[k]==b for k,b in expected.items())
    q=json.loads(first['qgv/latest.json'])
    assert q['display']['validation_tier']=='UNVERIFIED_REFERENCE'
    assert all(r['total'] is None for r in q['rows'].values() if r['axes']['V']['score'] is None)


@pytest.mark.parametrize('field',['request_pin','series_pin','clock','traversal'])
def test_bad_inputs_fail_instead_of_substituting_latest(tmp_path,field):
    request,_=inputs(tmp_path/'in');config=json.loads(request.read_bytes())
    if field=='request_pin':
        with pytest.raises(ValueError):list(api().rebuild(request,expected_request_sha256='0'*64))
        return
    if field=='series_pin':
        index=json.loads((request.parent/'series.json').read_bytes());index['files'][0]['store_manifest_sha256']='0'*64
        (request.parent/'series.json').write_bytes(json_bytes(index));config['series_index']['sha256']=sha((request.parent/'series.json').read_bytes())
    if field=='clock':config['calculated_at']='2026-10-20T04:00:00Z'
    if field=='traversal':config['financial']['path']='../outside.json'
    request.write_bytes(json_bytes(config))
    with pytest.raises(ValueError):list(api().rebuild(request,expected_request_sha256=sha(request.read_bytes())))


def test_comparison_catches_missing_extra_and_different_files(tmp_path):
    m=api();files={'chart/S/SYN.json':b'{}\n','qgv/latest.json':b'{}\n'}
    expected=[dict(path=k,bytes=len(v),sha256=sha(v)) for k,v in files.items()]
    assert m.compare_files(files.items(),expected)['different']==0
    altered={'chart/S/SYN.json':b'{"a":1}\n','unexpected.json':b'{}\n'}
    result=m.compare_files(altered.items(),expected)
    assert result['different']==result['missing']==result['extra']==1


def test_writer_is_new_directory_only_and_never_replaces_old_on_failure(tmp_path):
    m=api();out=tmp_path/'output'
    def broken():
        yield 'chart/S/SYN.json',b'{}\n'
        raise ValueError('SYNTHETIC_CALC_FAILURE')
    with pytest.raises(ValueError):m.write_bundle(broken(),out)
    assert not out.exists()
    m.write_bundle(iter([('chart/S/SYN.json',b'{}\n')]),out)
    with pytest.raises(FileExistsError):m.write_bundle(iter([]),out)
    assert (out/'chart/S/SYN.json').read_bytes()==b'{}\n'


def test_cli_check_only_uses_no_site_packages_and_no_network(tmp_path):
    request,_=inputs(tmp_path/'in')
    # -S disables site packages. Any socket attempt in this subprocess fails.
    script="""import socket,sys
socket.socket.connect=lambda *a,**k:(_ for _ in ()).throw(AssertionError('NETWORK_FORBIDDEN'))
socket.socket.connect_ex=socket.socket.connect
from investment_system.research.kis_rebuild import main
sys.exit(main(sys.argv[1:]))
"""
    args=[sys.executable,'-S','-c',script,'--request',str(request),
          '--expected-request-sha256',sha(request.read_bytes()),'--check-only']
    result=subprocess.run(args,capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    counts=json.loads(result.stdout)
    assert counts['files']==5 and all(type(v) is int for v in counts.values())
    assert result.stderr==''


def test_compact_command_uses_same_rebuild_and_requires_explicit_bootstrap(tmp_path,capsys):
    request,_=inputs(tmp_path/'in');pin=sha(request.read_bytes());m=api()
    args=['--request',str(request),'--expected-request-sha256',pin,'--check-only','--layout','compact']
    assert m.main(args)==2
    assert m.main(args+['--bootstrap'])==0
    assert all(type(v) is int for v in json.loads(capsys.readouterr().out.splitlines()[-1]).values())


def test_stock_command_uses_common_pipeline_without_network_and_keeps_null_totals(tmp_path,monkeypatch):
    import socket
    monkeypatch.setattr(socket.socket,'connect',lambda *a,**kw:pytest.fail('NETWORK_FORBIDDEN'))
    request,_=inputs(tmp_path/'in');pin=sha(request.read_bytes());m=api()
    from investment_system.research.kis_stock_bundle import stock_bundle,assemble_stock
    raw=m.rebuild(request,expected_request_sha256=pin,include_indicator_series=True)
    files=stock_bundle(raw,evaluation_day='2026-10-23')
    result=assemble_stock(files.__getitem__,'SYN')
    assert len(result['rows'])==5 and all(v is None for v in result['rows'][-1][7:])
    from investment_system.research.kis_compact import unpack_row
    for path,b in files.items():
        if path.startswith('qgv/buckets/'):
            packet=json.loads(b)
            for key in packet['rows']:
                row=unpack_row(packet,key)
                if row['axes']['V']['score'] is None:assert row['total'] is None
    args=['--request',str(request),'--expected-request-sha256',pin,'--check-only','--layout','stock','--bootstrap']
    assert m.main(args)==0


def test_changed_source_index_cannot_claim_original_file_pin(tmp_path):
    request,_=inputs(tmp_path/'in');config=json.loads(request.read_bytes())
    index=json.loads((request.parent/'series.json').read_bytes())
    index['files'][0]['source_contract_sha256']='0'*64
    (request.parent/'series.json').write_bytes(json_bytes(index))
    config['series_index']['sha256']=sha((request.parent/'series.json').read_bytes())
    request.write_bytes(json_bytes(config))
    with pytest.raises(ValueError,match='RETAINED_CONTRACT_FILE_PIN'):
        list(api().rebuild(request,expected_request_sha256=sha(request.read_bytes())))


def test_determinism_across_fresh_process_hash_seeds(tmp_path):
    request,_=inputs(tmp_path/'in');pin=sha(request.read_bytes())
    code="""import hashlib,json,sys
from investment_system.research.kis_rebuild import rebuild
rows=[(p,hashlib.sha256(b).hexdigest()) for p,b in rebuild(sys.argv[1],expected_request_sha256=sys.argv[2])]
print(hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest())
"""
    results=[]
    for seed in ('1','2'):
        env=dict(os.environ,PYTHONHASHSEED=seed)
        p=subprocess.run([sys.executable,'-S','-c',code,str(request),pin],env=env,capture_output=True,text=True)
        assert p.returncode==0,p.stderr
        results.append(p.stdout)
    assert results[0]==results[1]
