'use strict';
const {displayOnlyOff}=require('./display_only_off.js');
// S04/S05 value view (v1+dcf_v1_1_default) with a route-intercepted synthetic sec-valuation-inputs.json and a
// synthetic device quote entered on a throw-away browser context. Price stays in RAM: nothing price-derived is stored or sent.
const {chromium}=require('playwright'),assert=require('node:assert/strict');
const BASE=process.env.PAGES_COCKPIT_URL;
const VECTORS=JSON.parse(require('node:fs').readFileSync(require('node:path').join(__dirname,'../tests/fixtures/device_valuation_reference_v1.json'),'utf8')).cases;
const IDS=['asml','lrcx','klac','tokyo_electron','hanmi','nvda','amd','avgo','qcom','intc','msft','googl','amzn','rtx','stry','etn','hubb','gev','rok'];
const COMPONENTS=['operating_cash_flow','capital_expenditure','long_term_debt_issuance','long_term_debt_repayment','net_short_term_borrowing','diluted_shares'];
const H=c=>c.repeat(64);
function payload(){const at=new Date().toISOString(),companies={};
 for(const id of IDS)companies[id]={state:'NOT_AVAILABLE',source_hashes:{},fcfe:{state:'NOT_AVAILABLE',reason_codes:['SEC_INPUT_NOT_AVAILABLE'],fcfe_per_share:null,taxonomy:null,currency:null,fiscal_period_start:null,fiscal_period_end:null,accn:null,form:null,components:Object.fromEntries(COMPONENTS.map(k=>[k,null]))},v_inputs:{state:'NOT_AVAILABLE',reason_codes:['SEC_INPUT_NOT_AVAILABLE'],eps:null,revenue:null,revenue_prev:null,revenue_cagr_3y:null,currency:null}};
 const c=(concept,value)=>({concepts:[concept],value,assumed_zero:false,reason:null}),zero={concepts:[],value:0,assumed_zero:true,reason:'NOT_REPORTED_ASSUMED_ZERO'};
 companies.nvda={state:'LIVE',source_hashes:{companyfacts:H('a'),submissions:H('b')},fcfe:{state:'LIVE',reason_codes:[],fcfe_per_share:8.25,taxonomy:'us-gaap',currency:'USD',fiscal_period_start:'2025-01-01',fiscal_period_end:'2025-12-31',accn:'000104581026000001',form:'10-K',
  components:{operating_cash_flow:c('NetCashProvidedByUsedInOperatingActivities',1000),capital_expenditure:c('PaymentsToAcquirePropertyPlantAndEquipment',300),long_term_debt_issuance:c('ProceedsFromIssuanceOfLongTermDebt',200),long_term_debt_repayment:c('RepaymentsOfLongTermDebt',50),net_short_term_borrowing:c('ProceedsFromRepaymentsOfShortTermDebt',-25),diluted_shares:c('WeightedAverageNumberOfDilutedSharesOutstanding',100)}},
  v_inputs:{state:'LIVE',reason_codes:[],eps:4,revenue:5000,revenue_prev:4900,revenue_cagr_3y:0.08,currency:'USD'}};
 companies.amd={...companies.amd,state:'LIVE',source_hashes:{companyfacts:H('a'),submissions:H('b')},fcfe:{...companies.amd.fcfe,reason_codes:['NET_SHORT_TERM_BORROWING_MISSING'],taxonomy:'us-gaap',components:{...companies.amd.fcfe.components,operating_cash_flow:c('NetCashProvidedByUsedInOperatingActivities',500)}},v_inputs:{state:'LIVE',reason_codes:['REVENUE_CAGR_3Y_MISSING'],eps:2,revenue:100,revenue_prev:90,revenue_cagr_3y:null,currency:'USD'}};
 // IFRS 20-F filer reporting in EUR with unreported current/long-term repayment lines (assumed 0); no FX is applied.
 companies.asml={state:'LIVE',source_hashes:{companyfacts:H('a'),submissions:H('b')},fcfe:{state:'LIVE',reason_codes:[],fcfe_per_share:4.25,taxonomy:'ifrs-full',currency:'EUR',fiscal_period_start:'2025-01-01',fiscal_period_end:'2025-12-31',accn:'000093796626000001',form:'20-F',
  components:{operating_cash_flow:c('CashFlowsFromUsedInOperatingActivities',2000),capital_expenditure:c('PurchaseOfPropertyPlantAndEquipment',500),long_term_debt_issuance:c('ProceedsFromNoncurrentBorrowings',200),long_term_debt_repayment:zero,net_short_term_borrowing:zero,diluted_shares:c('AdjustedWeightedAverageShares',400)}},
  v_inputs:{state:'LIVE',reason_codes:[],eps:5,revenue:1331,revenue_prev:1210,revenue_cagr_3y:0.1,currency:'EUR'}};
 return{schema_version:1,kind:'SEC_VALUATION_INPUTS',as_of:at,state:'LIVE',sources:[{agency:'SEC_COMPANYFACTS',sha256:H('a'),acquired_at:at},{agency:'SEC_SUBMISSIONS',sha256:H('b'),acquired_at:at}],reason_codes:[],freshness_basis:'SOURCE_ACQUISITION',stale_after_seconds:86400,
  data:{companies,method_status:'PROVISIONAL_UNCALIBRATED',availability_basis:'OBSERVED_CAPTURE_ONLY',fcfe_definition:'fcfe/1.1',share_basis:'WEIGHTED_AVERAGE_DILUTED'}};}
