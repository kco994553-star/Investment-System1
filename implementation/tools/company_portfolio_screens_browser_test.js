'use strict';
// Design canvas S03 portfolio, S04 company summary, S05 company analysis.
// Phase A: empty device and the published public build (everything missing must read NOT_AVAILABLE, never 0).
// Phase B: synthetic, schema-valid sec-qg-factors / company-types-pricefree / sec-filing-windows served by route
// interception only, plus ACTUAL holdings entered on a throw-away browser context (RAM-only exposure maths).
const {chromium}=require('playwright'),assert=require('node:assert/strict');
const BASE=process.env.PAGES_COCKPIT_URL;
const IDS=['asml','lrcx','klac','tokyo_electron','hanmi','nvda','amd','avgo','qcom','intc','msft','googl','amzn','rtx','stry','etn','hubb','gev','rok'];
const FACTORS=['competitive_advantage','eps_fcf_per_share_growth','excess_growth_vs_industry','fcf_quality','financial_health','growth_durability','growth_efficiency','management_quality','margin_quality','market_position','next_3_5y_growth','revenue_growth','roic_wacc'];
const H=c=>c.repeat(64);
function envelope(kind,data,agencies){const at=new Date().toISOString();return{schema_version:1,kind,as_of:at,state:'LIVE',sources:[{agency:agencies[0],sha256:H('a'),acquired_at:at},{agency:agencies[1],sha256:H('b'),acquired_at:at}],reason_codes:[],freshness_basis:'SOURCE_ACQUISITION',stale_after_seconds:86400,data};}
const live={companyfacts:H('a'),submissions:H('b')};
function qg(){const companies={};for(const id of IDS)companies[id]={state:'NOT_AVAILABLE',source_hashes:{},factors:Object.fromEntries(FACTORS.map(f=>[f,{score:null,state:'NOT_AVAILABLE'}]))};
 companies.nvda={state:'LIVE',source_hashes:live,factors:Object.fromEntries(FACTORS.map(f=>[f,{score:f==='competitive_advantage'?90:f==='roic_wacc'?30:50,state:'LIVE'}]))};
 return envelope('SEC_QG_FACTORS',{companies,method_status:'PROVISIONAL_UNCALIBRATED',availability_basis:'OBSERVED_CAPTURE_ONLY'},['SEC_COMPANYFACTS','SEC_SUBMISSIONS']);}
function types(){const companies={};for(const id of IDS)companies[id]={state:'NOT_AVAILABLE',config_version:null,source_hashes:{},memberships:{growth:null,quality:null,cyclical:null,defensive:null}};
 companies.nvda={state:'LIVE',config_version:'type_config/1',source_hashes:live,memberships:{growth:0.8,quality:0.35,cyclical:null,defensive:null}};
 companies.hanmi={state:'LIVE',config_version:'type_config/1',source_hashes:live,memberships:{growth:0.1,quality:0.5,cyclical:null,defensive:null}};
 return envelope('COMPANY_TYPES_PRICEFREE',{companies,method_status:'PROVISIONAL_UNCALIBRATED',availability_basis:'OBSERVED_CAPTURE_ONLY'},['SEC_COMPANYFACTS','SEC_SUBMISSIONS']);}
function filings(){const companies={},soon=new Date(Date.now()+3*86400000);for(const id of IDS)companies[id]={state:'NOT_AVAILABLE',role:'ESTIMATED_PATTERN_NOT_CONFIRMED',confirmed_earnings_date:null,groups:[],source_hashes:{}};
 companies.nvda={state:'LIVE',role:'ESTIMATED_PATTERN_NOT_CONFIRMED',confirmed_earnings_date:null,source_hashes:live,groups:[{form:'10-Q',report_month_day:'09-30',observation_count:2,observed_filing_windows:[{month:soon.getUTCMonth()+1,day_min:soon.getUTCDate(),day_max:soon.getUTCDate(),count:2}]}]};
 return envelope('SEC_FILING_WINDOWS',{companies},['SEC_COMPANYFACTS','SEC_SUBMISSIONS']);}
