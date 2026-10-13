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
 const finish=(status)=>{let store={},comp={};try{store=runner().readVStore(view.localStorage);comp=runner().readVComposition(view.localStorage);}catch(_){store={};comp={};}return{result:plan?S.withVScores(result,store,comp):result,capture:status};};
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
return Object.freeze({KEY,SCHEMA,CODES,MAX_DATES,readStore,merge,record,capture});
});
