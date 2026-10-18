/* App shell: header (brand, language, theme, settings), the eight top-level menus (PC header menu / phone bottom
   navigation), the full-menu sheet that lists every existing route, the theme card in Settings, and the short
   "준비 중" pages for menus that have no screen yet. Navigation and presentation only: no data is read, computed or
   stored here except the theme choice (theme-boot.js, this device only).
   Owner IA (2026-10-18): 1 QGV · 2 기술적 분석 · 3 매크로 · 4 뉴스·공시·기업 관계 · 5 포트폴리오 · 6 프롬프트 라이브러리 ·
   7 투자시스템 안내·구조 · 8 Lab. Every existing route belongs to exactly one menu (home to 홈, settings to none). */
(function(root){
 'use strict';
 const doc=root.document,$=s=>doc.querySelector(s);
 const T=(locale,ko,en)=>locale==='en-US'?en:ko;
 const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]);
 // n: menu number. short: label on phones and narrower PCs. items: the sheet's links (existing routes only, or a
 // "준비 중" page that says what is missing). pending: the item has no working screen yet.
 const MENUS=Object.freeze([
  {key:'qgv',n:1,href:'#leaderboard',ko:'QGV',en:'QGV',short:['QGV','QGV'],
   desc:['기업 순위·점수·기업 상세','Rankings, scores and company detail'],
   routes:['leaderboard','qgv','companies','watchlist','company','analysis','entity','types','profiles'],
   items:[['#leaderboard','리더보드 · 기업 연구','Leaderboard · company research'],['#companies','기업 목록','Company list'],['#watchlist','관심 기업','Watchlist'],['#profiles','전략 프로필','Strategy profile'],['#types','기업 유형 커스텀','Company types'],['#qgv','QGV 허브 · 기능 안내','QGV hub']]},
  {key:'technical',n:2,href:'#technical',ko:'기술적 분석',en:'Technical analysis',short:['기술적 분석','Technical'],
   desc:['가격 차트·지표','Price chart and indicators'],routes:['technical'],
   items:[['#technical','기술적 분석','Technical analysis']]},
  {key:'macro',n:3,href:'#macro',ko:'매크로',en:'Macro',short:['매크로','Macro'],
   desc:['거시 8축·경고등','Eight macro axes and lights'],routes:['macro'],
   items:[['#macro','매크로','Macro']]},
  {key:'news',n:4,href:'#news',ko:'뉴스·공시·기업 관계',en:'News, filings & relations',short:['뉴스·공시','News'],
   desc:['공시·뉴스와 기업 관계망','Filings, news and the company network'],routes:['news'],
   items:[['#news','뉴스·공시 · 기업 관계망','News & filings · company network']]},
  {key:'portfolio',n:5,href:'#portfolio',ko:'포트폴리오',en:'Portfolio',short:['포트폴리오','Portfolio'],
   desc:['보유·모델·플레이북·일일보고','Holdings, model, playbook, daily reports'],routes:['portfolio','actual','model','playbook','brief','report'],
   items:[['#portfolio','포트폴리오','Portfolio'],['#actual','실제 보유 입력','Actual holdings'],['#model','모델 포트폴리오','Model portfolio'],['#playbook','플레이북','Playbook'],['#brief','오늘의 투자 화면','Today’s investment view'],['#report/real','투자 일일보고서','Investment daily report'],['#report/mock','모의투자 일일보고서','Paper trading daily report']]},
  {key:'prompts',n:6,href:'#research',ko:'프롬프트 라이브러리',en:'Prompt library',short:['프롬프트','Prompts'],
   desc:['공식 프롬프트 카탈로그','Official prompt catalogue'],routes:['research'],
   items:[['#research','프롬프트 라이브러리','Prompt library']]},
  {key:'system',n:7,href:'#system',ko:'투자시스템 안내·구조',en:'System guide & structure',short:['시스템 안내','System'],
   desc:['데이터에서 판단까지의 구조','How data becomes a judgement'],routes:['system'],
   items:[['#system','투자시스템 안내·구조','System guide & structure',true]]},
  {key:'lab',n:8,href:'#validation',ko:'Lab',en:'Lab',short:['Lab','Lab'],
   desc:['백테스트·전진검증·13F 가중치 연구','Backtests, forward validation, 13F weight research'],routes:['validation','lab-13f','thirteenf'],
   items:[['#validation','검증·연구 개요','Validation overview'],['#validation-backtest','백테스트','Backtest'],['#validation-forward','전진 검증','Forward validation'],['#thirteenf','투자자 13F 보유','Investor 13F holdings'],['#lab-13f','13F 가중치 연구','13F weight research',true]]}
 ]);
 const HOME=Object.freeze({key:'home',n:0,href:'#home',ko:'홈',en:'Home',short:['홈','Home'],routes:['home']});
 const TABS=Object.freeze([HOME,...MENUS]);
 const SETTINGS=Object.freeze({ko:'설정',en:'Settings',items:[['#settings','설정','Settings']]});
 // Kept for callers of the previous shape: every sheet group with its links.
 const MORE=Object.freeze([...MENUS.map(m=>({ko:m.ko,en:m.en,items:m.items})),SETTINGS]);
 const THEME_LABEL={light:['라이트','Light'],dark:['다크','Dark'],system:['시스템 설정','System']};
 let locale='ko-KR',route=null;
 // An entity page belongs to the menu of its kind (feature map 2026-10-18 §8): macro indicator → 매크로, investor → Lab
 // (13F research), industry and others → QGV. The kind is read from the current hash ('#entity/MACRO:...').
 const ENTITY_MENU=Object.freeze({MACRO:'macro',INVESTOR:'lab'});
 function entityMenu(){let id='';try{id=decodeURIComponent(root.location.hash.split('/')[1]||'');}catch(_){id='';}return ENTITY_MENU[id.split(':')[0]]||'qgv';}
 const tabFor=r=>r==='entity'?TABS.find(t=>t.key===entityMenu()):TABS.find(t=>t.routes.includes(r))||null;
 const pad=n=>String(n).padStart(2,'0');
 // Route → menu (number and label) for the screen's "01 / QGV" line; null for home and settings.
 function menuFor(r){const m=r==='entity'?MENUS.find(x=>x.key===entityMenu()):MENUS.find(x=>x.routes.includes(r));return m?{key:m.key,n:m.n,num:pad(m.n),label:T(locale,m.ko,m.en)}:null;}

 function label(){
  const nav=$('#primary-nav');if(!nav)return;
  nav.setAttribute('aria-label',T(locale,'주요 메뉴','Main menu'));
  for(const t of TABS){const a=nav.querySelector('[data-nav-tab="'+t.key+'"]');if(!a)continue;
   const long=a.querySelector('.nav-long'),short=a.querySelector('.nav-short');
   if(long)long.textContent=T(locale,t.ko,t.en);if(short)short.textContent=T(locale,t.short[0],t.short[1]);}
  const more=$('#more-button');if(more){const txt=T(locale,'전체 메뉴','All menus');more.querySelector('.nav-long').textContent=txt;more.querySelector('.nav-short').textContent=T(locale,'전체 메뉴','Menu');}
  const brand=$('header .brand');if(brand)brand.setAttribute('aria-label',T(locale,'QGV 투자 시스템 홈','QGV Investment System home'));
  const lang=$('#lang-toggle');if(lang){lang.querySelector('[data-lang-code]').textContent=locale==='en-US'?'EN':'KR';
   lang.setAttribute('aria-label',T(locale,'표시 언어: 한국어. English로 바꾸기','Display language: English. Switch to 한국어'));}
  paintThemeButton();
  if(!$('#more-menu')?.hidden)paintMore();
 }
 function paintThemeButton(){
  const b=$('#theme-button');if(!b||!root.AppTheme)return;const c=AppTheme.choice(),r=AppTheme.resolved();
  b.dataset.themeIcon=c==='system'?'system':r;
  b.setAttribute('aria-label',T(locale,'화면 테마: ','Theme: ')+T(locale,...THEME_LABEL[c]));
  for(const x of doc.querySelectorAll('[data-theme-choice]'))x.setAttribute('aria-checked',String(x.dataset.themeChoice===c));
  const menu=$('#theme-menu');if(menu){menu.setAttribute('aria-label',T(locale,'화면 테마','Theme'));for(const x of menu.querySelectorAll('[data-theme-choice]'))x.querySelector('span').textContent=T(locale,...THEME_LABEL[x.dataset.themeChoice]);}
  for(const x of doc.querySelectorAll('input[name="theme-choice"]'))x.checked=x.value===c;
 }
 function sync(r,loc){
  locale=loc||locale;route=r;doc.documentElement.dataset.route=r||'';
  const tab=tabFor(r);
  for(const a of doc.querySelectorAll('#primary-nav [data-nav-tab]')){if(tab&&a.dataset.navTab===tab.key)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');}
  const settings=$('.tool-settings');if(settings){if(r==='settings')settings.setAttribute('aria-current','page');else settings.removeAttribute('aria-current');}
  label();closeMore(false);closeTheme(false);
 }
 // ---------- full-menu sheet ----------
 // Each menu group carries its hand-drawn doodle (doodles.js; decoration only, aria-hidden).
 const doodle=key=>root.Doodles?Doodles.icon(Doodles.TAB_ICON[key],'more-icon'):'';
 function paintMore(){
  const host=$('#more-menu');if(!host)return;const here='#'+(root.location.hash.slice(1)||'home');
  host.setAttribute('aria-label',T(locale,'전체 메뉴','All menus'));host.setAttribute('aria-modal','true');
  const pendingTag='<span class="more-pending">'+esc(T(locale,'준비 중','Pending'))+'</span>';
  const link=([href,ko,en,pending])=>'<li><a href="'+href+'"'+(here===href?' aria-current="page"':'')+(pending?' data-menu-pending':'')+'>'+esc(T(locale,ko,en))+(pending?' '+pendingTag:'')+'</a></li>';
  host.innerHTML='<div class="more-head"><h2 id="more-title">'+esc(T(locale,'전체 메뉴','All menus'))+'</h2><button type="button" class="tool" data-more-close aria-label="'+esc(T(locale,'메뉴 닫기','Close menu'))+'"><span aria-hidden="true">×</span></button></div>'+
   '<div class="more-groups">'+MENUS.map(m=>'<section data-menu-group="'+m.key+'"><h3>'+doodle(m.key)+'<span class="more-num" aria-hidden="true">'+pad(m.n)+'</span>'+esc(T(locale,m.ko,m.en))+'</h3><p class="more-desc">'+esc(T(locale,...m.desc))+'</p><ul>'+m.items.map(link).join('')+'</ul></section>').join('')+
   '<section data-menu-group="settings"><h3><span class="more-num" aria-hidden="true">—</span>'+esc(T(locale,SETTINGS.ko,SETTINGS.en))+'</h3><ul>'+SETTINGS.items.map(link).join('')+'</ul></section></div>'+
   '<p class="more-note">'+esc(T(locale,'PERSONAL / READ ONLY · 보유 정보는 이 기기에만 저장됩니다.','PERSONAL / READ ONLY · Holdings stay on this device.'))+'</p>';
 }
 function openMore(){const host=$('#more-menu'),b=$('#more-button');if(!host||!b)return;closeTheme(false);paintMore();host.hidden=false;b.setAttribute('aria-expanded','true');doc.documentElement.dataset.more='open';
  const first=host.querySelector('[aria-current="page"]')||host.querySelector('a,button');if(first)first.focus({preventScroll:true});}
 function closeMore(refocus=true){const host=$('#more-menu'),b=$('#more-button');if(!host||host.hidden)return;host.hidden=true;host.replaceChildren();b?.setAttribute('aria-expanded','false');delete doc.documentElement.dataset.more;if(refocus&&b)b.focus({preventScroll:true});}
 // ---------- theme menu ----------
 function openTheme(){const m=$('#theme-menu'),b=$('#theme-button');if(!m||!b)return;closeMore(false);paintThemeButton();m.hidden=false;b.setAttribute('aria-expanded','true');(m.querySelector('[aria-checked="true"]')||m.querySelector('button'))?.focus({preventScroll:true});}
 function closeTheme(refocus=true){const m=$('#theme-menu'),b=$('#theme-button');if(!m||m.hidden)return;m.hidden=true;b?.setAttribute('aria-expanded','false');if(refocus&&b)b.focus({preventScroll:true});}
 function chooseTheme(c){if(!root.AppTheme)return;const stored=AppTheme.set(c);paintThemeButton();
  const n=$('#notice');if(n&&!stored)n.textContent=T(locale,'테마를 이 기기에 저장할 수 없습니다. 이번 방문에만 적용됩니다.','The theme could not be saved on this device; it applies to this visit only.');}
 // ---------- Settings: theme card (inserted after the language card) ----------
 function mountSettings(){
  const content=$('#content');if(!content||$('#theme-settings'))return;const anchor=$('#display-locale')?.closest('.card');if(!anchor)return;
  const c=root.AppTheme?AppTheme.choice():'system';
  anchor.insertAdjacentHTML('afterend','<section class="card" id="theme-settings" data-theme-settings><h2>'+esc(T(locale,'화면 테마','Theme'))+'</h2><div class="theme-options" role="radiogroup" aria-label="'+esc(T(locale,'화면 테마','Theme'))+'">'+
   ['light','dark','system'].map(v=>'<label class="theme-option"><input type="radio" name="theme-choice" value="'+v+'"'+(v===c?' checked':'')+'> '+esc(T(locale,...THEME_LABEL[v]))+'</label>').join('')+
   '</div><p class="small">'+esc(T(locale,'이 기기에만 저장됩니다. 시스템 설정은 기기의 라이트·다크 설정을 따릅니다. 위치·시간 정보는 쓰지 않습니다.','Saved on this device only. System follows the device light/dark setting. No location or time is used.'))+'</p></section>');
 }
 function afterRender(r){if(r==='settings')mountSettings();}
 // ---------- "준비 중" pages: menus without a screen say what is missing and where the closest existing screen is ----------
 // Statements only; no number, chart or sample value. Sources: owner directive 2026-10-18 §5, §11.
 const PENDING=Object.freeze({
  system:{eyebrow:'SYSTEM GUIDE',ko:'투자시스템 안내·구조',en:'System guide & structure',
   what:['데이터 → 지표 → 판단 → 비교 → 시나리오·기록의 흐름을 한 장의 구조도로 보여 줄 화면입니다. QGV는 축 → 요인 → 원지표·비중·비교군까지, 기술·매크로·뉴스·포트폴리오는 입력·규칙·출력·검증까지 내려가게 됩니다.',
         'One map of how data becomes indicators, judgements, comparisons and records. QGV goes down to axis → factor → raw metric, weight and peer group; technical, macro, news and portfolio go down to input, rule, output and check.'],
   need:[['영역별 입력·규칙·출력·검증 정리 (기능 대응표, 통합 작업에서 작성 중)','Per-area inputs, rules, outputs and checks (feature map, in progress in the integration work)'],
         ['기업·증권·공시·뉴스 사건·관계·점수·프로필·포트폴리오 사이의 실제 식별자 연결표','The real identifier links between companies, securities, filings, news events, relations, scores, profiles and portfolios'],
         ['예시 값 표시 규칙: 실제 자료는 출처·시점, 합성 예시는 계속 보이는 예시 표시','How examples are shown: real data with source and time, synthetic examples with a permanent example label']],
   links:[['#qgv','QGV 허브 · 기능별 사용 가능 상태','QGV hub · availability by feature'],['#brief','오늘의 투자 화면 · 시스템 흐름 카드','Today’s view · system flow card'],['#settings','설정 · 운영 상태','Settings · operations status']]},
  'lab-13f':{eyebrow:'LAB · 13F WEIGHT RESEARCH',ko:'13F 가중치 연구',en:'13F weight research',
   what:['과거 13F 보유와 비슷한 기업을 고르게 만드는 Q/G/V 축 가중치와 Q1~Q5·G1~G5·V1~V5 세부 요인 가중치를 탐색하고, 다른 기간의 유사도와 투자 성과로 검증하는 연구 화면입니다. 기관 관심도 슬라이더가 아니며, 기존 주검정과 별도의 실험으로 등록합니다.',
         'A research screen that searches Q/G/V axis weights and Q1–Q5, G1–G5, V1–V5 factor weights that make the selection resemble past 13F holdings, then checks similarity and investment results in other periods. It is not an institutional-interest slider and is registered apart from the main test.'],
   need:[['과거 Track C·Investor-QGV 연구 자산의 재사용 범위 확인','How much of the earlier Track C / Investor-QGV research can be reused'],
         ['분기별 13F 보유 이력(공개 시점 기준)과 증권 식별 연결','Quarterly 13F holdings history as of filing time, linked to security identifiers'],
         ['같은 시점의 요인 점수 이력','Factor score history at the same points in time'],
         ['학습·검증 기간, 평가 지표, 별도 실험 ID·버전 결정','Training and test periods, metrics, and a separate experiment ID and version']],
   links:[['#thirteenf','투자자 13F 보유 공시','Investor 13F filings'],['#validation','검증·연구 개요','Validation overview']]}
 });
 function pendingHtml(key,loc){
  const l=loc||locale,p=PENDING[key];if(!p)return '';const t=(ko,en)=>T(l,ko,en);
  return '<section class="pending-page" data-pending-page="'+esc(key)+'" aria-labelledby="pending-title">'+
   '<p class="eyebrow">'+esc(p.eyebrow)+'</p><h1 id="pending-title">'+esc(t(p.ko,p.en))+'</h1>'+
   '<p class="pending-state"><span class="badge" data-feature-status="준비 중">'+esc(t('준비 중','Pending'))+'</span><span class="badge NOT_AVAILABLE">NOT_AVAILABLE</span><span class="small">'+esc(t('아직 화면이 없습니다. 예시 숫자나 결과를 넣지 않습니다.','No screen yet. No example numbers or results are shown.'))+'</span></p>'+
   '<p>'+esc(t(...p.what))+'</p>'+
   '<h2>'+esc(t('필요한 자료·결정','Data and decisions needed'))+'</h2><ol data-pending-needs>'+p.need.map(x=>'<li>'+esc(t(...x))+'</li>').join('')+'</ol>'+
   '<h2>'+esc(t('지금 볼 수 있는 곳','Where to look now'))+'</h2><ul class="pending-links">'+p.links.map(([href,ko,en])=>'<li><a href="'+href+'">'+esc(t(ko,en))+' <span aria-hidden="true">→</span></a></li>').join('')+'</ul></section>';
 }
 // ---------- phone keyboard: the bottom navigation never covers a focused field or its results ----------
 const typingField=el=>!!el&&(el.isContentEditable||el.tagName==='TEXTAREA'||el.tagName==='SELECT'||(el.tagName==='INPUT'&&!['checkbox','radio','button','submit','reset','range','color','file','image'].includes(el.type)));
 // The navigation comes back a moment after the field is left, so a tap that ends the typing (e.g. on a button that was
 // just above the keyboard) is not caught by the bar reappearing under the finger.
 let typingTimer=0;
 function syncTyping(){const vv=root.visualViewport,kb=!!vv&&vv.height<root.innerHeight*0.78;const on=typingField(doc.activeElement)||kb;
  if(vv)doc.documentElement.style.setProperty('--vv-height',Math.round(vv.height)+'px');
  root.clearTimeout(typingTimer);
  if(on)doc.documentElement.dataset.typing='1';
  else if(doc.documentElement.dataset.typing)typingTimer=root.setTimeout(()=>{if(!typingField(doc.activeElement))delete doc.documentElement.dataset.typing;},450);}
 doc.addEventListener('focusin',syncTyping);doc.addEventListener('focusout',()=>setTimeout(syncTyping,0));
 if(root.visualViewport){root.visualViewport.addEventListener('resize',syncTyping);}

 doc.addEventListener('click',e=>{
  const t=e.target;
  if(t.closest('#more-button')){e.preventDefault();if($('#more-menu')?.hidden)openMore();else closeMore();return;}
  if(t.closest('[data-more-close]')){closeMore();return;}
  if(t.closest('#more-menu a')){closeMore(false);return;}
  if(t.closest('#theme-button')){if($('#theme-menu')?.hidden)openTheme();else closeTheme();return;}
  const choice=t.closest('#theme-menu [data-theme-choice]');if(choice){chooseTheme(choice.dataset.themeChoice);closeTheme();return;}
  if(t.closest('#lang-toggle')){const next=locale==='en-US'?'ko-KR':'en-US';if(typeof root.updateSettings==='function')root.updateSettings({display_locale:next});return;}
  if(!t.closest('#more-menu'))closeMore(false);
  if(!t.closest('.theme-control'))closeTheme(false);
 });
 doc.addEventListener('change',e=>{if(e.target.name==='theme-choice')chooseTheme(e.target.value);});
 doc.addEventListener('keydown',e=>{
  if(e.key!=='Escape')return;
  if(!$('#more-menu')?.hidden){e.preventDefault();closeMore();}
  else if(!$('#theme-menu')?.hidden){e.preventDefault();closeTheme();}
 });
 // Tab stays inside the open full-menu sheet (it covers the page); Escape or × closes it.
 doc.addEventListener('keydown',e=>{const host=$('#more-menu');if(e.key!=='Tab'||!host||host.hidden)return;
  const items=[...host.querySelectorAll('a[href],button:not([disabled])')];if(!items.length)return;
  const first=items[0],last=items[items.length-1],a=doc.activeElement;
  if(!host.contains(a)){e.preventDefault();(e.shiftKey?last:first).focus();}
  else if(e.shiftKey&&a===first){e.preventDefault();last.focus();}
  else if(!e.shiftKey&&a===last){e.preventDefault();first.focus();}});
 // Arrow keys inside the theme menu.
 doc.addEventListener('keydown',e=>{const m=$('#theme-menu');if(!m||m.hidden||!m.contains(doc.activeElement)||!['ArrowDown','ArrowUp'].includes(e.key))return;e.preventDefault();
  const items=[...m.querySelectorAll('[data-theme-choice]')],i=items.indexOf(doc.activeElement);items[(i+(e.key==='ArrowDown'?1:items.length-1))%items.length].focus();});
 if(root.AppTheme)AppTheme.subscribe(()=>paintThemeButton());
 root.AppShell=Object.freeze({MENUS,TABS,MORE,PENDING,sync,afterRender,tabFor,menuFor,pendingHtml,openMore,closeMore});
})(window);
