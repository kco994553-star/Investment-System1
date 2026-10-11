'use strict';/* Synthetic `sec-universe-shares.json` builder for Node/browser tests. Synthetic CIKs and hashes only; no prices. */
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),groups=require('../src/investment_system/product/web_assets/share-class-groups.js');
const CODES=JSON.parse(fs.readFileSync(path.join(__dirname,'../src/investment_system/universe/universe_codes_v1.json'),'utf8'));
const h=x=>crypto.createHash('sha256').update(x).digest('hex'),iso=t=>new Date(t).toISOString().replace('.000Z','Z');
function empty(reason='NOT_COLLECTED'){return{cik:null,listing_id:null,company_id:null,shares:null,measurement_date:null,accn:null,form:null,filed:null,acquired_at:null,concept:null,share_class_basis:'BASIS_UNCONFIRMED',basis_evidence:{cover_accn:null,class_count:null,class_members:[],listing_class_member:null},source_sha256:{companyfacts:null,submissions:null,cover:null},state:'NOT_AVAILABLE',reason_codes:[reason]};}
function row(code,n,{shares=1000,basis='SINGLE_CLASS_CONFIRMED',acquired,stale=false,members:classes=null,member=null}={}){
 const [venue,sym]=code.split(':'),cik=String(n).padStart(10,'0'),accn=cik+'-26-000001',mic=venue==='NASDAQ'?'XNAS':'XNYS',members=basis==='SHARE_CLASS_BASIS'?(classes||['CommonClassAMember','CommonClassBMember']):[];
 const reasons=basis==='SINGLE_CLASS_CONFIRMED'?[]:basis==='SHARE_CLASS_BASIS'?['SHARE_CLASS_BASIS']:['MULTI_CLASS_AMBIGUOUS'],day=new Date(acquired).toISOString().slice(0,10);
 return{cik,listing_id:mic+':'+sym.replaceAll('.','-')+':'+cik,company_id:'sec_'+cik,shares,measurement_date:'2026-01-02',accn,form:'10-Q',filed:'2026-01-05'>day?day:'2026-01-05',acquired_at:iso(acquired),concept:'dei:EntityCommonStockSharesOutstanding',share_class_basis:basis,
  basis_evidence:{cover_accn:basis==='BASIS_UNCONFIRMED'?null:accn,class_count:members.length,class_members:members,listing_class_member:member??members[0]??null},source_sha256:{companyfacts:h('facts'+cik),submissions:h('sub'+cik),cover:basis==='BASIS_UNCONFIRMED'?null:h('cover'+cik)},state:stale?'STALE':'LIVE',reason_codes:stale?[...reasons,'STALE_INPUT']:reasons};
}
/* `unlisted_classes` entry per configured group: rows[valued_at].unlisted=[{class_member,shares}] binds a count to that row's cover; otherwise NOT_COLLECTED (no count). */
function unlistedEntry(group,record,classes){const base={cik:group.cik,valued_at:group.unlisted.valued_at,accn:null,measurement_date:null,cover_sha256:null,classes:[],state:'NOT_AVAILABLE',reason_codes:['NOT_COLLECTED']};
 if(!classes)return base;return{...base,accn:record.accn,measurement_date:record.measurement_date,cover_sha256:record.source_sha256.cover,classes,state:record.state,reason_codes:record.state==='STALE'?['STALE_INPUT']:[]};}
/* rows: {code:{n,shares,basis,stale,members?,member?,unlisted?}}; `now` ms. Stale rows are acquired 20 days earlier (window 14 days). */
function payload(rows,now=Date.now()){
 const records=Object.fromEntries(CODES.map(c=>[c,empty(c==='BATS:CBOE'?'CIK_UNRESOLVED':'NOT_COLLECTED')]));
 for(const [code,o] of Object.entries(rows)){if(!Object.hasOwn(records,code))throw Error('UNKNOWN_CODE');records[code]=row(code,o.n,{...o,acquired:o.stale?now-20*86400e3:now-3600e3});}
 const states=Object.values(records).map(r=>r.state),state=states.includes('LIVE')?'LIVE':states.includes('STALE')?'STALE':'NOT_AVAILABLE';
 return{schema_version:1,kind:'SEC_UNIVERSE_SHARES',as_of:iso(now-1800e3),config_version:'sec-universe-shares/v0',config_status:'DEFAULT_V0_UNCALIBRATED',freshness_basis:'SOURCE_ACQUISITION',stale_after_seconds:14*86400,shard_count:7,last_shard_index:3,registry_sha256:h('registry'),code_count:CODES.length,state,reason_codes:state==='LIVE'?[]:state==='STALE'?['STALE_INPUT']:['NO_ELIGIBLE_INPUT'],records,
  unlisted_classes:Object.fromEntries(Object.entries(groups.UNLISTED).map(([id,g])=>[id,unlistedEntry(g,records[g.unlisted.valued_at],rows[g.unlisted.valued_at]?.unlisted)]))};
}
module.exports={CODES,payload,empty,unlistedEntry};
