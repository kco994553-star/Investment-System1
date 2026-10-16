'use strict';
// S07 news / S15 watchlist disclosure list and the company earnings status ('추정' -> '확인'), at 390 and 1440.
// Synthetic, schema-valid payloads by route interception only; no request leaves the local origin.
const {chromium}=require('playwright'),assert=require('node:assert/strict'),path=require('node:path');
const fixture=require('./sec_disclosures_fixture.js');
const BASE=process.env.PAGES_COCKPIT_URL,SHOTS=process.env.PAGES_COCKPIT_EVIDENCE_DIR||'.';
const noOverflow=page=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1);
(async()=>{const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_EXECUTABLE_PATH});let phase='START',pass=0,fail=0;
 try{for(const width of [390,1440]){const context=await browser.newContext({viewport:{width,height:900},serviceWorkers:'block'});const outside=[];
  await context.route('**/*',r=>{const u=new URL(r.request().url());if(u.origin===new URL(BASE).origin)return r.continue();outside.push(u.hostname);return r.abort();});
  await context.route('**/sec-disclosures.json*',r=>r.fulfill({status:200,contentType:'application/json',body:JSON.stringify(fixture.payload())}));
  await context.route('**/sec-filing-windows.json*',r=>r.fulfill({status:200,contentType:'application/json',body:JSON.stringify(fixture.filingWindows())}));
  const page=await context.newPage();let errors=0;page.on('pageerror',()=>errors++);
  try{
   phase='S07';await page.goto(BASE+'#news');await page.locator('#news-disclosures [data-disclosure]').first().waitFor();
   const items=page.locator('#news-disclosures [data-disclosure]');assert.equal(await items.count(),5);
   assert.deepEqual(await items.evaluateAll(n=>n.map(x=>x.dataset.occurrence)),['NEW','NEW','NEW','REPEAT','NEW']);
   assert.equal(await page.locator('#news-disclosures [data-channel="DISCLOSURE"]').first().textContent(),'공시·확정');
   assert.deepEqual(await items.evaluateAll(n=>n.map(x=>x.dataset.classification)),['OTHER','MATERIAL_AGREEMENT','OFFICERS_DIRECTORS','RESULTS','RESULTS']);
   assert.equal(await page.locator('[data-disclosure$="-000101"] [data-classification-label]').textContent(),'실적 (Results)');
   assert.equal(await page.locator('[data-disclosure$="-000140"] [data-occurrence-label]').textContent(),'정정·반복');
   assert.ok((await page.locator('[data-disclosure$="-000101"] [data-items]').textContent()).includes('2.02 영업 실적 및 재무 상태 (Results of Operations and Financial Condition)'));
   const link=page.locator('[data-disclosure$="-000101"] [data-exhibit-link]');assert.equal(await link.getAttribute('target'),'_blank');assert.equal(await link.getAttribute('rel'),'noopener noreferrer');
   assert.ok((await link.getAttribute('href')).startsWith('https://www.sec.gov/Archives/edgar/data/1045810/'));assert.ok((await page.locator('[data-disclosure$="-000150"]').textContent()).includes('EX-99.1 · NOT_AVAILABLE'));
   assert.equal(await page.locator('#news-disclosures [data-score-effect]').getAttribute('data-score-effect'),'NONE');
   assert.ok(await noOverflow(page),'overflow S07');await page.locator('#news-disclosures').screenshot({path:path.join(SHOTS,'sec-disclosures-news-'+width+'.png')});
   phase='S15';await page.evaluate(()=>localStorage.setItem('investment.web.v1.personal',JSON.stringify({version:1,interests:['nvda'],groups:[]})));await page.goto(BASE+'#watchlist');await page.reload();
   await page.locator('#watch-disclosures [data-disclosure]').first().waitFor();assert.deepEqual(await page.locator('#watch-disclosures [data-disclosure]').evaluateAll(n=>n.map(x=>x.dataset.occurrence)),['REPEAT','NEW']);
   assert.match(await page.locator('[data-week-filings]').textContent(),/^\d+ · 추정 \d+ · 확인 \d+ · /);assert.ok(await noOverflow(page),'overflow S15');
   await page.locator('#watch-disclosures').screenshot({path:path.join(SHOTS,'sec-disclosures-watchlist-'+width+'.png')});
   // S04 keeps one next-earnings line; the confirmed-status badge is on S05 (E row) and the raw filing card in Settings >
   // 원자료 보기(개발자용) (owner decision 2026-10-14).
   phase='COMPANY';await page.goto(BASE+'#company/nvda');await page.locator('[data-next-earnings-line]').waitFor();assert.equal(await page.locator('[data-next-earnings-line]').count(),1);
   assert.match(await page.locator('[data-next-earnings-line]').textContent(),/^다음 실적 (\d\d\/\d\d경 \(확정 아님\) · D-\d+|확인 불가)$/);assert.ok(await noOverflow(page),'overflow company');
   await page.goto(BASE+'#analysis/nvda');await page.locator('[data-analysis-tab="events"]').click();await page.locator('[data-earnings-status="CONFIRMED"]').first().waitFor();
   assert.equal(await page.locator('[data-earnings-status="CONFIRMED"]').first().textContent(),'확인');assert.equal(await page.locator('[data-earnings-status="ESTIMATED"]').count(),0);
   await page.goto(BASE+'#settings');await page.locator('[data-raw-data] > summary').click();await page.locator('[data-raw-data] [data-earnings-confirmed]').first().waitFor();
   assert.ok(await page.locator('[data-raw-data] [data-earnings-confirmed]').count()>0);
   assert.equal(errors,0);assert.deepEqual(outside,[]);pass++;console.log('PASS sec disclosures S07/S15/company '+width);
  }catch(e){fail++;console.log('FAIL sec disclosures '+width+' '+phase+' '+(e.code==='ERR_ASSERTION'?'CONTRACT':'EXECUTION'));if(process.env.DEBUG_TEST)console.log(e);}finally{await context.close();}}}
 finally{await browser.close();}console.log('COUNTS pass='+pass+' fail='+fail);process.exitCode=fail?1:0;})();
