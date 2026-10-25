/* 0. 기업 검색 · 검색 결과 (draft boards Main / MMain; feature 1.1.1–1.1.4, P2-1).
   - The search box is in the first paint (no layer needed): typing works at once, the list says 불러오는 중 until the company index
     is ready. The index (EntitySearch, reused) is built after IS2.ready from the three static public files only: the TARGET
     catalog (DeviceWatchlist.identities), the fixed Universe504 code list (universe-codes.json) and the reviewed names table
     (company-names-ko.json, also the code → company_id links). A missing file leaves its part out and a status line says which.
     Companies only; order = match quality, then name (never a recommendation); 8 options at most; no price, cap, score or rank.
   - ARIA combobox / listbox (the old SearchUI pattern): arrows move, Enter submits the form (implicit submission clicks the
     default button) and the selection runs in that click, Escape closes. IME safe: no key handling while composing, and the
     input element is never rebuilt when the list changes.
   - A chosen option (pointer click, or Enter with an option active) is saved as a recent search with that click
     (store.pushRecent, one action per event; a refused or failed save still navigates). A submit without an active option goes to
     the single exact match, else to #/company/<query> as P0 did; it saves nothing.
   - Home: recent chips (titles from the index, unknown keys skipped, 최근 지우기), favorites (store prefs interests) or, without
     any, the developer default (the TARGET 19, labelled as such, never written), one verified investor story (home-quotes.js).
   - Company page: the id as given in h1[data-result-code] at once; after IS2.ready the title, ticker, exchange code, membership,
     SIC group and investment type (public files, only when present); the ★ toggle (store prefs, a click); the five cards from the
     layer (QGV page row, macro lights, public filing / news lists, device holdings yes / no) or NA with the reason. No price and
     no price-derived value; the technical card asks for nothing (prices only on the technical screen's click). The resolved id
     becomes IS2.selection (RAM). Unknown id: a fixed sentence, no guess, no values. */
