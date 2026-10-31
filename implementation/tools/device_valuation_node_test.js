'use strict';
// Device value view (v1+dcf_v1_1_default): JS port vs Python reference vectors, reader validation, value-card HTML.
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const W=path.join(__dirname,'../src/investment_system/product/web_assets');
const V=require(path.join(W,'device-valuation.js')),P=require(path.join(W,'dcf-parameters-defaults.js'));
const vectors=JSON.parse(fs.readFileSync(path.join(__dirname,'../tests/fixtures/device_valuation_reference_v1.json'),'utf8'));
function equal(a,b,at='$'){if(typeof b==='number'){assert.equal(typeof a,'number',at);assert.ok(Number.isFinite(a)&&Math.abs(a-b)<=Math.max(1e-10,Math.abs(b)*1e-10),at+' '+a+' vs '+b);}else if(Array.isArray(b)){assert.ok(Array.isArray(a),at);assert.equal(a.length,b.length,at);b.forEach((v,i)=>equal(a[i],v,at+'['+i+']'));}else if(b&&typeof b==='object'){assert.deepEqual(Object.keys(a).sort(),Object.keys(b).sort(),at);Object.keys(b).forEach(k=>equal(a[k],b[k],at+'.'+k));}else assert.equal(a,b,at);}
for(const c of vectors.cases)test('python reference vector '+c.id,()=>{const input=structuredClone(c.input),before=JSON.stringify(input);equal(V.view(input),c.expected);assert.equal(JSON.stringify(input),before,'input not mutated');});
test('default parameters come from the separate dcf_parameters/v1.1-default copy',()=>{assert.equal(V.parameters(),P);assert.equal(P.status,'V1_1_UNCALIBRATED_DEFAULT');assert.equal(P.config_version,'dcf_parameters/v1.1-default');assert.ok(Object.isFrozen(P.solver)&&Object.isFrozen(P.explicit_growth_rule));
 assert.deepEqual({...P.explicit_growth_rule},{kind:'REVENUE_CAGR_3Y_CLAMP',metric:'revenue_cagr_3y',lower:0,upper:0.15,status:'PROVISIONAL'});
 const r=V.view({row:vectors.cases[0].input.row,quote:{price:100,currency:'USD'}});equal(r,vectors.cases[0].expected);});
test('view never returns the price or anything keyed as price',()=>{const r=V.view({row:vectors.cases[0].input.row,quote:{price:123.456,currency:'USD'}});const text=JSON.stringify(r);assert.ok(!text.includes('123.456'));assert.ok(!/"price"/i.test(text));});
test('reader rejects files that are not the valuation file or carry extra fields',()=>{assert.throws(()=>V.validate('sec-qg-factors.json',{}),/PUBLIC_SCREEN_INVALID/);assert.throws(()=>V.validate(V.FILE,{schema_version:1}),/PUBLIC_SCREEN_INVALID/);});
test('deviceQuote reads only DeviceActual.ramQuote and fails closed',async()=>{const calls=[];const win={DeviceActual:{ramQuote:async(w,c,t)=>{calls.push(t);return{price:50,currency:'USD',as_of:'2026-10-10T00:00:00Z',source:'MANUAL',stale:false};}}};
 assert.deepEqual(await V.deviceQuote(win,{},'NVDA'),{price:50,currency:'USD',as_of:'2026-10-10T00:00:00Z',source:'MANUAL',stale:false});assert.deepEqual(calls,['NVDA']);
 assert.equal(await V.deviceQuote({DeviceActual:{ramQuote:async()=>({price:0,currency:'USD'})}},{},'X'),null);assert.equal(await V.deviceQuote({},{},'X'),null);assert.equal(await V.deviceQuote({DeviceActual:{ramQuote:async()=>{throw Error('x');}}},{},'X'),null);});
// DC-31 (2026-10-31): the S04/S05 value card that rendered this view (CompanyScreen.valueHtml) is removed with the device V;
// the reader and view stay until the cleanup PR after 11/16.
