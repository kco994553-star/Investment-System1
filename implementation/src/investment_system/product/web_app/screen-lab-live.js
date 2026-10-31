/* Feature 9 · Lab (spec v1.0 9.1 백테스트 · 9.2 전진검증 · menu n+1 · route #/lab; boards Lab · MLab), the part that runs after
   IS2.ready. screen-lab.js draws the first-paint skeleton (head, sections lab-1 · lab-2 with a loading line) and hands its two
   slots to IS2.labLive.screen(route, {slots}) from this file (loader.js LOAD_ORDER, after the layer); nothing here touches the
   layer while the file loads. Public + private two layers (FUNCTION_STATUS 1-3, owner 2026-10-31): the public part is drawn at
   once and never waits for, reads or changes with a private panel.
   - 9.1 public: no public result file exists (lab-results/1 waits for LAB-PUBLISH), so the public part is the owner's words of
     the lab-backtest-v1 contract (IS2.lab.TEXT.EMPTY 연구 결과가 아직 없습니다), the readiness checklist (code; ✓ only for what
     exists, never a result), the 9.1.1–9.1.6 rows with their state, and what a result will show once there is one. The words
     do not change with a sign-in: a public result is never shown from a private read.
   - 9.1 private: one IS2.parts.privatePanel (lab-backtest, area 'lab'). Its state comes from IS2.lab.source() only (today NONE
     with PRIVATE_NOT_READY: the panel stays 비공개 기능 준비 중, nothing is requested): PRIVATE_LOGIN_REQUIRED → 로그인 필요 (Lab
     words); OK → the payload goes through IS2.lab.validate again (this file never checks a field itself) and is drawn only when
     the whole file is accepted, else ERROR with the refusal code (404 / schema / missing field / curve / number: the file is
     never partly shown); ERROR → the source's fixed code. Drawn: generated_at, source commit, one tab per run with the owner's
     status line (IS2.lab.status), the run's facts, the seven metrics (a null metric is IS2.lab.nullText: – and its reason, never
     0), the equity curve (start 100, months in the file's order; the strategy an ink line, the benchmark a dashed line, the 100
     line dotted; app.css .curve*) with its end values and a value table, and the limitations. No copy button (Lab private
     results never go into a prompt), no storage.
   - 9.2 public: forward-validation-ledger.json (the price-free public ledger) through IS2.data: IS2.engines.virtual.forward()
     (ForwardValidation.qgSummary / rowEvaluation / segments / evidence of the old reader, P1) and IS2.data.static on the same read
     for the rows' own fields (screen state, DART reference, observation basis counts), as the old web_assets/forward-validation.js
     showed them: facts, the daily Q·G table (v2 기본 + v1 비교용, newest first, 10 rows then the rest under a fold; a list on a
     phone), the evaluation segments (calc versions never chained) and the operating evidence (latest 7 session days). A read that failed or a file not
     published shows its own words; 9.1 stays (partial failure). 9.2.2 이후 성과 is 미산출 with what is missing (prices are not
     in the ledger; the click-only device computation is not wired here). v3 (#442, design approved, not built) is one 준비 중
     line with no v3 number. 9.2 private: one panel (lab-forward-kis, NOT_READY).
   - States: loading (skeleton, then the ledger line), empty (no run / no ledger row), error (loader, ledger, refused file),
     partial failure (one part fails, the other stays), login needed (panel). Keyboard: a roving tablist for runs (arrows, Home,
     End), folds, links. No request but the ledger read, no storage, no style attribute, no innerHTML, no number from the boards.
   Pure helpers (node: tools/web_app_lab_node_test.js): panelPlan, metricRows, curveGeometry, statusKind, evaluationLabel,
   ledgerTable, evidenceView. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else api.install(typeof window==='object'&&window?window:root);})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
const LEDGER='forward-validation-ledger.json',ROWS_SHOWN=10,DAYS_SHOWN=7;
const CODE=/^[A-Z][A-Z0-9_]{1,63}$/;
// Readiness before any backtest result (old web_assets/screen-detail.js list, updated 2026-10-31). ✓ only for what exists.
const CHECKLIST=Object.freeze([
 ['contract','checked','결과 계약 lab-backtest-v1 · 앱 판독기 — 시험용 합성 자료로만 확인, 실제 결과 없음'],
 ['private-path','pending','본인 인증 비공개 경로 (#436 설계의 Lab 결과 저장·조회) — 구현 전'],
 ['result-path','decide','결과 원본 정식 위치 — Codex 제안 #437 검토, 정식 위치는 #436 구현과 함께'],
 ['pit-adapter','checked','과거 시점 공시 어댑터 · 조기 폐장 종가 시각 — 연구 전용, 실제 자료 검증 전'],
 ['fsds-sample','checked','SEC FSDS 표본 확인 — 2015년 4분기 · 2016년 1분기 두 분기만 (접수 시각 = 뉴욕 현지)'],
 ['past-universe','pending','과거 모집단 — 그때의 S&P 500 편입·퇴출 이력이 아직 없습니다 (BT-2)'],
 ['bt-decisions','decide','기간 · 비용 · 체결 규칙 등 남은 결정 (BACKTEST BT-1~17 · 매크로 근사 MD-1~12)'],
 ['regime-frequency','decide','국면 전환 빈도 계산 — 매크로 3.2 순환매 · 3.3 산업 사이클 확률의 근거 (IA-3 · BACKTEST 뒤)'],
 ['returns','na','수익률 계산 — 위 결정이 끝난 뒤에만 합니다']].map(Object.freeze));
const STATE_WORDS=Object.freeze({checked:'✓ 확인됨',pending:'준비 중',decide:'결정 대기',na:'미산출',rule:'조건',private:'비공개 칸'});
// 9.1.1–9.1.6 (FUNCTION_HIERARCHY v1.0 names): [number, name, state, text].
const ROWS91=Object.freeze([
 ['9.1.1','연구 목적','pending','무엇을 무엇과 견주어 확인할지 먼저 적는 칸 · 공개 앱에 등록된 실험이 없습니다'],
 ['9.1.2','실험 구성','pending','전략·프로필 · 기간 · 종목 수 · 리밸런싱 · 비용 · 검증 엔진 연결 전 · 기간은 사용자가 정하고 화면이 고르지 않음'],
 ['9.1.3','가중치 연구','pending','축·세부 요인 가중치를 연구 프로필로 탐색 · 공식 기본값은 자동으로 바뀌지 않음'],
 ['9.1.4','평가 기준','na','비교 대상 = 실행마다 적힌 비교 기준 · 기준선 Track A (9.2.3) · 통과 기준 미산출'],
 ['9.1.5','데이터 조건','rule','시점 기준(PIT) 자료만 · Holdout 기간 미정 · 사용 금지 (UNCONFIRMED) · 가격은 공개 파일에 두지 않음'],
 ['9.1.6','결과 보고','private','실행 목록 · 지표 7개 · 자산 곡선 (시작 100) · 상태 문구 · 한계 — 본인 인증 비공개 칸에서만']].map(Object.freeze));
const METRIC_LABEL=Object.freeze({cagr:'연 복리 수익률 (CAGR)',total_return:'총수익률',max_drawdown:'최대 낙폭',volatility:'변동성 (연율)',sharpe:'샤프 지수',
 benchmark_cagr:'비교 기준 CAGR',excess_cagr:'초과 CAGR (CAGR − 비교 기준 CAGR)'});
const REBALANCE=Object.freeze({daily:'매일',weekly:'매주',monthly:'매월',quarterly:'분기마다',semiannual:'반년마다',annual:'매년'});
const KIND=Object.freeze({PILOT:'파일럿',FORMAL:'정식 실행'});
const LEDGER_STATUS=Object.freeze({ACTIVE:'기록 중 (ACTIVE)',NOT_STARTED:'시작 전 (NOT_STARTED)'});
const PREP='준비 관측 · 주 평가 대상 아님';
const RUNS='공개 원장에 미기록 · 원장에 정기/수동 구분과 실행 성공 여부가 없어 연속 횟수를 세지 않음';
const RULE='주 평가는 Q·G 각 454개 이상, 계산 버전 일치, 행별 실제 수집 시각 7일 이내를 모두 충족한 기록만 씁니다. 나머지는 "준비 관측 · 주 평가 대상 아님"으로 사유와 함께 보존합니다.';
const pct=v=>(v*100).toFixed(2)+'%';
const isObj=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);

/* ---------------------------------------------------------------- pure helpers */
// What the 9.1 private panel shows for one IS2.lab.source() answer. validate is IS2.lab.validate (never re-implemented here).
function panelPlan(src,validate){
 if(!isObj(src))return Object.freeze({state:'ERROR',code:'LAB_SOURCE_INVALID',value:null});
 if(src.state==='OK'){const r=validate(src.payload);
  return r&&r.ok===true?Object.freeze({state:'READY',code:null,value:r.value}):Object.freeze({state:'ERROR',code:r&&CODE.test(String(r.code))?r.code:'INVALID',value:null});}
 if(src.state==='ERROR')return Object.freeze({state:'ERROR',code:CODE.test(String(src.code))?src.code:'LAB_SOURCE_FAILED',value:null});
 if(src.state==='NONE')return Object.freeze({state:src.private==='PRIVATE_LOGIN_REQUIRED'?'LOGIN_REQUIRED':'NOT_READY',code:null,value:null});
 return Object.freeze({state:'ERROR',code:'LAB_SOURCE_UNKNOWN',value:null});}
