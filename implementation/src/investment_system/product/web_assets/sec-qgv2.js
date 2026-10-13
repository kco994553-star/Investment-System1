/* Public price-free `sec-qgv2.json` reader (QGV v2 Q·G from SEC; produced by the Q·G side in Actions). ISOLATED ADAPTER: the
   producer's file shape is not merged yet, so this reader accepts the ASSUMED shape documented in
   docs/qgv_scoring_standard/QGV_V2_V_DEVICE.md §6 and normalizes each row to the internal record QgvV2.scoreUniverse takes:
   {industry_group, profile, factors:{q_*,g_*: 0..100|null}, v_inputs:{currency, ebit, fcf, total_debt, cash, diluted_shares,
   ebit_per_share_history:[{period_end,value}], revenue_cagr_3y}, periods:{...labels}}. Only normalize() should change when the
   real shape lands. The file carries no price, market cap, EV, V score or rank; nothing here is stored. 404 -> null. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.SecQgv2=api;})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
const FILE='sec-qgv2.json',KIND='SEC_QGV2',MAX=4*1024*1024;
const FACTORS=Object.freeze(['q_profitability','q_moat_proxy','q_earnings_quality','q_financial_safety','q_capital_allocation','g_revenue_growth','g_per_share_growth','g_growth_efficiency','g_consistency','g_recent_acceleration']);
const CODE=/^[A-Z]{2,8}:[A-Z0-9][A-Z0-9.\-]{0,15}$/,DAY=/^\d{4}-\d{2}-\d{2}$/,GROUP=/^[a-z][a-z0-9_]{0,63}$/;
const object=v=>v!==null&&typeof v==='object'&&!Array.isArray(v),finite=v=>typeof v==='number'&&Number.isFinite(v);
function need(x){if(!x)throw Error('SEC_QGV2_INVALID');}
// A value is a number or {value, period_end|period_label|fiscal_period_end, ...}; anything else is null (NOT_AVAILABLE).
const num=x=>finite(x)?x:object(x)&&finite(x.value)?x.value:null;
const label=x=>{if(!object(x))return null;for(const k of ['period_label','period_end','fiscal_period_end','period'])if(typeof x[k]==='string'&&x[k].length<=32)return x[k];return null;};
const pick=(o,keys)=>{for(const k of keys)if(object(o)&&Object.hasOwn(o,k))return o[k];return undefined;};
function score(x){const v=num(object(x)&&Object.hasOwn(x,'score')?x.score:x);return v!==null&&v>=0&&v<=100?v:null;}
function history(list){
 const out=[];if(!Array.isArray(list))return out;
 for(const h of list){if(!object(h))continue;const pe=pick(h,['period_end','fiscal_period_end']),v=num(pick(h,['value','per_share','ebit_per_share']));if(typeof pe==='string'&&DAY.test(pe)&&v!==null)out.push({period_end:pe,value:v});}
 return out.sort((a,b)=>a.period_end<b.period_end?-1:a.period_end>b.period_end?1:0);
}
function vInputs(v){
 if(!object(v))return[null,{}];
 const ccy=pick(v,['currency']),ocf=num(pick(v,['ocf','operating_cash_flow'])),capex=num(pick(v,['capex','capital_expenditure']));
 let fcf=num(pick(v,['fcf','free_cash_flow']));if(fcf===null&&ocf!==null&&capex!==null)fcf=ocf-Math.abs(capex);
 const hist=pick(v,['ebit_per_share_history'])??pick(pick(v,['history']),['ebit_per_share']);
 const fields={ebit:pick(v,['ebit']),fcf:pick(v,['fcf','free_cash_flow']),total_debt:pick(v,['total_debt']),cash:pick(v,['cash','cash_and_equivalents']),diluted_shares:pick(v,['diluted_shares','shares_diluted']),revenue_cagr_3y:pick(v,['revenue_cagr_3y','realized_revenue_growth','revenue_growth_3y'])};
 const periods={};for(const[k,x]of Object.entries(fields)){const l=label(x);if(l)periods[k]=l;}
 return[{currency:typeof ccy==='string'&&/^[A-Z]{3}$/.test(ccy)?ccy:null,ebit:num(fields.ebit),fcf,total_debt:num(fields.total_debt),cash:num(fields.cash),diluted_shares:num(fields.diluted_shares),
  ebit_per_share_history:history(hist),revenue_cagr_3y:num(fields.revenue_cagr_3y)},periods];
}
// One row of the assumed shape -> internal record. Unknown extra fields are ignored; wrong types become null.
function normalize(r){
 need(object(r));const f=object(r.factors)?r.factors:{},factors={};for(const k of FACTORS)factors[k]=score(Object.hasOwn(f,k)?f[k]:null);
 const g=pick(r,['industry_group','sic_group','industry']),profile=pick(r,['profile','profile_kind']),[v,periods]=vInputs(pick(r,['v_inputs_v2','v_inputs']));
 return{industry_group:typeof g==='string'&&GROUP.test(g)?g:null,profile:profile==='FINANCIAL'?'FINANCIAL':'GENERAL',factors,v_inputs:v,periods,
  state:['LIVE','STALE','NOT_AVAILABLE'].includes(r.state)?r.state:'NOT_AVAILABLE',sic:typeof r.sic==='string'&&/^\d{4}$/.test(r.sic)?r.sic:null};
}
function toInputs(p){
 try{need(object(p)&&p.kind===KIND);const rows=object(p.records)?p.records:object(p.companies)?p.companies:object(p.data)&&object(p.data.records)?p.data.records:null;need(rows);
  const records={};for(const[code,r]of Object.entries(rows)){need(CODE.test(code));records[code]=normalize(r);}need(Object.keys(records).length>0&&Object.keys(records).length<=1024);
  const forbidden=/"(price|prices|market_?cap|marketcap|ev|enterprise_value|v_score|rank)"\s*:/i;need(!forbidden.test(JSON.stringify(p)));
  return Object.freeze({as_of:typeof p.as_of==='string'?p.as_of:null,config_version:typeof p.config_version==='string'?p.config_version:null,method_status:typeof p.method_status==='string'?p.method_status:'PROVISIONAL',records,count:Object.keys(records).length});}
 catch(_){throw Error('SEC_QGV2_INVALID');}
}
async function load(view,{signal}={}){
 try{const r=await view.fetch(FILE,{cache:'no-cache',credentials:'omit',referrerPolicy:'no-referrer',redirect:'error',signal,headers:{Accept:'application/json'}});if(!r.ok)return null;
  const text=await r.text();if(new TextEncoder().encode(text).length>MAX)return null;return toInputs(JSON.parse(text));}catch(_){return null;}
}
return Object.freeze({FILE,KIND,FACTORS,normalize,toInputs,load});
});
