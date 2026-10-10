'use strict';const {chromium}=require('playwright'),assert=require('node:assert/strict');
(async()=>{const b=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_EXECUTABLE_PATH});let pass=0,fail=0;
 try{for(const width of [390,1440]){const c=await b.newContext({viewport:{width,height:900},serviceWorkers:'block'}),p=await c.newPage();let errors=0;p.on('pageerror',()=>errors++);
  try{await p.goto(process.env.PAGES_COCKPIT_URL+'#settings');await p.locator('[data-ops-status]').waitFor();assert.equal(await p.locator('[data-ops-row]').count(),6);
   const states=await p.locator('[data-ops-state]').allTextContents();assert.ok(states.every(s=>/^(LIVE|STALE|NOT_AVAILABLE)( · STALE)?$/.test(s)));
   await p.goto(process.env.PAGES_COCKPIT_URL+'#home');await p.locator('[data-data-basis] a[href="#settings"]').waitFor();
   assert.ok(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));assert.equal(errors,0);pass++;console.log('PASS ops status '+width);}
  catch(e){fail++;console.log('FAIL ops status '+width+' '+(e.code==='ERR_ASSERTION'?'CONTRACT':'EXECUTION'));}finally{await c.close();}}}
 finally{await b.close();}console.log('COUNTS pass='+pass+' fail='+fail);process.exitCode=fail?1:0;})();
