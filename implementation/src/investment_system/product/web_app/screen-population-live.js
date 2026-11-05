/* 검색·계산 범위 (owner 2026-11-05 follow-up item 3) on the search home, the part that runs after IS2.ready. screen-search.js puts
   a [data-population] slot under the home; screen-search-live.js hands it to IS2.populationLive.fill(route, slot) from this file.
   - Two cards side by side (stacked on a phone), never merged: Universe504 (the official operating population: searchable codes
     from IS2.companies, QGV totals and official ranks from the public page IS2.qgv) and the current expansion population (Codex
     #482 current-expansion-research/1 through IS2.population). Each row keeps its own label: searchable, full-market denominator,
     eligible / excluded / unknown, financial rows, QGV computable, rankable.
   - The expansion result is private research: IS2.population.source() is NONE today and the card says so in words, with no number.
     A synthetic result says 합성 개발 검증; a partial roster says 부분 목록 · 전체 시장 분모 미확정 and shows no score or rank.
   - A file that breaks its contract is refused whole (code and path). The official population, scores, ranks and TARGET are not
     changed by anything here; changing the operating population, publishing or deploying needs its own approval.
   No request of its own (the page and the list are the layer's), no storage. */
(function(){
'use strict';
const I=window.IS2,{h}=I;
const phone=()=>{try{return window.matchMedia('(max-width:720px)').matches;}catch(_){return false;}};
const head=(title,hand)=>h('div',{class:'lb-head'},h('h3',{class:'stamp sub'},title),hand?h('span',{class:'hand'},hand):null);
function rowsOf(list,kind){
 return phone()
  ?h('ol',{class:'news-lines',dataset:{populationRows:kind}},list.map(x=>h('li',{dataset:{populationRow:x.id}},h('b',null,x.label),' · ',x.value,x.note?h('span',{class:'reason'},' · ',x.note):null)))
  :h('div',{class:'tbl-wrap'},h('table',{class:'tbl',dataset:{populationRows:kind}},
    h('thead',null,h('tr',null,['항목','수','설명'].map(t=>h('th',{scope:'col'},t)))),
    h('tbody',null,list.map(x=>h('tr',{dataset:{populationRow:x.id}},h('th',{scope:'row'},x.label),h('td',null,x.value),h('td',null,x.note||'–'))))));}
function universeCard(view){
 return h('div',{class:'sk card',dataset:{populationCard:'UNIVERSE504'}},head('Universe504','공식 운영 모집단'),h('p',{class:'hand'},view.basis),rowsOf(view.rows,'UNIVERSE504'));}
function expansionCard(src){const P=I.population;
 const card=(...kids)=>h('div',{class:'sk card',dataset:{populationCard:'EXPANSION'}},head('확장 모집단','연구 단계 · 공식 아님'),...kids);
 if(!src||src.state==='NONE')return card(h('p',{class:'reason',dataset:{populationState:'NONE',na:src&&src.code||'EXPANSION_NOT_CONNECTED'}},src&&src.text||P.TEXT.NONE));
 const r=P.validate(src.payload);
 if(!r.ok)return card(h('p',{class:'err',dataset:{populationState:'REFUSED',na:r.code}},'확장 모집단 파일이 계약과 달라 전부 읽지 않았습니다 · ',r.code,' · ',r.path));
 const v=P.expansionView(r.value);
 return card(v.synthetic?h('p',{class:'chip wait',dataset:{populationSynthetic:''}},P.TEXT.SYNTHETIC):null,
  h('p',{class:'hand',dataset:{populationState:v.partial?'PARTIAL':'ESTABLISHED'}},v.basis),
  v.partial?h('p',{class:'reason',dataset:{populationPartial:''}},P.TEXT.PARTIAL):null,
  rowsOf(v.rows,'EXPANSION'),
  v.reasons.length?h('p',{class:'reason',dataset:{populationReasons:String(v.reasons.length)}},'미확정 사유 · ',v.reasons.join(' · ')):null,
  h('p',{class:'meta'},'판 ',v.version));}
function fill(route,slot){const signal=route.signal,Q=I.qgv,C=I.companies,P=I.population;
 if(!slot||!P)return;
 // The home reads only its company index (web_app_data_layer_browser_test.js): QGV totals and ranks are counted only when the
 // public score file is already read in this tab (after #/qgv or a company page); otherwise the card says where they are.
 const held=(()=>{try{return I.data.state('sec-qgv2.json').state!=='NOT_READ';}catch(_){return false;}})();
 const universe=Promise.all([C.ready().catch(()=>null),held?Q.page({signal}).catch(()=>null):Promise.resolve(undefined)]).then(([,pg])=>{
  if(pg===undefined)return P.universeView({codes:C.list(),rows:undefined});
  let rows=null;try{rows=pg?Q.rows(pg,{scope:'UNIVERSE'}):null;}catch(_){rows=null;}
  return P.universeView({codes:C.list(),rows,asOf:pg&&pg.as_of?String(pg.as_of).slice(0,10):null});});
 Promise.all([universe,P.source().catch(()=>null)]).then(([u,src])=>{if(signal.aborted)return;
  slot.replaceChildren(head('검색·계산 범위','두 모집단은 따로 셉니다'),h('p',{class:'reason',dataset:{populationSeparate:''}},P.TEXT.SEPARATE),
   h('div',{class:'cards'},universeCard(u),expansionCard(src)));});}
I.populationLive=Object.freeze({fill});
})();
