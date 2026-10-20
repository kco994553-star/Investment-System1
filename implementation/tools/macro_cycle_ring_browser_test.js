'use strict';
// Macro cycle rings (FRONTEND_INTERACTION_CONTRACT_20261019 §4-8) at 390 (touch) and 1280 (mouse): wrap-around both ways by drag,
// keyboard and buttons, no rewind, vertical swipe is page scroll, no model = no arc ("미산출"), abstain, interval edges incl. the
// last→first wrap, reaction to a new publication (focus kept once turned), validated-only transition text, reduced motion, no
// overflow, separate rings, the device-only user estimate kept apart from the official layer, no probability text, no non-GET
// request. Publications here are synthetic draft §4-2 objects passed to MacroCycleRing.setPublication (publication file and
// schema are not decided: PM-2). Not model output, not market data.
const assert=require('node:assert/strict');const {chromium}=require('playwright');
const {routeEmptyPublicScreens}=require('./empty_public_screens.js');
const BASE=process.env.PAGES_COCKPIT_URL,SHOTS=process.env.PAGES_COCKPIT_EVIDENCE_DIR||'.';
const EV=(family,label,extra)=>({family,label,period:'2026-07~2026-09',release_at:'2026-10-02T12:30:00Z',release_basis:'SCHEDULE',acquired_at:'2026-10-02T13:05:00Z',source:'synthetic',rule_version:'synthetic/0',v0:true,...extra});
const out=(cycle,from,to,extra)=>({cycle,model_id:'synthetic-phase/'+cycle,layer:'EXPLORATORY_V0',status:'ESTIMATED_INTERVAL',interval:{from,to},point:null,probability:{state:'NOT_COMPUTED'},
 supporting:[EV('C','synthetic curve line'),EV('PO','synthetic output line',{release_basis:'CAPTURE',release_at:null})],opposing:[EV('LU','synthetic labour line')],mixed:[],missing:[{family:'MO',reason:'SOURCE_NOT_COLLECTED'}],
 as_of:'2026-10-15T00:00:00Z',oldest_input_release_at:'2026-07-30T12:30:00Z',...extra});
