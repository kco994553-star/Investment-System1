'use strict';
// PC layout (>= 1024px) at 390 / 768 / 1024 / 1440: S12 home dashboard, S17 report grid, S03/S06/S16/S10 tables
// (all columns without horizontal scroll, sticky header, keyboard-accessible stable sorting with NOT_AVAILABLE last) and
// the unchanged phone layout below 1024px. Two data sets: the empty public screens and a synthetic LIVE set served by
// route interception (synthetic Q/G scores, synthetic 13F names, synthetic forward ledger, synthetic report model with
// amounts hidden). No prices, no personal data. Optional PC_LAYOUT_SCREENSHOT_DIR saves viewport PNGs of the LIVE set.
const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {routeEmptyPublicScreens}=require('./empty_public_screens.js');
const BASE=process.env.PAGES_COCKPIT_URL,SHOTS=process.env.PC_LAYOUT_SCREENSHOT_DIR||'';
const WIDTHS=[390,768,1024,1440];
const ROUTES=[['S12','home','[data-home-dashboard]'],['S17','report/mock','[data-report-badges]'],['S03','companies','#company-list li'],['S03P','portfolio','#portfolio-screen [data-portfolio-badges]'],
 ['S06','leaderboard','[data-leaderboard-table]'],['S16','thirteenf','[data-public-screen="thirteenf"]'],['S10','validation','[data-validation-section]'],
 ['S02','qgv','[data-nav-tab][aria-current="page"]'],['S08','technical','[data-nav-tab][aria-current="page"]'],['S09','macro','[data-nav-tab][aria-current="page"]'],['S07','news','#news-pane'],
 ['S04','company/nvda','[data-nav-tab][aria-current="page"]'],['S15','watchlist','#watchlist-company-list'],['S17R','report/real','[data-report-badges]'],['S11','settings','#device-backup-export']];
const SHOT_ROUTES={S12:null,S17:'[data-report-summary]',S03:null,S06:'[data-leaderboard-table]',S16:'[data-13f-config-manager]',S10:'[data-forward-days]'};
const IDS=['asml','lrcx','klac','tokyo_electron','hanmi','nvda','amd','avgo','qcom','intc','msft','googl','amzn','rtx','stry','etn','hubb','gev','rok'];
const FACTORS=['competitive_advantage','eps_fcf_per_share_growth','excess_growth_vs_industry','fcf_quality','financial_health','growth_durability','growth_efficiency','management_quality','margin_quality','market_position','next_3_5y_growth','revenue_growth','roic_wacc'];
const H=c=>c.repeat(64);
function qg(){const at=new Date().toISOString(),companies={};IDS.forEach((id,i)=>{const live=i%3!==0;companies[id]=live?{state:'LIVE',source_hashes:{companyfacts:H('a'),submissions:H('b')},factors:Object.fromEntries(FACTORS.map((f,k)=>[f,{score:30+((i*7+k*3)%60),state:'LIVE'}]))}:{state:'NOT_AVAILABLE',source_hashes:{},factors:Object.fromEntries(FACTORS.map(f=>[f,{score:null,state:'NOT_AVAILABLE'}]))};});
 return {schema_version:1,kind:'SEC_QG_FACTORS',as_of:at,state:'LIVE',sources:[{agency:'SEC_COMPANYFACTS',sha256:H('a'),acquired_at:at},{agency:'SEC_SUBMISSIONS',sha256:H('b'),acquired_at:at}],reason_codes:[],freshness_basis:'SOURCE_ACQUISITION',stale_after_seconds:86400,data:{companies,method_status:'PROVISIONAL_UNCALIBRATED',availability_basis:'OBSERVED_CAPTURE_ONLY'}};}
