/* Feature 4 · 매크로 (spec v1.0 4.1–4.6 · menu 3 · route #/macro; boards Macro · MMacro · add/MacroPhase · add/MacroMore), the part
   that runs after IS2.ready. screen-macro.js draws the first-paint skeleton (head, legend band, sections 3-1..3-6 with a loading
   line) and hands its slots to IS2.macroLive.screen(route, refs) from this file (loader.js LOAD_ORDER, after the layer); nothing
   here touches the layer while the file loads. Every block that needs the public files says 불러오는 중 until IS2.data.ready()
   resolves, then fills in place (route.signal drops the late fill of a page that was left; a public refresh repaints with the
   view state kept).
   - Reads nothing of its own: the CORE generation through IS2.data.ready() (web_app_data_layer_browser_test.js MACRO_READS).
     macro-screen.json -> MacroLights.merge / MacroLights.render (the old renderer: text nodes only, no load button), its 8×6 cells
     and raw axis values; macro-evidence.json -> MacroEvidence.summary / events / TABS / LIMIT (the old reader's own functions on
     the payload the layer validated); sec-qgv2.json industry_group values (MacroCycleRing groupsOf rule, macro-cycle-ring.js:184)
     named by company-classification.json industry_config. A file that did not read shows its own words (IS2.data.state(name).text)
     and the other parts stay (partial failure).
   - Not computed today and shown as 준비 중 with what is missing, never a position, arc, point or probability: the official
     economy / market regime (no published model output: 공식 국면 미산출), the 순환매 position, the SIC industry-cycle position,
     the transition-frequency probabilities and 나비효과 (no path engine; relationship source REL-SOURCE undecided).
   - 4.1 device quote (table 1-3 "기기: 클릭 시 SPY·HYG·IEF 시세"): before a click the lights are the public state as before. The
     button asks the layer's one display member, IS2.prices.quote(), for SPY · HYG · IEF after the click-only device read
     IS2.prices.readUniverse(event) (the action gate's UNIVERSE_READ: the user's own price sheet, RAM only) when this page has not
     read it yet. The values show as text inside [data-ram-price] only, labelled as this device's quote (not a public value), and
     live in this render's RAM (never stored, logged or sent; not used by the lights). Not signed in / no price sheet / no value:
     the layer's reason words (IS2.qgv.reasonText), never a number.
   - 3.4 내가 고르는 현재 위치 (4.4): kept on this device through IS2.store.macroEstimates (MacroCycleRing's own key and schema
     macro-cycle-user-estimate/2, backup /5): read at every draw, written only inside the record / delete click (the gate refuses
     a write outside a click), so a record survives a reload.
   - Private additions (table 1-3, proposals): one IS2.parts.privatePanel each for 4.1 (macro-market-credit) and 4.2
     (macro-sector-rs); they stay NOT_READY and send or store nothing; the public part never waits for them.
   - View state (cycle, viewed cell, evidence tab, chosen group, chosen ring) lives in this module; quotes live in the render. */
