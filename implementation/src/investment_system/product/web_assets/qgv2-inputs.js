/* QGV v2 device inputs from the public price-free `sec-qgv2.json` (Q·G side: universe/sec_qgv2.py, reader web_assets/sec-qgv2.js
   = SecQgv2). This adapter is the ONLY place that knows that file's shape: it turns a SecQgv2.toInputs() result (or, when the
   strict reader is not on the page, a lightly checked payload) into the records QgvV2.scoreUniverse takes:
   {cik, industry_group, profile, factors:{q_*,g_*}, qg_axes:{Q:{score},G:{score}} (published axes), v_inputs:{currency, ebit, fcf,
   total_debt, cash, diluted_shares, ebit_per_share_history:[{period_end,value}], revenue_cagr_3y}, periods, in_cross_section}.
   EBIT/FCF use the TTM value when published, else the fiscal-year value. Universe rows are keyed by code (one cross-section
   point per CIK); TARGET rows by 'TARGET:<id>' (scored against the cross-section, not added to it). Nothing here is stored. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.Qgv2Inputs=api;})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
const FILE='sec-qgv2.json',KIND='SEC_QGV2',MAX=2*1024*1024;
const FACTORS=Object.freeze(['q_profitability','q_moat_proxy','q_earnings_quality','q_financial_safety','q_capital_allocation','g_revenue_growth','g_per_share_growth','g_growth_efficiency','g_consistency','g_recent_acceleration']);
const CODE=/^[A-Z]{2,8}:[A-Z0-9][A-Z0-9.\-]{0,15}$/,ID=/^[a-z][a-z0-9_]{0,63}$/,DAY=/^\d{4}-\d{2}-\d{2}$/,GROUP=/^[a-z][a-z0-9_]{0,63}$/;
const object=v=>v!==null&&typeof v==='object'&&!Array.isArray(v),finite=v=>typeof v==='number'&&Number.isFinite(v);
const score=v=>finite(v)&&v>=0&&v<=100?v:null,value=x=>object(x)&&finite(x.value)?x.value:null;
function flow(x){if(!object(x))return[null,null];if(finite(x.ttm_value))return[x.ttm_value,typeof x.ttm_end==='string'?'TTM '+x.ttm_end:'TTM'];if(finite(x.fy_value))return[x.fy_value,typeof x.fy_end==='string'?'FY '+x.fy_end:'FY'];return[null,null];}
function history(list){const out=[];for(const h of Array.isArray(list)?list:[]){const pe=object(h)?h.fiscal_year_end:null;if(typeof pe==='string'&&DAY.test(pe)&&finite(h.value))out.push({period_end:pe,value:h.value});}return out.sort((a,b)=>a.period_end<b.period_end?-1:a.period_end>b.period_end?1:0);}
function vInputs(v){
 if(!object(v)||typeof v.currency!=='string'||!/^[A-Z]{3}$/.test(v.currency))return[null,{}];
 const[ebit,ebitP]=flow(v.ebit),[fcf,fcfP]=flow(v.fcf),periods={};if(ebitP)periods.ebit=ebitP;if(fcfP)periods.fcf=fcfP;
 for(const k of ['total_debt','cash_and_equivalents','diluted_shares'])if(object(v[k])&&typeof v[k].period_end==='string')periods[k]=v[k].period_end;
 return[{currency:v.currency,ebit,fcf,total_debt:value(v.total_debt),cash:value(v.cash_and_equivalents),diluted_shares:value(v.diluted_shares),ebit_per_share_history:history(v.ebit_per_share_history),revenue_cagr_3y:finite(v.revenue_cagr_3y)?v.revenue_cagr_3y:null},periods];
}
function normalize(r,pooled){
 const f=object(r)&&object(r.factors)?r.factors:{},factors={};for(const k of FACTORS)factors[k]=score(Object.hasOwn(f,k)?f[k]:null);
 const has=object(r)&&r.state!=='NOT_AVAILABLE'&&r.fiscal_year_end!==null&&r.fiscal_year_end!==undefined,[v,periods]=has?vInputs(r.v_inputs_v2):[null,{}],ax=object(r)&&object(r.axes)?r.axes:{};
 return{cik:object(r)&&typeof r.cik==='string'?r.cik:null,industry_group:object(r)&&typeof r.industry_group==='string'&&GROUP.test(r.industry_group)?r.industry_group:null,profile:object(r)&&r.profile==='FINANCIAL'?'FINANCIAL':'GENERAL',
  factors,qg_axes:{Q:{score:object(ax.Q)?score(ax.Q.score):null},G:{score:object(ax.G)?score(ax.G.score):null}},v_inputs:v,periods,state:object(r)&&['LIVE','STALE'].includes(r.state)?r.state:'NOT_AVAILABLE',in_cross_section:pooled};
}
/* SecQgv2.toInputs() result (or a lightly checked payload) -> {as_of, records:{key: record}, count}. */
function fromInputs(inputs){
 if(!object(inputs)||!object(inputs.records))throw Error('SEC_QGV2_INVALID');
 const records={},seen=new Set();
 for(const code of Object.keys(inputs.records).sort()){if(!CODE.test(code))throw Error('SEC_QGV2_INVALID');const r=inputs.records[code],live=object(r)&&['LIVE','STALE'].includes(r.state),cik=object(r)?r.cik:null;
  const pooled=live&&!(cik&&seen.has(cik));if(live&&cik)seen.add(cik);records[code]=normalize(r,pooled);}
 for(const[id,r]of Object.entries(object(inputs.target)?inputs.target:{})){if(!ID.test(id))throw Error('SEC_QGV2_INVALID');records['TARGET:'+id]=normalize(r,false);}
 return Object.freeze({as_of:typeof inputs.as_of==='string'?inputs.as_of:null,records:Object.freeze(records),count:Object.keys(records).length});
}
// Light structural check used only when the strict SecQgv2 reader is absent; price-like keys fail closed.
function light(p){
 const bad=/"(price|prices|market_?cap|marketcap|ev|enterprise_value|v_score|rank)"\s*:/i;
 if(!object(p)||p.kind!==KIND||!object(p.records)||bad.test(JSON.stringify(p)))throw Error('SEC_QGV2_INVALID');return p;
}
async function load(view,{signal}={}){
 try{
  if(view.SecQgv2&&typeof view.SecQgv2.loadInputs==='function'){const x=await view.SecQgv2.loadInputs(view,{signal});return x?fromInputs(x):null;}
  const r=await view.fetch(FILE,{cache:'no-cache',credentials:'omit',referrerPolicy:'no-referrer',redirect:'error',signal,headers:{Accept:'application/json'}});if(!r.ok)return null;
  const text=await r.text();if(new TextEncoder().encode(text).length>MAX)return null;return fromInputs(light(JSON.parse(text)));
 }catch(_){return null;}
}
return Object.freeze({FILE,KIND,FACTORS,normalize,fromInputs,light,load});
});
