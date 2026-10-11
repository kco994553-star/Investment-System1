/* Virtual trading rules v1 (PROVISIONAL): deterministic daily replay of one virtual ledger, RAM only.
   Port of qgv/virtual_trading.py (vectors: tests/fixtures/virtual_trading_reference_v1.json). Prices, ledgers and P&L are
   arguments and results only: nothing here fetches, stores or sends them. A virtual buy/sell is a rule record, not an order. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.VirtualTrading=api;})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
const CONFIG=Object.freeze(JSON.parse('{"schema_version":1,"config_version":"virtual_trading/v1-provisional","rules_version":"virtual_trading_rules/v1","status":"PROVISIONAL_UNCALIBRATED","role":"RAM_ONLY_DEVICE","decided_at":"2026-10-11","start_date":"2026-10-19","base_currency":"KRW","daily_deposit":1000000,"buy_limit":1000000,"sell_limit":1000000,"execution":"NEXT_SESSION_CLOSE","cost_bps":0,"fractional_quantity":true,"band_pp":1,"qg_decline_threshold":5,"min_trade":10000,"abnormal_drop":{"window_sessions":20,"lookback_sessions":252,"k":2},"sector_basis":"SECTOR_ETF_CONFIRMED","macro_gate":"INACTIVE_MAPPING_PENDING","v_slope":{"lookback_sessions":20,"threshold":10},"benchmark":"SP500","hit_windows":[5,20,63],"hit_min_samples":30,"total_score":"TYPE_WEIGHTED_QGV_ELSE_QG","provenance":{"start_date":"D-13 DECIDED_2026-10-11","daily_deposit":"D-1 PROVISIONAL","buy_limit":"D-15 DECIDED_2026-10-10","sell_limit":"D-15 DECIDED_2026-10-10","execution":"D-2 PROVISIONAL","cost_bps":"D-3 PROVISIONAL","fractional_quantity":"D-4 PROVISIONAL","abnormal_drop":"D-5 PROVISIONAL","macro_gate":"D-6 PROVISIONAL","band_pp":"D-7 PROVISIONAL","qg_decline_threshold":"D-8 PROVISIONAL","min_trade":"D-9 PROVISIONAL","benchmark":"D-11 PROVISIONAL","hit_min_samples":"D-12 PROVISIONAL","total_score":"D-14 PROVISIONAL","v_slope":"D-21 PROVISIONAL","sector_basis":"D-22 DECIDED_2026-10-11 (sector_etf_map/v1)"}}'));
const LEDGER_KINDS=['SET_A','SET_B','SET_C','SET_D','SHADOW'],COVERAGES=['READY','PARTIAL','BLOCKED'],FLAG_KINDS=['HOLD','EXCLUDE','CONFIRMED_TEMPORARY','CONFIRMED_STRUCTURAL','CLEAR'],EVENT_KINDS=['EARNINGS_WINDOW','TYPE_CHANGED'];
const LEVELS=Object.freeze(['BLOCK','RISK_RECHECK','REDUCE_REVIEW','INCREASE_REVIEW','ADDITIONAL_REVIEW','HOLDING_CONTEXT','OBSERVE']);
const SYMBOLS=Object.freeze({BLOCK:'■',RISK_RECHECK:'▼',REDUCE_REVIEW:'▼',INCREASE_REVIEW:'▲',ADDITIONAL_REVIEW:'●',HOLDING_CONTEXT:'●',OBSERVE:'●'});
const SP500='SP500';
const has=(o,k)=>o!==null&&typeof o==='object'&&Object.prototype.hasOwnProperty.call(o,k);
const get=(o,k)=>has(o,k)?o[k]:undefined;
const obj=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
const num=v=>typeof v==='number'&&Number.isFinite(v),pos=v=>num(v)&&v>0,int=v=>Number.isInteger(v);
function day(v){if(!(typeof v==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(v)))return false;const m=+v.slice(5,7),d=+v.slice(8);return m>=1&&m<=12&&d>=1&&d<=31;}
function need(ok,code='INPUT_INVALID'){if(!ok)throw new Error(code);}
function validateConfig(c){
 need(obj(c)&&c.schema_version===1&&c.rules_version==='virtual_trading_rules/v1','CONFIG_INVALID');
 need(c.start_date===null||c.start_date===undefined||day(c.start_date),'CONFIG_INVALID');
 for(const k of ['daily_deposit','buy_limit','sell_limit','min_trade','band_pp','qg_decline_threshold'])need(num(c[k])&&c[k]>=0,'CONFIG_INVALID');
 need(num(c.cost_bps)&&c.cost_bps>=0&&c.cost_bps<10000,'CONFIG_INVALID');
 need(c.execution==='NEXT_SESSION_CLOSE'&&c.fractional_quantity===true,'CONFIG_INVALID');
 const a=c.abnormal_drop,s=c.v_slope;
 need(obj(a)&&int(a.window_sessions)&&a.window_sessions>0&&int(a.lookback_sessions)&&a.lookback_sessions>1&&pos(a.k),'CONFIG_INVALID');
 need(obj(s)&&int(s.lookback_sessions)&&s.lookback_sessions>0&&pos(s.threshold),'CONFIG_INVALID');
 need(Array.isArray(c.hit_windows)&&c.hit_windows.every(w=>int(w)&&w>0)&&int(c.hit_min_samples)&&c.hit_min_samples>0,'CONFIG_INVALID');
 need(['SP500_SUBSTITUTE_D22_PENDING','SECTOR_ETF_CONFIRMED'].includes(c.sector_basis),'CONFIG_INVALID');
 return c;
}
function series(v){need(obj(v)&&Object.entries(v).every(([k,x])=>day(k)&&pos(x)));return v;}
function validateLedger(L){
 need(obj(L)&&LEDGER_KINDS.includes(L.kind)&&typeof L.id==='string'&&L.id.length>0);
 const ss=L.sessions;need(Array.isArray(ss)&&ss.every(day));for(let i=0;i<ss.length-1;i++)need(ss[i]<ss[i+1]);
 const tw=L.target_weights;
 if(tw!==null&&tw!==undefined){need(obj(tw)&&Object.values(tw).every(v=>num(v)&&v>=0&&v<=100));let t=0;for(const k of Object.keys(tw).sort())t+=tw[k];need(t<=100+1e-9);}
 need(obj(L.companies));
 for(const c of Object.values(L.companies)){need(obj(c)&&typeof c.currency==='string'&&c.currency.length===3);series(c.closes);need(c.sector_benchmark===null||c.sector_benchmark===undefined||typeof c.sector_benchmark==='string');}
 const bm=has(L,'benchmarks')?L.benchmarks:{};need(obj(bm));for(const v of Object.values(bm))series(v);
 const fx=has(L,'fx')?L.fx:{};need(obj(fx));for(const v of Object.values(fx))series(v);
 const init=has(L,'initial')?L.initial:{cash:0,positions:{}};
 need(obj(init)&&num(init.cash)&&init.cash>=0&&obj(init.positions));
 for(const[cid,p]of Object.entries(init.positions))need(has(L.companies,cid)&&obj(p)&&pos(p.quantity)&&num(p.cost)&&p.cost>=0);
 const snaps=has(L,'snapshots')?L.snapshots:{};need(obj(snaps));
 for(const[d,rows]of Object.entries(snaps)){need(day(d)&&obj(rows));for(const r of Object.values(rows))need(obj(r)&&COVERAGES.includes(r.coverage)&&(r.q===null||r.q===undefined||num(r.q))&&(r.g===null||r.g===undefined||num(r.g)));}
 const vs=has(L,'v_scores')?L.v_scores:{};need(obj(vs)&&Object.entries(vs).every(([d,r])=>day(d)&&obj(r)&&Object.values(r).every(v=>v===null||num(v))));
 const vc=has(L,'v_composition')?L.v_composition:{};need(obj(vc)&&Object.entries(vc).every(([d,r])=>day(d)&&obj(r)&&Object.values(r).every(v=>v===null||typeof v==='string')));
 const flags=has(L,'flags')?L.flags:[];need(Array.isArray(flags)&&flags.every(f=>obj(f)&&day(f.date)&&FLAG_KINDS.includes(f.kind)&&typeof f.company==='string'));
 const ev=has(L,'events')?L.events:{};need(obj(ev)&&Object.entries(ev).every(([d,r])=>day(d)&&obj(r)&&Object.values(r).every(x=>Array.isArray(x)&&x.every(e=>EVENT_KINDS.includes(e)))));
 if(has(L,'resume')&&L.resume!==null&&L.resume!==undefined)validateResume(L.resume,L.companies);
 return L;
}
/* Recorded state to continue from (decision 2026-10-11): the recorded rows are canonical. Positions carry quantity and KRW
   cost; pending holds the virtual orders decided on the last recorded session (executed on the next one). */
