/* 1.1.8 기술 조건 필터 (feature 3.5; owner 2026-11-03 "계층 3 기술적 분석 리더보드 화면"), the part of the QGV leaderboard that runs
   after IS2.ready. screen-qgv-live.js asks IS2.techFilterLive.create({signal, redraw}) once per route and calls, on every draw:
   keep(rows) (the leaderboard rows the tech filter lets through, or null while it is off), head() / cell(row) / sub(row) (the
   table's tech column and the phone line) and block() (this block's content).
   - Flow (owner): 평가일·비교 그룹 선택 → 지표 원값·분위 확인 → 필터 조합 → QGV 등으로 정렬. The sort stays the leaderboard's
     (1.1.2, QGV high first by default): the filter only hides rows, never re-ranks; ranks and scores are unchanged.
   - Deciles, medians and denominators are the file's for the chosen group; adding filters never changes them (IS2.techScreen).
     A condition that needs a missing value or decile is 판정 불가: such rows leave the table and are listed here with their reason.
   - Data: IS2.techScreen.source() (today NONE: no public file, no request) validated by IS2.techScreen.validate; the whole file is
     refused at its first fault. Private research values are never wired to this public screen.
   - Values are price-derived: they appear only as text inside [data-ram-price]; reason codes go to data-na; the view state (switch,
     day, group, conditions) lives in RAM in this module (kept across routes of one page load, gone on reload). Nothing is stored. */
