/* 의외의 기업 reader (IS2.discovery; owner 2026-11-06, features 2.1.8 list and 2.4.6 mark). Reads Codex's discovery-company/v1
   as delivered in #503 (998414635aa4f1899748b1b76fc7ebf3ddc9d12f: implementation/docs/research/discovery_company/CONTRACT.md,
   schema.json, synthetic.json) with no conversion: one record per company with three layers — evidence (source extracts),
   judgments (reviewed claims with status, evidence and counterevidence) and display (what the screens show) — plus the state
   history. Selection, review and the display layer are Codex's (DC-42); this file only checks, joins and orders.
   - Input: one record, an array of records, or Codex's synthetic bundle {synthetic_only:true, cases:[{case_id, record,
     expected}]} (its expected blocks are kept aside, never read as data). One record per company (DUPLICATE_COMPANY).
   - validate(json) → {ok:true, value:{data_kind, records}} (deep-frozen) or {ok:false, code, path}: the whole input refused at
     its first fault. Besides the schema's keys, constants and enums it checks what the screens rely on: the display agrees with
     the state (list_eligible and mark: SELECTED → SELECTED, REVIEW_REQUIRED → REVIEW_REQUIRED, every other state → not listed,
     no mark; DISPLAY_STATE_MISMATCH), display.state_reason equals state_reason, a listed or past-selection state has a first
     selection time, a SELECTED record has no blocked gate, unresolved core claim or material refutation (GATES_OPEN), every
     shown judgment and risk is one of the record's own (DISPLAY_REF), every evidence id a judgment cites exists (EVIDENCE_REF),
     publication_approved is false.
   - view(value, {get, now}) → {entries, byId, dropped, hidden}: get = IS2.companies.get. The join is qgv_ref.company_id, the
     existing company key (never a ticker string); an unknown key or a listing-ended company is dropped with its reason. Only
     SELECTED and REVIEW_REQUIRED are entries (list and mark); CANDIDATE / IN_REVIEW / SUSPENDED / REMOVED are counted in hidden.
   - sort / filter / facets order and hide entries only: no new score, the official QGV rank stays the publication's, and a
     company without QGV stays listed (QGV 미산출 group, never 0).
   - source() → Promise {state:'NONE'}: no public file and no request. SELECTED is a research state; display.list_eligible is
     not a publication approval (publication_approved is always false in the producer); publishing reuses the existing approval.
   Text is plain text and reaches the page only as text nodes. Pure except source(). Nothing here stores or sends anything. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else{const I=root.IS2=root.IS2||{};I.discovery=api;}})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
const SCHEMA='discovery-company/v1',RULES='discovery-rules/1';
const STATES=Object.freeze(['CANDIDATE','IN_REVIEW','SELECTED','REVIEW_REQUIRED','SUSPENDED','REMOVED']);
const LISTED=Object.freeze(['SELECTED','REVIEW_REQUIRED']);
const CATEGORIES=Object.freeze(['IDENTITY','BUSINESS','DISCOVERY','ATTRACTIVENESS','COUNTER_REVIEW','CURRENTNESS','TYPE','STRENGTH','REGION','SIGNAL','RISK','AWARENESS']);
const GATES=Object.freeze(['IDENTITY','BUSINESS','DISCOVERY','ATTRACTIVENESS','COUNTER_REVIEW','CURRENTNESS']);
const EVENTS=Object.freeze(['CORE_EVIDENCE_ERROR','DOCUMENT_CHANGED','EVIDENCE_AGED','IDENTITY_ERROR','MATERIAL_REFUTATION','NEW_FILING']);
const DISPLAY_J=Object.freeze(['business','discovery_reason','selection_summary','strengths','regions','signals','types','risk_judgments']);
// The company-page panel (owner ①–⑥; ⑦ is the evidence block): display keys, words on the screen.
const SECTIONS=Object.freeze(['discovery_reason','types','strengths','regions','signals','risks']);
const SECTION_TEXT=Object.freeze({discovery_reason:'이 기업을 발견한 이유',types:'기업 유형',strengths:'눈여겨볼 사업 강점',regions:'사업지역과 성장 여력',signals:'추가로 주목할 신호',risks:'함께 확인할 위험'});
// Codex's descriptive type codes (CONTRACT.md); the screen never names them after the book.
const TYPE_TEXT=Object.freeze({SLOW_GROWER:'저성장',STALWART:'대형 우량',FAST_GROWER:'고성장',CYCLICAL:'경기순환',TURNAROUND:'회생',ASSET_PLAY:'자산 가치'});
const SIGNAL_TEXT=Object.freeze({SPINOFF:'분사',INSIDER_OPEN_MARKET_PURCHASE:'내부자 장내 매수',INSIDER_COMPENSATION:'내부자 보상',BUYBACK_PLAN:'자사주 매입 계획',BUYBACK_EXECUTED:'자사주 매입 실행',SHARE_COUNT_CHANGE:'주식 수 변화'});
const REGION_TEXT=Object.freeze({REVENUE:'매출 지역',PRODUCTION:'생산 지역',HEADQUARTERS:'본사',PERFORMANCE:'지역 성과',REPLICATION:'다른 지역 확장성',PROFITABILITY:'지역 수익성',EXPANSION:'확장',SATURATION:'포화',PROTECTION:'보호 요인',ACQUISITION_EFFECT:'인수 효과',FX_EFFECT:'환율 효과'});
const STATUS_TEXT=Object.freeze({CONFIRMED:'확인',UNCONFIRMED:'미확인',REFUTED:'반박됨'});
const SORTS=Object.freeze([['recent','최근 선정순 (기본)'],['name','기업명순'],['qgv','기존 QGV순']]);
const BANNED=Object.freeze(['린치 유형','린치유형','8장 특성','8장특성']);
const TEXT=Object.freeze({NONE:'의외의 기업 자료가 아직 연결되지 않았습니다',
 NONE_WHY:'선정·근거는 연구 담당(Codex, discovery-company/v1) · 연구상 선정은 공개 승인이 아님 · 공개는 기존 게시 승인 절차',
 LOADING:'불러오는 중',FAILED:'의외의 기업 자료를 불러오지 못했습니다',INVALID:'의외의 기업 파일이 규격과 달라 파일 전체를 쓰지 않습니다',
 EMPTY:'선정된 의외의 기업이 없습니다',FILTER_EMPTY:'이 조건에 맞는 의외의 기업이 없습니다',SYNTHETIC:'합성 데이터 · 시험용 · 실제 선정 아님',
 PARTIAL:'일부 근거 미확인',REVIEW:'선정 근거 재검토 필요',MARK:'의외의 기업'});
const MAX=Object.freeze({records:2000,list:500,text:4000});
const SHA=/^[0-9a-f]{64}$/,HTTP=/^https?:\/\//,TIME=/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?Z$/,DAY=/^\d{4}-\d{2}-\d{2}$/;
const own=(o,k)=>Object.prototype.hasOwnProperty.call(o,k);
const isObj=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
function Refusal(code,path){this.code=code;this.path=path;}
const refuse=(code,path)=>{throw new Refusal(code,path);};
function keys(o,want,path){if(!isObj(o))refuse('TYPE',path);for(const k of want)if(!own(o,k))refuse('KEY_MISSING',path+'.'+k);for(const k of Object.keys(o))if(!want.includes(k))refuse('KEY_UNKNOWN',path+'.'+k);}
const arr=(v,path,max=MAX.list)=>{if(!Array.isArray(v))refuse('TYPE',path);if(v.length>max)refuse('TOO_MANY',path);return v;};
const str=(v,path)=>{if(typeof v!=='string'||!v.length||v.length>MAX.text)refuse('TEXT_INVALID',path);return v;};
const strN=(v,path)=>v===null?null:str(v,path);
const time=(v,path)=>{if(typeof v!=='string'||!TIME.test(v)||!Number.isFinite(Date.parse(v)))refuse('TIME_INVALID',path);return v;};
const timeN=(v,path)=>v===null?null:time(v,path);
const dayN=(v,path)=>{if(v===null)return null;if(typeof v!=='string'||!DAY.test(v))refuse('DAY_INVALID',path);return v;};
const oneOf=(v,list,code,path)=>{if(!list.includes(v))refuse(code,path);return v;};
const banned=(v,path)=>{const t=String(v).replace(/\s+/g,' ');if(BANNED.some(b=>t.includes(b)))refuse('BANNED_LABEL',path);};

const FACT=['evidence_id','company_id','document_id','sha256','source_url','locator','value','published_on','published_at','period','acquired_at','unit','region','region_basis','origin','source_assertion'];
const JUDG=['judgment_id','category','topic','claim','evidence_ids','counterevidence_ids','status','reason','reviewed_by','rule_version','core','material'];
const EVENT=['event_id','kind','at','reason','document_id','sha256','evidence_ids'];
const HIST=['from_state','to_state','at','reason','rule_version','reviewer'];
const DISPLAY=['list_eligible','mark','state_reason','business','discovery_reason','selection_summary','strengths','regions','signals','types','risk_judgments','risks','unknowns'];
const RECORD=['schema_version','rule_version','company_id','company_name','identity_ref','qgv_ref','as_of','population','review_scope','state','state_reason','first_selected_at','last_reviewed_at',
 'evidence','judgments','awareness','unknowns','selection_ready','blocked_gates','unresolved_core','material_refutations','affected_judgment_ids','invalidated_evidence_ids','events','history',
 'history_ref','counterevidence_history','publication_approved','previous_record_hash','input_hash','display','record_hash'];
function fact(f,p){keys(f,FACT,p);str(f.evidence_id,p+'.evidence_id');str(f.company_id,p+'.company_id');str(f.document_id,p+'.document_id');
 if(typeof f.sha256!=='string'||!SHA.test(f.sha256))refuse('SHA_INVALID',p+'.sha256');if(typeof f.source_url!=='string'||!HTTP.test(f.source_url))refuse('URL_INVALID',p+'.source_url');
 if(!isObj(f.locator))refuse('TYPE',p+'.locator');const lk=Object.keys(f.locator);if(lk.length!==1||!['json_pointer','xml_id'].includes(lk[0])||typeof f.locator[lk[0]]!=='string')refuse('LOCATOR_INVALID',p+'.locator');
 dayN(f.published_on,p+'.published_on');timeN(f.published_at,p+'.published_at');keys(f.period,['start','end'],p+'.period');dayN(f.period.start,p+'.period.start');dayN(f.period.end,p+'.period.end');
 time(f.acquired_at,p+'.acquired_at');strN(f.unit,p+'.unit');strN(f.region,p+'.region');strN(f.region_basis,p+'.region_basis');
 if(f.origin!=='SOURCE_EXTRACT')refuse('ORIGIN_INVALID',p+'.origin');if(f.source_assertion!==true)refuse('ORIGIN_INVALID',p+'.source_assertion');}
function judgment(j,p,ev){keys(j,JUDG,p);str(j.judgment_id,p+'.judgment_id');oneOf(j.category,CATEGORIES,'CATEGORY_INVALID',p+'.category');strN(j.topic,p+'.topic');
 str(j.claim,p+'.claim');banned(j.claim,p+'.claim');
 for(const k of['evidence_ids','counterevidence_ids'])arr(j[k],p+'.'+k).forEach((x,i)=>{if(typeof x!=='string'||!ev.has(x))refuse('EVIDENCE_REF',p+'.'+k+'['+i+']');});
 oneOf(j.status,['CONFIRMED','UNCONFIRMED','REFUTED'],'STATUS_INVALID',p+'.status');str(j.reason,p+'.reason');strN(j.reviewed_by,p+'.reviewed_by');
 if(j.rule_version!==RULES)refuse('RULE_VERSION',p+'.rule_version');if(typeof j.core!=='boolean'||typeof j.material!=='boolean')refuse('TYPE',p+'.core');
 if(j.category==='TYPE'&&j.topic!==null&&!own(TYPE_TEXT,j.topic))refuse('TOPIC_INVALID',p+'.topic');}
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
function record(r,p){
 keys(r,RECORD,p);if(r.schema_version!==SCHEMA)refuse('SCHEMA_VERSION',p+'.schema_version');if(r.rule_version!==RULES)refuse('RULE_VERSION',p+'.rule_version');
 str(r.company_id,p+'.company_id');str(r.company_name,p+'.company_name');
 keys(r.identity_ref,['issuer_id','security_id','listing_id'],p+'.identity_ref');str(r.identity_ref.issuer_id,p+'.identity_ref.issuer_id');strN(r.identity_ref.security_id,p+'.identity_ref.security_id');strN(r.identity_ref.listing_id,p+'.identity_ref.listing_id');
 keys(r.qgv_ref,['company_id'],p+'.qgv_ref');str(r.qgv_ref.company_id,p+'.qgv_ref.company_id');
 time(r.as_of,p+'.as_of');str(r.population,p+'.population');str(r.review_scope,p+'.review_scope');
 oneOf(r.state,STATES,'STATE_INVALID',p+'.state');str(r.state_reason,p+'.state_reason');timeN(r.first_selected_at,p+'.first_selected_at');timeN(r.last_reviewed_at,p+'.last_reviewed_at');
 const ev=new Set();arr(r.evidence,p+'.evidence').forEach((f,i)=>{fact(f,p+'.evidence['+i+']');if(ev.has(f.evidence_id))refuse('DUPLICATE',p+'.evidence['+i+']');ev.add(f.evidence_id);});
 const J=new Map();arr(r.judgments,p+'.judgments').forEach((j,i)=>{judgment(j,p+'.judgments['+i+']',ev);if(J.has(j.judgment_id))refuse('DUPLICATE',p+'.judgments['+i+']');J.set(j.judgment_id,j);});
 keys(r.awareness,['consumer_contact','market_attention'],p+'.awareness');
 for(const k of['consumer_contact','market_attention']){const x=r.awareness[k];if(x!==null&&(typeof x!=='string'||!J.has(x)))refuse('JUDGMENT_REF',p+'.awareness.'+k);}
 arr(r.unknowns,p+'.unknowns').forEach((u,i)=>str(u,p+'.unknowns['+i+']'));
 if(typeof r.selection_ready!=='boolean')refuse('TYPE',p+'.selection_ready');
 arr(r.blocked_gates,p+'.blocked_gates').forEach((g,i)=>oneOf(g,GATES,'GATE_INVALID',p+'.blocked_gates['+i+']'));
 for(const k of['unresolved_core','material_refutations','affected_judgment_ids','invalidated_evidence_ids'])arr(r[k],p+'.'+k).forEach((x,i)=>str(x,p+'.'+k+'['+i+']'));
 arr(r.events,p+'.events').forEach((e,i)=>{const q=p+'.events['+i+']';keys(e,EVENT,q);str(e.event_id,q+'.event_id');oneOf(e.kind,EVENTS,'EVENT_INVALID',q+'.kind');time(e.at,q+'.at');str(e.reason,q+'.reason');
  str(e.document_id,q+'.document_id');if(typeof e.sha256!=='string'||!SHA.test(e.sha256))refuse('SHA_INVALID',q+'.sha256');arr(e.evidence_ids,q+'.evidence_ids').forEach((x,j)=>str(x,q+'.evidence_ids['+j+']'));});
 arr(r.history,p+'.history').forEach((h,i)=>{const q=p+'.history['+i+']';keys(h,HIST,q);oneOf(h.from_state,STATES,'STATE_INVALID',q+'.from_state');oneOf(h.to_state,STATES,'STATE_INVALID',q+'.to_state');
  time(h.at,q+'.at');str(h.reason,q+'.reason');if(h.rule_version!==RULES)refuse('RULE_VERSION',q+'.rule_version');strN(h.reviewer,q+'.reviewer');});
 str(r.history_ref,p+'.history_ref');
 arr(r.counterevidence_history,p+'.counterevidence_history').forEach((c,i)=>{const q=p+'.counterevidence_history['+i+']';keys(c,['evidence_id','first_recorded_at','disposition'],q);
  str(c.evidence_id,q+'.evidence_id');time(c.first_recorded_at,q+'.first_recorded_at');oneOf(c.disposition,['CURRENT','RETAINED_FOR_REVIEW'],'DISPOSITION_INVALID',q+'.disposition');});
 if(r.publication_approved!==false)refuse('PUBLICATION_APPROVED',p+'.publication_approved');
 strN(r.previous_record_hash,p+'.previous_record_hash');str(r.input_hash,p+'.input_hash');str(r.record_hash,p+'.record_hash');
 // the display layer: its keys, and that it agrees with the state and with the record's own judgments and facts
 const d=r.display,dp=p+'.display';keys(d,DISPLAY,dp);
 const listed=LISTED.includes(r.state);
 if(d.list_eligible!==listed||d.mark!==(listed?r.state:null))refuse('DISPLAY_STATE_MISMATCH',dp);
 if(d.state_reason!==r.state_reason)refuse('DISPLAY_STATE_MISMATCH',dp+'.state_reason');
 for(const k of DISPLAY_J)arr(d[k],dp+'.'+k).forEach((j,i)=>{const q=dp+'.'+k+'['+i+']';judgment(j,q,ev);if(!J.has(j.judgment_id)||!same(J.get(j.judgment_id),j))refuse('DISPLAY_REF',q);});
 arr(d.risks,dp+'.risks').forEach((f,i)=>{const q=dp+'.risks['+i+']';fact(f,q);if(!ev.has(f.evidence_id))refuse('DISPLAY_REF',q);});
 arr(d.unknowns,dp+'.unknowns').forEach((u,i)=>str(u,dp+'.unknowns['+i+']'));
 // states the screens rely on
 if(['SELECTED','REVIEW_REQUIRED','SUSPENDED','REMOVED'].includes(r.state)&&r.first_selected_at===null)refuse('FIRST_SELECTED_MISSING',p+'.first_selected_at');
 if(r.state==='SELECTED'&&(r.blocked_gates.length||r.unresolved_core.length||r.material_refutations.length||!r.selection_ready))refuse('GATES_OPEN',p+'.state');
 if(listed&&!d.discovery_reason.length)refuse('CORE_EVIDENCE_MISSING',dp+'.discovery_reason');
}
function freeze(o){if(o&&typeof o==='object'){Object.freeze(o);for(const v of Object.values(o))freeze(v);}return o;}
// The records of an input: one record, an array, or Codex's synthetic bundle (cases[].record; expected blocks set aside).
function recordsOf(json){
 if(isObj(json)&&own(json,'cases')){if(json.synthetic_only!==true)refuse('BUNDLE_INVALID','$.synthetic_only');return{kind:'SYNTHETIC',list:arr(json.cases,'$.cases',MAX.records).map((c,i)=>{if(!isObj(c)||!own(c,'record'))refuse('BUNDLE_INVALID','$.cases['+i+']');return c.record;}),base:'$.cases[].record'};}
 if(Array.isArray(json))return{kind:null,list:arr(json,'$',MAX.records),base:'$'};
 if(isObj(json))return{kind:null,list:[json],base:'$'};
 refuse('TYPE','$');}
function validate(json){
 try{
  const{kind,list}=recordsOf(json),seen=new Set();
  list.forEach((r,i)=>{const p='$['+i+']';record(r,p);if(seen.has(r.qgv_ref.company_id))refuse('DUPLICATE_COMPANY',p+'.qgv_ref.company_id');seen.add(r.qgv_ref.company_id);});
  // synthetic when Codex's bundle says so, or when every record carries the synthetic company id prefix it uses
  const data_kind=kind||(list.length&&list.every(r=>/^SYNTH:/.test(r.company_id))?'SYNTHETIC':'RESEARCH');
  return{ok:true,value:freeze({data_kind,records:JSON.parse(JSON.stringify(list))})};
 }catch(e){if(e instanceof Refusal)return{ok:false,code:e.code,path:e.path};return{ok:false,code:'INVALID',path:'$'};}
}

const shownJudgments=r=>DISPLAY_J.flatMap(k=>r.display[k]);
const partialOf=r=>shownJudgments(r).some(j=>j.status!=='CONFIRMED');
/* The one view the list and the mark read. get = IS2.companies.get; the join key is qgv_ref.company_id. */
function view(value,{get}={}){
 const entries=[],byId=new Map(),dropped={},hidden={};
 const bump=(o,c)=>{o[c]=own(o,c)?o[c]+1:1;};
 for(const r of value.records){
  if(!LISTED.includes(r.state)){bump(hidden,r.state);continue;}
  const row=typeof get==='function'?get(r.qgv_ref.company_id):null;
  if(!row){bump(dropped,'IDENTITY_UNRESOLVED');continue;}
  if(row.status==='WITHDRAWN'){bump(dropped,'LISTING_ENDED');continue;}
  const e=Object.freeze({record:r,company:row,status:r.state,review:r.state==='REVIEW_REQUIRED',partial:partialOf(r),synthetic:value.data_kind==='SYNTHETIC'});
  entries.push(e);byId.set(row.code,e);if(row.id!==row.code)byId.set(row.id,e);}
 return Object.freeze({entries:Object.freeze(entries),byId,dropped:Object.freeze(dropped),hidden:Object.freeze(hidden),data_kind:value.data_kind});
}
// The entry for one company row (the company page), or null: only listed states ever give a mark.
const markFor=(v,row)=>(v&&row&&(v.byId.get(row.code)||v.byId.get(row.id)))||null;

