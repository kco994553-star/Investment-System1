from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys
import pytest
from investment_system.macro import evidence_lines as el
from investment_system.research.macro_observed_timeline import timeline

SID='TREASURY:BC_10YEAR-BC_3MONTH:MONTHLY_MEAN'
T0=datetime(2026,1,2,12,tzinfo=timezone.utc)
def capture(rows, at, posted=None):
    return {SID:{'rows':rows,'acquired_at':at,'release':{'at':posted,'date':None}}}
def archive():
    p=el.build(capture({'2025-10':0.2,'2025-11':0.1},T0),previous=None,previous_state='NO_LIVE',now=T0)
    return el.build(capture({'2025-10':0.2,'2025-11':-0.1,'2025-12':-0.2},T0+timedelta(days=2)),previous=p,previous_state='LOADED',now=T0+timedelta(days=2))

def test_baseline_before_capture_is_unavailable_then_month_is_held_not_interpolated():
    result=timeline(archive(),[T0-timedelta(seconds=1),T0,T0+timedelta(days=1)])
    a,b,c=[x['series'][SID] for x in result['snapshots']]
    assert a['value'] is None and a['reason']=='BEFORE_CAPTURE_HISTORY'
    assert b['value']==0.1 and b['observation_period']=='2025-11'
    assert c['value']==0.1 and c['held'] and not c['new_observation']
    assert c['first_published_at'] is None and c['frequency']=='M'
    assert result['interpolation']=='NONE' and result['historical_pit_status']=='OBSERVED_CAPTURE_ONLY'

def test_revision_never_leaks_back_and_new_period_only_after_recorded_capture():
    result=timeline(archive(),[T0,T0+timedelta(days=2)])
    a,b=[x['series'][SID] for x in result['snapshots']]
    assert a['value']==0.1 and b['value']==-0.2 and b['new_observation']
    assert b['candidate_state']=='down' and b['model_status']=='NOT_APPLIED'

def test_source_last_modified_is_not_first_release_or_proven_receipt_time():
    first=el.build(capture({'2025-11':0.1},T0),previous=None,previous_state='NO_LIVE',now=T0)
    posted=T0+timedelta(days=1)
    p=el.build(capture({'2025-11':-0.1},T0+timedelta(days=2),posted),previous=first,previous_state='LOADED',now=T0+timedelta(days=2))
    a,b=[x['series'][SID] for x in timeline(p,[posted,T0+timedelta(days=2)])['snapshots']]
    assert a['value']==0.1 and b['value']==-0.1 and b['revised']
    assert b['available_at']==el.iso(T0+timedelta(days=2))
    assert b['source_posted_at']==el.iso(posted) and b['first_published_at'] is None
    assert b['availability_basis']=='ARCHIVE_CAPTURE_UPPER_BOUND'

def test_stale_keeps_last_value_and_rights_held_series_stays_null():
    r=timeline(archive(),[T0+timedelta(days=150)])['snapshots'][0]['series']
    assert r[SID]['state']=='STALE' and r[SID]['value']==-0.2
    assert r['DOL:ETA539:INITIAL_CLAIMS_SA']['value'] is None
    assert r['DOL:ETA539:INITIAL_CLAIMS_SA']['reason']=='TERMS_UNVERIFIED'


def test_invalid_cutoff_and_out_of_order_cutoffs_fail():
    with pytest.raises(ValueError):timeline(archive(),[datetime(2026,1,1)])
    with pytest.raises(ValueError):timeline(archive(),[T0,T0-timedelta(seconds=1)])


def test_cli_writes_private_output_and_never_overwrites(tmp_path):
    source=tmp_path/'archive.json'; output=tmp_path/'result.json';source.write_text(json.dumps(archive()))
    script=Path(__file__).resolve().parents[1]/'tools/macro_observed_timeline.py'
    cmd=[sys.executable,str(script),'--archive',str(source),'--at',el.iso(T0),'--output',str(output)]
    r=subprocess.run(cmd,capture_output=True,text=True)
    assert r.returncode==0,r.stderr
    assert json.loads(output.read_text())['snapshots'][0]['series'][SID]['value']==0.1
    assert output.stat().st_mode&0o777==0o600
    assert subprocess.run(cmd,capture_output=True).returncode!=0


def test_later_collection_revision_wins_over_earlier_posting_version_with_late_upper_bound():
    p=el.build(capture({'2025-11':0.1},T0),previous=None,previous_state='NO_LIVE',now=T0)
    p=el.build(capture({'2025-11':0.2},T0+timedelta(days=1),T0+timedelta(hours=12)),previous=p,previous_state='LOADED',now=T0+timedelta(days=1))
    p=el.build(capture({'2025-11':0.3},T0+timedelta(days=2)),previous=p,previous_state='LOADED',now=T0+timedelta(days=2))
    # A later, unchanged capture makes the conservative archive bound later still.
    p=el.build(capture({'2025-11':0.3},T0+timedelta(days=3)),previous=p,previous_state='LOADED',now=T0+timedelta(days=3))
    assert timeline(p,[T0+timedelta(days=3)])['snapshots'][0]['series'][SID]['value']==0.3
