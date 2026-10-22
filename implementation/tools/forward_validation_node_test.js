'use strict';
/* Forward validation device module: Python reference parity (synthetic vectors), ledger reader, RAM-only rules. */
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const file=path.join(__dirname,'../src/investment_system/product/web_assets/forward-validation.js'),api=require(file),source=fs.readFileSync(file,'utf8');
const vectors=JSON.parse(fs.readFileSync(path.join(__dirname,'../tests/fixtures/forward_validation_reference_v1.json'),'utf8'));
let pass=0,fail=0;async function test(name,f){try{await f();pass++;console.log('PASS '+name);}catch(e){fail++;console.log('FAIL '+name);if(process.env.DEBUG_TEST)console.log(e);}}
const V='forward_validation/v1',VV='forward_validation/v1+dcf_v1_default';
function ledger(asOf,status,rows=[]){return{schema_version:1,kind:'FORWARD_VALIDATION_LEDGER',start_date:'2026-10-19',status,as_of:asOf,strategy:'QGV_STANDARD_V1',calibration:'UNCALIBRATED',holdout:'UNCONFIRMED_NOT_USED',price_free:true,target:{portfolio_id:'TARGET',version:'v0'},versions:{[V]:rows,[VV]:[]},version_status:{[V]:{state:status,v_included:false,reason_codes:[]},[VV]:{state:'NOT_AVAILABLE',v_included:true,reason_codes:['V_REQUIRES_DEVICE_PRICES']}}};}
const H='a'.repeat(64);
function naRecord(date,created){return{date,version:V,strategy:'QGV_STANDARD_V1',calibration:'UNCALIBRATED',state:'NOT_AVAILABLE',reason_codes:['SEC_QG_FACTORS_MISSING','TARGET_CATALOG_MISSING'],target:null,qg_as_of:null,qg_screen_state:null,companies:null,source_sha256:{'sec-qg-factors.json':null,'actual-catalog.json':null},created_at:created};}
(async()=>{
await test('every synthetic vector equals the Python reference exactly',()=>{
 assert.equal(vectors.synthetic,true);assert.ok(vectors.cases.length>=7);
 for(const c of vectors.cases){assert.equal(c.synthetic,true);const got=c.operation==='forward_return'?api.forwardReturn(c.input):c.operation==='evaluation_segments'?api.segments(c.input):api.qgSummary(c.input);assert.deepStrictEqual(JSON.parse(JSON.stringify(got)),c.expected,c.id);}
 assert.ok(vectors.cases.some(c=>c.operation==='evaluation_segments')&&vectors.cases.some(c=>c.input.end_date));
});
await test('evaluation segments never chain calc versions and keep preparatory rows outside the primary evaluation',()=>{
 const [c]=vectors.cases.filter(c=>c.operation==='evaluation_segments'),segs=api.segments(c.input);
 assert.deepEqual(segs.map(s=>s.segment),['LEGACY','NONE','qgv2-calc/2026-10-15.1','qgv2-calc/2026-11-02.1']);
 assert.deepEqual(segs[2].eligible_dates,['2026-10-21','2026-10-26']);assert.deepEqual(segs[2].preparatory_dates,['2026-10-23']);
 assert.equal(api.PRIMARY_MIN,454);assert.equal(api.FRESH_DAYS,7);
});
await test('missing prices are NOT_AVAILABLE, never zero; benchmark stays NOT_AVAILABLE',()=>{
 const r=api.forwardReturn({start_date:'2026-10-19',weights_units:{a:1,b:1},series:{a:[{session_date:'2026-10-19',adjusted_close:2,session_status:'COMPLETE'},{session_date:'2026-10-20',adjusted_close:3,session_status:'COMPLETE'}]}});
 assert.equal(r.state,'NOT_AVAILABLE');assert.equal(r.portfolio_return,null);assert.deepEqual(r.instruments.b,{state:'NOT_AVAILABLE',reason:'HISTORY_NOT_LOADED'});
 assert.deepEqual(r.benchmark,{state:'NOT_AVAILABLE',reason:'SP500_NOT_IN_PRIVATE_HISTORY_WORKER'});
});
await test('ledger reader accepts NOT_STARTED / ACTIVE shapes and rejects V values, prices and rewrites',()=>{
 api.validate(ledger('2026-10-16T22:30:00+00:00','NOT_STARTED'));
 api.validate(ledger('2026-10-19T14:00:00+00:00','ACTIVE'));
 const ok=ledger('2026-10-20T22:30:00+00:00','ACTIVE',[naRecord('2026-10-19','2026-10-19T22:30:00+00:00'),naRecord('2026-10-20','2026-10-20T22:30:00+00:00')]);api.validate(ok);
 const bad=[p=>{p.price=1;},p=>{p.versions[VV].push({});},p=>{p.status='NOT_STARTED';},p=>{p.holdout='USED';},
  p=>{p.versions[V].reverse();},p=>{p.versions[V][0].date='2026-10-18';p.versions[V][0].created_at='2026-10-18T22:30:00+00:00';},
  p=>{p.versions[V][0].date='2026-11-26';},p=>{p.versions[V][0].created_at='2026-10-19T19:00:00+00:00';},
  p=>{p.versions[V][0].reason_codes=[];},p=>{p.versions[V][0].companies={};},p=>{p.versions[V][0].V=1;}];
 for(const m of bad){const p=structuredClone(ok);m(p);assert.throws(()=>api.validate(p),/FORWARD_LEDGER_INVALID/);}
 assert.throws(()=>api.validate(ledger('2026-10-16T22:30:00+00:00','ACTIVE')),/FORWARD_LEDGER_INVALID/);
});
await test('load reports 404, invalid and unreachable ledgers as NOT_AVAILABLE with a reason',async()=>{
 const view=body=>({AbortController,fetch:async()=>body});
 assert.deepEqual(await api.load(view({ok:false,status:404})),{state:'NOT_AVAILABLE',reason:'LEDGER_NOT_PUBLISHED'});
 assert.deepEqual(await api.load(view({ok:true,status:200,text:async()=>'{"price":1}'})),{state:'NOT_AVAILABLE',reason:'LEDGER_INVALID'});
 assert.deepEqual(await api.load({AbortController,fetch:async()=>{throw Error('offline');}}),{state:'NOT_AVAILABLE',reason:'LEDGER_UNREACHABLE'});
 const good=ledger('2026-10-16T22:30:00+00:00','NOT_STARTED'),r=await api.load(view({ok:true,status:200,text:async()=>JSON.stringify(good)}));
 assert.equal(r.state,'LOADED');assert.equal(r.ledger.status,'NOT_STARTED');
});
await test('history bars map to New York / provider session dates and the smallest covering range',()=>{
 const yahoo={timezone:'America/New_York',bars:[{timestamp:Date.parse('2026-10-19T13:30:00Z')/1000,adjusted_close:5,session_status:'COMPLETE'}]};
 assert.deepEqual(api.seriesFromHistory(yahoo),[{session_date:'2026-10-19',adjusted_close:5,session_status:'COMPLETE'}]);
 const tokyo={timezone:'Asia/Tokyo',bars:[{timestamp:Date.parse('2026-10-19T00:00:00Z')/1000,adjusted_close:5,session_status:'COMPLETE'}]};
 assert.equal(api.seriesFromHistory(tokyo)[0].session_date,'2026-10-19');
 const krx={timezone:'Asia/Seoul',bars:[{timestamp:Date.parse('2026-10-20T00:00:00Z')/1000,session_date:'2026-10-20',adjusted_close:null,session_status:'UNKNOWN'}]};
 assert.equal(api.seriesFromHistory(krx)[0].session_date,'2026-10-20');
 assert.equal(api.rangeFor('2026-10-19','2026-10-11'),'1mo');assert.equal(api.rangeFor('2026-10-19','2026-11-10'),'1mo');
 assert.equal(api.rangeFor('2026-10-19','2026-12-01'),'3mo');assert.equal(api.rangeFor('2026-10-19','2027-03-01'),'6mo');
 assert.equal(api.rangeFor('2026-10-19','2027-09-01'),'1y');assert.equal(api.rangeFor('2026-10-19','2028-06-01'),'2y');
});
await test('operating evidence: observation dates per version, gaps on US sessions only, empty ledger has no range, NA never 0',()=>{
 // Gap fixture: no record on 2026-10-20 and 2026-10-26; weekends and the 2026-11-26 holiday are not gaps.
 const days=['2026-10-19','2026-10-21','2026-10-22','2026-10-23','2026-10-27','2026-11-25','2026-11-27'];
 const p=api.validate(ledger('2026-11-27T22:30:00+00:00','ACTIVE',days.map(d=>naRecord(d,d+'T22:30:00+00:00')))),e=api.evidence(p);
 assert.equal(e.latest,'2026-11-27');assert.equal(e.as_of,'2026-11-27T22:30:00+00:00');assert.equal(e.start_date,'2026-10-19');assert.equal(e.run_kind,'NOT_IN_LEDGER');
 assert.deepEqual(e.versions.map(v=>[v.version,v.count,v.first,v.latest]),[[V,7,'2026-10-19','2026-11-27']]);assert.deepEqual(e.versions[0].dates,days);
 assert.deepEqual(e.missing.slice(0,2),['2026-10-20','2026-10-26']);assert.deepEqual(e.versions[0].missing,e.missing);
 for(const d of ['2026-10-24','2026-10-25','2026-11-26','2026-11-28'])assert.ok(!e.days.some(x=>x.date===d),d);
 assert.equal(e.session_count,e.days.length);assert.equal(e.session_count,days.length+e.missing.length);assert.ok(e.missing.includes('2026-11-24')&&!e.missing.includes('2026-11-26'));
 assert.deepEqual(e.days.find(x=>x.date==='2026-10-20'),{date:'2026-10-20',state:'MISSING',versions:{[V]:'MISSING'}});
 assert.deepEqual(e.days.find(x=>x.date==='2026-10-19'),{date:'2026-10-19',state:'RECORDED',versions:{[V]:'NOT_AVAILABLE'}},'a NOT_AVAILABLE record is still a record');
 // Schema 2: v2 (default) listed first; a day present in only one version is PARTIAL.
 const V2='forward_validation/v2',v2=d=>({...naRecord(d,d+'T22:30:00+00:00'),version:V2,strategy:'QGV_STANDARD_V2',reason_codes:['SEC_QGV2_MISSING','TARGET_CATALOG_MISSING'],source_sha256:{'sec-qgv2.json':null,'actual-catalog.json':null}});
 const q=ledger('2026-10-21T22:30:00+00:00','ACTIVE',[naRecord('2026-10-19','2026-10-19T22:30:00+00:00'),naRecord('2026-10-21','2026-10-21T22:30:00+00:00')]);
 q.schema_version=2;q.strategy='QGV_STANDARD_V2';q.versions[V2]=['2026-10-19','2026-10-20','2026-10-21'].map(v2);q.version_status[V2]={state:'ACTIVE',v_included:false,reason_codes:[]};
 const f=api.evidence(api.validate(q));
 assert.deepEqual(f.versions.map(v=>[v.version,v.count,v.missing]),[[V2,3,[]],[V,2,['2026-10-20']]]);
 assert.deepEqual(f.days.map(d=>d.state),['RECORDED','PARTIAL','RECORDED']);assert.deepEqual(f.missing,['2026-10-20']);assert.equal(f.latest,'2026-10-21');
 // Empty ledgers: zero records is a real count; there is no latest date and no range (null, never 0 or a made-up date).
 for(const empty of [ledger('2026-10-16T22:30:00+00:00','NOT_STARTED'),ledger('2026-10-19T14:00:00+00:00','ACTIVE')]){const g=api.evidence(api.validate(empty));
  assert.equal(g.latest,null);assert.equal(g.session_count,0);assert.deepEqual(g.days,[]);assert.deepEqual(g.missing,[]);
  assert.deepEqual(g.versions,[{version:V,count:0,dates:[],first:null,latest:null,missing:[]}]);}
 // Price-free: evidence carries only dates, counts and states.
 const text=JSON.stringify(api.evidence(api.validate(q)));for(const banned of ['score','companies','weights','target','sha256','close','return'])assert.ok(!text.includes(banned),banned);
});
await test('module never persists or transmits computed values',()=>{
 for(const banned of ['setItem','removeItem','indexedDB','sessionStorage','sendBeacon','XMLHttpRequest','postMessage','caches.'])assert.ok(!source.includes(banned),banned);
 assert.equal((source.match(/\.fetch\(/g)||[]).length,1);assert.equal((source.match(/fetchHistory\(/g)||[]).length,1);
});
console.log(`forward_validation_node_test pass=${pass} fail=${fail}`);process.exitCode=fail?1:0;
})();
