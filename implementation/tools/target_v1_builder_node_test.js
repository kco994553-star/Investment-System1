'use strict';
// TARGET v1 builder (owner decision 2026-10-14): filters, sector cap, selection and weights, template generation, replacement on
// 반대, the §16 limits re-check, finalize gate (number check), virtual set index and the fixed review rule. Synthetic data only.
const test=require('node:test'),assert=require('node:assert/strict');
const W='../src/investment_system/product/web_assets/';
const B=require(W+'target-v1-builder.js'),CFG=require(W+'target-v1-config-defaults.js'),PCFG=require(W+'playbook-config-defaults.js'),P=require(W+'playbook-screen.js');
const memory=()=>{const m=new Map();return{getItem:k=>m.get(k)??null,setItem:(k,v)=>m.set(k,String(v)),removeItem:k=>m.delete(k)};};
const FACTORS={q_profitability:90,q_moat_proxy:80,q_earnings_quality:70,q_financial_safety:60,q_capital_allocation:50,g_revenue_growth:85,g_per_share_growth:40,g_growth_efficiency:30,g_consistency:20,g_recent_acceleration:10};
const METRICS={roic:0.25,gross_profit_to_assets:0.3,moat_return_mean_5y:0.2,fcf_to_net_income:1.1,net_debt_to_ebitda:1,interest_coverage:12,revenue_cagr_3y:0.12,eps_cagr_3y:0.2,incremental_roic_3y:0.3,revenue_positive_growth_share:0.8,revenue_ttm_growth:0.1};
// One synthetic Universe company: v2 accessor row (QgvScores shape) + public sec-qgv2 record (Qgv2Inputs shape).
function universe(list){
 const computed={v2_state:'READY',v2_as_of:'2026-10-13',profile:{id:'qgv-v2/balanced/gate-on'},priced_codes:list.length,rows:{}},inputs={records:{}},codes=[];
 list.forEach((c,i)=>{const code='NASDAQ:'+c.symbol,ax=(s,w=1)=>({score:s,weight_available:w,state:s===null?'NOT_AVAILABLE':'READY'});codes.push(code);
  const factors={};for(const[f,s]of Object.entries(c.factors||FACTORS))factors[f]={score:s};
  computed.rows['id'+i]={ticker:c.symbol,code,v2:{total:c.total,q:c.q??60,g:c.g??60,v:c.v??50,axes:{Q:ax(c.q===undefined?60:c.q,c.qw??1),G:ax(c.g??60),V:ax(c.v===undefined?50:c.v)},factors,
   factors_available:c.fa??15,factors_total:15,q_industry_percentile:c.qp??55,value_trap_gate:c.trap===true,selected_types:c.types||['quality']}};
  inputs.records[code]={cik:c.cik||('C'+i),sic:c.sic||'7372',industry_group:c.ig||'services',metrics:{...METRICS,...(c.metrics||{})},qg_axes:{Q:{score:c.q===undefined?60:c.q},G:{score:c.g??60}}};});
 return{computed,inputs,universeCodes:codes};
}
const SICS=['7372','3674','3559','3612','3812','3823','2834','5812','4911','1311','2080','6798'];
function wide(n=40,extra=[]){const list=[];for(let i=0;i<n;i++)list.push({symbol:'S'+String(i).padStart(2,'0'),total:90-i*0.5,sic:SICS[i%SICS.length],ig:'grp'+(i%SICS.length)});return universe([...list,...extra]);}