async function open(page,hash,selector){await page.goto(BASE+'#'+hash);await page.locator('main '+selector).first().waitFor();}
async function noScroll(page,label){assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'no horizontal scroll '+label);}
const text=async(page,selector)=>(await page.locator(selector).first().textContent()).trim();
(async()=>{const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_EXECUTABLE_PATH});let phase='START',pass=0,fail=0;
 try{for(const width of [390,1440]){
  // ---------- Phase A: empty device, public build as published ----------
  {const context=await browser.newContext({viewport:{width,height:900},serviceWorkers:'block'}),page=await context.newPage();page.setDefaultTimeout(15000);let errors=0;page.on('pageerror',()=>errors++);
   try{
    phase='S04-EMPTY';await open(page,'company/nvda','[data-company-card="qgv"]');
    assert.equal(await text(page,'main h1'),'NVDA');assert.equal(await page.locator('main button.star').count(),1);
    assert.equal(await page.locator('[data-company-card="classification"] [data-axis]').count(),3);
    for(const axis of ['industry','theme','type'])assert.ok((await text(page,'[data-axis="'+axis+'"]')).includes('NOT_AVAILABLE'),axis+' NOT_AVAILABLE');
    assert.ok((await text(page,'[data-company-card="classification"]')).includes('서로 다른 축'));
    await page.waitForFunction(()=>document.querySelector('[data-holding="theme"]'));
    assert.equal(await text(page,'[data-holding="theme"]'),'AI·반도체');assert.equal(await text(page,'[data-holding="target"]'),'8.0%');
    assert.ok((await text(page,'[data-holding="actual"]')).includes('NOT_AVAILABLE'));assert.equal(await text(page,'[data-holding="delta"]'),'—');
    assert.equal(await page.locator('#company-holding a[href="#actual"]').count(),1);
    for(const key of ['V','rank','reeval'])assert.ok((await text(page,'[data-qgv="'+key+'"]')).includes('NOT_AVAILABLE'),key);
    assert.equal(await page.locator('[data-company-card="qgv"] a[href="#analysis/nvda"]').count(),1);
    assert.equal(await page.locator('[data-company-card="technical"] #private-history-chart').count(),1);
    assert.equal(await page.locator('[data-company-card="technical"] a[href="#technical"]').count(),1);
    for(const card of ['macro','news','vmr'])assert.ok((await text(page,'[data-company-card="'+card+'"]')).includes('NOT_AVAILABLE'),card);
    for(const mount of ['#sec-reported-panel','#public-qg','#public-types','#public-filings'])assert.equal(await page.locator('main '+mount).count(),1,mount);
    await noScroll(page,'S04 empty');
    phase='S05-EMPTY';await open(page,'analysis/nvda','[data-analysis-tab]');
    assert.equal(await text(page,'main h1'),'NVDA');assert.equal(await text(page,'[data-analysis-back]'),'← NVDA 요약');assert.equal(await page.locator('[data-analysis-back]').getAttribute('href'),'#company/nvda');
    assert.equal(await page.locator('[data-analysis-tab]').count(),7);
    assert.deepEqual(await page.locator('[data-analysis-tab]').allTextContents(),['종합','사업·경쟁','재무','주가·이벤트','QGV 요소','가치·시나리오','비교·컨센서스']);
    assert.equal(await text(page,'.sub-category'),'종목 찾기');assert.equal(await page.locator('#primary-nav [data-nav-tab][aria-current="page"]').getAttribute('data-nav-tab'),'qgv');
    assert.ok((await text(page,'[data-confidence-note]')).includes('확률 아님'));assert.ok((await text(page,'[data-na="overall"]')).includes('NOT_AVAILABLE'));
    for(const key of ['business','financials','events','factors','value','compare']){await page.locator('[data-analysis-tab="'+key+'"]').click();assert.equal(await page.locator('[data-analysis-panel="'+key+'"]').isVisible(),true,key);assert.equal(await page.locator('[data-analysis-panel]:visible').count(),1,'one panel '+key);}
    await page.locator('[data-analysis-tab="factors"]').click();assert.equal(await page.locator('[data-factor]').count(),13);
    assert.deepEqual(await page.locator('[data-factor-score]').evaluateAll(n=>[...new Set(n.map(x=>x.textContent))]),['—']);
    await page.locator('[data-analysis-tab="financials"]').click();assert.equal(await page.locator('[data-analysis-panel="financials"] #sec-reported-panel').count(),1);
    await page.locator('[data-analysis-tab="value"]').click();assert.ok((await text(page,'[data-analysis-panel="value"]')).includes('NOT_AVAILABLE'));
    await noScroll(page,'S05 empty');
    await open(page,'analysis/unknown-company','h1');assert.equal(await page.locator('[data-analysis-tab]').count(),0);
    phase='S03-EMPTY';await open(page,'portfolio','[data-portfolio-card="themes"] [data-theme-row]');
    assert.equal(await page.locator('#device-actual-summary').count(),1);
    assert.ok((await text(page,'[data-badge="target"]')).includes('v0'));assert.ok((await text(page,'[data-badge="actual"]')).includes('NOT_AVAILABLE'));assert.ok((await text(page,'[data-badge="quote"]')).includes('NOT_AVAILABLE'));
    for(const card of ['industry','types','combos'])assert.ok((await text(page,'[data-portfolio-card="'+card+'"]')).includes('NOT_AVAILABLE'),card);
    assert.equal(await page.locator('[data-theme-row]').count(),4);
    assert.deepEqual(await page.locator('[data-theme-actual]').evaluateAll(n=>[...new Set(n.map(x=>x.textContent))]),['—']);
    assert.deepEqual(await page.locator('[data-theme-delta]').evaluateAll(n=>[...new Set(n.map(x=>x.textContent))]),['—']);
    assert.ok((await text(page,'[data-concentration]')).includes('NOT_AVAILABLE'));
    await noScroll(page,'S03 empty');
    phase='EN';await page.evaluate(()=>localStorage.setItem(AppLanguage.KEY,JSON.stringify({version:1,display_locale:'en-US',source_language:'all'})));await page.reload();
    await open(page,'company/nvda','[data-company-card="classification"]');assert.ok((await text(page,'[data-company-card="classification"]')).includes('Three classification axes'));
    await open(page,'portfolio','[data-portfolio-card="industry"]');assert.ok((await text(page,'[data-portfolio-card="industry"]')).includes('Industry composition'));
    assert.equal(errors,0);pass++;console.log('PASS company/portfolio screens empty '+width);
   }catch(e){fail++;console.log('FAIL company/portfolio screens empty '+width+' '+phase+' '+(e.code==='ERR_ASSERTION'?'CONTRACT '+String(e.message).split('\n')[0]:'EXECUTION '+String(e.message).split('\n')[0]));}finally{await context.close();}}
  // ---------- Phase B: synthetic public inputs + device ACTUAL ----------
  {const context=await browser.newContext({viewport:{width,height:900},serviceWorkers:'block'});
   for(const[file,body]of [['sec-qg-factors.json',qg],['company-types-pricefree.json',types],['sec-filing-windows.json',filings]])await context.route('**/'+file,r=>r.fulfill({status:200,contentType:'application/json',body:JSON.stringify(body())}));
   const page=await context.newPage();page.setDefaultTimeout(15000);let errors=0;page.on('pageerror',()=>errors++);
   try{
    phase='S04-DATA';await open(page,'company/nvda','[data-qgv="Q"]');
    await page.waitForFunction(()=>/\d/.test(document.querySelector('[data-qgv="Q"]').textContent));
    assert.equal((await text(page,'[data-qgv="Q"]')).replace(/\s+/g,' '),'54.0');assert.equal(await text(page,'[data-qgv="G"]'),'50.0');
    assert.ok((await text(page,'[data-qgv="V"]')).includes('NOT_AVAILABLE'));
    assert.deepEqual(await page.locator('[data-type-chip]').allTextContents(),['성장 0.80','우량 0.35']);
    assert.ok((await text(page,'[data-next-earnings]')).startsWith('10-Q '));assert.ok((await text(page,'[data-company-card="qgv"]')).includes('확정일 아님'));
    await open(page,'company/amd','[data-qgv="Q"]');assert.ok((await text(page,'[data-qgv="Q"]')).includes('NOT_AVAILABLE'));assert.ok((await text(page,'[data-axis="type"]')).includes('NOT_AVAILABLE'));
    phase='S05-DATA';await open(page,'analysis/nvda','[data-analysis-tab]');await page.locator('[data-analysis-tab="factors"]').click();
    assert.equal(await text(page,'[data-factor="competitive_advantage"] [data-factor-score]'),'90.0');assert.equal(await text(page,'[data-factor="roic_wacc"] [data-factor-score]'),'30.0');
    assert.ok((await text(page,'[data-factor="roic_wacc"]')).includes('LIVE'));
    phase='ACTUAL-ENTRY';await open(page,'actual','[data-security-index="4"]');
    const fill=async(index,quantity,average,price)=>{const row=page.locator('[data-security-index="'+index+'"]');await row.locator('[data-field="quantity"]').fill(quantity);await row.locator('[data-field="average_cost"]').fill(average);await row.locator('[data-field="price"]').fill(price);};
    await fill(4,'10','1000','3000');await fill(5,'1','100','100');await page.locator('[data-fx-currency="USD"] [data-field="rate"]').fill('1000');
    await page.locator('[data-action="save"]').click();await page.locator('[data-market-total]').filter({hasText:'130'}).waitFor();
    phase='S03-DATA';await open(page,'portfolio','[data-portfolio-card="themes"]');
    await page.waitForFunction(()=>document.querySelector('[data-badge="actual"]')?.textContent.includes('시세 반영'));
    const w={hanmi:30000/130000,nvda:100000/130000},near=(got,want)=>assert.ok(Math.abs(parseFloat(got.replace('%','').replace('−','-'))-want*100)<0.06,got+' vs '+want*100);
    near(await text(page,'[data-theme-row="semi_equipment"] [data-theme-actual]'),w.hanmi);near(await text(page,'[data-theme-row="ai_semi"] [data-theme-actual]'),w.nvda);
    assert.ok((await text(page,'[data-theme-row="ai_semi"] [data-theme-delta]')).includes('%p'));
    assert.ok((await text(page,'[data-portfolio-card="industry"]')).includes('NOT_AVAILABLE'));
    const growth=w.nvda*0.8+w.hanmi*0.1,quality=w.nvda*0.35+w.hanmi*0.5;
    near(await text(page,'[data-portfolio-card="types"] [data-type="growth"] [data-type-value]'),growth);near(await text(page,'[data-portfolio-card="types"] [data-type="quality"] [data-type-value]'),quality);
    assert.ok((await text(page,'[data-portfolio-card="types"] [data-type="cyclical"]')).includes('NOT_AVAILABLE'));assert.ok((await text(page,'[data-portfolio-card="types"] [data-type="defensive"]')).includes('NOT_AVAILABLE'));
    near(await text(page,'[data-combo="growth+quality"] .num'),w.nvda);near(await text(page,'[data-combo="quality"] .num'),w.hanmi);
    assert.equal(await page.locator('[data-combo="unclassified"]').count(),0);
    const sum=(await page.locator('[data-portfolio-card="combos"] [data-combo] .num').allTextContents()).reduce((a,x)=>a+parseFloat(x),0);assert.ok(Math.abs(sum-100)<0.15,'combos total '+sum);
    await noScroll(page,'S03 data');
    phase='S04-ACTUAL';await open(page,'company/nvda','[data-holding="theme"]');await page.waitForFunction(()=>!document.querySelector('[data-holding="actual"]').textContent.includes('NOT_AVAILABLE'));
    near(await text(page,'[data-holding="actual"]'),w.nvda);assert.ok((await text(page,'[data-holding="delta"]')).includes('%p'));
    assert.equal(await text(page,'[data-holding="target"]'),'8.0%');
    phase='NO-LEAK';assert.equal(/quantity|average_cost|weight|membership/.test(await page.evaluate(()=>JSON.stringify({...localStorage,...sessionStorage}))),false);
    await noScroll(page,'S04 data');
    assert.equal(errors,0);pass++;console.log('PASS company/portfolio screens with data '+width);
   }catch(e){fail++;console.log('FAIL company/portfolio screens with data '+width+' '+phase+' '+(e.code==='ERR_ASSERTION'?'CONTRACT '+String(e.message).split('\n')[0]:'EXECUTION '+String(e.message).split('\n')[0]));}finally{await context.close();}}
 }}finally{await browser.close();}
 console.log('COUNTS pass='+pass+' fail='+fail);process.exitCode=fail?1:0;})();
