'use strict';
// The app-owned projection is tested directly, without reading any user state or making requests.
// During integration PROMPT_APP_SOURCE may point at Main's proposed app.js in an external preview.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const source=fs.readFileSync(process.env.PROMPT_APP_SOURCE || path.join(__dirname,'../src/investment_system/product/web_assets/app.js'),'utf8');
const projection=source.match(/\nfunction researchPublicContext\(\) \{[\s\S]*?\n\}/)?.[0];
const code=source.match(/\nfunction universeCode\(id\) \{[^\n]*\}/)?.[0];
if(!projection || !code)throw Error('Public projection functions are missing');
let checks=0;
function check(ok,message){if(!ok)throw Error(message);checks++;}
const alpha={company_id:'fixture-alpha',ticker:'FIXA',name:'Public Alpha'};
const beta={company_id:'fixture-beta',ticker:'FIXB',name:'Public Beta'};
function context({id=null,companies=[alpha,beta],identities=[],names=new Map()}={}) {
  const D={companies};
  const fail=()=>{throw Error('Private state, storage or network was read');};
  for(const key of ['portfolio','market','actual','account'])Object.defineProperty(D,key,{get:fail});
  const globals={D,researchCompanyId:id,identityCompanies:identities,companyNames:names,
    EXPIRES_AT:/^never$/,freshnessOf:()=>null};
  for(const key of ['localStorage','sessionStorage','indexedDB','DeviceActual','qgv2Quotes','companyQuote','fetch'])Object.defineProperty(globals,key,{get:fail});
  vm.createContext(globals);
  return vm.runInContext(code+projection+'\nresearchPublicContext()',globals);
}
const missing=context();
check(missing.selection?.company===null,'no explicit selection must have a missing company, never a catalog default');
const selected=context({id:alpha.company_id}).selection;
check(selected.company?.name===alpha.name && selected.company?.ticker===alpha.ticker,'selected identity is resolved from the public catalog');
check(Object.keys(selected.company).sort().join(',')==='company_id,name,ticker','exact identity allowlist');
check(selected.period===null && selected.period_reason==='PERIOD_MAPPING_UNSUPPORTED','period has no invented mapping');
check(context({id:'unknown'}).selection.company===null,'unknown selection does not reuse an older or first identity');
check(context({id:alpha.company_id,companies:[],identities:[alpha]}).selection.company?.ticker===alpha.ticker,'identity-only public catalog works without analysis data');
check(context({id:alpha.company_id,identities:[alpha]}).selection.company?.ticker===alpha.ticker,'identical identity in two public catalogs is not a conflict');
check(context({id:alpha.company_id,identities:[{...alpha,ticker:beta.ticker}]}).selection.company===null,'conflicting ticker for the selected id is withheld');
check(context({id:alpha.company_id,identities:[{...alpha,name:beta.name}]}).selection.company===null,'conflicting names for the selected id are withheld');
check(context({id:alpha.company_id,companies:[{...alpha,ticker:'not a ticker'}]}).selection.company===null,'malformed public ticker is withheld');
const unsafe=context({id:alpha.company_id,companies:[{...alpha,name:'sheet_id=canary',price:'canary',holdings:'canary'}]}).selection;
check(unsafe.company?.name===null && !JSON.stringify(unsafe).includes('canary'),'private-looking metadata and non-allowlisted properties never cross');
check(context({id:alpha.company_id,companies:[{...alpha,name:null}]}).selection.company?.name===null,'missing company name is represented without substitution');
const names=new Map([['NASDAQ:FIXU',{ticker:'FIXU',en_name:'Public Universe'}]]);
check(context({id:'NASDAQ:FIXU',names}).selection.company?.name==='Public Universe','known public Universe code resolves via reviewed names');
check(context({id:'NASDAQ:UNKNOWN',names}).selection.company===null,'unknown Universe code is withheld');
check(context({id:'NASDAQ:FIXU',names:new Map([['NASDAQ:FIXU',{ticker:'OTHER',en_name:'Wrong'}]])}).selection.company===null,'Universe code and public ticker must agree');
console.log('PASS prompt selected context projection: '+checks+' checks; no private state/network/storage access');
