/* Stat window (owner item 1.4; owner decisions 2026-10-18, PR #311): a hexagon radar of the core axes Q · G · V and three
   CANDIDATE price axes (가격 안정성 · 낙폭 방어력 · 상대 강도, "후보 축(커버리지 확인 전)": an axis is adopted only when it has a verified
   value and a displayed score for ≥ 454 of the 504 Universe companies), with comparison groups in the same polygon, plus the
   approved auxiliary 이익률 안정성 indicator. Explanatory only: official QGV
   scores, weights, ranks and eligibility are read, never changed; the polygon area is never computed. Screen only.

   Every drawn value is 0–100 and the outer edge is always the better evaluation.
   1 Q 질          the published Q axis score of sec-qgv2.json (qg_axes.Q.score, as published, no re-ranking)
   2 G 성장        the published G axis score (same)
   3 V 가치        the V axis score of the existing device path (QgvScores.collectQuotes -> QgvScores.compute); 미산출 without
                   quotes, with the engine's own reason (NO_DEVICE_PRICE, DEBT_CASH_NOT_AVAILABLE, EV_NON_POSITIVE, …); for the FINANCIAL
                   profile exactly '현재 금융업 가치평가 모델 미지원' (FINANCIAL_PROFILE_V_NOT_DEFINED) — a model scope, not a data failure;
                   no other metric ever stands in for V. The V detail lists the individual value inputs (vDetailHtml)
   4 가격 안정성   raw: 1-year volatility = sample std of VALID daily simple returns × √252 (%) — the VirtualTradingCompare
                   estimator, returns via VirtualTradingCompare.pointReturns on the SPY-session-aligned series, so a return is
                   valid only when both adjacent sessions have a close (a multi-day move across a gap is never a daily return)
   5 낙폭 방어력   raw: 1-year max drawdown = min(close ÷ running peak − 1) over the present closes (%); with gaps in the window
                   the true trough may have been missed, which the detail states
   6 상대 강도     raw: 6-month excess price return vs the market (%p) = (C_t ÷ C_t−126 − 1) − (SPY_t ÷ SPY_t−126 − 1). Not RSI.
   Price-axis scores (4–6) are "기기 보유 데이터 내 상대점수": the average-rank percentile among the issuers whose prices this user
   holds — never a 504-wide or market-wide percentile. Score directions: −volatility, MDD, excess return.
   Auxiliary (off the default radar): 이익률 안정성 — metrics.operating_margin_std_5y_pp (%p, population std of EBIT / revenue
   over FY0..FY-4), score = percentile of −std; beside the radar, in the detail table, as an optional 7th axis (toggle, RAM)
   and in the company financial detail (marginDetail).

   Price window (4–6). Calendar = the SPY session dates of the user's price data (ReportBenchmarks' SPY calendar: the sorted
   SPY close dates); a missing close is a gap, never interpolated or carried. Window = the last 252 SPY sessions ending at the
   latest session common to SPY and the subject (else the latest SPY session); every member is measured on the same window.
   Minimums: 4 needs ≥ 227 closes and ≥ 226 valid daily returns (90 % of 252 / 251); 5 needs ≥ 227 closes; 6 needs both
   endpoints (t, t−126) for the company and SPY and ≥ 113 of the last 126 sessions. Closes and valid returns are counted apart.
   Freshness: the window end is shown as "기준 거래일 YYYY-MM-DD · N일 전"; more than 5 sessions behind the latest SPY session or
   more than 7 calendar days old is STALE (muted, dashed polygon and a STALE label).

   Price basis. A series carries {basis, source, storage, as_of}. Scores and raw values are produced only on a CONFIRMED adjusted
   basis — SPLIT_ADJUSTED or TOTAL_RETURN (split + dividend) — shared by the company, SPY and every comparison member; a member
   on another basis is left out of the population and listed as such, a company/SPY mismatch is BASIS_MISMATCH. A raw-close
   series cannot confirm corporate-action handling, so it is 미산출 ADJUSTMENT_BASIS_UNCONFIRMED (a split-like close-to-close
   ratio within ±3 % of 2, 3, 4, 5, 10, their inverses, 3/2 or 2/3 is reported as CORPORATE_ACTION_UNADJUSTED instead; jump
   detection never confirms continuity). An adjusted series whose basis is not stated is ADJUSTMENT_BASIS_UNCONFIRMED too.
   Closes are never overwritten or adjusted here.
   Price inputs and where they live: the closes are the user's Prices_D tab of THEIR PRIVATE GOOGLE SHEET (PriceStore; raw closes
   from the private Worker: Yahoo chart, Tiingo/KRX fallback), read with PriceStore.dailyCloses(fetch:false) — no Worker request
   here — into this browser's memory (RAM) only; nothing is written to localStorage/IndexedDB, logs or files, and nothing is
   published. On that basis every price axis is ADJUSTMENT_BASIS_UNCONFIRMED today. The Worker's bars also carry
   adjusted_close (Yahoo chart adjclose; Tiingo adjClose on fallback) but the Worker does not state its basis and those bars stay
   inside the chart view's RAM, so no adjusted series is connected yet. V comes from the shared page result (QgvScores.pageResult; quotes from the Universe tab of the user's
   private Google Sheet, quotes stored in this browser and Worker closes, computed in RAM).

   Normalization: the QGV average-rank percentile 100 · (less + (equal − 1) / 2) / (n − 1) (qgv/v2_scoring.py percentile) over
   the published cross-section (Qgv2Inputs in_cross_section: one point per issuer CIK, the file's calc_version) with the subject
   replacing its own issuer point. A raw value is shown whenever it is verified; only the score becomes 미산출 (PEERS_TOO_FEW, n)
   when the population has fewer than 8.

   Groups (members exclude the subject's issuer; same 0–100 scale as the company): 업종 = the sec-qgv2 Q peer rule
   (v2_scoring._peer_set: FINANCIAL -> all FINANCIAL rows; GENERAL -> the same industry_group with ≥ 8 issuers incl. the subject,
   else all GENERAL rows); SIC = the same 4-digit SIC with ≥ 8 issuers, else the same 2-digit group. Value = mean member score;
   fewer than 5 -> 미산출 GROUP_TOO_SMALL (n). Identical member sets are drawn once ("업종 = SIC"). 경쟁사 평균: 미산출
   (REL_SOURCE_PENDING). The comparison companies of every axis (count, codes, period) are listed in the detail.
   A missing value is 미산출 with its reason: no vertex (never 0 or an average), the polygon breaks there, only a complete polygon
   is filled. No inline styles (CSP style-src 'self'); every series has a text label, a line style and a marker shape. */
