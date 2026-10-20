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
 const api=factory(dep('qgv-v2.js','QgvV2'),dep('scoring-default.js','ScoringDefault'),dep('qgv2-inputs.js','Qgv2Inputs'),dep('sec-qgv2.js','SecQgv2'),dep('price-time.js','PriceTime'));
 if(node)module.exports=api;else root.QgvScores=api;})(typeof globalThis==='object'?globalThis:this,function(qgvV2,scoringConfig,qgv2Inputs,secQgv2,priceTime){
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
  axes:r.axes,factors:r.factors,weights:r.weights,profile:r.profile,q_industry_percentile:r.q_industry_percentile,v_excluded:r.v_excluded,detail:r.detail,reference_range:r.reference_range,selected_types:r.selected_types,type_reason:r.type_reason,value_trap_gate:r.value_trap_gate===true,...(r.weight_stages?{weight_stages:r.weight_stages}:{})};
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
/* Two memos: the official result (memo) and the PERSONAL_PREVIEW result of a two-level weight tree (personalMemo, owner
   directive 2026-10-18 §4.2). A personal result never overwrites or replaces the official one and is never `primary`. The
   personal result also carries the engine's read-only weight stages (QgvV2 weightStages: base / type-adjusted / applied, owner
   decision 2026-10-18 preset v0.1), passed through as rows[cid].personal.weight_stages; the official result never has them. */
let memo=null,personalMemo=null;
function universeScores(v2Inputs,quotes,preset,gate,cyclicalBasis={},personal=null){
 const mk=JSON.stringify(personal?['personal',personal.weights,personal.typeWeights,gate,cyclicalBasis]:[preset,gate,cyclicalBasis]),held=personal?personalMemo:memo;
 if(held&&held.inputs===v2Inputs&&held.quotes===quotes&&held.key===mk)return held.result;
 // A row of another calculation-rule version never joins this device's ranking population (QGV_V2_QG_METHOD.md 5, calc_version).
 // TYPE-SCOPE (owner instruction 2026-10-17): type memberships come from each row's own published price-free metrics with the
 // same approved rule (QgvV2.pricefreeMemberships), for every Universe code and TARGET row alike. TARGET membership no longer
 // decides who is typed (formerly only TARGET ids, via company-types-pricefree.json, got type weights).
 const companies={};for(const[code,r]of Object.entries(v2Inputs.records))if(r.calc_version_mismatch!==true)companies[code]={cyclical_basis:cyclicalBasis[code]===true,cik:r.cik,industry_group:r.industry_group,profile:r.profile,factors:r.factors,v_inputs:r.v_inputs,qg_axes:r.qg_axes,in_cross_section:r.in_cross_section!==false,memberships:rowMemberships(r)};
 const result=qgvV2().scoreUniverse(companies,quotes,personal?{gate,weights:personal.weights,typeWeights:personal.typeWeights,weightStages:true}:{preset,gate}),next={inputs:v2Inputs,quotes,key:mk,result};
 if(personal)personalMemo=next;else memo=next;return result;
}
// Label of every personal result (S06, S13): it is a preview of the user's own weights, never an official score.
const PERSONAL_LABEL=['개인 설정 미리보기 · 공식 점수 아님','Personal setting preview · not an official score'];
/* PROVENANCE (owner instruction 2026-10-19: '개인 프리셋 결과의 ‘공식’ 표시를 수정한다. 공식 가중치 사용 여부, 개인 설정 여부, 기기 가격
   사용 여부, 중앙 게시 결과 여부를 구분한다. 문구를 고치기 위해 계산 결과를 바꾸지 않는다.'; D11: a personal result says 개인). Four
   independent facts of one shown value, read only from the profile it was computed with. Labels only: nothing is computed here.
   weights  OFFICIAL = the official default profile (QgvV2.DEFAULT_PRESET, gate GATE_DEFAULT, official weights) | PERSONAL;
   setting  the personal choices behind the value: PRESET (another preset), GATE_OFF (gate toggled), WEIGHTS (personal weights);
   prices   DEVICE = this device's prices went in (every V needs them; PrivateSubsetView read, device quotes) | NONE;
   source   DEVICE_COMPUTED = computed on this device | PUBLISHED = read as published (sec-qgv2.json Q·G axes).
   There is no central V/QGV publication yet (design only), so a QGV total, rank or N set is always DEVICE_COMPUTED, also on the
   official weights. kind: 'QGV' (a total, rank, list or N set: axis weights and gate count), 'V' (the V axis alone: preset and
   gate do not change it, personal inner weights do), 'QG' (a published Q·G axis). */
const RANK_LABEL={OFFICIAL:['Universe 공식 QGV 순위','Official Universe QGV rank'],PERSONAL:['개인 프리셋 순위 (Universe 기준)','Personal preset rank (Universe basis)']};
function provenance({kind='QGV',profile=null,priced=false}={}){let V2=null;try{V2=qgvV2();}catch(_){V2=null;}const p=object(profile)?profile:{},qg=kind==='QG';
 const setting=qg?[]:p.preset==='custom'||object(p.weights)?['WEIGHTS']:kind==='V'?[]:[...(V2&&typeof p.preset==='string'&&p.preset!==V2.DEFAULT_PRESET?['PRESET']:[]),...(V2&&typeof p.gate==='boolean'&&p.gate!==V2.GATE_DEFAULT?['GATE_OFF']:[])];
 return Object.freeze({kind,weights:setting.length?'PERSONAL':'OFFICIAL',setting:Object.freeze(setting),prices:!qg&&priced===true?'DEVICE':'NONE',source:qg?'PUBLISHED':'DEVICE_COMPUTED',
  profile_id:!qg&&typeof p.id==='string'?p.id:null,preset:typeof p.preset==='string'?p.preset:null,gate:typeof p.gate==='boolean'?p.gate:null});}
// '공식 가중치 · 이 기기 가격 · 기기 계산' / '개인 프리셋(성장 친화) · 이 기기 가격 · 기기 계산' / '공식 가중치 · 가격 없음 · 중앙 게시(sec-qgv2.json)'.
function provenanceText(x,en){const V2=(()=>{try{return qgvV2();}catch(_){return null;}})(),pr=V2&&x.preset&&Object.hasOwn(V2.PRESETS,x.preset)?V2.PRESETS[x.preset]:null,off=x.setting.includes('GATE_OFF');
 const w=x.weights==='OFFICIAL'?(en?'Official weights':'공식 가중치'):x.setting.includes('WEIGHTS')?(en?'Personal weights':'개인 가중치'):(en?'Personal preset (':'개인 프리셋(')+(pr?(en?pr.name_en:pr.name):(x.preset||'—'))+(off?(en?' · gate off':' · 관문 끔'):'')+')';
 return [w,x.prices==='DEVICE'?(en?'this device’s prices':'이 기기 가격'):(en?'no prices':'가격 없음'),x.source==='PUBLISHED'?(en?'published centrally (sec-qgv2.json)':'중앙 게시(sec-qgv2.json)'):(en?'computed on this device':'기기 계산')].join(' · ');}
function provenanceAttrs(x){return{'data-qgv-weights':x.weights,'data-qgv-setting':x.setting.join(' ')||'NONE','data-qgv-prices':x.prices,'data-qgv-source':x.source,'data-qgv-profile':x.profile_id||''};}
// The same attributes as an HTML attribute string (screens built from strings); values are fixed codes and a profile id.
function provenanceAttrHtml(x){return Object.entries(provenanceAttrs(x)).map(([k,v])=>' '+k+'="'+String(v).replace(/[&"<>]/g,c=>({'&':'&amp;','"':'&quot;','<':'&lt;','>':'&gt;'})[c])+'"').join('');}
// Rank heading of a result computed with `profile`: 'Universe 공식 QGV 순위' only on the official default profile.
function rankLabel(profile,en){return RANK_LABEL[provenance({profile}).weights][en?1:0];}
/* FE-MISSING-2 (owner instruction 2026-10-17): why a company's QGV is partial or missing, read only from fields the public
   contract already carries (sec-qgv2.json row state/acquired_at/fiscal_year_end/profile/metrics, the published Q/G axis coverage,
   the engine's factor reasons and v_inputs). Display only: nothing here feeds a score, total, rank or candidate, and nothing is
   estimated. Weights are QgvV2.WEIGHTS (the engine's own), sub-metric lists SecQgv2.SUBMETRICS (the reader's own). Missing is
   null, never 0. No per-row field exists for 'refresh failed' (Universe) or 'unit under review', so neither is shown. */
const DATA_STATE={FORMAT_NEWER:['형식 업데이트 필요','Data format update needed'],IDENTITY_STOPPED:['식별 충돌로 사용 중지','Stopped: identity conflict'],CALC_VERSION:['계산 규칙 버전 다름','Different calculation-rule version'],
 SOURCE_MISSING:['자료 미확보','Data not collected'],STALE:['오래된 자료','Stale data'],PRICE_NEEDED:['가격 입력 필요','Price input needed'],PARTIAL:['일부 자료 부족','Some data missing'],NOT_APPLICABLE:['해당 없음','Not applicable']};
const AXIS_STATUS={READY:['정상','Complete'],PARTIAL:['부분 산출','Partial'],NOT_AVAILABLE:['미산출','Not calculated'],NOT_APPLICABLE:['해당 없음','Not applicable'],STOPPED:['사용 중지','Stopped']};
const REASON={
 NOT_APPLICABLE_PROFILE:['해당 없음: 금융업 기준에는 이 요인의 하위 지표가 정의되어 있지 않습니다','Not applicable: no sub-metric is defined for this factor under the financial profile'],
 SEC_ITEMS_MISSING:['자료 미확보: SEC 공시에서 이 요인의 하위 지표를 계산할 항목을 찾지 못했습니다','Not collected: the SEC filings lack the items for this factor’s sub-metrics'],
 PEERS_TOO_FEW:['비교 대상 부족: 하위 지표는 있으나 같은 기준으로 비교할 기업이 8곳 미만입니다','Too few peers: the sub-metric exists but fewer than 8 companies can be compared'],
 SEC_FACTOR_NOT_AVAILABLE:['자료 부족: 이 요인을 계산할 SEC 자료가 부족합니다','Missing: not enough SEC data for this factor'],
 PEERS_BELOW_MINIMUM:['비교 대상 부족: 이 축의 비교 기업이 8곳 미만이라 축 전체를 계산하지 않았습니다','Too few peers: fewer than 8 comparable companies for this axis'],
 AXIS_COVERAGE_BELOW_50:['원래 가중치 기준 충족률이 50% 미만이라 이 축을 계산하지 않았습니다','Below 50% of the original weight, so the axis is not calculated'],
 ROW_NOT_AVAILABLE:['자료 미확보: 이 기업의 SEC 재무 자료가 없습니다','Not collected: no SEC financials for this company'],
 SOURCE_NOT_AVAILABLE:['자료 미확보: 이 기업의 공개 입력이 없습니다','Not collected: no public input for this company'],
 CALC_VERSION_MISMATCH:['계산 규칙 버전이 달라 이 기기 계산에서 뺐습니다','Left out: different calculation-rule version'],
 IDENTITY_CONFLICT_WITHDRAWN:['식별 충돌로 사용 중지된 행이라 쓰지 않습니다','Stopped: identity conflict'],
 PRICE_IDENTITY_CONFLICT:['가격 식별 충돌로 가격·V를 쓰지 않습니다','Stopped: price identity conflict'],
 FINANCIAL_PROFILE_V_NOT_DEFINED:['현재 금융업 가치평가 모델 미지원','Valuation model for financials not supported yet'],
 NO_DEVICE_PRICE:['가격 입력 필요: 이 기기에 이 종목 가격이 없습니다','Price needed: no price for this company on this device'],
 PRICE_HISTORY_NOT_AVAILABLE:['가격 입력 필요: 이 기기 가격 탭에 월말 종가가 없습니다','Price needed: no month-end closes in this device’s Prices tab'],
 V_INPUTS_NOT_AVAILABLE:['자료 미확보: 가치 계산용 SEC 입력이 없습니다','Not collected: no SEC value inputs'],
 CURRENCY_BASIS_UNCONFIRMED:['통화 확인 필요: 보고 통화와 가격 통화가 다르거나 확인되지 않았습니다(환율 변환 없음)','Currency unconfirmed: reported and price currency differ (no FX conversion)'],
 SHARES_NOT_AVAILABLE:['자료 미확보: 희석 주식수가 없습니다','Not collected: no diluted share count'],
 DEBT_CASH_NOT_AVAILABLE:['자료 미확보: 부채 또는 현금 항목이 없습니다','Not collected: debt or cash is missing'],
 EV_NON_POSITIVE:['계산 불가: 기업가치(EV)가 0 이하입니다','Cannot calculate: enterprise value is not positive'],
 EBIT_NOT_AVAILABLE:['자료 미확보: EBIT가 없습니다','Not collected: no EBIT'],
 FCF_NOT_AVAILABLE:['자료 미확보: FCF가 없습니다','Not collected: no FCF'],
 REALIZED_GROWTH_NOT_AVAILABLE:['자료 미확보: 실현 매출 성장(3년)이 없습니다','Not collected: no realized 3-year revenue growth'],
 HISTORY_TOO_SHORT:['일부 자료 부족: 연도별 EBIT/주와 그 달 월말 종가가 함께 있는 해가 3개 미만입니다','Some data missing: fewer than 3 years with both EBIT/share and that month’s close'],
 NORMALIZED_HISTORY_NOT_AVAILABLE:['해당 없음: 정규화 이익 기준의 자기 과거 비교는 아직 정의되지 않았습니다','Not applicable: own-history comparison on normalized earnings is not defined yet'],
 NORMALIZED_EARNINGS_NOT_AVAILABLE:['일부 자료 부족: 정규화 이익(최근 매출 × 평균 영업이익률)에 필요한 연도가 부족합니다','Some data missing: not enough years for normalized earnings'],
 CROSS_SECTION_TOO_SMALL:['비교 대상 부족: 같은 값을 가진 비교 기업이 8곳 미만입니다','Too few peers: fewer than 8 comparable companies']};
// Missing-factor reason -> data state of the row ('PARTIAL' when not listed).
const CATEGORY={NOT_APPLICABLE_PROFILE:'NOT_APPLICABLE',FINANCIAL_PROFILE_V_NOT_DEFINED:'NOT_APPLICABLE',NORMALIZED_HISTORY_NOT_AVAILABLE:'NOT_APPLICABLE',NO_DEVICE_PRICE:'PRICE_NEEDED',PRICE_HISTORY_NOT_AVAILABLE:'PRICE_NEEDED',
 PRICE_IDENTITY_CONFLICT:'IDENTITY_STOPPED',IDENTITY_CONFLICT_WITHDRAWN:'IDENTITY_STOPPED',CALC_VERSION_MISMATCH:'CALC_VERSION',ROW_NOT_AVAILABLE:'SOURCE_MISSING',SOURCE_NOT_AVAILABLE:'SOURCE_MISSING'};
// Price-free V inputs a V factor needs (v_inputs of sec-qgv2.json), checked so that 'price needed' does not hide a missing input.
const V_INPUT={ebit:['EBIT','EBIT'],fcf:['FCF','FCF'],total_debt:['총부채','Total debt'],cash:['현금','Cash'],diluted_shares:['희석 주식수','Diluted shares'],ebit_per_share_history:['연도별 EBIT/주(3년 이상)','EBIT/share history (3+ years)'],revenue_cagr_3y:['3년 매출 성장','3-year revenue growth']};
function reasonText(code,en){return code&&Object.hasOwn(REASON,code)?REASON[code][en?1:0]:(en?'Not calculated':'계산 불가')+(code?' ('+code+')':'');}
function subMetrics(profile,factor){try{const t=secQgv2()?.SUBMETRICS;return t&&object(t[profile])&&Array.isArray(t[profile][factor])?t[profile][factor]:null;}catch(_){return null;}}
function qgReason(factor,rec,ctx,pub){
 if(ctx.withdrawn)return 'IDENTITY_CONFLICT_WITHDRAWN';if(ctx.mismatch)return 'CALC_VERSION_MISMATCH';if(!rec||rec.state==='NOT_AVAILABLE'||!ctx.profile)return 'SOURCE_NOT_AVAILABLE';
 const codes=pub&&Array.isArray(pub.reason_codes)?pub.reason_codes:[];for(const c of ['ROW_NOT_AVAILABLE','CALC_VERSION_MISMATCH','PEERS_BELOW_MINIMUM'])if(codes.includes(c))return c;
 const sub=subMetrics(ctx.profile,factor);if(!sub)return 'SEC_FACTOR_NOT_AVAILABLE';if(!sub.length)return 'NOT_APPLICABLE_PROFILE';
 return sub.some(m=>object(rec.metrics)&&finite(rec.metrics[m]))?'PEERS_TOO_FEW':'SEC_ITEMS_MISSING';}
function axisCoverage(axis,d,rec,ctx){
 // ctx.inner (PERSONAL_PREVIEW): the effective inner weights; 0 = excluded (not missing). Absent: the official weights, unchanged.
 const OW=qgvV2().WEIGHTS[axis],custom=ctx.inner&&object(ctx.inner[axis])?ctx.inner[axis]:null,W=custom||OW,pub=axis!=='V'&&rec&&object(rec.qg_axes)&&object(rec.qg_axes[axis])?rec.qg_axes[axis]:null,score=axis==='Q'?d.q:axis==='G'?d.g:d.v;
 const factors=Object.entries(W).map(([id,weight])=>{const x=d.factors&&object(d.factors[id])?d.factors[id]:null,s=x&&finite(x.score)?x.score:null;let reason=null;
  if(s===null){if(axis==='V'){reason=ctx.withdrawn?'IDENTITY_CONFLICT_WITHDRAWN':ctx.blocked?'PRICE_IDENTITY_CONFLICT':ctx.mismatch?'CALC_VERSION_MISMATCH':!rec||rec.state==='NOT_AVAILABLE'?'SOURCE_NOT_AVAILABLE':x&&x.reason?x.reason:'V_INPUTS_NOT_AVAILABLE';}else reason=qgReason(id,rec,ctx,pub);}
  const out={id,weight,score:s,reason,raw:x&&x.reason?x.reason:null,category:s===null?(CATEGORY[reason]||'PARTIAL'):'OK',basis:x&&x.basis?x.basis:null,metrics:axis!=='V'&&ctx.profile?[...(subMetrics(ctx.profile,id)||[])]:[]};
  if(custom){out.official_weight=OW[id];out.excluded=weight===0;}return out;});
 let total=0,used=0,n=0,na=0,officialUsed=0;for(const f of factors){if(custom&&f.score!==null)officialUsed+=f.official_weight;if(f.excluded)continue;total+=f.weight;if(f.score!==null){used+=f.weight;n++;}else if(f.category==='NOT_APPLICABLE')na++;}
 // Renormalized share inside the axis (the engine's Σ(w·s)/Σ(w available)), only when the axis itself has a score.
 for(const f of factors)f.share=score!==null&&f.score!==null&&used>0&&!f.excluded?100*f.weight/used:null;
 const lacking=factors.some(f=>f.score===null&&f.category!=='NOT_APPLICABLE'&&!f.excluded);
 const status=ctx.withdrawn||axis==='V'&&ctx.blocked?'STOPPED':axis==='V'&&ctx.profile==='FINANCIAL'?'NOT_APPLICABLE':score===null?'NOT_AVAILABLE':lacking?'PARTIAL':'READY';
 const codes=pub&&Array.isArray(pub.reason_codes)?[...pub.reason_codes]:[];let reason=null;
 if(status==='STOPPED')reason=ctx.withdrawn?'IDENTITY_CONFLICT_WITHDRAWN':'PRICE_IDENTITY_CONFLICT';else if(status==='NOT_APPLICABLE')reason='FINANCIAL_PROFILE_V_NOT_DEFINED';
 else if(status==='NOT_AVAILABLE'){const first=factors.find(f=>f.score===null&&!f.excluded)||factors.find(f=>f.score===null);reason=ctx.mismatch?'CALC_VERSION_MISMATCH':codes.find(c=>['ROW_NOT_AVAILABLE','PEERS_BELOW_MINIMUM','CALC_VERSION_MISMATCH'].includes(c))||(!rec||rec.state==='NOT_AVAILABLE'?'SOURCE_NOT_AVAILABLE':n&&used/total<qgvV2().MIN_AXIS_WEIGHT?'AXIS_COVERAGE_BELOW_50':factors.every(f=>f.reason===first.reason)?first.reason:'AXIS_COVERAGE_BELOW_50');}
 const inTotal=finite(d.total)&&score!==null&&!(axis==='V'&&d.v_excluded),use=inTotal?'INCLUDED':!finite(d.total)?'TOTAL_NOT_AVAILABLE':score===null?'AXIS_NOT_AVAILABLE':'VALUE_TRAP_GATE';
 const extra=custom?{weights:'PERSONAL',weight_available_official:officialUsed/100,excluded:factors.filter(f=>f.excluded).map(f=>f.id)}:{};
 return{axis,status,score,weight_available:total?used/total:null,factors_available:n,factors_total:custom?factors.filter(f=>!f.excluded).length:factors.length,not_applicable:na,reason,use,factors,...extra,
  published:pub?{factors_available:pub.factors_available??null,available_weight:pub.available_weight??null,peer_basis:pub.peer_basis??null,peer_count:pub.peer_count??null,submetric_fallbacks:pub.submetric_fallbacks??null,reason_codes:codes}:null};}
/* Display coverage of one v2 display row d and its source record rec (null when no record). Returns null for a reference-only
   row (no published record behind it). */
function coverageFor(d,rec,{blocked=false,inner=null}={}){
 if(!d||d.reference_only)return null;const withdrawn=!!rec&&rec.identity_withdrawn===true,mismatch=!!rec&&rec.calc_version_mismatch===true,profile=rec&&['GENERAL','FINANCIAL'].includes(rec.published_profile)?rec.published_profile:null;
 const ctx={withdrawn,mismatch,blocked,profile,inner},axes={};for(const a of ['Q','G','V'])axes[a]=axisCoverage(a,d,rec,ctx);
 const v=rec&&object(rec.v_inputs)?rec.v_inputs:null,missing=[];
 if(rec&&!withdrawn&&rec.state!=='NOT_AVAILABLE'&&profile!=='FINANCIAL'){if(!v)missing.push('v_inputs');else for(const k of Object.keys(V_INPUT)){const x=v[k];if(k==='ebit_per_share_history'?!(Array.isArray(x)&&x.length>=qgvV2().MIN_HISTORY):!finite(x))missing.push(k);}}
 const all=Object.values(axes).flatMap(a=>a.factors),has=c=>all.some(f=>f.category===c),states=[];
 if(d.total_reason==='DATA_FORMAT_NEWER')states.push('FORMAT_NEWER');if(withdrawn||blocked)states.push('IDENTITY_STOPPED');if(mismatch)states.push('CALC_VERSION');
 if(!withdrawn&&(!rec||rec.state==='NOT_AVAILABLE'))states.push('SOURCE_MISSING');if(rec&&rec.state==='STALE')states.push('STALE');
 if(!withdrawn&&!blocked&&has('PRICE_NEEDED'))states.push('PRICE_NEEDED');if(rec&&rec.state!=='NOT_AVAILABLE'&&!withdrawn&&(has('PARTIAL')||missing.length))states.push('PARTIAL');if(has('NOT_APPLICABLE'))states.push('NOT_APPLICABLE');
 return{axes,states,v_inputs_missing:missing,v_periods:rec&&object(rec.periods)?{...rec.periods}:{},
  source:{state:rec?rec.state:'NOT_AVAILABLE',acquired_at:rec&&typeof rec.acquired_at==='string'?rec.acquired_at:null,fiscal_year_end:rec&&typeof rec.fiscal_year_end==='string'?rec.fiscal_year_end:null,profile,reason_codes:rec&&Array.isArray(rec.na_reasons)?[...rec.na_reasons]:[]}};}
/* D11 (approved owner rule 'Q·G만 있는 결과를 QGV 종합순위와 섞지 않는다'): the official QGV ranking holds only rows whose V axis
   score is finite. A row with a total but no V (financial: V not defined; no device price; V inputs missing) keeps its engine
   total unchanged and goes to the 'QG 참고 목록 (V 미포함)': its own order by the same total, never an official rank. A
   value-trap-gate row computed V and the approved gate left V out of its total: it is not 'Q·G only' and stays ranked with its
   flag. Display only: no total, axis score or engine rule changes. Reference-only rows (DART 참고 순위) keep their own state.
   qgReference(d): {reason} (the V axis reason code of the row's coverage, else the engine's) for such a row, else null. */
const QG_REFERENCE_LABEL=['QG 참고 목록 (V 미포함)','Q·G reference list (V not included)'];
// D12 labels: the rank population and the separate lists (owner decision 2026-10-19).
const OUTSIDE_UNIVERSE_LABEL=['Universe 밖 TARGET · 공식 순위 대상 아님','TARGET outside the Universe · not in the official ranking'];
const PORTFOLIO_RANK_LABEL=['포트폴리오 내 순위','Rank within the portfolio'];
const POPULATION_LABEL=Object.freeze({EVALUATION:['평가 모집단','Evaluation population'],RANK:['순위 모집단','Rank population'],ELIGIBLE:['후보 자격','Candidate eligibility'],FILTER:['화면 필터','Screen filters']});
const NO_OFFICIAL_RANK=['가격 연결 전: 공식 QGV 순위 없음 · QG 참고 목록 보기','Before prices: no official QGV ranking · see the Q·G reference list'];
const PERSONAL_V0_LABEL=['개인 설정 결과 (V 비중 0) · 공식 순위 아님','Personal setting result (V weight 0) · not the official ranking'];
function qgReference(d){if(!d||d.reference_only===true||!finite(d.total)||finite(d.v))return null;const ax=d.coverage&&d.coverage.axes?d.coverage.axes.V:null,f=ax&&Array.isArray(ax.factors)?ax.factors.find(x=>x.score===null&&x.reason):null;
 return{reason:ax&&ax.reason?ax.reason:f?f.reason:d.factors&&d.factors.v_earnings_yield&&d.factors.v_earnings_yield.reason?d.factors.v_earnings_yield.reason:'V_INPUTS_NOT_AVAILABLE'};}
/* S06 exploration group of one computed row: RANKED (official QGV rank: a total with V), QG_REFERENCE (a total from Q·G only, in
   the QG 참고 목록, no official rank), PARTIAL_AXES (some axis score but no total: never in either order) or CHECK_DATA (no axis
   score). */
function exploreGroup(row){if(!row||!row.primary)return 'CHECK_DATA';if(row.rank!==null&&row.rank!==undefined)return 'RANKED';const p=row.primary;if(qgReference(p))return 'QG_REFERENCE';return [p.q,p.g,p.v].some(finite)?'PARTIAL_AXES':'CHECK_DATA';}
/* Cross-screen marks (owner 2026-10-19 'V 일치': the same input, version and settings show the same values and states on every
   screen; tools/v_cross_screen_consistency_browser_test.js). The values a screen shows for one row of a computed result and the
   Universe read that result was priced from, as data-cx-* attributes. Display only: nothing is computed, stored or sent, and no
   price, market cap or EV is named. read failure = the last failed re-read after the kept read (PrivateSubsetView.readStatus). */
function readMarks(basis,win){const b=object(basis)?basis:null;let f='';try{const s=win&&win.PrivateSubsetView&&typeof win.PrivateSubsetView.readStatus==='function'?win.PrivateSubsetView.readStatus():null;f=s&&s.failure&&typeof s.failure.code==='string'?s.failure.code:'';}catch(_){f='';}
 return{'data-cx-read-id':b&&typeof b.read_id==='string'?b.read_id:'','data-cx-read-at':b&&typeof b.acquired_at==='string'?b.acquired_at:'','data-cx-read-failure':f};}
function marks(row,basis,win){const p=row&&object(row.primary)?row.primary:null,ax=p&&object(p.coverage)&&object(p.coverage.axes)?p.coverage.axes.V:null,n=v=>finite(v)?String(v):'NA';
 return{'data-cx-v':n(p&&p.v),'data-cx-v-status':ax&&typeof ax.status==='string'?ax.status:'NA','data-cx-v-reason':ax&&typeof ax.reason==='string'?ax.reason:'','data-cx-total':n(p&&p.total),
  'data-cx-rank':row&&Number.isInteger(row.rank)?String(row.rank):'','data-cx-qg-order':row&&object(row.qg_reference)&&Number.isInteger(row.qg_reference.order)?String(row.qg_reference.order):'',
  'data-cx-group':row?exploreGroup(row):'NA','data-cx-scope':row&&row.outside_universe===true?'OUTSIDE_UNIVERSE':row&&typeof row.universe_code==='string'?'UNIVERSE':'NA',...readMarks(basis,win)};}
// The same marks as an HTML attribute string (screens built from strings).
function markAttrs(m){return Object.entries(object(m)?m:{}).map(([k,v])=>' '+k+'="'+String(v).replace(/[&"<>]/g,c=>({'&':'&amp;','"':'&quot;','<':'&lt;','>':'&gt;'})[c])+'"').join('');}
function stateText(code,en){return Object.hasOwn(DATA_STATE,code)?DATA_STATE[code][en?1:0]:code;}
function axisStatusText(code,en){return Object.hasOwn(AXIS_STATUS,code)?AXIS_STATUS[code][en?1:0]:code;}
function vInputText(key,en){return Object.hasOwn(V_INPUT,key)?V_INPUT[key][en?1:0]:(en?'value inputs':'가치 입력 전체');}
/* The accessor. identities: [{company_id, ticker}] rows to show; publicScreens: the app's loaded public screens (sec-qgv2.json
   under SecQgv2.FILE; type memberships come from its rows, company-types-pricefree.json is display-only); quotes:
   {code:{price,currency}} RAM. Returns rows with v2 (= primary). reference is always null: there is no comparison score on screens. */
/* weights (optional, PERSONAL_PREVIEW two-level tree {axis, inner}; typeWeights default true): also computes the personal
   result with its own memo and returns it under `personal` (top level: state, profile, label) and rows[cid].personal /
   personal_rank. `primary`, `v2`, `rank` and every other field stay the official result, byte-identical to a call without
   weights. An invalid tree gives personal.state 'INVALID' (reason WEIGHTS_INVALID) and no personal rows. */
/* official (optional, D12): the population split of universeIdentities() (the shared page result passes it). When given, only a
   row that stands for a Universe code of the file (official.universe[cid] !== null) can get an official rank or a QG 참고 목록 order;
   a TARGET outside the Universe keeps its score display but no rank or list place (outside_universe true), and every row carries
   universe_code. The result then has `official` (the counts of the four populations' first two; see universeIdentities). Without
   it the result is unchanged: every identity with a total is ranked (callers that score their own identities). */
function compute({identities=[],publicScreens={},v2Inputs,quotes={},preset,gate=null,referenceRows={},weights=null,typeWeights=true,official=null}={}){
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
 // One display row of universe u (official: extra {}; personal: the weight tree), with the same flags, stops and coverage.
 const display=(u,c,code,extra)=>{let v2=v2Display(u&&code?u[code]:null);const universe=u;if(universe&&code&&inputs.records[code]?.calc_version_mismatch===true){v2.flags=['CALC_VERSION_MISMATCH'];v2.reason='CALC_VERSION_MISMATCH';}if(universe&&code&&universe[code]&&ebitEstimated(inputs.records[code])){v2.flags.push('EBIT_ESTIMATED');const ys=inputs.records[code].metrics.ebit_estimated_fiscal_years;if(Array.isArray(ys))v2.ebit_estimated_fiscal_years=[...ys];}
  // identity_withdrawn (Qgv2Inputs): a TARGET issuer withdrawn for an identity conflict, its TARGET row and same-CIK Universe codes.
  const src=inputs&&code&&Object.hasOwn(inputs.records,code)?inputs.records[code]:null;if(src&&(src.state==='NOT_AVAILABLE'||src.identity_withdrawn===true)&&src.calc_version_mismatch!==true&&v2.total===null){v2.total_reason='SOURCE_NOT_AVAILABLE';v2.source_reason_codes=[...(src.na_reasons||[])];}
  if(blocked.has(code)){v2.v=null;v2.total=null;v2.state='NOT_AVAILABLE';v2.total_reason='PRICE_IDENTITY_CONFLICT';if(!v2.flags.includes('PRICE_IDENTITY_CONFLICT'))v2.flags.push('PRICE_IDENTITY_CONFLICT');}
  if(newer){v2.total_reason='DATA_FORMAT_NEWER';}
  // Personal weight stages (engine diagnostic): a total this accessor stops (price identity conflict) has no applied weights.
  if(v2.weight_stages&&v2.total===null&&v2.weight_stages.applied.state==='READY')v2.weight_stages={...v2.weight_stages,display_stop:v2.total_reason};
  const ref=object(referenceRows)?referenceRows[c.company_id]:null;if(ref?.reference_only===true&&object(ref.factors)&&object(ref.axes)){try{const factors={},qg_axes={};for(const axis of ['Q','G']){let coverage=0;for(const[f,w]of Object.entries(V2.WEIGHTS[axis])){const s=ref.factors[f];factors[f]=finite(s)&&s>=0&&s<=100?s:null;if(factors[f]!==null)coverage+=w;}qg_axes[axis]={score:coverage>=50&&finite(ref.axes[axis]?.score)?ref.axes[axis].score:null};}
   v2=v2Display(V2.scoreUniverse({reference:{profile:'GENERAL',industry_group:null,factors,qg_axes,v_inputs:null,memberships:null}}, {},{preset:chosen,gate:gateOn,...extra}).reference);v2.reference_only=true;v2.reference_label='참고 순위';v2.reference_label_en='Reference ranking';}catch(_){}}
  if(inputs&&!newer){try{v2.coverage=coverageFor(v2,src,extra.weights?{blocked:blocked.has(code),inner:extra.weights.inner}:{blocked:blocked.has(code)});}catch(_){v2.coverage=null;}}else if(newer)v2.coverage={axes:null,states:['FORMAT_NEWER'],v_inputs_missing:[],v_periods:{},source:null};
  return v2;};
 const U=object(official)&&object(official.universe)?official.universe:null,inRank=r=>!U||U[r.company_id]!==null&&U[r.company_id]!==undefined;
 for(const c of identities){const code=codeFor(c),v2=display(universe,c,code,{});
  const row={company_id:c.company_id,ticker:c.ticker,code,v2,primary:v2,reference:null,rank:null,qg_reference:null};if(U){row.universe_code=typeof U[c.company_id]==='string'?U[c.company_id]:null;row.outside_universe=row.universe_code===null;}rows[c.company_id]=row;}
 // D11: official rank = rows with a total AND a V score; Q·G-only totals get qg_reference {order, reason} in their own order.
 const byTotal=k=>(a,b)=>b[k].total-a[k].total||(a.ticker<b.ticker?-1:1),scored=Object.values(rows).filter(r=>finite(r.primary.total)&&r.primary.reference_only!==true&&inRank(r));
 ranked=scored.filter(r=>!qgReference(r.primary)).sort(byTotal('primary'));ranked.forEach((r,i)=>{r.rank=i+1;});
 scored.filter(r=>qgReference(r.primary)).sort(byTotal('primary')).forEach((r,i)=>{r.qg_reference={order:i+1,...qgReference(r.primary)};});
 // PERSONAL_PREVIEW: same identities, inputs, quotes, stops and tie rule; a separate memo, rows[cid].personal, never primary.
 let personal=null;if(weights!==null&&weights!==undefined){let tree=null;try{tree=V2.validateWeights(weights);}catch(_){tree=null;}const typesOn=typeWeights!==false;
  personal={state:'NOT_AVAILABLE',reason:null,label:PERSONAL_LABEL,profile:tree?{id:V2.VERSION+'/custom/'+V2.weightsId(tree,typesOn)+'/gate-'+(gateOn?'on':'off'),namespace:V2.PERSONAL_NAMESPACE,gate:gateOn,type_weights:typesOn,weights:tree}:null};
  // A tree with V axis weight 0 is a personal Q·G-only result: its own label, all its totals ranked as that personal result only.
  if(tree&&tree.axis.V===0){personal.v_weight_zero=true;personal.label=PERSONAL_V0_LABEL;}
  if(!tree){personal.state='INVALID';personal.reason='WEIGHTS_INVALID';}
  else{let pu=null;if(inputs){try{pu=universeScores(inputs,priced,chosen,gateOn,cyclicalBasis,{weights:tree,typeWeights:typesOn});}catch(_){pu=null;personal.reason='V2_CALCULATION_FAILED';}}else personal.reason=v2Reason;
   const extra={weights:tree,typeWeights:typesOn};for(const c of identities){const row=rows[c.company_id];row.personal=display(pu,c,row.code,extra);row.personal_rank=null;row.personal_qg_reference=null;}
   // Same D11 split for the personal result (V weight > 0); with V weight 0 every personal total is ranked under PERSONAL_V0_LABEL.
   const mine=Object.values(rows).filter(r=>finite(r.personal.total)&&r.personal.reference_only!==true&&inRank(r)),qgOnly=r=>!personal.v_weight_zero&&qgReference(r.personal);
   mine.filter(r=>!qgOnly(r)).sort(byTotal('personal')).forEach((r,i)=>{r.personal_rank=i+1;});mine.filter(qgOnly).sort(byTotal('personal')).forEach((r,i)=>{r.personal_qg_reference={order:i+1,...qgReference(r.personal)};});
   if(pu&&Object.values(pu).some(r=>finite(r.total)))personal.state='READY';else if(!personal.reason)personal.reason='V2_SCORES_NOT_AVAILABLE';}}
 const quoted=object(quotes)?Object.keys(quotes).length:0;
 // D12 counts of the official result (rank population = Universe rows with an official rank; the QG 참고 목록 apart).
 const off=U?{evaluated:Object.values(rows).filter(r=>r.universe_code!==null).length,codes:Number.isInteger(official.codes)?official.codes:null,ranked:Object.values(rows).filter(r=>Number.isInteger(r.rank)).length,qg_reference:Object.values(rows).filter(r=>r.qg_reference).length,
  target_in_universe:Array.isArray(official.target_in_universe)?official.target_in_universe.map(x=>({...x})):[],outside:Array.isArray(official.outside)?[...official.outside]:[],by_code:object(official.by_code)?{...official.by_code}:{}}:null;
 return{default:current,basis:b,label:LABEL[current],profile:{preset:chosen,gate:gateOn,id:V2.VERSION+'/'+chosen+'/gate-'+(gateOn?'on':'off'),name:V2.PRESETS[chosen],type_scope:b.type_scope},
  v2_state:v2Ready?'READY':'NOT_AVAILABLE',v2_reason:v2Reason,v2_reason_text:v2Reason==='SEC_QGV2_SCHEMA_NEWER'?NEWER_TEXT:null,v2_as_of:inputs?inputs.as_of:null,priced_codes:quoted,rows,...(off?{official:off}:{}),...(personal?{personal}:{})};
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
/* meta (optional {}): filled with {code:{source,as_of}} of each collected quote, so a screen can show the price's own time per
   source. The Universe tab (GOOGLEFINANCE) carries no trade time: as_of null = 미확인, never the read time. */
async function collectQuotes(win,{identities=[],v2Inputs=null,catalog=null,meta=null}={}){
 const out={};if(!v2Inputs||!object(v2Inputs.records))return out;const codeFor=codeIndex(v2Inputs),tickers={},symbols=conflictedSymbols(v2Inputs);
 // No price is read for a stopped code (identity withdrawal) or a TARGET whose price symbol is in conflict (UNI-TARGET above).
 let universe=null;try{universe=win.PrivateSubsetView&&typeof win.PrivateSubsetView.prices==='function'?win.PrivateSubsetView.prices():null;}catch(_){universe=null;}
 const bySymbol=new Map();if(universe&&typeof universe.forEach==='function')universe.forEach((q,code)=>{if(!(q&&finite(q.price)&&q.price>0&&typeof q.currency==='string'))return;bySymbol.set(symbolOf(code),{price:q.price,currency:q.currency});if(Object.hasOwn(v2Inputs.records,code)&&v2Inputs.records[code]?.identity_withdrawn!==true){out[code]={price:q.price,currency:q.currency};if(meta)meta[code]=UNIVERSE_META;}});
 const dq=catalog&&win.DeviceValuation&&typeof win.DeviceValuation.deviceQuote==='function';
 for(const c of identities){const code=codeFor(c);if(!code||v2Inputs.records[code]?.identity_withdrawn===true||priceConflict(v2Inputs,c,code,symbols))continue;tickers[code]=c.ticker;if(Object.hasOwn(out,code))continue;if(bySymbol.has(key(c.ticker))){out[code]={...bySymbol.get(key(c.ticker))};if(meta)meta[code]=UNIVERSE_META;continue;}if(!dq)continue;
  let q=null;try{q=await win.DeviceValuation.deviceQuote(win,catalog,c.ticker);}catch(_){q=null;}if(q&&finite(q.price)&&q.price>0){out[code]={price:q.price,currency:q.currency};if(meta)meta[code]=Object.freeze({source:typeof q.source==='string'?q.source:'DEVICE_QUOTE',as_of:typeof q.as_of==='string'?q.as_of:null,stale:q.stale===true?true:typeof q.as_of==='string'&&q.freshness!=='UNDETERMINED'?false:null});}}
 // v_vs_own_history: month-end closes of the user's sheet Prices tab (PriceStore device module, RAM). Absent -> the factor is
 // NOT_AVAILABLE (PRICE_HISTORY_NOT_AVAILABLE); never filled.
 const store=win.PriceStore&&typeof win.PriceStore.monthEndCloses==='function'?win.PriceStore:null;
 if(store)for(const code of Object.keys(out)){let m=null;try{m=await store.monthEndCloses(symbolOf(Object.hasOwn(tickers,code)?tickers[code]:code));}catch(_){m=null;}
  const clean={};if(object(m))for(const[k,v]of Object.entries(m))if(/^\d{4}-(0[1-9]|1[0-2])$/.test(k)&&finite(v)&&v>0)clean[k]=v;if(Object.keys(clean).length)out[code]={...out[code],month_closes:clean};}
 return out;
}
/* SHARED PAGE RESULT (owner decision 2026-10-18; V coverage panel + stat radar): ONE collectQuotes and ONE compute over every
   Universe code of the loaded file plus the given identities (the registered page identities when set), memoized by the inputs
   object, the Universe-read revision (PrivateSubsetView.priceBasis().read_id of the kept read, which survives navigation),
   catalog, identities and device inputs (one quote set), then by preset and gate (one compute each). Screens that show V values or V counts read
   this result so the same input gives the same V everywhere (V percentiles depend on which rows have prices). No new rule:
   the existing collectQuotes/compute calls. RAM only. Resolves {computed, quotes, quote_meta, price_basis, identities} or null. */
// D10: the Universe column has no price time, so its freshness is 판정 불가 (stale null), never 'not stale'.
const UNIVERSE_META=Object.freeze({source:'UNIVERSE_SHEET',as_of:null,stale:null});
/* PriceTime.summarize input for one quote_meta entry: as_of is the price's own time (ISO = CONFIRMED, YYYY-MM-DD = DATE_ONLY,
   null = UNCONFIRMED); stale is the source rule's verdict already made (true / false / null = 판정 불가). */
function metaTime(m){const t=typeof m.as_of==='string'?m.as_of:null,date=t!==null&&/^\d{4}-\d{2}-\d{2}$/.test(t);
 return{status:t===null?'UNCONFIRMED':date?'DATE_ONLY':'CONFIRMED',price_time:t!==null&&!date?t:null,price_date:date?t:null,read_at:null,stale:m.stale===true?true:m.stale===false&&t!==null?false:null,freshness:m.stale===true?'STALE':m.stale===false&&t!==null?'CURRENT':'UNDETERMINED'};}
let pageMemo=null,quoteMemo=null,pageIds=null,deviceEpoch=0;const watched=new WeakSet();
function readBasis(win){try{const b=win&&win.PrivateSubsetView&&typeof win.PrivateSubsetView.priceBasis==='function'?win.PrivateSubsetView.priceBasis():null;return object(b)?b:null;}catch(_){return null;}}
const cleanIds=list=>(Array.isArray(list)?list:[]).filter(c=>object(c)&&typeof c.company_id==='string'&&typeof c.ticker==='string').map(c=>({company_id:c.company_id,ticker:c.ticker}));
/* PAGE IDENTITIES (owner rule 2026-10-19: the same inputs give the same V on every screen). The app registers its S06 identities
   once; every pageResult then collects device quotes over that same set, whichever screen asks (S06, V panel, company detail,
   Universe page, stat radar), so one screen never prices a different cross-section. A caller's own identity is added only when it
   is not a Universe code of the file (Universe codes are priced from the shared Universe read like every other code). */
function setPageIdentities(list){pageIds=cleanIds(list);quoteMemo=null;pageMemo=null;}
/* PAGE PROFILE (owner rule 2026-10-19: same inputs AND settings -> same scores on every screen). The app registers a read-only
   getter of its current official preset/gate (S06 qgv2Profile, RAM only); pageResult, the radar, the Universe page and any caller
   that does not pass its own preset/gate read it here, so a preset or gate change on S06 reaches every screen. */
let profileOf=null,referencesOf=null;
function setPageProfile(getter){profileOf=typeof getter==='function'?getter:null;}
/* PAGE REFERENCES: the app's read-only getter of its reference-only rows (DART 참고 순위, {company_id: row}); the shared result shows
   them like S04/S06 always did. A reference row is never ranked (reference_only), so no official rank or V changes with it. */
function setPageReferences(getter){referencesOf=typeof getter==='function'?getter:null;}
function pageReferences(){let r=null;try{r=referencesOf?referencesOf():null;}catch(_){r=null;}return object(r)?r:{};}
function pageProfile(){let p=null;try{p=profileOf?profileOf():null;}catch(_){p=null;}return Object.freeze({preset:object(p)&&typeof p.preset==='string'?p.preset:null,gate:object(p)&&typeof p.gate==='boolean'?p.gate:null});}
// Device inputs of collectQuotes besides the Universe read: stored/Worker quotes ('device-actual-changed') and the price tabs'
// loaded rows (PriceStore status counts; never its read time, so a no-op sync does not change the key).
function deviceKey(win){if(win&&win.document&&typeof win.document.addEventListener==='function'&&!watched.has(win.document)){watched.add(win.document);try{win.document.addEventListener('device-actual-changed',()=>{deviceEpoch++;});}catch(_){}}
 let store=null;try{const st=win&&win.PriceStore&&typeof win.PriceStore.status==='function'?win.PriceStore.status():null;store=object(st)?[st.state,st.tabs||null,st.symbols||null]:null;}catch(_){store=null;}return[deviceEpoch,store];}
/* Is a pageResult held by a screen still the one for the current Universe read and the current official preset/gate? A screen
   that keeps a result between paints (the stat radar) shows it again only when this is true; otherwise it shows 확인하는 중 until
   the new result arrives, so a V of an older read or another setting is never shown as current. */
function isCurrent(win,result){if(!object(result)||!object(result.computed)||!object(result.computed.profile))return false;
 const id=b=>b?b.read_id||b.acquired_at||'READ':null;if(id(readBasis(win))!==id(object(result.price_basis)?result.price_basis:null))return false;
 let V2=null;try{V2=qgvV2();}catch(_){return false;}const P=pageProfile(),preset=P.preset&&Object.hasOwn(V2.PRESETS,P.preset)?P.preset:V2.DEFAULT_PRESET,gate=P.gate===null?V2.GATE_DEFAULT:P.gate;
 return result.computed.profile.preset===preset&&result.computed.profile.gate===gate;}
/* D12 (owner decision 2026-10-19: '공식 리더보드는 Universe 전체 평가를 기준으로 한다. 기존 TARGET 19개는 별도 목록·필터로
   유지한다.'). Four populations, kept apart by name in code and on screen:
   - EVALUATION: every security of the ONE shared result (pageResult): each Universe code of the published sec-qgv2.json once, plus
     each TARGET identity outside the Universe (scored and shown, never ranked);
   - RANK: the rows of that result standing for a Universe code with an official rank (a total WITH a V axis score, D11; value-trap
     gate rows stay ranked);
   - ELIGIBLE: the approved model-portfolio eligibility rules over the RANK population (modelPortfolios below);
   - FILTER: the screen filters (search, group, interest, TARGET) only hide rows and never re-rank.
   One security, one row (dedupe): a TARGET identity whose ticker is the symbol of a Universe code of the file IS that code (the
   identity mapping every score and price already uses: codeIndex, collectQuotes), so the code gets no second row; the TARGET row
   keeps its existing score source (its TARGET record when it has data, else the Universe code; an identity withdrawal stops both).
   A TARGET identity whose ticker matches no Universe code (e.g. TSE 8035, KRX 042700) is OUTSIDE: listed apart, never ranked.
   Returns {identities, universe:{cid: code|null}, by_code:{code: cid}, target_in_universe:[{company_id,code}], outside:[cid], codes}
   or null without a readable file. No score, weight or engine input changes: the engine cross-section is the file itself. */
function universeIdentities(v2Inputs,page=[]){
 if(!v2Inputs||!object(v2Inputs.records))return null;
 const codes=Object.keys(v2Inputs.records).filter(c=>!c.startsWith('TARGET:')).sort(),bySymbol=new Map();for(const c of codes)if(!bySymbol.has(symbolOf(c)))bySymbol.set(symbolOf(c),c);
 const identities=[],universe={},by_code={},target_in_universe=[],outside=[],seen=new Set();
 for(const c of cleanIds(page)){if(seen.has(c.company_id))continue;seen.add(c.company_id);const own=codes.includes(c.company_id),code=own?c.company_id:bySymbol.get(key(c.ticker))||null;
  if(code&&Object.hasOwn(by_code,code))continue;// the same security is already one row
  identities.push(c);universe[c.company_id]=code;if(code){by_code[code]=c.company_id;if(!own)target_in_universe.push({company_id:c.company_id,code});}else outside.push(c.company_id);}
 for(const code of codes)if(!Object.hasOwn(by_code,code)){by_code[code]=code;universe[code]=code;identities.push({company_id:code,ticker:symbolOf(code)});}
 return{identities,universe,by_code,target_in_universe,outside,codes:codes.length};}
/* The row of a computed result for an id: its own row, else the row that stands for that Universe code (D12 dedupe: e.g.
   'NASDAQ:NVDA' -> the TARGET row 'nvda'). null when neither exists. */
function rowOf(computed,id){if(!object(computed)||!object(computed.rows)||typeof id!=='string')return null;if(Object.hasOwn(computed.rows,id))return computed.rows[id];
 const o=object(computed.official)&&object(computed.official.by_code)?computed.official.by_code:null,cid=o&&Object.hasOwn(o,id)?o[id]:null;return cid&&Object.hasOwn(computed.rows,cid)?computed.rows[cid]:null;}
// The row standing for Universe code `code` (its own scored row, or the TARGET row merged into it); null otherwise.
function codeRow(computed,code){const r=rowOf(computed,code);return r&&(r.code===code||r.universe_code===code)?r:null;}
function pageResult(win,{v2Inputs,catalog=null,identities=[],preset,gate}={}){
 if(!v2Inputs||!object(v2Inputs.records))return Promise.resolve(null);
 // preset/gate not given (undefined): the registered official page profile (S06), else the engine defaults.
 {const P=pageProfile();if(preset===undefined)preset=P.preset;if(gate===undefined)gate=P.gate;}
 const basis=readBasis(win),given=cleanIds(identities),seen=new Set(),ids=[];
 for(const c of pageIds?[...pageIds,...given.filter(c=>c.company_id.startsWith('TARGET:')||!Object.hasOwn(v2Inputs.records,c.company_id))]:given)if(!seen.has(c.company_id)){seen.add(c.company_id);ids.push(c);}
 // ONE quote set per (inputs, catalog, Universe read, identities, device inputs); every preset/gate is computed over it.
 const qk=JSON.stringify([basis?basis.read_id||basis.acquired_at||'READ':null,ids,deviceKey(win)]);
 if(!(quoteMemo&&quoteMemo.inputs===v2Inputs&&quoteMemo.catalog===catalog&&quoteMemo.key===qk)){
  const q={inputs:v2Inputs,catalog,key:qk,promise:(async()=>{const quote_meta={},quotes=await collectQuotes(win,{identities:ids,v2Inputs,catalog,meta:quote_meta});return{quotes,quote_meta};})()};
  quoteMemo=q;q.promise.catch(()=>{if(quoteMemo===q)quoteMemo=null;});}
 const held=quoteMemo,refs=pageReferences(),k=JSON.stringify([preset,gate,refs]);
 if(pageMemo&&pageMemo.quotes===held&&pageMemo.key===k)return pageMemo.promise;
 // D12: the identities are deduplicated into the official populations (universeIdentities): one row per security.
 const promise=held.promise.then(({quotes,quote_meta})=>{const U=universeIdentities(v2Inputs,ids);
  return Object.freeze({computed:compute({identities:U.identities,v2Inputs,quotes,preset,gate,referenceRows:refs,official:U}),quotes,quote_meta,price_basis:basis,identities:U.identities,official:U,reference_key:JSON.stringify(refs)});});
 const memo={quotes:held,key:k,promise};pageMemo=memo;promise.catch(()=>{if(pageMemo===memo)pageMemo=null;});return promise;}
/* V coverage counts of one pageResult (the V coverage panel; owner 2026-10-18). Read only from the engine's rows: V = a finite
   axis score, reasons = coverageFor's V axis reason (+ the missing factors' own reasons), input-complete = coverageFor
   v_inputs_missing; no new required input. Financials (FINANCIAL_PROFILE_V_NOT_DEFINED) are their own population, never a
   shortage; the full basis keeps every code in its denominator. V numbers are null before a Universe read (connected false).
   target = ceil(GENERAL n × 0.9): an observation metric only, wired to nothing else. */
const V_TARGET_SHARE=0.9;
/* Per-source price time of the priced rows (PriceTime.summarize): rows, confirmed, unconfirmed, stale (stale===true only), from/to
   over confirmed price times/dates. Without PriceTime every row stays unconfirmed (never dated, never stale). */
function sourceTimes(source,list){let PT=null;try{PT=priceTime();}catch(_){PT=null;}
 if(PT&&typeof PT.summarize==='function'){const t=PT.summarize(list);return{source,rows:t.rows,confirmed:t.confirmed,unconfirmed:t.unconfirmed,stale:t.stale,from:t.from,to:t.to};}
 return{source,rows:list.length,confirmed:0,unconfirmed:list.length,stale:0,from:null,to:null};}
function vCoverage(result,v2Inputs){
 if(!object(result)||!object(result.computed)||!v2Inputs||!object(v2Inputs.records))return null;
 const rows=object(result.computed.rows)?result.computed.rows:{},Q=object(result.quotes)?result.quotes:{},M=object(result.quote_meta)?result.quote_meta:{},on=!!result.price_basis;
 const codes=Object.keys(v2Inputs.records).filter(c=>!c.startsWith('TARGET:')).sort(),bump=(m,k)=>{m[k]=(m[k]||0)+1;},list=m=>Object.entries(m).sort((a,b)=>b[1]-a[1]||(a[0]<b[0]?-1:1));
 const pop={total:codes.length,general:0,financial:0,unknown:0,stopped:0},v={full:0,general:0},qgv={full:0,general:0},qgOnly={full:0,general:0,financial:0,no_v:0,gate:0},reasons={},factorReasons={},unknownRows=[],times={};
 let complete=0,upper=0,priced=0,mismatch=0,shares=0,from=null,to=null,missingV=0;
 for(const code of codes){
  // D12: the row standing for the code (a TARGET company's code is its TARGET row) and the record + price that row was scored
  // from, so the panel counts the same evaluation as S06 and the company pages. A withdrawn code stays 'stopped'.
  const own=v2Inputs.records[code],row=codeRow(result.computed,code),src=row&&typeof row.code==='string'&&row.code!==code&&Object.hasOwn(v2Inputs.records,row.code)&&own.identity_withdrawn!==true?row.code:code;
  const rec=v2Inputs.records[src],p=row?row.primary:null,vi=object(rec.v_inputs)?rec.v_inputs:null,q=object(Q[src])&&finite(Q[src].price)&&Q[src].price>0?Q[src]:null;
  const cls=own.identity_withdrawn===true?'stopped':rec.published_profile==='GENERAL'?'general':rec.published_profile==='FINANCIAL'?'financial':'unknown',hasV=!!p&&finite(p.v),all=hasV&&finite(p.q)&&finite(p.g),gen=cls==='general';pop[cls]++;
  if(cls==='unknown')unknownRows.push({code,reasons:Array.isArray(rec.na_reasons)?[...rec.na_reasons]:[]});
  if(q){priced++;const m=object(M[src])?M[src]:UNIVERSE_META;(times[m.source]||(times[m.source]=[])).push(metaTime(m));}
  if(hasV){v.full++;if(gen)v.general++;}if(all){qgv.full++;if(gen)qgv.general++;}
  // A total without V in the row (the engine renormalizes over the available axes and ranks every finite total): counted, not
  // changed. full/general = financial + no price / V not computed. Value-trap-gate rows had V computed and the approved gate rule
  // excluded it from the total (kept in the official ranking): their own field `gate`, never in full/general.
  if(p&&finite(p.total)&&!hasV){qgOnly.full++;if(gen)qgOnly.general++;if(cls==='financial')qgOnly.financial++;else qgOnly.no_v++;}
  if(p&&finite(p.total)&&hasV&&p.v_excluded)qgOnly.gate++;
  if(!gen)continue;
  if(p&&p.coverage&&Array.isArray(p.coverage.v_inputs_missing)&&!p.coverage.v_inputs_missing.length)complete++;
  if(vi&&finite(vi.diluted_shares)&&vi.diluted_shares>0){shares++;if(finite(vi.ebit)||finite(vi.fcf))upper++;const pe=object(rec.periods)?rec.periods.diluted_shares:null;if(typeof pe==='string'){if(from===null||pe<from)from=pe;if(to===null||pe>to)to=pe;}}
  if(q&&vi&&q.currency!==vi.currency)mismatch++;
  if(!hasV){missingV++;const ax=p&&p.coverage&&p.coverage.axes?p.coverage.axes.V:null,seen=new Set();bump(reasons,ax&&ax.reason?ax.reason:p&&p.total_reason?p.total_reason:'V2_INPUTS_NOT_AVAILABLE');
   for(const f of ax&&Array.isArray(ax.factors)?ax.factors:[])if(f.score===null&&f.reason&&!seen.has(f.reason)){seen.add(f.reason);bump(factorReasons,f.reason);}}}
 const target=Math.ceil(V_TARGET_SHARE*pop.general-1e-9);
 return{connected:on,read_at:on&&typeof result.price_basis.acquired_at==='string'?result.price_basis.acquired_at:null,population:pop,applicable:pop.general,
  target:{share:V_TARGET_SHARE,n:target,observation_only:true,met:on?v.general>=target:null},v:on?v:null,qgv:on?qgv:null,qg_only_total:on?qgOnly:null,input_complete:complete,
  not_computed:on?missingV:null,reasons:on?list(reasons):null,factor_reasons:on?list(factorReasons):null,upper_bound:upper,priced:on?priced:null,currency_mismatch:on?mismatch:null,
  price_time:on?Object.entries(times).map(([source,list])=>sourceTimes(source,list)).sort((a,b)=>b.rows-a.rows||(a.source<b.source?-1:1)):null,shares:{rows:shares,period_from:from,period_to:to,rule:'V-SHARES-SCALE'},
  calc_version:typeof v2Inputs.calc_version==='string'?v2Inputs.calc_version:null,as_of:typeof v2Inputs.as_of==='string'?v2Inputs.as_of:null,unknown_rows:unknownRows};}
/* MODEL PORTFOLIO N10 / N15 / N20 (D12; owner decisions 2026-10-14 TARGET v1 (b)(c) and set B, backtest protocol 2026-10-18 'N15
   주검정과 N10·N20 민감도', CENTRAL_V_PUBLICATION_DESIGN §10-4; D-CV15: computed on this device in RAM, never stored or sent).
   Rule precedence and sources: docs/qgv_scoring_standard/N_SELECTION_RULES_20261019.md.
   Input: ONE official result (pageResult().computed with `official`). Approved eligibility, applied in this order over the RANK
   population in official rank order:
   OFFICIAL_RANK  an official rank (a total with V; D11), a Universe row (never a TARGET outside the Universe);
   AXES_50        Q, G and V axis scores all present (each axis needs 50% of its original weight; '축 50% 미만 제외');
   VALUE_TRAP_GATE the approved value-trap gate did not fire on the row ('가치 함정 관문 제외');
   FINANCIAL_SAFETY not below the safety line: net debt/EBITDA >= 3 or interest coverage < 3 excludes ('재무 안전 미달 제외'), read
                  from the published metrics of the record that scored the row;
   FINANCIAL_SAFETY_NA a row whose net debt/EBITDA or interest coverage is NA is excluded too (owner decision 2026-10-15: '재무 안전
                  지표가 NA인 회사는 후보에서 뺀다(핵심·일반 모두)'; QGV_V2_NUMBER_CHECK_20261017.md §3-2), with its own count;
   SUBGROUP_MAX_4 at most 4 per industry subgroup (approved #20 subgroups: PlaybookEngine.sectorFor on the symbol / SIC, no ETF
                  input here). PROVISIONAL (open, no approved rule): a row whose subgroup cannot be determined is not capped
                  (subgroup UNKNOWN, counted);
   LIMITS_16      PLAYBOOK_V1 §16 (TARGET v1 (c) '16절 한도'): single name <= 10%, sector group <= 40% with semiconductors and
                  semiconductor equipment as ONE group (portfolio_limits.combined_groups), at least 10 names. Per N at its equal
                  weight 100/N: a row whose group would pass 40% is skipped and the next eligible rank takes the seat (the same
                  replacement as the subgroup cap); a row of unknown group is not capped (same provisional rule) and makes the 40%
                  check UNVERIFIED when the unknown weight plus the largest known group could pass 40%. Never relaxed: when the
                  eligible rows run out the set stays short; its shortfall weight and causes are returned, never filled or
                  rescaled (owner decision 2026-10-15: '적격 후보가 모자라도 조건을 완화하거나 제외한 종목을 다시 넣지 않는다').
   modelPortfolios reads the result it is given; officialModel() below gives it the OFFICIAL DEFAULT profile (balanced, gate on,
   official weights) whatever preset the device shows on S06.
   Selection per N = the first eligible rows in official rank order under the caps above, equal weight 100/N (set B). Computed
   checks that never change the selection: `tier_check` (N15 only: the TARGET v1 / R-C core 5 x 8% + general 10 x 6% weights of
   2026-10-14 put on the N15 rows, §16 re-checked; R-C itself needs the 10-K check and card answers) and `issuer_check` (same
   issuer = same CIK across share classes, e.g. GOOG/GOOGL: the summed weight; one seat per issuer is a RECOMMENDATION that needs
   an owner decision, not applied). Every code keeps its own price, V, analysis, official rank and percentile treatment. Not
   applied (no approved mechanical rule): the 10-K number check (TARGET v1 confirmation step) and BT-14 '업종 분산' beyond the caps.
   Returns null without an official result. */
const MODEL_NS=Object.freeze([10,15,20]),MODEL_PRIMARY=15,SUBGROUP_MAX=4,SAFETY={net_debt_to_ebitda_min_fail:3,interest_coverage_below_fail:3},EPS=1e-9;
const MODEL_RULES=Object.freeze(['OFFICIAL_RANK','AXES_50','VALUE_TRAP_GATE','FINANCIAL_SAFETY','FINANCIAL_SAFETY_NA','SUBGROUP_MAX_4','LIMITS_16']);
const MODEL_LABEL=Object.freeze({OFFICIAL_RANK:['공식 QGV 순위 있음 (V 포함 · Universe)','Official QGV rank (with V · Universe)'],AXES_50:['Q·G·V 세 축 모두 산출 (축 50% 규칙)','Q, G and V all calculated (50% axis rule)'],
 VALUE_TRAP_GATE:['가치 함정 관문 행 제외','Value-trap gate rows excluded'],FINANCIAL_SAFETY:['재무 안전 미달 제외 (순부채/EBITDA ≥ 3 또는 이자보상 < 3)','Financial safety fails excluded (net debt/EBITDA ≥ 3 or interest coverage < 3)'],
 FINANCIAL_SAFETY_NA:['재무 안전 지표 NA 제외 (핵심·일반 모두)','Financial safety metric NA excluded (core and general)'],
 SUBGROUP_MAX_4:['업종 하위 묶음당 최대 4종목','At most 4 per industry subgroup'],
 LIMITS_16:['16절 한도 (단일 종목 10% · 업종 묶음 40%, 반도체+반도체 장비 한 묶음 · 최소 10종목)','§16 limits (single name 10% · sector group 40%, semiconductors + equipment one group · at least 10 names)']});
/* §16 values from the approved playbook config (PlaybookConfigDefaults.portfolio_limits, PLAYBOOK_V1 §16); the frozen copy below is
   the same §16 text for a page without the config (node test pins it equal to the config). */
const LIMITS_16=Object.freeze({single_max_pct:10,sector_group_max_pct:40,min_holdings:10,combined_groups:Object.freeze([Object.freeze({id:'semiconductor_combined',ko:'반도체 묶음',sectors:Object.freeze(['semiconductors','semi_equipment'])})])});
// TARGET v1 / R-C tiers (owner decision 2026-10-14, PLAYBOOK_V1 §18 T-PB over §15-2): 15 names, core = top 5 with calculated factors >= 80% and financial safety passed, x 8%; general 10 x 6%.
const TIERS_RC=Object.freeze({n:15,core_n:5,core_pct:8,general_pct:6,core_factors_min:0.8});
function limits16(){try{const C=globalThis.PlaybookConfigDefaults,l=C&&object(C.portfolio_limits)?C.portfolio_limits:null;
 if(l&&finite(l.single_max_pct)&&finite(l.sector_group_max_pct)&&Number.isInteger(l.min_holdings)&&Array.isArray(l.combined_groups))return l;}catch(_){}return LIMITS_16;}
function sectorName(id,en){if(id===null)return en?'unknown':'미정';const L=limits16(),g=L.combined_groups.find(x=>x.id===id);if(g)return en?id:g.ko;
 try{const C=globalThis.PlaybookConfigDefaults,s=C&&Array.isArray(C.sector_checks)?C.sector_checks.find(x=>x.id===id):null;if(s&&!en&&typeof s.name==='string')return s.name;}catch(_){}return id;}
function defaultSectorOf(ticker,sic){try{const E=globalThis.PlaybookEngine,C=globalThis.PlaybookConfigDefaults;const s=E&&C&&typeof E.sectorFor==='function'?E.sectorFor(C,ticker,null,sic):null;return s&&typeof s.sector==='string'?s.sector:null;}catch(_){return null;}}
/* §16 check of a weighted list [{weight_pct, group}] (group null = unknown). group.status: FAIL when a known group passes 40%,
   UNVERIFIED when unknown rows exist and unknown weight + the largest known group could pass 40% (their group is not defined by an
   approved rule), PASS otherwise. */
function limitCheck(list,L){const sums={},counts={};let unknownN=0,unknownPct=0,single=0,sum=0;
 for(const e of list){const w=e.weight_pct;single=Math.max(single,w);sum+=w;if(e.group===null){unknownN++;unknownPct+=w;continue;}sums[e.group]=(sums[e.group]||0)+w;counts[e.group]=(counts[e.group]||0)+1;}
 const max=L.sector_group_max_pct,groups=Object.keys(sums).sort().map(id=>({id,pct:sums[id],count:counts[id],over:sums[id]>max+EPS})),top=groups.reduce((a,g)=>Math.max(a,g.pct),0);
 const status=groups.some(g=>g.over)?'FAIL':unknownN&&top+unknownPct>max+EPS?'UNVERIFIED':'PASS';
 return{single:{limit:L.single_max_pct,max_pct:single,ok:single<=L.single_max_pct+EPS},group:{limit:max,status,groups,top_pct:top,unknown:{count:unknownN,pct:unknownPct}},
  min_holdings:{limit:L.min_holdings,count:list.length,ok:list.length>=L.min_holdings},sum_pct:sum};}
function pickN(entries,n,L){const w=100/n,sub={},grp={},sel=[],skipped={SUBGROUP_MAX_4:0,SECTOR_GROUP_MAX_40:0},capped=[];let examined=0;
 for(const e of entries){if(sel.length>=n)break;examined++;if(e.excluded)continue;
  if(e.subgroup!==null&&(sub[e.subgroup]||0)>=SUBGROUP_MAX){skipped.SUBGROUP_MAX_4++;continue;}
  if(e.group!==null&&(grp[e.group]||0)+w>L.sector_group_max_pct+EPS){skipped.SECTOR_GROUP_MAX_40++;capped.push({company_id:e.company_id,ticker:e.ticker,rank:e.rank,group:e.group});continue;}
  if(e.subgroup!==null)sub[e.subgroup]=(sub[e.subgroup]||0)+1;if(e.group!==null)grp[e.group]=(grp[e.group]||0)+w;sel.push({...e,weight_pct:w});}
 return{sel,skipped,capped,examined};}
function issuerCheck(list,L){const by=new Map();for(const e of list){const k=e.issuer||'code:'+e.code;if(!by.has(k))by.set(k,{issuer:e.issuer,codes:[],tickers:[],pct:0});const x=by.get(k);x.codes.push(e.code);x.tickers.push(e.ticker);x.pct+=e.weight_pct;}
 const all=[...by.values()],multi=all.filter(x=>x.codes.length>1).map(x=>({...x,over_single_max:x.pct>L.single_max_pct+EPS}));
 return{rule:'ISSUER_ONE_SEAT',status:'RECOMMENDATION_DECISION_NEEDED',applied:false,limit:L.single_max_pct,issuers:multi,max_issuer_pct:all.reduce((a,x)=>Math.max(a,x.pct),0)};}
function tierCheck(set,L){if(set.n!==TIERS_RC.n)return null;
 const rows=set.selected.map((e,i)=>{const core=i<TIERS_RC.core_n&&finite(e.factors_ratio)&&e.factors_ratio>=TIERS_RC.core_factors_min-EPS&&e.safety==='PASS';return{company_id:e.company_id,ticker:e.ticker,rank:e.rank,tier:core?'CORE':'GENERAL',weight_pct:core?TIERS_RC.core_pct:TIERS_RC.general_pct,group:e.group};});
 const core=rows.filter(r=>r.tier==='CORE').length,lim=limitCheck(rows,L),status=!set.complete?'INCOMPLETE':core!==TIERS_RC.core_n?'CORE_SHORT':lim.single.ok&&lim.group.status!=='FAIL'&&lim.min_holdings.ok&&Math.abs(lim.sum_pct-100)<EPS?(lim.group.status==='UNVERIFIED'?'UNVERIFIED':'PASS'):'FAIL';
 return{rule:'TIERS_RC_20261014',applied_to_selection:false,status,core,general:rows.length-core,rows,limits:lim};}
function modelPortfolios(computed,v2Inputs,{sectorOf=defaultSectorOf}={}){
 if(!object(computed)||!object(computed.rows)||!object(computed.official)||!v2Inputs||!object(v2Inputs.records))return null;
 const L=limits16(),combined={};for(const g of L.combined_groups)for(const s of g.sectors)combined[s]=g.id;
 const recs=v2Inputs.records,rows=Object.values(computed.rows).filter(r=>Number.isInteger(r.rank)&&typeof r.universe_code==='string').sort((a,b)=>a.rank-b.rank),entries=[];
 for(const r of rows){const p=r.primary,rec=Object.hasOwn(recs,r.code)?recs[r.code]:null,m=rec&&object(rec.metrics)?rec.metrics:{},nd=finite(m.net_debt_to_ebitda)?m.net_debt_to_ebitda:null,ic=finite(m.interest_coverage)?m.interest_coverage:null;
  const fail=nd!==null&&nd>=SAFETY.net_debt_to_ebitda_min_fail||ic!==null&&ic<SAFETY.interest_coverage_below_fail,safety=fail?'FAIL':nd!==null&&ic!==null?'PASS':'UNKNOWN';
  let sub=null;try{sub=typeof sectorOf==='function'?sectorOf(r.ticker,rec?rec.sic:null):null;}catch(_){sub=null;}if(typeof sub!=='string'||!sub)sub=null;
  let reason=null;if(![p.q,p.g,p.v].every(finite))reason='AXES_50';else if(p.value_trap_gate===true)reason='VALUE_TRAP_GATE';else if(fail)reason='FINANCIAL_SAFETY';else if(safety==='UNKNOWN')reason='FINANCIAL_SAFETY_NA';
  const fa=finite(p.factors_available)&&finite(p.factors_total)&&p.factors_total>0?p.factors_available/p.factors_total:null;
  entries.push({company_id:r.company_id,ticker:r.ticker,code:r.code,universe_code:r.universe_code,issuer:rec&&typeof rec.cik==='string'&&rec.cik?rec.cik:null,rank:r.rank,total:p.total,q:p.q,g:p.g,v:p.v,factors_ratio:fa,subgroup:sub,group:sub===null?null:combined[sub]||sub,safety,excluded:reason});}
 const sets={};let walk20=null;
 for(const n of MODEL_NS){const w=100/n,x=pickN(entries,n,L),lim=limitCheck(x.sel,L),complete=x.sel.length===n,causes=[];if(n===Math.max(...MODEL_NS))walk20=x;
  if(!complete){causes.push({code:'ELIGIBLE_EXHAUSTED',picked:x.sel.length,n});if(x.skipped.SECTOR_GROUP_MAX_40)causes.push({code:'SECTOR_GROUP_MAX_40',count:x.skipped.SECTOR_GROUP_MAX_40,groups:[...new Set(x.capped.map(c=>c.group))]});
   if(x.skipped.SUBGROUP_MAX_4)causes.push({code:'SUBGROUP_MAX_4',count:x.skipped.SUBGROUP_MAX_4});if(!lim.min_holdings.ok)causes.push({code:'MIN_HOLDINGS',count:x.sel.length,limit:L.min_holdings});}
  if(lim.group.status==='UNVERIFIED')causes.push({code:'GROUP_UNKNOWN',count:lim.group.unknown.count,pct:lim.group.unknown.pct});
  const status=!complete?'SHORTFALL':!lim.single.ok||lim.group.status==='FAIL'||!lim.min_holdings.ok?'FAIL':lim.group.status==='UNVERIFIED'?'UNVERIFIED':'FEASIBLE';
  sets['N'+n]={n,selected:x.sel,complete,weight_pct:w,status,shortfall_pct:(n-x.sel.length)*w,causes,skipped:x.skipped,group_capped:x.capped,limits:lim,issuer_check:issuerCheck(x.sel,L)};
  sets['N'+n].tier_check=tierCheck(sets['N'+n],L);}
 // Exclusion counts over the rows the N20 walk examined (as before): the base eligibility reasons + the subgroup cap of that walk.
 const excluded={AXES_50:0,VALUE_TRAP_GATE:0,FINANCIAL_SAFETY:0,FINANCIAL_SAFETY_NA:0,SUBGROUP_MAX_4:walk20.skipped.SUBGROUP_MAX_4},unknown={subgroup:walk20.sel.filter(e=>e.subgroup===null).length};
 for(const e of entries.slice(0,walk20.examined))if(e.excluded)excluded[e.excluded]++;
 return{version:'model-portfolio/v2',provisional:['SUBGROUP_UNKNOWN_NOT_CAPPED'],primary:'N'+MODEL_PRIMARY,ns:[...MODEL_NS],rules:[...MODEL_RULES],limits:{single_max_pct:L.single_max_pct,sector_group_max_pct:L.sector_group_max_pct,min_holdings:L.min_holdings,combined_groups:L.combined_groups.map(g=>({id:g.id,sectors:[...g.sectors]}))},
  sets,excluded,unknown,checked:walk20.examined,ranked:rows.length,profile_id:object(computed.profile)?computed.profile.id:null,as_of:computed.v2_as_of||null,weighting:'EQUAL'};}
/* The model portfolio on the OFFICIAL evaluation (owner instruction: 'N10/N15/N20 selection uses the official evaluation and the
   approved eligibility rules'): the same identities, inputs and quotes as the shared result, scored with the official default
   profile (QgvV2.DEFAULT_PRESET, gate on, official weights) whatever preset/gate the device shows on S06. `computed` (optional) is
   reused when it already is that profile. Own memo (inputs, quotes, official split). RAM only. Returns modelPortfolios(...) plus
   profile {preset, gate, id} or null. */
let officialModelMemo=null;
function officialModel({identities,v2Inputs,quotes={},official,computed=null}={}){
 if(!v2Inputs||!object(v2Inputs.records)||!object(official)||!Array.isArray(identities))return null;const V2=qgvV2(),preset=V2.DEFAULT_PRESET,gate=true;
 const m=officialModelMemo;if(m&&m.inputs===v2Inputs&&m.quotes===quotes&&m.official===official)return m.value;
 const own=object(computed)&&object(computed.official)&&object(computed.profile)&&computed.profile.preset===preset&&computed.profile.gate===gate;
 const S=own?computed:compute({identities,v2Inputs,quotes,preset,gate,official}),M=modelPortfolios(S,v2Inputs);
 const value=M?Object.freeze({...M,official_profile:Object.freeze({preset,gate,id:S.profile.id})}):null;officialModelMemo={inputs:v2Inputs,quotes,official,value};return value;}
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
 const parts=[head,(en?'calculated factors ':'산출 요인 ')+d.factors_available+'/'+d.factors_total];let below=false;
 // Q/G come from the published file: its axis reason (coverage below 50%, too few peers) is used when the axis is not published.
 for(const a of ['Q','G','V']){const x=d.axes&&d.axes[a],c=d.coverage&&d.coverage.axes?d.coverage.axes[a]:null,pub=c&&c.published?c.published.reason_codes:[];if(!x)continue;
  if(a==='V'&&c&&x.score===null&&c.status==='STOPPED')continue;
  if(a==='V'&&c&&x.score===null&&c.status==='NOT_APPLICABLE'){parts.push(en?'V: valuation model for financials not supported yet':'V '+REASON.FINANCIAL_PROFILE_V_NOT_DEFINED[0]);continue;}
  if(a==='V'&&c&&x.score===null&&c.factors.every(f=>f.category==='PRICE_NEEDED')){parts.push(en?'V needs a price input':'V 가격 입력 필요');continue;}
  if(x.reason==='AXIS_WEIGHT_INSUFFICIENT'||x.reason==='AXIS_NOT_PUBLISHED'&&pub.includes('AXIS_COVERAGE_BELOW_50')){below=true;parts.push(a+(en?' axis below 50% of its weight':' 축 비중 50% 미만'));}
  else if(x.reason==='AXIS_NOT_PUBLISHED'&&pub.includes('PEERS_BELOW_MINIMUM'))parts.push(a+(en?' axis: fewer than 8 peers':' 축 비교 기업 8곳 미만'));}
 if(d.total_reason==='AXIS_WEIGHT_INSUFFICIENT'&&!below)parts.push(en?'available axes below 50% of the weight':'산출 축 비중 50% 미만');
 return parts.join(' · ');
}
function label(version,en){return(LABEL[version]||LABEL.v2)[en?1:0];}
// Badge text of the basis: '점수 기준 v2 · PROVISIONAL · 기본' (+ ' · 2026-10-19부터' when the switch date is configured)
// (+ ' · 유형 범위 qgv2-type-scope/…' = the type-application scope id the scores use).
function basisText(S,en){const b=S&&S.basis?S.basis:basis('v2',false);return label('v2',en)+' · '+(en?b.label_en:b.label)+(b.since?(en?' · since ':' · ')+b.since+(en?'':'부터'):'')+(b.type_scope?(en?' · type scope ':' · 유형 범위 ')+b.type_scope:'');}
function presets(){return qgvV2().PRESETS;}
return Object.freeze({RANK_LABEL,provenance,provenanceText,provenanceAttrs,provenanceAttrHtml,rankLabel,OUTSIDE_UNIVERSE_LABEL,PORTFOLIO_RANK_LABEL,POPULATION_LABEL,universeIdentities,rowOf,codeRow,setPageReferences,modelPortfolios,officialModel,MODEL_NS,MODEL_PRIMARY,MODEL_RULES,MODEL_LABEL,MODES,LABEL,PERSONAL_LABEL,PERSONAL_V0_LABEL,QG_REFERENCE_LABEL,NO_OFFICIAL_RANK,qgReference,FLAG,DATA_STATE,AXIS_STATUS,REASON,coverageFor,exploreGroup,reasonText,stateText,axisStatusText,vInputText,scoringDefault,compute,typeMemberships,judgmentRows,collectQuotes,pageResult,setPageIdentities,setPageProfile,pageProfile,isCurrent,vCoverage,V_TARGET_SHARE,summaryText,naText,flagText,label,basis,basisText,presets,symbolOf,LIMITS_16,TIERS_RC,limits16,sectorName,pageReferences,marks,readMarks,markAttrs});
});
