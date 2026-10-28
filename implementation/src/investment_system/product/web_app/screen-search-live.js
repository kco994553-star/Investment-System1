/* 0. 기업 검색 · 검색 결과, the part that runs after IS2.ready (feature 1.1.1–1.1.4, P2-1; P1_DATA_LAYER.md §1.1 screen-file rule).
   screen-search.js draws the first-paint skeleton (hero, search box, company header, card frames with pending blocks) and, once
   IS2.ready resolved, hands its regions to IS2.searchLive.home(route, refs) / company(route, refs) from this file (loader.js
   LOAD_ORDER, after engines.js). This file only fills those regions in place: the input element is never rebuilt, route.signal
   ends every late value, and nothing touches the layer while the file loads (it only puts IS2.searchLive).
   - The search box is the shared company search (search-part-live.js, DC-23: Universe504 only, ticker + English name, in
     memory). A chosen option is saved as a recent search with that click (store.pushRecent, one action per event; a refused or
     failed save still navigates); a submit's single exact match opens its page and saves nothing; no match stays on the page.
   - Company index (EntitySearch, reused) for the chips and the company page (never for the search box), built from the three
     static public files: the TARGET catalog (DeviceWatchlist.identities), the fixed Universe504 code list (universe-codes.json)
     and the reviewed names table (company-names-ko.json, also the code → company_id links). A missing file leaves its part out.
   - Home: recent chips (titles from the index, unknown keys skipped, 최근 지우기), favorites (store prefs interests) or, without
     any, the developer default (P21-DEFAULTS: the catalog's 19 companies, labelled as such, never written; also shown when the
     stored favorites cannot be read, so device storage never hides it; HOME-DEFAULT-V0 (c), owner 2026-10-28: it stays until a
     confirmed TARGET v1 is published as a public file, then that list replaces it; it is not a QGV or public TARGET list,
     DC-24), one verified investor story (home-quotes.js).
   - Company page: after the index the title, ticker, exchange code, membership (Universe504 or not, DC-24), SIC group and investment type (public files,
     only when present); the ★ toggle (store prefs, a click); the five cards from the layer (QGV page row with the score file's
     refresh time and calc_version, DC-22; macro lights, public
     filing / news lists, device holdings yes / no) or NA with the reason. No price and no price-derived value; the technical card
     asks for nothing (prices only on the technical screen's click). The resolved id becomes IS2.selection (RAM). Unknown id: a
     fixed sentence, no guess, no values. */
