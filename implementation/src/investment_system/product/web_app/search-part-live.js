/* The shared company search (DC-23, owner 2026-10-27): the one part every screen that picks a company uses. parts.js
   searchBox(id, label) draws its first-paint half; IS2.searchPart.attach(route, box, {onPick}) takes it over after IS2.ready
   (loader.js LOAD_ORDER, after the layer and before the screens' logic files). Nothing here touches the layer while the file
   loads (it only puts IS2.searchPart).
   - Scope: Universe504 only, from public files read once per page and kept in memory: the fixed code list (universe-codes.json,
     IS2.data.universe) and the reviewed names table (company-names-ko.json: the English SEC name and the code → TARGET
     company_id link). Keystrokes search that memory: no request per keystroke. A failed file is read again on the next attach.
   - Keys: ticker (case, '.', '-' and spaces ignored; a full code such as NYSE:FIX too) and the English company name. Korean
     names, aliases and TARGET companies outside Universe504 are not searched (owner rule); Korean text gets a fixed hint.
     Order: exact ticker or code, ticker prefix, name prefix, a name word prefix, ticker part, name part; ties by ticker. At most
     8 options; no price, cap, score or rank.
   - A listing-ended code (LISTING_ENDED below) is still found and can be chosen; its option says 상장 종료 and the date.
   - ARIA combobox / listbox (P2-1 pattern): arrows move (Home / End jump), Enter submits the form and the selection runs in that
     click, Escape closes (a second Escape clears). IME safe: no key handling while composing; the list repaints on every input
     event. Hover only highlights: the submit takes an option only when the arrow keys chose it. A submit without one takes the
     single exact match; with none it says so in the list and goes nowhere. A submit before the list is there (also one pressed
     before IS2.ready) runs once it is, with the text then in the box (never as a chosen option).
   - onPick(event, entry, {chosen}): the screen decides what a pick does (the home and company page save a chosen option as a
     recent search with that click and open #/company/<id>; a base-company screen sets its base). entry = {id, code, ticker, en,
     ended}: id = the TARGET company_id linked to the code, else the code. */
