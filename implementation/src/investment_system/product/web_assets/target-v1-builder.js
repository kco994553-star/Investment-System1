/* TARGET v1 builder (owner decision 2026-10-14 "QGV v2 채택과 TARGET v1 재구성"): pure, deterministic, device only.
   QGV v2 (QgvScores accessor) is the only score basis. Its total needs V, and V needs this device's prices, so every result here
   is computed in the browser from arguments and never published: no network, no storage, no logging in this module.
   Pipeline: candidate filters (axis coverage, value-trap gate, financial safety) → sector spread (≤ 4 per sub-group) → 30-candidate
   table → final 15 (core 5 × 8% + general 10 × 6%) under PLAYBOOK §16 limits → 3 reasons and 3 numerically checkable invalidation
   conditions per name from template rules → user cards (동의 / 반대 / 모름; 반대 replaces the name with the next-ranked one and the
   limits are checked again) → TARGET v1 version (blocked until the number check of the current calc_version passed) → rule sets R-B / R-C (규칙 지수, no backfill;
   named R-B·R-C by the 2026-10-15 owner decision T-SET so they never clash with the sheet ledger's user sets B/C/D), 3-round transition
   plan and the fixed review rule. T-PRICE (2026-10-15): TV1 judgement names outside the 19 get a price path through the user's own
   sheet (Prices_D) only after the user's confirmed click; the pure helpers here only list the symbols and shape the RAM series.
   2026-10-15 owner supplement: financial safety NA excludes a name from the candidates; a name shortfall (< 15) is shown and blocks
   finalize (no relaxing, no re-adding); finalize re-checks the LATEST sec-qgv2.json at that moment (calc_version, as_of freshness,
   Q·G coverage ≥ 90%) and needs a passed 10-company number check for the SAME calc_version; until TARGET v1 is finalized (target:
   2nd week of 2026-11) a rebalance round shows risk-code checks only, never a per-name list.
   2026-10-15 evening: freshness is each valued row's SEC acquisition time (acquired_at, 7 days), never the file as_of; a normal NA
   row (no value, NA reason) never blocks, a valued row of another calculation is CALC_VERSION_MIXED; the draft records its input
   basis (calc_version, as_of, per-shard newest acquired_at) and a changed basis at finalize regenerates the draft (answers kept
   for the same symbols only); the selected names' financial safety is re-checked against the latest file. Every number comes from TargetV1ConfigDefaults (qgv/target_v1_builder_v0.json,
   v0 · UNCALIBRATED) or PlaybookConfigDefaults. Missing is null / NA, never 0. No order function; no buy or sell wording. */
