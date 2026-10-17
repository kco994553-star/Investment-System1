'use strict';
// S16 13F quarter changes for TARGET companies and S13 custom company types (official vs '내 설정 미리보기').
// Synthetic, schema-valid public payloads by route interception only: reported quantities and metrics are invented;
// the CUSIPs are the public TARGET identifiers derived from actual-catalog.json ISINs. No prices or personal data.
const {chromium}=require('playwright'),assert=require('node:assert/strict');
const IDS=['asml','lrcx','klac','tokyo_electron','hanmi','nvda','amd','avgo','qcom','intc','msft','googl','amzn','rtx','stry','etn','hubb','gev','rok'];
const H=c=>c.repeat(64),NVDA='67066G104',MSFT='594918104',AMZN='023135106';
function thirteenF(){const at=new Date().toISOString(),change=(cusip,a,b,key='c')=>({cusip,security_key:H(key),unit:'SH',kind:a===0?'NEW':b===0?'EXIT':b>a?'ADD':'REDUCE',reported_before:a,reported_after:b,reported_delta:b-a});
 const report=(cik,changes,state='LIVE')=>({manager_cik:cik,previous_quarter:'2026-03-31',current_quarter:'2026-06-30',state,source_hashes:{previous:H('a'),current:H('b')},changes});
 const verified=(id,cik,name,extra={})=>({id,cik,state:'VERIFIED',reason_code:null,matched_name:name,verified_at:at,latest_13f_accession:'0000000000-26-000001',capture_reason:null,comparison_reasons:[],...extra});
 return {schema_version:1,kind:'SEC_13F',as_of:at,state:'LIVE',sources:[{agency:'SEC_13F',sha256:H('a'),acquired_at:at},{agency:'SEC_13F',sha256:H('b'),acquired_at:at}],reason_codes:[],freshness_basis:'SOURCE_ACQUISITION',stale_after_seconds:86400*120,
  data:{role:'REPORTED_QUANTITY_CHANGE_NOT_TRADES',reports:[report('0001067983',[change(NVDA,1000,2500),change(NVDA,0,300,'d'),change(MSFT,40,0),change('Z99999995',5,0),change('A00000009',0,7)]),report('0001135730',[],'NOT_AVAILABLE'),report('0001167483',[change(AMZN,10,4)])],
   managers:[verified('berkshire_hathaway','0001067983','SYNTHETIC NAME ONE'),verified('coatue_management','0001135730','SYNTHETIC NAME TWO',{comparison_reasons:['SYNTHETIC_REASON']}),verified('tiger_global','0001167483','SYNTHETIC NAME THREE')]}};}
function types(){const at=new Date().toISOString(),a=H('a'),b=H('b'),companies={};for(const id of IDS)companies[id]={state:'NOT_AVAILABLE',source_hashes:{},memberships:{growth:null,quality:null,cyclical:null,defensive:null},config_version:null,metrics:{revenue_cagr_3y:null,roic:null}};
 const live=(g,r)=>({state:'LIVE',source_hashes:{companyfacts:a,submissions:b},memberships:{growth:1,quality:null,cyclical:null,defensive:null},config_version:'type_config/1',metrics:{revenue_cagr_3y:g,roic:r}});
 companies.nvda=live(0.25,0.4);companies.amd=live(0.12,null);
 return {schema_version:1,kind:'COMPANY_TYPES_PRICEFREE',as_of:at,state:'LIVE',sources:[{agency:'SEC_COMPANYFACTS',sha256:a,acquired_at:at},{agency:'SEC_SUBMISSIONS',sha256:b,acquired_at:at}],reason_codes:[],freshness_basis:'SOURCE_ACQUISITION',stale_after_seconds:86400,data:{companies,method_status:'PROVISIONAL_UNCALIBRATED',availability_basis:'OBSERVED_CAPTURE_ONLY'}};}