(function(root,factory){const api=factory(root);if(typeof module==='object'&&module.exports)module.exports=api;else root.StatRadar=api;})(typeof globalThis!=='undefined'?globalThis:this,function(g){
'use strict';
const esc=v=>String(v??'—').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const finite=v=>typeof v==='number'&&Number.isFinite(v),object=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
const tr=locale=>(ko,en)=>locale==='en-US'?en:ko;
const MIN_PEERS=8,MIN_GROUP=5,SESSIONS=252,MIN_SESSIONS=227,MIN_RETURNS=226,RS_SESSIONS=126,MIN_RS_SESSIONS=113,SPLIT_TOLERANCE=0.03;
const STALE_SESSIONS=5,STALE_DAYS=7;
const SPLIT_RATIOS=Object.freeze([2,3,4,5,10,1/2,1/3,1/4,1/5,1/10,3/2,2/3]);
const CONFIRMED_BASES=Object.freeze(['SPLIT_ADJUSTED','TOTAL_RETURN']),BASES=Object.freeze(['RAW','SPLIT_ADJUSTED','TOTAL_RETURN','ADJUSTED_UNCONFIRMED']);
const FILE='sec-qgv2.json',SPY='SPY';
/* Financial-profile V: a model scope, shown with this exact text and never styled or counted as a data failure. */
const FIN_V_FALLBACK=Object.freeze(['현재 금융업 가치평가 모델 미지원','Financial-sector valuation model not supported yet']),FIN_V=Object.freeze([['금융업','모델 미지원'],['Financials','not supported']]);
/* Axis-set label (owner rule 2026-10-18): Q·G·V are the core axes; the three price axes are CANDIDATES until coverage is
   confirmed. Adoption rule: an axis needs a verified value AND a displayed score for ≥ ADOPT_MIN of the 504 Universe
   companies. The 이익률 안정성 auxiliary display is approved. */
const ADOPT_MIN=454,UNIVERSE_SIZE=504;
const DECISION=Object.freeze({state:'CANDIDATE',set:['핵심 축 Q·G·V + 후보 축(커버리지 확인 전) 가격 안정성·낙폭 방어력·상대 강도','Core axes Q·G·V + candidate axes (coverage unconfirmed): price stability · drawdown defence · relative strength'],ref:['채택 기준: 504곳 중 '+ADOPT_MIN+'곳 이상 검증 값·점수 · 이익률 안정성 보조 표시 승인','Adoption: verified value and score for ≥ '+ADOPT_MIN+' of 504 · margin-stability auxiliary display approved']});
/* kind: SCORE (published 0–100 axis score), DEVICE_SCORE (device V score), PRICE (price axis, relative score), PUBLIC
   (published metric, percentile). dir (percentile axes): +1 a larger raw value is better, −1 a smaller raw value is better.
   unit: score (0–100), pct (fraction shown in %), pp (fraction shown in %p), stdpp (already in %p). */
const AXES=Object.freeze([
 {id:'q',kind:'SCORE',axis:'Q',unit:'score',name:['Q 질','Q quality'],lines:[['Q 질'],['Q quality']],outer:['바깥 = 공개 Q 점수가 높음','Outer = higher published Q score']},
 {id:'g',kind:'SCORE',axis:'G',unit:'score',name:['G 성장','G growth'],lines:[['G 성장'],['G growth']],outer:['바깥 = 공개 G 점수가 높음','Outer = higher published G score']},
 {id:'v',kind:'DEVICE_SCORE',axis:'V',unit:'score',name:['V 가치','V value'],lines:[['V 가치'],['V value']],outer:['바깥 = V 점수가 높음(기존 V 경로)','Outer = higher V score (existing V path)']},
 {id:'price_stability',kind:'PRICE',dir:-1,unit:'pct',name:['가격 안정성','Price stability'],lines:[['가격 안정성','후보'],['Price stability','candidate']],outer:['바깥 = 1년 변동성이 작음','Outer = lower 1-year volatility'],how:['원값 1년 변동성 = 유효 일간 수익률 표본표준편차 × √252','raw: 1-year volatility = sample std of valid daily returns × √252']},
 {id:'drawdown_defense',kind:'PRICE',dir:1,unit:'pct',name:['낙폭 방어력','Drawdown defence'],lines:[['낙폭 방어력','후보'],['Drawdown defence','candidate']],outer:['바깥 = 1년 최대 낙폭이 얕음','Outer = shallower 1-year max drawdown'],how:['원값 1년 최대 낙폭 = 종가 ÷ 그때까지 최고 종가 − 1의 최솟값','raw: 1-year max drawdown = min of close ÷ running peak − 1']},
 {id:'relative_strength',kind:'PRICE',dir:1,unit:'pp',name:['상대 강도(시장(SPY) 대비 6개월)','Relative strength (vs SPY, 6 months)'],lines:[['상대 강도 · 후보','SPY 대비 6개월'],['Relative (cand.)','vs SPY 6m']],outer:['바깥 = 시장(SPY) 대비 6개월 초과 수익이 큼','Outer = larger 6-month excess return vs the market (SPY)'],how:['원값 (C_t ÷ C_t−126 − 1) − (SPY_t ÷ SPY_t−126 − 1) · RSI가 아님','raw: (C_t ÷ C_t−126 − 1) − (SPY_t ÷ SPY_t−126 − 1) · not RSI']}]);
const AUX=Object.freeze({id:'margin_stability',kind:'PUBLIC',dir:-1,unit:'stdpp',aux:true,name:['이익률 안정성(보조)','Margin stability (aux)'],lines:[['이익률 안정성','보조'],['Margin','stability (aux)']],outer:['바깥 = 5년 영업이익률 표준편차가 작음','Outer = smaller 5-year operating-margin std'],how:['원값 operating_margin_std_5y_pp','raw: operating_margin_std_5y_pp']});
/* Reason texts. Existing engine codes read QgvScores / UniverseCompany texts; the codes below are this screen's own. */
const REASON={
 PEERS_TOO_FEW:['비교 모집단이 8곳 미만이라 상대점수를 내지 않습니다(원값은 표시)','Fewer than 8 in the population, so no relative score (raw value shown)'],
 GROUP_TOO_SMALL:['비교군에 값이 있는 기업이 5곳 미만입니다','Fewer than 5 group members have a value'],
 GROUP_NO_DEVICE_PRICE:['비교군 가격 자료 없음','No price data for the group'],
 SAME_AS_INDUSTRY:['업종과 같은 기업 묶음이라 한 번만 표시합니다','Same members as the industry group, shown once'],
 INSUFFICIENT_SAMPLE:['관측 부족: 창 안 종가 또는 유효 일간 수익률이 최소 기준(90%)보다 적습니다','Too few observations: closes or valid daily returns below the 90% minimum'],
 HISTORY_TOO_SHORT:['시장(SPY) 일봉이 252거래일보다 짧습니다','The market (SPY) series is shorter than 252 sessions'],
 ENDPOINT_MISSING:['6개월 시작 또는 끝 종가가 없습니다(기업 또는 SPY)','A 6-month endpoint close is missing (company or SPY)'],
 ADJUSTMENT_BASIS_UNCONFIRMED:['가격 조정 기준(분할·배당 처리)을 확인할 수 없어 계산하지 않습니다','The price adjustment basis (split / dividend handling) cannot be confirmed, so it is not calculated'],
 CORPORATE_ACTION_UNADJUSTED:['미수정 종가에 분할로 보이는 하루 변화가 있습니다(조정 기준 미확인 · 직접 보정하지 않음)','An unadjusted close shows a split-like daily ratio (basis unconfirmed · no adjustment made)'],
 BASIS_MISMATCH:['기업·SPY·비교 기업의 가격 기준이 달라 계산하지 않습니다','The company, SPY and members are on different price bases, so it is not calculated'],
 SPY_NOT_AVAILABLE:['내 가격 자료에 시장(SPY) 일봉이 없어 창을 정할 수 없습니다','No market (SPY) bars in your price data, so no window'],
 NO_COMMON_SESSION:['기업과 SPY가 함께 있는 거래일이 없습니다','No session common to the company and SPY'],
 REL_SOURCE_PENDING:['경쟁사 집합 없음(REL-SOURCE 결정 대기)','No competitor set (REL-SOURCE pending)'],
 REL_SOURCE_PENDING_LONG:['경쟁사 집합 없음: 관계 자료원(REL-SOURCE) 결정 전이라 경쟁사를 만들지 않습니다','No competitor set: the relationship source (REL-SOURCE) is undecided, so none is invented'],
 SIC_NOT_AVAILABLE:['SIC 코드가 없습니다','No SIC code'],
 MDD_GAPS:['결측 구간 때문에 실제 저점을 놓쳤을 수 있음','The true trough may have been missed because of gaps'],
 PENDING:['확인하는 중','Checking'],
 OFF:['이 브라우저에서 가격 탭(내 구글 시트 Prices_D) 사용이 꺼져 있습니다','Price tabs (Prices_D in your Google Sheet) are off in this browser'],
 AUTH_REQUIRED:['구글 로그인이 필요합니다','Google sign-in is required'],
 SHEET_NOT_CONNECTED:['연결된 시트가 없습니다','No sheet is connected'],
 LOADING:['가격 탭을 읽는 중','Reading the price tab'],
 ERROR:['가격 탭을 쓸 수 없습니다','Price tab unavailable']};
function reasonText(code,en){
 if(!code)return '';if(Object.hasOwn(REASON,code))return REASON[code][en?1:0];
 const UC=g.UniverseCompany&&g.UniverseCompany.SOURCE_REASON;if(UC&&Object.hasOwn(UC,code))return UC[code][en?1:0];
 const QS=g.QgvScores;return QS&&QS.REASON&&Object.hasOwn(QS.REASON,code)?QS.REASON[code][en?1:0]:code;}
const na=(reason,detail)=>({value:null,score:null,reason,score_reason:null,detail:detail||null});


/* The financial-profile V text from the engine's own reason text (QgvScores.reasonText), the same words as every screen. */
const finText=en=>{const QS=g.QgvScores,t=QS&&QS.REASON&&QS.REASON.FINANCIAL_PROFILE_V_NOT_DEFINED;return t?t[en?1:0]:FIN_V_FALLBACK[en?1:0];};
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
/* A price series: {closes:{date:close}, basis, source, storage, as_of}; basis outside BASES reads as ADJUSTED_UNCONFIRMED. */
function series(x){const s=object(x)?x:{};return{closes:cleanCloses(s.closes),basis:BASES.includes(s.basis)?s.basis:'ADJUSTED_UNCONFIRMED',source:typeof s.source==='string'?s.source:null,storage:typeof s.storage==='string'?s.storage:null,as_of:typeof s.as_of==='string'?s.as_of:null};}
/* The 252 SPY sessions ending at `end` (ReportBenchmarks.build's SPY calendar: the sorted SPY close dates). */
function priceWindow(spyCloses,end){const cal=Object.keys(spyCloses).sort(),i=cal.indexOf(end);if(i<0)return null;if(i+1<SESSIONS)return{short:true};return{sessions:cal.slice(i+1-SESSIONS,i+1),behind:cal.length-1-i};}
/* Latest session common to SPY and the company's closes (null when none). */
function commonEnd(spyCloses,closes){const cal=Object.keys(spyCloses).sort();for(let i=cal.length-1;i>=0;i--)if(Object.hasOwn(closes,cal[i]))return cal[i];return null;}
/* Split-like close-to-close ratio between consecutive present closes (raw closes only; a diagnostic, never a confirmation). */
function splitLike(points){let prev=null;for(const p of points){if(!finite(p))continue;if(prev!==null){const r=p/prev;if(SPLIT_RATIOS.some(s=>Math.abs(r/s-1)<=SPLIT_TOLERANCE))return true;}prev=p;}return false;}
const PRICE_IDS=AXES.filter(a=>a.kind==='PRICE').map(a=>a.id);
const allPrice=(reason,extra={})=>Object.fromEntries(PRICE_IDS.map(id=>[id,{value:null,reason,...extra}]));
/* Why a basis cannot be used (null = confirmed adjusted basis). */
function basisProblem(s,points){if(CONFIRMED_BASES.includes(s.basis))return null;return s.basis==='RAW'&&splitLike(points)?'CORPORATE_ACTION_UNADJUSTED':'ADJUSTMENT_BASIS_UNCONFIRMED';}
/* One series on one window: {price_stability, drawdown_defense, relative_strength}: {value (raw), reason, closes, returns,
   gaps}. closes = sessions with a close; returns = valid daily returns (both adjacent sessions present). */
function priceAxesOn(companyIn,spyIn,sessions){
 const c=series(companyIn),s=series(spyIn);
 const pts=sessions.map(d=>Object.hasOwn(c.closes,d)?c.closes[d]:null),sp=sessions.map(d=>Object.hasOwn(s.closes,d)?s.closes[d]:null);
 const closes=pts.filter(finite).length,rets=returnsOf(pts).filter(finite),gaps=closes<sessions.length,base={closes,returns:rets.length,gaps,basis:c.basis};
 if(c.basis!==s.basis)return allPrice('BASIS_MISMATCH',base);
 const problem=basisProblem(c,pts)||basisProblem(s,sp);if(problem)return allPrice(problem,base);
 const out={};
 if(closes>=MIN_SESSIONS&&rets.length>=MIN_RETURNS){let m=0;for(const x of rets)m+=x;m/=rets.length;let v=0;for(const x of rets)v+=(x-m)*(x-m);out.price_stability={value:Math.sqrt(v/(rets.length-1))*Math.sqrt(252),reason:null,...base};}
 else out.price_stability={value:null,reason:'INSUFFICIENT_SAMPLE',...base};
 if(closes>=MIN_SESSIONS){let peak=null,mdd=0;for(const p of pts){if(!finite(p))continue;if(peak===null||p>peak)peak=p;const dd=p/peak-1;if(dd<mdd)mdd=dd;}out.drawdown_defense={value:mdd,reason:null,...base,note:gaps?'MDD_GAPS':null};}
 else out.drawdown_defense={value:null,reason:'INSUFFICIENT_SAMPLE',...base};
 const t=sessions.length-1,b=t-RS_SESSIONS,recent=pts.slice(t-RS_SESSIONS+1).filter(finite).length,rs={...base,closes:recent,returns:null};
 if(!finite(pts[t])||!finite(pts[b])||!finite(sp[t])||!finite(sp[b]))out.relative_strength={value:null,reason:'ENDPOINT_MISSING',...rs};
 else if(recent<MIN_RS_SESSIONS)out.relative_strength={value:null,reason:'INSUFFICIENT_SAMPLE',...rs};
 else out.relative_strength={value:(pts[t]/pts[b]-1)-(sp[t]/sp[b]-1),reason:null,...rs};
 return out;}
function windowInfo(sessions,basis,behind){return{start:sessions[0],end:sessions[sessions.length-1],rs_start:sessions[sessions.length-1-RS_SESSIONS],sessions:sessions.length,basis,behind};}
/* Freshness of a window end: calendar days to `now` and sessions behind the latest SPY session; STALE past either limit. */
function freshness(win,now){if(!win)return null;const days=Math.floor((now-Date.parse(win.end+'T00:00:00Z'))/864e5);return{end:win.end,days,behind:win.behind,stale:win.behind>STALE_SESSIONS||days>STALE_DAYS};}
/* Pure entry point: the window from SPY and the company (end = latest common session unless given) and the three raw values. */
function priceAxes(company,spy,end=null){
 const s=series(spy),c=series(company);if(!Object.keys(s.closes).length)return{window:null,axes:allPrice('SPY_NOT_AVAILABLE')};
 const e=end||commonEnd(s.closes,c.closes),w=e?priceWindow(s.closes,e):null;
 if(!w)return{window:null,axes:allPrice('NO_COMMON_SESSION')};if(w.short)return{window:null,axes:allPrice('HISTORY_TOO_SHORT')};
 return{window:windowInfo(w.sessions,c.basis,w.behind),axes:priceAxesOn(c,s,w.sessions)};}

/* ---------- price data reads (RAM only) ---------- */
let device={state:'PENDING',series:new Map(),priced:0};
let inflight=null,subscribed=false,memo=null;
const STORE_STATES=new Set(['OFF','AUTH_REQUIRED','SHEET_NOT_CONNECTED','LOADING','READY','ERROR']);
function storeState(){const PS=g.PriceStore;if(!PS||typeof PS.status!=='function'||typeof PS.dailyCloses!=='function')return 'NOT_AVAILABLE';let s=null;try{s=PS.status().state;}catch(_){s=null;}return STORE_STATES.has(s)?s:'ERROR';}
const isoDay=ms=>new Date(ms).toISOString().slice(0,10);
/* SPY and the given symbols from the Prices_D tab of the user's private Google Sheet (PriceStore, fetch:false: no Worker
   request), raw closes, into this module's memory only. */
async function readDevice(symbols){
 const PS=g.PriceStore;let state=storeState();
 if(state==='OFF'||state==='AUTH_REQUIRED'||state==='SHEET_NOT_CONNECTED'||state==='NOT_AVAILABLE')return{state,series:new Map(),priced:0};
 const from=isoDay(Date.now()-500*864e5),out=new Map();
 for(const s of [SPY,...symbols.filter(x=>x!==SPY)]){let c=null;try{c=await PS.dailyCloses(s,from,{fetch:false});}catch(_){c=null;}const closes=cleanCloses(c),days=Object.keys(closes).sort();
  if(days.length)out.set(s,{closes,basis:'RAW',source:'PriceStore Prices_D (Worker: Yahoo chart · Tiingo/KRX fallback)',storage:'USER_PRIVATE_GOOGLE_SHEET',as_of:days[days.length-1]});}
 state=storeState();const priced=[...out.keys()].filter(s=>s!==SPY).length;return{state:state==='LOADING'&&out.size?'READY':state,series:out,priced};}
/* Raw price-axis values of every series on the window ending at `end` (memoised per read and end, RAM only). */
function priceTable(dev,end){
 if(memo&&memo.dev===dev&&memo.end===end)return memo;
 const spy=dev.series.get(SPY),w=spy&&end?priceWindow(spy.closes,end):null,values=new Map(),ok=!!(w&&!w.short);
 if(ok)for(const[s,ser]of dev.series)if(s!==SPY)values.set(s,priceAxesOn(ser,spy,w.sessions));
 memo={dev,end,sessions:ok?w.sessions:null,window:ok?windowInfo(w.sessions,series(spy).basis,w.behind):null,short:!!(w&&w.short),values};return memo;}
/* V comes only from the shared page result (QgvScores.pageResult: ONE collectQuotes + ONE compute over every Universe code,
   shared with the V coverage panel and the other screens), so the same input gives the same V everywhere. The radar reads the
   subject's row and the peers' rows of that one computed result; it never computes V or collects quotes itself. total: the
   QGV total of the same row, shown only with the label 'Q·G만 반영(V 미포함)' when V is missing. */
function vOne(S,id,full=false){const row=S&&S.rows?S.rows[id]:null,d=row?row.primary:null,cov=d&&d.coverage&&d.coverage.axes?d.coverage.axes.V:null;
 const x=!S?na('PENDING'):d&&finite(d.v)?{value:d.v,score:d.v,reason:null}:na(cov&&cov.reason||'NO_DEVICE_PRICE');
 if(full){x.v_detail={detail:d&&object(d.detail)?d.detail:null,factors:cov&&Array.isArray(cov.factors)?cov.factors.map(f=>({id:f.id,reason:f.reason})):[]};x.total=d&&finite(d.total)?d.total:null;}return x;}
function vScores(result,subject,points){
 const S=object(result)&&object(result.computed)?result.computed:null,map=new Map();for(const p of points)map.set(p.code,vOne(S,p.code));
 return{map,subject:vOne(S,subject.identity.company_id,true),priced:!!(object(result)&&object(result.quotes)&&Object.keys(result.quotes).length)};}

/* ---------- model ---------- */
function mean(xs){let s=0;for(const x of xs)s+=x;return s/xs.length;}
function build(inputs,spec,dev,result,{aux=false,now=Date.now()}={}){
 const subject=subjectOf(inputs,spec),points=inputs?crossSection(inputs):[],noFile={state:'NOT_AVAILABLE',reason:'SEC_QGV2_NOT_AVAILABLE',members:[]};
 const gi=inputs?industryGroup(subject,points):noFile,gs=inputs?sicGroup(subject,points):noFile,same=sameMembers(gi,gs);
 const others=points.filter(p=>p.cik!==subject.cik),withdrawn=subject.rec&&subject.rec.identity_withdrawn===true,financial=scoredRow(subject.rec)&&subject.rec.profile==='FINANCIAL';
 const V=vScores(result,subject,points),priced=V.priced;
 const universeCodes=inputs?Object.keys(inputs.records).filter(k=>!k.startsWith('TARGET:')):[];
 // Price window: the latest session common to SPY and the subject, else the latest SPY session.
 const spy=dev.series.get(SPY),own=subject.symbol?dev.series.get(subject.symbol):null,sc=spy?spy.closes:null;
 const end=sc?(own&&commonEnd(sc,own.closes))||Object.keys(sc).sort().pop():null,pt=dev.state==='READY'&&spy?priceTable(dev,end):null;
 const priceReason=dev.state!=='READY'?'NO_DEVICE_PRICE':!spy?'SPY_NOT_AVAILABLE':pt.short?'HISTORY_TOO_SHORT':null;
 const ownPrice=withdrawn||priceReason||!own?null:priceAxesOn(own,spy,pt.sessions);
 // A raw or unstated SPY basis cannot confirm corporate-action handling: no member is comparable on it.
 const basisReason=spy&&!CONFIRMED_BASES.includes(series(spy).basis)?'ADJUSTMENT_BASIS_UNCONFIRMED':null;
 const axisModel=a=>{
  let valueOf,mine;const excluded=[];
  if(a.kind==='SCORE'){valueOf=p=>scoreValue(a.axis,p.rec);mine=inputs?scoreValue(a.axis,subject.rec):na('SEC_QGV2_NOT_AVAILABLE');}
  else if(a.kind==='DEVICE_SCORE'){valueOf=p=>V.map.get(p.code)||na('NO_DEVICE_PRICE');mine=inputs?V.subject:na('SEC_QGV2_NOT_AVAILABLE');}
  else if(a.kind==='PUBLIC'){valueOf=p=>marginValue(p.rec);mine=inputs?marginValue(subject.rec):na('SEC_QGV2_NOT_AVAILABLE');}
  else{valueOf=p=>{if(priceReason)return na(priceReason);const x=pt.values.get(universeSymbol(p.code));if(!x)return na('NO_DEVICE_PRICE');const y=x[a.id];
    if(finite(y.value))return{value:y.value,score:null,reason:null};excluded.push({code:p.code,reason:y.reason});return na(y.reason);};
   const x=ownPrice?ownPrice[a.id]:null;
   mine=withdrawn?na('IDENTITY_CONFLICT_WITHDRAWN'):priceReason?na(priceReason,Object.hasOwn(REASON,dev.state)?dev.state:null):!x?na('NO_DEVICE_PRICE'):finite(x.value)?{value:x.value,score:null,reason:null,score_reason:null,closes:x.closes,returns:x.returns,note:x.note||null}:{...na(x.reason),closes:x.closes,returns:x.returns};}
  const vals=new Map();for(const p of others){const x=valueOf(p);if(finite(x.value))vals.set(p.code,x.value);}
  const ranked=a.kind==='PUBLIC'||a.kind==='PRICE',scores=new Map();let n=vals.size+(finite(mine.value)?1:0);
  if(ranked){// Population: the cross-section with the subject's own issuer point replaced by the subject.
   const sorted=[...vals.values(),...(finite(mine.value)?[mine.value]:[])].map(v=>a.dir*v).sort((x,y)=>x-y);n=sorted.length;
   for(const[c,v]of vals){const s=percentile(sorted,a.dir*v);if(s!==null)scores.set(c,s);}
   if(finite(mine.value)){mine.score=percentile(sorted,a.dir*mine.value);if(mine.score===null)mine.score_reason='PEERS_TOO_FEW';}}
  else for(const[c,v]of vals)scores.set(c,v);
  mine.n=n;
  const group=gr=>{if(gr.state!=='OK')return{...na(gr.reason),n:null,codes:[]};
   if(a.kind==='DEVICE_SCORE'&&financial)return{...na('FINANCIAL_PROFILE_V_NOT_DEFINED'),n:null,codes:[]};
   if(a.kind==='PRICE'&&(priceReason||basisReason))return{...na(priceReason||basisReason),n:0,codes:[]};
   if(a.kind==='DEVICE_SCORE'&&!priced)return{...na('NO_DEVICE_PRICE'),n:0,codes:[]};
   const mem=gr.members.filter(p=>scores.has(p.code)),codes=mem.map(p=>p.code);
   if(mem.length<MIN_GROUP){const raw=gr.members.filter(p=>vals.has(p.code)).length;return{...na(ranked&&n<MIN_PEERS&&raw>=MIN_GROUP?'PEERS_TOO_FEW':'GROUP_TOO_SMALL'),n:mem.length,codes};}
   const v=mean(mem.map(p=>scores.get(p.code)));return{value:v,score:v,reason:null,n:mem.length,codes};};
  // Coverage across the 504 Universe codes: codes whose issuer has a verified value and a displayed score.
  const scoredCiks=new Set(others.filter(p=>scores.has(p.code)).map(p=>p.cik));if(finite(mine.score)&&subject.cik)scoredCiks.add(subject.cik);
  const coverage=universeCodes.filter(k=>scoredCiks.has(inputs.records[k].cik)).length;
  return{...a,population:n,population_codes:[...vals.keys()],excluded,coverage,company:mine,industry:group(gi),sic:same?{...na('SAME_AS_INDUSTRY'),n:null,codes:[]}:group(gs),competitor:{...na('REL_SOURCE_PENDING'),n:null,codes:[]}};};
 const auxAxis=axisModel(AUX),axes=AXES.map(axisModel),win=pt&&!priceReason?pt.window:null;
 return{subject,inputs,groups:{industry:gi,sic:gs,same},axes:aux?[...axes,auxAxis]:axes,aux:auxAxis,auxOn:!!aux,device:dev,priced,window:win,fresh:freshness(win,now),
  basis:spy?series(spy).basis:null,storage:spy?series(spy).storage:null,source:spy?series(spy).source:null,universe:universeCodes.length,points:points.length};}

/* ---------- formatting ---------- */
function fmtNum(v,locale,d=1){return new Intl.NumberFormat(locale==='en-US'?'en-US':'ko-KR',{minimumFractionDigits:d,maximumFractionDigits:d}).format(v);}
function fmtRaw(unit,v,locale){if(!finite(v))return '—';if(unit==='score')return fmtNum(v,locale,1);if(unit==='stdpp')return fmtNum(v,locale,2)+'%p';if(unit==='pp')return fmtNum(v*100,locale,1)+'%p';return fmtNum(v*100,locale,1)+'%';}
const scoreText=(v,locale)=>finite(v)?fmtNum(v,locale,1):'미산출';
const GROUP_NAME=(key,en)=>{const L=g.UniverseCompany&&g.UniverseCompany.GROUP_LABEL;return L&&Object.hasOwn(L,key)?L[key][en?1:0]:key;};
function groupTitle(kind,gr,T,en,same){
 if(kind==='industry'){if(gr.state!=='OK')return T('업종 평균','Industry average');const base=gr.basis==='FINANCIAL_PROFILE'?T('업종 평균 · 금융 프로필','Industry average · financial profile'):gr.basis==='INDUSTRY_GROUP'?T('업종 평균 · ','Industry average · ')+GROUP_NAME(gr.key,en):T('업종 평균 · 일반 전체(업종군 8곳 미만)','Industry average · all general (group below 8)');return same?T('업종 = SIC · ','Industry = SIC · ')+base:base;}
 if(gr.state!=='OK')return T('SIC 평균','SIC average');return gr.basis==='SIC4'?'SIC '+gr.key+T(' 평균',' average'):'SIC '+gr.key+'xx'+T(' 평균(4자리 8곳 미만)',' average (4-digit below 8)');}
const isScore=a=>a.kind==='SCORE'||a.kind==='DEVICE_SCORE';
const scoreLabel=(a,T)=>a.kind==='PRICE'?T('기기 보유 데이터 내 상대점수','relative score within the price data you hold'):a.kind==='PUBLIC'?T('공개 단면 백분위','published cross-section percentile'):T('점수','score');
const sourceBadge=(a,T)=>a.kind==='SCORE'?T('핵심 축 · 공개 점수','core · published score'):a.kind==='DEVICE_SCORE'?T('핵심 축 · 기존 V 경로','core · existing V path'):a.kind==='PRICE'?T('후보 축(커버리지 확인 전)','candidate (coverage unconfirmed)'):T('보조 지표 · 공개','auxiliary · published');
const BASIS_TEXT={RAW:['미수정 종가(조정 기준 미확인)','raw closes (adjustment basis unconfirmed)'],SPLIT_ADJUSTED:['분할 수정 종가','split-adjusted closes'],TOTAL_RETURN:['분할·배당 수정 종가(총수익)','split + dividend adjusted closes (total return)'],ADJUSTED_UNCONFIRMED:['수정 종가(기준 미확인)','adjusted closes (basis unconfirmed)']};
/* Where the price inputs live, said exactly (never "only on this device" for the private sheet). */
function storageText(model,T){return model.storage==='USER_PRIVATE_GOOGLE_SHEET'?T('내 비공개 구글 시트 Prices_D 탭 → 이 브라우저 메모리','your private Google Sheet, Prices_D tab → this browser’s memory'):model.storage?T('메모리 자료(','in-memory data (')+(model.source||model.storage)+')':T('가격 자료 없음','no price data');}
const clock=x=>typeof x==='string'&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(x)?x.slice(0,10)+' '+x.slice(11,16)+' UTC':'—';
/* Unit, period, as_of, basis and storage of one axis for the detail table. */
function axisMeta(a,model,T,en){
 const r=model.subject.rec,pubAsOf=model.inputs?clock(model.inputs.as_of):'—',w=model.window,fy=r&&r.fiscal_year_end?r.fiscal_year_end:'—';
 if(a.kind==='SCORE')return{unit:T('점(0–100)','points (0–100)'),period:'FY '+fy,asof:pubAsOf,basis:T('공개 sec-qgv2.json','published sec-qgv2.json'),storage:T('공개 파일','public file')};
 if(a.kind==='DEVICE_SCORE')return{unit:T('점(0–100)','points (0–100)'),period:T('현재 시세 · SEC 입력 FY ','current quote · SEC inputs FY ')+fy,asof:T('가격 기준 시각: 미확인 · 공개 ','price as-of: unknown · published ')+pubAsOf,basis:T('기존 V 경로','existing V path'),storage:T('시세: 내 비공개 구글 시트(Universe 탭)·이 브라우저 저장 시세·Worker 종가 → 메모리 계산','quotes: your private Google Sheet (Universe tab) · quotes stored in this browser · Worker closes → computed in memory')};
 if(a.kind==='PUBLIC')return{unit:'%p',period:T('5개 회계연도 FY0~FY-4 · FY ','5 fiscal years FY0–FY-4 · FY ')+fy,asof:pubAsOf,basis:T('공개 sec-qgv2.json','published sec-qgv2.json'),storage:T('공개 파일','public file')};
 const per=w?(a.id==='relative_strength'?w.rs_start+' ~ '+w.end+T(' (126거래일)',' (126 sessions)'):w.start+' ~ '+w.end+T(' (252거래일)',' (252 sessions)')):'—';
 return{unit:a.unit==='pp'?'%p':'%',period:per,asof:w?w.end+T(' (마지막 공통 거래일)',' (latest common session)'):'—',basis:model.basis?BASIS_TEXT[model.basis][en?1:0]:'—',storage:storageText(model,T)};}
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
  const none=a.company.reason==='FINANCIAL_PROFILE_V_NOT_DEFINED'?FIN_V[en?1:0][1]:T('미산출','n/a');
  const anchor=Math.abs(c)<0.2?'middle':c>0?'start':'end',lines=[...a.lines[en?1:0],...(a.company.reason==='FINANCIAL_PROFILE_V_NOT_DEFINED'&&!finite(a.company.score)?[FIN_V[en?1:0][0]]:[]),(finite(a.company.score)?fmtNum(a.company.score,locale,0):none)],lh=15;
  const y0=s<-0.9?y-lh*(lines.length-1):s>0.9?y+lh*0.8:y-lh*(lines.length-1)/2+4;
  return '<text class="sr-label" x="'+f2(x)+'" y="'+f2(y0)+'" text-anchor="'+anchor+'" data-sr-label="'+a.id+'">'+lines.map((t,k)=>'<tspan x="'+f2(x)+'" dy="'+(k?lh:0)+'"'+(k===lines.length-1?' class="sr-label-val'+(finite(a.company.score)?'':' sr-label-na')+'"':'')+'>'+esc(t)+'</tspan>').join('')+'</text>';}).join('');
 const summary=T('스탯창(설명용). 모든 축에서 바깥이 더 좋은 평가. 면적은 점수가 아님. ','Stat window (explanatory). Outer is better on every axis. The area is not a score. ')
  +model.axes.map(a=>T(a.name[0],a.name[1])+': '+T('기업 ','company ')+(a.company.reason==='FINANCIAL_PROFILE_V_NOT_DEFINED'?finText(en):scoreText(a.company.score,locale))+', '+T(same?'업종 = SIC ':'업종 평균 ',same?'industry = SIC ':'industry ')+scoreText(a.industry.score,locale)+(same?'':', SIC '+scoreText(a.sic.score,locale))+', '+T('경쟁사 미산출','competitors n/a')).join('; ');
 const stale=!!(model.fresh&&model.fresh.stale);
 return '<svg class="sr-svg'+(stale?' sr-stale':'')+'" viewBox="0 0 '+W+' '+H+'" role="img" aria-label="'+esc(summary)+'" focusable="false" data-sr-svg data-sr-axes="'+n+'">'
  +'<defs><filter id="'+id+'" x="-5%" y="-5%" width="110%" height="110%"><feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="2" seed="7" result="n"></feTurbulence><feDisplacementMap in="SourceGraphic" in2="n" scale="2.4"></feDisplacementMap></filter></defs>'
  +grid+ticks+(stale?'<text class="sr-stale-label" x="8" y="20">STALE · '+esc(model.fresh.end)+'</text>':'')+(same?'':seriesSvg('sic',model.axes))+seriesSvg('industry',model.axes)+seriesSvg('company',model.axes)+labels+'</svg>';}
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
 return '<div class="sr-aux" data-sr-aux-box="'+(model.auxOn?'ON':'OFF')+'"><p class="small"><b>'+esc(T('보조 지표 · 이익률 안정성','Auxiliary · margin stability'))+'</b> '+esc(finite(x.value)?fmtRaw('stdpp',x.value,locale)+T(' (5년 영업이익률 표준편차) · 공개 단면 백분위 ',' (5-year operating-margin std) · cross-section percentile ')+scoreText(x.score,locale):T('미산출 · ','n/a · ')+reasonText(x.reason,en))+'</p>'
  +'<button type="button" class="sr-aux-toggle" data-sr-aux-toggle aria-pressed="'+(model.auxOn?'true':'false')+'">'+esc(model.auxOn?T('보조 축 빼기(기본 6축)','Remove the auxiliary axis (default 6)'):T('보조 축으로 더하기(7축)','Add as an auxiliary axis (7)'))+'</button></div>';}