function validateResume(r,comps){
 need(obj(r)&&day(r.after)&&num(r.cash)&&r.cash>=0&&obj(r.positions)&&(r.total_value===null||r.total_value===undefined||num(r.total_value))&&Array.isArray(r.pending));
 for(const[cid,p]of Object.entries(r.positions))need(has(comps,cid)&&obj(p)&&pos(p.quantity)&&num(p.cost));
 for(const o of r.pending)need(obj(o)&&typeof o.company==='string'&&(o.side==='BUY'||o.side==='SELL')&&pos(o.amount)&&Array.isArray(o.reason_codes)&&o.reason_codes.every(c=>typeof c==='string'));
}
function fxRate(L,ccy,d){if(ccy==='KRW')return 1;const s=get(L.fx||{},ccy);return s?get(s,d)??null:null;}
function lastOnOrBefore(s,d){let best=null;for(const k of Object.keys(s))if(k<=d&&(best===null||k>best))best=k;return best;}
function activeFlag(flags,cid,d){let found=null;for(const f of flags)if(f.company===cid&&f.date<=d&&(found===null||f.date>=found.date))found=f;return found===null||found.kind==='CLEAR'?null:found.kind;}
function qg(r){if(!r||r.q===null||r.q===undefined||r.g===null||r.g===undefined)return null;return (r.q+r.g)/2;}
function prevSnapshot(snaps,cid,d){let best=null;for(const[k,rows]of Object.entries(snaps))if(k<d&&has(rows,cid)&&(best===null||k>best))best=k;return best!==null?snaps[best][cid]:null;}
function abnormalDrop(closes,bench,d,cfg){
 const a=cfg.abnormal_drop,w=a.window_sessions,nLook=a.lookback_sessions,k=a.k;
 if(!bench)return{state:'NOT_AVAILABLE',reason:'SECTOR_BASIS_NOT_AVAILABLE'};
 let dates=Object.keys(closes).filter(x=>x<=d&&has(bench,x)).sort();
 if(!dates.length||dates[dates.length-1]!==d)return{state:'NOT_AVAILABLE',reason:'PRICE_NOT_ALIGNED'};
 const needN=nLook+w+1;if(dates.length<needN)return{state:'NOT_AVAILABLE',reason:'HISTORY_INSUFFICIENT'};
 dates=dates.slice(dates.length-needN);
 const ex=[];for(let j=w;j<dates.length;j++){const rs=closes[dates[j]]/closes[dates[j-w]]-1,rb=bench[dates[j]]/bench[dates[j-w]]-1;ex.push(rs-rb);}
 const current=ex[ex.length-1],sample=ex.slice(0,-1);
 let mean=0;for(const x of sample)mean+=x;mean=mean/sample.length;
 let v=0;for(const x of sample)v+=(x-mean)*(x-mean);const sd=Math.sqrt(v/(sample.length-1));
 if(!(sd>0))return{state:'NOT_AVAILABLE',reason:'DISTRIBUTION_DEGENERATE'};
 const z=(current-mean)/sd;return{state:z<-k?'ABNORMAL':'NORMAL',reason:null,z};
}
function sectorSeries(L,cid,cfg){const bm=L.benchmarks||{},key=cfg.sector_basis==='SECTOR_ETF_CONFIRMED'?L.companies[cid].sector_benchmark:null;if(key&&has(bm,key))return[bm[key],key];return[get(bm,SP500),SP500];}
function finish(levels,reasons,aux,held,target,actual){
 if(!levels.length)levels=[held?'HOLDING_CONTEXT':'OBSERVE'];
 const main=levels[0];return{main,symbol:SYMBOLS[main],aux_levels:levels.slice(1),aux,reason_codes:reasons,held,target_weight:target,actual_weight:actual};
}
function judge(L,cfg,cid,d,idx,state,total){
 const comp=get(L.companies,cid),p=get(state.positions,cid),held=p!==undefined,target=get(L.target_weights||{},cid)??0;
 const snaps=L.snapshots||{},flags=L.flags||[],reasons=[],aux=[],levels=new Set();
 const price=comp?get(comp.closes,d)??null:null,fx=comp?fxRate(L,comp.currency,d):null,snap=get(get(snaps,d)||{},cid)??null,flag=activeFlag(flags,cid,d);
 if(!comp||price===null)reasons.push('DATA_PRICE_MISSING');else if(fx===null)reasons.push('DATA_FX_MISSING');
 if(snap===null)reasons.push('DATA_SNAPSHOT_MISSING');else if(snap.coverage==='BLOCKED')reasons.push('COVERAGE_BLOCKED');
 if(flag==='EXCLUDE')reasons.push('USER_EXCLUDE');
 let actual=0;if(held&&price!==null&&fx!==null&&total>0)actual=p.quantity*price*fx/total*100;
 if(reasons.length)return[finish(['BLOCK'],reasons,aux,held,target,actual),null];
 const qgNow=qg(snap),prev=prevSnapshot(snaps,cid,d),qgPrev=qg(prev);let noTrade=false,sellAll=false;
 if(qgNow!==null&&qgPrev!==null&&qgPrev-qgNow>=cfg.qg_decline_threshold){levels.add('RISK_RECHECK');reasons.push('QG_DECLINE');sellAll=held;}
 if(prev!==null&&prev.coverage==='READY'&&snap.coverage==='PARTIAL'){levels.add('RISK_RECHECK');reasons.push('COVERAGE_WORSENED');noTrade=true;}
 if(flag==='HOLD'){levels.add('RISK_RECHECK');reasons.push('USER_HOLD');noTrade=true;}
 const[bench,basis]=sectorSeries(L,cid,cfg),drop=abnormalDrop(comp.closes,bench,d,cfg);
 if(basis===SP500&&cfg.sector_basis!=='SECTOR_ETF_CONFIRMED')aux.push('SECTOR_SP500_SUBSTITUTE');
 const vUsable=drop.state!=='NOT_AVAILABLE';if(!vUsable)reasons.push('RECHECK_BASIS_NOT_AVAILABLE');
 if(drop.state==='ABNORMAL'){
  if(flag==='CONFIRMED_TEMPORARY')reasons.push('USER_CONFIRMED_TEMPORARY');
  else{levels.add('RISK_RECHECK');reasons.push('RECHECK_ABNORMAL_DROP');noTrade=true;if(flag==='CONFIRMED_STRUCTURAL')reasons.push('USER_CONFIRMED_STRUCTURAL');}
 }
 let vUp=false,vDown=false;const lb=cfg.v_slope.lookback_sessions;
 if(vUsable&&idx-lb>=0){
  const past=L.sessions[idx-lb],vs=L.v_scores||{},vNow=get(get(vs,d)||{},cid)??null,vPast=get(get(vs,past)||{},cid)??null,qgPast=qg(get(get(snaps,past)||{},cid)??null);
  // V slope compares only days with the same V factor composition; unknown or different → no slope (NA).
  const vc=L.v_composition||{},compNow=get(get(vc,d)||{},cid)??null,compPast=get(get(vc,past)||{},cid)??null,same=typeof compNow==='string'&&compNow===compPast;
  if(vNow!==null&&vPast!==null&&!same)aux.push('V_COMPOSITION_CHANGED');
  if(same&&vNow!==null&&vPast!==null&&qgNow!==null&&qgPast!==null&&qgNow-qgPast>-cfg.qg_decline_threshold){
   if(vNow-vPast>=cfg.v_slope.threshold)vUp=true;else if(vPast-vNow>=cfg.v_slope.threshold)vDown=true;
  }
 }
 const band=cfg.band_pp,upper=vUp?target+band:target,lower=vDown?target-band:target;let desire=null;
 if(levels.has('RISK_RECHECK')){
  if(vUp)aux.push('INCREASE_CANDIDATE');if(held&&actual>target+band)aux.push('OVERWEIGHT');
  if(sellAll&&!noTrade)desire=['SELL',actual,['QG_DECLINE']];
 }else if(held&&actual>target+band){
  levels.add('REDUCE_REVIEW');reasons.push('OVERWEIGHT_GAP');if(vDown)reasons.push('V_DETERIORATED');
  desire=['SELL',actual-lower,vDown?['OVERWEIGHT_GAP','V_DETERIORATED']:['OVERWEIGHT_GAP']];
 }else if(held&&vDown&&actual>lower){
  levels.add('REDUCE_REVIEW');reasons.push('V_DETERIORATED');desire=['SELL',actual-lower,['V_DETERIORATED']];
 }else if(actual<target-band){
  levels.add('INCREASE_REVIEW');reasons.push('UNDERWEIGHT_GAP');if(vUp)reasons.push('V_IMPROVED');
  desire=['BUY',upper-actual,vUp?['UNDERWEIGHT_GAP','V_IMPROVED']:['UNDERWEIGHT_GAP']];
 }else if(vUp&&actual<upper&&target>0){
  levels.add('INCREASE_REVIEW');reasons.push('V_IMPROVED');desire=['BUY',upper-actual,['V_IMPROVED']];
 }else if(held)reasons.push('BAND_INSIDE');
 if(snap.coverage==='PARTIAL'){levels.add('ADDITIONAL_REVIEW');aux.push('COVERAGE_PARTIAL');}
 for(const e of get(get(L.events||{},d)||{},cid)||[]){levels.add('ADDITIONAL_REVIEW');aux.push(e);}
 if(desire!==null&&desire[1]<=0)desire=null;
 return[finish([...levels].sort((x,y)=>LEVELS.indexOf(x)-LEVELS.indexOf(y)),reasons,aux,held,target,actual),desire];
}
function allocate(cands,limit,cfg){
 let total=0;for(const c of cands)total+=c.desired;
 const out=[];
 for(const c of cands){
  let amt=total<=limit?c.desired:limit*c.desired/total;amt=Math.floor(amt);
  const codes=[...c.reason_codes];if(amt<Math.floor(c.desired))codes.push('LIMIT_EXHAUSTED');
  if(amt<cfg.min_trade||amt<=0)continue;
  out.push({company:c.company,side:c.side,amount:amt,reason_codes:codes});
 }
 return out;
}
function valueOf(L,state,d){
 let total=0;const stale=[];
 for(const cid of Object.keys(state.positions).sort()){
  const p=state.positions[cid],comp=L.companies[cid],cd=lastOnOrBefore(comp.closes,d);let rate=1,fd=d;
  if(comp.currency!=='KRW'){const fs=get(L.fx||{},comp.currency)||{};fd=lastOnOrBefore(fs,d);rate=fd!==null?fs[fd]:null;}
  if(cd===null||rate===null)return[null,[cid]];
  if(cd!==d||fd!==d)stale.push(cid);
  total+=p.quantity*comp.closes[cd]*rate;
 }
 return[total,stale];
}
function sortedEntries(o){const r={};for(const k of Object.keys(o).sort())r[k]=o[k];return r;}
function runLedger(config,ledger){
 const cfg=validateConfig(config);
 const base={ledger_id:obj(ledger)?(ledger.id??null):null,config_version:cfg.config_version??null,rules_version:cfg.rules_version,status:cfg.status??null,role:'RAM_ONLY_DEVICE'};
 const stop=(state,code)=>({...base,state,reason_codes:[code],days:[],trades:[],summary:null});
 if(cfg.start_date===null||cfg.start_date===undefined)return stop('NOT_STARTED','START_DATE_NOT_SET');
 let L;try{L=validateLedger(ledger);}catch(e){return stop('NOT_AVAILABLE',e.message);}
 if(L.target_weights===null||L.target_weights===undefined)return stop('NOT_AVAILABLE','TARGET_NOT_AVAILABLE');
 const resume=has(L,'resume')&&L.resume!==null&&L.resume!==undefined?L.resume:null,after=resume?resume.after:null;
 const first=L.sessions.findIndex(x=>x>=cfg.start_date&&(after===null||x>after));if(first<0)return stop('NOT_STARTED',resume?'NO_SESSION_AFTER_RECORDED':'NO_SESSION_ON_OR_AFTER_START');
 const init=has(L,'initial')?L.initial:{cash:0,positions:{}},src=resume||init;
 const state={cash:src.cash,positions:{}};for(const[k,v]of Object.entries(sortedEntries(src.positions)))state.positions[k]={quantity:v.quantity,cost:v.cost};
 const days=[],trades=[];let pending=[],deposits=0,realized=0,prevTotal=null,growth=1,initialValue;
 if(resume){
  // Continue from the recorded state: no re-valuation of the recorded day, its pending orders execute next.
  initialValue=resume.total_value??null;prevTotal=resume.total_value??null;
  pending=resume.pending.map(o=>({company:o.company,side:o.side,amount:o.amount,reason_codes:[...o.reason_codes],decided_on:after,user_flag:activeFlag(L.flags||[],o.company,after)}));
 }else{
  [initialValue]=valueOf(L,state,L.sessions[first]);if(initialValue===null)return stop('NOT_AVAILABLE','INITIAL_VALUE_NOT_AVAILABLE');
  initialValue+=state.cash;
 }
 const feeRate=cfg.cost_bps/10000;
 const universe=[...new Set([...Object.keys(L.target_weights),...Object.keys(init.positions),...Object.keys(state.positions)])].sort();
 for(let idx=first;idx<L.sessions.length;idx++){
  const d=L.sessions[idx],executed=[],cancelled=[];
  const ordered=[...pending].sort((a,b)=>{const sa=a.side==='SELL'?0:1,sb=b.side==='SELL'?0:1;return sa!==sb?sa-sb:(a.company<b.company?-1:a.company>b.company?1:0);});
  for(const o of ordered){
   const comp=get(L.companies,o.company),price=comp?get(comp.closes,d)??null:null,rate=comp?fxRate(L,comp.currency,d):null;
   if(price===null||rate===null){cancelled.push({...o,cancel_reason:price===null?'EXEC_PRICE_MISSING':'EXEC_FX_MISSING'});continue;}
   const unit=price*rate;let rec;
   if(o.side==='SELL'){
    const p=get(state.positions,o.company);if(p===undefined){cancelled.push({...o,cancel_reason:'NO_POSITION'});continue;}
    let qty=o.amount/unit;if(qty>=p.quantity)qty=p.quantity;
    const gross=qty*unit,fee=gross*feeRate,avg=p.cost/p.quantity,costOut=avg*qty,pnl=gross-fee-costOut;
    realized+=pnl;state.cash+=gross-fee;
    if(qty===p.quantity)delete state.positions[o.company];else{p.quantity-=qty;p.cost-=costOut;}
    rec={date:d,decided_on:o.decided_on,company:o.company,side:'SELL',amount:gross,quantity:qty,price,fx:rate,fee,realized_pnl:pnl,reason_codes:o.reason_codes,user_flag:o.user_flag};
   }else{
    const amount=o.amount<=state.cash?o.amount:state.cash;
    if(amount<cfg.min_trade||amount<=0){cancelled.push({...o,cancel_reason:'CASH_INSUFFICIENT'});continue;}
    const fee=amount*feeRate,qty=(amount-fee)/unit;
    if(!has(state.positions,o.company))state.positions[o.company]={quantity:0,cost:0};
    const p=state.positions[o.company];p.quantity+=qty;p.cost+=amount;state.cash-=amount;
    rec={date:d,decided_on:o.decided_on,company:o.company,side:'BUY',amount,quantity:qty,price,fx:rate,fee,realized_pnl:null,reason_codes:o.reason_codes,user_flag:o.user_flag};
   }
   executed.push(rec);trades.push(rec);
  }
  state.cash+=cfg.daily_deposit;deposits+=cfg.daily_deposit;
  const[posValue,stale]=valueOf(L,state,d),total=posValue===null?null:posValue+state.cash;
  if(total!==null&&prevTotal!==null&&prevTotal>0)growth=growth*((total-cfg.daily_deposit)/prevTotal);
  const judgements={},sells=[],buys=[];
  if(total!==null){
   for(const cid of universe){
    const[j,desire]=judge(L,cfg,cid,d,idx,state,total);judgements[cid]=j;if(desire===null)continue;
    const[side,pct,codes]=desire;let desired=pct/100*total;
    if(side==='SELL'){const p=state.positions[cid],c=L.companies[cid],heldValue=p.quantity*c.closes[d]*fxRate(L,c.currency,d);if(desired>heldValue)desired=heldValue;}
    (side==='SELL'?sells:buys).push({company:cid,side,desired,reason_codes:codes,user_flag:activeFlag(L.flags||[],cid,d)});
   }
  }
  const orders=[...allocate(sells,cfg.sell_limit,cfg),...allocate(buys,Math.min(cfg.buy_limit,state.cash),cfg)];
  const flagsBy={};for(const c of [...sells,...buys])flagsBy[c.company]=c.user_flag;
  pending=orders.map(o=>({...o,decided_on:d,user_flag:flagsBy[o.company]}));
  days.push({date:d,executed,cancelled,deposit:cfg.daily_deposit,cash:state.cash,positions_value:posValue,total_value:total,stale_valuation:stale,
   judgements,orders:pending.map(o=>({company:o.company,side:o.side,amount:o.amount,reason_codes:o.reason_codes}))});
  if(total!==null)prevTotal=total;
 }
 const last=days[days.length-1];let unrealized=null;
 if(last.positions_value!==null){let cost=0;for(const cid of Object.keys(state.positions).sort())cost+=state.positions[cid].cost;unrealized=last.positions_value-cost;}
 const invested=initialValue===null?null:initialValue+deposits;
 const summary={start_date:L.sessions[first],end_date:last.date,initial_value:initialValue,deposits,total_value:last.total_value,cash:state.cash,
  simple_return:last.total_value===null||invested===null||invested<=0?null:last.total_value/invested-1,twr:growth-1,realized_pnl:realized,unrealized_pnl:unrealized,
  buy_count:trades.filter(t=>t.side==='BUY').length,sell_count:trades.filter(t=>t.side==='SELL').length,
  user_flagged_count:trades.filter(t=>t.user_flag!==null&&t.user_flag!==undefined).length,pending_orders:last.orders};
 return{...base,state:'OK',reason_codes:[],days,trades,summary};
}
function evaluateHits(config,ledger,trades){
 const cfg=validateConfig(config),ss=ledger.sessions,at=new Map(ss.map((d,i)=>[d,i])),bench=get(ledger.benchmarks||{},SP500),out=[];
 for(const w of cfg.hit_windows){
  let samples=0,hits=0,pendingN=0,missing=0;
  for(const t of trades){
   const i=at.get(t.date);if(i===undefined||i+w>=ss.length){pendingN++;continue;}
   const end=ss[i+w],closes=ledger.companies[t.company].closes;
   if(!bench||!has(closes,t.date)||!has(closes,end)||!has(bench,t.date)||!has(bench,end)){missing++;continue;}
   const rs=closes[end]/closes[t.date]-1,rb=bench[end]/bench[t.date]-1;samples++;
   if((t.side==='BUY'&&rs>rb)||(t.side==='SELL'&&rs<rb))hits++;
  }
  const enough=samples>=cfg.hit_min_samples;
  out.push({window:w,samples,hits,pending:pendingN,missing,state:enough?'OK':'INSUFFICIENT_SAMPLE',hit_rate:enough?hits/samples:null});
 }
 return out;
}
/* ---------- D-19 vocabulary: the ONE source for level order, symbols, Korean/English names, chip tones, auxiliary chips,
   reason-code labels and the fixed disclaimer on every virtual-trading surface (S17 screen and template v1, S03 virtual
   card, ledger sheet card). Python keeps LEVELS/SYMBOLS only (tests/test_virtual_trading.py checks equality). ---------- */
