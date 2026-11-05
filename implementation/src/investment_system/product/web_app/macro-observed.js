/* Macro observed-data reader (IS2.macroObserved, feature 4.1.3 매크로 관측 자료; owner 2026-11-05 "매크로: 관측 기간·갱신 시각·
   발표 근거·값 유지·수정·stale를 표시한다. 관측 자료와 미채택 국면 판단을 구분한다. 기존 운영 보류를 임의 해제하지 않는다.").
   Reads Codex's macro-current-query/1 (#477 efc8715f, implementation/docs/research/MACRO_UPDATE_20261105.md "현재 조회 파일
   연결"; evidence contract macro-observed-evidence/1, rows carried from the macro-observed-timeline/1 cache) as written by
   tools/macro_observed_timeline.py --timeline-cache, with no conversion. Calculation is Codex's (DC-42): this file only checks
   and words the file; it computes no state, stale flag, count or candidate rule (the consistency checks below compare the
   file with itself and never fill or repair it).
   - validate(json) → {ok:true, value} (a deep-frozen copy) or {ok:false, code, path}: the whole file is refused at its first
     fault. Besides shapes and enums it checks what the screen relies on: exactly the 14 series of the evidence catalog keyed
     by source_id (SERIES_SET); a value only with result_kind RAW_DIAGNOSTIC and a finite number, no value with NOT_COMPUTED
     (VALUE_WITH_NOT_COMPUTED); no value for a series held by terms (PUBLICATION_HELD_VALUE); state / stale / reason agree
     (STATE_MISMATCH); official_release_at and source_version_id are null with NOT_PROVEN_IN_ARCHIVE (the contract has no
     original-release or vintage proof: OFFICIAL_RELEASE_UNPROVEN, SOURCE_VERSION_UNPROVEN); historical_pit_eligible false,
     model_status NOT_APPLIED, scope EXPLORATION_ONLY with no official judgement / probability / gate (SCOPE_INVALID); the
     current query's transition flags new_observation / revised / newly_available false and held = query_usable (the doc:
     "캐시 조회는 새 관측·수정 사건을 만들지 않으므로 세 전환 플래그는 false"); update_status agrees with the last success and
     the collection state; the ages equal the stated times; counts equal the rows.
   - view(value) → words only (head, counts, one entry per series). No observed value is ever put in a view: the current query
     file is made privately and its use on a public screen is not approved (MACRO_UPDATE_20261105 "현재 조회 파일은 비공개로
     생성해 Main 계약만 인계한다 … 공개 화면의 파일 소비는 … 별도 승인 없이 바꾸지 않는다"), so the screen shows states,
     times and counts and says why the number is not shown. RAW_DIAGNOSTIC is 진단값 관측 (not an adopted regime judgment);
     NOT_COMPUTED is 미산출 with its reason. official_release_at null is 원발표 시각 미확인 · NOT_PROVEN_IN_ARCHIVE and is never
     filled from an acquisition, posting or planned time. candidate_state (v0 candidate rule) is not shown here.
   - source() → Promise {state:'NONE'}: no public file is approved, nothing is requested. Tests put a synthetic file in its place.
   Nothing here stores, reads or sends anything. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else{const I=root.IS2=root.IS2||{};I.macroObserved=api;}})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
const SCHEMA='macro-current-query/1',EVIDENCE='macro-observed-evidence/1',TIMELINE='macro-observed-timeline/1';
// The evidence catalog's 14 series (investment_system/macro/evidence_sources.py SERIES_IDS), with indicator and frequency.
const SERIES=Object.freeze([['TREASURY:BC_10YEAR-BC_3MONTH:MONTHLY_MEAN','E09','M'],['BLS:LNS14000000','E13','M'],['DOL:ETA539:INITIAL_CLAIMS_SA','E14','W'],
 ['BLS:CES6056132001','E16','M'],['BLS:CES3000000007','E17','M'],['CENSUS:M3:NXA:NO:SA','E21','M'],['FED:G17:IP.B50001.S','E22','M'],['BEA:NIPA:A191RL:Q','E25','Q'],
 ['CENSUS:RESCONST:APERMITS:TOTAL:SA','E26','M'],['FED:SLOOS:SUBLPDCILS_N.Q','E36','Q'],['BLS:CUSR0000SA0L1E','E39','M'],['BEA:NIPA:DPCCRG:M','E39','M'],
 ['FED:FOMC:TARGET_RANGE','E40','E'],['BTS:TSI:FREIGHT','E01','M']].map(x=>Object.freeze(x)));
const TOP=['schema_version','evidence_contract_version','query_at','cache_asof','archive_generated_at','archive_sha256','seconds_since_cache_asof','refresh_status',
 'new_external_requests','historical_pit_status','interpolation','scope','validity_rules','series','counts'],TOP_OPTIONAL=['timeline_cache_sha256'];
const ROW=['source_id','indicator','frequency','unit','seasonal_adjustment','observation_period','value','state','reason','first_published_at','source_posted_at','data_asof',
 'result_kind','stale','official_release_at','official_release_status','source_version_id','source_version_status','archive_version_id','version_time_basis',
 'first_acquired_at','first_acquired_by','first_acquisition_status','selected_version_acquired_at','query_usable','availability_status','historical_pit_eligible',
 'historical_pit_reason','available_at','availability_basis','version_kind','period_origin_kind','vintage_at','first_observed_at','new_observation','revised','held',
 'newly_available','observation_id','candidate_state','candidate_rule','model_status','latest_archive_success_at','collection_state_at_query',
 'collection_reason_at_query','valid_observations','history_window','source','last_successful_update_at','seconds_since_success','update_status'];
const SOURCE=['agency','source','url','license_class','publication','terms_checked_on','terms_note'];
const COUNTS=['series','query_usable','fresh_query_usable','system_available_by_query','official_release_proven','source_vintage_proven','historical_pit_eligible',
 'not_computed','stale','held'];
const SCOPE=Object.freeze({screen:'EXPLORATION_ONLY',official_judgement:false,probability:false,macro_gate:false,decision:'MEV-10'});
const ENUMS=Object.freeze({state:['AVAILABLE','STALE','NOT_AVAILABLE'],result_kind:['RAW_DIAGNOSTIC','NOT_COMPUTED'],seasonal_adjustment:['SA','NSA','SAAR','NOT_APPLICABLE'],
 first_acquisition_status:['RECORDED_CAPTURE','UPPER_BOUND_ONLY','NOT_AVAILABLE'],availability_status:['OBSERVED_CAPTURE_BY_QUERY','CONSERVATIVE_CAPTURE_BOUND_BY_QUERY','NOT_AVAILABLE_AT_QUERY'],
 update_status:['LAST_SUCCESS_RETAINED','FAILED_AFTER_SUCCESS','NEVER_SUCCEEDED'],kind:['BASELINE','FIRST','REVISION'],version_time_basis:['BASELINE','COLLECTION_TIME','SOURCE_LAST_MODIFIED'],
 availability_basis:['OBSERVED_CAPTURE','ARCHIVE_CAPTURE_UPPER_BOUND'],collection_state:['LIVE','PARTIAL','NOT_AVAILABLE']});
const PERIOD=Object.freeze({M:/^\d{4}-(0[1-9]|1[0-2])$/,Q:/^\d{4}Q[1-4]$/,W:/^\d{4}-\d{2}-\d{2}$/,E:/^\d{4}-\d{2}-\d{2}$/});
const TIME=/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$/,HEX64=/^[0-9a-f]{64}$/,CODE=/^[A-Z][A-Z0-9_]{0,63}$/;
const MAX=Object.freeze({text:2000,depth:8});

const REASON=Object.freeze({PERIOD_DELAYED:'기준 기간 지연 (기존 근거선 지연 기준 초과)',TERMS_UNVERIFIED:'약관 원문 미확인 · 공개 보류',SOURCE_NOT_COLLECTED:'수집 전',
 SOURCE_NOT_AVAILABLE:'출처 응답 없음',SOURCE_KEY_NOT_CONFIGURED:'API 키 미설정',BEFORE_CAPTURE_HISTORY:'보관 시작 전',NO_CAPTURE_AVAILABLE_AT_QUERY:'조회 시각까지 보관 기록 없음',
 SCHEMA_MISMATCH:'형식 불일치',SERIES_NOT_FOUND:'계열 없음',MISSING_SOURCE:'값 없음',PROVIDER_ERROR:'출처 오류 응답',INSUFFICIENT_HISTORY:'이력 부족',
 NO_QUERYABLE_VALUE:'조회 가능한 값 없음',OFFICIAL_RELEASE_AND_SOURCE_VINTAGE_NOT_PROVEN:'원발표·원기관 자료 버전 미입증'});
const TEXT=Object.freeze({
 TITLE:'관측 자료 · 갱신 상태',
 SCOPE:'관측 자료의 기간·시각·상태만 · 채택된 국면 판단이 아님 · 공식 국면은 미산출 · 기존 운영 보류(M-REENABLE 등) 그대로',
 NONE:'관측 조회 파일이 아직 연결되지 않았습니다',
 NONE_WHY:'Codex #477 macro-current-query/1 · 현재 조회 파일은 비공개로 생성 · 공개 게시와 화면 사용은 별도 승인 전 · 요청하지 않음',
 NONE_PLAN:'연결되면 계열마다: 기준 기간 · 갱신 시각 · 원발표 근거 · 값 유지/수정 · stale · 출처 약관',
 INVALID:'관측 조회 파일이 계약과 달라 파일 전체를 쓰지 않습니다',FAILED:'관측 조회 파일을 읽지 못했습니다',
 SYNTHETIC:'합성 개발 검증 · 실자료 아님',REAL:'실자료',UNSPECIFIED:'자료 종류 표시 없음',
 VALUES:'값 미표시 · 현재 조회 파일은 비공개 생성이고 공개 화면 사용이 승인되지 않음 (MACRO_UPDATE_20261105) · 상태·시각·개수만',
 CANDIDATE:'후보 규칙 상태는 여기 표시하지 않음 (해석 후보 · 미승인 · 근거 세로선 참고)',
 RELEASE:'원발표 시각 미확인 · NOT_PROVEN_IN_ARCHIVE',VINTAGE:'원기관 자료 버전 미확인 · NOT_PROVEN_IN_ARCHIVE',
 PIT:'과거 시점(PIT) 검증 불가',UNKNOWN_REASON:'사유 코드 미등록'});
const STATE_TEXT=Object.freeze({AVAILABLE:'조회 가능',STALE:'stale · 기준 기간 지연 (값 유지 · 진단용)',NOT_AVAILABLE:'자료 없음'});
const KIND_TEXT=Object.freeze({RAW_DIAGNOSTIC:'진단값 관측 · 채택된 국면 판단 아님',NOT_COMPUTED:'미산출'});
const UPDATE_TEXT=Object.freeze({LAST_SUCCESS_RETAINED:'마지막 성공 유지',FAILED_AFTER_SUCCESS:'최근 수집 실패 · 마지막 성공값 유지',NEVER_SUCCEEDED:'성공한 수집 없음'});
const REFRESH_TEXT=Object.freeze({CACHE_REUSED_NO_SOURCE_REFRESH:'계산 캐시 재사용 · 원천을 새로 받지 않음'});
const FREQ_TEXT=Object.freeze({M:'월',Q:'분기',W:'주',E:'사건 (효력일)'});
const SA_TEXT=Object.freeze({SA:'계절조정',NSA:'계절 미조정',SAAR:'계절조정 연율',NOT_APPLICABLE:'계절조정 해당 없음'});
const VERSION_TEXT=Object.freeze({BASELINE:'최초 보관 기준값',FIRST:'보관 중 첫 기록',REVISION:'수정 버전'});
const PUBLICATION_TEXT=Object.freeze({PUBLIC:'공개 범위',HELD_TERMS_UNVERIFIED:'약관 미확인 · 공개 보류'});

const own=(o,k)=>Object.prototype.hasOwnProperty.call(o,k);
const isObj=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
function Refusal(code,path){this.code=code;this.path=path;}
const refuse=(code,path)=>{throw new Refusal(code,path);};
function keys(o,want,path,optional=[]){if(!isObj(o))refuse('TYPE',path);for(const k of want)if(!own(o,k))refuse('KEY_MISSING',path+'.'+k);
 for(const k of Object.keys(o))if(!want.includes(k)&&!optional.includes(k))refuse('KEY_UNKNOWN',path+'.'+k);}
const str=(v,path)=>{if(typeof v!=='string'||!v)refuse('TYPE',path);if(v.length>MAX.text)refuse('TOO_LARGE',path);return v;};
const strOrNull=(v,path)=>{if(v!==null)str(v,path);};
const bool=(v,path)=>{if(typeof v!=='boolean')refuse('TYPE',path);};
const code=(v,path)=>{if(typeof v!=='string'||!CODE.test(v))refuse('REASON_INVALID',path);};
const codeOrNull=(v,path)=>{if(v!==null)code(v,path);};
const oneOf=(v,list,path)=>{if(!list.includes(v))refuse('ENUM',path);};
const oneOrNull=(v,list,path)=>{if(v!==null)oneOf(v,list,path);};
const hexOrNull=(v,path)=>{if(v!==null&&(typeof v!=='string'||!HEX64.test(v)))refuse('HASH_INVALID',path);};
function ms(v,path){if(typeof v!=='string'||!TIME.test(v))refuse('TIME_INVALID',path);const t=Date.parse(v);if(!Number.isFinite(t))refuse('TIME_INVALID',path);
 const d=new Date(t).toISOString();if(d.slice(0,19)!==v.slice(0,19))refuse('TIME_INVALID',path);return t;}
const msOrNull=(v,path)=>(v===null?null:ms(v,path));
const seconds=(v,path)=>{if(typeof v!=='number'||!Number.isFinite(v))refuse('TYPE',path);if(v<0)refuse('RANGE',path);};
const ageAgrees=(s,later,earlier)=>Math.abs(s-(later-earlier)/1000)<0.001;
const count=(v,path)=>{if(!Number.isInteger(v)||v<0)refuse('TYPE',path);};
function copy(v,path,depth){if(depth>MAX.depth)refuse('TOO_DEEP',path);
 if(v===null||typeof v==='string'||typeof v==='boolean')return v;if(typeof v==='number'){if(!Number.isFinite(v))refuse('NUMBER_NOT_FINITE',path);return v;}
 if(Array.isArray(v))return v.map((x,i)=>copy(x,path+'['+i+']',depth+1));
 if(isObj(v)&&(Object.getPrototypeOf(v)===Object.prototype||Object.getPrototypeOf(v)===null)){const o={};for(const k of Object.keys(v))o[k]=copy(v[k],path+'.'+k,depth+1);return o;}
 refuse('TYPE',path);}
function deepFreeze(v){if(v&&typeof v==='object'){Object.freeze(v);for(const k of Object.keys(v))deepFreeze(v[k]);}return v;}

function checkRow(r,sid,ind,freq,path,t){
 keys(r,ROW,path);
 if(r.source_id!==sid)refuse('SERIES_ID_MISMATCH',path+'.source_id');if(r.indicator!==ind)refuse('SERIES_ID_MISMATCH',path+'.indicator');
 if(r.frequency!==freq)refuse('SERIES_ID_MISMATCH',path+'.frequency');
 str(r.unit,path+'.unit');oneOf(r.seasonal_adjustment,ENUMS.seasonal_adjustment,path+'.seasonal_adjustment');
 keys(r.source,SOURCE,path+'.source');for(const k of SOURCE)str(r.source[k],path+'.source.'+k);code(r.source.publication,path+'.source.publication');code(r.source.license_class,path+'.source.license_class');
 oneOf(r.state,ENUMS.state,path+'.state');codeOrNull(r.reason,path+'.reason');oneOf(r.result_kind,ENUMS.result_kind,path+'.result_kind');
 // No original release or source vintage proof in this contract: null with NOT_PROVEN_IN_ARCHIVE, never filled.
 if(r.official_release_at!==null||r.first_published_at!==null||r.official_release_status!=='NOT_PROVEN_IN_ARCHIVE')refuse('OFFICIAL_RELEASE_UNPROVEN',path+'.official_release_at');
 if(r.source_version_id!==null||r.source_version_status!=='NOT_PROVEN_IN_ARCHIVE')refuse('SOURCE_VERSION_UNPROVEN',path+'.source_version_id');
 if(r.historical_pit_eligible!==false)refuse('PIT_ELIGIBLE',path+'.historical_pit_eligible');code(r.historical_pit_reason,path+'.historical_pit_reason');
 if(r.model_status!=='NOT_APPLIED')refuse('MODEL_APPLIED',path+'.model_status');
 strOrNull(r.candidate_state,path+'.candidate_state');strOrNull(r.candidate_rule,path+'.candidate_rule');
 for(const k of['new_observation','revised','held','newly_available','query_usable'])bool(r[k],path+'.'+k);
 // The current query projects a cache: it makes no new observation, revision or availability event.
 for(const k of['new_observation','revised','newly_available'])if(r[k]!==false)refuse('FLAG_INVALID',path+'.'+k);
 count(r.valid_observations,path+'.valid_observations');count(r.history_window,path+'.history_window');
 for(const k of['archive_version_id','observation_id'])hexOrNull(r[k],path+'.'+k);
 const at={};for(const k of['source_posted_at','first_acquired_at','first_acquired_by','selected_version_acquired_at','available_at','vintage_at','first_observed_at',
  'latest_archive_success_at','last_successful_update_at'])at[k]=msOrNull(r[k],path+'.'+k);
 oneOf(r.first_acquisition_status,ENUMS.first_acquisition_status,path+'.first_acquisition_status');oneOf(r.availability_status,ENUMS.availability_status,path+'.availability_status');
 oneOrNull(r.version_kind,ENUMS.kind,path+'.version_kind');oneOrNull(r.period_origin_kind,ENUMS.kind,path+'.period_origin_kind');
 oneOrNull(r.version_time_basis,ENUMS.version_time_basis,path+'.version_time_basis');oneOrNull(r.availability_basis,ENUMS.availability_basis,path+'.availability_basis');
 oneOrNull(r.collection_state_at_query,ENUMS.collection_state,path+'.collection_state_at_query');codeOrNull(r.collection_reason_at_query,path+'.collection_reason_at_query');
 oneOf(r.update_status,ENUMS.update_status,path+'.update_status');
 const has=r.value!==null;
 if(r.result_kind==='NOT_COMPUTED'&&has)refuse('VALUE_WITH_NOT_COMPUTED',path+'.value');
 if(r.result_kind==='RAW_DIAGNOSTIC'&&!has)refuse('VALUE_MISSING',path+'.value');
 if(has&&(typeof r.value!=='number'||!Number.isFinite(r.value)))refuse('NUMBER_NOT_FINITE',path+'.value');
 if(has&&r.source.publication!=='PUBLIC')refuse('PUBLICATION_HELD_VALUE',path+'.value');
 if(r.query_usable!==has)refuse('STATE_MISMATCH',path+'.query_usable');if(r.held!==r.query_usable)refuse('HELD_MISMATCH',path+'.held');
 if(r.data_asof!==r.observation_period)refuse('PERIOD_INVALID',path+'.data_asof');
 if(has){
  if(typeof r.observation_period!=='string'||!PERIOD[freq].test(r.observation_period))refuse('PERIOD_INVALID',path+'.observation_period');
  if(r.stale===null?freq!=='E':typeof r.stale!=='boolean')refuse('STALE_MISMATCH',path+'.stale');
  if(r.state!==(r.stale===true?'STALE':'AVAILABLE')||r.reason!==(r.stale===true?'PERIOD_DELAYED':null))refuse('STATE_MISMATCH',path+'.state');
  if(r.version_kind===null||r.period_origin_kind===null||r.version_time_basis===null||r.availability_basis===null||r.observation_id===null||r.archive_version_id===null)refuse('KEY_MISSING',path+'.version_kind');
  if(at.available_at===null||at.available_at>t.cache||at.first_acquired_by===null||at.vintage_at===null)refuse('AVAILABILITY_MISMATCH',path+'.available_at');
  if(r.availability_status==='NOT_AVAILABLE_AT_QUERY'||(r.availability_status==='OBSERVED_CAPTURE_BY_QUERY')!==(at.selected_version_acquired_at!==null))refuse('AVAILABILITY_MISMATCH',path+'.availability_status');
  if(r.first_acquisition_status==='NOT_AVAILABLE'||(r.first_acquisition_status==='RECORDED_CAPTURE')!==(at.first_acquired_at!==null))refuse('ACQUISITION_MISMATCH',path+'.first_acquisition_status');
  if(at.latest_archive_success_at===null)refuse('SUCCESS_MISMATCH',path+'.latest_archive_success_at');}
 else{
  if(r.observation_period!==null||r.stale!==null||r.state!=='NOT_AVAILABLE')refuse('STATE_MISMATCH',path+'.state');
  if(r.reason===null)refuse('REASON_MISSING',path+'.reason');
  if(r.availability_status!=='NOT_AVAILABLE_AT_QUERY'||r.first_acquisition_status!=='NOT_AVAILABLE'||at.first_acquired_at!==null||at.selected_version_acquired_at!==null||at.available_at!==null)
   refuse('AVAILABILITY_MISMATCH',path+'.availability_status');}
 // The last success is the archive's recorded success; its age is stated in seconds; the update status follows from both.
 if(r.last_successful_update_at!==r.latest_archive_success_at)refuse('SUCCESS_MISMATCH',path+'.last_successful_update_at');
 if(at.last_successful_update_at!==null&&at.last_successful_update_at>t.archive)refuse('SUCCESS_MISMATCH',path+'.last_successful_update_at');
 if(at.last_successful_update_at===null){if(r.seconds_since_success!==null)refuse('AGE_MISMATCH',path+'.seconds_since_success');}
 else{seconds(r.seconds_since_success,path+'.seconds_since_success');if(!ageAgrees(r.seconds_since_success,t.query,at.last_successful_update_at))refuse('AGE_MISMATCH',path+'.seconds_since_success');}
 const want=at.last_successful_update_at===null?'NEVER_SUCCEEDED':r.collection_state_at_query==='NOT_AVAILABLE'?'FAILED_AFTER_SUCCESS':'LAST_SUCCESS_RETAINED';
 if(r.update_status!==want)refuse('UPDATE_STATUS_MISMATCH',path+'.update_status');}

function validate(json){
 try{if(!isObj(json))refuse('TYPE','$');const v=copy(json,'$',0);keys(v,TOP,'$',TOP_OPTIONAL);
  if(v.schema_version!==SCHEMA)refuse('SCHEMA_VERSION','$.schema_version');if(v.evidence_contract_version!==EVIDENCE)refuse('EVIDENCE_CONTRACT','$.evidence_contract_version');
  const t={query:ms(v.query_at,'$.query_at'),cache:ms(v.cache_asof,'$.cache_asof'),archive:ms(v.archive_generated_at,'$.archive_generated_at')};
  if(!(t.archive<=t.cache&&t.cache<=t.query))refuse('TIME_ORDER','$.cache_asof');
  seconds(v.seconds_since_cache_asof,'$.seconds_since_cache_asof');if(!ageAgrees(v.seconds_since_cache_asof,t.query,t.cache))refuse('AGE_MISMATCH','$.seconds_since_cache_asof');
  hexOrNull(v.archive_sha256,'$.archive_sha256');if(v.archive_sha256===null)refuse('HASH_INVALID','$.archive_sha256');
  if(own(v,'timeline_cache_sha256'))hexOrNull(v.timeline_cache_sha256,'$.timeline_cache_sha256');
  oneOf(v.refresh_status,Object.keys(REFRESH_TEXT),'$.refresh_status');if(v.new_external_requests!==0)refuse('EXTERNAL_REQUESTS','$.new_external_requests');
  if(v.historical_pit_status!=='OBSERVED_CAPTURE_ONLY')refuse('PIT_STATUS','$.historical_pit_status');if(v.interpolation!=='NONE')refuse('INTERPOLATION','$.interpolation');
  keys(v.scope,Object.keys(SCOPE),'$.scope');for(const k of Object.keys(SCOPE))if(v.scope[k]!==SCOPE[k])refuse('SCOPE_INVALID','$.scope.'+k);
  if(!isObj(v.validity_rules))refuse('TYPE','$.validity_rules');for(const k of Object.keys(v.validity_rules))str(v.validity_rules[k],'$.validity_rules.'+k);
  if(!isObj(v.series))refuse('TYPE','$.series');const ids=Object.keys(v.series);
  if(ids.length!==SERIES.length||!SERIES.every(([s])=>own(v.series,s)))refuse('SERIES_SET','$.series');
  for(const[sid,ind,freq]of SERIES)checkRow(v.series[sid],sid,ind,freq,'$.series['+JSON.stringify(sid)+']',t);
  keys(v.counts,COUNTS,'$.counts');for(const k of COUNTS)count(v.counts[k],'$.counts.'+k);
  const rows=SERIES.map(([s])=>v.series[s]),n=f=>rows.filter(f).length;
  const want={series:rows.length,query_usable:n(r=>r.query_usable),fresh_query_usable:n(r=>r.query_usable&&r.stale!==true),system_available_by_query:n(r=>r.query_usable),
   official_release_proven:0,source_vintage_proven:0,historical_pit_eligible:0,not_computed:n(r=>!r.query_usable),stale:n(r=>r.stale===true),held:n(r=>r.held)};
  for(const k of COUNTS)if(v.counts[k]!==want[k])refuse('COUNT_MISMATCH','$.counts.'+k);
  return{ok:true,value:deepFreeze(v)};}
 catch(e){if(e instanceof Refusal)return{ok:false,code:e.code,path:e.path};return{ok:false,code:'TYPE',path:'$'};}}

/* ---- words */
const utc=t=>typeof t==='string'&&TIME.test(t)?t.slice(0,10)+' '+t.slice(11,16)+' UTC':'—';
// Elapsed seconds in words (formatting only; the seconds are the file's).
function ageText(s){if(typeof s!=='number'||!Number.isFinite(s))return'—';const x=Math.floor(s);
 if(x<60)return x+'초';if(x<3600)return Math.floor(x/60)+'분';if(x<86400){const hh=Math.floor(x/3600),mm=Math.floor((x%3600)/60);return hh+'시간'+(mm?' '+mm+'분':'');}
 const d=Math.floor(x/86400),hh=Math.floor((x%86400)/3600);return d+'일'+(hh?' '+hh+'시간':'');}
