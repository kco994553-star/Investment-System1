"""Confirmed split-only synthetic economic path, through the normal adapter."""
from copy import deepcopy
from decimal import Decimal
from datetime import date
import hashlib,json
import pytest
from investment_system.research.kis_price_bridge import normalize_page,analyze,validate_contract
from investment_system.research.private_technical_board import measure_contract
from investment_system.research.exp_deciles.technical_measures import sessions


def case(split=True,days_count=None):
    days=sessions(date(2016,1,4),date(2017,1,6))
    if days_count:days=days[-days_count:]
    event='2016-07-01';rows=[]
    for i,d in enumerate(days):
        factor=2 if split and d<event else 1
        rows.append(dict(xymd=d.replace('-',''),open=str(100*factor),high=str(101*factor),low=str(99*factor),clos=str(100*factor),tvol=str(200//factor),tamt='20000'))
    body=json.dumps({'rt_cd':'0','output1':{'rsym':'DNASSYN'},'output2':rows}).encode()
    evidence=dict(currency='USD',currency_reference='SYNTHETIC',identity_status='CONFIRMED',identity_reference='SYNTHETIC',identity_start=days[0],identity_end=days[-1],security_id='SYNTHETIC:SEC',confirmed_ranges=[],held_ranges=[],splits=[dict(date=event,ratio='2',status='CONFIRMED',evidence='SYNTHETIC_CONFIRMED_SPLIT')] if split else [])
    evidence['confirmed_ranges']=[{'from':days[0],'to':days[-1],'evidence':'SYNTHETIC_COMPLETE_ACTION_COVERAGE'}]
    return normalize_page(body,receipt=dict(sha256=hashlib.sha256(body).hexdigest(),bytes=len(body),fetched_at='2017-01-07T05:00:00Z',http_status=200),request=dict(SYMB='SYN',EXCD='NAS',MODP='0',GUBN='0',BYMD='20170106'),evidence=evidence,basis='SPLIT_ADJUSTED' if split else 'RAW')


def test_split_continuity_all_13_components_and_four_price_measures():
    adjusted,reference=case(),case(False)
    assert adjusted['bars'][0]['close']==adjusted['bars'][-1]['close']=='100'
    assert adjusted['bars'][0]['volume']=='200' and adjusted['raw_bars'][0]['volume']=='100'
    for c in (adjusted,reference):validate_contract(c)
    a,b=analyze(adjusted,evaluation_day='2017-01-06'),analyze(reference,evaluation_day='2017-01-06')
    for key in a['metrics']:
        assert a['metrics'][key]['value']==b['metrics'][key]['value'],key
    assert a['adopted_count']==b['adopted_count']
    assert a['adopted_count']==12
    for name,value in [('SMA_20',100),('EMA_20',100),('MACD_12_26',0),('MACD_SIGNAL_9',0),('ATR_14',2)]:
        assert a['metrics'][name]['value']==value
    x=measure_contract(adjusted,evaluation_day='2017-01-06',series_id='SYNTHETIC:REQUEST')
    y=measure_contract(reference,evaluation_day='2017-01-06',series_id='SYNTHETIC:REQUEST')
    for key in ('momentum_3m','momentum_6m','momentum_12m','volatility_6m'):
        assert Decimal(x['metrics'][key]['value'])==Decimal(y['metrics'][key]['value'])==0
    assert x['metrics']['dollar_volume_6m']['value'] is None
    assert 'TRADE_SCOPE_UNCONFIRMED' in x['metrics']['dollar_volume_6m']['null_reasons']
    assert x['diagnostic_basis']=='SPLIT_ADJUSTED'


def test_tampered_adjusted_values_and_missing_action_coverage_do_not_adopt():
    c=case();c['bars'][0]['close']='99.5'
    with pytest.raises(ValueError,match='ADJUSTED_ROWS'):validate_contract(c)
    c=case();c['confirmed_ranges']=[]
    r=analyze(c,evaluation_day='2017-01-06')
    assert r['adopted_count']==0
    assert all('ACTION_BASIS_UNCONFIRMED' in m['null_reasons'] for m in r['metrics'].values())


def test_future_split_never_rebases_earlier_evaluation():
    c=case();s='2016-06-30'
    a=analyze(c,evaluation_day=s)
    raw=deepcopy(c);raw['basis']='RAW';raw['bars']=deepcopy(raw['raw_bars']);raw['splits']=[]
    b=analyze(raw,evaluation_day=s)
    assert a['metrics']['SMA_20']['raw_value']==b['metrics']['SMA_20']['raw_value']==200

@pytest.mark.parametrize('n,key,value',[(14,'ATR_14',None),(15,'ATR_14',2),(19,'EMA_20',None),(20,'EMA_20',100),(25,'MACD_12_26',None),(26,'MACD_12_26',0),(33,'MACD_SIGNAL_9',None),(34,'MACD_SIGNAL_9',0)])
def test_recursive_and_rolling_warmup_unchanged(n,key,value):
    c=case(False,n);c['basis']='SPLIT_ADJUSTED'
    a=analyze(c,evaluation_day='2017-01-06');c['basis']='RAW'
    b=analyze(c,evaluation_day='2017-01-06')
    assert a['metrics'][key]['value']==value
    for key in a['metrics']:
        assert a['metrics'][key]['raw_value']==b['metrics'][key]['raw_value']
        assert a['metrics'][key]['value']==b['metrics'][key]['value']
        assert a['metrics'][key]['null_reasons']==b['metrics'][key]['null_reasons']

@pytest.mark.parametrize('change',[{'requested_symbol':'OTHER'},{'asof':'2018-02-16'},{'source_sha256':'x'*64}])
def test_separate_raw_liquidity_rows_retain_direct_source_validation(change):
    from test_technical_leaderboard import bars,evidence,S
    from investment_system.research.exp_deciles.technical_measures import measure
    rows=bars();liquid=deepcopy(rows);liquid[-1].update(change)
    with pytest.raises(ValueError):measure(rows,signal_day=S,symbol='TEST',series_id='SYNTHETIC',evidence=evidence(),liquidity_rows=liquid)


def test_adjusted_settings_and_group_are_separate_from_frozen_raw_policy():
    from investment_system.research.private_technical_board import build_contract_board
    c=case();m=measure_contract(c,evaluation_day='2017-01-06',series_id='SYNTHETIC:REQUEST')
    raw=case(False);r=measure_contract(raw,evaluation_day='2017-01-06',series_id='SYNTHETIC:REQUEST')
    assert m['settings_sha256']!=r['settings_sha256']
    assert m['settings_version']=='technical-leaderboard/split-adjusted-2026-11-05.1'
    group=dict(group_id='SYNTHETIC:ADJUSTED',signal_day='2017-01-06',membership_status='UNKNOWN',member_security_ids=None,membership_source=None)
    result=build_contract_board([dict(series_id='SYNTHETIC:REQUEST',contract=c)],group=group)
    assert result['board']['settings_sha256']==m['settings_sha256']
    with pytest.raises(ValueError,match='MIXED_PRICE_BASES'):
        build_contract_board([dict(series_id='SYNTHETIC:REQUEST',contract=c),dict(series_id='SYNTHETIC:OTHER',contract=raw)],group=group)
