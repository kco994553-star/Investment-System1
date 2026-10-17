/* Public price-free `sec-universe-shares.json` reader. Mirrors Python require_universe_shares; prices and ranks never enter this file. `unlisted_classes` (decision 2026-10-11): per share_class_groups/v0 group with an unlisted cover class, that class's count from the valued-at listing row's own cover filing, or NOT_AVAILABLE with no count. */
(function(root,factory){const node=typeof module==='object'&&module.exports,api=factory(node?require('./private-subset.js'):root.PrivateSubset,node?require('./share-class-groups.js'):root.ShareClassGroups);if(node)module.exports=api;else root.SecUniverseShares=api;})(typeof globalThis!=='undefined'?globalThis:this,function(core,groups){
 'use strict';
 const FILENAME='sec-universe-shares.json',CONFIG_VERSION='sec-universe-shares/v0',CONFIG_STATUS='DEFAULT_V0_UNCALIBRATED',MAX=2*1024*1024;
 const STATES=['LIVE','STALE','NOT_AVAILABLE'],BASES=['SINGLE_CLASS_CONFIRMED','SHARE_CLASS_BASIS','BASIS_UNCONFIRMED'],CONCEPTS=['dei:EntityCommonStockSharesOutstanding','us-gaap:CommonStockSharesOutstanding'],FORMS=['10-K','10-K/A','10-Q','10-Q/A','20-F','20-F/A','40-F','6-K'];
 const REASONS=new Set(['IDENTITY_UNCONFIRMED','CIK_MISMATCH','INVALID_INPUT','INVALID_TIMESTAMP','AVAILABLE_AFTER_AS_OF','BASIS_UNCONFIRMED','COVER_UNCONFIRMED','COVER_FACT_MISMATCH','COVER_NOT_AVAILABLE','ACCESSION_UNCONFIRMED','MULTI_CLASS_AMBIGUOUS','SHARE_CLASS_BASIS','SHARES_NOT_AVAILABLE','INVALID_TIME_ORDER','MANIFEST_MISMATCH','SOURCE_TOO_LARGE','MIXED_SYNTHETIC_INPUT','CURRENCY_SCOPE_NOT_SUPPORTED','CIK_UNRESOLVED','NOT_COLLECTED','STALE_INPUT']);
 const TOP=['schema_version','kind','as_of','config_version','config_status','freshness_basis','stale_after_seconds','shard_count','last_shard_index','registry_sha256','code_count','state','reason_codes','records','unlisted_classes'];
 const UNLISTED_REASONS=['NOT_COLLECTED','UNLISTED_CLASS_SHARES_NOT_AVAILABLE','UNLISTED_CLASS_AMBIGUOUS','STALE_INPUT'],UNLISTED_KEYS=['cik','valued_at','accn','measurement_date','cover_sha256','classes','state','reason_codes'];
 const KEYS=['cik','listing_id','company_id','shares','measurement_date','accn','form','filed','acquired_at','concept','share_class_basis','basis_evidence','source_sha256','state','reason_codes'];
 /* Identity-conflict withdrawal (owner decision UNI-WITHDRAWN (a) 2026-10-17; Python sec_universe_shares.WITHDRAWN_REASON /
    WITHDRAWAL_KEYS / require_withdrawal): the empty row with reason IDENTITY_CONFLICT_WITHDRAWN only, no CIK, acquired_at,
    sources or values, plus detected_at (when the conflict was seen, never an acquired_at) and withdrawn_acquired_at /
    withdrawn_cik (this file's stopped row). The three keys and the reason appear on no other row. Readers never use the stopped row. */
 const WITHDRAWN_REASON='IDENTITY_CONFLICT_WITHDRAWN',WITHDRAWAL_KEYS=['detected_at','withdrawn_acquired_at','withdrawn_cik'];
 function need(x){if(!x)throw Error('SEC_UNIVERSE_SHARES_INVALID');}
 const plain=x=>x!==null&&typeof x==='object'&&!Array.isArray(x),keys=(x,k)=>plain(x)&&Object.keys(x).length===k.length&&k.every(n=>Object.hasOwn(x,n));
 const hash=x=>typeof x==='string'&&/^[0-9a-f]{64}$/.test(x),accn=x=>typeof x==='string'&&/^\d{10}-\d{2}-\d{6}$/.test(x);
 const day=x=>typeof x==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(x)&&new Date(x+'T00:00:00Z').toISOString().slice(0,10)===x;
 function clock(x){need(typeof x==='string'&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$/.test(x)&&day(x.slice(0,10)));const t=Date.parse(x);need(Number.isFinite(t));return t;}
 const utcDay=t=>new Date(t).toISOString().slice(0,10),positive=x=>typeof x==='number'&&Number.isFinite(x)&&x>0;
 const canon=x=>Array.isArray(x)?'['+x.map(canon).join(',')+']':plain(x)?'{'+Object.keys(x).sort().map(k=>JSON.stringify(k)+':'+canon(x[k])).join(',')+'}':JSON.stringify(x);
 const cikOk=x=>typeof x==='string'&&/^\d{10}$/.test(x)&&x!=='0000000000',withdrawal=r=>plain(r)&&Object.hasOwn(r,'detected_at');
 function emptyRecord(reason='NOT_COLLECTED'){return{cik:null,listing_id:null,company_id:null,shares:null,measurement_date:null,accn:null,form:null,filed:null,acquired_at:null,concept:null,share_class_basis:'BASIS_UNCONFIRMED',basis_evidence:{cover_accn:null,class_count:null,class_members:[],listing_class_member:null},source_sha256:{companyfacts:null,submissions:null,cover:null},state:'NOT_AVAILABLE',reason_codes:[reason]};}
 /* One withdrawal row's own keys (mirrors Python require_withdrawal). */
 function withdrawn(r,cut,empty){need(keys(r,Object.keys(empty()).concat(WITHDRAWAL_KEYS))&&canon(Object.fromEntries(Object.entries(r).filter(([k])=>!WITHDRAWAL_KEYS.includes(k))))===canon(empty(WITHDRAWN_REASON)));const detected=clock(r.detected_at);need(detected<=cut&&clock(r.withdrawn_acquired_at)<=detected&&cikOk(r.withdrawn_cik));}
 function record(code,r,cut,ttl){
  const w=withdrawal(r);if(w)withdrawn(r,cut,emptyRecord);need(keys(r,w?KEYS.concat(WITHDRAWAL_KEYS):KEYS));const at=code.indexOf(':');need(at>0);const venue=code.slice(0,at),symbol=code.slice(at+1).replaceAll('.','-'),mic={NASDAQ:'XNAS',NYSE:'XNYS'}[venue];
  need(r.cik===null||typeof r.cik==='string'&&/^\d{10}$/.test(r.cik)&&r.cik!=='0000000000');need(r.listing_id===null||mic&&r.cik!==null&&r.listing_id===mic+':'+symbol+':'+r.cik);
  need(r.company_id===null||typeof r.company_id==='string'&&/^[a-z0-9_]{1,64}$/.test(r.company_id));need((r.listing_id===null)===(r.company_id===null));need(r.shares===null||positive(r.shares));
  for(const k of ['measurement_date','filed'])need(r[k]===null||day(r[k]));need(r.accn===null||accn(r.accn));need(r.form===null||FORMS.includes(r.form));need(r.concept===null||CONCEPTS.includes(r.concept));
  if(r.acquired_at!==null)need(clock(r.acquired_at)<=cut);need(BASES.includes(r.share_class_basis)&&STATES.includes(r.state));
  const e=r.basis_evidence;need(keys(e,['cover_accn','class_count','class_members','listing_class_member']));need(e.cover_accn===null||accn(e.cover_accn));const m=e.class_members;
  need(Array.isArray(m)&&m.length<=16&&m.every(x=>typeof x==='string'&&/^[A-Za-z][A-Za-z0-9_]{0,127}$/.test(x))&&JSON.stringify(m)===JSON.stringify([...new Set(m)].sort()));
  need(e.class_count===null&&!m.length||Number.isInteger(e.class_count)&&e.class_count===m.length);need(e.listing_class_member===null||m.includes(e.listing_class_member));
  const h=r.source_sha256;need(keys(h,['companyfacts','submissions','cover'])&&Object.values(h).every(v=>v===null||hash(v)));
  const reasons=r.reason_codes;need(Array.isArray(reasons)&&reasons.length<=4&&new Set(reasons).size===reasons.length&&reasons.every(x=>REASONS.has(x)||w&&x===WITHDRAWN_REASON));
  const filing=['measurement_date','accn','form','filed','concept'];need(r.listing_id===null||r.acquired_at!==null&&h.companyfacts&&h.submissions);
  if(r.shares===null){need(r.state==='NOT_AVAILABLE'&&reasons.length&&filing.every(k=>r[k]===null)&&r.share_class_basis==='BASIS_UNCONFIRMED');}
  else{need(['cik','listing_id','acquired_at',...filing].every(k=>r[k]!==null)&&h.companyfacts&&h.submissions);const acquired=clock(r.acquired_at);need(r.measurement_date<=r.filed&&r.filed<=utcDay(acquired));const fresh=cut-acquired<=ttl*1000;need(r.state===(fresh?'LIVE':'STALE')&&reasons.includes('STALE_INPUT')===!fresh);}
  if(r.share_class_basis==='SINGLE_CLASS_CONFIRMED')need(h.cover&&e.cover_accn===r.accn&&m.length<=1&&!reasons.includes('SHARE_CLASS_BASIS'));
  else if(r.share_class_basis==='SHARE_CLASS_BASIS')need(h.cover&&e.cover_accn===r.accn&&m.length>=2&&e.listing_class_member!==null&&reasons.includes('SHARE_CLASS_BASIS')&&r.concept===CONCEPTS[0]);
  else need(reasons.some(x=>x!=='STALE_INPUT')&&!reasons.includes('SHARE_CLASS_BASIS'));
  return r.state;
 }
 /* One `unlisted_classes` entry (mirrors Python _unlisted_entry): bound to the valued-at row's cover filing, or NOT_AVAILABLE with no count. */
 function unlisted(group,e,records){
  need(keys(e,UNLISTED_KEYS)&&e.cik===group.cik&&e.valued_at===group.unlisted.valued_at);const reasons=e.reason_codes,classes=e.classes;
  need(Array.isArray(reasons)&&reasons.length<=4&&new Set(reasons).size===reasons.length&&reasons.every(x=>UNLISTED_REASONS.includes(x))&&Array.isArray(classes)&&classes.length<=15);
  if(!classes.length){need(e.state==='NOT_AVAILABLE'&&reasons.length&&!reasons.includes('STALE_INPUT')&&e.accn===null&&e.measurement_date===null&&e.cover_sha256===null);return e.state;}
  const r=records[e.valued_at],ev=r.basis_evidence;need(r.share_class_basis==='SHARE_CLASS_BASIS'&&r.shares!==null&&r.cik===e.cik&&hash(e.cover_sha256)&&e.cover_sha256===r.source_sha256.cover&&e.accn===r.accn&&e.measurement_date===r.measurement_date);
  need(e.state===r.state&&JSON.stringify(reasons)===JSON.stringify(r.state==='STALE'?['STALE_INPUT']:[]));
  const names=classes.map(c=>{need(keys(c,['class_member','shares'])&&typeof c.class_member==='string'&&ev.class_members.includes(c.class_member)&&c.class_member!==ev.listing_class_member&&positive(c.shares));return c.class_member;});
  need(JSON.stringify(names)===JSON.stringify([...new Set(names)].sort())&&names.length<ev.class_members.length);
  /* A class listed by any group row from the same cover filing is not unlisted. */
  const listed=group.codes.map(c=>records[c]).filter(x=>x&&x.share_class_basis==='SHARE_CLASS_BASIS'&&x.accn===e.accn).map(x=>x.basis_evidence.listing_class_member);need(!names.some(n=>listed.includes(n)));return e.state;
 }
 function validate(p){
  try{
   need(keys(p,TOP)&&p.schema_version===1&&p.kind==='SEC_UNIVERSE_SHARES'&&p.config_version===CONFIG_VERSION&&p.config_status===CONFIG_STATUS&&p.freshness_basis==='SOURCE_ACQUISITION');const cut=clock(p.as_of),ttl=p.stale_after_seconds;
   need(Number.isInteger(ttl)&&ttl>0&&ttl<=366*86400&&Number.isInteger(p.shard_count)&&p.shard_count>=1&&p.shard_count<=366&&(p.last_shard_index===null||Number.isInteger(p.last_shard_index)&&p.last_shard_index>=0&&p.last_shard_index<p.shard_count)&&(p.registry_sha256===null||hash(p.registry_sha256)));
   const codes=plain(p.records)?Object.keys(p.records):[];need(codes.length===504&&p.code_count===504&&codes.every(c=>/^[A-Z]{2,8}:[A-Z0-9][A-Z0-9.\-]{0,15}$/.test(c)));
   const states=codes.map(c=>record(c,p.records[c],cut,ttl)),state=states.includes('LIVE')?'LIVE':states.includes('STALE')?'STALE':'NOT_AVAILABLE';need(p.state===state);
   const ids=Object.keys(groups.UNLISTED);need(plain(p.unlisted_classes)&&Object.keys(p.unlisted_classes).length===ids.length&&ids.every(id=>Object.hasOwn(p.unlisted_classes,id)&&unlisted(groups.UNLISTED[id],p.unlisted_classes[id],p.records)));
   need(Array.isArray(p.reason_codes)&&new Set(p.reason_codes).size===p.reason_codes.length&&p.reason_codes.every(x=>['STALE_INPUT','NO_ELIGIBLE_INPUT'].includes(x)));return p;
  }catch(_){throw Error('SEC_UNIVERSE_SHARES_INVALID');}
 }
 /* Device-time freshness from each row's own acquired_at (mirrors Python restate). Values never change. */
 function restate(r,now,ttl){const reasons=r.reason_codes.filter(x=>x!=='STALE_INPUT');if(r.shares===null)return Object.freeze({...r,state:'NOT_AVAILABLE',reason_codes:Object.freeze(reasons.length?reasons:['SHARES_NOT_AVAILABLE'])});const fresh=Date.parse(now)-Date.parse(r.acquired_at)<=ttl*1000;return Object.freeze({...r,state:fresh?'LIVE':'STALE',reason_codes:Object.freeze(fresh?reasons:[...reasons,'STALE_INPUT'])});}
 /* Unlisted entry freshness mirrors its restated valued-at row (mirrors Python restate_unlisted). */
 function restateUnlisted(e,row){const deep=x=>{if(x&&typeof x==='object'){Object.values(x).forEach(deep);Object.freeze(x);}return x;},copy=JSON.parse(JSON.stringify(e));if(!copy.classes.length)return deep(copy);return deep({...copy,state:row.state,reason_codes:row.state==='STALE'?['STALE_INPUT']:[]});}
 function toInputs(payload,{now=new Date().toISOString(),synthetic=false}={}){
  validate(payload);const identityLookup={},publicShares={},unlistedClasses={};
  for(const [code,r] of Object.entries(payload.records)){const row=restate(r,now,payload.stale_after_seconds),seed=core.publicListingSeed(code,row,{synthetic});publicShares[code]=row;if(seed)identityLookup[code]=seed;}
  for(const [id,e] of Object.entries(payload.unlisted_classes))unlistedClasses[id]=restateUnlisted(e,publicShares[e.valued_at]);
  return Object.freeze({identityLookup:Object.freeze(identityLookup),publicShares:Object.freeze(publicShares),unlistedClasses:Object.freeze(unlistedClasses),as_of:payload.as_of,config_version:payload.config_version,config_status:payload.config_status,state:payload.state});
 }
 async function loadInputs(view,{signal,now}={}){
  const response=await view.fetch(FILENAME,{cache:'no-cache',signal,headers:{Accept:'application/json'}});if(response.status===404)return null;if(!response.ok)throw Error('SEC_UNIVERSE_SHARES_UNAVAILABLE');
  const text=await response.text();if(new TextEncoder().encode(text).length>MAX)throw Error('SEC_UNIVERSE_SHARES_INVALID');let payload;try{payload=JSON.parse(text);}catch(_){throw Error('SEC_UNIVERSE_SHARES_INVALID');}
  return toInputs(payload,{now:now||new Date().toISOString()});
 }
 return Object.freeze({FILENAME,CONFIG_STATUS,WITHDRAWN_REASON,validate,restate,toInputs,loadInputs});
});
