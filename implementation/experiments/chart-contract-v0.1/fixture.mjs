// Entire fixture is fabricated for software validation, not a real security/feed.
import {hash} from './contract.mjs';
export function fixture(provider='yahoo-chart') {
  const values=[[100,104,98,102,1000],[102,105,100,101,1200],[101,107,100,106,1300],
    [106,108,103,104,0],[104,105,99,100,null],[100,103,97,102,800],
    [102,108,101,107,1500],[107,110,105,109,1700],[109,111,106,108,900],
    [108,109,102,103,1400],[103,107,102,106,1600],[106,112,105,111,1800]];
  const timestamp=values.map((_,i)=>Date.parse(`2024-01-${String(i+1).padStart(2,'0')}T00:00:00Z`)/1000);
  const quote=Object.fromEntries(['open','high','low','close','volume'].map((key,j)=>[key,values.map(r=>r[j])]));
  const raw=provider==='alpaca'?{bars:{DEMO:values.map((r,i)=>({t:new Date(timestamp[i]*1000).toISOString(),o:r[0],h:r[1],l:r[2],c:r[3],v:r[4]}))},next_page_token:null}:
    {chart:{result:[{meta:{symbol:'DEMO',currency:'USD',dataGranularity:'1d'},timestamp,indicators:{quote:[quote],adjclose:[{adjclose:values.map(()=>999)}]}}],error:null}};
  const bytes=Buffer.from(JSON.stringify(raw));
  return {bytes,ctx:{provider,transport:'FIXTURE',synthetic:true,raw_sha256:hash(bytes),symbol:'DEMO',company_id:'fixture-company',security_id:'fixture-security',listing_id:'fixture-listing',
    as_of:'2024-01-13T00:00:00Z',fetched_at:'2024-01-14T00:00:00Z',artifact_id:'fixture:ohlcv:v1',source_reference:'SYNTHETIC_SOFTWARE_FIXTURE',
    ...(provider==='alpaca'?{request:{timeframe:'1Day',adjustment:'raw',feed:'iex',currency:'USD'}}:{})}};
}
