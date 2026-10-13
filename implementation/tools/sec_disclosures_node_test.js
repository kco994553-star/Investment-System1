'use strict';
// SEC 8-K disclosures reader: validation fails closed, one chronological list, grouping, fetch options. Synthetic data only.
const assert=require('node:assert/strict'),test=require('node:test');
const api=require('../src/investment_system/product/web_assets/sec-disclosures.js'),screens=require('../src/investment_system/product/web_assets/public-screens.js');
const fixture=require('./sec_disclosures_fixture.js'),{EMPTY}=require('./empty_public_screens.js');
test('synthetic and empty build payloads validate; score effect is NONE',()=>{const p=fixture.payload();assert.equal(p.events.length,5);assert.equal(p.score_effect,'NONE');
 assert.equal(api.validate(EMPTY['sec-disclosures.json']).state,'NOT_AVAILABLE');assert.equal(EMPTY['sec-disclosures.json'].events.length,0);});
test('8-K and 8-K/A of one event share a group; amendments are REPEAT',()=>{const p=fixture.payload(),byAcc=Object.fromEntries(p.events.map(e=>[e.accession.slice(-3),e]));
 assert.equal(byAcc['101'].occurrence,'NEW');assert.equal(byAcc['140'].occurrence,'REPEAT');assert.equal(byAcc['140'].group_id,byAcc['101'].group_id);
 assert.deepEqual(p.events.map(e=>e.classification),['OTHER','MATERIAL_AGREEMENT','OFFICERS_DIRECTORS','RESULTS','RESULTS']);});
test('bodies, prices, score changes, reordering and forged links fail closed',()=>{for(const mutate of [p=>p.events[0].body='text',p=>p.events[0].price=1,p=>p.score_effect='Q',p=>p.events.reverse(),
  p=>p.events[0].link='https://example.com/',p=>p.events[0].exhibit_99_1.title='<b>x</b>',p=>p.events[3].occurrence='NEW',p=>p.events[0].items=['99.99'],p=>p.channel='NEWS',p=>p.companies.nvda.state='STALE',p=>delete p.companies.asml]){
  const p=structuredClone(fixture.payload());mutate(p);assert.throws(()=>api.validate(p),/SEC_DISCLOSURES_INVALID/);}});
test('one chronological list: disclosures and later news items merge by time, filtered by company',()=>{const p=fixture.payload(),news={channel:'NEWS',time:p.events[1].accepted_at.replace(/:\d\d\+/,':59+'),company_id:'msft'};
 const rows=api.timeline(p,{news:[news]});assert.deepEqual(rows.map(r=>r.channel),['DISCLOSURE','NEWS','DISCLOSURE','DISCLOSURE','DISCLOSURE','DISCLOSURE']);
 assert.deepEqual(api.timeline(p,{companyIds:['nvda']}).map(r=>r.event.form),['8-K/A','8-K']);assert.deepEqual(api.CHANNELS.DISCLOSURE,['공시·확정','Disclosure · confirmed']);assert.deepEqual(api.CHANNELS.NEWS,['뉴스·신호','News · signal']);
 assert.equal(api.classLabel('RESULTS',false,['2.02']),'실적 (Results)');assert.equal(api.classLabel('OTHER',false,['7.01','9.01']),'공정공시(Regulation FD) (Regulation FD Disclosure)');assert.equal(api.classLabel('OTHER',true,['9.01']),'Financial Statements and Exhibits (재무제표 및 첨부서류)');assert.equal(api.classLabel('OTHER',false,[]),'기타 공시 (Other disclosure)');});
test('fetch omits credentials, cache and redirects; 404, invalid and oversized files read as not connected',async()=>{const calls=[];const p=fixture.payload();
 assert.equal((await api.load({fetch:async(name,o)=>{calls.push([name,o]);return{ok:true,text:async()=>JSON.stringify(p)};}})).events.length,5);
 assert.equal(calls[0][0],'sec-disclosures.json');assert.ok(calls.every(([,o])=>o.cache==='no-store'&&o.credentials==='omit'&&o.redirect==='error'));
 assert.equal(await api.load({fetch:async()=>({ok:false,status:404})}),null);assert.equal(await api.load({fetch:async()=>({ok:true,text:async()=>'{"kind":"SEC_DISCLOSURES"}'})}),null);
 assert.equal(await api.load({fetch:async()=>({ok:true,text:async()=>' '.repeat(2*1024*1024+1)})}),null);assert.equal(await api.load({fetch:async()=>{throw Error('PRIVATE_TEST_DIAGNOSTIC');}}),null);});
test('filing windows: a results 8-K flips the latest quarter from ESTIMATED to CONFIRMED',()=>{const w=fixture.filingWindows();assert.equal(screens.validate('sec-filing-windows.json',w).state,'LIVE');
 const s=screens.earningsStatus(w.data.companies.nvda);assert.equal(s.status,'CONFIRMED');assert.equal(s.date,w.data.companies.nvda.confirmed_earnings_date);
 const before=structuredClone(w);before.data.companies.nvda.earnings_confirmation=null;before.data.companies.nvda.confirmed_earnings_date=null;assert.equal(screens.earningsStatus(screens.validate('sec-filing-windows.json',before).data.companies.nvda).status,'ESTIMATED');
 const forged=structuredClone(w);forged.data.companies.nvda.confirmed_earnings_date=forged.data.companies.nvda.earnings_confirmation.period_end;assert.throws(()=>screens.validate('sec-filing-windows.json',forged));});
