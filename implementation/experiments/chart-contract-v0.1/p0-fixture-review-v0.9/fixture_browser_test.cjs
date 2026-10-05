// Existing SAMPLE renderer regression, not production admission or authoritative input.
const {chromium}=require('../node_modules/playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const lab=path.resolve(__dirname,'..');
const output=path.resolve(process.env.CHART_REVIEW_OUTPUT||path.join(lab,'browser-results/v0.9'));
const baseline=process.argv.includes('--baseline');
const edgesOnly=process.argv.includes('--review-edges');
(async()=>{
 const {renderPortfolioInput}=await import('../portfolio_contract.mjs');
 const noCatalogSource=JSON.parse(fs.readFileSync(path.join(lab,'portfolio_reference.json'),'utf8'));noCatalogSource.type_catalog=[];
 const noCatalog=renderPortfolioInput(noCatalogSource);
 fs.mkdirSync(output,{recursive:true});
 let launch={headless:true,args:['--no-sandbox']};
 if(process.env.CHART_CHROMIUM_MODULE){const binary=(await import(process.env.CHART_CHROMIUM_MODULE)).default;launch.executablePath=await binary.executablePath();}
 const browser=await chromium.launch(launch);const results=[];
 try{
  for(const width of baseline||edgesOnly?[1280]:[360,390,1280]){
   const page=await browser.newPage({viewport:{width,height:900}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
   await page.goto('file://'+path.join(lab,'dist/index.html'));await page.evaluate(()=>document.fonts.ready);
   const ref=await page.evaluate(()=>__portfolioLab.doc);
   assert(ref.types.exposures.every(e=>e.member_units===0&&e.unknown_units===ref.total_units));
   if(baseline){
    const text=await page.locator('#portfolio-charts').innerText();
    await page.locator('#portfolio').screenshot({path:path.join(output,'baseline-1280.png')});
    fs.writeFileSync(path.join(output,'baseline.json'),JSON.stringify({input:'REFERENCE_TARGET',unknown_units:ref.total_units,displayed_false_zero:/확인된 유형 노출:.*0%/.test(text),text},null,2));
    assert.doesNotMatch(text,/확인된 유형 노출:.*0%/,'all missing memberships must not display measured zero exposure');
    continue;
   }
   if(edgesOnly){
    await page.evaluate(d=>{PORTFOLIO_CHARTS.no_catalog=d;__portfolioLab.render('no_catalog');},noCatalog);
    assert.equal(await page.locator('[data-dimension="INVESTMENT_TYPE"]').getAttribute('data-availability'),'NOT_AVAILABLE','empty catalog does not certify type exposure');
    assert.equal(await page.locator('[data-dimension="TYPE_OVERLAP"]').getAttribute('data-availability'),'NOT_AVAILABLE','UNKNOWN partition does not certify overlap');
    continue;
   }
   const dims=await page.locator('section[data-dimension]').evaluateAll(es=>es.map(e=>e.dataset.dimension));
   assert.deepEqual(dims,['GICS','STRATEGY_THEME','INVESTMENT_TYPE','TYPE_OVERLAP']);
   const types=page.locator('[data-dimension="INVESTMENT_TYPE"]');
   assert.match(await types.innerText(),/NOT_AVAILABLE/);assert.doesNotMatch(await types.innerText(),/확인된 유형 노출:.*0%/);
   assert((await types.locator('svg text').allTextContents()).every(t=>!/0%/.test(t)));
   assert.match(await page.locator('#portfolio-state').innerText(),/SAMPLE.*TARGET/);
   assert.match(await page.locator('#portfolio-meta').innerText(),/10000/);
   assert.match(await page.locator('#portfolio-meta').innerText(),/effective_at.*NOT_AVAILABLE/);
   assert.match(await page.locator('#portfolio-meta').innerText(),/available_at.*NOT_AVAILABLE/);
   assert.match(await page.locator('#portfolio-meta').innerText(),new RegExp(ref.as_of.replaceAll('.','\\.')));
   assert.match(await page.locator('[data-dimension="GICS"]').innerText(),/NOT_AVAILABLE/);
   assert.equal(await page.locator('[data-dimension="GICS"] svg').count(),0);
   assert.match(await page.locator('[data-dimension="STRATEGY_THEME"]').innerText(),/Strategy Theme/);
   const groups=ref.industry.buckets.filter(b=>b.kind==='INDUSTRY');assert.equal(groups.reduce((n,b)=>n+b.units,0),10000);
   await page.locator('#portfolio').screenshot({path:path.join(output,`reference-${width}.png`)});
   await page.locator('#portfolio-actual').click();
   assert.match(await page.locator('#portfolio-state').innerText(),/ACTUAL.*NOT_AVAILABLE/);
   assert.equal(await page.locator('#portfolio-charts svg').count(),0);assert.equal(await page.evaluate(()=>__portfolioLab.doc),null);
   await page.locator('#portfolio-reference').click();assert.equal(await page.evaluate(()=>__portfolioLab.doc.weight_basis),'TARGET');
   await page.locator('#portfolio-demo').click();const demo=await page.evaluate(()=>__portfolioLab.doc);
   assert.match(await page.locator('#portfolio-state').innerText(),/SAMPLE/);
   assert.equal(demo.types.exposures.reduce((n,e)=>n+e.member_units,0),105);
   assert.match(await page.locator('[data-dimension="INVESTMENT_TYPE"]').innerText(),/Growth 65% 하한\(최소\) \/ Quality 40% 하한\(최소\)/);
   assert.equal(demo.overlap.buckets.reduce((n,b)=>n+b.units,0),100);
   assert.match(await page.locator('[data-dimension="TYPE_OVERLAP"]').innerText(),/\[Growth\] \+ \[Quality\]/);
   assert.equal(await page.locator('[data-dimension="STRATEGY_THEME"] svg').count(),0);
   await page.locator('#portfolio').screenshot({path:path.join(output,`demo-${width}.png`)});
   // UI projection fixtures: explicitly known zero and partial lower bound.
   await page.evaluate(()=>{const d=structuredClone(PORTFOLIO_CHARTS.reference);d.types.exposures=d.types.exposures.map(e=>({...e,member_units:0,non_member_units:d.total_units,unknown_units:0,cash_units:0}));PORTFOLIO_CHARTS.ui_probe=d;__portfolioLab.render('ui_probe');});
   assert.match(await types.innerText(),/0%/);assert.doesNotMatch(await types.innerText(),/NOT_AVAILABLE/);
   await page.evaluate(()=>{const d=structuredClone(PORTFOLIO_CHARTS.reference);d.types.exposures=d.types.exposures.map(e=>({...e,member_units:1000,non_member_units:2000,unknown_units:6000,cash_units:1000}));PORTFOLIO_CHARTS.ui_probe=d;__portfolioLab.render('ui_probe');});
   assert.match(await types.innerText(),/최소.*10%|10%.*최소/);assert.match(await types.innerText(),/60%/);
   await page.evaluate(d=>{PORTFOLIO_CHARTS.no_catalog=d;__portfolioLab.render('no_catalog');},noCatalog);
   assert.equal(await types.getAttribute('data-availability'),'NOT_AVAILABLE');
   assert.equal(await page.locator('[data-dimension="TYPE_OVERLAP"]').getAttribute('data-availability'),'NOT_AVAILABLE');
   for(const invalid of ['null-member','null-denominator','actual-in-target','malformed-overlap']){
    await page.evaluate(kind=>{const d=structuredClone(PORTFOLIO_CHARTS.reference);if(kind==='null-member')d.types.exposures[0].member_units=null;else if(kind==='null-denominator')d.total_units=null;else if(kind==='malformed-overlap')d.overlap.buckets[0].types=null;else d.weight_basis='ACTUAL';PORTFOLIO_CHARTS.invalid_probe=d;__portfolioLab.render('invalid_probe');},invalid);
    assert.match(await page.locator('#portfolio-state').innerText(),/BLOCKED/);assert.equal(await page.locator('#portfolio-charts svg').count(),0);assert.equal(await page.evaluate(()=>__portfolioLab.doc),null);
   }
   await page.evaluate(()=>{PORTFOLIO_CHARTS.demo.data_state='NOT_AVAILABLE';__portfolioLab.render('demo');});
   assert.match(await page.locator('#portfolio-state').innerText(),/BLOCKED/);assert.equal(await page.locator('#portfolio-charts svg').count(),0);
   assert.equal(await page.evaluate(()=>__portfolioLab.doc),null);assert.deepEqual(errors,[]);
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
   results.push({width,result:'PASS',checks:['four-distinct-dimensions','missing-is-not-zero','sample-target-label','time-unit-denominator','GICS-unavailable','reference-theme-exact-100','actual-denied-clears-target','fictional-overlap-105-vs-partition-100','known-zero-and-partial-lower-bound','null-and-wrong-basis-denied','ineligible-denied-no-stale-svg','no-overflow','no-page-errors']});
   await page.close();
  }
  fs.writeFileSync(path.join(output,'results.json'),JSON.stringify({scope:'SAMPLE_ONLY',production_admission:false,results},null,2));console.log(JSON.stringify(results));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
