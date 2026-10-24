/* P1 device prices (IS2.prices): Google Sheet / Worker prices, requested only on a user click and held in RAM only (never stored,
   logged or sent anywhere but the user's own Sheet and Worker). P1 implementation spec, Main decisions 2, 3, 4, 8, 10; design
   §1.1 (4), §3; critique #2, #4, #7b, #9.
   - ONE price view for every session and price call: GoogleSheetQuotes.sessionFor and PriceStore keep their state in WeakMaps
     keyed by the view, so a second view would be a second session and a second store. Its fetch sends a public name through
     data.strictFetch and a private destination only while a click of the kind that allows it is in flight (action.guard);
     its IndexedDB is read-only (a read never creates the device database, not even inside a click).
   - storeFacade is PriceStore as every other caller sees it: the price view forced into every call, closes answered only after
     a click read the user's price tabs in this sign-in (else {} / null: a read with fetch:false still loads the tabs from the
     Sheet, price-store.js ensureLoaded), never a Worker request. The old boot-time tab read is not used.
   - The Universe read (the source of device V prices) is the old click pipeline of PrivateSubsetView.mount without a screen,
     same calls in the same order (private-subset-view.js:67-75), including SecUniverseShares.loadInputs(view, {now: read time});
     only its unexported glue (US prices of the read, the kept state, the sign-out rule) is written again here.
   - Prices leave this module only through quote() and history(), for display inside [data-ram-price] elements (P2 rule). */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else{const I=root.IS2=root.IS2||{};I.prices=api.create({win:root,action:I.action,data:I.data});}})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
// Old device keys this module reads (the store writes them): the Universe tab source (private-subset-view.js:3, its own setting)
// and the Worker address (private-history.js:8). The device database name is device-actual.js:9.
const UNIVERSE_SOURCE_KEY='investment.web.v1.universe-source',WORKER_ORIGIN_KEY='investment.web.v1.private-history-origin',DEVICE_DB='investment-device-actual-v1';
const CATALOG='actual-catalog.json',HISTORY_RANGES=Object.freeze(['1mo','3mo','6mo','1y','2y','5y']);
// Codes a failed Universe read keeps; anything else is UNIVERSE_READ_FAILED (private-subset-view.js:81).
const READ_CODES=Object.freeze(['SOURCE_TOO_LARGE','AUTH_REQUIRED','CANCELED','UNIVERSE_SOURCE_INVALID']);
// PriceStore exports without a view or a request (constants and pure functions), passed through the facade unchanged.
const PURE=Object.freeze(['SCHEMA','CODES','TAB_DAILY','TAB_MONTHLY','TABS','HEAD','RANGES','FLAG_KEY','currencyFor','timezoneFor','universeSymbol','parseTab','indexRows','closesFromHistory',
 'sourceOf','monthEnds','monthsBack','dueDate','nextRange','monthDue','nextMonthRange','appendPlan','sheetRows','monthEndClosesOf','dailyClosesOf','runnerPayload','chunkRows']);
