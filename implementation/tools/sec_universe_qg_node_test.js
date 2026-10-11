'use strict';const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const reader=require('../src/investment_system/product/web_assets/sec-universe-qg.js');
const vectors=JSON.parse(fs.readFileSync(path.join(__dirname,'../tests/fixtures/sec_universe_qg_vectors_v1.json'),'utf8'));
const CODES=JSON.parse(fs.readFileSync(path.join(__dirname,'../src/investment_system/universe/universe_codes_v1.json'),'utf8'));
let pass=0,fail=0;async function test(name,f){try{await f();pass++;console.log('PASS '+name);}catch(e){fail++;console.log('FAIL '+name+' '+(e.code==='ERR_ASSERTION'?'CONTRACT':'EXECUTION'));if(process.env.DEBUG_TEST)console.log(e);}}
/* Same expansion/mutation as tools/sec_universe_qg_reference.py expand()/apply(). */
function expand(base){const p=structuredClone(base),sparse=p.records;p.records=Object.fromEntries(CODES.map(c=>[c,sparse[c]?sparse[c]:reader.emptyRecord()]));return p;}
function apply(p,ops){for(const {path:keys,value} of ops){let t=p;for(const k of keys.slice(0,-1))t=t[k];const last=keys[keys.length-1];if(JSON.stringify(value)===JSON.stringify(vectors.delete_marker))delete t[last];else t[last]=structuredClone(value);}return p;}
const verdict=p=>{try{reader.validate(p);return true;}catch(e){assert.equal(e.message,'SEC_UNIVERSE_QG_INVALID');return false;}};
const valid=()=>expand(vectors.base);
(async()=>{
 await test('Python validator verdicts replay identically in JS ('+vectors.cases.length+' vectors)',async()=>{assert.equal(vectors.synthetic,true);assert.ok(vectors.cases.length>=40);assert.equal(CODES.length,504);for(const c of vectors.cases)assert.equal(verdict(apply(valid(),c.ops)),c.valid,c.id);});
 await test('factor ids are the Python Q+G set (no V)',async()=>{assert.deepEqual([...reader.FACTORS],vectors.factors);assert.equal(reader.FACTORS.length,13);for(const v of ['fundamental_value','reverse_dcf','margin_of_safety'])assert.ok(!reader.FACTORS.includes(v));});
 await test('device-time restate keeps scores, ages rows, never fills null with zero',async()=>{const p=valid(),i=reader.toInputs(p,{now:'2026-10-11T00:00:00Z'});assert.equal(i.state,'LIVE');assert.equal(i.scored_codes,2);assert.equal(i.records['NASDAQ:ADBE'].state,'LIVE');assert.equal(i.records['NYSE:MMM'].state,'STALE');assert.equal(i.records['NASDAQ:ADBE'].factors.competitive_advantage,null);assert.equal(i.records['NASDAQ:ADBE'].factors.roic_wacc,0);
  const later=reader.toInputs(p,{now:'2026-10-30T00:00:00Z'});assert.equal(later.records['NASDAQ:ADBE'].state,'STALE');assert.deepEqual([...later.records['NASDAQ:ADBE'].reason_codes],['STALE_INPUT']);assert.equal(later.records['NASDAQ:ADBE'].factors.margin_quality,62.5);assert.equal(later.state,'STALE');assert.equal(p.records['NASDAQ:ADBE'].state,'LIVE');assert.ok(Object.isFrozen(later.records['NASDAQ:ADBE'].factors));
  assert.equal(i.records['NASDAQ:AMD'].state,'NOT_AVAILABLE');assert.deepEqual([...i.records['NASDAQ:AMD'].reason_codes],['M1_NOT_AVAILABLE']);});
 await test('targetRow gives the TARGET sec-qg-factors row shape',async()=>{const r=reader.targetRow(valid().records['NASDAQ:ADBE']);assert.deepEqual(r.factors.revenue_growth,{score:80.00000000000003,state:'LIVE'});assert.deepEqual(r.factors.market_position,{score:null,state:'NOT_AVAILABLE'});assert.equal(r.state,'LIVE');});
 await test('loader: 404 stays not connected, invalid fails closed, other errors are fixed codes',async()=>{const body=JSON.stringify(valid()),view=(status,text=body)=>({fetch:async(name,opt)=>{assert.equal(name,'sec-universe-qg.json');assert.equal(opt.cache,'no-cache');return{status,ok:status===200,text:async()=>text};}});
  assert.equal(await reader.loadInputs(view(404)),null);assert.equal((await reader.loadInputs(view(200),{now:'2026-10-11T00:00:00Z'})).state,'LIVE');await assert.rejects(reader.loadInputs(view(200,'{"price":1}')),/SEC_UNIVERSE_QG_INVALID/);await assert.rejects(reader.loadInputs(view(200,'{')),/SEC_UNIVERSE_QG_INVALID/);await assert.rejects(reader.loadInputs(view(500)),/SEC_UNIVERSE_QG_UNAVAILABLE/);assert.equal(typeof globalThis.localStorage,'undefined');});
 console.log('COUNTS pass='+pass+' fail='+fail);if(fail)process.exitCode=1;
})();
