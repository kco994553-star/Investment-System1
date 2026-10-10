'use strict';
// Design canvas S01~S16 structure on the public build: flow numbers, QGV sub-categories,
// hub groups/legend, S14 MODEL/TARGET/ACTUAL separation, S08/S09/S10 headers. Empty device only.
const {chromium}=require('playwright'),assert=require('node:assert/strict');
const BASE=process.env.PAGES_COCKPIT_URL;
async function open(page,hash,selector){await page.goto(BASE+'#'+hash);await page.locator('main '+selector).first().waitFor();}
async function current(page){return page.locator('#primary-nav [data-nav-tab][aria-current="page"]').evaluateAll(n=>n.map(x=>x.dataset.navTab));}
(async()=>{const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_EXECUTABLE_PATH});let phase='START',pass=0,fail=0;
 try{for(const width of [390,1440]){const context=await browser.newContext({viewport:{width,height:900},serviceWorkers:'block'}),page=await context.newPage();page.setDefaultTimeout(15000);let errors=0;page.on('pageerror',()=>errors++);
  try{
   phase='S01';await open(page,'home','[data-integrated-judgement]');
   assert.ok((await page.locator('[data-integrated-judgement]').textContent()).includes('매수·매도 지시 아님'));
   assert.equal(await page.locator('[data-system-flow] .flow-number').count(),4);
   await page.waitForFunction(()=>document.querySelector('#home-target-version')?.textContent!=='—');
   assert.deepEqual(await current(page),['home']);
   phase='S02';await open(page,'qgv','[data-hub="qgv"]');
   assert.equal(await page.locator('.flow-step[data-flow-step="1"]').count(),1);
   assert.deepEqual(await page.locator('[data-hub="qgv"] .hub-group h2').allTextContents(),['내 투자','종목 찾기','시장 정보','성과']);
   assert.equal(await page.locator('[data-hub-legend] [data-feature-status]').count(),4);
   assert.equal(await page.locator('[data-hub="qgv"] a[href="#model"]').count(),1);
   assert.deepEqual(await current(page),['qgv']);
   phase='S14';await open(page,'model','[data-model-table]');await page.locator('[data-model-row]').first().waitFor();
   const rows=await page.locator('[data-model-row]').evaluateAll(r=>r.map(x=>[...x.cells].map(c=>c.textContent)));
   assert.equal(rows.length,19);
   for(const r of rows){assert.equal(r[1],'—');assert.equal(r[4],'—');assert.match(r[2],/^\d+(\.\d+)?%$|^—$/);assert.notEqual(r[3],'0');}
   assert.equal(await page.locator('[data-model-row] [data-na="NOT_AVAILABLE"]').count(),38);
   assert.equal(await page.locator('.parent-row [data-sub-category]').textContent(),'내 투자');
   assert.deepEqual(await current(page),['qgv']);
   phase='SUBCATEGORY';await open(page,'watchlist','h1');assert.equal(await page.locator('[data-sub-category]').textContent(),'종목 찾기');
   await open(page,'thirteenf','h1');assert.equal(await page.locator('[data-sub-category]').textContent(),'시장 정보');
   phase='S08';await open(page,'technical','[data-ia-screen="technical"]');
   assert.equal(await page.locator('.flow-step[data-flow-step="2"]').count(),1);
   assert.deepEqual(await page.locator('[data-screen-tab]').evaluateAll(n=>n.map(x=>x.dataset.screenTab)),['chart','state','execution','record']);
   assert.ok((await page.locator('#technical-execution').textContent()).includes('NOT_AVAILABLE'));
   phase='S09';await open(page,'macro','[data-macro-status]');
   assert.equal(await page.locator('.flow-step[data-flow-step="3"]').count(),1);
   assert.equal(await page.locator('[data-macro-regime]').textContent(),'자료 없음');
   phase='S10';await open(page,'validation','[data-hub="validation"]');
   assert.equal(await page.locator('.flow-step[data-flow-step="4"]').count(),1);
   assert.equal(await page.locator('[data-screen-tab]').count(),6);
   assert.ok((await page.locator('main .data-badges').textContent()).includes('UNCONFIRMED'));
   await open(page,'validation-backtest','#validation-backtest');assert.deepEqual(await current(page),['validation']);
   phase='LAYOUT';for(const hash of ['home','qgv','model','technical','macro','validation']){await open(page,hash,'h1');assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'no horizontal scroll '+hash);}
   if(width>=1024)assert.ok(await page.locator('.nav-device-note').isVisible());else assert.equal(await page.locator('.nav-device-note').isVisible(),false);
   assert.equal(errors,0);pass++;console.log('PASS design canvas S01~S16 structure '+width);
  }catch(e){fail++;console.log('FAIL design canvas '+width+' '+phase+' '+(e.code==='ERR_ASSERTION'?'CONTRACT':'EXECUTION'));}
  finally{await context.close();}}}
 finally{await browser.close();}
 console.log('COUNTS pass='+pass+' fail='+fail);process.exitCode=fail?1:0;})();
