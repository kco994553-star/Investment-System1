/* Virtual ledger sheet storage v1 (D-10): the virtual ledgers (Set A, user sets B/C/D, shadow) written to the user's own
   Google Sheet tabs VirtualA / VirtualB / VirtualC / VirtualD / VirtualMine / VirtualMeta / VirtualFlags, append-only,
   only on the user's click. Pure part mirrors qgv/virtual_ledger_sheets.py (vectors: tests/fixtures/virtual_ledger_sheets_v1.json):
   row format, continuation from the recorded state (decision 2026-10-11: recorded rows are canonical; a replay that
   differs only marks PRICE_REVISED, it never blocks or rewrites) and the missing-session plan.
   The sheet is the user's private storage, so its cells hold real numbers; this screen shows only dates, counts, codes
   and weights. Nothing here logs, stores on the device or publishes prices, ledgers, holdings or the sheet id.
   Virtual records only · not a recommendation · no order function. */
(function(root,factory){const node=typeof module==='object'&&module.exports;const api=factory(node?()=>require('./virtual-trading.js'):()=>root.VirtualTrading,node?()=>require('./virtual-trading-runner.js'):()=>root.VirtualTradingRunner);if(node)module.exports=api;else root.VirtualLedgerSheets=api;})(typeof globalThis==='object'?globalThis:this,function(engine,runner){
'use strict';
const SCHEMA='virtual-ledger-sheets/1';
// Every state/reason code this module can show or throw (labels: VirtualTrading.CODE_LABELS).
const CODES=Object.freeze(['PRICE_REVISED','SHEET_ROWS_INVALID','SET_NOT_DEFINED','SET_MEMBERS_OVER_30','PURPOSE_REQUIRED','PURPOSE_INVALID','SET_A_CHANGED','SET_DELETED','SET_REDEFINED','NO_SESSION_AFTER_RECORDED','SHEET_HEADER_MISMATCH','META_INVALID','META_ROW_INVALID','LEDGER_UNKNOWN','INPUTS_NOT_READY',
 'INPUTS_INCOMPLETE','INPUTS_CHANGED','WAITING_FOR_QG_RECORD','VALUATION_NOT_AVAILABLE','SHEET_NOT_READY','SHEET_NOT_LOADED','NOT_CONNECTED','SHADOW_NOT_STARTED',
 'SHADOW_ALREADY_STARTED','SET_B_REDEFINED','REHEARSAL_NOT_RECORDED','NUMBER_INVALID','VALUE_INVALID','CONFIG_NOT_CANONICAL','COMPANY_NOT_SUPPORTED','WEIGHT_INVALID',
 'WEIGHT_SUM_OVER_100','WEIGHTS_EMPTY','WRITE_FAILED','READ_FAILED','HASH_UNAVAILABLE','NO_ACTUAL','ACTUAL_INVALID','INITIAL_COST_FX_MISSING','BEFORE_START_DATE',
 'TARGET_NOT_AVAILABLE','REQUEST_INVALID','NOT_REQUESTED','SOURCE_TOO_LARGE','INVALID']);
const TABS=Object.freeze({SET_A:'VirtualA',SET_B:'VirtualB',SET_C:'VirtualC',SET_D:'VirtualD',SHADOW:'VirtualMine'}),META='VirtualMeta',FLAGS='VirtualFlags';
const LEDGER_HEAD=Object.freeze(['ledger_id','session_date','row_type','company','level','aux_levels','reason_codes','aux_codes','side','amount','quantity','price_used','fx_used','cash_after','total_value']);
const META_HEAD=Object.freeze(['recorded_at','ledger_id','kind','event','start_date','end_date','config_version','engine_version','last_recorded_session','inputs_sha256','payload']);
const FLAGS_HEAD=Object.freeze(['created_at','date','company','kind']);
const HEADS=Object.freeze({VirtualA:LEDGER_HEAD,VirtualB:LEDGER_HEAD,VirtualC:LEDGER_HEAD,VirtualD:LEDGER_HEAD,VirtualMine:LEDGER_HEAD,VirtualMeta:META_HEAD,VirtualFlags:FLAGS_HEAD});
const ALL_TABS=Object.freeze(['VirtualA','VirtualB','VirtualC','VirtualD','VirtualMine','VirtualMeta','VirtualFlags']);
const ROW_TYPES=['INITIAL','EXECUTED','CANCELLED','JUDGEMENT','ORDER','SUMMARY'],KINDS=['SET_A','SET_B','SET_C','SET_D','SHADOW'],USER_SETS=['SET_B','SET_C','SET_D'];
const BASES=['TARGET_V0','SET_A','SET_B','SET_C','SET_D','USER_TARGET'];
const PREFIX={SET_A:'set_a',SET_B:'set_b-',SET_C:'set_c-',SET_D:'set_d-',SHADOW:'shadow-'},CURRENCIES=['USD','KRW','JPY'],MAX_MEMBERS=30,MAX_PURPOSE=120;
const FLAG_KINDS=['HOLD','EXCLUDE','CONFIRMED_TEMPORARY','CONFIRMED_STRUCTURAL','CLEAR'];
const NA='NOT_AVAILABLE',ID=/^(?:set_a(?:@v(?:[2-9]|[1-9][0-9]{1,5}))?|set_[bcd]-[1-9][0-9]{0,5}|shadow-[1-9][0-9]{0,5})$/,WEIGHT_TEXT=/^(?:0|[1-9][0-9]{0,2})(?:\.[0-9]{1,4})?$/,SHA=/^[0-9a-f]{64}$/;
const NUMBER_TEXT=/^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:e[+-][0-9]+)?$/;
const DAY=/^\d{4}-\d{2}-\d{2}$/,CLOCK=/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$/;
const own=(o,k)=>o!==null&&typeof o==='object'&&Object.prototype.hasOwnProperty.call(o,k);
const object=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
const num=v=>typeof v==='number'&&Number.isFinite(v);
function day(v){if(!(typeof v==='string'&&DAY.test(v)))return false;const m=+v.slice(5,7),d=+v.slice(8);return m>=1&&m<=12&&d>=1&&d<=31;}
function fail(code){throw new Error(code);}
const targets=()=>runner().TARGETS,members=()=>runner().MEMBERS;

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
// INITIAL rows go with the ledger's first day; a continuation from a recorded state has no first day.
function ledgerRows(id,result,input,dates){
 const wanted=new Set(dates),out=[],first=!(own(input,'resume')&&input.resume!==null&&input.resume!==undefined);
 result.days.forEach((d,i)=>{if(wanted.has(d.date))out.push(...dayRows(id,d,i===0&&first?input.initial:null));});
 return out;
}

/* ---------- recorded state (decision 2026-10-11: recorded rows are canonical) ---------- */
function numberCell(text,positive=false){if(!(typeof text==='string'&&NUMBER_TEXT.test(text)))fail('SHEET_ROWS_INVALID');const x=Number(text);if(!num(x)||(positive&&!(x>0)))fail('SHEET_ROWS_INVALID');return x;}
/* One ledger's recorded rows (sheet order) → the engine resume state after its last recorded session: cash (SUMMARY
   cash_after), positions (INITIAL rows, then EXECUTED rows with the engine's own arithmetic), the orders decided on that
   session (ORDER rows) and the last valued total. Malformed rows → SHEET_ROWS_INVALID. */
function recordedState(rows){
 if(!Array.isArray(rows)||!rows.length)fail('SHEET_ROWS_INVALID');
 const positions={};let pending=[],last=null,summary=null,cash=null,total=null;
 for(const r of rows){
  const d=r[1],kind=r[2],cid=r[3];
  if(d!==last){if(last!==null&&summary!==last)fail('SHEET_ROWS_INVALID');last=d;pending=[];}
  if(summary===d)fail('SHEET_ROWS_INVALID');
  if(kind==='INITIAL'){if(own(positions,cid))fail('SHEET_ROWS_INVALID');positions[cid]={quantity:numberCell(r[10],true),cost:numberCell(r[9])};}
  else if(kind==='EXECUTED'){
   const side=r[8],amount=numberCell(r[9],true),qty=numberCell(r[10],true);
   if(side==='BUY'){if(!own(positions,cid))positions[cid]={quantity:0,cost:0};const p=positions[cid];p.quantity+=qty;p.cost+=amount;}
   else if(side==='SELL'){const p=own(positions,cid)?positions[cid]:null;if(!p||qty>p.quantity)fail('SHEET_ROWS_INVALID');
    const avg=p.cost/p.quantity,costOut=avg*qty;if(qty===p.quantity)delete positions[cid];else{p.quantity-=qty;p.cost-=costOut;}}
   else fail('SHEET_ROWS_INVALID');
  }else if(kind==='ORDER'){if(!(r[8]==='BUY'||r[8]==='SELL')||!cid)fail('SHEET_ROWS_INVALID');pending.push({company:cid,side:r[8],amount:numberCell(r[9],true),reason_codes:r[6]?r[6].split(','):[]});}
  else if(kind==='SUMMARY'){cash=numberCell(r[13]);if(cash<0)fail('SHEET_ROWS_INVALID');if(r[14]!==NA)total=numberCell(r[14]);summary=d;}
 }
 if(summary!==last)fail('SHEET_ROWS_INVALID');
 const sorted={};for(const cid of Object.keys(positions).sort())sorted[cid]=positions[cid];
 return{after:last,cash,total_value:total,pending,positions:sorted};
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
 if(!object(w)||!Object.keys(w).length||Object.keys(w).length>MAX_MEMBERS)return false;
 for(const[k,v]of Object.entries(w))if(!(own(members(),k)&&num(v)&&v>=0&&v<=100))return false;
 let total=0;for(const k of Object.keys(w).sort())total+=w[k];return total<=100+1e-9;
}
function snapshotOk(s){return object(s)&&typeof s.effective_at==='string'&&object(s.positions)&&Object.entries(s.positions).every(([k,p])=>own(targets(),k)&&object(p));}
// A set's one-line purpose: 1–120 characters, no line break or control character.
function purposeOk(v){return typeof v==='string'&&v.trim().length>0&&v.length<=MAX_PURPOSE&&v===v.trim()&&![...v].some(c=>c.charCodeAt(0)<32||c.charCodeAt(0)===127);}
function parseMeta(rows){
 const ledgers=new Map(),records={};let target=null;
 for(let i=0;i<rows.length;i++){
  const ev={};META_HEAD.forEach((k,j)=>{ev[k]=rows[i][j];});
  const bad={state:'META_INVALID',reason_codes:['META_ROW_INVALID'],row:i};
  let payload;try{payload=ev.payload?JSON.parse(ev.payload):{};}catch(_){return bad;}
  let ok=object(payload);const event=ev.event,lid=ev.ledger_id,kind=ev.kind;
  if(ok&&event==='LEDGER_START'){
   const basis=payload.target_basis,weights=payload.target_weights,purpose=own(payload,'purpose')?payload.purpose:null;
   ok=ID.test(lid)&&!ledgers.has(lid)&&KINDS.includes(kind)&&lid.startsWith(PREFIX[kind])&&day(ev.start_date)&&ev.end_date===''&&BASES.includes(basis)&&weightsOk(weights)&&(purpose===null||purposeOk(purpose))&&(kind!=='SHADOW'||snapshotOk(payload.snapshot));
   if(ok)ledgers.set(lid,{id:lid,kind,begin:ev.start_date,end:null,target_basis:basis,target_weights:weights,snapshot:kind==='SHADOW'?payload.snapshot:null,
    config_version:ev.config_version,engine_version:ev.engine_version,reason:typeof payload.reason==='string'?payload.reason:null,purpose,close_reason:null});
  }else if(ok&&event==='LEDGER_CLOSE'){
   const led=ledgers.get(lid);ok=!!led&&led.kind===kind&&led.end===null&&day(ev.end_date)&&ev.end_date>=led.begin;
   if(ok){led.end=ev.end_date;led.close_reason=typeof payload.reason==='string'?payload.reason:null;}
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
// The current Set A ledger: the open stored version, else the implicit v1.1 example (start date, TARGET v0).
function setALedger(meta,base,config){
 const found=active(meta,'SET_A');if(found)return found;
 if(meta.ledgers.some(l=>l.kind==='SET_A'))return null;
 return{id:'set_a',kind:'SET_A',begin:config.start_date,end:null,target_basis:'TARGET_V0',target_weights:{...base.target_weights},snapshot:null,implicit:true,
  config_version:config.config_version??null,engine_version:config.rules_version,reason:null,purpose:null,close_reason:null};
}
// Every ledger to verify/record, by kind (Set A, B, C, D, shadow) then start order: the stored ones (closed ones included)
// plus the implicit Set A when none is stored.
function allLedgers(meta,base,config){const stored=[...meta.ledgers];if(!stored.some(l=>l.kind==='SET_A'))stored.unshift(setALedger(meta,base,config));return stored.map((l,i)=>[KINDS.indexOf(l.kind),i,l]).sort((x,y)=>x[0]-y[0]||x[1]-y[1]).map(x=>x[2]);}
function nextId(meta,kind){const n=1+meta.ledgers.filter(l=>l.kind===kind).length;return kind==='SET_A'?(n===1?'set_a':'set_a@v'+n):PREFIX[kind]+n;}

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
// A set definition from the form: weights over allowlisted members (1–30, sum ≤ 100) and, for user sets B/C/D, the
// required one-line purpose.
function validateSet(rawWeights,purpose,kind,allowed){
 const v=validateWeights(rawWeights,allowed);if(v.state!=='OK')return{...v,purpose:null};
 const bad=code=>({state:'INVALID',reason_codes:[code],weights:null,purpose:null});
 if(Object.keys(v.weights).length>MAX_MEMBERS)return bad('SET_MEMBERS_OVER_30');
 const text=typeof purpose==='string'?purpose.trim():null;
 if(USER_SETS.includes(kind)&&!text)return bad('PURPOSE_REQUIRED');
 if(text&&!purposeOk(text))return bad('PURPOSE_INVALID');
 return{state:'OK',reason_codes:[],weights:v.weights,purpose:text||null};
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
/* One ledger's recorded rows → the sessions still to write, continued from the recorded state (pure, deterministic). The
   full replay is compared with the recorded rows only to mark PRICE_REVISED (first differing session); it never blocks
   or rewrites. Malformed recorded rows → SHEET_ROWS_INVALID (blocks). */
function ledgerStatus(ledger,base,recorded,config,through){
 const out={id:ledger.id,kind:ledger.kind,tab:TABS[ledger.kind],begin:ledger.begin,end:ledger.end,target_basis:ledger.target_basis,state:'OK',reason_codes:[],
  recorded_sessions:0,recorded_through:null,missing:[],price_revised:null,append_rows:[],replay_through:null};
 const dates=recordedDates(recorded);out.recorded_sessions=dates.length;out.recorded_through=dates.length?dates[dates.length-1]:null;
 const derived=deriveInput(base,ledger);
 if(derived.state!=='READY'){out.state=NA;out.reason_codes=[...derived.reason_codes];return{status:out,input:null};}
 const input=derived.input,result=engine().runLedger(config,input),replay=result.state==='OK'?result.days.map(d=>d.date):[];
 out.replay_through=replay.length?replay[replay.length-1]:null;
 if(!dates.length){
  if(result.state!=='OK'){out.state=result.state;out.reason_codes=[...result.reason_codes];return{status:out,input};}
  const missing=replay.filter(d=>through!==null&&d<=through);
  out.missing=missing;out.append_rows=ledgerRows(ledger.id,result,input,missing);
  if(!missing.length&&replay.length)out.reason_codes=['WAITING_FOR_QG_RECORD'];
  return{status:out,input};
 }
 let state;try{state=recordedState(recorded);}catch(e){out.state=e.message;out.reason_codes=[e.message];return{status:out,input};}
 const codes=[],expected=result.state==='OK'?ledgerRows(ledger.id,result,input,dates):[];
 const prefix=dates.every((d,i)=>replay[i]===d);
 if(result.state!=='OK'||!prefix||expected.length!==recorded.length||!expected.every((r,i)=>sameRow(r,recorded[i]))){
  let i=0;while(i<recorded.length&&i<expected.length&&sameRow(recorded[i],expected[i]))i++;
  const session=i<recorded.length?recorded[i][1]:(i<expected.length?expected[i][1]:dates[dates.length-1]);
  out.price_revised={session,row:i};codes.push('PRICE_REVISED');
 }
 const contInput={...input,resume:state},cont=engine().runLedger(config,contInput);
 if(cont.state==='NOT_STARTED'&&cont.reason_codes.length===1&&cont.reason_codes[0]==='NO_SESSION_AFTER_RECORDED'){out.reason_codes=codes;return{status:out,input};}
 if(cont.state!=='OK'){out.state=cont.state;out.reason_codes=[...codes,...cont.reason_codes];return{status:out,input};}
 const sessions=cont.days.map(d=>d.date),missing=sessions.filter(d=>through!==null&&d<=through);
 out.missing=missing;out.append_rows=ledgerRows(ledger.id,cont,contInput,missing);
 if(!missing.length&&sessions.length)codes.push('WAITING_FOR_QG_RECORD');
 out.reason_codes=codes;
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
// Meta rows for a new Set A version / user set / shadow ledger: LEDGER_CLOSE of the open one (if any) then LEDGER_START.
function replaceRows(meta,kind,now,config,payload,recordedLast=null,reason='INITIAL'){
 const old=active(meta,kind),begin=beginFor(now,config,old?recordedLast:null),fresh={id:nextId(meta,kind),kind,begin},rows=[];
 if(old)rows.push(closeRow(now,old,begin,{next:fresh.id,reason}));
 const body={...payload,reason};if(old)body.previous=old.id;
 rows.push(startRow(now,fresh,config,body));
 return rows;
}
/* Changing Set A's composition: the v1.1 example (implicit set_a, TARGET v0) is first stored as it was, then closed, and
   the new version set_a@vN starts (its own ledger; earlier versions and their rows stay viewable). */
function setAChangeRows(meta,base,now,config,payload,recordedLast=null){
 const rows=[];let current=meta;
 if(!meta.ledgers.some(l=>l.kind==='SET_A')){
  const implicit=setALedger(meta,base,config),start=startRow(now,implicit,config,{reason:'INITIAL',target_basis:'TARGET_V0',target_weights:implicit.target_weights});
  rows.push(start);const parsed=parseMeta([start]);if(parsed.state!=='OK')fail('META_INVALID');current={...parsed,ledgers:[...meta.ledgers,...parsed.ledgers]};
 }
 return[...rows,...replaceRows(current,'SET_A',now,config,{...payload,target_basis:'SET_A'},recordedLast,'SET_A_CHANGED')];
}
// Deleting a user set only closes its open ledger ('종료', SET_DELETED); its rows and definition are kept.
function deleteRows(meta,kind,now,config,recordedLast=null){
 const old=active(meta,kind);if(!old)fail('SET_NOT_DEFINED');
 return[closeRow(now,old,beginFor(now,config,recordedLast),{reason:'SET_DELETED'})];
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
// All ledgers (Set A implicit until first recorded, closed ones included) continued from their recorded state.
function statuses(sheet,result,config){
 if(!sheet||sheet.state!=='READY')return{state:'SHEET_NOT_READY',reason_codes:sheet?sheet.reason_codes:['SHEET_NOT_LOADED'],ledgers:[],inputs:{},through:null};
 if(!result||result.state!=='READY'||!result.ledgers||!result.ledgers.SET_A||result.ledgers.SET_A.state!=='READY')
  return{state:'INPUTS_NOT_READY',reason_codes:result&&result.reason_codes&&result.reason_codes.length?[...result.reason_codes]:['INPUTS_NOT_READY'],ledgers:[],inputs:{},through:null};
 const base=sheetBase(result,sheet),through=recordableThrough(base),ledgers=allLedgers(sheet.meta,base,config);
 const out={state:'READY',reason_codes:[],ledgers:[],inputs:{},through,defs:{},incomplete:inputsIncomplete(result)};
 for(const led of ledgers){const{status,input}=ledgerStatus(led,base,sheet.rows[led.id]||[],config,through);out.ledgers.push(status);out.inputs[led.id]=input;out.defs[led.id]=led;}
 return out;
}
/* Runner result → the same result with Set A / user sets / shadow inputs taken from the stored ledger definitions, so the
   report shows exactly what is (or will be) recorded. A user set without an open definition is not defined; the shadow
   ledger without a stored ledger keeps the runner's preview (the user's own target) or, without a target, NA. */
function apply(result,sheet){
 if(!result||result.state!=='READY'||!sheet||sheet.state!=='READY'||!result.ledgers.SET_A||result.ledgers.SET_A.state!=='READY')return result;
 const base=sheetBase(result,sheet),ledgers={...result.ledgers},meta=sheet.meta;
 const put=(kind,led)=>{const d=deriveInput(base,led);ledgers[kind]=d.state==='READY'?{state:'READY',reason_codes:[],input:d.input}:{state:NA,reason_codes:d.reason_codes,input:null};};
 const a=active(meta,'SET_A');if(a)put('SET_A',a);
 for(const k of USER_SETS){const led=active(meta,k);if(led)put(k,led);else ledgers[k]={state:NA,reason_codes:[k==='SET_B'?'SET_B_NOT_DEFINED':'SET_NOT_DEFINED'],input:null};}
 const s=active(meta,'SHADOW');
 if(s)put('SHADOW',s);
 else if(!meta.user_target)ledgers.SHADOW={state:NA,reason_codes:['TARGET_NOT_AVAILABLE'],input:null};
 return{...result,ledgers};
}
// Open definitions for the report tabs and the comparison (ids, purposes, weights only).
function definitions(sheet,catalog){
 const meta=sheet&&sheet.state==='READY'?sheet.meta:{ledgers:[],user_target:null},out={};
 const a=active(meta,'SET_A');
 out.SET_A=a?{id:a.id,kind:'SET_A',basis:a.target_basis,weights:{...a.target_weights},purpose:a.purpose||null,example:a.target_basis==='TARGET_V0'}
  :{id:'set_a',kind:'SET_A',basis:'TARGET_V0',weights:catalogWeights(catalog),purpose:null,example:true};
 for(const k of USER_SETS){const led=active(meta,k);out[k]=led?{id:led.id,kind:k,basis:led.target_basis,weights:{...led.target_weights},purpose:led.purpose||null,example:false}:null;}
 out.closed=meta.ledgers.filter(l=>l.end!==null&&l.kind!=='SHADOW').map(l=>({id:l.id,kind:l.kind,begin:l.begin,end:l.end,close_reason:l.close_reason||null,purpose:l.purpose||null}));
 out.count=1+USER_SETS.filter(k=>out[k]).length;
 return out;
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
// Example_* tabs are never read (GoogleSheetQuotes drops them from the title list; this check keeps it local too).
const ignoredTab=t=>typeof t==='string'&&t.startsWith('Example_');
async function load(session,id){
 const titles=(await session.sheetTitles(id)).filter(t=>!ignoredTab(t)),values={};
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
const SCOPES=Object.freeze({MOCK:['SET_A','SET_B','SET_C','SET_D'],REAL:['SHADOW']});
// A rehearsal result (mode REHEARSAL, a rehearsal block, or any Q·G filled from today's public screen) is never recorded.
const rehearsalResult=r=>!!r&&(r.mode==='REHEARSAL'||(r.rehearsal!==undefined&&r.rehearsal!==null&&r.rehearsal!==false)||(Array.isArray(r.qg_filled)&&r.qg_filled.length>0));
/* "장부 시트에 기록": fresh read → continue each ledger of the scope from its recorded state → append the missing sessions.
   Recording mode only: the canonical engine config, sessions on/after the start date, never a rehearsal result. A replay
   that differs from the recorded rows only marks PRICE_REVISED; malformed rows still block. */
async function record(session,id,{result,kind,now=nowIso(),rehearsal=false,cryptoImpl=null}){
 const VT=engine(),cfg=VT.defaultConfig();
 if(rehearsal===true||rehearsalResult(result))fail('REHEARSAL_NOT_RECORDED');
 if(cfg.start_date!==VT.CONFIG.start_date||cfg.config_version!==VT.CONFIG.config_version)fail('CONFIG_NOT_CANONICAL');
 const sheet=await load(session,id);if(sheet.state!=='READY')fail(sheet.reason_codes[0]);
 const st=statuses(sheet,result,cfg);if(st.state!=='READY')fail(st.reason_codes[0]||st.state);
 const scope=st.ledgers.filter(s=>SCOPES[kind].includes(s.kind));
 if(scope.some(s=>s.state==='SHEET_ROWS_INVALID'))fail('SHEET_ROWS_INVALID');
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
const lastRecorded=(sheet,led)=>led&&sheet.rows[led.id]?recordedDates(sheet.rows[led.id]).pop()||null:null;
// User set B/C/D definition: closes the open ledger of that set (if any) and starts a new one from the next session.
async function saveSet(session,id,kind,weights,purpose,{now=nowIso()}={}){
 if(!USER_SETS.includes(kind))fail('INVALID');
 const cfg=engine().defaultConfig(),v=validateSet(weights,purpose,kind,Object.keys(members()));if(v.state!=='OK')fail(v.reason_codes[0]);
 const sheet=await load(session,id);if(sheet.state!=='READY')fail(sheet.reason_codes[0]);
 const old=active(sheet.meta,kind),reason=old?(kind==='SET_B'?'SET_B_REDEFINED':'SET_REDEFINED'):'INITIAL';
 const rows=replaceRows(sheet.meta,kind,now,cfg,{target_basis:kind,target_weights:v.weights,purpose:v.purpose},lastRecorded(sheet,old),reason);
 await ensureTabs(session,id,sheet);await session.appendRows(id,"'"+META+"'!A1",rows);return rows;
}
async function saveSetB(session,id,weights,{now=nowIso(),purpose=null}={}){return saveSet(session,id,'SET_B',weights,purpose,{now});}
// Deleting a user set marks it '종료' (LEDGER_CLOSE, SET_DELETED); its rows stay.
async function deleteSet(session,id,kind,{now=nowIso()}={}){
 if(!USER_SETS.includes(kind))fail('INVALID');
 const cfg=engine().defaultConfig(),sheet=await load(session,id);if(sheet.state!=='READY')fail(sheet.reason_codes[0]);
 const rows=deleteRows(sheet.meta,kind,now,cfg,lastRecorded(sheet,active(sheet.meta,kind)));
 await ensureTabs(session,id,sheet);await session.appendRows(id,"'"+META+"'!A1",rows);return rows;
}
// Set A composition change: a new version (set_a@vN) with its own ledger; the v1.1 example and earlier versions are kept.
async function saveSetA(session,id,weights,{now=nowIso(),purpose=null,catalog=null}={}){
 const cfg=engine().defaultConfig(),v=validateSet(weights,purpose,'SET_A',Object.keys(members()));if(v.state!=='OK')fail(v.reason_codes[0]);
 const sheet=await load(session,id);if(sheet.state!=='READY')fail(sheet.reason_codes[0]);
 const example=catalogWeights(catalog);if(!sheet.meta.ledgers.some(l=>l.kind==='SET_A')&&!example)fail('TARGET_CATALOG_INVALID');
 const payload={target_weights:v.weights};if(v.purpose)payload.purpose=v.purpose;
 const rows=setAChangeRows(sheet.meta,{target_weights:example||{}},now,cfg,payload,lastRecorded(sheet,active(sheet.meta,'SET_A')));
 await ensureTabs(session,id,sheet);await session.appendRows(id,"'"+META+"'!A1",rows);return rows;
}
async function saveTarget(session,id,weights,{now=nowIso()}={}){
 const v=validateWeights(weights,Object.keys(members()));if(v.state==='INVALID')fail(v.reason_codes[0]);
 if(v.state==='OK'&&Object.keys(v.weights).length>MAX_MEMBERS)fail('SET_MEMBERS_OVER_30');
 await appendMeta(session,id,[targetRow(now,v.weights)]);return v;
}
// "[세트 A 목표를 내 목표로 복사]": Set A's current target weights (stored version or the v1.1 example) → USER_TARGET row.
async function copySetATarget(session,id,{now=nowIso(),catalog=null}={}){
 const sheet=await load(session,id);if(sheet.state!=='READY')fail(sheet.reason_codes[0]);
 const a=active(sheet.meta,'SET_A'),weights=a?a.target_weights:catalogWeights(catalog);if(!weights)fail('TARGET_CATALOG_INVALID');
 await ensureTabs(session,id,sheet);await session.appendRows(id,"'"+META+"'!A1",[targetRow(now,{...weights})]);return weights;
}
/* Shadow start snapshot (D-17) from the device's current ACTUAL holdings: quantities, average costs and currencies;
   the KRW cost follows the runner's FX rule at the ledger's first session. reason RESYNC closes the open shadow ledger
   ("실제 보유로 다시 맞추기"); its recorded rows stay as they are. The target is the user's own target only (decision
   2026-10-11): without it the shadow ledger is TARGET_NOT_AVAILABLE, TARGET v0 is never substituted. */
async function startShadow(session,id,holdings,{now=nowIso(),resync=false}={}){
 const cfg=engine().defaultConfig(),positions={};
 const raw=object(holdings)&&object(holdings.positions)?holdings.positions:{};
 for(const cid of Object.keys(raw).sort()){const p=raw[cid];if(own(targets(),cid)&&object(p)&&num(p.quantity)&&p.quantity>0)positions[cid]={quantity:p.quantity,average_cost:p.average_cost,currency:p.currency};}
 if(!Object.keys(positions).length)fail('NO_ACTUAL');
 if(Object.values(positions).some(p=>!(num(p.average_cost)&&p.average_cost>=0&&CURRENCIES.includes(p.currency))))fail('ACTUAL_INVALID');
 const sheet=await load(session,id);if(sheet.state!=='READY')fail(sheet.reason_codes[0]);
 const old=active(sheet.meta,'SHADOW');if(resync!==!!old)fail(old?'SHADOW_ALREADY_STARTED':'SHADOW_NOT_STARTED');
 const user=sheet.meta.user_target;if(!user)fail('TARGET_NOT_AVAILABLE');
 const rows=replaceRows(sheet.meta,'SHADOW',now,cfg,{target_basis:'USER_TARGET',target_weights:user,
  snapshot:{effective_at:now,source_effective_at:typeof holdings.effective_at==='string'?holdings.effective_at:null,positions}},lastRecorded(sheet,old),resync?'RESYNC':'INITIAL');
 await ensureTabs(session,id,sheet);await session.appendRows(id,"'"+META+"'!A1",rows);return rows;
}

/* ---------- S17 cards ---------- */
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const KIND_KO={SET_A:'세트 A',SET_B:'세트 B',SET_C:'세트 C',SET_D:'세트 D',SHADOW:'그림자 장부'};
const BASIS_KO={TARGET_V0:'v1.1 예시(TARGET v0)',SET_A:'세트 A 사용자 구성',SET_B:'세트 B 구성',SET_C:'세트 C 구성',SET_D:'세트 D 구성',USER_TARGET:'내 목표(TARGET)'};
const STATE_KO={OK:'기록된 상태에서 이어서 계산',NOT_AVAILABLE:'NOT_AVAILABLE',NOT_STARTED:'시작 전',SHEET_ROWS_INVALID:'SHEET_ROWS_INVALID · 기록 행 형식 오류(쓰기 중지)'};
const SHEET_KO={NOT_CONNECTED:'구글 로그인과 시트 연결이 필요합니다(설정 → Google 첫 설정).',LOADING:'내 시트의 가상 장부를 읽는 중',READY:'내 시트 가상 장부 읽음',ERROR:'시트 장부를 쓸 수 없습니다'};
const memberNote=()=>'구성 종목은 비공개 가격 Worker가 시세를 줄 수 있는 종목(앱 허용 목록: TARGET 19종목 + ETF 15종)에서만 고를 수 있습니다. 다른 종목은 Worker 허용 목록 변경이 먼저 필요하며 이 화면에서는 추가할 수 없습니다. ETF에는 공개 Q·G가 없어 '+engine().label('BLOCK')+'(가상 거래 없음)으로 표시됩니다.';
// TARGET v0 weights from the public catalog: Set A's v1.1 example.
function catalogWeights(catalog){const t=runner().catalogTargets(catalog);return t?Object.fromEntries(t.map(x=>[x.cid,x.weight])):null;}
function catalogRows(catalog){
 const ids=runner().IDS;try{return catalog.instruments.map(r=>({cid:ids[r.row_index],ticker:r.ticker,label:r.label,target:r.target_units/100})).filter(r=>r.cid);}catch(_){return ids.map(cid=>({cid,ticker:runner().TARGETS[cid],label:cid,target:null}));}
}
// Every allowlisted member: the 19 TARGET companies, then the ETFs (no public Q·G).
function memberRows(catalog){return[...catalogRows(catalog),...Object.entries(runner().ETF_MEMBERS).map(([cid,t])=>({cid,ticker:t,label:t+' · ETF',target:null,etf:true}))];}
function weightForm(kind,rows,current,{title,note,save,connected,purpose=null,withPurpose=false,extra=''}){
 const sum=Object.values(current||{}).reduce((a,v)=>a+v,0);
 let h='<section class="card" data-weight-form="'+kind+'" data-weight-state="'+(current?'OK':NA)+'"><h2>'+esc(title)+'</h2><p class="small">'+esc(note)+'</p>';
 if(withPurpose)h+='<label class="small" for="purpose-'+kind+'">목적 (한 줄, 필수)</label><input type="text" id="purpose-'+kind+'" maxlength="'+MAX_PURPOSE+'" data-set-purpose="'+kind+'" value="'+esc(purpose||'')+'">';
 h+='<div class="table-wrap"><table><thead><tr><th>종목</th><th>목표 %</th></tr></thead><tbody>'+rows.map(r=>'<tr'+(r.etf?' data-etf':'')+'><td>'+esc(r.label+' ('+r.ticker+')')+'</td><td><input type="text" inputmode="decimal" size="6" aria-label="'+esc(r.ticker+' 목표 %')+'" data-weight="'+esc(r.cid)+'" value="'+esc(current&&own(current,r.cid)?String(current[r.cid]):'')+'"></td></tr>').join('')+'</tbody></table></div>';
 h+='<p data-weight-sum>'+esc(current?'합계 '+(Math.round(sum*10000)/10000)+'% · '+Object.keys(current).length+'종목 · 나머지는 가상 현금':'NOT_AVAILABLE · 구성 없음')+'</p>';
 h+='<div class="sheet-actions"><button type="button" data-weight-save="'+kind+'"'+(connected?'':' disabled')+'>'+esc(save)+'</button>'+extra+'</div><p role="status" class="small" data-weight-status="'+kind+'"></p></section>';
 return h;
}
function ledgerLine(s,def){
 const parts=[KIND_KO[s.kind]+' '+s.id,'출발 '+s.begin+(s.end?' · 종료 '+s.end:''),'목표 기준 '+(BASIS_KO[s.target_basis]||s.target_basis),
  s.recorded_sessions?'기록 '+s.recorded_sessions+'거래일(~'+s.recorded_through+')':'기록 없음',STATE_KO[s.state]||engine().codeText(s.state)];
 if(s.price_revised)parts.push(engine().codeText('PRICE_REVISED')+' · 첫 차이 '+s.price_revised.session);
 const rest=s.reason_codes.filter(c=>c!=='PRICE_REVISED'&&c!==s.state);if(rest.length)parts.push(engine().codesText(rest));
 if(s.inputs_changed)parts.push(engine().codeText('INPUTS_CHANGED'));
 return '<li data-ledger-id="'+esc(s.id)+'" data-ledger-check="'+esc(s.state)+'" data-price-revised="'+(s.price_revised?esc(s.price_revised.session):'')+'" data-ledger-missing="'+s.missing.length+'">'+esc(parts.join(' · '))+(def&&def.implicit?' <span class="small">(첫 기록 때 VirtualMeta에 정의)</span>':'')+'</li>';
}
function recordCard(ctx,state){
 const{sheet,st,busy,before,connected}=state,scope=SCOPES[ctx.kind==='REAL'?'REAL':'MOCK'];
 const list=st&&st.state==='READY'?st.ledgers.filter(s=>scope.includes(s.kind)):[];
 const missing=list.reduce((a,s)=>a+s.missing.length,0),invalid=list.some(s=>s.state==='SHEET_ROWS_INVALID'),revised=list.filter(s=>s.price_revised);
 const sheetState=!connected?'NOT_CONNECTED':!sheet?'LOADING':sheet.state;
 let h='<section class="card" data-ledger-sheets data-sheet-state="'+esc(sheetState)+'" data-ledger-invalid="'+(invalid?'1':'0')+'" data-ledger-revised="'+revised.length+'"><h2>가상 장부 시트 기록 '+engine().disclaimerHtml('ko-KR')+'</h2>';
 h+='<p data-ledger-sheet-summary>'+esc((SHEET_KO[sheetState]||sheetState)+(sheet&&sheet.state==='ERROR'?' · '+engine().codesText(sheet.reason_codes)+(sheet.tab?' ('+sheet.tab+')':''):''))+'</p>';
 if(before)h+='<p class="badge NOT_AVAILABLE" data-ledger-before-start>'+esc('가상매매 시작일 '+engine().CONFIG.start_date+' 전 · 기록하지 않음')+'</p>';
 else if(st&&st.state==='INPUTS_NOT_READY'&&connected&&sheet&&sheet.state==='READY')h+='<p class="small" data-ledger-inputs>'+esc('장부 입력 준비 전 · 이어서 계산 대기('+engine().codesText(st.reason_codes)+')')+'</p>';
 if(list.length)h+='<ul class="small" data-ledger-list>'+list.map(s=>ledgerLine(s,st.defs[s.id])).join('')+'</ul>';
 const incomplete=st&&st.state==='READY'?st.incomplete:[];
 if(incomplete.length)h+='<p class="small" data-ledger-incomplete>'+esc('INPUTS_INCOMPLETE · 시세를 다시 받은 뒤 기록합니다: '+incomplete.join(', '))+'</p>';
 if(revised.length)h+='<p class="badge STALE" data-ledger-price-revised>'+esc('PRICE_REVISED · 기록 이후 과거 일봉 등 입력이 바뀌어 처음부터 다시 계산한 값이 기록과 다릅니다('+revised.map(s=>s.id+' 첫 차이 '+s.price_revised.session).join(', ')+'). 기록은 고치지 않고, 기록된 현금·보유·주문에서 이어서 기록합니다.')+'</p>';
 if(invalid)h+='<p class="badge NOT_AVAILABLE" data-ledger-rows-invalid>SHEET_ROWS_INVALID · 기록된 행의 형식이 맞지 않아 이어서 계산할 수 없습니다. 시트에 쓰지 않습니다.</p>';
 if(missing)h+='<p data-missing-sessions>'+esc('기록할 거래일: '+list.flatMap(s=>s.missing.map(d=>s.id+' '+d)).join(', '))+'</p>';
 else if(st&&st.state==='READY')h+='<p class="small" data-missing-sessions="0">'+esc('기록할 새 거래일 없음'+(st.through?' · Q·G 기록 기준 ~'+st.through:' · Q·G 기록 대기'))+'</p>';
 const can=connected&&sheet&&sheet.state==='READY'&&!before&&!invalid&&!incomplete.length&&missing>0&&!busy;
 h+='<div class="sheet-actions"><button type="button" data-ledger-record'+(can?'':' disabled')+'>'+esc('장부 시트에 기록'+(missing?' ('+missing+'거래일)':''))+'</button></div>';
 h+='<p class="small">기록은 이 버튼을 누를 때만, 아직 기록하지 않은 거래일만 내 시트(VirtualA~D·VirtualMine·VirtualMeta)에 덧붙입니다. 기록한 행이 기준이며 고치지 않습니다. 다음 거래일은 기록된 마지막 상태(현금·보유·주문)에서 이어서 계산합니다. 가상 매수·가상 매도 하루 한도(D-15)는 세트마다 따로 적용됩니다. 시트에는 실제 숫자가 저장되고, 화면에는 날짜·개수·코드만 보입니다. 값이 없던 날은 엔진 결과(NOT_AVAILABLE·EXEC_*_MISSING)대로 기록하고 채우지 않습니다.</p>';
 h+='<p role="status" data-ledger-status></p></section>';
 return h;
}
function segmentsList(meta,kind){
 const segs=meta?meta.ledgers.filter(l=>l.kind===kind):[];if(!segs.length)return'';
 return '<ul class="small" data-set-segments="'+kind+'">'+segs.map(l=>'<li data-segment="'+esc(l.id)+'" data-segment-state="'+(l.end?'CLOSED':'OPEN')+'">'+esc(l.id+' · 출발 '+l.begin+(l.end?' · 종료 '+l.end+(l.close_reason==='SET_DELETED'?' (삭제 → 종료, 기록 보존)':''):' · 진행 중')+(l.purpose?' · 목적: '+l.purpose:'')+' · '+Object.keys(l.target_weights).length+'종목')+'</li>').join('')+'</ul>';
}
function setACard(state,rows){
 const meta=state.sheet&&state.sheet.state==='READY'?state.sheet.meta:null,a=meta?active(meta,'SET_A'):null,example=!a||a.target_basis==='TARGET_V0';
 const label=example?'세트 A · v1.1 예시':'세트 A · '+a.id+' (사용자 구성)';
 let h='<section class="card" data-set-card="SET_A" data-set-example="'+(example?'1':'0')+'"><h2>'+esc(label)+' <span class="badge">'+esc(example?'v1.1 예시':a.id)+'</span></h2>';
 h+='<p class="small">'+esc(example?'현재 세트 A는 포트폴리오 v1.1의 TARGET v0 비중을 쓰는 예시입니다. 구성을 바꾸면 새 버전(set_a@v2 …)으로 새 장부를 시작하고, 이전 장부와 성과는 종료 상태로 그대로 볼 수 있습니다.':'세트 A를 사용자가 바꾼 구성입니다. 다시 바꾸면 다음 버전으로 새 장부를 시작합니다.')+'</p>';
 h+=segmentsList(meta,'SET_A')+'</section>';
 h+=weightForm('SET_A',rows,a?a.target_weights:catalogWeights(state.catalog),{title:'세트 A 구성 변경 (새 버전 · 새 장부)',note:memberNote()+' 1~30종목, 합계 100 이하. 저장하면 다음 거래일부터 새 장부로 기록됩니다.',save:'세트 A 새 버전 저장',connected:state.connected&&!!meta&&!state.busy});
 return h;
}
function userSetCard(kind,state,rows){
 const meta=state.sheet&&state.sheet.state==='READY'?state.sheet.meta:null,led=meta?active(meta,kind):null,name=KIND_KO[kind];
 let h='<section class="card" data-set-card="'+kind+'" data-set-state="'+(led?'OPEN':'NOT_DEFINED')+'"><h2>'+esc(name+' (사용자 정의)')+'</h2>';
 h+='<p data-set-purpose-shown>'+esc(led?'목적: '+(led.purpose||'(기록된 목적 없음)')+' · 장부 '+led.id+' · 출발 '+led.begin:'NOT_AVAILABLE · 구성 없음')+'</p>';
 h+=segmentsList(meta,kind)+'</section>';
 const del=led?'<button type="button" data-set-delete="'+kind+'"'+(state.connected&&!state.busy?'':' disabled')+'>'+esc(name+' 종료(삭제)')+'</button>':'';
 h+=weightForm(kind,rows,led?led.target_weights:null,{title:name+' 구성',note:memberNote()+' 1~30종목, 합계 100 이하, 나머지는 가상 현금. 저장하면 내 시트 VirtualMeta에 새 장부로 기록되고 다음 거래일부터 적용됩니다(이전 장부와 기록은 보존). 삭제는 종료로만 표시하고 기록은 지우지 않습니다.',
  save:name+' 구성 저장',connected:state.connected&&!!meta&&!state.busy,purpose:led?led.purpose:'',withPurpose:true,extra:del});
 return h;
}
function shadowCard(state){
 const{sheet,connected}=state,meta=sheet&&sheet.state==='READY'?sheet.meta:null,open=meta?active(meta,'SHADOW'):null;
 const user=meta?meta.user_target:null,basis=open?open.target_basis:(user?'USER_TARGET':null);
 let h='<section class="card" data-shadow-ledger data-shadow-state="'+(open?'STARTED':'NOT_STARTED')+'"><h2>그림자 장부 출발 스냅샷 <span class="badge">D-17</span></h2>';
 h+='<p data-target-basis="'+esc(basis||NA)+'">'+esc(basis?'목표 기준: '+BASIS_KO[basis]+(open?' · 장부 '+open.id+' 출발 '+open.begin:' · 출발 스냅샷 없음(화면은 기기 보유 기준 미리보기, 기록 안 함)'):'NOT_AVAILABLE · 내 목표가 없습니다. 그림자 장부는 TARGET v0로 대신하지 않습니다. 위 \'내 목표\'를 설정하거나 세트 A 목표를 복사하세요.')+'</p>';
 if(open&&user&&canonical(user)!==canonical(open.target_weights))h+='<p class="small" data-target-pending>'+esc('저장한 내 목표는 \'실제 보유로 다시 맞추기\' 뒤 새 장부부터 적용됩니다. 현재 장부는 출발 때의 목표를 유지합니다.')+'</p>';
 const segs=meta?meta.ledgers.filter(l=>l.kind==='SHADOW'):[];
 if(segs.length)h+='<ul class="small" data-shadow-segments>'+segs.map(l=>'<li data-segment="'+esc(l.id)+'">'+esc(l.id+' · 출발 '+l.begin+(l.end?' · 종료 '+l.end:' · 진행 중')+' · '+(l.reason==='RESYNC'?'다시 맞추기':'첫 출발')+' · 보유 '+Object.keys(l.snapshot.positions).length+'종목')+'</li>').join('')+'</ul>';
 const ready=connected&&meta&&!state.busy&&(open||user);
 h+='<div class="sheet-actions">'+(open?'<button type="button" data-shadow-resync'+(ready?'':' disabled')+'>실제 보유로 다시 맞추기</button>':'<button type="button" data-shadow-create'+(ready?'':' disabled')+'>실제 보유로 출발 스냅샷 만들기</button>')+'</div>';
 h+='<p class="small">현재 기기 실제 보유(수량·평균단가·통화)를 내 시트 VirtualMeta에 출발 스냅샷으로 저장합니다. 목표는 내 목표만 씁니다. 원화 원가는 장부 첫 거래일 이전 마지막 환율로 계산합니다. 그 뒤 그림자 장부는 실제 거래와 독립으로 움직입니다. 다시 맞추기는 현재 장부를 닫고 새 장부를 시작하며 이전 기록은 그대로 둡니다.</p>';
 h+='<p role="status" data-shadow-status></p></section>';
 return h;
}
function targetGuide(state){
 const meta=state.sheet&&state.sheet.state==='READY'?state.sheet.meta:null,user=meta?meta.user_target:null;
 let h='<section class="card" data-user-target-guide data-user-target-state="'+(user?'OK':NA)+'"><h2>내 목표 설정</h2>';
 h+='<p>'+esc(user?'내 목표가 저장되어 있습니다('+Object.keys(user).length+'종목). 그림자 장부는 이 목표를 씁니다.':'NOT_AVAILABLE · 내 목표가 없어 그림자 장부 판단을 계산하지 않습니다(TARGET v0로 대신하지 않음). 아래 표에 목표 비중을 넣고 저장하거나, 세트 A의 현재 목표를 복사하세요.')+'</p>';
 h+='<div class="sheet-actions"><button type="button" data-copy-set-a-target'+(state.connected&&meta&&!state.busy?'':' disabled')+'>세트 A 목표를 내 목표로 복사</button></div><p role="status" class="small" data-copy-status></p></section>';
 return h;
}

let carry=null; // status text carried into the next mount after a save re-renders the report
/* Report hook: mount(view, host, {kind, tab, reportDate, config, catalog: async () => catalog, refresh}) →
   {runnerOptions(), definitions(), update(result) → result for the report, dispose()}. */
function mount(view,host,ctx){
 const VT=engine(),cfg=VT.defaultConfig(),kind=ctx.kind==='REAL'?'REAL':'MOCK',tab=ctx.tab;
 const carried=carry&&carry.key===kind+'/'+tab?carry.notes:{};if(carry&&carry.key!==kind+'/'+tab)carry=null; // kept for repeated remounts of the same tab; cleared by the next action
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
  if(state.busy)return;carry=null;if(!isConnected()){say(statusSel,SHEET_KO.NOT_CONNECTED);return;}
  state.busy=true;paint();
  try{const text=await fn();state.busy=false;if(done){carry={key:kind+'/'+tab,notes:{[statusSel]:text}};done();return;}await reload();say(statusSel,text);}
  catch(e){state.busy=false;paint();say(statusSel,engine().codeText(errorCode(e)));}
 };
 const readForm=k=>{const out={};for(const input of host.querySelectorAll('[data-weight-form="'+k+'"] [data-weight]'))out[input.getAttribute('data-weight')]=input.value;return out;};
 const readPurpose=k=>{const n=host.querySelector('[data-set-purpose="'+k+'"]');return n?n.value:null;};
 function paint(){
  if(!live())return;
  const rows=catalogRows(state.catalog),all=memberRows(state.catalog);let h=recordCard(ctx,state);
  const meta=state.sheet&&state.sheet.state==='READY'?state.sheet.meta:null;
  if(kind==='MOCK'&&tab==='SET_A')h+=setACard(state,all);
  if(kind==='MOCK'&&USER_SETS.includes(tab))h+=userSetCard(tab,state,all);
  if(kind==='REAL'){
   h+=targetGuide(state);
   h+=weightForm('TARGET',[...rows,...all.filter(r=>r.etf)],meta?meta.user_target:null,{title:'내 목표(TARGET) · 비공개',note:'내 실제 포트폴리오의 목표 비중(%)입니다. 내 시트 VirtualMeta에만 저장되며 그림자 장부의 목표로 씁니다. 없으면 그림자 장부는 NOT_AVAILABLE입니다(TARGET v0로 대신하지 않음). 공식 TARGET v0는 바뀌지 않습니다.',save:'내 목표 저장',connected:state.connected&&!!meta&&!state.busy});
   h+=shadowCard(state);
  }
  host.innerHTML=h;
  for(const[sel,text]of Object.entries(state.notes)){const n=host.querySelector(sel);if(n)n.textContent=text;}
  const rec=host.querySelector('[data-ledger-record]');
  if(rec)rec.onclick=()=>void act('[data-ledger-status]',async()=>{const r=await record(session,sheetId(),{result:state.result,kind});return r.sessions?r.sessions+'거래일을 기록했습니다('+r.ledgers.join(', ')+').':'기록할 새 거래일이 없습니다.';});
  const sum=form=>{const k=form.getAttribute('data-weight-form'),v=validateWeights(readForm(k),Object.keys(members())),n=form.querySelector('[data-weight-sum]');
   if(n)n.textContent=v.state==='OK'?'합계 '+(Math.round(Object.values(v.weights).reduce((a,x)=>a+x,0)*10000)/10000)+'% · '+Object.keys(v.weights).length+'종목 · 나머지는 가상 현금':v.state===NA?'NOT_AVAILABLE · 구성 없음':engine().codeText(v.reason_codes[0]);form.setAttribute('data-weight-state',v.state);};
  // Typed values survive repaints (sheet reload, failed save) until a save succeeds.
  for(const form of host.querySelectorAll('[data-weight-form]')){const k=form.getAttribute('data-weight-form'),draft=state.drafts[k];
   if(draft){for(const input of form.querySelectorAll('[data-weight]'))input.value=own(draft.weights,input.getAttribute('data-weight'))?draft.weights[input.getAttribute('data-weight')]:'';const p=form.querySelector('[data-set-purpose]');if(p&&typeof draft.purpose==='string')p.value=draft.purpose;sum(form);}}
  for(const input of host.querySelectorAll('[data-weight],[data-set-purpose]'))input.oninput=()=>{const form=input.closest('[data-weight-form]'),k=form.getAttribute('data-weight-form');state.drafts[k]={weights:readForm(k),purpose:readPurpose(k)};sum(form);};
  const saved=k=>()=>{delete state.drafts[k];ctx.refresh();};
  for(const btn of host.querySelectorAll('[data-weight-save]')){const k=btn.getAttribute('data-weight-save');
   btn.onclick=()=>{const w=readForm(k),purpose=readPurpose(k),sel='[data-weight-status="'+k+'"]';
    if(k==='TARGET')void act(sel,async()=>{const v=await saveTarget(session,sheetId(),w);return v.state==='OK'?'내 목표를 저장했습니다.':'내 목표를 비웠습니다(NOT_AVAILABLE).';},saved(k));
    else if(k==='SET_A')void act(sel,async()=>{const rows=await saveSetA(session,sheetId(),w,{catalog:state.catalog});const last=rows[rows.length-1];return'세트 A 새 버전을 저장했습니다('+last[1]+', 출발 '+last[4]+'). 이전 장부는 종료로 보존됩니다.';},saved(k));
    else void act(sel,async()=>{const rows=await saveSet(session,sheetId(),k,w,purpose);const last=rows[rows.length-1];return KIND_KO[k]+' 구성을 저장했습니다('+last[1]+', 출발 '+last[4]+').';},saved(k));};}
  const del=host.querySelector('[data-set-delete]');
  if(del)del.onclick=()=>{const k=del.getAttribute('data-set-delete');if(view.confirm&&!view.confirm(KIND_KO[k]+'를 종료합니다. 기록과 정의는 지우지 않고 종료로 표시합니다.'))return;
   void act('[data-weight-status="'+k+'"]',async()=>{const rows=await deleteSet(session,sheetId(),k);return KIND_KO[k]+'를 종료했습니다('+rows[0][1]+', 종료 '+rows[0][5]+').';},saved(k));};
  const copy=host.querySelector('[data-copy-set-a-target]');
  if(copy)copy.onclick=()=>void act('[data-copy-status]',async()=>{const w=await copySetATarget(session,sheetId(),{catalog:state.catalog});return'세트 A 목표('+Object.keys(w).length+'종목)를 내 목표로 복사해 시트에 저장했습니다.';},saved('TARGET'));
  const shadow=async resync=>{
   if(resync&&view.confirm&&!view.confirm('현재 그림자 장부를 닫고 오늘 실제 보유로 새 장부를 시작합니다. 이전 기록은 그대로 보존됩니다.'))return;
   await act('[data-shadow-status]',async()=>{
    let holdings=null;try{const catalog=await ctx.catalog();holdings=runner().holdingsFromSnapshot(await view.DeviceActual.readHoldings(view,catalog),catalog);}catch(_){holdings=null;}
    if(!holdings)fail('NO_ACTUAL');
    const rows=await startShadow(session,sheetId(),holdings,{resync});return(resync?'다시 맞췄습니다: ':'출발 스냅샷을 저장했습니다: ')+rows[rows.length-1][1]+' · 출발 '+rows[rows.length-1][4];
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
  async runnerOptions(){const sheet=await loading;if(!sheet||sheet.state!=='READY')return{};const m=sheet.meta,def=k=>{const l=active(m,k);return l?{target_weights:{...l.target_weights}}:null;};
   return{sets:{SET_A:def('SET_A'),SET_B:def('SET_B'),SET_C:def('SET_C'),SET_D:def('SET_D')},user_target:m.user_target?{...m.user_target}:null,flags:sheet.flags};},
  async definitions(){const sheet=await loading;let catalog=state.catalog;if(!catalog){try{catalog=await ctx.catalog();}catch(_){catalog=null;}}return definitions(sheet,catalog);},
  update(result){state.result=result;void recompute();return apply(result,state.sheet);},
  dispose
 });
}

return Object.freeze({SCHEMA,CODES,TABS,META,FLAGS,LEDGER_HEAD,META_HEAD,FLAGS_HEAD,HEADS,ALL_TABS,USER_SETS,MAX_MEMBERS,MAX_PURPOSE,numStr,canonical,dayRows,ledgerRows,parseTab,groupLedgerRows,recordedDates,
 recordedState,purposeOk,parseMeta,active,setALedger,allLedgers,nextId,validateWeights,validateSet,parseFlags,recordableThrough,deriveInput,truncate,inputsText,ledgerStatus,startRow,closeRow,recordRow,targetRow,
 beginFor,replaceRows,setAChangeRows,deleteRows,sheetState,statuses,apply,definitions,inputsIncomplete,load,ensureTabs,record,saveSet,saveSetB,saveSetA,deleteSet,saveTarget,copySetATarget,startShadow,sha256,mount});
});
