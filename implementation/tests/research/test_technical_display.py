from datetime import date, timedelta, datetime, time, timezone
from zoneinfo import ZoneInfo
import pytest
from investment_system.research.technical_display import measure_display
from investment_system.research.exp_deciles import schedule


def sample(n=250):
    days=[];d=date(2017,1,3)
    while len(days)<n:
        if schedule.is_session(d):days.append(str(d))
        d+=timedelta(days=1)
    rows=[dict(date=d,close=str(i+1),open=str(i+1),high=str(i+2),low=str(i+.5),volume='100',price_basis='RAW',quality_reasons=[],requested_symbol='SYNTHETIC',returned_symbol='SYNTHETIC',asof='-',source_sha256='a'*64,source_timestamp=datetime.combine(date.fromisoformat(d),time(),ZoneInfo('America/New_York')).astimezone(timezone.utc).isoformat()) for i,d in enumerate(days)]
    evidence=dict(identity_status='DOCUMENT_RECONSTRUCTED',identity_reference='synthetic',no_split_start=days[0],no_split_end=days[-1],no_split_reference='synthetic',currency='USD',currency_reference='synthetic')
    return rows,evidence


def test_existing_kernels_on_real_shaped_rows_preserve_units_and_values():
    rows,e=sample();r=measure_display(rows,signal_day=rows[-1]['date'],series_id='SYNTHETIC',evidence=e,symbol='SYNTHETIC',source_kind='NORMALIZED_PROVIDER_DAILY_BARS')
    m=r['metrics']
    assert m['SMA_20']['raw_value']==240.5 and m['SMA_20']['value']==240.5
    assert m['RSI_14']['value']==100
    assert m['MACD_12_26']['value']==pytest.approx(7)
    assert m['MACD_SIGNAL_9']['value']==pytest.approx(7)
    assert m['MACD_HISTOGRAM_12_26_9']['value']==pytest.approx(0)
    assert m['ATR_14']['raw_value']==pytest.approx(2)
    assert 'SMA_240' not in m
    assert r['volume_note']['raw_state']=='WITHOUT_VOLUME'


def test_unknown_identity_keeps_raw_and_never_promotes_or_ranks():
    rows,e=sample();e['identity_status']='UNKNOWN'
    r=measure_display(rows,signal_day=rows[-1]['date'],series_id='SYNTHETIC',evidence=e,symbol='SYNTHETIC',source_kind='NORMALIZED_PROVIDER_DAILY_BARS')
    assert r['metrics']['SMA_20']['raw_value']==240.5 and r['metrics']['SMA_20']['value'] is None
    assert 'IDENTITY_UNCONFIRMED' in r['metrics']['SMA_20']['null_reasons']
    assert r['pit_status']=='NOT_VERIFIED' and r['rank'] is None


def test_missing_volume_or_high_does_not_erase_close_metrics():
    rows,e=sample();rows[-1]['volume']=None;rows[-1]['high']=None
    rows[-1]['quality_reasons']=['VOLUME_MISSING','HIGH_MISSING']
    r=measure_display(rows,signal_day=rows[-1]['date'],series_id='SYNTHETIC',evidence=e,symbol='SYNTHETIC',source_kind='NORMALIZED_PROVIDER_DAILY_BARS')
    assert r['metrics']['SMA_20']['raw_value']==240.5
    assert r['metrics']['ATR_14']['raw_value'] is None
    assert r['volume_note']['raw_state']=='NOT_AVAILABLE'
    assert r['readiness']['metrics']['ATR_14']['warmup']['state']=='NOT_EVALUATED'


def test_calendar_gap_cannot_be_smoothed_or_filled_and_future_bars_excluded():
    rows,e=sample();day=rows[-2]['date']
    first=measure_display(rows,signal_day=day,series_id='SYNTHETIC',evidence=e,symbol='SYNTHETIC',source_kind='NORMALIZED_PROVIDER_DAILY_BARS')
    assert first['excluded_future_rows']==1 and first['history_count']==249
    del rows[-3]
    second=measure_display(rows,signal_day=day,series_id='SYNTHETIC',evidence=e,symbol='SYNTHETIC',source_kind='NORMALIZED_PROVIDER_DAILY_BARS')
    assert second['metrics']['EMA_20']['raw_value'] is None
    assert 'PRICE_WINDOW_INCOMPLETE' in second['metrics']['EMA_20']['null_reasons']


