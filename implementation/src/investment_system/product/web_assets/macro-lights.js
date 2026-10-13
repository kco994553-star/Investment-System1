/* Macro state v1 (PLAYBOOK_V1 13-5): five warning lights → NORMAL / WARNING / CRISIS. v1 · UNCALIBRATED.
   Pure part mirrors macro/macro_lights_v1.py (vectors: tests/fixtures/macro_lights_v1_vectors.json; CONFIG equals
   macro/macro_lights_v1.json). Employment, inflation and curve come from the public macro-screen.json block; the market
   light (SPY) is computed here from Worker history in RAM only; the credit light (HYG ÷ IEF, estimate) needs HYG and IEF
   in the Worker allowlist and stays "확인 불가" until then. Nothing here stores, logs or sends prices or derived values.
   Macro only paces what to buy and how fast; it is never used for sell decisions. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.MacroLights=api;})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
const CONFIG=Object.freeze({id:'MACRO_LIGHTS_V1',version:'v1',status:'UNCALIBRATED',marker:'v1 · UNCALIBRATED',decided_on:'2026-10-13',source_section:'PLAYBOOK_V1 13-5',sell_decisions:false,comparison_epsilon:1e-9,
 lights:{employment:{series:'BLS:LNS14000000',avg_months:3,low_window_months:12,low_window_includes_latest:true,gap_pp_gte:0.5},
  inflation:{series:'BLS:CUUR0000SA0',base_lag_months:12,yoy_gt:0.05},
  curve:{series:'TREASURY:daily_treasury_yield_curve:BC_10YEAR-BC_3MONTH',spread_lt:0,min_run_days:20},
  market:{symbol:'SPY',drawdown_lte:-0.2,high_window_days:364,rv_window_returns:20,rv_annualization_days:252,rv_history_years:3,rv_top_share:0.05},
  credit:{numerator:'HYG',denominator:'IEF',window_sessions:20,change_lte:-0.05,estimate:true}},
 state:{warning_lit_count:2,crisis_lit_count:3,warning_inflation_gt:0.05,warning_growth_lt:0,crisis_inflation_gt:0.08,crisis_pair:['market','credit'],low_confidence_available_lt:3}});
const LIGHTS=Object.freeze(['employment','inflation','curve','market','credit']),PUBLIC_LIGHTS=Object.freeze(['employment','inflation','curve']),DEVICE_LIGHTS=Object.freeze(['market','credit']);
const FIELDS=Object.freeze({employment:['lit','reason','period','avg3','low12','low12_count','gap'],inflation:['lit','reason','period','base_period','yoy'],
 curve:['lit','reason','date','ten_year','three_month','spread','run_days'],
 market:['lit','reason','date','last_close','high_52w','drawdown','drawdown_lit','rv20','rv_count','rv_above_count','rv_lit'],
 credit:['lit','reason','date','base_date','ratio_change','estimate']});
const REASONS=Object.freeze(['LIT','NOT_LIT','NO_DATA','INVALID_INPUT','CONFLICTING_DUPLICATE','WINDOW_INCOMPLETE','INSUFFICIENT_HISTORY','BASE_MONTH_MISSING','VALUE_MISSING','WORKER_ALLOWLIST_REQUIRED',
 'SOURCE_NOT_COLLECTED','SOURCE_NOT_AVAILABLE','SCHEMA_MISMATCH','SYNTHETIC_INPUT_NOT_PUBLIC','SOURCE_AFTER_AS_OF','DEVICE_NOT_LOADED']);
const MISSING_REASONS=Object.freeze(REASONS.filter(r=>!['LIT','NOT_LIT','WORKER_ALLOWLIST_REQUIRED','DEVICE_NOT_LOADED'].includes(r)));
const META=Object.freeze({employment:{agency:'BLS',source_series_id:'BLS:LNS14000000',source:'BLS LNS14000000 · unemployment rate, SA, monthly'},
 inflation:{agency:'BLS',source_series_id:'BLS:CUUR0000SA0',source:'BLS CUUR0000SA0 · CPI-U all items, NSA, monthly'},
 curve:{agency:'TREASURY',source_series_id:'TREASURY:daily_treasury_yield_curve:BC_10YEAR-BC_3MONTH',source:'U.S. Treasury daily par yield curve · 10 Yr − 3 Mo'}});
const AS_OF_KEY=Object.freeze({employment:'period',inflation:'period',curve:'date'});
// User-approved expansion; this PR depends on the matching HYG / IEF Worker release. An old Worker fails closed.
const WORKER_ALLOWED=Object.freeze(['SPY','HYG','IEF']),RANGE='5y';
const num=v=>typeof v==='number'&&Number.isFinite(v);
const MONTH=/^\d{4}-(?:0[1-9]|1[0-2])$/,DAY=/^\d{4}-\d{2}-\d{2}$/;
function validDay(t){if(typeof t!=='string'||!DAY.test(t))return false;const ms=Date.parse(t+'T00:00:00Z');return Number.isFinite(ms)&&new Date(ms).toISOString().slice(0,10)===t;}
function keyOk(k,kind){return typeof k==='string'&&(kind==='month'?MONTH.test(k):validDay(k));}
function value(v,sign){if(!num(v))return null;if(sign==='positive'&&!(v>0))return null;if(sign==='nonneg'&&!(v>=0))return null;return v;}
function points(series,kind,sign,width=2){
 if(!Array.isArray(series)||!series.length)return[null,'NO_DATA'];
 const seen=new Map();
 for(const item of series){
  if(!Array.isArray(item)||item.length!==width||!keyOk(item[0],kind))return[null,'INVALID_INPUT'];
  const values=item.slice(1).map(v=>value(v,sign));
  if(seen.has(item[0])){const old=seen.get(item[0]);if(old.some((v,i)=>v!==values[i]))return[null,'CONFLICTING_DUPLICATE'];continue;}
  seen.set(item[0],values);
 }
 if(![...seen.values()].some(vs=>vs.some(v=>v!==null)))return[null,'NO_DATA'];
 return[[...seen.keys()].sort().map(k=>[k,...seen.get(k)]),null];
}
const monthIndex=p=>Number(p.slice(0,4))*12+Number(p.slice(5,7))-1;
const month=i=>String(Math.floor(i/12)).padStart(4,'0')+'-'+String(i%12+1).padStart(2,'0');
const daysBack=(d,n)=>new Date(Date.parse(d+'T00:00:00Z')-n*86400000).toISOString().slice(0,10);
function yearsBack(d,n){const y=Number(d.slice(0,4))-n,m=d.slice(5,7);let dd=d.slice(8,10);if(m==='02'&&dd==='29')dd='28';return String(y).padStart(4,'0')+'-'+m+'-'+dd;}
function unavailable(name,reason,values={}){const row={};for(const k of FIELDS[name])row[k]=null;Object.assign(row,values,{lit:null,reason});if(name==='credit')row.estimate=true;return row;}
function row(name,lit,values){const r={};for(const k of FIELDS[name])r[k]=null;Object.assign(r,values,{lit,reason:lit?'LIT':'NOT_LIT'});return r;}
function lastKey(pts){let k=null;for(const p of pts)if(p[1]!==null)k=p[0];return k;}

function employmentLight(series,config=CONFIG){
 const cfg=config.lights.employment,eps=config.comparison_epsilon,[pts,reason]=points(series,'month','nonneg');
 if(reason)return unavailable('employment',reason);
 const values=new Map(pts.map(p=>[p[0],p[1]])),latest=lastKey(pts),last=monthIndex(latest),get=k=>values.has(k)?values.get(k):null;
 const window=[];for(let i=cfg.avg_months-1;i>=0;i--)window.push(month(last-i));
 if(window.some(k=>get(k)===null))return unavailable('employment','WINDOW_INCOMPLETE',{period:latest});
 let total=0;for(const k of window)total+=get(k);
 const avg=total/cfg.avg_months,end=cfg.low_window_includes_latest?last:last-1,start=end-cfg.low_window_months+1;
 if(monthIndex(pts[0][0])>start)return unavailable('employment','INSUFFICIENT_HISTORY',{period:latest,avg3:avg});
 const low=[];for(let i=start;i<=end;i++){const v=get(month(i));if(v!==null)low.push(v);}
 if(!low.length)return unavailable('employment','WINDOW_INCOMPLETE',{period:latest,avg3:avg});
 const min=Math.min(...low),gap=avg-min;
 return row('employment',gap>=cfg.gap_pp_gte-eps,{period:latest,avg3:avg,low12:min,low12_count:low.length,gap});
}
function inflationLight(series,config=CONFIG){
 const cfg=config.lights.inflation,eps=config.comparison_epsilon,[pts,reason]=points(series,'month','positive');
 if(reason)return unavailable('inflation',reason);
 const values=new Map(pts.map(p=>[p[0],p[1]])),latest=lastKey(pts),base=month(monthIndex(latest)-cfg.base_lag_months);
 if(!values.has(base)||values.get(base)===null)return unavailable('inflation','BASE_MONTH_MISSING',{period:latest,base_period:base});
 const yoy=values.get(latest)/values.get(base)-1;
 return row('inflation',yoy>cfg.yoy_gt+eps,{period:latest,base_period:base,yoy});
}
function curveLight(rows,config=CONFIG){
 const cfg=config.lights.curve,eps=config.comparison_epsilon,[pts,reason]=points(rows,'day','any',3);
 if(reason)return unavailable('curve',reason);
 const [day,three,ten]=pts[pts.length-1];
 if(three===null||ten===null)return unavailable('curve','VALUE_MISSING',{date:day,ten_year:ten,three_month:three});
 const spread=ten-three,need=cfg.min_run_days,limit=cfg.spread_lt-eps;let run=0,exhausted=true;
 for(let i=pts.length-1;i>=0;i--){const m3=pts[i][1],y10=pts[i][2];
  if(m3===null||y10===null){if(run>=need){exhausted=false;break;}return unavailable('curve','VALUE_MISSING',{date:day,ten_year:ten,three_month:three,spread,run_days:run});}
  if(y10-m3<limit)run++;else{exhausted=false;break;}}
 if(exhausted&&run<need)return unavailable('curve','INSUFFICIENT_HISTORY',{date:day,ten_year:ten,three_month:three,spread,run_days:run});
 return row('curve',run>=need,{date:day,ten_year:ten,three_month:three,spread,run_days:run});
}
function rv(closes,index,n,annual){
 if(index<n)return null;const w=closes.slice(index-n,index+1);if(w.some(c=>c===null))return null;
 const r=[];for(let i=1;i<=n;i++)r.push(w[i]/w[i-1]-1);
 let total=0;for(const x of r)total+=x;const mean=total/n;let squares=0;for(const x of r)squares+=(x-mean)*(x-mean);
 return Math.sqrt(squares/(n-1)*annual);
}
function marketLight(series,config=CONFIG){
 const cfg=config.lights.market,eps=config.comparison_epsilon,[pts,reason]=points(series,'day','positive');
 if(reason)return unavailable('market',reason);
 const days=pts.map(p=>p[0]),closes=pts.map(p=>p[1]);let last=-1;closes.forEach((c,i)=>{if(c!==null)last=i;});
 const day=days[last],close=closes[last],out={date:day,last_close:close},reasons=[];
 const start=daysBack(day,cfg.high_window_days);let ddLit;
 if(days[0]>start){ddLit=null;reasons.push('INSUFFICIENT_HISTORY');}
 else{let high=-Infinity;for(let i=0;i<days.length;i++)if(closes[i]!==null&&start<=days[i]&&days[i]<=day&&closes[i]>high)high=closes[i];
  const drawdown=close/high-1;ddLit=drawdown<=cfg.drawdown_lte+eps;out.high_52w=high;out.drawdown=drawdown;}
 out.drawdown_lit=ddLit;
 const n=cfg.rv_window_returns,annual=cfg.rv_annualization_days,current=rv(closes,last,n,annual),cutoff=yearsBack(day,cfg.rv_history_years);let rvLit;
 if(current===null){rvLit=null;reasons.push('WINDOW_INCOMPLETE');}
 else if(days[0]>cutoff){rvLit=null;out.rv20=current;reasons.push('INSUFFICIENT_HISTORY');}
 else{const dist=[];for(let i=0;i<=last;i++)if(cutoff<=days[i]){const v=rv(closes,i,n,annual);if(v!==null)dist.push(v);}
  let above=0;for(const v of dist)if(v>current)above++;
  rvLit=above<cfg.rv_top_share*dist.length;out.rv20=current;out.rv_count=dist.length;out.rv_above_count=above;}
 out.rv_lit=rvLit;
 if(ddLit===true||rvLit===true)return row('market',true,out);
 if(ddLit===false&&rvLit===false)return row('market',false,out);
 return unavailable('market',reasons[0],out);
}
function creditLight(numerator,denominator,config=CONFIG){
 const cfg=config.lights.credit,eps=config.comparison_epsilon;
 const [hyg,r1]=points(numerator,'day','positive');if(r1)return unavailable('credit',r1);
 const [ief,r2]=points(denominator,'day','positive');if(r2)return unavailable('credit',r2);
 const h=new Map(hyg.map(p=>[p[0],p[1]])),f=new Map(ief.map(p=>[p[0],p[1]]));
 const joint=[...h.keys()].sort().filter(d=>h.get(d)!==null&&f.has(d)&&f.get(d)!==null),n=cfg.window_sessions;
 if(joint.length<n+1)return unavailable('credit','INSUFFICIENT_HISTORY',{date:joint.length?joint[joint.length-1]:null});
 const t=joint[joint.length-1],b=joint[joint.length-1-n],change=(h.get(t)/f.get(t))/(h.get(b)/f.get(b))-1;
 return row('credit',change<=cfg.change_lte+eps,{date:t,base_date:b,ratio_change:change,estimate:true});
}
function litOf(v){if(v!==null&&typeof v==='object'&&!Array.isArray(v))v=v.lit;return v===true||v===false?v:null;}
function macroState(lights,cpiYoy=null,growth=null,config=CONFIG){
 const cfg=config.state,eps=config.comparison_epsilon,src=lights!==null&&typeof lights==='object'&&!Array.isArray(lights)?lights:{};
 const lit={};for(const n of LIGHTS)lit[n]=litOf(Object.prototype.hasOwnProperty.call(src,n)?src[n]:null);
 const available=LIGHTS.filter(n=>lit[n]!==null),count=available.filter(n=>lit[n]).length;
 const cpi=num(cpiYoy)?cpiYoy:null,grow=num(growth)?growth:null,crisis=[],warning=[];
 if(count>=cfg.crisis_lit_count)crisis.push('LIT_COUNT_GE_3');
 if(cfg.crisis_pair.every(n=>lit[n]===true))crisis.push('MARKET_AND_CREDIT_LIT');
 if(cpi!==null&&cpi>cfg.crisis_inflation_gt+eps)crisis.push('INFLATION_GT_8PCT');
 if(count===cfg.warning_lit_count)warning.push('LIT_COUNT_EQ_2');
 if(cpi!==null&&grow!==null&&cpi>cfg.warning_inflation_gt+eps&&grow<cfg.warning_growth_lt-eps)warning.push('INFLATION_GT_5PCT_AND_GROWTH_LT_0');
 const [state,reasons]=crisis.length?['CRISIS',crisis]:warning.length?['WARNING',warning]:['NORMAL',['LIT_COUNT_LE_1']];
 const low=available.length<cfg.low_confidence_available_lt;
 return{state,lit_count:count,available_count:available.length,low_confidence:low,reasons:low?[...reasons,'AVAILABLE_LT_3']:reasons};
}

/* ---------- public block (macro-screen.json data.macro_lights_v1) validation, mirrors macro_lights_public.py ---------- */
function need(v){if(!v)throw Error('PUBLIC_SCREEN_INVALID');}
const obj=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
const sameKeys=(v,ks)=>obj(v)&&Object.keys(v).length===ks.length&&ks.every(k=>Object.prototype.hasOwnProperty.call(v,k));
const close=(a,b)=>Math.abs(a-b)<=1e-12*Math.max(1,Math.abs(a),Math.abs(b));
const PUBLIC_CONFIG=Object.freeze({id:CONFIG.id,version:CONFIG.version,status:CONFIG.status,marker:CONFIG.marker,decided_on:CONFIG.decided_on,source_section:CONFIG.source_section});
function requirePublicBlock(b,sources,cut,ttlSeconds,states,clock){
 const eps=CONFIG.comparison_epsilon,cfg=CONFIG.lights;
 need(sameKeys(b,['config','lights','device_lights'])&&sameKeys(b.config,Object.keys(PUBLIC_CONFIG)));for(const[k,v]of Object.entries(PUBLIC_CONFIG))need(b.config[k]===v);
 need(JSON.stringify(b.device_lights)===JSON.stringify(DEVICE_LIGHTS)&&sameKeys(b.lights,PUBLIC_LIGHTS));
 for(const name of PUBLIC_LIGHTS){const r=b.lights[name];
  need(sameKeys(r,['state','lit','reason','as_of','agency','source_series_id','source','inputs','values']));for(const[k,v]of Object.entries(META[name]))need(r[k]===v);
  need(['LIVE','STALE','NOT_AVAILABLE'].includes(r.state)&&[true,false,null].includes(r.lit)&&Array.isArray(r.inputs)&&r.inputs.length<=(name==='curve'?2:1));
  const stamps=[];for(const i of r.inputs){need(sameKeys(i,['sha256','acquired_at'])&&typeof i.sha256==='string'&&/^[0-9a-f]{64}$/.test(i.sha256));const s=clock(i.acquired_at);need(sources.get(r.agency+':'+i.sha256)===s);stamps.push(s);}
  const v=r.values,keys=FIELDS[name].filter(k=>k!=='lit'&&k!=='reason');need(sameKeys(v,keys)&&r.as_of===v[AS_OF_KEY[name]]);
  for(const x of Object.values(v))need(x===null||num(x)||typeof x==='string'&&x.length<=10);
  if(r.lit===null)need(r.state==='NOT_AVAILABLE'&&MISSING_REASONS.includes(r.reason));
  else{need(stamps.length>0&&r.reason===(r.lit?'LIT':'NOT_LIT'));need(r.state===(cut-Math.min(...stamps)>ttlSeconds*1000?'STALE':'LIVE'));
   if(name==='employment'){need(typeof v.period==='string'&&MONTH.test(v.period)&&num(v.avg3)&&num(v.low12)&&num(v.gap)&&Number.isInteger(v.low12_count)&&v.low12_count>=1&&v.low12_count<=cfg.employment.low_window_months&&close(v.gap,v.avg3-v.low12));need(r.lit===(v.gap>=cfg.employment.gap_pp_gte-eps));}
   else if(name==='inflation'){need(typeof v.period==='string'&&MONTH.test(v.period)&&v.base_period===month(monthIndex(v.period)-cfg.inflation.base_lag_months)&&num(v.yoy));need(r.lit===(v.yoy>cfg.inflation.yoy_gt+eps));}
   else{need(typeof v.date==='string'&&DAY.test(v.date)&&num(v.ten_year)&&num(v.three_month)&&num(v.spread)&&Number.isInteger(v.run_days)&&v.run_days>=0&&close(v.spread,v.ten_year-v.three_month));need(r.lit===(v.run_days>=cfg.curve.min_run_days));}}
  states.push(r.state);}
}

