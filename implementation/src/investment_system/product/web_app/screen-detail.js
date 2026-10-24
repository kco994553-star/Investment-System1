/* Detail screens (owner decision 2026-10-23): features without a place on the draft's first screens move here, reached from
   "→ 자세히" links, 전체 메뉴 and n. 구조 트리. P0 skeleton. */
(function(){
'use strict';
const{h,DETAILS,register,parts:{head,pending}}=window.IS2;
register('detail',route=>{const d=DETAILS.find(x=>x.id===route.params[0]);
 return h('div',{class:'screen',dataset:{detail:d.id}},head('',d.ko,'세부 화면'),pending('이 세부 화면의 기능'));});
})();
