/* Public price-free `sec-qgv2.json` reader: QGV v2 Q·G (PROVISIONAL default, GSQ-022 approved 2026-10-13). Mirrors Python universe/sec_qgv2.require_qgv2 including the full score recomputation (qgv/v2_scoring.py); JS==Python vectors: tests/fixtures/sec_qgv2_vectors_v1.json. Per Universe504 code and per TARGET id: raw SEC metrics, 10 factor percentiles (0-100 or null = NOT_AVAILABLE, never 0), Q/G axis scores with factors_available n/total and peer basis/count, and the price-free `v_inputs_v2` amounts the device needs for V. No price, market cap, V score or rank. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.SecQgv2=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
 'use strict';
 const FILENAME='sec-qgv2.json',KIND='SEC_QGV2',MAX=2*1024*1024,CODE_COUNT=504,STANDARD='QGV_V2',STANDARD_STATUS='PROVISIONAL_DEFAULT_UNCALIBRATED',DECISION_REF='GSQ-022';
 const CONFIG_VERSION='sec-universe-shares/v0',CONFIG_STATUS='DEFAULT_V0_UNCALIBRATED';
 const Q_WEIGHTS={q_profitability:25,q_moat_proxy:20,q_earnings_quality:20,q_financial_safety:20,q_capital_allocation:15};
 const G_WEIGHTS={g_revenue_growth:25,g_per_share_growth:25,g_growth_efficiency:20,g_consistency:15,g_recent_acceleration:15};
 const AXES={Q:Q_WEIGHTS,G:G_WEIGHTS},FACTOR_IDS=Object.freeze([...Object.keys(Q_WEIGHTS),...Object.keys(G_WEIGHTS)]),MIN_PEERS=8,AXIS_COVERAGE_MIN=50;
 const METHOD={weights:{Q:Q_WEIGHTS,G:G_WEIGHTS},min_peers:8,axis_coverage_min_percent:50,percentile:'AVERAGE_RANK_0_100',industry_groups:'sic_industry_groups/v0',financial_sic_range:[6000,6499],cross_section:'UNIVERSE504_LIVE_STALE_ONE_POINT_PER_CIK',submetric_fallback:'GROUP_VALUES_BELOW_MIN_PEERS_RANK_IN_GENERAL_UNIVERSE',earnings_surprise:'OMITTED_NO_FREE_SOURCE'};
 const METRIC_KEYS=Object.freeze(['roic','gross_profit_to_assets','accruals_to_assets','fcf_to_net_income','net_debt_to_ebitda','interest_coverage','incremental_roic_5y','roe','roa','net_interest_income_to_assets','equity_to_assets','incremental_roe_5y','moat_return_mean_5y','moat_return_std_5y','moat_return_years','moat_proxy','dilution_3y','revenue_cagr_3y','eps_cagr_3y','fcf_per_share_cagr_3y','book_value_per_share_cagr_3y','incremental_roic_3y','incremental_roe_3y','revenue_positive_growth_share','revenue_growth_volatility','revenue_ttm_growth','revenue_acceleration']);
 const DESCRIPTIVE=['moat_return_mean_5y','moat_return_std_5y','moat_return_years','revenue_ttm_growth'];
 const COMMON_G={g_revenue_growth:[['revenue_cagr_3y',1]],g_consistency:[['revenue_positive_growth_share',1],['revenue_growth_volatility',-1]],g_recent_acceleration:[['revenue_acceleration',1]]};
 const SUBMETRICS={
  GENERAL:{q_profitability:[['roic',1],['gross_profit_to_assets',1]],q_moat_proxy:[['moat_proxy',1]],q_earnings_quality:[['accruals_to_assets',-1],['fcf_to_net_income',1]],q_financial_safety:[['net_debt_to_ebitda',-1],['interest_coverage',1]],q_capital_allocation:[['dilution_3y',-1],['incremental_roic_5y',1]],g_per_share_growth:[['eps_cagr_3y',1],['fcf_per_share_cagr_3y',1]],g_growth_efficiency:[['incremental_roic_3y',1]],...COMMON_G},
  FINANCIAL:{q_profitability:[['roe',1],['roa',1],['net_interest_income_to_assets',1]],q_moat_proxy:[['moat_proxy',1]],q_earnings_quality:[],q_financial_safety:[['equity_to_assets',1]],q_capital_allocation:[['dilution_3y',-1],['incremental_roe_5y',1]],g_per_share_growth:[['eps_cagr_3y',1],['book_value_per_share_cagr_3y',1]],g_growth_efficiency:[['incremental_roe_3y',1]],...COMMON_G}};
 /* sic_industry_groups/v0 group ranges (node test compares with the packaged JSON). */
 const SIC_GROUPS=[['resources_mining',[[1000,1499]]],['construction',[[1500,1799]]],['food_tobacco',[[2000,2199]]],['manufacturing_industrial_tech',[[2200,3999]]],['transportation',[[4000,4799]]],['telecommunications',[[4800,4899]]],['utilities',[[4900,4999]]],['wholesale_retail',[[5000,5999]]],['finance_real_estate',[[6000,6799]]],['services_software_health',[[7000,8999]]]];
 const TARGET_CIKS={asml:'0000937966',lrcx:'0000707549',klac:'0000319201',tokyo_electron:null,hanmi:null,nvda:'0001045810',amd:'0000002488',avgo:'0001730168',qcom:'0000804328',intc:'0000050863',msft:'0000789019',googl:'0001652044',amzn:'0001018724',rtx:'0000101829',stry:'0000310764',etn:'0001551182',hubb:'0000048898',gev:'0001996810',rok:'0001024478'};
 const STATES=['LIVE','STALE','NOT_AVAILABLE'],SCORED=['LIVE','STALE'],REASONS=['NOT_COLLECTED','CIK_UNRESOLVED','INVALID_INPUT','NO_ANNUAL_SEC_FINANCIALS','NON_SEC_ISSUER','STALE_INPUT'],TOP_REASONS=['STALE_INPUT','NO_ELIGIBLE_INPUT'];
 const TOP=['schema_version','kind','as_of','standard','standard_status','decision_ref','method','config_version','config_status','freshness_basis','stale_after_seconds','shard_count','last_shard_index','registry_sha256','code_count','cross_section_size','cross_section_by_profile','state','reason_codes','records','target'];
 const ROW=['cik','acquired_at','source_sha256','state','reason_codes','sic','industry_group','profile','fiscal_year_end','currency','metrics','factors','axes','v_inputs_v2'];
 const AXIS_KEYS=['score','factors_available','available_weight','peer_basis','peer_count','submetric_fallbacks','reason_codes'];
 const LEGACY_V_KEYS=['currency','taxonomy','fiscal_year_end','ebit','fcf','total_debt','cash_and_equivalents','diluted_shares','ebit_per_share_history','fcf_per_share_history','revenue_cagr_3y','eps_cagr_3y','fcf_per_share_cagr_3y','revenue_ttm_growth'];
 const V_KEYS=LEGACY_V_KEYS.concat(['revenue','operating_margin_history']);
 const FLOW_KEYS=['fy_value','fy_end','ttm_value','ttm_end'],FLOW_V=['ebit','fcf','revenue'],INSTANT_V=['total_debt','cash_and_equivalents','diluted_shares'],GROWTH_V=['revenue_cagr_3y','eps_cagr_3y','fcf_per_share_cagr_3y','revenue_ttm_growth'];
 const LIMIT=1e12,HISTORY_YEARS=5;
 function need(x){if(!x)throw Error('SEC_QGV2_INVALID');}
 const plain=x=>x!==null&&typeof x==='object'&&!Array.isArray(x),keys=(x,k)=>plain(x)&&Object.keys(x).length===k.length&&k.every(n=>Object.hasOwn(x,n));
 const hash=x=>typeof x==='string'&&/^[0-9a-f]{64}$/.test(x),num=x=>typeof x==='number'&&Number.isFinite(x),cikOk=x=>typeof x==='string'&&/^\d{10}$/.test(x)&&x!=='0000000000';
 const day=x=>typeof x==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(x)&&new Date(x+'T00:00:00Z').toISOString().slice(0,10)===x;
 function date(x){need(day(x));return x;}
 function clock(x){need(typeof x==='string'&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$/.test(x)&&day(x.slice(0,10)));const t=Date.parse(x);need(Number.isFinite(t));return t;}
 const canon=x=>Array.isArray(x)?'['+x.map(canon).join(',')+']':plain(x)?'{'+Object.keys(x).sort().map(k=>JSON.stringify(k)+':'+canon(x[k])).join(',')+'}':JSON.stringify(x);
 function classify(sic){const code=Number(sic);const g=SIC_GROUPS.find(([,ranges])=>ranges.some(([lo,hi])=>lo<=code&&code<=hi));return g?g[0]:null;}
 const profileFor=sic=>typeof sic==='string'&&/^\d{4}$/.test(sic)&&Number(sic)>=6000&&Number(sic)<=6499?'FINANCIAL':'GENERAL';
 function emptyV(){return{currency:null,taxonomy:null,fiscal_year_end:null,ebit:null,fcf:null,total_debt:null,cash_and_equivalents:null,diluted_shares:null,ebit_per_share_history:[],fcf_per_share_history:[],revenue:null,operating_margin_history:[],revenue_cagr_3y:null,eps_cagr_3y:null,fcf_per_share_cagr_3y:null,revenue_ttm_growth:null};}
 function emptyAxis(reason){return{score:null,factors_available:'0/5',available_weight:0,peer_basis:null,peer_count:0,submetric_fallbacks:0,reason_codes:[reason]};}
 function emptyRecord(reason='NOT_COLLECTED'){return{cik:null,acquired_at:null,source_sha256:{companyfacts:null,submissions:null},state:'NOT_AVAILABLE',reason_codes:[reason],sic:null,industry_group:null,profile:null,fiscal_year_end:null,currency:null,metrics:{},factors:Object.fromEntries(FACTOR_IDS.map(k=>[k,null])),axes:{Q:emptyAxis('ROW_NOT_AVAILABLE'),G:emptyAxis('ROW_NOT_AVAILABLE')},v_inputs_v2:emptyV()};}
 const metricOk=(k,v)=>k==='moat_return_years'?Number.isInteger(v)&&v>=3&&v<=HISTORY_YEARS:num(v)&&Math.abs(v)<=LIMIT;
 function vInputs(v,cutDay,hasData){
  need(keys(v,V_KEYS)||keys(v,LEGACY_V_KEYS));if(!hasData){const empty=emptyV();need(canon(v)===canon(Object.fromEntries(Object.keys(v).map(k=>[k,empty[k]]))));return;}
  need(typeof v.currency==='string'&&/^[A-Z]{3}$/.test(v.currency)&&['us-gaap','ifrs-full'].includes(v.taxonomy)&&date(v.fiscal_year_end)<=cutDay);
  for(const k of FLOW_V){const f=v[k];if(f===null||f===undefined)continue;need(keys(f,FLOW_KEYS));
   for(const [vk,ek] of [['fy_value','fy_end'],['ttm_value','ttm_end']]){need((f[vk]===null)===(f[ek]===null));if(f[vk]!==null)need(num(f[vk])&&date(f[ek])<=cutDay);}
   need(f.fy_value!==null||f.ttm_value!==null);if(f.fy_end!==null&&f.ttm_end!==null)need(f.ttm_end>=f.fy_end);}
  for(const k of INSTANT_V){const i=v[k];if(i===null)continue;need(keys(i,['value','period_end'])&&num(i.value)&&date(i.period_end)<=cutDay);if(k==='diluted_shares')need(i.value>0);}
  for(const k of ['ebit_per_share_history','fcf_per_share_history','operating_margin_history']){const h=v[k]||[];need(Array.isArray(h)&&h.length<=HISTORY_YEARS);const ends=[];for(const e of h){need(keys(e,['fiscal_year_end','value'])&&num(e.value));ends.push(date(e.fiscal_year_end));need(ends[ends.length-1]<=cutDay);}for(let i=1;i<ends.length;i++)need(ends[i-1]<ends[i]);}
  for(const k of GROWTH_V)need(v[k]===null||num(v[k])&&Math.abs(v[k])<=LIMIT);
 }
 /* One row (mirrors Python _row); scores are compared separately against the recomputation. */
 function row(r,cut,ttl,targetId){
  need(keys(r,ROW)&&(r.cik===null||cikOk(r.cik)));if(targetId!==undefined&&r.cik!==null)need(r.cik===TARGET_CIKS[targetId]);
  const h=r.source_sha256;need(keys(h,['companyfacts','submissions'])&&Object.values(h).every(v=>v===null||hash(v)));
  if(r.acquired_at===null)need(h.companyfacts===null&&h.submissions===null);else need(clock(r.acquired_at)<=cut&&r.cik!==null&&h.companyfacts&&h.submissions);
  need(STATES.includes(r.state));const reasons=r.reason_codes;need(Array.isArray(reasons)&&new Set(reasons).size===reasons.length&&reasons.length<=3&&reasons.every(x=>REASONS.includes(x)));
  need(r.sic===null||typeof r.sic==='string'&&/^\d{4}$/.test(r.sic)&&r.sic!=='0000');
  if(r.sic===null)need(r.industry_group===null);else need(r.acquired_at!==null&&r.industry_group===classify(r.sic));
  const m=r.metrics;need(plain(m)&&Object.keys(m).every(k=>METRIC_KEYS.includes(k)&&metricOk(k,m[k])));
  const hasData=r.fiscal_year_end!==null,cutDay=new Date(cut).toISOString().slice(0,10);
  if(hasData){
   need(r.acquired_at!==null&&date(r.fiscal_year_end)<=cutDay&&r.profile===profileFor(r.sic)&&typeof r.currency==='string'&&/^[A-Z]{3}$/.test(r.currency));
   const allowed=new Set([...Object.values(SUBMETRICS[r.profile]).flat().map(([k])=>k),...DESCRIPTIVE,'dilution_3y']);need(Object.keys(m).every(k=>allowed.has(k)));
   const fresh=cut-clock(r.acquired_at)<=ttl*1000;need(r.state===(fresh?'LIVE':'STALE')&&canon(reasons)===canon(fresh?[]:['STALE_INPUT']));
   need(plain(r.v_inputs_v2)&&r.v_inputs_v2.currency===r.currency&&r.v_inputs_v2.fiscal_year_end===r.fiscal_year_end);
  }else{
   need(r.profile===null&&r.currency===null&&Object.keys(m).length===0&&r.state==='NOT_AVAILABLE'&&reasons.length&&!reasons.includes('STALE_INPUT'));
   if(targetId!==undefined&&TARGET_CIKS[targetId]===null)need(canon(reasons)==='["NON_SEC_ISSUER"]'&&r.cik===null&&r.acquired_at===null);else need(!reasons.includes('NON_SEC_ISSUER'));
  }
  vInputs(r.v_inputs_v2,cutDay,hasData);
  need(keys(r.factors,FACTOR_IDS)&&keys(r.axes,['Q','G'])&&Object.values(r.axes).every(a=>keys(a,AXIS_KEYS)));
  return r.state;
 }
 /* Score recomputation (mirrors qgv/v2_scoring.score_rows). */
 const percentile=(less,equal,n)=>100*(less+(equal-1)/2)/(n-1);
 function pool(points){return{points,size:points.size};}
 function rank(p,metric,dir,own,excludeCik){
  const x=dir*own;let less=0,equal=0,n=0;
  for(const [cik,m] of p.points){if(cik===excludeCik)continue;const v=m[metric];if(v===undefined||v===null)continue;const y=dir*v;n++;if(y<x)less++;else if(y===x)equal++;}
  return [less,equal+1,n+1];
 }
 function scoreRows(universe,target){
  const points=new Map();for(const key of Object.keys(universe).sort()){const r=universe[key];if(SCORED.includes(r.state)&&r.cik!==null&&!points.has(r.cik))points.set(r.cik,r);}
  const byProfile={GENERAL:new Map(),FINANCIAL:new Map()},groups=new Map();
  for(const [cik,r] of points){byProfile[r.profile].set(cik,r.metrics);if(r.profile==='GENERAL'&&r.industry_group!==null){if(!groups.has(r.industry_group))groups.set(r.industry_group,new Map());groups.get(r.industry_group).set(cik,r.metrics);}}
  const pools={GENERAL:pool(byProfile.GENERAL),FINANCIAL:pool(byProfile.FINANCIAL)},groupPools=new Map([...groups].map(([g,m])=>[g,pool(m)]));
  const out=new Map();for(const [role,rows] of [['universe',universe],['target',target]])for(const [key,r] of Object.entries(rows))out.set(role+'\u0000'+key,scoreRow(r,pools,groupPools));
  return{scores:out,summary:{cross_section_size:points.size,cross_section_by_profile:{GENERAL:byProfile.GENERAL.size,FINANCIAL:byProfile.FINANCIAL.size}}};
 }
 function peerSet(r,axis,pools,groupPools){
  const count=p=>p.size-(p.points.has(r.cik)?1:0)+1;
  if(r.profile==='FINANCIAL')return[pools.FINANCIAL,'FINANCIAL_PROFILE',count(pools.FINANCIAL)];
  if(axis==='Q'){const g=r.industry_group!==null?groupPools.get(r.industry_group):undefined;if(g!==undefined&&count(g)>=MIN_PEERS)return[g,'INDUSTRY_GROUP',count(g)];return[pools.GENERAL,'UNIVERSE_FALLBACK',count(pools.GENERAL)];}
  return[pools.GENERAL,'UNIVERSE',count(pools.GENERAL)];
 }
 function scoreRow(r,pools,groupPools){
  const factors=Object.fromEntries(FACTOR_IDS.map(k=>[k,null])),axes={};
  if(!SCORED.includes(r.state)||r.profile===null)return{factors,axes:{Q:emptyAxis('ROW_NOT_AVAILABLE'),G:emptyAxis('ROW_NOT_AVAILABLE')}};
  const specs=SUBMETRICS[r.profile];
  for(const [axis,weights] of Object.entries(AXES)){
   const [p,basis,peerCount]=peerSet(r,axis,pools,groupPools);
   if(peerCount<MIN_PEERS){axes[axis]={...emptyAxis('PEERS_BELOW_MINIMUM'),peer_basis:basis,peer_count:peerCount};continue;}
   let fallbacks=0;
   for(const fid of Object.keys(weights)){const pcts=[];for(const [metric,dir] of specs[fid]){const own=r.metrics[metric];if(own===undefined||own===null)continue;let [less,equal,n]=rank(p,metric,dir,own,r.cik);if(n<MIN_PEERS&&basis==='INDUSTRY_GROUP'){[less,equal,n]=rank(pools.GENERAL,metric,dir,own,r.cik);if(n>=MIN_PEERS)fallbacks++;}if(n>=MIN_PEERS)pcts.push(percentile(less,equal,n));}if(pcts.length)factors[fid]=pcts.reduce((a,b)=>a+b,0)/pcts.length;}
   const available=Object.keys(weights).filter(f=>factors[f]!==null),weight=available.reduce((a,f)=>a+weights[f],0),total=Object.values(weights).reduce((a,b)=>a+b,0);
   const o={score:null,factors_available:available.length+'/'+Object.keys(weights).length,available_weight:weight,peer_basis:basis,peer_count:peerCount,submetric_fallbacks:fallbacks,reason_codes:[]};
   if(weight*100<AXIS_COVERAGE_MIN*total)o.reason_codes=['AXIS_COVERAGE_BELOW_50'];else o.score=available.reduce((a,f)=>a+weights[f]*factors[f],0)/weight;
   axes[axis]=o;
  }
  return{factors,axes};
 }
 const sameNum=(a,b)=>a===null||b===null?a===null&&b===null:num(a)&&Math.abs(a-b)<=Math.max(1e-9,1e-9*Math.max(Math.abs(a),Math.abs(b)));
 function scoresMatch(r,e){need(FACTOR_IDS.every(f=>sameNum(r.factors[f],e.factors[f])));for(const axis of ['Q','G']){const g=r.axes[axis],w=e.axes[axis];need(sameNum(g.score,w.score));for(const k of AXIS_KEYS)if(k!=='score')need(canon(g[k])===canon(w[k]));}}
 function validate(p){
  try{
   need(keys(p,TOP)&&p.schema_version===1&&p.kind===KIND&&p.standard===STANDARD&&p.standard_status===STANDARD_STATUS&&[DECISION_REF,'GSQ-022_PENDING_APPROVAL'].includes(p.decision_ref)&&canon(p.method)===canon(METHOD));
   need(p.config_version===CONFIG_VERSION&&p.config_status===CONFIG_STATUS&&p.freshness_basis==='SOURCE_ACQUISITION');
   const cut=clock(p.as_of),ttl=p.stale_after_seconds;
   need(Number.isInteger(ttl)&&ttl>0&&ttl<=366*86400&&Number.isInteger(p.shard_count)&&p.shard_count>=1&&p.shard_count<=366&&(p.last_shard_index===null||Number.isInteger(p.last_shard_index)&&p.last_shard_index>=0&&p.last_shard_index<p.shard_count)&&(p.registry_sha256===null||hash(p.registry_sha256)));
   const codes=plain(p.records)?Object.keys(p.records):[];need(codes.length===CODE_COUNT&&p.code_count===CODE_COUNT&&codes.every(c=>/^[A-Z]{2,8}:[A-Z0-9][A-Z0-9.\-]{0,15}$/.test(c)));
   const ids=Object.keys(TARGET_CIKS);need(keys(p.target,ids));
   const states=[...codes.map(c=>row(p.records[c],cut,ttl)),...ids.map(i=>row(p.target[i],cut,ttl,i))];
   const state=states.includes('LIVE')?'LIVE':states.includes('STALE')?'STALE':'NOT_AVAILABLE';need(p.state===state);
   need(canon(p.reason_codes)===canon(state==='LIVE'?[]:state==='STALE'?['STALE_INPUT']:['NO_ELIGIBLE_INPUT']));
   const {scores,summary}=scoreRows(p.records,p.target);
   need(Number.isInteger(p.cross_section_size)&&p.cross_section_size===summary.cross_section_size&&keys(p.cross_section_by_profile,['GENERAL','FINANCIAL'])&&p.cross_section_by_profile.GENERAL===summary.cross_section_by_profile.GENERAL&&p.cross_section_by_profile.FINANCIAL===summary.cross_section_by_profile.FINANCIAL);
   const byCik=new Map();
   for(const c of codes){const r=p.records[c];if(r.state!=='NOT_AVAILABLE'){const text=canon(r);if(!byCik.has(r.cik))byCik.set(r.cik,text);need(byCik.get(r.cik)===text);}scoresMatch(r,scores.get('universe\u0000'+c));}
   for(const i of ids)scoresMatch(p.target[i],scores.get('target\u0000'+i));
   return p;
  }catch(_){throw Error('SEC_QGV2_INVALID');}
 }
 const deep=x=>{if(x&&typeof x==='object'){Object.values(x).forEach(deep);Object.freeze(x);}return x;};
 /* Device-time freshness from each row's own acquired_at (mirrors Python restate). Values and scores never change. */
 function restate(r,now,ttl){const copy=JSON.parse(JSON.stringify(r));if(copy.fiscal_year_end===null)return deep(copy);const fresh=Date.parse(now)-Date.parse(copy.acquired_at)<=ttl*1000;return deep({...copy,state:fresh?'LIVE':'STALE',reason_codes:fresh?[]:['STALE_INPUT']});}
 function toInputs(payload,{now=new Date().toISOString()}={}){
  validate(payload);const records={},target={};
  for(const [code,r] of Object.entries(payload.records))records[code]=restate(r,now,payload.stale_after_seconds);
  for(const [id,r] of Object.entries(payload.target))target[id]=restate(r,now,payload.stale_after_seconds);
  const all=[...Object.values(records),...Object.values(target)];
  return Object.freeze({records:Object.freeze(records),target:Object.freeze(target),as_of:payload.as_of,standard:payload.standard,standard_status:payload.standard_status,decision_ref:payload.decision_ref,method:deep(JSON.parse(JSON.stringify(payload.method))),cross_section_size:payload.cross_section_size,cross_section_by_profile:Object.freeze({...payload.cross_section_by_profile}),state:all.some(r=>r.state==='LIVE')?'LIVE':all.some(r=>r.state==='STALE')?'STALE':'NOT_AVAILABLE'});
 }
 /* 404 -> null (not published yet), invalid -> fail closed. No storage writes. */
 async function loadInputs(view,{signal,now}={}){
  const response=await view.fetch(FILENAME,{cache:'no-cache',signal,headers:{Accept:'application/json'}});if(response.status===404)return null;if(!response.ok)throw Error('SEC_QGV2_UNAVAILABLE');
  const text=await response.text();if(new TextEncoder().encode(text).length>MAX)throw Error('SEC_QGV2_INVALID');let payload;try{payload=JSON.parse(text);}catch(_){throw Error('SEC_QGV2_INVALID');}
  return toInputs(payload,{now:now||new Date().toISOString()});
 }
 return Object.freeze({FILENAME,FACTOR_IDS,METRIC_KEYS,Q_WEIGHTS:Object.freeze({...Q_WEIGHTS}),G_WEIGHTS:Object.freeze({...G_WEIGHTS}),SIC_GROUPS,TARGET_CIKS:Object.freeze({...TARGET_CIKS}),STANDARD_STATUS,validate,emptyRecord,restate,toInputs,loadInputs,scoreRows});
});
