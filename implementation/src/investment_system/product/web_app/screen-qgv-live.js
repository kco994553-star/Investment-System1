/* 1. QGV · 1.1 리더보드, the part that runs after IS2.ready (feature 2.1.1–2.1.7, P2-2a; P1_DATA_LAYER.md §1.1 screen-file rule).
   screen-qgv.js draws the first-paint skeleton (screen head, the QGV band with three disabled price buttons, four sections, the
   seven 1.1.x blocks with pending text) and, once IS2.ready resolved, hands its regions to IS2.qgvLive.leaderboard(route, refs)
   from this file (loader.js LOAD_ORDER, after screen-search-live.js). This file fills those regions in place; nothing here touches
   the layer while the file loads (it only puts IS2.qgvLive).
   - Data: IS2.qgv.page() with the default profile only (never setProfile / preset / gate: every screen shares one Page), rows /
     rankLabel / reasonText / preview / model; IS2.data.get of sec-qgv2.json and company-classification.json (CORE), the reviewed
     names (company-names-ko.json); IS2.prices status / rankFor / periodReturns; IS2.store prefs / weights. Opening reads CORE +
     actual-catalog.json + company-names-ko.json only.
   - ONE table (2.1.1) of the Universe504 rows that every control of 2.1.2–2.1.6 changes: list, sort, filters, period, return
     order, preview. No TARGET v0 scope, box, pill, filter or column (owner 2026-10-27, DC-24: TARGET v0 has nothing to do with QGV).
     Sorting and filters only order / hide rows: rank numbers are the layer's. NA is never 0; a missing value shows NA and its
     reason (<details>). The view state lives in RAM in this module (kept across routes of one page load, gone on reload).
   - Prices only after a click on this screen's buttons; price-derived values (M3 ranks, period returns) only as text inside
     [data-ram-price], never in an attribute, a sort value, storage, the console or the URL. Reason codes go to data-na /
     data-reason; the visible words come from say(code, fallback).
   - Small pure parts are ported from web_assets/leaderboard-screen.js (not loaded, Main 2026-10-25), each naming its source line;
     tools/web_app_qgv_screen_node_test.js pins them equal to the old functions and to frozen vectors. */
