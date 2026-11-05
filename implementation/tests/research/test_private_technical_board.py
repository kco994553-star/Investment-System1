import hashlib
import json
from copy import deepcopy
from datetime import date
from decimal import Decimal, localcontext
from pathlib import Path
import subprocess
import sys

import pytest

from investment_system.research.kis_price_bridge import normalize_page, retained_baseline
from investment_system.research.private_technical_board import measure_contract, build_contract_board, board_reader_payload
from investment_system.research.exp_deciles.technical_measures import sessions


def contract(index=1, short=False):
    days=sessions(date(2016,1,4),date(2017,1,6))
    if short:days=days[-100:]
    body=json.dumps({'rt_cd':'0','output1':{'rsym':'DNASSYN'},'output2':[
        dict(xymd=d.replace('-',''),open=str(100+i*index),high=str(102+i*index),
             low=str(99+i*index),clos=str(101+i*index),tvol='100',tamt='999999') for i,d in enumerate(days)]}).encode()
    evidence=dict(currency='USD',currency_reference='SYNTHETIC',identity_status='CONFIRMED',
                  identity_reference='SYNTHETIC',identity_start=days[0],identity_end=days[-1],
                  security_id=f'SYNTHETIC:SEC:{index}',issuer_id=f'SYNTHETIC:ISSUER:{index}',
                  held_ranges=[],splits=[])
    evidence['confirmed_ranges']=[{'from':days[0],'to':days[-1],'evidence':'SYNTHETIC'}]
    c=normalize_page(body,receipt=dict(sha256=hashlib.sha256(body).hexdigest(),bytes=len(body),
                                          fetched_at='2017-01-07T05:00:00Z',http_status=200),
                          request=dict(SYMB='SYN',EXCD='NAS',MODP='0',GUBN='0',BYMD='20170106'),evidence=evidence)
    c['fixture_kind']='SYNTHETIC_NOT_A_COMPANY'
    return c


def board_input(n=20):
    series=[dict(series_id=f'REQUEST:{i}',contract=contract(i)) for i in range(1,n+1)]
    links=[dict(series_id=s['series_id'],security_id=s['contract']['security_id'],identifier_type='SYNTHETIC_FIXED_SECURITY_ID',
                valid_from='2016-01-04',valid_to='2017-01-06',reference='AUTHOR_CREATED_TEST_RECORD') for s in series]
    group=dict(group_id='SYNTHETIC_DATED_GROUP',signal_day='2017-01-06',membership_status='CONFIRMED',
               member_security_ids=[x['security_id'] for x in links],membership_source='AUTHOR_CREATED_COMPLETE_SNAPSHOT')
    return series,links,group


def test_single_company_uses_shared_price_windows_but_never_synthesizes_vwap():
    c=contract();r=measure_contract(c,evaluation_day='2017-01-06',series_id='REQUEST:1')
    assert r['raw_count']==r['adopted_count']==4
    prices={x['date']:Decimal(x['close']) for x in c['raw_bars']}
    anchor='2016-10-06'
    with localcontext() as ctx:
        ctx.prec=50
        assert Decimal(r['metrics']['momentum_3m']['value'])==(prices['2017-01-06']-prices[anchor])/prices[anchor]*100
    volume=r['metrics']['dollar_volume_6m']
    assert volume['raw_value'] is None and volume['value'] is None
    assert volume['close_volume_proxy']['mean_complete'] is not None
    assert 'TRADE_SCOPE_UNCONFIRMED' in volume['null_reasons']
    assert r['security_id'] is None and r['qgv_join_key'] is None and r['rank_count']==0
    assert r['historical_available_at'] is None


def test_hundred_retained_bars_compute_three_months_without_inventing_long_history():
    r=measure_contract(contract(short=True),evaluation_day='2017-01-06',series_id='REQUEST:SHORT')
    assert r['raw_count']==r['adopted_count']==1
    assert r['metrics']['momentum_3m']['state']=='VALUE'
    assert r['metrics']['momentum_6m']['state']=='NOT_COMPUTED'
    assert r['metrics']['volatility_6m']['observed_days']<r['metrics']['volatility_6m']['expected_days']