/* ---------- merge public + device lights (RAM only) ---------- */
let current=null,deviceRows={market:null,credit:null},deviceRevision=null;
function publicInputs(bundle){
 const p=bundle&&bundle['macro-screen.json'],d=p&&p.data,b=d&&d.macro_lights_v1,lights={};
 for(const n of PUBLIC_LIGHTS){const r=b&&b.lights&&b.lights[n];lights[n]=r?{...r.values,lit:r.lit,reason:r.reason,state:r.state,as_of:r.as_of,source:r.source}:unavailable(n,'SOURCE_NOT_COLLECTED');}
 const yoy=lights.inflation.lit!==null&&num(lights.inflation.yoy)?lights.inflation.yoy:null;
 const g=d&&d.growth_inflation_v0&&d.growth_inflation_v0.axes&&d.growth_inflation_v0.axes.Growth;
 const growth=g&&g.state!=='NOT_AVAILABLE'&&typeof g.value==='string'&&num(Number(g.value))?Number(g.value):null;
 return{lights,cpi_yoy:yoy,growth,growth_period:growth===null?null:g.period,as_of:p?p.as_of:null};
}
function creditBlocked(){return!['numerator','denominator'].every(k=>WORKER_ALLOWED.includes(CONFIG.lights.credit[k]));}
function merge(bundle,device=deviceRows){
 const pub=publicInputs(bundle),lights={...pub.lights};
 lights.market=device&&device.market?device.market:unavailable('market','DEVICE_NOT_LOADED');
 lights.credit=creditBlocked()?unavailable('credit','WORKER_ALLOWLIST_REQUIRED'):device&&device.credit?device.credit:unavailable('credit','DEVICE_NOT_LOADED');
 const result=macroState(lights,pub.cpi_yoy,pub.growth);
 current={state:result.available_count===0?null:result.state,lit_count:result.lit_count,available_count:result.available_count,low_confidence:result.low_confidence};
 return{...result,lights,cpi_yoy:pub.cpi_yoy,growth:pub.growth,growth_period:pub.growth_period,as_of:pub.as_of};
}
function setPublic(bundle){try{return merge(bundle);}catch(_){return null;}}
// RAM-only state for the playbook engine; null until computed in this page session. Never persisted.
function currentState(){return current?{...current}:null;}
function clearDevice(){deviceRows={market:null,credit:null};deviceRevision=null;}

