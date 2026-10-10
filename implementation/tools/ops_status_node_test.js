'use strict';const test=require('node:test'),assert=require('node:assert/strict'),api=require('../src/investment_system/product/web_assets/ops-status.js');
test('ops status uses public metadata only and never invents freshness thresholds',()=>{const now=Date.parse('2026-10-10T12:00:00Z');
 const rows=api.summarize({now,secReported:{companies:{a:{status:'LIVE',acquired_at:'2026-10-09T22:20:00Z',reason_codes:[]},b:{status:'NOT_AVAILABLE',acquired_at:null,reason_codes:['SEC_HTTP_503']},c:{status:'LIVE',acquired_at:'2026-10-09T22:25:00Z',reason_codes:[]}}},
  screens:{'sec-qg-factors.json':{state:'LIVE',as_of:'2026-10-08T00:00:00Z',stale_after_seconds:86400,reason_codes:[]},'macro-screen.json':{state:'NOT_AVAILABLE',as_of:'2026-10-10T00:00:00Z',stale_after_seconds:86400,reason_codes:['NO_ELIGIBLE_INPUT']}}});
 const by=Object.fromEntries(rows.map(r=>[r.id,r]));assert.equal(rows.length,6);
 assert.deepEqual([by['sec-public-inputs.json'].failed_companies,by['sec-public-inputs.json'].total_companies,by['sec-public-inputs.json'].last_success_at],[1,3,'2026-10-09T22:25:00.000Z']);assert.deepEqual(by['sec-public-inputs.json'].reason_codes,['SEC_HTTP_503']);assert.equal(by['sec-public-inputs.json'].stale,null);
 assert.equal(by['sec-qg-factors.json'].stale,true);assert.equal(by['macro-screen.json'].last_success_at,null);assert.equal(by['sec-13f-changes.json'].state,'NOT_AVAILABLE');assert.deepEqual(by['sec-13f-changes.json'].reason_codes,['NOT_CONNECTED']);
 assert.equal(api.summarize({}).every(r=>r.state==='NOT_AVAILABLE'),true);});
