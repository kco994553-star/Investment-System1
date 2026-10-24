/* P1 action gate (IS2.action): every Sheet / Worker / OAuth request and every device-storage write runs inside a trusted user
   click, and only to the destinations that click's kind allows (P1 implementation spec, Main decisions 2 and 4).
   - run(event, kind, fn): fn(signal) runs in the same tick (GIS login must start inside the click) and the kind stays in flight
     until fn settles. A synthetic event (isTrusted false) or a plain object that only claims isTrusted is refused: CLICK_REQUIRED.
   - guard(url, init): the destination check every private request makes (the price view in prices.js). Private destinations
     pass only while an action whose kind allows them is in flight; otherwise blocked() grows and CLICK_REQUIRED is thrown.
   - view(overrides): the window as old modules see it (same binding rule as DataRefresh.proxy, data-refresh.js:49: lowercase
     window functions keep the real window as `this`, so dispatchEvent / addEventListener / setTimeout work). Every view replaces
     localStorage / sessionStorage / indexedDB with the gated versions below and refuses writes to window globals (DataRefresh's
     30 s PriceStore swap fails inside its own try/catch).
   Nothing here reads or writes storage by itself and nothing is sent anywhere. */
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
 const flight=new Map(),controllers=new Map(),stores={known:new Set(),supported:null};let blockedCount=0;
 const inFlight=k=>(flight.get(k)>0);
 const active=kind=>kind===undefined?[...flight.values()].some(n=>n>0):inFlight(kind);
 const writing=()=>WRITERS.some(inFlight);
 // A real user gesture: a trusted click, submit, or Enter / Space on a focused control.
 function trusted(e){return typeof win.Event==='function'&&e instanceof win.Event&&e.isTrusted===true&&(e.type==='click'||e.type==='submit'||e.type==='keydown'&&(e.key==='Enter'||e.key===' '));}
 function enter(kind,c){flight.set(kind,flight.has(kind)?flight.get(kind)+1:1);controllers.set(c,kind);}
 function leave(kind,c){flight.set(kind,flight.get(kind)-1);controllers.delete(c);}
 function run(event,kind,fn){
  if(!Object.hasOwn(KINDS,kind))throw Error('ACTION_KIND_UNKNOWN');
  if(typeof fn!=='function')throw Error('ACTION_INVALID');
  if(!trusted(event))throw Error('CLICK_REQUIRED');
  const c=new win.AbortController();enter(kind,c);let out;
  try{out=fn(c.signal);}catch(e){leave(kind,c);throw e;}
  if(out&&typeof out.then==='function')return Promise.resolve(out).finally(()=>leave(kind,c));
  leave(kind,c);return out;
 }
 // Cancels the in-flight actions of one kind (their fn sees signal.aborted); they still leave the gate when fn settles.
 function cancel(kind){for(const[c,k]of controllers)if(k===kind)c.abort();}
 function deny(code){blockedCount++;throw Error(code);}
 // Destination class of one request: PUBLIC (same origin; the caller then uses data.strictFetch), SHEETS_READ / SHEETS_WRITE,
 // OAUTH, WORKER_HISTORY / WORKER (the public Worker origin of app-config.js), else UNKNOWN.
 function classify(input,init){
  let u=null;try{u=new win.URL(typeof input==='string'?input:String(input&&input.url),win.location.href);}catch(_){return 'UNKNOWN';}
  if(u.origin===win.location.origin)return 'PUBLIC';
  const method=String(init&&init.method||'GET').toUpperCase(),config=win.InvestmentAppConfig,worker=config&&typeof config.privateHistoryWorkerOrigin==='string'?config.privateHistoryWorkerOrigin:null;
  if(u.origin===SHEETS)return method==='GET'?'SHEETS_READ':'SHEETS_WRITE';
  if(OAUTH.includes(u.origin))return 'OAUTH';
  if(worker&&u.origin===worker)return u.pathname==='/history'?'WORKER_HISTORY':'WORKER';
  return 'UNKNOWN';
 }
 function allows(dest){for(const[k,n]of flight)if(n>0&&KINDS[k].includes(dest))return true;return false;}
 function guard(input,init){const dest=classify(input,init);if(dest==='PUBLIC')return dest;if(dest==='UNKNOWN')deny('DESTINATION_UNKNOWN');if(!allows(dest))deny('CLICK_REQUIRED');return dest;}
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
 async function refreshStores(){const idb=realOf(()=>win.indexedDB);
  if(!idb||typeof idb.databases!=='function')stores.supported=false;
  else{try{const list=await idb.databases();stores.known=new Set((Array.isArray(list)?list:[]).map(d=>d&&d.name).filter(n=>typeof n==='string'));stores.supported=true;}catch(_){stores.supported=false;}}
  return Object.freeze({supported:stores.supported,names:Object.freeze([...stores.known].sort())});}
 function view(overrides,{readOnlyStores=false}={}){
  if(!overrides||typeof overrides.fetch!=='function')throw Error('VIEW_FETCH_REQUIRED');
  const own=Object.defineProperties(Object.create(null),{localStorage:{value:gatedStorage(()=>win.localStorage)},sessionStorage:{value:gatedStorage(()=>win.sessionStorage)},
   indexedDB:{value:gatedIndexedDB(()=>win.indexedDB,{readOnly:readOnlyStores})},...Object.getOwnPropertyDescriptors(overrides)});
  return new Proxy(win,{
   get(t,k){if(typeof k==='string'&&k in own)return own[k];const v=Reflect.get(t,k);return typeof v==='function'&&typeof k==='string'&&/^[a-z]/.test(k)?v.bind(t):v;},
   has(t,k){return(typeof k==='string'&&k in own)||Reflect.has(t,k);},
   set(){return false;},defineProperty(){return false;},deleteProperty(){return false;}});
 }
 return Object.freeze({KINDS,run,cancel,active,blocked:()=>blockedCount,classify,guard,gatedStorage,gatedIndexedDB,stores:refreshStores,view});
}
return Object.freeze({create,KINDS});
});
