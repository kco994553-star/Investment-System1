/* Menu 3 매크로 first-paint skeleton (feature 4); screen-macro-live.js fills it after IS2.ready (P1_DATA_LAYER.md §1.1). */
(function(){
'use strict';
const I=window.IS2,{h,register,parts:{head,section,mascot}}=I;
const S=[['3-1','3.1 경기 · 주식시장 현재 예상 위치'],['3-2','3.2 순환매 위치 (저점 / 고점)'],['3-3','3.3 산업 사이클 (SIC 분류 기준)'],['3-4','3.4 내가 고르는 현재 위치'],['3-5','3.5 나비효과'],['3-6','3.6 매크로 시스템 내용구성']];
function render(route){
 const a=()=>route.signal.aborted,slots={},legend=h('div',{class:'sk band',dataset:{macroLegend:''}}),band=h('div',{class:'scroll',role:'status',dataset:{macroBand:''}},h('span',{class:'chip wait'},'공개 자료 · 불러오는 중'));
 const secs=S.map(([id,t])=>section(id,t,null,slots[id]=h('div',{dataset:{macroSlot:id}},h('p',{class:'pending',role:'status',dataset:{state:'loading'}},'불러오는 중'))));
 const fail=()=>{if(a())return;band.replaceChildren(h('span',{class:'chip err',dataset:{fileState:'LOADER_FAILED'}},'층을 불러오지 못함'));
  for(const s of Object.values(slots))s.replaceChildren(h('div',{class:'sk state-card',dataset:{state:'error',na:'LOADER_FAILED'}},mascot('alarm'),h('p',{class:'err'},'층을 불러오지 못해 매크로 자료를 그리지 못했습니다 · 새로고침해 주세요')));};
 legend.append(band);
 const go=()=>{if(a())return;const L=I.macroLive;if(L&&I.loadState()==='READY')L.screen(route,{legend,band,slots});else fail();};
 const st=typeof I.loadState==='function'?I.loadState():null;
 if(st==='READY'||st==='FAILED')go();else(I.ready||Promise.reject()).then(go,go);
 return h('div',{class:'screen',dataset:{menuScreen:'macro'}},head('3','매크로','지금 경기·시장은 어디쯤? 그 근거는?'),legend,...secs);}
register('macro',render);
})();