const topicsOf=(r,k)=>[...new Set(r.display[k].map(j=>j.topic).filter(t=>t!==null))];
const typeLabel=t=>own(TYPE_TEXT,t)?TYPE_TEXT[t]:t;
const topicLabel=(k,t)=>t===null?null:k==='types'?typeLabel(t):k==='signals'?(own(SIGNAL_TEXT,t)?SIGNAL_TEXT[t]:t):k==='regions'?(own(REGION_TEXT,t)?REGION_TEXT[t]:t):t;
/* Filters: f = {sector, type, strength}; '' = all. sector = the existing SIC group (sectorOf(entry) → id | null; 'NOT_AVAILABLE' =
   none); type / strength = display topics ('NONE' = the record shows none). */
function filter(entries,f={},{sectorOf=()=>null}={}){
 return entries.filter(e=>{const r=e.record,s=sectorOf(e),ty=topicsOf(r,'types'),st=topicsOf(r,'strengths');
  if(f.sector&&(f.sector==='NOT_AVAILABLE'?s!==null:s!==f.sector))return false;
  if(f.type&&(f.type==='NONE'?ty.length>0:!ty.includes(f.type)))return false;
  if(f.strength&&(f.strength==='NONE'?st.length>0:!st.includes(f.strength)))return false;
  return true;});}
