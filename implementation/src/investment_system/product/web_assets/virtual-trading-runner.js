/* Virtual trading runner v1: builds the virtual-trading engine's ledger inputs on this device, RAM only.
   Pure part (assemble) mirrors qgv/virtual_trading_inputs.py (vectors: tests/fixtures/virtual_trading_inputs_v1.json).
   Thin fetch layer: daily history through the existing private history Worker session (same Google session, no new
   scope), the public price-free forward ledger and classification, the device's ACTUAL holdings and device V scores.
   Prices, FX rates, ledgers and results live only in memory: nothing here stores, logs or sends them. A missing close
   or rate stays absent (the engine then reports EXEC_PRICE_MISSING / EXEC_FX_MISSING); nothing is filled. */
(function(root,factory){const node=typeof module==='object'&&module.exports;const api=factory(node?()=>require('./virtual-trading.js'):()=>root.VirtualTrading);if(node)module.exports=api;else root.VirtualTradingRunner=api;})(typeof globalThis==='object'?globalThis:this,function(engine){
'use strict';
const SCHEMA='virtual-trading-inputs/1',RANGE='2y',FORWARD_VERSION='forward_validation/v1';
const IDS=['asml','lrcx','klac','tokyo_electron','hanmi','nvda','amd','avgo','qcom','intc','msft','googl','amzn','rtx','stry','etn','hubb','gev','rok'];
const TARGETS=Object.freeze({asml:'ASML',lrcx:'LRCX',klac:'KLAC',tokyo_electron:'8035.T',hanmi:'042700.KS',nvda:'NVDA',amd:'AMD',avgo:'AVGO',qcom:'QCOM',intc:'INTC',msft:'MSFT',googl:'GOOGL',amzn:'AMZN',rtx:'RTX',stry:'SYK',etn:'ETN',hubb:'HUBB',gev:'GEV',rok:'ROK'});
const SP500_SYMBOL='SPY',FX_SYMBOLS=Object.freeze({USD:'KRW=X',JPY:'JPYKRW=X'}),CURRENCIES=['USD','KRW','JPY'],STATUSES=['COMPLETE','IN_PROGRESS','UNKNOWN'];
const FLAG_KINDS=['HOLD','EXCLUDE','CONFIRMED_TEMPORARY','CONFIRMED_STRUCTURAL','CLEAR'],KINDS=['SET_A','SET_B','SHADOW'];
const MAX_BARS=1500,MAX_TIMESTAMP=4102444800;
const CODE=/^[A-Z][A-Z0-9_]{0,63}$/,DAY=/^\d{4}-\d{2}-\d{2}$/,CLOCK=/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$/,ZONE=/^[A-Za-z_]+(?:\/[A-Za-z0-9_+\-]+){0,2}$/;
// Device-only per-date V store (V scores only, never prices). Read here; no producer writes it yet.
const V_KEY='investment.web.v1.virtual-trading-v-scores',HISTORY_KEY='investment.web.v1.private-history-origin';
// Session-level failures: no further Worker request is made after one of these.
const STOP=new Set(['AUTH_REQUIRED','AUTH_FORBIDDEN','AUTH_UNAVAILABLE','ORIGIN_FORBIDDEN','CONFIG_UNAVAILABLE','CANCELED','RATE_LIMIT_UNAVAILABLE']);
const DEFAULT_SPACING_MS=5200,RATE_RETRY_MS=15000,RATE_RETRIES=2;
const own=(o,k)=>o!==null&&typeof o==='object'&&Object.prototype.hasOwnProperty.call(o,k);
const object=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
const num=v=>typeof v==='number'&&Number.isFinite(v);
function day(v){if(!(typeof v==='string'&&DAY.test(v)))return false;const m=+v.slice(5,7),d=+v.slice(8);return m>=1&&m<=12&&d>=1&&d<=31;}
function invalid(){throw new Error('INVALID');}
function need(ok){if(!ok)invalid();}
const formatters=new Map();
function formatter(tz){
 need(typeof tz==='string'&&ZONE.test(tz));
 if(!formatters.has(tz)){let f;try{f=new Intl.DateTimeFormat('en-CA',{timeZone:tz,year:'numeric',month:'2-digit',day:'2-digit'});}catch(_){invalid();}formatters.set(tz,f);}
 return formatters.get(tz);
}
function localDate(ms,tz){const p={};for(const x of formatter(tz).formatToParts(ms))p[x.type]=x.value;return p.year+'-'+p.month+'-'+p.day;}
function instant(text){need(typeof text==='string'&&CLOCK.test(text));const ms=Date.parse(text);need(Number.isFinite(ms));return ms;}
function easternDate(text){return localDate(instant(text),'America/New_York');}
function sortedObject(o){const r={};for(const k of Object.keys(o).sort())r[k]=o[k];return r;}

function catalogTargets(catalog){
 try{
  need(object(catalog)&&catalog.total_units===10000);const rows=catalog.instruments;need(Array.isArray(rows)&&rows.length===IDS.length);
  const out=[];
  IDS.forEach((cid,i)=>{const row=rows[i];need(object(row)&&row.row_index===i&&row.ticker===TARGETS[cid].split('.')[0]&&CURRENCIES.includes(row.currency));
   const units=row.target_units;need(Number.isInteger(units)&&units>=0&&units<=10000);out.push({cid,symbol:TARGETS[cid],currency:row.currency,weight:units/100});});
  let total=0;for(const r of out)total+=r.weight;need(total<=100+1e-9);
  return out;
 }catch(_){return null;}
}
function classificationRow(p,cid){try{const r=p.data.companies;return own(r,cid)?r[cid]:null;}catch(_){return null;}}
function sectorFor(classification,cid){
 const row=classificationRow(classification,cid);let sic=null,semis=null;
 if(object(row)){
  if(object(row.industry)&&typeof row.industry.sic==='string')sic=row.industry.sic;
  if(object(row.themes)&&object(row.themes.memberships)){const m=row.themes.memberships.semiconductors;if(object(m)&&(m.member===true||m.member===false))semis=m.member;}
 }
 return engine().sectorBenchmark(sic,semis);
}
const benchmarkKey=etf=>etf===SP500_SYMBOL?'SP500':etf;
function universe(targets,holdings,setB){
 const cids=targets.map(t=>t.cid);
 for(const extra of [object(holdings)&&object(holdings.positions)?holdings.positions:{},object(setB)&&object(setB.target_weights)?setB.target_weights:{}])
  for(const c of Object.keys(extra).filter(c=>own(TARGETS,c)&&!cids.includes(c)).sort())cids.push(c);
 return cids;
}
function requiredSymbols({catalog,classification=null,holdings=null,set_b=null}){
 const targets=catalogTargets(catalog);if(targets===null)return[];
 const currency={};for(const t of targets)currency[t.cid]=t.currency;
 const cids=universe(targets,holdings,set_b),used=new Set(cids.map(c=>currency[c]));
 const fx=['USD','JPY'].filter(c=>used.has(c)).map(c=>FX_SYMBOLS[c]);
 const etfs=[...new Set(cids.map(c=>sectorFor(classification,c).etf))].filter(e=>e!==SP500_SYMBOL).sort();
 return [SP500_SYMBOL,...fx,...cids.map(c=>TARGETS[c]),...etfs];
}
// Worker private-history/1 payload (or {error}) → [closes, null] or [{}, code]. Missing closes stay absent.
function seriesFromHistory(entry,symbol,currency){
 if(entry===null||entry===undefined)return[{},'NOT_REQUESTED'];
 if(object(entry)&&Object.keys(entry).length===1&&own(entry,'error'))return[{},typeof entry.error==='string'&&CODE.test(entry.error)?entry.error:'HISTORY_UNAVAILABLE'];
 const rows=[];let readDay;
 try{
  need(object(entry)&&entry.schema==='private-history/1'&&entry.symbol===symbol&&entry.interval==='1d');
  const tz=entry.timezone;formatter(tz);readDay=localDate(instant(entry.read_at),tz);
  const bars=entry.bars;need(Array.isArray(bars)&&bars.length<=MAX_BARS);let previous=0;
  for(const bar of bars){
   need(object(bar));const ts=bar.timestamp,status=bar.session_status,close=own(bar,'close')?bar.close:undefined;
   need(Number.isInteger(ts)&&previous<ts&&ts<=MAX_TIMESTAMP&&STATUSES.includes(status));
   need(close===null||close===undefined||num(close));previous=ts;
   const sd=own(bar,'session_date')?bar.session_date:null;need(sd===null||sd===undefined||day(sd));
   rows.push([sd||localDate(ts*1000,tz),status,close===undefined?null:close]);
  }
 }catch(_){return[{},'HISTORY_FORMAT_INVALID'];}
 if(entry.currency!==currency)return[{},'CURRENCY_MISMATCH'];
 const seen=new Map();for(const[d]of rows)seen.set(d,(seen.get(d)||0)+1);
 const closes={};
 for(const[d,status,close]of rows){
  if(seen.get(d)!==1||close===null||!(close>0))continue;
  if(status==='COMPLETE'||(status==='UNKNOWN'&&d<readDay))closes[d]=close;
 }
 if(!Object.keys(closes).length)return[{},'HISTORY_UNAVAILABLE'];
 return[sortedObject(closes),null];
}
function coverage(row){
 if(row.state==='NOT_AVAILABLE')return'BLOCKED';
 const axes=[row.Q.coverage,row.G.coverage];
 if(axes.includes('BLOCKED'))return'BLOCKED';
 if(row.state==='STALE'||axes.includes('PARTIAL'))return'PARTIAL';
 return'READY';
}
function snapshotsFromLedger(forward){
 const out={};let records;try{records=forward.versions[FORWARD_VERSION];}catch(_){return out;}
 for(const r of Array.isArray(records)?records:[]){
  if(!(object(r)&&r.state==='RECORDED'&&day(r.date)&&object(r.companies)))continue;
  const rows={};for(const cid of Object.keys(r.companies).sort()){const row=r.companies[cid];rows[cid]={q:row.Q.score,g:row.G.score,coverage:coverage(row)};}
  out[r.date]=rows;
 }
 return out;
}
function vScoresFromStore(store){
 const out={};if(!object(store))return out;
 for(const d of Object.keys(store).sort()){const row=store[d];if(!(day(d)&&object(row)))continue;
  const kept={};for(const cid of Object.keys(row).sort()){const v=row[cid];if(num(v)&&v>=0&&v<=100)kept[cid]=v;}
  if(Object.keys(kept).length)out[d]=kept;}
 return out;
}
function flagsFromStore(flags){return Array.isArray(flags)?flags.filter(f=>object(f)&&day(f.date)&&FLAG_KINDS.includes(f.kind)&&typeof f.company==='string').map(f=>({date:f.date,kind:f.kind,company:f.company})):[];}
function rateOnOrBefore(series,d){let best=null;for(const k of Object.keys(series))if(k<=d&&(best===null||k>best))best=k;return best===null?null:series[best];}
const unavailable=codes=>({state:'NOT_AVAILABLE',reason_codes:[...codes],input:null});

/* Pure assembly: same inputs → same ledger inputs as the Python reference. */
function assemble({config,catalog,forward_ledger=null,classification=null,histories={},holdings=null,set_b=null,v_store=null,flags=null}){
 histories=histories||{};const start=config&&config.start_date!==undefined?config.start_date:null;
 const out={schema:SCHEMA,state:'READY',reason_codes:[],sources:{},sector:{},ledgers:{}};
 const targets=catalogTargets(catalog);
 if(targets===null){out.state='NOT_AVAILABLE';out.reason_codes=['TARGET_CATALOG_INVALID'];for(const k of KINDS)out.ledgers[k]=unavailable(['TARGET_CATALOG_INVALID']);return out;}
 const listing={};for(const t of targets)listing[t.cid]=t.currency;
 const cids=universe(targets,holdings,set_b),series={},sector={};
 const source=(symbol,currency)=>{
  const[closes,code]=seriesFromHistory(own(histories,symbol)?histories[symbol]:null,symbol,currency);
  out.sources[symbol]={state:code===null?'OK':code==='NOT_REQUESTED'?'NOT_REQUESTED':'NOT_AVAILABLE',code,sessions:Object.keys(closes).length};
  if(code===null)series[symbol]=closes;
  return code===null?closes:null;
 };
 const spy=source(SP500_SYMBOL,'USD'),fx={},used=new Set(cids.map(c=>listing[c]));
 for(const ccy of ['USD','JPY'])if(used.has(ccy)){const rates=source(FX_SYMBOLS[ccy],'KRW');if(rates!==null)fx[ccy]=rates;}
 for(const cid of cids){source(TARGETS[cid],listing[cid]);sector[cid]=sectorFor(classification,cid);}
 for(const etf of [...new Set(Object.values(sector).map(s=>s.etf))].filter(e=>e!==SP500_SYMBOL).sort())source(etf,'USD');
 out.sector=sector;
 if(spy===null){out.state='NOT_AVAILABLE';out.reason_codes=['SESSIONS_NOT_AVAILABLE'];for(const k of KINDS)out.ledgers[k]=unavailable(['SESSIONS_NOT_AVAILABLE']);return out;}
 const sessions=Object.keys(spy).filter(d=>start!==null&&d>=start);
 const snapshots=snapshotsFromLedger(forward_ledger),vScores=vScoresFromStore(v_store),flagRows=flagsFromStore(flags);
 const ledger=(id,kind,members,weights,ledgerSessions,initial)=>{
  const companies={},bench={SP500:spy};
  for(const cid of [...members].sort()){const etf=sector[cid].etf,key=benchmarkKey(etf);
   companies[cid]={currency:listing[cid],closes:own(series,TARGETS[cid])?series[TARGETS[cid]]:{},sector_benchmark:key};
   if(key!=='SP500'&&own(series,etf))bench[key]=series[etf];}
  return{state:'READY',reason_codes:[],input:{id,kind,sessions:ledgerSessions,target_weights:weights,companies,benchmarks:bench,fx:{...fx},initial,snapshots,v_scores:vScores,flags:flagRows,events:{}}};
 };
 const targetWeights={};for(const t of targets)targetWeights[t.cid]=t.weight;
 out.ledgers.SET_A=ledger('set_a','SET_A',Object.keys(targetWeights),targetWeights,sessions,{cash:0,positions:{}});
 const wb=object(set_b)&&own(set_b,'target_weights')?set_b.target_weights:null;
 if(wb===null||wb===undefined)out.ledgers.SET_B=unavailable(['SET_B_NOT_DEFINED']);
 else{let total=0;const ok=object(wb)&&Object.keys(wb).length>0&&Object.entries(wb).every(([c,v])=>own(TARGETS,c)&&own(listing,c)&&num(v)&&v>=0&&v<=100);
  if(ok)for(const k of Object.keys(wb).sort())total+=wb[k];
  out.ledgers.SET_B=ok&&total<=100+1e-9?ledger('set_b','SET_B',Object.keys(wb),{...wb},sessions,{cash:0,positions:{}}):unavailable(['SET_B_INVALID']);}
 out.ledgers.SHADOW=shadow(holdings,targetWeights,sessions,fx,ledger);
 return out;
}
function shadow(holdings,targetWeights,sessions,fx,ledger){
 const positions=object(holdings)&&object(holdings.positions)?holdings.positions:{},held={};
 for(const cid of Object.keys(positions).sort()){const p=positions[cid];if(own(targetWeights,cid)&&object(p)&&num(p.quantity)&&p.quantity>0)held[cid]=p;}
 if(!Object.keys(held).length)return unavailable(['NO_ACTUAL']);
 if(Object.values(held).some(p=>!(num(p.average_cost)&&p.average_cost>=0&&CURRENCIES.includes(p.currency))))return unavailable(['ACTUAL_INVALID']);
 let begin;try{begin=easternDate(holdings.effective_at);}catch(_){return unavailable(['ACTUAL_INVALID']);}
 const mine=sessions.filter(d=>d>=begin),initial={cash:0,positions:{}};
 if(mine.length){for(const cid of Object.keys(held)){const p=held[cid],rate=p.currency==='KRW'?1:rateOnOrBefore(own(fx,p.currency)?fx[p.currency]:{},mine[0]);
  if(rate===null)return unavailable(['INITIAL_COST_FX_MISSING']);initial.positions[cid]={quantity:p.quantity,cost:p.quantity*p.average_cost*rate};}}
 return ledger('shadow-'+begin,'SHADOW',Object.keys(targetWeights),{...targetWeights},mine,initial);
}

/* Device ACTUAL snapshot (DeviceActual.readHoldings) → {effective_at, positions:{cid:{quantity, average_cost, currency}}}. */
function canonical(v){if(Array.isArray(v))return'['+v.map(canonical).join(',')+']';if(object(v))return'{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canonical(v[k])).join(',')+'}';return JSON.stringify(v);}
function holdingsFromSnapshot(snapshot,catalog){
 if(!object(snapshot)||!Array.isArray(snapshot.themes)||!object(catalog)||!Array.isArray(catalog.instruments))return null;
 const byRef=new Map();for(const row of catalog.instruments)if(object(row)&&Number.isInteger(row.row_index)&&row.row_index>=0&&row.row_index<IDS.length)byRef.set(canonical(row.security_reference),IDS[row.row_index]);
 const positions={};
 for(const theme of snapshot.themes)for(const h of (object(theme)&&Array.isArray(theme.holdings)?theme.holdings:[])){
  const cid=byRef.get(canonical(h.security_reference)),quantity=Number(h.quantity),average=Number(h.average_cost);
  if(!cid||!num(quantity)||!(quantity>0))continue;positions[cid]={quantity,average_cost:num(average)?average:null,currency:h.currency};
 }
 return{effective_at:snapshot.effective_at,positions:sortedObject(positions)};
}
function readVStore(storage){try{const raw=storage.getItem(V_KEY);if(!raw)return{};const v=JSON.parse(raw);return object(v)&&v.schema==='virtual-trading-v-scores/1'&&object(v.scores)?v.scores:{};}catch(_){return{};}}

/* Engine run for one report tab. Not READY → a ledger-shaped NOT_STARTED/NOT_AVAILABLE result with the reasons. */
function ledgerFor(result,kind,cfg){
 const VT=engine(),stop=(state,codes)=>({ledger_id:null,config_version:cfg.config_version??null,rules_version:cfg.rules_version,status:cfg.status??null,role:'RAM_ONLY_DEVICE',state,reason_codes:codes,days:[],trades:[],summary:null});
 if(!result||result.state==='NOT_STARTED')return{ledger:stop('NOT_STARTED',result?result.reason_codes:['BEFORE_START_DATE']),hits:null,input:null};
 if(result.state!=='READY')return{ledger:stop('NOT_AVAILABLE',result.reason_codes),hits:null,input:null};
 const entry=result.ledgers[kind];if(!entry||entry.state!=='READY')return{ledger:stop('NOT_AVAILABLE',entry?entry.reason_codes:['LEDGER_NOT_AVAILABLE']),hits:null,input:null};
 const ledger=VT.runLedger(cfg,entry.input);
 return{ledger,hits:ledger.state==='OK'?VT.evaluateHits(cfg,entry.input,ledger.trades):null,input:entry.input};
}
// Screen status rows: symbol, state and code only (no prices).
function statusRows(result){return result&&object(result.sources)?Object.keys(result.sources).map(symbol=>({symbol,state:result.sources[symbol].state,code:result.sources[symbol].code})):[];}

/* ---------- thin fetch layer (browser) ---------- */
const cache={revision:null,histories:new Map()};
function clearCache(){cache.revision=null;cache.histories.clear();}
function storedOrigin(view){try{const v=view.localStorage.getItem(HISTORY_KEY);return v&&view.PrivateHistory?view.PrivateHistory.parseWorkerOrigin(v):'';}catch(_){return null;}}
function readiness(view,config,session){
 if(config.privateHistoryEnabled!==true||!view.PrivateHistory)return'OFF';
 const origin=storedOrigin(view);if(origin===null)return'REQUEST_INVALID';if(!origin||origin!==config.privateHistoryWorkerOrigin)return'ORIGIN_UNAPPROVED';
 if(!session||!session.state().connected)return'AUTH_REQUIRED';return'READY';
}
function spacing(config){const v=config&&config.virtualTradingRequestSpacingMs;return Number.isInteger(v)&&v>=0&&v<=60000?v:DEFAULT_SPACING_MS;}
const pause=(view,ms,signal)=>new Promise((resolve,reject)=>{if(ms<=0){resolve();return;}const t=view.setTimeout(resolve,ms);if(signal)signal.addEventListener('abort',()=>{view.clearTimeout(t);reject(new Error('CANCELED'));},{once:true});});
async function fetchHistories(view,{session,origin,symbols,spacingMs=DEFAULT_SPACING_MS,signal=null,onProgress=null}){
 const revision=session.revision();if(cache.revision!==revision){cache.histories.clear();cache.revision=revision;}
 const out={};let stop=null,lastNetwork=false,done=0;
 const tick=()=>{done++;if(onProgress)try{onProgress(done,symbols.length);}catch(_){}};
 for(const symbol of symbols){
  if(signal&&signal.aborted)stop=stop||'CANCELED';
  if(cache.histories.has(symbol)){out[symbol]=cache.histories.get(symbol);tick();continue;}
  if(stop){out[symbol]={error:stop};tick();continue;}
  let code=null;
  for(let attempt=0;;attempt++){
   try{
    if(lastNetwork)await pause(view,attempt?RATE_RETRY_MS:spacingMs,signal);
    lastNetwork=true;
    const payload=await session.fetchHistory(origin,symbol,RANGE,{approvedOrigin:origin,signal:signal||undefined});
    if(session.revision()!==revision)throw new Error('CANCELED');
    cache.histories.set(symbol,payload);out[symbol]=payload;code=null;break;
   }catch(e){
    code=e&&typeof e.message==='string'&&CODE.test(e.message)?e.message:'HISTORY_UNAVAILABLE';
    if(code==='REQUEST_INVALID')lastNetwork=false;
    if(code==='RATE_LIMITED'&&attempt<RATE_RETRIES)continue;
    break;
   }
  }
  if(code!==null){out[symbol]={error:code};if(STOP.has(code))stop=code;}
  tick();
  // Without SPY there are no sessions: do not spend Worker requests on the rest.
  if(symbol===SP500_SYMBOL&&code!==null)break;
 }
 return out;
}
/* Everything for one report: NOT_STARTED before the start date (no request at all), else readiness, public JSON,
   device holdings and V store, Worker history (sequential, spaced), then the pure assembly. */
async function run(view,{config={},catalog,reportDate,signal=null,onProgress=null}={}){
 const VT=engine(),cfg=VT.defaultConfig();
 const base={schema:SCHEMA,sources:{},sector:{},ledgers:{}};
 if(!(typeof reportDate==='string'&&day(reportDate))||reportDate<cfg.start_date)return{...base,state:'NOT_STARTED',reason_codes:['BEFORE_START_DATE']};
 let session=null;try{session=config.googleSheetsClientId&&view.GoogleSheetQuotes?view.GoogleSheetQuotes.sessionFor(view,config.googleSheetsClientId):null;}catch(_){session=null;}
 const ready=readiness(view,config,session);if(ready!=='READY')return{...base,state:'NOT_AVAILABLE',reason_codes:[ready]};
 const forward=view.ForwardValidation?await view.ForwardValidation.load(view):{state:'NOT_AVAILABLE',reason:'LEDGER_UNREACHABLE'};
 if(forward.state!=='LOADED')return{...base,state:'NOT_AVAILABLE',reason_codes:[forward.reason]};
 const classification=view.ClassificationScreens?await view.ClassificationScreens.load(view):null;
 let holdings=null;try{holdings=holdingsFromSnapshot(await view.DeviceActual.readHoldings(view,catalog),catalog);}catch(_){holdings=null;}
 const symbols=requiredSymbols({catalog,classification,holdings});
 const histories=await fetchHistories(view,{session,origin:config.privateHistoryWorkerOrigin,symbols,spacingMs:spacing(config),signal,onProgress});
 return assemble({config:cfg,catalog,forward_ledger:forward.ledger,classification,histories,holdings,set_b:null,v_store:readVStore(view.localStorage),flags:[]});
}
return Object.freeze({SCHEMA,IDS,TARGETS,SP500_SYMBOL,FX_SYMBOLS,V_KEY,RANGE,catalogTargets,sectorFor,requiredSymbols,seriesFromHistory,coverage,snapshotsFromLedger,
 vScoresFromStore,flagsFromStore,assemble,holdingsFromSnapshot,readVStore,ledgerFor,statusRows,readiness,fetchHistories,run,clearCache});
});
