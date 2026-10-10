'use strict';const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs');
const path='../src/investment_system/product/web_assets/google-sheet-setup.js';const api=fs.existsSync(require('node:path').join(__dirname,path))?require(path):{};
const catalog={instruments:['ASML','LRCX','KLAC','8035','042700','NVDA','AMD','AVGO','QCOM','INTC','MSFT','GOOGL','AMZN','RTX','SYK','ETN','HUBB','GEV','ROK'].map(ticker=>({ticker}))};
test('sheet template creates exact tabs, header contracts, TARGET quotes and source codes with formulas',()=>{
 const seed={schema:'universe-codes/1',codes:['NASDAQ:NVDA','NYSE:ETN','KRX:042700']},body=api.template(catalog,seed);
 assert.equal(body.properties.title,'Investment Cockpit Data');assert.deepEqual(body.sheets.map(s=>s.properties.title),['Quotes','Trades','Universe']);
 for(const s of body.sheets){assert.ok(s.properties.gridProperties.columnCount<=4);assert.ok(s.properties.gridProperties.rowCount>=1025);}
 const quotes=body.sheets[0].data[0].rowData;assert.equal(quotes.length,20);assert.equal(quotes[1].values[0].userEnteredValue.stringValue,'NASDAQ:ASML');assert.ok(quotes[1].values[1].userEnteredValue.formulaValue.includes('GOOGLEFINANCE(A2,"price")'));assert.ok(quotes[1].values[2].userEnteredValue.formulaValue.includes('"tradetime"'));
 const universe=body.sheets[2].data[0].rowData;assert.equal(universe.length,4);assert.equal(universe[1].values[0].userEnteredValue.stringValue,'NASDAQ:NVDA');assert.ok(universe[1].values[1].userEnteredValue.formulaValue.includes('"marketcap"'));assert.ok(universe[1].values[2].userEnteredValue.formulaValue.includes('"price"'));assert.deepEqual(seed.codes,['NASDAQ:NVDA','NYSE:ETN','KRX:042700']);
});
test('missing seed creates header-only Universe; invalid supplied seeds are rejected',()=>{
 assert.equal(api.template(catalog,null).sheets[2].data[0].rowData.length,1);assert.equal(api.template(catalog).sheets[2].data[0].rowData.length,1);
 for(const seed of [[],{schema:'universe-codes/1',codes:[]},{schema:'universe-codes/1',codes:['NASDAQ:NVDA'],price:100},{schema:'universe-codes/1',codes:['=IMPORTDATA("x")']},{schema:'universe-codes/1',codes:['NASDAQ:NVDA','NASDAQ:NVDA']},{schema:'universe-codes/1',codes:Array(1025).fill('NASDAQ:NVDA')}])assert.throws(()=>api.template(catalog,seed));
});
test('header checks never expose original private cells and provide fixed repairs',()=>{
 const result=api.checkHeaders(['Quotes','Trades','Universe'],{Quotes:['code','price','tradetime'],Trades:['date','symbol','B/S','quantity'],Universe:['code','marketcap','price']});assert.equal(result.ready,true);assert.equal(result.tabs.length,3);
 const bad=api.checkHeaders(['Quotes'],{Quotes:['private text','price','tradetime']});assert.equal(bad.ready,false);assert.ok(!JSON.stringify(bad).includes('private text'));assert.ok(bad.tabs.every(t=>typeof t.fix==='string'));
});
test('unified source stays device-only and exact tab ranges do not accept another host',()=>{
 const values=new Map(),view={localStorage:{getItem:k=>values.get(k)||null,setItem:(k,v)=>values.set(k,v),removeItem:k=>values.delete(k)},GoogleSheetQuotes:require('../src/investment_system/product/web_assets/google-sheet-quotes.js')};
 const id='a'.repeat(30);api.source(view,id);assert.equal(api.source(view),id);assert.equal(api.range('Trades'),"'Trades'!A1:D1025");assert.throws(()=>api.range('unknown'));assert.throws(()=>api.source(view,'https://other.test/'+id));
});
