'use strict';
// S16 13F manager names, style badges/panel, style filter and limitation text; synthetic route-intercepted payload only.
const {chromium}=require('playwright'),assert=require('node:assert/strict');
const H=c=>c.repeat(64);
function payload(){const at=new Date().toISOString(),change=(cusip,a,b,kind)=>({cusip,security_key:H('c'),unit:'SH',kind,reported_before:a,reported_after:b,reported_delta:b-a});
 const report=(cik,changes)=>({manager_cik:cik,previous_quarter:'2026-03-31',current_quarter:'2026-06-30',state:'LIVE',source_hashes:{previous:H('a'),current:H('b')},changes});
 const verified=(id,cik,name,extra={})=>({id,cik,state:'VERIFIED',reason_code:null,matched_name:name,verified_at:at,latest_13f_accession:'0000000000-26-000001',capture_reason:null,comparison_reasons:[],...extra});
 const na=(id,cik,reason)=>({id,cik,state:'NOT_AVAILABLE',reason_code:reason,matched_name:null,verified_at:null,latest_13f_accession:null,capture_reason:null,comparison_reasons:[]});
 return {schema_version:1,kind:'SEC_13F',as_of:at,state:'LIVE',sources:[{agency:'SEC_13F',sha256:H('a'),acquired_at:at},{agency:'SEC_13F',sha256:H('b'),acquired_at:at}],reason_codes:[],freshness_basis:'SOURCE_ACQUISITION',stale_after_seconds:86400*120,
  data:{role:'REPORTED_QUANTITY_CHANGE_NOT_TRADES',reports:[report('0001067983',[change('A00000000',0,5,'NEW'),change('B00000000',4,0,'EXIT')]),report('0001135730',[change('A00000000',2,3,'ADD')])],
   managers:[verified('berkshire_hathaway','0001067983','SYNTHETIC NAME ONE'),verified('coatue_management','0001135730','SYNTHETIC NAME TWO'),na('tiger_global','0001167483','NAME_MISMATCH'),verified('renaissance_technologies','0001037389','SYNTHETIC NAME THREE',{capture_reason:'PUBLIC_SIZE_LIMIT'})]}};}
