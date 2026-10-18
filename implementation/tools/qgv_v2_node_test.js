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
 // No market cap or EV value is carried: none of price × shares or EV appears as a number.
 const nums=new Set();JSON.parse(text,(k,v)=>{if(typeof v==='number')nums.add(v);return v;});
 for(const[code,q]of Object.entries(full.input.synthetic_market)){const v=full.input.companies[code].v_inputs;if(!v)continue;const mc=q.price*v.diluted_shares;assert.ok(!nums.has(mc)&&!nums.has(mc+v.total_debt-v.cash),'market cap / EV echo '+code);}});
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
/* PERSONAL_PREVIEW two-level weights (owner directive 2026-10-18 §4.2). Python twin: tests/test_qgv_v2_custom_weights.py,
   vectors tests/fixtures/qgv_v2_custom_vectors_v1.json (tools/qgv_v2_custom_reference.py). */
const custom=JSON.parse(fs.readFileSync(path.join(__dirname,'../tests/fixtures/qgv_v2_custom_vectors_v1.json'),'utf8'));
const companiesOf=c=>c.input.companies==='scored_universe'?custom.scored_universe:c.input.companies;
const rankedCodes=res=>Object.entries(res).filter(([,r])=>r.total!==null).sort((a,b)=>b[1].total-a[1].total||(a[0]<b[0]?-1:1)).map(([k])=>k);
const stripProfile=res=>{const out={},profiles={};for(const[k,r]of Object.entries(res)){const{profile,...rest}=r;out[k]=rest;profiles[k]=profile;}return[out,profiles];};
test('E1: official weights via `weights` deep-equal the preset path for every vector case (incl. published-axes)',()=>{
 for(const c of vectors.cases){const i=c.input,preset=i.preset??'balanced';
  const a=V2.scoreUniverse(structuredClone(i.companies),structuredClone(i.synthetic_market),{typeConfig:TC,parameters:P,preset:i.preset,gate:i.gate});
  const b=V2.scoreUniverse(structuredClone(i.companies),structuredClone(i.synthetic_market),{typeConfig:TC,parameters:P,gate:i.gate,weights:V2.officialWeights(preset)});
  const[ra,pa]=stripProfile(a),[rb,pb]=stripProfile(b);assert.deepStrictEqual(rb,ra,c.id);
  for(const k of Object.keys(pa)){assert.equal(pb[k].namespace,'PERSONAL_PREVIEW');assert.match(pb[k].id,/^qgv-v2\/custom\/[0-9a-f]{16}\/gate-(on|off)$/);assert.ok(!('namespace' in pa[k]));assert.deepEqual(pb[k].recomputed_axes,[]);}
  equal(a,c.expected);}});
test('custom vectors: Python == JS (cases, custom axis units, stable weight ids)',()=>{
 for(const u of custom.units.axis)equal(V2.axisScore(u.scores,u.axis,u.weights),u.expected,'axis '+u.axis);
 for(const u of custom.units.weights_id)assert.equal(V2.weightsId(V2.validateWeights(u.weights),u.type_weights),u.expected);
 for(const c of custom.cases){const i=c.input,input=structuredClone(companiesOf(c)),before=JSON.stringify(input);
  const out=V2.scoreUniverse(input,structuredClone(i.synthetic_market),{typeConfig:TC,parameters:P,gate:i.gate,weights:structuredClone(i.weights),typeWeights:i.type_weights,recomputePublished:i.recompute_published});
  equal(out,c.expected,c.id);assert.equal(JSON.stringify(input),before,'input not mutated');}});
