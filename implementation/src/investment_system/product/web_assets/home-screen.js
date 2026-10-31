/* Home (search start) and the shared company search box.
   - SearchUI: the one search box (#global-search) as an ARIA combobox/listbox on every screen. It reads the app's existing
     price-free index (window.investmentSearch: INDUSTRY/MACRO entities + TARGET identities + Universe504 codes when
     published). Order = match quality, then name A-Z; it is never a recommendation. IME safe: the input element is never
     rebuilt and keys are ignored while a composition is open. No request is made except the existing same-origin
     Universe504 identity file (app.js ensureUniverseDirectory); no price is requested.
   - HomeScreen: title, the search box (moved into the home slot, never re-created), real recent searches / watchlist
     shortcuts (nothing invented when there are none), one verified investor story (home-quotes.js) and its source sheet,
     a discovery area (menu entry points, navigation only) and, only when the watchlist has companies, a personal news
     area built from the existing public disclosure/news files filtered to those companies (no sample items).
     While a query is open, the company of the highlighted row gets the search result (stamp, company line and the five
     menu cards of the owner draft; see 'search result' below): real public values or 미산출, never a sample number.
     Monochrome editorial look (theme.css); no background image and no animation. */
(function(root){
 'use strict';
 const doc=root.document,$=s=>doc.querySelector(s);
 const T=(locale,ko,en)=>locale==='en-US'?en:ko;
 const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]);
 const narrow=()=>root.matchMedia('(max-width: 749.98px)').matches;
 const finePointer=()=>root.matchMedia('(hover: hover) and (pointer: fine)').matches;
 let locale='ko-KR';

 // ---------- recent searches: this device only, entity keys only (no query text) ----------
 const RECENT_KEY='investment.web.v1.recent-search',RECENT_MAX=6,KEY_SHAPE=/^(COMPANY|INDUSTRY|INVESTOR|MACRO):[A-Za-z0-9_.:\-]{1,64}$/;
 function readRecent(){try{const v=JSON.parse(root.localStorage.getItem(RECENT_KEY)||'[]');return Array.isArray(v)?[...new Set(v.filter(x=>typeof x==='string'&&KEY_SHAPE.test(x)))].slice(0,RECENT_MAX):[];}catch(_){return [];}}
 function pushRecent(key){if(!KEY_SHAPE.test(key))return;const list=[key,...readRecent().filter(x=>x!==key)].slice(0,RECENT_MAX);try{root.localStorage.setItem(RECENT_KEY,JSON.stringify(list));}catch(_){}}
 function clearRecent(){try{root.localStorage.removeItem(RECENT_KEY);}catch(_){}}

 // ---------- search box ----------
 // Korean names that already exist in this app's public code (google-sheet-core.js, tradingview-widgets.js). No other
 // Korean company names are published, so no other Korean company query is answered with a guess.
 const KO_NAMES=Object.freeze({hanmi:'한미반도체',tokyo_electron:'도쿄일렉트론'});
 const FILTERS=Object.freeze({all:null,company:['COMPANY'],other:['INDUSTRY','INVESTOR','MACRO']});
 const S={filter:'all',active:-1,hits:[],composing:false,state:'idle',universe:null,chosen:false,refocus:false};
 const input=()=>$('#global-search'),list=()=>$('#global-results');
 function exchangeOf(e){
  if(e.scope==='UNIVERSE504'&&e.canonical_id.includes(':'))return e.canonical_id.split(':')[0];
  const sym=root.TradingViewWidgets?.SYMBOLS?.[e.canonical_id];return typeof sym==='string'&&sym.includes(':')?sym.split(':')[0]:null;
 }
 // KR-NAMES (2026-10-18): a company with a reviewed names record reads "한국어명 · 티커" (English name, then the ticker alone,
 // as fallbacks; EntitySearch.companyTitle). Without the names file the earlier labels stay.
 function displayName(e){
  if(e.entity_type==='COMPANY'&&e.names&&root.EntitySearch&&EntitySearch.companyTitle)return EntitySearch.companyTitle(e.names,e.ticker,locale);
  if(e.entity_type==='COMPANY'){if(e.scope==='UNIVERSE504')return e.ticker||e.canonical_id;return locale==='ko-KR'&&KO_NAMES[e.canonical_id]?KO_NAMES[e.canonical_id]:e.canonical_label;}
  const names=e.localized_names||{};return names[locale]||e.canonical_label;
 }
 const TYPE_LABEL={COMPANY:['기업','Company'],INDUSTRY:['산업','Industry'],INVESTOR:['투자자','Investor'],MACRO:['거시지표','Macro']};
 function href(e){return e.entity_type==='COMPANY'?'#company/'+encodeURIComponent(e.canonical_id):'#entity/'+encodeURIComponent(e.entity_type+':'+e.canonical_id);}
 function row(hit,i){
  const e=hit.entity,company=e.entity_type==='COMPANY',ex=company?exchangeOf(e):null,name=displayName(e);
  const logo=company&&root.CompanyLogos?CompanyLogos.html(e.ticker||e.canonical_id,20):'';
  const named=company&&e.names,shown=named&&locale!=='en-US'&&e.names.ko_name&&e.names.en_name?e.names.en_name:null;
  const sub=company?(named?[ex,shown,e.scope==='UNIVERSE504'?'Universe504':null]:[e.ticker,ex,e.scope==='UNIVERSE504'?T(locale,'이름 미공개','name not published'):(name!==e.canonical_label?e.canonical_label:null)]).filter(Boolean):[T(locale,...TYPE_LABEL[e.entity_type]||[e.entity_type,e.entity_type]),name!==e.canonical_label?e.canonical_label:null].filter(Boolean);
  return '<li class="item search-hit" role="option" id="search-opt-'+i+'" aria-selected="false" data-entity-id="'+esc(hit.canonical_entity_id)+'"'+(e.scope?' data-entity-scope="'+esc(e.scope)+'"':'')+(company&&e.names?' data-name-status="'+esc(e.names.ko_status)+'"':'')+'>'+
   '<a href="'+href(e)+'" tabindex="-1">'+logo+'<span class="hit-main"><b class="hit-name">'+esc(name)+'</b><span class="hit-sub">'+sub.map(x=>'<span>'+esc(x)+'</span>').join('<span aria-hidden="true"> · </span>')+'</span></span>'+
   '<span class="badge hit-type">'+esc(T(locale,...TYPE_LABEL[e.entity_type]||[e.entity_type,e.entity_type]))+'</span></a></li>';
 }
 function sortHits(hits){const coll=new Intl.Collator(locale,{sensitivity:'base',numeric:true});
  return hits.map((h,i)=>({h,i,name:displayName(h.entity)})).sort((a,b)=>a.h.rank-b.h.rank||a.h.score-b.h.score||coll.compare(a.name,b.name)||a.i-b.i).map(x=>x.h);}
 function head(){
  let h=$('#search-head');if(h)return h;const l=list();if(!l)return null;
  l.insertAdjacentHTML('beforebegin','<div class="search-head" id="search-head" hidden><span class="search-head-title" id="search-head-title"></span><div class="search-filter" role="group" id="search-filter">'+
   Object.keys(FILTERS).map(k=>'<button type="button" class="chip-btn" data-search-filter="'+k+'" aria-pressed="false"></button>').join('')+'</div></div><p class="sr-only" id="search-status" role="status" aria-live="polite"></p>');
  return $('#search-head');
 }
 function labelHead(){const h=head();if(!h)return;$('#search-head-title').textContent=T(locale,'검색 결과','Search results');
  $('#search-filter').setAttribute('aria-label',T(locale,'검색 범위','Search scope'));
  const names={all:['전체','All'],company:['기업','Companies'],other:['산업·지표','Industries · indicators']};
  for(const b of doc.querySelectorAll('[data-search-filter]')){b.textContent=T(locale,...names[b.dataset.searchFilter]);b.setAttribute('aria-pressed',String(b.dataset.searchFilter===S.filter));}}
 function setActive(i,scroll=true){
  const inp=input(),opts=[...doc.querySelectorAll('#global-results [role="option"]')];S.active=opts.length?Math.max(-1,Math.min(opts.length-1,i)):-1;
  opts.forEach((o,k)=>o.setAttribute('aria-selected',String(k===S.active)));
  if(S.active>=0){inp.setAttribute('aria-activedescendant',opts[S.active].id);if(scroll)opts[S.active].scrollIntoView({block:'nearest'});}else inp.removeAttribute('aria-activedescendant');
  if(scroll)result();
 }
 function status(text){const s=$('#search-status');if(s&&s.textContent!==text)s.textContent=text;}
 function paint(){
  const inp=input(),out=list();if(!inp||!out)return;head();labelHead();
  inp.setAttribute('role','combobox');inp.setAttribute('aria-autocomplete','list');inp.setAttribute('aria-controls','global-results');
  out.setAttribute('role','listbox');out.setAttribute('aria-label',T(locale,'검색 결과','Search results'));out.removeAttribute('aria-live');
  const q=inp.value.trim(),open=!!q;
  out.hidden=!open;$('#search-head').hidden=!open;inp.setAttribute('aria-expanded',String(open));
  doc.documentElement.dataset.searching=open?'1':'';if(!open){S.hits=[];setActive(-1);status('');out.innerHTML='';result();return;}
  if(typeof root.investmentSearch!=='function'){
   out.innerHTML=S.state==='error'?'<li class="search-note error" role="none" data-search-state="error">'+esc(T(locale,'검색 자료를 불러오지 못했습니다. 연결을 확인한 뒤 다시 시도하세요.','Search data could not be loaded. Check the connection and try again.'))+'</li>'
    :'<li class="search-note" role="none" data-search-state="loading">'+esc(T(locale,'검색 준비 중…','Preparing search…'))+'</li>';
   status(S.state==='error'?T(locale,'검색 오류','Search error'):T(locale,'검색 준비 중','Preparing search'));setActive(-1);S.hits=[];result();return;}
  let hits=[];try{hits=root.investmentSearch(inp.value,{limit:12,...(FILTERS[S.filter]?{types:FILTERS[S.filter]}:{})});}catch(_){hits=[];}
  S.hits=sortHits(hits);
  const prev=S.active>=0?$('#global-results [aria-selected="true"]')?.dataset.entityId:null;
  let note='';
  if(S.universe==='LOADING')note='<li class="search-note" role="none" data-search-state="loading">'+esc(T(locale,'Universe504 목록을 불러오는 중…','Loading the Universe504 list…'))+'</li>';
  else if(S.universe==='NOT_AVAILABLE'&&/^[A-Za-z.\-]{1,6}$/.test(q))note='<li class="search-note" role="none" data-search-state="partial">'+esc(T(locale,'Universe504 목록 없음 · TARGET 기업과 산업·지표만 검색합니다.','Universe504 list unavailable · searching TARGET companies, industries and indicators only.'))+'</li>';
  out.innerHTML=(S.hits.map(row).join('')||'<li class="empty" role="none" data-search-state="empty">'+esc(T(locale,'일치하는 항목이 없습니다.','No matching items.'))+'</li>')+note;
  const keep=prev?S.hits.findIndex(h=>h.canonical_entity_id===prev):-1;setActive(keep,false);
  status(S.hits.length?T(locale,'검색 결과 '+S.hits.length+'개','Search results: '+S.hits.length):T(locale,'일치하는 항목이 없습니다.','No matching items.'));
  result();
 }
 function choose(i){const h=S.hits[i];if(!h)return;const a=$('#search-opt-'+i+' a');remember(h.canonical_entity_id);if(a)root.location.hash=a.getAttribute('href');}
 function remember(key){pushRecent(key);S.chosen=true;if(currentRoute==='home'){const opt=[...doc.querySelectorAll('#global-results [role="option"]')].find(o=>o.dataset.entityId===key);
  home.saved={query:input().value,filter:S.filter,key,scrollY:root.scrollY,listScroll:list().scrollTop};home.pending=true;}}
 function wire(){
  const inp=input();if(!inp||inp.dataset.searchWired)return;inp.dataset.searchWired='1';
  inp.addEventListener('compositionstart',()=>{S.composing=true;});
  inp.addEventListener('compositionend',()=>{S.composing=false;paint();});
  inp.addEventListener('input',()=>{if(typeof root.ensureUniverseDirectory==='function'&&inp.value.trim())try{void root.ensureUniverseDirectory();}catch(_){}paint();});
  inp.addEventListener('keydown',e=>{
   if(e.isComposing||S.composing||e.keyCode===229)return;
   const n=S.hits.length;
   if((e.key==='ArrowDown'||e.key==='ArrowUp')&&n&&!list().hidden){e.preventDefault();setActive(S.active<0?(e.key==='ArrowDown'?0:n-1):(S.active+(e.key==='ArrowDown'?1:n-1))%n);}
   else if(e.key==='Enter'&&n&&!list().hidden){e.preventDefault();choose(S.active>=0?S.active:0);}
   else if(e.key==='Escape'){if(inp.value){e.preventDefault();inp.value='';paint();}else inp.blur();}
  });
  inp.addEventListener('focus',()=>{if(narrow()&&currentRoute==='home'){const top=inp.getBoundingClientRect().top+root.scrollY-12;root.setTimeout(()=>root.scrollTo({top:Math.max(0,top),behavior:'auto'}),60);}});
  doc.addEventListener('click',e=>{
   const f=e.target.closest('[data-search-filter]');if(f){S.filter=f.dataset.searchFilter;paint();input().focus({preventScroll:true});return;}
   // A chosen result is remembered (recent searches; on home also the query and row for the way back). The box is
   // emptied once the chosen screen has rendered (afterRender), as before.
   const a=e.target.closest('#global-results a');if(a){const li=a.closest('[data-entity-id]');if(li)remember(li.dataset.entityId);}
   // A link in the search-result cards is a choice of that company too (recent searches; the way back to the query).
   const r=e.target.closest('#home-result a[data-result-link]');if(r){const host=r.closest('[data-result-entity]');if(host)remember(host.dataset.resultEntity);}
  });
  list().addEventListener('mousemove',e=>{const o=e.target.closest('[role="option"]');if(o){const i=[...list().querySelectorAll('[role="option"]')].indexOf(o);if(i!==S.active)setActive(i,false);}});
  // PC "/" shortcut: only when no other field is being edited.
  doc.addEventListener('keydown',e=>{
   if(e.key!=='/'||e.ctrlKey||e.metaKey||e.altKey||e.defaultPrevented||!finePointer())return;
   const a=doc.activeElement;if(a&&(a.isContentEditable||['INPUT','TEXTAREA','SELECT'].includes(a.tagName)))return;
   if(doc.querySelector('dialog[open]')||doc.documentElement.dataset.more==='open')return;
   e.preventDefault();inp.focus();inp.select();
  });
 }
 function refresh(opts={}){if(opts.universe!==undefined)S.universe=opts.universe;paint();}
 function setUnavailable(){S.state='error';paint();}
 function setLocale(l){locale=l||locale;const inp=input();if(inp){inp.placeholder=currentRoute==='home'?T(locale,'기업명 또는 티커 검색','Company name or ticker'):inp.placeholder;}labelHead();}

 // ---------- search result (owner draft "투자시스템 화면 시안 (손그림 칠판)", menu 0, PC and 390px) ----------
 // While a query is open on home, the company of the highlighted row (else the first company row) gets one result block:
 // a "검색 결과" stamp, the company line (name, ticker, exchange, SIC group, investment type) and five cards that lead into
 // the owner menus: 1 QGV, 2 기술적 분석, 3 매크로, 4 이 기업 소식, 5 내 포트폴리오에서. Only values that already exist are
 // shown: QGV v2 from the app's one shared score result (ctx.scores, the same as S04/S06), the public SIC group and price-free
 // type, the public filing/news files (DataRefresh, one read per publication), the public TARGET model weight; this device's
 // ACTUAL weight is computed in RAM only (DeviceActual.ramView). Everything else reads 미산출 / NOT_AVAILABLE: no sample
 // number, no price in the page, no request beyond the same-origin public files the app already reads. The official macro
 // phase stays 미산출. Navigation only; nothing here orders, buys or sells.
 const RES={token:0,screens:null};
 const num=(v,d=1)=>new Intl.NumberFormat(locale==='en-US'?'en-US':'ko-KR',{minimumFractionDigits:d,maximumFractionDigits:d}).format(v);
 const pct=v=>num(v*100)+'%';
 const call=f=>{try{return typeof f==='function'?f():f;}catch(_){return null;}};
 // '미산출' (or '없음' when the source answered with nothing: state EMPTY) with its reason (the reason is a sentence for people; the state is in data-res-state for checks).
 const naHtml=(why,state='NOT_AVAILABLE')=>'<span class="res-na" data-res-state="'+state+'">'+esc(state==='EMPTY'?T(locale,'없음','None'):T(locale,'미산출','Not computed'))+'</span>'+(why?' <span class="res-why">'+esc(why)+'</span>':'');
 function resultHit(){const company=h=>!!h&&!!h.entity&&h.entity.entity_type==='COMPANY';const a=S.active>=0?S.hits[S.active]:null;return company(a)?a:S.hits.find(company)||null;}
 function industryOf(screens,id){
  const CS=root.ClassificationScreens,p=CS?screens[CS.FILE]:null,rec=p&&CS.record?CS.record(p,id):null,ind=rec?rec.industry:null;
  if(!ind||ind.state==='NOT_AVAILABLE')return null;const g=p.data.industry_config.groups.find(x=>x.id===ind.group);
  return {sic:ind.sic,group:g?(locale==='en-US'?g.name_en:g.name):ind.group};
 }
 function typesOf(screens,id){
  const CS=root.CompanyScreen;if(!CS||!CS.record||!CS.selectTypes)return null;const rec=CS.record(screens,'company-types-pricefree.json',id);
  const picked=rec&&rec.state!=='NOT_AVAILABLE'?CS.selectTypes(rec.memberships):null;return picked&&picked.length?picked.map(t=>CS.typeName(t,locale)).join(' · '):null;
 }
 function resultHead(e,screens){
  const id=e.canonical_id,ticker=e.ticker||(id.includes(':')?id.slice(id.indexOf(':')+1):id.toUpperCase()),ex=exchangeOf(e),ind=industryOf(screens,id),types=typesOf(screens,id);
  const logo=root.CompanyLogos?CompanyLogos.html(ticker||id,32):'';
  const fact=(k,label,value,why)=>'<span class="res-fact" data-res-fact="'+k+'"><span class="res-fact-k">'+esc(label)+'</span> '+(value?'<b>'+esc(value)+'</b>':naHtml(why))+'</span>';
  return '<h2 class="res-stamp" id="home-result-title">'+esc(T(locale,'검색 결과','Search result'))+'</h2>'+
   '<div class="res-company">'+logo+'<p class="res-name"><a href="#company/'+encodeURIComponent(id)+'" data-result-link="company"><span class="hl">'+esc(displayName(e))+'</span></a></p>'+
   '<p class="res-facts">'+fact('ticker',T(locale,'티커','Ticker'),ticker+(ex?' · '+ex:''))+fact('sic','SIC',ind?ind.sic+' · '+ind.group:null,T(locale,'공개 분류 없음','no public class'))+fact('type',T(locale,'유형','Type'),types,T(locale,'공개 유형 없음','no public type'))+'</p></div>';
 }
 function card(key,n,title,body,links){
  return '<article class="res-card" data-result-card="'+key+'" data-menu="'+key+'" aria-labelledby="res-'+key+'-title"><h3 id="res-'+key+'-title"><span class="res-num" aria-hidden="true">'+esc(n)+'</span> '+esc(title)+'</h3>'+body+
   '<p class="res-links">'+links.map(([href,label,k,sec])=>'<a href="'+href+'" data-result-link="'+k+'">'+(sec?'<span class="res-sec" aria-hidden="true">'+esc(sec)+'</span>':'')+esc(label)+' <span aria-hidden="true">→</span></a>').join('')+'</p></article>';
 }
 const dlRow=(k,label,value)=>'<div class="res-row" data-res-row="'+k+'"><dt>'+esc(label)+'</dt><dd>'+value+'</dd></div>';
 function bar(axis,v){
  const ok=typeof v==='number'&&Number.isFinite(v),w=ok?Math.max(0,Math.min(100,v)):0;
  return '<div class="res-bar" data-axis="'+axis+'" data-res-state="'+(ok?'AVAILABLE':'NOT_AVAILABLE')+'"><b>'+axis+'</b><svg viewBox="0 0 100 12" preserveAspectRatio="none" aria-hidden="true" focusable="false"><rect class="res-bar-track" x="1" y="1.5" width="98" height="9" rx="2"/>'+
   (ok?'<rect class="res-bar-fill" x="1" y="1.5" width="'+(w*.98).toFixed(1)+'" height="9" rx="2"/>':'<path class="res-bar-none" d="M4 6h92"/>')+'</svg><span class="res-bar-v">'+(ok?'<span class="num">'+esc(num(v))+'</span>':esc(T(locale,'미산출','n/a')))+'</span></div>';
 }
 // DC-31: the central V basis (basis day, publication time, STALE, calc version) and the IEX attribution with its terms link.
 function centralLine(screens){const QS=root.QgvScores;if(!QS||typeof QS.centralHtml!=='function')return '';const P=QS.pagePublication();
  return '<div data-res-central>'+QS.centralHtml(QS.centralBasis(P.publication,{reason:P.reason,v2Inputs:screens&&screens['sec-qgv2.json']||null}),locale==='en-US')+'</div>';}
 function qgvCard(e,screens,ctx){
  const id=e.canonical_id,QS=root.QgvScores,en=locale==='en-US',S=call(ctx.scores),r=S&&QS&&QS.rowOf?QS.rowOf(S,id):null,d=r?r.primary:null,cid=encodeURIComponent(id);
  const total=d&&typeof d.total==='number'?'<span class="num" data-res-state="AVAILABLE">'+esc(num(d.total))+'</span>'+(Number.isFinite(d.v)?'':' <span class="res-why">'+esc(T(locale,'V 미포함','V not included'))+'</span>'):naHtml(QS&&QS.naText?QS.naText(d,en):T(locale,'공개 점수 없음','no public score'));
  const ref=r&&r.rank===null&&(r.qg_reference||(QS&&QS.qgReference&&d&&QS.qgReference(d)))?(r.qg_reference||{order:null}):null;
  const rank=r&&Number.isInteger(r.rank)&&S.official?'<span class="num" data-res-state="AVAILABLE">'+esc(String(r.rank))+'</span> <span class="res-why">'+esc((QS.rankLabel?QS.rankLabel(S.profile,en):'')+(en?' · of '+S.official.ranked:' · '+S.official.ranked+'개 중'))+'</span>'
   :ref?naHtml(QS.QG_REFERENCE_LABEL[en?1:0]+(ref.order?' · '+(en?'#'+ref.order:ref.order+'번'):'')+T(locale,' · 공식 QGV 순위 아님',' · not an official QGV rank'),'QG_REFERENCE')
   :naHtml(T(locale,'공식 순위 없음','no official rank'));
  const ind=industryOf(screens,id),group=d?T(locale,'Universe504 백분위 · 업종: ','Universe504 percentile · industry: ')+(ind?ind.group:T(locale,'미산출','not computed')):null;
  return card('qgv','1','QGV','<div class="res-bars" role="img" aria-label="'+esc('Q '+(d&&Number.isFinite(d.q)?num(d.q):T(locale,'미산출','n/a'))+' · G '+(d&&Number.isFinite(d.g)?num(d.g):T(locale,'미산출','n/a'))+' · V '+(d&&Number.isFinite(d.v)?num(d.v):T(locale,'미산출','n/a')))+'">'+['Q','G','V'].map(a=>bar(a,d?d[a.toLowerCase()]:null)).join('')+'</div>'+
   '<dl class="res-dl">'+dlRow('score',T(locale,'QGV 점수','QGV score'),total)+dlRow('rank',T(locale,'순위','Rank'),rank)+dlRow('group',T(locale,'비교군','Comparison group'),group?esc(group):naHtml(T(locale,'점수 없음','no score')))+'</dl>'+centralLine(screens),
   [['#leaderboard',T(locale,'리더보드','Leaderboard'),'leaderboard','1.1'],['#profiles',T(locale,'가중치','Weights'),'profiles','1.2'],['#company/'+cid,T(locale,'스탯창','Stat window'),'radar','']]);
 }
 function taCard(e){
  const cid=encodeURIComponent(e.canonical_id);
  // The frame only: the line is drawn on the technical screen from this device's prices; the public page has no price.
  const chart='<svg class="res-chart" viewBox="0 0 160 56" preserveAspectRatio="none" aria-hidden="true" focusable="false"><path class="res-axis" d="M6 4.5c-.4 15.6-.3 31.4.2 47.1M5.8 51.5c49.6.6 99.4.4 149.1-.4"/><path class="res-none" d="M12 34c46 .8 92 .6 138-.4"/></svg>';
  return card('technical','2',T(locale,'기술적 분석','Technical analysis'),'<div class="res-chart-box">'+chart+'<p class="res-chart-note" data-res-state="DEVICE_ONLY">'+esc(T(locale,'가격 차트는 이 기기 시세로만 그립니다','The price chart is drawn from this device’s prices only'))+'</p></div>'+
   '<dl class="res-dl">'+dlRow('signal',T(locale,'신호','Signal'),naHtml(T(locale,'기기 시세 필요','needs device prices')))+dlRow('pattern',T(locale,'패턴','Pattern'),naHtml(T(locale,'기기 시세 필요','needs device prices')))+'</dl>',
   [['#technical/'+cid,T(locale,'시나리오','Scenarios'),'scenario','2.1'],['#technical-pattern/'+cid,T(locale,'패턴','Patterns'),'pattern','2.2'],['#technical-notes/'+cid,T(locale,'내 노트','My notes'),'notes','2.3']]);
 }
 const PHASE_EN={'회복':'Recovery','확장':'Expansion','둔화':'Slowdown','수축':'Contraction'};
 function macroCard(e,screens){
  const phases=root.MacroCycleRing&&MacroCycleRing.MODELS&&MacroCycleRing.MODELS.economy?MacroCycleRing.MODELS.economy.phases:['회복','확장','둔화','수축'],ind=industryOf(screens,e.canonical_id);
  // A concept curve with the phase names: no position marker until a validated model output is published.
  const curve='<svg class="res-curve" viewBox="0 0 160 56" preserveAspectRatio="none" aria-hidden="true" focusable="false"><path class="res-axis" d="M4 51.6c50.5.5 101.2.3 152-.3"/><path class="res-wave" d="M6 40c12-22 26-34 40-34s26 14 36 26 22 22 36 20 24-14 36-30"/></svg>';
  return card('macro','3',T(locale,'매크로','Macro'),'<div class="res-chart-box">'+curve+'<p class="res-phases" aria-hidden="true">'+phases.map(p=>'<span>'+esc(locale==='en-US'?PHASE_EN[p]||p:p)+'</span>').join('')+'</p></div>'+
   '<dl class="res-dl">'+dlRow('economy',T(locale,'경기 사이클 위치','Business-cycle position'),naHtml(T(locale,'공식 판정 없음','no official phase')))+dlRow('industry',T(locale,'산업 사이클','Industry cycle')+(ind?' · '+ind.group:''),naHtml(ind?T(locale,'위치 모델 검증 전','position model not validated'):T(locale,'SIC 업종 없음','no SIC group')))+'</dl>',
   [['#macro-cycle',T(locale,'근거','Evidence'),'evidence','3.1'],['#macro-rotation',T(locale,'조건','Conditions'),'conditions','3.2'],['#macro-industry',T(locale,'확률','Probability'),'probability','3.3']]);
 }
 function newsCard(e){
  return card('news','4',T(locale,'이 기업 소식','News on this company'),'<ul class="res-news" data-res-news aria-busy="true"><li class="res-why">'+esc(T(locale,'불러오는 중…','Loading…'))+'</li></ul>'+
   '<dl class="res-dl">'+dlRow('effect',T(locale,'Q·G 영향 · 주가 반영','Q·G effect · priced in'),naHtml(T(locale,'점수에 반영하지 않음','never changes scores')))+dlRow('relation',T(locale,'관계','Relations'),naHtml(T(locale,'관계 자료 미연결','relation data not connected')))+'</dl>',
   [['#news/'+encodeURIComponent(e.canonical_id),T(locale,'공시·뉴스 전체','All filings and news'),'news','4.2'],['#news-network',T(locale,'관계망','Network'),'network','4.1']]);
 }
 function portfolioCard(){
  const wait='<span class="res-why">'+esc(T(locale,'확인 중…','Checking…'))+'</span>';
  return card('portfolio','5',T(locale,'내 포트폴리오에서','In my portfolio'),'<dl class="res-dl" data-res-portfolio aria-busy="true">'+dlRow('actual',T(locale,'보유 비중 (이 기기)','Held weight (this device)'),wait)+dlRow('model',T(locale,'모델 비중','Model weight'),wait)+dlRow('paper',T(locale,'모의 편입','Paper portfolio'),naHtml(T(locale,'일일 보고에서 계산','computed in the daily report')))+'</dl>',
   [['#report/real',T(locale,'일일 보고에서 보기','See it in the daily report'),'report','5.2'],['#portfolio',T(locale,'포트폴리오','Portfolio'),'portfolio','5.1']]);
 }
 function fillNews(host,id,token){
  const box=host.querySelector('[data-res-news]'),R=root.DataRefresh,NS=root.NewsSignals,sec=root.SecDisclosures,dart=root.DartDisclosures,en=locale==='en-US';if(!box)return;
  const done=html=>{if(token!==RES.token||!box.isConnected)return;box.removeAttribute('aria-busy');box.innerHTML=html;};
  const none='<li data-res-news-empty>'+naHtml(T(locale,'최근 공시·뉴스 없음','no recent filings or news'),'EMPTY')+'</li>';
  if(!R||!NS||typeof NS.timeline!=='function'){done(none);return;}
  Promise.all([sec?R.list(root,'sec'):null,R.list(root,'news'),dart?R.list(root,'dart'):null]).catch(()=>[null,null,null]).then(([s,n,d])=>{
   let rows=[];try{rows=NS.timeline({sec:s,news:n,dart:d},{companyIds:[id],dartApi:dart}).slice(0,5);}catch(_){rows=[];}
   const text=r=>{try{if(r.source==='SEC'&&r.event)return r.event.form+' · '+sec.classLabel(r.event.classification,en,r.event.items);if(r.event&&r.event.title)return r.event.title;return r.item?r.item.title:'';}catch(_){return r.event?r.event.form||'':'';}};
   done(rows.length?rows.map(r=>{const disc=r.channel==='DISCLOSURE';return '<li data-res-news-item="'+(disc?'DISCLOSURE':'NEWS')+'"><span class="res-tag" data-channel="'+(disc?'DISCLOSURE':'NEWS')+'">'+esc(disc?T(locale,'공시','Filing'):T(locale,'뉴스','News'))+'</span><span class="res-day">'+esc(String(r.time||'').slice(0,10))+'</span><span class="res-title">'+esc(text(r))+'</span></li>';}).join(''):none);
  });
 }
 function fillPortfolio(host,e,ctx,token){
  const box=host.querySelector('[data-res-portfolio]'),ticker=e.ticker;if(!box)return;
  Promise.resolve().then(()=>call(ctx.catalog)).then(async catalog=>{
   const inst=catalog&&ticker&&Array.isArray(catalog.instruments)?catalog.instruments.find(i=>i.ticker===ticker):null;let ram=null;
   if(inst&&root.DeviceActual&&typeof DeviceActual.ramView==='function')try{ram=await DeviceActual.ramView(root,catalog);}catch(_){ram=null;}
   return {catalog,inst,ram};
  }).catch(()=>({catalog:null,inst:null,ram:null})).then(({catalog,inst,ram})=>{
   if(token!==RES.token||!box.isConnected)return;
   const held=inst&&ram&&ram.state==='AVAILABLE'?ram.rows.find(r=>r.ticker===inst.ticker&&Number.isFinite(r.weight)):null;
   const actual=held?'<span class="num" data-res-state="DEVICE">'+esc(pct(held.weight))+'</span> <span class="res-why">'+esc(T(locale,'이 기기 계산 · 저장 안 함','this device · not stored'))+'</span>'
    :naHtml(!catalog?T(locale,'공개 카탈로그 없음','no public catalog'):!inst?T(locale,'TARGET 밖 기업','outside TARGET'):ram&&ram.reason==='NO_ACTUAL'?T(locale,'이 기기에 보유 없음','no holdings on this device'):T(locale,'기기 시세 부족','not enough device prices'),inst&&ram&&ram.reason==='NO_ACTUAL'?'EMPTY':'NOT_AVAILABLE');
   const model=inst&&catalog.total_units>0?'<span class="num" data-res-state="AVAILABLE">'+esc(pct(inst.target_units/catalog.total_units))+'</span> <span class="res-why">TARGET '+esc(catalog.target_root_version||'')+'</span>'
    :naHtml(catalog?T(locale,'모델 포트폴리오에 없음','not in the model portfolio'):T(locale,'공개 카탈로그 없음','no public catalog'),catalog?'EMPTY':'NOT_AVAILABLE');
   box.querySelector('[data-res-row="actual"] dd').innerHTML=actual;box.querySelector('[data-res-row="model"] dd').innerHTML=model;box.removeAttribute('aria-busy');
  });
 }
 function result(){
  const host=$('#home-result');if(!host)return;
  const inp=input(),hit=currentRoute==='home'&&inp&&inp.value.trim()?resultHit():null;
  if(!hit){if(!host.hidden||host.childElementCount){host.hidden=true;host.replaceChildren();delete host.dataset.resultKey;}return;}
  const ctx=home.ctx||{},screens=call(ctx.screens)||{},key=hit.canonical_entity_id+'|'+locale;
  if(host.dataset.resultKey===key&&RES.screens===screens&&!host.hidden)return;
  const token=++RES.token,e=hit.entity;RES.screens=screens;host.dataset.resultKey=key;host.dataset.resultCompany=e.canonical_id;host.dataset.resultEntity=hit.canonical_entity_id;
  host.innerHTML=resultHead(e,screens)+'<div class="res-cards">'+qgvCard(e,screens,ctx)+taCard(e)+macroCard(e,screens)+newsCard(e)+portfolioCard()+'</div>'+
   '<p class="res-foot" data-res-foot>'+esc(T(locale,'검색 순서는 추천 순위가 아님 · V는 중앙 게시(IEX 마지막 체결가 기준) · 가격 차트는 내 기기 시세로만 그림 · 숫자는 공개 자료 그대로, 없으면 미산출','Search order is not a recommendation · V is published centrally (IEX last trade) · the price chart uses this device’s prices only · numbers come from public data as published, otherwise “not computed”'))+'</p>';
  host.hidden=false;fillNews(host,e.canonical_id,token);fillPortfolio(host,e,ctx,token);
 }

 // ---------- home ----------
 let currentRoute=null,lastRoute=null;
 const home={quoteId:null,saved:null,pending:false};
 function html(ctx){
  locale=ctx.locale||locale;
  return '<section class="home" data-home aria-labelledby="home-title">'+
   // Owner draft: no login yet, everything personal is this device's (the same rule as Settings and the full menu).
   '<p class="home-device" data-home-device>'+esc(T(locale,'로그인 안 함 · 이 기기 기준','Not signed in · this device'))+'</p>'+
   '<p class="home-eyebrow" aria-hidden="true">'+esc(T(locale,'기업 검색 · 근거에서 판단까지','Company search · from evidence to judgement'))+'</p>'+
   // The last words get the yellow highlighter (owner design 2026-10-18); the heading text is unchanged.
   '<h1 class="home-title" id="home-title">'+esc(T(locale,'어떤 기업을 ','Which company shall we '))+'<span class="hl">'+esc(T(locale,'살펴볼까요?','look into?'))+'</span></h1>'+
   // Self-made hand-drawn rule: decoration only.
   '<svg class="home-sketch" viewBox="0 0 220 14" preserveAspectRatio="none" aria-hidden="true" focusable="false"><path d="M2 8.5c18-3.2 36-4.1 55-2.6 17 1.3 30 3.9 49 3.1 22-.9 38-4.6 60-4.2 17 .3 33 2 52 3.6"/><path d="M40 11.2c25-1.6 52-1.2 80-.3"/></svg>'+
   '<p class="home-sub">'+esc(T(locale,'기업을 이해하고, 근거로 판단하세요.','Understand the business, decide on evidence.'))+'</p>'+
   '<div class="home-search-slot" id="home-search-slot"></div>'+
   '<div class="home-shortcuts" id="home-shortcuts" data-home-shortcuts></div>'+
   '<section class="home-result" id="home-result" data-home-result aria-labelledby="home-result-title" hidden></section>'+
   '<section class="home-quote" id="home-quote" data-home-quote aria-labelledby="home-quote-title"></section>'+
   '<section class="home-personal" id="home-personal" data-home-personal aria-labelledby="home-personal-title" hidden></section>'+
   discover()+
   '</section>';
 }
 // Discovery (shown when nothing is being searched): where each question is answered. Navigation only, no data.
 function discover(){
  // Numbers follow the owner menus (0 홈 · 1–6 · n 구조 트리 · n+1 Lab, 2026-10-18); data-menu carries the menu colour.
  const rows=[['1','QGV','무엇을 하는 기업인가','What does the company do?','리더보드 · 기업 목록 · 기업 상세','Leaderboard · company list · detail','#leaderboard'],
   ['3',T(locale,'매크로','Macro'),'지금 어떤 환경인가','What is the environment now?','거시 8축 · 경고등','Eight macro axes · lights','#macro'],
   ['4',T(locale,'뉴스','News'),'무슨 일이 있었나','What happened?','공시·뉴스 · 기업 관계망','Filings and news · company network','#news'],
   ['n+1','Lab','이 판단은 작동하는가','Does the judgement work?','검증·연구 · 전진검증','Validation · forward checks','#validation']];
  return '<nav class="home-discover" id="home-discover" data-home-discover aria-labelledby="home-discover-title"><h2 class="home-section-title" id="home-discover-title">'+esc(T(locale,'어디서 시작할까요','Where to begin'))+'</h2><ul class="discover-list">'+
   rows.map(([n,menu,qk,qe,tk,te,href])=>'<li data-menu="'+({'1':'qgv','3':'macro','4':'news','n+1':'lab'})[n]+'"><a href="'+href+'" data-discover="'+esc(href.slice(1))+'"><span class="discover-num">'+esc(n+' / '+menu)+'</span><span class="discover-q">'+esc(T(locale,qk,qe))+'</span><span class="discover-to">'+esc(T(locale,tk,te))+' <span aria-hidden="true">↗</span></span></a></li>').join('')+
   '</ul><p class="home-more"><a href="#brief" data-home-brief>'+esc(T(locale,'오늘의 투자 화면 · 운영 카드 보기','Today’s investment view · status cards'))+' <span aria-hidden="true">→</span></a></p></nav>';
 }
 // Personal news: only for companies on this device's watchlist, from the same public files the news screen reads
 // (SEC 8-K, DART, news signals). Nothing is shown without a watchlist; a short hint when those companies have no item.
 let personalLoad=null,personalToken=0;
 function personal(ctx){
  const host=$('#home-personal');if(!host)return;const ids=[...new Set((ctx.interests||[]).filter(x=>typeof x==='string'&&x))];
  if(!ids.length||typeof root.SecDisclosures!=='object'){host.hidden=true;host.replaceChildren();return;}
  const token=++personalToken;host.hidden=false;
  host.innerHTML='<h2 class="home-section-title" id="home-personal-title">'+esc(T(locale,'내 관심 기업 소식','News on my watchlist'))+'</h2>'+
   '<p class="home-personal-note">'+esc(T(locale,'관심 기업 '+ids.length+'곳 · 공시·확정과 뉴스·신호 · 점수에 반영하지 않음','Watchlist: '+ids.length+' · filings (confirmed) and news (signals) · never changes scores'))+'</p>'+
   '<div data-home-personal-feed aria-busy="true"><p class="small">'+esc(T(locale,'불러오는 중…','Loading…'))+'</p></div>'+
   '<a class="home-personal-all" href="#watchlist">'+esc(T(locale,'관심 기업 화면에서 전체 보기','See everything on the watchlist screen'))+' <span aria-hidden="true">→</span></a>';
  const news=typeof root.NewsSignals==='object'?root.NewsSignals:null,dart=typeof root.DartDisclosures==='object'?root.DartDisclosures:null;
  // The same in-tab copy of the list files as every other screen (DataRefresh: one read per publication, D6).
  const R=root.DataRefresh,lists=R?Promise.all([R.list(root,'sec'),news?R.list(root,'news'):null,dart?R.list(root,'dart'):null]).catch(()=>[null,null,null])
   :(personalLoad=personalLoad||Promise.all([root.SecDisclosures.load(root),news?news.load(root):null,dart?dart.load(root):null]).catch(()=>[null,null,null]));
  lists.then(([sec,signals,dartPayload])=>{
   const feed=host.querySelector('[data-home-personal-feed]');if(token!==personalToken||!feed||!feed.isConnected)return;
   // storage:null keeps the news screen's own view options untouched (home shows the default, newest first).
   const tmp=doc.createElement('div'),opts={locale,companyIds:ids,limit:5,interests:ids,storage:null};
   try{if(news)news.mount(tmp,{sec,news:signals,dart:dartPayload},Object.assign(opts,{secApi:root.SecDisclosures,dartApi:dart}));else root.SecDisclosures.mount(tmp,sec,opts);}catch(_){tmp.replaceChildren();}
   const items=tmp.querySelectorAll('[data-news-item],[data-disclosure]').length;
   feed.removeAttribute('aria-busy');
   if(items)feed.replaceChildren(...tmp.childNodes);
   else feed.innerHTML='<p class="small" data-home-personal-empty>'+esc(T(locale,'관심 기업의 최근 공시·뉴스가 없습니다.','No recent filings or news for your watchlist.'))+'</p>';
  });
 }
 function shortcuts(ctx){
  const host=$('#home-shortcuts');if(!host)return;
  const resolve=key=>{const cut=key.indexOf(':');try{return ctx.resolve(key.slice(0,cut),key.slice(cut+1));}catch(_){return null;}};
  const recent=readRecent().map(k=>({k,e:resolve(k)})).filter(x=>x.e);
  const watch=(ctx.interests||[]).map(id=>({k:'COMPANY:'+id,e:resolve('COMPANY:'+id)||ctx.company?.(id)})).filter(x=>x.e);
  const chip=x=>{const e=x.e,company=!e.entity_type||e.entity_type==='COMPANY',id=e.canonical_id||e.company_id,text=company?(e.ticker||id):displayName(e);
   return '<a class="chip-link" href="'+(company?'#company/'+encodeURIComponent(id):'#entity/'+encodeURIComponent(x.k))+'" data-shortcut="'+esc(x.k)+'">'+esc(text)+'</a>';};
  let out='';
  if(recent.length)out+='<div class="shortcut-row" data-recent-searches><span class="shortcut-label" id="recent-label">'+esc(T(locale,'최근 검색','Recent'))+'</span><div class="shortcut-chips" role="list" aria-labelledby="recent-label">'+recent.map(x=>'<span role="listitem">'+chip(x)+'</span>').join('')+'</div><button type="button" class="link-btn" data-recent-clear>'+esc(T(locale,'지우기','Clear'))+'</button></div>';
  if(watch.length)out+='<div class="shortcut-row" data-watch-shortcuts><span class="shortcut-label" id="watch-label">'+esc(T(locale,'관심 기업','Watchlist'))+'</span><div class="shortcut-chips" role="list" aria-labelledby="watch-label">'+watch.slice(0,8).map(x=>'<span role="listitem">'+chip(x)+'</span>').join('')+'</div>'+(watch.length>8?'<a class="link-btn" href="#watchlist">'+esc(T(locale,'전체 보기','See all'))+'</a>':'')+'</div>';
  if(!out)out='<p class="shortcut-hint" data-shortcut-hint>'+esc(T(locale,'검색해서 연 기업은 이 기기에만 최근 검색으로 남습니다.','Companies you open from search stay here as Recent, on this device only.'))+'</p>';
  host.innerHTML=out;
 }
 function quote(){
  const host=$('#home-quote');if(!host||!root.HomeQuotes)return;
  let q=HomeQuotes.byId(home.quoteId);if(!q){q=HomeQuotes.pick(null);home.quoteId=q.id;}
  const en=locale==='en-US',story=q.type==='STORY';
  const kind=story?T(locale,'일화 요약','Story summary'):T(locale,'직접 인용','Direct quote');
  host.innerHTML='<h2 class="sr-only" id="home-quote-title">'+esc(T(locale,'투자 이야기','Investor story'))+'</h2>'+
   '<p class="quote-kind" data-quote-type="'+q.type+'"><span data-quote-kind>'+esc(kind)+'</span>'+(en?'':'<span class="quote-tr">'+esc(story?'한국어 요약':'한국어 번역')+'</span>')+'</p>'+
   '<blockquote class="quote-text" data-quote-id="'+esc(q.id)+'" lang="'+(en?'en':'ko')+'"><p>'+esc(en?q.headline_en:q.ko)+'</p></blockquote>'+
   '<p class="quote-line">'+esc(en?q.line.en:q.line.ko)+'</p>'+
   '<div class="quote-actions"><button type="button" class="link-btn" id="quote-source-button" aria-haspopup="dialog" data-quote-source>'+esc(T(locale,'출처 보기','View source'))+' <span aria-hidden="true">↗</span></button>'+
   '<button type="button" class="link-btn" id="quote-next" data-quote-next><svg class="shuffle" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M3 7h3.5c2 0 3.2.9 4.3 2.6l2.4 4.8c1.1 1.7 2.3 2.6 4.3 2.6H21M3 17h3.5c1.4 0 2.4-.4 3.2-1.2M13.8 8.2c.8-.8 1.8-1.2 3.2-1.2H21M18 4l3 3-3 3M18 14l3 3-3 3"/></svg>'+esc(T(locale,'다른 이야기','Another story'))+'</button></div>';
 }
 function dialog(){
  let d=$('#quote-dialog');
  if(!d){doc.body.insertAdjacentHTML('beforeend','<dialog id="quote-dialog" class="quote-sheet" aria-labelledby="quote-dialog-title"></dialog>');d=$('#quote-dialog');
   d.addEventListener('close',()=>{const b=$('#quote-source-button');if(b)b.focus({preventScroll:true});});
   d.addEventListener('click',e=>{if(e.target===d)d.close();});}
  const q=HomeQuotes.byId(home.quoteId);if(!q)return null;const en=locale==='en-US',story=q.type==='STORY';
  const rows=[[T(locale,'유형','Type'),esc(story?T(locale,'일화 요약','Story summary'):T(locale,'직접 인용','Direct quote'))],
   [T(locale,'원문','Original'),'<blockquote lang="en" class="src-original">'+esc(q.original)+'</blockquote>'],
   ...(en?[]:[[story?'요약·번역 (자체 작성)':'번역 (자체 번역)','<p lang="ko">'+esc(q.ko_full)+'</p>']]),
   [T(locale,'발언자','Speaker'),esc(en?q.speaker.en:q.speaker.ko)],[T(locale,'출처','Source'),esc(q.source)],[T(locale,'날짜','Date'),esc(q.date)],
   [T(locale,'원문 링크','Link'),'<a href="'+esc(q.url)+'" target="_blank" rel="noopener noreferrer">'+esc(q.url.replace(/^https:\/\//,''))+' <span aria-hidden="true">↗</span></a>'],
   [T(locale,'맥락','Context'),esc(en?q.context.en:q.context.ko)],
   [T(locale,'확인','Checked'),esc(T(locale,'1차 출처 원문과 문장 대조 · '+q.checked_at,'Matched word for word against the primary source · '+q.checked_at))]];
  d.innerHTML='<div class="sheet-grab" aria-hidden="true"></div><div class="sheet-head"><h2 id="quote-dialog-title">'+esc(T(locale,'출처','Source'))+'</h2><button type="button" class="tool" data-dialog-close aria-label="'+esc(T(locale,'닫기','Close'))+'"><span aria-hidden="true">×</span></button></div>'+
   '<dl class="src-list">'+rows.map(([k,v])=>'<dt>'+esc(k)+'</dt><dd>'+v+'</dd>').join('')+'</dl>'+
   '<p class="small src-note">'+esc(T(locale,'투자 철학을 소개하는 글입니다. 종목 추천·매매 신호·성과 근거가 아닙니다.','Introduces an investing philosophy. Not a stock pick, trading signal or evidence of performance.'))+'</p>'+
   '<div class="sheet-foot"><button type="button" data-dialog-close>'+esc(T(locale,'닫기','Close'))+'</button></div>';
  return d;
 }
 function openSource(){const d=dialog();if(!d)return;if(typeof d.showModal==='function')d.showModal();else d.setAttribute('open','');d.querySelector('[data-dialog-close]')?.focus();}
 doc.addEventListener('click',e=>{
  if(e.target.closest('[data-quote-source]')){openSource();return;}
  if(e.target.closest('[data-dialog-close]')){const d=e.target.closest('dialog');if(d){if(typeof d.close==='function')d.close();else{d.removeAttribute('open');$('#quote-source-button')?.focus();}}return;}
  if(e.target.closest('[data-quote-next]')){const q=HomeQuotes.pick(home.quoteId);home.quoteId=q.id;quote();$('#quote-next')?.focus({preventScroll:true});return;}
  if(e.target.closest('[data-recent-clear]')){clearRecent();if(home.ctx)shortcuts(home.ctx);$('#home-shortcuts .shortcut-hint')?.setAttribute('tabindex','-1');$('#home-shortcuts .shortcut-hint')?.focus();}
 });
 // The search section moves into the home slot and back; the element (and any IME state) is never re-created.
 // nextRoute 'home' (a re-render of home, e.g. a language switch) keeps the query, the scope and the caret.
 function park(nextRoute){
  const sec=$('#global-search-section'),anchor=$('#global-search-anchor');if(!sec||!anchor||sec.previousElementSibling===anchor)return;
  const inp=input(),keep=nextRoute==='home';
  if(keep&&inp&&doc.activeElement===inp)S.refocus={start:inp.selectionStart,end:inp.selectionEnd};
  if(!keep&&inp)inp.value='';anchor.after(sec);paint();
 }
 function placeIntoHome(){
  const sec=$('#global-search-section'),slot=$('#home-search-slot');if(!sec||!slot||sec.parentElement===slot)return;
  const inp=input(),focused=doc.activeElement===inp;
  if(S.composing){inp.addEventListener('compositionend',()=>root.setTimeout(placeIntoHome,0),{once:true});return;}
  slot.append(sec);
  if(focused||S.refocus){inp.focus({preventScroll:true});if(S.refocus&&S.refocus.start!=null)try{inp.setSelectionRange(S.refocus.start,S.refocus.end);}catch(_){}}
  S.refocus=false;
 }
 function mount(ctx){
  locale=ctx.locale||locale;home.ctx=ctx;
  const entering=lastRoute!=='home';
  if(entering&&!home.pending){home.quoteId=HomeQuotes.pick(home.quoteId).id;}
  placeIntoHome();const inp=input();
  if(inp){inp.placeholder=T(locale,'기업명 또는 티커 검색','Company name or ticker');inp.setAttribute('aria-label',T(locale,'기업명 또는 티커 검색','Search by company name or ticker'));}
  shortcuts(ctx);quote();personal(ctx);
  // Back from a screen opened from these results: the query, scope and the chosen row come back.
  if(home.pending&&home.saved&&entering&&['company','analysis','entity','news','technical'].includes(lastRoute)){
   const s=home.saved;S.filter=s.filter;inp.value=s.query;
   if(typeof root.ensureUniverseDirectory==='function')try{void root.ensureUniverseDirectory();}catch(_){}
   paint();const i=S.hits.findIndex(h=>h.canonical_entity_id===s.key);setActive(i,false);
   if(i>=0)list().scrollTop=s.listScroll||0;
   root.requestAnimationFrame(()=>{root.scrollTo(0,s.scrollY||0);if(!narrow())inp.focus({preventScroll:true});});
  }
  home.pending=false;
 }
 function afterRender(route,ctx){
  lastRoute=currentRoute;currentRoute=route;locale=ctx.locale||locale;
  if(S.chosen){S.chosen=false;if(route!=='home'){const inp=input();if(inp){inp.value='';paint();}}}
  if(route==='home')mount(ctx);else backLink(route,ctx.id);
  setLocale(ctx.locale);paint();
 }
 // DataRefresh calls this only after applying a complete public generation (or re-judging that generation).
 // Leave the home/search DOM, IME/caret and highlighted result in place; the failed-refresh path never calls it.
 function refreshPersonal(interests){
  if(currentRoute!=='home'||!home.ctx)return false;
  home.ctx={...home.ctx,interests};personal(home.ctx);return true;
 }
 // The central V read settled (app.js refreshScoreViews): repaint the open result card with the same search state.
 function refreshScores(){const host=$('#home-result');if(!host||host.hidden)return false;delete host.dataset.resultKey;result();return true;}
 // A company / entity opened from the home results offers the way back to them (query, scope and row are restored).
 function backLink(route,id){
  if(!home.pending||!home.saved||!['company','analysis','entity'].includes(route))return;
  const key=route==='entity'?id:'COMPANY:'+id;if(home.saved.key!==key)return;
  const content=$('#content');if(!content||content.querySelector('[data-origin-link="home"]'))return;
  const link='<a class="parent-link" href="#home" data-origin-link="home">'+esc(T(locale,'\u2190 검색 결과','\u2190 Search results'))+'</a>';
  const row=content.querySelector(':scope > .parent-row');
  if(row)row.insertAdjacentHTML('afterbegin',link);else content.insertAdjacentHTML('afterbegin','<p class="parent-row">'+link+'</p>');
 }
 wire();
 root.SearchUI=Object.freeze({refresh,setUnavailable,setLocale,paint,readRecent,clearRecent,KO_NAMES});
 root.HomeScreen=Object.freeze({html,afterRender,park,refreshPersonal,refreshScores,state:()=>({route:currentRoute,quoteId:home.quoteId,filter:S.filter})});
})(window);
