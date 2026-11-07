/* Sector QGV (IS2.sectorQgv, feature 2.2; owner 2026-11-06 「섹터 QGV 실제 연결」): the screen side of Codex's common engine #505
   `investment_system.research.sector_qgv` (contract implementation/docs/research/sector_qgv/CONTRACT.md). Pure: no window, no
   request, no storage; runs in node as in the page.
   What the engine owns and this file never does: default presets, the factor catalog and its badges' facts (is_default,
   recommendation, calculator_status, accounting applicability), config validation and hashing, factor scores, peer
   normalization, strict missing, the official-Q gate, totals, ranks, coverage, before/after comparison and the saved record.
   Every number the screen shows comes from an engine answer (sector-qgv-engine-response/1, tools/sector_qgv_engine_bridge.py).
   What this file does:
   - request(op, fields) builds sector-qgv-engine-request/1 with a fresh request_id; check(op, req, res, ctx) refuses an answer
     that is not exactly that request's (schema, op, request_id, the context's versions, the preview and comparison schemas), so
     a late or foreign answer never replaces the current one;
   - edits of one preset in the engine's own shape (axis basis points, axes[axis][role] = {weight, factors: {variant: bp}}):
     axis / role / factor weights, add (a same-role addition splits that role's budget), remove, replace (same axis and role);
     scope: the edited preset goes into config.scoped_overrides['SECTOR|TEMPLATE'] only, or — the user's explicit 전체 섹터에
     적용 — into every scope whose template every selected variant applies to (the others are listed, never changed);
   - sums(preset): the sum lines the screen shows while editing (the engine's validate_config stays the authority);
   - words: sector / template / role / status / gate / factor-status texts, unknown codes shown as the code itself;
   - validateSaved(x): the shape of the engine's save_user_config answer, the only thing the device stores. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else{const I=root.IS2=root.IS2||{};I.sectorQgv=api;}})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
const REQUEST='sector-qgv-engine-request/1',RESPONSE='sector-qgv-engine-response/1',PREVIEW='sector-qgv-preview/1',CONFIG='sector-qgv-config/1';
const AXES=Object.freeze(['Q','G','V']),OPS=Object.freeze(['context','view','preview','save']);
const SECTOR_TEXT=Object.freeze({CONSUMER_DISCRETIONARY:'경기소비재',CONSUMER_STAPLES:'필수소비재',ENERGY:'에너지',FINANCIALS:'금융',HEALTH_CARE:'헬스케어',
 INDUSTRIALS:'산업재',INFORMATION_TECHNOLOGY:'정보기술',MATERIALS:'소재',TELECOMMUNICATIONS:'통신',UTILITIES:'유틸리티'});
const TEMPLATE_TEXT=Object.freeze({GENERAL:'일반',BANK:'은행',INSURANCE:'보험',BROKER:'증권',MORTGAGE_REIT:'모기지 REIT',ASSET_MANAGER:'자산운용',EQUITY_REIT:'지분형 REIT'});
const AXIS_TEXT=Object.freeze({Q:'Q · 질',G:'G · 성장',V:'V · 가치'});
const ROLE_TEXT=Object.freeze({profitability:'수익성',accounting_quality:'회계 품질',financial_capacity:'재무 여력',interest_capacity:'이자 지급 능력',stability:'안정성',
 growth:'성장',profitability_change:'수익성 개선',earnings:'이익',cash:'현금흐름',other_value:'기타 가치'});
// Row status of the engine (preview_qgv result_rows[].status).
const STATUS_TEXT=Object.freeze({VALID:'산출',GATE_UNKNOWN:'관문 판정 불가 · 최종 점수·순위 없음',STRICT_INCOMPLETE:'필수 요소 결측 · 총점 미산출',
 MAPPING_UNRESOLVED:'섹터·회계모형 분류 미확정 · 점수 계산 안 함',NO_WEIGHT_AFTER_GATE:'관문 뒤 남은 비중 없음 · 총점 미산출'});
// gate_status of the engine (official-q-percentile-required/1): three results, told apart in words.
const GATE_TEXT=Object.freeze({PASS:'관문 통과',VALUE_EXCLUDED:'관문: 가치(V) 제외 · 남은 축 비례 재배분',UNKNOWN:'관문 판정 불가 · 공식 Q 업종 분위 없음'});
// Factor raw_status / score_status codes of the engine.
const FACTOR_TEXT=Object.freeze({VALID:'점수 있음',VALID_ZERO:'값 0 (유효)',VALID_NEGATIVE:'음수 (유효)',MISSING_INPUT:'자료 없음',STALE:'오래된 자료',
 PEER_SAMPLE_SMALL:'비교집단 20개 미만',MAPPING_UNRESOLVED:'분류 미확정',ISSUER_REPRESENTATIVE_UNRESOLVED:'대표 증권 미확정',NOT_APPLICABLE:'이 회계모형에 적용 안 함',
 CALCULATOR_PENDING:'계산 기능 준비 중',DOMAIN_INVALID:'정의역 밖(분모 0 이하 등)',EVIDENCE_MISSING:'근거 없음',NOT_YET_AVAILABLE:'기준일 뒤 자료',PERIOD_MISMATCH:'기간 불일치',
 SCOPE_MISMATCH:'범위 불일치',UNIT_MISMATCH:'단위 불일치',CURRENCY_MISMATCH:'통화 불일치',INPUT_INVALID:'입력 오류',OBSERVATION_VERSION_MISMATCH:'관측 버전 불일치'});
// Fixed refusal codes of the route, the bridge or the engine.
const ERROR_TEXT=Object.freeze({ENGINE_NOT_CONNECTED:'계산 실행 경로 연결 전 · 이 사이트에는 엔진 경로가 없음 (개발 환경에서만 연결)',ENGINE_UNREACHABLE:'계산 엔진에 닿지 못함',
 ENGINE_HTTP_FAILED:'계산 엔진 응답 실패',ENGINE_ANSWER_INVALID:'계산 엔진 응답 형식 오류',ENGINE_ANSWER_TOO_LARGE:'계산 엔진 응답이 너무 큼',ENGINE_FAILED:'계산 엔진 내부 오류',
 ANSWER_MISMATCH:'다른 요청의 응답 · 버림',DUPLICATE_COMPANY_ID:'입력 거부 · 회사 ID 중복',WEIGHTS_MUST_SUM_10000:'비중 합계가 100%가 아님',DUPLICATE_VARIANT_ALIAS:'같은 요소가 두 번 선택됨',
 FACTOR_ROLE_MISMATCH:'요소가 다른 역할에 들어감',CALCULATOR_PENDING:'계산 기능 준비 중인 요소에 비중이 있음',AXES_INVALID:'축 구성 오류',MAPPING_UNRESOLVED:'섹터·회계모형 분류 미확정',
 PREVIEW_CONFIG_OR_REQUEST_MISMATCH:'미리보기와 설정이 달라 저장 거부',PREVIEW_NOT_FOUND:'미리보기를 다시 실행하세요',INPUT_UNKNOWN:'알 수 없는 입력',CONFIG_INVALID:'설정 형식 오류',
 INPUT_VERSION_MISMATCH:'입력 버전 불일치',DUPLICATE_MEMBER:'모집단 중복',ROW_OUTSIDE_UNIVERSE:'모집단 밖 행',LAST_FACTOR_OF_AXIS:'축의 마지막 요소 · 빼려면 축 비중을 0으로',
 NOT_APPLICABLE:'이 회계모형에 적용 안 되는 요소'});
const EVIDENCE_TEXT=Object.freeze({OWNER_INITIAL_DESIGN:'오너 초기 설계(성과 미검증)'});
const text=(map,code)=>code===null||code===undefined?'':Object.prototype.hasOwnProperty.call(map,code)?map[code]:String(code);
const errorText=code=>{const c=String(code||''),i=c.indexOf(':'),head=i<0?c:c.slice(0,i);return Object.prototype.hasOwnProperty.call(ERROR_TEXT,head)?ERROR_TEXT[head]+(i<0?'':' ('+c.slice(i+1)+')'):c;};

const object=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
const copy=v=>JSON.parse(JSON.stringify(v));
const own=(o,k)=>Object.prototype.hasOwnProperty.call(o,k);
const HEX64=/^[0-9a-f]{64}$/;

// ---- requests and answers
let seq=0;const token=Math.random().toString(36).slice(2,8);
function request(op,fields={}){if(!OPS.includes(op))throw Error('OP_UNKNOWN');seq+=1;return {schema_version:REQUEST,op,request_id:'ui-'+token+'-'+seq,...copy(fields)};}
const bad=code=>({ok:false,code});
function check(op,req,res,ctx=null){
 if(!object(res)||res.schema_version!==RESPONSE||res.op!==op||res.request_id!==req.request_id||typeof res.ok!=='boolean')return bad('ANSWER_MISMATCH');
 if(!res.ok)return bad(typeof res.code==='string'&&res.code?res.code:'ENGINE_FAILED');
 const has=k=>own(res,k);
 if(op==='context'){
  if(!object(res.versions)||!object(res.default_config)||res.default_config.schema_version!==CONFIG||!Array.isArray(res.sectors)||!Array.isArray(res.templates)||!Array.isArray(res.inputs)||!object(res.gate))return bad('ENGINE_ANSWER_INVALID');
  for(const s of res.sectors)if(!object(s)||typeof s.sector_id!=='string'||!object(s.axis_weights))return bad('ENGINE_ANSWER_INVALID');
  for(const x of res.inputs)if(!object(x)||typeof x.input_id!=='string'||x.data_kind!=='SYNTHETIC')return bad('ENGINE_ANSWER_INVALID');
  return {ok:true};}
 if(!object(ctx)||!object(ctx.versions))return bad('ANSWER_MISMATCH');
 if(op==='view'){
  if(!['sector_id','accounting_template','validation','preset','default_preset','factors'].every(has)||!Array.isArray(res.factors)||!object(res.preset)||!object(res.validation))return bad('ENGINE_ANSWER_INVALID');
  if(res.sector_id!==req.sector_id||res.accounting_template!==req.accounting_template||res.preset.preset_id!==ctx.versions.model_version)return bad('ANSWER_MISMATCH');
  return {ok:true};}
 if(op==='preview'){
  if(res.input_id!==req.input_id||res.data_kind!=='SYNTHETIC'||!object(res.before)||!object(res.after)||!object(res.comparison))return bad('ENGINE_ANSWER_INVALID');
  for(const p of [res.before,res.after]){if(p.schema_version!==PREVIEW||!Array.isArray(p.result_rows)||!object(p.coverage))return bad('ENGINE_ANSWER_INVALID');
   for(const k of ['model_version','engine_version','normalization_version','mapping_version'])if(p[k]!==ctx.versions[k])return bad('ANSWER_MISMATCH');}
  if(res.after.request_id!==req.request_id||res.comparison.comparison_id!==req.request_id)return bad('ANSWER_MISMATCH');
  // saved: the engine's save_user_config record for exactly this preview, or {refused: code}.
  if(!object(res.saved))return bad('ENGINE_ANSWER_INVALID');
  if(!own(res.saved,'refused')){const r=validateSaved(res.saved);if(!r.ok)return r;if(res.saved.preview_id!==res.after.preview_id)return bad('ANSWER_MISMATCH');}
  return {ok:true};}
 if(op==='save'){const r=validateSaved(res.saved);if(!r.ok)return r;if(res.saved.preview_id!==req.preview_id)return bad('ANSWER_MISMATCH');return {ok:true};}
 return bad('OP_UNKNOWN');}

// The engine's save_user_config answer: {config, canonical_config_hash, preview_id, snapshot_id, universe_id, universe_version}.
function validateSaved(x){
 if(!object(x))return bad('SAVED_INVALID');
 const keys=['config','canonical_config_hash','preview_id','snapshot_id','universe_id','universe_version'];
 if(Object.keys(x).length!==keys.length||!keys.every(k=>own(x,k)))return bad('SAVED_KEYS');
 if(!object(x.config)||x.config.schema_version!==CONFIG||typeof x.config.base_preset_id!=='string'||(own(x.config,'scoped_overrides')&&!object(x.config.scoped_overrides)))return bad('SAVED_CONFIG');
 if(!HEX64.test(x.canonical_config_hash)||!HEX64.test(x.preview_id))return bad('SAVED_HASH');
 for(const k of ['snapshot_id','universe_id','universe_version'])if(typeof x[k]!=='string'||!x[k]||x[k].length>200)return bad('SAVED_CONTEXT');
 return {ok:true};}

// ---- preset edits (the engine's shape; integer basis points, each level sums to 10000)
const scopeKey=(sector,template)=>sector+'|'+template;
function split(total,n){const base=Math.floor(total/n),out=Array(n).fill(base);for(let i=0;i<total-base*n;i++)out[i]+=1;return out;}
// Rescale integer weights to sum `total`, keeping their proportions (largest remainders; all zero -> equal shares).
function rescale(weights,total){const keys=Object.keys(weights);if(!keys.length)return {};const sum=keys.reduce((t,k)=>t+weights[k],0);
 if(sum<=0){const s=split(total,keys.length);return Object.fromEntries(keys.map((k,i)=>[k,s[i]]));}
 const raw=keys.map(k=>weights[k]*total/sum),out=raw.map(Math.floor);let left=total-out.reduce((a,b)=>a+b,0);
 const order=keys.map((k,i)=>i).sort((a,b)=>(raw[b]-out[b])-(raw[a]-out[a])||a-b);for(let i=0;left>0;i++,left--)out[order[i%order.length]]+=1;
 return Object.fromEntries(keys.map((k,i)=>[k,out[i]]));}
const bp=n=>{const v=Math.round(Number(n));if(!Number.isFinite(v)||v<0||v>10000)throw Error('WEIGHT_RANGE');return v;};
function setAxis(p,axis,value){if(!AXES.includes(axis))throw Error('AXIS_UNKNOWN');const o=copy(p);o.axis_weights[axis]=bp(value);return o;}
function setRole(p,axis,role,value){const o=copy(p);if(!object(o.axes[axis])||!own(o.axes[axis],role))throw Error('ROLE_UNKNOWN');o.axes[axis][role].weight=bp(value);return o;}
function setFactor(p,axis,role,variant,value){const o=copy(p),r=o.axes[axis]&&o.axes[axis][role];if(!r||!own(r.factors,variant))throw Error('FACTOR_UNKNOWN');r.factors[variant]=bp(value);return o;}
// factor: an entry of the engine's list_factors answer (variant_id, axis, role, calculator_status, accounting_applicability).
function selectable(factor){if(factor.calculator_status!=='IMPLEMENTED')return 'PENDING';if(factor.accounting_applicability!==true)return 'NOT_FIT';return 'OK';}
const selected=p=>new Set(AXES.flatMap(a=>Object.values(p.axes[a]||{}).flatMap(r=>Object.keys(r.factors))));
function addFactor(p,factor){const why=selectable(factor);if(why!=='OK')throw Error(why==='PENDING'?'CALCULATOR_PENDING':'NOT_APPLICABLE');
 const o=copy(p),{axis,role,variant_id:v}=factor;if(selected(o).has(v))throw Error('DUPLICATE_VARIANT_ALIAS');
 const roles=o.axes[axis];if(!own(roles,role)){roles[role]={weight:0,factors:{[v]:10000}};return o;}// a new role starts at weight 0: the user sets its budget
 const names=[...Object.keys(roles[role].factors),v],s=split(10000,names.length);roles[role].factors=Object.fromEntries(names.map((n,i)=>[n,s[i]]));return o;}
function removeFactor(p,axis,role,variant){const o=copy(p),roles=o.axes[axis];if(!roles||!own(roles,role)||!own(roles[role].factors,variant))throw Error('FACTOR_UNKNOWN');
 const count=Object.values(roles).reduce((t,r)=>t+Object.keys(r.factors).length,0);if(count<=1)throw Error('LAST_FACTOR_OF_AXIS');
 delete roles[role].factors[variant];
 if(!Object.keys(roles[role].factors).length){delete roles[role];const w=rescale(Object.fromEntries(Object.entries(roles).map(([k,r])=>[k,r.weight])),10000);for(const k of Object.keys(roles))roles[k].weight=w[k];}
 else roles[role].factors=rescale(roles[role].factors,10000);return o;}
function replaceFactor(p,axis,role,from,factor){if(factor.axis!==axis||factor.role!==role)throw Error('FACTOR_ROLE_MISMATCH');const why=selectable(factor);if(why!=='OK')throw Error(why==='PENDING'?'CALCULATOR_PENDING':'NOT_APPLICABLE');
 const o=copy(p),r=o.axes[axis]&&o.axes[axis][role];if(!r||!own(r.factors,from))throw Error('FACTOR_UNKNOWN');if(selected(o).has(factor.variant_id))throw Error('DUPLICATE_VARIANT_ALIAS');
 r.factors=Object.fromEntries(Object.entries(r.factors).map(([k,w])=>k===from?[factor.variant_id,w]:[k,w]));return o;}
// The sum lines (axis, each axis's roles, each role's factors); the engine's validate_config decides.
function sums(p){const out={axis:AXES.reduce((t,a)=>t+p.axis_weights[a],0),roles:{},factors:{}};
 for(const a of AXES){out.roles[a]=Object.values(p.axes[a]).reduce((t,r)=>t+r.weight,0);for(const [role,r] of Object.entries(p.axes[a]))out.factors[a+'|'+role]=Object.values(r.factors).reduce((t,w)=>t+w,0);}
 out.ok=out.axis===10000&&AXES.every(a=>out.roles[a]===10000)&&Object.values(out.factors).every(s=>s===10000);return out;}
// Config with this scope's edited preset (owner_scope PRIVATE: the user's own device setting; it does not change the hash).
function withScope(config,p){const c=copy(config);c.scoped_overrides=c.scoped_overrides||{};c.scoped_overrides[scopeKey(p.sector_id,p.accounting_template)]=copy(p);c.owner_scope='PRIVATE';c.config_id='device';return c;}
function withoutScope(config,sector,template){const c=copy(config);if(c.scoped_overrides)delete c.scoped_overrides[scopeKey(sector,template)];return c;}
// 전체 섹터에 적용: the user's explicit copy into every scope whose template every selected variant applies to.
// scopes: [{sector_id, accounting_template}], catalog: [{variant_id, scope:[templates]}] (the engine's list_factors answer).
function applyAll(config,p,scopes,catalog){const c=withScope(config,p),used=selected(p),applied=[],skipped=[],scopeOf=new Map(catalog.map(f=>[f.variant_id,f.scope]));
 for(const s of scopes){const key=scopeKey(s.sector_id,s.accounting_template);if(key===scopeKey(p.sector_id,p.accounting_template)){applied.push(key);continue;}
  const fits=[...used].every(v=>Array.isArray(scopeOf.get(v))&&scopeOf.get(v).includes(s.accounting_template));
  if(!fits){skipped.push(key);continue;}c.scoped_overrides[key]={...copy(p),sector_id:s.sector_id,accounting_template:s.accounting_template};applied.push(key);}
 return {config:c,applied,skipped};}

// ---- factor list words (facts from the engine's list_factors answer and the last preview's coverage)
function badges(factor,coverage){const out=[];
 if(factor.is_default)out.push({code:'BASE',text:'기본값 · 초기 설정'});
 if(factor.recommendation&&factor.recommendation.recommended)out.push({code:'RECOMMENDED',text:'추천'});
 if(factor.selected)out.push({code:'SELECTED',text:'선택됨'});
 const why=selectable(factor);if(why==='PENDING')out.push({code:'PENDING',text:'계산 기능 준비 중 · 선택 불가'});if(why==='NOT_FIT')out.push({code:'NOT_FIT',text:'산식 적용 부적합 · 선택 불가'});
 const c=coverage&&coverage.factors&&coverage.factors[factor.variant_id];
 if(why==='OK'&&c&&c.denominator>0&&c.raw_valid<c.denominator)out.push({code:'PARTIAL',text:'자료 일부 부족 '+c.raw_valid+'/'+c.denominator+' · 선택 가능'});
 return out;}
function search(factors,q){const t=String(q||'').trim().toLowerCase();if(!t)return [];
 return factors.filter(f=>[f.display_name,f.factor_id,f.variant_id,...(f.aliases||[])].some(x=>String(x||'').toLowerCase().includes(t)));}

return Object.freeze({REQUEST,RESPONSE,PREVIEW,CONFIG,AXES,OPS,SECTOR_TEXT,TEMPLATE_TEXT,AXIS_TEXT,ROLE_TEXT,STATUS_TEXT,GATE_TEXT,FACTOR_TEXT,ERROR_TEXT,EVIDENCE_TEXT,
 text,errorText,request,check,validateSaved,scopeKey,rescale,setAxis,setRole,setFactor,selectable,addFactor,removeFactor,replaceFactor,sums,withScope,withoutScope,applyAll,badges,search});
});
