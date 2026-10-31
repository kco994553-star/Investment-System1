/* Menu 6 프롬프트 first-paint skeleton (feature 7); screen-prompts-live.js fills it once its file ran (P1_DATA_LAYER.md §1.1). */
(function(){
'use strict';
const I=window.IS2,{h,register,parts:{head,section,mascot}}=I;
function render(route){
 const wait=k=>h('div',{dataset:{promptSlot:k}},h('p',{class:'pending',role:'status',dataset:{state:'loading'}},'불러오는 중')),s1=wait('6-1'),s2=wait('6-2');
 const root=h('div',{class:'screen lb-screen',dataset:{promptScreen:'',screenState:'loading'}},head('6','프롬프트 라이브러리','분석을 AI에게 맡길 때 쓰는 질문 모음'),
  section('6-1','6.1 프롬프트 라이브러리',null,s1),section('6-2','6.2 개인화 · 다른 화면에서 열기',null,s2));
 const go=()=>{if(route.signal.aborted)return;const L=I.promptsLive;if(L){L.screen(route,{root,s1,s2});return;}root.dataset.screenState='error';s2.replaceChildren();
  s1.replaceChildren(h('div',{class:'sk state-card',role:'alert',dataset:{state:'error',promptError:'LOADER_FAILED'}},mascot('alarm'),h('h3',{class:'card-title'},'프롬프트 화면을 불러오지 못했습니다'),h('p',null,'새로고침해 주세요')));};
 const st=typeof I.loadState==='function'?I.loadState():null;
 if(st==='READY'||st==='FAILED')go();else(I.ready||Promise.reject()).then(go,go);
 return root;}
register('prompts',render);
})();