function thirteenF(){const at=new Date().toISOString(),change=(cusip,a,b,kind)=>({cusip,security_key:H('c'),unit:'SH',kind,reported_before:a,reported_after:b,reported_delta:b-a});
 const report=(cik,changes)=>({manager_cik:cik,previous_quarter:'2026-03-31',current_quarter:'2026-06-30',state:'LIVE',source_hashes:{previous:H('a'),current:H('b')},changes});
 const verified=(id,cik,name)=>({id,cik,state:'VERIFIED',reason_code:null,matched_name:name,verified_at:at,latest_13f_accession:'0000000000-26-000001',capture_reason:null,comparison_reasons:[]});
 return {schema_version:1,kind:'SEC_13F',as_of:at,state:'LIVE',sources:[{agency:'SEC_13F',sha256:H('a'),acquired_at:at},{agency:'SEC_13F',sha256:H('b'),acquired_at:at}],reason_codes:[],freshness_basis:'SOURCE_ACQUISITION',stale_after_seconds:86400*120,
  data:{role:'REPORTED_QUANTITY_CHANGE_NOT_TRADES',reports:[report('0001067983',[change('A00000000',0,5,'NEW'),change('B00000000',4,0,'EXIT')]),report('0001135730',[change('A00000000',2,3,'ADD')])],
   managers:[verified('berkshire_hathaway','0001067983','SYNTHETIC NAME ONE'),verified('coatue_management','0001135730','SYNTHETIC NAME TWO')]}};}
const V='forward_validation/v1',VV='forward_validation/v1+dcf_v1_default';
const UNITS={asml:900,lrcx:600,klac:550,tokyo_electron:500,hanmi:450,nvda:800,amd:500,avgo:500,qcom:400,intc:300,msft:700,googl:700,amzn:600,rtx:600,stry:550,etn:500,hubb:350,gev:300,rok:200};
const target=()=>({portfolio_id:'TARGET',version:'v0',root_sha256:H('b'),total_units:10000,weights_units:{...UNITS}});
function recorded(date,shift){const companies={};IDS.forEach((id,i)=>{const live=i%4!==0;companies[id]=live?{state:'LIVE',Q:{score:40+((i+shift)%9),coverage:'PARTIAL',missing_factor_count:5},G:{score:60-((i+shift)%7),coverage:'PARTIAL',missing_factor_count:4}}:{state:'NOT_AVAILABLE',Q:{score:null,coverage:'BLOCKED',missing_factor_count:7},G:{score:null,coverage:'BLOCKED',missing_factor_count:6}};});
 return{date,version:V,strategy:'QGV_STANDARD_V1',calibration:'UNCALIBRATED',state:'RECORDED',reason_codes:[],target:target(),qg_as_of:date+'T22:10:00+00:00',qg_screen_state:'LIVE',companies,source_sha256:{'sec-qg-factors.json':H('b'),'actual-catalog.json':H('b')},created_at:date+'T22:30:00+00:00'};}
function missingDay(date){return{date,version:V,strategy:'QGV_STANDARD_V1',calibration:'UNCALIBRATED',state:'NOT_AVAILABLE',reason_codes:['SEC_QG_FACTORS_MISSING'],target:target(),qg_as_of:null,qg_screen_state:null,companies:null,source_sha256:{'sec-qg-factors.json':null,'actual-catalog.json':H('b')},created_at:date+'T22:30:00+00:00'};}
function ledger(){return{schema_version:1,kind:'FORWARD_VALIDATION_LEDGER',start_date:'2026-10-19',status:'ACTIVE',as_of:'2026-10-22T22:31:00+00:00',strategy:'QGV_STANDARD_V1',calibration:'UNCALIBRATED',holdout:'UNCONFIRMED_NOT_USED',price_free:true,target:{portfolio_id:'TARGET',version:'v0'},
 versions:{[V]:[recorded('2026-10-19',3),missingDay('2026-10-20'),recorded('2026-10-21',0),recorded('2026-10-22',5)],[VV]:[]},version_status:{[V]:{state:'ACTIVE',v_included:false,reason_codes:[]},[VV]:{state:'NOT_AVAILABLE',v_included:true,reason_codes:['V_REQUIRES_DEVICE_PRICES']}}};}
