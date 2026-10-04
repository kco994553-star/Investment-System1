const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
(async()=>{
 let launch={headless:true,args:['--no-sandbox']};
 if(process.env.CHART_CHROMIUM_MODULE){const binary=(await import(process.env.CHART_CHROMIUM_MODULE)).default;launch.executablePath=await binary.executablePath();}
 const browser=await chromium.launch(launch);const results=[];fs.mkdirSync('browser-results',{recursive:true});
 try{
  for(const width of [360,390,1280]){
   const page=await browser.newPage({viewport:{width,height:900}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
   await page.goto('file://'+path.resolve(process.env.CHART_DEMO_FILE||'dist/index.html'));await page.evaluate(()=>document.fonts.ready);
   const ref=await page.evaluate(()=>__portfolioLab.doc);
   assert.equal(ref.data_state,'REFERENCE');assert.equal(ref.weight_basis,'TARGET');assert.equal(ref.holdings.length,19);
   assert.deepEqual(ref.industry.buckets.filter(b=>b.kind==='INDUSTRY').map(b=>b.units).sort((a,b)=>a-b),[2000,2500,2500,3000]);
   assert(ref.holdings.every(h=>h.types===null&&h.security_id===null));
   assert.match(await page.locator('#portfolio-state').innerText(),/실제 계좌 아님/);
   assert.match(await page.locator('#portfolio-charts').innerText(),/기업별 유형 배정 근거가 없어/);
   await page.locator('#portfolio-demo').click();const demo=await page.evaluate(()=>__portfolioLab.doc);
   assert.equal(demo.data_state,'DEMO');assert.equal(demo.types.exposures.reduce((n,e)=>n+e.member_units,0),105);
   assert(demo.types.exposures.every(e=>e.member_units+e.non_member_units+e.unknown_units+e.cash_units===100));
   assert.equal(demo.overlap.buckets.reduce((n,b)=>n+b.units,0),100);
   assert.match(await page.locator('#portfolio-charts').innerText(),/Growth 65% \/ Quality 40%/);
   assert.match(await page.locator('#portfolio-charts').innerText(),/\[Growth\] \+ \[Quality\]/);
   assert.match(await page.locator('#portfolio-state').innerText(),/가상 기업/);
   assert.equal(await page.locator('#portfolio-charts svg[role="img"]').count(),3);
   await page.locator('#portfolio').screenshot({path:`browser-results/portfolio-${width}.png`});
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
   assert.equal(await page.locator('.inventory-row').count(),113);
   await page.locator('#inventory-search').fill('RSI');assert.equal(await page.locator('.inventory-row').count(),1);
   await page.locator('.inventory-row summary').click();assert.match(await page.locator('.inventory-row').innerText(),/L1 원본/);
   await page.locator('#inventory-search').fill('');await page.locator('#inventory-group').selectOption('K');assert.equal(await page.locator('.inventory-row').count(),8);
   await page.locator('#inventory-group').selectOption('');assert.equal(await page.locator('.inventory-row').count(),113);
   await page.locator('#portfolio-reference').click();assert.equal(await page.evaluate(()=>__portfolioLab.mode),'reference');
   // A serialized observed-data payload cannot acquire display eligibility by a mode switch.
   await page.evaluate(()=>{PORTFOLIO_CHARTS.demo.data_state='NOT_AVAILABLE';__portfolioLab.render('demo');});
   assert.match(await page.locator('#portfolio-charts').innerText(),/BLOCKED/);assert.equal(await page.locator('#portfolio-charts svg').count(),0);assert.match(await page.locator('#portfolio-state').innerText(),/BLOCKED/);assert.equal(await page.evaluate(()=>__portfolioLab.doc),null);
   assert.deepEqual(errors,[]);results.push({width,result:'PASS',checks:['reference-19-exact-groups','no-inferred-types-or-security','fictional-105-percent','unknown-cash-denominator','exact-set-partition','three-SVGs','scope-labels','inventory-113-search-filter','reference-restore','observed-blocked','no-overflow','no-page-errors']});await page.close();
  }
  fs.writeFileSync('browser-results/portfolio-results.json',JSON.stringify({scope:'REFERENCE_TARGET_AND_FICTIONAL_PORTFOLIO',results},null,2));console.log(JSON.stringify(results));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
