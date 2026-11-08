/* 1.2 · Q/G 부분 비교 — the view of one engine comparison (sector-qgv-axis-comparison/1, IS2.sectorQgvAxis; owner 2026-11-07
   「#505 실자료 부분 비교 계약 추가 인수」). Used by screen-sector-qgv-live.js for the comparison of the shown preview and for a
   listed comparison file (Codex's synthetic file; private retained files only on a development process started with them).
   - Q and G each: before / after / delta / transition / missing reasons and the counts (전 산출 · 후 산출 · 공통 · 새로 · 빠짐 ·
     둘 다 없음 · 공통 중 바뀜) out of the whole denominator. A Q / G row is shown even when the total has no common value; V and
     total are only said to be 산출 / 산출 없음 (null is never 0).
   - The cause is named: 요소·비중 변경 (D1, same input) or 분류 보완·비교집단 확대 (I1, same settings; its relative change is not
     a company improvement), with the config / input / snapshot / classification versions of both sides and what differs.
   - Rows keep the engine's order (no sort by delta, no axis rank, total or market rank); filters only choose what to show;
     50 rows at a time; factor detail is drawn when a row is opened. Text only (no HTML). */
(function(){
'use strict';
const I=window.IS2,{h}=I;
const A=()=>I.sectorQgvAxis,S=()=>I.sectorQgv;
let NF=null;const f2=v=>(NF||(NF=new Intl.NumberFormat('ko-KR',{minimumFractionDigits:2,maximumFractionDigits:2}))).format(v);
const sign=v=>(v>0?'+':v<0?'−':'')+f2(Math.abs(v));
const PAGE=50;
const ctxText=c=>c[0]===null&&c[1]===null?'분류 미확정':S().text(S().SECTOR_TEXT,c[0])+'·'+S().text(S().TEMPLATE_TEXT,c[1]);
const why=list=>list.map(x=>S().text(S().FACTOR_TEXT,x)===x?S().text(S().STATUS_TEXT,x):S().text(S().FACTOR_TEXT,x)).join(', ');
const val=(v,reasons)=>v===null?h('span',{class:'na',dataset:{na:reasons.join(' ')}},'미산출 · ',why(reasons)):h('span',{dataset:{exact:String(v)}},f2(v));

function cell(x,v){
 return h('span',{dataset:{sqAxisCell:x,sqTransition:v.transition}},val(v.before,v.before_reasons),' → ',val(v.after,v.after_reasons),
  v.delta!==null?h('span',{dataset:{sqDelta:String(v.delta)}},' (',sign(v.delta),')'):null,' · ',A().text(A().TRANSITION_TEXT,v.transition),
  v.change_reason!=='UNCHANGED'?' · '+A().text(A().REASON_TEXT,v.change_reason):'');}
function factors(r){const P=S();
 const alloc=a=>a?P.text(P.ROLE_TEXT||{},a.role)+' '+f2(a.axis_weight*100)+'% (총 '+f2(a.nominal_total_weight*100)+'%)':'없음';
 const sc=(s,st)=>s===null?P.text(P.FACTOR_TEXT,st):f2(s);
 return h('div',null,...A().AXES.map(x=>h('div',{dataset:{sqAxisFactors:x}},h('b',null,x,' 요소'),
  r.axes[x].factors.length?h('ul',{class:'news-lines'},...r.axes[x].factors.map(f=>h('li',{dataset:{sqFactor:f.variant_id}},f.variant_id,' · 비중 ',alloc(f.before_allocation),' → ',alloc(f.after_allocation),
   ' · 점수 ',sc(f.before_score,f.before_status),' → ',sc(f.after_score,f.after_status),' · 유효 표본 ',f.before_valid_n===null?'—':String(f.before_valid_n),' → ',f.after_valid_n===null?'—':String(f.after_valid_n),
   f.allocation_changed?' · 비중 바뀜':'',f.score_changed?' · 점수 바뀜':''))):h('p',{class:'reason'},'이 축의 요소 없음'))));}

// render(c, {kind:'PREVIEW'|'SYNTHETIC'|'PRIVATE', name}) -> element (validated here; refused whole with its code)
function render(json,{kind,name=null}){
 const r=A().validate(json);
 if(!r.ok)return h('div',{class:'sk state-card',role:'alert',dataset:{sqAxisState:'INVALID'}},I.parts.mascot('alarm'),h('b',null,'부분 비교 규격 불일치 · 전체 거부'),h('span',{class:'reason'},r.code+' · '+r.path));
 const vw=A().view(r.value),St={axis:'ANY',show:'ALL',limit:PAGE};
 const box=h('section',{class:'sq-axis','aria-label':'Q/G 부분 비교',dataset:{sqAxis:vw.comparison_id,sqAxisKind:kind,sqAxisTreatment:vw.treatment}});
 const kindText={PREVIEW:'이 미리보기의 비교 (합성)',SYNTHETIC:'합성 · 시험용',PRIVATE:'비공개 실자료 · 이 개발 환경에서만'}[kind];
 const idRow=k=>{const b=vw.before_identity[k],a=vw.after_identity[k],d=b!==a,short=v=>/^[0-9a-f]{64}$/.test(v)?v.slice(0,12):v;
  return h('tr',{dataset:{sqIdentity:k,sqDiff:d?'':'no'}},h('th',{scope:'row'},A().text(A().IDENTITY_TEXT,k)),h('td',null,short(b)),h('td',null,short(a)),h('td',null,d?'다름':'같음'));};
 const sum=x=>{const s=vw.axes[x];return h('p',{dataset:{sqAxisSummary:x}},h('b',null,x),' · 전 산출 ',String(s.before_valid),' · 후 산출 ',String(s.after_valid),' · 공통 ',String(s.COMMON_VALID),
  ' · 새로 산출 ',String(s.GAINED),' · 빠짐 ',String(s.LOST),' · 둘 다 없음 ',String(s.BOTH_UNAVAILABLE),' · 공통 중 바뀜 ',String(s.changed_common),' / 전체 ',String(vw.denominator));};
 function rows(){const list=A().filter(vw,St),shown=list.slice(0,St.limit);
  const sel=(k,lab,opts)=>h('div',{class:'sort-row'},h('label',{for:'sq-axis-'+k+'-'+vw.comparison_id},lab),h('select',{id:'sq-axis-'+k+'-'+vw.comparison_id,dataset:{k:'sq-axis-'+k},
   onchange:e=>{St[k]=e.target.value;St.limit=PAGE;draw();}},...opts.map(([v,t])=>h('option',{value:v,selected:St[k]===v},t))));
  const controls=h('div',{class:'sq-axis-filters'},sel('axis','축',[['ANY','Q·G'],['Q','Q'],['G','G']]),
   sel('show','보기',[['ALL','전체(원래 모집단)'],['CHANGED','공통 중 바뀜'],['GAINED','새로 산출'],['LOST','빠짐'],['UNAVAILABLE','둘 다 없음'],['RECLASSIFIED','분류 바뀜']]));
  const items=shown.map(x=>{const det=h('details',{class:'why',dataset:{sqAxisRow:x.company_id}});let done=false;
   det.addEventListener('toggle',()=>{if(det.open&&!done){done=true;det.append(factors(x));}});
   const moved=x.before_context[0]!==x.after_context[0]||x.before_context[1]!==x.after_context[1];
   det.append(h('summary',null,h('b',null,x.company_id),' · ',ctxText(x.before_context),moved?h('span',{dataset:{sqReclassified:''}},' → ',ctxText(x.after_context),' (분류 바뀜)'):null,h('br'),
    cell('Q',x.axes.Q),h('br'),cell('G',x.axes.G),h('br'),
    h('span',{class:'reason'},'V ',x.V.before===null?'산출 없음':f2(x.V.before),' → ',x.V.after===null?'산출 없음':f2(x.V.after),' · 총점 ',x.total.before===null?'산출 없음':f2(x.total.before),' → ',x.total.after===null?'산출 없음':f2(x.total.after))));
   return h('li',null,det);});
  return [controls,h('p',{class:'reason',dataset:{sqAxisCount:String(list.length)}},String(list.length),'행 · 엔진 순서(회사 ID) 그대로 · 필터는 보이는 행만 고르고 비교·비교집단을 바꾸지 않음'),
   items.length?h('ol',{class:'news-lines sq-axis-rows',dataset:{sqAxisRows:String(items.length)}},...items):h('p',{class:'reason',dataset:{sqAxisRows:'0'}},'고른 조건의 행 없음'),
   list.length>St.limit?h('button',{type:'button',class:'btn',dataset:{k:'sq-axis-more'},onclick:()=>{St.limit+=PAGE;draw();}},String(Math.min(PAGE,list.length-St.limit)),'행 더 보기'):null].filter(Boolean);}
 const head=[
  h('h4',null,'Q/G 부분 비교 · ',vw.comparison_id),
  h('p',{class:'sk status-line',dataset:{sqAxisHead:''}},h('span',{class:'chip',dataset:{sqAxisData:kind}},kindText),' ',h('b',{dataset:{sqAxisCause:vw.treatment}},A().text(A().TREATMENT_TEXT,vw.treatment)),
   ' · 기준일 ',vw.valuation_date,' · 자료 시각 ',vw.as_of,' · 모집단 ',vw.universe_id,' ',String(vw.denominator),'개',name?' · '+name:''),
  h('p',{class:vw.treatment==='INPUT_CLASSIFICATION'?'hand err':'reason',dataset:{sqAxisNote:vw.treatment}},A().text(A().TREATMENT_NOTE,vw.treatment),vw.reclassified?' · 분류 바뀐 행 '+vw.reclassified+'개':''),
  h('div',{class:'tbl-wrap'},h('table',{class:'tbl',dataset:{sqAxisIdentity:vw.identity_diff.join(' ')}},h('caption',null,'설정·입력·분류 버전 (전 → 후)'),
   h('thead',null,h('tr',null,...['항목','전','후',''].map(t=>h('th',{scope:'col'},t)))),h('tbody',null,...A().IDENTITY.map(idRow)))),
  ...A().AXES.map(sum),
  h('p',{class:'reason',dataset:{sqAxisVt:vw.vt.total.before+'/'+vw.vt.total.after+'/'+vw.vt.total_common}},'V 산출 전 ',String(vw.vt.V.before),' · 후 ',String(vw.vt.V.after),' · 총점 산출 전 ',String(vw.vt.total.before),' · 후 ',String(vw.vt.total.after),
   ' · 총점 공통 ',String(vw.vt.total_common),'건 · 총점이 없어도 Q/G 비교는 따로 보임 (산출 없음은 0점이 아님)'),
  h('p',{class:'reason',dataset:{sqAxisRank:'NONE'}},'축별 순위·총점·시장 순위 없음 (엔진이 만들지 않음) · 성과 미측정')];
 const body=h('div');
 function draw(){const k=document.activeElement&&box.contains(document.activeElement)&&document.activeElement.dataset?document.activeElement.dataset.k:null;
  body.replaceChildren(...rows());if(k){const el=body.querySelector('[data-k="'+k+'"]');if(el)el.focus({preventScroll:true});}}
 draw();box.replaceChildren(...head,body);return box;}

I.sectorQgvAxisLive=Object.freeze({render});
})();