/* One detail cell. The raw value and the score are separate: a verified raw value is shown even when the score is 미산출. */
function cell(series,a,x,locale){
 const T=tr(locale),en=locale==='en-US',hasRaw=finite(x.value),hasScore=finite(x.score),why=hasRaw?(x.score_reason||x.reason||''):(x.reason||'');
 const attrs=' data-sr-series="'+series+'" data-sr-raw="'+(hasRaw?String(x.value):'NA')+'" data-sr-score="'+(hasScore?String(x.score):'NA')+'" data-sr-reason="'+esc(why)+'"'+(Number.isInteger(x.n)?' data-sr-n="'+x.n+'"':'')+(Number.isInteger(x.closes)?' data-sr-closes="'+x.closes+'"':'')+(Number.isInteger(x.returns)?' data-sr-returns="'+x.returns+'"':'')+(x.note?' data-sr-note="'+esc(x.note)+'"':'');
 const label=series==='company'?T('기업','Company'):series==='industry'?T('업종 평균','Industry'):series==='sic'?T('SIC 평균','SIC'):T('경쟁사 평균','Competitors');
 const badge=r=>r==='FINANCIAL_PROFILE_V_NOT_DEFINED'?'<span class="badge sr-model-scope" data-sr-model-scope>'+esc(finText(en))+'</span>':'<span class="badge NOT_AVAILABLE">'+esc(T('미산출','n/a'))+'</span>';
 const counts=(Number.isInteger(x.closes)?T(' · 종가 ',' · closes ')+x.closes:'')+(Number.isInteger(x.returns)?T(' · 유효 일간 수익률 ',' · valid daily returns ')+x.returns:'');
 let body;
 if(series==='company'&&hasRaw&&!isScore(a)){
  body=T('원값 ','raw ')+'<b class="num">'+esc(fmtRaw(a.unit,x.value,locale))+'</b><br>'+esc(scoreLabel(a,T))+' '+(hasScore?'<b class="num">'+esc(scoreText(x.score,locale))+'</b>':badge(why)+' <span class="small">'+esc(reasonText(why,en)+' (n='+x.n+')')+'</span>')
   +'<span class="small">'+esc(counts)+'</span>'+(x.note?'<br><span class="small sr-note">'+esc(reasonText(x.note,en))+'</span>':'');}
 else if(hasScore)body=T(series==='company'?'점수 ':'평균 ',series==='company'?'score ':'mean ')+'<b class="num">'+esc(scoreText(x.score,locale))+'</b>'+(series!=='company'&&Number.isInteger(x.n)?' <span class="small">n='+x.n+'</span>':'');
 else{const code=series!=='company'&&why==='NO_DEVICE_PRICE'?'GROUP_NO_DEVICE_PRICE':why;
  const qgOnly=series==='company'&&a.id==='v'&&finite(x.total)?'<br><span class="small" data-sr-total-qg-only>'+esc(T('QGV 종합 ','QGV total ')+fmtNum(x.total,locale,1)+T(' · Q·G만 반영(V 미포함)',' · Q·G only (V not included)'))+'</span>':'';
  body=(why==='FINANCIAL_PROFILE_V_NOT_DEFINED'?badge(why):badge(why)+' <span class="small">'+esc(reasonText(code,en)+(x.detail?' · '+reasonText(x.detail,en):'')+(Number.isInteger(x.n)&&series!=='company'?' (n='+x.n+')':'')+counts)+'</span>')+qgOnly;}
 return '<td'+attrs+' data-label="'+esc(label)+'">'+body+'</td>';}
