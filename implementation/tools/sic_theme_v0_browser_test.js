'use strict';
// SIC industry group v0 + theme v0 (2026-10-11 user decision) on S04/S03.
// Phase A: published build (offline company-classification.json, all NOT_AVAILABLE).
// Phase B: Python-generated synthetic classification payload served by route interception, plus ACTUAL holdings
// entered on a throw-away context; the concentration warning is computed in RAM and never stored.
const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const BASE=process.env.PAGES_COCKPIT_URL;
const fixture=JSON.parse(fs.readFileSync(path.join(__dirname,'..','tests/fixtures/company_classification_v0_payloads.json'),'utf8')).live;
async function open(page,hash,selector){await page.goto(BASE+'#'+hash);await page.locator('main '+selector).first().waitFor();}
const text=async(page,selector)=>(await page.locator(selector).first().textContent()).replace(/\s+/g,' ').trim();
async function noScroll(page,label){assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'no horizontal scroll '+label);}
(async()=>{const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_EXECUTABLE_PATH});let phase='START',pass=0,fail=0;
 try{for(const width of [390,1440]){
  {const context=await browser.newContext({viewport:{width,height:900},serviceWorkers:'block'}),page=await context.newPage();page.setDefaultTimeout(15000);let errors=0;page.on('pageerror',()=>errors++);
   try{
    phase='A-FILE';const r=await page.request.get(BASE+'company-classification.json');assert.equal(r.status(),200);const body=await r.json();assert.equal(body.state,'NOT_AVAILABLE');assert.equal(body.kind,'COMPANY_CLASSIFICATION');
    phase='A-S04';await open(page,'company/nvda','[data-company-card="classification"]');
    await page.waitForFunction(()=>document.querySelector('[data-axis="industry"] [data-v0-marker]'));
    assert.ok((await text(page,'[data-axis="industry"]')).includes('NOT_AVAILABLE'));assert.ok((await text(page,'[data-axis="theme"]')).includes('NOT_AVAILABLE'));
    assert.ok((await text(page,'[data-axis="industry"] [data-v0-marker]')).includes('v0 기본값 · UNCALIBRATED · 나중에 수정 가능'));
    phase='A-S03';await open(page,'portfolio','[data-concentration]');assert.ok((await text(page,'[data-concentration]')).includes('NOT_AVAILABLE'));
    assert.equal(await page.locator('[data-concentration-warning]').count(),0);assert.ok((await text(page,'[data-concentration] [data-v0-marker]')).includes('UNCALIBRATED'));
    assert.equal(errors,0);pass++;console.log('PASS sic/theme v0 published build '+width);
   }catch(e){fail++;console.log('FAIL sic/theme v0 published build '+width+' '+phase+' '+String(e.message).split('\n')[0]);}finally{await context.close();}}
  {const context=await browser.newContext({viewport:{width,height:900},serviceWorkers:'block'});
   await context.route('**/company-classification.json',r=>r.fulfill({status:200,contentType:'application/json',body:JSON.stringify(fixture)}));
   const page=await context.newPage();page.setDefaultTimeout(15000);let errors=0;page.on('pageerror',()=>errors++);
   try{
    phase='B-S04';await open(page,'company/nvda','[data-company-card="classification"]');await page.locator('[data-industry-chip]').waitFor();
    assert.equal(await text(page,'[data-industry-chip]'),'제조·산업·기술 · 반도체');assert.equal(await text(page,'[data-axis="industry"] [data-sic]'),'SIC 3674');
    assert.deepEqual(await page.locator('[data-axis="theme"] [data-theme-chip]').evaluateAll(n=>n.map(x=>x.dataset.themeChip)),['ai','semiconductors','datacenter_reits']);
    assert.ok((await text(page,'[data-theme-chip="semiconductors"] [data-theme-evidence]')).includes('ETF SOXX·SMH + 10-K 키워드'));
    assert.ok((await text(page,'[data-axis="theme"] [data-v0-marker]')).includes('나중에 수정 가능'));
    await open(page,'company/msft','[data-company-card="classification"]');await page.locator('[data-weak-evidence="consumer_brands"]').waitFor();assert.equal(await text(page,'[data-weak-evidence="consumer_brands"]'),'근거 약함');
    await open(page,'company/gev','[data-company-card="classification"]');assert.ok((await text(page,'[data-axis="industry"]')).includes('NOT_AVAILABLE'));
    await noScroll(page,'S04 v0');
    phase='B-ACTUAL';await open(page,'actual','[data-security-index="4"]');
    const fill=async(index,quantity,average,price)=>{const row=page.locator('[data-security-index="'+index+'"]');await row.locator('[data-field="quantity"]').fill(quantity);await row.locator('[data-field="average_cost"]').fill(average);await row.locator('[data-field="price"]').fill(price);};
    await fill(4,'10','1000','3000');await fill(5,'1','100','100');await page.locator('[data-fx-currency="USD"] [data-field="rate"]').fill('1000');
    await page.locator('[data-action="save"]').click();await page.locator('[data-market-total]').filter({hasText:'130'}).waitFor();
    phase='B-S03';await open(page,'portfolio','[data-portfolio-card="themes"]');
    await page.waitForFunction(()=>document.querySelector('[data-concentration-warning="semiconductors"]'));
    const warn=await text(page,'[data-concentration-scope="strategy"] [data-concentration-warning="semiconductors"]');assert.ok(/^쏠림 경고 · 반도체 76\.9% > 40% · v0 기본값$/.test(warn),warn);
    assert.equal(await page.locator('[data-concentration-scope="strategy"] [data-concentration-warning="ai"]').count(),1);
    assert.equal(await page.locator('[data-concentration-scope="target"] [data-concentration-warning="ai_semi"]').count(),1);
    assert.equal(await page.locator('[data-concentration-scope="target"] [data-concentration-warning="semi_equipment"]').count(),0);
    assert.ok((await text(page,'[data-concentration]')).includes('v0 기본값 · UNCALIBRATED · 나중에 수정 가능'));
    assert.ok((await text(page,'[data-portfolio-card="industry"] [data-industry="manufacturing_industrial_tech"]')).includes('76.9%'));
    assert.ok((await text(page,'[data-portfolio-card="industry"] [data-industry="nodata"]')).includes('23.1%'));
    await noScroll(page,'S03 v0');
    phase='B-NO-LEAK';assert.equal(/concentration|company-classification|semiconductors|weight/.test(await page.evaluate(()=>JSON.stringify({...localStorage,...sessionStorage}))),false);
    phase='B-EN';await page.evaluate(()=>localStorage.setItem(AppLanguage.KEY,JSON.stringify({version:1,display_locale:'en-US',source_language:'all'})));await page.reload();
    await open(page,'portfolio','[data-portfolio-card="themes"]');await page.waitForFunction(()=>document.querySelector('[data-concentration-warning="semiconductors"]'));
    assert.ok((await text(page,'[data-concentration-warning="semiconductors"]')).includes('Concentration warning · Semiconductors'));
    await open(page,'company/nvda','[data-industry-chip]');assert.equal(await text(page,'[data-industry-chip]'),'Manufacturing / industrial / technology · Semiconductors');
    assert.equal(errors,0);pass++;console.log('PASS sic/theme v0 with data '+width);
   }catch(e){fail++;console.log('FAIL sic/theme v0 with data '+width+' '+phase+' '+String(e.message).split('\n')[0]);}finally{await context.close();}}
 }}finally{await browser.close();}
 console.log('COUNTS pass='+pass+' fail='+fail);process.exitCode=fail?1:0;})();
