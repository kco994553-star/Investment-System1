'use strict';
const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {routeEmptyPublicScreens}=require('./empty_public_screens.js');const BASE=process.env.PAGES_COCKPIT_URL||'http://127.0.0.1:8990/';
(async()=>{const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_EXECUTABLE_PATH});let pass=0;
try{for(const width of [390,1280]){
 const context=await browser.newContext({viewport:{width,height:900},serviceWorkers:'block'});await routeEmptyPublicScreens(context);let external=0,frames=0,scripts=0,errors=0;
 await context.route('**/*',route=>{const request=route.request(),url=new URL(request.url());if(url.origin===new URL(BASE).origin)return route.fallback();
  if(request.resourceType()==='script')scripts++;if(url.origin==='https://www.tradingview-widget.com'){frames++;return route.fulfill({status:200,contentType:'text/html',body:'<html><body>display-only stub<script>parent.postMessage({price:123456789},"*")</script></body></html>'});}external++;return route.abort();});
 const page=await context.newPage();page.on('pageerror',()=>errors++);await page.goto(BASE+'#home');await page.locator('[data-tv-disabled]').waitFor();assert.equal(frames,0);assert.equal(external,0);
 assert.ok((await page.locator('[data-tv-toggle="on"]').textContent()).includes('종목명이 TradingView로 전달됩니다'));
 await page.locator('[data-tv-toggle="on"]').click();await page.locator('[data-tv-widget="ticker"] iframe').waitFor();await page.waitForFunction(()=>document.querySelector('[data-tv-widget="ticker"] iframe').contentDocument===null);
 assert.equal(await page.locator('script[src*="s3.tradingview.com"]').count(),0);assert.equal(scripts,0);
 assert.equal(await page.locator('[data-tv-unverified]').count(),1);assert.ok((await page.locator('[data-tv-unverified]').textContent()).includes('TSE:8035'));
 await page.goto(BASE+'#company/hanmi');await page.locator('[data-tv-widget="mini"] iframe').waitFor();assert.ok((await page.locator('[data-tv-unverified]').textContent()).includes('확인 불가'));
 const frame=page.locator('[data-tv-widget="mini"] iframe');assert.equal(await frame.evaluate(f=>f.contentDocument),null);assert.ok(decodeURIComponent(await frame.getAttribute('src')).includes('KRX:042700'));
 assert.equal(await page.evaluate(()=>JSON.stringify({...localStorage,...sessionStorage}).includes('123456789')),false);assert.equal(await page.locator('main').evaluate(n=>n.textContent.includes('123456789')),false);
 await page.locator('[data-tv-toggle="off"]').click();await page.locator('[data-tv-disabled]').waitFor();assert.equal(await page.locator('iframe[data-tv-iframe]').count(),0);assert.equal(await page.evaluate(()=>TradingViewWidgets.enabled(localStorage)),false);
 assert.equal(errors,0);assert.equal(external,0);assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
 const out=process.env.PAGES_COCKPIT_EVIDENCE_DIR;if(out){fs.mkdirSync(out,{recursive:true});await page.screenshot({path:path.join(out,'direct-tradingview-'+width+'.png')});}
 await context.close();pass++;
}console.log('TRADINGVIEW_DIRECT_BROWSER pass='+pass+' fail=0');}catch(e){console.log('TRADINGVIEW_DIRECT_BROWSER fail=1 '+e.stack);process.exitCode=1;}finally{await browser.close();}})();
