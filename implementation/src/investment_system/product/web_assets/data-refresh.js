/* Public data refresh: the '자료 새로고침' button (FRONTEND_DATA_CONTRACT.md §2-3 rule R; defects D1, D2, D5, D6).
   This module owns the in-tab copy of the public, price-free publication. The file readers are the existing ones
   (PublicScreens, ClassificationScreens, Qgv2Inputs/SecQgv2, SecReported, SecDisclosures, NewsSignals, DartDisclosures,
   SecUniverseShares, MacroEvidence); their own requests and cache options go through unchanged, only the HTTP status is noted per file.
   - load(view): the page-open read of the core files. list(view,key), shares(view), financials(view): the lazy reads (filing /
     news / DART lists, sec-universe-shares.json, dart-financials.json), read once per publication and shared by every screen,
     so the 4.2 list and the 4.3 tree example show the same file (D6).
   - refresh(): the user-pressed re-read of the whole set. All or nothing: when any file fails to read (network, HTTP error,
     invalid content, newer data format) nothing is replaced, every screen keeps the old values and the bar says '갱신 실패'
     with the old basis time. Otherwise the new set is handed to the app at once (attach hooks.apply), the open screen is
     repainted without re-mounting private parts, and window receives the 'public-data-updated' CustomEvent so that every
     calculation memo drops the old inputs (D1).
   - rejudge(): no network. When the clock passes a boundary of a file's own freshness rule (sec-qgv2 / sec-universe-shares rows:
     acquired_at + the file's stale_after_seconds; other files: as_of + stale_after_seconds), the same readers recompute the row
     states from the text already read and the open screen is repainted (D2). It runs every minute, when the tab is shown again,
     after a screen change, and inside refresh() when there is no new publication.
   - A FULL screen drawn again by refresh() or rejudge() keeps the user's view state (scroll, focus, open details, filter / sort /
     search fields, the chosen view button); only the values are new (captureView / restoreFields / restoreView, G2).
   - status(file) / readText(file): a failed read (network, HTTP n, invalid, newer format) and a file that is not published
     (HTTP 404) never get the same words (D5).
   Never: a request to the private Worker or Google Sheets, a storage write, a change to a user setting or a Cache Storage
   entry. While DataRefresh repaints a screen, quiet() is true: the app skips its own device quote collection then; the shared
   QgvScores.pageResult that the leaderboard, V panel and stat radar recompute on the new inputs reads device prices from RAM only
   (guardPrices below). */
