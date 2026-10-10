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
  const stars=await page.evaluate(async()=>{
   const catalog=await (await fetch('actual-catalog.json')).json(),K=PublicScreens.STAR_KEY,mine=['0000000011','0000000022'],other=JSON.stringify(['0000000099']);
   if(DeviceBackup.STAR_KEY!==K||DeviceBackup.SCHEMA!=='investment-device-backup/3')return 'schema';
   const marker='SYNTHETIC-PRIVATE-MARKER',planted=['investment.web.v1.unified-sheet-source','investment.web.v1.universe-source','investment.web.v1.trades-source','investment.web.v1.private-history-origin','investment.web.v1.sheet-create-pending'];
   localStorage.setItem(K,JSON.stringify(mine));planted.forEach(k=>localStorage.setItem(k,JSON.stringify({spreadsheetId:marker,token:marker,workerOrigin:marker})));
   const backup=await DeviceBackup.read(window,catalog),text=JSON.stringify(backup);planted.forEach(k=>localStorage.removeItem(k));
   if(JSON.stringify(backup.investor_stars)!==JSON.stringify(mine)||text.includes(marker)||text.includes('market_data')||/token|spreadsheet|worker/i.test(Object.keys(backup.settings).join()))return 'export';
   localStorage.setItem(K,other);await DeviceBackup.restore(window,catalog,JSON.parse(text));
   if(JSON.stringify(PublicScreens.readStars(localStorage))!==JSON.stringify(mine))return 'restore3';
   for(const schema of ['investment-device-backup/2','investment-device-backup/1']){
    const old={...backup,schema};delete old.investor_stars;if(schema.endsWith('/1'))delete old.profiles;
    localStorage.setItem(K,other);await DeviceBackup.restore(window,catalog,old);if(localStorage.getItem(K)!==other)return 'legacy'+schema;
    localStorage.removeItem(K);await DeviceBackup.restore(window,catalog,old);if(localStorage.getItem(K)!==null)return 'legacy-absent'+schema;
   }
   localStorage.setItem(K,other);const personal=localStorage.getItem('investment.web.v1.personal');
   for(const bad of [['0000000011','0000000011'],['11'],Array.from({length:51},(_,i)=>String(i+1).padStart(10,'0'))]){
    try{await DeviceBackup.restore(window,catalog,{...backup,investor_stars:bad});return 'invalid';}catch(_){}
    if(localStorage.getItem(K)!==other||localStorage.getItem('investment.web.v1.personal')!==personal)return 'invalid-write';
   }
   const api=window.DeviceActual;window.DeviceActual={...api,restoreHoldings:async()=>{throw Error('STORAGE');}};
   try{await DeviceBackup.restore(window,catalog,backup);return 'rollback';}catch(_){}finally{window.DeviceActual=api;}
   return localStorage.getItem(K)===other?'ok':'rollback-write';
  });
  page.on('dialog',d=>d.accept());const K='investment.web.v1.investor-stars';
  const file=async(payload,name)=>{await page.locator('#device-backup-import').setInputFiles({name,mimeType:'application/json',buffer:Buffer.from(JSON.stringify(payload))});};
  const exported=await page.evaluate(async()=>{localStorage.setItem('investment.web.v1.investor-stars',JSON.stringify(['0000000033']));return DeviceBackup.read(window,await (await fetch('actual-catalog.json')).json());});
  await page.evaluate(k=>localStorage.setItem(k,JSON.stringify(['0000000044'])),K);await file(exported,'v3.json');
  await page.waitForFunction(k=>localStorage.getItem(k)===JSON.stringify(['0000000033']),K,{timeout:8000});
  const v2={...exported,schema:'investment-device-backup/2',preferences:{version:1,interests:['legacy-interest'],groups:[]}};delete v2.investor_stars;
  await page.locator('#device-backup-import').waitFor();await file(v2,'v2.json');
  await page.waitForFunction(()=>JSON.parse(localStorage.getItem('investment.web.v1.personal')||'{}').interests?.[0]==='legacy-interest',undefined,{timeout:8000});
  const ui=await page.evaluate(k=>localStorage.getItem(k),K)===JSON.stringify(['0000000033'])&&await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth);
  if(stars==='ok'&&ui){pass++;console.log('PASS investor stars backup schema 3 browser '+width);}else{fail++;console.log('FAIL investor stars backup schema 3 browser '+width+' '+stars+' ui='+ui);}
  await context.close();
 }}catch(_){fail++;console.log('FAIL backup browser fixed diagnostic');}finally{await browser.close();}
 console.log('COUNTS pass='+pass+' fail='+fail);if(fail)process.exitCode=1;
})();
