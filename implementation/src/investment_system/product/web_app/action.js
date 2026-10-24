/* P1 action gate (IS2.action): every Sheet / Worker / OAuth request and every device-storage write runs inside a trusted user
   click, and only to the destinations that click's kind allows (P1 implementation spec, Main decisions 2 and 4; owner decisions
   2026-10-24, P1_DATA_LAYER.md §11).
   - run(event, kind, fn, {parent}): fn(signal) runs in the same tick (GIS login must start inside the click) and the kind stays in
     flight until fn settles or cancel(kind). The event must be a real gesture of this window read through the window's own Event
     accessors (a forged object or a Proxy that only claims isTrusted makes them throw), a click or Enter / Space keydown (not a
     submit: form.requestSubmit() and a script's button.click() make trusted submits), still being dispatched, with transient user
     activation where the browser reports it. One event starts ONE top-level action: a second run with it is ACTION_ALREADY_STARTED
     (still dispatching) or CLICK_REQUIRED (a kept event replayed later). A next step of that action (engines.target.syncScoringPrices
     -> prices.syncSymbols after awaits) is a nested run that presents its parent's signal ({parent: signal}, the AbortSignal its fn
     received): it passes only while that parent action of the same event is in flight, and it ends when the parent is cancelled.
   - guard(url, init, {sheets}): the destination check every private request makes (the price view in prices.js). Private
     destinations pass only while an action whose kind allows them is in flight, and Sheets only for the spreadsheets this device
     saved; otherwise blocked() grows and CLICK_REQUIRED (or DESTINATION_UNKNOWN) is thrown.
   - view(overrides): the window as old modules see it (same binding rule as DataRefresh.proxy, data-refresh.js:49: lowercase
     window functions keep the real window as `this`, so dispatchEvent / addEventListener / setTimeout work). Every view replaces
     localStorage / sessionStorage / indexedDB with the gated versions below and refuses writes to window globals (DataRefresh's
     30 s PriceStore swap fails inside its own try/catch).
   - IndexedDB through a view: a write transaction needs a storage-writing action (ACTION_REQUIRED), and the device quote records
     (STOPPED: DeviceActual's 'market' quotes and 'market-import-history') are never written, not even inside a click
     (MARKET_STORE_STOPPED), and read as absent (owner 2026-10-24, DC-18: device prices only in RAM and the user's own Sheet).
     What a device stored before stays until the user removes it (stoppedRecords.clear on a WRITE click: "저장된 시세 삭제").
   The permission is page wide while an action is in flight (any code may write storage or reach that kind's destinations until
   it settles or is cancelled): P1_DATA_LAYER.md §3. Nothing here reads or writes storage by itself and nothing is sent anywhere. */
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
const STOPPED=Object.freeze({'investment-device-actual-v1':Object.freeze({snapshots:Object.freeze(['market','market-import-history'])})});
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
 const NATIVE=Object.freeze({trusted:sample?accessor(sample,'isTrusted'):null,type:E?accessor(E.prototype,'type'):null,phase:E?accessor(E.prototype,'eventPhase'):null,key:KE?accessor(KE.prototype,'key'):null});
 const read=(get,e)=>Reflect.apply(get,e,[]);
 // A real user gesture: a trusted click, or Enter / Space on a focused control. Read through the native accessors, a forged
 // event (Object.create(Event.prototype, ...), a Proxy answering isTrusted) throws and is refused.
 function gesture(e){if(!E||!NATIVE.trusted||!NATIVE.type||!(e instanceof E))return false;
  try{if(read(NATIVE.trusted,e)!==true)return false;const t=read(NATIVE.type,e);if(t==='click')return true;if(t!=='keydown')return false;
   const k=NATIVE.key&&e instanceof KE?read(NATIVE.key,e):e.key;return k==='Enter'||k===' ';}catch(_){return false;}}
 // Its handlers are running now (eventPhase is NONE once the dispatch is over: a kept event, a timer's later call).
 function dispatching(e){if(!NATIVE.phase)return false;try{return read(NATIVE.phase,e)!==0;}catch(_){return false;}}
 // Transient user activation, where the browser reports it (no input, no activation: a script's submit, a replay).
 function activated(){let ua=null;try{ua=win.navigator?win.navigator.userActivation:null;}catch(_){ua=null;}return !ua||typeof ua.isActive!=='boolean'||ua.isActive===true;}
 // The parent a nested run presents: the signal of an action of the same event that is still in flight.
 function parentOf(signal,event){for(const[c,x]of controllers)if(c.signal===signal&&x.event===event)return c;return null;}
 function run(event,kind,fn,opts){
  if(!Object.hasOwn(KINDS,kind))throw Error('ACTION_KIND_UNKNOWN');
  if(typeof fn!=='function')throw Error('ACTION_INVALID');
  const given=opts!==null&&typeof opts==='object'&&opts.parent!==undefined&&opts.parent!==null?opts.parent:null;
  if(!gesture(event))throw Error('CLICK_REQUIRED');
  let parent=null;
  if(given!==null){parent=parentOf(given,event);if(!parent||parent.signal.aborted)throw Error('CLICK_REQUIRED');}
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
  return Object.freeze({getItem(k){const s=realOf(get);return s?s.getItem(k):null;},key(i){const s=realOf(get);return s?s.key(i):null;},get length(){const s=realOf(get);return s?s.length:0;},
   setItem(k,v){return write(s=>s.setItem(k,v));},removeItem(k){return write(s=>s.removeItem(k));},clear(){return write(s=>s.clear());}});
 }
 /* IndexedDB objects as the old modules see them through a view: methods and accessors keep the real object as `this` (a Proxy
    that forwards to it, one per object). A write transaction needs a storage-writing action (ACTION_REQUIRED). In a STOPPED store a
    read of a stopped record asks for NO_RECORD (absent: DeviceActual then has no stored quote and computes nothing from one) and
    every write of one is MARKET_STORE_STOPPED, inside a click too; such a store takes record names only (the old module never
    passes anything else), so a key range or a cursor that could reach them is refused the same way. */
 const proxies=new WeakMap();
 function forward(real,hooks){if(real===null||typeof real!=='object')return real;let p=proxies.get(real);if(p)return p;
  p=new Proxy(real,{get(t,k){if(Object.hasOwn(hooks,k))return hooks[k](t);const v=Reflect.get(t,k);return typeof v==='function'?v.bind(t):v;},set(t,k,v){t[k]=v;return true;}});
  proxies.set(real,p);return p;}
 function openRequest(r,stopped){return forward(r,{result:t=>dbOf(t.result,stopped)});}
 function dbOf(db,stopped){return forward(db,{transaction:t=>(names,mode,o)=>{if(mode!==undefined&&mode!=='readonly'&&!writing())deny('ACTION_REQUIRED');return txOf(o===undefined?t.transaction(names,mode):t.transaction(names,mode,o),stopped);}});}
 function txOf(tx,stopped){return forward(tx,{db:t=>dbOf(t.db,stopped),objectStore:t=>name=>storeOf(t.objectStore(name),stopped,stopped&&Object.hasOwn(stopped,name)?stopped[name]:null)});}
 function storeOf(st,stopped,keys){const hooks={transaction:t=>txOf(t.transaction,stopped)};
  if(keys){const read=k=>{if(typeof k!=='string')deny('MARKET_STORE_STOPPED');return keys.includes(k)?NO_RECORD:k;},write=k=>{if(typeof k!=='string'||keys.includes(k)||k===NO_RECORD)deny('MARKET_STORE_STOPPED');return k;};
   for(const m of['get','getKey','count','getAll','getAllKeys','openCursor','openKeyCursor'])hooks[m]=t=>(k,...a)=>t[m](read(k),...a);
   hooks.put=t=>(v,k)=>t.put(v,write(k));hooks.add=t=>(v,k)=>t.add(v,write(k));hooks.delete=t=>k=>t.delete(write(k));
   hooks.clear=()=>()=>deny('MARKET_STORE_STOPPED');hooks.index=()=>()=>deny('MARKET_STORE_STOPPED');}
  return forward(st,hooks);}
 /* Opening a database that does not exist creates it (device-actual.js:187 onupgradeneeded), so open() passes only for a database
    this browser already lists (stores(): indexedDB.databases()) or inside a storage-writing action. readOnly views (the score path)
    never create one, not even inside an action. Without databases() nothing opens outside an action. A refused open is the normal
    "nothing stored yet" state (DEVICE_STORE_NOT_OPENED), not a blocked write. */
 function gatedIndexedDB(get,{readOnly=false}={}){
  return Object.freeze({
   open(name,version){const idb=realOf(get);if(!idb)throw Error('DEVICE_STORE_NOT_OPENED');const n=String(name),stopped=Object.hasOwn(STOPPED,n)?STOPPED[n]:null;
    if(stores.known.has(n))return openRequest(idb.open(name,version),stopped);
    if(!readOnly&&writing()){const r=idb.open(name,version);stores.known.add(n);return openRequest(r,stopped);}
    throw Error('DEVICE_STORE_NOT_OPENED');},
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
    this browser does not list is never opened, so nothing is created; a browser that cannot list its databases answers null
    (unknown) and removes nothing. Numbers only. */
 function existing(name){return new Promise((resolve,reject)=>{let r;try{r=realOf(()=>win.indexedDB).open(name);}catch(_){reject(Error('DEVICE_STORE_NOT_OPENED'));return;}
  r.onupgradeneeded=()=>{try{r.transaction.abort();}catch(_){}};// it was gone after all: the creation is aborted
  r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(Error('DEVICE_STORE_NOT_OPENED'));});}
 async function stoppedHeld(remove){const s=await refreshStores();if(!s.available||!s.supported)return null;let n=0;
  for(const[name,map]of Object.entries(STOPPED)){if(!s.names.includes(name))continue;const db=await existing(name);
   try{const names=Object.keys(map).filter(x=>db.objectStoreNames.contains(x));if(!names.length)continue;
    n+=await new Promise((resolve,reject)=>{const tx=db.transaction(names,remove?'readwrite':'readonly');let held=0;
     for(const x of names){const st=tx.objectStore(x);for(const k of map[x]){const r=st.getKey(k);r.onsuccess=()=>{if(r.result!==undefined)held++;};if(remove)st.delete(k);}}
     tx.oncomplete=()=>resolve(held);tx.onabort=tx.onerror=()=>reject(Error('DEVICE_STORAGE_UNAVAILABLE'));});}
   finally{db.close();}}
  return n;}
 const stoppedRecords=Object.freeze({
  count(){return stoppedHeld(false).catch(()=>null);},
  clear(signal){let ok=false;for(const[c,x]of controllers)if(c.signal===signal&&x.kind==='WRITE')ok=true;if(!ok)deny('ACTION_REQUIRED');return stoppedHeld(true);}});
 function view(overrides,{readOnlyStores=false}={}){
  if(!overrides||typeof overrides.fetch!=='function')throw Error('VIEW_FETCH_REQUIRED');
  const own=Object.defineProperties(Object.create(null),{localStorage:{value:gatedStorage(()=>win.localStorage)},sessionStorage:{value:gatedStorage(()=>win.sessionStorage)},
   indexedDB:{value:gatedIndexedDB(()=>win.indexedDB,{readOnly:readOnlyStores})},...Object.getOwnPropertyDescriptors(overrides)});
  return new Proxy(win,{
   get(t,k){if(typeof k==='string'&&k in own)return own[k];const v=Reflect.get(t,k);return typeof v==='function'&&typeof k==='string'&&/^[a-z]/.test(k)?v.bind(t):v;},
   has(t,k){return(typeof k==='string'&&k in own)||Reflect.has(t,k);},
   set(){return false;},defineProperty(){return false;},deleteProperty(){return false;}});
 }
 return Object.freeze({KINDS,STOPPED,run,cancel,active,writing,blocked:()=>blockedCount,classify,guard,gatedStorage,gatedIndexedDB,stores:refreshStores,stoppedRecords,view});
}
return Object.freeze({create,KINDS,STOPPED});
});