const LABELS=Object.freeze({ko:Object.freeze({BLOCK:'차단',RISK_RECHECK:'위험재검토',REDUCE_REVIEW:'비중축소검토',INCREASE_REVIEW:'비중확대검토',ADDITIONAL_REVIEW:'추가검토',HOLDING_CONTEXT:'보유맥락',OBSERVE:'관찰'}),
 en:Object.freeze({BLOCK:'Blocked',RISK_RECHECK:'Risk re-check',REDUCE_REVIEW:'Review reducing weight',INCREASE_REVIEW:'Review adding weight',ADDITIONAL_REVIEW:'Further review',HOLDING_CONTEXT:'Holding context',OBSERVE:'Observe'})});
// Chip colour family per level (style.css .chip.vt[data-tone]); judgement colours differ from return colours (template §7.1).
const TONES=Object.freeze({BLOCK:'block',RISK_RECHECK:'risk',REDUCE_REVIEW:'reduce',INCREASE_REVIEW:'increase',ADDITIONAL_REVIEW:'review',HOLDING_CONTEXT:'neutral',OBSERVE:'neutral'});
// Directional auxiliary codes shown as chips next to the main judgement (template §7.3: `▼비중`, `▲확대 후보`).
const SIGNALS=Object.freeze({OVERWEIGHT:Object.freeze({level:'REDUCE_REVIEW',ko:'비중',en:'Weight'}),INCREASE_CANDIDATE:Object.freeze({level:'INCREASE_REVIEW',ko:'확대 후보',en:'Add candidate'})});
const DISCLAIMER=Object.freeze({ko:'가상 · 실제 추천 아님 · 주문 기능 없음',en:'Virtual · not a recommendation · no order function'});
// Every code the engine itself can emit, by family (the runner, signals, V history and ledger sheet modules export theirs).
const CODES=Object.freeze({
 judgement:Object.freeze(['DATA_PRICE_MISSING','DATA_FX_MISSING','DATA_SNAPSHOT_MISSING','COVERAGE_BLOCKED','USER_EXCLUDE','QG_DECLINE','COVERAGE_WORSENED','USER_HOLD','RECHECK_BASIS_NOT_AVAILABLE','RECHECK_ABNORMAL_DROP','USER_CONFIRMED_TEMPORARY','USER_CONFIRMED_STRUCTURAL','OVERWEIGHT_GAP','UNDERWEIGHT_GAP','V_IMPROVED','V_DETERIORATED','BAND_INSIDE']),
 aux:Object.freeze(['OVERWEIGHT','INCREASE_CANDIDATE','COVERAGE_PARTIAL','EARNINGS_WINDOW','TYPE_CHANGED','SECTOR_SP500_SUBSTITUTE','V_COMPOSITION_CHANGED']),
 order:Object.freeze(['LIMIT_EXHAUSTED']),
 execution:Object.freeze(['EXEC_PRICE_MISSING','EXEC_FX_MISSING','NO_POSITION','CASH_INSUFFICIENT']),
 ledger:Object.freeze(['START_DATE_NOT_SET','INPUT_INVALID','CONFIG_INVALID','TARGET_NOT_AVAILABLE','NO_SESSION_ON_OR_AFTER_START','INITIAL_VALUE_NOT_AVAILABLE','NO_SESSION_AFTER_RECORDED']),
 basis:Object.freeze(['SECTOR_BASIS_NOT_AVAILABLE','PRICE_NOT_ALIGNED','HISTORY_INSUFFICIENT','DISTRIBUTION_DEGENERATE']),
 sector:Object.freeze(['SIC_NOT_AVAILABLE','SEMIS_MEMBERSHIP_NOT_AVAILABLE','SECTOR_ETF_NOT_MAPPED']),
 hits:Object.freeze(['INSUFFICIENT_SAMPLE']),
 flags:Object.freeze(['HOLD','EXCLUDE','CONFIRMED_TEMPORARY','CONFIRMED_STRUCTURAL','CLEAR'])});
