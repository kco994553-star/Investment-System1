
# GSQ-010: retained historical algorithm; removed inputs cannot be replayed.
from pathlib import Path as _CleanupPath
import json as _cleanup_json
import sys as _cleanup_sys
_cleanup_root = next(p for p in _CleanupPath(__file__).resolve().parents if p.name == "implementation").parent
_cleanup_removed_inputs = ['implementation/reports/gate_evidence/track_a_data_vintage_comparison_2026-09-27.json']
if any(not (_cleanup_root / p).is_file() for p in _cleanup_removed_inputs):
    print(_cleanup_json.dumps({"status": "NOT_AVAILABLE", "reason": "GSQ-010: archived inputs removed"}))
    _cleanup_sys.exit(2)

import sys,json
from pathlib import Path
sys.path[:0]=['src','tools']
import official_pipeline as op
from investment_system.ingestion.raw_store import RawDatasetStore
from investment_system.validation.vertical_slice import run_vertical_slice_from_store
snap,_=op.load_official('2024-12-31')
a,b=[run_vertical_slice_from_store(RawDatasetStore(s),op._dt('2024-12-31'),op._dt('2025-03-31'),snap) for s in ['/tmp/track_a_run70/data/raw','/tmp/track_a_network500']]
Path('/tmp/ca_unit/dec_pinned_full.json').write_text(json.dumps(a,default=str))
Path('/tmp/ca_unit/dec_fresh_full.json').write_text(json.dumps(b,default=str))
diffs=[]
for cid in a['outcomes']:
 if a['outcomes'][cid]!=b['outcomes'].get(cid):diffs.append({'company_id':cid,'pinned':a['outcomes'][cid],'fresh':b['outcomes'].get(cid)})
r={'kind':'TRACK_A_DATA_VINTAGE_COMPARISON','same_universe':a['universe']==b['universe'],'same_selected':a['selected']==b['selected'],'same_name_errors':a['name_errors']==b['name_errors'],'pinned_return':a['equal_weight_realized'],'fresh_return':b['equal_weight_realized'],'absolute_return_difference':abs(a['equal_weight_realized']-b['equal_weight_realized']),'outcome_differences':diffs}
Path('reports/gate_evidence/track_a_data_vintage_comparison_2026-09-27.json').write_text(json.dumps(r,indent=2,default=str)+'\n')
print({k:v for k,v in r.items() if k!='outcome_differences'},'n_outcome_differences',len(diffs),flush=True)
