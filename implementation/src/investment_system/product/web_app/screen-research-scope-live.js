/* Lab n+1.1 · 연구 범위 · 선정 방식 (owner 2026-11-04 third, item 4), the part that runs after IS2.ready. screen-lab-live.js asks
   IS2.researchScopeLive.block({signal}) once per route and puts the node under the 9.1 private panel.
   - Data: IS2.researchScope (research-scope.js): Codex's operational-qgv-coverage/1 (#474) and the general research selection
     fields of validation.vertical_slice (#473). Today source() is NONE: the block says so and draws no number. Private research
     results are not connected to a public screen without the owner's approval.
   - Coverage card: the denominator words first (운영 Universe504 코드 기준 · 고정 증권 ID 아님), then Q, G, V each, all three axes,
     each preset total and the published default total as separate rows (never one label); not computed stays 미산출 with its
     reason, never 0. The 15 factors sit in <details>.
   - Selection card: the mode (조건 충족 전부 · 상위 N · 상위 %), eligible → selected, equal weight, and the fixed line that the
     official model keeps its N15 tiers and TARGET rules. Outcomes and returns of the same result are never read.
   - A file that breaks its contract is refused whole (code and path shown); nothing is repaired. No storage, no request. */
(function(){
'use strict';
const I=window.IS2,{h}=I;
const RS=()=>I.researchScope;
const phone=()=>{try{return window.matchMedia('(max-width:720px)').matches;}catch(_){return false;}};
const sub=(title,fn,hand)=>h('div',{class:'lb-head'},h('h3',{class:'stamp sub'},title),fn?h('span',{class:'meta'},'기능 ',fn):null,hand?h('span',{class:'hand'},hand):null);
const note=(t,d)=>h('p',{class:'reason',dataset:d||{}},t);

function coverageCard(r){const S=RS();
 if(!r)return null;
 if(!r.ok)return h('div',{class:'sk state-card',dataset:{state:'error',na:r.code,scopeRefused:'coverage'}},h('p',{class:'err'},'커버리지 파일이 계약과 달라 전부 읽지 않았습니다 · ',r.code,' · ',r.path));
 const v=S.coverageView(r.value);
 const rows=phone()
  ?h('ol',{class:'news-lines',dataset:{scopeRows:String(v.rows.length)}},v.rows.map(x=>h('li',{dataset:{scopeRow:x.id,scopeKind:x.kind}},h('b',null,x.label),' · ',x.value,x.note?h('span',{class:'reason'},' · ',x.note):null)))
  :h('div',{class:'tbl-wrap'},h('table',{class:'tbl',dataset:{scopeRows:String(v.rows.length)}},
    h('thead',null,h('tr',null,['항목','계산 가능 / 분모','사유'].map(t=>h('th',{scope:'col'},t)))),
    h('tbody',null,v.rows.map(x=>h('tr',{dataset:{scopeRow:x.id,scopeKind:x.kind}},h('th',{scope:'row'},x.label),h('td',null,x.value),h('td',null,x.note||'–'))))));
 return h('div',{class:'sk card',dataset:{block:'scope-coverage'}},sub('운영 커버리지','9.1','Q·G·V 각각 · 세 축 동시 · 프리셋 총점은 따로 셉니다'),
  h('p',{class:'hand',dataset:{scopeHead:''}},v.head),
  h('p',{dataset:{scopeBasis:String(r.value.denominator.count)}},h('b',null,v.basis)),
  rows,
  v.engine?note('프리셋 총점 7개 모두 미산출: '+v.engine,{scopeEngine:'MISMATCH'}):null,
  note(v.presetBasis),note(v.scope,{scopeScope:''}),
  h('details',{class:'why'},h('summary',null,'팩터 15개 · 원본 ID ▸'),h('ul',null,v.factors.map(f=>h('li',{dataset:{scopeFactor:f.id}},h('b',null,f.axis,' · ',f.label),' · ',f.value))),
   h('p',{class:'reason',dataset:{scopeIds:''}},'게시본 ID',h('br'),h('code',{class:'wrap-any'},v.ids.publication_id),h('br'),'원본 SHA-256',h('br'),h('code',{class:'wrap-any'},v.ids.source_sha256))));}

function selectionCard(r){const S=RS();
 if(!r)return null;
 if(!r.ok)return h('div',{class:'sk state-card',dataset:{state:'error',na:r.code,scopeRefused:'selection'}},h('p',{class:'err'},'선정 결과가 계약과 달라 전부 읽지 않았습니다 · ',r.code,' · ',r.path));
 const v=S.selectionView(r.value);
 return h('div',{class:'sk card',dataset:{block:'scope-selection',scopeMode:v.mode}},sub('일반 연구 선정 방식','9.1','조건 충족 전부 · 상위 N · 상위 %'),
  h('dl',{class:'card-body'},[['선정 방식',v.label,{scopeLabel:''}],['선정 수',v.count,{scopeCount:''}],['선정 규칙',v.rule,{scopeRule:''}],['비중',v.weight,{scopeWeight:''}]]
   .map(([k,x,d])=>[h('dt',null,h('b',null,k)),h('dd',{dataset:d},x)])),
  v.shortfall?note(v.shortfall,{scopeShortfall:''}):null,note(v.scope,{scopeScope:''}),note(v.absent,{scopeAbsent:''}),
  note(v.general),note(v.official,{scopeOfficial:''}));}

function block({signal}){
 const box=h('div',{class:'sk card',dataset:{block:'research-scope'}},sub('연구 범위 · 선정 방식','9.1','운영 커버리지 (#474) · 일반 연구 선정 (#473) · 결과 종류: 연구 범위 · 수익률 · 전략 성과 아님'),
  h('p',{class:'pending',role:'status',dataset:{state:'loading'}},'불러오는 중 · 연구 범위 자료'));
 const paint=(...c)=>{box.replaceChildren(box.firstChild);I.append(box,c);};
 let p;try{p=RS().source();}catch(e){p=Promise.reject(e);}
 Promise.resolve(p).then(src=>{if(signal.aborted)return;
  if(!src||src.state!=='OK'){paint(h('div',{class:'sk state-card',dataset:{state:'empty',na:(src&&src.code)||'RESEARCH_SCOPE_NOT_CONNECTED'}},I.parts.mascot('plain'),h('p',null,RS().TEXT.NONE)),
   note(RS().TEXT.OFFICIAL,{scopeOfficial:''}));return;}
  const cov=src.coverage===null||src.coverage===undefined?null:RS().validateCoverage(src.coverage),sel=src.selection===null||src.selection===undefined?null:RS().validateSelection(src.selection);
  paint(h('p',{class:'hand',dataset:{scopeKind:src.data_kind||''}},src.data_kind==='SYNTHETIC'?'합성 자료 · 시험용 · 실제 연구 결과 아님':'연구 결과 · '+(src.data_kind||'자료 종류 표시 없음')),
   coverageCard(cov),selectionCard(sel),cov||sel?null:note('연결된 결과 없음',{scopeEmpty:''}));},
 ()=>{if(signal.aborted)return;paint(h('div',{class:'sk state-card',dataset:{state:'error',na:'RESEARCH_SCOPE_SOURCE_FAILED'}},h('p',{class:'err'},'연구 범위 자료를 불러오지 못했습니다')));});
 return box;}
I.researchScopeLive=Object.freeze({block});
})();
