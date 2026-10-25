/* Loader (P2-1a, owner 2026-10-24 "휴대폰 첫 화면 비용"; P1_DATA_LAYER.md §1.1): index.html loads only the first screen (core,
   shell, parts, this file, the screen files, boot.js). boot.js draws the shell and calls IS2.load(); after the shell's first
   paint (IS2.firstPaint from shell.js: the first render's frame painted) and an idle moment, the reused old modules and the P1
   layer load from LOAD_ORDER below.
   - LOAD_ORDER is the one load list. tools/build_web_app.py (plan A: a listed name with no file in web_app is an old
     web_assets file, kept byte-identical; a name found in neither folder fails the build) and tools/web_app_reuse.js read it
     from this file, so it stays a literal of plain quoted names.
   - Each file is a same-origin <script src> with a plain file name (NAME below; the build and tools/web_app_reuse.js refuse
     the same names and a name listed twice, so a build that passes never meets LOADER_NAME_INVALID here), async=false so all
     of them download in parallel and run in list order. No inline code, no eval; the CSP is unchanged ('self').
   - IS2.ready resolves when every file ran and the layer installed itself (IS2.action and the five namespaces). It rejects with
     Error('LOADER_FAILED <file>') for the first file in list order that did not arrive, threw while it ran, or did not install
     its namespace; it never retries (a reload does).
   - Until then IS2.data / qgv / prices / store / engines are facades with the layer's own members (API below):
       'p'   returns a promise: waits for IS2.ready, then calls the layer;
       'a'   an action (its first argument is the user's event): throws LAYER_NOT_READY, because the gate needs the event still
             being dispatched and a click cannot wait (screens keep action buttons off until IS2.ready);
       's'/'v' a synchronous getter or a value: gives IS2.NOT_READY ({state:'NOT_READY', reason:'LAYER_NOT_READY'});
       'sub' subscribe(fn, {signal}): kept and attached to the layer when ready (dropped if the signal aborts first).
     The layer files replace the facades on IS2 when they run; a facade a screen kept forwards every call to the layer once
     ready. After a failure the facades are put back and refuse: 'p' rejects and 'a' throws the LOADER_FAILED error, 's'/'v'
     give IS2.LOAD_FAILED ({state:'NOT_READY', reason:'LOADER_FAILED'}), 'sub' keeps nothing.
   Nothing here stores, reads or sends anything but the listed scripts. Marks: is2-ready / is2-load-failed. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else api.install(root);})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
// The old modules in the old page's relative order (backup /5 validators chart-workbench.js and macro-cycle-ring.js included),
// then the P1 layer action → data → prices → store → qgv → engines.
const LOAD_ORDER=Object.freeze([
 'locale.js','entity-search.js','price-time.js','device-market.js','device-actual.js','profile-defaults.js','type-config-defaults.js',
 'device-profiles.js','engine-preview.js','dcf-parameters-defaults.js','device-valuation.js','playbook-config-defaults.js','playbook-engine.js',
 'qgv-v2.js','scoring-default.js','qgv2-inputs.js','qgv-scores.js','private-subset.js','share-class-groups.js','sec-universe-shares.js',
 'sec-qgv2.js','private-subset-view.js','target-v1-config-defaults.js','target-v1-builder.js','playbook-screen.js','target-v1-screen.js',
 'device-backup.js','watchlist.js','app-config.js','google-sheet-core.js','google-sheet-quotes.js','technical-chart.js','chart-workbench.js',
 'google-sheet-setup.js','private-trades.js','holdings-capture.js','worker-quote-fallback.js','forward-validation.js','private-history.js',
 'sec-reported.js','manager-styles-v0.js','thirteenf-quarter.js','macro-lights.js','macro-cycle-ring.js','macro-evidence.js','public-screens.js',
 'sec-disclosures.js','news-signals.js','classification-screens.js','dart-disclosures.js','virtual-trading.js','virtual-trading-runner.js',
 'virtual-trading-signals.js','virtual-trading-v-history.js','virtual-ledger-sheets.js','price-store.js','report-benchmarks.js',
 'virtual-trading-compare.js','home-quotes.js','data-refresh.js',
 'action.js','data.js','prices.js','store.js','qgv.js','engines.js',
]);
// A plain lowercase script name. tools/build_web_app.py holds this exact line (the build fails when the two differ).
const NAME=/^[a-z0-9][a-z0-9-]*(?:\.[a-z0-9-]+)*\.js$/;
// The namespace each layer file installs on IS2 (action.js installs IS2.action, which has no facade: screens do not call it).
const NAMESPACES=Object.freeze({data:'data.js',prices:'prices.js',store:'store.js',qgv:'qgv.js',engines:'engines.js'});
// The layer's members a screen may use (the node test checks this against the real layer: async or promise → 'p', first
// parameter `event` → 'a', subscribe → 'sub', the rest 's', non-functions 'v'). The views and results the layer hands only to
// old modules and engines.js (source rules) have no facade member.
const API=Object.freeze({
 data:{FILES:'v',CORE:'v',LIST_FILES:'v',STATIC:'v',READERS:'v',MAX_BYTES:'v',EVENT:'v',strictFetch:'p',ready:'p',get:'s',screens:'s',state:'s',
  publication:'s',list:'p',shares:'p',financials:'p',refresh:'a',static:'p',peek:'p',subscribe:'sub',universe:'p'},
 prices:{UNIVERSE_SOURCE_KEY:'v',WORKER_ORIGIN_KEY:'v',status:'s',subscribe:'sub',deviceSettings:'p',prepare:'a',login:'a',logout:'a',readUniverse:'a',
  universeView:{prices:'s',priceBasis:'s',readStatus:'s',ranks:'s'},universeRanks:'s',rankFor:'s',useTabs:'a',loadTabs:'a',syncSymbols:'a',
  syncUniverse:'a',history:'a',held:'s',quote:'p'},
 store:{KEYS:'v',prefs:'s',savePrefs:'a',recent:'s',pushRecent:'a',clearRecent:'a',weights:'s',saveWeights:'a',holdings:'p',playbook:'s',saveThesis:'a',saveHold:'a',saveRecord:'a',
  stars:'s',toggleStar:'a',backup:{create:'p',download:'a',restore:'a',restored:'s'},vHistory:'s',sheetSource:{has:'s',set:'a'},
  universeSource:{has:'s',set:'a',useSheet:'a'},workerOrigin:{has:'s',approved:'s',set:'a'},marketQuotes:{count:'p',clear:'a'},subscribe:'sub',PRODUCT_PRESETS:'v'},
 qgv:{V_SOURCES:'v',RANK_LABELS:'v',READERS:'v',vSource:'s',page:'p',isPage:'s',row:'s',rows:'s',coverage:'s',preview:'s',setProfile:'s',profile:'s',
  reasonText:'s',rankLabel:'s',constants:'s',subscribe:'sub'},
 engines:{target:{state:'s',basis:'p',draft:'p',build:'a',blockers:'p',finalize:'a',answer:'a',ruleBDue:'s',selectRuleB:'a',compare:'a',scoringPending:'p',
  refreshScoring:'p',syncScoringPrices:'a'},playbook:{facts:'p',judge:'p',record:'a',due:'s',limits:'s'},
  virtual:{stored:'p',compare:'s',forward:'p',rehearse:'p',run:'s'},macro:{current:'p'}}});
const NOT_READY=Object.freeze({state:'NOT_READY',reason:'LAYER_NOT_READY'}),LOAD_FAILED=Object.freeze({state:'NOT_READY',reason:'LOADER_FAILED'});
const MARK_READY='is2-ready',MARK_FAILED='is2-load-failed',PAINT_WAIT_MS=3000,IDLE_WAIT_MS=200;

function create(win,{list=LOAD_ORDER}={}){
 if(!Array.isArray(list)||!list.every(n=>typeof n==='string'&&NAME.test(n))||new Set(list).size!==list.length)throw Error('LOADER_NAME_INVALID');
 const order=Object.freeze([...list]);
 let phase='WAITING',error=null,real=null,settle=null,started=false;
 const ready=new Promise((resolve,reject)=>{settle={resolve,reject};});
 ready.catch(()=>{});// the failure is reported through IS2.ready and the facades; it is not an unhandled rejection
 const parentOf=path=>{let o=real[path[0]];for(let i=1;i<path.length-1;i++)o=o[path[i]];return o;};
 const forward=(path,args)=>{const o=parentOf(path);return o[path[path.length-1]](...args);};
 function later(path,[fn,opts]){
  if(typeof fn!=='function')throw Error('SUBSCRIBER_INVALID');
  const signal=opts&&opts.signal;if(phase==='FAILED'||(signal&&signal.aborted))return()=>{};
  let off=null,dead=false;const stop=()=>{dead=true;if(typeof off==='function')off();};
  ready.then(()=>{if(!dead&&!(signal&&signal.aborted))off=forward(path,[fn,opts]);},()=>{});
  if(signal)signal.addEventListener('abort',stop,{once:true});
  return stop;}
 function facade(spec,path){
  const o={};
  for(const[k,kind]of Object.entries(spec)){
   const p=[...path,k];
   if(kind&&typeof kind==='object'){o[k]=facade(kind,p);continue;}
   if(kind==='v'){Object.defineProperty(o,k,{enumerable:true,get:()=>phase==='READY'?parentOf(p)[k]:phase==='FAILED'?LOAD_FAILED:NOT_READY});continue;}
   o[k]=function(...args){
    if(phase==='READY')return forward(p,args);
    const failed=phase==='FAILED';
    if(kind==='p')return failed?Promise.reject(error):ready.then(()=>forward(p,args));
    if(kind==='a')throw failed?error:Error('LAYER_NOT_READY');
    if(kind==='sub')return later(p,args);
    return failed?LOAD_FAILED:NOT_READY;};
  }
  return Object.freeze(o);}
 const facades=Object.freeze(Object.fromEntries(Object.keys(NAMESPACES).map(ns=>[ns,facade(API[ns],[ns])])));
 const mark=name=>{try{win.performance.mark(name);}catch(_){}};
 const frames=()=>new Promise(r=>win.requestAnimationFrame(()=>win.requestAnimationFrame(()=>r())));
 const delay=ms=>new Promise(r=>win.setTimeout(r,ms));
 const idle=()=>new Promise(r=>{if(typeof win.requestIdleCallback==='function')win.requestIdleCallback(()=>r(),{timeout:IDLE_WAIT_MS});else win.setTimeout(r,0);});

 // Inserts every listed file at once (async=false: parallel downloads, list order) and settles IS2.ready when all of them ran.
 function insert(){
  phase='LOADING';
  const doc=win.document,origin=win.location.origin,I=win.IS2;let first=null;
  const fail=name=>{const i=order.indexOf(name);if(first===null||(i>=0&&i<order.indexOf(first)))first=name;};
  const fileOf=url=>{try{const u=new URL(String(url));return u.origin===origin?u.pathname.split('/').pop():null;}catch(_){return null;}};
  // A listed file that throws while it runs still fires 'load'; the window's error event names it.
  const thrown=e=>{const n=fileOf(e&&e.filename);if(n&&order.includes(n))fail(n);};
  win.addEventListener('error',thrown);
  const runs=order.map(name=>new Promise(done=>{
   const s=doc.createElement('script');s.async=false;s.src=name;
   if(fileOf(s.src)!==name){fail(name);done();return;}
   s.addEventListener('load',()=>done(),{once:true});s.addEventListener('error',()=>{fail(name);done();},{once:true});
   doc.body.appendChild(s);}));
  Promise.all(runs).then(()=>{
   win.removeEventListener('error',thrown);
   if(order.includes('action.js')&&!(I.action&&typeof I.action.run==='function'))fail('action.js');
   for(const[ns,file]of Object.entries(NAMESPACES))if(order.includes(file)&&(!I[ns]||typeof I[ns]!=='object'||I[ns]===facades[ns]))fail(file);
   if(first===null){real=Object.freeze(Object.fromEntries(Object.keys(NAMESPACES).map(ns=>[ns,I[ns]])));phase='READY';mark(MARK_READY);settle.resolve();return;}
   error=Object.assign(Error('LOADER_FAILED '+first),{code:'LOADER_FAILED',file:first});phase='FAILED';
   for(const[ns,f]of Object.entries(facades))I[ns]=f;
   mark(MARK_FAILED);settle.reject(error);});
 }
 // After the shell's first paint (or at once in a hidden page, which paints nothing), then an idle moment.
 function load(){
  if(started)return ready;started=true;
  const painted=win.IS2&&win.IS2.firstPaint&&typeof win.IS2.firstPaint.then==='function'?win.IS2.firstPaint:frames();
  const hidden=win.document&&win.document.visibilityState==='hidden';
  (hidden?Promise.resolve():Promise.race([painted,delay(PAINT_WAIT_MS)])).then(idle).then(insert);
  return ready;}
 function install(){
  const I=win.IS2=win.IS2||{};
  for(const[ns,f]of Object.entries(facades))if(I[ns]===undefined)I[ns]=f;
  Object.assign(I,{ready,load,loadState:()=>phase,NOT_READY,LOAD_FAILED,LOAD_ORDER:order});
  return I;}
 return Object.freeze({ready,load,install,facades,state:()=>phase,list:order});
}
return Object.freeze({LOAD_ORDER,NAME,NAMESPACES,API,NOT_READY,LOAD_FAILED,MARK_READY,MARK_FAILED,create,install:root=>create(root).install()});
});
