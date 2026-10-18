/* Stat window (owner item 1.4; owner correction 2026-10-18 for PR #311): a hexagon radar of Q · G · V plus three properties
   QGV does not capture, with comparison groups in the same polygon. Screen only: no engine, schema or storage change.

   Axes (clockwise from the top). The outer side always means "more of this property", never good or bad; the area is not a
   score. Each label states its direction (점수 ↑ / 변동성 ↑ / 낙폭 ↑ / 안정성 ↑).
   1 Q 질            public  the published Q axis score of sec-qgv2.json (qg_axes.Q.score, 0–100 as published, no re-ranking)
   2 G 성장          public  the published G axis score (same treatment)
   3 V 가치          device  the V axis score of the existing device path (QgvScores.collectQuotes -> QgvScores.compute): NA
                             without device prices (NO_DEVICE_PRICE), not applicable for the FINANCIAL profile
                             (FINANCIAL_PROFILE_V_NOT_DEFINED, "해당 없음")
   4 가격 변동성(1년) device  sample std of simple daily returns over the last 252 returns × √252 (the VirtualTradingCompare
                             volatility estimator; returns via VirtualTradingCompare.pointReturns). Outer = larger swings.
   5 최대 낙폭(1년)   device  min_t (C_t / max_{s≤t} C_s − 1) over the same 253 closes (≤ 0, the VirtualTradingCompare peak
                             rule). Outer = deeper drawdown, so the percentile is taken on −MDD.
   6 이익률 안정성     public  metrics.operating_margin_std_5y_pp (percentage points). Outer = SMALLER 5-year operating-margin
                             standard deviation (steadier), so the percentile is taken on −std.
   Device windows (4, 5) need ≥ 253 stored closes whose first is within 400 calendar days of the last, else INSUFFICIENT_SAMPLE.

   Scale. Q, G and V are already 0–100 scores and are drawn as they are. Axes 4–6 use a percentile computed in the page: the
   population is the published cross-section (Qgv2Inputs in_cross_section: LIVE/STALE rows of the file's calc_version, one
   point per issuer CIK) with the subject replacing its own issuer point; device axes use the members that have device bars,
   plus the subject. percentile(x) = 100 · (less + (equal − 1) / 2) / (n − 1) on the oriented value (QGV's average-rank rule,
   qgv/v2_scoring.py percentile), n ≥ 8 (QGV MIN_PEERS) else PEERS_TOO_FEW. The table beside the radar shows the score, or the
   raw value and its percentile.

   Comparison groups (members exclude the subject's own issuer):
   - 업종 평균: the peer grouping sec-qgv2 uses for Q (v2_scoring._peer_set): FINANCIAL profile -> all FINANCIAL rows;
     GENERAL -> the same industry_group when it has ≥ 8 issuers (subject included), else all GENERAL rows (UNIVERSE_FALLBACK).
   - SIC 평균: same 4-digit SIC when it has ≥ 8 issuers (subject included), else the same 2-digit SIC major group.
   - Group value per axis: the mean over members that have a value on that axis — Q/G: published axis scores; V: device-priced
     peers only; axes 4–6: mean of the members' percentiles (radius) and of their raw values (table). n is shown; fewer than 5
     such members -> GROUP_TOO_SMALL (NA).
   - 경쟁사 평균: no competitor set exists (REL-SOURCE undecided) -> NOT_AVAILABLE (REL_SOURCE_PENDING). Never invented.
   A missing value is NA with a reason: no vertex is drawn for it (never 0), the polygon is broken there and only a complete
   polygon is filled.

   Prices stay on this device. Axes 4–5 read this device's price tab in RAM (PriceStore.dailyCloses with fetch:false, no Worker
   request); V uses the existing QgvScores device path unchanged. Closes, quotes and every value derived from them live in memory
   and on the page only: nothing is logged, stored (no localStorage/sessionStorage/IndexedDB) or sent. No inline styles (CSP
   style-src 'self'): SVG attributes and stat-radar.css classes; every series has a text label, a line style and a marker shape. */
