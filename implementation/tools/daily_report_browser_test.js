'use strict';const {chromium}=require('playwright'),assert=require('node:assert/strict');
// S17 daily reports at 390 and 1440: links from S01, badges, amount hiding on by default, template export with/without guide,
// 보고 불가 card with a copyable prompt, AI answer review before save with format/number warnings (pasted or from the AI mailbox),
// no horizontal scroll, and no network request carrying the report.
(async()=>{const b=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_EXECUTABLE_PATH});let pass=0,fail=0;
 try{for(const width of [390,1440]){const c=await b.newContext({viewport:{width,height:900},serviceWorkers:'block',permissions:['clipboard-read','clipboard-write']}),p=await c.newPage();let errors=0;const posts=[];
  p.on('pageerror',e=>{errors++;console.log(String(e));});p.on('request',r=>{if(r.method()!=='GET'||/ReportInbox|%5B%EC%9D%BC%EC%9D%BC|일일보고서 템플릿/.test(r.url()))posts.push(r.url());});
  try{await p.goto(process.env.PAGES_COCKPIT_URL+'#brief');await p.locator('[data-report-link="mock"]').click();
   await p.locator('[data-report-badges]').waitFor();
   const badges=await p.locator('[data-report-badges]').textContent();
   for(const s of ['STANDARD v1 · UNCALIBRATED','가상매매 규칙 v1','PROVISIONAL'])assert.ok(badges.includes(s),s);
   assert.equal(await p.locator('[data-hide-amounts]').isChecked(),true);
   assert.equal(await p.locator('[data-report-not-started]').count(),1);
   // Set A + user sets B/C/D; 비교 only with at least two defined sets (none without a connected sheet).
   assert.deepEqual(await p.locator('[data-report-tabs] a').allTextContents(),['세트 A','세트 B','세트 C','세트 D']);
   await p.locator('[data-export-template]').click();
   await p.waitForFunction(()=>/복사|표시/.test(document.querySelector('[data-report-status]')?.textContent||''));
   let text=await p.evaluate(async()=>{try{return await navigator.clipboard.readText();}catch(_){return document.querySelector('[data-export-fallback]')?.value||'';}});
   assert.ok(text.startsWith('[Investment-System1 · AI 해석 지침 v1 · 템플릿 v1]'));assert.ok(text.includes('금액 표시: 숨김'));assert.ok(text.includes('## ⑬ 성과·위험'));
   await p.locator('[data-include-guide]').uncheck();await p.locator('[data-export-template]').click();
   await p.waitForTimeout(200);text=await p.evaluate(async()=>{try{return await navigator.clipboard.readText();}catch(_){const a=document.querySelectorAll('[data-export-fallback]');return a[a.length-1]?.value||'';}});
   assert.ok(text.startsWith('아래 일일보고서 템플릿의 【AI】 칸을'));
   // 보고 불가 (directive §9): reason → minimum missing inputs → copyable prompt, no filled numbers.
   const card=p.locator('[data-report-unavailable]');
   assert.equal(await card.getAttribute('data-unavailable-state'),'UNAVAILABLE');
   assert.ok((await p.locator('[data-unavailable-reason]').textContent()).includes('만들 수 없습니다'));
   assert.ok(await p.locator('[data-unavailable-missing] [data-missing-key]').count()>0);
   const prompt=await p.locator('[data-unavailable-prompt]').inputValue();
   for(const s of ['대상:','기간:','버전:','가용 자료','누락 자료','출처:','계산 가능 범위:','추정하거나 만들지 마라'])assert.ok(prompt.includes(s),s);
   assert.ok(!/\d+만원|●●●/.test(prompt),'no amount in the prompt');
   await p.locator('[data-unavailable-copy="all"]').click();
   await p.waitForFunction(()=>/복사|선택/.test(document.querySelector('[data-unavailable-status]')?.textContent||''));
   const copied=await p.evaluate(async()=>{try{return await navigator.clipboard.readText();}catch(_){return document.querySelector('[data-unavailable-prompt]').value;}});
   assert.equal(copied,prompt);
   await p.locator('[data-unavailable-areas] summary').click();await p.locator('[data-unavailable-copy="2"]').click();
   await p.waitForFunction(()=>(document.querySelector('[data-unavailable-scope]')?.textContent||'').includes('②'));
   assert.ok((await p.locator('[data-unavailable-prompt]').inputValue()).includes('영역 ② 포트폴리오 구성'));
   // Review before save: pasting stores nothing, the review is shown first, the user saves explicitly.
   const before=await p.evaluate(()=>Object.fromEntries(Object.keys(localStorage).map(k=>[k,localStorage.getItem(k)])));
   const AI=await p.evaluate(()=>window.DailyReport.AI_KEY);assert.equal(before[AI],undefined);
   await p.locator('[data-ai-input]').fill(text+'\n목표가 999.5');
   assert.equal(await p.locator('[data-save-answer]').isDisabled(),true,'save waits for a review');
   await p.locator('[data-review-answer]').click();await p.locator('[data-answer-review-result]').waitFor();
   assert.equal(await p.locator('[data-review-check="numbers"]').getAttribute('data-review-ok'),'0');
   assert.ok((await p.locator('[data-review-check="numbers"]').textContent()).includes('999.5'));
   assert.ok(await p.locator('[data-review-sections] li').count()>=16);
   assert.equal(await p.evaluate(k=>localStorage.getItem(k),AI),null,'review stores nothing');
   await p.locator('[data-ai-input]').press('End');await p.keyboard.type(' ');
   assert.equal(await p.locator('[data-save-answer]').isDisabled(),true,'an edit after the review needs a new review');
   assert.equal(await p.locator('[data-answer-review-result]').count(),0);
   await p.locator('[data-review-answer]').click();await p.locator('[data-answer-review-result]').waitFor();
   await p.locator('[data-save-answer]').click();
   await p.locator('[data-ai-answer]').waitFor();
   const after=await p.evaluate(()=>Object.fromEntries(Object.keys(localStorage).map(k=>[k,localStorage.getItem(k)])));
   assert.deepEqual(Object.keys(after).filter(k=>after[k]!==before[k]),[AI],'saving writes only the AI answer store');
   assert.equal((await p.locator('[data-answer-format]').textContent()).trim(),'형식 확인 필요');
   assert.ok((await p.locator('[data-foreign-numbers]').textContent()).includes('1개'));
   await p.reload();await p.locator('[data-ai-answer]').waitFor();
   p.once('dialog',d=>d.dismiss());await p.locator('[data-hide-amounts]').click();assert.equal(await p.locator('[data-hide-amounts]').isChecked(),true);
   await p.goto(process.env.PAGES_COCKPIT_URL+'#report/real');await p.locator('[data-report-badges]').waitFor();
   assert.equal(await p.locator('[data-report-tabs]').count(),0);assert.ok((await p.locator('h1, h2').first().textContent()).length>0);
   await p.locator('[data-report-unavailable]').waitFor();assert.equal(await p.locator('[data-missing-key="HOLDINGS"]').count(),1,'real report names the missing holdings');
   assert.ok((await p.locator('[data-unavailable-prompt]').inputValue()).includes('투자 일일보고서 · 내 실제 포트폴리오'));
   // AI 우체통: the Outbox answer with the same hash goes into the answer box and is reviewed like a pasted one; nothing is
   // stored until '검토한 답변 보관', which keeps source MAILBOX with the Outbox model and time. In-memory synthetic sheet session.
   await p.evaluate(()=>{const tabs=new Map(),tab=range=>/'([^']+)'/.exec(range)[1];window.__mailbox=tabs;
    const session={state:()=>({connected:true}),async sheetTitles(){return [...tabs.keys()];},async addTabs(_id,names){for(const n of names)tabs.set(n,[]);},
     async appendRows(_id,range,rows){tabs.get(tab(range)).push(...rows);},async fetchValues(_id,range){return {values:tabs.get(tab(range))||[]};}};
    window.GoogleSheetQuotes={...GoogleSheetQuotes,sessionFor:()=>session};window.GoogleSheetSetup={...GoogleSheetSetup,source:()=>'synthetic_mailbox_sheet_fixture'};});
   const mailAnswer='【AI】 우체통 합성 답변 · synthetic',storedBefore=await p.evaluate(k=>localStorage.getItem(k),AI);
   await p.locator('[data-mailbox-post]').click();
   await p.waitForFunction(()=>(document.querySelector('[data-report-status]')?.textContent||'').includes('ReportInbox'));
   await p.evaluate(a=>{const inbox=window.__mailbox.get(DailyReport.INBOX);window.__mailbox.get(DailyReport.OUTBOX).push([inbox[inbox.length-1][4],'synthetic-model','2026-10-18T09:00:00Z',a]);},mailAnswer);
   await p.locator('[data-mailbox-read]').click();await p.locator('[data-answer-review-result]').waitFor();
   assert.equal(await p.locator('[data-ai-input]').inputValue(),mailAnswer,'the mailbox answer is placed in the answer box');
   assert.equal(await p.locator('[data-save-answer]').isDisabled(),false,'reviewed: the save button is offered');
   assert.ok((await p.locator('[data-report-status]').textContent()).includes('아직 보관하지 않았습니다'));
   assert.equal(await p.evaluate(k=>localStorage.getItem(k),AI),storedBefore,'fetching from the mailbox stores nothing');
   assert.equal(await p.locator('[data-ai-answer]').count(),0);
   await p.locator('[data-save-answer]').click();await p.locator('[data-ai-answer]').waitFor();
   const mailStored=Object.values(await p.evaluate(k=>JSON.parse(localStorage.getItem(k)),AI)).filter(x=>x.answer===mailAnswer);
   assert.equal(mailStored.length,1);assert.equal(mailStored[0].source,'MAILBOX');assert.equal(mailStored[0].model,'synthetic-model');assert.equal(mailStored[0].saved_at,'2026-10-18T09:00:00Z');
   assert.ok((await p.locator('[data-report-ai-summary]').textContent()).includes('우체통'));
   assert.ok(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
   assert.equal(posts.length,0,posts.join(','));assert.equal(errors,0);pass++;console.log('PASS daily report '+width);}
  catch(e){fail++;console.log('FAIL daily report '+width+' '+(e.code==='ERR_ASSERTION'?'CONTRACT':'EXECUTION')+' '+e.message);}finally{await c.close();}}}
 finally{await b.close();}console.log('COUNTS pass='+pass+' fail='+fail);process.exitCode=fail?1:0;})();