(function(){
'use strict';
const I=window.IS2,{h,href,parts:{mascot}}=I;
const MS='macro-screen.json',ME='macro-evidence.json',QGV2='sec-qgv2.json',CLS='company-classification.json';
// macro-cycle-ring.js:24 PARTS (IA-4 8칸, PM-1 결정 대기); MacroCycleRing.parseUserExport refuses any other part.
const PARTS=Object.freeze(['초입','후반']);
const RING_KO={economy:'경기',market:'주식시장',industry:'업종 그룹'};
// Display words of macro-evidence.js FAMILY / RULE_SOURCE / REASON (the module does not export them).
const FAMILY={C:'금리곡선',LU:'실업·청구',LD:'노동 수요 선행',MO:'제조 주문',PO:'생산·산출',HO:'주택',BK:'은행 대출',IN:'물가',PL:'정책금리',T:'운송'};
const RULE_SOURCE={LITERATURE:'[문헌]',PROPOSAL:'[제안]',LITERATURE_UP_PROPOSAL_DOWN:'[문헌] 상향 · [제안] 하향',AGENCY_EVENT:'[기관 사건]'};
const REASON={SOURCE_NOT_COLLECTED:'수집 전',SOURCE_NOT_AVAILABLE:'출처 응답 없음',SOURCE_KEY_NOT_CONFIGURED:'API 키 미설정',TERMS_UNVERIFIED:'약관 원문 미확인 · 공개 보류',
 SCHEMA_MISMATCH:'형식 불일치',SERIES_NOT_FOUND:'계열 없음',MISSING_SOURCE:'값 없음',PROVIDER_ERROR:'출처 오류 응답',INSUFFICIENT_HISTORY:'이력 부족'};
const V={cycle:'economy',view:{economy:0,market:0},ev:null,group:'',ring:'economy',node:'data'};
const obj=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
// replaceChildren would write "null" for a part that is not there: core append skips null / false.
const put=(box,...c)=>{box.replaceChildren();I.append(box,c);return box;};
const utc=t=>typeof t==='string'&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(t)?t.slice(0,10)+' '+t.slice(11,16)+' UTC':'—';
const phone=()=>{try{return window.matchMedia('(max-width:720px)').matches;}catch(_){return false;}};
const pct=v=>(Number(v)*100).toFixed(2)+'%';
const loading=what=>h('p',{class:'pending',role:'status',dataset:{state:'loading'}},'불러오는 중 · ',what);
const failed=(code,text)=>h('div',{class:'sk state-card',dataset:{state:'error',na:code}},mascot('alarm'),h('p',{class:'err'},text));
const empty=(code,text)=>h('div',{class:'sk state-card',dataset:{state:'empty',na:code}},mascot('plain'),h('p',null,text));
// An unfinished model: 준비 중, what it would show, what is missing. The common base's parts.notReady when it is there (same words).
const prep=(what,missing)=>{const t='준비 중 · '+what,n=typeof I.parts.notReady==='function'?I.parts.notReady(t,missing):h('p',{class:'pending',dataset:{notReady:''}},t,' · 없는 것: ',missing.join(' · '));n.dataset.prep='';return n;};
const sub=(title,fn,hand)=>h('div',{class:'lb-head'},h('h3',{class:'stamp sub'},title),fn?h('span',{class:'meta'},'기능 ',fn):null,hand?h('span',{class:'hand'},hand):null);
const block=(id,...c)=>h('div',{class:'sk card',dataset:{block:id}},...c);
const dl=rows=>h('dl',{class:'card-body'},rows.map(([k,v,attrs])=>[h('dt',null,h('b',null,k)),h('dd',attrs||null,v)]));
const conds=()=>h('ul',{class:'news-lines',dataset:{conds:''}},[['▲ 상향','up'],['● 유지','hold'],['▼ 하향','down']].map(([t,k])=>h('li',{dataset:{cond:k}},t,' · 기준 미정 (PM-3)')));
const prob=()=>h('div',{dataset:{prob:'NOT_COMPUTED'}},h('p',null,'확률 미산출 · 근거 = 과거 국면 전환 빈도 (결정됨) · Lab 검증 전에는 숫자를 쓰지 않음'),
 dl([['비율','—',{dataset:{na:'NOT_COMPUTED'}}],['기간','—',{dataset:{na:'NOT_COMPUTED'}}],['표본 수','—',{dataset:{na:'NOT_COMPUTED'}}]]));
const fileState=n=>{try{return I.data.state(n);}catch(_){return{state:'FAILED',text:''};}};
// A file that did not read: its own words (data.js state text), never the empty state's words.
function fileFail(n,what){const s=fileState(n);
 return s.state==='NOT_PUBLISHED'?failed('NOT_PUBLISHED',what+' 파일이 아직 게시되지 않았습니다 · '+(s.text||n)):failed('READ_FAILED',what+' 파일을 읽지 못했습니다 · '+(s.text||n));}
const models=()=>window.MacroCycleRing&&window.MacroCycleRing.MODELS;
const cellsOf=cyc=>models()[cyc].phases.flatMap(phase=>PARTS.map(part=>({phase,part,label:phase+' '+part})));
const span=(a,b)=>a.phase===b.phase&&a.part===b.part?a.phase+' '+a.part:a.phase+' '+a.part+' ~ '+b.phase+' '+b.part;
const keyName=k=>{if(!k.startsWith('industry:'))return RING_KO[k];const g=k.slice(9),x=groups().find(y=>y.id===g);return '업종 그룹 · '+(x&&x.name?x.name:g);};
// This device's records (IS2.store.macroEstimates): {state, rings:{<ring key>:[entry, oldest first]}}, read at every draw.
function stored(){let r=null;try{r=I.store.macroEstimates.read();}catch(_){r=null;}return r&&(r.state==='OK'||r.state==='EMPTY')&&r.value?{state:r.state,rings:r.value.rings}:{state:'INVALID',rings:{}};}
const latest=k=>{const l=stored().rings[k]||[];return l.length?{key:k,entry:l[l.length-1]}:null;};
const errCode=e=>{const m=e&&typeof e.message==='string'?e.message.split(' ')[0]:'';return /^[A-Z][A-Z0-9_]{2,60}$/.test(m)?m:'FAILED';};
// A layer code in the layer's words (IS2.qgv.reasonText; QgvScores words the codes it knows), else the fallback; never a code alone.
function say(c,fb){const S=window.QgvScores;if(typeof c!=='string'||!c||!S)return fb;let t;try{t=I.qgv.reasonText(c);}catch(_){return fb;}return Object.hasOwn(S.REASON,c)||t!==S.reasonText(c)?t:fb;}

/* ---------------------------------------------------------------- 3.1 ring (4.1.1 · 4.1.2): concept diagram only */
const C=150,pt=(r,deg)=>{const t=(deg-90)*Math.PI/180;return[(C+r*Math.cos(t)).toFixed(2),(C+r*Math.sin(t)).toFixed(2)];};
// macro-cycle-ring.js:114 band (same geometry): an annular sector between radii r0 < r1 from a0 to a1 degrees clockwise from 12.
function band(r0,r1,a0,a1){if(a1-a0>=359.99)return band(r0,r1,a0,a0+180)+' '+band(r0,r1,a0+180,a0+360);
 const L=a1-a0>180?1:0,[x0,y0]=pt(r1,a0),[x1,y1]=pt(r1,a1),[x2,y2]=pt(r0,a1),[x3,y3]=pt(r0,a0);
 return 'M'+x0+' '+y0+' A'+r1+' '+r1+' 0 '+L+' 1 '+x1+' '+y1+' L'+x2+' '+y2+' A'+r0+' '+r0+' 0 '+L+' 0 '+x3+' '+y3+' Z';}
// Cell k of n (phase k>>1, part k&1) spans [(k−1)·s, k·s] with s = 360/n: phase 0 sits at 12 o'clock as in the old ring.
function ringSvg(cyc,cur,onPick){
 const cl=cellsOf(cyc),n=cl.length,s=360/n,u=latest(cyc),g=[];
 cl.forEach((c,k)=>{const on=k===cur,[x,y]=pt(99,(k-0.5)*s);
  g.push(h('svg:path',{d:band(70,128,(k-1)*s+0.6,k*s-0.6),fill:on?'#FFE45C':'#ffffff',stroke:'#161616','stroke-width':on?'3.5':'1.5',dataset:{cell:String(k)},onclick:()=>onPick(k,null)}),
   h('svg:text',{'pointer-events':'none',x,y:(Number(y)-3).toFixed(2),'text-anchor':'middle','font-size':'11',fill:'#161616'},c.phase),h('svg:text',{'pointer-events':'none',x,y:(Number(y)+10).toFixed(2),'text-anchor':'middle','font-size':'10',fill:'#5c5c5c'},c.part));});
 if(u){const a=cl.findIndex(c=>c.phase===u.entry.from.phase&&c.part===u.entry.from.part),b=cl.findIndex(c=>c.phase===u.entry.to.phase&&c.part===u.entry.to.part);
  if(a>=0&&b>=0){const a0=(a-1)*s;let a1=b*s;while(a1<=a0)a1+=360;
   g.push(h('svg:path',{d:band(56,64,a0,Math.min(a1,a0+360)),fill:'none',stroke:'#7A4CC2','stroke-width':'2','stroke-dasharray':'5 4',dataset:{userArc:span(u.entry.from,u.entry.to)}}));}}
 g.push(h('svg:text',{'pointer-events':'none',x:'150',y:'146','text-anchor':'middle','font-size':'12',fill:'#5c5c5c'},'보는 칸'),h('svg:text',{'pointer-events':'none',x:'150',y:'164','text-anchor':'middle','font-size':'14',fill:'#161616',dataset:{center:''}},cl[cur].label));
 return h('svg:svg',{viewBox:'0 0 300 300',width:'280',height:'280',role:'img',focusable:'false',dataset:{ring:cyc},
  'aria-label':RING_KO[cyc]+' 국면 개념도 · '+n+'칸 · 보는 칸 '+cl[cur].label+'('+(cur+1)+'/'+n+') · 공식 판정 미산출'+(u?' · 내 추정 '+span(u.entry.from,u.entry.to)+' (공식 판정 아님)':'')},g);}
// A roving tablist (arrows, Home, End); pick(i) redraws and gives the chosen tab the focus (a click or Enter keeps the user there).
function tablist(label,items,cur,pick,key){
 const pre=key.replace(/[A-Z]/g,m=>'-'+m.toLowerCase());
 const el=h('div',{role:'tablist','aria-label':label,class:'scroll'},items.map(([id,text],i)=>h('button',{type:'button',role:'tab',id:pre+'-'+id,class:'chip'+(i===cur?' on':''),'aria-selected':String(i===cur),tabindex:i===cur?'0':'-1',dataset:{[key]:id},onclick:()=>pick(i,false)},text)));
 el.addEventListener('keydown',e=>{const n=items.length;let j=null;if(e.key==='ArrowRight'||e.key==='ArrowDown')j=(cur+1)%n;else if(e.key==='ArrowLeft'||e.key==='ArrowUp')j=(cur+n-1)%n;else if(e.key==='Home')j=0;else if(e.key==='End')j=n-1;
  if(j!==null){e.preventDefault();pick(j,true);}});
 return el;}
const focusLater=(root,sel)=>{const x=root.querySelector(sel);if(x)x.focus();};
function ringBlock(box){
 const cyc=V.cycle,cl=cellsOf(cyc),n=cl.length,cur=V.view[cyc],live=h('p',{class:'sr-only',role:'status','aria-live':'polite',dataset:{ringLive:''}});
 const redraw=(sel,msg)=>{ringBlock(box);if(sel)focusLater(box,sel);if(msg){const l=box.querySelector('[data-ring-live]');if(l)l.textContent=msg;}};
 const go=(k,focus)=>{const before=V.view[cyc];V.view[cyc]=(k+n)%n;const f=V.view[cyc];
  const msg=k===n&&before===n-1?cl[before].label+' 다음은 '+cl[f].label+' · 처음으로':k===-1&&before===0?cl[before].label+' 이전은 '+cl[f].label+' · 마지막으로':'보는 칸 '+cl[f].label+' ('+(f+1)+'/'+n+')';
  redraw(focus==='tab'?'[data-cell-tab="'+f+'"]':focus==='prev'?'[data-cell-prev]':focus==='next'?'[data-cell-next]':null,msg);};
 const cycles=[['economy','경기'],['market','주식시장']];
 const panel=h('div',{role:'tabpanel',id:'macro-cell-panel','aria-labelledby':'cell-tab-'+cur,tabindex:'0',class:'card-body',dataset:{cellPanel:cl[cur].label}},
  h('h4',null,cl[cur].label,' · ',String(cur+1),'/',String(n),' · 추정 구간 없음 (미산출)'),
  h('p',{class:'reason'},'굵은 테두리 = 보는 칸 (판정 위치 아님) · 넘기기는 보는 칸만 바꿈 · 마지막 칸 다음은 처음 칸'),
  h('p',null,h('b',null,'근거 패턴 · 전환 조건'),' · 초안 해석 후보 (미승인) · 이 화면에는 문구 연결 전'),
  h('p',null,h('b',null,'조정 조건')),conds(),h('p',null,h('b',null,'전환 확률')),prob());
 put(box,sub('국면 그래프 · 국면 탐색','4.1.1 · 4.1.2','개념도 · 국면 순서 · 칸 길이는 기간이 아님'),
  tablist('사이클 선택',cycles,cycles.findIndex(c=>c[0]===cyc),i=>{V.cycle=cycles[i][0];V.ev=null;redraw('[data-ring-tab="'+V.cycle+'"]','사이클 '+cycles[i][1]);paintEvidence();},'ringTab'),
  h('div',{class:'card-body',dataset:{official:'NOT_COMPUTED'}},
   h('p',null,h('b',null,'공식 판정: 미산출'),' · 게시된 모델 출력 없음 ',h('span',{class:'dash'},'NO_MODEL_OUTPUT')),
   h('p',{dataset:{probability:'NOT_COMPUTED'}},'확률 미산출 · 링 위 점 좌표 없음'),
   cyc==='market'?h('p',{class:'reason'},'모델이 생기면 공개 기본값 = 판정 유보 · 공개 근거 부족 · 가격 근거는 이 기기에서만'):null),
  // PC: the ring and its controls left, the viewed cell's panel right (grid-2 is one column on a phone).
  h('div',{class:'grid-2'},h('div',{class:'card-body'},
   h('figure',{class:'card-body'},ringSvg(cyc,cur,go),h('figcaption',{class:'reason'},'바깥 띠 = 게시된 추정 구간 (있을 때만 · 지금 없음) · 안쪽 보라 점선 = 내 추정 (3.4 · 공식 판정 아님)')),
   h('div',{class:'scroll'},h('button',{type:'button',class:'btn','aria-label':'이전 칸',dataset:{cellPrev:''},onclick:()=>go(V.view[cyc]-1,'prev')},'◀'),
    h('button',{type:'button',class:'btn','aria-label':'다음 칸',dataset:{cellNext:''},onclick:()=>go(V.view[cyc]+1,'next')},'▶'),
    h('span',{dataset:{viewing:''}},'보는 칸: ',cl[cur].label)),
   tablist(RING_KO[cyc]+' 국면 칸',cl.map((c,k)=>[String(k),c.label]),cur,i=>go(i,'tab'),'cellTab'),
   h('p',{class:'reason'},'순환은 둘러보기 순서일 뿐 · 실제 경기·시장이 이 순서로만 움직이지 않음 · 국면은 건너뛰거나 되돌아갈 수 있음')),panel),live);
 box.querySelectorAll('[data-cell-tab]').forEach(b=>b.setAttribute('aria-controls','macro-cell-panel'));}

/* ---------------------------------------------------------------- 3.1 evidence lines (4.1.3): exploration only */
const edgeOf=(p,e)=>{const i=p.indicators.find(x=>x.id===e.indicator);return{ind:i,edge:i&&i.edges[e.direction]};};
// macro-evidence.js eventLabel / basisLabel (not exported): the event's own words.
function eventLabel(p,e){const{edge}=edgeOf(p,e),base=edge?edge.label:e.direction;return e.kind==='REVISION_CLEARED'?'수정 발표로 조건 해제: '+base:e.cause==='REVISION'?'수정 발표로 조건 성립: '+base:base;}
const basisLabel=(b,rd)=>b==='SOURCE_LAST_MODIFIED'?'발표 시각 (게시 파일 시각)':'수집 시각 기준'+(rd?' · 기관 발표일 '+rd+' (시각 미상)':'');
const stateText=(s,r)=>s==='LIVE'?'수집됨':(s==='PARTIAL'?'일부 수집 · ':'자료 없음 · ')+(r?r+(REASON[r]?' ('+REASON[r]+')':''):'사유 없음');
let evidenceBox=null;
function paintEvidence(){if(evidenceBox&&evidenceBox.isConnected&&evidenceBox.dataset.ready)evidenceBlock(evidenceBox);}
function evidenceBlock(box){
 box.dataset.ready='1';const top=[sub('근거 세로선 · 근거 탐색','4.1.3','탐색 전용 · 공식 판정·확률·매크로 게이트에 쓰지 않음'),
  h('p',{class:'reason',dataset:{evScope:''}},'탐색 화면 전용 · 해석 후보 · 미승인 · v0 · 미검증')];
 const s=fileState(ME),p=s.state==='OK'?I.data.get(ME):null,ME_=window.MacroEvidence;
 if(!p||!ME_){put(box,...top,s.state==='OK'?failed('READER_MISSING','근거 지표를 읽는 모듈이 없습니다'):fileFail(ME,'근거'));return;}
 const tabsList=ME_.TABS.map(([c,l])=>[c,l]),cyc=V.ev||V.cycle,ci=Math.max(0,tabsList.findIndex(t=>t[0]===cyc));
 const sum=ME_.summary(p,tabsList[ci][0]),names=a=>a.map(f=>FAMILY[f]||f).join(', ')||'없음';
 const evs=ME_.events({cycle:tabsList[ci][0]},p),N=phone()?ME_.LIMIT.mobile:ME_.LIMIT.pc;
 const line=e=>{const{ind,edge}=edgeOf(p,e);return h('li',{dataset:{event:e.id,eventBasis:e.basis}},h('b',null,utc(e.at)),' · ',e.indicator,' ',ind?ind.name:'',' · ',eventLabel(p,e),' · 기준 기간 ',e.period,' · ',basisLabel(e.basis,e.rd),' · ',e.rule,' · 해석 후보 · 미승인: ',edge?edge.interpretation:'—');};
 const held=i=>i.source.publication!=='PUBLIC'||i.reason==='TERMS_UNVERIFIED';
 const cat=h('details',{dataset:{catalog:''}},h('summary',{class:'lk'},'근거 더 보기 (전체 지표 목록 · ',String(p.indicators.length),'개)'),
  h('p',{class:'reason'},'공개 파일에 실린 지표 전부 · 이름·출처·수집 상태만 (값·국면·확률 없음) · 목록에 있다고 사건이 생긴 것은 아님 · 규칙은 모두 v0 · 미검증'),
  h('ul',{class:'news-lines'},p.indicators.map(i=>h('li',{dataset:{catalogRow:i.id,catalogState:i.state}},h('b',null,i.id,' ',i.name),' · ',stateText(i.state,i.reason),
   held(i)?' · 약관 원문 미확인 · 이름과 상태만 표시':' · '+(FAMILY[i.family]||i.family)+' · '+i.cycles.map(c=>(tabsList.find(t=>t[0]===c)||[c,c])[1]).join('·')+' · '+(RULE_SOURCE[i.rule.source_class]||i.rule.source_class)+' '+i.rule.version+' · v0 · 미검증'))));
 put(box,...top,
  p.generated_at===null?h('p',{class:'reason',dataset:{notCollected:''}},'아직 수집 전입니다 · 매일 실행에서 공식 통계를 모으면 표시됩니다')
   :h('p',{class:'reason',dataset:{collection:''}},'수집 시작 ',utc(p.collection_started_at),' · 최근 생성 ',utc(p.generated_at),p.state==='PARTIAL'?' · 일부 수집':''),
  tablist('근거 사이클',tabsList,ci,i=>{V.ev=tabsList[i][0];evidenceBlock(box);focusLater(box,'[data-ev-tab="'+V.ev+'"]');},'evTab'),
  h('div',{class:'card-body',dataset:{summary:sum.cycle}},h('p',{dataset:{summaryCounts:''}},'유효 경고 ',String(sum.warning.length),'계열 · 유효 개선 ',String(sum.improving.length),'계열',sum.mixed.length?' · 엇갈림 '+sum.mixed.length+'계열':''),
   h('p',{class:'reason'},'경고: ',names(sum.warning),' · 개선: ',names(sum.improving),sum.mixed.length?' · 엇갈림: '+names(sum.mixed):''),
   h('p',{class:'reason'},sum.label,' · 사이클별 따로 셈 · 한 계열은 1개'),sum.cycle==='market'?h('p',{class:'reason'},p.labels.market_price):null),
  h('h4',null,'발생 사건 목록 (실시간 기록)'),
  evs.length?h('ol',{class:'news-lines',dataset:{events:sum.cycle}},evs.slice(0,N).map(line)):h('p',{class:'reason',dataset:{noEvents:''}},'실시간 기록 사건 없음',p.collection_started_at?' · 수집 시작 '+utc(p.collection_started_at)+' 이후만 기록 (과거로 채우지 않음)':''),
  evs.length>N?h('details',{dataset:{eventsMore:String(evs.length-N)}},h('summary',{class:'lk'},'더 보기 (',String(evs.length-N),')'),h('ol',{class:'news-lines',start:String(N+1)},evs.slice(N).map(line))):null,
  h('p',{class:'reason'},'관측 그래프(실제 날짜 축)는 다음 단계 · 세로선은 발표 시각에, 발표 시각을 모르면 수집 시각에 긋고 그렇게 표시'),cat);}

/* ---------------------------------------------------------------- 4.1 device quote: SPY · HYG · IEF on a click only */
const SYMS=Object.freeze(['SPY','HYG','IEF']),SOURCE_KO={UNIVERSE_SHEET:'가격 시트 읽기',WORKER_CLOSE:'Worker 종가'};
const clock=t=>typeof t==='string'&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(t)?t.slice(11,16)+' UTC':'시각 미확인';
// The quotes live in this block's RAM (a repaint or leaving the route drops them); nothing is stored, logged or sent.
function quoteBlock(){
 const Q={rows:null,code:null,busy:false},list=h('ul',{class:'news-lines',dataset:{deviceQuoteList:''}}),status=h('p',{class:'reason',role:'status',dataset:{deviceQuoteStatus:''}});
 // The device price path needs the Google price sheet: its sign-in is "시트 연결 필요", never the private-area login (2층 표 1-3).
 const words=c=>c==='AUTH_REQUIRED'?'시트 연결 필요 · 구글 가격 시트':say(c,'시세를 가져오지 못했습니다');
 const btn=h('button',{type:'button',class:'btn mine',dataset:{deviceQuoteLoad:''},onclick:e=>load(e)},'SPY · HYG · IEF 기기 시세 보기 · 이 기기에서만');
 function paint(){btn.disabled=Q.busy;
  list.replaceChildren(...SYMS.map((t,i)=>{const q=Q.rows&&Q.rows[i],li=(st,...c)=>h('li',{dataset:{deviceQuoteSymbol:t,quoteState:st}},h('b',null,t),' · ',...c);
   if(Q.code)return li('NA',h('span',{dataset:{na:Q.code}},'— · ',words(Q.code)));
   if(!q)return li('BEFORE','— · 누르기 전 · 공개 화면은 가격을 보이지 않음');
   if(q.state!=='OK')return li('NA',h('span',{dataset:{na:q.reason}},'— · ',say(q.reason,'이 기기 시세 없음')));
   return li('OK',h('span',{dataset:{ramPrice:''}},String(q.price),' ',String(q.currency)),' · 이 기기 시세 · 공개 값 아님 · ',SOURCE_KO[q.source]||'이 기기 가격',' · 읽은 시각 ',clock(q.read_at));}));
  status.textContent=Q.busy?'이 기기 가격 경로로 묻는 중':Q.code?words(Q.code):Q.rows?'이 기기 시세를 이 화면에만 보였습니다 · 저장·전송 안 함 · 새로고침하면 사라짐':'';}
 const show=c=>{Q.busy=false;Q.code=c;Q.rows=null;paint();};
 // One click: the device read through the gate when this page has none yet (the event passed synchronously), then quote().
 function load(e){if(Q.busy)return;let st=null;try{st=I.prices.status();}catch(_){st=null;}
  if(!st||st.state==='NOT_READY'){show('LAYER_NOT_READY');return;}
  let read=null;
  if(!(st.universe&&st.universe.state==='READY')){
   if(!(st.google&&st.google.connected)){show('AUTH_REQUIRED');return;}
   if(!(st.universe_source&&st.universe_source.set)){show('UNIVERSE_SOURCE_NOT_SET');return;}
   try{read=I.prices.readUniverse(e);}catch(err){show(errCode(err));return;}}
  Q.busy=true;Q.code=null;Q.rows=null;paint();
  Promise.resolve(read).then(()=>Promise.all(SYMS.map(t=>I.prices.quote({ticker:t})))).then(rows=>{if(!btn.isConnected)return;Q.busy=false;Q.rows=rows;paint();},err=>{if(btn.isConnected)show(errCode(err));});}
 paint();
 return h('div',{class:'card-body',dataset:{deviceQuote:''}},h('h4',null,'기기 시세 · SPY · HYG · IEF'),
  h('p',{class:'reason'},'시장(SPY) · 신용(HYG ÷ IEF) 경고등의 기기 쪽 가격 · 누를 때만 이 기기의 가격 시트 읽기로 묻고 RAM에만 둠 · 저장·전송 안 함 · 공개 값 아님 · 위 경고등 판정에 넣지 않음'),
  btn,status,list);}

/* ---------------------------------------------------------------- 3.1 lights (4.1.4) and judgement state (4.1.5) */
function lightsBlock(box){
 const title=sub('기존 경고등 · 상태판 (참고 모드)','4.1.4','국면 링과 섞지 않음');
 if(fileState(MS).state!=='OK'){put(box,title,fileFail(MS,'경고등·상태판'),quoteBlock());return null;}
 const ML=window.MacroLights,screens=I.data.screens(),ms=I.data.get(MS);let merged=null;
 try{merged=ML.merge(screens);}catch(_){merged=null;}
 if(!merged||!obj(ms)){put(box,title,failed('LIGHTS_FAILED','경고등을 계산하지 못했습니다'),quoteBlock());return null;}
 const lb=ms.data.growth_inflation_v0,legacy=lb&&lb.engine?{state:lb.engine.state,rule_label:lb.engine.rule_label}:{state:'NOT_AVAILABLE',rule_label:null};
 const host=h('div',{dataset:{lightsHost:''}});ML.render(host,merged,{locale:'ko-KR',status:'',legacy});restyle(host);
 const d=ms.data,why=c=>c.state==='RAW_EVIDENCE'?['원자료','RAW_EVIDENCE']:c.axis==='FX'?['NA · 제외','PUBLIC_FX_EXCLUDED']:c.dimension==='Level'?['NA · 자료 없음','SOURCE_NOT_COLLECTED']:['NA · 규칙','NO_APPROVED_STATE_RULE'];
 const grid=h('details',{dataset:{board:''}},h('summary',{class:'lk'},'8축 × 6칸 상태판 · 하나로 합치지 않음'),
  h('div',{class:'tbl-wrap'},h('table',{class:'tbl'},h('caption',null,'공개 macro-screen.json · Level 칸만 원자료가 될 수 있음'),
   h('thead',null,h('tr',null,h('th',{scope:'col'},'축'),d.dimensions.map(x=>h('th',{scope:'col'},x)))),
   h('tbody',null,d.axes.map(ax=>h('tr',{dataset:{axis:ax}},h('th',{scope:'row'},ax),d.cells.filter(c=>c.axis===ax).map(c=>{const[t,code]=why(c);return h('td',{dataset:{na:code}},t);})))))),
  h('p',{class:'reason'},'NA 사유: 규칙 = NO_APPROVED_STATE_RULE (원자료 표시만 · 판정 보류) · 자료 없음 = 그 축 원자료 미수집 · 제외 = PUBLIC_FX_EXCLUDED (공개 가격 경계 밖)'));
 put(box,title,host,h('p',{class:'reason',dataset:{deviceLights:''}},'시장 · 신용 경고등은 이 기기 가격 이력이 있어야 계산합니다 · 위 판정은 공개 경고등 기준 그대로 · 아래 버튼을 누를 때만 이 기기 시세를 보여 줌 (경고등 계산에는 넣지 않음)'),quoteBlock(),grid);
 return merged;}
// The old card's classes mean other things in app.css (.badge is a padded block, .card a second frame): the same nodes and
// data attributes, re-classed to the new look; the h2 becomes an h4 under this block's h3. Nothing in the text changes.
function restyle(host){const card=host.firstElementChild;if(!card)return;card.setAttribute('class','card-body');
 const t=card.querySelector('h2');if(t)t.replaceWith(h('h4',null,t.textContent));
 for(const el of card.querySelectorAll('.badge'))el.setAttribute('class',el.classList.contains('NOT_AVAILABLE')?'dash':el.classList.contains('partial')||el.classList.contains('vt-disclaimer')?'chip err':'pill');
 for(const el of card.querySelectorAll('.small'))el.setAttribute('class','reason');for(const el of card.querySelectorAll('.list'))el.setAttribute('class','news-lines');}
const STATE_ROWS=[['근거 부족','MISSING_SOURCE · SOURCE_NOT_COLLECTED','셀 수 있는 계열이 기준 수에 닿으면'],['자료 낡음','STALE','계열의 다음 정기 발표가 수집되면'],
 ['근거 충돌 (후보)','CONFLICTING_FAMILIES','받치는 계열이 반대 계열보다 많아지면'],['구간 과대 (후보)','INTERVAL_TOO_WIDE','구간이 최대 폭 안으로 좁혀지면'],
 ['규칙 미승인','NO_APPROVED_STATE_RULE','소유자가 해석 규칙을 승인하면 (PM-4)'],['수정 직후','CONFLICTING_VINTAGE','다음 정기 발표까지 기다리면'],['시각 의문','AVAILABLE_AFTER_AS_OF','근거 시각이 판정 시각 앞으로 확인되면']];
function judgeBlock(){
 const card=(cyc,extra)=>h('div',{class:'sk card',dataset:{judge:cyc}},h('h4',null,RING_KO[cyc]),dl([['공식 판정','미산출 · 게시된 모델 출력 없음 (NO_MODEL_OUTPUT)',{dataset:{na:'NO_MODEL_OUTPUT'}}],
  ['근거 수','모델 출력 없음 · 근거 목록 없음'],['기준일','판정 시각 없음 (미산출)']]),extra);
 return block('4.1.5',sub('판단 상태','4.1.5','왜 판정이 없는지 · 무엇이 오면 풀리는지'),
  h('div',{class:'grid-2'},card('economy',h('p',{class:'reason'},'탐색 층 가설 · v0 · 미검증 · PM-2 결정 뒤에만 표시 · 지금은 없음')),
   card('market',h('p',{class:'reason'},'모델이 생기면 공개 기본값 = 판정 유보 · 공개 근거 부족 · 가격은 이 기기에서만'))),
  h('details',null,h('summary',{class:'lk'},'미판정 사유 · 쉬운 말 + 코드'),h('ul',{class:'news-lines'},STATE_ROWS.map(([a,b,c])=>h('li',null,h('b',null,a),' · ',b,' · 풀리는 때: ',c)))),
  h('ul',{class:'news-lines',dataset:{layers:''}},h('li',null,'공식 층 · 승인된 모델이 게시할 때만 · 지금 미산출'),h('li',null,'사용자 층 (3.4) · 내 판단 · 보라 점선 · 공식 층에 섞지 않음'),
   h('li',null,'탐색 층 (근거선) · v0 · 미검증 · 판정·확률·게이트에 쓰지 않음')));}

/* ---------------------------------------------------------------- 3.3 industry groups (4.3) */
function groups(){
 const p=I.data.get(QGV2),c=I.data.get(CLS),cfg=obj(c)&&obj(c.data)&&obj(c.data.industry_config)&&Array.isArray(c.data.industry_config.groups)?c.data.industry_config.groups:[];
 const out=new Set();if(obj(p)&&obj(p.records))for(const r of Object.values(p.records))if(r&&typeof r.industry_group==='string'&&r.industry_group)out.add(r.industry_group);
 const at=id=>{const i=cfg.findIndex(g=>g&&g.id===id);return i<0?cfg.length:i;},name=id=>{const g=cfg.find(x=>x&&x.id===id);return g&&typeof g.name==='string'?g.name:null;};
 return[...out].sort((a,b)=>at(a)-at(b)||(a<b?-1:a>b?1:0)).map(id=>({id,name:name(id)}));}
function industryBlock(box,onChange){
 const title=sub('산업 사이클 상태','4.3.1 · 4.3.2 · 4.3.3','산업 단위 권장안 · 결정 대기 (IA-5) · 산업 어휘 미정 (PM-7)');
 if(fileState(QGV2).state!=='OK'){put(box,title,fileFail(QGV2,'업종 그룹(sec-qgv2.json)'));return;}
 const list=groups(),gone=V.group&&!list.some(g=>g.id===V.group);
 const sel=h('select',{id:'macro-group',dataset:{group:''},onchange:e=>{V.group=e.target.value;industryBlock(box,onChange);focusLater(box,'[data-group]');onChange();}},
  h('option',{value:''},'선택 안 함'),list.map(g=>h('option',{value:g.id,selected:g.id===V.group},g.name?g.name+' ('+g.id+')':g.id)),gone?h('option',{value:V.group,selected:true,disabled:true},V.group+' · 새 게시본에 없음'):null);
 const pick=h('div',{class:'card-body'},h('label',{for:'macro-group'},'업종 그룹 (공개 sec-qgv2.json industry_group)'),sel);
 let body;
 if(!list.length)body=empty('NO_GROUP_VALUES','공개 파일에 업종 그룹 값이 없습니다');
 else if(gone)body=h('p',{class:'reason',dataset:{na:'GROUP_MISSING'}},'고른 업종 그룹이 새 게시본에 없음 · 선택은 그대로 남김');
 else if(!V.group)body=h('p',{class:'reason',dataset:{na:'NO_GROUP'}},'업종 그룹을 고르지 않음');
 else{const g=list.find(x=>x.id===V.group);
  body=h('div',{class:'sk card',dataset:{industryCard:g.id}},h('h4',null,g.name||g.id,' · 분석 대상 내 표본 집계 · 산업 전체 아님'),
   prep('미산출 · 산업 사이클 모델 없음',['산업 사이클 위치 모델','집계 계열','산업 어휘 결정 (PM-7)']),
   dl([['매출 증가율 중앙값','— · 집계 미구현',{dataset:{na:'NOT_IMPLEMENTED'}}],['재고/매출','— · 집계 미구현',{dataset:{na:'NOT_IMPLEMENTED'}}],['이익 증가 발행인 비율 (후행)','— · 집계 미구현',{dataset:{na:'NOT_IMPLEMENTED'}}],['기준일','— · 모델 없음']]),
   h('details',null,h('summary',{class:'lk'},'조건 · 반대 근거 · 확률'),conds(),h('p',{class:'reason'},'반대 근거: 엇갈림 · 합계 비율과 중앙값 방향이 다르면'),h('p',{class:'reason'},'반대 근거: 집중 · 한 발행인이 큰 몫이면 합계 비율 근거 제외'),prob()));}
 put(box,title,pick,body);}

/* ---------------------------------------------------------------- 3.4 my position (4.4): kept on this device */
// Words for a refused or failed write (the old ring's own words where it had them, macro-cycle-ring.js:21 / :352).
const SAVE_WORDS={CLICK_REQUIRED:'버튼을 직접 눌러야 저장합니다',ACTION_ALREADY_STARTED:'버튼을 직접 눌러야 저장합니다',MACRO_ESTIMATE_INVALID:'기록 형식을 확인하지 못했습니다',
 MACRO_ESTIMATES_STORAGE_INVALID:'이 기기에 저장된 추정 기록을 읽을 수 없어 덮어쓰지 않습니다 · 기존 값은 그대로입니다',
 MACRO_ESTIMATE_SAVE_FAILED:'저장 실패 · 이 브라우저 저장 공간이 가득 찼거나 쓸 수 없습니다 · 기존 기록은 그대로 두었고 이번 변경만 저장하지 않았습니다',
 MACRO_ESTIMATE_NOT_FOUND:'그 기록이 이 기기에 없습니다 · 다시 그렸습니다'};
const saveWords=c=>(SAVE_WORDS[c]||'저장 경로를 쓰지 못했습니다');
function mineBlock(box,onChange){
 const rings=[['economy','경기'],['market','주식시장'],...(V.group&&groups().some(g=>g.id===V.group)?[['industry:'+V.group,keyName('industry:'+V.group)]]:[])];
 if(!rings.some(r=>r[0]===V.ring))V.ring='economy';
 const st=stored(),cyc=V.ring.split(':')[0],cl=cellsOf(cyc),u=latest(V.ring);
 const status=h('p',{role:'status',class:'reason',dataset:{mineStatus:''}});
 const say_=t=>{const x=box.querySelector('[data-mine-status]');if(x)x.textContent=t;};
 const ringSel=h('select',{id:'mine-ring',dataset:{mineRing:''},onchange:e=>{V.ring=e.target.value;mineBlock(box,onChange);focusLater(box,'[data-mine-ring]');}},rings.map(([k,t])=>h('option',{value:k,selected:k===V.ring},t)));
 const opt=sel=>cl.map((c,k)=>h('option',{value:String(k),selected:k===sel},c.label));
 const at=r=>u?cl.findIndex(c=>c.phase===u.entry[r].phase&&c.part===u.entry[r].part):-1;
 const from=h('select',{id:'mine-from',dataset:{mineFrom:''}},opt(Math.max(0,at('from'))));
 const to=h('select',{id:'mine-to',dataset:{mineTo:''}},h('option',{value:''},'시작과 같음'),opt(u&&at('to')!==at('from')?at('to'):-1));
 const count=h('span',{class:'reason',dataset:{noteCount:''}},'0 / 200');
 const note=h('input',{id:'mine-note',type:'text',maxlength:'200',autocomplete:'off',dataset:{mineNote:''},oninput:e=>{count.textContent=e.target.value.length+' / 200';}});
 // The record click writes through the store (the gate: inside this click only); the store numbers it and stamps the time.
 const record=e=>{
  const a=cl[Number(from.value)],b=to.value===''?a:cl[Number(to.value)],key=V.ring;
  const entry={from:{phase:a.phase,part:a.part},to:{phase:b.phase,part:b.part},note:note.value.replace(/[\x00-\x1f]/g,' ').slice(0,200),
   system:{state:'NOT_COMPUTED',text:'미산출',reason:'NO_MODEL_OUTPUT',layer:null,model_id:null,as_of:null}};
  let saved;try{saved=I.store.macroEstimates.add(e,key,entry);}catch(err){say_('기록하지 않음 · '+saveWords(errCode(err)));return;}
  mineBlock(box,onChange);focusLater(box,'[data-mine-record]');say_('이 기기에 저장했습니다 · '+keyName(key)+' '+span(saved.from,saved.to));onChange();};
 // Newest first (saved_at); records of one ring keep their own order (seq).
 const rows=Object.entries(st.rings).flatMap(([key,list])=>list.map(entry=>({key,entry})))
  .sort((x,y)=>x.entry.saved_at<y.entry.saved_at?1:x.entry.saved_at>y.entry.saved_at?-1:x.key===y.key?y.entry.seq-x.entry.seq:0);
 const prev=r=>{const l=st.rings[r.key]||[],i=l.findIndex(x=>x.seq===r.entry.seq);return i>0?l[i-1]:null;};
 const del=(e,r)=>{try{I.store.macroEstimates.remove(e,r.key,r.entry.seq);}catch(err){const c=errCode(err);if(c==='MACRO_ESTIMATE_NOT_FOUND')mineBlock(box,onChange);say_('지우지 않음 · '+saveWords(c));return;}
  mineBlock(box,onChange);focusLater(box,'[data-mine-record]');say_('기록 하나를 지웠습니다');onChange();};
 const item=r=>{const p=prev(r),now=span(r.entry.from,r.entry.to),was=p?span(p.from,p.to):null;
  return h('li',{dataset:{mineEntry:r.key+':'+r.entry.seq}},h('b',null,keyName(r.key),' · ',now),' · ',utc(r.entry.saved_at),
   h('br'),h('span',{class:'reason'},'근거: ',r.entry.note||'— · 근거 안 씀',' · 그때 시스템 표시: ',r.entry.system.text||'기록 없음',' · 이전 내 기록과: ',p?(was===now?'같음':'바뀜: '+was+' → '+now):'첫 기록'),' ',
   h('button',{type:'button',class:'chip','aria-label':'이 기록 지우기 · '+keyName(r.key)+' '+now+' · '+utc(r.entry.saved_at),dataset:{mineDelete:r.key+':'+r.entry.seq},onclick:e=>del(e,r)},'지우기'));};
 put(box,sub('내 국면 판단 기록','4.4.1 · 4.4.2','사용자 추정 · 공식 판정 아님'),
  h('p',{class:'reason',dataset:{mineScope:''}},'이 기기에만 저장 · 기기 백업 /5(사용자 작성 객체 포함)에 들어감 · 어디에도 보내지 않고 점수에 쓰지 않음 · 누를 때만 저장'),
  st.state==='INVALID'?h('p',{class:'err',dataset:{na:'MACRO_ESTIMATES_STORAGE_INVALID'}},'이 기기에 저장된 추정 기록을 읽을 수 없습니다 · 덮어쓰지 않음'):null,
  h('fieldset',{class:'card-body'},h('legend',null,'사용자 추정 · 공식 판정 아님'),
   h('label',{for:'mine-ring'},'링'),ringSel,h('label',{for:'mine-from'},'시작 칸'),from,h('label',{for:'mine-to'},'끝 칸 (한 칸만 고르면 시작 = 끝)'),to,
   h('label',{for:'mine-note'},'근거 (선택 · 200자까지)'),note,count,
   h('p',{class:'reason'},'8칸 (초입 · 후반) · 초안 후보 · 결정 대기 (PM-1) · 지금 시스템: 미산출 · 공식 점·호 없음'),
   h('button',{type:'button',class:'btn solid',dataset:{mineRecord:''},onclick:record},'이 기기에 기록')),status,
  h('h4',null,'내 추정 기록 · 비교'),rows.length?h('ol',{class:'news-lines',dataset:{mineList:''}},rows.map(item)):h('p',{class:'reason',dataset:{mineEmpty:''}},'이 기기에 저장한 사용자 추정 없음'));}

/* ---------------------------------------------------------------- 3.6 tree (4.6) */
const NODES=[['data','자료','BLS · BEA · 재무부 · 연준 공개 지표 · 시장·신용 가격은 이 기기에서만','일부 연결','3-1'],['ind','지표','경고등 5 · 상태판 8×6 · 근거 지표 목록','일부 연결','3-1'],
 ['phase','국면','경기 링 · 주식시장 링','미산출','3-1'],['industry','산업','SIC 업종 그룹 · 순환매','미산출 · 결정 대기 (IA-5)','3-3'],['firm','기업 영향','나비효과 · 관계망 · QGV 업종','미연결 · 결정 대기 (REL-SOURCE)','3-5']];
function rawRows(ms){const d=ms.data,out=[];const g=d.growth_inflation_v0&&d.growth_inflation_v0.axes||{},r=d.raw_axes_v0&&d.raw_axes_v0.axes||{};
 for(const[ax,x]of[['Growth',g.Growth],['Inflation',g.Inflation],...['Labor','Monetary Policy','Liquidity','Credit','Fiscal','FX'].map(a=>[a,r[a]])]){if(!obj(x))continue;
  let v='—';if(x.state!=='NOT_AVAILABLE'){if(ax==='Growth')v=x.published_percent+'% (발표 전기비 연율)';else if(ax==='Inflation')v='지수 '+x.index_value+' (1982-84=100) · 전년동월비 '+pct(x.value);
   else if(x.value_unit==='RATIO')v=x.published_value!==null&&/PERCENT/.test(x.transform)?x.published_value+'%':pct(x.value)+' (변화율)';else v=x.value+' (발표 단위 그대로)';}
  out.push({ax,x,v});}return out;}
function treeBlock(box,merged){
 const node=NODES.find(n=>n[0]===V.node)||NODES[0],ms=fileState(MS).state==='OK'?I.data.get(MS):null,p=fileState(ME).state==='OK'?I.data.get(ME):null;
 const jump=id=>{const s=document.getElementById('s-'+id);if(!s)return;s.setAttribute('tabindex','-1');s.scrollIntoView({block:'start'});s.focus({preventScroll:true});};
 const facts=[merged?'경고등 · 자료 있는 경고등 '+merged.available_count+'/5 · 참고 모드':'경고등 · 파일을 읽지 못해 표시 안 함',
  p?'근거 지표 · 목록 '+p.indicators.length+'개 중 수집됨 '+p.indicators.filter(i=>i.state==='LIVE').length+'개':'근거 지표 · 파일을 읽지 못해 표시 안 함',
  ms?'상태판 8×6 · Level 원자료 '+ms.data.cells.filter(c=>c.state==='RAW_EVIDENCE').length+'칸 · 나머지 NA':'상태판 · 파일을 읽지 못해 표시 안 함'];
 const rows=ms?rawRows(ms):[],live=rows.filter(r=>r.x.state!=='NOT_AVAILABLE');
 put(box,sub('매크로 구조 트리','4.6.1 · 4.6.2','자료 → 지표 → 국면 → 산업 → 기업 영향 · 마디를 누르면 아래 설명'),
  h('div',{class:'chip-row',role:'group','aria-label':'구조 마디',dataset:{tree:''}},NODES.map(([id,name,,st],i)=>[i?h('span',{'aria-hidden':'true'},'→'):null,h('button',{type:'button',class:'chip'+(id===node[0]?' on':''),'aria-pressed':String(id===node[0]),dataset:{node:id},
   onclick:()=>{V.node=id;treeBlock(box,merged);focusLater(box,'[data-node="'+id+'"]');}},name,' · ',st)])),
  h('div',{class:'card-body',dataset:{nodeText:node[0]}},h('p',null,h('b',null,node[1]),' · ',node[2]),h('p',{class:'reason'},'상태: ',node[3]),
   h('button',{type:'button',class:'btn',dataset:{jump:node[4]},onclick:()=>jump(node[4])},'→ ',node[4].replace('-','.'),' 로')),
  h('h4',null,'실제 계산 결과 (공개)'),h('ul',{class:'news-lines',dataset:{facts:''}},facts.map(t=>h('li',null,t))),
  h('h4',null,'미확정 모델 (초안)'),h('ul',{class:'news-lines'},h('li',null,'국면 판정 규칙 · 미승인 (PM-3 · PM-4 · PM-10)'),h('li',null,'순환매 · 산업 사이클 위치 · 모델 없음'),h('li',null,'전환 빈도 확률 · Lab 검증 전'),h('li',null,'나비효과 경로 엔진 · 연구 단계')),
  h('h4',null,'공개 원값 · macro-screen.json (판정 아님)'),
  !ms?fileFail(MS,'경고등·상태판'):!live.length?empty('NO_PUBLIC_OBSERVATION','macro-screen.json에 공개 관측이 없습니다 · 예시를 지어내지 않음'):null,
  rows.length?h('ul',{class:'news-lines',dataset:{raw:''}},rows.map(({ax,x,v})=>h('li',{dataset:{rawAxis:ax,rawState:x.state}},h('b',null,ax),' · ',x.agency,' · ',x.source_series_code||x.source_series_id,' · ',
   x.state==='NOT_AVAILABLE'?h('span',{dataset:{na:(x.reason_codes||[]).join(' ')}},'— · ',(x.reason_codes||[]).join(', ')):[x.period,' · ',h('span',{dataset:{rawValue:''}},v),' · 수집 상한 ',utc(x.acquired_at)]))):null,
  h('p',{class:'reason'},'정부 통계 · 가격 아님 · 발표 시각 미확인이라 수집 시각이 상한 · FX는 공개 가격 경계에 따라 제외'));}

/* ---------------------------------------------------------------- screen */
function fileBand(refs){
 const chip=(n,label)=>{const s=fileState(n),ok=s.state==='OK';return h('span',{class:'chip'+(ok?'':' err'),dataset:{file:n,fileState:s.state}},label,' · ',ok?'기준 '+utc(s.as_of):s.text||s.state);};
 put(refs.band,chip(MS,'경고등·상태판'),chip(ME,'근거 지표'),chip(QGV2,'업종 그룹'));}
// The skeleton's slots filled: blocks with their loading lines, the static 준비 중 sections and the two private panels at once,
// then the public files once IS2.data.ready() resolves.
function screen(route,{legend,band,slots}){
 const aborted=()=>route.signal.aborted;
 legend.prepend(h('p',{class:'hand'},'공식 국면 · 확률 = 승인된 모델이 게시할 때만 (지금 미산출) · 내 추정 = 보라 점선, 이 기기에만 · 근거 세로선 = 탐색 전용'));
 const refs={band,ring:block('4.1.1',sub('국면 그래프 · 국면 탐색','4.1.1 · 4.1.2'),loading('국면 링')),evidence:block('4.1.3',sub('근거 세로선 · 근거 탐색','4.1.3'),loading('근거 지표')),
  lights:block('4.1.4',sub('기존 경고등 · 상태판 (참고 모드)','4.1.4'),loading('경고등')),industry:block('4.3',sub('산업 사이클 상태','4.3.1 · 4.3.2 · 4.3.3'),loading('업종 그룹')),
  mine:block('4.4',sub('내 국면 판단 기록','4.4.1 · 4.4.2'),loading('기록 칸')),tree:block('4.6',sub('매크로 구조 트리','4.6.1 · 4.6.2'),loading('구조 트리'))};
 evidenceBox=refs.evidence;
 // The public part never depends on a panel: a panel that cannot be built is left out (put skips null).
 const panel=(id,title)=>{try{return I.parts.privatePanel({id,title}).node;}catch(_){return null;}};
 put(slots['3-1'],h('p',{class:'hand'},'공식 국면은 아직 미산출 · 위치·확률을 임의로 찍지 않음 · 경고등 5개는 참고 모드 그대로'),refs.ring,refs.evidence,refs.lights,judgeBlock(),
  panel('macro-market-credit','시장·신용 근거 계열 (KIS 일봉)'));
 put(slots['3-2'],block('4.2',sub('순환매 · 위치 · 조건 · 확률','4.2.1 · 4.2.2 · 4.2.3','근거는 결정됨 · 계산·보정 방법 결정 대기 (IA-3)'),
   prep('지금 위치 미산출 · 순환매 위치 모델 없음 · 점·구간을 그리지 않음',['순환매 위치 모델','3.1 공식 국면 (미산출)','검증된 전환 빈도','자산 자료·단위 결정']),
   h('p',null,'기준 국면 (3.1): 미산출 → 위치도 미산출 · 기준일 — · 모델 없음'),h('h4',null,'다음 조정 조건'),conds(),h('h4',null,'확률'),prob(),
   h('p',{class:'reason'},'검증 상태: 연구 단계 → ',h('a',{href:href('lab'),class:'lk'},'n+1 Lab'))),
  panel('macro-sector-rs','섹터 ETF 상대강도 (KIS, 탐색 전용)'));
 put(slots['3-3'],refs.industry);put(slots['3-4'],refs.mine);
 put(slots['3-5'],block('4.5',sub('나비효과 · 사건 → 원인 고리 → 영향받는 기업','4.5.1 · 4.5.2 · 4.5.3 · 4.5.4','고리마다 근거 · 시차 · 확신도'),
   prep('나비효과 엔진 없음 · 빈 틀만 보임 · 자동으로 지어내지 않음',['경로 엔진','기업 관계 자료원 결정 (REL-SOURCE)','근거 문서 연결']),
   h('p',null,h('b',null,'어디서 시작할까')),h('div',{class:'scroll'},['사건 (공시·뉴스)','매크로 동인','기술·제품','밸류체인 단계'].map(t=>h('button',{type:'button',class:'chip',disabled:true},t,' · 준비 중'))),
   h('ol',{class:'news-lines',dataset:{chain:'NOT_AVAILABLE'},'aria-label':'나비효과 틀 · 빈 칸'},['사건','원인 고리','영향받는 기업'].map(t=>h('li',null,h('b',null,t),' ',h('span',{dataset:{na:'NOT_AVAILABLE'}},'—')))),
   h('p',{class:'reason'},'걸음마다 사실 · 추론 · 가설을 나눔 · 한 고리라도 가설이면 경로 전체가 가설 · 호재·악재 · 크기 · 확률은 쓰지 않음 · 확신도 숫자는 검증 전에는 쓰지 않음'),
   h('p',{class:'links'},h('a',{href:href('news'),class:'lk'},'→ 4.1 관계망'),' ',h('a',{href:href('news'),class:'lk'},'→ 4.2 공시 · 뉴스'))));
 put(slots['3-6'],refs.tree);
 const paint=()=>{if(aborted())return;fileBand(refs);
  let merged=null;try{merged=lightsBlock(refs.lights);}catch(e){put(refs.lights,failed('LIGHTS_FAILED','경고등을 그리지 못했습니다'));}
  const again=()=>{if(!aborted()){ringBlock(refs.ring);mineBlock(refs.mine,again2);}},again2=()=>{if(!aborted())ringBlock(refs.ring);};
  ringBlock(refs.ring);evidenceBlock(refs.evidence);industryBlock(refs.industry,again);mineBlock(refs.mine,again2);treeBlock(refs.tree,merged);};
 const fail=(code,text)=>{if(aborted())return;put(refs.band,h('span',{class:'chip err',dataset:{fileState:code}},text));
  for(const k of['ring','evidence','lights','industry','mine','tree'])put(refs[k],refs[k].firstChild,failed(code,text));};
 if(!models()||!window.MacroLights||!window.MacroEvidence){fail('READER_MISSING','매크로 모듈을 불러오지 못했습니다 · 새로고침해 주세요');return;}
 Promise.resolve().then(()=>I.data.ready()).then(()=>{if(aborted())return;paint();I.data.subscribe(d=>{if(d&&d.reason==='REFRESH')paint();},{signal:route.signal});},
  ()=>fail('DATA_FAILED','공개 자료를 읽지 못했습니다 · 새로고침해 주세요'));}
window.IS2.macroLive=Object.freeze({screen});
})();
