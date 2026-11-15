"""DC-54 owner-private reference views; no verification upgrade or public output."""
from copy import deepcopy
from decimal import Decimal
from types import SimpleNamespace
from ._private_artifacts import digest,json_bytes,MAX_BYTES
from .kis_split_evidence import assess_splits
from ..qgv import qgv_official as common
from ..qgv import v2_factors,qgv_v2

# Conservative review screen, not a split inference/adjustment rule.
JUMP_POLICY={'version':'raw-integer-jump-screen/1','new_old_ratios':['1.5','2','3','4','5','10','20'],
             'relative_tolerance':'0.08','minimum_absolute_return':'0.30','window_sessions':100}

def split_candidates(c,day):
 assessment=assess_splits(c,day)
 if assessment['block_reasons']:raise ValueError(assessment['block_reasons'][0])
 rows=[r for r in c['raw_bars'] if r['date']<=day][-100:];out=[]
 known={s['date'] for s in c['splits'] if s['date']<=day}
 ratios=[Decimal(r) for r in JUMP_POLICY['new_old_ratios']]
 for a,b in zip(rows,rows[1:]):
  if not a.get('close') or not b.get('close'):continue
  q=Decimal(b['close'])/Decimal(a['close'])
  if abs(q-1)<Decimal(JUMP_POLICY['minimum_absolute_return']) or b['date'] in known:continue
  near=min(ratios+[1/r for r in ratios],key=lambda r:abs(q/r-1))
  if abs(q/near-1)<=Decimal(JUMP_POLICY['relative_tolerance']):
   out.append(dict(date=b['date'],reason='RAW_SPLIT_LIKE_JUMP_REVIEW_REQUIRED',confirmed=False,
                   observed_close_ratio=str(q),candidate_close_ratio=str(near),policy=JUMP_POLICY['version']))
 return out

