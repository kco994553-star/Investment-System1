'use strict';
// News signals reader: validation fails closed, combined chronological list with SEC 8-K, related IR nesting, fetch options. Synthetic data only.
const assert=require('node:assert/strict'),test=require('node:test');
const api=require('../src/investment_system/product/web_assets/news-signals.js'),secFixture=require('./sec_disclosures_fixture.js');
const fixture=require('./news_signals_fixture.js'),{EMPTY}=require('./empty_public_screens.js');
const NOW=Date.now(),SEC=secFixture.payload(NOW),NEWS=fixture.payload(NOW,SEC);
test('synthetic and empty build payloads validate; channel NEWS, score effect NONE, GDELT attribution',()=>{assert.equal(NEWS.items.length,7);assert.equal(NEWS.score_effect,'NONE');assert.equal(NEWS.channel,'NEWS');
 assert.equal(NEWS.attribution.GDELT.url,'https://www.gdeltproject.org/');assert.equal(api.validate(EMPTY['news-signals.json']).state,'NOT_AVAILABLE');assert.equal(EMPTY['news-signals.json'].items.length,0);});
test('similar titles of one company within 72h form one group: first NEW, later REPEAT',()=>{const by=Object.fromEntries(NEWS.items.map(i=>[i.link,i]));
 const head=by['https://news.example.com/nvda-record'],repeat=by['https://wire.example.org/nvda-revenue'];assert.equal(head.occurrence,'NEW');assert.equal(repeat.occurrence,'REPEAT');assert.equal(repeat.group_id,head.group_id);
 assert.equal(by['https://news.microsoft.com/synthetic/agreement'].relation,'RELATED_TO_8K');assert.equal(by['https://law.example.com/amd-suit'].classification,'LEGAL');});
test('bodies, prices, score changes, forged links, irrelevant titles and broken grouping fail closed',()=>{
 for(const mutate of [p=>p.items[0].body='text',p=>p.items[0].price=1,p=>p.score_effect='Q',p=>p.items.reverse(),p=>{p.items.find(i=>i.source==='IR').link='https://evil.example.com/x';},
  p=>{p.items.find(i=>i.source==='GDELT').title='Unrelated headline';},p=>{p.items.find(i=>i.source==='GDELT').link='javascript:alert(1)';},p=>{p.items.find(i=>i.occurrence==='REPEAT'&&i.relation==='NONE').occurrence='NEW';},
  p=>p.attribution.GDELT.url='https://example.com/',p=>delete p.sources.GDELT.asml,p=>p.items.push(Object.assign({},p.items[0])),p=>p.channel='DISCLOSURE',p=>{p.items.find(i=>i.relation==='RELATED_TO_8K').related_8k_accession=null;}]){
  const p=structuredClone(NEWS);mutate(p);assert.throws(()=>api.validate(p),/NEWS_SIGNALS_INVALID/);}});
test('one chronological list: 8-K rows carry their related IR release, news groups collapse repeats, company filter applies',()=>{
 const rows=api.timeline({sec:SEC,news:NEWS});const times=rows.map(r=>r.time);assert.deepEqual(times,[...times].sort().reverse());
 const msft=rows.find(r=>r.channel==='DISCLOSURE'&&r.company_id==='msft');assert.deepEqual(msft.related.map(i=>i.link),['https://news.microsoft.com/synthetic/agreement']);
 const nvda=rows.find(r=>r.channel==='NEWS'&&r.company_id==='nvda');assert.equal(nvda.item.occurrence,'NEW');assert.deepEqual(nvda.repeats.map(i=>i.link),['https://wire.example.org/nvda-revenue']);
 assert.equal(rows.filter(r=>r.channel==='NEWS').length,5);assert.equal(rows.filter(r=>r.channel==='DISCLOSURE').length,5);
 assert.deepEqual(api.timeline({sec:SEC,news:NEWS},{companyIds:['msft']}).map(r=>r.channel),['NEWS','DISCLOSURE']);
 // without the SEC file the related IR release is shown on its own, marked as related
 const alone=api.timeline({sec:null,news:NEWS},{companyIds:['msft']});assert.equal(alone.length,2);assert.ok(alone.some(r=>r.orphan&&r.item.relation==='RELATED_TO_8K'));
 // DART rows join when a reader exposes timeline()
 const dart={timeline:()=>[{channel:'DISCLOSURE',source:'DART',time:'2999-01-01T00:00:00+00:00',company_id:'hanmi',event:{}}]};assert.equal(api.timeline({sec:SEC,news:NEWS,dart:{}},{dartApi:dart})[0].source,'DART');});
