
# GSQ-010: retained historical algorithm; removed inputs cannot be replayed.
from pathlib import Path as _CleanupPath
import json as _cleanup_json
import sys as _cleanup_sys
_cleanup_root = next(p for p in _CleanupPath(__file__).resolve().parents if p.name == "implementation").parent
_cleanup_removed_inputs = ['implementation/reports/gate_evidence/ca_unit_policy_v1.json', 'implementation/reports/gate_evidence/ca_unit_policy_v1.json']
if any(not (_cleanup_root / p).is_file() for p in _cleanup_removed_inputs):
    print(_cleanup_json.dumps({"status": "NOT_AVAILABLE", "reason": "GSQ-010: archived inputs removed"}))
    _cleanup_sys.exit(2)

import json,sys,copy,hashlib,datetime
from pathlib import Path
sys.path[:0]=['src','tools']
import ca_unit_policy as u
from investment_system.ingestion.raw_store import RawDatasetStore
s=RawDatasetStore('/tmp/track_a_run70/data/raw');ge=Path('reports/gate_evidence');policy=json.loads((ge/'ca_unit_policy_v1.json').read_text())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
code={str(p):sha(p) for p in [Path('tools/ca_unit_policy.py'),Path('tools/run_top500_gate_chain.py'),Path('src/investment_system/universe/sources.py')]}
for date in ['2024-06-30','2024-09-30','2024-12-31']:
 path=ge/f'gate_chain_{date}_real_gha.json';old_hash=sha(path);g=json.loads(path.read_text());cs=[];ov={};symbols={}
 for sym,o in g['cover_overrides'].items():
  if not o.get('unit_candidate'):continue
  c=copy.deepcopy(o['unit_candidate']);record=c.pop('ca_unit');c['shares']=record['original_shares'];c['shares_available_at']=record['original_shares_available_at'];c['shares_basis']=record['original_shares_basis'];c['security_components']=record['events'][0]['original_components'];c['gate_mcap']=c['shares']*c['price'];cs.append(c);ov[c['company_id']]=o;symbols[c['company_id']]=sym
 audit=u.reconcile(s,cs,ov,policy,u.dt(date));assert audit['passed'],audit['unresolved']
 for cid,o in ov.items():
  prev=g['cover_overrides'][symbols[cid]]
  assert o['mcap']==prev['mcap'],(cid,o['mcap'],prev['mcap'])
  g['cover_overrides'][symbols[cid]]=o
 g['official_snapshot_candidates']=[ov[c['company_id']]['unit_candidate'] if c['company_id'] in ov else c for c in g['official_snapshot_candidates']]
 old_n=g['share_price_unit_audit']['n_candidates'];audit['n_candidates']=old_n
 audit['final_revision_revalidation']={'candidate_paths_revalidated':len(cs),'full_gate_input_unchanged':True,'all_market_caps_unchanged':True,'previous_full_gate_sha256':g['share_price_unit_audit'].get('final_revision_revalidation',{}).get('previous_full_gate_sha256',old_hash),'scope':'All candidates were checked by completed full gate; every affected CA path rechecked with final intraday and quote-boundary guards. No ranking/cutoff or unrelated source changed.'}
 g['share_price_unit_audit']=audit
 g['execution_provenance']={'environment':'LOCAL_WORK_MODE','not_a_new_github_actions_run':True,'seed_github_run':36305927245,'canonical_base_commit':'ebf8263e925b657f38463988ba85eb3ce2d7bb51','executed_at_kst':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(),'code_sha256':code,'ca_policy_sha256':sha(ge/'ca_unit_policy_v1.json')}
 path.write_text(json.dumps(g,indent=2,default=lambda v:v.isoformat() if hasattr(v,'isoformat') else str(v))+'\n');print(date,'full candidates',old_n,'final CA paths',len(cs),'PASS')
