/* 1.1.8 기술 조건 필터 (feature 3.5; owner 2026-11-03 and 2026-11-04), the part of the QGV leaderboard that runs after IS2.ready.
   screen-qgv-live.js asks IS2.techFilterLive.create({signal, redraw}) once per route and calls on every draw: keep(rows, {basis,
   universe}) (the leaderboard rows the filter lets through, or null when it does not apply; basis = the page's price_basis,
   universe = the Universe504 rows the join is checked against), head() / cell(row) / sub(row) (the table's tech column
   and the phone line) and block() (this block's content).
   - Data: Codex's technical-leaderboard/1 boards (#469) through IS2.techScreen (validate, evaluate); today the source is NONE.
     One board per (signal_day, group_id). Ranks, N, medians and deciles are the board's and never change with the filters; the
     conditions are the board's own booleans (중앙값 이상 = ge_median, 중앙값 초과 = gt_median); a null condition is 판정 불가.
   - Flow (owner): ① 평가일·비교 그룹(보드) → ② 지표 원값·분위 → ③ 필터 → ④ 결과. The block's own board table lists the board's rows
     with their ORIGINAL rank of the chosen metric (the rank number is the board's, never renumbered after filtering). The
     leaderboard table is filtered only when IS2.techScreen.joinRows verifies the same evaluation date and the same security
     (owner audit 2026-11-07; QGV join key [signal_day, security_id]): the QGV evaluation date is the official publication's
     price_basis_date (publication present, inputs matching) and must equal signal_day; the security map (source().map, none
     today) must map every board security one-to-one to a Universe504 row by listing key + company id. A security id, ticker or
     code is never matched by itself. Its sort stays 1.1.2 (QGV high first by default). No join → the leaderboard is left as it
     is (no technical condition applied) and the block says why (date missing / date mismatch / mapping missing / ambiguous …).
   - States kept apart: 그룹 구성 미확인 (GROUP_MEMBERSHIP_UNCONFIRMED: no N, rank, median or decile), 유효 N < 10 (ranks and median,
     no decile), 계산 후 조건 충족 0건 (every condition decided, none passed), 판정 불가 (a condition the board cannot decide).
   - A null value is NA with its reason; raw_value is never shown and never fills it. Values are price-derived: text inside
     [data-ram-price] only; the view state lives in RAM (this page load); nothing is stored. */
