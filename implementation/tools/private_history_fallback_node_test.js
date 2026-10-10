'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const History=require('../src/investment_system/product/web_assets/private-history.js'),Trades=require('../src/investment_system/product/web_assets/private-trades.js');
function fixture(provider='Tiingo EOD',symbol='NVDA') {return {schema:'private-history/1',provider,symbol,range:'1mo',currency:symbol==='042700.KS'?'KRW':'USD',exchange:symbol==='042700.KS'?'KOSPI':'NASDAQ',timezone:symbol==='042700.KS'?'Asia/Seoul':'America/New_York',interval:'1d',basis:'RAW_CLOSE',delay_status:'UNKNOWN',timestamp_kind:'PROVIDER_SESSION_LABEL',read_at:'2026-10-10T12:00:00Z',bars:[{timestamp:Date.UTC(2026,9,8)/1000,session_date:'2026-10-08',open:100,high:104,low:98,close:102,adjusted_close:91,volume:10,session_status:'COMPLETE'}]};}
test('fallback dates survive normalization and B/S matches the provider session, not previous US UTC date',()=>{
 const raw=fixture(),v=History.validateHistory(raw,{symbol:raw.symbol,range:raw.range});assert.equal(v.timestamp_kind,'PROVIDER_SESSION_LABEL');assert.equal(v.bars[0].session_date,'2026-10-08');
 const rows=[{state:'USER_DEVICE_ONLY',symbol:'NVDA',date:'2026-10-08',side:'B',quantity:1},{state:'USER_DEVICE_ONLY',symbol:'NVDA',date:'2026-10-07',side:'S',quantity:1}];const markers=Trades.markers({rows},v.bars,'NVDA',v.timezone);assert.equal(markers.length,1);assert.equal(markers[0].side,'B');
});
test('fallback market/provider/date contracts reject wrong source, labels and adjusted intraday masquerading',()=>{
 for(const change of [p=>p.symbol='8035.T',p=>delete p.timestamp_kind,p=>delete p.bars[0].session_date,p=>p.bars[0].session_date='2026-10-07',p=>p.bars[0].session_date='2026-02-30',p=>p.bars[0].timestamp+=3600,p=>p.bars[0].session_date='2026-10-11',p=>p.timezone='Asia/Seoul']){const p=fixture();change(p);assert.throws(()=>History.validateHistory(p,{symbol:p.symbol,range:p.range}),{message:'YAHOO_FORMAT_CHANGED'});}
 const p=fixture('KRX OPEN API','042700.KS');assert.equal(History.validateHistory(p,{symbol:p.symbol,range:p.range}).provider,p.provider);
});
test('current Korean session labels may precede their synthetic UTC timestamp but remain UNKNOWN',()=>{
 const p=fixture('KRX OPEN API','042700.KS');p.read_at='2026-10-07T17:00:00Z';p.bars[0].session_status='UNKNOWN';assert.equal(History.validateHistory(p,{symbol:p.symbol,range:p.range}).bars[0].session_status,'UNKNOWN');p.bars[0].session_status='COMPLETE';assert.throws(()=>History.validateHistory(p,{symbol:p.symbol,range:p.range}),{message:'YAHOO_FORMAT_CHANGED'});
});
