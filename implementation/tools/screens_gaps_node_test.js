'use strict';
// S06 M3 rank index (RAM only), company search entities, backup-restored notice marker, daily-run estimate and the
// "SEC 수집 전" state. Synthetic identities only; no prices are read or produced here.
const assert=require('node:assert/strict'),dir='../src/investment_system/product/web_assets/';
const View=require(dir+'private-subset-view.js'),Board=require(dir+'leaderboard-screen.js'),Search=require(dir+'entity-search.js'),
 Backup=require(dir+'device-backup.js'),Ops=require(dir+'ops-status.js'),Sec=require(dir+'sec-reported.js');
let pass=0,fail=0;const queue=[];function test(name,f){queue.push([name,f]);}
const listing=(id,symbol)=>({company_id:id,symbol,listing_id:'XNAS:'+symbol+':0000000001',issuer_id:'sec:0000000001'});
function selection(){
 const parsed={row_count:6,row_limit_reached:false,rows:[{row_index:2,code:'NASDAQ:GOOGL',listing:listing('sec_0000000009','GOOGL')},{row_index:3,code:'NASDAQ:GOOG',listing:listing('sec_0000000009','GOOG')},{row_index:4,code:'NASDAQ:NVDA',listing:listing('nvda','NVDA')},{row_index:5,code:'NYSE:BRK.B',listing:listing('sec_0000000002','BRK-B')},{row_index:6,code:'NYSE:ZZZ',listing:null},{row_index:7,code:'NASDAQ:AMD',listing:listing('amd','AMD')}]};
 const full={state:'PERSONAL_REFERENCE',reason_codes:['VALIDATION_INCOMPLETE'],selected:[{group_id:'alphabet',member_symbols:['GOOGL','GOOG'],listing:parsed.rows[0].listing,quality:'WITHIN_TOLERANCE'},{listing:parsed.rows[2].listing,quality:'MISMATCH'},{listing:parsed.rows[3].listing,quality:'WITHIN_TOLERANCE'}],missing:[{row_index:6,reason_codes:['IDENTITY_UNCONFIRMED']},{row_index:7,reason_codes:['SHARES_NOT_AVAILABLE']}]};
 return {parsed,full};
}
test('M3 rank index ranks every verified row, maps groups to member symbols and keeps reasons',()=>{
 const {parsed,full}=selection(),index=View.rankIndex(full,parsed,{config_status:'DEFAULT_V0_UNCALIBRATED'});
 assert.equal(index.state,'READY');assert.equal(index.status,'PARTIAL');assert.equal(index.verified_count,3);assert.equal(index.basis,'M3_DEVICE_V0');
 assert.equal(View.rankFor(index,{company_id:'googl',ticker:'GOOGL'}).rank,1);assert.equal(View.rankFor(index,{company_id:'x',ticker:'GOOG'}).group_id,'alphabet');
 assert.equal(View.rankFor(index,{company_id:'nvda',ticker:'NVDA'}).rank,2);assert.equal(View.rankFor(index,{company_id:'brk',ticker:'BRK.B'}).rank,3);
 assert.deepEqual([...View.rankFor(index,{company_id:'amd',ticker:'AMD'}).reason_codes],['SHARES_NOT_AVAILABLE']);
 assert.deepEqual([...View.rankFor(index,{company_id:'asml',ticker:'ASML'}).reason_codes],['NOT_IN_UNIVERSE']);
 const none=View.rankIndex(null,null);assert.equal(none.state,'NOT_AVAILABLE');assert.deepEqual([...View.rankFor(none,{company_id:'nvda'}).reason_codes],['UNIVERSE_NOT_READ']);
 assert.deepEqual([...View.rankIndex(full,parsed,{reason:'SEC_INPUTS_UNAVAILABLE'}).reason_codes],['SEC_INPUTS_UNAVAILABLE']);
 assert.equal(View.ranks(),null);
});
test('S06 rows carry the M3 rank only when a device index is passed',()=>{
 const {parsed,full}=selection(),index=View.rankIndex(full,parsed),ids=[{company_id:'googl',ticker:'GOOGL',name:'Alphabet'},{company_id:'asml',ticker:'ASML',name:'ASML'},{company_id:'amd',ticker:'AMD',name:'AMD'}];
 const rows=Board.rowsFor(ids,{deviceRanks:index});assert.deepEqual(rows.map(r=>r.m3.rank),[1,null,null]);assert.deepEqual(rows[1].m3.reason_codes,['NOT_IN_UNIVERSE']);assert.deepEqual(rows[2].m3.reason_codes,['SHARES_NOT_AVAILABLE']);
 assert.ok(Board.rowsFor(ids).every(r=>r.m3.state==='NOT_AVAILABLE'&&r.m3.reason_codes[0]==='UNIVERSE_NOT_READ'));
 assert.equal(JSON.stringify(Board.rowsFor(ids)).includes('price'),false);assert.deepEqual(Board.M3_LABEL,['M3 · 내 기기 기준 · v0','M3 · My device · v0']);
});
test('company search covers TARGET identities and Universe504 codes without duplicates or prices',()=>{
 const ids=[{company_id:'nvda',ticker:'NVDA',name:'NVIDIA'},{company_id:'stry',ticker:'SYK',name:'Stryker'}];
 const entities=Search.companyEntities(ids,{'NASDAQ:NVDA':'nvda','NYSE:SYK':'sec_0000000003','NYSE:MMM':'sec_0000000066','NYSE:BRK.B':null,'BAD':'x','NASDAQ:lower':null});
 assert.deepEqual(entities.map(e=>e.canonical_id),['nvda','stry','NYSE:BRK.B','NYSE:MMM']);assert.ok(entities.every(e=>Object.keys(e).sort().join()==='canonical_id,canonical_label,entity_type,scope,ticker'));
 const index=Search.createIndex(entities);assert.equal(index.search('nvda')[0].entity.canonical_id,'nvda');assert.equal(index.search('Stryker')[0].entity.canonical_id,'stry');
 assert.equal(index.search('MMM')[0].entity.canonical_id,'NYSE:MMM');assert.equal(index.search('MMM')[0].entity.scope,'UNIVERSE504');assert.equal(index.search('brk.b')[0].entity.canonical_id,'NYSE:BRK.B');
 assert.deepEqual(Search.companyEntities(null,null),[]);
});
function storage(initial={}){const map=new Map(Object.entries(initial));return {map,getItem:k=>map.has(k)?map.get(k):null,setItem:(k,v)=>map.set(k,String(v)),removeItem:k=>map.delete(k)};}
test('a successful restore leaves a dismissible marker; a failed restore leaves none',async()=>{
 const M=require(dir+'device-market.js'),L=require(dir+'locale.js'),b=Backup.create({version:1,interests:[],groups:[]},{version:1,display_locale:'ko-KR',source_language:'all'},null,null,M,L);
 const ok={localStorage:storage(),AppLanguage:L,DeviceMarket:M,DeviceActual:{restoreHoldings:async()=>{}}};await Backup.restore(ok,null,JSON.parse(JSON.stringify(b)));
 const notice=Backup.restoredNotice(ok.localStorage);assert.equal(notice.schema,Backup.SCHEMA);assert.ok(Number.isFinite(Date.parse(notice.restored_at)));assert.deepEqual(Object.keys(JSON.parse(ok.localStorage.getItem(Backup.RESTORED_KEY))).sort(),['restored_at','schema']);
 assert.equal(Backup.dismissRestored(ok.localStorage),true);assert.equal(Backup.restoredNotice(ok.localStorage),null);
 const bad={localStorage:storage(),AppLanguage:L,DeviceMarket:M,DeviceActual:{restoreHoldings:async()=>{throw Error('STORAGE');}}};await assert.rejects(Backup.restore(bad,null,b));assert.equal(bad.localStorage.getItem(Backup.RESTORED_KEY),null);
 assert.equal(Backup.restoredNotice(storage({[Backup.RESTORED_KEY]:'{"restored_at":"x","schema":"investment-device-backup/3"}'})),null);assert.equal(Backup.restoredNotice(storage({[Backup.RESTORED_KEY]:'{bad'})),null);
 assert.equal(Backup.mountRestoredNotice(null),null);
});
test('daily run is estimated from public timestamps only',()=>{
 const now=Date.parse('2026-10-11T10:00:00Z'),screen=(as_of,state='LIVE')=>({state,as_of,stale_after_seconds:172800,reason_codes:[]});
 const names=['sec-qg-factors.json','company-types-pricefree.json','sec-filing-windows.json','macro-screen.json','sec-13f-changes.json','company-classification.json'];
 const screens=Object.fromEntries(names.map(n=>[n,screen('2026-10-10T22:30:00Z')])),secReported={companies:{a:{status:'LIVE',acquired_at:'2026-10-10T22:25:00Z',reason_codes:[]}}};
 const ok=Ops.dailyRun({secReported,screens,now});assert.equal(ok.state,'SUCCESS');assert.equal(ok.latest_at,'2026-10-10T22:30:00.000Z');assert.equal(ok.elapsed_hours,11.5);assert.equal(ok.files_in_run,7);
 const partial=Ops.dailyRun({secReported,screens:{...screens,'macro-screen.json':screen('2026-10-10T22:30:00Z','NOT_AVAILABLE')},now});assert.equal(partial.state,'PARTIAL');assert.deepEqual(partial.reason_codes,['macro-screen.json']);
 assert.equal(Ops.dailyRun({secReported,screens:{...screens,'sec-13f-changes.json':screen('2026-10-08T22:30:00Z')},now}).state,'PARTIAL');
 const failed=Ops.dailyRun({secReported,screens,now:now+2*86400000});assert.equal(failed.state,'FAILED');assert.deepEqual(failed.reason_codes,['NO_PUBLISH_WITHIN_CADENCE']);
 const before=Ops.dailyRun({secStatus:{reason:'SEC_NOT_COLLECTED'},now});assert.equal(before.state,'NOT_AVAILABLE');assert.deepEqual(before.reason_codes,['SEC_NOT_COLLECTED']);
 assert.deepEqual(Ops.summarize({secStatus:{reason:'SEC_NOT_COLLECTED'}})[0].reason_codes,['SEC_NOT_COLLECTED']);assert.deepEqual(Ops.summarize({})[0].reason_codes,['NOT_CONNECTED']);
});
test('SEC public inputs 404 is a handled SEC_NOT_COLLECTED state, other failures stay distinct',async()=>{
 assert.equal(Sec.status().state,'NOT_LOADED');
 assert.equal(await Sec.load({fetch:async()=>({ok:false,status:404})}),null);assert.deepEqual({...Sec.status()},{state:'NOT_AVAILABLE',reason:'SEC_NOT_COLLECTED'});
 assert.equal(await Sec.load({fetch:async()=>({ok:false,status:503})}),null);assert.equal(Sec.status().reason,'SEC_PUBLIC_INPUT_UNAVAILABLE');
 assert.equal(await Sec.load({fetch:async()=>{throw Error('offline');}}),null);assert.equal(Sec.status().reason,'SEC_PUBLIC_INPUT_UNAVAILABLE');
 assert.equal(await Sec.load({fetch:async()=>({ok:true,status:200,text:async()=>'{"schema":"x"}'})}),null);assert.equal(Sec.status().reason,'SEC_PUBLIC_INPUT_INVALID');
});
(async()=>{
 for(const [name,f] of queue){try{await f();pass++;console.log('PASS '+name);}catch(e){fail++;console.log('FAIL '+name+(process.env.DEBUG_TEST?' '+e.stack:''));}}
 console.log('COUNTS pass='+pass+' fail='+fail);if(fail)process.exitCode=1;
})();
