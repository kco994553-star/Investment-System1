/* P1 action gate (IS2.action): every Sheet / Worker / OAuth request and every device-storage write runs inside a trusted user
   click, and only to the destinations that click's kind allows (P1 implementation spec, Main decisions 2 and 4).
   - run(event, kind, fn): fn(signal) runs in the same tick (GIS login must start inside the click) and the kind stays in flight
     until fn settles or cancel(kind). The event must be a real gesture of this window read through the window's own Event
     accessors (a forged object or a Proxy that only claims isTrusted makes them throw), a click or Enter / Space keydown (not a
     submit: form.requestSubmit() and a script's button.click() make trusted submits), still being dispatched, with transient user
     activation where the browser reports it. A kept event replayed later is refused, except by a nested run while an action
     started from that same event is still in flight (engines.target.syncScoringPrices -> prices.syncSymbols after awaits).
   - guard(url, init, {sheets}): the destination check every private request makes (the price view in prices.js). Private
     destinations pass only while an action whose kind allows them is in flight, and Sheets only for the spreadsheets this device
     saved; otherwise blocked() grows and CLICK_REQUIRED (or DESTINATION_UNKNOWN) is thrown.
   - view(overrides): the window as old modules see it (same binding rule as DataRefresh.proxy, data-refresh.js:49: lowercase
     window functions keep the real window as `this`, so dispatchEvent / addEventListener / setTimeout work). Every view replaces
     localStorage / sessionStorage / indexedDB with the gated versions below and refuses writes to window globals (DataRefresh's
     30 s PriceStore swap fails inside its own try/catch).
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
function create({win}){
 // live: event -> number of its actions in flight (an entry exists only while at least one is).
 const flight=new Map(),controllers=new Map(),live=new WeakMap(),stores={known:new Set(),supported:null};let blockedCount=0;
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
 function run(event,kind,fn){
  if(!Object.hasOwn(KINDS,kind))throw Error('ACTION_KIND_UNKNOWN');
  if(typeof fn!=='function')throw Error('ACTION_INVALID');
  const nested=live.has(event);
  if(!gesture(event)||!nested&&(!dispatching(event)||!activated()))throw Error('CLICK_REQUIRED');
  const c=new win.AbortController();let left=false;
  // Leaves the gate once: when fn settles, or at cancel(kind), whichever comes first.
  const done=()=>{if(left)return;left=true;flight.set(kind,flight.get(kind)-1);controllers.delete(c);const n=live.get(event)-1;if(n>0)live.set(event,n);else live.delete(event);};
  flight.set(kind,flight.has(kind)?flight.get(kind)+1:1);controllers.set(c,{kind,done});live.set(event,live.has(event)?live.get(event)+1:1);
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
 /* IndexedDB: opening a database that does not exist creates it (device-actual.js:187 onupgradeneeded), so open() passes only for
    a database this browser already lists (stores(): indexedDB.databases()) or inside a storage-writing action. readOnly views (the
    score path) never create one, not even inside an action. Without databases() nothing opens outside an action. A refused open
    is the normal "nothing stored yet" state (DEVICE_STORE_NOT_OPENED), not a blocked write. */
 function gatedIndexedDB(get,{readOnly=false}={}){
  return Object.freeze({
   open(name,version){const idb=realOf(get);if(!idb)throw Error('DEVICE_STORE_NOT_OPENED');const n=String(name);
    if(stores.known.has(n))return idb.open(name,version);
    if(!readOnly&&writing()){const r=idb.open(name,version);stores.known.add(n);return r;}
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
 function view(overrides,{readOnlyStores=false}={}){
  if(!overrides||typeof overrides.fetch!=='function')throw Error('VIEW_FETCH_REQUIRED');
  const own=Object.defineProperties(Object.create(null),{localStorage:{value:gatedStorage(()=>win.localStorage)},sessionStorage:{value:gatedStorage(()=>win.sessionStorage)},
   indexedDB:{value:gatedIndexedDB(()=>win.indexedDB,{readOnly:readOnlyStores})},...Object.getOwnPropertyDescriptors(overrides)});
  return new Proxy(win,{
   get(t,k){if(typeof k==='string'&&k in own)return own[k];const v=Reflect.get(t,k);return typeof v==='function'&&typeof k==='string'&&/^[a-z]/.test(k)?v.bind(t):v;},
   has(t,k){return(typeof k==='string'&&k in own)||Reflect.has(t,k);},
   set(){return false;},defineProperty(){return false;},deleteProperty(){return false;}});
 }
 return Object.freeze({KINDS,run,cancel,active,writing,blocked:()=>blockedCount,classify,guard,gatedStorage,gatedIndexedDB,stores:refreshStores,view});
}
return Object.freeze({create,KINDS});
});