test('fetch omits credentials, cache and redirects; 404, invalid and oversized files read as not connected',async()=>{const calls=[];
 assert.equal((await api.load({fetch:async(name,o)=>{calls.push([name,o]);return{ok:true,text:async()=>JSON.stringify(NEWS)};}})).items.length,7);
 assert.equal(calls[0][0],'news-signals.json');assert.ok(calls.every(([,o])=>o.cache==='no-store'&&o.credentials==='omit'&&o.redirect==='error'));
 assert.equal(await api.load({fetch:async()=>({ok:false,status:404})}),null);assert.equal(await api.load({fetch:async()=>({ok:true,text:async()=>'{"kind":"NEWS_SIGNALS"}'})}),null);
 assert.equal(await api.load({fetch:async()=>({ok:true,text:async()=>' '.repeat(1024*1024+1)})}),null);assert.equal(await api.load({fetch:async()=>{throw Error('PRIVATE_TEST_DIAGNOSTIC');}}),null);});

test('structural E4 excludes generic legal stories and repeat reports',()=>{const rows=[{company_id:'asml',title:'ASML export controls extended',link:'https://example.invalid/export',published_at:'2031-01-01T10:00:00+00:00',group_id:'a',occurrence:'NEW'},{company_id:'asml',title:'ASML lawsuit filed',link:'https://example.invalid/suit',published_at:'2031-01-01T11:00:00+00:00',group_id:'b',occurrence:'NEW'},{company_id:'asml',title:'ASML export controls repeated',link:'https://example.invalid/repeat',published_at:'2031-01-02T10:00:00+00:00',group_id:'a',occurrence:'REPEAT'}];const c=api.structuralCandidates(rows);assert.equal(c.length,1);assert.equal(c[0].code,'E4');assert.equal(c[0].evidence_grade,'SIGNAL');assert.equal(c[0].score_effect,'NONE');assert.equal(c[0].info_only,true);});

test('display filters: defaults when storage is missing, throws or holds junk; valid values round-trip per tab',()=>{
 const memory=()=>{const m=new Map();return{getItem:k=>m.has(k)?m.get(k):null,setItem:(k,v)=>m.set(k,String(v))};};
 assert.deepEqual(api.readFilters(null),api.FILTER_DEFAULT);assert.deepEqual(api.readFilters({getItem:()=>{throw Error('SecurityError');}}),api.FILTER_DEFAULT);
 assert.equal(api.writeFilters({channel:'NEWS'},{setItem:()=>{throw Error('QuotaExceededError');}}),false);assert.equal(api.writeFilters({channel:'NEWS'},null),false);
 const s=memory();s.setItem(api.FILTER_KEY,'{not json');assert.deepEqual(api.readFilters(s),api.FILTER_DEFAULT);
 s.setItem(api.FILTER_KEY,JSON.stringify({channel:'X',category:'<b>',occurrence:'NEW',order:'IMPORTANCE',extra:1}));assert.deepEqual(api.readFilters(s),{channel:'ALL',category:'ALL',occurrence:'NEW',order:'IMPORTANCE'});
 const f={channel:'DISCLOSURE',category:'SEC:MATERIAL_AGREEMENT',occurrence:'REPEAT',order:'TIME'};assert.equal(api.writeFilters(f,s),true);assert.deepEqual(api.readFilters(s),f);});