function table(model,locale){
 const T=tr(locale),en=locale==='en-US',same=model.groups.same,rows=[...model.axes.filter(a=>!a.aux),model.aux];
 const head='<thead><tr><th scope="col">'+esc(T('축 · 단위 · 기간 · 기준','Axis · unit · period · basis'))+'</th><th scope="col">'+esc(T('기업','Company'))+'</th><th scope="col">'+esc(same?T('업종 = SIC 평균','Industry = SIC'):T('업종 평균','Industry'))+'</th>'+(same?'':'<th scope="col">'+esc(T('SIC 평균','SIC'))+'</th>')+'<th scope="col">'+esc(T('경쟁사 평균','Competitors'))+'</th></tr></thead>';
 const row=a=>{const m=axisMeta(a,model,T,en),cov=a.kind==='PRICE'?T('커버리지 ','coverage ')+a.coverage+' / '+UNIVERSE_SIZE+T(' (채택 기준 ',' (adoption ≥ ')+ADOPT_MIN+(en?')':'곳 이상)'):null;
  return '<tr data-sr-axis="'+a.id+'" data-sr-kind="'+a.kind+'"'+(a.aux?' data-sr-aux-row':'')+' data-sr-population="'+a.population+'" data-sr-coverage="'+a.coverage+'" data-sr-unit="'+esc(m.unit)+'" data-sr-period="'+esc(m.period)+'" data-sr-asof="'+esc(m.asof)+'" data-sr-basis="'+esc(m.basis)+'" data-sr-storage="'+esc(m.storage)+'"><th scope="row"><b>'+esc(a.name[en?1:0])+'</b> <span class="badge'+(a.kind==='PRICE'||a.kind==='DEVICE_SCORE'?' partial':'')+'">'+esc(sourceBadge(a,T))+'</span><br><span class="small">'
  +esc([a.outer[en?1:0],a.how?a.how[en?1:0]:null,T('단위 ','unit ')+m.unit,T('기간 ','period ')+m.period,'as_of '+m.asof,T('기준 ','basis ')+m.basis,T('저장 위치 ','stored in ')+m.storage,T('모집단 n=','population n=')+a.population,cov].filter(Boolean).join(' · '))+'</span></th>'
  +cell('company',a,a.company,locale)+cell('industry',a,a.industry,locale)+(same?'':cell('sic',a,a.sic,locale))+cell('competitor',a,a.competitor,locale)+'</tr>';};
 return '<div class="sr-table table-wrap"><table><caption class="sr-only">'+esc(T('스탯창 상세: 축별 원값, 점수(0–100), 단위, 기간, 기준 시점, 가격 기준, 저장 위치, 모집단 수','Stat window detail: per-axis raw value, score (0–100), unit, period, as_of, price basis, storage, population count'))+'</caption>'+head+'<tbody>'+rows.map(row).join('')+'</tbody></table></div>';}
