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
 assert.equal(scored.base_date,'2026-10-13');assert.equal(scored.base_rule,'SAME_SESSION');
 // B-1: saved on a non-session day → previous completed session is the base; before the first session → NA.
 const gap=sessions.filter(d=>d!=='2026-10-17'&&d!=='2026-10-18'),gapData={...data,sessions:gap};
 const holiday=P.scoreRecord({...r,date:'2026-10-18'},gapData,1);assert.equal(holiday.state,'OK');assert.equal(holiday.base_date,'2026-10-16');assert.equal(holiday.base_rule,'PREVIOUS_COMPLETED_SESSION');assert.equal(holiday.date,'2026-10-19');
 assert.equal(holiday.stock,closes['2026-10-19']/closes['2026-10-16']-1);
 assert.equal(P.scoreRecord({...r,date:'2026-10-12'},gapData,1).reason,'BASE_SESSION_UNAVAILABLE');
});
test('informational E4 records stay outside judgment scoring',()=>{
 const info={symbol:'SYN',date:'2026-10-13',primary_code:'E4',verdict:'',next_check_date:'2026-10-20'},decision={...info,primary_code:'R2',verdict:'R2_ONE_OFF'};
 const original=JSON.stringify(info),onlyInfo=P.scoringHtml([info],{});assert.equal(JSON.stringify(info),original);assert.equal(P.due({records:[info]},'2026-10-20').length,1);assert.match(onlyInfo,/정보 기록 1건 · 채점 제외/);assert.equal((onlyInfo.match(/<tr><td>/g)||[]).length,0);assert.equal(onlyInfo.includes('시스템 판정대로'),false);
 const mixed=P.scoringHtml([info,decision],{});assert.equal((mixed.match(/<tr><td>/g)||[]).length,3);assert.match(mixed,/시스템 판정대로/);
});
test('one daily E4 candidate preserves both news and verified 13F cause codes',()=>{
 const storage=memory();P.recordOccurrences(storage,'2026-10-13','SYN',[{code:'E4',reasons:['NEWS_STRUCTURAL_EVENT']}]);P.recordOccurrences(storage,'2026-10-13','SYN',[{code:'E4',reasons:['THIRTEENF_REPORTED_FULL_EXITS_3_PLUS','NEWS_STRUCTURAL_EVENT']}]);
 const saved=P.read(storage);assert.equal(P.countCandidates(saved).E4,1);assert.deepEqual(saved.occurrences[0].reasons,['NEWS_STRUCTURAL_EVENT','THIRTEENF_REPORTED_FULL_EXITS_3_PLUS']);
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
 const computed={default:'v2',rows:{one:{ticker:'SYN1',rank:1,qg_reference:null,primary:{total:80,q:75,g:70,v:60}},two:{ticker:'SYN2',rank:2,qg_reference:null,primary:{total:70,q:65,g:60,v:50}},three:{ticker:'SYN3',rank:null,qg_reference:null,primary:{total:null,q:null,g:null,v:null}}}},screens={'sec-qgv2.json':{records:{'NYSE:SYN1':{industry_group:'industry'},'NYSE:SYN2':{industry_group:'industry'},'NYSE:SYN3':{industry_group:null}}}};
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
test('quota rollback restores the exact original keys after an earlier replacement freed space',async()=>{
 const B=require('../src/investment_system/product/web_assets/device-backup.js'),L=require('../src/investment_system/product/web_assets/locale.js'),M=require('../src/investment_system/product/web_assets/device-market.js'),D=require('../src/investment_system/product/web_assets/device-profiles.js');
 const oldPrefs={version:1,interests:Array.from({length:20},(_,i)=>'synthetic-issuer-'+i),groups:[]},newPrefs={version:1,interests:[],groups:[]},profiles={...D.empty(),strategies:Array.from({length:3},(_,i)=>({id:'synthetic-'+i,name:'Synthetic '+i,weights:D.copyOfficial()}))},old=B.create(oldPrefs,L.settings(),null,null,M,L,D.empty(),['0000000001']),record={id:'SYN',date:'2026-10-13',symbol:'SYN',primary_code:'E4',secondary_codes:[],type:'default',sector:null,thresholds:{},checks:[],ai_summary:'s'.repeat(12000),verdict:'',action:{kind:'NONE'},next_check_date:null,memo:''},next=B.create(newPrefs,L.settings(),null,null,M,L,profiles,[],{...P.empty(),records:[record]});
 const keys=['investment.web.v1.personal',L.KEY,D.KEY,B.STAR_KEY,P.KEY],values=x=>[x.preferences,x.settings,x.profiles,x.investor_stars,x.playbook].map(v=>JSON.stringify(v)),original=new Map(keys.map((k,i)=>[k,values(old)[i]])),map=new Map(original),size=m=>[...m.values()].reduce((n,v)=>n+v.length,0),cap=size(new Map(keys.map((k,i)=>[k,(i<3?values(next):values(old))[i]])));
 assert.ok(size(original)<=cap);let holdingsWrites=0;
 const storage={getItem:k=>map.get(k)??null,removeItem:k=>map.delete(k),setItem:(k,v)=>{const proposed=new Map(map);proposed.set(k,String(v));if(size(proposed)>cap)throw Error('QuotaExceededError');map.set(k,String(v));}};
 await assert.rejects(B.restore({localStorage:storage,AppLanguage:L,DeviceMarket:M,DeviceActual:{restoreHoldings:async()=>holdingsWrites++}},null,next),/BACKUP_RESTORE_FAILED/);assert.deepEqual(map,original);assert.equal(holdingsWrites,0);
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
test('DC-31: v_now is the official V and v_prev20 stays null (V_HISTORY_NOT_PUBLISHED); no device V history is read',()=>{
 const previous=globalThis.VirtualTradingVHistory,storage=memory(),context={idByTicker:new Map([['SYN','syn']]),computed:{default:'v2',profile:{id:'SYNTHETIC-PROFILE'},rows:{syn:{primary:{q:70,g:60,v:40}}}},heldSymbols:['SYN'],storage};
 globalThis.VirtualTradingVHistory={v2Comparison:()=>{throw new Error('the device V history must not be read');}};
 const f=P.factsFor('SYN',context);assert.equal(f.v_now,40);assert.equal(f.v_prev20,null);assert.equal(f.v_comparison_reason,'V_HISTORY_NOT_PUBLISHED');assert.equal(storage.getItem('investment.web.v2.virtual-trading-v-scores'),null);
 if(previous===undefined)delete globalThis.VirtualTradingVHistory;else globalThis.VirtualTradingVHistory=previous;
});
test('device interests become W1 watch facts independently of holding quantity',()=>{
 const context={idByTicker:new Map([['SYN','syn']]),heldSymbols:[],interests:['syn']};assert.equal(P.factsFor('SYN',context).watched,true);assert.equal(P.factsFor('SYN',context).held,false);assert.equal(P.factsFor('OTHER',context).watched,false);
});
test('approved SIC and strict 5-year revenue volatility classify playbook types without NA passes',()=>{
 const types=(sic,rank,existing={quality:1,defensive:1},extra={})=>P.playbookTypeFacts({sic,metrics:{revenue_volatility_5y_rank_pct:rank,...extra}},existing,null,null);
 assert.equal(types('3674',null).memberships.cyclical,1);
 assert.equal(types('7372',90).memberships.cyclical,1);
 assert.equal(types('2834',20).memberships.defensive,1);
 assert.equal(types('7372',20).memberships.defensive,0);
 assert.equal(types(null,null).memberships.quality,null);assert.equal(types(null,null).memberships.defensive,null);
 assert.equal(types(null,null).memberships.cyclical,null);
 for(const invalid of [NaN,Infinity,-1,101,'20',false])assert.equal(types(null,invalid).metrics.revenue_volatility_5y_rank_pct,null);
 const unchanged={growth:.9,quality:1,defensive:1};const result=types('2834',20,unchanged);assert.equal(result.memberships.growth,.9);assert.deepEqual(unchanged,{growth:.9,quality:1,defensive:1});
 assert.equal(result.metrics.revenue_volatility_5y_rank_pct,.2);assert.equal(result.memberships.quality,null);
 assert.equal(types('7372',50,{}, {roic:.99}).memberships.quality,null);
 const context={idByTicker:new Map([['SYN','syn']]),screens:{'sec-qgv2.json':{records:{'NYSE:SYN':{sic:'2834',metrics:{revenue_volatility_5y_rank_pct:20}}}}}};
 assert.equal(P.factsFor('SYN',context).memberships.defensive,1);assert.equal(P.factsFor('SYN',context).memberships.quality,null);
});
test('quality (#19) reads the published sec-qgv2 fields roic_avg_3y and operating_margin_std_5y_pp',()=>{
 const reader=require('../src/investment_system/product/web_assets/sec-qgv2.js');assert.deepEqual(Object.keys(reader.EXTRA_METRICS).filter(k=>!k.startsWith('ebit_')),['roic_avg_3y','operating_margin_std_5y_pp']);
 const row=metrics=>({idByTicker:new Map([['SYN','syn']]),screens:{'sec-qgv2.json':{records:{'NYSE:SYN':{sic:'3674',metrics}}}}});
 const pass={roic_avg_3y:0.2,operating_margin_std_5y_pp:2.0,net_debt_to_ebitda:1.0};
 let f=P.factsFor('SYN',row(pass));assert.equal(f.memberships.quality,1);assert.equal(f.type_classification.quality.member,true);
 assert.equal(P.factsFor('SYN',row({...pass,operating_margin_std_5y_pp:3.0})).memberships.quality,0);
 assert.equal(P.factsFor('SYN',row({...pass,roic_avg_3y:0.149})).memberships.quality,0);
 const{roic_avg_3y,...noRoic}=pass;assert.equal(P.factsFor('SYN',row(noRoic)).memberships.quality,null);
 const{operating_margin_std_5y_pp,...noStd}=pass;assert.equal(P.factsFor('SYN',row(noStd)).memberships.quality,null);
});
test('v2 facts use their own QG snapshot and ephemeral per-symbol price availability',async()=>{
 const primary={q:70,g:60,v:null,axes:{Q:{state:'READY'},G:{state:'READY'},V:{state:'NOT_AVAILABLE'}}},idByTicker=new Map([['SYN','syn']]),context={idByTicker,computed:{default:'v2',rows:{syn:{primary}},playbook_price_symbols:['SYN']},ram:{state:'NOT_AVAILABLE',rows:[]}};
 const ready=P.factsFor('SYN',context);assert.equal(ready.data.snapshot_missing,false);assert.equal(ready.data.price_missing,false);assert.equal(ready.coverage,'READY');
 const missingQuote=P.factsFor('SYN',{...context,computed:{...context.computed,playbook_price_symbols:[]}});assert.equal(missingQuote.data.price_missing,true);assert.equal(missingQuote.data.snapshot_missing,false);assert.equal(P.factsFor('SYN',{...context,computed:{...context.computed,playbook_price_symbols:['OTHER']}}).data.price_missing,true);assert.equal(P.factsFor('SYN',{...context,computed:{...context.computed,default:'v1',playbook_price_symbols:[]},ram:{state:'AVAILABLE'}}).data.price_missing,false);
 const partial=P.factsFor('SYN',{...context,computed:{...context.computed,rows:{syn:{primary:{...primary,g:null,axes:{...primary.axes,G:{state:'NOT_AVAILABLE'}}}}}}});assert.equal(partial.coverage,'PARTIAL');assert.equal(partial.data.snapshot_missing,true);
 const absent=P.factsFor('SYN',{...context,computed:{...context.computed,rows:{syn:{primary:{q:null,g:null,v:null}}}}});assert.equal(absent.data.snapshot_missing,true);
 const previous=globalThis.QgvScores;
 try{globalThis.QgvScores={collectQuotes:async()=>({'NYSE:SYN':{price:123.456789,currency:'USD'}}),compute:()=>({default:'v2',rows:{syn:{ticker:'SYN',code:'NYSE:SYN',primary}}})};const preparedContext={idByTicker,universeCodes:['NYSE:SYN'],screens:{'sec-qgv2.json':{records:{'NYSE:SYN':{currency:'USD'}}}}},computed=await P.prepareScores({},preparedContext);assert.deepEqual(computed.playbook_price_symbols,['SYN']);assert.equal(JSON.stringify(computed).includes('123.456789'),false);globalThis.QgvScores.collectQuotes=async()=>({'NYSE:SYN':{price:123.456789,currency:'EUR'}});assert.deepEqual((await P.prepareScores({},preparedContext)).playbook_price_symbols,[]);globalThis.QgvScores.collectQuotes=async()=>({'NYSE:OTHER':{price:123.456789,currency:'USD'}});assert.deepEqual((await P.prepareScores({},preparedContext)).playbook_price_symbols,[]);}finally{if(previous===undefined)delete globalThis.QgvScores;else globalThis.QgvScores=previous;}
});
test('navigation keeps shared RAM quotes and selected v2 basis, fresh device reads win without storing prices',async()=>{
 const previous=globalThis.QgvScores,referenceRows={hanmi:{reference_only:true}},cache={'NYSE:SYN':{price:123.456789,currency:'USD'}},primary={q:70,g:60,v:50};let fresh={},seen;
 try{globalThis.QgvScores={collectQuotes:async()=>fresh,compute:args=>{seen=args;return{default:'v2',profile:{preset:args.preset,gate:args.gate},rows:{syn:{ticker:'SYN',code:'NYSE:SYN',primary}}};}};
 const context={idByTicker:new Map([['SYN','syn']]),universeCodes:['NYSE:SYN'],screens:{'sec-qgv2.json':{records:{'NYSE:SYN':{currency:'USD'}}}},scoreOptions:()=>({quotes:cache,preset:'value',gate:false,referenceRows})};
 const first=await P.prepareScores({},context);assert.deepEqual(first.playbook_price_symbols,['SYN']);assert.equal(seen.quotes['NYSE:SYN'].price,123.456789);assert.equal(seen.preset,'value');assert.equal(seen.gate,false);assert.equal(seen.referenceRows,referenceRows);assert.equal(JSON.stringify(first).includes('123.456789'),false);
 fresh={'NYSE:SYN':{price:88.7654321,currency:'USD'}};await P.prepareScores({},context);assert.equal(seen.quotes['NYSE:SYN'].price,88.7654321);assert.equal(cache['NYSE:SYN'].price,123.456789);
 fresh={'NYSE:SYN':{price:88.7654321,currency:'USD'}};context.screens['sec-qgv2.json'].records['NYSE:SYN']={v_inputs:{currency:'EUR'}};assert.deepEqual((await P.prepareScores({},context)).playbook_price_symbols,[]);context.screens['sec-qgv2.json'].records['NYSE:SYN']={v_inputs:{currency:'USD'}};assert.deepEqual((await P.prepareScores({},context)).playbook_price_symbols,['SYN']);
 fresh={};context.scoreOptions=()=>({quotes:{},preset:'balanced',gate:true});const cleared=await P.prepareScores({},context);assert.deepEqual(cleared.playbook_price_symbols,[]);assert.deepEqual(seen.quotes,{});
 }finally{if(previous===undefined)delete globalThis.QgvScores;else globalThis.QgvScores=previous;}
});
test('macro reference-only (M-239): the screen shows CRISIS but no U3 and no macro expansion block; a gate-on copy still applies both',()=>{
 const E=require('../src/investment_system/product/web_assets/playbook-engine.js'),CFG=require('../src/investment_system/product/web_assets/playbook-config-defaults.js');
 const fixture=JSON.parse(require('node:fs').readFileSync(require('node:path').join(__dirname,'../tests/fixtures/playbook_reference_v1.json'),'utf8'));
 assert.equal(CFG.macro.gate_active,false);assert.equal(CFG.macro.gate_status.state,'REFERENCE_ONLY');assert.equal(CFG.macro.gate_status.reason,'REPLAY_PENDING');
 const situation={...fixture.cases.find(c=>c.id==='U3-crisis-all-five').input.situation,symbol:'SYN',macro_state:'CRISIS',macro_available_count:5};
 const codes=j=>[j.primary,...j.secondary].filter(Boolean).map(c=>c.code),macroBlocks=j=>JSON.stringify([j.disabled,j.choices_by_code]).match(/MACRO_[A-Z_]+/g)||[];
 const off=E.evaluate(CFG,situation); // default mode, as openPanel() calls it
 assert.equal(off.macro.state,'CRISIS');assert.equal(off.macro.label,'CRISIS');assert.equal(off.macro.gate,'REFERENCE_ONLY');assert.equal(off.macro.split_multiplier,1);
 assert.ok(!codes(off).includes('U3'));assert.deepEqual(macroBlocks(off),[]);
 const html=P.panelHtml({symbol:'SYN',situation,judgement:off,stored:P.empty(),code:off.primary?.code||'H1'});
 assert.match(html,/CRISIS · 매크로 참고 표시/);assert.ok(!html.includes('data-playbook-code="U3"'));
 const warning=E.evaluate(CFG,{...situation,macro_state:'WARNING',memberships:{...situation.memberships,cyclical:1}});
 assert.equal(warning.macro.state,'WARNING');assert.deepEqual(macroBlocks(warning),[]);assert.equal(warning.macro.split_multiplier,1);
 const on=E.evaluate({...CFG,macro:{...CFG.macro,gate_active:true}},situation);
 assert.ok(codes(on).includes('U3'));assert.ok(macroBlocks(on).includes('MACRO_CRISIS'));assert.ok(macroBlocks(on).includes('MACRO_BLOCK'));assert.equal(on.macro.gate,'ACTIVE');
 assert.ok(!P.panelHtml({symbol:'SYN',situation,judgement:on,stored:P.empty(),code:on.primary.code}).includes('매크로 참고 표시'));
 // Other safety rules are not part of the macro gate and still apply with it off.
 assert.ok(JSON.stringify(E.evaluate(CFG,{...situation,theme_weight_pct:45}).disabled).includes('THEME_CONCENTRATION'));
 assert.ok(JSON.stringify(E.evaluate(CFG,{...situation,sector:'financials'}).disabled).includes(CFG.financial_exception.reason));
});
