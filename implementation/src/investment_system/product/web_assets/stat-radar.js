/* Stat window (owner item 1.4; owner decision 2026-10-18): a hexagon radar of Q · G · V + 가격 안정성 · 낙폭 방어력 · 상대 강도,
   with comparison groups in the same polygon. Explanatory only: official QGV scores, weights, ranks and eligibility are read,
   never changed; the polygon area is never computed. Screen only: no engine, schema or storage change.

   Every axis is a 0–100 value and the outer edge is always the better evaluation.
   1 Q 질          the published Q axis score of sec-qgv2.json (qg_axes.Q.score, as published, no re-ranking)
   2 G 성장        the published G axis score (same)
   3 V 가치        the device V axis score of the existing path (QgvScores.collectQuotes -> QgvScores.compute); 미산출 without
                   device prices (NO_DEVICE_PRICE), 해당 없음 for the FINANCIAL profile (FINANCIAL_PROFILE_V_NOT_DEFINED)
   4 가격 안정성   raw: 1-year volatility = sample std of daily simple returns × √252 (%) — the VirtualTradingCompare estimator,
                   returns via VirtualTradingCompare.pointReturns (a gap gives no return); score: percentile of −volatility
   5 낙폭 방어력   raw: 1-year max drawdown = min(close ÷ running peak − 1) (%) — the VirtualTradingCompare peak rule over the
                   present closes; score: percentile of MDD (a shallower drawdown is further out)
   6 상대 강도     raw: 6-month excess price return vs the market (%p) = (C_t ÷ C_t−126 − 1) − (SPY_t ÷ SPY_t−126 − 1), both on
                   the same price basis; score: percentile of the excess return. "시장(SPY) 대비 6개월"; not RSI.
   Auxiliary (off the default radar): 이익률 안정성 — raw metrics.operating_margin_std_5y_pp (%p), score: percentile of −std. It is
   always listed beside the radar and in the detail table, and a toggle adds it as an optional 7th axis.

   Price window (axes 4–6). Calendar = this device's SPY session dates (ReportBenchmarks' SPY calendar: the sorted SPY close
   dates); a missing close is a gap, never interpolated or carried. The window is the last 252 SPY sessions ending at the latest
   session common to SPY and the subject (the latest SPY session when the subject has no bars); every population member is
   measured on the same window. Minimum observations: 4–5 need ≥ 227 of the 252 sessions with a close (90 %); 6 needs both
   endpoint closes (t and t−126) for the company and SPY and ≥ 113 of the last 126 sessions (90 %).
   Price basis: adjusted closes when the series carries them, else raw closes; the company and SPY must share one basis, else the
   axes are 미산출 (BASIS_MISMATCH). This device's price tab (PriceStore Prices_D) keeps raw closes, so on this device the basis is
   raw. Raw closes get a corporate-action check: any close-to-close ratio within ±3 % of a typical split ratio (2, 3, 4, 5, 10,
   1/2, 1/3, 1/4, 1/5, 1/10, 3/2, 2/3) in the window makes the axes 미산출 (CORPORATE_ACTION_UNADJUSTED); nothing is adjusted here.

   Normalization: the QGV average-rank percentile, 100 · (less + (equal − 1) / 2) / (n − 1) (qgv/v2_scoring.py percentile), over
   the published cross-section (Qgv2Inputs in_cross_section: one point per issuer CIK, the file's calc_version) with the subject
   replacing its own issuer point; price axes use only the members whose bars meet the axis minimum on the same basis as SPY.
   n ≥ 8 (QGV MIN_PEERS) else PEERS_TOO_FEW.

   Groups (members exclude the subject's own issuer; same 0–100 scale as the company):
   - 업종: the sec-qgv2 Q peer rule (v2_scoring._peer_set): FINANCIAL -> all FINANCIAL rows; GENERAL -> the same industry_group
     when it has ≥ 8 issuers (subject included), else all GENERAL rows (UNIVERSE_FALLBACK).
   - SIC: the same 4-digit SIC when it has ≥ 8 issuers (subject included), else the same 2-digit group.
   - Value = mean of the members' axis values (Q/G published scores, V device scores where available, price-axis and margin
     percentiles). Fewer than 5 members with a value -> 미산출 (GROUP_TOO_SMALL) with n. Identical member sets -> one group,
     "업종 = SIC".
   - 경쟁사 평균: no competitor set (REL-SOURCE undecided) -> 미산출 (REL_SOURCE_PENDING). Never invented.
   A missing axis is 미산출 with its reason: no vertex (never 0 or an average), the polygon breaks there, only a complete polygon
   is filled.

   Prices stay on this device: closes are read from the price tab in RAM (PriceStore.dailyCloses, fetch:false, no Worker
   request) and kept only in this module's memory; V uses the existing QgvScores device path unchanged. Nothing is logged, stored
   (no localStorage/sessionStorage/IndexedDB) or sent. No inline styles (CSP style-src 'self'): SVG attributes and stat-radar.css
   classes; every series has a text label, a line style and a marker shape. */
