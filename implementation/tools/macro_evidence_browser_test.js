'use strict';
// Macro evidence lines on the macro screen at 390 and 1280: the build's NOT_COLLECTED placeholder, then the synthetic
// multi-run payload (tests/fixtures/macro_evidence/browser_payload.json, written by tests/macro_evidence_fixture.py):
// 경기/주식시장/산업 tabs counted separately, recent-5 lines + "더 보기" on mobile (10 on PC), collection-time lines
// labelled as such, revision markers and release ticks, the reconstruction layer off by default, interpretations
// labelled "해석 후보 · 미승인", the held DOL series and the C1 API. Nothing is stored or sent; no outside host is contacted.
const assert=require('node:assert/strict');const fs=require('node:fs');const path=require('node:path');const {chromium}=require('playwright');
const BASE=process.env.PAGES_COCKPIT_URL,SHOTS=process.env.PAGES_COCKPIT_EVIDENCE_DIR||'.';
const PAYLOAD=fs.readFileSync(path.join(__dirname,'../tests/fixtures/macro_evidence/browser_payload.json'),'utf8');
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
(async()=>{
 let pass=0,phase='INIT';const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_EXECUTABLE_PATH});
 try{
  for(const width of [390,1280]){
   const mobile=width<600;
   phase='EMPTY '+width;
   {const {ctx,page,seen}=await context(browser,width,null);
    await page.goto(BASE+'#macro');await page.locator('[data-macro-evidence]').waitFor();
    await page.locator('[data-me-not-collected]').waitFor();
    assert.equal(await page.locator('[data-me-catalog-row]').count(),13);
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
