/* Virtual ledger sheet storage v1 (D-10): the virtual ledgers (Set A, Set B, shadow) written to the user's own Google
   Sheet tabs VirtualA / VirtualB / VirtualMine / VirtualMeta / VirtualFlags, append-only, only on the user's click.
   Pure part mirrors qgv/virtual_ledger_sheets.py (vectors: tests/fixtures/virtual_ledger_sheets_v1.json): row format,
   replay verification of recorded rows (LEDGER_REPLAY_MISMATCH → no writes) and the missing-session plan.
   The sheet is the user's private storage, so its cells hold real numbers; this screen shows only dates, counts, codes
   and weights. Nothing here logs, stores on the device or publishes prices, ledgers, holdings or the sheet id.
   Virtual records only · not a recommendation · no order function. */
(function(root,factory){const node=typeof module==='object'&&module.exports;const api=factory(node?()=>require('./virtual-trading.js'):()=>root.VirtualTrading,node?()=>require('./virtual-trading-runner.js'):()=>root.VirtualTradingRunner);if(node)module.exports=api;else root.VirtualLedgerSheets=api;})(typeof globalThis==='object'?globalThis:this,function(engine,runner){
'use strict';
const SCHEMA='virtual-ledger-sheets/1';
const TABS=Object.freeze({SET_A:'VirtualA',SET_B:'VirtualB',SHADOW:'VirtualMine'}),META='VirtualMeta',FLAGS='VirtualFlags';
const LEDGER_HEAD=Object.freeze(['ledger_id','session_date','row_type','company','level','aux_levels','reason_codes','aux_codes','side','amount','quantity','price_used','fx_used','cash_after','total_value']);
const META_HEAD=Object.freeze(['recorded_at','ledger_id','kind','event','start_date','end_date','config_version','engine_version','last_recorded_session','inputs_sha256','payload']);
const FLAGS_HEAD=Object.freeze(['created_at','date','company','kind']);
const HEADS=Object.freeze({VirtualA:LEDGER_HEAD,VirtualB:LEDGER_HEAD,VirtualMine:LEDGER_HEAD,VirtualMeta:META_HEAD,VirtualFlags:FLAGS_HEAD});
const ALL_TABS=Object.freeze(['VirtualA','VirtualB','VirtualMine','VirtualMeta','VirtualFlags']);
const ROW_TYPES=['INITIAL','EXECUTED','CANCELLED','JUDGEMENT','ORDER','SUMMARY'],KINDS=['SET_A','SET_B','SHADOW'],BASES=['TARGET_V0','SET_B','USER_TARGET'];
const PREFIX={SET_A:'set_a',SET_B:'set_b-',SHADOW:'shadow-'},CURRENCIES=['USD','KRW','JPY'];
const FLAG_KINDS=['HOLD','EXCLUDE','CONFIRMED_TEMPORARY','CONFIRMED_STRUCTURAL','CLEAR'];
const NA='NOT_AVAILABLE',ID=/^(?:set_a|set_b-[1-9][0-9]{0,5}|shadow-[1-9][0-9]{0,5})$/,WEIGHT_TEXT=/^(?:0|[1-9][0-9]{0,2})(?:\.[0-9]{1,4})?$/,SHA=/^[0-9a-f]{64}$/;
const DAY=/^\d{4}-\d{2}-\d{2}$/,CLOCK=/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$/;
const own=(o,k)=>o!==null&&typeof o==='object'&&Object.prototype.hasOwnProperty.call(o,k);
const object=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
const num=v=>typeof v==='number'&&Number.isFinite(v);
function day(v){if(!(typeof v==='string'&&DAY.test(v)))return false;const m=+v.slice(5,7),d=+v.slice(8);return m>=1&&m<=12&&d>=1&&d<=31;}
function fail(code){throw new Error(code);}
const targets=()=>runner().TARGETS;

/* ---------- text form ---------- */
// ECMAScript Number-to-String (the Python reference reproduces it exactly).
function numStr(x){if(!num(x))fail('NUMBER_INVALID');return String(x);}
function canonical(v){
 if(v===null)return'null';if(v===true)return'true';if(v===false)return'false';
 if(typeof v==='number')return numStr(v);if(typeof v==='string')return JSON.stringify(v);
 if(Array.isArray(v))return'['+v.map(canonical).join(',')+']';
 if(object(v))return'{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canonical(v[k])).join(',')+'}';
 fail('VALUE_INVALID');
}
const codes=list=>(list||[]).join(',');

/* ---------- ledger rows (one engine day → rows) ---------- */
function dayRows(id,d,initial=null){
 const rows=[],pos=initial&&object(initial.positions)?initial.positions:{};
 for(const cid of Object.keys(pos).sort())rows.push([id,d.date,'INITIAL',cid,'','','','','',numStr(pos[cid].cost),numStr(pos[cid].quantity),'','','','']);
 for(const t of d.executed)rows.push([id,d.date,'EXECUTED',t.company,'','',codes(t.reason_codes),t.user_flag||'',t.side,numStr(t.amount),numStr(t.quantity),numStr(t.price),numStr(t.fx),'','']);
 for(const o of d.cancelled)rows.push([id,d.date,'CANCELLED',o.company,'','',o.cancel_reason,codes(o.reason_codes),o.side,numStr(o.amount),'','','','','']);
 for(const cid of Object.keys(d.judgements).sort()){const j=d.judgements[cid];rows.push([id,d.date,'JUDGEMENT',cid,j.main,codes(j.aux_levels),codes(j.reason_codes),codes(j.aux),'','','','','','','']);}
 for(const o of d.orders)rows.push([id,d.date,'ORDER',o.company,'','',codes(o.reason_codes),'',o.side,numStr(o.amount),'','','','','']);
 const total=d.total_value;
 rows.push([id,d.date,'SUMMARY',codes(d.stale_valuation),'','',total===null?'VALUATION_NOT_AVAILABLE':'','','',numStr(d.deposit),'','','',numStr(d.cash),total===null?NA:numStr(total)]);
 return rows;
}
function ledgerRows(id,result,input,dates){
 const wanted=new Set(dates),out=[];
 result.days.forEach((d,i)=>{if(wanted.has(d.date))out.push(...dayRows(id,d,i===0?input.initial:null));});
 return out;
}

/* ---------- reading tabs ---------- */
function parseTab(values,head){
 if(!Array.isArray(values))fail('SHEET_ROWS_INVALID');
 if(!values.length)return{header:false,rows:[]};
 const first=values[0];if(!Array.isArray(first)||first.length!==head.length||first.some((c,i)=>c!==head[i]))fail('SHEET_HEADER_MISMATCH');
 const rows=[];
 for(const raw of values.slice(1)){
  if(!Array.isArray(raw)||!raw.length||raw.length>head.length||raw.some(c=>typeof c!=='string'))fail('SHEET_ROWS_INVALID');
  rows.push([...raw,...Array(head.length-raw.length).fill('')]);
 }
 return{header:true,rows};
}
function groupLedgerRows(rows){
 const out={};
 for(const r of rows){
  if(!ID.test(r[0])||!day(r[1])||!ROW_TYPES.includes(r[2]))fail('SHEET_ROWS_INVALID');
  const prev=own(out,r[0])?out[r[0]]:null;if(prev&&prev[prev.length-1][1]>r[1])fail('SHEET_ROWS_INVALID');
  (out[r[0]]=out[r[0]]||[]).push(r);
 }
 return out;
}
function recordedDates(rows){const out=[];for(const r of rows)if(!out.length||out[out.length-1]!==r[1])out.push(r[1]);return out;}
function weightsOk(w){
 if(!object(w)||!Object.keys(w).length)return false;
 for(const[k,v]of Object.entries(w))if(!(own(targets(),k)&&num(v)&&v>=0&&v<=100))return false;
 let total=0;for(const k of Object.keys(w).sort())total+=w[k];return total<=100+1e-9;
}
function snapshotOk(s){return object(s)&&typeof s.effective_at==='string'&&object(s.positions)&&Object.entries(s.positions).every(([k,p])=>own(targets(),k)&&object(p));}
function parseMeta(rows){
 const ledgers=new Map(),records={};let target=null;
 for(let i=0;i<rows.length;i++){
  const ev={};META_HEAD.forEach((k,j)=>{ev[k]=rows[i][j];});
  const bad={state:'META_INVALID',reason_codes:['META_ROW_INVALID'],row:i};
  let payload;try{payload=ev.payload?JSON.parse(ev.payload):{};}catch(_){return bad;}
  let ok=object(payload);const event=ev.event,lid=ev.ledger_id,kind=ev.kind;
  if(ok&&event==='LEDGER_START'){
   const basis=payload.target_basis,weights=payload.target_weights;
   ok=ID.test(lid)&&!ledgers.has(lid)&&KINDS.includes(kind)&&lid.startsWith(PREFIX[kind])&&day(ev.start_date)&&ev.end_date===''&&BASES.includes(basis)&&weightsOk(weights)&&(kind!=='SHADOW'||snapshotOk(payload.snapshot));
   if(ok)ledgers.set(lid,{id:lid,kind,begin:ev.start_date,end:null,target_basis:basis,target_weights:weights,snapshot:kind==='SHADOW'?payload.snapshot:null,
    config_version:ev.config_version,engine_version:ev.engine_version,reason:typeof payload.reason==='string'?payload.reason:null});
  }else if(ok&&event==='LEDGER_CLOSE'){
   const led=ledgers.get(lid);ok=!!led&&led.kind===kind&&led.end===null&&day(ev.end_date)&&ev.end_date>=led.begin;
   if(ok)led.end=ev.end_date;
  }else if(ok&&event==='RECORD'){
   ok=ledgers.has(lid)&&ledgers.get(lid).kind===kind&&day(ev.last_recorded_session)&&SHA.test(ev.inputs_sha256);
   if(ok)records[lid]={session:ev.last_recorded_session,sha256:ev.inputs_sha256};
  }else if(ok&&event==='USER_TARGET'){
   const w=own(payload,'target_weights')?payload.target_weights:null;ok=lid===''&&kind==='TARGET'&&(w===null||weightsOk(w));
   if(ok)target=w;
  }else ok=false;
  if(!ok)return bad;
 }
 return{state:'OK',reason_codes:[],ledgers:[...ledgers.values()],records,user_target:target};
}
function active(meta,kind){let found=null;for(const led of meta.ledgers)if(led.kind===kind&&led.end===null)found=led;return found;}
function setALedger(meta,base,config){
 for(const led of meta.ledgers)if(led.id==='set_a')return led;
 return{id:'set_a',kind:'SET_A',begin:config.start_date,end:null,target_basis:'TARGET_V0',target_weights:{...base.target_weights},snapshot:null,implicit:true,
  config_version:config.config_version??null,engine_version:config.rules_version,reason:null};
}
function nextId(meta,kind){return PREFIX[kind]+(1+meta.ledgers.filter(l=>l.kind===kind).length);}

/* ---------- weights / flags input ---------- */
function validateWeights(raw,allowed){
 const invalid=code=>({state:'INVALID',reason_codes:[code],weights:null});
 if(!object(raw))return invalid('WEIGHT_INVALID');
 const allow=new Set(allowed),out={};
 for(const cid of Object.keys(raw).sort()){
  let v=raw[cid];
  if(v===null||v===undefined||(typeof v==='string'&&v.trim()===''))continue;
  if(!allow.has(cid))return invalid('COMPANY_NOT_SUPPORTED');
  if(typeof v==='string'){if(!WEIGHT_TEXT.test(v.trim()))return invalid('WEIGHT_INVALID');v=Number(v.trim());}
  else if(!num(v))return invalid('WEIGHT_INVALID');
  if(!(v>=0&&v<=100))return invalid('WEIGHT_INVALID');
  if(v>0)out[cid]=v;
 }
 if(!Object.keys(out).length)return{state:NA,reason_codes:['WEIGHTS_EMPTY'],weights:null};
 let total=0;for(const k of Object.keys(out).sort())total+=out[k];
 if(total>100+1e-9)return invalid('WEIGHT_SUM_OVER_100');
 return{state:'OK',reason_codes:[],weights:out};
}
function flagDate(v){
 if(typeof v==='string'&&day(v.trim()))return v.trim();
 if(num(v)&&v>=1&&v<2958466&&Number.isInteger(v))return new Date(Date.UTC(1899,11,30)+v*86400000).toISOString().slice(0,10);
 return null;
}
function parseFlags(values){
 if(!Array.isArray(values)||!values.length)return{flags:[],ignored:0};
 const first=values[0];if(!Array.isArray(first)||first.length!==FLAGS_HEAD.length||first.some((c,i)=>c!==FLAGS_HEAD[i]))fail('SHEET_HEADER_MISMATCH');
 const byTicker={};for(const[cid,t]of Object.entries(targets()))byTicker[t]=cid;
 const flags=[];let ignored=0;
 for(const raw of values.slice(1)){
  if(!Array.isArray(raw))continue;const row=[...raw,...Array(Math.max(0,4-raw.length)).fill('')];
  if(!row.some(c=>c!==''&&c!==null))continue;
  const d=flagDate(row[1]),company=typeof row[2]==='string'?row[2].trim():'',cid=own(targets(),company)?company:(own(byTicker,company.toUpperCase())?byTicker[company.toUpperCase()]:null);
  const kind=typeof row[3]==='string'?row[3].trim().toUpperCase():'';
  if(d===null||cid===null||!FLAG_KINDS.includes(kind)){ignored++;continue;}
  flags.push({date:d,company:cid,kind});
 }
 return{flags,ignored};
}

/* ---------- ledger inputs ---------- */
function recordableThrough(base){
 if(!base||!base.sessions.length)return null;
 const last=base.sessions[base.sessions.length-1],days=Object.keys(base.snapshots||{}).filter(d=>d<=last).sort();
 return days.length?days[days.length-1]:null;
}
function rateOnOrBefore(series,d){let best=null;for(const k of Object.keys(series))if(k<=d&&(best===null||k>best))best=k;return best===null?null:series[best];}
function deriveInput(base,ledger){
 const sessions=base.sessions.filter(d=>d>=ledger.begin&&(ledger.end===null||d<ledger.end)),initial={cash:0,positions:{}};
 if(ledger.kind==='SHADOW'){
  const positions=object(ledger.snapshot)&&object(ledger.snapshot.positions)?ledger.snapshot.positions:{},held={};
  for(const cid of Object.keys(positions).sort()){const p=positions[cid];if(own(base.companies,cid)&&object(p)&&num(p.quantity)&&p.quantity>0)held[cid]=p;}
  if(!Object.keys(held).length)return{state:NA,reason_codes:['NO_ACTUAL'],input:null};
  if(Object.values(held).some(p=>!(num(p.average_cost)&&p.average_cost>=0&&CURRENCIES.includes(p.currency))))return{state:NA,reason_codes:['ACTUAL_INVALID'],input:null};
  if(sessions.length)for(const cid of Object.keys(held)){const p=held[cid],rate=p.currency==='KRW'?1:rateOnOrBefore(own(base.fx,p.currency)?base.fx[p.currency]:{},sessions[0]);
   if(rate===null)return{state:NA,reason_codes:['INITIAL_COST_FX_MISSING'],input:null};initial.positions[cid]={quantity:p.quantity,cost:p.quantity*p.average_cost*rate};}
 }
 return{state:'READY',reason_codes:[],input:{...base,id:ledger.id,kind:ledger.kind,sessions,target_weights:{...ledger.target_weights},initial}};
}
function truncate(L,last){
 const cut=s=>{const r={};for(const k of Object.keys(s))if(k<=last)r[k]=s[k];return r;},map=(o,f)=>{const r={};for(const k of Object.keys(o||{}))r[k]=f(o[k]);return r;};
 return{id:L.id,kind:L.kind,sessions:L.sessions.filter(d=>d<=last),target_weights:L.target_weights,initial:own(L,'initial')?L.initial:{cash:0,positions:{}},
  companies:map(L.companies,c=>({currency:c.currency,sector_benchmark:c.sector_benchmark??null,closes:cut(c.closes)})),
  benchmarks:map(L.benchmarks,cut),fx:map(L.fx,cut),snapshots:cut(L.snapshots||{}),v_scores:cut(L.v_scores||{}),
  flags:(L.flags||[]).filter(f=>f.date<=last),events:cut(L.events||{})};
}
const inputsText=(L,last)=>canonical(truncate(L,last));

/* ---------- replay verification + missing sessions ---------- */
const sameRow=(a,b)=>a.length===b.length&&a.every((c,i)=>c===b[i]);
function ledgerStatus(ledger,base,recorded,config,through){
 const out={id:ledger.id,kind:ledger.kind,tab:TABS[ledger.kind],begin:ledger.begin,end:ledger.end,target_basis:ledger.target_basis,state:'OK',reason_codes:[],
  recorded_sessions:0,recorded_through:null,missing:[],first_mismatch:null,append_rows:[],replay_through:null};
 const dates=recordedDates(recorded);out.recorded_sessions=dates.length;out.recorded_through=dates.length?dates[dates.length-1]:null;
 const derived=deriveInput(base,ledger);
 if(derived.state!=='READY'){out.state=dates.length?'LEDGER_REPLAY_MISMATCH':NA;out.reason_codes=[...derived.reason_codes];if(dates.length)out.first_mismatch={session:dates[0],row:0};return{status:out,input:null};}
 const input=derived.input,result=engine().runLedger(config,input),replay=result.state==='OK'?result.days.map(d=>d.date):[];
 out.replay_through=replay.length?replay[replay.length-1]:null;
 if(result.state!=='OK'){
  if(dates.length){out.state='LEDGER_REPLAY_MISMATCH';out.reason_codes=[...result.reason_codes];out.first_mismatch={session:dates[0],row:0};}
  else{out.state=result.state;out.reason_codes=[...result.reason_codes];}
  return{status:out,input};
 }
 const expected=ledgerRows(ledger.id,result,input,dates);
 const prefix=dates.every((d,i)=>replay[i]===d);
 if(!prefix||expected.length!==recorded.length||!expected.every((r,i)=>sameRow(r,recorded[i]))){
  let i=0;while(i<recorded.length&&i<expected.length&&sameRow(recorded[i],expected[i]))i++;
  const session=i<recorded.length?recorded[i][1]:(i<expected.length?expected[i][1]:dates[dates.length-1]);
  out.state='LEDGER_REPLAY_MISMATCH';out.reason_codes=['LEDGER_REPLAY_MISMATCH'];out.first_mismatch={session,row:i};return{status:out,input};
 }
 const missing=replay.slice(dates.length).filter(d=>through!==null&&d<=through);
 out.missing=missing;out.append_rows=ledgerRows(ledger.id,result,input,missing);
 if(!missing.length&&replay.length>dates.length)out.reason_codes=['WAITING_FOR_QG_RECORD'];
 return{status:out,input};
}

/* ---------- VirtualMeta rows ---------- */
function startRow(now,ledger,config,payload){return[now,ledger.id,ledger.kind,'LEDGER_START',ledger.begin,'',config.config_version||'',config.rules_version,'','',canonical(payload)];}
function closeRow(now,ledger,end,payload){return[now,ledger.id,ledger.kind,'LEDGER_CLOSE','',end,'','','','',canonical(payload)];}
function recordRow(now,status,config,sha256,rows){return[now,status.id,status.kind,'RECORD','','',config.config_version||'',config.rules_version,status.missing[status.missing.length-1],sha256,canonical({rows,sessions:status.missing.length})];}
function targetRow(now,weights){return[now,'','TARGET','USER_TARGET','','','','','','',canonical({target_weights:weights})];}
let nyFormat=null;
function easternDate(text){
 if(!(typeof text==='string'&&CLOCK.test(text)))fail('INVALID');const ms=Date.parse(text);if(!Number.isFinite(ms))fail('INVALID');
 nyFormat=nyFormat||new Intl.DateTimeFormat('en-CA',{timeZone:'America/New_York',year:'numeric',month:'2-digit',day:'2-digit'});
 const p={};for(const x of nyFormat.formatToParts(ms))p[x.type]=x.value;return p.year+'-'+p.month+'-'+p.day;
}
function nextDay(d){return new Date(Date.parse(d+'T00:00:00Z')+86400000).toISOString().slice(0,10);}
function beginFor(now,config,previousLast=null){
 let begin=easternDate(now);
 if(config.start_date&&begin<config.start_date)begin=config.start_date;
 if(previousLast&&begin<=previousLast)begin=nextDay(previousLast);
 return begin;
}
function replaceRows(meta,kind,now,config,payload,recordedLast=null,reason='INITIAL'){
 const old=active(meta,kind),begin=beginFor(now,config,old?recordedLast:null),fresh={id:nextId(meta,kind),kind,begin},rows=[];
 if(old)rows.push(closeRow(now,old,begin,{next:fresh.id,reason}));
 const body={...payload,reason};if(old)body.previous=old.id;
 rows.push(startRow(now,fresh,config,body));
 return rows;
}
const nowIso=(ms=Date.now())=>new Date(ms).toISOString().replace(/\.\d{3}Z$/,'Z');

/* ---------- sheet state (pure on loaded values) ---------- */
// values: {tab: values|undefined (tab absent)} → parsed sheet state. Any error blocks writes.
function sheetState(values){
 const tabs={};for(const t of ALL_TABS)tabs[t]=Array.isArray(values[t]);
 const out={state:'READY',reason_codes:[],tab:null,tabs,headerless:[],meta:{state:'OK',reason_codes:[],ledgers:[],records:{},user_target:null},rows:{},flags:[],ignored_flags:0};
 const stop=(code,tab)=>({...out,state:'ERROR',reason_codes:[code],tab});
 const parsed={};
 for(const t of [META,...Object.values(TABS)]){if(!tabs[t])continue;try{parsed[t]=parseTab(values[t],HEADS[t]);}catch(e){return stop(e.message,t);}if(!parsed[t].header)out.headerless.push(t);}
 if(tabs[FLAGS]){try{const f=parseFlags(values[FLAGS]);out.flags=f.flags;out.ignored_flags=f.ignored;if(!values[FLAGS].length)out.headerless.push(FLAGS);}catch(e){return stop(e.message,FLAGS);}}
 if(parsed[META]){const m=parseMeta(parsed[META].rows);if(m.state!=='OK')return{...stop('META_INVALID',META),meta_row:m.row};out.meta=m;}
 const known=new Map(out.meta.ledgers.map(l=>[l.id,l.kind]));
 for(const[kind,t]of Object.entries(TABS)){
  if(!parsed[t])continue;let groups;try{groups=groupLedgerRows(parsed[t].rows);}catch(e){return stop(e.message,t);}
  for(const id of Object.keys(groups)){if(known.get(id)!==kind)return stop('LEDGER_UNKNOWN',t);out.rows[id]=groups[id];}
 }
 return out;
}
// The assembled Set A input with the flags as they are in the sheet now (VirtualFlags), for every ledger.
function sheetBase(result,sheet){return{...result.ledgers.SET_A.input,flags:runner().flagsFromStore(sheet.flags)};}
// Symbols whose history failed for a reason that may pass (rate limit, network, sign-in): recording waits for them so a
// transient gap is not written as a permanent NOT_AVAILABLE. A rejected symbol (REQUEST_INVALID) is a lasting state.
const LASTING=new Set(['REQUEST_INVALID','NOT_REQUESTED']);
function inputsIncomplete(result){const src=result&&object(result.sources)?result.sources:{};return Object.keys(src).filter(k=>src[k].state!=='OK'&&!LASTING.has(src[k].code)).sort();}
// All ledgers (Set A implicit until first recorded) with replay verification against the runner's assembled inputs.
function statuses(sheet,result,config){
 if(!sheet||sheet.state!=='READY')return{state:'SHEET_NOT_READY',reason_codes:sheet?sheet.reason_codes:['SHEET_NOT_LOADED'],ledgers:[],inputs:{},through:null};
 if(!result||result.state!=='READY'||!result.ledgers||!result.ledgers.SET_A||result.ledgers.SET_A.state!=='READY')
  return{state:'INPUTS_NOT_READY',reason_codes:result&&result.reason_codes&&result.reason_codes.length?[...result.reason_codes]:['INPUTS_NOT_READY'],ledgers:[],inputs:{},through:null};
 const base=sheetBase(result,sheet),through=recordableThrough(base),ledgers=[setALedger(sheet.meta,base,config),...sheet.meta.ledgers.filter(l=>l.kind!=='SET_A')];
 const out={state:'READY',reason_codes:[],ledgers:[],inputs:{},through,defs:{},incomplete:inputsIncomplete(result)};
 for(const led of ledgers){const{status,input}=ledgerStatus(led,base,sheet.rows[led.id]||[],config,through);out.ledgers.push(status);out.inputs[led.id]=input;out.defs[led.id]=led;}
 return out;
}
/* Runner result → the same result with Set A / Set B / shadow inputs taken from the stored ledger definitions, so the
   report shows exactly what is (or will be) recorded. Without a stored shadow ledger the runner's preview stays, with the
   user's TARGET as its target when one is saved. */
function apply(result,sheet){
 if(!result||result.state!=='READY'||!sheet||sheet.state!=='READY'||!result.ledgers.SET_A||result.ledgers.SET_A.state!=='READY')return result;
 const base=sheetBase(result,sheet),cfg=engine().defaultConfig(),ledgers={...result.ledgers},meta=sheet.meta;
 const put=(kind,led)=>{const d=deriveInput(base,led);ledgers[kind]=d.state==='READY'?{state:'READY',reason_codes:[],input:d.input}:{state:NA,reason_codes:d.reason_codes,input:null};};
 if(meta.ledgers.some(l=>l.id==='set_a'))put('SET_A',setALedger(meta,base,cfg));
 const b=active(meta,'SET_B');if(b)put('SET_B',b);
 const s=active(meta,'SHADOW');
 if(s)put('SHADOW',s);
 else if(meta.user_target&&ledgers.SHADOW&&ledgers.SHADOW.state==='READY')ledgers.SHADOW={...ledgers.SHADOW,input:{...ledgers.SHADOW.input,target_weights:{...meta.user_target}}};
 return{...result,ledgers};
}

/* ---------- Google Sheet I/O (user's own sheet, drive.file session) ---------- */
const PAGE=1000,MAX_PAGES=200,MAX_APPEND=200000;
const column=n=>String.fromCharCode(64+n);
async function readTab(session,id,tab){
 const out=[],width=HEADS[tab].length;
 for(let p=0;p<MAX_PAGES;p++){
  const from=p*PAGE+1,payload=await session.fetchValues(id,"'"+tab+"'!A"+from+':'+column(width)+(from+PAGE-1),{maxBytes:1048576,allowEmpty:true});
  const rows=Array.isArray(payload.values)?payload.values:[];out.push(...rows);
  if(rows.length<PAGE)return out;
 }
 fail('SOURCE_TOO_LARGE');
}
async function load(session,id){
 const titles=await session.sheetTitles(id),values={};
 for(const t of ALL_TABS)if(titles.includes(t))values[t]=await readTab(session,id,t);
 return sheetState(values);
}
async function sha256(text,cryptoImpl){
 const c=cryptoImpl||(typeof crypto!=='undefined'?crypto:null);if(!c||!c.subtle)fail('HASH_UNAVAILABLE');
 const digest=await c.subtle.digest('SHA-256',new TextEncoder().encode(text));return[...new Uint8Array(digest)].map(b=>b.toString(16).padStart(2,'0')).join('');
}
// Creates missing tabs with their header row; a present tab without a header gets the header appended. Nothing else.
async function ensureTabs(session,id,sheet){
 const missing=ALL_TABS.filter(t=>!sheet.tabs[t]);
 if(missing.length)await session.addTabs(id,missing);
 for(const t of [...missing,...sheet.headerless])await session.appendRows(id,"'"+t+"'!A1",[[...HEADS[t]]]);
}
// Session-aligned chunks: a chunk boundary never splits one session's rows.
function sessionChunks(rows){
 const bySession=[];for(const r of rows){if(!bySession.length||bySession[bySession.length-1][0][1]!==r[1])bySession.push([]);bySession[bySession.length-1].push(r);}
 const out=[];let cur=[],size=0;
 for(const group of bySession){const n=JSON.stringify(group).length;if(cur.length&&size+n>MAX_APPEND){out.push(cur);cur=[];size=0;}cur.push(...group);size+=n;}
 if(cur.length)out.push(cur);return out;
}
const SCOPES=Object.freeze({MOCK:['SET_A','SET_B'],REAL:['SHADOW']});
/* "장부 시트에 기록": fresh read → replay check → append the missing sessions of the scope's ledgers. Recording mode only:
   the canonical engine config, sessions on/after the start date, never a rehearsal result. */
async function record(session,id,{result,kind,now=nowIso(),rehearsal=false,cryptoImpl=null}){
 const VT=engine(),cfg=VT.defaultConfig();
 if(rehearsal===true||(result&&(result.rehearsal===true||result.mode==='REHEARSAL')))fail('REHEARSAL_NOT_RECORDED');
 if(cfg.start_date!==VT.CONFIG.start_date||cfg.config_version!==VT.CONFIG.config_version)fail('CONFIG_NOT_CANONICAL');
 const sheet=await load(session,id);if(sheet.state!=='READY')fail(sheet.reason_codes[0]);
 const st=statuses(sheet,result,cfg);if(st.state!=='READY')fail(st.reason_codes[0]||st.state);
 const scope=st.ledgers.filter(s=>SCOPES[kind].includes(s.kind));
 if(scope.some(s=>s.state==='LEDGER_REPLAY_MISMATCH'))fail('LEDGER_REPLAY_MISMATCH');
 if(st.incomplete.length)fail('INPUTS_INCOMPLETE');
 const todo=scope.filter(s=>s.missing.length);
 for(const s of todo)if(s.missing.some(d=>d<VT.CONFIG.start_date))fail('BEFORE_START_DATE');
 if(!todo.length)return{sessions:0,ledgers:[]};
 await ensureTabs(session,id,sheet);
 let sessions=0;const written=[];
 for(const s of todo){
  const def=st.defs[s.id];
  if(def.implicit)await session.appendRows(id,"'"+META+"'!A1",[startRow(now,def,cfg,{reason:'INITIAL',target_basis:def.target_basis,target_weights:def.target_weights})]);
  for(const chunk of sessionChunks(s.append_rows))await session.appendRows(id,"'"+s.tab+"'!A1",chunk);
  const hash=await sha256(inputsText(st.inputs[s.id],s.missing[s.missing.length-1]),cryptoImpl);
  await session.appendRows(id,"'"+META+"'!A1",[recordRow(now,s,cfg,hash,s.append_rows.length)]);
  sessions+=s.missing.length;written.push(s.id);
 }
 return{sessions,ledgers:written};
}
async function appendMeta(session,id,rows){const sheet=await load(session,id);if(sheet.state!=='READY')fail(sheet.reason_codes[0]);await ensureTabs(session,id,sheet);await session.appendRows(id,"'"+META+"'!A1",rows);}
// Set B definition: closes the open Set B ledger (if any) and starts a new one from the next session (no back-filling).
async function saveSetB(session,id,weights,{now=nowIso()}={}){
 const cfg=engine().defaultConfig(),v=validateWeights(weights,runner().IDS);if(v.state!=='OK')fail(v.reason_codes[0]);
 const sheet=await load(session,id);if(sheet.state!=='READY')fail(sheet.reason_codes[0]);
 const old=active(sheet.meta,'SET_B'),last=old&&sheet.rows[old.id]?recordedDates(sheet.rows[old.id]).pop():null;
 const rows=replaceRows(sheet.meta,'SET_B',now,cfg,{target_basis:'SET_B',target_weights:v.weights},last,old?'SET_B_REDEFINED':'INITIAL');
 await ensureTabs(session,id,sheet);await session.appendRows(id,"'"+META+"'!A1",rows);return rows;
}
async function saveTarget(session,id,weights,{now=nowIso()}={}){
 const v=validateWeights(weights,runner().IDS);if(v.state==='INVALID')fail(v.reason_codes[0]);
 await appendMeta(session,id,[targetRow(now,v.weights)]);return v;
}
/* Shadow start snapshot (D-17) from the device's current ACTUAL holdings: quantities, average costs and currencies;
   the KRW cost follows the runner's FX rule at the ledger's first session. reason RESYNC closes the open shadow ledger
   ("실제 보유로 다시 맞추기"); its recorded rows stay as they are. */
async function startShadow(session,id,holdings,{now=nowIso(),resync=false,catalogWeights=null}={}){
 const cfg=engine().defaultConfig(),positions={};
 const raw=object(holdings)&&object(holdings.positions)?holdings.positions:{};
 for(const cid of Object.keys(raw).sort()){const p=raw[cid];if(own(targets(),cid)&&object(p)&&num(p.quantity)&&p.quantity>0)positions[cid]={quantity:p.quantity,average_cost:p.average_cost,currency:p.currency};}
 if(!Object.keys(positions).length)fail('NO_ACTUAL');
 if(Object.values(positions).some(p=>!(num(p.average_cost)&&p.average_cost>=0&&CURRENCIES.includes(p.currency))))fail('ACTUAL_INVALID');
 const sheet=await load(session,id);if(sheet.state!=='READY')fail(sheet.reason_codes[0]);
 const old=active(sheet.meta,'SHADOW');if(resync!==!!old)fail(old?'SHADOW_ALREADY_STARTED':'SHADOW_NOT_STARTED');
 const user=sheet.meta.user_target,catalog=catalogWeights&&weightsOk(catalogWeights)?catalogWeights:null;
 if(!user&&!catalog)fail('TARGET_NOT_AVAILABLE');
 const last=old&&sheet.rows[old.id]?recordedDates(sheet.rows[old.id]).pop():null;
 const rows=replaceRows(sheet.meta,'SHADOW',now,cfg,{target_basis:user?'USER_TARGET':'TARGET_V0',target_weights:user||catalog,
  snapshot:{effective_at:now,source_effective_at:typeof holdings.effective_at==='string'?holdings.effective_at:null,positions}},last,resync?'RESYNC':'INITIAL');
 await ensureTabs(session,id,sheet);await session.appendRows(id,"'"+META+"'!A1",rows);return rows;
}

/* ---------- S17 cards ---------- */
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const KIND_KO={SET_A:'세트 A',SET_B:'세트 B',SHADOW:'그림자 장부'},BASIS_KO={TARGET_V0:'TARGET v0(공식)',SET_B:'세트 B 구성',USER_TARGET:'내 목표(TARGET)'};
const STATE_KO={OK:'재생 확인 일치',LEDGER_REPLAY_MISMATCH:'LEDGER_REPLAY_MISMATCH · 기록과 재생 결과가 다릅니다(쓰기 중지)',NOT_AVAILABLE:'NOT_AVAILABLE',NOT_STARTED:'시작 전'};
const SHEET_KO={NOT_CONNECTED:'구글 로그인과 시트 연결이 필요합니다(설정 → Google 첫 설정).',LOADING:'내 시트의 가상 장부를 읽는 중',READY:'내 시트 가상 장부 읽음',ERROR:'시트 장부를 쓸 수 없습니다'};
// TARGET v0 weights from the public catalog: the shadow basis when no user TARGET is saved.
function catalogWeights(catalog){const t=runner().catalogTargets(catalog);return t?Object.fromEntries(t.map(x=>[x.cid,x.weight])):null;}
function catalogRows(catalog){
 const ids=runner().IDS;try{return catalog.instruments.map(r=>({cid:ids[r.row_index],ticker:r.ticker,label:r.label,target:r.target_units/100})).filter(r=>r.cid);}catch(_){return ids.map(cid=>({cid,ticker:runner().TARGETS[cid],label:cid,target:null}));}
}
function weightForm(kind,rows,current,{title,note,save,connected}){
 const sum=Object.values(current||{}).reduce((a,v)=>a+v,0);
 let h='<section class="card" data-weight-form="'+kind+'" data-weight-state="'+(current?'OK':NA)+'"><h2>'+esc(title)+'</h2><p class="small">'+esc(note)+'</p>';
 h+='<div class="table-wrap"><table><thead><tr><th>기업</th><th>목표 %</th></tr></thead><tbody>'+rows.map(r=>'<tr><td>'+esc(r.label+' ('+r.ticker+')')+'</td><td><input type="text" inputmode="decimal" size="6" aria-label="'+esc(r.ticker+' 목표 %')+'" data-weight="'+esc(r.cid)+'" value="'+esc(current&&own(current,r.cid)?String(current[r.cid]):'')+'"></td></tr>').join('')+'</tbody></table></div>';
 h+='<p data-weight-sum>'+esc(current?'합계 '+(Math.round(sum*10000)/10000)+'% · 나머지는 가상 현금':'NOT_AVAILABLE · 구성 없음')+'</p>';
 h+='<div class="sheet-actions"><button type="button" data-weight-save="'+kind+'"'+(connected?'':' disabled')+'>'+esc(save)+'</button></div><p role="status" class="small" data-weight-status="'+kind+'"></p></section>';
 return h;
}
function ledgerLine(s,def){
 const parts=[KIND_KO[s.kind]+' '+s.id,'출발 '+s.begin+(s.end?' · 종료 '+s.end:''),'목표 기준 '+(BASIS_KO[s.target_basis]||s.target_basis),
  s.recorded_sessions?'기록 '+s.recorded_sessions+'거래일(~'+s.recorded_through+')':'기록 없음',STATE_KO[s.state]||s.state];
 if(s.state==='LEDGER_REPLAY_MISMATCH'&&s.first_mismatch)parts.push('첫 차이 '+s.first_mismatch.session);
 if(s.reason_codes.length&&s.state!=='LEDGER_REPLAY_MISMATCH')parts.push(s.reason_codes.join(', '));
 if(s.inputs_changed)parts.push('INPUTS_CHANGED');
 return '<li data-ledger-id="'+esc(s.id)+'" data-ledger-check="'+esc(s.state)+'" data-ledger-missing="'+s.missing.length+'">'+esc(parts.join(' · '))+(def&&def.implicit?' <span class="small">(첫 기록 때 VirtualMeta에 정의)</span>':'')+'</li>';
}
function recordCard(ctx,state){
 const{sheet,st,busy,before,connected}=state,scope=SCOPES[ctx.kind==='REAL'?'REAL':'MOCK'];
 const list=st&&st.state==='READY'?st.ledgers.filter(s=>scope.includes(s.kind)):[];
 const missing=list.reduce((a,s)=>a+s.missing.length,0),mismatch=list.some(s=>s.state==='LEDGER_REPLAY_MISMATCH');
 const sheetState=!connected?'NOT_CONNECTED':!sheet?'LOADING':sheet.state;
 let h='<section class="card" data-ledger-sheets data-sheet-state="'+esc(sheetState)+'" data-ledger-mismatch="'+(mismatch?'1':'0')+'"><h2>가상 장부 시트 기록 <span class="badge">가상 · 실제 추천 아님 · 주문 기능 없음</span></h2>';
 h+='<p data-ledger-sheet-summary>'+esc((SHEET_KO[sheetState]||sheetState)+(sheet&&sheet.state==='ERROR'?' · '+sheet.reason_codes.join(', ')+(sheet.tab?' ('+sheet.tab+')':''):''))+'</p>';
 if(before)h+='<p class="badge NOT_AVAILABLE" data-ledger-before-start>'+esc('가상매매 시작일 '+engine().CONFIG.start_date+' 전 · 기록하지 않음')+'</p>';
 else if(st&&st.state==='INPUTS_NOT_READY'&&connected&&sheet&&sheet.state==='READY')h+='<p class="small" data-ledger-inputs>'+esc('장부 입력 준비 전 · 재생 확인 대기('+st.reason_codes.join(', ')+')')+'</p>';
 if(list.length)h+='<ul class="small" data-ledger-list>'+list.map(s=>ledgerLine(s,st.defs[s.id])).join('')+'</ul>';
 const incomplete=st&&st.state==='READY'?st.incomplete:[];
 if(incomplete.length)h+='<p class="small" data-ledger-incomplete>'+esc('INPUTS_INCOMPLETE · 시세를 다시 받은 뒤 기록합니다: '+incomplete.join(', '))+'</p>';
 if(mismatch)h+='<p class="badge NOT_AVAILABLE" data-ledger-replay-mismatch>LEDGER_REPLAY_MISMATCH · 기록된 행이 같은 입력의 재생 결과와 다릅니다. 시트에 쓰지 않습니다.</p>';
 if(missing)h+='<p data-missing-sessions>'+esc('빠진 거래일 재생: '+list.flatMap(s=>s.missing.map(d=>s.id+' '+d)).join(', '))+'</p>';
 else if(st&&st.state==='READY')h+='<p class="small" data-missing-sessions="0">'+esc('기록할 새 거래일 없음'+(st.through?' · Q·G 기록 기준 ~'+st.through:' · Q·G 기록 대기'))+'</p>';
 const can=connected&&sheet&&sheet.state==='READY'&&!before&&!mismatch&&!incomplete.length&&missing>0&&!busy;
 h+='<div class="sheet-actions"><button type="button" data-ledger-record'+(can?'':' disabled')+'>'+esc('장부 시트에 기록'+(missing?' ('+missing+'거래일)':''))+'</button></div>';
 h+='<p class="small">기록은 이 버튼을 누를 때만, 아직 기록하지 않은 거래일만 내 시트(VirtualA·VirtualB·VirtualMine·VirtualMeta)에 덧붙입니다. 기록한 행은 고치지 않습니다. 시트에는 실제 숫자가 저장되고, 화면에는 날짜·개수·코드만 보입니다. 값이 없던 날은 엔진 결과(NOT_AVAILABLE·EXEC_*_MISSING)대로 기록하고 채우지 않습니다.</p>';
 h+='<p role="status" data-ledger-status></p></section>';
 return h;
}
function shadowCard(state){
 const{sheet,connected,st}=state,meta=sheet&&sheet.state==='READY'?sheet.meta:null,open=meta?active(meta,'SHADOW'):null;
 const user=meta?meta.user_target:null,basis=open?open.target_basis:(user?'USER_TARGET':'TARGET_V0');
 let h='<section class="card" data-shadow-ledger data-shadow-state="'+(open?'STARTED':'NOT_STARTED')+'"><h2>그림자 장부 출발 스냅샷 <span class="badge">D-17</span></h2>';
 h+='<p data-target-basis="'+esc(basis)+'">'+esc('목표 기준: '+BASIS_KO[basis]+(open?' · 장부 '+open.id+' 출발 '+open.begin:' · 출발 스냅샷 없음(화면은 기기 보유 기준 미리보기, 기록 안 함)'))+'</p>';
 if(open&&user&&canonical(user)!==canonical(open.target_weights))h+='<p class="small" data-target-pending>'+esc('저장한 내 목표는 \'실제 보유로 다시 맞추기\' 뒤 새 장부부터 적용됩니다. 현재 장부는 출발 때의 목표를 유지합니다.')+'</p>';
 const segs=meta?meta.ledgers.filter(l=>l.kind==='SHADOW'):[];
 if(segs.length)h+='<ul class="small" data-shadow-segments>'+segs.map(l=>'<li data-segment="'+esc(l.id)+'">'+esc(l.id+' · 출발 '+l.begin+(l.end?' · 종료 '+l.end:' · 진행 중')+' · '+(l.reason==='RESYNC'?'다시 맞추기':'첫 출발')+' · 보유 '+Object.keys(l.snapshot.positions).length+'종목')+'</li>').join('')+'</ul>';
 h+='<div class="sheet-actions">'+(open?'<button type="button" data-shadow-resync'+(connected&&!state.busy?'':' disabled')+'>실제 보유로 다시 맞추기</button>':'<button type="button" data-shadow-create'+(connected&&meta&&!state.busy?'':' disabled')+'>실제 보유로 출발 스냅샷 만들기</button>')+'</div>';
 h+='<p class="small">현재 기기 실제 보유(수량·평균단가·통화)를 내 시트 VirtualMeta에 출발 스냅샷으로 저장합니다. 원화 원가는 장부 첫 거래일 이전 마지막 환율로 계산합니다. 그 뒤 그림자 장부는 실제 거래와 독립으로 움직입니다. 다시 맞추기는 현재 장부를 닫고 새 장부를 시작하며 이전 기록은 그대로 둡니다.</p>';
 h+='<p role="status" data-shadow-status></p></section>';
 return h;
}

let carry=null; // status text carried into the next mount after a save re-renders the report
/* Report hook: mount(view, host, {kind, tab, reportDate, config, catalog: async () => catalog, refresh}) →
   {runnerOptions(), update(result) → result for the report, dispose()}. */
function mount(view,host,ctx){
 const VT=engine(),cfg=VT.defaultConfig(),kind=ctx.kind==='REAL'?'REAL':'MOCK',tab=ctx.tab;
 const carried=carry&&carry.key===kind+'/'+tab?carry.notes:{};carry=null;
 const state={sheet:null,st:null,result:null,notes:{...carried},drafts:{},busy:false,connected:false,before:typeof ctx.reportDate==='string'&&ctx.reportDate<cfg.start_date,catalog:null};
 let session=null,disposed=false,loading=null,unsubscribe=null,revision=0;
 try{session=ctx.config&&ctx.config.googleSheetsClientId&&view.GoogleSheetQuotes?view.GoogleSheetQuotes.sessionFor(view,ctx.config.googleSheetsClientId):null;}catch(_){session=null;}
 const sheetId=()=>{try{return view.GoogleSheetSetup?view.GoogleSheetSetup.source(view):'';}catch(_){return'';}};
 const isConnected=()=>!!(session&&session.state().connected&&sheetId());
 const live=()=>!disposed&&host&&host.isConnected;
 const verifyHashes=async()=>{
  const st=state.st;if(!st||st.state!=='READY')return;
  for(const s of st.ledgers){const rec=state.sheet.meta.records[s.id];if(!rec||rec.session!==s.recorded_through||!st.inputs[s.id])continue;
   try{s.inputs_changed=(await sha256(inputsText(st.inputs[s.id],rec.session)))!==rec.sha256;}catch(_){}}
 };
 const recompute=async()=>{state.st=state.sheet&&state.sheet.state==='READY'?statuses(state.sheet,state.result,cfg):null;await verifyHashes();paint();};
 const reload=()=>{
  const mine=++revision;state.connected=isConnected();
  if(!state.connected){state.sheet=null;loading=Promise.resolve(null);paint();return loading;}
  state.sheet=null;paint();
  loading=load(session,sheetId()).catch(e=>({state:'ERROR',reason_codes:[e&&typeof e.message==='string'&&/^[A-Z][A-Z0-9_]{0,63}$/.test(e.message)?e.message:'READ_FAILED'],tab:null,tabs:{},headerless:[],meta:null,rows:{},flags:[]}))
   .then(async sheet=>{if(mine!==revision||disposed)return sheet;state.sheet=sheet;await recompute();return sheet;});
  return loading;
 };
 const say=(sel,text)=>{state.notes[sel]=text;const n=live()&&host.querySelector(sel);if(n)n.textContent=text;};
 const errorCode=e=>e&&typeof e.message==='string'&&/^[A-Z][A-Z0-9_]{0,63}$/.test(e.message)?e.message:'WRITE_FAILED';
 const act=async(statusSel,fn,done)=>{
  if(state.busy)return;if(!isConnected()){say(statusSel,SHEET_KO.NOT_CONNECTED);return;}
  state.busy=true;paint();
  try{const text=await fn();state.busy=false;if(done){carry={key:kind+'/'+tab,notes:{[statusSel]:text}};done();return;}await reload();say(statusSel,text);}
  catch(e){state.busy=false;paint();say(statusSel,errorCode(e));}
 };
 const readForm=k=>{const out={};for(const input of host.querySelectorAll('[data-weight-form="'+k+'"] [data-weight]'))out[input.getAttribute('data-weight')]=input.value;return out;};
 function paint(){
  if(!live())return;
  const rows=catalogRows(state.catalog);let h=recordCard(ctx,state);
  const meta=state.sheet&&state.sheet.state==='READY'?state.sheet.meta:null;
  if(kind==='MOCK'&&tab==='SET_B'){const b=meta?active(meta,'SET_B'):null;
   h+=weightForm('SET_B',rows,b?b.target_weights:null,{title:'세트 B 구성 (사용자 정의)',note:'TARGET 19종목 중에서 고르고 목표 비중(%)을 넣으세요. 합계는 100 이하, 나머지는 가상 현금입니다. 비우면 NOT_AVAILABLE입니다. 저장하면 내 시트 VirtualMeta에 새 세트 B 장부로 기록되고 다음 거래일부터 적용됩니다(이전 장부와 기록은 보존).',save:'세트 B 구성 저장',connected:state.connected&&!!meta&&!state.busy});}
  if(kind==='REAL'){
   h+=weightForm('TARGET',rows,meta?meta.user_target:null,{title:'내 목표(TARGET) · 비공개',note:'내 실제 포트폴리오의 목표 비중(%)입니다. 내 시트 VirtualMeta에만 저장되며, 있으면 그림자 장부의 목표로 TARGET v0 대신 씁니다. 공식 TARGET v0는 바뀌지 않습니다.',save:'내 목표 저장',connected:state.connected&&!!meta&&!state.busy});
   h+=shadowCard(state);
  }
  host.innerHTML=h;
  for(const[sel,text]of Object.entries(state.notes)){const n=host.querySelector(sel);if(n)n.textContent=text;}
  const rec=host.querySelector('[data-ledger-record]');
  if(rec)rec.onclick=()=>void act('[data-ledger-status]',async()=>{const r=await record(session,sheetId(),{result:state.result,kind});return r.sessions?r.sessions+'거래일을 기록했습니다('+r.ledgers.join(', ')+').':'기록할 새 거래일이 없습니다.';});
  const sum=form=>{const k=form.getAttribute('data-weight-form'),v=validateWeights(readForm(k),runner().IDS),n=form.querySelector('[data-weight-sum]');
   if(n)n.textContent=v.state==='OK'?'합계 '+(Math.round(Object.values(v.weights).reduce((a,x)=>a+x,0)*10000)/10000)+'% · 나머지는 가상 현금':v.state===NA?'NOT_AVAILABLE · 구성 없음':v.reason_codes[0];form.setAttribute('data-weight-state',v.state);};
  // Typed values survive repaints (sheet reload, failed save) until a save succeeds.
  for(const form of host.querySelectorAll('[data-weight-form]')){const k=form.getAttribute('data-weight-form'),draft=state.drafts[k];
   if(draft){for(const input of form.querySelectorAll('[data-weight]'))input.value=own(draft,input.getAttribute('data-weight'))?draft[input.getAttribute('data-weight')]:'';sum(form);}}
  for(const input of host.querySelectorAll('[data-weight]'))input.oninput=()=>{const form=input.closest('[data-weight-form]');state.drafts[form.getAttribute('data-weight-form')]=readForm(form.getAttribute('data-weight-form'));sum(form);};
  const saved=k=>()=>{delete state.drafts[k];ctx.refresh();};
  const saveB=host.querySelector('[data-weight-save="SET_B"]');
  if(saveB)saveB.onclick=()=>{const w=readForm('SET_B');void act('[data-weight-status="SET_B"]',async()=>{const rows=await saveSetB(session,sheetId(),w);return'세트 B 구성을 저장했습니다('+rows[rows.length-1][1]+', 출발 '+rows[rows.length-1][4]+').';},saved('SET_B'));};
  const saveT=host.querySelector('[data-weight-save="TARGET"]');
  if(saveT)saveT.onclick=()=>{const w=readForm('TARGET');void act('[data-weight-status="TARGET"]',async()=>{const v=await saveTarget(session,sheetId(),w);return v.state==='OK'?'내 목표를 저장했습니다.':'내 목표를 비웠습니다(NOT_AVAILABLE).';},saved('TARGET'));};
  const shadow=async resync=>{
   if(resync&&view.confirm&&!view.confirm('현재 그림자 장부를 닫고 오늘 실제 보유로 새 장부를 시작합니다. 이전 기록은 그대로 보존됩니다.'))return;
   await act('[data-shadow-status]',async()=>{
    let holdings=null;try{const catalog=await ctx.catalog();holdings=runner().holdingsFromSnapshot(await view.DeviceActual.readHoldings(view,catalog),catalog);}catch(_){holdings=null;}
    if(!holdings)fail('NO_ACTUAL');
    const rows=await startShadow(session,sheetId(),holdings,{resync,catalogWeights:catalogWeights(state.catalog)});return(resync?'다시 맞췄습니다: ':'출발 스냅샷을 저장했습니다: ')+rows[rows.length-1][1]+' · 출발 '+rows[rows.length-1][4];
   },ctx.refresh);
  };
  const create=host.querySelector('[data-shadow-create]');if(create)create.onclick=()=>void shadow(false);
  const resync=host.querySelector('[data-shadow-resync]');if(resync)resync.onclick=()=>void shadow(true);
 }
 (async()=>{try{state.catalog=await ctx.catalog();}catch(_){state.catalog=null;}paint();})();
 try{if(session)unsubscribe=session.subscribe(()=>{if(!live()){dispose();return;}if(isConnected()!==state.connected)void reload();});}catch(_){unsubscribe=null;}
 reload();
 function dispose(){disposed=true;if(unsubscribe){try{unsubscribe();}catch(_){}unsubscribe=null;}}
 return Object.freeze({
  async runnerOptions(){const sheet=await loading;if(!sheet||sheet.state!=='READY')return{};const b=active(sheet.meta,'SET_B');return{set_b:b?{target_weights:{...b.target_weights}}:null,flags:sheet.flags};},
  update(result){state.result=result;void recompute();return apply(result,state.sheet);},
  dispose
 });
}

return Object.freeze({SCHEMA,TABS,META,FLAGS,LEDGER_HEAD,META_HEAD,FLAGS_HEAD,HEADS,ALL_TABS,numStr,canonical,dayRows,ledgerRows,parseTab,groupLedgerRows,recordedDates,
 parseMeta,active,setALedger,nextId,validateWeights,parseFlags,recordableThrough,deriveInput,truncate,inputsText,ledgerStatus,startRow,closeRow,recordRow,targetRow,
 beginFor,replaceRows,sheetState,statuses,apply,inputsIncomplete,load,ensureTabs,record,saveSetB,saveTarget,startShadow,sha256,mount});
});