const reasonText=c=>(typeof c==='string'&&own(REASON,c)?REASON[c]:TEXT.UNKNOWN_REASON+(typeof c==='string'?' · '+c:''));
const kindText=v=>(v.dataKind==='SYNTHETIC'?TEXT.SYNTHETIC:v.dataKind==='REAL'?TEXT.REAL:TEXT.UNSPECIFIED);
const yes=b=>(b?'예':'아니오');
function acquisition(r){
 if(r.first_acquisition_status==='RECORDED_CAPTURE')return'첫 취득 '+utc(r.first_acquired_at)+' (기록된 수신)';
 if(r.first_acquisition_status==='UPPER_BOUND_ONLY')return'첫 취득 시각 기록 없음 · 늦어도 '+utc(r.first_acquired_by)+' (보관본 생성 상한)';
 return'취득 기록 없음';}
function selected(r){
 if(r.availability_status==='OBSERVED_CAPTURE_BY_QUERY')return'선택 버전 취득 '+utc(r.selected_version_acquired_at);
 if(r.availability_status==='CONSERVATIVE_CAPTURE_BOUND_BY_QUERY')return'선택 버전 취득 시각 기록 없음 · 늦어도 '+utc(r.available_at)+' (보수 상한)';
 return'조회 시각 기준 선택 버전 없음';}
