'use strict';const test=require('node:test'),assert=require('node:assert/strict');
const api=require('../src/investment_system/product/web_assets/sec-reported.js'),{fixture,unavailable}=require('./sec_reported_fixture.js');
test('v1/v2/v3 are compatible; only a fixed price-free display projection leaves the reader',()=>{
 for(const v of [1,2,3]){const p=fixture(v);p.companies[2].reported_shares[0].namespace='ifrs-full';p.companies[2].reported_shares[0].concept='NumberOfSharesOutstanding';const out=api.project(p);assert.equal(Object.keys(out.companies).length,17);assert.equal(out.companies.asml.status,'LIVE');assert.deepEqual(out.companies.amd.excluded_fact_counts,{});assert.ok(!JSON.stringify(out).includes('reported_shares'));assert.ok(!JSON.stringify(out).includes('https://'));assert.ok(!JSON.stringify(out).includes('100'));}
});
test('v3 live and unavailable rows keep exclusions and class caution without reading absent facts',()=>{
 const p=fixture();p.companies[0].excluded_fact_counts={VALUE_INVALID:3,CLASS_SPLIT:2};p.companies[0].share_class_notice='SHARE_CLASS_BASIS';p.companies[1]=unavailable(p.companies[1],2);const out=api.project(p);
 assert.equal(out.companies.amd.excluded_fact_counts.VALUE_INVALID,3);assert.equal(out.companies.amd.share_class_notice,'SHARE_CLASS_BASIS');assert.equal(out.companies.amzn.status,'NOT_AVAILABLE');assert.equal(out.companies.amzn.reason_codes[0],'SEC_NO_ELIGIBLE_SHARE_FACTS');
 const old=fixture(2);old.companies[0]=unavailable(old.companies[0],1,2);assert.equal(api.project(old).companies.amd.status,'NOT_AVAILABLE');
});
test('reject unknown fields, malformed facts, source identity, exclusion counts and incompatible notices',()=>{
 const mutations=[p=>p.price=1,p=>p.companies[0].price=1,p=>p.schema='public-sec-reported-inputs/4',p=>p.companies[0].excluded_fact_counts={PRICE_INVALID:1},p=>p.companies[0].excluded_fact_counts={VALUE_INVALID:0},p=>p.companies[0].excluded_fact_counts={VALUE_INVALID:1.5},p=>p.companies[0].share_class_notice='SHARE_CLASS_BASIS',p=>p.companies[0].share_class_basis='CONFIRMED',p=>p.companies[0].sources.companyfacts.url='https://other.test/',p=>p.companies[0].reported_shares[0].val=Infinity,p=>p.companies[0].reported_shares[0].end='2025-02-30',p=>p.companies[0].reported_shares[0].price=1,p=>p.companies.reverse(),p=>p.companies.pop(),p=>p.companies[0]=unavailable(p.companies[0],2)];
 for(const mutate of mutations){const p=fixture();mutate(p);assert.throws(()=>api.project(p),/SEC_PUBLIC_INPUT_INVALID/);}
});
test('optional input fetch is bounded, same-origin, no-store and safe on missing/invalid responses',async()=>{
 let request;const view={fetch:async(path,options)=>{request={path,options};return{ok:true,text:async()=>JSON.stringify(fixture())};}};assert.equal(Object.keys((await api.load(view)).companies).length,17);assert.equal(request.path,'sec-public-inputs.json');assert.equal(request.options.cache,'no-store');assert.equal(request.options.credentials,'omit');assert.equal(request.options.redirect,'error');
 for(const response of [{ok:false},{ok:true,text:async()=>'{bad'},{ok:true,text:async()=> 'x'.repeat(2*1024*1024+1)}]){assert.equal(await api.load({fetch:async()=>response}),null);}
});
test('v4 keeps run states apart and never exposes a withdrawn or failed row as an observation',()=>{
 const {mixed}=require('./sec_reported_fixture.js'),out=api.project(mixed()),c=out.companies;
 assert.deepEqual(out.collection,{checked_at:'2026-01-02T12:05:00Z',run_day:'2026-01-02',trigger:'SCHEDULED',previous:'LOADED',stale_after_seconds:86400,scheduled_streak:{count:3,since:'2025-12-31',last_run_day:'2026-01-02'}});
 assert.deepEqual([c.amd.run,c.amzn.run,c.asml.run,c.avgo.run,c.etn.run],['PRESERVED','COLLECTED','WITHDRAWN','FAILED','COLLECTED']);
 assert.deepEqual(c.amd.preserved,{checked_at:'2026-01-02T12:04:00Z',reason_codes:['SEC_HTTP_503']});assert.equal(c.amd.acquired_at,'2026-01-01T12:00:00Z');
 assert.equal(c.amzn.status,'NOT_AVAILABLE');assert.equal(c.amzn.acquired_at,'2026-01-02T12:00:00Z');
 assert.equal(c.asml.status,'WITHDRAWN');assert.equal(c.asml.acquired_at,null);assert.equal(c.asml.detected_at,'2026-01-02T12:03:00Z');assert.equal(c.asml.withdrawn_acquired_at,'2026-01-01T12:00:00Z');
 assert.equal(c.avgo.acquired_at,null);assert.equal(c.avgo.checked_at,'2026-01-02T12:02:00Z');
 assert.ok(!JSON.stringify(out).includes('reported_shares')&&!JSON.stringify(out).includes('https://'));
});
test('v4 rejects failure times disguised as collections, status-only withdrawals and inconsistent run context',()=>{
 const {mixed}=require('./sec_reported_fixture.js');
 const mutations=[p=>{p.companies[2].acquired_at='2026-01-02T12:03:00Z';},p=>{p.companies[3].acquired_at='2026-01-02T12:02:00Z';},p=>{p.companies[2].reason_codes=['SEC_HTTP_503'];},
  p=>{p.companies[1].failure_stage='fetch';p.companies[1].reason_codes=['SEC_HTTP_503'];},p=>{p.companies[0].preserved_previous.reason_codes=['SEC_HTTP_404'];},p=>{p.companies[0].preserved_previous.reason_codes=['SEC_CIK_MISMATCH'];},
  p=>{p.companies[0].preserved_previous.checked_at='2025-12-31T00:00:00Z';},p=>{p.companies[3].preserved_previous={checked_at:'2026-01-02T12:04:00Z',reason_codes:['SEC_HTTP_503'],failure_stage:'fetch',http_status:503};},
  p=>{p.companies[2].withdrawn_acquired_at='2026-01-02T12:04:00Z';},p=>{p.companies[4].acquired_at='2026-01-02T12:06:00Z';},p=>{p.companies[2].sources=p.companies[4].sources;},
  p=>{delete p.collection;},p=>{p.collection.trigger='CRON';},p=>{p.collection.scheduled_streak.count=5;},p=>{p.collection.scheduled_streak.since=null;},p=>{p.collection.price=1;},p=>{p.companies[2].excluded_fact_counts={VALUE_INVALID:1};}];
 for(const mutate of mutations){const p=mixed();mutate(p);assert.throws(()=>api.project(p),/SEC_PUBLIC_INPUT_INVALID/);}
});