const P=(phase,part)=>({phase,part});
async function noOverflow(page,label){assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'horizontal scroll '+label);}
async function context(browser,width){
 const touch=width<600;
 const ctx=await browser.newContext({viewport:{width,height:900},serviceWorkers:'block',hasTouch:touch,isMobile:touch});await routeEmptyPublicScreens(ctx);
 const page=await ctx.newPage(),seen={errors:[],outside:[],writes:[]};page.on('pageerror',e=>seen.errors.push(String(e&&e.message||e).split('\n')[0]));
 page.on('request',r=>{if(r.method()!=='GET')seen.writes.push(r.method()+' '+r.url());});
 await page.route('**/*',r=>{const url=new URL(r.request().url());if(url.origin===new URL(BASE).origin)return r.fallback();seen.outside.push(url.host);return r.abort();});
 return{ctx,page,seen,touch};
}
const R=c=>'[data-cycle-ring="'+c+'"]';
async function focusOf(page,c){return page.locator(R(c)+' [data-cycle-phase][aria-selected="true"]').getAttribute('data-cycle-phase');}
async function turnDeg(page,c){return Number(await page.locator(R(c)+' svg').getAttribute('data-cycle-turn-deg'));}
async function live(page){return page.locator('[data-cycle-live]').textContent();}
async function settle(page,c){await page.waitForFunction(sel=>{const s=document.querySelector(sel+' svg');return s&&Math.abs(Number(s.dataset.cycleDisplayDeg)-Number(s.dataset.cycleTurnDeg))<1e-6;},R(c));}
async function openMacro(page){await page.goto(BASE+'#macro');await page.locator('[data-cycle-root]').waitFor();await page.locator('[data-macro-lights]').waitFor();}
// drag horizontally by `cells` ring cells (pixels per cell = max(60, drag width / 3), a UI constant of the ring)
async function drag(page,c,cells,touch,cdp){
 const box=await page.locator(R(c)+' [data-cycle-drag]').boundingBox(),px=Math.max(60,box.width/3),y=box.y+box.height*0.5,x0=box.x+box.width*0.5+(cells>0?px*cells/2:-px*(-cells)/2),x1=x0-px*cells;
 const steps=12;
 if(touch){await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x:x0,y}]});
  for(let i=1;i<=steps;i++)await cdp.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x:x0+(x1-x0)*i/steps,y}]});
  await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});}
 else{await page.mouse.move(x0,y);await page.mouse.down();await page.mouse.move(x1,y,{steps});await page.mouse.up();}
 await settle(page,c);
}
(async()=>{
 let pass=0,phase='INIT';const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_EXECUTABLE_PATH});
 try{
  for(const width of [390,1280]){
   const {ctx,page,seen,touch}=await context(browser,width);const cdp=touch?await ctx.newCDPSession(page):null;
   phase='EMPTY '+width;await openMacro(page);
   // macro lights reference mode stays visible and unchanged
   assert.equal(await page.locator('[data-macro-lights-marker]').textContent(),'v1 · UNCALIBRATED');
   assert.equal(await page.locator('[data-macro-reference-only]').textContent(),'참고 표시 · 과거 재생 완료 전에는 확대 차단·U3에 쓰지 않음');
   assert.equal(await page.locator('[data-cycle-frame]').textContent(),'화면 틀 · 예시 · 사용자 입력');
   // 7 no model = no interval: every ring NOT_COMPUTED, reason, no arc, no point, concept svg only, no probability
   for(const c of ['economy','market','industry']){
    assert.equal(await page.locator(R(c)).getAttribute('data-cycle-state'),'NOT_COMPUTED',c);
    const txt=await page.locator(R(c)).textContent();
    assert.ok(txt.includes('공식 판정: 미산출'),c+' official');assert.ok(txt.includes(c==='industry'?'업종 그룹을 고르지 않음':'위치 판정 모델 없음'),c+' reason');
    assert.ok(txt.includes('확률 미산출'),c);assert.equal(await page.locator(R(c)+' [data-cycle-transition="NOT_COMPUTED"]').count(),1,c+' transition');
    assert.ok(txt.includes('미정(소유자 결정)'),c+' open values');assert.ok(txt.includes('기준 미정'),c+' up/hold/down');
    for(const k of ['근거 패턴','전환 조건','반대 증거','판정 유보 조건'])assert.ok(txt.includes(k),c+' '+k);
   }
   const root=page.locator('[data-cycle-root]');
   assert.equal(await page.locator('[data-cycle-interval]').count(),0);assert.equal(await page.locator('[data-cycle-user-arc]').count(),0);
   assert.equal(await root.locator('svg:not([data-cycle-kind="concept"]), canvas, circle, [data-cycle-point]').count(),0,'concept svg only, no point');
   const rootText=await root.textContent();assert.ok(!/%|확률\s*[:：]?\s*\d|\d+\s*\/\s*\d+\s*·\s*기간/.test(rootText),'no probability text');
   assert.ok(rootText.includes('순환은 둘러보기 순서일 뿐입니다'));
   assert.equal(await focusOf(page,'economy'),'회복');assert.equal(await focusOf(page,'market'),'바닥');
   assert.equal(await page.locator(R('economy')+' [data-cycle-phase][tabindex="0"]').count(),1);
   assert.match(await page.locator(R('economy')+' svg').getAttribute('aria-label'),/^경기 국면 개념도 · 4개 국면 · 보는 국면 회복\(1\/4\) · 미산출$/);
   pass++;console.log('PASS cycle ring empty '+width);
   // 14 width: no overflow, ◀ ▶ visible
   phase='WIDTH '+width;await noOverflow(page,'macro '+width);
   for(const s of ['[data-cycle-prev]','[data-cycle-next]']){const b=await page.locator(R('economy')+' '+s).boundingBox();assert.ok(b&&b.x>=0&&b.x+b.width<=width,s+' visible');}
   {const b=await page.locator(R('economy')+' svg').boundingBox();assert.ok(b.width<=width-32+0.5,'ring diameter <= width - 32');}
   await page.locator('#macro-cycle-ring').screenshot({path:SHOTS+'/macro-cycle-ring-empty-'+width+'.png'}).catch(()=>{});
   // 4 buttons: N and 2N presses come back; 5 cumulative angle
   phase='BUTTONS '+width;
   const d0=await turnDeg(page,'economy');
   for(let i=0;i<4;i++)await page.locator(R('economy')+' [data-cycle-next]').click();
   assert.equal(await focusOf(page,'economy'),'회복');assert.equal(await turnDeg(page,'economy'),d0+360);
   for(let i=0;i<8;i++)await page.locator(R('economy')+' [data-cycle-next]').click();
   assert.equal(await focusOf(page,'economy'),'회복');assert.equal(await turnDeg(page,'economy'),d0+1080);
   await page.locator(R('economy')+' [data-cycle-prev]').click();assert.equal(await focusOf(page,'economy'),'수축');assert.ok((await live(page)).includes('마지막으로'));
   assert.equal(await page.evaluate(()=>document.activeElement&&document.activeElement.hasAttribute('data-cycle-prev')),true,'focus stays on the button');
   pass++;console.log('PASS cycle ring buttons '+width);
   // 3 keyboard wrap, Home/End, focus on the selected tab
   phase='KEYBOARD '+width;
   await page.locator(R('economy')+' [data-cycle-phase][aria-selected="true"]').focus();
   await page.keyboard.press('ArrowRight');assert.equal(await focusOf(page,'economy'),'회복');assert.ok((await live(page)).includes('수축 다음은 회복 · 처음으로'));
   assert.equal(await page.evaluate(()=>document.activeElement.dataset.cyclePhase),'회복');
   await page.keyboard.press('ArrowLeft');assert.equal(await focusOf(page,'economy'),'수축');
   await page.keyboard.press('Home');assert.equal(await focusOf(page,'economy'),'회복');
   await page.keyboard.press('End');assert.equal(await focusOf(page,'economy'),'수축');
   await page.keyboard.press('ArrowDown');assert.equal(await focusOf(page,'economy'),'회복');await page.keyboard.press('ArrowUp');assert.equal(await focusOf(page,'economy'),'수축');
   pass++;console.log('PASS cycle ring keyboard '+width);
   // 1, 2, 5 drag wrap last→first and first→last, +360/N only, multi-cell drag
   phase='DRAG '+width;await settle(page,'economy');
   {const before=await turnDeg(page,'economy');await drag(page,'economy',1.2,touch,cdp);
    assert.equal(await focusOf(page,'economy'),'회복','drag left from last = first');assert.equal(await turnDeg(page,'economy'),before+90,'no rewind');
    assert.ok((await live(page)).includes('처음으로'));
    assert.equal(await page.locator(R('economy')+' [data-cycle-phase="회복"]').getAttribute('aria-selected'),'true');
    await drag(page,'economy',-1.2,touch,cdp);assert.equal(await focusOf(page,'economy'),'수축','drag right from first = last');assert.equal(await turnDeg(page,'economy'),before);
    assert.ok((await live(page)).includes('마지막으로'));
    await drag(page,'economy',2.2,touch,cdp);assert.equal(await focusOf(page,'economy'),'확장','two cells');assert.equal(await turnDeg(page,'economy'),before+180);
    await drag(page,'economy',0.1,touch,cdp);assert.equal(await focusOf(page,'economy'),'확장','small move snaps back');}
   pass++;console.log('PASS cycle ring drag '+width);
   // 6 vertical swipe does not turn (and scrolls the page on touch)
   phase='VERTICAL '+width;
   {const box=await page.locator(R('economy')+' [data-cycle-drag]').boundingBox(),x=box.x+box.width/2,y=box.y+box.height*0.7,f=await focusOf(page,'economy'),deg=await turnDeg(page,'economy');
    if(touch){const sy=await page.evaluate(()=>scrollY);await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x,y}]});
     for(let i=1;i<=10;i++)await cdp.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x:x+1,y:y-16*i}]});await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
     await page.waitForTimeout(200);assert.ok(await page.evaluate(()=>scrollY)>sy,'vertical swipe scrolls the page');}
    else{await page.mouse.move(x,y);await page.mouse.down();await page.mouse.move(x+3,y-160,{steps:8});await page.mouse.up();}
    assert.equal(await focusOf(page,'economy'),f);assert.equal(await turnDeg(page,'economy'),deg);
    assert.equal(await page.locator(R('economy')+' [data-cycle-drag]').evaluate(n=>getComputedStyle(n).touchAction),'pan-y');}
   pass++;console.log('PASS cycle ring vertical '+width);
   // cell tap turns to that cell
   phase='TAP '+width;
   {const cell=page.locator(R('economy')+' [data-cycle-cell="2"]'),b=await cell.boundingBox();
    if(touch)await page.touchscreen.tap(b.x+b.width/2,b.y+b.height/2);else await page.mouse.click(b.x+b.width/2,b.y+b.height/2);
    await settle(page,'economy');assert.equal(await focusOf(page,'economy'),'둔화');}
   pass++;console.log('PASS cycle ring tap '+width);
   // 16 separate rings
   phase='SEPARATE '+width;
   await page.locator('[data-cycle-tab="market"]').click();assert.equal(await page.locator(R('market')).isVisible(),true);assert.equal(await page.locator(R('economy')).isVisible(),false);
   assert.equal(await focusOf(page,'market'),'바닥');assert.equal(await turnDeg(page,'market'),0);
   await page.locator(R('market')+' [data-cycle-next]').click();assert.equal(await focusOf(page,'market'),'상승 초기');assert.equal(await focusOf(page,'economy'),'둔화');
   await page.locator('[data-cycle-tab="market"]').focus();await page.keyboard.press('ArrowLeft');assert.equal(await page.locator('[data-cycle-tab="economy"]').getAttribute('aria-selected'),'true');
   pass++;console.log('PASS cycle ring separate '+width);
   // 15 full re-render keeps focus (macro is a full re-render screen)
   phase='REMOUNT '+width;
   await page.evaluate(()=>{location.hash='#home';});await page.locator('[data-home]').first().waitFor();await page.evaluate(()=>{location.hash='#macro';});await page.locator('[data-cycle-root]').waitFor();
   assert.equal(await focusOf(page,'economy'),'둔화');assert.equal(await focusOf(page,'market'),'상승 초기');assert.equal(await page.locator('[data-cycle-tab="economy"]').getAttribute('aria-selected'),'true');
   pass++;console.log('PASS cycle ring remount '+width);
   // user estimate: device-local, separate from the official layer, survives reload, clears
   phase='USER '+width;
   assert.equal(await page.evaluate(k=>localStorage.getItem(k),'investment.web.v1.macro-cycle-user-estimate'),null);
   await page.locator(R('economy')+' [data-cycle-user-from]').selectOption('확장|후반');await page.locator(R('economy')+' [data-cycle-user-to]').selectOption('둔화|초입');
   await page.locator(R('economy')+' [data-cycle-user-note]').fill('synthetic note');
   await page.locator(R('economy')+' [data-cycle-user-save]').click();
   {const v=JSON.parse(await page.evaluate(k=>localStorage.getItem(k),'investment.web.v1.macro-cycle-user-estimate'));
    assert.equal(v.schema,'macro-cycle-user-estimate/1');assert.deepEqual(Object.keys(v.rings),['economy']);assert.deepEqual(v.rings.economy.from,{phase:'확장',part:'후반'});}
   assert.equal(await page.locator(R('economy')+' [data-cycle-user-arc]').count(),1);assert.equal(await page.locator('[data-cycle-interval]').count(),0,'user arc is not the official interval');
   assert.equal(await page.locator(R('economy')+' [data-cycle-user-arc]').getAttribute('data-cycle-user-from'),'확장 후반');
   assert.equal(await page.locator(R('economy')).getAttribute('data-cycle-state'),'NOT_COMPUTED');assert.ok((await page.locator(R('economy')+' [data-cycle-official]').textContent()).includes('미산출'));
   assert.ok((await page.locator(R('economy')+' [data-cycle-user] legend').textContent()).includes('사용자 추정 · 공식 판정 아님'));
   assert.equal(await page.locator(R('market')+' [data-cycle-user-arc]').count(),0);
   await page.reload();await page.locator('[data-cycle-root]').waitFor();
   assert.equal(await page.locator(R('economy')+' [data-cycle-user-arc]').count(),1,'kept on this device');assert.ok((await page.locator(R('economy')+' [data-cycle-user-current]').textContent()).includes('확장 후반~둔화 초입'));
   await page.locator(R('economy')+' [data-cycle-user-clear]').click();
   assert.equal(await page.evaluate(k=>localStorage.getItem(k),'investment.web.v1.macro-cycle-user-estimate'),null);assert.equal(await page.locator('[data-cycle-user-arc]').count(),0);
   pass++;console.log('PASS cycle ring user estimate '+width);
   // 10, 9 synthetic estimated interval (fresh page: nothing turned yet), incl. last→first wrap on the market ring
   phase='ESTIMATED '+width;
   await page.reload();await page.locator('[data-cycle-root]').waitFor();
   await page.evaluate(o=>MacroCycleRing.setPublication({outputs:o}),[out('economy',P('확장','후반'),P('둔화','초입')),out('market',P('하락','후반'),P('바닥','초입'))]);
   {const iv=page.locator(R('economy')+' [data-cycle-interval]');assert.equal(await iv.count(),1);
    assert.equal(await iv.getAttribute('data-cycle-from'),'확장 후반');assert.equal(await iv.getAttribute('data-cycle-to'),'둔화 초입');assert.equal(await iv.getAttribute('data-cycle-span-deg'),'90.0');
    assert.equal(await page.locator(R('economy')).getAttribute('data-cycle-state'),'ESTIMATED');
    assert.ok((await page.locator(R('economy')+' [data-cycle-interval-text]').textContent()).includes('추정 구간: 확장 후반~둔화 초입'));
    assert.ok((await page.locator(R('economy')+' [data-cycle-interval-text]').textContent()).includes('탐색 층 · v0 · 미검증'));
    assert.ok((await page.locator(R('economy')+' [data-cycle-official]').textContent()).includes('미산출'),'exploratory output is not official');
    assert.equal(await focusOf(page,'economy'),'확장','focus follows the interval until turned');
    assert.ok((await page.locator(R('economy')+' [data-cycle-phase="둔화"]').getAttribute('aria-label')).includes('추정 구간에 포함'));
    for(const kind of ['for','against']){const lines=page.locator(R('economy')+' [data-cycle-evidence="'+kind+'"] [data-cycle-evidence-line]');assert.ok(await lines.count()>0,kind);
     for(const t of await lines.allTextContents())for(const k of ['관측 기간','발표','수집','출처'])assert.ok(t.includes(k),kind+' '+k);}
    assert.ok((await page.locator(R('economy')+' [data-cycle-evidence="for"]').textContent()).includes('수집 시각 기준(상한)'));
    assert.equal(await page.locator(R('economy')+' [data-cycle-transition="NOT_COMPUTED"]').count(),1);}
   {await page.locator('[data-cycle-tab="market"]').click();const iv=page.locator(R('market')+' [data-cycle-interval]');assert.equal(await iv.count(),1);
    assert.equal(await iv.getAttribute('data-cycle-from'),'하락 후반');assert.equal(await iv.getAttribute('data-cycle-to'),'바닥 초입');assert.equal(await iv.getAttribute('data-cycle-span-deg'),'90.0');
    assert.equal(await focusOf(page,'market'),'하락');
    await settle(page,'market');
    // one continuous band reaching both sides of the 하락|바닥 boundary (the boundary before cell 0)
    const crosses=await iv.evaluate(p=>{if((p.getAttribute('d').match(/M/g)||[]).length!==1)return false;const t=p.ownerSVGElement.querySelector('[data-cycle-boundary="0"]'),ang=(x,y)=>Math.atan2(x-160,160-y)*180/Math.PI;
     const b=ang(Number(t.getAttribute('x2')),Number(t.getAttribute('y2'))),L=p.getTotalLength();let before=false,after=false;
     for(let i=0;i<=400;i++){const q=p.getPointAtLength(L*i/400);let d=((ang(q.x,q.y)-b+540)%360)-180;if(d<-5)before=true;if(d>5)after=true;}return before&&after;});
    assert.ok(crosses,'wrap interval drawn across the first/last boundary without a gap');
    await page.locator('#macro-cycle-ring').screenshot({path:SHOTS+'/macro-cycle-ring-synthetic-'+width+'.png'}).catch(()=>{});
    await page.locator('[data-cycle-tab="economy"]').click();}
   assert.ok(!/%/.test(await root.textContent()));
   pass++;console.log('PASS cycle ring estimated (synthetic) '+width);
   // 11 new publication: follows while untouched, kept once turned, back to interval, withdrawn = 미산출, failure keeps the old arc
   phase='NEW PUBLICATION '+width;
   await page.evaluate(o=>MacroCycleRing.setPublication({outputs:o}),[out('economy',P('둔화','초입'),P('둔화','후반'),{as_of:'2026-10-16T00:00:00Z'})]);
   assert.equal(await focusOf(page,'economy'),'둔화');assert.equal(await page.locator(R('economy')+' [data-cycle-interval]').getAttribute('data-cycle-span-deg'),'90.0');
   assert.ok((await page.locator(R('economy')+' [data-cycle-changed]').textContent()).includes('추정 구간 바뀜: 확장 후반~둔화 초입 → 둔화 초입~둔화 후반 · 기준 2026-10-15T00:00:00Z → 2026-10-16T00:00:00Z'));
   await page.locator(R('economy')+' [data-cycle-prev]').click();assert.equal(await focusOf(page,'economy'),'확장');
   await page.evaluate(o=>MacroCycleRing.setPublication({outputs:o}),[out('economy',P('수축','초입'),P('수축','후반'),{as_of:'2026-10-17T00:00:00Z'})]);
   assert.equal(await focusOf(page,'economy'),'확장','turned focus is kept');assert.equal(await page.locator(R('economy')+' [data-cycle-interval]').getAttribute('data-cycle-from'),'수축 초입');
   await page.locator(R('economy')+' [data-cycle-goto-interval]').click();assert.equal(await focusOf(page,'economy'),'수축');assert.equal(await page.locator(R('economy')+' [data-cycle-changed]').count(),0);
   await page.evaluate(()=>MacroCycleRing.refreshFailed());
   assert.equal(await page.locator(R('economy')+' [data-cycle-interval]').count(),1,'failed refresh keeps the old arc');assert.ok((await page.locator(R('economy')+' [data-cycle-refresh-failed]').textContent()).includes('갱신 실패'));
   await page.evaluate(()=>MacroCycleRing.setPublication({outputs:[]}));
   assert.equal(await page.locator('[data-cycle-interval]').count(),0);assert.equal(await page.locator(R('economy')).getAttribute('data-cycle-state'),'NOT_COMPUTED');
   assert.ok((await page.locator(R('economy')+' [data-cycle-reason]').textContent()).includes('위치 판정 모델 없음'));assert.equal(await page.locator('[data-cycle-refresh-failed]').count(),0);
   pass++;console.log('PASS cycle ring new publication '+width);
   // 8 abstain; 9 a point coordinate is never used; 12 transition text only when validated with period and sample
   phase='ABSTAIN '+width;
   await page.evaluate(o=>MacroCycleRing.setPublication({outputs:o}),[{...out('economy',P('확장','후반'),P('둔화','초입')),status:'ABSTAIN',interval:null,abstain_reasons:['NO_APPROVED_STATE_RULE','CONFLICTING_FAMILIES']},
    out('market',P('바닥','초입'),P('바닥','후반'),{point:{deg:12}})]);
   assert.equal(await page.locator('[data-cycle-interval]').count(),0);assert.equal(await page.locator(R('economy')).getAttribute('data-cycle-state'),'ABSTAINED');
   assert.ok((await page.locator(R('economy')+' [data-cycle-interval-text]').textContent()).includes('판정 유보'));assert.ok((await page.locator(R('economy')+' [data-cycle-reason]').textContent()).includes('NO_APPROVED_STATE_RULE'));
   assert.ok(await page.locator(R('economy')+' [data-cycle-evidence="for"] [data-cycle-evidence-line]').count()>0);assert.ok(await page.locator(R('economy')+' [data-cycle-evidence="against"] [data-cycle-evidence-line]').count()>0);
   assert.equal(await page.locator(R('market')).getAttribute('data-cycle-state'),'NOT_COMPUTED');assert.ok((await page.locator(R('market')+' [data-cycle-reason]').textContent()).includes('점 좌표'));
   const tf={to:'수축',k:3,n:9,period_from:'1960-01',period_to:'2025-12',rule_id:'synthetic-rule/0'};
   await page.evaluate(o=>MacroCycleRing.setPublication({outputs:o}),[out('economy',P('둔화','초입'),P('둔화','후반'),{transition_frequency:{...tf,validated:false}})]);
   assert.equal(await page.locator(R('economy')+' [data-cycle-transition="NOT_COMPUTED"]').count(),1,'unvalidated stays 미산출');
   await page.evaluate(o=>MacroCycleRing.setPublication({outputs:o}),[out('economy',P('둔화','초입'),P('둔화','후반'),{transition_frequency:{...tf,validated:true,period_to:undefined}})]);
   assert.equal(await page.locator(R('economy')+' [data-cycle-transition="NOT_COMPUTED"]').count(),1,'missing period stays 미산출');
   await page.evaluate(o=>MacroCycleRing.setPublication({outputs:o}),[out('economy',P('둔화','초입'),P('둔화','후반'),{transition_frequency:{...tf,validated:true}})]);
   assert.ok((await page.locator(R('economy')+' [data-cycle-transition="VALIDATED"]').textContent()).includes('3/9 · 기간 1960-01~2025-12 · 표본 9회 · 규칙 synthetic-rule/0'));
   await page.evaluate(()=>MacroCycleRing.setPublication({outputs:[]}));
   pass++;console.log('PASS cycle ring abstain/point/transition '+width);
   // industry ring: groups from the published sec-qgv2.json rows, own key, group missing from a new publication
   phase='INDUSTRY '+width;
   await page.evaluate(()=>MacroCycleRing.mount(document.querySelector('#macro-cycle-ring-root'),{bundle:{'sec-qgv2.json':{records:{a:{industry_group:'utilities'},b:{industry_group:'transportation'},c:{industry_group:null}}}}}));
   await page.locator('[data-cycle-tab="industry"]').click();
   assert.deepEqual(await page.locator(R('industry')+' [data-cycle-group] option').evaluateAll(n=>n.map(x=>x.value)),['','transportation','utilities']);
   await page.locator(R('industry')+' [data-cycle-group]').selectOption('utilities');assert.equal(await page.locator(R('industry')).getAttribute('data-cycle-key'),'industry:utilities');
   await page.evaluate(o=>MacroCycleRing.setPublication({outputs:o}),[out('industry:utilities',P('둔화',null),P('둔화',null))]);
   assert.equal(await page.locator(R('industry')+' [data-cycle-interval]').getAttribute('data-cycle-span-deg'),'90.0');assert.equal(await focusOf(page,'industry'),'둔화');
   assert.equal(await page.locator(R('economy')+' [data-cycle-interval]').count(),0,'industry interval stays on its own ring');
   await page.evaluate(()=>MacroCycleRing.mount(document.querySelector('#macro-cycle-ring-root'),{bundle:{'sec-qgv2.json':{records:{b:{industry_group:'transportation'}}}}}));
   assert.equal(await page.locator(R('industry')+' [data-cycle-group]').inputValue(),'');assert.ok((await page.locator(R('industry')+' [data-cycle-group-missing]').textContent()).includes('고른 업종 그룹이 새 게시본에 없음'));
   assert.equal(await page.locator('[data-cycle-interval]').count(),0);
   await page.evaluate(()=>MacroCycleRing.setPublication({outputs:[]}));
   pass++;console.log('PASS cycle ring industry '+width);
   // evidence hook for the observation-graph lane
   phase='HOOK '+width;
   await page.locator('[data-cycle-tab="economy"]').click();
   await page.evaluate(()=>MacroCycleRing.attachEvidence(({phase,codes})=>'hook '+phase+' '+codes.join(',')));
   assert.ok((await page.locator(R('economy')+' [data-cycle-evidence-slot]').first().textContent()).startsWith('hook '));
   await page.evaluate(()=>MacroCycleRing.attachEvidence(null));
   pass++;console.log('PASS cycle ring evidence hook '+width);
   // 13 reduced motion: no transition time
   phase='REDUCED '+width;
   await page.emulateMedia({reducedMotion:'reduce'});
   assert.equal(await page.evaluate(()=>{const r=document.querySelector('[data-cycle-ring="economy"]');r.querySelector('[data-cycle-next]').click();const s=r.querySelector('svg');return s.dataset.cycleDisplayDeg===Number(s.dataset.cycleTurnDeg).toFixed(3);}),true,'instant with reduced motion');
   await page.emulateMedia({reducedMotion:'no-preference'});
   assert.equal(await page.evaluate(()=>{const r=document.querySelector('[data-cycle-ring="economy"]');r.querySelector('[data-cycle-next]').click();const s=r.querySelector('svg');return s.dataset.cycleDisplayDeg===Number(s.dataset.cycleTurnDeg).toFixed(3);}),false,'animated otherwise');
   await settle(page,'economy');
   pass++;console.log('PASS cycle ring reduced motion '+width);
   phase='SAFETY '+width;
   await noOverflow(page,'end '+width);
   assert.deepEqual(seen.writes,[],'no non-GET request');assert.deepEqual(seen.outside,[],'no outside request');assert.deepEqual(seen.errors,[],'no page error');
   assert.deepEqual(await page.evaluate(()=>Object.keys(sessionStorage)),[],'no session storage');
   pass++;console.log('PASS cycle ring safety '+width);
   await ctx.close();
  }
  console.log('PASS macro cycle ring ('+pass+')');
 }catch(error){console.log('FAIL macro cycle ring '+phase+' '+(error&&error.message?error.message.split('\n')[0]:''));process.exitCode=1;}
 finally{await browser.close();}
})();
