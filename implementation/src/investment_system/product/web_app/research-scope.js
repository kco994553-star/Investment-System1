/* Research scope reader (IS2.researchScope; owner 2026-11-04 third, item 4). Two Codex research outputs, read as they are; the
   calculation is Codex's (DC-42), this file only checks, reads and words them. validateCoverage / coverageView / validateSelection /
   selectionView are pure and run in node as in the page.
   - Coverage: operational-qgv-coverage/1 (#474 572f0b5e, research/operational_coverage.py and
     the coverage contract doc OPERATIONAL_COVERAGE_CONTRACT_20261104.md). One dated operational publication; the denominator is that publication's
     non-TARGET code rows (the operational Universe504 codes), not fixed security ids and not a historical whole market. Q, G and V,
     all three axes at once, each preset total (derived from the archived axes, never a stored or PIT total) and the published
     default total are separate counts and never share a label. NOT_APPLICABLE stays apart from missing. A preset left null by the
     file (engine version mismatch, type weights not linked) is shown as not computed with its reason, never as 0.
   - Selection: the general research result of validation.vertical_slice (#473 f14262a6): selection_policy null | {mode all, value
     null} | {mode top_n, value int > 0} | {mode top_percent, value 0 < v ≤ 100}, n_eligible, n_selected, selected, weights (equal, or
     null when nothing is selected). n_selected must follow Codex's rule (all; min(n, N); floor(n × p / 100)). Only these fields are
     read: outcomes and realised returns in the same result are never read or shown. The official model (N15 tiers, TARGET rules)
     is a different path and does not follow this policy; the words say so.
   - The first fault refuses the whole input ({ok:false, code, path}); nothing is repaired or filled. Results are private research:
     source() is NONE (no request) until a private connection is approved. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else{const I=root.IS2=root.IS2||{};I.researchScope=api;}})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
const COVERAGE_SCHEMA='operational-qgv-coverage/1';
const UNIVERSE_N=504;
const FACTORS=Object.freeze(['q_profitability','q_moat_proxy','q_earnings_quality','q_financial_safety','q_capital_allocation','g_revenue_growth','g_per_share_growth',
 'g_growth_efficiency','g_consistency','g_recent_acceleration','v_earnings_yield','v_fcf_yield','v_vs_industry','v_vs_own_history','v_expectation_check']);
const AXES=Object.freeze(['Q','G','V']);
const PRESETS=Object.freeze(['balanced','quality','growth','value','user-preset/aggressive@0.1','user-preset/balanced@0.1','user-preset/defensive@0.1']);
const CATEGORIES=Object.freeze(['NOT_APPLICABLE','INPUT_MISMATCH','INPUT_NOT_LINKED','BASIS_UNCONFIRMED','REPORTED_MISSING_INPUT_OR_RULE']);
const TOP=Object.freeze(['all_axes','axes','calc_version','denominator','engine_matches','factors','historical_whole_market_coverage','membership_codes','pit_reason','presets',
 'publication_id','published_default_total','raw_input_connection_audit','raw_input_reason','result_kind','schema_version','scope','signal_date_pit_eligible','source_inputs',
 'source_sha256','times']);
const DEN=Object.freeze(['count','cross_section_rows','kind','missing_cik_rows','published_rows','security_identity_reason','target_rows_excluded','unique_code_strings',
 'unique_issuer_ciks','unique_securities']);
const MEASURE=Object.freeze(['denominator','missing','not_applicable','reason_categories','reasons','valid']);
const PRESET=Object.freeze(['basis','denominator','known_valid','reasons','unknown','valid']);
const MODES=Object.freeze(['all','top_n','top_percent']);
const AXIS_LABEL=Object.freeze({Q:'Q 축',G:'G 축',V:'V 축'});
const PRESET_LABEL=Object.freeze({balanced:'균형','quality':'품질',growth:'성장',value:'가치','user-preset/aggressive@0.1':'공격형','user-preset/balanced@0.1':'균형형','user-preset/defensive@0.1':'방어형'});
const FACTOR_LABEL=Object.freeze({q_profitability:'수익성',q_moat_proxy:'해자 대리',q_earnings_quality:'이익의 질',q_financial_safety:'재무 안전',q_capital_allocation:'자본 배분',
 g_revenue_growth:'매출 성장',g_per_share_growth:'주당 성장',g_growth_efficiency:'성장 효율',g_consistency:'성장 일관성',g_recent_acceleration:'최근 가속',
 v_earnings_yield:'이익 수익률',v_fcf_yield:'FCF 수익률',v_vs_industry:'업종 대비',v_vs_own_history:'자기 과거 대비',v_expectation_check:'기대 점검'});
const REASON=Object.freeze({ENGINE_VERSION_MISMATCH:'엔진 버전이 게시본과 달라 프리셋 가능 여부를 다시 계산하지 않음',TYPE_WEIGHTS_NOT_LINKED:'유형 가중치가 연결되지 않음',
 CALC_VERSION_MISMATCH:'계산 버전 불일치',PRICE_IDENTITY_CONFLICT:'가격 신원 충돌',AXIS_WEIGHT_INSUFFICIENT:'계산된 축 비중이 기준(50%)에 못 미침',
 FINANCIAL_PROFILE_V_NOT_DEFINED:'금융 업종이라 이 V 팩터는 정의되지 않음(해당 없음)'});
const CATEGORY_LABEL=Object.freeze({NOT_APPLICABLE:'해당 없음',INPUT_MISMATCH:'입력 불일치',INPUT_NOT_LINKED:'입력 미연결',BASIS_UNCONFIRMED:'기준 미확인',REPORTED_MISSING_INPUT_OR_RULE:'게시본에 결손으로 기록'});
const TEXT=Object.freeze({
 NONE:'연결된 연구 결과 없음 · 비공개 연구 결과는 공개 승인 전에는 이 화면에 잇지 않습니다',
 SCOPE:'선택한 운영 게시본 하나 기준 · 과거 전체 시장 커버리지 아님 · 신호일 기준 시점 검증 안 됨',
 PRESET_BASIS:'보관된 축 점수에서 도출한 계산 가능 수 · 저장된 프리셋 총점이나 과거 시점 재구성이 아님',
 OFFICIAL:'공식 모델은 기존 N15 구간·TARGET 규칙 그대로 · 이 선정 방식을 따르지 않음',
 GENERAL:'일반 연구(임시) 선정 · 조건 = Q·G 계산됨 · 같은 비중'});

const own=(o,k)=>Object.prototype.hasOwnProperty.call(o,k);
const isObj=v=>!!v&&typeof v==='object'&&!Array.isArray(v);
const isInt=v=>Number.isInteger(v)&&v>=0;
class Refusal extends Error{constructor(code,path){super(code+' '+path);this.code=code;this.path=path;}}
const refuse=(code,path)=>{throw new Refusal(code,path);};
function keys(o,want,at,{optional=[]}={}){if(!isObj(o))refuse('TYPE',at);
 for(const k of Object.keys(o))if(!want.includes(k)&&!optional.includes(k))refuse('KEY_UNKNOWN',at+'.'+k);
 for(const k of want)if(!own(o,k))refuse('KEY_MISSING',at+'.'+k);}
const int=(v,at)=>{if(!isInt(v))refuse('COUNT_INVALID',at);return v;};
const intOrNull=(v,at)=>(v===null?null:int(v,at));
const str=(v,at)=>{if(typeof v!=='string'||!v||v.length>200)refuse('TYPE',at);return v;};
const sum=o=>Object.values(o).reduce((a,b)=>a+b,0);
// A counter key that is absent counted zero times (a count, not a missing value).
const times=(o,k)=>(own(o,k)?o[k]:0);
function counter(o,at,allowed){if(!isObj(o))refuse('TYPE',at);for(const[k,v]of Object.entries(o)){if(allowed&&!allowed.includes(k))refuse('ENUM',at+'.'+k);
 if(!/^[A-Z][A-Z0-9_]{1,63}$/.test(k))refuse('REASON_INVALID',at+'.'+k);if(!isInt(v)||v===0)refuse('COUNT_INVALID',at+'.'+k);}return o;}
function measure(m,at,n){keys(m,MEASURE,at);const d=int(m.denominator,at+'.denominator'),v=int(m.valid,at+'.valid'),miss=int(m.missing,at+'.missing'),
 na=int(m.not_applicable,at+'.not_applicable');
 if(d!==n)refuse('DENOMINATOR_MISMATCH',at+'.denominator');if(v>d)refuse('COUNT_RANGE',at+'.valid');
 if(miss!==d-v)refuse('COUNT_MISMATCH',at+'.missing');if(na>miss)refuse('COUNT_RANGE',at+'.not_applicable');
 counter(m.reasons,at+'.reasons');counter(m.reason_categories,at+'.reason_categories',CATEGORIES);
 if(sum(m.reasons)!==miss)refuse('COUNT_MISMATCH',at+'.reasons');if(sum(m.reason_categories)!==miss)refuse('COUNT_MISMATCH',at+'.reason_categories');
 if(times(m.reason_categories,'NOT_APPLICABLE')!==na)refuse('COUNT_MISMATCH',at+'.reason_categories.NOT_APPLICABLE');
 if(times(m.reasons,'FINANCIAL_PROFILE_V_NOT_DEFINED')!==na)refuse('COUNT_MISMATCH',at+'.reasons.FINANCIAL_PROFILE_V_NOT_DEFINED');}
function freeze(o){if(o&&typeof o==='object'){Object.freeze(o);for(const v of Object.values(o))freeze(v);}return o;}

/* operational-qgv-coverage/1 → {ok:true, value} | {ok:false, code, path}. The value is a frozen copy of the file. */
function validateCoverage(json){
 try{
  const c=JSON.parse(JSON.stringify(json)),at='$';keys(c,TOP,at);
  if(c.schema_version!==COVERAGE_SCHEMA)refuse('SCHEMA_VERSION',at+'.schema_version');
  if(c.result_kind!=='OPERATIONAL_COVERAGE')refuse('ENUM',at+'.result_kind');
  if(c.scope!=='SELECTED_OPERATIONAL_PUBLICATION_ONLY')refuse('ENUM',at+'.scope');
  str(c.publication_id,at+'.publication_id');str(c.calc_version,at+'.calc_version');
  if(typeof c.source_sha256!=='string'||!/^[0-9a-f]{64}$/.test(c.source_sha256))refuse('SHA_INVALID',at+'.source_sha256');
  if(typeof c.engine_matches!=='boolean')refuse('TYPE',at+'.engine_matches');
  if(!isObj(c.times))refuse('TYPE',at+'.times');for(const[k,v]of Object.entries(c.times))if(v!==null&&typeof v!=='string')refuse('TYPE',at+'.times.'+k);
  if(!Array.isArray(c.source_inputs)||c.source_inputs.some(x=>!isObj(x)))refuse('TYPE',at+'.source_inputs');
  if(c.historical_whole_market_coverage!==null)refuse('WHOLE_MARKET_NOT_ALLOWED',at+'.historical_whole_market_coverage');
  if(c.signal_date_pit_eligible!==null&&typeof c.signal_date_pit_eligible!=='boolean')refuse('TYPE',at+'.signal_date_pit_eligible');
  if(c.raw_input_connection_audit!==null&&!isObj(c.raw_input_connection_audit))refuse('TYPE',at+'.raw_input_connection_audit');
  for(const k of['pit_reason','raw_input_reason'])if(c[k]!==null)str(c[k],at+'.'+k);
  const d=c.denominator,da=at+'.denominator';keys(d,DEN,da);
  if(d.kind!=='DATED_OPERATIONAL_UNIVERSE_CODES')refuse('ENUM',da+'.kind');
  const n=int(d.count,da+'.count');int(d.target_rows_excluded,da+'.target_rows_excluded');
  if(int(d.published_rows,da+'.published_rows')!==n+d.target_rows_excluded)refuse('COUNT_MISMATCH',da+'.published_rows');
  if(int(d.unique_code_strings,da+'.unique_code_strings')!==n)refuse('COUNT_MISMATCH',da+'.unique_code_strings');
  if(d.unique_securities!==null)refuse('SECURITY_ID_NOT_ALLOWED',da+'.unique_securities');str(d.security_identity_reason,da+'.security_identity_reason');
  const mc=int(d.missing_cik_rows,da+'.missing_cik_rows');if(mc>n)refuse('COUNT_RANGE',da+'.missing_cik_rows');
  if(mc>0?d.unique_issuer_ciks!==null:(intOrNull(d.unique_issuer_ciks,da+'.unique_issuer_ciks')===null||d.unique_issuer_ciks>n))refuse('COUNT_MISMATCH',da+'.unique_issuer_ciks');
  if(int(d.cross_section_rows,da+'.cross_section_rows')>n)refuse('COUNT_RANGE',da+'.cross_section_rows');
  const codes=c.membership_codes;if(!Array.isArray(codes)||codes.length!==n)refuse('COUNT_MISMATCH',at+'.membership_codes');
  const seen=new Set();codes.forEach((x,i)=>{if(typeof x!=='string'||!x||x.startsWith('TARGET:'))refuse('CODE_INVALID',at+'.membership_codes['+i+']');
   if(seen.has(x))refuse('CODE_DUPLICATE',at+'.membership_codes['+i+']');seen.add(x);});
  keys(c.factors,FACTORS,at+'.factors');for(const f of FACTORS)measure(c.factors[f],at+'.factors.'+f,n);
  keys(c.axes,AXES,at+'.axes');for(const a of AXES)measure(c.axes[a],at+'.axes.'+a,n);
  keys(c.all_axes,['denominator','valid'],at+'.all_axes');if(int(c.all_axes.denominator,at+'.all_axes.denominator')!==n)refuse('DENOMINATOR_MISMATCH',at+'.all_axes.denominator');
  if(int(c.all_axes.valid,at+'.all_axes.valid')>Math.min(...AXES.map(a=>c.axes[a].valid)))refuse('COUNT_RANGE',at+'.all_axes.valid');
  keys(c.published_default_total,['denominator','valid'],at+'.published_default_total');
  if(int(c.published_default_total.denominator,at+'.published_default_total.denominator')!==n)refuse('DENOMINATOR_MISMATCH',at+'.published_default_total.denominator');
  if(int(c.published_default_total.valid,at+'.published_default_total.valid')>n)refuse('COUNT_RANGE',at+'.published_default_total.valid');
  keys(c.presets,PRESETS,at+'.presets');
  for(const p of PRESETS){const x=c.presets[p],pa=at+'.presets.'+p;keys(x,PRESET,pa);
   if(x.basis!=='DERIVED_FROM_ARCHIVED_AXES')refuse('ENUM',pa+'.basis');if(int(x.denominator,pa+'.denominator')!==n)refuse('DENOMINATOR_MISMATCH',pa+'.denominator');
   const u=int(x.unknown,pa+'.unknown');if(u>n)refuse('COUNT_RANGE',pa+'.unknown');counter(x.reasons,pa+'.reasons');
   if(!c.engine_matches){if(x.valid!==null||x.known_valid!==null||u!==n||sum(x.reasons)!==n||x.reasons.ENGINE_VERSION_MISMATCH!==n)refuse('ENGINE_MISMATCH_NOT_NULL',pa);continue;}
   const k=int(x.known_valid,pa+'.known_valid');if(k+u>n)refuse('COUNT_RANGE',pa+'.known_valid');
   if(u>0?x.valid!==null:x.valid!==k)refuse('PRESET_VALID_MISMATCH',pa+'.valid');
   if(sum(x.reasons)!==n-k)refuse('COUNT_MISMATCH',pa+'.reasons');if(times(x.reasons,'TYPE_WEIGHTS_NOT_LINKED')!==u)refuse('COUNT_MISMATCH',pa+'.reasons.TYPE_WEIGHTS_NOT_LINKED');}
  return{ok:true,value:freeze(c)};
 }catch(e){if(e instanceof Refusal)return{ok:false,code:e.code,path:e.path};return{ok:false,code:'INVALID',path:'$'};}}

