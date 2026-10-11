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
// Codes on basis rows: V slope use and the engine's D-5 basis reasons (labels: VirtualTrading.CODE_LABELS).
const CODES=Object.freeze(['BASIS_NOT_AVAILABLE','V_HISTORY_SHORT','V_COMPOSITION_CHANGED','V_CORE_FACTOR_MISSING','V_FACTORS_NOT_AVAILABLE','REHEARSAL_ONLY','SECTOR_BASIS_NOT_AVAILABLE','PRICE_NOT_ALIGNED','HISTORY_INSUFFICIENT','DISTRIBUTION_DEGENERATE']);
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
// Rehearsal only (decision 2026-10-11): any other mode is refused (REHEARSAL_ONLY), so recording never fills a missing day.
function applyRehearsalSnapshots(result,qgRows,mode){
 if(mode!=='REHEARSAL')throw new Error('REHEARSAL_ONLY');
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
 const vs=object(L.v_scores)?L.v_scores:{},vc=object(L.v_composition)?L.v_composition:{},past=idx-lb>=0?ss[idx-lb]:null,out={};
 for(const cid of Object.keys(L.companies).sort()){
  const comp=L.companies[cid],requested=(cfg.sector_basis==='SECTOR_ETF_CONFIRMED'?comp.sector_benchmark:null)||SP500;
  const[bench,used]=sectorSeries(L,cid,cfg),drop=VT.abnormalDrop(comp.closes,bench,d,cfg);
  let aligned=0;if(bench)for(const x of Object.keys(comp.closes))if(x<=d&&own(bench,x))aligned++;
  const vNow=own(vs,d)&&own(vs[d],cid)?vs[d][cid]:null,vPast=past!==null&&own(vs,past)&&own(vs[past],cid)?vs[past][cid]:null;
  const cNow=own(vc,d)&&own(vc[d],cid)?vc[d][cid]:null,cPast=past!==null&&own(vc,past)&&own(vc[past],cid)?vc[past][cid]:null;
  const vState=drop.state==='NOT_AVAILABLE'?'BASIS_NOT_AVAILABLE':vNow===null||vPast===null?'V_HISTORY_SHORT':typeof cNow==='string'&&cNow===cPast?'READY':'V_COMPOSITION_CHANGED';
  out[cid]={requested,benchmark:used,fallback:requested!==SP500&&used===SP500,state:drop.state,reason:drop.reason,aligned,needed,v_slope:vState};
 }
 return out;
}
// With a composition map (V history /2) only dates recorded with their factor composition count: entries written before
// the composition was stored (/1) have an unknown composition and cannot anchor a 20-session V slope.
function vProgress(sessions,vScores,lookback,vComposition=null){
 const known=d=>!object(vComposition)||(object(vComposition[d])&&Object.keys(vComposition[d]).length>0);
 const dates=Object.keys(object(vScores)?vScores:{}).filter(d=>day(d)&&object(vScores[d])&&Object.keys(vScores[d]).length&&known(d)).sort();
 if(!dates.length)return{state:'NOT_RECORDED',first:null,last:null,recorded:0,elapsed:0,needed:lookback};
 const first=dates[0],elapsed=sessions.length?sessions.filter(s=>s>first).length:dates.length-1;
 return{state:elapsed>=lookback?'READY':'COLLECTING',first,last:dates[dates.length-1],recorded:dates.length,elapsed,needed:lookback};
}
/* Core V factors (decision 2026-10-11): the spec defines no "core" subset, so every factor with weight > 0 in the official
   v1 V weight copy is core. A missing core factor makes that day's V NA (V_CORE_FACTOR_MISSING): V is never computed with a
   missing factor counted as 0. The composition key is the sorted ids of the factors present ('a+b+…'). */
