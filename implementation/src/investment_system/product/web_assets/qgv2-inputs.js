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
 const[ebit,ebitP]=flow(v.ebit),[fcf,fcfP]=flow(v.fcf),[revenue,revenueP]=flow(v.revenue),periods={};if(ebitP)periods.ebit=ebitP;if(fcfP)periods.fcf=fcfP;if(revenueP)periods.revenue=revenueP;
 for(const k of ['total_debt','cash_and_equivalents','diluted_shares'])if(object(v[k])&&typeof v[k].period_end==='string')periods[k]=v[k].period_end;
 return[{currency:v.currency,ebit,fcf,revenue,operating_margin_history:history(v.operating_margin_history),total_debt:value(v.total_debt),cash:value(v.cash_and_equivalents),diluted_shares:value(v.diluted_shares),ebit_per_share_history:history(v.ebit_per_share_history),revenue_cagr_3y:finite(v.revenue_cagr_3y)?v.revenue_cagr_3y:null},periods];
}
/* calc_version (QGV_V2_QG_METHOD.md 5): a row whose calculation-rule version differs from the file's declared version (or a row
   without one in a versioned file) is NOT ranked with the others: it leaves the cross-section and every device percentile
   population, and the accessor shows it as NA with reason CALC_VERSION_MISMATCH. An unversioned (legacy) file is one population. */
function versionMismatch(r,fileVersion){return typeof fileVersion==='string'&&object(r)&&r.state!=='NOT_AVAILABLE'&&r.fiscal_year_end!==null&&r.fiscal_year_end!==undefined&&r.calc_version!==fileVersion;}
function normalize(r,pooled){
 const f=object(r)&&object(r.factors)?r.factors:{},factors={};for(const k of FACTORS)factors[k]=score(Object.hasOwn(f,k)?f[k]:null);
 const has=object(r)&&r.state!=='NOT_AVAILABLE'&&r.fiscal_year_end!==null&&r.fiscal_year_end!==undefined,[v,periods]=has?vInputs(r.v_inputs_v2):[null,{}],ax=object(r)&&object(r.axes)?r.axes:{};
 const years=object(r)&&object(r.metrics)&&Array.isArray(r.metrics.ebit_estimated_fiscal_years)&&r.metrics.ebit_estimated_fiscal_years.every(y=>Number.isInteger(y)&&y>=1900&&y<=2100)?{ebit_estimated_fiscal_years:[...r.metrics.ebit_estimated_fiscal_years]}:{};
 // Rows without data keep their published source reason codes (NOT_COLLECTED, CIK_UNRESOLVED, NO_ANNUAL_SEC_FINANCIALS, ...):
 // they are outside every ranking population but stay in the 504-code denominator with an explicit NA reason.
 const naReasons=object(r)&&!has&&Array.isArray(r.reason_codes)?r.reason_codes.filter(x=>typeof x==='string'&&/^[A-Z][A-Z0-9_]{0,63}$/.test(x)):[];
 return{na_reasons:naReasons,metrics:object(r)&&object(r.metrics)?{...Object.fromEntries(Object.entries(r.metrics).filter(([k,v])=>/^[a-z][a-z0-9_]{0,63}$/.test(k)&&finite(v))),...years}:{},sic:object(r)&&typeof r.sic==='string'&&/^\d{4}$/.test(r.sic)?r.sic:null,cik:object(r)&&typeof r.cik==='string'?r.cik:null,industry_group:object(r)&&typeof r.industry_group==='string'&&GROUP.test(r.industry_group)?r.industry_group:null,profile:object(r)&&r.profile==='FINANCIAL'?'FINANCIAL':'GENERAL',
  factors,qg_axes:{Q:{score:object(ax.Q)?score(ax.Q.score):null},G:{score:object(ax.G)?score(ax.G.score):null}},v_inputs:v,periods,state:object(r)&&['LIVE','STALE'].includes(r.state)?r.state:'NOT_AVAILABLE',in_cross_section:pooled};
}
/* Identity-conflict withdrawal (owner instruction 2026-10-17 item 3; sec-qgv2.json TARGET withdrawal rows, Python
   sec_qgv2.WITHDRAWN_REASON): a withdrawn TARGET issuer is used nowhere on this device. Its TARGET record and every Universe
   code of the same CIK (other share classes and codes) carry no factors, axes, V inputs or metrics, leave every ranking
   population and candidate list, and show the reason IDENTITY_CONFLICT_WITHDRAWN (`identity_withdrawn`). Their state is
   WITHDRAWN, not NOT_AVAILABLE: QgvScores falls back from a NOT_AVAILABLE TARGET row to the Universe code of the same ticker,
   and a withdrawn TARGET issuer must not be scored through any other code or CIK. The withdrawal row itself has no values
   and nothing is read from an earlier copy or another row. */
