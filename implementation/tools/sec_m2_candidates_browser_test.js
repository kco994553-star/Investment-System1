"use strict";
// Locally generated synthetic test evidence only. Never capture private device data.
const {chromium}=require('playwright');
const fs=require('node:fs');
const base=process.env.M2_BROWSER_URL || 'http://127.0.0.1:8992/';
const out=process.env.M2_BROWSER_EVIDENCE || '/tmp/m2-browser-evidence';
const checks=[];
let phase="launch";
const must=(v,label)=>{if(!v){const e=Error(label);e.safeReason=label;throw e;}};
(async()=>{
 fs.mkdirSync(out,{recursive:true});
 const launch={headless:true};
 if(process.env.WEB_TEST_CHROMIUM_PATH)launch.executablePath=process.env.WEB_TEST_CHROMIUM_PATH;
 const browser=await chromium.launch(launch);
 try {
 for(const width of [390,1280])for(const locale of ['ko-KR','en-US']){
  const context=await browser.newContext({viewport:{width,height:900},locale});
  await context.route('**/*',route=>new URL(route.request().url()).origin===new URL(base).origin?route.continue():route.abort());
  const page=await context.newPage();let errors=0;page.on('pageerror',()=>errors++);
  phase='settings';await page.goto(base+'candidate/#settings');
  await page.locator('#display-locale').selectOption(locale);
  await page.goto(base+'candidate/#leaderboard');
  phase='candidate-panel';const panel=page.locator('[data-m2-candidates]');await panel.waitFor();
  must(await panel.locator('[data-m2-company]').count()===3,'candidate row count');
  must((await panel.textContent()).includes(locale==='ko-KR'?'보정 전·가격 미포함':'Uncalibrated · No prices'),'badge');
  must((await panel.textContent()).includes('SYNTHETIC'),'synthetic disclosure');
  must(await panel.locator('[data-m2-company="asml"] [data-score="Q"]').textContent()==='0','zero preserved');
  must(await panel.locator('[data-m2-company="stry"] [data-score="Q"]').textContent()==='NOT_AVAILABLE','missing preserved');
  phase='asml-route';await panel.locator('a[href="#company/asml"]').click();
  await page.waitForFunction(()=>document.querySelector('h1')?.textContent==='ASML');
  must(await page.locator('[data-score="V"]').textContent()==='NOT_AVAILABLE','V unavailable');
  must((await page.locator('[data-m2-candidates]').textContent()).includes('ASML'),'ASML exact route');
  phase='stry-route';await page.goto(base+'candidate/#company/stry');await page.locator('[data-m2-company="stry"]').waitFor();
  must((await page.locator('h1').textContent()).includes('SYK'),'stry registry ticker');
  if(width===1280&&locale==='en-US')await page.screenshot({path:out+'/detail-1280-en-US.png',fullPage:true});
  await page.goto(base+'candidate/#company/SYK');await page.waitForTimeout(100);
  must(await page.locator('[data-m2-company]').count()===0,'no ticker alias guessing');
  for(const id of ['toString','__proto__','constructor']) {
    await page.goto(base+'candidate/#company/'+id);
    await page.waitForFunction(()=>document.querySelector('h1')?.textContent?.includes('찾을 수 없습니다')||document.querySelector('h1')?.textContent?.includes('not found'));
    must(await page.locator('[data-m2-company]').count()===0,'prototype ID rejected');
  }
  await page.goto(base+'candidate/#leaderboard');await page.locator('[data-m2-company="asml"]').waitFor();
  must(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'no horizontal overflow');
  await page.screenshot({path:`${out}/candidate-${width}-${locale}.png`,fullPage:true});
  await page.goto(base+'default/#leaderboard');await page.locator('[data-m2-candidates]').waitFor();
  must(await page.locator('[data-m2-company]').count()===0,'default no sample scores');
  must((await page.locator('[data-m2-candidates]').textContent()).includes('NOT_AVAILABLE'),'default unavailable');
  for(const id of ['toString','__proto__']) {
    await page.goto(base+'default/#company/'+id);
    await page.waitForFunction(()=>document.querySelector('h1')?.textContent?.includes('찾을 수 없습니다')||document.querySelector('h1')?.textContent?.includes('not found'));
    must(await page.locator('[data-m2-company]').count()===0,'default prototype ID rejected');
  }
  await page.goto(base+'candidate/#leaderboard');await page.locator('[data-m2-company="asml"]').waitFor();
  must(await page.evaluate(()=>{
    const changes=[v=>v.prices_used=true,v=>v.companies.asml.V_score=0,v=>v.companies.asml.Q_score=NaN,v=>v.companies.asml.extra='INVENTED_CANARY',v=>v.companies.asml.ticker='wrong'];
    return changes.every(change=>{const v=structuredClone(m2Candidates);change(v);return Object.keys(guardM2Candidates(v).companies).length===0;}) && !JSON.stringify(researchPublicContext()).includes('sec_m2_');
  }),'runtime malformed candidates and prompt exclusion');
  await page.goto(base+'candidate/#actual');await page.locator('#device-actual-root').waitFor();
  must(await page.locator('[data-m2-company]').count()===0,'candidate independent of ACTUAL');
  must(errors===0,'browser errors');
  checks.push({width,locale,status:'PASS'});await context.close();
 }
 }finally{await browser.close();}
 fs.writeFileSync(out+'/checks.json',JSON.stringify({checks},null,2));
 console.log(JSON.stringify({checks}));
})().catch(e=>{fs.writeFileSync(out+'/failure.txt',String(e.stack));console.error('M2_BROWSER_CHECK_FAILED '+phase+' '+(e.safeReason || e.name));process.exitCode=1;});