/* The actual comparison companies of every axis: count, codes and period (one text node per list). */
function membersHtml(model,locale){
 const T=tr(locale),en=locale==='en-US',same=model.groups.same,rows=[...model.axes.filter(a=>!a.aux),model.aux];
 const list=codes=>codes.length?codes.map(tickerOf).join(' · '):'—';
 return '<div class="sr-members"><h3 class="small">'+esc(T('축별 비교 기업','Comparison companies per axis'))+'</h3>'+rows.map(a=>{const m=axisMeta(a,model,T,en);
  const groups=[[same?T('업종 = SIC','industry = SIC'):T('업종','industry'),a.industry],...(same?[]:[['SIC',a.sic]])];
  return '<details class="sr-member-list" data-sr-members="'+a.id+'" data-sr-members-n="'+a.population_codes.length+'"><summary>'+esc(a.name[en?1:0]+' · '+T('비교 기업 ','companies ')+a.population_codes.length+T('곳 · 기간 ',' · period ')+m.period)+'</summary>'
   +'<p class="small" data-sr-members-list>'+esc(T('모집단(값 있는 기업): ','population (with a value): ')+list(a.population_codes))+'</p>'
   +groups.map(([name,x])=>'<p class="small" data-sr-group-list="'+esc(name)+'">'+esc(name+' ('+x.codes.length+T('곳): ',' cos): ')+list(x.codes))+'</p>').join('')
   +(a.excluded.length?'<p class="small" data-sr-excluded>'+esc(T('가격 자료는 있으나 제외: ','price data held but excluded: ')+a.excluded.map(e=>tickerOf(e.code)+' ('+e.reason+')').join(' · '))+'</p>':'')+'</details>';}).join('')+'</div>';}
