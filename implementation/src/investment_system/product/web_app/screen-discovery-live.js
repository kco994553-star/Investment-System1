/* 의외의 기업 screens (owner 2026-11-06): the list block of the QGV leaderboard (feature 2.1.8, menu stamp 1.1.9) and the mark next
   to the company name on the existing company page (feature 2.4.6). No new menu, no new company page, no company data of its own:
   names and tickers come from IS2.companies, QGV from IS2.qgv.page() (the published official score, never a new score), the
   sector from the existing SIC group of the published classification (IS2.qgvLive.helpers.industryOf).
   - One reader (IS2.discovery: validate → view) and one load per page for both screens, so the list and the mark show the same
     status and the same reasons for a company, whether the page was opened from the list, the search box or a direct link.
   - List: 최근 선정순 (default) · 기업명순 · 기존 QGV순. Under 기존 QGV순 the entries without an official rank stand in their own
     group (QGV 미산출 · 0점 아님); a row shows the official rank as 공식 순위 n / N, never its place in this list. Filters (섹터 ·
     기업 유형 · 사업 강점) are offered only for values present in the file; a filter that leaves 0 rows says so and keeps the
     conditions (only the user's 조건 모두 풀기 clears them).
   - Mark: a button next to the name (closed by default; Enter / Space / click open it, aria-expanded / aria-controls) opening ①–⑥
     and ⑦ 확인 근거 · 자료 기준일 · 마지막 검토일 in one panel; risks and the evidence summary are in the first opening, the long
     source list in a further <details>.
   - States kept apart: 불러오는 중 · 자료 연결 전 (source NONE, today) · 자료 불러오기 실패 · 규격 불일치 · 선정 기업 없음 · 필터 결과
     없음 · 일부 근거 미확인 · 선정 근거 재검토 필요. The last review day is always shown; discovery-company/v1 has no blanket
     expiry (aging evidence makes Codex move a record to REVIEW_REQUIRED). SUSPENDED / REMOVED / CANDIDATE / IN_REVIEW never get
     a selection mark or a list row.
   - Codex's discovery-company/v1 (#503): the list rows use display.business and display.discovery_reason; the panel shows each
     reviewed claim with its status, supporting and opposing facts and reason, the risks (facts and claims), unknowns, retained
     counterevidence, and the source facts with their document, dates, locator and hash. Text is set as text nodes only.
   View state (sort, filters) lives in RAM for this page load. Nothing is stored or sent; every text is a text node. */
