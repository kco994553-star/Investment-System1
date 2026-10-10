/* Exercise the actual app and Worker contract with synthetic credentials and bars. */
import assert from 'node:assert/strict';
import test from 'node:test';
import { createRequire } from 'node:module';

globalThis.fetch = async () => { throw new Error('Live network transport is disabled'); };
const { createHandler, HistoryRateLimiter } = await import('../worker/src/index.js');
const require = createRequire(import.meta.url);
const { createSession } = require('../src/investment_system/product/web_assets/google-sheet-quotes.js');
const history = require('../src/investment_system/product/web_assets/private-history.js');
const ORIGIN = 'https://kco994553-star.github.io';
const WORKER = 'https://synthetic-history.example-account.workers.dev';
const NOW = Date.UTC(2030, 0, 8, 12);
const json = value => new Response(JSON.stringify(value), { headers: {'Content-Type':'application/json'} });

function harness(tokenOverrides = {}) {
  let record, callback;
  const upstream = [], appRequests = [];
  const storage = {
    async get() { return structuredClone(record); },
    async put(_key, value) { record = structuredClone(value); },
    async transaction(fn) { return fn(this); }
  };
  const limiter = new HistoryRateLimiter({storage}, {}, {now:()=>NOW});
  const env = {ALLOWED_EMAIL:'owner@example.test',GOOGLE_CLIENT_ID:'synthetic-client',HISTORY_RATE_LIMITER:{
    idFromName(name) { return name; },
    get() { return {fetch:(url,init)=>limiter.fetch(new Request(url,init))}; }
  }};
  const handler = createHandler({now:()=>NOW,fetch:async(url,init)=>{
    upstream.push({url,init});
    if(url === 'https://oauth2.googleapis.com/tokeninfo') return json({aud:env.GOOGLE_CLIENT_ID,email:env.ALLOWED_EMAIL,email_verified:true,expires_in:3600,...tokenOverrides});
    const symbol = decodeURIComponent(new URL(url).pathname.split('/').at(-1));
    const currency = symbol.endsWith('.KS')?'KRW':symbol.endsWith('.T')?'JPY':'USD';
    const timezone = symbol.endsWith('.KS')?'Asia/Seoul':symbol.endsWith('.T')?'Asia/Tokyo':'America/New_York';
    return json({chart:{error:null,result:[{meta:{symbol,currency,exchangeName:'TEST',exchangeTimezoneName:timezone,dataGranularity:'1d'},timestamp:[NOW/1000-86400,NOW/1000-3600],indicators:{quote:[{open:[10,null],high:[12,null],low:[9,null],close:[11,null],volume:[0,null]}],adjclose:[{adjclose:[110,null]}]}}]}});
  }});
  const view = {AbortController,setTimeout:()=>1,clearTimeout(){},addEventListener(){},google:{accounts:{oauth2:{
    initTokenClient(options) { callback=options.callback;return {requestAccessToken(){}}; },revoke(_token,done){done();}
  }}},fetch:async(url,init)=>{
    appRequests.push({url,init});
    return handler(new Request(url,{...init,headers:{...init.headers,Origin:ORIGIN}}),env);
  }};
  const session = createSession(view,{clientId:env.GOOGLE_CLIENT_ID,now:()=>NOW});
  session.setEnabled(true);session.login();
  callback({access_token:'synthetic-access',expires_in:3600,scope:'email https://www.googleapis.com/auth/drive.file',token_type:'Bearer'});
  return {session,upstream,appRequests,storage};
}

for(const [companyId,currency] of [['nvda','USD'],['hanmi','KRW'],['tokyo_electron','JPY']]) {
  test(`app requests and validates Worker daily history for ${companyId}`,async()=>{
    const s=harness(),symbol=history.symbolFor(companyId);
    try {
      const payload=await s.session.fetchHistory(WORKER,symbol,'1y',{approvedOrigin:WORKER});
      const data=history.validateHistory(payload,{symbol,range:'1y'});
      assert.equal(data.currency,currency);
      assert.equal(data.bars[0].close,11);
      assert.equal(data.bars[0].adjusted_close,110);
      assert.equal(data.bars[1].close,null);
      assert.equal(new URL(s.appRequests[0].url).searchParams.size,2);
      assert.equal(s.appRequests[0].init.cache,'no-store');
      assert.equal(new Headers(s.upstream[0].init.headers).get('Authorization'),'Bearer synthetic-access');
      assert.equal(new Headers(s.upstream[1].init.headers).has('Authorization'),false);
      assert.equal(s.upstream.length,2);
      const persisted=await s.storage.get();
      assert.deepEqual(Object.keys(persisted).sort(),['activeLease','leaseUntil','nextLease','times']);
    } finally {await s.session.disconnect();}
  });
}

test('Worker owner rejection invalidates the shared app login before Yahoo',async()=>{
  const s=harness({email:'other@example.test'});
  try {
    await assert.rejects(s.session.fetchHistory(WORKER,'NVDA','1y',{approvedOrigin:WORKER}),{message:'AUTH_FORBIDDEN'});
    assert.equal(s.session.state().connected,false);
    assert.equal(s.upstream.length,1);
  } finally {await s.session.disconnect();}
});
