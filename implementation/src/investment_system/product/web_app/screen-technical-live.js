/* Feature 3 · 기술적 분석 (spec v1.0 3.1–3.4 · menu 2 · route #/technical[/<company>]; boards Technical · MTechnical), the part that
   runs after IS2.ready. screen-technical.js draws the first-paint skeleton (head, the company box, sections 2-1..2-4 with a loading
   line) and hands its refs to IS2.technicalLive.screen(route, refs) from this file (loader.js LOAD_ORDER, after the layer); nothing
   here touches the layer while the file loads.
   - Company: chosen only through the one company list (IS2.companies, DEV_SYSTEM_20261031 §3.1) with the shared search part
     (IS2.searchPart.attach on the skeleton's box). The list is read when it is needed: the first focus or typing in the box, or a
     company already chosen (route parameter, else IS2.selection from the home / company page). A fresh open with no company reads
     nothing. A pick sets IS2.selection (RAM). A listing-ended code says 상장 종료 <date> and asks for no price.
   - Prices (§3.2): no approved, validated chart series exists, and the IEX last-trade path is not chart OHLCV. So the public screen
     shows the structure (indicators, patterns, scenarios, the tree) and every indicator and pattern verdict stays 판정 보류 with its
     reason (NO_APPROVED_PRICE_SERIES); no number is made up. The private layer (KIS integrated daily bars: raw MODP=0 plus confirmed
     splits; MODP=0 is never treated as adjusted) is one IS2.parts.privatePanel each for 3.1 (tech-kis-chart) and 3.2
     (tech-kis-pattern): NOT_READY, nothing sent or stored, the public part never waits for them.
   - Device daily bars (table 1-3 "기기: 클릭 시 Worker 일봉(RAM)"): only behind the 일봉 불러오기 button, through the layer's one
     member IS2.prices.history(event, company) (the action gate's HISTORY click: Google sign-in, the approved Worker address, a
     TARGET symbol). The bars stay in RAM only (never stored, logged or sent): this screen drops its own copy on a company change
     or when leaving the route, and the layer keeps its page-life cache of each read (prices.js histories, readable through
     IS2.prices.held) until a sign-out or a reload. The chart draws the close line with TechnicalChart.geometry / paths (the old
     renderer's math) and optional SMA lines (a port of ResearchIndicators' sma, node-checked); every price shown as text sits
     inside [data-ram-price]. Device bars are chart only: verdicts stay on hold (PRICE_BASIS_CONTINUITY_UNCONFIRMED, raw closes
     without confirmed splits).
   - Notes (3.3) and scenarios (3.1.3): the user's own anchors and words, kept on this device only through IS2.store.chartNotes
     (ChartWorkbench's key, schema chart-user-objects/1 and validator; backup /5), written only inside the save / delete click; no
     account step. A click on the device chart fills the note form with that bar's date and the pointer's price (rounded to six
     significant digits, the old rule), never a supplier close: a click on or outside the plot band's edges (y 20 / 220, where
     the highest / lowest value drawn sits) fills nothing.
   - Degree (3.2.2): swing = daily rule values (D), long = weekly (W) of pattern-rules/1 (ported here, node-checked against
     pattern-config-defaults.js); the exploration sets come from ChartWorkbench.EXPLORE_GRID, the minimum bars from
     ChartWorkbench.minBars. The choice lives in this module's RAM only.
   - States: loading (skeleton), empty (no company, no note), error (layer failed: the structure still draws, the company box and
     notes say why), partial failure (company list part missing, unreadable stored notes kept, an old module missing: without
     ChartWorkbench the notes say CHART_MODULE_MISSING, never a storage failure). */