const noScroll=page=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1);
const texts=(page,sel)=>page.locator(sel).evaluateAll(n=>n.map(r=>[...r.cells].map(c=>c.textContent)));
(async()=>{const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_EXECUTABLE_PATH});let phase='START',pass=0,fail=0;
 try{for(const width of [390,1280]){const pc=width>=1024,context=await browser.newContext({viewport:{width,height:900},serviceWorkers:'block'});
  await context.route('**/sec-13f-changes.json*',r=>r.fulfill({status:200,contentType:'application/json',body:JSON.stringify(thirteenF())}));
  await context.route('**/company-types-pricefree.json*',r=>r.fulfill({status:200,contentType:'application/json',body:JSON.stringify(types())}));
  const page=await context.newPage();let errors=0;page.on('pageerror',()=>errors++);
  try{phase='S16_LOAD';await page.goto(process.env.PAGES_COCKPIT_URL+'#thirteenf');await page.locator('[data-13f-target-table="0001067983"]').waitFor();
   const b=page.locator('[data-13f-config-manager="berkshire_hathaway"]');
   assert.ok((await b.locator('[data-13f-period]').textContent()).includes('2026-03-31 → 2026-06-30'));
   assert.ok((await b.locator('[data-13f-filed]').textContent()).includes('NOT_AVAILABLE · FILING_DATE_NOT_PUBLISHED'));
   assert.equal(await b.locator('[data-13f-cell="NEW"]').textContent(),'2');assert.equal(await b.locator('[data-13f-cell="EXIT"]').textContent(),'2');
   assert.equal(await b.locator('[data-13f-cell="top10"]').textContent(),'NOT_AVAILABLE');assert.equal(await b.locator('[data-13f-cell="holdings"]').textContent(),'NOT_AVAILABLE');
   const why=await b.locator('[data-13f-cell-reasons]').textContent();assert.ok(why.includes('REPORTED_VALUES_NOT_PUBLISHED')&&why.includes('UNCHANGED_POSITIONS_NOT_PUBLISHED'));
   phase='S16_TARGET';const rows=await texts(page,'[data-13f-target-table="0001067983"] tbody tr');
   assert.deepEqual(rows.map(r=>[r[0],r[1]]).sort(),[['MSFT','전량매도'],['NVDA','신규'],['NVDA','추가']]);
   const add=rows.find(r=>r[1]==='추가');assert.equal(add[2],'1,000 → 2,500 SH');assert.equal(add[3],'+1,500');assert.equal(rows.find(r=>r[0]==='MSFT')[3],'−40');
   assert.ok(await b.locator('[data-13f-multi]').isVisible());
   assert.ok((await b.locator('[data-13f-target-na="NOT_13F_SECURITY"]').textContent()).includes('도쿄일렉트론')||(await b.locator('[data-13f-target-na="NOT_13F_SECURITY"]').textContent()).includes('Tokyo Electron'));
   assert.ok((await b.locator('[data-13f-target-quiet]').textContent()).includes('ETN'));
   assert.ok((await b.locator('[data-13f-target-quiet]').textContent()).includes('ASML'));
   phase='S16_OTHER';await b.locator('[data-13f-other] summary').click();assert.deepEqual((await texts(page,'[data-13f-other-table="0001067983"] tbody tr')).map(r=>r[0]),['A00000009','Z99999995']);
   assert.ok((await b.locator('[data-13f-other]').textContent()).includes('ISSUER_NAME_NOT_PUBLISHED'));
   phase='S16_NA';const coatue=page.locator('[data-13f-config-manager="coatue_management"]');assert.ok((await coatue.locator('[data-13f-target-na="COMPARISON_NOT_AVAILABLE"]').textContent()).includes('NVDA'));
   assert.ok((await coatue.locator('[data-13f-comparison]').textContent()).includes('SYNTHETIC_REASON'));
   const text=await page.locator('[data-public-screen="thirteenf"]').textContent();assert.ok(!/\$|USD|평가액|price/i.test(text.replace(/USD_?/g,'')),'no amounts');
   if(pc){phase='S16_SORT';const table=page.locator('[data-13f-target-table="0001067983"]');await page.waitForFunction(()=>document.querySelector('[data-13f-target-table="0001067983"]').hasAttribute('data-table-sort'));
    await table.locator('[data-sort-col="3"]').click();assert.deepEqual((await texts(page,'[data-13f-target-table="0001067983"] tbody tr')).map(r=>r[3]),['−40','+300','+1,500']);
    await table.locator('[data-sort-col="3"]').click();assert.deepEqual((await texts(page,'[data-13f-target-table="0001067983"] tbody tr')).map(r=>r[3]),['+1,500','+300','−40']);}
   phase='S16_OVERLAP';await page.evaluate(()=>localStorage.setItem('investment.web.v1.personal',JSON.stringify({version:1,interests:['nvda','asml'],groups:[]})));await page.reload();
   await page.locator('[data-13f-view="overlap"]').click();await page.locator('[data-13f-overlap-table]').waitFor();
   assert.equal(await page.locator('[data-13f-overlap-target]').getAttribute('data-13f-overlap-target'),'3');assert.equal(await page.locator('[data-13f-overlap-watch]').getAttribute('data-13f-overlap-watch'),'1');
   const nvda=await texts(page,'[data-13f-overlap-row="nvda"]');assert.equal(nvda.length,2);assert.ok(nvda.every(r=>r[0]==='★ NVDA'&&r[1]==='Berkshire Hathaway'));
   assert.ok((await page.locator('[data-13f-overlap-row="amzn"]').textContent()).includes('Tiger Global'));
   assert.ok((await page.locator('[data-13f-overlap-row="hanmi"]').textContent()).includes('NOT_13F_SECURITY'));assert.ok((await page.locator('[data-13f-overlap-row="asml"]').textContent()).includes('보고 변화 없음'));
   assert.ok(await noScroll(page));
   phase='S16_STORAGE';assert.deepEqual(await page.evaluate(()=>Object.keys(localStorage).filter(k=>/13f|thirteen|cusip/i.test(k))),[]);
   phase='S13_OFFICIAL';await page.goto(process.env.PAGES_COCKPIT_URL+'#types');await page.locator('[data-type-official-table]').waitFor();
   assert.equal(await page.locator('[data-type-official-row]').count(),9);assert.equal(await page.locator('[data-type-panel="mine"]').isVisible(),false);
   assert.equal(await page.locator('[data-type-view="official"]').getAttribute('aria-selected'),'true');assert.ok((await page.locator('[data-type-official-row="growth"]').textContent()).includes('3년 매출 성장률 0.1–0.2'));assert.ok(!(await page.locator('[data-type-official]').textContent()).includes('revenue_cagr_3y'),'metric id not on screen');
   const officialBefore=await page.evaluate(()=>JSON.stringify(TypeConfigDefaults));
   phase='S13_COPY';await page.locator('#type-copy').click();await page.locator('[data-type-panel="mine"]').waitFor();
   assert.equal(await page.locator('[data-type-custom-badge=""]').textContent(),'사용자 설정 · 공식 아님');assert.equal(await page.locator('[data-type-panel="official"]').isVisible(),false);
   await page.fill('#type-growth-lower','0.3');await page.fill('#type-growth-upper','0.4');await page.locator('#type-preview').click();await page.locator('[data-type-preview-row="nvda"]').waitFor();
   const n=(await texts(page,'[data-type-preview-row="nvda"]'))[0];assert.equal(n[1],'성장');assert.equal(n[2],'미분류');assert.ok(n[5].startsWith('유형 변경'));
   assert.deepEqual(await page.locator('[data-type-diff-path]').evaluateAll(x=>x.map(e=>e.dataset.typeDiffPath)),['types.growth.rule.lower','types.growth.rule.upper']);
   assert.equal(await page.locator('[data-type-preview-state="PREVIEW"]').count(),2);assert.equal(await page.locator('[data-type-preview-row]').count(),19);
   assert.ok((await page.locator('[data-type-custom-badge="preview"]').textContent()).includes('공식 아님'));
   if(pc)await page.waitForFunction(()=>document.querySelector('[data-type-preview-table]').hasAttribute('data-table-sort'));
   phase='S13_RESET';await page.locator('#type-reset').click();assert.equal(await page.inputValue('#type-growth-lower'),'0.1');assert.equal(await page.locator('[data-type-preview-row]').count(),0);
   await page.locator('#type-preview').click();await page.locator('[data-type-diff-none]').waitFor();assert.ok((await texts(page,'[data-type-preview-row="nvda"]'))[0][5].includes('같음'));
   phase='S13_SAVE';await page.fill('#type-growth-Q','40');await page.fill('#type-growth-G','40');await page.locator('#type-preview').click();await page.locator('[data-type-preview-row="nvda"]').waitFor();await page.locator('#type-save').click();
   assert.equal(await page.evaluate(()=>JSON.stringify(TypeConfigDefaults)),officialBefore);
   const backup=await page.evaluate(async()=>{const catalog=await(await fetch('actual-catalog.json')).json(),b=await DeviceBackup.read(window,catalog);return {n:b.profiles.types.length,status:b.profiles.types[0].config.status,q:b.profiles.types[0].config.types[0].weights.Q};});
   assert.deepEqual(backup,{n:1,status:'CUSTOM_PREVIEW',q:40});
   assert.ok(!(await page.evaluate(()=>JSON.stringify(localStorage))).includes('weight_delta'),'preview results stay in RAM');
   phase='S13_OFFICIAL_UNCHANGED';await page.reload();await page.locator('[data-type-official-row="growth"]').waitFor();const g=(await texts(page,'[data-type-official-row="growth"]'))[0];assert.deepEqual(g.slice(2),['30','50','20']);
   assert.ok(await noScroll(page));assert.equal(errors,0);pass++;console.log('PASS S16 13F quarter changes and S13 custom types '+width);
  }catch(e){fail++;console.log('FAIL S16/S13 '+width+' '+phase+' '+(e.code==='ERR_ASSERTION'?'CONTRACT':'EXECUTION'));if(process.env.DEBUG_S16)console.log(e);}finally{await context.close();}}}
 finally{await browser.close();}console.log('COUNTS pass='+pass+' fail='+fail);process.exitCode=fail?1:0;})();
