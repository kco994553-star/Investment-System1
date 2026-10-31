/* Menu 4 뉴스 first-paint skeleton (feature 5: 5.1 관계망 · 5.2 공시·뉴스 · 5.3 내용구성 트리); screen-news-live.js fills it after
   IS2.ready (P1_DATA_LAYER.md §1.1). Loaded before screen-menus.js, so it replaces the menu's placeholder. */
(function(){
'use strict';
const I=window.IS2,{h,register,parts:{head,section,mascot}}=I;
const S=[['4-1','4.1 관계망'],['4-2','4.2 공시 · 뉴스'],['4-3','4.3 뉴스 시스템 내용구성']];
function render(route){
 const a=()=>route.signal.aborted,slots={},band=h('div',{class:'scroll',role:'status',dataset:{newsBand:''}},h('span',{class:'chip wait'},'공개 자료 · 불러오는 중'));
 const legend=h('div',{class:'sk band',dataset:{newsLegend:''}},band);
 const secs=S.map(([id,t])=>section(id,t,null,slots[id]=h('div',{dataset:{newsSlot:id}},h('p',{class:'pending',role:'status',dataset:{state:'loading'}},'불러오는 중'))));
 const fail=()=>{if(a())return;band.replaceChildren(h('span',{class:'chip err',dataset:{fileState:'LOADER_FAILED'}},'층을 불러오지 못함'));
  for(const s of Object.values(slots))s.replaceChildren(h('div',{class:'sk state-card',dataset:{state:'error',na:'LOADER_FAILED'}},mascot('alarm'),h('p',{class:'err'},'층을 불러오지 못해 공시·뉴스를 그리지 못했습니다 · 새로고침해 주세요')));};
 const go=()=>{if(a())return;const L=I.newsLive;if(L&&I.loadState()==='READY')L.screen(route,{legend,band,slots});else fail();};
 const st=typeof I.loadState==='function'?I.loadState():null;
 if(st==='READY'||st==='FAILED')go();else(I.ready||Promise.reject()).then(go,go);
 return h('div',{class:'screen',dataset:{menuScreen:'news'}},head('4','뉴스','공시 · 뉴스 · 관계망 · 점수는 바꾸지 않음'),legend,...secs);}
register('news',render);
})();
