/* News refresh-by-source reader (IS2.newsRefresh, feature 5.2.7 수집 상태; owner 2026-11-05: "원천별 마지막 성공·부분 실패·신규·
   중복·변경을 표시한다. 일부 원천 실패 때문에 정상 수집된 다른 원천까지 숨기지 않는다"). Reads the `refresh` block of the public
   news-signals.json schema_version 2 as Codex publishes it (implementation/docs/daily_data_pipeline/NEWS_SIGNALS.md "공개 파일 형식
   (schema_version 2, 별도 파일)"; product/news_signals.py source_refresh / refresh_result; #483 e3154ee3 keeps the public shape) with
   no conversion. Calculation is Codex's (DC-42): nothing here is summed, derived or filled; it only checks, keeps and words.
   - Input: the news-signals.json payload. The whole file is validated by the old reader (web_assets/news-signals.js
     NewsSignals.validate through IS2.data.list('news'), which also re-derives each summary from the company entries); this reader
     checks again only what it shows, so an injected payload cannot reach the screen unchecked.
   - validate(payload) → {ok:true, value} (a deep-frozen copy: schema_version, as_of, reason_codes, refresh) or {ok:false, code,
     path}; the first fault refuses the whole block. Checks: schema 1 has no `refresh`; schema 2 has it (null = written without a
     collection); exact keys; instants (YYYY-MM-DDTHH:MM:SS+00:00); attempted_at = as_of and each last_attempt_at = attempted_at;
     result enums; last_result_code null exactly for UPDATED / NO_NEW_ITEMS, else a fixed code; company counts and new_items
     non-negative integers; result agrees with the counts the file states (all answered → UPDATED / NO_NEW_ITEMS, UPDATED exactly
     when new_items > 0; some → PARTIAL_FAILED; none → FAILED when one failed, else NOT_RUN; no new item without an answer);
     items_carried_from null when every company answered and never after last_success_at; last_success_at not after the attempt;
     refresh.result = the two sources' combination; reason_codes carry REFRESH_<result> exactly for a failed / partial / not-run
     refresh.
   - view(value) → {kind, overall, sources:[{source, label, result, bad, cells:[{key, label, text, kind}]}]}: words only. kind
     RECORDED (schema 2 run), NO_RUN (refresh null), UNRECORDED (schema 1). A cell's kind is VALUE (from the file) or NA (미산출 /
     미제공, with its reason): a null is never shown as 0, a real 0 is a value. Revisions and DUPLICATE re-observations are counted
     only in the run log (`counts.revisions`, `duplicates`), not in the public file: always 미제공 here.
   - source(layerValue) → {state:'OK', payload, data_kind:null} for the layer's validated file, {state:'NONE'} when the layer has none.
     Tests replace it to show a synthetic payload (data_kind 'SYNTHETIC' → the block says 합성 개발 검증).
   No request, no storage, no score. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else{const I=root.IS2=root.IS2||{};I.newsRefresh=api;}})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
const SOURCES=Object.freeze(['GDELT','IR']);
const RESULTS=Object.freeze(['UPDATED','NO_NEW_ITEMS','PARTIAL_FAILED','FAILED','NOT_RUN']),SUCCEEDED=Object.freeze(['UPDATED','NO_NEW_ITEMS']);
const REFRESH_KEYS=Object.freeze(['attempted_at','result','sources']);
const SOURCE_KEYS=Object.freeze(['last_attempt_at','last_success_at','last_result','last_result_code','items_carried_from','companies','new_items']);
const COUNT_KEYS=Object.freeze(['succeeded','failed','not_run']);
const REFRESH_REASONS=Object.freeze({PARTIAL_FAILED:'REFRESH_PARTIAL_FAILED',FAILED:'REFRESH_FAILED',NOT_RUN:'REFRESH_NOT_RUN'});
const INSTANT=/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00$/,CODE=/^[A-Z][A-Z0-9_]{0,39}$/,REASON=/^[A-Z][A-Z0-9_]{0,63}$/;
const LABEL=Object.freeze({GDELT:'GDELT',IR:'회사 IR'});
const RESULT_TEXT=Object.freeze({UPDATED:'갱신',NO_NEW_ITEMS:'새 항목 없음',PARTIAL_FAILED:'일부 실패',FAILED:'실패',NOT_RUN:'미실행'});
const OVERALL_TEXT=Object.freeze({UPDATED:'두 원천 모두 응답 · 새 항목 반영',NO_NEW_ITEMS:'두 원천 모두 응답 · 새 항목 없음',PARTIAL_FAILED:'일부 원천·회사 실패 · 응답한 원천은 그대로 표시',
 FAILED:'모든 원천 응답 없음 · 이전 자료 유지',NOT_RUN:'요청하지 않음 · 이전 자료 유지'});
const TEXT=Object.freeze({NONE:'뉴스 파일이 없어 원천별 갱신 기록을 보일 수 없습니다',INVALID:'원천별 갱신 기록이 계약과 달라 이 칸을 쓰지 않습니다',
 UNRECORDED:'원천별 갱신 기록 없음 · 이전 형식 파일 (schema 1)',NO_RUN:'원천별 갱신 기록 없음 · 이 파일은 수집 없이 만들어짐 (refresh 없음)',
 SYNTHETIC:'합성 개발 검증 · 실제 수집 결과 아님',NOT_IN_FILE:'미제공 · 공개 파일에 없음'});
const own=(o,k)=>Object.prototype.hasOwnProperty.call(o,k);
const isObj=v=>v!==null&&typeof v==='object'&&!Array.isArray(v)&&(Object.getPrototypeOf(v)===Object.prototype||Object.getPrototypeOf(v)===null);
function Refusal(code,path){this.code=code;this.path=path;}
const refuse=(code,path)=>{throw new Refusal(code,path);};
function keys(o,want,path){if(!isObj(o))refuse('TYPE',path);for(const k of want)if(!own(o,k))refuse('KEY_MISSING',path+'.'+k);
 for(const k of Object.keys(o))if(!want.includes(k))refuse('KEY_UNKNOWN',path+'.'+k);}
function instant(v,path){if(typeof v!=='string'||!INSTANT.test(v))refuse('INSTANT_INVALID',path);const t=Date.parse(v);
 if(!Number.isFinite(t)||new Date(t).toISOString().slice(0,19)!==v.slice(0,19))refuse('INSTANT_INVALID',path);return t;}
const count=(v,path)=>{if(!Number.isInteger(v))refuse('TYPE',path);if(v<0)refuse('RANGE',path);return v;};
function deepFreeze(v){if(v&&typeof v==='object'){Object.freeze(v);for(const k of Object.keys(v))deepFreeze(v[k]);}return v;}
// A plain copy of JSON data (strings, finite numbers, booleans, null, arrays, plain objects); anything else is refused.
function copy(v,path,depth){if(depth>12)refuse('TOO_DEEP',path);
 if(v===null||typeof v==='string'||typeof v==='boolean')return v;if(typeof v==='number'){if(!Number.isFinite(v))refuse('NUMBER_NOT_FINITE',path);return v;}
 if(Array.isArray(v))return v.map((x,i)=>copy(x,path+'['+i+']',depth+1));
 if(isObj(v)){const o={};for(const k of Object.keys(v))o[k]=copy(v[k],path+'.'+k,depth+1);return o;}
 refuse('TYPE',path);}
// The two sources' combination (NEWS_SIGNALS.md refresh.result, product/news_signals.py refresh_result).
function combined(results){if(results.every(r=>SUCCEEDED.includes(r)))return results.includes('UPDATED')?'UPDATED':'NO_NEW_ITEMS';
 if(results.some(r=>SUCCEEDED.includes(r)||r==='PARTIAL_FAILED'))return 'PARTIAL_FAILED';return results.includes('FAILED')?'FAILED':'NOT_RUN';}
function checkSource(s,attempted,path){
 keys(s,SOURCE_KEYS,path);
 const at=instant(s.last_attempt_at,path+'.last_attempt_at');if(s.last_attempt_at!==attempted)refuse('ATTEMPT_MISMATCH',path+'.last_attempt_at');
 if(!RESULTS.includes(s.last_result))refuse('ENUM',path+'.last_result');const ok=SUCCEEDED.includes(s.last_result);
 if(ok){if(s.last_result_code!==null)refuse('CODE_UNEXPECTED',path+'.last_result_code');}
 else if(typeof s.last_result_code!=='string'||!CODE.test(s.last_result_code))refuse('CODE_INVALID',path+'.last_result_code');
 keys(s.companies,COUNT_KEYS,path+'.companies');const n={};for(const k of COUNT_KEYS)n[k]=count(s.companies[k],path+'.companies.'+k);
 const fresh=count(s.new_items,path+'.new_items');
 const want=n.succeeded>0&&!n.failed&&!n.not_run?(fresh>0?'UPDATED':'NO_NEW_ITEMS'):n.succeeded>0?'PARTIAL_FAILED':n.failed>0?'FAILED':'NOT_RUN';
 if(s.last_result!==want)refuse('RESULT_MISMATCH',path+'.last_result');
 if(fresh>0&&n.succeeded===0)refuse('NEW_ITEMS_WITHOUT_ANSWER',path+'.new_items');
 let success=null;if(s.last_success_at!==null){success=instant(s.last_success_at,path+'.last_success_at');if(success>at)refuse('SUCCESS_AFTER_ATTEMPT',path+'.last_success_at');}
 if(s.items_carried_from!==null){const c=instant(s.items_carried_from,path+'.items_carried_from');
  if(ok)refuse('CARRIED_WITHOUT_FAILURE',path+'.items_carried_from');if(success===null||c>success)refuse('CARRIED_AFTER_SUCCESS',path+'.items_carried_from');}}
function check(p){
 if(!isObj(p))refuse('TYPE','$');if(!Number.isInteger(p.schema_version)||![1,2].includes(p.schema_version))refuse('SCHEMA_VERSION','$.schema_version');
 const asOf=p.as_of;instant(asOf,'$.as_of');
 if(!Array.isArray(p.reason_codes))refuse('TYPE','$.reason_codes');p.reason_codes.forEach((c,i)=>{if(typeof c!=='string'||!REASON.test(c))refuse('REASON_INVALID','$.reason_codes['+i+']');});
 const extra=p.reason_codes.filter(c=>Object.values(REFRESH_REASONS).includes(c));
 if(p.schema_version===1){if(own(p,'refresh'))refuse('KEY_UNKNOWN','$.refresh');if(extra.length)refuse('REASON_MISMATCH','$.reason_codes');return{schema_version:1,as_of:asOf,reason_codes:p.reason_codes,refresh:null};}
 if(!own(p,'refresh'))refuse('KEY_MISSING','$.refresh');const r=p.refresh;
 if(r===null){if(extra.length)refuse('REASON_MISMATCH','$.reason_codes');return{schema_version:2,as_of:asOf,reason_codes:p.reason_codes,refresh:null};}
 keys(r,REFRESH_KEYS,'$.refresh');instant(r.attempted_at,'$.refresh.attempted_at');if(r.attempted_at!==asOf)refuse('ATTEMPT_MISMATCH','$.refresh.attempted_at');
 if(!RESULTS.includes(r.result))refuse('ENUM','$.refresh.result');
 keys(r.sources,SOURCES,'$.refresh.sources');for(const s of SOURCES)checkSource(r.sources[s],r.attempted_at,'$.refresh.sources.'+s);
 if(r.result!==combined(SOURCES.map(s=>r.sources[s].last_result)))refuse('RESULT_MISMATCH','$.refresh.result');
 const want=own(REFRESH_REASONS,r.result)?[REFRESH_REASONS[r.result]]:[];if(JSON.stringify(extra)!==JSON.stringify(want))refuse('REASON_MISMATCH','$.reason_codes');
 return{schema_version:2,as_of:asOf,reason_codes:p.reason_codes,refresh:{attempted_at:r.attempted_at,result:r.result,sources:Object.fromEntries(SOURCES.map(s=>[s,r.sources[s]]))}};}
function validate(payload){
 try{return{ok:true,value:deepFreeze(copy(check(copy(payload,'$',0)),'$',0))};}
 catch(e){if(e instanceof Refusal)return{ok:false,code:e.code,path:e.path};throw e;}}
const utc=t=>t.slice(0,10)+' '+t.slice(11,16)+' UTC';
const value=(key,label,text)=>Object.freeze({key,label,text,kind:'VALUE'});
const na=(key,label,text)=>Object.freeze({key,label,text,kind:'NA'});
// One source's words, from the file's own fields only.
function sourceView(name,s){const ok=SUCCEEDED.includes(s.last_result),c=s.companies;
 const result=ok?RESULT_TEXT[s.last_result]:RESULT_TEXT[s.last_result]+' ('+s.last_result_code+')'+(s.items_carried_from!==null?' · 이전 자료 유지':' · 이전 자료 없음');
 const cells=[
  s.last_success_at!==null?value('last_success_at','마지막 성공',utc(s.last_success_at)):na('last_success_at','마지막 성공','미산출 · 응답 받은 적 없음'),
  value('last_attempt_at','마지막 시도',utc(s.last_attempt_at)),
  value('last_result','결과',result),
  value('companies','회사','성공 '+c.succeeded+' · 실패 '+c.failed+' · 미실행 '+c.not_run),
  value('new_items','이번 새 항목',s.new_items+'건'),
  s.items_carried_from!==null?value('items_carried_from','이월 시작',utc(s.items_carried_from)+' 수집분'):ok?na('items_carried_from','이월 시작','이월 없음 · 모든 회사 응답'):na('items_carried_from','이월 시작','이월 없음 · 이전 자료 없음'),
  na('revisions','수정',TEXT.NOT_IN_FILE),
  na('duplicates','중복',TEXT.NOT_IN_FILE)];
 return Object.freeze({source:name,label:LABEL[name],result:s.last_result,code:s.last_result_code,bad:!ok,cells:Object.freeze(cells)});}
function view(v){
 if(v.schema_version===1)return Object.freeze({kind:'UNRECORDED',text:TEXT.UNRECORDED,overall:null,sources:Object.freeze([])});
 if(v.refresh===null)return Object.freeze({kind:'NO_RUN',text:TEXT.NO_RUN,overall:null,sources:Object.freeze([])});
 const r=v.refresh;
 return Object.freeze({kind:'RECORDED',text:'',overall:Object.freeze({result:r.result,text:OVERALL_TEXT[r.result],attempted_at:r.attempted_at,when:utc(r.attempted_at)}),
  sources:Object.freeze(SOURCES.map(s=>sourceView(s,r.sources[s])))});}
function source(layerValue){return layerValue?Object.freeze({state:'OK',payload:layerValue,data_kind:null,text:''}):Object.freeze({state:'NONE',payload:null,data_kind:null,text:TEXT.NONE});}
return Object.freeze({SOURCES,RESULTS,SOURCE_KEYS,RESULT_TEXT,OVERALL_TEXT,TEXT,LABEL,validate,view,source,combined});
});
