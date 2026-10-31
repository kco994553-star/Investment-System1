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
   - Backups: schemas /1–/5 through DeviceBackup unchanged. /5 adds the opt-in user objects (chart notes and scenarios, macro
     cycle estimates) validated by their owners' own validators, ChartWorkbench and MacroCycleRing (reused byte-identical; loading
     them has no side effect), which DeviceBackup looks up itself (device-backup.js:26-32): owner 2026-10-24, nothing written again.
     A backup never holds a price, a sheet id, a token or the Worker address.
   - Device quotes (owner 2026-10-24, DC-18): never stored by the new frontend (the gate stops them, action.js STOPPED). What a
     device stored before stays until the user removes it: marketQuotes.count() (a number only) and marketQuotes.clear(event).
   - Device V history (owner 2026-10-31, DC-31: no device V history): neither read nor written. Its two keys are stopped at the gate
     (action.js STOPPED: reads absent, writes refused); what a device stored before stays until the user removes it on a click
     (vHistoryKeys.count() a number only, vHistoryKeys.clear(event): the manual settings action, DC-18 precedent).
   - Sheet ids and the Worker address never come back to a screen: has() / set() only.
   - Recent searches (1.1.4, P2-1, Main): the old home's device list (home-screen.js RECENT_KEY): entity keys only, newest first,
     at most 6, never the query text. Read as the old readRecent read it (invalid entries dropped); the new screen writes
     COMPANY:<id> keys only, on the selection click.
   - Macro cycle user estimates (4.4, 2026-10-31 table 1-3: kept on this device, in backup /5): MacroCycleRing's own store
     (readUserStore / writeUserStore / parseUserExport) on the gated storage, the old key and schema macro-cycle-user-estimate/2;
     seq and saved_at are set here as the old ring's save click set them (macro-cycle-ring.js:350-351); an unreadable stored value
     is never overwritten (writeUser refuses it).
   - Prompt favorites and personal copies (7.1.4, table 1-3: kept in this browser): the old prompt page's two keys and shapes
     (research-bridge.js:189-208 PL_FAV_KEY / PL_COPY_KEY, plRead / plState / the save rules), read as plState read them and
     written only on a click. DeviceBackup /4 and /5 do not carry them (this browser only).
   - Chart notes and scenarios (3.3 · 3.1.3, bundle 2, table 1-3: kept on this device, in backup /5): ChartWorkbench's own user
     objects (key and schema chart-user-objects/1, validUserObject, createDeviceUserStore) on the gated storage; id, author,
     price_basis and the times are set here; an unreadable stored value is never overwritten and unreadable entries are kept. */
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
 V_HISTORY:'investment.web.v1.virtual-trading-v-scores',V_HISTORY_V2:'investment.web.v2.virtual-trading-v-scores',// VirtualTradingVHistory (stopped, DC-31)
 SHEET_SOURCE:'investment.web.v1.unified-sheet-source',// GoogleSheetSetup (PriceStore, PrivateTrades)
 UNIVERSE_SOURCE:'investment.web.v1.universe-source',// PrivateSubsetView's own Universe tab source
 WORKER_ORIGIN:'investment.web.v1.private-history-origin',// PrivateHistory / PriceStore / WorkerQuoteFallback
 PRICE_STORE_ENABLED:'investment.web.v1.price-store-enabled',// PriceStore opt-in flag (no price)
 CHART_USER_OBJECTS:'investment.web.v1.chart-user-objects',// ChartWorkbench user notes / scenarios (backup /5)
 MACRO_USER_ESTIMATES:'investment.web.v1.macro-cycle-user-estimate',// MacroCycleRing user estimates (backup /5)
 RECENT:'investment.web.v1.recent-search',// home-screen.js RECENT_KEY: recent search entity keys (no query text)
 PROMPT_FAVORITES:'investment.web.v1.prompt-favorites',// research-bridge.js PL_FAV_KEY: favorite prompt ids (not in a backup)
 PROMPT_COPIES:'investment.web.v1.prompt-personal-copies',// research-bridge.js PL_COPY_KEY: personal prompt copies (not in a backup)
 DEVICE_DB:'investment-device-actual-v1'});// DeviceActual IndexedDB
