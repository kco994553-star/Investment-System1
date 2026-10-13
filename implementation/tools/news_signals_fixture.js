'use strict';
/* Synthetic, schema-valid `news-signals.json` relative to now, matching tools/sec_disclosures_fixture.js (same `now`):
   GDELT items with one repeat group, a company IR release that repeats the MSFT 8-K Exhibit 99.1, and a plain IR release.
   Synthetic titles and example links only (company IR links use the companies' own domains); no bodies, no prices. */
const api=require('../src/investment_system/product/web_assets/news-signals.js'),secFixture=require('./sec_disclosures_fixture.js');
const sec=t=>new Date(Math.floor(t/1000)*1000).toISOString().replace('.000Z','+00:00'),HOUR=3600000,DAY=24*HOUR;
function payload(now=Date.now(),secPayload=secFixture.payload(now)){
 const asOf=now-30*60000,acquired=sec(asOf-60000),sources={GDELT:{},IR:{}};
 for(const id of api.GDELT_COMPANIES)sources.GDELT[id]={state:'LIVE',acquired_at:acquired,reason_code:null};
 for(const id of api.IR_COMPANIES)sources.IR[id]=Object.hasOwn(api.IR_DOMAINS,id)?{state:'LIVE',acquired_at:acquired,reason_code:null,feed_status:'UNVERIFIED_URL'}:{state:'NOT_AVAILABLE',acquired_at:null,reason_code:'NO_OFFICIAL_FEED_KNOWN',feed_status:'NOT_AVAILABLE'};
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
   (now-Date.parse(msft.accepted_at))/HOUR-0.1,{relation:'RELATED_TO_8K',related_8k_accession:msft.accession,group_id:msft.group_id})];
 items.sort((a,b)=>a.published_at<b.published_at?1:a.published_at>b.published_at?-1:a.link<b.link?1:-1);
 api.groups(items).forEach((g,i)=>Object.assign(items[i],g));
 return api.validate({schema_version:1,kind:'NEWS_SIGNALS',as_of:sec(asOf),state:'LIVE',reason_codes:[],freshness_basis:'SOURCE_ACQUISITION',stale_after_seconds:172800,window_days:14,channel:'NEWS',score_effect:'NONE',
  attribution:JSON.parse(JSON.stringify(api.ATTRIBUTION)),matching_rule:'TITLE_NAME_OR_TICKER_V0',sources,items});
}
module.exports={payload};
