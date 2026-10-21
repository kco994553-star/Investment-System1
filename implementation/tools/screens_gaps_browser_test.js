'use strict';
// S06 M3 rank (RAM only), company global search incl. Universe504 codes, backup-restored notice, SEC "수집 전" state,
// daily-run status card and home-screen install UX. Synthetic route fixtures only; nothing private is served or stored.
const {chromium}=require('playwright'),assert=require('node:assert/strict'),fixture=require('./sec_universe_shares_fixture.js'),{routeEmptyPublicScreens}=require('./empty_public_screens.js'),{fixture:secFixture}=require('./sec_reported_fixture.js');
const BASE=process.env.PAGES_COCKPIT_URL;
const ABC=['CommonClassAMember','CommonClassBMember','CommonClassCMember'];
const ROWS={'NASDAQ:ADBE':{n:1},'NASDAQ:AMD':{n:4,basis:'BASIS_UNCONFIRMED'},
 'NASDAQ:GOOGL':{n:1652044,basis:'SHARE_CLASS_BASIS',shares:5800,members:ABC,member:'CommonClassAMember',unlisted:[{class_member:'CommonClassBMember',shares:300}]},'NASDAQ:GOOG':{n:1652044,basis:'SHARE_CLASS_BASIS',shares:5400,members:ABC,member:'CommonClassCMember'}};
