/* Menu n+1 Lab first-paint skeleton (feature 9: 9.1 백테스트 · 9.2 전진검증); screen-lab-live.js fills it after IS2.ready
   (P1_DATA_LAYER.md §1.1). Loaded before screen-menus.js, so this real screen replaces the menu placeholder (same section ids). */
(function(){
'use strict';
const I=window.IS2,{h,register,parts:{head,section,mascot}}=I;
const S=[['lab-1','n+1.1 백테스트'],['lab-2','n+1.2 전진검증']];
function render(route){
 const a=()=>route.signal.aborted,slots={};
 const secs=S.map(([id,t])=>section(id,t,null,slots[id]=h('div',{dataset:{labSlot:id}},h('p',{class:'pending',role:'status',dataset:{state:'loading'}},'불러오는 중'))));
 const fail=()=>{if(a())return;for(const s of Object.values(slots))s.replaceChildren(h('div',{class:'sk state-card',dataset:{state:'error',na:'LOADER_FAILED'}},mascot('alarm'),h('p',{class:'err'},'층을 불러오지 못해 Lab 자료를 그리지 못했습니다 · 새로고침해 주세요')));};
 const go=()=>{if(a())return;const L=I.labLive;if(L&&I.loadState()==='READY')L.screen(route,{slots});else fail();};
 const st=typeof I.loadState==='function'?I.loadState():null;
 if(st==='READY'||st==='FAILED')go();else(I.ready||Promise.reject()).then(go,go);
 return h('div',{class:'screen',dataset:{menuScreen:'lab'}},head('n+1','Lab','실험 · 검증 — 결과가 없으면 없다고 적습니다'),...secs);}
register('lab',render);
})();
