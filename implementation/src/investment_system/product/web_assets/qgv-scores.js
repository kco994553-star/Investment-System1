/* QgvScores: the ONE score accessor. S04/S05 (company-screen.js), S06 (leaderboard-screen.js), the virtual-trading rehearsal
   judgement rows and the daily report + its export (app.js -> DailyReport) all read scores here, and only this module reads
   ScoringDefault.scoring_default ('v1'|'v2'). Flipping that one setting flips every consumer:
   - default v1: v1 exactly as before (official v1 weights, no renormalization) is primary; v2 is shown as '비교용'.
   - default v2: v2 PROVISIONAL (QgvV2) is primary; v1 with missing-factor renormalization is shown under [자세히].
   v2 V needs this device's prices (Universe sheet tab / device quotes / Worker closes via DeviceValuation.deviceQuote), held in
   RAM only: nothing here is stored, logged or sent, and no result carries a price, market cap or EV. Missing is null, never 0. */
(function(root,factory){const node=typeof module==='object'&&module.exports;
 const dep=(file,name)=>node?()=>require('./'+file):()=>root[name];
 const api=factory(dep('engine-preview.js','EnginePreview'),dep('qgv-v2.js','QgvV2'),dep('profile-defaults.js','ProfileDefaults'),dep('scoring-default.js','ScoringDefault'),dep('sec-qgv2.js','SecQgv2'));
 if(node)module.exports=api;else root.QgvScores=api;})(typeof globalThis==='object'?globalThis:this,function(enginePreview,qgvV2,profileDefaults,scoringConfig,secQgv2){
'use strict';
const MODES=['v1','v2'];
const LABEL={v1:['점수 기준 v1 · 보정 전','Score basis v1 · uncalibrated'],v2:['점수 기준 v2 · PROVISIONAL','Score basis v2 · PROVISIONAL'],v1_renormalized:['v1 · 결측 재정규화 · 참고','v1 · missing renormalized · reference']};
const FLAG={VALUE_TRAP_CAUTION:['가치 함정 주의','Value-trap caution'],V_NOT_AVAILABLE:['V 없음','No V'],GATE_NOT_EVALUATED:['관문 판정 불가','Gate not evaluated']};
const object=v=>v!==null&&typeof v==='object'&&!Array.isArray(v),finite=v=>typeof v==='number'&&Number.isFinite(v);
function scoringDefault(){let c=null;try{c=scoringConfig();}catch(_){c=null;}return c&&c.scoring_default==='v2'?'v2':'v1';}
const key=t=>String(t||'').replaceAll('.','-').toUpperCase(),symbolOf=code=>key(String(code).slice(String(code).indexOf(':')+1));
function record(screens,file,id){const p=screens&&screens[file];return p&&p.data&&object(p.data.companies)&&Object.hasOwn(p.data.companies,id)?p.data.companies[id]:null;}
// v1 from the public TARGET sec-qg-factors.json row through EnginePreview.strategy, which applies the missing-factor rule
// (user decision 2026-10-13: renormalized over computed factors, axis NA below 50% of its weight, never 0). The v1 record shown
// under [자세히] when v2 is the default is this same renormalized v1.
function v1For(rec){
 const W=profileDefaults().weights,total=Object.keys(W.Q).length+Object.keys(W.G).length,obs={};
 if(rec&&rec.state!=='NOT_AVAILABLE'&&object(rec.factors))for(const[f,v]of Object.entries(rec.factors))if(v&&v.score!==null&&v.state!=='NOT_AVAILABLE')obs[f]={score:v.score,quality:v.state==='LIVE'?'OK':'STALE_DATA'};
 const n=Object.keys(obs).length,r=n?enginePreview().strategy({observations:obs}):null,axis=a=>r&&r.axes&&finite(r.axes[a].score)?r.axes[a].score:null,part=a=>!!(r&&r.axes&&r.axes[a].coverage&&r.axes[a].coverage!=='READY');
 const official={version:'v1',q:axis('Q'),g:axis('G'),v:null,total:r&&finite(r.qg_preview_total)?r.qg_preview_total:null,partial:part('Q')||part('G'),factors_available:n,factors_total:total,flags:[],state:n&&(axis('Q')!==null||axis('G')!==null)?'READY':'NOT_AVAILABLE'};
 return[official,{...official,version:'v1_renormalized'}];
}
function v2Display(r){
 if(!r)return{version:'v2',q:null,g:null,v:null,total:null,partial:true,factors_available:0,factors_total:qgvV2().FACTORS.length,flags:['V2_INPUTS_NOT_AVAILABLE'],state:'NOT_AVAILABLE'};
 const ax=a=>r.axes[a].score;
 return{version:'v2',q:ax('Q'),g:ax('G'),v:ax('V'),total:r.total,partial:['Q','G','V'].some(a=>r.axes[a].state!=='READY'),factors_available:r.factors_available,factors_total:r.factors_total,flags:[...r.flags],state:r.total===null?'NOT_AVAILABLE':'READY',
  axes:r.axes,factors:r.factors,weights:r.weights,profile:r.profile,q_industry_percentile:r.q_industry_percentile,v_excluded:r.v_excluded,detail:r.detail,reference_range:r.reference_range,selected_types:r.selected_types,type_reason:r.type_reason};
}
let memo=null;
function universeScores(v2Inputs,quotes,preset,gate,memberships){
 const mk=JSON.stringify([preset,gate,memberships]);if(memo&&memo.inputs===v2Inputs&&memo.quotes===quotes&&memo.key===mk)return memo.result;
 const companies={};for(const[code,r]of Object.entries(v2Inputs.records))companies[code]={industry_group:r.industry_group,profile:r.profile,factors:r.factors,v_inputs:r.v_inputs,memberships:Object.hasOwn(memberships,code)?memberships[code]:null};
 const result=qgvV2().scoreUniverse(companies,quotes,{preset,gate});memo={inputs:v2Inputs,quotes,key:mk,result};return result;
}
/* The accessor. identities: [{company_id, ticker}] rows to show; publicScreens: the app's loaded public screens (v1 factors,
   company types, and sec-qgv2.json under SecQgv2.FILE); quotes: {code:{price,currency}} RAM. Returns rows with v1, v1_renormalized,
   v2 and the primary/reference pick of the current setting. */
function compute({identities=[],publicScreens={},v2Inputs,quotes={},preset,gate=null,scoringDefault:mode}={}){
 const V2=qgvV2(),current=MODES.includes(mode)?mode:scoringDefault(),inputs=v2Inputs===undefined?(publicScreens&&secQgv2()?publicScreens[secQgv2().FILE]||null:null):v2Inputs;
 const chosen=preset&&Object.hasOwn(V2.PRESETS,preset)?preset:V2.DEFAULT_PRESET,gateOn=gate===null||gate===undefined?V2.GATE_DEFAULT:Boolean(gate);
 const codes=new Map();if(inputs)for(const code of Object.keys(inputs.records))if(!codes.has(symbolOf(code)))codes.set(symbolOf(code),code);
 const memberships={};for(const c of identities){const code=codes.get(key(c.ticker)),t=record(publicScreens,'company-types-pricefree.json',c.company_id);if(code&&t&&t.state!=='NOT_AVAILABLE'&&object(t.memberships))memberships[code]=t.memberships;}
 let universe=null,v2Reason=inputs?null:'SEC_QGV2_NOT_AVAILABLE';if(inputs){try{universe=universeScores(inputs,object(quotes)?quotes:{},chosen,gateOn,memberships);}catch(_){universe=null;v2Reason='V2_CALCULATION_FAILED';}}
 const rows={};let ranked=[];
 for(const c of identities){const[v1,v1r]=v1For(record(publicScreens,'sec-qg-factors.json',c.company_id)),code=codes.get(key(c.ticker))||null,v2=v2Display(universe&&code?universe[code]:null);
  const row={company_id:c.company_id,ticker:c.ticker,code,v1,v1_renormalized:v1r,v2};row.primary=current==='v2'?v2:v1;row.reference=current==='v2'?v1r:v2;row.rank=null;rows[c.company_id]=row;}
 ranked=Object.values(rows).filter(r=>finite(r.primary.total)).sort((a,b)=>b.primary.total-a.primary.total||(a.ticker<b.ticker?-1:1));
 if(current==='v2')ranked.forEach((r,i)=>{r.rank=i+1;});
 const quoted=object(quotes)?Object.keys(quotes).length:0;
 return{default:current,label:LABEL[current],profile:{preset:chosen,gate:gateOn,id:V2.VERSION+'/'+chosen+'/gate-'+(gateOn?'on':'off'),name:V2.PRESETS[chosen]},
  v2_state:universe?'READY':'NOT_AVAILABLE',v2_reason:v2Reason,v2_as_of:inputs?inputs.as_of:null,priced_codes:quoted,rows};
}
/* Rows for the virtual-trading rehearsal snapshot and the daily report (+ export): {cid:{q,g,partial,...}} from the primary
   version. In v1 the q/g/partial values are exactly the previous ones (official v1). */
function judgmentRows(computed){
 const out={};if(!computed||!object(computed.rows))return out;
 for(const[cid,r]of Object.entries(computed.rows)){const p=r.primary,ref=r.reference;
  out[cid]={q:p.q,g:p.g,partial:p.partial,v:p.v,total:p.total,version:p.version,factors_available:p.factors_available,factors_total:p.factors_total,flags:[...p.flags],value_trap:p.flags.includes('VALUE_TRAP_CAUTION'),
   compare:ref&&ref.state!=='NOT_AVAILABLE'?{version:ref.version,q:ref.q,g:ref.g,v:ref.v,total:ref.total,factors_available:ref.factors_available,factors_total:ref.factors_total}:null};}
 return out;
}
/* Device quotes for the v2 cross-section (RAM): the Universe tab read on this device (PrivateSubsetView.prices) first, then
   this device's stored/sheet/Worker quote per shown company (DeviceValuation.deviceQuote), plus PriceStore month-end closes
   for the own-history factor. Never stored or sent. */
async function collectQuotes(win,{identities=[],v2Inputs=null,catalog=null}={}){
 const out={};if(!v2Inputs||!object(v2Inputs.records))return out;const codes=new Map();for(const code of Object.keys(v2Inputs.records))if(!codes.has(symbolOf(code)))codes.set(symbolOf(code),code);
 let universe=null;try{universe=win.PrivateSubsetView&&typeof win.PrivateSubsetView.prices==='function'?win.PrivateSubsetView.prices():null;}catch(_){universe=null;}
 if(universe&&typeof universe.forEach==='function')universe.forEach((q,code)=>{if(Object.hasOwn(v2Inputs.records,code)&&q&&finite(q.price)&&q.price>0&&typeof q.currency==='string')out[code]={price:q.price,currency:q.currency};});
 if(catalog&&win.DeviceValuation&&typeof win.DeviceValuation.deviceQuote==='function')for(const c of identities){const code=codes.get(key(c.ticker));if(!code||Object.hasOwn(out,code))continue;
  let q=null;try{q=await win.DeviceValuation.deviceQuote(win,catalog,c.ticker);}catch(_){q=null;}if(q&&finite(q.price)&&q.price>0)out[code]={price:q.price,currency:q.currency};}
 // v_vs_own_history: month-end closes of the user's sheet Prices tab (PriceStore device module, RAM). Absent -> the factor is
 // NOT_AVAILABLE (PRICE_HISTORY_NOT_AVAILABLE); never filled.
 const store=win.PriceStore&&typeof win.PriceStore.monthEndCloses==='function'?win.PriceStore:null;
 if(store)for(const code of Object.keys(out)){let m=null;try{m=await store.monthEndCloses(code.slice(code.indexOf(':')+1));}catch(_){m=null;}
  const clean={};if(object(m))for(const[k,v]of Object.entries(m))if(/^\d{4}-(0[1-9]|1[0-2])$/.test(k)&&finite(v)&&v>0)clean[k]=v;if(Object.keys(clean).length)out[code]={...out[code],month_closes:clean};}
 return out;
}
const num=(v,d=1)=>finite(v)?(Math.round(v*10**d)/10**d).toFixed(d):'—';
function flagText(flags,en){return(flags||[]).filter(f=>Object.hasOwn(FLAG,f)).map(f=>FLAG[f][en?1:0]);}
// One-line text of a display row: 'QGV 61.2 · Q 60.1 · G 55.0 · V 48.2 · 요인 14/15'.
function summaryText(d,en){
 if(!d)return '—';const n=(en?'factors ':'요인 ')+d.factors_available+'/'+d.factors_total;
 if(d.version==='v2')return 'QGV '+num(d.total)+' · Q '+num(d.q)+' · G '+num(d.g)+' · V '+num(d.v)+' · '+n;
 return 'Q '+num(d.q)+' · G '+num(d.g)+(d.total!==null?' · Q·G '+num(d.total):'')+' · '+n;
}
function label(version,en){return(LABEL[version]||LABEL.v1)[en?1:0];}
function presets(){return qgvV2().PRESETS;}
return Object.freeze({MODES,LABEL,FLAG,scoringDefault,compute,judgmentRows,collectQuotes,summaryText,flagText,label,presets,symbolOf});
});
