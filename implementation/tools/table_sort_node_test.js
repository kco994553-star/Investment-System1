'use strict';
// PC table sorting (table-sort.js) pure helpers: cell keys, NOT_AVAILABLE last in both directions, stable ties. Synthetic values only.
const assert=require('node:assert/strict');
const S=require('../src/investment_system/product/web_assets/table-sort.js');
let pass=0,fail=0;function test(name,f){try{f();pass++;console.log('PASS '+name);}catch(e){fail++;console.log('FAIL '+name+' '+(e.code==='ERR_ASSERTION'?'CONTRACT':'EXECUTION'));if(process.env.DEBUG_TEST)console.log(e);}}
test('cell keys: numbers, percents, dates, text and NOT_AVAILABLE forms',()=>{
 assert.deepEqual(S.keyOf('12.5%'),{kind:'number',value:12.5});
 assert.deepEqual(S.keyOf('−3.1pp'),{kind:'number',value:-3.1});
 assert.deepEqual(S.keyOf('1,234'),{kind:'number',value:1234});
 assert.deepEqual(S.keyOf('#7'),{kind:'number',value:7});
 assert.deepEqual(S.keyOf('12/19'),{kind:'number',value:12});
 assert.equal(S.keyOf('2026-10-19').kind,'text');
 assert.equal(S.keyOf('NASDAQ').kind,'text');
 for(const v of ['','—','-','N/A','NA','NOT_AVAILABLE','NOT_AVAILABLE · SEC_QG_FACTORS_MISSING','[—]','— · (est.)'])assert.equal(S.keyOf(v).kind,'missing',v);
});
test('NOT_AVAILABLE sorts last ascending and descending',()=>{
 const texts=['5','—','2','NOT_AVAILABLE · X','9','N/A'];
 assert.deepEqual(S.order(texts,1).map(i=>texts[i]),['2','5','9','—','NOT_AVAILABLE · X','N/A']);
 assert.deepEqual(S.order(texts,-1).map(i=>texts[i]),['9','5','2','—','NOT_AVAILABLE · X','N/A']);
});
test('stable: equal keys keep original order in both directions',()=>{
 const texts=['b','a','B','a','A'];
 assert.deepEqual(S.order(texts,1),[1,3,4,0,2]);
 assert.deepEqual(S.order(texts,-1),[0,2,1,3,4]);
});
test('numbers before text, text uses numeric collation',()=>{
 const texts=['item 10','item 2','3','x'];
 assert.deepEqual(S.order(texts,1).map(i=>texts[i]),['3','item 2','item 10','x']);
 assert.equal(S.QUERY,'(min-width: 1024px)');
});
test('structured data-sort-value keys win over display text (S06 numeric columns); empty = NOT_AVAILABLE',()=>{
 const cell=(text,value)=>({textContent:text,hasAttribute:k=>k==='data-sort-value'&&value!==undefined,getAttribute:()=>value});
 assert.deepEqual(S.cellKey(cell('61.2 QGV 종합 순위 밖 · Q 12.0','61.234')),{kind:'number',value:61.234});
 assert.deepEqual(S.cellKey(cell('—','')),{kind:'missing'});assert.deepEqual(S.cellKey(cell('12/19')),{kind:'number',value:12});assert.deepEqual(S.cellKey(null),{kind:'missing'});
 const cells=[cell('9.0 x','9'),cell('—',''),cell('10.0 y','10'),cell('2.5','2.5'),cell('1e1 tie','10')],keys=cells.map(S.cellKey);
 assert.deepEqual(S.orderKeys(keys,1),[3,0,2,4,1]);assert.deepEqual(S.orderKeys(keys,-1),[2,4,0,3,1]);
});
console.log('COUNTS pass='+pass+' fail='+fail);if(fail)process.exitCode=1;
