/* Google/OAuth endpoints are always mocked. Credentials, values and exports stay in memory. */
'use strict';
const { chromium } = require('playwright');
const fs = require('node:fs'), path = require('node:path');
const base = new URL(process.env.GOOGLE_SHEET_QUOTES_URL || process.env.GOOGLE_SHEET_URL || 'http://127.0.0.1:8990/Investment-System1/#settings');
const evidence = path.resolve(process.env.GOOGLE_SHEET_QUOTES_EVIDENCE_DIR || process.env.GOOGLE_SHEET_EVIDENCE_DIR || '/tmp/google-sheet-quotes-evidence');
const NOW = '2030-01-08T12:00:00.000Z', SCOPE = 'https://www.googleapis.com/auth/spreadsheets.readonly';
const STYLE = 'https://accounts.google.com/gsi/style', STYLE_ID = 'googleidentityservice_button_styles';
const ID = ['synthetic', 'spreadsheet', 'fixture'].join('_'), TOKEN = ['memory', 'only', 'synthetic', 'credential'].join('-');
const codes = ['NASDAQ:ASML','NASDAQ:LRCX','NASDAQ:KLAC','NASDAQ:NVDA','NASDAQ:AMD','NASDAQ:AVGO','NASDAQ:QCOM','NASDAQ:INTC','NASDAQ:MSFT','NASDAQ:GOOGL','NASDAQ:AMZN','NYSE:RTX','NYSE:SYK','NYSE:ETN','NYSE:HUBB','NYSE:GEV','NYSE:ROK','TYO:8035','KRX:042700','CURRENCY:USDKRW','CURRENCY:JPYKRW'];
const serial = (Date.parse('2030-01-07T16:00:01Z') - Date.UTC(1899,11,30)) / 86400000;
const values = () => [['code','price','tradetime'], ...codes.map((code,index) => [code, 41.231 + index, index < 19 ? serial : ''])];
const checks = [], traffic = { css_mocked:0, gis_mocked:0, sheets_mocked:0, revoke_mocked:0, unexpected_external:0, unsafe_request:0, console_private:0 };
let browser, currentCheck = 'browser launch', errors = 0, cspViolations = 0;
function verify(condition, reason) { if (!condition) { const error = new Error(reason); error.safeReason = reason; throw error; } }
async function check(name, run) { currentCheck = name; await run(); checks.push(name); console.log('PASS ' + name); }
async function records(page) {
  return page.evaluate(async () => {
    const db = await new Promise((resolve,reject) => { const r=indexedDB.open('investment-device-actual-v1',1); r.onsuccess=()=>resolve(r.result); r.onerror=()=>reject(new Error('storage')); });
    try { return await new Promise((resolve,reject) => { const result={},tx=db.transaction('snapshots','readonly'),store=tx.objectStore('snapshots'),r=store.openCursor(); r.onsuccess=()=>{ const c=r.result;if(c){result[c.key]=c.value;c.continue();} };tx.oncomplete=()=>resolve(result);tx.onabort=tx.onerror=()=>reject(new Error('storage')); }); }
    finally { db.close(); }
  });
}
async function waitNotice(page, value) { await page.waitForFunction(value=>document.querySelector('[data-sheet-notice]')?.dataset.notice===value,value); }
async function waitImport(page, successes, failures) {
  await page.waitForFunction(({successes,failures})=>{ const n=document.querySelector('[data-sheet-summary]');return n?.dataset.successCount===String(successes)&&n?.dataset.failureCount===String(failures); },{successes,failures});
}
async function open(locale,width,missingClient=false) {
  const context=await browser.newContext({viewport:{width,height:844},locale});
  const mode={status:200,partial:false,unknown:false,delayed:false,pending:null,reads:0,scripts:0,styles:0,styleStatus:200,delayCSS:false,pendingCSS:null,styleStarted:null,loadOrder:[]};
  await context.addInitScript(({locale})=>{
    localStorage.setItem('investment.web.v1.settings',JSON.stringify({version:1,display_locale:locale,source_language:'all'}));
    window.__sheetCsp={count:0};
    document.addEventListener('securitypolicyviolation',()=>{window.__sheetCsp.count++;});
  },{locale});
  await context.route('**/*',async route=>{
    const request=route.request(),url=new URL(request.url());
    if(url.origin===base.origin){
      if(request.method()!=='GET'||request.postData()){traffic.unsafe_request++;await route.abort();return;}
      if(missingClient&&url.pathname.endsWith('/app-config.js')){await route.fulfill({contentType:'application/javascript',body:'window.InvestmentAppConfig = Object.freeze({googleSheetsClientId:""});'});return;}
      await route.continue();return;
    }
    if(url.href===STYLE){
      traffic.css_mocked++;mode.styles++;mode.loadOrder.push('css-request');
      verify(request.method()==='GET'&&!request.postData()&&!request.headers().referer,'Google CSS request has no body or referrer');
      const fulfill=()=>route.fulfill({status:mode.styleStatus,contentType:'text/css',body:mode.styleStatus===200?'.g_id_signin { font-family: Arial; }':''});
      if(mode.delayCSS){mode.pendingCSS=fulfill;if(mode.styleStarted)mode.styleStarted();}else await fulfill();return;
    }
    if(url.href==='https://accounts.google.com/gsi/client'){
      traffic.gis_mocked++;mode.scripts++;mode.loadOrder.push('sdk-request');
      await route.fulfill({contentType:'application/javascript',body:`window.__sheetMock={popup:0,revoke:0,gestureFailures:0,scopes:[],pending:null,delayAuth:false,externalStyleReady:[]};function installGisStyles(){let marker=document.getElementById('googleidentityservice_button_styles');window.__sheetMock.externalStyleReady.push(!!marker&&marker.tagName==='LINK'&&marker.href==='https://accounts.google.com/gsi/style'&&marker.rel==='stylesheet'&&!!marker.sheet);if(!marker){marker=document.createElement('style');marker.id='googleidentityservice_button_styles';marker.textContent='.g_id_signin { font-family: Arial; }';document.head.append(marker);}}installGisStyles();window.google={accounts:{oauth2:{initTokenClient(config){installGisStyles();window.__sheetMock.scopes.push(config.scope);return {requestAccessToken(){const m=window.__sheetMock;m.popup++;if(!navigator.userActivation.isActive)m.gestureFailures++;const respond=()=>config.callback({access_token:['memory','only','synthetic','credential'].join('-'),expires_in:3600,scope:'https://www.googleapis.com/auth/spreadsheets.readonly email',token_type:'Bearer'});if(m.delayAuth)m.pending=respond;else respond();}};},revoke(token,done){window.__sheetMock.revoke++;fetch('https://oauth2.googleapis.com/revoke',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:'token='+encodeURIComponent(token),credentials:'omit',referrerPolicy:'no-referrer'}).then(()=>done({}));}}}};`});return;
    }
    if(url.origin==='https://sheets.googleapis.com'&&url.pathname===('/v4/spreadsheets/'+ID+'/values/'+encodeURIComponent('Quotes!A1:C22'))){
      traffic.sheets_mocked++;mode.reads++;
      verify(request.method()==='GET'&&!request.postData(),'Sheets request must be GET without a body');
      verify(request.headers().authorization==='Bearer '+TOKEN,'Sheets request uses the memory token');
      verify(!request.headers().cookie&&!request.headers().referer,'Google requests omit cookies and referrer');
      verify(url.searchParams.get('valueRenderOption')==='UNFORMATTED_VALUE'&&url.searchParams.get('dateTimeRenderOption')==='SERIAL_NUMBER','Sheets render modes are fixed');
      const rows=values();if(mode.partial){rows[4][1]='#N/A';rows[18][1]='#N/A';}if(mode.unknown)rows.push(['UNMAPPED_PRIVATE_CODE',71.233,'']);
      const fulfill=()=>route.fulfill({status:mode.status,contentType:'application/json',body:JSON.stringify(mode.status===200?{values:rows}:{error:{message:'synthetic unauthorized'}})});
      if(mode.delayed)mode.pending=fulfill;else await fulfill();return;
    }
    if(url.origin==='https://oauth2.googleapis.com'&&url.pathname==='/revoke'){
      traffic.revoke_mocked++;verify(request.method()==='POST'&&new URLSearchParams(request.postData()).get('token')===TOKEN,'revocation is mocked');await route.fulfill({contentType:'application/json',body:'{}'});return;
    }
    traffic.unexpected_external++;await route.abort();
  });
  const page=await context.newPage();page.on('pageerror',()=>{errors++;});page.on('console',message=>{if([ID,TOKEN,'UNMAPPED_PRIVATE_CODE',...values().slice(1).map(row=>String(row[1]))].some(value=>message.text().includes(value)))traffic.console_private++;});
  await page.clock.install({time:new Date(NOW)});
  const url=new URL(base);url.hash='settings';await page.goto(url.href,{waitUntil:'networkidle'});
  const root=page.locator('[data-google-sheet-quotes]');await root.locator('[data-sheet-action="paste"]').waitFor();
  return {context,page,root,mode};
}
async function configure(session) {
  const {page,root}=session;await root.locator('[data-sheet-enabled]').check();
  await root.locator('[data-sheet-id]').fill('https://docs.google.com/spreadsheets/u/0/d/'+ID+'/edit#gid=0');
  await root.locator('[data-sheet-action="save"]').click();await waitNotice(page,'saved');
}
async function login(session) {
  const {root,page}=session;
  if(await root.locator('[data-sheet-action="prepare"]').isVisible()){await root.locator('[data-sheet-action="prepare"]').click();await root.locator('[data-sheet-action="login"]').waitFor({state:'visible'});}
  await root.locator('[data-sheet-action="login"]').click();await root.locator('[data-sheet-action="fetch"]').waitFor({state:'visible'});
  verify(await page.evaluate(()=>window.__sheetMock.gestureFailures===0&&window.__sheetMock.scopes.every(scope=>{const grants=new Set(scope.trim().split(/\s+/));return grants.size===2&&grants.has('https://www.googleapis.com/auth/spreadsheets.readonly')&&grants.has('email');})),'login preserves button gesture and exact readonly plus email scopes');
}
async function verifyStyles(session) {
  const {page,mode}=session;
  await page.evaluate(()=>new Promise(requestAnimationFrame));
  verify(await page.evaluate(()=>window.__sheetCsp.count===0),'GIS load and OAuth initialization must cause zero CSP violation events');
  verify(mode.styles===1&&mode.loadOrder.join(',')==='css-request,sdk-request','official CSS must load once before the SDK request');
  verify(await page.evaluate(()=>window.__sheetMock.externalStyleReady.every(Boolean)&&document.querySelectorAll('#googleidentityservice_button_styles').length===1),'GIS sees a loaded external marker on load and OAuth initialization');
}
async function main(){
  fs.mkdirSync(evidence,{recursive:true});
  try {
    const executablePath=process.env.CHROMIUM_EXECUTABLE_PATH||process.env.WEB_TEST_CHROMIUM_PATH;
    browser=await chromium.launch({headless:true,...(executablePath?{executablePath}:{})});
    for(const locale of ['ko-KR','en-US'])for(const width of [390,1280]){
      const label=locale+' '+width,session=await open(locale,width),{page,root,mode}=session;
      try {
        await check(label+': default OFF hides Google buttons and never loads external code',async()=>{
          verify(!await root.locator('[data-sheet-enabled]').isChecked(),'default OFF');verify(!await root.locator('[data-sheet-action="prepare"]').isVisible()&&!await root.locator('[data-sheet-action="fetch"]').isVisible(),'OFF hides Google actions');verify(mode.styles===0&&mode.scripts===0&&mode.reads===0,'OFF makes no Google CSS or API calls');verify(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'mobile layout does not overflow');
          verify((await root.locator('h2').textContent()).includes(locale==='en-US'?'Google Sheet':'구글 시트'),'locale is applied');
        });
        await check(label+': enabling and saving remain local, explicit login then normal 21 import',async()=>{
          await configure(session);verify(mode.styles===0&&mode.scripts===0&&mode.reads===0,'settings do not initiate Google CSS or API requests');await login(session);await verifyStyles(session);verify(mode.reads===0,'login does not read quotes');await root.locator('[data-sheet-action="fetch"]').click();await waitImport(page,21,0);
          const data=await records(page);verify(data.market.quotes.length===19&&data.market.fx.length===2,'normal 21 are saved');verify(data['market-import-history'].entries.length===1,'one batch history record');verify(data.market.fx.every(row=>row.time_status==='FX_UNKNOWN'),'FX timestamp is explicitly unknown');verify(data.market.quotes.every(row=>row.source==='GOOGLEFINANCE'&&row.time_status==='KNOWN'),'exchange serial timestamps are interpreted');
        });
        await check(label+': partial unavailable rows retain previous manual values and unknown codes are safe',async()=>{
          await page.evaluate(async()=>{const db=await new Promise(resolve=>{const r=indexedDB.open('investment-device-actual-v1',1);r.onsuccess=()=>resolve(r.result);});await new Promise(resolve=>{const tx=db.transaction('snapshots','readwrite'),store=tx.objectStore('snapshots'),r=store.get('market');r.onsuccess=()=>{const row=r.result.quotes.find(item=>item.currency==='JPY');row.source='MANUAL';delete row.time_status;store.put(r.result,'market');};tx.oncomplete=resolve;});db.close();});
          const before=await records(page),jpyBefore=before.market.quotes.find(row=>row.currency==='JPY');mode.partial=true;mode.unknown=true;await root.locator('[data-sheet-action="fetch"]').click();await waitImport(page,19,2);
          const after=await records(page);verify(JSON.stringify(after.market.quotes.find(row=>row.currency==='JPY'))===JSON.stringify(jpyBefore),'Tokyo manual quote is preserved');verify(after['market-import-history'].entries.length===2,'partial import adds one history record');verify(!(await root.locator('[data-sheet-summary]').textContent()).includes('UNMAPPED_PRIVATE_CODE'),'unknown code is not echoed');verify((await root.locator('[data-sheet-summary]').textContent()).includes('NOT_AVAILABLE'),'failed rows report unavailable');mode.partial=false;mode.unknown=false;
        });
        await check(label+': token and settings excluded from backup and persistent token storage',async()=>{
          const data=await records(page);verify(data['google-sheet-settings'].spreadsheet_id===ID,'settings stay on device');verify(!JSON.stringify(data).includes(TOKEN),'IndexedDB has no token');
          const safe=await page.evaluate(async({id,token})=>{const catalog=await(await fetch('actual-catalog.json')).json(),now=new Date().toISOString(),snapshot=DeviceActual.makeSnapshot(catalog,[],null,now),db=await new Promise(resolve=>{const r=indexedDB.open('investment-device-actual-v1',1);r.onsuccess=()=>resolve(r.result);}),market=await new Promise(resolve=>{const r=db.transaction('snapshots','readonly').objectStore('snapshots').get('market');r.onsuccess=()=>resolve(r.result);});db.close();const backup=JSON.stringify(DeviceMarket.exportBackup(snapshot,market,catalog,{now}));return !backup.includes(id)&&!backup.includes(token)&&!backup.includes('google-sheet-settings')&&!Object.values(localStorage).some(value=>value.includes(id)||value.includes(token));},{id:ID,token:TOKEN,now:NOW});verify(safe,'backup and localStorage exclude credentials/settings');
        });
        await check(label+': route and locale renders preserve only memory login and never read automatically',async()=>{
          const reads=mode.reads,scripts=mode.scripts,styles=mode.styles;await page.evaluate(()=>{location.hash='home';});await page.locator('[data-google-sheet-quotes]').waitFor({state:'detached'});await page.evaluate(()=>{location.hash='settings';});await root.locator('[data-sheet-action="fetch"]').waitFor({state:'visible'});verify(mode.reads===reads&&mode.scripts===scripts&&mode.styles===styles,'route change does not perform external reads');
          const otherLocale=locale==='en-US'?'ko-KR':'en-US';await page.locator('#display-locale').selectOption(otherLocale);await root.locator('[data-sheet-action="fetch"]').waitFor({state:'visible'});verify((await root.locator('h2').textContent()).includes(otherLocale==='en-US'?'Google Sheet':'구글 시트'),'locale rerender preserves login');await page.locator('#display-locale').selectOption(locale);await root.locator('[data-sheet-action="fetch"]').waitFor({state:'visible'});verify(mode.reads===reads&&mode.scripts===scripts&&mode.styles===styles,'locale changes do not perform external reads');
        });
        await check(label+': expiry and unauthorized responses require user sign-in again',async()=>{
          const before=mode.reads;await page.clock.fastForward(3600001);await root.locator('[data-sheet-action="login"]').waitFor({state:'visible'});verify(mode.reads===before,'expiry does not refresh automatically');await login(session);mode.status=401;await root.locator('[data-sheet-action="fetch"]').click();await waitNotice(page,'auth');await root.locator('[data-sheet-action="login"]').waitFor({state:'visible'});mode.status=200;await login(session);
        });
        await check(label+': disconnect revokes then paste works while Google is OFF',async()=>{
          const readCount=mode.reads;await root.locator('[data-sheet-action="disconnect"]').click();await waitNotice(page,'removed');verify(await page.evaluate(()=>window.__sheetMock.revoke===1),'disconnect calls revoke');await root.locator('[data-sheet-enabled]').uncheck();await root.locator('[data-sheet-paste]').fill(values().map(row=>row.join('\t')).join('\n'));await root.locator('[data-sheet-action="paste"]').click();await waitImport(page,21,0);verify(await root.locator('[data-sheet-paste]').inputValue()==='','paste clears after save');verify(mode.reads===readCount,'paste requires no Google read');const data=await records(page);verify(data['market-import-history'].entries.at(-1).method==='paste','paste shares batch history');
        });
        if(locale==='ko-KR'&&width===390){
          await check(label+': disabling rejects delayed auth callback',async()=>{
            await root.locator('[data-sheet-enabled]').check();await page.evaluate(()=>{window.__sheetMock.delayAuth=true;});await root.locator('[data-sheet-action="login"]').click();await root.locator('[data-sheet-enabled]').uncheck();await page.evaluate(()=>{window.__sheetMock.pending();window.__sheetMock.delayAuth=false;});await root.locator('[data-sheet-enabled]').check();verify(!await root.locator('[data-sheet-action="fetch"]').isVisible(),'late auth cannot reconnect');await login(session);
          });
          await check(label+': disconnect during a pending Sheets read cannot save its response',async()=>{
            const before=JSON.stringify((await records(page)).market);mode.delayed=true;await root.locator('[data-sheet-action="fetch"]').click();await page.waitForFunction(()=>document.querySelector('[data-sheet-action="fetch"]')?.disabled===true);verify(mode.pending!==null,'pending mock read');await root.locator('[data-sheet-action="disconnect"]').click();await waitNotice(page,'canceled');await mode.pending().catch(()=>{});mode.delayed=false;verify(JSON.stringify((await records(page)).market)===before,'canceled read preserves market');
          });
        }
        await check(label+': external GIS stylesheet keeps CSP violations at zero',async()=>{await verifyStyles(session);});
      }finally{cspViolations+=await page.evaluate(()=>window.__sheetCsp.count);await session.context.close();}
    }
    await check('empty OAuth configuration hides every Google control while paste remains usable',async()=>{
      const session=await open('ko-KR',390,true);try{verify(await session.root.locator('[data-sheet-enabled]').count()===0&&await session.root.locator('[data-sheet-action="login"]').count()===0,'missing client hides Google controls');await session.root.locator('[data-sheet-paste]').fill(values().map(row=>row.join(',')).join('\n'));await session.root.locator('[data-sheet-action="paste"]').click();await waitImport(session.page,21,0);verify(session.mode.styles===0&&session.mode.scripts===0&&session.mode.reads===0,'missing config never calls Google CSS or API');}finally{cspViolations+=await session.page.evaluate(()=>window.__sheetCsp.count);await session.context.close();}
    });
    const retry=await open('ko-KR',390);
    try{
      await check('fresh OFF paste makes no Google CSS, SDK or API request',async()=>{
        await retry.root.locator('[data-sheet-paste]').fill(values().map(row=>row.join('\t')).join('\n'));await retry.root.locator('[data-sheet-action="paste"]').click();await waitImport(retry.page,21,0);verify(retry.mode.styles===0&&retry.mode.scripts===0&&retry.mode.reads===0,'OFF paste never loads Google CSS or SDK');
      });
      await check('CSS load failure stops SDK and OAuth and preserves local quotes',async()=>{
        await configure(retry);const before=JSON.stringify(await records(retry.page));retry.mode.styleStatus=404;await retry.root.locator('[data-sheet-action="prepare"]').click();await waitNotice(retry.page,'authFailed');verify(retry.mode.styles===1&&retry.mode.scripts===0&&retry.mode.reads===0,'failed CSS cannot load SDK or request a token');verify(!await retry.root.locator('[data-sheet-action="login"]').isVisible(),'CSS failure never shows the token login button');verify(JSON.stringify(await records(retry.page))===before,'CSS failure preserves all device records');verify(await retry.page.evaluate(()=>!window.google&&!document.getElementById('googleidentityservice_button_styles')&&window.__sheetCsp.count===0),'failed stylesheet marker is removed without CSP violations');
      });
      await check('explicit CSS retry and concurrent prepare clicks load one CSS then one SDK',async()=>{
        retry.mode.styleStatus=200;retry.mode.delayCSS=true;const started=new Promise(resolve=>{retry.mode.styleStarted=resolve;});await retry.root.locator('[data-sheet-action="prepare"]').click();await started;
        await retry.page.evaluate(()=>{const button=document.querySelector('[data-sheet-action="prepare"]');button.dispatchEvent(new Event('click',{bubbles:true}));button.dispatchEvent(new Event('click',{bubbles:true}));});verify(retry.mode.styles===2&&retry.mode.scripts===0,'concurrent preparation stays behind the pending single CSS load');
        await retry.mode.pendingCSS();retry.mode.delayCSS=false;await retry.root.locator('[data-sheet-action="login"]').waitFor({state:'visible'});await login(retry);verify(retry.mode.styles===2&&retry.mode.scripts===1&&retry.mode.loadOrder.join(',')==='css-request,css-request,sdk-request','retry adds one successful CSS and one SDK request');verify(await retry.page.evaluate(()=>window.__sheetMock.popup===1&&window.__sheetMock.externalStyleReady.every(Boolean)&&document.querySelectorAll('#googleidentityservice_button_styles').length===1&&window.__sheetCsp.count===0),'successful retry uses one loaded marker and one explicit token popup with no CSP violations');
      });
    }finally{cspViolations+=await retry.page.evaluate(()=>window.__sheetCsp.count);await retry.context.close();}
    const cancel=await open('en-US',1280);
    try{
      await check('OFF during a pending stylesheet load prevents any late SDK or token request',async()=>{
        await configure(cancel);cancel.mode.delayCSS=true;const started=new Promise(resolve=>{cancel.mode.styleStarted=resolve;});await cancel.root.locator('[data-sheet-action="prepare"]').click();await started;await cancel.root.locator('[data-sheet-enabled]').uncheck();await cancel.mode.pendingCSS();await cancel.page.waitForFunction(()=>document.querySelector('[data-sheet-action="prepare"]')?.disabled===false);verify(cancel.mode.styles===1&&cancel.mode.scripts===0&&cancel.mode.reads===0,'late CSS cannot start the SDK after OFF');verify(await cancel.page.evaluate(()=>!window.google&&window.__sheetCsp.count===0),'canceled preparation has no OAuth client or CSP violation');
      });
    }finally{cspViolations+=await cancel.page.evaluate(()=>window.__sheetCsp.count);await cancel.context.close();}
    await check('privacy: all external Google calls mocked, no private console output, CSP violations or runtime errors',async()=>{verify(traffic.unexpected_external===0&&traffic.unsafe_request===0&&traffic.console_private===0,'no unsafe or unmocked traffic/private output');verify(errors===0,'no unhandled browser errors');verify(cspViolations===0,'all mocked flows produce zero CSP violation events');});
    fs.writeFileSync(path.join(evidence,'google-sheet-quotes-browser.json'),JSON.stringify({passed:true,checks,traffic,page_error_count:errors,csp_violation_count:cspViolations,screenshots:[],payload_files_written:0},null,2)+'\n');
  }catch(error){fs.writeFileSync(path.join(evidence,'google-sheet-quotes-browser.json'),JSON.stringify({passed:false,failed_check:currentCheck,failure_reason:error.safeReason||'browser interaction failed (details redacted)',checks,traffic,page_error_count:errors,csp_violation_count:cspViolations,screenshots:[],payload_files_written:0},null,2)+'\n');console.error('FAIL '+currentCheck+': '+(error.safeReason||'browser interaction failed (details redacted)'));process.exitCode=1;}
  finally{if(browser)await browser.close();}
}
main();