(function(){
'use strict';
const I=window.IS2,{h}=I;
const MAX=8,NAMES='company-names-ko.json';
// Listing-ended codes, display only: the same codes and dates as sec_universe_shares.LISTING_ENDED_CODES (the server table);
// implementation/tests/test_web_app_search_part.py keeps them equal. A public reason code is pending (LISTING-ENDED-CODE).
const LISTING_ENDED=Object.freeze({'NASDAQ:WBD':Object.freeze({effective:'2026-10-06'})});
const HANGUL=/[ᄀ-ᇿ㄰-㆏가-힯]/;
const VENUE=/^(NYSE|NASDAQ|BATS):[A-Z0-9][A-Z0-9.\-]{0,15}$/;
const tickerKey=s=>String(s).toUpperCase().replace(/[\s.\-\/]/g,'');
const nameKey=s=>String(s).toLowerCase().replace(/[^a-z0-9&]+/g,' ').trim();

/* ---------------------------------------------------------------- the index (memory, once per page) */
let indexP=null;
function index(){
 if(!indexP){indexP=build();indexP.then(x=>{if(x.missing.length)indexP=null;},()=>{indexP=null;});}
 return indexP;}
async function build(){
 const D=I.data,[codes,names]=await Promise.all([D.universe(),D.static(NAMES)]);
 const list=Array.isArray(codes)?codes.filter(c=>VENUE.test(c)):[],links=new Map();
 if(names)for(const[c,id]of names.codes())if(id)links.set(c,id);
 const entries=list.map(code=>{const rec=names?names.get(code):null,ticker=code.slice(code.indexOf(':')+1);
  const en=rec&&rec.en_name?rec.en_name+(rec.class_label?' Class '+rec.class_label:''):null;
  return Object.freeze({id:links.get(code)||code,code,ticker,en,ended:LISTING_ENDED[code]||null,t:tickerKey(ticker),n:en?nameKey(en):''});});
 const byId=new Map();for(const e of entries){byId.set(e.id,e);byId.set(e.code,e);}
 function rank(e,raw,T,N){
  if(e.code===raw||e.t===T)return 0;if(T&&e.t.startsWith(T))return 1;if(raw.includes(':')&&e.code.startsWith(raw))return 1;
  if(!e.n||!N)return T.length>=2&&e.t.includes(T)?4:null;
  if(e.n.startsWith(N))return 2;if((' '+e.n).includes(' '+N))return 3;if(T.length>=2&&e.t.includes(T))return 4;if(N.length>=3&&e.n.includes(N))return 5;return null;}
 function search(q){const raw=String(q).trim().toUpperCase(),T=tickerKey(raw),N=nameKey(raw);if(!raw||HANGUL.test(raw))return[];
  const out=[];for(const e of entries){const r=rank(e,raw,T,N);if(r!==null)out.push({e,r});}
  return out.sort((a,b)=>a.r-b.r||(a.e.ticker<b.e.ticker?-1:a.e.ticker>b.e.ticker?1:0)).map(x=>x.e);}
 // The single exact match of a query (ticker or code, else the full English name), else null.
 function exact(q){const raw=String(q).trim().toUpperCase(),T=tickerKey(raw),N=nameKey(raw);if(!raw)return null;
  const a=entries.filter(e=>e.code===raw||e.t===T);if(a.length===1)return a[0];if(a.length)return null;
  const b=N?entries.filter(e=>e.n===N):[];return b.length===1?b[0]:null;}
 const missing=[!list.length&&'Universe504 목록',!names&&'영문 회사명 표'].filter(Boolean);
 return Object.freeze({search,exact,get:id=>byId.get(id)||null,title:e=>e.en?e.ticker+' · '+e.en:e.ticker,size:entries.length,missing:Object.freeze(missing)});
}

/* ---------------------------------------------------------------- the combobox on the skeleton's input */
// b = parts.searchBox(...): {input, list, status, note, anchor, pre, submit}. Its 불러오는 중 listener stops (pre); this one takes over.
function attach(route,b,{onPick}){
 const signal=route.signal,{input,list,status,note,anchor}=b,S={hits:[],active:-1,key:false,composing:false,idx:null,pend:!!b.later},base=input.id;
 b.pre.abort();b.later=false;
 const say=t=>{if(status.textContent!==t)status.textContent=t;};
 const msg=(state,text)=>h('li',{class:'search-msg',role:'presentation',dataset:{searchState:state}},text);
 function setActive(i,scroll=true){const opts=[...list.querySelectorAll('[role=option]')];S.active=opts.length?Math.max(-1,Math.min(opts.length-1,i)):-1;
  opts.forEach((o,k)=>o.setAttribute('aria-selected',String(k===S.active)));
  if(S.active>=0){input.setAttribute('aria-activedescendant',opts[S.active].id);if(scroll)opts[S.active].scrollIntoView({block:'nearest'});}else input.removeAttribute('aria-activedescendant');}
 function show(open){list.hidden=!open;input.setAttribute('aria-expanded',String(open));if(!open){S.hits=[];setActive(-1);}}
 function option(e,i){
  return h('li',{id:base+'-opt-'+i,class:'search-opt',role:'option','aria-selected':'false',dataset:{entityKey:'COMPANY:'+e.id,entityId:e.id,code:e.code},
   onmousedown:ev=>ev.preventDefault(),onmousemove:()=>{S.key=false;if(S.active!==i)setActive(i,false);},onclick:ev=>pick(ev,e,true)},
   h('b',{class:'opt-name'},S.idx.title(e)),
   h('span',{class:'opt-sub'},e.code,' · Universe504',e.ended?h('span',{class:'opt-ended',dataset:{listingEnded:e.ended.effective}},' · 상장 종료 ',e.ended.effective,' · 점수 없음'):null));}
 function paint(){
  const q=input.value.trim();if(!q){list.replaceChildren();show(false);say('');return;}
  if(!S.idx){S.hits=[];list.replaceChildren(msg('loading','불러오는 중'));show(true);setActive(-1);say('검색 목록 불러오는 중');return;}
  if(HANGUL.test(q)){S.hits=[];list.replaceChildren(msg('hangul','티커나 영문 회사명으로 찾아 주세요'));show(true);setActive(-1);say('티커나 영문 회사명으로 찾아 주세요');return;}
  const keep=S.active>=0&&S.hits[S.active]?S.hits[S.active].code:null;
  S.hits=S.idx.search(q).slice(0,MAX);
  list.replaceChildren(...(S.hits.length?S.hits.map(option):[msg('empty','일치하는 기업이 없습니다 · Universe504 안에서만 찾습니다')]));
  show(true);setActive(keep?S.hits.findIndex(x=>x.code===keep):-1);say(S.hits.length?'찾은 기업 '+S.hits.length+'곳':'일치하는 기업이 없습니다');}
 function pick(ev,e,chosen){if(ev)ev.preventDefault();show(false);onPick(ev,e,{chosen});}
 // The form's default button (the skeleton's click handler calls this): a click, or Enter in the input (implicit submission).
 b.submit=ev=>{const q=input.value.trim();if(!q)return;if(!S.idx){S.pend=true;return;}
  if(S.key&&S.active>=0&&S.hits[S.active]){pick(ev,S.hits[S.active],true);return;}
  const one=HANGUL.test(q)?null:S.idx.exact(q);
  if(one){pick(ev,one,false);return;}
  paint();input.focus({preventScroll:true});};
 input.addEventListener('compositionstart',()=>{S.composing=true;},{signal});
 input.addEventListener('compositionend',()=>{S.composing=false;paint();},{signal});
 input.addEventListener('input',paint,{signal});
 input.addEventListener('keydown',e=>{
  if(e.isComposing||S.composing||e.keyCode===229)return;
  const n=S.hits.length,open=!list.hidden;
  if((e.key==='ArrowDown'||e.key==='ArrowUp')&&n&&open){e.preventDefault();S.key=true;setActive(S.active<0?(e.key==='ArrowDown'?0:n-1):(S.active+(e.key==='ArrowDown'?1:n-1))%n);}
  else if((e.key==='Home'||e.key==='End')&&n&&open&&S.active>=0){e.preventDefault();S.key=true;setActive(e.key==='Home'?0:n-1);}
  else if(e.key==='Escape'&&(open||input.value)){e.preventDefault();if(open)show(false);else{input.value='';paint();}}},{signal});
 input.addEventListener('focus',()=>{if(input.value.trim())paint();
  if(window.matchMedia&&window.matchMedia('(max-width:720px)').matches){const top=input.getBoundingClientRect().top+window.scrollY-12;setTimeout(()=>{if(!signal.aborted&&document.activeElement===input)window.scrollTo({top:Math.max(0,top),behavior:'auto'});},60);}},{signal});
 // The list is hidden when the focus leaves the box; the highlighted option stays chosen (a browser that does not focus a clicked
 // button blurs the input before the 검색 click). Escape and an emptied box clear it.
 anchor.addEventListener('focusout',()=>{setTimeout(()=>{if(!signal.aborted&&!anchor.contains(document.activeElement)){list.hidden=true;input.setAttribute('aria-expanded','false');}},0);},{signal});
 paint();// text typed before now: 불러오는 중 until the index, then the options
 index().then(idx=>{if(signal.aborted)return;S.idx=idx;
  note.replaceChildren(idx.missing.length?h('p',{class:'reason',dataset:{indexMissing:''}},'일부 목록을 읽지 못했습니다(',idx.missing.join(' · '),') · 읽은 목록으로만 찾습니다'):'');paint();
  if(S.pend){S.pend=false;S.key=false;b.submit(null);}},()=>{});
}

I.searchPart=Object.freeze({index,attach,LISTING_ENDED});
})();
