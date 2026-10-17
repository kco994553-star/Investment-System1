'use strict';const test=require('node:test'),assert=require('node:assert/strict'),api=require('../src/investment_system/product/web_assets/ops-status.js');
test('ops status uses public metadata only and never invents freshness thresholds',()=>{const now=Date.parse('2026-10-10T12:00:00Z');
 const rows=api.summarize({now,secReported:{companies:{a:{status:'LIVE',acquired_at:'2026-10-09T22:20:00Z',reason_codes:[]},b:{status:'NOT_AVAILABLE',acquired_at:null,reason_codes:['SEC_HTTP_503']},c:{status:'LIVE',acquired_at:'2026-10-09T22:25:00Z',reason_codes:[]}}},
  screens:{'sec-qg-factors.json':{state:'LIVE',as_of:'2026-10-08T00:00:00Z',stale_after_seconds:86400,reason_codes:[]},'macro-screen.json':{state:'NOT_AVAILABLE',as_of:'2026-10-10T00:00:00Z',stale_after_seconds:86400,reason_codes:['NO_ELIGIBLE_INPUT']}}});
 const by=Object.fromEntries(rows.map(r=>[r.id,r]));assert.equal(rows.length,7);
 assert.deepEqual([by['sec-public-inputs.json'].failed_companies,by['sec-public-inputs.json'].total_companies,by['sec-public-inputs.json'].last_success_at],[1,3,'2026-10-09T22:25:00.000Z']);assert.deepEqual(by['sec-public-inputs.json'].reason_codes,['SEC_HTTP_503']);assert.equal(by['sec-public-inputs.json'].stale,null);
 assert.equal(by['sec-qg-factors.json'].stale,true);assert.equal(by['macro-screen.json'].last_success_at,null);assert.equal(by['sec-13f-changes.json'].state,'NOT_AVAILABLE');assert.deepEqual(by['sec-13f-changes.json'].reason_codes,['NOT_CONNECTED']);
 assert.equal(api.summarize({}).every(r=>r.state==='NOT_AVAILABLE'),true);});
test('schema /4: new collections, kept previous rows, failures and withdrawals are counted apart, with each kept row age',()=>{
 const Sec=require('../src/investment_system/product/web_assets/sec-reported.js'),{mixed}=require('./sec_reported_fixture.js'),secReported=Sec.project(mixed());
 const now=Date.parse('2026-01-02T18:00:00Z'),c=api.collection({secReported,now});
 assert.equal(c.state,'INCOMPLETE');assert.equal(c.checked_at,'2026-01-02T12:05:00Z');assert.equal(c.trigger,'SCHEDULED');
 assert.deepEqual(c.counts,{companies:17,collected:14,collected_live:13,collected_na:1,preserved:1,failed:1,withdrawn:1});
 const by=Object.fromEntries(c.rows.map(r=>[r.company_id,r]));assert.deepEqual(Object.keys(by),['amd','asml','avgo']);
 assert.deepEqual([by.amd.run,by.amd.acquired_at,by.amd.elapsed_hours,by.amd.stale,by.amd.reason_codes],['PRESERVED','2026-01-01T12:00:00Z',30,true,['SEC_HTTP_503']]);
 assert.deepEqual([by.asml.run,by.asml.acquired_at,by.asml.detected_at],['WITHDRAWN',null,'2026-01-02T12:03:00Z']);assert.deepEqual([by.avgo.run,by.avgo.checked_at],['FAILED','2026-01-02T12:02:00Z']);
 assert.equal(api.collection({secReported,now:Date.parse('2026-01-02T00:00:00Z')}).rows[0].stale,false);
 // The table row: a policy NA after a successful collection is not a failure; kept, failed and withdrawn companies are.
 const row=api.summarize({secReported,now})[0];assert.deepEqual([row.failed_companies,row.total_companies,row.last_success_at],[3,17,'2026-01-02T12:00:00.000Z']);
 assert.ok(row.reason_codes.includes('SEC_HTTP_503')&&row.reason_codes.includes('SEC_CIK_MISMATCH'));
 // Older schemas have no run context: completeness is NOT_AVAILABLE, never guessed.
 const old=Sec.project(require('./sec_reported_fixture.js').fixture(3));assert.deepEqual([api.collection({secReported:old}).state,api.collection({secReported:old}).reason_codes],['NOT_AVAILABLE',['OLDER_SCHEMA']]);
 assert.equal(api.collection({}).reason_codes[0],'NOT_CONNECTED');
});
test('scheduled deploy streak is reported apart from completeness and only while its last scheduled day is current',()=>{
 const Sec=require('../src/investment_system/product/web_assets/sec-reported.js'),{fixture}=require('./sec_reported_fixture.js');
 const p=fixture(4),secReported=Sec.project(p);
 assert.deepEqual(api.deployStreak({secReported,now:Date.parse('2026-01-03T15:00:00Z')}),{target:7,count:3,since:'2025-12-31',last_run_day:'2026-01-02',state:'COUNTING',reason_codes:[]});
 assert.equal(api.deployStreak({secReported,now:Date.parse('2026-01-04T06:00:00Z')}).state,'BROKEN');   // New York 01:00 on 01-04: no deploy for 01-03
 assert.equal(api.deployStreak({secReported,now:Date.parse('2026-01-04T04:00:00Z')}).state,'COUNTING'); // still 01-03 in New York
 p.collection.scheduled_streak={count:7,since:'2025-12-27',last_run_day:'2026-01-02'};assert.equal(api.deployStreak({secReported:Sec.project(p),now:Date.parse('2026-01-02T13:00:00Z')}).state,'MET');
 p.collection.scheduled_streak={count:null,since:null,last_run_day:'2026-01-02'};assert.deepEqual(api.deployStreak({secReported:Sec.project(p)}).reason_codes,['PREVIOUS_COPY_UNREAD']);
 p.collection.trigger='MANUAL';p.collection.scheduled_streak={count:null,since:null,last_run_day:null};assert.equal(api.deployStreak({secReported:Sec.project(p)}).state,'NOT_AVAILABLE');
 assert.equal(api.deployStreak({secReported:Sec.project(fixture(3))}).state,'NOT_AVAILABLE');
});