test('E2: forced recompute at official weights on score_rows axes: same NA, gate flags, rank order, |diff| <= 1e-9',()=>{
 const u=custom.scored_universe,market=custom.cases.find(c=>c.id==='scored-official-forced-recompute').input.synthetic_market;
 const pub=V2.scoreUniverse(u,market,{typeConfig:TC,parameters:P}),rec=V2.scoreUniverse(u,market,{typeConfig:TC,parameters:P,weights:V2.officialWeights(),recomputePublished:true});
 let worst=0;for(const k of Object.keys(pub)){const a=pub[k],b=rec[k];
  for(const ax of ['Q','G','V']){const x=a.axes[ax].score,y=b.axes[ax].score;assert.equal(x===null,y===null,k+ax);if(x!==null)worst=Math.max(worst,Math.abs(x-y));}
  assert.equal(a.total===null,b.total===null,k);if(a.total!==null)worst=Math.max(worst,Math.abs(a.total-b.total));
  assert.deepEqual(b.flags,a.flags,k);assert.equal(b.value_trap_gate,a.value_trap_gate,k);}
 assert.ok(worst<=1e-9,String(worst));assert.deepEqual(rankedCodes(rec),rankedCodes(pub));assert.deepEqual(rec[Object.keys(rec)[0]].profile.recomputed_axes,['Q','G']);});
test('E3: one inner weight changes only affected rows; the official result object is unchanged',()=>{
 const u=custom.scored_universe,market=custom.cases.find(c=>c.id==='scored-q-profitability-40').input.synthetic_market,opts={typeConfig:TC,parameters:P};
 const before=V2.scoreUniverse(u,market,opts),tree=V2.officialWeights();tree.inner.Q.q_profitability=40;
 const mine=V2.scoreUniverse(u,market,{...opts,weights:tree}),after=V2.scoreUniverse(u,market,opts),base=V2.scoreUniverse(u,market,{...opts,weights:V2.officialWeights(),recomputePublished:true});
 assert.deepStrictEqual(after,before);let changed=0;
 for(const[k,r]of Object.entries(mine)){assert.deepStrictEqual(r.axes.G,before[k].axes.G);assert.deepStrictEqual(r.axes.V,before[k].axes.V);
  const has=r.factors.q_profitability.score!==null,o=base[k].axes.Q.score,n=r.axes.Q.score;
  if(!has&&(o===null)===(n===null)&&n!==null)assert.ok(Math.abs(n-o)<=1e-9,k);else if(has&&n!==null&&o!==null&&Math.abs(n-o)>1e-9)changed++;
  const qp=r.q_industry_percentile;assert.equal(r.value_trap_gate,qp!==null&&qp<=V2.GATE_PERCENTILE);}
 assert.ok(changed>20);});
test('invalid weight trees are rejected (sum 0, negative, NaN, unknown factor, ...); zero = excluded, not missing',()=>{
 const bad=custom.units.invalid.map(u=>u.weights);for(const v of [NaN,Infinity,-Infinity]){const t=V2.officialWeights();t.inner.G.g_consistency=v;bad.push(t);}bad.push('balanced',{},[]);
 for(const t of bad)assert.throws(()=>V2.scoreUniverse({},{},{typeConfig:TC,parameters:P,weights:t}),/WEIGHTS_INVALID/,JSON.stringify(t));
 assert.throws(()=>V2.officialWeights('tuned'),/PRESET_INVALID/);
 const w={q_profitability:25,q_moat_proxy:0,q_earnings_quality:20,q_financial_safety:20,q_capital_allocation:15},s={q_profitability:80,q_moat_proxy:null,q_earnings_quality:40,q_financial_safety:null,q_capital_allocation:null},o=V2.axisScore(s,'Q',w);
 assert.deepEqual(o.excluded,['q_moat_proxy']);assert.deepEqual(o.missing,['q_financial_safety','q_capital_allocation']);assert.equal(o.factors_total,4);assert.ok(Math.abs(o.weight_available_official-0.45)<1e-12);assert.equal(V2.axisScore(s,'Q').state,'NOT_AVAILABLE');
 assert.equal(V2.weightsId(V2.validateWeights({...V2.officialWeights(),axis:{Q:34,G:33,V:-0}})),V2.weightsId(V2.validateWeights({...V2.officialWeights(),axis:{Q:34,G:33,V:0}})));});