// The seven metrics of a validated run in the contract's order: ratios as %, sharpe with 2 decimals, a null as nullText.
function metricRows(run,{metrics,nullText}){
 return metrics.map(k=>{const v=run.metrics[k],label=METRIC_LABEL[k]||k;
  return Object.freeze(v===null?{key:k,label,value:null,na:true,text:nullText(run,k)}:{key:k,label,value:v,na:false,text:k==='sharpe'?v.toFixed(2):pct(v)});});}
// Drawing geometry of a validated equity curve (null below two points): x by position in the file's order, y on one scale
// for both lines and the 100 line. A value that is not a finite number > 0 throws (the validator refused it already).
function curveGeometry(curve,{w=600,h=240,pad=12}={}){
 if(!Array.isArray(curve)||curve.length<2)return null;
 const vals=[100];
 for(const p of curve)for(const k of['strategy','benchmark']){const v=p&&p[k];if(typeof v!=='number'||!Number.isFinite(v)||!(v>0))throw Error('CURVE_VALUE');vals.push(v);}
 let lo=Math.min(...vals),hi=Math.max(...vals);if(hi===lo)hi=lo+1;
 const n=curve.length,r=v=>Math.round(v*100)/100,x=i=>r(pad+i*(w-2*pad)/(n-1)),y=v=>r(pad+(hi-v)/(hi-lo)*(h-2*pad));
 const path=k=>curve.map((p,i)=>(i?'L':'M')+x(i)+' '+y(p[k])).join(' ');
 return Object.freeze({w,h,pad,lo,hi,base:y(100),s:path('strategy'),b:path('benchmark'),xs:Object.freeze(curve.map((_,i)=>x(i))),first:curve[0],last:curve[n-1]});}
