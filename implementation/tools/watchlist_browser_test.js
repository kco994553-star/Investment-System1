'use strict';const {chromium}=require('playwright'),assert=require('node:assert/strict');
/* Owner decision 2026-10-23 (TARGET v0 결합 해소) + IA-7. The watchlist, ★ and groups are keyed by Issuer ('sec:'+CIK10) and take
   any company (TARGET aliases and Universe504 codes); old TARGET company_id records are read, written back as issuer keys, and the
   original record is kept on the device (investment.web.v1.personal-v0). The S06 TARGET directory stays the v0 list (19 rows). */
const KEY='investment.web.v1.personal',V0='investment.web.v1.personal-v0',NVDA='sec:0001045810',AAPL='sec:0000320193';
(async()=>{const b=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_EXECUTABLE_PATH});let phase='START',pass=0,fail=0;try{for(const width of [390,1440]){const c=await b.newContext({viewport:{width,height:900},serviceWorkers:'block'}),p=await c.newPage();let errors=0,history=0;p.on('pageerror',()=>errors++);p.on('request',r=>{if(/\/history\?|workers\.dev/.test(r.url()))history++;});
 const stored=()=>p.evaluate(k=>JSON.parse(localStorage.getItem(k)||'null'),KEY);
 phase='LEADERBOARD';await p.goto(process.env.PAGES_COCKPIT_URL+'#leaderboard');await p.locator('#leader-company-list [data-star="nvda"]').waitFor();
 assert.equal(await p.locator('#leader-company-list [data-star]').count(),19,'S06 TARGET v0 list keeps its 19 rows');await p.locator('#leader-company-list [data-star="nvda"]').click();
 assert.deepEqual((await stored()).interests,[NVDA],'a TARGET star writes the issuer key, not the TARGET id');
 phase='DETAIL';await p.goto(process.env.PAGES_COCKPIT_URL+'#company/nvda');assert.equal(await p.locator('[data-star="nvda"]').first().getAttribute('aria-pressed'),'true');
 phase='UNIVERSE';await p.goto(process.env.PAGES_COCKPIT_URL+'#company/NASDAQ:AAPL');const uStar=p.locator('[data-uc-star] [data-star="NASDAQ:AAPL"]');await uStar.waitFor();
 assert.equal(await uStar.getAttribute('aria-pressed'),'false');assert.equal(await p.locator('[data-uc-chart="NA"]').count(),1,'outside the range before ★');
 await uStar.click();await p.locator('[data-uc-star] [data-star="NASDAQ:AAPL"][aria-pressed="true"]').waitFor();
 assert.deepEqual((await stored()).interests,[NVDA,AAPL],'a Universe504 company (outside TARGET) is watched by its issuer key');
 assert.equal(await p.locator('[data-uc-chart="NA"]').count(),0,'★ puts the company in the device chart range');assert.equal(await p.locator('[data-uc-chart-host] [data-private-history]').count(),1);
 assert.notEqual(await p.locator('[data-history-status]').first().getAttribute('data-code'),'LOADING');assert.equal(history,0,'no price request without a click');
 phase='GROUP';await p.goto(process.env.PAGES_COCKPIT_URL+'#watchlist');
 assert.deepEqual(await p.locator('#watchlist-company-list [data-star]').evaluateAll(n=>n.map(x=>x.dataset.star)),['nvda','NASDAQ:AAPL'],'the watchlist screen lists the watched companies, not the TARGET catalog');
 await p.locator('details').last().evaluate(e=>e.open=true);await p.locator('#group-name').fill('Synthetic group');await p.locator('#new-group button').click();await p.locator('details').last().evaluate(e=>e.open=true);
 await p.locator('[data-member="'+AAPL+'"]').check();const group=await p.locator('[data-member="'+AAPL+'"]').getAttribute('data-group');await p.selectOption('#watch-group',group);
 assert.deepEqual(await p.locator('#watchlist-company-list [data-star]').evaluateAll(n=>n.map(x=>x.dataset.star)),['NASDAQ:AAPL']);
 phase='FILTER';await p.goto(process.env.PAGES_COCKPIT_URL+'#leaderboard/interest');await p.locator('#leader-company-list [data-star="nvda"]').waitFor();assert.equal(await p.locator('#leader-company-list [data-star]').count(),1);
 await p.locator('#leader-company-list [data-star="nvda"]').click();assert.equal(await p.locator('#leader-company-list [data-star]').count(),0);
 assert.ok(await p.evaluate(([k,a])=>{const v=JSON.parse(localStorage.getItem(k));return v.interests.length===1&&v.interests[0]===a&&v.groups[0].members.length===1&&v.groups[0].members[0]===a;},[KEY,AAPL]));
 phase='COMPANIES';await p.goto(process.env.PAGES_COCKPIT_URL+'#companies');await p.locator('#company-list [data-star]').first().waitFor();
 await p.locator('#search').fill('AAPL');assert.deepEqual(await p.locator('#company-list [data-star]').evaluateAll(n=>n.map(x=>x.dataset.star)),['NASDAQ:AAPL'],'the company list includes Universe504 companies');
 await p.locator('#search').fill('amd');await p.locator('#company-list [data-star="amd"]').click();await p.reload();await p.locator('#company-list [data-star="amd"]').waitFor();
 assert.equal(await p.locator('#company-list [data-star="amd"]').getAttribute('aria-pressed'),'true');assert.ok((await stored()).interests.includes('sec:0000002488'));
 phase='MIGRATION';const old=JSON.stringify({version:1,interests:['nvda','amd','legacy_unknown'],groups:[{id:'g1',name:'Old',members:['nvda']}]});
 await p.evaluate(([k,v,o])=>{localStorage.removeItem(v);localStorage.setItem(k,o);},[KEY,V0,old]);await p.goto(process.env.PAGES_COCKPIT_URL+'#watchlist');await p.reload();await p.locator('#watchlist-company-list [data-star="nvda"]').waitFor();
 assert.equal(await p.evaluate(k=>localStorage.getItem(k),KEY),old,'reading old keys does not write');assert.equal(await p.locator('#watchlist-company-list [data-star="nvda"]').getAttribute('aria-pressed'),'true');
 await p.locator('#watchlist-company-list [data-star="amd"]').click();
 assert.equal(await p.evaluate(k=>localStorage.getItem(k),V0),old,'the v0 record is kept as it was');
 assert.deepEqual(await stored(),{version:1,interests:[NVDA,'legacy_unknown'],groups:[{id:'g1',name:'Old',members:[NVDA]}]},'new keys written, unknown keys kept');
 await p.locator('#watchlist-company-list [data-star="nvda"]').click();assert.equal(await p.evaluate(k=>localStorage.getItem(k),V0),old,'the v0 record is written once and never overwritten');
 assert.ok(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));assert.equal(errors,0);pass++;console.log('PASS issuer-keyed-watchlist-any-company-migration '+width);await c.close();}}catch(e){fail++;console.log('FAIL watchlist '+phase+' '+(e&&e.message||'').slice(0,200));}finally{await b.close();}console.log('COUNTS pass='+pass+' fail='+fail);if(fail)process.exitCode=1;})();
