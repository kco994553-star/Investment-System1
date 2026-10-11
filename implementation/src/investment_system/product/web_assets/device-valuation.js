/* sec-valuation-inputs.json reader (price-free, fcfe/1) and the RAM-only device value view (v1+dcf_v1_default).
   The device price is a transient argument: no result field, storage key or request carries it or anything derived from it.
   Python reference: qgv/device_valuation.py (vectors: tests/fixtures/device_valuation_reference_v1.json). */
(function(root,factory){const node=typeof module==='object'&&module.exports;const api=factory(node?()=>require('./engine-preview.js'):()=>root.EnginePreview,node?()=>require('./type-config-defaults.js'):()=>root.TypeConfigDefaults);if(node)module.exports=api;else root.DeviceValuation=api;})(typeof globalThis==='object'?globalThis:this,function(engine,typeDefaults){
'use strict';
const FILE='sec-valuation-inputs.json',KIND='SEC_VALUATION_INPUTS',MAX=2*1024*1024,DEFAULT_STATUS='V1_UNCALIBRATED_DEFAULT';
const IDS=['asml','lrcx','klac','tokyo_electron','hanmi','nvda','amd','avgo','qcom','intc','msft','googl','amzn','rtx','stry','etn','hubb','gev','rok'];
const STATES=['LIVE','STALE','NOT_AVAILABLE'],FORMS=['10-K','10-K/A'];
const REASONS=['NO_ELIGIBLE_INPUT','SOURCE_NOT_AVAILABLE','SYNTHETIC_INPUT_NOT_PUBLIC','SOURCE_AFTER_AS_OF','STALE_INPUT','UPSTREAM_NOT_AVAILABLE','TYPE_ENGINE_PENDING_MERGE','CRITERIA_UNDEFINED','PUBLIC_FX_EXCLUDED','UNAPPROVED_ENGINE_INPUT_MAPPING'];
const ALTERNATIVES={operating_cash_flow:[['NetCashProvidedByUsedInOperatingActivities'],['NetCashProvidedByUsedInOperatingActivitiesContinuingOperations']],
 capital_expenditure:[['PaymentsToAcquirePropertyPlantAndEquipment'],['PaymentsToAcquireProductiveAssets']],
 long_term_debt_issuance:[['ProceedsFromIssuanceOfLongTermDebt'],['ProceedsFromIssuanceOfSeniorLongTermDebt']],
 long_term_debt_repayment:[['RepaymentsOfLongTermDebt'],['RepaymentsOfSeniorDebt']],
 net_short_term_borrowing:[['ProceedsFromRepaymentsOfShortTermDebt'],['ProceedsFromRepaymentsOfCommercialPaper'],['ProceedsFromShortTermDebt','RepaymentsOfShortTermDebt']],
 diluted_shares:[['WeightedAverageNumberOfDilutedSharesOutstanding']]};
const COMPONENTS=Object.keys(ALTERNATIVES);
const FCFE_REASONS=['SEC_INPUT_NOT_AVAILABLE','US_GAAP_CASH_FLOW_NOT_REPORTED','PERIOD_AMBIGUOUS','CURRENCY_AMBIGUOUS','COMPONENT_CURRENCY_MISMATCH','COMPONENT_AMBIGUOUS','MIXED_FILINGS','DILUTED_SHARES_NON_POSITIVE','NUMERIC_INVALID',...COMPONENTS.map(k=>k.toUpperCase()+'_MISSING')];
const V_KEYS=['eps','revenue','revenue_prev'],V_REASONS=['SEC_INPUT_NOT_AVAILABLE','SEC_INPUT_AMBIGUOUS','EPS_MISSING','REVENUE_MISSING','REVENUE_PREV_MISSING'];
const V_ORDER=['fundamental_value','peer_relative_value','historical_valuation','sector_context','theme_premium_discount','reverse_dcf','margin_of_safety'];
const number=v=>typeof v==='number'&&Number.isFinite(v),hash=v=>typeof v==='string'&&/^[0-9a-f]{64}$/.test(v),ccy=v=>typeof v==='string'&&/^[A-Z]{3}$/.test(v);
function need(v){if(!v)throw Error('PUBLIC_SCREEN_INVALID');}
function object(v){return v!==null&&typeof v==='object'&&!Array.isArray(v);}
function keys(v,ks){need(object(v)&&Object.keys(v).length===ks.length&&ks.every(k=>Object.hasOwn(v,k)));}
function clock(v){need(typeof v==='string'&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$/.test(v));const n=Date.parse(v);need(Number.isFinite(n));return n;}
function day(v){need(typeof v==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&new Date(v+'T00:00:00Z').toISOString().slice(0,10)===v);return Date.parse(v+'T00:00:00Z');}
function aggregate(states){return states.includes('LIVE')?'LIVE':states.includes('STALE')?'STALE':'NOT_AVAILABLE';}
// Same summation order as product/sec_valuation_inputs.fcfe_total.
function fcfeTotal(c){return c.operating_cash_flow.value-c.capital_expenditure.value+c.long_term_debt_issuance.value+c.net_short_term_borrowing.value-c.long_term_debt_repayment.value;}
function unique(list){return new Set(list).size===list.length;}
function validateFcfe(f,rowState){
 keys(f,['state','reason_codes','fcfe_per_share','currency','fiscal_period_start','fiscal_period_end','accn','form','components']);
 need(['NOT_AVAILABLE',rowState].includes(f.state)&&Array.isArray(f.reason_codes)&&unique(f.reason_codes)&&f.reason_codes.every(r=>FCFE_REASONS.includes(r)));
 need(f.currency===null||ccy(f.currency));need((f.fiscal_period_start===null)===(f.fiscal_period_end===null));
 if(f.fiscal_period_end!==null){const days=(day(f.fiscal_period_end)-day(f.fiscal_period_start))/86400000;need(days>=300&&days<=400);}
 need(f.accn===null||typeof f.accn==='string'&&/^\d{18}$/.test(f.accn));need(f.form===null||FORMS.includes(f.form));
 keys(f.components,COMPONENTS);
 for(const k of COMPONENTS){const c=f.components[k];if(c===null)continue;keys(c,['concepts','value']);need(Array.isArray(c.concepts)&&ALTERNATIVES[k].some(a=>a.length===c.concepts.length&&a.every((x,i)=>x===c.concepts[i]))&&number(c.value));}
 if(f.state==='NOT_AVAILABLE'){need(f.fcfe_per_share===null&&f.reason_codes.length>0);return;}
 need(f.reason_codes.length===0&&COMPONENTS.every(k=>f.components[k]!==null)&&f.currency!==null&&f.fiscal_period_end!==null&&f.accn!==null&&f.form!==null);
 const shares=f.components.diluted_shares.value;need(shares>0&&number(f.fcfe_per_share));
 const expected=fcfeTotal(f.components)/shares;need(Math.abs(f.fcfe_per_share-expected)<=Math.max(1e-12,1e-12*Math.max(Math.abs(expected),Math.abs(f.fcfe_per_share))));
}
function validateV(v,rowState){
 keys(v,['state','reason_codes','eps','revenue','revenue_prev','currency']);
 need(['NOT_AVAILABLE',rowState].includes(v.state)&&Array.isArray(v.reason_codes)&&unique(v.reason_codes)&&v.reason_codes.every(r=>V_REASONS.includes(r)));
 for(const k of V_KEYS)need(v[k]===null||number(v[k]));
 const present=V_KEYS.some(k=>v[k]!==null);need((v.state!=='NOT_AVAILABLE')===present);
 if(!present){need(v.currency===null&&v.reason_codes.length>0);}
 else{need(ccy(v.currency));const expected=V_KEYS.filter(k=>v[k]===null).map(k=>k.toUpperCase()+'_MISSING');need(JSON.stringify(v.reason_codes)===JSON.stringify(expected));}
}
function validate(name,p){
 need(name===FILE&&new TextEncoder().encode(JSON.stringify(p)).length<=MAX);
 keys(p,['schema_version','kind','as_of','state','sources','reason_codes','freshness_basis','stale_after_seconds','data']);
 need(p.schema_version===1&&p.kind===KIND&&STATES.includes(p.state)&&p.freshness_basis==='SOURCE_ACQUISITION'&&number(p.stale_after_seconds)&&p.stale_after_seconds>0);
 const cut=clock(p.as_of),fresh=stamp=>cut-stamp>p.stale_after_seconds*1000?'STALE':'LIVE';
 need(Array.isArray(p.reason_codes)&&p.reason_codes.every(r=>REASONS.includes(r))&&Array.isArray(p.sources)&&p.sources.length<=10000);
 const sources=new Map(),states=[],map={companyfacts:'SEC_COMPANYFACTS',submissions:'SEC_SUBMISSIONS'};
 for(const s of p.sources){keys(s,['agency','sha256','acquired_at']);need(['SEC_COMPANYFACTS','SEC_SUBMISSIONS'].includes(s.agency)&&hash(s.sha256));const stamp=clock(s.acquired_at),key=s.agency+':'+s.sha256;need(stamp<=cut&&(!sources.has(key)||sources.get(key)===stamp));sources.set(key,stamp);}
 const d=p.data;keys(d,['companies','method_status','availability_basis','fcfe_definition','share_basis']);
 need(d.method_status==='PROVISIONAL_UNCALIBRATED'&&d.availability_basis==='OBSERVED_CAPTURE_ONLY'&&d.fcfe_definition==='fcfe/1'&&d.share_basis==='WEIGHTED_AVERAGE_DILUTED');
 keys(d.companies,IDS);
 for(const r of Object.values(d.companies)){
  keys(r,['state','source_hashes','fcfe','v_inputs']);need(STATES.includes(r.state));validateFcfe(r.fcfe,r.state);validateV(r.v_inputs,r.state);
  const inner=[r.fcfe.state,r.v_inputs.state];need(r.state===(inner.every(s=>s==='NOT_AVAILABLE')?'NOT_AVAILABLE':inner.find(s=>s!=='NOT_AVAILABLE')));
  need(object(r.source_hashes)&&Object.keys(r.source_hashes).every(k=>Object.hasOwn(map,k)));for(const[k,v]of Object.entries(r.source_hashes))need(hash(v)&&sources.has(map[k]+':'+v));
  if(r.state!=='NOT_AVAILABLE'){keys(r.source_hashes,Object.keys(map));need(r.state===fresh(sources.get('SEC_SUBMISSIONS:'+r.source_hashes.submissions)));}
  states.push(r.state);
 }
 need(p.state===aggregate(states));
 return p;
}
async function load(view){
 const control=new view.AbortController(),timer=setTimeout(()=>control.abort(),20000);
 try{const r=await view.fetch(FILE,{cache:'no-store',credentials:'omit',referrerPolicy:'no-referrer',redirect:'error',signal:control.signal});if(!r.ok)return null;const text=await r.text();if(new TextEncoder().encode(text).length>MAX)return null;return validate(FILE,JSON.parse(text));}
 catch(_){return null;}finally{clearTimeout(timer);}
}
function row(payload,id){const c=payload&&payload.data&&payload.data.companies;return c&&Object.hasOwn(c,id)?c[id]:null;}
function parameters(){const t=typeDefaults();return t&&t.dcf?t.dcf:null;}
const na=reason=>({score:null,state:'NOT_AVAILABLE',reason});
// Mirror of qgv/device_valuation.device_value_view. `quote` is {price,currency} held only in RAM by the caller.
function view({row:r=null,quote=null,parameters:p=parameters()}={}){
 const E=engine(),status=object(p)&&typeof p.status==='string'?p.status:null,fcfe=object(r)&&object(r.fcfe)?r.fcfe:null,v=object(r)&&object(r.v_inputs)?r.v_inputs:null;
 const fcfeValue=fcfe&&fcfe.state!=='NOT_AVAILABLE'?fcfe.fcfe_per_share:null,price=object(quote)&&quote.price!==undefined?quote.price:null,priceCurrency=object(quote)?quote.currency:undefined;
 const reasons=[];if(fcfeValue===null||fcfeValue===undefined)reasons.push('FCFE_NOT_AVAILABLE');if(price===null)reasons.push('NO_DEVICE_PRICE');
 let reverse;if(reasons.length)reverse={state:'NOT_AVAILABLE',reason_codes:reasons,implied_growth:null};
 else{const x=E.reverseDcf({cashflow_per_share:fcfeValue,price,parameters:p,cashflow_currency:fcfe.currency,price_currency:priceCurrency});reverse={state:x.state,reason_codes:[...x.reason_codes],implied_growth:x.implied_growth};}
 const implied=reverse.implied_growth;
 const inputs={eps:v?v.eps:null,revenue:v?v.revenue:null,revenue_prev:v?v.revenue_prev:null,reverse_dcf_implied_growth:implied,basis_confirmed:!!v&&v.currency!==null&&v.currency!==undefined&&v.currency===priceCurrency};
 const result=E.vFactors({inputs,price}),factors={...result.factors};
 if(implied===null)factors.reverse_dcf=na('REVERSE_DCF_NOT_AVAILABLE');
 factors.margin_of_safety=na('EXPLICIT_GROWTH_UNDECIDED');
 return{version:status===DEFAULT_STATUS?'v1+dcf_v1_default':'v1+dcf_custom',parameters_status:status,role:'RAM_ONLY_DEVICE',
  dcf:{state:'NOT_AVAILABLE',reason_codes:['EXPLICIT_GROWTH_UNDECIDED'],value_per_share:null},reverse_dcf:reverse,
  v_factors:Object.fromEntries(V_ORDER.map(k=>[k,{score:factors[k].score,state:factors[k].state,reason:factors[k].reason}])),standard_status:result.standard_status};
}
// Device quote for one ticker from this device's stored market data (existing DeviceActual storage), RAM only.
async function deviceQuote(win,catalog,ticker){
 try{const q=win.DeviceActual&&win.DeviceActual.ramQuote?await win.DeviceActual.ramQuote(win,catalog,ticker):null;return q&&number(q.price)&&q.price>0&&ccy(q.currency)?q:null;}catch(_){return null;}
}
return Object.freeze({FILE,KIND,IDS,ALTERNATIVES,FCFE_REASONS,V_REASONS,validate,load,row,parameters,view,deviceQuote,fcfeTotal});
});
