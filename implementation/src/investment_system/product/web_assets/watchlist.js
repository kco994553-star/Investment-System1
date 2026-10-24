/* Device watchlist and company keys. Favorites never imply rank, scores or price.
   Owner decision 2026-10-23 (TARGET v0 결합 해소): the watchlist, ★ favorites, groups and memos are not limited to the TARGET v0
   catalog. Keys follow IA-7 (PRODUCT_IA_ONTOLOGY_CHECK_20261018): watch / group / memo = Issuer ('sec:' + CIK10), chart drawings =
   Listing (Universe code EXCHANGE:SYMBOL). A TARGET company_id is only an alias of its issuer; the two TARGET issuers without a SEC
   CIK (hanmi, tokyo_electron) keep the alias as their issuer key. Universe504 codes get their CIK from the reviewed company table
   (company-names-ko.json, field `cik`), cross-checked against the TARGET CIKs below; a code without a CIK has no issuer key and
   cannot be starred (no guess). Records written before this decision (TARGET company_id keys) are read and mapped by migrate();
   the caller keeps the original record. identities() still projects the TARGET v0 catalog for set A and the v0 lists. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.DeviceWatchlist=api;})(globalThis,function(){
'use strict';const IDS={ASML:'asml',LRCX:'lrcx',KLAC:'klac','8035':'tokyo_electron','042700':'hanmi',NVDA:'nvda',AMD:'amd',AVGO:'avgo',QCOM:'qcom',INTC:'intc',MSFT:'msft',GOOGL:'googl',AMZN:'amzn',RTX:'rtx',SYK:'stry',ETN:'etn',HUBB:'hubb',GEV:'gev',ROK:'rok'};
// TARGET v0 alias -> [Listing, CIK10 | null]. Same CIKs as SecQgv2.TARGET_CIKS; listings as company-names-ko.json / TradingView.
const TARGET=Object.freeze({asml:['NASDAQ:ASML','0000937966'],lrcx:['NASDAQ:LRCX','0000707549'],klac:['NASDAQ:KLAC','0000319201'],nvda:['NASDAQ:NVDA','0001045810'],amd:['NASDAQ:AMD','0000002488'],avgo:['NASDAQ:AVGO','0001730168'],qcom:['NASDAQ:QCOM','0000804328'],intc:['NASDAQ:INTC','0000050863'],msft:['NASDAQ:MSFT','0000789019'],googl:['NASDAQ:GOOGL','0001652044'],amzn:['NASDAQ:AMZN','0001018724'],rtx:['NYSE:RTX','0000101829'],stry:['NYSE:SYK','0000310764'],etn:['NYSE:ETN','0001551182'],hubb:['NYSE:HUBB','0000048898'],gev:['NYSE:GEV','0001996810'],rok:['NYSE:ROK','0001024478'],hanmi:['KRX:042700',null],tokyo_electron:['TSE:8035',null]});
const CODE=/^(NYSE|NASDAQ|BATS):([A-Z0-9][A-Z0-9.\-]{0,15})$/,LISTING=/^(NYSE|NASDAQ|BATS|KRX|TSE):([A-Z0-9][A-Z0-9.\-]{0,15})$/,ISSUER=/^sec:\d{10}$/;
const own=(o,k)=>Object.prototype.hasOwnProperty.call(o,k);
let codes=new Map();// Universe code -> issuer key | null (no CIK)
function useNames(index){const next=new Map();try{if(index&&typeof index.codes==='function'&&typeof index.get==='function')for(const[code,target]of index.codes()){if(!CODE.test(code))continue;const rec=index.get(code),cik=rec&&typeof rec.cik==='string'&&/^\d{10}$/.test(rec.cik)&&rec.cik!=='0000000000'?rec.cik:null;
  if(target!==null&&target!==undefined){if(!own(TARGET,target)||TARGET[target][0]!==code||TARGET[target][1]!==cik)continue;}next.set(code,cik?'sec:'+cik:null);}}catch(_){return false;}
 for(const[id,[code,cik]]of Object.entries(TARGET))if(cik&&CODE.test(code)&&!next.has(code))next.set(code,'sec:'+cik);codes=next;return true;}
useNames(null);
function isTarget(id){return typeof id==='string'&&own(TARGET,id);}
// Issuer key of a TARGET alias, a Universe code or an issuer key; null when it cannot be resolved.
function issuerOf(id){if(typeof id!=='string')return null;if(isTarget(id))return TARGET[id][1]?'sec:'+TARGET[id][1]:id;if(ISSUER.test(id))return id;if(codes.has(id))return codes.get(id);return null;}
// Listing of a TARGET alias or a Universe code (chart drawings, quotes, charts).
function listingOf(id){if(isTarget(id))return TARGET[id][0];return typeof id==='string'&&LISTING.test(id)&&(codes.has(id)||Object.values(TARGET).some(t=>t[0]===id))?id:null;}
// Private price Worker symbol of a listing (BRK.B -> BRK-B, KRX -> .KS, TSE -> .T).
function providerSymbol(id){const listing=listingOf(id)||(typeof id==='string'&&LISTING.test(id)?id:null),m=listing?LISTING.exec(listing):null;if(!m)return null;return m[1]==='KRX'?m[2]+'.KS':m[1]==='TSE'?m[2]+'.T':m[2].replace(/\./g,'-');}
function tickerOf(id){const l=listingOf(id);return l?l.split(':')[1]:null;}
// Every entity id (TARGET alias first, then Universe codes) of an issuer.
function entitiesOf(issuer){if(typeof issuer!=='string')return[];const out=[];for(const id of Object.keys(TARGET))if(issuerOf(id)===issuer)out.push(id);for(const[code,i]of[...codes.entries()].sort((a,b)=>a[0]<b[0]?-1:1))if(i===issuer&&!out.some(t=>TARGET[t]&&TARGET[t][0]===code))out.push(code);if(!out.length&&!ISSUER.test(issuer))out.push(issuer);return out;}
// The page that opens for an issuer: its TARGET alias when it has one (richer page), else its first Universe code.
function primaryOf(issuer){return entitiesOf(issuer)[0]||null;}
function listingsOf(issuer){return[...new Set(entitiesOf(issuer).map(listingOf).filter(Boolean))];}
// Old records (TARGET company_id keys, or codes) -> issuer keys. Order kept, duplicates dropped, unknown keys kept as they are.
function migrateList(list){const out=[];for(const id of Array.isArray(list)?list:[]){const k=issuerOf(id)||id;if(!out.includes(k))out.push(k);}return out;}
function migrate(p){const interests=migrateList(p.interests),groups=p.groups.map(g=>({...g,members:migrateList(g.members)}));
 const changed=JSON.stringify(interests)!==JSON.stringify(p.interests)||groups.some((g,i)=>JSON.stringify(g.members)!==JSON.stringify(p.groups[i].members));return{prefs:{...p,interests,groups},changed};}
function keyOf(id){return issuerOf(id)||id;}
function watched(prefs,id){const k=keyOf(id);return Array.isArray(prefs?.interests)&&prefs.interests.some(i=>keyOf(i)===k);}
// Page ids of the watched issuers (one per issuer, in added order) for screens keyed by company page id.
function pageIds(interests){return(Array.isArray(interests)?interests:[]).map(i=>primaryOf(i)||i).filter((x,i,a)=>x&&a.indexOf(x)===i);}
// Every id of the watched issuers (TARGET aliases and all their Universe codes).
function allIds(interests){const out=new Set();for(const i of Array.isArray(interests)?interests:[]){out.add(i);for(const e of entitiesOf(i))out.add(e);}return[...out];}
// Directory rows of every known company: the TARGET aliases and every Universe code that is not a TARGET listing.
function directory(nameOf=()=>''){const rows=[];for(const id of Object.keys(TARGET))rows.push({company_id:id,ticker:tickerOf(id),name:nameOf(id)||'',identity_only:true});
 const targetListings=new Set(Object.values(TARGET).map(t=>t[0]));for(const code of[...codes.keys()].sort())if(!targetListings.has(code))rows.push({company_id:code,ticker:code.split(':')[1],name:nameOf(code)||'',identity_only:true});return rows;}
// Watched rows for the watchlist screen (any company): one row per watched issuer.
function watchRows(prefs,nameOf=()=>''){return pageIds(prefs?.interests).map(id=>({company_id:id,ticker:tickerOf(id)||id,name:nameOf(id)||'',identity_only:true}));}
function identities(catalog){if(catalog?.schema!=='DEVICE_ACTUAL_CATALOG/1'||!Array.isArray(catalog.instruments)||catalog.instruments.length!==19)throw Error('IDENTITY_CATALOG_INVALID');const seen=new Set();const rows=catalog.instruments.map(r=>{const id=IDS[r.ticker];if(!id||seen.has(id)||typeof r.label!=='string'||r.label.length>128||!r.label.trim())throw Error('IDENTITY_CATALOG_INVALID');seen.add(id);return Object.freeze({company_id:id,ticker:r.ticker,name:r.label,identity_only:true});});return rows.sort((a,b)=>a.ticker<b.ticker?-1:a.ticker>b.ticker?1:0);}
function filter(rows,prefs,{query='',group='',onlyInterest=false,sort='ticker'}={}){const q=query.trim().toLocaleLowerCase(),g=prefs.groups.find(g=>g.id===group),interests=prefs.interests.map(keyOf),members=g?g.members.map(keyOf):null,at=r=>interests.indexOf(keyOf(r.company_id)),on=r=>at(r)>=0;const filtered=rows.filter(r=>(!q||(r.ticker+' '+r.name).toLocaleLowerCase().includes(q))&&(!onlyInterest||on(r))&&(!members||members.includes(keyOf(r.company_id))));return filtered.sort((a,b)=>sort==='added'?(at(a)-at(b)):sort==='favorites'?(Number(on(b))-Number(on(a))||a.ticker.localeCompare(b.ticker)):sort==='name'?a.name.localeCompare(b.name):a.ticker.localeCompare(b.ticker));}
return Object.freeze({IDS:Object.freeze({...IDS}),TARGET,useNames,issuerOf,listingOf,providerSymbol,tickerOf,entitiesOf,primaryOf,listingsOf,migrate,keyOf,watched,pageIds,allIds,directory,watchRows,identities,filter});
});
