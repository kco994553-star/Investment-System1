/* P1 device storage (IS2.store): the old keys and schemas of this device's saved settings, read freely, written only inside a
   user action (P1 implementation spec, Main decisions 2, 4, 7; design §1.1 (5); critique #4, #8).
   - Every read and write goes through the old module that owns the data (DeviceBackup.preferences, DeviceProfiles v2 trees,
     PlaybookScreen store, PublicScreens stars, DeviceBackup, VirtualTradingVHistory, GoogleSheetSetup.source, DeviceActual), on
     one store view: localStorage / sessionStorage gated (a write outside a click is ACTION_REQUIRED and changes nothing),
     public files through data.strictFetch only (no private destination at all).
   - IndexedDB (DeviceActual's database) is read only when it already exists; a read never creates it (DeviceActual opens with
     onupgradeneeded, device-actual.js:189). A backup restore without holdings on a device without the database creates none.
     A browser that cannot list databases (no indexedDB.databases()) opens it only inside a storage-writing click (Main decision
     4), so a backup download there still carries the stored holdings.
   - Backups: schemas /1–/4 as before; /5 (user objects: chart notes, macro estimates) needs validators that are not loaded in P1
     and is refused with BACKUP_USER_OBJECTS_UNSUPPORTED. A backup never holds a price, a sheet id, a token or the Worker address.
   - Sheet ids and the Worker address never come back to a screen: has() / set() only. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else{const I=root.IS2=root.IS2||{};I.store=api.create({win:root,action:I.action,data:I.data});}})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
// The old device keys, unchanged so existing devices keep their data (the node test checks each against the old constant).
const KEYS=Object.freeze({
 PERSONAL:'investment.web.v1.personal',// interests and groups (app.js, DeviceBackup)
 SETTINGS:'investment.web.v1.settings',// AppLanguage
 PROFILES:'investment.web.v1.profile-drafts',// DeviceProfiles v1 drafts (kept through backups)
 PROFILES_V2:'investment.web.v1.profile-drafts-v2',// QGV v2 personal weight trees
 PLAYBOOK:'investment.web.v1.playbook',// PlaybookScreen (TARGET v1 state lives inside it)
 INVESTOR_STARS:'investment.web.v1.investor-stars',// PublicScreens / DeviceBackup
 BACKUP_RESTORED:'investment.web.v1.backup-restored',// DeviceBackup restore marker (time + schema)
 V_HISTORY:'investment.web.v1.virtual-trading-v-scores',V_HISTORY_V2:'investment.web.v2.virtual-trading-v-scores',// VirtualTradingVHistory
 SHEET_SOURCE:'investment.web.v1.unified-sheet-source',// GoogleSheetSetup (PriceStore, PrivateTrades)
 UNIVERSE_SOURCE:'investment.web.v1.universe-source',// PrivateSubsetView's own Universe tab source
 WORKER_ORIGIN:'investment.web.v1.private-history-origin',// PrivateHistory / PriceStore / WorkerQuoteFallback
 PRICE_STORE_ENABLED:'investment.web.v1.price-store-enabled',// PriceStore opt-in flag (no price)
 DEVICE_DB:'investment-device-actual-v1'});// DeviceActual IndexedDB
const CATALOG='actual-catalog.json',ID=/^[A-Za-z0-9_-]{20,100}$/;
const object=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
function deepFreeze(v){if(v&&typeof v==='object'&&!Object.isFrozen(v)){Object.freeze(v);for(const x of Object.values(v))deepFreeze(x);}return v;}
const copy=v=>v===undefined?undefined:JSON.parse(JSON.stringify(v));
function create({win,action,data}){
 if(!action||typeof action.view!=='function'||!data||typeof data.strictFetch!=='function')throw Error('LAYER_MISSING');
 const need=n=>{const m=win[n];if(!m)throw Error('READER_MISSING');return m;};
 const subs=new Set(),changed=what=>{for(const fn of[...subs]){try{fn(what);}catch(_){}}};
 // The device database exists; or the browser cannot say (no databases()) and a storage-writing click is in flight, where the gate
 // lets the real open run (outside a click such a browser reads no stored holdings: DEVICE_STORE_NOT_OPENED).
 const known=async()=>(await action.stores()).names.includes(KEYS.DEVICE_DB);
 const exists=async()=>{const s=await action.stores();return s.names.includes(KEYS.DEVICE_DB)||s.supported===false&&s.available===true&&action.writing();};
 /* DeviceActual as the store's old callers see it (DeviceBackup.read / restore): stored holdings only from an existing database,
    and a restore that has no holdings to write does not create one. Everything else is the module unchanged. */
 let actualMemo=null;
 function actual(){const DA=win.DeviceActual;if(!DA)return DA;if(actualMemo&&actualMemo.of===DA)return actualMemo.api;
  const api=Object.freeze({...DA,
   async readHoldings(view,catalog){return await exists()?DA.readHoldings(view,catalog):null;},
   async restoreHoldings(view,catalog,snapshot){if(snapshot===null&&!(await known()))return null;return DA.restoreHoldings(view,catalog,snapshot);}});
  actualMemo={of:DA,api};return api;}
 const view=action.view(Object.defineProperties({fetch:data.strictFetch},{DeviceActual:{enumerable:true,get:actual}}));
 // The gated localStorage every store call (and engines.js) hands to the old modules.
 const storage=view.localStorage;
 const write=(event,what,fn)=>action.run(event,'WRITE',signal=>{const out=fn(signal);if(out&&typeof out.then==='function')return out.then(x=>{changed(what);return x;});changed(what);return out;});

 // ---- interests and groups (1.1.4): DeviceBackup.preferences is the validator (app.js validatePrefs moved here)
 function readPrefs(){const B=need('DeviceBackup'),raw=storage.getItem(KEYS.PERSONAL);if(raw===null||raw==='')return{state:'EMPTY',value:{version:1,interests:[],groups:[]}};
  try{return{state:'OK',value:B.preferences(JSON.parse(raw))};}catch(_){return{state:'INVALID',value:null};}}
 const prefs=()=>deepFreeze(readPrefs());
 // An unreadable stored value is never overwritten (app.js save(): the original is kept, the user exports instead).
 function savePrefs(event,next){return write(event,'PERSONAL',()=>{const B=need('DeviceBackup');if(readPrefs().state==='INVALID')throw Error('PREFS_STORAGE_INVALID');
  let v;try{v=B.preferences(next);}catch(_){throw Error('PREFS_INVALID');}storage.setItem(KEYS.PERSONAL,JSON.stringify(v));return deepFreeze(copy(v));});}

 // ---- personal QGV v2 weight trees (2.2): DeviceProfiles v2 storage
 function weights(){const DP=need('DeviceProfiles');try{return deepFreeze({state:'OK',value:DP.readV2(storage)});}catch(_){return deepFreeze({state:'INVALID',value:null});}}
 // A save of an open profile is its next version (same id), otherwise a new profile (DeviceProfiles.saveV2). Returns the saved one.
 function saveWeights(event,spec){return write(event,'PROFILES_V2',()=>{const DP=need('DeviceProfiles');let doc,next;
  try{doc=DP.readV2(storage);}catch(_){throw Error('WEIGHTS_STORAGE_INVALID');}
  try{next=DP.saveV2(doc,spec);}catch(_){throw Error('WEIGHTS_INVALID');}
  DP.writeV2(storage,next);return deepFreeze(copy(next.profiles.find(p=>!doc.profiles.some(q=>q.id===p.id&&q.version===p.version))||null));});}

 // ---- ACTUAL holdings (6.1): stored only on this device (IndexedDB), read only when the database exists
 async function holdings(){const DA=need('DeviceActual'),none=reason=>deepFreeze({state:'NOT_AVAILABLE',reason,snapshot:null,source:null,as_of:null});
  const catalog=await data.static(CATALOG);if(!catalog)return none('CATALOG_NOT_AVAILABLE');if(!(await exists()))return none('DEVICE_STORE_NOT_OPENED');
  try{const r=await DA.effectiveHoldings(view,catalog);return deepFreeze({state:r&&r.snapshot?'OK':'EMPTY',reason:null,snapshot:r?copy(r.snapshot):null,source:r?r.source:null,as_of:r?r.as_of:null});}
  catch(_){return none('DEVICE_STORAGE_UNAVAILABLE');}}

 // ---- playbook records (detail screen playbook, 6.1.x): PlaybookScreen's device store
 function playbook(){const PB=need('PlaybookScreen');try{return deepFreeze({state:'OK',value:PB.read(storage)});}catch(_){return deepFreeze({state:'INVALID',value:null});}}
 const saveThesis=(event,symbol,thesis,invalidation,ev)=>write(event,'PLAYBOOK',()=>deepFreeze(need('PlaybookScreen').saveThesis(storage,symbol,thesis,invalidation,ev)));
 const saveHold=(event,symbol,row)=>write(event,'PLAYBOOK',()=>deepFreeze(need('PlaybookScreen').saveHold(storage,symbol,row)));
 const saveRecord=(event,row)=>write(event,'PLAYBOOK',()=>deepFreeze(need('PlaybookScreen').saveRecord(storage,row)));

 // ---- investor stars (2.3.1)
 const stars=()=>Object.freeze([...need('PublicScreens').readStars(storage)]);
 const toggleStar=(event,cik)=>write(event,'INVESTOR_STARS',()=>Object.freeze([...need('PublicScreens').toggleStar(storage,cik)]));

 // ---- one price-free backup (DeviceBackup): always written as /4 (no user objects); /1–/4 restored; /5 refused
 function parseBackup(text){const B=need('DeviceBackup');let p=text;
  if(typeof text==='string'){if(new TextEncoder().encode(text).length>B.MAX_BYTES)throw Error('BACKUP_TOO_LARGE');try{p=JSON.parse(text);}catch(_){throw Error('BACKUP_INVALID');}}
  if(!object(p))throw Error('BACKUP_INVALID');if(p.schema===B.USER_OBJECTS_SCHEMA)throw Error('BACKUP_USER_OBJECTS_UNSUPPORTED');if(!B.accepts(p))throw Error('BACKUP_INVALID');return p;}
 async function createBackup(){const B=need('DeviceBackup'),catalog=await data.static(CATALOG);return deepFreeze(await B.read(view,catalog));}
 const backup=Object.freeze({
  create:createBackup,
  download(event){return action.run(event,'WRITE',async()=>{const B=need('DeviceBackup'),payload=await createBackup();B.download(view,payload);return Object.freeze({schema:payload.schema});});},
  // Merges into this device as DeviceBackup.restore does (all keys or none: it rolls back a failed write).
  restore(event,text){return write(event,'BACKUP',async()=>{const B=need('DeviceBackup'),payload=parseBackup(text),catalog=await data.static(CATALOG);await B.restore(view,catalog,payload);return Object.freeze({schema:payload.schema});});},
  restored(){const B=need('DeviceBackup');return B.restoredNotice(storage);}});

 // ---- device V history (6.3): read only (recording on a click is an owner decision, D-21)
 function vHistory(){const VH=need('VirtualTradingVHistory');return deepFreeze(copy({v1:VH.readStore(storage),v2:VH.readV2(storage)}));}

 // ---- sheet ids and the Worker address: never returned, only whether one is set
 const sheetSource=Object.freeze({
  has(){const GS=need('GoogleSheetSetup');try{return !!GS.source(view);}catch(_){return false;}},
  // The unified sheet (PriceStore price tabs, Trades tab). '' or null removes it.
  set(event,value){return write(event,'SHEET_SOURCE',()=>{const GS=need('GoogleSheetSetup');let id;try{id=GS.source(view,value===null||value===undefined?'':String(value));}catch(_){throw Error('SHEET_SOURCE_INVALID');}return Object.freeze({set:!!id});});}});
 // The Universe tab source (PrivateSubsetView.mountSettings rule: an id or a sheet URL; its own key, not the unified sheet).
 const universeSource=Object.freeze({
  has(){const v=storage.getItem(KEYS.UNIVERSE_SOURCE);return typeof v==='string'&&ID.test(v);},
  set(event,value){return write(event,'UNIVERSE_SOURCE',()=>{const Q=need('GoogleSheetQuotes'),text=value===null||value===undefined?'':String(value);let id='';
   if(text){try{id=Q.extractSpreadsheetId(text);}catch(_){throw Error('UNIVERSE_SOURCE_INVALID');}storage.setItem(KEYS.UNIVERSE_SOURCE,id);}else storage.removeItem(KEYS.UNIVERSE_SOURCE);return Object.freeze({set:!!id});});}});
 // The Worker address (PrivateHistory.mountSettings rule); price requests need it equal to the approved app-config origin.
 const approvedOrigin=()=>{const c=object(win.InvestmentAppConfig)?win.InvestmentAppConfig:{};return c.privateHistoryEnabled===true&&typeof c.privateHistoryWorkerOrigin==='string'?c.privateHistoryWorkerOrigin:null;};
 function storedOrigin(){const PH=need('PrivateHistory'),v=storage.getItem(KEYS.WORKER_ORIGIN);if(!v)return'';try{return PH.parseWorkerOrigin(v);}catch(_){return'';}}
 const workerOrigin=Object.freeze({
  has:()=>!!storedOrigin(),approved:()=>{const o=storedOrigin();return !!o&&o===approvedOrigin();},
  set(event,value){return write(event,'WORKER_ORIGIN',()=>{const PH=need('PrivateHistory'),text=value===null||value===undefined?'':String(value);let o='';
   if(text){try{o=PH.parseWorkerOrigin(text);}catch(_){throw Error('REQUEST_INVALID');}storage.setItem(KEYS.WORKER_ORIGIN,o);}else storage.removeItem(KEYS.WORKER_ORIGIN);
   return Object.freeze({set:!!o,approved:!!o&&o===approvedOrigin()});});}});

 function subscribe(fn,{signal}={}){if(typeof fn!=='function')throw Error('SUBSCRIBER_INVALID');if(signal&&signal.aborted)return()=>{};subs.add(fn);const off=()=>{subs.delete(fn);};if(signal)signal.addEventListener('abort',off,{once:true});return off;}
 const api={KEYS,storage,prefs,savePrefs,weights,saveWeights,holdings,playbook,saveThesis,saveHold,saveRecord,stars,toggleStar,backup,vHistory,sheetSource,universeSource,workerOrigin,subscribe};
 // DeviceProfiles' preset list, read when asked (the old module loads before this one; tests swap modules).
 Object.defineProperty(api,'PRODUCT_PRESETS',{enumerable:true,get:()=>need('DeviceProfiles').PRODUCT_PRESETS});
 return Object.freeze(api);
}
return Object.freeze({create,KEYS});
});
