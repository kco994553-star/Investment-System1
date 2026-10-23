'use strict';const test=require('node:test'),assert=require('node:assert/strict'),api=require('../src/investment_system/product/web_assets/watchlist.js');
const tickers=['ASML','LRCX','KLAC','8035','042700','NVDA','AMD','AVGO','QCOM','INTC','MSFT','GOOGL','AMZN','RTX','SYK','ETN','HUBB','GEV','ROK'],catalog={schema:'DEVICE_ACTUAL_CATALOG/1',instruments:tickers.map(ticker=>({ticker,label:ticker,price:123,market_cap_rank:999}))};
test('identity projection omits all prices/ranks and source order',()=>{const a=api.identities(catalog),b=api.identities({...catalog,instruments:[...catalog.instruments].reverse()});assert.deepEqual(a,b);assert.ok(a.every(r=>Object.keys(r).sort().join(',')==='company_id,identity_only,name,ticker'));assert.throws(()=>api.identities({...catalog,instruments:[...catalog.instruments.slice(1),catalog.instruments[1]]}));});
test('favorite, multiple-group, added-order and name filters preserve caller data',()=>{const rows=api.identities(catalog),p={interests:['nvda','amd'],groups:[{id:'a',members:['nvda']},{id:'b',members:['nvda','amd']}]},before=JSON.stringify([rows,p]);assert.deepEqual(api.filter(rows,p,{onlyInterest:true,sort:'added'}).map(x=>x.company_id),['nvda','amd']);assert.deepEqual(api.filter(rows,p,{group:'a'}).map(x=>x.company_id),['nvda']);assert.equal(api.filter(rows,p,{group:'b'}).length,2);assert.deepEqual(api.filter(rows,p,{query:'syk'}).map(x=>x.company_id),['stry']);assert.equal(JSON.stringify([rows,p]),before);});
/* Owner decision 2026-10-23 (TARGET v0 결합 해소) + IA-7: watch/group keys = Issuer ('sec:'+CIK10), chart drawings = Listing
   (Universe code). Any company with an issuer key can be watched; old TARGET company_id records are read and mapped. */
const names=require('../src/investment_system/product/web_assets/entity-search.js').nameIndex(JSON.parse(require('node:fs').readFileSync(require('node:path').join(__dirname,'../src/investment_system/product/web_assets/company-names-ko.json'),'utf8')));
const universe=JSON.parse(require('node:fs').readFileSync(require('node:path').join(__dirname,'../src/investment_system/universe/universe_codes_v1.json'),'utf8'));
test('issuer and listing keys cover TARGET aliases and every Universe504 code',()=>{assert.ok(api.useNames(names));
 assert.equal(api.issuerOf('nvda'),'sec:0001045810');assert.equal(api.issuerOf('NASDAQ:NVDA'),'sec:0001045810');assert.equal(api.issuerOf('stry'),'sec:0000310764');
 assert.equal(api.issuerOf('hanmi'),'hanmi');assert.equal(api.issuerOf('tokyo_electron'),'tokyo_electron');// non-SEC issuers keep the TARGET alias
 assert.equal(api.issuerOf('NASDAQ:GOOG'),api.issuerOf('NASDAQ:GOOGL'));assert.equal(api.issuerOf('NASDAQ:GOOG'),api.issuerOf('googl'));// one issuer, two listings
 assert.equal(api.listingOf('stry'),'NYSE:SYK');assert.equal(api.listingOf('hanmi'),'KRX:042700');assert.equal(api.providerSymbol('hanmi'),'042700.KS');assert.equal(api.providerSymbol('tokyo_electron'),'8035.T');
 for(const id of ['','aapl','AAPL','COMPANY:nvda','__proto__','toString','NYSE:NOPE',null])assert.equal(api.issuerOf(id),null,String(id));
 const outside=[];for(const code of universe){const k=api.issuerOf(code);if(!k)outside.push(code);else assert.match(k,/^sec:\d{10}$/);assert.equal(api.listingOf(code),code);}
 assert.equal(outside.length,0,'every Universe504 code has an issuer key (CIK)');
 assert.ok(api.directory().length>=universe.length,'the company directory is not the 19 TARGET rows');
 assert.deepEqual(api.entitiesOf('sec:0001652044'),['googl','NASDAQ:GOOG']);assert.equal(api.primaryOf('sec:0001652044'),'googl');
 const aapl=api.issuerOf('NASDAQ:AAPL');assert.deepEqual(api.entitiesOf(aapl),['NASDAQ:AAPL']);assert.equal(api.providerSymbol('NYSE:BRK.B'),'BRK-B');});