(function(root,factory){const api=factory(root);if(typeof module==='object'&&module.exports)module.exports=api;else root.StatRadar=api;})(typeof globalThis!=='undefined'?globalThis:this,function(g){
'use strict';
const esc=v=>String(v??'—').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const finite=v=>typeof v==='number'&&Number.isFinite(v),object=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
const tr=locale=>(ko,en)=>locale==='en-US'?en:ko;
const MIN_PEERS=8,MIN_GROUP=5,SESSIONS=252,MAX_SPAN_DAYS=400;
const FILE='sec-qgv2.json',EMPTY=Object.freeze({});
/* Axis-set label. PROVISIONAL until Main records the RADAR-AXES decision; then set state 'DECIDED' and the decision reference. */
const DECISION=Object.freeze({state:'PROVISIONAL',set:['Q·G·V + 변동성·최대낙폭·이익률 안정성','Q·G·V + volatility · max drawdown · margin stability'],ref:['소유자 지시 2026-10-18 · RADAR-AXES 기록 대기','Owner instruction 2026-10-18 · RADAR-AXES record pending']});
/* kind: SCORE (published 0–100 axis score), DEVICE_SCORE (device V score), PUBLIC / DEVICE (percentile axes). dir: +1 larger raw
   value = outer, −1 smaller raw value = outer (percentile axes only). */
const AXES=Object.freeze([
 {id:'q',kind:'SCORE',axis:'Q',unit:'score',name:['Q 질','Q quality'],lines:[['Q 질','점수 ↑'],['Q quality','score ↑']],outer:['바깥 = Q 점수가 높음','Outer = higher Q score'],how:['공개 sec-qgv2.json Q 축 점수(0–100, 그대로)','Published Q axis score (0–100, as published)']},
 {id:'g',kind:'SCORE',axis:'G',unit:'score',name:['G 성장','G growth'],lines:[['G 성장','점수 ↑'],['G growth','score ↑']],outer:['바깥 = G 점수가 높음','Outer = higher G score'],how:['공개 sec-qgv2.json G 축 점수(0–100, 그대로)','Published G axis score (0–100, as published)']},
 {id:'v',kind:'DEVICE_SCORE',axis:'V',unit:'score',name:['V 가치','V value'],lines:[['V 가치','점수 ↑'],['V value','score ↑']],outer:['바깥 = V 점수가 높음','Outer = higher V score'],how:['이 기기 시세로 계산한 V 축 점수(기존 V 경로)','V axis score from this device’s quotes (existing V path)']},
 {id:'volatility_1y',kind:'DEVICE',dir:1,unit:'pct',name:['가격 변동성(1년)','Volatility (1y)'],lines:[['가격 변동성','변동성 ↑'],['Volatility','swings ↑']],outer:['바깥 = 하루 등락이 큼','Outer = larger daily swings'],how:['일간 수익률 표본표준편차 × √252','Sample std of daily returns × √252']},
 {id:'max_drawdown_1y',kind:'DEVICE',dir:-1,unit:'pct',name:['최대 낙폭(1년)','Max drawdown (1y)'],lines:[['최대 낙폭','낙폭 ↑'],['Drawdown','depth ↑']],outer:['바깥 = 고점 대비 낙폭이 깊음','Outer = deeper fall from a peak'],how:['종가 ÷ 그때까지 최고 종가 − 1의 최솟값','min of close ÷ running peak − 1']},
 {id:'margin_stability',kind:'PUBLIC',dir:-1,unit:'pp',name:['이익률 안정성','Margin stability'],lines:[['이익률','안정성 ↑'],['Margin','stability ↑']],outer:['바깥 = 5년 영업이익률 표준편차가 작음','Outer = smaller 5-year operating-margin std'],how:['operating_margin_std_5y_pp (낮을수록 안정)','operating_margin_std_5y_pp (lower = steadier)']}]);
const SERIES=Object.freeze(['company','industry','sic','competitor']);
/* Reason texts. Existing engine codes read QgvScores / UniverseCompany texts; the codes below are this screen's own. */
const REASON={
 PEERS_TOO_FEW:['비교 모집단이 8곳 미만이라 백분위를 내지 않습니다','Fewer than 8 in the population, so no percentile'],
 GROUP_TOO_SMALL:['비교군에 값이 있는 기업이 5곳 미만입니다','Fewer than 5 group members have a value'],
 GROUP_NO_DEVICE_PRICE:['비교군 기기 가격 없음','No device prices for the group'],
 INSUFFICIENT_SAMPLE:['일봉이 1년치(253개, 400일 안)보다 적습니다','Fewer than one year of daily closes (253 within 400 days)'],
 REL_SOURCE_PENDING:['경쟁사 집합 없음(REL-SOURCE 결정 대기)','No competitor set (REL-SOURCE pending)'],
 REL_SOURCE_PENDING_LONG:['경쟁사 집합 없음: 관계 자료원(REL-SOURCE) 결정 전이라 경쟁사를 만들지 않습니다','No competitor set: the relationship source (REL-SOURCE) is undecided, so none is invented'],
 SIC_NOT_AVAILABLE:['SIC 코드가 없습니다','No SIC code'],
 PENDING:['이 기기 가격 탭을 확인하는 중','Checking this device’s price tab'],
 OFF:['이 기기에서 가격 탭이 꺼져 있습니다','Price tabs are off on this device'],
 AUTH_REQUIRED:['구글 로그인이 필요합니다','Google sign-in is required'],
 SHEET_NOT_CONNECTED:['연결된 시트가 없습니다','No sheet is connected'],
 LOADING:['가격 탭을 읽는 중','Reading the price tab'],
 ERROR:['가격 탭을 쓸 수 없습니다','Price tab unavailable']};
function reasonText(code,en){
 if(!code)return '';if(Object.hasOwn(REASON,code))return REASON[code][en?1:0];
 const UC=g.UniverseCompany&&g.UniverseCompany.SOURCE_REASON;if(UC&&Object.hasOwn(UC,code))return UC[code][en?1:0];
 const QS=g.QgvScores;return QS&&QS.REASON&&Object.hasOwn(QS.REASON,code)?QS.REASON[code][en?1:0]:code;}
const na=(reason,detail)=>({value:null,pct:null,reason,detail:detail||null});

/* ---------- published rows ---------- */
function inputsOf(screens){const F=g.Qgv2Inputs?g.Qgv2Inputs.FILE:FILE;return object(screens)&&object(screens[F])&&object(screens[F].records)?screens[F]:null;}
const scoredRow=r=>object(r)&&(r.state==='LIVE'||r.state==='STALE')&&r.identity_withdrawn!==true&&r.calc_version_mismatch!==true;
function rowReason(r){if(!object(r))return 'NOT_IN_UNIVERSE';if(r.identity_withdrawn===true)return 'IDENTITY_CONFLICT_WITHDRAWN';if(r.calc_version_mismatch===true)return 'CALC_VERSION_MISMATCH';return (Array.isArray(r.na_reasons)&&r.na_reasons[0])||'ROW_NOT_AVAILABLE';}
/* Q / G: the published axis score as it is (0–100); NA keeps the published axis reason. */
function scoreValue(axis,r){
 if(!scoredRow(r))return na(rowReason(r));const pub=object(r.qg_axes)&&object(r.qg_axes[axis])?r.qg_axes[axis]:null;
 if(pub&&finite(pub.score))return{value:pub.score,pct:pub.score,reason:null};
 return na(pub&&Array.isArray(pub.reason_codes)&&pub.reason_codes[0]||'AXIS_COVERAGE_BELOW_50');}
function marginValue(r){if(!scoredRow(r))return na(rowReason(r));const x=object(r.metrics)?r.metrics.operating_margin_std_5y_pp:null;return finite(x)?{value:x,pct:null,reason:null}:na('SEC_ITEMS_MISSING');}
/* One point per issuer: the rows Qgv2Inputs put in the cross-section (TARGET rows are never added to it). */
function crossSection(inputs){const out=[];for(const[code,r]of Object.entries(inputs.records))if(!code.startsWith('TARGET:')&&r&&r.in_cross_section===true&&typeof r.cik==='string')out.push({code,cik:r.cik,rec:r});return out.sort((a,b)=>a.code<b.code?-1:a.code>b.code?1:0);}
const UNIVERSE_CODE=/^(?:NYSE|NASDAQ|BATS):([A-Z][A-Z0-9.]{0,15})$/;
function universeSymbol(code){const PS=g.PriceStore;if(PS&&typeof PS.universeSymbol==='function')return PS.universeSymbol(code);const m=typeof code==='string'?UNIVERSE_CODE.exec(code):null;return m?m[1].replace(/\./g,'-'):null;}
const tickerOf=code=>String(code).slice(String(code).indexOf(':')+1);
/* Subject: a Universe code, or a TARGET id (its TARGET row; when that row has no data, the scored Universe row of the same CIK,
   as the score accessor does; a withdrawn or other-version TARGET row is never replaced). identity = the QgvScores identity. */
function subjectOf(inputs,spec){
 const recs=inputs?inputs.records:{};
 if(spec&&typeof spec.targetId==='string'){const id=spec.targetId,key='TARGET:'+id,rec=Object.hasOwn(recs,key)?recs[key]:null,SQ=g.SecQgv2,cik=rec&&typeof rec.cik==='string'?rec.cik:SQ&&SQ.TARGET_CIKS&&SQ.TARGET_CIKS[id]||null;
  const PH=g.PrivateHistory,symbol=PH&&PH.symbolFor?PH.symbolFor(id):null;
  if((!rec||rec.state==='NOT_AVAILABLE')&&cik){const alt=Object.keys(recs).filter(k=>!k.startsWith('TARGET:')&&recs[k].cik===cik&&scoredRow(recs[k])).sort()[0];if(alt)return{key,label:alt,rec:recs[alt],cik,symbol:symbol||universeSymbol(alt),identity:{company_id:id,ticker:tickerOf(alt)}};}
  return{key,label:id.toUpperCase(),rec,cik,symbol,identity:{company_id:id,ticker:symbol||id.toUpperCase()}};}
 const code=spec&&typeof spec.code==='string'?spec.code:'',rec=Object.hasOwn(recs,code)?recs[code]:null;
 return{key:code,label:code,rec,cik:rec&&typeof rec.cik==='string'?rec.cik:null,symbol:universeSymbol(code),identity:{company_id:code,ticker:tickerOf(code)}};}
/* QGV average-rank percentile over a sorted oriented population (qgv/v2_scoring.py percentile). */
function lower(a,x){let lo=0,hi=a.length;while(lo<hi){const m=(lo+hi)>>1;if(a[m]<x)lo=m+1;else hi=m;}return lo;}
function upper(a,x){let lo=0,hi=a.length;while(lo<hi){const m=(lo+hi)>>1;if(a[m]<=x)lo=m+1;else hi=m;}return lo;}
function percentile(sorted,x){const n=sorted.length;if(n<MIN_PEERS)return null;const less=lower(sorted,x),equal=upper(sorted,x)-less;return 100*(less+(equal-1)/2)/(n-1);}
function industryGroup(subject,points){
 const r=subject.rec;if(!scoredRow(r))return{state:'NOT_AVAILABLE',reason:rowReason(r),members:[]};
 const others=points.filter(p=>p.cik!==subject.cik);
 if(r.profile==='FINANCIAL')return{state:'OK',basis:'FINANCIAL_PROFILE',key:'FINANCIAL',members:others.filter(p=>p.rec.profile==='FINANCIAL')};
 const general=others.filter(p=>p.rec.profile!=='FINANCIAL');
 if(r.industry_group){const m=general.filter(p=>p.rec.industry_group===r.industry_group);if(m.length+1>=MIN_PEERS)return{state:'OK',basis:'INDUSTRY_GROUP',key:r.industry_group,members:m};}
 return{state:'OK',basis:'UNIVERSE_FALLBACK',key:'GENERAL',members:general};}
function sicGroup(subject,points){
 const r=subject.rec;if(!scoredRow(r))return{state:'NOT_AVAILABLE',reason:rowReason(r),members:[]};
 if(typeof r.sic!=='string'||!/^\d{4}$/.test(r.sic))return{state:'NOT_AVAILABLE',reason:'SIC_NOT_AVAILABLE',members:[]};
 const others=points.filter(p=>p.cik!==subject.cik&&typeof p.rec.sic==='string'),m4=others.filter(p=>p.rec.sic===r.sic);
 if(m4.length+1>=MIN_PEERS)return{state:'OK',basis:'SIC4',key:r.sic,members:m4};
 return{state:'OK',basis:'SIC2',key:r.sic.slice(0,2),members:others.filter(p=>p.rec.sic.slice(0,2)===r.sic.slice(0,2))};}

/* ---------- device price axes (pure) ---------- */
const DAY=/^\d{4}-\d{2}-\d{2}$/;
function returnsOf(closes){const VTC=g.VirtualTradingCompare;if(VTC&&typeof VTC.pointReturns==='function')return VTC.pointReturns(closes);const out=[];for(let i=1;i<closes.length;i++)out.push(closes[i]/closes[i-1]-1);return out;}
/* bars: [{date:'YYYY-MM-DD', close>0}] (any order; one bar per date) -> {volatility_1y, max_drawdown_1y}: {value, reason}. */
function priceMetrics(bars){
 const clean=(Array.isArray(bars)?bars:[]).filter(b=>object(b)&&typeof b.date==='string'&&DAY.test(b.date)&&finite(b.close)&&b.close>0).sort((a,b)=>a.date<b.date?-1:a.date>b.date?1:0);
 const fail=code=>({volatility_1y:{value:null,reason:code},max_drawdown_1y:{value:null,reason:code}});
 if(clean.length<SESSIONS+1)return fail('INSUFFICIENT_SAMPLE');
 const w=clean.slice(-(SESSIONS+1)),span=(Date.parse(w[w.length-1].date+'T00:00:00Z')-Date.parse(w[0].date+'T00:00:00Z'))/864e5;
 if(!(span<=MAX_SPAN_DAYS))return fail('INSUFFICIENT_SAMPLE');
 const c=w.map(b=>b.close),r=returnsOf(c);
 let m=0;for(const x of r)m+=x;m/=r.length;let v=0;for(const x of r)v+=(x-m)*(x-m);
 let peak=null,mdd=0;for(const p of c){if(peak===null||p>peak)peak=p;const dd=p/peak-1;if(dd<mdd)mdd=dd;}
 return{volatility_1y:{value:Math.sqrt(v/(r.length-1))*Math.sqrt(252),reason:null},max_drawdown_1y:{value:mdd,reason:null}};}

/* ---------- device reads (RAM only) ---------- */
let device={state:'PENDING',metrics:new Map(),priced:0};
let inflight=null,subscribed=false;
const STORE_STATES=new Set(['OFF','AUTH_REQUIRED','SHEET_NOT_CONNECTED','LOADING','READY','ERROR']);
function storeState(){const PS=g.PriceStore;if(!PS||typeof PS.status!=='function'||typeof PS.dailyCloses!=='function')return 'NOT_AVAILABLE';let s=null;try{s=PS.status().state;}catch(_){s=null;}return STORE_STATES.has(s)?s:'ERROR';}
const isoDay=ms=>new Date(ms).toISOString().slice(0,10);
/* Stored daily closes of the given symbols from this device's price tab (no Worker fetch); only the two derived metrics are
   kept, the closes are dropped right after. */
async function readDevice(symbols){
 const PS=g.PriceStore;let state=storeState();
 if(state==='OFF'||state==='AUTH_REQUIRED'||state==='SHEET_NOT_CONNECTED'||state==='NOT_AVAILABLE')return{state,metrics:new Map(),priced:0};
 const from=isoDay(Date.now()-(MAX_SPAN_DAYS+60)*864e5),metrics=new Map();
 for(const s of symbols){let closes=null;try{closes=await PS.dailyCloses(s,from,{fetch:false});}catch(_){closes=null;}
  if(!object(closes))continue;const bars=Object.keys(closes).map(d=>({date:d,close:closes[d]}));if(bars.length)metrics.set(s,priceMetrics(bars));}
 state=storeState();return{state:state==='LOADING'&&metrics.size?'READY':state,metrics,priced:metrics.size};}
/* V for the subject and every cross-section issuer through the one score accessor (same engine and population as the other
   screens): {map: code -> {value, reason}, subject}. quotes: this device's quotes (RAM). The issuer map is kept for the last
   (inputs, quotes) pair only (RAM). */
let vMemo=null;
function vOne(S,id){const row=S&&S.rows?S.rows[id]:null,d=row?row.primary:null,cov=d&&d.coverage&&d.coverage.axes?d.coverage.axes.V:null;
 return d&&finite(d.v)?{value:d.v,pct:d.v,reason:null}:na(cov&&cov.reason||'NO_DEVICE_PRICE');}
function vScores(inputs,subject,points,quotes){
 const QS=g.QgvScores,q=object(quotes)?quotes:EMPTY;if(!inputs||!QS||typeof QS.compute!=='function')return{map:new Map(),subject:na('NO_DEVICE_PRICE')};
 const run=ids=>{try{return QS.compute({identities:ids,v2Inputs:inputs,quotes:q});}catch(_){return null;}};
 if(!vMemo||vMemo.inputs!==inputs||vMemo.quotes!==q){const S=run(points.map(p=>({company_id:p.code,ticker:tickerOf(p.code)}))),map=new Map();for(const p of points)map.set(p.code,vOne(S,p.code));vMemo={inputs,quotes:q,map};}
 return{map:vMemo.map,subject:vOne(run([subject.identity]),subject.identity.company_id)};}

/* ---------- model ---------- */
function deviceValue(axis,symbol,dev){
 if(dev.state!=='READY')return na('NO_DEVICE_PRICE',Object.hasOwn(REASON,dev.state)?dev.state:null);
 const m=symbol?dev.metrics.get(symbol):null;if(!m)return na('NO_DEVICE_PRICE');
 const x=m[axis];return x&&finite(x.value)?{value:x.value,pct:null,reason:null}:na(x&&x.reason||'NO_DEVICE_PRICE');}
function mean(xs){let s=0;for(const x of xs)s+=x;return s/xs.length;}
function build(inputs,spec,dev,quotes){
 const subject=subjectOf(inputs,spec),points=inputs?crossSection(inputs):[],noFile={state:'NOT_AVAILABLE',reason:'SEC_QGV2_NOT_AVAILABLE',members:[]};
 const groups={industry:inputs?industryGroup(subject,points):noFile,sic:inputs?sicGroup(subject,points):noFile};
 const others=points.filter(p=>p.cik!==subject.cik),withdrawn=subject.rec&&subject.rec.identity_withdrawn===true,financial=scoredRow(subject.rec)&&subject.rec.profile==='FINANCIAL';
 const V=vScores(inputs,subject,points,quotes),priced=object(quotes)&&Object.keys(quotes).length>0;
 const axes=AXES.map(a=>{
  let own,valueOf;
  if(a.kind==='SCORE'){valueOf=p=>scoreValue(a.axis,p.rec);own=inputs?scoreValue(a.axis,subject.rec):na('SEC_QGV2_NOT_AVAILABLE');}
  else if(a.kind==='DEVICE_SCORE'){valueOf=p=>V.map.get(p.code)||na('NO_DEVICE_PRICE');own=inputs?V.subject:na('SEC_QGV2_NOT_AVAILABLE');}
  else if(a.kind==='PUBLIC'){valueOf=p=>marginValue(p.rec);own=inputs?marginValue(subject.rec):na('SEC_QGV2_NOT_AVAILABLE');}
  else{valueOf=p=>deviceValue(a.id,universeSymbol(p.code),dev);own=withdrawn?na('IDENTITY_CONFLICT_WITHDRAWN'):deviceValue(a.id,subject.symbol,dev);}
  const vals=new Map();for(const p of others){const x=valueOf(p);if(finite(x.value))vals.set(p.code,x.value);}
  const ranked=a.kind==='PUBLIC'||a.kind==='DEVICE';
  // Percentile axes: population = the cross-section with the subject's own issuer point replaced by the subject.
  const sorted=ranked?[...vals.values(),...(finite(own.value)?[own.value]:[])].map(v=>a.dir*v).sort((x,y)=>x-y):null,n=ranked?sorted.length:vals.size+(finite(own.value)?1:0);
  if(ranked&&finite(own.value)){own.pct=percentile(sorted,a.dir*own.value);if(own.pct===null)own.reason='PEERS_TOO_FEW';}
  const group=gr=>{if(gr.state!=='OK')return{...na(gr.reason),n:null};
   if(a.kind==='DEVICE_SCORE'&&financial)return{...na('FINANCIAL_PROFILE_V_NOT_DEFINED'),n:null};
   if((a.kind==='DEVICE'&&dev.state!=='READY')||(a.kind==='DEVICE_SCORE'&&!priced))return{...na('NO_DEVICE_PRICE'),n:0};
   const mem=gr.members.filter(p=>vals.has(p.code));if(mem.length<MIN_GROUP)return{...na('GROUP_TOO_SMALL'),n:mem.length};
   const raw=mean(mem.map(p=>vals.get(p.code)));if(!ranked)return{value:raw,pct:raw,reason:null,n:mem.length};
   if(n<MIN_PEERS)return{value:raw,pct:null,reason:'PEERS_TOO_FEW',n:mem.length};
   return{value:raw,pct:mean(mem.map(p=>percentile(sorted,a.dir*vals.get(p.code)))),reason:null,n:mem.length};};
  return{...a,population:n,company:own,industry:group(groups.industry),sic:group(groups.sic),competitor:{...na('REL_SOURCE_PENDING'),n:null}};});
 return{subject,inputs,groups,axes,device:dev,priced,points:points.length};}

/* ---------- formatting ---------- */
function fmtNum(v,locale,d=1){return new Intl.NumberFormat(locale==='en-US'?'en-US':'ko-KR',{minimumFractionDigits:d,maximumFractionDigits:d}).format(v);}
function fmtRaw(unit,v,locale){if(!finite(v))return '—';if(unit==='pp')return fmtNum(v,locale,2)+'%p';if(unit==='score')return fmtNum(v,locale,1);return fmtNum(v*100,locale,1)+'%';}
const pctText=(v,locale)=>finite(v)?fmtNum(v,locale,1):'NA';
const GROUP_NAME=(key,en)=>{const L=g.UniverseCompany&&g.UniverseCompany.GROUP_LABEL;return L&&Object.hasOwn(L,key)?L[key][en?1:0]:key;};
function groupTitle(kind,gr,T,en){
 if(kind==='industry'){if(gr.state!=='OK')return T('업종 평균','Industry average');return gr.basis==='FINANCIAL_PROFILE'?T('업종 평균 · 금융 프로필','Industry average · financial profile'):gr.basis==='INDUSTRY_GROUP'?T('업종 평균 · ','Industry average · ')+GROUP_NAME(gr.key,en):T('업종 평균 · 일반 전체(업종군 8곳 미만)','Industry average · all general (group below 8)');}
 if(gr.state!=='OK')return T('SIC 평균','SIC average');return gr.basis==='SIC4'?'SIC '+gr.key+T(' 평균',' average'):'SIC '+gr.key+'xx'+T(' 평균(4자리 8곳 미만)',' average (4-digit below 8)');}
const isScore=a=>a.kind==='SCORE'||a.kind==='DEVICE_SCORE';
const sourceBadge=(a,T)=>a.kind==='SCORE'?T('공개 점수','published score'):a.kind==='DEVICE_SCORE'?T('이 기기 시세','device quotes'):a.kind==='DEVICE'?T('이 기기 가격','device prices'):T('공개','public');

/* ---------- drawing ---------- */
const W=440,H=410,CX=220,CY=200,R=124;
let uid=0;
function pt(i,n,v){const a=-Math.PI/2+2*Math.PI*i/n,r=R*v/100;return[CX+r*Math.cos(a),CY+r*Math.sin(a)];}
const f2=x=>x.toFixed(2);
function marker(series,x,y,axis){
 const at=' data-sr-series="'+series+'" data-sr-axis="'+axis+'"';
 if(series==='company')return '<circle class="sr-mark sr-s-company" cx="'+f2(x)+'" cy="'+f2(y)+'" r="4.6"'+at+'></circle>';
 if(series==='industry')return '<rect class="sr-mark sr-s-industry" x="'+f2(x-3.8)+'" y="'+f2(y-3.8)+'" width="7.6" height="7.6"'+at+'></rect>';
 return '<path class="sr-mark sr-s-sic" d="M'+f2(x)+' '+f2(y-5)+'L'+f2(x+4.6)+' '+f2(y+3.4)+'L'+f2(x-4.6)+' '+f2(y+3.4)+'Z"'+at+'></path>';}
function seriesSvg(series,vals){
 const n=vals.length,p=vals.map((v,i)=>finite(v)?pt(i,n,v):null),cls='sr-s-'+series;let shape='';
 if(p.every(Boolean))shape='<polygon class="sr-poly '+cls+(series==='company'?' sr-fill':'')+'" points="'+p.map(q=>f2(q[0])+','+f2(q[1])).join(' ')+'" data-sr-shape="'+series+'" data-sr-complete="true"></polygon>';
 else{const d=[];for(let i=0;i<n;i++){const a=p[i],b=p[(i+1)%n];if(a&&b)d.push('M'+f2(a[0])+' '+f2(a[1])+'L'+f2(b[0])+' '+f2(b[1]));}
  if(d.length)shape='<path class="sr-poly '+cls+'" d="'+d.join('')+'" data-sr-shape="'+series+'" data-sr-complete="false"></path>';}
 return '<g class="sr-series sr-series-'+series+'">'+shape+p.map((q,i)=>q?marker(series,q[0],q[1],AXES[i].id):'').join('')+'</g>';}
function svg(model,locale){
 const T=tr(locale),en=locale==='en-US',n=model.axes.length,id='sr-rough-'+(++uid);
 const ring=v=>model.axes.map((_,i)=>pt(i,n,v)).map(q=>f2(q[0])+','+f2(q[1])).join(' ');
 const grid='<g class="sr-grid" filter="url(#'+id+')">'+[25,50,75,100].map(v=>'<polygon class="sr-ring'+(v===50?' sr-ring-mid':'')+(v===100?' sr-ring-out':'')+'" points="'+ring(v)+'"></polygon>').join('')
  +model.axes.map((_,i)=>{const q=pt(i,n,100);return '<line class="sr-spoke" x1="'+CX+'" y1="'+CY+'" x2="'+f2(q[0])+'" y2="'+f2(q[1])+'"></line>';}).join('')+'</g>';
 const ticks='<text class="sr-tick" x="'+(CX-5)+'" y="'+f2(CY-R*0.5+4)+'" text-anchor="end">50</text>';
 const labels=model.axes.map((a,i)=>{const ang=-Math.PI/2+2*Math.PI*i/n,c=Math.cos(ang),s=Math.sin(ang),x=CX+(R+16)*c,y=CY+(R+16)*s;
  const na=a.company.reason==='FINANCIAL_PROFILE_V_NOT_DEFINED'?T('해당 없음','n/a'):'NA';
  const anchor=Math.abs(c)<0.2?'middle':c>0?'start':'end',lines=[...a.lines[en?1:0],(finite(a.company.pct)?fmtNum(a.company.pct,locale,0):na)],lh=15;
  const y0=s<-0.9?y-lh*(lines.length-1):s>0.9?y+lh*0.8:y-lh*(lines.length-1)/2+4;
  return '<text class="sr-label" x="'+f2(x)+'" y="'+f2(y0)+'" text-anchor="'+anchor+'" data-sr-label="'+a.id+'">'+lines.map((t,k)=>'<tspan x="'+f2(x)+'" dy="'+(k?lh:0)+'"'+(k===lines.length-1?' class="sr-label-val'+(finite(a.company.pct)?'':' sr-label-na')+'"':'')+'>'+esc(t)+'</tspan>').join('')+'</text>';}).join('');
 const summary=T('스탯창(레이더). 바깥일수록 그 성질이 큼, 좋고 나쁨이 아님. 면적은 점수가 아님. ','Stat window (radar). Outer = more of the property, not good or bad. Area is not a score. ')
  +model.axes.map(a=>T(a.name[0],a.name[1])+': '+T('기업 ','company ')+pctText(a.company.pct,locale)+', '+T('업종 평균 ','industry ')+pctText(a.industry.pct,locale)+', SIC '+pctText(a.sic.pct,locale)+', '+T('경쟁사 NA','competitors NA')).join('; ');
 const vals=k=>model.axes.map(a=>a[k].pct);
 return '<svg class="sr-svg" viewBox="0 0 '+W+' '+H+'" role="img" aria-label="'+esc(summary)+'" focusable="false" data-sr-svg>'
  +'<defs><filter id="'+id+'" x="-5%" y="-5%" width="110%" height="110%"><feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="2" seed="7" result="n"></feTurbulence><feDisplacementMap in="SourceGraphic" in2="n" scale="2.4"></feDisplacementMap></filter></defs>'
  +grid+ticks+seriesSvg('sic',vals('sic'))+seriesSvg('industry',vals('industry'))+seriesSvg('company',vals('company'))+labels+'</svg>';}
/* Legend: every series by name, line style and marker (never colour alone). */
function swatch(series){
 const m=series==='company'?'<circle class="sr-mark sr-s-company" cx="17" cy="7" r="4"></circle>':series==='industry'?'<rect class="sr-mark sr-s-industry" x="13.5" y="3.5" width="7" height="7"></rect>':series==='sic'?'<path class="sr-mark sr-s-sic" d="M17 2.4L21.2 10L12.8 10Z"></path>':'';
 return '<svg class="sr-swatch" viewBox="0 0 34 14" aria-hidden="true" focusable="false"><line class="sr-poly sr-s-'+series+'" x1="1" y1="7" x2="33" y2="7"></line>'+m+'</svg>';}
function legend(model,locale){
 const T=tr(locale),en=locale==='en-US',gi=model.groups.industry,gs=model.groups.sic;
 const cnt=(gr,pred)=>{const xs=model.axes.filter(pred).map(a=>a[gr].n).filter(Number.isInteger);return xs.length?Math.max(...xs):0;};
 const nText=gr=>T(' · 공개 n=',' · public n=')+cnt(gr,a=>a.kind==='SCORE'||a.kind==='PUBLIC')+T(' · 기기 n=',' · device n=')+cnt(gr,a=>a.kind==='DEVICE'||a.kind==='DEVICE_SCORE');
 const item=(series,label,extra,state)=>'<li data-sr-legend="'+series+'" data-sr-legend-state="'+state+'">'+swatch(series)+'<span><b>'+esc(label)+'</b>'+(extra?' <span class="small">'+esc(extra)+'</span>':'')+'</span></li>';
 return '<ul class="sr-legend" aria-label="'+esc(T('범례','Legend'))+'">'
  +item('company',T('기업 ','Company ')+model.subject.label,T('실선 · 원','solid · circle'),model.subject.rec?'OK':'NOT_AVAILABLE')
  +item('industry',groupTitle('industry',gi,T,en),gi.state==='OK'?T('점선(긴) · 네모','dashed · square')+nText('industry'):'NOT_AVAILABLE · '+reasonText(gi.reason,en),gi.state)
  +item('sic',groupTitle('sic',gs,T,en),gs.state==='OK'?T('점선(짧은) · 세모','dotted · triangle')+nText('sic'):'NOT_AVAILABLE · '+reasonText(gs.reason,en),gs.state)
  +item('competitor',T('경쟁사 평균','Competitor average'),'NOT_AVAILABLE · '+reasonText('REL_SOURCE_PENDING_LONG',en),'NOT_AVAILABLE')+'</ul>';}
function cell(series,a,x,locale){
 const T=tr(locale),en=locale==='en-US',has=finite(x.value);
 const attrs=' data-sr-series="'+series+'" data-sr-raw="'+(has?String(x.value):'NA')+'" data-sr-pct="'+(finite(x.pct)?String(x.pct):'NA')+'" data-sr-reason="'+esc(x.reason||'')+'"'+(Number.isInteger(x.n)?' data-sr-n="'+x.n+'"':'');
 const label=series==='company'?T('기업','Company'):series==='industry'?T('업종 평균','Industry'):series==='sic'?T('SIC 평균','SIC'):T('경쟁사 평균','Competitors');
 const nTag=Number.isInteger(x.n)?' <span class="small">n='+x.n+'</span>':'';let body;
 if(has&&isScore(a))body=T(series==='company'?'점수 ':'평균 점수 ',series==='company'?'score ':'mean score ')+'<b class="num">'+esc(fmtRaw('score',x.value,locale))+'</b>'+nTag;
 else if(has)body='<span class="num">'+esc(fmtRaw(a.unit,x.value,locale))+'</span> · '+T('백분위 ','pct ')+'<b class="num">'+esc(pctText(x.pct,locale))+'</b>'+nTag+(x.reason?' <span class="small">'+esc(reasonText(x.reason,en))+'</span>':'');
 else{const code=series!=='company'&&x.reason==='NO_DEVICE_PRICE'?'GROUP_NO_DEVICE_PRICE':x.reason,badge=x.reason==='FINANCIAL_PROFILE_V_NOT_DEFINED'?T('해당 없음','n/a'):'NA';
  body='<span class="badge NOT_AVAILABLE">'+esc(badge)+'</span> <span class="small">'+esc(reasonText(code,en)+(x.detail?' · '+reasonText(x.detail,en):'')+(Number.isInteger(x.n)?' (n='+x.n+')':''))+'</span>';}
 return '<td'+attrs+' data-label="'+esc(label)+'">'+body+'</td>';}
function table(model,locale){
 const T=tr(locale),en=locale==='en-US';
 const head='<thead><tr><th scope="col">'+esc(T('축 · 바깥의 뜻','Axis · outer means'))+'</th><th scope="col">'+esc(T('기업','Company'))+'</th><th scope="col">'+esc(T('업종 평균','Industry'))+'</th><th scope="col">'+esc(T('SIC 평균','SIC'))+'</th><th scope="col">'+esc(T('경쟁사 평균','Competitors'))+'</th></tr></thead>';
 const rows=model.axes.map(a=>'<tr data-sr-axis="'+a.id+'" data-sr-kind="'+a.kind+'" data-sr-population="'+a.population+'"><th scope="row"><b>'+esc(a.name[en?1:0])+'</b> <span class="badge'+(a.kind==='DEVICE'||a.kind==='DEVICE_SCORE'?' partial':'')+'">'+esc(sourceBadge(a,T))+'</span><br><span class="small">'+esc(a.outer[en?1:0]+' · '+a.how[en?1:0]+' · '+T(isScore(a)?'점수 있는 기업 ':'모집단 ',isScore(a)?'scored companies ':'population ')+a.population)+'</span></th>'
  +cell('company',a,a.company,locale)+cell('industry',a,a.industry,locale)+cell('sic',a,a.sic,locale)+cell('competitor',a,a.competitor,locale)+'</tr>').join('');
 return '<div class="sr-table table-wrap"><table><caption class="sr-only">'+esc(T('스탯창 값: Q·G·V는 점수(0–100), 나머지는 원값과 백분위(0–100, 평균 순위)','Stat window values: Q·G·V as scores (0–100), the others as raw value and percentile (0–100, average rank)'))+'</caption>'+head+'<tbody>'+rows+'</tbody></table></div>';}
function clock(x){return typeof x==='string'&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(x)?x.slice(0,10)+' '+x.slice(11,16)+' UTC':'—';}
function body(model,locale){
 const T=tr(locale),en=locale==='en-US',d=model.device,dev=d.state==='READY'?T('읽음 · 가격 있는 종목 ','read · priced symbols ')+d.priced:d.state==='PENDING'?reasonText('PENDING',en):d.state+' · '+reasonText(d.state==='NOT_AVAILABLE'?'NO_DEVICE_PRICE':d.state,en);
 return '<div class="sr-layout"><figure class="sr-figure">'+svg(model,locale)+'<figcaption class="sr-notes small">'+esc(T('바깥일수록 그 성질이 큽니다(좋고 나쁨이 아님). 면적은 종합 점수가 아닙니다. NA 축에는 점을 찍지 않습니다(0 아님).','Outer = more of the property (not good or bad). The area is not a score. NA axes get no point (never 0).'))+'</figcaption></figure>'
  +'<div class="sr-side">'+legend(model,locale)+'</div></div>'+table(model,locale)
  +'<p class="small sr-fresh" data-sr-fresh>'+esc([T('Q·G·이익률 출처 sec-qgv2.json','Q·G·margin: sec-qgv2.json'),'as_of '+(model.inputs?clock(model.inputs.as_of):'—'),T('단면 ','cross-section ')+model.points+T('곳(발행사당 한 점)',' issuers (one point each)'),T('Q·G·V는 점수 그대로, 나머지 백분위 = 평균 순위 0–100(모집단 8곳 이상)','Q·G·V as scores; others: percentile = average rank 0–100 (population ≥ 8)'),T('비교군 평균은 5곳 이상','group averages need ≥ 5')].join(' · '))+'</p>'
  +'<p class="small sr-fresh" data-sr-device-line>'+esc([T('V: 기존 V 계산 경로(이 기기 시세 '+(model.priced?'있음':'없음')+')','V: existing V path (device quotes '+(model.priced?'present':'none')+')'),T('변동성·낙폭: 이 기기 가격 탭(Prices_D) 종가로 메모리에서만 계산, Worker 요청 없음','Volatility · drawdown: from this device’s price tab (Prices_D) closes, in memory only, no Worker request'),T('상태 ','state ')+dev,T('저장·전송·공개 안 함','never stored, sent or published')].join(' · '))+'</p>';}
function stateOf(model){return{'data-sr-subject':model.subject.label,'data-sr-device':model.device.state,'data-sr-quotes':model.priced?'PRESENT':'NONE','data-sr-industry-basis':model.groups.industry.basis||'NA','data-sr-industry-key':model.groups.industry.key||'',
 'data-sr-sic-basis':model.groups.sic.basis||'NA','data-sr-sic-key':model.groups.sic.key||''};}
const stateAttrs=model=>Object.entries(stateOf(model)).map(([k,v])=>' '+k+'="'+esc(v)+'"').join('');

/* ---------- public API ---------- */
const live=new Map();
const keyOf=spec=>spec&&typeof spec.targetId==='string'?'target:'+spec.targetId:'code:'+(spec&&spec.code||'');
/* Synchronous HTML from the already loaded public file (ctx.screens), the device quotes already in RAM (ctx.quotes) and the
   device price metrics already read (if any). spec: {code} (Universe code) or {targetId} (TARGET company id). */
function html(spec,ctx={}){
 const locale=ctx.locale==='en-US'?'en-US':'ko-KR',T=tr(locale),inputs=inputsOf(ctx.screens),key=keyOf(spec),quotes=object(ctx.quotes)?ctx.quotes:EMPTY;
 live.set(key,{spec,inputs,locale,quotes});const model=build(inputs,spec,device,quotes),decided=DECISION.state==='DECIDED';
 return '<div class="stat-radar" data-stat-radar="'+esc(key)+'" data-sr-decision="'+DECISION.state+'"'+stateAttrs(model)+'><h2 class="sr-title"><span class="hl">'+esc(T('스탯창 — QGV + QGV가 못 담는 것','Stat window — QGV + what QGV misses'))+'</span> <span class="badge'+(decided?'':' partial')+'">'+esc(decided?T('결정됨','DECIDED'):'PROVISIONAL')+'</span></h2>'
  +'<p class="small" data-sr-axis-set>'+esc(T('축: ','Axes: ')+DECISION.set[locale==='en-US'?1:0]+' · '+DECISION.ref[locale==='en-US'?1:0]+T(' · 추천 아님',' · not a recommendation'))+'</p><div data-sr-body>'+body(model,locale)+'</div></div>';}
function paint(el){const entry=live.get(el.dataset.statRadar);if(!entry)return;const model=build(entry.inputs,entry.spec,device,entry.quotes),b=el.querySelector('[data-sr-body]');
 if(b)b.innerHTML=body(model,entry.locale);for(const[k,v]of Object.entries(stateOf(model)))el.setAttribute(k,v);}
function symbolsFor(){const out=new Set();for(const{spec,inputs}of live.values()){if(!inputs)continue;const s=subjectOf(inputs,spec);if(s.symbol)out.add(s.symbol);for(const p of crossSection(inputs)){const y=universeSymbol(p.code);if(y)out.add(y);}}return[...out];}
async function refreshDevice(){
 if(inflight)return inflight;
 inflight=(async()=>{try{device=await readDevice(symbolsFor());}catch(_){device={state:'ERROR',metrics:new Map(),priced:0};}finally{inflight=null;}})();
 return inflight;}
/* Device quotes for V through the existing accessor (QgvScores.collectQuotes, RAM) unless the caller already holds them. */
async function quotesFor(entry,opts){
 if(object(opts.quotes))return{...entry.quotes,...opts.quotes};const QS=g.QgvScores;if(!entry.inputs||!QS||typeof QS.collectQuotes!=='function')return entry.quotes;
 let catalog=null;try{catalog=await opts.catalogPromise;}catch(_){catalog=null;}
 const s=subjectOf(entry.inputs,entry.spec);try{return{...entry.quotes,...await QS.collectQuotes(g,{identities:[s.identity],v2Inputs:entry.inputs,catalog})};}catch(_){return entry.quotes;}}
function radarsIn(root){if(!root)return[];const list=[];if(root.matches&&root.matches('[data-stat-radar]'))list.push(root);if(root.querySelectorAll)list.push(...root.querySelectorAll('[data-stat-radar]'));return list;}
let again=false;
function subscribeOnce(){const PS=g.PriceStore;if(subscribed||!PS||typeof PS.subscribe!=='function')return;subscribed=true;
 try{PS.subscribe(()=>{if(again)return;again=true;Promise.resolve().then(async()=>{again=false;const doc=g.document;if(!doc)return;const els=radarsIn(doc);if(!els.length)return;await refreshDevice();for(const el of radarsIn(doc))paint(el);});});}catch(_){subscribed=false;}}
/* After html(): read the device quotes (V) and the device price tab (volatility, drawdown) and repaint every radar under root.
   opts: {quotes} (quotes the caller already collected) or {catalogPromise} (device catalog for the quote accessor). */
async function mount(root,opts={}){
 const els=radarsIn(root);if(!els.length)return;subscribeOnce();
 for(const el of els){const entry=live.get(el.dataset.statRadar);if(entry)entry.quotes=await quotesFor(entry,opts||{});}
 await refreshDevice();for(const el of els)if(el.isConnected)paint(el);}
/* Model for tests and other screens (no DOM). */
function compute(spec,{screens,quotes}={},dev=device){return build(inputsOf(screens),spec,dev,object(quotes)?quotes:EMPTY);}
return Object.freeze({AXES,SERIES,DECISION,MIN_PEERS,MIN_GROUP,SESSIONS,MAX_SPAN_DAYS,REASON,percentile,priceMetrics,compute,html,mount,reasonText});
});
