'use strict';
// S07 news / S15 watchlist: one chronological '공시·확정' + '뉴스·신호' list at 390 and 1440. Distinct badges, GDELT attribution,
// new/repeat markers, the IR release that repeats an 8-K Exhibit 99.1 collapsed under that 8-K, news repeats collapsed.
// Display filters (channel / category / new-repeat / order) persist across #news -> #watchlist in sessionStorage; each row has a closed
// '근거 보기' with source link, published/collected times and dedup status; importance is held/watchlist only.
// Synthetic, schema-valid payloads by route interception only; no request leaves the local origin.
const {chromium}=require('playwright'),assert=require('node:assert/strict'),path=require('node:path');
const api=require('../src/investment_system/product/web_assets/news-signals.js'),secFixture=require('./sec_disclosures_fixture.js'),fixture=require('./news_signals_fixture.js');
const BASE=process.env.PAGES_COCKPIT_URL,SHOTS=process.env.PAGES_COCKPIT_EVIDENCE_DIR||'.';
const noOverflow=page=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1);
const NOW=Date.now(),SEC=secFixture.payload(NOW),NEWS=fixture.payload(NOW,SEC);
const key=r=>r.channel==='NEWS'?'N:'+r.item.group_id:'D:'+r.event.accession,rowKeys=page=>page.locator('[data-timeline] > li').evaluateAll(n=>n.map(x=>x.dataset.news?'N:'+x.dataset.news:'D:'+x.dataset.disclosure));
(async()=>{const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_EXECUTABLE_PATH});let phase='START',pass=0,fail=0;
 try{for(const width of [390,1280,1440]){const context=await browser.newContext({viewport:{width,height:900},serviceWorkers:'block'});const outside=[];
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
   phase='EVIDENCE';const ev=group.locator(':scope > details[data-evidence="NEWS"]');assert.equal(await ev.count(),1);assert.equal(await ev.getAttribute('open'),null);assert.equal(await ev.locator('summary').textContent(),'근거 보기');
   await ev.locator('summary').click();const evText=await ev.textContent();assert.ok(evText.includes('발표 시각')&&evText.includes('수집 시각')&&evText.includes('중복 처리')&&evText.includes('반복 1건')&&evText.includes('언론 보도 제목 (내용 미확인)'));
   assert.equal(await ev.locator('[data-evidence-link]').getAttribute('href'),nvda.link);assert.equal(await ev.locator('[data-evidence-link]').getAttribute('rel'),'noopener noreferrer');
   const secEv=page.locator(`[data-disclosure="${msft.accession}"] details[data-evidence="SEC"]`);assert.equal(await secEv.count(),1);await secEv.locator('summary').click();
   assert.equal(await secEv.locator('[data-evidence-link]').first().getAttribute('href'),msft.link);assert.ok((await secEv.textContent()).includes('수집 시각'));
   assert.equal(await page.locator('#news-disclosures [data-timeline] > li').count(),await page.locator('#news-disclosures [data-timeline] > li > details[data-evidence]').count());
   assert.ok((await page.locator('#news-disclosures [data-importance-basis]').textContent()).startsWith('중요도 기준: 보유·관심 여부'));
   for(const word of ['RIG','Track D','Impact Graph'])assert.equal((await page.locator('#news-disclosures').textContent()).includes(word),false,word);
   assert.ok(await noOverflow(page),'overflow evidence');await page.locator('#news-disclosures').screenshot({path:path.join(SHOTS,'news-evidence-'+width+'.png')});
   phase='FILTER';const channel=page.locator('#news-disclosures select[data-news-filter="channel"]');await channel.selectOption('DISCLOSURE');
   assert.deepEqual(await rowKeys(page.locator('#news-disclosures')),api.timeline({sec:SEC,news:NEWS}).slice(0,30).filter(r=>r.channel==='DISCLOSURE').map(key));
   assert.match(await page.locator('#news-disclosures [data-news-filter-count]').textContent(),/^표시 5건 · 최신 30행 안에서 거름$/);
   await page.locator('#news-disclosures select[data-news-filter="category"]').selectOption('NEWS:LEGAL');assert.equal(await page.locator('#news-disclosures [data-news-filter-empty]').count(),1);
   await page.locator('#news-disclosures select[data-news-filter="category"]').selectOption('RESULTS');await channel.selectOption('ALL');
   assert.deepEqual(await rowKeys(page.locator('#news-disclosures')),api.filterRows(api.timeline({sec:SEC,news:NEWS}).slice(0,30),{channel:'ALL',category:'RESULTS',occurrence:'ALL',order:'TIME'}).map(key));
   await page.locator('#news-disclosures select[data-news-filter="occurrence"]').selectOption('NEW');await channel.selectOption('DISCLOSURE');
   assert.ok(await page.locator('#news-disclosures [data-timeline] > li').count()>0);assert.ok(await noOverflow(page),'overflow filters');await page.locator('#news-disclosures').screenshot({path:path.join(SHOTS,'news-filters-'+width+'.png')});
   await page.locator('#news-disclosures select[data-news-filter="category"]').selectOption('NEWS:LEGAL');
   phase='S15';await page.evaluate(()=>localStorage.setItem('investment.web.v1.personal',JSON.stringify({version:1,interests:['msft'],groups:[]})));await page.goto(BASE+'#watchlist');await page.reload();
   await page.locator('#watch-disclosures [data-news-filters]').waitFor();
   assert.equal(await page.locator('#watch-disclosures select[data-news-filter="channel"]').inputValue(),'DISCLOSURE','filters persist across screens');
   assert.equal(await page.locator('#watch-disclosures select[data-news-filter="occurrence"]').inputValue(),'NEW');
   assert.equal(await page.locator('#watch-disclosures select[data-news-filter="category"]').inputValue(),'ALL','category absent from this screen falls back to all');
   assert.ok((await page.locator('#watch-disclosures [data-timeline] > li').evaluateAll(n=>n.map(x=>x.dataset.disclosure?'D':'N'))).every(x=>x==='D'));
   await page.locator('#watch-disclosures [data-news-filter-reset]').click();assert.equal(await page.evaluate(()=>JSON.parse(sessionStorage.getItem('investment.web.v1.news-filters')).channel),'ALL');
   await page.locator('#watch-disclosures [data-timeline] > li').first().waitFor();
   assert.deepEqual(await rowKeys(page.locator('#watch-disclosures')),api.timeline({sec:SEC,news:NEWS},{companyIds:['msft']}).map(key));
   assert.equal(await page.locator('#watch-disclosures [data-related-ir]').count(),1);assert.ok(await noOverflow(page),'overflow S15');
   await page.locator('#watch-disclosures').screenshot({path:path.join(SHOTS,'news-signals-watchlist-'+width+'.png')});
   phase='IMPORTANCE';await page.goto(BASE+'#news');await page.locator('#news-disclosures [data-news-filters]').waitFor();await page.locator('#news-disclosures select[data-news-filter="order"]').selectOption('IMPORTANCE');
   const tiers=await page.locator('#news-disclosures [data-timeline] > li [data-importance]').evaluateAll(n=>n.map(x=>x.dataset.importance));const order=['HELD','INTEREST','OTHER','MARKET'];
   assert.equal(tiers.length,await page.locator('#news-disclosures [data-timeline] > li').count());assert.deepEqual(tiers,[...tiers].sort((a,b)=>order.indexOf(a)-order.indexOf(b)));assert.equal(tiers[0],'INTEREST');
   assert.deepEqual(await rowKeys(page.locator('#news-disclosures')),api.filterRows(api.timeline({sec:SEC,news:NEWS}).slice(0,30),{channel:'ALL',category:'ALL',occurrence:'ALL',order:'IMPORTANCE'},{held:[],interests:['msft']}).map(key));
   assert.ok((await page.locator('#news-disclosures [data-importance-basis]').textContent()).includes('보유 정보 미연결'));
   assert.ok(await noOverflow(page),'overflow importance');await page.locator('#news-disclosures').screenshot({path:path.join(SHOTS,'news-importance-'+width+'.png')});
   await page.locator('#news-disclosures [data-news-filter-reset]').click();
   assert.equal(errors,0);assert.deepEqual(outside,[]);pass++;console.log('PASS news signals S07/S15 filters evidence '+width);
  }catch(e){fail++;console.log('FAIL news signals '+width+' '+phase+' '+(e.code==='ERR_ASSERTION'?'CONTRACT':'EXECUTION'));if(process.env.DEBUG_TEST)console.log(e);}finally{await context.close();}}}
 finally{await browser.close();}console.log('COUNTS pass='+pass+' fail='+fail);process.exitCode=fail?1:0;})();