/* ---------- device fetch (Worker history, RAM only) ---------- */
function storedOrigin(view){try{const v=view.localStorage.getItem('investment.web.v1.private-history-origin');return v&&view.PrivateHistory?view.PrivateHistory.parseWorkerOrigin(v):'';}catch(_){return null;}}
function sessionFor(view,config){try{return config.googleSheetsClientId&&view.GoogleSheetQuotes?view.GoogleSheetQuotes.sessionFor(view,config.googleSheetsClientId):null;}catch(_){return null;}}
function readiness(view,config,session){
 if(config.privateHistoryEnabled!==true||!view.PrivateHistory)return'OFF';
 const origin=storedOrigin(view);if(origin===null)return'REQUEST_INVALID';if(!origin||origin!==config.privateHistoryWorkerOrigin)return'ORIGIN_UNAPPROVED';
 if(!session||!session.state().connected)return'AUTH_REQUIRED';return'READY';
}
function closesFrom(view,payload,symbol){
 const R=view.VirtualTradingRunner;if(!R||typeof R.seriesFromHistory!=='function')throw Error('HISTORY_FORMAT_INVALID');
 const[closes,code]=R.seriesFromHistory(payload,symbol,'USD');if(code)throw Error(code);
 return Object.keys(closes).sort().map(d=>[d,closes[d]]);
}
async function loadDevice(view,config){
 const session=sessionFor(view,config),ready=readiness(view,config,session);if(ready!=='READY')return{code:ready};
 const revision=session.revision();
 try{const payload=await session.fetchHistory(config.privateHistoryWorkerOrigin,CONFIG.lights.market.symbol,RANGE,{approvedOrigin:config.privateHistoryWorkerOrigin});
  if(session.revision()!==revision)return{code:'CANCELED'};
  const rows={market:marketLight(closesFrom(view,payload,CONFIG.lights.market.symbol)),credit:null};
  // HYG / IEF are requested only once both are in the Worker allowlist (owner approval); until then no request is made.
  if(!creditBlocked()){const c=CONFIG.lights.credit,read=async s=>closesFrom(view,await session.fetchHistory(config.privateHistoryWorkerOrigin,s,'1y',{approvedOrigin:config.privateHistoryWorkerOrigin}),s);
   try{rows.credit=creditLight(await read(c.numerator),await read(c.denominator));}catch(_){rows.credit=unavailable('credit','NO_DATA');}
   if(session.revision()!==revision)return{code:'CANCELED'};}
  deviceRows=rows;deviceRevision=revision;return{code:'READY'};}
 catch(e){const code=e&&typeof e.message==='string'&&/^[A-Z_]{3,40}$/.test(e.message)?e.message:'HISTORY_UNAVAILABLE';return{code};}
}

