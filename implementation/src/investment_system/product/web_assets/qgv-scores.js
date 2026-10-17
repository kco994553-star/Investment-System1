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
const FLAG={VALUE_TRAP_CAUTION:['가치 함정 주의','Value-trap caution'],V_NOT_AVAILABLE:['V 없음','No V'],GATE_NOT_EVALUATED:['관문 판정 불가','Gate not evaluated'],EBIT_ESTIMATED:['추정(대체 계산)','Estimate (substitute calculation)'],CALC_VERSION_MISMATCH:['계산 규칙 버전이 달라 순위에서 제외','Excluded from ranking: different calculation-rule version'],PRICE_IDENTITY_CONFLICT:['가격 식별 충돌로 가격·V·종합 점수 사용 중지','Price identity conflict: price, V and total not used']};
/* EBIT_ESTIMATED: the published sec-qgv2.json row says (metrics.ebit_estimated_years >= 1) that at least one EBIT it used is the
   substitute pretax income + interest expense (no reported operating income; QGV_V2_QG_METHOD.md rule EBIT). Every EBIT-derived
   v2 value of that row (ROIC, moat, interest coverage, net debt/EBITDA, EV/EBIT, operating margins) carries the flag. */
function ebitEstimated(record){const n=record&&object(record.metrics)?record.metrics.ebit_estimated_years:null;return finite(n)&&n>=1;}
const object=v=>v!==null&&typeof v==='object'&&!Array.isArray(v),finite=v=>typeof v==='number'&&Number.isFinite(v);
function config(){let c=null;try{c=scoringConfig();}catch(_){c=null;}return c&&typeof c==='object'?c:{};}
// v2 is the only display score (owner decision 2026-10-14); any other stored value no longer reaches a screen.
function scoringDefault(){return 'v2';}
/* {basis, label, since, type_scope}: always v2 '기본'. Before v2 is computed on this device the screens show the v2 NOT_AVAILABLE
   state with its reason (no v1 fallback any more). since = the configured switch date of strategy version v2. type_scope = the
   type-application scope id the scores use (QgvV2.TYPE_SCOPE, owner decision 2026-10-17 item 4); calc_version stays as published. */
function typeScope(){try{const v=qgvV2();return v&&typeof v.TYPE_SCOPE==='string'?v.TYPE_SCOPE:null;}catch(_){return null;}}
function basis(intended,v2Ready){const since=config().v2_since;
 return Object.freeze({basis:'v2',label:'기본',label_en:'default',since:typeof since==='string'?since:null,intended:'v2',ready:v2Ready===true,type_scope:typeScope()});}
const key=t=>String(t||'').replaceAll('.','-').toUpperCase(),symbolOf=code=>key(String(code).slice(String(code).indexOf(':')+1));
// Identity -> v2 record key: the TARGET row ('TARGET:<id>', fresher) when it has data, else the Universe code by ticker.
/* UNI-TARGET (owner decision 2026-10-17, #289 item 4). A TARGET row's own SEC observation (fixed CIK) stays usable when a Universe
   code is withdrawn for an identity conflict (Qgv2Inputs universe_withdrawal), and no withdrawn row ever lends it a score. Its device
   price, however, is fetched by ticker symbol (the Universe sheet row of that symbol, DeviceValuation.deviceQuote, PriceStore closes).
   When that symbol is the symbol of a withdrawn Universe code, the price identity is in conflict: no price, no V, no total score,
   no rank or candidate place for that TARGET (reason PRICE_IDENTITY_CONFLICT); its Q·G stay. A TARGET of another symbol is
   independent and unchanged. */
