/* Price store v1: daily and month-end closes kept in the user's own Google Sheet (tabs Prices_D and Prices_M, drive.file
   session, append-only) so a close fetched once is not fetched again. Pure part mirrors qgv/price_store.py (vectors:
   tests/fixtures/price_store_v1.json): fixed header (a different header → SHEET_HEADER_MISMATCH, nothing is written),
   malformed rows skipped and counted, first stored row wins, dedupe by symbol + date (daily) or symbol + month (month-end),
   a provider revision of a stored close is ignored and counted (PRICE_REVISED_IGNORED), only the Worker's ranges (1mo … 5y).
   Device API (RAM only): PriceStore.monthEndCloses(symbol) → {'YYYY-MM': close}, PriceStore.dailyCloses(symbol, fromDate)
   → {date: close}, PriceStore.status(), PriceStore.coverage(symbol).
   CLICK-ONLY REQUESTS (owner decision 2026-10-23): opening a screen reads the stored rows only (the reads above never request
   unless the caller passes fetch:true from a button handler); the Worker is asked only from a user's button (settings core /
   Universe504 buttons, the company '받기' button, a screen's own fetch button). Closes live in this module's memory and the user's
   sheet only: nothing here logs them, puts them in localStorage/sessionStorage or sends them anywhere else; the device
   keeps one opt-in flag (no price). Missing → absent (NA), never 0. Example_* tabs are never read or written. */