/* ---------- screen ---------- */
const NAMES={employment:['고용 악화','Employment'],inflation:['물가 과열','Inflation'],curve:['금리 곡선 역전','Yield curve'],market:['시장 스트레스','Market stress'],credit:['신용 스트레스','Credit stress']};
const STATE_LABEL={NORMAL:['정상','Normal'],WARNING:['경고','Warning'],CRISIS:['위기','Crisis']};
const pct=v=>(v*100).toFixed(2)+'%',pp=v=>v.toFixed(2)+'%p';
function detail(name,r,en){
 if(name==='credit'&&r.reason==='WORKER_ALLOWLIST_REQUIRED')return en?'Not available · Worker allowlist needed (HYG, IEF)':'확인 불가 · Worker 허용 목록 필요';
 if(r.reason==='DEVICE_NOT_LOADED')return en?'Device prices not loaded':'기기 가격을 불러오지 않았습니다';
 if(r.lit===null&&!(name==='market'&&(r.drawdown!==null||r.rv20!==null)))return(en?'No data · ':'자료 없음 · ')+r.reason;
 if(name==='employment')return(en?'3-month average ':'실업률 3개월 평균 ')+r.avg3.toFixed(2)+'% − '+(en?'12-month low ':'12개월 최저 ')+r.low12.toFixed(1)+'% = '+pp(r.gap)+' ('+r.period+')';
 if(name==='inflation')return(en?'CPI YoY ':'CPI 전년동월비 ')+pct(r.yoy)+' ('+r.period+' ÷ '+r.base_period+')';
 if(name==='curve')return(en?'10Y ':'10년 ')+r.ten_year.toFixed(2)+'% − '+(en?'3M ':'3개월 ')+r.three_month.toFixed(2)+'% = '+pp(r.spread)+' · '+(en?'inverted ':'역전 ')+r.run_days+(en?' days':'거래일')+' ('+r.date+')';
 if(name==='market')return(en?'From 52-week high ':'52주 고점 대비 ')+(r.drawdown===null?'—':pct(r.drawdown))+' · '+(en?'20-day realized vol ':'20일 실현변동성 ')+(r.rv20===null?'—':pct(r.rv20))+(r.rv_count?' ('+(en?'higher in 3y: ':'3년 중 더 높은 날 ')+r.rv_above_count+'/'+r.rv_count+')':'')+' · '+r.date+(r.lit===null?' · '+r.reason:'');
 return'HYG ÷ IEF '+(en?'20-session change ':'20거래일 변화 ')+pct(r.ratio_change)+' · '+(en?'estimate':'추정')+' ('+r.base_date+' → '+r.date+')';
}
function render(host,merged,{locale,status='',onLoad=null,legacy=null}={}){
 const doc=host.ownerDocument,en=locale==='en-US',x=(ko,e)=>en?e:ko;
 const el=(tag,text,attrs={})=>{const n=doc.createElement(tag);if(text!==undefined)n.textContent=text;for(const[k,v]of Object.entries(attrs))n.setAttribute(k,v);return n;};
 const card=el('section',undefined,{class:'card','data-macro-lights':'','data-macro-lights-state':merged.state});
 card.append(el('h2',x('매크로 상태','Macro state')),el('p',CONFIG.marker,{class:'badge','data-macro-lights-marker':''}));
 const head=el('p',undefined,{'data-macro-lights-summary':''});
 head.append(el('span',x('매크로(','Macro(')+merged.available_count+x('/5 경고등)','/5 lights)'),{'data-macro-lights-count':String(merged.available_count)}),doc.createTextNode(' · '),
  el('span',merged.available_count===0?x('매크로 확인 불가','Macro unavailable'):x(STATE_LABEL[merged.state][0],STATE_LABEL[merged.state][1]),{class:merged.available_count===0?'badge NOT_AVAILABLE':merged.state==='NORMAL'?'badge':merged.state==='WARNING'?'badge partial':'badge vt-disclaimer','data-macro-lights-verdict':merged.available_count===0?'NOT_AVAILABLE':merged.state}),
  doc.createTextNode(' · '+x('켜짐 ','lit ')+merged.lit_count+x('개','')));
 if(merged.low_confidence)head.append(doc.createTextNode(' '),el('span',x('판정 신뢰도 낮음','Low confidence'),{class:'badge partial','data-macro-low-confidence':''}));
 card.append(head);
 if(merged.available_count===0)card.append(el('p',x('매크로 자료로 인한 확대 제한 없음 · U3 확인 불가','No expansion restriction from macro data · U3 unavailable'),{class:'small','data-macro-unavailable':''}));
 const list=el('ul',undefined,{class:'list','data-macro-lights-list':''});
 for(const name of LIGHTS){const r=merged.lights[name],label=r.lit===true?x('켜짐','On'):r.lit===false?x('꺼짐','Off'):x('자료 없음','No data');
  const li=el('li',undefined,{'data-macro-light':name,'data-macro-light-state':r.lit===true?'ON':r.lit===false?'OFF':'NO_DATA'});
  li.append(el('strong',x(NAMES[name][0],NAMES[name][1])),doc.createTextNode(' · '),el('span',label,{'data-macro-light-label':'',class:r.lit===true?'badge partial':r.lit===false?'badge':'badge NOT_AVAILABLE'}),
   el('p',detail(name,r,en),{class:'small','data-macro-light-detail':''}),
   el('p',(PUBLIC_LIGHTS.includes(name)?x('공개 통계 · ','Public statistics · ')+(r.source||'—')+(r.state?' · '+r.state:''):x('기기 가격 계산 · RAM만','Device price calculation · RAM only')+(name==='credit'?x(' · 추정',' · estimate'):''))+(r.as_of?' · '+x('기준 ','as of ')+r.as_of:''),{class:'meta'}));
  list.append(li);}
 card.append(list);
 const why=merged.reasons.join(', ');
 card.append(el('p',x('판정 근거: ','Basis: ')+why+(merged.growth!==null?' · '+x('성장(GDP) ','growth (GDP) ')+pct(merged.growth)+' ('+merged.growth_period+')':' · '+x('성장(GDP) 자료 없음','growth (GDP) not available')),{class:'small','data-macro-lights-reasons':why}));
 card.append(el('p',x('자료 없는 경고등은 판정에서 뺍니다. 매크로는 무엇을 얼마나 빨리 살지만 조절하며 매도 판단에는 쓰지 않습니다. 과거 재생(2000·2008·2020·2022) 검증 전 v1 · UNCALIBRATED.','Lights without data are excluded. Macro only paces buying and is never used for sell decisions. v1 · UNCALIBRATED until the 2000/2008/2020/2022 replay is validated.'),{class:'small'}));
 if(onLoad){const b=el('button',x('SPY·HYG·IEF 불러와 경고등 계산 (기기 RAM)','Load SPY, HYG and IEF to compute lights (device RAM)'),{type:'button','data-macro-lights-load':''});b.addEventListener('click',onLoad);card.append(b);}
 card.append(el('p',status,{role:'status','data-macro-lights-status':status}));
 if(legacy){const det=el('details',undefined,{'data-macro-legacy':''});det.append(el('summary',x('자세히','Details')),el('p',x('이전 기준(v0.1.1)','Previous rule (v0.1.1)')+': '+legacy.state+(legacy.rule_label?' · '+legacy.rule_label:''),{'data-macro-legacy-state':legacy.state}));card.append(det);}
 host.replaceChildren(card);return card;
}
function mount(host,options={}){
 if(!host)return null;const view=host.ownerDocument.defaultView,config=options.config||view.InvestmentAppConfig||{},bundle=options.bundle||{},locale=options.locale;
 const session=sessionFor(view,config);if(deviceRevision!==null&&(!session||session.revision()!==deviceRevision))clearDevice();
 const legacyBlock=bundle['macro-screen.json']&&bundle['macro-screen.json'].data&&bundle['macro-screen.json'].data.growth_inflation_v0;
 const legacy=legacyBlock&&legacyBlock.engine?{state:legacyBlock.engine.state,rule_label:legacyBlock.engine.rule_label}:{state:'NOT_AVAILABLE',rule_label:null};
 let busy=false;
 const paint=status=>{if(!host.isConnected)return;const ready=readiness(view,config,session);render(host,merge(bundle),{locale,status:status||(ready==='READY'?'':ready==='OFF'?'OFF · '+(locale==='en-US'?'No price requests':'가격 호출 없음'):ready),legacy,onLoad:ready==='READY'&&!busy?load:null});};
 async function load(){if(busy)return;busy=true;paint('LOADING');try{const r=await loadDevice(view,config);busy=false;paint(r.code==='READY'?'READY':r.code);}catch(_){busy=false;paint('HISTORY_UNAVAILABLE');}}
 paint('');return Object.freeze({refresh:()=>paint('')});
}
return Object.freeze({CONFIG,LIGHTS,PUBLIC_LIGHTS,DEVICE_LIGHTS,FIELDS,REASONS,WORKER_ALLOWED,RANGE,employmentLight,inflationLight,curveLight,marketLight,creditLight,macroState,
 requirePublicBlock,publicInputs,merge,setPublic,current:currentState,clearDevice,readiness,mount,render});
});
