/* S17 report ⑪ Track Record, ⑫ period returns and ⑬ relative-index dashboard. RAM only.
   Pure part mirrors qgv/report_benchmarks.py (vectors: tests/fixtures/report_benchmarks_v1.json); see that module for the
   rules: SPY session calendar, base = close of the session before the period start = 100, a missing close / rate / ledger
   value is a gap (never interpolated or carried), one currency basis for every series (KRW default: USD index × same-session
   KRW=X; USD: ledger ÷ same-session KRW=X), ledger index = engine time-weighted chain, ⑪ from the engine evaluateHits with
   the 30-sample minimum. Inputs are passed in; nothing here fetches, stores, logs or sends prices, values or returns.
   chartSvg draws the ⑬ lines with TechnicalChart.paths (gaps break the line). */
(function(root,factory){const node=typeof module==='object'&&module.exports;const api=factory(node?require('./technical-chart.js'):root.TechnicalChart);if(node)module.exports=api;else root.ReportBenchmarks=api;})(typeof globalThis==='object'?globalThis:this,function(TC){
'use strict';
const SCHEMA='report-benchmarks/1';
const PERIODS=Object.freeze([['1D',1],['5D',5],['20D',20],['60D',60],['120D',120],['SINCE_START',null]]),PERIOD_IDS=Object.freeze(PERIODS.map(p=>p[0]));
const DASHBOARD=Object.freeze([['SP500','SPY'],['XLK','XLK'],['VUG','VUG'],['QUAL','QUAL'],['XLY','XLY'],['XLP','XLP']]);
const SPY='SPY',FX_SYMBOL='KRW=X',BASES=Object.freeze(['KRW','USD']);
// NYSE full-day holidays, used only to estimate future session dates (2026–2027 published calendar).
const NYSE_HOLIDAYS=new Set(['2026-01-01','2026-01-19','2026-02-16','2026-04-03','2026-05-25','2026-06-19','2026-07-03','2026-09-07','2026-11-26','2026-12-25',
 '2027-01-01','2027-01-18','2027-02-15','2027-03-26','2027-05-31','2027-06-18','2027-07-05','2027-09-06','2027-11-25','2027-12-24']);
const HOLIDAYS_KNOWN_UNTIL='2027-12-31';
// A gap at the base session / the as-of session → the series' NOT_AVAILABLE reason.
const BASE_CODES=Object.freeze({CLOSE_MISSING:'BASE_CLOSE_MISSING',FX_MISSING:'BASE_FX_MISSING'}),LAST_CODES=Object.freeze({CLOSE_MISSING:'LAST_CLOSE_MISSING',FX_MISSING:'LAST_FX_MISSING',VALUE_MISSING:'LAST_VALUE_MISSING'});
const own=(o,k)=>o!==null&&typeof o==='object'&&Object.prototype.hasOwnProperty.call(o,k);
const object=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
const num=v=>typeof v==='number'&&Number.isFinite(v);
const get=(o,k)=>own(o,k)?o[k]:undefined;
const na=reason=>({state:'NOT_AVAILABLE',reason});
const empty=reason=>({state:'NOT_AVAILABLE',reason,return:null,points:[],gap_codes:[],gaps:0});

function periodWindow(calendar,asOf,period,startDate){
 if(asOf===null||asOf===undefined||!calendar.includes(asOf))return na('SESSIONS_NOT_AVAILABLE');
 const a=calendar.indexOf(asOf);
 if(period==='SINCE_START'){
  if(startDate===null||startDate===undefined||startDate>asOf)return na('BEFORE_START_DATE');
  const before=calendar.filter(d=>d<startDate);if(!before.length)return na('NO_SESSION_BEFORE_START');
  return{state:'OK',reason:null,base:before[before.length-1],sessions:calendar.filter(d=>startDate<=d&&d<=asOf)};
 }
 const p=PERIODS.find(x=>x[0]===period),n=p?p[1]:null;
 if(n===null)return na('PERIOD_INVALID');
 if(a<n)return na('HISTORY_TOO_SHORT');
 return{state:'OK',reason:null,base:calendar[a-n],sessions:calendar.slice(a-n+1,a+1)};
}
function series(points,codes,ret,lastCode){
 const gaps=points.filter(p=>p===null).length;
 return ret===null?{state:'NOT_AVAILABLE',reason:lastCode,return:null,points,gap_codes:codes,gaps}:{state:'OK',reason:null,return:ret,points,gap_codes:codes,gaps};
}
function priceIndex(closes,fx,window,basis){
 const level=d=>{const c=get(closes,d);if(!num(c))return[null,'CLOSE_MISSING'];
  if(basis==='KRW'){const r=get(fx,d);if(!num(r))return[null,'FX_MISSING'];return[c*r,null];}return[c,null];};
 const[base,code]=level(window.base);if(base===null)return empty(BASE_CODES[code]);
 const points=[],codes=[];
 for(const d of window.sessions){const[v,c]=level(d);points.push(v===null?null:v/base*100);codes.push(c);}
 const[last,lastCode]=level(window.sessions[window.sessions.length-1]);
 return series(points,codes,last===null?null:last/base-1,lastCode===null?null:LAST_CODES[lastCode]);
}
function ledgerIndex(days,calendar,window,basis,fx){
 const by=new Map(days.map(d=>[d.date,d])),first=days[0].date,before=calendar.filter(d=>d<first),b=window.base;
 let prev=null,prevRate=null;
 if(b<first){if(!before.length||b!==before[before.length-1])return empty('PERIOD_BEFORE_LEDGER_START');}
 else{const day=by.get(b);if(!day||!num(day.total_value))return empty('BASE_VALUE_MISSING');prev=day.total_value;
  if(basis==='USD'){prevRate=get(fx,b);if(!num(prevRate))return empty('BASE_FX_MISSING');}}
 let index=1,deposits=0,code=null;const points=[],codes=[];
 for(const d of window.sessions){
  const day=by.get(d);if(!day){points.push(null);codes.push('VALUE_MISSING');code='VALUE_MISSING';continue;}
  deposits+=num(day.deposit)?day.deposit:0;
  const total=day.total_value;if(!num(total)){points.push(null);codes.push('VALUE_MISSING');code='VALUE_MISSING';continue;}
  let rate=null;if(basis==='USD'){rate=get(fx,d);if(!num(rate)){points.push(null);codes.push('FX_MISSING');code='FX_MISSING';continue;}}
  if(prev!==null&&prev>0){let link=(total-deposits)/prev;if(basis==='USD')link=link*prevRate/rate;index=index*link;}
  prev=total;prevRate=rate;deposits=0;code=null;points.push(index*100);codes.push(null);
 }
 return series(points,codes,points[points.length-1]===null?null:index-1,code===null?null:LAST_CODES[code]);
}
function ledgerSeries(entry,calendar,window,basis,fx){
 if(!object(entry)||entry.state!=='OK'||!Array.isArray(entry.days)||!entry.days.length){const codes=object(entry)&&Array.isArray(entry.reason_codes)?entry.reason_codes:[];return empty(codes.length?codes[0]:'LEDGER_NOT_AVAILABLE');}
 if(basis==='USD'&&!Object.keys(fx).length)return empty('FX_NOT_AVAILABLE');
 return ledgerIndex(entry.days,calendar,window,basis,fx);
}
function indexSeries(symbol,indices,sources,calendar,window,basis,fx){
 const closes=get(indices,symbol);
 if(!object(closes)||!Object.keys(closes).length){const s=get(sources,symbol),code=object(s)?s.code:null;return empty(code||'NOT_REQUESTED');}
 if(basis==='KRW'&&!Object.keys(fx).length)return empty('FX_NOT_AVAILABLE');
 return priceIndex(closes,fx,window,basis);
}
const verdict=x=>x===null?null:x>0?'ABOVE':x<0?'BELOW':'EQUAL';
/* ⑫ period table + ⑬ dashboard. ledgers[0] is the report target: {key, state, reason_codes, days:[{date,total_value,deposit}]}. */
function build({indices={},sources={},ledgers=[],start_date=null,period='20D',basis='KRW'}={}){
 indices=object(indices)?indices:{};sources=object(sources)?sources:{};
 basis=BASES.includes(basis)?basis:'KRW';period=PERIOD_IDS.includes(period)?period:'20D';
 const spy=get(indices,SPY),calendar=object(spy)?Object.keys(spy).sort():[],fx=object(get(indices,FX_SYMBOL))?indices[FX_SYMBOL]:{};
 const target=ledgers.length?ledgers[0]:null,targetDays=target&&target.state==='OK'&&Array.isArray(target.days)&&target.days.length?target.days:null;
 const asOf=targetDays?targetDays[targetDays.length-1].date:(calendar.length?calendar[calendar.length-1]:null);
 let startDate=start_date;if(targetDays&&targetDays[0].date)startDate=targetDays[0].date;
 const out={schema:SCHEMA,basis,period,as_of:asOf,start_date:startDate,state:'OK',reason:null,periods:[],dashboard:null};
 if(!calendar.length){const s=get(sources,SPY);out.state='NOT_AVAILABLE';const mine=target&&target.state!=='OK'&&Array.isArray(target.reason_codes)&&target.reason_codes.length?target.reason_codes[0]:null;out.reason=(object(s)&&s.code)||mine||'SESSIONS_NOT_AVAILABLE';}
 for(const pid of PERIOD_IDS){
  const w=calendar.length?periodWindow(calendar,asOf,pid,startDate):na(out.reason);
  if(w.state!=='OK'){out.periods.push({period:pid,state:'NOT_AVAILABLE',reason:w.reason,base:null,start:null,end:null,target:null,sp500:null,excess:null,verdict:null});continue;}
  const t=target?ledgerSeries(target,calendar,w,basis,fx):empty('LEDGER_NOT_AVAILABLE'),s=indexSeries(SPY,indices,sources,calendar,w,basis,fx);
  const excess=t.return===null||s.return===null?null:t.return-s.return;
  out.periods.push({period:pid,state:'OK',reason:null,base:w.base,start:w.sessions[0],end:w.sessions[w.sessions.length-1],
   target:{state:t.state,reason:t.reason,return:t.return},sp500:{state:s.state,reason:s.reason,return:s.return},excess,verdict:verdict(excess)});
 }
 const w=calendar.length?periodWindow(calendar,asOf,period,startDate):na(out.reason);
 const dash={period,state:w.state,reason:w.reason,base:w.base===undefined?null:w.base,sessions:w.sessions||[],series:[]};
 if(w.state==='OK'){
  for(const entry of ledgers)dash.series.push({key:entry.key,kind:'LEDGER',...ledgerSeries(entry,calendar,w,basis,fx)});
  for(const[key,sym]of DASHBOARD)dash.series.push({key,kind:'INDEX',...indexSeries(sym,indices,sources,calendar,w,basis,fx)});
 }
 out.dashboard=dash;return out;
}

/* ---------- ⑪ Track Record ---------- */
function iso(d){return d.toISOString().slice(0,10);}
function nextWeekday(d){const x=new Date(d+'T00:00:00Z');for(;;){x.setUTCDate(x.getUTCDate()+1);const s=iso(x),wd=x.getUTCDay();if(wd!==0&&wd!==6&&!NYSE_HOLIDAYS.has(s))return s;}}
function nthSessionAfter(known,date,k){
 const after=known.filter(s=>s>date);if(after.length>=k)return[after[k-1],false];
 let cursor=after.length?after[after.length-1]:date;for(let i=0;i<k-after.length;i++)cursor=nextWeekday(cursor);
 return[cursor,true];
}
function dayBefore(d){const x=new Date(d+'T00:00:00Z');x.setUTCDate(x.getUTCDate()-1);return iso(x);}
function tradeOutcomes(input,trades,window){
 const sessions=input.sessions,pos=new Map(sessions.map((d,i)=>[d,i])),bench=object(input.benchmarks)?get(input.benchmarks,'SP500'):undefined,out=[];
 for(const t of trades){
  const i=pos.get(t.date);if(i===undefined||i+window>=sessions.length||!object(bench))continue;
  const end=sessions[i+window],closes=input.companies[t.company].closes;
  if(!own(closes,t.date)||!own(closes,end)||!own(bench,t.date)||!own(bench,end))continue;
  const rs=closes[end]/closes[t.date]-1,rb=bench[end]/bench[t.date]-1;
  out.push({date:t.date,end,company:t.company,side:t.side,window,stock_return:rs,benchmark_return:rb,hit:(t.side==='BUY'&&rs>rb)||(t.side==='SELL'&&rs<rb)});
 }
 return out;
}
const tupleCmp=(a,b)=>{for(const k of ['date','company','side']){if(a[k]<b[k])return -1;if(a[k]>b[k])return 1;}return 0;};
function trackRecord({hits=null,trades=[],ledger_input=null,ledger_reasons=[],start_date=null,windows=[5,20,63],min_samples=30,recent_window=5,recent_limit=5}={}){
 const sessions=ledger_input?[...ledger_input.sessions]:[],rows=[];trades=Array.isArray(trades)?trades:[];
 for(const w of windows){
  const h=(Array.isArray(hits)?hits:[]).find(x=>x.window===w)||null;
  if(h===null){
   let first=null,est=false;
   if(start_date){const[s1,e1]=nthSessionAfter(sessions,dayBefore(start_date),1),[f,e2]=nthSessionAfter(sessions,s1,1+w);first=f;est=e1||e2;}
   const reasons=Array.isArray(ledger_reasons)?ledger_reasons:[];
   rows.push({window:w,state:'NOT_AVAILABLE',reason:reasons.length?reasons[0]:'LEDGER_NOT_AVAILABLE',samples:null,hits:null,pending:null,missing:null,hit_rate:null,expected_first:first,expected_estimated:est});
   continue;
  }
  const enough=h.samples>=min_samples;
  const row={window:w,samples:h.samples,hits:enough?h.hits:null,pending:h.pending,missing:h.missing,hit_rate:enough?h.hit_rate:null,expected_first:null,expected_estimated:false};
  if(enough)Object.assign(row,{state:'OK',reason:null});
  else if(h.samples>0)Object.assign(row,{state:'INSUFFICIENT_SAMPLE',reason:'SAMPLE_BELOW_MINIMUM'});
  else{
   let reason,anchor,k;
   if(!trades.length){reason='NO_TRADES';anchor=sessions.length?sessions[sessions.length-1]:null;k=1+w;}
   else if(h.pending>0){reason='WINDOW_NOT_ELAPSED';anchor=trades.map(t=>t.date).sort()[0];k=w;}
   else{reason='PRICE_OR_BENCHMARK_MISSING';anchor=null;k=0;}
   Object.assign(row,{state:'NOT_AVAILABLE',reason});
   if(anchor!==null){const[d,e]=nthSessionAfter(sessions,anchor,k);row.expected_first=d;row.expected_estimated=e;}
  }
  rows.push(row);
 }
 const recent=ledger_input&&trades.length?tradeOutcomes(ledger_input,trades,recent_window).sort(tupleCmp).reverse().slice(0,recent_limit):[];
 return{schema:SCHEMA,benchmark:'SP500',min_samples,windows:rows,recent,recent_window,holidays_known_until:HOLIDAYS_KNOWN_UNTIL};
}

/* ---------- labels and chart (display only) ---------- */
const PERIOD_LABELS=Object.freeze({'1D':['1D','1D'],'5D':['5D','5D'],'20D':['20D','20D'],'60D':['60D','60D'],'120D':['120D','120D'],SINCE_START:['시작 이후','Since start']});
const SERIES_LABELS=Object.freeze({SET_A:['세트 A','Set A'],SET_B:['세트 B','Set B'],SHADOW:['그림자 장부','Shadow ledger'],SP500:['S&P 500 (SPY)','S&P 500 (SPY)'],XLK:['XLK','XLK'],VUG:['VUG','VUG'],QUAL:['QUAL','QUAL'],XLY:['XLY','XLY'],XLP:['XLP','XLP']});
const BASIS_LABELS=Object.freeze({KRW:['원화 기준: 장부 원화 그대로 · 미국 지수는 같은 날 KRW=X 종가로 원화 환산(환율 효과 포함)','KRW basis: ledgers in KRW · US indices × same-session KRW=X close (FX effect included)'],
 USD:['달러 기준: 미국 지수 현지 종가 · 장부는 같은 날 KRW=X 종가로 달러 환산','USD basis: US indices at local closes · ledgers ÷ same-session KRW=X close']});
const VERDICT_LABELS=Object.freeze({ABOVE:['상회','Above'],BELOW:['하회','Below'],EQUAL:['같음','Equal']});
const CODE_LABELS=Object.freeze({
 SESSIONS_NOT_AVAILABLE:['S&P 500 세션 없음','No S&P 500 sessions'],BEFORE_START_DATE:['시작일 전','Before the start date'],NO_SESSION_BEFORE_START:['시작 직전 세션 없음','No session before the start'],
 PERIOD_INVALID:['기간 형식 오류','Invalid period'],HISTORY_TOO_SHORT:['일봉 기간 부족','History too short'],PERIOD_BEFORE_LEDGER_START:['기간이 장부 시작보다 이름','Period starts before the ledger'],
 BASE_CLOSE_MISSING:['기준일 종가 없음','Base close missing'],BASE_FX_MISSING:['기준일 환율 없음','Base FX rate missing'],BASE_VALUE_MISSING:['기준일 장부 평가 없음','Base ledger value missing'],
 LAST_CLOSE_MISSING:['마지막 세션 종가 없음','Last close missing'],LAST_FX_MISSING:['마지막 세션 환율 없음','Last FX rate missing'],LAST_VALUE_MISSING:['마지막 세션 장부 평가 없음','Last ledger value missing'],
 CLOSE_MISSING:['종가 없음','Close missing'],FX_MISSING:['환율 없음','FX rate missing'],VALUE_MISSING:['장부 평가 없음','Ledger value missing'],FX_NOT_AVAILABLE:['KRW=X 환율 시세 없음','KRW=X rates unavailable'],
 LEDGER_NOT_AVAILABLE:['장부 없음','Ledger unavailable'],NOT_REQUESTED:['요청 안 함','Not requested'],SAMPLE_BELOW_MINIMUM:['표본 부족(n<30)','Too few samples (n<30)'],
 NO_TRADES:['가상 거래 없음','No virtual trades'],WINDOW_NOT_ELAPSED:['평가 창 미경과','Window not elapsed'],PRICE_OR_BENCHMARK_MISSING:['종가·벤치마크 결측','Close or benchmark missing'],NO_COMPARABLE_PERIOD:['비교 가능한 기간 없음','No comparable period']});
const CODES=Object.freeze(Object.keys(CODE_LABELS));
const lang=locale=>locale==='en-US'?1:0;
function label(table,key,locale){return own(table,key)?table[key][lang(locale)]:String(key);}
function codeLabel(code,locale){return own(CODE_LABELS,code)?CODE_LABELS[code][lang(locale)]:null;}
// One categorical order (validated reference palette), fixed per entity so a filter never repaints a series.
const COLORS=Object.freeze({SET_A:'#2a78d6',SET_B:'#6250d6',SHADOW:'#6250d6',SP500:'#eb6834',XLK:'#1baf7a',VUG:'#eda100',QUAL:'#e87ba4',XLY:'#008300',XLP:'#e34948'});
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function localPaths(values,g){const out=[];let pts=[];const finish=()=>{if(pts.length){out.push(pts.length===1?pts[0]+' L'+pts[0].slice(1):pts.join(' '));pts=[];}};
 values.forEach((v,i)=>{if(v===null||!Number.isFinite(v)){finish();return;}pts.push((pts.length?'L':'M')+g.x(i).toFixed(2)+','+g.y(v).toFixed(2));});finish();return out;}
/* ⑬ SVG: base point (100) + one point per period session; gaps break the line (TechnicalChart.paths). Index levels only. */
function chartSvg(dash,{locale='ko-KR',target=null}={}){
 if(!dash||dash.state!=='OK')return'';
 const shown=dash.series.filter(s=>s.points.some(p=>p!==null)),dates=[dash.base,...dash.sessions];
 if(!shown.length)return'';
 const values=shown.flatMap(s=>s.points.filter(p=>p!==null)).concat([100]);
 let lo=Math.min(...values),hi=Math.max(...values);if(hi-lo<1){lo-=0.5;hi+=0.5;}
 const pad=(hi-lo)*0.06;lo-=pad;hi+=pad;
 const W=640,H=280,L=58,R=12,T=14,B=34,g={x:i=>L+i*(W-L-R)/Math.max(1,dates.length-1),y:v=>T+(hi-v)/(hi-lo)*(H-T-B)};
 const paths=TC&&typeof TC.paths==='function'?TC.paths:localPaths,en=lang(locale)===1;
 let h='<svg viewBox="0 0 '+W+' '+H+'" width="100%" role="img" data-bench-chart aria-label="'+esc(en?'Relative index, base = 100':'상대지수, 기준 = 100')+'">';
 for(const v of [lo+pad,100,hi-pad]){const y=g.y(v).toFixed(2);h+='<line x1="'+L+'" x2="'+(W-R)+'" y1="'+y+'" y2="'+y+'" class="bench-grid'+(v===100?' bench-base':'')+'"/><text x="'+(L-4)+'" y="'+(+y+3)+'" text-anchor="end" class="chart-axis">'+esc(v.toFixed(1))+'</text>';}
 for(const i of [...new Set([0,Math.floor((dates.length-1)/2),dates.length-1])])h+='<text x="'+g.x(i).toFixed(2)+'" y="'+(H-8)+'" text-anchor="'+(i===0?'start':i===dates.length-1?'end':'middle')+'" class="chart-axis">'+esc(dates[i])+'</text>';
 for(const s of shown){const vals=[100,...s.points],main=s.key===target;
  for(const d of paths(vals,g))h+='<path d="'+d+'" fill="none" stroke="'+(COLORS[s.key]||'#5e6863')+'" stroke-width="'+(main?2.5:1.5)+'" stroke-linejoin="round" stroke-linecap="round" data-bench-line="'+esc(s.key)+'"/>';}
 // Hover: one transparent column per session with a native tooltip of every series' index level on that date.
 const step=(W-L-R)/Math.max(1,dates.length-1);
 dates.forEach((d,i)=>{const tip=d+' · '+shown.map(s=>label(SERIES_LABELS,s.key,locale)+' '+(i===0?'100.0':s.points[i-1]===null?'N/A':s.points[i-1].toFixed(1))).join(' · ');
  h+='<rect x="'+Math.max(0,g.x(i)-step/2).toFixed(2)+'" y="'+T+'" width="'+Math.max(2,step).toFixed(2)+'" height="'+(H-T-B)+'" fill="transparent" data-bench-hover="'+esc(d)+'"><title>'+esc(tip)+'</title></rect>';});
 return h+'</svg>';
}
// Legend swatch: a short line in the series colour (SVG attribute, no inline style: the page CSP has no unsafe-inline).
function swatchSvg(key,main=false){return '<svg class="bench-swatch" width="18" height="8" viewBox="0 0 18 8" aria-hidden="true"><line x1="2" y1="4" x2="16" y2="4" stroke="'+(COLORS[key]||'#5e6863')+'" stroke-width="'+(main?3.5:2.5)+'" stroke-linecap="round"/></svg>';}
return Object.freeze({SCHEMA,PERIODS,PERIOD_IDS,DASHBOARD,SPY,FX_SYMBOL,BASES,NYSE_HOLIDAYS,HOLIDAYS_KNOWN_UNTIL,CODES,CODE_LABELS,PERIOD_LABELS,SERIES_LABELS,BASIS_LABELS,VERDICT_LABELS,COLORS,
 periodWindow,priceIndex,ledgerIndex,build,nthSessionAfter,tradeOutcomes,trackRecord,label,codeLabel,chartSvg,swatchSvg});
});