const VALUES=[['code','marketcap','price'],['NASDAQ:ADBE',10500,10],['NASDAQ:AMD',1,1],['NASDAQ:GOOGL',1735000,150],['NASDAQ:GOOG',1735000,151],...fixture.CODES.filter(c=>!ROWS[c]).slice(0,8).map(c=>[c,1,1])];
const overflow=page=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1);
(async()=>{const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_EXECUTABLE_PATH});let phase='START',pass=0,fail=0;
 try{for(const width of [390,1440]){
  const context=await browser.newContext({viewport:{width,height:900},serviceWorkers:'block'});await routeEmptyPublicScreens(context);const page=await context.newPage();page.setDefaultTimeout(15000);let errors=0,universe=true,sec=false;
  page.on('pageerror',()=>errors++);page.on('dialog',d=>d.accept());
  // Same-origin requests fall through to the empty public-data routes, so a daily-run build with live data behaves like a PR build.
  await page.route('**/*',r=>new URL(r.request().url()).origin===new URL(BASE).origin?r.fallback():r.abort());
  await page.route('**/sec-universe-shares.json',r=>universe?r.fulfill({status:200,contentType:'application/json',body:JSON.stringify(fixture.payload(ROWS))}):r.fulfill({status:404,body:''}));
  await page.route('**/sec-public-inputs.json',r=>sec?r.fulfill({status:200,contentType:'application/json',body:JSON.stringify(secFixture(3))}):r.fulfill({status:404,body:''}));

  phase='SEC_NOT_COLLECTED';await page.goto(BASE+'#leaderboard');await page.locator('[data-sec-unavailable="SEC_NOT_COLLECTED"]').waitFor();
  assert.equal(await page.locator('[data-sec-unavailable]').textContent(),'SEC 수집 전 · NOT_AVAILABLE');
  assert.equal(await page.locator('[data-leaderboard-m3-basis]').getAttribute('data-leaderboard-m3-basis'),'NOT_AVAILABLE');
  assert.ok((await page.locator('[data-leaderboard-m3-basis]').textContent()).startsWith('M3 · 내 기기 기준 · v0 · NOT_AVAILABLE'));
  assert.equal(await page.locator('[data-leaderboard-m3-rank]').count(),0);

  phase='M3_RANK';await page.goto(BASE+'#settings');await page.locator('[data-universe-source]').fill('u'.repeat(24));await page.locator('[data-universe-settings] button[type="submit"]').click();
  await page.evaluate(async values=>{await DeviceActual.sheetSettings(window,{schema:'device-google-sheet-settings/1',enabled:true,spreadsheet_id:'',range:'Quotes!A1:C22'});const listeners=new Set();
   const session={state:()=>({enabled:true,connected:true}),revision:()=>1,setEnabled(){},subscribe:f=>{listeners.add(f);return()=>listeners.delete(f);},async fetchValues(id,range){if(id!=='u'.repeat(24)||range!==PrivateSubsetView.RANGE)throw Error('READ_FAILED');return{values};}};
   window.GoogleSheetQuotes={...GoogleSheetQuotes,sessionFor:()=>session};location.hash='leaderboard';},VALUES);
  await page.locator('[data-leaderboard-view="device"]').click();const root=page.locator('[data-private-subset]');await root.locator('[data-subset-action="read"]:enabled').click();
  await page.locator('[data-leaderboard-row="googl"] [data-leaderboard-m3-rank="1"]').waitFor();
  assert.ok((await page.locator('[data-leaderboard-row="googl"] [data-leaderboard-m3-rank]').textContent()).includes('M3 #1'));
  assert.equal(await page.locator('[data-leaderboard-m3-basis]').getAttribute('data-leaderboard-m3-basis'),'READY');
  assert.ok((await page.locator('[data-leaderboard-m3-basis]').textContent()).includes('M3 · 내 기기 기준 · v0 · 검증 행만 · 부분'));
  assert.equal(await page.locator('[data-leaderboard-row="asml"] [data-leaderboard-m3]').getAttribute('data-reason'),'NOT_IN_UNIVERSE');
  const amd=await page.locator('[data-leaderboard-row="amd"] [data-leaderboard-m3]').getAttribute('data-reason');assert.ok(amd&&amd!=='NOT_IN_UNIVERSE'&&amd!=='UNIVERSE_NOT_READ',amd);
  assert.equal(await page.locator('[data-leaderboard-m3-rank]').count(),1);
  phase='M3_RAM';assert.equal(await page.evaluate(()=>{const s=JSON.stringify({...localStorage,...sessionStorage});return /M3 #|1730400|PERSONAL_REFERENCE|"rank"/.test(s);}),false);
  await root.locator('[data-subset-action="clear"]').click();await page.locator('[data-leaderboard-m3-basis="NOT_AVAILABLE"]').waitFor();assert.equal(await page.locator('[data-leaderboard-m3-rank]').count(),0);
  assert.ok(await overflow(page));

  phase='SEARCH';await page.goto(BASE+'#home');await page.locator('#global-search').fill('ADBE');await page.locator('#global-results [data-entity-id="COMPANY:NASDAQ:ADBE"]').waitFor();
  assert.equal(await page.locator('#global-results li').first().getAttribute('data-entity-scope'),'UNIVERSE504');
  await page.locator('#global-search').fill('GOOGL');assert.equal(await page.locator('#global-results li').first().getAttribute('data-entity-id'),'COMPANY:googl');assert.equal(await page.locator('#global-results [data-entity-id="COMPANY:NASDAQ:GOOGL"]').count(),0);
  await page.locator('#global-search').fill('adbe');await page.locator('#global-results li').first().locator('a').click();await page.locator('[data-universe-company="LIVE"]').waitFor();
  assert.equal(await page.locator('main h1').textContent(),'어도비 · ADBE');assert.ok(page.url().endsWith('#company/NASDAQ%3AADBE'));const detail=await page.locator('[data-universe-company]').textContent();assert.ok(detail.includes('NOT_AVAILABLE')&&!/\$|10500|R 10000/.test(detail));
  await page.goto(BASE+'#company/NASDAQ%3AZZZZ');await page.reload();await page.locator('[data-universe-company="NOT_AVAILABLE"]').waitFor();
  universe=false;await page.goto(BASE+'#home');await page.reload();await page.locator('#global-search').fill('ADBE');await page.waitForFunction(()=>document.querySelector('#global-results .empty'));
  await page.locator('#global-search').fill('NVDA');await page.locator('#global-results [data-entity-id="COMPANY:nvda"]').waitFor();await page.locator('#global-search').press('Escape');

  phase='RESTORE_NOTICE';await page.goto(BASE+'#settings');await page.locator('#device-backup-import').waitFor();assert.equal(await page.locator('[data-backup-restored]').count(),0);
  const backup=await page.evaluate(async()=>DeviceBackup.read(window,await (await fetch('actual-catalog.json')).json()));
  await page.locator('#device-backup-import').setInputFiles({name:'b.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(backup))});
  await page.locator('[data-backup-restored]').waitFor();assert.ok((await page.locator('[data-backup-restored]').textContent()).includes('백업에서 복원됨 · 시트 다시 읽기 필요'));
  await page.goto(BASE+'#actual');await page.locator('[data-backup-restored]').waitFor();await page.reload();await page.locator('[data-backup-restored]').waitFor();
  await page.locator('[data-backup-restored-dismiss]').click();assert.equal(await page.locator('[data-backup-restored]').count(),0);await page.goto(BASE+'#settings');await page.locator('#device-backup-import').waitFor();assert.equal(await page.locator('[data-backup-restored]').count(),0);
  assert.equal(await page.evaluate(()=>localStorage.getItem('investment.web.v1.backup-restored')),null);

  phase='DAILY_RUN';await page.locator('[data-daily-run]').waitFor();assert.equal(await page.locator('[data-daily-run]').getAttribute('data-daily-run'),'NOT_AVAILABLE');
  assert.ok((await page.locator('[data-daily-run-summary]').textContent()).includes('최근 일일 수집: NOT_AVAILABLE · SEC 수집 전'));assert.ok((await page.locator('[data-ops-row="sec-public-inputs.json"]').textContent()).includes('SEC_NOT_COLLECTED'));
  sec=true;await page.reload();await page.locator('[data-daily-run]').waitFor();const run=await page.locator('[data-daily-run]').getAttribute('data-daily-run');assert.ok(['SUCCESS','PARTIAL','FAILED'].includes(run),run);
  assert.ok(/최근 일일 수집: (성공|부분|실패)\(추정\) · 2026-01-02T12:00:00.000Z · \d+일 전/.test(await page.locator('[data-daily-run-summary]').textContent()));

  phase='PWA';const pwa=page.locator('#device-pwa-settings');assert.equal(await pwa.getAttribute('data-pwa-mode'),'manual');assert.ok(await pwa.locator('[data-pwa-install]').isHidden());assert.ok((await pwa.locator('[data-pwa-status]').textContent()).includes('홈 화면에 추가'));
  await page.evaluate(()=>{const e=new Event('beforeinstallprompt',{cancelable:true});e.prompt=async()=>{window.__prompted=(window.__prompted||0)+1;};e.userChoice=Promise.resolve({outcome:'accepted'});window.dispatchEvent(e);});
  assert.equal(await pwa.getAttribute('data-pwa-mode'),'prompt');assert.ok(await pwa.locator('[data-pwa-install]').isEnabled());await pwa.locator('[data-pwa-install]').click();
  await page.waitForFunction(()=>document.querySelector('#device-pwa-settings').dataset.pwaMode==='installed');assert.equal(await page.evaluate(()=>window.__prompted),1);assert.ok(await pwa.locator('[data-pwa-install]').isHidden());
  const manifest=await page.evaluate(async()=>(await fetch('manifest.json')).json());assert.equal(manifest.display,'standalone');assert.deepEqual(manifest.icons.map(i=>i.sizes),['192x192','512x512']);assert.equal(await page.locator('link[rel="apple-touch-icon"]').count(),1);
  assert.ok(await overflow(page));assert.equal(errors,0);await context.close();

  phase='PWA_IOS';const ios=await browser.newContext({viewport:{width,height:900},serviceWorkers:'block',userAgent:'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1'}),ip=await ios.newPage();
  await ip.route('**/*',r=>new URL(r.request().url()).origin===new URL(BASE).origin?r.continue():r.abort());await ip.goto(BASE+'#settings');await ip.locator('#device-pwa-settings[data-pwa-mode="ios"]').waitFor();
  assert.ok((await ip.locator('[data-pwa-status]').textContent()).includes('공유 버튼(□↑) → "홈 화면에 추가"'));assert.ok(await ip.locator('[data-pwa-install]').isHidden());await ios.close();
  pass++;console.log('PASS M3 rank, company search, restore notice, SEC before collection, daily run, install UX '+width);}
 }catch(e){fail++;console.log('FAIL screens gaps '+phase+(process.env.DEBUG_TEST?' '+e.stack:''));}finally{await browser.close();}console.log('COUNTS pass='+pass+' fail='+fail);if(fail)process.exitCode=1;})();
