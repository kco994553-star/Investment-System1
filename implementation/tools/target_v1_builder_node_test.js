'use strict';
// TARGET v1 builder (owner decision 2026-10-14): filters, sector cap, selection and weights, template generation, replacement on
// 반대, the §16 limits re-check, finalize gate (number check), rule sets R-B / R-C (규칙 지수, 2026-10-15 T-SET), the holiday rule
// (T-REBAL), the TV1 scoring price path (T-PRICE) and the fixed review rule. Synthetic data only.
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
 // R-B: equal weight 100/15 with the same spread and caps.
 const seg=B.ruleBSegment(B.universeRows({...u,existing:[]}).filter(r=>!B.exclusions(r).length),'2026-10-14');assert.equal(seg.rows.length,15);assert.ok(seg.rows.every(r=>Math.abs(r.pct-100/15)<1e-3));assert.equal(seg.limits_ok,true);assert.equal(seg.ready,true);
 assert.equal(B.ruleBSegment(B.universeRows({...u,existing:[]}).filter(r=>!B.exclusions(r).length).slice(0,20),'2026-10-14').ready,false);
});

test('templates: 3 reasons and 3 numerically checkable invalidations from the strongest factors, deterministic',()=>{
 const u=wide(20),draft=B.buildDraft({...u,existing:[],date:'2026-10-14'}),row=draft.pool[0];
 assert.equal(row.reasons.length,3);assert.equal(row.invalidations.length,3);
 // strongest: q_profitability 90 (ROIC 25% × 0.7 = 17.5%), g_revenue_growth 85 (12% − 5%p = 7%), q_moat_proxy 80 (20% × 0.7 = 14%).
 assert.deepEqual(row.invalidations.map(c=>[c.factor,c.metric,c.op,c.threshold]),[['q_profitability','roic','LT',0.175],['g_revenue_growth','revenue_cagr_3y','LT',0.07],['q_moat_proxy','moat_return_mean_5y','LT',0.14]]);
 assert.match(row.invalidations[0].text,/ROIC가 17\.5% 아래로 내려가면 \(현재 25\.0%\)/);assert.match(row.reasons[0],/수익성 점수 90\.0 · ROIC 25\.0%/);
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

test('finalize: every card answered, limits pass, blocked until number_check_passed; R-C starts that day',()=>{
 assert.equal(CFG.number_check_passed,false);assert.equal(CFG.status,'v0');assert.equal(CFG.calibration,'UNCALIBRATED');
 const u=wide(40),draft=B.buildDraft({...u,existing:[],date:'2026-10-14'});let state={...B.emptyState(),draft};
 assert.throws(()=>B.finalize(state,{date:'2026-10-14'}),/TARGET_V1_CARDS_PENDING/);
 for(const r of B.currentSelection(state).rows)state=B.answer(state,{symbol:r.symbol,answer:'AGREE',date:'2026-10-14'});
 assert.equal(B.currentSelection(state).complete,true);assert.throws(()=>B.finalize(state,{date:'2026-10-14'}),/NUMBER_CHECK_NOT_PASSED/);
 const open={...CFG,number_check_passed:true},done=B.finalize(state,{date:'2026-10-15',cfg:open});
 assert.equal(done.versions.length,1);assert.equal(done.versions[0].version,'v1');assert.deepEqual(done.rule_c,{start:'2026-10-15',version:'v1'});
 let sum=done.versions[0].cash_pct;for(const r of done.versions[0].rows)sum+=r.pct;assert.equal(sum,100);assert.ok(done.versions[0].rows.every(r=>r.confirmed));
 assert.equal(B.finalize(done,{date:'2026-11-16',cfg:open}).versions[1].version,'v1.1');B.validateState(done);
});

test('rebalance calendar, transition rows (1/3 per round) and R-B re-selection days',()=>{
 assert.deepEqual(B.rounds().map(r=>r.date),['2026-11-16','2027-02-15','2027-05-17']);
 assert.equal(B.lastRebalanceOnOrBefore('2026-12-01'),'2026-11-16');assert.equal(B.nextRebalanceOnOrAfter('2026-11-17'),'2027-02-15');
 const state={...B.emptyState(),rule_b:[{date:'2026-10-14',rows:[{symbol:'A',pct:50}]}]};
 assert.equal(B.ruleBDue(B.emptyState(),'2026-10-14'),true);assert.equal(B.ruleBDue(state,'2026-11-15'),false);assert.equal(B.ruleBDue(state,'2026-11-16'),true);
 assert.equal(B.ruleBDue({...state,rule_b:[...state.rule_b,{date:'2026-11-18',rows:[]}]},'2026-12-01'),false);
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
 assert.equal(B.reviewRule({compare:{A:ok(0.05),'R-B':ok(0.01),'R-C':ok(0.02),SP500:ok(0.04)},date:'2027-04-01'}).suggest,true);
 assert.equal(B.reviewRule({compare:{A:ok(0.05),'R-B':ok(0.01),'R-C':ok(0.045),SP500:ok(0.04)},date:'2027-04-01'}).suggest,false);
 assert.equal(B.reviewRule({compare:{A:ok(0.05),'R-B':ok(0.06),'R-C':ok(0.02),SP500:ok(0.04)},date:'2027-04-01'}).suggest,false);
 const na=B.reviewRule({compare:{A:ok(0.05),'R-B':{state:'NOT_AVAILABLE',return:null},'R-C':ok(0.02),SP500:ok(0.04)},date:'2027-04-01'});assert.deepEqual([na.state,na.suggest],['NOT_AVAILABLE',false]);
 assert.equal(B.reviewRule({compare:{A:ok(0.05),'R-B':ok(0.01),'R-C':ok(0.02),SP500:ok(0.04)},date:'2027-01-10'}).state,'NOT_DUE');
 assert.equal(B.reviewRule({compare:{A:ok(0.05),'R-B':ok(0.01),'R-C':ok(0.02),SP500:ok(0.04)},date:'2027-05-17'}).state,'NOT_DUE');
 // compareSets: no R-C → NA everywhere; with R-C, A/R-B/R-C/SPY over the common window (keys are the R-B / R-C ids).
 assert.deepEqual(B.COMPARE_KEYS,['A','R-B','R-C','SP500']);assert.equal(B.compareSets({state:B.emptyState(),closes,asOf:'2026-10-20'})['R-C'].reason,'R_C_NOT_STARTED');
 closes.BBB['2026-10-20']=20;const st={...B.emptyState(),versions:[{version:'v1',date:'2026-10-15',rows:[{symbol:'AAA',pct:100}],cash_pct:0}],rule_c:{start:'2026-10-15',version:'v1'},rule_b:[{date:'2026-10-15',rows:[{symbol:'BBB',pct:100}]}]};
 const cmp=B.compareSets({state:st,v0Weights:{AAA:50,BBB:50},closes,asOf:'2026-10-20'});assert.deepEqual(B.COMPARE_KEYS.map(k=>cmp[k].state),['OK','OK','OK','OK']);
 assert.equal(Object.hasOwn(cmp,'B')||Object.hasOwn(cmp,'C'),false);
 assert.ok(Math.abs(cmp['R-C'].return-0.3)<1e-12);assert.equal(cmp['R-B'].return,0);assert.ok(Math.abs(cmp.SP500.return-0.03)<1e-12);
 assert.equal(B.compareSets({state:{...st,rule_b:[]},v0Weights:{AAA:50},closes,asOf:'2026-10-20'})['R-B'].reason,'R_B_NOT_STARTED');
});

test('config: every section carries v0 and a decision state; JS copy loads',()=>{
 for(const k of ['number_check','score_basis','coverage','filters','sector_spread','candidates','selection','templates','cards','rebalance','transition','virtual_sets','review_rule'])assert.ok(CFG[k].version==='v0'&&['UNCALIBRATED','OWNER_RULE','USER_DECISION_2026-10-15'].includes(CFG[k].decision),k);
 assert.equal(CFG.selection.core.count*CFG.selection.core.pct+CFG.selection.general.count*CFG.selection.general.pct,CFG.selection.sum_pct);
 assert.equal(PCFG.portfolio_limits.single_max_pct,10);assert.equal(PCFG.portfolio_limits.sector_group_max_pct,40);
});

test('2026-10-15 decisions: T-COV 0.9 Q and G, T-REBAL decided, R-B / R-C ids with 규칙 지수, sheet sets B/C/D untouched',()=>{
 for(const k of ['coverage','rebalance','scoring_prices'])assert.equal(CFG[k].decision,'USER_DECISION_2026-10-15',k);
 assert.equal(CFG.coverage.ready_min_ratio,0.9);assert.match(CFG.coverage.decided,/^2026-10-15 .*T-COV/);assert.match(CFG.rebalance.decided,/^2026-10-15 .*T-REBAL/);
 // 0.9 on both axes: 454/504 ≥ 0.9 is ready; 453/504 on either axis keeps the draft label.
 const recs=(q,g)=>({records:Object.fromEntries(Array.from({length:504},(_,i)=>['NYSE:F'+i,{qg_axes:{Q:{score:i<q?50:null},G:{score:i<g?50:null}}}]))});
 assert.equal(B.coverage(recs(454,454)).ready,true);assert.equal(B.coverage(recs(453,504)).ready,false);assert.equal(B.coverage(recs(504,453)).ready,false);
 assert.match(B.coverage(recs(453,504)).label,/^초안 · 커버리지 편향 가능 \(Q 453\/504, G 504\/504\)$/);
 assert.deepEqual(CFG.virtual_sets.rule_ids,['R-B','R-C']);for(const id of ['R-B','R-C']){assert.equal(CFG.virtual_sets[id].id,id);assert.equal(CFG.virtual_sets[id].source_ko,'규칙 지수');assert.ok(CFG.virtual_sets[id].ko.startsWith(id+' · '));}
 assert.equal(Object.hasOwn(CFG.virtual_sets,'B')||Object.hasOwn(CFG.virtual_sets,'C'),false);assert.equal(CFG.virtual_sets.A.ko,'세트 A · TARGET v0');
 assert.equal(CFG.review_rule.condition,'R_B_AND_R_C_BELOW_A_AND_SP500');assert.match(CFG.review_rule.text,/^R-B와 R-C\(규칙 지수\)가/);
 // The sheet ledger's user sets keep their names.
 const L=require(W+'virtual-ledger-sheets.js');assert.deepEqual(L.USER_SETS,['SET_B','SET_C','SET_D']);assert.deepEqual([L.TABS.SET_B,L.TABS.SET_C,L.TABS.SET_D],['VirtualB','VirtualC','VirtualD']);
});

test('T-REBAL: Monday of days 15–21; a holiday Monday resets the rule index on the next session',()=>{
 assert.equal(CFG.rebalance.holiday_rule,'NEXT_SESSION');assert.deepEqual(CFG.rebalance.months,[2,5,8,11]);
 for(const[y,m,d]of [[2026,11,'2026-11-16'],[2027,2,'2027-02-15'],[2027,5,'2027-05-17'],[2027,8,'2027-08-16'],[2027,11,'2027-11-15'],[2028,2,'2028-02-21']]){assert.equal(B.rebalanceDay(y,m),d);assert.equal(new Date(d+'T00:00:00Z').getUTCDay(),1);}
 // 2027-02-15 is a US market holiday: the calendar skips it, so the reset uses the 2027-02-16 close (never a carried value).
 const cal=['2027-02-11','2027-02-12','2027-02-16','2027-02-17'],closes={SPY:{},UP:{},FLAT:{}};cal.forEach((d,i)=>{closes.SPY[d]=100;closes.UP[d]=[10,10,20,20][i];closes.FLAT[d]=10;});
 const seg=[{date:'2027-02-11',rows:[{symbol:'UP',pct:50},{symbol:'FLAT',pct:50}]}];
 const idx=B.ruleIndex({segments:seg,closes,calendar:cal,start:'2027-02-11',asOf:'2027-02-17',resetDays:B.rebalanceDays('2027-02-11','2027-02-17')});
 assert.deepEqual(B.rebalanceDays('2027-02-11','2027-02-17'),['2027-02-15']);assert.equal(idx.state,'OK');assert.ok(Math.abs(idx.return-0.5)<1e-12);
 // Without the reset the same path also gives +50% here; a reset-day close missing → NA (no fill).
 delete closes.FLAT['2027-02-16'];const gap=B.ruleIndex({segments:seg,closes,calendar:cal,start:'2027-02-11',asOf:'2027-02-17',resetDays:['2027-02-15']});
 assert.deepEqual([gap.state,gap.reason,gap.date],['NOT_AVAILABLE','REBALANCE_CLOSE_MISSING','2027-02-16']);
 // R-B is re-selected once the calendar Monday has passed (holiday or not).
 const st={...B.emptyState(),rule_b:[{date:'2026-11-16',rows:[]}]};assert.equal(B.ruleBDue(st,'2027-02-14'),false);assert.equal(B.ruleBDue(st,'2027-02-15'),true);assert.equal(B.ruleBDue(st,'2027-02-16'),true);
});

test('state: R-B / R-C keys, legacy #248 layout read as R-B / R-C, price_symbols are symbols only',()=>{
 const e=B.emptyState();assert.deepEqual(Object.keys(e).sort(),['answers','draft','price_symbols','rule_b','rule_c','schema','versions']);
 const legacy={schema:B.SCHEMA,draft:null,answers:[],versions:[{version:'v1',date:'2026-10-15',rows:[{symbol:'AAA',pct:100}],cash_pct:0}],set_b:[{date:'2026-10-14',rows:[{symbol:'BBB',pct:100}]}],set_c:{start:'2026-10-15',version:'v1'}};
 const v=B.validateState(legacy);assert.deepEqual(v.rule_b,legacy.set_b);assert.deepEqual(v.rule_c,legacy.set_c);assert.deepEqual(v.price_symbols,[]);assert.equal(Object.hasOwn(v,'set_b'),false);
 // A playbook store holding the legacy layout still reads (older device records stay valid).
 const s=memory(),pb=P.empty();pb.target_v1=legacy;s.setItem(P.KEY,JSON.stringify(pb));assert.equal(P.read(s).target_v1.schema,B.SCHEMA);
 assert.throws(()=>B.validateState({...e,set_b:[]}),/TARGET_V1_STATE_INVALID/);assert.throws(()=>B.validateState({...e,price_symbols:['abc']}),/TARGET_V1_STATE_INVALID/);
 assert.throws(()=>B.validateState({...e,price_symbols:['AAA','AAA']}),/TARGET_V1_STATE_INVALID/);assert.throws(()=>B.validateState({...e,price_symbols:[12.5]}),/TARGET_V1_STATE_INVALID/);
 assert.throws(()=>B.validateState({...e,price_symbols:Array.from({length:CFG.scoring_prices.max_symbols+1},(_,i)=>'S'+i)}),/TARGET_V1_STATE_INVALID/);
 const ok={...e,price_symbols:['BRK-B','XLF','SPY']};assert.deepEqual(B.validateState(ok),ok);const pb2=P.empty();pb2.target_v1=ok;P.write(s,pb2);assert.deepEqual(P.read(s).target_v1.price_symbols,['BRK-B','XLF','SPY']);
});

test('T-PRICE: TV1 names outside the 19 get a sheet price path; scoring reads it like the runner series, missing stays NA',()=>{
 const rec=(symbol,verdict='TV1_DISAGREE',date='2026-10-15',code='TV1')=>({id:symbol+date+verdict,date,symbol,primary_code:code,secondary_codes:[],type:'CANDIDATE',sector:null,thresholds:{},checks:[],ai_summary:'',verdict,action:{kind:'TARGET_V1_EXCLUDE'},next_check_date:null,memo:'x'});
 const records=[rec('NVDA','TV1_AGREE'),rec('BRK.B'),rec('ABBV'),rec('ABBV','TV1_UNKNOWN'),rec('KO','','2026-10-15'),rec('MMM','CONVICTION_KEEP','2026-10-15','H1')];
 const sics={'BRK.B':'6331',ABBV:'2834'};
 const needs=B.scoringNeeds(records,{have:['NVDA','ASML'],sicOf:s=>sics[s]??null});
 assert.deepEqual(needs.map(n=>[n.symbol,n.price_symbol]),[['BRK.B','BRK-B'],['ABBV','ABBV']]);
 assert.equal(needs[1].sector_symbol,'XLV');assert.ok(/^[A-Z]{2,4}$/.test(needs[0].sector_symbol));
 assert.equal(B.sectorEtfOf(null),'SPY');
 // Added names are no longer pending; the add merges names, their sector ETFs and SPY (symbols only, deduped, bounded).
 const st=B.addPriceSymbols(B.emptyState(),needs);assert.deepEqual(st.price_symbols,['BRK-B',needs[0].sector_symbol,'SPY','ABBV','XLV'].filter((x,i,a)=>a.indexOf(x)===i));B.validateState(st);
 assert.deepEqual(B.scoringNeeds(records,{have:['NVDA'],added:st.price_symbols,sicOf:s=>sics[s]??null}),[]);
 assert.throws(()=>B.addPriceSymbols({...st,price_symbols:Array.from({length:CFG.scoring_prices.max_symbols},(_,i)=>'S'+i)},needs),/PRICE_SYMBOLS_MAX/);
 // Series from RAM closes: sessions = SPY dates; any of name / sector / SPY absent → null (record stays NA).
 const days=[];for(let d=new Date('2026-10-01T00:00:00Z');days.length<40;d.setUTCDate(d.getUTCDate()+1))if(d.getUTCDay()%6)days.push(d.toISOString().slice(0,10));
 const series=(f)=>Object.fromEntries(days.map((d,i)=>[d,f(i)]));
 const closes={SPY:series(i=>100+i),XLV:series(()=>50),ABBV:series(i=>200+2*i)};
 assert.equal(B.scoringSeries(needs[1],{SPY:closes.SPY,ABBV:closes.ABBV}),null);assert.equal(B.scoringSeries(needs[1],{XLV:closes.XLV,ABBV:closes.ABBV}),null);assert.equal(B.scoringSeries(needs[1],{SPY:closes.SPY,XLV:closes.XLV}),null);
 const data=B.scoringSeries(needs[1],closes);assert.deepEqual(data.sessions,days);assert.equal(data.sector_symbol,'XLV');
 const r=rec('ABBV'),score=P.scoreRecord(r,data,20);assert.equal(score.state,'OK');assert.equal(score.base_date,'2026-10-15');
 const base=days.indexOf('2026-10-15');assert.ok(Math.abs(score.stock-((200+2*(base+20))/(200+2*base)-1))<1e-12);assert.equal(score.sector,0);
 // A missing close on the window end → NA (never 0).
 const holed={...closes,ABBV:{...closes.ABBV}};delete holed.ABBV[days[base+20]];const na=P.scoreRecord(r,B.scoringSeries(needs[1],holed),20);
 assert.deepEqual([na.state,na.reason],['NOT_AVAILABLE','PRICE_OR_BENCHMARK_MISSING']);assert.equal(P.scoreRecord(r,undefined,20).reason,'DEVICE_HISTORY_UNAVAILABLE');
 // PlaybookScreen keeps the added series in RAM; the runner's own series for the same symbol wins; the table shows NA, never 0.
 P.addScoringSeries({ABBV:data,'bad symbol':data,XLV:{sessions:'x'}});const merged=P.scoringSeries({NVDA:{sessions:[]}});assert.ok(merged.ABBV&&merged.NVDA);assert.equal(Object.hasOwn(merged,'XLV'),false);assert.equal(Object.hasOwn(merged,'bad symbol'),false);
 assert.equal(P.scoringSeries({ABBV:{sessions:[]}}).ABBV.sessions.length,0);
 const html=P.scoringHtml([r,rec('BRK.B')],P.scoringSeries({}));assert.match(html,/ABBV 2026-10-15 · TARGET v1 반대/);assert.match(html,/BRK\.B 2026-10-15 · TARGET v1 반대<\/td><td>D\+20<\/td><td>NA · DEVICE_HISTORY_UNAVAILABLE/);assert.ok([...html.matchAll(/<tr><td>BRK\.B[^]*?<\/tr>/g)].every(m=>!/\d%/.test(m[0])&&(m[0].match(/>NA</g)||[]).length===2));
});

test('T-PRICE screen helpers: confirm text names the sheet and the symbols; no write without the confirm',async()=>{
 const S=require(W+'target-v1-screen.js');const text=S.confirmText([{symbol:'ABBV',price_symbol:'ABBV',sector_symbol:'XLV'}],CFG);
 assert.match(text,/내 비공개 구글 시트의 Prices_D 탭에 덧붙입니다:\nABBV · XLV · SPY/);assert.match(text,/공개 파일·로그·저장소에는 남지 않습니다/);assert.match(text,/0으로 채우지 않음/);assert.match(text,/추가할까요\?$/);
 assert.ok(!/매수|매도|\bbuy\b|\bsell\b|order/i.test(text));
 const s=memory();assert.deepEqual(S.priceSymbols(P,s),[]);const pb=P.empty();pb.target_v1={...B.emptyState(),price_symbols:['ABBV','XLV','SPY']};P.write(s,pb);assert.deepEqual(S.priceSymbols(P,s),['ABBV','XLV','SPY']);
});