// Synthetic S17 model: amounts stay hidden ([숨김]/●●●); company names are placeholders.
async function injectReport(page){return page.evaluate(()=>{try{if(typeof window.disposeReport==='function')window.disposeReport();const R=window.DailyReport,levels=Object.keys(R.LEVEL_KO);
 const holdings=Array.from({length:12},(_,i)=>({company:'syn'+i,name:'SYNTHETIC CO '+String.fromCharCode(65+i),actual_weight:i%5===0?null:2+i*0.7,target_weight:3+(i%4),main:levels[i%levels.length],aux:i%3?[levels[(i+2)%levels.length]]:[],reasons:[],q:i%4===0?null:40+i,g:i%4===0?null:50+i}));
 const m={kind:'MOCK',tab:'SET_A',report_date:'2026-10-22',base_dates:{US:'2026-10-21'},started:true,ledger_state:'OK',ledger_reasons:[],start_date:'2026-10-19',invest_start:null,buy_limit:1000000,sell_limit:1000000,
  summary:{total_value:10000000,simple_return:0.0123,cash:1000,realized_pnl:0,unrealized_pnl:0},last:null,days:[],holdings,
  executed:[{side:'BUY',company:'syn1',amount:300000,quantity:1.5,reason_codes:['SYNTHETIC_RULE']},{side:'SELL',company:'syn2',amount:200000,quantity:2,reason_codes:['SYNTHETIC_RULE']}],orders:[],cancelled:[],runner:null,hits:[],buy_total:300000,sell_total:200000,ram_state:'NOT_AVAILABLE'};
 document.querySelector('#daily-report').innerHTML=R.screenHtml(m,{hidden:true,locale:'ko-KR'});return 'OK';}catch(e){return 'SKIP '+String(e&&e.message||e);}});}
const overflow=page=>page.evaluate(()=>({sw:document.documentElement.scrollWidth,cw:document.documentElement.clientWidth}));
async function tableFacts(page){return page.evaluate(()=>[...document.querySelectorAll('main table')].filter(t=>t.offsetParent!==null).map(t=>{const wrap=t.closest('.table-wrap,.table-scroll')||t.parentElement,th=t.querySelector('thead th');
 return{wrapOverflow:wrap.scrollWidth-wrap.clientWidth,tableRight:t.getBoundingClientRect().right,mainRight:document.querySelector('main').getBoundingClientRect().right,sticky:th?getComputedStyle(th).position:null,buttons:t.querySelectorAll('.th-sort').length,cols:t.querySelectorAll('thead th').length,hidden:[...t.querySelectorAll('thead th')].filter(h=>h.getBoundingClientRect().width<1).length};}));}