test('filters: axis coverage, value-trap gate and financial safety (known thresholds only)',()=>{
 assert.equal(B.safety({net_debt_to_ebitda:3,interest_coverage:10}).state,'FAIL');
 assert.equal(B.safety({net_debt_to_ebitda:2.9,interest_coverage:2.99}).state,'FAIL');
 assert.equal(B.safety({net_debt_to_ebitda:2.9,interest_coverage:3}).state,'PASS');
 assert.equal(B.safety({interest_coverage:20}).state,'UNKNOWN');assert.equal(B.safety({}).state,'UNKNOWN');
 const u=universe([{symbol:'OK',total:80},{symbol:'AXIS',total:79,q:null},{symbol:'THIN',total:78,qw:0.4},{symbol:'TRAP',total:77,trap:true},{symbol:'DEBT',total:76,metrics:{net_debt_to_ebitda:3.5}},
  {symbol:'COVER',total:75,metrics:{interest_coverage:2}},{symbol:'MISS',total:74,metrics:{net_debt_to_ebitda:null,interest_coverage:null}},{symbol:'NOV',total:73,v:null}]);
 const rows=B.universeRows({...u,existing:['OK']}),why=Object.fromEntries(rows.map(r=>[r.symbol,B.exclusions(r)]));
 assert.deepEqual(why,{OK:[],AXIS:['AXIS_COVERAGE_LOW'],THIN:['AXIS_COVERAGE_LOW'],TRAP:['VALUE_TRAP_GATE'],DEBT:['FINANCIAL_SAFETY_FAIL'],COVER:['FINANCIAL_SAFETY_FAIL'],MISS:[],NOV:['AXIS_COVERAGE_LOW']});
 assert.equal(rows.find(r=>r.symbol==='MISS').safety.state,'UNKNOWN');assert.equal(rows.find(r=>r.symbol==='OK').in19,true);
 const draft=B.buildDraft({...u,existing:[],date:'2026-10-14'});
 assert.deepEqual(draft.pool.map(r=>r.symbol),['OK','MISS']);assert.deepEqual(draft.excluded_counts,{AXIS_COVERAGE_LOW:3,VALUE_TRAP_GATE:1,FINANCIAL_SAFETY_FAIL:2});
 assert.throws(()=>B.buildDraft({...u,computed:{...u.computed,v2_state:'NOT_AVAILABLE'},existing:[],date:'2026-10-14'}),/QGV2_NOT_READY/);
});

test('one point per issuer, industry rank and coverage label from the public file',()=>{
 const u=universe([{symbol:'GOOGL',total:70,cik:'X',ig:'a'},{symbol:'GOOG',total:71,cik:'X',ig:'a'},{symbol:'B1',total:60,ig:'a'},{symbol:'B2',total:65,ig:'b'}]);
 const rows=B.universeRows({...u,existing:[]});assert.deepEqual(rows.map(r=>r.symbol).sort(),['B1','B2','GOOG']);
 const g=rows.find(r=>r.symbol==='GOOG'),b1=rows.find(r=>r.symbol==='B1');assert.deepEqual([g.rank,g.industry_rank,g.industry_size,b1.industry_rank],[1,1,2,2]);
 const cov=B.coverage(u.inputs);assert.deepEqual([cov.q,cov.g,cov.ready],[4,4,false]);assert.equal(cov.label,'초안 · 커버리지 편향 가능 (Q 4/504, G 4/504)');
 const full={records:Object.fromEntries(Array.from({length:460},(_,i)=>['NYSE:F'+i,{qg_axes:{Q:{score:50},G:{score:50}}}]))};assert.equal(B.coverage(full).ready,true);assert.equal(B.coverage(full).label,null);
});

test('sector spread: at most 4 per sub-group, semis + equipment one §16 group',()=>{
 assert.equal(B.subgroupOf('ZZZ','3674','x').subgroup,'semiconductors');assert.equal(B.subgroupOf('ZZZ','3559','x').subgroup,'semi_equipment');assert.equal(B.subgroupOf('ZZZ','7372','x').subgroup,'software_internet');
 assert.equal(B.subgroupOf('NVDA',null,null).subgroup,'semiconductors');assert.equal(B.subgroupOf('ZZZ',null,'retail').subgroup,'industry:retail');
 assert.equal(B.groupOf('semi_equipment'),'semiconductor_combined');assert.equal(B.groupOf('semiconductors'),'semiconductor_combined');
 const list=[];for(let i=0;i<8;i++)list.push({symbol:'SEMI'+i,total:99-i,sic:'3674'});for(let i=0;i<8;i++)list.push({symbol:'EQ'+i,total:89-i,sic:'3559'});for(let i=0;i<30;i++)list.push({symbol:'O'+String(i).padStart(2,'0'),total:70-i*0.1,sic:SICS[3+(i%9)],ig:'g'+(i%9)});
 const u=universe(list),draft=B.buildDraft({...u,existing:[],date:'2026-10-14'}),cands=B.candidates(draft);
 assert.equal(cands.length,30);const per={};for(const r of cands)per[r.subgroup]=(per[r.subgroup]||0)+1;assert.ok(Object.values(per).every(n=>n<=4),JSON.stringify(per));
 assert.deepEqual(cands.slice(0,8).map(r=>r.symbol),['SEMI0','SEMI1','SEMI2','SEMI3','EQ0','EQ1','EQ2','EQ3']);
 const sel=B.currentSelection({...B.emptyState(),draft});const semis=sel.rows.filter(r=>B.groupOf(r.subgroup)==='semiconductor_combined');
 let groupPct=0;for(const r of semis)groupPct+=r.pct;assert.ok(groupPct<=40+1e-9,String(groupPct));assert.ok(sel.skipped.some(s=>s.reason==='SECTOR_GROUP_MAX'));
 assert.ok(sel.skipped.some(s=>s.reason==='SUBGROUP_MAX'));assert.equal(sel.limits.ok,true);
});