def test_retained_vwap_is_preserved_as_diagnostic_without_scope_promotion():
    original=contract()
    rows=[{**row,'price_basis':'RAW','returned_symbol':'SYN','asof':'-', 'quality_reasons':[],
           'acquired_at':row['collected_at'],'vwap':'10','trade_count':2} for row in original['raw_bars']]
    c=retained_baseline(rows,symbol='SYN',source='SYNTHETIC_PROVIDER',currency_reference='SYNTHETIC',
                        evidence={**original['identity'],'confirmed_ranges':original['confirmed_ranges']})
    assert c['bars'][0]['vwap']=='10' and c['bars'][0]['trade_count']==2
    r=measure_contract(c,evaluation_day='2017-01-06',series_id='REQUEST:VWAP')
    m=r['metrics']['dollar_volume_6m']
    assert Decimal(m['raw_value'])==1000 and m['value'] is None
    assert m['null_reasons']==['TRADE_SCOPE_UNCONFIRMED']


def test_missing_signal_session_is_not_replaced_by_last_observed_day():
    r=measure_contract(contract(),evaluation_day='2017-01-09',series_id='REQUEST:STALE')
    assert r['signal_day']=='2017-01-09' and r['data_asof']=='2017-01-06' and r['status']=='STALE'
    assert r['raw_count']==r['adopted_count']==0


def test_identity_and_held_ranges_block_adoption_and_absolute_condition_only():
    c=contract();c['identity']['identity_start']='2016-12-01'
    c['held_ranges']=[{'from':'2016-11-01','to':'2016-11-01','reason':'SYNTHETIC_HOLD'}]
    r=measure_contract(c,evaluation_day='2017-01-06',series_id='REQUEST:1')
    m=r['metrics']['momentum_3m']
    assert m['state']=='DIAGNOSTIC' and m['raw_gt_zero'] is True and m['gt_zero'] is None
    assert 'IDENTITY_RANGE_UNCONFIRMED' in m['null_reasons'] and 'HELD_RANGE_IN_WINDOW' in m['null_reasons']


def test_confirmed_group_filters_preserve_original_ranks_and_metric_population():
    series,links,group=board_input();saved=deepcopy((series,links,group))
    r=build_contract_board(series,group=group,security_links=links,
                           conditions=[dict(metric='volatility_6m',condition='exclude_D10')])
    m=r['board']['metrics']['volatility_6m']
    assert m['n_members']==m['n_valid']==20 and m['k']==2
    assert len(r['selection']['security_ids'])==18
    selected=set(r['selection']['security_ids'])
    assert sorted(row['rank'] for row in m['rows'] if row['security_id'] in selected)==list(range(3,21))
    assert r['board']['metrics']['dollar_volume_6m']['n_valid']==0
    assert r['ranked_security_count']==20 and r['selection']['rank_origin']=='ORIGINAL_GROUP'
    assert (series,links,group)==saved


def test_unknown_group_or_missing_fixed_link_does_not_stop_company_measures():
    series,links,group=board_input(1)
    unknown={**group,'membership_status':'UNKNOWN','member_security_ids':None,'membership_source':None}
    r=build_contract_board(series,group=unknown)
    assert r['measurements'][0]['adopted_count']==4
    assert r['board']['metrics']['momentum_3m']['n_valid'] is None
    assert r['board']['metrics']['momentum_3m']['rows'][0]['rank'] is None
    assert r['ranked_security_count']==r['fixed_security_id_count']==0
    assert r['selection']['status']=='NOT_COMPUTED'
    assert r['selection']['reason']=='GROUP_MEMBERSHIP_UNCONFIRMED'
    confirmed=build_contract_board(series,group=group)
    assert confirmed['board']['metrics']['momentum_3m']['n_members']==1
    assert confirmed['board']['metrics']['momentum_3m']['n_valid']==0


