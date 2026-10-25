/* P1 score accessor (IS2.qgv): the single QGV v2 page result every screen shares, with its V source (device V is labelled
   as the temporary V until a central V is published). P1 implementation spec, Main decisions 5, 6, 13; design §1.1 (3), §2.
   - Scores are QgvScores.pageResult (the old shared result: one collectQuotes and one compute over the whole sec-qgv2.json),
     computed with the score view: fetch always fails (SCORE_PATH_NO_NETWORK); RAM prices only, from the click-only price layer
     (the Universe tab read on a click, the price tabs, RAM Worker closes: prices.universeView / storeFacade); stored device
     quotes are not read (DC-18: the gate answers them as absent).
     The page identities / profile / references are set here and nowhere else (app.js did it before).
   - Page and row records are a projection of that result: no price, quote, month close, EV, yield or reference range (engine
     `detail` / `reference_range`, collectQuotes quotes and meta) leaves this module, a missing value is null and always carries
     its reason code, rows keep QgvScores' order and rank fields (sorting / filters / radar are P2-2, reusing the old functions).
   - One V source switch for the whole page (V percentiles depend on which rows are priced): OFFICIAL_READER below routes page()
     to the central or the device page. A device page (and a preview) is computed from device quotes, so it is always labelled
     DEVICE_TEMPORARY, whatever the switch says by the time it is built. Engines always compute with the device result
     (forEngines), so a page also says engine_v_source. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else{const I=root.IS2=root.IS2||{};I.qgv=api.create({win:root,data:I.data,prices:I.prices,action:I.action});}})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
// DEVICE_TEMPORARY is byte-identical to #391 TargetV1Builder.V_SOURCE. OFFICIAL_CENTRAL is draft wording (owner sign-off when the
// central V lands). Screens show source_label only; this is the only file with these words.
const V_SOURCES=Object.freeze({
 DEVICE_TEMPORARY:Object.freeze({id:'DEVICE_TEMPORARY',ko:'임시 V',note:'기기 시세로 계산 · 중앙 V 미게시'}),
 OFFICIAL_CENTRAL:Object.freeze({id:'OFFICIAL_CENTRAL',ko:'공식 V',note:'중앙 게시 · IEX 마지막 체결가 기준(공식 종가 아님)'})});
// What a rank computed with each V source is called (owner 2026-10-24, Main pick: the old screens already say "공식 순위 아님").
// A device page and a personal preview rank on the temporary V: never the official ranking. OFFICIAL_CENTRAL is draft wording.
const RANK_LABELS=Object.freeze({
 DEVICE_TEMPORARY:Object.freeze({ko:'임시 V 기준 순위 · 공식 순위 아님',en:'Ranked on the temporary V · not the official ranking'}),
 OFFICIAL_CENTRAL:Object.freeze({ko:'공식 순위(초안 문구)',en:'Official ranking (draft wording)'})});
// The strict qgv-official/1 reader (DC-02). Not built yet: set it here, and only here, when the central V is published.
const OFFICIAL_READER=null;
function vSource(pub){return OFFICIAL_READER&&OFFICIAL_READER.state(pub)==='OFFICIAL'?'OFFICIAL_CENTRAL':'DEVICE_TEMPORARY';}
const QGV2='sec-qgv2.json',CATALOG='actual-catalog.json';
// Without these the score would change silently (PlaybookEngine: cyclical V basis; SecQgv2: light sec-qgv2 path): READER_MISSING.
const READERS=Object.freeze(['QgvScores','QgvV2','Qgv2Inputs','SecQgv2','ScoringDefault','PlaybookEngine','PlaybookConfigDefaults','DeviceWatchlist','TargetV1Builder']);
// Without a price layer (a node test that passes none): no device prices from either (V stays NA with its reason).
const NO_UNIVERSE=Object.freeze({prices:()=>null,priceBasis:()=>null,readStatus:()=>null});
const NO_STORE=Object.freeze({status:()=>null,coverage:()=>null,subscribe:()=>()=>{},monthEndCloses:()=>Promise.resolve({}),dailyCloses:()=>Promise.resolve({}),runnerHistories:()=>Promise.resolve(null)});
// Codes the old reason table (QgvScores.REASON) does not word: P1 states, rank reasons, and the central V codes pre-registered
// from the central V design (draft wording until the central V lands).
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
 NO_OFFICIAL_YET:['중앙 V 게시본이 아직 없습니다(초안 문구)','No central V publication yet (draft wording)'],
 SUPPLY_FAILED:['중앙 V 가격 공급 실패(초안 문구)','Central V price supply failed (draft wording)'],
 VERIFY_FAILED:['중앙 V 검증 실패(초안 문구)','Central V verification failed (draft wording)'],
 PRICE_DEPENDENT_NOT_COMPUTABLE:['가격이 필요한 값이라 중앙 게시본에서 계산하지 않았습니다(초안 문구)','Price-dependent value not computed centrally (draft wording)'],
 JUDGEMENT_NOT_RECORDED:['기록 안 됨','Not recorded'],
 NOTHING_TO_RECORD:['기록할 발생 신호 없음','No occurrence to record']});
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
 // A device page without a result (no usable sec-qgv2.json).
 function emptyPage(state,reason,pub){const pg=deepFreeze({v_source:V_SOURCES.DEVICE_TEMPORARY,engine_v_source:V_SOURCES.DEVICE_TEMPORARY,rank_label:RANK_LABELS.DEVICE_TEMPORARY.ko,state,reason,as_of:null,calc_version:null,type_scope:null,profile_id:null,preset:null,gate:null,
  generation:pub?pub.generation:0,basis_id:null,price_basis:priceBasis(null,null),identities:null,coverage:null,rows:[]});known.add(pg);return pg;}
 function absent(){const s=data.state(QGV2);
  if(s.state==='FAILED'&&s.why==='SCHEMA_NEWER')return['DATA_FORMAT_NEWER','SEC_QGV2_SCHEMA_NEWER'];
  if(s.state==='FAILED')return['READ_FAILED',s.why==='INVALID'?'SEC_QGV2_INVALID':'SEC_QGV2_UNAVAILABLE'];
  return['NO_DATA',s.state==='NOT_PUBLISHED'?'SEC_QGV2_NOT_PUBLISHED':'SEC_QGV2_NOT_AVAILABLE'];}
 function identitiesOf(catalog){try{return catalog?win.DeviceWatchlist.identities(catalog).map(c=>({company_id:c.company_id,ticker:c.ticker})):[];}catch(_){return[];}}
 // Price basis without a price: where the device prices came from, when this device read them, and their own time status.
 function priceBasis(b,cov){
  if(!object(b))return{kind:'DEVICE_RAM',connected:false,source:null,read_id:null,read_at:null,time_status:null,freshness:null,times:[]};
  const t=cov&&Array.isArray(cov.price_time)?cov.price_time:[],rows=t.reduce((a,x)=>a+x.rows,0),confirmed=t.reduce((a,x)=>a+x.confirmed,0),stale=t.reduce((a,x)=>a+x.stale,0);
  return{kind:'DEVICE_RAM',connected:true,source:str(b.source),read_id:str(b.read_id),read_at:str(b.acquired_at),time_status:!rows?null:!confirmed?'UNCONFIRMED':confirmed===rows?'CONFIRMED':'PARTIAL',
   freshness:stale>0?'STALE':rows&&confirmed===rows?'CURRENT':'UNDETERMINED',times:t.map(x=>({source:x.source,rows:x.rows,confirmed:x.confirmed,unconfirmed:x.unconfirmed,stale:x.stale,from:x.from,to:x.to}))};}
 function axisOf(x){if(!object(x))return null;return{status:x.status,score:num(x.score),weight_available:num(x.weight_available),factors_available:x.factors_available,factors_total:x.factors_total,reason:str(x.reason),use:str(x.use),
  factors:(Array.isArray(x.factors)?x.factors:[]).map(f=>({id:f.id,weight:f.weight,score:num(f.score),reason:str(f.reason),category:f.category,basis:str(f.basis)})),
  published:object(x.published)?{...x.published,reason_codes:Array.isArray(x.published.reason_codes)?[...x.published.reason_codes]:[]}:null};}
 /* One row of the computed result (primary, or personal for a preview). A null score always has its reason: V = the coverage V
    reason (the same rule QgvScores.vCoverage counts with), Q/G = the axis reason, total = DATA_FORMAT_NEWER / CALC_VERSION_MISMATCH /
    total_reason, rank = why there is no official rank. */
 function rowRecord(r,{vs,weights,of,targets,personal=false}){
  const QS=win.QgvScores,TB=win.TargetV1Builder,p=personal?r.personal:r.primary,cov=object(p.coverage)?p.coverage:null,axes=cov&&object(cov.axes)?cov.axes:null,flags=Array.isArray(p.flags)?p.flags:[];
  const score={total:num(p.total),q:num(p.q),g:num(p.g),v:num(p.v)},fallback=p.total_reason?p.total_reason:'V2_INPUTS_NOT_AVAILABLE';
  const axisReason=a=>{const x=axes&&axes[a];if(x&&x.reason)return x.reason;const f=x&&Array.isArray(x.factors)?x.factors.find(y=>y.score===null&&y.reason):null;return f?f.reason:fallback;};
  const totalReason=p.total_reason==='DATA_FORMAT_NEWER'?'DATA_FORMAT_NEWER':flags.includes('CALC_VERSION_MISMATCH')?'CALC_VERSION_MISMATCH':fallback;
  const rank=personal?r.personal_rank:r.rank,qgr=personal?r.personal_qg_reference:r.qg_reference,placed=Number.isInteger(rank)?rank:null,qgOrder=object(qgr)&&Number.isInteger(qgr.order)?qgr.order:null;
  const rankReason=placed!==null?null:p.reference_only===true?'REFERENCE_ONLY':r.outside_universe===true?'OUTSIDE_UNIVERSE':qgOrder!==null?'QG_REFERENCE':score.total===null?totalReason:'NOT_RANKED';
  const vf=TB.vFactors(p),src=cov&&object(cov.source)?cov.source:null;
  return{id:r.company_id,ticker:r.ticker,code:str(r.universe_code),record:str(r.code),scope:r.outside_universe===true?'OUTSIDE_UNIVERSE':'UNIVERSE',target:targets.has(r.company_id),reference_only:p.reference_only===true,
   source:vs.id,source_label:vs.ko,score,
   na_reason:{total:score.total===null?totalReason:null,q:score.q===null?axisReason('Q'):null,g:score.g===null?axisReason('G'):null,v:score.v===null?axisReason('V'):null,rank:rankReason},
   rank:{official:personal?null:placed,personal:personal?placed:null,qg_reference_order:qgOrder,group:personal?null:QS.exploreGroup(r),of,weights},
   coverage:{v_factors:{n:vf.n,total:vf.total,missing:[...vf.missing],required_ok:vf.required_ok},axes:{Q:axisOf(axes&&axes.Q),G:axisOf(axes&&axes.G),V:axisOf(axes&&axes.V)},
    factors:{available:num(p.factors_available),total:num(p.factors_total)},states:cov&&Array.isArray(cov.states)?[...cov.states]:[],v_inputs_missing:cov&&Array.isArray(cov.v_inputs_missing)?[...cov.v_inputs_missing]:[]},
   flags:[...flags],value_trap_gate:p.value_trap_gate===true,v_excluded:str(p.v_excluded),types:{selected:Array.isArray(p.selected_types)?[...p.selected_types]:[],reason:str(p.type_reason)},
   row_state:src?str(src.state):null,acquired_at:src?str(src.acquired_at):null,fiscal_year_end:src?str(src.fiscal_year_end):null,profile:src?str(src.profile):null,
   source_reason_codes:src&&Array.isArray(src.reason_codes)?[...src.reason_codes]:[]};}
 // A device result: computed from device quotes, so DEVICE_TEMPORARY (never the switch state read again after the awaits).
 function project(result,inputs,pub){
  const QS=win.QgvScores,c=result.computed,vs=V_SOURCES.DEVICE_TEMPORARY,weights=QS.provenance({kind:'QGV',profile:c.profile}).weights,targets=new Set(ids.map(x=>x.company_id));
  const of=object(c.official)&&Number.isInteger(c.official.ranked)?c.official.ranked:Object.values(c.rows).filter(r=>Number.isInteger(r.rank)).length;
  const cov=QS.vCoverage(result,inputs),b=object(result.price_basis)?result.price_basis:null,calc=str(inputs.calc_version);
  return deepFreeze({v_source:vs,engine_v_source:V_SOURCES.DEVICE_TEMPORARY,rank_label:RANK_LABELS[vs.id].ko,state:'READY',reason:c.v2_state==='READY'?null:c.v2_reason?c.v2_reason:'V2_SCORES_NOT_AVAILABLE',
   as_of:str(c.v2_as_of),calc_version:calc,type_scope:str(c.profile.type_scope),profile_id:c.profile.id,preset:c.profile.preset,gate:c.profile.gate,generation:pub.generation,
   basis_id:JSON.stringify([str(c.v2_as_of),calc,b?str(b.read_id)||str(b.acquired_at)||'READ':null,c.profile.id,pub.generation,epoch]),
   price_basis:priceBasis(b,cov),identities:ids.length?{state:'OK',reason:null,count:ids.length}:{state:'NOT_AVAILABLE',reason:'CATALOG_NOT_AVAILABLE',count:0},
   coverage:cov,rows:Object.values(c.rows).map(r=>rowRecord(r,{vs,weights,of,targets}))});}
 async function devicePage(pub,{preset,gate,signal}){
  const QS=win.QgvScores,inputs=data.get(QGV2);if(!inputs){const[state,reason]=absent();return emptyPage(state,reason,pub);}
  const catalog=await data.static(CATALOG),list=identitiesOf(catalog),key=JSON.stringify(list);stop(signal);
  if(key!==idsKey){idsKey=key;ids=list;QS.setPageIdentities(list);}
  fin=await data.financials().catch(()=>null);await action.stores();stop(signal);
  const result=await QS.pageResult(scoreView,{v2Inputs:inputs,catalog,identities:ids,preset,gate});stop(signal);
  if(!result){const[state,reason]=absent();return emptyPage(state,reason,pub);}
  let pg=byResult.get(result);if(!pg){pg=project(result,inputs,pub);byResult.set(result,pg);held.set(pg,{result,inputs});known.add(pg);}
  return pg;}
 // Central V page (qgv-official/1, Q·G·V all from the publication, never mixed with sec-qgv2.json): not built while OFFICIAL_READER is null.
 function centralPage(){throw Error('NO_OFFICIAL_YET');}
 // preset / gate: a caller's own choice; omitted = this page's profile (setProfile). Every screen gets the same result for the same inputs.
 async function page({preset,gate,signal}={}){check();wire();await data.ready();stop(signal);const pub=data.publication();
  return vSource(pub)==='OFFICIAL_CENTRAL'?centralPage(pub):devicePage(pub,{preset,gate,signal});}
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
 /* Personal preview of the user's own weights over the same inputs, prices and population: never primary, never an official rank.
    The 2.2 personal call (device-profiles.js compare): QgvScores.compute({...base, gate, weights, typeWeights}) with no preset and the
    weight profile's own gate (gate null = QgvV2.GATE_DEFAULT, on). Device quotes: DEVICE_TEMPORARY. */
 function preview(pg,weights,{typeWeights=true,gate=null}={}){const h=result_(pg),QS=win.QgvScores;if(gate!==null&&typeof gate!=='boolean')throw Error('GATE_INVALID');
  let refs={};try{refs=JSON.parse(h.result.reference_key);}catch(_){refs={};}
  const out=QS.compute({identities:h.result.identities,v2Inputs:h.inputs,quotes:h.result.quotes,referenceRows:refs,official:h.result.official,gate,weights,typeWeights}),vs=V_SOURCES.DEVICE_TEMPORARY;
  const x=out.personal,rs=Object.values(out.rows),of=rs.filter(r=>Number.isInteger(r.personal_rank)).length,targets=new Set(ids.map(i=>i.company_id));
  return deepFreeze({weights:'PERSONAL',v_source:vs,rank_label:RANK_LABELS[vs.id].ko,state:x.state,reason:str(x.reason),label:[...x.label],profile_id:x.profile?x.profile.id:null,v_weight_zero:x.v_weight_zero===true,
   rows:x.state==='INVALID'?[]:rs.map(r=>rowRecord(r,{vs,weights:'PERSONAL',of,targets,personal:true}))});}
 function setProfile({preset=null,gate=null}={}){const V2=win.QgvV2;if(preset!==null&&!(V2&&Object.hasOwn(V2.PRESETS,preset)))throw Error('PRESET_UNKNOWN');if(gate!==null&&typeof gate!=='boolean')throw Error('GATE_INVALID');
  profile=Object.freeze({preset,gate});emit('PROFILE');return profile;}
 // The rank wording of a V source id, a Page / preview, or a row (its source): screens show this next to any rank.
 function rankLabel(x,en=false){const id=typeof x==='string'?x:x&&typeof x==='object'?(x.v_source&&x.v_source.id)||x.source:null;const l=Object.hasOwn(RANK_LABELS,id)?RANK_LABELS[id]:RANK_LABELS.DEVICE_TEMPORARY;return en?l.en:l.ko;}
 function reasonText(code,en=false){const QS=win.QgvScores;if(typeof code==='string'&&QS&&Object.hasOwn(QS.REASON,code))return QS.reasonText(code,en);if(typeof code==='string'&&Object.hasOwn(TEXT,code))return TEXT[code][en?1:0];return QS?QS.reasonText(code,en):String(code);}
 let consts=null;
 // Read-only copies for the 2.5 factor tree and weight screens.
 function constants(){check();if(!consts){const V2=win.QgvV2,TB=win.TargetV1Builder;consts=deepFreeze(JSON.parse(JSON.stringify({WEIGHTS:V2.WEIGHTS,PRESETS:V2.PRESETS,DEFAULT_PRESET:V2.DEFAULT_PRESET,GATE_DEFAULT:V2.GATE_DEFAULT,
  FACTORS:V2.FACTORS,MIN_AXIS_WEIGHT:V2.MIN_AXIS_WEIGHT,SUBMETRICS:win.SecQgv2.SUBMETRICS,V_FACTORS:TB.V_FACTORS,V_REQUIRED:TB.V_REQUIRED})));}return consts;}
 function subscribe(fn,{signal}={}){if(typeof fn!=='function')throw Error('SUBSCRIBER_INVALID');if(signal&&signal.aborted)return()=>{};subs.add(fn);const off=()=>{subs.delete(fn);};if(signal)signal.addEventListener('abort',off,{once:true});return off;}
 // engines.js only (source rule): the computed result exactly as QgvScores made it, for the old engines (TARGET draft, playbook).
 // It is always the device result: engines record page.engine_v_source, never page.v_source.
 const forEngines=pg=>result_(pg).result.computed;
 // engines.js only, with forEngines: the sec-qgv2.json value (Qgv2Inputs output) that result was computed from (a re-judgement can
 // replace data.get's value later), and the score view itself (PlaybookScreen.prepareScores reads the same shared result through it).
 const engineInputs=pg=>result_(pg).inputs;
 return Object.freeze({V_SOURCES,RANK_LABELS,READERS,vSource:()=>vSource(data.publication()),page,isPage,row,rows,coverage,preview,setProfile,profile:()=>profile,reasonText,rankLabel,constants,subscribe,forEngines,engineInputs,scoreView});
}
return Object.freeze({create,V_SOURCES,RANK_LABELS,READERS});
});
