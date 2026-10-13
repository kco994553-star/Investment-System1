'use strict';
const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {routeEmptyPublicScreens}=require('./empty_public_screens.js');
const BASE=process.env.PAGES_COCKPIT_URL||'http://127.0.0.1:8990/';
const PNG='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==';
(async()=>{const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_EXECUTABLE_PATH});let pass=0;
try{for(const width of [390,1280]){
 const context=await browser.newContext({viewport:{width,height:900},serviceWorkers:'block'});await routeEmptyPublicScreens(context);let external=0,errors=0;
 await context.route('**/*',route=>{if(new URL(route.request().url()).origin===new URL(BASE).origin)return route.fallback();external++;return route.abort();});
 await context.route('**/company-logos.json',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({schema:'company-logos/1',rows:[['NASDAQ:NVDA',PNG,'WIKIDATA']]})}));
 const page=await context.newPage();page.on('pageerror',()=>errors++);await page.goto(BASE+'#home');await page.locator('#global-search').fill('NVDA');
 await page.locator('#global-results .co-logo[data-logo-state="img"]').first().waitFor();
 assert.ok((await page.locator('#global-results .co-logo img').first().getAttribute('src')).startsWith('data:image/png;base64,'));
 await page.locator('#global-search').fill('AMD');await page.locator('#global-results .co-logo[data-logo-state="letter"]').first().waitFor();
 assert.equal(await page.locator('#global-results .co-logo').first().getAttribute('data-letter'),'A');
 await page.goto(BASE+'#company/nvda');await page.locator('h1 .co-logo[data-logo-state="img"]').waitFor();
 await page.goto(BASE+'#leaderboard');await page.locator('[data-leaderboard-row="nvda"] .co-logo[data-logo-state="img"]').waitFor();
 await page.goto(BASE+'#settings');await page.locator('[data-logo-setting="display"]').uncheck();
 await page.goto(BASE+'#company/nvda');await page.locator('h1 .co-logo[data-logo-state="letter"]').waitFor();
 assert.equal(external,0);assert.equal(errors,0);assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
 const out=process.env.PAGES_COCKPIT_EVIDENCE_DIR;if(out){fs.mkdirSync(out,{recursive:true});await page.screenshot({path:path.join(out,'local-logos-'+width+'.png')});}
 await context.close();pass++;
}console.log('COMPANY_LOGOS_BROWSER pass='+pass+' fail=0');}catch(e){console.log('COMPANY_LOGOS_BROWSER fail=1 '+e.message);process.exitCode=1;}finally{await browser.close();}})();
