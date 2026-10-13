/* QGV v2 PROVISIONAL device scoring (docs/qgv_scoring_standard/QGV_V2_CANDIDATE.md, QGV_V2_V_DEVICE.md): V v2 factors from
   the public price-free v_inputs_v2 and this device's prices, Q·G·V axes (renormalized, < 50% weight -> NA), composite with
   the §5 presets on top of the GSQ-017 type weights, and the §4 value-trap gate. Pure and RAM only: prices, market caps, EV
   and V scores are arguments/results, never stored, logged or sent. Missing is null (NOT_AVAILABLE), never 0.
   Python reference: qgv/qgv_v2.py (vectors: tests/fixtures/qgv_v2_vectors_v1.json). Sums are left-to-right like the reference. */
(function(root,factory){const node=typeof module==='object'&&module.exports;
 const api=factory(node?()=>require('./engine-preview.js'):()=>root.EnginePreview,node?()=>require('./type-config-defaults.js'):()=>root.TypeConfigDefaults,node?()=>require('./dcf-parameters-defaults.js'):()=>root.DcfParametersDefaults);
 if(node)module.exports=api;else root.QgvV2=api;})(typeof globalThis==='object'?globalThis:this,function(engine,typeDefaults,dcfDefaults){
'use strict';
const VERSION='qgv-v2',STATUS='PROVISIONAL',PILLARS=['Q','G','V'];
const WEIGHTS={Q:{q_profitability:25,q_moat_proxy:20,q_earnings_quality:20,q_financial_safety:20,q_capital_allocation:15},
 G:{g_revenue_growth:25,g_per_share_growth:25,g_growth_efficiency:20,g_consistency:15,g_recent_acceleration:15},
 V:{v_earnings_yield:25,v_fcf_yield:25,v_vs_industry:20,v_vs_own_history:15,v_expectation_check:15}};
const FACTORS=PILLARS.flatMap(a=>Object.keys(WEIGHTS[a])),QG_FACTORS=['Q','G'].flatMap(a=>Object.keys(WEIGHTS[a]));
const PRESETS={balanced:{name:'균형',name_en:'Balanced',weights:{Q:34,G:33,V:33}},quality:{name:'우량 중심',name_en:'Quality first',weights:{Q:50,G:25,V:25}},
 growth:{name:'성장 친화',name_en:'Growth friendly',weights:{Q:30,G:50,V:20}},value:{name:'가치(관문 켬)',name_en:'Value (gate on)',weights:{Q:25,G:20,V:55}}};
const DEFAULT_PRESET='balanced',GATE_DEFAULT=true,GATE_PERCENTILE=30,MIN_PEERS=8,MIN_UNIVERSE=8,MIN_AXIS_WEIGHT=0.5,MIN_HISTORY=3,CLOSE_WINDOW_DAYS=10;
const DAY=/^\d{4}-\d{2}-\d{2}$/;
const deep=x=>{if(x&&typeof x==='object'){Object.values(x).forEach(deep);Object.freeze(x);}return x;};
deep(WEIGHTS);deep(PRESETS);Object.freeze(FACTORS);Object.freeze(QG_FACTORS);
const finite=v=>typeof v==='number'&&Number.isFinite(v),positive=v=>finite(v)&&v>0,object=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
function percentile(value,population){const n=population.length;if(n<2)return null;let less=0,equal=0;for(const y of population){if(y<value)less++;else if(y===value)equal++;}return 100*(less+0.5*(equal-1))/(n-1);}
function axisScore(scores,axis){
 const weights=WEIGHTS[axis];let total=0,used=0,acc=0,available=0;const missing=[];
 for(const[f,w]of Object.entries(weights)){total+=w;const s=Object.hasOwn(scores,f)?scores[f]:null;if(s===null||s===undefined){missing.push(f);continue;}available++;used+=w;acc+=w*s;}
 const share=used/total,out={score:null,state:'NOT_AVAILABLE',weight_available:share,factors_available:available,factors_total:Object.keys(weights).length,missing};
 if(used===0||share<MIN_AXIS_WEIGHT){out.reason='AXIS_WEIGHT_INSUFFICIENT';return out;}
 out.score=acc/used;out.state=missing.length?'PARTIAL':'READY';out.reason=null;return out;}
// GSQ-017 mixing (type_config/1): memberships {type_id: 0..1|null} -> parent Q/G/V weights.
function typeAxisWeights(memberships,cfg){
 const fallback={};for(const p of PILLARS)fallback[p]=cfg.fallback.weights[p];const mix=cfg.mixing,types=cfg.types;
 if(!object(memberships))return[fallback,'TYPE_UNCONFIRMED',[]];
 const m=id=>{const v=Object.hasOwn(memberships,id)?memberships[id]:null;return finite(v)&&v>=0&&v<=1?v:null;},order={};types.forEach((t,i)=>{order[t.id]=i;});
 const recognized=types.filter(t=>t.affects_qgv&&m(t.id)!==null&&m(t.id)>=mix.minimum_membership).sort((a,b)=>m(b.id)-m(a.id)||order[a.id]-order[b.id]),dropped=new Set();
 for(const[a,b]of mix.exclusive_pairs){const present=recognized.filter(t=>(t.id===a||t.id===b)&&!dropped.has(t.id));if(present.length===2)dropped.add(present[1].id);}
 const selected=recognized.filter(t=>!dropped.has(t.id)).slice(0,mix.maximum_types);let weights,reason;
 if(!selected.length){weights={...fallback};reason=types.filter(t=>t.affects_qgv).every(t=>m(t.id)===null)?'TYPE_UNCONFIRMED':'NO_RECOGNIZED_TYPE';}
 else{let mass=0;for(const t of selected)mass+=m(t.id);weights={};for(const p of PILLARS){let acc=0;for(const t of selected)acc+=t.weights[p]*m(t.id);weights[p]=acc/mass;}reason=null;}
 const clamped={};for(const p of PILLARS)clamped[p]=Math.min(mix.pillar_max,Math.max(mix.pillar_min,weights[p]));let total=0;for(const p of PILLARS)total+=clamped[p];
 const out={};for(const p of PILLARS)out[p]=100*clamped[p]/total;return[out,reason,selected.map(t=>t.id)];}
// Type weights on top of the preset: w_p ∝ preset_p × type_p / fallback_p (the balanced preset reproduces the GSQ-017 weights).
function compositeWeights(preset,type,fallback){const raw={};for(const p of PILLARS)raw[p]=preset[p]*type[p]/fallback[p];let total=0;for(const p of PILLARS)total+=raw[p];const out={};for(const p of PILLARS)out[p]=100*raw[p]/total;return out;}
function dayMinus(day,days){return new Date(Date.parse(day+'T00:00:00Z')-days*86400000).toISOString().slice(0,10);}
function closeAt(closes,periodEnd){
 if(!object(closes)||typeof periodEnd!=='string'||!DAY.test(periodEnd))return null;const low=dayMinus(periodEnd,CLOSE_WINDOW_DAYS);let best=null;
 for(const d of Object.keys(closes).sort())if(DAY.test(d)&&low<=d&&d<=periodEnd&&positive(closes[d]))best=closes[d];return best;}
function metrics(company,quote,parameters){
 const E=engine(),v=object(company)&&object(company.v_inputs)?company.v_inputs:null,out={ebit_yield:null,fcf_yield:null,own_history:null,gap:null,implied_growth:null,realized_growth:null,reasons:{}},r=out.reasons;
 const fail=(reason,keys=['ebit_yield','fcf_yield','own_history','gap'])=>{for(const k of keys)if(!Object.hasOwn(r,k))r[k]=reason;return out;};
 if(object(company)&&company.profile==='FINANCIAL')return fail('FINANCIAL_PROFILE_V_NOT_DEFINED');
 if(!v)return fail('V_INPUTS_NOT_AVAILABLE');
 const price=object(quote)?quote.price:null;if(!positive(price))return fail('NO_DEVICE_PRICE');
 if(v.currency===null||v.currency===undefined||quote.currency!==v.currency)return fail('CURRENCY_BASIS_UNCONFIRMED');
 const shares=v.diluted_shares;if(!positive(shares))return fail('SHARES_NOT_AVAILABLE');
 const ebit=v.ebit,fcf=v.fcf,debt=v.total_debt,cash=v.cash,hist=v.ebit_per_share_history,closes=quote.closes;
 if(!finite(ebit))r.own_history='EBIT_NOT_AVAILABLE';
 else if(!object(closes)||!Object.keys(closes).length)r.own_history='PRICE_HISTORY_NOT_AVAILABLE';
 else{const past=[];for(const h of Array.isArray(hist)?hist:[]){if(!object(h)||!finite(h.value))continue;const c=closeAt(closes,h.period_end);if(c!==null)past.push(h.value/c);}
  if(past.length<MIN_HISTORY)r.own_history='HISTORY_TOO_SHORT';else{const current=ebit/shares/price;out.own_history=percentile(current,[...past,current]);}}
 const realized=v.revenue_cagr_3y;out.realized_growth=finite(realized)?realized:null;
 if(!finite(fcf))r.gap='FCF_NOT_AVAILABLE';
 else{const rev=E.reverseDcf({cashflow_per_share:fcf/shares,price,parameters,cashflow_currency:v.currency,price_currency:quote.currency});
  if(rev.state==='NOT_AVAILABLE')r.gap=rev.reason_codes[0];else{out.implied_growth=rev.implied_growth;if(!finite(realized))r.gap='REALIZED_GROWTH_NOT_AVAILABLE';else out.gap=rev.implied_growth-realized;}}
 if(!finite(debt)||!finite(cash)||debt<0||cash<0)return fail('DEBT_CASH_NOT_AVAILABLE',['ebit_yield','fcf_yield']);
 const ev=price*shares+debt-cash;if(!(ev>0))return fail('EV_NON_POSITIVE',['ebit_yield','fcf_yield']);
 if(finite(ebit))out.ebit_yield=ebit/ev;else r.ebit_yield='EBIT_NOT_AVAILABLE';
 if(finite(fcf))out.fcf_yield=fcf/ev;else r.fcf_yield='FCF_NOT_AVAILABLE';
 return out;}
// Price-free DCF '참고 범위' (not a factor): FCF per share at the explicit-growth rule's lower and upper bounds.
function referenceRange(company,parameters){
 const E=engine(),v=object(company)&&object(company.v_inputs)?company.v_inputs:null,na=reason=>({state:'NOT_AVAILABLE',reason,low:null,high:null});
 if(object(company)&&company.profile==='FINANCIAL')return na('FINANCIAL_PROFILE_V_NOT_DEFINED');
 if(!v||!finite(v.fcf)||!positive(v.diluted_shares))return na('FCF_NOT_AVAILABLE');
 const rule=object(parameters)&&object(parameters.explicit_growth_rule)?parameters.explicit_growth_rule:null;if(!rule)return na('EXPLICIT_GROWTH_UNDECIDED');
 const cf=v.fcf/v.diluted_shares;if(!(cf>0))return na('NON_POSITIVE_CASHFLOW');const ends=[];
 for(const g of [rule.lower,rule.upper]){const x=E.dcf({cashflow_per_share:cf,growth_rate:g,parameters,cashflow_currency:v.currency});if(x.state==='NOT_AVAILABLE')return na(x.reason_codes[0]);ends.push(x.value_per_share);}
 return{state:'PROVISIONAL',reason:null,low:ends[0],high:ends[1]};}
function cross(values,groups,ids,industry){
 const pop=ids.filter(i=>values[i]!==null),out={};
 for(const i of ids){if(values[i]===null)continue;if(pop.length<MIN_UNIVERSE){out[i]=[null,'CROSS_SECTION_TOO_SMALL',null,pop.length];continue;}
  let basis='UNIVERSE',peers=pop;if(industry){const g=groups[i],members=pop.filter(j=>g!==null&&g!==undefined&&groups[j]===g);if(g!==null&&g!==undefined&&members.length>=MIN_PEERS){basis='INDUSTRY';peers=members;}else basis='UNIVERSE_FALLBACK';}
  out[i]=[percentile(values[i],peers.map(j=>values[j])),null,basis,peers.length];}
 return out;}
/* companies: {code: {industry_group, profile, factors, v_inputs, memberships}}; quotes: {code: {price, currency, closes?}} (RAM).
   Returns {code: result}. */
function scoreUniverse(companies,quotes,{typeConfig=typeDefaults(),parameters=dcfDefaults(),preset=DEFAULT_PRESET,gate=null}={}){
 if(!Object.hasOwn(PRESETS,preset))throw Error('PRESET_INVALID');
 const gateOn=gate===null||gate===undefined?GATE_DEFAULT:Boolean(gate),ids=Object.keys(object(companies)?companies:{}).sort(),groups={},fallback={};
 for(const i of ids){const g=companies[i].industry_group;groups[i]=g===undefined?null:g;}for(const p of PILLARS)fallback[p]=typeConfig.fallback.weights[p];
 const Q=object(quotes)?quotes:{},qg={},qAxis={},gAxis={},m={};
 for(const i of ids){const f=object(companies[i].factors)?companies[i].factors:{};qg[i]={};for(const k of QG_FACTORS){const v=Object.hasOwn(f,k)?f[k]:null;qg[i][k]=finite(v)&&v>=0&&v<=100?v:null;}qAxis[i]=axisScore(qg[i],'Q');gAxis[i]=axisScore(qg[i],'G');}
 const map=fn=>{const o={};for(const i of ids)o[i]=fn(i);return o;};
 const qPct=cross(map(i=>qAxis[i].score),groups,ids,true);
 for(const i of ids)m[i]=metrics(companies[i],Object.hasOwn(Q,i)?Q[i]:null,parameters);
 const ey=cross(map(i=>m[i].ebit_yield),groups,ids,false),fy=cross(map(i=>m[i].fcf_yield),groups,ids,false),ind=cross(map(i=>m[i].ebit_yield),groups,ids,true),exp=cross(map(i=>m[i].gap===null?null:-m[i].gap),groups,ids,false);
 const pw=PRESETS[preset].weights,results={};
 for(const i of ids){const c=companies[i],x=m[i],factors={};
  for(const k of QG_FACTORS){const s=qg[i][k];factors[k]={score:s,state:s===null?'NOT_AVAILABLE':'PUBLIC',reason:s===null?'SEC_FACTOR_NOT_AVAILABLE':null,basis:null};}
  for(const[k,cr,key]of [['v_earnings_yield',ey,'ebit_yield'],['v_fcf_yield',fy,'fcf_yield'],['v_vs_industry',ind,'ebit_yield'],['v_expectation_check',exp,'gap']]){
   if(Object.hasOwn(cr,i)&&cr[i][0]!==null)factors[k]={score:cr[i][0],state:'CALCULATED',reason:null,basis:cr[i][2]};
   else factors[k]={score:null,state:'NOT_AVAILABLE',reason:Object.hasOwn(cr,i)?cr[i][1]:(Object.hasOwn(x.reasons,key)?x.reasons[key]:null),basis:null};}
  const oh=x.own_history;factors.v_vs_own_history=oh!==null?{score:oh,state:'CALCULATED',reason:null,basis:'OWN_HISTORY'}:{score:null,state:'NOT_AVAILABLE',reason:Object.hasOwn(x.reasons,'own_history')?x.reasons.own_history:null,basis:null};
  const vs={};for(const k of Object.keys(WEIGHTS.V))vs[k]=factors[k].score;
  const axes={Q:qAxis[i],G:gAxis[i],V:axisScore(vs,'V')},[tw,typeReason,selected]=typeAxisWeights(c.memberships,typeConfig),weights=compositeWeights(pw,tw,fallback),flags=[];
  const qp=Object.hasOwn(qPct,i)?qPct[i]:null,qPercentile=qp?qp[0]:null,qBasis=qp?qp[2]:null,trap=gateOn&&qPercentile!==null&&qPercentile<GATE_PERCENTILE;
  if(trap)flags.push('VALUE_TRAP_CAUTION');if(gateOn&&qPercentile===null)flags.push('GATE_NOT_EVALUATED');if(axes.V.score===null)flags.push('V_NOT_AVAILABLE');
  let data=0;for(const p of PILLARS)if(axes[p].score!==null)data+=weights[p];
  const included=PILLARS.filter(p=>axes[p].score!==null&&!(p==='V'&&trap));let total=null,totalReason=null;
  if(data/100<MIN_AXIS_WEIGHT||!included.length)totalReason='AXIS_WEIGHT_INSUFFICIENT';else{let acc=0,used=0;for(const p of included){acc+=weights[p]*axes[p].score;used+=weights[p];}total=acc/used;}
  let available=0;for(const k of FACTORS)if(factors[k].score!==null)available++;
  results[i]={version:VERSION,status:STATUS,profile:{preset,gate:gateOn,id:VERSION+'/'+preset+'/gate-'+(gateOn?'on':'off')},axes,factors,factors_available:available,factors_total:FACTORS.length,
   q_industry_percentile:qPercentile,q_industry_basis:qBasis,type_weights:tw,type_reason:typeReason,selected_types:selected,weights,v_excluded:trap?'VALUE_TRAP_GATE':null,total,total_reason:totalReason,flags,
   detail:{ebit_yield:x.ebit_yield,fcf_yield:x.fcf_yield,implied_growth:x.implied_growth,realized_growth:x.realized_growth,expectation_gap:x.gap,industry_basis:factors.v_vs_industry.basis,industry_peers:Object.hasOwn(ind,i)?ind[i][3]:null},
   reference_range:referenceRange(c,parameters)};}
 return results;}
return Object.freeze({VERSION,STATUS,PILLARS,WEIGHTS,FACTORS,QG_FACTORS,PRESETS,DEFAULT_PRESET,GATE_DEFAULT,GATE_PERCENTILE,MIN_PEERS,MIN_UNIVERSE,MIN_AXIS_WEIGHT,MIN_HISTORY,CLOSE_WINDOW_DAYS,
 percentile,axisScore,typeAxisWeights,compositeWeights,closeAt,scoreUniverse});
});
