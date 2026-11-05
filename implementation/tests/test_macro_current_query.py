"""Current reading projects a verified calculation cache, not a new capture."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest
from investment_system.macro import evidence_lines as el
from investment_system.research.macro_observed_timeline import timeline

SID='TREASURY:BC_10YEAR-BC_3MONTH:MONTHLY_MEAN'
T0=datetime(2026,1,2,12,tzinfo=timezone.utc)


def cached(*, failure=False):
    capture={SID:{'rows':{'2025-10':0.2,'2025-11':0.1},'acquired_at':T0,'release':{}}}
    p=el.build(capture,previous=None,previous_state='NO_LIVE',now=T0)
    if failure:
        p=el.build({SID:{'reason':'SOURCE_NOT_AVAILABLE'}},previous=p,previous_state='LOADED',now=T0+timedelta(hours=1))
    result=timeline(p,[el.parse_iso(p['generated_at'])])
    result['archive_sha256']='a'*64
    return result


def current(cache,at):
    from investment_system.research.macro_observed_timeline import current_query
    return current_query(cache,at)


def test_current_query_preserves_cached_calculation_and_exposes_source_update_and_availability(monkeypatch):
    cache=cached()
    monkeypatch.setattr(el,'current_state',lambda *a,**k:pytest.fail('must reuse cached candidate calculation'))
    result=current(cache,T0+timedelta(days=1))
    row=result['series'][SID]
    assert result['schema_version']=='macro-current-query/1'
    assert result['query_at']==el.iso(T0+timedelta(days=1)) and result['cache_asof']==el.iso(T0)
    assert result['seconds_since_cache_asof']==86400 and result['new_external_requests']==0
    assert row['value']==0.1 and row['candidate_state']=='clear'
    assert row['source']['agency']=='TREASURY' and row['source']['publication']=='PUBLIC'
    assert row['last_successful_update_at']==el.iso(T0) and row['seconds_since_success']==86400
    assert row['held'] and not row['new_observation'] and not row['revised']
    assert row['query_usable'] and not row['historical_pit_eligible']
    assert row['official_release_at'] is None and row['source_version_id'] is None
    assert result['counts']['query_usable']==1 and result['counts']['stale']==0
    assert result['scope']==el.SCOPE


def test_current_query_rechecks_only_period_stale_and_keeps_missing_reasons():
    result=current(cached(),T0+timedelta(days=150))
    row=result['series'][SID]
    assert row['stale'] and row['state']=='STALE' and row['value']==0.1
    assert row['query_usable'] and row['reason']=='PERIOD_DELAYED'
    assert result['counts']['fresh_query_usable']==0 and result['counts']['stale']==1
    missing=result['series']['CENSUS:M3:NXA:NO:SA']
    assert missing['value'] is None and missing['update_status']=='NEVER_SUCCEEDED'
    assert result['series']['DOL:ETA539:INITIAL_CLAIMS_SA']['reason']=='TERMS_UNVERIFIED'


def test_current_query_keeps_last_success_and_distinguishes_failed_collection():
    row=current(cached(failure=True),T0+timedelta(days=1))['series'][SID]
    assert row['value']==0.1 and row['query_usable'] and not row['stale']
    assert row['last_successful_update_at']==el.iso(T0)
    assert row['update_status']=='FAILED_AFTER_SUCCESS'
    assert row['collection_reason_at_query']=='SOURCE_NOT_AVAILABLE'


@pytest.mark.parametrize('mutate',[
    lambda p:p.update(evidence_contract_version='unknown'),
    lambda p:p['snapshots'][-1]['series'].pop(SID),
    lambda p:p['snapshots'][-1]['series'][SID].update(value=float('nan')),
    lambda p:p['snapshots'][-1]['series'][SID].update(query_usable=False),
    lambda p:p['snapshots'][-1]['series'][SID].update(historical_pit_eligible=True),
    lambda p:p['snapshots'][-1]['series'][SID].update(latest_archive_success_at='broken'),
])
def test_invalid_cache_fails_before_current_file(mutate):
    p=deepcopy(cached());mutate(p)
    with pytest.raises(ValueError):current(p,T0+timedelta(days=1))


def test_current_query_rejects_backward_query_and_cache_not_current_for_archive():
    with pytest.raises(ValueError):current(cached(),T0-timedelta(seconds=1))
    p=cached();p['archive_generated_at']=el.iso(T0+timedelta(hours=1))
    with pytest.raises(ValueError):current(p,T0+timedelta(days=1))


def test_existing_cli_projects_pinned_cache_without_network_or_overwrite(tmp_path):
    p=tmp_path/'timeline.json';p.write_text(json.dumps(cached()))
    output=tmp_path/'macro-current.json'
    script=Path(__file__).resolve().parents[1]/'tools/macro_observed_timeline.py'
    base=[sys.executable,str(script),'--timeline-cache',str(p),'--at',el.iso(T0+timedelta(days=1)),'--output',str(output)]
    bad=subprocess.run(base+['--cache-sha256','b'*64],capture_output=True,text=True)
    assert bad.returncode!=0 and not output.exists()
    digest=hashlib.sha256(p.read_bytes()).hexdigest()
    good=subprocess.run(base+['--cache-sha256',digest],capture_output=True,text=True)
    assert good.returncode==0,good.stderr
    result=json.loads(output.read_text())
    assert result['series'][SID]['query_usable'] and not result['series'][SID]['historical_pit_eligible']
    assert result['timeline_cache_sha256']==digest and result['archive_sha256']=='a'*64
    assert output.stat().st_mode&0o777==0o600
    assert subprocess.run(base+['--cache-sha256',digest],capture_output=True).returncode!=0
