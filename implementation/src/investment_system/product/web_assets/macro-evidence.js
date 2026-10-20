/* Macro evidence lines (MEV-1 P1 13 candidate set) on the macro screen: an observation graph on a real time axis with
   evidence vertical lines, release ticks and revision markers, from the public macro-evidence.json (government statistics
   only; no prices, B-PRICE). Exploration screen only (MEV-10): nothing here feeds the official judgement, probabilities,
   the macro gate or any engine. Every rule is "v0 · 미검증", every interpretation "해석 후보 · 미승인".
   - Lines are drawn at the recorded release time; when the source gave no posting time the line is at the collection
     time and says so ("수집 시각 기준"). Lines are never moved to the reference period. The reconstruction layer
     (current revised vintage, reference-period position) is off by default and drawn dashed when turned on.
   - Mobile: the 5 most recent lines (same day = one line with a count), the rest under "더 보기 (n)" (up to 8 drawn).
     PC: up to 10. Tabs 경기 / 주식시장 / 산업 are counted separately; one family counts once.
   - This module only reads one public file; it stores nothing (selected tab/lines live in this page's RAM only).
   API for the cycle ring (lane C1): MacroEvidence.current(), .events({cycle, layer}), .subscribe(fn), .load(). */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.MacroEvidence=api;})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
const FILENAME='macro-evidence.json',SCHEMA='macro-evidence/1',MAX=2*1024*1024;
const TABS=Object.freeze([['economy','경기'],['market','주식시장'],['industry','산업']]);
const FAMILY=Object.freeze({C:'금리곡선',LU:'실업·청구',LD:'노동 수요 선행',MO:'제조 주문',PO:'생산·산출',HO:'주택',BK:'은행 대출',IN:'물가',PL:'정책금리',T:'운송'});
const RULE_SOURCE=Object.freeze({LITERATURE:'[문헌]',PROPOSAL:'[제안]',LITERATURE_UP_PROPOSAL_DOWN:'[문헌] 상향 · [제안] 하향',AGENCY_EVENT:'[기관 사건]'});
const VALIDATION=Object.freeze({POST_HOC_LITERATURE_ONLY:'문헌상 사후 검증만',UNVALIDATED:'미검증',EVENT_FACT_NOT_REQUIRED:'사건은 검증 불필요 · 해석 미검증'});
const REASON=Object.freeze({SOURCE_NOT_COLLECTED:'수집 전',SOURCE_NOT_AVAILABLE:'출처 응답 없음',SOURCE_KEY_NOT_CONFIGURED:'API 키 미설정',TERMS_UNVERIFIED:'약관 원문 미확인 · 공개 보류',
 SCHEMA_MISMATCH:'형식 불일치',SERIES_NOT_FOUND:'계열 없음',MISSING_SOURCE:'값 없음',CONFLICTING_DUPLICATE:'중복 충돌',PROVIDER_ERROR:'출처 오류 응답',UNSAFE_XML:'안전하지 않은 XML',INSUFFICIENT_HISTORY:'이력 부족'});