/* V detail: the individual value inputs, each with its raw value, period and source, or 미산출 and the reason. EBIT / FCF yield
   come from the existing V computation (device quote, RAM); the reference inputs are the published v_inputs_v2 fields. A
   FINANCIAL subject shows only the model-scope text (no general-company formula is applied). */
function vDetailHtml(model,locale){
 const T=tr(locale),en=locale==='en-US',v=model.axes.find(a=>a.id==='v')||null,x=v?v.company:null,r=model.subject.rec;if(!x)return '';
 if(x.reason==='FINANCIAL_PROFILE_V_NOT_DEFINED')return '<div class="sr-v-detail" data-sr-v-detail="FINANCIAL"><h3 class="small">'+esc(T('V 상세','V detail'))+'</h3><p><span class="badge sr-model-scope" data-sr-model-scope>'+esc(finText(en))+'</span></p></div>';
 const vi=r&&object(r.v_inputs)?r.v_inputs:null,per=r&&object(r.periods)?r.periods:{},cur=vi&&typeof vi.currency==='string'?vi.currency:null,asOf=model.inputs?clock(model.inputs.as_of):'—';
 const det=x.v_detail&&x.v_detail.detail,fr=id=>{const f=x.v_detail&&x.v_detail.factors.find(y=>y.id===id);return f&&f.reason||x.reason||'NO_DEVICE_PRICE';};
 const money=v=>cur?new Intl.NumberFormat(en?'en-US':'ko-KR',{style:'currency',currency:cur,notation:'compact',maximumFractionDigits:2}).format(v):fmtNum(v,locale,0);
 const pubSrc=T('공개 sec-qgv2.json v_inputs_v2 · as_of ','published sec-qgv2.json v_inputs_v2 · as_of ')+asOf,devSrc=T('기존 V 경로(공개 입력 + 이 브라우저 메모리의 시세)','existing V path (published inputs + quote in this browser’s memory)');
 const noInputs=!scoredRow(r)?rowReason(r):'V_INPUTS_NOT_AVAILABLE';
 const rows=[
  ['ebit_yield',T('EBIT 수익률 (EBIT ÷ EV)','EBIT yield (EBIT ÷ EV)'),det&&finite(det.ebit_yield)?det.ebit_yield:null,v=>fmtNum(v*100,locale,2)+'%',(per.ebit||'—')+T(' · 현재 시세',' · current quote'),devSrc,fr('v_earnings_yield')],
  ['fcf_yield',T('FCF 수익률 (FCF ÷ EV)','FCF yield (FCF ÷ EV)'),det&&finite(det.fcf_yield)?det.fcf_yield:null,v=>fmtNum(v*100,locale,2)+'%',(per.fcf||'—')+T(' · 현재 시세',' · current quote'),devSrc,fr('v_fcf_yield')],
  ['ebit','EBIT',vi&&finite(vi.ebit)?vi.ebit:null,money,per.ebit||'—',pubSrc,vi?'EBIT_NOT_AVAILABLE':noInputs],
  ['fcf','FCF',vi&&finite(vi.fcf)?vi.fcf:null,money,per.fcf||'—',pubSrc,vi?'FCF_NOT_AVAILABLE':noInputs],
  ['total_debt',T('총부채','Total debt'),vi&&finite(vi.total_debt)?vi.total_debt:null,money,per.total_debt||'—',pubSrc,vi?'DEBT_CASH_NOT_AVAILABLE':noInputs],
  ['cash',T('현금성 자산','Cash'),vi&&finite(vi.cash)?vi.cash:null,money,per.cash_and_equivalents||'—',pubSrc,vi?'DEBT_CASH_NOT_AVAILABLE':noInputs],
  ['diluted_shares',T('희석 주식수','Diluted shares'),vi&&finite(vi.diluted_shares)?vi.diluted_shares:null,v=>new Intl.NumberFormat(en?'en-US':'ko-KR',{notation:'compact',maximumFractionDigits:2}).format(v),per.diluted_shares||'—',pubSrc,vi?'SHARES_NOT_AVAILABLE':noInputs],
  ['revenue_cagr_3y',T('3년 매출 성장(CAGR)','3-year revenue CAGR'),vi&&finite(vi.revenue_cagr_3y)?vi.revenue_cagr_3y:null,v=>fmtNum(v*100,locale,1)+'%',T('최근 3개 회계연도','latest 3 fiscal years'),pubSrc,vi?'REALIZED_GROWTH_NOT_AVAILABLE':noInputs],
  ['ebit_per_share_history',T('연도별 EBIT/주','EBIT per share by year'),vi&&Array.isArray(vi.ebit_per_share_history)&&vi.ebit_per_share_history.length?vi.ebit_per_share_history.length:null,v=>v+T('개 연도',' years'),vi&&Array.isArray(vi.ebit_per_share_history)&&vi.ebit_per_share_history.length?'FY '+vi.ebit_per_share_history[0].period_end+' ~ '+vi.ebit_per_share_history[vi.ebit_per_share_history.length-1].period_end:'—',pubSrc,vi?'HISTORY_TOO_SHORT':noInputs]];
 return '<div class="sr-v-detail table-wrap" data-sr-v-detail="GENERAL"><h3 class="small">'+esc(T('V 상세 · 가치 입력','V detail · value inputs'))+'</h3><table><thead><tr><th scope="col">'+esc(T('입력','Input'))+'</th><th scope="col">'+esc(T('원값','Raw value'))+'</th><th scope="col">'+esc(T('기간','Period'))+'</th><th scope="col">'+esc(T('출처','Source'))+'</th></tr></thead><tbody>'
  +rows.map(([id,name,val,fmt,period,src,why])=>'<tr data-sr-v-input="'+id+'" data-sr-raw="'+(val===null?'NA':String(val))+'" data-sr-reason="'+esc(val===null?why:'')+'"><th scope="row">'+esc(name)+'</th><td data-label="'+esc(T('원값','Raw value'))+'">'+(val===null?'<span class="badge NOT_AVAILABLE">'+esc(T('미산출','n/a'))+'</span> <span class="small">'+esc(reasonText(why,en))+'</span>':'<span class="num">'+esc(fmt(val))+'</span>')+'</td><td data-label="'+esc(T('기간','Period'))+'">'+esc(period)+'</td><td class="small" data-label="'+esc(T('출처','Source'))+'">'+esc(src)+'</td></tr>').join('')
  +'</tbody></table></div>';}
