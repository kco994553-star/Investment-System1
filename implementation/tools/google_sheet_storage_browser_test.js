"use strict";
// All observation/settings canaries are constructed and checked in browser memory.
// This tool never saves a populated screenshot, export, identifier or token.
const {chromium} = require('playwright');
const base = process.env.GOOGLE_SHEET_QUOTES_URL || new URL('#actual', process.env.PAGES_COCKPIT_URL || 'http://127.0.0.1:8990/Investment-System1/').href;
let checks = 0;
function verify(value, label) { if (!value) throw new Error(label); checks++; }
(async () => {
  const browser = await chromium.launch({headless:true, executablePath:process.env.WEB_TEST_CHROMIUM_PATH || undefined});
  const context = await browser.newContext();
  let external = 0;
  await context.route('**/*', route => {
    if (new URL(route.request().url()).origin !== new URL(base).origin) {external++; return route.abort();}
    return route.continue();
  });
  try {
    const page = await context.newPage();
    await page.goto(base);
    await page.locator('[data-security-index]').last().waitFor();
    verify(await page.evaluate(() => typeof DeviceActual.sheetSettings === 'function' && typeof DeviceActual.applyMarketImport === 'function'), 'device import helpers exist');
    const result = await page.evaluate(async () => {
      const catalog = await (await fetch('actual-catalog.json')).json();
      const now = Date.now() - 60000, timestamp = new Date(now).toISOString();
      const read = async key => {
        const db = await new Promise(resolve => {const r=indexedDB.open('investment-device-actual-v1',1);r.onsuccess=()=>resolve(r.result);});
        try {return await new Promise(resolve => {const tx=db.transaction('snapshots','readonly'),r=tx.objectStore('snapshots').get(key);r.onsuccess=()=>resolve(r.result);});}
        finally {db.close();}
      };
      const put = async (key,value) => {
        const db = await new Promise(resolve => {const r=indexedDB.open('investment-device-actual-v1',1);r.onsuccess=()=>resolve(r.result);});
        try {await new Promise((resolve,reject)=>{const tx=db.transaction('snapshots','readwrite');tx.objectStore('snapshots').put(value,key);tx.oncomplete=resolve;tx.onabort=()=>reject(Error('storage'));});}
        finally {db.close();}
      };
      const out = {};
      const settings = await DeviceActual.sheetSettings(window);
      out.defaultOff = !settings.enabled && settings.spreadsheet_id === '' && settings.range === 'Quotes!A1:C22';
      const id = ['synthetic',...Array(7).fill('device')].join('_');
      const saved = await DeviceActual.sheetSettings(window,{...settings,enabled:true,spreadsheet_id:id});
      out.deviceSettings = saved.spreadsheet_id === id && (await read('google-sheet-settings')).spreadsheet_id === id;
      let rejected = false;
      try {await DeviceActual.sheetSettings(window,{...saved,access_token:['ya','29.'].join('')+'x'.repeat(32)});} catch (_) {rejected=true;}
      out.secretRejected = rejected && JSON.stringify(await DeviceActual.sheetSettings(window)) === JSON.stringify(saved);
      const instrument = catalog.instruments[0];
      const quote = {security_reference:instrument.security_reference,price:String(10+7),currency:instrument.currency,as_of:timestamp,available_at:timestamp,source:'GOOGLEFINANCE',time_status:'KNOWN'};
      const batch = {quotes:[quote],fx:[],successes:[{code:'NASDAQ:ASML',name:instrument.label}],failures:[],warnings:[]};
      await DeviceActual.applyMarketImport(window,catalog,batch,{now,method:'paste'});
      const first = await read('market');
      const history = await read('market-import-history');
      out.historyRecord = first.version === 1 && history.entries.length === 1 && history.entries[0].quotes[0].price === quote.price;
      const failed = {quotes:[],fx:[],successes:[],failures:[{code:'NASDAQ:ASML',name:instrument.label,state:'NOT_AVAILABLE'}],warnings:[]};
      await DeviceActual.applyMarketImport(window,catalog,failed,{now,method:'google-sheet'});
      out.failurePreserves = JSON.stringify(await read('market')) === JSON.stringify(first);
      out.oneBatch = (await DeviceActual.readMarketImportHistory(window,catalog)).length === 2;
      const secondQuote = {...quote,price:String(20+7)};
      await DeviceActual.applyMarketImport(window,catalog,{...batch,quotes:[secondQuote]},{now,method:'paste'});
      out.newRecord = (await read('market')).version === 2 && (await read('market-import-history')).entries.length === 3;
      const snapshot = DeviceActual.makeSnapshot(catalog,[],null,timestamp);
      const backup = JSON.stringify(DeviceMarket.exportBackup(snapshot,await read('market'),catalog));
      out.backupExcludes = !backup.includes(id) && !backup.includes('google-sheet-settings') && !backup.includes('access_token') && !backup.includes('market-import-history');
      const before = JSON.stringify(await read('market'));
      const beforeHistory = JSON.stringify(await read('market-import-history'));
      rejected = false;
      try {await DeviceActual.applyMarketImport(window,catalog,batch,{now,method:'paste',isCurrent:()=>false});} catch (_) {rejected=true;}
      out.cancelPreserves = rejected && JSON.stringify(await read('market')) === before && JSON.stringify(await read('market-import-history')) === beforeHistory;
      const race = await Promise.allSettled([1,2].map(()=>DeviceActual.applyMarketImport(window,catalog,batch,{now,method:'paste'})));
      out.atomicRace = race.filter(r=>r.status==='fulfilled').length === 1 && (await read('market-import-history')).entries.length === 4;
      await put('market-import-history',{schema:'corrupt'});
      const marketBefore = JSON.stringify(await read('market'));
      rejected = false;
      try {await DeviceActual.applyMarketImport(window,catalog,batch,{now,method:'paste'});} catch (_) {rejected=true;}
      out.corruptionPreserves = rejected && JSON.stringify(await read('market')) === marketBefore && (await read('market-import-history')).schema === 'corrupt';
      return out;
    });
    for (const [name,passed] of Object.entries(result)) verify(passed,name);
    verify(external === 0,'no external calls');
    console.log('PASS Google sheet device storage: '+checks+' checks; no payload files');
  } catch (_) {console.error('FAIL Google sheet device storage verification (payload details omitted)');process.exitCode=1;}
  finally {await context.close();await browser.close();}
})();
