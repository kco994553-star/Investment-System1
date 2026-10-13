'use strict';
// QGV v2 device scoring: JS port (web_assets/qgv-v2.js) == Python reference (qgv/qgv_v2.py) on shared synthetic vectors.
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const W=path.join(__dirname,'../src/investment_system/product/web_assets');
const V2=require(path.join(W,'qgv-v2.js')),TC=require(path.join(W,'type-config-defaults.js')),P=require(path.join(W,'dcf-parameters-defaults.js'));
const vectors=JSON.parse(fs.readFileSync(path.join(__dirname,'../tests/fixtures/qgv_v2_vectors_v1.json'),'utf8'));
function equal(a,b,at='$'){
 if(typeof b==='number'){assert.equal(typeof a,'number',at);assert.ok(Number.isFinite(a)&&Math.abs(a-b)<=Math.max(1e-9,Math.abs(b)*1e-9),at+' '+a+' vs '+b);}
 else if(Array.isArray(b)){assert.ok(Array.isArray(a),at);assert.equal(a.length,b.length,at);b.forEach((v,i)=>equal(a[i],v,at+'['+i+']'));}
 else if(b&&typeof b==='object'){assert.ok(a&&typeof a==='object'&&!Array.isArray(a),at);assert.deepEqual(Object.keys(a).sort(),Object.keys(b).sort(),at);for(const k of Object.keys(b))equal(a[k],b[k],at+'.'+k);}
 else assert.equal(a,b,at);
}
test('config equals the Python reference (default weights exactly, presets, thresholds)',()=>{
 const c=vectors.config;equal(V2.WEIGHTS,c.weights);equal(V2.PRESETS,c.presets);
 assert.equal(V2.DEFAULT_PRESET,c.default_preset);assert.equal(V2.GATE_DEFAULT,c.gate_default);assert.equal(V2.GATE_PERCENTILE,c.gate_percentile);
 assert.equal(V2.MIN_PEERS,c.min_peers);assert.equal(V2.MIN_UNIVERSE,c.min_universe);assert.equal(V2.MIN_AXIS_WEIGHT,c.min_axis_weight);
 assert.equal(V2.MIN_HISTORY,c.min_history);
 for(const a of ['Q','G','V'])assert.equal(Object.values(V2.WEIGHTS[a]).reduce((x,y)=>x+y,0),100);
 assert.deepEqual(Object.keys(V2.WEIGHTS.V),['v_earnings_yield','v_fcf_yield','v_vs_industry','v_vs_own_history','v_expectation_check']);
 assert.ok(Object.isFrozen(V2.WEIGHTS.V)&&Object.isFrozen(V2.PRESETS.balanced.weights));});
test('unit vectors: percentile, axis, GSQ-017 type weights, composite weights',()=>{
 for(const u of vectors.units.percentile)equal(V2.percentile(u.value,u.population),u.expected,'pct '+JSON.stringify(u));
 for(const u of vectors.units.axis)equal(V2.axisScore(u.scores,u.axis),u.expected,'axis');
 for(const u of vectors.units.type_weights)equal(V2.typeAxisWeights(u.memberships,TC),u.expected,'types '+JSON.stringify(u.memberships));
 const fb={Q:34,G:33,V:33};for(const u of vectors.units.composite)equal(V2.compositeWeights(V2.PRESETS[u.preset].weights,u.type_weights,fb),u.expected,'composite '+u.preset);});
for(const c of vectors.cases)test('python reference universe '+c.id,()=>{
 const input=structuredClone(c.input),before=JSON.stringify(input);
 const out=V2.scoreUniverse(input.companies,input.synthetic_market,{typeConfig:TC,parameters:P,preset:input.preset,gate:input.gate});
 equal(out,c.expected);assert.equal(JSON.stringify(input),before,'input not mutated');});
test('missing is NOT_AVAILABLE, never 0; results carry no price or market cap',()=>{
 const c=vectors.cases.find(x=>x.id==='no-device-prices'),out=V2.scoreUniverse(c.input.companies,{},{typeConfig:TC,parameters:P});
 for(const r of Object.values(out)){for(const k of Object.keys(V2.WEIGHTS.V)){assert.equal(r.factors[k].score,null);assert.equal(r.factors[k].state,'NOT_AVAILABLE');}assert.equal(r.axes.V.score,null);assert.ok(r.flags.includes('V_NOT_AVAILABLE'));}
 const full=vectors.cases.find(x=>x.id==='balanced-default'),res=V2.scoreUniverse(full.input.companies,full.input.synthetic_market,{typeConfig:TC,parameters:P}),text=JSON.stringify(res);
 assert.ok(!/"price"|"market_cap"|"marketcap"|"ev"\s*:|month_closes/i.test(text));
 for(const[code,q]of Object.entries(full.input.synthetic_market))assert.ok(!text.includes(':'+q.price+','),'price echo '+code);});
test('balanced preset reproduces the GSQ-017 type weights; the gate excludes V and flags 가치 함정 주의',()=>{
 const fb={Q:34,G:33,V:33},[tw]=V2.typeAxisWeights({growth:1},TC),w=V2.compositeWeights(V2.PRESETS.balanced.weights,tw,fb);
 for(const p of ['Q','G','V'])assert.ok(Math.abs(w[p]-tw[p])<1e-9);
 const c=vectors.cases.find(x=>x.id==='balanced-default'),res=V2.scoreUniverse(c.input.companies,c.input.synthetic_market,{typeConfig:TC,parameters:P});
 const trapped=Object.values(res).filter(r=>r.flags.includes('VALUE_TRAP_CAUTION'));assert.ok(trapped.length>0);
 for(const r of trapped){assert.equal(r.v_excluded,'VALUE_TRAP_GATE');assert.ok(r.q_industry_percentile<30);
  if(r.total!==null&&r.axes.Q.score!==null&&r.axes.G.score!==null){const e=(r.weights.Q*r.axes.Q.score+r.weights.G*r.axes.G.score)/(r.weights.Q+r.weights.G);assert.ok(Math.abs(r.total-e)<1e-9);}}
 const off=V2.scoreUniverse(c.input.companies,c.input.synthetic_market,{typeConfig:TC,parameters:P,gate:false});for(const r of Object.values(off))assert.ok(!r.flags.includes('VALUE_TRAP_CAUTION'));
 assert.throws(()=>V2.scoreUniverse({}, {}, {preset:'tuned'}),/PRESET_INVALID/);});
test('monthClose: month-end close of the fiscal period-end month from the device Prices tab shape',()=>{
 assert.equal(V2.monthClose({'2024-11':5,'2024-12':6},'2024-12-31'),6);assert.equal(V2.monthClose({'2024-11':5},'2024-12-31'),null);assert.equal(V2.monthClose({'2024-12':0},'2024-12-31'),null);assert.equal(V2.monthClose(null,'2024-12-31'),null);});
