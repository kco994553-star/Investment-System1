'use strict';
// S08 indicator cards, S09 macro and S10 validation canon sections (design canvas). Synthetic bars only.
const assert=require('node:assert/strict');const {chromium}=require('playwright');
const BASE=process.env.PAGES_COCKPIT_URL,SHOTS=process.env.TECH_SHOT_DIR||process.env.PAGES_COCKPIT_EVIDENCE_DIR||'.';
// Deterministic synthetic daily bars; OHLC are consistent (low <= open,close <= high).
function makeBars(n){const last=Math.floor(Date.now()/1000)-86400;return Array.from({length:n},(_,i)=>{const c=100+(i*7)%19+Math.floor(i/6);return{timestamp:last-(n-1-i)*86400,open:c-1,high:c+3,low:c-3,close:c,adjusted_close:c-2,volume:1000+i,session_status:'COMPLETE'};});}
const IDS=['SMA_5','SMA_20','SMA_60','SMA_120','EMA_20','RSI_14','MACD_12_26','MACD_SIGNAL_9','MACD_HISTOGRAM_12_26_9','ATR_14','BOLL_UPPER_20_2','BOLL_MIDDLE_20','BOLL_LOWER_20_2'];
const NO_DEFINITION=['VOLUME','RELATIVE','STRUCTURE'];
async function open(page,hash,selector){await page.evaluate(h=>{location.hash=h;},hash);await page.locator(selector).first().waitFor();}
async function noOverflow(page,label){assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'horizontal scroll '+label);}
async function values(page){return page.evaluate(()=>Object.fromEntries([...document.querySelectorAll('[data-indicator-cards] [data-card-value]')].map(n=>[n.dataset.cardValue,{text:n.textContent.trim(),state:n.dataset.state}])));}
async function seedBars(page,bars){
 await page.evaluate(async bars=>{
  const catalog=await (await fetch('actual-catalog.json')).json(),i=catalog.instruments.find(x=>x.ticker==='NVDA');
  await DeviceActual.restoreHoldings(window,catalog,DeviceActual.makeSnapshot(catalog,[{security_reference:i.security_reference,quantity:'3',average_cost:'120',currency:i.currency}]));
  await DeviceActual.sheetSettings(window,{schema:'device-google-sheet-settings/1',enabled:true,spreadsheet_id:'',range:'Quotes!A1:C22'});
  localStorage.setItem('investment.web.v1.private-history-origin',InvestmentAppConfig.privateHistoryWorkerOrigin);
  let connected=true,epoch=1;const listeners=new Set();window.__audit={reads:0};window.__logout=()=>{connected=false;epoch++;listeners.forEach(f=>f());};
  const session={state:()=>({enabled:true,connected}),revision:()=>epoch,setEnabled(){},subscribe:f=>{listeners.add(f);return()=>listeners.delete(f);},
   async fetchHistory(origin,symbol,range){window.__audit.reads++;return{schema:'private-history/1',provider:'Yahoo Finance(비공식)',symbol,range,currency:'USD',exchange:'NMS',timezone:'America/New_York',interval:'1d',basis:'RAW_CLOSE',delay_status:'UNKNOWN',read_at:new Date().toISOString(),bars};}};
  window.GoogleSheetQuotes={...GoogleSheetQuotes,sessionFor:()=>session};location.hash='technical/nvda';
 },bars);
}
(async()=>{
 let pass=0,phase='INIT';const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_EXECUTABLE_PATH});
 try{
  for(const width of [390,1440]){
   // ---- Empty device: logged out, no bars, nothing stored.
   phase='EMPTY '+width;
   {const context=await browser.newContext({viewport:{width,height:900},serviceWorkers:'block'}),page=await context.newPage();let errors=0,csp=0;
    page.on('pageerror',()=>errors++);page.on('console',m=>{if(m.text().includes('Content Security Policy'))csp++;});
    await page.route('**/*',r=>new URL(r.request().url()).origin===new URL(BASE).origin?r.continue():r.abort());
    await page.goto(BASE+'#technical');await page.locator('[data-indicator-cards]').waitFor();
    // S08
    assert.deepEqual(await page.locator('[data-indicator-card]').evaluateAll(n=>n.map(x=>x.dataset.indicatorCard)),['trend','momentum','volume','relative','structure','volatility']);
    assert.deepEqual(await page.locator('[data-indicator-mode]').evaluateAll(n=>n.map(x=>x.textContent)),['모델 지표','연구용 지표']);
    assert.equal(await page.locator('[data-indicator-mode="model"]').getAttribute('aria-pressed'),'true');
    let v=await values(page);assert.equal(Object.keys(v).length,6);
    for(const x of Object.values(v)){assert.ok(x.text.startsWith('NOT_AVAILABLE'),'model '+x.text);assert.equal(x.state,'NOT_AVAILABLE');}
    await page.locator('[data-indicator-mode="research"]').click();
    assert.ok((await page.locator('[data-indicator-note]').textContent()).includes('표시 전용 · 모델·QGV에 쓰지 않음'));
    v=await values(page);assert.ok(Object.keys(v).length>=16,'research rows '+Object.keys(v).length);
    for(const[k,x]of Object.entries(v)){assert.ok(x.text.startsWith('NOT_AVAILABLE'),k+' '+x.text);assert.equal(x.state,'NOT_AVAILABLE');assert.ok(!/^0(\.0+)?$/.test(x.text));}
    for(const k of NO_DEFINITION)assert.ok(v[k].text.includes('NOT_AVAILABLE'));
    for(const id of ['technical-phase','technical-qgv-context','technical-scenarios','technical-execution','technical-record'])assert.equal(await page.locator('#'+id).count(),1,id);
    for(const id of ['technical-phase','technical-qgv-context','technical-scenarios'])assert.ok((await page.locator('#'+id).textContent()).includes('NOT_AVAILABLE'),id);
    assert.ok((await page.locator('#technical-qgv-context').textContent()).includes('합치거나'));
    assert.ok((await page.locator('#technical-scenarios').textContent()).includes('확률 검증 전'));
    assert.equal(await page.locator('[data-screen-tab]').count(),4);
    await noOverflow(page,'technical '+width);
    await page.screenshot({path:SHOTS+'/technical-empty-'+width+'.png',fullPage:true}).catch(()=>{});
    // S09
    phase='MACRO '+width;await open(page,'macro','[data-macro-status]');
    assert.equal(await page.locator('[data-macro-regime]').textContent(),'자료 없음');
    assert.equal(await page.locator('#public-macro').count(),1);
    assert.deepEqual(await page.locator('[data-macro-section]').evaluateAll(n=>n.map(x=>x.dataset.macroSection)),['equity-state','regime-history','signal-evidence','scenarios','transmission']);
    for(const s of await page.locator('[data-macro-section]').all()){assert.ok((await s.textContent()).includes('NOT_AVAILABLE'));}
    assert.ok((await page.locator('#macro-signal-evidence').textContent()).includes('FRED/ALFRED'));
    assert.ok((await page.locator('#macro-scenarios').textContent()).includes('확률 검증 전'));
    assert.equal(await page.locator('#macro-scenarios td').filter({hasText:/\d/}).filter({hasNotText:/^S[123]$/}).count(),0);
    await noOverflow(page,'macro '+width);
    await page.screenshot({path:SHOTS+'/macro-'+width+'.png',fullPage:true}).catch(()=>{});
    // S10
    phase='VALIDATION '+width;await open(page,'validation','[data-hub="validation"]');
    assert.equal(await page.locator('[data-screen-tab]').count(),6);
    assert.ok((await page.locator('main .data-badges').textContent()).includes('UNCONFIRMED'));
    assert.deepEqual(await page.locator('[data-validation-section]').evaluateAll(n=>n.map(x=>x.dataset.validationSection)),['setup','equity-curve','quarterly','track-record','baseline','promotion']);
    const controls=await page.locator('[data-validation-section="setup"] select, [data-validation-section="setup"] input').evaluateAll(n=>n.map(x=>({disabled:x.disabled,value:x.value})));
    assert.equal(controls.length,5);for(const c of controls){assert.equal(c.disabled,true);assert.equal(c.value,'');}
    assert.deepEqual(await page.locator('#exp-profile option').allTextContents(),['NOT_AVAILABLE','균형','공격','방어']);
    assert.equal(await page.locator('#exp-count').getAttribute('min'),'1');assert.equal(await page.locator('#exp-count').getAttribute('max'),'30');
    assert.ok((await page.locator('#validation-equity-curve').textContent()).includes('100'));
    assert.deepEqual(await page.locator('#validation-track-record th').allTextContents(),['D+5','D+20','D+63','D+252']);
    assert.ok((await page.locator('#validation-track-record').textContent()).includes('과거 판단은 다시 쓰지 않음'));
    assert.ok((await page.locator('#validation-baseline').textContent()).includes('3개 시점 동결'));
    assert.ok((await page.locator('#validation-baseline').textContent()).includes('사용 금지 · UNCONFIRMED'));
    assert.equal(await page.locator('#validation-promotion button').isDisabled(),true);
    for(const s of await page.locator('[data-validation-section]').all())assert.ok((await s.textContent()).includes('NOT_AVAILABLE')||(await s.textContent()).includes('동결'));
    await page.locator('#validation-backtest').waitFor();
    await noOverflow(page,'validation '+width);
    await page.screenshot({path:SHOTS+'/validation-'+width+'.png',fullPage:true}).catch(()=>{});
    // nothing computed or selected is stored
    const keys=await page.evaluate(()=>Object.keys(localStorage).concat(Object.keys(sessionStorage)));
    assert.ok(!keys.some(k=>/indicator|technical|period/i.test(k)),'storage '+keys.join());
    assert.equal(errors,0,'page errors');assert.equal(csp,0,'csp');
    await context.close();}
   // ---- Populated: 260 bars (all warm-ups satisfied except optional SMA240) and 30 bars (warm-up shortfall).
   for(const count of [260,30]){
    phase='POPULATED '+count+' '+width;
    const context=await browser.newContext({viewport:{width,height:900},serviceWorkers:'block'}),page=await context.newPage();let errors=0,csp=0;
    page.on('pageerror',()=>errors++);page.on('console',m=>{if(m.text().includes('Content Security Policy'))csp++;});
    await page.route('**/*',r=>new URL(r.request().url()).origin===new URL(BASE).origin?r.continue():r.abort());
    await page.goto(BASE+'#settings');await page.locator('#device-backup-export').waitFor();
    await seedBars(page,makeBars(count));
    const root=page.locator('[data-private-history]');await root.locator('[data-history-action="fetch"]:enabled').waitFor();
    // Before the explicit click: every card is NOT_AVAILABLE (no auto fetch).
    await page.locator('[data-indicator-mode="research"]').click();
    for(const x of Object.values(await values(page)))assert.equal(x.state,'NOT_AVAILABLE');
    const before=await page.evaluate(()=>JSON.stringify(Object.entries(localStorage)));
    await root.locator('[data-history-action="fetch"]').click();await root.locator('[data-candle-index]').first().waitFor();
    assert.equal(await page.evaluate(()=>window.__audit.reads),1);
    // Expected values come from ResearchIndicators.calculate on the same bars.
    const result=await page.evaluate(bars=>{const r=ResearchIndicators.calculate(bars,{});return Object.fromEntries(r.indicators.map(i=>[i.indicator_id,i.values.at(-1)]));},makeBars(count));
    const shown=await values(page);
    for(const id of IDS){
     const want=result[id];
     if(want===null){assert.equal(shown[id].state,'NOT_AVAILABLE',id+' warm-up');assert.ok(shown[id].text.startsWith('NOT_AVAILABLE'),id);assert.ok(!/^0(\.0+)?$/.test(shown[id].text));}
     else{assert.equal(shown[id].state,'AVAILABLE',id);assert.equal(Number(shown[id].text.replace(/,/g,'')),Number(want.toFixed(2)),id);}
    }
    if(count===260){for(const id of IDS)assert.notEqual(result[id],null,id+' expected available');}
    else{for(const id of ['SMA_60','SMA_120','MACD_SIGNAL_9','MACD_HISTOGRAM_12_26_9'])assert.equal(shown[id].state,'NOT_AVAILABLE',id+' shortfall');
         for(const id of ['SMA_5','SMA_20','EMA_20','RSI_14','MACD_12_26','ATR_14'])assert.equal(shown[id].state,'AVAILABLE',id);}
    for(const k of NO_DEFINITION)assert.equal(shown[k].state,'NOT_AVAILABLE');
    assert.equal(await page.locator('[data-card-value="SMA_240"]').count(),0);
    // Optional SMA 240 appears only after the chart turns it on; 260 bars can show it, 30 bars show NOT_AVAILABLE.
    await root.locator('[data-chart-overlay="SMA_240"]').click();
    const s240=await page.locator('[data-card-value="SMA_240"]');assert.equal(await s240.count(),1);
    assert.equal(await s240.getAttribute('data-state'),count===260?'AVAILABLE':'NOT_AVAILABLE');
    // Model toggle stays NOT_AVAILABLE even with bars.
    await page.locator('[data-indicator-mode="model"]').click();
    for(const x of Object.values(await values(page))){assert.equal(x.state,'NOT_AVAILABLE');assert.ok(x.text.includes('모델 입력 미연결'));}
    await page.locator('[data-indicator-mode="research"]').click();
    // Nothing computed is stored.
    assert.equal(await page.evaluate(()=>JSON.stringify(Object.entries(localStorage))),before);
    assert.equal(await page.evaluate(()=>JSON.stringify(Object.entries(sessionStorage))),'[]');
    await noOverflow(page,'populated '+count+' '+width);
    if(count===260)await page.screenshot({path:SHOTS+'/technical-populated-'+width+'.png',fullPage:true}).catch(()=>{});
    // Logout clears the bars and every card returns to NOT_AVAILABLE.
    await page.evaluate(()=>window.__logout());await root.locator('[data-history-chart]').waitFor({state:'detached'});
    for(const x of Object.values(await values(page)))assert.equal(x.state,'NOT_AVAILABLE');
    assert.equal(errors,0,'page errors');assert.equal(csp,0,'csp');
    await context.close();pass++;console.log('PASS technical cards populated '+count+' bars '+width);
   }
   pass++;console.log('PASS technical macro validation empty device '+width);
  }
 }catch(error){console.log('FAIL technical macro validation '+phase+' '+(error&&error.message?error.message.split('\n')[0]:'')); process.exitCode=1;}
 finally{await browser.close();}
 console.log('COUNTS pass='+pass+' fail='+(process.exitCode?1:0));
})();
