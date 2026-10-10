
# GSQ-010: this historical entrypoint is retired even if old paths reappear.
# Original algorithms remain below for provenance; no replay is authorized here.
import json as _cleanup_json
import sys as _cleanup_sys
print(_cleanup_json.dumps({"status": "NOT_AVAILABLE", "reason": "GSQ-010: archived inputs removed"}))
_cleanup_sys.exit(2)

import sys,json,time,hashlib,concurrent.futures,threading,shutil,resource
from pathlib import Path
sys.path[:0]=['src','tools']
import fetch_real_data as fetch
from investment_system.ingestion.raw_store import RawDatasetStore
import official_pipeline as op
from investment_system.validation.vertical_slice import run_vertical_slice_from_store
GE=Path('reports/gate_evidence');date='2024-12-31'
evidence=json.loads((GE/f'gate_chain_{date}_real_gha.json').read_text())
assert evidence['official_top500_declared']
rows=evidence['top500'];assert len(rows)==500
store=RawDatasetStore('/tmp/track_a_network500')
# A warm dependency store is explicit: 500 facts, submissions, charts and events
# are fetched over the network; reviewed fallback and older SEC pages stay pinned.
original=RawDatasetStore('/tmp/track_a_run70/data/raw')
for directory in ['blobs','manifests']:
 for src in (original.root/directory).iterdir():
  dest=store.root/directory/src.name
  if not dest.exists():shutil.copyfile(src,dest)
tasks=[]
for r in rows:
 c=str(r['cik']).zfill(10);t=r['yahoo']
 tasks.extend([(f'companyfacts:{c}',fetch.SEC_FACTS_URL.format(cik=c),'SEC_COMPANYFACTS',fetch.UA),
               (f'submissions:{c}',fetch.SEC_SUBS_URL.format(cik=c),'SEC_SUBMISSIONS',fetch.UA),
               (f'yahoo_chart:{t}:5y',fetch.YAHOO_CHART_URL.format(symbol=t,range='5y'),'YAHOO_CHART',fetch.YAHOO_UA),
               (f'yahoo_events:{t}:5y',fetch.YAHOO_EVENTS_URL.format(symbol=t,range='5y'),'YAHOO_SPLIT_EVENTS',fetch.YAHOO_UA)])
lock=threading.Lock();next_request=0.;start=time.perf_counter();log=[]
def request(task):
 global next_request
 aid,url,kind,ua=task
 with lock:
  delay=max(0,next_request-time.perf_counter());next_request=max(time.perf_counter(),next_request)+.18
 if delay:time.sleep(delay)
 old=original.get_manifest(aid) if original.has(aid) else None
 # Isolate fetched bytes; never silently replace the validated data vintage.
 request_store=RawDatasetStore(store.root/'fresh')
 items=[];t=time.perf_counter();fetch._fetch_one(request_store,aid,url,kind,ua,items,True)
 entry=items[0];entry['wall_s']=time.perf_counter()-t
 if entry['status']=='OK':
  entry['sha256']=request_store.get_manifest(aid)['sha256']
  entry['identical_to_baseline']=bool(old and old['sha256']==entry['sha256'])
 return entry
with concurrent.futures.ThreadPoolExecutor(max_workers=32) as pool:
 for entry in pool.map(request,tasks):
  log.append(entry)
  if len(log)%100==0:print('network',len(log),'/',len(tasks),'seconds',round(time.perf_counter()-start,1),flush=True)
network_s=time.perf_counter()-start
# Use freshly ingested payloads in the measured replay. Reviewed alternative
# price sources keep their separately evidenced source selection.
used=[];preserved=[]
for entry in log:
 aid=entry['artifact_id']
 if entry['status']!='OK':
  preserved.append({'artifact_id':aid,'reason':entry['status']});continue
 old=original.get_manifest(aid) if original.has(aid) else {}
 if aid.startswith('yahoo_') and old.get('source_kind') not in {'YAHOO_CHART','YAHOO_SPLIT_EVENTS'}:
  preserved.append({'artifact_id':aid,'reason':'REVIEWED_ALTERNATIVE_SOURCE','source_kind':old.get('source_kind')});continue
 fresh=RawDatasetStore(store.root/'fresh');m=fresh.get_manifest(aid)
 store.put(aid,fresh.get_bytes(aid),m['source_url'],m['source_kind'],m['content_type'],'network500 measured ingest',m.get('http_status'))
 used.append(aid)

snap,status=op.load_official(date);assert snap
replay_start=time.perf_counter();res=run_vertical_slice_from_store(store,op._dt(date),op._dt('2025-03-31'),snap)
from collections import Counter
report={'kind':'TRACK_A_NETWORK_INCLUSIVE_500_BENCHMARK','as_of':date,'n_companies':500,
 'network_mode':'2000 actual network requests plus replay of successful fresh payloads; older SEC pages and reviewed alternative prices retained as explicit warm dependencies',
 'request_status_counts':dict(Counter(x['status'] for x in log)),'network_wall_s':network_s,'replay_wall_s':time.perf_counter()-replay_start,'total_wall_s':time.perf_counter()-start,
 'peak_rss_mb':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,'n_name_errors':len(res['name_errors']),'n_selected':res['n_selected'],
 'baseline_universe_id':snap.universe_id,'roster':rows,'requests':log,'fresh_payloads_used':len(used),'preserved_dependencies':preserved,
 'equal_weight_realized':res['equal_weight_realized'], 'selected':res['selected'],
 'note':'Network-inclusive warm-dependency benchmark. Fresh ingest-to-replay measured in one clock; compare outputs with the pinned Official replay before acceptance.'}
(GE/'track_a_network_500_benchmark_2026-09-27.json').write_text(json.dumps(report,indent=2,default=str)+'\n')
print({k:v for k,v in report.items() if k not in ['requests','roster']},flush=True)
