"""Deterministic audit outputs only; Decimal parses provider numeric tokens without rounding.
No repair, deletion, gap fill, production schema or producer grant is performed.
"""

# GSQ-010: this historical entrypoint is retired even if old paths reappear.
# Original algorithms remain below for provenance; no replay is authorized here.
import json as _cleanup_json
import sys as _cleanup_sys
print(_cleanup_json.dumps({"status": "NOT_AVAILABLE", "reason": "GSQ-010: archived inputs removed"}))
_cleanup_sys.exit(2)

from pathlib import Path
from datetime import datetime,timezone
from decimal import Decimal
import hashlib,json
ROOT=Path(__file__).resolve().parents[4]; REPO=ROOT.parent; OUT=Path(__file__).resolve().parent
OLD=ROOT/'experiments/chart-contract-v0.1/p0-prerequisites/market'
cov=json.loads((OLD/'MARKET_REFERENCE_COVERAGE.json').read_bytes())
cap=json.loads((OUT/'ACTION_ACQUISITION_PROBES_v0.3.json').read_bytes()); newmap={r['provider_symbol']:r for r in cap['rows']}
FIELDS=['open','high','low','close','volume']
def utc(x):return datetime.fromtimestamp(int(x),timezone.utc).isoformat()
def lex(x):return None if x is None else str(x)
def write(name,data):
 with (OUT/name).open('x') as h:json.dump(data,h,indent=2,allow_nan=False)
