/* 참조집단 확대 연구 reader (IS2.referenceView; owner 2026-11-10 「통합 QGV·섹터 QGV」 queue §6, Codex #528
   research.sector_qgv_reference.reference_view → sector-qgv-reference-view/1, REFERENCE_STUDY.md). Read as written; nothing is
   recalculated, ranked, filtered into the result or filled (DC-42).
   - What it is: the same evaluation population (운영504 code rows / 501 issuers) scored by the same engine, model, settings,
     minimum 20, strict missing and official-Q gate, with eligible external issuer observations added ONLY to the preregistered
     factor reference pools. Reference-only issuers are never scored targets, never ranked and never in the denominator. It is
     PRIVATE_RESEARCH and NOT_ADOPTED: never the official QGV, never a performance claim, never the whole market.
   - Comparison type words (owner queue §6): 참조집단 확대 here; 원값 보완 is the input connection repair (IS2.inputRepair);
     핵심 요소 축소 and 비중 변경 are other studies. They are never shown as one another.
   - Trust: accepted only for the result already delivered in the checked held issuer bundle: the coverage scope whose context
     has the same population id / version / members hash / code-row denominator, evaluation day, input hash (result identity)
     and config hash as this view's evaluation population and bindings. Its own hashes alone prove nothing. A refused file is
     this block's error; the bundle, coverage and details stay as they were.
   - Checked as written: exact keys; both populations' identities; same day and availability cutoff for the reference pool;
     bindings.evaluation = evaluation_population; rows: one per evaluation code row, unique, a null total has a null rank;
     axis and factor counts per unit (code rows: after = before + gained − lost; issuers never above code rows or the issuer
     denominator); each group's reference N = its reference issuers.
   - Words: reference N is the factor's pool size after admission; it stays the same whatever the screen filters. 0 stays 0,
     null is 미산출. Reference membership lists are not shown (counts only).
   Pure; no storage, no request. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else{const I=root.IS2=root.IS2||{};I.referenceView=api;}})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
const SCHEMA='sector-qgv-reference-view/1';
const KEYS=Object.freeze(['study','request_id','cache_key','result_id','evaluation_population','reference_population','bindings','comparison','groups',
 'performance','whole_market_denominator','operating_adoption','rank_scope','schema_version','visibility','source_result_hash']);
const AXES=Object.freeze(['Q','G','V','joint','total']),KINDS=Object.freeze(['before','after','gained','lost','changed_common']);
const HEX64=/^[0-9a-f]{64}$/,DAY=/^\d{4}-\d{2}-\d{2}$/,FACTOR_KEY=/^([a-z][a-z0-9_]{0,63}):(raw|score)$/;
const own=(o,k)=>Object.prototype.hasOwnProperty.call(o,k);
const isObj=v=>!!v&&typeof v==='object'&&!Array.isArray(v);
const nat=v=>Number.isInteger(v)&&v>=0;
const str=v=>typeof v==='string'&&v.length>0;
class Refusal extends Error{constructor(code,path){super(code+' '+path);this.code=code;this.path=path;}}
const need=(c,code,path)=>{if(!c)throw new Refusal(code,path);};
const exact=(o,keys,path)=>{need(isObj(o),'TYPE',path);const k=Object.keys(o);need(k.length===keys.length&&keys.every(x=>own(o,x)),'KEYS',path);};
function canonical(v){if(Array.isArray(v))return'['+v.map(canonical).join(',')+']';
 if(isObj(v))return'{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canonical(v[k])).join(',')+'}';return JSON.stringify(v);}
const same=(a,b)=>canonical(a)===canonical(b);
function population(p,path){need(isObj(p),'TYPE',path);
 for(const k of['id','version'])need(str(p[k]),'POPULATION_INVALID',path+'.'+k);
 need(typeof p.members_hash==='string'&&HEX64.test(p.members_hash),'POPULATION_INVALID',path+'.members_hash');
 need(typeof p.valuation_date==='string'&&DAY.test(p.valuation_date),'POPULATION_INVALID',path+'.valuation_date');
 need(str(p.as_of),'POPULATION_INVALID',path+'.as_of');need(nat(p.code_rows)&&nat(p.issuers)&&p.issuers<=p.code_rows,'POPULATION_INVALID',path+'.code_rows');
 need(typeof p.input_hash==='string'&&HEX64.test(p.input_hash),'POPULATION_INVALID',path+'.input_hash');}
// counter of one unit: rows exact arithmetic; issuers bounded by rows and the issuer denominator.
function counter(c,rowsDen,issuerDen,path,issuers){
 const want=[...KINDS.map(k=>k+'_rows'),...(issuers?KINDS.map(k=>k+'_issuers'):[])];exact(c,want,path);
 for(const k of KINDS){need(nat(c[k+'_rows'])&&c[k+'_rows']<=rowsDen,'COUNT_RANGE',path+'.'+k+'_rows');
  if(issuers)need(nat(c[k+'_issuers'])&&c[k+'_issuers']<=issuerDen&&c[k+'_issuers']<=c[k+'_rows'],'COUNT_RANGE',path+'.'+k+'_issuers');}
 need(c.after_rows===c.before_rows+c.gained_rows-c.lost_rows&&c.changed_common_rows<=c.before_rows-c.lost_rows,'COUNT_ARITHMETIC',path);}
const axesOf=(a,path)=>{exact(a,['Q','G','V'],path);for(const k of['Q','G','V'])need(a[k]===null||(typeof a[k]==='number'&&Number.isFinite(a[k])),'TYPE',path+'.'+k);};
const num=(v,path)=>need(v===null||(typeof v==='number'&&Number.isFinite(v)),'TYPE',path);

function check(x,anchor){
 exact(x,KEYS,'$');need(x.schema_version===SCHEMA,'SCHEMA','$.schema_version');need(x.visibility==='PRIVATE_RESEARCH','VISIBILITY','$.visibility');
 need(x.operating_adoption==='NOT_ADOPTED','ADOPTION_CLAIMED','$.operating_adoption');need(x.rank_scope==='ORIGINAL_EVALUATION_POPULATION_ONLY','RANK_SCOPE','$.rank_scope');
 need(x.performance===null,'PERFORMANCE_CLAIMED','$.performance');need(x.whole_market_denominator===null,'MARKET_NOT_NULL','$.whole_market_denominator');
 for(const k of['request_id','cache_key','result_id'])need(str(x[k]),'TYPE','$.'+k);need(typeof x.source_result_hash==='string'&&HEX64.test(x.source_result_hash),'HASH','$.source_result_hash');
 const s=x.study;need(isObj(s)&&str(s.study_id)&&str(s.version)&&str(s.policy)&&nat(s.minimum)&&Array.isArray(s.eligible_groups),'STUDY_INVALID','$.study');
 const E=x.evaluation_population,R=x.reference_population;population(E,'$.evaluation_population');population(R,'$.reference_population');
 need(typeof R.group_members_hash==='string'&&HEX64.test(R.group_members_hash)&&str(R.scope)&&nat(R.additional_issuers)&&R.additional_issuers<=R.issuers,'POPULATION_INVALID','$.reference_population');
 need(R.valuation_date===E.valuation_date&&R.as_of===E.as_of,'REFERENCE_DATE_MISMATCH','$.reference_population.valuation_date');
 const B=x.bindings;need(isObj(B)&&typeof B.config_hash==='string'&&HEX64.test(B.config_hash),'BINDINGS_INVALID','$.bindings');
 need(same(B.evaluation,E),'BINDINGS_MISMATCH','$.bindings.evaluation');
 for(const k of['engine_version','model_version','normalization_version','reference_adapter_version'])need(str(B[k]),'BINDINGS_INVALID','$.bindings.'+k);
 const C=x.comparison;exact(C,['denominator_code_rows','denominator_issuers','axes','factors','new_any_axis_issuers','rows'],'$.comparison');
 need(C.denominator_code_rows===E.code_rows&&C.denominator_issuers===E.issuers,'DENOMINATOR_MISMATCH','$.comparison.denominator_code_rows');
 exact(C.axes,AXES,'$.comparison.axes');for(const k of AXES)counter(C.axes[k],E.code_rows,E.issuers,'$.comparison.axes.'+k,true);
 need(isObj(C.factors),'TYPE','$.comparison.factors');for(const[k,c]of Object.entries(C.factors)){need(FACTOR_KEY.test(k),'FACTOR_KEY','$.comparison.factors');counter(c,E.code_rows,E.issuers,'$.comparison.factors.'+k,false);}
 need(nat(C.new_any_axis_issuers)&&C.new_any_axis_issuers<=E.issuers,'COUNT_RANGE','$.comparison.new_any_axis_issuers');
 need(Array.isArray(C.rows)&&C.rows.length===E.code_rows,'ROWS_INVALID','$.comparison.rows');const seen=new Set();
 C.rows.forEach((r,i)=>{const p='$.comparison.rows['+i+']';exact(r,['company_id','issuer_id','before_axes','after_axes','before_total','after_total','before_rank','after_rank','factors'],p);
  need(str(r.company_id)&&!seen.has(r.company_id),'ROWS_INVALID',p+'.company_id');seen.add(r.company_id);need(r.issuer_id===null||str(r.issuer_id),'ROWS_INVALID',p+'.issuer_id');
  axesOf(r.before_axes,p+'.before_axes');axesOf(r.after_axes,p+'.after_axes');for(const k of['before_total','after_total'])num(r[k],p+'.'+k);
  for(const[t,k]of[['before_total','before_rank'],['after_total','after_rank']]){need(r[k]===null||(Number.isInteger(r[k])&&r[k]>=1&&r[k]<=E.code_rows),'ROWS_INVALID',p+'.'+k);
   need(r[t]!==null||r[k]===null,'RANK_WITHOUT_TOTAL',p+'.'+k);}
  need(Array.isArray(r.factors),'ROWS_INVALID',p+'.factors');
  r.factors.forEach((f,j)=>{exact(f,['variant_id','before','after','reason'],p+'.factors['+j+']');need(str(f.variant_id)&&isObj(f.before)&&isObj(f.after)&&str(f.reason),'ROWS_INVALID',p+'.factors['+j+']');});});
 need(Array.isArray(x.groups),'TYPE','$.groups');
 x.groups.forEach((g,i)=>{const p='$.groups['+i+']';exact(g,['sector_id','accounting_template','variant_id','before_valid_n','after_valid_n','reference_members','reference_issuers','additional_members','minimum'],p);
  for(const k of['sector_id','accounting_template','variant_id'])need(str(g[k]),'GROUPS_INVALID',p+'.'+k);
  need(Array.isArray(g.before_valid_n)&&g.before_valid_n.every(nat)&&nat(g.after_valid_n)&&nat(g.minimum),'GROUPS_INVALID',p+'.after_valid_n');
  for(const k of['reference_members','reference_issuers','additional_members'])need(Array.isArray(g[k])&&g[k].every(str)&&new Set(g[k]).size===g[k].length,'GROUPS_INVALID',p+'.'+k);
  need(g.after_valid_n===g.reference_issuers.length&&g.additional_members.length<=g.reference_members.length,'GROUPS_INVALID',p+'.after_valid_n');});
 // The anchor: the delivered result (coverage scope context) this study evaluated.
 need(isObj(anchor)&&Array.isArray(anchor.scopes)&&anchor.scopes.length,'ANCHOR_REQUIRED','$.anchor');
 const hit=anchor.scopes.find(a=>isObj(a)&&a.population_id===E.id&&a.population_version===E.version&&a.members_hash===E.members_hash&&a.input_hash===E.input_hash&&a.denominator===E.code_rows);
 need(hit,'REFERENCE_RESULT_MISMATCH','$.evaluation_population');
 need(hit.valuation_date===E.valuation_date,'REFERENCE_DATE_MISMATCH','$.evaluation_population.valuation_date');
 need(hit.config_hash===B.config_hash,'REFERENCE_CONFIG_MISMATCH','$.bindings.config_hash');
 return hit;}
function validate(x,anchor){try{const hit=check(x,anchor);return{ok:true,value:Object.freeze({view:x,scope:hit.scope})};}
 catch(e){if(e instanceof Refusal)return{ok:false,code:e.code,path:e.path};return{ok:false,code:'INVALID',path:'$'};}}
// From a checked held issuer bundle (IS2.expandedIssuers.checkBundle value): each coverage scope's own context.
function anchorOf(bundle){const out=[];const sc=bundle&&bundle.coverage&&isObj(bundle.coverage.scopes)?bundle.coverage.scopes:{};
 for(const[k,s]of Object.entries(sc)){const c=isObj(s)&&isObj(s.context)?s.context:null;if(!c||!isObj(c.result_identity)||!isObj(c.population))continue;
  out.push(Object.freeze({scope:k,valuation_date:c.valuation_date,population_id:c.population.id,population_version:c.population.version,members_hash:c.population.members_hash,
   denominator:c.population.denominator,input_hash:c.result_identity.input_hash,config_hash:c.result_identity.config_hash}));}
 return Object.freeze({scopes:Object.freeze(out)});}

/* ---------------- words */
const TYPE=Object.freeze({REFERENCE:'참조집단 확대',INPUT_REPAIR:'원값 보완(입력 연결 수정)',CORE_REDUCTION:'핵심 요소 축소',WEIGHTS:'비중 변경'});
const AXIS_LABEL=Object.freeze({Q:'Q',G:'G',V:'V',joint:'Q·G·V 세 축 동시',total:'최종 총점'});
const W=Object.freeze({
 HEAD:'참조집단 확대 연구 (PRIVATE_RESEARCH · 운영 채택 안 됨)',
 NOT:'평가 대상·요소·비중·최소 표본·strict·공식 Q 관문은 그대로 · 참조 전용 기업은 순위·분모에 들어가지 않음 · 원값 보완·핵심 요소 축소·비중 변경과 다른 비교',
 LIMITS:'성과 미측정 · 전체시장 분모 미측정 · 공식 QGV·TARGET에 반영되지 않음',
 SCOPE:{FACTOR_VALID_RESEARCH_REFERENCES_NOT_LISTING_OR_SECURITY_ELIGIBILITY:'요소 입력이 적격인 연구 참조 · 상장·증권·투자 적격 확인 아님'},
 N_FIXED:'참조 N은 요소별 참조집단 크기 · 화면 필터로 바뀌지 않음',
 NULL:'미산출'});
