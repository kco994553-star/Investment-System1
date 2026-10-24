/* New frontend shell: draft header (map logo, menu 0~n+1, device chip), phone bottom tabs + 전체 메뉴 drawer, footer line,
   and the hash-route mount. Screens register themselves with IS2.register(id, render(route) -> Node). */
(function(){
'use strict';
const{h,icon,MENU,TABS,DETAILS,parse,href,menuOf,screen}=window.IS2;
const LOGO=['M5 10 L15 6 L25 10 L35 6 L35 32 L25 36 L15 32 L5 36 Z','M15 6 L15 32 M25 10 L25 36'];
const TAB_ICON={search:['M6 18 L18 7 L30 18 M10 15 L10 30 L26 30 L26 15'],qgv:['M6 30 L6 20 M14 30 L14 12 M22 30 L22 16','M26 6 A5 5 0 1 1 26.01 6'],
 portfolio:['M18 6 A12 12 0 1 0 30 18 L18 18 Z','M22 4 A12 12 0 0 1 32 14 L22 14 Z'],news:['M7 8 L25 8 L25 30 L7 30 Z','M11 13 L21 13 M11 18 L21 18 M11 23 L17 23','M25 12 L30 12 L30 28 A2 2 0 0 1 25 28']};
const label=m=>m.no+'. '+m.ko;

function header(current){
 const logo=icon(LOGO,40);const dot=document.createElementNS('http://www.w3.org/2000/svg','circle');dot.setAttribute('cx','29');dot.setAttribute('cy','18');dot.setAttribute('r','3');dot.setAttribute('stroke','#D7322A');logo.appendChild(dot);
 return h('header',{class:'top'},
  h('a',{class:'brand',href:href('search')},logo,h('span',null,'투자시스템 지도')),
  h('nav',{class:'menu','aria-label':'주요 메뉴'},MENU.filter(m=>m.id!=='search').map(m=>h('a',{href:href(m.id),'aria-current':current===m.id?'page':null,dataset:{menu:m.id}},label(m)))),
  h('span',{class:'chip device-chip',dataset:{deviceChip:''}},'로그인 안 함 · 이 기기 기준'));
}
function drawer(){
 const panel=h('div',{class:'drawer-panel',role:'dialog','aria-modal':'true','aria-label':'전체 메뉴'},
  h('h2',null,'전체 메뉴'),
  h('nav',{'aria-label':'전체 메뉴 목록'},MENU.map(m=>h('a',{href:href(m.id),dataset:{drawerMenu:m.id}},label(m)))),
  h('h3',null,'세부 화면'),
  h('nav',{'aria-label':'세부 화면 목록'},DETAILS.map(d=>h('a',{href:href('detail',d.id),dataset:{drawerDetail:d.id}},d.ko))),
  h('button',{class:'btn',type:'button',dataset:{drawerClose:''}},'닫기'));
 const el=h('div',{class:'drawer',hidden:true,dataset:{drawer:''}},panel);
 el.addEventListener('click',e=>{if(e.target===el||e.target.closest('[data-drawer-close]')||e.target.closest('a'))close();});
 return el;
}
function tabbar(current){
 return h('nav',{class:'tabbar','aria-label':'아래 메뉴'},
  TABS.map(id=>{const m=MENU.find(x=>x.id===id);return h('a',{href:href(id),'aria-current':current===id?'page':null,dataset:{tab:id}},icon(TAB_ICON[id],26),id==='search'?'홈':m.ko);}),
  h('button',{type:'button','aria-haspopup':'dialog',dataset:{tab:'all'},onclick:open},icon(['M6 10 L30 10 M6 18 L30 18 M6 26 L30 26'],26),'전체'));
}
let lastFocus=null;
function open(){const d=document.querySelector('[data-drawer]');lastFocus=document.activeElement;d.hidden=false;d.querySelector('a').focus();}
function close(){const d=document.querySelector('[data-drawer]');if(d.hidden)return;d.hidden=true;if(lastFocus&&lastFocus.focus)lastFocus.focus();}

function render(){
 const route=parse(location.hash),current=menuOf(route),app=document.getElementById('app');
 const make=screen(route.id);let body;
 try{body=make?make(route):h('p',{class:'pending'},'화면 준비 중');}catch(e){body=h('p',{class:'pending',role:'alert'},'화면을 그리지 못했습니다 · '+String(e&&e.message||e));}
 app.replaceChildren(h('div',{class:'page'},header(current),h('main',{id:'main',tabindex:'-1',dataset:{route:route.id}},body),
  h('footer',{class:'foot'},'검색 순서는 추천 순위가 아님 · 가격 기반 값은 내 기기에서만 계산 · 투자 권유나 자문이 아님')),tabbar(current),drawer());
 document.title=(route.id==='search'?'':((MENU.find(m=>m.id===current)||{}).ko||'세부 화면')+' · ')+'투자시스템 지도';
}
window.addEventListener('hashchange',()=>{render();const m=document.getElementById('main');if(m)m.focus({preventScroll:true});window.scrollTo(0,0);});
document.addEventListener('keydown',e=>{if(e.key==='Escape')close();});
window.IS2.start=render;
})();
