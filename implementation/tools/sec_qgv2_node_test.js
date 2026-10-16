'use strict';const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const reader=require('../src/investment_system/product/web_assets/sec-qgv2.js');
const vectors=JSON.parse(fs.readFileSync(path.join(__dirname,'../tests/fixtures/sec_qgv2_vectors_v1.json'),'utf8'));
const CODES=JSON.parse(fs.readFileSync(path.join(__dirname,'../src/investment_system/universe/universe_codes_v1.json'),'utf8'));
const SIC=JSON.parse(fs.readFileSync(path.join(__dirname,'../src/investment_system/qgv/sic_industry_groups_v0.json'),'utf8'));
let pass=0,fail=0;async function test(name,f){try{await f();pass++;console.log('PASS '+name);}catch(e){fail++;console.log('FAIL '+name+' '+(e.code==='ERR_ASSERTION'?'CONTRACT':'EXECUTION'));if(process.env.DEBUG_TEST)console.log(e);}}
/* Same expansion/mutation as tools/sec_qgv2_reference.py expand()/apply(). */
function expand(base){const p=structuredClone(base),sparse=p.records;p.records=Object.fromEntries(CODES.map(c=>[c,sparse[c]?sparse[c]:reader.emptyRecord()]));return p;}
function apply(p,ops){for(const {path:keys,value} of ops){let t=p;for(const k of keys.slice(0,-1))t=t[k];const last=keys[keys.length-1];if(JSON.stringify(value)===JSON.stringify(vectors.delete_marker))delete t[last];else t[last]=structuredClone(value);}return p;}
const verdict=p=>{try{reader.validate(p);return true;}catch(e){assert.equal(e.message,'SEC_QGV2_INVALID');return false;}};
const valid=()=>expand(vectors.base);
(async()=>{
 await test('Python validator verdicts replay identically in JS ('+vectors.cases.length+' vectors)',async()=>{assert.equal(vectors.synthetic,true);assert.ok(vectors.cases.length>=40);assert.equal(CODES.length,504);for(const c of vectors.cases)assert.equal(verdict(apply(valid(),c.ops)),c.valid,c.id);});
 await test('embedded constants equal the Python/config sources',async()=>{const k=vectors.constants;assert.deepEqual({...reader.TARGET_CIKS},k.target_ciks);assert.deepEqual(reader.SIC_GROUPS,SIC.groups.map(g=>[g.id,g.sic_ranges]));assert.deepEqual(reader.SIC_GROUPS,k.sic_groups);assert.deepEqual([...reader.METRIC_KEYS],k.metric_keys);assert.deepEqual(JSON.parse(JSON.stringify(reader.EXTRA_METRICS)),k.extra_metrics);assert.deepEqual([...reader.FACTOR_IDS],k.factor_ids);
  assert.deepEqual({Q:{...reader.Q_WEIGHTS},G:{...reader.G_WEIGHTS}},k.method.weights);assert.equal(Object.values(reader.Q_WEIGHTS).reduce((a,b)=>a+b,0),100);assert.equal(Object.values(reader.G_WEIGHTS).reduce((a,b)=>a+b,0),100);});
 await test('JS recomputation reproduces every published Python score',async()=>{const p=valid(),{scores,summary}=reader.scoreRows(p.records,p.target);assert.equal(summary.cross_section_size,p.cross_section_size);let compared=0;
  for(const [code,r] of Object.entries(p.records)){const e=scores.get('universe\u0000'+code);for(const f of reader.FACTOR_IDS){if(r.factors[f]===null)assert.equal(e.factors[f],null);else{assert.ok(Math.abs(r.factors[f]-e.factors[f])<1e-9,code+f);compared++;}}}
  assert.ok(compared>200);assert.ok(Object.values(p.target).some(r=>r.axes.Q.score!==null&&r.axes.G.score!==null));});
 await test('no zero fill: missing factors and axes stay null with fixed reasons',async()=>{const p=valid();const fin=Object.values(p.records).find(r=>r.profile==='FINANCIAL');assert.equal(fin.factors.q_earnings_quality,null);assert.equal(fin.axes.Q.factors_available,'4/5');assert.equal(fin.axes.Q.peer_basis,'FINANCIAL_PROFILE');
  const empty=p.records[CODES[200]];assert.equal(empty.axes.Q.score,null);assert.deepEqual(empty.axes.Q.reason_codes,['ROW_NOT_AVAILABLE']);assert.deepEqual(p.target.hanmi.reason_codes,['NON_SEC_ISSUER']);});
 await test('device-time restate ages rows without changing values',async()=>{const p=valid(),i=reader.toInputs(p,{now:'2026-10-14T00:00:00Z'});assert.equal(i.state,'LIVE');const code=Object.keys(vectors.base.records).find(c=>vectors.base.records[c].state==='LIVE');assert.equal(i.records[code].state,'LIVE');
  const later=reader.toInputs(p,{now:'2026-11-30T00:00:00Z'});assert.equal(later.records[code].state,'STALE');assert.deepEqual([...later.records[code].reason_codes],['STALE_INPUT']);assert.equal(later.records[code].axes.Q.score,p.records[code].axes.Q.score);assert.ok(Object.isFrozen(later.records[code].v_inputs_v2));assert.equal(later.target.nvda.v_inputs_v2.currency,'USD');});
 await test('loader: 404 stays not connected, invalid fails closed, other errors are fixed codes',async()=>{const body=JSON.stringify(valid()),view=(status,text=body)=>({fetch:async(name,opt)=>{assert.equal(name,'sec-qgv2.json');assert.equal(opt.cache,'no-cache');return{status,ok:status===200,text:async()=>text};}});
  assert.equal(await reader.loadInputs(view(404)),null);assert.equal((await reader.loadInputs(view(200),{now:'2026-10-14T00:00:00Z'})).state,'LIVE');await assert.rejects(reader.loadInputs(view(200,'{"price":1}')),/SEC_QGV2_INVALID/);await assert.rejects(reader.loadInputs(view(200,'{')),/SEC_QGV2_INVALID/);await assert.rejects(reader.loadInputs(view(500)),/SEC_QGV2_UNAVAILABLE/);assert.equal(typeof globalThis.localStorage,'undefined');});
 console.log('COUNTS pass='+pass+' fail='+fail);if(fail)process.exitCode=1;
})();
