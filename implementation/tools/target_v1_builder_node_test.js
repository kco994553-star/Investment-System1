'use strict';
// TARGET v1 builder (owner decision 2026-10-14): filters, sector cap, selection and weights, template generation, replacement on
// 반대, the §16 limits re-check, finalize gate (number check), rule sets R-B / R-C (규칙 지수, 2026-10-15 T-SET), the holiday rule
// (T-REBAL), the TV1 scoring price path (T-PRICE) and the fixed review rule. Synthetic data only.
const test=require('node:test'),assert=require('node:assert/strict');
const W='../src/investment_system/product/web_assets/';
const B=require(W+'target-v1-builder.js'),CFG=require(W+'target-v1-config-defaults.js'),PCFG=require(W+'playbook-config-defaults.js'),P=require(W+'playbook-screen.js');
const memory=()=>{const m=new Map();return{getItem:k=>m.get(k)??null,setItem:(k,v)=>m.set(k,String(v)),removeItem:k=>m.delete(k)};};
const FACTORS={q_profitability:90,q_moat_proxy:80,q_earnings_quality:70,q_financial_safety:60,q_capital_allocation:50,g_revenue_growth:85,g_per_share_growth:40,g_growth_efficiency:30,g_consistency:20,g_recent_acceleration:10,
 // Synthetic V factor scores (V1..V5 all present; 2026-10-23 V count): below the top three so the templates are unchanged.
 v_earnings_yield:45,v_fcf_yield:44,v_vs_industry:43,v_vs_own_history:42,v_expectation_check:41};
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

test('filters: axis coverage, value-trap gate, financial safety fail and financial safety NA (excluded, 2026-10-15)',()=>{
 assert.equal(B.safety({net_debt_to_ebitda:3,interest_coverage:10}).state,'FAIL');
 assert.equal(B.safety({net_debt_to_ebitda:2.9,interest_coverage:2.99}).state,'FAIL');
 assert.equal(B.safety({net_debt_to_ebitda:2.9,interest_coverage:3}).state,'PASS');
 assert.equal(B.safety({interest_coverage:20}).state,'UNKNOWN');assert.equal(B.safety({}).state,'UNKNOWN');
 const u=universe([{symbol:'OK',total:80},{symbol:'AXIS',total:79,q:null},{symbol:'THIN',total:78,qw:0.4},{symbol:'TRAP',total:77,trap:true},{symbol:'DEBT',total:76,metrics:{net_debt_to_ebitda:3.5}},
  {symbol:'COVER',total:75,metrics:{interest_coverage:2}},{symbol:'MISS',total:74,metrics:{net_debt_to_ebitda:null,interest_coverage:null}},{symbol:'NOV',total:73,v:null}]);
 const rows=B.universeRows({...u,existing:['OK']}),why=Object.fromEntries(rows.map(r=>[r.symbol,B.exclusions(r)]));
 assert.deepEqual(why,{OK:[],AXIS:['AXIS_COVERAGE_LOW'],THIN:['AXIS_COVERAGE_LOW'],TRAP:['VALUE_TRAP_GATE'],DEBT:['FINANCIAL_SAFETY_FAIL'],COVER:['FINANCIAL_SAFETY_FAIL'],MISS:['FINANCIAL_SAFETY_NOT_AVAILABLE'],NOV:['AXIS_COVERAGE_LOW']});
 assert.equal(rows.find(r=>r.symbol==='MISS').safety.state,'UNKNOWN');assert.equal(rows.find(r=>r.symbol==='OK').in19,true);
 const draft=B.buildDraft({...u,existing:[],date:'2026-10-14'});
 assert.deepEqual(draft.pool.map(r=>r.symbol),['OK']);assert.deepEqual(draft.excluded_counts,{AXIS_COVERAGE_LOW:3,VALUE_TRAP_GATE:1,FINANCIAL_SAFETY_FAIL:2,FINANCIAL_SAFETY_NOT_AVAILABLE:1});
 assert.deepEqual(draft.excluded.find(r=>r.symbol==='MISS'),{symbol:'MISS',total:74,reasons:['FINANCIAL_SAFETY_NOT_AVAILABLE'],safety:'UNKNOWN'});
 // One value missing is NA too (excluded); when the data appears the next build re-evaluates it (nothing is frozen per name).
 const half=universe([{symbol:'HALF',total:80,metrics:{interest_coverage:null}}]);assert.deepEqual(B.exclusions(B.universeRows({...half,existing:[]})[0]),['FINANCIAL_SAFETY_NOT_AVAILABLE']);
 const later=universe([{symbol:'HALF',total:80}]);assert.deepEqual(B.exclusions(B.universeRows({...later,existing:[]})[0]),[]);
 assert.throws(()=>B.buildDraft({...u,computed:{...u.computed,v2_state:'NOT_AVAILABLE'},existing:[],date:'2026-10-14'}),/QGV2_NOT_READY/);
});

