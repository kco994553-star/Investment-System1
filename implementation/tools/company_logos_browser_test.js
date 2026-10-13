'use strict';
// Company logos: runtime-only images with a fallback chain (key service -> favicon -> letter circle) and an off switch.
// Every logo, favicon and TradingView origin is stubbed by route interception: no real network request is made.
// Places: search results, company header, watchlist (관심 기업), leaderboard, portfolio ACTUAL rows, investment report rows.
const {routeEmptyPublicScreens}=require('./empty_public_screens.js');
const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const SHOTS=path.resolve(process.env.TRADINGVIEW_SCREENSHOT_DIR||path.join(process.env.PAGES_COCKPIT_EVIDENCE_DIR||'/tmp/pages-browser-evidence','tradingview'));
const BASE=process.env.PAGES_COCKPIT_URL||'http://127.0.0.1:8990/';
const PNG=Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==','base64');
const KEY='pk_TESTONLY_12345678',LOGO_ORIGINS=['https://img.logo.dev','https://cdn.brandfetch.io','https://icons.duckduckgo.com'];
// Which synthetic domains each stub serves; everything else answers 404 (so the chain moves on).
const SERVES={'https://img.logo.dev':['nvidia.com'],'https://cdn.brandfetch.io':['nvidia.com'],'https://icons.duckduckgo.com':['nvidia.com','kla.com','hanmisemi.com']};
const PINNED={'NASDAQ:NVDA':'nvidia.com','NASDAQ:KLAC':'kla.com','NASDAQ:AMD':'amd.com','KRX:042700':'hanmisemi.com'};
let phase='START';
function domainOf(url){const u=new URL(url);return decodeURIComponent(u.pathname.replace(/^\/(ip3\/)?/,'').replace(/\.ico$/,''));}
async function session(browser,width){
 const context=await browser.newContext({viewport:{width,height:900},serviceWorkers:'block',locale:'ko-KR'});
 const log={logo:[],unexpected:0,unsafe:0,tv:0};
 await context.route('**/*',async route=>{const request=route.request(),url=new URL(request.url());
  if(request.method()!=='GET'){log.unsafe++;return route.abort();}
  if(url.origin===new URL(BASE).origin)return route.fallback();
  if(LOGO_ORIGINS.includes(url.origin)){const domain=domainOf(url.href),headers=await request.allHeaders();
   log.logo.push({origin:url.origin,domain,referer:headers.referer||null,query:url.search});
   return SERVES[url.origin].includes(domain)?route.fulfill({status:200,contentType:'image/png',body:PNG}):route.fulfill({status:404,contentType:'text/plain',body:'no'});}
  if(/tradingview/.test(url.hostname)){log.tv++;return route.abort();}
  log.unexpected++;return route.abort();});
 await routeEmptyPublicScreens(context);
 // Fixed domains for the checked rows, so live deploy builds (SEC/Wikidata rows) behave the same.
 await context.route('**/universe-domains.json*',async route=>{const response=await route.fetch(),payload=await response.json();
  for(const row of payload.rows){const fixed=PINNED[row[0]];if(fixed!==undefined){row[1]=fixed;row[2]=fixed?'manual':null;}}
  return route.fulfill({response,contentType:'application/json',body:JSON.stringify(payload)});});
 const page=await context.newPage();page.setDefaultTimeout(15000);
 const console_=[],errors=[];page.on('console',m=>console_.push(m.text()));page.on('pageerror',e=>errors.push(String(e&&e.message||e)));
 await page.addInitScript(()=>{window.__csp=0;document.addEventListener('securitypolicyviolation',()=>window.__csp++);});
 return {context,page,log,console_,errors};
}
async function go(page,hash,selector){await page.evaluate(h=>{location.hash=h;},hash);await page.locator(selector).first().waitFor();}
// Wait until a placeholder settles; returns {state, source, letter}.
async function settled(locator){
 await locator.scrollIntoViewIfNeeded();
 await locator.evaluate(n=>new Promise((resolve,reject)=>{const t=Date.now();(function poll(){const s=n.dataset.logoState;if(s==='img'||s==='letter')return resolve();if(Date.now()-t>10000)return reject(Error('logo state '+s));setTimeout(poll,50);})();}));
 return locator.evaluate(n=>({state:n.dataset.logoState,source:n.dataset.logoSource||null,letter:n.dataset.letter}));
}
async function search(page,text){await page.locator('#global-search').fill(text);await page.locator('#global-results li').first().waitFor();}
function contrast(fg,bg){const lum=c=>{const v=c.match(/\d+/g).slice(0,3).map(Number).map(x=>{x/=255;return x<=0.03928?x/12.92:((x+0.055)/1.055)**2.4;});return 0.2126*v[0]+0.7152*v[1]+0.0722*v[2];};const a=lum(fg),b=lum(bg);return (Math.max(a,b)+0.05)/(Math.min(a,b)+0.05);}
(async()=>{
 fs.mkdirSync(SHOTS,{recursive:true});
 const browser=await chromium.launch({headless:true,...(process.env.WEB_TEST_CHROMIUM_PATH?{executablePath:process.env.WEB_TEST_CHROMIUM_PATH}:{})});
 let pass=0;
 try{
  for(const width of [390,1440]){
   const s=await session(browser,width),{page,log}=s;
   phase=width+' DEFAULT-FAVICON';
   await page.goto(BASE+'#home');await page.locator('[data-home-dashboard]').waitFor();
   await search(page,'NVDA');
   const nv=await settled(page.locator('#global-results li .co-logo').first());
   assert.deepEqual([nv.state,nv.source],['img','favicon'],'no key: favicon is the first source');
   assert.ok(log.logo.every(r=>r.origin==='https://icons.duckduckgo.com'),'no key: no logo service request');
   assert.ok(log.logo.every(r=>r.referer===null),'favicon requests send no Referer');
   await search(page,'AMD');
   const amd=await settled(page.locator('#global-results li .co-logo').first());
   assert.deepEqual([amd.state,amd.letter],['letter','A'],'favicon 404 -> letter circle');
   assert.equal(await page.locator('#global-results li').first().evaluate(n=>n.textContent.includes('AMD')),true,'row text unchanged');
   await page.locator('#global-search').fill('');
   phase=width+' HEADER';
   await go(page,'company/nvda','h1 .co-logo-40');
   assert.deepEqual(Object.values(await settled(page.locator('h1 .co-logo-40'))).slice(0,2),['img','favicon']);
   assert.equal(await page.locator('h1').evaluate(n=>n.textContent.trim().startsWith('NVDA')),true,'header text unchanged');
   phase=width+' WATCHLIST';
   await page.locator('[data-star="nvda"]').first().click();
   await go(page,'watchlist','#watchlist-company-list .co-logo');
   assert.equal((await settled(page.locator('#watchlist-company-list .co-logo').first())).state,'img');
   phase=width+' LEADERBOARD';
   await go(page,'leaderboard','[data-leaderboard-row="nvda"] .co-logo');
   assert.equal((await settled(page.locator('[data-leaderboard-row="nvda"] .co-logo'))).state,'img');
   assert.equal((await settled(page.locator('[data-leaderboard-row="amd"] .co-logo'))).state,'letter');
   await page.locator('[data-leaderboard-row="asml"]').scrollIntoViewIfNeeded();await page.screenshot({path:path.join(SHOTS,'logos-leaderboard-'+width+'.png')});
   phase=width+' PORTFOLIO';
   await go(page,'actual','[data-security-index="5"]');
   const fill=async(index,quantity,average,price)=>{const row=page.locator('[data-security-index="'+index+'"]');await row.locator('[data-field="quantity"]').fill(quantity);await row.locator('[data-field="average_cost"]').fill(average);await row.locator('[data-field="price"]').fill(price);};
   await fill(4,'10','1000','3000');await fill(5,'1','100','100');await page.locator('[data-fx-currency="USD"] [data-field="rate"]').fill('1000');
   await page.locator('[data-action="save"]').click();await page.locator('[data-market-total]').filter({hasText:'130'}).waitFor();
   await go(page,'portfolio','#device-actual-summary .actual-value-row .co-logo');
   const rows=page.locator('#device-actual-summary .actual-value-row .co-logo');
   assert.equal(await rows.count(),2);
   for(let i=0;i<2;i++){const r=await settled(rows.nth(i));assert.equal(r.state,'img',JSON.stringify(r)+await rows.nth(i).getAttribute('data-logo-key'));}
   const sent=log.logo.map(r=>r.domain+r.query).join(' ');
   assert.ok(!/1000|3000|130|quantity|cost/.test(sent),'logo requests carry the domain only, never quantities or values');
   phase=width+' REPORT';
   await go(page,'report/real','#daily-report table .co-logo');
   assert.ok(await page.locator('#daily-report table .co-logo').count()>=2);
   assert.equal((await settled(page.locator('#daily-report table .co-logo').first())).state,'img');
   phase=width+' LETTER-COLOR';
   const circles=await page.evaluate(()=>{const a=CompanyLogos.html('NVDA'),b=CompanyLogos.html('NVDA'),t=document.createElement('div');t.innerHTML=CompanyLogos.html('ZZZ')+CompanyLogos.html('MMM');document.body.append(t);const out=[...t.children].map(n=>{const cs=getComputedStyle(n);return [cs.color,cs.backgroundColor];});t.remove();return {same:a===b,out};});
   assert.ok(circles.same,'color is deterministic per ticker');
   for(const[fg,bg]of circles.out)assert.ok(contrast(fg,bg)>=4.5,'letter contrast '+fg+' on '+bg);
   phase=width+' LOGODEV';
   await go(page,'settings','#logo-provider');
   await page.locator('#logo-provider').selectOption('logodev');await page.locator('#logo-key').fill(KEY);await page.locator('[data-logo-action="save"]').click();
   await page.locator('[data-logo-attribution="settings"]').waitFor();
   assert.equal(await page.locator('footer [data-logo-attribution="footer"] a').getAttribute('href'),'https://logo.dev');
   assert.equal(await page.evaluate(()=>localStorage.getItem('investment.web.v1.logo-key')),KEY);
   log.logo.length=0;
   await go(page,'company/nvda','h1 .co-logo-40');
   assert.deepEqual(Object.values(await settled(page.locator('h1 .co-logo-40'))).slice(0,2),['img','logodev']);
   const ld=log.logo.find(r=>r.origin==='https://img.logo.dev');
   assert.ok(ld&&ld.query.includes('token='+KEY)&&ld.referer===null,'logo.dev gets the device key and no Referer');
   await go(page,'company/klac','h1 .co-logo-40');
   assert.deepEqual(Object.values(await settled(page.locator('h1 .co-logo-40'))).slice(0,2),['img','favicon'],'service 404 -> favicon');
   await go(page,'company/amd','h1 .co-logo-40');
   assert.equal((await settled(page.locator('h1 .co-logo-40'))).state,'letter','service and favicon fail -> letter circle');
   phase=width+' BRANDFETCH';
   await go(page,'settings','#logo-provider');
   await page.locator('#logo-provider').selectOption('brandfetch');await page.locator('[data-logo-action="save"]').click();
   await page.locator('[data-logo-status]').filter({hasText:'저장'}).waitFor();
   assert.equal(await page.locator('[data-logo-attribution]').count(),0,'Brandfetch needs no attribution link');
   log.logo.length=0;
   await go(page,'company/nvda','h1 .co-logo-40');
   assert.deepEqual(Object.values(await settled(page.locator('h1 .co-logo-40'))).slice(0,2),['img','brandfetch']);
   const bf=log.logo.find(r=>r.origin==='https://cdn.brandfetch.io');
   assert.ok(bf&&bf.query==='?c='+KEY&&bf.referer&&new URL(bf.referer).origin===new URL(BASE).origin,'Brandfetch gets a Referer and the client id');
   phase=width+' OFF';
   await go(page,'settings','#logo-display');
   await page.locator('#logo-display').uncheck();await page.locator('[data-logo-status]').filter({hasText:'저장'}).waitFor();
   assert.equal(await page.evaluate(()=>localStorage.getItem('investment.web.v1.logo-display')),'off');
   await page.reload();await page.locator('#content').waitFor();
   log.logo.length=0;
   await search(page,'NVDA');assert.equal((await settled(page.locator('#global-results li .co-logo').first())).state,'letter');await page.locator('#global-search').fill('');
   for(const[hash,sel]of [['company/nvda','h1 .co-logo-40'],['watchlist','#watchlist-company-list .co-logo'],['leaderboard','[data-leaderboard-row="nvda"] .co-logo'],['portfolio','#device-actual-summary .actual-value-row .co-logo'],['report/real','#daily-report table .co-logo']]){
    await go(page,hash,sel);const r=await settled(page.locator(sel).first());assert.ok(r.state==='letter'&&/^[A-Z0-9]$/.test(r.letter),hash+' shows only the letter circle when off');assert.equal(await page.locator(sel).first().locator('img').count(),0);
   }
   await page.waitForTimeout(300);
   assert.equal(log.logo.length,0,'logo switch off: no logo or favicon request at all');
   phase=width+' PRIVACY';
   assert.ok(s.console_.every(t=>!t.includes(KEY)),'the key never reaches the console');
   assert.equal(await page.evaluate(()=>window.__csp),0,'zero CSP violations');
   assert.equal(log.unexpected+log.unsafe,0,'no unexpected or unsafe request');
   assert.deepEqual(s.errors,[]);
   await s.context.close();pass++;console.log('PASS company logos chain/places/off '+width);
  }
  console.log('COMPANY_LOGOS_BROWSER_OK checks='+pass);
 }catch(error){console.error('FAIL '+phase+': '+(error&&error.message||error));process.exitCode=1;}
 finally{await browser.close();}
})();