test('a TARGET row whose names-table CIK or listing disagrees is not used to key a code',()=>{const bad={codes:()=>[['NASDAQ:NVDA','nvda']],get:()=>({cik:'0000000001'})};assert.ok(api.useNames(bad));assert.equal(api.issuerOf('NASDAQ:NVDA'),'sec:0001045810');assert.ok(api.useNames(names));});
test('old TARGET company_id records are read as issuer keys; unknown keys are kept, nothing dropped',()=>{api.useNames(names);const old={version:1,interests:['nvda','NASDAQ:AAPL','googl','NASDAQ:GOOG','hanmi','legacy_x'],groups:[{id:'g',name:'G',members:['nvda','legacy_x']}]},before=JSON.stringify(old);
 const m=api.migrate(old);assert.equal(JSON.stringify(old),before,'the old record object is not changed');assert.ok(m.changed);
 assert.deepEqual(m.prefs.interests,['sec:0001045810',api.issuerOf('NASDAQ:AAPL'),'sec:0001652044','hanmi','legacy_x']);assert.deepEqual(m.prefs.groups[0].members,['sec:0001045810','legacy_x']);
 assert.equal(api.migrate(m.prefs).changed,false,'migration is idempotent');
 assert.ok(api.watched(m.prefs,'nvda')&&api.watched(m.prefs,'NASDAQ:NVDA')&&api.watched(old,'NASDAQ:NVDA'),'old and new keys both read');
 assert.deepEqual(api.pageIds(m.prefs.interests),['nvda','NASDAQ:AAPL','googl','hanmi','legacy_x']);
 assert.ok(api.allIds(m.prefs.interests).includes('NASDAQ:GOOG')&&api.allIds(m.prefs.interests).includes('googl'));
 const rows=api.watchRows(m.prefs);assert.deepEqual(rows.map(r=>r.ticker),['NVDA','AAPL','GOOGL','042700','legacy_x']);
 const all=api.directory(),shown=api.filter(all,m.prefs,{onlyInterest:true,sort:'added'});assert.deepEqual(shown.map(r=>r.company_id),['nvda','NASDAQ:AAPL','googl','NASDAQ:GOOG','hanmi']);
 assert.deepEqual(api.filter(all,m.prefs,{group:'g'}).map(r=>r.company_id),['nvda']);});
test('Worker allowlist covers every Universe504 and TARGET listing (no widening needed)',()=>{const src=require('node:fs').readFileSync(require('node:path').join(__dirname,'../worker/src/index.js'),'utf8');
 const us=new Set(JSON.parse('['+src.slice(src.indexOf('const US_SYMBOLS = [')+20,src.indexOf('];',src.indexOf('const US_SYMBOLS = ['))).replace(/'/g,'"').replace(/,\s*$/,'')+']'));
 const markets=new Set([...us,'042700.KS','8035.T']);api.useNames(names);
 for(const code of universe)assert.ok(markets.has(api.providerSymbol(code)),code);for(const id of Object.keys(api.TARGET))assert.ok(markets.has(api.providerSymbol(id)),id);
 assert.ok(src.includes("MARKETS.set('042700.KS'")&&src.includes("MARKETS.set('8035.T'"));});
