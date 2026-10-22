'use strict';
// Macro evidence lines on the macro screen at 390 and 1280: an explicit NOT_COLLECTED fixture, then the synthetic
// multi-run payload (tests/fixtures/macro_evidence/browser_payload.json, written by tests/macro_evidence_fixture.py):
// 경기/주식시장/산업 tabs counted separately, recent-5 lines + "더 보기" on mobile (10 on PC), collection-time lines
// labelled as such, revision markers and release ticks, the reconstruction layer off by default, interpretations
// labelled "해석 후보 · 미승인", the held DOL series, the "근거 더 보기 (전체)" catalog (collapsed; names and states only) and
// the C1 API. Also checks the served artifact and atomic public
// refresh (HTTP/invalid/other-file failure keep the old publication), with view choices kept across redraw/navigation.
// Nothing is stored or sent; no outside host is contacted.
const assert=require('node:assert/strict');const fs=require('node:fs');const path=require('node:path');const {execFileSync}=require('node:child_process');const {chromium}=require('playwright');
const BASE=process.env.PAGES_COCKPIT_URL,SHOTS=process.env.PAGES_COCKPIT_EVIDENCE_DIR||'.';
const PAYLOAD=fs.readFileSync(path.join(__dirname,'../tests/fixtures/macro_evidence/browser_payload.json'),'utf8');
// Daily and manual-deploy artifacts carry observations. Generate the empty case from the production contract,
// without editing the served artifact or assuming that its first collection has not happened yet.
const EMPTY=execFileSync('python3',['-I','-c',[
 'import sys', 'from datetime import datetime, timezone', 'sys.path.insert(0,sys.argv[1])',
 'from investment_system.macro.evidence_lines import empty_payload, encode',
 'sys.stdout.buffer.write(encode(empty_payload(datetime(2026,10,1,tzinfo=timezone.utc))))'
].join('\n'),path.resolve(__dirname,'../src')],{encoding:'utf8',maxBuffer:2*1024*1024});
async function context(browser,width,payload){
 const ctx=await browser.newContext({viewport:{width,height:900},serviceWorkers:'block'});
 if(payload)await ctx.route('**/macro-evidence.json*',r=>r.fulfill({status:200,contentType:'application/json',body:payload}));
 const page=await ctx.newPage(),seen={errors:[],outside:[],writes:[]};page.on('pageerror',e=>seen.errors.push(String(e&&e.message)));
 page.on('request',r=>{if(r.method()!=='GET')seen.writes.push(r.method());});
 await page.route('**/*',r=>{const url=new URL(r.request().url());if(url.origin===new URL(BASE).origin)return r.fallback();seen.outside.push(url.host);return r.abort();});
 return{ctx,page,seen};
}
async function noOverflow(page,label){assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'horizontal scroll '+label);}
async function storage(page){return page.evaluate(()=>JSON.stringify(Object.entries(localStorage).sort())+JSON.stringify(Object.entries(sessionStorage).sort()));}
const text=(page,sel)=>page.locator(sel).first().textContent();
async function pick(page,id){await page.locator('[data-me-indicator]').selectOption(id);await page.locator(`[data-me-meta="${id}"]`).waitFor();}
// "근거 더 보기 (전체)" catalog (L4): collapsed until asked, every published indicator with name, series, rule source, validation and
// collection state; no observation value, date, phase or probability. Held (unverified terms) rows show name and state only.
async function openCatalog(page,width){
 const cat=page.locator('[data-me-catalog]');
 assert.equal(await cat.evaluate(d=>d.tagName),'DETAILS');assert.equal(await cat.getAttribute('open'),null,'catalog collapsed by default');
 assert.ok((await text(page,'[data-me-catalog] > summary')).startsWith('근거 더 보기 (전체'));
 assert.equal(await page.locator('[data-me-catalog] [data-me-catalog-row]').first().isVisible(),false);
 await page.locator('[data-me-catalog] > summary').click();assert.equal(await cat.getAttribute('open'),'');
 const rowDisplay=await page.locator('[data-me-catalog-row] td').first().evaluate(n=>getComputedStyle(n).display);
 assert.equal(rowDisplay,width<600?'block':'table-cell','phone stacks rows, PC keeps every column');
 assert.ok(await page.locator('[data-me-catalog] .table-wrap').evaluate(n=>n.scrollWidth<=n.clientWidth+1),'no inner horizontal scroll '+width);
 return cat;
}
async function catalogRows(page){return page.locator('[data-me-catalog-row]').evaluateAll(rows=>rows.map(r=>({id:r.dataset.meCatalogRow,state:r.dataset.meCatalogState,
 held:r.hasAttribute('data-me-catalog-held'),collected:r.querySelector('[data-me-catalog-collected]')?.dataset.meCatalogCollected,text:r.textContent,
 series:[...r.querySelectorAll('[data-me-catalog-series]')].map(n=>[n.dataset.meCatalogSeries,n.dataset.meCatalogCollected,n.textContent]),
 rule:r.querySelector('[data-me-catalog-rule]')?.textContent||null,validation:r.querySelector('[data-me-catalog-validation]')?.textContent||null})));}