(function(root,factory){const node=typeof module==='object'&&module.exports;const api=factory(node?()=>require('./virtual-trading-runner.js'):()=>root.VirtualTradingRunner,node?()=>require('./virtual-ledger-sheets.js'):()=>root.VirtualLedgerSheets);if(node)module.exports=api;else root.PriceStore=api;})(typeof globalThis==='object'?globalThis:this,function(runner,ledger){
'use strict';
const SCHEMA='price-store/1',TAB_DAILY='Prices_D',TAB_MONTHLY='Prices_M',TABS=Object.freeze({'1d':TAB_DAILY,'1mo':TAB_MONTHLY});
const HEAD=Object.freeze(['symbol','date','close','source','fetched_at']);
const RANGES=Object.freeze([['1mo',1],['3mo',3],['6mo',6],['1y',12],['2y',24],['5y',60]]),RUNNER_RANGE='2y',MAX_BARS=1500;
const SOURCES=Object.freeze({'Yahoo Finance(비공식)':'YAHOO','Tiingo EOD':'TIINGO','KRX OPEN API':'KRX'});
const SYMBOL=/^[A-Z0-9][A-Z0-9.=\-]{0,15}$/,NUMBER_TEXT=/^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:e[+-][0-9]+)?$/,DAY=/^\d{4}-\d{2}-\d{2}$/,CLOCK=/^\d{2}:\d{2}$/;
// Regular-session close (local time) after which today's daily bar can be final. FX pairs: never the same day.
const CLOSE_TIMES=Object.freeze([['.KS','15:30'],['.T','15:30'],['=X',null]]),US_CLOSE='16:00';
const UNIVERSE_CODE=/^(?:NYSE|NASDAQ|BATS):([A-Z][A-Z0-9.]{0,15})$/;
// Every state/reason code this module shows (codes only, never a value).
const CODES=Object.freeze(['OFF','AUTH_REQUIRED','SHEET_NOT_CONNECTED','LOADING','READY','ERROR','UP_TO_DATE','SHEET_HEADER_MISMATCH','SHEET_ROWS_INVALID','PRICE_REVISED_IGNORED',
 'PRICE_ROW_INVALID','PRICE_ROW_DUPLICATE','WORKER_ALLOWLIST','ORIGIN_UNAPPROVED','REQUEST_INVALID','RATE_LIMITED','HISTORY_UNAVAILABLE','HISTORY_FORMAT_INVALID','CURRENCY_MISMATCH',
 'WRITE_FAILED','READ_FAILED','SOURCE_TOO_LARGE','CANCELED','INVALID','UNIVERSE_CODES_NOT_AVAILABLE','NOT_ENABLED']);
const own=(o,k)=>o!==null&&typeof o==='object'&&Object.prototype.hasOwnProperty.call(o,k);
const object=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
function fail(code){throw new Error(code);}
function sortedObject(o){const r={};for(const k of Object.keys(o).sort())r[k]=o[k];return r;}
function isDay(v){if(!(typeof v==='string'&&DAY.test(v)&&v>='1900-01-01'))return false;const t=Date.parse(v+'T00:00:00Z');return Number.isFinite(t)&&new Date(t).toISOString().slice(0,10)===v;}
const okSymbol=v=>typeof v==='string'&&SYMBOL.test(v);
function currencyFor(symbol){return symbol.endsWith('.KS')||symbol.endsWith('=X')?'KRW':symbol.endsWith('.T')?'JPY':'USD';}
function timezoneFor(symbol){return symbol.endsWith('.KS')?'Asia/Seoul':symbol.endsWith('.T')?'Asia/Tokyo':symbol.endsWith('=X')?'Europe/London':'America/New_York';}
// Public Universe504 code → Worker/Yahoo symbol ('NYSE:BRK.B' → 'BRK-B'); anything else → null.
function universeSymbol(code){const m=typeof code==='string'?UNIVERSE_CODE.exec(code):null;return m?m[1].replace(/\./g,'-'):null;}

/* ---------- tab parsing ---------- */
/* values = [header, row, ...] as read (rows: at least symbol, date, close). A header other than HEAD → SHEET_HEADER_MISMATCH.
   Empty rows are skipped; malformed rows are skipped and counted. */
function parseTab(values,interval){
 if(!own(TABS,interval))fail('INVALID');
 if(!Array.isArray(values))fail('SHEET_ROWS_INVALID');
 if(!values.length)return{header:false,rows:[],invalid:0};
 const first=values[0];if(!Array.isArray(first)||first.length!==HEAD.length||first.some((c,i)=>c!==HEAD[i]))fail('SHEET_HEADER_MISMATCH');
 const rows=[];let invalid=0;
 for(let i=1;i<values.length;i++){
  const raw=values[i];if(!Array.isArray(raw)||!raw.some(c=>c!==''&&c!==null&&c!==undefined))continue;
  const symbol=raw[0],d=raw[1],text=raw.length>2?raw[2]:'';
  if(!(okSymbol(symbol)&&isDay(d)&&typeof text==='string'&&NUMBER_TEXT.test(text))){invalid++;continue;}
  const close=Number(text);if(!(close>0)||!Number.isFinite(close)){invalid++;continue;}
  rows.push([symbol,d,close]);
 }
 return{header:true,rows,invalid};
}
// Stored rows (sheet order) → {symbol: {key: close}}, key = date (1d) or month (1mo). The first stored row wins.
function indexRows(rows,interval){
 const series={};let duplicates=0;
 for(const[symbol,d,close]of rows){const key=interval==='1d'?d:d.slice(0,7),s=series[symbol]||(series[symbol]={});if(own(s,key)){duplicates++;continue;}s[key]=close;}
 const out={};for(const k of Object.keys(series).sort())out[k]=sortedObject(series[k]);
 return{series:out,duplicates};
}

/* ---------- Worker payload ---------- */
// Worker private-history/1 payload → [final closes {date: close}, null] or [{}, code]: exactly the runner's rule.
function closesFromHistory(payload,symbol){return runner().seriesFromHistory(payload,symbol,currencyFor(symbol));}
function sourceOf(payload){const p=object(payload)?payload.provider:null;return typeof p==='string'&&own(SOURCES,p)?SOURCES[p]:'UNKNOWN';}
// Daily closes → {month: [last session date, close]} for complete months only (months before as_of's month).
function monthEnds(closes,asOf){const current=asOf.slice(0,7),out={};for(const d of Object.keys(closes).sort())if(d.slice(0,7)<current)out[d.slice(0,7)]=[d,closes[d]];return out;}

/* ---------- incremental plan ---------- */
const pad=n=>String(n).padStart(2,'0');
function monthsBack(today,n){
 let y=+today.slice(0,4),m=+today.slice(5,7)-n;while(m<=0){y--;m+=12;}
 const last=new Date(Date.UTC(y,m,0)).getUTCDate();return String(y).padStart(4,'0')+'-'+pad(m)+'-'+pad(Math.min(+today.slice(8,10),last));
}
const weekday=d=>new Date(Date.parse(d+'T00:00:00Z')).getUTCDay();
const prevDay=d=>new Date(Date.parse(d+'T00:00:00Z')-86400000).toISOString().slice(0,10);
// Latest session date whose close can be final at localDay localTime (weekends → Friday; a holiday costs one extra request).
function dueDate(symbol,localDay,localTime){
 if(!isDay(localDay)||!(typeof localTime==='string'&&CLOCK.test(localTime)))fail('INVALID');
 let close=US_CLOSE;for(const[suffix,at]of CLOSE_TIMES)if(symbol.endsWith(suffix))close=at;
 let d=localDay;const wd=weekday(d);
 if(!(wd%6!==0&&close!==null&&localTime>=close)){d=prevDay(d);while(weekday(d)%6===0)d=prevDay(d);}
 return d;
}
// Daily: null when the last stored date reaches the due date, else the smallest Worker range whose window starts on or
// before the last stored date (overlap); '5y' without stored rows or for a longer gap.
function nextRange(last,due,today){
 if(last!==null&&last>=due)return null;if(last===null)return'5y';
 for(const[name,months]of RANGES)if(monthsBack(today,months)<=last)return name;return'5y';
}
function monthDue(today){let y=+today.slice(0,4),m=+today.slice(5,7)-1;if(m===0){y--;m=12;}return String(y).padStart(4,'0')+'-'+pad(m);}
// Month-end rows: null when the last stored month reaches the last complete month; '5y' first (5-year backfill).
function nextMonthRange(lastMonth,today){
 if(lastMonth!==null&&lastMonth>=monthDue(today))return null;if(lastMonth===null)return'5y';
 const y=+lastMonth.slice(0,4),m=+lastMonth.slice(5,7),end=lastMonth+'-'+pad(new Date(Date.UTC(y,m,0)).getUTCDate());
 return nextRange(end,'9999-12-31',today);
}
/* stored {key: close}; fetched daily {date: close} or month-ends {month: [date, close]} → rows to append [[date, close]]
   (keys not stored, date order) and how many stored keys the provider now reports differently (ignored, counted). */
function appendPlan(stored,fetched,interval){
 const out=[];let revised=0;
 for(const key of Object.keys(fetched).sort()){
  const item=fetched[key],d=interval==='1d'?key:item[0],close=interval==='1d'?item:item[1];
  if(own(stored,key)){if(stored[key]!==close)revised++;continue;}
  out.push([d,close]);
 }
 out.sort((a,b)=>a[0]<b[0]?-1:a[0]>b[0]?1:0);
 return{append:out,revised_ignored:revised};
}
function sheetRows(symbol,planRows,source,fetchedAt){return planRows.map(([d,close])=>[symbol,d,ledger().numStr(close),source,fetchedAt]);}

/* ---------- reads ---------- */
// {month: close}: stored month-end rows first; complete months missing there come from the stored daily closes.
function monthEndCloses(daily,monthly,asOf){
 const out={...(monthly||{})};for(const[month,[,close]]of Object.entries(monthEnds(daily||{},asOf)))if(!own(out,month))out[month]=close;
 return sortedObject(out);
}
function dailyCloses(daily,fromDate=null){const out={};for(const d of Object.keys(daily||{}).sort())if(fromDate===null||fromDate===undefined||d>=fromDate)out[d]=daily[d];return out;}
/* Stored daily closes → a private-history/1 payload the runner reads exactly like a Worker answer: the runner's 2y window
   (dates on or after today minus 24 months), at most MAX_BARS bars, every bar COMPLETE. */
function runnerPayload(closes,symbol,today,readAt){
 const cutoff=monthsBack(today,24),days=Object.keys(closes).sort().filter(d=>d>=cutoff).slice(-MAX_BARS);
 const bars=days.map(d=>({timestamp:Date.UTC(+d.slice(0,4),+d.slice(5,7)-1,+d.slice(8,10),12)/1000,session_date:d,session_status:'COMPLETE',close:closes[d]}));
 return{schema:'private-history/1',provider:'PRICE_STORE',symbol,range:RUNNER_RANGE,currency:currencyFor(symbol),exchange:'PRICE_STORE',timezone:timezoneFor(symbol),interval:'1d',
  basis:'RAW_CLOSE',delay_status:'UNKNOWN',read_at:readAt,bars};
}
// Append chunks whose JSON text stays within maxBytes.
function chunkRows(rows,maxBytes){const out=[];let cur=[],size=0;for(const r of rows){const n=JSON.stringify(r).length+1;if(cur.length&&size+n>maxBytes){out.push(cur);cur=[];size=0;}cur.push(r);size+=n;}if(cur.length)out.push(cur);return out;}

/* ---------- Google Sheet I/O (user's own sheet, drive.file session; write allowlist in GoogleSheetQuotes) ---------- */
const FLAG_KEY='investment.web.v1.price-store-enabled',HISTORY_KEY='investment.web.v1.private-history-origin';
const PAGE=10000,MAX_PAGES=60,MAX_APPEND=200000,DEFAULT_SPACING_MS=5200,RATE_RETRY_MS=15000,RATE_RETRIES=2;
const STOP=new Set(['AUTH_REQUIRED','AUTH_FORBIDDEN','AUTH_UNAVAILABLE','ORIGIN_FORBIDDEN','CONFIG_UNAVAILABLE','CANCELED','RATE_LIMIT_UNAVAILABLE']);
const CODE_TEXT=/^[A-Z][A-Z0-9_]{0,63}$/;
const errorCode=(e,fallback)=>e&&typeof e.message==='string'&&CODE_TEXT.test(e.message)?e.message:fallback;
const ignoredTab=t=>typeof t==='string'&&t.startsWith('Example_');
// Header row, then data pages (symbol, date, close only). An empty header with rows below reads as a header mismatch.
async function readValues(session,id,tab){
 const head=await session.fetchValues(id,"'"+tab+"'!A1:E1",{maxBytes:65536,allowEmpty:true}),header=Array.isArray(head.values)&&head.values.length?head.values[0]:[];
 const rows=[];let done=false;
 for(let p=0;p<MAX_PAGES&&!done;p++){const from=2+p*PAGE,payload=await session.fetchValues(id,"'"+tab+"'!A"+from+':C'+(from+PAGE-1),{maxBytes:1048576,allowEmpty:true});
  const page=Array.isArray(payload.values)?payload.values:[];for(const r of page)rows.push(r);done=page.length<PAGE;}
 if(!done)fail('SOURCE_TOO_LARGE');
 if(!header.length&&!rows.some(r=>Array.isArray(r)&&r.some(c=>c!==''&&c!==null&&c!==undefined)))return[];
 return[header,...rows];
}
// Reads the wanted tabs into sheet: one tab per interval, so Prices_M (Universe504 month-ends) is read only when a
// month-end view is needed and an app open reads Prices_D alone.
async function readInto(session,id,sheet,intervals){
 for(const interval of intervals){
  const tab=TABS[interval];if(sheet.state!=='READY'||sheet.loaded[interval])continue;
  if(sheet.tabs[tab]){
   const values=await readValues(session,id,tab);let parsed;
   try{parsed=parseTab(values,interval);}catch(e){Object.assign(sheet,{state:'ERROR',reason_codes:[errorCode(e,'SHEET_ROWS_INVALID')],tab,daily:{},monthly:{}});return sheet;}
   if(!parsed.header&&!sheet.headerless.includes(tab))sheet.headerless.push(tab);
   const idx=indexRows(parsed.rows,interval);sheet[interval==='1d'?'daily':'monthly']=idx.series;sheet.invalid+=parsed.invalid;sheet.duplicates+=idx.duplicates;sheet.rows[tab]=parsed.rows.length;
  }
  sheet.loaded[interval]=true;
 }
 return sheet;
}
async function load(session,id,intervals=['1d','1mo']){
 const titles=(await session.sheetTitles(id)).filter(t=>!ignoredTab(t));
 const sheet={state:'READY',reason_codes:[],tab:null,tabs:{},headerless:[],daily:{},monthly:{},invalid:0,duplicates:0,rows:{[TAB_DAILY]:0,[TAB_MONTHLY]:0},loaded:{'1d':false,'1mo':false}};
 for(const tab of Object.values(TABS))sheet.tabs[tab]=titles.includes(tab);
 return readInto(session,id,sheet,intervals);
}
// Creates a missing tab (title only) and writes the header into an empty tab. Nothing else.
async function ensureTab(session,id,sheet,tab){
 if(!sheet.tabs[tab]){await session.addTabs(id,[tab]);sheet.tabs[tab]=true;if(!sheet.headerless.includes(tab))sheet.headerless.push(tab);}
 if(sheet.headerless.includes(tab)){await session.appendRows(id,"'"+tab+"'!A1",[[...HEAD]]);sheet.headerless=sheet.headerless.filter(t=>t!==tab);}
}
async function appendTab(session,id,sheet,tab,rows){await ensureTab(session,id,sheet,tab);for(const chunk of chunkRows(rows,MAX_APPEND))await session.appendRows(id,"'"+tab+"'!A1",chunk);}

/* ---------- device state (RAM only, one per window) ---------- */
const stores=new WeakMap();
function storeFor(view){let s=stores.get(view);if(!s){s={key:null,sheet:null,loading:null,queue:Promise.resolve(),checked:new Map(),lastNetwork:0,revised_ignored:0,lastSync:null,listeners:new Set(),busy:null,progress:null,abort:null};stores.set(view,s);}return s;}
function notify(store){for(const f of [...store.listeners]){try{f();}catch(_){}}}
function reset(store){store.key=null;store.sheet=null;store.loading=null;store.checked=new Map();store.revised_ignored=0;store.lastSync=null;notify(store);}
function enabled(view){try{return view.localStorage.getItem(FLAG_KEY)==='1';}catch(_){return false;}}
function context(view){
 const config=object(view.InvestmentAppConfig)?view.InvestmentAppConfig:{};let session=null,sheetId='',origin='';
 try{session=config.googleSheetsClientId&&view.GoogleSheetQuotes?view.GoogleSheetQuotes.sessionFor(view,config.googleSheetsClientId):null;}catch(_){session=null;}
 try{sheetId=view.GoogleSheetSetup?view.GoogleSheetSetup.source(view):'';}catch(_){sheetId='';}
 try{const v=view.localStorage.getItem(HISTORY_KEY);origin=v&&view.PrivateHistory?view.PrivateHistory.parseWorkerOrigin(v):'';}catch(_){origin='';}
 const connected=!!(session&&session.state().connected);
 const code=!enabled(view)?'OFF':!connected?'AUTH_REQUIRED':!sheetId?'SHEET_NOT_CONNECTED':'READY';
 const fetchCode=config.privateHistoryEnabled!==true?'OFF':!origin||origin!==config.privateHistoryWorkerOrigin?'ORIGIN_UNAPPROVED':'READY';
 const v=config.virtualTradingRequestSpacingMs,spacing=Number.isInteger(v)&&v>=0&&v<=60000?v:DEFAULT_SPACING_MS;
 return{config,session,sheetId,origin,code,fetchCode,spacing};
}
// interval '1d' reads Prices_D; '1mo' also reads Prices_M (month-end views merge both).
function ensureLoaded(view,ctx,store,interval='1d'){
 const key=ctx.sheetId+'#'+ctx.session.revision();
 if(store.key!==key){reset(store);store.key=key;}
 const want=interval==='1mo'?['1d','1mo']:['1d'],ready=s=>!!s&&(s.state!=='READY'||want.every(i=>s.loaded[i]));
 if(ready(store.sheet))return Promise.resolve(store.sheet);
 if(store.loading)return store.loading.then(()=>ensureLoaded(view,ctx,store,interval));
 const loading=(store.sheet?readInto(ctx.session,ctx.sheetId,store.sheet,want):load(ctx.session,ctx.sheetId,want)).then(sheet=>{if(store.loading===loading){store.sheet=sheet;store.loading=null;notify(store);}return sheet;},
  e=>{if(store.loading===loading){store.loading=null;if(!store.sheet)store.key=null;notify(store);}throw e;});
 store.loading=loading;notify(store);return loading;
}
// One Worker/sheet operation at a time per window (app-open sync, runner, company view, Universe504 button).
function exclusive(store,fn){const run=store.queue.then(fn,fn);store.queue=run.catch(()=>{});return run;}
const pause=(view,ms,signal)=>new Promise((resolve,reject)=>{if(signal&&signal.aborted){reject(new Error('CANCELED'));return;}if(ms<=0){resolve();return;}const t=view.setTimeout(resolve,ms);if(signal)signal.addEventListener('abort',()=>{view.clearTimeout(t);reject(new Error('CANCELED'));},{once:true});});
// The runner's request discipline: spacing between Worker requests, RATE_LIMITED retried twice after 15 s.
async function fetchOne(view,store,ctx,symbol,range,signal,spacing){
 for(let attempt=0;;attempt++){
  try{const wait=store.lastNetwork?store.lastNetwork+(attempt?RATE_RETRY_MS:spacing)-Date.now():0;await pause(view,Math.min(wait,RATE_RETRY_MS),signal);}catch(_){return{payload:null,code:'CANCELED'};}
  store.lastNetwork=Date.now();
  try{const payload=await ctx.session.fetchHistory(ctx.origin,symbol,range,{approvedOrigin:ctx.origin,signal:signal||undefined});return{payload,code:null};}
  catch(e){const code=errorCode(e,'HISTORY_UNAVAILABLE');if(code==='REQUEST_INVALID')store.lastNetwork=0;if(code==='RATE_LIMITED'&&attempt<RATE_RETRIES)continue;return{payload:null,code};}
 }
}
function localNow(ms,tz){
 const p={};for(const x of new Intl.DateTimeFormat('en-CA',{timeZone:tz,year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(ms))p[x.type]=x.value;
 return{day:p.year+'-'+p.month+'-'+p.day,time:p.hour+':'+p.minute};
}
const nowIso=ms=>new Date(ms).toISOString().replace(/\.\d{3}Z$/,'Z');
// What one symbol needs now: the Worker range to request, or null when the stored rows are current; due = the date (1d) or
// month (1mo) the stored rows must reach, so a 'current' memo ends when a new session / complete month becomes due.
function need(sheet,symbol,interval,ms){
 const{day,time}=localNow(ms,timezoneFor(symbol));
 if(interval==='1d'){const keys=Object.keys(sheet.daily[symbol]||{}),due=dueDate(symbol,day,time);return{day,due,range:nextRange(keys.length?keys[keys.length-1]:null,due,day)};}
 const keys=Object.keys(monthEndCloses(sheet.daily[symbol],sheet.monthly[symbol],day));return{day,due:monthDue(day),range:nextMonthRange(keys.length?keys[keys.length-1]:null,day)};
}
/* One symbol: fetch the missing range (if any), append only rows not stored, update the RAM index. Returns
   {code, fetched, appended, payload}: code null = current; payload = the Worker answer when the write failed. */
async function syncOne(view,store,ctx,symbol,interval,{signal=null,spacing=ctx.spacing,stop=null,now=Date.now}={}){
 const revision=ctx.session.revision(),sheet=store.sheet;
 if(!okSymbol(symbol))return{code:'REQUEST_INVALID',fetched:false,appended:0};
 const{day,due,range}=need(sheet,symbol,interval,now()),memo=interval+'|'+symbol,mark=revision+'|'+due;
 if(store.checked.get(memo)===mark)return{code:null,fetched:false,appended:0};
 if(range===null){store.checked.set(memo,mark);return{code:null,fetched:false,appended:0};}
 if(stop)return{code:stop,fetched:false,appended:0};
 if(ctx.fetchCode!=='READY')return{code:ctx.fetchCode,fetched:false,appended:0};
 const{payload,code}=await fetchOne(view,store,ctx,symbol,range,signal,spacing);
 if(code)return{code,fetched:true,appended:0};
 if(ctx.session.revision()!==revision||store.sheet!==sheet)return{code:'CANCELED',fetched:true,appended:0};
 const[closes,bad]=closesFromHistory(payload,symbol);if(bad)return{code:bad,fetched:true,appended:0};
 const daily=interval==='1d',tab=TABS[interval],target=daily?sheet.daily:sheet.monthly,stored=target[symbol]||{};
 const plan=appendPlan(stored,daily?closes:monthEnds(closes,day),interval);
 store.revised_ignored+=plan.revised_ignored;
 if(plan.append.length){
  try{await appendTab(ctx.session,ctx.sheetId,sheet,tab,sheetRows(symbol,plan.append,sourceOf(payload),nowIso(now())));}
  catch(e){return{code:null,fetched:true,appended:0,write:errorCode(e,'WRITE_FAILED'),payload};}
  const next={...stored};for(const[d,close]of plan.append)next[daily?d:d.slice(0,7)]=close;target[symbol]=sortedObject(next);sheet.rows[tab]+=plan.append.length;
 }
 store.checked.set(memo,mark);
 return{code:null,fetched:true,appended:plan.append.length,revised:plan.revised_ignored};
}
function summary(kind,results,extra={}){
 const failed={};let appended=0,fetched=0,current=0,writeFailed=0;
 for(const r of Object.values(results)){appended+=r.appended||0;if(r.fetched)fetched++;if(r.write)writeFailed++;if(r.code)failed[r.code]=(failed[r.code]||0)+1;else if(!r.write)current++;}
 return{kind,symbols:Object.keys(results).length,fetched,appended_rows:appended,current,write_failed:writeFailed,failed:sortedObject(failed),...extra};
}
async function syncMany(view,symbols,interval,{kind='CORE',signal=null,onProgress=null,now=Date.now,allowlistOnly=false}={}){
 const ctx=context(view),store=storeFor(view);if(ctx.code!=='READY')return{state:ctx.code};
 return exclusive(store,async()=>{
  const fresh=context(view);if(fresh.code!=='READY')return{state:fresh.code};
  let sheet;try{sheet=await ensureLoaded(view,fresh,store,interval);}catch(e){return{state:'ERROR',reason_codes:[errorCode(e,'READ_FAILED')]};}
  if(sheet.state!=='READY')return{state:'ERROR',reason_codes:sheet.reason_codes,tab:sheet.tab};
  // progress: symbols done / total, rows appended so far, the symbol being worked on (codes and counts only, never a close).
  const results={},list=[...new Set(symbols)];let stop=null,notAllowed=0,done=0,appended=0,requested=0;store.busy=kind;store.progress={done:0,total:list.length,appended:0,requested:0,current:null};notify(store);
  try{for(const symbol of list){
   if(signal&&signal.aborted)stop=stop||'CANCELED';
   store.progress={...store.progress,current:symbol};notify(store);
   if(allowlistOnly&&!allowed(view,symbol)){notAllowed++;results[symbol]={code:'WORKER_ALLOWLIST',fetched:false,appended:0};}
   else{const r=await syncOne(view,store,fresh,symbol,interval,{signal,stop,now});results[symbol]=r;if(r.code&&STOP.has(r.code))stop=r.code;appended+=r.appended||0;if(r.fetched)requested++;}
   done++;store.progress={done,total:list.length,appended,requested,current:symbol};if(onProgress)try{onProgress(done,list.length,{appended,requested,current:symbol});}catch(_){}notify(store);
  }}finally{store.busy=null;store.progress=null;}
  const out=summary(kind,results,{not_allowed:notAllowed});store.lastSync={...out,at:nowIso(now())};notify(store);
  return{state:'READY',...out,results};
 });
}
function allowed(view,symbol){const list=view.GoogleSheetQuotes&&view.GoogleSheetQuotes.HISTORY_SYMBOLS;return Array.isArray(list)&&list.includes(symbol);}

/* ---------- device API (RAM only) ---------- */
const viewOf=o=>o&&o.view?o.view:globalThis;
const clockOf=o=>o&&typeof o.now==='function'?o.now:Date.now;
// Stored month-end closes {'YYYY-MM': close} (Prices_M first, complete months from Prices_D). Stored rows only by default;
// fetch:true (a button handler only): a missing range of an allowlisted symbol is fetched through the Worker and appended
// first. Not connected → {} (NA).
async function apiMonthEndCloses(symbol,options={}){
 const view=viewOf(options),ctx=context(view),store=storeFor(view);if(ctx.code!=='READY'||!okSymbol(symbol))return{};
 const now=clockOf(options);
 if(options.fetch===true&&allowed(view,symbol))await syncMany(view,[symbol],'1mo',{kind:'API',signal:options.signal||null,now});
 let sheet;try{sheet=await ensureLoaded(view,ctx,store,'1mo');}catch(_){return{};}if(sheet.state!=='READY')return{};
 return monthEndCloses(sheet.daily[symbol],sheet.monthly[symbol],localNow(now(),timezoneFor(symbol)).day);
}
// Stored daily closes {date: close} on or after fromDate; stored rows only unless fetch:true (a button handler), which
// appends the missing tail first.
async function apiDailyCloses(symbol,fromDate=null,options={}){
 const view=viewOf(options),ctx=context(view),store=storeFor(view);if(ctx.code!=='READY'||!okSymbol(symbol))return{};
 if(options.fetch===true&&allowed(view,symbol))await syncMany(view,[symbol],'1d',{kind:'API',signal:options.signal||null,now:clockOf(options)});
 let sheet;try{sheet=await ensureLoaded(view,ctx,store);}catch(_){return{};}if(sheet.state!=='READY')return{};
 return dailyCloses(sheet.daily[symbol],fromDate);
}
const span=keys=>({count:keys.length,first:keys.length?keys[0]:null,last:keys.length?keys[keys.length-1]:null});
// Dates and counts only (no close).
function coverage(symbol,options={}){
 const store=storeFor(viewOf(options)),sheet=store.sheet;if(!sheet||sheet.state!=='READY')return{daily:span([]),monthly:span([]),month_ends:span([])};
 return{daily:span(Object.keys(sheet.daily[symbol]||{})),monthly:span(Object.keys(sheet.monthly[symbol]||{})),
  month_ends:span(Object.keys(monthEndCloses(sheet.daily[symbol],sheet.monthly[symbol],localNow(Date.now(),timezoneFor(okSymbol(symbol)?symbol:'SPY')).day)))};
}
// Store state with counts only (no close, no sheet id).
function status(options={}){
 const view=viewOf(options),ctx=context(view),store=storeFor(view),sheet=store.sheet;
 const base={schema:SCHEMA,state:ctx.code,fetch:ctx.fetchCode,reason_codes:[],tabs:{},symbols:{daily:0,monthly:0},invalid_rows:0,duplicate_rows:0,revised_ignored:store.revised_ignored,busy:store.busy,progress:store.progress,last_sync:store.lastSync};
 if(ctx.code!=='READY')return base;
 if(!sheet)return{...base,state:'LOADING'};
 if(sheet.state!=='READY')return{...base,state:'ERROR',reason_codes:[...sheet.reason_codes],tab:sheet.tab};
 const tab=(t,i)=>({present:sheet.tabs[t],read:sheet.loaded[i],rows:sheet.loaded[i]?sheet.rows[t]:null});
 return{...base,tabs:{[TAB_DAILY]:tab(TAB_DAILY,'1d'),[TAB_MONTHLY]:tab(TAB_MONTHLY,'1mo')},
  symbols:{daily:Object.keys(sheet.daily).length,monthly:sheet.loaded['1mo']?Object.keys(sheet.monthly).length:null},invalid_rows:sheet.invalid,duplicate_rows:sheet.duplicates};
}
function subscribe(listener,options={}){const store=storeFor(viewOf(options));store.listeners.add(listener);return()=>store.listeners.delete(listener);}

/* ---------- runner integration ---------- */
/* Histories for VirtualTradingRunner (same shape as its own fetch): read the stored daily closes first and fetch only the
   missing range per symbol through the same Worker session (same spacing, RATE_LIMITED retries, stop codes, SPY rule).
   A symbol whose missing range failed gets the same {error} as before (never a stale series). null = store not in use
   (OFF, not connected, sheet unreadable or header mismatch): the runner then uses its own path.
   fetch (default false = a screen open): the stored rows only, no Worker request; a symbol without stored rows gets
   {error:'PRICE_NOT_FETCHED'}. fetch:true only from the report's button. */
async function runnerHistories(view,{session,origin,symbols,spacingMs=DEFAULT_SPACING_MS,signal=null,onProgress=null,now=Date.now,fetch=false}={}){
 const ctx=context(view),store=storeFor(view);
 if(ctx.code!=='READY'||ctx.session!==session||!Array.isArray(symbols))return null;
 return exclusive(store,async()=>{
  const fresh=context(view);if(fresh.code!=='READY'||fresh.session!==session)return null;
  let sheet;try{sheet=await ensureLoaded(view,fresh,store);}catch(_){return null;}if(sheet.state!=='READY')return null;
  const run={...fresh,origin,fetchCode:fresh.fetchCode==='READY'&&origin===fresh.origin?'READY':fresh.fetchCode};
  const out={},results={};let stop=null,done=0;
  const stored=symbol=>{const closes=store.sheet.daily[symbol]||{};return Object.keys(closes).length?runnerPayload(closes,symbol,localNow(now(),timezoneFor(symbol)).day,nowIso(now())):null;};
  if(fetch!==true){for(const symbol of symbols){out[symbol]=stored(symbol)||{error:'PRICE_NOT_FETCHED'};done++;if(onProgress)try{onProgress(done,symbols.length);}catch(_){}}return out;}
  for(const symbol of symbols){
   if(signal&&signal.aborted)stop=stop||'CANCELED';
   const r=await syncOne(view,store,run,symbol,'1d',{signal,spacing:spacingMs,stop,now});results[symbol]=r;
   if(r.code!==null){out[symbol]={error:r.code};if(STOP.has(r.code))stop=r.code;}
   else if(r.write&&r.payload)out[symbol]=r.payload;
   else out[symbol]=stored(symbol)||{error:'HISTORY_UNAVAILABLE'};
   done++;if(onProgress)try{onProgress(done,symbols.length);}catch(_){}
   if(symbol==='SPY'&&r.code!==null)break;
  }
  store.lastSync={...summary('RUNNER',results),at:nowIso(now())};notify(store);
  return out;
 });
}

/* ---------- core symbols (holdings, watchlist ★, sets A–D, runner benchmarks/FX) ---------- */
async function readMetaSets(session,id){
 const L=ledger();if(!L)return null;const titles=await session.sheetTitles(id);if(!titles.includes(L.META))return null;
 const values=[];for(let p=0;p<20;p++){const from=p*1000+1,payload=await session.fetchValues(id,"'"+L.META+"'!A"+from+':K'+(from+999),{maxBytes:1048576,allowEmpty:true});const rows=Array.isArray(payload.values)?payload.values:[];for(const r of rows)values.push(r);if(rows.length<1000)break;}
 const meta=L.parseMeta(L.parseTab(values,L.META_HEAD).rows);if(meta.state!=='OK')return null;
 const def=k=>{const l=L.active(meta,k);return l?{target_weights:{...l.target_weights}}:null;};
 return{sets:{SET_A:def('SET_A'),SET_B:def('SET_B'),SET_C:def('SET_C'),SET_D:def('SET_D')},user_target:meta.user_target?{...meta.user_target}:null};
}
async function coreSymbols(view,{catalog,interests=[]}={}){
 const R=runner(),ctx=context(view);let classification=null,holdings=null,sheetSets={sets:null,user_target:null};
 try{classification=view.ClassificationScreens?await view.ClassificationScreens.load(view):null;}catch(_){classification=null;}
 try{const A=view.DeviceActual;holdings=R.holdingsFromSnapshot(A.effectiveHoldings?(await A.effectiveHoldings(view,catalog)).snapshot:await A.readHoldings(view,catalog),catalog);}catch(_){holdings=null;}
 try{if(ctx.code==='READY')sheetSets=(await readMetaSets(ctx.session,ctx.sheetId))||sheetSets;}catch(_){}
 const required=R.requiredSymbols({catalog,classification,holdings,sets:sheetSets.sets,user_target:sheetSets.user_target});
 const starred=(Array.isArray(interests)?interests:[]).filter(c=>own(R.TARGETS,c)).map(c=>R.TARGETS[c]);
 return[...new Set([...required,...starred])];
}
/* App open: once per Google session (and after the user turns the store on), READ the stored Prices_D rows into RAM. No
   Worker request and no sheet write (owner decision 2026-10-23: requests only from a button; the core symbols' daily bars
   are appended by the settings button '핵심 종목 일봉 지금 갱신'). Nothing happens while the store is OFF or not connected. */
function autoLoad(view){
 const ctx=context(view),store=storeFor(view);let last=null;
 const tick=()=>{const c=context(view);if(c.code!=='READY'||!c.session){if(c.code!=='READY'&&store.sheet)reset(store);return;}const key=c.sheetId+'#'+c.session.revision();if(key===last)return;last=key;
  void ensureLoaded(view,c,store).catch(()=>{});};
 store.retick=()=>{last=null;tick();};
 let unsubscribe=null;try{if(ctx.session)unsubscribe=ctx.session.subscribe(tick);}catch(_){unsubscribe=null;}
 tick();return()=>{if(unsubscribe)unsubscribe();store.retick=null;};
}
// "Use Prices tabs" (user's click): creates Prices_D / Prices_M with their header when missing, then turns the store on
// for this device. A tab whose header differs is never written (SHEET_HEADER_MISMATCH).
async function enable(view){
 const config=object(view.InvestmentAppConfig)?view.InvestmentAppConfig:{};let session=null,sheetId='';
 try{session=view.GoogleSheetQuotes.sessionFor(view,config.googleSheetsClientId);sheetId=view.GoogleSheetSetup.source(view);}catch(_){fail('SHEET_NOT_CONNECTED');}
 if(!session||!session.state().connected)fail('AUTH_REQUIRED');if(!sheetId)fail('SHEET_NOT_CONNECTED');
 const store=storeFor(view);
 return exclusive(store,async()=>{
  const sheet=await load(session,sheetId);if(sheet.state!=='READY')fail(sheet.reason_codes[0]);
  for(const tab of [TAB_DAILY,TAB_MONTHLY])await ensureTab(session,sheetId,sheet,tab);
  try{view.localStorage.setItem(FLAG_KEY,'1');}catch(_){fail('DEVICE_STORAGE_UNAVAILABLE');}
  reset(store);store.key=sheetId+'#'+session.revision();store.sheet=sheet;notify(store);
  if(store.retick)store.retick();return status({view});
 });
}
// Turns the store off on this device only (the sheet and its rows stay as they are) and drops the RAM index.
function disable(view){try{view.localStorage.removeItem(FLAG_KEY);}catch(_){}reset(storeFor(view));}
// Universe504 month-ends (user's click): first run backfills 5 years, then only new complete months. Only symbols on the
// approved Worker allowlist are requested; unknown symbols are counted as WORKER_ALLOWLIST.
async function universeSymbols(view){
 const config=object(view.InvestmentAppConfig)?view.InvestmentAppConfig:{};if(config.universeCodeCatalogURL!=='universe-codes.json')fail('UNIVERSE_CODES_NOT_AVAILABLE');
 const response=await view.fetch('universe-codes.json',{credentials:'omit',cache:'no-store',referrerPolicy:'no-referrer',redirect:'error'});if(!response.ok)fail('UNIVERSE_CODES_NOT_AVAILABLE');
 const text=await response.text();if(text.length>65536)fail('SOURCE_TOO_LARGE');let codes;try{codes=view.GoogleSheetSetup.codes(JSON.parse(text));}catch(_){fail('UNIVERSE_CODES_NOT_AVAILABLE');}
 return[...new Set(codes.map(universeSymbol).filter(Boolean))];
}
async function syncUniverse(view,{signal=null,onProgress=null,now=Date.now}={}){
 const symbols=await universeSymbols(view);
 const result=await syncMany(view,symbols,'1mo',{kind:'UNIVERSE504',signal,onProgress,now,allowlistOnly:true});
 return result.state==='READY'?{...result,results:undefined,universe:symbols.length}:result;
}
function universeProgress(view,symbols,ms=Date.now()){
 const sheet=storeFor(view).sheet;if(!sheet||sheet.state!=='READY')return null;let current=0;
 for(const s of symbols){const keys=Object.keys(monthEndCloses(sheet.daily[s],sheet.monthly[s],localNow(ms,timezoneFor(s)).day));if(keys.length&&keys[keys.length-1]>=monthDue(localNow(ms,timezoneFor(s)).day))current++;}
 return{current,total:symbols.length};
}

/* ---------- screens (codes, counts and dates only) ---------- */
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const T={
 title:['가격 저장 탭 · 내 구글 시트 (Prices_D · Prices_M)','Price tabs · my Google Sheet (Prices_D · Prices_M)'],
 detail:['한 번 받은 종가를 내 시트에 덧붙여 두고 다음부터는 시트에서 읽습니다. 화면을 열 때는 저장된 가격만 읽고, 가격 요청은 버튼을 눌렀을 때만 합니다. 핵심 종목(보유·관심 ★·세트 A–D·벤치마크/환율·판정 채점용으로 추가한 종목)은 아래 버튼으로 마지막 저장일 이후 일봉만, Universe504는 버튼으로 월말 종가만(첫 실행 5년, 다음부터 새 달치만) 덧붙입니다. 기록한 행은 고치지 않습니다. 화면에는 개수·날짜·코드만 보이며 가격은 이 기기 메모리와 내 시트에만 있습니다.',
  'Closes fetched once are appended to your own sheet and read from it afterwards. Opening a screen reads stored prices only; prices are requested only when you press a button. Core symbols (holdings, watchlist ★, sets A–D, benchmarks/FX, symbols added for judgement scoring): daily bars after the last stored date, by the button below. Universe504: month-end closes only, by the button (first run: 5 years, then new months only). Stored rows are never rewritten. Only counts, dates and codes are shown; prices stay in this device\'s memory and your sheet.'],
 enable:['가격 탭 사용 시작','Use price tabs'],disable:['이 기기에서 끄기','Turn off on this device'],core:['핵심 종목 일봉 지금 갱신','Update core daily bars now'],universe:['Universe504 월말 종가 일괄 받기 (첫 실행 5년 · 이어받기)','Fetch all Universe504 month-ends (first run: 5 years · resumes)'],
 cancel:['중단','Stop'],canceled:['중단됨 · 다시 누르면 이미 받은 종목은 요청 없이 건너뛰고 이어받습니다.','Stopped · press again to resume; symbols already received are skipped without a request.'],
 working:['받는 중','fetching'],partial:['받은 종목부터 순위·V에 반영됩니다(다 받기 전에도). 요청 간격 약 5초 · 504종목 첫 실행은 약 45분.','Received symbols count toward ranks and V right away (before the run ends). About 5 s between requests · the first 504-symbol run takes about 45 minutes.'],
 OFF:['OFF · 이 기기에서 가격 탭을 쓰지 않습니다.','OFF · Price tabs are not used on this device.'],AUTH_REQUIRED:['구글 로그인이 필요합니다.','Google sign-in is required.'],SHEET_NOT_CONNECTED:['연결된 시트가 없습니다(설정 → Google 첫 설정).','No sheet is connected (Settings → Google first setup).'],
 LOADING:['내 시트의 가격 탭을 읽는 중','Reading the price tabs of your sheet'],READY:['가격 탭 읽음','Price tabs read'],ERROR:['가격 탭을 쓸 수 없습니다','Price tabs cannot be used'],
 worker:['승인된 비공개 가격 Worker 허용 범위는 Universe504 · TARGET 19 · ETF 17(HYG·IEF 포함) · 환율입니다. 등록되지 않은 종목은 WORKER_ALLOWLIST로 세며, Worker 연결에 실패하면 확인 불가로 표시합니다.','The approved private price Worker scope is Universe504, TARGET 19, 17 ETFs (including HYG/IEF), and FX. Unlisted symbols count as WORKER_ALLOWLIST; a failed Worker connection is shown as unavailable.']};
const tx=(locale,k)=>T[k][locale==='en-US'?1:0];
function statusLine(s,locale){
 const en=locale==='en-US';let text=tx(locale,s.state==='LOADING'||s.state==='ERROR'||s.state==='READY'||s.state==='OFF'||s.state==='AUTH_REQUIRED'||s.state==='SHEET_NOT_CONNECTED'?s.state:'ERROR');
 if(s.state==='ERROR'&&s.reason_codes.length)text+=' · '+s.reason_codes.join(', ')+(s.tab?' ('+s.tab+')':'');
 if(s.state==='READY'){const d=s.tabs[TAB_DAILY],m=s.tabs[TAB_MONTHLY];
  const tabText=(t,n)=>!t||!t.present?'—':t.read?t.rows+(en?' rows / ':'행 / ')+n+(en?' symbols':'종목'):(en?'not read yet':'아직 읽지 않음');
  text+=' · '+TAB_DAILY+' '+tabText(d,s.symbols.daily)+' · '+TAB_MONTHLY+' '+tabText(m,s.symbols.monthly);
  const flags=[];if(s.invalid_rows)flags.push('PRICE_ROW_INVALID '+s.invalid_rows);if(s.duplicate_rows)flags.push('PRICE_ROW_DUPLICATE '+s.duplicate_rows);if(s.revised_ignored)flags.push('PRICE_REVISED_IGNORED '+s.revised_ignored);if(flags.length)text+=' · '+flags.join(' · ');}
 if(s.fetch!=='READY'&&s.state==='READY')text+=' · Worker '+s.fetch;
 return text;
}
// Live progress of a button run: kind · done/total · rows appended · current symbol (codes and counts only).
function progressLine(s,locale){const p=s.progress,en=locale==='en-US';if(!p)return'';
 return(s.busy==='UNIVERSE504'?'Universe504 ':s.busy+' ')+tx(locale,'working')+' · '+p.done+'/'+p.total+' · '+(en?'rows appended ':'덧붙인 행 ')+(p.appended||0)+(p.current?' · '+(en?'current ':'현재 ')+p.current:'');}
function syncLine(r,locale){
 if(!r)return'';const en=locale==='en-US',f=Object.entries(r.failed||{}).map(([k,v])=>k+' '+v).join(', ');
 return(r.kind||'')+' · '+(en?'symbols ':'종목 ')+r.symbols+' · '+(en?'requests ':'요청 ')+r.fetched+' · '+(en?'rows appended ':'덧붙인 행 ')+r.appended_rows+' · '+(en?'current ':'최신 ')+r.current+(r.not_allowed?' · WORKER_ALLOWLIST '+r.not_allowed:'')+(r.write_failed?' · WRITE_FAILED '+r.write_failed:'')+(f?' · '+f:'')+(r.at?' · '+r.at:'');
}
const mounted=new WeakMap();
function mountSettings(host,{locale='ko-KR',coreSymbols:list=null}={}){
 const view=host.ownerDocument.defaultView,old=mounted.get(host);if(old)old();
 let note='',disposed=false;const live=()=>!disposed&&host.isConnected;
 const paint=()=>{
  if(!live()){dispose();return;}const s=status({view}),on=s.state!=='OFF',busy=!!s.busy,store=storeFor(view);
  // While a run only advances (same state, same buttons), update the status/progress lines in place: re-rendering every
  // tick would replace the 중단 button under the user's finger.
  const shape=[s.state,on,busy,!!(busy&&store.abort&&!store.abort.signal.aborted),!!s.progress,note].join('|'),sec=host.querySelector('[data-price-store]');
  if(sec&&host.dataset.priceStoreShape===shape){
   const st=sec.querySelector('[data-price-store-status]');if(st)st.textContent=statusLine(s,locale);
   const pr=sec.querySelector('[data-price-store-progress]');if(pr&&s.progress){pr.textContent=progressLine(s,locale);pr.dataset.done=String(s.progress.done);pr.dataset.total=String(s.progress.total);pr.dataset.appended=String(s.progress.appended||0);}
   const la=sec.querySelector('[data-price-store-last]');if(la)la.textContent=syncLine(s.last_sync,locale);
   return;}
  host.dataset.priceStoreShape=shape;
  host.innerHTML='<section class="card" data-price-store data-price-store-state="'+esc(s.state)+'"><h2>'+esc(tx(locale,'title'))+'</h2><p class="small">'+esc(tx(locale,'detail'))+'</p>'
   +'<p role="status" data-price-store-status>'+esc(statusLine(s,locale))+'</p>'
   +(s.progress?'<p class="small" role="status" data-price-store-progress data-done="'+s.progress.done+'" data-total="'+s.progress.total+'" data-appended="'+(s.progress.appended||0)+'">'+esc(progressLine(s,locale))+'</p>':'')
   +'<p class="small" data-price-store-last>'+esc(syncLine(s.last_sync,locale))+'</p>'
   +'<div class="sheet-actions">'+(on?'<button type="button" data-price-store-action="core"'+(s.state==='READY'&&!busy?'':' disabled')+'>'+esc(tx(locale,'core'))+'</button><button type="button" data-price-store-action="universe"'+(s.state==='READY'&&!busy?'':' disabled')+'>'+esc(tx(locale,'universe'))+'</button>'+(busy&&store.abort&&!store.abort.signal.aborted?'<button type="button" data-price-store-action="cancel">'+esc(tx(locale,'cancel'))+'</button>':'')+'<button type="button" data-price-store-action="disable">'+esc(tx(locale,'disable'))+'</button>'
    :'<button type="button" data-price-store-action="enable">'+esc(tx(locale,'enable'))+'</button>')+'</div>'
   +(on?'<p class="small" data-price-store-partial>'+esc(tx(locale,'partial'))+'</p>':'')+'<p class="small">'+esc(tx(locale,'worker'))+'</p><p role="status" class="small" data-price-store-note>'+esc(note)+'</p></section>';
  const act=(name,fn)=>{const b=host.querySelector('[data-price-store-action="'+name+'"]');if(b)b.onclick=()=>void(async()=>{note='';try{note=(await fn())||'';}catch(e){note=errorCode(e,'WRITE_FAILED');}if(live())paint();})();};
  act('enable',async()=>{await enable(view);return'';});
  act('disable',async()=>{disable(view);return'OFF';});
  // Button runs: one AbortController per window (중단); a stopped run keeps every row already appended, and pressing again
  // skips the symbols already current (checked this session, or stored up to the last complete month) without a request.
  const runText=r=>r.state!=='READY'?r.state+(r.reason_codes?' · '+r.reason_codes.join(', '):''):r.failed&&r.failed.CANCELED?tx(locale,'canceled'):'';
  const withAbort=async fn=>{const c=new view.AbortController();store.abort=c;try{return await fn(c.signal);}finally{if(store.abort===c)store.abort=null;}};
  act('core',()=>withAbort(async signal=>{const symbols=list?await list():[];return runText(await syncMany(view,symbols,'1d',{kind:'CORE',signal}));}));
  act('universe',()=>withAbort(async signal=>runText(await syncUniverse(view,{signal}))));
  const cancel=host.querySelector('[data-price-store-action="cancel"]');if(cancel)cancel.onclick=()=>{cancel.disabled=true;if(store.abort)store.abort.abort();};
 };
 const unsubscribe=subscribe(()=>{if(live())paint();else dispose();},{view});
 const ctx=context(view);let unsession=null;try{if(ctx.session)unsession=ctx.session.subscribe(()=>{if(live())paint();else dispose();});}catch(_){unsession=null;}
 function dispose(){if(disposed)return;disposed=true;unsubscribe();if(unsession)unsession();mounted.delete(host);}
 mounted.set(host,dispose);paint();
 if(ctx.code==='READY'&&!storeFor(view).sheet)void ensureLoaded(view,ctx,storeFor(view)).catch(()=>{});
 return dispose;
}
/* Company screen: opening it READS the stored month-ends only (no Worker request). The button '이 종목 월말 종가 받기'
   (Worker-allowed symbols only) stores its 5-year month-ends the first time and only new complete months afterwards.
   Shows counts and the stored month range only. */
function mountCompany(host,{symbol,locale='ko-KR'}={}){
 const view=host.ownerDocument.defaultView,en=locale==='en-US';let busy=false;
 const paint=(code)=>{if(!host.isConnected)return;const c=coverage(symbol,{view}),m=c.month_ends,cx=context(view),canFetch=code!=='LOADING'&&allowed(view,symbol)&&cx.code==='READY'&&cx.fetchCode==='READY';
  host.innerHTML='<p class="small" data-price-store-company="'+esc(code)+'" data-month-ends="'+m.count+'">'+esc((en?'Price tab · ':'가격 탭 · ')+(code==='READY'?(m.count?(en?'month-ends ':'월말 ')+m.count+(en?' stored (':'개 저장 (')+m.first+' ~ '+m.last+')':(en?'no month-ends stored':'저장된 월말 없음')):code))+'</p>'
   +(canFetch?'<div class="sheet-actions"><button type="button" data-price-store-company-fetch>'+esc(en?'Fetch this symbol\'s month-ends':'이 종목 월말 종가 받기')+'</button></div>':'');
  const b=host.querySelector('[data-price-store-company-fetch]');if(b)b.onclick=()=>{if(busy)return;busy=true;paint('LOADING');void(async()=>{let code='READY';
   try{const r=await syncMany(view,[symbol],'1mo',{kind:'VIEW'}),one=r.results&&r.results[symbol];code=r.state!=='READY'?(r.reason_codes&&r.reason_codes[0])||r.state:one&&one.code?one.code:one&&one.write?one.write:'READY';}catch(_){code='HISTORY_UNAVAILABLE';}
   busy=false;paint(code);})();};};
 const ctx=context(view);if(ctx.code==='OFF'){host.replaceChildren();return;}if(!okSymbol(symbol)){paint('REQUEST_INVALID');return;}if(ctx.code!=='READY'){paint(ctx.code);return;}
 paint('LOADING');
 void(async()=>{let code='READY';try{const sheet=await ensureLoaded(view,ctx,storeFor(view),'1mo');if(sheet.state!=='READY')code=sheet.reason_codes[0]||'ERROR';}catch(e){code=errorCode(e,'READ_FAILED');}
  paint(code==='READY'&&!allowed(view,symbol)?'WORKER_ALLOWLIST':code);})();
}

return Object.freeze({SCHEMA,CODES,TAB_DAILY,TAB_MONTHLY,TABS,HEAD,RANGES,FLAG_KEY,currencyFor,timezoneFor,universeSymbol,parseTab,indexRows,closesFromHistory,sourceOf,monthEnds,monthsBack,dueDate,nextRange,monthDue,
 nextMonthRange,appendPlan,sheetRows,monthEndClosesOf:monthEndCloses,dailyClosesOf:dailyCloses,runnerPayload,chunkRows,load,readValues,ensureTab,
 monthEndCloses:apiMonthEndCloses,dailyCloses:apiDailyCloses,coverage,status,subscribe,runnerHistories,coreSymbols,autoLoad,enable,disable,syncMany,syncUniverse,universeSymbols,universeProgress,allowed,mountSettings,mountCompany});
});