test('selection and weights: core 5 × 8% + general 10 × 6% = 100, core needs factors ≥ 80% and safety PASS',()=>{
 const extra=[{symbol:'TOPLOW',total:99,fa:11},{symbol:'TOPMISS',total:98.5,metrics:{net_debt_to_ebitda:null}}];
 const u=wide(40,extra),draft=B.buildDraft({...u,existing:[],date:'2026-10-14'}),sel=B.currentSelection({...B.emptyState(),draft});
 assert.equal(sel.rows.length,15);assert.equal(sel.core_count,5);assert.equal(sel.cash_pct,0);
 const core=sel.rows.filter(r=>r.grade==='CORE'),general=sel.rows.filter(r=>r.grade==='GENERAL');assert.equal(core.length,5);assert.equal(general.length,10);
 assert.ok(core.every(r=>r.pct===8)&&general.every(r=>r.pct===6));let sum=0;for(const r of sel.rows)sum+=r.pct;assert.equal(sum,100);
 // 11/15 factors (< 80%) and an unknown net debt/EBITDA cannot be core; they stay as general names.
 assert.equal(sel.rows.find(r=>r.symbol==='TOPLOW').grade,'GENERAL');assert.equal(sel.rows.find(r=>r.symbol==='TOPMISS').grade,'GENERAL');
 assert.deepEqual(sel.rows.map(r=>r.symbol),[...sel.rows].sort((a,b)=>b.total-a.total).map(r=>r.symbol));assert.equal(sel.limits.ok,true);
 // Fewer qualifying core names → the shortfall stays cash (never filled), limits still checked against 100%.
 const few=universe(Array.from({length:20},(_,i)=>({symbol:'F'+String(i).padStart(2,'0'),total:80-i,sic:SICS[i%SICS.length],ig:'g'+(i%6),fa:i<3?15:10})));
 const s2=B.currentSelection({...B.emptyState(),draft:B.buildDraft({...few,existing:[],date:'2026-10-14'})});assert.equal(s2.core_count,3);assert.equal(s2.rows.length,15);assert.equal(s2.cash_pct,4);assert.equal(s2.limits.ok,true);
 // Set B: equal weight 100/15 with the same spread and caps.
 const seg=B.setBSegment(B.universeRows({...u,existing:[]}).filter(r=>!B.exclusions(r).length),'2026-10-14');assert.equal(seg.rows.length,15);assert.ok(seg.rows.every(r=>Math.abs(r.pct-100/15)<1e-3));assert.equal(seg.limits_ok,true);
});