def test_zero_volume_is_observed_but_flat_rsi_is_missing():
    rows,e=sample(35)
    for r in rows:r.update(close='10',open='10',high='11',low='9',volume='0')
    out=measure_display(rows,signal_day=rows[-1]['date'],series_id='SYNTHETIC',evidence=e,symbol='SYNTHETIC',source_kind='NORMALIZED_PROVIDER_DAILY_BARS')
    assert out['volume_latest']['raw_value']==0
    assert out['metrics']['RSI_14']['raw_value'] is None
    assert 'ZERO_TOTAL_CHANGE' in out['metrics']['RSI_14']['null_reasons']
    assert out['metrics']['SMA_120']['raw_value'] is None


def test_last_trade_source_is_not_promoted_to_daily_bars():
    rows,e=sample()
    with pytest.raises(ValueError,match='DAILY_BAR_SOURCE_REQUIRED'):
        measure_display(rows,signal_day=rows[-1]['date'],series_id='IEX',evidence=e,symbol='SYNTHETIC',source_kind='IEX_LAST_TRADE')


def test_offline_cli_keeps_values_private_and_refuses_overwrite(tmp_path):
    import json,subprocess,sys
    from pathlib import Path
    rows,e=sample();source=tmp_path/'input.json';out=tmp_path/'out.json'
    source.write_text(json.dumps({'signal_day':rows[-1]['date'],'series':[{'series_id':'SYNTHETIC','symbol':'SYNTHETIC','source_kind':'NORMALIZED_PROVIDER_DAILY_BARS','rows':rows,'evidence':e}]}))
    cmd=[sys.executable,str(Path(__file__).resolve().parents[2]/'tools/technical_display_offline.py'),'--input',str(source),'--output',str(out)]
    r=subprocess.run(cmd,capture_output=True,text=True)
    assert r.returncode==0,r.stderr
    assert out.stat().st_mode & 0o777 == 0o600
    assert json.loads(out.read_text())['series'][0]['metrics']['SMA_20']['raw_value']==240.5
    assert subprocess.run(cmd,capture_output=True).returncode != 0


def test_stateless_sma_requires_action_evidence_only_for_its_actual_window():
    rows,e=sample();e['no_split_start']=rows[-120]['date']
    r=measure_display(rows,signal_day=rows[-1]['date'],series_id='SYNTHETIC',evidence=e,symbol='SYNTHETIC',source_kind='NORMALIZED_PROVIDER_DAILY_BARS')
    assert r['metrics']['SMA_20']['value']==240.5
    assert r['metrics']['SMA_120']['value']==190.5
    assert r['metrics']['EMA_20']['value'] is None
    assert r['metrics']['SMA_20']['window_start']==rows[-20]['date']


def test_missing_signal_session_does_not_relabel_previous_volume_as_current():
    rows,e=sample();signal=rows[-1]['date'];rows.pop()
    r=measure_display(rows,signal_day=signal,series_id='SYNTHETIC',evidence=e,symbol='SYNTHETIC',source_kind='NORMALIZED_PROVIDER_DAILY_BARS')
    assert r['volume_latest']['raw_value'] is None and r['volume_latest']['value'] is None
    assert 'SIGNAL_SESSION_MISSING' in r['volume_latest']['null_reasons']
    assert r['volume_latest']['last_observed_session']==rows[-1]['date']


@pytest.mark.parametrize('change,reason', [
    ({'returned_symbol':'OTHER'},'SYMBOL_MISMATCH'),
    ({'requested_symbol':'OTHER'},'SYMBOL_MISMATCH'),
    ({'asof':'2026-11-05'},'RAW_DIRECT_SYMBOL_BASIS_REQUIRED'),
    ({'source_sha256':None},'SOURCE_HASH_REQUIRED'),
    ({'source_timestamp':'2018-01-01T00:00:00Z'},'BAR_TIME_NOT_NY_MIDNIGHT'),
])
def test_normalized_row_provenance_must_match_the_evidence_series(change,reason):
    rows,e=sample();rows[-1].update(change)
    with pytest.raises(ValueError,match=reason):
        measure_display(rows,signal_day=rows[-1]['date'],series_id='SYNTHETIC',symbol='SYNTHETIC',evidence=e,source_kind='NORMALIZED_PROVIDER_DAILY_BARS')


def test_volume_uses_its_actual_21_session_evidence_window():
    rows,e=sample();e['no_split_start']=rows[-21]['date']
    out=measure_display(rows,signal_day=rows[-1]['date'],series_id='SYNTHETIC',symbol='SYNTHETIC',evidence=e,source_kind='NORMALIZED_PROVIDER_DAILY_BARS')
    assert out['volume_note']['state']=='WITHOUT_VOLUME'
    assert out['volume_latest']['value']==100


