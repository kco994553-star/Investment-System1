/* P1 action gate (IS2.action): every Sheet / Worker / OAuth request and every device-storage write runs inside a trusted user
   click, and only to the destinations that click's kind allows (P1 implementation spec, Main decisions 2 and 4; owner decisions
   2026-10-24, P1_DATA_LAYER.md §11).
   - run(event, kind, fn, {parent}): fn(signal) runs in the same tick (GIS login must start inside the click) and the kind stays in
     flight until fn settles or cancel(kind). The event must be a real gesture of this window read through the window's own Event
     accessors (a forged object or a Proxy that only claims isTrusted makes them throw), a click or Enter / Space keydown (not a
     submit: form.requestSubmit() and a script's button.click() make trusted submits), still being dispatched, with transient user
     activation where the browser reports it. A keydown counts only on a control without activation behaviour and never as an
     auto-repeat: a button, a link, a summary or an input turns the same key press into its own trusted click (an input in a form
     may do so through implicit submission), so there the click is the gesture and one press starts one action.
     One event starts ONE top-level action: a second run with it is ACTION_ALREADY_STARTED (still dispatching) or CLICK_REQUIRED
     (a kept event replayed later). A next step of that action (engines.target.syncScoringPrices -> prices.syncSymbols after
     awaits) is a nested run that presents its parent's signal ({parent: signal}, the AbortSignal its fn received): it passes only
     while that parent action of the same event is in flight, it ends when the parent is cancelled, and it may only reach what the
     parent may (the same kind, or a WRITE step under a storage-writing action; nothing under PUBLIC_REFRESH): else
     ACTION_KIND_NOT_COVERED.
   - guard(url, init, {sheets}): the destination check every private request makes (the price view in prices.js). Private
     destinations pass only while an action whose kind allows them is in flight, and Sheets only for the spreadsheets this device
     saved; otherwise blocked() grows and CLICK_REQUIRED (or DESTINATION_UNKNOWN) is thrown.
   - view(overrides): the window as old modules see it (same binding rule as DataRefresh.proxy, data-refresh.js:49: lowercase
     window functions keep the real window as `this`, so dispatchEvent / addEventListener / setTimeout work). Every view replaces
     localStorage / sessionStorage / indexedDB with the gated versions below and refuses writes to window globals (DataRefresh's
     30 s PriceStore swap fails inside its own try/catch).
   - IndexedDB through a view: a write transaction or a version change needs a storage-writing action (ACTION_REQUIRED), and the
     device quote records (STOPPED: DeviceActual's 'market' quotes and 'market-import-history') are never written, not even inside
     a click (MARKET_STORE_STOPPED), and read as absent (owner 2026-10-24, DC-18: device prices only in RAM and the user's own
     Sheet). Every IndexedDB object reachable from one the view handed out (a request's source / transaction / result, a cursor,
     an index, an event's target in a handler) is the gated one too. What a device stored before stays until the user removes it
     (stoppedRecords.clear on a WRITE click: "저장된 시세 삭제").
   - localStorage through a view: the device V history keys (STOPPED.localStorage, owner 2026-10-31, DC-31: no device V history)
     read as absent (getItem null) and are never set or removed by key, not even inside a click (V_HISTORY_STOPPED; a whole-storage
     clear(), which no module calls, stays a storage-writing action); key() / length still count them (names only, no value). Their removal is the user's settings click (stoppedKeys.clear with a WRITE signal).
   The permission is page wide while an action is in flight (any code may write storage or reach that kind's destinations until
   it settles or is cancelled): P1_DATA_LAYER.md §3. The gate holds for the old modules, which only see a view; it is not a sandbox
   for page code, which has the real window. Nothing here reads or writes storage by itself and nothing is sent anywhere. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else(root.IS2=root.IS2||{}).action=api.create({win:root});})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
// Kind -> private destinations it may reach. PUBLIC_REFRESH reads public files only (it never opens the private gate, critique #3);
// WRITE is device storage only. SYNC reads the Worker history and appends/updates the user's own Sheet.
const KINDS=Object.freeze({PUBLIC_REFRESH:Object.freeze([]),LOGIN:Object.freeze(['OAUTH']),UNIVERSE_READ:Object.freeze(['SHEETS_READ']),HISTORY:Object.freeze(['WORKER_HISTORY']),
 SYNC:Object.freeze(['WORKER','WORKER_HISTORY','SHEETS_READ','SHEETS_WRITE']),WRITE:Object.freeze([])});
// Kinds that may write device storage (each writes only its own documented keys): every user action except the public refresh.
const WRITERS=Object.freeze(Object.keys(KINDS).filter(k=>k!=='PUBLIC_REFRESH'));
const SHEETS='https://sheets.googleapis.com',OAUTH=Object.freeze(['https://oauth2.googleapis.com','https://accounts.google.com']);
// Device quote records the new frontend neither writes nor reads (owner 2026-10-24, DC-18; plan §2.1): database -> object store ->
// record keys. DeviceActual keeps its stored market quotes under 'market' and every import's quotes and FX under
// 'market-import-history' (device-actual.js:9-10), next to the holdings ('actual') and the Google on/off record, which stay.
// localStorage: the device V history keys of VirtualTradingVHistory (virtual-trading-v-history.js KEY / V2_KEY), stopped (DC-31).
const STOPPED=Object.freeze({indexedDB:Object.freeze({'investment-device-actual-v1':Object.freeze({snapshots:Object.freeze(['market','market-import-history'])})}),
 localStorage:Object.freeze(['investment.web.v1.virtual-trading-v-scores','investment.web.v2.virtual-trading-v-scores'])});
const STOPPED_KEYS=STOPPED.localStorage;
// A key no record has (DeviceActual keys its records by name): a read of a stopped record asks for it, so the real request
// answers "no record" and the old module sees the quotes as never stored.
const NO_RECORD='MARKET_STORE_STOPPED';
function create({win}){
 // controllers: AbortController -> {kind, done, event} of each action in flight; started: events that started their top-level action.
 const flight=new Map(),controllers=new Map(),started=new WeakSet(),stores={known:new Set(),supported:null};let blockedCount=0;
 const inFlight=k=>(flight.get(k)>0);
 const active=kind=>kind===undefined?[...flight.values()].some(n=>n>0):inFlight(kind);
 const writing=()=>WRITERS.some(inFlight);
 // The window's own Event accessors, captured once (isTrusted is an own accessor of each event, the others sit on the prototypes).
 const E=typeof win.Event==='function'?win.Event:null,KE=typeof win.KeyboardEvent==='function'?win.KeyboardEvent:null;
 const accessor=(o,k)=>{for(let p=o;p;p=Object.getPrototypeOf(p)){const d=Object.getOwnPropertyDescriptor(p,k);if(d)return typeof d.get==='function'?d.get:null;}return null;};
 let sample=null;try{sample=E?new E('x'):null;}catch(_){sample=null;}
 const NATIVE=Object.freeze({trusted:sample?accessor(sample,'isTrusted'):null,type:E?accessor(E.prototype,'type'):null,phase:E?accessor(E.prototype,'eventPhase'):null,key:KE?accessor(KE.prototype,'key'):null,
  repeat:KE?accessor(KE.prototype,'repeat'):null,target:E?accessor(E.prototype,'target'):null});
 const read=(get,e)=>Reflect.apply(get,e,[]);
 // Inputs whose Enter / Space the browser turns into their own trusted click (activation behaviour).
 const CLICKING_INPUTS=Object.freeze(['button','submit','reset','image','checkbox','radio','file','color']);
 const isA=(v,n)=>{const C=win[n];return typeof C==='function'&&v instanceof C;};
 // The keydown's target fires its own click for this key (a button, a link, a summary, a clicking input), or may click the form's
 // default button by implicit submission (Enter in any other input of a form): its click is the gesture, not the keydown.
 function clicksItself(t,k){if(t===null||typeof t!=='object')return false;
  if(isA(t,'HTMLButtonElement'))return true;if((isA(t,'HTMLAnchorElement')||isA(t,'HTMLAreaElement'))&&t.hasAttribute('href'))return true;
  if(isA(t,'HTMLElement')&&t.localName==='summary')return true;
  if(isA(t,'HTMLInputElement'))return CLICKING_INPUTS.includes(String(t.type).toLowerCase())||(k==='Enter'&&t.form!==null);return false;}
 // A real user gesture: a trusted click, or Enter / Space (not an auto-repeat) on a focused control that has no activation
 // behaviour. Read through the native accessors, a forged event (Object.create(Event.prototype, ...), a Proxy answering
 // isTrusted) throws and is refused.
 function gesture(e){if(!E||!NATIVE.trusted||!NATIVE.type||!(e instanceof E))return false;
  try{if(read(NATIVE.trusted,e)!==true)return false;const t=read(NATIVE.type,e);if(t==='click')return true;if(t!=='keydown')return false;
   const kb=!!KE&&e instanceof KE,k=NATIVE.key&&kb?read(NATIVE.key,e):e.key,rep=NATIVE.repeat&&kb?read(NATIVE.repeat,e):e.repeat;
   if(k!=='Enter'&&k!==' ')return false;if(rep===true)return false;return !clicksItself(NATIVE.target?read(NATIVE.target,e):null,k);}catch(_){return false;}}
 // Its handlers are running now (eventPhase is NONE once the dispatch is over: a kept event, a timer's later call).
 function dispatching(e){if(!NATIVE.phase)return false;try{return read(NATIVE.phase,e)!==0;}catch(_){return false;}}
 // Transient user activation, where the browser reports it (no input, no activation: a script's submit, a replay).
 function activated(){let ua=null;try{ua=win.navigator?win.navigator.userActivation:null;}catch(_){ua=null;}return !ua||typeof ua.isActive!=='boolean'||ua.isActive===true;}
 // The parent a nested run presents: the signal of an action of the same event that is still in flight.
 function parentOf(signal,event){for(const[c,x]of controllers)if(c.signal===signal&&x.event===event)return c;return null;}
 // A nested step reaches only what its parent may: the same kind, or a WRITE step (device storage only) under a storage-writing
 // action. Nothing nests under the public refresh (no private destination, no write), and no SYNC under a WRITE click.
 const covers=(parentKind,kind)=>parentKind!=='PUBLIC_REFRESH'&&(kind===parentKind||(kind==='WRITE'&&WRITERS.includes(parentKind)));
 function run(event,kind,fn,opts){
  if(!Object.hasOwn(KINDS,kind))throw Error('ACTION_KIND_UNKNOWN');
  if(typeof fn!=='function')throw Error('ACTION_INVALID');
  const given=opts!==null&&typeof opts==='object'&&opts.parent!==undefined&&opts.parent!==null?opts.parent:null;
  if(!gesture(event))throw Error('CLICK_REQUIRED');
  let parent=null;
  if(given!==null){parent=parentOf(given,event);if(!parent||parent.signal.aborted)throw Error('CLICK_REQUIRED');if(!covers(controllers.get(parent).kind,kind))throw Error('ACTION_KIND_NOT_COVERED');}
  else{if(!dispatching(event)||!activated())throw Error('CLICK_REQUIRED');if(started.has(event))throw Error('ACTION_ALREADY_STARTED');started.add(event);}
  const c=new win.AbortController();let left=false,unlink=null;
  // Leaves the gate once: when fn settles, at cancel(kind), or when its parent is cancelled, whichever comes first.
  const done=()=>{if(left)return;left=true;flight.set(kind,flight.get(kind)-1);controllers.delete(c);if(unlink)unlink();};
  flight.set(kind,flight.has(kind)?flight.get(kind)+1:1);controllers.set(c,{kind,done,event});
  if(parent){const stop=()=>{c.abort();done();};parent.signal.addEventListener('abort',stop,{once:true});unlink=()=>parent.signal.removeEventListener('abort',stop);}
  let out;try{out=fn(c.signal);}catch(e){done();throw e;}
  if(out&&typeof out.then==='function')return Promise.resolve(out).finally(done);
  done();return out;
 }
 // Cancels the in-flight actions of one kind: their fn sees signal.aborted and they leave the gate now, so a stalled step cannot
 // keep it open (a request or a write they still try is refused).
 function cancel(kind){for(const[c,x]of[...controllers])if(x.kind===kind){c.abort();x.done();}}
 function deny(code){blockedCount++;throw Error(code);}
 // Destination class of one request: PUBLIC (same origin; the caller then uses data.strictFetch), SHEETS_READ (a values GET) /
 // SHEETS_WRITE (every other Sheets request: append, update, batchUpdate, tab list, create), OAUTH, WORKER_HISTORY / WORKER (the
 // public Worker origin of app-config.js), else UNKNOWN. The method of a Request object counts when init gives none.
 function classify(input,init){
  const req=typeof win.Request==='function'&&input instanceof win.Request?input:null,href=typeof input==='string'?input:req?req.url:typeof win.URL==='function'&&input instanceof win.URL?input.href:null;
  if(href===null)return 'UNKNOWN';let u=null;try{u=new win.URL(href,win.location.href);}catch(_){return 'UNKNOWN';}
  if(u.origin===win.location.origin)return 'PUBLIC';
  const method=String(init&&init.method!==undefined?init.method:req?req.method:'GET').toUpperCase(),config=win.InvestmentAppConfig,worker=config&&typeof config.privateHistoryWorkerOrigin==='string'?config.privateHistoryWorkerOrigin:null;
  if(u.origin===SHEETS)return method==='GET'&&/^\/v4\/spreadsheets\/[^/]+\/values\//.test(u.pathname)?'SHEETS_READ':'SHEETS_WRITE';
  if(OAUTH.includes(u.origin))return 'OAUTH';
  if(worker&&u.origin===worker)return u.pathname==='/history'?'WORKER_HISTORY':'WORKER';
  return 'UNKNOWN';
 }
 function allows(dest){for(const[k,n]of flight)if(n>0&&KINDS[k].includes(dest))return true;return false;}
 // The spreadsheet a Sheets URL names (none for a create), checked against the ids the caller saved.
 function sheetOf(input){try{const m=/^\/v4\/spreadsheets\/([^/:?]+)/.exec(new win.URL(input).pathname);return m?decodeURIComponent(m[1]):null;}catch(_){return null;}}
 /* sheets (optional): the spreadsheet ids this device saved, or a function giving them (prices.js: the unified sheet and the
    Universe tab source). A private request is a string URL (the old modules never pass anything else). */
 function guard(input,init,{sheets=null}={}){const dest=classify(input,init);if(dest==='PUBLIC')return dest;
  if(dest==='UNKNOWN'||typeof input!=='string')deny('DESTINATION_UNKNOWN');if(!allows(dest))deny('CLICK_REQUIRED');
  if(sheets!==null&&dest.startsWith('SHEETS_')){const ids=typeof sheets==='function'?sheets():sheets,id=sheetOf(input);if(!id||!Array.isArray(ids)||!ids.includes(id))deny('DESTINATION_UNKNOWN');}
  return dest;}
 const realOf=get=>{try{return typeof get==='function'?get():get;}catch(_){return null;}};
 // Reads pass; setItem / removeItem / clear only inside a storage-writing action, else ACTION_REQUIRED (the storage is unchanged).
 function gatedStorage(get){
  const write=op=>{if(!writing())deny('ACTION_REQUIRED');const s=realOf(get);if(!s)throw Error('DEVICE_STORE_NOT_OPENED');return op(s);};
  const stopped=k=>STOPPED_KEYS.includes(String(k));
  return Object.freeze({getItem(k){if(stopped(k))return null;const s=realOf(get);return s?s.getItem(k):null;},key(i){const s=realOf(get);return s?s.key(i):null;},get length(){const s=realOf(get);return s?s.length:0;},
   setItem(k,v){if(stopped(k))deny('V_HISTORY_STOPPED');return write(s=>s.setItem(k,v));},removeItem(k){if(stopped(k))deny('V_HISTORY_STOPPED');return write(s=>s.removeItem(k));},clear(){return write(s=>s.clear());}});
 }
 /* IndexedDB objects as the old modules see them through a view: a membrane. Each is a Proxy that forwards to the real object
    (one per object; its methods keep the real object as `this`), and every IndexedDB object it hands out is the gated one too:
    a method's result, an accessor (request.source / transaction / result, cursor.source / request, index.objectStore,
    store.transaction, transaction.db), an array of them, and the event a handler receives with its target / currentTarget
    (on* properties and addEventListener). So a module cannot step behind the gate through an object it was given. A write
    transaction needs a storage-writing action (ACTION_REQUIRED). In a STOPPED store a read of a stopped record asks for NO_RECORD
    (absent: DeviceActual then has no stored quote and computes nothing from one) and every write of one is MARKET_STORE_STOPPED,
    inside a click too; such a store takes record names only (the old module never passes anything else), so a key range, a
    cursor or an index that could reach them is refused the same way, and the store cannot be deleted or renamed. */
 const proxies=new WeakMap(),gated=new WeakSet(),listeners=new WeakMap();
 const keysOf=(stopped,name)=>stopped&&Object.hasOwn(stopped,String(name))?stopped[String(name)]:null;
 const idbTarget=t=>isA(t,'IDBRequest')||isA(t,'IDBTransaction')||isA(t,'IDBDatabase');
 // The gated counterpart of a value an IndexedDB object hands out; anything else (a record, a name list) as it is.
 function wrap(v,stopped){if(v===null||typeof v!=='object'||gated.has(v))return v;
  if(Array.isArray(v))return v.some(x=>wrap(x,stopped)!==x)?v.map(x=>wrap(x,stopped)):v;
  if(isA(v,'IDBDatabase'))return dbOf(v,stopped);if(isA(v,'IDBTransaction'))return txOf(v,stopped);
  if(isA(v,'IDBObjectStore'))return storeOf(v,stopped,keysOf(stopped,v.name));if(isA(v,'IDBRequest'))return requestOf(v,stopped);
  if(isA(v,'IDBIndex')||isA(v,'IDBCursor')||(isA(v,'Event')&&idbTarget(v.target)))return forward(v,stopped,{});
  return v;}
 // A handler of a gated object receives the gated event, with the gated object as `this`.
 function listenerOf(fn,stopped){const call=typeof fn==='function';if(!call&&!(fn!==null&&typeof fn==='object'&&typeof fn.handleEvent==='function'))return fn;
  let m=listeners.get(fn);if(!m)listeners.set(fn,m=new Map());let w=m.get(stopped);
  if(!w){w=function(ev){const e=wrap(ev,stopped);return call?Reflect.apply(fn,wrap(this,stopped),[e]):fn.handleEvent(e);};m.set(stopped,w);}return w;}
 // locked: properties that cannot be set (a stopped store's name).
 function forward(real,stopped,hooks,locked=[]){if(real===null||typeof real!=='object')return real;let p=proxies.get(real);if(p)return p;
  p=new Proxy(real,{get(t,k){if(Object.hasOwn(hooks,k))return hooks[k](t);
    if(k==='addEventListener'||k==='removeEventListener'){const f=t[k];if(typeof f!=='function')return f;
     return(type,fn,o)=>Reflect.apply(f,t,[type,k==='addEventListener'?listenerOf(fn,stopped):(listeners.has(fn)&&listeners.get(fn).get(stopped))||fn,o]);}
    const v=Reflect.get(t,k);return typeof v==='function'?(...a)=>wrap(Reflect.apply(v,t,a),stopped):wrap(v,stopped);},
   set(t,k,v){if(locked.includes(k))deny('MARKET_STORE_STOPPED');t[k]=typeof k==='string'&&k.startsWith('on')&&typeof v==='function'?listenerOf(v,stopped):v;return true;}});
  proxies.set(real,p);gated.add(p);return p;}
 // An open request: its result is the gated database, its transaction (a version change) the gated transaction.
 function openRequest(r,stopped){return forward(r,stopped,{result:t=>dbOf(t.result,stopped),transaction:t=>txOf(t.transaction,stopped),source:()=>null});}
 // source: the gated store that made the request (undefined: the real source, gated).
 function requestOf(r,stopped,source){return forward(r,stopped,{result:t=>wrap(t.result,stopped),transaction:t=>txOf(t.transaction,stopped),source:t=>source!==undefined?source:wrap(t.source,stopped)});}
 function dbOf(db,stopped){return forward(db,stopped,{
  transaction:t=>(names,mode,o)=>{if(mode!==undefined&&mode!=='readonly'&&!writing())deny('ACTION_REQUIRED');return txOf(o===undefined?t.transaction(names,mode):t.transaction(names,mode,o),stopped);},
  createObjectStore:t=>(name,o)=>storeOf(o===undefined?t.createObjectStore(name):t.createObjectStore(name,o),stopped,keysOf(stopped,name)),
  deleteObjectStore:t=>name=>{if(keysOf(stopped,name))deny('MARKET_STORE_STOPPED');return t.deleteObjectStore(name);}});}
 function txOf(tx,stopped){return forward(tx,stopped,{db:t=>dbOf(t.db,stopped),objectStore:t=>name=>storeOf(t.objectStore(name),stopped,keysOf(stopped,name))});}
 function storeOf(st,stopped,keys){const req=(t,r)=>requestOf(r,stopped,proxies.get(t)),hooks={transaction:t=>txOf(t.transaction,stopped)};
  if(keys){const read=k=>{if(typeof k!=='string')deny('MARKET_STORE_STOPPED');return keys.includes(k)?NO_RECORD:k;},write=k=>{if(typeof k!=='string'||keys.includes(k)||k===NO_RECORD)deny('MARKET_STORE_STOPPED');return k;};
   for(const m of['get','getKey','count','getAll','getAllKeys','openCursor','openKeyCursor'])hooks[m]=t=>(k,...a)=>req(t,t[m](read(k),...a));
   hooks.put=t=>(v,k)=>req(t,t.put(v,write(k)));hooks.add=t=>(v,k)=>req(t,t.add(v,write(k)));hooks.delete=t=>k=>req(t,t.delete(write(k)));
   for(const m of['clear','index','createIndex'])hooks[m]=()=>()=>deny('MARKET_STORE_STOPPED');}
  else for(const m of['get','getKey','count','getAll','getAllKeys','openCursor','openKeyCursor','put','add','delete','clear'])hooks[m]=t=>(...a)=>req(t,t[m](...a));
  return forward(st,stopped,hooks,keys?['name']:[]);}
 /* Opening a database that does not exist creates it (device-actual.js:187 onupgradeneeded), so open() passes only for a database
    this browser already lists (stores(): indexedDB.databases()) or inside a storage-writing action. readOnly views (the score path)
    never create one, not even inside an action (a listed database deleted since is not created again: its version change is
    aborted). Without databases() nothing opens outside an action. A refused open is the normal "nothing stored yet" state
    (DEVICE_STORE_NOT_OPENED), not a blocked write. */
 function gatedIndexedDB(get,{readOnly=false}={}){
  return Object.freeze({
   open(name,version){const idb=realOf(get);if(!idb)throw Error('DEVICE_STORE_NOT_OPENED');const n=String(name),stopped=Object.hasOwn(STOPPED.indexedDB,n)?STOPPED.indexedDB[n]:null;let r;
    if(stores.known.has(n))r=idb.open(name,version);else if(!readOnly&&writing()){r=idb.open(name,version);stores.known.add(n);}else throw Error('DEVICE_STORE_NOT_OPENED');
    // A version change (a database created after all, or upgraded) is a write: aborted outside a storage-writing action and on a
    // readOnly view (counted in blocked()). This listener runs before any handler the module sets.
    if(r&&typeof r.addEventListener==='function')r.addEventListener('upgradeneeded',()=>{if(readOnly||!writing()){blockedCount++;try{r.transaction.abort();}catch(_){}}});
    return openRequest(r,stopped);},
   deleteDatabase(name){if(!writing())deny('ACTION_REQUIRED');const idb=realOf(get);if(!idb)throw Error('DEVICE_STORE_NOT_OPENED');stores.known.delete(String(name));return idb.deleteDatabase(name);},
   databases(){const idb=realOf(get);return idb&&typeof idb.databases==='function'?idb.databases():Promise.reject(Error('DEVICE_STORE_NOT_OPENED'));},
   cmp(a,b){const idb=realOf(get);if(!idb)throw Error('DEVICE_STORE_NOT_OPENED');return idb.cmp(a,b);}});
 }
 // Refreshes the list of databases that already exist (no database is opened or created). Callers await it before a read path.
 // {supported: databases() answered, available: the browser has IndexedDB at all, names}.
 async function refreshStores(){const idb=realOf(()=>win.indexedDB);
  if(!idb||typeof idb.databases!=='function')stores.supported=false;
  else{try{const list=await idb.databases();stores.known=new Set((Array.isArray(list)?list:[]).map(d=>d&&d.name).filter(n=>typeof n==='string'));stores.supported=true;}catch(_){stores.supported=false;}}
  return Object.freeze({supported:stores.supported,available:!!idb,names:Object.freeze([...stores.known].sort())});}
 /* The stopped records, by key only (no value is ever read): count() is how many this device still holds; clear(signal) removes
    them and needs the signal of a WRITE action in flight (store.marketQuotes, the settings button "저장된 시세 삭제"). A database
    this browser does not list is never opened, so nothing is created. A browser that cannot list its databases: count() answers
    null (unknown) and opens nothing; clear() (inside its WRITE click) opens the database by name, and one that is not there is
    not created (existing() aborts the creation). Numbers only. */
 function existing(name){return new Promise((resolve,reject)=>{let r;try{r=realOf(()=>win.indexedDB).open(name);}catch(_){reject(Error('DEVICE_STORE_NOT_OPENED'));return;}
  r.onupgradeneeded=()=>{try{r.transaction.abort();}catch(_){}};// it was gone after all: the creation is aborted
  r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(Error('DEVICE_STORE_NOT_OPENED'));});}
 async function stoppedHeld(remove){const s=await refreshStores();if(!s.available||(!s.supported&&!remove))return null;let n=0;
  for(const[name,map]of Object.entries(STOPPED.indexedDB)){if(s.supported&&!s.names.includes(name))continue;let db;
   try{db=await existing(name);}catch(e){if(s.supported)throw e;continue;}// not listed and not there: nothing to remove
   try{const names=Object.keys(map).filter(x=>db.objectStoreNames.contains(x));if(!names.length)continue;
    n+=await new Promise((resolve,reject)=>{const tx=db.transaction(names,remove?'readwrite':'readonly');let held=0;
     for(const x of names){const st=tx.objectStore(x);for(const k of map[x]){const r=st.getKey(k);r.onsuccess=()=>{if(r.result!==undefined)held++;};if(remove)st.delete(k);}}
     tx.oncomplete=()=>resolve(held);tx.onabort=tx.onerror=()=>reject(Error('DEVICE_STORAGE_UNAVAILABLE'));});}
   finally{db.close();}}
  return n;}
 const stoppedRecords=Object.freeze({
  count(){return stoppedHeld(false).catch(()=>null);},
  clear(signal){let ok=false;for(const[c,x]of controllers)if(c.signal===signal&&x.kind==='WRITE')ok=true;if(!ok)deny('ACTION_REQUIRED');return stoppedHeld(true);}});
 /* The stopped localStorage keys (DC-31), by key only (no value is ever read): count() how many this device still holds (null: no
    storage); clear(signal) removes them with the signal of a WRITE action in flight (store.vHistoryKeys, a settings click). */
 const writeSignal=signal=>{for(const[c,x]of controllers)if(c.signal===signal&&x.kind==='WRITE')return true;return false;};
 const stoppedKeys=Object.freeze({
  count(){const s=realOf(()=>win.localStorage);if(!s)return null;try{return STOPPED_KEYS.filter(k=>s.getItem(k)!==null).length;}catch(_){return null;}},
  clear(signal){if(!writeSignal(signal))deny('ACTION_REQUIRED');const s=realOf(()=>win.localStorage);if(!s)throw Error('DEVICE_STORE_NOT_OPENED');let n=0;for(const k of STOPPED_KEYS)if(s.getItem(k)!==null){s.removeItem(k);n++;}return n;}});
 function view(overrides,{readOnlyStores=false}={}){
  if(!overrides||typeof overrides.fetch!=='function')throw Error('VIEW_FETCH_REQUIRED');
  const own=Object.defineProperties(Object.create(null),{localStorage:{value:gatedStorage(()=>win.localStorage)},sessionStorage:{value:gatedStorage(()=>win.sessionStorage)},
   indexedDB:{value:gatedIndexedDB(()=>win.indexedDB,{readOnly:readOnlyStores})},...Object.getOwnPropertyDescriptors(overrides)});
  return new Proxy(win,{
   get(t,k){if(typeof k==='string'&&k in own)return own[k];const v=Reflect.get(t,k);return typeof v==='function'&&typeof k==='string'&&/^[a-z]/.test(k)?v.bind(t):v;},
   has(t,k){return(typeof k==='string'&&k in own)||Reflect.has(t,k);},
   set(){return false;},defineProperty(){return false;},deleteProperty(){return false;}});
 }
 return Object.freeze({KINDS,STOPPED,run,cancel,active,writing,blocked:()=>blockedCount,classify,guard,gatedStorage,gatedIndexedDB,stores:refreshStores,stoppedRecords,stoppedKeys,view});
}
return Object.freeze({create,KINDS,STOPPED});
});
