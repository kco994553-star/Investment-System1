'use strict';
const {chromium}=require('playwright');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_EXECUTABLE_PATH});let pass=0,fail=0;
 try{for(const width of [390,1440]){
  const context=await browser.newContext({viewport:{width,height:900},serviceWorkers:'block'}),page=await context.newPage();
  await page.route('**/*',route=>new URL(route.request().url()).origin===new URL(process.env.PAGES_COCKPIT_URL).origin?route.continue():route.abort());
  await page.goto(process.env.PAGES_COCKPIT_URL+'#settings');await page.locator('#device-backup-export').waitFor();
  const valid=await page.evaluate(async()=>{
   const catalog=await (await fetch('actual-catalog.json')).json(),i=catalog.instruments[0];
   const p={version:1,interests:['synthetic-interest'],groups:[{id:'synthetic-group',name:'Synthetic',members:['synthetic-interest']}]};
   const s=DeviceActual.makeSnapshot(catalog,[{security_reference:i.security_reference,quantity:'3',average_cost:'7',currency:i.currency}]);
   const backup=DeviceBackup.create(p,{version:1,display_locale:'en-US',source_language:'ko'},s,catalog,DeviceMarket,AppLanguage);
   await DeviceBackup.restore(window,catalog,backup);const roundtrip=await DeviceBackup.read(window,catalog);
   const stored=roundtrip.portfolio.themes.flatMap(x=>x.holdings);
   if(stored.length!==1||stored[0].quantity!=='3'||roundtrip.preferences.groups[0].members[0]!=='synthetic-interest'||roundtrip.settings.display_locale!=='en-US')return false;
   if(JSON.stringify(roundtrip).includes('market_data'))return false;
   const before=JSON.stringify(await DeviceActual.readHoldings(window,catalog)),raw=localStorage.getItem('investment.web.v1.personal');
   try{await DeviceBackup.restore(window,catalog,{...backup,settings:{...backup.settings,workerOrigin:'not-allowed'}});return false;}catch(_){}
   if(before!==JSON.stringify(await DeviceActual.readHoldings(window,catalog))||raw!==localStorage.getItem('investment.web.v1.personal'))return false;
   const api=window.DeviceActual,meta=localStorage.getItem('investment.web.v1.settings');
   window.DeviceActual={...api,restoreHoldings:async()=>{throw Error('STORAGE');}};
   try{await DeviceBackup.restore(window,catalog,DeviceBackup.create({version:1,interests:[],groups:[]},AppLanguage.settings(),null,catalog,DeviceMarket,AppLanguage));return false;}catch(_){}finally{window.DeviceActual=api;}
   if(raw!==localStorage.getItem('investment.web.v1.personal')||meta!==localStorage.getItem('investment.web.v1.settings')||before!==JSON.stringify(await DeviceActual.readHoldings(window,catalog)))return false;
   const empty=DeviceBackup.create(p,AppLanguage.settings(),null,catalog,DeviceMarket,AppLanguage);
   await DeviceBackup.restore(window,catalog,empty);if(await DeviceActual.readHoldings(window,catalog)!==null)return false;
   return document.documentElement.scrollWidth<=innerWidth;
  });
  if(valid){pass++;console.log('PASS backup restore browser '+width);}else{fail++;console.log('FAIL backup restore browser '+width);}
  await context.close();
 }}catch(_){fail++;console.log('FAIL backup browser fixed diagnostic');}finally{await browser.close();}
 console.log('COUNTS pass='+pass+' fail='+fail);if(fail)process.exitCode=1;
})();
