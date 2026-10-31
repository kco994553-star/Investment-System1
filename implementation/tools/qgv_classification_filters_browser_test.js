'use strict';
// Real app controls with synthetic public publications: the strictly valid synthetic sec-qgv2.json and the synthetic central V
// publication (qgv_official_fixture.js; DC-31: screens show only the central V, no Universe read, no price).
// Optional proposal overlay is for a worker review BEFORE Main integrates the app hooks; CI uses served assets normally.
const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {routeEmptyPublicScreens}=require('./empty_public_screens.js'),F=require('./qgv_v2_fixture.js'),O=require('./qgv_official_fixture.js');
const W=path.join(__dirname,'../src/investment_system/product/web_assets'),BASE=process.env.PAGES_COCKPIT_URL,ORIGIN=new URL(BASE).origin;
const CLASS=require('../tests/fixtures/company_classification_v0_payloads.json').live,CS=require(path.join(W,'classification-screens.js'));
function classification(day){const p=structuredClone(CLASS);if(day===1){p.data.companies.gev.industry={...structuredClone(p.data.companies.nvda.industry),sic:'4900',group:'utilities',subgroup:null};}
 else p.as_of='2026-10-12T00:00:00+00:00';return CS.validate(p);}
function types(){const at='2026-10-13T12:00:00Z',companies=Object.fromEntries(Object.keys(CLASS.data.companies).map(id=>[id,{state:'NOT_AVAILABLE',config_version:null,source_hashes:{},memberships:{growth:null,quality:null,cyclical:null,defensive:null}}]));
 companies.nvda={state:'LIVE',config_version:'type_config/1',source_hashes:{companyfacts:'a'.repeat(64),submissions:'b'.repeat(64)},memberships:{growth:.8,quality:.35,cyclical:null,defensive:null}};
 companies.amd={...structuredClone(companies.nvda),memberships:{growth:.1,quality:.1,cyclical:null,defensive:null}};
 return {schema_version:1,kind:'COMPANY_TYPES_PRICEFREE',as_of:at,state:'LIVE',sources:[{agency:'SEC_COMPANYFACTS',sha256:'a'.repeat(64),acquired_at:at},{agency:'SEC_SUBMISSIONS',sha256:'b'.repeat(64),acquired_at:at}],reason_codes:[],freshness_basis:'SOURCE_ACQUISITION',stale_after_seconds:86400,data:{companies,method_status:'PROVISIONAL_UNCALIBRATED',availability_basis:'OBSERVED_CAPTURE_ONLY'}};
}
const ids=page=>page.locator('[data-leaderboard-row]').evaluateAll(rs=>rs.map(r=>r.dataset.leaderboardRow));
// L3: each shown row's published SIC (row attribute), official rank cell and the visible SIC text (wide: SIC column; phone: company cell).
const rowsInfo=page=>page.locator('[data-leaderboard-row]').evaluateAll(rs=>rs.map(r=>({id:r.dataset.leaderboardRow,sic:r.dataset.leaderboardSic,rank:r.querySelector('[data-leaderboard-rank]')?.dataset.leaderboardRank||null,
 cell:r.querySelector('[data-leaderboard-sic-cell]')?.textContent??null,code:r.querySelector('[data-leaderboard-sic-code]')?.textContent??null})));
