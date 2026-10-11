'use strict';
/* Synthetic, schema-valid `sec-disclosures.json` and a filing-windows payload with one confirmed quarter, relative to now.
   Synthetic accessions and titles only; real issuer CIKs only to form valid SEC archive links. No prices, no bodies. */
const api=require('../src/investment_system/product/web_assets/sec-disclosures.js');
const H=c=>c.repeat(64),IDS=['asml','lrcx','klac','tokyo_electron','hanmi','nvda','amd','avgo','qcom','intc','msft','googl','amzn','rtx','stry','etn','hubb','gev','rok'];
const sec=t=>new Date(Math.floor(t/1000)*1000).toISOString().replace('.000Z','+00:00'),utcDay=t=>new Date(t).toISOString().slice(0,10);
function payload(now=Date.now()){
 const asOf=now-30*60000,acquired=asOf-60000,day=86400000,companies={};
 for(const id of Object.keys(api.CIKS))companies[id]={state:'NOT_AVAILABLE',acquired_at:null,reason_code:'NOT_COLLECTED'};
 for(const id of ['nvda','amd','msft','googl'])companies[id]={state:'LIVE',acquired_at:sec(acquired),reason_code:null};
 const ev=(company,n,form,daysAgo,eventDaysAgo,items,exhibit)=>{const cik=api.CIKS[company],accession=cik+'-26-'+String(n).padStart(6,'0'),accepted=sec(now-daysAgo*day);
  const x=exhibit?{state:'AVAILABLE',title:exhibit,url:'https://www.sec.gov/Archives/edgar/data/'+Number(cik)+'/'+accession.replaceAll('-','')+'/ex991-'+n+'.htm',released_at:accepted}:{state:'NOT_AVAILABLE',reason_code:'NO_EXHIBIT_99_1'};
  return{company_id:company,accession,form,filing_date:utcDay(now-daysAgo*day),event_date:eventDaysAgo===null?null:utcDay(now-eventDaysAgo*day),accepted_at:accepted,items,classification:api.classify(items),link:api.indexUrl(company,accession),group_id:null,occurrence:null,first_seen_at:sec(Math.min(asOf,now-daysAgo*day+3600000)),exhibit_99_1:x};};
 const events=[ev('nvda',101,'8-K',40,40,['2.02','9.01'],'Synthetic press release announcing quarterly results'),ev('nvda',140,'8-K/A',30,40,['2.02','9.01'],null),
  ev('amd',150,'8-K',20,21,['5.02'],null),ev('msft',160,'8-K',10,11,['1.01','2.03','9.01'],'Synthetic agreement press release'),ev('googl',170,'8-K',2,2,['7.01','8.01','9.01'],'Synthetic other event release')];
 events.sort((a,b)=>a.accepted_at<b.accepted_at?1:a.accepted_at>b.accepted_at?-1:a.accession<b.accession?1:-1);
 api.groups(events).forEach((g,i)=>Object.assign(events[i],g));
 return api.validate({schema_version:1,kind:'SEC_DISCLOSURES',as_of:sec(asOf),state:'LIVE',reason_codes:[],freshness_basis:'SOURCE_ACQUISITION',stale_after_seconds:172800,window_days:90,channel:'DISCLOSURE',score_effect:'NONE',companies,events});
}
/* nvda: one 10-Q group whose period ended 50 days ago, confirmed by an 8-K Item 2.02 released 40 days ago. */
function filingWindows(now=Date.now()){const at=new Date(now-30*60000).toISOString(),day=86400000,end=new Date(now-50*day),released=utcDay(now-40*day),companies={};
 for(const id of IDS)companies[id]={state:'NOT_AVAILABLE',role:'ESTIMATED_PATTERN_NOT_CONFIRMED',confirmed_earnings_date:null,earnings_confirmation:null,groups:[],source_hashes:{}};
 const md=String(end.getUTCMonth()+1).padStart(2,'0')+'-'+String(end.getUTCDate()).padStart(2,'0'),next=new Date(now+40*day);
 companies.nvda={state:'LIVE',role:'ESTIMATED_PATTERN_NOT_CONFIRMED',confirmed_earnings_date:released,source_hashes:{companyfacts:H('a'),submissions:H('b')},
  earnings_confirmation:{basis:'SEC_8K_ITEM_2_02',period_end:utcDay(end.getTime()),accession:'0001045810-26-000101',accepted_at:released+'T20:20:31+00:00'},
  groups:[{form:'10-Q',report_month_day:md,observation_count:2,observed_filing_windows:[{month:next.getUTCMonth()+1,day_min:Math.min(next.getUTCDate(),28),day_max:Math.min(next.getUTCDate(),28),count:2}]}]};
 return{schema_version:1,kind:'SEC_FILING_WINDOWS',as_of:at,state:'LIVE',sources:[{agency:'SEC_COMPANYFACTS',sha256:H('a'),acquired_at:at},{agency:'SEC_SUBMISSIONS',sha256:H('b'),acquired_at:at}],reason_codes:[],freshness_basis:'SOURCE_ACQUISITION',stale_after_seconds:86400,data:{companies}};}
module.exports={payload,filingWindows};
