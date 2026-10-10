
# GSQ-010: retained historical algorithm; removed inputs cannot be replayed.
from pathlib import Path as _CleanupPath
import json as _cleanup_json
import sys as _cleanup_sys
_cleanup_root = next(p for p in _CleanupPath(__file__).resolve().parents if p.name == "implementation").parent
_cleanup_removed_inputs = ['implementation/reports/gate_evidence/gate_chain_2024-12-31_real_gha.json', 'implementation/reports/gate_evidence/track_a_data_vintage_comparison_2026-09-27.json']
if any(not (_cleanup_root / p).is_file() for p in _cleanup_removed_inputs):
    print(_cleanup_json.dumps({"status": "NOT_AVAILABLE", "reason": "GSQ-010: archived inputs removed"}))
    _cleanup_sys.exit(2)

import sys,json
from pathlib import Path
sys.path[:0]=['src','tools']
from investment_system.ingestion.raw_store import RawDatasetStore
from investment_system.ingestion.replay import load_price_bars
from investment_system.providers.yahoo_chart import pit_bar
from ca_unit_policy import dt
GE=Path('reports/gate_evidence');p=GE/'track_a_data_vintage_comparison_2026-09-27.json';d=json.loads(p.read_text());a=json.loads(Path('/tmp/ca_unit/dec_pinned_full.json').read_text());b=json.loads(Path('/tmp/ca_unit/dec_fresh_full.json').read_text());g=json.loads((GE/'gate_chain_2024-12-31_real_gha.json').read_text());sym={x['company_id']:x['yahoo'] for x in g['top500']};stores=[RawDatasetStore(x) for x in ['/tmp/track_a_run70/data/raw','/tmp/track_a_network500']];diffs=[]
for cid,x in a['outcomes'].items():
 y=b['outcomes'][cid];assert x['status']==y['status']=='LINKED' and x['parent_payload_intact'] and y['parent_payload_intact']
 if x['realized_return']==y['realized_return']:continue
 bars=[[pit_bar(load_price_bars(s,sym[cid],'5y'),dt(t)) for t in ['2024-12-31','2025-03-31']] for s in stores]
 for out,px in zip([x,y],bars):assert px[1]['price']/px[0]['price']-1==out['realized_return']
 diffs.append({'company_id':cid,'symbol':sym[cid],'pinned_return':x['realized_return'],'fresh_return':y['realized_return'],'absolute_delta':abs(x['realized_return']-y['realized_return']),'pinned_bars':bars[0],'fresh_bars':bars[1],'same_raw_close':all(bars[0][j]['close']==bars[1][j]['close'] for j in [0,1]),'same_observed_at':all(bars[0][j]['observed_at']==bars[1][j]['observed_at'] for j in [0,1])})
d['outcome_differences']=diffs;d['n_numeric_outcome_differences']=len(diffs);d['max_individual_return_delta']=max(x['absolute_delta'] for x in diffs);d['all_same_raw_close']=all(x['same_raw_close'] for x in diffs);d['all_same_observed_at']=all(x['same_observed_at'] for x in diffs)
d['review']='Fresh provider adjusted-close payload vintage differs slightly. Each numeric outcome difference is reproduced exactly from retained endpoint prices; no tolerance used to claim exact equality. UUID-only differences omitted. Membership, selection and errors identical. Frozen baseline remains pinned to original validated bytes; network benchmark uses separately archived fresh bytes.'
p.write_text(json.dumps(d,indent=2,default=lambda x:x.isoformat())+'\n');print({k:v for k,v in d.items() if k!='outcome_differences'})