const LIMIT=Object.freeze({mobile:5,pc:10,mobileMax:8,pcMax:14}),MOBILE_PX=600;
const S={payload:null,status:'NOT_LOADED',listeners:new Set(),loading:null};
const obj=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
function validate(p){
 try{
  if(!obj(p)||p.schema!==SCHEMA||p.kind!=='MACRO_EVIDENCE_LINES')return null;
  const sc=p.scope;if(!obj(sc)||sc.screen!=='EXPLORATION_ONLY'||sc.official_judgement!==false||sc.probability!==false||sc.macro_gate!==false)return null;
  if(!Array.isArray(p.indicators)||p.indicators.length!==13||!obj(p.series)||!Array.isArray(p.events)||!Array.isArray(p.releases)||!Array.isArray(p.replay_events)||!obj(p.summary))return null;
  for(const i of p.indicators){if(!obj(i)||typeof i.id!=='string'||!Array.isArray(i.series)||!Array.isArray(i.cycles)||!obj(i.edges)||!obj(i.rule)||!obj(i.source))return null;for(const s of i.series)if(!obj(p.series[s])||!Array.isArray(p.series[s].obs))return null;}
  for(const e of p.events)if(!obj(e)||e.layer!=='REALTIME'||typeof e.at!=='string'||!['up','down'].includes(e.direction))return null;
  for(const [c] of TABS)if(!obj(p.summary[c]))return null;
  return p;
 }catch(_){return null;}
}
function notify(){for(const fn of S.listeners){try{fn(current());}catch(_){}}}
function setPayload(p,status){S.payload=p?validate(p):null;S.status=S.payload?(S.payload.state==='NOT_AVAILABLE'?'NOT_AVAILABLE':'LOADED'):(status||'INVALID');notify();return S.payload;}
async function load(view=globalThis){
 if(S.loading)return S.loading;
 S.loading=(async()=>{
  try{const r=await view.fetch(FILENAME,{cache:'no-store',credentials:'omit',referrerPolicy:'no-referrer',redirect:'error'});
   if(!r.ok)return setPayload(null,'NOT_AVAILABLE');const text=await r.text();if(new TextEncoder().encode(text).length>MAX)return setPayload(null,'INVALID');
   return setPayload(JSON.parse(text));}catch(_){return setPayload(null,'NOT_AVAILABLE');}
  finally{S.loading=null;}
 })();
 return S.loading;
}
const byId=(p,id)=>p.indicators.find(i=>i.id===id)||null;
function cycleIndicators(p,cycle){return p?p.indicators.filter(i=>i.cycles.includes(cycle)):[];}
// One cycle's summary: families (one family counts once; mixed families on neither side). EVL-1 candidate, not approved.
function summary(p,cycle){
 const b=p&&p.summary[cycle];if(!b)return{cycle,warning:[],improving:[],mixed:[],realtime:[],label:'자료 없음'};
 return{cycle,warning:b.warning_families.slice(),improving:b.improving_families.slice(),mixed:b.mixed_families.slice(),realtime:b.realtime_event_indicators.slice(),label:p.labels.summary};
}
function current(){const p=S.payload;return{status:S.status,generated_at:p?p.generated_at:null,collection_started_at:p?p.collection_started_at:null,scope:p?Object.assign({},p.scope):null,
 summary:Object.fromEntries(TABS.map(([c])=>[c,summary(p,c)])),labels:p?Object.assign({},p.labels):null};}
function events({cycle,layer='REALTIME',indicator}={},p=S.payload){
 if(!p)return[];const ok=i=>{const ind=byId(p,i);return ind&&(!cycle||ind.cycles.includes(cycle))&&(!indicator||indicator===i);};
 if(layer==='REPLAY')return p.replay_events.filter(e=>ok(e.indicator)).map(e=>Object.assign({layer:'REPLAY'},e));
 return p.events.filter(e=>ok(e.indicator)).slice().sort((a,b)=>a.at<b.at?1:a.at>b.at?-1:0).map(e=>Object.assign({},e));
}
function subscribe(fn){if(typeof fn!=='function')return()=>{};S.listeners.add(fn);return()=>S.listeners.delete(fn);}
// Mobile recent-5 + more: group by UTC day of the recorded time; the newest groups are drawn, extras are opt-in.
function lineGroups(list,{mobile,extra=new Set()}){
 const groups=[];const index=new Map();
 for(const e of list){const day=e.at.slice(0,10);if(!index.has(day)){index.set(day,groups.length);groups.push({day,at:e.at,items:[]});}groups[index.get(day)].items.push(e);}
 const base=mobile?LIMIT.mobile:LIMIT.pc,max=mobile?LIMIT.mobileMax:LIMIT.pcMax;
 const drawn=groups.slice(0,base),more=groups.slice(base);
 for(const g of more)if(extra.has(g.day)&&drawn.length<max)drawn.push(g);
 return{drawn,more,max};
}
function periodTime(period,frequency){
 if(frequency==='M')return Date.UTC(Number(period.slice(0,4)),Number(period.slice(5,7))-1,1);
 if(frequency==='Q')return Date.UTC(Number(period.slice(0,4)),(Number(period[5])-1)*3,1);
 return Date.parse(period+'T00:00:00Z');
}
const fmtTime=t=>typeof t==='string'?t.slice(0,16).replace('T',' ')+' UTC':'—';
function fmtNum(v){if(typeof v!=='number'||!Number.isFinite(v))return'—';const a=Math.abs(v);return a>=1000?Math.round(v).toLocaleString('en-US'):a>=100?v.toFixed(1):v.toFixed(2);}
function eventLabel(p,e){const ind=byId(p,e.indicator),edge=ind&&ind.edges[e.direction];const base=edge?edge.label:e.direction;return e.kind==='REVISION_CLEARED'?'수정 발표로 조건 해제: '+base:e.cause==='REVISION'?'수정 발표로 조건 성립: '+base:base;}
function basisLabel(b,rd){return b==='SOURCE_LAST_MODIFIED'?'발표 시각(게시 파일 시각)':'수집 시각 기준'+(rd?' · 기관 발표일 '+rd+'(시각 미상)':'');}