function conflictedSymbols(inputs){const out=new Set();if(inputs&&object(inputs.records))for(const[code,r]of Object.entries(inputs.records))if(!code.startsWith('TARGET:')&&r&&r.universe_withdrawal===true)out.add(symbolOf(code));return out;}
function priceConflict(inputs,c,code,symbols){return !!code&&code.startsWith('TARGET:')&&symbols.has(key(c.ticker))&&inputs.records[code]?.identity_withdrawn!==true;}
function codeIndex(inputs){const codes=new Map();if(inputs)for(const code of Object.keys(inputs.records))if(!code.startsWith('TARGET:')&&!codes.has(symbolOf(code)))codes.set(symbolOf(code),code);
 return c=>{const t='TARGET:'+c.company_id,r=inputs&&Object.hasOwn(inputs.records,t)?inputs.records[t]:null;if(r&&r.state!=='NOT_AVAILABLE')return t;return codes.get(key(c.ticker))||null;};}
function v2Display(r){
 if(!r)return{version:'v2',q:null,g:null,v:null,total:null,partial:true,factors_available:0,factors_total:qgvV2().FACTORS.length,flags:['V2_INPUTS_NOT_AVAILABLE'],state:'NOT_AVAILABLE',total_reason:'V2_INPUTS_NOT_AVAILABLE'};
 const ax=a=>r.axes[a].score;
 return{version:'v2',q:ax('Q'),g:ax('G'),v:ax('V'),total:r.total,total_reason:r.total===null?(r.total_reason||'AXIS_WEIGHT_INSUFFICIENT'):null,partial:['Q','G','V'].some(a=>r.axes[a].state!=='READY'),factors_available:r.factors_available,factors_total:r.factors_total,flags:[...r.flags],state:r.total===null?'NOT_AVAILABLE':'READY',
  axes:r.axes,factors:r.factors,weights:r.weights,profile:r.profile,q_industry_percentile:r.q_industry_percentile,v_excluded:r.v_excluded,detail:r.detail,reference_range:r.reference_range,selected_types:r.selected_types,type_reason:r.type_reason,value_trap_gate:r.value_trap_gate===true};
}
/* TYPE-SCOPE: the memberships of one v2 record — the same approved rule for every row (QgvV2.pricefreeMemberships on the row's
   own published metrics); a row of another calc_version is not scored, so it has none (null, never 0). */
function rowMemberships(r){return r&&r.calc_version_mismatch!==true?qgvV2().pricefreeMemberships(r.metrics):null;}
/* The type memberships the v2 score of one identity uses: the same record (codeIndex: the TARGET row when it has data, else the
   Universe code by ticker) and the same rule (rowMemberships). The playbook's growth fact reads it (owner decision 2026-10-17
   item 4). Returns {code, type_scope, memberships} or null when the identity has no scored v2 record. */
function typeMemberships({identity,publicScreens={},v2Inputs}={}){
 const inputs=v2Inputs===undefined?(publicScreens&&qgv2Inputs()?publicScreens[qgv2Inputs().FILE]||null:null):v2Inputs;
 if(!object(identity)||!inputs||!object(inputs.records))return null;const code=codeIndex(inputs)(identity),m=code?rowMemberships(inputs.records[code]):null;
 return m?{code,type_scope:typeScope(),memberships:m}:null;}
let memo=null;
function universeScores(v2Inputs,quotes,preset,gate,cyclicalBasis={}){
 const mk=JSON.stringify([preset,gate,cyclicalBasis]);if(memo&&memo.inputs===v2Inputs&&memo.quotes===quotes&&memo.key===mk)return memo.result;
 // A row of another calculation-rule version never joins this device's ranking population (QGV_V2_QG_METHOD.md 5, calc_version).
 // TYPE-SCOPE (owner instruction 2026-10-17): type memberships come from each row's own published price-free metrics with the
 // same approved rule (QgvV2.pricefreeMemberships), for every Universe code and TARGET row alike. TARGET membership no longer
 // decides who is typed (formerly only TARGET ids, via company-types-pricefree.json, got type weights).
 const companies={};for(const[code,r]of Object.entries(v2Inputs.records))if(r.calc_version_mismatch!==true)companies[code]={cyclical_basis:cyclicalBasis[code]===true,cik:r.cik,industry_group:r.industry_group,profile:r.profile,factors:r.factors,v_inputs:r.v_inputs,qg_axes:r.qg_axes,in_cross_section:r.in_cross_section!==false,memberships:rowMemberships(r)};
 const result=qgvV2().scoreUniverse(companies,quotes,{preset,gate});memo={inputs:v2Inputs,quotes,key:mk,result};return result;
}
/* The accessor. identities: [{company_id, ticker}] rows to show; publicScreens: the app's loaded public screens (sec-qgv2.json
   under SecQgv2.FILE; type memberships come from its rows, company-types-pricefree.json is display-only); quotes:
   {code:{price,currency}} RAM. Returns rows with v2 (= primary). reference is always null: there is no comparison score on screens. */
