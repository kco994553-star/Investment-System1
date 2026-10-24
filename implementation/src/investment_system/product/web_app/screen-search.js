/* 0. 기업 검색 · 검색 결과 (draft board Main / MMain). P0 skeleton: the search box routes to the result page; the result page
   shows the draft's five cards (1 QGV · 2 기술적 분석 · 3 매크로 · 4 이 기업 소식 · 5 내 포트폴리오에서) as 연결 전. */
(function(){
'use strict';
const{h,icon,href,register,parts:{card,pending,more}}=window.IS2;
const SEARCH=['M13 4 A9 9 0 1 1 12.99 4','M20 20 L27 27'];
function search(){
 const input=h('input',{id:'q',type:'search',autocomplete:'off',placeholder:'티커 · 회사명 · 한글명',dataset:{searchInput:''}});
 const form=h('form',{class:'sk search-box',role:'search',dataset:{searchForm:''},onsubmit:e=>{e.preventDefault();const q=input.value.trim();if(q)location.hash=href('company',q);}},
  icon(SEARCH,30),input,h('button',{class:'btn solid',type:'submit'},'검색'));
 return h('div',{class:'screen'},
  h('section',{class:'hero'},
   h('h1',{class:'hero-title'},'어떤 기업을 ',h('span',{class:'hl'},'볼까요?')),
   h('label',{for:'q',class:'hand hero-label'},'티커 · 회사명 · 한글명으로 검색'),form,
   h('p',{class:'hand hero-aside'},'검색하면 ↓ QGV + 기술적 분석 + 매크로를 한 장에 보여 줌')),
  pending('최근 · ★ 즐겨찾기 기업'));
}
function result(route){
 const code=route.params[0];
 return h('div',{class:'screen'},
  h('section',{class:'result-head'},h('span',{class:'stamp'},'검색 결과'),h('h1',{class:'result-name',dataset:{resultCode:code}},code),pending('회사명 · SIC · 유형')),
  h('div',{class:'grid-3'},
   card('1. QGV',{shadow:'q',id:'qgv',link:href('qgv')},pending('Q · G · V 막대, 종합 점수 · 순위 · 비교군'),more('리더보드 · 가중치 · 스탯창')),
   card('2. 기술적 분석',{shadow:'g',id:'technical',link:href('technical')},pending('추세 신호 · 패턴'),more('시나리오 · 패턴 · 내 노트')),
   card('3. 매크로',{shadow:'v',id:'macro',link:href('macro')},pending('경기 위치 · 산업 사이클'),more('근거 · 조건 · 확률'))),
  h('div',{class:'grid-2'},
   card(h('span',{class:'hl'},'4. 이 기업 소식'),{id:'news'},pending('공시 · 뉴스 · 관계 다섯 줄 요약')),
   card('5. 내 포트폴리오에서',{id:'portfolio'},pending('보유 비중 · 모델 적합 비중 (이 기기에서만)'),more('일일 보고에서 보기',href('portfolio')))));
}
register('search',search);register('company',result);
})();