(function(){
'use strict';
const I=window.IS2,{h,href,parts:{mascot}}=I;
const HOLD=Object.freeze({code:'NO_APPROVED_PRICE_SERIES',text:'승인·검증된 차트용 가격 계열이 아직 없습니다'});
const IEX=Object.freeze({code:'IEX_LAST_TRADE_NOT_OHLCV',text:'지금의 IEX 마지막 체결가 경로는 차트용 연속·조정 OHLCV가 아닙니다'});
const CONT=Object.freeze({code:'PRICE_BASIS_CONTINUITY_UNCONFIRMED',text:'기기 일봉은 원주가이고 분할 연속성을 확인하지 못했습니다 · 차트만'});
const RANGES=Object.freeze(['1mo','3mo','6mo','1y','2y','5y']),RANGE_KO=Object.freeze({'1mo':'1개월','3mo':'3개월','6mo':'6개월','1y':'1년','2y':'2년','5y':'5년'});
// The old technical tree's indicator set (ia-screens.js technicalTree 3.1.2, chart-workbench.js INDICATOR_GROUPS): fixed periods.
const INDICATORS=Object.freeze([
 ['SMA','단순 이동평균','5 · 20 · 60 · 120 · 240','최근 N봉 종가의 평균 · 가격이 평균 위인지 아래인지, 평균끼리의 순서','추세 방향'],
 ['EMA','지수 이동평균','20','최근 봉에 더 큰 무게를 둔 평균','단기 추세'],
 ['BOLL','볼린저 밴드','20 · 2σ','20봉 평균 ± 표준편차 2배 · 변동 폭','과열 · 수축'],
 ['RSI','상대강도지수','14','14봉 상승폭과 하락폭의 비율 (0~100)','모멘텀 과열 · 침체'],
 ['MACD','MACD','12 · 26 · 9','EMA 12 − EMA 26과 그 9봉 신호선','모멘텀 전환'],
 ['ATR','평균 실제 범위','14 · RAW_CLOSE','하루 변동 폭의 14봉 평균 · 패턴 규칙의 길이 단위','변동성 크기']].map(Object.freeze));
// pattern-rules/1 research defaults (pattern-config-defaults.js, generated from technical/pattern_rules_v1.json; the node test
// keeps this copy equal to it, so the loader does not have to load that file on every page).
const PATTERN_RULES=Object.freeze({rule_version:'pattern-rules/1',status:'RESEARCH_DEFAULT',label_ko:'연구 기본값 · 투자 유용성 미검증',
 params:Object.freeze({PIVOT_K:{D:3,W:2},SWING_MIN_ATR:1,ZONE_LOOKBACK:{D:250,W:104},ZONE_TOL_ATR:0.5,ZONE_MIN_TOUCHES:2,BREAK_BUFFER_ATR:0.25,BOX_MIN_BARS:{D:15,W:6},
  BOX_MAX_BARS:{D:120,W:52},BOX_HEIGHT_ATR:{min:2,max:10},FAIL_WINDOW:{D:5,W:2},DB_TOL_ATR:0.75,DB_SEP_MIN:{D:10,W:4},DB_SEP_MAX:{D:120,W:52},DB_DEPTH_ATR:2,
  VOL_AVG_N:{D:20,W:10},VOL_MULT:1.5})});
// chart-workbench.js PATTERN_NAMES / STATE_NAMES (not exported): display words only.
const PATTERNS=Object.freeze([
 ['SUPPORT_RESISTANCE_ZONE','지지·저항 구간','피벗 고점·저점이 ATR 허용오차 안에서 여러 번 닿은 가격대'],
 ['BOX_BREAKOUT_UP','박스 상향 돌파','정해진 길이 동안 위아래 경계 안에서 움직인 뒤 종가가 돌파 여유만큼 위 경계를 넘음'],
 ['BOX_BREAKDOWN','박스 하향 이탈','같은 박스에서 종가가 돌파 여유만큼 아래 경계를 내려감'],
 ['DOUBLE_BOTTOM','이중 바닥','높이가 비슷한 저점 둘과 그 사이 반등 고점(목선) · 목선 위 종가로 확인'],
 ['DOUBLE_TOP','이중 천장','높이가 비슷한 고점 둘과 그 사이 되밀림 저점(목선) · 목선 아래 종가로 확인']].map(Object.freeze));
const STATES=Object.freeze([['FORMED','형성 완료 · 확인 대기'],['CONFIRMED','확인'],['FAILED','확인 후 실패'],['INVALIDATED','무효화'],['EXPIRED','만료'],['NOT_JUDGEABLE','판정 불가']]);
const MIN_BARS_KO=Object.freeze({ATR14:'ATR 14',PIVOT:'피벗',ZONE:'지지·저항 구간',BOX:'박스',DOUBLE:'이중 바닥·천장',VOLUME_NOTE:'거래량 참고'});
const NOTE_KINDS=Object.freeze({PEN:'펜',LINE:'추세선',HLINE:'수평선',RANGE:'구간 상자',MEMO:'메모'});
const DIRECTIONS=Object.freeze({UP:['상승','↑'],SIDEWAYS:['횡보','→'],DOWN:['하락','↓']});
const MINE='#7A4CC2',MUTED='#5c5c5c';
const SMA_N=Object.freeze([20,60,120]),SMA_DASH=Object.freeze({20:'6 4',60:'2 3',120:'10 4'});
// View state (no price, no company data): degree, chosen SMA lines, history range. Kept while the page lives.
const V={tf:'D',sma:{20:true,60:false,120:false},range:'1y'};

/* ---------------------------------------------------------------- pure helpers (node-checked) */
const finite=x=>typeof x==='number'&&Number.isFinite(x);
// chart-indicators.js mean / sma (scaled mean; a missing value restarts the window) over the COMPLETE closes it reads.
function mean(xs){const scale=Math.max(...xs.map(Math.abs));return scale===0?0:xs.reduce((a,x)=>a+x/scale,0)/xs.length*scale;}
function sma(xs,n){const out=[];let w=[];for(const x of xs){if(x===null)w=[];else{w.push(x);if(w.length>n)w.shift();}const v=w.length===n?mean(w):null;out.push(finite(v)?v:null);}return out;}
const closes=bars=>bars.map(b=>b.session_status==='COMPLETE'?b.close:null);
// TechnicalChart.geometry's y(v) = 220 − (v/scale − minimum)/spread·200, read backwards; the old pointer rounding (toPrecision(6)).
// Only strictly inside the plot band: on or outside its edges (the highest / lowest value drawn) there is no price (null).
function priceAt(g,y){if(!(y>20&&y<220))return null;const spread=g.maximum-g.minimum||1;return Number((((220-y)/200*spread+g.minimum)*g.scale).toPrecision(6));}
// The bar nearest to a viewBox x (TechnicalChart x(i) = 20 + i·600/(n−1)).
function indexAt(n,x){if(n<=1)return 0;return Math.min(n-1,Math.max(0,Math.round((x-20)/600*(n-1))));}
const isDate=v=>typeof v==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&Number.isFinite(Date.parse(v+'T00:00:00Z'))&&new Date(Date.parse(v+'T00:00:00Z')).toISOString().slice(0,10)===v;
const positive=v=>finite(v)&&v>0;
// A user note (chart-annotation/1) of one kind at one anchor; the store adds id, author, price_basis and the times.
function noteFor({kind,symbol,date,price,text}){
 if(!['HLINE','MEMO'].includes(kind)||!isDate(date)||!positive(price))return null;
 return{schema:'chart-annotation/1',kind,symbol,interval:'D',points:[{time:date,price}],text:String(text||'').slice(0,500)};}
// A user scenario (chart-scenario/1): 1–3 key levels, condition, invalidation (and its optional price).
function scenarioFor({symbol,direction,horizon,date,levels,condition,invalidation,invalidationPrice}){
 const lv=(levels||[]).filter(l=>l&&positive(l.price)).slice(0,3).map(l=>({label:String(l.label||'').slice(0,40),price:l.price}));
 if(!DIRECTIONS[direction]||!['long','swing'].includes(horizon)||!isDate(date)||!lv.length||(invalidationPrice!==null&&!positive(invalidationPrice)))return null;
 return{schema:'chart-scenario/1',symbol,interval:'D',text:'',anchor_time:date,horizon,direction,levels:lv,condition:String(condition||'').slice(0,500),
  invalidation:String(invalidation||'').slice(0,500),invalidation_price:invalidationPrice};}
// This symbol's objects of one schema, newest first: created_at, then the stored order (the store appends, so later is newer).
const ofSymbol=(items,symbol,schema)=>items.map((o,i)=>[o,i]).filter(([o])=>o.symbol===symbol&&o.schema===schema)
 .sort(([a,i],[b,j])=>a.created_at<b.created_at?1:a.created_at>b.created_at?-1:j-i).map(([o])=>o);
// Where each daily note of the chart's symbol sits on the chart (g = TechnicalChart.geometry, dates = the bars' session dates);
// a note whose anchor date is not a bar or whose price is outside the chart's range is left off the chart (it stays listed).
function marks(g,dates,items){
 const at=new Map(dates.map((d,i)=>[d,i])),lo=g.minimum*g.scale,hi=g.maximum*g.scale,inside=p=>p>=lo&&p<=hi,xy=p=>[g.x(at.get(p.time)),g.y(p.price)],f=v=>v.toFixed(2),out=[];
 for(const o of items){if(o.schema!=='chart-annotation/1'||o.interval!=='D')continue;
  if(o.kind==='HLINE'){const p=o.points[0].price;if(inside(p))out.push({id:o.id,kind:'HLINE',d:'M20,'+f(g.y(p))+' L620,'+f(g.y(p))});continue;}
  if(!o.points.every(p=>at.has(p.time)&&inside(p.price)))continue;
  const pts=o.points.map(xy);
  if(o.kind==='MEMO')out.push({id:o.id,kind:'MEMO',cx:f(pts[0][0]),cy:f(pts[0][1])});
  else if(o.kind==='RANGE'){const[x0,x1]=[Math.min(pts[0][0],pts[1][0]),Math.max(pts[0][0],pts[1][0])],[y0,y1]=[Math.min(pts[0][1],pts[1][1]),Math.max(pts[0][1],pts[1][1])];
   out.push({id:o.id,kind:'RANGE',x:f(x0),y:f(y0),w:f(Math.max(1,x1-x0)),h:f(Math.max(1,y1-y0))});}
  else out.push({id:o.id,kind:o.kind,d:pts.map((p,i)=>(i?'L':'M')+f(p[0])+','+f(p[1])).join(' ')});}
 return out;}
// The degree's rule values for the 3.2.2 table: [name, label, value, exploration choices] from ChartWorkbench.EXPLORE_GRID.
function paramRows(rules,grid,tf){
 const val=(name)=>{const[hd,sb]=name.split('.'),v=rules.params[hd];return sb?v[sb]:v&&typeof v==='object'?v[tf]:v;};
 const rows=grid.map(([name,choices,[ko]])=>[name,ko,val(name),Array.isArray(choices)?choices:choices[tf]]);
 const at=rows.findIndex(r=>r[0]==='BOX_MAX_BARS');
 rows.splice(at+1,0,['DB_SEP_MAX','이중 최대 간격 (봉) · 박스 최대 길이를 따름',val('DB_SEP_MAX'),null]);
 return rows;}

/* ---------------------------------------------------------------- shared bits */
const put=(box,...c)=>{box.replaceChildren();I.append(box,c);return box;};
const block=(id,...c)=>h('div',{class:'sk card',dataset:{block:id}},...c);
const sub=(title,fn,hand)=>h('div',{class:'lb-head'},h('h3',{class:'stamp sub'},title),fn?h('span',{class:'meta'},'기능 ',fn):null,hand?h('span',{class:'hand'},hand):null);
const failed=(code,text,more)=>h('div',{class:'sk state-card',dataset:{state:'error',na:code}},mascot('alarm'),h('p',{class:'err'},text),more?h('p',{class:'reason'},more):null);
const empty=(code,text)=>h('div',{class:'sk state-card',dataset:{state:'empty',na:code}},mascot('plain'),h('p',null,text));
const prep=(what,missing)=>{const t='준비 중 · '+what,n=typeof I.parts.notReady==='function'?I.parts.notReady(t,missing):h('p',{class:'pending',dataset:{notReady:''}},t,' · 없는 것: ',missing.join(' · '));n.dataset.prep='';return n;};
const hold=code=>h('span',{class:'dash nobr',dataset:{verdict:'HOLD',na:code}},'판정 보류');
// A code in text with a break point after each underscore (<wbr>, no style), so a long code never widens a phone screen.
const code=c=>String(c).split('_').map((x,i,a)=>i<a.length-1?[x+'_',h('wbr')]:x);
const errCode=e=>{const m=e&&typeof e.message==='string'?e.message.split(' ')[0]:'';return /^[A-Z][A-Z0-9_]{2,60}$/.test(m)?m:'FAILED';};
const today=()=>new Date().toISOString().slice(0,10);
const clock=t=>typeof t==='string'&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(t)?t.slice(0,10)+' '+t.slice(11,16)+' UTC':'시각 미확인';
const fmt=v=>finite(v)?v.toLocaleString('ko-KR',{maximumSignificantDigits:6}):'—';
const field=(label,input,id)=>h('label',{class:'who',for:id},h('span',null,label),input);
const num=v=>{const t=String(v||'').trim();if(!t)return null;const n=Number(t);return finite(n)?n:NaN;};
// The device history path's codes in words (prices.history, the gate, the Worker); never a code alone.
const HIST_WORDS=Object.freeze({LAYER_NOT_READY:'층이 아직 준비되지 않았습니다 · 잠시 뒤 다시 눌러 주세요',LOADER_FAILED:'층을 불러오지 못했습니다 · 새로고침해 주세요',
 CLICK_REQUIRED:'버튼을 직접 눌러 주세요',ACTION_ALREADY_STARTED:'이미 묻는 중입니다',OFF:'이 기기 일봉 경로가 꺼져 있습니다',
 HISTORY_UNAVAILABLE:'이 기업은 기기 일봉 경로에 없습니다 · 지원: TARGET 19개 기업',REQUEST_INVALID:'요청 형식이 맞지 않습니다',
 ORIGIN_UNAPPROVED:'Worker 주소 설정 필요 · 승인된 주소가 이 기기에 없습니다',AUTH_REQUIRED:'시트 연결 필요 · 구글 로그인 (1. QGV 화면의 구글 연결)',
 CANCELED:'취소됨 · 로그인이 바뀌었거나 화면을 떠났습니다',RATE_LIMITED:'요청이 많아 잠시 막혔습니다 · 나중에 다시 눌러 주세요',YAHOO_FORMAT_CHANGED:'받은 일봉의 형식이 맞지 않아 쓰지 않습니다'});
const histWords=c=>HIST_WORDS[c]||'일봉을 가져오지 못했습니다';
const NOTE_WORDS=Object.freeze({CHART_NOTE_INVALID:'형식이 맞지 않아 저장하지 않았습니다',CHART_NOTES_FULL:'이 기기의 사용자 작성 객체가 500개라 더 저장하지 않습니다',
 CHART_NOTES_STORAGE_INVALID:'저장된 노트를 읽지 못해 덮어쓰지 않습니다',CHART_NOTE_SAVE_FAILED:'이 브라우저 저장소가 가득 찼거나 막혀 저장하지 못했습니다 · 이미 저장된 것은 그대로',
 CHART_NOTE_NOT_FOUND:'이미 지워진 항목입니다',CLICK_REQUIRED:'버튼을 직접 눌러 주세요',ACTION_ALREADY_STARTED:'이미 저장 중입니다',LAYER_NOT_READY:'층이 아직 준비되지 않았습니다',
 LOADER_FAILED:'층을 불러오지 못했습니다 · 새로고침해 주세요'});
const noteWords=c=>NOTE_WORDS[c]||'저장하지 못했습니다';

/* ---------------------------------------------------------------- the screen */
function screen(route,{root,box,chosen,slots}){
 const signal=route.signal,layer=typeof I.loadState==='function'&&I.loadState()==='READY';
 const S={row:null,dev:{busy:false,code:null,data:null},repaints:new Set()};
 const onChange=fn=>{S.repaints.add(fn);return fn;};
 const changed=()=>{for(const fn of[...S.repaints]){try{fn();}catch(_){}}};
 // ---- notes store (read at every draw; the facade refuses before / after a failed layer)
 // A missing ChartWorkbench (the store's READER_MISSING) is its own state, not a storage failure (storeFail words each).
 function stored(){if(!layer)return{state:'LOADER_FAILED',items:[],unreadable:0};let r=null;
  try{r=I.store.chartNotes.read();}catch(err){return{state:errCode(err)==='READER_MISSING'?'MODULE_MISSING':'UNAVAILABLE',items:[],unreadable:0};}
  return r&&typeof r.state==='string'&&Array.isArray(r.items)?r:{state:'UNAVAILABLE',items:[],unreadable:0};}
 const unusable=st=>st.state==='INVALID'||st.state==='UNAVAILABLE'||st.state==='MODULE_MISSING';
 const tfWord=()=>V.tf==='W'?'장기 · 주봉 기준 (W)':'스윙 · 일봉 기준 (D)';

 /* ---------------- company box and chosen line */
 const chosenState=(state,...c)=>{chosen.dataset.techChosenState=state;put(chosen,...c);};
 function paintChosen(){const r=S.row;
  if(!layer){chosenState('LOADER_FAILED',failed('LOADER_FAILED','기업 목록을 불러오지 못했습니다','층을 불러오지 못했습니다 · 새로고침해 주세요 · 아래 구조와 설명은 그대로 봅니다'));return;}
  if(!r){chosenState('NONE',h('p',{class:'reason',role:'status'},'기업을 고르면 기기 일봉 버튼과 그 기업의 노트 · 시나리오가 열립니다 · 구조와 설명은 기업 없이도 봅니다'));return;}
  chosen.dataset.code=r.code;
  chosenState('CHOSEN',h('div',{class:'lb-head',role:'status'},h('h2',{class:'card-title',dataset:{techCompany:r.code}},r.ticker,r.name_en?' · '+r.name_en:''),
   h('span',{class:'meta'},r.code,' · ',I.companies.scope().label,r.name_ko?' · '+r.name_ko:'')),
   r.status==='WITHDRAWN'?h('p',{class:'reason',dataset:{listingEnded:r.withdrawn_on}},'상장 종료 ',r.withdrawn_on,' · 점수 없음 · 일봉을 묻지 않습니다'):null,
   h('a',{class:'more',href:href('company',r.id)},'→ 기업 화면'));}
 function choose(row){if(S.row===row)return;S.row=row;S.dev={busy:false,code:null,data:null};paintChosen();changed();}
 function attachBox(){
  if(!layer){box.input.disabled=true;return;}
  let done=false;
  const go=()=>{if(done||signal.aborted)return;done=true;
   I.searchPart.attach(route,box,{onPick:(ev,e)=>{const row=I.companies.get(e.code);if(!row)return;I.selection.set(row.id);box.input.value='';
    if(route.params.length)try{history.replaceState(history.state,'',href('technical',row.id));}catch(_){}
    choose(row);}});};
  if(box.later||box.input.value.trim()||document.activeElement===box.input){go();return;}
  box.anchor.addEventListener('focusin',go,{once:true,signal});box.input.addEventListener('input',go,{once:true,signal});}
 // A company chosen before this screen (route parameter, else the selection): read the list once, then find it.
 function resolve(){
  const sel=I.selection&&I.selection.get(),want=route.params[0]||(sel&&sel.id)||null;
  if(!layer||!want){paintChosen();return;}
  chosenState('LOADING',h('p',{class:'pending',role:'status',dataset:{state:'loading'}},'불러오는 중 · 고른 기업'));
  I.companies.ready().then(r=>{if(signal.aborted)return;const row=I.companies.get(want);
   if(row){choose(row);paintChosen();return;}
   if(r.state==='FAILED'){chosenState('FAILED',failed('COMPANY_LIST_FAILED','기업 목록을 읽지 못했습니다','다시 고르면 목록을 다시 읽습니다 · 아래 구조와 설명은 그대로 봅니다'));return;}
   if(r.missing.length){chosenState('PARTIAL',failed('COMPANY_LIST_PARTIAL','기업 목록 일부를 읽지 못해 고른 기업('+want+')을 찾지 못했습니다','읽지 못한 것: '+r.missing.join(' · ')+' · 다시 고르면 목록을 다시 읽습니다'));return;}
   chosenState('NOT_FOUND',empty('NOT_IN_SCOPE','고른 기업('+want+')이 Universe504 목록에 없습니다 · 기술적 분석은 Universe504 안에서만 고릅니다'));},()=>{});}

 /* ---------------- 2-1 · 3.1 지표 · 시나리오 */
 const verdictBand=h('p',{class:'pending',role:'status',dataset:{verdictHold:HOLD.code}});
 const paintVerdict=onChange(()=>{const d=S.dev.data;put(verdictBand,h('b',null,'지표 판정 보류'),' · ',HOLD.text,' (',code(HOLD.code),') · ',IEX.text,
  d?h('span',{dataset:{verdictDevice:CONT.code}},' · 이 기기 일봉: ',CONT.text,' (',code(CONT.code),')'):null);});

 // 3.1.1 차트 탐색: no public chart; the device chart behind the button; the private KIS panel next to it.
 const dev={status:h('p',{class:'reason',role:'status',dataset:{techLoadStatus:''}}),chart:h('div',{dataset:{techChart:''}}),facts:h('div',{dataset:{techChartFacts:''}}),
  lines:h('div',{class:'checks',role:'group','aria-label':'차트에 표시할 지표 선',dataset:{techSmaToggles:''}}),why:h('p',{class:'reason',dataset:{techLoadWhy:''}})};
 const rangeSel=h('select',{id:'tech-range','aria-label':'일봉 기간',dataset:{techRange:''},onchange:e=>{V.range=e.target.value;}},RANGES.map(r=>h('option',{value:r,selected:r===V.range},RANGE_KO[r])));
 const loadBtn=h('button',{type:'button',class:'btn mine',dataset:{techLoad:''},onclick:e=>load(e)},'일봉 불러오기 · 이 기기에서만');
 const supported=row=>!!(row&&window.PrivateHistory&&typeof window.PrivateHistory.symbolFor==='function'&&window.PrivateHistory.symbolFor(row.id));
 function load(e){if(S.dev.busy||!S.row)return;const row=S.row;let p;
  try{p=I.prices.history(e,row.id,{range:V.range});}catch(err){S.dev={busy:false,code:errCode(err),data:null};changed();return;}
  S.dev={busy:true,code:null,data:null};changed();
  Promise.resolve(p).then(data=>{if(signal.aborted||S.row!==row)return;S.dev={busy:false,code:null,data};changed();},
   err=>{if(signal.aborted||S.row!==row)return;S.dev={busy:false,code:errCode(err),data:null};changed();});}
 const paintDevice=onChange(()=>{const r=S.row,d=S.dev,ok=layer&&r&&r.status!=='WITHDRAWN'&&supported(r);
  loadBtn.disabled=!ok;rangeSel.disabled=!ok||d.busy;loadBtn.setAttribute('aria-busy',String(d.busy));
  dev.why.textContent=!layer?'층을 불러오지 못해 일봉을 물을 수 없습니다':!r?'기업을 고르면 누를 수 있습니다':r.status==='WITHDRAWN'?'상장 종료 기업은 일봉을 묻지 않습니다':!supported(r)?HIST_WORDS.HISTORY_UNAVAILABLE+' · 공개 화면은 그대로':'';
  dev.why.hidden=!dev.why.textContent;
  dev.status.replaceChildren(...(d.busy?['이 기기 일봉 경로로 묻는 중']:d.code?[h('span',{dataset:{na:d.code}},'— · ',histWords(d.code),' · ',code(d.code))]:d.data?['이 기기 일봉을 이 화면에만 보였습니다 · 저장·전송 안 함 · 새로고침하면 사라짐']:[]));
  if(!d.data){dev.chart.replaceChildren();dev.facts.replaceChildren();dev.lines.replaceChildren();dev.chart.dataset.state=d.code?'NA':'BEFORE';return;}
  dev.chart.dataset.state='OK';drawChart();});
 function drawChart(){const d=S.dev.data,TC=window.TechnicalChart,CW=window.ChartWorkbench;
  if(!TC||!CW){dev.chart.dataset.state='NA';put(dev.chart,failed('CHART_MODULE_MISSING','차트 모듈을 불러오지 못했습니다'));return;}
  const bars=d.bars,lines=SMA_N.filter(n=>V.sma[n]).map(n=>({n,values:sma(closes(bars),n)})),g=TC.geometry(bars,lines.map(l=>l.values));
  if(!g){put(dev.chart,empty('NO_CLOSE','그릴 종가가 없습니다'));return;}
  const dates=CW.dailyView(bars,d.timezone).map(b=>b.time),last=bars.length-1;
  const svg=h('svg:svg',{class:'curve tech-chart',viewBox:'0 0 640 240',role:'img',focusable:'false',dataset:{techChartSvg:d.symbol},
   'aria-label':'이 기기 일봉 종가 선 · '+d.symbol+' · '+RANGE_KO[d.range]+' · '+bars.length+'봉 · 판정 보류 · 누르면 그 자리를 노트 양식에 채움'},
   h('svg:path',{d:'M20,220 L620,220',class:'curve-base'}),
   TC.paths(bars.map(b=>b.close),g).map(p=>h('svg:path',{d:p,class:'curve-s',dataset:{closeLine:''}})),
   lines.flatMap(l=>TC.paths(l.values,g).map(p=>h('svg:path',{d:p,fill:'none',stroke:MUTED,'stroke-width':'1.5','stroke-dasharray':SMA_DASH[l.n],'vector-effect':'non-scaling-stroke',dataset:{smaLine:String(l.n)}}))),
   markNodes(g,dates,d.symbol));
  svg.addEventListener('click',e=>{const m=svg.getScreenCTM();if(!m)return;const pt=svg.createSVGPoint();pt.x=e.clientX;pt.y=e.clientY;const q=pt.matrixTransform(m.inverse());
   const p=priceAt(g,q.y);if(p===null)return;notes.fill(dates[indexAt(bars.length,q.x)],p);},{signal});
  // The scale as text under the chart (SVG text would shrink to nothing on a phone); prices only inside [data-ram-price].
  dev.chart.replaceChildren(svg,h('p',{class:'reason',dataset:{techChartRange:''}},'세로 ',h('span',{dataset:{ramPrice:''}},fmt(g.minimum*g.scale)),' ~ ',
   h('span',{dataset:{ramPrice:''}},fmt(g.maximum*g.scale)),' ',d.currency,' · 가로 ',dates[0],' ~ ',dates[last]));
  const lastBar=bars[last];
  put(dev.facts,h('dl',{class:'card-body'},
   [['출처',d.provider+' · '+d.symbol+' · '+d.exchange],['기간',RANGE_KO[d.range]+' · '+bars.length+'봉 · 일봉만 (주봉은 비공개 차트 준비 뒤)'],
    ['마지막 봉',h('span',null,dates[last],' · 종가 ',h('span',{dataset:{ramPrice:''}},fmt(lastBar.close),' ',d.currency),lastBar.session_status==='COMPLETE'?'':' · 장중 또는 미확정')],
    ['읽은 시각',clock(d.read_at)],['가격 기준',['RAW_CLOSE (원주가) · '+CONT.text+' → 지표·패턴 판정 보류 (',code(CONT.code),')']]].map(([k,v])=>[h('dt',null,h('b',null,k)),h('dd',null,v)])),
   h('p',{class:'reason'},'— 종가 · ┄ 지표 선은 표시용(연구용, 판정 아님) · 보라 점선은 내 노트 · 차트를 누르면 그 날짜와 위치 가격을 2.3 노트 양식에 채웁니다'));
  if(!dev.lines.firstChild)put(dev.lines,...SMA_N.map(n=>{const id='tech-sma-'+n;return h('label',{class:'check',for:id},h('input',{type:'checkbox',id,checked:V.sma[n],dataset:{techSma:String(n)},
   onchange:e=>{V.sma[n]=e.target.checked;if(S.dev.data)drawChart();}}),'SMA '+n);}));}
 function markNodes(g,dates,symbol){const st=stored(),list=marks(g,dates,ofSymbol(st.items,symbol,'chart-annotation/1')),by=new Map(st.items.map(o=>[o.id,o]));
  const line={fill:'none',stroke:MINE,'stroke-width':'2','stroke-dasharray':'5 4','vector-effect':'non-scaling-stroke'};
  return list.map(m=>{const o=by.get(m.id),title=h('svg:title',null,'사용자 작성 · '+NOTE_KINDS[m.kind]+(o&&o.text?' · '+o.text:''));
   if(m.kind==='MEMO')return h('svg:circle',{cx:m.cx,cy:m.cy,r:'6',...line,dataset:{noteMark:m.id,noteKind:m.kind}},title);
   if(m.kind==='RANGE')return h('svg:rect',{x:m.x,y:m.y,width:m.w,height:m.h,...line,dataset:{noteMark:m.id,noteKind:m.kind}},title);
   return h('svg:path',{d:m.d,...line,dataset:{noteMark:m.id,noteKind:m.kind}},title);});}
 const panelChart=I.parts.privatePanel({id:'tech-kis-chart',title:'실가격 차트 · 지표 (KIS 통합 일봉)'});
 const b311=block('3.1.1',sub('차트 탐색','3.1.1','공개 · 이 기기 · 비공개 세 층'),
  h('p',{dataset:{publicChart:'NONE',na:HOLD.code}},h('b',null,'공개 차트 없음'),' · ',HOLD.text,' (',code(HOLD.code),')'),
  h('p',{class:'reason',dataset:{na:IEX.code}},IEX.text,' (',code(IEX.code),') · 합성 시험 봉은 화면에 싣지 않음'),
  h('div',{class:'sk mine outside',dataset:{techDevice:''}},h('h4',null,'이 기기 일봉 · 차트만 · 판정 보류'),
   h('p',{class:'reason'},'누를 때만 이 기기의 비공개 Worker에 묻고 RAM에만 둠 · 저장·전송 안 함 · 공개 값 아님 · 판정·신호·매매 기능 없음'),
   h('div',{class:'load-row'},h('label',{for:'tech-range',class:'check'},'기간 ',rangeSel),loadBtn),dev.why,dev.status,dev.chart,dev.lines,dev.facts),
  h('p',{class:'reason',dataset:{privateWhy:'tech-kis-chart'}},'비공개 층: KIS 원주가(MODP=0)는 조정 완료 가격으로 보지 않음 · 차트 계열 = 원주가 + 확인된 분할(원주가÷수정주가 정수비 계단 + SEC 주식수 교차 확인) · MODP=1은 대조용 · 확인 구간만 판정 · KIS 값은 공개 파일·화면·로그에 넣지 않음'));

 // 3.1.2 지표와 정도 설정
 const b312=block('3.1.2',sub('지표와 정도 설정','3.1.2','연구 표시용 · 기간은 지금 고정'),
  h('div',{class:'tbl-wrap'},h('table',{class:'tbl',dataset:{indicators:''}},h('caption',null,'지표 판정은 모두 보류 · ',HOLD.text),
   h('thead',null,h('tr',null,h('th',{scope:'col'},'지표 · 기간'),h('th',{scope:'col'},'보는 것'),h('th',{scope:'col'},'판정'))),
   h('tbody',null,INDICATORS.map(([id,name,win,what,kind])=>h('tr',{dataset:{indicator:id}},h('th',{scope:'row'},name,h('span',{class:'sub'},id,' · ',win)),h('td',null,what,' · 판정하면: ',kind),
    h('td',null,hold(HOLD.code))))))),
  prep('정도(기간 묶음) 고르기',['승인된 기간 묶음 정의']));

 // 3.1.3 시나리오: the official one is not computed; the user's own are kept on this device.
 const scen={form:h('div',{dataset:{scenarioForm:''}}),list:h('div',{dataset:{scenarioList:''}}),status:h('p',{class:'reason',role:'status',dataset:{scenarioStatus:''}})};
 // Built once (typed values survive repaints); shown when a company is chosen and the store is readable.
 const sc=(()=>{
  const dir=h('select',{id:'tech-sc-dir',dataset:{scDir:''}},Object.entries(DIRECTIONS).map(([k,[ko,ar]])=>h('option',{value:k},ar+' '+ko)));
  const date=h('input',{type:'date',id:'tech-sc-date',value:today(),dataset:{scDate:''}});
  const lv=[1,2,3].map(i=>({label:h('input',{type:'text',id:'tech-sc-l'+i,maxlength:'40',autocomplete:'off',dataset:{scLabel:String(i)}}),
   price:h('input',{type:'number',id:'tech-sc-p'+i,min:'0',step:'any',inputmode:'decimal',dataset:{scPrice:String(i)}})}));
  const cond=h('input',{type:'text',id:'tech-sc-cond',maxlength:'500',autocomplete:'off',dataset:{scCond:''}}),inv=h('input',{type:'text',id:'tech-sc-inv',maxlength:'500',autocomplete:'off',dataset:{scInv:''}});
  const invP=h('input',{type:'number',id:'tech-sc-invp',min:'0',step:'any',inputmode:'decimal',dataset:{scInvPrice:''}}),horizon=h('span',{dataset:{scHorizon:''}});
  const say=t=>{scen.status.textContent=t;};
  const save=h('button',{type:'button',class:'btn mine',dataset:{scenarioSave:''},onclick:e=>{const r=S.row;if(!r)return;
   const levels=lv.map(x=>({label:x.label.value.trim(),price:num(x.price.value)}));
   if(levels.some(l=>Number.isNaN(l.price)||(l.price!==null&&!positive(l.price)))||!levels.some(l=>positive(l.price))){say('저장하지 않음 · 핵심 가격을 하나 이상 0보다 큰 수로 적어 주세요');return;}
   const ip=num(invP.value);if(Number.isNaN(ip)||(ip!==null&&!positive(ip))){say('저장하지 않음 · 무효화 가격은 비우거나 0보다 큰 수로 적어 주세요');return;}
   const o=scenarioFor({symbol:r.ticker,direction:dir.value,horizon:V.tf==='W'?'long':'swing',date:date.value,levels:levels.filter(l=>positive(l.price)),condition:cond.value.trim(),invalidation:inv.value.trim(),invalidationPrice:ip});
   if(!o){say('저장하지 않음 · 기준 날짜를 확인해 주세요');return;}
   try{I.store.chartNotes.add(e,o);}catch(err){say('저장하지 않음 · '+noteWords(errCode(err)));return;}
   say('시나리오를 이 기기에 저장했습니다 · 계정 단계 없음');for(const x of lv){x.label.value='';x.price.value='';}cond.value='';inv.value='';invP.value='';changed();}},'시나리오 저장 · 이 기기에만');
  const node=h('div',null,h('div',{class:'model-boxes'},field('방향',dir,'tech-sc-dir'),field('기준 날짜',date,'tech-sc-date'),
   ...lv.flatMap((x,i)=>[field('핵심 가격 '+(i+1)+' 이름'+(i?' (선택)':''),x.label,'tech-sc-l'+(i+1)),field('핵심 가격 '+(i+1)+(i?' (선택)':''),x.price,'tech-sc-p'+(i+1))]),
   field('조건',cond,'tech-sc-cond'),field('무효화',inv,'tech-sc-inv'),field('무효화 가격 (선택)',invP,'tech-sc-invp')),
   h('p',{class:'reason'},'보기: ',horizon,' (2.2 정도 설정을 따름) · 가격은 내가 적는 기준선 · 공급처 값 아님'),save);
  return{node,horizon};})();
 function scenarioForm(){const r=S.row,st=stored();sc.horizon.textContent=tfWord();
  if(!layer){put(scen.form,failed('LOADER_FAILED','층을 불러오지 못해 시나리오를 읽지 못했습니다','새로고침해 주세요'));return;}
  if(!r){put(scen.form,h('p',{class:'reason'},'기업을 고르면 그 기업의 시나리오를 이 기기에 적을 수 있습니다'));return;}
  if(unusable(st)){put(scen.form);return;}
  if(scen.form.firstChild!==sc.node)put(scen.form,sc.node);}
 function scenarioList(){const r=S.row;if(!layer||!r){put(scen.list);return;}
  const st=stored();if(unusable(st)){put(scen.list,storeFail(st));return;}
  const mine=ofSymbol(st.items,r.ticker,'chart-scenario/1');
  if(!mine.length){put(scen.list,empty('NO_SCENARIO',r.ticker+'의 시나리오가 아직 없습니다 · 이 기기 기준'));return;}
  put(scen.list,h('ul',{class:'news-lines',dataset:{scenarios:r.ticker}},mine.map(o=>h('li',{dataset:{scenario:o.id}},h('span',{class:'pill'},'사용자 작성'),' ',
   DIRECTIONS[o.direction][1],' ',DIRECTIONS[o.direction][0],' · ',o.horizon==='long'?'장기':'스윙',' · 기준 ',o.anchor_time,' · 핵심 가격 ',
   o.levels.map((l,i)=>[i?', ':'',l.label?l.label+' ':'',h('span',{dataset:{userPrice:''}},String(l.price))]),
   o.condition?' · 조건: '+o.condition:'',o.invalidation||o.invalidation_price!==null?[' · 무효화: ',o.invalidation||'',o.invalidation_price!==null?h('span',{dataset:{userPrice:''}},' (',String(o.invalidation_price),')'):null]:null,' ',
   h('button',{type:'button',class:'linkish',dataset:{scenarioDelete:o.id},'aria-label':'시나리오 지우기 · '+DIRECTIONS[o.direction][0]+' · 기준 '+o.anchor_time,onclick:e=>remove(e,o.id,scen.status)},'지우기')))));}
 onChange(()=>{scenarioForm();scenarioList();});
 const b313=block('3.1.3',sub('시나리오','3.1.3','방향 · 핵심 가격 · 조건 · 무효화'),
  prep('공식 시나리오',['같은 패턴·정도의 과거 결과 빈도 (시나리오 근거)','승인·검증된 가격 계열']),
  h('h4',null,'내 시나리오 · 이 기기에만'),scen.form,scen.status,scen.list);

 // 3.1.4 결과 구분
 const b314=block('3.1.4',sub('결과 구분','3.1.4','섞지 않고 따로 표시'),h('ul',{class:'news-lines',dataset:{resultKinds:''}},
  h('li',{dataset:{kind:'AUTO'}},h('b',null,'공식 판정'),' · 지금 보류 (',code(HOLD.code),')'),
  h('li',{dataset:{kind:'USER_SETTINGS'}},h('b',null,'사용자 설정 탐색'),' · 정도를 바꾼 결과 · 공식 이력에 쓰지 않음 · 지금은 계열이 없어 탐색도 없음'),
  h('li',{dataset:{kind:'USER'}},h('b',null,'사용자 작성'),' · 내 노트 · 시나리오 (보라 점선) · 이 기기에만 · 공식 증거 아님'),
  h('li',{dataset:{kind:'PRIVATE'}},h('b',null,'비공개 KIS'),' · 로그인한 오너에게만 덧붙음 · ',typeof I.privateArea.text==='function'&&typeof I.privateArea.text()==='string'?I.privateArea.text():'비공개 기능 준비 중')));

 /* ---------------- 2-2 · 3.2 차트 패턴 */
 const b321=block('3.2.1',sub('패턴 탐색','3.2.1',PATTERN_RULES.label_ko+' (pattern-rules/1)'),
  h('p',{class:'reason'},'패턴 판정은 모두 보류 · ',HOLD.text,' (',code(HOLD.code),')'),
  h('ul',{class:'news-lines',dataset:{patterns:''}},PATTERNS.map(([id,name,what])=>h('li',{dataset:{pattern:id}},h('b',null,name),' · ',what,' ',hold(HOLD.code)))));
 const degree=h('div',{class:'scroll',role:'group','aria-label':'정도 설정',dataset:{degree:''}});
 const params=h('div',{dataset:{params:''}}),minBars=h('div',{dataset:{minBars:''}});
 const paintDegree=onChange(()=>{
  if(!degree.firstChild)put(degree,...[['D','스윙 · 일봉 기준'],['W','장기 · 주봉 기준']].map(([k,t])=>h('button',{type:'button',class:'chip',dataset:{degreeTf:k},
   onclick:()=>{if(V.tf===k)return;V.tf=k;changed();}},t)));
  for(const b of degree.querySelectorAll('[data-degree-tf]'))b.setAttribute('aria-pressed',String(V.tf===b.dataset.degreeTf));
  const CW=window.ChartWorkbench,grid=CW&&Array.isArray(CW.EXPLORE_GRID)?CW.EXPLORE_GRID:null;
  if(!grid){put(params,failed('PATTERN_GRID_MISSING','규칙 탐색 묶음을 불러오지 못했습니다','규칙 기본값은 그대로 · 탐색 묶음만 없음'));}
  else put(params,h('div',{class:'tbl-wrap'},h('table',{class:'tbl',dataset:{paramTf:V.tf}},h('caption',null,tfWord(),' · ',PATTERN_RULES.label_ko,' · 탐색 결과는 "사용자 설정 탐색"으로 따로 · 공식 이력에 쓰지 않음'),
   h('thead',null,h('tr',null,h('th',{scope:'col'},'규칙'),h('th',{scope:'col',class:'num'},'기본값'),h('th',{scope:'col'},'탐색 묶음'))),
   h('tbody',null,paramRows(PATTERN_RULES,grid,V.tf).map(([name,label,value,choices])=>h('tr',{dataset:{param:name}},h('th',{scope:'row'},label,h('span',{class:'sub'},name)),
    h('td',{class:'num'},String(value)),h('td',null,choices?choices.join(' · '):'— · 따로 고르지 않음')))))));
  const mb=CW&&typeof CW.minBars==='function'?CW.minBars(PATTERN_RULES.params,V.tf):null;
  put(minBars,mb?h('ul',{class:'news-lines'},mb.map(([k,n])=>h('li',{dataset:{minBar:k}},MIN_BARS_KO[k]||k,' · 최소 ',String(n),'봉'))):failed('MIN_BARS_MISSING','최소 봉 수를 계산하지 못했습니다'));});
 const b322=block('3.2.2',sub('정도 설정','3.2.2','규칙의 민감도 묶음'),degree,params);
 const b323=block('3.2.3',sub('확인 · 실패 · 무효화','3.2.3','형태 적합도는 상승 확률이 아님'),
  h('ol',{class:'news-lines',dataset:{states:''}},STATES.map(([k,t])=>h('li',{dataset:{state:k}},h('b',null,t),' (',k,')'))),
  h('p',{class:'reason'},'형성 → 확인 → 확인 후 실패 · 무효화 · 만료 · 지금 공개 화면의 모든 패턴은 "판정 불가"로 둡니다'));
 const b324=block('3.2.4',sub('패턴 카드와 시나리오','3.2.4'),prep('패턴 카드 (근거 · 확인 가격 · 무효화 가격)',['승인·검증된 가격 계열','시나리오 근거 빈도']));
 const b325=block('3.2.5',sub('데이터 적합성','3.2.5','TA-361'),
  h('p',{dataset:{suitability:CONT.code}},h('b',null,'실가격 창 판정 불가'),' · ',code(CONT.code),' · 공개 쪽 분할 공급원 없음 (Yahoo 분할 이벤트 경로 쓰지 않음)'),
  h('p',{class:'reason'},'분할 확인은 비공개 KIS 차트에서만: 원주가÷수정주가 정수비 계단 + SEC 주식수 교차 확인 · 확인 안 된 구간은 분석 보류와 사유'),
  h('h4',null,'규칙이 요구하는 최소 봉 수 · ',h('span',{dataset:{minBarsTf:''}},'')),minBars);
 const panelPattern=I.parts.privatePanel({id:'tech-kis-pattern',title:'패턴 탐색 (KIS 분할 반영 계열, 탐색 전용)'});
 onChange(()=>{const t=b325.querySelector('[data-min-bars-tf]');if(t)t.textContent=tfWord();});

 /* ---------------- 2-3 · 3.3 차트 노트 */
 const notes=(()=>{
  const wrap=h('div',{dataset:{notes:''}}),status=h('p',{class:'reason',role:'status',dataset:{noteStatus:''}}),list=h('div',{dataset:{noteList:''}});
  const kind=h('select',{id:'tech-note-kind',dataset:{noteKind:''}},h('option',{value:'HLINE'},'수평선'),h('option',{value:'MEMO'},'메모'));
  const date=h('input',{type:'date',id:'tech-note-date',value:today(),dataset:{noteDate:''}});
  const price=h('input',{type:'number',id:'tech-note-price',min:'0',step:'any',inputmode:'decimal',dataset:{notePrice:''}});
  const text=h('input',{type:'text',id:'tech-note-text',maxlength:'500',autocomplete:'off',dataset:{noteText:''}});
  const save=h('button',{type:'button',class:'btn mine',dataset:{noteSave:''},onclick:e=>{const r=S.row;if(!r)return;
   const p=num(price.value),o=noteFor({kind:kind.value,symbol:r.ticker,date:date.value,price:p,text:text.value.trim()});
   if(!o){status.textContent='저장하지 않음 · 날짜와 0보다 큰 가격을 적어 주세요';return;}
   try{I.store.chartNotes.add(e,o);}catch(err){status.textContent='저장하지 않음 · '+noteWords(errCode(err));return;}
   status.textContent='노트를 이 기기에 저장했습니다 · 계정 단계 없음';text.value='';changed();}},'노트 저장 · 이 기기에만');
  const form=h('div',{dataset:{noteForm:''}},h('div',{class:'model-boxes'},field('종류',kind,'tech-note-kind'),field('날짜',date,'tech-note-date'),field('가격 (내 기준선)',price,'tech-note-price'),field('메모 (선택, 500자까지)',text,'tech-note-text')),save);
  function paint(){const r=S.row,st=stored();
   if(!layer){put(wrap,failed('LOADER_FAILED','층을 불러오지 못해 노트를 읽지 못했습니다','새로고침해 주세요'));return;}
   if(!r){put(wrap,empty('NO_COMPANY','기업을 고르면 그 기업의 노트를 씁니다 · 이 기기에만 저장'));return;}
   if(unusable(st)){put(wrap,storeFail(st));return;}
   save.disabled=false;
   const mine=ofSymbol(st.items,r.ticker,'chart-annotation/1'),all=st.items.length,lim=window.ChartWorkbench?window.ChartWorkbench.USER_LIMIT:500;
   put(list,h('p',{class:'meta',dataset:{noteCounts:mine.length+'/'+all}},r.ticker,' 노트 ',String(mine.length),'개 · 이 기기 전체 사용자 작성 ',String(all),'개 / ',String(lim)),
    st.state==='PARTLY_INVALID'?h('p',{class:'reason',dataset:{notesPartly:String(st.unreadable)}},'읽지 못한 항목 ',String(st.unreadable),'개는 지우지 않고 그대로 둡니다'):null,
    mine.length?h('ul',{class:'news-lines',dataset:{noteItems:r.ticker}},mine.map(o=>h('li',{dataset:{note:o.id,noteKind:o.kind}},h('span',{class:'pill'},'사용자 작성'),' ',
     h('b',null,NOTE_KINDS[o.kind]||o.kind),' · ',o.interval==='W'?'주봉':'일봉',' · ',o.points.length>2?['점 ',String(o.points.length),'개 · ',o.points[0].time,' ~ ',o.points[o.points.length-1].time]
      :o.points.map((p,i)=>[i?' ~ ':'',p.time,' · 가격 ',h('span',{dataset:{userPrice:''}},String(p.price))]),o.text?' · '+o.text:'',' · 적은 날 ',String(o.created_at).slice(0,10),' ',
     h('button',{type:'button',class:'linkish',dataset:{noteDelete:o.id},'aria-label':'노트 지우기 · '+(NOTE_KINDS[o.kind]||o.kind)+' · '+o.points[0].time,onclick:e=>remove(e,o.id,status)},'지우기'))))
     :empty('NO_NOTE',r.ticker+'의 노트가 아직 없습니다 · 이 기기 기준'));
   put(wrap,form,status,list);}
  // A click on the device chart: that bar's date and the pointer's price (the user's own coordinate) into the form.
  function fill(d,p){if(!S.row||!wrap.contains(form))return;date.value=d;price.value=String(p);status.textContent='차트에서 고른 자리를 양식에 채웠습니다 · '+d+' · 저장은 노트 저장 단추로';}
  onChange(paint);
  return{wrap,fill};})();
 function storeFail(st){return st.state==='INVALID'?failed('CHART_NOTES_STORAGE_INVALID','이 기기에 저장된 노트를 읽지 못했습니다','덮어쓰지 않습니다 · 기기 백업으로 옮긴 뒤 설정에서 지울 수 있습니다')
  :st.state==='MODULE_MISSING'?failed('CHART_MODULE_MISSING','차트 노트 모듈(ChartWorkbench)을 불러오지 못해 노트를 읽지 못했습니다','저장된 노트는 그대로입니다 · 새로고침해 주세요')
  :failed('STORAGE_UNAVAILABLE','이 브라우저 저장소를 쓸 수 없습니다','사생활 보호 모드나 저장소 차단을 확인해 주세요');}
 function remove(e,id,status){try{I.store.chartNotes.remove(e,id);}catch(err){const c=errCode(err);status.textContent='지우지 않음 · '+noteWords(c);if(c==='CHART_NOTE_NOT_FOUND')changed();return;}
  status.textContent='지웠습니다 · 이 기기에서만';changed();}
 const b33=block('3.3',sub('차트 노트','3.3','보라 점선 · 이 기기에만'),
  h('p',{class:'reason'},'수평선 · 메모를 날짜와 내 기준 가격으로 적습니다 · 기기 일봉을 불러오면 차트 위에 보이고, 차트를 누르면 그 자리가 양식에 채워집니다 · 이 기기에만 저장 (백업 /5에 포함) · 계정 단계 없음 · 공식 탐지·성과 기록에 쓰지 않음'),
  notes.wrap);

 /* ---------------- 2-4 · 3.4 내용구성 트리 (ia-screens.js technicalTree, static) */
 const jump=(sec,t)=>h('button',{type:'button',class:'linkish',dataset:{jump:sec},onclick:()=>{const el=document.getElementById('s-'+sec);if(!el)return;el.setAttribute('tabindex','-1');el.scrollIntoView({block:'start'});el.focus({preventScroll:true});}},'↑ ',t);
 const node=(no,title,note,kids,sec)=>h('li',{dataset:{treeNode:no}},h('details',{open:no.split('.').length<3},h('summary',null,h('b',null,no,' ',title),note?' · '+note:''),
  kids&&kids.length?h('ul',{class:'news-lines'},kids):null,sec?jump(sec,'이 화면 '+sec.replace('-','.')+'에서 보기'):null));
 const leaf=(no,title,note)=>h('li',{dataset:{treeNode:no}},h('b',null,no,' ',title),note?[' · ',note]:null);
 const b34=block('3.4',sub('기술적 분석 내용구성','3.4','입력 → 지표 → 패턴 → 시나리오 → 내 노트'),
  h('p',{class:'reason'},'상자 번호(3.x)는 기능 번호, 메뉴 번호(2.x)가 아님 · QGV 점수와 나란히 볼 뿐 합치지 않음'),
  h('ul',{class:'news-lines',dataset:{techTree:''}},
   leaf('입력','일봉','공개: 승인된 계열 없음 · 이 기기: 누를 때 Worker 일봉(RAM) · 비공개: KIS 통합 일봉 (준비 중) · 가격 기준 RAW_CLOSE'),
   node('3.1','기술적 지표 · 시나리오','메뉴 2.1',[leaf('3.1.1','차트 탐색','일봉 · 장기/스윙 보기'),leaf('3.1.2','지표와 정도 설정','SMA 5·20·60·120·240 · EMA 20 · RSI 14 · MACD 12·26·9 · 볼린저 20·2σ · ATR 14'),
    leaf('3.1.3','시나리오','사용자 작성 (chart-scenario/1): 상승·횡보·하락 · 핵심 가격 · 조건 · 무효화 · 이 기기에만'),leaf('3.1.4','결과 구분','공식 · 사용자 설정 탐색 · 사용자 작성 · 비공개')],'2-1'),
   node('3.2','차트 패턴 · 시나리오','메뉴 2.2 · '+PATTERN_RULES.label_ko,[leaf('3.2.1','패턴 탐색','지지·저항 구간 · 박스 돌파·이탈 · 이중 바닥·천장'),leaf('3.2.2','정도 설정','민감도 묶음 · 공식 이력에 쓰지 않음'),
    leaf('3.2.3','확인 · 실패 · 무효화','형태 적합도는 확률이 아님'),leaf('3.2.4','패턴 카드와 시나리오','근거 빈도 미산출'),leaf('3.2.5','데이터 적합성',['공개 실가격은 판정 불가 · ',code(CONT.code)])],'2-2'),
   node('3.3','차트 노트 (보라 점선)','메뉴 2.3',[leaf('3.3.1','직접 작성','수평선 · 메모 (chart-annotation/1)'),leaf('3.3.2','편집과 저장','이 기기에만 · 백업 /5 · 계정 저장은 결정 대기 (DRAW-STORE)'),
    leaf('3.3.3','분석과 분리','공식 탐지 이력·성과 기록에 쓰지 않음')],'2-3')),
  h('p',{class:'na',dataset:{treeExample:HOLD.code}},'실가격 예시: — · ',HOLD.text,' · 가격은 공개하지 않습니다 (',code(HOLD.code),')'),
  h('p',{class:'reason',dataset:{treePrivate:''}},'선택: 고른 기업의 KIS 지표 값 예시 (3.1 결과 읽기만) · ',typeof I.privateArea.text==='function'&&typeof I.privateArea.text()==='string'?I.privateArea.text():'비공개 기능 준비 중'));

 /* ---------------- assemble */
 put(slots['2-1'],verdictBand,b311,b312,b313,b314,panelChart.node);
 put(slots['2-2'],b321,b322,b323,b324,b325,panelPattern.node);
 put(slots['2-3'],b33);
 put(slots['2-4'],b34);
 root.dataset.screenState=layer?'ready':'partial';
 changed();attachBox();resolve();
}

I.technicalLive=Object.freeze({screen,helpers:Object.freeze({HOLD,IEX,CONT,INDICATORS,PATTERN_RULES,PATTERNS,HIST_WORDS,mean,sma,closes,priceAt,indexAt,noteFor,scenarioFor,ofSymbol,marks,paramRows})});
})();