// [Korean, English] per code. A code missing here is shown verbatim (codeText), never dropped or invented.
const CODE_LABELS=Object.freeze({
 // engine: judgement reasons
 DATA_PRICE_MISSING:['가격 결측','Price missing'],DATA_FX_MISSING:['환율 결측','FX rate missing'],DATA_SNAPSHOT_MISSING:['Q·G 스냅샷 없음','No Q·G snapshot'],
 COVERAGE_BLOCKED:['데이터 Coverage BLOCKED','Data coverage BLOCKED'],USER_EXCLUDE:['사용자 제외 플래그','User exclude flag'],
 QG_DECLINE:['Q·G 평균이 직전 스냅샷보다 임계 이상 하락','Q·G average fell by the threshold or more since the previous snapshot'],
 COVERAGE_WORSENED:['Coverage가 READY에서 PARTIAL로 악화','Coverage worsened from READY to PARTIAL'],USER_HOLD:['사용자 보류 플래그','User hold flag'],
 RECHECK_BASIS_NOT_AVAILABLE:['이상 하락 기준 계산 불가(1년 일봉·업종 기준 부족), V 신호 미사용','Abnormal-drop basis not computable (one year of daily bars or sector basis missing); V signal unused'],
 RECHECK_ABNORMAL_DROP:['업종 기준 대비 개별 이상 하락(−2σ), 원인 확인 전 거래 없음','Abnormal drop against the sector basis (−2σ); no virtual trade until the cause is checked'],
 USER_CONFIRMED_TEMPORARY:['사용자 확인: 일시적','User confirmed: temporary'],USER_CONFIRMED_STRUCTURAL:['사용자 확인: 구조적','User confirmed: structural'],
 OVERWEIGHT_GAP:['목표 비중보다 Band 이상 초과','Above the target weight by more than the band'],UNDERWEIGHT_GAP:['목표 비중보다 Band 이상 부족','Below the target weight by more than the band'],
 V_IMPROVED:['Q·G 유지 중 V가 20거래일 전보다 개선','V improved over 20 sessions while Q·G held'],V_DETERIORATED:['Q·G 유지 중 V가 20거래일 전보다 악화','V deteriorated over 20 sessions while Q·G held'],
 BAND_INSIDE:['범위 안, 보유','Inside the band, held'],
 // engine: auxiliary codes
 OVERWEIGHT:['보조: 목표 비중보다 Band 이상 초과(위험재검토 중이라 거래 없음)','Auxiliary: above target by more than the band (risk re-check, no virtual trade)'],
 INCREASE_CANDIDATE:['보조: V 개선으로 확대 후보(위험재검토 중이라 거래 없음)','Auxiliary: add candidate on improved V (risk re-check, no virtual trade)'],
 COVERAGE_PARTIAL:['Coverage PARTIAL(일부 데이터)','Coverage PARTIAL (partial data)'],EARNINGS_WINDOW:['실적 발표 예상 기간','Expected earnings window'],TYPE_CHANGED:['유형 소속 변경','Type membership changed'],
 SECTOR_SP500_SUBSTITUTE:['업종 ETF 대신 S&P 500 기준 사용','S&P 500 used instead of the sector ETF'],
 V_COMPOSITION_CHANGED:['V 요소 구성이 20거래일 전과 다르거나 알 수 없어 V 기울기 미사용','V factor composition differs from 20 sessions earlier or is unknown; V slope unused'],
 // engine: virtual orders and executions
 LIMIT_EXHAUSTED:['하루 한도 소진으로 일부만 배분','Daily limit reached; only part allocated'],
 EXEC_PRICE_MISSING:['체결일 종가 결측으로 가상 주문 취소','Virtual order cancelled: no close on the execution day'],
 EXEC_FX_MISSING:['체결일 환율 결측으로 가상 주문 취소','Virtual order cancelled: no FX rate on the execution day'],
 NO_POSITION:['보유분 없음으로 가상 매도 취소','Virtual sale cancelled: no position'],CASH_INSUFFICIENT:['가상 현금 부족으로 가상 매수 취소','Virtual purchase cancelled: not enough virtual cash'],
 // engine: whole-ledger stops
 START_DATE_NOT_SET:['가상매매 시작일 미정','Virtual trading start date not set'],INPUT_INVALID:['장부 입력 형식 오류','Ledger input invalid'],CONFIG_INVALID:['규칙 설정 형식 오류','Rule configuration invalid'],
 TARGET_NOT_AVAILABLE:['목표 비중 없음','No target weights'],NO_SESSION_ON_OR_AFTER_START:['시작일 이후 거래일 없음','No session on or after the start date'],
 INITIAL_VALUE_NOT_AVAILABLE:['출발 평가액 계산 불가(가격·환율 결측)','Initial value not computable (price or FX missing)'],
 NO_SESSION_AFTER_RECORDED:['마지막 기록 거래일 이후 거래일 없음','No session after the last recorded session'],
 // engine: D-5 basis and D-22 sector mapping
 SECTOR_BASIS_NOT_AVAILABLE:['업종 기준 시세 없음','No sector basis series'],PRICE_NOT_ALIGNED:['보고일 종가가 기준 시세와 맞지 않음','Close not aligned with the basis on this day'],
 HISTORY_INSUFFICIENT:['정렬된 일봉 부족','Not enough aligned daily bars'],DISTRIBUTION_DEGENERATE:['초과수익률 분포 계산 불가(변동 0)','Excess-return distribution degenerate (zero spread)'],
 SIC_NOT_AVAILABLE:['SIC 없음 → S&P 500 기준','No SIC → S&P 500 basis'],SEMIS_MEMBERSHIP_NOT_AVAILABLE:['반도체 테마 소속 미확인 → XLI 기준','Semiconductor theme membership unknown → XLI basis'],
 SECTOR_ETF_NOT_MAPPED:['대응 업종 ETF 없음 → S&P 500 기준','No mapped sector ETF → S&P 500 basis'],
 INSUFFICIENT_SAMPLE:['표본 부족(30건 미만)','Insufficient sample (under 30)'],
 // engine: user flags
 HOLD:['보류','Hold'],EXCLUDE:['제외','Exclude'],CONFIRMED_TEMPORARY:['확인: 일시적','Confirmed: temporary'],CONFIRMED_STRUCTURAL:['확인: 구조적','Confirmed: structural'],CLEAR:['플래그 해제','Flag cleared'],
 // runner: inputs and sources
 BEFORE_START_DATE:['가상매매 시작일 전','Before the virtual trading start date'],TARGET_CATALOG_INVALID:['공개 TARGET 카탈로그 형식 오류','Public TARGET catalog invalid'],
 SESSIONS_NOT_AVAILABLE:['S&P 500 일봉 없음 → 거래일 없음','No S&P 500 daily bars → no sessions'],SET_B_NOT_DEFINED:['세트 B 구성 없음','Set B not defined'],SET_B_INVALID:['세트 B 구성 형식 오류','Set B definition invalid'],
 SET_NOT_DEFINED:['세트 구성 없음(정의 전 또는 종료됨)','Set not defined (not yet defined or closed)'],SET_INVALID:['세트 구성 형식 오류','Set definition invalid'],
 NO_ACTUAL:['기기 실제 보유 없음','No ACTUAL holdings on this device'],ACTUAL_INVALID:['기기 실제 보유 형식 오류','ACTUAL holdings invalid'],
 INITIAL_COST_FX_MISSING:['출발 원가 환산 환율 없음','No FX rate for the initial cost'],LEDGER_NOT_AVAILABLE:['가상 장부 없음','Virtual ledger not available'],
 NOT_REQUESTED:['요청하지 않음','Not requested'],HISTORY_UNAVAILABLE:['일봉 없음','Daily history unavailable'],HISTORY_FORMAT_INVALID:['일봉 형식 오류','Daily history format invalid'],
 CURRENCY_MISMATCH:['통화 불일치','Currency mismatch'],OFF:['비공개 가격 Worker 꺼짐','Private price Worker off'],REQUEST_INVALID:['요청 형식 오류','Request invalid'],
 ORIGIN_UNAPPROVED:['가격 Worker 주소 미승인','Price Worker origin not approved'],ORIGIN_FORBIDDEN:['가격 Worker가 이 주소를 거부','Price Worker refused this origin'],
 AUTH_REQUIRED:['구글 로그인 필요','Google sign-in required'],AUTH_FORBIDDEN:['구글 계정 권한 없음','Google account not allowed'],AUTH_UNAVAILABLE:['로그인 확인 불가','Sign-in check unavailable'],
 AUTH_FAILED:['로그인 실패','Sign-in failed'],CONFIG_UNAVAILABLE:['Worker 설정 없음','Worker configuration unavailable'],CANCELED:['취소됨','Cancelled'],
 RATE_LIMITED:['요청 한도 초과','Rate limited'],RATE_LIMIT_UNAVAILABLE:['요청 한도 확인 불가','Rate limit unavailable'],READ_FAILED:['읽기 실패','Read failed'],
 SOURCE_TOO_LARGE:['응답이 너무 큼','Response too large'],YAHOO_UNAVAILABLE:['시세 원천 응답 없음','Quote source unavailable'],INVALID:['형식 오류','Invalid'],
 LEDGER_UNREACHABLE:['공개 전진 검증 장부를 열 수 없음','Public forward ledger unreachable'],LEDGER_INVALID:['공개 전진 검증 장부 형식 오류','Public forward ledger invalid'],
 LEDGER_NOT_PUBLISHED:['공개 전진 검증 장부 미게시','Public forward ledger not published'],
 // S17 report glue (app.js)
 RUNNER_LOADING:['가상 장부 입력 불러오는 중','Loading virtual ledger inputs'],RUNNER_FAILED:['가상 장부 계산 실패','Virtual ledger run failed'],
 PUBLIC_CATALOG_UNAVAILABLE:['공개 카탈로그 없음','Public catalog unavailable'],MAILBOX_FAILED:['우체통 처리 실패','Mailbox failed'],HASH_UNAVAILABLE:['해시 계산 불가','Hash unavailable'],
 // signals: V slope use
 BASIS_NOT_AVAILABLE:['V 기울기 미사용','V slope unused'],V_HISTORY_SHORT:['V 기록 부족','V history too short'],
 V_CORE_FACTOR_MISSING:['V 핵심 요소 결측 → 그날 V는 NA(0으로 계산하지 않음)','A core V factor is missing → that day\'s V is NA (never computed as 0)'],
 V_FACTORS_NOT_AVAILABLE:['V 요소 없음','No V factors'],REHEARSAL_ONLY:['오늘 공개 Q·G로 빈 날 채우기는 리허설 전용','Filling missing days with today\'s public Q·G is rehearsal-only'],
 // V history store
 DATE_INVALID:['날짜 형식 오류','Date invalid'],DATE_BEFORE_LAST_RECORDED:['마지막 기록일보다 이른 날짜(소급 안 함)','Before the last recorded date (no backfill)'],
 UNCHANGED:['새 값 없음(이미 기록)','Nothing new (already recorded)'],NO_VALUES:['기록할 V 없음','No V values to record'],DEVICE_STORAGE_UNAVAILABLE:['기기 저장소 사용 불가','Device storage unavailable'],
 V_STORE_INVALID:['기기 V 기록 형식 오류(그대로 둠)','Device V store invalid (left untouched)'],SESSION_NOT_AVAILABLE:['완료 거래일 없음','No completed session'],
 VALUATION_INPUTS_UNAVAILABLE:['공개 가치평가 입력 없음','Public valuation inputs unavailable'],
 // ledger sheets (D-10)
 PRICE_REVISED:['기록 이후 과거 일봉 등이 바뀌어 재생 결과가 기록과 다름(기록 유지, 기록된 상태에서 이어서 기록)','Replay differs from the recorded rows, e.g. revised daily bars (records kept, recording continues from the recorded state)'],
 SHEET_ROWS_INVALID:['시트 행 형식 오류(쓰기 중지)','Sheet rows invalid (writes stopped)'],
 SHEET_HEADER_MISMATCH:['시트 머리글 불일치','Sheet header mismatch'],META_INVALID:['VirtualMeta 형식 오류','VirtualMeta invalid'],META_ROW_INVALID:['VirtualMeta 행 형식 오류','VirtualMeta row invalid'],
 LEDGER_UNKNOWN:['VirtualMeta에 없는 장부 ID','Ledger ID not in VirtualMeta'],INPUTS_NOT_READY:['장부 입력 준비 전','Ledger inputs not ready'],
 INPUTS_INCOMPLETE:['시세 일부 없음(다시 받은 뒤 기록)','Inputs incomplete (record after reloading quotes)'],INPUTS_CHANGED:['기록 이후 입력이 바뀜','Inputs changed since recording'],
 WAITING_FOR_QG_RECORD:['Q·G 기록 대기','Waiting for the Q·G record'],VALUATION_NOT_AVAILABLE:['평가액 계산 불가','Valuation not available'],
 SHEET_NOT_READY:['시트 장부 준비 전','Sheet ledger not ready'],SHEET_NOT_LOADED:['시트를 아직 읽지 않음','Sheet not loaded yet'],NOT_CONNECTED:['구글 시트 미연결','Google Sheet not connected'],
 SHADOW_NOT_STARTED:['그림자 장부 출발 전','Shadow ledger not started'],SHADOW_ALREADY_STARTED:['그림자 장부가 이미 출발함','Shadow ledger already started'],
 SET_B_REDEFINED:['세트 B 재정의','Set B redefined'],REHEARSAL_NOT_RECORDED:['리허설 결과는 기록하지 않음','Rehearsal results are never recorded'],
 SET_REDEFINED:['세트 구성 변경(새 장부)','Set redefined (new ledger)'],SET_A_CHANGED:['세트 A 구성 변경(새 버전·새 장부)','Set A changed (new version, new ledger)'],
 SET_DELETED:['세트 삭제 → 종료(기록 보존)','Set deleted → closed (records kept)'],SET_MEMBERS_OVER_30:['구성 종목 30개 초과','More than 30 members'],
 WEIGHTS_NOT_AVAILABLE:['보유 비중 계산 불가(마지막 거래일 가격·환율 결측)','Holding weights not available (price or FX missing on the last session)'],TYPES_NOT_AVAILABLE:['공개 유형 소속 없음','Public company types unavailable'],
 COMPARE_NEEDS_TWO_SETS:['비교는 세트 2개 이상 필요','Comparison needs at least two sets'],
 PURPOSE_REQUIRED:['세트 목적(한 줄) 필요','A one-line set purpose is required'],PURPOSE_INVALID:['세트 목적 형식 오류(한 줄, 120자 이하)','Set purpose invalid (one line, up to 120 characters)'],
 NUMBER_INVALID:['숫자 형식 오류','Number invalid'],VALUE_INVALID:['값 형식 오류','Value invalid'],CONFIG_NOT_CANONICAL:['규칙 설정이 공식 v1과 다름','Configuration differs from the official v1'],
 COMPANY_NOT_SUPPORTED:['허용 목록 밖 종목(가격 Worker 허용 목록: TARGET 19종목 + ETF 15종)','Not on the price Worker allowlist (19 TARGET companies + 15 ETFs)'],WEIGHT_INVALID:['비중 형식 오류(0~100)','Weight invalid (0 to 100)'],
 WEIGHT_SUM_OVER_100:['비중 합계 100 초과','Weights sum above 100'],WEIGHTS_EMPTY:['비중 없음','No weights'],WRITE_FAILED:['시트 쓰기 실패','Sheet write failed']});
