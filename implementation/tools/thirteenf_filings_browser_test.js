'use strict';
// S16 13F views/investor stars and S15 filing timing use synthetic, schema-valid payloads by route interception only.
const {chromium}=require('playwright'),assert=require('node:assert/strict');
const IDS=['asml','lrcx','klac','tokyo_electron','hanmi','nvda','amd','avgo','qcom','intc','msft','googl','amzn','rtx','stry','etn','hubb','gev','rok'];
const H=c=>c.repeat(64);
function thirteenf(){const at=new Date().toISOString(),change=(cusip,a,b,kind)=>({cusip,security_key:H('c'),unit:'SH',kind,reported_before:a,reported_after:b,reported_delta:b-a});
 return {schema_version:1,kind:'SEC_13F',as_of:at,state:'LIVE',sources:[{agency:'SEC_13F',sha256:H('a'),acquired_at:at},{agency:'SEC_13F',sha256:H('b'),acquired_at:at}],reason_codes:[],freshness_basis:'SOURCE_ACQUISITION',stale_after_seconds:86400*120,
  data:{role:'REPORTED_QUANTITY_CHANGE_NOT_TRADES',reports:[{manager_cik:'0000000001',previous_quarter:'2026-03-31',current_quarter:'2026-06-30',state:'LIVE',source_hashes:{previous:H('a'),current:H('b')},changes:[change('A00000000',0,5,'NEW'),change('B00000000',4,0,'EXIT')]},
   {manager_cik:'0000000002',previous_quarter:'2026-03-31',current_quarter:'2026-06-30',state:'LIVE',source_hashes:{previous:H('a'),current:H('b')},changes:[change('A00000000',2,3,'ADD')]}]}};}
function filings(){const at=new Date().toISOString(),now=new Date(),soon=new Date(now.getTime()+2*86400000),companies={};
 for(const id of IDS)companies[id]={state:'NOT_AVAILABLE',role:'ESTIMATED_PATTERN_NOT_CONFIRMED',confirmed_earnings_date:null,groups:[],source_hashes:{}};
 const d=soon.getUTCDate();companies.nvda={state:'LIVE',role:'ESTIMATED_PATTERN_NOT_CONFIRMED',confirmed_earnings_date:null,source_hashes:{companyfacts:H('a'),submissions:H('b')},groups:[{form:'10-Q',report_month_day:'09-30',observation_count:2,observed_filing_windows:[{month:soon.getUTCMonth()+1,day_min:d,day_max:d,count:2}]}]};
 return {schema_version:1,kind:'SEC_FILING_WINDOWS',as_of:at,state:'LIVE',sources:[{agency:'SEC_COMPANYFACTS',sha256:H('a'),acquired_at:at},{agency:'SEC_SUBMISSIONS',sha256:H('b'),acquired_at:at}],reason_codes:[],freshness_basis:'SOURCE_ACQUISITION',stale_after_seconds:86400,data:{companies}};}
(async()=>{const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_EXECUTABLE_PATH});let phase='START',pass=0,fail=0;
 try{for(const width of [390,1440]){const context=await browser.newContext({viewport:{width,height:900},serviceWorkers:'block'});
  await context.route('**/sec-13f-changes.json',r=>r.fulfill({status:200,contentType:'application/json',body:JSON.stringify(thirteenf())}));await context.route('**/sec-filing-windows.json',r=>r.fulfill({status:200,contentType:'application/json',body:JSON.stringify(filings())}));
  const page=await context.newPage();let errors=0;page.on('pageerror',()=>errors++);
  try{phase='13F';await page.goto(process.env.PAGES_COCKPIT_URL+'#thirteenf');await page.locator('[data-13f-manager]').first().waitFor();
   assert.ok((await page.locator('[data-13f-warning]').textContent()).includes('투자 신호 아님'));assert.equal(await page.locator('[data-13f-manager]').count(),2);
   phase='STAR';await page.locator('[data-investor-star="0000000002"]').click();await page.locator('[data-investor-star="0000000002"][aria-pressed="true"]').waitFor();
   assert.deepEqual(await page.locator('[data-13f-manager]').evaluateAll(n=>n.map(x=>x.dataset['13fManager'])),['0000000002','0000000001']);
   await page.reload();await page.locator('[data-investor-star="0000000002"][aria-pressed="true"]').waitFor();
   phase='VIEWS';await page.locator('[data-13f-view="security"]').click();await page.locator('[data-13f-security]').first().waitFor();assert.deepEqual(await page.locator('[data-13f-security]').evaluateAll(n=>n.map(x=>x.dataset['13fSecurity'])),['A00000000','B00000000']);
   await page.locator('[data-13f-view="overlap"]').click();assert.ok((await page.locator('[data-13f-overlap]').textContent()).includes('NOT_AVAILABLE'));
   phase='FILINGS';await page.goto(process.env.PAGES_COCKPIT_URL+'#company/nvda');await page.locator('[data-next-window]').waitFor();assert.ok((await page.locator('[data-public-screen="filings"]').textContent()).includes('확정일 아님'));
   phase='WEEK';await page.evaluate(()=>localStorage.setItem('investment.web.v1.personal',JSON.stringify({version:1,interests:['nvda','amd'],groups:[]})));await page.goto(process.env.PAGES_COCKPIT_URL+'#watchlist');await page.reload();await page.locator('[data-week-filings]').waitFor();
   assert.ok((await page.locator('[data-week-filings]').textContent()).startsWith('1 · '));
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));assert.equal(errors,0);pass++;console.log('PASS 13F views stars and filing timing '+width);
  }catch(e){fail++;console.log('FAIL 13F/filings '+width+' '+phase+' '+(e.code==='ERR_ASSERTION'?'CONTRACT':'EXECUTION'));}finally{await context.close();}}}
 finally{await browser.close();}console.log('COUNTS pass='+pass+' fail='+fail);process.exitCode=fail?1:0;})();
