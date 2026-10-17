'use strict';
// S06 leaderboard table/views, S07 news notes, S11 settings badges, S13 official view. Synthetic public Q/G payload by route interception only.
const {chromium}=require('playwright'),assert=require('node:assert/strict');
const IDS=['asml','lrcx','klac','tokyo_electron','hanmi','nvda','amd','avgo','qcom','intc','msft','googl','amzn','rtx','stry','etn','hubb','gev','rok'];
const FACTORS=['competitive_advantage','eps_fcf_per_share_growth','excess_growth_vs_industry','fcf_quality','financial_health','growth_durability','growth_efficiency','management_quality','margin_quality','market_position','next_3_5y_growth','revenue_growth','roic_wacc'];
function qg(){const at=new Date().toISOString(),a='a'.repeat(64),b='b'.repeat(64),companies={};for(const id of IDS)companies[id]={state:'NOT_AVAILABLE',source_hashes:{},factors:Object.fromEntries(FACTORS.map(f=>[f,{score:null,state:'NOT_AVAILABLE'}]))};
 companies.nvda={state:'LIVE',source_hashes:{companyfacts:a,submissions:b},factors:Object.fromEntries(FACTORS.map(f=>[f,{score:f==='competitive_advantage'?90:50,state:'LIVE'}]))};
 return {schema_version:1,kind:'SEC_QG_FACTORS',as_of:at,state:'LIVE',sources:[{agency:'SEC_COMPANYFACTS',sha256:a,acquired_at:at},{agency:'SEC_SUBMISSIONS',sha256:b,acquired_at:at}],reason_codes:[],freshness_basis:'SOURCE_ACQUISITION',stale_after_seconds:86400,data:{companies,method_status:'PROVISIONAL_UNCALIBRATED',availability_basis:'OBSERVED_CAPTURE_ONLY'}};}
(async()=>{const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_EXECUTABLE_PATH});let phase='START',pass=0,fail=0;
 try{for(const width of [390,1440]){const context=await browser.newContext({viewport:{width,height:900},serviceWorkers:'block'});await context.route('**/sec-qg-factors.json',r=>r.fulfill({status:200,contentType:'application/json',body:JSON.stringify(qg())}));const page=await context.newPage();let errors=0;page.on('pageerror',()=>errors++);
  try{phase='S06';await page.goto(process.env.PAGES_COCKPIT_URL+'#leaderboard');await page.locator('[data-leaderboard-table]').waitFor();
   assert.equal(await page.locator('[data-leaderboard-table] thead th').count(),10);assert.equal(await page.locator('[data-leaderboard-row]').count(),19);
   // QGV v2 is the only score (owner decision 2026-10-14): the v1 Q·G (Q 58.0 from sec-qg-factors.json) is not shown; each row
   // shows v2 or the v2 NOT_AVAILABLE reason (LIVE builds may publish sec-qgv2.json).
   const nvda=await page.locator('[data-leaderboard-row="nvda"] td').allTextContents();assert.ok(!nvda[2].includes('Q 58.0'));assert.match(nvda[2],/^(QGV |QGV v2 산출 불가 · )/);assert.equal(await page.locator('[data-leaderboard-row="amd"] [data-leaderboard-qg]').count(),0);
   assert.equal(await page.locator('[data-leaderboard-qg]').count(),0);assert.ok(!/임시 기본|v1 비교용|v1 참고|점수 기준 v1/.test(await page.locator('[data-leaderboard-screen]').textContent()));
   assert.equal(await page.locator('[data-reeval-stages] li').count(),4);
   phase='PROFILE_VIEW';await page.evaluate(()=>{const w=JSON.parse(JSON.stringify(window.ProfileDefaults.weights));w.Q.competitive_advantage=40;w.Q.roic_wacc=0;localStorage.setItem('investment.web.v1.profile-drafts',JSON.stringify({schema:'device-profile-drafts/1',strategies:[{id:'p-1',name:'Mine',weights:w}],types:[]}));});
   await page.locator('[data-leaderboard-view="profile"]').click();await page.locator('[data-leaderboard-profile]').selectOption('p-1');await page.locator('[data-leaderboard-preview-note]').waitFor();
   assert.ok((await page.locator('[data-leaderboard-row="nvda"] [data-leaderboard-qg]').textContent()).includes('Q 66.0'));assert.ok((await page.locator('[data-leaderboard-row="nvda"] [data-leaderboard-qg]').textContent()).includes('PREVIEW'));
   await page.locator('[data-leaderboard-view="device"]').click();assert.equal(await page.locator('details:has(#private-subset-root)').getAttribute('open'),'');
   phase='S07';await page.goto(process.env.PAGES_COCKPIT_URL+'#news');await page.locator('[data-news-overlay]').waitFor();assert.equal(await page.locator('[data-news-scopes] .badge').count(),7);
   phase='S11';await page.goto(process.env.PAGES_COCKPIT_URL+'#settings');await page.locator('[data-settings-badges]').waitFor();assert.ok((await page.locator('[data-settings-badges]').textContent()).includes('주문 기능 없음'));
   // S13: the v1 official leaf-weight bars and 'v1 비교용' are gone; the v2 default axes are shown (owner decision 2026-10-14).
   phase='S13';await page.goto(process.env.PAGES_COCKPIT_URL+'#profiles');await page.locator('[data-profile-official]').waitFor();assert.equal(await page.locator('[data-v2-official-axis]').count(),3);assert.equal(await page.locator('[data-official-axis]').count(),0);assert.equal(await page.locator('[data-six-perspectives] dd').count(),6);
   assert.ok((await page.locator('[data-version-record]').textContent()).includes('v2 기본'));assert.ok(!/v1 비교용|비교용 · v1|임시 기본/.test(await page.locator('[data-profile-official]').textContent()));
   assert.equal(await page.evaluate(()=>Object.keys(localStorage).some(k=>/leaderboard|preview/i.test(k))),false);
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));assert.equal(errors,0);pass++;console.log('PASS leaderboard/news/settings/profile screens '+width);
  }catch(e){fail++;console.log('FAIL screens '+width+' '+phase+' '+(e.code==='ERR_ASSERTION'?'CONTRACT':'EXECUTION'));}finally{await context.close();}}}
 finally{await browser.close();}console.log('COUNTS pass='+pass+' fail='+fail);process.exitCode=fail?1:0;})();