// The filter choices present in the entries (only prepared data is offered): [[value, label, count]] per filter.
function facets(entries,{sectorOf=()=>null,sectorName=id=>id}={}){
 const add=(m,k,label)=>{const x=m.get(k);if(x)x[2]++;else m.set(k,[k,label,1]);};
 const sec=new Map(),typ=new Map(),str_=new Map();
 for(const e of entries){const r=e.record,s=sectorOf(e);add(sec,s===null?'NOT_AVAILABLE':s,s===null?'섹터 미확인':sectorName(s));
  const ty=topicsOf(r,'types'),st=topicsOf(r,'strengths');
  if(ty.length)for(const t of ty)add(typ,t,typeLabel(t));else add(typ,'NONE','유형 미분류');
  if(st.length)for(const t of st)add(str_,t,t);else add(str_,'NONE','강점 미정');}
 const list=m=>Object.freeze([...m.values()].map(x=>Object.freeze(x)));
 return Object.freeze({sector:list(sec),type:list(typ),strength:list(str_)});}
/* Orders only. recent: first selection time, newest first; name: the shown name ('ko'); qgv: the official rank ascending, then
   every entry without an official rank in its own group (never ranked as 0). Ties by name, then company key. */
function sort(entries,by,{qgv=()=>({rank:null,total:null}),title=e=>e.company.ticker}={}){
 const k=entries.map(e=>({e,t:String(title(e)),q:qgv(e)||{rank:null}}));
 const name=(a,b)=>a.t.localeCompare(b.t,'ko')||(a.e.company.code<b.e.company.code?-1:a.e.company.code>b.e.company.code?1:0);
 const ranked=x=>Number.isInteger(x.q.rank);
 if(by==='name')k.sort(name);
 else if(by==='qgv')k.sort((a,b)=>Number(!ranked(a))-Number(!ranked(b))||(ranked(a)&&ranked(b)?a.q.rank-b.q.rank:0)||name(a,b));
 else k.sort((a,b)=>(a.e.record.first_selected_at<b.e.record.first_selected_at?1:a.e.record.first_selected_at>b.e.record.first_selected_at?-1:0)||name(a,b));
 return Object.freeze(k.map(x=>x.e));}
