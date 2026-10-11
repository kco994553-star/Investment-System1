'use strict';
// S13 PREVIEW: a synthetic, schema-valid sec-qg-factors.json is served by route interception only.
// Draft weights recalculate Q/G in RAM; nothing calculated is written to device storage.
const {chromium}=require('playwright'),assert=require('node:assert/strict');
const IDS=['asml','lrcx','klac','tokyo_electron','hanmi','nvda','amd','avgo','qcom','intc','msft','googl','amzn','rtx','stry','etn','hubb','gev','rok'];
const FACTORS=['competitive_advantage','eps_fcf_per_share_growth','excess_growth_vs_industry','fcf_quality','financial_health','growth_durability','growth_efficiency','management_quality','margin_quality','market_position','next_3_5y_growth','revenue_growth','roic_wacc'];
function payload(){const at=new Date().toISOString(),a='a'.repeat(64),b='b'.repeat(64),companies={};
 for(const id of IDS)companies[id]={state:'NOT_AVAILABLE',source_hashes:{},factors:Object.fromEntries(FACTORS.map(f=>[f,{score:null,state:'NOT_AVAILABLE'}]))};
 const live=(scores)=>({state:'LIVE',source_hashes:{companyfacts:a,submissions:b},factors:Object.fromEntries(FACTORS.map(f=>[f,{score:scores[f]??50,state:'LIVE'}]))});
 companies.nvda=live({competitive_advantage:90,roic_wacc:30});companies.amd=live({competitive_advantage:10,roic_wacc:90});
 return {schema_version:1,kind:'SEC_QG_FACTORS',as_of:at,state:'LIVE',sources:[{agency:'SEC_COMPANYFACTS',sha256:a,acquired_at:at},{agency:'SEC_SUBMISSIONS',sha256:b,acquired_at:at}],reason_codes:[],freshness_basis:'SOURCE_ACQUISITION',stale_after_seconds:86400,data:{companies,method_status:'PROVISIONAL_UNCALIBRATED',availability_basis:'OBSERVED_CAPTURE_ONLY'}};}
function types(){const at=new Date().toISOString(),a='a'.repeat(64),b='b'.repeat(64),companies={};for(const id of IDS)companies[id]={state:'NOT_AVAILABLE',source_hashes:{},memberships:{growth:null,quality:null,cyclical:null,defensive:null},config_version:null,metrics:{revenue_cagr_3y:null,roic:null}};
 companies.nvda={state:'LIVE',source_hashes:{companyfacts:a,submissions:b},memberships:{growth:1,quality:null,cyclical:null,defensive:null},config_version:'type_config/1',metrics:{revenue_cagr_3y:0.25,roic:null}};
 return {schema_version:1,kind:'COMPANY_TYPES_PRICEFREE',as_of:at,state:'LIVE',sources:[{agency:'SEC_COMPANYFACTS',sha256:a,acquired_at:at},{agency:'SEC_SUBMISSIONS',sha256:b,acquired_at:at}],reason_codes:[],freshness_basis:'SOURCE_ACQUISITION',stale_after_seconds:86400,data:{companies,method_status:'PROVISIONAL_UNCALIBRATED',availability_basis:'OBSERVED_CAPTURE_ONLY'}};}
(async()=>{const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_EXECUTABLE_PATH});let phase='START',pass=0,fail=0;
 try{for(const width of [390,1440]){const context=await browser.newContext({viewport:{width,height:900},serviceWorkers:'block'});await context.route('**/sec-qg-factors.json',r=>r.fulfill({status:200,contentType:'application/json',body:JSON.stringify(payload())}));await context.route('**/company-types-pricefree.json',r=>r.fulfill({status:200,contentType:'application/json',body:JSON.stringify(types())}));const page=await context.newPage();let errors=0;page.on('pageerror',()=>errors++);
  try{phase='OPEN';await page.goto(process.env.PAGES_COCKPIT_URL+'#profiles');await page.locator('#profile-copy').click();
   phase='EDIT';await page.fill('#weight-Q-competitive_advantage','5');await page.fill('#weight-Q-roic_wacc','35');await page.locator('#profile-preview').click();
   phase='PREVIEW';await page.locator('[data-preview-row]').first().waitFor();
   const rows=await page.locator('[data-preview-row]').evaluateAll(r=>r.map(x=>[x.dataset.previewRow,...[...x.cells].map(c=>c.textContent)]));
   assert.deepEqual(rows.map(r=>r[0]),['amd','nvda']);assert.equal(rows[0][5],'▲1');assert.equal(rows[1][5],'▼1');
   assert.ok((await page.locator('[data-profile-preview]').textContent()).includes('NOT_AVAILABLE'));
   assert.equal(await page.evaluate(()=>JSON.stringify({...localStorage,...sessionStorage}).includes('qg_preview_total')||JSON.stringify({...localStorage}).includes('rank')),false);
   phase='CHANGE';await page.fill('#weight-Q-roic_wacc','30');assert.equal(await page.locator('[data-preview-row]').count(),0);
   phase='TYPES';await page.goto(process.env.PAGES_COCKPIT_URL+'#types');await page.locator('#type-copy').click();await page.fill('#type-profile-name','Mine');
   await page.fill('#type-growth-Q','60');await page.locator('#type-preview').click();assert.ok((await page.locator('[data-type-errors]').textContent()).includes('WEIGHT_SUM'));assert.equal(await page.locator('#type-save').isDisabled(),true);
   await page.fill('#type-growth-G','20');await page.locator('#type-preview').click();assert.equal(await page.locator('#type-save').isDisabled(),false);await page.locator('[data-type-preview-row="nvda"]').waitFor();const typeRow=await page.locator('[data-type-preview-row="nvda"] td').allTextContents();assert.equal(typeRow[1],'growth');assert.ok(typeRow[4].startsWith('Q 60.0 · G 20.0'));assert.equal(await page.locator('[data-type-preview-row]').count(),1);
   await page.locator('#type-save').click();await page.reload();await page.locator('[data-open-type]').first().waitFor();assert.equal(await page.locator('[data-open-type]').count(),1);
   const stored=await page.evaluate(()=>JSON.parse(localStorage.getItem('investment.web.v1.profile-drafts')));assert.equal(stored.types[0].config.types[0].weights.Q,60);assert.equal(stored.types[0].config.status,'CUSTOM_PREVIEW');
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));assert.equal(errors,0);pass++;console.log('PASS profile preview recalculation '+width);
  }catch(e){fail++;console.log('FAIL profile preview '+width+' '+phase+' '+(e.code==='ERR_ASSERTION'?'CONTRACT':'EXECUTION'));}finally{await context.close();}}}
 finally{await browser.close();}console.log('COUNTS pass='+pass+' fail='+fail);process.exitCode=fail?1:0;})();
