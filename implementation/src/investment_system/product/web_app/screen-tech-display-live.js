/* 3.1.2 고른 기업의 지표 (기업별; owner 2026-11-05 "기술: 기업별 지표와 그룹별 순위·필터를 각각 연결한다. 전체시장 순위가 없어도
   적격 기업 지표는 표시할 수 있게 한다."), the part of the 기술적 분석 screen (2-1) that runs after IS2.ready.
   screen-technical-live.js asks IS2.techDisplayLive.create({signal, redraw}) once per route and calls block(row) on every
   company change; block returns this block's content for the chosen company row (or none).
   - Data: Codex's technical-offline-display/1 + technical-display-readiness/1 (#478) through IS2.techDisplay (validate, find,
     view); today the source is NONE (private research output), so the block says so and draws no number. The series is the one
     whose symbol is the company's ticker.
   - Per company only. The group ranks and filters are 1.1.8 (screen-tech-filter-live.js on #/qgv) and are not drawn here; this
     file never ranks. A company with indicators and no group / full-market rank still shows its indicators; the rank line says
     순위 없음 with the file's reason (fixed security id state) and points to 1.1.8.
   - Each of the 13 components: VALUE → 채택값 with the adopted value; DIAGNOSTIC → 진단값만 있음 (raw_value is never shown, not even
     as RAM text: the block says a diagnostic exists and counts it); NOT_COMPUTED → 미산출 with its null reasons in words. Also
     observation / expected days, window, warm-up, initialization policy, continuity and adjustment; per series the identity,
     availability (NOT_VERIFIED) and freshness (UNKNOWN · UPDATE_SCHEDULE_NOT_CONNECTED). Synthetic input says 합성 개발 검증.
   - The public verdict band and the 3.1.2 table stay 판정 보류 (NO_APPROVED_PRICE_SERIES): a shown value is not a verdict.
   Values are price-derived: text inside [data-ram-price] only; the read lives in RAM (this route); nothing is stored. */
