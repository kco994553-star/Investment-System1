/* 5.1.1 기업 중심 관계 · 5.1.2 연결 근거 · company detail 관계 lines (IS2.ownershipScreen; owner 2026-11-11 「#530 후속」 §4,
   Codex #531 company-ownership-view/1 read by IS2.ownershipView). One block drawn from one checked view in RAM (IS2.ownershipView.ram);
   with no checked view for the centre the screens keep 「관계 자료 미연결」 (REL-SOURCE) as before. Nothing is fetched, stored, inferred
   or computed here: the lists, words and ids are the reader's.
   - Five lists apart (모회사 / 자회사 / 보유 지분 / 주주 / 운용 재량 13F), each a <details> (keyboard: Tab to the summary, Enter /
     Space opens), never merged into one "related companies" list; an empty list says it carries nothing delivered (not a confirmed
     none) unless the view is VERIFIED_ZERO_IN_SCOPE.
   - A counterparty links to its company page only when it is a company of the shared company list; otherwise its name stands with
     「기업 페이지 없음」 and no page is made.
   - 5.1.2: each relationship shows its relationship_id (the same id from either company), the evidence ids, observed and reviewed
     times; share capital and voting power on separate lines with their basis, class and date. */
(function(){
'use strict';
const I=window.IS2,{h}=I;
const O=()=>I.ownershipView;
function block(v,{compact=false,href,companies}={}){const M=O(),x=M.view(v,{receipt:M.ram.receiptFor?M.ram.receiptFor(v):null,companyLink:code=>{const r=companies&&companies.get(code);return r&&href?href('company',r.id):null;}});
 const centre=x.centre.entity_id;
 const head=h('div',{class:'cc-wrap',dataset:{ownState:x.collection_state}},...x.state.map(t=>h('p',{class:'reason',role:'status'},t)),
  h('p',{class:'meta',dataset:{ownScope:x.collection_state}},'조사 범위 · ',x.scopeState),h('p',{class:'meta',dataset:{ownEvidenceState:''}},'근거 확인 · ',x.evidenceState),
  x.refresh?h('p',{class:'reason',dataset:{ownRefresh:''}},x.refresh):null,
  h('p',{class:'meta'},x.when),h('p',{class:'meta'},x.denominator),NOTES.get(v)?h('p',{class:'meta',dataset:{ownDelivery:''}},NOTES.get(v)):null);
 const party=p=>p.link?h('a',{class:'lk',href:p.link,dataset:{ownParty:p.entity_id}},p.name):h('span',{dataset:{ownParty:p.entity_id}},p.name,h('span',{class:'meta'},' · 기업 목록에 없음 · 기업 페이지 없음'));
 const obs=(label,list,key)=>list.length?h('ul',{class:'news-lines',dataset:{ownObs:key}},...list.map(o=>h('li',null,o.text,' · ',h('span',{class:'meta'},o.basis),o.zero?h('span',{class:'meta'},' · ',o.zero):null))):null;
 const row=r=>h('li',{class:'cc-wrap',dataset:{ownRel:r.relationship_id,ownRelative:r.relative,ownRelState:r.state}},
  h('p',null,party(r.party),' · ',r.directness,r.capacity?' · '+r.capacity:'',' · ',h('b',null,r.stateText),r.validity?' · '+r.validity:''),
  obs('지분율',r.share,'share'),obs('의결권',r.voting,'voting'),obs('운용 보유',r.managed,'managed'),
  r.percentNote?h('p',{class:'meta'},r.percentNote):null,
  compact?null:h('p',{class:'meta',dataset:{ownEvidence:r.relationship_id}},'연결 근거 · 관계 ID ',r.relationship_id,' · 근거 ',r.evidence.join(', ')||'없음',' · 관측 ',r.observedOn||'미상',' · 검토 ',r.reviewedAt||'미상'));
 const none=x.collection_state==='VERIFIED_ZERO_IN_SCOPE'?'검토한 범위에서 없음 확인':'전달된 관계 없음 · 없다는 확인이 아님';
 const lists=x.lists.map(l=>h('details',{class:'why',dataset:{ownList:l.key}},h('summary',null,l.label,' · ',String(l.rows.length),'건 ▸'),
  l.rows.length?h('ul',{class:'news-lines'},...l.rows.map(row)):h('p',{class:'reason',dataset:{ownEmpty:l.key}},none)));
 const unresolved=x.unresolved.length?h('div',{class:'cc-wrap',dataset:{ownUnresolved:''}},h('p',{class:'meta'},'목록에 없는 대상(이름만 확인 · 기업으로 만들지 않음)'),
  h('ul',{class:'news-lines'},...x.unresolved.map(u=>h('li',{dataset:{ownMention:u.assertion_id}},u.name,' · ',u.word,' · ',u.type==='PARENT_SUBSIDIARY'?'모회사·자회사 언급':'지분 언급',' · ',u.directness)))):null;
 return h('div',{class:'cc-wrap',dataset:{ownBlock:centre,ownCompact:String(compact)}},
  h('p',{class:'hand'},compact?'관계 (5.1)':'기업 중심 관계 (5.1.1) · 연결 근거 (5.1.2)',' · ',x.centre.name,' · 연구 자료 ',x.dataKind),
  head,...lists,unresolved);}
// 관계 자료 불러오기 (owner 2026-11-13): the owner's authenticated delivery, on the existing private Worker route
// (/kis/classification ?part=ownership_index, then ?part=ownership_view|ownership_receipt&entity=<id>), each read on its own click,
// RAM only. Click 1 reads Main's index (one read); for a company the index lists, click 2 reads its view and, if staged, its refresh
// receipt (two reads, the receipt OPTIONAL). The reader (IS2.ownershipView.checkDelivered) takes the view only when its bytes are the
// ones the index names; then it goes into IS2.ownershipView.ram and the screens draw it. A missing file, a refused sign-in, damaged
// bytes or a failed refresh each keep their own words, and none of them is read as "no relationships". Signed out: nothing is drawn.
let INDEX=null,DELIVERED=false,WATCH=false;const NOTES=new WeakMap();
// Signing out drops the index and every delivered view from RAM (nothing of it is kept on the device).
const watch=()=>{if(WATCH)return;try{P().kisSubscribe(()=>{if(connected())return;INDEX=null;if(DELIVERED&&O()){DELIVERED=false;O().ram.clear();}});WATCH=true;}catch(_){}};
const AUTH=new Set(['AUTH_REQUIRED','AUTH_FORBIDDEN','TOKEN_EXPIRED','TOKEN_REJECTED','LOGIN_REFUSED','LOGIN_CANCELED']);
const NOT_NONE=' · 관계가 없다는 뜻이 아님';
const failText=(e,what)=>{const c=e&&e.message||String(e);return c==='KIS_SERIES_NOT_FOUND'?what+' 없음 · 전달 위치에 아직 배치되지 않음'+NOT_NONE:AUTH.has(c)?'로그인이 필요하거나 권한이 없습니다 · '+c+NOT_NONE
 :c==='CANCELED'?'취소됨'+NOT_NONE:'불러오지 못함('+what+') · '+c+NOT_NONE;};
const refusedText=r=>r.code==='FILE_MISMATCH'?'파일이 목록표와 다릅니다(손상 또는 다른 파일) · 쓰지 않음 · '+r.path+NOT_NONE
 :r.code==='RECEIPT_MISSING'?'목록표에 있는 갱신 기록 파일이 없습니다 · 쓰지 않음'+NOT_NONE:r.code==='RECEIPT_UNLISTED'?'목록표에 없는 갱신 기록 파일 · 쓰지 않음'+NOT_NONE
 :r.code==='INDEX_COMPANY_MISMATCH'||r.code==='INDEX_DATASET_MISMATCH'||r.code==='CENTRE_MISMATCH'?'목록표와 관계 파일이 서로 다른 기업·자료입니다 · 쓰지 않음 · '+r.code+NOT_NONE
 :'관계 자료 형식이 계약과 다릅니다 · 쓰지 않음 · '+r.code+' '+(r.path||'')+NOT_NONE;
const P=()=>I.prices,connected=()=>{try{return!!P().kisState().connected;}catch(_){return false;}};
function privateLoader(code,{signal}={}){watch();const area=h('div',{class:'cc-wrap',dataset:{ownPrivate:code||''}});let busy=false;
 const st=(state,text)=>h('p',{class:state==='ERROR'||state==='ABSENT'?'reason':'meta',role:'status',dataset:{ownPrivateState:state}},text);
 const draw=(msg)=>{if(signal&&signal.aborted)return;if(!connected()||!code||!O()){area.replaceChildren();return;}
  const M=O();if(M.ram.forCompany(code)){area.replaceChildren();return;}
  if(!INDEX){const b=h('button',{type:'button',class:'btn',dataset:{ownPrivateOpen:''}},'관계 자료 목록 불러오기 (비공개 · 1개 읽기)');
   b.addEventListener('click',e=>{if(busy)return;busy=true;b.disabled=true;area.replaceChildren(b,st('LOADING','불러오는 중 · 관계 자료 목록표 1개'));
    let p;try{p=P().kisRead(e,[['classification','ownership_index']]);}catch(err){p=Promise.reject(err);}
    Promise.resolve(p).then(([idx])=>{const r=M.checkDeliveryIndex(idx);busy=false;if(!r.ok){draw(st('ERROR','관계 자료 목록표를 쓰지 않음 · '+r.code+' '+r.path+NOT_NONE));return;}INDEX=r.value;draw();},
     err=>{busy=false;draw(st('ERROR',failText(err,'관계 자료 목록표')));});});
   area.replaceChildren(b,msg||st('IDLE','비공개 보관본 · 인증 경로 · 연구 자료(현재 지분·완결 목록 아님)'));return;}
  const entry=M.entryFor(INDEX,code);
  if(!entry){area.replaceChildren(st('ABSENT','이 기업은 전달된 관계 자료 목록에 없음 · 목록 '+INDEX.views.length+'개 기업'+NOT_NONE));return;}
  const b=h('button',{type:'button',class:'btn',dataset:{ownPrivateShow:entry.entity_id}},'이 기업 관계 불러오기 (2개 읽기 · 갱신 기록은 없으면 없음)');
  b.addEventListener('click',e=>{if(busy)return;busy=true;b.disabled=true;area.replaceChildren(b,st('LOADING','불러오는 중 · 관계 파일 + 갱신 기록 · 서버 요청 간격 5초'));
   let p;try{p=P().kisRead(e,[['classification','ownership_view/'+entry.entity_id],['classification','ownership_receipt/'+entry.entity_id,'OPTIONAL']]);}catch(err){p=Promise.reject(err);}
   Promise.resolve(p).then(async([view,receipt])=>{const r=await M.checkDelivered(INDEX,entry,view,receipt,I.expandedIssuers.sha256);busy=false;
     if(!r.ok){draw(st('ERROR',refusedText(r)));return;}
     if(r.value.receiptRefused)NOTES.set(r.value.view,'갱신 기록을 쓰지 않음 · '+r.value.receiptRefused+' · 보관된 관계 자료만 보임');
     NOTES.set(r.value.view,[NOTES.get(r.value.view),'비공개 보관본 · 인증 경로 · '+(r.value.dataKind==='SYNTHETIC'?'합성 자료 · 시험용':'실자료(연구)')].filter(Boolean).join(' · '));
     DELIVERED=true;M.ram.put(r.value.view,r.value.receipt||undefined);},
    err=>{busy=false;draw(st('ERROR',failText(err,'관계 파일')));});});
  area.replaceChildren(b,msg||st('LISTED','목록표에 있음 · 실체 '+entry.entity_id+' · 갱신 기록 '+(entry.receipt?'있음':'없음')));};
 draw();
 // A loader replaced by a redraw of its screen stops listening once it has left the page.
 let off=()=>{},offRam=()=>{},seen=false;const live=()=>{if(area.isConnected){seen=true;return true;}if(seen){off();offRam();return false;}return true;};
 try{off=P().kisSubscribe(()=>{if(live())draw();});}catch(_){}
 offRam=O()?O().ram.subscribe(()=>{if(live())draw();}):()=>{};
 if(signal)signal.addEventListener('abort',()=>{off();offRam();},{once:true});
 return area;}
I.ownershipScreen=Object.freeze({block,privateLoader,note:v=>NOTES.get(v)||null});
})();