(function(root,factory){const api=factory(root);if(typeof module==='object'&&module.exports)module.exports=api;else root.DataRefresh=api;})(typeof globalThis==='object'?globalThis:this,function(g){
'use strict';
const EVENT='public-data-updated',TICK=60000;
const QGV2='sec-qgv2.json',SHARES='sec-universe-shares.json',REPORTED='sec-public-inputs.json',FIN='dart-financials.json';
const LISTS=Object.freeze({sec:'sec-disclosures.json',news:'news-signals.json',dart:'dart-disclosures.json'});
const RAW=new Set([QGV2,SHARES]);
// After a new set: screens that mount nothing private are rendered again; the app repaints its score screens in place
// (hooks.inPlace); screens holding device work (charts, editors, reports, settings forms) get a notice and a redraw button.
const FULL=new Set(['qgv','thirteenf','news','watchlist','macro','tree','system','companies','entity']),NONE=new Set(['home','brief','research','lab-13f']);
const object=v=>v!==null&&typeof v==='object'&&!Array.isArray(v),finite=v=>typeof v==='number'&&Number.isFinite(v);
let view=null,hooks={},gen=null,seq=0,busy=false,initializing=false,quiet=false,judgedAt=0,timer=0,last={state:'IDLE',at:null,failed:[],changed:[],previous:null,repaint:null};
function fresh(){return{id:++seq,checked_at:null,files:{},screens:{},reported:null,raw:{},bounds:{},lists:{},listValues:{},shares:null,sharesDir:undefined,financials:null};}
function current(){if(!gen)gen=fresh();return gen;}
const nowIso=()=>new Date(Date.now()).toISOString();
function nameOf(input){try{const u=String(object(input)&&typeof input.url==='string'?input.url:input);return u.split(/[?#]/)[0].split('/').pop();}catch(_){return '';}}
// A view for the existing readers: its request is the reader's own (same URL and init), only the status is noted.
function recorder(win){
 const base=win.fetch,seen=new Map(),raw=new Map();
 const tap=(input,init)=>{const name=nameOf(input);return Promise.resolve().then(()=>base.call(win,input,init)).then(r=>{seen.set(name,r.status);if(RAW.has(name)&&r.ok&&typeof r.clone==='function')raw.set(name,r.clone().text().catch(()=>null));return r;},e=>{seen.set(name,0);throw e;});};
 return{seen,raw,view:proxy(win,tap)};
}
// A view that serves text already read (re-judging). It never reaches the network.
function local(win,text){return proxy(win,()=>Promise.resolve(new win.Response(text,{status:200,headers:{'Content-Type':'application/json'}})));}
// The window with only its request function replaced; other window functions keep the window as `this`.
function proxy(win,request){return new Proxy(win,{get(t,k){if(k==='fetch')return request;const v=Reflect.get(t,k);return typeof v==='function'&&typeof k==='string'&&/^[a-z]/.test(k)?v.bind(t):v;}});}
function outcome(name,ok,rec,newer){
 if(ok)return{state:'OK',why:null,http:rec.seen.get(name)??null};const http=rec.seen.get(name);
 if(newer)return{state:'FAILED',why:'SCHEMA_NEWER',http:http??null};
 if(http===undefined)return{state:'NOT_READ',why:null,http:null};
 if(http===404)return{state:'NOT_PUBLISHED',why:null,http};
 return{state:'FAILED',why:http===0?'NETWORK':http>=200&&http<300?'INVALID':'HTTP',http:http||null};
}
const info=(o,p)=>({...o,as_of:object(p)&&typeof p.as_of==='string'?p.as_of:null});
async function keepRaw(rec,G){for(const[name,p]of rec.raw){const text=await p;if(typeof text!=='string'||!G.files[name]||G.files[name].state!=='OK')continue;G.raw[name]=text;try{G.bounds[name]=rowBounds(JSON.parse(text),name);}catch(_){delete G.raw[name];}}}
// sec-universe-shares.json as the app's search / Universe page directory (same shape as app.js ensureUniverseDirectory).
function directory(x,error){if(x)return{state:'READY',as_of:x.as_of,records:x.publicShares};if(!error)return{state:'NOT_AVAILABLE',reason:'SEC_UNIVERSE_SHARES_NOT_PUBLISHED'};
 const m=String(error&&error.message);return{state:'NOT_AVAILABLE',reason:['SEC_UNIVERSE_SHARES_INVALID','SEC_UNIVERSE_SHARES_SCHEMA_NEWER'].includes(m)?m:'SEC_UNIVERSE_SHARES_UNAVAILABLE'};}
async function readCore(win,rec,G,withFinancials){
 const PS=win.PublicScreens,CS=win.ClassificationScreens,QI=win.Qgv2Inputs,SR=win.SecReported,DD=withFinancials&&win.DartDisclosures&&win.DartDisclosures.loadFinancials?win.DartDisclosures:null,v=rec.view;
 const ME=win.MacroEvidence&&win.MacroEvidence.read?win.MacroEvidence:null;
 const[reported,screens,classification,qgv2,financials,evidence]=await Promise.all([SR?SR.load(v):null,PS?PS.load(v):{},CS?CS.load(v):null,QI?QI.load(v):null,DD?DD.loadFinancials(v):null,ME?ME.read(v):null]);
 const out={...(object(screens)?screens:{})};if(classification)out[CS.FILE]=classification;if(qgv2)out[QI.FILE]=qgv2;if(financials)out[FIN]=financials;
 const newer=(()=>{try{return!!QI&&QI.lastReason()==='SCHEMA_NEWER';}catch(_){return false;}})();
 for(const n of[...(PS?Object.keys(PS.FILES):[]),CS&&CS.FILE,QI&&QI.FILE,DD&&FIN].filter(Boolean))G.files[n]=info(outcome(n,Object.hasOwn(out,n),rec,n===QGV2&&newer),out[n]);
 if(SR)G.files[REPORTED]=info(outcome(REPORTED,!!reported,rec,false),reported);
 if(ME){G.macroEvidence=evidence;G.files[ME.FILENAME]={...outcome(ME.FILENAME,!!evidence.payload,rec,false),as_of:evidence.payload?evidence.payload.generated_at:null};}
 return{screens:out,reported};
}
// Silent commit keeps the old DOM intact until the app captures its view state and redraws the macro screen.
function installEvidence(win,G){if(G.macroEvidence&&win.MacroEvidence)win.MacroEvidence.setPayload(G.macroEvidence.payload,G.macroEvidence.status,{silent:true});}
const apiOf=(win,key)=>key==='sec'?win.SecDisclosures:key==='news'?win.NewsSignals:key==='dart'?win.DartDisclosures:null;
function readList(win,rec,G,key){const api=apiOf(win,key),file=LISTS[key];if(!api||!file)return Promise.resolve(null);
 return Promise.resolve(api.load(rec.view)).catch(()=>null).then(p=>{G.files[file]=info(outcome(file,!!p,rec,false),p);G.listValues[key]=p;return p;});}
function readShares(win,rec,G){const S=win.SecUniverseShares;if(!S)return Promise.resolve({x:null,error:null});
 return S.loadInputs(rec.view).then(x=>({x,error:null}),error=>({x:null,error})).then(r=>{G.files[SHARES]=info(r.x?outcome(SHARES,true,rec,false):outcome(SHARES,false,rec,/SCHEMA_NEWER/.test(String(r.error&&r.error.message))),r.x);G.sharesDir=directory(r.x,r.error);return r;});}

// ---------- page-open and lazy reads ----------
async function load(win){view=view||win;initializing=true;paint();
 try{const G=current(),rec=recorder(win),r=await readCore(win,rec,G,false);await keepRaw(rec,G);
  G.screens=r.screens;G.reported=r.reported;installEvidence(win,G);G.checked_at=nowIso();judgedAt=Date.now();return{screens:r.screens,reported:r.reported};
 }finally{initializing=false;paint();}}
function list(win,key){const G=current();if(!LISTS[key]||!apiOf(win,key))return Promise.resolve(null);
 if(!G.lists[key])G.lists[key]=readList(win,recorder(win),G,key).then(p=>{paint();return p;});return G.lists[key];}
function shares(win){const G=current();if(!win.SecUniverseShares)return Promise.resolve(null);
 if(!G.shares){const rec=recorder(win);G.shares=readShares(win,rec,G).then(async r=>{await keepRaw(rec,G);paint();if(r.error)throw r.error;return r.x;});}return G.shares;}
function financials(win){const G=current(),DD=win.DartDisclosures;if(!DD||!DD.loadFinancials)return Promise.resolve(null);
 if(!G.financials){const rec=recorder(win);G.financials=Promise.resolve(DD.loadFinancials(rec.view)).catch(()=>null).then(p=>{G.files[FIN]=info(outcome(FIN,!!p,rec,false),p);paint();return p;});}
 // A late answer for a publication that a refresh has already replaced is not handed to the app.
 return G.financials.then(p=>gen===G?p:null);}

// ---------- refresh (user-pressed) ----------
const basisOf=G=>{const q=G&&G.screens?G.screens[QGV2]:null;return q&&typeof q.as_of==='string'?q.as_of:null;};
function changedFiles(old,G){if(!old)return Object.keys(G.files);const out=[];for(const[n,f]of Object.entries(G.files)){const o=old.files[n];if(o&&(o.state!==f.state||o.as_of!==f.as_of))out.push(n);}return out.sort();}
async function refresh(){
 if(initializing)return 'LOADING';if(busy||!view)return last.state;busy=true;const old=gen,G=fresh(),rec=recorder(view);last={...last,state:'LOADING'};paint();
 try{
  const lists=Object.keys(LISTS).map(k=>readList(view,rec,G,k).then(p=>{G.lists[k]=Promise.resolve(p);return p;}));
  const sharesRead=old&&old.shares?readShares(view,rec,G).then(r=>{G.shares=r.error?Promise.reject(r.error):Promise.resolve(r.x);G.shares.catch(()=>{});return r;}):null;
  const[core]=await Promise.all([readCore(view,rec,G,true),...lists,sharesRead]);await keepRaw(rec,G);
  G.screens=core.screens;G.reported=core.reported;G.financials=Promise.resolve(core.screens[FIN]||null);G.checked_at=nowIso();
  // A missing file on first load is unpublished; disappearance of a previously valid file is a failed refresh.
  const failed=Object.entries(G.files).filter(([file,f])=>f.state==='FAILED'||(f.state==='NOT_PUBLISHED'&&old?.files[file]?.state==='OK'))
   .map(([file,f])=>({file,...f,state:'FAILED',why:f.why||'HTTP'}));
  if(failed.length){last={state:'FAILED',at:G.checked_at,failed,changed:[],previous:null,repaint:null};paint();return 'FAILED';}
  const changed=changedFiles(old,G);
  if(old&&!changed.length){old.checked_at=G.checked_at;last={state:'UNCHANGED',at:G.checked_at,failed:[],changed:[],previous:null,repaint:null};busy=false;await rejudge('REFRESH');paint();return 'UNCHANGED';}
  const previous=old?{basis:basisOf(old),generation:old.id}:null;gen=G;judgedAt=Date.now();
  last={state:'APPLIED',at:G.checked_at,failed:[],changed,previous,repaint:null};
  hand(G,'REFRESH',changed,previous);paint();return 'APPLIED';
 }catch(_){last={state:'FAILED',at:nowIso(),failed:[{file:'*',state:'FAILED',why:'ERROR',http:null}],changed:[],previous:null,repaint:null};paint();return 'FAILED';}
 finally{busy=false;paint();}
}
// Hand one set to the app, repaint the open screen, tell every other cache owner.
function hand(G,reason,changed,previous,trigger='BUTTON'){
 guardPrices();
 installEvidence(view,G);
 try{if(typeof hooks.apply==='function')hooks.apply(Object.freeze({screens:G.screens,reported:G.reported,shares:G.sharesDir}));}catch(_){}
 last.repaint=repaint(reason);
 try{view.dispatchEvent(new view.CustomEvent(EVENT,{detail:Object.freeze({reason,trigger,generation:G.id,publication:publication(),changed:Object.freeze([...changed]),previous,checked_at:G.checked_at})}));}catch(_){}
}
/* While the screens recompute on the new set (the shared QgvScores.pageResult runs collectQuotes again for the new inputs object),
   the device price reads stay inside this browser: PriceStore month-end / daily closes are read with fetch:false and only when the
   user's Prices tabs are already loaded in RAM; otherwise they answer {} (no Worker sync, no Sheets read). The guard ends at the next
   screen change (before the app draws it) or after GUARD_MS. Device quotes (Universe read, stored quotes) are RAM reads already. */
const GUARD_MS=30000;let guardTimer=0,guarded=null;
function guardPrices(){const PS=view.PriceStore;if(!PS||guarded||typeof PS.monthEndCloses!=='function')return;const orig=PS;
 const loaded=()=>{try{const s=orig.status();return s.state==='READY'&&Object.values(object(s.tabs)?s.tabs:{}).every(t=>!t||!t.present||t.read);}catch(_){return false;}};
 const wrap=(name)=>typeof orig[name]==='function'?(...a)=>{if(!loaded())return Promise.resolve({});const o=a[name==='dailyCloses'?2:1];a[name==='dailyCloses'?2:1]={...(object(o)?o:{}),fetch:false};return orig[name](...a);}:orig[name];
 try{view.PriceStore=Object.freeze({...orig,monthEndCloses:wrap('monthEndCloses'),dailyCloses:wrap('dailyCloses')});guarded=orig;}catch(_){return;}
 guardTimer=view.setTimeout(unguardPrices,GUARD_MS);}
function unguardPrices(){if(!guarded)return;try{view.clearTimeout(guardTimer);view.PriceStore=guarded;}catch(_){}guarded=null;}
function repaint(reason){
 const route=typeof hooks.route==='function'?hooks.route()||'home':'home';let how='NONE';quiet=true;
 try{if(typeof hooks.inPlace==='function'&&hooks.inPlace())how='IN_PLACE';else if(FULL.has(route)&&typeof hooks.render==='function'){hooks.render({keep:true});how='RENDER';}else if(!NONE.has(route)){outdated(reason);how='NOTICE';}}
 catch(_){how='ERROR';}finally{quiet=false;}
 return how;
}

/* ---------- the view state of a screen drawn again (G2) ----------
   A refresh or a re-judgement draws a FULL screen again from the new set (hooks.render({keep:true})); nothing the user did to the
   open screen is lost: the app calls captureView(root) before it replaces the screen, restoreFields(root,s) right after the new
   markup is in (before the screen reads its controls), restoreView(root,s) at the end. Kept: text / select / checkbox values,
   open details, the pressed view button of a button group or the selected tab, inner scroll, the page position (the same element
   at the same height in the window) and the focused element.
   Elements are matched by id, else by tag + data-* / name / href / type attributes (+ the nearest ancestor id) + order; a focused
   element whose state attribute changed is matched by attribute names. Values are never kept: every number and state comes from
   the new markup. A screen opened by the user (hash change) still starts at the top. Stars (data-star, data-investor-star) are
   settings, not view state, and are never pressed here. */
const VIEW_TABS='[role="group"] button[aria-pressed]:not([data-star]):not([data-investor-star]),[role="tab"][aria-selected]',VIEW_SETTLE_TICKS=30;
let viewSeq=0;
const KEY_ATTR=/^(data-|name$|href$|type$|aria-controls$)/;
function viewSig(n,values){if(n.id)return'#'+n.id;let s=n.tagName;for(const a of n.attributes)if(KEY_ATTR.test(a.name))s+='['+a.name+(values?'='+a.value:'')+']';
 let p=n.parentElement;while(p&&!p.id)p=p.parentElement;return(p?'#'+p.id+' ':'')+s;}
function keyed(root,sel,values=true){const seen=new Map(),out=new Map();for(const n of root.querySelectorAll(sel)){const k=viewSig(n,values),i=seen.get(k)||0;seen.set(k,i+1);out.set(k+'@'+i,n);}return out;}
const keyOf=(root,n,values)=>{for(const[k,m]of keyed(root,n.tagName,values))if(m===n)return k;return null;};
function captureView(root){if(!root)return null;const win=root.ownerDocument.defaultView,doc=root.ownerDocument,s={x:win.scrollX,y:win.scrollY,anchor:null,fields:[],details:[],tabs:[],scrolled:[],focus:null};
 for(const[k,n]of keyed(root,'input,select,textarea')){const type=(n.type||'').toLowerCase();if(['file','hidden','submit','button','reset','image','password'].includes(type))continue;
  s.fields.push([k,type==='checkbox'||type==='radio'?{checked:n.checked}:{value:n.value}]);}
 for(const[k,n]of keyed(root,'details'))s.details.push([k,n.open]);
 for(const[k,n]of keyed(root,VIEW_TABS))s.tabs.push([k,n.getAttribute('aria-pressed')==='true'||n.getAttribute('aria-selected')==='true']);
 // The page position is the first element that starts inside the window and its distance from the window top (the scroll
 // position itself when none): text above it may grow or shrink with the new values and the bar above the screen changes height.
 for(const n of root.querySelectorAll('*')){if(n.scrollLeft>0||n.scrollTop>0){const k=keyOf(root,n,true);if(k)s.scrolled.push([n.tagName,k,n.scrollLeft,n.scrollTop]);}
  if(!s.anchor&&s.y>0){const r=n.getBoundingClientRect();if(r.height>0&&r.top>=0&&r.top<win.innerHeight)s.anchor={tag:n.tagName,key:keyOf(root,n,true),alt:keyOf(root,n,false),top:r.top};}}
 const a=doc.activeElement;if(a&&a!==root&&root.contains(a)){s.focus={tag:a.tagName,key:keyOf(root,a,true),alt:keyOf(root,a,false),sel:null};try{if(typeof a.selectionStart==='number')s.focus.sel=[a.selectionStart,a.selectionEnd];}catch(_){}}
 return s;}
function restoreFields(root,s){if(!root||!s)return;const now=keyed(root,'input,select,textarea');
 for(const[k,v]of s.fields){const n=now.get(k);if(!n)continue;if('checked'in v)n.checked=v.checked;else if(n.tagName!=='SELECT'||[...n.options].some(o=>o.value===v.value))n.value=v.value;}
 openDetails(root,s);}
function openDetails(root,s){const now=keyed(root,'details');for(const[k,open]of s.details){const n=now.get(k);if(n&&n.open!==open)n.open=open;}}
const pressed=n=>n.getAttribute('aria-pressed')==='true'||n.getAttribute('aria-selected')==='true';
// A view button re-draws its panel on click; the buttons are looked up again after every click. First the buttons that were on
// (a button group's choice), then the independent toggles that were off.
function pressTabs(root,s){for(const want of[true,false])for(const[k,on]of s.tabs){if(on!==want)continue;const n=keyed(root,VIEW_TABS).get(k);if(n&&pressed(n)!==on&&!n.disabled)n.click();}}
const find=(root,f)=>(f.key&&keyed(root,f.tag,true).get(f.key))||(f.alt&&keyed(root,f.tag,false).get(f.alt))||null;
function targetY(root,s,win){const n=s.anchor&&find(root,s.anchor);return n?Math.max(0,Math.round(n.getBoundingClientRect().top+win.scrollY-s.anchor.top)):s.y;}
function focusKept(root,s){const f=s.focus;if(!f)return true;const n=find(root,f);if(!n)return false;
 try{n.focus({preventScroll:true});if(f.sel&&typeof n.setSelectionRange==='function')n.setSelectionRange(f.sel[0],f.sel[1]);}catch(_){}return root.ownerDocument.activeElement===n;}
function restoreView(root,s){if(!root||!s)return;const win=root.ownerDocument.defaultView,doc=root.ownerDocument,hash=win.location.hash,seq=++viewSeq;
 openDetails(root,s);pressTabs(root,s);
 for(const[tag,k,l,t]of s.scrolled){const n=keyed(root,tag,true).get(k);if(n){n.scrollLeft=l;n.scrollTop=t;}}
 let focused=focusKept(root,s);win.scrollTo(s.x,targetY(root,s,win));
 // Parts filled after the screen (lists read once per publication, panels) can still grow the page: the position and the focus are
 // put back for 1.5 s (30 ticks of 50 ms) unless the user scrolls or presses something, the screen changes or it is drawn again.
 let user=false;const stop=()=>{user=true;},ev=['wheel','touchstart','pointerdown','keydown'];for(const e of ev)win.addEventListener(e,stop,{capture:true,passive:true,once:true});
 let ticks=0;const end=()=>{for(const e of ev)win.removeEventListener(e,stop,{capture:true});};
 const settle=()=>{if(user||seq!==viewSeq||!root.isConnected||win.location.hash!==hash||++ticks>VIEW_SETTLE_TICKS){end();return;}
  if(!focused&&(doc.activeElement===doc.body||!doc.activeElement)){openDetails(root,s);focused=focusKept(root,s);}
  const y=targetY(root,s,win);if(Math.abs(win.scrollY-y)>1||Math.abs(win.scrollX-s.x)>1)win.scrollTo(s.x,y);win.setTimeout(settle,50);};
 win.setTimeout(settle,50);}

// ---------- re-judging freshness as time passes (no network) ----------
function rowBounds(p,file){const out=[];if(!object(p)||!finite(p.stale_after_seconds))return out;const ttl=p.stale_after_seconds*1000;
 const rows=file===QGV2?[...Object.values(object(p.records)?p.records:{}),...Object.values(object(p.target)?p.target:{})]:Object.values(object(p.records)?p.records:{});
 for(const r of rows){if(!object(r)||typeof r.acquired_at!=='string')continue;if(file===QGV2?r.fiscal_year_end===null:r.shares===null)continue;const t=Date.parse(r.acquired_at);if(Number.isFinite(t))out.push(t+ttl);}return out;}
function fileBound(p){if(!object(p)||typeof p.as_of!=='string'||!finite(p.stale_after_seconds))return null;const t=Date.parse(p.as_of);return Number.isFinite(t)?t+p.stale_after_seconds*1000:null;}
function crossedFiles(G,from,to){const hit=b=>b!==null&&b>=from&&b<to,out=[];
 for(const f of RAW)if(G.bounds[f]&&G.bounds[f].some(hit))out.push(f);
 for(const[n,p]of Object.entries(G.screens))if(!RAW.has(n)&&hit(fileBound(p)))out.push(n);
 for(const[k,p]of Object.entries(G.listValues))if(hit(fileBound(p)))out.push(LISTS[k]);
 return out;}
let judging=null;
function rejudge(reason='TIME'){if(!judging)judging=judge(reason).finally(()=>{judging=null;});return judging;}
async function judge(reason){
 if(!gen||!view||busy||initializing)return false;const G=gen,now=Date.now(),hit=crossedFiles(G,judgedAt,now);if(!hit.length){judgedAt=Math.max(judgedAt,now);return false;}
 let screens=G.screens,dir=G.sharesDir;
 if(hit.includes(QGV2)&&G.raw[QGV2]&&view.Qgv2Inputs){const x=await view.Qgv2Inputs.load(local(view,G.raw[QGV2]));if(x)screens={...screens,[view.Qgv2Inputs.FILE]:x};}
 if(hit.includes(SHARES)&&G.raw[SHARES]&&view.SecUniverseShares){try{const x=await view.SecUniverseShares.loadInputs(local(view,G.raw[SHARES]));if(x){dir=directory(x,null);G.shares=Promise.resolve(x);}}catch(_){}}
 if(gen!==G||busy)return false;G.screens=screens;G.sharesDir=dir;judgedAt=now;
 hand(G,'REJUDGE',hit,null,reason);paint();return true;
}

// ---------- status ----------
function publication(){const G=gen,files={};if(G)for(const[n,f]of Object.entries(G.files))files[n]=Object.freeze({state:f.state,as_of:f.as_of});
 return Object.freeze({generation:G?G.id:0,basis:basisOf(G),checked_at:G?G.checked_at:null,key:JSON.stringify(Object.keys(files).sort().map(n=>[n,files[n].state,files[n].as_of])),files:Object.freeze(files)});}
function status(file){const f=gen&&gen.files[file];return f?Object.freeze({...f}):null;}
const en=()=>{try{return /^en/i.test(view.document.documentElement.lang);}catch(_){return false;}};
const T=(ko,e)=>en()?e:ko;
function clock(x){return typeof x==='string'&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(x)?x.slice(0,10)+' '+x.slice(11,16)+' UTC':'—';}
// Plain words for a file without a value. A failed read and a not-yet-published file never share a sentence.
function readText(file,f=status(file)){
 if(!f)return'';if(f.state==='NOT_PUBLISHED')return T('아직 게시되지 않음(HTTP 404)','Not published yet (HTTP 404)');
 if(f.state!=='FAILED')return'';
 if(f.why==='SCHEMA_NEWER')return T('읽기 실패 · 자료 형식이 새 버전입니다. 페이지를 새로 여세요','Read failed · newer data format. Reopen the page');
 if(f.why==='INVALID')return T('읽기 실패 · 내용 검증 실패','Read failed · content did not validate');
 if(f.why==='NETWORK')return T('읽기 실패 · 네트워크 오류','Read failed · network error');
 return T('읽기 실패(HTTP ','Read failed (HTTP ')+(f.http||'?')+')';
}

// ---------- the bar ----------
function el(doc,tag,attrs={},text){const n=doc.createElement(tag);for(const[k,v]of Object.entries(attrs))n.setAttribute(k,v);if(text!==undefined)n.textContent=text;return n;}
function bar(){try{return view&&view.document?view.document.getElementById('data-refresh'):null;}catch(_){return null;}}
function mountBar(){const doc=view.document,main=doc.getElementById('content');if(!main||bar())return;
 const box=el(doc,'section',{id:'data-refresh',class:'data-refresh','aria-label':T('공개 자료 갱신','Public data refresh')});
 const button=el(doc,'button',{type:'button','data-refresh-button':''});button.addEventListener('click',()=>{void refresh();});
 box.append(button,el(doc,'p',{class:'small','data-refresh-status':'',role:'status','aria-live':'polite'}),el(doc,'details',{'data-refresh-details':''}));
 main.before(box);}
function paint(){const box=bar();if(!box)return;const G=gen,basis=basisOf(G),button=box.querySelector('[data-refresh-button]'),line=box.querySelector('[data-refresh-status]'),det=box.querySelector('[data-refresh-details]');
 const loading=busy||initializing,s=loading?'LOADING':last.state;box.dataset.refreshState=s;box.dataset.refreshBasis=basis||'';box.dataset.refreshChecked=G&&G.checked_at||'';box.setAttribute('aria-label',T('공개 자료 갱신','Public data refresh'));
 button.disabled=loading;button.textContent=loading?T('확인 중…','Checking…'):T('자료 새로고침','Refresh data');
 const b=T('점수 기준 ','Scores as of ')+(basis||T('없음','none')),c=T('마지막 확인 ','Last checked ')+clock(G&&G.checked_at);
 const text=s==='LOADING'?T('공개 자료를 다시 읽는 중…','Reading the public files again…')
  :s==='APPLIED'?T('새 게시본 적용','New publication applied')+' · '+(last.previous&&last.previous.basis&&last.previous.basis!==basis?T('점수 기준 ','Scores as of ')+last.previous.basis+' → '+(basis||T('없음','none')):b)+' · '+c
  :s==='UNCHANGED'?T('새 게시본 없음','No new publication')+' · '+b+' · '+c
  :s==='FAILED'?T('갱신 실패 · 이전 값 유지','Refresh failed · previous values kept')+' · '+b+' · '+c+' · '+T('시도 ','tried ')+clock(last.at)+' · '+last.failed.map(f=>f.file+' '+readText(f.file,f)).join(' · ')
  :T('공개 자료','Public data')+' · '+b+' · '+c;
 if(line.textContent!==text)line.textContent=text;
 const rows=G?Object.entries(G.files).filter(([,f])=>f.state==='FAILED'||f.state==='NOT_PUBLISHED').sort((a,b)=>a[0]<b[0]?-1:1):[],nFail=rows.filter(([,f])=>f.state==='FAILED').length;
 const summary=T('파일별 상태','Per-file status')+' · '+T('읽기 실패 ','read failed ')+nFail+' · '+T('미게시 ','not published ')+(rows.length-nFail);
 const doc=view.document,list=el(doc,'ul',{class:'small'});
 for(const[n,f]of rows)list.append(el(doc,'li',{'data-refresh-file':n,'data-refresh-file-state':f.state},n+' · '+readText(n,f)+(f.state==='FAILED'?T(' · 값 없음',' · no value'):'')));
 if(!rows.length)list.append(el(doc,'li',{},T('모든 공개 파일을 읽었습니다.','Every public file was read.')));
 const open=det.open;det.replaceChildren(el(doc,'summary',{},summary),list);det.open=open;
}
function outdated(reason){const doc=view.document,main=doc.getElementById('content');if(!main)return;let n=main.querySelector(':scope > [data-refresh-outdated]');
 if(!n){n=el(doc,'div',{class:'banner','data-refresh-outdated':''});main.prepend(n);}
 const redraw=el(doc,'button',{type:'button','data-refresh-redraw':''},T('이 화면 다시 그리기','Redraw this screen'));redraw.addEventListener('click',()=>{if(typeof hooks.render==='function')hooks.render();});
 n.dataset.refreshReason=reason;n.replaceChildren(el(doc,'span',{},(reason==='REJUDGE'?T('자료 신선도 판정이 바뀌었습니다','Data freshness changed'):T('새 공개 자료를 적용했습니다','New public data applied'))+' · '+T('이 화면은 기기 작업을 지키려고 다시 그리지 않았습니다. ','This screen was not redrawn to keep your device work. ')),redraw);}

// ---------- wiring ----------
function attach(win,h={}){view=win;hooks=h||{};current();
 const go=()=>{mountBar();paint();};if(win.document.readyState==='loading')win.document.addEventListener('DOMContentLoaded',go,{once:true});else go();
 try{new win.MutationObserver(()=>paint()).observe(win.document.documentElement,{attributes:true,attributeFilter:['lang']});}catch(_){}
 if(!timer)timer=win.setInterval(()=>{void rejudge('TIME');},TICK);
 win.document.addEventListener('visibilitychange',()=>{if(win.document.visibilityState==='visible')void rejudge('VISIBLE');});
 // After a screen change too: the new screen was drawn from the states judged earlier; a crossed boundary repaints it.
 win.addEventListener('hashchange',()=>{void rejudge('NAVIGATE');});
 // A screen the user opens is a normal screen open: the device price guard of a refresh ends before the app draws it (capture).
 win.addEventListener('hashchange',unguardPrices,true);
 return api;}
const api=Object.freeze({EVENT,LISTS,pricesGuarded:()=>guarded!==null,attach,load,list,shares,financials,refresh,rejudge,status,readText,publication,captureView,restoreFields,restoreView,quiet:()=>quiet,last:()=>Object.freeze({...last})});
return api;
});
