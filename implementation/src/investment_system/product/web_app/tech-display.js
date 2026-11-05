/* Per-company technical display reader (IS2.techDisplay, feature 3.1.2 기업별 지표; owner 2026-11-05 "기술: 기업별 지표와 그룹별
   순위·필터를 각각 연결한다. 전체시장 순위가 없어도 적격 기업 지표는 표시할 수 있게 한다."). Reads Codex's research output
   technical-offline-display/1 with its readiness projection technical-display-readiness/1 (#478 head 419add34,
   TECHNICAL_OFFLINE_DISPLAY_20261105.md, technical_display_offline.py) as written, with no conversion. Calculation
   is Codex's (DC-42): this file only checks, reads and words. validate / find / view are pure and run in node as in the page.
   Price basis (owner 11/05 item 5; Codex #498 head 5597e25e, TECHNICAL_ADJUSTED_LINK_20261105.md, technical_display.py
   describe_readiness / measure_display): a series is RAW (result_kind RAW_SERIES_DIAGNOSTIC, evidence no_split_*, readiness
   adjustment.state DOCUMENTED_NO_SPLIT | UNCONFIRMED, evidence_start/end = no_split_start/end) or SPLIT_ADJUSTED (result_kind
   SPLIT_ADJUSTED_SERIES_DIAGNOSTIC, evidence adjustment_start/end/reference + adjustment_method CONFIRMED_SPLITS_ONLY, state
   CONFIRMED_SPLITS_ONLY | UNCONFIRMED, evidence_start/end = adjustment_start/end). The basis, result_kind, evidence.price_basis,
   every adjustment.price_basis, the state and its evidence range must agree (BASIS_MISMATCH, EVIDENCE_MISMATCH,
   ADJUSTMENT_STATE_MISMATCH, EVIDENCE_RANGE_MISMATCH); an unknown basis / state / method is ENUM. This is the direct-kernel
   output only: the KIS wrapper (kis-bars/1/analysis: evaluation_day, RETAINED_CAPTURE, NORMAL/STALE/MISSING) is another schema
   and is refused here, never renamed into this one. The direct-kernel output carries no settings version (only the five-measure
   boards of 1.1.8 do), so none is shown.
   - Input: {schema, signal_day, series:[{schema, result_kind, series_id, symbol, signal_day, source_kind
     NORMALIZED_PROVIDER_DAILY_BARS, input_start, history_count, excluded_future_rows, price_basis RAW|SPLIT_ADJUSTED, pit_status NOT_VERIFIED,
     publication_status RESEARCH_PRIVATE_ONLY, evidence, rank null, metrics:{<13 ids>:{raw_value, value, unit, null_reasons,
     observation_days, expected_days, window_start, window_end}}, volume_note, volume_latest, pattern_status, readiness:{schema,
     as_of, value_scope, availability_status, source_available_at, availability_reason, stale_status, stale_reason, metrics:{<id>:
     {state, initialization, warmup, continuity, adjustment, identity, block_reasons}}}}]}. SMA_240 (default OFF) may also appear.
   - validate(json) → {ok:true, value} (deep-frozen copy) or {ok:false, code, path}: the whole file is refused at its first fault;
     nothing is repaired or filled. Besides shapes and enums it checks what the block relies on: state VALUE ⇔ value non-null
     (then value = raw_value, no reason); DIAGNOSTIC ⇔ value null and raw_value non-null; NOT_COMPUTED ⇔ both null; a null value
     has a reason (STATE_MISMATCH, VALUE_NOT_RAW, NULL_REASON_MISSING); block_reasons = null_reasons; the warm-up's observed
     sessions = observation_days and its minimum / the initialization method and policy are the contract's table; the adjustment's
     required range = the metric's window; one identity per series; window_end = signal_day = readiness.as_of; rank is null.
   - find(value, symbol) → {state:'FOUND', series} | {state:'NOT_IN_FILE'} | {state:'AMBIGUOUS', count}: by the series' symbol.
     The symbol is only the lookup key of a display series inside this payload (Codex #491): never an identity or join key;
     several series with one symbol stay AMBIGUOUS and none is chosen. Identity is per series (one per output component set);
     window eligibility is per indicator (block_reasons).
   - view(series) → words: per component the kind (채택값 / 진단값만 있음 / 미산출), the adopted value's display text (VALUE only;
     raw_value is never shown, a DIAGNOSTIC says only that a diagnostic exists, counted), the null reasons in words, observation /
     expected days, window, warm-up, continuity, adjustment; per series counts, identity, rank (always 순위 없음 with its reason),
     availability (NOT_VERIFIED) and freshness (UNKNOWN · UPDATE_SCHEDULE_NOT_CONNECTED), the basis (원주가 / 확인된 분할 반영)
     with, on adjusted results, the fixed line ADJUSTED_NOTE, and the evaluation (signal) day. Counts are indicator cells of this one
     result on its one day, never companies or coverage. A null stays 미산출, never 0; a real 0 is a value.
   - source() → Promise {state:'NONE'}: the output is private research (Git-outside, 0600); no public file, no request.
   Values are price-derived: screens show them only as text inside [data-ram-price]; nothing is stored. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else{const I=root.IS2=root.IS2||{};I.techDisplay=api;}})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
const SCHEMA='technical-offline-display/1',READINESS='technical-display-readiness/1';
const BASIS=Object.freeze({RAW:'원주가',SPLIT_ADJUSTED:'확인된 분할 반영'});
const RESULT_KIND=Object.freeze({RAW:'RAW_SERIES_DIAGNOSTIC',SPLIT_ADJUSTED:'SPLIT_ADJUSTED_SERIES_DIAGNOSTIC'});
// Per basis: the evidence prefix, the confirmed adjustment state, the other basis' evidence keys (never mixed in one series).
const BASIS_RULE=Object.freeze({RAW:Object.freeze({prefix:'no_split_',confirmed:'DOCUMENTED_NO_SPLIT',other:'adjustment_'}),
 SPLIT_ADJUSTED:Object.freeze({prefix:'adjustment_',confirmed:'CONFIRMED_SPLITS_ONLY',other:'no_split_'})});
const METHOD=Object.freeze({CONFIRMED_SPLITS_ONLY:'확인된 분할만 반영'});
const ADJUSTED_NOTE='실제 분할 사건 검증 미완료 · 분할 없는 구간의 조정 경로 확인';
const COMPONENTS=Object.freeze(['SMA_5','SMA_20','SMA_60','SMA_120','EMA_20','RSI_14','MACD_12_26','MACD_SIGNAL_9','MACD_HISTOGRAM_12_26_9',
 'BOLL_MIDDLE_20','BOLL_UPPER_20_2','BOLL_LOWER_20_2','ATR_14']);
const OPTIONAL=Object.freeze(['SMA_240']);
const ROLL='GSQ015_ROLLING_WINDOW',FULL='GSQ015_FULL_RETAINED_HISTORY',MEAN='ROLLING_CLOSE_MEAN',SD='ROLLING_20_CLOSE_POPULATION_STDDEV';
// [label, group (the 3.1.2 table row), minimum sessions, initialization method, policy] from the contract's table.
const META=Object.freeze(Object.fromEntries([
 ['SMA_5','SMA 5','SMA',5,MEAN,ROLL],['SMA_20','SMA 20','SMA',20,MEAN,ROLL],['SMA_60','SMA 60','SMA',60,MEAN,ROLL],['SMA_120','SMA 120','SMA',120,MEAN,ROLL],
 ['SMA_240','SMA 240 (기본 꺼짐)','SMA',240,MEAN,ROLL],
 ['EMA_20','EMA 20','EMA',20,'FIRST_20_CLOSE_SMA_THEN_EMA',FULL],['RSI_14','RSI 14','RSI',15,'FIRST_14_CHANGES_MEAN_THEN_WILDER',FULL],
 ['MACD_12_26','MACD 선 (12·26)','MACD',26,'FULL_INPUT_SMA_SEEDED_EMA_12_MINUS_26',FULL],['MACD_SIGNAL_9','MACD 신호선 (9)','MACD',34,'FIRST_9_VALID_MACD_MEAN_THEN_EMA',FULL],
 ['MACD_HISTOGRAM_12_26_9','MACD 히스토그램','MACD',34,'MACD_MINUS_SIGNAL',FULL],
 ['BOLL_MIDDLE_20','볼린저 중심선 (20)','BOLL',20,MEAN,ROLL],['BOLL_UPPER_20_2','볼린저 상단 (20 · 2σ)','BOLL',20,SD,ROLL],['BOLL_LOWER_20_2','볼린저 하단 (20 · 2σ)','BOLL',20,SD,ROLL],
 ['ATR_14','ATR 14','ATR',15,'FIRST_14_TRUE_RANGES_MEAN_THEN_WILDER_RESET_AFTER_OHLC_GAP',FULL]].map(([id,label,group,min,method,policy])=>[id,Object.freeze({label,group,min,method,policy})])));
const UNIT=Object.freeze({PERCENT:'% (0~100)',SOURCE_CURRENCY_PER_SHARE:'주당 · 원 통화',ADJUSTED_PER_SHARE:'주당 · 확인된 분할 반영 · 원 통화'});
const KIND=Object.freeze({VALUE:'채택값',DIAGNOSTIC:'진단값만 있음',NOT_COMPUTED:'미산출'});
const REASON=Object.freeze({PRICE_WINDOW_INCOMPLETE:'보유 일봉에 빠진 거래일',RAW_PRICE_BASIS_REQUIRED:'원주가 기준이 아님',CLOSE_INVALID:'종가 값 이상',
 WARMUP:'초기 봉 부족',CALCULATION_ERROR:'계산 오류',ZERO_TOTAL_CHANGE:'가격 변화 0 · 정의 불가',OHLC_MISSING:'고가·저가 결손',OHLC_BASIS_UNCONFIRMED:'OHLC 기준 미확인',
 ACTION_BASIS_UNCONFIRMED:'무분할 근거가 의존 구간을 덮지 못함',IDENTITY_UNCONFIRMED:'증권 신원 미확인',CURRENCY_UNCONFIRMED:'통화 근거 미확인'});
const WARMUP=Object.freeze({READY:'초기 봉 충족',INSUFFICIENT:'초기 봉 부족',NOT_EVALUATED:'초기 봉 평가 불가'});
const CONTINUITY=Object.freeze({COMPLETE:'세션 연속',INCOMPLETE:'세션 결손',INVALID:'종가·기준 이상'});
// Words of the basis-dependent codes on an adjusted series (RAW keeps REASON / ADJUSTMENT).
const REASON_ADJUSTED=Object.freeze({RAW_PRICE_BASIS_REQUIRED:'봉 가격 기준이 분할 반영 기준과 다름',ACTION_BASIS_UNCONFIRMED:'분할 반영 근거가 의존 구간을 덮지 못함'});
const ADJUSTMENT=Object.freeze({DOCUMENTED_NO_SPLIT:'의존 구간 무분할 문서 확인',CONFIRMED_SPLITS_ONLY:'의존 구간 확인된 분할 반영',UNCONFIRMED:'의존 구간 무분할 근거 미확인'});
const ADJUSTMENT_ADJUSTED=Object.freeze({...ADJUSTMENT,UNCONFIRMED:'의존 구간 분할 반영 근거 미확인'});
const IDENTITY=Object.freeze({CONFIRMED:'신원 확인',DOCUMENT_RECONSTRUCTED:'문서 재구성 신원',UNKNOWN:'신원 미확인'});
const FIXED_ID=Object.freeze({MISSING_RANKING_BLOCKED:'고정 증권 ID 없음 · 순위를 매기지 않음',PRESENT_NOT_RANKED:'고정 증권 ID 있음 · 이 파일은 순위를 매기지 않음'});
const POLICY=Object.freeze({[ROLL]:'최근 N봉 창',[FULL]:'전체 보유 이력으로 시작값'});
const SCOPE=Object.freeze({PRIVATE_RESEARCH_DOCUMENT_RECONSTRUCTION:'비공개 연구 문서 재구성 범위의 값 · 공식 운영 가격 아님'});
const AVAILABILITY=Object.freeze({NOT_VERIFIED:'과거 자료 가용 시각 미확인 · 날짜로 추정하지 않음'});
const STALE=Object.freeze({UNKNOWN:'최신 여부 알 수 없음'}),STALE_REASON=Object.freeze({UPDATE_SCHEDULE_NOT_CONNECTED:'갱신 일정 미연결'});
const TEXT=Object.freeze({NONE:'기업별 지표 자료가 아직 없습니다',NONE_WHY:'계산은 Codex(#478 · #498 technical-offline-display/1, 원주가 · 확인된 분할 반영) · 비공개 연구 결과라 공개 화면에 연결하지 않음 · 합성 자료는 개발 검증에서만',
 INVALID:'지표 파일이 계약과 달라 파일 전체를 쓰지 않습니다',FAILED:'지표 파일을 읽지 못했습니다',SYNTHETIC:'합성 개발 검증',UNKNOWN_REASON:'사유 코드 미등록',
 RANK_NONE:'순위 없음',GROUP:'그룹별 순위·필터는 1. QGV의 1.1.8 기술 조건 필터에서 따로 봅니다'});
const MAX=Object.freeze({series:1000,text:200,depth:10,list:50,evidence:40});
const DAY=/^(\d{4})-(\d{2})-(\d{2})$/,CODE=/^[A-Z][A-Z0-9_]{0,63}$/;
const own=(o,k)=>Object.prototype.hasOwnProperty.call(o,k);
const isObj=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
function Refusal(code,path){this.code=code;this.path=path;}
const refuse=(code,path)=>{throw new Refusal(code,path);};
function keys(o,want,path,optional=[]){if(!isObj(o))refuse('TYPE',path);for(const k of want)if(!own(o,k))refuse('KEY_MISSING',path+'.'+k);
 for(const k of Object.keys(o))if(!want.includes(k)&&!optional.includes(k))refuse('KEY_UNKNOWN',path+'.'+k);}
const str=(v,path)=>{if(typeof v!=='string'||!v)refuse('TYPE',path);if(v.length>MAX.text)refuse('TOO_LARGE',path);return v;};
const code=(v,path)=>{if(typeof v!=='string'||!CODE.test(v))refuse('CODE_INVALID',path);return v;};
const codeOrNull=(v,path)=>{if(v!==null)code(v,path);};
const codes=(v,path)=>{if(!Array.isArray(v))refuse('TYPE',path);if(v.length>MAX.list)refuse('TOO_LARGE',path);v.forEach((c,i)=>code(c,path+'['+i+']'));};
const count=(v,path)=>{if(!Number.isInteger(v))refuse('TYPE',path);if(v<0)refuse('RANGE',path);};
const numOrNull=(v,path)=>{if(v!==null&&typeof v!=='number')refuse('TYPE',path);};
const is=(v,want,path)=>{if(v!==want)refuse('ENUM',path);};
const oneOf=(v,set,path)=>{if(typeof v!=='string'||!own(set,v))refuse('ENUM',path);};
function day(v,path){const m=typeof v==='string'&&DAY.exec(v);if(!m)refuse('DATE_INVALID',path);const d=new Date(Date.UTC(+m[1],+m[2]-1,+m[3]));
 if(d.getUTCMonth()!==+m[2]-1||d.getUTCDate()!==+m[3])refuse('DATE_INVALID',path);return v;}
const dayOrNull=(v,path)=>{if(v!==null)day(v,path);};
const same=(a,b)=>a.length===b.length&&a.every((x,i)=>x===b[i]);
function copy(v,path,depth){if(depth>MAX.depth)refuse('TOO_DEEP',path);
 if(v===null||typeof v==='string'||typeof v==='boolean')return v;if(typeof v==='number'){if(!Number.isFinite(v))refuse('NUMBER_NOT_FINITE',path);return v;}
 if(Array.isArray(v))return v.map((x,i)=>copy(x,path+'['+i+']',depth+1));
 if(isObj(v)&&(Object.getPrototypeOf(v)===Object.prototype||Object.getPrototypeOf(v)===null)){const o={};for(const k of Object.keys(v))o[k]=copy(v[k],path+'.'+k,depth+1);return o;}
 refuse('TYPE',path);}
function deepFreeze(v){if(v&&typeof v==='object'){Object.freeze(v);for(const k of Object.keys(v))deepFreeze(v[k]);}return v;}

const TOP=['schema','signal_day','series'];
const SERIES=['schema','result_kind','series_id','symbol','signal_day','source_kind','input_start','history_count','excluded_future_rows','price_basis',
 'pit_status','publication_status','evidence','rank','metrics','volume_note','volume_latest','pattern_status','readiness'];
const METRIC=['raw_value','value','unit','null_reasons','observation_days','expected_days','window_start','window_end'];
const RDY=['schema','as_of','value_scope','availability_status','source_available_at','availability_reason','stale_status','stale_reason','metrics'];
const RMETRIC=['state','initialization','warmup','continuity','adjustment','identity','block_reasons'];
function checkMetric(id,m,r,s,path,rpath){const B=BASIS_RULE[s.price_basis];
 keys(m,METRIC,path);numOrNull(m.raw_value,path+'.raw_value');numOrNull(m.value,path+'.value');
 is(m.unit,id==='RSI_14'?'PERCENT':'SOURCE_CURRENCY_PER_SHARE',path+'.unit');codes(m.null_reasons,path+'.null_reasons');
 count(m.observation_days,path+'.observation_days');count(m.expected_days,path+'.expected_days');
 if(m.observation_days>m.expected_days)refuse('RANGE',path+'.observation_days');
 day(m.window_start,path+'.window_start');day(m.window_end,path+'.window_end');
 if(m.window_end!==s.signal_day)refuse('WINDOW_MISMATCH',path+'.window_end');if(m.window_start>m.window_end)refuse('RANGE',path+'.window_start');
 if(m.value!==null){if(m.value!==m.raw_value)refuse('VALUE_NOT_RAW',path+'.value');if(m.null_reasons.length)refuse('REASON_WITH_VALUE',path+'.null_reasons');}
 else if(!m.null_reasons.length)refuse('NULL_REASON_MISSING',path+'.null_reasons');
 const M=META[id];keys(r,RMETRIC,rpath);
 oneOf(r.state,KIND,rpath+'.state');if(r.state!==(m.value!==null?'VALUE':m.raw_value!==null?'DIAGNOSTIC':'NOT_COMPUTED'))refuse('STATE_MISMATCH',rpath+'.state');
 keys(r.initialization,['method','policy','input_start'],rpath+'.initialization');is(r.initialization.method,M.method,rpath+'.initialization.method');
 is(r.initialization.policy,M.policy,rpath+'.initialization.policy');if(r.initialization.input_start!==s.input_start)refuse('INPUT_START_MISMATCH',rpath+'.initialization.input_start');
 keys(r.warmup,['minimum_sessions','observed_sessions','state'],rpath+'.warmup');is(r.warmup.minimum_sessions,M.min,rpath+'.warmup.minimum_sessions');
 if(r.warmup.observed_sessions!==m.observation_days)refuse('OBSERVED_MISMATCH',rpath+'.warmup.observed_sessions');oneOf(r.warmup.state,WARMUP,rpath+'.warmup.state');
 keys(r.continuity,['state','reasons'],rpath+'.continuity');oneOf(r.continuity.state,CONTINUITY,rpath+'.continuity.state');codes(r.continuity.reasons,rpath+'.continuity.reasons');
 const a=r.adjustment,ap=rpath+'.adjustment';keys(a,['price_basis','state','required_start','required_end','evidence_start','evidence_end'],ap);
 oneOf(a.price_basis,BASIS,ap+'.price_basis');if(a.price_basis!==s.price_basis)refuse('BASIS_MISMATCH',ap+'.price_basis');
 oneOf(a.state,ADJUSTMENT,ap+'.state');if(a.state!=='UNCONFIRMED'&&a.state!==B.confirmed)refuse('BASIS_MISMATCH',ap+'.state');
 if(a.required_start!==m.window_start||a.required_end!==m.window_end)refuse('WINDOW_MISMATCH',ap+'.required_start');
 dayOrNull(a.evidence_start,ap+'.evidence_start');dayOrNull(a.evidence_end,ap+'.evidence_end');
 // evidence_start/end are the series' own no_split_* (RAW) or adjustment_* (SPLIT_ADJUSTED) range, as written.
 for(const e of['start','end'])if(a['evidence_'+e]!==(own(s.evidence,B.prefix+e)?s.evidence[B.prefix+e]:null))refuse('EVIDENCE_MISMATCH',ap+'.evidence_'+e);
 if((a.state==='UNCONFIRMED')!==m.null_reasons.includes('ACTION_BASIS_UNCONFIRMED'))refuse('ADJUSTMENT_STATE_MISMATCH',ap+'.state');
 if(a.state===B.confirmed){if(a.evidence_start===null||a.evidence_end===null||a.evidence_start>a.required_start||a.evidence_end<a.required_end)refuse('EVIDENCE_RANGE_MISMATCH',ap+'.evidence_start');
  if(s.price_basis==='SPLIT_ADJUSTED'&&s.evidence.adjustment_method!=='CONFIRMED_SPLITS_ONLY')refuse('EVIDENCE_MISMATCH',path.replace(/\.metrics\.[A-Z0-9_]+$/,'')+'.evidence.adjustment_method');
  if(typeof s.evidence[B.prefix+'reference']!=='string'||!s.evidence[B.prefix+'reference'])refuse('EVIDENCE_MISMATCH',path.replace(/\.metrics\.[A-Z0-9_]+$/,'')+'.evidence.'+B.prefix+'reference');}
 keys(r.identity,['state','reference_present','fixed_security_id_state'],rpath+'.identity');code(r.identity.state,rpath+'.identity.state');
 if(typeof r.identity.reference_present!=='boolean')refuse('TYPE',rpath+'.identity.reference_present');oneOf(r.identity.fixed_security_id_state,FIXED_ID,rpath+'.identity.fixed_security_id_state');
 codes(r.block_reasons,rpath+'.block_reasons');if(!same(r.block_reasons,m.null_reasons))refuse('BLOCK_REASONS_MISMATCH',rpath+'.block_reasons');}
function checkSeries(s,top,path){
 keys(s,SERIES,path);is(s.schema,SCHEMA,path+'.schema');oneOf(s.price_basis,BASIS,path+'.price_basis');
 if(typeof s.result_kind!=='string'||!Object.values(RESULT_KIND).includes(s.result_kind))refuse('ENUM',path+'.result_kind');
 if(s.result_kind!==RESULT_KIND[s.price_basis])refuse('BASIS_MISMATCH',path+'.result_kind');str(s.series_id,path+'.series_id');str(s.symbol,path+'.symbol');
 day(s.signal_day,path+'.signal_day');if(s.signal_day!==top.signal_day)refuse('SIGNAL_DAY_MISMATCH',path+'.signal_day');
 is(s.source_kind,'NORMALIZED_PROVIDER_DAILY_BARS',path+'.source_kind');day(s.input_start,path+'.input_start');if(s.input_start>s.signal_day)refuse('RANGE',path+'.input_start');
 count(s.history_count,path+'.history_count');count(s.excluded_future_rows,path+'.excluded_future_rows');
 is(s.pit_status,'NOT_VERIFIED',path+'.pit_status');is(s.publication_status,'RESEARCH_PRIVATE_ONLY',path+'.publication_status');
 if(!isObj(s.evidence))refuse('TYPE',path+'.evidence');if(Object.keys(s.evidence).length>MAX.evidence)refuse('TOO_LARGE',path+'.evidence');
 for(const[k,v]of Object.entries(s.evidence))if(v!==null&&!['string','number','boolean'].includes(typeof v))refuse('TYPE',path+'.evidence.'+k);
 const ep=path+'.evidence',B=BASIS_RULE[s.price_basis];
 if(own(s.evidence,'price_basis')?s.evidence.price_basis!==s.price_basis:s.price_basis!=='RAW')refuse('BASIS_MISMATCH',ep+'.price_basis');
 for(const k of Object.keys(s.evidence))if(k.startsWith(B.other))refuse('BASIS_MISMATCH',ep+'.'+k);
 if(own(s.evidence,'adjustment_method'))oneOf(s.evidence.adjustment_method,METHOD,ep+'.adjustment_method');
 if(s.rank!==null)refuse('RANK_UNEXPECTED',path+'.rank');
 code(s.pattern_status,path+'.pattern_status');
 const vn=s.volume_note,vp=path+'.volume_note';keys(vn,['raw_state','state','reason','window_start','window_end','null_reasons'],vp);
 code(vn.raw_state,vp+'.raw_state');codeOrNull(vn.state,vp+'.state');codeOrNull(vn.reason,vp+'.reason');day(vn.window_start,vp+'.window_start');day(vn.window_end,vp+'.window_end');codes(vn.null_reasons,vp+'.null_reasons');
 const vl=s.volume_latest,lp=path+'.volume_latest';keys(vl,['raw_value','value','unit','last_observed_session','null_reasons'],lp);
 numOrNull(vl.raw_value,lp+'.raw_value');numOrNull(vl.value,lp+'.value');is(vl.unit,'SHARES',lp+'.unit');dayOrNull(vl.last_observed_session,lp+'.last_observed_session');codes(vl.null_reasons,lp+'.null_reasons');
 const R=s.readiness,rp=path+'.readiness';keys(R,RDY,rp);is(R.schema,READINESS,rp+'.schema');if(R.as_of!==s.signal_day)refuse('AS_OF_MISMATCH',rp+'.as_of');
 oneOf(R.value_scope,SCOPE,rp+'.value_scope');oneOf(R.availability_status,AVAILABILITY,rp+'.availability_status');
 if(R.source_available_at!==null)refuse('AVAILABILITY_UNEXPECTED',rp+'.source_available_at');code(R.availability_reason,rp+'.availability_reason');
 oneOf(R.stale_status,STALE,rp+'.stale_status');code(R.stale_reason,rp+'.stale_reason');
 keys(s.metrics,COMPONENTS,path+'.metrics',OPTIONAL);keys(R.metrics,Object.keys(s.metrics),rp+'.metrics');
 let identity=null;
 for(const id of Object.keys(s.metrics)){checkMetric(id,s.metrics[id],R.metrics[id],s,path+'.metrics.'+id,rp+'.metrics.'+id);
  const t=JSON.stringify(R.metrics[id].identity);if(identity===null)identity=t;else if(t!==identity)refuse('IDENTITY_MISMATCH',rp+'.metrics.'+id+'.identity');}}
function validate(json){
 try{if(!isObj(json))refuse('TYPE','$');const v=copy(json,'$',0);keys(v,TOP,'$');is(v.schema,SCHEMA,'$.schema');day(v.signal_day,'$.signal_day');
  if(!Array.isArray(v.series))refuse('TYPE','$.series');if(!v.series.length)refuse('EMPTY','$.series');if(v.series.length>MAX.series)refuse('TOO_LARGE','$.series');
  const ids=new Set();v.series.forEach((s,i)=>{const p='$.series['+i+']';checkSeries(s,v,p);if(ids.has(s.series_id))refuse('SERIES_DUPLICATE',p+'.series_id');ids.add(s.series_id);});
  return{ok:true,value:deepFreeze(v)};}
 catch(e){if(e instanceof Refusal)return{ok:false,code:e.code,path:e.path};throw e;}}

// The series of one company, by symbol (the file has no security id to join; more than one series for a symbol is not chosen).
function find(value,symbol){const hits=value.series.filter(s=>s.symbol===symbol);
 return hits.length===1?{state:'FOUND',series:hits[0]}:hits.length?{state:'AMBIGUOUS',count:hits.length}:{state:'NOT_IN_FILE'};}
// Display of one adopted value (display only; never used for logic): up to four decimals, a real 0 is '0', a null is null.
function num(v){if(v===null||v===undefined||typeof v!=='number'||!Number.isFinite(v))return null;
 const t=Math.abs(v).toFixed(4).replace(/\.?0+$/,'');return(v<0&&t!=='0'?'−':'')+t;}
const reasonText=(c,basis)=>(typeof c==='string'&&basis==='SPLIT_ADJUSTED'&&own(REASON_ADJUSTED,c)?REASON_ADJUSTED[c]:typeof c==='string'&&own(REASON,c)?REASON[c]:TEXT.UNKNOWN_REASON);
const words=(set,c)=>(typeof c==='string'&&own(set,c)?set[c]:TEXT.UNKNOWN_REASON);
function view(s){const R=s.readiness,ids=Object.keys(s.metrics),first=R.metrics[ids[0]],adj=s.price_basis==='SPLIT_ADJUSTED';
 const cur=typeof s.evidence.currency==='string'&&/^[A-Z]{3}$/.test(s.evidence.currency)?s.evidence.currency:null;
 const counts={VALUE:0,DIAGNOSTIC:0,NOT_COMPUTED:0};
 const items=[...COMPONENTS,...OPTIONAL].filter(id=>ids.includes(id)).map(id=>{const m=s.metrics[id],r=R.metrics[id],a=r.adjustment;counts[r.state]++;
  return Object.freeze({id,label:META[id].label,group:META[id].group,kind:r.state,kindText:KIND[r.state],
   value:r.state==='VALUE'?num(m.value):null,unit:m.unit==='PERCENT'?UNIT.PERCENT:(adj?UNIT.ADJUSTED_PER_SHARE:UNIT.SOURCE_CURRENCY_PER_SHARE)+(cur?' '+cur:''),
   reasons:Object.freeze(m.null_reasons.map(c=>Object.freeze({code:c,text:reasonText(c,s.price_basis)}))),
   observed:m.observation_days+' / '+m.expected_days+'세션',window:m.window_start+' ~ '+m.window_end,
   warmup:words(WARMUP,r.warmup.state)+' · 최소 '+r.warmup.minimum_sessions+' · 관측 '+r.warmup.observed_sessions,warmupState:r.warmup.state,
   init:words(POLICY,r.initialization.policy)+(r.initialization.policy===FULL?' (시작 '+r.initialization.input_start+')':''),
   continuity:words(CONTINUITY,r.continuity.state),continuityState:r.continuity.state,
   adjustment:words(adj?ADJUSTMENT_ADJUSTED:ADJUSTMENT,a.state)+' · 필요 '+a.required_start+' ~ '+a.required_end+' · 근거 '+(a.evidence_start===null||a.evidence_end===null?'없음':a.evidence_start+' ~ '+a.evidence_end),
   adjustmentState:a.state});});
 const id=first.identity;
 return Object.freeze({symbol:s.symbol,series_id:s.series_id,as_of:R.as_of,items:Object.freeze(items),counts:Object.freeze(counts),
  countsText:'이 결과(평가일 '+R.as_of+')의 지표 '+items.length+'칸 · '+KIND.VALUE+' '+counts.VALUE+' · '+KIND.DIAGNOSTIC+' '+counts.DIAGNOSTIC+' · '+KIND.NOT_COMPUTED+' '+counts.NOT_COMPUTED,
  day:'평가일(신호일) '+s.signal_day,
  history:'보유 일봉 '+s.history_count+'봉 · '+s.input_start+' ~ '+s.signal_day+(s.excluded_future_rows?' · 평가일 뒤 '+s.excluded_future_rows+'봉 제외':''),
  basis:'가격 기준 '+BASIS[s.price_basis]+'('+s.price_basis+') · PIT 미검증 · '+words(SCOPE,R.value_scope),basisCode:s.price_basis,basisText:BASIS[s.price_basis],
  adjustedNote:adj?ADJUSTED_NOTE:null,
  identity:words(IDENTITY,id.state)+(id.reference_present?' · 근거 문서 있음':' · 근거 문서 없음'),identityState:id.state,
  rank:TEXT.RANK_NONE+' · '+words(FIXED_ID,id.fixed_security_id_state),rankCode:id.fixed_security_id_state,
  availability:words(AVAILABILITY,R.availability_status),availabilityCode:R.availability_status,
  stale:words(STALE,R.stale_status)+' · '+words(STALE_REASON,R.stale_reason),staleCode:R.stale_status,staleReason:R.stale_reason});}
const status=src=>(!src?TEXT.NONE:src.data_kind==='SYNTHETIC'?TEXT.SYNTHETIC:typeof src.data_kind==='string'&&src.data_kind?'자료 종류 · '+src.data_kind:'자료 종류 표시 없음');
function source(){return Promise.resolve(Object.freeze({state:'NONE',code:'TECH_DISPLAY_NOT_CONNECTED',payload:null,data_kind:null,text:TEXT.NONE}));}
return Object.freeze({SCHEMA,READINESS,BASIS,ADJUSTED_NOTE,COMPONENTS,OPTIONAL,META,KIND,REASON,TEXT,validate,find,view,num,reasonText,status,source});
});
