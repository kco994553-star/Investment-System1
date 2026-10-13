'use strict';
// TradingView display-only widgets (ticker tape / mini chart / full chart). TradingView never sees a real request:
// the embed scripts and the widget frame origin are stubbed by route interception, logo origins are aborted.
// Checks: lazy insertion per screen, the off switch, blocked-script fallback, the TSE/KRX availability notes,
// zero CSP violations, and that no app value, storage or export reads from the (cross-origin) widget.
const {routeEmptyPublicScreens}=require('./empty_public_screens.js');
const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const BASE=process.env.PAGES_COCKPIT_URL||'http://127.0.0.1:8990/';
const SHOTS=path.resolve(process.env.TRADINGVIEW_SCREENSHOT_DIR||path.join(process.env.PAGES_COCKPIT_EVIDENCE_DIR||'/tmp/pages-browser-evidence','tradingview'));
const ASSETS=path.join(__dirname,'../src/investment_system/product/web_assets');
const NOTE='표시 전용 · 계산에 쓰지 않음',NOT_SHOWN='이 종목은 TradingView 무료 위젯에서 표시되지 않음',CANARY='99123.45';
const SCRIPT_RE=/^https:\/\/s3\.tradingview\.com\/external-embedding\/embed-widget-(ticker-tape|mini-symbol-overview|advanced-chart)\.js$/;
// Stub of an embed script: reads its own config text and adds one cross-origin iframe, like the real widget.
const STUB=`(function(){var s=document.currentScript,cfg=JSON.parse(s.textContent),name=s.src.match(/embed-widget-([a-z-]+)\\.js/)[1];
(window.__tvStub=window.__tvStub||[]).push({name:name,symbol:cfg.symbol||null,symbols:(cfg.symbols||[]).map(function(x){return x.proName}),locale:cfg.locale,keys:Object.keys(cfg).sort()});
var f=document.createElement('iframe');f.title='TradingView '+name;f.src='https://www.tradingview-widget.com/embed-widget/'+name+'/?locale='+cfg.locale+'#'+encodeURIComponent(JSON.stringify(cfg));
(s.parentNode.querySelector('.tradingview-widget-container__widget')||s.parentNode).appendChild(f);})();`;
const FRAME='<!doctype html><meta charset="utf-8"><body style="margin:0;font:13px sans-serif;background:#eef3f8"><p style="margin:8px">TradingView stub · NVDA '+CANARY+' · +1.23%</p><script>parent.postMessage({price:'+CANARY+',symbol:"NASDAQ:NVDA"},"*")</script></body>';
let phase='START';
async function session(browser,width,{scriptMode='stub'}={}){
 const context=await browser.newContext({viewport:{width,height:900},serviceWorkers:'block',locale:'ko-KR'});
 const traffic={scripts:[],frames:0,unexpected:0,unsafe:0,logos:0};
 // Registered first, so the empty-public-screen routes (registered after) are tried before it.
 await context.route('**/*',async route=>{const request=route.request(),url=new URL(request.url());
  if(request.method()!=='GET'){traffic.unsafe++;return route.abort();}
  if(url.origin===new URL(BASE).origin)return route.fallback();
  if(SCRIPT_RE.test(url.href)){traffic.scripts.push(url.pathname.split('/').pop());return scriptMode==='abort'?route.abort('blockedbyclient'):route.fulfill({status:200,contentType:'application/javascript',body:STUB});}
  if(url.origin==='https://www.tradingview-widget.com'){traffic.frames++;return route.fulfill({status:200,contentType:'text/html',body:FRAME});}
  if(['https://icons.duckduckgo.com','https://img.logo.dev','https://cdn.brandfetch.io'].includes(url.origin)){traffic.logos++;return route.abort();}
  traffic.unexpected++;return route.abort();});
 await routeEmptyPublicScreens(context);
 const page=await context.newPage();page.setDefaultTimeout(15000);
 const errors=[];page.on('pageerror',e=>errors.push(String(e&&e.message||e)));
 await page.addInitScript(()=>{window.__csp=0;document.addEventListener('securitypolicyviolation',()=>window.__csp++);});
 return {context,page,traffic,errors};
}
async function go(page,hash,selector){await page.evaluate(h=>{location.hash=h;},hash);await page.locator(selector).first().waitFor();}
async function noHorizontalScroll(page,label){assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),label+': no horizontal scroll');}
(async()=>{
 fs.mkdirSync(SHOTS,{recursive:true});
 const browser=await chromium.launch({headless:true,...(process.env.WEB_TEST_CHROMIUM_PATH?{executablePath:process.env.WEB_TEST_CHROMIUM_PATH}:{})});
 let pass=0;
 try{
  for(const width of [390,1440]){
   const s=await session(browser,width),{page,traffic}=s;
   phase=width+' LAZY';
   await page.goto(BASE+'#macro');await page.locator('[data-ia-screen="macro"]').waitFor();
   assert.equal(traffic.scripts.length,0,'no widget script before a widget screen is opened');
   assert.equal(await page.locator('script[src*="s3.tradingview.com"]').count(),0);
   phase=width+' TICKER';
   await go(page,'home','[data-tv-widget="ticker"] iframe');
   assert.deepEqual(traffic.scripts,['embed-widget-ticker-tape.js']);
   const ticker=page.locator('[data-tv-widget="ticker"]');
   assert.equal(await ticker.locator('[data-tv-note]').textContent(),NOTE);
   const tape=(await page.evaluate(()=>window.__tvStub))[0];
   assert.equal(tape.name,'ticker-tape');assert.equal(tape.locale,'kr');
   assert.equal(tape.symbols.length,18,'TARGET 19 minus the symbol free widgets do not show');
   for(const sym of ['NASDAQ:ASML','NASDAQ:NVDA','NYSE:SYK','NYSE:GEV','KRX:042700'])assert.ok(tape.symbols.includes(sym),sym);
   assert.ok(!tape.symbols.includes('TSE:8035'));
   assert.ok((await ticker.locator('[data-tv-excluded]').textContent()).includes(NOT_SHOWN));
   assert.ok((await ticker.locator('[data-tv-unverified]').textContent()).includes('KRX:042700'));
   assert.equal(await ticker.locator('iframe').evaluate(f=>new URL(f.src).origin),'https://www.tradingview-widget.com');
   assert.equal(await ticker.locator('iframe').evaluate(f=>f.contentDocument),null,'widget frame is cross-origin: the app cannot read it');
   await noHorizontalScroll(page,'home');await page.screenshot({path:path.join(SHOTS,'tradingview-home-'+width+'.png'),fullPage:false});
   phase=width+' MINI';
   await go(page,'company/nvda','[data-tv-widget="mini"] iframe');
   const mini=page.locator('[data-tv-widget="mini"]');
   assert.equal(await mini.locator('[data-tv-note]').textContent(),NOTE);
   assert.equal((await page.evaluate(()=>window.__tvStub)).at(-1).symbol,'NASDAQ:NVDA');
   await mini.scrollIntoViewIfNeeded();await page.screenshot({path:path.join(SHOTS,'tradingview-company-'+width+'.png')});
   const before=traffic.scripts.length;
   await go(page,'company/tokyo_electron','[data-tv-widget="mini"] [data-tv-fallback="notDisplayed"]');
   assert.ok((await page.locator('[data-tv-fallback="notDisplayed"]').textContent()).includes(NOT_SHOWN));
   assert.equal(traffic.scripts.length,before,'TSE:8035 loads no widget script');
   await go(page,'company/hanmi','[data-tv-widget="mini"] iframe');
   assert.equal((await page.evaluate(()=>window.__tvStub)).at(-1).symbol,'KRX:042700');
   assert.equal(await page.locator('[data-tv-widget="mini"] [data-tv-unverified]').count(),1);
   phase=width+' ADVANCED';
   await go(page,'technical','[data-tv-widget="advanced"] iframe');
   const adv=page.locator('[data-tv-widget="advanced"]');
   assert.equal(await adv.locator('[data-tv-note]').textContent(),NOTE);
   assert.equal((await page.evaluate(()=>window.__tvStub)).at(-1).symbol,'NASDAQ:ASML');
   await page.locator('[data-technical-symbol]').selectOption('stry');
   await page.waitForFunction(()=>window.__tvStub.at(-1).symbol==='NYSE:SYK');
   await adv.scrollIntoViewIfNeeded();await noHorizontalScroll(page,'technical');await page.screenshot({path:path.join(SHOTS,'tradingview-technical-'+width+'.png')});
   const stub=await page.evaluate(()=>window.__tvStub);
   for(const entry of stub)assert.ok(entry.keys.every(k=>!/price|quantity|cost|amount|token|sheet|holding/i.test(k)),'widget config carries symbols and display options only');
   phase=width+' NO-READ';
   // The stub frame shows and posts a canary price. Nothing in the app may pick it up.
   await go(page,'company/nvda','[data-tv-widget="mini"] iframe');await page.waitForTimeout(300);
   assert.ok((await page.locator('[data-value="quote"]').first().textContent()).includes('NO_DEVICE_PRICE'),'valuation never takes a price from the widget');
   const leaks=await page.evaluate(c=>{const out=[];if(document.body.innerText.includes(c))out.push('dom');if(JSON.stringify({...localStorage,...sessionStorage}).includes(c))out.push('storage');return out;},CANARY);
   assert.deepEqual(leaks,[]);
   phase=width+' OFF';
   await go(page,'technical','[data-tv-widget="advanced"] [data-tv-toggle="off"]');
   await page.locator('[data-tv-widget="advanced"] [data-tv-toggle="off"]').click();
   await page.locator('[data-tv-widget="advanced"] [data-tv-disabled]').waitFor();
   assert.equal(await page.locator('[data-tv-frame]').count(),0,'off switch removes the widget frame');
   assert.equal(await page.evaluate(()=>localStorage.getItem('investment.web.v1.tradingview-widgets')),'off');
   const offCount=traffic.scripts.length;
   await go(page,'home','[data-tv-widget="ticker"] [data-tv-disabled]');await go(page,'company/nvda','[data-tv-widget="mini"] [data-tv-disabled]');
   assert.equal(traffic.scripts.length,offCount,'no widget script while off');
   await go(page,'settings','[data-tv-setting]');
   assert.equal(await page.locator('[data-tv-setting]').isChecked(),false);
   await page.locator('[data-tv-setting]').check();
   assert.equal(await page.evaluate(()=>localStorage.getItem('investment.web.v1.tradingview-widgets')),null);
   await go(page,'home','[data-tv-widget="ticker"] iframe');
   assert.equal(await page.evaluate(()=>window.__csp),0,'zero CSP violations');
   assert.equal(traffic.unexpected+traffic.unsafe,0,'no unexpected or unsafe request');
   assert.deepEqual(s.errors,[]);
   await s.context.close();pass++;console.log('PASS TradingView widgets lazy/off/no-read '+width);
   phase=width+' BLOCKED';
   const b=await session(browser,width,{scriptMode:'abort'});
   await b.page.goto(BASE+'#home');await b.page.locator('[data-tv-widget="ticker"] [data-tv-fallback="blocked"]').waitFor();
   assert.ok((await b.page.locator('[data-tv-fallback="blocked"]').textContent()).includes('TradingView'));
   assert.equal(await b.page.locator('[data-tv-frame]').count(),0);
   await b.page.screenshot({path:path.join(SHOTS,'tradingview-blocked-home-'+width+'.png')});
   assert.deepEqual(b.errors,[]);await b.context.close();pass++;console.log('PASS TradingView blocked-script fallback '+width);
  }
  phase='STATIC';
  // Only the widget module touches widget DOM or TradingView; other modules only mount it with a company id.
  for(const name of fs.readdirSync(ASSETS).filter(n=>/\.(js|html)$/.test(n))){
   const text=fs.readFileSync(path.join(ASSETS,name),'utf8');
   if(name==='tradingview-widgets.js')continue;
   assert.ok(!/tradingview-widget-container|data-tv-frame|__tvStub/.test(text),name+' never reads widget DOM');
   if(/TradingViewWidgets\./.test(text))assert.equal(name,'app.js',name+' must not use the widget API');
   // Existing same-origin bridges only; a TradingView frame message never passes their origin check.
   assert.ok(!/addEventListener\(\s*['"]message['"]/.test(text)||['app.js','research-bridge.js','network-bridge.js'].includes(name),name+' adds no message listener');
  }
  const app=fs.readFileSync(path.join(ASSETS,'app.js'),'utf8');
  assert.ok(/e\.origin===location\.origin && e\.source===research\?\.contentWindow/.test(app)&&/e\.origin !== location\.origin \|\|/.test(app),'app message listener accepts same-origin frames only');
  assert.deepEqual([...app.matchAll(/TradingViewWidgets\.(\w+)/g)].map(m=>m[1]).sort(),['mountAdvanced','mountMini','mountSettings','mountTickerTape']);
  pass++;console.log('PASS TradingView static isolation');
  console.log('TRADINGVIEW_WIDGETS_BROWSER_OK checks='+pass+' screenshots='+fs.readdirSync(SHOTS).filter(n=>n.startsWith('tradingview-')).length);
 }catch(error){console.error('FAIL '+phase+': '+(error&&error.message||error));process.exitCode=1;}
 finally{await browser.close();}
})();
