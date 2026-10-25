/* 0. 기업 검색 · 검색 결과: first-paint skeleton only; screen-search-live.js fills it after IS2.ready (P1_DATA_LAYER.md §1.1). */
(function(){
'use strict';
const I=window.IS2,{h,icon,href,register,parts:{card,pending,more}}=I;
const later=(route,kind,refs)=>{if(I.ready)I.ready.then(()=>{const L=I.searchLive;if(L&&!route.signal.aborted)L[kind](route,refs);},()=>{});};
function box(label){
 const input=h('input',{id:'q',type:'search',autocomplete:'off',spellcheck:'false',placeholder:'티커 · 회사명 · 한글명',role:'combobox','aria-expanded':'false',
  'aria-controls':'q-list','aria-autocomplete':'list',dataset:{searchInput:''}});
 const list=h('ul',{id:'q-list',class:'sk search-list',role:'listbox','aria-label':'찾은 기업',hidden:true,dataset:{searchList:''}});
 const status=h('p',{class:'sr-only',role:'status',dataset:{searchStatus:''}}),pre=new AbortController(),b={input,list,status,pre,submit:null};
 input.addEventListener('input',()=>{const q=!!input.value.trim();list.replaceChildren(...(q?[h('li',{class:'search-msg',role:'presentation',dataset:{searchState:'loading'}},'불러오는 중')]:[]));
  list.hidden=!q;input.setAttribute('aria-expanded',String(q));status.textContent=q?'검색 목록 불러오는 중':'';},{signal:pre.signal});
 const go=e=>{e.preventDefault();if(b.submit)return b.submit(e);const q=input.value.trim();if(q)location.hash=href('company',q);};
 const form=h('form',{class:'sk search-box',role:'search',dataset:{searchForm:''},onsubmit:e=>e.preventDefault()},
  icon(['M13 4 A9 9 0 1 1 12.99 4','M20 20 L27 27'],30),input,h('button',{class:'btn solid',type:'submit',onclick:go},'검색'));
 b.anchor=h('div',{class:'search-anchor'},form,list);b.note=h('div',{class:'search-note-line'});
 b.node=h('div',{class:'search-wrap'},label,b.anchor,status,b.note);
 return b;}
function search(route){
 const b=box(h('label',{for:'q',class:'hand hero-label'},'티커 · 회사명 · 한글명으로 검색'));
 const chips=h('div',{class:'chip-rows',tabindex:'-1',dataset:{homeChips:''}},pending('최근 · ★ 즐겨찾기 기업'));
 const quote=h('section',{class:'sk home-quote','aria-label':'투자 이야기',dataset:{quote:''}},pending('투자 이야기 · 인물과 출처'));
 later(route,'home',{box:b,chips,quote});
 return h('div',{class:'screen'},
  h('section',{class:'hero'},
   h('h1',{class:'hero-title'},'어떤 기업을 ',h('span',{class:'hl'},'볼까요?')),
   h('svg:svg',{class:'hero-underline',viewBox:'0 0 560 26',preserveAspectRatio:'none','aria-hidden':'true'},h('svg:path',{d:'M8 16 C 120 6, 260 22, 380 12 S 520 8, 552 14'})),
   b.node,chips,h('p',{class:'hand hero-aside'},'검색하면 ↓ QGV + 기술적 분석 + 매크로를 한 장에 보여 줌')),
  quote);
}
function result(route){
 const given=route.params[0],b=box(h('label',{for:'q',class:'sr-only'},'다른 기업 검색')),body=x=>h('div',{class:'card-body'},x);
 const name=h('h1',{class:'result-name',dataset:{resultCode:given}},given),facts=h('div',{class:'result-facts',dataset:{resultFacts:''}},pending('회사명 · 거래소 · SIC · 유형'));
 const star=h('span',{class:'star-wrap'},h('button',{type:'button',class:'chip star','aria-pressed':'false',disabled:true,dataset:{favorite:''}},h('span',{'aria-hidden':'true'},'☆ '),'즐겨찾기'));
 const bodies={qgv:body(pending('Q · G · V 막대, 종합 점수 · 순위')),technical:body(h('p',{class:'na',dataset:{na:'PRICE_ON_CLICK'}},'가격 이력은 기술적 분석 화면에서 [불러오기]를 눌러야 계산합니다')),
  macro:body(pending('경고등 판정 · 공개 자료 기준')),news:body(pending('공시 · 뉴스 다섯 줄')),portfolio:body(pending('이 기기 보유 기록'))};
 later(route,'company',{box:b,given,name,facts,star,bodies});
 return h('div',{class:'screen'},b.node,h('section',{class:'result-head'},h('span',{class:'stamp'},'검색 결과'),name,facts,star),
  h('div',{class:'grid-3'},
   card('1. QGV',{shadow:'q',id:'qgv',link:href('qgv')},bodies.qgv,more('리더보드 · 가중치 · 스탯창')),
   card('2. 기술적 분석',{shadow:'g',id:'technical',link:href('technical')},bodies.technical,more('시나리오 · 패턴 · 내 노트')),
   card('3. 매크로',{shadow:'v',id:'macro',link:href('macro')},bodies.macro,more('근거 · 조건 · 확률'))),
  h('div',{class:'grid-2'},
   card(h('span',{class:'hl'},'4. 이 기업 소식'),{id:'news'},bodies.news,more('뉴스에서 전체 보기',href('news'))),
   card('5. 내 포트폴리오에서',{id:'portfolio'},bodies.portfolio,more('포트폴리오에서 보기',href('portfolio')))));
}
register('search',search);register('company',result);
})();
