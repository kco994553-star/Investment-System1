'use strict';const {chromium}=require('playwright'),assert=require('node:assert/strict'),{mixed}=require('./sec_reported_fixture.js');
(async()=>{const b=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_EXECUTABLE_PATH});let pass=0,fail=0;
 try{for(const width of [390,1440]){const c=await b.newContext({viewport:{width,height:900},serviceWorkers:'block'}),p=await c.newPage();let errors=0;p.on('pageerror',()=>errors++);
  try{await p.goto(process.env.PAGES_COCKPIT_URL+'#settings');await p.locator('[data-ops-status]').waitFor();assert.equal(await p.locator('[data-ops-row]').count(),7);
   const states=await p.locator('[data-ops-state]').allTextContents();assert.ok(states.every(s=>/^(LIVE|STALE|NOT_AVAILABLE)( · STALE)?$/.test(s)));
   // Schema /4 (owner decision 2026-10-17): completeness of the run and the scheduled deploy streak, shown apart.
   await p.route('**/sec-public-inputs.json',r=>r.fulfill({contentType:'application/json',body:JSON.stringify(mixed())}));await p.reload();await p.locator('[data-sec-collection="INCOMPLETE"]').waitFor();
   assert.ok((await p.locator('[data-sec-collection] strong').textContent()).endsWith('신규 수집 14/17'));
   assert.ok((await p.locator('[data-sec-collection-counts]').textContent()).startsWith('값 13 · 정책상 NA 1 · 이전 관측 유지 1 · 수집 실패 1 · 식별 충돌 철회 1 · 실행 2026-01-02T12:05:00Z (정기) · 이전 사본 읽음'));
   assert.deepEqual(await p.locator('[data-sec-collection-row]').evaluateAll(n=>n.map(x=>x.dataset.secCollectionRow+':'+x.dataset.run)),['amd:PRESERVED','asml:WITHDRAWN','avgo:FAILED']);
   const kept=await p.locator('[data-sec-collection-row="amd"]').textContent();assert.ok(kept.startsWith('AMD · 이전 관측 유지 · 수집 2026-01-01T12:00:00Z · ')&&kept.endsWith(' · STALE · SEC_HTTP_503'));
   assert.ok((await p.locator('[data-sec-collection-row="asml"]').textContent()).includes('식별 충돌 · 이전 관측 사용 중지 · 감지 2026-01-02T12:03:00Z'));
   // The fixture's scheduled run (2026-01-02) is before the 2026-10-19 start day: 0, not started before it, broken after it.
   const streak=p.locator('[data-deploy-streak]');assert.ok(['NOT_STARTED','BROKEN'].includes(await streak.getAttribute('data-deploy-streak')));
   const streakText=await streak.textContent();assert.ok(streakText.includes('정기 실행 연속 배포 성공(게시본 기준 추정): 0회 / 7회')&&streakText.includes('2026-10-19 실행부터 집계')&&streakText.includes('수집 완전성과 별도')&&streakText.includes('실제 배포 성공은 보고 때 Actions 기록으로 확인합니다'));
   assert.ok(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
   await p.goto(process.env.PAGES_COCKPIT_URL+'#home');await p.locator('[data-data-basis] a[href="#settings"]').waitFor();
   assert.ok(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));assert.equal(errors,0);pass++;console.log('PASS ops status '+width);}
  catch(e){fail++;console.log('FAIL ops status '+width+' '+(e.code==='ERR_ASSERTION'?'CONTRACT':'EXECUTION'));}finally{await c.close();}}}
 finally{await b.close();}console.log('COUNTS pass='+pass+' fail='+fail);process.exitCode=fail?1:0;})();
