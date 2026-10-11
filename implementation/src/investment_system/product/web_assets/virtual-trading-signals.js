/* Virtual trading signals v1: D-5 basis labels, device V scores per completed session and the rehearsal window, RAM only.
   Pure part mirrors qgv/virtual_trading_signals.py (vectors: tests/fixtures/virtual_trading_signals_v1.json).
   basisRows: which benchmark the engine's D-5 abnormal-drop check used on the last session (the D-22 sector ETF, or
   S&P 500 when the ETF series is absent: the engine's own fallback) and whether the basis is NOT_AVAILABLE; labels and
   counts only, never a price or z value. Rehearsal (리허설 · 기록 없음): the engine runs from the first of the last N
   completed SPY sessions with cash 0 + daily deposits, purely in memory; nothing here writes a ledger, sheet or store. */
(function(root,factory){const node=typeof module==='object'&&module.exports;
 const api=factory(node?()=>require('./virtual-trading.js'):()=>root.VirtualTrading,node?()=>require('./virtual-trading-runner.js'):()=>root.VirtualTradingRunner,
  node?()=>require('./device-valuation.js'):()=>root.DeviceValuation,node?()=>require('./engine-preview.js'):()=>root.EnginePreview);
 if(node)module.exports=api;else root.VirtualTradingSignals=api;})(typeof globalThis==='object'?globalThis:this,function(engine,runner,valuation,preview){
'use strict';
const SCHEMA='virtual-trading-signals/1',REHEARSAL_WINDOW=5,SP500='SP500',LEDGER_KINDS=['SET_A','SET_B','SHADOW'];
const own=(o,k)=>o!==null&&typeof o==='object'&&Object.prototype.hasOwnProperty.call(o,k);
const object=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
const num=v=>typeof v==='number'&&Number.isFinite(v);
const day=v=>typeof v==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&+v.slice(5,7)>=1&&+v.slice(5,7)<=12&&+v.slice(8)>=1&&+v.slice(8)<=31;
// Half-up to 2 decimals with the same float steps as the Python reference (y - floor(y) is exact).
function round2(v){const y=v*100,n=Math.floor(y);return (n+(y-n>=0.5?1:0))/100;}

function rehearsalStart(histories,window=REHEARSAL_WINDOW){
 if(!(Number.isInteger(window)&&window>=1))return null;
 const R=runner(),entry=object(histories)&&own(histories,R.SP500_SYMBOL)?histories[R.SP500_SYMBOL]:null,[closes,code]=R.seriesFromHistory(entry,R.SP500_SYMBOL,'USD');
 if(code!==null)return null;const sessions=Object.keys(closes).sort();return sessions[Math.max(0,sessions.length-window)];
}
// Only start_date moves; every rule value stays as configured.
function rehearsalConfig(histories,config,window=REHEARSAL_WINDOW){const start=rehearsalStart(histories,window),out={...config};if(start!==null)out.start_date=start;return out;}

// Today's public Q·G screen rows {cid:{q,g,partial}} → engine snapshot rows (rehearsal only).
function rehearsalSnapshot(qgRows){
 const out={},rows=object(qgRows)?qgRows:{},T=runner().TARGETS;
 for(const cid of Object.keys(rows).sort()){const r=rows[cid];if(!own(T,cid)||!object(r))continue;
  const q=num(r.q)?r.q:null,g=num(r.g)?r.g:null;out[cid]={q,g,coverage:q===null||g===null?'BLOCKED':r.partial===true?'PARTIAL':'READY'};}
 return out;
}
// Rehearsal: window sessions without a RECORDED forward-ledger snapshot use today's public Q·G screen snapshot.
function applyRehearsalSnapshots(result,qgRows){
 const rows=rehearsalSnapshot(qgRows);if(!object(result)||!Object.keys(rows).length)return[result,[]];
 const ledgers={...(result.ledgers||{})},filled=new Set();
 for(const[k,e]of Object.entries(ledgers)){if(!object(e)||e.state!=='READY')continue;
  const snaps={...(e.input.snapshots||{})};for(const d of e.input.sessions)if(!own(snaps,d)){snaps[d]=rows;filled.add(d);}
  const sorted={};for(const d of Object.keys(snaps).sort())sorted[d]=snaps[d];ledgers[k]={...e,input:{...e.input,snapshots:sorted}};}
 return[{...result,ledgers},[...filled].sort()];
}
function sectorSeries(L,cid,cfg){const bm=L.benchmarks||{},key=cfg.sector_basis==='SECTOR_ETF_CONFIRMED'?L.companies[cid].sector_benchmark:null;if(key&&own(bm,key))return[bm[key],key];return[own(bm,SP500)?bm[SP500]:null,SP500];}
function basisRows(L,cfg){
 if(!object(L)||!Array.isArray(L.sessions)||!L.sessions.length)return{};
 const VT=engine(),ss=L.sessions,d=ss[ss.length-1],idx=ss.length-1,a=cfg.abnormal_drop,lb=cfg.v_slope.lookback_sessions,needed=a.lookback_sessions+a.window_sessions+1;
 const vs=object(L.v_scores)?L.v_scores:{},past=idx-lb>=0?ss[idx-lb]:null,out={};
 for(const cid of Object.keys(L.companies).sort()){
  const comp=L.companies[cid],requested=(cfg.sector_basis==='SECTOR_ETF_CONFIRMED'?comp.sector_benchmark:null)||SP500;
  const[bench,used]=sectorSeries(L,cid,cfg),drop=VT.abnormalDrop(comp.closes,bench,d,cfg);
  let aligned=0;if(bench)for(const x of Object.keys(comp.closes))if(x<=d&&own(bench,x))aligned++;
  const vNow=own(vs,d)&&own(vs[d],cid)?vs[d][cid]:null,vPast=past!==null&&own(vs,past)&&own(vs[past],cid)?vs[past][cid]:null;
  const vState=drop.state==='NOT_AVAILABLE'?'BASIS_NOT_AVAILABLE':vNow!==null&&vPast!==null?'READY':'V_HISTORY_SHORT';
  out[cid]={requested,benchmark:used,fallback:requested!==SP500&&used===SP500,state:drop.state,reason:drop.reason,aligned,needed,v_slope:vState};
 }
 return out;
}
function vProgress(sessions,vScores,lookback){
 const dates=Object.keys(object(vScores)?vScores:{}).filter(d=>day(d)&&object(vScores[d])&&Object.keys(vScores[d]).length).sort();
 if(!dates.length)return{state:'NOT_RECORDED',first:null,last:null,recorded:0,elapsed:0,needed:lookback};
 const first=dates[0],elapsed=sessions.length?sessions.filter(s=>s>first).length:dates.length-1;
 return{state:elapsed>=lookback?'READY':'COLLECTING',first,last:dates[dates.length-1],recorded:dates.length,elapsed,needed:lookback};
}
// PREVIEW V axis of the official v1 V weight copy (EnginePreview.strategy, missing factors not renormalized).
function vAxis(view){
 const factors=object(view)&&object(view.v_factors)?view.v_factors:null;if(!factors)return null;
 const observations={};for(const[k,f]of Object.entries(factors))if(object(f)&&f.state!=='NOT_AVAILABLE'&&num(f.score))observations[k]={score:f.score,quality:'OK'};
 if(!Object.keys(observations).length)return null;
 const r=preview().strategy({observations}),s=r&&r.axes&&r.axes.V?r.axes.V.score:null;return num(s)?s:null;
}
function valuationRow(payload,cid){try{const r=payload.data.companies;return object(r)&&own(r,cid)?r[cid]:null;}catch(_){return null;}}
// Latest completed SPY session and the companies (closes, currency) of every READY ledger, or null.
function capturePlan(result){
 if(!object(result)||result.state!=='READY')return null;let d=null;const companies={};
 for(const kind of LEDGER_KINDS){const e=object(result.ledgers)?result.ledgers[kind]:null;if(!object(e)||e.state!=='READY')continue;
  const spy=e.input.benchmarks[SP500]||{},keys=Object.keys(spy);if(keys.length){const last=keys.sort()[keys.length-1];if(d===null||last>d)d=last;}
  for(const cid of Object.keys(e.input.companies))if(!own(companies,cid))companies[cid]=e.input.companies[cid];}
 if(d===null)return null;const sorted={};for(const cid of Object.keys(companies).sort())sorted[cid]=companies[cid];
 return{date:d,companies:sorted};
}
// V per company on plan.date from that session's close. Absent close, row or V stays absent (never 0).
function vScoresFor(plan,payload,parameters){
 const out={},raw={};if(!plan)return[out,raw];const V=valuation(),d=plan.date;
 for(const cid of Object.keys(plan.companies)){const comp=plan.companies[cid],close=own(comp.closes,d)?comp.closes[d]:null,row=valuationRow(payload,cid);
  if(close===null||row===null)continue;
  const v=vAxis(V.view({row,quote:{price:close,currency:comp.currency},parameters}));
  if(v!==null&&v>=0&&v<=100){raw[cid]=v;out[cid]=round2(v);}}
 return[out,raw];
}
function withVScores(result,store){
 if(!object(result))return result;const scores=runner().vScoresFromStore(store),ledgers={...(result.ledgers||{})};
 for(const[k,e]of Object.entries(ledgers))if(object(e)&&e.state==='READY')ledgers[k]={...e,input:{...e.input,v_scores:scores}};
 return{...result,ledgers};
}
function reportSignals(result,kind,cfg,store){
 const lb=cfg.v_slope.lookback_sessions,e=object(result)&&object(result.ledgers)?result.ledgers[kind]:null;
 if(object(e)&&e.state==='READY'){const L=e.input,sessions=Object.keys(L.benchmarks[SP500]||{}).sort();
  return{schema:SCHEMA,date:L.sessions.length?L.sessions[L.sessions.length-1]:null,basis:basisRows(L,cfg),v_progress:vProgress(sessions,L.v_scores,lb)};}
 return{schema:SCHEMA,date:null,basis:{},v_progress:vProgress([],runner().vScoresFromStore(store),lb)};
}
/* Rehearsal run (browser): the runner's normal fetch path without the start-date gate, then the engine config moved to the
   rehearsal window. Returns {result, config}; result.mode is REHEARSAL so no recording hook may persist it. */
async function rehearse(view,{qgRows=null,window=REHEARSAL_WINDOW,...opts}={}){
 let used=null;const w=Number.isInteger(window)&&window>=1?window:REHEARSAL_WINDOW;
 const result=await runner().run(view,{...opts,rehearsal:(histories,cfg)=>(used=rehearsalConfig(histories,cfg,w))});
 const[filledResult,filled]=applyRehearsalSnapshots(result,qgRows),cfg=used||engine().defaultConfig();
 return{result:{...filledResult,mode:'REHEARSAL',rehearsal:{start_date:cfg.start_date,window:w,qg_filled:filled}},config:cfg};
}
return Object.freeze({SCHEMA,REHEARSAL_WINDOW,round2,rehearsalStart,rehearsalConfig,rehearsalSnapshot,applyRehearsalSnapshots,basisRows,vProgress,vAxis,capturePlan,vScoresFor,withVScores,reportSignals,rehearse});
});
