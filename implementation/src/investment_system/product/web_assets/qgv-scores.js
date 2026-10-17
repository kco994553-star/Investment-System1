/* QgvScores: the ONE score accessor. S04/S05 (company-screen.js), S06 (leaderboard-screen.js), the virtual-trading rehearsal
   judgement rows and the daily report + its export (app.js -> DailyReport) all read scores here, and only this module reads
   ScoringDefault. Owner decision 2026-10-14: QGV v2 PROVISIONAL (QgvV2) is the ONLY score on screens. v1 is neither a primary,
   a comparison nor a [자세히] reference, and a company whose v2 cannot be computed shows the v2 NOT_AVAILABLE state with its
   reason (naText: calculated factors n/total, axis below 50% of its weight); never v1. v1 survives only in the forward-validation
   ledger comparison record (tools/forward_validation_ledger.py), which does not read this module.
   v2 V needs this device's prices (Universe sheet tab / device quotes / Worker closes via DeviceValuation.deviceQuote), held in
   RAM only: nothing here is stored, logged or sent, and no result carries a price, market cap or EV. Missing is null, never 0. */
(function(root,factory){const node=typeof module==='object'&&module.exports;
 const dep=(file,name)=>node?()=>require('./'+file):()=>root[name];
 const api=factory(dep('qgv-v2.js','QgvV2'),dep('scoring-default.js','ScoringDefault'),dep('qgv2-inputs.js','Qgv2Inputs'));
 if(node)module.exports=api;else root.QgvScores=api;})(typeof globalThis==='object'?globalThis:this,function(qgvV2,scoringConfig,qgv2Inputs){
'use strict';
const MODES=['v2'];
const LABEL={v2:['점수 기준 v2 · PROVISIONAL','Score basis v2 · PROVISIONAL']};
const FLAG={VALUE_TRAP_CAUTION:['가치 함정 주의','Value-trap caution'],V_NOT_AVAILABLE:['V 없음','No V'],GATE_NOT_EVALUATED:['관문 판정 불가','Gate not evaluated'],EBIT_ESTIMATED:['추정(대체 계산)','Estimate (substitute calculation)'],CALC_VERSION_MISMATCH:['계산 규칙 버전이 달라 순위에서 제외','Excluded from ranking: different calculation-rule version']};
/* EBIT_ESTIMATED: the published sec-qgv2.json row says (metrics.ebit_estimated_years >= 1) that at least one EBIT it used is the
   substitute pretax income + interest expense (no reported operating income; QGV_V2_QG_METHOD.md rule EBIT). Every EBIT-derived
   v2 value of that row (ROIC, moat, interest coverage, net debt/EBITDA, EV/EBIT, operating margins) carries the flag. */
function ebitEstimated(record){const n=record&&object(record.metrics)?record.metrics.ebit_estimated_years:null;return finite(n)&&n>=1;}
const object=v=>v!==null&&typeof v==='object'&&!Array.isArray(v),finite=v=>typeof v==='number'&&Number.isFinite(v);
function config(){let c=null;try{c=scoringConfig();}catch(_){c=null;}return c&&typeof c==='object'?c:{};}
// v2 is the only display score (owner decision 2026-10-14); any other stored value no longer reaches a screen.
function scoringDefault(){return 'v2';}
/* {basis, label, since}: always v2 '기본'. Before v2 is computed on this device the screens show the v2 NOT_AVAILABLE state
   with its reason (no v1 fallback any more). since = the configured switch date of strategy version v2. */
function basis(intended,v2Ready){const since=config().v2_since;
 return Object.freeze({basis:'v2',label:'기본',label_en:'default',since:typeof since==='string'?since:null,intended:'v2',ready:v2Ready===true});}
const key=t=>String(t||'').replaceAll('.','-').toUpperCase(),symbolOf=code=>key(String(code).slice(String(code).indexOf(':')+1));
// Identity -> v2 record key: the TARGET row ('TARGET:<id>', fresher) when it has data, else the Universe code by ticker.
function codeIndex(inputs){const codes=new Map();if(inputs)for(const code of Object.keys(inputs.records))if(!code.startsWith('TARGET:')&&!codes.has(symbolOf(code)))codes.set(symbolOf(code),code);
 return c=>{const t='TARGET:'+c.company_id,r=inputs&&Object.hasOwn(inputs.records,t)?inputs.records[t]:null;if(r&&r.state!=='NOT_AVAILABLE')return t;return codes.get(key(c.ticker))||null;};}
function record(screens,file,id){const p=screens&&screens[file];return p&&p.data&&object(p.data.companies)&&Object.hasOwn(p.data.companies,id)?p.data.companies[id]:null;}
function v2Display(r){
 if(!r)return{version:'v2',q:null,g:null,v:null,total:null,partial:true,factors_available:0,factors_total:qgvV2().FACTORS.length,flags:['V2_INPUTS_NOT_AVAILABLE'],state:'NOT_AVAILABLE',total_reason:'V2_INPUTS_NOT_AVAILABLE'};
 const ax=a=>r.axes[a].score;
 return{version:'v2',q:ax('Q'),g:ax('G'),v:ax('V'),total:r.total,total_reason:r.total===null?(r.total_reason||'AXIS_WEIGHT_INSUFFICIENT'):null,partial:['Q','G','V'].some(a=>r.axes[a].state!=='READY'),factors_available:r.factors_available,factors_total:r.factors_total,flags:[...r.flags],state:r.total===null?'NOT_AVAILABLE':'READY',
  axes:r.axes,factors:r.factors,weights:r.weights,profile:r.profile,q_industry_percentile:r.q_industry_percentile,v_excluded:r.v_excluded,detail:r.detail,reference_range:r.reference_range,selected_types:r.selected_types,type_reason:r.type_reason,value_trap_gate:r.value_trap_gate===true};
}
let memo=null;
function universeScores(v2Inputs,quotes,preset,gate,memberships,cyclicalBasis={}){
 const mk=JSON.stringify([preset,gate,memberships,cyclicalBasis]);if(memo&&memo.inputs===v2Inputs&&memo.quotes===quotes&&memo.key===mk)return memo.result;
 // A row of another calculation-rule version never joins this device's ranking population (QGV_V2_QG_METHOD.md 5, calc_version).
 const companies={};for(const[code,r]of Object.entries(v2Inputs.records))if(r.calc_version_mismatch!==true)companies[code]={cyclical_basis:cyclicalBasis[code]===true,cik:r.cik,industry_group:r.industry_group,profile:r.profile,factors:r.factors,v_inputs:r.v_inputs,qg_axes:r.qg_axes,in_cross_section:r.in_cross_section!==false,memberships:Object.hasOwn(memberships,code)?memberships[code]:null};
 const result=qgvV2().scoreUniverse(companies,quotes,{preset,gate});memo={inputs:v2Inputs,quotes,key:mk,result};return result;
}
/* The accessor. identities: [{company_id, ticker}] rows to show; publicScreens: the app's loaded public screens (company types
   and sec-qgv2.json under SecQgv2.FILE); quotes: {code:{price,currency}} RAM. Returns rows with v2 (= primary). reference is
   always null: there is no comparison score on screens. */
function compute({identities=[],publicScreens={},v2Inputs,quotes={},preset,gate=null,referenceRows={}}={}){
 const V2=qgvV2(),intended='v2',inputs=v2Inputs===undefined?(publicScreens&&qgv2Inputs()?publicScreens[qgv2Inputs().FILE]||null:null):v2Inputs;
 const chosen=preset&&Object.hasOwn(V2.PRESETS,preset)?preset:V2.DEFAULT_PRESET,gateOn=gate===null||gate===undefined?V2.GATE_DEFAULT:Boolean(gate);
 const codeFor=codeIndex(inputs);
 const memberships={};for(const c of identities){const code=codeFor(c),t=record(publicScreens,'company-types-pricefree.json',c.company_id);if(code&&t&&t.state!=='NOT_AVAILABLE'&&object(t.memberships))memberships[code]=t.memberships;}
 const cyclicalBasis={};try{const engine=globalThis.PlaybookEngine,cfg=globalThis.PlaybookConfigDefaults;if(engine?.classifyTypesV0&&cfg&&inputs?.records){const symbols={};for(const c of identities){const code=codeFor(c);if(code)symbols[code]=c.ticker;}for(const[code,r]of Object.entries(inputs.records)){const symbol=symbols[code]||symbolOf(code),group=engine.sectorFor?.(cfg,symbol,null,r.sic);cyclicalBasis[code]=engine.classifyTypesV0(cfg,{sic:r.sic,sector_subgroup:group?.sector??null,revenue_volatility_5y_rank_pct:finite(r.metrics?.revenue_volatility_5y_rank_pct)?r.metrics.revenue_volatility_5y_rank_pct/100:null}).cyclical?.member===true;}}}catch(_){}
 let universe=null,v2Reason=inputs?null:'SEC_QGV2_NOT_AVAILABLE';if(inputs){try{universe=universeScores(inputs,object(quotes)?quotes:{},chosen,gateOn,memberships,cyclicalBasis);}catch(_){universe=null;v2Reason='V2_CALCULATION_FAILED';}}
 const v2Ready=!!universe&&Object.values(universe).some(r=>finite(r.total));if(universe&&!v2Ready)v2Reason='V2_SCORES_NOT_AVAILABLE';
 const b=basis(intended,v2Ready),current=b.basis,rows={};let ranked=[];
 for(const c of identities){const code=codeFor(c);let v2=v2Display(universe&&code?universe[code]:null);if(universe&&code&&inputs.records[code]?.calc_version_mismatch===true){v2.flags=['CALC_VERSION_MISMATCH'];v2.reason='CALC_VERSION_MISMATCH';}if(universe&&code&&universe[code]&&ebitEstimated(inputs.records[code])){v2.flags.push('EBIT_ESTIMATED');const ys=inputs.records[code].metrics.ebit_estimated_fiscal_years;if(Array.isArray(ys))v2.ebit_estimated_fiscal_years=[...ys];}
  const src=inputs&&code&&Object.hasOwn(inputs.records,code)?inputs.records[code]:null;if(src&&src.state==='NOT_AVAILABLE'&&src.calc_version_mismatch!==true&&v2.total===null){v2.total_reason='SOURCE_NOT_AVAILABLE';v2.source_reason_codes=[...(src.na_reasons||[])];}
  const ref=object(referenceRows)?referenceRows[c.company_id]:null;if(ref?.reference_only===true&&object(ref.factors)&&object(ref.axes)){try{const factors={},qg_axes={};for(const axis of ['Q','G']){let coverage=0;for(const[f,w]of Object.entries(V2.WEIGHTS[axis])){const s=ref.factors[f];factors[f]=finite(s)&&s>=0&&s<=100?s:null;if(factors[f]!==null)coverage+=w;}qg_axes[axis]={score:coverage>=50&&finite(ref.axes[axis]?.score)?ref.axes[axis].score:null};}
   v2=v2Display(V2.scoreUniverse({reference:{profile:'GENERAL',industry_group:null,factors,qg_axes,v_inputs:null,memberships:null}}, {},{preset:chosen,gate:gateOn}).reference);v2.reference_only=true;v2.reference_label='참고 순위';v2.reference_label_en='Reference ranking';}catch(_){}}
  const row={company_id:c.company_id,ticker:c.ticker,code,v2,primary:v2,reference:null,rank:null};rows[c.company_id]=row;}
 ranked=Object.values(rows).filter(r=>finite(r.primary.total)&&r.primary.reference_only!==true).sort((a,b)=>b.primary.total-a.primary.total||(a.ticker<b.ticker?-1:1));
 ranked.forEach((r,i)=>{r.rank=i+1;});
 const quoted=object(quotes)?Object.keys(quotes).length:0;
 return{default:current,basis:b,label:LABEL[current],profile:{preset:chosen,gate:gateOn,id:V2.VERSION+'/'+chosen+'/gate-'+(gateOn?'on':'off'),name:V2.PRESETS[chosen]},
  v2_state:v2Ready?'READY':'NOT_AVAILABLE',v2_reason:v2Reason,v2_as_of:inputs?inputs.as_of:null,priced_codes:quoted,rows};
}
/* Rows for the virtual-trading rehearsal snapshot and the daily report (+ export): {cid:{q,g,partial,...}} from v2 only.
   compare is always null (no comparison score). */
function judgmentRows(computed){
 const out={};if(!computed||!object(computed.rows))return out;
 for(const[cid,r]of Object.entries(computed.rows)){const p=r.primary;
  out[cid]={q:p.q,g:p.g,partial:p.partial,v:p.v,total:p.total,total_reason:p.total_reason||null,version:p.version,factors_available:p.factors_available,factors_total:p.factors_total,flags:[...p.flags],value_trap:p.flags.includes('VALUE_TRAP_CAUTION'),value_trap_gate:p.value_trap_gate===true,compare:null};}
 return out;
}
/* Device quotes for the v2 cross-section (RAM): the Universe tab read on this device (PrivateSubsetView.prices) first, then
   this device's stored/sheet/Worker quote per shown company (DeviceValuation.deviceQuote), plus PriceStore month-end closes
   for the own-history factor. Never stored or sent. */
async function collectQuotes(win,{identities=[],v2Inputs=null,catalog=null}={}){
 const out={};if(!v2Inputs||!object(v2Inputs.records))return out;const codeFor=codeIndex(v2Inputs),tickers={};
 let universe=null;try{universe=win.PrivateSubsetView&&typeof win.PrivateSubsetView.prices==='function'?win.PrivateSubsetView.prices():null;}catch(_){universe=null;}
 const bySymbol=new Map();if(universe&&typeof universe.forEach==='function')universe.forEach((q,code)=>{if(!(q&&finite(q.price)&&q.price>0&&typeof q.currency==='string'))return;bySymbol.set(symbolOf(code),{price:q.price,currency:q.currency});if(Object.hasOwn(v2Inputs.records,code))out[code]={price:q.price,currency:q.currency};});
 const dq=catalog&&win.DeviceValuation&&typeof win.DeviceValuation.deviceQuote==='function';
 for(const c of identities){const code=codeFor(c);if(!code)continue;tickers[code]=c.ticker;if(Object.hasOwn(out,code))continue;if(bySymbol.has(key(c.ticker))){out[code]={...bySymbol.get(key(c.ticker))};continue;}if(!dq)continue;
  let q=null;try{q=await win.DeviceValuation.deviceQuote(win,catalog,c.ticker);}catch(_){q=null;}if(q&&finite(q.price)&&q.price>0)out[code]={price:q.price,currency:q.currency};}
 // v_vs_own_history: month-end closes of the user's sheet Prices tab (PriceStore device module, RAM). Absent -> the factor is
 // NOT_AVAILABLE (PRICE_HISTORY_NOT_AVAILABLE); never filled.
 const store=win.PriceStore&&typeof win.PriceStore.monthEndCloses==='function'?win.PriceStore:null;
 if(store)for(const code of Object.keys(out)){let m=null;try{m=await store.monthEndCloses(symbolOf(Object.hasOwn(tickers,code)?tickers[code]:code));}catch(_){m=null;}
  const clean={};if(object(m))for(const[k,v]of Object.entries(m))if(/^\d{4}-(0[1-9]|1[0-2])$/.test(k)&&finite(v)&&v>0)clean[k]=v;if(Object.keys(clean).length)out[code]={...out[code],month_closes:clean};}
 return out;
}
const num=(v,d=1)=>finite(v)?(Math.round(v*10**d)/10**d).toFixed(d):'—';
/* `row` (optional display row): EBIT_ESTIMATED names the substituted fiscal years, e.g. '추정(대체 계산): FY2023·FY2024'. */
function flagText(flags,en,row){const years=row&&Array.isArray(row.ebit_estimated_fiscal_years)?row.ebit_estimated_fiscal_years.filter(y=>Number.isInteger(y)):[];
 return(flags||[]).filter(f=>Object.hasOwn(FLAG,f)).map(f=>FLAG[f][en?1:0]+(f==='EBIT_ESTIMATED'&&years.length?': '+years.map(y=>'FY'+y).join(en?', ':'·'):''));}
// One-line text of a display row: 'QGV 61.2 · Q 60.1 · G 55.0 · V 48.2 · 산출 요인 14/15'.
function summaryText(d,en){
 if(!d)return '—';const n=(en?'calculated factors ':'산출 요인 ')+d.factors_available+'/'+d.factors_total;
 return (d.reference_only?(en?'Reference ranking · ':'참고 순위 · '):'')+'QGV '+num(d.total)+' · Q '+num(d.q)+' · G '+num(d.g)+' · V '+num(d.v)+' · '+n;
}
/* Why v2 is NOT_AVAILABLE for a row: 'QGV v2 산출 불가 · 산출 요인 6/15 · Q 축 비중 50% 미만'. Never a v1 fallback. */
const SOURCE_REASON={NOT_COLLECTED:['아직 수집 안 됨','not collected yet'],CIK_UNRESOLVED:['CIK 미해결','CIK unresolved'],NO_ANNUAL_SEC_FINANCIALS:['연간 SEC 재무 없음','no annual SEC financials'],INVALID_INPUT:['원자료 형식 오류','invalid source data'],NON_SEC_ISSUER:['SEC 공시 대상 아님','not an SEC filer']};
function naText(d,en){
 const head=en?'QGV v2 not available':'QGV v2 산출 불가';
 if(d&&d.total_reason==='SOURCE_NOT_AVAILABLE')return head+' · '+(en?'source data missing':'원자료 없음')+((d.source_reason_codes||[]).length?' ('+d.source_reason_codes.map(r=>SOURCE_REASON[r]?SOURCE_REASON[r][en?1:0]:r).join(', ')+')':'');
 if(d&&(d.flags||[]).includes('CALC_VERSION_MISMATCH'))return head+' · '+FLAG.CALC_VERSION_MISMATCH[en?1:0];
 if(!d||(d.flags||[]).includes('V2_INPUTS_NOT_AVAILABLE'))return head+' · '+(en?'no v2 input for this company':'이 기업의 v2 입력 없음');
 const parts=[head,(en?'calculated factors ':'산출 요인 ')+d.factors_available+'/'+d.factors_total];
 for(const a of ['Q','G','V']){const x=d.axes&&d.axes[a];if(x&&x.reason==='AXIS_WEIGHT_INSUFFICIENT')parts.push(a+(en?' axis below 50% of its weight':' 축 비중 50% 미만'));}
 if(d.total_reason==='AXIS_WEIGHT_INSUFFICIENT'&&parts.length===2)parts.push(en?'available axes below 50% of the weight':'산출 축 비중 50% 미만');
 return parts.join(' · ');
}
/* Screen words for v2 codes (owner rule 2026-10-14: screens show results; codes stay in data-* attributes and in
   Settings > 원자료 보기(개발자용)). Unknown codes read '자료 부족', never the code itself. */
const REASON={SEC_FACTOR_NOT_AVAILABLE:['SEC 재무로 계산할 수 없음','Not computable from SEC financials'],NO_DEVICE_PRICE:['이 기기에 시세 없음','No price on this device'],
 PRICE_HISTORY_NOT_AVAILABLE:['월말 가격 이력 없음','No month-end price history'],HISTORY_TOO_SHORT:['비교할 과거 기간이 짧음','History too short'],
 NORMALIZED_HISTORY_NOT_AVAILABLE:['경기민감 기업이라 과거 비교 보류','Cyclical: own-history comparison withheld'],NORMALIZED_EARNINGS_NOT_AVAILABLE:['정상화 이익을 계산할 자료 부족','Not enough data for normalized earnings'],
 EBIT_NOT_AVAILABLE:['영업이익 자료 없음','No operating income'],FCF_NOT_AVAILABLE:['잉여현금흐름 자료 없음','No free cash flow'],SHARES_NOT_AVAILABLE:['주식 수 자료 없음','No share count'],
 DEBT_CASH_NOT_AVAILABLE:['부채·현금 자료 없음','No debt / cash data'],EV_NON_POSITIVE:['기업가치가 0 이하','Enterprise value not positive'],NON_POSITIVE_CASHFLOW:['현금흐름이 0 이하','Cash flow not positive'],
 CROSS_SECTION_TOO_SMALL:['비교할 종목 수 부족','Too few companies to compare'],REALIZED_GROWTH_NOT_AVAILABLE:['실현 성장률 자료 없음','No realized growth'],
 FINANCIAL_PROFILE_V_NOT_DEFINED:['금융업 가치 계산 방식 미정','Financials: value method not defined'],V_INPUTS_NOT_AVAILABLE:['가치 입력 자료 없음','No value inputs'],
 CURRENCY_BASIS_UNCONFIRMED:['시세와 재무 통화가 달라 계산 보류','Price and filing currencies differ'],EXPLICIT_GROWTH_UNDECIDED:['성장률 규칙 미정','Growth rule undecided'],
 AXIS_NOT_PUBLISHED:['공개 축 점수 없음','Axis score not published'],AXIS_WEIGHT_INSUFFICIENT:['산출 요인 비중 50% 미만','Available weight below 50%']};
function reasonText(code,en){return code&&Object.hasOwn(REASON,code)?REASON[code][en?1:0]:(en?'Not enough data':'자료 부족');}
const BASIS={INDUSTRY:['업종 안 비교','Within industry'],UNIVERSE:['전체 비교','Whole universe'],UNIVERSE_FALLBACK:['전체 비교 (업종 표본 부족)','Whole universe (industry too small)'],OWN_HISTORY:['자기 과거 비교','Own history']};
// A v2 factor's state in words: where the score came from, or '산출 불가'.
function factorStateText(x,en){if(!x||x.score===null||x.score===undefined)return en?'Not available':'산출 불가';
 if(x.basis&&Object.hasOwn(BASIS,x.basis))return BASIS[x.basis][en?1:0];return x.state==='PUBLIC'?(en?'Published':'공개 점수'):(en?'This device':'이 기기 계산');}
// '균형 · 관문 켬' for {preset, gate}; the preset's own parenthesis (e.g. '가치(관문 켬)') is dropped so the gate is said once.
function profileText(profile,en){if(!profile)return '';const p=qgvV2().PRESETS[profile.preset],name=p?String(en?p.name_en:p.name).replace(/\s*\(.*\)$/,''):String(profile.preset||'');
 return name+' · '+(profile.gate?(en?'gate on':'관문 켬'):(en?'gate off':'관문 끔'));}
function label(version,en){return(LABEL[version]||LABEL.v2)[en?1:0];}
// Badge text of the basis: '점수 기준 v2 · PROVISIONAL · 기본' (+ ' · 2026-10-19부터' when the switch date is configured).
function basisText(S,en){const b=S&&S.basis?S.basis:basis('v2',false);return label('v2',en)+' · '+(en?b.label_en:b.label)+(b.since?(en?' · since ':' · ')+b.since+(en?'':'부터'):'');}
function presets(){return qgvV2().PRESETS;}
return Object.freeze({MODES,LABEL,FLAG,scoringDefault,compute,judgmentRows,collectQuotes,summaryText,naText,flagText,label,basis,basisText,presets,symbolOf,reasonText,factorStateText,profileText});
});