(function(root,factory){const api=factory(root);if(typeof module==='object'&&module.exports)module.exports=api;else root.StatRadar=api;})(typeof globalThis!=='undefined'?globalThis:this,function(g){
'use strict';
const esc=v=>String(v??'—').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const finite=v=>typeof v==='number'&&Number.isFinite(v),object=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
const tr=locale=>(ko,en)=>locale==='en-US'?en:ko;
const MIN_PEERS=8,MIN_GROUP=5,SESSIONS=252,MIN_SESSIONS=227,RS_SESSIONS=126,MIN_RS_SESSIONS=113,SPLIT_TOLERANCE=0.03;
const SPLIT_RATIOS=Object.freeze([2,3,4,5,10,1/2,1/3,1/4,1/5,1/10,3/2,2/3]);
const FILE='sec-qgv2.json',SPY='SPY',EMPTY=Object.freeze({});
/* Axis-set label: the owner decision of 2026-10-18 as Main proposed it; Main switches state to 'DECIDED' once recorded. */
const DECISION=Object.freeze({state:'PROVISIONAL',set:['Q·G·V + 가격 안정성·낙폭 방어력·상대 강도','Q·G·V + price stability · drawdown defence · relative strength'],ref:['소유자 결정 2026-10-18 · 기록 대기','Owner decision 2026-10-18 · record pending']});
/* kind: SCORE (published 0–100 axis score), DEVICE_SCORE (device V score), PRICE (device price axis, percentile), PUBLIC
   (published metric, percentile). dir (percentile axes): +1 a larger raw value is better, −1 a smaller raw value is better.
   unit: score (0–100), pct (fraction shown in %), pp (fraction shown in %p), stdpp (already in %p). */
const AXES=Object.freeze([
 {id:'q',kind:'SCORE',axis:'Q',unit:'score',name:['Q 질','Q quality'],lines:[['Q 질'],['Q quality']],outer:['바깥 = 공개 Q 점수가 높음','Outer = higher published Q score']},
 {id:'g',kind:'SCORE',axis:'G',unit:'score',name:['G 성장','G growth'],lines:[['G 성장'],['G growth']],outer:['바깥 = 공개 G 점수가 높음','Outer = higher published G score']},
 {id:'v',kind:'DEVICE_SCORE',axis:'V',unit:'score',name:['V 가치','V value'],lines:[['V 가치'],['V value']],outer:['바깥 = 이 기기 V 점수가 높음','Outer = higher device V score']},
 {id:'price_stability',kind:'PRICE',dir:-1,unit:'pct',name:['가격 안정성','Price stability'],lines:[['가격 안정성'],['Price stability']],outer:['바깥 = 1년 변동성이 작음','Outer = lower 1-year volatility'],how:['원값 1년 변동성 = 일간 수익률 표본표준편차 × √252','raw: 1-year volatility = sample std of daily returns × √252']},
 {id:'drawdown_defense',kind:'PRICE',dir:1,unit:'pct',name:['낙폭 방어력','Drawdown defence'],lines:[['낙폭 방어력'],['Drawdown','defence']],outer:['바깥 = 1년 최대 낙폭이 얕음','Outer = shallower 1-year max drawdown'],how:['원값 1년 최대 낙폭 = 종가 ÷ 그때까지 최고 종가 − 1의 최솟값','raw: 1-year max drawdown = min of close ÷ running peak − 1']},
 {id:'relative_strength',kind:'PRICE',dir:1,unit:'pp',name:['상대 강도(시장(SPY) 대비 6개월)','Relative strength (vs SPY, 6 months)'],lines:[['상대 강도','SPY 대비 6개월'],['Relative','vs SPY 6m']],outer:['바깥 = 시장(SPY) 대비 6개월 초과 수익이 큼','Outer = larger 6-month excess return vs the market (SPY)'],how:['원값 (C_t ÷ C_t−126 − 1) − (SPY_t ÷ SPY_t−126 − 1) · RSI가 아님','raw: (C_t ÷ C_t−126 − 1) − (SPY_t ÷ SPY_t−126 − 1) · not RSI']}]);
const AUX=Object.freeze({id:'margin_stability',kind:'PUBLIC',dir:-1,unit:'stdpp',aux:true,name:['이익률 안정성(보조)','Margin stability (aux)'],lines:[['이익률 안정성','보조'],['Margin','stability (aux)']],outer:['바깥 = 5년 영업이익률 표준편차가 작음','Outer = smaller 5-year operating-margin std'],how:['원값 operating_margin_std_5y_pp','raw: operating_margin_std_5y_pp']});
/* Reason texts. Existing engine codes read QgvScores / UniverseCompany texts; the codes below are this screen's own. */
const REASON={
 PEERS_TOO_FEW:['비교 모집단이 8곳 미만이라 점수를 내지 않습니다','Fewer than 8 in the population, so no score'],
 GROUP_TOO_SMALL:['비교군에 값이 있는 기업이 5곳 미만입니다','Fewer than 5 group members have a value'],
 GROUP_NO_DEVICE_PRICE:['비교군 기기 가격 없음','No device prices for the group'],
 SAME_AS_INDUSTRY:['업종과 같은 기업 묶음이라 한 번만 표시합니다','Same members as the industry group, shown once'],
 INSUFFICIENT_SAMPLE:['관측 부족: 창 안 종가가 최소 기준(90%)보다 적습니다','Too few observations: fewer closes in the window than the 90% minimum'],
 HISTORY_TOO_SHORT:['시장(SPY) 일봉이 252거래일보다 짧습니다','The market (SPY) series is shorter than 252 sessions'],
 ENDPOINT_MISSING:['6개월 시작 또는 끝 종가가 없습니다(기업 또는 SPY)','A 6-month endpoint close is missing (company or SPY)'],
 CORPORATE_ACTION_UNADJUSTED:['미수정 종가에 분할로 보이는 하루 변화가 있어 계산하지 않습니다(직접 보정하지 않음)','An unadjusted close shows a split-like daily ratio, so it is not calculated (no adjustment is made here)'],
 BASIS_MISMATCH:['기업과 SPY의 가격 기준(수정·미수정)이 달라 계산하지 않습니다','The company and SPY price bases (adjusted / raw) differ, so it is not calculated'],
 SPY_NOT_AVAILABLE:['이 기기에 시장(SPY) 일봉이 없어 창을 정할 수 없습니다','No market (SPY) bars on this device, so no window'],
 NO_COMMON_SESSION:['기업과 SPY가 함께 있는 거래일이 없습니다','No session common to the company and SPY'],
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
const na=(reason,detail)=>({value:null,score:null,reason,detail:detail||null});

/* ---------- published rows ---------- */
function inputsOf(screens){const F=g.Qgv2Inputs?g.Qgv2Inputs.FILE:FILE;return object(screens)&&object(screens[F])&&object(screens[F].records)?screens[F]:null;}
const scoredRow=r=>object(r)&&(r.state==='LIVE'||r.state==='STALE')&&r.identity_withdrawn!==true&&r.calc_version_mismatch!==true;
function rowReason(r){if(!object(r))return 'NOT_IN_UNIVERSE';if(r.identity_withdrawn===true)return 'IDENTITY_CONFLICT_WITHDRAWN';if(r.calc_version_mismatch===true)return 'CALC_VERSION_MISMATCH';return (Array.isArray(r.na_reasons)&&r.na_reasons[0])||'ROW_NOT_AVAILABLE';}
/* Q / G: the published axis score as it is (0–100); 미산출 keeps the published axis reason. */
function scoreValue(axis,r){
 if(!scoredRow(r))return na(rowReason(r));const pub=object(r.qg_axes)&&object(r.qg_axes[axis])?r.qg_axes[axis]:null;
 if(pub&&finite(pub.score))return{value:pub.score,score:pub.score,reason:null};
 return na(pub&&Array.isArray(pub.reason_codes)&&pub.reason_codes[0]||'AXIS_COVERAGE_BELOW_50');}
function marginValue(r){if(!scoredRow(r))return na(rowReason(r));const x=object(r.metrics)?r.metrics.operating_margin_std_5y_pp:null;return finite(x)?{value:x,score:null,reason:null}:na('SEC_ITEMS_MISSING');}
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
const sameMembers=(a,b)=>a.state==='OK'&&b.state==='OK'&&a.members.length===b.members.length&&a.members.every((p,i)=>p.code===b.members[i].code);

/* ---------- price axes (pure) ---------- */
const DAY=/^\d{4}-\d{2}-\d{2}$/;
function returnsOf(points){const VTC=g.VirtualTradingCompare;if(VTC&&typeof VTC.pointReturns==='function')return VTC.pointReturns(points);const out=[];for(let i=1;i<points.length;i++){const a=points[i-1],b=points[i];out.push(finite(a)&&finite(b)&&a>0?b/a-1:null);}return out;}
const cleanCloses=c=>{const out={};if(object(c))for(const[d,v]of Object.entries(c))if(DAY.test(d)&&finite(v)&&v>0)out[d]=v;return out;};
/* The 252 SPY sessions ending at `end` (ReportBenchmarks.build's SPY calendar: the sorted SPY close dates). */
function priceWindow(spyCloses,end){const cal=Object.keys(spyCloses).sort(),i=cal.indexOf(end);if(i<0)return null;if(i+1<SESSIONS)return{short:true};return{sessions:cal.slice(i+1-SESSIONS,i+1)};}
/* Latest session common to SPY and the company's closes (null when none). */
function commonEnd(spyCloses,closes){const cal=Object.keys(spyCloses).sort();for(let i=cal.length-1;i>=0;i--)if(Object.hasOwn(closes,cal[i]))return cal[i];return null;}
/* Split-like close-to-close ratio between consecutive present closes (raw basis only). */
function splitLike(points){let prev=null;for(const p of points){if(!finite(p))continue;if(prev!==null){const r=p/prev;if(SPLIT_RATIOS.some(s=>Math.abs(r/s-1)<=SPLIT_TOLERANCE))return true;}prev=p;}return false;}
const PRICE_IDS=AXES.filter(a=>a.kind==='PRICE').map(a=>a.id);
const allPrice=(reason,observed=null)=>Object.fromEntries(PRICE_IDS.map(id=>[id,{value:null,reason,observed}]));
/* One series on one window. company / spy: {basis:'ADJUSTED'|'RAW', closes:{date:close}}; sessions: the window's SPY dates.
   Returns {price_stability, drawdown_defense, relative_strength}: {value (raw), reason, observed}. */
function priceAxesOn(company,spy,sessions){
 const cc=cleanCloses(company&&company.closes),sc=cleanCloses(spy&&spy.closes),basis=company&&company.basis;
 if(!basis||!spy||basis!==spy.basis)return allPrice('BASIS_MISMATCH');
 const pts=sessions.map(d=>Object.hasOwn(cc,d)?cc[d]:null),sp=sessions.map(d=>Object.hasOwn(sc,d)?sc[d]:null),observed=pts.filter(finite).length,out={};
 if(basis==='RAW'&&splitLike(pts))return allPrice('CORPORATE_ACTION_UNADJUSTED',observed);
 if(observed>=MIN_SESSIONS){
  const r=returnsOf(pts).filter(finite);let m=0;for(const x of r)m+=x;m/=r.length;let v=0;for(const x of r)v+=(x-m)*(x-m);
  out.price_stability=r.length>1?{value:Math.sqrt(v/(r.length-1))*Math.sqrt(252),reason:null,observed}:{value:null,reason:'INSUFFICIENT_SAMPLE',observed};
  let peak=null,mdd=0;for(const p of pts){if(!finite(p))continue;if(peak===null||p>peak)peak=p;const dd=p/peak-1;if(dd<mdd)mdd=dd;}out.drawdown_defense={value:mdd,reason:null,observed};
 }else{out.price_stability={value:null,reason:'INSUFFICIENT_SAMPLE',observed};out.drawdown_defense={value:null,reason:'INSUFFICIENT_SAMPLE',observed};}
 const t=sessions.length-1,b=t-RS_SESSIONS,recent=pts.slice(t-RS_SESSIONS+1).filter(finite).length;
 if(basis==='RAW'&&splitLike(sp))out.relative_strength={value:null,reason:'CORPORATE_ACTION_UNADJUSTED',observed:recent};
 else if(!finite(pts[t])||!finite(pts[b])||!finite(sp[t])||!finite(sp[b]))out.relative_strength={value:null,reason:'ENDPOINT_MISSING',observed:recent};
 else if(recent<MIN_RS_SESSIONS)out.relative_strength={value:null,reason:'INSUFFICIENT_SAMPLE',observed:recent};
 else out.relative_strength={value:(pts[t]/pts[b]-1)-(sp[t]/sp[b]-1),reason:null,observed:recent};
 return out;}
function windowInfo(sessions,basis){return{start:sessions[0],end:sessions[sessions.length-1],rs_start:sessions[sessions.length-1-RS_SESSIONS],sessions:sessions.length,basis};}
/* Pure entry point: the window from SPY and the company (end = latest common session unless given) and the three raw values. */
function priceAxes(company,spy,end=null){
 const sc=cleanCloses(spy&&spy.closes);if(!Object.keys(sc).length)return{window:null,axes:allPrice('SPY_NOT_AVAILABLE')};
 const e=end||commonEnd(sc,cleanCloses(company&&company.closes)),w=e?priceWindow(sc,e):null;
 if(!w)return{window:null,axes:allPrice('NO_COMMON_SESSION')};if(w.short)return{window:null,axes:allPrice('HISTORY_TOO_SHORT')};
 return{window:windowInfo(w.sessions,company&&company.basis||null),axes:priceAxesOn(company,{...spy,closes:sc},w.sessions)};}

/* ---------- device reads (RAM only) ---------- */
let device={state:'PENDING',series:new Map(),priced:0};
let inflight=null,subscribed=false,memo=null;
const STORE_STATES=new Set(['OFF','AUTH_REQUIRED','SHEET_NOT_CONNECTED','LOADING','READY','ERROR']);
function storeState(){const PS=g.PriceStore;if(!PS||typeof PS.status!=='function'||typeof PS.dailyCloses!=='function')return 'NOT_AVAILABLE';let s=null;try{s=PS.status().state;}catch(_){s=null;}return STORE_STATES.has(s)?s:'ERROR';}
const isoDay=ms=>new Date(ms).toISOString().slice(0,10);
/* Stored daily closes (raw basis) of SPY and the given symbols from this device's price tab, no Worker fetch. RAM only. */
async function readDevice(symbols){
 const PS=g.PriceStore;let state=storeState();
 if(state==='OFF'||state==='AUTH_REQUIRED'||state==='SHEET_NOT_CONNECTED'||state==='NOT_AVAILABLE')return{state,series:new Map(),priced:0};
 const from=isoDay(Date.now()-500*864e5),series=new Map();
 for(const s of [SPY,...symbols.filter(x=>x!==SPY)]){let c=null;try{c=await PS.dailyCloses(s,from,{fetch:false});}catch(_){c=null;}const clean=cleanCloses(c);if(Object.keys(clean).length)series.set(s,{basis:'RAW',closes:clean});}
 state=storeState();const priced=[...series.keys()].filter(s=>s!==SPY).length;return{state:state==='LOADING'&&series.size?'READY':state,series,priced};}
/* Raw price-axis values of every device series on the window ending at `end` (memoised per device read and end, RAM only). */
function priceTable(dev,end){
 if(memo&&memo.dev===dev&&memo.end===end)return memo;
 const spy=dev.series.get(SPY),w=spy&&end?priceWindow(spy.closes,end):null,values=new Map(),ok=!!(w&&!w.short);
 if(ok)for(const[s,ser]of dev.series)if(s!==SPY)values.set(s,priceAxesOn(ser,spy,w.sessions));
 memo={dev,end,sessions:ok?w.sessions:null,window:ok?windowInfo(w.sessions,spy.basis):null,short:!!(w&&w.short),values};return memo;}
/* V for the subject and every cross-section issuer through the one score accessor (same engine and population as the other
   screens). The issuer map is kept for the last (inputs, quotes) pair only (RAM). */
let vMemo=null;
function vOne(S,id){const row=S&&S.rows?S.rows[id]:null,d=row?row.primary:null,cov=d&&d.coverage&&d.coverage.axes?d.coverage.axes.V:null;
 return d&&finite(d.v)?{value:d.v,score:d.v,reason:null}:na(cov&&cov.reason||'NO_DEVICE_PRICE');}
function vScores(inputs,subject,points,quotes){
 const QS=g.QgvScores,q=object(quotes)?quotes:EMPTY;if(!inputs||!QS||typeof QS.compute!=='function')return{map:new Map(),subject:na('NO_DEVICE_PRICE')};
 const run=ids=>{try{return QS.compute({identities:ids,v2Inputs:inputs,quotes:q});}catch(_){return null;}};
 if(!vMemo||vMemo.inputs!==inputs||vMemo.quotes!==q){const S=run(points.map(p=>({company_id:p.code,ticker:tickerOf(p.code)}))),map=new Map();for(const p of points)map.set(p.code,vOne(S,p.code));vMemo={inputs,quotes:q,map};}
 return{map:vMemo.map,subject:vOne(run([subject.identity]),subject.identity.company_id)};}

/* ---------- model ---------- */
function mean(xs){let s=0;for(const x of xs)s+=x;return s/xs.length;}
function build(inputs,spec,dev,quotes,{aux=false}={}){
 const subject=subjectOf(inputs,spec),points=inputs?crossSection(inputs):[],noFile={state:'NOT_AVAILABLE',reason:'SEC_QGV2_NOT_AVAILABLE',members:[]};
 const gi=inputs?industryGroup(subject,points):noFile,gs=inputs?sicGroup(subject,points):noFile,same=sameMembers(gi,gs);
 const others=points.filter(p=>p.cik!==subject.cik),withdrawn=subject.rec&&subject.rec.identity_withdrawn===true,financial=scoredRow(subject.rec)&&subject.rec.profile==='FINANCIAL';
 const V=vScores(inputs,subject,points,quotes),priced=object(quotes)&&Object.keys(quotes).length>0;
 // Price window: the latest session common to SPY and the subject, else the latest SPY session.
 const spy=dev.series.get(SPY),own=subject.symbol?dev.series.get(subject.symbol):null,sc=spy?spy.closes:null;
 const end=sc?(own&&commonEnd(sc,own.closes))||Object.keys(sc).sort().pop():null,pt=dev.state==='READY'&&spy?priceTable(dev,end):null;
 const priceReason=dev.state!=='READY'?'NO_DEVICE_PRICE':!spy?'SPY_NOT_AVAILABLE':pt.short?'HISTORY_TOO_SHORT':null;
 const ownPrice=withdrawn||priceReason||!own?null:priceAxesOn(own,spy,pt.sessions);
 const axisModel=a=>{
  let valueOf,mine;
  if(a.kind==='SCORE'){valueOf=p=>scoreValue(a.axis,p.rec);mine=inputs?scoreValue(a.axis,subject.rec):na('SEC_QGV2_NOT_AVAILABLE');}
  else if(a.kind==='DEVICE_SCORE'){valueOf=p=>V.map.get(p.code)||na('NO_DEVICE_PRICE');mine=inputs?V.subject:na('SEC_QGV2_NOT_AVAILABLE');}
  else if(a.kind==='PUBLIC'){valueOf=p=>marginValue(p.rec);mine=inputs?marginValue(subject.rec):na('SEC_QGV2_NOT_AVAILABLE');}
  else{valueOf=p=>{if(priceReason)return na(priceReason);const x=pt.values.get(universeSymbol(p.code));return x&&finite(x[a.id].value)?{value:x[a.id].value,score:null,reason:null}:na(x?x[a.id].reason:'NO_DEVICE_PRICE');};
   const x=ownPrice?ownPrice[a.id]:null;
   mine=withdrawn?na('IDENTITY_CONFLICT_WITHDRAWN'):priceReason?na(priceReason,Object.hasOwn(REASON,dev.state)?dev.state:null):!x?na('NO_DEVICE_PRICE'):finite(x.value)?{value:x.value,score:null,reason:null,observed:x.observed}:{...na(x.reason),observed:x.observed};}
  const vals=new Map();for(const p of others){const x=valueOf(p);if(finite(x.value))vals.set(p.code,x.value);}
  const ranked=a.kind==='PUBLIC'||a.kind==='PRICE',scores=new Map();let n=vals.size+(finite(mine.value)?1:0);
  if(ranked){// Population: the cross-section with the subject's own issuer point replaced by the subject.
   const sorted=[...vals.values(),...(finite(mine.value)?[mine.value]:[])].map(v=>a.dir*v).sort((x,y)=>x-y);n=sorted.length;
   for(const[c,v]of vals){const s=percentile(sorted,a.dir*v);if(s!==null)scores.set(c,s);}
   if(finite(mine.value)){mine.score=percentile(sorted,a.dir*mine.value);if(mine.score===null)mine.reason='PEERS_TOO_FEW';}}
  else for(const[c,v]of vals)scores.set(c,v);
  const group=gr=>{if(gr.state!=='OK')return{...na(gr.reason),n:null};
   if(a.kind==='DEVICE_SCORE'&&financial)return{...na('FINANCIAL_PROFILE_V_NOT_DEFINED'),n:null};
   if(a.kind==='PRICE'&&priceReason)return{...na(priceReason),n:0};
   if(a.kind==='DEVICE_SCORE'&&!priced)return{...na('NO_DEVICE_PRICE'),n:0};
   const mem=gr.members.filter(p=>scores.has(p.code));
   if(mem.length<MIN_GROUP){const raw=gr.members.filter(p=>vals.has(p.code)).length;return{...na(ranked&&n<MIN_PEERS&&raw>=MIN_GROUP?'PEERS_TOO_FEW':'GROUP_TOO_SMALL'),n:mem.length};}
   const v=mean(mem.map(p=>scores.get(p.code)));return{value:v,score:v,reason:null,n:mem.length};};
  return{...a,population:n,company:mine,industry:group(gi),sic:same?{...na('SAME_AS_INDUSTRY'),n:null}:group(gs),competitor:{...na('REL_SOURCE_PENDING'),n:null}};};
 const auxAxis=axisModel(AUX),axes=AXES.map(axisModel);
 return{subject,inputs,groups:{industry:gi,sic:gs,same},axes:aux?[...axes,auxAxis]:axes,aux:auxAxis,auxOn:!!aux,device:dev,priced,window:pt&&!priceReason?pt.window:null,points:points.length};}

/* ---------- formatting ---------- */
function fmtNum(v,locale,d=1){return new Intl.NumberFormat(locale==='en-US'?'en-US':'ko-KR',{minimumFractionDigits:d,maximumFractionDigits:d}).format(v);}
function fmtRaw(unit,v,locale){if(!finite(v))return '—';if(unit==='score')return fmtNum(v,locale,1);if(unit==='stdpp')return fmtNum(v,locale,2)+'%p';if(unit==='pp')return fmtNum(v*100,locale,1)+'%p';return fmtNum(v*100,locale,1)+'%';}
const scoreText=(v,locale)=>finite(v)?fmtNum(v,locale,1):'미산출';
const GROUP_NAME=(key,en)=>{const L=g.UniverseCompany&&g.UniverseCompany.GROUP_LABEL;return L&&Object.hasOwn(L,key)?L[key][en?1:0]:key;};
function groupTitle(kind,gr,T,en,same){
 if(kind==='industry'){if(gr.state!=='OK')return T('업종 평균','Industry average');const base=gr.basis==='FINANCIAL_PROFILE'?T('업종 평균 · 금융 프로필','Industry average · financial profile'):gr.basis==='INDUSTRY_GROUP'?T('업종 평균 · ','Industry average · ')+GROUP_NAME(gr.key,en):T('업종 평균 · 일반 전체(업종군 8곳 미만)','Industry average · all general (group below 8)');return same?T('업종 = SIC · ','Industry = SIC · ')+base:base;}
 if(gr.state!=='OK')return T('SIC 평균','SIC average');return gr.basis==='SIC4'?'SIC '+gr.key+T(' 평균',' average'):'SIC '+gr.key+'xx'+T(' 평균(4자리 8곳 미만)',' average (4-digit below 8)');}
const isScore=a=>a.kind==='SCORE'||a.kind==='DEVICE_SCORE';
const sourceBadge=(a,T)=>a.kind==='SCORE'?T('공개 점수','published score'):a.kind==='DEVICE_SCORE'?T('이 기기 시세','device quotes'):a.kind==='PRICE'?T('이 기기 일봉','device bars'):T('공개 지표 · 보조','published metric · aux');
const clock=x=>typeof x==='string'&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(x)?x.slice(0,10)+' '+x.slice(11,16)+' UTC':'—';
/* Unit, period, as_of and basis of one axis for the detail table. */
function axisMeta(a,model,T){
 const r=model.subject.rec,pubAsOf=model.inputs?clock(model.inputs.as_of):'—',w=model.window,fy=r&&r.fiscal_year_end?r.fiscal_year_end:'—';
 if(a.kind==='SCORE')return{unit:T('점(0–100)','points (0–100)'),period:'FY '+fy,asof:pubAsOf,basis:T('공개 sec-qgv2.json','published sec-qgv2.json')};
 if(a.kind==='DEVICE_SCORE')return{unit:T('점(0–100)','points (0–100)'),period:T('현재 시세 · SEC 입력 FY ','current quote · SEC inputs FY ')+fy,asof:T('시세 시각 미보관 · 공개 ','quote time not kept · published ')+pubAsOf,basis:T('이 기기 시세(메모리)','device quote (RAM)')};
 if(a.kind==='PUBLIC')return{unit:'%p',period:T('5회계연도 · FY ','5 fiscal years · FY ')+fy,asof:pubAsOf,basis:T('공개 sec-qgv2.json','published sec-qgv2.json')};
 const per=w?(a.id==='relative_strength'?w.rs_start+' ~ '+w.end+T(' (126거래일)',' (126 sessions)'):w.start+' ~ '+w.end+T(' (252거래일)',' (252 sessions)')):'—';
 return{unit:a.unit==='pp'?'%p':'%',period:per,asof:w?w.end+T(' (마지막 공통 거래일)',' (latest common session)'):'—',basis:w?(w.basis==='ADJUSTED'?T('수정 종가 기준','adjusted closes'):T('미수정 종가 · 분할 점검','raw closes · split check')):'—'};}

/* ---------- drawing ---------- */
const W=480,H=410,CX=240,CY=200,R=124;
let uid=0;
function pt(i,n,v){const a=-Math.PI/2+2*Math.PI*i/n,r=R*v/100;return[CX+r*Math.cos(a),CY+r*Math.sin(a)];}
const f2=x=>x.toFixed(2);
function marker(series,x,y,axis){
 const at=' data-sr-series="'+series+'" data-sr-axis="'+axis+'"';
 if(series==='company')return '<circle class="sr-mark sr-s-company" cx="'+f2(x)+'" cy="'+f2(y)+'" r="4.6"'+at+'></circle>';
 if(series==='industry')return '<rect class="sr-mark sr-s-industry" x="'+f2(x-3.8)+'" y="'+f2(y-3.8)+'" width="7.6" height="7.6"'+at+'></rect>';
 return '<path class="sr-mark sr-s-sic" d="M'+f2(x)+' '+f2(y-5)+'L'+f2(x+4.6)+' '+f2(y+3.4)+'L'+f2(x-4.6)+' '+f2(y+3.4)+'Z"'+at+'></path>';}
function seriesSvg(series,axes){
 const vals=axes.map(a=>a[series].score),n=vals.length,p=vals.map((v,i)=>finite(v)?pt(i,n,v):null),cls='sr-s-'+series;let shape='';
 if(p.every(Boolean))shape='<polygon class="sr-poly '+cls+(series==='company'?' sr-fill':'')+'" points="'+p.map(q=>f2(q[0])+','+f2(q[1])).join(' ')+'" data-sr-shape="'+series+'" data-sr-complete="true"></polygon>';
 else{const d=[];for(let i=0;i<n;i++){const a=p[i],b=p[(i+1)%n];if(a&&b)d.push('M'+f2(a[0])+' '+f2(a[1])+'L'+f2(b[0])+' '+f2(b[1]));}
  if(d.length)shape='<path class="sr-poly '+cls+'" d="'+d.join('')+'" data-sr-shape="'+series+'" data-sr-complete="false"></path>';}
 return '<g class="sr-series sr-series-'+series+'">'+shape+p.map((q,i)=>q?marker(series,q[0],q[1],axes[i].id):'').join('')+'</g>';}
function svg(model,locale){
 const T=tr(locale),en=locale==='en-US',n=model.axes.length,id='sr-rough-'+(++uid),same=model.groups.same;
 const ring=v=>model.axes.map((_,i)=>pt(i,n,v)).map(q=>f2(q[0])+','+f2(q[1])).join(' ');
 const grid='<g class="sr-grid" filter="url(#'+id+')">'+[25,50,75,100].map(v=>'<polygon class="sr-ring'+(v===50?' sr-ring-mid':'')+(v===100?' sr-ring-out':'')+'" points="'+ring(v)+'"></polygon>').join('')
  +model.axes.map((_,i)=>{const q=pt(i,n,100);return '<line class="sr-spoke" x1="'+CX+'" y1="'+CY+'" x2="'+f2(q[0])+'" y2="'+f2(q[1])+'"></line>';}).join('')+'</g>';
 const ticks='<text class="sr-tick" x="'+(CX-5)+'" y="'+f2(CY-R*0.5+4)+'" text-anchor="end">50</text>';
 const labels=model.axes.map((a,i)=>{const ang=-Math.PI/2+2*Math.PI*i/n,c=Math.cos(ang),s=Math.sin(ang),x=CX+(R+16)*c,y=CY+(R+16)*s;
  const none=a.company.reason==='FINANCIAL_PROFILE_V_NOT_DEFINED'?T('해당 없음','n/a'):T('미산출','n/a');
  const anchor=Math.abs(c)<0.2?'middle':c>0?'start':'end',lines=[...a.lines[en?1:0],(finite(a.company.score)?fmtNum(a.company.score,locale,0):none)],lh=15;
  const y0=s<-0.9?y-lh*(lines.length-1):s>0.9?y+lh*0.8:y-lh*(lines.length-1)/2+4;
  return '<text class="sr-label" x="'+f2(x)+'" y="'+f2(y0)+'" text-anchor="'+anchor+'" data-sr-label="'+a.id+'">'+lines.map((t,k)=>'<tspan x="'+f2(x)+'" dy="'+(k?lh:0)+'"'+(k===lines.length-1?' class="sr-label-val'+(finite(a.company.score)?'':' sr-label-na')+'"':'')+'>'+esc(t)+'</tspan>').join('')+'</text>';}).join('');
 const summary=T('스탯창(설명용). 모든 축에서 바깥이 더 좋은 평가. 면적은 점수가 아님. ','Stat window (explanatory). Outer is better on every axis. The area is not a score. ')
  +model.axes.map(a=>T(a.name[0],a.name[1])+': '+T('기업 ','company ')+scoreText(a.company.score,locale)+', '+T(same?'업종 = SIC ':'업종 평균 ',same?'industry = SIC ':'industry ')+scoreText(a.industry.score,locale)+(same?'':', SIC '+scoreText(a.sic.score,locale))+', '+T('경쟁사 미산출','competitors n/a')).join('; ');
 return '<svg class="sr-svg" viewBox="0 0 '+W+' '+H+'" role="img" aria-label="'+esc(summary)+'" focusable="false" data-sr-svg data-sr-axes="'+n+'">'
  +'<defs><filter id="'+id+'" x="-5%" y="-5%" width="110%" height="110%"><feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="2" seed="7" result="n"></feTurbulence><feDisplacementMap in="SourceGraphic" in2="n" scale="2.4"></feDisplacementMap></filter></defs>'
  +grid+ticks+(same?'':seriesSvg('sic',model.axes))+seriesSvg('industry',model.axes)+seriesSvg('company',model.axes)+labels+'</svg>';}
/* Legend: every series by name, line style and marker (never colour alone). */
function swatch(series){
 const m=series==='company'?'<circle class="sr-mark sr-s-company" cx="17" cy="7" r="4"></circle>':series==='industry'?'<rect class="sr-mark sr-s-industry" x="13.5" y="3.5" width="7" height="7"></rect>':series==='sic'?'<path class="sr-mark sr-s-sic" d="M17 2.4L21.2 10L12.8 10Z"></path>':'';
 return '<svg class="sr-swatch" viewBox="0 0 34 14" aria-hidden="true" focusable="false"><line class="sr-poly sr-s-'+series+'" x1="1" y1="7" x2="33" y2="7"></line>'+m+'</svg>';}
function legend(model,locale){
 const T=tr(locale),en=locale==='en-US',gi=model.groups.industry,gs=model.groups.sic,same=model.groups.same;
 const cnt=(gr,pred)=>{const xs=model.axes.filter(pred).map(a=>a[gr].n).filter(Number.isInteger);return xs.length?Math.max(...xs):0;};
 const nText=gr=>T(' · 공개 n=',' · public n=')+cnt(gr,a=>a.kind==='SCORE'||a.kind==='PUBLIC')+T(' · 기기 n=',' · device n=')+cnt(gr,a=>a.kind==='PRICE'||a.kind==='DEVICE_SCORE');
 const item=(series,label,extra,state)=>'<li data-sr-legend="'+series+'" data-sr-legend-state="'+state+'">'+swatch(series)+'<span><b>'+esc(label)+'</b>'+(extra?' <span class="small">'+esc(extra)+'</span>':'')+'</span></li>';
 return '<ul class="sr-legend" aria-label="'+esc(T('범례','Legend'))+'">'
  +item('company',T('기업 ','Company ')+model.subject.label,T('실선 · 원','solid · circle'),model.subject.rec?'OK':'NOT_AVAILABLE')
  +item('industry',groupTitle('industry',gi,T,en,same),gi.state==='OK'?T('점선(긴) · 네모','dashed · square')+nText('industry'):T('미산출 · ','n/a · ')+reasonText(gi.reason,en),gi.state)
  +(same?'':item('sic',groupTitle('sic',gs,T,en,false),gs.state==='OK'?T('점선(짧은) · 세모','dotted · triangle')+nText('sic'):T('미산출 · ','n/a · ')+reasonText(gs.reason,en),gs.state))
  +item('competitor',T('경쟁사 평균','Competitor average'),T('미산출 · ','n/a · ')+reasonText('REL_SOURCE_PENDING_LONG',en),'NOT_AVAILABLE')+'</ul>';}
function auxBox(model,locale){
 const T=tr(locale),en=locale==='en-US',x=model.aux.company;
 return '<div class="sr-aux" data-sr-aux-box="'+(model.auxOn?'ON':'OFF')+'"><p class="small"><b>'+esc(T('보조 지표 · 이익률 안정성','Auxiliary · margin stability'))+'</b> '+esc(finite(x.value)?fmtRaw('stdpp',x.value,locale)+T(' (5년 영업이익률 표준편차) · 점수 ',' (5-year operating-margin std) · score ')+scoreText(x.score,locale):T('미산출 · ','n/a · ')+reasonText(x.reason,en))+'</p>'
  +'<button type="button" class="sr-aux-toggle" data-sr-aux-toggle aria-pressed="'+(model.auxOn?'true':'false')+'">'+esc(model.auxOn?T('보조 축 빼기(기본 6축)','Remove the auxiliary axis (default 6)'):T('보조 축으로 더하기(7축)','Add as an auxiliary axis (7)'))+'</button></div>';}
function cell(series,a,x,locale){
 const T=tr(locale),en=locale==='en-US',has=finite(x.score)||(series==='company'&&finite(x.value));
 const attrs=' data-sr-series="'+series+'" data-sr-raw="'+(finite(x.value)?String(x.value):'NA')+'" data-sr-score="'+(finite(x.score)?String(x.score):'NA')+'" data-sr-reason="'+esc(x.reason||'')+'"'+(Number.isInteger(x.n)?' data-sr-n="'+x.n+'"':'')+(Number.isInteger(x.observed)?' data-sr-observed="'+x.observed+'"':'');
 const label=series==='company'?T('기업','Company'):series==='industry'?T('업종 평균','Industry'):series==='sic'?T('SIC 평균','SIC'):T('경쟁사 평균','Competitors');
 let body;
 if(has&&series==='company')body=T('점수 ','score ')+'<b class="num">'+esc(scoreText(x.score,locale))+'</b>'+(isScore(a)?'':' · '+T('원값 ','raw ')+'<span class="num">'+esc(fmtRaw(a.unit,x.value,locale))+'</span>')+(Number.isInteger(x.observed)?' <span class="small">'+T('관측 ','obs ')+x.observed+'</span>':'')+(x.reason?' <span class="small">'+esc(reasonText(x.reason,en))+'</span>':'');
 else if(has)body=T('평균 점수 ','mean score ')+'<b class="num">'+esc(scoreText(x.score,locale))+'</b> <span class="small">n='+x.n+'</span>';
 else{const code=series!=='company'&&x.reason==='NO_DEVICE_PRICE'?'GROUP_NO_DEVICE_PRICE':x.reason,badge=x.reason==='FINANCIAL_PROFILE_V_NOT_DEFINED'?T('해당 없음','n/a'):T('미산출','n/a');
  body='<span class="badge NOT_AVAILABLE">'+esc(badge)+'</span> <span class="small">'+esc(reasonText(code,en)+(x.detail?' · '+reasonText(x.detail,en):'')+(Number.isInteger(x.n)?' (n='+x.n+')':'')+(Number.isInteger(x.observed)?T(' · 관측 ',' · obs ')+x.observed:''))+'</span>';}
 return '<td'+attrs+' data-label="'+esc(label)+'">'+body+'</td>';}
function table(model,locale){
 const T=tr(locale),en=locale==='en-US',same=model.groups.same,rows=[...model.axes.filter(a=>!a.aux),model.aux];
 const head='<thead><tr><th scope="col">'+esc(T('축 · 단위 · 기간 · 기준','Axis · unit · period · basis'))+'</th><th scope="col">'+esc(T('기업','Company'))+'</th><th scope="col">'+esc(same?T('업종 = SIC 평균','Industry = SIC'):T('업종 평균','Industry'))+'</th>'+(same?'':'<th scope="col">'+esc(T('SIC 평균','SIC'))+'</th>')+'<th scope="col">'+esc(T('경쟁사 평균','Competitors'))+'</th></tr></thead>';
 const row=a=>{const m=axisMeta(a,model,T);return '<tr data-sr-axis="'+a.id+'" data-sr-kind="'+a.kind+'"'+(a.aux?' data-sr-aux-row':'')+' data-sr-population="'+a.population+'" data-sr-unit="'+esc(m.unit)+'" data-sr-period="'+esc(m.period)+'" data-sr-asof="'+esc(m.asof)+'" data-sr-basis="'+esc(m.basis)+'"><th scope="row"><b>'+esc(a.name[en?1:0])+'</b> <span class="badge'+(a.kind==='PRICE'||a.kind==='DEVICE_SCORE'?' partial':'')+'">'+esc(sourceBadge(a,T))+'</span><br><span class="small">'
  +esc([a.outer[en?1:0],a.how?a.how[en?1:0]:null,T('단위 ','unit ')+m.unit,T('기간 ','period ')+m.period,'as_of '+m.asof,T('기준 ','basis ')+m.basis,T('모집단 n=','population n=')+a.population].filter(Boolean).join(' · '))+'</span></th>'
  +cell('company',a,a.company,locale)+cell('industry',a,a.industry,locale)+(same?'':cell('sic',a,a.sic,locale))+cell('competitor',a,a.competitor,locale)+'</tr>';};
 return '<div class="sr-table table-wrap"><table><caption class="sr-only">'+esc(T('스탯창 상세: 축별 점수(0–100), 원값, 단위, 기간, 기준 시점, 모집단 수','Stat window detail: per-axis score (0–100), raw value, unit, period, as_of, population count'))+'</caption>'+head+'<tbody>'+rows.map(row).join('')+'</tbody></table></div>';}
function body(model,locale){
 const T=tr(locale),en=locale==='en-US',d=model.device,dev=d.state==='READY'?T('읽음 · 가격 있는 종목 ','read · priced symbols ')+d.priced+(d.series.has(SPY)?' · SPY':T(' · SPY 없음',' · no SPY')):d.state==='PENDING'?reasonText('PENDING',en):d.state+' · '+reasonText(d.state==='NOT_AVAILABLE'?'NO_DEVICE_PRICE':d.state,en);
 return '<div class="sr-layout"><figure class="sr-figure">'+svg(model,locale)+'<figcaption class="sr-notes small">'+esc(T('모든 축에서 바깥이 더 좋은 평가입니다. 설명용이며 공식 QGV 점수·비중·순위를 바꾸지 않습니다. 면적은 계산하지 않습니다. 미산출 축에는 점을 찍지 않습니다(0이나 평균으로 채우지 않음).','Outer is the better evaluation on every axis. Explanatory only: official QGV scores, weights and ranks are unchanged. The area is not computed. 미산출 axes get no point (never 0 or an average).'))+'</figcaption></figure>'
  +'<div class="sr-side">'+legend(model,locale)+auxBox(model,locale)+'</div></div>'+table(model,locale)
  +'<p class="small sr-fresh" data-sr-fresh>'+esc([T('Q·G·이익률 출처 sec-qgv2.json','Q·G·margin: sec-qgv2.json'),'as_of '+(model.inputs?clock(model.inputs.as_of):'—'),T('단면 ','cross-section ')+model.points+T('곳(발행사당 한 점)',' issuers (one point each)'),T('가격 축 점수 = 평균 순위 백분위(모집단 8곳 이상) · 비교군 평균은 5곳 이상','price-axis score = average-rank percentile (population ≥ 8) · group averages need ≥ 5')].join(' · '))+'</p>'
  +'<p class="small sr-fresh" data-sr-device-line>'+esc([T('V: 기존 V 계산 경로(이 기기 시세 '+(model.priced?'있음':'없음')+')','V: existing V path (device quotes '+(model.priced?'present':'none')+')'),T('가격 축: 이 기기 가격 탭(Prices_D) 일봉, SPY 거래일 252일 창, 메모리에서만 계산, Worker 요청 없음','Price axes: this device’s price tab (Prices_D) bars, 252 SPY-session window, in memory only, no Worker request'),T('상태 ','state ')+dev,T('저장·전송·공개 안 함','never stored, sent or published')].join(' · '))+'</p>';}
function stateOf(model){return{'data-sr-subject':model.subject.label,'data-sr-device':model.device.state,'data-sr-quotes':model.priced?'PRESENT':'NONE','data-sr-groups':model.groups.same?'SAME':'DISTINCT','data-sr-aux':model.auxOn?'ON':'OFF','data-sr-window-end':model.window?model.window.end:'NA',
 'data-sr-industry-basis':model.groups.industry.basis||'NA','data-sr-industry-key':model.groups.industry.key||'','data-sr-sic-basis':model.groups.sic.basis||'NA','data-sr-sic-key':model.groups.sic.key||''};}
const stateAttrs=model=>Object.entries(stateOf(model)).map(([k,v])=>' '+k+'="'+esc(v)+'"').join('');

/* ---------- public API ---------- */
const live=new Map();
const keyOf=spec=>spec&&typeof spec.targetId==='string'?'target:'+spec.targetId:'code:'+(spec&&spec.code||'');
/* Synchronous HTML from the loaded public file (ctx.screens), device quotes already in RAM (ctx.quotes) and the device bars
   already read (if any). spec: {code} (Universe code) or {targetId} (TARGET company id). */
function html(spec,ctx={}){
 const locale=ctx.locale==='en-US'?'en-US':'ko-KR',T=tr(locale),inputs=inputsOf(ctx.screens),key=keyOf(spec),quotes=object(ctx.quotes)?ctx.quotes:EMPTY,prev=live.get(key),aux=!!(prev&&prev.aux);
 live.set(key,{spec,inputs,locale,quotes,aux});const model=build(inputs,spec,device,quotes,{aux}),decided=DECISION.state==='DECIDED';
 return '<div class="stat-radar" data-stat-radar="'+esc(key)+'" data-sr-decision="'+DECISION.state+'"'+stateAttrs(model)+'><h2 class="sr-title"><span class="hl">'+esc(T('스탯창','Stat window'))+'</span> <span class="badge'+(decided?'':' partial')+'">'+esc(decided?T('결정됨','DECIDED'):'PROVISIONAL')+'</span></h2>'
  +'<p class="small" data-sr-axis-set>'+esc(T('축: ','Axes: ')+DECISION.set[locale==='en-US'?1:0]+' · '+DECISION.ref[locale==='en-US'?1:0]+T(' · 설명용 · 추천 아님',' · explanatory · not a recommendation'))+'</p><div data-sr-body>'+body(model,locale)+'</div></div>';}
function paint(el){const entry=live.get(el.dataset.statRadar);if(!entry)return;const model=build(entry.inputs,entry.spec,device,entry.quotes,{aux:entry.aux}),b=el.querySelector('[data-sr-body]');
 if(b)b.innerHTML=body(model,entry.locale);for(const[k,v]of Object.entries(stateOf(model)))el.setAttribute(k,v);}
function symbolsFor(){const out=new Set();for(const{spec,inputs}of live.values()){if(!inputs)continue;const s=subjectOf(inputs,spec);if(s.symbol)out.add(s.symbol);for(const p of crossSection(inputs)){const y=universeSymbol(p.code);if(y)out.add(y);}}return[...out];}
async function refreshDevice(){
 if(inflight)return inflight;
 inflight=(async()=>{try{device=await readDevice(symbolsFor());}catch(_){device={state:'ERROR',series:new Map(),priced:0};}finally{inflight=null;}})();
 return inflight;}
/* Device quotes for V through the existing accessor (QgvScores.collectQuotes, RAM) unless the caller already holds them. */
async function quotesFor(entry,opts){
 if(object(opts.quotes))return opts.quotes;const QS=g.QgvScores;if(!entry.inputs||!QS||typeof QS.collectQuotes!=='function')return entry.quotes;
 let catalog=null;try{catalog=await opts.catalogPromise;}catch(_){catalog=null;}
 const s=subjectOf(entry.inputs,entry.spec);let q=null;try{q=await QS.collectQuotes(g,{identities:[s.identity],v2Inputs:entry.inputs,catalog});}catch(_){q=null;}
 return object(q)&&Object.keys(q).length?{...entry.quotes,...q}:entry.quotes;}
function radarsIn(root){if(!root)return[];const list=[];if(root.matches&&root.matches('[data-stat-radar]'))list.push(root);if(root.querySelectorAll)list.push(...root.querySelectorAll('[data-stat-radar]'));return list;}
let again=false,wired=false;
function subscribeOnce(){const PS=g.PriceStore;if(subscribed||!PS||typeof PS.subscribe!=='function')return;subscribed=true;
 try{PS.subscribe(()=>{if(again)return;again=true;Promise.resolve().then(async()=>{again=false;const doc=g.document;if(!doc)return;const els=radarsIn(doc);if(!els.length)return;await refreshDevice();for(const el of radarsIn(doc))paint(el);});});}catch(_){subscribed=false;}}
/* The auxiliary-axis toggle (event delegation; no inline handlers under the CSP). The choice lives in RAM for this page only. */
function wireOnce(doc){if(wired||!doc||typeof doc.addEventListener!=='function')return;wired=true;
 doc.addEventListener('click',e=>{const b=e.target&&e.target.closest?e.target.closest('[data-sr-aux-toggle]'):null;if(!b)return;const el=b.closest('[data-stat-radar]'),entry=el?live.get(el.dataset.statRadar):null;if(!entry)return;
  entry.aux=!entry.aux;paint(el);const nb=el.querySelector('[data-sr-aux-toggle]');if(nb)nb.focus();});}
/* After html(): read the device quotes (V) and this device's price tab (price axes) and repaint every radar under root.
   opts: {quotes} (quotes the caller already collected) or {catalogPromise} (device catalog for the quote accessor). */
async function mount(root,opts={}){
 const els=radarsIn(root);if(!els.length)return;subscribeOnce();wireOnce(els[0].ownerDocument);
 for(const el of els){const entry=live.get(el.dataset.statRadar);if(entry)entry.quotes=await quotesFor(entry,opts||{});}
 await refreshDevice();for(const el of els)if(el.isConnected)paint(el);}
/* Model for tests and other screens (no DOM). */
function compute(spec,{screens,quotes,aux=false}={},dev=device){return build(inputsOf(screens),spec,dev,object(quotes)?quotes:EMPTY,{aux});}
return Object.freeze({AXES,AUX,DECISION,MIN_PEERS,MIN_GROUP,SESSIONS,MIN_SESSIONS,RS_SESSIONS,MIN_RS_SESSIONS,SPLIT_RATIOS,REASON,percentile,priceAxes,compute,html,mount,reasonText});
});
