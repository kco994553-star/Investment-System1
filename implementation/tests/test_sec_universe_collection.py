import json
from datetime import datetime, timezone
from dataclasses import FrozenInstanceError
import pytest
from investment_system.providers.sec_universe_collection import (
    universe_registry, daily_partition, UniverseSecClient,
)
from investment_system.providers.sec_collection import SecResponse, SecCollectionError


UA='Synthetic collector contact@example.com'


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


def test_cboe_exchange_binds_only_the_explicit_cboe_alias():
    r=universe_registry(body([[7,'Synthetic','CBOE','CBOE'],[8,'Synthetic','GOOG','CBOE'],[9,'Synthetic','XYZ','CBOE']]))
    assert [(x.cik,x.codes) for x in r.issuers]==[('0000000007',('BATS:CBOE',))]
    assert r.unresolved_code_count==503 and not r.conflicting_codes


@pytest.mark.parametrize('rows',[[[1,'x','CBOE','Nasdaq']],[[1,'x','CBOE','NYSE']],[[1,'x','CBOE','OTC']],[[1,'x','cboe','CBOE']],[[1,'x','CBOE','Cboe']]])
def test_cboe_code_is_not_bound_from_other_exchange_or_ticker_spellings(rows):
    assert not universe_registry(body(rows)).issuers


def test_cboe_alias_keeps_the_single_cik_rule():
    r=universe_registry(body([[7,'Synthetic','CBOE','CBOE'],[8,'Synthetic','CBOE','CBOE']]))
    assert not r.issuers and r.conflicting_codes==frozenset({'BATS:CBOE'}) and r.unresolved_code_count==504


# NASDAQ:PSKY -> NYSE SKYD (same issuer CIK 0002041610, listing moved 2026-10-06): one exact pair, pinned to that CIK.
PSKY_CIK=2041610
SKYD=('SK'+'YD','NY'+'SE')


def test_skyd_alias_binds_psky_only_for_the_named_cik():
    r=universe_registry(body([[PSKY_CIK,'Synthetic',*SKYD]]))
    assert [(x.cik,x.codes) for x in r.issuers]==[('0002041610',('NASDAQ:PSKY',))]
    assert r.unresolved_code_count==503 and not r.conflicting_codes


@pytest.mark.parametrize('rows',[[[7,'Synthetic',*SKYD]],[[PSKY_CIK,'x',*SKYD],[7,'x',*SKYD]],[[7,'x',*SKYD],[PSKY_CIK,'x',*SKYD]]])
def test_skyd_alias_from_another_cik_is_unresolved_not_a_conflict(rows):
    r=universe_registry(body(rows))
    assert not r.issuers and r.unresolved_code_count==504 and not r.conflicting_codes


@pytest.mark.parametrize('row',[[PSKY_CIK,'x',SKYD[0],'Nasdaq'],[PSKY_CIK,'x',SKYD[0]+'-WT',SKYD[1]],[PSKY_CIK,'x',SKYD[0].lower(),SKYD[1]],
                                [PSKY_CIK,'x',SKYD[0],'CBOE'],[PSKY_CIK,'x','PSKY',SKYD[1]],[PSKY_CIK,'x',SKYD[0],'Nyse']])
def test_skyd_alias_is_one_exact_pair(row):
    assert not universe_registry(body([row])).issuers


def test_skyd_alias_keeps_the_single_cik_rule_with_the_code_own_ticker():
    same=universe_registry(body([[PSKY_CIK,'x','PSKY','Nasdaq'],[PSKY_CIK,'x',*SKYD]]))
    assert [(x.cik,x.codes) for x in same.issuers]==[('0002041610',('NASDAQ:PSKY',))]
    other=universe_registry(body([[7,'x','PSKY','Nasdaq'],[PSKY_CIK,'x',*SKYD]]))
    assert not other.issuers and other.conflicting_codes==frozenset({'NASDAQ:PSKY'})


def _archived_sec_rows():
    from pathlib import Path
    path=Path(__file__).parents[1]/'experiments/chart-contract-v0.1/p0-classification-review-v0.3/market-identity-time/sec_tickers_exchange_original.json'
    return json.loads(path.read_text())['data']


def _legacy_binding_map(rows):
    """The registry rule before the SKYD alias (exact Nasdaq/NYSE code pair, else the CBOE pair only), independent of the module."""
    from pathlib import Path
    codes=json.loads((Path(__file__).parents[1]/'src/investment_system/universe/universe_codes_v1.json').read_text())
    lookup={(c.split(':')[0],c.split(':')[1].replace('.','-')):c for c in codes}
    bound={c:set() for c in codes}
    for cik,_,ticker,exchange in rows:
        venue={'Nasdaq':'NASDAQ','NYSE':'NYSE'}.get(exchange)
        code=lookup.get((venue,ticker)) if venue is not None else {('CBOE','CBOE'):'BATS:CBOE'}.get((exchange,ticker))
        if code is not None:bound[code].add(str(cik).zfill(10))
    return {c:next(iter(v)) for c,v in bound.items() if len(v)==1}


