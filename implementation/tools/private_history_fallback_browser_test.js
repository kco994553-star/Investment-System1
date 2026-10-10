'use strict';const {chromium}=require('playwright');
(async()=>{let pass=0,fail=0,phase='INIT';const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_EXECUTABLE_PATH});
try{for(const width of [390,1440]){
 const context=await browser.newContext({viewport:{width,height:900},serviceWorkers:'block'}),page=await context.newPage();let csp=0;page.on('console',m=>{if(m.text().includes('Content Security Policy'))csp++;});
 await page.route('**/*',r=>new URL(r.request().url()).origin===new URL(process.env.PAGES_COCKPIT_URL).origin?r.continue():r.abort());await page.goto(process.env.PAGES_COCKPIT_URL+'#settings');await page.locator('#device-backup-export').waitFor();
 phase='SEED';await page.evaluate(async()=>{
  const catalog=await (await fetch('actual-catalog.json')).json(),i=catalog.instruments.find(x=>x.ticker==='NVDA');await DeviceActual.restoreHoldings(window,catalog,DeviceActual.makeSnapshot(catalog,[{security_reference:i.security_reference,quantity:'3',average_cost:'120',currency:i.currency}]));
  await DeviceActual.sheetSettings(window,{schema:'device-google-sheet-settings/1',enabled:true,spreadsheet_id:'',range:'Quotes!A1:C22'});localStorage.setItem('investment.web.v1.private-history-origin',InvestmentAppConfig.privateHistoryWorkerOrigin);
  let connected=true,epoch=1;const listeners=new Set();window.__chartAudit={reads:0};window.__chartLogout=()=>{connected=false;epoch++;listeners.forEach(f=>f());};
  const session={state:()=>({enabled:true,connected}),revision:()=>epoch,setEnabled(){},subscribe:f=>{listeners.add(f);return()=>listeners.delete(f);},async fetchHistory(origin,symbol,range){window.__chartAudit.reads++;const last=Math.floor(Date.now()/1000)-86400;return{schema:'private-history/1',provider:'Tiingo EOD',timestamp_kind:'PROVIDER_SESSION_LABEL',symbol,range,currency:'USD',exchange:'NASDAQ',timezone:'America/New_York',interval:'1d',basis:'RAW_CLOSE',delay_status:'UNKNOWN',read_at:new Date().toISOString(),bars:Array.from({length:260},(_,i)=>({timestamp:Math.floor((last-(259-i)*86400)/86400)*86400,session_date:new Date((last-(259-i)*86400)*1000).toISOString().slice(0,10),open:100+i,high:103+i,low:98+i,close:101+i,adjusted_close:99+i,volume:1,session_status:'COMPLETE'}))};}};
  window.GoogleSheetQuotes={...GoogleSheetQuotes,sessionFor:()=>session};location.hash='technical/nvda';
 });
 phase='READY';const root=page.locator('[data-private-history]');await root.locator('[data-history-action="fetch"]:enabled').waitFor();
 if(await page.evaluate(()=>window.__chartAudit.reads)!==0)throw Error('AUTO_READ');phase='FETCH';await root.locator('[data-history-action="fetch"]').click();phase='AVERAGE';await root.locator('[data-average-line]').waitFor({state:'attached'});
 phase='LOADED';if(await root.locator('[data-candle-index]').count()!==260||await root.locator('[data-indicator="SMA_120"]').count()!==1||await root.locator('[data-indicator="SMA_240"]').count()!==0)throw Error('CHART');
 phase='OVERLAY';await root.locator('[data-chart-overlay="SMA_240"]').click();await root.locator('[data-indicator="SMA_240"]').waitFor();await root.locator('[data-chart-overlay="AVG"]').click();if(await root.locator('[data-average-line]').count()!==0)throw Error('AVG');
 if(await page.evaluate(()=>window.__chartAudit.reads)!==1||csp||await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('BOUNDARY');
 await page.evaluate(()=>window.__chartLogout());await root.locator('[data-history-chart]').waitFor({state:'detached'});if(await root.locator('[data-research-value]').count())throw Error('RAM');
 pass++;console.log('PASS fallback candle date MA AVG browser '+width);await context.close();
}}catch(error){fail++;const code=['AUTO_READ','CHART','AVG','BOUNDARY','RAM'].includes(error.message)?error.message:'BROWSER_FAILURE';console.log('FAIL chart browser '+phase+' '+code);}finally{await browser.close();}console.log('COUNTS pass='+pass+' fail='+fail);if(fail)process.exitCode=1;})();
