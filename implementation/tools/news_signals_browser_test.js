'use strict';
// S07 news / S15 watchlist: one chronological '공시·확정' + '뉴스·신호' list at 390 and 1440. Distinct badges, GDELT attribution,
// new/repeat markers, the IR release that repeats an 8-K Exhibit 99.1 collapsed under that 8-K, news repeats collapsed.
// Synthetic, schema-valid payloads by route interception only; no request leaves the local origin.
const {chromium}=require('playwright'),assert=require('node:assert/strict'),path=require('node:path');
const api=require('../src/investment_system/product/web_assets/news-signals.js'),secFixture=require('./sec_disclosures_fixture.js'),fixture=require('./news_signals_fixture.js');
const BASE=process.env.PAGES_COCKPIT_URL,SHOTS=process.env.PAGES_COCKPIT_EVIDENCE_DIR||'.';
const noOverflow=page=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1);
const NOW=Date.now(),SEC=secFixture.payload(NOW),NEWS=fixture.payload(NOW,SEC);
const key=r=>r.channel==='NEWS'?'N:'+r.item.group_id:'D:'+r.event.accession,rowKeys=page=>page.locator('[data-timeline] > li').evaluateAll(n=>n.map(x=>x.dataset.news?'N:'+x.dataset.news:'D:'+x.dataset.disclosure));
(async()=>{const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_EXECUTABLE_PATH});let phase='START',pass=0,fail=0;
 try{for(const width of [390,1440]){const context=await browser.newContext({viewport:{width,height:900},serviceWorkers:'block'});const outside=[];
  await context.route('**/*',r=>{const u=new URL(r.request().url());if(u.origin===new URL(BASE).origin)return r.continue();outside.push(u.hostname);return r.abort();});
  await context.route('**/sec-disclosures.json*',r=>r.fulfill({status:200,contentType:'application/json',body:JSON.stringify(SEC)}));
  await context.route('**/news-signals.json*',r=>r.fulfill({status:200,contentType:'application/json',body:JSON.stringify(NEWS)}));
  const page=await context.newPage();let errors=0;page.on('pageerror',()=>errors++);
  try{
   phase='S07';await page.goto(BASE+'#news');await page.locator('#news-disclosures [data-news]').first().waitFor();
   assert.deepEqual(await rowKeys(page.locator('#news-disclosures')),api.timeline({sec:SEC,news:NEWS}).slice(0,30).map(key));
   assert.equal(await page.locator('#news-disclosures [data-channel="NEWS"]').first().textContent(),'뉴스·신호');
   assert.equal(await page.locator('#news-disclosures [data-channel="DISCLOSURE"]').first().textContent(),'공시·확정');
   assert.ok(await page.locator('#news-disclosures [data-channel="NEWS"]').first().evaluate(n=>n.classList.contains('news-signal')&&!n.classList.contains('LIVE')));
   const gdelt=page.locator('#news-disclosures [data-gdelt-attribution]');assert.equal(await gdelt.getAttribute('href'),'https://www.gdeltproject.org/');assert.equal(await gdelt.getAttribute('rel'),'noopener noreferrer');assert.equal(await gdelt.textContent(),'The GDELT Project');
   assert.equal(await page.locator('#news-disclosures [data-score-effect]').getAttribute('data-score-effect'),'NONE');
   const nvda=NEWS.items.find(i=>i.link==='https://news.example.com/nvda-record'),group=page.locator(`[data-news="${nvda.group_id}"]`);
   assert.equal(await group.locator('[data-news-occurrence-label]').textContent(),'새 소식');assert.equal(await group.locator('[data-news-classification-label]').textContent(),'실적 (Earnings)');
   const repeats=group.locator('details[data-news-repeats="1"]');assert.equal(await repeats.getAttribute('open'),null);assert.equal(await repeats.locator('[data-news-occurrence="REPEAT"]').count(),1);
   const link=group.locator('[data-news-link]').first();assert.equal(await link.getAttribute('target'),'_blank');assert.equal(await link.getAttribute('rel'),'noopener noreferrer');assert.equal(await link.getAttribute('href'),nvda.link);
   const msft=SEC.events.find(e=>e.company_id==='msft'),related=page.locator(`[data-disclosure="${msft.accession}"] details[data-related-ir]`);
   assert.equal(await related.count(),1);assert.equal(await related.getAttribute('open'),null);assert.equal(await related.locator('[data-relation="RELATED_TO_8K"] [data-news-link]').getAttribute('href'),'https://news.microsoft.com/synthetic/agreement');
   assert.equal(await page.locator('#news-disclosures [data-news-link][href="https://news.microsoft.com/synthetic/agreement"]').count(),1,'related IR appears only under its 8-K');
   assert.ok((await page.locator('[data-news][data-news-source="IR"]').first().textContent()).includes('회사 IR'));
   assert.ok(await noOverflow(page),'overflow S07');await page.locator('#news-disclosures').screenshot({path:path.join(SHOTS,'news-signals-news-'+width+'.png')});
   phase='S15';await page.evaluate(()=>localStorage.setItem('investment.web.v1.personal',JSON.stringify({version:1,interests:['msft'],groups:[]})));await page.goto(BASE+'#watchlist');await page.reload();
   await page.locator('#watch-disclosures [data-timeline] > li').first().waitFor();
   assert.deepEqual(await rowKeys(page.locator('#watch-disclosures')),api.timeline({sec:SEC,news:NEWS},{companyIds:['msft']}).map(key));
   assert.equal(await page.locator('#watch-disclosures [data-related-ir]').count(),1);assert.ok(await noOverflow(page),'overflow S15');
   await page.locator('#watch-disclosures').screenshot({path:path.join(SHOTS,'news-signals-watchlist-'+width+'.png')});
   assert.equal(errors,0);assert.deepEqual(outside,[]);pass++;console.log('PASS news signals S07/S15 '+width);
  }catch(e){fail++;console.log('FAIL news signals '+width+' '+phase+' '+(e.code==='ERR_ASSERTION'?'CONTRACT':'EXECUTION'));if(process.env.DEBUG_TEST)console.log(e);}finally{await context.close();}}}
 finally{await browser.close();}console.log('COUNTS pass='+pass+' fail='+fail);process.exitCode=fail?1:0;})();
