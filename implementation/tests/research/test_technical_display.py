from datetime import date, timedelta
import pytest
from investment_system.research.technical_display import measure_display
from investment_system.research.exp_deciles import schedule


def sample(n=250):
    days=[];d=date(2017,1,3)
    while len(days)<n:
        if schedule.is_session(d):days.append(str(d))
        d+=timedelta(days=1)
    rows=[dict(date=d,close=str(i+1),open=str(i+1),high=str(i+2),low=str(i+.5),volume='100',price_basis='RAW',quality_reasons=[]) for i,d in enumerate(days)]
    evidence=dict(identity_status='DOCUMENT_RECONSTRUCTED',identity_reference='synthetic',no_split_start=days[0],no_split_end=days[-1],no_split_reference='synthetic',currency='USD',currency_reference='synthetic')
    return rows,evidence


def test_existing_kernels_on_real_shaped_rows_preserve_units_and_values():
    rows,e=sample();r=measure_display(rows,signal_day=rows[-1]['date'],series_id='SYNTHETIC',evidence=e,source_kind='NORMALIZED_PROVIDER_DAILY_BARS')
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
    r=measure_display(rows,signal_day=rows[-1]['date'],series_id='SYNTHETIC',evidence=e,source_kind='NORMALIZED_PROVIDER_DAILY_BARS')
    assert r['metrics']['SMA_20']['raw_value']==240.5 and r['metrics']['SMA_20']['value'] is None
    assert 'IDENTITY_UNCONFIRMED' in r['metrics']['SMA_20']['null_reasons']
    assert r['pit_status']=='NOT_VERIFIED' and r['rank'] is None


def test_missing_volume_or_high_does_not_erase_close_metrics():
    rows,e=sample();rows[-1]['volume']=None;rows[-1]['high']=None
    rows[-1]['quality_reasons']=['VOLUME_MISSING','HIGH_MISSING']
    r=measure_display(rows,signal_day=rows[-1]['date'],series_id='SYNTHETIC',evidence=e,source_kind='NORMALIZED_PROVIDER_DAILY_BARS')
    assert r['metrics']['SMA_20']['raw_value']==240.5
    assert r['metrics']['ATR_14']['raw_value'] is None
    assert r['volume_note']['raw_state']=='NOT_AVAILABLE'


def test_calendar_gap_cannot_be_smoothed_or_filled_and_future_bars_excluded():
    rows,e=sample();day=rows[-2]['date']
    first=measure_display(rows,signal_day=day,series_id='SYNTHETIC',evidence=e,source_kind='NORMALIZED_PROVIDER_DAILY_BARS')
    assert first['excluded_future_rows']==1 and first['history_count']==249
    del rows[-3]
    second=measure_display(rows,signal_day=day,series_id='SYNTHETIC',evidence=e,source_kind='NORMALIZED_PROVIDER_DAILY_BARS')
    assert second['metrics']['EMA_20']['raw_value'] is None
    assert 'PRICE_WINDOW_INCOMPLETE' in second['metrics']['EMA_20']['null_reasons']


def test_zero_volume_is_observed_but_flat_rsi_is_missing():
    rows,e=sample(35)
    for r in rows:r.update(close='10',open='10',high='11',low='9',volume='0')
    out=measure_display(rows,signal_day=rows[-1]['date'],series_id='SYNTHETIC',evidence=e,source_kind='NORMALIZED_PROVIDER_DAILY_BARS')
    assert out['volume_latest']['raw_value']==0
    assert out['metrics']['RSI_14']['raw_value'] is None
    assert 'ZERO_TOTAL_CHANGE' in out['metrics']['RSI_14']['null_reasons']
    assert out['metrics']['SMA_120']['raw_value'] is None


def test_last_trade_source_is_not_promoted_to_daily_bars():
    rows,e=sample()
    with pytest.raises(ValueError,match='DAILY_BAR_SOURCE_REQUIRED'):
        measure_display(rows,signal_day=rows[-1]['date'],series_id='IEX',evidence=e,source_kind='IEX_LAST_TRADE')


def test_offline_cli_keeps_values_private_and_refuses_overwrite(tmp_path):
    import json,subprocess,sys
    from pathlib import Path
    rows,e=sample();source=tmp_path/'input.json';out=tmp_path/'out.json'
    source.write_text(json.dumps({'signal_day':rows[-1]['date'],'series':[{'series_id':'SYNTHETIC','source_kind':'NORMALIZED_PROVIDER_DAILY_BARS','rows':rows,'evidence':e}]}))
    cmd=[sys.executable,str(Path(__file__).resolve().parents[2]/'tools/technical_display_offline.py'),'--input',str(source),'--output',str(out)]
    r=subprocess.run(cmd,capture_output=True,text=True)
    assert r.returncode==0,r.stderr
    assert out.stat().st_mode & 0o777 == 0o600
    assert json.loads(out.read_text())['series'][0]['metrics']['SMA_20']['raw_value']==240.5
    assert subprocess.run(cmd,capture_output=True).returncode != 0


def test_stateless_sma_requires_action_evidence_only_for_its_actual_window():
    rows,e=sample();e['no_split_start']=rows[-120]['date']
    r=measure_display(rows,signal_day=rows[-1]['date'],series_id='SYNTHETIC',evidence=e,source_kind='NORMALIZED_PROVIDER_DAILY_BARS')
    assert r['metrics']['SMA_20']['value']==240.5
    assert r['metrics']['SMA_120']['value']==190.5
    assert r['metrics']['EMA_20']['value'] is None
    assert r['metrics']['SMA_20']['window_start']==rows[-20]['date']
