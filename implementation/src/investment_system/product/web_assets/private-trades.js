/* Read-only Trades rows. Sheet ID is device settings; rows and markers are RAM only. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.PrivateTrades=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
 'use strict';const KEY='investment.web.v1.trades-source',RANGE="'Trades'!A1:D1025",LIMIT=1024;
 const SYMBOLS=new Set(['ASML','LRCX','KLAC','NVDA','AMD','AVGO','QCOM','INTC','MSFT','GOOGL','AMZN','RTX','SYK','ETN','HUBB','GEV','ROK','042700.KS','8035.T']);
 const NYSE=new Set(['RTX','SYK','ETN','HUBB','GEV','ROK']);
 function date(value){
  if(typeof value==='number'&&Number.isInteger(value)&&value>0&&value<100000)value=new Date(Date.UTC(1899,11,30)+value*86400000).toISOString().slice(0,10);
  if(typeof value!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(value))return null;const d=new Date(value+'T00:00:00Z');return Number.isFinite(d.getTime())&&d.toISOString().slice(0,10)===value?value:null;
 }
 function symbol(value){
  if(typeof value!=='string')return null;if(value==='KRX:042700'||value==='042700')return '042700.KS';if(value==='TYO:8035'||value==='8035')return '8035.T';if(SYMBOLS.has(value))return value;
  const [prefix,ticker,...extra]=value.split(':');if(extra.length||!SYMBOLS.has(ticker))return null;
  return prefix===(NYSE.has(ticker)?'NYSE':ticker.endsWith('.KS')?'KRX':ticker.endsWith('.T')?'TYO':'NASDAQ')?ticker:null;
 }
 function number(value){if(typeof value==='string'&&/^(?:0|[1-9]\d{0,14})(?:\.\d{1,12})?$/.test(value))value=Number(value);return typeof value==='number'&&Number.isFinite(value)&&value>0?value:null;}
 function parse(values){
  if(!Array.isArray(values))throw Error('TRADES_SCHEMA_INVALID');
  const headers=[['date','symbol','b/s','quantity'],['date','symbol','side','quantity'],['날짜','종목','b/s','수량']];let start=values.length&&Array.isArray(values[0])&&headers.some(h=>JSON.stringify(h)===JSON.stringify(values[0].map(x=>typeof x==='string'?x.toLowerCase():x)))?1:0;
  let end=values.length;while(end>start&&Array.isArray(values[end-1])&&values[end-1].every(x=>x===null||x===''))end--;
  const rows=[];for(let i=start;i<Math.min(end,start+LIMIT);i++){
   const raw=values[i],reasons=[];if(!Array.isArray(raw)||raw.length>4){rows.push(Object.freeze({row_index:i,state:'NOT_AVAILABLE',reason_codes:['TRADES_SCHEMA_INVALID']}));continue;}
   const day=date(raw[0]),ticker=symbol(raw[1]),side=['B','S'].includes(raw[2])?raw[2]:null,quantity=number(raw[3]);
   if(day===null)reasons.push('TRADE_DATE_INVALID');if(ticker===null)reasons.push('IDENTITY_UNCONFIRMED');if(side===null)reasons.push('TRADE_SIDE_INVALID');if(quantity===null)reasons.push('TRADE_QUANTITY_INVALID');
   rows.push(Object.freeze({row_index:i,state:reasons.length?'NOT_AVAILABLE':'USER_DEVICE_ONLY',date:day,symbol:ticker,side,quantity,reason_codes:Object.freeze(reasons)}));
  }
  return Object.freeze({role:'USER_DEVICE_ONLY',rows:Object.freeze(rows),row_limit_reached:end-start>=LIMIT});
 }
 function sessionDate(timestamp,timezone){const parts=new Intl.DateTimeFormat('en-CA',{timeZone:timezone,year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date(timestamp*1000)),get=type=>parts.find(x=>x.type===type)?.value;return get('year')+'-'+get('month')+'-'+get('day');}
 function markers(parsed,bars,ticker,timezone){const dates=new Map();bars.forEach((b,i)=>{const day=sessionDate(b.timestamp,timezone);dates.set(day,dates.has(day)?null:i);});return parsed.rows.filter(r=>r.state==='USER_DEVICE_ONLY'&&r.symbol===ticker&&dates.has(r.date)&&dates.get(r.date)!==null).map(r=>Object.freeze({...r,bar_index:dates.get(r.date)}));}
 function source(view){const unified=view.GoogleSheetSetup?.source(view);if(unified)return unified;const value=view.localStorage.getItem(KEY);if(value===null)return '';if(!/^[A-Za-z0-9_-]{20,100}$/.test(value))throw Error('TRADES_SOURCE_INVALID');return value;}
 async function read(view,session,{signal}={}){const id=source(view);if(!id)throw Error('TRADES_SOURCE_REQUIRED');const payload=await session.fetchValues(id,RANGE,{signal,maxBytes:1048576});return parse(payload.values);}
 function mountSettings(host,{locale='ko-KR'}={}){
  const doc=host.ownerDocument,view=doc.defaultView,english=locale==='en-US',make=(tag,text)=>{const n=doc.createElement(tag);if(text)n.textContent=text;return n;};
  const root=make('section');root.className='card';root.dataset.tradesSettings='';root.append(make('h2',english?'My Trades · Read only':'내 거래 · 읽기 전용'),make('p',english?'Trades tab: date, symbol, B/S, quantity. Reuses Google login. Sheet ID stays on this device and is excluded from backups.':'Trades 탭: 날짜·종목·B/S·수량. 기존 Google 로그인을 재사용하며 시트 ID는 기기에만 저장되고 백업에서 제외됩니다.'));
  const form=make('form'),label=make('label',english?'Trades sheet ID or URL':'Trades 시트 ID 또는 URL'),input=make('input'),status=make('p');input.type='text';input.maxLength=256;input.autocomplete='off';input.dataset.tradesSource='';label.append(input);try{input.value=source(view);}catch(_){status.textContent='TRADES_SOURCE_INVALID';}
  const save=make('button',english?'Save source':'출처 저장');save.type='submit';const remove=make('button',english?'Remove source':'출처 지우기');remove.type='button';status.setAttribute('role','status');form.append(label,save,remove);root.append(form,status);host.replaceChildren(root);
  form.addEventListener('submit',e=>{e.preventDefault();try{const id=view.GoogleSheetQuotes.extractSpreadsheetId(input.value);view.localStorage.setItem(KEY,id);input.value=id;status.textContent='SAVED';}catch(_){status.textContent='TRADES_SOURCE_INVALID';}});
  remove.addEventListener('click',()=>{try{view.localStorage.removeItem(KEY);input.value='';status.textContent='REMOVED';}catch(_){status.textContent='STORAGE_UNAVAILABLE';}});
 }
 return Object.freeze({RANGE,parse,markers,source,read,mountSettings});
});