function compute({identities=[],publicScreens={},v2Inputs,quotes={},preset,gate=null,referenceRows={}}={}){
 const V2=qgvV2(),intended='v2',inputs=v2Inputs===undefined?(publicScreens&&qgv2Inputs()?publicScreens[qgv2Inputs().FILE]||null:null):v2Inputs;
 const chosen=preset&&Object.hasOwn(V2.PRESETS,preset)?preset:V2.DEFAULT_PRESET,gateOn=gate===null||gate===undefined?V2.GATE_DEFAULT:Boolean(gate);
 const codeFor=codeIndex(inputs);
 const cyclicalBasis={};try{const engine=globalThis.PlaybookEngine,cfg=globalThis.PlaybookConfigDefaults;if(engine?.classifyTypesV0&&cfg&&inputs?.records){const symbols={};for(const c of identities){const code=codeFor(c);if(code)symbols[code]=c.ticker;}for(const[code,r]of Object.entries(inputs.records)){const symbol=symbols[code]||symbolOf(code),group=engine.sectorFor?.(cfg,symbol,null,r.sic);cyclicalBasis[code]=engine.classifyTypesV0(cfg,{sic:r.sic,sector_subgroup:group?.sector??null,revenue_volatility_5y_rank_pct:finite(r.metrics?.revenue_volatility_5y_rank_pct)?r.metrics.revenue_volatility_5y_rank_pct/100:null}).cyclical?.member===true;}}}catch(_){}
 // A file this page cannot read: SCHEMA_NEWER (a newer data format; reload) is told apart from a missing file (Qgv2Inputs.lastReason).
 const newer=!inputs&&(()=>{try{return qgv2Inputs().lastReason?.()==='SCHEMA_NEWER';}catch(_){return false;}})();
 const symbols=conflictedSymbols(inputs),blocked=new Set(inputs?identities.map(c=>codeFor(c)).filter((code,i)=>priceConflict(inputs,identities[i],code,symbols)):[]);
 let priced=object(quotes)?quotes:{};if(blocked.size){priced={...priced};for(const code of blocked)delete priced[code];}
 let universe=null,v2Reason=inputs?null:newer?'SEC_QGV2_SCHEMA_NEWER':'SEC_QGV2_NOT_AVAILABLE';if(inputs){try{universe=universeScores(inputs,priced,chosen,gateOn,cyclicalBasis);}catch(_){universe=null;v2Reason='V2_CALCULATION_FAILED';}}
 const v2Ready=!!universe&&Object.values(universe).some(r=>finite(r.total));if(universe&&!v2Ready)v2Reason='V2_SCORES_NOT_AVAILABLE';
 const b=basis(intended,v2Ready),current=b.basis,rows={};let ranked=[];
 for(const c of identities){const code=codeFor(c);let v2=v2Display(universe&&code?universe[code]:null);if(universe&&code&&inputs.records[code]?.calc_version_mismatch===true){v2.flags=['CALC_VERSION_MISMATCH'];v2.reason='CALC_VERSION_MISMATCH';}if(universe&&code&&universe[code]&&ebitEstimated(inputs.records[code])){v2.flags.push('EBIT_ESTIMATED');const ys=inputs.records[code].metrics.ebit_estimated_fiscal_years;if(Array.isArray(ys))v2.ebit_estimated_fiscal_years=[...ys];}
  // identity_withdrawn (Qgv2Inputs): a TARGET issuer withdrawn for an identity conflict, its TARGET row and same-CIK Universe codes.
  const src=inputs&&code&&Object.hasOwn(inputs.records,code)?inputs.records[code]:null;if(src&&(src.state==='NOT_AVAILABLE'||src.identity_withdrawn===true)&&src.calc_version_mismatch!==true&&v2.total===null){v2.total_reason='SOURCE_NOT_AVAILABLE';v2.source_reason_codes=[...(src.na_reasons||[])];}
  if(blocked.has(code)){v2.v=null;v2.total=null;v2.state='NOT_AVAILABLE';v2.total_reason='PRICE_IDENTITY_CONFLICT';if(!v2.flags.includes('PRICE_IDENTITY_CONFLICT'))v2.flags.push('PRICE_IDENTITY_CONFLICT');}
  if(newer){v2.total_reason='DATA_FORMAT_NEWER';}
  const ref=object(referenceRows)?referenceRows[c.company_id]:null;if(ref?.reference_only===true&&object(ref.factors)&&object(ref.axes)){try{const factors={},qg_axes={};for(const axis of ['Q','G']){let coverage=0;for(const[f,w]of Object.entries(V2.WEIGHTS[axis])){const s=ref.factors[f];factors[f]=finite(s)&&s>=0&&s<=100?s:null;if(factors[f]!==null)coverage+=w;}qg_axes[axis]={score:coverage>=50&&finite(ref.axes[axis]?.score)?ref.axes[axis].score:null};}
   v2=v2Display(V2.scoreUniverse({reference:{profile:'GENERAL',industry_group:null,factors,qg_axes,v_inputs:null,memberships:null}}, {},{preset:chosen,gate:gateOn}).reference);v2.reference_only=true;v2.reference_label='참고 순위';v2.reference_label_en='Reference ranking';}catch(_){}}
  const row={company_id:c.company_id,ticker:c.ticker,code,v2,primary:v2,reference:null,rank:null};rows[c.company_id]=row;}
 ranked=Object.values(rows).filter(r=>finite(r.primary.total)&&r.primary.reference_only!==true).sort((a,b)=>b.primary.total-a.primary.total||(a.ticker<b.ticker?-1:1));
 ranked.forEach((r,i)=>{r.rank=i+1;});
 const quoted=object(quotes)?Object.keys(quotes).length:0;
 return{default:current,basis:b,label:LABEL[current],profile:{preset:chosen,gate:gateOn,id:V2.VERSION+'/'+chosen+'/gate-'+(gateOn?'on':'off'),name:V2.PRESETS[chosen],type_scope:b.type_scope},
  v2_state:v2Ready?'READY':'NOT_AVAILABLE',v2_reason:v2Reason,v2_reason_text:v2Reason==='SEC_QGV2_SCHEMA_NEWER'?NEWER_TEXT:null,v2_as_of:inputs?inputs.as_of:null,priced_codes:quoted,rows};
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
 const out={};if(!v2Inputs||!object(v2Inputs.records))return out;const codeFor=codeIndex(v2Inputs),tickers={},symbols=conflictedSymbols(v2Inputs);
 // No price is read for a stopped code (identity withdrawal) or a TARGET whose price symbol is in conflict (UNI-TARGET above).
 let universe=null;try{universe=win.PrivateSubsetView&&typeof win.PrivateSubsetView.prices==='function'?win.PrivateSubsetView.prices():null;}catch(_){universe=null;}
 const bySymbol=new Map();if(universe&&typeof universe.forEach==='function')universe.forEach((q,code)=>{if(!(q&&finite(q.price)&&q.price>0&&typeof q.currency==='string'))return;bySymbol.set(symbolOf(code),{price:q.price,currency:q.currency});if(Object.hasOwn(v2Inputs.records,code)&&v2Inputs.records[code]?.identity_withdrawn!==true)out[code]={price:q.price,currency:q.currency};});
 const dq=catalog&&win.DeviceValuation&&typeof win.DeviceValuation.deviceQuote==='function';
 for(const c of identities){const code=codeFor(c);if(!code||v2Inputs.records[code]?.identity_withdrawn===true||priceConflict(v2Inputs,c,code,symbols))continue;tickers[code]=c.ticker;if(Object.hasOwn(out,code))continue;if(bySymbol.has(key(c.ticker))){out[code]={...bySymbol.get(key(c.ticker))};continue;}if(!dq)continue;
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
const SOURCE_REASON={NOT_COLLECTED:['아직 수집 안 됨','not collected yet'],CIK_UNRESOLVED:['CIK 미해결','CIK unresolved'],NO_ANNUAL_SEC_FINANCIALS:['연간 SEC 재무 없음','no annual SEC financials'],INVALID_INPUT:['원자료 형식 오류','invalid source data'],NON_SEC_ISSUER:['SEC 공시 대상 아님','not an SEC filer'],IDENTITY_CONFLICT_WITHDRAWN:['식별 충돌로 사용 중지','withdrawn: identity conflict']};
const NEWER_TEXT=['자료 형식이 새 버전입니다. 새로고침하세요','The data format is newer. Reload the page'];
function naText(d,en){
 const head=en?'QGV v2 not available':'QGV v2 산출 불가';
 if(d&&d.total_reason==='DATA_FORMAT_NEWER')return head+' · '+NEWER_TEXT[en?1:0];
 if(d&&d.total_reason==='PRICE_IDENTITY_CONFLICT')return head+' · '+FLAG.PRICE_IDENTITY_CONFLICT[en?1:0];
 if(d&&d.total_reason==='SOURCE_NOT_AVAILABLE')return head+' · '+(en?'source data missing':'원자료 없음')+((d.source_reason_codes||[]).length?' ('+d.source_reason_codes.map(r=>SOURCE_REASON[r]?SOURCE_REASON[r][en?1:0]:r).join(', ')+')':'');
 if(d&&(d.flags||[]).includes('CALC_VERSION_MISMATCH'))return head+' · '+FLAG.CALC_VERSION_MISMATCH[en?1:0];
 if(!d||(d.flags||[]).includes('V2_INPUTS_NOT_AVAILABLE'))return head+' · '+(en?'no v2 input for this company':'이 기업의 v2 입력 없음');
 const parts=[head,(en?'calculated factors ':'산출 요인 ')+d.factors_available+'/'+d.factors_total];
 for(const a of ['Q','G','V']){const x=d.axes&&d.axes[a];if(x&&x.reason==='AXIS_WEIGHT_INSUFFICIENT')parts.push(a+(en?' axis below 50% of its weight':' 축 비중 50% 미만'));}
 if(d.total_reason==='AXIS_WEIGHT_INSUFFICIENT'&&parts.length===2)parts.push(en?'available axes below 50% of the weight':'산출 축 비중 50% 미만');
 return parts.join(' · ');
}
function label(version,en){return(LABEL[version]||LABEL.v2)[en?1:0];}
// Badge text of the basis: '점수 기준 v2 · PROVISIONAL · 기본' (+ ' · 2026-10-19부터' when the switch date is configured)
// (+ ' · 유형 범위 qgv2-type-scope/…' = the type-application scope id the scores use).
function basisText(S,en){const b=S&&S.basis?S.basis:basis('v2',false);return label('v2',en)+' · '+(en?b.label_en:b.label)+(b.since?(en?' · since ':' · ')+b.since+(en?'':'부터'):'')+(b.type_scope?(en?' · type scope ':' · 유형 범위 ')+b.type_scope:'');}
function presets(){return qgvV2().PRESETS;}
return Object.freeze({MODES,LABEL,FLAG,scoringDefault,compute,typeMemberships,judgmentRows,collectQuotes,summaryText,naText,flagText,label,basis,basisText,presets,symbolOf});
});