function freshLine(model,locale){
 const T=tr(locale),f=model.fresh;if(!f)return '<p class="small sr-fresh" data-sr-freshness="UNKNOWN">'+esc(T('가격 기준 시각: 미확인','Price as-of: unknown'))+'</p>';
 return '<p class="small sr-fresh" data-sr-freshness="'+(f.stale?'STALE':'CURRENT')+'" data-sr-days="'+f.days+'">'+(f.stale?'<span class="badge partial">STALE</span> ':'')+esc(T('가격 기준 시각(마지막 공통 종가일) ','price as-of (latest common close) ')+f.end+' · '+f.days+T('일 전',' days ago')+' · '+T('최신 SPY 거래일보다 ','behind the latest SPY session by ')+f.behind+T('거래일 뒤',' sessions')+(f.stale?T(' · '+STALE_SESSIONS+'거래일 또는 '+STALE_DAYS+'일 초과라 STALE',' · beyond '+STALE_SESSIONS+' sessions or '+STALE_DAYS+' days: STALE'):''))+'</p>';}
function body(model,locale){
 const T=tr(locale),en=locale==='en-US',d=model.device,dev=d.state==='READY'?T('읽음 · 가격 있는 종목 ','read · symbols with prices ')+d.priced+(d.series.has(SPY)?' · SPY':T(' · SPY 없음',' · no SPY')):d.state==='PENDING'?reasonText('PENDING',en):d.state+' · '+reasonText(d.state==='NOT_AVAILABLE'?'NO_DEVICE_PRICE':d.state,en);
 return '<div class="sr-layout"><figure class="sr-figure">'+svg(model,locale)+'<figcaption class="sr-notes small">'+(model.axes.some(a=>a.id==='v'&&a.company.reason==='FINANCIAL_PROFILE_V_NOT_DEFINED')?'<span class="badge sr-model-scope" data-sr-model-scope>V · '+esc(finText(en))+'</span> ':'')+esc(T('모든 축에서 바깥이 더 좋은 평가입니다. 설명용이며 공식 QGV 점수·비중·순위를 바꾸지 않습니다. 면적은 계산하지 않습니다. 미산출 축에는 점을 찍지 않습니다(0이나 평균으로 채우지 않음).','Outer is the better evaluation on every axis. Explanatory only: official QGV scores, weights and ranks are unchanged. The area is not computed. 미산출 axes get no point (never 0 or an average).'))+'</figcaption></figure>'
  +'<div class="sr-side">'+legend(model,locale)+auxBox(model,locale)+'</div></div>'+freshLine(model,locale)+table(model,locale)+vDetailHtml(model,locale)+membersHtml(model,locale)
  +'<p class="small sr-fresh" data-sr-fresh>'+esc([T('Q·G·이익률 출처 sec-qgv2.json','Q·G·margin: sec-qgv2.json'),'as_of '+(model.inputs?clock(model.inputs.as_of):'—'),T('단면 ','cross-section ')+model.points+T('곳(발행사당 한 점)',' issuers (one point each)'),T('가격 후보 축 점수 = 기기 보유 데이터 내 상대점수(504 전체·시장 전체 백분위 아님, 모집단 8곳 이상) · 비교군 평균은 5곳 이상','candidate price-axis score = relative score within the price data you hold (not a 504- or market-wide percentile; population ≥ 8) · group averages need ≥ 5')].join(' · '))+'</p>'
  +'<p class="small sr-fresh" data-sr-device-line>'+esc([T('가격 입력: ','Price input: ')+(model.storage?storageText(model,T):T('내 비공개 구글 시트 Prices_D 탭(가격 탭 사용 시) → 이 브라우저 메모리','the Prices_D tab of your private Google Sheet (when price tabs are on) → this browser’s memory'))+T(' · Worker 요청 없음 · 공개 안 함',' · no Worker request · never published'),T('기준 ','basis ')+(model.basis?BASIS_TEXT[model.basis][en?1:0]:'—'),T('상태 ','state ')+dev,T('V: 기존 V 경로(시세 '+(model.priced?'있음':'없음')+')','V: existing V path (quotes '+(model.priced?'present':'none')+')')].join(' · '))+'</p>';}