(function(root,factory){const node=typeof module==='object'&&module.exports;
 const api=factory(node?require('./playbook-engine.js'):root.PlaybookEngine,node?require('./playbook-config-defaults.js'):root.PlaybookConfigDefaults,
  node?require('./target-v1-config-defaults.js'):root.TargetV1ConfigDefaults,node?()=>require('./virtual-trading.js'):()=>root.VirtualTrading,node?()=>require('./qgv-v2.js'):()=>root.QgvV2);
 if(node)module.exports=api;else root.TargetV1Builder=api;})(typeof globalThis==='object'?globalThis:this,function(E,PCFG,CFG,virtualTrading,qgvV2){
'use strict';
const SCHEMA='target-v1-builder/1',DAY=/^\d{4}-\d{2}-\d{2}$/,SYMBOL=/^[A-Za-z0-9][A-Za-z0-9.\-=]{0,31}$/,UNIVERSE=/^(?:NYSE|NASDAQ|BATS):([A-Z0-9][A-Z0-9.\-]{0,15})$/;
const ANSWERS=['AGREE','DISAGREE','UNKNOWN'];
const object=v=>v!==null&&typeof v==='object'&&!Array.isArray(v),finite=v=>typeof v==='number'&&Number.isFinite(v);
const round=(v,d=2)=>finite(v)?Math.round(v*10**d)/10**d:null;
const key=t=>String(t||'').replaceAll('.','-').toUpperCase();
function fail(code){throw Error(code);}
function validDay(v){return typeof v==='string'&&DAY.test(v)&&new Date(v+'T00:00:00Z').toISOString().slice(0,10)===v;}
function text(v,max=12000){return typeof v==='string'&&v.length<=max&&!/[\x00-\x1f\x7f]/.test(v);}
const byTotal=(a,b)=>b.total-a.total||(a.symbol<b.symbol?-1:a.symbol>b.symbol?1:0);

/* ---------- coverage (public file counts) ---------- */
// Q n/504, G n/504 from the public sec-qgv2.json (Qgv2Inputs records): US Universe rows only (TARGET:<id> rows are not counted).
function coverage(inputs,cfg=CFG){
 const size=cfg.coverage.universe_size;let q=0,g=0;
 for(const[code,r]of Object.entries(object(inputs)&&object(inputs.records)?inputs.records:{})){if(code.startsWith('TARGET:'))continue;if(finite(r?.qg_axes?.Q?.score))q++;if(finite(r?.qg_axes?.G?.score))g++;}
 const ready=!!inputs&&q/size>=cfg.coverage.ready_min_ratio&&g/size>=cfg.coverage.ready_min_ratio;
 return{q,g,size,ready,label:ready?null:cfg.coverage.draft_label+' (Q '+q+'/'+size+', G '+g+'/'+size+')'};
}

/* ---------- sub-group (PLAYBOOK §7 / §17 #20) ---------- */
// Assignment or §17 SIC sub-group first, then the D-22 SIC → ETF map through PlaybookEngine.sectorFor (XLK → 기술 하드웨어,
// XLI → 일반 산업, a unique ETF → its §7 row), else the v2 SIC industry group ('industry:<group>') so spreading still applies.
function subgroupOf(symbol,sic,industry,cfg=CFG,pcfg=PCFG){
 let s=E.sectorFor(pcfg,symbol,null,sic);if(s.sector)return{subgroup:s.sector,sector:s.sector,source:s.source};
 let etf=null;try{const VT=virtualTrading();etf=VT&&sic!==null&&sic!==undefined?VT.sectorBenchmark(String(sic)).etf:null;}catch(_){etf=null;}
 if(etf==='SEMIS_THEME_SMH_ELSE_XLI')etf='XLI';
 if(etf&&etf!=='SPY'){s=E.sectorFor(pcfg,symbol,etf,sic);if(s.sector)return{subgroup:s.sector,sector:s.sector,source:s.source};}
 return{subgroup:cfg.sector_spread.industry_group_prefix+(industry||'unknown'),sector:null,source:industry?'V2_INDUSTRY_GROUP':'NOT_AVAILABLE'};
}
function groupOf(subgroup,pcfg=PCFG){for(const g of pcfg.portfolio_limits.combined_groups)if(g.sectors.includes(subgroup))return g.id;return subgroup;}

/* ---------- financial safety ---------- */
// FAIL: a known net debt/EBITDA ≥ 3 or a known interest coverage < 3. PASS: both known and inside the thresholds.
// UNKNOWN (a value missing, nothing failing): excluded from the candidates (2026-10-15 supplement; re-evaluated on the next build).
function safety(metrics,cfg=CFG){
 const fs=cfg.filters.financial_safety,nd=finite(metrics?.net_debt_to_ebitda)?metrics.net_debt_to_ebitda:null,ic=finite(metrics?.interest_coverage)?metrics.interest_coverage:null;
 const failed=(nd!==null&&nd>=fs.net_debt_to_ebitda_fail_at_or_above)||(ic!==null&&ic<fs.interest_coverage_fail_below);
 const passed=nd!==null&&ic!==null&&!failed;
 return{state:failed?'FAIL':passed?'PASS':'UNKNOWN',net_debt_to_ebitda:nd,interest_coverage:ic};
}

/* ---------- V factor count (user decision 2026-10-23) ---------- */
/* 「가격이 일부만 있을 때 V가 '몇 개 요인으로 계산됐는지'(예: 3/5)를 리더보드와 TARGET 후보 표에 표시하고, V3·V4가 빠진 V로 TARGET v1
   후보를 확정하지 않는다(초안은 가능, 표시 필수).」 The 5 V factors in QgvV2.WEIGHTS.V order (V1..V5); a factor counts when its score
   is a number. A V that is null counts 0/5 (never filled). V3 (v_vs_industry) and V4 (v_vs_own_history) are required for finalize
   (finalizeBlockers → V_FACTORS_V3_V4_MISSING); a draft without them stays allowed and shows the marker. Display and gate only: no
   score, weight, selection count or config number changes. Kept in code (no config field) as the decision needs no number. */
const V_FACTORS=Object.freeze(['v_earnings_yield','v_fcf_yield','v_vs_industry','v_vs_own_history','v_expectation_check']),V_REQUIRED=Object.freeze(['v_vs_industry','v_vs_own_history']);
function vFactors(v2){const f=object(v2?.factors)?v2.factors:{},have=finite(v2?.v)?V_FACTORS.filter(k=>finite(f[k]?.score)):[];
 return{n:have.length,total:V_FACTORS.length,missing:V_FACTORS.filter(k=>!have.includes(k)),required_ok:V_REQUIRED.every(k=>have.includes(k))};}
// A draft row's V lacks V3 or V4. A row from a draft built before 2026-10-23 (no v_missing) cannot show it → counted as lacking.
const vIncomplete=r=>!Array.isArray(r?.v_missing)||V_REQUIRED.some(k=>r.v_missing.includes(k));

/* ---------- rows from the accessor ---------- */
/* computed: QgvScores.compute result over Universe identities (RAM, with device quotes); inputs: Qgv2Inputs result (public);
   universeCodes: ['NYSE:XYZ', ...]; existing: the 19 TARGET tickers. → every Universe row with the fields the pipeline uses. */
function universeRows({computed,inputs,universeCodes=[],existing=[],cfg=CFG,pcfg=PCFG}){
 const byTicker=new Map();for(const r of Object.values(object(computed?.rows)?computed.rows:{}))if(r&&r.ticker)byTicker.set(key(r.ticker),r);
 const records=object(inputs?.records)?inputs.records:{},have=new Set(existing.map(key)),seen=new Map(),out=[];
 for(const code of universeCodes){const m=typeof code==='string'?UNIVERSE.exec(code):null;if(!m)continue;const symbol=m[1],row=byTicker.get(key(symbol));
  const rec=(row&&row.code&&records[row.code])||records[code]||null,v2=row?.v2||null;if(!v2||v2.reference_only===true)continue;
  // Identity-conflict stop (Qgv2Inputs identity_withdrawn, #285/#289): the Universe code's own record or the record the score used.
  // A stopped row keeps no total (so it never takes a rank) and never borrows the score of another row with the same ticker.
  const withdrawn=records[code]?.identity_withdrawn===true||rec?.identity_withdrawn===true;
  const metrics=object(rec?.metrics)?rec.metrics:{},sic=rec?.sic??null,industry=rec?.industry_group??null,sg=subgroupOf(symbol,sic,industry,cfg,pcfg);
  const axisOk=a=>{const x=v2.axes?.[a];return!!x&&finite(x.score)&&finite(x.weight_available)&&x.weight_available>=cfg.filters.axis_min_weight;};
  const factorScores={};for(const[f,x]of Object.entries(object(v2.factors)?v2.factors:{}))if(finite(x?.score))factorScores[f]=x.score;const vf=vFactors(v2);
  const r={symbol,code,cik:rec?.cik??null,total:!withdrawn&&finite(v2.total)?v2.total:null,q:finite(v2.q)?v2.q:null,g:finite(v2.g)?v2.g:null,v:finite(v2.v)?v2.v:null,
   q_pct:finite(v2.q_industry_percentile)?v2.q_industry_percentile:null,factors_n:v2.factors_available??0,factors_total:v2.factors_total??15,v_n:vf.n,v_total:vf.total,v_missing:vf.missing,
   axes_ok:Object.fromEntries(cfg.filters.axes.map(a=>[a,axisOk(a)])),value_trap:v2.value_trap_gate===true,types:Array.isArray(v2.selected_types)?[...v2.selected_types]:[],
   subgroup:sg.subgroup,sector:sg.sector,subgroup_source:sg.source,industry,sic,safety:safety(metrics,cfg),metrics,factor_scores:factorScores,in19:have.has(key(symbol)),withdrawn,rank:null,industry_rank:null,industry_size:null};
  // One point per issuer (second share class of the same CIK): keep the higher total, then the first code.
  if(cfg.score_basis.dedupe_issuer&&r.cik){const prior=seen.get(r.cik);if(prior){if((r.total??-1)>(prior.total??-1)){out[out.indexOf(prior)]=r;seen.set(r.cik,r);}continue;}seen.set(r.cik,r);}
  out.push(r);}
 // Overall rank and rank within the v2 industry group, among rows with a total.
 const scored=out.filter(r=>finite(r.total)).sort(byTotal),groups={},sizes={};scored.forEach((r,i)=>{r.rank=i+1;if(r.industry){groups[r.industry]=(groups[r.industry]||0)+1;r.industry_rank=groups[r.industry];}});
 for(const r of scored)if(r.industry)sizes[r.industry]=(sizes[r.industry]||0)+1;for(const r of scored)if(r.industry)r.industry_size=sizes[r.industry];
 return out;
}
// Step 1: exclusion reasons (empty = eligible). A row stopped for an identity conflict (Qgv2Inputs identity_withdrawn: a withdrawn
// TARGET issuer's same-CIK codes or a withdrawn Universe code) is used nowhere and carries only that reason.
function exclusions(row,cfg=CFG){
 if(row.withdrawn===true)return['IDENTITY_CONFLICT_WITHDRAWN'];
 const out=[];if(!finite(row.total))out.push('TOTAL_NOT_AVAILABLE');
 if(cfg.filters.axes.some(a=>!row.axes_ok[a]))out.push('AXIS_COVERAGE_LOW');
 if(cfg.filters.exclude_value_trap_gate&&row.value_trap)out.push('VALUE_TRAP_GATE');
 if(row.safety.state==='FAIL')out.push('FINANCIAL_SAFETY_FAIL');
 else if(row.safety.state==='UNKNOWN'&&cfg.filters.financial_safety.missing_for_exclusion==='EXCLUDED')out.push(cfg.filters.financial_safety.missing_reason);
 return out;
}
// Step 2a: rank by total with at most max names per sub-group.
function spread(rows,max=CFG.sector_spread.max_per_subgroup,limit=Infinity){const per={},out=[];for(const r of [...rows].sort(byTotal)){if(out.length>=limit)break;if((per[r.subgroup]||0)>=max)continue;per[r.subgroup]=(per[r.subgroup]||0)+1;out.push(r);}return out;}
const factorRatio=r=>r.factors_total>0?r.factors_n/r.factors_total:0;
const coreEligible=(r,cfg=CFG)=>factorRatio(r)>=cfg.selection.core.min_factor_ratio&&(!cfg.selection.core.require_financial_safety_pass||r.safety==='PASS'||r.safety?.state==='PASS');

/* Step 2b + 4: the final selection. mode 'TARGET': core (first `core.count` in total order with factors ≥ 80% and financial safety
   PASS) at core.pct, the rest at general.pct. mode 'EQUAL' (set B): 100 / count each. A name is skipped when its sub-group already
   has max names or its §16 group would exceed the group cap; the next-ranked name takes the place. Shortfall stays cash. */
function select(pool,{exclude=[],mode='TARGET',cfg=CFG,pcfg=PCFG}={}){
 const S=cfg.selection,L=pcfg.portfolio_limits,max=cfg.sector_spread.max_per_subgroup,skip=new Set(exclude.map(key)),count=S.count;
 const rows=[],skipped=[],per={},groups={};let core=0;
 for(const r of [...pool].sort(byTotal)){
  if(rows.length>=count)break;if(skip.has(key(r.symbol)))continue;
  if((per[r.subgroup]||0)>=max){skipped.push({symbol:r.symbol,reason:'SUBGROUP_MAX'});continue;}
  let grade,pct;if(mode==='EQUAL'){grade='EQUAL';pct=100/count;}else if(core<S.core.count&&coreEligible(r,cfg)){grade=S.core.id;pct=S.core.pct;}else{grade=S.general.id;pct=S.general.pct;}
  const g=groupOf(r.subgroup,pcfg);if((groups[g]||0)+pct>L.sector_group_max_pct+1e-9){skipped.push({symbol:r.symbol,reason:'SECTOR_GROUP_MAX'});continue;}
  if(pct>L.single_max_pct){skipped.push({symbol:r.symbol,reason:'SINGLE_MAX'});continue;}
  if(grade===S.core.id)core++;per[r.subgroup]=(per[r.subgroup]||0)+1;groups[g]=(groups[g]||0)+pct;rows.push({...r,grade,pct});
 }
 let sum=0;for(const r of rows)sum+=r.pct;const cash=round(Math.max(0,S.sum_pct-sum),4);
 return{rows,cash_pct:cash,skipped,core_count:core,limits:limits(rows,cash,pcfg)};
}
// §16 re-check (PlaybookEngine.portfolioLimits) with the sub-group as the sector (semis + equipment combined by the config).
function limits(rows,cash,pcfg=PCFG){return E.portfolioLimits(pcfg,rows.map(r=>({symbol:r.symbol,sector:r.subgroup,pct:r.pct})),cash);}

/* ---------- Step 5: reasons and invalidation conditions ---------- */
// Korean subject particle for a metric label (이 after a final consonant, else 가); a trailing '(…)' is ignored.
function josa(label){const t=String(label).replace(/\([^)]*\)\s*$/,'').trim(),c=t.charCodeAt(t.length-1);if(c>=0xac00&&c<=0xd7a3)return(c-0xac00)%28?'이':'가';return/[LMNR]$/i.test(t)?'이':'가';}
const fmt=(v,unit)=>unit==='pct'?(v*100).toFixed(1)+'%':unit==='x'?v.toFixed(2)+'배':v.toFixed(1);
function threshold(m,current){
 if(m.rule==='RELATIVE')return current>0?current*m.factor:null;
 if(m.rule==='FLOOR_RELATIVE')return current>0?Math.max(m.floor,current*m.factor):null;
 if(m.rule==='DELTA')return current+m.delta;
 if(m.rule==='FIXED')return m.value;return null;
}
/* Deterministic: factors sorted by score (desc, config order on ties); a factor gives a template only when its metric value is
   known (and the threshold rule applies to it). Up to `count` from the strongest; the fallback templates fill the rest. */
function templates(row,cfg=CFG,pcfg=PCFG){
 const T=cfg.templates,order=T.factors.map(f=>f.factor),scored=T.factors.filter(f=>finite(row.factor_scores?.[f.factor])).sort((a,b)=>row.factor_scores[b.factor]-row.factor_scores[a.factor]||order.indexOf(a.factor)-order.indexOf(b.factor));
 const reasons=[],invalidations=[];
 for(const f of scored){if(reasons.length>=T.count)break;const score=row.factor_scores[f.factor];
  for(const m of f.metrics){const current=m.metric==='SCORE'?score:(finite(row.metrics?.[m.metric])?row.metrics[m.metric]:null);if(current===null)continue;
   if(m.direction==='lower'&&m.rule==='FIXED'&&current>=m.value)continue;let x=threshold(m,current);if(x===null||!finite(x))continue;if(m.metric==='SCORE')x=Math.max(0,x);
   const op=m.direction==='higher'?'LT':'GT';
   reasons.push(f.ko+' 점수 '+score.toFixed(1)+' · '+m.label+' '+fmt(current,m.unit));
   invalidations.push({text:m.label+josa(m.label)+' '+fmt(x,m.unit)+(op==='LT'?' 아래로 내려가면':' 이상이 되면')+' (현재 '+fmt(current,m.unit)+')',factor:f.factor,metric:m.metric,op:op==='LT'?'LT':'GTE',threshold:round(x,6),current:round(current,6),unit:m.unit,rule:m.rule});
   break;}}
 for(const fb of T.fallback){if(reasons.length>=T.count)break;
  if(fb.id==='TOTAL_RANK'&&finite(row.total)&&finite(row.rank)){const lim=cfg.candidates.count;reasons.push(fb.reason.replace('{total}',row.total.toFixed(1)).replace('{rank}',row.rank));invalidations.push({text:fb.invalidation.replace('{limit}',lim).replace('{rank}',row.rank),factor:null,metric:'v2_rank',op:'GT',threshold:lim,current:row.rank,unit:'rank',rule:'FIXED'});}
  else if(fb.id==='Q_INDUSTRY_PCT'&&finite(row.q_pct)){const lim=pcfg.v2_adjustments.value_trap_gate.q_industry_pct_bottom;reasons.push(fb.reason.replace('{value}',row.q_pct.toFixed(1)));invalidations.push({text:fb.invalidation.replace('{limit}',lim).replace('{value}',row.q_pct.toFixed(1)),factor:null,metric:'q_industry_percentile',op:'LTE',threshold:lim,current:round(row.q_pct,6),unit:'pt',rule:'FIXED'});}
  else if(fb.id==='G_AXIS'&&finite(row.g)){const lim=Math.max(0,row.g+fb.delta);reasons.push(fb.reason.replace('{value}',row.g.toFixed(1)));invalidations.push({text:fb.invalidation.replace('{limit}',lim.toFixed(1)).replace('{value}',row.g.toFixed(1)),factor:null,metric:'g_axis',op:'LT',threshold:round(lim,6),current:round(row.g,6),unit:'pt',rule:'DELTA'});}}
 return{reasons,invalidations};
}
// An invalidation condition checked against a current value: true (occurred) / false / null (unknown, never assumed).
function invalidated(cond,current){if(!finite(current)||!finite(cond?.threshold))return null;return cond.op==='LT'?current<cond.threshold:cond.op==='LTE'?current<=cond.threshold:cond.op==='GT'?current>cond.threshold:current>=cond.threshold;}

/* ---------- draft (frozen ranking stored on this device) ---------- */
function poolRow(r,cfg=CFG,pcfg=PCFG){const t=templates(r,cfg,pcfg);return{symbol:r.symbol,code:r.code,subgroup:r.subgroup,sector:r.sector,industry:r.industry,types:r.types.slice(0,4),
 q:round(r.q),g:round(r.g),v:round(r.v),total:round(r.total,4),q_pct:round(r.q_pct),rank:r.rank,industry_rank:r.industry_rank,industry_size:r.industry_size,factors_n:r.factors_n,factors_total:r.factors_total,
 v_n:r.v_n,v_total:r.v_total,v_missing:[...r.v_missing],in19:r.in19,safety:r.safety.state,reasons:t.reasons,invalidations:t.invalidations};}
// basis: inputBasis() of the published file the draft was built from (null when it could not be read → regenerated at finalize).
function buildDraft({computed,inputs,universeCodes,existing,date,basis=null,cfg=CFG,pcfg=PCFG}){
 if(!validDay(date))fail('DATE_INVALID');if(computed?.v2_state!=='READY')fail('QGV2_NOT_READY');
 const all=universeRows({computed,inputs,universeCodes,existing,cfg,pcfg}),eligible=[],excluded={},excludedRows=[];
 for(const r of all){const why=exclusions(r,cfg);if(why.length){for(const w of why)excluded[w]=(excluded[w]||0)+1;excludedRows.push({symbol:r.symbol,total:round(r.total,4),reasons:why,safety:r.safety.state});}else eligible.push(r);}
 const pool=eligible.sort(byTotal).slice(0,cfg.candidates.pool_size).map(r=>poolRow(r,cfg,pcfg));
 excludedRows.sort((a,b)=>(b.total??-1)-(a.total??-1)||(a.symbol<b.symbol?-1:1));
 return{created:date,basis:object(basis)?{...basis}:null,config_version:cfg.config_version,profile_id:computed.profile?.id||null,v2_as_of:computed.v2_as_of||null,coverage:coverage(inputs,cfg),
  universe_rows:all.length,eligible_count:eligible.length,excluded_counts:excluded,excluded:excludedRows.slice(0,cfg.candidates.excluded_shown),pool};
}
// Step 3: the 30-candidate table rows.
function candidates(draft,cfg=CFG){return spread(draft?.pool||[],cfg.sector_spread.max_per_subgroup,cfg.candidates.count);}

/* ---------- device state (inside the playbook store under target_v1; backed up with it) ---------- */
// rule_b / rule_c: the R-B / R-C rule-index definitions (storage keys stay identifier-safe for the playbook store).
// price_symbols: Worker symbols the user added to the own sheet's Prices_D for TV1 scoring (symbols only, never a price).
function emptyState(){return{schema:SCHEMA,draft:null,answers:[],versions:[],rule_b:[],rule_c:null,price_symbols:[]};}
const STATE_KEYS='answers,draft,price_symbols,rule_b,rule_c,schema,versions',LEGACY_KEYS='answers,draft,schema,set_b,set_c,versions',PRICE_SYMBOL=/^[A-Z0-9][A-Z0-9.=\-]{0,15}$/;
// Returns the state in the current layout. The first #248 layout (set_b / set_c, no price_symbols) is read as R-B / R-C.
function validateState(input){
 if(!object(input)||input.schema!==SCHEMA)fail('TARGET_V1_STATE_INVALID');
 const keys=Object.keys(input).sort().join(',');let v;
 if(keys===STATE_KEYS)v=input;else if(keys===LEGACY_KEYS){const{set_b,set_c,...rest}=input;v={...rest,rule_b:set_b,rule_c:set_c,price_symbols:[]};}else fail('TARGET_V1_STATE_INVALID');
 if(!Array.isArray(v.answers)||!Array.isArray(v.versions)||!Array.isArray(v.rule_b)||!(v.draft===null||object(v.draft))||!(v.rule_c===null||object(v.rule_c))||!Array.isArray(v.price_symbols))fail('TARGET_V1_STATE_INVALID');
 if(v.price_symbols.length>CFG.scoring_prices.max_symbols||new Set(v.price_symbols).size!==v.price_symbols.length||v.price_symbols.some(s=>typeof s!=='string'||!PRICE_SYMBOL.test(s)))fail('TARGET_V1_STATE_INVALID');
 for(const a of v.answers)if(!object(a)||!SYMBOL.test(a.symbol)||!ANSWERS.includes(a.answer)||!validDay(a.date)||!text(a.reason,200)||(a.answer==='DISAGREE'&&!a.reason.trim()))fail('TARGET_V1_STATE_INVALID');
 if(v.draft&&(!validDay(v.draft.created)||!Array.isArray(v.draft.pool)||v.draft.pool.some(r=>!object(r)||!SYMBOL.test(r.symbol)||!finite(r.total))))fail('TARGET_V1_STATE_INVALID');
 if(v.draft&&v.draft.basis!==undefined&&v.draft.basis!==null&&(!object(v.draft.basis)||!(v.draft.basis.shards===undefined||text(v.draft.basis.shards,12000))||!(v.draft.basis.type_scope===undefined||v.draft.basis.type_scope===null||text(v.draft.basis.type_scope,100))||!(v.draft.basis.withdrawn===undefined||text(v.draft.basis.withdrawn,12000))))fail('TARGET_V1_STATE_INVALID');
 for(const x of v.versions)if(!object(x)||!validDay(x.date)||!Array.isArray(x.rows)||x.rows.some(r=>!SYMBOL.test(r?.symbol)||!finite(r.pct)))fail('TARGET_V1_STATE_INVALID');
 for(const s of v.rule_b)if(!object(s)||!validDay(s.date)||!Array.isArray(s.rows)||s.rows.some(r=>!SYMBOL.test(r?.symbol)||!finite(r.pct)))fail('TARGET_V1_STATE_INVALID');
 if(v.rule_c&&(!validDay(v.rule_c.start)||!text(v.rule_c.version,20)))fail('TARGET_V1_STATE_INVALID');
 return v;
}
function latestAnswers(state){const out=new Map();for(const a of state?.answers||[])out.set(key(a.symbol),a);return out;}
/* The current selection after the user's answers: every 반대 name is excluded and the next-ranked name takes its place under the
   same constraints (limits re-checked by select()). pending = selected names without an answer yet. */
function currentSelection(state,cfg=CFG,pcfg=PCFG){
 const answers=latestAnswers(state),rejected=[...answers.values()].filter(a=>a.answer==='DISAGREE').map(a=>a.symbol);
 const sel=select(state?.draft?.pool||[],{exclude:rejected,cfg,pcfg}),pending=sel.rows.filter(r=>!answers.has(key(r.symbol))).map(r=>r.symbol);
 // Name shortfall: fewer than selection.count names pass — shown with its reasons and finalize stays blocked (nothing relaxed).
 const shortfall=Math.max(0,cfg.selection.count-sel.rows.length),why={};if(shortfall){for(const x of sel.skipped)why[x.reason]=(why[x.reason]||0)+1;if(rejected.length)why.USER_DISAGREE=rejected.length;for(const[k,v]of Object.entries(state?.draft?.excluded_counts||{}))why[k]=(why[k]||0)+v;}
 return{...sel,rejected,pending,shortfall,shortfall_reasons:why,answers:Object.fromEntries([...answers.entries()].map(([k,a])=>[k,a])),complete:sel.rows.length>0&&pending.length===0};
}
function answer(state,{symbol,answer:kind,reason='',date},cfg=CFG){
 if(!state?.draft)fail('TARGET_V1_DRAFT_REQUIRED');if(!ANSWERS.includes(kind))fail('TARGET_V1_ANSWER_INVALID');if(!validDay(date))fail('DATE_INVALID');
 const spec=cfg.cards.answers.find(a=>a.id===kind),why=typeof reason==='string'?reason.trim():'';
 if(spec.reason_required&&!why)fail('DISAGREE_REASON_REQUIRED');if(!text(why,spec.reason_max||200))fail('REASON_INVALID');
 const sel=currentSelection(state,cfg);if(!sel.rows.some(r=>key(r.symbol)===key(symbol)))fail('TARGET_V1_NOT_SELECTED');
 // Latest answer per name only (the full history is in the playbook judgement records).
 return{...state,answers:[...state.answers.filter(a=>key(a.symbol)!==key(symbol)),{symbol,answer:kind,reason:kind==='UNKNOWN'?(why||spec.memo):why,date}]};
}
// One judgement record per card response for the playbook store (scored later like every record, rejected names included).
function judgementRecord({row,answer:kind,reason='',date,id},cfg=CFG){
 const spec=cfg.cards.answers.find(a=>a.id===kind);if(!spec)fail('TARGET_V1_ANSWER_INVALID');
 return{id:id||('TV1-'+date+'-'+row.symbol+'-'+kind),date,symbol:row.symbol,primary_code:cfg.cards.record_primary_code,secondary_codes:[],type:row.grade||'CANDIDATE',sector:row.subgroup||null,
  thresholds:{v2_total:row.total,q:row.q,g:row.g,v:row.v,rank:row.rank,industry_rank:row.industry_rank,pct:row.pct??null,config_version:cfg.config_version},
  checks:[...row.reasons.map(t=>({code:'REASON',text:t})),...row.invalidations.map(c=>({code:'INVALIDATION',text:c.text,metric:c.metric,op:c.op,threshold:c.threshold}))],
  ai_summary:'',verdict:spec.verdict,action:{kind:spec.action},next_check_date:null,memo:kind==='UNKNOWN'?(reason||spec.memo):reason};
}
/* ---------- finalize gate (2026-10-15 supplement): re-checked at the moment finalize runs ---------- */
const CALC_VERSION=/^qgv2-calc\/\d{4}-\d{2}-\d{2}\.\d{1,4}$/;
function axisScore(r,a){const ax=object(r?.axes)?r.axes:object(r?.qg_axes)?r.qg_axes:{},v=ax[a]?.score;return finite(v)&&v>=0&&v<=100?v:null;}
/* The LATEST published sec-qgv2.json payload (re-read by the caller at finalize; never the draft-time inputs) → {ok, reasons}.
   (a) file calc_version present (else CALC_VERSION_MISSING); a row WITH a value (Q or G score, or LIVE / STALE) must carry the
   file calc_version, and a row without a value is a normal NA when it has an NA reason and no calc_version or the file's one —
   anything else is CALC_VERSION_MIXED; (b) every valued row's acquired_at within finalize_check.freshness_max_days of the finalize
   date (the file as_of never counts: a regenerated file is not fresher data) → ROW_DATA_STALE; (c) Q and G scored rows each ≥
   universe_size × coverage.ready_min_ratio (NA rows stay in the denominator). TARGET:<id> rows are not counted. */
function publishedCheck(payload,{date,cfg=CFG}={}){
 const F=cfg.finalize_check,size=cfg.coverage.universe_size,min=cfg.coverage.ready_min_ratio,base={calc_version:null,as_of:null,q:0,g:0,size,rows:0,na_rows:0,mixed_rows:0,stale_rows:0,oldest_acquired:null};
 if(!object(payload)||!object(payload.records))return{...base,ok:false,reasons:['SEC_QGV2_NOT_AVAILABLE']};
 const calc=typeof payload.calc_version==='string'&&CALC_VERSION.test(payload.calc_version)?payload.calc_version:null,reasons=[];
 const end=validDay(date)?Date.parse(date+'T23:59:59Z'):NaN,limit=end-F.freshness_max_days*86400000;let q=0,g=0,rows=0,na=0,mixed=0,stale=0,oldest=null;
 for(const[code,r]of Object.entries(payload.records)){if(code.startsWith('TARGET:'))continue;rows++;const rv=object(r)&&typeof r.calc_version==='string'?r.calc_version:null;
  const qs=axisScore(r,'Q'),gs=axisScore(r,'G'),valued=qs!==null||gs!==null||['LIVE','STALE'].includes(r?.state);if(qs!==null)q++;if(gs!==null)g++;
  if(valued){if(rv===null||rv!==calc)mixed++;const t=typeof r.acquired_at==='string'?Date.parse(r.acquired_at):NaN;if(!Number.isFinite(t)||!(t>=limit))stale++;if(Number.isFinite(t)&&(oldest===null||t<Date.parse(oldest)))oldest=r.acquired_at;}
  else{const reason=Array.isArray(r?.reason_codes)&&r.reason_codes.length>0;if(reason&&(rv===null||rv===calc))na++;else mixed++;}}
 if(F.calc_version_required&&calc===null)reasons.push('CALC_VERSION_MISSING');else if(mixed>0)reasons.push('CALC_VERSION_MIXED');
 if(!Number.isFinite(end))reasons.push('DATE_INVALID');else if(stale>0)reasons.push('ROW_DATA_STALE');
 if(q/size<min)reasons.push('Q_COVERAGE_LOW');if(g/size<min)reasons.push('G_COVERAGE_LOW');
 return{ok:reasons.length===0,reasons,calc_version:calc,as_of:typeof payload.as_of==='string'?payload.as_of:null,q,g,size,rows,na_rows:na,mixed_rows:mixed,stale_rows:stale,oldest_acquired:oldest};
}
/* Input basis of a published payload: calc_version, file as_of and the newest acquired_at per shard (shard = sha256(cik) mod
   shard_count, the daily partition rule of tools/published_coverage.py). Async (Web Crypto digest); counts and times only.
   type_scope (owner decision 2026-10-17 item 4): the device type-application scope the scores use (QgvV2.TYPE_SCOPE, = QgvScores
   basis.type_scope); calc_version stays the raw-metric version. null when QgvV2 is not on the page.
   withdrawn (owner instruction 2026-10-17 item 3, #285 / #289): the identity-conflict withdrawal rows of the file, as sorted
   'records' codes and 'TARGET:<id>' ids ('' when none). A withdrawal row has no acquired_at, so it can leave the shard times
   unchanged; listing it here makes a new withdrawal a basis change, and the regenerated draft drops the stopped rows. */
const WITHDRAWN_REASON='IDENTITY_CONFLICT_WITHDRAWN';
const isWithdrawal=r=>object(r)&&(Object.hasOwn(r,'detected_at')||Array.isArray(r.reason_codes)&&r.reason_codes.includes(WITHDRAWN_REASON));
function withdrawnList(payload){const out=[];for(const[code,r]of Object.entries(payload.records))if(isWithdrawal(r))out.push(code);
 for(const[id,r]of Object.entries(object(payload.target)?payload.target:{}))if(isWithdrawal(r))out.push('TARGET:'+id);return [...new Set(out)].sort().join('|');}
function deviceTypeScope(){try{const v=qgvV2()?.TYPE_SCOPE;return typeof v==='string'?v:null;}catch(_){return null;}}
async function sha256Hex(text){const d=await globalThis.crypto.subtle.digest('SHA-256',new TextEncoder().encode(text));return [...new Uint8Array(d)].map(b=>b.toString(16).padStart(2,'0')).join('');}
async function inputBasis(payload,{digest=sha256Hex,typeScope=deviceTypeScope()}={}){
 if(!object(payload)||!object(payload.records))return null;
 const count=Number.isInteger(payload.shard_count)&&payload.shard_count>=1&&payload.shard_count<=366?payload.shard_count:null,newest={};
 if(count)for(const[code,r]of Object.entries(payload.records)){if(code.startsWith('TARGET:')||!object(r)||typeof r.cik!=='string'||!r.cik||typeof r.acquired_at!=='string')continue;const t=Date.parse(r.acquired_at);if(!Number.isFinite(t))continue;
  const shard=Number(BigInt('0x'+await digest(r.cik))%BigInt(count));if(!newest[shard]||t>Date.parse(newest[shard]))newest[shard]=r.acquired_at;}
 return{calc_version:typeof payload.calc_version==='string'&&CALC_VERSION.test(payload.calc_version)?payload.calc_version:null,as_of:typeof payload.as_of==='string'?payload.as_of:null,shard_count:count,
  shards:Object.keys(newest).map(Number).sort((a,b)=>a-b).map(k=>k+'='+newest[k]).join('|'),type_scope:typeof typeScope==='string'?typeScope:null,withdrawn:withdrawnList(payload)};
}
// The draft's input basis differs from the latest (calc_version, type_scope, withdrawal rows, shard count or any shard's newest
// acquisition). A draft basis without type_scope or withdrawn (built before those ids existed) counts as changed.
function basisChanged(draftBasis,latest){if(!object(draftBasis)||!object(latest))return true;return draftBasis.calc_version!==latest.calc_version||draftBasis.type_scope!==latest.type_scope||draftBasis.withdrawn!==latest.withdrawn||draftBasis.shard_count!==latest.shard_count||draftBasis.shards!==latest.shards;}
/* A new draft from the current scores and the latest basis. Card answers carry over only for symbols in the new candidate pool;
   names newly selected need a fresh card answer (pending). */
function regenerateDraft(state,{computed,inputs,universeCodes,existing,date,basis,cfg=CFG,pcfg=PCFG}){
 const draft=buildDraft({computed,inputs,universeCodes,existing,date,basis,cfg,pcfg}),names=new Set(draft.pool.map(r=>key(r.symbol)));
 const answers=(state?.answers||[]).filter(a=>names.has(key(a.symbol))),next={...state,draft,answers},sel=currentSelection(next,cfg,pcfg),kept=new Set(answers.map(a=>key(a.symbol)));
 return{state:next,carried:sel.rows.filter(r=>kept.has(key(r.symbol))).map(r=>r.symbol),fresh:sel.pending,dropped:(state?.answers||[]).filter(a=>!names.has(key(a.symbol))).map(a=>a.symbol)};
}
// Financial safety of the selected names re-checked against the latest file's metrics (anything but PASS fails, NA included).
function safetyRecheck(rows,payload,cfg=CFG){const out=[];for(const r of rows||[]){const rec=object(payload?.records)?payload.records[r.code]:null;if(safety(object(rec)?rec.metrics:null,cfg).state!=='PASS')out.push(r.symbol);}return out;}
// The 10-company number check counts only for the calc_version it was run against (config number_check.result).
function numberCheck(calcVersion,cfg=CFG){
 const N=cfg.number_check,r=object(N.result)?N.result:{},out={calc_version:r.calc_version??null,passed:r.passed===true,date:r.date??null,companies:finite(r.companies)?r.companies:0};
 if(!out.passed||out.companies<N.companies_required)return{...out,ok:false,reason:'NUMBER_CHECK_NOT_PASSED'};
 if(!calcVersion||out.calc_version!==calcVersion)return{...out,ok:false,reason:'NUMBER_CHECK_CALC_VERSION_MISMATCH'};
 return{...out,ok:true,reason:null};
}
// Every reason that blocks finalize now, in order (cards → name shortfall → §16 → V without V3·V4 (2026-10-23) → latest public file →
// draft basis → financial safety re-check → number check). basis: inputBasis(published), computed by the caller at the same moment.
// v_incomplete: the selected names whose V lacks V3 (v_vs_industry) or V4 (v_vs_own_history), or whose draft row predates the count.
// V source of this builder (2026-10-23 decision): central V (qgv-official) when it is published and read, else the device-path V
// labelled 임시 V. This build has no central V reader yet, so every draft and version uses the device path.
const V_SOURCE=Object.freeze({id:'DEVICE_TEMPORARY',ko:'임시 V',note:'기기 시세로 계산 · 중앙 V 미게시'});
function finalizeBlockers(state,{date,published,basis=null,cfg=CFG,pcfg=PCFG}={}){
 if(!validDay(date))return{blockers:['DATE_INVALID'],check:null,number:null,sel:null};if(!state?.draft)return{blockers:['TARGET_V1_DRAFT_REQUIRED'],check:null,number:null,sel:null};
 const sel=currentSelection(state,cfg,pcfg),out=[];if(!sel.complete)out.push('TARGET_V1_CARDS_PENDING');if(sel.shortfall>0)out.push('TARGET_V1_SHORTFALL');if(sel.limits.ok!==true)out.push('TARGET_LIMITS_BLOCKED');
 const v_incomplete=sel.rows.filter(vIncomplete).map(r=>r.symbol);if(v_incomplete.length)out.push('V_FACTORS_V3_V4_MISSING');
 const check=publishedCheck(published,{date,cfg});out.push(...check.reasons);
 const basis_changed=object(published)&&object(published.records)?basisChanged(state.draft.basis,basis):false;if(basis_changed)out.push('DRAFT_BASIS_CHANGED');
 const safety_failed=object(published)&&object(published.records)?safetyRecheck(sel.rows,published,cfg):[];if(safety_failed.length)out.push('FINANCIAL_SAFETY_RECHECK_FAILED');
 const number=numberCheck(check.calc_version,cfg);if(!number.ok)out.push(number.reason);
 return{blockers:out,check,number,sel,basis_changed,safety_failed,v_incomplete};
}
/* Step 7: TARGET v1 as a new device TARGET version once nothing blocks (finalizeBlockers, run here against `published`, the
   sec-qgv2.json payload the caller re-read at this moment). The version keeps the calc_version, the file as_of and the number
   check it was confirmed with. R-C starts on that date (no backfill). The thrown error carries every blocker. */
function finalize(state,{date,published=null,basis=null,cfg=CFG,pcfg=PCFG}={}){
 const r=finalizeBlockers(state,{date,published,basis,cfg,pcfg});if(r.blockers.length){const e=Error(r.blockers[0]);e.blockers=r.blockers;e.check=r.check;e.number=r.number;throw e;}
 const sel=r.sel,n=state.versions.length+1,version=n===1?'v1':'v1.'+(n-1),answers=latestAnswers(state);
 const rows=sel.rows.map(x=>({symbol:x.symbol,grade:x.grade,pct:x.pct,subgroup:x.subgroup,confirmed:answers.get(key(x.symbol))?.answer==='AGREE'}));
 return{...state,versions:[...state.versions,{version,date,draft_created:state.draft.created,config_version:cfg.config_version,calc_version:r.check.calc_version,type_scope:basis.type_scope??null,sec_qgv2_as_of:r.check.as_of,input_shards:basis.shards,
  number_check:{calc_version:r.number.calc_version,passed:true,date:r.number.date,companies:r.number.companies},v_source:V_SOURCE.id,rows,cash_pct:sel.cash_pct}],rule_c:{start:date,version}};
}
function latestVersion(state){return state?.versions?.length?state.versions[state.versions.length-1]:null;}

/* ---------- rebalance calendar (PLAYBOOK 13-4) ---------- */
// 셋째 주 = the Monday among days 15–21 of the month (T-REBAL, 2026-10-15). A holiday Monday stays the calendar day here; the rule
// index applies it on the next session (config rebalance.holiday_rule NEXT_SESSION).
function rebalanceDay(year,month){for(let d=15;d<=21;d++){const t=new Date(Date.UTC(year,month-1,d));if(t.getUTCDay()===1)return t.toISOString().slice(0,10);}return null;}
function rebalanceDays(from,to,cfg=CFG){const out=[];const y0=Number(from.slice(0,4)),y1=Number(to.slice(0,4));for(let y=y0;y<=y1;y++)for(const m of cfg.rebalance.months){const d=rebalanceDay(y,m);if(d>=from&&d<=to)out.push(d);}return out;}
function lastRebalanceOnOrBefore(date,cfg=CFG){const y=Number(date.slice(0,4));const days=rebalanceDays((y-1)+'-01-01',date,cfg);return days.length?days[days.length-1]:null;}
function nextRebalanceOnOrAfter(date,cfg=CFG){const y=Number(date.slice(0,4));return rebalanceDays(date,(y+1)+'-12-31',cfg)[0]||null;}
function rounds(cfg=CFG){return cfg.transition.rounds.map(r=>({round:r.round,month:r.month,date:rebalanceDay(Number(r.month.slice(0,4)),Number(r.month.slice(5,7)))}));}

/* ---------- schedule (2026-10-15 supplement): finalize target = 2nd week of 2026-11 ---------- */
// Not finalized by the deadline → postponed. A round lists names only when TARGET v1 was finalized on or before that round day;
// otherwise the round shows the risk-code checks only (BLOCK / RISK_RECHECK codes of the playbook config), no list, no amount.
function scheduleState(state,date,cfg=CFG){const S=cfg.schedule,v=latestVersion(state);return{finalized:!!v,finalized_on:v?.date||null,window:[...S.finalize_window],deadline:S.deadline,postponed:!v&&validDay(date)&&date>S.deadline,late:!!v&&v.date>S.deadline};}
// A version saved after the deadline is a postponed TARGET v1: the deadline month's round stays risk-code checks only (B-3 F1).
function roundMode(state,round,cfg=CFG){const v=latestVersion(state),S=cfg.schedule;
 if(!v||!round||!validDay(round.date)||v.date>round.date)return S.unfinalized_round_mode;
 if(v.date>S.deadline&&round.date.slice(0,7)===S.deadline.slice(0,7))return S.unfinalized_round_mode;return 'LIST';}
function riskCodes(cfg=CFG,pcfg=PCFG){return pcfg.codes.filter(c=>cfg.schedule.risk_levels.includes(c.level)).map(c=>({code:c.code,level:c.level,text:c.entry_text}));}

/* ---------- Step 8 / D: transition plan (RAM) ---------- */
/* v0: {symbol: pct} (TARGET v0), v1: {symbol: pct} (TARGET v1), actual: {symbol: pct} | null (RAM), total: RAM total value | null.
   Each round moves (v1 − v0) × 1/3; round k's target = v0 + step × k. Amount = step %p × total (RAM only, null without it). */
function transitionRows({v0={},v1={},actual=null,total=null,round:k=1,cfg=CFG}){
 const [num,den]=cfg.transition.step_fraction,symbols=[...new Set([...Object.keys(v1),...Object.keys(v0)])].sort((a,b)=>(v1[b]??0)-(v1[a]??0)||(a<b?-1:1));
 return symbols.map(s=>{const from=finite(v0[s])?v0[s]:0,to=finite(v1[s])?v1[s]:0,step=(to-from)*num/den,cur=actual&&finite(actual[s])?actual[s]:null;
  return{symbol:s,v0_pct:from,final_pct:to,current_pct:cur,step_pp:round(step,4),round_target_pct:round(from+step*k,4),amount:finite(total)&&total>0?step/100*total:null};});
}

/* ---------- C: rule sets R-B and R-C (규칙 지수; no backfill) ---------- */
function ruleBDue(state,date,cfg=CFG){const last=state?.rule_b?.length?state.rule_b[state.rule_b.length-1].date:null;if(!last)return true;const day=lastRebalanceOnOrBefore(date,cfg);return!!day&&last<day&&day<=date;}
// R-B segment (equal weight, same spread and caps). ready: enough eligible names (V priced on this device) and a full,
// limit-passing selection; the screen starts / re-selects R-B only when ready (no partial start, no backfill).
function ruleBSegment(eligibleRows,date,cfg=CFG,pcfg=PCFG){const sel=select(eligibleRows,{mode:'EQUAL',cfg,pcfg}),limitsOk=sel.limits.ok===true,R=cfg.virtual_sets['R-B'];
 return{date,rows:sel.rows.map(r=>({symbol:r.symbol,pct:r.pct,subgroup:r.subgroup})),cash_pct:sel.cash_pct,limits_ok:limitsOk,
  ready:eligibleRows.length>=R.start_min_eligible&&sel.rows.length===R.count&&limitsOk};}
/* Rule index: base session close = 100; units from the segment's target weights; reset to the target weights on every rebalance
   day and every new segment (first session on/after the date, so a holiday Monday resets on the next session). A missing close is a gap (that session NA); a reset or the last
   session without every close → NOT_AVAILABLE. Nothing is interpolated or carried. closes: {symbol: {date: close}} (RAM). */
function ruleIndex({segments,closes,calendar,start,asOf,resetDays=[]}){
 const na=(reason,date=null)=>({state:'NOT_AVAILABLE',reason,date,value:null,return:null});
 if(!validDay(start)||!validDay(asOf)||!Array.isArray(segments)||!segments.length)return na('SET_NOT_STARTED');
 const sessions=(calendar||[]).filter(d=>d>=start&&d<=asOf).sort();if(!sessions.length)return na('NO_SESSION');
 const segs=[...segments].sort((a,b)=>a.date<b.date?-1:1),resets=new Set([sessions[0]]);
 for(const d of [...segs.map(s=>s.date),...resetDays]){const s=sessions.find(x=>x>=d);if(s&&s>sessions[0])resets.add(s);}
 const close=(s,d)=>{const v=closes?.[s]?.[d];return finite(v)&&v>0?v:null;};
 let units=null,cash=0,value=100,last=null;
 for(const d of sessions){
  const seg=segs.filter(s=>s.date<=d).pop();if(!seg)return na('SET_NOT_STARTED',d);
  if(units===null||resets.has(d)){
   if(units!==null){let v=cash;for(const[s,u]of Object.entries(units)){const c=close(s,d);if(c===null)return na('REBALANCE_CLOSE_MISSING',d);v+=u*c;}value=v;}
   units={};let used=0;for(const r of seg.rows){const c=close(r.symbol,d);if(c===null)return na('REBALANCE_CLOSE_MISSING',d);units[r.symbol]=value*r.pct/100/c;used+=r.pct;}cash=value*Math.max(0,100-used)/100;
  }
  let v=cash;for(const[s,u]of Object.entries(units)){const c=close(s,d);if(c===null){v=null;break;}v+=u*c;}last={date:d,value:v};
 }
 if(last.value===null)return na('LAST_CLOSE_MISSING',last.date);
 return{state:'OK',reason:null,base_date:sessions[0],date:last.date,value:last.value,return:last.value/100-1};
}
/* A, R-B, R-C and S&P 500 over the common window [max(R-C start, R-B first), asOf] (local price returns, PLAYBOOK 13-4 reset days). */
const COMPARE_KEYS=Object.freeze(['A','R-B','R-C','SP500']);
function compareSets({state,v0Weights={},closes={},asOf,cfg=CFG}){
 const benchmark=cfg.virtual_sets.benchmark.symbol,calendar=Object.keys(closes?.[benchmark]||{}).sort(),out={window_start:null,as_of:asOf,A:null,'R-B':null,'R-C':null,SP500:null};
 const na=reason=>({state:'NOT_AVAILABLE',reason,value:null,return:null});
 const c=state?.rule_c,version=c?state.versions.find(v=>v.version===c.version):null,firstB=state?.rule_b?.length?state.rule_b[0].date:null;
 if(!c||!version){for(const k of COMPARE_KEYS)out[k]=na('R_C_NOT_STARTED');return out;}
 const start=firstB&&firstB>c.start?firstB:c.start;out.window_start=start;
 if(!validDay(asOf)||asOf<start){for(const k of COMPARE_KEYS)out[k]=na('WINDOW_NOT_STARTED');return out;}
 const resetDays=rebalanceDays(start,asOf,cfg),aRows=Object.entries(v0Weights).filter(([,p])=>finite(p)&&p>0).map(([symbol,pct])=>({symbol,pct}));
 const bSegs=(state.rule_b||[]).filter(s=>s.date<=asOf),bStart=bSegs.filter(s=>s.date<=start).pop();
 out.A=aRows.length?ruleIndex({segments:[{date:start,rows:aRows}],closes,calendar,start,asOf,resetDays}):na('TARGET_V0_NOT_AVAILABLE');
 out['R-B']=bStart?ruleIndex({segments:[{...bStart,date:start},...bSegs.filter(s=>s.date>start)],closes,calendar,start,asOf,resetDays}):na('R_B_NOT_STARTED');
 out['R-C']=ruleIndex({segments:[{date:start,rows:version.rows.map(r=>({symbol:r.symbol,pct:r.pct}))}],closes,calendar,start,asOf,resetDays});
 out.SP500=ruleIndex({segments:[{date:start,rows:[{symbol:benchmark,pct:100}]}],closes,calendar,start,asOf});
 return out;
}
/* E: before the round-3 rebalance (from the round-2 day), if R-B and R-C are each below BOTH A and the S&P 500 → a suggestion to hold
   round 3. Suggestion only; any NA → NOT_AVAILABLE (never a suggestion from missing data). */
function reviewRule({compare,date,cfg=CFG}){
 const R=cfg.review_rule,list=rounds(cfg),before=list.find(r=>r.round===R.before_round),from=list.find(r=>r.round===R.active_from_round);
 if(!validDay(date)||!before||!from||date<from.date||date>=before.date)return{state:'NOT_DUE',suggest:false,round:R.before_round,from:from?.date||null,until:before?.date||null};
 const v=k=>compare?.[k]?.state==='OK'?compare[k].return:null,a=v('A'),b=v('R-B'),c=v('R-C'),s=v('SP500');
 if([a,b,c,s].includes(null))return{state:'NOT_AVAILABLE',suggest:false,round:R.before_round,reason:'RETURN_NOT_AVAILABLE'};
 const suggest=b<a&&b<s&&c<a&&c<s;return{state:'EVALUATED',suggest,round:R.before_round,text:suggest?R.text:null};
}
/* ---------- T-PRICE (2026-10-15): price path for TV1 judgement names (pure; prices only in RAM arguments) ---------- */
// Worker / Prices_D symbol of a Universe ticker ('BRK.B' → 'BRK-B'); null when it cannot be one.
function priceSymbolOf(symbol){const s=key(symbol);return PRICE_SYMBOL.test(s)?s:null;}
// Sector ETF of a TV1 name: the D-22 SIC → ETF map (VirtualTrading.sectorBenchmark; semis theme without membership → XLI),
// else the S&P 500 benchmark (then the sector excess equals the S&P 500 excess, as in the runner).
function sectorEtfOf(sic,cfg=CFG){let etf=null;try{const VT=virtualTrading();etf=VT&&sic!==null&&sic!==undefined?VT.sectorBenchmark(String(sic)).etf:null;}catch(_){etf=null;}return etf&&PRICE_SYMBOL.test(etf)?etf:cfg.scoring_prices.benchmark;}
/* TV1 records whose name has no device price path: not one of the 19 (runner series) and not yet added. → [{symbol, price_symbol,
   sector_symbol}] in record order, one per name. sicOf(symbol) → SIC or null (public file). */
function scoringNeeds(records,{have=[],added=[],sicOf=()=>null,cfg=CFG}={}){
 const code=cfg.scoring_prices.record_primary_code,known=new Set([...have,...added].map(key)),out=[],seen=new Set();
 for(const r of Array.isArray(records)?records:[]){if(r?.primary_code!==code||!r.verdict)continue;const ps=priceSymbolOf(r.symbol);if(!ps||known.has(key(r.symbol))||known.has(ps)||seen.has(ps))continue;seen.add(ps);
  out.push({symbol:r.symbol,price_symbol:ps,sector_symbol:sectorEtfOf(sicOf(r.symbol),cfg)});}
 return out;
}
// The symbols one confirmed click adds (names, their sector ETFs, the S&P 500 benchmark), merged into state.price_symbols.
function addPriceSymbols(state,needs,cfg=CFG){
 const list=[...(state?.price_symbols||[])];for(const n of needs||[])for(const s of [n.price_symbol,n.sector_symbol,cfg.scoring_prices.benchmark])if(s&&PRICE_SYMBOL.test(s)&&!list.includes(s))list.push(s);
 if(list.length>cfg.scoring_prices.max_symbols)fail('PRICE_SYMBOLS_MAX');return{...state,price_symbols:list};
}
/* Scoring series for PlaybookScreen.scoreRecord from daily closes read into RAM ({symbol: {date: close}}): sessions are the S&P 500
   benchmark's dates. A name or benchmark without closes → null (the record stays NA; nothing is filled with 0). */
function scoringSeries(need,closes,cfg=CFG){
 const b=cfg.scoring_prices.benchmark,sp=closes?.[b],stock=closes?.[need?.price_symbol],sector=closes?.[need?.sector_symbol];
 const ok=x=>object(x)&&Object.keys(x).length>0;if(!ok(sp)||!ok(stock)||!ok(sector))return null;
 return{sessions:Object.keys(sp).filter(validDay).sort(),stock:{...stock},sector:{...sector},sp500:{...sp},sector_symbol:need.sector_symbol};
}
return Object.freeze({SCHEMA,V_SOURCE,ANSWERS,COMPARE_KEYS,V_FACTORS,V_REQUIRED,vFactors,vIncomplete,publishedCheck,inputBasis,basisChanged,regenerateDraft,safetyRecheck,numberCheck,finalizeBlockers,scheduleState,roundMode,riskCodes,coverage,subgroupOf,groupOf,safety,universeRows,exclusions,spread,select,limits,templates,invalidated,buildDraft,candidates,
 emptyState,validateState,latestAnswers,currentSelection,answer,judgementRecord,finalize,latestVersion,rebalanceDay,rebalanceDays,lastRebalanceOnOrBefore,
 nextRebalanceOnOrAfter,rounds,transitionRows,ruleBDue,ruleBSegment,ruleIndex,compareSets,reviewRule,coreEligible,priceSymbolOf,sectorEtfOf,scoringNeeds,addPriceSymbols,scoringSeries});
});
