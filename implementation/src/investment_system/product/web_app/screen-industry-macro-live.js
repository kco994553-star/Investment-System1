/* 공통 산업 → 매크로 근거 (owner 2026-11-09 queue item 5; Codex #525 company-industry-macro-query/1) inside the common classification
   private panel of 0. 기업 검색 (private-expand-live.js ccPaint asks IS2.industryMacroLive.block({view}) once the bundle is painted).
   - One click, one private read (the classification route, part industry_macro) → IS2.industryMacro.validate against the bundle's view
     (same date, hash, dictionary, mapping) and the one taxonomy IS2.taxonomy shows → the summary (rows, links, active mappings, series,
     unknown mappings and their reasons) and, for the company chosen on this screen (IS2.selection), its common industry, mapping,
     series observation and evidence.
   - Never an industry link or a regime call when the query says UNKNOWN: the words say 미확인 with the reason, that the macro current
     query is unaffected, and that a link is not a regime, cycle position, probability, signal or weight. 0 stays 0; a hidden value is
     미산출. RAM only; nothing stored; the request only inside the click (IS2.prices.kisRead). */
(function(){
'use strict';
const I=window.IS2,{h}=I;
const M=()=>I.industryMacro;
const CODE=/^[A-Z][A-Z0-9_]{1,63}$/;
const codeOf=e=>{const m=e&&typeof e.message==='string'?e.message:'';return CODE.test(m)?m:'PRIVATE_READ_FAILED';};
const WORD=Object.freeze({KIS_SERIES_NOT_FOUND:'전달 위치에 산업 매크로 조회 결과가 없습니다',ROUTE_NOT_FOUND:'비공개 서버에 이 경로가 아직 없습니다(Worker 배포 전)',
 REQUEST_INVALID:'비공개 서버가 이 요청을 받지 않습니다(Worker 배포 전일 수 있음)',RATE_LIMITED:'요청이 많아 잠시 뒤 다시',UPSTREAM_UNAVAILABLE:'비공개 자료 서버 응답 없음',
 AUTH_FORBIDDEN:'서버가 오너 확인을 거부했습니다 · 다시 로그인하세요',AUTH_REQUIRED:'로그인이 끝났습니다 · 다시 로그인하세요',
 CLASSIFICATION_CONTEXT_MISMATCH:'지금 받은 분류 묶음과 다른 분류로 만든 조회입니다',TAXONOMY_MISMATCH:'화면의 공통 사전과 다른 사전으로 만든 조회입니다',
 TAXONOMY_VERSION_MISMATCH:'화면의 공통 사전과 다른 판으로 만든 조회입니다'});
const say=c=>WORD[c]||'오류 · '+c;
const KIND=Object.freeze({RETAINED_INPUT:'보관 실자료',SYNTHETIC:'합성 자료 · 시험용'});
const list=(items,d,empty)=>items.length?h('ul',{class:'news-lines',dataset:d},items.map(t=>h('li',null,t))):h('p',{class:'reason',dataset:d},empty);

function block({view}){
 const state=h('p',{class:'reason',role:'status',dataset:{imState:'IDLE'}}),area=h('div',{class:'cc-wrap',dataset:{imArea:''}});
 const btn=h('button',{type:'button',class:'btn',dataset:{imOpen:''}},'산업 매크로 근거 불러오기');
 const set=(c,t)=>{state.dataset.imState=c;state.textContent=t;};
 let busy=false;
 btn.addEventListener('click',e=>{if(busy)return;busy=true;btn.disabled=true;set('LOADING','불러오는 중 · 산업 매크로 조회 결과 1개');
  let p;try{p=I.prices.kisRead(e,[['classification','industry_macro']]);}catch(err){p=Promise.reject(err);}
  Promise.resolve(p).then(([q])=>{const r=M().validate(q,{view});
   if(!r.ok){set('ERROR','산업 매크로 조회를 쓰지 않음 · '+say(r.code)+' · '+r.code+' · '+r.path);btn.disabled=false;return;}
   btn.hidden=true;paint(r.value);},
  err=>{const c=codeOf(err);set('ERROR',say(c));btn.disabled=false;}).finally(()=>{busy=false;});});
 function paint(q){const s=M().summaryView(q);
  set('READY',s.head+' · '+(KIND[q.data_kind]||q.data_kind));
  let sel=null;try{const x=I.selection.get();sel=x&&x.id?x.id:null;}catch(_){sel=null;}
  const c=sel?M().companyView(q,sel):null;
  area.replaceChildren(
   h('p',{class:'reason',dataset:{imContext:''}},s.context),
   h('p',{class:'hand',dataset:{imNot:''}},s.not),
   s.unknownMappings?h('p',{class:'reason',dataset:{imUnknownMappings:''}},s.unknownMappings):null,
   s.inactive.length?list(s.inactive,{imInactive:String(s.inactive.length)},''):null,
   s.unknownCompanies.length?h('p',{class:'reason',dataset:{imUnknownCompanies:''}},'산업 미연결 기업 · ',s.unknownCompanies.join(' · ')):null,
   h('p',{class:'reason',dataset:{imKeeps:''}},s.keeps,' · ',s.pit),
   c?h('div',{class:'sk card',dataset:{imCompany:c.id,imStatus:c.status}},h('h4',null,'이 기업 · ',c.id,' · ',c.industry),
     h('p',{dataset:{imHead:''}},c.head),
     list(c.mappings,{imMappings:String(c.mappings.length)},'근거 있는 산업 대응 없음'),
     list(c.series,{imSeries:String(c.series.length)},'연결된 계열 없음'),
     c.gaps.length?list(c.gaps,{imGaps:String(c.gaps.length)},''):null,
     list(c.evidence,{imEvidence:String(c.evidence.length)},'근거 없음'))
    :h('p',{class:'reason',dataset:{imCompany:'NONE'}},sel?'선택한 기업이 이 조회에 없습니다':'기업을 고르면 그 기업의 산업 근거를 보입니다'));}
 return h('div',{class:'sk card',dataset:{imBlock:''}},h('h4',null,'공통 산업 → 매크로 근거 (비공개 조회 결과)'),
  h('p',{class:'reason'},'근거가 확인된 원천 산업 대응만 · 계열 값은 원래 조회 시각 그대로 · 나누거나 합치거나 국면을 만들지 않음'),btn,state,area);}
I.industryMacroLive=Object.freeze({block});
})();
