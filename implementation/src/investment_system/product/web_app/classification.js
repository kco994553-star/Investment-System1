/* 공통 분류 reader (IS2.classification; DC-48, owner 2026-11-07; docs/frontend_v2/COMMON_CLASSIFICATION.md). Reads Codex's
   common-classification/1 outputs (#516 9343b5e6, docs/research/common_classification/CONTRACT.md) as published, checks them and
   answers the screens. It decides no classification: resolve / technical_groups / macro_projection / project_qgv are Codex's,
   this file only reads their results (field names, ids, states and reason codes unchanged). Pure parts run in node as in the page.
   - Parts (each strictly checked, refused whole at the first fault {ok:false, code, path}):
     view       common-classification-view/1 (records.resolve): one row per member company, sector / industry / accounting each
                {id, status CONFIRMED|UNKNOWN|CONFLICT, reasons, evidence_refs}; a non-CONFIRMED part has id null and a reason.
     technical  common-classification-technical/1 (technical_groups): one technical-leaderboard/1 board per book sector
                (checked by IS2.techScreen.validate), group_id COMMON:<sector>:<price basis>, a confirmed group's
                membership_source = common-classification:<classification_hash>; rows with classification_record_id.
     macro      common-classification-macro/1 (macro_projection): common sector / industry, the source SIC group and the ETF
                comparison series kept apart (benchmark_is_common_sector and source_industry_is_common_sector false; own sector
                returns and rotation probabilities null).
     qgv_links  common-classification-qgv-links/1 (CLI qgv-classification-links.json): preview identity + record id per company.
     dictionary common-classification-dictionary/1 (catalog.dictionary): sector and industry names only.
   - Same record: every part must carry the view's classification_hash and valuation_date, and per company the view's record_id
     and issuer_id (classification_record_id); otherwise that part is kept aside as 분류 버전 불일치 (VERSION_MISMATCH) and no
     join or comparison uses it. Three ids stay distinct: company_id (the Universe504 security-code row; Main rows' code),
     issuer_id (issuer / CIK, not a security id) and security_id (a verified fixed id; a classification record has none: null).
   - recordFor(company_id, valuation_date) → the record's state and words (STATE / WORDS below); unknown is never 0 or 기타.
     sameRecord(a, b): same company, record id, classification_hash, dictionary / mapping version and valuation date.
   - groupRows(board, universe) (screen-tech-filter-live keep): the confirmed board group's FULL rows — board group_id
     COMMON:<sector>:<basis> → the technical projection's rows of that sector (all CONFIRMED) → the universe rows whose code is
     each company_id, every one of them (never only those already on the board); each row gets the record's issuer_id; signal_day
     and security_id stay the row's own (null today, never made up). null when anything is unknown (groupRowsWhy gives the code).
   - sample(kind, metric) keeps the small-sample states apart: GROUP_UNCONFIRMED (no rank / median), EMPTY_GROUP, SAMPLE_SMALL
     (tech N < 10: no decile, rank and median kept; sector QGV N < 20: no factor score), OK.
   - context: the hash token cc:<sector|->:<industry|->:<valuation date>:<hash 12> carried between screens; contextState says
     whether it is this record set (OK), another version (VERSION_MISMATCH) or another date (DATE_MISMATCH).
   - source() → Promise {state:'NONE'} (no public file, no request) until the owner's private delivery: connectPrivate(payload)
     from the 비공개 펼치기 click (delivery PRIVATE, 비공개 보관본 · 인증 경로 · 게시본 아님) until disconnectPrivate(). load()
     reads the current source once (again only when the source function or the private delivery changes) and keeps the checked
     bundle in RAM; nothing is stored or sent. A public classification file is not a precondition of the private delivery.
   - The accounting model is its own state (Codex #516 4cf2e037): recordFor gives accounting_state and peer_complete (sector AND
     accounting confirmed); a confirmed sector with an unknown accounting model is shown, never as a complete QGV peer group.
   - evidence_refs are opaque locators (never shown): their own length bound (MAX.ref), apart from the words' MAX.text. */