const frac=(v,n)=>v+' / '+n;
const reasonText=c=>(typeof c==='string'&&own(REASON,c)?REASON[c]:'사유 코드 '+c);
// The denominator words (owner: the operational 504 codes). A count other than 504 says so; it is never forced to 504.
function basisText(d){const n=d.count;
 return(n===UNIVERSE_N?'운영 Universe504 코드 504개 기준':'운영 게시본 코드 '+n+'개 기준 · Universe504(504개)와 다름')+' · 게시 행 '+d.published_rows+'개 중 TARGET '+d.target_rows_excluded+'개 제외'
  +' · 고정 증권 ID 아님'+(d.unique_issuer_ciks===null?' · 발행사 CIK 수 미확인(CIK 없는 행 '+d.missing_cik_rows+'개)':' · 발행사 CIK '+d.unique_issuer_ciks+'개');}
function measureLine(m){const parts=['계산 가능 '+frac(m.valid,m.denominator)];
 if(m.not_applicable)parts.push('해당 없음 '+m.not_applicable);const other=m.missing-m.not_applicable;if(other)parts.push('결손 '+other);return parts.join(' · ');}
function categoryLines(m){return CATEGORIES.filter(k=>m.reason_categories[k]).map(k=>CATEGORY_LABEL[k]+' '+m.reason_categories[k]);}
/* The view model of a valid coverage file: header, basis, rows [{id, kind axis|all_axes|preset|published_total, label, value, note}], factors. */
function coverageView(c){const n=c.denominator.count,t=c.times||{};
 const rows=[...AXES.map(a=>({id:'axis-'+a,kind:'axis',label:AXIS_LABEL[a]+' 단독',value:measureLine(c.axes[a]),valid:c.axes[a].valid,note:categoryLines(c.axes[a]).join(' · ')||null})),
  {id:'all-axes',kind:'all_axes',label:'Q·G·V 세 축 동시',value:'계산 가능 '+frac(c.all_axes.valid,n),valid:c.all_axes.valid,note:null},
  ...PRESETS.map(p=>{const x=c.presets[p];const reasons=Object.keys(x.reasons).sort().map(r=>reasonText(r)+' '+x.reasons[r]);
   return{id:'preset-'+p,kind:'preset',label:'프리셋 총점 · '+PRESET_LABEL[p],
    value:x.valid===null?(x.known_valid===null?'미산출':'미산출 · 확인된 '+x.known_valid+'개 · 미확인 '+x.unknown+'개'):'계산 가능 '+frac(x.valid,n),valid:x.valid,note:c.engine_matches?reasons.join(' · ')||null:null};}),// engine mismatch: one line for all seven (engine below)
  {id:'published-total',kind:'published_total',label:'게시본 기본 총점(저장값)',value:'있음 '+frac(c.published_default_total.valid,n),valid:c.published_default_total.valid,note:null}];
 // A publication id is one long unbroken token: the head shows its first 18 characters (the full id and source hash sit in ids).
 const short=c.publication_id.length>24?c.publication_id.slice(0,18)+'…':c.publication_id;
 return Object.freeze({ids:Object.freeze({publication_id:c.publication_id,source_sha256:c.source_sha256}),head:'운영 게시본 '+short+' · 가격 기준일 '+(t.price_basis_date||'미기록')+' · '+c.calc_version,basis:basisText(c.denominator),
  scope:TEXT.SCOPE,presetBasis:TEXT.PRESET_BASIS,engine:c.engine_matches?null:reasonText('ENGINE_VERSION_MISMATCH'),rows:Object.freeze(rows),
  factors:Object.freeze(FACTORS.map(f=>({id:f,axis:f[0].toUpperCase(),label:FACTOR_LABEL[f],value:measureLine(c.factors[f])})))});}