function catalogContract(rows,payload){
 const ind=new Map(payload.indicators.map(i=>[i.id,i]));
 assert.deepEqual(rows.map(r=>r.id),payload.indicators.map(i=>i.id),'every published indicator is listed');
 for(const r of rows){const i=ind.get(r.id);
  assert.ok(r.text.includes(i.name),r.id+' name');assert.equal(r.state,i.state);
  assert.equal(r.collected,i.state==='LIVE'?'YES':i.state==='PARTIAL'?'PARTIAL':'NO',r.id+' collected');
  assert.ok(!/\d{4}-\d{2}|=|확률|국면/.test(r.text),r.id+' no value, date, phase or probability: '+r.text);
  if(i.state!=='LIVE')assert.ok(r.text.includes(i.reason),r.id+' reason code shown');
  const held=i.source.publication!=='PUBLIC'||i.reason==='TERMS_UNVERIFIED';assert.equal(r.held,held,r.id+' held');
  if(held){assert.deepEqual(r.series,[],r.id+' held: no series');assert.equal(r.rule,null);assert.equal(r.validation,null);
   for(const sid of i.series)assert.ok(!r.text.includes(sid),r.id+' held series id hidden');assert.ok(r.text.includes('약관 원문 미확인'));continue;}
  assert.deepEqual(r.series.map(x=>x[0]),i.series,r.id+' series');
  for(const [sid,collected,t] of r.series){const row=payload.series[sid];
   assert.equal(collected,row.state==='LIVE'?'YES':'NO',sid);
   if(row.state!=='LIVE')assert.ok(t.includes('NOT_AVAILABLE')&&t.includes(row.reason),sid+' reason, never a value: '+t);}
  assert.ok(r.rule.includes(i.rule.version)&&r.rule.includes('v0 · 미검증'),r.id+' rule '+r.rule);
  assert.ok(r.validation.includes('이 시스템 안에서는 미검증'),r.id+' validation');}
}
(async()=>{
 let pass=0,phase='INIT';const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_EXECUTABLE_PATH});
 try{
  for(const width of [390,1280]){
   const mobile=width<600;
   phase='INITIAL_READ '+width;
   {const {ctx,page,seen}=await context(browser,width,null);let release,started,calls=0;
    const held=new Promise(resolve=>{release=resolve;}),requested=new Promise(resolve=>{started=resolve;});
    const newer=JSON.stringify({...JSON.parse(PAYLOAD),generated_at:'2026-10-21T10:00:00Z'});
    await ctx.route('**/macro-evidence.json*',async r=>{calls++;if(calls===1){started();await held;}
     await r.fulfill({status:200,contentType:'application/json',body:calls===1?PAYLOAD:newer});});
    await page.goto(BASE+'#macro',{waitUntil:'domcontentloaded'});await requested;
    assert.equal(await page.locator('[data-refresh-button]').isDisabled(),true,'initial publication must complete before refresh');
    assert.equal(await page.evaluate(()=>DataRefresh.refresh()),'LOADING','programmatic refresh cannot race initial read');
    assert.equal(calls,1);release();await page.locator('[data-me-collection]').waitFor();
    await page.locator('[data-refresh-button]').click();await page.locator('#data-refresh:not([data-refresh-state="LOADING"])').waitFor();
    assert.equal(await page.locator('#data-refresh').getAttribute('data-refresh-state'),'APPLIED');
    assert.equal((await page.evaluate(()=>MacroEvidence.current())).generated_at,JSON.parse(newer).generated_at);
    assert.equal(calls,2);assert.deepEqual(seen.errors,[]);assert.deepEqual(seen.outside,[]);assert.deepEqual(seen.writes,[]);
    await ctx.close();pass++;}
   phase='EMPTY '+width;
   {const {ctx,page,seen}=await context(browser,width,EMPTY);
    await page.goto(BASE+'#macro');await page.locator('[data-macro-evidence]').waitFor();
    await page.locator('[data-me-not-collected]').waitFor();
    assert.equal(await page.locator('[data-me-catalog-row]').count(),13);
    await openCatalog(page,width);const emptyRows=await catalogRows(page);catalogContract(emptyRows,JSON.parse(EMPTY));
    assert.ok(emptyRows.every(r=>r.collected==='NO'&&r.text.includes('SOURCE_NOT_COLLECTED')),'nothing collected yet');
    assert.deepEqual(emptyRows.filter(r=>r.held).map(r=>r.id),['E14'],'DOL held for unverified terms');
    assert.equal(await page.locator('[data-me-catalog] svg').count(),0);
    assert.equal(await text(page,'[data-me-summary-counts]'),'유효 경고 0계열 · 유효 개선 0계열');
    assert.equal(await text(page,'[data-me-scope]'),'탐색 화면 전용 · 공식 판정·확률·매크로 게이트에 쓰지 않음');
    assert.ok((await text(page,'[data-me-panel="observation"]')).includes('사이클 개념도가 아님'));
    assert.equal(await page.locator('[data-me-line]').count(),0);
    assert.equal(await page.locator('[data-macro-evidence] svg').count(),0,'no chart without observations');
    assert.ok((await text(page,'[data-me-no-obs]')).includes('NOT_AVAILABLE'));
    assert.equal(await page.locator('[data-macro-lights]').count(),1,'macro lights still mounted');
    await page.locator('[data-cycle-ring="economy"] [data-cycle-evidence-slot] [data-me-ring-empty]').first().waitFor();
    assert.ok((await text(page,'[data-cycle-ring="economy"] [data-me-ring-empty]')).includes('NOT_AVAILABLE'));
    await noOverflow(page,'empty '+width);
    assert.deepEqual(seen.errors,[]);assert.deepEqual(seen.outside,[]);await ctx.close();pass++;}
   phase='ARTIFACT '+width;
   {const {ctx,page,seen}=await context(browser,width,null);
    const response=await page.request.get(BASE+'macro-evidence.json');assert.ok(response.ok(),'served macro evidence exists');
    const actual=await response.json();
    await page.goto(BASE+'#macro');await page.locator('[data-me-catalog-row]').first().waitFor({state:'attached'});
    const current=await page.evaluate(()=>MacroEvidence.current());
    assert.equal(current.status,actual.state==='NOT_AVAILABLE'?'NOT_AVAILABLE':'LOADED');
    assert.equal(current.generated_at,actual.generated_at,'served collection timestamp reaches the screen');
    assert.equal(await page.locator('[data-me-not-collected]').count(),actual.generated_at===null?1:0);
    assert.equal(await page.locator('[data-me-collection]').count(),actual.generated_at===null?0:1);
    assert.deepEqual(await page.locator('[data-me-catalog-row]').evaluateAll(rows=>rows.map(r=>[r.dataset.meCatalogRow,r.dataset.meCatalogState])),
     actual.indicators.map(i=>[i.id,i.state]),'served indicator states reach the catalog');
    await openCatalog(page,width);catalogContract(await catalogRows(page),actual);
    assert.equal(current.scope.official_judgement,false);assert.equal(current.scope.probability,false);assert.equal(current.scope.macro_gate,false);
    await noOverflow(page,'artifact '+width);assert.deepEqual(seen.errors,[]);assert.deepEqual(seen.outside,[]);assert.deepEqual(seen.writes,[]);
    await ctx.close();pass++;}
   phase='REFRESH '+width;
   {const {ctx,page,seen}=await context(browser,width,EMPTY);let body=EMPTY,http=200;
    await ctx.route('**/macro-evidence.json*',r=>r.fulfill({status:http,contentType:'application/json',body}));
    await page.goto(BASE+'#macro');await page.locator('[data-me-not-collected]').waitFor();
    await page.locator('[data-me-tab="industry"]').click();await page.locator('[data-me-catalog] summary').click();
    const refresh=async()=>{await page.locator('[data-refresh-button]').click();await page.locator('#data-refresh:not([data-refresh-state="LOADING"])').waitFor();};
    body=PAYLOAD;await refresh();
    assert.equal(await page.locator('#data-refresh').getAttribute('data-refresh-state'),'APPLIED','macro-only publication applies');
    assert.equal((await page.evaluate(()=>MacroEvidence.current())).generated_at,JSON.parse(PAYLOAD).generated_at);
    assert.equal(await page.locator('[data-me-not-collected]').count(),0);
    assert.equal(await page.locator('[data-me-tab="industry"]').getAttribute('aria-selected'),'true','cycle selection survives refresh');
    assert.equal(await page.locator('[data-me-indicator]').inputValue(),'E01');
    assert.equal(await page.locator('[data-me-catalog]').getAttribute('open'),'','catalog expansion survives refresh');
    await page.locator('[data-me-tab="economy"]').click();await pick(page,'E39');await page.locator('[data-me-replay]').check();
    await page.evaluate(()=>{location.hash='home';});await page.locator('#content h1').waitFor();
    await page.evaluate(()=>{location.hash='macro';});await page.locator('[data-me-meta="E39"]').waitFor();
    assert.equal(await page.locator('[data-me-replay]').isChecked(),true,'indicator and reconstruction choice survive navigation');
    await refresh();assert.equal(await page.locator('#data-refresh').getAttribute('data-refresh-state'),'UNCHANGED');
    const previous=await page.evaluate(()=>({macro:MacroEvidence.current(),generation:DataRefresh.publication().generation}));
    // A failed macro fetch and a malformed response preserve the whole previous publication.
    const invalidLabels=JSON.parse(PAYLOAD);delete invalidLabels.labels;
    const invalidSummary=JSON.parse(PAYLOAD);invalidSummary.summary.economy.warning_families=null;
    const invalidObservation=JSON.parse(PAYLOAD);Object.values(invalidObservation.series).find(s=>s.obs.length).obs[0]=null;
    for(const [failure,status,payload] of [['HTTP',503,'{}'],['REMOVED',404,'{}'],['INVALID',200,'{}'],
     ['LABELS',200,JSON.stringify(invalidLabels)],['SUMMARY',200,JSON.stringify(invalidSummary)],['OBSERVATION',200,JSON.stringify(invalidObservation)]]){http=status;body=payload;await refresh();
     assert.equal(await page.locator('#data-refresh').getAttribute('data-refresh-state'),'FAILED',failure);
     assert.deepEqual(await page.evaluate(()=>({macro:MacroEvidence.current(),generation:DataRefresh.publication().generation})),previous,failure+' keeps previous values');}
    // Successful macro data is staged, never installed before all other public readers succeed.
    http=200;body=JSON.stringify({...JSON.parse(PAYLOAD),generated_at:'2026-10-09T10:00:00Z'});
    await ctx.route('**/sec-qgv2.json*',r=>r.fulfill({status:503,body:''}));await refresh();
    assert.equal(await page.locator('#data-refresh').getAttribute('data-refresh-state'),'FAILED');
    assert.deepEqual(await page.evaluate(()=>({macro:MacroEvidence.current(),generation:DataRefresh.publication().generation})),previous,'other-file failure does not install staged macro data');
    await noOverflow(page,'refresh '+width);assert.deepEqual(seen.errors,[]);assert.deepEqual(seen.outside,[]);assert.deepEqual(seen.writes,[]);
    await ctx.close();pass++;}
   phase='DATA '+width;
   {const {ctx,page,seen}=await context(browser,width,PAYLOAD);
    await page.goto(BASE+'#macro');await page.locator('[data-me-summary-counts]').waitFor();
    const before=await storage(page);
    await page.waitForFunction(()=>MacroEvidence.current().status==='LOADED');
    assert.equal(await page.locator('[data-me-tab="economy"]').getAttribute('aria-selected'),'true');
    assert.equal(await text(page,'[data-me-summary-counts]'),'유효 경고 2계열 · 유효 개선 3계열');
    assert.ok((await text(page,'[data-me-summary-families]')).startsWith('경고: 금리곡선, 운송'));
    // FOMC events: seven on seven days -> mobile 5 + 더 보기 (2), PC all 7.
    await pick(page,'E40');
    assert.equal(await page.locator('[data-me-line]').count(),mobile?5:7);
    assert.equal(await page.locator('[data-me-more]').getAttribute('data-me-more'),mobile?'2':'0');
    assert.ok(await page.locator('[data-me-line][data-me-line-basis="COLLECTION_TIME"]').count()>=2,'collection-time lines are marked');
    if(mobile){await page.locator('[data-me-more] summary').click();await page.locator('[data-me-more-line]').first().check();
     assert.equal(await page.locator('[data-me-line]').count(),6,'a line from 더 보기 is added');}
    assert.ok((await text(page,'[data-me-interpretation]')).includes('해석 후보: 첫 인하'));
    // Sahm: the condition line and the revision that cleared it; the revised observation and release ticks.
    await pick(page,'E13');
    assert.equal(await page.locator('[data-me-line]').count(),2);
    assert.equal(await page.locator('[data-me-revision="2026-08"]').count(),1);
    assert.ok(await page.locator('[data-me-release="FIRST"]').count()>=1&&await page.locator('[data-me-release="REVISION"]').count()===1);
    const events=await text(page,'[data-me-events="economy"]');
    for(const s of['수정 발표로 조건 해제: Sahm 발동','수집 시각 기준','발표 시각(게시 파일 시각)','해석 후보 · 미승인','E13.v0'])assert.ok(events.includes(s),s);
    // Reconstruction layer: off by default, dashed lines at reference periods when turned on.
    await pick(page,'E09');
    assert.equal(await page.locator('[data-me-replay-line]').count(),0);
    await page.locator('[data-me-replay]').check();
    assert.ok(await page.locator('[data-me-replay-line]').count()>=1);
    assert.ok((await text(page,'.me-replay-toggle')).includes('발표 시각 아님'));
    // Separate cycles: market (FOMC only, price lines device-only) and industry (transport).
    await page.locator('[data-me-tab="market"]').click();
    assert.equal(await text(page,'[data-me-summary-counts]'),'유효 경고 0계열 · 유효 개선 0계열');
    assert.ok((await text(page,'[data-me-market-note]')).includes('기기 전용'));
    assert.deepEqual(await page.locator('[data-me-indicator] option').evaluateAll(o=>o.map(x=>x.value)),['E40']);
    await page.locator('[data-me-tab="industry"]').click();
    assert.equal(await text(page,'[data-me-summary-counts]'),'유효 경고 1계열 · 유효 개선 0계열');
    assert.deepEqual(await page.locator('[data-me-indicator] option').evaluateAll(o=>o.map(x=>x.value)),['E01']);
    assert.equal(await page.locator('[data-me-line]').count(),1);
    assert.equal(await page.locator('[data-me-line]').getAttribute('data-me-line-basis'),'SOURCE_LAST_MODIFIED');
    // Catalog list (13 indicators) is separate from the event list; the held DOL series shows no data.
    assert.equal(await page.locator('[data-me-catalog-row="E14"]').getAttribute('data-me-catalog-state'),'NOT_AVAILABLE');
    assert.equal(await page.locator('[data-me-catalog-row="E21"]').getAttribute('data-me-catalog-state'),'NOT_AVAILABLE');
    await openCatalog(page,width);const rows=await catalogRows(page),payload=JSON.parse(PAYLOAD);catalogContract(rows,payload);
    const row=id=>rows.find(r=>r.id===id);
    assert.equal(row('E14').held,true);assert.ok(row('E14').text.includes('TERMS_UNVERIFIED'));assert.ok(!row('E14').text.includes('DOL:'));
    for(const id of['E21','E26']){assert.equal(row(id).collected,'NO');const [[sid,c,t]]=row(id).series;
     assert.equal(c,'NO');assert.equal(t,sid+' · NOT_AVAILABLE · SOURCE_KEY_NOT_CONFIGURED (API 키 미설정)','Census key missing is a reason, never 0');}
    assert.equal(row('E09').collected,'YES');assert.ok(row('E09').rule.includes('[문헌]'));assert.ok(row('E09').validation.startsWith('문헌상 사후 검증만'));
    assert.deepEqual(row('E39').series.map(x=>x[1]),['YES','YES']);assert.ok(row('E40').validation.startsWith('사건은 검증 불필요'));
    assert.ok((await text(page,'[data-me-catalog]')).includes('발생 사건 목록과 별개'));
    // The opened catalog stays open across this module's own redraws (tab change), in this page's RAM only.
    await page.locator('[data-me-tab="market"]').click();assert.equal(await page.locator('[data-me-catalog]').getAttribute('open'),'');
    await noOverflow(page,'catalog '+width);
    await page.locator('[data-me-catalog] > summary').click();assert.equal(await page.locator('[data-me-catalog]').getAttribute('open'),null);
    // Cycle ring (C1): observations -> evidence slots of the focused phase; 관측 그래프 selects the indicator here.
    await page.locator('[data-me-tab="economy"]').click();
    const ring='[data-cycle-ring="economy"]';
    await page.locator(ring+' [data-me-ring-line]').first().waitFor();
    const lines=await page.locator(ring+' [data-me-ring-line]').evaluateAll(n=>n.map(x=>[x.dataset.meRingLine,x.dataset.meRingState]));
    assert.ok(lines.length>=4&&lines.some(([c,st])=>c==='E25'&&st==='LIVE')&&lines.some(([c,st])=>c==='E14'&&st==='NOT_AVAILABLE'),JSON.stringify(lines));
    const slotText=await page.locator(ring+' [data-me-ring-line="E25"]').first().textContent();
    for(const s of['v0 · 미검증','최신 관측','E25.v0'])assert.ok(slotText.includes(s),s);
    assert.equal(await page.locator(ring+' [data-cycle-interval], '+ring+' [data-cycle-point]').count(),0,'evidence gives the ring no position');
    await page.locator(ring+' [data-me-ring-show="E25"]').first().click();
    await page.waitForFunction(()=>document.querySelector('[data-me-indicator]')?.value==='E25');
    assert.equal(await page.locator('[data-me-meta="E25"]').count(),1);
    await page.locator('[data-me-tab="market"]').click();
    await page.locator('[data-cycle-ring="economy"] [data-cycle-next]').click();
    await page.waitForFunction(()=>document.querySelector('[data-me-tab="economy"]')?.getAttribute('aria-selected')==='true');
    // API for the cycle ring (C1).
    const api=await page.evaluate(()=>({c:MacroEvidence.current(),m:MacroEvidence.events({cycle:'market'}).length,i:MacroEvidence.events({cycle:'industry'}).map(e=>e.indicator),
     r:MacroEvidence.events({cycle:'economy',layer:'REPLAY'}).every(e=>e.layer==='REPLAY')}));
    assert.deepEqual(api.c.summary.economy.warning,['C','T']);assert.equal(api.c.scope.official_judgement,false);assert.equal(api.c.scope.macro_gate,false);
    assert.equal(api.m,7);assert.deepEqual(api.i,['E01']);assert.equal(api.r,true);
    await noOverflow(page,'data '+width);await page.screenshot({path:SHOTS+'/macro-evidence-'+width+'.png',fullPage:true}).catch(()=>{});
    assert.equal(await storage(page),before,'nothing is stored');assert.deepEqual(seen.writes,[],'nothing is sent');
    assert.deepEqual(seen.errors,[]);assert.deepEqual(seen.outside,[]);await ctx.close();pass++;}
  }
  console.log('MACRO_EVIDENCE_BROWSER_OK pass='+pass);
 }catch(e){console.error('MACRO_EVIDENCE_BROWSER_FAIL '+phase+' '+(e&&e.message));process.exitCode=1;}
 finally{await browser.close();}
})();