(function(){
'use strict';
const I=window.IS2,{h}=I;
const T=()=>I.techScreen;
// RAM view state, this page load only.
const V={on:false,day:null,group:null,f:null};
const ramText=(...t)=>h('span',{dataset:{ramPrice:''}},...t);
const naLine=(code,words)=>h('span',{class:'reason',dataset:{na:code||''}},words);

function create({signal,redraw}){
 const ctx={src:null,value:null,err:null,loading:false};
 const S=T();if(!V.f)V.f=S.blank();
 function load(){if(ctx.loading)return;ctx.loading=true;
  let p;try{p=T().source();}catch(e){p=Promise.reject(e);}
  Promise.resolve(p).then(src=>{if(signal.aborted)return;ctx.loading=false;ctx.src=src||null;ctx.value=null;ctx.err=null;
   if(src&&src.state==='OK'){const r=T().validate(src.payload);if(r.ok)ctx.value=r.value;else ctx.err=r.code;}
   if(ctx.value){const ev=ctx.value.evaluations;if(!ev.some(e=>e.as_of===V.day))V.day=ev[ev.length-1].as_of;
    const e=evOf();if(!e.groups.some(g=>g.id===V.group))V.group=e.groups[0].id;}
   redraw();},()=>{if(signal.aborted)return;ctx.loading=false;ctx.src={state:'ERROR',code:'TECH_SOURCE_FAILED'};ctx.value=null;ctx.err=null;redraw();});}
 const evOf=()=>ctx.value?ctx.value.evaluations.find(e=>e.as_of===V.day)||null:null;
 const groupOf=()=>{const e=evOf();return e?e.groups.find(g=>g.id===V.group)||null:null;};
 const on=()=>V.on&&!!evOf()&&!!groupOf();
 let memo=null;
 function result(){const e=evOf();if(!e)return null;const key=e.as_of+'|'+V.group+'|'+JSON.stringify(V.f);
  if(memo&&memo.key===key&&memo.e===e)return memo.r;memo={key,e,r:T().evaluate(e,V.group,V.f)};return memo.r;}
 const rowOf=id=>{const e=evOf();return e?e.rows.find(r=>r.company_id===id)||null:null;};

 // The leaderboard rows the filter lets through (PASS of the chosen group), or null while it is off.
 function keep(rows){if(!on())return null;const r=result(),pass=new Set();for(const[id,x]of r.rows)if(x.state==='PASS')pass.add(id);
  let outside=0;for(const row of rows)if(!r.rows.has(row.id))outside++;
  return{rows:rows.filter(x=>pass.has(x.id)),outside,result:r};}

 /* ---- one metric of one row: value + decile (RAM text) or NA with its reason */
 function metricLine(r,m,{short=false}={}){
  const S=T(),x=r.metrics[m],g=V.group,d=x.decile[g],e=evOf(),st=e.stats[g][m],label=short?S.META[m].short:S.META[m].label;
  if(x.value===null)return h('span',{class:'tm',dataset:{metric:m}},label,' ',naLine(x.reason,'NA · '+S.reasonText(x.reason)));
  return h('span',{class:'tm',dataset:{metric:m}},label,' ',ramText(S.format(m,x.value),d!==null?' · '+S.decileText(d):''),
   d===null?[' ',naLine(st.reason||'DECILE_NA','분위 없음 · '+S.reasonText(st.reason||'DECILE_NA'))]:null);}
 function detail(r){const S=T(),e=evOf(),g=groupOf();
  return h('details',{class:'why tech-why'},h('summary',null,'기술 상세 ▸'),
   h('ul',null,...S.METRICS.map(m=>{const x=r.metrics[m],st=e.stats[g.id][m],d=x.decile[g.id];
    return h('li',{dataset:{metric:m}},h('b',null,S.META[m].label),' · ',S.META[m].unit,' · ',
     x.value===null?naLine(x.reason,'값 NA · '+S.reasonText(x.reason)):ramText('값 ',S.format(m,x.value),' · 분위 ',d===null?'없음':S.decileText(d)),
     x.value!==null&&d===null?[' ',naLine(st.reason||'DECILE_NA',S.reasonText(st.reason||'DECILE_NA'))]:null,
     ' · 분모 ',String(st.n_valid),'/',String(g.members),' (',g.label,') · 관측 ',x.obs_days===null?'NA':String(x.obs_days),'/',x.expected_days===null?'NA':String(x.expected_days),'일',
     x.value!==null&&x.reason?[' · ',naLine(x.reason,S.reasonText(x.reason))]:null);})),
   h('p',{class:'reason'},'기준일 ',e.as_of,' · 비교 그룹 ',g.label));}
 // Table column (PC) and phone line: the chosen conditions' metrics first, then the rest (PC) / 6개월 모멘텀 (phone).
 function order(){const S=T(),first=T().conditions(V.f).map(c=>c.metric);return[...new Set([...first,...S.METRICS])];}
 const head=()=>(on()?'기술 지표 · '+groupOf().label+' 기준':null);
 function cell(row){if(!on())return null;const r=rowOf(row.id);if(!r)return naLine('NO_TECH_ROW',T().reasonText('NO_TECH_ROW'));
  return h('div',{class:'tech-cell'},...order().map(m=>metricLine(r,m,{short:false})),detail(r));}
 function sub(row){if(!on())return null;const r=rowOf(row.id);if(!r)return h('span',{class:'m-only sub-line'},naLine('NO_TECH_ROW',T().reasonText('NO_TECH_ROW')));
  const firsts=T().conditions(V.f).map(c=>c.metric),show=firsts.length?[...new Set(firsts)].slice(0,3):['mom_6m'];
  return[h('span',{class:'m-only sub-line tech-line'},...show.flatMap((m,i)=>[i?' · ':'',metricLine(r,m,{short:true})])),h('span',{class:'m-only'},detail(r))];}

 /* ---- the block */
 function block(){
  const S=T(),src=ctx.src;
  if(!src){load();return[h('p',{class:'pending',role:'status',dataset:{state:'loading'}},'불러오는 중')];}
  if(src.state==='NONE')return[h('div',{class:'sk state-card',dataset:{techState:'NONE',na:src.code||'TECH_SCREEN_NOT_CONNECTED'}},h('b',null,S.TEXT.NONE),h('span',null,S.TEXT.NONE_WHY)),
   h('p',{class:'hand'},'흐름: ① 평가일·비교 그룹 → ② 지표 원값·분위 → ③ 필터 → ④ QGV 순으로 보기 · 자료가 오면 켜짐'),
   h('div',{class:'tech-defs'},...S.METRICS.map(m=>h('p',{class:'reason',dataset:{metricDef:m}},h('b',null,S.META[m].label),' · ',S.META[m].unit,' · ',S.META[m].d10)))];
  if(src.state!=='OK'||ctx.err)return[h('div',{class:'sk state-card',role:'alert',dataset:{techState:'ERROR',na:ctx.err||src.code||'TECH_SOURCE_FAILED'}},h('b',null,ctx.err?S.TEXT.INVALID:S.TEXT.FAILED),
   h('span',{class:'reason'},'리더보드는 기술 조건 없이 그대로')),];
  const e=evOf(),g=groupOf(),val=ctx.value;
  const status=h('p',{class:'sk status-line',dataset:{techData:val.data_status}},S.status(val),' · 생성 ',val.generated_at.slice(0,16).replace('T',' '),' · 계산 Codex · 공개 판정 아님');
  // ① 평가일 · 비교 그룹
  const daySel=h('select',{id:'tf-day',dataset:{k:'tf-day'},onchange:ev=>{V.day=ev.target.value;const x=evOf();if(x&&!x.groups.some(q=>q.id===V.group))V.group=x.groups[0].id;redraw();}},
   ...val.evaluations.map(x=>h('option',{value:x.as_of,selected:x.as_of===V.day},x.as_of)));
  const groupSel=h('select',{id:'tf-group',dataset:{k:'tf-group'},onchange:ev=>{V.group=ev.target.value;redraw();}},
   ...e.groups.map(q=>h('option',{value:q.id,selected:q.id===V.group},q.label,' · ',String(q.members),'개')));
  const step1=h('div',{class:'tf-step',dataset:{tfStep:'1'}},h('b',null,'① 평가일 · 비교 그룹'),
   h('div',{class:'sort-row'},h('label',{for:'tf-day'},'평가일'),daySel,h('label',{for:'tf-group'},'비교 그룹'),groupSel),
   h('p',{class:'reason'},'분위·중앙값·분모는 이 그룹 기준으로 고정 · 필터를 더해도 다시 매기지 않음'));
  // ② 지표 원값 · 분위 (one card per metric)
  const cards=S.METRICS.map(m=>{const st=e.stats[g.id][m];
   return h('div',{class:'sk tcard',dataset:{metricCard:m}},h('b',null,S.META[m].label),
    h('span',{class:'reason'},'단위 ',S.META[m].unit,' · 창 ',S.META[m].window),
    h('span',null,'기준일 ',e.as_of,' · 비교 그룹 ',g.label),
    h('span',{dataset:{validCount:''}},'유효 종목 ',String(st.n_valid),' / ',String(g.members)),
    st.median===null?naLine(st.reason||'GROUP_MEDIAN_NA','중앙값 없음 · '+S.reasonText(st.reason||'GROUP_MEDIAN_NA')):h('span',null,'중앙값 ',ramText(S.format(m,st.median))),
    st.deciles?h('span',null,'분위 매김 (D1~D10)'):naLine(st.reason,'분위 없음 · '+S.reasonText(st.reason)),
    h('span',{class:'hand'},S.META[m].d10));});
  const step2=h('div',{class:'tf-step',dataset:{tfStep:'2'}},h('b',null,'② 지표 원값 · 분위'),h('div',{class:'tcards'},...cards),
   h('p',{class:'reason'},'종목별 값은 표의 기술 지표 칸 · 휴대폰은 줄 아래 · 분모·관측일·결손 사유는 \'기술 상세\''));
  // ③ 필터
  const pick=(id,label,opts,value,set)=>h('div',{class:'sk fcard',dataset:{tfFilter:id}},h('label',{for:'tf-'+id},label),
   h('select',{id:'tf-'+id,dataset:{k:'tf-'+id},onchange:ev=>{set(ev.target.value);redraw();}},...opts.map(([v,t])=>h('option',{value:v,selected:v===value},t))));
  const filters=[...S.PERIODS.map(p=>pick('mom-'+p,S.META['mom_'+p].label,S.COND.mom,V.f.mom[p],v=>{V.f={...V.f,mom:{...V.f.mom,[p]:v}};})),
   pick('vol',S.META.vol_6m.label,S.COND.vol,V.f.vol,v=>{V.f={...V.f,vol:v};}),pick('adv',S.META.adv_6m.label,S.COND.adv,V.f.adv,v=>{V.f={...V.f,adv:v};})];
  const sw=h('label',{class:'check'},h('input',{type:'checkbox',checked:V.on,dataset:{k:'tf-on'},onchange:ev=>{V.on=ev.target.checked;redraw();}}),'기술 조건 적용 (표를 이 그룹·조건으로 거름)');
  const step3=h('div',{class:'tf-step',dataset:{tfStep:'3'}},h('b',null,'③ 필터 조합'),sw,h('div',{class:'lb-filters open tf-filters'},...filters),
   S.active(V.f)?h('button',{type:'button',class:'btn',dataset:{k:'tf-clear'},onclick:()=>{V.f=S.blank();redraw();}},'기술 조건 모두 풀기'):null,
   h('p',{class:'reason'},'조건이 없으면 그룹 안의 모든 종목 · 판정할 수 없는 조건은 통과로도 미충족으로도 세지 않음'));
  // ④ 결과
  const r=result(),conds=r.conditions,total=r.counts.PASS+r.counts.FAIL+r.counts.UNKNOWN;
  const unknown=[...r.rows].filter(([,x])=>x.state==='UNKNOWN');
  const tick=id=>{const x=rowOf(id);return x?x.ticker:id;};
  const step4=h('div',{class:'tf-step',dataset:{tfStep:'4'}},h('b',null,'④ 결과 · QGV 등으로 정렬'),
   h('p',{class:'sk status-line',role:'status',dataset:{tfCount:''}},g.label,' ',String(total),'개 중 · 통과 ',String(r.counts.PASS),' · 조건 미충족 ',String(r.counts.FAIL),' · 판정 불가 ',String(r.counts.UNKNOWN)),
   conds.length?h('p',{class:'reason',dataset:{tfConds:''}},'조건: ',conds.map(c=>S.condText(c.metric,c.rule)).join(' · ')):h('p',{class:'reason'},'조건 없음 · 그룹 안 전체'),
   total>0&&r.counts.PASS===0?h('div',{class:'sk empty',dataset:{empty:'TECH_ZERO'}},h('p',null,'계산은 정상 · 조건을 모두 만족하는 종목 0개'),h('p',{class:'reason'},'자료 결손이 아니라 조건 결과 · 조건을 줄여 보세요')):null,
   total===0?h('div',{class:'sk empty',dataset:{empty:'TECH_GROUP_EMPTY'}},h('p',null,'이 그룹에 기술 지표 행이 없습니다')):null,
   unknown.length?h('details',{class:'na',dataset:{tfUnknown:String(unknown.length)}},h('summary',null,'판정 불가 ',String(unknown.length),'개 · 사유'),
    h('ul',null,...unknown.map(([id,x])=>h('li',{dataset:{unknownRow:id}},tick(id),' · ',...x.unknown.flatMap((u,i)=>[i?' · ':'',S.META[u.metric].label,' ',naLine(u.reason,S.reasonText(u.reason))]))))):null,
   h('p',{class:'reason'},V.on?'표: 통과한 종목만 · 정렬은 1.1.2 그대로 (기본 QGV 높은 순) · 순위 번호·점수 그대로':'표에 적용하려면 위 \'기술 조건 적용\'을 켜세요'));
  return[status,step1,step2,step3,step4];}
 return Object.freeze({load,on,keep,head,cell,sub,block});}
I.techFilterLive=Object.freeze({create});
})();
