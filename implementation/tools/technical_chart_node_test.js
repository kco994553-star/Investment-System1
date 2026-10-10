'use strict';const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const p=path.join(__dirname,'../src/investment_system/product/web_assets/technical-chart.js'),api=fs.existsSync(p)?require(p):{};let pass=0,fail=0;
function test(name,f){try{f();pass++;console.log('PASS '+name);}catch(_){fail++;console.log('FAIL '+name);}}
test('common candle MA and AVG scale includes all known values',()=>{const bars=[{open:10,close:12,low:9,high:13},{open:12,close:11,low:10,high:14}],g=api.geometry(bars,[[null,15]],8);assert.equal(g.x(0),20);assert.equal(g.x(1),620);assert.ok(Math.abs(g.y(15)-20)<1e-10);assert.ok(Math.abs(g.y(8)-220)<1e-10);assert.ok(g.y(13)>g.y(15));});
test('missing moving average values split paths and warmup draws none',()=>{const g=api.geometry([{close:1,low:null,high:null,open:null},{close:2,low:null,high:null,open:null}]);assert.equal(api.paths([null,null],g).length,0);assert.equal(api.paths([1,null,2],g).length,2);});
test('extreme finite prices remain finite in chart coordinates',()=>{const g=api.geometry([{close:Number.MAX_VALUE,low:Number.MAX_VALUE/2,high:Number.MAX_VALUE,open:Number.MAX_VALUE}]);assert.ok(Number.isFinite(g.y(Number.MAX_VALUE)));assert.ok(Number.isFinite(g.y(Number.MAX_VALUE/2)));});
console.log('COUNTS pass='+pass+' fail='+fail);if(fail)process.exitCode=1;
