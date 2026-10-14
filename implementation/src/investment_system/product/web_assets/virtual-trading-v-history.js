/* Device V history producer for the virtual-trading D-21 V slope: {date: {company: V}} in this browser only.
   Key investment.web.v1.virtual-trading-v-scores (read by VirtualTradingRunner.readVStore / readVComposition).
   Schema /2 (decision 2026-10-11): {schema:'virtual-trading-v-scores/2', scores:{date:{cid:V}}, composition:{date:{cid:key}}},
   key = sorted ids of the V factors present that day. A V with a missing core factor is NA and never stored. Entries
   written under /1 keep their value with no composition (unknown → no V slope until 20 new-format days); the first /2
   write upgrades the schema and leaves those entries as they are.
   V numbers only (0..100, 2 decimals): no price, FX, ledger or holding is ever written. Append-only: an existing
   date/company value is never overwritten, a date before the latest recorded date is never added (no backfill), at most
   MAX_DATES dates are kept (oldest dropped). The date is the latest completed SPY session of the runner's own date rules.
   Recorded in both recording and rehearsal mode: V history is independent of any ledger. Not part of the device backup
   (device-backup.js carries only explicit preferences and holdings; this is a price-derived observation log). */
(function(root,factory){const node=typeof module==='object'&&module.exports;
 const api=factory(node?()=>require('./virtual-trading-runner.js'):()=>root.VirtualTradingRunner,node?()=>require('./virtual-trading-signals.js'):()=>root.VirtualTradingSignals);
 if(node)module.exports=api;else root.VirtualTradingVHistory=api;})(typeof globalThis==='object'?globalThis:this,function(runner,signals){
'use strict';
const KEY='investment.web.v1.virtual-trading-v-scores',SCHEMA='virtual-trading-v-scores/2',LEGACY='virtual-trading-v-scores/1',MAX_DATES=400;
const COMPOSITION=/^[a-z][a-z0-9_]{0,63}(?:\+[a-z][a-z0-9_]{0,63}){0,15}$/;
// NOT_RECORDED reasons shown on S17 (labels: VirtualTrading.CODE_LABELS).
const CODES=Object.freeze(['DATE_INVALID','DATE_BEFORE_LAST_RECORDED','UNCHANGED','NO_VALUES','DEVICE_STORAGE_UNAVAILABLE','V_STORE_INVALID','SESSION_NOT_AVAILABLE','VALUATION_INPUTS_UNAVAILABLE','V_CORE_FACTOR_MISSING']);
const own=(o,k)=>o!==null&&typeof o==='object'&&Object.prototype.hasOwnProperty.call(o,k);
const object=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
const num=v=>typeof v==='number'&&Number.isFinite(v);
const day=v=>typeof v==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&+v.slice(5,7)>=1&&+v.slice(5,7)<=12&&+v.slice(8)>=1&&+v.slice(8)<=31;
const valid=(cid,v)=>own(runner().TARGETS,cid)&&num(v)&&v>=0&&v<=100;
// Stored scores: EMPTY (nothing yet), OK, INVALID (unreadable: left untouched), UNAVAILABLE (storage blocked).
function readStore(storage){
 let raw;try{raw=storage.getItem(KEY);}catch(_){return{state:'UNAVAILABLE',scores:{},composition:{}};}
 if(raw===null||raw===undefined||raw==='')return{state:'EMPTY',scores:{},composition:{}};
 try{const v=JSON.parse(raw);
  if(object(v)&&v.schema===SCHEMA&&object(v.scores)&&object(v.composition))return{state:'OK',scores:v.scores,composition:v.composition};
  // /1 entries: value kept, composition unknown (never guessed).
  if(object(v)&&v.schema===LEGACY&&object(v.scores))return{state:'OK',scores:v.scores,composition:{}};}catch(_){}
 return{state:'INVALID',scores:{},composition:{}};
}
/* Pure merge. Returns {scores, composition, added, dropped, reason}; reason is null when something was added. A value is
   added only with its composition key (compositions[cid]); without one it is not stored. */
function merge(scores,date,values,{max=MAX_DATES,compositions={},composition={}}={}){
 const base=object(scores)?scores:{},comps=object(composition)?composition:{},dates=Object.keys(base).filter(day).sort(),last=dates.length?dates[dates.length-1]:null;
 const keep=(reason)=>({scores:base,composition:comps,added:[],dropped:[],reason});
 if(!day(date))return keep('DATE_INVALID');
 if(last!==null&&date<last)return keep('DATE_BEFORE_LAST_RECORDED');
 const row=object(base[date])?{...base[date]}:{},crow=object(comps[date])?{...comps[date]}:{},added=[],r2=signals().round2,keys=object(compositions)?compositions:{};
 for(const cid of Object.keys(object(values)?values:{}).sort()){const v=values[cid],k=own(keys,cid)?keys[cid]:null;
  if(!valid(cid,v)||own(row,cid)||!(typeof k==='string'&&COMPOSITION.test(k)))continue;row[cid]=r2(v);crow[cid]=k;added.push(cid);}
 if(!added.length)return keep(Object.keys(object(values)?values:{}).length?'UNCHANGED':'NO_VALUES');
 const sorted=o=>Object.fromEntries(Object.keys(o).sort().map(c=>[c,o[c]]));
 const next={};for(const d of dates)next[d]=base[d];next[date]=sorted(row);
 const nextC={};for(const d of Object.keys(comps).filter(day))nextC[d]=comps[d];nextC[date]=sorted(crow);
 const all=Object.keys(next).sort(),limit=Number.isInteger(max)&&max>0?max:MAX_DATES,dropped=all.slice(0,Math.max(0,all.length-limit));
 for(const d of dropped){delete next[d];delete nextC[d];}
 const out={},outC={};for(const d of Object.keys(next).sort())out[d]=next[d];for(const d of Object.keys(nextC).sort())if(own(out,d))outC[d]=nextC[d];
 return{scores:out,composition:outC,added,dropped,reason:null};
}
function record(storage,date,values,compositions={},opts={}){
 const current=readStore(storage);
 if(current.state==='UNAVAILABLE')return{state:'NOT_RECORDED',reason:'DEVICE_STORAGE_UNAVAILABLE',date,added:[]};
 if(current.state==='INVALID')return{state:'NOT_RECORDED',reason:'V_STORE_INVALID',date,added:[]};
 const m=merge(current.scores,date,values,{...opts,compositions,composition:current.composition});
 if(m.reason!==null)return{state:'NOT_RECORDED',reason:m.reason,date,added:[]};
 try{storage.setItem(KEY,JSON.stringify({schema:SCHEMA,scores:m.scores,composition:m.composition}));}catch(_){return{state:'NOT_RECORDED',reason:'DEVICE_STORAGE_UNAVAILABLE',date,added:[]};}
 return{state:'RECORDED',reason:null,date,added:m.added};
}
/* Browser glue: V per company on the runner result's latest completed SPY session from that session's close (RAM) and
   the public price-free valuation inputs, appended to the store; the result's ledgers then read the updated store. */
async function capture(view,result){
 const S=signals(),plan=S.capturePlan(result);
 const finish=(status)=>{let store={},comp={};try{store=runner().readVStore(view.localStorage);comp=runner().readVComposition(view.localStorage);}catch(_){store={};comp={};}return{result:plan&&result?.snapshot_basis!=='v2'?S.withVScores(result,store,comp):result,capture:status};};
 if(!plan)return finish({state:'NOT_RECORDED',reason:'SESSION_NOT_AVAILABLE',date:null,added:[]});
 const V=view.DeviceValuation;let payload=null;
 try{payload=V?await V.load(view):null;}catch(_){payload=null;}
 if(!payload)return finish({state:'NOT_RECORDED',reason:'VALUATION_INPUTS_UNAVAILABLE',date:plan.date,added:[]});
 let values={},comps={},skipped={};try{[values,,comps,skipped]=S.vScoresFor(plan,payload,V.parameters());}catch(_){values={};comps={};skipped={};}
 // Companies whose V is NA (a missing core factor) are listed with their reason; nothing is stored for them.
 const status=record(view.localStorage,plan.date,values,comps),missing=Object.keys(skipped).sort();
 if(status.reason==='NO_VALUES'&&missing.length)status.reason='V_CORE_FACTOR_MISSING';
 return finish({...status,skipped:missing});
}
// v2 is an independent private V-score observation log. Underlying prices never enter this store.
const V2_KEY='investment.web.v2.virtual-trading-v-scores',V2_SCHEMA='virtual-trading-v2-v-scores/1';
const V2_FIELDS=['score','version','profile','composition','earnings_basis','pool_hash','parameters_version','source_as_of','observed_at'];
const v2api=()=>typeof module==='object'&&module.exports?require('./qgv-v2.js'):globalThis.QgvV2;
function exact(o,keys){return object(o)&&Object.keys(o).length===keys.length&&keys.every(k=>own(o,k));}
function easternClock(s){if(typeof s!=='string'||!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$/.test(s))return null;const ms=Date.parse(s);if(!Number.isFinite(ms))return null;const p=Object.fromEntries(new Intl.DateTimeFormat('en-CA',{timeZone:'America/New_York',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(ms).map(x=>[x.type,x.value]));return{date:p.year+'-'+p.month+'-'+p.day,minutes:Number(p.hour)*60+Number(p.minute),ms};}
function completedToday(date,source,observed){const a=easternClock(source),b=easternClock(observed);let session=false;try{const f=typeof module==='object'&&module.exports?require('./forward-validation.js'):globalThis.ForwardValidation;session=f.sessionDay(date);}catch(_){}return day(date)&&session&&a&&b&&a.date===date&&b.date===date&&b.minutes>=16*60&&a.ms<=b.ms;}
function v2Valid(date,cid,r){
 if(!exact(r,V2_FIELDS)||!valid(cid,r.score)||r.version!=='v2'||!/^qgv-v2\/(balanced|quality|growth|value)\/gate-(on|off)$/.test(r.profile)||!['NORMALIZED','REPORTED'].includes(r.earnings_basis)||!/^[0-9a-f]{64}$/.test(r.pool_hash)||r.parameters_version==='UNKNOWN'||!/^[-A-Za-z0-9_./]{1,63}$/.test(r.parameters_version)||!completedToday(date,r.source_as_of,r.observed_at))return false;
 const weights=v2api().WEIGHTS.V,parts=typeof r.composition==='string'?r.composition.split('+'):[];
 return parts.length>0&&parts.join('+')===[...new Set(parts)].sort().join('+')&&parts.every(f=>own(weights,f))&&parts.reduce((a,f)=>a+weights[f],0)>=50;
}
function readV2(storage){
 let raw;try{raw=storage.getItem(V2_KEY);}catch(_){return{state:'UNAVAILABLE',records:{}};}
 if(!raw)return{state:'EMPTY',records:{}};
 try{const p=JSON.parse(raw);if(!exact(p,['schema','records'])||p.schema!==V2_SCHEMA||!object(p.records)||Object.keys(p.records).length>MAX_DATES)throw Error();
  for(const[d,row]of Object.entries(p.records))if(!day(d)||!object(row)||!Object.keys(row).length||!Object.entries(row).every(([cid,r])=>v2Valid(d,cid,r)))throw Error();
  return{state:'OK',records:p.records};}catch(_){return{state:'INVALID',records:{}};}
}
function recordV2(storage,date,observations){
 const current=readV2(storage),keep=reason=>({state:'NOT_RECORDED',reason,date,added:[]});
 if(current.state==='UNAVAILABLE')return keep('DEVICE_STORAGE_UNAVAILABLE');if(current.state==='INVALID')return keep('V_STORE_INVALID');
 const dates=Object.keys(current.records).sort();if(!day(date))return keep('DATE_INVALID');if(dates.length&&date<dates.at(-1))return keep('DATE_BEFORE_LAST_RECORDED');
 const row={...(current.records[date]||{})},added=[];for(const[cid,r]of Object.entries(observations||{})){if(!own(row,cid)&&v2Valid(date,cid,r)){row[cid]={...r,score:signals().round2(r.score)};added.push(cid);}}
 if(!added.length)return keep('NO_VALID_V2_OBSERVATIONS');
 const records={...current.records,[date]:row},keys=Object.keys(records).sort();for(const d of keys.slice(0,Math.max(0,keys.length-MAX_DATES)))delete records[d];
 try{storage.setItem(V2_KEY,JSON.stringify({schema:V2_SCHEMA,records}));}catch(_){return keep('DEVICE_STORAGE_UNAVAILABLE');}
 return{state:'RECORDED',reason:null,date,added:added.sort()};
}
function v2Signature(r){
 // Preserve every provenance byte. Chunked ASCII hex keeps the existing engine key grammar without
 // collapsing punctuation/case in versions or truncating the full cohort hash.
 const identity=JSON.stringify([r.version,r.profile,r.composition,r.earnings_basis,r.pool_hash,r.parameters_version]);
 const hex=[...identity].map(c=>c.charCodeAt(0).toString(16).padStart(2,'0')).join(''),parts=['qgv_v2'];
 for(let i=0;i<hex.length;i+=56)parts.push('v2id_'+(i/56)+'_'+hex.slice(i,i+56));return parts.join('+');
}
function v2Values(storage,profile=null){const r=readV2(storage),scores={},composition={};if(r.state!=='OK')return{scores,composition};for(const[d,row]of Object.entries(r.records)){scores[d]={};composition[d]={};for(const[cid,o]of Object.entries(row)){if(profile&&o.profile!==profile)continue;scores[d][cid]=o.score;composition[d][cid]=v2Signature(o);}}return{scores,composition};}
function v2Comparison(storage,cid,sessions,profile=null){
 const r=readV2(storage),days=[...new Set((sessions||[]).filter(day))].sort(),date=days.at(-1),now=date?r.records[date]?.[cid]:null;
 const out={basis:'v2',state:'NOT_AVAILABLE',reason:'V2_FORWARD_V_HISTORY_NOT_AVAILABLE',current_date:date||null,current:now?.score??null,previous_date:null,previous:null};
 if(!now)return out;if(profile&&now.profile!==profile)return{...out,current:null,reason:'V_COMPOSITION_CHANGED'};const index=days.indexOf(date)-20;if(index<0)return{...out,reason:'V_HISTORY_SHORT'};
 const previousDate=days[index],past=r.records[previousDate]?.[cid];if(!past)return{...out,previous_date:previousDate,reason:'V_HISTORY_SHORT'};
 if(v2Signature(now)!==v2Signature(past))return{...out,previous_date:previousDate,reason:'V_COMPOSITION_CHANGED'};
 return{...out,state:'READY',reason:null,previous_date:previousDate,previous:past.score,profile:now.profile,composition:now.composition};
}
async function captureV2(view,result,{identities=[],publicScreens={},preset=null,gate=null,now=new Date().toISOString()}={}){
 const S=signals(),plan=S.capturePlan(result),api=v2api(),chosen=preset&&own(api.PRESETS,preset)?preset:api.DEFAULT_PRESET,profile='qgv-v2/'+chosen+'/gate-'+(gate===false?'off':'on'),finish=capture=>{const stored=v2Values(view.localStorage,profile);return{result:result?.snapshot_basis==='v2'?S.withVScores(result,stored.scores,stored.composition):result,capture};};
 const inputs=publicScreens[view.Qgv2Inputs?.FILE||'sec-qgv2.json'];if(!plan||!inputs||!completedToday(plan.date,inputs.as_of,now))return finish({state:'NOT_RECORDED',reason:'V2_SAME_SESSION_INPUTS_REQUIRED',date:plan?.date||null,added:[]});
 const quotes={},symbols=new Map(identities.map(c=>[c.company_id,c.ticker])),QS=view.QgvScores;
 if(!QS||!view.crypto?.subtle)return finish({state:'NOT_RECORDED',reason:'V2_INPUTS_NOT_AVAILABLE',date:plan.date,added:[]});
 for(const[cid,comp]of Object.entries(plan.companies)){const price=comp.closes?.[plan.date],symbol=symbols.get(cid);if(!num(price)||price<=0||!symbol)continue;for(const code of Object.keys(inputs.records)){if(code==='TARGET:'+cid||!code.startsWith('TARGET:')&&QS.symbolOf(code)===QS.symbolOf(symbol))quotes[code]={price,currency:comp.currency};}}
 const pool=Object.keys(quotes).sort().join('|'),digest=await view.crypto.subtle.digest('SHA-256',new TextEncoder().encode(pool)),poolHash=[...new Uint8Array(digest)].map(v=>v.toString(16).padStart(2,'0')).join('');
 const computed=QS.compute({identities,publicScreens,quotes,preset,gate,scoringDefault:'v2'}),observations={};
 for(const[cid,row]of Object.entries(computed.rows)){const x=row.v2;if(!valid(cid,x.v))continue;const composition=Object.keys(x.factors).filter(f=>f.startsWith('v_')&&num(x.factors[f].score)).sort().join('+');observations[cid]={score:x.v,version:'v2',profile:x.profile.id,composition,earnings_basis:x.detail.earnings_basis,pool_hash:poolHash,parameters_version:view.DcfParametersDefaults?.config_version||'UNKNOWN',source_as_of:inputs.as_of,observed_at:now};}
 return finish(recordV2(view.localStorage,plan.date,observations));
}

return Object.freeze({KEY,SCHEMA,CODES,MAX_DATES,readStore,merge,record,capture,V2_KEY,V2_SCHEMA,readV2,recordV2,v2Values,v2Comparison,captureV2});
});