test('templates: 3 reasons and 3 numerically checkable invalidations from the strongest factors, deterministic',()=>{
 const u=wide(20),draft=B.buildDraft({...u,existing:[],date:'2026-10-14'}),row=draft.pool[0];
 assert.equal(row.reasons.length,3);assert.equal(row.invalidations.length,3);
 // strongest: q_profitability 90 (ROIC 25% × 0.7 = 17.5%), g_revenue_growth 85 (12% − 5%p = 7%), q_moat_proxy 80 (20% × 0.7 = 14%).
 assert.deepEqual(row.invalidations.map(c=>[c.factor,c.metric,c.op,c.threshold]),[['q_profitability','roic','LT',0.175],['g_revenue_growth','revenue_cagr_3y','LT',0.07],['q_moat_proxy','moat_return_mean_5y','LT',0.14]]);
 assert.match(row.invalidations[0].text,/ROIC이\(가\) 17\.5% 아래로 내려가면 \(현재 25\.0%\)/);assert.match(row.reasons[0],/수익성 점수 90\.0 · ROIC 25\.0%/);
 assert.deepEqual(B.buildDraft({...u,existing:[],date:'2026-10-14'}).pool[0],row);
 assert.equal(B.invalidated(row.invalidations[0],0.18),false);assert.equal(B.invalidated(row.invalidations[0],0.17),true);assert.equal(B.invalidated(row.invalidations[0],null),null);
 // Missing metrics are skipped (never 0); the fallback templates fill the rest.
 const bare=universe([{symbol:'BARE',total:80,metrics:{roic:null,gross_profit_to_assets:null,moat_return_mean_5y:null,fcf_to_net_income:null,revenue_cagr_3y:null,eps_cagr_3y:null,incremental_roic_3y:null,revenue_positive_growth_share:null,revenue_ttm_growth:null,interest_coverage:null,net_debt_to_ebitda:null},factors:{q_profitability:90}}]);
 const r2=B.buildDraft({...bare,existing:[],date:'2026-10-14'}).pool[0];assert.deepEqual(r2.invalidations.map(c=>c.metric),['v2_rank','q_industry_percentile','g_axis']);
 assert.match(r2.invalidations[0].text,/30위 밖/);assert.equal(r2.invalidations[1].threshold,30);assert.equal(r2.invalidations[2].threshold,45);
 // Lower-is-better FIXED rule only when the current value is inside the threshold.
 const t=B.templates({factor_scores:{q_financial_safety:95},metrics:{net_debt_to_ebitda:1.2},total:70,rank:3,q_pct:60,g:50});assert.equal(t.invalidations[0].metric,'net_debt_to_ebitda');assert.equal(t.invalidations[0].op,'GTE');assert.equal(t.invalidations[0].threshold,3);
});

test('반대 replaces the name with the next-ranked one, re-checks limits; 모름 keeps it as 미확인; records validate in the playbook store',()=>{
 const u=wide(40),draft=B.buildDraft({...u,existing:[],date:'2026-10-14'});let state={...B.emptyState(),draft};
 const before=B.currentSelection(state),victim=before.rows[0].symbol,sixteenth=draft.pool.filter(r=>!before.rows.some(x=>x.symbol===r.symbol))[0].symbol;
 assert.throws(()=>B.answer(state,{symbol:victim,answer:'DISAGREE',reason:'  ',date:'2026-10-14'}),/DISAGREE_REASON_REQUIRED/);
 assert.throws(()=>B.answer(state,{symbol:victim,answer:'DISAGREE',reason:'line\nbreak',date:'2026-10-14'}),/REASON_INVALID/);
 assert.throws(()=>B.answer(state,{symbol:'NOPE',answer:'AGREE',date:'2026-10-14'}),/TARGET_V1_NOT_SELECTED/);
 state=B.answer(state,{symbol:victim,answer:'DISAGREE',reason:'사업 이해 부족',date:'2026-10-14'});
 const after=B.currentSelection(state);assert.equal(after.rows.length,15);assert.ok(!after.rows.some(r=>r.symbol===victim));assert.ok(after.rows.some(r=>r.symbol===sixteenth));
 assert.deepEqual(after.rejected,[victim]);assert.equal(after.limits.ok,true);let sum=after.cash_pct;for(const r of after.rows)sum+=r.pct;assert.equal(sum,100);
 // The former #2 is promoted to core when the core #1 is rejected (core = first 5 qualifying in total order).
 assert.equal(after.rows.filter(r=>r.grade==='CORE').length,5);
 state=B.answer(state,{symbol:after.rows[1].symbol,answer:'UNKNOWN',date:'2026-10-14'});assert.equal(state.answers.at(-1).reason,'미확인');
 const s=memory(),row=after.rows[1];P.saveRecord(s,B.judgementRecord({row,answer:'UNKNOWN',reason:'미확인',date:'2026-10-14',id:'TV1-1'}));
 const rec=B.judgementRecord({row:draft.pool.find(r=>r.symbol===victim),answer:'DISAGREE',reason:'사업 이해 부족',date:'2026-10-14',id:'TV1-2'});P.saveRecord(s,rec);
 const stored=P.read(s);assert.equal(stored.records.length,2);assert.deepEqual(stored.records.map(r=>[r.primary_code,r.verdict,r.memo]),[['TV1','TV1_UNKNOWN','미확인'],['TV1','TV1_DISAGREE','사업 이해 부족']]);
 assert.equal(stored.records[1].checks.filter(c=>c.code==='INVALIDATION').length,3);
 // The builder state rides in the same store and backup; older stores without it stay valid.
 const v=P.read(s);v.target_v1=state;P.write(s,v);assert.deepEqual(P.read(s).target_v1,JSON.parse(JSON.stringify(state)));
 assert.equal(Object.hasOwn(P.validate(P.empty()),'target_v1'),false);assert.throws(()=>P.validate({...P.empty(),target_v1:{schema:'other'}}),/TARGET_V1_STATE_INVALID/);
 // Re-answering keeps only the latest answer per name (history stays in the records).
 const again=B.answer(state,{symbol:after.rows[1].symbol,answer:'AGREE',date:'2026-10-15'});assert.equal(again.answers.filter(a=>a.symbol===after.rows[1].symbol).length,1);
});

