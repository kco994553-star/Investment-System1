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
