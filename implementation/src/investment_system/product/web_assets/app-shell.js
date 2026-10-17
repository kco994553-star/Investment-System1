/* App shell: header (brand, language, theme, settings), the main menu (PC header) / bottom navigation (phone), the
   "더보기" menu that lists every other existing route, and the theme card in Settings. Navigation and presentation only:
   no data is read, computed or stored here except the theme choice (theme-boot.js, this device only). */
(function(root){
 'use strict';
 const doc=root.document,$=s=>doc.querySelector(s);
 const T=(locale,ko,en)=>locale==='en-US'?en:ko;
 const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]);
 // Primary destinations. Each existing route belongs to exactly one of them (or none, e.g. settings), which is what
 // aria-current follows. 'home' is the search start; the brand link also goes there.
 const TABS=Object.freeze([
  {key:'home',href:'#home',ko:'홈',en:'Home',routes:['home']},
  {key:'explore',href:'#companies',ko:'기업 탐색',en:'Companies',short:['탐색','Explore'],routes:['companies','leaderboard','watchlist','company','analysis','entity','types','qgv']},
  {key:'invest',href:'#portfolio',ko:'내 투자',en:'My investments',short:['내 투자','Mine'],routes:['portfolio','actual','profiles','model','playbook','brief']},
  {key:'market',href:'#news',ko:'시장·뉴스',en:'Market & news',routes:['news','macro','technical','thirteenf']},
  {key:'records',href:'#validation',ko:'기록',en:'Records',routes:['validation','research','report']}
 ]);
 // "더보기": every existing route stays reachable from here (phone) and from the PC "전체 메뉴".
 const MORE=Object.freeze([
  {ko:'기업 탐색',en:'Companies',items:[['#companies','기업 목록','Company list'],['#leaderboard','기업 연구','Company research'],['#watchlist','관심 기업','Watchlist'],['#types','기업 유형 커스텀','Company types'],['#qgv','QGV 허브','QGV hub']]},
  {ko:'내 투자',en:'My investments',items:[['#portfolio','포트폴리오','Portfolio'],['#actual','실제 보유 입력','Actual holdings'],['#brief','오늘의 투자 화면','Today’s investment view'],['#profiles','전략 프로필','Strategy profile'],['#model','모델 포트폴리오','Model portfolio'],['#playbook','플레이북','Playbook']]},
  {ko:'시장·뉴스',en:'Market & news',items:[['#news','뉴스·관계망','News / Network'],['#macro','매크로','Macro'],['#technical','기술적 분석','Technical analysis'],['#thirteenf','투자자 13F','Investor 13F']]},
  {ko:'기록',en:'Records',items:[['#report/mock','모의투자 일일보고서','Paper trading daily report'],['#report/real','투자 일일보고서','Investment daily report'],['#validation','검증·연구','Validation / research'],['#research','리서치','Research']]},
  {ko:'설정',en:'Settings',items:[['#settings','설정','Settings']]}
 ]);
 const THEME_LABEL={light:['라이트','Light'],dark:['다크','Dark'],system:['시스템 설정','System']};
 let locale='ko-KR',route=null;
 const tabFor=r=>TABS.find(t=>t.routes.includes(r))||null;

 function label(){
  const nav=$('#primary-nav');if(!nav)return;
  nav.setAttribute('aria-label',T(locale,'주요 화면','Main navigation'));
  for(const t of TABS){const a=nav.querySelector('[data-nav-tab="'+t.key+'"]');if(!a)continue;
   const long=a.querySelector('.nav-long'),short=a.querySelector('.nav-short');
   if(long)long.textContent=T(locale,t.ko,t.en);if(short)short.textContent=t.short?T(locale,t.short[0],t.short[1]):T(locale,t.ko,t.en);}
  const more=$('#more-button');if(more){more.querySelector('.nav-long').textContent=T(locale,'전체 메뉴','All menus');more.querySelector('.nav-short').textContent=T(locale,'더보기','More');}
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
 // ---------- 더보기 / 전체 메뉴 ----------
 function paintMore(){
  const host=$('#more-menu');if(!host)return;const here='#'+(root.location.hash.slice(1)||'home');
  host.setAttribute('aria-label',T(locale,'전체 메뉴','All menus'));
  host.innerHTML='<div class="more-head"><h2 id="more-title">'+esc(T(locale,'전체 메뉴','All menus'))+'</h2><button type="button" class="tool" data-more-close aria-label="'+esc(T(locale,'메뉴 닫기','Close menu'))+'"><span aria-hidden="true">×</span></button></div>'+
   '<div class="more-groups">'+MORE.map(g=>'<section><h3>'+esc(T(locale,g.ko,g.en))+'</h3><ul>'+g.items.map(([href,ko,en])=>'<li><a href="'+href+'"'+(here===href?' aria-current="page"':'')+'>'+esc(T(locale,ko,en))+'</a></li>').join('')+'</ul></section>').join('')+'</div>'+
   '<p class="more-note">'+esc(T(locale,'PERSONAL / READ ONLY · 보유 정보는 이 기기에만 저장됩니다.','PERSONAL / READ ONLY · Holdings stay on this device.'))+'</p>';
 }
 function openMore(){const host=$('#more-menu'),b=$('#more-button');if(!host||!b)return;closeTheme(false);paintMore();host.hidden=false;b.setAttribute('aria-expanded','true');doc.documentElement.dataset.more='open';
  const first=host.querySelector('a,button');if(first)first.focus({preventScroll:true});}
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
 // Arrow keys inside the theme menu.
 doc.addEventListener('keydown',e=>{const m=$('#theme-menu');if(!m||m.hidden||!m.contains(doc.activeElement)||!['ArrowDown','ArrowUp'].includes(e.key))return;e.preventDefault();
  const items=[...m.querySelectorAll('[data-theme-choice]')],i=items.indexOf(doc.activeElement);items[(i+(e.key==='ArrowDown'?1:items.length-1))%items.length].focus();});
 if(root.AppTheme)AppTheme.subscribe(()=>paintThemeButton());
 root.AppShell=Object.freeze({TABS,MORE,sync,afterRender,tabFor,openMore,closeMore});
})(window);