const CATALOG='actual-catalog.json',ID=/^[A-Za-z0-9_-]{20,100}$/;
// home-screen.js RECENT_MAX / KEY_SHAPE (read), and the one key shape the new screen writes.
const RECENT_MAX=6,RECENT_SHAPE=/^(COMPANY|INDUSTRY|INVESTOR|MACRO):[A-Za-z0-9_.:\-]{1,64}$/,RECENT_WRITE=/^COMPANY:[A-Za-z0-9_.:\-]{1,64}$/;
// research-bridge.js PL_MAX_CHARS / PL_MAX_COPIES; a prompt id is a plain token (catalog ids such as plv1.fund.030).
const PROMPT_MAX_CHARS=50000,PROMPT_MAX_COPIES=100,PROMPT_ID=/^[A-Za-z0-9_.:-]{1,128}$/;
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

 // ---- recent searches (1.1.4): home-screen.js readRecent / pushRecent / clearRecent on the gated storage
 function readRecent(){let v;try{v=JSON.parse(storage.getItem(KEYS.RECENT)||'[]');}catch(_){return[];}
  return Array.isArray(v)?[...new Set(v.filter(x=>typeof x==='string'&&RECENT_SHAPE.test(x)))].slice(0,RECENT_MAX):[];}
 const recent=()=>Object.freeze(readRecent());
 // The chosen company first, an earlier copy of it removed, at most RECENT_MAX. Returns the stored list.
 function pushRecent(event,key){return write(event,'RECENT',()=>{if(typeof key!=='string'||!RECENT_WRITE.test(key))throw Error('RECENT_KEY_INVALID');
  const list=[key,...readRecent().filter(x=>x!==key)].slice(0,RECENT_MAX);storage.setItem(KEYS.RECENT,JSON.stringify(list));return Object.freeze(list);});}
 const clearRecent=event=>write(event,'RECENT',()=>{storage.removeItem(KEYS.RECENT);return Object.freeze([]);});

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

 // ---- macro cycle user estimates (4.4): MacroCycleRing's store on the gated storage (old key and schema, backup /5)
 function readEstimates(){const MC=need('MacroCycleRing');try{return{state:'OK',value:MC.readUserStore(storage)};}catch(_){return{state:'INVALID',value:null};}}
 function saveEstimates(rings){const MC=need('MacroCycleRing');if(!MC.writeUserStore({schema:MC.USER_SCHEMA,rings},storage))throw Error('MACRO_ESTIMATE_SAVE_FAILED');}
 const macroEstimates=Object.freeze({
  // {state:'OK'|'EMPTY'|'INVALID', value:{schema, rings:{<ring key>:[entry, oldest first]}}|null}
  read(){const r=readEstimates();return deepFreeze(r.state==='OK'&&!Object.keys(r.value.rings).length?{state:'EMPTY',value:r.value}:r);},
  // One more record of one ring (economy | market | industry:<group>): checked by MacroCycleRing.parseUserExport; returns it.
  add(event,key,entry){return write(event,'MACRO_USER_ESTIMATES',()=>{const MC=need('MacroCycleRing'),cur=readEstimates();if(cur.state!=='OK')throw Error('MACRO_ESTIMATES_STORAGE_INVALID');
   const list=cur.value.rings[key]||[],seq=list.reduce((m,e)=>Math.max(m,e.seq),0)+1;let clean;
   try{clean=MC.parseUserExport({schema:MC.USER_SCHEMA,rings:{[key]:[{...entry,seq,saved_at:new Date().toISOString().slice(0,19)+'Z'}]}}).rings[key][0];}catch(_){throw Error('MACRO_ESTIMATE_INVALID');}
   saveEstimates({...cur.value.rings,[key]:[...list,clean]});return deepFreeze(copy(clean));});},
  // The user's delete of one record (by its seq); returns the ring's remaining records.
  remove(event,key,seq){return write(event,'MACRO_USER_ESTIMATES',()=>{const cur=readEstimates();if(cur.state!=='OK')throw Error('MACRO_ESTIMATES_STORAGE_INVALID');
   const list=cur.value.rings[key]||[],next=list.filter(e=>e.seq!==seq);if(next.length===list.length)throw Error('MACRO_ESTIMATE_NOT_FOUND');
   const rings={...cur.value.rings};if(next.length)rings[key]=next;else delete rings[key];saveEstimates(rings);return deepFreeze(copy(next));});}});

 // ---- prompt favorites and personal copies (7.1.4): research-bridge.js plRead / plState on the gated storage
 const readJson=key=>{try{return JSON.parse(storage.getItem(key)||'null');}catch(_){return null;}};
 function readFavorites(){const v=readJson(KEYS.PROMPT_FAVORITES);return Array.isArray(v)?[...new Set(v.filter(x=>typeof x==='string'&&PROMPT_ID.test(x)))]:[];}
 function readCopies(){const v=readJson(KEYS.PROMPT_COPIES),out={};if(object(v))for(const[id,c]of Object.entries(v))
  if(PROMPT_ID.test(id)&&object(c)&&typeof c.body==='string')out[id]={body:c.body.slice(0,PROMPT_MAX_CHARS),saved_at:String(c.saved_at||''),content_version:String(c.content_version||'')};return out;}
 const promptFavorites=Object.freeze({
  read:()=>Object.freeze(readFavorites()),
  // The ★ click: adds or removes one id; returns the stored list.
  toggle(event,id){return write(event,'PROMPT_FAVORITES',()=>{if(typeof id!=='string'||!PROMPT_ID.test(id))throw Error('PROMPT_ID_INVALID');
   const cur=readFavorites(),next=cur.includes(id)?cur.filter(x=>x!==id):[...cur,id];storage.setItem(KEYS.PROMPT_FAVORITES,JSON.stringify(next));return Object.freeze(next);});}});
 const promptCopies=Object.freeze({
  read:()=>deepFreeze(readCopies()),
  // The save click (research-bridge.js:288-292 rules): not empty, at most 50,000 characters, at most 100 copies; returns the saved copy.
  save(event,id,body,contentVersion){return write(event,'PROMPT_COPIES',()=>{if(typeof id!=='string'||!PROMPT_ID.test(id))throw Error('PROMPT_ID_INVALID');
   if(typeof body!=='string'||!body.trim())throw Error('PROMPT_COPY_EMPTY');if(body.length>PROMPT_MAX_CHARS)throw Error('PROMPT_COPY_TOO_LONG');
   const cur=readCopies();if(!Object.hasOwn(cur,id)&&Object.keys(cur).length>=PROMPT_MAX_COPIES)throw Error('PROMPT_COPIES_FULL');
   const c={body,saved_at:new Date().toISOString(),content_version:String(contentVersion||'')};storage.setItem(KEYS.PROMPT_COPIES,JSON.stringify({...cur,[id]:c}));return deepFreeze(copy(c));});},
  // The delete click; returns whether a copy was removed.
  remove(event,id){return write(event,'PROMPT_COPIES',()=>{const cur=readCopies();if(!Object.hasOwn(cur,id))return false;delete cur[id];storage.setItem(KEYS.PROMPT_COPIES,JSON.stringify(cur));return true;});}});

 // ---- chart notes and scenarios (3.3 · 3.1.3): ChartWorkbench's device user store on the gated storage (old key and schema, backup /5)
 const NOTE_STATE=Object.freeze({EMPTY:'EMPTY',LOADED:'OK',PARTLY_INVALID:'PARTLY_INVALID',STORE_INVALID:'INVALID'});
 // chart-workbench.js newId: 'u-' and 8 random bytes in base 36 (validUserObject: /^u-[a-z0-9]{6,32}$/).
 function noteId(){const b=new Uint8Array(8),c=win.crypto;if(c&&typeof c.getRandomValues==='function')c.getRandomValues(b);else for(let i=0;i<b.length;i++)b[i]=Math.floor(Math.random()*256);
  return 'u-'+[...b].map(x=>x.toString(36)).join('').slice(0,16).padEnd(6,'0');}
 const chartNotes=Object.freeze({
  // {state:'OK'|'EMPTY'|'PARTLY_INVALID'|'INVALID'|'UNAVAILABLE', items:[valid user objects, stored order], unreadable:n}
  read(){const r=need('ChartWorkbench').createDeviceUserStore(storage).load();return deepFreeze({state:NOTE_STATE[r.code]||'UNAVAILABLE',items:copy(r.items),unreadable:r.unreadable});},
  // One more note (chart-annotation/1) or scenario (chart-scenario/1): the caller's fields, checked by validUserObject; returns it.
  add(event,obj){return write(event,'CHART_USER_OBJECTS',()=>{const CW=need('ChartWorkbench'),st=CW.createDeviceUserStore(storage),cur=st.load();
   if(cur.code==='STORE_INVALID'||cur.code==='STORAGE_UNAVAILABLE')throw Error('CHART_NOTES_STORAGE_INVALID');
   if(cur.items.length>=CW.USER_LIMIT)throw Error('CHART_NOTES_FULL');
   const now=new Date().toISOString(),item=object(obj)?{...copy(obj),id:noteId(),author:'USER',price_basis:'RAW_CLOSE',created_at:now,updated_at:now}:null;
   if(!item||!['chart-annotation/1','chart-scenario/1'].includes(item.schema)||!CW.validUserObject(item))throw Error('CHART_NOTE_INVALID');
   if(!st.save([...cur.items,item]))throw Error('CHART_NOTE_SAVE_FAILED');return deepFreeze(copy(item));});},
  // The user's delete of one object by id; returns how many valid objects remain.
  remove(event,id){return write(event,'CHART_USER_OBJECTS',()=>{const CW=need('ChartWorkbench'),st=CW.createDeviceUserStore(storage),cur=st.load();
   if(cur.code==='STORE_INVALID'||cur.code==='STORAGE_UNAVAILABLE')throw Error('CHART_NOTES_STORAGE_INVALID');
   const next=cur.items.filter(o=>o.id!==id);if(next.length===cur.items.length)throw Error('CHART_NOTE_NOT_FOUND');
   if(!st.save(next))throw Error('CHART_NOTE_SAVE_FAILED');return next.length;});}});

 // ---- investor stars (2.3.1)
 const stars=()=>Object.freeze([...need('PublicScreens').readStars(storage)]);
 const toggleStar=(event,cik)=>write(event,'INVESTOR_STARS',()=>Object.freeze([...need('PublicScreens').toggleStar(storage,cik)]));

 // ---- one price-free backup (DeviceBackup): /4, or /5 with the user's opt-in user objects (app.js exportDeviceBackup); /1–/5 restored
 function parseBackup(text){const B=need('DeviceBackup');let p=text;
  if(typeof text==='string'){if(new TextEncoder().encode(text).length>B.MAX_BYTES)throw Error('BACKUP_TOO_LARGE');try{p=JSON.parse(text);}catch(_){throw Error('BACKUP_INVALID');}}
  if(!object(p)||!B.accepts(p))throw Error('BACKUP_INVALID');return p;}
 // userObjects: the "사용자 작성 객체 포함" choice (off = /4, byte for byte as before).
 async function createBackup({userObjects=false}={}){const B=need('DeviceBackup'),catalog=await data.static(CATALOG);return deepFreeze(await B.read(view,catalog,{userObjects:userObjects===true}));}
 const backup=Object.freeze({
  create:createBackup,
  download(event,{userObjects=false}={}){return action.run(event,'WRITE',async()=>{const B=need('DeviceBackup'),payload=await createBackup({userObjects});B.download(view,payload);return Object.freeze({schema:payload.schema});});},
  // Merges into this device as DeviceBackup.restore does (all keys or none: it rolls back a failed write); /5 user objects are
  // merged in, nothing on this device removed.
  restore(event,text){return write(event,'BACKUP',async()=>{const B=need('DeviceBackup'),payload=parseBackup(text),catalog=await data.static(CATALOG);await B.restore(view,catalog,payload);return Object.freeze({schema:payload.schema});});},
  restored(){const B=need('DeviceBackup');return B.restoredNotice(storage);}});

 // ---- device V history keys (DC-31): how many of the two stopped keys this device still holds (never a value), and their removal
 // on the user's click (a WRITE action; nothing else is removed).
 const vHistoryKeys=Object.freeze({count:()=>action.stoppedKeys.count(),clear(event){return write(event,'V_HISTORY',signal=>action.stoppedKeys.clear(signal));}});

 // ---- sheet ids and the Worker address: never returned, only whether one is set
 const sheetSource=Object.freeze({
  has(){const GS=need('GoogleSheetSetup');try{return !!GS.source(view);}catch(_){return false;}},
  // The unified sheet (PriceStore price tabs, Trades tab). '' or null removes it.
  set(event,value){return write(event,'SHEET_SOURCE',()=>{const GS=need('GoogleSheetSetup');let id;try{id=GS.source(view,value===null||value===undefined?'':String(value));}catch(_){throw Error('SHEET_SOURCE_INVALID');}return Object.freeze({set:!!id});});}});
 // The Universe tab source (PrivateSubsetView.mountSettings rule: an id or a sheet URL; its own key, not the unified sheet).
 const universeSource=Object.freeze({
  has(){const v=storage.getItem(KEYS.UNIVERSE_SOURCE);return typeof v==='string'&&ID.test(v);},
  set(event,value){return write(event,'UNIVERSE_SOURCE',()=>{const Q=need('GoogleSheetQuotes'),text=value===null||value===undefined?'':String(value);let id='';
   if(text){try{id=Q.extractSpreadsheetId(text);}catch(_){throw Error('UNIVERSE_SOURCE_INVALID');}storage.setItem(KEYS.UNIVERSE_SOURCE,id);}else storage.removeItem(KEYS.UNIVERSE_SOURCE);return Object.freeze({set:!!id});});},
  // "통합 시트와 같게" (owner 2026-10-24, Main pick: the Universe source keeps its own key; the user may copy the unified sheet into
  // it on a click). The id is copied inside the store and never returned.
  useSheet(event){return write(event,'UNIVERSE_SOURCE',()=>{const GS=need('GoogleSheetSetup');let id='';try{id=GS.source(view);}catch(_){id='';}if(!id)throw Error('SHEET_SOURCE_NOT_SET');storage.setItem(KEYS.UNIVERSE_SOURCE,id);return Object.freeze({set:true});});}});
 // The Worker address (PrivateHistory.mountSettings rule); price requests need it equal to the approved app-config origin.
 const approvedOrigin=()=>{const c=object(win.InvestmentAppConfig)?win.InvestmentAppConfig:{};return c.privateHistoryEnabled===true&&typeof c.privateHistoryWorkerOrigin==='string'?c.privateHistoryWorkerOrigin:null;};
 function storedOrigin(){const PH=need('PrivateHistory'),v=storage.getItem(KEYS.WORKER_ORIGIN);if(!v)return'';try{return PH.parseWorkerOrigin(v);}catch(_){return'';}}
 const workerOrigin=Object.freeze({
  has:()=>!!storedOrigin(),approved:()=>{const o=storedOrigin();return !!o&&o===approvedOrigin();},
  set(event,value){return write(event,'WORKER_ORIGIN',()=>{const PH=need('PrivateHistory'),text=value===null||value===undefined?'':String(value);let o='';
   if(text){try{o=PH.parseWorkerOrigin(text);}catch(_){throw Error('REQUEST_INVALID');}storage.setItem(KEYS.WORKER_ORIGIN,o);}else storage.removeItem(KEYS.WORKER_ORIGIN);
   return Object.freeze({set:!!o,approved:!!o&&o===approvedOrigin()});});}});

 // ---- device quotes stored before the new frontend (owner 2026-10-24, DC-18): how many records remain (a number, never a value;
 // null = this browser cannot tell without opening, and nothing is opened or created) and their removal on the user's click
 // (the settings button "저장된 시세 삭제"; holdings and every other record stay).
 const marketQuotes=Object.freeze({
  count:()=>action.stoppedRecords.count(),
  clear(event){return write(event,'MARKET_QUOTES',signal=>action.stoppedRecords.clear(signal));}});

 function subscribe(fn,{signal}={}){if(typeof fn!=='function')throw Error('SUBSCRIBER_INVALID');if(signal&&signal.aborted)return()=>{};subs.add(fn);const off=()=>{subs.delete(fn);};if(signal)signal.addEventListener('abort',off,{once:true});return off;}
 const api={KEYS,storage,prefs,savePrefs,recent,pushRecent,clearRecent,weights,saveWeights,holdings,playbook,saveThesis,saveHold,saveRecord,stars,toggleStar,macroEstimates,promptFavorites,promptCopies,
  chartNotes,backup,vHistoryKeys,sheetSource,universeSource,workerOrigin,marketQuotes,subscribe};
 // DeviceProfiles' preset list, read when asked (the old module loads before this one; tests swap modules).
 Object.defineProperty(api,'PRODUCT_PRESETS',{enumerable:true,get:()=>need('DeviceProfiles').PRODUCT_PRESETS});
 return Object.freeze(api);
}
return Object.freeze({create,KEYS});
});
