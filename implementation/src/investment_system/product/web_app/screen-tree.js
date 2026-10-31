/* Menu n 구조 트리 first-paint skeleton (feature 8); screen-tree-live.js fills it once its file ran (P1_DATA_LAYER.md §1.1). */
(function(){
'use strict';
const I=window.IS2,{h,register,parts:{head,section,mascot}}=I;
function render(route){
 const slot=h('div',{dataset:{treeSlot:''}},h('p',{class:'pending',role:'status',dataset:{state:'loading'}},'불러오는 중 · 구조 트리'));
 const root=h('div',{class:'screen',dataset:{menuScreen:'tree',treeState:'loading'}},head('n','투자시스템 한 장 지도','전체 내용구성 트리 · 메뉴 · 기능 번호 · 세부 화면이 어디로 이어지는지'),section('n-1','n. 구조 트리',null,slot));
 const go=()=>{if(route.signal.aborted)return;const L=I.treeLive;if(L){L.screen(route,{root,slot});return;}root.dataset.treeState='error';
  slot.replaceChildren(h('div',{class:'sk state-card',role:'alert',dataset:{treeCard:'error'}},mascot('alarm'),h('p',{class:'err'},'구조 트리를 그리지 못했습니다'),h('p',{class:'reason'},'화면 파일을 불러오지 못했습니다 · 새로고침해 주세요')));};
 const st=typeof I.loadState==='function'?I.loadState():null;
 if(st==='READY'||st==='FAILED')go();else(I.ready||Promise.reject()).then(go,go);
 return root;}
register('tree',render);
})();