async function settle(page){await page.waitForFunction(()=>QgvScores.pagePublication().publication&&leaderScores()&&leaderPage&&leaderPage.source==='PUBLICATION');}
async function official(page){return page.evaluate(()=>{const S=leaderScores(),pop=officialPopulation();return {scores:S,model:QgvScores.officialModel({identities:pop.official.identities,v2Inputs:publicScreens[Qgv2Inputs.FILE],quotes:{},official:pop.official,computed:S})};});}
(async()=>{const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_EXECUTABLE_PATH});let checks=0,phase='START';
 try{for(const width of [390,1280])for(const locale of ['ko-KR','en-US']){
  const context=await browser.newContext({viewport:{width,height:900},serviceWorkers:'block'}),served={day:1,fail:false};let external=0;const errors=[];
  await context.route('**/*',r=>{if(new URL(r.request().url()).origin!==ORIGIN){external++;return r.abort();}return r.continue();});
  await routeEmptyPublicScreens(context);
  await context.route('**/sec-qgv2.json*',r=>r.fulfill({status:200,contentType:'application/json',body:JSON.stringify(F.strictPayload())}));
  await context.route('**/company-classification.json*',r=>r.fulfill(served.fail?{status:503,body:'synthetic unavailable'}:{status:200,contentType:'application/json',body:JSON.stringify(classification(served.day))}));
  await O.routeOfficial(context);
  await context.route('**/company-types-pricefree.json*',r=>r.fulfill({status:200,contentType:'application/json',body:JSON.stringify(types())}));
  if(process.env.QGV_FILTERS_PROPOSAL_APP){await context.route('**/app.js',r=>r.fulfill({path:process.env.QGV_FILTERS_PROPOSAL_APP,contentType:'text/javascript'}));
   for(const name of ['leaderboard-screen.js','portfolio-screen.js'])await context.route('**/'+name,r=>r.fulfill({path:path.join(W,name),contentType:'text/javascript'}));}
  const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));await page.clock.install({time:new Date('2026-10-13T12:00:00Z')});
  try{
   phase=width+' '+locale+' setup';await page.goto(BASE+'#settings');await page.locator('[data-universe-source]').waitFor();
   if(locale==='en-US'){await page.locator('#display-locale').selectOption(locale);await page.waitForFunction(()=>appSettings.display_locale==='en-US');}
   await page.evaluate(()=>{location.hash='leaderboard';});
   await page.locator('[data-leaderboard-table]').waitFor();await settle(page);
   await page.locator('[data-leaderboard-rank]').first().waitFor();const before=await official(page);assert.equal(before.scores.official.codes,504);assert.ok(before.model.sets.N20.selected.length);checks++;
   const industry=page.locator('#leader-classification-industry'),type=page.locator('#leader-classification-type');
   assert.equal(await industry.count(),1);assert.equal(await type.count(),1);assert.match(await page.locator('[data-classification-note]').textContent(),locale==='en-US'?/separate axes/:/서로 다른 축/);checks++;
   phase=width+' '+locale+' intersect';await page.locator('#leader-target').check();await industry.selectOption('manufacturing_industrial_tech');await type.selectOption('growth');assert.deepEqual(await ids(page),['nvda']);assert.deepEqual(await official(page),before);checks++;
   assert.match(await page.locator('#leader-summary').textContent(),locale==='en-US'?/Company type.*Growth/:/기업 유형.*성장/);checks++;
   await page.locator('#leader-query').fill('AMD');assert.deepEqual(await ids(page),[]);await page.locator('#leader-query').fill('');assert.deepEqual(await ids(page),['nvda']);checks++;
   await type.selectOption('NO_SELECTED_TYPE');assert.deepEqual(await ids(page),['amd']);assert.deepEqual(await official(page),before);checks++;
   await page.locator('#leader-target').uncheck();await industry.selectOption('');await type.selectOption('NOT_AVAILABLE');assert.ok(!(await ids(page)).includes('amd'));assert.ok((await ids(page)).length>400);assert.deepEqual(await official(page),before);checks++;
   phase=width+' '+locale+' sic';await type.selectOption('');const sic2=page.locator('#leader-classification-sic2'),sic4=page.locator('#leader-classification-sic4');
   for(const s of [sic2,sic4]){assert.equal(await s.count(),1);const b=await s.boundingBox();assert.ok(b&&b.height>=44&&b.width>=44,'SIC control is at least 44px');assert.equal(await page.locator('label[for="'+await s.getAttribute('id')+'"]').count(),1);}checks++;
   const all=await rowsInfo(page),sicOf=Object.fromEntries(all.map(r=>[r.id,r.sic])),rankOf=Object.fromEntries(all.map(r=>[r.id,r.rank]));
   assert.equal(all.length,504);assert.equal(sicOf.nvda,'3674');assert.equal(sicOf.amd,'3674');assert.equal(sicOf.gev,'4900');assert.ok(all.every(r=>r.sic==='NOT_AVAILABLE'||/^\d{4}$/.test(r.sic)));
   const missing=all.filter(r=>r.sic==='NOT_AVAILABLE');assert.ok(missing.length>400&&missing.length<all.length,'synthetic data has rows without a published SIC');
   assert.equal(await page.locator('[data-leaderboard-table] th[data-leaderboard-col="sic"]').count(),width<750?0:1);
   for(const r of all)if(width<750){assert.equal(r.cell,null);assert.equal(r.code,r.sic==='NOT_AVAILABLE'?null:' · SIC '+r.sic,'phone: code in the company cell, nothing invented when missing');}
    else{assert.equal(r.code,null);assert.equal(r.cell,r.sic==='NOT_AVAILABLE'?'—':r.sic,'missing SIC is —, never 0 or another class');}checks++;
   await sic4.selectOption('3674');const want=all.filter(r=>r.sic==='3674').map(r=>r.id);assert.ok(want.includes('nvda')&&want.includes('amd'));assert.deepEqual(await ids(page),want);
   for(const r of await rowsInfo(page))assert.equal(r.rank,rankOf[r.id],'official rank number unchanged under a SIC filter');assert.deepEqual(await official(page),before);
   assert.match(await page.locator('#leader-summary').textContent(),locale==='en-US'?/SIC 4-digit: 3674/:/SIC 4자리: 3674/);checks++;
   await sic4.selectOption('');await sic2.selectOption('36');assert.deepEqual(await ids(page),all.filter(r=>r.sic.startsWith('36')).map(r=>r.id));
   assert.ok((await rowsInfo(page)).every(r=>r.sic!=='NOT_AVAILABLE'&&r.rank===rankOf[r.id]),'missing-SIC rows are never shown under a SIC code');
   await sic4.selectOption('7372');assert.deepEqual(await ids(page),[],'2-digit and 4-digit intersect');await sic2.selectOption('');assert.deepEqual(await ids(page),all.filter(r=>r.sic==='7372').map(r=>r.id));
   await sic4.selectOption('NOT_AVAILABLE');assert.deepEqual(await ids(page),missing.map(r=>r.id));assert.ok((await rowsInfo(page)).every(r=>r.sic==='NOT_AVAILABLE'&&r.code===null&&(width<750||r.cell==='—')),'never relabeled');
   assert.deepEqual(await official(page),before);await sic4.selectOption('');assert.equal((await ids(page)).length,504);checks++;
   phase=width+' '+locale+' sic+industry';await industry.selectOption('utilities');assert.deepEqual(await ids(page),['gev']);await sic4.selectOption('4900');assert.deepEqual(await ids(page),['gev']);checks++;
   phase=width+' '+locale+' refresh';served.day=2;await page.locator('[data-refresh-button]').click();await page.waitForFunction(()=>DataRefresh.last().state==='APPLIED');await settle(page);
   assert.equal(await industry.inputValue(),'utilities');assert.deepEqual(await ids(page),[]);assert.match(await industry.locator('option:checked').textContent(),locale==='en-US'?/absent.*publication/:/새 게시본에 없음/);assert.deepEqual(await official(page),before);checks++;
   assert.equal(await sic4.inputValue(),'4900','a SIC code absent from the new publication stays selected (no silent broadening)');assert.match(await sic4.locator('option:checked').textContent(),locale==='en-US'?/SIC 4900 absent.*publication/:/SIC 4900.*새 게시본에 없음/);checks++;
   phase=width+' '+locale+' failure';served.day=1;served.fail=true;await page.locator('[data-refresh-button]').click();await page.waitForFunction(()=>DataRefresh.last().state==='FAILED');
   assert.equal(await industry.inputValue(),'utilities');assert.equal(await sic4.inputValue(),'4900');assert.deepEqual(await ids(page),[]);assert.deepEqual(await official(page),before);checks++;
   phase=width+' '+locale+' rejudge';await page.clock.setSystemTime(new Date('2026-10-29T00:00:00Z'));await page.evaluate(()=>DataRefresh.rejudge('VISIBLE'));await settle(page);
   assert.equal(await industry.inputValue(),'utilities');assert.equal(await sic4.inputValue(),'4900');assert.deepEqual(await ids(page),[]);checks++;
   phase=width+' '+locale+' navigation';await page.evaluate(()=>location.hash='portfolio');await page.locator('[data-model-candidates]').waitFor();
   const model=await page.locator('[data-model-candidates]').textContent();assert.doesNotMatch(model,/생성기|no generator|no selector/i);assert.match(model,/N10[\s\S]*N15[\s\S]*N20/);assert.match(model,locale==='en-US'?/TARGET.*not finalized/:/TARGET 확정 결과는 (?:아닙니다|아니며)/);checks++;
   await page.locator('[data-model-candidates] a[href="#leaderboard"]').click();await industry.waitFor();await settle(page);assert.equal(await industry.inputValue(),'utilities');assert.equal(await sic4.inputValue(),'4900');assert.deepEqual(await ids(page),[]);checks++;
   await sic4.selectOption('');assert.deepEqual(await ids(page),[]);await industry.selectOption('');assert.equal((await ids(page)).length,504);assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));checks++;
   assert.equal(await page.evaluate(()=>Object.values(sessionStorage).some(v=>/classificationView|leader-classification/.test(v))),false);assert.deepEqual(errors,[]);assert.equal(external,0);checks++;
  }finally{await context.close();}
 }}catch(e){console.error('FAIL qgv classification '+phase+' '+e.message);process.exitCode=1;}finally{await browser.close();}
 if(!process.exitCode)console.log('QGV_CLASSIFICATION_FILTERS_BROWSER_OK checks='+checks);
})();