// ------------------------------------------------------------------ rendering
function el(tag,attrs={},text){const n=document.createElement(tag);for(const[k,v]of Object.entries(attrs))if(v!==undefined&&v!==null&&v!==false)n.setAttribute(k,v===true?'':String(v));if(text!==undefined)n.textContent=text;return n;}
const NS='http://www.w3.org/2000/svg';
function svg(tag,attrs={},text){const n=document.createElementNS(NS,tag);for(const[k,v]of Object.entries(attrs))n.setAttribute(k,String(v));if(text!==undefined)n.textContent=text;return n;}
function graph(p,ind,sid,lines,replay,width){
 const row=p.series[sid],W=Math.max(280,Math.min(900,width)),H=220,L=44,R=10,T=14,B=34;
 const obs=row.obs;
 // No observation -> no chart at all (never an empty or invented graph).
 if(!obs.length)return el('p',{class:'small me-empty','data-me-no-obs':sid},'관측 자료 없음 · NOT_AVAILABLE · '+(REASON[row.reason]||row.reason||'—'));
 const box=svg('svg',{viewBox:`0 0 ${W} ${H}`,width:'100%',height:H,role:'img','aria-label':ind.name+' 관측 그래프','data-me-svg':sid,class:'me-svg'});
 const xs=obs.map(o=>periodTime(o[0],row.frequency)),ys=obs.map(o=>o[1]);
 const times=xs.concat(lines.map(g=>Date.parse(g.at)),(p.releases||[]).filter(r=>r.series===sid).map(r=>Date.parse(r.at)));
 let x0=Math.min(...xs),x1=Math.max(...times);if(x1<=x0)x1=x0+864e5;
 let y0=Math.min(...ys),y1=Math.max(...ys);if(ind.id==='E09'||ind.id==='E36'||ind.id==='E25'){y0=Math.min(y0,0);y1=Math.max(y1,0);}if(y1-y0<1e-9){y0-=1;y1+=1;}const pad=(y1-y0)*0.08;y0-=pad;y1+=pad;
 const X=t=>L+(t-x0)/(x1-x0)*(W-L-R),Y=v=>T+(y1-v)/(y1-y0)*(H-T-B);
 box.append(svg('rect',{x:L,y:T,width:W-L-R,height:H-T-B,class:'me-plot'}));
 if(y0<0&&y1>0)box.append(svg('line',{x1:L,x2:W-R,y1:Y(0),y2:Y(0),class:'me-zero'}));
 const pts=[];obs.forEach((o,i)=>{if(ind.id==='E40'&&i>0)pts.push(X(xs[i]).toFixed(1)+','+Y(obs[i-1][1]).toFixed(1));pts.push(X(xs[i]).toFixed(1)+','+Y(o[1]).toFixed(1));});
 box.append(svg('polyline',{points:pts.join(' '),class:'me-series','data-me-series':sid}));
 for(const [period,versions] of Object.entries(row.history||{})){
  if(!versions.some(v=>v.kind==='REVISION'))continue;const i=obs.findIndex(o=>o[0]===period);if(i<0)continue;
  const c=svg('circle',{cx:X(xs[i]),cy:Y(obs[i][1]),r:4,class:'me-revision','data-me-revision':period});
  c.append(svg('title',{},period+' · '+versions.map(v=>({BASELINE:'수집 시작값 ',FIRST:'최초 발표 ',REVISION:'수정 '}[v.kind])+fmtNum(v.v)+' ('+fmtTime(v.at)+')').join(' → ')));box.append(c);
 }
 for(const r of (p.releases||[]).filter(r=>r.series===sid)){const x=X(Date.parse(r.at));
  const tick=svg('path',{d:r.kind==='FIRST'?`M${x-3} ${H-B+9} L${x+3} ${H-B+9} L${x} ${H-B+3} Z`:`M${x} ${H-B+2} L${x+3} ${H-B+6} L${x} ${H-B+10} L${x-3} ${H-B+6} Z`,class:'me-release me-release-'+r.kind.toLowerCase(),'data-me-release':r.kind});
  tick.append(svg('title',{},(r.kind==='FIRST'?'최초 발표 ':'수정 발표 ')+r.period+' · '+fmtTime(r.at)+' · '+basisLabel(r.basis,r.rd)));box.append(tick);}
 if(replay)for(const e of replay){const x=X(periodTime(e.period,row.frequency));const ln=svg('line',{x1:x,x2:x,y1:T,y2:H-B,class:'me-line me-line-replay','data-me-replay-line':e.period});ln.append(svg('title',{},'재구성 · '+e.period+' · '+(ind.edges[e.direction]||{}).label+' · 수정치 기준 · 발표 시각 아님'));box.append(ln);}
 lines.forEach((g,k)=>{const x=X(Date.parse(g.at)),collection=g.items.every(e=>e.basis==='COLLECTION_TIME');
  const ln=svg('line',{x1:x,x2:x,y1:T,y2:H-B,class:'me-line '+(collection?'me-line-collection':'me-line-release'),'data-me-line':g.day,'data-me-line-count':g.items.length,'data-me-line-basis':collection?'COLLECTION_TIME':'SOURCE_LAST_MODIFIED'});
  ln.append(svg('title',{},g.items.map(e=>eventLabel(p,e)+' · '+fmtTime(e.at)+' · '+basisLabel(e.basis,e.rd)).join('\n')));box.append(ln);
  box.append(svg('text',{x:x+2,y:T+10+(k%3)*11,class:'me-line-label'},String(k+1)+(g.items.length>1?' ×'+g.items.length:'')));});
 box.append(svg('text',{x:L,y:H-6,class:'me-axis'},obs[0][0]),svg('text',{x:W-R,y:H-6,class:'me-axis me-axis-end'},new Date(x1).toISOString().slice(0,10)));
 box.append(svg('text',{x:L-4,y:T+8,class:'me-axis me-axis-end'},fmtNum(y1-pad)),svg('text',{x:L-4,y:H-B,class:'me-axis me-axis-end'},fmtNum(y0+pad)));
 return box;
}
function metaBlock(p,ind){
 const s=ind.source,d=el('dl',{class:'me-meta','data-me-meta':ind.id});
 const add=(k,v,attr)=>{d.append(el('dt',{},k),el('dd',attr||{},v));};
 add('출처',s.source+' · '+s.agency);add('공식 통계',s.official_statistic?'예':'아니오');add('규칙 (v0 · 미검증)',ind.rule.text+' '+(RULE_SOURCE[ind.rule.source_class]||''));
 add('실시간 검증',(VALIDATION[ind.rule.realtime_validation]||'')+' · 이 시스템 안에서는 미검증');add('라이선스',s.license_class+' · 약관 확인 '+s.terms_checked_on);
 add('약관 메모',s.terms_note);add('공개',s.publication==='PUBLIC'?'공개 가능':'공개 보류(약관 원문 미확인)',{'data-me-publication':s.publication});
 const interp=Object.entries(ind.edges).map(([k,e])=>(k==='up'?'↑ ':'↓ ')+e.label+' → '+e.interpretation).join(' / ');
 add('해석 후보 · 미승인',interp,{'data-me-interpretation':''});
 return d;
}
function mount(host,{locale,view=globalThis}={}){
 if(!host)return null;
 const ui={cycle:'economy',indicator:null,replay:false,extra:new Set()};
 const root=el('section',{class:'card macro-evidence','data-macro-evidence':''});host.replaceChildren(root);
 const paint=()=>{
  const p=S.payload;root.replaceChildren();root.setAttribute('data-macro-evidence-status',S.status);
  root.append(el('h2',{},'근거 지표 · 관측 그래프'));
  const chips=el('p',{class:'chips me-badges'});chips.append(el('span',{class:'badge','data-me-scope':''},'탐색 화면 전용 · 공식 판정·확률·매크로 게이트에 쓰지 않음'),el('span',{class:'badge','data-me-interp-label':''},'해석 후보 · 미승인'),el('span',{class:'badge'},'v0 · 미검증'));root.append(chips);
  root.append(el('p',{class:'small','data-me-panel':'observation'},'관측 그래프 · 실제 자료 (사이클 개념도가 아님). 세로선은 발표 시각에, 발표 시각을 모르면 수집 시각에 그리고 그렇게 표시합니다.'));
  if(!p){root.append(el('p',{'data-me-unavailable':''},S.status==='NOT_LOADED'?'불러오는 중':'근거 지표 자료 없음 (NOT_AVAILABLE)'));return;}
  if(p.generated_at===null)root.append(el('p',{class:'small','data-me-not-collected':''},'아직 수집 전입니다. 매일 실행에서 공식 통계를 모으면 표시됩니다.'));
  else root.append(el('p',{class:'small','data-me-collection':''},'수집 시작 '+fmtTime(p.collection_started_at)+' · 최근 생성 '+fmtTime(p.generated_at)+(p.continuity==='RESET_PREVIOUS_UNAVAILABLE'?' · 이전 기록을 읽지 못해 새로 시작':'')));
  const tabs=el('div',{class:'chips screen-tabs me-tabs',role:'tablist','aria-label':'사이클'});
  for(const[c,label]of TABS){const b=el('button',{type:'button',role:'tab','data-me-tab':c,'aria-selected':String(ui.cycle===c),class:'chip'+(ui.cycle===c?' active':'')},label);b.addEventListener('click',()=>{ui.cycle=c;ui.indicator=null;ui.extra.clear();paint();});tabs.append(b);}
  root.append(tabs);
  const sum=summary(p,ui.cycle),box=el('div',{class:'me-summary','data-me-summary':ui.cycle});
  box.append(el('p',{'data-me-summary-counts':''},'유효 경고 '+sum.warning.length+'계열 · 유효 개선 '+sum.improving.length+'계열'+(sum.mixed.length?' · 엇갈림 '+sum.mixed.length+'계열':'')));
  const names=a=>a.map(f=>FAMILY[f]||f).join(', ')||'없음';
  box.append(el('p',{class:'small','data-me-summary-families':''},'경고: '+names(sum.warning)+' · 개선: '+names(sum.improving)+(sum.mixed.length?' · 엇갈림: '+names(sum.mixed):'')));
  box.append(el('p',{class:'small'},sum.label+' · 현재 빈티지 기준 · 사이클별 따로 셈 (한 계열은 1개)'));
  if(ui.cycle==='market')box.append(el('p',{class:'small','data-me-market-note':''},p.labels.market_price));
  root.append(box);
  const inds=cycleIndicators(p,ui.cycle);if(!ui.indicator||!inds.some(i=>i.id===ui.indicator))ui.indicator=(inds.find(i=>i.state!=='NOT_AVAILABLE')||inds[0]||{}).id;
  const ind=byId(p,ui.indicator);
  const pick=el('select',{'data-me-indicator':'','aria-label':'근거 지표'});for(const i of inds){const o=el('option',{value:i.id},i.id+' · '+i.name+(i.state==='NOT_AVAILABLE'?' (자료 없음)':''));if(i.id===ui.indicator)o.selected=true;pick.append(o);}
  pick.addEventListener('change',()=>{ui.indicator=pick.value;ui.extra.clear();paint();});
  const pl=el('label',{class:'me-pick'},'지표 ');pl.append(pick);root.append(pl);
  if(!ind)return;
  const mobile=(root.clientWidth||host.clientWidth||view.innerWidth||1280)<MOBILE_PX;
  const list=events({indicator:ind.id},p),groups=lineGroups(list,{mobile,extra:ui.extra});
  const replay=ui.replay?events({indicator:ind.id,layer:'REPLAY'},p):null;
  for(const sid of ind.series){
   const row=p.series[sid],fig=el('figure',{class:'me-figure','data-me-figure':sid});
   fig.append(graph(p,ind,sid,groups.drawn.map(g=>({day:g.day,at:g.at,items:g.items.filter(e=>e.series===sid)})).filter(g=>g.items.length),replay&&replay.filter(e=>e.series===sid),root.clientWidth||360));
   const last=row.obs[row.obs.length-1];
   fig.append(el('figcaption',{class:'small','data-me-caption':sid},sid+' · '+(row.state==='LIVE'?'최신 '+(last?last[0]+' = '+fmtNum(last[1])+' '+ind.unit:'—')+(row.delayed?' · 자료 지연':''):'NOT_AVAILABLE · '+(REASON[row.reason]||row.reason))+(row.release_evidence&&row.release_evidence.date?' · 기관 발표일 '+row.release_evidence.date:'')));
   root.append(fig);
  }
  const legend=el('p',{class:'small me-legend'},'실선 = 발표 시각 · 점선 = 수집 시각 기준 · ▲ 최초 발표 기록 · ◆ 수정 발표 기록 · ○ 수정된 관측');root.append(legend);
  const more=el('div',{'data-me-more':String(groups.more.length)});
  if(groups.more.length){const d=el('details',{});d.append(el('summary',{},'더 보기 ('+groups.more.length+')'));
   for(const g of groups.more){const lab=el('label',{class:'me-more-item'});const cb=el('input',{type:'checkbox','data-me-more-line':g.day});cb.checked=ui.extra.has(g.day);
    cb.addEventListener('change',()=>{if(cb.checked)ui.extra.add(g.day);else ui.extra.delete(g.day);paint();});lab.append(cb,document.createTextNode(' '+g.day+' · '+g.items.map(e=>eventLabel(p,e)).join(', ')));d.append(lab);}
   d.append(el('p',{class:'small'},'선은 최대 '+groups.max+'개까지 켭니다.'));more.append(d);}
  root.append(more);
  const rl=el('label',{class:'me-replay-toggle'});const rc=el('input',{type:'checkbox','data-me-replay':''});rc.checked=ui.replay;rc.addEventListener('change',()=>{ui.replay=rc.checked;paint();});
  rl.append(rc,document.createTextNode(' 재구성 층 보기 ('+p.labels.replay+')'));root.append(rl);
  root.append(metaBlock(p,ind));
  root.append(el('h3',{},'발생 사건 목록 (실시간 기록)'));
  const evs=events({cycle:ui.cycle},p),ul=el('ul',{class:'me-events','data-me-events':ui.cycle});
  if(!evs.length)ul.append(el('li',{class:'small','data-me-no-events':''},'실시간 기록 사건 없음'+(p.collection_started_at?' · 수집 시작 '+fmtTime(p.collection_started_at)+' 이후만 기록 (과거로 채우지 않음)':'')));
  for(const e of evs){const ie=byId(p,e.indicator),edge=ie.edges[e.direction]||{};
   ul.append(el('li',{'data-me-event':e.id,'data-me-event-basis':e.basis},fmtTime(e.at)+' · '+e.indicator+' '+eventLabel(p,e)+' · 기준 기간 '+e.period+' · '+basisLabel(e.basis,e.rd)+' · '+e.rule+' · 해석 후보 · 미승인: '+(edge.interpretation||'—')));}
  root.append(ul);
  const cat=el('details',{'data-me-catalog':''});cat.append(el('summary',{},'지표 목록 (P1 13 · 카탈로그, 발생 사건과 별개)'));
  const t=el('table',{class:'me-table'});const head=el('tr');for(const h of['지표','계열','사이클','상태','공식','라이선스','공개'])head.append(el('th',{},h));t.append(head);
  for(const i of p.indicators){const tr=el('tr',{'data-me-catalog-row':i.id,'data-me-catalog-state':i.state});
   for(const v of[i.id+' '+i.name,FAMILY[i.family]||i.family,i.cycles.map(c=>(TABS.find(x=>x[0]===c)||[c,c])[1]).join('·'),i.state==='LIVE'?'수집됨':i.state==='PARTIAL'?'일부 · '+(REASON[i.reason]||i.reason):'NOT_AVAILABLE · '+(REASON[i.reason]||i.reason),i.source.official_statistic?'Y':'N',i.source.license_class,i.source.publication==='PUBLIC'?'공개':'보류'])tr.append(el('td',{},v));t.append(tr);}
  cat.append(t);root.append(cat);
 };
 const off=subscribe(()=>{if(root.isConnected)paint();else off();});
 paint();
 if(S.status==='NOT_LOADED')void load(view);
 return{paint,state:ui};
}
return Object.freeze({FILENAME,SCHEMA,TABS,LIMIT,validate,load,setPayload,current,events,summary,subscribe,lineGroups,periodTime,mount});
});
