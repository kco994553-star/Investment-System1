/* Menu 5 포트폴리오 first-paint skeleton (feature 6: 6.1 세 가지 포트폴리오 · 6.2 · 6.3 보고 · 6.4 트리, route #/portfolio, P2-6
   public layer); screen-portfolio-live.js fills it after IS2.ready (P1_DATA_LAYER.md §1.1). Loaded before screen-menus.js, so
   this real screen replaces the menu placeholder (same section ids 5-1 … 5-4). The notice that the model candidates are not a
   confirmed portfolio nor an instruction is drawn here, above every slot, so it stands before any candidate row in every state. */
(function(){
'use strict';
const I=window.IS2,{h,register,parts:{head,section,mascot}}=I;
const S=[['5-1','5.1 세 가지 포트폴리오'],['5-2','5.2 포트폴리오 보고'],['5-3','5.3 모의 포트폴리오 일일 보고'],['5-4','5.4 포트폴리오 시스템 내용구성']];
function notice(){
 return h('div',{class:'sk card notice',role:'note',dataset:{portfolioNotice:'MODEL_NOT_CONFIRMED'}},
  h('p',null,h('b',null,'모델 후보'),'는 공식 평가로 계산한 후보 목록입니다.'),
  h('p',null,h('b',null,'확정된 포트폴리오가 아니고'),', ',h('b',null,'매매 지시도 아닙니다'),'.'),
  h('p',null,'TARGET v1은 아직 ',h('b',null,'확정되지 않았습니다'),'.'));}
function render(route){
 const a=()=>route.signal.aborted,slots={};
 const secs=S.map(([id,t])=>section(id,t,null,id==='5-1'?notice():null,slots[id]=h('div',{dataset:{portfolioSlot:id}},h('p',{class:'pending',role:'status',dataset:{state:'loading'}},'불러오는 중'))));
 const fail=()=>{if(a())return;for(const s of Object.values(slots))s.replaceChildren(h('div',{class:'sk state-card',dataset:{state:'error',na:'LOADER_FAILED'}},mascot('alarm'),h('p',{class:'err'},'층을 불러오지 못해 포트폴리오 자료를 그리지 못했습니다 · 새로고침해 주세요')));};
 const go=()=>{if(a())return;const L=I.portfolioLive;if(L&&I.loadState()==='READY')L.screen(route,{slots});else fail();};
 const st=typeof I.loadState==='function'?I.loadState():null;
 if(st==='READY'||st==='FAILED')go();else(I.ready||Promise.reject()).then(go,go);
 return h('div',{class:'screen',dataset:{menuScreen:'portfolio'}},head('5','포트폴리오','실제 · 모델 · 모의 — 보유와 거래는 이 기기와 내 시트에만'),...secs);}
register('portfolio',render);
})();
