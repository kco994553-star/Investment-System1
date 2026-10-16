'use strict';
// S10 forward validation: public price-free ledger (served by route interception, synthetic) and the device-only
// TARGET v0 forward return from synthetic in-memory history. Nothing computed may be stored or sent.
const assert=require('node:assert/strict');const {chromium}=require('playwright');
const BASE=process.env.PAGES_COCKPIT_URL,SHOTS=process.env.PAGES_COCKPIT_EVIDENCE_DIR||'.';
const V='forward_validation/v1',VV='forward_validation/v1+dcf_v1_default',H='b'.repeat(64);
const IDS=['asml','lrcx','klac','tokyo_electron','hanmi','nvda','amd','avgo','qcom','intc','msft','googl','amzn','rtx','stry','etn','hubb','gev','rok'];
const UNITS={asml:900,lrcx:600,klac:550,tokyo_electron:500,hanmi:450,nvda:800,amd:500,avgo:500,qcom:400,intc:300,msft:700,googl:700,amzn:600,rtx:600,stry:550,etn:500,hubb:350,gev:300,rok:200};
function recorded(){const companies={};IDS.forEach((id,i)=>{const live=i%4!==0;companies[id]=live?{state:'LIVE',Q:{score:40+i,coverage:'PARTIAL',missing_factor_count:5},G:{score:60-i,coverage:'PARTIAL',missing_factor_count:4}}:{state:'NOT_AVAILABLE',Q:{score:null,coverage:'BLOCKED',missing_factor_count:7},G:{score:null,coverage:'BLOCKED',missing_factor_count:6}};});
 return{date:'2026-10-19',version:V,strategy:'QGV_STANDARD_V1',calibration:'UNCALIBRATED',state:'RECORDED',reason_codes:[],target:{portfolio_id:'TARGET',version:'v0',root_sha256:H,total_units:10000,weights_units:{...UNITS}},qg_as_of:'2026-10-19T22:10:00+00:00',qg_screen_state:'LIVE',companies,source_sha256:{'sec-qg-factors.json':H,'actual-catalog.json':H},created_at:'2026-10-19T22:30:00+00:00'};}
function missingDay(){return{date:'2026-10-20',version:V,strategy:'QGV_STANDARD_V1',calibration:'UNCALIBRATED',state:'NOT_AVAILABLE',reason_codes:['SEC_QG_FACTORS_MISSING'],target:{portfolio_id:'TARGET',version:'v0',root_sha256:H,total_units:10000,weights_units:{...UNITS}},qg_as_of:null,qg_screen_state:null,companies:null,source_sha256:{'sec-qg-factors.json':null,'actual-catalog.json':H},created_at:'2026-10-20T22:30:00+00:00'};}
function ledger(){return{schema_version:1,kind:'FORWARD_VALIDATION_LEDGER',start_date:'2026-10-19',status:'ACTIVE',as_of:'2026-10-20T22:31:00+00:00',strategy:'QGV_STANDARD_V1',calibration:'UNCALIBRATED',holdout:'UNCONFIRMED_NOT_USED',price_free:true,target:{portfolio_id:'TARGET',version:'v0'},versions:{[V]:[recorded(),missingDay()],[VV]:[]},version_status:{[V]:{state:'ACTIVE',v_included:false,reason_codes:[]},[VV]:{state:'NOT_AVAILABLE',v_included:true,reason_codes:['V_REQUIRES_DEVICE_PRICES']}}};}
// Schema-2 ledger with observation bases (owner instruction 2026-10-16): 10/19 PREPARATORY (unversioned input, low
// coverage), 10/20-10/21 PRIMARY under calc version A: two segments, shown separately and never chained.
const V2='forward_validation/v2',CALC_A='qgv2-calc/2026-10-15.1';
function v2Row(date,basis){const companies={};IDS.forEach((id,i)=>{companies[id]=i%4?{state:'LIVE',Q:{score:40+i,coverage:'PARTIAL',missing_factor_count:1},G:{score:60-i,coverage:'PARTIAL',missing_factor_count:2}}:{state:'NOT_AVAILABLE',Q:{score:null,coverage:'BLOCKED',missing_factor_count:5},G:{score:null,coverage:'BLOCKED',missing_factor_count:5}};});
 return{date,version:V2,strategy:'QGV_STANDARD_V2',calibration:'UNCALIBRATED',state:'RECORDED',reason_codes:[],target:{portfolio_id:'TARGET',version:'v0',root_sha256:H,total_units:10000,weights_units:{...UNITS}},qg_as_of:date+'T22:10:00+00:00',qg_screen_state:'LIVE',companies,source_sha256:{'sec-qgv2.json':H,'actual-catalog.json':H},created_at:date+'T22:30:00+00:00',basis};}