// Solid status chip only for real inputs with a recorded check and a point-in-time universe; everything else dashed.
const statusKind=run=>run.data_status==='REAL'&&run.validation_status!=='NOT_VALIDATED'&&isObj(run.universe)&&run.universe.point_in_time===true?'checked':'unchecked';
// The old forward-validation.js evaluationLabel (same codes and words), for one raw ledger row.
function evaluationLabel(r,FV){
 if(r.version!==FV.V2_VERSION)return{code:'COMPARISON',text:'비교용 · 평가 대상 아님'};
 if(Object.hasOwn(r,'basis')){const b=r.basis,e=b.evaluation;
  if(r.state!=='RECORDED')return{code:'PREPARATORY',text:PREP+' · '+e.reasons.join(', ')};
  const counts=b.population===null?'':' · Q '+b.q_scored+' · G '+b.g_scored+' · 모집단 '+b.population.n+' ('+b.population.id+')'+(b.acquired?' · 수집 '+b.acquired[0]+'~'+b.acquired[1]:'');
  return e.status==='PRIMARY'?{code:'PRIMARY',text:'주 평가 · '+b.segment+counts}:{code:'PREPARATORY',text:PREP+' · '+e.reasons.join(', ')+' · '+b.segment+counts};}
 if(r.state!=='RECORDED')return{code:'NOT_AVAILABLE',text:'—'};
 return{code:'LEGACY',text:'관측 기준 미기록 (이전 기록, 별도 구간)'};}
const vName=(v,FV)=>v===FV.V2_VERSION?'v2 기본':'v1 비교용';
// One axis of qgSummary: available / companies · weighted mean (2 decimals), or — with the reason; never 0 for a missing mean.
const axisText=(a,n)=>a.available+'/'+n+' · '+(a.weighted_mean===null?'— (점수 있는 종목 없음)':a.weighted_mean.toFixed(2));
/* The daily table of a loaded forward() result fw and the raw validated ledger p (rows zipped by version and position: fw.rows
   is p.versions[fw.primary] in order, fw.comparison p.versions[v1] for schema 2): newest first, v2 before v1 on one date. */
function ledgerTable(fw,p,FV){
 const raw=v=>Array.isArray(p.versions[v])?p.versions[v]:[];
 const lines=[...fw.rows.map((x,i)=>[x,raw(fw.primary)[i]]),...fw.comparison.map((x,i)=>[x,raw(FV.VERSION)[i]])];
 return lines.map(([x,r])=>{const s=x.summary,rec=s.state==='RECORDED',ev=evaluationLabel(r,FV);
  return Object.freeze({date:x.date,version:x.version,vname:vName(x.version,FV),recorded:rec,
   state:rec?r.qg_screen_state+(r.reference_sources?' · DART 참고':''):'기록 · 입력 없음 · '+s.reason_codes.join(', '),
   q:rec?axisText(s.Q,s.companies):'—',g:rec?axisText(s.G,s.companies):'—',evaluation:ev.code,evaluationText:ev.text});})
  .sort((a,b)=>b.date.localeCompare(a.date)||(a.version===FV.V2_VERSION?-1:b.version===FV.V2_VERSION?1:0));}
