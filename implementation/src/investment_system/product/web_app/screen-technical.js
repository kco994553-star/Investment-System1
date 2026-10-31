/* Menu 2 기술적 분석 first-paint skeleton (feature 3); screen-technical-live.js fills it once its file ran (P1_DATA_LAYER.md §1.1).
   The company box is the shared search part's first-paint half (parts.searchBox); the live file attaches IS2.searchPart to it. */
(function(){
'use strict';
const I=window.IS2,{h,register,parts:{head,section,mascot}}=I;
const S=[['2-1','2.1 기술적 지표 + 정도 설정 + 시나리오'],['2-2','2.2 차트 패턴 + 정도 설정 + 시나리오'],['2-3','2.3 차트 위 내 노트'],['2-4','2.4 기술적 분석 시스템 내용구성']];
function render(route){
 const wait=t=>h('p',{class:'pending',role:'status',dataset:{state:'loading'}},'불러오는 중',t?' · '+t:''),slots={};
 const box=I.parts.searchBox('tech-q',h('label',{for:'tech-q',class:'hand'},'기술적 분석할 기업 · 티커 · 영문 회사명 (Universe504)'));
 const chosen=h('div',{dataset:{techChosen:''}},wait('고른 기업'));
 const secs=S.map(([id,t])=>section(id,t,null,slots[id]=h('div',{dataset:{techSlot:id}},wait())));
 const root=h('div',{class:'screen',dataset:{menuScreen:'technical',screenState:'loading'}},head('2','기술적 분석','추세 · 패턴 · 시나리오와 내 노트 · 공개 판정은 보류'),
  h('section',{class:'sk band','aria-label':'기업 고르기',dataset:{techPick:''}},box.node,chosen),...secs);
 const go=()=>{if(route.signal.aborted)return;const L=I.technicalLive;if(L){L.screen(route,{root,box,chosen,slots});return;}
  root.dataset.screenState='error';chosen.replaceChildren();let first=true;
  for(const s of Object.values(slots)){s.replaceChildren(h('div',{class:'sk state-card',role:first?'alert':null,dataset:{state:'error',na:'LOADER_FAILED'}},mascot('alarm'),
   h('p',{class:'err'},'기술적 분석 화면을 불러오지 못했습니다'),h('p',{class:'reason'},'화면 파일을 불러오지 못했습니다 · 새로고침해 주세요')));first=false;}};
 const st=typeof I.loadState==='function'?I.loadState():null;
 if(st==='READY'||st==='FAILED')go();else(I.ready||Promise.reject()).then(go,go);
 return root;}
register('technical',render);
})();
