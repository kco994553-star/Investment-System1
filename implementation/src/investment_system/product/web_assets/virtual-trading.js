/* Virtual trading rules v1 (PROVISIONAL): deterministic daily replay of one virtual ledger, RAM only.
   Port of qgv/virtual_trading.py (vectors: tests/fixtures/virtual_trading_reference_v1.json). Prices, ledgers and P&L are
   arguments and results only: nothing here fetches, stores or sends them. A virtual buy/sell is a rule record, not an order. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.VirtualTrading=api;})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
const CONFIG=Object.freeze(JSON.parse('{"schema_version":1,"config_version":"virtual_trading/v1-provisional","rules_version":"virtual_trading_rules/v1","status":"PROVISIONAL_UNCALIBRATED","role":"RAM_ONLY_DEVICE","decided_at":"2026-10-11","start_date":"2026-10-19","base_currency":"KRW","daily_deposit":1000000,"buy_limit":1000000,"sell_limit":1000000,"execution":"NEXT_SESSION_CLOSE","cost_bps":0,"fractional_quantity":true,"band_pp":1,"qg_decline_threshold":5,"min_trade":10000,"abnormal_drop":{"window_sessions":20,"lookback_sessions":252,"k":2},"sector_basis":"SECTOR_ETF_CONFIRMED","macro_gate":"INACTIVE_MAPPING_PENDING","v_slope":{"lookback_sessions":20,"threshold":10},"benchmark":"SP500","hit_windows":[5,20,63],"hit_min_samples":30,"total_score":"TYPE_WEIGHTED_QGV_ELSE_QG","provenance":{"start_date":"D-13 DECIDED_2026-10-11","daily_deposit":"D-1 PROVISIONAL","buy_limit":"D-15 DECIDED_2026-10-10","sell_limit":"D-15 DECIDED_2026-10-10","execution":"D-2 PROVISIONAL","cost_bps":"D-3 PROVISIONAL","fractional_quantity":"D-4 PROVISIONAL","abnormal_drop":"D-5 PROVISIONAL","macro_gate":"D-6 PROVISIONAL","band_pp":"D-7 PROVISIONAL","qg_decline_threshold":"D-8 PROVISIONAL","min_trade":"D-9 PROVISIONAL","benchmark":"D-11 PROVISIONAL","hit_min_samples":"D-12 PROVISIONAL","total_score":"D-14 PROVISIONAL","v_slope":"D-21 PROVISIONAL","sector_basis":"D-22 DECIDED_2026-10-11 (sector_etf_map/v1)"}}'));
const LEDGER_KINDS=['SET_A','SET_B','SHADOW'],COVERAGES=['READY','PARTIAL','BLOCKED'],FLAG_KINDS=['HOLD','EXCLUDE','CONFIRMED_TEMPORARY','CONFIRMED_STRUCTURAL','CLEAR'],EVENT_KINDS=['EARNINGS_WINDOW','TYPE_CHANGED'];
const LEVELS=['BLOCK','RISK_RECHECK','REDUCE_REVIEW','INCREASE_REVIEW','ADDITIONAL_REVIEW','HOLDING_CONTEXT','OBSERVE'];
const SYMBOLS={BLOCK:'■',RISK_RECHECK:'▼',REDUCE_REVIEW:'▼',INCREASE_REVIEW:'▲',ADDITIONAL_REVIEW:'●',HOLDING_CONTEXT:'●',OBSERVE:'●'};
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
 const flags=has(L,'flags')?L.flags:[];need(Array.isArray(flags)&&flags.every(f=>obj(f)&&day(f.date)&&FLAG_KINDS.includes(f.kind)&&typeof f.company==='string'));
 const ev=has(L,'events')?L.events:{};need(obj(ev)&&Object.entries(ev).every(([d,r])=>day(d)&&obj(r)&&Object.values(r).every(x=>Array.isArray(x)&&x.every(e=>EVENT_KINDS.includes(e)))));
 return L;
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
  if(vNow!==null&&vPast!==null&&qgNow!==null&&qgPast!==null&&qgNow-qgPast>-cfg.qg_decline_threshold){
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
 const first=L.sessions.findIndex(x=>x>=cfg.start_date);if(first<0)return stop('NOT_STARTED','NO_SESSION_ON_OR_AFTER_START');
 const init=has(L,'initial')?L.initial:{cash:0,positions:{}};
 const state={cash:init.cash,positions:{}};for(const[k,v]of Object.entries(sortedEntries(init.positions)))state.positions[k]={quantity:v.quantity,cost:v.cost};
 let[initialValue]=valueOf(L,state,L.sessions[first]);if(initialValue===null)return stop('NOT_AVAILABLE','INITIAL_VALUE_NOT_AVAILABLE');
 initialValue+=state.cash;
 const feeRate=cfg.cost_bps/10000,days=[],trades=[];let pending=[],deposits=0,realized=0,prevTotal=null,growth=1;
 const universe=[...new Set([...Object.keys(L.target_weights),...Object.keys(state.positions)])].sort();
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
 const invested=initialValue+deposits;
 const summary={start_date:L.sessions[first],end_date:last.date,initial_value:initialValue,deposits,total_value:last.total_value,cash:state.cash,
  simple_return:last.total_value===null||invested<=0?null:last.total_value/invested-1,twr:growth-1,realized_pnl:realized,unrealized_pnl:unrealized,
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
const LABELS={ko:{BLOCK:'차단',RISK_RECHECK:'위험재검토',REDUCE_REVIEW:'비중축소검토',INCREASE_REVIEW:'비중확대검토',ADDITIONAL_REVIEW:'추가검토',HOLDING_CONTEXT:'보유맥락',OBSERVE:'관찰'},
 en:{BLOCK:'Blocked',RISK_RECHECK:'Risk re-check',REDUCE_REVIEW:'Review reducing weight',INCREASE_REVIEW:'Review adding weight',ADDITIONAL_REVIEW:'Further review',HOLDING_CONTEXT:'Holding context',OBSERVE:'Observe'}};
function label(level,locale){const t=LABELS[locale==='en-US'||locale==='en'?'en':'ko'];return SYMBOLS[level]+' '+t[level];}
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
return Object.freeze({CONFIG,SECTOR_MAP,sectorBenchmark,LEVELS,SYMBOLS,defaultConfig,validateConfig,runLedger,evaluateHits,abnormalDrop,label});
});