(function(){
'use strict';
const I=window.IS2,{h,href}=I,mascot=m=>I.parts.mascot(m);
const QGV2='sec-qgv2.json',CLS='company-classification.json',NAMES='company-names-ko.json',STEP=50;
const ok=v=>typeof v==='number'&&Number.isFinite(v);
const loaded=x=>!!x&&typeof x==='object'&&x.state!=='NOT_READY';
const get=(o,...keys)=>keys.reduce((x,k)=>(x===null||x===undefined?undefined:x[k]),o);

/* ---------------------------------------------------------------- pure parts (ports, node parity) */
// Sort ids, keys and directions: leaderboard-screen.js:128–134 SORTS without ticker-desc / name-desc (the board has no reverse
// option); labels from board L:145.
const SORTS=Object.freeze([['qgv','qgv',-1,'QGV 높은 순 (기본)'],['qgv-asc','qgv',1,'QGV 낮은 순'],['q-desc','q',-1,'Q 높은 순'],['q-asc','q',1,'Q 낮은 순'],
 ['g-desc','g',-1,'G 높은 순'],['g-asc','g',1,'G 낮은 순'],['v-desc','v',-1,'V 높은 순'],['v-asc','v',1,'V 낮은 순'],['ticker','ticker',1,'티커 순'],['name','name',1,'기업명 순'],
 ['favorites','favorites',-1,'관심기업 우선'],['asof-desc','asof',-1,'자료 기준일 최신 순'],['asof-asc','asof',1,'자료 기준일 오래된 순'],
 ['cap-desc','cap',-1,'시가총액 큰 순 · 내 기기'],['cap-asc','cap',1,'시가총액 작은 순 · 내 기기']].map(s=>Object.freeze(s)));
const sortSpec=id=>SORTS.find(s=>s[0]===id)||SORTS[0];// sortSpec :135
// oppositeSort :140 over this list: the same key in the other direction; null for the one-way keys ticker, name, favorites.
function oppositeSort(id){const[,key,dir]=sortSpec(id),o=SORTS.find(s=>s[1]===key&&s[2]===-dir);return o?o[0]:null;}
/* sortRows :146–158 (D11) for the ids it orders (qgv, q, g, v, asof, cap): QGV = ranked rows, then the QG reference tier by its own
   total, then rows without a total, never interleaved; equal totals by place number (rank / QG order, the publication's tie order), then ticker; cap ties by company id; NA last both ways.
   ticker / favorites as DeviceWatchlist.filter (watchlist.js:5). name: NEW rule (Main 2026-10-25), the shown title with
   localeCompare 'ko', ties by ticker. rows = page rows; cap(row) = M3 rank (1 = largest) or null; rank(row) = the rank shown. */
function sortRows(rows,id,{cap=null,title=null,interests=[],rank=r=>r.rank.official}={}){
 const[,key,dir]=sortSpec(id);
 if(key==='ticker')return[...rows].sort((a,b)=>a.ticker.localeCompare(b.ticker));
 if(key==='favorites')return[...rows].sort((a,b)=>Number(interests.includes(b.id))-Number(interests.includes(a.id))||a.ticker.localeCompare(b.ticker));
 if(key==='name'){const t=typeof title==='function'?title:r=>r.ticker,k=rows.map(r=>({r,t:String(t(r))}));k.sort((a,b)=>a.t.localeCompare(b.t,'ko')||a.r.ticker.localeCompare(b.r.ticker));return k.map(x=>x.r);}
 const num=v=>(ok(v)?v:null),ranked=r=>Number.isInteger(rank(r)),qg=r=>r.rank.qg_reference_order!==null;
 const value=r=>{if(key==='qgv')return ranked(r)||qg(r)?num(r.score.total):null;if(key==='q'||key==='g'||key==='v')return num(r.score[key]);
  if(key==='asof'){const t=Date.parse(r.acquired_at);return Number.isFinite(t)?t:null;}if(key==='cap'){const m=cap?cap(r):null;return Number.isInteger(m)?m:null;}return null;};
 const tie=key==='cap'?(a,b)=>(a.id<b.id?-1:a.id>b.id?1:0):(a,b)=>String(a.ticker).localeCompare(String(b.ticker));
 // Equal totals under the qgv sort follow the place number (rank, or the QG order in tier 1), the publication's tie order
 // (total, symbol, key), reversed for low-first; then ticker. Same rule as the old S06 sortRows (leaderboard-screen.js).
 const m=key==='cap'?-dir:dir,tier=r=>(key==='qgv'&&qg(r)&&!ranked(r)?1:0);
 const place=r=>key!=='qgv'?null:ranked(r)?rank(r):qg(r)&&Number.isInteger(r.rank.qg_reference_order)?r.rank.qg_reference_order:null,keyed=rows.map(r=>({r,v:value(r),t:tier(r),p:place(r)}));
 keyed.sort((a,b)=>(a.v===null)-(b.v===null)||a.t-b.t||(a.v!==null&&b.v!==null?(a.v<b.v?-1:a.v>b.v?1:0)*m:0)||(a.v!==null&&b.v!==null&&a.p!==null&&b.p!==null?(a.p-b.p)*-m:0)||tie(a.r,b.r));
 return keyed.map(x=>x.r);}
// sicOf :41 (identity.company_id = the row id): the published 4-digit SIC; '0000', WITHDRAWN and identity_withdrawn are null.
const SIC4=/^\d{4}$/;
function sicOf(identity,ps={}){const id=identity.company_id,code=v=>(typeof v==='string'&&SIC4.test(v)&&v!=='0000'?v:null);
 if(typeof id==='string'&&id.includes(':')){const rec=get(ps,QGV2,'records',id);return rec&&rec.state!=='WITHDRAWN'&&rec.identity_withdrawn!==true?code(rec.sic):null;}
 const ind=get(ps,CLS,'data','companies',id,'industry');return ind&&ind.identity_withdrawn!==true?code(ind.sic):null;}
// classificationOf :47–56, the industry part only (the type axis is the page row's own types here).
function industryOf(identity,ps={}){const id=identity.company_id,live=r=>!!r&&['LIVE','STALE'].includes(r.state)&&r.identity_withdrawn!==true;
 if(typeof id==='string'&&id.includes(':')){const rec=get(ps,QGV2,'records',id);return live(rec)?rec.industry_group||null:null;}
 const ind=get(ps,CLS,'data','companies',id,'industry');return live(ind)?ind.group||null:null;}
// filterClassifications :63 (sicMatch :45), industry and SIC filters only; '' = all, 'NOT_AVAILABLE' = no classification.
const sicMatch=(sic,want,digits)=>!want||(want==='NOT_AVAILABLE'?sic===null:sic!==null&&sic.slice(0,digits)===want);
function filterClassified(identities,ps={},f={}){return identities.filter(c=>{const ind=industryOf(c,ps),sic=sicOf(c,ps),i=f.industry;
 return(!i||(i==='NOT_AVAILABLE'?ind===null:ind===i))&&sicMatch(sic,f.sic4,4)&&sicMatch(sic,f.sic2,2);});}
// populationOf :160: pooled sec-qgv2 cross-section rows (in_cross_section, LIVE / STALE, same calc version, not withdrawn).
function populationOf(ps){const inputs=ps&&ps[QGV2];if(!inputs||!inputs.records||typeof inputs.records!=='object')return null;
 let n=0;for(const r of Object.values(inputs.records))if(r&&r.in_cross_section===true&&['LIVE','STALE'].includes(r.state)&&r.calc_version_mismatch!==true&&r.identity_withdrawn!==true)n++;return n;}
// The 2.1.5 list of a row (D12: rows outside the Universe and reference rows have no list place; exploreGroup alone ignores it).
function listOf(r){if(r.scope==='OUTSIDE_UNIVERSE'||r.reference_only)return null;if(Number.isInteger(r.rank.official))return'RANKED';if(r.rank.qg_reference_order!==null)return'QG_REFERENCE';
 if(r.rank.group==='PARTIAL_AXES')return'PARTIAL_AXES';if(r.rank.group==='CHECK_DATA')return'CHECK_DATA';return null;}
// Return order (2.1.4): by the period's value, high first, NA last, ties by ticker. value(row) = a number or null.
function returnOrder(rows,value){return rows.map(r=>({r,v:value(r)})).sort((a,b)=>(a.v===null)-(b.v===null)||(a.v!==null&&b.v!==null?b.v-a.v:0)||String(a.r.ticker).localeCompare(String(b.r.ticker))).map(x=>x.r);}
const helpers=Object.freeze({SORTS,sortSpec,oppositeSort,sortRows,sicOf,industryOf,filterClassified,populationOf,listOf,returnOrder});

/* ---------------------------------------------------------------- view state (RAM, this page load only) */
const V={list:'ALL',sort:'qgv',f:{industry:'',sic2:'',sic4:'',type:'',state:''},fav:false,period:'1D',ret:false,
 preview:false,profile:null,gate:true,shown:STEP,panel:false,n:15};
const LISTS=[['ALL','전체'],['RANKED','QGV 종합 순위'],['QG_REFERENCE',null],['PARTIAL_AXES','일부 축만 가능'],['CHECK_DATA','자료 확인 필요']];
const PERIODS=['1D','5D','20D'],WAIT_PERIODS=['60D','120D','YTD','1Y'];
const STATES=['SOURCE_MISSING','STALE','PRICE_NEEDED','PARTIAL','NOT_APPLICABLE','IDENTITY_STOPPED','CALC_VERSION'];
const MODEL_STATUS={FEASIBLE:'16절 한도 아래 구성 가능',UNVERIFIED:'업종 묶음 미정 · 확인 불가',FAIL:'16절 한도 초과'};
const EXCLUDED=[['AXES_50','축 50%'],['VALUE_TRAP_GATE','가치 함정 관문'],['FINANCIAL_SAFETY','재무 안전 미달'],['FINANCIAL_SAFETY_NA','재무 안전 지표 NA'],['SUBGROUP_MAX_4','하위 묶음 상한']];

/* ---------------------------------------------------------------- small view parts */
let NF=null,DF=null,TF=null,SF=null;
const fmt=v=>(NF||(NF=new Intl.NumberFormat('ko-KR',{minimumFractionDigits:1,maximumFractionDigits:1}))).format(v);
const day=t=>{const d=Date.parse(t);return Number.isFinite(d)?(DF||(DF=new Intl.DateTimeFormat('ko-KR',{year:'numeric',month:'2-digit',day:'2-digit',timeZone:'UTC'}))).format(d):null;};
const clock=t=>{const d=Date.parse(t);return Number.isFinite(d)?(TF||(TF=new Intl.DateTimeFormat('ko-KR',{hour:'2-digit',minute:'2-digit',hour12:false}))).format(d):null;};
// Date and time in UTC (the score file's refresh time, DC-22): the publication runs on a UTC schedule.
const stamp=t=>{const d=Date.parse(t);return Number.isFinite(d)?(SF||(SF=new Intl.DateTimeFormat('ko-KR',{year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false,timeZone:'UTC'}))).format(d)+' UTC':null;};
const pct2=v=>(ok(v)?v.toFixed(2):'NA');
const QS=()=>window.QgvScores;
const text=c=>I.qgv.reasonText(c);
// The words of a code: the layer's text when QgvScores.REASON or qgv.js knows it, else this place's fixed Korean fallback (never
// the generic text that prints the code). The code itself goes to data-na / data-reason only.
function say(code,fallback){const S=QS();if(typeof code!=='string'||!code||!S)return fallback;if(Object.hasOwn(S.REASON,code))return text(code);const t=text(code);return t!==S.reasonText(code)?t:fallback;}
const errCode=e=>String(e&&e.message||e).split(' ')[0];
const naBox=(words,code,label='NA')=>h('details',{class:'na',dataset:{na:code||''}},h('summary',null,label),h('span',{class:'reason'},words));
const chip=(label,on,attrs={})=>h('button',{type:'button',class:'chip','aria-pressed':String(!!on),...attrs},label);
const wait=t=>h('span',{class:'chip wait'},t);
const hand=(...t)=>h('p',{class:'hand'},...t);
const red=(code,words,...more)=>h('p',{class:'hand err',dataset:{reason:code}},words,...more);
// DC-26 colour hooks: the Q·G·V columns take their axis tint; the source chip takes the mine mark only while the shown score is the
// one this device's engines compute (page.engine_v_source): never since the central V (DC-31: the device result is TARGET's only).
const AX=['q','g','v'],vsrcClass=pg=>'chip vsrc'+(pg.v_source===pg.engine_v_source?' mine':'');
const settingsLink=()=>h('a',{class:'lk',href:href('detail','settings')},'→ 세부: 설정·시트 연결');
const group=(label,...kids)=>h('div',{class:'scroll',role:'group','aria-label':label},...kids);

/* ---------------------------------------------------------------- the leaderboard */
function leaderboard(route,refs){
 const signal=route.signal,Q=I.qgv,D=I.data,P=I.prices,B=refs.bodies;
 const ctx={pg:null,names:null,model:null,ret:null,retGen:0,band:{err:null},tabs:{err:null,after:false},pub:{busy:false,result:null,err:null},preview:null,gen:0};
 let queued=false;
 const later=()=>{if(queued)return;queued=true;Promise.resolve().then(()=>{queued=false;if(!signal.aborted)draw();});};

 // ---- names, classification, prices
 const title=r=>{const N=ctx.names,ES=window.EntitySearch,rec=N?N.get(r.id)||(r.code?N.get(r.code):null):null;return ES?ES.companyTitle(rec,r.ticker,'ko-KR'):r.ticker;};
 const ps=()=>({[QGV2]:D.get(QGV2),[CLS]:D.get(CLS)});
 const ranks=()=>{const ur=P.universeRanks();return!!ur&&typeof ur==='object'&&ur.state==='READY'?ur:null;};
 const interests=()=>{const pf=I.store.prefs();if(!loaded(pf))return{state:'NOT_READY',ids:[]};if(pf.state==='INVALID'||!pf.value)return{state:'INVALID',ids:[]};return{state:pf.state,ids:[...pf.value.interests]};};
 const profiles=()=>{const w=I.store.weights();return loaded(w)&&w.state==='OK'&&w.value&&Array.isArray(w.value.profiles)?w.value.profiles:[];};
 const typeName=id=>{const T=window.TypeConfigDefaults,t=T&&Array.isArray(T.types)?T.types.find(x=>x.id===id):null;return t?t.name:null;};
 const typeOrder=()=>{const T=window.TypeConfigDefaults;return T&&Array.isArray(T.types)?T.types:[];};

 // ---- focus kept across repaints (controls are rebuilt; data-k names each one)
 const focusKey=()=>{const a=document.activeElement;return a&&a.dataset&&a.dataset.k&&refs.band.closest('main')&&refs.band.closest('main').contains(a)?a.dataset.k:null;};
 const refocus=k=>{if(!k)return;const m=refs.band.closest('main'),el=m?m.querySelector('[data-k="'+k+'"]'):null;if(el&&!el.disabled)el.focus({preventScroll:true});};
 const toTable=k=>h('button',{type:'button',class:'linkish',dataset:{k:'to-table-'+k},onclick:()=>{const c=document.querySelector('[data-lb-table] caption');if(c){c.scrollIntoView({block:'start'});c.focus({preventScroll:true});}}},'↑ 목록에서 보기');

 /* ---- the QGV band: three price buttons, one layer action per click (the event passed in the handler, synchronously) */
 const[bPrep,bLogin,bRead]=refs.buttons;
 function act(event,fn,box){let p;try{p=fn(event);}catch(e){box.err=errCode(e);later();return;}box.err=null;later();
  Promise.resolve(p).then(()=>{if(!signal.aborted){box.err=null;after(box);later();}},e=>{if(!signal.aborted){box.err=errCode(e);after(box);later();}});}
 const after=box=>{if(box===ctx.tabs){box.after=true;refreshReturns();}};
 bPrep.addEventListener('click',e=>act(e,ev=>P.prepare(ev),ctx.band),{signal});
 bLogin.addEventListener('click',e=>act(e,ev=>P.login(ev),ctx.band),{signal});
 bRead.addEventListener('click',e=>act(e,ev=>P.readUniverse(ev),ctx.band),{signal});
 for(const b of refs.nav.querySelectorAll('button[data-to]')){b.disabled=false;b.addEventListener('click',()=>{const t=document.getElementById('s-'+b.dataset.to);if(!t)return;t.setAttribute('tabindex','-1');t.scrollIntoView({block:'start'});t.focus({preventScroll:true});},{signal});}
 function paintBand(){
  const st=P.status();if(!loaded(st))return;const g=st.google;
  refs.conn.textContent=g&&g.connected?'로그인됨':g&&g.ready?'로그인 준비됨':'연결 전';refs.conn.classList.toggle('wait',!(g&&(g.connected||g.ready)));
  bPrep.disabled=false;bLogin.disabled=!(g&&g.ready);bRead.disabled=!(g&&g.connected&&st.universe_source.set);
  const lines=[],e=ctx.band.err;
  if(e)lines.push(red(e,say(e,'실행하지 못했습니다'),e==='UNIVERSE_SOURCE_NOT_SET'?[' ',settingsLink()]:null));
  if(st.universe_source.set===false&&e!=='UNIVERSE_SOURCE_NOT_SET')lines.push(red('UNIVERSE_SOURCE_NOT_SET',text('UNIVERSE_SOURCE_NOT_SET'),' ',settingsLink()));
  const fail=st.universe.failure;if(fail&&fail.code&&fail.code!==e)lines.push(red(fail.code,say(fail.code,'실행하지 못했습니다')));
  if(st.universe.state==='READY'&&clock(st.universe.read_at))lines.push(hand('읽은 뒤: 읽은 시각 ',clock(st.universe.read_at),' · RAM에만 · 새로고침하면 사라짐'));
  refs.status.replaceChildren(...lines);}
 function paintChips(pg){refs.chips.replaceChildren(...basis(pg),h('span',{class:vsrcClass(pg)},'V 출처: ',pg.v_source.ko),h('span',{class:'chip'},Q.rankLabel(pg)),...central(pg));}
 /* ---- the central V basis (DC-31): "공식 V · IEX 마지막 체결가 기준(공식 종가 아님)", the price basis day, the publication time, STALE
    past FRESH_SESSIONS completed New York sessions, a different calc_version, the last failed publication attempt, why there is
    no official V, and the IEX attribution with its terms link (IEX HIST terms clause 01, DC-29). The last publication stays shown.
    Times carry their date and zone (stamp: a STALE publication is days old); sessions that cannot be counted (basis day ahead of
    this device's clock, calendar past its end) say so instead of passing for fresh. */
 function central(pg){const b=pg.price_basis||{},a=b.attempt;
  return[h('span',{class:'chip',dataset:{centralBasis:b.publication_id||''}},b.label||pg.v_source.ko,' · 가격 기준일 ',b.price_basis_date||'NA',' · 게시 ',stamp(b.generated_at)||'NA'),
   b.reason?h('span',{class:'chip err',dataset:{na:b.reason}},text(b.reason)):null,
   b.stale===true?h('span',{class:'chip err',dataset:{centralState:'STALE'}},'STALE · 기준일 뒤 끝난 뉴욕 정규장 2회 초과 · 마지막 게시본 그대로'):null,
   b.publication_id&&b.stale===null?h('span',{class:'chip err',dataset:{centralState:'STALE_UNKNOWN'}},'STALE 판정 불가 · 기준일 뒤 정규장 수를 셀 수 없음 · 마지막 게시본 그대로'):null,
   b.calc_differs===true?h('span',{class:'chip err',dataset:{centralState:'CALC_DIFFERS'}},'계산 버전 다름 · 게시본 값 그대로'):null,
   a&&a.state!=='OK'?h('span',{class:'chip err',dataset:{centralAttempt:a.state}},'마지막 게시 시도 ',stamp(a.at)||'NA',' · ',say(a.reason,text(a.state))):null,
   b.attribution?h('span',{class:'chip',dataset:{attribution:''}},b.attribution.text,' ',h('a',{class:'lk',href:b.attribution.terms_url,target:'_blank',rel:'noopener noreferrer'},'IEX 약관')):null].filter(Boolean);}
 /* ---- the 기준 chips in every page state (DC-22, owner 2026-10-27): the score file's refresh time (its as_of, UTC), this tab's last
    check of the public files, the calc_version, a file past its stale_after_seconds, the last re-read's outcome, and the re-read
    button (public files only: IS2.data.refresh, kind PUBLIC_REFRESH, one action per click; the private gate never opens). */
 const basisOf=pg=>['점수 갱신 ',stamp(pg.as_of)||'없음',' · 계산 버전 ',pg.calc_version||'없음'];
 function basis(pg){
  const pub=D.publication(),raw=D.get(QGV2),ttl=raw&&ok(raw.stale_after_seconds)?raw.stale_after_seconds*1000:null,t=Date.parse(pg.as_of),b=ctx.pub;
  const stale=ttl!==null&&Number.isFinite(t)&&Date.now()>t+ttl,failed=!!b.err||b.result==='FAILED';
  return[h('span',{class:'chip',dataset:{basis:''}},'점수 갱신 ',stamp(pg.as_of)||'없음',' · 마지막 확인 ',clock(pub&&pub.checked_at)||'NA',' · 계산 버전 ',h('small',null,pg.calc_version||'없음')),
   stale?h('span',{class:'chip err',dataset:{basisState:'STALE'}},'STALE · 점수 파일 기한 지남'):null,
   b.busy?h('span',{class:'chip wait',dataset:{basisState:'REFRESHING'}},'갱신 중 · 이전 값 표시 중'):failed?h('span',{class:'chip err',dataset:{basisState:'FAILED'}},'갱신 실패 · 이전 값 유지')
    :b.result==='UNCHANGED'?h('span',{class:'chip',dataset:{basisState:'UNCHANGED'}},'새 게시본 없음'):b.result==='APPLIED'?h('span',{class:'chip',dataset:{basisState:'APPLIED'}},'새 게시본 적용'):null,
   h('button',{type:'button',class:'chip',disabled:b.busy,dataset:{k:'reread'},onclick:reread},'공개 자료 다시 읽기')].filter(Boolean);}
 function reread(event){const b=ctx.pub;let p;try{p=D.refresh(event);}catch(e){b.err=errCode(e);later();return;}b.busy=true;b.err=null;b.result=null;later();
  Promise.resolve(p).then(r=>{if(signal.aborted)return;b.busy=false;b.result=r;later();},e=>{if(signal.aborted)return;b.busy=false;b.err=errCode(e);later();});}

 /* ---- loading: the shared page (default profile), the names; late values dropped (signal, generation) */
 function reload(){const my=++ctx.gen;
  Promise.all([Q.page({signal}),D.static(NAMES).catch(()=>null)]).then(([pg,names])=>{if(signal.aborted||my!==ctx.gen)return;
   if(pg!==ctx.pg)ctx.preview=null;ctx.pg=pg;ctx.names=names;ctx.model=null;
   if(pg.state==='READY'){try{ctx.model=Q.model(pg);}catch(_){ctx.model=null;}refreshReturns();}
   draw();},
  e=>{if(signal.aborted||my!==ctx.gen||errCode(e)==='ABORTED')return;for(const b of Object.values(B))b.replaceChildren(h('p',{class:'na',dataset:{na:'PAGE_FAILED'}},'QGV 점수를 계산하지 못했습니다'));});}
 function refreshReturns(){const pg=ctx.pg;if(!pg||pg.state!=='READY')return;const my=++ctx.retGen;
  let p;try{p=P.periodReturns(V.period,pg.rows.map(r=>({id:r.id,ticker:r.ticker,code:r.code})));}catch(e){p=Promise.reject(e);}
  Promise.resolve(p).then(r=>{if(signal.aborted||my!==ctx.retGen)return;ctx.ret=r;later();},()=>{if(signal.aborted||my!==ctx.retGen)return;ctx.ret=null;later();});}

 /* ---- the view: Universe504 → list → filters → order → first rows */
 function previewOf(pg){
  const list=profiles(),p=list.find(x=>x.id===V.profile)||list[0];if(!V.preview||!p||pg.state!=='READY')return null;
  const key=p.id+'|'+p.version+'|'+V.gate;if(ctx.preview&&ctx.preview.key===key&&ctx.preview.pg===pg)return ctx.preview;
  let out;try{out=Q.preview(pg,p.weights,{typeWeights:p.type_weights!==false,gate:V.gate});}catch(e){out={state:'INVALID',reason:errCode(e),rows:[]};}
  ctx.preview={key,pg,p,out};return ctx.preview;}
 function view(){
  // Universe504 rows only (owner 2026-10-27, DC-24): the layer's TARGET v0 catalog rows (in the Universe or outside it) are not
  // a QGV population, scope or filter here; TARGET v0 has nothing to do with QGV.
  const pg=ctx.pg,pv=previewOf(pg),base=pv?pv.out.rows:null,cls=ps();
  const scoped=base?base.filter(r=>r.scope==='UNIVERSE'):Q.rows(pg,{scope:'UNIVERSE'});
  const list=pv?'ALL':V.list,listed=list==='ALL'?scoped:scoped.filter(r=>listOf(r)===list);
  const fav=interests(),f=V.f,any=!!(f.industry||f.sic2||f.sic4||f.type||f.state||V.fav);
  const byId=new Map(filterClassified(listed.map(r=>({company_id:r.id,row:r})),cls,f).map(x=>[x.company_id,x.row]));
  const filtered=listed.filter(r=>byId.has(r.id)&&(!f.type||(f.type==='UNCLASSIFIED'?!r.types.selected.length&&r.types.reason==='NO_RECOGNIZED_TYPE':f.type==='NOT_AVAILABLE'?!r.types.selected.length&&r.types.reason!=='NO_RECOGNIZED_TYPE':r.types.selected.includes(f.type)))
   &&(!f.state||r.coverage.states.includes(f.state))&&(!V.fav||fav.ids.includes(r.id)));
  const ur=ranks(),m3=new Map(),cap=r=>{if(!ur)return null;if(!m3.has(r.id))m3.set(r.id,P.rankFor({company_id:r.id,ticker:r.ticker}));const e=m3.get(r.id);return e&&Number.isInteger(e.rank)?e.rank:null;};
  if(sortSpec(V.sort)[1]==='cap'&&!ur||V.sort==='favorites'&&!fav.ids.length||!SORTS.some(s=>s[0]===V.sort))V.sort='qgv';
  const ret=ctx.ret&&ctx.ret.state==='READY'?ctx.ret:null,byRet=V.ret&&!!ret;
  const rv=r=>{const x=ret&&Object.hasOwn(ret.rows,r.id)?ret.rows[r.id]:null;return x&&x.state==='OK'?x.value:null;};
  const ordered=byRet?returnOrder(filtered,rv):sortRows(filtered,V.sort,{cap,title,interests:fav.ids,rank:pv?r=>r.rank.personal:r=>r.rank.official});
  const official=Q.rows(pg,{scope:'UNIVERSE'});
  return{byRet,pg,pv,scoped,official,list,listed,filtered,ordered,drawn:ordered.slice(0,V.shown),any,fav,ur,m3,cap,ret,cls,of:pg.rows.length?pg.rows[0].rank.of:null};}

 /* ---- draw everything (each control has data-k so the focus comes back after a repaint) */
 function draw(){
  paintBand();const pg=ctx.pg;if(!pg)return;const k=focusKey();
  if(pg.state!=='READY'){stateCards(pg);refocus(k);return;}
  paintChips(pg);const v=view();
  const fill=(fn,list)=>B[fn].replaceChildren(...list.flat(Infinity).filter(x=>x!==null&&x!==undefined&&x!==false));
  fill('2.1.1',block1(v));fill('2.1.2',block2(v));fill('2.1.3',block3(v));fill('2.1.4',block4(v));fill('2.1.5',block5(v));fill('2.1.6',block6(v));fill('2.1.7',block7(v));
  refocus(k);}
 const set=(fn)=>()=>{fn();draw();};
 function stateCards(pg){
  const t={NO_DATA:'화면 상태 · 미게시',READ_FAILED:'화면 상태 · 읽기 실패',DATA_FORMAT_NEWER:'화면 상태 · 새 형식'}[pg.state]||'화면 상태 · 미게시';
  refs.chips.replaceChildren(...basis(pg),h('span',{class:vsrcClass(pg)},'V 출처: ',pg.v_source.ko),h('span',{class:'chip'},Q.rankLabel(pg)),...central(pg));
  // The character once, on the first block (2.1.1); the other six cards repeat the words only.
  Object.values(B).forEach((b,i)=>b.replaceChildren(h('div',{class:'sk state-card',dataset:{na:pg.reason||pg.state,pageState:pg.state}},i?null:mascot(pg.state==='NO_DATA'?'plain':'alarm'),h('b',null,t),h('span',null,text(pg.reason)),
   pg.state==='DATA_FORMAT_NEWER'?h('button',{type:'button',class:'btn',dataset:{k:'reload'},onclick:()=>location.reload()},'새로고침'):null)));}

 /* ---- 2.1.1 평가 대상과 목록: Universe504 only (DC-24: no TARGET v0 scope, box or column), counts, the one table */
 function block1(v){
  const pg=v.pg,E=populationOf(v.cls);
  const scope=group('보기 범위',h('span',{class:'chip on',dataset:{scope:'UNIVERSE'}},'Universe504 전체 · 고정 504코드'));
  const count=h('p',{class:'count',dataset:{lbCount:''}},'평가: Universe504 중 점수 행 ',E===null?naBox(text('SEC_QGV2_NOT_AVAILABLE'),'SEC_QGV2_NOT_AVAILABLE'):h('b',null,String(E)));
  // A READY page with a reason (V2_SCORES_NOT_AVAILABLE …): the reason above the table, the rows still draw.
  const why=pg.reason?h('p',{class:'reason',dataset:{na:pg.reason,pageReason:''}},say(pg.reason,'QGV 점수를 모두 계산하지 못했습니다')):null;
  return[scope,count,why,h('div',{class:'lb-grid'},table(v))];}
 const LIST_NAME=id=>id==='QG_REFERENCE'?(QS()?QS().QG_REFERENCE_LABEL[0]:'QG 참고 목록'):(LISTS.find(l=>l[0]===id)||LISTS[0])[1];
 function rankHead(v){if(!v.pv)return Q.rankLabel(v.pg);const S=QS(),o=v.pv.out;return Q.rankLabel(o)+' · '+(o.v_weight_zero?S.PERSONAL_V0_LABEL[0]:S.PERSONAL_LABEL[0]);}
 function table(v){
  const pg=v.pg,[,key,dir]=sortSpec(V.sort),active=v.byRet?'ret':key==='name'?'name':['qgv','q','g','v','asof','cap'].includes(key)?key:null;
  const ariaSort=col=>(col!==active?null:col==='ret'||col==='cap'?(v.byRet||dir===-1?'descending':'ascending'):dir===-1?'descending':'ascending');
  const arrow=col=>(col===active?(ariaSort(col)==='descending'?' ↓':' ↑'):'');
  const headBtn=(col,label,onclick,disabled=false)=>h('button',{type:'button',class:'th-btn',disabled,dataset:{k:'th-'+col,col},onclick},label,h('span',{class:'arrow '+(col==='q'||col==='g'||col==='v'?col+'-text':'')},arrow(col)));
  const pick=(desc,asc)=>set(()=>{V.ret=false;V.sort=V.sort===desc?asc:desc;});
  const th=(col,content,sub,pc)=>h('th',{scope:'col',class:(pc?'pc-col ':'')+(col&&col===active?'on':'')+(AX.includes(col)?' ax-'+col:''),'aria-sort':col?ariaSort(col):null},content,sub?h('small',{class:'sub'},sub):null);
  const vf=v.list==='RANKED',cols=[
   th(null,'순위',rankHead(v)),th('name',headBtn('name','기업',set(()=>{V.ret=false;V.sort='name';}))),th(null,'SIC',null,true),th(null,'유형',null,true),
   th('qgv',headBtn('qgv','QGV',pick('qgv','qgv-asc'))),th('q',headBtn('q','Q',pick('q-desc','q-asc')),null,true),th('g',headBtn('g','G',pick('g-desc','g-asc')),null,true),
   th('v',headBtn('v','V',pick('v-desc','v-asc')),pg.v_source.ko,true),th('cap',headBtn('cap','M3',pick('cap-desc','cap-asc'),!v.ur),null,true),
   th('ret',headBtn('ret','수익률 '+V.period,set(()=>{V.ret=!v.byRet;}),!v.ret),text('PRICE_BASIS_CONTINUITY_UNCONFIRMED')),
   th('asof',headBtn('asof','자료 기준일',pick('asof-desc','asof-asc')),'수집 시각 · 공개 점수 파일',true),
   vf?th(null,'V 요인',null,true):null].filter(Boolean);
  const dirText=v.byRet?'내림차순':oppositeSort(V.sort)===null?'한 방향':dir===-1?'내림차순':'오름차순';
  const sortText=v.byRet?'수익률 '+V.period+' 높은 순 · QGV 순위와 별개':sortSpec(V.sort)[3];
  const caption=h('caption',{tabindex:'-1'},LIST_NAME(v.list),' · ',rankHead(v),' · 정렬: ',sortText,' · ',dirText,' · 표시 ',String(v.drawn.length),'개');
  let body;
  if(v.pv&&v.pv.out.state==='INVALID')body=[emptyRow(cols.length,h('p',{class:'na',dataset:{na:v.pv.out.reason||''}},say(v.pv.out.reason,'내 설정으로 계산하지 못했습니다')))];
  else if(v.list==='RANKED'&&!v.listed.length)body=[emptyRow(cols.length,noRanking())];
  else if(!v.drawn.length)body=[emptyRow(cols.length,v.any?h('div',{class:'empty',dataset:{empty:'FILTER'}},h('p',null,'일치하는 기업이 없습니다'),
   h('button',{type:'button',class:'btn',dataset:{k:'clear-filters'},onclick:set(clearFilters)},'필터 모두 풀기')):h('p',{class:'empty',dataset:{empty:'VIEW'}},'이 보기에 해당하는 기업이 없습니다'))];
  else body=v.drawn.map(r=>row(r,v,active));
  const rest=v.ordered.length-v.drawn.length;
  return h('div',{class:'lb-main'},h('div',{class:'tbl-wrap'},h('table',{class:'tbl lb-tbl',dataset:{lbTable:'',list:v.list,scope:'UNIVERSE',sort:v.byRet?'ret':V.sort}},caption,h('thead',null,h('tr',null,...cols)),h('tbody',null,...body))),
   rest>0?h('button',{type:'button',class:'btn',dataset:{k:'more'},onclick:set(()=>{V.shown+=STEP;})},'더 보기 · 50개 (남은 ',String(rest),'개)'):null,
   h('p',{class:'reason'},'\'참고 n\'은 순위 아님'),
   v.ur?h('p',{class:'reason',dataset:{m3Coverage:''}},'M3 · 내 기기 기준 · v0 · ',v.ur.status==='COMPLETE'?'전체':'부분',' · 확인 ',Number.isInteger(v.ur.verified_count)?String(v.ur.verified_count):'NA'):null);}
 const emptyRow=(n,content)=>h('tr',{class:'empty-row'},h('td',{colspan:String(n)},content));
 function rankCell(r,v){const n=v.pv?r.rank.personal:r.rank.official;if(Number.isInteger(n))return String(n);
  if(r.rank.qg_reference_order!==null&&!(r.scope==='OUTSIDE_UNIVERSE'||r.reference_only))return'참고 '+r.rank.qg_reference_order;
  return naBox(say(r.na_reason.rank,'순위 없음'),r.na_reason.rank,'—');}
 function score(r,k){return ok(r.score[k])?fmt(r.score[k]):naBox(text(r.na_reason[k]),r.na_reason[k]);}
 function types(r){const names=typeOrder().filter(t=>r.types.selected.includes(t.id)).map(t=>t.name);if(names.length)return names.join(' · ');
  if(!r.types.selected.length&&r.types.reason==='NO_RECOGNIZED_TYPE')return'미분류';return naBox(say(r.types.reason,'유형 자료 없음'),r.types.reason||'TYPE_NOT_AVAILABLE');}
 function m3(r,v){
  // Before a read: UNIVERSE_NOT_READ (rankFor not called); a read whose rank index is not READY: the index's own reason.
  if(!v.ur){const ur=P.universeRanks(),c=ur&&typeof ur==='object'&&Array.isArray(ur.reason_codes)&&ur.reason_codes[0]&&ur.reason_codes[0]!=='UNIVERSE_NOT_READ'?ur.reason_codes[0]:null;
   return c?h('span',{class:'dash',dataset:{reason:c}},'M3 — · ',say(c,'M3 순위 없음')):h('span',{class:'dash',dataset:{reason:'UNIVERSE_NOT_READ'}},'M3 — · ',text('UNIVERSE_NOT_READ'));}
  if(!v.m3.has(r.id))v.m3.set(r.id,P.rankFor({company_id:r.id,ticker:r.ticker}));const e=v.m3.get(r.id);
  if(e&&Number.isInteger(e.rank))return[h('span',{dataset:{ramPrice:''}},'#',String(e.rank),e.quality==='MISMATCH'?' (불일치)':'',e.group_id?' · 종류 합산':''),h('small',{class:'reason'},' 내 기기 기준 · v0 · 공식 순위 아님')];
  const c=e&&Array.isArray(e.reason_codes)?e.reason_codes[0]:null;return h('span',{class:'dash',dataset:{reason:c||''}},'M3 — · ',say(c,'M3 순위 없음'));}
 function ret(r,v){
  const x=ctx.ret&&Object.hasOwn(ctx.ret.rows,r.id)?ctx.ret.rows[r.id]:null;
  if(!x||x.state==='NA'&&x.reason==='PRICE_TABS_NOT_LOADED')return h('span',{class:'reason',dataset:{reason:'PRICE_TABS_NOT_LOADED'}},'— ',text('PRICE_TABS_NOT_LOADED'));
  if(x.state!=='OK'){const stop=x.reason==='PRICE_IDENTITY_CONFLICT'||x.reason==='IDENTITY_CONFLICT_WITHDRAWN';
   return h('span',{class:'reason',dataset:{reason:x.reason}},stop?['— ',text(x.reason)]:['— 미산출 · 근거: ',say(x.reason,'미산출')]);}
  const p=Math.round(x.value*1000)/10,cls=p>0?'ret up':p<0?'ret down':'ret',s=(p>0?'+':p<0?'−':'')+fmt(Math.abs(p))+'%';
  return[h('span',{class:cls,dataset:{ramPrice:''}},s),' ',h('small',{class:'note',dataset:{reason:'PRICE_BASIS_CONTINUITY_UNCONFIRMED'}},'분할 미확인')];}
 function row(r,v,active){
  const sic=sicOf({company_id:r.id},v.cls),ty=types(r),on=c=>(c===active?'on':''),pc=c=>'pc-col '+on(c);
  const sub=[['Q','q'],['G','g'],['V','v']].map(([a,k])=>h(k===active?'b':'span',{class:k===active?k+'-text':''},a,' ',ok(r.score[k])?fmt(r.score[k]):'NA'));
  const why=['total','q','g','v','rank'].filter(k=>r.na_reason[k]).map(k=>h('li',null,{total:'QGV',q:'Q',g:'G',v:'V',rank:'순위'}[k],' · ',text(r.na_reason[k])));
  const company=h('td',{class:on('name')},h('a',{href:href('company',r.id),class:'co'},title(r)),title(r).includes(r.ticker)?null:h('span',{class:'reason'},' ',r.ticker),
   h('span',{class:'m-only sub-line'},sic||'SIC NA',' · ',typeof ty==='string'?ty:'유형 NA'),
   h('span',{class:'m-only sub-line'},...sub.flatMap((x,i)=>[i?' · ':'',x]),' · ',m3(r,v)),
   why.length?h('details',{class:'m-only why'},h('summary',null,'사유 ▸'),h('ul',null,...why)):null);
  let qgvCell=score(r,'total'),vCell=score(r,'v');
  if(v.list==='QG_REFERENCE'&&!ok(r.score.v))vCell=h('span',{class:'reason'},'— 근거: ',text(r.na_reason.v));
  if(v.list==='CHECK_DATA'&&!ok(r.score.total))qgvCell=h('span',{class:'reason'},'어느 축도 산출 안 됨 → 근거: ',text(r.na_reason.total));
  if(v.list==='PARTIAL_AXES'&&!ok(r.score.total))qgvCell=h('span',{class:'reason'},'종합 없음 · 순위 없음 · ',text(r.na_reason.total));
  const vf=r.coverage.v_factors,miss=(vf.missing||[]).map(f=>{const L=window.DeviceProfiles&&window.DeviceProfiles.FACTOR_LABELS;return L&&L[f]?L[f][0]:'이름 없는 요인';});
  return h('tr',{dataset:{row:r.id}},h('td',{class:'rk',dataset:{cell:'rank'}},rankCell(r,v)),company,
   h('td',{class:'pc-col',dataset:{cell:'sic'}},sic||naBox('분류 자료 없음','SIC_NOT_AVAILABLE')),h('td',{class:'pc-col',dataset:{cell:'type'}},ty),
   h('td',{class:'num qgv '+on('qgv'),dataset:{cell:'qgv'}},qgvCell),h('td',{class:'num ax-q '+pc('q'),dataset:{cell:'q'}},score(r,'q')),h('td',{class:'num ax-g '+pc('g'),dataset:{cell:'g'}},score(r,'g')),
   h('td',{class:'num ax-v '+pc('v'),dataset:{cell:'v'}},vCell),h('td',{class:pc('cap'),dataset:{cell:'m3'}},m3(r,v)),h('td',{class:on('ret'),dataset:{cell:'ret'}},ret(r,v)),
   h('td',{class:pc('asof'),dataset:{cell:'asof'}},day(r.acquired_at)||naBox('자료 기준일 없음','ACQUIRED_AT_NOT_AVAILABLE')),
   v.list==='RANKED'?h('td',{class:'pc-col',dataset:{cell:'vfactors'}},String(vf.n),'/',String(vf.total),miss.length?h('details',{class:'na'},h('summary',null,'빠진 요인'),h('span',{class:'reason'},miss.join(' · '))):null):null);}
 // The 2.1.5 empty state of 종합 순위: no official rank without a central V publication (no device price can give one, DC-31).
 const noRankWhy=()=>{const b=ctx.pg&&ctx.pg.price_basis;return b&&b.reason?text(b.reason):text('OFFICIAL_NOT_PUBLISHED');};
 function noRanking(){return h('div',{class:'sk empty',dataset:{empty:'NO_RANKING'}},mascot('plain'),h('p',null,'QGV 순위 없음'),h('p',{class:'reason'},noRankWhy()),
  h('button',{type:'button',class:'btn',dataset:{k:'qg-list'},onclick:set(()=>{V.list='QG_REFERENCE';V.shown=STEP;})},'QG 참고 목록 보기'));}

 /* ---- 2.1.2 순위와 정렬 */
 function block2(v){
  const S=QS(),fav=v.fav,[,,dir]=sortSpec(V.sort),opp=oppositeSort(V.sort);
  const sel=h('select',{id:'lb-sort',dataset:{k:'sort'},onchange:e=>{V.ret=false;V.sort=e.target.value;draw();}},
   ...SORTS.map(([id,key,,label])=>{const capOff=key==='cap'&&!v.ur,favOff=key==='favorites'&&!fav.ids.length;
    return h('option',{value:id,selected:id===V.sort,disabled:capOff||favOff},label,capOff?' (이 기기 가격 시트 읽은 뒤)':'');}));
  const toggle=h('button',{type:'button',class:'chip dir','aria-pressed':String(opp!==null&&dir===-1),disabled:opp===null,'aria-label':dir===-1?'내림차순':'오름차순',dataset:{k:'dir'},
   onclick:set(()=>{const o=oppositeSort(V.sort);if(o){V.ret=false;V.sort=o;}})},dir===-1?'↓ 내림':'↑ 오름',h('span',{class:'pc-only'},'차순'));
  const reset=h('button',{type:'button',class:'btn reset',dataset:{k:'reset'},onclick:set(()=>{V.ret=false;V.sort='qgv';})},'기본 정렬(QGV 높은 순)');
  const of=Number.isInteger(v.of)?String(v.of):'NA',E=populationOf(v.cls),M=ctx.model,L=S.POPULATION_LABEL;
  const eligible=M?['N20 선정에서 살펴본 ',String(M.checked),'행 · 자격 제외 ',String(M.excluded.AXES_50+M.excluded.VALUE_TRAP_GATE+M.excluded.FINANCIAL_SAFETY+M.excluded.FINANCIAL_SAFETY_NA),
   ' · 한도로 건너뜀 ',String(M.excluded.SUBGROUP_MAX_4+M.sets.N20.skipped.SECTOR_GROUP_MAX_40),' · → 1.1.7']:['순위가 없어 살피지 않음'];
  const box=(k,label,...t)=>h('div',{class:'sk pop-box',dataset:{pop:k,...(k==='ELIGIBLE'&&!M?{na:'NO_RANKED_ROWS'}:{})}},h('b',null,label),h('span',null,...t));
  return[h('div',{class:'sort-row'},h('label',{for:'lb-sort'},'정렬'),sel,toggle,reset),opp===null?h('p',{class:'reason',dataset:{oneWay:''}},'이 정렬은 한 방향만'):null,
   h('p',{class:'sk status-line',dataset:{sortStatus:''}},'정렬: ',sortSpec(V.sort)[3],' · ',opp===null?'한 방향':dir===-1?'내림차순':'오름차순',' · 순위 모집단: V 포함 종합점수 ',of,'개'),
   h('div',{class:'pop'},box('EVALUATION',L.EVALUATION[0],'Universe504 점수 행 ',E===null?'NA':String(E)),box('RANK',L.RANK[0],'종합점수 + V 있는 행 ',of),
    box('ELIGIBLE',L.ELIGIBLE[0],...eligible),box('FILTER',L.FILTER[0],'표시 ',String(v.drawn.length),' · 순위 다시 매기지 않음')),
   h('div',{class:'hand rules'},h('p',null,'· NA는 오름·내림 모두 맨 뒤'),h('p',null,'· 동점: QGV는 티커 순(순위 순서), 시총은 기업 ID 순'),h('p',null,'· 정렬은 줄 순서만 바꿈 · 순위 번호는 그대로')),toTable('sort')];}

 /* ---- 2.1.3 분류와 필터 */
 function clearFilters(){V.f={industry:'',sic2:'',sic4:'',type:'',state:''};V.fav=false;}
 function block3(v){
  const cls=v.cls,cfg=get(cls[CLS],'data','industry_config','groups'),groups=Array.isArray(cfg)?cfg:null,ids=v.pg.rows.map(r=>({company_id:r.id}));
  const sics=digits=>[...new Set(ids.map(c=>sicOf(c,cls)).filter(Boolean).map(s=>s.slice(0,digits)))].sort();
  const lines=[];
  const select=(key,label,options,disabled=false)=>{const chosen=V.f[key],opts=[['','전체'],...options];
   if(chosen&&!opts.some(o=>o[0]===chosen)){opts.push([chosen,(key==='sic2'||key==='sic4'?chosen+' · ':'선택한 값 · ')+'새 게시본에 없음',true]);lines.push(h('p',{class:'reason',dataset:{kept:key}},key==='industry'?'선택한 업종군이 새 게시본에 없음 · 선택은 그대로 남김':'선택한 분류가 새 게시본에 없음 · 선택은 그대로 남김'));}
   const id='lb-f-'+key;
   return h('div',{class:'sk fcard',dataset:{filter:key}},h('label',{for:id},label),h('select',{id,disabled,dataset:{k:'f-'+key},onchange:e=>{V.f={...V.f,[key]:e.target.value};V.shown=STEP;draw();}},
    ...opts.map(([val,name,gone])=>h('option',{value:val,selected:val===chosen,disabled:!!gone},name))),
    key==='sic4'?h('span',{class:'hand'},'SIC 이름은 공개 자료에 없어 코드만'):null,key==='industry'&&!groups?h('p',{class:'reason',dataset:{na:'INDUSTRY_CONFIG_NOT_AVAILABLE'}},'업종군 설정을 공개 파일에서 읽지 못해 고를 수 없습니다'):null);};
  const unresolved=t=>t.rule&&t.rule.kind==='unresolved';
  const cards=[select('industry','① 산업 (SIC 업종군 v0)',[...(groups||[]).map(g=>[g.id,g.name]),['NOT_AVAILABLE','업종군 자료 없음']],!groups),
   select('sic2','② SIC 2자리',[...sics(2).map(c=>[c,c]),['NOT_AVAILABLE','분류 자료 없음']]),select('sic4','③ SIC 4자리',[...sics(4).map(c=>[c,c]),['NOT_AVAILABLE','분류 자료 없음']]),
   select('type','④ 기업 유형',[...typeOrder().map(t=>[t.id,t.name+(unresolved(t)?' · 규칙 결정 대기':'')]),['UNCLASSIFIED','미분류'],['NOT_AVAILABLE','유형 자료 없음']]),
   select('state','⑤ 자료 상태',STATES.map(s=>[s,QS().stateText(s)+(s==='NOT_APPLICABLE'?' · 결정 대기 (FIN-NA-CODE)':'')]))];
  const fav=v.fav,favOff=!fav.ids.length,favWhy=fav.state==='INVALID'?'저장된 관심 기업 자료를 읽을 수 없습니다 · 원본은 그대로 둠':'관심 기업 없음 · ★는 기업 화면에서';
  if(favOff&&V.fav)V.fav=false;
  const check=(k,label,on,disabled,onchange)=>h('label',{class:'check'},h('input',{type:'checkbox',checked:on,disabled,dataset:{k},onchange}),label);
  const panelOpen=V.panel;
  return[h('div',{class:'filter-head'},h('button',{type:'button',class:'chip m-only','aria-expanded':String(panelOpen),'aria-controls':'lb-filters',dataset:{k:'panel'},onclick:set(()=>{V.panel=!V.panel;})},'필터 ▾'),
    wait('산업 단위 · 결정 대기 (IA-5)')),
   h('div',{id:'lb-filters',class:'lb-filters'+(panelOpen?' open':'')},...cards),...lines,
   h('div',{class:'checks'},check('fav','관심만',V.fav,favOff,e=>{V.fav=e.target.checked;draw();}),favOff?h('span',{class:'reason',dataset:{favorites:fav.state}},favWhy):null),
   h('p',{class:'sk status-line',role:'status',dataset:{filterCount:''}},'표시 ',String(v.drawn.length),'개 · 순위 기준 ',Number.isInteger(v.of)?String(v.of):'NA','개 중'),
   hand('필터는 줄만 숨김 · 순위·점수·후보 그대로'),hand('분류 자료 없음은 0이나 다른 분류로 채우지 않음'),
   v.any?h('button',{type:'button',class:'btn',dataset:{k:'clear-filters-2'},onclick:set(clearFilters)},'필터 모두 풀기'):null,toTable('filters')];}

 /* ---- 2.1.4 기간별 수익률 (prices only after a click, RAM only) */
 function block4(v){
  const st=P.status(),s=loaded(st)?st.store:null,g=loaded(st)?st.google:null,states=['READY','LOADING','ERROR'];
  const usable=loaded(st)&&g&&g.connected&&st.sheet.set&&s&&states.includes(s.state);
  let why=null;
  if(!usable){if(!s||s.state==='OFF')why=['PRICE_TABS_OFF',true];else if(!(g&&g.connected)||s.state==='AUTH_REQUIRED')why=['AUTH_REQUIRED',false];else why=['SHEET_NOT_CONNECTED',true];}
  const load=h('button',{type:'button',class:'btn mine',disabled:!usable,dataset:{k:'load-tabs'},onclick:e=>act(e,ev=>P.loadTabs(ev),ctx.tabs)},'수익률용 가격 불러오기 · 이 기기에서만');
  const lines=[];
  if(s&&s.state==='ERROR')lines.push(red((s.reason_codes||[])[0]||'ERROR',say((s.reason_codes||[])[0],'가격 탭을 읽지 못했습니다')));
  if(ctx.tabs.err)lines.push(red(ctx.tabs.err,say(ctx.tabs.err,'실행하지 못했습니다')));
  if(ctx.tabs.after&&!(s&&s.tabs_loaded&&s.tabs_loaded.daily))lines.push(h('p',{class:'reason',dataset:{reason:'PRICE_TABS_NOT_LOADED'}},text('PRICE_TABS_NOT_LOADED'),s&&s.state==='ERROR'?[' · ',say((s.reason_codes||[])[0],'가격 탭을 읽지 못했습니다')]:''));
  return[group('수익률 기간',...PERIODS.map(p=>chip(p,V.period===p,{dataset:{k:'period-'+p,period:p},onclick:()=>{if(V.period===p)return;V.period=p;ctx.ret=null;refreshReturns();draw();}})),
    ...WAIT_PERIODS.map(p=>h('button',{type:'button',class:'chip wait',disabled:true,dataset:{period:p}},p+' · 결정 대기 (IA-12)'))),
   h('p',{class:'reason'},'YTD·1Y: IA-12 결정 대기 · 가격 조정·배당 기준 정한 뒤'),
   hand('분할·배당 조정 없는 종가로 계산 · 분할이 낀 기간은 틀릴 수 있음 (TA-G1 결정 대기)'),
   ...lines,h('div',{class:'load-row'},load,why?h('span',{class:'reason',dataset:{reason:why[0]}},'연결 전에는 꺼짐 · ',text(why[0]),why[1]?[' ',settingsLink()]:null):null),
   hand('누른 뒤: 이 기기 RAM에만 · 새로고침하면 사라짐 · 공개·저장 안 함'),
   h('div',{class:'ret-row'},h('button',{type:'button',class:'chip','aria-pressed':String(v.byRet),disabled:!v.ret,dataset:{k:'ret-sort'},onclick:set(()=>{V.ret=!v.byRet;})},'수익률 순으로 보기'),
    v.byRet?h('span',{class:'reason',dataset:{retStatus:''}},'QGV 순위와 별개 · 순위 번호 그대로 · 분할 미확인'):null,h('span',{class:'hand'},'값이 없으면 0으로 채우지 않음')),toTable('returns')];}

 /* ---- 2.1.5 산출 상태별 목록 */
 function block5(v){
  const counts={ALL:v.official.length};for(const r of v.official){const l=listOf(r);if(l)counts[l]=(Object.hasOwn(counts,l)?counts[l]:0)+1;}
  const locked=!!v.pv;
  return[group('산출 상태별 목록',...LISTS.map(([id])=>chip(LIST_NAME(id)+' '+String(Object.hasOwn(counts,id)?counts[id]:0),v.list===id,
    {disabled:locked&&id!=='ALL',dataset:{k:'list-'+id,list:id},onclick:set(()=>{V.list=id;V.shown=STEP;})}))),
   v.pv?h('p',{class:'reason',dataset:{listLock:'PREVIEW'}},'산출 상태별 목록은 공식 가중치 결과 기준'):null,
   hand('후보 자격 없는 결과는 순위에 섞지 않음 · 0점 아님 · 순위 번호 없음'),toTable('lists')];}

 /* ---- 2.1.6 공식 결과와 개인 결과 */
 function block6(v){
  const S=QS(),pg=v.pg,list=profiles(),canPreview=list.length>0&&pg.state==='READY';if(!canPreview&&V.preview)V.preview=false;
  const pv=v.pv,p=pv?pv.p:null;
  const x=S.provenance({kind:'QGV',profile:pv?{weights:p.weights,gate:V.gate,id:pv.out.profile_id}:{preset:pg.preset,gate:pg.gate,id:pg.profile_id},central:!pv});
  const weightWord=x.weights==='OFFICIAL'?'공식 가중치':x.setting.includes('WEIGHTS')?'개인 가중치':'개인 프리셋',where=x.source==='DEVICE_COMPUTED'?'기기 계산 · 게시 요인 점수로':'중앙 게시';
  const turn=on=>set(()=>{if(on===V.preview)return;V.preview=on;ctx.preview=null;if(on){const q=list.find(y=>y.id===V.profile)||list[0];V.profile=q.id;V.gate=q.gate===false?false:true;}});
  const badge=(k,label,word)=>h('div',{class:'sk badge',dataset:{badge:k}},h('b',null,label),h('span',{class:'hl'},word));
  const b=pg.price_basis,time=['가격 기준일 ',b.price_basis_date||'NA',' · 게시 ',stamp(b.generated_at)||'NA',b.stale===true?' · STALE':b.publication_id&&b.stale===null?' · STALE 판정 불가':''];
  return[group('결과 보기',chip('공식 가중치 결과',!V.preview,{dataset:{k:'mode-official'},onclick:turn(false)}),chip('내 설정 결과(미리보기)',V.preview,{disabled:!canPreview,dataset:{k:'mode-preview'},onclick:turn(true)})),
   canPreview?null:h('p',{class:'reason',dataset:{previewOff:''}},'저장된 내 설정이 없습니다 · 1.2 가중치 화면에서 만듭니다(다음 단계)'),
   V.preview&&list.length>1?h('div',{class:'sort-row'},h('label',{for:'lb-profile'},'내 설정'),h('select',{id:'lb-profile',dataset:{k:'profile'},onchange:e=>{const q=list.find(y=>y.id===e.target.value);if(q){V.profile=q.id;V.gate=q.gate===false?false:true;ctx.preview=null;}draw();}},
    ...list.map(q=>h('option',{value:q.id,selected:p&&q.id===p.id},q.name)))):null,
   h('label',{class:'check'},h('input',{type:'checkbox',checked:V.preview?V.gate:true,disabled:!V.preview,dataset:{k:'gate'},onchange:e=>{V.gate=e.target.checked;ctx.preview=null;draw();}}),'가치 함정 관문 (기본 켬)'),
   V.preview?null:h('p',{class:'reason'},'공식 결과는 관문 켬 고정'),
   h('div',{class:'badges',dataset:{badges:''},...S.provenanceAttrs(x)},badge('weights','가중치',weightWord),badge('prices','가격',pv?'가격 없음 · 게시 요인 점수':b.label||pg.v_source.ko),badge('where','계산 장소',where),badge('vsource','V 출처',pg.v_source.ko)),
   V.preview&&V.gate===false?h('p',{class:'reason',dataset:{gateOff:''}},'관문 끔'):null,
   V.preview&&pv?h('p',{class:'reason',dataset:{na:pv.out.weight_stages.reason}},text(pv.out.weight_stages.reason)):null,
   V.preview&&pv&&pv.out.state==='INVALID'?h('p',{class:'na',dataset:{na:pv.out.reason||''}},say(pv.out.reason,'내 설정으로 계산하지 못했습니다')):null,
   h('div',{class:'cards'},h('div',{class:'sk card-now'},h('b',null,'지금'),h('span',null,pg.v_source.ko,' · ',where),h('span',{class:'boxed'},Q.rankLabel(pg)),h('span',null,...time)),
    h('div',{class:'sk'},h('b',null,'내 설정 결과(미리보기)를 켜면'),h('span',{class:'boxed'},S.PERSONAL_LABEL[0]),h('span',null,'V 비중 0이면 → ',S.PERSONAL_V0_LABEL[0]))),
   hand('개인 결과는 공식 점수·순위를 덮어쓰지 않음 · 계산값은 저장 안 함(RAM)'),toTable('results')];}

 /* ---- 2.1.7 후보 선정 연결 (the official default profile; filters and personal settings change nothing) */
 function block7(v){
  const S=QS(),M=ctx.model,links=h('div',{class:'links'},h('a',{class:'lk',href:href('portfolio')},'→ 5.1 모델 후보 자세히'),h('a',{class:'lk',href:href('detail','target-v1')},'→ 세부: TARGET v1 빌더'),
   h('p',{class:'hand'},'매매 지시 아님 · 후보 목록일 뿐'));
  const head=h('b',{class:'model-title'},'모델 후보 N10 · N15 · N20 (N15 주검정) · 공식 기본 프로필 기준');
  const basisLine=h('p',{class:'reason',dataset:{modelBasis:''}},...basisOf(v.pg));
  if(!M)return[h('div',{class:'sk model'},head,h('div',{class:'sk empty dashed',dataset:{empty:'NO_MODEL'}},h('p',null,v.pg.price_basis.inputs_match===false?text('OFFICIAL_INPUTS_DIFFER'):text(v.pg.price_basis.reason||'OFFICIAL_NOT_PUBLISHED')+' · 선정하지 않습니다')),basisLine),links];
  const n=V.n,set_=M.sets['N'+n],chosen=new Set(set_.selected.map(e=>e.id)),capped=new Map(set_.group_capped.map(c=>[c.id,c]));
  const top=v.pg.rows.filter(r=>Number.isInteger(r.rank.official)).sort((a,b)=>a.rank.official-b.rank.official),topN=top.slice(0,n);
  const status=set_.status==='SHORTFALL'?'부족 '+pct2(set_.shortfall_pct)+'% · 채우지 않음':MODEL_STATUS[set_.status]||'구성 상태 미확인';
  const name=id=>{const r=v.pg.rows.find(x=>x.id===id);return r?title(r):id;};
  const phone=window.matchMedia&&window.matchMedia('(max-width:720px)').matches;
  const memberships=top.slice(0,20).map(r=>h('li',{dataset:{member:r.id}},h('span',null,String(r.rank.official),' ',title(r)),
   h('span',{class:'tags'},...M.ns.filter(k=>M.sets['N'+k].selected.some(e=>e.id===r.id)).map(k=>h('span',{class:'pill'},'N'+k)))));
  return[h('div',{class:'sk model',dataset:{model:'N'+n}},head,
   group('후보 수',...M.ns.map(k=>chip('N'+k,n===k,{dataset:{k:'n-'+k,n:String(k)},onclick:set(()=>{V.n=k;})}))),
   h('p',{class:'status-line',dataset:{modelStatus:set_.status}},'N',String(n),' ',String(set_.selected.length),'/',String(n),' · 각 ',pct2(set_.weight_pct),'% · ',status),
   h('div',{class:'model-boxes pc-only'},
    h('div',{class:'mbox',dataset:{topN:''}},h('b',null,'상위 N개 목록 (순위만)'),h('ol',null,...topN.map(r=>h('li',{class:chosen.has(r.id)?'':'dim',dataset:{top:r.id}},String(r.rank.official),' ',title(r),
     chosen.has(r.id)?null:capped.has(r.id)?h('span',{class:'reason'},' — 업종 묶음 40% 한도로 건너뜀 · ',S.sectorName(capped.get(r.id).group)):h('span',{class:'reason'},' — 후보 아님'))))),
    h('div',{class:'mbox blue',dataset:{selected:''}},h('b',null,'포트폴리오 후보 (자격·비중 조건 통과)'),h('ol',null,...set_.selected.map(e=>h('li',{dataset:{pick:e.id}},String(e.rank),' ',name(e.id)))))),
   h('ul',{class:'m-only members'},...memberships),h('p',{class:'m-only reason'},'상위 N개 목록(순위만) ≠ 포트폴리오 후보(자격·비중 조건 통과)'),
   h('details',{class:'excl',open:!phone},h('summary',null,'제외 목록 · 자격 체크 펼치기'),
    h('p',{class:'reason',dataset:{modelExcluded:''}},'제외: ',...EXCLUDED.flatMap(([k,l],i)=>[i?' · ':'',l,' ',String(M.excluded[k])])),
    h('p',{class:'reason',dataset:{modelSkipped:''}},'업종 묶음 40% 한도로 건너뜀 ',String(set_.skipped.SECTOR_GROUP_MAX_40)),
    M.provisional.includes('SUBGROUP_UNKNOWN_NOT_CAPPED')?h('p',{class:'reason',dataset:{modelUnknown:''}},'하위 묶음 미정 ',String(M.unknown.subgroup),'종목 · 상한 미적용 · 잠정 · 결정 대기'):null),
   set_.issuer_check.issuers_n>0?wait('같은 발행사 합산 비중 · 결정 대기 (선정 불변)'):null,
   h('p',{class:'reason'},'V 출처: ',M.v_source.ko,' · 화면 필터·내 설정은 선정에 영향 없음'),basisLine),links];}

 // ---- start: band now, the page, then the layer's notices for this route only
 paintBand();reload();
 Q.subscribe(why=>{if(why==='DATA'||why==='PRICES'||why==='DEVICE')reload();},{signal});
 P.subscribe(()=>{if(!ctx.pg)paintBand();else{refreshReturns();later();}},{signal});
 I.store.subscribe(()=>{ctx.preview=null;later();},{signal});
}
I.qgvLive=Object.freeze({leaderboard,helpers});
})();