(function(){
'use strict';
const I=window.IS2,{h,icon,href,register,parts:{card,pending,more}}=I;
const SEARCH=['M13 4 A9 9 0 1 1 12.99 4','M20 20 L27 27'];
const MAX=8,CATALOG='actual-catalog.json',NAMES='company-names-ko.json',MACRO='macro-screen.json',DEFAULT_SHOWN=8;
const LISTS=[['sec','sec-disclosures.json'],['news','news-signals.json'],['dart','dart-disclosures.json']];
const MACRO_STATE={NORMAL:'정상',WARNING:'경고',CRISIS:'위기'};// MacroLights STATE_LABEL (not exported)
// The investment types the company page names (company-screen.js TYPES), mixed by type_config/1.
const TYPES=['growth','quality','cyclical','defensive'];
const ok=v=>typeof v==='number'&&Number.isFinite(v);
const fmt=v=>new Intl.NumberFormat('ko-KR',{minimumFractionDigits:1,maximumFractionDigits:1}).format(v);
const settled=(signal,fn)=>v=>{if(!signal.aborted)fn(v);};
// IS2.ready (none at all when loader.js itself failed to load: the shell shows the failure notice).
const ready=()=>I.ready||Promise.reject(Error('LOADER_FAILED loader.js'));
const canonical=v=>Array.isArray(v)?'['+v.map(canonical).join(',')+']':v&&typeof v==='object'?'{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canonical(v[k])).join(',')+'}':JSON.stringify(v);

/* ---------------------------------------------------------------- company index (after IS2.ready, static files only) */
let indexP=null,quoteId=null;
function companyIndex(){
 if(!indexP){indexP=build();indexP.then(x=>{if(x.missing.length)indexP=null;},()=>{indexP=null;});}
 return indexP;}
async function build(){
 await ready();
 const D=I.data,ES=window.EntitySearch,W=window.DeviceWatchlist;
 const[catalog,names,codes]=await Promise.all([D.static(CATALOG),D.static(NAMES),D.universe()]);
 let ids=[];try{ids=catalog?W.identities(catalog):[];}catch(_){ids=[];}
 const list=Array.isArray(codes)?codes:[],links={};for(const c of list)links[c]=null;
 if(names)for(const[c,id]of names.codes())if(id&&Object.hasOwn(links,c))links[c]=id;
 const idx=ES.createIndex(ES.companyEntities(ids,links,names));
 // A TARGET company's Universe504 code: the code linked to its company_id, else the code with its ticker (companyEntities' rule).
 const tick=t=>String(t).replaceAll('.','-'),codeOf=new Map(),targetOf=new Map();
 for(const c of ids){const code=list.find(x=>links[x]===c.company_id)||list.find(x=>/^(NYSE|NASDAQ|BATS):/.test(x)&&tick(x.slice(x.indexOf(':')+1))===tick(c.ticker));
  if(code){codeOf.set(c.company_id,code);targetOf.set(code,c.company_id);}}
 const missing=[!ids.length&&'TARGET 기업 목록',!list.length&&'Universe504 목록',!names&&'한국어 이름표'].filter(Boolean);
 const resolve=id=>typeof id==='string'?idx.resolve('COMPANY',id)||(targetOf.has(id)?idx.resolve('COMPANY',targetOf.get(id)):null)||null:null;
 const coll=new Intl.Collator('ko-KR',{sensitivity:'base',numeric:true});
 const title=e=>e.names?ES.companyTitle(e.names,e.ticker,'ko-KR'):e.scope==='TARGET'?e.canonical_label+' · '+e.ticker:e.ticker;
 const code=e=>e.scope==='UNIVERSE504'?e.canonical_id:codeOf.get(e.canonical_id)||(e.names&&e.names.exchange)||null;
 const member=e=>e.scope==='UNIVERSE504'?'Universe504':codeOf.has(e.canonical_id)?'TARGET · Universe504 둘 다':'TARGET';
 // The English (SEC) name under a Korean title; the title itself is the English name or the ticker otherwise.
 const english=e=>e.names&&e.names.ko_name&&e.names.en_name?e.names.en_name:null;
 // EntitySearch's match order, then the shown name (the old SearchUI rule): navigation only.
 function search(q){let hits=[];try{hits=idx.search(q,{limit:1000,types:['COMPANY']});}catch(_){hits=[];}
  return hits.map((x,i)=>({x,i,name:title(x.entity)})).sort((a,b)=>a.x.rank-b.x.rank||a.x.score-b.x.score||coll.compare(a.name,b.name)||a.i-b.i).map(o=>o.x);}
 // The one exact match of a query (ticker, name, Korean name or alias written out in full), else null.
 function exact(q){const hits=search(q).filter(x=>/^EXACT_/.test(x.match_type));return hits.length===1?hits[0].entity:null;}
 return Object.freeze({search,exact,resolve,find:q=>resolve(q)||exact(q),title,code,member,english,missing:Object.freeze(missing),
  targets:Object.freeze(ids.map(c=>c.company_id)),catalog});
}
const missingLine=idx=>idx.missing.length?h('p',{class:'reason',dataset:{indexMissing:''}},'일부 목록을 읽지 못했습니다(',idx.missing.join(' · '),') · 읽은 목록으로만 찾습니다'):null;
// The store's sync getters answer IS2.NOT_READY before the layer is there.
const loaded=x=>!!x&&typeof x==='object'&&x.state!=='NOT_READY';

/* ---------------------------------------------------------------- search box (combobox) */
function searchBox(route,{label}){
 const signal=route.signal,S={hits:[],active:-1,composing:false,idx:null};
 const input=h('input',{id:'q',type:'search',autocomplete:'off',spellcheck:'false',placeholder:'티커 · 회사명 · 한글명',role:'combobox','aria-expanded':'false',
  'aria-controls':'q-list','aria-autocomplete':'list',dataset:{searchInput:''}});
 const list=h('ul',{id:'q-list',class:'sk search-list',role:'listbox','aria-label':'찾은 기업',hidden:true,dataset:{searchList:''}});
 const status=h('p',{class:'sr-only',role:'status',dataset:{searchStatus:''}});
 const note=h('div',{class:'search-note-line'});
 const say=t=>{if(status.textContent!==t)status.textContent=t;};
 function setActive(i){const opts=[...list.querySelectorAll('[role=option]')];S.active=opts.length?Math.max(-1,Math.min(opts.length-1,i)):-1;
  opts.forEach((o,k)=>o.setAttribute('aria-selected',String(k===S.active)));
  if(S.active>=0){input.setAttribute('aria-activedescendant',opts[S.active].id);opts[S.active].scrollIntoView({block:'nearest'});}else input.removeAttribute('aria-activedescendant');}
 function show(open){list.hidden=!open;input.setAttribute('aria-expanded',String(open));if(!open){S.hits=[];setActive(-1);}}
 function option(hit,i){const e=hit.entity,ix=S.idx,sub=[ix.english(e),ix.code(e),ix.member(e)].filter(Boolean);
  return h('li',{id:'q-opt-'+i,class:'search-opt',role:'option','aria-selected':'false',dataset:{entityKey:hit.canonical_entity_id,entityId:e.canonical_id},
   onmousedown:ev=>ev.preventDefault(),onmousemove:()=>{if(S.active!==i)setActive(i);},onclick:ev=>go(ev,e)},
   h('b',{class:'opt-name'},ix.title(e)),h('span',{class:'opt-sub'},sub.join(' · ')));}
 function paint(){
  const q=input.value.trim();if(!q){list.replaceChildren();show(false);say('');return;}
  if(!S.idx){S.hits=[];list.replaceChildren(h('li',{class:'search-msg',role:'presentation',dataset:{searchState:'loading'}},'불러오는 중'));show(true);setActive(-1);say('검색 목록 불러오는 중');return;}
  const keep=S.active>=0&&S.hits[S.active]?S.hits[S.active].canonical_entity_id:null;
  S.hits=S.idx.search(q).slice(0,MAX);
  list.replaceChildren(...(S.hits.length?S.hits.map(option):[h('li',{class:'search-msg',role:'presentation',dataset:{searchState:'empty'}},'일치하는 기업이 없습니다')]));
  show(true);setActive(keep?S.hits.findIndex(x=>x.canonical_entity_id===keep):-1);say(S.hits.length?'찾은 기업 '+S.hits.length+'곳':'일치하는 기업이 없습니다');}
 // Saved with this click (a trusted click only; the store refuses others), then navigation in any case.
 function go(ev,e){if(ev)ev.preventDefault();try{I.store.pushRecent(ev,'COMPANY:'+e.canonical_id);}catch(_){}location.hash=href('company',e.canonical_id);}
 // The form's default button: a click, or Enter in the input (implicit submission clicks it).
 function submit(ev){ev.preventDefault();const q=input.value.trim();
  if(S.active>=0&&S.hits[S.active]){go(ev,S.hits[S.active].entity);return;}
  const one=S.idx&&q?S.idx.exact(q):null;
  if(one){location.hash=href('company',one.canonical_id);return;}
  if(q)location.hash=href('company',q);}
 input.addEventListener('compositionstart',()=>{S.composing=true;});
 input.addEventListener('compositionend',()=>{S.composing=false;paint();});
 input.addEventListener('input',()=>{if(!S.composing)paint();});
 input.addEventListener('keydown',e=>{
  if(e.isComposing||S.composing||e.keyCode===229)return;
  const n=S.hits.length,open=!list.hidden;
  if((e.key==='ArrowDown'||e.key==='ArrowUp')&&n&&open){e.preventDefault();setActive(S.active<0?(e.key==='ArrowDown'?0:n-1):(S.active+(e.key==='ArrowDown'?1:n-1))%n);}
  else if(e.key==='Escape'&&(open||input.value)){e.preventDefault();if(open)show(false);else{input.value='';paint();}}});
 input.addEventListener('focus',()=>{if(input.value.trim())paint();});
 const form=h('form',{class:'sk search-box',role:'search',dataset:{searchForm:''},onsubmit:e=>e.preventDefault()},
  icon(SEARCH,30),input,h('button',{class:'btn solid',type:'submit',onclick:submit},'검색'));
 companyIndex().then(settled(signal,idx=>{S.idx=idx;note.replaceChildren(missingLine(idx)||'');if(!S.composing)paint();}),()=>{});
 const anchor=h('div',{class:'search-anchor'},form,list);
 // The list is hidden when the focus leaves the box; the highlighted option stays chosen (a browser that does not focus a clicked
 // button blurs the input before the 검색 click). Escape and an emptied box clear it.
 anchor.addEventListener('focusout',()=>{setTimeout(()=>{if(!signal.aborted&&!anchor.contains(document.activeElement)){list.hidden=true;input.setAttribute('aria-expanded','false');}},0);});
 return h('div',{class:'search-wrap'},label,anchor,status,note);
}

/* ---------------------------------------------------------------- home */
function chipLink(idx,id,star){const e=idx.resolve(id);return e?h('a',{class:'chip',href:href('company',e.canonical_id),dataset:{chip:e.canonical_id}},star?'★ ':'',idx.title(e)):null;}
function chips(route,host){
 const signal=route.signal;
 companyIndex().then(settled(signal,idx=>draw(idx)),()=>{});
 function draw(idx){
  const S=I.store,recent=S.recent(),prefs=S.prefs(),rows=[];
  const keys=Array.isArray(recent)?recent.filter(k=>k.startsWith('COMPANY:')).map(k=>k.slice(8)):[];
  const recentChips=keys.map(id=>chipLink(idx,id,false)).filter(Boolean);
  if(recentChips.length){
   const clear=h('button',{type:'button',class:'linkish',dataset:{recentClear:''},onclick:e=>{try{S.clearRecent(e);}catch(_){}draw(idx);}},'최근 지우기');
   rows.push(h('div',{class:'chip-row',dataset:{recent:''}},h('span',{class:'hand chip-label'},'최근 →'),...recentChips,clear));}
  if(!loaded(prefs)){rows.push(pending('즐겨찾기 기업'));}
  else if(prefs.state==='INVALID'){rows.push(h('p',{class:'reason',dataset:{favorites:'INVALID'}},'이 기기의 관심 기업 기록을 읽을 수 없어 즐겨찾기를 보이지 않습니다 · 설정에서 백업으로 확인하세요'));}
  else{
   const mine=prefs.value.interests.map(id=>chipLink(idx,id,true)).filter(Boolean);
   if(mine.length)rows.push(h('div',{class:'chip-row',dataset:{favorites:'MINE'}},h('span',{class:'hand chip-label'},'★ 즐겨찾기'),...mine));
   else{
    // No personal input: the developer default (feature 1.1.4), shown as such and never written.
    const all=idx.targets.map(id=>chipLink(idx,id,false)).filter(Boolean),extra=all.slice(DEFAULT_SHOWN);
    const row=h('div',{class:'chip-row',dataset:{favorites:'DEFAULT'}},h('span',{class:'hand chip-label',dataset:{defaultLabel:''}},'기본 목록 · 개발자 기본값 · 추천 아님'),...all.slice(0,DEFAULT_SHOWN));
    if(extra.length){const box=h('span',{class:'chip-more',hidden:true},...extra);
     const tog=h('button',{type:'button',class:'linkish','aria-expanded':'false',dataset:{defaultMore:''}},'+'+extra.length+' 더 보기');
     tog.addEventListener('click',()=>{const open=box.hidden;box.hidden=!open;tog.setAttribute('aria-expanded',String(open));tog.textContent=open?'접기':'+'+extra.length+' 더 보기';});
     row.append(box,tog);}
    if(all.length)rows.push(row);}}
  host.replaceChildren(...rows);
  if(!rows.length)host.append(h('p',{class:'reason'},'검색해서 고른 기업은 이 기기에만 최근 검색으로 남습니다'));}
 return host;
}
// One investor story (feature 1.1.3): the module's checked text; Korean is our translation / summary and says so.
function quote(route){
 const host=h('section',{class:'sk home-quote','aria-label':'투자 이야기',dataset:{quote:''}},pending('투자 이야기 · 인물과 출처'));
 ready().then(settled(route.signal,()=>{const Q=window.HomeQuotes;if(!Q)return;const q=Q.pick(quoteId);quoteId=q.id;const story=q.type==='STORY';
  host.dataset.quoteType=q.type;host.dataset.quoteId=q.id;
  host.replaceChildren(
   h('p',{class:'hand quote-kind'},story?'일화 요약 · 직접 인용 아님':'직접 인용',' · ',story?'우리말 요약(자체 작성)':'우리말 번역(자체 번역)'),
   h('blockquote',{class:'quote-ko',lang:'ko'},h('p',null,q.ko)),
   h('p',{class:'quote-en',lang:'en'},'원문 발췌: ',q.headline_en),
   h('p',{class:'quote-who'},'— ',q.speaker.ko),
   h('p',{class:'quote-src'},'출처: ',q.source,q.date?' ('+q.date+')':'',' ',q.url?h('a',{href:q.url,target:'_blank',rel:'noopener noreferrer',dataset:{quoteLink:''}},'원문 보기 ↗'):null));}),()=>{});
 return host;
}
function search(route){
 return h('div',{class:'screen'},
  h('section',{class:'hero'},
   h('h1',{class:'hero-title'},'어떤 기업을 ',h('span',{class:'hl'},'볼까요?')),
   h('svg:svg',{class:'hero-underline',viewBox:'0 0 560 26',preserveAspectRatio:'none','aria-hidden':'true'},h('svg:path',{d:'M8 16 C 120 6, 260 22, 380 12 S 520 8, 552 14'})),
   searchBox(route,{label:h('label',{for:'q',class:'hand hero-label'},'티커 · 회사명 · 한글명으로 검색')}),
   chips(route,h('div',{class:'chip-rows',dataset:{homeChips:''}},pending('최근 · ★ 즐겨찾기 기업'))),
   h('p',{class:'hand hero-aside'},'검색하면 ↓ QGV + 기술적 분석 + 매크로를 한 장에 보여 줌')),
  quote(route));
}

/* ---------------------------------------------------------------- company page */
const na=(text,code)=>h('p',{class:'na',dataset:{na:code||''}},text);
function bar(axis,v,why){
 const row=h('div',{class:'qrow',dataset:{axis,state:ok(v)?'OK':'NA'}},h('b',{class:axis.toLowerCase()+'-text'},axis));
 const svg=h('svg:svg',{class:'qbar '+axis.toLowerCase()+(ok(v)?'':' na'),viewBox:'0 0 100 10',preserveAspectRatio:'none','aria-hidden':'true'},
  h('svg:rect',{class:'qbar-track',x:'0.5',y:'0.5',width:'99',height:'9',rx:'3'}),
  ok(v)?h('svg:rect',{class:'qbar-fill',x:'0.5',y:'0.5',width:String(Math.max(0,Math.min(100,v))*0.99),height:'9',rx:'3'}):null);
 row.append(svg,ok(v)?h('span',{class:'qval'},fmt(v)):h('span',{class:'qval na'},'NA'));
 return why&&!ok(v)?[row,h('p',{class:'reason qwhy',dataset:{why:axis}},axis,' NA · ',why)]:[row];
}
function qgvCard(body,cid,signal){
 const Q=I.qgv;
 Q.page({signal}).then(settled(signal,pg=>{
  if(pg.state!=='READY'){body.replaceChildren(na(Q.reasonText(pg.reason),pg.reason));return;}
  const row=Q.row(pg,cid);if(!row){body.replaceChildren(na('이 기업의 QGV 행이 공개 점수 입력에 없습니다','NO_ROW'));return;}
  const s=row.score,r=row.na_reason;
  const rank=Number.isInteger(row.rank.official)?h('span',null,'순위 ',String(row.rank.official),' / ',String(row.rank.of),' · ',Q.rankLabel(pg)):h('span',{class:'na'},'순위 NA · ',Q.reasonText(r.rank));
  body.replaceChildren(h('div',{class:'qbars',dataset:{qgv:row.id}},...bar('Q',s.q,r.q&&Q.reasonText(r.q)),...bar('G',s.g,r.g&&Q.reasonText(r.g)),...bar('V',s.v,r.v&&Q.reasonText(r.v))),
   h('p',{class:'reason'},'V 출처: ',row.source_label),
   h('p',{dataset:{total:''}},ok(s.total)?['QGV 종합 ',h('b',null,fmt(s.total)),ok(s.v)?'':h('span',{class:'reason'},' · V 미포함')]:h('span',{class:'na'},'QGV 종합 NA · ',Q.reasonText(r.total))),
   h('p',{dataset:{rank:''}},rank));}),
 e=>{if(!signal.aborted&&String(e&&e.message)!=='ABORTED')body.replaceChildren(na('QGV 점수를 계산하지 못했습니다','PAGE_FAILED'));});
}
function macroCard(body,signal){
 I.engines.macro.current().then(settled(signal,c=>{
  const st=I.data.state(MACRO);
  if(!c){body.replaceChildren(na(st.state==='OK'?'공개 매크로 경고등 판정이 없습니다':st.text||'공개 매크로 파일을 읽지 못했습니다',st.state));return;}
  const lines=[c.state&&Object.hasOwn(MACRO_STATE,c.state)?h('p',null,'경고등 판정: ',h('b',null,MACRO_STATE[c.state]),' · 켜진 경고등 ',String(c.lit_count),' / 확인 ',String(c.available_count)):na('확인한 경고등이 없어 판정하지 않았습니다','NO_LIGHTS')];
  if(c.state&&c.low_confidence)lines.push(h('p',{class:'reason'},'확인한 경고등이 적어 신뢰도가 낮습니다'));
  if(st.as_of)lines.push(h('p',{class:'reason'},'공개 자료 기준 ',String(st.as_of).slice(0,10)));
  body.replaceChildren(...lines);}),e=>{if(!signal.aborted)body.replaceChildren(na('매크로 판정을 읽지 못했습니다','MACRO_FAILED'));});
}
function newsCard(body,e,cid,signal){
 const D=I.data,korean=/^\d{6}$/.test(String(e.ticker)),want=LISTS.filter(([k])=>k!=='dart'||korean),ids=[cid];
 Promise.all(want.map(([k])=>D.list(k))).then(settled(signal,got=>{
  const lists={};want.forEach(([k],i)=>{lists[k]=got[i];});
  if(want.every(([k])=>!lists[k])){const st=D.state(want[0][1]);body.replaceChildren(na(st.text||'공개 소식 파일을 읽지 못했습니다',st.state));return;}
  const NS=window.NewsSignals,SD=window.SecDisclosures;let rows=[];
  try{rows=NS.timeline({sec:lists.sec||null,news:lists.news||null,dart:lists.dart||null},{companyIds:ids,dartApi:window.DartDisclosures}).slice(0,5);}catch(_){rows=[];}
  if(!rows.length){body.replaceChildren(na('공개 파일에 이 기업 소식이 없습니다','EMPTY'));return;}
  const text=r=>{try{if(r.source==='SEC'&&r.event)return r.event.form+' · '+SD.classLabel(r.event.classification,false,r.event.items);if(r.event&&r.event.title)return r.event.title;return r.item?r.item.title:'';}catch(_){return r.event?r.event.form||'':'';}};
  body.replaceChildren(h('ul',{class:'news-lines',dataset:{news:''}},...rows.map(r=>h('li',{dataset:{newsItem:r.channel}},
   h('b',null,'[',r.channel==='DISCLOSURE'?'공시 · '+r.source:'뉴스','] '),text(r),' · ',String(r.time||'').slice(0,10)))));}),
 ()=>{if(!signal.aborted)body.replaceChildren(na('공개 소식 파일을 읽지 못했습니다','LIST_FAILED'));});
}
function portfolioCard(body,e,idx,signal){
 const Q=I.qgv,weight=h('p',{class:'reason'},'비중은 포트폴리오 화면에서(가격을 불러온 뒤 이 기기에서 계산)');
 if(e.scope!=='TARGET'){body.replaceChildren(na('TARGET 밖 기업이라 이 기기 보유 기록과 맞춰 보지 않습니다','OUTSIDE_TARGET'),weight);return;}
 I.store.holdings().then(settled(signal,x=>{
  if(x.state==='NOT_AVAILABLE'){body.replaceChildren(na(Q.reasonText(x.reason),x.reason),weight);return;}
  const cat=idx.catalog||null,inst=cat&&Array.isArray(cat.instruments)?cat.instruments.find(i=>i.ticker===e.ticker):null,ref=inst?canonical(inst.security_reference):null;
  const held=!!(ref&&x.snapshot&&Array.isArray(x.snapshot.themes)&&x.snapshot.themes.some(t=>(t.holdings||[]).some(r=>canonical(r.security_reference)===ref&&Number(r.quantity)>0)));
  body.replaceChildren(h('p',{dataset:{held:String(held)}},held?'이 기기 보유 기록 있음':'이 기기 보유 기록 없음'),weight);}),
 ()=>{if(!signal.aborted)body.replaceChildren(na('이 기기 보유 기록을 읽지 못했습니다','HOLDINGS_FAILED'),weight);});
}
// ★ (feature 1.1.4): adds / removes the id in prefs interests on a click; unstarring also leaves the groups (the validator needs it).
function starButton(cid,signal){
 const btn=h('button',{type:'button',class:'chip star','aria-pressed':'false',disabled:true,dataset:{favorite:cid}},'☆ 즐겨찾기'),why=h('span',{class:'reason',dataset:{favoriteWhy:''}});
 const paint=()=>{const p=I.store.prefs();if(!loaded(p)){btn.disabled=true;return;}
  if(p.state==='INVALID'){btn.disabled=true;why.textContent='이 기기의 관심 기업 기록을 읽을 수 없어 바꿀 수 없습니다';return;}
  const on=p.value.interests.includes(cid);btn.disabled=false;btn.setAttribute('aria-pressed',String(on));btn.textContent=on?'★ 즐겨찾기 해제':'☆ 즐겨찾기';};
 btn.addEventListener('click',e=>{const p=I.store.prefs();if(!loaded(p)||p.state==='INVALID')return;const v=p.value,on=v.interests.includes(cid);
  const next={version:1,interests:on?v.interests.filter(x=>x!==cid):[...v.interests,cid],groups:v.groups.map(g=>({id:g.id,name:g.name,members:on?g.members.filter(x=>x!==cid):[...g.members]}))};
  try{I.store.savePrefs(e,next);why.textContent='';}catch(err){why.textContent=String(err&&err.message)==='PREFS_STORAGE_INVALID'?'이 기기의 관심 기업 기록을 읽을 수 없어 바꿀 수 없습니다':'저장하지 못했습니다';}
  paint();});
 ready().then(settled(signal,paint),()=>{});
 return h('span',{class:'star-wrap'},btn,why);
}
function result(route){
 const given=route.params[0],signal=route.signal;
 const name=h('h1',{class:'result-name',dataset:{resultCode:given}},given),facts=h('div',{class:'result-facts',dataset:{resultFacts:''}},pending('회사명 · 거래소 · SIC · 유형'));
 // The ★ is drawn at once and stays off until the layer is ready and the id resolved (then starButton takes its place).
 const star=h('span',{class:'star-wrap'},h('button',{type:'button',class:'chip star','aria-pressed':'false',disabled:true,dataset:{favorite:''}},'☆ 즐겨찾기'));
 const head=h('section',{class:'result-head'},h('span',{class:'stamp'},'검색 결과'),name,facts,star);
 const bodies={qgv:h('div',{class:'card-body'},pending('Q · G · V 막대, 종합 점수 · 순위')),technical:h('div',{class:'card-body'},na('가격 이력은 기술적 분석 화면에서 [불러오기]를 눌러야 계산합니다','PRICE_ON_CLICK')),
  macro:h('div',{class:'card-body'},pending('경고등 판정 · 공개 자료 기준')),news:h('div',{class:'card-body'},pending('공시 · 뉴스 다섯 줄')),portfolio:h('div',{class:'card-body'},pending('이 기기 보유 기록'))};
 const page=h('div',{class:'screen'},
  searchBox(route,{label:h('label',{for:'q',class:'sr-only'},'다른 기업 검색')}),head,
  h('div',{class:'grid-3'},
   card('1. QGV',{shadow:'q',id:'qgv',link:href('qgv')},bodies.qgv,more('리더보드 · 가중치 · 스탯창')),
   card('2. 기술적 분석',{shadow:'g',id:'technical',link:href('technical')},bodies.technical,more('시나리오 · 패턴 · 내 노트')),
   card('3. 매크로',{shadow:'v',id:'macro',link:href('macro')},bodies.macro,more('근거 · 조건 · 확률'))),
  h('div',{class:'grid-2'},
   card(h('span',{class:'hl'},'4. 이 기업 소식'),{id:'news'},bodies.news,more('뉴스에서 전체 보기',href('news'))),
   card('5. 내 포트폴리오에서',{id:'portfolio'},bodies.portfolio,more('포트폴리오에서 보기',href('portfolio')))));
 companyIndex().then(settled(signal,idx=>{
  const e=idx.find(given);
  if(!e){
   name.textContent=given;star.remove();
   facts.replaceChildren(h('p',{class:'not-found',role:'status',dataset:{notFound:''}},'이 이름의 기업을 찾지 못했습니다'),missingLine(idx)||'');
   for(const k of['qgv','macro','news','portfolio'])bodies[k].replaceChildren(na('기업을 찾지 못해 값이 없습니다','NOT_FOUND'));
   return;}
  const cid=e.canonical_id;I.selection.set(cid);
  name.textContent=idx.title(e);
  const bits=[e.ticker,idx.code(e),idx.member(e)].filter(Boolean),extra=h('span',{class:'facts-more'});
  facts.replaceChildren(h('p',{class:'facts-line'},bits.join(' · '),extra));star.replaceWith(starButton(cid,signal));
  I.data.ready().then(settled(signal,()=>{const add=classOf(cid);if(add.length)extra.append(...add.map(t=>' · '+t));}),()=>{});
  qgvCard(bodies.qgv,cid,signal);macroCard(bodies.macro,signal);newsCard(bodies.news,e,cid,signal);portfolioCard(bodies.portfolio,e,idx,signal);}),
 ()=>{if(!signal.aborted)facts.replaceChildren(na('기업 목록을 불러오지 못했습니다','INDEX_FAILED'));});
 return page;
}
// SIC group and investment type, only from the published files (company-classification.json, company-types-pricefree.json).
function classOf(id){
 const out=[],CS=window.ClassificationScreens,cls=CS?I.data.get(CS.FILE):null,rec=cls&&CS.record?CS.record(cls,id):null,ind=rec?rec.industry:null;
 if(ind&&ind.state!=='NOT_AVAILABLE'&&ind.sic){const g=cls.data.industry_config.groups.find(x=>x.id===ind.group);out.push('SIC '+ind.sic+(g?' '+g.name:''));}
 const types=I.data.get('company-types-pricefree.json'),t=types&&types.data&&types.data.companies&&Object.hasOwn(types.data.companies,id)?types.data.companies[id]:null,C=window.TypeConfigDefaults;
 if(t&&t.state!=='NOT_AVAILABLE'&&t.memberships&&C&&C.mixing){
  // type_config/1 mixing rule (company-screen.js selectTypes): membership ≥ minimum, at most maximum_types, exclusive pairs, config order.
  const m=C.mixing,order=C.types.map(x=>x.id),picked=[];
  for(const k of TYPES.filter(k=>ok(t.memberships[k])&&t.memberships[k]>=m.minimum_membership).sort((a,b)=>t.memberships[b]-t.memberships[a]||order.indexOf(a)-order.indexOf(b))){
   if(picked.length>=m.maximum_types)break;if(m.exclusive_pairs.some(([x,y])=>(k===x&&picked.includes(y))||(k===y&&picked.includes(x))))continue;picked.push(k);}
  if(picked.length)out.push('유형: '+picked.map(k=>(C.types.find(x=>x.id===k)||{name:k}).name).join(' · '));}
 return out;
}
register('search',search);register('company',result);
})();