(function(){
'use strict';
const I=window.IS2,{h,href,parts:{pending}}=I;
const CATALOG='actual-catalog.json',NAMES='company-names-ko.json',MACRO='macro-screen.json',DEFAULT_SHOWN=8;
const LISTS=[['sec','sec-disclosures.json'],['news','news-signals.json'],['dart','dart-disclosures.json']];
const MACRO_STATE={NORMAL:'정상',WARNING:'경고',CRISIS:'위기'};// MacroLights STATE_LABEL (not exported)
// The investment types the company page names (company-screen.js TYPES), mixed by type_config/1.
const TYPES=['growth','quality','cyclical','defensive'];
const ok=v=>typeof v==='number'&&Number.isFinite(v);
const fmt=v=>new Intl.NumberFormat('ko-KR',{minimumFractionDigits:1,maximumFractionDigits:1}).format(v);
const settled=(signal,fn)=>v=>{if(!signal.aborted)fn(v);};
const canonical=v=>Array.isArray(v)?'['+v.map(canonical).join(',')+']':v&&typeof v==='object'?'{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canonical(v[k])).join(',')+'}':JSON.stringify(v);

/* ---------------------------------------------------------------- company index (static files only) */
let indexP=null,quoteId=null;
function companyIndex(){
 if(!indexP){indexP=build();indexP.then(x=>{if(x.missing.length)indexP=null;},()=>{indexP=null;});}
 return indexP;}
async function build(){
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
 // Membership names Universe504 only: TARGET v0 (the catalog) has nothing to do with QGV and is not shown as a membership (DC-24).
 const member=e=>e.scope==='UNIVERSE504'||codeOf.has(e.canonical_id)?'Universe504':'Universe504 밖';
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

/* ---------------------------------------------------------------- search box: the shared part (search-part-live.js, DC-23) */
// A chosen option (pointer click, or Enter on an option the arrow keys made active) is saved as a recent search with that click
// (store.pushRecent, one action per event; a refused or failed save still navigates); a submit's single exact match opens its
// page and saves nothing; a submit without a match stays (the part says so in the list).
const attach=(route,b)=>I.searchPart.attach(route,b,{onPick:(ev,e,{chosen})=>{if(chosen)try{I.store.pushRecent(ev,'COMPANY:'+e.id);}catch(_){}location.hash=href('company',e.id);}});

/* ---------------------------------------------------------------- home */
function chipLink(idx,id,star,mine){const e=idx.resolve(id);return e?h('a',{class:mine?'chip mine':'chip',href:href('company',e.canonical_id),dataset:{chip:e.canonical_id}},star?'★ ':'',idx.title(e)):null;}
function chips(route,host){
 const signal=route.signal;
 companyIndex().then(settled(signal,idx=>draw(idx)),()=>{});
 function draw(idx,cleared){
  const S=I.store,recent=S.recent(),prefs=S.prefs(),rows=[];
  const keys=Array.isArray(recent)?recent.filter(k=>k.startsWith('COMPANY:')).map(k=>k.slice(8)):[];
  const recentChips=keys.map(id=>chipLink(idx,id,false,true)).filter(Boolean);
  if(recentChips.length){
   const clear=h('button',{type:'button',class:'linkish',dataset:{recentClear:''},onclick:e=>{let done=false;try{S.clearRecent(e);done=true;}catch(_){}draw(idx,done);}},'최근 지우기');
   rows.push(h('div',{class:'chip-row',dataset:{recent:''}},h('span',{class:'hand chip-label'},'최근 →'),...recentChips,clear));}
  if(!loaded(prefs)){rows.push(pending('즐겨찾기 기업'));}
  else{
   const invalid=prefs.state==='INVALID';
   if(invalid)rows.push(h('p',{class:'reason',dataset:{favorites:'INVALID'}},'이 기기의 관심 기업 기록을 읽을 수 없어 즐겨찾기를 표시하지 않습니다 · 설정의 백업에서 기록을 확인하세요'));
   const mine=invalid?[]:prefs.value.interests.map(id=>chipLink(idx,id,true,true)).filter(Boolean);
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
  if(cleared)rows.unshift(h('p',{class:'reason',role:'status',dataset:{recentCleared:''}},'최근 검색을 지웠습니다'));
  host.replaceChildren(...rows);
  if(!rows.length)host.append(h('p',{class:'reason'},'검색해서 고른 기업은 이 기기에만 최근 검색으로 남습니다'));
  // The pressed 최근 지우기 is gone with its row: the focus stays in this block instead of falling back to the page.
  if(cleared)host.focus({preventScroll:true});}
}
// One investor story (feature 1.1.3): the module's checked text; Korean is our translation / summary and says so.
function quote(host){
 const Q=window.HomeQuotes;if(!Q)return;const q=Q.pick(quoteId);quoteId=q.id;const story=q.type==='STORY';
 host.dataset.quoteType=q.type;host.dataset.quoteId=q.id;
 host.replaceChildren(
  h('p',{class:'hand quote-kind'},story?'일화 요약 · 직접 인용 아님':'직접 인용',' · ',story?'우리말 정리(자체 작성)':'우리말 번역(자체 번역)'),
  h('blockquote',{class:'quote-ko',lang:'ko'},h('p',null,q.ko)),
  h('p',{class:'quote-en',lang:'en'},'원문 발췌: ',q.headline_en),
  h('p',{class:'quote-who'},'— ',q.speaker.ko),
  h('p',{class:'quote-src'},'출처: ',q.source,q.date?' ('+q.date+')':'',' ',q.url?h('a',{href:q.url,target:'_blank',rel:'noopener noreferrer',dataset:{quoteLink:''}},'원문 보기 ↗'):null));
}
function home(route,{box,chips:host,quote:story}){attach(route,box);chips(route,host);quote(story);}

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
// The score file's refresh time (its as_of, date and time in UTC) and calc_version under the QGV card (DC-22), in every state.
let SF=null;
const stamp=t=>{const d=Date.parse(t);return Number.isFinite(d)?(SF||(SF=new Intl.DateTimeFormat('ko-KR',{year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false,timeZone:'UTC'}))).format(d)+' UTC':null;};
const basisLine=pg=>h('p',{class:'reason',dataset:{qgvBasis:''}},'점수 갱신 ',stamp(pg.as_of)||'없음',' · 계산 버전 ',pg.calc_version||'없음');
function qgvCard(body,cid,signal){
 const Q=I.qgv;
 Q.page({signal}).then(settled(signal,pg=>{
  if(pg.state!=='READY'){body.replaceChildren(na(Q.reasonText(pg.reason),pg.reason),basisLine(pg));return;}
  const row=Q.row(pg,cid);if(!row){body.replaceChildren(na('이 기업의 QGV 행이 공개 점수 입력에 없습니다','NO_ROW'),basisLine(pg));return;}
  const s=row.score,r=row.na_reason;
  const rank=Number.isInteger(row.rank.official)?h('span',null,'순위 ',String(row.rank.official),' / ',String(row.rank.of),' · ',Q.rankLabel(pg)):h('span',{class:'na'},'순위 NA · ',Q.reasonText(r.rank));
  body.replaceChildren(h('div',{class:'qbars',dataset:{qgv:row.id}},...bar('Q',s.q,r.q&&Q.reasonText(r.q)),...bar('G',s.g,r.g&&Q.reasonText(r.g)),...bar('V',s.v,r.v&&Q.reasonText(r.v))),
   h('p',{class:'reason'},'V 출처: ',row.source_label),
   h('p',{dataset:{total:''}},ok(s.total)?['QGV 종합 ',h('b',null,fmt(s.total)),ok(s.v)?'':h('span',{class:'reason'},' · V 미포함')]:h('span',{class:'na'},'QGV 종합 NA · ',Q.reasonText(r.total))),
   h('p',{dataset:{rank:''}},rank),basisLine(pg));}),
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
   h('b',null,'[',r.channel==='DISCLOSURE'?'공시 · '+r.source:'뉴스','] '),text(r),' · ',h('span',{class:'nobr'},String(r.time||'').slice(0,10))))));}),
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
// The ★ toggle's name stays 즐겨찾기 (aria-pressed carries the state); the glyph and 해제 are visible only.
const starText=on=>[h('span',{'aria-hidden':'true'},on?'★ ':'☆ '),'즐겨찾기',on?h('span',{'aria-hidden':'true'},' 해제'):''];
// ★ (feature 1.1.4): adds / removes the id in prefs interests on a click; unstarring also leaves the groups (the validator needs it).
function starButton(cid){
 const btn=h('button',{type:'button',class:'chip star','aria-pressed':'false',disabled:true,dataset:{favorite:cid}},...starText(false)),why=h('span',{class:'reason',dataset:{favoriteWhy:''}});
 const paint=()=>{const p=I.store.prefs();if(!loaded(p)){btn.disabled=true;return;}
  if(p.state==='INVALID'){btn.disabled=true;why.textContent='이 기기의 관심 기업 기록을 읽을 수 없어 바꿀 수 없습니다';return;}
  const on=p.value.interests.includes(cid);btn.disabled=false;btn.setAttribute('aria-pressed',String(on));btn.replaceChildren(...starText(on));};
 btn.addEventListener('click',e=>{const p=I.store.prefs();if(!loaded(p)||p.state==='INVALID')return;const v=p.value,on=v.interests.includes(cid);
  const next={version:1,interests:on?v.interests.filter(x=>x!==cid):[...v.interests,cid],groups:v.groups.map(g=>({id:g.id,name:g.name,members:on?g.members.filter(x=>x!==cid):[...g.members]}))};
  try{I.store.savePrefs(e,next);why.textContent='';}catch(err){why.textContent=String(err&&err.message)==='PREFS_STORAGE_INVALID'?'이 기기의 관심 기업 기록을 읽을 수 없어 바꿀 수 없습니다':'저장하지 못했습니다';}
  paint();});
 paint();
 return h('span',{class:'star-wrap'},btn,why);
}
// refs = the skeleton's {box, given, name, facts, star, bodies}; only these regions change.
function company(route,{box,given,name,facts,star,bodies}){
 const signal=route.signal;attach(route,box);
 companyIndex().then(settled(signal,idx=>{
  const e=idx.find(given);
  if(!e){
   name.textContent=given;star.remove();
   facts.replaceChildren(I.parts.mascot('plain'),h('p',{class:'not-found',role:'status',dataset:{notFound:''}},'이 이름의 기업을 찾지 못했습니다'),missingLine(idx)||'');
   for(const k of['qgv','macro','news','portfolio'])bodies[k].replaceChildren(na('기업을 찾지 못해 값이 없습니다','NOT_FOUND'));
   return;}
  const cid=e.canonical_id;I.selection.set(cid);
  const title=idx.title(e);name.textContent=title;
  const bits=[e.ticker&&!title.includes(e.ticker)?e.ticker:null,idx.code(e),idx.member(e)].filter(Boolean),extra=h('span',{class:'facts-more'});
  const ended=I.searchPart.LISTING_ENDED[idx.code(e)];// display only (search-part-live.js table; LISTING-ENDED-CODE pending)
  facts.replaceChildren(h('p',{class:'facts-line'},...bits.flatMap((b,i)=>[i?' · ':'',h('span',{class:'nobr'},b)]),extra),
   ended?h('p',{class:'reason',dataset:{listingEnded:ended.effective}},'상장 종료 ',ended.effective,' · 점수 없음'):'');star.replaceWith(starButton(cid));
  I.data.ready().then(settled(signal,()=>{const add=classOf(cid);if(add.length)extra.append(...add.map(t=>' · '+t));}),()=>{});
  qgvCard(bodies.qgv,cid,signal);macroCard(bodies.macro,signal);newsCard(bodies.news,e,cid,signal);portfolioCard(bodies.portfolio,e,idx,signal);}),
 ()=>{if(!signal.aborted)facts.replaceChildren(na('기업 목록을 불러오지 못했습니다','INDEX_FAILED'));});
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
I.searchLive=Object.freeze({home,company});
})();