function seriesView(r){
 const has=r.result_kind==='RAW_DIAGNOSTIC';
 const state=r.state==='NOT_AVAILABLE'?STATE_TEXT.NOT_AVAILABLE+' · '+reasonText(r.reason):r.state==='STALE'?STATE_TEXT.STALE:STATE_TEXT.AVAILABLE+(r.stale===null?' · stale 판정 없음 (사건 계열)':'');
 const period=has?'기준 기간 '+r.observation_period+' · data_asof '+r.data_asof:'기준 기간 없음';
 const meta=FREQ_TEXT[r.frequency]+' · 단위 '+r.unit+' · '+SA_TEXT[r.seasonal_adjustment];
 const kind=has?KIND_TEXT.RAW_DIAGNOSTIC+' · 값 미표시':KIND_TEXT.NOT_COMPUTED+' · '+reasonText(r.reason);
 const evidence=[TEXT.RELEASE,acquisition(r),has?selected(r):null,has?'버전 '+VERSION_TEXT[r.version_kind]+' · 기간 첫 근거 '+VERSION_TEXT[r.period_origin_kind]:null].filter(x=>x!==null).join(' · ');
 const flags='값 유지 '+yes(r.held)+' · 수정 버전 '+yes(r.version_kind==='REVISION')+' · 이번 조회의 수정 '+yes(r.revised)+' · 새 관측 '+yes(r.new_observation)+' · 새로 조회 가능 '+yes(r.newly_available);
 const update=(r.last_successful_update_at===null?'마지막 성공 수집 없음':'마지막 성공 수집 '+utc(r.last_successful_update_at)+' ('+ageText(r.seconds_since_success)+' 전)')+' · '+UPDATE_TEXT[r.update_status]+
  (r.update_status==='FAILED_AFTER_SUCCESS'&&r.collection_reason_at_query?' · 실패 사유 '+reasonText(r.collection_reason_at_query):'');
 const src=r.source;
 const terms=src.agency+' · '+src.license_class+' · '+(own(PUBLICATION_TEXT,src.publication)?PUBLICATION_TEXT[src.publication]:src.publication)+' · 약관 확인 '+src.terms_checked_on+' · '+src.terms_note;
 return Object.freeze({id:r.source_id,indicator:r.indicator,name:src.source,state:r.state,resultKind:r.result_kind,update:r.update_status,stale:r.stale,
  version:r.version_kind,held:r.held,lines:Object.freeze({state,period,meta,kind,evidence,flags,update,terms,vintage:TEXT.VINTAGE+' · '+TEXT.PIT+' · '+reasonText(r.historical_pit_reason),url:src.url})});}