(function(){
'use strict';
const I=window.IS2,{h,href}=I;
const T=()=>I.techDisplay;
const ram=(...t)=>h('span',{dataset:{ramPrice:''}},...t);
const na=(code,...words)=>h('span',{class:'reason',dataset:{na:code||''}},...words);
const reasons=list=>list.map(r=>r.text).join(' · ');

function create({signal,redraw}){
 const ctx={src:null,value:null,err:null,loading:false};
 function load(){if(ctx.loading)return;ctx.loading=true;let p;try{p=T().source();}catch(e){p=Promise.reject(e);}
  Promise.resolve(p).then(src=>{if(signal.aborted)return;ctx.loading=false;ctx.src=src||null;ctx.value=null;ctx.err=null;
   if(src&&src.state==='OK'){const r=T().validate(src.payload);if(r.ok)ctx.value=r.value;else ctx.err={code:r.code,path:r.path};}redraw();},
  ()=>{if(signal.aborted)return;ctx.loading=false;ctx.src={state:'ERROR',code:'TECH_DISPLAY_SOURCE_FAILED'};ctx.value=null;redraw();});}
 const head=()=>h('div',{class:'lb-head'},h('h3',{class:'stamp sub'},'고른 기업의 지표'),h('span',{class:'meta'},'기능 3.1.2 · 기업별'),
  h('span',{class:'hand'},'그룹 순위·필터와 따로'));
 const group=()=>h('p',{class:'reason',dataset:{displayGroup:''}},T().TEXT.GROUP,' · ',h('a',{class:'more',href:href('qgv')},'→ 1.1.8 기술 조건 필터'));
 function card(it){
  const line=it.kind==='VALUE'?h('span',{dataset:{displayValue:''}},ram(it.value),' ',h('span',{class:'reason'},it.unit))
   :it.kind==='DIAGNOSTIC'?na('DIAGNOSTIC','진단값 1개 있음 · 채택 조건 미충족이라 값은 보이지 않음 · ',reasons(it.reasons))
   :na(it.reasons.length?it.reasons[0].code:'NOT_COMPUTED','미산출 · ',reasons(it.reasons));
  return h('div',{class:'sk tcard',dataset:{displayMetric:it.id,displayKind:it.kind}},h('b',null,it.label),
   h('span',null,h('span',{class:'pill',dataset:{displayKindText:''}},it.kindText)),line,
   h('span',{class:'reason'},'관측 ',it.observed,' · 창 ',it.window),
   h('span',{class:'reason',dataset:{warmup:it.warmupState}},it.warmup,' · ',it.init),
   h('span',{class:'reason',dataset:{continuity:it.continuityState,adjustment:it.adjustmentState}},it.continuity,' · ',it.adjustment));}
 function block(row){
  const S=T();
  if(!row)return[head(),h('p',{class:'reason',dataset:{techDisplayState:'NO_COMPANY'}},'기업을 고르면 그 기업의 지표 상태(채택값 · 진단값만 있음 · 미산출)를 봅니다'),group()];
  const src=ctx.src;
  if(!src){load();return[head(),h('p',{class:'pending',role:'status',dataset:{state:'loading'}},'불러오는 중')];}
  if(src.state==='NONE')return[head(),h('div',{class:'sk state-card',dataset:{techDisplayState:'NONE',na:src.code||'TECH_DISPLAY_NOT_CONNECTED'}},h('b',null,S.TEXT.NONE),h('span',{class:'reason'},S.TEXT.NONE_WHY)),
   h('p',{class:'reason'},'읽을 지표 13개: ',S.COMPONENTS.map(id=>S.META[id].label).join(' · '),' · 상태는 ',Object.values(S.KIND).join(' / ')),group()];
  if(src.state!=='OK'||ctx.err)return[head(),h('div',{class:'sk state-card',role:'alert',dataset:{techDisplayState:'ERROR',na:ctx.err?ctx.err.code:src.code||'TECH_DISPLAY_SOURCE_FAILED',path:ctx.err?ctx.err.path:''}},
   h('b',null,ctx.err?S.TEXT.INVALID:S.TEXT.FAILED),h('span',{class:'reason'},'지표 값 없이 구조와 설명만 봅니다')),group()];
  const hit=S.find(ctx.value,row.ticker);
  if(hit.state!=='FOUND')return[head(),h('p',{class:'sk status-line',dataset:{techDisplayData:src.data_kind||'UNSPECIFIED'}},S.status(src),' · ',S.SCHEMA),
   h('div',{class:'sk state-card',dataset:{techDisplayState:hit.state}},h('b',null,hit.state==='AMBIGUOUS'?row.ticker+' 계열이 '+hit.count+'개라 고르지 않습니다':'이 파일에 '+row.ticker+' 계열이 없습니다'),
    h('span',{class:'reason'},'계열 기호(symbol)로만 찾습니다 · 숫자를 만들지 않음')),group()];
  const v=S.view(hit.series);
  return[head(),
   h('p',{class:'sk status-line',dataset:{techDisplayData:src.data_kind||'UNSPECIFIED',techDisplayState:'FOUND'}},S.status(src),' · ',S.SCHEMA,' · 평가일 ',v.as_of,' · 계산 Codex · 공개 판정 아님'),
   h('p',{dataset:{displayRank:v.rankCode}},h('b',null,v.rank),' · 지표는 순위 없이도 표시'),group(),
   h('dl',{class:'card-body',dataset:{displayFacts:''}},
    [['보유 일봉',v.history],['가격 기준',v.basis],['신원',v.identity],['가용 시각',h('span',{dataset:{displayAvailability:v.availabilityCode}},v.availability)],
     ['최신 여부',h('span',{dataset:{displayStale:v.staleCode,na:v.staleReason}},v.stale)]].map(([k,x])=>[h('dt',null,h('b',null,k)),h('dd',null,x)])),
   h('p',{class:'sk status-line',role:'status',dataset:{displayCounts:v.counts.VALUE+'/'+v.counts.DIAGNOSTIC+'/'+v.counts.NOT_COMPUTED}},v.countsText,' · 진단값은 개수만'),
   h('div',{class:'td-cards'},...v.items.map(card)),
   h('p',{class:'reason'},'채택값 = 신원 · 의존 구간 무분할 · 통화 근거를 모두 갖춘 값 · 값 표시는 판정이 아님 · 지표 판정은 위 표대로 보류')];}
 return Object.freeze({load,block});}
I.techDisplayLive=Object.freeze({create});
})();
