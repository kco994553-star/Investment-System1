'use strict';
// Device value view (v1+dcf_v1_default): JS port vs Python reference vectors, reader validation, value-card HTML.
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const W=path.join(__dirname,'../src/investment_system/product/web_assets');
const V=require(path.join(W,'device-valuation.js')),CS=require(path.join(W,'company-screen.js')),P=require(path.join(W,'dcf-parameters-defaults.js'));
const vectors=JSON.parse(fs.readFileSync(path.join(__dirname,'../tests/fixtures/device_valuation_reference_v1.json'),'utf8'));
function equal(a,b,at='$'){if(typeof b==='number'){assert.equal(typeof a,'number',at);assert.ok(Number.isFinite(a)&&Math.abs(a-b)<=Math.max(1e-10,Math.abs(b)*1e-10),at+' '+a+' vs '+b);}else if(Array.isArray(b)){assert.ok(Array.isArray(a),at);assert.equal(a.length,b.length,at);b.forEach((v,i)=>equal(a[i],v,at+'['+i+']'));}else if(b&&typeof b==='object'){assert.deepEqual(Object.keys(a).sort(),Object.keys(b).sort(),at);Object.keys(b).forEach(k=>equal(a[k],b[k],at+'.'+k));}else assert.equal(a,b,at);}
for(const c of vectors.cases)test('python reference vector '+c.id,()=>{const input=structuredClone(c.input),before=JSON.stringify(input);equal(V.view(input),c.expected);assert.equal(JSON.stringify(input),before,'input not mutated');});
test('default parameters come from the separate dcf_parameters/v1-default copy',()=>{assert.equal(V.parameters(),P);assert.equal(P.status,'V1_UNCALIBRATED_DEFAULT');assert.equal(P.config_version,'dcf_parameters/v1-default');assert.ok(Object.isFrozen(P.solver));
 const r=V.view({row:vectors.cases[0].input.row,quote:{price:100,currency:'USD'}});equal(r,vectors.cases[0].expected);});
test('view never returns the price or anything keyed as price',()=>{const r=V.view({row:vectors.cases[0].input.row,quote:{price:123.456,currency:'USD'}});const text=JSON.stringify(r);assert.ok(!text.includes('123.456'));assert.ok(!/"price"/i.test(text));});
test('reader rejects files that are not the valuation file or carry extra fields',()=>{assert.throws(()=>V.validate('sec-qg-factors.json',{}),/PUBLIC_SCREEN_INVALID/);assert.throws(()=>V.validate(V.FILE,{schema_version:1}),/PUBLIC_SCREEN_INVALID/);});
test('deviceQuote reads only DeviceActual.ramQuote and fails closed',async()=>{const calls=[];const win={DeviceActual:{ramQuote:async(w,c,t)=>{calls.push(t);return{price:50,currency:'USD',as_of:'2026-10-10T00:00:00Z',source:'MANUAL',stale:false};}}};
 assert.deepEqual(await V.deviceQuote(win,{},'NVDA'),{price:50,currency:'USD',as_of:'2026-10-10T00:00:00Z',source:'MANUAL',stale:false});assert.deepEqual(calls,['NVDA']);
 assert.equal(await V.deviceQuote({DeviceActual:{ramQuote:async()=>({price:0,currency:'USD'})}},{},'X'),null);assert.equal(await V.deviceQuote({},{},'X'),null);assert.equal(await V.deviceQuote({DeviceActual:{ramQuote:async()=>{throw Error('x');}}},{},'X'),null);});
test('value card: badge, defaults, NA reasons everywhere else',()=>{const c=vectors.cases.find(x=>x.id==='full'),html=CS.valueHtml({locale:'ko-KR',row:{fcfe:{...c.input.row.fcfe,fiscal_period_end:'2025-12-31',form:'10-K',accn:'000104581026000001'}},result:c.expected,quote:{source:'MANUAL',as_of:'2026-10-10T00:00:00Z'},params:P});
 assert.ok(html.includes('v1 UNCALIBRATED 기본값'));assert.ok(html.includes('v1+dcf_v1_default'));assert.ok(html.includes('명시 5년 · 할인율 10.0% · 영구성장 2.0% · 역DCF 탐색 −50.0%~+100.0%'));
 assert.ok(html.includes('0001045810-26-000001'));assert.ok(html.includes('data-implied-growth>0.8%'));assert.equal((html.match(/EXPLICIT_GROWTH_UNDECIDED/g)||[]).length,3);
 assert.ok(html.includes('data-v-factor="reverse_dcf"'));assert.ok(!html.includes('100.0</span>'));
 const empty=CS.valueHtml({locale:'ko-KR',params:P});assert.ok(empty.includes('NOT_AVAILABLE'));assert.ok(empty.includes('NO_DEVICE_PRICE'));assert.ok(!/data-implied-growth/.test(empty));
 const en=CS.valueHtml({locale:'en-US',params:P,compact:true});assert.ok(en.includes('v1 UNCALIBRATED default'));assert.ok(!en.includes('data-v-table'));});
