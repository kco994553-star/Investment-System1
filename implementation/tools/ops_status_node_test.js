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
test('scheduled deploy streak: an estimate from the published copy, counted from 2026-10-19, current only while its last scheduled day is',()=>{
 const Sec=require('../src/investment_system/product/web_assets/sec-reported.js'),{fixture}=require('./sec_reported_fixture.js');
 const realNow=Date.now;Date.now=()=>Date.parse('2026-11-01T00:00:00Z');   // the reader refuses future times
 try{
  const at=(day,trigger,streak)=>{const p=fixture(4);p.collection={...p.collection,checked_at:day+'T22:20:00Z',run_day:day,trigger,scheduled_streak:{start_day:'2026-10-19',...streak}};return Sec.project(p);};
  const pre=at('2026-10-18','SCHEDULED',{count:0,since:null,last_run_day:'2026-10-18'});
  assert.deepEqual(api.deployStreak({secReported:pre,now:Date.parse('2026-10-18T23:00:00Z')}),{target:7,start_day:'2026-10-19',count:0,since:null,last_run_day:'2026-10-18',state:'NOT_STARTED',reason_codes:['BEFORE_START_DAY']});
  assert.deepEqual(api.deployStreak({secReported:pre,now:Date.parse('2026-10-19T20:00:00Z')}).reason_codes,['START_DAY_RUN_PENDING']);   // 10/19 New York, run not deployed yet
  assert.equal(api.deployStreak({secReported:pre,now:Date.parse('2026-10-20T13:00:00Z')}).state,'BROKEN');   // the 10/19 run never reached Pages
  const three=at('2026-10-21','SCHEDULED',{count:3,since:'2026-10-19',last_run_day:'2026-10-21'});
  assert.deepEqual(api.deployStreak({secReported:three,now:Date.parse('2026-10-22T15:00:00Z')}),{target:7,start_day:'2026-10-19',count:3,since:'2026-10-19',last_run_day:'2026-10-21',state:'COUNTING',reason_codes:[]});
  assert.equal(api.deployStreak({secReported:three,now:Date.parse('2026-10-23T06:00:00Z')}).state,'BROKEN');   // New York 02:00 on 10-23: no deploy for 10-22
  assert.equal(api.deployStreak({secReported:three,now:Date.parse('2026-10-23T03:00:00Z')}).state,'COUNTING'); // still 10-22 in New York
  assert.equal(api.deployStreak({secReported:at('2026-10-25','SCHEDULED',{count:7,since:'2026-10-19',last_run_day:'2026-10-25'}),now:Date.parse('2026-10-25T23:00:00Z')}).state,'MET');
  const unknown=at('2026-10-21','SCHEDULED',{count:null,since:null,last_run_day:'2026-10-21'});
  assert.deepEqual([api.deployStreak({secReported:unknown,now:Date.parse('2026-10-21T23:00:00Z')}).state,api.deployStreak({secReported:unknown,now:Date.parse('2026-10-21T23:00:00Z')}).count],['UNKNOWN',null]);
  assert.equal(api.deployStreak({secReported:unknown,now:Date.parse('2026-10-24T23:00:00Z')}).state,'BROKEN');   // unknown count, but a day was missed since
  // A manual run carries the live streak: it neither counts nor resets.
  assert.deepEqual(api.deployStreak({secReported:at('2026-10-22','MANUAL',{count:3,since:'2026-10-19',last_run_day:'2026-10-21'}),now:Date.parse('2026-10-22T23:00:00Z')}).count,3);
  assert.equal(api.deployStreak({secReported:at('2026-10-22','MANUAL',{count:null,since:null,last_run_day:null}),now:Date.parse('2026-10-22T23:00:00Z')}).state,'UNKNOWN');
  assert.equal(api.deployStreak({secReported:Sec.project(fixture(3))}).state,'NOT_AVAILABLE');
 }finally{Date.now=realNow;}
});
