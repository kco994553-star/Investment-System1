'use strict';
// Existing implemented controls must be reachable from their menu, without requesting private prices.
const assert=require('node:assert/strict'),{chromium}=require('playwright');
const {displayOnlyOff}=require('./display_only_off.js');
const BASE=process.env.PAGES_COCKPIT_URL;
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_EXECUTABLE_PATH});let checks=0;
 try{for(const width of [390,1280])for(const theme of ['light','dark']){
  const ctx=await browser.newContext({viewport:{width,height:900},colorScheme:theme,serviceWorkers:'block'}),page=await ctx.newPage(),outside=[],errors=[];
  await displayOnlyOff(ctx);page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/*',r=>{if(new URL(r.request().url()).origin===new URL(BASE).origin)return r.continue();outside.push(r.request().url());return r.abort();});
  const go=async hash=>{await page.goto(BASE+hash,{waitUntil:'domcontentloaded'});await page.waitForFunction(()=>!!document.querySelector('#content h1'));};
  const focused=async selector=>{await page.waitForFunction(s=>{const n=document.querySelector(s);return n&&(n===document.activeElement||n.contains(document.activeElement));},selector);
   assert.equal(await page.locator(selector).evaluate(n=>n===document.activeElement||n.contains(document.activeElement)),true,selector+' receives focus');};
  await go('#technical-pattern/nvda');await page.locator('[data-pattern-panel]').waitFor();await focused('[data-pattern-panel]');
  assert.equal(await page.locator('html').getAttribute('data-theme'),theme);
  assert.equal(await page.locator('[data-technical-symbol]').inputValue(),'nvda');checks++;
  await page.locator('[data-cw-synthetic]').click();
  await page.waitForFunction(()=>document.querySelector('[data-chart-workbench]').dataset.source==='synthetic');
  const chartBefore=await page.locator('[data-chart-workbench]').evaluate(n=>({source:n.dataset.source,bars:n.dataset.barCount,id:n.querySelector('[data-pattern-panel]').getAttribute('aria-labelledby')}));
  const notes=page.locator('[data-ia-sub="technical"] a[data-ia-sec="2.3"]');
  assert.equal(await notes.getAttribute('href'),'#technical-notes/nvda');await notes.click();
  await focused('[data-user-panel]');assert.equal(await page.locator('[data-technical-symbol]').inputValue(),'nvda');checks++;
  assert.deepEqual(await page.locator('[data-chart-workbench]').evaluate(n=>({source:n.dataset.source,bars:n.dataset.barCount,id:n.querySelector('[data-pattern-panel]').getAttribute('aria-labelledby')})),chartBefore,'same-company section navigation keeps the existing chart and results in RAM');checks++;
  await page.locator('[data-ia-sub="technical"] a[data-ia-sec="2.1"]').click();await focused('#technical-chart');
  assert.deepEqual(await page.locator('[data-chart-workbench]').evaluate(n=>({source:n.dataset.source,bars:n.dataset.barCount,id:n.querySelector('[data-pattern-panel]').getAttribute('aria-labelledby')})),chartBefore,'returning to the same-company indicator section keeps the mounted chart');checks++;
  await page.locator('[data-ia-sub="technical"] a[data-ia-sec="2.3"]').click();await focused('[data-user-panel]');
  await page.locator('[data-technical-symbol]').selectOption('msft');
  await page.locator('[data-ia-sub="technical"] a[data-ia-sec="2.2"]').click();
  await focused('[data-pattern-panel]');assert.equal(await page.locator('[data-technical-symbol]').inputValue(),'msft');checks++;
  await go('#macro-industry');await page.locator('[data-cycle-tab="industry"]').waitFor();
  assert.equal(await page.locator('[data-cycle-tab="industry"]').getAttribute('aria-selected'),'true');await focused('[data-cycle-ring="industry"]');checks++;
  assert.equal(await page.locator('#macro-cycle [data-macro-evidence]').count(),1,'evidence belongs inside the position area');
  await page.locator('[data-ia-sub="macro"] a[data-ia-sec="3.4"]').click();
  await focused('[data-cycle-ring]:not([hidden]) [data-cycle-user-box]');checks++;
  await page.locator('[data-ia-sub="macro"] a[data-ia-sec="3.1"]').click();await focused('#macro-cycle');
  assert.equal(await page.locator('[data-cycle-ring="economy"]').isVisible(),true,'economy/market section leaves the industry cycle');
  assert.equal(await page.locator('[data-me-tab="economy"]').getAttribute('aria-selected'),'true');checks++;
  await go('#validation-forward');await page.locator('#plab-92').waitFor();await focused('#plab-92');
  assert.equal(await page.locator('[data-fn-group="9.2"] #forward-validation-root').count(),1,'forward ledger remains in the selected forward-validation section');checks++;
  await go('#validation-backtest');await focused('#plab-91');checks++;
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),true);
  assert.deepEqual(errors,[]);assert.deepEqual(outside,[]);await ctx.close();
 }}finally{await browser.close();}
 console.log('IMPLEMENTED_NAVIGATION_BROWSER_OK checks='+checks);
})().catch(e=>{console.error('IMPLEMENTED_NAVIGATION_BROWSER_FAIL',e.stack);process.exit(1);});