function ledgerV2(){
 const prep={calc_version:null,q_scored:300,g_scored:290,population:{n:310,id:'0123456789abcdef'},acquired:['2026-10-14','2026-10-19'],evaluation:{eligible:false,status:'PREPARATORY',reasons:['Q_BELOW_454','G_BELOW_454','CALC_VERSION_MISSING']},segment:'NONE'};
 const primary=d=>({calc_version:CALC_A,q_scored:470,g_scored:466,population:{n:480,id:'fedcba9876543210'},acquired:['2026-10-14',d],evaluation:{eligible:true,status:'PRIMARY',reasons:[]},segment:CALC_A});
 const p=ledger();p.schema_version=2;p.strategy='QGV_STANDARD_V2';p.as_of='2026-10-21T22:31:00+00:00';p.versions[V]=[recorded()];
 p.versions[V2]=[v2Row('2026-10-19',prep),v2Row('2026-10-20',primary('2026-10-20')),v2Row('2026-10-21',primary('2026-10-21'))];
 p.version_status[V2]={state:'ACTIVE',v_included:false,reason_codes:[]};return p;}
async function open(page,hash,selector){await page.evaluate(h=>{location.hash=h;},hash);await page.locator(selector).first().waitFor();}
async function noOverflow(page,label){assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'horizontal scroll '+label);}
async function storageKeys(page){return page.evaluate(()=>Object.keys(localStorage).concat(Object.keys(sessionStorage)).sort());}
// Synthetic in-memory session: the 13th history read is RATE_LIMITED once (like the Worker's 12/min cap).
async function seedSession(page){
 await page.evaluate(async()=>{
  await DeviceActual.sheetSettings(window,{schema:'device-google-sheet-settings/1',enabled:true,spreadsheet_id:'',range:'Quotes!A1:C22'});
  localStorage.setItem('investment.web.v1.private-history-origin',InvestmentAppConfig.privateHistoryWorkerOrigin);
  const meta={'042700.KS':['KRW','Asia/Seoul','KSC','T00:30:00Z'],'8035.T':['JPY','Asia/Tokyo','JPX','T00:30:00Z']};
  window.__audit={reads:0,limited:false};const listeners=new Set();
  const session={state:()=>({enabled:true,connected:true}),revision:()=>1,setEnabled(){},subscribe:f=>{listeners.add(f);return()=>listeners.delete(f);},
   async fetchHistory(origin,symbol,range){window.__audit.reads++;if(window.__audit.reads===13&&!window.__audit.limited){window.__audit.limited=true;throw Error('RATE_LIMITED');}
    const [currency,timezone,exchange,time]=meta[symbol]||['USD','America/New_York','NMS','T13:30:00Z'],k=symbol.length;
    const bars=[['2026-10-16',90],['2026-10-19',100],['2026-10-20',100+k],['2026-10-21',100+2*k]].map(([d,c])=>({timestamp:Date.parse(d+time)/1000,open:c,high:c,low:c,close:c,adjusted_close:c,volume:1,session_status:'COMPLETE'}));
    return{schema:'private-history/1',provider:'Yahoo Finance(비공식)',symbol,range,currency,exchange,timezone,interval:'1d',basis:'RAW_CLOSE',delay_status:'UNKNOWN',read_at:'2026-10-22T21:00:00Z',bars};}};
  window.GoogleSheetQuotes={...GoogleSheetQuotes,sessionFor:()=>session};
 });
}
(async()=>{
 let pass=0,phase='INIT';const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_EXECUTABLE_PATH});
 try{
  for(const width of [390,1440]){
   phase='NO_LEDGER '+width;
   {const context=await browser.newContext({viewport:{width,height:900},serviceWorkers:'block'}),page=await context.newPage();let errors=0;page.on('pageerror',()=>errors++);
    await page.route('**/*',r=>new URL(r.request().url()).origin===new URL(BASE).origin?r.continue():r.abort());
    await page.route('**/forward-validation-ledger.json',r=>r.fulfill({status:404,body:''}));
    await page.goto(BASE+'#validation');await page.locator('[data-forward-validation]').waitFor();
    await page.locator('[data-forward-status]').filter({hasText:'LEDGER_NOT_PUBLISHED'}).waitFor();
    assert.equal(await page.locator('[data-forward-start]').textContent(),'2026-10-19');assert.equal(await page.locator('[data-forward-count]').textContent(),'0');
    assert.ok((await page.locator('[data-forward-holdout]').textContent()).includes('Holdout UNCONFIRMED · 사용 금지'));
    assert.equal(await page.locator('[data-forward-price-status]').getAttribute('data-code'),'LEDGER_NOT_AVAILABLE');assert.equal(await page.locator('[data-forward-action="load"]').isDisabled(),true);
    assert.equal(await page.locator('[data-forward-benchmark]').getAttribute('data-forward-benchmark'),'NOT_AVAILABLE');
    assert.deepEqual(await page.locator('[data-validation-section]').evaluateAll(n=>n.map(x=>x.dataset.validationSection)),['setup','equity-curve','quarterly','track-record','baseline','promotion']);
    await noOverflow(page,'no ledger '+width);assert.equal(errors,0);await context.close();pass++;}
   phase='LEDGER '+width;
   {const context=await browser.newContext({viewport:{width,height:900},serviceWorkers:'block'}),page=await context.newPage();let errors=0;const sent=[];page.on('pageerror',()=>errors++);
    page.on('request',r=>{if(r.method()!=='GET')sent.push(r.method());});
    await page.route('**/*',r=>new URL(r.request().url()).origin===new URL(BASE).origin?r.continue():r.abort());
    await page.route('**/forward-validation-ledger.json',r=>r.fulfill({status:200,contentType:'application/json',body:JSON.stringify(ledger())}));
    await page.goto(BASE+'#settings');await page.locator('#device-backup-export').waitFor();
    await seedSession(page);const before=await storageKeys(page);
    await open(page,'validation','[data-forward-days]');
    assert.equal(await page.locator('[data-forward-status]').textContent(),'ACTIVE');assert.equal(await page.locator('[data-forward-count]').textContent(),'2');
    assert.ok((await page.locator('[data-forward-strategy]').textContent()).includes('QGV_STANDARD_V1 · forward_validation/v1 · UNCALIBRATED'));
    assert.ok((await page.locator('[data-forward-v-version]').textContent()).includes('V_REQUIRES_DEVICE_PRICES'));
    assert.deepEqual(await page.locator('[data-forward-day]').evaluateAll(n=>n.map(x=>x.dataset.forwardDay)),['2026-10-20','2026-10-19']);
    assert.ok((await page.locator('[data-forward-day="2026-10-20"]').textContent()).includes('NOT_AVAILABLE · SEC_QG_FACTORS_MISSING'));
    const live=await page.locator('[data-forward-day="2026-10-19"] td').allTextContents();assert.equal(live[1],'LIVE');assert.equal(live[2],'14/19');assert.equal(live[4],'14/19');
    assert.equal(await page.locator('[data-forward-portfolio]').getAttribute('data-forward-portfolio'),'NOT_AVAILABLE');
    await page.locator('[data-forward-action="load"]:enabled').waitFor();
    await page.locator('[data-forward-action="load"]').click();
    await page.locator('[data-forward-price-status][data-code="READY"]').filter({hasText:'RATE_LIMITED'}).waitFor();
    assert.equal(await page.locator('[data-forward-portfolio]').getAttribute('data-forward-portfolio'),'NOT_AVAILABLE');
    assert.equal(await page.evaluate(()=>window.__audit.reads),13);
    await page.locator('[data-forward-action="load"]').click();
    await page.locator('[data-forward-portfolio="AVAILABLE"]').waitFor();
    assert.equal(await page.evaluate(()=>window.__audit.reads),20,'second click reads only the remaining symbols');
    const text=await page.locator('[data-forward-portfolio]').textContent();assert.ok(/2026-10-19 → 2026-10-21 · -?\d+\.\d{2}%/.test(text),text);
    assert.equal(await page.locator('[data-forward-instrument]').count(),19);
    assert.equal(await page.locator('[data-forward-benchmark]').getAttribute('data-forward-benchmark'),'NOT_AVAILABLE');
    await noOverflow(page,'ledger '+width);await page.screenshot({path:SHOTS+'/forward-validation-'+width+'.png',fullPage:true}).catch(()=>{});
    assert.deepEqual(await storageKeys(page),before,'nothing new is stored');
    assert.ok(!(await page.evaluate(()=>JSON.stringify(localStorage)+JSON.stringify(sessionStorage))).includes('%'),'no computed value stored');
    assert.deepEqual(sent,[],'nothing is sent');
    await page.locator('[data-forward-action="clear"]').click();assert.equal(await page.locator('[data-forward-portfolio]').getAttribute('data-forward-portfolio'),'NOT_AVAILABLE');
    await open(page,'home','.hero');assert.equal(await page.locator('[data-forward-validation]').count(),0);
    assert.equal(errors,0);await context.close();pass++;}
   phase='BASIS '+width;
   {const context=await browser.newContext({viewport:{width,height:900},serviceWorkers:'block'}),page=await context.newPage();let errors=0;page.on('pageerror',()=>errors++);
    await page.route('**/*',r=>new URL(r.request().url()).origin===new URL(BASE).origin?r.continue():r.abort());
    await page.route('**/forward-validation-ledger.json',r=>r.fulfill({status:200,contentType:'application/json',body:JSON.stringify(ledgerV2())}));
    await page.goto(BASE+'#settings');await page.locator('#device-backup-export').waitFor();
    await seedSession(page);await open(page,'validation','[data-forward-segments]');
    const prep=await page.locator('[data-forward-day="2026-10-19"][data-forward-evaluation="PREPARATORY"]').textContent();
    assert.ok(prep.includes('준비 관측·주 평가 대상 아님')&&prep.includes('Q_BELOW_454, G_BELOW_454, CALC_VERSION_MISSING'),prep);
    assert.ok((await page.locator('[data-forward-day="2026-10-20"][data-forward-evaluation="PRIMARY"]').textContent()).includes('Q 470 · G 466'));
    assert.equal(await page.locator('[data-forward-day="2026-10-19"][data-forward-evaluation="COMPARISON"]').count(),1);
    assert.deepEqual(await page.locator('[data-forward-segment]').evaluateAll(n=>n.map(x=>x.dataset.forwardSegment)),['NONE',CALC_A]);
    await page.locator('[data-forward-action="load"]:enabled').waitFor();await page.locator('[data-forward-action="load"]').click();
    await page.locator('[data-forward-price-status][data-code="READY"]').filter({hasText:'RATE_LIMITED'}).waitFor();
    await page.locator('[data-forward-action="load"]').click();await page.locator('[data-forward-portfolio="AVAILABLE"]').waitFor();
    // The current segment starts on its first PRIMARY record (10/20), never on the preparatory 10/19.
    assert.ok((await page.locator('[data-forward-portfolio]').textContent()).includes('2026-10-20 → 2026-10-21'));
    assert.ok((await page.locator('[data-forward-segment-return="NONE"]').textContent()).includes('주 평가 기록 없음'));
    assert.ok(/2026-10-20 → 현재 · -?\d+\.\d{2}%/.test(await page.locator(`[data-forward-segment-return="${CALC_A}"]`).textContent()));
    await noOverflow(page,'basis '+width);assert.equal(errors,0);await context.close();pass++;}
  }
  console.log('forward_validation_browser_test PASS '+pass);
 }catch(e){console.log('forward_validation_browser_test FAIL '+phase);if(process.env.DEBUG_TEST)console.log(e);process.exitCode=1;}
 finally{await browser.close();}
})();
