import json
from datetime import datetime, timezone
from dataclasses import FrozenInstanceError
import pytest
from investment_system.providers.sec_universe_collection import (
    universe_registry, daily_partition, UniverseSecClient,
)
from investment_system.providers.sec_collection import SecResponse, SecCollectionError


def body(rows):
    return json.dumps({'fields':['cik','name','ticker','exchange'],'data':rows}).encode()


def registry():
    return universe_registry(body([[1,'Synthetic','GOOG','Nasdaq'],[1,'Synthetic','GOOGL','Nasdaq'],[2,'Synthetic','BRK-B','NYSE']]))


def test_bound_issuer_grouping_and_dot_class_alias():
    r=registry();assert len(r.issuers)==2
    assert r.issuers[0].codes==('NASDAQ:GOOG','NASDAQ:GOOGL')
    assert r.issuers[1].codes==('NYSE:BRK.B',)
    assert r.code_count==3 and r.unresolved_code_count==501
    assert len(r.source_sha256)==64
    with pytest.raises(FrozenInstanceError):r.issuers=()


def test_conflicting_cik_identity_is_unresolved_not_guessed():
    r=universe_registry(body([[1,'Synthetic','GOOG','Nasdaq'],[2,'Synthetic','GOOG','Nasdaq'],[3,'Synthetic','GOOG','NYSE']]))
    assert not r.issuers and r.unresolved_code_count==504


@pytest.mark.parametrize('row',[[True,'x','GOOG','Nasdaq'],[0,'x','GOOG','Nasdaq'],[1,'x','GOOG','Unknown'],['1','x','GOOG','Nasdaq'],[1,'x','GOOG'],[1,'x','UNKNOWN','Nasdaq']])
def test_nonbinding_rows_never_expand_approved_roster(row):
    assert not universe_registry(body([row])).issuers


@pytest.mark.parametrize('value',[b'{}',b'{"fields":[],"data":[]}',b'{"fields":[],"fields":[],"data":[]}',b'{"x":NaN}'])
def test_bad_envelope_has_fixed_error(value):
    with pytest.raises(SecCollectionError,match='SEC_UNIVERSE_INPUT_INVALID'):universe_registry(value)


def test_daily_shards_disjoint_exhaustive_deterministic():
    r=registry();parts=[daily_partition(r,shard_count=7,shard_index=i) for i in range(7)]
    assert sorted(x.cik for p in parts for x in p)==[x.cik for x in r.issuers]
    assert parts==[daily_partition(r,shard_count=7,shard_index=i) for i in range(7)]


@pytest.mark.parametrize('count,index',[(0,0),(True,0),(367,0),(2,-1),(2,2),(2,True)])
def test_invalid_schedule(count,index):
    with pytest.raises(SecCollectionError,match='SEC_UNIVERSE_CONFIG_INVALID'):daily_partition(registry(),shard_count=count,shard_index=index)


def test_scope_and_shared_pacing_with_company_isolation():
    r=registry();elapsed=[0.];calls=[]
    def sleep(t):elapsed[0]+=t
    def transport(url,**kwargs):
        calls.append((url,elapsed[0]));cik=url.split('CIK')[-1].split('.')[0]
        if cik=='0000000002':return SecResponse(403,b'',final_url=url)
        return SecResponse(200,json.dumps({'cik':int(cik)}).encode(),final_url=url)
    c=UniverseSecClient('Synthetic collector contact@example.com',registry=r,transport=transport,sleep=sleep,monotonic=lambda:elapsed[0],now=lambda:datetime(2026,1,1,tzinfo=timezone.utc))
    with pytest.raises(SecCollectionError,match='SEC_ISSUER_NOT_ALLOWED'):c.collect_universe('0000000003')
    assert not calls
    facts,sub,_=c.collect_universe('0000000001');assert facts==sub
    with pytest.raises(SecCollectionError,match='SEC_HTTP_403'):c.collect_universe('0000000002')
    assert [t for _,t in calls]==pytest.approx([0,.2,.4])
    assert len(calls)==3


def test_partial_batch_preserves_good_issuer_and_reports_fixed_failures():
    from investment_system.providers.sec_universe_collection import collect_partition
    c=UniverseSecClient('Synthetic collector contact@example.com',registry=registry())
    def collect(cik):
        if cik.endswith('2'):raise SecCollectionError('PRIVATE_SENTINEL')
        return b'facts',b'sub',datetime(2026,1,1,tzinfo=timezone.utc)
    c.collect_universe=collect;saved=[]
    r=collect_partition(c,registry().issuers,on_success=lambda *x:saved.append(x))
    assert r.collected==r.failed==1 and not r.all_failed
    assert r.failures==((2,'SEC_TRANSPORT_FAILED'),) and len(saved)==1


def test_sink_error_and_all_failed_are_fixed_and_do_not_stop_next_company():
    from investment_system.providers.sec_universe_collection import collect_partition
    c=UniverseSecClient('Synthetic collector contact@example.com',registry=registry())
    c.collect_universe=lambda cik:(b'f',b's',datetime(2026,1,1,tzinfo=timezone.utc))
    def sink(*x):raise OSError('PRIVATE_SENTINEL')
    r=collect_partition(c,registry().issuers,on_success=sink)
    assert r.collected==0 and r.failed==2 and r.all_failed
    assert r.failures==((1,'SEC_OUTPUT_FAILED'),(2,'SEC_OUTPUT_FAILED'))


@pytest.mark.parametrize('code',['SEC_TRANSPORT_RETRIES_EXHAUSTED','SEC_RETRY_AFTER_EXCEEDS_BUDGET'])
def test_retry_diagnostics_retained(code):
    from investment_system.providers.sec_universe_collection import collect_partition
    c=UniverseSecClient('Synthetic collector contact@example.com',registry=registry())
    def fail(_):raise SecCollectionError(code)
    c.collect_universe=fail
    assert collect_partition(c,registry().issuers,on_success=lambda *x:None).failures==((1,code),(2,code))


@pytest.mark.parametrize('args',[['--shard-count','PRIVATE_CANARY'],['--PRIVATE_CANARY']])
def test_cli_argparse_never_echoes_input(args):
    import importlib.util
    from pathlib import Path
    import contextlib,io
    path=Path(__file__).parents[1]/'tools/sec_universe_collect.py'
    s=importlib.util.spec_from_file_location('cli',path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
    out=io.StringIO();err=io.StringIO()
    with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err),pytest.raises(SystemExit):m.main(args)
    assert 'PRIVATE_CANARY' not in out.getvalue()+err.getvalue()
    assert out.getvalue()=='SEC_UNIVERSE SEC_UNIVERSE_CONFIG_INVALID\n'


def test_registry_requires_approved_code_binding_factory():
    from investment_system.providers.sec_universe_collection import UniverseRegistry,UniverseIssuer
    forged=UniverseRegistry((UniverseIssuer('0000000003',('NYSE:UNKNOWN',)),),'0'*64,503)
    with pytest.raises(SecCollectionError,match='SEC_UNIVERSE_CONFIG_INVALID'):UniverseSecClient('Synthetic collector contact@example.com',registry=forged)
    with pytest.raises(SecCollectionError,match='SEC_UNIVERSE_CONFIG_INVALID'):daily_partition(forged,shard_count=1,shard_index=0)
