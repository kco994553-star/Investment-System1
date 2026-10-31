/* P1 score accessor (IS2.qgv): the single QGV v2 page result every screen shares. Owner decision 2026-10-31 (DC-31, device V
   abolished): a page shows only the central V of qgv-official.json (V source OFFICIAL_CENTRAL); this device computes no V for a
   screen and keeps no V history. P1 implementation spec, Main decisions 5, 6, 13; design §1.1 (3), §2; P1_DATA_LAYER.md §10.
   - Scores are QgvScores.officialPage over the publication data.official() read and validated (web_assets/qgv-official.js,
     byte-identical): Q·G·V, totals and ranks as published, no engine call, no price. Without a usable publication every V is NA
     with OFFICIAL_NOT_PUBLISHED / OFFICIAL_INVALID / OFFICIAL_UNAVAILABLE and the Q·G totals of sec-qgv2.json stand in the QG
     reference list (price-free); a missing or late central V is never filled with a device V. A late one is shown as it is, with
     its basis day, publication time and STALE past FRESH_SESSIONS completed New York sessions (price_basis below).
     The page identities / profile / references are set here and nowhere else (app.js did it before).
   - Page and row records are a projection of that result: no price, quote, month close, EV, yield or reference range leaves this
     module, a missing value is null and always carries its reason code, rows keep QgvScores' order and rank fields (sorting and
     filters: small ports in screen-qgv-live.js, P2-2a; radar: P2-2c). model() is the price-free projection of the N10 / N15 / N20
     candidates (QgvScores.officialModel) on the official result.
   - preview() recomputes the user's weights from the published factor scores (QgvScores.compute({publication, weights})): never
     primary, never an official rank; weight stages are NA (WEIGHT_STAGES_NOT_REBUILT).
   - The TARGET v1 builder keeps its V source until the 11/16 PR: forEngines (engines.js only) is the hidden device result
     (QgvScores.pageResult on the score view: RAM prices of a click only), labelled engine_v_source DEVICE_TEMPORARY. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else{const I=root.IS2=root.IS2||{};I.qgv=api.create({win:root,data:I.data,prices:I.prices,action:I.action});}})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
// Byte-identical to QgvOfficial.V_SOURCES and TargetV1Builder.V_SOURCES until the 11/16 PR (parity test). DEVICE_TEMPORARY labels
// only the hidden TARGET engine result (engine_v_source), never a page or a row. Screens show source_label only.
const V_SOURCES=Object.freeze({
 DEVICE_TEMPORARY:Object.freeze({id:'DEVICE_TEMPORARY',ko:'임시 V',note:'기기 시세로 계산 · 중앙 V 미게시'}),
 OFFICIAL_CENTRAL:Object.freeze({id:'OFFICIAL_CENTRAL',ko:'공식 V',note:'중앙 게시 · IEX 마지막 체결가 기준(공식 종가 아님)'})});
// What a rank is called: the published official rank, a personal preview recomputed from the published scores, and the hidden
// TARGET engine result (never shown as a page rank).
const RANK_LABELS=Object.freeze({
 OFFICIAL_CENTRAL:Object.freeze({ko:'공식 순위 · 중앙 게시 V',en:'Official ranking · central V'}),
 PERSONAL_PREVIEW:Object.freeze({ko:'내 설정 순위 · 공식 V로 다시 계산 · 공식 순위 아님',en:'My-setting rank · recomputed from the official V · not the official ranking'}),
 DEVICE_TEMPORARY:Object.freeze({ko:'임시 V 기준 순위 · 공식 순위 아님',en:'Ranked on the temporary V · not the official ranking'})});
// The strict qgv-official/1 reader (DC-02, DC-31): web_assets/qgv-official.js (window.QgvOfficial, loader.js LOAD_ORDER).
const OFFICIAL_READER='QgvOfficial';
const vSource=()=>'OFFICIAL_CENTRAL';
const QGV2='sec-qgv2.json',CATALOG='actual-catalog.json';
// Without these the score would change silently (PlaybookEngine: cyclical V basis; SecQgv2: light sec-qgv2 path): READER_MISSING.
const READERS=Object.freeze(['QgvScores','QgvV2','Qgv2Inputs','SecQgv2','ScoringDefault','PlaybookEngine','PlaybookConfigDefaults','DeviceWatchlist','TargetV1Builder',OFFICIAL_READER]);
// Without a price layer (a node test that passes none): the hidden TARGET engine result gets no device price either.
const NO_UNIVERSE=Object.freeze({prices:()=>null,priceBasis:()=>null,readStatus:()=>null});
const NO_STORE=Object.freeze({status:()=>null,coverage:()=>null,subscribe:()=>()=>{},monthEndCloses:()=>Promise.resolve({}),dailyCloses:()=>Promise.resolve({}),runnerHistories:()=>Promise.resolve(null)});
// Codes the old reason table (QgvScores.REASON, which words the central V codes) does not word: P1 states, rank reasons and the
// publication attempt states of qgv-official-status.json.
const TEXT=Object.freeze({
 READER_MISSING:['계산 모듈이 없어 계산하지 않았습니다','Not calculated: a calculation module is missing'],
 SCORE_PATH_NO_NETWORK:['점수 계산은 네트워크를 쓰지 않습니다','The score path makes no network request'],
 SEC_QGV2_NOT_PUBLISHED:['점수 입력 파일이 아직 게시되지 않았습니다','The score input file is not published yet'],
 SEC_QGV2_NOT_AVAILABLE:['점수 입력 파일을 읽지 못했습니다','The score input file could not be read'],
 SEC_QGV2_SCHEMA_NEWER:['자료 형식이 새 버전입니다. 페이지를 새로 여세요','Newer data format. Reopen the page'],
 SEC_QGV2_INVALID:['점수 입력 파일 내용 검증 실패','The score input file did not validate'],
 SEC_QGV2_UNAVAILABLE:['점수 입력 파일 읽기 실패','The score input file could not be read'],
 DATA_FORMAT_NEWER:['자료 형식이 새 버전입니다. 페이지를 새로 여세요','Newer data format. Reopen the page'],
 V2_SCORES_NOT_AVAILABLE:['종합 점수를 계산할 수 있는 기업이 없습니다','No company has a total score'],
 V2_CALCULATION_FAILED:['점수 계산 실패','Score calculation failed'],
 V2_INPUTS_NOT_AVAILABLE:['점수 입력이 없습니다','No score input'],
 AXIS_WEIGHT_INSUFFICIENT:['산출된 축 비중이 50% 미만이라 계산하지 않았습니다','Below 50% of the weight, so not calculated'],
 AXIS_NOT_PUBLISHED:['게시된 축 점수가 없습니다','No published axis score'],
 QG_REFERENCE:['V가 없어 공식 순위 대신 QG 참고 목록에 있습니다','No V: in the Q·G reference list, not the official ranking'],
 OUTSIDE_UNIVERSE:['Universe 밖 TARGET이라 공식 순위 대상이 아닙니다','TARGET outside the Universe: not in the official ranking'],
 REFERENCE_ONLY:['참고 순위 행이라 공식 순위가 없습니다','Reference row: no official rank'],
 NOT_RANKED:['순위 없음','Not ranked'],
 WEIGHTS_INVALID:['개인 가중치가 올바르지 않습니다','Invalid personal weights'],
 DEVICE_STORE_NOT_OPENED:['이 기기 저장소가 아직 없습니다','No device store yet'],
 CATALOG_NOT_AVAILABLE:['기업 목록 파일을 읽지 못해 TARGET 행이 없습니다','The company catalog could not be read: no TARGET rows'],
 NO_OFFICIAL_YET:['중앙 V 게시본이 아직 없습니다','No central V publication yet'],
 SUPPLY_FAILED:['마지막 게시 시도 실패: IEX 가격 공급이 95% 기준에 못 미쳤습니다 · 이전 게시본 유지','Last attempt failed: IEX price supply below 95% · previous publication kept'],
 VERIFY_FAILED:['마지막 게시 시도 실패: 게시 전 검증 실패 · 이전 게시본 유지','Last attempt failed: verification before publishing · previous publication kept'],
 NOT_RUN:['마지막 게시 시도: 실행되지 않음','Last publication attempt: not run'],
 OFFICIAL_STATUS_INVALID:['게시 상태 파일 검증 실패','The publication status file did not validate'],
 ISSUER_RANKED_ONCE:['같은 발행사(CIK)는 공식 순위 한 자리 · 대표 코드에 순위','One official place per issuer (CIK) · ranked on its representative code'],
 WEIGHT_STAGES_NOT_REBUILT:['가중치 단계 NA: 공식 V 미리보기에서는 단계 표를 다시 만들지 않습니다','Weight stages NA: not rebuilt for the official-V preview'],
 OFFICIAL_INPUTS_DIFFER:['점수 파일이 게시본의 입력과 달라 게시본 값만 표시 · 후보 선정 안 함','The score file is not the publication\'s input: publication values only · no candidate selection'],
 JUDGEMENT_NOT_RECORDED:['기록 안 됨','Not recorded'],
 NOTHING_TO_RECORD:['기록할 발생 신호 없음','No occurrence to record'],
 // P2-2a (Main 2026-10-25): the price buttons' codes (prices.readUniverse / prepare / login, PriceStore) and the M3 rank reasons
 // (PrivateSubsetView.rankFor / rankIndex), worded once here so a screen never prints a code. The sheet they name is the user's
 // price sheet; the Universe504 list itself is a public file (DC-22, owner 2026-10-27), so the words say 가격 시트.
 UNIVERSE_SOURCE_NOT_SET:['가격 시트 없음 · Universe 목록은 공개 파일','No price sheet · the Universe list is a public file'],
 UNIVERSE_SOURCE_INVALID:['가격 시트 주소 형식이 올바르지 않습니다','The price sheet address is not valid'],
 AUTH_REQUIRED:['로그인 필요','Sign-in required'],
 CANCELED:['취소됨','Canceled'],
 PREPARE_TIMEOUT:['로그인 준비 시간 초과','Sign-in preparation timed out'],
 SOURCE_TOO_LARGE:['시트가 너무 커서 읽지 않았습니다','The sheet is too large to read'],
 UNIVERSE_READ_FAILED:['가격 시트 읽기 실패','Price sheet read failed'],
 SHEET_NOT_CONNECTED:['가격 시트가 연결되지 않았습니다','No price sheet is connected'],
 PRICE_TABS_OFF:['가격 탭 사용이 꺼져 있습니다','Price tabs are off on this device'],
 UNIVERSE_NOT_READ:['가격 시트 읽기 전','Price sheet not read yet'],
 NOT_IN_UNIVERSE:['이 기기 가격 시트에 없음','Not in this device\'s price sheet read'],
 NO_VERIFIED_ROWS:['확인된 시총 순위 행 없음','No verified market-cap rank rows'],
 // Period returns (prices.periodReturns, P2-2a): RAM only, after the price-tab click. RETURN_* are their own codes because
 // QgvScores.REASON.HISTORY_TOO_SHORT already names a V history rule. PRICE_BASIS_CONTINUITY_UNCONFIRMED is the TA-G1 code.
 PRICE_TABS_NOT_LOADED:['가격 불러오기 전','Prices not loaded yet'],
 RETURN_SESSIONS_NOT_AVAILABLE:['기간 이력 없음: S&P 500 세션 없음','No period history: no S&P 500 sessions'],
 RETURN_HISTORY_TOO_SHORT:['기간 이력 없음','No period history'],
 RETURN_BASE_CLOSE_MISSING:['기준일 종가 없음','Base close missing'],
 RETURN_LAST_CLOSE_MISSING:['마지막 세션 종가 없음','Last session close missing'],
 PERIOD_PENDING:['기간 정의 결정 대기 (IA-12)','Period definition pending (IA-12)'],
 PRICE_BASIS_CONTINUITY_UNCONFIRMED:['분할 등 가격 연속성 미확인','Price continuity (splits) unconfirmed']});
const object=v=>v!==null&&typeof v==='object'&&!Array.isArray(v),finite=v=>typeof v==='number'&&Number.isFinite(v),num=v=>finite(v)?v:null,str=v=>typeof v==='string'?v:null;
function deepFreeze(v){if(v&&typeof v==='object'&&!Object.isFrozen(v)){Object.freeze(v);for(const x of Object.values(v))deepFreeze(x);}return v;}
function create({win,data,prices,action}){
 if(!data||typeof data.ready!=='function'||!action||typeof action.view!=='function')throw Error('LAYER_MISSING');
 const P=prices&&!prices.NOT_READY?prices:null,universeView=()=>P&&P.universeView?P.universeView:NO_UNIVERSE,storeFacade=()=>P&&P.storeFacade?P.storeFacade:NO_STORE;
 // The score view: never a request (public files are read by data.js before), never a new IndexedDB (readOnly), no storage write.
 async function noNetwork(){throw Error('SCORE_PATH_NO_NETWORK');}
 const scoreView=action.view(Object.defineProperties({fetch:noNetwork},{PrivateSubsetView:{enumerable:true,get:universeView},PriceStore:{enumerable:true,get:storeFacade}}),{readOnlyStores:true});
 let profile=Object.freeze({preset:null,gate:null}),epoch=0,ids=[],idsKey=null,fin=null,wired=false;
 const held=new WeakMap(),known=new WeakSet(),byResult=new WeakMap(),scoped=new WeakMap(),subs=new Set();
 const emit=why=>{for(const fn of[...subs]){try{fn(why);}catch(_){}}};
 // app.js dartReferenceRows: the DART issuer scored as a reference row only (never a US Universe point).
 function references(){try{const inputs=data.get(QGV2),universe=inputs&&inputs.records,DD=win.DartDisclosures;if(!fin||!universe||!DD)return{};const row=DD.qgv2Reference(fin,universe);return row?{hanmi:row}:{};}catch(_){return{};}}
 function wire(){if(wired)return;wired=true;const QS=win.QgvScores;QS.setPageProfile(()=>profile);QS.setPageReferences(references);
  try{win.document.addEventListener('device-actual-changed',()=>{epoch++;emit('DEVICE');});}catch(_){}
  data.subscribe(()=>emit('DATA'));if(P&&typeof P.subscribe==='function')P.subscribe(()=>emit('PRICES'));}
 function check(){if(READERS.some(n=>!win[n]))throw Error('READER_MISSING');}
 const stop=signal=>{if(signal&&signal.aborted)throw Error('ABORTED');};
 // A page without a result: neither a usable publication nor a usable sec-qgv2.json.
 function emptyPage(state,reason,pub,off){const pg=deepFreeze({v_source:V_SOURCES.OFFICIAL_CENTRAL,engine_v_source:V_SOURCES.DEVICE_TEMPORARY,rank_label:RANK_LABELS.OFFICIAL_CENTRAL.ko,state,reason,as_of:null,calc_version:null,type_scope:null,profile_id:null,preset:null,gate:null,
  generation:pub?pub.generation:0,basis_id:null,price_basis:centralBasis(off,null),identities:null,coverage:null,rows:[]});known.add(pg);return pg;}
 function absent(){const s=data.state(QGV2);
  if(s.state==='FAILED'&&s.why==='SCHEMA_NEWER')return['DATA_FORMAT_NEWER','SEC_QGV2_SCHEMA_NEWER'];
  if(s.state==='FAILED')return['READ_FAILED',s.why==='INVALID'?'SEC_QGV2_INVALID':'SEC_QGV2_UNAVAILABLE'];
  return['NO_DATA',s.state==='NOT_PUBLISHED'?'SEC_QGV2_NOT_PUBLISHED':'SEC_QGV2_NOT_AVAILABLE'];}
 function identitiesOf(catalog){try{return catalog?win.DeviceWatchlist.identities(catalog).map(c=>({company_id:c.company_id,ticker:c.ticker})):[];}catch(_){return[];}}
 /* The central V basis of a page (no price): kind CENTRAL_IEX, the publication's price basis day, generation and verification times,
    publication_id and calc_version; sessions = completed New York sessions after the basis day (QgvOfficial.sessionsAfter, counted
    up to FRESH_SESSIONS + 1), stale = more than FRESH_SESSIONS (null: not countable); calc_differs = the loaded sec-qgv2.json
    declares another calc_version (null: unknown); inputs_match = the loaded sec-qgv2.json is the publication's input; attempt =
    the last publication attempt of qgv-official-status.json (null when that file is unread); reason = why there is no official V;
    attribution = the IEX text and terms link the publication carries (IEX HIST terms clause 01, DC-29). */
 function centralBasis(off,inputs,match=null){const QO=win.QgvOfficial,pub=off&&off.state==='OFFICIAL'?off.payload:null,st=off&&off.status&&off.status.value?off.status.value:null;
  const attempt=st?{state:st.attempt_state,at:st.last_attempt_at,reason:st.reason_code,publication_id:st.official_publication_id}:off&&off.status&&off.status.reason?{state:'UNKNOWN',at:null,reason:off.status.reason,publication_id:null}:null;
  const reason=pub?null:off&&off.reason?off.reason:'OFFICIAL_NOT_PUBLISHED';
  if(!pub||!QO)return{kind:'CENTRAL_IEX',label:'공식 V · IEX 마지막 체결가 기준(공식 종가 아님)',reason,price_basis_date:null,generated_at:null,verified_at:null,publication_id:null,calc_version:null,sessions:null,stale:null,calc_differs:null,inputs_match:null,attempt,attribution:null};
  let sessions=null;try{const ny=QO.nyNow();sessions=ny?QO.sessionsAfter(pub.times.price_basis_date,ny.date,!(ny.minutes<QO.CLOSE_MINUTES)):null;}catch(_){sessions=null;}
  const own=inputs&&typeof inputs.calc_version==='string'?inputs.calc_version:null;
  return{kind:'CENTRAL_IEX',label:'공식 V · '+pub.attribution.label_ko,reason,price_basis_date:pub.times.price_basis_date,generated_at:pub.times.generated_at,verified_at:pub.times.verified_at,publication_id:pub.publication_id,
   calc_version:pub.calc_version,sessions,stale:sessions===null?null:sessions>QO.FRESH_SESSIONS,calc_differs:own===null?null:own!==pub.calc_version,inputs_match:match,attempt,attribution:{text:pub.attribution.text,terms_url:pub.attribution.terms_url}};}
 function axisOf(x){if(!object(x))return null;return{status:x.status,score:num(x.score),weight_available:num(x.weight_available),factors_available:x.factors_available,factors_total:x.factors_total,reason:str(x.reason),use:str(x.use),
  factors:(Array.isArray(x.factors)?x.factors:[]).map(f=>({id:f.id,weight:f.weight,score:num(f.score),reason:str(f.reason),category:f.category,basis:str(f.basis)})),
  published:object(x.published)?{...x.published,reason_codes:Array.isArray(x.published.reason_codes)?[...x.published.reason_codes]:[]}:null};}
 /* One row of the computed result (primary, or personal for a preview). A null score always has its reason: V = the coverage V
    reason (the same rule QgvScores.vCoverage counts with), Q/G = the axis reason, total = DATA_FORMAT_NEWER / CALC_VERSION_MISMATCH /
    total_reason, rank = why there is no official rank. */
 function rowRecord(r,{vs,weights,of,targets,personal=false,pub=null}){
  const QS=win.QgvScores,TB=win.TargetV1Builder,p=personal?r.personal:r.primary,cov=object(p.coverage)?p.coverage:null,axes=cov&&object(cov.axes)?cov.axes:null,flags=Array.isArray(p.flags)?p.flags:[];
  const score={total:num(p.total),q:num(p.q),g:num(p.g),v:num(p.v)},fallback=p.total_reason?p.total_reason:'V2_INPUTS_NOT_AVAILABLE';
  const axisReason=a=>{const x=axes&&axes[a];if(x&&x.reason)return x.reason;const f=x&&Array.isArray(x.factors)?x.factors.find(y=>y.score===null&&y.reason):null;return f?f.reason:fallback;};
  const totalReason=p.total_reason==='DATA_FORMAT_NEWER'?'DATA_FORMAT_NEWER':flags.includes('CALC_VERSION_MISMATCH')?'CALC_VERSION_MISMATCH':fallback;
  const rank=personal?r.personal_rank:r.rank,qgr=personal?r.personal_qg_reference:r.qg_reference,placed=Number.isInteger(rank)?rank:null,qgOrder=object(qgr)&&Number.isInteger(qgr.order)?qgr.order:null;
  const rankReason=placed!==null?null:p.reference_only===true?'REFERENCE_ONLY':r.outside_universe===true?'OUTSIDE_UNIVERSE':qgOrder!==null?'QG_REFERENCE':score.total===null?totalReason:(personal?r.personal_rank_row:r.rank_row)?'ISSUER_RANKED_ONCE':'NOT_RANKED';
  const vf=TB.vFactors(p),src=cov&&object(cov.source)?cov.source:null;
  return{id:r.company_id,ticker:r.ticker,code:str(r.universe_code),record:str(r.code),scope:r.outside_universe===true?'OUTSIDE_UNIVERSE':'UNIVERSE',target:targets.has(r.company_id),reference_only:p.reference_only===true,
   source:vs.id,source_label:vs.ko,score,
   na_reason:{total:score.total===null?totalReason:null,q:score.q===null?axisReason('Q'):null,g:score.g===null?axisReason('G'):null,v:score.v===null?axisReason('V'):null,rank:rankReason},
   rank:{official:personal?null:placed,personal:personal?placed:null,qg_reference_order:qgOrder,group:personal?null:QS.exploreGroup(r),of,weights},
   coverage:{v_factors:{n:vf.n,total:vf.total,missing:[...vf.missing],required_ok:vf.required_ok},axes:{Q:axisOf(axes&&axes.Q),G:axisOf(axes&&axes.G),V:axisOf(axes&&axes.V)},
    factors:{available:num(p.factors_available),total:num(p.factors_total)},states:cov&&Array.isArray(cov.states)?[...cov.states]:[],v_inputs_missing:cov&&Array.isArray(cov.v_inputs_missing)?[...cov.v_inputs_missing]:[]},
   flags:[...flags],value_trap_gate:p.value_trap_gate===true,v_excluded:str(p.v_excluded),types:{selected:Array.isArray(p.selected_types)?[...p.selected_types]:[],reason:str(p.type_reason)},
   price_status:pub&&r.code&&Object.hasOwn(pub.rows,r.code)?pub.rows[r.code].price_status:null,rank_row:str(personal?r.personal_rank_row:r.rank_row),
   row_state:src?str(src.state):null,acquired_at:src?str(src.acquired_at):null,fiscal_year_end:src?str(src.fiscal_year_end):null,profile:src?str(src.profile):null,
   source_reason_codes:src&&Array.isArray(src.reason_codes)?[...src.reason_codes]:[]};}
 // The central result as a page: V source OFFICIAL_CENTRAL whether or not a publication was read (without one every V is NA).
 function project(result,inputs,pub,off,held_){
  const QS=win.QgvScores,c=result.computed,vs=V_SOURCES.OFFICIAL_CENTRAL,weights=QS.provenance({kind:'QGV',profile:c.profile}).weights,targets=new Set(ids.map(x=>x.company_id)),P=held_.pub;
  const of=object(c.official)&&Number.isInteger(c.official.ranked)?c.official.ranked:Object.values(c.rows).filter(r=>Number.isInteger(r.rank)).length;
  const calc=P?P.calc_version:inputs?str(inputs.calc_version):null,basis=centralBasis(off,inputs,result.inputs_match);
  return deepFreeze({v_source:vs,engine_v_source:V_SOURCES.DEVICE_TEMPORARY,rank_label:RANK_LABELS[vs.id].ko,state:'READY',
   reason:!P?result.v_reason:c.v2_state==='READY'?(result.inputs_match===false?'OFFICIAL_INPUTS_DIFFER':null):c.v2_reason?c.v2_reason:'V2_SCORES_NOT_AVAILABLE',
   as_of:str(c.v2_as_of),calc_version:calc,type_scope:str(c.profile.type_scope),profile_id:c.profile.id,preset:c.profile.preset,gate:c.profile.gate,generation:pub.generation,
   basis_id:JSON.stringify([str(c.v2_as_of),calc,basis.publication_id,basis.stale,basis.attempt&&basis.attempt.at,c.profile.id,pub.generation,epoch]),
   price_basis:basis,identities:ids.length?{state:'OK',reason:null,count:ids.length}:{state:'NOT_AVAILABLE',reason:'CATALOG_NOT_AVAILABLE',count:0},
   coverage:P?{...JSON.parse(JSON.stringify(P.coverage)),source:'PUBLICATION'}:null,rows:Object.values(c.rows).map(r=>rowRecord(r,{vs,weights,of,targets,pub:P}))});}
 async function centralPage(pub,{signal}){
  const QS=win.QgvScores,inputs=data.get(QGV2),off=await data.official();stop(signal);
  const catalog=await data.static(CATALOG),list=identitiesOf(catalog),key=JSON.stringify(list);stop(signal);
  if(key!==idsKey){idsKey=key;ids=list;QS.setPageIdentities(list);}
  fin=await data.financials().catch(()=>null);stop(signal);
  const P=off.state==='OFFICIAL'?off.payload:null,result=QS.officialPage(win,{publication:P,v2Inputs:inputs,identities:ids,reason:off.reason});
  if(!result){const[state,reason]=absent();return emptyPage(state,reason,pub,off);}
  const h={result,inputs,base:P&&result.inputs_match===false?null:inputs,pub:P,catalog};
  let pg=project(result,inputs,pub,off,h);const prev=byResult.get(result);if(prev&&prev.basis_id===pg.basis_id)return prev;
  byResult.set(result,pg);held.set(pg,h);known.add(pg);return pg;}
 // Every page is the central one (official profile); preset / gate are not page arguments any more (a personal setting is preview()).
 async function page({signal}={}){check();wire();await data.ready();stop(signal);return centralPage(data.publication(),{signal});}
 function of_(pg){if(!known.has(pg))throw Error('PAGE_UNKNOWN');return pg;}
 // A page this accessor made (engines refuse anything else with PAGE_UNKNOWN before reading its fields).
 const isPage=pg=>known.has(pg);
 // A page without a result (NO_DATA, READ_FAILED, DATA_FORMAT_NEWER) has rows [] and nothing to preview or hand to engines.
 function result_(pg){of_(pg);const h=held.get(pg);if(!h)throw Error('PAGE_NOT_READY');return h;}
 function rows(pg,{scope='ALL'}={}){of_(pg);if(scope==='ALL')return pg.rows;if(scope!=='UNIVERSE'&&scope!=='TARGET')throw Error('SCOPE_UNKNOWN');
  let m=scoped.get(pg);if(!m){m={};scoped.set(pg,m);}if(!m[scope])m[scope]=Object.freeze(pg.rows.filter(r=>scope==='UNIVERSE'?r.scope==='UNIVERSE':r.target));return m[scope];}
 // By id, else the row standing for that Universe code (QgvScores.rowOf / codeRow: a TARGET in the Universe is that code's row).
 function row(pg,id){of_(pg);return pg.rows.find(r=>r.id===id)||pg.rows.find(r=>r.code===id)||null;}
 const coverage=pg=>{of_(pg);return pg.coverage;};
 /* Personal preview of the user's own weights over the same publication and population: never primary, never an official rank.
    QgvScores.compute({publication, weights, typeWeights, gate}) recomputes from the published factor scores (no price); without a
    publication the price-free Q·G compute (every V NA with the page's reason). gate null = QgvV2.GATE_DEFAULT (on). */
 function preview(pg,weights,{typeWeights=true,gate=null}={}){const h=result_(pg),QS=win.QgvScores;if(gate!==null&&typeof gate!=='boolean')throw Error('GATE_INVALID');
  let refs={};try{refs=JSON.parse(h.result.reference_key);}catch(_){refs={};}const r=h.result;
  const out=QS.compute({identities:r.identities,v2Inputs:h.pub?h.base||undefined:h.inputs,quotes:{},referenceRows:refs,official:r.official,gate,weights,typeWeights,...(h.pub?{publication:h.pub}:{vMissing:r.v_reason})}),vs=V_SOURCES.OFFICIAL_CENTRAL;
  const x=out.personal,rs=Object.values(out.rows),of=rs.filter(y=>Number.isInteger(y.personal_rank)).length,targets=new Set(ids.map(i=>i.company_id));
  return deepFreeze({weights:'PERSONAL',v_source:vs,rank_label:RANK_LABELS.PERSONAL_PREVIEW.ko,state:x.state,reason:str(x.reason),label:[...x.label],profile_id:x.profile?x.profile.id:null,v_weight_zero:x.v_weight_zero===true,
   weight_stages:{state:'NOT_AVAILABLE',reason:'WEIGHT_STAGES_NOT_REBUILT'},rows:x.state==='INVALID'?[]:rs.map(y=>rowRecord(y,{vs,weights:'PERSONAL',of,targets,personal:true,pub:h.pub}))});}
 /* The model candidates N10 / N15 / N20 (feature 2.1.7, P2-2a, Main 2026-10-25): QgvScores.officialModel over the page's held
    result (official default profile, gate on, whatever profile the page shows; D12), projected to what is price-free: ranks,
    group ids, tickers, totals, counts and percentages of an equal-weight set. No metric value, quote or price. null when there is
    no official ranking (no publication) or the loaded sec-qgv2.json is not the publication's input (the safety metrics would be
    another file's). PAGE_NOT_READY for a page without a result. */
 const models=new WeakMap();
 function model(pg){const h=result_(pg);if(models.has(pg))return models.get(pg);const QS=win.QgvScores;
  const M=h.pub&&h.base?QS.officialModel({identities:h.result.identities,v2Inputs:h.base,quotes:h.result.quotes,official:h.result.official,computed:h.result.computed}):null;
  let out=null;
  if(M&&Number.isInteger(M.ranked)&&M.ranked>0){
   const int=v=>Number.isInteger(v)?v:null,group=v=>typeof v==='string'?v:null,sets={};
   for(const[k,x]of Object.entries(M.sets))sets[k]={n:x.n,complete:x.complete===true,status:str(x.status),weight_pct:num(x.weight_pct),shortfall_pct:num(x.shortfall_pct),
    causes:(Array.isArray(x.causes)?x.causes:[]).map(c=>JSON.parse(JSON.stringify(c))),skipped:{SUBGROUP_MAX_4:int(x.skipped.SUBGROUP_MAX_4),SECTOR_GROUP_MAX_40:int(x.skipped.SECTOR_GROUP_MAX_40)},
    group_capped:x.group_capped.map(c=>({id:c.company_id,ticker:c.ticker,rank:int(c.rank),group:group(c.group)})),
    selected:x.selected.map(e=>({id:e.company_id,ticker:e.ticker,rank:int(e.rank),total:num(e.total),group:group(e.group)})),
    issuer_check:{status:str(x.issuer_check.status),applied:x.issuer_check.applied===true,issuers_n:Array.isArray(x.issuer_check.issuers)?x.issuer_check.issuers.length:0}};
   out=deepFreeze({v_source:pg.v_source,official_profile:{...M.official_profile},primary:str(M.primary),ns:[...M.ns],as_of:str(M.as_of),checked:int(M.checked),ranked:int(M.ranked),
    provisional:[...M.provisional],excluded:{...M.excluded},unknown:{subgroup:int(M.unknown.subgroup)},sets});}
  models.set(pg,out);return out;}
 function setProfile({preset=null,gate=null}={}){const V2=win.QgvV2;if(preset!==null&&!(V2&&Object.hasOwn(V2.PRESETS,preset)))throw Error('PRESET_UNKNOWN');if(gate!==null&&typeof gate!=='boolean')throw Error('GATE_INVALID');
  profile=Object.freeze({preset,gate});emit('PROFILE');return profile;}
 // The rank wording of a V source id, a Page / preview, or a row (its source): screens show this next to any rank.
 const UNKNOWN_RANK=Object.freeze({ko:'순위 출처 미확인 · 공식 순위 아님',en:'Rank source unknown · not the official ranking'});
 function rankLabel(x,en=false){const personal=x&&typeof x==='object'&&(x.weights==='PERSONAL'||object(x.rank)&&x.rank.weights==='PERSONAL');
  const id=typeof x==='string'?x:personal?'PERSONAL_PREVIEW':x&&typeof x==='object'?(x.v_source&&x.v_source.id)||x.source:null;const l=Object.hasOwn(RANK_LABELS,id)?RANK_LABELS[id]:UNKNOWN_RANK;return en?l.en:l.ko;}
 function reasonText(code,en=false){const QS=win.QgvScores;if(typeof code==='string'&&QS&&Object.hasOwn(QS.REASON,code))return QS.reasonText(code,en);if(typeof code==='string'&&Object.hasOwn(TEXT,code))return TEXT[code][en?1:0];return QS?QS.reasonText(code,en):String(code);}
 let consts=null;
 // Read-only copies for the 2.5 factor tree and weight screens.
 function constants(){check();if(!consts){const V2=win.QgvV2,TB=win.TargetV1Builder;consts=deepFreeze(JSON.parse(JSON.stringify({WEIGHTS:V2.WEIGHTS,PRESETS:V2.PRESETS,DEFAULT_PRESET:V2.DEFAULT_PRESET,GATE_DEFAULT:V2.GATE_DEFAULT,
  FACTORS:V2.FACTORS,MIN_AXIS_WEIGHT:V2.MIN_AXIS_WEIGHT,SUBMETRICS:win.SecQgv2.SUBMETRICS,V_FACTORS:TB.V_FACTORS,V_REQUIRED:TB.V_REQUIRED})));}return consts;}
 function subscribe(fn,{signal}={}){if(typeof fn!=='function')throw Error('SUBSCRIBER_INVALID');if(signal&&signal.aborted)return()=>{};subs.add(fn);const off=()=>{subs.delete(fn);};if(signal)signal.addEventListener('abort',off,{once:true});return off;}
 /* engines.js only (source rule). forEngines: the TARGET v1 builder's hidden device result until the 11/16 PR (DC-31: the builder
    keeps its V source), computed when engines ask (never for a screen): QgvScores.pageResult on the score view, RAM prices of a
    click only, the current profile; engines record page.engine_v_source for it. Asked again on every call: pageResult memoizes by
    the Universe read, the device inputs and preset / gate, so a later read or setProfile reaches the builder although the central
    page (keyed by the publication) stays the same object. Resolves the computed result; PAGE_NOT_READY without one. */
 function forEngines(pg){const h=result_(pg);if(!h.inputs)return Promise.reject(Error('PAGE_NOT_READY'));
  return(async()=>{await action.stores();const r=await win.QgvScores.pageResult(scoreView,{v2Inputs:h.inputs,catalog:h.catalog,identities:ids,preset:profile.preset,gate:profile.gate});if(!r)throw Error('PAGE_NOT_READY');return r.computed;})();}
 // The central result exactly as QgvScores made it (playbook facts, the rehearsal's Q·G rows: price-free).
 const centralComputed=pg=>result_(pg).result.computed;
 // The sec-qgv2.json value (Qgv2Inputs output) the page read (a re-judgement can replace data.get's value later; null without one).
 const engineInputs=pg=>result_(pg).inputs;
 return Object.freeze({V_SOURCES,RANK_LABELS,READERS,vSource,page,isPage,row,rows,coverage,preview,model,setProfile,profile:()=>profile,reasonText,rankLabel,constants,subscribe,forEngines,centralComputed,engineInputs,scoreView});
}
return Object.freeze({create,V_SOURCES,RANK_LABELS,READERS});
});