test('finalize: every card answered, limits pass, blocked until number_check_passed; set C starts that day',()=>{
 assert.equal(CFG.number_check_passed,false);assert.equal(CFG.status,'v0');assert.equal(CFG.calibration,'UNCALIBRATED');
 const u=wide(40),draft=B.buildDraft({...u,existing:[],date:'2026-10-14'});let state={...B.emptyState(),draft};
 assert.throws(()=>B.finalize(state,{date:'2026-10-14'}),/TARGET_V1_CARDS_PENDING/);
 for(const r of B.currentSelection(state).rows)state=B.answer(state,{symbol:r.symbol,answer:'AGREE',date:'2026-10-14'});
 assert.equal(B.currentSelection(state).complete,true);assert.throws(()=>B.finalize(state,{date:'2026-10-14'}),/NUMBER_CHECK_NOT_PASSED/);
 const open={...CFG,number_check_passed:true},done=B.finalize(state,{date:'2026-10-15',cfg:open});
 assert.equal(done.versions.length,1);assert.equal(done.versions[0].version,'v1');assert.deepEqual(done.set_c,{start:'2026-10-15',version:'v1'});
 let sum=done.versions[0].cash_pct;for(const r of done.versions[0].rows)sum+=r.pct;assert.equal(sum,100);assert.ok(done.versions[0].rows.every(r=>r.confirmed));
 assert.equal(B.finalize(done,{date:'2026-11-16',cfg:open}).versions[1].version,'v1.1');B.validateState(done);
});

test('rebalance calendar, transition rows (1/3 per round) and set B re-selection days',()=>{
 assert.deepEqual(B.rounds().map(r=>r.date),['2026-11-16','2027-02-15','2027-05-17']);
 assert.equal(B.lastRebalanceOnOrBefore('2026-12-01'),'2026-11-16');assert.equal(B.nextRebalanceOnOrAfter('2026-11-17'),'2027-02-15');
 const state={...B.emptyState(),set_b:[{date:'2026-10-14',rows:[{symbol:'A',pct:50}]}]};
 assert.equal(B.setBDue(B.emptyState(),'2026-10-14'),true);assert.equal(B.setBDue(state,'2026-11-15'),false);assert.equal(B.setBDue(state,'2026-11-16'),true);
 assert.equal(B.setBDue({...state,set_b:[...state.set_b,{date:'2026-11-18',rows:[]}]},'2026-12-01'),false);
 const rows=B.transitionRows({v0:{OLD:9,BOTH:6},v1:{NEW:8,BOTH:9},actual:{BOTH:5.5},total:1000000,round:2});
 const by=Object.fromEntries(rows.map(r=>[r.symbol,r]));assert.equal(by.NEW.step_pp,2.6667);assert.equal(by.NEW.round_target_pct,5.3333);assert.equal(by.OLD.step_pp,-3);assert.equal(by.OLD.round_target_pct,3);
 assert.equal(by.BOTH.current_pct,5.5);assert.equal(by.OLD.current_pct,null);assert.equal(Math.round(by.BOTH.amount),10000);
 assert.equal(B.transitionRows({v0:{X:1},v1:{X:4}})[0].amount,null);
});