const qgvGroup=q=>(q&&Number.isInteger(q.rank)?'RANKED':'NO_RANK');
// A panel section's state from its display list: NONE (nothing shown) | CONFIRMED | PARTIAL | UNCONFIRMED.
function sectionState(r){return s=>{const it=s==='risks'?r.display.risk_judgments:r.display[s];
 if(s==='risks'&&!it.length)return r.display.risks.length?'CONFIRMED':'NONE';
 return!it.length?'NONE':it.every(x=>x.status==='CONFIRMED')?'CONFIRMED':it.some(x=>x.status==='CONFIRMED')?'PARTIAL':'UNCONFIRMED';};}
const awarenessOf=(r,k)=>{const id=r.awareness[k];return id===null?null:r.judgments.find(j=>j.judgment_id===id)||null;};
const status=v=>(!v?TEXT.NONE:v.data_kind==='SYNTHETIC'?TEXT.SYNTHETIC:'연구 자료 · '+SCHEMA);
function source(){return Promise.resolve(Object.freeze({state:'NONE',code:'DISCOVERY_NOT_CONNECTED',payload:null,text:TEXT.NONE}));}
return Object.freeze({SCHEMA,RULES,STATES,LISTED,SECTIONS,SECTION_TEXT,TYPE_TEXT,SIGNAL_TEXT,REGION_TEXT,STATUS_TEXT,SORTS,BANNED,TEXT,
 validate,view,markFor,filter,facets,sort,qgvGroup,sectionState,awarenessOf,topicLabel,shownJudgments,status,source});
});
