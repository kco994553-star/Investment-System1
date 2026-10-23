"use strict";
// Exercise the real app -> same-origin frame -> Frozen preview. No input payloads or screenshots are saved.
const {chromium} = require('playwright');
const base = new URL(process.env.PAGES_COCKPIT_URL || 'http://127.0.0.1:9010/Investment-System1/');
let browser, phase = 'launch', checks = 0;
function check(ok, label) { if (!ok) throw new Error(label); checks++; }
async function choose(frame, id) {
  await frame.locator('#list [data-id="' + id + '"]').click();
  await frame.locator('[data-v]').first().waitFor();
}
async function request(frame) {
  await frame.locator('html').evaluate(() => new Promise(resolve => {
    const receive = event => {
      if (event.source !== parent || event.origin !== location.origin || event.data?.type !== 'research_public_context') return;
      removeEventListener('message', receive); resolve();
    };
    addEventListener('message', receive);
    parent.postMessage({type:'research_public_context_request'}, location.origin);
  }));
}
async function navigate(page, hash) {
  await page.evaluate(hash => {location.hash = hash;}, hash);
  await page.waitForFunction(hash => currentHash === hash, hash);
}
async function run(width, locale) {
  phase = width + ' ' + locale;
  const context = await browser.newContext({viewport:{width, height:844}});
  const failures = {external:0, unsafe:0, runtime:0};
  await context.addInitScript(locale => {
    localStorage.setItem('investment.web.v1.settings', JSON.stringify({version:1,display_locale:locale,source_language:'all'}));
    // Decision 2026-10-23 (TA G2): the technical picker offers ACTUAL ∪ watchlist ∪ TARGET v1 candidates; this device watches the
    // TARGET companies (old company_id record, read through the issuer-key migration).
    if(localStorage.getItem('investment.web.v1.personal')===null)localStorage.setItem('investment.web.v1.personal',JSON.stringify({version:1,interests:['asml','lrcx','klac','tokyo_electron','hanmi','nvda','amd','avgo','qcom','intc','msft','googl','amzn','rtx','stry','etn','hubb','gev','rok'],groups:[]}));
  }, locale);
  await context.route('**/*', route => {
    const r=route.request();
    if(new URL(r.url()).origin !== base.origin) {failures.external++; return route.abort();}
    if(r.method() !== 'GET' || r.postData()) {failures.unsafe++; return route.abort();}
    return route.continue();
  });
  const page = await context.newPage(); page.on('pageerror', () => failures.runtime++);
  try {
    await page.goto(new URL('#research',base).href, {waitUntil:'domcontentloaded'});
    const frame=page.frameLocator('#research-frame');
    await frame.locator('#list [data-id]').first().waitFor();
    const frozen=await frame.locator('#plv1-data').textContent();
    await choose(frame,'plv1.fund.002');
    check(await frame.locator('[data-selected-company-import]').count() === 1, 'selected-company import is offered explicitly');
    check(await frame.locator('[data-selected-company-import]').isDisabled(), 'no selected company never defaults to the first company');
    check(await frame.locator('[data-selected-company-status]').getAttribute('data-selected-company-status') === 'MISSING', 'missing context has an explicit reason');
    const companies=await page.evaluate(() => identityCompanies.slice(0,2).map(c=>({id:c.company_id,ticker:c.ticker,name:c.name})));
    check(companies.length===2, 'real public identity catalog is available');
    await navigate(page,'#company/'+encodeURIComponent(companies[0].id));
    await navigate(page,'#research');
    await frame.locator('#list [data-id]').first().waitFor();
    await choose(frame,'plv1.fund.002'); await request(frame);
    const button=frame.locator('[data-selected-company-import]');
    check(await button.isEnabled(), 'real company navigation makes public identity available');
    check(await frame.locator('[data-v="company"]').inputValue()==='' && await frame.locator('[data-v="ticker"]').inputValue()==='', 'context arrival never writes inputs');
    await button.click();
    check(await frame.locator('[data-v="company"]').inputValue()===companies[0].name && await frame.locator('[data-v="ticker"]').inputValue()===companies[0].ticker, 'explicit click fills the exact selected public name and ticker');
    check((await frame.locator('#pv').textContent()).includes(companies[0].name), 'canonical preview consumes imported values through normal validation');
    check(await frame.locator('[data-v="as_of"]').inputValue()==='' && await frame.locator('[data-v="qgv_snapshot_summary"]').inputValue()==='', 'identity import does not fill cutoff or analysis');

    // Company context changes through the real parent projector, while the current form has user edits.
    await frame.locator('[data-v="company"]').fill('My edited company');
    await page.evaluate(id => {researchCompanyId=id;},companies[1].id); await request(frame);
    check(await frame.locator('[data-v="company"]').inputValue()==='My edited company' && await frame.locator('[data-v="ticker"]').inputValue()===companies[0].ticker, 'switching company preserves the whole existing input pair');
    check(await button.isDisabled(), 'import cannot overwrite either half of an edited pair');
    await frame.locator('[data-v="company"]').fill('');
    check(await button.isDisabled(), 'clearing only one half cannot produce mismatched identities');
    await frame.locator('[data-v="ticker"]').fill(''); await button.click();
    check(await frame.locator('[data-v="company"]').inputValue()===companies[1].name && await frame.locator('[data-v="ticker"]').inputValue()===companies[1].ticker, 'clearing both fields explicitly permits the newly selected company');

    const originChecks=await frame.locator('html').evaluate(() => {
      const before=JSON.stringify(publicResearchContext);
      const data={type:'research_public_context',context:{selection:{company:{company_id:'fake',ticker:'FAKE',name:'Untrusted'}}}};
      dispatchEvent(new MessageEvent('message',{data,origin:location.origin,source:window}));
      dispatchEvent(new MessageEvent('message',{data,origin:'https://wrong-origin.invalid',source:parent}));
      return JSON.stringify(publicResearchContext)===before;
    });
    check(originChecks, 'frame rejects wrong-source and wrong-origin responses');
    const parentChecks=await page.evaluate(async () => {
      const frame=document.getElementById('research-frame'), original=frame.contentWindow.postMessage;let replies=0;
      frame.contentWindow.postMessage=()=>{replies++;};
      try {
        const data={type:'research_public_context_request'};
        dispatchEvent(new MessageEvent('message',{data,origin:location.origin,source:window}));
        dispatchEvent(new MessageEvent('message',{data,origin:'https://wrong-origin.invalid',source:frame.contentWindow}));
        return replies===0;
      } finally {frame.contentWindow.postMessage=original;}
    });
    check(parentChecks,'parent rejects wrong-source and wrong-origin requests');

    await choose(frame,'plv1.idea.012'); await frame.locator('[data-selected-company-import]').click();
    check(await frame.locator('[data-v="seed_company"]').inputValue()===companies[1].name && await frame.locator('[data-v="seed_ticker"]').inputValue()===companies[1].ticker, 'declared seed identity uses the same explicit import');
    await choose(frame,'plv1.tech.001');
    await frame.locator('[data-selected-company-import]').click();
    check(await frame.locator('[data-v="ticker"]').inputValue()===companies[1].ticker, 'ticker-only prompt can import the selected identity');
    check(await frame.locator('[data-v="period"]').inputValue()==='' && await frame.locator('[data-v="input_mode"]').inputValue()==='', 'chart range is never invented as period or mode');
    check(await frame.locator('[data-selected-period-status]').getAttribute('data-selected-period-status')==='UNSUPPORTED', 'unsupported period mapping has a visible precise reason');
    check((await frame.locator('[data-selected-period-status]').textContent())===(locale==='en-US'?'Periods mean different things in different prompts, so they are not transferred automatically. Enter the period you need.':'프롬프트마다 기간의 뜻이 달라 자동으로 옮기지 않습니다. 필요한 기간은 직접 입력합니다.'), 'period guidance uses the approved plain-language explanation');
    await frame.locator('[data-v="period"]').fill('User research period'); await request(frame);
    check(await frame.locator('[data-v="period"]').inputValue()==='User research period', 'context updates preserve the user period');
    await choose(frame,'plv1.macro.001');
    check(await frame.locator('[data-selected-company-import]').isHidden() && await frame.locator('[data-v="company"],[data-v="ticker"]').count()===0, 'prompts without company variables receive no invented field or import offer');
    check(await frame.locator('[data-v="horizon"]').inputValue()==='', 'macro horizon is not mapped from a technical range');

    await navigate(page,'#technical/'+encodeURIComponent(companies[0].id));
    await navigate(page,'#research');await frame.locator('#list [data-id]').first().waitFor();
    await choose(frame,'plv1.tech.001'); await request(frame); await frame.locator('[data-selected-company-import]').click();
    check(await frame.locator('[data-v="ticker"]').inputValue()===companies[0].ticker, 'explicit technical route selection reaches prompts');
    await navigate(page,'#technical');
    await navigate(page,'#research'); await frame.locator('#list [data-id]').first().waitFor();
    await choose(frame,'plv1.tech.001'); await request(frame);
    check(await frame.locator('[data-selected-company-import]').isDisabled(), 'implicit default ASML is never treated as an explicit selection');
    await navigate(page,'#technical/'+encodeURIComponent(companies[0].id));
    await page.locator('[data-technical-symbol]').selectOption(companies[1].id);
    await navigate(page,'#research'); await frame.locator('#list [data-id]').first().waitFor();
    await choose(frame,'plv1.tech.001'); await request(frame); await frame.locator('[data-selected-company-import]').click();
    check(await frame.locator('[data-v="ticker"]').inputValue()===companies[1].ticker, 'explicit technical picker changes the selected public company');
    await navigate(page,'#company/unknown-public-company'); await navigate(page,'#research');
    await frame.locator('#list [data-id]').first().waitFor(); await choose(frame,'plv1.fund.002'); await request(frame);
    check(await frame.locator('[data-selected-company-import]').isDisabled(), 'unknown selection clears the previous company offer');

    const projected=await page.evaluate(id => {
      researchCompanyId=id;
      const original=identityCompanies;
      const selected=original.find(c=>c.company_id===id);
      identityCompanies=original.map(c=>c===selected?{...c,price:'never-transfer',holdings:'never-transfer'}:c);
      const selection=researchPublicContext().selection;
      identityCompanies=[...original,{...selected,ticker:'DIFFERENT'}];
      const ambiguous=researchPublicContext().selection.company;
      identityCompanies=original;
      return {keys:Object.keys(selection.company).sort().join(','),noPrivate:!JSON.stringify(selection).includes('never-transfer'),ambiguous:ambiguous===null,period:selection.period===null};
    },companies[0].id);
    check(projected.keys==='company_id,name,ticker' && projected.noPrivate, 'selection projects only three public identity properties');
    check(projected.ambiguous,'conflicting public identity rows are unavailable');
    check(projected.period,'projection sends no inferred period');
    await page.evaluate(id=>{
      window.__promptIdentityBefore=identityCompanies;
      identityCompanies=identityCompanies.map(c=>c.company_id===id?{...c,name:null}:c);
    },companies[0].id); await request(frame);
    check(await frame.locator('[data-selected-company-import]').isDisabled() && await frame.locator('[data-selected-company-status]').getAttribute('data-selected-company-status')==='NAME_UNAVAILABLE', 'missing public name never becomes a guessed company name');
    await choose(frame,'plv1.tech.001'); await frame.locator('[data-selected-company-import]').click();
    check(await frame.locator('[data-v="ticker"]').inputValue()===companies[0].ticker, 'ticker-only prompt still accepts a known ticker when name is unpublished');
    await page.evaluate(()=>{identityCompanies=window.__promptIdentityBefore;delete window.__promptIdentityBefore;});
    await choose(frame,'plv1.fund.002');await request(frame);
    const received=await frame.locator('html').evaluate(()=>{
      dispatchEvent(new MessageEvent('message',{source:parent,origin:location.origin,data:{type:'research_public_context',context:{selection:{company:{company_id:'missing-name',ticker:17}}}}}));
      return !document.querySelector('[data-selected-company-import]').disabled;
    });
    check(!received,'malformed selected-company response does not enable import');
    await request(frame);
    await frame.locator('html').evaluate(() => {
      window.__contextReads=0;
      const fail=()=>{window.__contextReads++;throw Error('forbidden access');};
      Storage.prototype.getItem=Storage.prototype.setItem=fail; indexedDB.open=fail; window.fetch=fail;
    });
    await page.evaluate(() => {
      window.__contextReads=0;
      const fail=()=>{window.__contextReads++;throw Error('forbidden access');};
      for(const name of ['portfolio','market','actual','account'])Object.defineProperty(D,name,{configurable:true,get:fail});
      Object.defineProperty(window,'DeviceActual',{configurable:true,get:fail});
      Storage.prototype.getItem=Storage.prototype.setItem=fail; indexedDB.open=fail; window.fetch=fail;
    });
    await request(frame); await frame.locator('[data-selected-company-import]').click();
    check(await page.evaluate(()=>window.__contextReads===0) && await frame.locator('html').evaluate(()=>window.__contextReads===0), 'identity request and import touch no private objects, network or storage');
    check(await frame.locator('#plv1-data').textContent()===frozen,'Frozen catalog bytes remain unchanged');
    check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'parent fits PC/mobile viewport');
    check(await frame.locator('html').evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'import panel fits PC/mobile viewport');
    check(Object.values(failures).every(n=>n===0),'no external/unsafe calls or runtime failures');
  } finally {await context.close();}
}
(async()=>{
  try {
    browser=await chromium.launch({headless:true,...(process.env.WEB_TEST_CHROMIUM_PATH?{executablePath:process.env.WEB_TEST_CHROMIUM_PATH}:{})});
    for(const width of [390,1280])for(const locale of ['ko-KR','en-US'])await run(width,locale);
    console.log('PASS prompt selected context: '+checks+' checks / 4 viewport-language flows');
  } catch(error) {console.error('FAIL '+phase+': '+error.message);process.exitCode=1;}
  finally {if(browser)await browser.close();}
})();
