/* Public price-free `sec-universe-shares.json` reader. Mirrors Python require_universe_shares; prices and ranks never enter this file. */
(function(root,factory){const api=factory(typeof module==='object'&&module.exports?require('./private-subset.js'):root.PrivateSubset);if(typeof module==='object'&&module.exports)module.exports=api;else root.SecUniverseShares=api;})(typeof globalThis!=='undefined'?globalThis:this,function(core){
 'use strict';
 const FILENAME='sec-universe-shares.json',CONFIG_VERSION='sec-universe-shares/v0',CONFIG_STATUS='DEFAULT_V0_UNCALIBRATED',MAX=2*1024*1024;
 const STATES=['LIVE','STALE','NOT_AVAILABLE'],BASES=['SINGLE_CLASS_CONFIRMED','SHARE_CLASS_BASIS','BASIS_UNCONFIRMED'],CONCEPTS=['dei:EntityCommonStockSharesOutstanding','us-gaap:CommonStockSharesOutstanding'],FORMS=['10-K','10-K/A','10-Q','10-Q/A','20-F','20-F/A','40-F','6-K'];
 const REASONS=new Set(['IDENTITY_UNCONFIRMED','CIK_MISMATCH','INVALID_INPUT','INVALID_TIMESTAMP','AVAILABLE_AFTER_AS_OF','BASIS_UNCONFIRMED','COVER_UNCONFIRMED','COVER_FACT_MISMATCH','COVER_NOT_AVAILABLE','ACCESSION_UNCONFIRMED','MULTI_CLASS_AMBIGUOUS','SHARE_CLASS_BASIS','SHARES_NOT_AVAILABLE','INVALID_TIME_ORDER','MANIFEST_MISMATCH','SOURCE_TOO_LARGE','MIXED_SYNTHETIC_INPUT','CURRENCY_SCOPE_NOT_SUPPORTED','CIK_UNRESOLVED','NOT_COLLECTED','STALE_INPUT']);
 const TOP=['schema_version','kind','as_of','config_version','config_status','freshness_basis','stale_after_seconds','shard_count','last_shard_index','registry_sha256','code_count','state','reason_codes','records'];
 const KEYS=['cik','listing_id','company_id','shares','measurement_date','accn','form','filed','acquired_at','concept','share_class_basis','basis_evidence','source_sha256','state','reason_codes'];
 function need(x){if(!x)throw Error('SEC_UNIVERSE_SHARES_INVALID');}
 const plain=x=>x!==null&&typeof x==='object'&&!Array.isArray(x),keys=(x,k)=>plain(x)&&Object.keys(x).length===k.length&&k.every(n=>Object.hasOwn(x,n));
 const hash=x=>typeof x==='string'&&/^[0-9a-f]{64}$/.test(x),accn=x=>typeof x==='string'&&/^\d{10}-\d{2}-\d{6}$/.test(x);
 const day=x=>typeof x==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(x)&&new Date(x+'T00:00:00Z').toISOString().slice(0,10)===x;
 function clock(x){need(typeof x==='string'&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$/.test(x)&&day(x.slice(0,10)));const t=Date.parse(x);need(Number.isFinite(t));return t;}
 const utcDay=t=>new Date(t).toISOString().slice(0,10),positive=x=>typeof x==='number'&&Number.isFinite(x)&&x>0;
 function record(code,r,cut,ttl){
  need(keys(r,KEYS));const at=code.indexOf(':');need(at>0);const venue=code.slice(0,at),symbol=code.slice(at+1).replaceAll('.','-'),mic={NASDAQ:'XNAS',NYSE:'XNYS'}[venue];
  need(r.cik===null||typeof r.cik==='string'&&/^\d{10}$/.test(r.cik)&&r.cik!=='0000000000');need(r.listing_id===null||mic&&r.cik!==null&&r.listing_id===mic+':'+symbol+':'+r.cik);
  need(r.company_id===null||typeof r.company_id==='string'&&/^[a-z0-9_]{1,64}$/.test(r.company_id));need((r.listing_id===null)===(r.company_id===null));need(r.shares===null||positive(r.shares));
  for(const k of ['measurement_date','filed'])need(r[k]===null||day(r[k]));need(r.accn===null||accn(r.accn));need(r.form===null||FORMS.includes(r.form));need(r.concept===null||CONCEPTS.includes(r.concept));
  if(r.acquired_at!==null)need(clock(r.acquired_at)<=cut);need(BASES.includes(r.share_class_basis)&&STATES.includes(r.state));
  const e=r.basis_evidence;need(keys(e,['cover_accn','class_count','class_members','listing_class_member']));need(e.cover_accn===null||accn(e.cover_accn));const m=e.class_members;
  need(Array.isArray(m)&&m.length<=16&&m.every(x=>typeof x==='string'&&/^[A-Za-z][A-Za-z0-9_]{0,127}$/.test(x))&&JSON.stringify(m)===JSON.stringify([...new Set(m)].sort()));
  need(e.class_count===null&&!m.length||Number.isInteger(e.class_count)&&e.class_count===m.length);need(e.listing_class_member===null||m.includes(e.listing_class_member));
  const h=r.source_sha256;need(keys(h,['companyfacts','submissions','cover'])&&Object.values(h).every(v=>v===null||hash(v)));
  const reasons=r.reason_codes;need(Array.isArray(reasons)&&reasons.length<=4&&new Set(reasons).size===reasons.length&&reasons.every(x=>REASONS.has(x)));
  const filing=['measurement_date','accn','form','filed','concept'];need(r.listing_id===null||r.acquired_at!==null&&h.companyfacts&&h.submissions);
  if(r.shares===null){need(r.state==='NOT_AVAILABLE'&&reasons.length&&filing.every(k=>r[k]===null)&&r.share_class_basis==='BASIS_UNCONFIRMED');}
  else{need(['cik','listing_id','acquired_at',...filing].every(k=>r[k]!==null)&&h.companyfacts&&h.submissions);const acquired=clock(r.acquired_at);need(r.measurement_date<=r.filed&&r.filed<=utcDay(acquired));const fresh=cut-acquired<=ttl*1000;need(r.state===(fresh?'LIVE':'STALE')&&reasons.includes('STALE_INPUT')===!fresh);}
  if(r.share_class_basis==='SINGLE_CLASS_CONFIRMED')need(h.cover&&e.cover_accn===r.accn&&m.length<=1&&!reasons.includes('SHARE_CLASS_BASIS'));
  else if(r.share_class_basis==='SHARE_CLASS_BASIS')need(h.cover&&e.cover_accn===r.accn&&m.length>=2&&e.listing_class_member!==null&&reasons.includes('SHARE_CLASS_BASIS')&&r.concept===CONCEPTS[0]);
  else need(reasons.some(x=>x!=='STALE_INPUT')&&!reasons.includes('SHARE_CLASS_BASIS'));
  return r.state;
 }
 function validate(p){
  try{
   need(keys(p,TOP)&&p.schema_version===1&&p.kind==='SEC_UNIVERSE_SHARES'&&p.config_version===CONFIG_VERSION&&p.config_status===CONFIG_STATUS&&p.freshness_basis==='SOURCE_ACQUISITION');const cut=clock(p.as_of),ttl=p.stale_after_seconds;
   need(Number.isInteger(ttl)&&ttl>0&&ttl<=366*86400&&Number.isInteger(p.shard_count)&&p.shard_count>=1&&p.shard_count<=366&&(p.last_shard_index===null||Number.isInteger(p.last_shard_index)&&p.last_shard_index>=0&&p.last_shard_index<p.shard_count)&&(p.registry_sha256===null||hash(p.registry_sha256)));
   const codes=plain(p.records)?Object.keys(p.records):[];need(codes.length===504&&p.code_count===504&&codes.every(c=>/^[A-Z]{2,8}:[A-Z0-9][A-Z0-9.\-]{0,15}$/.test(c)));
   const states=codes.map(c=>record(c,p.records[c],cut,ttl)),state=states.includes('LIVE')?'LIVE':states.includes('STALE')?'STALE':'NOT_AVAILABLE';need(p.state===state);
   need(Array.isArray(p.reason_codes)&&new Set(p.reason_codes).size===p.reason_codes.length&&p.reason_codes.every(x=>['STALE_INPUT','NO_ELIGIBLE_INPUT'].includes(x)));return p;
  }catch(_){throw Error('SEC_UNIVERSE_SHARES_INVALID');}
 }
 /* Device-time freshness from each row's own acquired_at (mirrors Python restate). Values never change. */
 function restate(r,now,ttl){const reasons=r.reason_codes.filter(x=>x!=='STALE_INPUT');if(r.shares===null)return Object.freeze({...r,state:'NOT_AVAILABLE',reason_codes:Object.freeze(reasons.length?reasons:['SHARES_NOT_AVAILABLE'])});const fresh=Date.parse(now)-Date.parse(r.acquired_at)<=ttl*1000;return Object.freeze({...r,state:fresh?'LIVE':'STALE',reason_codes:Object.freeze(fresh?reasons:[...reasons,'STALE_INPUT'])});}
 function toInputs(payload,{now=new Date().toISOString(),synthetic=false}={}){
  validate(payload);const identityLookup={},publicShares={};
  for(const [code,r] of Object.entries(payload.records)){const row=restate(r,now,payload.stale_after_seconds),seed=core.publicListingSeed(code,row,{synthetic});publicShares[code]=row;if(seed)identityLookup[code]=seed;}
  return Object.freeze({identityLookup:Object.freeze(identityLookup),publicShares:Object.freeze(publicShares),as_of:payload.as_of,config_version:payload.config_version,config_status:payload.config_status,state:payload.state});
 }
 async function loadInputs(view,{signal,now}={}){
  const response=await view.fetch(FILENAME,{cache:'no-cache',signal,headers:{Accept:'application/json'}});if(response.status===404)return null;if(!response.ok)throw Error('SEC_UNIVERSE_SHARES_UNAVAILABLE');
  const text=await response.text();if(new TextEncoder().encode(text).length>MAX)throw Error('SEC_UNIVERSE_SHARES_INVALID');let payload;try{payload=JSON.parse(text);}catch(_){throw Error('SEC_UNIVERSE_SHARES_INVALID');}
  return toInputs(payload,{now:now||new Date().toISOString()});
 }
 return Object.freeze({FILENAME,CONFIG_STATUS,validate,restate,toInputs,loadInputs});
});