def reference_files(files,c,day):
 """Enrich saved payloads. Keep original adopted values/null reasons unchanged."""
 candidates=split_candidates(c,day)
 reasons=list(dict.fromkeys([r['reason'] for r in candidates]+[
  r['reason'] for r in c['held_ranges'] if r['from']<=day and r['to']>=c['raw_bars'][0]['date']]))
 out={}
 for path,raw in files.items():
  obj=__import__('json').loads(raw)
  if path.startswith(('chart/','technical/','measures/')):
   obj['display']=dict(state='WITHHELD' if reasons else 'AVAILABLE',
    validation_tier='UNVERIFIED_REFERENCE',label='검증 전(참고)',official=False,
    hold_reasons=reasons,split_candidates=deepcopy(candidates),screen_policy=deepcopy(JUMP_POLICY))
   if 'metrics' in obj:
    for metric in obj['metrics'].values():
     metric['validation_tier']='VERIFIED' if metric['value'] is not None else 'UNVERIFIED_REFERENCE'
     metric['reference_value']=None if reasons else metric.get('raw_value')
     metric['reference_reasons']=list(dict.fromkeys(reasons+metric.get('null_reasons',[])))
    obj['reference_count']=sum(m['reference_value'] is not None for m in obj['metrics'].values())
   elif not reasons and c['identity'].get('identity_status')=='CONFIRMED' and c['confirmed_ranges']:
    # A chart reference label never asserts per-metric acceptance.
    obj['display']['verified_metric_values_are_separate']=True
  out[path]=json_bytes(obj)
 # Changed payload bytes require fresh per-file hashes; original source pins stay.
 import hashlib,json
 for path,raw in list(out.items()):
  if path.startswith('manifests/'):
   obj=json.loads(raw);obj['reference_policy']='owner-private-reference/1'
   obj['qgv']['state']='SEPARATE_CALC23_1_REFERENCE_ADAPTER'
   for entry in obj['files']:
    b=out[entry['path']];entry.update(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
   out[path]=json_bytes(obj)
 if any(len(b)>MAX_BYTES for b in out.values()):raise ValueError('PRIVATE_ARTIFACT_TOO_LARGE')
 return out

def official_reference(payload,contracts,links,*,day,calculated_at,expected_payload_hash,expected_links_hash,expected_contract_hashes,monthends=None):
 """Same official engine/gates; only quote supplier changes. Reference, never official."""
 from .kis_price_bridge import _ts,validate_contract
 if digest(payload)!=expected_payload_hash or digest(links)!=expected_links_hash:raise ValueError('SOURCE_PIN_MISMATCH')
 if payload['calc_version']!=v2_factors.CALC_VERSION:raise ValueError('CALC_VERSION_MISMATCH')
 now=_ts(calculated_at)
 if day>now.date().isoformat() or _ts(payload['as_of'])>now:raise ValueError('INPUT_NOT_AVAILABLE')
 ctx=common.prepare(payload,now);quotes={};statuses={}
 for key,code in ctx['keys'].items():
  c=contracts.get(code);link=links.get(code)
  if c is None or link is None:statuses[key]='PRICE_NOT_AVAILABLE';continue
  if digest(c)!=expected_contract_hashes.get(code):raise ValueError('CONTRACT_PIN_MISMATCH')
  validate_contract(c)
  if c['source_query']['SYMB']!=link['symb'] or c['source_query']['EXCD']!=link['excd']:
   statuses[key]='PRICE_IDENTITY_CONFLICT';continue
  if _ts(c['collected_at'])>now:statuses[key]='PRICE_NOT_YET_AVAILABLE';continue
  if split_candidates(c,day) or any(r['from']<=day<=r['to'] for r in c['held_ranges']):
   statuses[key]='PRICE_INPUT_HELD';continue
  row=next((r for r in c['raw_bars'] if r['date']==day),None)
  if row is None or row['close'] is None:statuses[key]='PRICE_BASIS_DATE_MISSING';continue
  quotes[key]=dict(price=float(row['close']),currency=c['currency']);statuses[key]='SUPPLIED'
 supplied=SimpleNamespace(day=day,quotes=quotes,status=statuses)
 st=common.price_status(ctx,supplied,months=monthends or {})
 engine,excluded=common.engine_quotes(ctx,supplied,st,monthends or {})
 calculated=common.score(ctx,engine)
 rows={k:common.projection(v) for k,v in calculated.items()}
 detail={k:deepcopy(v['detail']) for k,v in calculated.items()}
 counts=dict(price=sum(k in engine for k in payload['records']),
  raw_any=sum(any(detail[k].get(f) is not None for f in ('ebit_yield','fcf_yield','expectation_gap')) for k in payload['records']),
  role_any=sum(any(v['score'] is not None for f,v in rows[k]['factors'].items() if f.startswith('v_')) for k in payload['records']))
 return dict(schema='kis-qgv/1',layer='OWNER_PRIVATE',calc_version=payload['calc_version'],engine_version=qgv_v2.VERSION,
  calculation_path='qgv_official.prepare/price_status/engine_quotes/score/projection',
  price_basis_date=day,calculated_at=calculated_at,financial_input_as_of=payload['as_of'],
  input_sha256=expected_payload_hash,lookup_sha256=expected_links_hash,
  display=dict(validation_tier='UNVERIFIED_REFERENCE',label='검증 전(참고)',official=False),
  share_count_basis='WEIGHTED_AVERAGE_DILUTED_PROXY_NOT_ACTUAL_OUTSTANDING',
  identity_basis='OFFICIAL_CALC_RULES_AND_PINNED_PROVIDER_LOOKUP_NOT_FIXED_SECURITY_VERIFICATION',
  rows=rows,private_raw_detail=detail,stages=counts,price_status=st,price_rows_supplied=len(engine),monthend_exclusions=excluded,
  weights=common.weights_block(),config_versions=common.config_versions_block(),
  population=sorted(payload['records']),population_sha256=digest(sorted(payload['records'])),
  coverage=dict(codes=len(payload['records']),**{a:sum(r['axes'][a]['score'] is not None for k,r in rows.items() if k in payload['records']) for a in ('Q','G','V')},
   QGV=sum(all(r['axes'][a]['score'] is not None for a in ('Q','G','V')) for k,r in rows.items() if k in payload['records']),
   engine_total_computed=sum(r['total'] is not None for k,r in rows.items() if k in payload['records'])),
  rank=None,rank_reason='PRIVATE_REFERENCE_NOT_OFFICIAL_RANK',historical_pit_proven=False,
  official_publication_replaced=False,TARGET_modified=False)