test('rule index (no fill) and the round-3 review rule (suggestion only, NA never suggests)',()=>{
 const days=['2026-10-15','2026-10-16','2026-10-19','2026-10-20'],closes={SPY:{},AAA:{},BBB:{}};days.forEach((d,i)=>{closes.SPY[d]=100+i;closes.AAA[d]=10*(1+i/10);closes.BBB[d]=20;});
 const idx=B.ruleIndex({segments:[{date:'2026-10-15',rows:[{symbol:'AAA',pct:50},{symbol:'BBB',pct:50}]}],closes,calendar:Object.keys(closes.SPY),start:'2026-10-15',asOf:'2026-10-20'});
 assert.equal(idx.state,'OK');assert.ok(Math.abs(idx.return-0.15)<1e-12);
 delete closes.BBB['2026-10-20'];const gap=B.ruleIndex({segments:[{date:'2026-10-15',rows:[{symbol:'AAA',pct:50},{symbol:'BBB',pct:50}]}],closes,calendar:Object.keys(closes.SPY),start:'2026-10-15',asOf:'2026-10-20'});
 assert.deepEqual([gap.state,gap.reason,gap.return],['NOT_AVAILABLE','LAST_CLOSE_MISSING',null]);
 const ok=(r)=>({state:'OK',return:r});
 assert.equal(B.reviewRule({compare:{A:ok(0.05),B:ok(0.01),C:ok(0.02),SP500:ok(0.04)},date:'2027-04-01'}).suggest,true);
 assert.equal(B.reviewRule({compare:{A:ok(0.05),B:ok(0.01),C:ok(0.045),SP500:ok(0.04)},date:'2027-04-01'}).suggest,false);
 assert.equal(B.reviewRule({compare:{A:ok(0.05),B:ok(0.06),C:ok(0.02),SP500:ok(0.04)},date:'2027-04-01'}).suggest,false);
 const na=B.reviewRule({compare:{A:ok(0.05),B:{state:'NOT_AVAILABLE',return:null},C:ok(0.02),SP500:ok(0.04)},date:'2027-04-01'});assert.deepEqual([na.state,na.suggest],['NOT_AVAILABLE',false]);
 assert.equal(B.reviewRule({compare:{A:ok(0.05),B:ok(0.01),C:ok(0.02),SP500:ok(0.04)},date:'2027-01-10'}).state,'NOT_DUE');
 assert.equal(B.reviewRule({compare:{A:ok(0.05),B:ok(0.01),C:ok(0.02),SP500:ok(0.04)},date:'2027-05-17'}).state,'NOT_DUE');
 // compareSets: no set C → NA everywhere; with C, A/B/C/SPY over the common window.
 assert.equal(B.compareSets({state:B.emptyState(),closes,asOf:'2026-10-20'}).C.reason,'SET_C_NOT_STARTED');
 closes.BBB['2026-10-20']=20;const st={...B.emptyState(),versions:[{version:'v1',date:'2026-10-15',rows:[{symbol:'AAA',pct:100}],cash_pct:0}],set_c:{start:'2026-10-15',version:'v1'},set_b:[{date:'2026-10-15',rows:[{symbol:'BBB',pct:100}]}]};
 const cmp=B.compareSets({state:st,v0Weights:{AAA:50,BBB:50},closes,asOf:'2026-10-20'});assert.deepEqual(['A','B','C','SP500'].map(k=>cmp[k].state),['OK','OK','OK','OK']);
 assert.ok(Math.abs(cmp.C.return-0.3)<1e-12);assert.equal(cmp.B.return,0);assert.ok(Math.abs(cmp.SP500.return-0.03)<1e-12);
});

test('config: every section carries v0 and a decision state; JS copy loads',()=>{
 for(const k of ['number_check','score_basis','coverage','filters','sector_spread','candidates','selection','templates','cards','rebalance','transition','virtual_sets','review_rule'])assert.ok(CFG[k].version==='v0'&&['UNCALIBRATED','OWNER_RULE'].includes(CFG[k].decision),k);
 assert.equal(CFG.selection.core.count*CFG.selection.core.pct+CFG.selection.general.count*CFG.selection.general.pct,CFG.selection.sum_pct);
 assert.equal(PCFG.portfolio_limits.single_max_pct,10);assert.equal(PCFG.portfolio_limits.sector_group_max_pct,40);
});