function stateOf(model){return{'data-sr-subject':model.subject.label,'data-sr-device':model.device.state,'data-sr-quotes':model.priced?'PRESENT':'NONE','data-sr-groups':model.groups.same?'SAME':'DISTINCT','data-sr-aux':model.auxOn?'ON':'OFF','data-sr-window-end':model.window?model.window.end:'NA',
 'data-sr-stale':model.fresh?(model.fresh.stale?'STALE':'CURRENT'):'NA','data-sr-basis':model.basis||'NA',
 'data-sr-industry-basis':model.groups.industry.basis||'NA','data-sr-industry-key':model.groups.industry.key||'','data-sr-sic-basis':model.groups.sic.basis||'NA','data-sr-sic-key':model.groups.sic.key||''};}
const stateAttrs=model=>Object.entries(stateOf(model)).map(([k,v])=>' '+k+'="'+esc(v)+'"').join('');

/* ---------- public API ---------- */
const live=new Map();
const keyOf=spec=>spec&&typeof spec.targetId==='string'?'target:'+spec.targetId:'code:'+(spec&&spec.code||'');
const decisionBadge=T=>DECISION.state==='DECIDED'?T('결정됨','DECIDED'):DECISION.state==='CANDIDATE'?T('후보 축 포함','with candidate axes'):'PROVISIONAL';
/* Synchronous HTML from the loaded public file (ctx.screens), the last shared page result of this radar and the price data already
   read (if any; ctx.device: a price-data snapshot to render instead, RAM only). spec: {code} or {targetId}. */
function html(spec,ctx={}){
 const locale=ctx.locale==='en-US'?'en-US':'ko-KR',T=tr(locale),inputs=inputsOf(ctx.screens),key=keyOf(spec),prev=live.get(key),aux=!!(prev&&prev.aux),dev=object(ctx.device)?ctx.device:null;
 const result=prev&&prev.inputs===inputs?prev.result:null;live.set(key,{spec,inputs,locale,result,aux,dev});const model=build(inputs,spec,dev||device,result,{aux});
 return '<div class="stat-radar" data-stat-radar="'+esc(key)+'" data-sr-decision="'+DECISION.state+'"'+stateAttrs(model)+'><h2 class="sr-title"><span class="hl">'+esc(T('스탯창','Stat window'))+'</span> <span class="badge partial">'+esc(decisionBadge(T))+'</span></h2>'
  +'<p class="small" data-sr-axis-set>'+esc(T('축: ','Axes: ')+DECISION.set[locale==='en-US'?1:0]+' · '+DECISION.ref[locale==='en-US'?1:0]+T(' · 설명용 · 추천 아님',' · explanatory · not a recommendation'))+'</p><div data-sr-body>'+body(model,locale)+'</div></div>';}
function paint(el){const entry=live.get(el.dataset.statRadar);if(!entry)return;const model=build(entry.inputs,entry.spec,entry.dev||device,entry.result,{aux:entry.aux}),b=el.querySelector('[data-sr-body]');
 if(b)b.innerHTML=body(model,entry.locale);for(const[k,v]of Object.entries(stateOf(model)))el.setAttribute(k,v);}
function symbolsFor(){const out=new Set();for(const{spec,inputs}of live.values()){if(!inputs)continue;const s=subjectOf(inputs,spec);if(s.symbol)out.add(s.symbol);for(const p of crossSection(inputs)){const y=universeSymbol(p.code);if(y)out.add(y);}}return[...out];}
async function refreshDevice(){
 if(inflight)return inflight;
 inflight=(async()=>{try{device=await readDevice(symbolsFor());}catch(_){device={state:'ERROR',series:new Map(),priced:0};}finally{inflight=null;}})();
 return inflight;}
/* The shared page result for V (QgvScores.pageResult; memoised there per inputs, Universe read, catalog and identities). */
async function resultFor(entry,opts){const QS=g.QgvScores;if(!entry.inputs||!QS||typeof QS.pageResult!=='function')return null;
 let catalog=null;try{catalog=await opts.catalogPromise;}catch(_){catalog=null;}
 try{return await QS.pageResult(g,{v2Inputs:entry.inputs,catalog:catalog||null,identities:[subjectOf(entry.inputs,entry.spec).identity]});}catch(_){return null;}}
function radarsIn(root){if(!root)return[];const list=[];if(root.matches&&root.matches('[data-stat-radar]'))list.push(root);if(root.querySelectorAll)list.push(...root.querySelectorAll('[data-stat-radar]'));return list;}
let again=false,wired=false;
function subscribeOnce(){const PS=g.PriceStore;if(subscribed||!PS||typeof PS.subscribe!=='function')return;subscribed=true;
 try{PS.subscribe(()=>{if(again)return;again=true;Promise.resolve().then(async()=>{again=false;const doc=g.document;if(!doc)return;const els=radarsIn(doc);if(!els.length)return;await refreshDevice();for(const el of radarsIn(doc))paint(el);});});}catch(_){subscribed=false;}}
/* The auxiliary-axis toggle (event delegation; no inline handlers under the CSP). The choice lives in RAM for this page only. */
function wireOnce(doc){if(wired||!doc||typeof doc.addEventListener!=='function')return;wired=true;
 doc.addEventListener('click',e=>{const b=e.target&&e.target.closest?e.target.closest('[data-sr-aux-toggle]'):null;if(!b)return;const el=b.closest('[data-stat-radar]'),entry=el?live.get(el.dataset.statRadar):null;if(!entry)return;
  entry.aux=!entry.aux;paint(el);const nb=el.querySelector('[data-sr-aux-toggle]');if(nb)nb.focus();});}
/* After html(): read the shared page result (V) and the price data (price axes) and repaint every radar under root.
   opts: {catalogPromise} (the device catalog the page result reads quotes with). */
async function mount(root,opts={}){
 const els=radarsIn(root);if(!els.length)return;subscribeOnce();wireOnce(els[0].ownerDocument);
 for(const el of els){const entry=live.get(el.dataset.statRadar);if(entry)entry.result=await resultFor(entry,opts||{});}
 await refreshDevice();for(const el of els)if(el.isConnected)paint(el);}
/* Model for tests and other screens (no DOM). */
function compute(spec,{screens,result=null,aux=false,now}={},dev=device){return build(inputsOf(screens),spec,dev,result,{aux,now:finite(now)?now:Date.now()});}
/* Financial detail row (TARGET analysis 재무 tab, Universe504 page): the published operating_margin_std_5y_pp with its basis
   (FY0..FY-4: the fiscal years of v_inputs_v2.operating_margin_history when published, else "5개 회계연도"), source and as_of,
   or the missing-data reason. Returns '<dt>…</dt><dd>…</dd>' for a <dl class="kv">. */
function marginDetail(spec,ctx={}){
 const locale=ctx.locale==='en-US'?'en-US':'ko-KR',T=tr(locale),en=locale==='en-US',inputs=inputsOf(ctx.screens),s=subjectOf(inputs,spec),x=inputs?marginValue(s.rec):na('SEC_QGV2_NOT_AVAILABLE');
 const hist=s.rec&&object(s.rec.v_inputs)&&Array.isArray(s.rec.v_inputs.operating_margin_history)?s.rec.v_inputs.operating_margin_history.map(h=>h.period_end).filter(d=>typeof d==='string'&&DAY.test(d)).sort().slice(-5):[];
 const years=hist.length===5?'FY '+hist.join(' · '):T('5개 회계연도','5 fiscal years');
 const src=T('출처 sec-qgv2.json · as_of ','source sec-qgv2.json · as_of ')+(inputs?clock(inputs.as_of):'—');
 const dd=finite(x.value)?'<span class="num">'+esc(fmtRaw('stdpp',x.value,locale))+'</span> <span class="small">'+esc(T('5년 영업이익률 모표준편차(낮을수록 안정) · 기준 ','population std of the 5-year operating margin (lower = steadier) · basis ')+years+' · '+src)+'</span>'
  :'<span class="badge NOT_AVAILABLE">'+esc(T('미산출','n/a'))+'</span> <span class="small">'+esc(reasonText(x.reason,en)+' · '+src)+'</span>';
 return '<dt>'+esc(T('이익률 안정성','Margin stability'))+'</dt><dd data-sr-margin-detail="'+(finite(x.value)?String(x.value):'NA')+'" data-sr-margin-reason="'+esc(x.reason||'')+'" data-sr-margin-years="'+esc(hist.join(','))+'">'+dd+'</dd>';}
return Object.freeze({AXES,AUX,DECISION,ADOPT_MIN,MIN_PEERS,MIN_GROUP,SESSIONS,MIN_SESSIONS,MIN_RETURNS,RS_SESSIONS,MIN_RS_SESSIONS,STALE_SESSIONS,STALE_DAYS,SPLIT_RATIOS,BASES,CONFIRMED_BASES,REASON,percentile,priceAxes,freshness,compute,html,mount,marginDetail,reasonText});
});