// The operating evidence of ForwardValidation.evidence (old paintEvidence words): the latest session days and per-version lines.
function evidenceView(e,FV){
 const mark=s=>s==='RECORDED'?'✓':s==='MISSING'?'기록 없음':'기록 · 입력 없음';
 const days=e.days.slice(-DAYS_SHOWN).map(d=>Object.freeze({date:d.date,state:d.state,text:d.date.slice(5)+' · '+Object.entries(d.versions).map(([v,s])=>(v===FV.V2_VERSION?'v2 ':'v1 ')+mark(s)).join(' · ')}));
 const versions=e.versions.map(v=>Object.freeze({version:v.version,name:vName(v.version,FV),count:v.count,
  text:v.count+'건'+(v.count?' · '+v.first+' ~ '+v.latest:'')+' · '+(!v.count?'관측일 없음':v.missing.length?'빠진 거래일 '+v.missing.join(', '):'빠진 거래일 없음')}));
 const missing=e.latest===null?'범위 없음 · 기록 0건':(e.missing.length?e.missing.join(', ')+' · 기록 없음 · 나중에 채우지 않음':'없음')+' · 범위 '+e.start_date+' ~ '+e.latest+' · 미국 거래일 '+e.session_count+'일';
 return Object.freeze({days:Object.freeze(days),total:e.session_count,versions:Object.freeze(versions),latest:e.latest,missing,missingCount:e.missing.length,as_of:e.as_of});}

