/* App shell: header (brand, language, theme, settings), the owner menus (PC numbered header menu / phone bottom tab bar),
   the full-menu sheet drawn as the n 구조 트리, the numbered sub-menu strip of each menu, the theme and chart-colour cards
   in Settings, and the short "준비 중" page for 13F weight research. Navigation and presentation only: no data is read,
   computed or stored here except the theme and candle-colour choices (theme-boot.js, this device only).
   Owner IA (2026-10-18, PRODUCT_IA_DIRECTIVE_20261018): 0 홈(기업 검색) · 1 QGV · 2 기술적 분석 · 3 매크로 · 4 뉴스 ·
   5 포트폴리오 · 6 프롬프트 라이브러리 · n 구조 트리 · n+1 Lab. Every existing route belongs to exactly one menu
   (settings to none). 13F (#thirteenf, #lab-13f) moved from Lab to QGV 1.3 (ontology check IA-2). */
(function(root){
 'use strict';
 const doc=root.document,$=s=>doc.querySelector(s);
 const T=(locale,ko,en)=>locale==='en-US'?en:ko;
 const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]);
 // n: order; num: the owner's menu number as shown (0, 1–6, n, n+1). short: label on phones and narrower PCs.
 // items: the sheet's leaves [href, section number, ko, en, pending]; pending = the screen states NOT_AVAILABLE only.
 // subs: the numbered strip on the menu's screens [section, href, ko, en, raw hash keys that count as "here"].
 const MENUS=Object.freeze([
  {key:'qgv',n:1,num:'1',href:'#leaderboard',ko:'QGV',en:'QGV',short:['QGV','QGV'],
   desc:['리더보드 · 가중치 · 13F 가중치 · 구조','Leaderboard · weights · 13F weights · structure'],
   routes:['leaderboard','qgv','companies','watchlist','company','analysis','entity','types','profiles','thirteenf','lab-13f'],
   items:[['#leaderboard','1.1','리더보드','Leaderboard'],['#companies','1.1','기업 목록','Company list'],['#watchlist','1.1','관심 기업','Watchlist'],
    ['#profiles','1.2','가중치 · 사용자 설정','Weights · user settings'],['#types','1.2','기업 유형 커스텀','Company types'],
    ['#lab-13f','1.3','13F 가중치 연구','13F weight research',true],['#thirteenf','1.3','투자자 13F 보유','Investor 13F holdings'],
    ['#tree/qgv','1.4','QGV 구조 트리','QGV structure tree'],['#qgv','1','QGV 허브 · 기능 안내','QGV hub']],
   subs:[['1.1','#leaderboard','리더보드','Leaderboard',['leaderboard','companies','watchlist','company','analysis','entity','qgv']],['1.2','#profiles','가중치 · 사용자 설정','Weights · settings',['profiles','types']],
    ['1.3','#lab-13f','13F 가중치','13F weights',['lab-13f','thirteenf']],['1.4','#tree/qgv','구조 트리','Structure tree',['tree/qgv']]]},
  {key:'technical',n:2,num:'2',href:'#technical',ko:'기술적 분석',en:'Technical analysis',short:['기술적 분석','Technical'],
   desc:['지표 · 패턴 · 내 노트 · 구조','Indicators · patterns · my notes · structure'],routes:['technical'],
   items:[['#technical','2.1','지표 · 정도 · 시나리오','Indicators · degree · scenarios'],['#technical-pattern','2.2','차트 패턴','Chart patterns'],
    ['#technical-notes','2.3','차트 위 내 노트','My notes on the chart'],['#tree/technical','2.4','기술적 분석 구조 트리','Technical structure tree']],
   subs:[['2.1','#technical','지표 · 시나리오','Indicators',['technical','technical-chart','technical-state','technical-execution','technical-record']],['2.2','#technical-pattern','차트 패턴','Patterns',['technical-pattern']],
    ['2.3','#technical-notes','내 노트','My notes',['technical-notes']],['2.4','#tree/technical','구조 트리','Structure tree',['tree/technical']]]},
  {key:'macro',n:3,num:'3',href:'#macro',ko:'매크로',en:'Macro',short:['매크로','Macro'],
   desc:['경고등 · 위치 · 순환매 · 나비효과 · 구조','Lights · position · rotation · butterfly effect · structure'],routes:['macro'],
   items:[['#macro','3','매크로 상태판 · 경고등','Macro board · lights'],['#macro-cycle','3.1','경기 · 시장 위치','Economy · market position'],
    ['#macro-rotation','3.2','순환매 위치','Sector rotation',true],['#macro-industry','3.3','산업 사이클 (SIC)','Industry cycles (SIC)'],
    ['#macro-mine','3.4','내가 고른 위치','My chosen position'],['#macro-chain','3.5','나비효과','Butterfly effect',true],
    ['#tree/macro','3.6','매크로 구조 트리','Macro structure tree']],
   subs:[['3.1','#macro-cycle','위치','Position',['macro','macro-cycle']],['3.2','#macro-rotation','순환매','Rotation',['macro-rotation']],['3.3','#macro-industry','산업 사이클','Industry',['macro-industry']],
    ['3.4','#macro-mine','내 위치','Mine',['macro-mine']],['3.5','#macro-chain','나비효과','Butterfly effect',['macro-chain']],['3.6','#tree/macro','구조 트리','Structure tree',['tree/macro']]]},
  {key:'news',n:4,num:'4',href:'#news',ko:'뉴스',en:'News',short:['뉴스','News'],
   desc:['관계망 · 공시 · 뉴스 · 구조','Network · filings · news · structure'],routes:['news'],
   items:[['#news-network','4.1','관계망','Company network'],['#news','4.2','공시 · 뉴스','Filings · news'],['#tree/news','4.3','뉴스 구조 트리','News structure tree']],
   subs:[['4.1','#news-network','관계망','Network',['news-network']],['4.2','#news','공시 · 뉴스','Filings · news',['news']],['4.3','#tree/news','구조 트리','Structure tree',['tree/news']]]},
  {key:'portfolio',n:5,num:'5',href:'#portfolio',ko:'포트폴리오',en:'Portfolio',short:['포트폴리오','Portfolio'],
   desc:['모델 · 내 것 · 모의 · 일일 보고 · 구조','Model · mine · paper · daily reports · structure'],routes:['portfolio','actual','model','playbook','brief','report'],
   items:[['#portfolio','5.1','모델 · 내 것 · 모의','Model · mine · paper'],['#model','5.1','모델 포트폴리오','Model portfolio'],['#actual','5.1','실제 보유 입력','Actual holdings'],
    ['#report/real','5.2','투자 일일보고서 · 보고 불가 → 프롬프트','Daily report · prompt when it cannot be made'],['#report/mock','5.3','모의투자 일일보고서','Paper trading daily report'],
    ['#playbook','5','플레이북','Playbook'],['#brief','5','오늘의 투자 화면','Today’s investment view'],['#tree/portfolio','5.4','포트폴리오 구조 트리','Portfolio structure tree']],
   subs:[['5.1','#portfolio','모델 · 내 것 · 모의','Model · mine · paper',['portfolio','model','actual','playbook','brief']],['5.2','#report/real','일일 보고','Daily report',['report/real']],
    ['5.3','#report/mock','모의 일일 보고','Paper daily report',['report/mock','report/mock-set_b','report/mock-set_c','report/mock-set_d','report/mock-compare']],['5.4','#tree/portfolio','구조 트리','Structure tree',['tree/portfolio']]]},
  {key:'prompts',n:6,num:'6',href:'#research',ko:'프롬프트 라이브러리',en:'Prompt library',short:['프롬프트','Prompts'],
   desc:['공식 카탈로그 · ★ · 내 사본','Official catalogue · ★ · personal copies'],routes:['research'],
   items:[['#research','6','프롬프트 라이브러리 · 내 사본','Prompt library · personal copies']],subs:[]},
  {key:'system',n:7,num:'n',href:'#system',ko:'구조 트리',en:'Structure tree',short:['구조 트리','Tree'],
   desc:['투자시스템 한 장 지도','The whole system on one page'],routes:['system'],
   items:[['#system','n','투자시스템 구조 트리','Whole-system tree']],subs:[]},
  {key:'lab',n:8,num:'n+1',href:'#validation',ko:'Lab',en:'Lab',short:['Lab','Lab'],
   desc:['백테스트 · 전진 검증','Backtests · forward validation'],routes:['validation'],
   items:[['#validation','n+1','검증·연구 개요','Validation overview'],['#validation-backtest','n+1.1','백테스트','Backtest'],['#validation-forward','n+1.2','전진 검증','Forward validation']],
   subs:[['n+1.1','#validation-backtest','백테스트','Backtest',['validation-backtest']],['n+1.2','#validation-forward','전진 검증','Forward validation',['validation-forward']]]}
 ]);
 // Per-menu structure trees live at #tree/<menu key> (1.4, 2.4, 3.6, 4.3, 5.4); n is #system.
 const TREE_KEYS=Object.freeze(['qgv','technical','macro','news','portfolio']);
 const HOME=Object.freeze({key:'home',n:0,num:'0',href:'#home',ko:'홈',en:'Home',short:['홈','Home'],routes:['home']});
 const TABS=Object.freeze([HOME,...MENUS]);
 const SETTINGS=Object.freeze({ko:'설정',en:'Settings',items:[['#settings','—','설정','Settings']]});
 // Kept for callers of the previous shape: every sheet group with its links ([href, ko, en, pending]).
 const MORE=Object.freeze([...MENUS.map(m=>({ko:m.ko,en:m.en,items:m.items.map(([h,,ko,en,p])=>[h,ko,en,!!p])})),{ko:SETTINGS.ko,en:SETTINGS.en,items:[['#settings','설정','Settings']]}]);
 const THEME_LABEL={light:['라이트','Light'],dark:['다크 · 칠판','Dark · chalkboard'],system:['시스템 설정','System']};
 const CANDLE_LABEL={kr:['한국식 · 상승 빨강 / 하락 파랑','Korean · up red / down blue'],us:['미국식 · 상승 초록 / 하락 빨강','US · up green / down red']};
 let locale='ko-KR',route=null;
 // An entity page belongs to the menu of its kind: macro indicator → 매크로; industry, investor (13F, now QGV 1.3) and
 // others → QGV. A structure tree belongs to its menu. Both read the current hash ('#entity/MACRO:...', '#tree/qgv').
 const ENTITY_MENU=Object.freeze({MACRO:'macro'});
 function hashPart(i){try{return decodeURIComponent(root.location.hash.slice(1).split('/')[i]||'');}catch(_){return '';}}
 function entityMenu(){return ENTITY_MENU[hashPart(1).split(':')[0]]||'qgv';}
 function treeMenu(){const k=hashPart(1);return TREE_KEYS.includes(k)?k:'qgv';}
 const menuKeyFor=r=>r==='entity'?entityMenu():r==='tree'?treeMenu():(MENUS.find(m=>m.routes.includes(r))||{}).key||null;
 const tabFor=r=>r==='home'?HOME:MENUS.find(m=>m.key===menuKeyFor(r))||null;
 const pad=n=>String(n).padStart(2,'0');
 // Route → menu (number and label) for the screen's "1 / QGV" line; null for home and settings.
 function menuFor(r){const m=MENUS.find(x=>x.key===menuKeyFor(r));return m?{key:m.key,n:m.n,num:m.num,label:T(locale,m.ko,m.en)}:null;}
 // Numbered sub-menu strip (stamp boxes) for the current menu. "Here" is shown by a mark and hidden text, not aria-current,
 // so each route keeps exactly one aria-current (the primary menu).
 function rawKey(){const h=root.location.hash.slice(1).split('/');return h[0]==='tree'||h[0]==='report'?h[0]+'/'+(h[1]||''):h[0];}
 function contextHref(href){const [r,id]=root.location.hash.slice(1).split('/');
  if(/^technical(?:-|$)/.test(r)&&id&&/^#technical(?:-[a-z]+)?$/.test(href)){try{return href+'/'+encodeURIComponent(decodeURIComponent(id));}catch(_){}}
  return href;}
 function subNavHtml(r){
  const m=MENUS.find(x=>x.key===menuKeyFor(r));if(!m||!m.subs.length)return '';const key=rawKey();
  return '<nav class="ia-sub" data-ia-sub="'+m.key+'" aria-label="'+esc(T(locale,m.ko+' 세부 메뉴',m.en+' sections'))+'"><ol>'+m.subs.map(([sec,href,ko,en,keys])=>{const here=keys.includes(key);
   return '<li><a href="'+esc(contextHref(href))+'" data-ia-sec="'+esc(sec)+'"'+(here?' data-here="1"':'')+'><span class="ia-sec">'+esc(sec)+'</span><span class="ia-sub-label">'+esc(T(locale,ko,en))+'</span>'+(here?'<span class="sr-only"> '+esc(T(locale,'(지금 화면)','(this screen)'))+'</span>':'')+'</a></li>';}).join('')+'</ol></nav>';
 }
 function label(){
  const nav=$('#primary-nav');if(!nav)return;
  nav.setAttribute('aria-label',T(locale,'주요 메뉴','Main menu'));
  for(const t of TABS){const a=nav.querySelector('[data-nav-tab="'+t.key+'"]');if(!a)continue;
   const long=a.querySelector('.nav-long'),short=a.querySelector('.nav-short');
   if(long)long.textContent=T(locale,t.ko,t.en);if(short)short.textContent=T(locale,t.short[0],t.short[1]);
   const num=a.querySelector('.nav-num');if(num)num.textContent=t.num;}
  const more=$('#more-button');if(more){more.querySelector('.nav-long').textContent=T(locale,'전체 메뉴','All menus');more.querySelector('.nav-short').textContent=T(locale,'전체','Menu');}
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
  const k=AppTheme.candles?AppTheme.candles():'kr';for(const x of doc.querySelectorAll('input[name="candle-choice"]'))x.checked=x.value===k;
 }
 function sync(r,loc){
  locale=loc||locale;route=r;doc.documentElement.dataset.route=r||'';
  const tab=tabFor(r);doc.documentElement.dataset.menu=tab?tab.key:'';
  for(const a of doc.querySelectorAll('#primary-nav [data-nav-tab]')){if(tab&&a.dataset.navTab===tab.key)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');}
  const settings=$('.tool-settings');if(settings){if(r==='settings')settings.setAttribute('aria-current','page');else settings.removeAttribute('aria-current');}
  label();closeMore(false);closeTheme(false);
 }
 // ---------- full-menu sheet ----------
 // The sheet is the n 구조 트리 on one page: sources, then each menu as a coloured branch with numbered leaves.
 const doodle=key=>root.Doodles?Doodles.icon(Doodles.TAB_ICON[key],'more-icon'):'';
 function paintMore(){
  const host=$('#more-menu');if(!host)return;const here='#'+(root.location.hash.slice(1)||'home');
  host.setAttribute('aria-label',T(locale,'전체 메뉴','All menus'));host.setAttribute('aria-modal','true');
  const pendingTag='<span class="more-pending">'+esc(T(locale,'준비 중','Pending'))+'</span>';
  const link=([href,sec,ko,en,pending])=>'<li><a href="'+esc(contextHref(href))+'"'+(here===contextHref(href)?' aria-current="page"':'')+(pending?' data-menu-pending':'')+'><span class="more-sec" aria-hidden="true">'+esc(sec)+'</span><span class="more-label">'+esc(T(locale,ko,en))+'</span>'+(pending?' '+pendingTag:'')+'</a></li>';
  host.innerHTML='<div class="more-head"><h2 id="more-title">'+esc(T(locale,'전체 메뉴','All menus'))+'</h2><button type="button" class="tool" data-more-close aria-label="'+esc(T(locale,'메뉴 닫기','Close menu'))+'"><span aria-hidden="true">×</span></button></div>'+
   '<p class="more-lede">'+esc(T(locale,'= 투자시스템 한 장 지도 (n 구조 트리)','= the whole system on one page (n structure tree)'))+'</p>'+
   '<p class="more-sources">'+esc(T(locale,'재료: SEC 공시 · DART · 시세(이 기기) · 경제지표 · 뉴스 · 내 정보(비공개)','Inputs: SEC filings · DART · prices (this device) · economic data · news · my data (private)'))+'</p>'+
   '<div class="more-groups">'+MENUS.map(m=>'<section data-menu-group="'+m.key+'"><h3>'+doodle(m.key)+'<span class="more-num" aria-hidden="true">'+esc(m.num)+'</span>'+esc(T(locale,m.ko,m.en))+'</h3><p class="more-desc">'+esc(T(locale,...m.desc))+'</p><ul>'+m.items.map(link).join('')+'</ul></section>').join('')+
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
   '</div><p class="small">'+esc(T(locale,'이 기기에만 저장됩니다. 시스템 설정은 기기의 라이트·다크 설정을 따릅니다. 위치·시간 정보는 쓰지 않습니다.','Saved on this device only. System follows the device light/dark setting. No location or time is used.'))+'</p></section>'+
   // Chart colour convention: candles, return numbers and scenario lines (theme.css --up / --down). Device preference only.
   '<section class="card" id="candle-settings" data-candle-settings><h2>'+esc(T(locale,'차트 색 관례','Chart colour convention'))+'</h2><div class="theme-options" role="radiogroup" aria-label="'+esc(T(locale,'차트 색 관례','Chart colour convention'))+'">'+
   ['kr','us'].map(v=>'<label class="theme-option"><input type="radio" name="candle-choice" value="'+v+'"'+(v===(root.AppTheme&&AppTheme.candles?AppTheme.candles():'kr')?' checked':'')+'> <span class="candle-swatch" data-candle-swatch="'+v+'" aria-hidden="true"><i class="sw-up"></i><i class="sw-down"></i></span>'+esc(T(locale,...CANDLE_LABEL[v]))+'</label>').join('')+
   '</div><p class="small">'+esc(T(locale,'캔들(종가 ≥ 시가 = 상승)·수익률 숫자·시나리오 선에 같은 관례를 씁니다. 색만으로 뜻을 전하지 않으며, 이 기기에만 저장됩니다. 내가 그린 선은 보라색 펜입니다.','Applies to candles (close ≥ open = up), return numbers and scenario lines. Colour never carries meaning alone; saved on this device only. Your own drawings use a purple pen.'))+'</p></section>');
 }
 // The numbered strip scrolls sideways on phones: bring the current section into view without moving the page.
 function afterRender(r){if(r==='settings')mountSettings();const here=$('.ia-sub [data-here]'),ol=here&&here.closest('ol');if(ol&&ol.scrollWidth>ol.clientWidth)ol.scrollLeft=Math.max(0,here.parentElement.offsetLeft-8);}
 // ---------- "준비 중" pages: menus without a screen say what is missing and where the closest existing screen is ----------
 // Statements only; no number, chart or sample value. Sources: owner directive 2026-10-18 §5, §11.
 const PENDING=Object.freeze({
  'lab-13f':{eyebrow:'QGV 1.3 · 13F WEIGHT RESEARCH',ko:'13F 가중치 연구',en:'13F weight research',
   what:['과거 13F 보유와 비슷한 기업을 고르게 만드는 Q/G/V 축 가중치와 Q1~Q5·G1~G5·V1~V5 세부 요인 가중치를 탐색하고, 다른 기간의 유사도와 투자 성과로 검증하는 연구 화면입니다. 기관 관심도 슬라이더가 아니며, 기존 주검정과 별도의 실험으로 등록합니다.',
         'A research screen that searches Q/G/V axis weights and Q1–Q5, G1–G5, V1–V5 factor weights that make the selection resemble past 13F holdings, then checks similarity and investment results in other periods. It is not an institutional-interest slider and is registered apart from the main test.'],
   need:[['과거 13F 투자자 보유 연구 자산의 재사용 범위 확인','How much of the earlier 13F investor-holdings research can be reused'],
         ['분기별 13F 보유 이력(공개 시점 기준)과 증권 식별 연결','Quarterly 13F holdings history as of filing time, linked to security identifiers'],
         ['같은 시점의 요인 점수 이력','Factor score history at the same points in time'],
         ['학습·검증 기간, 평가 지표, 별도 실험 ID·버전 결정','Training and test periods, metrics, and a separate experiment ID and version']],
   // Planned ①→④ flow (owner draft QGV 1.3). Nothing is built: decision IDs only, no result, example weight or similarity.
   flow:[['① 운용사 고르기','① Choose managers','그 시점에 공개된 정보만으로 정한 운용사 목록과 그 분기의 13F 보유를 맞춥니다.','Match a manager list fixed with only the information public at the time to that quarter\'s 13F holdings.','13F-R1~R9'],
         ['② 학습 기간에 맞추기','② Fit on the training period','보유 종목과 가장 닮은 선택을 만드는 Q/G/V 축 비중과 세부 요인 비중을 학습 기간 안에서만 찾습니다.','Search, within the training period only, for the Q/G/V axis and factor weights whose selection most resembles the holdings.','13F-R10~R12'],
         ['③ 다른 기간에서 확인','③ Check in another period','학습에 쓰지 않은 기간에서 유사도를 확인하고, 투자 성과는 가격 자료가 준비된 뒤에 확인합니다.','Check similarity in a period not used for training; investment results are checked only after price data is ready.','13F-R13 · 13F-R16'],
         ['④ 결과','④ Result','찾은 비중은 별도 실험 ID·버전으로 등록하고, 개인 실험 적용과 공식 채택은 따로 결정합니다.','Weights found are registered under a separate experiment ID and version; personal-experiment use and official adoption are decided separately.','13F-R14 · 13F-R15 · TRACKC-PORT']],
   bounds:[['결과는 기관의 실제 기준이 아닙니다.','Results are not the institutions\' actual criteria.'],
           ['공식 기본값을 자동으로 바꾸지 않습니다.','Official defaults are never changed automatically.'],
           ['지금은 준비 단계입니다(결정 13F-R1~R16 대기).','This is the preparation stage (decisions 13F-R1–R16 pending).']],
   links:[['#thirteenf','투자자 13F 보유 공시','Investor 13F filings'],['#validation','Lab · 검증·연구 개요 (실험 등록)','Lab · validation overview (experiment register)']]}
 });
 function pendingHtml(key,loc){
  const l=loc||locale,p=PENDING[key];if(!p)return '';const t=(ko,en)=>T(l,ko,en);
  return '<section class="pending-page" data-pending-page="'+esc(key)+'" aria-labelledby="pending-title">'+
   '<p class="eyebrow">'+esc(p.eyebrow)+'</p><h1 id="pending-title">'+esc(t(p.ko,p.en))+'</h1>'+
   '<p class="pending-state"><span class="badge" data-feature-status="준비 중">'+esc(t('준비 중','Pending'))+'</span><span class="badge NOT_AVAILABLE">NOT_AVAILABLE</span><span class="small">'+esc(t('아직 화면이 없습니다. 예시 숫자나 결과를 넣지 않습니다.','No screen yet. No example numbers or results are shown.'))+'</span></p>'+
   '<p>'+esc(t(...p.what))+'</p>'+
   (p.flow?'<h2>'+esc(t('계획한 흐름 ①~④','Planned flow ①–④'))+'</h2><ol class="vt-list" data-pending-flow>'+p.flow.map(([ko,en,dko,den,ids],i)=>'<li data-pending-step="'+(i+1)+'"><b>'+esc(t(ko,en))+'</b><span class="badge fn-unconnected">'+esc(t('만들지 않음','Not built'))+'</span> '+esc(t(dko,den))+' <span class="small" data-decision-ids>'+esc(t('결정 ','Decisions '))+esc(ids)+'</span></li>').join('')+'</ol>'+
    '<ul data-pending-bounds>'+p.bounds.map(x=>'<li>'+esc(t(...x))+'</li>').join('')+'</ul>':'')+
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
 doc.addEventListener('change',e=>{if(e.target.name==='theme-choice')chooseTheme(e.target.value);
  if(e.target.name==='candle-choice'&&root.AppTheme&&AppTheme.setCandles){const stored=AppTheme.setCandles(e.target.value);const n=$('#notice');if(n&&!stored)n.textContent=T(locale,'차트 색 관례를 이 기기에 저장할 수 없습니다. 이번 방문에만 적용됩니다.','The chart colour choice could not be saved on this device; it applies to this visit only.');}});
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
 root.AppShell=Object.freeze({MENUS,TABS,MORE,PENDING,TREE_KEYS,sync,afterRender,tabFor,menuFor,menuKeyFor,subNavHtml,pendingHtml,openMore,closeMore});
})(window);