def _binding_map(rows):
    return {c:x.cik for x in universe_registry(body(rows)).issuers for c in x.codes}


def test_full_binding_map_on_archived_sec_file_changes_only_psky():
    rows=_archived_sec_rows()
    assert sum(1 for r in rows if r[2]==SKYD[0])==0 and any(r[0]==PSKY_CIK and r[2]=='PSKY' for r in rows)
    before=_legacy_binding_map(rows)
    assert len(before)==504 and before['BATS:CBOE']==_binding_map(rows)['BATS:CBOE']
    assert _binding_map(rows)==before   # archived file (PSKY still on Nasdaq): every code binds exactly as before
    moved=[[c,n,*SKYD] if (c==PSKY_CIK and t=='PSKY') else [c,n,t,e] for c,n,t,e in rows]
    old,new=_legacy_binding_map(moved),_binding_map(moved)
    assert 'NASDAQ:PSKY' not in old and new.pop('NASDAQ:PSKY')=='0002041610' and new==old and len(old)==503
    stranger=[r for r in rows if not (r[0]==PSKY_CIK and r[2]=='PSKY')]+[[7,'Synthetic',*SKYD]]
    assert _binding_map(stranger)==_legacy_binding_map(stranger) and 'NASDAQ:PSKY' not in _binding_map(stranger)


def test_universe_client_accepts_unpadded_string_cik_only_for_the_same_issuer():
    r=registry();seen=[]
    def transport(url,**kwargs):
        cik=url.split('CIK')[-1].split('.')[0];seen.append(url)
        value=str(int(cik)) if 'companyfacts' in url else cik
        if cik=='0000000002':value=str(int(cik)+1) if 'companyfacts' in url else cik
        return SecResponse(200,json.dumps({'cik':value}).encode(),final_url=url)
    clock=[0.]
    def sleep(t):clock[0]+=t
    c=UniverseSecClient(UA,registry=r,transport=transport,sleep=sleep,monotonic=lambda:clock[0],now=lambda:datetime(2026,1,1,tzinfo=timezone.utc))
    facts,sub,_=c.collect_universe('0000000001')
    assert json.loads(facts)['cik']=='1' and json.loads(sub)['cik']=='0000000001'
    with pytest.raises(SecCollectionError,match='SEC_CIK_MISMATCH'):c.collect_universe('0000000002')


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
    c=UniverseSecClient(UA,registry=r,transport=transport,sleep=sleep,monotonic=lambda:elapsed[0],now=lambda:datetime(2026,1,1,tzinfo=timezone.utc))
    with pytest.raises(SecCollectionError,match='SEC_ISSUER_NOT_ALLOWED'):c.collect_universe('0000000003')
    assert not calls
    facts,sub,_=c.collect_universe('0000000001');assert facts==sub
    with pytest.raises(SecCollectionError,match='SEC_HTTP_403'):c.collect_universe('0000000002')
    assert [t for _,t in calls]==pytest.approx([0,.2,.4])
    assert len(calls)==3


def test_partial_batch_preserves_good_issuer_and_reports_fixed_failures():
    from investment_system.providers.sec_universe_collection import collect_partition
    c=UniverseSecClient(UA,registry=registry())
    def collect(cik):
        if cik.endswith('2'):raise SecCollectionError('PRIVATE_SENTINEL')
        return b'facts',b'sub',datetime(2026,1,1,tzinfo=timezone.utc)
    c.collect_universe=collect;saved=[]
    r=collect_partition(c,registry().issuers,on_success=lambda *x:saved.append(x))
    assert r.collected==r.failed==1 and not r.all_failed
    assert r.failures==((2,'SEC_TRANSPORT_FAILED'),) and len(saved)==1


def test_sink_error_and_all_failed_are_fixed_and_do_not_stop_next_company():
    from investment_system.providers.sec_universe_collection import collect_partition
    c=UniverseSecClient(UA,registry=registry())
    c.collect_universe=lambda cik:(b'f',b's',datetime(2026,1,1,tzinfo=timezone.utc))
    def sink(*x):raise OSError('PRIVATE_SENTINEL')
    r=collect_partition(c,registry().issuers,on_success=sink)
    assert r.collected==0 and r.failed==2 and r.all_failed
    assert r.failures==((1,'SEC_OUTPUT_FAILED'),(2,'SEC_OUTPUT_FAILED'))


@pytest.mark.parametrize('code',['SEC_TRANSPORT_RETRIES_EXHAUSTED','SEC_RETRY_AFTER_EXCEEDS_BUDGET'])
def test_retry_diagnostics_retained(code):
    from investment_system.providers.sec_universe_collection import collect_partition
    c=UniverseSecClient(UA,registry=registry())
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
    with pytest.raises(SecCollectionError,match='SEC_UNIVERSE_CONFIG_INVALID'):UniverseSecClient(UA,registry=forged)
    with pytest.raises(SecCollectionError,match='SEC_UNIVERSE_CONFIG_INVALID'):daily_partition(forged,shard_count=1,shard_index=0)