/* ---------------------------------------------------------------- screen */
function install(win){
 const I=win.IS2,{h,href}=I;
 const put=(box,...c)=>{box.replaceChildren();I.append(box,c);return box;};
 const mascot=m=>I.parts.mascot(m);
 const sub=(title,fn,hand)=>h('div',{class:'lb-head'},h('h3',{class:'stamp sub'},title),fn?h('span',{class:'meta'},'기능 ',fn):null,hand?h('span',{class:'hand'},hand):null);
 const block=(id,...c)=>h('div',{class:'sk card',dataset:{block:id}},...c);
 const dl=(rows,attrs)=>h('dl',{class:'card-body',...(attrs||{})},rows.map(([k,v,d])=>[h('dt',null,h('b',null,k)),h('dd',d?{dataset:d}:null,v)]));
 const loading=what=>h('p',{class:'pending',role:'status',dataset:{state:'loading'}},'불러오는 중 · ',what);
 const failed=(code,text)=>h('div',{class:'sk state-card',dataset:{state:'error',na:code}},mascot('alarm'),h('p',{class:'err'},text));
 const empty=(code,text)=>h('div',{class:'sk state-card',dataset:{state:'empty',na:code}},mascot('plain'),h('p',null,text));
 const chip=k=>h('span',{class:'lab-status'+(k==='checked'?' checked':''),dataset:{labState:k}},STATE_WORDS[k]);
 const prep=(what,missing)=>{const n=I.parts.notReady('준비 중 · '+what,missing);n.dataset.prep='';return n;};
 const panel=(id,title,area)=>{try{return I.parts.privatePanel(area?{id,title,area}:{id,title});}catch(_){return null;}};
 const utc=t=>{const n=Date.parse(t);return Number.isFinite(n)?new Date(n).toISOString().slice(0,16).replace('T',' ')+' UTC':String(t);};
 const fileState=n=>{try{return I.data.state(n);}catch(_){return{state:'FAILED',text:''};}};
 // A phone (390 board) gets lists instead of the wide ledger tables (macro-live's rule: decided when the route draws).
 const phone=()=>{try{return win.matchMedia('(max-width:720px)').matches;}catch(_){return false;}};

 /* ---------------- 9.1 public (static: the same with or without a private read) */
 function public91(){
  const L=I.lab,labels=L.METRICS.map(k=>METRIC_LABEL[k]||k);
  return[
   h('p',{class:'hand'},'공개 결과 파일 없음 · 실제 수익 곡선은 본인 인증을 통과한 비공개 경로에서만 · 화면에서 숨기는 것만으로 비공개라고 하지 않음'),
   h('div',{class:'sk state-card',dataset:{state:'empty',na:'LAB_NO_PUBLIC_RESULT',labPublic:''}},mascot('plain'),
    h('p',null,h('b',{dataset:{labPublicText:''}},L.TEXT.EMPTY)),
    h('p',{class:'reason'},'공개 게시 계약 (lab-results/1)은 공개 결정 (LAB-PUBLISH) 전 · 공개 저장소 · Pages · 로그에 결과를 넣지 않음')),
   block('9.1-ready',sub('준비 체크리스트 · 결과 아님','9.1'),
    h('ul',{class:'news-lines',dataset:{btChecklist:''}},CHECKLIST.map(([k,s,t])=>h('li',{dataset:{btItem:k,btState:s}},chip(s),' ',t))),
    h('p',{class:'reason'},'매크로 3.2 순환매 · 3.3 산업 사이클의 확률은 이 계산과 검증 전까지 미산출 ',h('a',{href:href('macro'),class:'lk'},'→ 3. 매크로'))),
   block('9.1-rows',sub('백테스트 구성','9.1.1 ~ 9.1.6','결과가 생기면 채울 자리'),
    h('ol',{class:'news-lines',dataset:{labRows:''}},ROWS91.map(([n,name,s,t])=>h('li',{dataset:{labRow:n,labRowState:s}},h('b',null,n,' ',name),' ',chip(s),' ',t,
     n==='9.1.3'?[' ',h('a',{href:href('qgv'),class:'lk'},'→ 1. QGV 가중치')]:null)))),
   block('9.1-contract',sub('결과가 생기면 보이는 것','lab-backtest-v1','비공개 칸에서만'),
    h('ul',{class:'news-lines',dataset:{labRules:''}},
     h('li',null,'실행 목록 · 실행마다 상태 문구 (실데이터 파일럿 · 미검증 / 합성 데이터 · 시험용 / 혼합 / 모집단 시점 정합성 미확인)'),
     h('li',null,'지표 ',String(labels.length),'개: ',labels.join(' · '),' · 계산할 수 없는 값은 – 와 사유 (0으로 채우지 않음)'),
     h('li',null,'자산 곡선 · 시작 100 · 월별 · 전략 = 실선 · 비교 기준 = 점선'),
     h('li',null,'한계 · 모집단 정의 · 생존 편향 설명'),
     h('li',null,'아래 비공개 칸 (본인 인증 비공개 경로 · 계약 lab-backtest-v1)에만 보임')),
    h('p',{class:'reason',dataset:{labRule:''}},'판독 규칙 · 계약과 다르면 ',L.TEXT.INVALID,' (오류 코드만 보임) · 판독 통과는 사실 검증 · 시점 검증 · 게시 허가가 아님'))];}

 /* ---------------- 9.1 private: one validated file */
 function curveFigure(r){
  const g=curveGeometry(r.equity_curve);
  if(!g)return h('p',{class:'reason',dataset:{curve:'NONE'}},r.equity_curve.length===1?'곡선 점 1개 (시작 100) · 선을 그리지 않음':'곡선 없음 · 성과 지표가 모두 계산 불가라 그리지 않음');
  const tr=r.metrics.total_return,n=r.equity_curve.length;
  return h('div',{class:'card-body',role:'group','aria-label':'자산 곡선 · '+r.name,dataset:{curve:r.id}},
   h('svg:svg',{class:'curve',viewBox:'0 0 '+g.w+' '+g.h,role:'img',focusable:'false',dataset:{curveMonths:String(n),curveBase:String(g.base)},
    'aria-label':'자산 곡선 · '+g.first.date+' 시작 100 · '+g.last.date+' 끝 전략 '+g.last.strategy+' · 비교 기준 '+g.last.benchmark+' · '+n+'개 월'},
    h('svg:path',{class:'curve-base',d:'M'+g.pad+' '+g.base+' H'+(g.w-g.pad),dataset:{curveLine:'base'}}),
    h('svg:path',{class:'curve-b',d:g.b,dataset:{curveLine:'benchmark'}}),
    h('svg:path',{class:'curve-s',d:g.s,dataset:{curveLine:'strategy'}})),
   h('div',{class:'card-body'},
    h('p',{class:'curve-key'},h('span',{class:'s'},'전략'),h('span',{class:'b'},'비교 기준 · ',r.benchmark.name),h('span',null,'가는 점선 = 100')),
    h('p',{class:'reason',dataset:{curveRange:''}},g.first.date,' 시작 100 → ',g.last.date,' 끝 · 전략 ',h('span',{dataset:{curveEnd:'strategy'}},String(g.last.strategy)),
     ' · 비교 기준 ',h('span',{dataset:{curveEnd:'benchmark'}},String(g.last.benchmark)),' · 총수익률 ',tr===null?I.lab.nullText(r,'total_return'):pct(tr))),
   h('details',{dataset:{curveTable:''}},h('summary',null,'곡선 값 표 · ',String(n),'개 월'),
    h('div',{class:'tbl-wrap'},h('table',{class:'tbl'},h('thead',null,h('tr',null,h('th',{scope:'col'},'월'),h('th',{scope:'col',class:'num'},'전략'),h('th',{scope:'col',class:'num'},'비교 기준'))),
     h('tbody',null,r.equity_curve.map(p=>h('tr',{dataset:{curvePoint:p.date}},h('td',null,p.date),h('td',{class:'num'},String(p.strategy)),h('td',{class:'num'},String(p.benchmark)))))))));}
 function runDetail(r,i){
  const L=I.lab,u=r.universe,rows=metricRows(r,{metrics:L.METRICS,nullText:L.nullText});
  return h('div',{role:'tabpanel',id:'lab-run-panel','aria-labelledby':'lab-run-tab-'+i,tabindex:'0',class:'card-body',dataset:{labRun:r.id}},
   h('h4',null,r.name),
   h('p',null,h('span',{class:'lab-status'+(statusKind(r)==='checked'?' checked':''),dataset:{labStatus:r.data_status+' '+r.validation_status}},L.status(r))),
   h('p',null,r.description),
   dl([['실행',r.id+' · '+KIND[r.run_type]+' · QGV '+r.qgv_version],['기간',r.period.start+' ~ '+r.period.end],['재조정',REBALANCE[r.rebalance]],
    ['비교 기준',r.benchmark.name+' · '+(r.benchmark.total_return?'배당 재투자 포함':'배당 재투자 제외')],['비용','수수료 '+r.costs.fee_bps+' bp · 슬리피지 '+r.costs.slippage_bps+' bp (한쪽 체결당)'],
    ['모집단',u.definition],['모집단 시점',u.point_in_time?'시점별 모집단':'시점 정합성 미확인',{labPit:String(u.point_in_time)}],['생존 · 선정 편향',u.survivorship_note]],{dataset:{labRunFacts:''}}),
   h('div',{class:'tbl-wrap'},h('table',{class:'tbl',dataset:{labMetrics:''}},h('caption',null,'지표 · 비율은 백분율 · 계산할 수 없는 값은 – 와 사유'),
    h('thead',null,h('tr',null,h('th',{scope:'col'},'지표'),h('th',{scope:'col',class:'num'},'값'))),
    h('tbody',null,rows.map(m=>h('tr',{dataset:m.na?{metric:m.key,na:'NULL'}:{metric:m.key}},h('td',null,h('b',null,m.label)),h('td',m.na?{dataset:{metricValue:''}}:{class:'num',dataset:{metricValue:''}},m.text)))))),
   curveFigure(r),
   h('h4',null,'한계'),
   r.limitations.length?h('ul',{class:'news-lines',dataset:{labLimitations:String(r.limitations.length)}},r.limitations.map(t=>h('li',null,t))):h('p',{class:'reason',dataset:{labLimitations:'0'}},'적힌 한계 없음'));}
 function runsView(v){
  const box=h('div',{class:'card-body',dataset:{labRuns:String(v.runs.length)}});let cur=0;
  const draw=focus=>{
   const n=v.runs.length,tabs=h('div',{role:'tablist','aria-label':'실행 고르기',class:'scroll'},v.runs.map((r,i)=>h('button',{type:'button',role:'tab',id:'lab-run-tab-'+i,class:'chip'+(i===cur?' on':''),
    'aria-selected':String(i===cur),'aria-controls':'lab-run-panel',tabindex:i===cur?'0':'-1',dataset:{labRunTab:r.id},onclick:()=>{cur=i;draw(true);}},r.name)));
   tabs.addEventListener('keydown',e=>{let j=null;if(e.key==='ArrowRight'||e.key==='ArrowDown')j=(cur+1)%n;else if(e.key==='ArrowLeft'||e.key==='ArrowUp')j=(cur+n-1)%n;else if(e.key==='Home')j=0;else if(e.key==='End')j=n-1;
    if(j!==null){e.preventDefault();cur=j;draw(true);}});
   box.replaceChildren(tabs,runDetail(v.runs[cur],cur));
   if(focus){const t=box.querySelector('[role=tab][aria-selected="true"]');if(t)t.focus();}};
  draw(false);return box;}
 function results(v){
  return h('div',{class:'card-body',dataset:{labResults:''}},
   h('p',{class:'reason',dataset:{labFile:''}},'계약 lab-backtest-v1 판독 통과 · 생성 ',utc(v.generated_at),' · 연구 코드 ',v.source_commit.slice(0,12),' · 판독 통과는 사실 검증 · 시점 검증 · 게시 허가가 아님'),
   v.runs.length?runsView(v):empty('LAB_NO_RUNS',I.lab.status(null)));}
 function apply(p,plan){
  if(!p)return;
  if(plan.state==='READY'){let node;try{node=results(plan.value);}catch(_){p.set('ERROR',{code:'LAB_RENDER_FAILED'});return;}p.set('READY',{render:b=>b.appendChild(node)});return;}
  if(plan.state==='ERROR'){try{p.set('ERROR',{code:plan.code});}catch(_){p.set('ERROR',{code:'LAB_SOURCE_FAILED'});}return;}
  p.set(plan.state);}

 /* ---------------- 9.2 public: the price-free ledger */
 function table(rows){
  const at=r=>({forwardDay:r.date,forwardVersion:r.version,forwardEvaluation:r.evaluation});
  if(phone())return h('ol',{class:'news-lines',dataset:{forwardDays:String(rows.length)}},rows.map(r=>h('li',{dataset:at(r)},
   h('b',null,r.date,' · ',r.vname),' · ',r.state,h('br'),'Q ',r.q,' · G ',r.g,h('br'),h('span',{class:'reason'},r.evaluationText))));
  return h('div',{class:'tbl-wrap'},h('table',{class:'tbl',dataset:{forwardDays:String(rows.length)}},
   h('thead',null,h('tr',null,['날짜 · 판','상태','Q 가용 · 가중평균','G 가용 · 가중평균','평가 구분'].map(t=>h('th',{scope:'col'},t)))),
   h('tbody',null,rows.map(r=>h('tr',{dataset:at(r)},
    h('td',null,r.date,' · ',r.vname),h('td',null,r.state),h('td',null,r.q),h('td',null,r.g),h('td',null,r.evaluationText))))));}
 function paint92(refs,fw,p){
  const FV=win.ForwardValidation;
  if(!fw||fw.state!=='LOADED'||!p||!FV){
   const s=fileState(LEDGER),words=fw&&fw.state==='NOT_PUBLISHED'?failed('NOT_PUBLISHED','전진검증 원장이 아직 게시되지 않았습니다 · '+(s.text||LEDGER)):failed('READ_FAILED','전진검증 원장을 읽지 못했습니다 · '+(s.text||LEDGER));
   put(refs.ledger,sub('관측 기록','9.2.1','그날의 Q·G를 가격 없이 추가만 하는 원장'),words);
   put(refs.eligibility,sub('평가 가능 여부','9.2.3'),h('p',{class:'reason',dataset:{forwardEligibility:'NOT_AVAILABLE'}},'원장을 읽지 못해 평가 구간을 보이지 않음'),baseline());
   put(refs.evidence,sub('운영 증거','9.2.4'),h('p',{class:'reason',dataset:{forwardEvidence:'NOT_AVAILABLE'}},'원장을 읽지 못해 관측일을 보이지 않음 · 정기/수동 · 실행 결과: ',RUNS));
   return;}
  const primary=p.versions[fw.primary]||[],target=[...primary].reverse().find(r=>r.target),n=target?Object.keys(target.target.weights_units).length:null;
  const counts=[[fw.primary,fw.rows.length],...(fw.comparison.length||p.schema_version===2?[[FV.VERSION,fw.comparison.length]]:[])].map(([v,c])=>vName(v,FV)+' '+c+'건').join(' · ');
  const facts=dl([['상태',LEDGER_STATUS[fw.status]||fw.status,{forwardStatus:fw.status}],['시작일',fw.start_date],['기록 수',counts,{forwardCount:String(fw.rows.length)}],
   ['전략 · 판',p.strategy+' · '+fw.primary+' · '+p.calibration],['V 포함 판',FV.V_VERSION+' · 기록 0건 · V_REQUIRES_DEVICE_PRICES'],
   ['대상',p.target.portfolio_id+' '+p.target.version+(n===null?'':' · '+n+'종목')],['Holdout',p.holdout+' · 사용 금지'],['가격','원장에 가격 없음 (price_free)'],['원장 기준 시각',fw.as_of]],{dataset:{forwardFacts:''}});
  const rows=ledgerTable(fw,p,FV);
  put(refs.ledger,sub('관측 기록','9.2.1','그날의 Q·G를 가격 없이 추가만 하는 원장'),facts,
   h('h4',null,'일별 Q·G 요약 (V 없음)'),
   !rows.length?empty('NO_LEDGER_ROWS',fw.status==='NOT_STARTED'?'시작일 전이라 기록이 없습니다':'아직 완료된 미국 거래일 기록이 없습니다'):table(rows.slice(0,ROWS_SHOWN)),
   rows.length>ROWS_SHOWN?h('details',{dataset:{forwardMore:String(rows.length-ROWS_SHOWN)}},h('summary',null,'이전 기록 ',String(rows.length-ROWS_SHOWN),'행 더 보기'),table(rows.slice(ROWS_SHOWN))):null,
   h('p',{class:'reason'},'가중평균은 점수가 있는 종목만 대상 비중으로 평균한 화면 표시값이며 저장하지 않습니다 · 보정 전 (UNCALIBRATED)'));
  const withBasis=p.schema_version===2&&primary.some(r=>Object.hasOwn(r,'basis'));
  const segName=s=>s==='LEGACY'?'관측 기준 미기록 (이전 기록)':s==='NONE'?'계산 버전 없음 (NONE)':s;
  const segAt=s=>({forwardSegment:s.segment,forwardPrimary:String(s.eligible_dates.length),forwardPrep:String(s.preparatory_dates.length)});
  const segs=!withBasis?h('p',{class:'reason',dataset:{forwardEligibility:'NO_BASIS'}},'관측 기준이 기록된 행이 없어 평가 구간이 없습니다')
   :phone()?h('ol',{class:'news-lines',dataset:{forwardSegments:String(fw.segments.length)}},fw.segments.map(s=>h('li',{dataset:segAt(s)},h('b',null,segName(s.segment)),' · ',
    s.first_date+' → '+s.last_date,' · 주 평가 기록 ',String(s.eligible_dates.length),' · 준비 관측 ',String(s.preparatory_dates.length))))
   :h('div',{class:'tbl-wrap'},h('table',{class:'tbl',dataset:{forwardSegments:String(fw.segments.length)}},
    h('thead',null,h('tr',null,['평가 구간 (계산 버전)','기간','주 평가 기록','준비 관측'].map(t=>h('th',{scope:'col'},t)))),
    h('tbody',null,fw.segments.map(s=>h('tr',{dataset:segAt(s)},h('td',null,segName(s.segment)),h('td',null,s.first_date+' → '+s.last_date),
     h('td',{class:'num'},String(s.eligible_dates.length)),h('td',{class:'num'},String(s.preparatory_dates.length)))))));
  put(refs.eligibility,sub('평가 가능 여부','9.2.3','서로 다른 계산 버전은 잇지 않음'),segs,
   h('p',{class:'reason',dataset:{forwardRule:''}},RULE),baseline());
  const e=evidenceView(fw.evidence,FV);
  put(refs.evidence,sub('운영 증거','9.2.4','기록이 제때, 고쳐 쓰이지 않고 쌓였다는 증거'),
   e.days.length?h('div',{class:'scroll',dataset:{forwardEvidenceDays:String(e.days.length)}},e.days.map(d=>h('span',{class:d.state==='RECORDED'?'chip':d.state==='MISSING'?'chip err':'chip wait',dataset:{forwardEvidenceDay:d.date,forwardEvidenceState:d.state}},d.text)))
    :empty('NO_OBSERVATION','관측일 없음 · 공개 원장 기록 0건'),
   e.total>e.days.length?h('p',{class:'reason'},'최근 ',String(e.days.length),'거래일 · 전체 ',String(e.total),'거래일'):null,
   dl([...e.versions.map(v=>['관측일 · '+v.name,v.text,{forwardEvidenceVersion:v.version}]),['마지막 관측일',e.latest===null?'없음 · 기록 0건':e.latest],
    ['빠진 거래일',e.missing,{forwardEvidenceMissing:String(e.missingCount)}],['원장 기준 시각',e.as_of],['정기/수동 · 실행 결과',RUNS]],{dataset:{forwardEvidence:''}}),
   h('p',{class:'reason'},'원장은 추가만 하며 지난 기록을 고쳐 쓰지 않습니다 · 공개 원장에는 가격이 없습니다'));}
 const baseline=()=>dl([['기준선','Track A 미국 상위 500 · 3개 시점 동결 · 동결된 기록은 바꾸지 않음'],['Holdout','사용 금지 · UNCONFIRMED'],['프로필 승격','통과한 검증 기록이 없어 승격할 수 없습니다']],{dataset:{forwardBaseline:''}});

 // The skeleton's two slots filled: 9.1's public part and its panel at once, 9.2's blocks with their loading lines and its panel;
 // the panel state after IS2.lab.source(), the ledger once IS2.data answered (route.signal drops a late fill of a page left).
 function screen(route,{slots}){
  const aborted=()=>route.signal.aborted;
  const p91=panel('lab-backtest','연구 결과','lab'),p92=panel('lab-forward-kis','이후 수익률 (KIS)');
  put(slots['lab-1'],...public91(),p91?p91.node:null);
  const refs={ledger:block('9.2.1',sub('관측 기록','9.2.1','그날의 Q·G를 가격 없이 추가만 하는 원장'),loading('전진검증 원장')),
   outcome:block('9.2.2',sub('이후 성과','9.2.2','기록 이후의 결과'),
    prep('이후 성과 미산출 · D+5 · D+20 · D+63 · D+252',['가격 (공개 원장에 없음)','이 화면의 클릭 계산 연결 (기기 시세 · 메모리 전용)','S&P 500 비교 계열']),
    h('p',{class:'reason'},'과거 판단은 다시 쓰지 않음 · 계산한 수익률은 저장 · 전송하지 않음'),
    h('p',{class:'reason',dataset:{forwardPrivateNote:''}},'아래 비공개 칸 (로그인한 오너에게만): KIS 분할 반영 일봉으로 D+5 · 20 · 63 · 252 수익률과 SPY 대비 · 공개 원장 · 공식 평가에 넣지 않음')),
   eligibility:block('9.2.3',sub('평가 가능 여부','9.2.3'),loading('평가 구간')),evidence:block('9.2.4',sub('운영 증거','9.2.4'),loading('관측일'))};
  const v3=prep('전진검증 v3 · 설계 승인 (#442) · 구현 전이라 v3 숫자 없음',['v3 원장','바구니 단위 구간별 수익률 계산']);v3.dataset.forwardV3='NOT_BUILT';
  put(slots['lab-2'],h('p',{class:'hand'},'결과를 미리 알 수 없는 날부터 쌓는 기록 · 기록이 없으면 없다고 적습니다 · v1 · v2는 지금 기록 그대로'),v3,
   h('p',{class:'reason'},'v3가 시작되면 v1 · v2는 새 기록을 멈추고 지금 기록은 그대로 보존합니다'),refs.ledger,refs.outcome,p92?p92.node:null,refs.eligibility,refs.evidence);
  Promise.resolve().then(()=>I.lab.source()).then(src=>{if(!aborted())apply(p91,panelPlan(src,I.lab.validate));},()=>{if(!aborted()&&p91)p91.set('ERROR',{code:'LAB_SOURCE_FAILED'});});
  // One read: forward() starts IS2.data.static(LEDGER) and the second call joins it (the layer keeps one read per page).
  let fw,raw;try{fw=I.engines.virtual.forward();raw=I.data.static(LEDGER);}catch(e){fw=Promise.reject(e);raw=null;}
  Promise.all([fw,raw]).then(([f,p])=>{if(!aborted())paint92(refs,f,p);},()=>{if(!aborted())paint92(refs,null,null);});}
 I.labLive=Object.freeze({screen});
}
return Object.freeze({LEDGER,CHECKLIST,ROWS91,METRIC_LABEL,panelPlan,metricRows,curveGeometry,statusKind,evaluationLabel,ledgerTable,evidenceView,install});
});
