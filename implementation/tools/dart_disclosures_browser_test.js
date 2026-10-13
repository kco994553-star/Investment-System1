'use strict';
// S07 news / S15 watchlist DART (042700) disclosure list at 390 and 1440: '공시·확정', source DART, classification, link attributes,
// company filter and the offline NOT_AVAILABLE state. Synthetic Python-generated vectors by route interception; no request leaves the origin.
const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const vectors=JSON.parse(fs.readFileSync(path.join(__dirname,'../tests/fixtures/dart_public_vectors_v1.json'),'utf8'));
const live=vectors.cases.find(c=>c.name==='live').payload;
const BASE=process.env.PAGES_COCKPIT_URL,SHOTS=process.env.PAGES_COCKPIT_EVIDENCE_DIR||'.';
const noOverflow=page=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1);
(async()=>{const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_EXECUTABLE_PATH});let phase='START',pass=0,fail=0;
 try{for(const width of [390,1440]){const context=await browser.newContext({viewport:{width,height:900},serviceWorkers:'block'});const outside=[];
  await context.route('**/*',r=>{const u=new URL(r.request().url());if(u.origin===new URL(BASE).origin)return r.continue();outside.push(u.hostname);return r.abort();});
  const page=await context.newPage();let errors=0;page.on('pageerror',()=>errors++);
  try{
   phase='OFFLINE';await page.goto(BASE+'#news');await page.locator('#news-dart-disclosures [data-dart-disclosures]').waitFor();
   assert.equal(await page.locator('#news-dart-disclosures [data-disclosure-state]').textContent(),'NOT_AVAILABLE');
   assert.equal(await page.locator('#news-dart-disclosures [data-disclosure-reason]').getAttribute('data-disclosure-reason'),'NOT_COLLECTED');
   assert.equal(await page.locator('#news-dart-disclosures [data-disclosure]').count(),0);
   phase='S07';await context.route('**/dart-disclosures.json*',r=>r.fulfill({status:200,contentType:'application/json',body:JSON.stringify(live)}));
   await page.reload();await page.locator('#news-dart-disclosures [data-disclosure]').first().waitFor();
   const items=page.locator('#news-dart-disclosures [data-disclosure]');assert.equal(await items.count(),live.events.length);
   assert.deepEqual(await items.evaluateAll(n=>n.map(x=>x.dataset.disclosure)),live.events.map(e=>e.rcept_no));
   assert.deepEqual(await items.evaluateAll(n=>[...new Set(n.map(x=>x.dataset.source))]),['DART']);
   assert.equal(await page.locator('#news-dart-disclosures h2').textContent(),'공시·확정 · DART');
   assert.equal(await page.locator('#news-dart-disclosures [data-channel="DISCLOSURE"]').first().textContent(),'공시·확정');
   assert.equal(await page.locator('[data-disclosure="20260725000301"] [data-classification-label]').textContent(),'실적(잠정실적 공정공시) (Results (preliminary earnings))');
   assert.equal(await page.locator('[data-disclosure="20260801000301"] [data-occurrence-label]').textContent(),'정정·반복');
   const link=page.locator('[data-disclosure="20260725000301"] [data-filing-link]');assert.equal(await link.getAttribute('target'),'_blank');assert.equal(await link.getAttribute('rel'),'noopener noreferrer');
   assert.equal(await link.getAttribute('href'),'https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260725000301');assert.equal(await link.textContent(),'연결재무제표기준영업(잠정)실적(공정공시)');
   assert.ok((await page.locator('[data-disclosure="20260725000301"]').textContent()).includes('DART · 2026-07-25 KST'));
   assert.equal(await page.locator('#news-dart-disclosures [data-score-effect]').getAttribute('data-score-effect'),'NONE');
   assert.equal(await page.locator('#news-pane #news-dart-disclosures').count(),0);await page.locator('#show-network').click();assert.equal(await page.locator('#news-dart-disclosures').isVisible(),false);
   await page.locator('#show-news').click();assert.equal(await page.locator('#news-dart-disclosures').isVisible(),true);
   assert.ok(await noOverflow(page),'overflow S07');await page.locator('#news-dart-disclosures').screenshot({path:path.join(SHOTS,'dart-disclosures-news-'+width+'.png')});
   phase='S07_COMPANY';await page.goto(BASE+'#news/nvda');await page.locator('#news-dart-disclosures [data-dart-disclosures]').waitFor();
   assert.equal(await page.locator('#news-dart-disclosures [data-disclosure]').count(),0);
   phase='S15';await page.evaluate(()=>localStorage.setItem('investment.web.v1.personal',JSON.stringify({version:1,interests:['hanmi'],groups:[]})));await page.goto(BASE+'#watchlist');await page.reload();
   await page.locator('#watch-dart-disclosures [data-disclosure]').first().waitFor();assert.equal(await page.locator('#watch-dart-disclosures [data-disclosure]').count(),live.events.length);
   assert.ok(await noOverflow(page),'overflow S15');await page.locator('#watch-dart-disclosures').screenshot({path:path.join(SHOTS,'dart-disclosures-watchlist-'+width+'.png')});
   phase='S15_OTHER';await page.evaluate(()=>localStorage.setItem('investment.web.v1.personal',JSON.stringify({version:1,interests:['nvda'],groups:[]})));await page.reload();
   await page.locator('#watch-dart-disclosures [data-dart-disclosures]').waitFor();assert.equal(await page.locator('#watch-dart-disclosures [data-disclosure]').count(),0);
   assert.equal(await page.locator('#watch-dart-disclosures .empty').textContent(),'관심 기업의 DART 공시가 없습니다.');
   phase='INVALID';await context.unroute('**/dart-disclosures.json*');await context.route('**/dart-disclosures.json*',r=>r.fulfill({status:200,contentType:'application/json',body:JSON.stringify({...live,price:1})}));
   await page.goto(BASE+'#news');await page.reload();await page.locator('#news-dart-disclosures [data-dart-disclosures]').waitFor();
   assert.equal(await page.locator('#news-dart-disclosures [data-disclosure]').count(),0);assert.ok((await page.locator('#news-dart-disclosures').textContent()).includes('DART 공시 자료가 연결되지 않았습니다.'));
   assert.equal(errors,0);assert.deepEqual(outside,[]);pass++;console.log('PASS dart disclosures S07/S15 '+width);
  }catch(e){fail++;console.log('FAIL dart disclosures '+width+' '+phase+' '+(e.code==='ERR_ASSERTION'?'CONTRACT':'EXECUTION'));if(process.env.DEBUG_TEST)console.log(e);}finally{await context.close();}}}
 finally{await browser.close();}console.log('COUNTS pass='+pass+' fail='+fail);process.exitCode=fail?1:0;})();
