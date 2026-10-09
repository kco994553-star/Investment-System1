/* Only synthetic daily bars are tested; assertion messages never include payloads. */
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const file = require('node:path').join(__dirname, '../src/investment_system/product/web_assets/private-history.js');
const api = fs.existsSync(file) ? require(file) : {};
function daily() {
  return {schema:'private-history/1',provider:'Yahoo Finance(비공식)',symbol:'NVDA',range:'1y',currency:'USD',exchange:'NMS',timezone:'America/New_York',interval:'1d',basis:'RAW_CLOSE',delay_status:'UNKNOWN',read_at:'2030-01-08T12:00:00.000Z',bars:[
    {timestamp:1893844800,open:40,high:43,low:39,close:42,adjusted_close:420,volume:100,session_status:'COMPLETE'},
    {timestamp:1893931200,open:null,high:null,low:null,close:null,adjusted_close:430,volume:null,session_status:'UNKNOWN'},
    {timestamp:1894017600,open:43,high:45,low:42,close:44,adjusted_close:440,volume:110,session_status:'IN_PROGRESS'}]};
}
test('private history exports work without initiating requests', () => {
  for(const name of ['mount','mountSettings','disposeAll','validateHistory','chartPaths','symbolFor','parseWorkerOrigin']) assert.equal(typeof api[name], 'function', name + ' available');
});
test('history targets are limited to existing TARGET19 identities', () => {
  const mappings={asml:'ASML',lrcx:'LRCX',klac:'KLAC',nvda:'NVDA',amd:'AMD',avgo:'AVGO',qcom:'QCOM',intc:'INTC',msft:'MSFT',googl:'GOOGL',amzn:'AMZN',rtx:'RTX',stry:'SYK',etn:'ETN',hubb:'HUBB',gev:'GEV',rok:'ROK',hanmi:'042700.KS',tokyo_electron:'8035.T'};
  for(const [id,symbol] of Object.entries(mappings)) assert.ok(api.symbolFor(id)===symbol,'approved identity resolves');
  for(const id of ['aapl','NVDA','COMPANY:nvda','toString','__proto__','']) assert.ok(api.symbolFor(id)===null,'unapproved identity has no history');
});
test('worker settings accept only lowercase HTTPS workers.dev root origins', () => {
  const origin='https://synthetic-history.example-account.workers.dev';
  assert.ok(api.parseWorkerOrigin(origin)===origin);
  assert.ok(api.parseWorkerOrigin(origin+'/')===origin);
  for(const value of ['',origin+'/history',origin+'?x=1',origin+'#x',origin+':443',origin.replace('https:','http:'),'https://user@synthetic-history.example-account.workers.dev','https://example-account.workers.dev','https://x.y.workers.dev.evil.test',' https://x.y.workers.dev','https://X.y.workers.dev','https://x..workers.dev']) assert.throws(()=>api.parseWorkerOrigin(value),{message:'REQUEST_INVALID'});
});
test('daily contract copies only approved fields and preserves nulls and adjusted close separately', () => {
  const source=daily();source.untrusted='private upstream message';source.bars[0].untrusted='private';
  const result=api.validateHistory(source,{symbol:'NVDA',range:'1y'});
  assert.ok(result!==source&&result.bars!==source.bars&&result.bars[0]!==source.bars[0]);
  assert.ok(result.bars[1].close===null&&result.bars[1].open===null&&result.bars[0].adjusted_close===420);
  assert.ok(!('untrusted' in result)&&!('untrusted' in result.bars[0]));
});
test('invalid daily contracts fail closed with a fixed format code', () => {
  const changes=[p=>p.schema='other',p=>p.provider='private upstream',p=>p.symbol='MSFT',p=>p.range='5y',p=>p.interval='1h',p=>p.basis='ADJUSTED_CLOSE',p=>p.currency='private text',p=>p.read_at='yesterday',p=>p.bars[0].close=Infinity,p=>p.bars[0].session_status='DONE',p=>delete p.bars[0].volume,p=>p.bars[1].timestamp=p.bars[0].timestamp,p=>p.bars[0].timestamp=1.5,p=>p.timezone='private\ntext'];
  for(const change of changes){const p=daily();change(p);assert.throws(()=>api.validateHistory(p,{symbol:'NVDA',range:'1y'}),{message:'YAHOO_FORMAT_CHANGED'});}
});
test('raw-close chart segments leave gaps without using adjusted closes', () => {
  const p=daily();const paths=api.chartPaths(p.bars);
  assert.ok(paths.length===2,'missing close splits the path');
  const changed=daily();changed.bars.forEach(b=>b.adjusted_close=999999);
  assert.ok(JSON.stringify(api.chartPaths(changed.bars))===JSON.stringify(paths),'adjusted closes cannot change raw-close plot');
  assert.ok(api.chartPaths(p.bars.map(b=>({...b,close:null}))).length===0,'no known closes renders no paths');
});

test('daily history rejects zero prices, wrong listing currency and future bars', () => {
  const changes=[p=>p.currency='EUR',p=>p.bars[0].close=0,p=>p.bars[0].open=0,p=>p.bars[0].high=0,p=>p.bars[0].low=0,p=>p.bars[0].adjusted_close=0,p=>p.bars[2].timestamp=Date.parse(p.read_at)/1000+1];
  for(const change of changes){const p=daily();change(p);assert.throws(()=>api.validateHistory(p,{symbol:'NVDA',range:'1y'}),{message:'YAHOO_FORMAT_CHANGED'});}
  for(const [symbol,currency] of [['042700.KS','KRW'],['8035.T','JPY']]){const p=daily();p.symbol=symbol;p.currency=currency;assert.ok(api.validateHistory(p,{symbol,range:'1y'}).currency===currency);}
  const p=daily();p.bars[0].volume=0;assert.ok(api.validateHistory(p,{symbol:'NVDA',range:'1y'}).bars[0].volume===0,'zero volume remains valid');
});
test('no bars or no known raw closes are unavailable', () => {
  const empty=daily();empty.bars=[];assert.throws(()=>api.validateHistory(empty,{symbol:'NVDA',range:'1y'}),{message:'HISTORY_UNAVAILABLE'});
  const missing=daily();missing.bars.forEach(bar=>bar.close=null);assert.throws(()=>api.validateHistory(missing,{symbol:'NVDA',range:'1y'}),{message:'HISTORY_UNAVAILABLE'});
});
test('finite extreme raw closes do not create invalid SVG coordinates', () => {
  const p=daily();p.bars[0].close=1;p.bars[2].close=Number.MAX_VALUE;
  assert.ok(api.chartPaths(p.bars).every(path=>!/(?:Infinity|NaN)/.test(path)),'finite prices stay finite when scaled for display');
});
test('isolated known closes have drawable marks on either side of a gap', () => {
  const paths=api.chartPaths(daily().bars);
  assert.ok(paths.length===2&&paths.every(path=>path.includes('L')),'a move-only SVG path would hide a known daily close');
});
