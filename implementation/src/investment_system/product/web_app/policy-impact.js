/* 정책·지정학 (IS2.policyImpact; 4.5 나비효과 안, owner 2026-11-07; contract docs/frontend_v2/POLICY_IMPACT_V1.md).
   The strict reader of Codex's policy-impact-view/1 envelope (#509 e0bb68dd: research/policy_impact/build.py) and the
   policy-impact/1 bundle inside it. Pure: no window, no request, no storage; runs in node as in the page.
   - validate(json) -> {ok:true, value} (deep-frozen copy) or {ok:false, code, path}: the whole file is refused at its first fault,
     never partly shown. The envelope's exact keys; the bundle field by field as Codex's contract.py checks it (exact keys at every
     level, enums, UTC times, dates with their precision, https links without credentials, content hashes, unique revision keys,
     every reference resolved in the file, independent review records); current_policy_revisions naming one present revision
     of every policy and nothing else; and the screen's public boundary: no UNREVIEWED record, no CANDIDATE exposure, effects
     NONE, historical_pit_eligible false, an exposure or hypothesis on a non-current revision only as REVIEW_REQUIRED, a
     synthetic file only with reserved test-domain links.
   - view(value) NEVER selects a revision, an availability time or a review state: the current revision of a policy is the one
     current_policy_revisions names; older revisions, the order of the list, REVIEW_REQUIRED and freshness.review_due are the
     engine's output as delivered. view only indexes it (by policy, by source key) for the screen.
   - list(view, filters) keeps the engine's policy order; filters are type / jurisdiction / status / company, from values present
     in the file. Nothing is scored, ranked, weighed or netted.
   - status(view, revision): the file's lifecycle status; with the bundle reason HISTORICAL_CASES_CURRENT_STATE_UNVERIFIED it is
     read 역사 사례 · 현재 상태 미확인. A date never changes a status here.
   - forCompany(view, id): the 관련 정책 summary of a company page. newsLinks(view): NEWS_REFERENCE url -> policies citing it. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else{const I=root.IS2=root.IS2||{};I.policyImpact=api;}})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
const VIEW_SCHEMA='policy-impact-view/1',SCHEMA='policy-impact/1',FILE='policy-impact.json';
const E=Object.freeze({
 data_kind:['SYNTHETIC','REAL_REVIEWED'],policy_type:['TARIFF','EXPORT_CONTROL','INDUSTRIAL_SUBSIDY'],
 lifecycle_status:['STATEMENT','PROPOSED','ADOPTED','EFFECTIVE','SUSPENDED','WITHDRAWN','EXPIRED','UNKNOWN'],
 review_status:['UNREVIEWED','REVIEWED','REVIEW_REQUIRED'],kind:['OFFICIAL_RULE','OFFICIAL_RELEASE','COMPANY_FILING','NEWS_REFERENCE'],
 verification_status:['VERIFIED','SOURCE_UNVERIFIED','CONFLICTING_EVIDENCE'],subsidy_stage:['PRELIMINARY_TERMS','FINAL_AWARD','DISBURSEMENT_CONFIRMED','UNKNOWN'],
 exposure_type:['REVENUE_REGION','PRODUCTION_SITE','PROCUREMENT','CONTROLLED_PRODUCT','SUBSIDY_PROJECT'],evidence_status:['DOCUMENTED','CANDIDATE','UNKNOWN'],
 policy_applicability:['DOCUMENTED','UNCONFIRMED','OUTSIDE_SCOPE'],epistemic_status:['SUPPORTED_FACT','HYPOTHESIS','UNKNOWN'],
 watch_kind:['MACRO_SERIES','COMPANY_DISCLOSURE','POLICY_UPDATE'],precision:['DATETIME','DATE','UNKNOWN'],
 identity_method:['ISSUER_DOCUMENT_VERIFIED_RELATION','ISSUER_OFFICIAL_URL'],review_method:['AI_INDEPENDENT_SOURCE_CHECK','HUMAN_SOURCE_CHECK'],
 review_group:['policies','exposures','hypotheses'],refresh_mode:['MANUAL_REVIEW','AUTOMATED'],
 refresh_result:['UPDATED','NO_NEW_ITEMS','PARTIAL_FAILED','FAILED','NOT_RUN','INCOMPLETE']});
const KEYS=Object.freeze({
 view:['query_timezone','schema_version','bundle','current_policy_revisions','as_of','historical_pit_eligible'],
 top:['schema_version','bundle_id','generated_at','data_kind','policy_as_of','score_effect','gate_effect','scope','sources','policies','exposures','hypotheses','refresh','reason_codes','historical_pit_eligible','freshness','review_records'],
 scope:['policy_types','jurisdictions','source_scope','coverage_kind'],
 sources:['source_id','source_revision_id','kind','publisher','url','title','document_id','published','first_seen_at','acquired_at','revision_acquired_at','verification_status','evidence_locator','content_sha256','data_kind'],
 policies:['policy_id','revision_id','supersedes_revision_id','policy_type','title','issuer','jurisdiction','target_regions','scope_description','lifecycle_status','published','effective_from','effective_to','evidence_refs','recorded_at','change_recorded_at','reviewed_at','review_status','next_review_on','identity_basis','subsidy_stage','parent_policy_id','data_kind'],
 exposures:['exposure_id','exposure_revision_id','company_id','policy_id','policy_revision_id','exposure_type','evidence_status','policy_applicability','description','period','evidence_refs','recorded_at','reviewed_at','review_status','ratio','reason_codes','data_kind'],
 hypotheses:['hypothesis_id','hypothesis_revision_id','policy_id','policy_revision_id','company_ids','exposure_refs','claim','steps','conditions','counter_conditions','watch_items','created_at','recorded_at','reviewed_at','review_status','data_kind'],
 identity:['method','issuer','document_id','relation_evidence_refs'],ratio:['value','unit','denominator_description','period','scope'],period:['start','end'],
 step:['text','epistemic_status','evidence_refs'],watch:['kind','reference_id','rationale','availability'],eref:['exposure_id','exposure_revision_id'],
 ref:['source_id','source_revision_id','locator','claim'],temporal:['value','precision','timezone'],
 review:['group','id','revision_id','reviewed_at','recorded_at','reviewer','author','method','evidence_refs'],
 refresh:['mode','result','last_attempt_at','last_success_at','last_manual_review_at','retained_bundle_id','retained_policy_as_of','sources','incomplete_ranges'],
 freshness:['last_source_check_at','last_reviewed_at','review_due','reason_codes']});
const RKEY=Object.freeze({sources:['source_id','source_revision_id'],policies:['policy_id','revision_id'],exposures:['exposure_id','exposure_revision_id'],hypotheses:['hypothesis_id','hypothesis_revision_id']});
// Screen words (Korean).
const TYPE_TEXT=Object.freeze({TARIFF:'관세',EXPORT_CONTROL:'수출통제',INDUSTRIAL_SUBSIDY:'산업 보조금'});
const STATUS_TEXT=Object.freeze({STATEMENT:'발언·성명',PROPOSED:'제안',ADOPTED:'채택',EFFECTIVE:'시행(근거 확인)',SUSPENDED:'유예',WITHDRAWN:'철회',EXPIRED:'만료',UNKNOWN:'현재 상태 미확인'});
const REVIEW_TEXT=Object.freeze({REVIEWED:'검토됨',REVIEW_REQUIRED:'이전 분석 · 재검토 필요',UNREVIEWED:'미검토'});
const STAGE_TEXT=Object.freeze({PRELIMINARY_TERMS:'예비 조건 · 지급 아님',FINAL_AWARD:'확정 지원 발표 · 실제 지급 아님(지급 미확인)',DISBURSEMENT_CONFIRMED:'지급 확인',UNKNOWN:'지원 단계 미확인'});
const EXPOSURE_TEXT=Object.freeze({REVENUE_REGION:'지역 매출',PRODUCTION_SITE:'생산 거점',PROCUREMENT:'조달',CONTROLLED_PRODUCT:'통제 대상 제품',SUBSIDY_PROJECT:'보조금 프로젝트'});
const EVIDENCE_TEXT=Object.freeze({DOCUMENTED:'노출 근거 확인',CANDIDATE:'후보',UNKNOWN:'노출 근거 없음 · 확인 필요'});
const APPLY_TEXT=Object.freeze({DOCUMENTED:'정책 적용 근거 확인',UNCONFIRMED:'정책 적용 미확인',OUTSIDE_SCOPE:'정책 적용 범위 밖'});
const EPI_TEXT=Object.freeze({SUPPORTED_FACT:'확인된 사실',HYPOTHESIS:'가설',UNKNOWN:'모름'});
const KIND_TEXT=Object.freeze({OFFICIAL_RULE:'공식 규칙',OFFICIAL_RELEASE:'공식 발표',COMPANY_FILING:'기업 공시',NEWS_REFERENCE:'뉴스 참조'});
const VERIFY_TEXT=Object.freeze({VERIFIED:'원문 확인',SOURCE_UNVERIFIED:'원문 미확인',CONFLICTING_EVIDENCE:'근거 충돌'});
const WATCH_TEXT=Object.freeze({MACRO_SERIES:'4.1 공개 지표',COMPANY_DISCLOSURE:'기업 공시',POLICY_UPDATE:'정책 갱신'});
const AVAIL_TEXT=Object.freeze({PUBLIC_REFERENCE:'공개 참조',UNAVAILABLE:'공개 불가 · 숫자는 옮기지 않음'});
const METHOD_TEXT=Object.freeze({AI_INDEPENDENT_SOURCE_CHECK:'AI 독립 원문 대조 · 사람 검토 아님',HUMAN_SOURCE_CHECK:'사람 원문 대조'});
const KIND_DATA_TEXT=Object.freeze({SYNTHETIC:'합성 · 시험용',REAL_REVIEWED:'실자료 · 검토 기록 있음'});
const REFRESH_TEXT=Object.freeze({UPDATED:'갱신됨',NO_NEW_ITEMS:'새 문서 없음',PARTIAL_FAILED:'일부 원천 갱신 실패 · 마지막 정상본 유지',FAILED:'갱신 실패 · 마지막 정상본 유지',NOT_RUN:'자동 갱신 실행 전',INCOMPLETE:'갱신 불완전 · 미조회 구간 있음'});
const REASON_TEXT=Object.freeze({
 HISTORICAL_CASES_CURRENT_STATE_UNVERIFIED:'역사 사례 · 현재 상태 미확인',LEGAL_PDF_NOT_CHECKED:'법적 효력 PDF 원문 미확인(웹 게시본 기준)',
 NOT_MARKET_COVERAGE:'선별 사례 · 시장 전체 범위 아님',CURRENT_POLICY_STATUS_UNCONFIRMED:'현재 정책 상태 미확인',MANUAL_REVIEW_ONLY:'수동 검토만 · 자동 갱신 없음',
 POLICY_CHECK_NOT_AVAILABLE_AT_QUERY:'이 조회 시점의 정책 확인 기록 없음',SOURCE_CHECK_HISTORY_UNAVAILABLE_AT_QUERY:'이 조회 시점의 원천 확인 이력 없음',
 REFRESH_HISTORY_UNAVAILABLE_AT_QUERY:'이 조회 시점의 갱신 이력 없음',RATIO_NOT_DISCLOSED:'비율 미공시',RATIO_NOT_APPLICABLE:'비율 해당 없음',
 RATIO_NOT_ESTABLISHED:'비율 미확정',CURRENT_DISBURSEMENT_UNCONFIRMED:'현재 지급 미확인'});
const HISTORICAL='HISTORICAL_CASES_CURRENT_STATE_UNVERIFIED';
const own=(m,k)=>Object.prototype.hasOwnProperty.call(m,k);
const t=(map,code)=>code===null||code===undefined?'':own(map,code)?map[code]:String(code);

const object=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
const MAX_TEXT=4000,MAX_LIST=5000,ID=/^[A-Za-z0-9][A-Za-z0-9._:\-|]{0,159}$/,TZ=/^(UTC|[A-Za-z]+(?:\/[A-Za-z0-9_+\-]+){1,2})$/;
const STAMP=/^(\d{4}-\d{2}-\d{2})T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(Z|[+-]\d{2}:\d{2})$/,DAY=/^\d{4}-\d{2}-\d{2}$/,HEX=/^[0-9a-f]{64}$/;
class Fault extends Error{constructor(code,path){super(code);this.code=code;this.path=path;}}
const fail=(code,path)=>{throw new Fault(code,path);};
const need=(ok,code,path)=>{if(!ok)fail(code,path);};
function keys(o,want,path){if(!object(o))fail('TYPE',path);for(const k of want)if(!own(o,k))fail('KEY_MISSING',path+'.'+k);
 for(const k of Object.keys(o))if(!want.includes(k))fail('KEY_UNKNOWN',path+'.'+k);}
const text=(v,path,{nullable=false,max=MAX_TEXT}={})=>{if(v===null&&nullable)return;need(typeof v==='string'&&v.trim().length>0,'TEXT',path);need(v.length<=max,'TOO_LARGE',path);};
const id=(v,path,{nullable=false}={})=>{if(v===null&&nullable)return;need(typeof v==='string'&&ID.test(v),'ID',path);};
const en=(v,list,path,{nullable=false}={})=>{if(v===null&&nullable)return;need(E[list].includes(v),'ENUM',path);};
const real=s=>{const m=STAMP.exec(s);return m&&Number.isFinite(Date.parse(s))&&new Date(m[1]+'T00:00:00Z').toISOString().slice(0,10)===m[1];};
// Actual instants are UTC (Codex contract time(): offset zero), any precision up to microseconds.
function utc(v,path,{nullable=false}={}){if(v===null&&nullable)return;need(typeof v==='string'&&real(v),'TIME',path);const z=STAMP.exec(v)[2];need(z==='Z'||z==='+00:00','UTC_REQUIRED',path);}
function day(v,path,{nullable=false}={}){if(v===null&&nullable)return;need(typeof v==='string'&&DAY.test(v)&&Number.isFinite(Date.parse(v+'T00:00:00Z'))&&new Date(v+'T00:00:00Z').toISOString().slice(0,10)===v,'DATE',path);}
// {value, precision, timezone}: DATE stays a date (never a midnight), DATETIME carries an offset, UNKNOWN has no value.
function temporal(v,path){keys(v,KEYS.temporal,path);en(v.precision,'precision',path+'.precision');if(v.timezone!==null)text(v.timezone,path+'.timezone',{max:64});
 if(v.precision==='UNKNOWN')need(v.value===null&&v.timezone===null,'PRECISION',path);
 else if(v.precision==='DATE'){day(v.value,path+'.value');need(v.timezone===null,'DATE_TIMEZONE',path);}
 else need(typeof v.value==='string'&&real(v.value),'TIME',path+'.value');}
function arr(v,path,{min=0}={}){need(Array.isArray(v),'ARRAY',path);need(v.length<=MAX_LIST,'TOO_LARGE',path);need(v.length>=min,'EMPTY',path);}
const texts=(v,path,{max=500}={})=>{arr(v,path);v.forEach((x,i)=>text(x,path+'['+i+']',{max}));};
function url(v,path){need(typeof v==='string'&&v.length<=2048,'UNSAFE_URL',path);let u=null;try{u=new URL(v);}catch(_){u=null;}
 need(u&&u.protocol==='https:'&&u.hostname&&!u.username&&!u.password,'UNSAFE_URL',path);}
// Reserved documentation / test domains (RFC 2606, RFC 6761) are never links: a synthetic file uses only these.
const RESERVED=/(^|\.)(example\.(com|net|org)|example|invalid|test|localhost)$/;
const linkable=v=>{try{const u=new URL(v);return u.protocol==='https:'&&!RESERVED.test(u.hostname)&&!u.username&&!u.password;}catch(_){return false;}};
const copyFreeze=v=>{const c=JSON.parse(JSON.stringify(v));(function f(x){if(x&&typeof x==='object'){Object.freeze(x);for(const y of Object.values(x))f(y);}})(c);return c;};
const kpair=(a,b)=>a+'\u0000'+b;
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);

function check(j){
 keys(j,KEYS.view,'$');need(j.schema_version===VIEW_SCHEMA,'VIEW_VERSION','$.schema_version');need(typeof j.query_timezone==='string'&&TZ.test(j.query_timezone),'TIMEZONE','$.query_timezone');
 utc(j.as_of,'$.as_of');need(j.historical_pit_eligible===false,'PIT_UNPROVEN','$.historical_pit_eligible');
 const b=j.bundle,B='$.bundle';keys(b,KEYS.top,B);need(b.schema_version===SCHEMA,'VERSION',B+'.schema_version');
 need(b.score_effect==='NONE','FORBIDDEN_EFFECT',B+'.score_effect');need(b.gate_effect==='NONE','FORBIDDEN_EFFECT',B+'.gate_effect');
 need(b.historical_pit_eligible===false,'PIT_UNPROVEN',B+'.historical_pit_eligible');en(b.data_kind,'data_kind',B+'.data_kind');text(b.bundle_id,B+'.bundle_id',{max:200});
 utc(b.generated_at,B+'.generated_at');utc(b.policy_as_of,B+'.policy_as_of',{nullable:true});
 keys(b.scope,KEYS.scope,B+'.scope');need(b.scope.coverage_kind==='CURATED_SAMPLE','COVERAGE',B+'.scope.coverage_kind');
 for(const k of ['policy_types','jurisdictions','source_scope'])texts(b.scope[k],B+'.scope.'+k,{max:120});b.scope.policy_types.forEach((x,i)=>en(x,'policy_type',B+'.scope.policy_types['+i+']'));
 texts(b.reason_codes,B+'.reason_codes',{max:120});
 // records, keyed as Codex keys them (id, revision)
 const ix={};
 for(const g of Object.keys(RKEY)){arr(b[g],B+'.'+g);const m=new Map();
  b[g].forEach((r,i)=>{const p=B+'.'+g+'['+i+']';keys(r,KEYS[g],p);need(r.data_kind===b.data_kind,'MIXED_KIND',p+'.data_kind');
   const [a,c]=RKEY[g];id(r[a],p+'.'+a);id(r[c],p+'.'+c);const k=kpair(r[a],r[c]);need(!m.has(k),'DUPLICATE_REVISION',p);m.set(k,r);});
  ix[g]=m;}
 const refs=(list,p,{min=1}={})=>{arr(list,p,{min});list.forEach((x,i)=>{const q=p+'['+i+']';keys(x,KEYS.ref,q);id(x.source_id,q+'.source_id');id(x.source_revision_id,q+'.source_revision_id');
  need(ix.sources.has(kpair(x.source_id,x.source_revision_id)),'SOURCE_REF',q);text(x.locator,q+'.locator',{max:400});text(x.claim,q+'.claim',{max:1000});});};
 b.sources.forEach((s,i)=>{const p=B+'.sources['+i+']';en(s.kind,'kind',p+'.kind');text(s.publisher,p+'.publisher',{max:300});url(s.url,p+'.url');text(s.title,p+'.title',{max:1000});
  text(s.document_id,p+'.document_id',{nullable:true,max:200});temporal(s.published,p+'.published');utc(s.first_seen_at,p+'.first_seen_at',{nullable:true});
  utc(s.acquired_at,p+'.acquired_at');utc(s.revision_acquired_at,p+'.revision_acquired_at');need(Date.parse(s.acquired_at)<=Date.parse(s.revision_acquired_at),'SOURCE_TIME_ORDER',p);
  en(s.verification_status,'verification_status',p+'.verification_status');text(s.evidence_locator,p+'.evidence_locator',{max:400});need(typeof s.content_sha256==='string'&&HEX.test(s.content_sha256),'SOURCE_HASH',p+'.content_sha256');
  if(b.data_kind==='SYNTHETIC')need(!linkable(s.url),'SYNTHETIC_REAL_LINK',p+'.url');});
 const policyIds=new Set(b.policies.map(x=>x.policy_id));
 b.policies.forEach((x,i)=>{const p=B+'.policies['+i+']';en(x.policy_type,'policy_type',p+'.policy_type');text(x.title,p+'.title',{max:500});text(x.issuer,p+'.issuer',{max:300});
  text(x.jurisdiction,p+'.jurisdiction',{max:120});texts(x.target_regions,p+'.target_regions',{max:120});text(x.scope_description,p+'.scope_description');en(x.lifecycle_status,'lifecycle_status',p+'.lifecycle_status');
  for(const k of ['published','effective_from','effective_to'])temporal(x[k],p+'.'+k);refs(x.evidence_refs,p+'.evidence_refs');
  for(const k of ['recorded_at','change_recorded_at'])utc(x[k],p+'.'+k);utc(x.reviewed_at,p+'.reviewed_at',{nullable:true});en(x.review_status,'review_status',p+'.review_status');
  day(x.next_review_on,p+'.next_review_on',{nullable:true});id(x.supersedes_revision_id,p+'.supersedes_revision_id',{nullable:true});id(x.parent_policy_id,p+'.parent_policy_id',{nullable:true});
  keys(x.identity_basis,KEYS.identity,p+'.identity_basis');en(x.identity_basis.method,'identity_method',p+'.identity_basis.method');
  need(x.identity_basis.issuer===x.issuer,'UNSTABLE_POLICY_ID',p+'.identity_basis.issuer');text(x.identity_basis.document_id,p+'.identity_basis.document_id',{nullable:true,max:200});
  need(x.identity_basis.document_id!==null||x.identity_basis.method==='ISSUER_OFFICIAL_URL','UNSTABLE_POLICY_ID',p+'.identity_basis.document_id');
  if(x.supersedes_revision_id!==null)need(ix.policies.has(kpair(x.policy_id,x.supersedes_revision_id)),'REVISION_REF',p+'.supersedes_revision_id');
  refs(x.identity_basis.relation_evidence_refs,p+'.identity_basis.relation_evidence_refs',{min:x.supersedes_revision_id!==null?1:0});
  if(x.parent_policy_id!==null)need(x.parent_policy_id!==x.policy_id&&policyIds.has(x.parent_policy_id),'PARENT_REF',p+'.parent_policy_id');
  need((x.policy_type==='INDUSTRIAL_SUBSIDY')===(x.subsidy_stage!==null),'SUBSIDY_STAGE',p+'.subsidy_stage');en(x.subsidy_stage,'subsidy_stage',p+'.subsidy_stage',{nullable:true});
  need(x.review_status!=='UNREVIEWED','UNREVIEWED_PUBLIC',p+'.review_status');});
 // one identity and one current revision per policy, named by the engine (never chosen here)
 const cur=j.current_policy_revisions;need(object(cur),'TYPE','$.current_policy_revisions');
 for(const [pid,rev] of Object.entries(cur)){id(pid,'$.current_policy_revisions');id(rev,'$.current_policy_revisions.'+pid);need(ix.policies.has(kpair(pid,rev)),'CURRENT_REF','$.current_policy_revisions.'+pid);}
 for(const pid of policyIds){need(own(cur,pid),'CURRENT_REF','$.current_policy_revisions.'+pid);
  const rows=b.policies.filter(x=>x.policy_id===pid);need(new Set(rows.map(x=>x.issuer+'\u0000'+x.policy_type+'\u0000'+x.jurisdiction)).size===1,'POLICY_IDENTITY_MUTATION','$.bundle.policies['+pid+']');}
 const isCurrent=(pid,rev)=>own(cur,pid)&&cur[pid]===rev;
 b.exposures.forEach((x,i)=>{const p=B+'.exposures['+i+']';id(x.company_id,p+'.company_id');need(ix.policies.has(kpair(x.policy_id,x.policy_revision_id)),'POLICY_REF',p);
  en(x.exposure_type,'exposure_type',p+'.exposure_type');en(x.evidence_status,'evidence_status',p+'.evidence_status');en(x.policy_applicability,'policy_applicability',p+'.policy_applicability');
  text(x.description,p+'.description');keys(x.period,KEYS.period,p+'.period');day(x.period.start,p+'.period.start',{nullable:true});day(x.period.end,p+'.period.end',{nullable:true});
  refs(x.evidence_refs,p+'.evidence_refs');utc(x.recorded_at,p+'.recorded_at');utc(x.reviewed_at,p+'.reviewed_at',{nullable:true});en(x.review_status,'review_status',p+'.review_status');
  texts(x.reason_codes,p+'.reason_codes',{max:120});
  if(x.ratio===null)need(x.reason_codes.length>0,'NULL_REASON',p+'.ratio');
  else{keys(x.ratio,KEYS.ratio,p+'.ratio');need(typeof x.ratio.value==='number'&&Number.isFinite(x.ratio.value)&&x.ratio.value>=0&&x.ratio.value<=1&&x.ratio.unit==='fraction','RATIO',p+'.ratio');
   need(same(x.ratio.period,x.period),'RATIO_SCOPE',p+'.ratio.period');text(x.ratio.scope,p+'.ratio.scope',{max:300});text(x.ratio.denominator_description,p+'.ratio.denominator_description',{max:300});}
  need(x.review_status!=='UNREVIEWED','UNREVIEWED_PUBLIC',p+'.review_status');need(x.evidence_status!=='CANDIDATE','CANDIDATE_PUBLIC',p+'.evidence_status');
  need(isCurrent(x.policy_id,x.policy_revision_id)||x.review_status==='REVIEW_REQUIRED','STALE_NOT_FLAGGED',p+'.review_status');});
 b.hypotheses.forEach((x,i)=>{const p=B+'.hypotheses['+i+']';need(ix.policies.has(kpair(x.policy_id,x.policy_revision_id)),'POLICY_REF',p);
  arr(x.company_ids,p+'.company_ids',{min:1});x.company_ids.forEach((c,k)=>id(c,p+'.company_ids['+k+']'));
  arr(x.exposure_refs,p+'.exposure_refs');x.exposure_refs.forEach((r,k)=>{const q=p+'.exposure_refs['+k+']';keys(r,KEYS.eref,q);const e=ix.exposures.get(kpair(r.exposure_id,r.exposure_revision_id));
   need(e&&x.company_ids.includes(e.company_id)&&e.policy_id===x.policy_id&&e.policy_revision_id===x.policy_revision_id,'EXPOSURE_REF',q);});
  text(x.claim,p+'.claim',{max:1000});arr(x.steps,p+'.steps',{min:1});
  x.steps.forEach((s,k)=>{const q=p+'.steps['+k+']';keys(s,KEYS.step,q);text(s.text,q+'.text',{max:1000});en(s.epistemic_status,'epistemic_status',q+'.epistemic_status');
   refs(s.evidence_refs,q+'.evidence_refs',{min:s.epistemic_status==='SUPPORTED_FACT'?1:0});});
  arr(x.conditions,p+'.conditions',{min:1});arr(x.counter_conditions,p+'.counter_conditions',{min:1});texts(x.conditions,p+'.conditions');texts(x.counter_conditions,p+'.counter_conditions');
  arr(x.watch_items,p+'.watch_items');x.watch_items.forEach((w,k)=>{const q=p+'.watch_items['+k+']';keys(w,KEYS.watch,q);en(w.kind,'watch_kind',q+'.kind');
   text(w.reference_id,q+'.reference_id',{max:200});text(w.rationale,q+'.rationale',{max:500});id(w.availability,q+'.availability');});
  utc(x.created_at,p+'.created_at');utc(x.recorded_at,p+'.recorded_at');utc(x.reviewed_at,p+'.reviewed_at',{nullable:true});en(x.review_status,'review_status',p+'.review_status');
  need(x.review_status!=='UNREVIEWED','UNREVIEWED_PUBLIC',p+'.review_status');
  need(isCurrent(x.policy_id,x.policy_revision_id)||x.review_status==='REVIEW_REQUIRED','STALE_NOT_FLAGGED',p+'.review_status');});
 arr(b.review_records,B+'.review_records');b.review_records.forEach((r,i)=>{const p=B+'.review_records['+i+']';keys(r,KEYS.review,p);en(r.group,'review_group',p+'.group');
  text(r.id,p+'.id',{max:200});text(r.revision_id,p+'.revision_id',{max:200});need(ix[r.group].has(kpair(r.id,r.revision_id)),'REVIEW_REF',p);
  text(r.reviewer,p+'.reviewer',{max:200});text(r.author,p+'.author',{max:200});need(r.reviewer!==r.author,'INDEPENDENT_REVIEW',p+'.reviewer');en(r.method,'review_method',p+'.method');
  utc(r.reviewed_at,p+'.reviewed_at');utc(r.recorded_at,p+'.recorded_at');refs(r.evidence_refs,p+'.evidence_refs');});
 const f=b.freshness;keys(f,KEYS.freshness,B+'.freshness');utc(f.last_source_check_at,B+'.freshness.last_source_check_at',{nullable:true});utc(f.last_reviewed_at,B+'.freshness.last_reviewed_at',{nullable:true});
 need(f.review_due===null||typeof f.review_due==='boolean','BOOLEAN',B+'.freshness.review_due');texts(f.reason_codes,B+'.freshness.reason_codes',{max:120});
 // refresh: attempt, success and manual review are separate; manual review never claims an automated run.
 const refresh=(r,p,depth)=>{need(depth<=3,'TOO_LARGE',p);keys(r,KEYS.refresh,p);en(r.mode,'refresh_mode',p+'.mode');
  if(r.mode==='MANUAL_REVIEW')need(r.result===null&&r.last_attempt_at===null&&r.last_success_at===null,'MANUAL_NOT_AUTO',p);else en(r.result,'refresh_result',p+'.result');
  for(const k of ['last_attempt_at','last_success_at','last_manual_review_at','retained_policy_as_of'])utc(r[k],p+'.'+k,{nullable:true});
  text(r.retained_bundle_id,p+'.retained_bundle_id',{nullable:true,max:200});texts(r.incomplete_ranges,p+'.incomplete_ranges',{max:200});
  if(r.result==='INCOMPLETE')need(r.incomplete_ranges.length>0,'INCOMPLETE_RANGE',p+'.incomplete_ranges');
  arr(r.sources,p+'.sources');r.sources.forEach((s,i)=>refresh(s,p+'.sources['+i+']',depth+1));};
 refresh(b.refresh,B+'.refresh',0);
}
function validate(json){try{if(typeof json==='string')return {ok:false,code:'TYPE',path:'$'};check(json);return {ok:true,value:copyFreeze(json)};}
 catch(e){if(e instanceof Fault)return {ok:false,code:e.code,path:e.path};return {ok:false,code:'INVALID',path:'$'};}}

// ---- view: an index of the engine's output. No revision is chosen, no time compared, no review state set here.
function view(v){const b=v.bundle,cur=v.current_policy_revisions,src=new Map(b.sources.map(s=>[kpair(s.source_id,s.source_revision_id),s]));
 const policies=new Map();
 for(const r of b.policies){if(!policies.has(r.policy_id))policies.set(r.policy_id,{policy_id:r.policy_id,current:null,revisions:[],older:[],exposures:[],hypotheses:[],children:[],parent:null});
  const p=policies.get(r.policy_id);p.revisions.push(r);if(r.revision_id===cur[r.policy_id])p.current=r;else p.older.push(r);}
 for(const p of policies.values())p.parent=p.current.parent_policy_id;
 for(const p of policies.values())if(p.parent&&policies.has(p.parent))policies.get(p.parent).children.push(p.policy_id);
 for(const e of b.exposures)policies.get(e.policy_id).exposures.push(e);
 for(const x of b.hypotheses)policies.get(x.policy_id).hypotheses.push(x);
 const reviews=new Map();for(const r of b.review_records){const k=r.group+'\u0000'+kpair(r.id,r.revision_id);if(!reviews.has(k))reviews.set(k,[]);reviews.get(k).push(r);}
 // the list keeps the engine's order: the position of each policy's current revision in bundle.policies
 const order=b.policies.filter(r=>r.revision_id===cur[r.policy_id]).map(r=>policies.get(r.policy_id));
 return {data_kind:b.data_kind,bundle_id:b.bundle_id,as_of:v.as_of,query_timezone:v.query_timezone,policy_as_of:b.policy_as_of,generated_at:b.generated_at,scope:b.scope,
  refresh:b.refresh,freshness:b.freshness,reason_codes:b.reason_codes,historical:b.reason_codes.includes(HISTORICAL),policies,order,sources:src,reviews};}
const source=(vw,ref)=>vw.sources.get(kpair(ref.source_id,ref.source_revision_id))||null;
const reviewsOf=(vw,group,idv,rev)=>vw.reviews.get(group+'\u0000'+kpair(idv,rev))||[];
function status(vw,r){const s={code:r.lifecycle_status,text:STATUS_TEXT[r.lifecycle_status],historical:false};
 if(vw.historical&&r.lifecycle_status==='UNKNOWN'){s.text=REASON_TEXT[HISTORICAL];s.historical=true;}return s;}
function facets(vw){const f={type:new Set(),jurisdiction:new Set(),status:new Set(),company:new Set()};
 for(const p of vw.order){f.type.add(p.current.policy_type);f.jurisdiction.add(p.current.jurisdiction);f.status.add(p.current.lifecycle_status);
  for(const e of p.exposures)f.company.add(e.company_id);for(const x of p.hypotheses)for(const c of x.company_ids)f.company.add(c);}
 return Object.fromEntries(Object.entries(f).map(([k,s])=>[k,[...s].sort()]));}
function list(vw,{type=null,jurisdiction=null,status:st=null,company=null}={}){
 return vw.order.filter(p=>(!type||p.current.policy_type===type)&&(!jurisdiction||p.current.jurisdiction===jurisdiction)&&(!st||p.current.lifecycle_status===st)&&
  (!company||p.exposures.some(e=>e.company_id===company)||p.hypotheses.some(x=>x.company_ids.includes(company))));}
function get(vw,policyId,revisionId=null){const p=vw.policies.get(policyId);if(!p)return null;if(revisionId===null)return {...p,shown:p.current};
 const r=p.revisions.find(x=>x.revision_id===revisionId);return r?{...p,shown:r}:null;}
function forCompany(vw,companyId){const ps=list(vw,{company:companyId});if(!ps.length)return null;let documented=0,confirm=0,old=0,last=null;
 for(const p of ps)for(const e of p.exposures.filter(e=>e.company_id===companyId)){
  if(e.review_status==='REVIEW_REQUIRED')old++;else if(e.evidence_status==='DOCUMENTED'&&e.policy_applicability==='DOCUMENTED')documented++;else confirm++;
  if(e.reviewed_at&&(!last||Date.parse(e.reviewed_at)>Date.parse(last)))last=e.reviewed_at;}
 return {policies:ps.map(p=>({policy_id:p.policy_id,title:p.current.title,type:p.current.policy_type})),documented,confirm,old,last_reviewed_at:last};}
function newsLinks(vw){const out=new Map();
 for(const p of vw.order){const rs=[...p.revisions.flatMap(r=>r.evidence_refs),...p.exposures.flatMap(e=>e.evidence_refs),...p.hypotheses.flatMap(x=>x.steps.flatMap(s=>s.evidence_refs))];
  for(const r of rs){const s=source(vw,r);if(s&&s.kind==='NEWS_REFERENCE'){if(!out.has(s.url))out.set(s.url,[]);if(!out.get(s.url).includes(p.policy_id))out.get(s.url).push(p.policy_id);}}}
 return out;}

return Object.freeze({VIEW_SCHEMA,SCHEMA,FILE,ENUMS:E,TYPE_TEXT,STATUS_TEXT,REVIEW_TEXT,STAGE_TEXT,EXPOSURE_TEXT,EVIDENCE_TEXT,APPLY_TEXT,EPI_TEXT,KIND_TEXT,VERIFY_TEXT,
 WATCH_TEXT,AVAIL_TEXT,METHOD_TEXT,KIND_DATA_TEXT,REFRESH_TEXT,REASON_TEXT,
 text:t,linkable,validate,view,source,reviewsOf,status,facets,list,get,forCompany,newsLinks});
});