test('display filters narrow or reorder rows only; 실적 joins news earnings and SEC results; importance = held → watchlist → other, newest first inside',()=>{
 const rows=api.timeline({sec:SEC,news:NEWS});assert.deepEqual(api.filterRows(rows),rows);
 const only=f=>api.filterRows(rows,Object.assign({},api.FILTER_DEFAULT,f));
 assert.ok(only({channel:'NEWS'}).every(r=>r.channel==='NEWS'));assert.equal(only({channel:'NEWS'}).length+only({channel:'DISCLOSURE'}).length,rows.length);
 const results=only({category:'RESULTS'});assert.ok(results.some(r=>r.channel==='NEWS'&&r.item.classification==='EARNINGS')&&results.some(r=>r.channel==='DISCLOSURE'&&r.event.classification==='RESULTS'));
 assert.ok(only({category:'NEWS:LEGAL'}).every(r=>r.item.classification==='LEGAL'));
 assert.ok(only({occurrence:'REPEAT'}).every(r=>api.rowOccurrence(r)==='REPEAT'));assert.equal(only({occurrence:'NEW'}).length+only({occurrence:'REPEAT'}).length,rows.length);
 const ctx={held:['amd'],interests:['nvda','msft']},ordered=api.filterRows(rows,Object.assign({},api.FILTER_DEFAULT,{order:'IMPORTANCE'}),ctx),tiers=ordered.map(r=>api.rowTier(r,ctx));
 assert.equal(ordered.length,rows.length);assert.deepEqual(tiers,[...tiers].sort((a,b)=>['HELD','INTEREST','OTHER','MARKET'].indexOf(a)-['HELD','INTEREST','OTHER','MARKET'].indexOf(b)));
 for(const t of ['HELD','INTEREST','OTHER']){const times=ordered.filter(r=>api.rowTier(r,ctx)===t).map(r=>r.time);assert.deepEqual(times,[...times].sort().reverse());}
 assert.equal(api.rowTier({company_id:null}),'MARKET');assert.equal(api.rowTier(rows[0]),'OTHER');});
test('refresh outcome: "새 뉴스 없음" (answered) and "최근 갱신 실패" (failed / not requested) are different lines; schema 1 says not recorded',()=>{
 const failed=fixture.payload(NOW,SEC,{scenario:'GDELT_429'}),utc=v=>v.slice(0,16).replace('T',' ')+' UTC',t=utc(failed.as_of);
 assert.deepEqual(failed.reason_codes,['REFRESH_PARTIAL_FAILED']);assert.equal(failed.state,'LIVE');assert.equal(failed.items.length,NEWS.items.length);
 const [g,ir]=api.refreshStatus(failed,{companyIds:['stry']});
 assert.equal(api.refreshText(ir),'회사 IR · 새 뉴스 없음 · 확인 '+t);
 assert.equal(api.refreshText(g),'GDELT · 이전 자료 유지 · 마지막 성공 '+utc(failed.refresh.sources.GDELT.last_success_at)+' · 최근 갱신 실패(GDELT 요청 안 함 · HTTP_429, '+t+')');
 assert.equal(api.refreshText(api.refreshStatus(failed)[0],true),'GDELT · previous items kept · last success '+utc(failed.refresh.sources.GDELT.last_success_at)+' · latest refresh failed (GDELT HTTP_429, '+t+')');
 const v1=structuredClone(NEWS);v1.schema_version=1;delete v1.refresh;v1.reason_codes=[];for(const e of Object.values(v1.sources))for(const c of Object.values(e)){delete c.last_result;delete c.last_result_code;}
 assert.equal(api.validate(v1).schema_version,1);assert.ok(api.refreshText(api.refreshStatus(v1)[0]).endsWith('최근 갱신 결과 미기록(이전 형식)'));
 for(const mutate of [p=>{p.refresh.result='UPDATED';},p=>{p.reason_codes=[];},p=>{p.sources.GDELT.amd.last_result='NO_NEW_ITEMS';p.sources.GDELT.amd.last_result_code=null;}]){
  const p=structuredClone(failed);mutate(p);assert.throws(()=>api.validate(p),/NEWS_SIGNALS_INVALID/);}});
