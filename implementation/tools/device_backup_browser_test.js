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
   if(DeviceBackup.STAR_KEY!==K||DeviceBackup.SCHEMA!=='investment-device-backup/4')return 'schema';
   const marker='SYNTHETIC-PRIVATE-MARKER',planted=['investment.web.v1.unified-sheet-source','investment.web.v1.universe-source','investment.web.v1.trades-source','investment.web.v1.private-history-origin','investment.web.v1.sheet-create-pending'];
   localStorage.setItem(K,JSON.stringify(mine));planted.forEach(k=>localStorage.setItem(k,JSON.stringify({spreadsheetId:marker,token:marker,workerOrigin:marker})));
   const backup=await DeviceBackup.read(window,catalog),text=JSON.stringify(backup);planted.forEach(k=>localStorage.removeItem(k));
   if(JSON.stringify(backup.investor_stars)!==JSON.stringify(mine)||text.includes(marker)||text.includes('market_data')||/token|spreadsheet|worker/i.test(Object.keys(backup.settings).join()))return 'export';
   localStorage.setItem(K,other);await DeviceBackup.restore(window,catalog,JSON.parse(text));
   if(JSON.stringify(PublicScreens.readStars(localStorage))!==JSON.stringify(mine))return 'restore3';
   for(const schema of ['investment-device-backup/2','investment-device-backup/1']){
    const old={...backup,schema};delete old.investor_stars;delete old.playbook;if(schema.endsWith('/1'))delete old.profiles;
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
  const v2={...exported,schema:'investment-device-backup/2',preferences:{version:1,interests:['legacy-interest'],groups:[]}};delete v2.investor_stars;delete v2.playbook;
  await page.locator('#device-backup-import').waitFor();await file(v2,'v2.json');
  await page.waitForFunction(()=>JSON.parse(localStorage.getItem('investment.web.v1.personal')||'{}').interests?.[0]==='legacy-interest',undefined,{timeout:8000});
  const ui=await page.evaluate(k=>localStorage.getItem(k),K)===JSON.stringify(['0000000033'])&&await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth);
  if(stars==='ok'&&ui){pass++;console.log('PASS investor stars backup schema 3 browser '+width);}else{fail++;console.log('FAIL investor stars backup schema 3 browser '+width+' '+stars+' ui='+ui);}
  // opt-in user-objects section (/5): chart notes/scenarios + macro estimate history (synthetic anchors only), via the settings UI
  const CK='investment.web.v1.chart-user-objects',MK='investment.web.v1.macro-cycle-user-estimate',NOW='2026-10-20T00:00:00.000Z';
  const note={schema:'chart-annotation/1',id:'u-bk0001',kind:'LINE',symbol:'SYNTH',interval:'D',price_basis:'RAW_CLOSE',author:'USER',points:[{time:'2025-01-06',price:100},{time:'2025-02-03',price:110}],text:'synthetic',created_at:NOW,updated_at:NOW};
  const hist={schema:'macro-cycle-user-estimate/2',rings:{economy:Array.from({length:60},(_,i)=>({seq:i+1,saved_at:'2026-10-20T'+String(Math.floor((i+1)/60)).padStart(2,'0')+':'+String((i+1)%60).padStart(2,'0')+':00Z',from:{phase:'회복',part:'초입'},to:{phase:'확장',part:'후반'},note:'synthetic '+(i+1),system:{state:'NOT_COMPUTED',text:'미산출',reason:'NO_MODEL_OUTPUT',layer:null,model_id:null,as_of:null}}))}};
  const chartRaw=JSON.stringify({schema:'chart-user-objects/1',items:[note]}),macroRaw=JSON.stringify(hist);
  await page.evaluate(([a,b,c,d])=>{localStorage.setItem(a,b);localStorage.setItem(c,d);},[CK,chartRaw,MK,macroRaw]);
  await page.locator('#device-backup-export').waitFor();
  const grab=async()=>{const dl=page.waitForEvent('download');await page.locator('#device-backup-export').click();return JSON.parse(require('node:fs').readFileSync(await (await dl).path(),'utf8'));};
  const plain=await grab();await page.locator('#device-backup-user-objects').check();const withUser=await grab();
  let userOk=plain.schema==='investment-device-backup/4'&&!('user_objects' in plain)&&withUser.schema==='investment-device-backup/5'&&withUser.user_objects.chart.items.length===1&&withUser.user_objects.macro.rings.economy.length===60;
  await page.evaluate(([a,c])=>{localStorage.removeItem(a);localStorage.removeItem(c);},[CK,MK]);
  await page.locator('#device-backup-import').waitFor();await file(withUser,'v5.json');
  await page.waitForFunction(k=>JSON.parse(localStorage.getItem(k)||'null')?.rings?.economy?.length===60,MK,{timeout:8000});
  userOk=userOk&&await page.evaluate(k=>JSON.parse(localStorage.getItem(k)).items.length,CK)===1&&JSON.stringify(JSON.parse(await page.evaluate(k=>localStorage.getItem(k),MK)))===JSON.stringify(hist);
  const merged=await page.evaluate(async([v5,CK,MK])=>{const catalog=await (await fetch('actual-catalog.json')).json();await DeviceBackup.restore(window,catalog,v5);
   return [JSON.parse(localStorage.getItem(CK)).items.length,JSON.parse(localStorage.getItem(MK)).rings.economy.length];},[withUser,CK,MK]);
  userOk=userOk&&merged[0]===1&&merged[1]===60;
  const refused=await page.evaluate(async([v5,v4,CK,MK])=>{const catalog=await (await fetch('actual-catalog.json')).json(),c=localStorage.getItem(CK),m=localStorage.getItem(MK),out=[];
   for(const bad of [{...v5,user_objects:{...v5.user_objects,chart:{...v5.user_objects.chart,items:[{...v5.user_objects.chart.items[0],close:101}]}}},{...v5,user_objects:{...v5.user_objects,macro:{...v5.user_objects.macro,series:[1]}}},{...v5,user_objects:{...v5.user_objects,quotes:[]}}]){
    try{await DeviceBackup.restore(window,catalog,bad);out.push(false);}catch(_){out.push(localStorage.getItem(CK)===c&&localStorage.getItem(MK)===m);}}
   await DeviceBackup.restore(window,catalog,v4);out.push(localStorage.getItem(CK)===c&&localStorage.getItem(MK)===m);return out;},[withUser,plain,CK,MK]);
  userOk=userOk&&refused.length===4&&refused.every(Boolean)&&await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth);
  if(userOk){pass++;console.log('PASS user objects backup schema 5 browser '+width);}else{fail++;console.log('FAIL user objects backup schema 5 browser '+width+' '+JSON.stringify(refused)+' '+JSON.stringify(merged));}
  await context.close();
 }}catch(_){fail++;console.log('FAIL backup browser fixed diagnostic');}finally{await browser.close();}
 console.log('COUNTS pass='+pass+' fail='+fail);if(fail)process.exitCode=1;
})();