function view(value,{dataKind=null}={}){
 const v=value,c=v.counts;
 return Object.freeze({
  status:kindText({dataKind})+' · '+SCHEMA+' · 근거 계약 '+EVIDENCE+' · 계산 Codex · 공개 판정 아님',
  query:Object.freeze([['조회 시각',utc(v.query_at)],['계산 캐시 기준',utc(v.cache_asof)+' · '+ageText(v.seconds_since_cache_asof)+' 전'],['보관본 생성',utc(v.archive_generated_at)],
   ['갱신',REFRESH_TEXT[v.refresh_status]+' · 외부 요청 '+v.new_external_requests+'건'],['시점 범위','보관 시점 관측만 (OBSERVED_CAPTURE_ONLY) · 보간 없음']].map(x=>Object.freeze(x))),
  counts:c.series+'계열 · 조회 가능 '+c.query_usable+' (신선 '+c.fresh_query_usable+' · stale '+c.stale+') · 값 유지 '+c.held+' · 미산출 '+c.not_computed+
   ' · 원발표 입증 '+c.official_release_proven+' · 원기관 버전 입증 '+c.source_vintage_proven+' · 과거 시점 검증 가능 '+c.historical_pit_eligible,
  series:Object.freeze(SERIES.map(([s])=>seriesView(v.series[s])))});}
function source(){return Promise.resolve(Object.freeze({state:'NONE',code:'MACRO_CURRENT_NOT_CONNECTED',payload:null,data_kind:null,text:TEXT.NONE}));}
return Object.freeze({SCHEMA,EVIDENCE,TIMELINE,SERIES,REASON,TEXT,STATE_TEXT,KIND_TEXT,UPDATE_TEXT,REFRESH_TEXT,validate,view,reasonText,ageText,source});
});