const text=async(page,selector)=>(await page.locator(selector).first().textContent()).replace(/\s+/g,' ').trim();
async function open(page,hash,selector){await page.goto(BASE+'#'+hash);await page.locator('main '+selector).first().waitFor();}
async function valueTab(page,id){await open(page,'analysis/'+id,'[data-analysis-tab]');await page.locator('[data-analysis-tab="value"]').click();await page.locator('[data-analysis-panel="value"] [data-value="fcfe"]').waitFor();}
(async()=>{const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_EXECUTABLE_PATH});let pass=0,fail=0,phase='START';
 try{for(const width of [390,1440]){
  const context=await browser.newContext({viewport:{width,height:900},serviceWorkers:'block'});await displayOnlyOff(context);
  await context.route('**/sec-valuation-inputs.json',r=>r.fulfill({status:200,contentType:'application/json',body:JSON.stringify(payload())}));
  const page=await context.newPage();page.setDefaultTimeout(15000);let errors=0;page.on('pageerror',()=>errors++);
  const requests=[];page.on('request',r=>requests.push({url:r.url(),method:r.method(),body:r.postData()}));
  try{
   phase='BROWSER-PARITY';await open(page,'home','h1');
   const bad=await page.evaluate(cases=>{const close=(a,b)=>typeof b==='number'?typeof a==='number'&&Math.abs(a-b)<=Math.max(1e-10,Math.abs(b)*1e-10):Array.isArray(b)?Array.isArray(a)&&a.length===b.length&&b.every((v,i)=>close(a[i],v)):b&&typeof b==='object'?a&&typeof a==='object'&&Object.keys(a).sort().join()===Object.keys(b).sort().join()&&Object.keys(b).every(k=>close(a[k],b[k])):a===b;
    return cases.filter(c=>!close(DeviceValuation.view(c.input),c.expected)).map(c=>c.id);},VECTORS);
   assert.deepEqual(bad,[],'browser DeviceValuation.view matches every Python vector');
   phase='S05-NO-PRICE';await valueTab(page,'nvda');
   await page.waitForFunction(()=>document.querySelector('[data-value="fcfe"]').textContent.includes('8.25'));
   assert.ok((await text(page,'[data-dcf-badge]')).includes('v1.1 UNCALIBRATED 기본값 · 나중에 수정 가능'));assert.equal(await text(page,'[data-dcf-version]'),'v1+dcf_v1_1_default');
   assert.ok((await text(page,'[data-dcf-params]')).includes('명시 5년 · 할인율 10.0% · 영구성장 2.0% · 역DCF 탐색 −50.0%~+100.0% · 명시기간 성장률 h = 자사 3년 매출 CAGR, 0.0%~15.0% 범위로 제한 (PROVISIONAL)'));
   assert.ok((await text(page,'[data-value="fcfe"]')).includes('0001045810-26-000001'));
   for(const k of ['quote','reverse'])assert.ok((await text(page,'[data-value="'+k+'"]')).includes('NO_DEVICE_PRICE'),k);
   // The forward DCF value is price-free (public FCFE and h); the margin of safety needs the device price.
   assert.equal(await text(page,'[data-explicit-growth]'),'8.0%');assert.equal(await text(page,'[data-dcf-value]'),'USD 135.02');
   assert.ok((await text(page,'[data-value="mos"]')).includes('MISSING_PRICE'));assert.equal(await page.locator('[data-value="assumed-zero"]').count(),0);
   assert.equal(await page.locator('[data-v-factor]').count(),7);assert.deepEqual([...new Set(await page.locator('[data-v-score]').allTextContents())],['—']);
   phase='S05-IFRS';await valueTab(page,'asml');await page.waitForFunction(()=>document.querySelector('[data-value="fcfe"]').textContent.includes('4.25'));
   assert.ok((await text(page,'[data-value="fcfe"]')).includes('20-F · IFRS'));
   assert.ok((await text(page,'[data-value="assumed-zero"]')).includes('미보고 → 0 가정 장기차입 상환 · 단기차입 순증감'));
   assert.ok((await text(page,'[data-value="currency-basis"]')).includes('보고 통화 EUR · 기준 통화 USD · 환율 변환 없음'));
   assert.equal(await text(page,'[data-explicit-growth]'),'10.0%');assert.ok((await text(page,'[data-value="dcf"]')).includes('CURRENCY_BASIS_UNCONFIRMED'));
   phase='S05-FCFE-NA';await valueTab(page,'amd');await page.waitForFunction(()=>document.querySelector('[data-value="fcfe"]').textContent.includes('NET_SHORT_TERM_BORROWING_MISSING'));
   assert.ok(!(await text(page,'[data-value="fcfe"]')).includes('0.00'));
   assert.ok((await text(page,'[data-value="growth"]')).includes('EXPLICIT_GROWTH_NOT_AVAILABLE'));
   assert.ok((await text(page,'[data-value="dcf"]')).includes('FCFE_NOT_AVAILABLE'));assert.ok((await text(page,'[data-value="mos"]')).includes('DCF_NOT_AVAILABLE'));
   phase='DEVICE-QUOTE';await open(page,'actual','[data-security-index="5"]');
   const row=page.locator('[data-security-index="5"]');await row.locator('[data-field="quantity"]').fill('1');await row.locator('[data-field="average_cost"]').fill('90');await row.locator('[data-field="price"]').fill('100');
   await page.locator('[data-fx-currency="USD"] [data-field="rate"]').fill('1000');await page.locator('[data-action="save"]').click();await page.locator('[data-market-total]').filter({hasText:'100'}).waitFor();
   const before=requests.length;
   phase='S05-PRICE';await valueTab(page,'nvda');await page.waitForFunction(()=>document.querySelector('[data-implied-growth]'));
   assert.equal(await text(page,'[data-implied-growth]'),'0.8%');
   assert.ok((await text(page,'[data-value="quote"]')).includes('기기 수동 시세'));
   // Approved raw_map DCF branches: central (135.02/100−1)/0.4 and margin of safety (0.75×135.02/100−1)/0.3.
   assert.equal(await text(page,'[data-v-factor="fundamental_value"] [data-v-score]'),'93.8');assert.equal(await text(page,'[data-v-factor="reverse_dcf"] [data-v-score]'),'54.1');
   assert.equal(await text(page,'[data-v-factor="margin_of_safety"] [data-v-score]'),'52.1');assert.equal(await text(page,'[data-mos-score]'),'52.1');
   for(const k of ['peer_relative_value','historical_valuation','sector_context','theme_premium_discount'])assert.ok((await text(page,'[data-v-factor="'+k+'"]')).includes('NOT_AVAILABLE'),k);
   assert.equal(await text(page,'[data-dcf-value]'),'USD 135.02');
   phase='S04-PRICE';await open(page,'company/nvda','[data-company-card="value"]');await page.waitForFunction(()=>document.querySelector('[data-company-card="value"] [data-implied-growth]'));
   assert.equal(await text(page,'[data-company-card="value"] [data-implied-growth]'),'0.8%');assert.equal(await page.locator('[data-company-card="value"] [data-v-table]').count(),0);
   assert.ok((await text(page,'[data-company-card="value"] [data-dcf-badge]')).includes('v1.1 UNCALIBRATED'));assert.equal(await text(page,'[data-company-card="value"] [data-mos-score]'),'52.1');
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'no horizontal scroll');
   phase='NO-LEAK';
   const after=requests.slice(before);assert.ok(after.every(r=>r.method==='GET'&&!r.body&&new URL(r.url).origin===new URL(BASE).origin),'only same-origin GETs after a device price exists');
   assert.ok(after.every(r=>!/implied|growth|score|price/i.test(new URL(r.url).search)),'no derived values in URLs');
   const stored=await page.evaluate(async()=>{const out=[JSON.stringify({...localStorage}),JSON.stringify({...sessionStorage})];for(const info of await indexedDB.databases()){const db=await new Promise((ok,no)=>{const q=indexedDB.open(info.name);q.onsuccess=()=>ok(q.result);q.onerror=no;});for(const name of db.objectStoreNames){const all=await new Promise(ok=>{const q=db.transaction(name).objectStore(name).getAll();q.onsuccess=()=>ok(q.result);});out.push(JSON.stringify(all));}db.close();}return out.join('\n');});
   // Stored records carry ISO times (effective_at, available_at, as_of); a time at hh:mm:52.1xx would read as the score 52.1, so
   // times are masked before the value check (a wall-clock false positive, not a leak).
   assert.equal(/implied|reverse_dcf|fundamental_value|margin_of_safety|explicit_growth|135\.02|52\.1|0\.0081|v1\+dcf/.test(stored.replace(/\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?(?:Z|[+-]\d{2}:\d{2})/g,'<time>')),false,'nothing price-derived in device storage');
   assert.equal(errors,0);pass++;console.log('PASS dcf value view '+width);
  }catch(e){fail++;console.log('FAIL dcf value view '+width+' '+phase+' '+String(e.message).split('\n')[0]);}finally{await context.close();}
 }}finally{await browser.close();}
 console.log('COUNTS pass='+pass+' fail='+fail);process.exitCode=fail?1:0;})();
