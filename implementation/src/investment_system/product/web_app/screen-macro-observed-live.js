/* 3.1 관측 자료 · 갱신 상태 (feature 4.1.3; owner 2026-11-05 "관측 기간·갱신 시각·발표 근거·값 유지·수정·stale를 표시한다. 관측
   자료와 미채택 국면 판단을 구분한다. 기존 운영 보류를 임의 해제하지 않는다."), the part of the 매크로 screen that draws Codex's
   macro-current-query/1 (#477) through IS2.macroObserved (validate, view). screen-macro-live.js makes the block (its head) inside
   section 3-1 after the evidence lines and calls IS2.macroObservedLive.draw(box, {signal}) once per route; this file fills the
   rest of the box. It does not wait for the public files: the source is its own.
   - Source: IS2.macroObserved.source(); today NONE (no public file approved) → the block says so in words, draws no number and
     requests nothing. A file that fails the contract is refused whole (its code), the rest of the screen stays.
   - A shown file: its kind first (합성 개발 검증 for a synthetic file), the query (조회 시각, 계산 캐시 기준과 경과, 보관본 생성, 갱신
     = 캐시 재사용 · 외부 요청 0), the file's counts, then one entry per series with state / stale and reason, 기준 기간 and
     data_asof, frequency · unit · seasonal adjustment, 진단값 관측 or 미산출, 원발표 시각 미확인 · NOT_PROVEN_IN_ARCHIVE, first
     acquisition and selected version times (or their upper bound in words), 값 유지 / 수정 버전 / 새 관측 flags, the last
     successful update with its age and update status (FAILED_AFTER_SUCCESS keeps the last success), and the source's agency /
     terms under 출처 · 약관.
   - No observed value is drawn (the current query file is private and not approved for a public screen; the block says why).
     The fixed line above it keeps 공식 국면 미산출: observed data is not an adopted regime judgment.
   - nodes(src) is the block's drawing from a given source ({state:'OK', payload, data_kind} or NONE / ERROR): the public block
     uses it, and the owner-private panel under it (macro-observed-private, screen-macro-live.js; IS2.privateExpand kind 'macro',
     owner 2026-11-05, DC-44) draws the private copy with it, so both show one format under one rule (no observed value).
   Nothing here stores, logs or sends anything. */
(function(){
'use strict';
const I=window.IS2,{h}=I;
const M=()=>I.macroObserved;
const put=(box,...c)=>{box.replaceChildren();I.append(box,c);return box;};
const line=(k,text)=>h('span',{class:'obs-line',dataset:{obsLine:k}},text);

function entry(s){
 return h('li',{dataset:{obsRow:s.id,obsState:s.state,obsKind:s.resultKind,obsUpdate:s.update,obsVersion:s.version||'NONE'}},
  h('b',null,s.indicator,' · ',s.id),line('name',s.name),line('state',s.lines.state),line('period',s.lines.period+' · '+s.lines.meta),line('kind',s.lines.kind),
  line('evidence',s.lines.evidence),line('flags',s.lines.flags),line('update',s.lines.update),
  h('details',{class:'why'},h('summary',null,'출처 · 약관 ▸'),h('p',{class:'reason',dataset:{obsTerms:''}},s.lines.terms),
   h('p',{class:'reason'},s.lines.vintage),h('p',{class:'reason obs-url'},'원기관 주소 ',s.lines.url)));}

function draw(box,{signal}){
 const S=()=>M(),head=box.firstChild;
 const scope=h('p',{class:'hand',dataset:{obsScope:''}},S().TEXT.SCOPE);
 put(box,head,scope,h('p',{class:'pending',role:'status',dataset:{state:'loading'}},'불러오는 중 · 관측 자료'));
 let p;try{p=S().source();}catch(e){p=Promise.reject(e);}
 Promise.resolve(p).then(src=>{if(signal.aborted)return;paint(box,head,scope,src||null);},()=>{if(!signal.aborted)paint(box,head,scope,{state:'ERROR',code:'MACRO_CURRENT_SOURCE_FAILED'});});}

function paint(box,head,scope,src){put(box,head,scope,...nodes(src));}

function nodes(src){
 const S=M(),T=S.TEXT;
 if(!src||src.state==='NONE')return[h('div',{class:'sk state-card',dataset:{obsState:'NONE',na:(src&&src.code)||'MACRO_CURRENT_NOT_CONNECTED'}},h('b',null,T.NONE),h('span',null,T.NONE_WHY)),
  h('p',{class:'reason'},T.NONE_PLAN)];
 const r=src.state==='OK'?S.validate(src.payload):null;
 if(!r||!r.ok)return[h('div',{class:'sk state-card',role:'alert',dataset:{obsState:'ERROR',na:r?r.code:(src.code||'MACRO_CURRENT_SOURCE_FAILED'),obsPath:r?r.path:''}},
  h('b',null,r?T.INVALID:T.FAILED),h('span',{class:'reason'},r?'계약 위반 '+r.code+' · '+r.path+' · 값을 채우거나 고치지 않음':'다른 매크로 블록은 그대로'))];
 const v=S.view(r.value,{dataKind:src.data_kind||null});
 return[
  h('p',{class:'sk status-line',dataset:{obsData:src.data_kind||'UNSPECIFIED'}},v.status),
  h('dl',{class:'card-body',dataset:{obsQuery:''}},v.query.map(([k,t])=>[h('dt',null,h('b',null,k)),h('dd',null,t)])),
  h('p',{dataset:{obsCounts:''}},v.counts),
  h('p',{class:'reason',dataset:{obsValues:'NOT_SHOWN'}},T.VALUES),
  h('p',{class:'reason'},T.CANDIDATE),
  h('ol',{class:'news-lines obs-rows',dataset:{obsSeries:String(v.series.length)}},v.series.map(entry))];}

I.macroObservedLive=Object.freeze({draw,nodes});
})();
