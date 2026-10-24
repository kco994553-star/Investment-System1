/* P1 public data (IS2.data): strict same-origin reader of the published files through the old DataRefresh core and readers,
   one generation at a time. Opening a page reads nothing private (P1 implementation spec, Main decisions 2 and 13; design §1.1 (2), §4).
   - Every public request of every view goes through strictFetch: a fixed file list (FILES), same origin, credentials omitted,
     redirects refused, no referrer, at most 2 MiB (= Pages guard MAX_FILE_BYTES); the HTTP status is kept, so DataRefresh still
     tells a failed read from an unpublished file (404). Readers that set none of these options (SecQgv2, SecUniverseShares,
     EntitySearch) get them here without being edited.
   - Validation is the old readers' own (DataRefresh.load / refresh / rejudge / list / shares / financials, SecQgv2.validate,
     GoogleSheetSetup.codes, EntitySearch.loadNames, DeviceValuation.load, ForwardValidation.load); nothing is re-checked here.
   - All or nothing, generations, 404 = NOT_PUBLISHED on first read, late answers of a replaced generation dropped, stale states
     re-judged without network: DataRefresh's rules, unchanged. Its bar, view-state code and listeners (attach) are not used.
   - DataRefresh exports no getter for the set it commits (only attach hooks receive it), so the core readers are handed to it
     through the public view and their validated results are kept per read; a refresh commits them on DataRefresh's own
     'public-data-updated' event, a re-judgement replaces the sec-qgv2.json rows it restated (data-refresh.js judge).
   No storage, no private request, no price. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else{const I=root.IS2=root.IS2||{};I.data=api.create({win:root,action:I.action});}})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
const MAX_BYTES=2*1024*1024,EVENT='public-data-updated',TICK=60000;
const QGV2='sec-qgv2.json',REPORTED='sec-public-inputs.json',FIN='dart-financials.json',EVIDENCE='macro-evidence.json',SHARES='sec-universe-shares.json',CODES='universe-codes.json';
// DataRefresh's set: PublicScreens.FILES, classification, sec-qgv2, sec-public-inputs, dart-financials, macro-evidence; its lists; shares.
const CORE=Object.freeze(['macro-screen.json','sec-13f-changes.json','sec-filing-windows.json','sec-qg-factors.json','company-types-pricefree.json','company-classification.json',QGV2,REPORTED,FIN,EVIDENCE]);
const LIST_FILES=Object.freeze(['sec-disclosures.json','news-signals.json','dart-disclosures.json']);
// Read once per page, outside the generation (identity catalog, search names, the fixed 504-code Universe list, financial detail, ledger).
const STATIC=Object.freeze(['actual-catalog.json','entities.json','company-names-ko.json',CODES,'sec-valuation-inputs.json','forward-validation-ledger.json']);
const FILES=Object.freeze([...CORE,...LIST_FILES,SHARES,...STATIC]),FILE_SET=new Set(FILES),STATIC_SET=new Set(STATIC);
// Without these the public path would silently change (light sec-qgv2 check, macro file rejected, cyclical V basis lost): READER_MISSING.
const READERS=Object.freeze(['DataRefresh','SecQgv2','Qgv2Inputs','PublicScreens','MacroLights','PlaybookEngine','PlaybookConfigDefaults']);
// Core readers whose results DataRefresh commits, with the call its readCore makes (data-refresh.js:65).
const CORE_READERS=Object.freeze({SecReported:'load',PublicScreens:'load',ClassificationScreens:'load',Qgv2Inputs:'load',DartDisclosures:'loadFinancials',MacroEvidence:'read'});
const TEXT=Object.freeze({READER_MISSING:['읽기 실패 · 읽기 모듈 없음','Read failed · reader missing']});
const object=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
function deepFreeze(v){if(v&&typeof v==='object'&&!Object.isFrozen(v)){Object.freeze(v);for(const x of Object.values(v))deepFreeze(x);}return v;}
function create({win,action}){
 if(!action||typeof action.view!=='function')throw Error('ACTION_MISSING');
 const DR=()=>win.DataRefresh,missing=()=>READERS.filter(n=>!win[n]);
 const seen=new Map();// file -> last HTTP status of a strict read (0 = no answer), for the static files' state
 async function capped(r){
  const len=Number(r.headers.get('content-length'));if(Number.isFinite(len)&&len>MAX_BYTES)throw Error('PUBLIC_FILE_TOO_LARGE');
  if(r.body&&typeof r.body.getReader==='function'){const reader=r.body.getReader(),parts=[];let size=0;
   for(;;){const{done,value}=await reader.read();if(done)break;size+=value.byteLength;if(size>MAX_BYTES){try{await reader.cancel();}catch(_){}throw Error('PUBLIC_FILE_TOO_LARGE');}parts.push(value);}
   const out=new Uint8Array(size);let at=0;for(const p of parts){out.set(p,at);at+=p.byteLength;}return out;}
  const out=new Uint8Array(await r.arrayBuffer());if(out.byteLength>MAX_BYTES)throw Error('PUBLIC_FILE_TOO_LARGE');return out;
 }
 // The one public request function of every view (public, price and score views). Cache: the reader's no-cache, else no-store.
 async function strictFetch(input,init){
  const name=typeof input==='string'&&FILE_SET.has(input)?input:null;if(!name)throw Error('PUBLIC_FILE_UNKNOWN');
  const i=object(init)?init:{};if(i.method!==undefined&&String(i.method).toUpperCase()!=='GET'||i.body!==undefined&&i.body!==null)throw Error('PUBLIC_FILE_METHOD');
  const opts={method:'GET',cache:i.cache==='no-cache'?'no-cache':'no-store',credentials:'omit',redirect:'error',referrerPolicy:'no-referrer',mode:'same-origin',headers:{Accept:'application/json'}};
  if(i.signal)opts.signal=i.signal;
  let r;try{r=await win.fetch(name,opts);}catch(e){seen.set(name,0);throw e;}
  seen.set(name,r.status);const body=await capped(r),none=r.status===204||r.status===205||r.status===304;
  return new win.Response(none?null:body,{status:r.status,statusText:r.statusText,headers:{'Content-Type':r.headers.get('content-type')||'application/json'}});
 }
 // ---- the public view: core readers that keep their results for the read in progress ----
 let sink=null,judged=null;const apis=new Map();
 function reader(name){const R=win[name],m=CORE_READERS[name];if(!object(R)||typeof R[m]!=='function')return R;let w=apis.get(name);
  // sink: the load or refresh whose readers are starting (set only while DataRefresh starts them, synchronously). A sec-qgv2 read
  // outside both is DataRefresh's re-judgement of the committed text (judge, or rejudge inside an unchanged refresh).
  if(!w||w.of!==R){w={of:R,api:Object.freeze({...R,[m]:(...a)=>{const s=sink;return Promise.resolve(R[m](...a)).then(x=>{if(s)s[name]=x;else if(name==='Qgv2Inputs')judged={x};return x;});}})};apis.set(name,w);}
  return w.api;}
 const over={fetch:strictFetch};for(const name of Object.keys(CORE_READERS))Object.defineProperty(over,name,{enumerable:true,get:()=>reader(name)});
 const publicView=action.view(over);
 function started(s,call){sink=s;try{return call();}finally{sink=null;}}
 // readCore's assembly of one read (data-refresh.js:66): PublicScreens' files + classification + sec-qgv2 + DART financials.
 function assemble(s){const CS=win.ClassificationScreens,QI=win.Qgv2Inputs,out={...(object(s.PublicScreens)?s.PublicScreens:{})};
  if(CS&&s.ClassificationScreens)out[CS.FILE]=s.ClassificationScreens;if(QI&&s.Qgv2Inputs)out[QI.FILE]=s.Qgv2Inputs;if(s.DartDisclosures)out[FIN]=s.DartDisclosures;return out;}
 let cur=Object.freeze({generation:0,screens:Object.freeze({}),reported:null,evidence:null}),readyP=null,refreshing=null,pending=null,ticking=false;const subs=new Set();
 const notify=d=>{for(const fn of[...subs]){try{fn(d);}catch(_){}}};
 win.addEventListener(EVENT,e=>{const d=e&&e.detail;if(!object(d))return;
  if(d.reason==='REFRESH'&&pending){const s=pending;pending=null;cur=Object.freeze({generation:d.generation,screens:Object.freeze(assemble(s)),reported:s.SecReported||null,evidence:s.MacroEvidence||null});}
  else if(d.reason==='REJUDGE'){const j=judged;judged=null;if(j&&j.x&&d.generation===cur.generation&&Array.isArray(d.changed)&&d.changed.includes(QGV2))cur=Object.freeze({...cur,screens:Object.freeze({...cur.screens,[QGV2]:j.x})});}
  else return;
  notify(d);});
 // Freshness boundaries pass with time: DataRefresh re-judges from the text already read (no network) every minute while shown,
 // when the tab is shown again and after a screen change.
 function tick(reason){const D=DR();if(readyP&&D)void D.rejudge(reason).catch(()=>{});}
 function startTicks(){if(ticking)return;ticking=true;const visible=()=>{try{return win.document.visibilityState==='visible';}catch(_){return false;}};
  if(typeof win.setInterval==='function')win.setInterval(()=>{if(visible())tick('TIME');},TICK);
  try{win.document.addEventListener('visibilitychange',()=>{if(visible())tick('VISIBLE');});}catch(_){}
  win.addEventListener('hashchange',()=>tick('NAVIGATE'));}
 // The first call reads the core files (DataRefresh.load); later calls share it. Nothing is read when the page opens: screens call it.
 function ready(){
  if(!readyP){readyP=(async()=>{if(missing().length)throw Error('READER_MISSING');const s={},r=await started(s,()=>DR().load(publicView));
    cur=Object.freeze({generation:DR().publication().generation,screens:Object.freeze(object(r&&r.screens)?r.screens:{}),reported:r&&r.reported||null,evidence:s.MacroEvidence||null});
    startTicks();return DR().publication();})();
   readyP.catch(e=>{if(String(e&&e.message)!=='READER_MISSING')readyP=null;});}
  return readyP;}
 // The validated value of the current generation (sec-qgv2.json = Qgv2Inputs output); null when not read or not valid.
 function get(name){if(!FILE_SET.has(name))throw Error('PUBLIC_FILE_UNKNOWN');
  if(name===REPORTED)return cur.reported;if(name===EVIDENCE)return cur.evidence&&cur.evidence.payload?cur.evidence.payload:null;
  return Object.hasOwn(cur.screens,name)?cur.screens[name]:null;}
 const NOT_READ=Object.freeze({state:'NOT_READ',why:null,as_of:null,text:''});
 function textOf(name,f){if(Object.hasOwn(TEXT,f.why))return TEXT[f.why][0];const D=DR();return D?D.readText(name,f):'';}
 const statics=new Map();
 // {state:'OK'|'NOT_PUBLISHED'|'FAILED'|'NOT_READ', why, as_of, text}: a failed read and an unpublished file never share words.
 function state(name){if(!FILE_SET.has(name))throw Error('PUBLIC_FILE_UNKNOWN');
  if(STATIC_SET.has(name)){const e=statics.get(name);return e&&e.state?e.state:NOT_READ;}
  if(missing().length){const f={state:'FAILED',why:'READER_MISSING',http:null};return Object.freeze({state:f.state,why:f.why,as_of:null,text:textOf(name,f)});}
  const f=DR().status(name);return f?Object.freeze({state:f.state,why:f.why,as_of:f.as_of,text:textOf(name,f)}):NOT_READ;}
 function publication(){const D=DR();return D?D.publication():null;}
 async function list(key){await ready();return DR().list(publicView,key);}
 async function shares(){await ready();return DR().shares(publicView);}
 async function financials(){await ready();return DR().financials(publicView);}
 // The user-pressed re-read (all or nothing). Public files only: the PUBLIC_REFRESH kind never opens the private gate.
 function refresh(event){return action.run(event,'PUBLIC_REFRESH',()=>{
  if(!refreshing)refreshing=(async()=>{await ready();const s={},p=started(s,()=>DR().refresh());pending=s;try{return await p;}finally{if(pending===s)pending=null;}})().finally(()=>{refreshing=null;});
  return refreshing;});}
 function failure(name,err){const m=String(err&&err.message),http=seen.has(name)?seen.get(name):null;let f;
  if(m==='READER_MISSING')f={state:'FAILED',why:m,http:null};else if(http===404||m==='LEDGER_NOT_PUBLISHED')f={state:'NOT_PUBLISHED',why:null,http:404};
  else f={state:'FAILED',why:http===null||http===0?'NETWORK':http>=200&&http<300?'INVALID':'HTTP',http};
  return Object.freeze({state:f.state,why:f.why,as_of:null,text:textOf(name,f)});}
 async function readStatic(name){
  const need=n=>{if(!win[n])throw Error('READER_MISSING');return win[n];};
  if(name==='company-names-ko.json'){const x=await need('EntitySearch').loadNames(publicView);if(!x)throw Error('INVALID');return x;}
  if(name==='sec-valuation-inputs.json'){const x=await need('DeviceValuation').load(publicView);if(!x)throw Error('INVALID');return x;}
  if(name==='forward-validation-ledger.json'){const r=await need('ForwardValidation').load(publicView);if(r&&r.state==='LOADED')return r.ledger;throw Error(r&&r.reason?r.reason:'LEDGER_UNREACHABLE');}
  const r=await strictFetch(name,{cache:'no-store'});if(!r.ok)throw Error('HTTP');let v;try{v=JSON.parse(await r.text());}catch(_){throw Error('INVALID');}
  if(name===CODES){const GS=need('GoogleSheetSetup');try{return Object.freeze(GS.codes(v));}catch(_){throw Error('INVALID');}}
  // actual-catalog.json and entities.json: the old app checks only the answer and the JSON (app.js deviceCatalog, boot); their
  // users validate the content (DeviceWatchlist.identities, EntitySearch).
  if(!object(v))throw Error('INVALID');return deepFreeze(v);}
 // One read per page; resolves the value or null (state(name) says why).
 function staticFile(name){if(!STATIC_SET.has(name))throw Error('PUBLIC_FILE_UNKNOWN');let e=statics.get(name);
  if(!e){e={state:null};e.promise=readStatic(name).then(v=>{e.state=Object.freeze({state:'OK',why:null,as_of:object(v)&&typeof v.as_of==='string'?v.as_of:null,text:''});return v;},err=>{e.state=failure(name,err);return null;});statics.set(name,e);}
  return e.promise;}
 // TARGET's re-check before a version is saved: a stand-alone strict read that leaves the generation alone and returns the RAW
 // JSON that passed SecQgv2.validate (shard_count, row calc_version and reason codes are needed: target-v1-builder.js publishedCheck).
 async function peek(name){if(name!==QGV2)throw Error('PEEK_UNSUPPORTED');const SQ=win.SecQgv2;if(!SQ||typeof SQ.validate!=='function')throw Error('READER_MISSING');
  const r=await strictFetch(QGV2,{cache:'no-store'});if(r.status===404)return null;if(!r.ok)throw Error('SEC_QGV2_UNAVAILABLE');
  let p;try{p=JSON.parse(await r.text());}catch(_){throw Error('SEC_QGV2_INVALID');}
  SQ.validate(p);return deepFreeze(p);}
 function subscribe(fn,{signal}={}){if(typeof fn!=='function')throw Error('SUBSCRIBER_INVALID');if(signal&&signal.aborted)return()=>{};
  subs.add(fn);const off=()=>{subs.delete(fn);};if(signal)signal.addEventListener('abort',off,{once:true});return off;}
 // The fixed 504-code Universe list (universe-codes.json, GoogleSheetSetup.codes), or null.
 const universe=()=>staticFile(CODES);
 return Object.freeze({FILES,CORE,LIST_FILES,STATIC,READERS,MAX_BYTES,EVENT,strictFetch,ready,get,state,publication,list,shares,financials,refresh,static:staticFile,peek,subscribe,universe});
}
return Object.freeze({create,FILES,READERS,MAX_BYTES,EVENT});
});
