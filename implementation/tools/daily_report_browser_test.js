'use strict';const {chromium}=require('playwright'),assert=require('node:assert/strict');
// S17 daily reports at 390 and 1440: links from S01, badges, amount hiding on by default, template export with/without guide,
// AI answer storage with format/number warnings, no horizontal scroll, and no network request carrying the report.
(async()=>{const b=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_EXECUTABLE_PATH});let pass=0,fail=0;
 try{for(const width of [390,1440]){const c=await b.newContext({viewport:{width,height:900},serviceWorkers:'block',permissions:['clipboard-read','clipboard-write']}),p=await c.newPage();let errors=0;const posts=[];
  p.on('pageerror',e=>{errors++;console.log(String(e));});p.on('request',r=>{if(r.method()!=='GET'||/ReportInbox|%5B%EC%9D%BC%EC%9D%BC|일일보고서 템플릿/.test(r.url()))posts.push(r.url());});
  try{await p.goto(process.env.PAGES_COCKPIT_URL+'#home');await p.locator('[data-report-link="mock"]').click();
   await p.locator('[data-report-badges]').waitFor();
   const badges=await p.locator('[data-report-badges]').textContent();
   for(const s of ['STANDARD v1 · UNCALIBRATED','가상매매 규칙 v1','PROVISIONAL'])assert.ok(badges.includes(s),s);
   assert.equal(await p.locator('[data-hide-amounts]').isChecked(),true);
   assert.equal(await p.locator('[data-report-not-started]').count(),1);
   assert.equal(await p.locator('[data-report-tabs] a').count(),3);
   await p.locator('[data-export-template]').click();
   await p.waitForFunction(()=>/복사|표시/.test(document.querySelector('[data-report-status]')?.textContent||''));
   let text=await p.evaluate(async()=>{try{return await navigator.clipboard.readText();}catch(_){return document.querySelector('[data-export-fallback]')?.value||'';}});
   assert.ok(text.startsWith('[Investment-System1 · AI 해석 지침 v1 · 템플릿 v1]'));assert.ok(text.includes('금액 표시: 숨김'));assert.ok(text.includes('## ⑬ 성과·위험'));
   await p.locator('[data-include-guide]').uncheck();await p.locator('[data-export-template]').click();
   await p.waitForTimeout(200);text=await p.evaluate(async()=>{try{return await navigator.clipboard.readText();}catch(_){const a=document.querySelectorAll('[data-export-fallback]');return a[a.length-1]?.value||'';}});
   assert.ok(text.startsWith('아래 일일보고서 템플릿의 【AI】 칸을'));
   await p.locator('[data-ai-input]').fill(text+'\n목표가 999.5');await p.locator('[data-save-answer]').click();
   await p.locator('[data-ai-answer]').waitFor();
   assert.equal((await p.locator('[data-answer-format]').textContent()).trim(),'형식 확인 필요');
   assert.ok((await p.locator('[data-foreign-numbers]').textContent()).includes('1개'));
   await p.reload();await p.locator('[data-ai-answer]').waitFor();
   p.once('dialog',d=>d.dismiss());await p.locator('[data-hide-amounts]').click();assert.equal(await p.locator('[data-hide-amounts]').isChecked(),true);
   await p.goto(process.env.PAGES_COCKPIT_URL+'#report/real');await p.locator('[data-report-badges]').waitFor();
   assert.equal(await p.locator('[data-report-tabs]').count(),0);assert.ok((await p.locator('h1, h2').first().textContent()).length>0);
   assert.ok(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
   assert.equal(posts.length,0,posts.join(','));assert.equal(errors,0);pass++;console.log('PASS daily report '+width);}
  catch(e){fail++;console.log('FAIL daily report '+width+' '+(e.code==='ERR_ASSERTION'?'CONTRACT':'EXECUTION')+' '+e.message);}finally{await c.close();}}}
 finally{await b.close();}console.log('COUNTS pass='+pass+' fail='+fail);process.exitCode=fail?1:0;})();