/* The general research selection fields of a vertical_slice result → {ok:true, value} | {ok:false, code, path}. Other result keys
   (outcomes, realised returns, …) are not read. */
function validateSelection(res){
 try{
  if(!isObj(res))refuse('TYPE','$');const at='$';for(const k of['selection_policy','n_eligible','n_selected','selected','weights'])if(!own(res,k))refuse('KEY_MISSING',at+'.'+k);
  const p=res.selection_policy;let mode='all',value=null;
  if(p!==null){keys(p,['mode','value'],at+'.selection_policy');mode=p.mode;value=p.value;
   if(!MODES.includes(mode))refuse('ENUM',at+'.selection_policy.mode');
   if(mode==='all'&&value!==null)refuse('POLICY_INVALID',at+'.selection_policy.value');
   if(mode==='top_n'&&!(Number.isInteger(value)&&value>0))refuse('POLICY_INVALID',at+'.selection_policy.value');
   if(mode==='top_percent'&&!(typeof value==='number'&&Number.isFinite(value)&&value>0&&value<=100))refuse('POLICY_INVALID',at+'.selection_policy.value');}
  const e=int(res.n_eligible,at+'.n_eligible'),s=int(res.n_selected,at+'.n_selected');
  // Codex's count rule (select_provisional): all; min(n, N); floor(n × p / 100), computed in integer hundredths of a percent.
  const expect=mode==='top_n'?Math.min(e,value):mode==='top_percent'?Math.floor(e*Math.round(value*1e6)/1e8):e;
  if(s!==expect)refuse('SELECTED_COUNT_MISMATCH',at+'.n_selected');
  if(!Array.isArray(res.selected)||res.selected.length!==s||new Set(res.selected).size!==s||res.selected.some(x=>typeof x!=='string'||!x))refuse('SELECTED_INVALID',at+'.selected');
  const w=res.weights;
  if(s===0){if(w!==null)refuse('WEIGHTS_INVALID',at+'.weights');}
  else{if(!isObj(w))refuse('WEIGHTS_INVALID',at+'.weights');const ids=Object.keys(w);
   if(ids.length!==s||ids.some(id=>!res.selected.includes(id)))refuse('WEIGHTS_INVALID',at+'.weights');
   for(const id of ids){const x=w[id];if(typeof x!=='number'||!Number.isFinite(x)||Math.abs(x-1/s)>1e-9)refuse('WEIGHTS_NOT_EQUAL',at+'.weights.'+id);}}
  return{ok:true,value:freeze({mode,value,legacy:p===null,n_eligible:e,n_selected:s,weight:s?1/s:null})};
 }catch(e){if(e instanceof Refusal)return{ok:false,code:e.code,path:e.path};return{ok:false,code:'INVALID',path:'$'};}}
const pct=x=>(Math.round(x*10000)/100).toString().replace(/\.0+$/,'')+'%';
function modeText(v){if(v.mode==='top_n')return'상위 '+v.value+'개';if(v.mode==='top_percent')return'상위 '+v.value+'% (소수점 아래 버림)';return v.legacy?'조건 충족 전부 (선정 방식 지정 없음)':'조건 충족 전부';}
function selectionView(v){return Object.freeze({mode:v.mode,label:modeText(v),
 count:'조건 충족 '+v.n_eligible+'개 중 '+v.n_selected+'개 선정',weight:v.n_selected?'같은 비중 · 각 '+pct(v.weight):'선정 0개 · 비중 없음',general:TEXT.GENERAL,official:TEXT.OFFICIAL});}

function source(){return Promise.resolve(Object.freeze({state:'NONE',code:'RESEARCH_SCOPE_NOT_CONNECTED',coverage:null,selection:null,text:TEXT.NONE}));}
return Object.freeze({COVERAGE_SCHEMA,UNIVERSE_N,FACTORS,AXES,PRESETS,MODES,TEXT,validateCoverage,coverageView,basisText,validateSelection,selectionView,reasonText,source});
});
