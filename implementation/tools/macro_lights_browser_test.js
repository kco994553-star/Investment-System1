'use strict';
// Macro lights v1 (PLAYBOOK_V1 13-5) on the macro screen: public employment/inflation/curve lights from a synthetic
// macro-screen.json, the device market light from a stubbed Worker session (synthetic SPY bars, RAM only), the credit
// light blocked until HYG/IEF are allowed, "매크로(n/5 경고등)", 정상/경고/위기, low confidence and the previous rule under 자세히.
const assert=require('node:assert/strict');const {chromium}=require('playwright');
const {EMPTY,routeEmptyPublicScreens}=require('./empty_public_screens.js');
const BASE=process.env.PAGES_COCKPIT_URL,SHOTS=process.env.PAGES_COCKPIT_EVIDENCE_DIR||'.';
const A='a'.repeat(64),B='b'.repeat(64),AT='2026-01-01T00:00:00+00:00';
function macroScreen(){
 const p=structuredClone(EMPTY['macro-screen.json']);p.state='LIVE';p.sources=[{agency:'BLS',sha256:A,acquired_at:AT},{agency:'TREASURY',sha256:B,acquired_at:AT}];
 const L=p.data.macro_lights_v1.lights;
 Object.assign(L.employment,{state:'LIVE',lit:true,reason:'LIT',as_of:'2025-12',inputs:[{sha256:A,acquired_at:AT}],values:{period:'2025-12',avg3:4.6,low12:4.0,low12_count:12,gap:0.6}});
 Object.assign(L.inflation,{state:'LIVE',lit:false,reason:'NOT_LIT',as_of:'2025-12',inputs:[{sha256:A,acquired_at:AT}],values:{period:'2025-12',base_period:'2024-12',yoy:0.03}});
 Object.assign(L.curve,{state:'LIVE',lit:true,reason:'LIT',as_of:'2025-12-31',inputs:[{sha256:B,acquired_at:AT}],values:{date:'2025-12-31',ten_year:4.2,three_month:4.5,spread:-0.3,run_days:25}});
 return p;
}
// Synthetic SPY bars (about 5 years of weekdays, a 30 % fall in the last 40 sessions). Not market data.
function bars(){const out=[];let d=Date.UTC(2021,9,11),v=100,s=12345;
 for(let i=0;out.length<1260;i++,d+=864e5){const w=new Date(d).getUTCDay();if(w===0||w===6)continue;s=(s*1103515245+12345)%2147483648;
  v=v*(1+0.0003+0.01*(s/2147483648*2-1));out.push({timestamp:d/1000+48600,open:v,high:v,low:v,close:v,adjusted_close:v,volume:1,session_status:'COMPLETE'});}
 for(let i=out.length-40;i<out.length;i++){const c=out[i-1].close*0.991;Object.assign(out[i],{open:c,high:c,low:c,close:c,adjusted_close:c});}
 return out;}