test('normal NA row (no value, NA reason): no rank, not a candidate, Q·G denominator stays 504 (2026-10-15 evening)',()=>{
 const u=universe([{symbol:'A1',total:80},{symbol:'NA0',total:null,q:null,v:null},{symbol:'A2',total:70}]);
 const v2=Object.values(u.computed.rows).find(r=>r.ticker==='NA0').v2;v2.g=null;v2.axes.G={score:null,weight_available:0,state:'NOT_AVAILABLE'};
 const rec=u.inputs.records['NASDAQ:NA0'];rec.qg_axes={Q:{score:null},G:{score:null}};rec.reason_codes=['NOT_COLLECTED'];rec.metrics={};
 const rows=B.universeRows({...u,existing:[]}),na=rows.find(r=>r.symbol==='NA0');
 assert.deepEqual([na.total,na.rank,na.industry_rank],[null,null,null]);
 assert.deepEqual(rows.filter(r=>r!==na).map(r=>[r.symbol,r.rank]),[['A1',1],['A2',2]],'the NA row takes no rank');
 assert.ok(B.exclusions(na).includes('TOTAL_NOT_AVAILABLE'));
 const draft=B.buildDraft({...u,existing:[],date:'2026-10-14'});
 assert.deepEqual(draft.pool.map(r=>r.symbol),['A1','A2']);assert.deepEqual(B.candidates(draft).map(r=>r.symbol),['A1','A2']);
 assert.equal(draft.excluded_counts.TOTAL_NOT_AVAILABLE,1);
 assert.deepEqual([draft.coverage.q,draft.coverage.g,draft.coverage.size],[2,2,504],'NA stays in the 504 denominator');
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
 // 11/15 factors (< 80%) cannot be core (stays general); an unknown net debt/EBITDA is not a candidate at all (2026-10-15).
 assert.equal(sel.rows.find(r=>r.symbol==='TOPLOW').grade,'GENERAL');assert.equal(sel.rows.some(r=>r.symbol==='TOPMISS'),false);assert.equal(draft.pool.some(r=>r.symbol==='TOPMISS'),false);assert.equal(sel.shortfall,0);
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
 const bare=universe([{symbol:'BARE',total:80,metrics:{roic:null,gross_profit_to_assets:null,moat_return_mean_5y:null,fcf_to_net_income:null,revenue_cagr_3y:null,eps_cagr_3y:null,incremental_roic_3y:null,revenue_positive_growth_share:null,revenue_ttm_growth:null,interest_coverage:12,net_debt_to_ebitda:1},factors:{q_profitability:90}}]);
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

// A published sec-qgv2.json payload in the raw shape (records[code]: cik, state, reason_codes, acquired_at, axes, metrics,
// calc_version), 504 US rows: the given universe's codes first (their metrics, for the financial-safety re-check), then fillers.
const ACQ='2026-10-13T20:00:00Z';
function published({calc='qgv2-calc/2026-10-15.1',records=calc,asOf='2026-10-14T21:00:00Z',q=504,g=504,u=null,acquired=ACQ,patch={}}={}){
 const out={kind:'SEC_QGV2',as_of:asOf,shard_count:7,records:{},target:{x:{axes:{Q:{score:1}}}}};if(calc!==null)out.calc_version=calc;
 const src=u?.inputs?.records||{},codes=Object.keys(src);for(let i=codes.length;i<504;i++)codes.push('NYSE:P'+i);
 codes.forEach((code,i)=>{const r={cik:src[code]?.cik||('P'+i),state:'LIVE',reason_codes:[],acquired_at:acquired,axes:{Q:{score:i<q?50:null},G:{score:i<g?50:null}},metrics:src[code]?{...src[code].metrics}:{}};if(records!==null)r.calc_version=records;out.records[code]=r;});
 for(const[code,f]of Object.entries(patch))f(out.records[code]);return out;}
const notPassed={...CFG,number_check:{...CFG.number_check,result:{calc_version:null,passed:false,date:null,companies:0}}};
const passed=(calc='qgv2-calc/2026-10-15.1',extra={})=>({...CFG,number_check:{...CFG.number_check,result:{calc_version:calc,passed:true,date:'2026-10-15',companies:10,...extra}}});
// finalize with the basis of the payload computed the way the screen does; → the new state, or the error's blockers.
async function tryFinalize(state,{date='2026-10-15',pub=null,cfg=passed()}={}){const basis=pub?await B.inputBasis(pub):null;try{return B.finalize(state,{date,published:pub,basis,cfg});}catch(e){if(!e.blockers)throw e;return e.blockers;}}
const NA_ROW=r=>{r.state='NOT_AVAILABLE';r.reason_codes=['NOT_COLLECTED'];r.acquired_at=null;r.axes={Q:{score:null},G:{score:null}};r.metrics={};delete r.calc_version;};

test('production calc_version: published check and input basis retain the exact production version',async()=>{
 // Current public artifact plus the production contract's 1–4 digit revision boundary.
 for(const calc of ['qgv2-calc/2026-10-17.1','qgv2-calc/2026-10-17.12','qgv2-calc/2026-10-17.123','qgv2-calc/2026-10-17.1234']){
  const pub=published({calc}),check=B.publishedCheck(pub,{date:'2026-10-15'});
  assert.equal(check.calc_version,calc);assert.deepEqual(check.reasons,[]);assert.equal(check.ok,true);
  assert.equal((await B.inputBasis(pub)).calc_version,calc);
 }
});

test('production calc_version: malformed or missing versions stay blocked, not broadly slash-allowed',async()=>{
 for(const calc of [undefined,null,17,'','calc-2026-10-15','cv-test','other/2026-10-17.1','qgv2-calc/2026-1-17.1',
  'qgv2-calc/2026-10-7.1','qgv2-calc/26-10-17.1','qgv2-calc/2026-10-17','qgv2-calc/2026-10-17.',
  'qgv2-calc/2026-10-17.12345','qgv2-calc/2026-10-17.x','qgv2-calc/2026-10-17.1/extra',' qgv2-calc/2026-10-17.1','qgv2-calc/2026-10-17.1 ']){
  const pub=published();if(calc===undefined)delete pub.calc_version;else pub.calc_version=calc;
  const check=B.publishedCheck(pub,{date:'2026-10-15'});
  assert.equal(check.calc_version,null,String(calc));assert.deepEqual(check.reasons,['CALC_VERSION_MISSING'],String(calc));assert.equal(check.ok,false);
  assert.equal((await B.inputBasis(pub)).calc_version,null,String(calc));
 }
});

test('production calc_version: valid mixed rows and another number-check version remain blocked',()=>{
 const calc='qgv2-calc/2026-10-17.1',other='qgv2-calc/2026-10-17.2',pub=published({calc});
 assert.deepEqual(B.publishedCheck(pub,{date:'2026-10-15'}).reasons,[]);
 pub.records['NYSE:P0'].calc_version=other;
 const mixed=B.publishedCheck(pub,{date:'2026-10-15'});assert.equal(mixed.mixed_rows,1);assert.deepEqual(mixed.reasons,['CALC_VERSION_MIXED']);
 // Recorded 2026-10-23 (app formula check, test prices) for qgv2-calc/2026-10-17.1 only: another calc_version is a mismatch.
 assert.deepEqual(CFG.number_check.result,{calc_version:'qgv2-calc/2026-10-17.1',passed:true,date:'2026-10-23',companies:10});assert.equal(B.numberCheck(calc).ok,true);assert.equal(B.numberCheck(other).reason,'NUMBER_CHECK_CALC_VERSION_MISMATCH');assert.equal(B.numberCheck(null).reason,'NUMBER_CHECK_CALC_VERSION_MISMATCH');
 assert.equal(B.numberCheck(calc,notPassed).reason,'NUMBER_CHECK_NOT_PASSED');
 assert.equal(B.numberCheck(calc,passed(other)).reason,'NUMBER_CHECK_CALC_VERSION_MISMATCH');
 assert.equal(B.numberCheck(calc,passed(calc)).ok,true);
});

test('finalize: a listing-ended NA row (CIK_UNRESOLVED, last acquired_at kept, no calc_version) is a normal NA, never stale (2026-10-25 B-a)',()=>{
 // sec_universe_shares.LISTING_ENDED_CODES (NASDAQ:WBD): the row keeps its last acquired_at (freshness guard: EQUAL, never
 // LOST_RECORD) but has no value, so publishedCheck counts it as a normal NA; the same old row while still valued blocks.
 const u=wide(40),old='2026-10-01T03:15:35Z',ended=r=>{NA_ROW(r);r.reason_codes=['CIK_UNRESOLVED'];r.acquired_at=old;};
 const chk=B.publishedCheck(published({u,patch:{'NYSE:P500':ended}}),{date:'2026-10-15'});
 assert.deepEqual([chk.ok,chk.reasons,chk.na_rows,chk.stale_rows,chk.mixed_rows,chk.q,chk.g,chk.oldest_acquired],[true,[],1,0,0,503,503,ACQ]);
 const kept=B.publishedCheck(published({u,patch:{'NYSE:P500':r=>{r.acquired_at=old;}}}),{date:'2026-10-15'});
 assert.deepEqual([kept.ok,kept.reasons,kept.na_rows,kept.stale_rows,kept.oldest_acquired],[false,['ROW_DATA_STALE'],0,1,old]);
});

test('finalize: cards, shortfall, limits, LATEST file (calc_version, row freshness 7 days, Q·G 90%), draft basis, safety re-check, number check',async()=>{
 assert.equal(Object.hasOwn(CFG,'number_check_passed'),false);assert.deepEqual(CFG.number_check.result,{calc_version:'qgv2-calc/2026-10-17.1',passed:true,date:'2026-10-23',companies:10});assert.equal(CFG.number_check.companies_required,10);
 assert.equal(CFG.status,'v0');assert.equal(CFG.calibration,'UNCALIBRATED');assert.equal(CFG.finalize_check.freshness_max_days,7);assert.equal(CFG.finalize_check.freshness_basis,'ROW_ACQUIRED_AT');
 const u=wide(40),pub=published({u}),basis=await B.inputBasis(pub);assert.equal(basis.calc_version,'qgv2-calc/2026-10-15.1');assert.equal(basis.shard_count,7);assert.match(basis.shards,/^(\d=2026-10-13T20:00:00Z\|?)+$/);
 const draft=B.buildDraft({...u,existing:[],date:'2026-10-14',basis});assert.deepEqual(draft.basis,basis);let state={...B.emptyState(),draft};B.validateState(state);
 assert.equal((await tryFinalize(state,{pub}))[0],'TARGET_V1_CARDS_PENDING');
 for(const r of B.currentSelection(state).rows)state=B.answer(state,{symbol:r.symbol,answer:'AGREE',date:'2026-10-14'});assert.equal(B.currentSelection(state).complete,true);
 // Nothing re-read → blocked; the draft-time pass is never reused.
 assert.ok((await tryFinalize(state)).includes('SEC_QGV2_NOT_AVAILABLE'));
 // (a) calc_version: legacy file; valued rows without / with another calc_version → CALC_VERSION_MIXED.
 assert.deepEqual(await tryFinalize(state,{pub:published({u,calc:null,records:null})}),['CALC_VERSION_MISSING','DRAFT_BASIS_CHANGED','NUMBER_CHECK_CALC_VERSION_MISMATCH']);
 assert.deepEqual(await tryFinalize(state,{pub:published({u,records:null})}),['CALC_VERSION_MIXED']);
 assert.deepEqual(await tryFinalize(state,{pub:published({u,records:'qgv2-calc/2026-10-14.1'})}),['CALC_VERSION_MIXED']);
 // Normal NA vs version mixing: 1 normal-NA row (no value, NA reason, no calc_version) + the rest current → allowed;
 // the same row carrying the current calc_version is also normal; 1 valued old-calculation row → CALC_VERSION_MIXED.
 const okNa=published({u,patch:{'NYSE:P500':NA_ROW}}),chkNa=B.publishedCheck(okNa,{date:'2026-10-15'});assert.deepEqual([chkNa.ok,chkNa.na_rows,chkNa.q,chkNa.size],[true,1,503,504]);
 assert.equal((await tryFinalize(state,{pub:published({u,patch:{'NYSE:P500':r=>{NA_ROW(r);r.calc_version='qgv2-calc/2026-10-15.1';}}})})).versions.length,1);
 const doneNa=await tryFinalize(state,{pub:okNa});assert.equal(doneNa.versions.length,1,JSON.stringify(doneNa));
 assert.deepEqual(await tryFinalize(state,{pub:published({u,patch:{'NYSE:P500':r=>{r.calc_version='qgv2-calc/2026-10-14.1';}}})}),['CALC_VERSION_MIXED']);
 assert.deepEqual(await tryFinalize(state,{pub:published({u,patch:{'NYSE:P500':r=>{NA_ROW(r);r.calc_version='qgv2-calc/2026-10-14.1';}}})}),['CALC_VERSION_MIXED']);
 assert.deepEqual(await tryFinalize(state,{pub:published({u,patch:{'NYSE:P500':r=>{NA_ROW(r);r.reason_codes=[];}}})}),['CALC_VERSION_MIXED']);
 // (b) freshness per valued row's acquired_at (7 days from the finalize date), never the file as_of.
 assert.equal(B.publishedCheck(pub,{date:'2026-10-19'}).ok,true);assert.deepEqual(B.publishedCheck(pub,{date:'2026-10-20'}).reasons,['ROW_DATA_STALE']);
 const regenerated=published({u,asOf:'2026-10-21T00:00:00Z'});assert.deepEqual(await tryFinalize(state,{date:'2026-10-21',pub:regenerated}),['ROW_DATA_STALE']);
 const oneOld=published({u,patch:{'NYSE:P499':r=>{r.acquired_at='2026-10-07T00:00:00Z';}}}),chkOld=B.publishedCheck(oneOld,{date:'2026-10-15'});
 assert.deepEqual([chkOld.reasons,chkOld.stale_rows,chkOld.oldest_acquired],[['ROW_DATA_STALE'],1,'2026-10-07T00:00:00Z']);assert.deepEqual(await tryFinalize(state,{pub:oneOld}),['ROW_DATA_STALE']);
 assert.deepEqual(B.publishedCheck(published({u,patch:{'NYSE:P499':r=>{r.acquired_at=null;}}}),{date:'2026-10-15'}).reasons,['ROW_DATA_STALE']);
 assert.match(CFG.finalize_check.stale_action_ko,/workflow_dispatch all_shards=true/);
 // (c) Q and G each ≥ 90% of 504 (454); TARGET rows are not counted.
 assert.deepEqual(await tryFinalize(state,{pub:published({u,q:453})}),['Q_COVERAGE_LOW']);assert.deepEqual(await tryFinalize(state,{pub:published({u,g:453})}),['G_COVERAGE_LOW']);
 const chk=B.publishedCheck(published({u,q:454,g:454}),{date:'2026-10-15'});assert.deepEqual([chk.ok,chk.q,chk.g,chk.rows,chk.calc_version],[true,454,454,504,'qgv2-calc/2026-10-15.1']);
 // (d) draft basis: a newer acquisition in any shard (or another calc_version) is a changed input basis.
 const newer=published({u,patch:{'NYSE:P498':r=>{r.acquired_at='2026-10-14T05:00:00Z';}}});assert.equal(B.basisChanged(draft.basis,await B.inputBasis(newer)),true);
 assert.deepEqual(await tryFinalize(state,{pub:newer}),['DRAFT_BASIS_CHANGED']);assert.equal(B.basisChanged(draft.basis,await B.inputBasis(regenerated)),false);
 assert.equal(B.basisChanged(null,basis),true);
 // (e) the selected names' financial safety against the latest metrics.
 const first=B.currentSelection(state).rows[0],worse=published({u,patch:{[first.code]:r=>{r.metrics.net_debt_to_ebitda=4;}}}),wb=await B.inputBasis(worse);
 assert.deepEqual(await tryFinalize(state,{pub:worse}),['FINANCIAL_SAFETY_RECHECK_FAILED']);assert.deepEqual(B.finalizeBlockers(state,{date:'2026-10-15',published:worse,basis:wb,cfg:passed()}).safety_failed,[first.symbol]);
 assert.deepEqual(await tryFinalize(state,{pub:published({u,patch:{[first.code]:r=>{r.metrics.interest_coverage=null;}}})}),['FINANCIAL_SAFETY_RECHECK_FAILED']);
 // Number check: not passed; another calc_version (the shipped record is for 17.1, this fixture is 15.1) → mismatch; fewer than 10 companies → not passed.
 assert.deepEqual(await tryFinalize(state,{pub,cfg:notPassed}),['NUMBER_CHECK_NOT_PASSED']);assert.deepEqual(await tryFinalize(state,{pub,cfg:CFG}),['NUMBER_CHECK_CALC_VERSION_MISMATCH']);assert.deepEqual(await tryFinalize(state,{pub,cfg:passed('qgv2-calc/2026-10-14.1')}),['NUMBER_CHECK_CALC_VERSION_MISMATCH']);
 assert.deepEqual(await tryFinalize(state,{pub,cfg:passed('qgv2-calc/2026-10-15.1',{companies:9})}),['NUMBER_CHECK_NOT_PASSED']);
 const done=await tryFinalize(state,{pub});
 assert.equal(done.versions.length,1);assert.equal(done.versions[0].version,'v1');assert.deepEqual(done.rule_c,{start:'2026-10-15',version:'v1'});
 assert.equal(done.versions[0].calc_version,'qgv2-calc/2026-10-15.1');assert.equal(done.versions[0].sec_qgv2_as_of,'2026-10-14T21:00:00Z');assert.equal(done.versions[0].input_shards,basis.shards);
 assert.deepEqual(done.versions[0].number_check,{calc_version:'qgv2-calc/2026-10-15.1',passed:true,date:'2026-10-15',companies:10});
 assert.equal(done.versions[0].v_source,'DEVICE_TEMPORARY');assert.equal(B.V_SOURCE.ko,'임시 V');  // a device draft stays device V (PR-D: official only from a usable publication)
 let sum=done.versions[0].cash_pct;for(const r of done.versions[0].rows)sum+=r.pct;assert.equal(sum,100);assert.ok(done.versions[0].rows.every(r=>r.confirmed));
 // A later file with a new calc_version: changed basis + a new number check needed; after regeneration (all names kept) → v1.1.
 const next=published({u,calc:'qgv2-calc/2026-11-16.1',asOf:'2026-11-15T00:00:00Z',acquired:'2026-11-14T00:00:00Z'});
 assert.deepEqual(await tryFinalize(done,{date:'2026-11-16',pub:next}),['DRAFT_BASIS_CHANGED','NUMBER_CHECK_CALC_VERSION_MISMATCH']);
 const re=B.regenerateDraft(done,{...u,existing:[],date:'2026-11-16',basis:await B.inputBasis(next)});assert.deepEqual(re.fresh,[]);assert.equal(re.carried.length,15);
 assert.equal((await tryFinalize(re.state,{date:'2026-11-16',pub:next,cfg:passed('qgv2-calc/2026-11-16.1')})).versions[1].version,'v1.1');B.validateState(done);
 // The stored version rides in the playbook store.
 const s=memory(),pb=P.empty();pb.target_v1=done;P.write(s,pb);assert.equal(P.read(s).target_v1.versions[0].number_check.calc_version,'qgv2-calc/2026-10-15.1');
});

// 확정 차단 점검 (2026-10-25, display only): freshnessRows is the one source of the finalize freshness rows and cutoff.
const shard7=c=>Number(BigInt('0x'+require('node:crypto').createHash('sha256').update(c).digest('hex'))%7n);
const one=(f,code)=>f.rows.find(r=>r.code===code);
test('freshnessRows: cutoff = finalize date 23:59:59Z − 7 days; passes through acquisition UTC date + 6, blocks from + 7',()=>{
 assert.equal(CFG.finalize_check.freshness_max_days,7);
 const pub=published({acquired:'2026-10-17T03:13:16.553527Z'}),d23=B.freshnessRows(pub,{finalizeDate:'2026-10-23'}),d24=B.freshnessRows(pub,{finalizeDate:'2026-10-24'});
 assert.deepEqual([d23.cutoff,d23.next_cutoff,d24.cutoff],['2026-10-16T23:59:59.000Z','2026-10-17T23:59:59.000Z','2026-10-17T23:59:59.000Z']);
 assert.deepEqual([d23.rows.length,d23.today,d23.tomorrow,d24.today,d24.tomorrow],[504,0,504,504,504]);
 const r23=one(d23,'NYSE:P0'),r24=one(d24,'NYSE:P0');
 assert.deepEqual([r23.age_days,r23.last_ok_day,r23.blocks_today,r23.blocks_tomorrow],[6,'2026-10-23',false,true]);
 assert.deepEqual([r24.age_days,r24.last_ok_day,r24.blocks_today,r24.blocks_tomorrow],[7,'2026-10-23',true,true]);
 // Same rule as publishedCheck, never a second definition.
 for(const d of ['2026-10-22','2026-10-23','2026-10-24','2026-10-25']){const f=B.freshnessRows(pub,{finalizeDate:d}),c=B.publishedCheck(pub,{date:d});
  assert.equal(c.stale_rows,f.today,d);assert.equal(c.oldest_acquired,f.oldest_acquired,d);assert.equal(c.reasons.includes('ROW_DATA_STALE'),f.today>0,d);}
 // last_ok_day comes from the rule itself: the first second of the day and the second before 23:59:59Z are + 6; 23:59:59Z is + 7.
 for(const[at,last,pass24]of [['2026-10-17T00:00:00Z','2026-10-23',false],['2026-10-17T23:59:58.999Z','2026-10-23',false],['2026-10-17T23:59:59Z','2026-10-24',true]]){
  const p=published({patch:{'NYSE:P1':r=>{r.acquired_at=at;}}}),f=B.freshnessRows(p,{finalizeDate:'2026-10-24'}),r=one(f,'NYSE:P1');
  assert.deepEqual([r.last_ok_day,r.blocks_today],[last,!pass24],at);assert.equal(B.publishedCheck(p,{date:'2026-10-24'}).stale_rows,f.today,at);}
 // An invalid finalize date blocks every valued row (publishedCheck reports DATE_INVALID), as before.
 const bad=B.freshnessRows(pub,{finalizeDate:'20261024'});assert.deepEqual([bad.date_ok,bad.cutoff,bad.today,one(bad,'NYSE:P0').age_days],[false,null,504,null]);
 assert.deepEqual(B.publishedCheck(pub,{date:'20261024'}).reasons,['DATE_INVALID']);
 assert.deepEqual(B.freshnessRows(null,{finalizeDate:'2026-10-23'}).rows,[]);
});
test('freshnessRows: valued rows only — a normal NA row (even with an old acquired_at) and TARGET rows never appear',()=>{
 const pub=published({patch:{'NYSE:P10':r=>{NA_ROW(r);r.acquired_at='2026-09-01T00:00:00Z';},'NYSE:P11':NA_ROW,
  'NYSE:P12':r=>{r.axes={Q:{score:null},G:{score:null}};r.acquired_at='2026-09-01T00:00:00Z';},'NYSE:P13':r=>{r.acquired_at=null;}}});
 pub.target.x.acquired_at='2026-09-01T00:00:00Z';
 const f=B.freshnessRows(pub,{finalizeDate:'2026-10-15'}),codes=f.rows.map(r=>r.code);
 assert.equal(f.rows.length,502);assert.ok(!codes.includes('NYSE:P10')&&!codes.includes('NYSE:P11'),'NA rows excluded');assert.ok(!codes.some(c=>c.startsWith('TARGET:')));
 // LIVE without scores is still a valued row; a valued row without acquired_at blocks both days and cannot be classified.
 assert.deepEqual([one(f,'NYSE:P12').blocks_today,one(f,'NYSE:P12').age_days],[true,44]);
 assert.deepEqual(one(f,'NYSE:P13'),{code:'NYSE:P13',acquired_at:null,age_days:null,last_ok_day:null,blocks_today:true,blocks_tomorrow:true,shard:null,kind:'UNKNOWN',next_turn_day:null});
 const c=B.publishedCheck(pub,{date:'2026-10-15'});assert.deepEqual([f.today,c.stale_rows,c.na_rows,f.oldest_acquired,c.oldest_acquired],[2,2,2,'2026-09-01T00:00:00Z','2026-09-01T00:00:00Z']);
});
test('freshnessRows: KEPT (older than its own shard newest) vs ROTATION (whole shard old), from the inputBasis shard times',async()=>{
 const pub=published({patch:{'NYSE:P0':r=>{r.acquired_at='2026-10-05T03:00:00Z';}}}),shardOf=await B.rowShards(pub),basis=await B.inputBasis(pub,{shardOf});
 assert.equal(shardOf['NYSE:P0'],shard7('P0'));assert.equal(Object.keys(shardOf).length,504);assert.deepEqual(basis,await B.inputBasis(pub),'same basis with or without the precomputed shards');
 const f=B.freshnessRows(pub,{finalizeDate:'2026-10-15',basis,shardOf});
 assert.deepEqual([f.today,f.tomorrow,f.kept],[1,1,1]);assert.deepEqual(one(f,'NYSE:P0'),{code:'NYSE:P0',acquired_at:'2026-10-05T03:00:00Z',age_days:10,last_ok_day:'2026-10-11',blocks_today:true,blocks_tomorrow:true,shard:shard7('P0'),kind:'KEPT',next_turn_day:one(f,'NYSE:P0').next_turn_day});
 assert.ok(f.rows.filter(r=>r.code!=='NYSE:P0').every(r=>r.kind==='ROTATION'&&!r.blocks_today));
 // A kept row counts before it blocks (line '보존 행'); the counts never depend on the classification.
 assert.deepEqual([B.freshnessRows(pub,{finalizeDate:'2026-10-11',basis,shardOf}).today,B.freshnessRows(pub,{finalizeDate:'2026-10-11',basis,shardOf}).kept],[0,1]);
 // Without the basis every row is UNKNOWN: `unknown` counts them, so the screen shows the kept count as not known (never 0).
 const bare=B.freshnessRows(pub,{finalizeDate:'2026-10-15'});assert.deepEqual([bare.today,bare.kept,bare.unknown],[1,0,504]);assert.equal(f.unknown,0);assert.ok(bare.rows.every(r=>r.kind==='UNKNOWN'&&r.shard===null));
 // Whole shard old (collected 2026-10-06 in one run, minutes apart) → ROTATION, not KEPT; the other shards stay current.
 const s=shard7('P0'),old=published({patch:Object.fromEntries(Array.from({length:504},(_,i)=>['NYSE:P'+i,r=>{if(shard7(r.cik)===s)r.acquired_at='2026-10-06T22:'+String(37+i%5).padStart(2,'0')+':00Z';}]))});
 const so=await B.rowShards(old),fo=B.freshnessRows(old,{finalizeDate:'2026-10-14',basis:await B.inputBasis(old,{shardOf:so}),shardOf:so}),inShard=fo.rows.filter(r=>r.shard===s);
 assert.ok(inShard.length>0);assert.deepEqual([fo.today,fo.kept],[inShard.length,0]);assert.ok(inShard.every(r=>r.kind==='ROTATION'&&r.blocks_today&&r.last_ok_day==='2026-10-12'));
 // Runs farther apart than KEPT_GAP_MS (12 h) are different collections: a row 13 h older than its shard newest is KEPT, 11 h is not.
 assert.equal(B.KEPT_GAP_MS,12*3600000);
 for(const[at,kind]of [['2026-10-13T07:00:00Z','KEPT'],['2026-10-13T09:00:00Z','ROTATION']]){const p=published({patch:{'NYSE:P2':r=>{r.acquired_at=at;}}}),sp=await B.rowShards(p);
  assert.equal(one(B.freshnessRows(p,{finalizeDate:'2026-10-15',basis:await B.inputBasis(p,{shardOf:sp}),shardOf:sp}),'NYSE:P2').kind,kind,at);}
 // A normal NA row with an old acquired_at (a reasoned NA keeps its last acquisition) is neither counted nor kept.
 const na=published({patch:{'NYSE:P3':r=>{NA_ROW(r);r.acquired_at='2026-09-01T00:00:00Z';}}}),sn=await B.rowShards(na),fn=B.freshnessRows(na,{finalizeDate:'2026-10-15',basis:await B.inputBasis(na,{shardOf:sn}),shardOf:sn});
 assert.deepEqual([fn.today,fn.kept,one(fn,'NYSE:P3')],[0,0,undefined]);
 assert.deepEqual(await B.rowShards({records:{'NYSE:A':{cik:'1'}}}),{},'no shard_count → no shards');
 // next_turn_day: the first day ≥ the finalize date whose scheduled run collects the shard (day ordinal mod shard_count, as
 // universe/sec_universe_shares.py shard_index_for; Python date(2026, 10, 25).toordinal() % 7 = 0, 2026-10-15 → 4).
 assert.equal(pub.shard_count,7);
 for(const[d,s,turn]of [['2026-10-25',0,'2026-10-25'],['2026-10-25',1,'2026-10-26'],['2026-10-25',6,'2026-10-31'],['2026-10-15',4,'2026-10-15'],['2026-10-15',3,'2026-10-21'],['2026-10-15',5,'2026-10-16']]){
  const code=Object.keys(shardOf).find(c=>shardOf[c]===s);assert.equal(one(B.freshnessRows(pub,{finalizeDate:d,basis,shardOf}),code).next_turn_day,turn,d+' shard '+s);}
 assert.equal(B.freshnessRows(pub,{finalizeDate:'2026-10-25',basis,shardOf}).shard_count,7);assert.equal(one(B.freshnessRows({...pub,shard_count:undefined},{finalizeDate:'2026-10-25',basis,shardOf}),'NYSE:P0').next_turn_day,null,'no shard_count → no turn');assert.equal(await B.rowShards(null),null);
});

// User decision 2026-10-23: 「가격이 일부만 있을 때 V가 '몇 개 요인으로 계산됐는지'(예: 3/5)를 … 표시하고, V3·V4가 빠진 V로 TARGET v1
// 후보를 확정하지 않는다(초안은 가능, 표시 필수).」 Synthetic factor scores only (no price): a missing factor is a null score.
test('V factor count n/5 on draft rows; V without V3 or V4 stays in the draft but blocks finalize (2026-10-23)',async()=>{
 const V5={v_earnings_yield:{score:45},v_fcf_yield:{score:44},v_vs_industry:{score:43},v_vs_own_history:{score:42},v_expectation_check:{score:41}};
 assert.deepEqual(B.V_FACTORS,['v_earnings_yield','v_fcf_yield','v_vs_industry','v_vs_own_history','v_expectation_check']);assert.deepEqual(B.V_REQUIRED,['v_vs_industry','v_vs_own_history']);
 assert.deepEqual(B.vFactors({v:50,factors:V5}),{n:5,total:5,missing:[],required_ok:true});
 assert.deepEqual(B.vFactors({v:50,factors:{...V5,v_vs_industry:{score:null},v_expectation_check:{score:null}}}),{n:3,total:5,missing:['v_vs_industry','v_expectation_check'],required_ok:false});
 assert.deepEqual(B.vFactors({v:50,factors:{...V5,v_earnings_yield:{score:null}}}),{n:4,total:5,missing:['v_earnings_yield'],required_ok:true});
 // V null → 0/5 (never filled from factor scores), and no factors at all → 0/5.
 assert.equal(B.vFactors({v:null,factors:V5}).n,0);assert.equal(B.vFactors(null).n,0);assert.equal(B.vFactors({v:50}).required_ok,false);
 const miss=k=>({...FACTORS,[k]:null});
 const u=wide(40,[{symbol:'NOV3',total:99,sic:'2834',ig:'grpA',factors:miss('v_vs_industry')},{symbol:'NOV4',total:98.8,sic:'4911',ig:'grpB',factors:miss('v_vs_own_history')},{symbol:'NOV1',total:98.6,sic:'1311',ig:'grpC',factors:miss('v_earnings_yield')}]);
 const pub=published({u}),basis=await B.inputBasis(pub),draft=B.buildDraft({...u,existing:[],date:'2026-10-14',basis}),row=s=>draft.pool.find(r=>r.symbol===s);
 // The draft is allowed and carries the count and the missing ids per row.
 assert.deepEqual([row('NOV3').v_n,row('NOV3').v_total,row('NOV3').v_missing],[4,5,['v_vs_industry']]);assert.deepEqual(row('NOV4').v_missing,['v_vs_own_history']);
 assert.deepEqual([row('NOV1').v_n,row('NOV1').v_missing],[4,['v_earnings_yield']]);assert.deepEqual([row('S00').v_n,row('S00').v_missing],[5,[]]);
 assert.deepEqual(draft.pool.filter(B.vIncomplete).map(r=>r.symbol),['NOV3','NOV4']);
 let state={...B.emptyState(),draft};B.validateState(state);
 const sel=B.currentSelection(state);assert.ok(['NOV3','NOV4','NOV1'].every(s=>sel.rows.some(r=>r.symbol===s)),'the V3/V4-missing names are selected in the draft');
 for(const r of sel.rows)state=B.answer(state,{symbol:r.symbol,answer:'AGREE',date:'2026-10-14'});
 // Finalize blocked with that reason only (everything else passes); the names are listed.
 assert.deepEqual(await tryFinalize(state,{pub}),['V_FACTORS_V3_V4_MISSING']);
 assert.deepEqual(B.finalizeBlockers(state,{date:'2026-10-15',published:pub,basis,cfg:passed()}).v_incomplete,['NOV3','NOV4']);
 // 반대 on both → the next-ranked names take their place; NOV1 (4/5 without V1, V3 and V4 present) does not block → finalize allowed.
 for(const s of ['NOV3','NOV4'])state=B.answer(state,{symbol:s,answer:'DISAGREE',reason:'합성 · V3·V4 없음',date:'2026-10-14'});
 for(const s of B.currentSelection(state).pending)state=B.answer(state,{symbol:s,answer:'AGREE',date:'2026-10-14'});
 const done=await tryFinalize(state,{pub});assert.equal(done.versions.length,1,JSON.stringify(done));assert.ok(done.versions[0].rows.some(r=>r.symbol==='NOV1'));
 assert.ok(!done.versions[0].rows.some(r=>['NOV3','NOV4'].includes(r.symbol)));
 // A draft row stored before the count (no v_missing) cannot show V3·V4 → blocks until the draft is rebuilt.
 const legacy={...state,draft:{...state.draft,pool:state.draft.pool.map(({v_n,v_total,v_missing,...r})=>r)}};B.validateState(legacy);
 assert.deepEqual(await tryFinalize(legacy,{pub}),['V_FACTORS_V3_V4_MISSING']);
 // Scores, totals, selection counts and weights are unchanged by the count (display + gate only).
 assert.deepEqual(B.currentSelection(legacy).rows.map(r=>[r.symbol,r.grade,r.pct,r.total]),B.currentSelection(state).rows.map(r=>[r.symbol,r.grade,r.pct,r.total]));
});

test('input basis: shard = sha256(cik) mod shard_count (same rule as tools/published_coverage.py), newest acquisition per shard',async()=>{
 const crypto=require('node:crypto'),pub={calc_version:'qgv2-calc/2026-10-14.1',as_of:'2026-10-14T00:00:00Z',shard_count:7,records:{
  'NYSE:A':{cik:'0000320193',acquired_at:'2026-10-12T00:00:00Z'},'NYSE:B':{cik:'0000789019',acquired_at:'2026-10-13T00:00:00Z'},'NYSE:C':{cik:'0000320193',acquired_at:'2026-10-14T00:00:00Z'},
  'NYSE:D':{cik:null,acquired_at:null,reason_codes:['CIK_UNRESOLVED']},'TARGET:x':{cik:'0000000001',acquired_at:'2026-10-14T00:00:00Z'}}};
 const shard=c=>Number(BigInt('0x'+crypto.createHash('sha256').update(c).digest('hex'))%7n),b=await B.inputBasis(pub);
 const want=[[shard('0000320193'),'2026-10-14T00:00:00Z'],[shard('0000789019'),'2026-10-13T00:00:00Z']].sort((x,y)=>x[0]-y[0]).map(([k,v])=>k+'='+v).join('|');
 assert.deepEqual(b,{calc_version:'qgv2-calc/2026-10-14.1',as_of:'2026-10-14T00:00:00Z',shard_count:7,shards:want,type_scope:require(W+'qgv-v2.js').TYPE_SCOPE,withdrawn:''});assert.equal(await B.inputBasis(null),null);
 // A regenerated file (new as_of only) keeps the basis; a new acquisition changes it.
 assert.equal(B.basisChanged(b,await B.inputBasis({...pub,as_of:'2026-10-20T00:00:00Z'})),false);
 assert.equal(B.basisChanged(b,await B.inputBasis({...pub,records:{...pub.records,'NYSE:B':{cik:'0000789019',acquired_at:'2026-10-15T00:00:00Z'}}})),true);
});

// Owner decision 2026-10-17 item 4 (TYPE-SCOPE #284): the device type-application scope id is part of the input basis.
test('type_scope in the input basis: a scope change alone regenerates the draft; card answers carry over for the same symbols only',async()=>{
 const V2=require(W+'qgv-v2.js'),u=wide(40),pub=published({u}),basis=await B.inputBasis(pub);
 assert.equal(basis.type_scope,V2.TYPE_SCOPE);assert.match(basis.type_scope,/^qgv2-type-scope\/\d{4}-\d{2}-\d{2}\.\d+$/);
 assert.equal((await B.inputBasis({...pub,type_scope:'from-the-file'})).type_scope,V2.TYPE_SCOPE,'the scope is the device code, never read from the file');
 const old='qgv2-type-scope/2026-01-01.1',oldBasis=await B.inputBasis(pub,{typeScope:old});
 assert.deepEqual({...oldBasis,type_scope:V2.TYPE_SCOPE},basis,'same file, calc_version and acquisitions: only the scope differs');
 assert.equal(B.basisChanged(oldBasis,basis),true);assert.equal(B.basisChanged(basis,await B.inputBasis(pub)),false);
 const{type_scope:_,...legacy}=basis;assert.equal(B.basisChanged(legacy,basis),true,'a draft basis from before the scope id counts as changed');
 assert.equal(B.basisChanged({...basis,type_scope:null},basis),true);
 assert.throws(()=>B.validateState({...B.emptyState(),draft:B.buildDraft({...u,existing:[],date:'2026-10-14',basis:{...basis,type_scope:{bad:1}}})}),/TARGET_V1_STATE_INVALID/);
 // All cards answered (one 반대) on a draft built under the old scope → finalize blocked by DRAFT_BASIS_CHANGED only.
 let state={...B.emptyState(),draft:B.buildDraft({...u,existing:[],date:'2026-10-14',basis:oldBasis})};B.validateState(state);
 const no=B.currentSelection(state).rows[0].symbol;state=B.answer(state,{symbol:no,answer:'DISAGREE',reason:'합성',date:'2026-10-14'});
 for(const r of B.currentSelection(state).rows)state=B.answer(state,{symbol:r.symbol,answer:'AGREE',date:'2026-10-14'});assert.equal(B.currentSelection(state).complete,true);
 assert.deepEqual(await tryFinalize(state,{pub}),['DRAFT_BASIS_CHANGED']);
 // Scores under the new scope: a new top name enters and a former name leaves the Universe.
 const gone=B.currentSelection(state).rows[2].symbol,u2=wide(40,[{symbol:'NEWTOP',total:99}]);u2.universeCodes=u2.universeCodes.filter(c=>c!=='NASDAQ:'+gone);
 const pub2=published({u:u2}),basis2=await B.inputBasis(pub2),re=B.regenerateDraft(state,{...u2,existing:[],date:'2026-10-15',basis:basis2});
 assert.equal(re.state.draft.basis.type_scope,V2.TYPE_SCOPE);assert.equal(B.basisChanged(re.state.draft.basis,basis2),false);
 assert.ok(re.dropped.includes(gone));assert.ok(!re.state.answers.some(a=>a.symbol===gone),'an answer for a name outside the new pool is not carried');
 assert.ok(re.fresh.includes('NEWTOP'));assert.ok(!re.state.answers.some(a=>a.symbol==='NEWTOP'),'a new name needs a fresh card');
 const after=B.currentSelection(re.state);assert.ok(!after.rows.some(r=>r.symbol===no),'반대 carries over for the same symbol');
 assert.ok(re.carried.every(s=>state.answers.some(a=>a.symbol===s)));assert.equal(re.carried.length+re.fresh.length,after.rows.length);
 let next=re.state;assert.deepEqual(await tryFinalize(next,{date:'2026-10-15',pub:pub2}),['TARGET_V1_CARDS_PENDING']);
 for(const s of after.pending)next=B.answer(next,{symbol:s,answer:'AGREE',date:'2026-10-15'});
 const done=await tryFinalize(next,{date:'2026-10-15',pub:pub2});assert.equal(done.versions.length,1,JSON.stringify(done));assert.equal(done.versions[0].type_scope,V2.TYPE_SCOPE);B.validateState(done);
});

// #285 / #289 (owner instruction 2026-10-17 item 3): an identity-conflict withdrawal row in the latest file is part of the input
// basis. It has no acquired_at, so the shard times can stay the same; the withdrawal list alone makes the draft basis changed,
// finalize is blocked until the draft is regenerated, and the regenerated draft drops the stopped issuer.
test('withdrawal in the input basis: a new TARGET or Universe withdrawal blocks finalize until the draft is regenerated without it',async()=>{
 const u=wide(40),pub=published({u}),basis=await B.inputBasis(pub);assert.equal(basis.withdrawn,'');
 let state={...B.emptyState(),draft:B.buildDraft({...u,existing:[],date:'2026-10-14',basis})};
 for(const r of B.currentSelection(state).rows)state=B.answer(state,{symbol:r.symbol,answer:'AGREE',date:'2026-10-14'});
 const victim=B.currentSelection(state).rows[0],cik=u.inputs.records[victim.code].cik,when={detected_at:'2026-10-14T22:00:00Z',withdrawn_acquired_at:'2026-10-13T20:00:00Z'};
 // TARGET withdrawal (same CIK as a selected Universe code): the raw Universe row keeps its values, so only the basis catches it.
 const pubT=published({u});pubT.target.w={cik,state:'NOT_AVAILABLE',reason_codes:['IDENTITY_CONFLICT_WITHDRAWN'],acquired_at:null,...when};
 const bT=await B.inputBasis(pubT);assert.equal(bT.shards,basis.shards,'shard times unchanged');assert.equal(bT.withdrawn,'TARGET:w');
 assert.equal(B.basisChanged(state.draft.basis,bT),true);assert.deepEqual(await tryFinalize(state,{pub:pubT}),['DRAFT_BASIS_CHANGED']);
 // Universe withdrawal row (records section: empty row, no cik, the withdrawal reason).
 const pubU=published({u,patch:{[victim.code]:r=>{NA_ROW(r);r.reason_codes=['IDENTITY_CONFLICT_WITHDRAWN'];delete r.cik;Object.assign(r,when,{withdrawn_cik:cik});}}});
 assert.equal((await B.inputBasis(pubU)).withdrawn,victim.code);assert.ok((await tryFinalize(state,{pub:pubU})).includes('DRAFT_BASIS_CHANGED'));
 // A draft basis from before the withdrawal list existed counts as changed.
 const{withdrawn:_,...legacy}=basis;assert.equal(B.basisChanged(legacy,basis),true);
 // Regenerate from the device scores (Qgv2Inputs marks the stopped code identity_withdrawn): the issuer leaves the pool.
 const u2=wide(40);u2.inputs.records[victim.code]={...u2.inputs.records[victim.code],identity_withdrawn:true};
 const re=B.regenerateDraft(state,{...u2,existing:[],date:'2026-10-15',basis:bT});assert.ok(re.dropped.includes(victim.symbol));
 assert.ok(!re.state.draft.pool.some(r=>r.code===victim.code));assert.equal(re.state.draft.excluded_counts.IDENTITY_CONFLICT_WITHDRAWN,1);
 assert.equal(B.basisChanged(re.state.draft.basis,bT),false);B.validateState(re.state);
 let next=re.state;for(const s of B.currentSelection(next).pending)next=B.answer(next,{symbol:s,answer:'AGREE',date:'2026-10-15'});
 const done=await tryFinalize(next,{pub:pubT});assert.equal(done.versions.length,1,JSON.stringify(done));assert.ok(!done.versions[0].rows.some(r=>r.symbol===victim.symbol));
 assert.throws(()=>B.validateState({...state,draft:{...state.draft,basis:{...basis,withdrawn:{bad:1}}}}),/TARGET_V1_STATE_INVALID/);
});

test('draft regeneration: answers carry over only for the same symbols; new names need a fresh card',()=>{
 const u=wide(40),draft=B.buildDraft({...u,existing:[],date:'2026-10-14',basis:{calc_version:'qgv2-calc/2026-10-14.1',as_of:null,shard_count:7,shards:'0=x'}});let state={...B.emptyState(),draft};
 const sel=B.currentSelection(state);state=B.answer(state,{symbol:sel.rows[1].symbol,answer:'DISAGREE',reason:'합성',date:'2026-10-14'});
 for(const r of B.currentSelection(state).rows)state=B.answer(state,{symbol:r.symbol,answer:'AGREE',date:'2026-10-14'});
 // New scores: a new top name appears and the former #3 leaves the Universe (its answer is dropped).
 const gone=B.currentSelection(state).rows[2].symbol,u2=wide(40,[{symbol:'NEWTOP',total:99}]);
 u2.universeCodes=u2.universeCodes.filter(c=>c!=='NASDAQ:'+gone);
 const re=B.regenerateDraft(state,{...u2,existing:[],date:'2026-11-16',basis:{calc_version:'qgv2-calc/2026-11-16.1',as_of:null,shard_count:7,shards:'0=y'}});
 assert.deepEqual(re.fresh,['NEWTOP'].concat(re.fresh.filter(x=>x!=='NEWTOP')));assert.ok(re.fresh.includes('NEWTOP'));assert.ok(re.dropped.includes(gone));
 assert.equal(re.state.draft.basis.calc_version,'qgv2-calc/2026-11-16.1');assert.equal(re.state.draft.created,'2026-11-16');
 const after=B.currentSelection(re.state);assert.ok(!after.rows.some(r=>r.symbol===sel.rows[1].symbol),'반대 stays applied');assert.ok(after.pending.includes('NEWTOP'));assert.equal(after.complete,false);
 assert.ok(re.carried.every(s=>re.state.answers.some(a=>a.symbol===s)));assert.equal(re.carried.length+re.fresh.length,after.rows.length);
});

test('name shortfall (< 15 eligible): shown with reasons, nothing relaxed or re-added, finalize blocked',async()=>{
 const few=universe(Array.from({length:12},(_,i)=>({symbol:'N'+String(i).padStart(2,'0'),total:80-i,sic:SICS[i%SICS.length],ig:'g'+(i%6)})).concat([{symbol:'NA1',total:99,metrics:{net_debt_to_ebitda:null}},{symbol:'BAD',total:98,metrics:{interest_coverage:1}}]));
 const pub=published({u:few}),draft=B.buildDraft({...few,existing:[],date:'2026-10-14',basis:await B.inputBasis(pub)});let state={...B.emptyState(),draft};
 let sel=B.currentSelection(state);assert.equal(sel.rows.length,12);assert.equal(sel.shortfall,3);assert.ok(!sel.rows.some(r=>['NA1','BAD'].includes(r.symbol)));
 assert.deepEqual(sel.shortfall_reasons,{FINANCIAL_SAFETY_NOT_AVAILABLE:1,FINANCIAL_SAFETY_FAIL:1});
 state=B.answer(state,{symbol:'N00',answer:'DISAGREE',reason:'합성',date:'2026-10-14'});sel=B.currentSelection(state);assert.equal(sel.rows.length,11);assert.equal(sel.shortfall,4);assert.equal(sel.shortfall_reasons.USER_DISAGREE,1);
 for(const r of sel.rows)state=B.answer(state,{symbol:r.symbol,answer:'AGREE',date:'2026-10-14'});assert.equal(B.currentSelection(state).complete,true);
 assert.deepEqual(await tryFinalize(state,{pub}),['TARGET_V1_SHORTFALL']);
});

test('schedule: finalize target 2nd week of 2026-11; unfinalized or late → that round is risk-code checks only (no list)',()=>{
 assert.deepEqual(CFG.schedule.finalize_window,['2026-11-09','2026-11-15']);assert.equal(CFG.schedule.deadline,'2026-11-15');assert.equal(CFG.schedule.unfinalized_round_mode,'RISK_CODE_CHECK_ONLY');
 const [r1,r2]=B.rounds();assert.ok(CFG.schedule.deadline<r1.date);
 const none=B.emptyState();assert.equal(B.roundMode(none,r1),'RISK_CODE_CHECK_ONLY');assert.equal(B.roundMode(none,r2),'RISK_CODE_CHECK_ONLY');
 assert.deepEqual(B.scheduleState(none,'2026-11-12'),{finalized:false,finalized_on:null,window:['2026-11-09','2026-11-15'],deadline:'2026-11-15',postponed:false,late:false});
 assert.equal(B.scheduleState(none,'2026-11-16').postponed,true);
 const onTime={...none,versions:[{version:'v1',date:'2026-11-12',rows:[],cash_pct:100}]};assert.equal(B.roundMode(onTime,r1),'LIST');assert.equal(B.scheduleState(onTime,'2026-11-20').late,false);
 // B-3 F1: saved on the deadline month's round day but after the deadline → still postponed for that round (no list).
 assert.equal(r1.date,'2026-11-16');const lateSameDay={...none,versions:[{version:'v1',date:'2026-11-16',rows:[],cash_pct:100}]};
 assert.equal(B.roundMode(lateSameDay,r1),'RISK_CODE_CHECK_ONLY');assert.equal(B.roundMode(lateSameDay,r2),'LIST');
 const onDeadline={...none,versions:[{version:'v1',date:'2026-11-15',rows:[],cash_pct:100}]};assert.equal(B.roundMode(onDeadline,r1),'LIST');
 const late={...none,versions:[{version:'v1',date:'2026-12-01',rows:[],cash_pct:100}]};assert.equal(B.roundMode(late,r1),'RISK_CODE_CHECK_ONLY');assert.equal(B.roundMode(late,r2),'LIST');assert.equal(B.scheduleState(late,'2026-12-02').late,true);
 // F1 (owner decision 2026-10-24): the first finalize date decides. An on-time v1 re-saved as v1.1 after the deadline or
 // after the round keeps the round's list, the schedule is not late, and finalized_on stays the first date.
 const resaved=(d)=>({...none,versions:[{version:'v1',date:'2026-11-12',rows:[],cash_pct:100},{version:'v1.1',date:d,rows:[],cash_pct:100}]});
 for(const d of ['2026-11-16','2026-11-20','2026-12-01']){assert.equal(B.roundMode(resaved(d),r1),'LIST',d);assert.equal(B.roundMode(resaved(d),r2),'LIST',d);
  assert.equal(B.scheduleState(resaved(d),'2026-12-02').late,false,d);assert.equal(B.scheduleState(resaved(d),'2026-12-02').finalized_on,'2026-11-12',d);}
 assert.equal(B.firstVersion(resaved('2026-11-20')).version,'v1');assert.equal(B.latestVersion(resaved('2026-11-20')).version,'v1.1');assert.equal(B.firstVersion(none),null);
 // A late first finalize stays late even after a later re-save.
 const lateResaved={...none,versions:[{version:'v1',date:'2026-11-16',rows:[],cash_pct:100},{version:'v1.1',date:'2026-11-20',rows:[],cash_pct:100}]};
 assert.equal(B.roundMode(lateResaved,r1),'RISK_CODE_CHECK_ONLY');assert.equal(B.roundMode(lateResaved,r2),'LIST');assert.equal(B.scheduleState(lateResaved,'2026-11-21').late,true);
 assert.deepEqual(B.riskCodes().map(c=>c.code),['X1','X2','X3','R1','R2','R3','R4','R5']);assert.ok(B.riskCodes().every(c=>c.text&&!/매수|매도/.test(c.text)));
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
 for(const k of ['number_check','score_basis','coverage','filters','sector_spread','candidates','selection','templates','cards','rebalance','transition','virtual_sets','review_rule'])assert.ok(CFG[k].version==='v0'&&['UNCALIBRATED','OWNER_RULE','USER_DECISION_2026-10-15','USER_DECISION_2026-10-15_EVENING'].includes(CFG[k].decision),k);
 assert.equal(CFG.schedule.decision,'USER_DECISION_2026-10-15');assert.equal(CFG.finalize_check.decision,'USER_DECISION_2026-10-15_EVENING');assert.equal(CFG.filters.financial_safety.missing_for_exclusion,'EXCLUDED');
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

// #285 (owner instruction 2026-10-17 item 3): a TARGET issuer withdrawn for an identity conflict is used nowhere. Through the real
// loader (Qgv2Inputs) and accessor (QgvScores), its same-CIK Universe codes never reach the candidate pool and carry only the
// withdrawal reason; other issuers are unchanged. Synthetic data only (tools/qgv_v2_fixture.js).
test('identity-conflict withdrawal: same-CIK Universe codes are excluded from the TARGET v1 pool with the withdrawal reason',async()=>{
 const path=require('node:path'),D=path.join(__dirname,W),F=require('./qgv_v2_fixture.js');
 for(const[name,file]of[['ProfileDefaults','profile-defaults.js'],['TypeConfigDefaults','type-config-defaults.js'],['QgvV2','qgv-v2.js'],['Qgv2Inputs','qgv2-inputs.js'],['QgvScores','qgv-scores.js']])globalThis[name]=globalThis[name]||require(path.join(D,file));
 const SQ=globalThis.Qgv2Inputs,QS=globalThis.QgvScores,p=F.payload(),codes=Object.keys(p.records).filter(c=>!c.startsWith('TARGET:')).sort();
 const identities=codes.map(c=>({company_id:c,ticker:c.split(':')[1]})),empty={state:'NOT_AVAILABLE',acquired_at:null,fiscal_year_end:null,metrics:{},factors:{},axes:{},v_inputs_v2:{}};
 const cik=p.records['NASDAQ:GOOGL'].cik,same=codes.filter(c=>p.records[c].cik===cik);assert.ok(same.length>=1);
 p.target.googl={...empty,cik,reason_codes:[SQ.WITHDRAWN_REASON],detected_at:'2026-10-13T12:00:00Z',withdrawn_acquired_at:'2026-10-12T00:00:00Z'};
 const inputs=SQ.fromInputs(SQ.light(p)),quotes=await QS.collectQuotes({PrivateSubsetView:{prices:()=>new Map(Object.entries(F.quotes()))}},{identities,v2Inputs:inputs});
 const computed=QS.compute({identities,publicScreens:{[SQ.FILE]:inputs},v2Inputs:inputs,quotes});assert.equal(computed.v2_state,'READY');
 const rows=B.universeRows({computed,inputs,universeCodes:codes,existing:[]});
 const hit=rows.filter(x=>x.cik===cik);assert.equal(hit.length,1);   // one point per issuer (share classes deduped)
 for(const r of hit){assert.equal(r.withdrawn,true);assert.equal(r.total,null);assert.deepEqual(B.exclusions(r),['IDENTITY_CONFLICT_WITHDRAWN']);}
 const draft=B.buildDraft({computed,inputs,universeCodes:codes,existing:[],date:'2026-10-17'}),pooled=new Set(draft.pool.map(r=>r.code));
 assert.ok(same.every(c=>!pooled.has(c)));assert.ok(draft.excluded_counts.IDENTITY_CONFLICT_WITHDRAWN>=1);
 assert.ok(rows.filter(r=>r.cik!==cik).every(r=>r.withdrawn===false));assert.equal(draft.excluded_counts.IDENTITY_CONFLICT_WITHDRAWN,1);   // the pool may be empty here: the fixture has no safety metrics (NA excluded)
});

// #289 (UNI-WITHDRAWN): a Universe code withdrawn for an identity conflict is stopped even when a live TARGET row of the same
// ticker exists; the builder row of that code never borrows the TARGET row's score and carries only the withdrawal reason.
test('identity-conflict withdrawal: a withdrawn Universe code never borrows a same-ticker TARGET score',async()=>{
 const path=require('node:path'),D=path.join(__dirname,W),F=require('./qgv_v2_fixture.js');
 for(const[name,file]of[['ProfileDefaults','profile-defaults.js'],['TypeConfigDefaults','type-config-defaults.js'],['QgvV2','qgv-v2.js'],['Qgv2Inputs','qgv2-inputs.js'],['QgvScores','qgv-scores.js']])globalThis[name]=globalThis[name]||require(path.join(D,file));
 const SQ=globalThis.Qgv2Inputs,QS=globalThis.QgvScores,p=F.payload(),codes=Object.keys(p.records).filter(c=>!c.startsWith('TARGET:')).sort();
 assert.ok(codes.includes('NASDAQ:NVDA')&&p.target.nvda);
 p.records['NASDAQ:NVDA']={state:'NOT_AVAILABLE',acquired_at:null,fiscal_year_end:null,metrics:{},factors:{},axes:{},v_inputs_v2:{},cik:p.records['NASDAQ:NVDA'].cik,reason_codes:[SQ.WITHDRAWN_REASON],detected_at:'2026-10-13T12:00:00Z',withdrawn_acquired_at:'2026-10-12T00:00:00Z'};
 const ids=new Map([['NVDA','nvda']]),identities=codes.map(c=>{const t=c.split(':')[1];return{company_id:ids.get(t)||c,ticker:t};});
 const inputs=SQ.fromInputs(SQ.light(p));assert.equal(inputs.records['NASDAQ:NVDA'].identity_withdrawn,true);
 const quotes=await QS.collectQuotes({PrivateSubsetView:{prices:()=>new Map(Object.entries(F.quotes()))}},{identities,v2Inputs:inputs});
 const computed=QS.compute({identities,publicScreens:{[SQ.FILE]:inputs},v2Inputs:inputs,quotes});
 const rows=B.universeRows({computed,inputs,universeCodes:codes,existing:[]}),nv=rows.find(r=>r.code==='NASDAQ:NVDA');
 assert.ok(nv);assert.deepEqual([nv.withdrawn,nv.total,nv.rank],[true,null,null]);assert.deepEqual(B.exclusions(nv),['IDENTITY_CONFLICT_WITHDRAWN']);
 const draft=B.buildDraft({computed,inputs,universeCodes:codes,existing:[],date:'2026-10-17'});
 assert.ok(!draft.pool.some(r=>r.symbol==='NVDA'));assert.equal(draft.excluded_counts.IDENTITY_CONFLICT_WITHDRAWN,1);
});

test('canonical shared QGV page result feeds TARGET without QG-only candidates or a separate score calculation',async()=>{
 const names=['EnginePreview','ProfileDefaults','TypeConfigDefaults','DcfParametersDefaults','QgvV2','Qgv2Inputs','QgvScores'];
 const before=new Map(names.map(n=>[n,Object.getOwnPropertyDescriptor(globalThis,n)]));
 try{
  for(const[name,file]of [['EnginePreview','engine-preview.js'],['ProfileDefaults','profile-defaults.js'],['TypeConfigDefaults','type-config-defaults.js'],['DcfParametersDefaults','dcf-parameters-defaults.js'],['QgvV2','qgv-v2.js'],['Qgv2Inputs','qgv2-inputs.js'],['QgvScores','qgv-scores.js']])globalThis[name]=require(W+file);
  const F=require('./qgv_v2_fixture.js'),S=require(W+'sec-qgv2.js'),Q=globalThis.QgvScores;
  const inputs=Qgv2Inputs.fromInputs(S.toInputs(F.strictPayload(),{now:'2026-10-14T00:00:00Z'}));
  const codes=Object.keys(inputs.records).filter(c=>!c.startsWith('TARGET:')),ids=codes.map(c=>({company_id:c,ticker:c.split(':')[1]}));
  const quotes=new Map(F.strictUniverseValues().slice(1).map(r=>[r[0],{price:r[2],currency:'USD'}]));
  const view={PrivateSubsetView:{prices:()=>quotes}},catalog={instruments:[]};
  const page=await Q.pageResult(view,{v2Inputs:inputs,catalog,identities:ids});
  assert.ok(page.computed.official);assert.equal(page.computed.v2_state,'READY');
  globalThis.QgvScores={...Q,compute(){throw Error('unexpected separate computation');}};
  const computed=await P.prepareScores(view,{catalog,screens:{'sec-qgv2.json':inputs},idByTicker:new Map(ids.map(r=>[r.ticker,r.company_id])),universeCodes:codes});
  assert.equal(computed.rows,page.computed.rows,'same shared evaluated rows');
  const draft=B.buildDraft({computed,inputs,universeCodes:codes,date:'2026-10-14'});
  assert.ok(draft.pool.length>0,'strict synthetic fixture has eligible names');
  const byTicker=new Map(Object.values(computed.rows).map(r=>[r.ticker,r]));
  for(const r of draft.pool){const source=byTicker.get(r.symbol);assert.ok(Number.isInteger(source.rank));assert.equal(source.qg_reference,null);assert.ok(Number.isFinite(r.v));assert.equal(r.safety,'PASS');assert.ok(Math.abs(r.total-source.v2.total)<0.0001);
   // V factor count from the shared accessor row (2026-10-23): score !== null among the 5 V factors.
   const have=B.V_FACTORS.filter(k=>Number.isFinite(source.v2.factors?.[k]?.score));assert.equal(r.v_n,have.length,r.symbol);assert.deepEqual(r.v_missing,B.V_FACTORS.filter(k=>!have.includes(k)),r.symbol);}
  for(const r of Object.values(computed.rows).filter(r=>r.qg_reference))assert.ok(!draft.pool.some(p=>p.symbol===r.ticker),'QG-only row excluded');
  assert.deepEqual(CFG.number_check.result,{calc_version:'qgv2-calc/2026-10-17.1',passed:true,date:'2026-10-23',companies:10},'integration leaves the recorded number check as decided 2026-10-23');
 }finally{for(const[n,d]of before)if(d)Object.defineProperty(globalThis,n,d);else delete globalThis[n];}
});

// ---------- PR-D (owner decision D8 (b), GSQ-024; spec 2.1.7, 6.1.2~6.1.4): the central V publication as the V source ----------
// The synthetic publication of tests/fixtures/qgv_official_vectors_v1.json (base_text: calc_version qgv2-calc/2026-10-23.1, price
// basis 2026-10-13, verified), read through the real QgvOfficial. Synthetic data only; nothing here carries a price.
const QO=require(W+'qgv-official.js'),FIX=JSON.parse(require('node:fs').readFileSync(require('node:path').join(__dirname,'../tests/fixtures/qgv_official_vectors_v1.json'),'utf8'));
const OFFICIAL_CALC='qgv2-calc/2026-10-23.1',OTHER_ID='qgvpub-'+'a'.repeat(64);
const enc=s=>new TextEncoder().encode(s);
const officialPub=(text=FIX.base_text)=>QO.parse(enc(text));
// The page's sec-qgv2.json value (Qgv2Inputs shape) for the publication's codes: sic / metrics / cik, the parts the publication lacks.
function officialInputs(pub,patch={}){const records={};let i=0;for(const[code,r]of Object.entries(pub.rows))records[code]={cik:r.cik||('PUB'+i),state:r.state,sic:SICS[(i++)%SICS.length],industry_group:r.industry_group,metrics:{...METRICS,...(patch[code]||{})},qg_axes:{Q:{score:r.axes.Q.score},G:{score:r.axes.G.score}}};return{records};}
const universeOf=pub=>Object.keys(pub.rows).filter(k=>!k.startsWith('TARGET:'));
/* A device-path computed (QgvScores accessor shape: rows by company id, extra accessor fields) holding the same published scores.
   The record each row reads comes from the REAL device identity mapping (QgvScores.universeIdentities + compute, i.e. codeIndex:
   the TARGET record when it is there and not NOT_AVAILABLE, else the Universe code by ticker), never from the adapter's rule. TARGET
   identities: the device catalog (VirtualTradingRunner.TARGETS, exchange suffix dropped). */
const QS=require(W+'qgv-scores.js'),PAGE_TARGETS=Object.entries(require(W+'virtual-trading-runner.js').TARGETS).map(([company_id,t])=>({company_id,ticker:t.split('.')[0]}));
function deviceTwin(pub,inputs=officialInputs(pub)){const U=QS.universeIdentities(inputs,PAGE_TARGETS),dev=QS.compute({identities:U.identities,v2Inputs:inputs,quotes:{},official:U}),rows={};
 for(const[cid,d]of Object.entries(dev.rows)){if(!d.code)continue;const r=pub.rows[d.code];
  rows[cid]={company_id:cid,ticker:d.ticker,code:d.code,rank:r.rank,qg_reference:null,primary:null,v2:{version:'v2',flags:[],total:r.total,q:r.axes.Q.score,g:r.axes.G.score,v:r.axes.V.score,axes:structuredClone(r.axes),factors:structuredClone(r.factors),
   factors_available:Object.values(r.factors).filter(f=>Number.isFinite(f.score)).length,factors_total:15,q_industry_percentile:r.q_industry_percentile,value_trap_gate:r.value_trap_gate,selected_types:[...r.selected_types]}};}
 return{v2_state:'READY',v2_as_of:pub.times.inputs_as_of,profile:{id:pub.weights.profile_id},priced_codes:pub.price_source.supplied,rows};}
// A vector case of the fixture (JSON ops on the base, Python verdict valid) through the real QgvOfficial.validate.
function applyOps(p,ops){p=structuredClone(p);for(const op of ops){const path=[...op.path],last=path.pop();let t=p;for(const k of path)t=t[k];if(op.delete)delete t[last];else t[last]=structuredClone(op.value);}return p;}
const casePub=id=>{const c=FIX.cases.find(x=>x.id===id);assert.ok(c&&c.valid===true,id);return QO.validate(applyOps(JSON.parse(FIX.base_text),c.ops));};
const DRAFT_KEYS=['basis','config_version','coverage','created','eligible_count','excluded','excluded_counts','pool','profile_id','universe_rows','v2_as_of'];
const VERSION_KEYS=['calc_version','cash_pct','config_version','date','draft_created','input_shards','number_check','rows','sec_qgv2_as_of','type_scope','v_source','version'];
function walkKeys(v,out=new Set()){if(v&&typeof v==='object'){for(const[k,x]of Object.entries(v)){out.add(k.toLowerCase());walkKeys(x,out);}}return out;}
// A fetch-like source answering qgv-official.json (QgvOfficial.resolve's one request).
const served=(status,text=FIX.base_text)=>async()=>({status,ok:status>=200&&status<300,headers:{get:()=>null},arrayBuffer:async()=>enc(text).buffer});

test('PR-D V sources: V_SOURCE unchanged (web_app pin), V_SOURCES = web_app/qgv.js text with DEVICE_TEMPORARY the same object',()=>{
 assert.deepEqual({...B.V_SOURCE},{id:'DEVICE_TEMPORARY',ko:'임시 V',note:'기기 시세로 계산 · 중앙 V 미게시'});assert.ok(Object.isFrozen(B.V_SOURCE));
 assert.equal(B.V_SOURCES.DEVICE_TEMPORARY,B.V_SOURCE);assert.deepEqual(Object.keys(B.V_SOURCES),['DEVICE_TEMPORARY','OFFICIAL_CENTRAL']);
 const WQ=require('../src/investment_system/product/web_app/qgv.js');assert.deepEqual(JSON.parse(JSON.stringify(B.V_SOURCES)),JSON.parse(JSON.stringify(WQ.V_SOURCES)));
 assert.deepEqual(JSON.parse(JSON.stringify(B.V_SOURCES)),JSON.parse(JSON.stringify(QO.V_SOURCES)));assert.ok(Object.isFrozen(B.V_SOURCES.OFFICIAL_CENTRAL));
});

test('PR-D adapter: officialComputed maps published rows only (the TARGET row as on the device, NA kept null, no price key); not for an unchecked payload',async()=>{
 const pub=await officialPub(),c=B.officialComputed(pub);
 assert.equal(B.officialComputed(pub),c,'memoized per publication');assert.ok(Object.isFrozen(c)&&Object.isFrozen(c.rows)&&Object.isFrozen(c.rows['NASDAQ:AMD'].v2));
 assert.deepEqual([c.v2_state,c.v2_as_of,c.profile.id,c.priced_codes],['READY',pub.times.inputs_as_of,'qgv-v2/balanced/gate-on',pub.price_source.supplied]);
 assert.deepEqual(Object.keys(c.rows).sort(),universeOf(pub).sort(),'one row per Universe code; TARGET rows outside the Universe are not rows');
 // NASDAQ:AMD reads TARGET:amd (LIVE, the device path reads that TARGET record); GOOG keeps its own row (TARGET:googl is NOT_AVAILABLE).
 const amd=c.rows['NASDAQ:AMD'];assert.deepEqual([amd.ticker,amd.code,amd.v2.total,amd.v2.v],['AMD','TARGET:amd',pub.rows['TARGET:amd'].total,pub.rows['TARGET:amd'].axes.V.score]);
 assert.deepEqual([c.rows['NASDAQ:GOOG'].code,c.rows['NASDAQ:GOOG'].v2.total],['NASDAQ:GOOG',pub.rows['NASDAQ:GOOG'].total]);
 // NA stays null with its reason: NO_IEX_TRADE rows have V null (never 0); a price-dependent factor keeps its public label.
 for(const k of ['NYSE:ARE','NYSE:MMM']){const v2=c.rows[k].v2;assert.equal(pub.rows[k].price_status,'NO_IEX_TRADE');assert.equal(v2.v,null);assert.equal(v2.axes.V.score,null);assert.ok(Number.isFinite(v2.total),'Q·G-only total stays as published');}
 const algn=c.rows['NASDAQ:ALGN'].v2,pd=Object.values(algn.factors).filter(f=>f.reason==='PRICE_DEPENDENT_NOT_COMPUTABLE');assert.ok(pd.length>0&&pd.every(f=>f.score===null));
 assert.equal(algn.factors_available,Object.values(algn.factors).filter(f=>f.score!==null).length);assert.equal(algn.factors_total,15);
 for(const k of walkKeys(c))assert.ok(!QO.FORBIDDEN_KEYS.includes(k),'no price-shaped key: '+k);
 // Not validated by QgvOfficial (plain JSON, or a copy of an accepted one) → no adapter, no record.
 const plain=JSON.parse(FIX.base_text);assert.equal(B.officialComputed(plain),null);assert.equal(B.officialRecord(plain),null);assert.equal(B.officialRecord(structuredClone(pub)),null);
 assert.deepEqual(B.officialRecord(pub),{publication_id:pub.publication_id,price_basis_date:'2026-10-13',calc_version:OFFICIAL_CALC,inputs_as_of:pub.times.inputs_as_of});
});

test('PR-D draft: the official pool equals the device pool for the same scores (builder logic unchanged); only official adds v_source + official',async()=>{
 const pub=await officialPub(),inputs=officialInputs(pub),universeCodes=universeOf(pub),args={inputs,universeCodes,existing:['AMD'],date:'2026-10-14',basis:null};
 const official=B.buildDraft({...args,computed:B.officialComputed(pub),official:pub}),device=B.buildDraft({...args,computed:deviceTwin(pub)});
 const{v_source,official:rec,...rest}=official;assert.equal(v_source,'OFFICIAL_CENTRAL');assert.deepEqual(rec,B.officialRecord(pub));
 assert.deepEqual(rest,device,'same rank, issuer dedupe, exclusions, pool and templates from the same scores');assert.deepEqual(Object.keys(device).sort(),DRAFT_KEYS,'a device draft gains no key');
 assert.deepEqual(official.pool.map(r=>r.symbol),['AFL','AMD','AES','APD','ALLE','ACN','LNT','ADBE','A']);assert.equal(official.pool.find(r=>r.symbol==='AMD').in19,true);
 // NA never 0: the V-null rows are excluded by axis coverage, never ranked on a filled V.
 const rows=B.universeRows({...args,computed:B.officialComputed(pub)});for(const s of ['ARE','MMM']){const r=rows.find(x=>x.symbol===s);assert.equal(r.v,null);assert.ok(B.exclusions(r).includes('AXIS_COVERAGE_LOW'));}
 // Device drafts are as before: official null / absent are the same call; device scores never carry an official label.
 const plainDevice=B.buildDraft({...u0(),existing:[],date:'2026-10-14'});assert.deepEqual(B.buildDraft({...u0(),existing:[],date:'2026-10-14',official:null}),plainDevice);assert.deepEqual(Object.keys(plainDevice).sort(),DRAFT_KEYS);
 // No mixing: official needs its own adapted scores; an unchecked payload is refused.
 assert.throws(()=>B.buildDraft({...args,computed:deviceTwin(pub),official:pub}),/V_SOURCE_MIXED/);
 assert.throws(()=>B.buildDraft({...args,computed:B.officialComputed(pub),official:JSON.parse(FIX.base_text)}),/OFFICIAL_INVALID/);
 assert.throws(()=>B.buildDraft({...args,computed:null,official:pub}),/V_SOURCE_MIXED/);
 // The state validates and rides in the playbook store (bounded); a broken record or an unknown source does not.
 const st={...B.emptyState(),draft:official};B.validateState(st);const s=memory(),pb=P.empty();pb.target_v1=st;P.write(s,pb);assert.deepEqual(P.read(s).target_v1.draft.official,rec);
 for(const bad of [{...official,v_source:'ELSEWHERE'},{...official,official:{...rec,publication_id:'qgvpub-x'}},{...official,official:{...rec,extra:1}},{...official,official:{...rec,price_basis_date:'2026-02-30'}},{...official,official:{...rec,inputs_as_of:'later'}},{...official,official:null}])
  assert.throws(()=>B.validateState({...B.emptyState(),draft:bad}),/TARGET_V1_STATE_INVALID/);
 B.validateState({...B.emptyState(),draft:{...device,v_source:'DEVICE_TEMPORARY'}});   // web_app records its device source on the draft
});
const u0=()=>wide(40);

test('PR-D adapter: every Universe code reads the record the device path reads (second share class, unplaced TARGET, TARGET of another calc_version)',async()=>{
 assert.deepEqual(Object.fromEntries(PAGE_TARGETS.map(t=>[t.company_id,t.ticker])),{...QO.TARGET_TICKERS},'the reader\'s TARGET tickers are the device catalog');
 const expect={
  // D-CV8 ranks the GOOG/GOOGL issuer through TARGET:googl for both codes (rank_row); the device reads TARGET:googl for GOOGL only
  // and GOOG's own row, and the builder's issuer dedupe keeps the higher total → GOOG with its own scores, not in the old 19.
  target_for_two_share_classes_valid:(pub,c,rows)=>{assert.deepEqual([pub.rows['NASDAQ:GOOG'].rank_row,pub.rows['NASDAQ:GOOGL'].rank_row],['TARGET:googl','TARGET:googl']);
   assert.deepEqual([c.rows['NASDAQ:GOOG'].code,c.rows['NASDAQ:GOOGL'].code],['NASDAQ:GOOG','TARGET:googl']);
   const issuer=rows.filter(r=>r.cik===pub.rows['TARGET:googl'].cik);assert.deepEqual(issuer.map(r=>[r.symbol,r.code,r.total,r.in19]),[['GOOG','NASDAQ:GOOG',pub.rows['NASDAQ:GOOG'].total,false]]);},
  // TARGET:amd LIVE without a total: the publication gives the issuer no rank (rank_row null); the device reads that row → no total,
  // excluded; never NASDAQ:AMD's own row behind it.
  target_live_unplaced_valid:(pub,c,rows)=>{assert.deepEqual([pub.rows['NASDAQ:AMD'].rank,pub.rows['NASDAQ:AMD'].rank_row],[null,null]);assert.ok(Number.isFinite(pub.rows['NASDAQ:AMD'].total));
   assert.deepEqual([c.rows['NASDAQ:AMD'].code,c.rows['NASDAQ:AMD'].v2.total],['TARGET:amd',null]);assert.ok(B.exclusions(rows.find(r=>r.symbol==='AMD')).includes('TOTAL_NOT_AVAILABLE'));},
  // TARGET:amd of another calc_version (shard rotation): the publication ranks NASDAQ:AMD itself; the device still reads the TARGET
  // record (state LIVE) and has no total for it → excluded the same way (TOTAL_NOT_AVAILABLE).
  target_calc_mismatch_valid:(pub,c,rows)=>{assert.equal(pub.rows['NASDAQ:AMD'].rank_row,'NASDAQ:AMD');assert.equal(pub.rows['TARGET:amd'].total_reason,'CALC_VERSION_MISMATCH');
   assert.deepEqual([c.rows['NASDAQ:AMD'].code,c.rows['NASDAQ:AMD'].v2.total],['TARGET:amd',null]);assert.ok(B.exclusions(rows.find(r=>r.symbol==='AMD')).includes('TOTAL_NOT_AVAILABLE'));}};
 for(const[id,check]of Object.entries(expect)){const pub=await casePub(id),inputs=officialInputs(pub),universeCodes=universeOf(pub),args={inputs,universeCodes,existing:['AMD','GOOGL'],date:'2026-10-14',basis:null};
  const c=B.officialComputed(pub),twin=deviceTwin(pub,inputs),byTicker=new Map(Object.values(twin.rows).map(r=>[r.ticker,r.code]));
  for(const code of universeCodes)assert.equal(c.rows[code].code,byTicker.get(code.split(':')[1]),id+' '+code);
  check(pub,c,B.universeRows({...args,computed:c}));
  const{v_source,official:rec,...rest}=B.buildDraft({...args,computed:c,official:pub});assert.equal(v_source,'OFFICIAL_CENTRAL');assert.deepEqual(rest,B.buildDraft({...args,computed:twin}),id+': same draft as the device path on the same scores');
  assert.ok(!rest.pool.some(r=>r.symbol==='GOOGL'||(id!=='target_for_two_share_classes_valid'&&r.symbol==='AMD')),id);}
});

test('PR-D state: the publication record rides only with OFFICIAL_CENTRAL (draft and version); a version keeps all three publication fields',async()=>{
 const pub=await officialPub(),rec=B.officialRecord(pub),pool=[{symbol:'AMD',total:60}],row={date:'2026-10-14',rows:[{symbol:'AMD',pct:5}]};
 const pubFields={publication_id:rec.publication_id,price_basis_date:rec.price_basis_date,official_inputs_as_of:rec.inputs_as_of};
 const state=(draft,versions=[])=>({...B.emptyState(),draft:{created:'2026-10-14',pool,...draft},versions});
 B.validateState(state({v_source:'OFFICIAL_CENTRAL',official:rec},[{...row,v_source:'OFFICIAL_CENTRAL',...pubFields}]));
 for(const[name,bad]of Object.entries({
  device_draft_with_record:state({v_source:'DEVICE_TEMPORARY',official:rec}),untagged_draft_with_record:state({official:rec}),
  device_version_with_publication:state({},[{...row,v_source:'DEVICE_TEMPORARY',...pubFields}]),untagged_version_with_publication:state({},[{...row,...pubFields}]),
  official_version_without_basis_day:state({},[{...row,v_source:'OFFICIAL_CENTRAL',publication_id:rec.publication_id,official_inputs_as_of:rec.inputs_as_of}]),
  device_version_with_basis_day_only:state({},[{...row,v_source:'DEVICE_TEMPORARY',price_basis_date:'2026-10-13'}])}))
  assert.throws(()=>B.validateState(bad),/TARGET_V1_STATE_INVALID/,name);
 // Still readable (web_app's engines record the draft's id on a version, web_app_engines_node_test.js): an OFFICIAL_CENTRAL id without
 // the record. The screen shows no 공식 V value for such a draft and finalize calls it V_SOURCE_CHANGED.
 B.validateState(state({v_source:'OFFICIAL_CENTRAL'},[{...row,v_source:'OFFICIAL_CENTRAL'}]));
 const bare={...state({v_source:'OFFICIAL_CENTRAL'}),answers:[]};assert.ok(B.finalizeBlockers(bare,{date:'2026-10-15',published:null,official:pub}).blockers.includes('V_SOURCE_CHANGED'));
});

test('PR-D use rule at the click: not published / unavailable / invalid / calc differs / stale → no publication, the device draft as before',async()=>{
 const sec=OFFICIAL_CALC,ok=await QO.resolve(served(200),{secCalcVersion:sec,nyToday:'2026-10-14'});assert.equal(ok.ok,true);assert.equal(B.officialRecord(ok.payload).publication_id,JSON.parse(FIX.base_text).publication_id);
 const tampered=FIX.base_text.replace('"price_basis_date":"2026-10-13"','"price_basis_date":"2026-10-12"');
 const cases={OFFICIAL_NOT_PUBLISHED:[served(404),sec,'2026-10-14'],OFFICIAL_UNAVAILABLE:[served(500),sec,'2026-10-14'],OFFICIAL_INVALID:[served(200,tampered),sec,'2026-10-14'],
  OFFICIAL_CALC_VERSION_DIFFERS:[served(200),'qgv2-calc/2026-10-23.2','2026-10-14'],OFFICIAL_STALE:[served(200),sec,'2026-10-16']};
 const u=u0(),device=B.buildDraft({...u,existing:[],date:'2026-10-14'});
 for(const[code,[src,calc,day]]of Object.entries(cases)){const r=await QO.resolve(src,{secCalcVersion:calc,nyToday:day});assert.deepEqual([r.ok,r.reason,r.payload],[false,code,null],code);
  // The screen passes official only when ok; otherwise exactly today's device call and draft (no new key).
  assert.deepEqual(B.buildDraft({...u,existing:[],date:'2026-10-14',official:r.ok?r.payload:null}),device,code);}
 assert.deepEqual(QO.REASONS,Object.keys(cases));
});

test('PR-D finalize: official version records OFFICIAL_CENTRAL + publication; V_SOURCE_CHANGED both ways and on a new publication → regenerate',async()=>{
 const pub=await officialPub(),pub2=await officialPub(FIX.base_text.replace(pub.publication_id,OTHER_ID)),rec=B.officialRecord(pub);assert.equal(B.officialRecord(pub2).publication_id,OTHER_ID);
 // A 15-name device-scored draft stamped with the publication's record (the mini publication has 9 eligible names; the source
 // logic does not depend on the pool), all cards answered; the re-read sec-qgv2.json has the publication's calc_version.
 const u=wide(40),secPub=published({u,calc:OFFICIAL_CALC}),basis=await B.inputBasis(secPub),cfg=passed(OFFICIAL_CALC);
 let device={...B.emptyState(),draft:B.buildDraft({...u,existing:[],date:'2026-10-14',basis})};for(const r of B.currentSelection(device).rows)device=B.answer(device,{symbol:r.symbol,answer:'AGREE',date:'2026-10-14'});
 const stamped={...device,draft:{...device.draft,v_source:'OFFICIAL_CENTRAL',official:rec}};B.validateState(stamped);
 const fb=(state,official,pubSec=secPub)=>B.finalizeBlockers(state,{date:'2026-10-15',published:pubSec,basis,official,cfg});
 // Same source and publication → no new blocker; the version keeps the source, the publication id and its days.
 assert.deepEqual(fb(stamped,pub).blockers,[]);assert.deepEqual(fb(stamped,pub).official,rec);
 const done=B.finalize(stamped,{date:'2026-10-15',published:secPub,basis,official:pub,cfg}),v=done.versions[0];
 assert.deepEqual([v.v_source,v.publication_id,v.price_basis_date,v.official_inputs_as_of,v.calc_version,v.sec_qgv2_as_of],['OFFICIAL_CENTRAL',pub.publication_id,'2026-10-13',pub.times.inputs_as_of,OFFICIAL_CALC,secPub.as_of]);
 B.validateState(done);assert.throws(()=>B.validateState({...done,versions:[{...v,publication_id:'x'}]}),/TARGET_V1_STATE_INVALID/);assert.throws(()=>B.validateState({...done,versions:[{...v,v_source:'X'}]}),/TARGET_V1_STATE_INVALID/);
 // A device draft finalized on the device path: the version is exactly as before (no new key).
 const plain=B.finalize(device,{date:'2026-10-15',published:secPub,basis,cfg}).versions[0];assert.deepEqual(Object.keys(plain).sort(),VERSION_KEYS);assert.equal(plain.v_source,'DEVICE_TEMPORARY');
 assert.deepEqual(B.finalize(device,{date:'2026-10-15',published:secPub,basis,official:null,cfg}).versions[0],plain);
 // Official draft, publication gone / stale / of another calc_version (the caller passes null) → V_SOURCE_CHANGED, a changed basis.
 const gone=fb(stamped,null);assert.deepEqual(gone.blockers,['V_SOURCE_CHANGED']);assert.deepEqual([gone.basis_changed,gone.v_source_changed,gone.official],[true,true,null]);
 assert.deepEqual(fb(stamped,pub,published({u,calc:'qgv2-calc/2026-10-24.1'})).blockers.includes('V_SOURCE_CHANGED'),true,'a publication of another calc_version than the re-read file is not usable');
 // Device draft and a usable publication now → V_SOURCE_CHANGED (the other direction); a new publication id → V_SOURCE_CHANGED.
 assert.deepEqual(fb(device,pub).blockers,['V_SOURCE_CHANGED']);assert.deepEqual(fb(stamped,pub2).blockers,['V_SOURCE_CHANGED']);
 assert.throws(()=>B.finalize(stamped,{date:'2026-10-15',published:secPub,basis,official:pub2,cfg}),e=>e.blockers.join()==='V_SOURCE_CHANGED');
 // An unchecked payload never counts as official.
 assert.deepEqual(fb(device,JSON.parse(FIX.base_text)).blockers,[]);assert.deepEqual(fb(stamped,JSON.parse(FIX.base_text)).blockers,['V_SOURCE_CHANGED']);
 // Regenerate path (the screen's): official gone → device scores, the draft loses the official keys, answers kept, finalize as device.
 const back=B.regenerateDraft(stamped,{...u,existing:[],date:'2026-10-15',basis,official:null});assert.equal(back.state.draft.v_source,undefined);assert.equal(back.state.draft.official,undefined);
 assert.equal(back.carried.length,15);assert.deepEqual(fb(back.state,null).blockers,[]);assert.equal(B.finalize(back.state,{date:'2026-10-15',published:secPub,basis,cfg}).versions[0].v_source,'DEVICE_TEMPORARY');
 // Usable publication now → regenerate from its rows (official draft of the new publication); the change blocker is gone.
 const inputs=officialInputs(pub2),fwd=B.regenerateDraft(stamped,{computed:B.officialComputed(pub2),inputs,universeCodes:universeOf(pub2),existing:[],date:'2026-10-15',basis,official:pub2});
 assert.deepEqual([fwd.state.draft.v_source,fwd.state.draft.official.publication_id],['OFFICIAL_CENTRAL',OTHER_ID]);assert.ok(!fb(fwd.state,pub2).blockers.includes('V_SOURCE_CHANGED'));
 assert.ok(fb(fwd.state,pub2).blockers.includes('TARGET_V1_SHORTFALL'),'the mini publication has fewer than 15 eligible names: shown, nothing relaxed');
 // No number change: the shipped number check stays on its own calc_version, so finalize on the publication's calc_version is still blocked.
 assert.ok(B.finalizeBlockers(stamped,{date:'2026-10-15',published:secPub,basis,official:pub,cfg:CFG}).blockers.includes('NUMBER_CHECK_CALC_VERSION_MISMATCH'));
});

test('PR-D without QgvOfficial on the page (web_app): never official, the device path as before',async()=>{
 const vm=require('node:vm'),fs=require('node:fs'),path=require('node:path'),src=fs.readFileSync(path.join(__dirname,W,'target-v1-builder.js'),'utf8');
 const box={PlaybookEngine:require(W+'playbook-engine.js'),PlaybookConfigDefaults:PCFG,TargetV1ConfigDefaults:CFG,TextEncoder,crypto:globalThis.crypto};vm.createContext(box);vm.runInContext(src,box);
 const WB=box.TargetV1Builder,pub=await officialPub();assert.ok(WB&&WB.V_SOURCES.OFFICIAL_CENTRAL);
 assert.equal(WB.officialComputed(pub),null);assert.equal(WB.officialRecord(pub),null);
 const u=u0();assert.throws(()=>WB.buildDraft({...u,existing:[],date:'2026-10-14',official:pub}),/OFFICIAL_INVALID/);
 const draft=WB.buildDraft({...u,existing:[],date:'2026-10-14'});assert.deepEqual(Object.keys(draft).sort(),DRAFT_KEYS);
 let st={...WB.emptyState(),draft:{...draft,v_source:'OFFICIAL_CENTRAL',official:B.officialRecord(pub)}};
 assert.ok(WB.finalizeBlockers(st,{date:'2026-10-15',published:null,official:pub}).blockers.includes('V_SOURCE_CHANGED'),'an official draft cannot be confirmed without the reader');
});