def load(path):return json.loads(path.read_bytes(),parse_float=Decimal)
rows=[]; anomalies=[]; comparisons=[]; actions=[]
for r in cov['rows']:
 sym=r['provider_symbol']; path=REPO/r['raw_path']; body=path.read_bytes(); actualhash=hashlib.sha256(body).hexdigest(); assert actualhash==r['raw_sha256'],sym
 data=load(path)['chart']['result'][0]; ts=data['timestamp']; q=data['indicators']['quote'][0]; adj=data['indicators']['adjclose'][0]['adjclose']; nr=newmap[sym]; npath=REPO/nr['raw_path']; nbody=npath.read_bytes(); assert hashlib.sha256(nbody).hexdigest()==nr['sha256']; ndata=load(npath)['chart']['result'][0]; nts=ndata['timestamp']; nq=ndata['indicators']['quote'][0]; nadj=ndata['indicators']['adjclose'][0]['adjclose']; index={t:i for i,t in enumerate(nts)}
 shape_complete=0; envelope_fail=0; closeadjdiff=0; source_null=0
 for i,t in enumerate(ts):
  vals={f:q[f][i] for f in FIELDS}; complete=all(v is not None for v in vals.values()); shape_complete+=complete
  if q['close'][i] is not None and adj[i] is not None and q['close'][i]!=adj[i]:closeadjdiff+=1
  failures=[]
  if not complete:source_null+=1; failures.append('SOURCE_NULL_OHLCV')
  else:
   if vals['high']<vals['low']:failures.append('HIGH_LT_LOW')
   if vals['open']<vals['low']:failures.append('OPEN_LT_LOW')
   if vals['open']>vals['high']:failures.append('OPEN_GT_HIGH')
   if vals['close']<vals['low']:failures.append('CLOSE_LT_LOW')
   if vals['close']>vals['high']:failures.append('CLOSE_GT_HIGH')
  if complete and failures:envelope_fail+=1
  if failures:
   ni=index.get(t); nv={f:nq[f][ni] for f in FIELDS} if ni is not None else None
   a=dict(anomaly_id=f'PR41-RAW-{sym}-{utc(t)[:10]}',provider='YAHOO_CHART',provider_symbol=sym,provider_name_hint=(data.get('meta') or {}).get('longName'),certified_security_identity=None,certified_security_status='UNBOUND_NOT_INFERRED_FROM_SYMBOL',original_raw_path=r['raw_path'],original_raw_sha256=actualhash,original_row_index=i,bar_timestamp_numeric=t,bar_timestamp_utc=utc(t),bar_date_utc=utc(t)[:10],raw_numeric_tokens={f:lex(v) for f,v in vals.items()},raw_adjclose_token=lex(adj[i]),json_pointers={f:f'/chart/result/0/indicators/quote/0/{f}/{i}' for f in FIELDS},timestamp_pointer=f'/chart/result/0/timestamp/{i}',adjclose_pointer=f'/chart/result/0/indicators/adjclose/0/adjclose/{i}',affected_fields=['open','high','low','close','volume'] if not complete else ['high','low','close'],anomaly_types=failures,deterministic_result='NOT_AVAILABLE_SOURCE_FIELDS' if not complete else 'FAIL_EXACT_OHLC_ENVELOPE',validation_rule='all OHLCV present; low <= open <= high and low <= close <= high; exact source-token Decimal comparisons; no epsilon or tolerance',cause='UNKNOWN',verified_explanation=None,source_action_same_bar_date_candidates=[cat+':'+str(key) for cat,evs in (ndata.get('events') or {}).items() for key,event in evs.items() if utc(event['date'])[:10]==utc(t)[:10]],latest_comparison_raw_path=nr['raw_path'],latest_comparison_sha256=nr['sha256'],latest_comparison_row_index=ni,latest_comparison_values={f:lex(v) for f,v in nv.items()} if nv else None,ohlcv_equal_in_two_observed_responses=(nv==vals if nv else None),historical_available_at=None,raw_preservation='UNCHANGED',downstream_candle_candidate='BLOCK_INVALID_CANDLE_NO_REPAIR' if complete else 'BLOCK_MISSING_CANDLE_NO_ZERO_FILL',diagnostic_view_candidate='ANNOTATE_ORIGINAL_VALUES_AND_EXPLICIT_ROW_STATE',series_state_candidate='DEGRADE_WITH_EXPLICIT_GAP_ONLY_IF_APPROVED_OTHERWISE_BLOCK_SERIES',derived_indicator_candidate='BLOCK_ANY_DEPENDENT_WINDOW_UNTIL_OWNER_VALIDATION',production_rule_adoption=False)
   anomalies.append(a)
 changed={f:0 for f in FIELDS+['adjclose']}; details=[]
 for i,t in enumerate(ts):
  if t not in index:continue
  j=index[t]
  for f in changed:
   ov=adj[i] if f=='adjclose' else q[f][i];nv=nadj[j] if f=='adjclose' else nq[f][j]
   if ov!=nv:
    changed[f]+=1
    if len(details)<40:details.append(dict(timestamp_utc=utc(t),field=f,old_token=lex(ov),new_token=lex(nv),old_index=i,new_index=j))
 comparisons.append(dict(provider_symbol=sym,prior_raw_sha256=actualhash,comparison_raw_sha256=nr['sha256'],prior_rows=len(ts),new_rows=len(nts),shared_timestamp_count=sum(t in index for t in ts),prior_only_timestamps=[utc(t) for t in ts if t not in index],new_only_timestamps=[utc(t) for t in nts if t not in set(ts)],different_field_counts=changed,differences_sample_max40=details,interpretation='Two current observations only; not historical vintage/availability or cause proof'))
 for cat,evs in (ndata.get('events') or {}).items():
  for key,event in evs.items():
   actions.append(dict(provider_symbol=sym,certified_security_identity=None,source_raw_path=nr['raw_path'],source_sha256=nr['sha256'],category=cat,provider_outer_key=key,provider_event_date_token=event.get('date'),provider_event_date_utc=utc(event['date']),outer_key_matches_event_date=(str(key)==str(event['date'])),provider_raw_fields={k:lex(v) if isinstance(v,(int,Decimal)) else v for k,v in event.items()},json_pointer=f'/chart/result/0/events/{cat}/{key}',available_at=None,announced_at=None,legal_effective_at=None,event_semantics='PROVIDER_DECLARED_DATE_NOT_ANNOUNCEMENT_OR_AVAILABILITY',coverage_certified=False))
 row=dict(provider_symbol=sym,certified_security_identity=None,original_raw_path=r['raw_path'],original_raw_sha256=actualhash,original_hash_verified=True,prior_rows=len(ts),complete_ohlcv_rows=shape_complete,missing_ohlcv_rows=source_null,exact_envelope_failure_rows=envelope_fail,source_ohlcv_state='READY' if not(source_null or envelope_fail) else 'PARTIAL',source_ohlcv_state_scope='SOURCE_STRUCTURAL_FACTS_ONLY_NOT_PRODUCTION_ADMISSION',source_close='READY',source_adjclose='READY',adjclose_non_null_count=sum(v is not None for v in adj),close_vs_adjclose_difference_rows=closeadjdiff,raw_unadjusted_full_ohlcv='NOT_AVAILABLE',split_dividend_adjusted_full_ohlcv='BLOCKED',source_per_field_ohlcv_basis='PARTIAL',basis_explanation='Source quote O/H/L/C/V plus source adjclose retained; no per-field transformation lineage or unadjusted pair certified',action_candidate_capture_state='PARTIAL',action_capture_sha256=nr['sha256'],action_counts=nr.get('event_counts',{}),action_request='div,splits',absence_semantics='NO_EVENTS_RETURNED_NOT_CERTIFIED_NO_ACTIONS' if not nr.get('event_counts') else 'EVENTS_RETURNED_COVERAGE_UNCERTIFIED',corporate_action_completeness='UNKNOWN',historical_action_available_at='NOT_AVAILABLE',historical_price_available_at='NOT_AVAILABLE',quote_state='UNKNOWN',explicit_marketState=data.get('meta',{}).get('marketState'),explicit_exchangeDataDelayedBy=data.get('meta',{}).get('exchangeDataDelayedBy'),product_state='NOT_ELEVATED',production_ready='BLOCKED')
 rows.append(row)
