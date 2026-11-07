/* Q/G 부분 비교 (IS2.sectorQgvAxis; owner 2026-11-07 「#505 실자료 부분 비교 계약 추가 인수」; Codex #505 7c2225a3
   `research/sector_qgv_partial.compare_axes`, contract `sector-qgv-axis-comparison/1`, docs/research/sector_qgv/PARTIAL_COMPARISON.md).
   The strict reader of one engine comparison. Pure: no window, no request, no storage; runs in node as in the page.
   - validate(json) -> {ok:true, value} (deep-frozen copy) or {ok:false, code, path}: refused whole at its first fault. Exact keys;
     Q and G each with before / after / delta / common_valid / transition / change_reason / reasons / factors, kept apart (a Q or G
     row is never hidden because the total has no common value); rank and performance null; the summary counts equal to the rows;
     the two kinds of comparison never mixed: SAME_INPUT_CONFIGURATION (D1, settings only: same input / snapshot / version, reasons
     FACTOR_ALLOCATION_CHANGED or UNCHANGED) and INPUT_CLASSIFICATION (I1, classification and peer input: same config, reasons
     CLASSIFICATION_OR_PEER_INPUT_CHANGED / PEER_RESCORING / UNCHANGED).
   - view(value): the engine's rows in the engine's order, the identity of each side (config / input / snapshot / versions) with
     what differs, V and total kept as they are (null = 산출 없음, never 0). Nothing is recomputed: no axis rank, no total, no
     market rank, no performance. filter(view, f) only selects rows to show; it never changes the comparison or a peer set. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else{const I=root.IS2=root.IS2||{};I.sectorQgvAxis=api;}})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
const SCHEMA='sector-qgv-axis-comparison/1';
const TREATMENTS=Object.freeze(['SAME_INPUT_CONFIGURATION','INPUT_CLASSIFICATION']);
const TRANSITIONS=Object.freeze(['COMMON_VALID','GAINED','LOST','BOTH_UNAVAILABLE']);
const REASONS=Object.freeze({SAME_INPUT_CONFIGURATION:['FACTOR_ALLOCATION_CHANGED','UNCHANGED'],INPUT_CLASSIFICATION:['CLASSIFICATION_OR_PEER_INPUT_CHANGED','PEER_RESCORING','UNCHANGED']});
const AXES=Object.freeze(['Q','G']);
const IDENTITY=Object.freeze(['config_hash','input_hash','cache_key','snapshot_id','input_version','engine_version','model_version','normalization_version','mapping_version']);
const SUMMARY=Object.freeze(['before_valid','after_valid','COMMON_VALID','GAINED','LOST','BOTH_UNAVAILABLE','changed_common']);
const TOP=Object.freeze(['schema_version','comparison_id','treatment','valuation_date','as_of','universe_id','universe_version','denominator','axes','rows',
 'before_identity','after_identity','performance','performance_reason','rank','rank_reason']);
const CELL=Object.freeze(['before','after','delta','common_valid','transition','change_reason','before_reasons','after_reasons','factors']);
const FACTOR=Object.freeze(['variant_id','before_allocation','after_allocation','before_score','after_score','before_valid_n','after_valid_n','before_status','after_status','allocation_changed','score_changed']);
const ALLOC=Object.freeze(['role','role_weight_bp','inner_weight_bp','axis_weight','nominal_total_weight']);
// Screen words (Korean).
const TREATMENT_TEXT=Object.freeze({SAME_INPUT_CONFIGURATION:'요소·비중 변경 (같은 입력·분류 · 설정만 다름)',INPUT_CLASSIFICATION:'분류 보완·비교집단 확대 (설정은 같음 · 입력·분류가 다름)'});
const TREATMENT_NOTE=Object.freeze({SAME_INPUT_CONFIGURATION:'변화는 요소·비중 설정 차이에서 옴 · 원자료·비교집단은 같음',
 INPUT_CLASSIFICATION:'상대점수 변화는 분류 보완과 비교집단 확대에서 옴 · 기업 실적이 좋아지거나 나빠졌다는 뜻이 아님'});
const TRANSITION_TEXT=Object.freeze({COMMON_VALID:'전후 모두 산출',GAINED:'새로 산출',LOST:'산출 안 됨으로 바뀜',BOTH_UNAVAILABLE:'전후 모두 미산출'});
const REASON_TEXT=Object.freeze({FACTOR_ALLOCATION_CHANGED:'요소·비중 변경',UNCHANGED:'변화 없음',PEER_RESCORING:'비교집단 변화로 상대점수 재계산 (실적 변화 아님)',
 CLASSIFICATION_OR_PEER_INPUT_CHANGED:'분류 보완 (섹터·회계모형 바뀜)'});
const IDENTITY_TEXT=Object.freeze({config_hash:'설정',input_hash:'입력',cache_key:'계산 키',snapshot_id:'스냅숏',input_version:'입력 버전',engine_version:'엔진',
 model_version:'모델',normalization_version:'정규화',mapping_version:'분류 버전'});
const text=(map,code)=>code===null||code===undefined?'':Object.prototype.hasOwnProperty.call(map,code)?map[code]:String(code);

const object=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
const own=(o,k)=>Object.prototype.hasOwnProperty.call(o,k);
class Fault extends Error{constructor(code,path){super(code);this.code=code;this.path=path;}}
const need=(ok,code,path)=>{if(!ok)throw new Fault(code,path);};
function keys(o,want,path){need(object(o),'TYPE',path);for(const k of want)need(own(o,k),'KEY_MISSING',path+'.'+k);for(const k of Object.keys(o))need(want.includes(k),'KEY_UNKNOWN',path+'.'+k);}
const num=(v,path,{nullable=true}={})=>{if(v===null&&nullable)return;need(typeof v==='number'&&Number.isFinite(v),'NUMBER',path);};
const str=(v,path,{nullable=false}={})=>{if(v===null&&nullable)return;need(typeof v==='string'&&v.length>0&&v.length<=200,'TEXT',path);};
const int=(v,path)=>need(Number.isInteger(v)&&v>=0,'COUNT',path);
const copyFreeze=v=>{const c=JSON.parse(JSON.stringify(v));(function f(x){if(x&&typeof x==='object'){Object.freeze(x);for(const y of Object.values(x))f(y);}})(c);return c;};

function check(c){
 keys(c,TOP,'$');need(c.schema_version===SCHEMA,'SCHEMA_VERSION','$.schema_version');str(c.comparison_id,'$.comparison_id');need(TREATMENTS.includes(c.treatment),'ENUM','$.treatment');
 for(const k of ['valuation_date','as_of','universe_id','universe_version'])str(c[k],'$.'+k);
 need(c.rank===null,'RANK_NOT_NULL','$.rank');need(c.performance===null,'PERFORMANCE_NOT_NULL','$.performance');str(c.rank_reason,'$.rank_reason');str(c.performance_reason,'$.performance_reason');
 for(const side of ['before_identity','after_identity']){keys(c[side],IDENTITY,'$.'+side);for(const k of IDENTITY)str(c[side][k],'$.'+side+'.'+k);}
 const b=c.before_identity,a=c.after_identity;
 for(const k of ['engine_version','model_version','normalization_version'])need(b[k]===a[k],'CONTEXT_MISMATCH','$.after_identity.'+k);
 // D1 and I1 are never mixed: settings only on the same input, or input / classification on the same settings.
 if(c.treatment==='SAME_INPUT_CONFIGURATION')for(const k of ['input_hash','snapshot_id','input_version','mapping_version'])need(b[k]===a[k],'TREATMENT_MIXED','$.after_identity.'+k);
 else need(b.config_hash===a.config_hash,'TREATMENT_MIXED','$.after_identity.config_hash');
 need(Array.isArray(c.rows),'ARRAY','$.rows');int(c.denominator,'$.denominator');need(c.denominator===c.rows.length,'DENOMINATOR','$.denominator');
 keys(c.axes,AXES,'$.axes');const counted={};for(const x of AXES){keys(c.axes[x],SUMMARY,'$.axes.'+x);for(const k of SUMMARY)int(c.axes[x][k],'$.axes.'+x+'.'+k);counted[x]=Object.fromEntries(SUMMARY.map(k=>[k,0]));}
 const seen=new Set();
 c.rows.forEach((r,i)=>{const p='$.rows['+i+']';keys(r,['company_id','before_context','after_context','axes','V','total'],p);str(r.company_id,p+'.company_id');need(!seen.has(r.company_id),'DUPLICATE',p+'.company_id');seen.add(r.company_id);
  for(const k of ['before_context','after_context']){need(Array.isArray(r[k])&&r[k].length===2,'CONTEXT',p+'.'+k);r[k].forEach((v,j)=>str(v,p+'.'+k+'['+j+']',{nullable:true}));}
  if(c.treatment==='SAME_INPUT_CONFIGURATION')need(r.before_context[0]===r.after_context[0]&&r.before_context[1]===r.after_context[1],'TREATMENT_MIXED',p+'.after_context');
  for(const k of ['V','total']){keys(r[k],['before','after'],p+'.'+k);num(r[k].before,p+'.'+k+'.before');num(r[k].after,p+'.'+k+'.after');}
  keys(r.axes,AXES,p+'.axes');
  for(const x of AXES){const q=p+'.axes.'+x,v=r.axes[x];keys(v,CELL,q);num(v.before,q+'.before');num(v.after,q+'.after');num(v.delta,q+'.delta');
   need(typeof v.common_valid==='boolean','TYPE',q+'.common_valid');need(TRANSITIONS.includes(v.transition),'ENUM',q+'.transition');need(REASONS[c.treatment].includes(v.change_reason),'TREATMENT_MIXED',q+'.change_reason');
   const both=v.before!==null&&v.after!==null;need(v.common_valid===both,'COMMON_MISMATCH',q+'.common_valid');need((v.delta!==null)===both,'DELTA_MISMATCH',q+'.delta');
   const t=both?'COMMON_VALID':v.after!==null?'GAINED':v.before!==null?'LOST':'BOTH_UNAVAILABLE';need(v.transition===t,'TRANSITION_MISMATCH',q+'.transition');
   for(const k of ['before_reasons','after_reasons']){need(Array.isArray(v[k]),'ARRAY',q+'.'+k);v[k].forEach((s,j)=>str(s,q+'.'+k+'['+j+']'));}
   need((v.before===null)===(v.before_reasons.length>0)&&(v.after===null)===(v.after_reasons.length>0),'NULL_WITHOUT_REASON',q);
   need(Array.isArray(v.factors),'ARRAY',q+'.factors');
   v.factors.forEach((f,j)=>{const fp=q+'.factors['+j+']';keys(f,FACTOR,fp);str(f.variant_id,fp+'.variant_id');
    for(const k of ['before_allocation','after_allocation'])if(f[k]!==null){keys(f[k],ALLOC,fp+'.'+k);str(f[k].role,fp+'.'+k+'.role');for(const n of ['role_weight_bp','inner_weight_bp','axis_weight','nominal_total_weight'])num(f[k][n],fp+'.'+k+'.'+n,{nullable:false});}
    num(f.before_score,fp+'.before_score');num(f.after_score,fp+'.after_score');
    for(const k of ['before_valid_n','after_valid_n'])if(f[k]!==null)int(f[k],fp+'.'+k);
    for(const k of ['before_status','after_status'])str(f[k],fp+'.'+k,{nullable:true});
    need(typeof f.allocation_changed==='boolean'&&typeof f.score_changed==='boolean','TYPE',fp);});
   const n=counted[x];n[t]++;if(v.before!==null)n.before_valid++;if(v.after!==null)n.after_valid++;if(both&&v.delta!==0)n.changed_common++;}});
 for(const x of AXES)for(const k of SUMMARY)need(counted[x][k]===c.axes[x][k],'SUMMARY_MISMATCH','$.axes.'+x+'.'+k);
}
function validate(json){try{check(json);return {ok:true,value:copyFreeze(json)};}catch(e){return e instanceof Fault?{ok:false,code:e.code,path:e.path}:{ok:false,code:'INVALID',path:'$'};}}

// ---- view: the comparison as delivered (no rank, no total, no rescoring)
function view(c){
 const diff=IDENTITY.filter(k=>c.before_identity[k]!==c.after_identity[k]);
 const present=(side,k)=>c.rows.filter(r=>r[k][side]!==null).length;
 return {comparison_id:c.comparison_id,treatment:c.treatment,valuation_date:c.valuation_date,as_of:c.as_of,universe_id:c.universe_id,universe_version:c.universe_version,
  denominator:c.denominator,axes:c.axes,rows:c.rows,before_identity:c.before_identity,after_identity:c.after_identity,identity_diff:diff,
  // V and total are only counted as present or not (never scored, never 0): the Q / G rows stay even when these are 0.
  vt:{V:{before:present('before','V'),after:present('after','V')},total:{before:present('before','total'),after:present('after','total')},
   total_common:c.rows.filter(r=>r.total.before!==null&&r.total.after!==null).length},
  reclassified:c.rows.filter(r=>r.before_context[0]!==r.after_context[0]||r.before_context[1]!==r.after_context[1]).length,
  rank_reason:c.rank_reason,performance_reason:c.performance_reason};}
// Row selection for display only. axis: 'Q'|'G'|'ANY'; show: 'ALL'|'CHANGED'|'GAINED'|'LOST'|'RECLASSIFIED'|'UNAVAILABLE'.
function filter(vw,{axis='ANY',show='ALL'}={}){
 const ax=axis==='ANY'?AXES:[axis];
 const hit=r=>{if(show==='ALL')return true;if(show==='RECLASSIFIED')return r.before_context[0]!==r.after_context[0]||r.before_context[1]!==r.after_context[1];
  return ax.some(x=>{const v=r.axes[x];return show==='CHANGED'?v.common_valid&&v.delta!==0:show==='GAINED'?v.transition==='GAINED':show==='LOST'?v.transition==='LOST':show==='UNAVAILABLE'?v.transition==='BOTH_UNAVAILABLE':false;});};
 return vw.rows.filter(hit);}

return Object.freeze({SCHEMA,TREATMENTS,TRANSITIONS,AXES,IDENTITY,TREATMENT_TEXT,TREATMENT_NOTE,TRANSITION_TEXT,REASON_TEXT,IDENTITY_TEXT,text,validate,view,filter});
});
