'use strict';
// Pure parts of the display-only modules: TradingView symbol map/config and the company-logo source chain.
const test=require('node:test'),assert=require('node:assert/strict');
const TV=require('../src/investment_system/product/web_assets/tradingview-widgets.js');
const LOGO=require('../src/investment_system/product/web_assets/company-logos.js');
const IDS=['asml','lrcx','klac','nvda','amd','avgo','qcom','intc','msft','googl','amzn','rtx','stry','etn','hubb','gev','rok','hanmi','tokyo_electron'];
function memory(init={}){const m=new Map(Object.entries(init));return{getItem:k=>m.has(k)?m.get(k):null,setItem:(k,v)=>m.set(k,String(v)),removeItem:k=>m.delete(k),dump:()=>Object.fromEntries(m)};}
const broken={getItem(){throw Error('denied');},setItem(){throw Error('denied');},removeItem(){throw Error('denied');}};

test('TradingView maps exactly the TARGET 19 to exchange-prefixed symbols',()=>{
 assert.deepEqual(Object.keys(TV.SYMBOLS).sort(),[...IDS].sort());
 assert.ok(Object.values(TV.SYMBOLS).every(s=>/^(NASDAQ|NYSE|AMEX|KRX|TSE):[A-Z0-9]+$/.test(s)));
 assert.equal(TV.symbolFor('stry'),'NYSE:SYK');assert.equal(TV.symbolFor('hanmi'),'KRX:042700');assert.equal(TV.symbolFor('tokyo_electron'),'TSE:8035');
 assert.equal(TV.symbolFor('nope'),null);assert.equal(TV.symbolFor('__proto__'),null);
 assert.equal(TV.availability('TSE:8035'),'NOT_DISPLAYED');assert.equal(TV.availability('KRX:042700'),'UNVERIFIED');assert.equal(TV.availability('NASDAQ:NVDA'),'AVAILABLE');
});
test('TradingView configs carry symbols and display options only, from fixed script URLs',()=>{
 const tape=TV.config('ticker',null,'ko-KR');
 assert.equal(tape.symbols.length,18);assert.ok(!tape.symbols.some(s=>s.proName==='TSE:8035'));assert.equal(tape.locale,'kr');
 for(const c of [tape,TV.config('mini','NASDAQ:NVDA','en-US'),TV.config('advanced','NYSE:SYK','ko-KR')]){
  assert.ok(!/price|quantity|cost|amount|token|sheet|holding|weight/i.test(JSON.stringify(Object.keys(c))));
 }
 assert.equal(TV.config('advanced','NYSE:SYK','en-US').allow_symbol_change,false);
 assert.ok(Object.values(TV.SCRIPTS).every(u=>u.startsWith('https://s3.tradingview.com/external-embedding/embed-widget-')));
});
test('TradingView switch defaults on, survives storage failures and stores only on/off',()=>{
 const s=memory();assert.equal(TV.enabled(s),true);assert.equal(TV.setEnabled(s,false),true);assert.deepEqual(s.dump(),{'investment.web.v1.tradingview-widgets':'off'});assert.equal(TV.enabled(s),false);
 TV.setEnabled(s,true);assert.deepEqual(s.dump(),{});assert.equal(TV.enabled(broken),true);assert.equal(TV.setEnabled(broken,false),false);
});
test('logo settings default on, validate the key and fail closed on storage errors',()=>{
 assert.deepEqual(LOGO.settings(memory()),{enabled:true,provider:'none',key:''});
 assert.deepEqual(LOGO.settings(broken),{enabled:true,provider:'none',key:''});
 assert.deepEqual(LOGO.settings(memory({'investment.web.v1.logo-provider':'evil','investment.web.v1.logo-key':'bad key!'})),{enabled:true,provider:'none',key:''});
 const s=memory();assert.equal(LOGO.save(s,{enabled:false,provider:'logodev',key:'pk_ABCDEFGH123'}),true);
 assert.deepEqual(LOGO.settings(s),{enabled:false,provider:'logodev',key:'pk_ABCDEFGH123'});
 LOGO.save(s,{enabled:true,provider:'none',key:null});assert.deepEqual(s.dump(),{});
});
test('logo source chain: key service first, then the fixed favicon origin; no key means favicon only',()=>{
 assert.deepEqual(LOGO.sources('nvidia.com',{provider:'none',key:''}).map(x=>x.kind),['favicon']);
 const ld=LOGO.sources('nvidia.com',{provider:'logodev',key:'pk_ABCDEFGH123'});
 assert.deepEqual(ld.map(x=>x.kind),['logodev','favicon']);
 assert.equal(ld[0].url,'https://img.logo.dev/nvidia.com?token=pk_ABCDEFGH123&size=64&format=png');assert.equal(ld[0].referrer,'no-referrer');
 assert.equal(ld[1].url,'https://icons.duckduckgo.com/ip3/nvidia.com.ico');assert.equal(ld[1].referrer,'no-referrer');
 const bf=LOGO.sources('nvidia.com',{provider:'brandfetch',key:'client1234'});
 assert.equal(bf[0].url,'https://cdn.brandfetch.io/nvidia.com?c=client1234');assert.equal(bf[0].referrer,null,'Brandfetch needs the Referer');
 assert.deepEqual(LOGO.sources('nvidia.com',{provider:'logodev',key:''}).map(x=>x.kind),['favicon']);
 for(const s of [...ld,...bf])assert.ok(Object.values(LOGO.ORIGINS).includes(new URL(s.url).origin));
});
test('logo identity: codes, TARGET ids and device tickers resolve to catalog codes; letters and colors are stable',()=>{
 assert.deepEqual(LOGO.codeCandidates('NYSE:MMM'),['NYSE:MMM']);assert.deepEqual(LOGO.codeCandidates('stry'),['NYSE:SYK']);
 assert.deepEqual(LOGO.codeCandidates('042700.KS'),['KRX:042700']);assert.deepEqual(LOGO.codeCandidates('042700'),['KRX:042700']);
 assert.deepEqual(LOGO.codeCandidates('8035.T'),['TYO:8035']);assert.deepEqual(LOGO.codeCandidates('BRK-B'),['NASDAQ:BRK.B','NYSE:BRK.B','BATS:BRK.B']);
 assert.equal(LOGO.letter('nvda'),'N');assert.equal(LOGO.letter('042700.KS'),'0');assert.equal(LOGO.letter(''),'?');
 assert.equal(LOGO.colorIndex('NVDA'),LOGO.colorIndex('nvda'));assert.ok(LOGO.colorIndex('NVDA')>=0&&LOGO.colorIndex('NVDA')<12);
 assert.equal(new Set(['A','B','C','D','E','F','G','H','I','J','K','L','M','N'].map(LOGO.colorIndex)).size>3,true);
 assert.ok(!LOGO.html('<x>').includes('<x>'));assert.ok(LOGO.html('NVDA',40).includes('co-logo-40'));
});
test('device backup never carries the logo key or display switches',()=>{
 const src=require('node:fs').readFileSync(require('node:path').join(__dirname,'../src/investment_system/product/web_assets/device-backup.js'),'utf8');
 for(const k of [...Object.values(LOGO.KEYS),TV.STORAGE_KEY])assert.ok(!src.includes(k));
 assert.ok(!/Object\.keys\(\s*(view\.)?localStorage|localStorage\.key\(/.test(src),'backup reads named keys only');
});
test('logo catalog parser accepts domains only and drops anything else',()=>{
 const ok=LOGO.parseCatalog({schema:'universe-domains/1',rows:[['NASDAQ:NVDA','nvidia.com','manual'],['NYSE:MMM',null,null],['NYSE:X','https://evil.com/x','sec'],['bad code','a.com','sec']]});
 assert.deepEqual([...ok],[['NASDAQ:NVDA','nvidia.com']]);
 assert.equal(LOGO.parseCatalog({schema:'universe-domains/1',rows:[],price:1}).size,0);assert.equal(LOGO.parseCatalog(null).size,0);
 assert.equal(LOGO.domainFor('nvda',ok),'nvidia.com');assert.equal(LOGO.domainFor('NVDA',ok),'nvidia.com');assert.equal(LOGO.domainFor('AMD',ok),null);
});