async function open(page,hash,selector){await page.evaluate(h=>{location.hash=h;},hash);await page.locator(selector).first().waitFor();}
async function noOverflow(page,label){assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'horizontal scroll '+label);}
async function storage(page){return page.evaluate(()=>JSON.stringify(Object.entries(localStorage).sort())+JSON.stringify(Object.entries(sessionStorage).sort()));}
async function context(browser,width,payload){
 const ctx=await browser.newContext({viewport:{width,height:900},serviceWorkers:'block'});await routeEmptyPublicScreens(ctx);
 if(payload)await ctx.route('**/macro-screen.json*',r=>r.fulfill({status:200,contentType:'application/json',body:JSON.stringify(payload)}));
 const page=await ctx.newPage(),seen={errors:0,outside:[],writes:[]};page.on('pageerror',()=>seen.errors++);
 page.on('request',r=>{if(r.method()!=='GET')seen.writes.push(r.method());});
 await page.route('**/*',r=>{const url=new URL(r.request().url());if(url.origin===new URL(BASE).origin)return r.fallback();seen.outside.push(url.host);return r.abort();});
 return{ctx,page,seen};
}
async function lights(page){return page.locator('[data-macro-light]').evaluateAll(n=>n.map(x=>[x.dataset.macroLight,x.dataset.macroLightState]));}
(async()=>{
 let pass=0,phase='INIT';const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_EXECUTABLE_PATH});
 try{
  for(const width of [390,1280]){
   phase='EMPTY '+width;
   {const {ctx,page,seen}=await context(browser,width,null);
    await page.goto(BASE+'#macro');await page.locator('[data-macro-lights]').waitFor();
    assert.deepEqual(await lights(page),[['employment','NO_DATA'],['inflation','NO_DATA'],['curve','NO_DATA'],['market','NO_DATA'],['credit','NO_DATA']]);
    assert.equal(await page.locator('[data-macro-lights-count]').textContent(),'매크로(0/5 경고등)');
    assert.equal(await page.locator('[data-macro-lights-verdict]').textContent(),'매크로 확인 불가');
    assert.equal(await page.locator('[data-macro-low-confidence]').textContent(),'판정 신뢰도 낮음');
    assert.ok((await page.locator('[data-macro-light="credit"]').textContent()).includes('기기 가격을 불러오지 않았습니다'));
    assert.equal(await page.locator('[data-macro-lights-marker]').textContent(),'v1 · UNCALIBRATED');
    assert.ok((await page.locator('[data-macro-lights]').textContent()).includes('매도 판단에는 쓰지 않습니다'));
    assert.equal(await page.locator('[data-macro-regime]').textContent(),'자료 없음');
    assert.deepEqual(await page.evaluate(()=>MacroLights.current()),{state:null,lit_count:0,available_count:0,low_confidence:true});
    assert.ok((await page.locator('[data-macro-unavailable]').textContent()).includes('확대 제한 없음'));
    assert.equal(seen.errors,0);assert.deepEqual(seen.outside,[]);await ctx.close();pass++;}
   phase='PUBLIC '+width;
   {const {ctx,page,seen}=await context(browser,width,macroScreen());
    await page.goto(BASE+'#home');await page.locator('main').waitFor();
    await page.waitForFunction(()=>MacroLights.current()&&MacroLights.current().available_count===3);
    assert.deepEqual(await page.evaluate(()=>MacroLights.current()),{state:'WARNING',lit_count:2,available_count:3,low_confidence:false},'state is in RAM before the macro screen opens');
    await open(page,'macro','[data-macro-lights]');
    assert.deepEqual(await lights(page),[['employment','ON'],['inflation','OFF'],['curve','ON'],['market','NO_DATA'],['credit','NO_DATA']]);
    assert.deepEqual(await page.locator('[data-macro-light-label]').allTextContents(),['켜짐','꺼짐','켜짐','자료 없음','자료 없음']);
    assert.equal(await page.locator('[data-macro-lights-count]').textContent(),'매크로(3/5 경고등)');
    assert.equal(await page.locator('[data-macro-lights-verdict]').textContent(),'경고');assert.equal(await page.locator('[data-macro-low-confidence]').count(),0);
    const emp=await page.locator('[data-macro-light="employment"]').textContent();for(const s of ['4.60%','4.0%','0.60%p','2025-12','BLS LNS14000000'])assert.ok(emp.includes(s),s);
    const cur=await page.locator('[data-macro-light="curve"]').textContent();for(const s of ['25거래일','2025-12-31','U.S. Treasury'])assert.ok(cur.includes(s),s);
    assert.ok((await page.locator('[data-macro-light="market"]').textContent()).includes('기기 가격 계산 · RAM만'));
    assert.ok((await page.locator('[data-macro-light="credit"]').textContent()).includes('추정'));
    assert.equal(await page.locator('[data-macro-lights-reasons]').getAttribute('data-macro-lights-reasons'),'LIT_COUNT_EQ_2');
    // The previous v0.1.1 result is only under 자세히.
    const legacy=page.locator('[data-macro-legacy-state]');assert.equal(await legacy.isVisible(),false);
    await page.locator('[data-macro-legacy] summary').click();assert.ok((await legacy.textContent()).startsWith('이전 기준(v0.1.1): NOT_AVAILABLE'));
    assert.equal(await page.locator('[data-macro-v0-engine]').isVisible(),false);
    // Without an approved Worker address and a Google session the Worker is never asked.
    assert.equal(await page.locator('[data-macro-lights-load]').count(),0);
    assert.equal(await page.locator('[data-macro-lights-status]').textContent(),'ORIGIN_UNAPPROVED');
    await noOverflow(page,'public '+width);await page.screenshot({path:SHOTS+'/macro-lights-public-'+width+'.png',fullPage:true}).catch(()=>{});
    assert.equal(seen.errors,0);assert.deepEqual(seen.outside,[]);await ctx.close();pass++;}
   phase='DEVICE '+width;
   {const {ctx,page,seen}=await context(browser,width,macroScreen());
    await page.goto(BASE+'#home');await page.locator('main').waitFor();
    await page.evaluate(spy=>{localStorage.setItem('investment.web.v1.private-history-origin',InvestmentAppConfig.privateHistoryWorkerOrigin);window.__reads=[];
     const session={state:()=>({enabled:true,connected:true}),revision:()=>1,setEnabled(){},subscribe:()=>()=>{},
      async fetchHistory(origin,symbol,range){window.__reads.push([symbol,range]);if(symbol!=='SPY')throw Error('REQUEST_INVALID');
       return{schema:'private-history/1',provider:'Yahoo Finance(비공식)',symbol,range,currency:'USD',exchange:'PCX',timezone:'America/New_York',interval:'1d',basis:'RAW_CLOSE',delay_status:'UNKNOWN',read_at:'2026-10-10T21:00:00Z',bars:spy};}};
     window.GoogleSheetQuotes={...GoogleSheetQuotes,sessionFor:()=>session};},bars());
    const before=await storage(page);
    await open(page,'macro','[data-macro-lights-load]');
    assert.deepEqual(await page.evaluate(()=>window.__reads),[],'no request before the click');
    await page.locator('[data-macro-lights-load]').click();
    await page.locator('[data-macro-lights-status="READY"]').waitFor();
    assert.deepEqual(await page.evaluate(()=>window.__reads),[['SPY','5y'],['HYG','1y']],'old Worker rejects HYG; credit fails closed without retry');
    assert.deepEqual(await lights(page),[['employment','ON'],['inflation','OFF'],['curve','ON'],['market','ON'],['credit','NO_DATA']]);
    const market=await page.locator('[data-macro-light="market"]').textContent();assert.ok(/52주 고점 대비 -\d+\.\d{2}%/.test(market),market);
    assert.equal(await page.locator('[data-macro-lights-verdict]').textContent(),'위기');
    assert.equal(await page.locator('[data-macro-lights-count]').textContent(),'매크로(4/5 경고등)');
    assert.equal(await page.locator('[data-macro-lights-reasons]').getAttribute('data-macro-lights-reasons'),'LIT_COUNT_GE_3');
    assert.deepEqual(await page.evaluate(()=>MacroLights.current()),{state:'CRISIS',lit_count:3,available_count:4,low_confidence:false});
    assert.equal(await storage(page),before,'nothing is stored');assert.deepEqual(seen.writes,[],'nothing is sent');
    assert.ok(!(await storage(page)).includes('%'));
    // Matching Worker release: all three requested symbols succeed; ratio computed in RAM.
    await page.evaluate(spy=>{const session={state:()=>({enabled:true,connected:true}),revision:()=>1,setEnabled(){},subscribe:()=>()=>{},
     async fetchHistory(origin,symbol,range){window.__reads.push([symbol,range]);return{schema:'private-history/1',provider:'Yahoo Finance(비공식)',symbol,range,currency:'USD',exchange:'PCX',timezone:'America/New_York',interval:'1d',basis:'RAW_CLOSE',delay_status:'UNKNOWN',read_at:'2026-10-10T21:00:00Z',bars:spy};}};
     window.GoogleSheetQuotes={...GoogleSheetQuotes,sessionFor:()=>session};},bars());
    await open(page,'home','main');await open(page,'macro','[data-macro-lights-load]');
    await page.locator('[data-macro-lights-load]').click();await page.locator('[data-macro-lights-status="READY"]').waitFor();
    assert.deepEqual((await page.evaluate(()=>window.__reads)).slice(-3),[['SPY','5y'],['HYG','1y'],['IEF','1y']]);
    assert.equal((await page.evaluate(()=>MacroLights.current())).available_count,5);
    assert.equal(await storage(page),before);assert.deepEqual(seen.writes,[]);
    await noOverflow(page,'device '+width);await page.screenshot({path:SHOTS+'/macro-lights-device-'+width+'.png',fullPage:true}).catch(()=>{});
    assert.equal(seen.errors,0);assert.deepEqual(seen.outside,[]);await ctx.close();pass++;}
  }
  console.log('MACRO_LIGHTS_BROWSER_OK pass='+pass);
 }catch(e){console.error('MACRO_LIGHTS_BROWSER_FAIL '+phase+' '+(e&&e.message));process.exitCode=1;}
 finally{await browser.close();}
})();
