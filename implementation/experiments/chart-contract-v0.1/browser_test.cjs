const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const path=require('node:path');const fs=require('node:fs');
(async()=>{
 let launch={headless:true,args:['--no-sandbox']};
 if(process.env.CHART_CHROMIUM_MODULE){const binary=(await import(process.env.CHART_CHROMIUM_MODULE)).default;launch={headless:true,args:['--no-sandbox'],executablePath:await binary.executablePath()};}
 const browser=await chromium.launch(launch);
 const results=[];fs.mkdirSync('browser-results',{recursive:true});
 try{
  for(const width of [360,390,1280]){
   const page=await browser.newPage({viewport:{width,height:900}});const errors=[];
   page.on('pageerror',e=>errors.push(e.message));
   await page.goto('file://'+path.resolve(process.env.CHART_DEMO_FILE || 'dist/index.html'));
   await page.evaluate(()=>document.fonts.ready);
   await page.waitForFunction(()=>window.__chartLab?.candles.data().length===12);
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
   assert.equal(await page.evaluate(()=>__chartLab.volume.data().find(p=>p.time===__chartLab.rows[3].time)?.value),0);
   assert.equal(await page.evaluate(()=>__chartLab.volume.data().find(p=>p.time===__chartLab.rows[4].time)?.value),undefined);
   await page.locator('#chart').scrollIntoViewIfNeeded();
   for(const index of [0,3,4]){
    const point=await page.evaluate(i=>{const a=__chartLab;return {x:a.chart.timeScale().timeToCoordinate(a.rows[i].time),y:a.candles.priceToCoordinate(a.rows[i].close)};},index);
    const box=await page.locator('#chart').boundingBox();
    await page.mouse.move(box.x+point.x,box.y+point.y);
    await page.waitForFunction(i=>document.querySelector('#values').textContent.includes(new Date(__chartLab.rows[i].time*1000).toISOString().slice(0,10)),index);
    const value=await page.locator('#values').innerText();
    assert(value.includes(index===3?'V 0':index===4?'V 미제공':'O 100 · H 104 · L 98 · C 102 · V 1000'));
   }
   await page.locator('#all').click();
   await page.locator('#next').click();assert.match(await page.locator('#values').innerText(),/O 100 · H 104/);
   await page.locator('#chart').focus();await page.keyboard.press('ArrowRight');assert.match(await page.locator('#values').innerText(),/O 102 · H 105/);
   await page.locator('#previous').click();assert.match(await page.locator('#values').innerText(),/O 100 · H 104/);
   const downloadPromise=page.waitForEvent('download');await page.locator('#download').click();const download=await downloadPromise;
   const downloaded=JSON.parse(fs.readFileSync(await download.path(),'utf8'));assert.equal(downloaded.data_state,'DEMO');assert.equal(downloaded.points.length,12);
   await page.locator('#last').click();
   await page.waitForFunction(()=>Math.abs(__chartLab.chart.timeScale().getVisibleLogicalRange().from-7)<0.000001);
   assert.equal(await page.evaluate(()=>__chartLab.chart.timeScale().getVisibleLogicalRange().from),7);
   await page.locator('#empty').click();assert.equal(await page.evaluate(()=>__chartLab.candles.data().length),0);
   assert.match(await page.locator('#status').innerText(),/EMPTY/);assert.equal(await page.locator('#next').isDisabled(),true);assert.doesNotMatch(await page.locator('#values').innerText(),/O 100/);
   await page.locator('#blocked').click();assert.equal(await page.evaluate(()=>__chartLab.volume.data().length),0);
   assert.match(await page.locator('#status').innerText(),/BLOCKED/);assert.equal(await page.locator('#previous').isDisabled(),true);
   await page.locator('#all').click();
   assert.deepEqual(await page.evaluate(()=>__chartLab.candles.data().map(r=>[r.open,r.high,r.low,r.close])),await page.evaluate(()=>__chartLab.doc.points.map(r=>[r.open,r.high,r.low,r.close])));
   assert.deepEqual(errors,[]);
   await page.screenshot({path:`browser-results/${width}.png`,fullPage:true});
   results.push({width,result:'PASS',checks:['no-overflow','OHLC-exact','zero-vs-null-volume','crosshair-values','range','empty','blocked','restore','no-page-errors','keyboard-and-buttons','no-stale-values','contract-download']});
   await page.close();
  }
  fs.writeFileSync('browser-results/results.json',JSON.stringify({scope:'SYNTHETIC_DEMO_ONLY',results},null,2));console.log(JSON.stringify(results));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
