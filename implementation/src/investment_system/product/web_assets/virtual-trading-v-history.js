/* Device V history producer for the virtual-trading D-21 V slope: {date: {company: V}} in this browser only.
   Key investment.web.v1.virtual-trading-v-scores (read by VirtualTradingRunner.readVStore), schema virtual-trading-v-scores/1.
   V numbers only (0..100, 2 decimals): no price, FX, ledger or holding is ever written. Append-only: an existing
   date/company value is never overwritten, a date before the latest recorded date is never added (no backfill), at most
   MAX_DATES dates are kept (oldest dropped). The date is the latest completed SPY session of the runner's own date rules.
   Recorded in both recording and rehearsal mode: V history is independent of any ledger. Not part of the device backup
   (device-backup.js carries only explicit preferences and holdings; this is a price-derived observation log). */
(function(root,factory){const node=typeof module==='object'&&module.exports;
 const api=factory(node?()=>require('./virtual-trading-runner.js'):()=>root.VirtualTradingRunner,node?()=>require('./virtual-trading-signals.js'):()=>root.VirtualTradingSignals);
 if(node)module.exports=api;else root.VirtualTradingVHistory=api;})(typeof globalThis==='object'?globalThis:this,function(runner,signals){
'use strict';
const KEY='investment.web.v1.virtual-trading-v-scores',SCHEMA='virtual-trading-v-scores/1',MAX_DATES=400;
const own=(o,k)=>o!==null&&typeof o==='object'&&Object.prototype.hasOwnProperty.call(o,k);
const object=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
const num=v=>typeof v==='number'&&Number.isFinite(v);
const day=v=>typeof v==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&+v.slice(5,7)>=1&&+v.slice(5,7)<=12&&+v.slice(8)>=1&&+v.slice(8)<=31;
const valid=(cid,v)=>own(runner().TARGETS,cid)&&num(v)&&v>=0&&v<=100;
// Stored scores: EMPTY (nothing yet), OK, INVALID (unreadable: left untouched), UNAVAILABLE (storage blocked).
function readStore(storage){
 let raw;try{raw=storage.getItem(KEY);}catch(_){return{state:'UNAVAILABLE',scores:{}};}
 if(raw===null||raw===undefined||raw==='')return{state:'EMPTY',scores:{}};
 try{const v=JSON.parse(raw);if(object(v)&&v.schema===SCHEMA&&object(v.scores))return{state:'OK',scores:v.scores};}catch(_){}
 return{state:'INVALID',scores:{}};
}
/* Pure merge. Returns {scores, added, dropped, reason}; reason is null when something was added. */
function merge(scores,date,values,{max=MAX_DATES}={}){
 const base=object(scores)?scores:{},dates=Object.keys(base).filter(day).sort(),last=dates.length?dates[dates.length-1]:null;
 const keep=(reason)=>({scores:base,added:[],dropped:[],reason});
 if(!day(date))return keep('DATE_INVALID');
 if(last!==null&&date<last)return keep('DATE_BEFORE_LAST_RECORDED');
 const row=object(base[date])?{...base[date]}:{},added=[],r2=signals().round2;
 for(const cid of Object.keys(object(values)?values:{}).sort()){const v=values[cid];if(!valid(cid,v)||own(row,cid))continue;row[cid]=r2(v);added.push(cid);}
 if(!added.length)return keep(Object.keys(object(values)?values:{}).length?'UNCHANGED':'NO_VALUES');
 const next={};for(const d of dates)next[d]=base[d];next[date]=Object.fromEntries(Object.keys(row).sort().map(c=>[c,row[c]]));
 const all=Object.keys(next).sort(),limit=Number.isInteger(max)&&max>0?max:MAX_DATES,dropped=all.slice(0,Math.max(0,all.length-limit));
 for(const d of dropped)delete next[d];
 const out={};for(const d of Object.keys(next).sort())out[d]=next[d];
 return{scores:out,added,dropped,reason:null};
}
function record(storage,date,values,opts={}){
 const current=readStore(storage);
 if(current.state==='UNAVAILABLE')return{state:'NOT_RECORDED',reason:'DEVICE_STORAGE_UNAVAILABLE',date,added:[]};
 if(current.state==='INVALID')return{state:'NOT_RECORDED',reason:'V_STORE_INVALID',date,added:[]};
 const m=merge(current.scores,date,values,opts);
 if(m.reason!==null)return{state:'NOT_RECORDED',reason:m.reason,date,added:[]};
 try{storage.setItem(KEY,JSON.stringify({schema:SCHEMA,scores:m.scores}));}catch(_){return{state:'NOT_RECORDED',reason:'DEVICE_STORAGE_UNAVAILABLE',date,added:[]};}
 return{state:'RECORDED',reason:null,date,added:m.added};
}
/* Browser glue: V per company on the runner result's latest completed SPY session from that session's close (RAM) and
   the public price-free valuation inputs, appended to the store; the result's ledgers then read the updated store. */
async function capture(view,result){
 const S=signals(),plan=S.capturePlan(result);
 const finish=(status)=>{let store={};try{store=runner().readVStore(view.localStorage);}catch(_){store={};}return{result:plan?S.withVScores(result,store):result,capture:status};};
 if(!plan)return finish({state:'NOT_RECORDED',reason:'SESSION_NOT_AVAILABLE',date:null,added:[]});
 const V=view.DeviceValuation;let payload=null;
 try{payload=V?await V.load(view):null;}catch(_){payload=null;}
 if(!payload)return finish({state:'NOT_RECORDED',reason:'VALUATION_INPUTS_UNAVAILABLE',date:plan.date,added:[]});
 let values={};try{[values]=S.vScoresFor(plan,payload,V.parameters());}catch(_){values={};}
 return finish(record(view.localStorage,plan.date,values));
}
return Object.freeze({KEY,SCHEMA,MAX_DATES,readStore,merge,record,capture});
});
