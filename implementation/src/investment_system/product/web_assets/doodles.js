/* Hand-drawn doodle set (self-made, inline SVG strings, no file or request): one line doodle for home and for each of
   the eight owner menus, the 전체 메뉴 lines, hand-drawn arrows, a hand-drawn underline and a hand-drawn ring.
   Decoration only: every SVG is aria-hidden and focusable="false"; the text next to it carries the meaning. Colour comes
   from currentColor (ink) or the one accent token (theme.css --mark) through CSS classes, never from inline styles.
   Loaded right after the header so the menu has its doodles before first paint. Presentation only: no data. */
(function(root){
 'use strict';
 // 24 x 24 line doodles: round caps, slightly uneven strokes so they read as drawn by hand.
 const ICONS=Object.freeze({
  // home: a small house
  home:['M3.6 11.4 12.2 4.1l8.3 7.2','M5.9 9.7l-.2 10c0 .5.3.8.8.8h11.2c.5 0 .8-.3.8-.8l.1-9.9','M10.1 20.4v-5.2c0-.5.4-.9.9-.9h2c.5 0 .9.4.9.9v5.1'],
  // 1 QGV: a magnifier over bars
  qgv:['M2.8 20.7c5.9-.3 12.1-.3 18.5.1','M4.6 20.4v-4.5','M8.5 20.5v-7.6','M12.4 20.4v-3.9','M15.4 4c2.5-.1 4.5 1.9 4.5 4.4.1 2.5-1.9 4.5-4.4 4.6-2.5 0-4.5-1.9-4.6-4.4C10.8 6.1 12.8 4.1 15.4 4z','M18.6 11.9l2.9 3.1'],
  // 2 기술적 분석: three candlesticks
  technical:['M5.2 9.3h2.7l-.1 6.2H5.1z','M6.6 5.9v3.3M6.5 15.6v3.6','M11 6.4h2.7v5.5H11z','M12.4 3.2v3.1M12.3 12v3.7','M16.7 11.6h2.7v4.6h-2.8z','M18 8.2v3.3M18.1 16.3v3.5','M2.9 21c6-.4 12.2-.3 18.4.1'],
  // 3 매크로: a globe
  macro:['M12 3.2c4.9-.2 8.9 3.8 8.9 8.8 0 4.9-3.9 8.8-8.8 8.9-5 0-8.9-4-8.9-8.9C3.2 7 7.1 3.3 12 3.2z','M12 3.4c-2.5 2.5-3.8 5.4-3.7 8.7.1 3.2 1.3 6.1 3.8 8.7','M12.1 3.3c2.4 2.7 3.6 5.6 3.6 8.8 0 3.1-1.2 6-3.6 8.7','M3.5 12.1c5.8.5 11.6.4 17.3-.2','M5.1 7.6c4.6.9 9.3.9 14 .1','M5.2 16.5c4.6-.8 9.2-.8 13.8.2'],
  // 4 뉴스·공시·기업 관계: a folded newspaper
  news:['M4.2 5c4.1-.3 8.3-.3 12.4 0l.1 13.6c0 .9.6 1.7 1.6 1.7H5.8c-.9 0-1.6-.7-1.6-1.6z','M16.7 9.2h2.5c.5 0 .9.4.9.9v8.6c0 .9-.7 1.6-1.6 1.6','M6.9 8.1c2.3-.2 4.6-.1 6.9 0','M6.9 11.5h6.7','M6.8 14.3c2.3.1 4.5.1 6.8 0','M6.9 17.1h4.1'],
  // 5 포트폴리오: a pie with one slice lifted out
  portfolio:['M10.9 4.7c-4 .4-7 3.8-6.8 7.8.1 4.2 3.6 7.6 7.9 7.4 3.9-.1 7-3.2 7.3-7.1l-8.3.1z','M13.9 2.9c3.7.2 6.7 3.2 7.1 6.9l-7.1.1z'],
  // 6 프롬프트 라이브러리: a speech bubble and a pencil
  prompts:['M3.8 5.6c0-.9.7-1.7 1.7-1.7h10.8c.9 0 1.7.8 1.7 1.7v6.1c0 1-.8 1.7-1.7 1.7H9.4l-3.7 3.3.3-3.3h-.5c-.9 0-1.7-.7-1.7-1.7z','M7.3 7.6c2.3-.1 4.6-.1 6.9.1','M7.4 10.2h4.2','M14.5 20.8l.9-3.5 5-5.1c.6-.6 1.5-.6 2 0 .6.5.6 1.4 0 2l-5 5.1z','M15.4 17.3l2.4 2.4'],
  // 7 투자시스템 안내·구조: a folded map with a route
  system:['M3.4 6.5 8.8 4.2l6.3 2.4 5.5-2.2-.1 13.5-5.3 2.1-6.4-2.4-5.3 2.2z','M8.8 4.3l-.1 13.4','M15.1 6.7l.1 13.3','M5.5 14.3c.9-1.3 1.8-1.5 3.1-.9 1.4.7 2.6.3 3.4-.9.8-1.2 2-1.6 3.4-1'],
  // 8 Lab: a flask with liquid and two bubbles
  lab:['M9.3 3.4c1.8-.1 3.6-.1 5.4 0','M10.3 3.6l-.1 5.6-5 8.7c-.7 1.2.2 2.6 1.5 2.6h10.7c1.3 0 2.2-1.4 1.5-2.6l-5-8.7.1-5.6','M7.2 14.5c2.9-1 5.6.9 9.5-.2','M11.2 17.4h.1','M14.1 16.8h.1'],
  // 전체 메뉴: three drawn lines
  menu:['M4.3 7.2c5.2-.4 10.4-.3 15.5.1','M4.2 12.1c5.3.3 10.4.2 15.6-.2','M4.4 16.9c5.1-.3 10.3-.2 15.4.2']
 });
 const NAMES=Object.freeze(Object.keys(ICONS));
 const svg=(cls,box,body,extra)=>'<svg class="'+cls+'" viewBox="'+box+'"'+(extra||'')+' aria-hidden="true" focusable="false">'+body+'</svg>';
 const paths=(list,attr)=>list.map(d=>'<path d="'+d+'"'+(attr||'')+'/>').join('');
 function icon(name,cls){const d=ICONS[name];return d?svg('doodle'+(cls?' '+cls:''),'0 0 24 24',paths(d)):'';}
 // Long curved arrow pointing up (the head is at the top); CSS turns it toward each node.
 function arrow(cls){return svg('doodle-arrow'+(cls?' '+cls:''),'0 0 36 56',paths(['M17.6 53.4c-3.6-12.8-1.9-30.3 3.8-46.1','M14.2 14.4c2.2-2.6 4.5-5.4 7.2-8.2 1.6 3.1 3.6 6 5.7 8.7'],' pathLength="1"'));}
 // Short arrow pointing right, for the phone list.
 function arrowShort(cls){return svg('doodle-arrow'+(cls?' '+cls:''),'0 0 40 20',paths(['M2.4 12.6c8.4-5.5 19.6-7.1 31.7-3.4','M26.9 3.7c2.6 1.6 5 3.4 7.3 5.6-2.4 1.9-4.6 4-6.6 6.2'],' pathLength="1"'));}
 // Hand-drawn underline (stretches with its box; the stroke keeps its width).
 function underline(cls){return svg('doodle-line'+(cls?' '+cls:''),'0 0 120 12',paths(['M2.6 8.1c18.9-3.7 40.7-4.9 61.8-3.6 17.3 1.1 33.6 2.9 53.1 1.4'],' vector-effect="non-scaling-stroke"'),' preserveAspectRatio="none"');}
 // Hand-drawn ring that overshoots where it closes, as a pen would.
 function ring(cls){return svg('doodle-ring'+(cls?' '+cls:''),'0 0 400 100',paths(['M206 7.4C300 5.2 392 19.6 394.6 50.3c2.4 29.6-88.7 43.1-191.9 43.6C99.3 94.4 5.6 81.6 5.4 50.8 5.2 22.3 90.2 6.2 192.4 7.6c24.6.4 45.8 2.6 63.1 6.3'],' vector-effect="non-scaling-stroke"'),' preserveAspectRatio="none"');}
 // Menu: each primary link and the 전체 메뉴 button get their doodle and the (hidden until current) accent underline.
 const TAB_ICON=Object.freeze({home:'home',qgv:'qgv',technical:'technical',macro:'macro',news:'news',portfolio:'portfolio',prompts:'prompts',system:'system',lab:'lab'});
 function decorateNav(doc){
  const nav=doc&&doc.querySelector('#primary-nav');if(!nav)return;
  for(const a of nav.querySelectorAll('[data-nav-tab]')){
   if(a.querySelector('.doodle'))continue;const name=TAB_ICON[a.dataset.navTab];if(!name)continue;
   a.querySelector('.nav-icon')?.remove();a.insertAdjacentHTML('afterbegin',icon(name,'nav-icon'));a.insertAdjacentHTML('beforeend',underline('nav-mark'));
  }
  const more=nav.querySelector('#more-button');
  if(more&&!more.querySelector('.doodle')){more.querySelector('.nav-icon')?.remove();more.insertAdjacentHTML('afterbegin',icon('menu','nav-icon'));}
 }
 root.Doodles=Object.freeze({NAMES,TAB_ICON,icon,arrow,arrowShort,underline,ring,decorateNav});
 decorateNav(root.document);
})(window);