const col=(page,sel,i)=>page.locator(sel+' tbody tr').evaluateAll((rows,i)=>rows.map(r=>r.cells[i].textContent.trim()),i);
(async()=>{const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_EXECUTABLE_PATH});let phase='START',pass=0,fail=0;const matrix=[];
 if(SHOTS)fs.mkdirSync(SHOTS,{recursive:true});
 try{for(const dataset of ['EMPTY','LIVE'])for(const width of WIDTHS){const pc=width>=1024,context=await browser.newContext({viewport:{width,height:900},serviceWorkers:'block'});
  await routeEmptyPublicScreens(context);
  if(dataset==='LIVE'){await context.route('**/sec-qg-factors.json*',r=>r.fulfill({status:200,contentType:'application/json',body:JSON.stringify(qg())}));
   await context.route('**/sec-13f-changes.json*',r=>r.fulfill({status:200,contentType:'application/json',body:JSON.stringify(thirteenF())}));
   await context.route('**/forward-validation-ledger.json*',r=>r.fulfill({status:200,contentType:'application/json',body:JSON.stringify(ledger())}));}
  await context.route('**/*',r=>new URL(r.request().url()).origin===new URL(BASE).origin?r.fallback():r.abort());
  const page=await context.newPage();let errors=[];const expected404=[];
  page.on('pageerror',e=>errors.push('pageerror '+String(e)));
  page.on('console',m=>{if(m.type()!=='error')return;const url=(m.location()&&m.location().url)||'';if(/Failed to load resource/.test(m.text())&&/\/(sec-public-inputs|sec-valuation-inputs|sec-universe-shares|company-classification|forward-validation-ledger)\.json/.test(url)){expected404.push(url);return;}errors.push(m.text()+' '+url);});
  try{for(const [screen,route,selector] of ROUTES){phase=dataset+'_'+width+'_'+screen;const before=errors.length;
    await page.goto(BASE+'#'+route);await page.locator(selector).first().waitFor();await page.waitForTimeout(250);
    if(screen==='S17'&&dataset==='LIVE'){const r=await injectReport(page);if(r!=='OK')console.log('NOTE S17 synthetic report '+r);else await page.locator('[data-report-section="3"] table').waitFor();await page.waitForTimeout(100);}
    const o=await overflow(page);matrix.push({dataset,width,screen,route,overflow:o.sw-o.cw,console:errors.length-before});
    assert.ok(o.sw<=o.cw,'horizontal overflow '+o.sw+'>'+o.cw);
    const tables=await tableFacts(page);
    for(const t of tables){assert.equal(t.hidden,0,'hidden column');
     if(pc){assert.ok(t.wrapOverflow<=1,'table scrolls horizontally '+t.wrapOverflow);assert.ok(t.tableRight<=t.mainRight+1,'table wider than main');assert.equal(t.sticky,'sticky');}
     else{assert.equal(t.buttons,0,'sort buttons on phone');assert.notEqual(t.sticky,'sticky');}}
    if(screen==='S12'){const f=await page.evaluate(()=>{const d=document.querySelector('[data-home-dashboard]'),s=getComputedStyle(d),a=d.querySelector('[data-integrated-judgement]').getBoundingClientRect(),b=d.querySelector('.hero').getBoundingClientRect();return{display:s.display,cols:s.gridTemplateColumns.split(' ').length,sameRow:Math.abs(a.top-b.top)<2&&b.left>a.left};});
     if(pc){assert.equal(f.display,'grid');assert.equal(f.cols,width>=1360?3:2);assert.ok(f.sameRow,'judgement and portfolio side by side');}else assert.equal(f.display,'block');}
    if(screen==='S17'&&await page.locator('[data-report-section="3"] table').count()){const f=await page.evaluate(()=>{const s=document.querySelector('[data-report-summary]'),cells=[s.querySelector('.big'),s.querySelector('.big + p'),...s.querySelectorAll('.grid.two > *')].map(n=>n.getBoundingClientRect());
      const ten=document.querySelector('[data-report-section="10"]').getBoundingClientRect(),rest=document.querySelector('[data-report-section="rest"]').getBoundingClientRect(),led=document.querySelector('[data-report-section="3"]').getBoundingClientRect(),host=document.querySelector('#daily-report').getBoundingClientRect();
      return{cells:cells.length,oneRow:cells.every(c=>Math.abs(c.top-cells[0].top)<2)&&cells.every((c,i)=>!i||c.left>cells[i-1].left),twoCol:Math.abs(ten.top-rest.top)<2&&rest.left>ten.left,ledgerFull:led.width>=host.width-2,ths:document.querySelectorAll('[data-report-section="3"] thead th').length};});
     assert.equal(f.cells,4);assert.equal(f.ths,4);
     if(pc){assert.ok(f.oneRow,'summary numbers in one row');assert.ok(f.twoCol,'sections in two columns');assert.ok(f.ledgerFull,'ledger full width');}else{assert.ok(!f.oneRow,'phone summary unchanged');assert.ok(!f.twoCol,'phone sections stacked');}}
    if(screen==='S16'&&pc&&width>=1440){const cols=await page.evaluate(()=>getComputedStyle(document.querySelector('[data-public-screen="thirteenf"]')).gridTemplateColumns.split(' ').length);assert.ok(cols>=2,'13F cards in columns');}
    if(screen==='S03'&&pc){const cols=await page.evaluate(()=>getComputedStyle(document.querySelector('#company-list')).gridTemplateColumns.split(' ').length);assert.ok(cols>=2,'company list in columns');}
    if(screen==='S06'&&dataset==='LIVE'&&pc){const T='[data-leaderboard-table]',original=await col(page,T,1);
     await page.locator(T+' thead th').nth(1).locator('.th-sort').click();assert.equal(await page.locator(T+' thead th').nth(1).getAttribute('aria-sort'),'ascending');
     const asc=await col(page,T,1);assert.deepEqual(asc,[...original].sort(new Intl.Collator(undefined,{numeric:true,sensitivity:'base'}).compare));
     await page.locator(T+' thead th').nth(1).locator('.th-sort').focus();await page.keyboard.press('Enter');assert.equal(await page.locator(T+' thead th').nth(1).getAttribute('aria-sort'),'descending');assert.deepEqual(await col(page,T,1),[...asc].reverse());
     await page.keyboard.press('Space');assert.equal(await page.locator(T+' thead th').nth(1).getAttribute('aria-sort'),'none');assert.deepEqual(await col(page,T,1),original);
     // Sticky header: scroll past the table top and the header row stays at the viewport top.
     const top=await page.evaluate(T=>{const t=document.querySelector(T);scrollTo(0,t.getBoundingClientRect().top+scrollY+120);return t.querySelector('thead th').getBoundingClientRect().top;},T);assert.ok(Math.abs(top)<=1,'sticky header top '+top);await page.evaluate(()=>scrollTo(0,0));}
    if(screen==='S10'&&dataset==='LIVE'){const T='[data-forward-days]';await page.locator(T).waitFor();if(pc){const original=await col(page,T,3);
     await page.locator(T+' thead th').nth(3).locator('.th-sort').press('Enter');const asc=await col(page,T,3);assert.equal(asc[asc.length-1],'—','NOT_AVAILABLE last ascending');assert.deepEqual(asc.slice(0,-1).map(Number),asc.slice(0,-1).map(Number).sort((a,b)=>a-b));
     await page.locator(T+' thead th').nth(3).locator('.th-sort').press('Enter');const desc=await col(page,T,3);assert.equal(desc[desc.length-1],'—','NOT_AVAILABLE last descending');assert.deepEqual(desc.slice(0,-1).map(Number),desc.slice(0,-1).map(Number).sort((a,b)=>b-a));
     // Stable: equal keys keep their original relative order (date column ties never occur, so sort by state: all RECORDED rows tie).
     await page.locator(T+' thead th').nth(3).locator('.th-sort').press('Enter');assert.deepEqual(await col(page,T,3),original);
     const dates=await col(page,T,0);await page.locator(T+' thead th').nth(1).locator('.th-sort').click();const tie=(await page.locator(T+' tbody tr').evaluateAll(r=>r.map(x=>[x.cells[0].textContent,x.cells[1].textContent]))).filter(x=>x[1]==='LIVE').map(x=>x[0]);assert.deepEqual(tie,dates.filter(d=>tie.includes(d)),'stable ties');}
     else assert.equal(await page.locator('.th-sort').count(),0);}
    if(SHOTS&&dataset==='LIVE'&&Object.hasOwn(SHOT_ROUTES,screen)){const target=SHOT_ROUTES[screen];await page.evaluate(sel=>{if(document.activeElement)document.activeElement.blur();const n=sel&&document.querySelector(sel);scrollTo(0,n?Math.max(0,n.getBoundingClientRect().top+scrollY-(innerWidth>=1024?24:120)):0);},target);await page.waitForTimeout(60);
     await page.screenshot({path:path.join(SHOTS,screen+'_'+route.split('/')[0]+'_'+width+'.png')});}
    assert.equal(errors.length,before,'console errors '+errors.slice(before).join(' | '));}
   pass++;console.log('PASS pc layout '+dataset+' '+width+(expected404.length?' (expected 404 for absent optional sidecars: '+expected404.length+')':''));}
  catch(e){fail++;console.log('FAIL pc layout '+phase+' '+(e.code==='ERR_ASSERTION'?'ASSERTION ':'BROWSER ')+(e.message||''));}
  finally{await context.close();}}}
 finally{await browser.close();}
 console.log('MATRIX dataset width screen route overflow_px console_errors');for(const r of matrix)console.log('MATRIX '+[r.dataset,r.width,r.screen,r.route,r.overflow,r.console].join(' '));
 console.log('COUNTS pass='+pass+' fail='+fail);if(fail)process.exitCode=1;})();
