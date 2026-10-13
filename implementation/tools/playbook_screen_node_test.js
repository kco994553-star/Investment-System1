'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const P=require('../src/investment_system/product/web_assets/playbook-screen.js');
const memory=()=>{const m=new Map();return{getItem:k=>m.get(k)??null,setItem:(k,v)=>m.set(k,String(v)),removeItem:k=>m.delete(k)}};
test('required thesis and hold fields, invalid dates, backup roundtrip and due followup',()=>{
 const s=memory();assert.throws(()=>P.saveThesis(s,'SYN','','no'),/THESIS_REQUIRED/);
 P.saveThesis(s,'SYN','Recurring cash flow','Margin deterioration');
 assert.throws(()=>P.saveHold(s,'SYN',{reason:'Wait',release_condition:'Filing',release_date:'2026-02-30'}),/HOLD_REQUIRED/);
 P.saveHold(s,'SYN',{reason:'Wait',release_condition:'Filing',release_date:'2026-10-20'});
 const r={id:'SYN1',date:'2026-10-13',symbol:'SYN',primary_code:'R2',secondary_codes:[],type:'quality',sector:'software_internet',thresholds:{},checks:[],ai_summary:'Synthetic answer',verdict:'R2_ONE_OFF',action:{action:'MAINTAIN'},next_check_date:'2026-10-15',memo:'Synthetic'};
 P.saveRecord(s,r);assert.equal(P.due(P.read(s),'2026-10-15').length,1);
 const copy=JSON.parse(JSON.stringify(P.read(s)));const t=memory();P.write(t,copy);assert.deepEqual(P.read(t),copy);
 P.recordOccurrences(s,'2026-10-13','SYN',[{code:'T1',reasons:['V_DETERIORATED']}]);P.recordOccurrences(s,'2026-10-13','SYN',[{code:'T1',reasons:['V_DETERIORATED']}]);assert.equal(P.countCandidates(P.read(s)).T1,1);
});
test('actual sessions scoring never fabricates prices and rejects unconfirmed result',()=>{
 const r={date:'2026-10-13',symbol:'SYN',action:{action:'MAINTAIN'}},sessions=Array.from({length:22},(_,i)=>new Date(Date.UTC(2026,9,13+i)).toISOString().slice(0,10));
 assert.equal(P.scoreRecord(r,null,20).state,'NOT_AVAILABLE');
 const closes=Object.fromEntries(sessions.map((d,i)=>[d,100+i]));const data={sessions,stock:closes,sector:closes,sp500:closes,sector_symbol:'XLK'};
 const scored=P.scoreRecord(r,data,20);assert.equal(scored.state,'OK');assert.equal(scored.sector_excess,0);assert.equal(scored.sp500_excess,0);
 assert.equal(P.scoreRecord(r,data,63).reason,'WINDOW_PENDING');
});
test('quarter comparison uses calendar quarters, no fabricated snapshots',()=>{
 const snapshots={'2026-04-30':{syn:{q:80,g:81}},'2026-07-03':{syn:{q:76,g:79}},'2026-08-31':{syn:{q:75,g:78}},'2026-10-13':{syn:{q:70,g:73}}};
 assert.deepEqual(P.quarterComparisons(snapshots,'syn','2026-10-13'),{q_prev:75,g_prev:78,q_prev2:80,g_prev2:81});
 assert.deepEqual(P.quarterComparisons({},'syn','2026-10-13'),{q_prev:null,g_prev:null,q_prev2:null,g_prev2:null});
});
test('same-day new review supersedes prior followup and cross-version quarter snapshots are unavailable',()=>{
 const r={symbol:'SYN',date:'2026-10-13',next_check_date:'2026-10-13'},next={...r,next_check_date:'2026-10-20'};
 assert.equal(P.due({records:[r,next]},'2026-10-13').length,0);
 assert.deepEqual(P.quarterComparisons({'2026-07-02':{syn:{q:99,g:99}}},'syn','2026-10-13','v2','v1'),{q_prev:null,g_prev:null,q_prev2:null,g_prev2:null});
 assert.throws(()=>P.targetValidate({rows:[],cash_pct:-1}),/TARGET_CASH_INVALID/);
});
test('TARGET candidates use v2 industry ranks and comparison includes exits and remaining-difference steps',()=>{
 const computed={default:'v2',rows:{one:{ticker:'SYN1',primary:{total:80,q:75,g:70}},two:{ticker:'SYN2',primary:{total:70,q:65,g:60}},three:{ticker:'SYN3',primary:{total:null,q:null,g:null}}}},screens={'sec-qgv2.json':{records:{'NYSE:SYN1':{industry_group:'industry'},'NYSE:SYN2':{industry_group:'industry'},'NYSE:SYN3':{industry_group:null}}}};
 const ranked=P.candidateRanking(computed,screens,['NYSE:SYN1','NYSE:SYN2','NYSE:SYN3']);assert.equal(ranked[0].industry_rank,1);assert.equal(ranked[1].industry_rank,2);assert.equal(ranked[2].total,null);
 const compared=P.targetComparison({rows:[{symbol:'SYN2',pct:10,sector:'industrial'}],cash_pct:90,transition_quarters:2},{total_units:10000,instruments:[{ticker:'SYN1',target_units:1000}]},ranked);
 assert.equal(compared.changes[0].change,'제외');assert.deepEqual(compared.changes[0].steps,[5,2.5]);assert.equal(compared.changes[1].change,'편입');assert.equal(compared.trade_amount,null);assert.equal(compared.tax,null);
});
test('backup TARGET rejects malformed drafts and HTML attribute payloads',()=>{
 for(const draft of [{rows:42},{rows:[{}]},{rows:[],cash_pct:'0" autofocus onfocus="alert(1)',transition_plan:'x',transition_quarters:2,first_apply:'2027-02'}]){
  assert.throws(()=>P.validate({...P.empty(),target_draft:draft}),/PLAYBOOK_INVALID|TARGET_/);
 }
});
test('UTF-8 backups beyond old 1MB limit roundtrip, oversize rejected without truncation',()=>{
 const B=require('../src/investment_system/product/web_assets/device-backup.js'),L=require('../src/investment_system/product/web_assets/locale.js'),M=require('../src/investment_system/product/web_assets/device-market.js'),D=require('../src/investment_system/product/web_assets/device-profiles.js');
 const record=i=>({id:'SYN'+i,date:'2026-10-13',symbol:'SYN',primary_code:'E4',secondary_codes:[],type:'default',sector:null,thresholds:{},checks:[],ai_summary:'합성'.repeat(6000),verdict:'',action:{kind:'NONE'},next_check_date:null,memo:''});
 const playbook={...P.empty(),records:Array.from({length:100},(_,i)=>record(i))},backup=B.create({version:1,interests:[],groups:[]},L.settings(),null,null,M,L,D.empty(),[],playbook);
 const bytes=new TextEncoder().encode(JSON.stringify(backup)).length;assert.ok(bytes>1000000&&bytes<B.MAX_BYTES);assert.deepEqual(B.parse(JSON.parse(JSON.stringify(backup)),null,M,L).playbook,playbook);
 const oversize={...playbook,records:Array.from({length:500},(_,i)=>record(i))};assert.throws(()=>B.create({version:1,interests:[],groups:[]},L.settings(),null,null,M,L,D.empty(),[],oversize),/BACKUP_TOO_LARGE/);assert.equal(oversize.records.length,500);assert.throws(()=>B.validateSize({s:'x'.repeat(B.MAX_BYTES-10)}),/BACKUP_TOO_LARGE/);
});
test('malformed imported TARGET is rejected before any storage is changed',async()=>{
 const B=require('../src/investment_system/product/web_assets/device-backup.js'),L=require('../src/investment_system/product/web_assets/locale.js'),M=require('../src/investment_system/product/web_assets/device-market.js');const storage=memory();P.saveThesis(storage,'SYN','Synthetic reason','Synthetic invalidation');const before=storage.getItem(P.KEY),backup=B.create({version:1,interests:[],groups:[]},L.settings(),null,null,M,L);backup.playbook.target_draft={rows:[],cash_pct:'0" autofocus onfocus="alert(1)',transition_plan:'Synthetic',transition_quarters:2,first_apply:'2027-02'};
 let holdingsWrites=0;await assert.rejects(B.restore({localStorage:storage,AppLanguage:L,DeviceMarket:M,DeviceActual:{restoreHoldings:async()=>holdingsWrites++}},null,backup));assert.equal(storage.getItem(P.KEY),before);assert.equal(holdingsWrites,0);
});
test('zero quantities are closed while positive holdings with missing quotes remain held',()=>{
 const catalog={instruments:[{ticker:'SYN0',security_reference:{scheme:'SYNTHETIC',value:'zero'}},{ticker:'SYN1',security_reference:{scheme:'SYNTHETIC',value:'positive'}}]},snapshot={themes:[{holdings:[{security_reference:{value:'zero',scheme:'SYNTHETIC'},quantity:'0'},{security_reference:{scheme:'SYNTHETIC',value:'positive'},quantity:'1'}]}]};assert.deepEqual(P.positiveHeldSymbols(snapshot,catalog),['SYN1']);
 const idByTicker=new Map([['SYN0','syn0'],['SYN1','syn1']]),ram={state:'NOT_AVAILABLE',rows:[{ticker:'SYN0',weight:null},{ticker:'SYN1',weight:null}]},context={catalog,idByTicker,ram,heldSymbols:['SYN1']};assert.equal(P.factsFor('SYN0',context).held,false);assert.equal(P.factsFor('SYN1',context).held,true);
});
test('manual invalidation event requires provenance and never parses AI text',()=>{
 const storage=memory();P.saveThesis(storage,'SYN','Synthetic thesis','Synthetic condition');
 assert.throws(()=>P.saveThesis(storage,'SYN','Synthetic thesis','Synthetic condition',{status:'OCCURRED',source:'',grade:'SIGNAL'}),/INVALIDATION_SOURCE_REQUIRED/);
 P.saveThesis(storage,'SYN','Synthetic thesis','Synthetic condition',{status:'OCCURRED',source:'Synthetic filing link',grade:'EVIDENCE'});assert.equal(P.read(storage).theses.SYN.event.status,'OCCURRED');
 assert.throws(()=>P.saveThesis(storage,'SYN','Synthetic thesis','Synthetic condition',{status:'OCCURRED',source:'Synthetic source',grade:'GUESS'}),/INVALIDATION_EVENT_INVALID/);
 P.saveThesis(storage,'SYN','Synthetic thesis','Synthetic condition',{status:'UNKNOWN',source:'',grade:'BELIEF'});assert.equal(P.read(storage).theses.SYN.event.status,'UNKNOWN');
});
