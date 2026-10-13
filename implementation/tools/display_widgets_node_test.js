'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const TV=require('../src/investment_system/product/web_assets/tradingview-widgets.js'),LOGO=require('../src/investment_system/product/web_assets/company-logos.js');
function memory(init={}){const m=new Map(Object.entries(init));return{getItem:k=>m.has(k)?m.get(k):null,setItem:(k,v)=>m.set(k,String(v)),removeItem:k=>m.delete(k),dump:()=>Object.fromEntries(m)};}
const broken={getItem(){throw Error('denied');},setItem(){throw Error('denied');},removeItem(){throw Error('denied');}};
test('TradingView defaults off including unavailable storage; opt-in is device only',()=>{
 const store=memory();assert.equal(TV.enabled(store),false);assert.equal(TV.enabled(broken),false);assert.equal(TV.setEnabled(broken,true),false);
 TV.setEnabled(store,true);assert.equal(TV.enabled(store),true);assert.deepEqual(store.dump(),{[TV.STORAGE_KEY]:'on'});
 TV.setEnabled(store,false);assert.equal(TV.enabled(store),false);
});
test('direct frame symbols remain public display-only config; no third-party application script',()=>{
 assert.equal(Object.keys(TV.SYMBOLS).length,19);assert.equal(TV.availability('TSE:8035'),'UNVERIFIED');assert.equal(TV.availability('KRX:042700'),'UNVERIFIED');
 assert.equal(TV.tickerSymbols('ko-KR').length,19);
 for(const url of Object.values(TV.FRAMES))assert.equal(new URL(url).origin,'https://www.tradingview-widget.com');
 const source=fs.readFileSync(path.join(__dirname,'../src/investment_system/product/web_assets/tradingview-widgets.js'),'utf8');
 assert.ok(!/createElement\(['"]script/.test(source));assert.ok(source.includes('종목명이 TradingView로 전달됩니다'));
 for(const config of [TV.config('ticker',null,'ko-KR'),TV.config('mini','NASDAQ:NVDA','en-US')])assert.ok(!/quantity|cost|amount|token|sheet|holding/i.test(JSON.stringify(Object.keys(config))));
});
test('company logos accept bundled PNG data only, rejecting arbitrary URLs or mutable extra fields',()=>{
 const image='data:image/png;base64,aW1hZ2U=';
 const map=LOGO.parseCatalog({schema:'company-logos/1',rows:[['NASDAQ:NVDA',image,'WIKIDATA'],['NYSE:X','https://external.invalid/logo.png','WIKIDATA'],['NYSE:MMM',null,null]]});
 assert.deepEqual([...map],[['NASDAQ:NVDA',image]]);assert.deepEqual(LOGO.sources(image).map(x=>x.kind),['bundled']);assert.deepEqual(LOGO.sources('https://external.invalid/logo.png'),[]);
 assert.equal(LOGO.parseCatalog({schema:'company-logos/1',rows:[],price:1}).size,0);
 assert.deepEqual(LOGO.settings(memory()),{enabled:true});assert.equal(LOGO.save(memory(),{enabled:false}),true);
});
test('stable initials remain available for missing logos and backup excludes display settings',()=>{
 assert.equal(LOGO.letter('nvda'),'N');assert.equal(LOGO.letter('042700.KS'),'0');assert.ok(!LOGO.html('<x>').includes('<x>'));
 const source=fs.readFileSync(path.join(__dirname,'../src/investment_system/product/web_assets/device-backup.js'),'utf8');
 for(const key of [...Object.values(LOGO.KEYS),TV.STORAGE_KEY])assert.ok(!source.includes(key));
});