const noScroll=page=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1);
const configIds=page=>page.locator('[data-13f-config-manager]').evaluateAll(n=>n.map(x=>x.dataset['13fConfigManager']));
(async()=>{const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_EXECUTABLE_PATH});let phase='START',pass=0,fail=0;
 try{for(const width of [390,1280]){const mobile=width===390,context=await browser.newContext({viewport:{width,height:900},serviceWorkers:'block',hasTouch:mobile,isMobile:mobile});
  await context.route('**/sec-13f-changes.json',r=>r.fulfill({status:200,contentType:'application/json',body:JSON.stringify(payload())}));
  const page=await context.newPage();let errors=0;page.on('pageerror',()=>errors++);
  try{phase='LOAD';await page.goto(process.env.PAGES_COCKPIT_URL+'#thirteenf');await page.waitForLoadState('networkidle');await page.locator('[data-13f-config-manager]').first().waitFor();
   assert.equal(await page.locator('[data-13f-config-manager]').count(),10);
   const berkshire=page.locator('[data-13f-config-manager="berkshire_hathaway"]');
   assert.equal(await berkshire.locator('h3').textContent(),'Berkshire Hathaway');assert.equal(await berkshire.getAttribute('data-13f-manager'),'0001067983');
   assert.equal(await page.locator('h3',{hasText:/^0001067983$/}).count(),0);
   assert.ok((await berkshire.locator('[data-13f-verified]').textContent()).includes('SEC 확인'));assert.deepEqual(await berkshire.locator('[data-13f-kind-chips] [data-13f-kind]').allTextContents(),['신규 1','추가 0','축소 0','전량매도 1']);assert.ok((await berkshire.locator('[data-13f-period]').textContent()).includes('2026-03-31 → 2026-06-30'));assert.ok((await berkshire.locator('[data-13f-filed]').textContent()).includes('NOT_AVAILABLE · FILING_DATE_NOT_PUBLISHED'));
   phase='BADGES';for(const id of await configIds(page)){const badge=page.locator(`[data-13f-config-manager="${id}"] [data-style-badge]`).first();assert.ok(await badge.isVisible(),id);}
   assert.equal(await berkshire.locator('[data-style-badge="value"]').textContent(),'가치');
   assert.equal(await page.locator('[data-13f-config-manager="renaissance_technologies"] [data-style-badge="quant"]').textContent(),'퀀트');
   assert.ok((await page.locator('[data-13f-style-label]').textContent()).includes('일반적 평가 기반 v0 분류'));
   phase='NA';const tiger=await page.locator('[data-13f-unverified="tiger_global"]').textContent();assert.ok(tiger.startsWith('NOT_AVAILABLE · NAME_MISMATCH'));
   assert.ok((await page.locator('[data-13f-unverified="baupost_group"]').textContent()).includes('VERIFICATION_NOT_RUN'));assert.equal(await page.locator('[data-13f-config-manager="tiger_global"] [data-13f-manager]').count(),0);
   assert.ok((await page.locator('[data-13f-comparison="renaissance_technologies"]').textContent()).includes('PUBLIC_SIZE_LIMIT'));assert.ok(await page.locator('[data-13f-reference="renaissance_technologies"]').isVisible());
   phase='LIMITS';const limits=await page.locator('[data-13f-limits]').textContent();for(const t of ['분기 종료 후 최대 45일','미국 상장 주식(13F 대상 증권)','매수 포지션만','퀀트·매크로 기관은','참고용'])assert.ok(limits.includes(t),t);
   phase='TAP';const badge=berkshire.locator('[data-style-badge="value"]'),panel=page.locator('[data-style-panel="berkshire_hathaway"]');
   assert.equal(await badge.getAttribute('aria-controls'),await panel.getAttribute('id'));assert.equal(await panel.isVisible(),false);
   if(mobile)await badge.tap();else await badge.click();await panel.waitFor({state:'visible'});assert.equal(await badge.getAttribute('aria-expanded'),'true');
   assert.ok((await panel.textContent()).includes('가치 투자'));assert.ok((await panel.textContent()).includes('일반적 평가 기반 v0 분류'));assert.ok(await noScroll(page));
   await page.keyboard.press('Escape');if(!mobile)await page.mouse.move(0,0);await panel.waitFor({state:'hidden'});assert.equal(await badge.getAttribute('aria-expanded'),'false');
   const info=berkshire.locator('[data-style-info]');if(mobile)await info.tap();else await info.click();await panel.waitFor({state:'visible'});assert.equal(await info.getAttribute('aria-expanded'),'true');
   if(mobile)await info.tap();else await info.click();if(!mobile)await page.mouse.move(0,0);await panel.waitFor({state:'hidden'});
   if(!mobile){phase='HOVER';const coatue=page.locator('[data-13f-config-manager="coatue_management"]'),cp=page.locator('[data-style-panel="coatue_management"]');
    await coatue.locator('[data-style-badge="growth_tech"]').hover();await cp.waitFor({state:'visible'});assert.ok((await cp.textContent()).includes('기술·성장'));assert.ok(await noScroll(page));
    await page.mouse.move(0,0);await cp.waitFor({state:'hidden'});}
   phase='FILTER';await page.locator('[data-13f-style="growth_tech"]').click();await page.locator('[data-13f-style="growth_tech"][aria-pressed="true"]').waitFor();
   assert.deepEqual(await configIds(page),['coatue_management','tiger_global']);
   await page.locator('[data-13f-style="quant"]').click();await page.locator('[data-13f-style="quant"][aria-pressed="true"]').waitFor();
   assert.deepEqual(await configIds(page),['coatue_management','tiger_global','renaissance_technologies']);
   await page.locator('[data-13f-style="growth_tech"]').click();await page.locator('[data-13f-style="growth_tech"][aria-pressed="false"]').waitFor();assert.deepEqual(await configIds(page),['renaissance_technologies']);
   await page.locator('[data-13f-style-all]').click();await page.locator('[data-13f-style-all][aria-pressed="true"]').waitFor();assert.equal(await page.locator('[data-13f-config-manager]').count(),10);
   phase='STAR';await page.locator('[data-investor-star="0001135730"]').click();await page.locator('[data-investor-star="0001135730"][aria-pressed="true"]').waitFor();assert.equal((await configIds(page))[0],'coatue_management');
   phase='SECURITY';await page.locator('[data-13f-view="security"]').click();await page.locator('[data-13f-security]').first().waitFor();assert.ok((await page.locator('[data-13f-security="A00000000"]').textContent()).includes('Berkshire Hathaway · NEW'));
   phase='EN';await page.evaluate(()=>localStorage.setItem(AppLanguage.KEY,JSON.stringify({version:1,display_locale:'en-US',source_language:'all'})));await page.reload();await page.locator('[data-13f-config-manager]').first().waitFor();
   const en=await page.locator('[data-13f-limits]').textContent();for(const t of ['45 days after quarter end','long positions in US-listed equities (13F securities)','Quant and macro managers are reference only'])assert.ok(en.includes(t),t);
   assert.ok((await page.locator('[data-13f-style-label]').textContent()).includes('v0 classification'));assert.equal(await page.locator('[data-13f-config-manager="berkshire_hathaway"] [data-style-badge="value"]').textContent(),'Value');
   assert.ok(await noScroll(page));assert.equal(errors,0);pass++;console.log('PASS 13F manager styles badges filter limits '+width);
  }catch(e){fail++;console.log('FAIL 13F managers '+width+' '+phase+' '+(e.code==='ERR_ASSERTION'?'CONTRACT':'EXECUTION'));if(process.env.DEBUG_13F)console.log(e);}finally{await context.close();}}}
 finally{await browser.close();}console.log('COUNTS pass='+pass+' fail='+fail);process.exitCode=fail?1:0;})();