@pytest.mark.parametrize('change,error',[
    ({'identifier_type':'CIK'},'FIXED_SECURITY_LINK_EVIDENCE_REQUIRED'),
    ({'identifier_type':'TICKER'},'FIXED_SECURITY_LINK_EVIDENCE_REQUIRED'),
    ({'reference':None},'FIXED_SECURITY_LINK_EVIDENCE_REQUIRED'),
    ({'security_id':'SYN'},'ISSUER_OR_TICKER_IS_NOT_SECURITY_ID'),
])
def test_board_requires_evidenced_security_ids(change,error):
    series,links,group=board_input(1);links[0].update(change)
    with pytest.raises(ValueError,match=error):build_contract_board(series,group=group,security_links=links)


def test_metric_valid_n_is_independent_and_missing_volatility_never_passes_filter():
    series,links,group=board_input(10)
    c=series[0]['contract'];gap='2016-08-01'
    for name in ('bars','raw_bars'):c[name]=[r for r in c[name] if r['date']!=gap]
    r=build_contract_board(series,group=group,security_links=links,
                           conditions=[dict(metric='volatility_6m',condition='exclude_D10')])
    assert r['board']['metrics']['momentum_3m']['n_valid']==10
    assert r['board']['metrics']['volatility_6m']['n_valid']==9
    assert r['selection']['security_ids']==[] # N<10 and the missing value both fail.


def test_dated_link_does_not_extend_expired_source_identity():
    series,links,group=board_input(1)
    series[0]['contract']['identity']['identity_end']='2017-01-05'
    r=build_contract_board(series,group=group,security_links=links)
    assert r['fixed_security_id_count']==0 and r['ranked_security_count']==0
    assert r['linkage'][0]['reason']=='IDENTITY_RANGE_UNCONFIRMED'


def test_adjusted_chart_does_not_adopt_raw_diagnostics_as_adjusted_measures():
    c=contract();c['basis']='SPLIT_ADJUSTED'
    r=measure_contract(c,evaluation_day='2017-01-06',series_id='REQUEST:ADJUSTED')
    assert r['raw_count']==4 and r['adopted_count']==0
    assert r['diagnostic_basis']=='RAW' and r['chart_basis']=='SPLIT_ADJUSTED'
    assert 'SPLIT_ADJUSTED_DISPLAY_ADAPTER_PENDING' in r['metrics']['momentum_3m']['null_reasons']


def test_synthetic_ids_cannot_be_assigned_to_actual_retained_contracts():
    series,links,group=board_input(1);series[0]['contract'].pop('fixture_kind')
    with pytest.raises(ValueError,match='SYNTHETIC_SECURITY_ID_ON_RETAINED_INPUT'):
        build_contract_board(series,group=group,security_links=links)


def test_two_provider_series_cannot_silently_duplicate_one_group_security():
    series,links,group=board_input(2)
    series[1]['contract']['security_id']=links[0]['security_id']
    links[1]['security_id']=links[0]['security_id']
    with pytest.raises(ValueError,match='DUPLICATE_SECURITY_ID'):
        build_contract_board(series,group=group,security_links=links)


@pytest.mark.parametrize('mode',['technical-measures','technical-board'])
def test_normal_cli_private_output_and_no_provider_request(mode,tmp_path):
    tool=Path(__file__).parents[2]/'tools/kis_retained_calculate.py'
    if mode=='technical-measures':args=dict(c=contract(short=True),evaluation_day='2017-01-06',series_id='REQUEST:1')
    else:
        series,links,group=board_input(1);args=dict(series=series,group=group,security_links=links)
    job=tmp_path/'job.json';out=tmp_path/'result.json';job.write_text(json.dumps(dict(mode=mode,arguments=args)))
    r=subprocess.run([sys.executable,str(tool),'--job',str(job),'--output',str(out)],capture_output=True,text=True)
    assert r.returncode==0 and r.stdout=='OFFLINE_PRIVATE_JOB_WRITTEN\n' and r.stderr==''
    assert out.stat().st_mode&0o777==0o600
    assert json.loads(out.read_text())['publication_scope']=='OWNER_PRIVATE_ONLY'


