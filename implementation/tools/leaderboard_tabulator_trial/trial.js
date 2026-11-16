/* Leaderboard table trial page (development only; tools/leaderboard_tabulator_trial, never part of web_app or Pages).
   ?ds=<rows file>&mode=existing50|existingAll|tabulator
   - existing50 / existingAll: the leaderboard table drawn the way web_app/screen-qgv-live.js table()/row() draw it: IS2.h from
     web_app/core.js, the shipped helpers (IS2.qgvLive.helpers.sortRows, loaded unchanged from screen-qgv-live.js), app.css
     classes (.tbl, .th-btn, .pc-col, .m-only, details.na), a full rebuild of the table on each sort or filter, focus restored
     by data-k. existing50 = the shipped first window of 50 rows (STEP) with the 더 보기 button; existingAll = every row.
     Columns are the trial subset (순위, 기업, SIC, 유형, QGV, Q, G, V, 자료 기준일); prices, M3, returns and 1.1.8 are out of scope.
   - tabulator: the same rows and columns in Tabulator (self-hosted file, loaded by this page only), virtual DOM (fixed height).
   Ranks are the rows' own rank_text (the engine's / generator's); no table numbers rows. Nothing is stored or sent. */
(function(){
'use strict';
const I=window.IS2,h=I.h,H=I.qgvLive.helpers,q=new URLSearchParams(location.search),MODE=q.get('mode')||'existing50',DS=q.get('ds')||'synthetic504';
const phone=window.matchMedia('(max-width:720px)').matches,host=document.getElementById('trial-host'),sel=document.getElementById('trial-industry');
const NF=new Intl.NumberFormat('ko-KR',{minimumFractionDigits:1,maximumFractionDigits:1});
const DF=new Intl.DateTimeFormat('ko-KR',{year:'numeric',month:'2-digit',day:'2-digit',timeZone:'UTC'});
const ok=v=>typeof v==='number'&&Number.isFinite(v);
const day=t=>{const d=Date.parse(t);return Number.isFinite(d)?DF.format(d):null;};
const painted=()=>new Promise(r=>requestAnimationFrame(()=>setTimeout(r,0)));
const naBox=(words,label='NA')=>h('details',{class:'na'},h('summary',null,label),h('span',{class:'reason'},words));
let ROWS=[],byId=new Map(),table=null;
const S={sort:'qgv',industry:'',shown:MODE==='existing50'?50:Infinity};

/* ---------------------------------------------------------------- shared */
function visible(){return S.industry?ROWS.filter(r=>r.industry===S.industry):ROWS;}
function expectedOrder(sortId,industry){const rows=industry?ROWS.filter(r=>r.industry===industry):ROWS;return H.sortRows(rows,sortId,{title:r=>r.title}).map(r=>r.id);}
function company(r){return[h('a',{href:'#/company/'+encodeURIComponent(r.id),class:'co'},r.title),h('span',{class:'reason'},' ',r.ticker),
 h('span',{class:'m-only sub-line'},r.sic||'SIC NA',' · ',r.types_text||'유형 NA'),
 h('span',{class:'m-only sub-line'},...[['Q','q'],['G','g'],['V','v']].flatMap(([a,k],i)=>[i?' · ':'',a,' ',ok(r.score[k])?NF.format(r.score[k]):'NA']))];}
const score=(r,k)=>ok(r.score[k])?NF.format(r.score[k]):naBox(r.na_reason[k]||'값 없음');
const rankCell=r=>r.rank_text==='—'?naBox(r.na_reason.rank||'순위 없음','—'):r.rank_text;

/* ---------------------------------------------------------------- existing table (screen-qgv-live.js table()/row() way) */
const COLS=[['name','기업',['name','name']],['qgv','QGV',['qgv','qgv-asc']],['q','Q',['q-desc','q-asc']],['g','G',['g-desc','g-asc']],['v','V',['v-desc','v-asc']],['asof','자료 기준일',['asof-desc','asof-asc']]];
function existingDraw(){
 const a=document.activeElement,k=a&&a.dataset&&a.dataset.k&&host.contains(a)?a.dataset.k:null;
 const[,key,dir]=H.sortSpec(S.sort),active=key;
 const ordered=H.sortRows(visible(),S.sort,{title:r=>r.title}),drawn=ordered.slice(0,S.shown);
 const ariaSort=col=>col!==active?null:dir===-1?'descending':'ascending',arrow=col=>col===active?(dir===-1?' ↓':' ↑'):'';
 const head=(col,label)=>{const c=COLS.find(x=>x[0]===col),[desc,asc]=c[2];
  return h('button',{type:'button',class:'th-btn',dataset:{k:'th-'+col,col},onclick:()=>{S.sort=col==='name'?'name':S.sort===desc?asc:desc;existingDraw();}},label,h('span',{class:'arrow '+(['q','g','v'].includes(col)?col+'-text':'')},arrow(col)));};
 const th=(col,content,pc)=>h('th',{scope:'col',class:(pc?'pc-col ':'')+(col&&col===active?'on':'')+(['q','g','v'].includes(col)?' ax-'+col:''),'aria-sort':col?ariaSort(col):null},content);
 const cols=[th(null,'순위'),th('name',head('name','기업')),th(null,'SIC',true),th(null,'유형',true),th('qgv',head('qgv','QGV')),th('q',head('q','Q'),true),th('g',head('g','G'),true),th('v',head('v','V'),true),th('asof',head('asof','자료 기준일'),true)];
 const on=c=>(c===active?'on':''),pc=c=>'pc-col '+on(c);
 const body=drawn.map(r=>h('tr',{dataset:{row:r.id}},h('td',{class:'rk',dataset:{cell:'rank'}},rankCell(r)),h('td',{class:on('name')},company(r)),
  h('td',{class:'pc-col',dataset:{cell:'sic'}},r.sic||naBox('분류 자료 없음')),h('td',{class:'pc-col',dataset:{cell:'type'}},r.types_text||naBox('유형 자료 없음')),
  h('td',{class:'num qgv '+on('qgv'),dataset:{cell:'qgv'}},score(r,'total')),h('td',{class:'num ax-q '+pc('q'),dataset:{cell:'q'}},score(r,'q')),
  h('td',{class:'num ax-g '+pc('g'),dataset:{cell:'g'}},score(r,'g')),h('td',{class:'num ax-v '+pc('v'),dataset:{cell:'v'}},score(r,'v')),
  h('td',{class:pc('asof'),dataset:{cell:'asof'}},day(r.acquired_at)||naBox('자료 기준일 없음'))));
 const caption=h('caption',{tabindex:'-1'},'합성 자료 · 정렬: ',H.sortSpec(S.sort)[3],' · 표시 ',String(drawn.length),'개');
 const rest=ordered.length-drawn.length;
 host.replaceChildren(h('div',{class:'lb-main'},h('div',{class:'tbl-wrap'},h('table',{class:'tbl lb-tbl',dataset:{lbTable:'',sort:S.sort}},caption,h('thead',null,h('tr',null,...cols)),h('tbody',null,...body))),
  rest>0?h('button',{type:'button',class:'btn',dataset:{k:'more'},onclick:()=>{S.shown+=50;existingDraw();}},'더 보기 · 50개 (남은 ',String(rest),'개)'):null));
 if(k){const el=host.querySelector('[data-k="'+k+'"]');if(el)el.focus({preventScroll:true});}}

/* ---------------------------------------------------------------- Tabulator */
function loadTabulator(){return new Promise((resolve,reject)=>{
 const css=document.createElement('link');css.rel='stylesheet';css.href='tabulator.min.css';document.head.appendChild(css);
 const s=document.createElement('script');s.src='tabulator.min.js';s.onload=()=>resolve();s.onerror=()=>reject(Error('TABULATOR_NOT_LOADED'));document.head.appendChild(s);});}
function tabulatorBuild(){
 const num=k=>cell=>{const r=cell.getRow().getData()._row;return ok(r.score[k])?NF.format(r.score[k]):naBox(r.na_reason[k]||'값 없음');};
 const numCol=(field,title,k,pcOnly)=>({title,field,sorter:'number',sorterParams:{alignEmptyValues:'bottom'},headerSortStartingDir:'desc',hozAlign:'right',formatter:num(k),visible:!(pcOnly&&phone)});
 const columns=[
  {title:'순위',field:'rank_text',headerSort:false,formatter:cell=>rankCell(cell.getRow().getData()._row)},
  {title:'기업',field:'title',sorter:(a,b)=>String(a).localeCompare(String(b),'ko'),formatter:cell=>h('div',null,company(cell.getRow().getData()._row)),widthGrow:3},
  {title:'SIC',field:'sic',headerSort:false,visible:!phone},{title:'유형',field:'types_text',headerSort:false,visible:!phone},
  numCol('total','QGV','total',false),numCol('q','Q','q',true),numCol('g','G','g',true),numCol('v','V','v',true),
  {title:'자료 기준일',field:'asof',sorter:'number',sorterParams:{alignEmptyValues:'bottom'},headerSortStartingDir:'desc',formatter:cell=>day(cell.getRow().getData()._row.acquired_at)||naBox('자료 기준일 없음'),visible:!phone}];
 const data=ROWS.map(r=>({id:r.id,_row:r,rank_text:r.rank_text,title:r.title,sic:r.sic,types_text:r.types_text,industry:r.industry,total:r.score.total,q:r.score.q,g:r.score.g,v:r.score.v,asof:Date.parse(r.acquired_at)}));
 const el=h('div',{class:'trial-tab'});host.replaceChildren(el);
 return new Promise(resolve=>{table=new window.Tabulator(el,{data,columns,index:'id',layout:'fitColumns',height:phone?'70vh':'600px',
  rowFormatter:row=>{row.getElement().dataset.row=row.getData().id;}});table.on('tableBuilt',()=>resolve());});}
const tabRendered=()=>new Promise(r=>{let done=false;const fin=()=>{if(!done){done=true;table.off('renderComplete',fin);r();}};table.on('renderComplete',fin);setTimeout(fin,5000);});

/* ---------------------------------------------------------------- API for run_trial.js */
async function render(){
 const t0=performance.now();
 if(MODE==='tabulator'){await tabulatorBuild();while(!host.querySelector('.tabulator-row'))await painted();await painted();}
 else{existingDraw();await painted();}
 return{ms:performance.now()-t0,domRows:host.querySelectorAll('tr[data-row],.tabulator-row').length};}
// One header activation (the element a user clicks), measured to the next paint after the table changed.
async function sortBy(col){
 const target=MODE==='tabulator'?host.querySelector('.tabulator-col[tabulator-field="'+(col==='qgv'?'total':col)+'"]'):host.querySelector('button[data-col="'+col+'"]');
 if(!target)throw Error('NO_HEADER '+col);
 const wait=MODE==='tabulator'?tabRendered():null,t0=performance.now();target.click();if(wait)await wait;await painted();return performance.now()-t0;}
async function filterTo(industry){
 const wait=MODE==='tabulator'?tabRendered():null,t0=performance.now();sel.value=industry;sel.dispatchEvent(new Event('change'));if(wait)await wait;await painted();return performance.now()-t0;}
function onFilter(){S.industry=sel.value;if(MODE==='tabulator'){if(S.industry)table.setFilter('industry','=',S.industry);else table.clearFilter(true);}else{S.shown=MODE==='existing50'?50:Infinity;existingDraw();}}
// The ids in the table's current order (all rows that pass the filter, not only the drawn ones).
function order(){if(MODE==='tabulator')return table.getData('active').map(d=>d.id);return H.sortRows(visible(),S.sort,{title:r=>r.title}).map(r=>r.id);}
// Every drawn row's rank text against the row's own rank (filters and sorts must never renumber), and NA never drawn as 0.
function check(){const bad=[],zero=[];let n=0;
 for(const el of host.querySelectorAll('tr[data-row],.tabulator-row')){n++;const id=el.dataset.row,r=byId.get(id),rk=MODE==='tabulator'?el.querySelector('.tabulator-cell[tabulator-field="rank_text"]'):el.querySelector('td[data-cell=rank]');
  const t=rk?rk.textContent.replace(/^—.*$/,'—'):null;if(!r||t!==r.rank_text)bad.push(id+': '+t+' ≠ '+(r&&r.rank_text));
  for(const k of['q','g','v','total'])if(!ok(r.score[k])){const c=MODE==='tabulator'?el.querySelector('.tabulator-cell[tabulator-field="'+k+'"]'):el.querySelector('td[data-cell="'+(k==='total'?'qgv':k)+'"]');if(c&&/^\s*0(?:[.,]0)?\s*$/.test(c.textContent))zero.push(id+' '+k);}}
 const rowsAll=MODE==='tabulator'?table.getData('active'):null,dataBad=rowsAll?rowsAll.filter(d=>d.rank_text!==byId.get(d.id).rank_text).length:0;
 return{n,bad,zero,dataBad,filter:S.industry,shown:n};}

const ready=(async()=>{
 const res=await fetch('rows-'+DS+'.json');ROWS=await res.json();byId=new Map(ROWS.map(r=>[r.id,r]));
 const groups=[...new Map(ROWS.map(r=>[r.industry,r.industry_label])).entries()].filter(([id])=>id).sort();
 sel.replaceChildren(h('option',{value:''},'전체'),...groups.map(([id,label])=>h('option',{value:id},label||id)));sel.addEventListener('change',onFilter);
 if(MODE==='tabulator'){const t0=performance.now();await loadTabulator();return{load:performance.now()-t0};}return{load:0};})();
window.TRIAL=Object.freeze({MODE,DS,ready,render,sortBy,filterTo,order,check,expectedOrder,groups:()=>[...sel.options].map(o=>o.value).filter(Boolean),n:()=>ROWS.length});
})();