write('MARKET_BASIS_READINESS_19_v0.3.json',dict(kind='READ_ONLY_19_SYMBOL_BASIS_EVIDENCE_NOT_ADOPTION',generated_at=datetime.now(timezone.utc).isoformat(),pins=dict(chart_head='54ee254',prior_audit_baseline='8668c69070c7956cb85d1ccf8cbeb8d9d2daf5cf'),rows=rows))
write('IMMUTABLE_RAW_ANOMALIES_v0.3.json',dict(kind='EXACT_ORIGINAL_SOURCE_ANOMALIES_PRESERVED',total_original_rows=sum(r['prior_rows'] for r in rows),missing_rows=sum(r['missing_ohlcv_rows'] for r in rows),envelope_failure_rows=sum(r['exact_envelope_failure_rows'] for r in rows),rows=anomalies))
write('CURRENT_ACTION_EVENT_CANDIDATES_v0.3.json',dict(kind='VENDOR_ACTION_CANDIDATES_NOT_CERTIFIED_ACTION_LEDGER',dividend_count=sum(a['category']=='dividends' for a in actions),split_count=sum(a['category']=='splits' for a in actions),rows=actions))
write('TWO_OBSERVATIONS_COMPARISON_v0.3.json',dict(kind='NO_REPLACEMENT_NO_VINTAGE_INFERENCE',rows=comparisons))
print(json.dumps({'original_rows':sum(r['prior_rows'] for r in rows),'anomalies':len(anomalies),'dividend_candidates':sum(a['category']=='dividends' for a in actions),'split_candidates':sum(a['category']=='splits' for a in actions),'new_probe_rows':sum(x['new_rows'] for x in comparisons),'field_difference_totals':{f:sum(x['different_field_counts'][f] for x in comparisons) for f in FIELDS+['adjclose']}},indent=2))