const v=x=>x===null||x===undefined?W.NULL:String(x);
const short=h=>h.slice(0,12)+'…';
// view(x, scope, {sectorName}) → plain lines (counts and words only; no member list).
function view(x,scope,opt){const name=opt&&typeof opt.sectorName==='function'?opt.sectorName:(id=>id);
 const E=x.evaluation_population,R=x.reference_population,C=x.comparison;
 const ax=k=>{const c=C.axes[k];return AXIS_LABEL[k]+' · 코드 행 전 '+c.before_rows+' → 후 '+c.after_rows+' (새로 +'+c.gained_rows+' · 사라짐 '+c.lost_rows+' · 기존 값 바뀜 '+c.changed_common_rows+')'
  +' · 고유 발행사 '+c.before_issuers+' → '+c.after_issuers+' (새로 +'+c.gained_issuers+')';};
 const moved=Object.entries(C.factors).filter(([,c])=>c.gained_rows+c.lost_rows+c.changed_common_rows>0).sort(([a],[b])=>a<b?-1:1)
  .map(([k,c])=>{const[vid,stage]=k.split(':');return vid+' · '+(stage==='raw'?'원지표':'요소 점수')+' · 코드 행 '+c.before_rows+' → '+c.after_rows+' (+'+c.gained_rows+' · −'+c.lost_rows+' · 바뀜 '+c.changed_common_rows+')';});
 return Object.freeze({
  type:TYPE.REFERENCE,
  head:W.HEAD+' · '+x.study.study_id+' v'+x.study.version+' · 평가일 '+E.valuation_date,
  not:W.NOT,limits:W.LIMITS,nFixed:W.N_FIXED,
  evaluation:'평가 모집단 '+E.id+' · 코드 행 '+E.code_rows+' · 고유 발행사 '+E.issuers+' · 구성원 '+short(E.members_hash)+' · 입력 '+short(E.input_hash)+' (지금 받은 결과)',
  reference:'참조집단 '+R.id+' v'+R.version+' · 발행사 '+R.issuers+' (외부 추가 '+R.additional_issuers+') · '+(W.SCOPE[R.scope]||R.scope)+' · 구성원 '+short(R.members_hash),
  units:'단위가 다른 두 집단입니다 · 평가 코드 행과 참조 발행사의 수가 같아도 같은 집단이 아님',
  axes:Object.freeze(AXES.map(k=>Object.freeze({key:k,text:ax(k)}))),
  newAny:'Q·G·V 중 한 축이라도 새로 생긴 고유 발행사 '+C.new_any_axis_issuers+' / '+E.issuers,
  groups:Object.freeze(x.groups.map(g=>Object.freeze({key:g.sector_id+'|'+g.accounting_template+'|'+g.variant_id,
   text:name(g.sector_id)+' · '+g.accounting_template+' · '+g.variant_id+' · 참조 N '+[...new Set(g.before_valid_n)].join('/')+' → '+g.after_valid_n+' (외부 추가 '+g.additional_members.length+') · 최소 '+g.minimum}))),
  factors:Object.freeze(moved),
  rows:Object.freeze(C.rows.filter(r=>r.factors.length).map(r=>Object.freeze({id:r.company_id,text:r.company_id+' · 바뀐 요소 '+r.factors.map(f=>f.variant_id).join(', ')
   +' · Q '+v(r.before_axes.Q)+'→'+v(r.after_axes.Q)+' · G '+v(r.before_axes.G)+'→'+v(r.after_axes.G)+' · V '+v(r.before_axes.V)+'→'+v(r.after_axes.V)
   +' · 총점 '+v(r.before_total)+'→'+v(r.after_total)+' · 순위 '+v(r.before_rank)+'→'+v(r.after_rank)}))),
  scope});}

return Object.freeze({SCHEMA,TYPE,W,validate,anchorOf,view});
});