const lang=locale=>locale==='en-US'||locale==='en'?'en':'ko';
const byLevel=(a,b)=>LEVELS.indexOf(a)-LEVELS.indexOf(b);
const escHtml=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
// '▲비중확대검토': symbol + name, no space (D-19 register wording).
function label(level,locale){return LEVELS.includes(level)?SYMBOLS[level]+LABELS[lang(locale)][level]:String(level);}
function codeLabel(code,locale){return has(CODE_LABELS,code)?CODE_LABELS[code][lang(locale)==='en'?1:0]:null;}
// Known code → 'label (CODE)'; unknown (e.g. a Worker error passed through) → the code verbatim, deliberately.
function codeText(code,locale){const l=codeLabel(code,locale);return l===null?String(code):l+' ('+code+')';}
function codesText(codes,locale){return (Array.isArray(codes)?codes:[]).map(c=>codeText(c,locale)).join(', ');}
/* One judgement → chips: exactly one main level, then the auxiliary levels in priority order (never the main again), then
   directional auxiliary signals whose level is not already shown. The same tokens feed the screen chips and the template text. */
function judgementTokens(j,locale){
 if(!obj(j)||!LEVELS.includes(j.main))return[];
 const shown=new Set([j.main]),rest=[];
 for(const l of [...new Set(Array.isArray(j.aux_levels)?j.aux_levels:[])].filter(l=>LEVELS.includes(l)&&!shown.has(l))){shown.add(l);rest.push({kind:'aux',key:l,level:l,text:'+'+label(l,locale)});}
 const aux=Array.isArray(j.aux)?j.aux:[];
 for(const c of Object.keys(SIGNALS).filter(c=>aux.includes(c)&&!shown.has(SIGNALS[c].level))){const s=SIGNALS[c];rest.push({kind:'signal',key:c,level:s.level,text:'+'+SYMBOLS[s.level]+s[lang(locale)]});}
 // Auxiliary chips by level priority (a signal whose level is already shown is skipped above, so levels never repeat).
 rest.sort((a,b)=>byLevel(a.level,b.level));
 return [{kind:'main',key:j.main,level:j.main,text:label(j.main,locale)},...rest];
}
function judgementText(j,locale){return judgementTokens(j,locale).map(t=>t.text).join(' ');}
function judgementHtml(j,{locale='ko-KR'}={}){
 const tokens=judgementTokens(j,locale);if(!tokens.length)return'';
 return '<span class="vt-judgement" data-judgement data-main="'+tokens[0].level+'">'+tokens.map(t=>'<span class="chip vt '+t.kind+'" data-chip="'+t.kind+'" data-level="'+t.level+'" data-tone="'+TONES[t.level]+'"'+(t.kind==='signal'?' data-signal="'+t.key+'"':'')+'>'+escHtml(t.text)+'</span>').join('')+'</span>';
}
// Reason codes then auxiliary codes, each once, in engine order.
function reasonCodes(j){return obj(j)?[...new Set([...(Array.isArray(j.reason_codes)?j.reason_codes:[]),...(Array.isArray(j.aux)?j.aux:[])])]:[];}
function reasonsHtml(codes,{locale='ko-KR'}={}){
 const list=Array.isArray(codes)?codes:[];if(!list.length)return'';
 return '<span class="vt-reasons">'+list.map(c=>'<span class="vt-reason" data-reason-code="'+escHtml(c)+'"'+(has(CODE_LABELS,c)?'':' data-unlabeled')+'>'+escHtml(codeText(c,locale))+'</span>').join('<span aria-hidden="true"> · </span>')+'</span>';
}
function disclaimerHtml(locale){return '<span class="badge vt-disclaimer" data-vt-disclaimer>'+escHtml(DISCLAIMER[lang(locale)])+'</span>';}
// Row order on every surface: main judgement priority, then company id ({main, company}; rows without a main go last).
function compareRows(a,b){const r=x=>LEVELS.includes(x&&x.main)?LEVELS.indexOf(x.main):99;return r(a)-r(b)||String(a.company).localeCompare(String(b.company));}
// '■차단 > ▼위험재검토 > …' from LEVELS.
function priorityText(locale,sep=' > '){return LEVELS.map(l=>label(l,locale)).join(sep);}
// D-22 (decided 2026-10-11): SIC → sector benchmark ETF, first matching row wins; mirrors qgv/sector_basis.py.
const SECTOR_MAP=Object.freeze(JSON.parse('{"schema_version":1,"config_version":"sector_etf_map/v1","status":"DECIDED_2026-10-11","source":"docs/virtual_trading/D22_SECTOR_ETF_MAPPING_DRAFT.md rows 1-14, option A for semiconductor equipment","sp500_benchmark":"SPY","rules":[{"order":1,"etf":"SMH","sic":[[3674,3674]],"exclude":[]},{"order":2,"etf":"SEMIS_THEME_SMH_ELSE_XLI","sic":[[3559,3559],[3827,3827]],"exclude":[]},{"order":3,"etf":"XLK","sic":[[3570,3579],[3660,3679],[7370,7379]],"exclude":[3674]},{"order":4,"etf":"XLV","sic":[[2830,2836],[3840,3851],[8000,8099]],"exclude":[]},{"order":5,"etf":"XLE","sic":[[1311,1311],[1381,1389],[2900,2999]],"exclude":[]},{"order":6,"etf":"XLB","sic":[[1000,1299],[1400,1499],[2600,2699],[2800,2829],[2850,2899],[3300,3399]],"exclude":[]},{"order":7,"etf":"XLP","sic":[[2000,2199],[2840,2844],[5400,5499],[5912,5912]],"exclude":[]},{"order":8,"etf":"XLY","sic":[[3711,3711],[5200,5399],[5500,5999],[7000,7099],[7900,7999]],"exclude":[5912]},{"order":9,"etf":"XLC","sic":[[4800,4899],[7810,7849]],"exclude":[]},{"order":10,"etf":"XLU","sic":[[4900,4999]],"exclude":[]},{"order":11,"etf":"XLRE","sic":[[6500,6553],[6798,6798]],"exclude":[]},{"order":12,"etf":"XLF","sic":[[6000,6499],[6700,6797],[6799,6799]],"exclude":[]},{"order":13,"etf":"XLI","sic":[[1500,1799],[2200,2599],[2700,2799],[3000,3299],[3400,3569],[3580,3659],[3680,3839],[3852,3999],[4000,4799],[5000,5199],[8700,8799]],"exclude":[3827]}]}'));
function sectorBenchmark(sic,semisMember=null,map=SECTOR_MAP){
 if(!(typeof sic==='string'&&/^[0-9]{4}$/.test(sic)&&sic!=='0000'))return{etf:map.sp500_benchmark,rule:14,reason:'SIC_NOT_AVAILABLE'};
 const code=Number(sic);
 for(const rule of map.rules){
  if(rule.exclude.includes(code))continue;
  if(rule.sic.some(([lo,hi])=>lo<=code&&code<=hi)){
   if(rule.etf==='SEMIS_THEME_SMH_ELSE_XLI'){if(semisMember===true)return{etf:'SMH',rule:rule.order,reason:null};return{etf:'XLI',rule:rule.order,reason:semisMember===false?null:'SEMIS_MEMBERSHIP_NOT_AVAILABLE'};}
   return{etf:rule.etf,rule:rule.order,reason:null};
  }
 }
 return{etf:map.sp500_benchmark,rule:14,reason:'SECTOR_ETF_NOT_MAPPED'};
}
function defaultConfig(){return JSON.parse(JSON.stringify(CONFIG));}
return Object.freeze({CONFIG,SECTOR_MAP,sectorBenchmark,LEVELS,SYMBOLS,LABELS,TONES,SIGNALS,DISCLAIMER,CODES,CODE_LABELS,defaultConfig,validateConfig,runLedger,evaluateHits,abnormalDrop,
 label,codeLabel,codeText,codesText,judgementTokens,judgementText,judgementHtml,reasonCodes,reasonsHtml,disclaimerHtml,priorityText,compareRows});
});
