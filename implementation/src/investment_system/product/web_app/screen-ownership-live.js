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
  h('p',{class:'meta'},x.when),h('p',{class:'meta'},x.denominator));
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
I.ownershipScreen=Object.freeze({block});
})();