@pytest.mark.parametrize('known', [True, False])
def test_reader_export_cli_uses_merged_main_reader_without_recalculation(known, tmp_path):
    # Regression: rich metric rows contain unit/window fields refused by #470.
    # Exercise the real reader, not a second Python copy of its validator.
    import shutil
    if not shutil.which('node'):
        pytest.skip('Node is required to check the merged Main reader')
    series, links, group = board_input(20 if known else 1)
    if not known:
        group.update(membership_status='UNKNOWN', member_security_ids=None, membership_source=None)
    result = build_contract_board(series, group=group, security_links=links if known else ())
    # Decimal calculations may emit exponent notation; the real JS reader only
    # accepts plain decimal strings, including null-adopted raw diagnostics.
    result['board']['metrics']['dollar_volume_6m']['rows'][0]['raw_value'] = '0E-49'
    original = deepcopy(result)
    job, out = tmp_path/'reader-job.json', tmp_path/'reader.json'
    job.write_text(json.dumps(dict(mode='technical-reader', arguments=dict(result=result))))
    root = Path(__file__).parents[2]
    run = subprocess.run([sys.executable, str(root/'tools/kis_retained_calculate.py'),
                          '--job', str(job), '--output', str(out)], capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    assert run.stdout == 'OFFLINE_PRIVATE_JOB_WRITTEN\n'
    payload = json.loads(out.read_text())
    assert payload['publication_scope'] == 'OWNER_PRIVATE_ONLY'
    assert payload['data_kind'] == 'SYNTHETIC'
    projected = payload['cases']['private']['metrics']
    for name, metric in result['board']['metrics'].items():
        assert projected[name]['n_valid'] == metric['n_valid']
        for before, after in zip(metric['rows'], projected[name]['rows']):
            for key in ('value', 'rank', 'decile', 'conditions', 'null_reasons'):
                assert after[key] == before[key]
    assert result == original
    assert out.stat().st_mode & 0o777 == 0o600
    reader = root/'src/investment_system/product/web_app/tech-screen.js'
    script = "const fs=require('fs'),T=require(process.argv[1]); const r=T.validate(JSON.parse(fs.readFileSync(process.argv[2],'utf8'))); console.log(JSON.stringify({ok:r.ok,code:r.code,path:r.path}));"
    checked = subprocess.run(['node', '-e', script, str(reader), str(out)], capture_output=True, text=True)
    assert checked.returncode == 0, checked.stderr
    assert json.loads(checked.stdout) == {'ok': True}


def test_reader_export_preserves_exact_tiny_decimal_values_and_median():
    series, links, group = board_input(1)
    result = build_contract_board(series, group=group, security_links=links)
    metric = result['board']['metrics']['momentum_3m']
    metric['rows'][0]['value'] = '1.23456789012345678901234567890123456789E-20'
    metric['rows'][0]['raw_value'] = '1.23456789012345678901234567890123456789E-20'
    metric['median'] = '1.23456789012345678901234567890123456789E-20'
    exported = board_reader_payload(result)['cases']['private']['metrics']['momentum_3m']
    exact = '0.0000000000000000000123456789012345678901234567890123456789'
    assert exported['median'] == exact
    assert exported['rows'][0]['value'] == exported['rows'][0]['raw_value'] == exact
    assert metric['median'].endswith('E-20')


@pytest.mark.parametrize('change,error', [
    ('unit', 'READER_METRIC_UNIT_MISMATCH'),
    ('day', 'READER_BOARD_DATE_OR_SCHEMA_MISMATCH'),
    ('missing_member', 'READER_SERIES_ID_MISSING'),
    ('scope', 'PRIVATE_BOARD_RESULT_REQUIRED'),
])
def test_reader_export_refuses_semantic_changes_without_filling_or_dropping_members(change, error):
    series, links, group = board_input(1)
    if change == 'missing_member':
        group['member_security_ids'].append('SYNTHETIC:MISSING')
    result = build_contract_board(series, group=group, security_links=links)
    if change == 'unit':
        result['board']['metrics']['momentum_3m']['rows'][0]['unit'] = 'FRACTION'
    elif change == 'day':
        result['signal_day'] = '2017-01-05'
    elif change == 'scope':
        result['publication_scope'] = 'PUBLIC'
    before = deepcopy(result)
    with pytest.raises(ValueError, match=error):
        board_reader_payload(result)
    assert result == before