function coreVFactors(){const r=preview().strategy({observations:{}}),w=r&&r.official_weights&&r.official_weights.V||{};return Object.keys(w).filter(k=>num(w[k])&&w[k]>0).sort();}
function vAxisDetail(view){
 const factors=object(view)&&object(view.v_factors)?view.v_factors:null;
 if(!factors)return{state:'NOT_AVAILABLE',score:null,composition:null,reason:'V_FACTORS_NOT_AVAILABLE',missing:coreVFactors()};
 const observations={};for(const[k,f]of Object.entries(factors))if(object(f)&&f.state!=='NOT_AVAILABLE'&&num(f.score))observations[k]={score:f.score,quality:'OK'};
 const missing=coreVFactors().filter(k=>!own(observations,k));
 if(missing.length)return{state:'NOT_AVAILABLE',score:null,composition:null,reason:'V_CORE_FACTOR_MISSING',missing};
 const r=preview().strategy({observations}),s=r&&r.axes&&r.axes.V?r.axes.V.score:null;
 if(!num(s))return{state:'NOT_AVAILABLE',score:null,composition:null,reason:'V_FACTORS_NOT_AVAILABLE',missing:[]};
 return{state:'OK',score:s,composition:Object.keys(observations).sort().join('+'),reason:null,missing:[]};
}
function vAxis(view){const d=vAxisDetail(view);return d.state==='OK'?d.score:null;}
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
// V per company on plan.date from that session's close. Absent close, row or V stays absent (never 0); a missing core factor
// skips the company with its reason. Returns [V rounded, V raw, composition key, skipped reasons].
function vScoresFor(plan,payload,parameters){
 const out={},raw={},composition={},skipped={};if(!plan)return[out,raw,composition,skipped];const V=valuation(),d=plan.date;
 for(const cid of Object.keys(plan.companies)){const comp=plan.companies[cid],close=own(comp.closes,d)?comp.closes[d]:null,row=valuationRow(payload,cid);
  if(close===null||row===null)continue;
  const x=vAxisDetail(V.view({row,quote:{price:close,currency:comp.currency},parameters}));
  if(x.state!=='OK'){skipped[cid]=x.reason;continue;}
  if(x.score>=0&&x.score<=100){raw[cid]=x.score;out[cid]=round2(x.score);composition[cid]=x.composition;}}
 return[out,raw,composition,skipped];
}
function withVScores(result,store,composition=null){
 if(!object(result))return result;const scores=runner().vScoresFromStore(store),comp=runner().vCompositionFromStore(composition),ledgers={...(result.ledgers||{})};
 for(const[k,e]of Object.entries(ledgers))if(object(e)&&e.state==='READY')ledgers[k]={...e,input:{...e.input,v_scores:scores,v_composition:comp}};
 return{...result,ledgers};
}
function reportSignals(result,kind,cfg,store,composition=null){
 const lb=cfg.v_slope.lookback_sessions,e=object(result)&&object(result.ledgers)?result.ledgers[kind]:null;
 if(object(e)&&e.state==='READY'){const L=e.input,sessions=Object.keys(L.benchmarks[SP500]||{}).sort();
  return{schema:SCHEMA,date:L.sessions.length?L.sessions[L.sessions.length-1]:null,basis:basisRows(L,cfg),v_progress:vProgress(sessions,L.v_scores,lb,object(L.v_composition)?L.v_composition:{})};}
 return{schema:SCHEMA,date:null,basis:{},v_progress:vProgress([],runner().vScoresFromStore(store),lb,runner().vCompositionFromStore(composition))};
}
/* Rehearsal run (browser): the runner's normal fetch path without the start-date gate, then the engine config moved to the
   rehearsal window. Returns {result, config}; result.mode is REHEARSAL so no recording hook may persist it. */
async function rehearse(view,{qgRows=null,window=REHEARSAL_WINDOW,...opts}={}){
 let used=null;const w=Number.isInteger(window)&&window>=1?window:REHEARSAL_WINDOW;
 const result=await runner().run(view,{...opts,rehearsal:(histories,cfg)=>(used=rehearsalConfig(histories,cfg,w))});
 const[filledResult,filled]=applyRehearsalSnapshots(result,qgRows,'REHEARSAL'),cfg=used||engine().defaultConfig();
 return{result:{...filledResult,mode:'REHEARSAL',rehearsal:{start_date:cfg.start_date,window:w,qg_filled:filled}},config:cfg};
}
return Object.freeze({SCHEMA,CODES,REHEARSAL_WINDOW,round2,rehearsalStart,rehearsalConfig,rehearsalSnapshot,applyRehearsalSnapshots,basisRows,vProgress,coreVFactors,vAxisDetail,vAxis,capturePlan,vScoresFor,withVScores,reportSignals,rehearse});
});
