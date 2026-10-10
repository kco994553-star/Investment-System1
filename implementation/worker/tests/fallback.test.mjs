import assert from 'node:assert/strict';
import test from 'node:test';
import { createHandler } from '../src/index.js';

globalThis.fetch = async () => { throw new Error('LIVE_TRANSPORT_DISABLED'); };
const NOW = Date.UTC(2026, 9, 10, 12);
const json = (v, status = 200, headers = {}) => new Response(JSON.stringify(v), {status, headers});
function setup(symbol='NVDA', range='1mo', options={}) {
  const calls=[], env={ALLOWED_EMAIL:['owner','example.test'].join('@'), GOOGLE_CLIENT_ID:'synthetic-client', TIINGO_API_KEY:'synthetic-tiingo', KRX_API_KEY:'synthetic-krx', ...options.env};
  let released=0;
  env.HISTORY_RATE_LIMITER={idFromName:x=>x,get:()=>({fetch:async url=>String(url).endsWith('/release')?(released++,new Response(null,{status:204})):json({allowed:true,lease:1})})};
  const fetch=async (url,init)=>{
    calls.push({url:String(url),init});
    if(String(url).includes('oauth2.googleapis.com'))return json({aud:env.GOOGLE_CLIENT_ID,email:env.ALLOWED_EMAIL,email_verified:true,expires_in:3600});
    if(String(url).includes('query1.finance.yahoo.com'))return json({},503);
    return options.provider?options.provider(String(url),init):String(url).includes('/prices?')?json([{date:'2026-10-08T00:00:00.000Z',open:100,high:104,low:98,close:102,adjClose:91,volume:10}]):json({ticker:symbol.toLowerCase(),exchangeCode:'NASDAQ'});
  };
  const handler=createHandler({fetch,now:()=>NOW,...options.dependencies});
  const run=(headers={})=>handler(new Request('https://private.test/history?symbol='+symbol+'&range='+range,{headers:{Origin:'https://kco994553-star.github.io',Authorization:'Bearer synthetic',...headers}}),env);
  return {run,calls,env,released:()=>released};
}
test('Yahoo failure falls back to authenticated Tiingo EOD without leaking keys or changing date labels',async()=>{
  const s=setup();const r=await s.run(),v=await r.json();assert.equal(r.status,200);assert.equal(v.provider,'Tiingo EOD');assert.equal(v.bars[0].session_date,'2026-10-08');assert.equal(v.timestamp_kind,'PROVIDER_SESSION_LABEL');assert.equal(v.bars[0].close,102);assert.equal(v.bars[0].adjusted_close,91);assert.equal(v.bars[0].session_status,'COMPLETE');assert.equal(s.released(),1);
  assert.equal(r.headers.get('Cache-Control'),'private, no-store, max-age=0');
  const requests=s.calls.filter(c=>c.url.includes('api.tiingo.com'));assert.equal(requests.length,2);
  for(const c of requests){assert.equal(c.init.headers.Authorization,'Token '+s.env.TIINGO_API_KEY);assert.equal(c.init.cache,'no-store');assert.equal(c.init.redirect,'error');assert.ok(!c.url.includes(s.env.TIINGO_API_KEY));}
  assert.ok(!JSON.stringify(v).includes(s.env.TIINGO_API_KEY));
});
test('KRX falls back only for the Korean listing, keeps explicit session date, and bounds day requests',async()=>{
  const s=setup('042700.KS','1mo',{provider:(u,init)=>{assert.ok(u.startsWith('https://data-dbg.krx.co.kr/svc/apis/sto/stk_bydd_trd?basDd='));assert.equal(init.headers.AUTH_KEY,'synthetic-krx');const day=new URL(u).searchParams.get('basDd');return json({OutBlock_1:day==='20261008'?[{ISU_CD:'042700',BAS_DD:day,MKT_NM:'KOSPI',TDD_OPNPRC:'100,000',TDD_HGPRC:'104,000',TDD_LWPRC:'98,000',TDD_CLSPRC:'102,000',ACC_TRDVOL:'1,000',MKTCAP:'999999'}]:[]});}});
  const r=await s.run(),v=await r.json();assert.equal(r.status,200);assert.equal(v.provider,'KRX OPEN API');assert.equal(v.bars.length,1);assert.equal(v.bars[0].session_date,'2026-10-08');assert.equal(v.bars[0].close,102000);assert.equal(v.bars[0].adjusted_close,null);assert.ok(!JSON.stringify(v).includes('MKTCAP'));
  assert.ok(s.calls.filter(c=>c.url.includes('krx.co.kr')).length<=32);assert.ok(!s.calls.some(c=>c.url.includes('tiingo')));
});
test('KRX long ranges fail before any KRX request and never silently truncate history',async()=>{
  const s=setup('042700.KS','5y');const r=await s.run();assert.equal(r.status,422);assert.deepEqual(await r.json(),{error:{code:'KRX_RANGE_UNSUPPORTED'}});assert.ok(!s.calls.some(c=>c.url.includes('krx.co.kr')));assert.equal(s.released(),1);
});
test('Japanese listings and missing provider Secrets preserve the Yahoo failure without new providers',async()=>{
  for(const [symbol,env] of [['8035.T',{}],['NVDA',{TIINGO_API_KEY:''}],['042700.KS',{KRX_API_KEY:''}]]){const s=setup(symbol,'1mo',{env}),r=await s.run();assert.equal(r.status,503);assert.deepEqual(await r.json(),{error:{code:'YAHOO_UNAVAILABLE'}});assert.equal(s.calls.length,2);}
});
test('origin/auth rejection prevents every price provider call',async()=>{
  for(const headers of [{Origin:'https://other.test'},{Authorization:''}]){const s=setup(),r=await s.run(headers);assert.equal(r.status,403);assert.equal(s.calls.length,0);}
});
test('provider metadata mismatch, OHLC corruption, duplicate/future dates and upstream messages fail closed',async()=>{
  for(const mode of ['metadata','ohlc','duplicate','future','upstream','oversize']){
    const s=setup('NVDA','1mo',{provider:u=>{if(!u.includes('/prices?'))return json({ticker:mode==='metadata'?'wrong':'nvda',exchangeCode:'NASDAQ'});if(mode==='upstream')return json({privateMessage:'never forwarded'},401);if(mode==='oversize')return json([] ,200,{'Content-Length':String(2**21)});const row={date:mode==='future'?'2026-10-11T00:00:00Z':'2026-10-08T00:00:00Z',open:100,high:mode==='ohlc'?90:104,low:98,close:102,adjClose:91,volume:10};return json(mode==='duplicate'?[row,row]:[row]);}});
    const r=await s.run(),v=await r.json();assert.ok(r.status>=400);assert.ok(/^TIINGO_/.test(v.error.code));assert.ok(!JSON.stringify(v).includes('never forwarded'));assert.equal(s.released(),1);
  }
});
test('KRX duplicate listing, malformed grouping, mismatched day and zero placeholders fail closed',async()=>{
  for(const mode of ['duplicate','number','day','zero']){const s=setup('042700.KS','1mo',{provider:u=>{const day=new URL(u).searchParams.get('basDd'),row={ISU_CD:'042700',BAS_DD:mode==='day'?'20260101':day,MKT_NM:'KOSPI',TDD_OPNPRC:'100',TDD_HGPRC:'104',TDD_LWPRC:'98',TDD_CLSPRC:mode==='number'?'10,20':mode==='zero'?'0':'102',ACC_TRDVOL:'10'};return json({OutBlock_1:mode==='duplicate'?[row,row]:[row]});}});const r=await s.run();assert.equal(r.status,502);assert.deepEqual(await r.json(),{error:{code:'KRX_FORMAT_CHANGED'}});assert.equal(s.released(),1);}
});