(function(){
'use strict';
const I=window.IS2,{h,href}=I;
const X=()=>I.discovery;
const QGV2='sec-qgv2.json',CLS='company-classification.json';
const V={sort:'recent',f:{sector:'',type:'',strength:''}};
const ok=v=>typeof v==='number'&&Number.isFinite(v);
let NF=null;const fmt=v=>(NF||(NF=new Intl.NumberFormat('ko-KR',{minimumFractionDigits:1,maximumFractionDigits:1}))).format(v);
const get=(o,...k)=>k.reduce((x,y)=>(x===null||x===undefined?undefined:x[y]),o);
const reason=(code,words)=>h('span',{class:'reason',dataset:{na:code||''}},words);
const NO='①②③④⑤⑥⑦';

/* ---------------------------------------------------------------- one load per page (list and mark share it) */
let shared=null;
function cikOf(){const s=I.data.get(QGV2),rec=c=>get(s,'records',c);return code=>{const r=rec(code);return r&&typeof r.cik==='string'?r.cik:null;};}
function load(){
 const api=X();if(shared&&shared.api===api)return shared.p;
 const p=(async()=>{
  let src;try{src=await api.source();}catch(_){return{state:'ERROR',code:'DISCOVERY_SOURCE_FAILED'};}
  if(!src||src.state==='NONE')return{state:'NONE',code:(src&&src.code)||'DISCOVERY_NOT_CONNECTED'};
  if(src.state!=='OK')return{state:'ERROR',code:src.code||'DISCOVERY_SOURCE_FAILED'};
  const r=api.validate(src.payload);if(!r.ok)return{state:'INVALID',code:r.code,path:r.path};
  const c=await I.companies.ready();if(!c||c.state==='FAILED')return{state:'ERROR',code:'COMPANY_LIST_FAILED'};
  try{await I.data.ready();}catch(_){}
  return{state:'OK',view:api.view(r.value,{get:I.companies.get,cikOf:cikOf(),now:Date.now()})};
 })().catch(()=>({state:'ERROR',code:'DISCOVERY_SOURCE_FAILED'}));
 shared={api,p};
 // A failed read is not kept: the next screen (or 다시 읽기) reads again.
 p.then(x=>{if(x.state==='ERROR'&&shared&&shared.p===p)shared=null;});
 return p;}

/* ---------------------------------------------------------------- shared view parts */
const titleOf=e=>e.company.name_ko||e.company.name_en||e.company.ticker;
function qgvOf(pg){return e=>{if(!pg||pg.state!=='READY')return{rank:null,total:null,reason:pg?pg.reason||pg.state:'NO_PAGE',of:null};
 const row=I.qgv.row(pg,e.company.id)||I.qgv.row(pg,e.company.code);if(!row)return{rank:null,total:null,reason:'NO_ROW',of:null};
 return{rank:Number.isInteger(row.rank.official)?row.rank.official:null,total:ok(row.score.total)?row.score.total:null,reason:row.na_reason.rank||row.na_reason.total||null,of:row.rank.of};};}
function qgvLine(q){
 if(Number.isInteger(q.rank))return h('p',{class:'disc-qgv',dataset:{discQgv:'RANKED'}},'기존 QGV ',q.total===null?'NA':h('b',null,fmt(q.total)),' · 공식 순위 ',String(q.rank),' / ',String(q.of));
 const why=q.reason==='NO_ROW'?'공개 점수 입력에 이 기업 행 없음':q.reason?I.qgv.reasonText(q.reason):'산출 안 됨';
 return h('p',{class:'disc-qgv',dataset:{discQgv:'NO_RANK'}},q.total!==null?['기존 QGV ',fmt(q.total),' · ']:'',h('span',{class:'na'},'공식 QGV 순위 미산출'),' · ',reason(q.reason||'',why),' · 0점 아님');}
function badges(e){
 const r=e.record;
 return h('span',{class:'disc-badges'},
  e.synthetic?h('span',{class:'chip wait',dataset:{discSynthetic:''}},'합성 · 시험용'):null,
  e.review?h('span',{class:'chip disc-review',dataset:{discReview:r.state}},X().TEXT.REVIEW):null,
  e.partial?h('span',{class:'chip',dataset:{discPartial:''}},X().TEXT.PARTIAL):null);}
const day=t=>typeof t==='string'?t.slice(0,10):'없음';
const first=(list,none)=>list.length?list[0].claim:none;
function sectorTools(){
 const H=I.qgvLive&&I.qgvLive.helpers,ps={[QGV2]:I.data.get(QGV2),[CLS]:I.data.get(CLS)};
 const groups=get(ps[CLS],'data','industry_config','groups'),names=new Map(Array.isArray(groups)?groups.map(g=>[g.id,g.name]):[]);
 return{sectorOf:e=>H&&typeof H.industryOf==='function'?H.industryOf({company_id:e.company.id},ps)||null:null,sectorName:id=>names.get(id)||id};}

/* ---------------------------------------------------------------- 2.1.8 list (QGV leaderboard block) */
function stateCard(state,words,why,{alert=false,retry=null}={}){
 return h('div',{class:'sk state-card',role:alert?'alert':null,dataset:{discState:state}},I.parts.mascot(alert?'alarm':'plain'),h('b',null,words),why?h('span',{class:'reason'},why):null,retry);}
function list(route,{body}){
 const signal=route.signal;let res=null,pg=null,queued=false;
 const later=()=>{if(queued)return;queued=true;Promise.resolve().then(()=>{queued=false;if(!signal.aborted)draw();});};
 const read=()=>{res=null;draw();load().then(x=>{if(!signal.aborted){res=x;later();}});};
 I.qgv.page({signal}).then(x=>{if(!signal.aborted){pg=x;later();}},()=>{});
 const focusKey=()=>{const a=document.activeElement;return a&&body.contains(a)&&a.dataset&&a.dataset.k?a.dataset.k:null;};
 const refocus=k=>{if(!k)return;const el=body.querySelector('[data-k="'+k+'"]');if(el&&!el.disabled)el.focus({preventScroll:true});};
 function draw(){
  const k=focusKey(),T=X().TEXT;
  if(!res){body.replaceChildren(h('p',{class:'pending',role:'status',dataset:{discState:'LOADING'}},T.LOADING));return;}
  if(res.state==='NONE'){body.replaceChildren(stateCard('NONE',T.NONE,T.NONE_WHY),
   h('p',{class:'hand'},'자료가 오면: 기업명·티커 · 하는 일 한 줄 · 발견 이유 한 줄 · 기존 QGV 점수와 산출 상태 · 누르면 기존 기업 상세'));return;}
  if(res.state==='ERROR'||res.state==='INVALID'){body.replaceChildren(stateCard(res.state==='ERROR'?'ERROR':'INVALID',res.state==='ERROR'?T.FAILED:T.INVALID,
   res.state==='INVALID'?'규격 위반 '+res.code+' · '+res.path:'리더보드는 그대로',{alert:true,retry:res.state==='ERROR'?h('button',{type:'button',class:'btn',dataset:{k:'disc-retry'},onclick:read},'다시 읽기'):null}));
   body.dataset.discCode=res.code;refocus(k);return;}
  const v=res.view,S=sectorTools(),q=qgvOf(pg),all=v.entries;
  const hiddenN=Object.values(v.hidden).reduce((a,b)=>a+b,0),droppedN=Object.values(v.dropped).reduce((a,b)=>a+b,0);
  const status=h('p',{class:'sk status-line',dataset:{discData:v.data_kind}},X().status(v),' · ',X().SCHEMA,' · 선정·근거 Codex · 화면은 판단하지 않음');
  const notes=[hiddenN?h('p',{class:'reason',dataset:{discHidden:String(hiddenN)}},'보류·해제·검토 중 ',String(hiddenN),'건은 목록과 마크에 넣지 않음'):null,
   droppedN?h('p',{class:'reason',dataset:{discDropped:Object.entries(v.dropped).map(([c,n])=>c+':'+n).join(' ')}},'기업 신원을 확인하지 못한 ',String(droppedN),'건은 넣지 않음 (기존 기업 식별자 불일치)'):null].filter(Boolean);
  const method=h('details',{class:'why',dataset:{discMethod:''}},h('summary',null,'선정 방법 ▸'),
   h('p',{class:'reason'},'새 의외성 점수는 없음 · 정렬은 줄 순서일 뿐 · 공식 QGV 순위는 각 줄의 "공식 순위" 값 · QGV가 없어도 선정에서 빼지 않음'),
   h('p',{class:'reason'},'인지도 자료가 없으면 "미측정"으로 표시 · 미측정만으로 빼거나 저인지도로 확정하지 않음'),
   h('p',{class:'reason'},'선정은 근거 대조를 거친 연구 검토 결과(discovery-company/v1) · 자동 결과는 후보로 남고 목록에 넣지 않음 · 선정 기준과 유형 분류는 연구 규칙표(discovery-rules/1)'));
  if(!all.length){body.replaceChildren(status,stateCard('EMPTY',T.EMPTY,'자료는 읽었고 목록에 넣을 선정 기업이 0개'),...notes,method);refocus(k);return;}
  // controls: sort and the filters present in the data
  // A chosen filter value stays chosen even when no entry has it any more (the screen never clears a condition).
  const fc=X().facets(all,S);
  const sortSel=h('select',{id:'disc-sort',dataset:{k:'disc-sort'},onchange:e=>{V.sort=e.target.value;draw();}},...X().SORTS.map(([id,t])=>h('option',{value:id,selected:V.sort===id},t)));
  const real=key=>fc[key].some(o=>o[0]!=='NONE'&&o[0]!=='NOT_AVAILABLE');
  const LABEL={sector:'섹터 (SIC 업종군)',type:'기업 유형',strength:'사업 강점'};
  const pick=key=>real(key)||V.f[key]?h('div',{class:'sk fcard',dataset:{discFilter:key}},h('label',{for:'disc-'+key},LABEL[key]),
   h('select',{id:'disc-'+key,dataset:{k:'disc-'+key},onchange:e=>{V.f={...V.f,[key]:e.target.value};draw();}},h('option',{value:'',selected:!V.f[key]},'전체'),
    ...fc[key].map(([val,t,n])=>h('option',{value:val,selected:V.f[key]===val},t,' (',String(n),')')),
    V.f[key]&&!fc[key].some(o=>o[0]===V.f[key])?h('option',{value:V.f[key],selected:true},V.f[key]):null))
   :h('p',{class:'reason',dataset:{discFilterNa:key}},LABEL[key],' 자료 없음 · 이 필터는 없음');
  const any=!!(V.f.sector||V.f.type||V.f.strength);
  const controls=h('div',{class:'disc-controls'},h('div',{class:'sort-row'},h('label',{for:'disc-sort'},'정렬'),sortSel),
   h('div',{class:'lb-filters open disc-filters'},pick('sector'),pick('type'),pick('strength')),
   any?h('button',{type:'button',class:'btn',dataset:{k:'disc-clear'},onclick:()=>{V.f={sector:'',type:'',strength:''};draw();}},'조건 모두 풀기'):null);
  const kept=X().filter(all,V.f,S),ordered=X().sort(kept,V.sort,{qgv:q,title:titleOf});
  const count=h('p',{class:'sk status-line',role:'status',dataset:{discCount:String(ordered.length)}},'의외의 기업 ',String(all.length),'개 중 ',String(ordered.length),'개',any?' · 조건 적용':'',
   V.sort==='qgv'?' · 공식 QGV 순위 순 (순위 없는 기업은 따로 아래)':'');
  if(!ordered.length){body.replaceChildren(status,controls,count,h('div',{class:'sk empty',dataset:{discState:'FILTER_EMPTY'}},h('p',null,T.FILTER_EMPTY),
   h('p',{class:'reason'},'조건은 그대로 둠 · 풀려면 위 "조건 모두 풀기"')),...notes,method);refocus(k);return;}
  const rows=[];let group=null;
  for(const e of ordered){const qq=q(e);
   if(V.sort==='qgv'){const g=X().qgvGroup(qq);if(g!==group){group=g;rows.push(h('li',{class:'disc-group',dataset:{discGroup:g}},g==='RANKED'?'공식 QGV 순위가 있는 기업':'공식 QGV 순위 미산출 · 0점 아님 · 이름순'));}}
   const r=e.record;
   rows.push(h('li',{class:'sk disc-row',dataset:{discRow:e.company.code,discStatus:e.status}},
    h('div',{class:'disc-row-head'},h('a',{class:'disc-name',href:href('company',e.company.id),dataset:{discLink:e.company.id}},titleOf(e),' ',h('span',{class:'nobr disc-ticker'},e.company.ticker)),badges(e)),
    h('p',{class:'disc-line',dataset:{discWhat:''}},h('b',null,'하는 일 '),first(r.display.business,'자료 없음')),
    h('p',{class:'disc-line',dataset:{discWhy:''}},h('b',null,'발견 이유 '),first(r.display.discovery_reason,'자료 없음')),
    e.review?h('p',{class:'reason',dataset:{discReviewWhy:''}},T.REVIEW,' · ',r.state_reason):null,
    qgvLine(qq),
    h('p',{class:'reason'},'최초 선정 ',day(r.first_selected_at),' · 마지막 검토 ',day(r.last_reviewed_at),' · 기준 시각 ',day(r.as_of))));}
  body.replaceChildren(status,controls,count,h('ul',{class:'disc-list',dataset:{discList:String(ordered.length)}},...rows),...notes,method);
  delete body.dataset.discCode;refocus(k);}
 read();
}

/* ---------------------------------------------------------------- 2.4.6 mark on the company page */
let seq=0;
// One reviewed claim: the claim, its status (확인 / 미확인 / 반박됨), how many facts support and oppose it, the reviewer's reason.
function claimLine(j,ev,k){const S=X(),topic=k?S.topicLabel(k,j.topic):null;
 return h('li',{dataset:{discItem:j.status,discJudgment:j.judgment_id}},topic?h('b',null,topic,' · '):null,j.claim,' ',
  h('span',{class:j.status==='CONFIRMED'?'reason':'reason disc-open',dataset:{na:j.status==='CONFIRMED'?'':j.status}},'· ',S.STATUS_TEXT[j.status],
   j.evidence_ids.length?' · 근거 '+j.evidence_ids.map(x=>ev.get(x)).join(', '):' · 근거 없음',
   j.counterevidence_ids.length?' · 반대 근거 '+j.counterevidence_ids.map(x=>ev.get(x)).join(', '):'',' · ',j.reason));}
function itemList(r,s,num,ev){const S=X(),state=S.sectionState(r)(s);
 const words={CONFIRMED:'확인됨',PARTIAL:'일부 근거 미확인',UNCONFIRMED:'미확인',NONE:'자료 없음'}[state];
 const list=s==='risks'?[...r.display.risk_judgments.map(j=>claimLine(j,ev,null)),
  ...r.display.risks.map(f=>h('li',{dataset:{discRisk:f.evidence_id}},h('b',null,'원문 · '),String(f.value),' ',h('span',{class:'reason'},'· 근거 '+ev.get(f.evidence_id)+' · ',f.document_id)))]
  :r.display[s].map(j=>claimLine(j,ev,s==='discovery_reason'?null:s));
 const extra=s==='discovery_reason'?[...r.display.selection_summary.map(j=>h('p',{class:'reason',dataset:{discSummary:j.judgment_id}},'선정 판단 · ',j.claim,' · ',S.STATUS_TEXT[j.status])),
   ...['consumer_contact','market_attention'].map(k=>{const a=S.awarenessOf(r,k),label=k==='consumer_contact'?'소비자 접점':'시장 관심';
    return h('p',{class:'reason',dataset:{discAwareness:a?a.status:'NOT_MEASURED',discAwarenessKind:k}},'인지도(',label,') · ',a?[a.claim,' · ',S.STATUS_TEXT[a.status]]:'미측정 (미측정만으로 빼거나 저인지도로 확정하지 않음)');})]
  :s==='types'&&!r.display.types.length?[h('p',{class:'reason'},'유형 미분류')]:[];
 return h('div',{class:'disc-sec',dataset:{discSection:s,discSectionState:state}},
  h('h3',{class:'disc-sec-title'},NO[num],' ',S.SECTION_TEXT[s],' ',h('span',{class:state==='CONFIRMED'?'chip':'chip wait'},words)),
  list.length?h('ul',{class:'disc-items'},...list):h('p',{class:'reason'},'이 항목의 자료 없음'),...extra);}
function panelOf(e,id){
 const r=e.record,T=X().TEXT,S=X(),ev=new Map(r.evidence.map((x,i)=>[x.evidence_id,i+1]));
 const head=h('div',{class:'disc-panel-head'},
  e.synthetic?h('p',{class:'sk status-line',dataset:{discSynthetic:''}},T.SYNTHETIC):null,
  e.review?h('p',{class:'disc-review-line',role:'note',dataset:{discReview:r.state}},h('b',null,T.REVIEW),' · ',r.state_reason)
   :h('p',null,h('b',null,T.MARK),' · ',r.state_reason,' · 최초 선정 ',day(r.first_selected_at)),
  r.display.business.length?h('p',{dataset:{discBusiness:''}},h('b',null,'하는 일 · '),r.display.business.map(j=>j.claim).join(' / ')):null,
  h('p',{class:'reason'},'연구상 선정이며 공개 승인·투자 권유가 아님 · 새 점수 없음 · 아래 QGV·재무·기술·뉴스 카드는 기존 그대로'));
 const retained=r.counterevidence_history.filter(c=>c.disposition==='RETAINED_FOR_REVIEW');
 const seven=h('div',{class:'disc-sec',dataset:{discSection:'evidence'}},h('h3',{class:'disc-sec-title'},NO[6],' 확인 근거 · 자료 기준일 · 마지막 검토일'),
  h('p',{dataset:{discEvidence:String(r.evidence.length)}},'원문 근거 ',String(r.evidence.length),'건 · 기준 시각 ',day(r.as_of),' · 마지막 검토일 ',day(r.last_reviewed_at),' · 검토 범위 ',r.review_scope),
  e.partial?h('p',{class:'reason',dataset:{discPartial:''}},T.PARTIAL,' · 미확인·반박 줄은 위 각 항목에 사유와 함께'):null,
  r.display.unknowns.length?h('p',{class:'reason',dataset:{discUnknowns:String(r.display.unknowns.length)}},'모르는 것 · ',r.display.unknowns.join(' · ')):null,
  retained.length?h('p',{class:'reason',dataset:{discRetained:String(retained.length)}},'검토용으로 남긴 반대 근거 ',String(retained.length),'건'):null,
  r.evidence.length?h('details',{class:'why',dataset:{discSources:''}},h('summary',null,'출처 내역 ',String(r.evidence.length),'건 보기 ▸'),
   h('ol',{class:'disc-sources'},...r.evidence.map(x=>h('li',{dataset:{discSource:x.evidence_id}},h('b',null,x.document_id),' · ',String(x.value),
    ' · 게시 ',x.published_on||'미상',x.period.start||x.period.end?' · 기간 '+(x.period.start||'?')+'~'+(x.period.end||'?'):'',' · 취득 ',day(x.acquired_at),
    ' · 위치 ',x.locator.json_pointer!==undefined?x.locator.json_pointer:x.locator.xml_id,' · SHA-256 ',x.sha256.slice(0,12),'…',
    /^https:\/\//.test(x.source_url)&&!/\.invalid(\/|$)/.test(new URL(x.source_url).hostname+'/')?[' · ',h('a',{href:x.source_url,target:'_blank',rel:'noopener noreferrer'},'원문')]:[' · ',h('span',{class:'reason'},'원문 주소 없음(합성)')])))):null);
 return h('section',{id,class:'sk card disc-panel',hidden:true,'aria-label':'의외의 기업 선정 이유',dataset:{discPanel:e.company.code}},head,
  ...S.SECTIONS.map((s,i)=>itemList(r,s,i,ev)),seven);}
function mark({name,cid,signal}){
 load().then(res=>{
  if(signal.aborted||!name.isConnected)return;
  if(res.state==='ERROR'||res.state==='INVALID'){name.after(h('p',{class:'reason disc-mark-na',dataset:{discMarkState:res.state,na:res.code}},'의외의 기업 자료를 읽지 못해 표시 여부를 확인하지 못함'));return;}
  if(res.state!=='OK')return;
  const row=I.companies.get(cid),e=X().markFor(res.view,row);if(!e)return;
  const id='disc-panel-'+(++seq),panel=panelOf(e,id);
  const btn=h('button',{type:'button',class:'chip disc-mark','aria-expanded':'false','aria-controls':id,dataset:{discMark:e.status,discCode:e.company.code}},
   h('span',{'aria-hidden':'true'},'◆ '),X().TEXT.MARK,e.review?' · 재검토 필요':'',e.synthetic?' · 합성':'',h('span',{'aria-hidden':'true',class:'disc-caret'},' ▸'));
  btn.addEventListener('click',()=>{const open=btn.getAttribute('aria-expanded')!=='true';btn.setAttribute('aria-expanded',String(open));panel.hidden=!open;
   btn.querySelector('.disc-caret').textContent=open?' ▾':' ▸';});
  const wrap=h('div',{class:'disc-name-row'});name.before(wrap);wrap.append(name,btn);
  const sec=wrap.closest('section');(sec||wrap).after(panel);});
}
I.discoveryLive=Object.freeze({list,mark,load});
})();