// Count and code fields of a sync result; per-symbol results lose the Worker answer kept for a failed write (it holds closes).
const SUMMARY=Object.freeze(['state','kind','symbols','fetched','appended_rows','current','write_failed','failed','not_allowed','universe','reason_codes','tab']);
const object=v=>v!==null&&typeof v==='object'&&!Array.isArray(v),str=v=>typeof v==='string'?v:null;
const key=t=>String(t||'').replaceAll('.','-').toUpperCase(),symbolOf=code=>key(String(code).slice(String(code).indexOf(':')+1));// qgv-scores.js:31
function deepFreeze(v){if(v&&typeof v==='object'&&!Object.isFrozen(v)){Object.freeze(v);for(const x of Object.values(v))deepFreeze(x);}return v;}
function create({win,action,data}){
 if(!action||typeof action.view!=='function'||!data||typeof data.strictFetch!=='function')throw Error('LAYER_MISSING');
 const need=n=>{const m=win[n];if(!m)throw Error('READER_MISSING');return m;};
 const config=()=>object(win.InvestmentAppConfig)?win.InvestmentAppConfig:{};
 const subs=new Set();let wired=false;
 const emit=()=>{for(const fn of[...subs]){try{fn();}catch(_){}}};

 // ---- the kept Universe read (RAM only): the last successful read of this page session, as PrivateSubsetView keeps it
 let kept=null,failure=null,ranks=null,ranksRevision=null,readSeq=0,readCtl=null;
 // private-subset-view.js:36: US exchange codes with a positive sheet price, first row of a code wins, USD.
 function usPrices(parsed){const out=new Map();for(const r of parsed.rows)if(typeof r.code==='string'&&/^(?:NYSE|NASDAQ|BATS):/.test(r.code)&&typeof r.sheet_price==='number'&&Number.isFinite(r.sheet_price)&&r.sheet_price>0&&!out.has(r.code))out.set(r.code,Object.freeze({price:r.sheet_price,currency:'USD'}));return out;}
 // :39: acquired_at is when the tab was read, not a price time; the GOOGLEFINANCE column has none (price_time null = 미확인).
 function keep(parsed){const rc=parsed.receipt;kept=Object.freeze({prices:usPrices(parsed),basis:Object.freeze({source:'GOOGLEFINANCE_PRIVATE_UNIVERSE',read_id:rc&&typeof rc.job_id==='string'?rc.job_id:null,
  acquired_at:rc&&typeof rc.acquired_at==='string'?rc.acquired_at:null,currency:'USD',price_time:null})});failure=null;}
 function failed(code){failure=Object.freeze({code,at:new Date().toISOString()});emit();}
 const prices=()=>kept?new Map(kept.prices):null,priceBasis=()=>kept?kept.basis:null;
 const readStatus=()=>Object.freeze({state:kept?'READY':'NOT_READ',basis:kept?kept.basis:null,failure});
 // PrivateSubsetView's contract, for QgvScores (collectQuotes / pageResult / readMarks) through the price and score views.
 const universeView=Object.freeze({prices,priceBasis,readStatus,ranks:()=>ranks});

 // ---- the price tabs (PriceStore), always with the price view
 let tabsKey=null;const histories=new Map();
 const opts=o=>({...(object(o)?o:{}),view:priceView,fetch:false});
 // The store's own key (price-store.js ensureLoaded): this sheet in this sign-in. A different key would make PriceStore reload.
 function keyNow(){let id='',rev=null;try{id=need('GoogleSheetSetup').source(priceView);}catch(_){id='';}try{rev=session().revision();}catch(_){rev=null;}return id+'#'+rev;}
 // A click read the tabs this interval needs, for this sheet and sign-in (DataRefresh.guardPrices' loaded() rule plus the key).
 function tabsReady(interval){const PS=win.PriceStore;if(!PS||tabsKey===null)return false;
  try{const s=PS.status(opts());if(!s||s.state!=='READY'||tabsKey!==keyNow())return false;const t=object(s.tabs)?s.tabs:{};
   return(interval==='1mo'?[PS.TAB_DAILY,PS.TAB_MONTHLY]:[PS.TAB_DAILY]).every(n=>!t[n]||!t[n].present||t[n].read===true);}catch(_){return false;}}
 const storeFacade=Object.freeze(Object.defineProperties({
  status(o){const PS=win.PriceStore;return PS?PS.status(opts(o)):null;},
  subscribe(fn,o){const PS=win.PriceStore;return PS?PS.subscribe(fn,opts(o)):()=>{};},
  coverage(symbol,o){const PS=win.PriceStore;return PS?PS.coverage(symbol,opts(o)):null;},
  monthEndCloses(symbol,o){const PS=win.PriceStore;return PS&&tabsReady('1mo')?PS.monthEndCloses(symbol,opts(o)):Promise.resolve({});},
  dailyCloses(symbol,from=null,o){const PS=win.PriceStore;return PS&&tabsReady('1d')?PS.dailyCloses(symbol,from,opts(o)):Promise.resolve({});},
  // The runner's stored-closes path (fetch:false); null = store not in use, the runner then reports its own state.
  runnerHistories(_view,o){const PS=win.PriceStore;return PS&&tabsReady('1d')?PS.runnerHistories(priceView,{...(object(o)?o:{}),fetch:false}):Promise.resolve(null);},
  universeProgress(_view,symbols,ms){const PS=win.PriceStore;return PS?PS.universeProgress(priceView,symbols,ms):null;}
 },Object.fromEntries(PURE.map(k=>[k,{enumerable:true,get:()=>{const PS=win.PriceStore;return PS?PS[k]:undefined;}}]))));

 // ---- the price view: public names through strictFetch, private destinations only inside the click kind that allows them
 async function privateFetch(input,init){if(action.guard(input,init)==='PUBLIC')return data.strictFetch(input,init);return win.fetch(input,init);}
 const priceView=action.view({fetch:privateFetch,PrivateSubsetView:universeView,PriceStore:storeFacade},{readOnlyStores:true});

 // ---- the one Google session
 let sess=null;
 function session(){const s=need('GoogleSheetQuotes').sessionFor(priceView,config().googleSheetsClientId);if(s!==sess){sess=s;s.subscribe(onSession);}return s;}
 /* private-subset-view.js:40 and :66: a sign-out (disconnect, or Google turned off) clears the kept read and the held histories; an
    expired sign-in (AUTH_REQUIRED) keeps the read. Ranks belong to one sign-in: cleared when it ends or changes. */
 function onSession(){const s=sess;let st=null,rev=null;try{st=s.state();rev=s.revision();}catch(_){st=null;}
  const out=!st||st.enabled===false||!st.connected&&!st.pending&&!st.error;
  if(out){if(kept||failure){kept=null;failure=null;}histories.clear();}
  if(ranks&&(!st||!st.connected||rev!==ranksRevision))ranks=null;
  emit();}

 // ---- status, subscriptions
 function storeStatus(){const PS=win.PriceStore;let s=null;try{s=PS?PS.status(opts()):null;}catch(_){s=null;}
  return s?{...JSON.parse(JSON.stringify(s)),tabs_loaded:{daily:tabsReady('1d'),monthly:tabsReady('1mo')}}:null;}
 function universeSource(){const v=priceView.localStorage.getItem(UNIVERSE_SOURCE_KEY);if(v===null)return'';if(!/^[A-Za-z0-9_-]{20,100}$/.test(v))throw Error('UNIVERSE_SOURCE_INVALID');return v;}// :5
 // Codes and counts only: no price, no sheet id, no Worker address.
 function status(){let google=null;try{const st=session().state();google={enabled:st.enabled===true,ready:st.ready===true,connected:st.connected===true,pending:st.pending===true,preparing:st.preparing===true,error:str(st.error)||null};}catch(_){google=null;}
  let sheet=false,source=false;try{sheet=!!need('GoogleSheetSetup').source(priceView);}catch(_){sheet=false;}try{source=!!universeSource();}catch(_){source=false;}
  const store=storeStatus();
  return deepFreeze({google,sheet:{set:sheet},universe_source:{set:source},store,universe:{state:kept?'READY':'NOT_READ',read_at:kept?kept.basis.acquired_at:null,failure:failure?{...failure}:null},
   worker:{state:store?store.fetch:null},history:{held:histories.size}});}
 function subscribe(fn,{signal}={}){if(typeof fn!=='function')throw Error('SUBSCRIBER_INVALID');if(signal&&signal.aborted)return()=>{};
  if(!wired){wired=true;try{session();}catch(_){}try{const PS=win.PriceStore;if(PS)PS.subscribe(emit,opts());}catch(_){}}
  subs.add(fn);const off=()=>{subs.delete(fn);};if(signal)signal.addEventListener('abort',off,{once:true});return off;}

 // ---- sign-in (decision 8): GIS script and token only inside a LOGIN click; the session refuses prepare until it is on.
 function prepare(event){return action.run(event,'LOGIN',()=>{const s=session();s.setEnabled(true);return s.prepare();});}
 // GIS needs requestAccessToken synchronously inside the click (google-sheet-quotes.js:185).
 function login(event){return action.run(event,'LOGIN',()=>{session().login();});}
 function logout(event){return action.run(event,'LOGIN',()=>session().disconnect());}
 /* This device's saved Google on/off (DeviceActual.sheetSettings), read only when the device database already exists. A saved
    'on' turns the session on (a flag, no request); a saved 'off' never turns off a session the user switched on by a click. */
 async function deviceSettings(){const s=session(),known=(await action.stores()).names.includes(DEVICE_DB);let st=null;
  if(known){try{st=await need('DeviceActual').sheetSettings(priceView);}catch(_){st=null;}}
  if(st&&st.enabled===true&&s.state().enabled!==true)s.setEnabled(true);
  return Object.freeze({stored:!!st,enabled:s.state().enabled===true});}

 // ---- the Universe read (UNIVERSE_READ click): private-subset-view.js:67-75 without the screen
 function readUniverse(event){return action.run(event,'UNIVERSE_READ',signal=>readNow(signal));}
 async function readNow(signal){
  const core=need('PrivateSubset'),PSV=need('PrivateSubsetView'),s=session();let id;
  try{id=universeSource();}catch(_){throw Error('UNIVERSE_SOURCE_INVALID');}
  if(!id)throw Error('UNIVERSE_SOURCE_NOT_SET');if(!s.state().connected)throw Error('AUTH_REQUIRED');
  if(readCtl)readCtl.abort();const my=++readSeq,ctl=new win.AbortController();readCtl=ctl;
  const stop=()=>ctl.abort();if(signal){if(signal.aborted)ctl.abort();else signal.addEventListener('abort',stop,{once:true});}
  const sessionRevision=s.revision(),current=()=>readSeq===my&&!ctl.signal.aborted&&s.revision()===sessionRevision&&s.state().connected;let done=false;
  try{
   const payload=await s.fetchValues(id,PSV.RANGE,{signal:ctl.signal,maxBytes:1048576});if(!current())throw Error('CANCELED');
   const acquired=new Date().toISOString(),receipt={source:'GOOGLEFINANCE_PRIVATE_UNIVERSE',acquired_at:acquired,content_sha256:await core.digest(core.canonicalValues(payload.values)),job_id:'job_'+win.crypto.randomUUID(),session_epoch:sessionRevision,synthetic:false};
   // The public share counts re-judged at the read time (row state LIVE/STALE at this moment: private-subset.js:69 STALE_INPUT).
   const SUS=win.SecUniverseShares;let inputs=null,inputError=null;
   try{inputs=SUS?await SUS.loadInputs(priceView,{signal:ctl.signal,now:acquired}):null;}catch(e){const m=e&&e.message;inputError=m==='SEC_UNIVERSE_SHARES_INVALID'||m==='SEC_UNIVERSE_SHARES_SCHEMA_NEWER'?m:'SEC_INPUTS_UNAVAILABLE';}
   if(!current())throw Error('CANCELED');
   const parsed=await core.parseUniverseValues(payload.values,receipt,inputs&&inputs.identityLookup||{});if(!current())throw Error('CANCELED');
   const checks=[];
   if(inputs)for(const row of parsed.rows){if(!row.listing)continue;const record=inputs.publicShares&&inputs.publicShares[row.code];
    if(record){const pub=core.preparePublicShares(row.listing,record,acquired);checks.push(core.compareUniverseMarketCap(row,pub.shares,core.prepareUniversePrice(row,pub.basis,acquired)));continue;}
    const src=inputs.secByListing&&inputs.secByListing[row.listing.listing_id],basis=inputs.basisByListing&&inputs.basisByListing[row.listing.listing_id];if(!src||!basis)continue;
    const shares=await core.prepareSecShares(row.listing,src,basis,acquired),price=core.prepareUniversePrice(row,basis,acquired);checks.push(core.compareUniverseMarketCap(row,shares,price));if(!current())throw Error('CANCELED');}
   const G=win.ShareClassGroups,groups=inputs&&inputs.publicShares&&G?core.prepareShareClassGroups(parsed,inputs.publicShares,acquired,G.CONFIG,undefined,inputs.unlistedClasses||{}):[];
   const selection=core.selectVerifiedUniverseTopN(checks,parsed,{groups});let full=null;try{full=inputs?core.selectVerifiedUniverseTopN(checks,parsed,{groups,n:parsed.row_count}):null;}catch(_){full=null;}
   ranks=PSV.rankIndex(full,parsed,{config_status:inputs&&inputs.config_status||null,reason:inputs?null:(inputError||'SEC_INPUTS_NOT_CONNECTED')});ranksRevision=sessionRevision;
   keep(parsed);done=true;emit();
   // Codes and counts only (the selection itself carries market caps, a price-derived value).
   return deepFreeze({state:'READY',read_id:kept.basis.read_id,read_at:kept.basis.acquired_at,inputs:inputs?'READY':inputError||'SEC_INPUTS_NOT_CONNECTED',config_status:inputs&&inputs.config_status||null,
    selection:{state:selection.state,status:selection.status,selected_n:Number.isInteger(selection.selected_n)?selection.selected_n:null,verified_count:Number.isInteger(selection.verified_count)?selection.verified_count:null,missing_count:Number.isInteger(selection.missing_count)?selection.missing_count:null},
    ranks:{state:ranks.state,status:str(ranks.status),verified_count:Number.isInteger(ranks.verified_count)?ranks.verified_count:null,row_count:Number.isInteger(ranks.row_count)?ranks.row_count:null,reason_codes:[...ranks.reason_codes]}});
  }catch(e){// A read overtaken by a newer read, a cancel or a sign-in change records nothing (the old handler's current() rule).
   if(!current())throw Error(e&&e.message==='AUTH_REQUIRED'?'AUTH_REQUIRED':'CANCELED');const code=READ_CODES.includes(e&&e.message)?e.message:'UNIVERSE_READ_FAILED';if(!done)failed(code);throw Error(code);}
  finally{if(readCtl===ctl)readCtl=null;if(signal)signal.removeEventListener('abort',stop);}
 }
 // Personal M3 rank of one company (2.1.1, PrivateSubsetView.rankFor over the kept read's index; ranks only, never a cap).
 function rankFor(target){return need('PrivateSubsetView').rankFor(ranks,target);}

 // ---- price tab clicks (SYNC): every Sheet / Worker step is the old PriceStore's, with the price view
 function tabsOp(event,run){return action.run(event,'SYNC',async signal=>{const PS=need('PriceStore'),before=keyNow();const out=await run(PS,signal);
  let s=null;try{s=PS.status(opts());}catch(_){s=null;}if(s&&s.state==='READY'&&keyNow()===before)tabsKey=before;emit();return out===undefined?counts():out;});}
 // Store state after the click (codes and counts; tabs_loaded says whether the facade now answers).
 const counts=()=>deepFreeze(storeStatus());
 function summary(r){if(!object(r))return null;const out={};for(const k of SUMMARY)if(Object.hasOwn(r,k)&&r[k]!==undefined)out[k]=JSON.parse(JSON.stringify(r[k]));
  if(object(r.results))out.results=Object.fromEntries(Object.entries(r.results).map(([sym,x])=>[sym,{code:object(x)?str(x.code):null,fetched:object(x)&&x.fetched===true,appended:object(x)&&Number.isInteger(x.appended)?x.appended:null,write:object(x)?str(x.write):null}]));
  return deepFreeze(out);}
 // "Use price tabs": creates Prices_D / Prices_M with their header when missing and turns the store on for this device.
 const useTabs=event=>tabsOp(event,async PS=>{await PS.enable(priceView);});
 // Reads the stored rows of both tabs into RAM (the closes stay inside PriceStore; screens read them through the facade).
 const loadTabs=event=>tabsOp(event,async PS=>{await PS.monthEndCloses('SPY',{view:priceView});});
 function syncSymbols(event,symbols,interval='1d',{kind='CORE'}={}){if(!Array.isArray(symbols))throw Error('SYMBOLS_INVALID');if(interval!=='1d'&&interval!=='1mo')throw Error('INTERVAL_INVALID');
  return tabsOp(event,async(PS,signal)=>summary(await PS.syncMany(priceView,[...symbols],interval,{kind:String(kind),signal,allowlistOnly:true})));}
 const syncUniverse=event=>tabsOp(event,async(PS,signal)=>summary(await PS.syncUniverse(priceView,{signal})));

 // ---- Worker daily history of one TARGET (HISTORY click), RAM only (private-history.js load, without the chart)
 function targetSymbol(x){if(typeof x!=='string')return null;const PH=win.PrivateHistory,R=win.VirtualTradingRunner,s=PH?PH.symbolFor(x):null;if(s)return s;return R&&object(R.TARGETS)&&Object.values(R.TARGETS).includes(x)?x:null;}
 function history(event,company,{range='1y'}={}){return action.run(event,'HISTORY',async signal=>{
  const PH=need('PrivateHistory'),c=config(),symbol=targetSymbol(company);
  if(c.privateHistoryEnabled!==true)throw Error('OFF');if(!symbol)throw Error('HISTORY_UNAVAILABLE');if(!HISTORY_RANGES.includes(range))throw Error('REQUEST_INVALID');
  let origin='';try{const v=priceView.localStorage.getItem(WORKER_ORIGIN_KEY);origin=v?PH.parseWorkerOrigin(v):'';}catch(_){throw Error('REQUEST_INVALID');}
  if(!origin||origin!==c.privateHistoryWorkerOrigin)throw Error('ORIGIN_UNAPPROVED');
  const s=session();if(!s.state().connected)throw Error('AUTH_REQUIRED');const rev=s.revision();
  const payload=await s.fetchHistory(origin,symbol,range,{approvedOrigin:c.privateHistoryWorkerOrigin,signal});
  if(s.revision()!==rev||!s.state().connected)throw Error('CANCELED');
  const out=deepFreeze(PH.validateHistory(payload,{symbol,range}));histories.set(symbol+'|'+range,out);emit();return out;});}
 const held=(company,{range='1y'}={})=>{const s=targetSymbol(company);return s&&histories.get(s+'|'+range)||null;};

 // ---- one device price for display ([data-ram-price] only): QgvScores.collectQuotes' order for one company
 async function quote(company){const c=object(company)?company:{},code=str(c.code),ticker=str(c.ticker);
  const ram=(q,extra)=>Object.freeze({state:'OK',price:q.price,currency:q.currency,...extra});
  if(kept){const b=kept.basis,u={source:'UNIVERSE_SHEET',read_at:b.acquired_at,as_of:null,time_status:'UNCONFIRMED',freshness:'UNDETERMINED'};
   if(code&&kept.prices.has(code))return ram(kept.prices.get(code),u);
   if(ticker)for(const[k,q]of kept.prices)if(symbolOf(k)===key(ticker))return ram(q,u);}
  // A stored device quote, only from a device database that already exists (a read never creates one).
  const DV=win.DeviceValuation;
  if(ticker&&DV&&typeof DV.deviceQuote==='function'&&(await action.stores()).names.includes(DEVICE_DB)){const catalog=await data.static(CATALOG);let q=null;try{q=catalog?await DV.deviceQuote(priceView,catalog,ticker):null;}catch(_){q=null;}
   if(q)return ram(q,{source:str(q.source)||'DEVICE_QUOTE',read_at:str(q.read_at),as_of:str(q.as_of),time_status:str(q.price_time_status)||'UNCONFIRMED',freshness:str(q.freshness)||'UNDETERMINED'});}
  return Object.freeze({state:'NA',reason:'NO_DEVICE_PRICE'});}

 return Object.freeze({UNIVERSE_SOURCE_KEY,WORKER_ORIGIN_KEY,status,subscribe,deviceSettings,prepare,login,logout,readUniverse,universeView,universeRanks:()=>ranks,rankFor,
  useTabs,loadTabs,syncSymbols,syncUniverse,history,held,quote,priceView,storeFacade});
}
return Object.freeze({create});
});