const WITHDRAWN_REASON='IDENTITY_CONFLICT_WITHDRAWN';
const withdrawn=r=>object(r)&&(Object.hasOwn(r,'detected_at')||Array.isArray(r.reason_codes)&&r.reason_codes.includes(WITHDRAWN_REASON));
function stopped(rec){return{...rec,state:'WITHDRAWN',na_reasons:[WITHDRAWN_REASON],metrics:{},sic:null,industry_group:null,factors:Object.fromEntries(FACTORS.map(k=>[k,null])),qg_axes:{Q:{score:null},G:{score:null}},v_inputs:null,periods:{},in_cross_section:false,identity_withdrawn:true};}
const frozenCopy=x=>{const copy=JSON.parse(JSON.stringify(x));function freeze(v){if(object(v)||Array.isArray(v)){Object.values(v).forEach(freeze);Object.freeze(v);}return v;}return freeze(copy);};
/* SecQgv2.toInputs() result (or a lightly checked payload) -> {as_of, records:{key: record}, count}. */
function fromInputs(inputs){
 if(!object(inputs)||!object(inputs.records))throw Error('SEC_QGV2_INVALID');
 const records={},seen=new Set(),version=typeof inputs.calc_version==='string'?inputs.calc_version:null;
 const mark=(rec,r)=>{if(!versionMismatch(r,version))return rec;return{...rec,factors:Object.fromEntries(FACTORS.map(k=>[k,null])),qg_axes:{Q:{score:null},G:{score:null}},v_inputs:null,in_cross_section:false,calc_version_mismatch:true};};
 const targets=object(inputs.target)?inputs.target:{},withdrawnCiks=new Set(Object.values(targets).filter(withdrawn).map(r=>r.cik).filter(c=>typeof c==='string'));
 for(const code of Object.keys(inputs.records).sort()){if(!CODE.test(code))throw Error('SEC_QGV2_INVALID');const r=inputs.records[code],cik=object(r)?r.cik:null,stop=withdrawn(r)||typeof cik==='string'&&withdrawnCiks.has(cik),live=!stop&&object(r)&&['LIVE','STALE'].includes(r.state);
  const mismatch=versionMismatch(r,version),pooled=live&&!mismatch&&!(cik&&seen.has(cik));if(live&&!mismatch&&cik)seen.add(cik);records[code]=stop?{...stopped(normalize(r,false)),universe_withdrawal:withdrawn(r)}:mark(normalize(r,pooled),r);}
 for(const[id,r]of Object.entries(targets)){if(!ID.test(id))throw Error('SEC_QGV2_INVALID');records['TARGET:'+id]=withdrawn(r)?stopped(normalize(r,false)):mark(normalize(r,false),r);}
 // Keep the source TARGET rows in RAM for exact-period disclosure confirmation. The strict reader supplies these rows;
 // normalization must not discard their price-free source dates or replace them with an inferred confirmation.
 return Object.freeze({as_of:typeof inputs.as_of==='string'?inputs.as_of:null,calc_version:version,target:frozenCopy(object(inputs.target)?inputs.target:{}),records:Object.freeze(records),count:Object.keys(records).length});
}
// Light structural check used only when the strict SecQgv2 reader is absent; price-like keys fail closed.
function light(p){
 const bad=/"(price|prices|market_?cap|marketcap|ev|enterprise_value|v_score|rank)"\s*:/i;
 if(!object(p)||p.kind!==KIND||!object(p.records)||bad.test(JSON.stringify(p)))throw Error('SEC_QGV2_INVALID');return p;
}
/* Why the last load returned null (owner instruction 2026-10-17, #289 item 3): 'SCHEMA_NEWER' when the file is a newer data format
   than this page reads (SecQgv2.ERR_NEWER; the screens ask for a reload instead of showing nothing), 'UNAVAILABLE' otherwise,
   null after a successful load. Nothing earlier is kept: a rejected file leaves no scores in RAM. */
let lastReason=null;
const NEWER=/_SCHEMA_NEWER$/;
async function load(view,{signal}={}){
 lastReason=null;
 try{
  if(view.SecQgv2&&typeof view.SecQgv2.loadInputs==='function'){const x=await view.SecQgv2.loadInputs(view,{signal});if(!x)lastReason='UNAVAILABLE';return x?fromInputs(x):null;}
  const r=await view.fetch(FILE,{cache:'no-cache',credentials:'omit',referrerPolicy:'no-referrer',redirect:'error',signal,headers:{Accept:'application/json'}});if(!r.ok){lastReason='UNAVAILABLE';return null;}
  const text=await r.text();if(new TextEncoder().encode(text).length>MAX){lastReason='UNAVAILABLE';return null;}const p=JSON.parse(text);if(object(p)&&p.kind===KIND&&Number.isInteger(p.schema_version)&&p.schema_version>2)throw Error('SEC_QGV2_SCHEMA_NEWER');return fromInputs(light(p));
 }catch(e){lastReason=NEWER.test(String(e&&e.message))?'SCHEMA_NEWER':'UNAVAILABLE';return null;}
}
return Object.freeze({FILE,KIND,FACTORS,WITHDRAWN_REASON,normalize,fromInputs,light,load,lastReason:()=>lastReason});
});