def test_readiness_separates_seed_warmup_identity_and_action_window():
    rows,e=sample();e['no_split_start']=rows[-120]['date']
    out=measure_display(rows,signal_day=rows[-1]['date'],series_id='SYNTHETIC',symbol='SYNTHETIC',evidence=e,source_kind='NORMALIZED_PROVIDER_DAILY_BARS')
    readiness=out['readiness']['metrics']['EMA_20']
    assert readiness['state']=='DIAGNOSTIC'
    assert readiness['initialization']['method']=='FIRST_20_CLOSE_SMA_THEN_EMA'
    assert readiness['initialization']['input_start']==rows[0]['date']
    assert readiness['warmup']==dict(minimum_sessions=20,observed_sessions=250,state='READY')
    assert readiness['continuity']['state']=='COMPLETE'
    assert readiness['identity']['state']=='DOCUMENT_RECONSTRUCTED'
    assert readiness['identity']['fixed_security_id_state']=='MISSING_RANKING_BLOCKED'
    assert readiness['adjustment']['state']=='UNCONFIRMED'
    assert readiness['block_reasons']==['ACTION_BASIS_UNCONFIRMED']
    assert out['readiness']['as_of']==rows[-1]['date']
    assert out['readiness']['availability_status']=='NOT_VERIFIED'
    assert out['readiness']['source_available_at'] is None
    assert out['readiness']['stale_status']=='UNKNOWN'
    assert out['readiness']['metrics']['BOLL_MIDDLE_20']['initialization']['method']=='ROLLING_CLOSE_MEAN'
    assert out['readiness']['metrics']['BOLL_UPPER_20_2']['initialization']['method']=='ROLLING_20_CLOSE_POPULATION_STDDEV'


def test_extending_documented_action_evidence_never_changes_seed_or_raw_values():
    rows,e=sample();e['no_split_start']=rows[31]['date']
    kwargs=dict(signal_day=rows[-1]['date'],series_id='SYNTHETIC',symbol='SYNTHETIC',source_kind='NORMALIZED_PROVIDER_DAILY_BARS')
    before=measure_display(rows,evidence=e,**kwargs)
    e['no_split_start']=rows[0]['date']
    after=measure_display(rows,evidence=e,**kwargs)
    recursive=('EMA_20','RSI_14','MACD_12_26','MACD_SIGNAL_9','MACD_HISTOGRAM_12_26_9','ATR_14')
    for name in before['metrics']:
        assert before['metrics'][name]['raw_value']==after['metrics'][name]['raw_value']
    for name in recursive:
        assert before['metrics'][name]['value'] is None
        assert after['metrics'][name]['value']==before['metrics'][name]['raw_value']
        assert after['readiness']['metrics'][name]['state']=='VALUE'
        assert after['metrics'][name]['window_start']==rows[0]['date']
    assert before['input_start']==after['input_start']==rows[0]['date']
    assert after['pit_status']=='NOT_VERIFIED' and after['rank'] is None


def test_empty_series_is_not_a_warmed_up_or_available_measurement():
    rows,e=sample()
    out=measure_display([],signal_day=rows[-1]['date'],series_id='SYNTHETIC',symbol='SYNTHETIC',evidence=e,source_kind='NORMALIZED_PROVIDER_DAILY_BARS')
    status=out['readiness']['metrics']['RSI_14']
    assert status['state']=='NOT_COMPUTED'
    assert status['warmup']==dict(minimum_sessions=15,observed_sessions=0,state='NOT_EVALUATED')
    assert status['continuity']['state']=='INCOMPLETE'
    assert 'PRICE_WINDOW_INCOMPLETE' in status['block_reasons']


def test_undefined_rsi_is_not_warmup_and_valid_zero_is_value():
    rows,e=sample(35)
    for row in rows:row.update(close='10',open='10',high='11',low='9')
    out=measure_display(rows,signal_day=rows[-1]['date'],series_id='SYNTHETIC',symbol='SYNTHETIC',evidence=e,source_kind='NORMALIZED_PROVIDER_DAILY_BARS')
    rsi=out['readiness']['metrics']['RSI_14']
    assert rsi['state']=='NOT_COMPUTED' and rsi['warmup']['state']=='READY'
    assert rsi['block_reasons']==['ZERO_TOTAL_CHANGE']
    assert out['metrics']['MACD_12_26']['value']==0
    assert out['readiness']['metrics']['MACD_12_26']['state']=='VALUE'
