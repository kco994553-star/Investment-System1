'use strict';
/* Synthetic, schema-valid `news-signals.json` relative to now, matching tools/sec_disclosures_fixture.js (same `now`):
   GDELT items with one repeat group, a company IR release that repeats the MSFT 8-K Exhibit 99.1, and a plain IR release.
   Synthetic titles and example links only (company IR links use the companies' own domains); no bodies, no prices.
   scenario 'UPDATED' (default): every listed company answered this run; companies with items are UPDATED, the rest NO_NEW_ITEMS.
   scenario 'GDELT_429': the observed 2026-10-19 run shape. GDELT company 1 (amd) FAILED HTTP_429 and companies 2-19 NOT_RUN
   HTTP_429; IR stry answered with nothing new, amzn REDIRECT_REJECTED, the other 8 feeds HTTP_FAILED. Every item is carried
   from the previous run (acquired 10h before as_of) and stays listed.
   without: company ids whose items are left out (a later day where those items are gone). */
const api=require('../src/investment_system/product/web_assets/news-signals.js'),secFixture=require('./sec_disclosures_fixture.js');
const sec=t=>new Date(Math.floor(t/1000)*1000).toISOString().replace('.000Z','+00:00'),HOUR=3600000,DAY=24*HOUR;
function payload(now=Date.now(),secPayload=secFixture.payload(now),{scenario='UPDATED',without=[]}={}){
 const asOf=now-30*60000,failed=scenario==='GDELT_429',acquired=sec(asOf-60000),previous=sec(asOf-10*HOUR),sources={GDELT:{},IR:{}};
 const msft=secPayload.events.find(e=>e.company_id==='msft');
 const item=(company,source,title,link,hoursAgo,extra={})=>Object.assign({company_id:company,source,title,link,published_at:sec(now-hoursAgo*HOUR),classification:api.classify(title),group_id:null,occurrence:null,relation:'NONE',related_8k_accession:null},extra);
 const items=[
  item('nvda','GDELT','Nvidia posts record quarterly revenue on AI demand','https://news.example.com/nvda-record',30),
  item('nvda','GDELT','Nvidia posts record quarterly revenue as AI demand surges','https://wire.example.org/nvda-revenue',20),
  item('googl','GDELT','Google unveils new Pixel phone lineup','https://tech.example.com/pixel',72),
  item('amd','GDELT','AMD sued over chip patent in Delaware court','https://law.example.com/amd-suit',120),
  item('hanmi','GDELT','Hanmi Semiconductor wins TC bonder order','https://kr.example.com/hanmi',100),
  item('msft','IR','Microsoft announces quarterly dividend','https://news.microsoft.com/synthetic/dividend',150),
  item('msft','IR','Synthetic agreement press release from Microsoft','https://news.microsoft.com/synthetic/agreement',
   (now-Date.parse(msft.accepted_at))/HOUR-0.1,{relation:'RELATED_TO_8K',related_8k_accession:msft.accession,group_id:msft.group_id})].filter(i=>!without.includes(i.company_id));
 const has=(source,id)=>items.some(i=>i.source===source&&i.company_id===id);
 const result=(source,id,index)=>{if(!failed)return has(source,id)?['UPDATED',null]:['NO_NEW_ITEMS',null];
  if(source==='GDELT')return index===0?['FAILED','HTTP_429']:['NOT_RUN','HTTP_429'];
  return id==='stry'?['NO_NEW_ITEMS',null]:id==='amzn'?['FAILED','REDIRECT_REJECTED']:['FAILED','HTTP_FAILED'];};
 const entry=(source,id,index)=>{const [r,code]=result(source,id,index),at=r==='FAILED'||r==='NOT_RUN'?previous:acquired;return{state:'LIVE',acquired_at:at,reason_code:null,last_result:r,last_result_code:code};};
 api.GDELT_COMPANIES.forEach((id,n)=>{sources.GDELT[id]=entry('GDELT',id,n);});
 for(const id of api.IR_COMPANIES)sources.IR[id]=Object.hasOwn(api.IR_DOMAINS,id)?Object.assign(entry('IR',id),{feed_status:'UNVERIFIED_URL'}):{state:'NOT_AVAILABLE',acquired_at:null,reason_code:'NO_OFFICIAL_FEED_KNOWN',feed_status:'NOT_AVAILABLE',last_result:null,last_result_code:null};
 items.sort((a,b)=>a.published_at<b.published_at?1:a.published_at>b.published_at?-1:a.link<b.link?1:-1);
 api.groups(items).forEach((g,i)=>Object.assign(items[i],g));
 // Synthetic run: every item of an UPDATED company counts as added by this run.
 const added=source=>items.filter(i=>i.source===source&&sources[source][i.company_id].last_result==='UPDATED').length;
 const summaries={GDELT:api.sourceRefresh('GDELT',sources.GDELT,sec(asOf),added('GDELT')),IR:api.sourceRefresh('IR',sources.IR,sec(asOf),added('IR'))};
 const result_=api.refreshResult(summaries),extra={PARTIAL_FAILED:['REFRESH_PARTIAL_FAILED'],FAILED:['REFRESH_FAILED'],NOT_RUN:['REFRESH_NOT_RUN']}[result_]||[];
 return api.validate({schema_version:2,kind:'NEWS_SIGNALS',as_of:sec(asOf),state:'LIVE',reason_codes:extra,freshness_basis:'SOURCE_ACQUISITION',stale_after_seconds:172800,window_days:14,channel:'NEWS',score_effect:'NONE',
  attribution:JSON.parse(JSON.stringify(api.ATTRIBUTION)),matching_rule:'TITLE_NAME_OR_TICKER_V0',sources,refresh:{attempted_at:sec(asOf),result:result_,sources:summaries},items});
}
module.exports={payload};
