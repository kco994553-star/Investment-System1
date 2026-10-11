/* Public price-free `sec-universe-qg.json` reader (user queue 2.1). Mirrors Python universe/sec_universe_qg.require_universe_qg; JS==Python vectors: tests/fixtures/sec_universe_qg_vectors_v1.json. Per Universe504 code: the 13 Q/G factor scores from the TARGET sec-qg-factors path (0-100 or null = NOT_AVAILABLE, never 0), the row's own SEC acquisition time and hashes. No V, price, rank or weights here; S06 display is a later task. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.SecUniverseQg=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
 'use strict';
 const FILENAME='sec-universe-qg.json',KIND='SEC_UNIVERSE_QG',CONFIG_VERSION='sec-universe-shares/v0',CONFIG_STATUS='DEFAULT_V0_UNCALIBRATED',METHOD_STATUS='PROVISIONAL_UNCALIBRATED',AVAILABILITY_BASIS='OBSERVED_CAPTURE_ONLY',MAX=2*1024*1024,CODE_COUNT=504;
 const FACTORS=Object.freeze(['competitive_advantage','eps_fcf_per_share_growth','excess_growth_vs_industry','fcf_quality','financial_health','growth_durability','growth_efficiency','management_quality','margin_quality','market_position','next_3_5y_growth','revenue_growth','roic_wacc']);
 const STATES=['LIVE','STALE','NOT_AVAILABLE'],REASONS=['NOT_COLLECTED','CIK_UNRESOLVED','INVALID_INPUT','M1_NOT_AVAILABLE','UNRESOLVED_CURRENT_FACT_AMBIGUITY','QG_NOT_AVAILABLE','STALE_INPUT'],TOP_REASONS=['STALE_INPUT','NO_ELIGIBLE_INPUT'];
 const TOP=['schema_version','kind','as_of','config_version','config_status','method_status','availability_basis','freshness_basis','stale_after_seconds','shard_count','last_shard_index','registry_sha256','code_count','state','reason_codes','records'];
 const KEYS=['cik','acquired_at','source_sha256','factors','state','reason_codes'];
 function need(x){if(!x)throw Error('SEC_UNIVERSE_QG_INVALID');}
 const plain=x=>x!==null&&typeof x==='object'&&!Array.isArray(x),keys=(x,k)=>plain(x)&&Object.keys(x).length===k.length&&k.every(n=>Object.hasOwn(x,n));
 const hash=x=>typeof x==='string'&&/^[0-9a-f]{64}$/.test(x),score=x=>typeof x==='number'&&Number.isFinite(x)&&x>=0&&x<=100;
 const day=x=>typeof x==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(x)&&new Date(x+'T00:00:00Z').toISOString().slice(0,10)===x;
 function clock(x){need(typeof x==='string'&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$/.test(x)&&day(x.slice(0,10)));const t=Date.parse(x);need(Number.isFinite(t));return t;}
 const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
 /* One row (mirrors Python _record). A scored factor shares the row's LIVE/STALE state; a row without any score is NOT_AVAILABLE with a fixed reason. */
 function record(r,cut,ttl){
  need(keys(r,KEYS));need(r.cik===null||typeof r.cik==='string'&&/^\d{10}$/.test(r.cik)&&r.cik!=='0000000000');
  const h=r.source_sha256;need(keys(h,['companyfacts','submissions'])&&Object.values(h).every(v=>v===null||hash(v)));
  if(r.acquired_at===null)need(h.companyfacts===null&&h.submissions===null);else need(clock(r.acquired_at)<=cut&&r.cik!==null&&h.companyfacts&&h.submissions);
  need(STATES.includes(r.state));const reasons=r.reason_codes;
  need(Array.isArray(reasons)&&reasons.length<=4&&new Set(reasons).size===reasons.length&&reasons.every(x=>REASONS.includes(x)));
  const f=r.factors;need(keys(f,FACTORS)&&FACTORS.every(k=>f[k]===null||score(f[k])));
  if(!FACTORS.some(k=>f[k]!==null))need(r.state==='NOT_AVAILABLE'&&reasons.length&&!reasons.includes('STALE_INPUT'));
  else{need(r.acquired_at!==null);const fresh=cut-clock(r.acquired_at)<=ttl*1000;need(r.state===(fresh?'LIVE':'STALE')&&same(reasons,fresh?[]:['STALE_INPUT']));}
  return r.state;
 }
 function validate(p){
  try{
   need(keys(p,TOP)&&p.schema_version===1&&p.kind===KIND&&p.config_version===CONFIG_VERSION&&p.config_status===CONFIG_STATUS&&p.method_status===METHOD_STATUS&&p.availability_basis===AVAILABILITY_BASIS&&p.freshness_basis==='SOURCE_ACQUISITION');
   const cut=clock(p.as_of),ttl=p.stale_after_seconds;
   need(Number.isInteger(ttl)&&ttl>0&&ttl<=366*86400&&Number.isInteger(p.shard_count)&&p.shard_count>=1&&p.shard_count<=366&&(p.last_shard_index===null||Number.isInteger(p.last_shard_index)&&p.last_shard_index>=0&&p.last_shard_index<p.shard_count)&&(p.registry_sha256===null||hash(p.registry_sha256)));
   const codes=plain(p.records)?Object.keys(p.records):[];need(codes.length===CODE_COUNT&&p.code_count===CODE_COUNT&&codes.every(c=>/^[A-Z]{2,8}:[A-Z0-9][A-Z0-9.\-]{0,15}$/.test(c)));
   const states=codes.map(c=>record(p.records[c],cut,ttl)),state=states.includes('LIVE')?'LIVE':states.includes('STALE')?'STALE':'NOT_AVAILABLE';need(p.state===state);
   need(Array.isArray(p.reason_codes)&&new Set(p.reason_codes).size===p.reason_codes.length&&p.reason_codes.every(x=>TOP_REASONS.includes(x)));return p;
  }catch(_){throw Error('SEC_UNIVERSE_QG_INVALID');}
 }
 function emptyRecord(reason='NOT_COLLECTED'){return{cik:null,acquired_at:null,source_sha256:{companyfacts:null,submissions:null},factors:Object.fromEntries(FACTORS.map(k=>[k,null])),state:'NOT_AVAILABLE',reason_codes:[reason]};}
 const deep=x=>{if(x&&typeof x==='object'){Object.values(x).forEach(deep);Object.freeze(x);}return x;};
 /* Device-time freshness from the row's own acquired_at (mirrors Python restate). Scores never change. */
 function restate(r,now,ttl){const copy=JSON.parse(JSON.stringify(r)),reasons=copy.reason_codes.filter(x=>x!=='STALE_INPUT');if(!FACTORS.some(k=>copy.factors[k]!==null))return deep({...copy,state:'NOT_AVAILABLE',reason_codes:reasons.length?reasons:['QG_NOT_AVAILABLE']});const fresh=Date.parse(now)-Date.parse(copy.acquired_at)<=ttl*1000;return deep({...copy,state:fresh?'LIVE':'STALE',reason_codes:fresh?[]:['STALE_INPUT']});}
 /* The TARGET sec-qg-factors.json row shape ({state, factors:{id:{score,state}}}) for readers already written against it. */
 function targetRow(r){return deep({state:r.state,factors:Object.fromEntries(FACTORS.map(k=>[k,{score:r.factors[k],state:r.factors[k]===null?'NOT_AVAILABLE':r.state}]))});}
 function toInputs(payload,{now=new Date().toISOString()}={}){
  validate(payload);const records={};for(const [code,r] of Object.entries(payload.records))records[code]=restate(r,now,payload.stale_after_seconds);
  const scored=Object.values(records).filter(r=>r.state!=='NOT_AVAILABLE').length;
  return Object.freeze({records:Object.freeze(records),scored_codes:scored,as_of:payload.as_of,config_version:payload.config_version,config_status:payload.config_status,method_status:payload.method_status,state:scored?(Object.values(records).some(r=>r.state==='LIVE')?'LIVE':'STALE'):'NOT_AVAILABLE'});
 }
 /* Minimal "data available" read: 404 -> null (not published yet), invalid -> fail closed. No storage writes. */
 async function loadInputs(view,{signal,now}={}){
  const response=await view.fetch(FILENAME,{cache:'no-cache',signal,headers:{Accept:'application/json'}});if(response.status===404)return null;if(!response.ok)throw Error('SEC_UNIVERSE_QG_UNAVAILABLE');
  const text=await response.text();if(new TextEncoder().encode(text).length>MAX)throw Error('SEC_UNIVERSE_QG_INVALID');let payload;try{payload=JSON.parse(text);}catch(_){throw Error('SEC_UNIVERSE_QG_INVALID');}
  return toInputs(payload,{now:now||new Date().toISOString()});
 }
 return Object.freeze({FILENAME,FACTORS,CONFIG_STATUS,validate,emptyRecord,restate,targetRow,toInputs,loadInputs});
});