(function(root,factory){const api=factory(root);if(typeof module==='object'&&module.exports)module.exports=api;else{const I=root.IS2=root.IS2||{};I.classification=api;}})(typeof globalThis==='object'?globalThis:this,function(root){
'use strict';
const SCHEMAS=Object.freeze({view:'common-classification-view/1',technical:'common-classification-technical/1',macro:'common-classification-macro/1',
 qgv_links:'common-classification-qgv-links/1',dictionary:'common-classification-dictionary/1'});
const VERSIONS=Object.freeze({dictionary:'common-industry-dictionary/1',mapping:'common-classification-map/1'});
// book-sector-map/1 (Codex sector_qgv_registry.SECTORS): the ids a confirmed sector may carry. Names come from the dictionary part.
const SECTORS=Object.freeze(['CONSUMER_DISCRETIONARY','CONSUMER_STAPLES','ENERGY','FINANCIALS','HEALTH_CARE','INDUSTRIALS','INFORMATION_TECHNOLOGY','MATERIALS','TELECOMMUNICATIONS','UTILITIES']);
const STATUS=Object.freeze(['CONFIRMED','UNKNOWN','CONFLICT']);
const DATA_KINDS=Object.freeze(['SYNTHETIC','RETAINED_INPUT']);
// Reasons that mean "no classification applies on this evaluation date" (records._eligibility).
const DATE_REASONS=Object.freeze(['OUTSIDE_CLASSIFICATION_INTERVAL','EVALUATION_ONLY_DATE_MISMATCH','EFFECTIVE_START_UNKNOWN']);
const STATE=Object.freeze({CONFIRMED:'CONFIRMED',SECTOR_ONLY:'SECTOR_ONLY',CONFLICT:'CONFLICT',NOT_APPLICABLE_ON_DATE:'NOT_APPLICABLE_ON_DATE',
 NO_DATA:'NO_DATA',UNRESOLVED:'UNRESOLVED',VERSION_MISMATCH:'VERSION_MISMATCH'});
const WORDS=Object.freeze({CONFIRMED:'확인',SECTOR_ONLY:'섹터 확인 · 하위 산업 미확인',SECTOR_INDUSTRY_CONFLICT:'섹터 확인 · 하위 산업 근거 불일치',
 CONFLICT:'분류 충돌 · 근거 불일치',NO_DATA:'분류 자료 없음',VERSION_MISMATCH:'분류 버전 불일치',UNRESOLVED:'섹터 대응 미확인 · 근거 부족',
 SAMPLE_SMALL:'표본 부족 · 기능별 규칙(섹터 QGV N<20 요소 점수 미산출 · 기술 N<10 분위 미산출, 순위·중앙값 유지)',GROUP_UNCONFIRMED:'구성원·신원 미확인 · 상대순위·중앙값도 미산출',EMPTY_GROUP:'구성원 0 · 비교 대상 없음',
 NONE:'공통 분류 실자료 묶음 보존됨 · 인증된 화면 전달 경로 미연결',NONE_WHY:'분류는 Codex(common-classification/1) · 실자료 묶음은 Codex 비공개 보존 · 이 화면에는 합성 자료만 시험에서',
 INVALID:'공통 분류 파일이 계약과 달라 쓰지 않습니다',PRIVATE:'비공개 보관본 · 인증 경로 · 게시본 아님',
 ACCOUNTING_UNKNOWN:'회계모형 미확인 · 섹터가 확인돼도 QGV 비교집단 완결 아님',ACCOUNTING_CONFLICT:'회계모형 근거 불일치 · QGV 비교집단 완결 아님',
 ACCOUNTING_WITHOUT_SECTOR:'회계모형만 확인 · 섹터 미확인',SECURITY_NONE:'검증된 증권 ID 없음',ISSUER_NONE:'발행사 ID 미확인'});
const dateWords=d=>'평가일 '+d+'에 적용되는 분류 없음';
// Why a tech board group's full rows are not known (groupRowsWhy codes) — words for the tech filter block.
const GROUP_TEXT=Object.freeze({NO_BOARD:'보드 없음',CLASSIFICATION_NOT_CONNECTED:'공통 분류 기록 미연결',TECHNICAL_PROJECTION_NOT_CONNECTED:'공통 분류 기술 투영 미연결',
 CLASSIFICATION_VERSION_MISMATCH:'분류 버전 불일치',BOARD_GROUP_NOT_COMMON:'보드 그룹이 공통 분류 그룹이 아님',BOARD_GROUP_NOT_IN_PROJECTION:'공통 분류 투영에 없는 보드 그룹',
 BOARD_DATE_MISMATCH:'보드 평가일 ≠ 분류 평가일',GROUP_MEMBERSHIP_UNCONFIRMED:'그룹 구성원 미확인',
 ROW_CLASSIFICATION_MISMATCH:'행의 분류 해시·기록 ID ≠ 분류 기록 · 덮어쓰지 않음',ISSUER_CONNECTION_EVIDENCE_REQUIRED:'발행사 연결 근거 없음',
 GROUP_UNIVERSE_CONTEXT_REQUIRED:'분류 기록에 모집단 문맥(universe) 없음 · 그룹 명부를 만들 수 없음',GROUP_PROJECTION_RECORD_MISMATCH:'기술 투영과 분류 기록 불일치',
 GROUP_PROJECTION_MEMBERS_MISMATCH:'기술 투영 구성원 ≠ 분류 기록 구성원',GROUP_PROJECTION_GROUP_MISMATCH:'기술 투영에서 그룹을 하나로 찾지 못함',MEMBER_NOT_MAPPED:'그룹 구성원이 리더보드 행과 1:1로 대응되지 않음',
 ISSUER_MISMATCH:'행의 발행사 ID ≠ 분류 기록 발행사 ID'});
// text: words a screen may show; ref: an opaque evidence locator (never shown). Codex #516 4cf2e037 held-review refs reach 330 characters
// (source id + ':metadata:' + hash, HELD_REVIEW.md); the contract sets no length, so a ref has its own bound and is never shortened.
const MAX=Object.freeze({rows:20000,text:300,ref:4096,depth:14});
const DAY=/^(\d{4})-(\d{2})-(\d{2})$/,HEX64=/^[0-9a-f]{64}$/,CODE=/^[A-Z][A-Z0-9_:]{0,95}$/,TS=/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/;
const own=(o,k)=>Object.prototype.hasOwnProperty.call(o,k);
const isObj=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
function Refusal(code,path){this.code=code;this.path=path;}
const refuse=(code,path)=>{throw new Refusal(code,path);};
function keys(o,want,path,optional=null){if(!isObj(o))refuse('TYPE',path);for(const k of want)if(!own(o,k))refuse('KEY_MISSING',path+'.'+k);
 if(optional)for(const k of Object.keys(o))if(!want.includes(k)&&!optional.includes(k))refuse('KEY_UNKNOWN',path+'.'+k);}
const text=(v,path)=>{if(typeof v!=='string'||!v.trim()||v!==v.trim())refuse('TYPE',path);if(v.length>MAX.text)refuse('TOO_LARGE',path);return v;};
const textOrNull=(v,path)=>(v===null?null:text(v,path));
function day(v,path){const m=typeof v==='string'&&DAY.exec(v);if(!m)refuse('DATE_INVALID',path);const d=new Date(Date.UTC(+m[1],+m[2]-1,+m[3]));
 if(d.getUTCMonth()!==+m[2]-1||d.getUTCDate()!==+m[3])refuse('DATE_INVALID',path);return v;}
const stamp=(v,path)=>{if(typeof v!=='string'||!TS.test(v)||!Number.isFinite(Date.parse(v)))refuse('TIME_INVALID',path);return v;};
const hex=(v,path)=>{if(typeof v!=='string'||!HEX64.test(v))refuse('HASH_INVALID',path);return v;};
const list=(v,path)=>{if(!Array.isArray(v))refuse('TYPE',path);if(v.length>MAX.rows)refuse('TOO_LARGE',path);return v;};
const codes=(v,path)=>list(v,path).forEach((c,i)=>{if(typeof c!=='string'||!CODE.test(c))refuse('REASON_INVALID',path+'['+i+']');});
const texts=(v,path)=>list(v,path).forEach((c,i)=>text(c,path+'['+i+']'));
const ref=(v,path)=>{if(typeof v!=='string'||!v.trim()||v!==v.trim())refuse('TYPE',path);if(v.length>MAX.ref)refuse('TOO_LARGE',path);return v;};
const refs=(v,path)=>list(v,path).forEach((c,i)=>ref(c,path+'['+i+']'));
const int=(v,path)=>{if(!Number.isInteger(v)||v<0)refuse('TYPE',path);};
function copy(v,path,depth){if(depth>MAX.depth)refuse('TOO_DEEP',path);
 if(v===null||typeof v==='string'||typeof v==='boolean')return v;if(typeof v==='number'){if(!Number.isFinite(v))refuse('NUMBER_NOT_FINITE',path);return v;}
 if(Array.isArray(v))return v.map((x,i)=>copy(x,path+'['+i+']',depth+1));
 if(isObj(v)&&(Object.getPrototypeOf(v)===Object.prototype||Object.getPrototypeOf(v)===null)){const o={};for(const k of Object.keys(v))o[k]=copy(v[k],path+'.'+k,depth+1);return o;}
 refuse('TYPE',path);}
function deepFreeze(v){if(v&&typeof v==='object'){Object.freeze(v);for(const k of Object.keys(v))deepFreeze(v[k]);}return v;}
const techReader=()=>{const I=root&&root.IS2;if(I&&I.techScreen)return I.techScreen;
 try{return typeof module==='object'&&module.exports&&typeof require==='function'?require('./tech-screen.js'):null;}catch(_){return null;}};
const pass=fn=>json=>{try{const v=copy(json,'$',0);fn(v,'$');return{ok:true,value:deepFreeze(v)};}catch(e){if(e instanceof Refusal)return{ok:false,code:e.code,path:e.path};throw e;}};

/* ---------------------------------------------------------------- parts */
// One classified part. CONFIRMED: an id from the allowed list, evidence, no reason. UNKNOWN / CONFLICT: id null and a reason.
function component(c,path,allowed){if(!isObj(c))refuse('TYPE',path);if(!STATUS.includes(c.status))refuse('STATUS_INVALID',path+'.status');
 codes(c.reasons,path+'.reasons');refs(c.evidence_refs,path+'.evidence_refs');
 if(c.status==='CONFIRMED'){text(c.id,path+'.id');if(allowed&&!allowed.includes(c.id))refuse('ID_UNKNOWN',path+'.id');
  if(!c.evidence_refs.length||c.reasons.length)refuse('CONFIRMED_COMPONENT_INVALID',path);}
 else if(c.id!==null||!c.reasons.length)refuse('UNKNOWN_COMPONENT_REQUIRES_NULL_AND_REASON',path);}
function sourceSic(s,path){if(s===null)return;if(!isObj(s))refuse('TYPE',path);text(s.system,path+'.system');if(own(s,'code')&&s.code!==null)text(s.code,path+'.code');}
function applicability(a,path){if(!isObj(a))refuse('TYPE',path);
 if(a.kind==='EVALUATION_ONLY'){day(a.evaluation_date,path+'.evaluation_date');if(a.valid_from!==null||a.valid_to!==null)refuse('EVALUATION_ONLY_IS_NOT_EFFECTIVE_INTERVAL',path);}
 else if(a.kind==='INTERVAL'){for(const f of['valid_from','valid_to'])if(a[f]!==null&&a[f]!==undefined)day(a[f],path+'.'+f);
  if(a.valid_from&&a.valid_to&&a.valid_from>=a.valid_to)refuse('CLASSIFICATION_INTERVAL_INVALID',path);}
 else refuse('APPLICABILITY_INVALID',path+'.kind');}
const VIEW_KEYS=['schema_version','valuation_date','knowledge_as_of','data_kind','members','rows','classification_hash','dictionary_version','mapping_version'];
function checkView(v,path){keys(v,VIEW_KEYS,path);if(v.schema_version!==SCHEMAS.view)refuse('SCHEMA_VERSION',path+'.schema_version');
 if(v.dictionary_version!==VERSIONS.dictionary||v.mapping_version!==VERSIONS.mapping)refuse('CLASSIFICATION_VERSION_INVALID',path+'.dictionary_version');
 day(v.valuation_date,path+'.valuation_date');stamp(v.knowledge_as_of,path+'.knowledge_as_of');
 if(v.valuation_date>v.knowledge_as_of.slice(0,10))refuse('VALUATION_AFTER_KNOWLEDGE',path+'.valuation_date');
 if(!DATA_KINDS.includes(v.data_kind))refuse('DATA_KIND_REQUIRED',path+'.data_kind');hex(v.classification_hash,path+'.classification_hash');
 for(const k of['history_hash','display_hash','dictionary_hash'])if(own(v,k))hex(v[k],path+'.'+k);
 texts(v.members,path+'.members');if(new Set(v.members).size!==v.members.length)refuse('MEMBERS_DUPLICATE',path+'.members');
 const seen=new Set();
 list(v.rows,path+'.rows').forEach((r,i)=>{const p=path+'.rows['+i+']';keys(r,['company_id','issuer_id','record_id','sector','industry','accounting'],p);
  text(r.company_id,p+'.company_id');textOrNull(r.issuer_id,p+'.issuer_id');textOrNull(r.record_id,p+'.record_id');
  if(seen.has(r.company_id))refuse('ROW_DUPLICATE',p+'.company_id');seen.add(r.company_id);
  component(r.sector,p+'.sector',SECTORS);component(r.industry,p+'.industry',null);component(r.accounting,p+'.accounting',null);
  if(r.industry.status==='CONFIRMED'&&r.sector.status!=='CONFIRMED')refuse('INDUSTRY_PARENT_CONFLICT',p+'.industry');
  if(r.record_id===null&&['sector','industry','accounting'].some(f=>r[f].status==='CONFIRMED'))refuse('CONFIRMED_WITHOUT_RECORD',p);
  if(own(r,'source_sic'))sourceSic(r.source_sic,p+'.source_sic');if(own(r,'applicability'))applicability(r.applicability,p+'.applicability');});
 if(seen.size!==v.members.length||v.members.some(m=>!seen.has(m)))refuse('COMMON_VIEW_MEMBERSHIP_MISMATCH',path+'.rows');}
const TECH_KEYS=['schema_version','valuation_date','data_kind','classification_hash','price_basis','groups','input_hash','cache_key','settings_version','rows','diagnostics','security_link_diagnostics','counts'];
function checkTechnical(t,path){keys(t,TECH_KEYS,path,[]);if(t.schema_version!==SCHEMAS.technical)refuse('SCHEMA_VERSION',path+'.schema_version');
 day(t.valuation_date,path+'.valuation_date');if(!DATA_KINDS.includes(t.data_kind))refuse('DATA_KIND_REQUIRED',path+'.data_kind');
 hex(t.classification_hash,path+'.classification_hash');hex(t.input_hash,path+'.input_hash');if(t.cache_key!==t.input_hash)refuse('CACHE_KEY_MISMATCH',path+'.cache_key');
 if(!['RAW','SPLIT_ADJUSTED'].includes(t.price_basis))refuse('ENUM',path+'.price_basis');text(t.settings_version,path+'.settings_version');
 list(t.diagnostics,path+'.diagnostics');list(t.security_link_diagnostics,path+'.security_link_diagnostics');
 keys(t.counts,['original_companies','unclassified_companies','requested_measurements'],path+'.counts',[]);for(const k of Object.keys(t.counts))int(t.counts[k],path+'.counts.'+k);
 const TS_=techReader();if(!TS_)refuse('TECH_READER_MISSING',path);
 const sectors=new Set();
 list(t.groups,path+'.groups').forEach((g,i)=>{const p=path+'.groups['+i+']';keys(g,['sector_id','membership_status','membership_reasons','counts','board'],p,[]);
  if(!SECTORS.includes(g.sector_id)||sectors.has(g.sector_id))refuse('SECTOR_INVALID',p+'.sector_id');sectors.add(g.sector_id);
  if(!['CONFIRMED','UNKNOWN'].includes(g.membership_status))refuse('ENUM',p+'.membership_status');codes(g.membership_reasons,p+'.membership_reasons');
  if((g.membership_status==='CONFIRMED')!==(g.membership_reasons.length===0))refuse('MEMBERSHIP_REASON_MISMATCH',p+'.membership_reasons');
  keys(g.counts,['company_members','confirmed_companies','verified_security_count','unclassified_companies'],p+'.counts',[]);for(const k of Object.keys(g.counts))int(g.counts[k],p+'.counts.'+k);
  const r=TS_.validate(g.board);if(!r.ok)refuse('BOARD_'+r.code,p+'.board'+String(r.path||'').replace(/^\$/,''));const b=g.board;
  if(b.group_id!=='COMMON:'+g.sector_id+':'+t.price_basis)refuse('BOARD_GROUP_ID_MISMATCH',p+'.board.group_id');
  if(b.signal_day!==t.valuation_date)refuse('BOARD_DATE_MISMATCH',p+'.board.signal_day');
  if(b.membership_status!==g.membership_status)refuse('BOARD_MEMBERSHIP_MISMATCH',p+'.board.membership_status');
  if(b.membership_source!==(g.membership_status==='CONFIRMED'?'common-classification:'+t.classification_hash:null))refuse('MEMBERSHIP_SOURCE_MISMATCH',p+'.board.membership_source');});
 const ids=new Set();
 list(t.rows,path+'.rows').forEach((r,i)=>{const p=path+'.rows['+i+']';
  keys(r,['company_id','issuer_id','sector_id','classification_record_id','status','reasons','measurement_status','security_ids'],p,[]);
  text(r.company_id,p+'.company_id');if(ids.has(r.company_id))refuse('ROW_DUPLICATE',p+'.company_id');ids.add(r.company_id);
  textOrNull(r.issuer_id,p+'.issuer_id');textOrNull(r.classification_record_id,p+'.classification_record_id');
  if(r.sector_id!==null&&!SECTORS.includes(r.sector_id))refuse('SECTOR_INVALID',p+'.sector_id');
  if(!['CONFIRMED','UNKNOWN'].includes(r.status))refuse('ENUM',p+'.status');codes(r.reasons,p+'.reasons');
  if(!['COMPLETE','PARTIAL'].includes(r.measurement_status))refuse('ENUM',p+'.measurement_status');texts(r.security_ids,p+'.security_ids');
  if(r.status==='CONFIRMED'&&r.sector_id===null)refuse('CONFIRMED_WITHOUT_SECTOR',p);
  if(r.security_ids.some(s=>s===r.company_id||s===r.issuer_id))refuse('ISSUER_OR_TICKER_IS_NOT_SECURITY_ID',p+'.security_ids');});
 if(t.counts.original_companies!==t.rows.length)refuse('COUNT_MISMATCH',path+'.counts.original_companies');
 for(const g of t.groups){const members=t.rows.filter(r=>r.sector_id===g.sector_id);
  if(g.counts.company_members!==members.length)refuse('COUNT_MISMATCH',path+'.groups.'+g.sector_id+'.counts.company_members');
  if(g.membership_status==='CONFIRMED'&&members.some(r=>r.status!=='CONFIRMED'))refuse('CONFIRMED_GROUP_WITH_UNKNOWN_MEMBER',path+'.groups.'+g.sector_id);}}
const MACRO_ROW=['company_id','issuer_id','classification_record_id','sector','industry','source_classification','source_industry','benchmark','statistic_mapping','probabilities','sector_returns'];
function checkMacro(m,path){keys(m,['schema_version','valuation_date','data_kind','classification_hash','rows','source_link_diagnostics','source_industry_is_common_sector','benchmark_is_common_sector','probabilities','sector_returns'],path,[]);
 if(m.schema_version!==SCHEMAS.macro)refuse('SCHEMA_VERSION',path+'.schema_version');day(m.valuation_date,path+'.valuation_date');
 if(!DATA_KINDS.includes(m.data_kind))refuse('DATA_KIND_REQUIRED',path+'.data_kind');hex(m.classification_hash,path+'.classification_hash');
 // The SIC group and the ETF series are not the common sector; no own sector return or probability is published.
 if(m.source_industry_is_common_sector!==false||m.benchmark_is_common_sector!==false)refuse('SCOPE_CLAIM_NOT_SUPPORTED',path+'.benchmark_is_common_sector');
 if(m.probabilities!==null||m.sector_returns!==null)refuse('ESTIMATE_NOT_SUPPORTED',path+'.probabilities');list(m.source_link_diagnostics,path+'.source_link_diagnostics');
 const ids=new Set();
 list(m.rows,path+'.rows').forEach((r,i)=>{const p=path+'.rows['+i+']';keys(r,MACRO_ROW,p,[]);text(r.company_id,p+'.company_id');
  if(ids.has(r.company_id))refuse('ROW_DUPLICATE',p+'.company_id');ids.add(r.company_id);
  textOrNull(r.issuer_id,p+'.issuer_id');textOrNull(r.classification_record_id,p+'.classification_record_id');
  component(r.sector,p+'.sector',SECTORS);component(r.industry,p+'.industry',null);sourceSic(r.source_classification,p+'.source_classification');
  for(const k of['source_industry','benchmark']){if(!isObj(r[k]))refuse('TYPE',p+'.'+k);text(r[k].system,p+'.'+k+'.system');text(r[k].version,p+'.'+k+'.version');}
  if(r.benchmark.etf!==null&&r.benchmark.etf!==undefined)text(r.benchmark.etf,p+'.benchmark.etf');
  const s=r.statistic_mapping;keys(s,['status','source_links','reasons'],p+'.statistic_mapping',[]);if(!['LINKED','UNKNOWN'].includes(s.status))refuse('ENUM',p+'.statistic_mapping.status');
  list(s.source_links,p+'.statistic_mapping.source_links');codes(s.reasons,p+'.statistic_mapping.reasons');
  if((s.status==='LINKED')!==(s.source_links.length>0))refuse('STATISTIC_LINK_MISMATCH',p+'.statistic_mapping');
  if(r.probabilities!==null||r.sector_returns!==null)refuse('ESTIMATE_NOT_SUPPORTED',p+'.probabilities');});}
function checkLinks(l,path){keys(l,['schema_version','classification_hash','valuation_date','preview_identity','rows'],path,[]);
 if(l.schema_version!==SCHEMAS.qgv_links)refuse('SCHEMA_VERSION',path+'.schema_version');hex(l.classification_hash,path+'.classification_hash');day(l.valuation_date,path+'.valuation_date');
 const pi=l.preview_identity;keys(pi,['preview_id','input_hash','config_hash','cache_key','engine_version'],path+'.preview_identity',[]);
 for(const k of['preview_id','input_hash','config_hash','cache_key'])hex(pi[k],path+'.preview_identity.'+k);text(pi.engine_version,path+'.preview_identity.engine_version');
 const ids=new Set();
 list(l.rows,path+'.rows').forEach((r,i)=>{const p=path+'.rows['+i+']';keys(r,['company_id','issuer_id','classification_record_id'],p,[]);text(r.company_id,p+'.company_id');
  if(ids.has(r.company_id))refuse('ROW_DUPLICATE',p+'.company_id');ids.add(r.company_id);textOrNull(r.issuer_id,p+'.issuer_id');textOrNull(r.classification_record_id,p+'.classification_record_id');});}
function checkDictionary(d,path){keys(d,['schema_version','version','sector_version','sectors','industries'],path);
 if(d.schema_version!==SCHEMAS.dictionary)refuse('SCHEMA_VERSION',path+'.schema_version');if(d.version!==VERSIONS.dictionary)refuse('CLASSIFICATION_VERSION_INVALID',path+'.version');
 if(!isObj(d.sectors))refuse('TYPE',path+'.sectors');for(const k of Object.keys(d.sectors)){if(!SECTORS.includes(k))refuse('SECTOR_INVALID',path+'.sectors.'+k);text(d.sectors[k],path+'.sectors.'+k);}
 const ids=new Set();list(d.industries,path+'.industries').forEach((x,i)=>{const p=path+'.industries['+i+']';keys(x,['id','name','parent_sector'],p);text(x.id,p+'.id');text(x.name,p+'.name');
  if(!SECTORS.includes(x.parent_sector))refuse('SECTOR_INVALID',p+'.parent_sector');if(ids.has(x.id))refuse('ROW_DUPLICATE',p+'.id');ids.add(x.id);});}
const validateView=pass(checkView),validateTechnical=pass(checkTechnical),validateMacro=pass(checkMacro),validateLinks=pass(checkLinks),validateDictionary=pass(checkDictionary);

/* ---------------------------------------------------------------- the bundle: one view and the parts that read the same records */
const PARTS=['technical','macro','qgv_links'];
const CHECK={view:checkView,technical:checkTechnical,macro:checkMacro,qgv_links:checkLinks,dictionary:checkDictionary};
// A part reads the view's records when it has the view's hash and date and, for every company it names, the view's record id
// and issuer id (and names every member).
function partMismatch(view,part,name){
 if(part.classification_hash!==view.classification_hash)return'CLASSIFICATION_HASH_MISMATCH';if(part.valuation_date!==view.valuation_date)return'VALUATION_DATE_MISMATCH';
 if(own(part,'data_kind')&&part.data_kind!==view.data_kind)return'DATA_KIND_MISMATCH';
 const byId=new Map(view.rows.map(r=>[r.company_id,r]));if(part.rows.length!==view.rows.length)return'MEMBERS_MISMATCH';
 for(const r of part.rows){const v=byId.get(r.company_id);if(!v)return'MEMBERS_MISMATCH';if(r.classification_record_id!==v.record_id)return'RECORD_ID_MISMATCH';if(r.issuer_id!==v.issuer_id)return'ISSUER_ID_MISMATCH';}
 return null;}
// validate({view, technical?, macro?, qgv_links?, dictionary?}) → {ok:true, value:{view, technical, macro, qgv_links, dictionary,
// mismatch:{part: code}}} or {ok:false, code, path}. A part that is well formed but reads other records is kept in mismatch only.
function validate(json){
 try{if(!isObj(json))refuse('TYPE','$');keys(json,['view'],'$',['view','dictionary',...PARTS]);const v=copy(json,'$',0);
  for(const k of Object.keys(v))if(v[k]!==null)CHECK[k](v[k],'$.'+k);if(v.view===null)refuse('VIEW_REQUIRED','$.view');
  const out={view:v.view,dictionary:v.dictionary||null,mismatch:{}};
  for(const k of PARTS){out[k]=null;if(!v[k])continue;const why=partMismatch(v.view,v[k],k);if(why)out.mismatch[k]=why;else out[k]=v[k];}
  return{ok:true,value:deepFreeze(out)};}
 catch(e){if(e instanceof Refusal)return{ok:false,code:e.code,path:e.path};throw e;}}

/* ---------------------------------------------------------------- source and the loaded state (RAM) */
const TEXT=WORDS;
/* Private delivery (owner 2026-11-08 「통합 결과 수령」 2항): the held bundle comes only through the owner-checked private Worker
   (IS2.privateExpand kind 'classification' → the IS2.kisPrivate classification route, one click). connectPrivate(payload) checks it
   whole and keeps it in RAM as the current source (delivery PRIVATE: 비공개 보관본 · 인증 경로 · 게시본 아님); disconnectPrivate()
   drops it (접기 / 연결 끊기 / 403). Nothing is stored or sent. No public classification file is a precondition: without the
   private delivery the source stays NONE. subscribe(fn) tells open screens that the source changed. */
let privatePayload=null,generation=0;const listeners=new Set();
const notify=()=>{for(const f of[...listeners]){try{f();}catch(_){}}};
function connectPrivate(payload){const r=validate(payload);if(!r.ok)return Object.freeze({ok:false,code:r.code,path:r.path});
 privatePayload=payload;generation++;notify();return Object.freeze({ok:true,value:r.value});}
function disconnectPrivate(){if(privatePayload===null)return;privatePayload=null;generation++;notify();}
const subscribe=fn=>{listeners.add(fn);return()=>listeners.delete(fn);};
function source(){if(privatePayload!==null)return Promise.resolve(Object.freeze({state:'OK',code:null,payload:privatePayload,delivery:'PRIVATE',text:WORDS.PRIVATE}));
 return Promise.resolve(Object.freeze({state:'NONE',code:'CLASSIFICATION_NOT_CONNECTED',payload:null,text:WORDS.NONE}));}
const api=()=>{const I=root&&root.IS2;return I&&I.classification&&typeof I.classification.source==='function'?I.classification:self;};
let current=Object.freeze({state:'NOT_LOADED',code:null,value:null}),loadP=null,loadFn=null,loadGen=-1;
function load(){const fn=api().source;if(loadP&&loadFn===fn&&loadGen===generation)return loadP;loadFn=fn;loadGen=generation;current=Object.freeze({state:'LOADING',code:null,value:null});
 let p;try{p=Promise.resolve(fn());}catch(e){p=Promise.reject(e);}
 const mine=loadP=p.then(src=>{if(!src||src.state!=='OK')return Object.freeze({state:src&&src.state==='NONE'?'NONE':'ERROR',code:src&&src.code||'CLASSIFICATION_SOURCE_FAILED',value:null});
   const r=validate(src.payload);return r.ok?Object.freeze({state:'OK',code:null,value:r.value,delivery:src.delivery==='PRIVATE'?'PRIVATE':'PUBLIC'}):Object.freeze({state:'INVALID',code:r.code,path:r.path,value:null});},
  ()=>Object.freeze({state:'ERROR',code:'CLASSIFICATION_SOURCE_FAILED',value:null})).then(st=>{if(loadP===mine)current=st;return st;});
 return mine;}
// The loaded state; a source swapped since the last load (tests) counts as not loaded until load() runs again.
const state=()=>(loadFn===api().source&&loadGen===generation?current:Object.freeze({state:'NOT_LOADED',code:null,value:null}));
const value=()=>{const s=state();return s.state==='OK'?s.value:null;};

/* ---------------------------------------------------------------- words and records */
const sectorName=(id,dict)=>{const d=dict||(value()&&value().dictionary);return id&&d&&d.sectors&&own(d.sectors,id)?d.sectors[id]:id;};
const industryName=(id,dict)=>{const d=dict||(value()&&value().dictionary),x=id&&d?d.industries.find(i=>i.id===id):null;return x?x.name:id;};
const unresolved=reasons=>reasons.find(r=>/UNRESOLVED/.test(r))||null;
// The state of one view row (Codex's statuses and reasons, worded; nothing inferred).
function rowState(row,valuation_date){const s=row.sector,i=row.industry,first=s.reasons[0]||null;
 if(s.status==='CONFLICT')return{state:STATE.CONFLICT,words:WORDS.CONFLICT,reason:first};
 if(s.status==='CONFIRMED'){if(i.status==='CONFIRMED')return{state:STATE.CONFIRMED,words:WORDS.CONFIRMED,reason:null};
  return{state:STATE.SECTOR_ONLY,words:i.status==='CONFLICT'?WORDS.SECTOR_INDUSTRY_CONFLICT:WORDS.SECTOR_ONLY,reason:i.reasons[0]||null};}
 const u=unresolved(s.reasons);if(u)return{state:STATE.UNRESOLVED,words:WORDS.UNRESOLVED+' ('+u+')',reason:u};
 if(s.reasons.some(r=>DATE_REASONS.includes(r)))return{state:STATE.NOT_APPLICABLE_ON_DATE,words:dateWords(valuation_date),reason:s.reasons.find(r=>DATE_REASONS.includes(r))};
 return{state:STATE.NO_DATA,words:WORDS.NO_DATA,reason:first};}
const part=c=>Object.freeze({id:c.id,status:c.status,reasons:Object.freeze([...c.reasons])});
// The accounting model (회계모형 = 계산 규칙, DC-48) is its own state (Codex #516 4cf2e037 HELD_REVIEW.md): a confirmed sector with an
// unknown accounting model shows its sector but is never a complete QGV peer group; an accounting model may be confirmed while the
// sector is not. peer_complete = both confirmed (the words only; the QGV engine still decides its own comparison group).
function accountingOf(row){const a=row.accounting,s=row.sector;
 if(a.status==='CONFIRMED')return{accounting_state:'CONFIRMED',peer_complete:s.status==='CONFIRMED',accounting_words:s.status==='CONFIRMED'?null:WORDS.ACCOUNTING_WITHOUT_SECTOR};
 return{accounting_state:a.status,peer_complete:false,accounting_words:a.status==='CONFLICT'?WORDS.ACCOUNTING_CONFLICT:WORDS.ACCOUNTING_UNKNOWN};}
// recordFor(company_id, valuation_date = the view's) → a frozen record answer, always with state + words.
function recordFor(company_id,valuation_date=null,bundle=null){const b=bundle||value(),s=state();
 const base={company_id:typeof company_id==='string'?company_id:null,issuer_id:null,security_id:null,record_id:null,classification_hash:null,
  dictionary_version:null,mapping_version:null,valuation_date:valuation_date||null,knowledge_as_of:null,data_kind:null,sector:null,industry:null,accounting:null,source_sic:null,applicability:null,
  accounting_state:null,peer_complete:false,accounting_words:null,delivery:null};
 if(!b)return Object.freeze({...base,state:STATE.NO_DATA,words:WORDS.NO_DATA,reason:s.state==='INVALID'?s.code:'CLASSIFICATION_NOT_CONNECTED'});
 const v=b.view,when=valuation_date||v.valuation_date,head={...base,classification_hash:v.classification_hash,dictionary_version:v.dictionary_version,mapping_version:v.mapping_version,
  valuation_date:when,knowledge_as_of:v.knowledge_as_of,data_kind:v.data_kind,delivery:s.delivery||null};
 if(when!==v.valuation_date)return Object.freeze({...head,state:STATE.NOT_APPLICABLE_ON_DATE,words:dateWords(when),reason:'VALUATION_DATE_MISMATCH'});
 const row=v.rows.find(r=>r.company_id===company_id);
 if(!row)return Object.freeze({...head,state:STATE.NO_DATA,words:WORDS.NO_DATA,reason:'CLASSIFICATION_RECORD_MISSING'});
 const st=rowState(row,when);
 return Object.freeze({...head,...st,...accountingOf(row),issuer_id:row.issuer_id,record_id:row.record_id,sector:part(row.sector),industry:part(row.industry),accounting:part(row.accounting),
  source_sic:row.source_sic?Object.freeze({system:row.source_sic.system,code:row.source_sic.code||null}):null,applicability:row.applicability?deepFreeze(copy(row.applicability,'$',0)):null});}
// The record id a part (technical / macro / qgv_links) gives one company, or null; a part in mismatch gives VERSION_MISMATCH.
function partRecord(name,company_id,bundle=null){const b=bundle||value();if(!b||!PARTS.includes(name))return null;
 if(own(b.mismatch,name))return Object.freeze({state:STATE.VERSION_MISMATCH,words:WORDS.VERSION_MISMATCH,reason:b.mismatch[name],classification_record_id:null,classification_hash:null});
 const p=b[name];if(!p)return null;const r=p.rows.find(x=>x.company_id===company_id);
 return r?Object.freeze({state:'OK',company_id,issuer_id:r.issuer_id,classification_record_id:r.classification_record_id,classification_hash:p.classification_hash,valuation_date:p.valuation_date}):null;}
// Same record: company, record id, classification hash, versions and evaluation date (each side as recordFor or a part row).
function sameRecord(a,b){if(!isObj(a)||!isObj(b))return false;const id=x=>own(x,'record_id')?x.record_id:x.classification_record_id;
 if(!id(a)||id(a)!==id(b)||!a.classification_hash||a.classification_hash!==b.classification_hash||a.company_id!==b.company_id)return false;
 for(const k of['dictionary_version','mapping_version','valuation_date'])if(a[k]&&b[k]&&a[k]!==b[k])return false;return true;}
const shortHash=h=>(typeof h==='string'?h.slice(0,12):null);

/* ---------------------------------------------------------------- the tech filter: the confirmed board group's full rows */
const GROUP=/^COMMON:([A-Z_]+):(RAW|SPLIT_ADJUSTED)$/;
/* technical-filter-membership/1 (Codex #516 5b0ec88a common_classification.group_join.build_group_manifest; GROUP_JOIN.md): the
   dated group roster from the checked view and technical projection only — never from requested rows, measurements, filter or
   join results. Same checks, order and codes; universe_members_hash = sector_qgv.digest(sorted(members)) (compact JSON). */
function GroupRefusal(code){this.code=code;}
const gno=code=>{throw new GroupRefusal(code);};
const sectorOf=row=>(row.sector&&row.sector.status==='CONFIRMED'&&SECTORS.includes(row.sector.id)?row.sector.id:null);
function applies(row,d){const a=isObj(row.applicability)?row.applicability:{};
 if(a.kind==='EVALUATION_ONLY')return a.evaluation_date===d&&(a.valid_from===null||a.valid_from===undefined)&&(a.valid_to===null||a.valid_to===undefined);
 if(a.kind==='INTERVAL'&&a.valid_from)return a.valid_from<=d&&(a.valid_to===null||a.valid_to===undefined||d<a.valid_to);return false;}
function buildGroupManifest(view,technical,group_id){
 const TS_=techReader();if(!TS_)gno('TECH_READER_MISSING');const companies=new Map(view.rows.map(r=>[r.company_id,r]));
 if(['universe_id','universe_version'].some(k=>typeof view[k]!=='string'||!view[k]))gno('GROUP_UNIVERSE_CONTEXT_REQUIRED');
 if(technical.schema_version!==SCHEMAS.technical)gno('GROUP_PROJECTION_SCHEMA_MISMATCH');
 for(const k of['valuation_date','classification_hash','data_kind'])if(technical[k]!==view[k])gno('GROUP_PROJECTION_CONTEXT_MISMATCH:'+k);
 const projected=technical.rows||[],ids=new Set(projected.map(r=>r.company_id));
 if(projected.length!==companies.size||ids.size!==companies.size||[...ids].some(k=>!companies.has(k)))gno('GROUP_PROJECTION_MEMBERS_MISMATCH');
 const byCode=new Map(projected.map(r=>[r.company_id,r]));
 for(const[code,row]of companies){const p=byCode.get(code);if(p.issuer_id!==row.issuer_id||p.classification_record_id!==row.record_id||p.sector_id!==sectorOf(row))gno('GROUP_PROJECTION_RECORD_MISMATCH');}
 const found=(technical.groups||[]).filter(g=>g.board.group_id===group_id);if(found.length!==1)gno('GROUP_PROJECTION_GROUP_MISMATCH');
 const group=found[0],board=group.board,basis=technical.price_basis;
 if(group_id!=='COMMON:'+group.sector_id+':'+basis||board.signal_day!==view.valuation_date||board.membership_status!==group.membership_status)gno('GROUP_PROJECTION_CONTEXT_MISMATCH:board');
 if(board.membership_source!==(group.membership_status==='CONFIRMED'?'common-classification:'+view.classification_hash:null))gno('GROUP_PROJECTION_CONTEXT_MISMATCH:classification_hash');
 const relevant=view.rows.filter(r=>sectorOf(r)===group.sector_id);if(group.counts.company_members!==relevant.length)gno('GROUP_PROJECTION_MEMBERS_MISMATCH');
 const reasons=[...(group.membership_reasons||[])];if([...companies.values()].some(r=>sectorOf(r)===null))reasons.push('CLASSIFICATION_POPULATION_INCOMPLETE');
 const members=[];
 for(const row of relevant){const p=byCode.get(row.company_id),sids=p.security_ids||[];
  if(p.status!=='CONFIRMED'||sids.length!==1)reasons.push('GROUP_MEMBER_SECURITY_UNCONFIRMED');
  if(!applies(row,view.valuation_date))reasons.push('CLASSIFICATION_APPLICABILITY_UNCONFIRMED');
  if(!row.record_id||!row.issuer_id)reasons.push('GROUP_MEMBER_EVIDENCE_UNCONFIRMED');
  const refs=Array.isArray(row.source_refs)&&row.source_refs.length?row.source_refs:row.sector.evidence_refs||[];
  members.push({company_id:row.company_id,issuer_id:row.issuer_id,classification_record_id:row.record_id,security_id:sids.length===1?sids[0]:null,evidence_refs:[...refs]});}
 if(group.membership_status!=='CONFIRMED'&&!reasons.length)reasons.push('GROUP_MEMBERSHIP_UNCONFIRMED');
 const context={signal_day:view.valuation_date,group_id,classification_hash:view.classification_hash,population_hash:board.population_hash,
  universe_id:view.universe_id,universe_version:view.universe_version,universe_members_hash:TS_.sha256(JSON.stringify([...view.members].sort())),
  dictionary_version:view.dictionary_version,mapping_version:view.mapping_version,knowledge_as_of:view.knowledge_as_of,price_basis:basis};
 return deepFreeze({schema_version:'technical-filter-membership/1',data_kind:view.data_kind,context,membership_status:reasons.length?'UNKNOWN':'CONFIRMED',
  reasons:[...new Set(reasons)].sort(),members});}
// The /2 call-site input for a COMMON:<sector>:<basis> board (screen-tech-filter-live keep): the trusted roster, the request
// context pinned from the loaded record set and the requested board group, and the universe rows whose code is a roster member
// (every such row, duplicates included, unchanged; out-of-group rows are never passed). {mode:'NONE'} for any other board (the
// /1 identity-only path, completeness NOT_CHECKED). code = why no roster could be made (no join).
function groupInput(board,universe,bundle=null){
 if(!isObj(board)||!GROUP.test(typeof board.group_id==='string'?board.group_id:''))return Object.freeze({mode:'NONE'});
 const no=code=>Object.freeze({mode:'V2',code,rows:null,manifest:null,context:null}),b=bundle||value();
 if(!b)return no('CLASSIFICATION_NOT_CONNECTED');if(own(b.mismatch,'technical'))return no('CLASSIFICATION_VERSION_MISMATCH');
 const t=b.technical;if(!t)return no('TECHNICAL_PROJECTION_NOT_CONNECTED');
 if(!t.groups.some(g=>g.board.group_id===board.group_id))return no('BOARD_GROUP_NOT_IN_PROJECTION');
 let manifest;try{manifest=buildGroupManifest(b.view,t,board.group_id);}catch(e){if(e instanceof GroupRefusal)return no(e.code);throw e;}
 const v=b.view,g=t.groups.find(x=>x.board.group_id===board.group_id);
 const context=Object.freeze({signal_day:v.valuation_date,group_id:board.group_id,classification_hash:v.classification_hash,population_hash:g.board.population_hash,
  universe_id:v.universe_id,universe_version:v.universe_version,universe_members_hash:manifest.context.universe_members_hash,dictionary_version:v.dictionary_version,
  mapping_version:v.mapping_version,knowledge_as_of:v.knowledge_as_of,price_basis:t.price_basis});
 const codes=new Set(manifest.members.map(m=>m.company_id)),rows=(Array.isArray(universe)?universe:[]).filter(r=>isObj(r)&&codes.has(r.code));
 return Object.freeze({mode:'V2',code:null,manifest,context,rows:Object.freeze(rows)});}
// groupRowsWhy (identity-only consumers, e.g. Codex's consumer probe): the confirmed roster's rows, each exactly once, checked like
// the /2 roster check — a row classification_hash / classification_record_id that differs is refused (never overwritten); a
// non-null issuer that differs is refused; a null / absent issuer is connected from the roster member of the same code, record,
// hash and date with evidence, on a copy carrying issuer_connection (the original row is unchanged).
function groupRowsWhy(board,universe,bundle=null){const no=code=>Object.freeze({rows:null,code});
 if(!isObj(board))return no('NO_BOARD');if(!GROUP.test(typeof board.group_id==='string'?board.group_id:''))return no(bundle||value()?'BOARD_GROUP_NOT_COMMON':'CLASSIFICATION_NOT_CONNECTED');
 const gi=groupInput(board,universe,bundle);if(gi.code)return no(gi.code);const b=bundle||value(),t=b.technical,g=t.groups.find(x=>x.board.group_id===board.group_id);
 if(board.signal_day!==t.valuation_date)return no('BOARD_DATE_MISMATCH');
 if(board.membership_source!==g.board.membership_source||board.population_hash!==g.board.population_hash)return no('CLASSIFICATION_VERSION_MISMATCH');
 if(gi.manifest.membership_status!=='CONFIRMED'||board.membership_status!=='CONFIRMED')return no('GROUP_MEMBERSHIP_UNCONFIRMED');
 const out=[],c=gi.context;
 for(const m of gi.manifest.members){const hit=gi.rows.filter(r=>r.code===m.company_id);if(hit.length!==1)return no('MEMBER_NOT_MAPPED');const r=hit[0];
  if(own(r,'classification_hash')&&r.classification_hash!==c.classification_hash)return no('ROW_CLASSIFICATION_MISMATCH');
  if(own(r,'classification_record_id')&&r.classification_record_id!==m.classification_record_id)return no('ROW_CLASSIFICATION_MISMATCH');
  if(r.issuer_id!==null&&r.issuer_id!==undefined){if(r.issuer_id!==m.issuer_id)return no('ISSUER_MISMATCH');out.push(Object.freeze({...r}));continue;}
  if(!m.evidence_refs.length)return no('ISSUER_CONNECTION_EVIDENCE_REQUIRED');
  out.push(Object.freeze({...r,issuer_id:m.issuer_id,issuer_connection:Object.freeze({previous_field_present:own(r,'issuer_id'),previous_issuer_id:own(r,'issuer_id')?r.issuer_id:null,
   classification_record_id:m.classification_record_id,classification_hash:c.classification_hash,signal_day:c.signal_day,knowledge_as_of:c.knowledge_as_of,
   evidence_refs:m.evidence_refs,basis:'VERIFIED_CLASSIFICATION_RECORD'})}));}
 return Object.freeze({rows:Object.freeze(out),code:null});}
function groupRows(board,universe){return groupRowsWhy(board,universe).rows;}
const groupText=code=>(own(GROUP_TEXT,code)?GROUP_TEXT[code]:'사유 코드 미등록');

/* ---------------------------------------------------------------- 2.2.7 섹터 QGV preview × 분류 연결 기록 (Codex GROUP_JOIN.md
   "2.2.7 인계"): a sector-qgv preview is read against the record set only when common-classification-qgv-links/1 names exactly
   that preview (preview_id, input_hash, config_hash, cache_key, engine_version) on the same valuation date; then each result row
   finds its classification_record_id by company_id (rows without one stay, with their reason). Anything else is its own state
   and no row is matched (never a silent mix). */
const PREVIEW_STATE=Object.freeze({OK:'분류 기록 대조 · 같은 미리보기 · 같은 분류 기록',NONE:'공통 분류 기록 미연결 · 분류 대조 안 함',LINKS_NONE:'섹터 QGV 분류 연결 기록 없음 · 분류 대조 안 함',
 VERSION_MISMATCH:'분류 버전 불일치 · 분류 연결 기록을 쓰지 않음',PREVIEW_NOT_LINKED:'이 미리보기는 분류 연결 기록의 미리보기와 다름 · 분류 기록과 섞지 않음',
 DATE_MISMATCH:'미리보기 기준일 ≠ 분류 평가일 · 분류 기록과 섞지 않음',PREVIEW_INVALID:'미리보기 형식 오류 · 분류 대조 안 함'});
const PREVIEW_IDENTITY=Object.freeze(['preview_id','input_hash','config_hash','cache_key','engine_version']);
function previewCheck(preview,bundle=null){const b=bundle||value(),st=(state,extra={})=>Object.freeze({state,words:PREVIEW_STATE[state],rows:null,...extra});
 if(!isObj(preview)||!Array.isArray(preview.result_rows))return st('PREVIEW_INVALID');if(!b)return st('NONE');
 if(own(b.mismatch,'qgv_links'))return st('VERSION_MISMATCH',{reason:b.mismatch.qgv_links});const l=b.qgv_links;if(!l)return st('LINKS_NONE');
 const differs=PREVIEW_IDENTITY.filter(k=>preview[k]!==l.preview_identity[k]);if(differs.length)return st('PREVIEW_NOT_LINKED',{differs:Object.freeze(differs)});
 if(preview.valuation_date!==l.valuation_date)return st('DATE_MISMATCH');
 const links=new Map(l.rows.map(r=>[r.company_id,r])),views=new Map(b.view.rows.map(r=>[r.company_id,r])),rows=new Map();let missing=0;
 for(const r of preview.result_rows){const x=links.get(r.company_id),v=views.get(r.company_id);
  if(!x){missing++;rows.set(r.company_id,Object.freeze({record_id:null,reason:'CLASSIFICATION_LINK_MISSING'}));continue;}
  if(!v||x.classification_record_id!==v.record_id||(r.issuer_id!==undefined&&r.issuer_id!==null&&x.issuer_id!==null&&r.issuer_id!==x.issuer_id))return st('VERSION_MISMATCH',{reason:'ROW_RECORD_MISMATCH:'+r.company_id});
  rows.set(r.company_id,Object.freeze({record_id:x.classification_record_id,reason:x.classification_record_id?null:'CLASSIFICATION_RECORD_ABSENT'}));}
 return Object.freeze({state:'OK',words:PREVIEW_STATE.OK,rows,missing,classification_hash:l.classification_hash,valuation_date:l.valuation_date,preview_id:l.preview_identity.preview_id});}

/* ---------------------------------------------------------------- small samples, kept apart */
// kind 'TECH' (minimum 10: no decile below, rank and median kept) or 'SECTOR_QGV' (minimum 20: no factor score below);
// metric = {n_valid, membership_status}. Identity / membership unknown → no rank and no median either.
const MIN=Object.freeze({TECH:10,SECTOR_QGV:20});
function sample(kind,{n_valid=null,membership_status='CONFIRMED'}={}){const min=MIN[kind];if(!min)throw Error('SAMPLE_KIND_INVALID');
 if(membership_status!=='CONFIRMED'||n_valid===null)return Object.freeze({state:'GROUP_UNCONFIRMED',words:WORDS.GROUP_UNCONFIRMED,min,n_valid:null,rank:false,median:false,decile:false,score:false});
 if(n_valid===0)return Object.freeze({state:'EMPTY_GROUP',words:WORDS.EMPTY_GROUP,min,n_valid,rank:false,median:false,decile:false,score:false});
 if(n_valid<min)return Object.freeze({state:'SAMPLE_SMALL',words:'표본 부족 · 유효 N '+n_valid+' < '+min+(kind==='TECH'?' · 분위·상하위10% 미산출 · 순위·중앙값 유지':' · 요소 점수 미산출'),
  min,n_valid,rank:kind==='TECH',median:kind==='TECH',decile:false,score:false});
 return Object.freeze({state:'OK',words:null,min,n_valid,rank:true,median:true,decile:kind==='TECH',score:true});}

/* ---------------------------------------------------------------- hash context between screens */
const CTX=/^cc:([A-Z_]+|-):([a-z0-9_]+|-):(\d{4}-\d{2}-\d{2}):([0-9a-f]{12})$/;
function context({sector=null,industry=null}={},bundle=null){const b=bundle||value();if(!b)return null;
 if(sector!==null&&!SECTORS.includes(sector))return null;if(industry!==null&&!/^[a-z0-9_]+$/.test(industry))return null;
 return'cc:'+(sector||'-')+':'+(industry||'-')+':'+b.view.valuation_date+':'+shortHash(b.view.classification_hash);}
function parseContext(token){const m=typeof token==='string'?CTX.exec(token):null;if(!m)return null;
 return Object.freeze({sector:m[1]==='-'?null:m[1],industry:m[2]==='-'?null:m[2],valuation_date:m[3],hash12:m[4]});}
function contextState(token,bundle=null){const c=parseContext(token);if(!c)return'INVALID';const b=bundle||value();if(!b)return'NOT_CONNECTED';
 if(c.hash12!==shortHash(b.view.classification_hash))return'VERSION_MISMATCH';if(c.valuation_date!==b.view.valuation_date)return'DATE_MISMATCH';
 if(c.sector&&!SECTORS.includes(c.sector))return'INVALID';return'OK';}
// The sectors / industries the view's records confirm (for filter options), with counts; never adds a sector it does not hold.
function options(bundle=null){const b=bundle||value();if(!b)return null;const sec=new Map(),ind=new Map(),add=(m,k)=>m.set(k,m.has(k)?m.get(k)+1:1);
 for(const r of b.view.rows){if(r.sector.status==='CONFIRMED')add(sec,r.sector.id);if(r.industry.status==='CONFIRMED')add(ind,r.sector.id+'|'+r.industry.id);}
 return Object.freeze({sectors:Object.freeze([...sec].sort((a,b)=>SECTORS.indexOf(a[0])-SECTORS.indexOf(b[0])).map(([id,n])=>Object.freeze({id,n}))),
  industries:Object.freeze([...ind].sort((a,b)=>a[0]<b[0]?-1:1).map(([k,n])=>{const[sector,id]=k.split('|');return Object.freeze({sector,id,n});}))});}
// One row passes the common filter {sector, industry} ('' = all): CONFIRMED sector equal, and CONFIRMED industry equal when
// asked; 'UNCLASSIFIED' = the record's sector is not CONFIRMED. Only hides rows: scores, ranks and denominators are the caller's.
function matches(rec,{sector='',industry=''}={}){if(!sector)return true;if(!rec||!rec.sector)return sector==='UNCLASSIFIED';
 if(sector==='UNCLASSIFIED')return rec.sector.status!=='CONFIRMED';if(rec.sector.status!=='CONFIRMED'||rec.sector.id!==sector)return false;
 if(!industry)return true;if(industry==='UNCLASSIFIED')return rec.industry.status!=='CONFIRMED';return rec.industry.status==='CONFIRMED'&&rec.industry.id===industry;}

const self=Object.freeze({SCHEMAS,VERSIONS,SECTORS,STATE,WORDS,TEXT,GROUP_TEXT,DATE_REASONS,MIN,buildGroupManifest:(v,t,g)=>{try{return{ok:true,value:buildGroupManifest(v,t,g)};}catch(e){if(e instanceof GroupRefusal)return{ok:false,code:e.code};throw e;}},groupInput,previewCheck,PREVIEW_STATE,validate,validateView,validateTechnical,validateMacro,validateLinks,validateDictionary,
 source,load,state,value,connectPrivate,disconnectPrivate,subscribe,recordFor,partRecord,sameRecord,rowState,dateWords,sectorName,industryName,shortHash,groupRows,groupRowsWhy,groupText,sample,
 context,parseContext,contextState,options,matches});
return self;
});