(function(){
'use strict';
const I=window.IS2,{h}=I;
const T=()=>I.techScreen;
const V={on:false,board:null,conds:{},by:'momentum_6m'};
const ram=(...t)=>h('span',{dataset:{ramPrice:''}},...t);
const na=(code,words)=>h('span',{class:'reason',dataset:{na:code||''}},words);
const STATE_WORDS={UNCONFIRMED:'그룹 구성 미확인 · 순위·중앙값·분위 없음',N_BELOW_10:null,OK:null};

function create({signal,redraw}){
 const ctx={src:null,value:null,map:null,err:null,loading:false};
 function load(){if(ctx.loading)return;ctx.loading=true;let p;try{p=T().source();}catch(e){p=Promise.reject(e);}
  Promise.resolve(p).then(src=>{if(signal.aborted)return;ctx.loading=false;ctx.src=src||null;ctx.value=null;ctx.err=null;ctx.map=src&&src.map!==undefined?src.map:null;
   if(src&&src.state==='OK'){const r=T().validate(src.payload);if(r.ok)ctx.value=r.value;else ctx.err=r.code;}
   if(ctx.value&&!ctx.value.boards.some(b=>b.id===V.board))V.board=ctx.value.boards[0].id;redraw();},
  ()=>{if(signal.aborted)return;ctx.loading=false;ctx.src={state:'ERROR',code:'TECH_SOURCE_FAILED'};ctx.value=null;redraw();});}
 const entry=()=>ctx.value?ctx.value.boards.find(b=>b.id===V.board)||null:null;
 const board=()=>{const e=entry();return e?e.board:null;};
 const conds=()=>T().METRICS.filter(m=>V.conds[m]&&V.conds[m]!=='none').map(m=>({metric:m,condition:V.conds[m]}));
 let memo=null;
 function result(){const b=board();if(!b)return null;const key=V.board+'|'+JSON.stringify(conds());if(memo&&memo.key===key&&memo.b===b)return memo.r;
  memo={key,b,r:T().evaluate(b,conds())};return memo.r;}
 let secMemo=null;const secs=()=>{const b=board();if(!b)return new Map();if(secMemo&&secMemo.b===b)return secMemo.s;secMemo={b,s:T().securities(b)};return secMemo.s;};
 // The QGV list's evaluation date: the official publication's price basis day, only with a publication whose inputs match.
 const qgvDay=b=>(b&&b.publication_id&&b.inputs_match===true&&typeof b.price_basis_date==='string'?b.price_basis_date:null);
 // Board rows joined to leaderboard rows only when verified (IS2.techScreen.joinRows: same evaluation date, same security, one to one).
 let joinMemo=null;
 function keep(rows,{basis=null,universe=rows}={}){if(!V.on||!board())return null;const j=T().joinRows(board(),universe,{day:qgvDay(basis),map:ctx.map});joinMemo=j;
  if(!j.ok)return null;const r=result();
  return{rows:rows.filter(x=>j.pairs.has(x.id)&&r.rows.get(j.pairs.get(x.id)).state==='PASS'),joined:j.pairs.size,result:r};}
 const on=()=>V.on&&!!board()&&!!joinMemo&&joinMemo.ok;
 const secOfRow=row=>{const k=on()&&joinMemo.pairs.get(row.id);return k?secs().get(k):null;};

 /* ---- one metric of one security: value + rank/decile (RAM text) or NA with its reason */
 function metricLine(s,m,{short=false}={}){const S=T(),r=s.rows[m],label=short?S.META[m].short:S.META[m].label;
  if(!r)return h('span',{class:'tm',dataset:{metric:m}},label,' ',na('NO_ROW',S.reasonText('NO_ROW')));
  const v=S.display(m,r);if(v===null)return h('span',{class:'tm',dataset:{metric:m}},label,' ',na(r.null_reasons[0]||'',S.reasonText(r.null_reasons[0])));
  return h('span',{class:'tm',dataset:{metric:m}},label,' ',ram(v,r.rank!==null?' · '+r.rank+'위':'',r.decile!==null?' · '+S.decileText(r.decile):''),
   r.decile===null&&r.null_reasons.length?[' ',na(r.null_reasons[0],S.reasonText(r.null_reasons[0]))]:null);}
 function detail(s){const S=T(),b=board();
  return h('details',{class:'why tech-why'},h('summary',null,'기술 상세 ▸'),
   h('ul',null,...S.METRICS.map(m=>{const x=b.metrics[m],r=s.rows[m],v=r?S.display(m,r):null;
    return h('li',{dataset:{metric:m}},h('b',null,S.META[m].label),' · ',
     v===null?na(r?r.null_reasons[0]||'':'NO_ROW','NA · '+S.reasonText(r?r.null_reasons[0]:'NO_ROW')):ram('값 ',v,' · 순위 ',r.rank===null?'없음':r.rank+'위',' · 분위 ',r.decile===null?'없음':S.decileText(r.decile)),
     ' · 분모 ',x.n_valid===null?'NA':String(x.n_valid),'/',x.n_members===null?'NA':String(x.n_members),
     r&&v!==null&&r.null_reasons.length?[' · ',na(r.null_reasons[0],S.reasonText(r.null_reasons[0]))]:null);})),
   h('p',{class:'reason'},'기준일 ',b.signal_day,' · 비교 그룹 ',b.group_id));}
 const head=()=>(on()?'기술 지표 · '+board().group_id+' · '+board().signal_day:null);
 function cell(row){if(!on())return null;const s=secOfRow(row);if(!s)return na('NO_ROW',T().reasonText('NO_ROW'));
  return h('div',{class:'tech-cell'},...T().METRICS.map(m=>metricLine(s,m)),detail(s));}
 function sub(row){if(!on())return null;const s=secOfRow(row);if(!s)return h('span',{class:'m-only sub-line'},na('NO_ROW',T().reasonText('NO_ROW')));
  const first=conds().map(c=>c.metric),show=first.length?[...new Set(first)].slice(0,3):['momentum_6m'];
  return[h('span',{class:'m-only sub-line tech-line'},...show.flatMap((m,i)=>[i?' · ':'',metricLine(s,m,{short:true})])),h('span',{class:'m-only'},detail(s))];}

 /* ---- the board table of ④: rows in the ORIGINAL rank of the chosen metric (null ranks last), never renumbered */
 function boardTable(keys,phone){const S=T(),list=[...keys].map(k=>secs().get(k)),by=V.by;
  const rk=s=>{const r=s.rows[by];return r&&r.rank!==null?r.rank:Infinity;};
  list.sort((a,b)=>rk(a)-rk(b)||(a.key<b.key?-1:a.key>b.key?1:0));
  const name=s=>s.symbol||s.security_id||s.series_id,rankCell=s=>{const r=s.rows[by];return r&&r.rank!==null?String(r.rank):'—';};
  if(phone)return h('ol',{class:'news-lines tf-board',dataset:{tfBoard:String(list.length)}},...list.map(s=>h('li',{dataset:{tfRow:s.key}},
   h('b',{dataset:{tfRank:''}},rankCell(s)),' ',name(s),h('span',{class:'sub-line tech-line'},...S.METRICS.flatMap((m,i)=>[i?' · ':'',metricLine(s,m,{short:true})])),detail(s))));
  return h('div',{class:'tbl-wrap'},h('table',{class:'tbl tf-board',dataset:{tfBoard:String(list.length)}},
   h('caption',null,'보드 행 · 원래 순위 = ',S.META[by].label,' 순위(보드 그대로, 필터 뒤 다시 매기지 않음)'),
   h('thead',null,h('tr',null,h('th',{scope:'col'},'원래 순위'),h('th',{scope:'col'},'종목'),...S.METRICS.map(m=>h('th',{scope:'col'},S.META[m].short)))),
   h('tbody',null,...list.map(s=>h('tr',{dataset:{tfRow:s.key}},h('td',{dataset:{tfRank:''}},rankCell(s)),h('td',null,name(s)),
    ...S.METRICS.map(m=>h('td',{dataset:{metric:m}},metricLine(s,m,{short:true}))))))));}

 /* ---- the block */
 function block(){
  const S=T(),src=ctx.src;
  if(!src){load();return[h('p',{class:'pending',role:'status',dataset:{state:'loading'}},'불러오는 중')];}
  if(src.state==='NONE')return[h('div',{class:'sk state-card',dataset:{techState:'NONE',na:src.code||'TECH_SCREEN_NOT_CONNECTED'}},h('b',null,S.TEXT.NONE),h('span',null,S.TEXT.NONE_WHY)),
   h('p',{class:'hand'},'흐름: ① 평가일·비교 그룹 → ② 지표 원값·분위 → ③ 필터 → ④ QGV 순으로 보기 · 자료가 오면 켜짐'),
   h('div',{class:'tech-defs'},...S.METRICS.map(m=>h('p',{class:'reason',dataset:{metricDef:m}},h('b',null,S.META[m].label),' · ',S.META[m].unit,' · ',S.META[m].d10)))];
  if(src.state!=='OK'||ctx.err)return[h('div',{class:'sk state-card',role:'alert',dataset:{techState:'ERROR',na:ctx.err||src.code||'TECH_SOURCE_FAILED'}},
   h('b',null,ctx.err?S.TEXT.INVALID:S.TEXT.FAILED),h('span',{class:'reason'},'리더보드는 기술 조건 없이 그대로'))];
  const val=ctx.value,b=board(),phone=window.matchMedia&&window.matchMedia('(max-width:720px)').matches;
  const status=h('p',{class:'sk status-line',dataset:{techData:val.data_kind||'UNSPECIFIED'}},S.status(val),' · ',S.SCHEMA,' · 설정 ',b.settings_version,' · 계산 Codex · 공개 판정 아님');
  // ① 평가일 · 비교 그룹 (보드)
  const sel=h('select',{id:'tf-board',dataset:{k:'tf-board'},onchange:e=>{V.board=e.target.value;redraw();}},...val.boards.map(x=>h('option',{value:x.id,selected:x.id===V.board},x.label)));
  const step1=h('div',{class:'tf-step',dataset:{tfStep:'1'}},h('b',null,'① 평가일 · 비교 그룹'),h('div',{class:'sort-row'},h('label',{for:'tf-board'},'보드'),sel),
   h('p',{class:'reason',dataset:{tfMembership:b.membership_status}},'평가일 ',b.signal_day,' · 그룹 ',b.group_id,' · 구성원 ',b.membership_status==='CONFIRMED'?'확인됨':'미확인',
    ' · 순위·분위·중앙값·분모는 이 보드 그대로 · 필터를 더해도 다시 매기지 않음'));
  // ② 지표 카드
  const cards=S.METRICS.map(m=>{const x=b.metrics[m],st=S.metricState(b,m);
   const words=st==='UNCONFIRMED'?STATE_WORDS.UNCONFIRMED:st==='N_BELOW_10'?'유효 종목 '+x.n_valid+' < 10 · 순위·중앙값만 · 분위 없음':'분위 매김 (D10·D1 각 '+x.k+'개)';
   return h('div',{class:'sk tcard',dataset:{metricCard:m,techMetricState:st}},h('b',null,S.META[m].label),h('span',{class:'reason'},'단위 ',S.META[m].unit),
    h('span',null,'기준일 ',b.signal_day,' · 비교 그룹 ',b.group_id),
    h('span',{dataset:{validCount:''}},'유효 종목 ',x.n_valid===null?'NA':String(x.n_valid),' / ',x.n_members===null?'NA':String(x.n_members)),
    x.median===null?na(x.null_reason||'',' 중앙값 없음'):h('span',null,'중앙값 ',ram(S.medianText(m,x.median))),
    h('span',{class:st==='OK'?'':'reason',dataset:{metricStateText:st}},words),h('span',{class:'hand'},S.META[m].d10));});
  const step2=h('div',{class:'tf-step',dataset:{tfStep:'2'}},h('b',null,'② 지표 원값 · 분위'),h('div',{class:'tcards'},...cards));
  // ③ 필터
  const pick=m=>h('div',{class:'sk fcard',dataset:{tfFilter:m}},h('label',{for:'tf-'+m},S.META[m].label),
   h('select',{id:'tf-'+m,dataset:{k:'tf-'+m},onchange:e=>{V.conds={...V.conds,[m]:e.target.value};redraw();}},
    h('option',{value:'none',selected:!V.conds[m]||V.conds[m]==='none'},'조건 없음'),...S.CHOICES[m].map(c=>h('option',{value:c,selected:V.conds[m]===c},S.COND_TEXT[c]))));
  const by=h('div',{class:'sort-row'},h('label',{for:'tf-by'},'원래 순위 기준'),h('select',{id:'tf-by',dataset:{k:'tf-by'},onchange:e=>{V.by=e.target.value;redraw();}},
   ...S.METRICS.map(m=>h('option',{value:m,selected:V.by===m},S.META[m].label))));
  const sw=h('label',{class:'check'},h('input',{type:'checkbox',checked:V.on,dataset:{k:'tf-on'},onchange:e=>{V.on=e.target.checked;redraw();}}),'리더보드 표에도 적용 (보드와 결합된 행만)');
  const step3=h('div',{class:'tf-step',dataset:{tfStep:'3'}},h('b',null,'③ 필터 조합'),h('div',{class:'lb-filters open tf-filters'},...S.METRICS.map(pick)),by,sw,
   conds().length?h('button',{type:'button',class:'btn',dataset:{k:'tf-clear'},onclick:()=>{V.conds={};redraw();}},'기술 조건 모두 풀기'):null,
   h('p',{class:'reason'},'중앙값 이상 = 중앙값과 같은 값 포함 · 중앙값 초과 = 같은 값 제외 · 판정할 수 없는 조건은 통과로도 미충족으로도 세지 않음'));
  // ④ 결과
  const r=result(),cs=r.conditions,total=r.counts.PASS+r.counts.FAIL+r.counts.UNKNOWN,unknown=[...r.rows].filter(([,x])=>x.state==='UNKNOWN');
  const shown=cs.length?[...r.rows].filter(([,x])=>x.state==='PASS').map(([k])=>k):[...r.rows.keys()];
  const j=V.on?joinMemo:null,joined=j&&j.ok?j.pairs.size:null;
  const step4=h('div',{class:'tf-step',dataset:{tfStep:'4'}},h('b',null,'④ 결과 · QGV 등으로 정렬'),
   h('p',{class:'sk status-line',role:'status',dataset:{tfCount:''}},b.group_id,' ',String(total),'개 중 · 통과 ',String(r.counts.PASS),' · 조건 미충족 ',String(r.counts.FAIL),' · 판정 불가 ',String(r.counts.UNKNOWN)),
   cs.length?h('p',{class:'reason',dataset:{tfConds:''}},'조건: ',cs.map(c=>S.condText(c.metric,c.condition)).join(' · ')):h('p',{class:'reason'},'조건 없음 · 보드 전체'),
   cs.length&&r.counts.PASS===0&&r.counts.UNKNOWN===0?h('div',{class:'sk empty',dataset:{empty:'TECH_ZERO'}},h('p',null,'계산 후 조건 충족 0건'),h('p',{class:'reason'},'모든 조건을 판정했고 통과한 종목이 없음 · 자료 결손이 아님')):null,
   cs.length&&r.counts.PASS===0&&r.counts.UNKNOWN>0?h('div',{class:'sk empty',dataset:{empty:'TECH_UNDECIDED'}},h('p',null,'조건 충족 0건 · 판정 불가 ',String(r.counts.UNKNOWN),'건'),h('p',{class:'reason'},'판정할 수 없는 조건이 있음 · 아래 사유')):null,
   unknown.length?h('details',{class:'na',dataset:{tfUnknown:String(unknown.length)}},h('summary',null,'판정 불가 ',String(unknown.length),'개 · 사유'),
    h('ul',null,...unknown.map(([k,x])=>h('li',{dataset:{unknownRow:k}},(secs().get(k).symbol||secs().get(k).security_id||k),' · ',
     ...x.unknown.flatMap((u,i)=>[i?' · ':'',S.META[u.metric].label,' ',na(u.reason,S.reasonText(u.reason))]))))):null,
   shown.length?boardTable(shown,phone):null,
   h('p',{class:'reason',dataset:j&&!j.ok?{tfJoin:j.code,na:j.code}:{tfJoin:joined===null?'OFF':String(joined)}},!j?'리더보드 표에 적용하려면 위 스위치를 켜세요 · 보드 표는 원래 순위 그대로':
    j.ok?'리더보드 표: 결합된 '+joined+'개 중 통과한 종목만 · 정렬은 1.1.2 그대로(기본 QGV 높은 순) · 순위 번호·점수 그대로':
    '리더보드 표에 적용할 수 없음 · '+S.joinText(j)+' · 같은 평가일·같은 증권으로 확인된 행만 결합(QGV 결합 키 [평가일, 증권 ID]) · 리더보드는 기술 조건 없이 그대로'));
  return[status,step1,step2,step3,step4];}
 return Object.freeze({load,on,keep,head,cell,sub,block});}
I.techFilterLive=Object.freeze({create});
})();
