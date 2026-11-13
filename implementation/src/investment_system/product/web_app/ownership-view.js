/* Company relationship reader (IS2.ownershipView; 5.1.1 기업 중심 관계 · 5.1.2 연결 근거 and the company detail's 관계 칸; owner
   2026-11-11 「Main_QGV_Relationship_Queue」 and 「#530 후속」 §4). Reads Codex #531's company-ownership-view/1 (CONTRACT.md
   e057973c…, synthetic.json 4946549b…) as delivered: one view per centre company (entity_context), its relationships in the
   producer's direction (holder → investee, stated parent → subsidiary) with relative_direction OUTGOING / INCOMING for the centre.
   Nothing is inferred, summed, averaged, looked through or filled here; validate / view are pure and run in node as in the page.
   - Four lists kept apart (never one "related companies" list): 모회사 (PARENT_SUBSIDIARY, centre = subsidiary), 자회사
     (PARENT_SUBSIDIARY, centre = parent), 보유 지분 (OWNERSHIP, the centre holds), 주주 (OWNERSHIP, holds the centre). Parent /
     subsidiary is a stated fact independent of any percentage; a percentage never makes a parent. 13F investment discretion
     (capacity INVESTMENT_DISCRETION) is its own list and is never own equity, a parent or a subsidiary.
   - Direct / indirect / unknown, share capital and voting power, each observation's denominator basis, class and date stay apart.
     A percentage is the producer's decimal string with its qualifier; 0 is an observation (not a holding, not an end).
   - States kept apart: no data collected / partial review (확인된 n개 · 전체 목록 미확인) / not found in the reviewed scope (not a
     confirmed none) / confirmed none in the reviewed scope / the chosen kind is empty while others exist / last refresh failed
     (the previous good data shown) / conflict / review required (validity on the query date unconfirmed).
   - A counterparty that is not an existing entity (an unresolved mention) is named as written with 「목록에 없는 대상 · 기업 페이지
     없음」; no page or company is made for it. The same relationship_id is read from either side (the producer stores one fact).
   - The relationship denominator and coverage are unknown (null): no coverage, ratio or 95% line is made for relationships. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else{const I=root.IS2=root.IS2||{};I.ownershipView=api;}})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
const SCHEMA='company-ownership-view/1';
const TOP=['collection','collection_state','confirmed_paths','counts','dataset_hash','dataset_id','dataset_version','diagnostics','entities','entity_context',
 'evidence','generated_at','historical_system_pit','identity_context','mentions','pit_reason','publication','query_as_of','query_mode','relationship_coverage',
 'relationship_denominator','relationships','schema_version','unresolved_assertions'];
const REL_KEYS=['assertions','capacity','direction','directness','history','observations','positive_ownership','relationship_id','relative_direction',
 'source_entity_id','state','target_entity_id','temporal','type','validity_status','version'];
const ASSERTION_KEYS=['assertion_id','capacity','directness','evidence_ids','observations','previous_version','publication','source_entity_id','source_mention_id',
 'statement','status','target_entity_id','target_mention_id','temporal','type','version'];
const OBS_KEYS=['denominator_basis','lower','metric','missing_reason','observation_id','observed_as_of','qualifier','security_id','share_class','unit','upper','value'];
const TEMPORAL_KEYS=['observed_on','reviewed_at','system_known_at','valid_from','valid_to'];
const ENTITY_KEYS=['company_ids','display_name','entity_id','identity_ref','identity_status','kind','node_id','publication'];
const TYPE=Object.freeze(['OWNERSHIP','PARENT_SUBSIDIARY']);
const DIRECTNESS=Object.freeze({DIRECT:'직접',INDIRECT:'간접',UNKNOWN:'직접·간접 미확인'});
const CAPACITY=Object.freeze({CORPORATE_INVESTMENT:'회사 투자',LEGAL_OWNERSHIP:'법적 소유',BENEFICIAL_OWNERSHIP:'실질 소유',
 INVESTMENT_DISCRETION:'운용 재량(13F) · 자기 지분 아님',UNKNOWN:'보유 성격 미확인'});
const STATE=Object.freeze({VERIFIED:'확인됨',COMPLETED:'완료 확인',PLANNED:'예정(완료 확인 전)',DISPOSED:'처분 확인',CONFLICT:'자료 충돌 · 값을 고르지 않음',
 REVIEW_REQUIRED:'재검토 필요 · 조회일 유효성 미확인',UNREVIEWED:'검토 전'});
const METRIC=Object.freeze({SHARE_CAPITAL:'지분율',VOTING_POWER:'의결권',MANAGED_HOLDINGS:'운용 보유'});
const QUALIFIER=Object.freeze({EXACT:'',APPROX:'약 ',RANGE:'범위 ',AT_LEAST:'이상 ',AT_MOST:'이하 ',NOT_DISCLOSED:'미공개'});
const BASIS=Object.freeze({CLASS_OUTSTANDING:'해당 주식 종류 발행주식 기준',VOTING_RIGHTS:'의결권 기준'});
// collection_state words: none of them is turned into another; only VERIFIED_ZERO_IN_SCOPE is a confirmed none, and only in scope.
const COLLECTION=Object.freeze({
 NOT_COLLECTED:'관계 자료 없음 · 수집 전 · 관계가 없다는 뜻이 아님',
 PARTIAL_REVIEW:'일부 검토',
 NOT_FOUND_IN_REVIEWED_SCOPE:'검토한 범위에서 찾지 못함 · 관계 없음 확인이 아님',
 VERIFIED_ZERO_IN_SCOPE:'검토한 범위에서 관계 없음 확인 · 그 범위 밖은 모름',
 FILTER_EMPTY:'고른 종류에 해당 없음 · 다른 종류의 관계는 있음',
 // Codex #531 b53b0ec0 (CONTRACT.md 4fc9f07c…): the sixth state. Complete within the declared scope only; no whole-market claim.
 REVIEWED_SCOPE:'검토한 범위는 검토 완료 · 그 범위 밖은 모름 · 전체 관계 완결 아님'});
// A centre without its own review (NOT_COLLECTED) can still carry relationships that another centre's reviewed evidence states about
// it (INCOMING only): the review state and the evidence state are then two lines, never one "관계 자료 없음".
const NOT_REVIEWED_WITH_INCOMING='이 기업 자체 검토 전 · 관계가 없다는 뜻이 아님';
const LISTS=Object.freeze([['parents','모회사'],['subsidiaries','자회사'],['holdings','보유 지분 (이 기업이 보유)'],['holders','주주 (이 기업을 보유)'],['discretion','운용 재량(13F) · 자기 지분 아님']]);
const DEC=/^(?:0|[1-9]\d{0,2})(?:\.\d{1,12})?$/;

const CHECKED=new WeakSet();
class Refusal extends Error{constructor(code,path){super(code);this.code=code;this.path=path;}}
const refuse=(code,path)=>{throw new Refusal(code,path);};
const isObj=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
const own=(o,k)=>Object.prototype.hasOwnProperty.call(o,k);
function exact(o,keys,at){if(!isObj(o))refuse('TYPE',at);for(const k of keys)if(!own(o,k))refuse('KEY_MISSING',at+'.'+k);
 for(const k of Object.keys(o))if(!keys.includes(k))refuse('KEY_UNEXPECTED',at+'.'+k);}
const str=v=>typeof v==='string'&&v.length>0;
const optStr=v=>v===null||str(v);
const dec=v=>v===null||(typeof v==='string'&&DEC.test(v)&&Number(v)>=0&&Number(v)<=100);
function freeze(o){if(o&&typeof o==='object'&&!Object.isFrozen(o)){Object.freeze(o);for(const v of Object.values(o))freeze(v);}return o;}

function temporal(t,at){exact(t,TEMPORAL_KEYS,at);for(const k of TEMPORAL_KEYS)if(!optStr(t[k]))refuse('TYPE',at+'.'+k);}
function observation(o,at){exact(o,OBS_KEYS,at);
 if(!own(METRIC,o.metric))refuse('METRIC',at+'.metric');if(!own(QUALIFIER,o.qualifier))refuse('QUALIFIER',at+'.qualifier');if(o.unit!=='PERCENT')refuse('UNIT',at+'.unit');
 for(const k of['value','lower','upper'])if(!dec(o[k]))refuse('DECIMAL',at+'.'+k);
 if(o.qualifier==='NOT_DISCLOSED'?(o.value!==null||!str(o.missing_reason)):o.qualifier==='RANGE'?(o.lower===null||o.upper===null):o.value===null)refuse('QUALIFIER',at+'.qualifier');
 for(const k of['observation_id','denominator_basis','observed_as_of'])if(!str(o[k]))refuse('TYPE',at+'.'+k);
 for(const k of['security_id','share_class','missing_reason'])if(!optStr(o[k]))refuse('TYPE',at+'.'+k);}
function assertion(a,at){exact(a,ASSERTION_KEYS,at);if(!TYPE.includes(a.type))refuse('TYPE_UNKNOWN',at+'.type');
 if(!own(DIRECTNESS,a.directness))refuse('DIRECTNESS',at+'.directness');if(!own(CAPACITY,a.capacity))refuse('CAPACITY',at+'.capacity');
 if(a.capacity==='INVESTMENT_DISCRETION'&&a.type!=='OWNERSHIP')refuse('13F_CAPACITY',at+'.capacity');
 if(!Array.isArray(a.observations))refuse('TYPE',at+'.observations');a.observations.forEach((o,i)=>observation(o,at+'.observations['+i+']'));
 temporal(a.temporal,at+'.temporal');}

// The view {body} (already parsed). Returns {ok, value} or {ok:false, code, path}. opts.entityId: the centre the screen asked for.
function validate(v,opts={}){
 try{exact(v,TOP,'$');if(v.schema_version!==SCHEMA)refuse('SCHEMA','$.schema_version');
  if(v.relationship_denominator!==null||v.relationship_coverage!==null)refuse('COVERAGE_CLAIMED','$.relationship_denominator');
  if(v.historical_system_pit!==false)refuse('PIT_CLAIMED','$.historical_system_pit');
  if(!own(COLLECTION,v.collection_state))refuse('COLLECTION_STATE','$.collection_state');
  if(!isObj(v.query_as_of)||!str(v.query_as_of.valid_on)||!str(v.query_as_of.knowledge_at))refuse('TYPE','$.query_as_of');
  if(!Array.isArray(v.entities))refuse('TYPE','$.entities');const ents=new Map();
  v.entities.forEach((e,i)=>{const at='$.entities['+i+']';exact(e,ENTITY_KEYS,at);if(!str(e.entity_id)||ents.has(e.entity_id))refuse('ENTITY',at+'.entity_id');
   if(e.kind!=='LEGAL_ENTITY'||!Array.isArray(e.company_ids)||!e.company_ids.every(str))refuse('ENTITY',at);ents.set(e.entity_id,e);});
  if(!isObj(v.entity_context)||!ents.has(v.entity_context.entity_id))refuse('CENTRE_UNKNOWN','$.entity_context');
  const centre=v.entity_context.entity_id;if(opts.entityId!==undefined&&opts.entityId!==centre)refuse('CENTRE_MISMATCH','$.entity_context');
  if(!Array.isArray(v.mentions))refuse('TYPE','$.mentions');const ment=new Map();
  v.mentions.forEach((m,i)=>{if(!isObj(m)||!str(m.mention_id)||!str(m.name)||ments(ents,m))refuse('MENTION','$.mentions['+i+']');ment.set(m.mention_id,m);});
  if(!Array.isArray(v.relationships))refuse('TYPE','$.relationships');const ids=new Set();
  v.relationships.forEach((r,i)=>{const at='$.relationships['+i+']';exact(r,REL_KEYS,at);
   if(!str(r.relationship_id)||ids.has(r.relationship_id))refuse('RELATIONSHIP_ID',at+'.relationship_id');ids.add(r.relationship_id);
   if(!TYPE.includes(r.type))refuse('TYPE_UNKNOWN',at+'.type');if(r.direction!=='SOURCE_TO_TARGET')refuse('DIRECTION',at+'.direction');
   if(!ents.has(r.source_entity_id)||!ents.has(r.target_entity_id)||r.source_entity_id===r.target_entity_id)refuse('ENTITY',at+'.source_entity_id');
   const rel=r.source_entity_id===centre?'OUTGOING':r.target_entity_id===centre?'INCOMING':null;
   if(!rel||r.relative_direction!==rel)refuse('RELATIVE_DIRECTION',at+'.relative_direction');
   if(!own(DIRECTNESS,r.directness))refuse('DIRECTNESS',at+'.directness');if(!own(CAPACITY,r.capacity))refuse('CAPACITY',at+'.capacity');
   if(r.capacity==='INVESTMENT_DISCRETION'&&r.type!=='OWNERSHIP')refuse('13F_CAPACITY',at+'.capacity');
   if(!own(STATE,r.state))refuse('STATE',at+'.state');if(!str(r.validity_status))refuse('TYPE',at+'.validity_status');
   if(!(r.positive_ownership===null||typeof r.positive_ownership==='boolean'))refuse('TYPE',at+'.positive_ownership');
   if(r.type==='PARENT_SUBSIDIARY'&&r.positive_ownership!==null)refuse('CONTROL_FROM_PERCENT',at+'.positive_ownership');
   if(!Array.isArray(r.observations)||!Array.isArray(r.assertions)||!r.assertions.length||!Array.isArray(r.history))refuse('TYPE',at+'.assertions');
   r.observations.forEach((o,j)=>observation(o,at+'.observations['+j+']'));temporal(r.temporal,at+'.temporal');
   r.assertions.forEach((a,j)=>{assertion(a,at+'.assertions['+j+']');if(a.type!==r.type||a.source_entity_id!==r.source_entity_id||a.target_entity_id!==r.target_entity_id)refuse('ASSERTION_CONTEXT',at+'.assertions['+j+']');});
   r.history.forEach((a,j)=>assertion(a,at+'.history['+j+']'));});
  if(!Array.isArray(v.unresolved_assertions))refuse('TYPE','$.unresolved_assertions');
  v.unresolved_assertions.forEach((a,i)=>{const at='$.unresolved_assertions['+i+']';assertion(a,at);
   const side=a.source_entity_id===centre?'target':a.target_entity_id===centre?'source':null;
   if(!side||a[side+'_entity_id']!==null||!ment.has(a[side+'_mention_id']))refuse('UNRESOLVED',at);});
  if(!Array.isArray(v.confirmed_paths)||v.confirmed_paths.some(p=>!isObj(p)||p.economic_ownership_percent!==null||!Array.isArray(p.relationship_ids)))refuse('LOOK_THROUGH','$.confirmed_paths');
  const c=v.counts;exact(c,['code_rows','filtered_relationships','legal_entities','ownership_observations','relationships','unresolved_assertions'],'$.counts');
  if(c.filtered_relationships!==v.relationships.length||c.unresolved_assertions!==v.unresolved_assertions.length||c.legal_entities!==v.entities.length||c.relationships<c.filtered_relationships)refuse('COUNTS','$.counts');
  if(v.collection_state==='FILTER_EMPTY'?(v.relationships.length!==0||c.relationships===0):false)refuse('COLLECTION_STATE','$.collection_state');
  if(['NOT_FOUND_IN_REVIEWED_SCOPE','VERIFIED_ZERO_IN_SCOPE'].includes(v.collection_state)&&(v.relationships.length||v.unresolved_assertions.length))refuse('COLLECTION_STATE','$.collection_state');
  // NOT_COLLECTED: no review of this centre, so nothing it states itself (no outgoing relationship, no unresolved assertion of its
  // own); relationships other centres' evidence states about it (INCOMING) are kept (Codex consumer case incoming_centre_not_reviewed).
  if(v.collection_state==='NOT_COLLECTED'&&(v.unresolved_assertions.length||v.relationships.some(r=>r.relative_direction!=='INCOMING')))refuse('COLLECTION_STATE','$.collection_state');
  if(!isObj(v.collection)||!own(v.collection,'last_failure')||!own(v.collection,'last_success_at'))refuse('TYPE','$.collection');
  const value=freeze(JSON.parse(JSON.stringify(v)));CHECKED.add(value);return{ok:true,value};}
 catch(e){if(e instanceof Refusal)return{ok:false,code:e.code,path:e.path};throw e;}}
// A mention never carries an entity's id (an unresolved name is not an entity).
function ments(ents,m){return ents.has(m.mention_id);}

function pct(o){const q=QUALIFIER[o.qualifier];
 if(o.qualifier==='NOT_DISCLOSED')return '미공개'+(o.missing_reason?' ('+o.missing_reason+')':'');
 if(o.qualifier==='RANGE')return '범위 '+o.lower+'–'+o.upper+'%';
 return q+o.value+'%';}
function obsLine(o){return freeze({metric:o.metric,text:METRIC[o.metric]+' '+pct(o),basis:(BASIS[o.denominator_basis]||o.denominator_basis)+(o.share_class?' · '+o.share_class:'')+' · '+o.observed_as_of+' 기준',
 zero:o.value==='0'?'0% 관측(보유 아님 · 종료 추정 아님)':null});}
// The centre's view: five lists kept apart, unresolved mentions, the state line and the dates. Words only; nothing computed.
function view(v,{companyLink,receipt}={}){const centre=v.entity_context.entity_id,ents=new Map(v.entities.map(e=>[e.entity_id,e])),ment=new Map(v.mentions.map(m=>[m.mention_id,m]));
 const party=id=>{const e=ents.get(id);const link=companyLink?e.company_ids.map(companyLink).find(Boolean)||null:null;return freeze({entity_id:id,name:e.display_name,company_ids:e.company_ids,link});};
 const lists=Object.fromEntries(LISTS.map(([k])=>[k,[]]));
 for(const r of v.relationships){const other=r.relative_direction==='OUTGOING'?r.target_entity_id:r.source_entity_id;
  const key=r.capacity==='INVESTMENT_DISCRETION'?'discretion':r.type==='PARENT_SUBSIDIARY'?(r.relative_direction==='OUTGOING'?'subsidiaries':'parents'):(r.relative_direction==='OUTGOING'?'holdings':'holders');
  const obs=r.observations.map(obsLine);
  lists[key].push(freeze({relationship_id:r.relationship_id,relative:r.relative_direction,party:party(other),directness:DIRECTNESS[r.directness],capacity:r.type==='OWNERSHIP'?CAPACITY[r.capacity]:null,
   state:r.state,stateText:STATE[r.state],validity:r.validity_status==='VALIDITY_UNCONFIRMED'?'조회일 유효성 미확인':null,
   share:obs.filter(o=>o.metric==='SHARE_CAPITAL'),voting:obs.filter(o=>o.metric==='VOTING_POWER'),managed:obs.filter(o=>o.metric==='MANAGED_HOLDINGS'),
   percentNote:r.type==='PARENT_SUBSIDIARY'?(obs.length?'모회사·자회사 관계는 지분율과 따로 확인된 사실':'지분율 미공개 · 관계는 문서에 명시됨'):null,
   evidence:[...new Set(r.assertions.flatMap(a=>a.evidence_ids))],observedOn:r.temporal.observed_on,reviewedAt:r.temporal.reviewed_at}));}
 const unresolved=v.unresolved_assertions.map(a=>{const side=a.source_entity_id===centre?'target':'source',m=ment.get(a[side+'_mention_id']);
  return freeze({assertion_id:a.assertion_id,name:m.name,word:'목록에 없는 대상 · 기업 페이지 없음',type:a.type,relative:side==='target'?'OUTGOING':'INCOMING',directness:DIRECTNESS[a.directness]});});
 const n=v.relationships.length,conflicts=v.relationships.filter(r=>r.state==='CONFLICT').length,review=v.relationships.filter(r=>r.state==='REVIEW_REQUIRED').length;
 // Two states apart: how far this centre was reviewed (scope) and what the delivered evidence confirms (evidence).
 const scopeState=v.collection_state==='NOT_COLLECTED'&&n?NOT_REVIEWED_WITH_INCOMING:v.collection_state==='PARTIAL_REVIEW'?'일부 검토 · 전체 목록 미확인':COLLECTION[v.collection_state];
 const evidenceState=n?(v.collection_state==='NOT_COLLECTED'?'다른 기업 근거로 확인된 관계 '+n+'개(이 기업을 향한 관계)':'근거로 확인된 관계 '+n+'개'):'근거로 확인된 관계 없음 · 관계가 없다는 확인은 위 범위 상태만 말함';
 const state=[v.collection_state==='PARTIAL_REVIEW'?'확인된 '+n+'개 · 전체 목록 미확인':scopeState];
 if(v.collection_state==='NOT_COLLECTED'&&n)state.push(evidenceState);
 if(v.collection.last_failure)state.push('마지막 갱신 실패 · 이전에 성공한 자료를 보임'+(v.collection.last_success_at?' ('+v.collection.last_success_at+')':''));
 // A separate refresh receipt (checkReceipt) bound to these very view bytes: the failed attempt is shown beside the retained view,
 // whose own generated and last-success times stay as they are.
 const refresh=receipt&&RECEIPTS.has(receipt)&&receipt.attempt.outcome!=='SUCCESS'?'마지막 갱신 시도 '+(ATTEMPT[receipt.attempt.outcome])+' · 시도 '+receipt.attempt.attempted_at
  +' · 이전에 성공한 자료를 보임(성공 '+receipt.unchanged_last_success_at+' · 생성 '+receipt.unchanged_generated_at+')':null;

 if(conflicts)state.push('자료 충돌 '+conflicts+'건 · 값을 고르지 않음');if(review)state.push('재검토 필요 '+review+'건');
 if(unresolved.length)state.push('목록에 없는 대상 '+unresolved.length+'건');
 return freeze({centre:party(centre),collection_state:v.collection_state,state,scopeState,evidenceState,refresh,lists:LISTS.map(([k,label])=>freeze({key:k,label,rows:lists[k]})),unresolved,
  denominator:'전체 관계 수 미상 · 커버리지 계산 안 함',when:'조회 기준일 '+v.query_as_of.valid_on+' · 알려진 시점 '+v.query_as_of.knowledge_at+' · 과거 시점 재현(PIT) 아님',
  dataKind:v.dataset_id});}
// The producer's refresh attempt receipt (CONTRACT.md "merge_update receipts", consumer-synthetic refresh_* cases): kept apart from the
// view (the view's collection.last_failure stays null by contract). It must name the SHA-256 of exactly these view bytes (the
// producer's json_bytes: sorted-key compact JSON + newline) and the view's unchanged generated and last-success times; its attempt
// is later than the view. Anything else is refused and the view is shown without a refresh line.
const ATTEMPT=Object.freeze({SUCCESS:'성공',FAILED:'실패',PARTIAL:'일부만 성공',PARSE_FAILED:'해석 실패'});
const RECEIPTS=new WeakSet();
const canonicalJson=x=>Array.isArray(x)?'['+x.map(canonicalJson).join(',')+']':isObj(x)?'{'+Object.keys(x).sort().map(k=>JSON.stringify(k)+':'+canonicalJson(x[k])).join(',')+'}':JSON.stringify(x);
async function checkReceipt(r,v,sha256){
 try{if(!CHECKED.has(v))refuse('OWNERSHIP_VIEW_NOT_CHECKED','$');if(typeof sha256!=='function')refuse('HASH_UNAVAILABLE','$');
  exact(r,['attempt','retained_dataset_sha256','retained_view_sha256','unchanged_generated_at','unchanged_last_success_at'],'$receipt');
  exact(r.attempt,['attempted_at','outcome'],'$receipt.attempt');if(!own(ATTEMPT,r.attempt.outcome))refuse('RECEIPT_OUTCOME','$receipt.attempt.outcome');
  if(!/^[0-9a-f]{64}$/.test(r.retained_dataset_sha256)||!/^[0-9a-f]{64}$/.test(r.retained_view_sha256))refuse('TYPE','$receipt');
  if((await sha256(new TextEncoder().encode(canonicalJson(v)+'\n')))!==r.retained_view_sha256)refuse('RECEIPT_VIEW_MISMATCH','$receipt.retained_view_sha256');
  if(r.unchanged_generated_at!==v.generated_at||r.unchanged_last_success_at!==v.collection.last_success_at)refuse('RECEIPT_VIEW_MISMATCH','$receipt.unchanged_generated_at');
  if(typeof r.attempt.attempted_at!=='string'||!(Date.parse(r.attempt.attempted_at)>Date.parse(v.generated_at)))refuse('RECEIPT_TIME','$receipt.attempt.attempted_at');
  const value=freeze(JSON.parse(JSON.stringify(r)));RECEIPTS.add(value);return{ok:true,value};}
 catch(e){if(e instanceof Refusal)return{ok:false,code:e.code,path:e.path};throw e;}}
// The authenticated delivery (owner 2026-11-13): Main's index of the staged views (company-ownership-delivery/1, written by
// stage_private_ownership_view.py) names, per centre entity, its company ids, the view file's size and SHA-256 and the dataset hash,
// and the optional refresh receipt's size and SHA-256. The reader takes a view only when its own bytes are the ones the index names,
// it validates for that centre and names the same company ids and dataset; a listed receipt must be there and match, an unlisted
// one is refused. A receipt that fails checkReceipt leaves the view shown without a refresh line (receiptRefused names why).
const DELIVERY='company-ownership-delivery/1';
const HEX64=/^[0-9a-f]{64}$/,ENTITY_ID=/^[A-Z0-9][A-Z0-9-]{0,31}$/;
const fileRef=(f,at)=>{exact(f,['sha256','size'],at);if(!HEX64.test(f.sha256)||!Number.isInteger(f.size)||f.size<1)refuse('TYPE',at);return freeze({sha256:f.sha256,size:f.size});};
const INDEXES=new WeakSet();
function checkDeliveryIndex(file){
 try{const x=file&&file.body;exact(x,['schema_version','data_kind','sources','views','new_external_requests'],'$index');
  if(x.schema_version!==DELIVERY)refuse('SCHEMA','$index.schema_version');if(x.data_kind!=='PRIVATE'&&x.data_kind!=='SYNTHETIC')refuse('DATA_KIND','$index.data_kind');
  if(x.new_external_requests!==0)refuse('NOT_PROJECTION','$index.new_external_requests');
  if(!Array.isArray(x.sources)||!x.sources.length)refuse('TYPE','$index.sources');
  x.sources.forEach((s,i)=>{exact(s,['handoff_path','handoff_manifest_sha256'],'$index.sources['+i+']');if(typeof s.handoff_path!=='string'||!HEX64.test(s.handoff_manifest_sha256))refuse('TYPE','$index.sources['+i+']');});
  if(!Array.isArray(x.views)||!x.views.length)refuse('TYPE','$index.views');
  const ids=new Set(),codes=new Set();
  const views=x.views.map((v,i)=>{const at='$index.views['+i+']';exact(v,['entity_id','company_ids','dataset_hash','view','receipt'],at);
   if(typeof v.entity_id!=='string'||!ENTITY_ID.test(v.entity_id))refuse('TYPE',at+'.entity_id');if(ids.has(v.entity_id))refuse('INDEX_DUPLICATE',at+'.entity_id');ids.add(v.entity_id);
   if(!Array.isArray(v.company_ids)||v.company_ids.some(c=>typeof c!=='string'||!c))refuse('TYPE',at+'.company_ids');
   for(const c of v.company_ids){if(codes.has(c))refuse('INDEX_DUPLICATE',at+'.company_ids');codes.add(c);}
   if(!HEX64.test(v.dataset_hash))refuse('TYPE',at+'.dataset_hash');
   return freeze({entity_id:v.entity_id,company_ids:freeze([...v.company_ids]),dataset_hash:v.dataset_hash,view:fileRef(v.view,at+'.view'),receipt:v.receipt===null?null:fileRef(v.receipt,at+'.receipt')});});
  const value=freeze({data_kind:x.data_kind,views:freeze(views),sources:freeze(x.sources.map(s=>freeze({...s})))});INDEXES.add(value);return{ok:true,value};}
 catch(e){if(e instanceof Refusal)return{ok:false,code:e.code,path:e.path};throw e;}}
const entryFor=(index,code)=>INDEXES.has(index)&&code?index.views.find(v=>v.company_ids.includes(code))||null:null;
const hex=async(sha256,bytes)=>sha256(bytes);
async function checkDelivered(index,entry,viewFile,receiptFile,sha256){
 try{if(!INDEXES.has(index)||!index.views.includes(entry))refuse('INDEX_NOT_CHECKED','$');if(typeof sha256!=='function')refuse('HASH_UNAVAILABLE','$');
  if(!viewFile||!(viewFile.bytes instanceof Uint8Array))refuse('VIEW_MISSING','$view');
  if(viewFile.bytes.length!==entry.view.size||(await hex(sha256,viewFile.bytes))!==entry.view.sha256)refuse('FILE_MISMATCH','$view');
  const r=validate(viewFile.body,{entityId:entry.entity_id});if(!r.ok)return r;const v=r.value;
  const centre=v.entities.find(e=>e.entity_id===entry.entity_id);
  if(!centre||centre.company_ids.join('\u0000')!==entry.company_ids.join('\u0000'))refuse('INDEX_COMPANY_MISMATCH','$view.entities');
  if(v.dataset_hash!==entry.dataset_hash)refuse('INDEX_DATASET_MISMATCH','$view.dataset_hash');
  if(entry.receipt===null&&receiptFile)refuse('RECEIPT_UNLISTED','$receipt');
  if(entry.receipt!==null&&!receiptFile)refuse('RECEIPT_MISSING','$receipt');
  let receipt=null,receiptRefused=null;
  if(receiptFile){if(!(receiptFile.bytes instanceof Uint8Array)||receiptFile.bytes.length!==entry.receipt.size||(await hex(sha256,receiptFile.bytes))!==entry.receipt.sha256)refuse('FILE_MISMATCH','$receipt');
   const q=await checkReceipt(receiptFile.body,v,sha256);if(q.ok)receipt=q.value;else receiptRefused=q.code;}
  return{ok:true,value:freeze({view:v,receipt,receiptRefused,dataKind:index.data_kind})};}
 catch(e){if(e instanceof Refusal)return{ok:false,code:e.code,path:e.path};throw e;}}
// A relationship read from both sides is one fact: the same relationship_id, opposite relative directions (5.1.2 연결 근거).
function sameFact(a,b){const x=new Map(a.relationships.map(r=>[r.relationship_id,r]));return b.relationships.filter(r=>x.has(r.relationship_id))
 .map(r=>{const o=x.get(r.relationship_id);return freeze({relationship_id:r.relationship_id,consistent:o.source_entity_id===r.source_entity_id&&o.target_entity_id===r.target_entity_id&&o.type===r.type&&o.relative_direction!==r.relative_direction});});}
// RAM only (nothing stored): checked views by centre; a screen finds the view whose centre entity carries that code row. A value that
// validate did not return is refused; a drop tells the screens.
const ram=(()=>{const views=new Map(),subs=new Set();const tell=()=>{for(const f of subs)try{f();}catch(_){}};
 const receipts=new WeakMap();
 return Object.freeze({put(v,receipt){if(!CHECKED.has(v))throw Error('OWNERSHIP_VIEW_NOT_CHECKED');if(receipt!==undefined&&!RECEIPTS.has(receipt))throw Error('OWNERSHIP_RECEIPT_NOT_CHECKED');
   views.set(v.entity_context.entity_id,v);if(receipt)receipts.set(v,receipt);tell();},receiptFor(v){return receipts.get(v)||null;},
  forCompany(code){for(const v of views.values()){const e=v.entities.find(x=>x.entity_id===v.entity_context.entity_id);if(e&&e.company_ids.includes(code))return v;}return null;},
  get(id){return views.get(id)||null;},all(){return[...views.values()];},clear(){views.clear();tell();},subscribe(f){subs.add(f);return()=>subs.delete(f);}});})();
return Object.freeze({ram,SCHEMA,DELIVERY,TYPE,DIRECTNESS,CAPACITY,STATE,METRIC,QUALIFIER,COLLECTION,LISTS,ATTEMPT,validate,view,sameFact,checkReceipt,checkDeliveryIndex,entryFor,checkDelivered});
});
