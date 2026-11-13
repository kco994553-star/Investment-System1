/* 확장 발행사 찾기 (owner 2026-11-09 queue item 4; Codex #524 held-issuer-sharded/1): inside the common classification private panel
   of 0. 기업 검색 (private-expand-live.js expandedBlock asks IS2.expandedBrowse.block(anchor) once the checked bundle is painted).
   - Flow: 색인 불러오기 (one click, three private reads 5 s apart: manifest, index, coverage) → IS2.expandedIssuers.checkBundle against
     the anchor (the summary delivered in the same bundle: its bytes' SHA-256 and its checked held scope) → search box over the index
     → a result → 상세 보기 (one click, one shard read; shards already read stay in RAM for this bundle) → checkDetail → the issuer's
     classification, Q / G / V, factors, gate input, prices / technical state, input gaps and evidence, each as written.
   - A refused bundle shows its code and nothing else; a refused or missing detail is that issuer's 연결 오류, the index stays.
   - The population is the held financial sample (its own denominator), never Universe504 and never the whole market; a ticker is a
     catalog observation; nothing is ranked, summed or filled; null is 미산출, 0 is a value.
   - RAM only (dropped with the bundle); no storage; requests only inside a click, through IS2.prices.kisRead. */
(function(){
'use strict';
const I=window.IS2,{h}=I;
// Checked factor leaders per checked dual delivery in RAM (key = that RAM entry, so they go when it goes).
const LEAD=new WeakMap(),DISTS=new WeakMap();
// The checked 3/3/3 EPS input connection record (IS2.dualQgv.checkEps), held while the classification bundle is.
const EPS_HELD={value:null};
// The checked 3/3/3 Q input recovery record (IS2.dualQgv.checkQinput), the next input version; held and dropped the same way.
const Q_HELD={value:null};
const E=()=>I.expandedIssuers;
// The dual research deliveries in RAM are dropped with the classification bundle (접기 / 연결 끊기 / a dropped token).
try{if(I.classification&&typeof I.classification.subscribe==='function'&&I.dualQgv)I.classification.subscribe(()=>{const s=I.classification.state();
 if(!(s&&s.state==='OK'&&s.delivery==='PRIVATE')){I.dualQgv.ram.drop();EPS_HELD.value=null;Q_HELD.value=null;}});}catch(_){}
const CODE=/^[A-Z][A-Z0-9_]{1,63}$/;
const codeOf=e=>{const m=e&&typeof e.message==='string'?e.message:'';return CODE.test(m)?m:'PRIVATE_READ_FAILED';};
const WORD=Object.freeze({KIS_SERIES_NOT_FOUND:'전달 위치에 확장 발행사 묶음이 없습니다',ROUTE_NOT_FOUND:'비공개 서버에 이 경로가 아직 없습니다(Worker 배포 전)',
 REQUEST_INVALID:'비공개 서버가 이 요청을 받지 않습니다(Worker 배포 전일 수 있음)',AUTH_FORBIDDEN:'서버가 오너 확인을 거부했습니다 · 다시 로그인하세요',
 AUTH_REQUIRED:'로그인이 끝났습니다 · 다시 로그인하세요',RATE_LIMITED:'요청이 많아 잠시 뒤 다시',UPSTREAM_UNAVAILABLE:'비공개 자료 서버 응답 없음',
 SUMMARY_UNAVAILABLE:'같은 묶음의 확장 요약 집계가 검증되지 않아 열지 않습니다',SUMMARY_MISMATCH:'확장 묶음이 지금 받은 요약과 다른 결과를 가리킵니다'});
const say=c=>WORD[c]||'오류 · '+c;
const KIND=Object.freeze({RETAINED_INPUT:'보관 실자료',SYNTHETIC:'합성 자료 · 시험용'});
const LIMIT=20;
const dl=(rows,d)=>h('dl',{class:'card-body',dataset:d||{}},rows.filter(Boolean).map(([k,v,data])=>[h('dt',null,h('b',null,k)),h('dd',data?{dataset:data}:null,v)]));
const list=(items,d,empty)=>items.length?h('ul',{class:'news-lines',dataset:d},items.map(t=>h('li',null,t))):h('p',{class:'reason',dataset:d},empty);

function block(anchor){
 const st={bundle:null,shards:new Map(),busy:false};
 const state=h('p',{class:'reason',role:'status',dataset:{heldState:'IDLE'}});
 const area=h('div',{class:'cc-wrap',dataset:{heldArea:''}});
 const open=h('button',{type:'button',class:'btn',dataset:{heldOpen:''}},'확장 발행사 색인 불러오기');
 const set=(code,text)=>{state.dataset.heldState=code;state.textContent=text;};
 open.addEventListener('click',e=>{if(st.busy)return;st.busy=true;open.disabled=true;set('LOADING','비공개 자료 3개(목록표 · 색인 · 커버리지)를 차례로 불러옵니다 · 서버 요청 간격 5초');
  let p;try{p=I.prices.kisRead(e,[['classification','expanded_manifest'],['classification','expanded_index'],['classification','expanded_coverage']]);}catch(err){p=Promise.reject(err);}
  Promise.resolve(p).then(async([manifest,index,coverage])=>{
   const sha=anchor&&anchor.bytes instanceof Uint8Array?await E().sha256(anchor.bytes):null;
   const r=await E().checkBundle({manifest,index,coverage},{summarySha:sha,held:anchor?anchor.held:null});
   if(!r.ok){set('ERROR','확장 발행사 묶음을 쓰지 않음 · '+say(r.code)+' · '+r.code+' · '+r.path);open.disabled=false;return;}
   st.bundle=r.value;paintBundle();},
  err=>{const c=codeOf(err);set('ERROR',say(c));open.disabled=c!=='CANCELED'?false:false;}).finally(()=>{st.busy=false;});});

 function paintBundle(){const b=st.bundle,ctx=b.identity.context;open.hidden=true;
  set('READY','확장 발행사 '+b.issuer_count+'개 · 평가일 '+b.identity.valuation_date+' · '+(KIND[b.data_kind]||b.data_kind)+' · 목록표·색인·커버리지 검증됨');
  const q=h('input',{type:'search',id:'held-q',class:'tbl',autocomplete:'off',spellcheck:'false',enterkeyhint:'search',placeholder:'발행사 ID · 관측 티커 · 이름',dataset:{heldQuery:''}});
  const count=h('p',{class:'meta',role:'status',dataset:{heldCount:''}});
  const results=h('ul',{class:'news-lines',dataset:{heldResults:''}});
  const detail=h('div',{dataset:{heldDetailSlot:''}});
  const run=()=>{const hits=E().search(b.rows,q.value,LIMIT);
   count.textContent=q.value.trim()?'찾은 발행사 '+hits.length+'개'+(hits.length===LIMIT?' (앞 '+LIMIT+'개만 표시)':''):'발행사 ID · 관측 티커 · 이름으로 찾습니다';
   results.replaceChildren(...hits.map(r=>h('li',{dataset:{heldResult:r.issuer_id}},
    h('button',{type:'button',class:'lk',onclick:e=>show(e,r,detail)},r.issuer_id),' · ',r.observed_tickers.join(', ')||'관측 티커 없음',
    ' · 섹터 ',r.classification.sector&&r.classification.sector.status||'—',' · ',r.calculation_status)));};
  q.addEventListener('input',run);run();
  area.replaceChildren(
   dl([['모집단',ctx.population.id+' · 발행사 '+ctx.population.denominator+'개 · 운영504와 합치지 않음',{heldPopulation:String(ctx.population.denominator)}],
    ['점수의 비교집단',ctx.scoring_population.id+' · '+ctx.scoring_population.denominator+'개(보유 표본으로 다시 점수화하지 않음)'],
    ['분류',ctx.classification.dictionary_version+' + '+ctx.classification.mapping_version+' · 해시 '+ctx.classification.classification_hash.slice(0,12)+'…'],
    ['원결과',ctx.result_identity.preview_id.slice(0,12)+'… · 입력 '+ctx.input_as_of],
    ['생산자',b.identity.producer_sha.slice(0,12)+'… · 요약 '+b.identity.summary.sha256.slice(0,12)+'…']],{heldMeta:''}),
   coverageBlock(b.coverage),
   I.inputRepair?repairBlock():null,
   I.referenceView?referenceBlock():null,
   I.dualQgv&&I.referenceView?dualBlock():null,
   h('label',{for:'held-q',class:'meta'},'확장 발행사 찾기'),q,count,results,detail);}

 // Coverage by stage (IS2.expandedIssuers.coverageView): one list per unit in pipeline order, then the gate decisions, the total
 // failure reasons, the causes (overlapping, never summed) and each factor's own counts. Words and counts only; nothing derived.
 function coverageBlock(cov){const v=E().coverageView(cov);
  // Stages up to 세 축 동시, then the gate decisions, then the totals: the pipeline order on screen.
  const stageList=(u,late)=>h('ol',{class:'news-lines',dataset:{heldStages:u.unit+(late?':total':':axes'),heldStagesDen:String(u.denominator)}},
   u.stages.filter(s=>(s.group==='총점')===late).map(s=>h('li',{dataset:{heldStage:s.key,heldStageValue:s.text}},h('span',{class:'meta'},s.group,' · '),s.label,' ',h('b',null,s.text))));
  return h('details',{class:'why',dataset:{heldCoverage:''}},h('summary',null,'커버리지 단계 · 95% 목표 · 관문 · 미산출 사유 ▸'),
   h('p',{class:'hand',dataset:{heldBaseline:''}},'연구 기준선 · 보관 입력·기본 설정(입력 연결 수정 #527 뒤) · 공식 QGV 게시 결과의 커버리지 아님'),
   h('p',{class:'reason'},'단계마다 따로 셉니다 · 분류 확인 수나 원지표 수는 QGV 계산 완료율이 아님 · 95% 목표는 세 축 동시 + 최종 총점 기준'),
   ...v.map(c=>h('div',{class:'cc-wrap',dataset:{heldScope:c.scope}},h('h4',null,c.label),
    ...c.units.map(u=>h('div',null,h('p',null,h('b',null,u.label),' · 분모 ',String(u.denominator)),stageList(u,false))),
    h('p',{class:'meta'},'관문 판정 · ',c.gateUnit,' 기준'),
    c.gate.length?h('ul',{class:'news-lines',dataset:{heldGate:c.scope}},c.gate.map(g=>h('li',{dataset:{heldGateDecision:g.key}},g.text))):h('p',{class:'reason'},'관문 판정 수 전달 안 됨'),
    ...c.units.map(u=>h('div',null,h('p',{class:'meta'},u.label,' · 총점 단계'),stageList(u,true))),
    h('p',{class:'reason',dataset:{heldTarget:c.scope}},c.target),
    h('p',{class:'meta'},'최종 총점이 없는 행의 사유(행마다 하나)'),
    c.totalFailures.length?h('ul',{class:'news-lines',dataset:{heldTotalFail:c.scope}},c.totalFailures.map(t=>h('li',null,t))):h('p',{class:'reason'},'전달 안 됨'),
    c.unresolved?h('p',{class:'reason',dataset:{heldUnresolved:c.scope}},c.unresolved):null,
    h('p',{class:'meta'},'원인 · 발행사 기준 · 겹칠 수 있음 · 더하지 않음 · 관문은 위 판정별 수로만'),
    h('ul',{class:'news-lines',dataset:{heldCauses:c.scope}},c.causes.map(t=>h('li',null,t))),
    c.factors.length?h('details',{class:'why',dataset:{heldFactorCounts:c.scope}},h('summary',null,'요소별 수 · 실패 사유 (요소마다 따로 · 요소끼리 더하지 않음) ▸'),
     h('ul',{class:'news-lines'},c.factors.map(f=>h('li',{dataset:{heldFactorCount:f.id}},h('b',null,f.id),' · ',f.text,
      f.raw.length?[' · 원지표 없음: ',f.raw.join(', ')]:null,f.score.length?[' · 점수 없음: ',f.score.join(', ')]:null)))):null)),
   h('p',{class:'reason',dataset:{heldMarket:''}},E().marketText(cov)));}

 // 참조집단 확대 연구 (Codex #528, IS2.referenceView): its own click and one read, accepted only when its evaluation population is
 // the operating result of this checked bundle (population id / version / members hash / denominator, day, input and config hash).
 // A refusal or failed read is this block's error; the bundle, coverage, details and the repair block stay. Counts only.
 function referenceBlock(){const RV=I.referenceView;
  const rs=h('p',{class:'reason',role:'status',dataset:{referenceState:'IDLE'}},'비교 유형: 참조집단 확대 · 평가 대상은 그대로, 요소 점수의 참조집단만 넓힌 연구 · 공식 결과 아님');
  const slot=h('div',{dataset:{referenceArea:''}});
  const btn=h('button',{type:'button',class:'btn',dataset:{referenceOpen:''}},'참조집단 확대 연구 불러오기');
  const set=(c,t)=>{rs.dataset.referenceState=c;rs.textContent=t;};let busy=false;
  btn.addEventListener('click',e=>{if(busy||st.busy)return;busy=true;btn.disabled=true;set('LOADING','불러오는 중 · 연구 결과 1개');
   let p;try{p=I.prices.kisRead(e,[['classification','reference_view']]);}catch(err){p=Promise.reject(err);}
   Promise.resolve(p).then(([x])=>{const r=RV.validate(x,RV.anchorOf(st.bundle));
    if(!r.ok){set('ERROR','연구 결과를 쓰지 않음 · '+(r.code==='REFERENCE_RESULT_MISMATCH'?'지금 받은 결과와 다른 평가 집단의 연구입니다':r.code==='REFERENCE_DATE_MISMATCH'?'평가일이 다릅니다':r.code==='REFERENCE_CONFIG_MISMATCH'?'설정이 다릅니다':'형식 오류')
     +' · '+r.code+' · '+r.path+' · 위 묶음은 그대로');btn.disabled=false;return;}
    btn.hidden=true;paintReference(RV.view(r.value.view,r.value.scope,{sectorName:id=>I.taxonomy?I.taxonomy.sectorName(id):id}));},
   err=>{const c=codeOf(err);set('ERROR',(c==='KIS_SERIES_NOT_FOUND'?'전달 위치에 참조집단 연구 결과가 없습니다(배치 전)':say(c))+' · 위 묶음은 그대로');btn.disabled=false;})
   .finally(()=>{busy=false;});});
  function paintReference(v){set('READY',v.head);
   slot.replaceChildren(h('p',{class:'hand',dataset:{referenceNot:''}},v.not),h('p',{class:'reason'},v.limits),
    h('p',{class:'reason',dataset:{referencePopulation:'evaluation'}},v.evaluation),
    h('p',{class:'reason',dataset:{referencePopulation:'reference'}},v.reference),
    h('p',{class:'meta'},v.units),
    h('ul',{class:'news-lines',dataset:{referenceAxes:''}},v.axes.map(a=>h('li',{dataset:{referenceAxis:a.key}},a.text))),
    h('p',{class:'reason',dataset:{referenceNewAny:''}},v.newAny),
    h('details',{class:'why',dataset:{referenceGroups:String(v.groups.length)}},h('summary',null,'처리한 참조 그룹 ',String(v.groups.length),' · ',v.nFixed,' ▸'),
     list(v.groups.map(g=>g.text),{},'없음')),
    h('details',{class:'why',dataset:{referenceFactors:String(v.factors.length)}},h('summary',null,'바뀐 요소 ',String(v.factors.length),' ▸'),list(v.factors,{},'없음')),
    h('details',{class:'why',dataset:{referenceRows:String(v.rows.length)}},h('summary',null,'값이 바뀐 평가 행 ',String(v.rows.length),' ▸'),list(v.rows.map(r=>r.text),{},'없음')));}
  return h('div',{class:'sk card',dataset:{referenceBlock:''}},h('h4',null,'참조집단 확대 연구 (연구 · 운영 채택 안 됨)'),btn,rs,slot);}

 // 두 모형 연구 결과 (Codex #529 qgv-dual-delivery/1, IS2.dualQgv): one click per scope (운영504 / 보유1057), three reads 5 s apart
 // (manifest, summary, index), each file's own bytes checked against the manifest, accepted only when its evaluation population is
 // the result of this checked bundle. Checked deliveries stay in RAM (IS2.dualQgv.ram) for 2.1 until the bundle drops. A company's
 // models side by side is one more read (its detail file), cached for the delivery. A refusal is this block's error; the rest stays.
 function dualBlock(){const DQ=I.dualQgv,RV=I.referenceView;
  const rs=h('p',{class:'reason',role:'status',dataset:{dualState:'IDLE'}},'비교 유형: 연구 후보 U1·U2(통합)·S1(섹터, 핵심 요소 축소)와 3/3/3 후보 U2-333·U1-333(통합)·S1-333(섹터)는 따로 불러옴 · 운영 채택 안 됨 · 공식 QGV 아님 · 성과 미측정');
  // A slot is one scope × one generation (IS2.dualQgv.SLOTS): the 3/3/3 delivery of a scope is its own read and its own RAM slot.
  const slotWord=k=>DQ.SCOPES[DQ.SLOTS[k].scope].label+(DQ.SLOTS[k].gen==='Q333'?' 3/3/3':' 두 모형');
  const slot=h('div',{dataset:{dualArea:''}});
  const set=(c,t)=>{rs.dataset.dualState=c;rs.textContent=t;};let busy=false;
  const btns=Object.keys(DQ.SLOTS).map(scope=>{const S=DQ.SCOPES[DQ.SLOTS[scope].scope],b=h('button',{type:'button',class:'btn',dataset:{dualOpen:scope}},slotWord(scope)+' 결과 불러오기');
   // held1057 (평가 입력 = 참조 원천의 투영) also reads the producer's projection proof when staged (OPTIONAL: absent = 평가 입력 미검증).
   // operating504 (평가 입력 = 결과의 입력) also reads the producer's independent reference anchor when staged (OPTIONAL: absent = 참조 입력 대조 안 됨).
   const proof=S.input==='reference',reads=[...['dual_manifest','dual_summary','dual_index'].map(x=>['classification',x+'/'+scope]),['classification',(proof?'dual_lineage/':'dual_reference_anchor/')+scope,'OPTIONAL']];
   b.addEventListener('click',e=>{if(busy||st.busy)return;busy=true;b.disabled=true;set('LOADING','불러오는 중 · '+slotWord(scope)+' 목록표·요약·색인'+(proof?'·투영 증명 ':'·참조 기준 ')+reads.length+'개 · 서버 요청 간격 5초');
    let p;try{p=I.prices.kisRead(e,reads);}catch(err){p=Promise.reject(err);}
    Promise.resolve(p).then(async([manifest,summary,index,extra])=>{const r=await DQ.checkDelivery({manifest,summary,index,...(extra?(proof?{lineage:extra}:{reference_anchor:extra}):{})},{scope,anchor:RV.anchorOf(st.bundle),sha256:E().sha256});
     if(!r.ok){set('ERROR',slotWord(scope)+' 연구 결과를 쓰지 않음 · '+(r.code==='MODEL_GENERATION_MIXED'?'옛 후보와 3/3/3 후보가 한 묶음에 섞여 있습니다':r.code==='MODEL_GENERATION_SLOT'?'이 자리에 넣을 세대의 후보가 아닙니다':r.code==='CONFIG_VERSION_MISMATCH'||r.code==='MODEL_VERSION_UNKNOWN'?'등록된 모형 설정·버전과 다릅니다':r.code==='DUAL_POPULATION_MISMATCH'||r.code==='DUAL_INPUT_MISMATCH'?'지금 받은 결과와 다른 평가 집단·입력의 연구입니다':r.code==='DUAL_DATE_MISMATCH'?'평가일이 다릅니다':r.code==='BYTES_MISMATCH'?'파일이 목록표의 해시와 다릅니다':/^LINEAGE_/.test(r.code)?'평가 입력 투영 증명이 이 결과와 맞지 않습니다':/^REFERENCE_ANCHOR_/.test(r.code)?'참조 입력 독립 기준이 이 결과와 맞지 않습니다':'형식 오류')
      +' · '+r.code+' · '+r.path+' · 위 묶음은 그대로');b.disabled=false;return;}
     DQ.ram.set(scope,r.value);b.hidden=true;paint();},
    err=>{const c=codeOf(err);set('ERROR',(c==='KIS_SERIES_NOT_FOUND'?slotWord(scope)+' 결과가 전달 위치에 없습니다(배치 전)':say(c))+' · 위 묶음은 그대로');b.disabled=false;})
    .finally(()=>{busy=false;});});return b;});
  const sectorName=id=>I.taxonomy?I.taxonomy.sectorName(id):id;
  function paint(){epsDraw();qDraw();const held=Object.keys(DQ.SLOTS).filter(k=>DQ.ram.get(k));if(!held.length)return;
   set('READY','연구 후보 결과 · '+held.map(slotWord).join(' · ')+' · 목록표·요약·색인 검증됨 · 보관 결과만 · 화면 재계산 없음');
   slot.replaceChildren(h('p',{class:'hand',dataset:{dualKinds:''}},'새 후보 결과(U1·U2·S1 / 3/3/3 U2-333·U1-333·S1-333, 세대마다 따로 · 섞지 않음) · 연구 기준선(#527 보관 기본값 · #528 참조집단 확대)과 공식 QGV 게시 결과는 따로 · 지금 받은 묶음과 같은 평가일·모집단의 결과만 엶'),
    h('ul',{class:'news-lines',dataset:{dualRules:''}},DQ.RULES.map(t=>h('li',{class:'reason'},t))),...held.map(scopeCard));}
  function scopeCard(scope){const d=DQ.ram.get(scope).delivery,L=DQ.SLOTS[scope],S=DQ.SCOPES[L.scope],q=L.gen==='Q333';
   return h('div',{class:'cc-wrap',dataset:{dualScope:scope}},h('h4',null,S.label,q?' · 3/3/3':'',' · ',S.text),h('p',{class:'meta',dataset:{dualGeneration:L.gen}},DQ.GEN[L.gen]),
    L.scope==='operating504'?h('p',{class:'meta',dataset:{dualLeaderboard:''}},'2.1 리더보드의 QGV 모형에서 '+(q?'U2-333·U1-333·S1-333':'U1·U2·S1')+'을 고를 수 있음(이 결과를 RAM에서 읽음)'):null,
    ...d.models.map(k=>{const v=DQ.boardView(d,k);
     return h('details',{class:'why',dataset:{dualBoard:scope+':'+k}},h('summary',null,v.head,' ▸'),
      dl(v.states.map(([a,b])=>[a,b]),{dualStates:scope+':'+k}),
      v.config?h('p',{class:'reason',dataset:{dualConfig:scope+':'+k}},v.config):null,
      h('p',{class:'reason',dataset:{dualPopulation:'evaluation'}},v.population),h('p',{class:'reason',dataset:{dualPopulation:'reference'}},v.reference),
      h('p',{class:'meta'},v.kind,' · ',v.classification),
      h('ol',{class:'news-lines',dataset:{dualStages:scope+':'+k}},v.stages.map(x=>h('li',{dataset:{dualStage:x.key}},x.label,' ',h('b',null,x.text)))),
      h('p',{class:'reason',dataset:{dualTarget:scope+':'+k}},v.target),
      h('p',{class:'meta'},'결손 사유 · 겹칠 수 있음 · 더하지 않음'),list(v.causes,{dualCauses:k},'전달 안 됨'),
      v.upper?h('p',{class:'reason',dataset:{dualUpper:scope+':'+k}},v.upper):null,
      h('p',{class:'meta'},v.incomplete),h('p',{class:'reason'},v.market));}),
    // The 3/3/3 delivery has no factor leaders companion: its factor bands are read from the full ten-band path only.
    finder(scope,d),q?null:leadersBlock(scope),distBlock(scope));}
  // 개별 요소 상위권 (Codex qgv-dual-factor-leaders/1, optional companion of this checked delivery): its own click and two reads
  // (manifest + index), then one shard read per 보기 when not cached. Kept with the delivery in RAM (dropped with it). Only the
  // stored ranks 1..min(N, 20) of one model × ranking scope × factor, as delivered; nothing re-sorted, merged or filled.
  function leadersBlock(scope){const area=h('div',{class:'cc-wrap',dataset:{dualLeaders:scope}});
   const draw=()=>{const held=DQ.ram.get(scope);if(!held)return;const L=LEAD.get(held);
    if(!L){const b=h('button',{type:'button',class:'btn',dataset:{dualLeadersOpen:scope}},'개별 요소 상위권 불러오기 (목록표·색인 + 선택 계약)');
     const st=h('p',{class:'reason',role:'status',dataset:{dualLeadersState:'IDLE'}},'저장된 요소 순위의 앞부분(최대 20개)만 · 다시 정렬하지 않음');
     b.addEventListener('click',e=>{if(busy)return;busy=true;b.disabled=true;st.dataset.dualLeadersState='LOADING';st.textContent='불러오는 중 · 요소 상위권 목록표·색인·선택 계약 4개(선택 계약은 없으면 없음) · 서버 요청 간격 5초';
      let p;try{p=I.prices.kisRead(e,[['classification','dual_leaders_manifest/'+scope],['classification','dual_leaders_index/'+scope],
       ['classification','dual_leaders_selection_manifest/'+scope,'OPTIONAL'],['classification','dual_leaders_selection/'+scope,'OPTIONAL']]);}catch(err){p=Promise.reject(err);}
      Promise.resolve(p).then(async([manifest,index,selManifest,selBody])=>{let r=await DQ.checkLeaders({manifest,index},held.delivery,E().sha256),sel=null;
       // The selection contract is optional, but one that is delivered must check: half of it, or one that disagrees, refuses the click.
       if(r.ok&&(selManifest||selBody)){const q=selManifest&&selBody?await DQ.checkSelection({manifest:selManifest,body:selBody},r.value,E().sha256):{ok:false,code:'SELECTION_INCOMPLETE',path:'selection'};
        if(q.ok)sel=q.value;else r=q;}
       if(!r.ok){st.dataset.dualLeadersState='ERROR';st.textContent='요소 상위권을 쓰지 않음 · '+(r.code==='LEADERS_SOURCE_MISMATCH'||r.code==='LEADERS_BOARD_MISMATCH'||r.code==='SELECTION_SOURCE_MISMATCH'?'이 연구 결과가 아닌 다른 전달본의 순위입니다':r.code==='BYTES_MISMATCH'?'파일이 목록표의 해시와 다릅니다':'형식 오류')+' · '+r.code+' · '+r.path+' · 위 결과는 그대로';b.disabled=false;return;}
       LEAD.set(held,{value:r.value,selection:sel,shards:new Map(),board:null,group:null});draw();},
      err=>{const c=codeOf(err);st.dataset.dualLeadersState='ERROR';st.textContent=(c==='KIS_SERIES_NOT_FOUND'?'요소 상위권 파일이 전달 위치에 없습니다(배치 전)':say(c))+' · 위 결과는 그대로';b.disabled=false;})
      .finally(()=>{busy=false;});});
     area.replaceChildren(h('h5',null,'개별 요소 상위권'),b,st);return;}
    const mid='dual-lb-'+scope,gid='dual-lg-'+scope,M=DQ.MODELS;
    const mSel=h('select',{id:mid,dataset:{dualLeadersModel:scope}},h('option',{value:''},'모형 선택'),...held.delivery.models.map(k=>h('option',{value:k,selected:L.board===k},M[k].label)));
    mSel.addEventListener('change',()=>{L.board=mSel.value||null;L.group=null;draw();});
    const groups=L.board?DQ.leaderGroups(L.value,L.board):[],byScope=new Map();for(const g of groups){if(!byScope.has(g.ranking_scope))byScope.set(g.ranking_scope,[]);byScope.get(g.ranking_scope).push(g);}
    const gSel=h('select',{id:gid,disabled:!L.board,dataset:{dualLeadersGroup:scope}},h('option',{value:''},L.board?'요소 선택 · '+groups.length+'개':'모형을 먼저 고르세요'),
     ...[...byScope].map(([rs,gs])=>h('optgroup',{label:rs==='COMMON'?'공통 순위':rs.split('|').slice(1).map((x,i)=>i===0?sectorName(x):x).join(' · ')},
      ...gs.map(g=>h('option',{value:g.group_id,selected:L.group===g.group_id},g.variant_id+' · 유효 '+g.evaluation_valid_n)))));
    gSel.addEventListener('change',()=>{L.group=gSel.value||null;draw();});
    const show=h('button',{type:'button',class:'btn',disabled:!L.group,dataset:{dualLeadersShow:scope}},'보기');
    const out=h('div',{dataset:{dualLeadersOut:scope}}),cmpL=h('div',{dataset:{dualCompare:scope+':leaders'}});
    const render=g=>{const v=DQ.leaderView(g,{sectorName,selection:L.selection?L.selection.groups.get(g.group_id):null});const th=t=>h('th',{scope:'col'},t);
     const selLine=h('p',{class:v.selectionOk?'meta':'hand err',dataset:{dualLeadersSelection:v.selectionOk?(L.selection?'MATCHED':'NONE'):'MISMATCH'}},v.sel);
     if(!v.selectionOk){out.replaceChildren(selLine);return;}
     // 분위 구간 (owner 2026-11-12): all ten bands of this group from the stored boundaries; choosing one only narrows the rows shown.
     const cur=v.bands.find(b=>b.decile===L.band)||null,bid='dual-band-'+scope;
     const bSel=v.bands.length?h('select',{id:bid,dataset:{dualLeadersBand:scope}},h('option',{value:''},'전체 구간(미리보기 순서)'),
      ...v.bands.map(b=>h('option',{value:String(b.decile),selected:L.band===b.decile},b.band+' · 분위 '+b.decile+' · '+b.count+'개'))):null;
     if(bSel)bSel.addEventListener('change',()=>{L.band=bSel.value?Number(bSel.value):null;render(g);});
     const shown=cur?v.rows.filter(r=>r.d===cur.decile):v.rows,byId=new Map(held.delivery.rows.map(r=>[r.company_id,r]));
     const who=id=>{const row=byId.get(id);return row?h('button',{type:'button',class:'lk',dataset:{dualLeaderOpen:id},onclick:e=>compare(e,scope,row,cmpL)},id):id;};
     out.replaceChildren(h('p',{class:'hand',dataset:{dualLeadersHead:g.group_id}},M[g.board].label,' · ',v.head),h('p',{class:'meta'},v.counts),h('p',{class:'reason',dataset:{dualLeadersPreview:''}},v.preview),
      h('p',{class:'reason',dataset:{dualLeadersD10:''}},v.d10),selLine,
      bSel?h('div',{class:'sort-row'},h('label',{for:bid},'분위 구간'),bSel):h('p',{class:'meta',dataset:{dualBandsNone:''}},'분위 구간 없음 · ',v.d10),
      cur?h('p',{class:'reason',dataset:{dualBand:String(cur.decile),dualBandComplete:String(cur.complete)}},cur.band,' · 분위 ',String(cur.decile),' · ',String(cur.count),'개 · ',cur.ranks,' · ',cur.scores,' · ',cur.members):null,
      h('details',{class:'why',dataset:{dualBandRule:''}},h('summary',null,'분위 읽는 법 ▸'),list(DQ.DECILE_RULE,{dualBandRules:''},'')),
      shown.length?h('div',{class:'tbl-wrap'},h('table',{class:'tbl',dataset:{dualLeadersTable:g.group_id}},h('caption',null,'저장된 순위 그대로 · 같은 모형·범위·요소 안에서만 비교 · 기업을 누르면 세 모형 상세'),
       h('thead',null,h('tr',null,th('순위'),th('기업'),th('요소 점수'),th('분위 구간'),th('구분'))),
       h('tbody',null,...shown.map(r=>h('tr',{dataset:{dualLeader:r.company_id}},h('td',null,r.rank),h('td',null,who(r.company_id)),h('td',null,r.score),h('td',null,r.decile),h('td',null,r.kind))))))
      :h('p',{class:'reason',dataset:{dualLeadersEmpty:''}},cur?'이 구간의 기업은 이 미리보기에 없음 · 전체 구성 목록은 분할 전달 대기':'이 요소에 저장된 순위가 없음'),cmpL);};
    show.addEventListener('click',e=>{const g=L.value.groups.find(x=>x.group_id===L.group);if(!g||busy)return;const cached=L.shards.get(g.file);
     if(cached){render(cached.get(g.group_id));return;}
     busy=true;show.disabled=true;out.replaceChildren(h('p',{class:'reason',dataset:{dualLeadersState:'LOADING'}},'요소 순위 파일 1개를 불러옵니다'));
     let p;try{p=I.prices.kisRead(e,[['classification','dual_leaders_detail/'+scope+'/'+g.file.slice(15,18)]]);}catch(err){p=Promise.reject(err);}
     Promise.resolve(p).then(async([x])=>{const r=await DQ.checkLeaderShard(x,g.file,L.value,E().sha256);
      if(!r.ok){out.replaceChildren(h('p',{class:'reason',dataset:{dualLeadersState:'ERROR'}},'이 순위 파일을 쓰지 않음 · '+r.code+' · '+r.path));return;}
      L.shards.set(g.file,r.value);if(L.group===g.group_id)render(r.value.get(g.group_id));},
     err=>{out.replaceChildren(h('p',{class:'reason',dataset:{dualLeadersState:'ERROR'}},'연결 오류 · '+say(codeOf(err))));}).finally(()=>{busy=false;show.disabled=!L.group;});});
    area.replaceChildren(h('h5',null,'개별 요소 상위권'),h('p',{class:'meta',dataset:{dualLeadersState:'READY'}},'목록표·색인 검증됨',L.selection?' · 선택 계약 검증됨':' · 선택 계약 없음',' · 요소 묶음 ',String(L.value.groups.length),'개(유효 0인 요소 포함 · 기업 수 아님) · 저장된 순위의 앞부분만'),
     h('div',{class:'sort-row'},h('label',{for:mid},'모형'),mSel),h('div',{class:'sort-row'},h('label',{for:gid},'요소'),gSel),h('div',{class:'load-row'},show),out);
    const g=L.group&&L.shards.size?L.value.groups.find(x=>x.group_id===L.group):null;if(g&&L.shards.has(g.file))render(L.shards.get(g.file).get(g.group_id));};
   draw();return area;}
  // 요소 10분위 전체 조회 (owner 2026-11-12; Codex qgv-dual-factor-distribution/1, optional companion of this checked delivery):
  // its own click and two reads (manifest + index), then the parts of the chosen group (once each, kept in RAM with the delivery).
  // 모형 → 요소(비교 범위별) → 보기 → 분위 구간(10개 + 분위 없음) → 기업 목록(50개씩) → 기업 상세. Band, page and model only
  // choose what is shown: every rank, band and N is the producer's. A part that fails to load is an error, never an empty band.
  function distBlock(scope){const area=h('div',{class:'cc-wrap',dataset:{dualDist:scope}});
   const draw=()=>{const held=DQ.ram.get(scope);if(!held)return;const S=DISTS.get(held);
    if(!S){const b=h('button',{type:'button',class:'btn',dataset:{dualDistOpen:scope}},'요소 10분위 전체 불러오기 (목록표·색인)');
     const st=h('p',{class:'reason',role:'status',dataset:{dualDistState:'IDLE'}},'요소마다 평가 기업 전체를 10개 구간으로 · 위 상위권은 상위 20개 미리보기');
     // The all-bin routing (Codex qgv-dual-factor-bins/1) is OPTIONAL, but one that is delivered must check: half of it, or one that
     // disagrees, refuses the click (the distribution alone is never shown as routed).
     b.addEventListener('click',e=>{if(busy)return;busy=true;b.disabled=true;st.dataset.dualDistState='LOADING';st.textContent='불러오는 중 · 10분위 목록표·색인 + 구간 색인 4개(구간 색인은 없으면 없음) · 서버 요청 간격 5초';
      let p;try{p=I.prices.kisRead(e,[['classification','dual_dist_manifest/'+scope],['classification','dual_dist_index/'+scope],
       ['classification','dual_bins_manifest/'+scope,'OPTIONAL'],['classification','dual_bins_index/'+scope,'OPTIONAL']]);}catch(err){p=Promise.reject(err);}
      Promise.resolve(p).then(async([manifest,index,binsManifest,binsIndex])=>{let r=await DQ.checkDistribution({manifest,index},held.delivery,E().sha256),bins=null;
       if(r.ok&&(binsManifest||binsIndex)){const q=binsManifest&&binsIndex?await DQ.checkBins({manifest:binsManifest,index:binsIndex},r.value,E().sha256):{ok:false,code:'BINS_INCOMPLETE',path:'bins'};
        if(q.ok)bins=q.value;else r=q;}
       if(!r.ok){st.dataset.dualDistState='ERROR';st.textContent='10분위 자료를 쓰지 않음 · '+(r.code==='DIST_BOARD_MISMATCH'||r.code==='COMPANIES_MISMATCH'?'이 연구 결과가 아닌 다른 결과의 분위입니다'
        :r.code==='BINS_SOURCE_MISMATCH'?'구간 색인이 이 분위 파일의 것이 아닙니다':r.code==='BINS_INCOMPLETE'?'구간 색인 파일이 반만 있습니다'
        :r.code==='POLICY_NOT_CONFIRMED'?'활성화하지 않은 별도 연구 후보의 표시 기준입니다(저장된 분위 규칙만 씀)':r.code==='BYTES_MISMATCH'?'파일이 목록표의 해시와 다릅니다':'형식 오류')+' · '+r.code+' · '+r.path+' · 위 결과는 그대로';b.disabled=false;return;}
       DISTS.set(held,{value:r.value,bins,binParts:new Map(),parts:new Map(),board:null,group:null,band:null,page:0,view:null,routed:false});draw();},
      err=>{const c=codeOf(err);st.dataset.dualDistState='ERROR';st.textContent=(c==='KIS_SERIES_NOT_FOUND'?'10분위 전체 자료가 전달 위치에 없습니다(배치 전) · 위 상위 20개 미리보기만 있음 · 10분위 전체 조회 아님':say(c))+' · 위 결과는 그대로';b.disabled=false;})
      .finally(()=>{busy=false;});});
     area.replaceChildren(h('h5',null,'요소 10분위 전체'),b,st);return;}
    const D=S.value,M=DQ.MODELS,mid='dual-db-'+scope,gid='dual-dg-'+scope;
    const mSel=h('select',{id:mid,dataset:{dualDistModel:scope}},h('option',{value:''},'모형 선택'),...held.delivery.models.filter(k=>D.boards[k]).map(k=>h('option',{value:k,selected:S.board===k},M[k].label)));
    mSel.addEventListener('change',()=>{S.board=mSel.value||null;S.group=null;S.view=null;S.band=null;S.page=0;draw();});
    const groups=S.board?D.groups.filter(g=>g.board===S.board):[],byScope=new Map();for(const g of groups){if(!byScope.has(g.ranking_scope))byScope.set(g.ranking_scope,[]);byScope.get(g.ranking_scope).push(g);}
    const gSel=h('select',{id:gid,disabled:!S.board,dataset:{dualDistGroup:scope}},h('option',{value:''},S.board?'요소 선택 · '+groups.length+'개':'모형을 먼저 고르세요'),
     ...[...byScope].map(([rs,gs])=>h('optgroup',{label:rs==='COMMON'?'통합 비교집단':'섹터 · '+rs.split('|').slice(1).map((x,i)=>i===0?sectorName(x):x).join(' · ')},
      ...gs.map(g=>h('option',{value:g.group_id,selected:S.group===g.group_id},g.variant_id+' · 유효 '+g.evaluation_valid_n+' / '+g.evaluation_rows_in_scope)))));
    gSel.addEventListener('change',()=>{S.group=gSel.value||null;S.view=null;S.band=null;S.page=0;draw();});
    const show=h('button',{type:'button',class:'btn',disabled:!S.group,dataset:{dualDistShow:scope}},'보기');
    const out=h('div',{dataset:{dualDistOut:scope}}),cmpD=h('div',{dataset:{dualCompare:scope+':dist'}}),byId=new Map(held.delivery.rows.map(r=>[r.company_id,r]));
    const render=()=>{const G=S.view;if(!G)return;const v=DQ.distributionView(D,G,{band:S.band,page:S.page,sectorName}),th=t=>h('th',{scope:'col'},t);
     const pick=b=>{S.band=b;S.page=0;render();};
     const bandBtn=(key,label,count,on)=>{const x=h('button',{type:'button',class:'chip','aria-pressed':String(on),dataset:{dualDistBand:String(key)}},label+' · '+count+'개');x.addEventListener('click',()=>pick(key));return x;};
     const who=id=>{const row=byId.get(id);return row?h('button',{type:'button',class:'lk',dataset:{dualDistOpenCo:id},onclick:e=>compare(e,scope,row,cmpD)},id):id;};
     const pager=v.pages>1?h('div',{class:'load-row',dataset:{dualDistPager:''}},
       (()=>{const x=h('button',{type:'button',class:'btn',disabled:v.page===0,dataset:{dualDistPage:'prev'}},'이전 50개');x.addEventListener('click',()=>{S.page=v.page-1;render();});return x;})(),
       h('span',{class:'meta',dataset:{dualDistRange:''}},v.range+' · '+(v.page+1)+' / '+v.pages+'쪽'),
       (()=>{const x=h('button',{type:'button',class:'btn',disabled:v.page>=v.pages-1,dataset:{dualDistPage:'next'}},'다음 50개');x.addEventListener('click',()=>{S.page=v.page+1;render();});return x;})()):null;
     out.replaceChildren(h('p',{class:'hand',dataset:{dualDistHead:G.group.group_id}},v.head),
      h('p',{class:'meta',dataset:{dualDistRouted:String(S.routed)}},S.routed?'전체 구성원 · 구간 색인과 대조됨(10개 구간의 개수·저장 순위·구성원 해시 일치)':'전체 구성원 · 분위 파일 전체 행으로 확인(구간 색인 없음)'),h('p',{class:'meta',dataset:{dualDistContext:''}},v.context),
      h('p',{class:'meta'},v.members),h('p',{class:v.inputVerified?'meta':'reason',dataset:{dualDistInput:String(v.inputVerified)}},v.input),
      h('p',{class:'reason',dataset:{dualDistPolicy:D.display_policy}},v.policy),
      v.ties.length?h('details',{class:'why',dataset:{dualDistTies:String(v.ties.length)}},h('summary',null,'같은 점수가 갈린 경계 '+v.ties.length+'곳 ▸'),
       h('ul',{class:'news-lines'},...v.ties.map(t=>h('li',null,t.text)))):null,
      h('p',{class:'meta'},'구간을 고르면 그 구간의 기업만 보임 · 순위·분위·분모는 생산자 값 그대로'),
      h('div',{class:'chips',role:'group','aria-label':'분위 구간',dataset:{dualDistBands:G.group.group_id}},...v.bands.map(b=>bandBtn(b.decile,b.label,b.count,b.selected)),
       bandBtn('NONE','분위 없음',v.unavailable.count,v.unavailable.selected)),
      v.unavailable.reasons.length?h('p',{class:'meta',dataset:{dualDistReasons:''}},'분위 없음 사유 · ',v.unavailable.reasons.join(' · ')):null,
      v.selected?h('p',{class:'reason',role:'status',dataset:{dualDistSelected:String(S.band)}},v.selected):h('p',{class:'meta',dataset:{dualDistSelected:''}},'구간을 고르세요'),
      v.rows.length?h('div',{class:'tbl-wrap'},h('table',{class:'tbl',dataset:{dualDistTable:G.group.group_id}},h('caption',null,'저장된 순위 그대로 · 같은 모형·비교집단·요소 안에서만 · 기업을 누르면 세 모형 상세'),
       h('thead',null,h('tr',null,th('순위'),th('기업'),th('요소 점수'),th('분위 구간'),th('구분'))),
       h('tbody',null,...v.rows.map(r=>h('tr',{dataset:{dualDistRow:r.company_id}},h('td',null,r.rank),h('td',null,who(r.company_id)),h('td',null,r.score),h('td',null,r.band),h('td',null,r.kind))))))
      :v.selected?h('p',{class:'reason',dataset:{dualDistEmpty:''}},'이 구간의 기업 0개 · 확인된 빈 구간(불러오기 실패 아님)'):null,
      pager,cmpD);};
    show.addEventListener('click',e=>{const g=D.groups.find(x=>x.group_id===S.group);if(!g||busy)return;const need=g.files.filter(f=>!S.parts.has(f));
     const binFile=S.bins?S.bins.routes[g.group_id]:null,needBin=binFile&&!S.binParts.has(binFile)?[binFile]:[];
     const fail=(w,c,pa)=>out.replaceChildren(h('p',{class:'reason',dataset:{dualDistState:'ERROR'}},w+' · '+c+' · '+pa+' · 기업 없음이 아님'));
     // Every bin of the group is checked against the routing (count, saved ranks, members hash) before any band is shown.
     const finish=async()=>{const G=DQ.distributionGroup(D,g.group_id,S.parts);
      if(!G.ok){fail('이 요소의 분위를 쓰지 않음',G.code,G.path);return;}
      if(S.bins){const m=await DQ.binsMatchGroup(S.binParts.get(binFile).get(g.group_id),G.value,E().sha256);if(!m.ok){fail('구간 색인과 이 요소의 분위가 다름 · 쓰지 않음',m.code,m.path);return;}}
      if(S.group!==g.group_id)return;S.view=G.value;S.routed=!!S.bins;render();};
     if(!need.length&&!needBin.length){finish();return;}
     busy=true;show.disabled=true;out.replaceChildren(h('p',{class:'reason',dataset:{dualDistState:'LOADING'}},'분위 파일 '+need.length+'개'+(needBin.length?' + 구간 색인 1개':'')+'를 불러옵니다'));
     let p;try{p=I.prices.kisRead(e,[...need.map(f=>['classification','dual_dist_detail/'+scope+'/'+f.slice(13,16)]),...needBin.map(f=>['classification','dual_bins_detail/'+scope+'/'+f.slice(5,8)])]);}catch(err){p=Promise.reject(err);}
     Promise.resolve(p).then(async xs=>{for(let i=0;i<need.length;i++){const r=await DQ.checkDistributionPart(xs[i],need[i],D,E().sha256);
       if(!r.ok){fail('이 분위 파일을 쓰지 않음',r.code,r.path);return;}S.parts.set(need[i],r.value);}
      if(needBin.length){const r=await DQ.checkBinsPart(xs[need.length],binFile,S.bins,E().sha256);if(!r.ok){fail('이 구간 색인 파일을 쓰지 않음',r.code,r.path);return;}S.binParts.set(binFile,r.value);}
      if(S.group===g.group_id)await finish();},
     err=>{out.replaceChildren(h('p',{class:'reason',dataset:{dualDistState:'ERROR'}},'분위 파일을 불러오지 못함 · '+say(codeOf(err))+' · 기업 없음이 아님'));}).finally(()=>{busy=false;show.disabled=!S.group;});});
    area.replaceChildren(h('h5',null,'요소 10분위 전체'),h('p',{class:'meta',dataset:{dualDistState:'READY'}},'목록표·색인 검증됨 · 요소 묶음 ',String(D.groups.length),'개(기업 수 아님) · ',
      D.display_policy==='stored-evaluation-deciles/1'?'저장된 평가 순위 분위':'연구 표시 후보(합성)',' · 평가 기업 전체 · 분위 없음도 사유와 함께',S.bins?' · 구간 색인 검증됨':' · 구간 색인 없음'),
     h('div',{class:'sort-row'},h('label',{for:mid},'모형'),mSel),h('div',{class:'sort-row'},h('label',{for:gid},'요소 · 비교 범위'),gSel),h('div',{class:'load-row'},show),out);
    if(S.view)render();};
   draw();return area;}
  function finder(scope,d){const id='dual-q-'+scope,q=h('input',{type:'search',id,class:'tbl',autocomplete:'off',spellcheck:'false',enterkeyhint:'search',placeholder:'기업 코드 · 발행사 ID',dataset:{dualQuery:scope}});
   const out=h('ul',{class:'news-lines',dataset:{dualResults:scope}}),cmp=h('div',{dataset:{dualCompare:scope}});
   const run=()=>{const t=q.value.trim().toLowerCase();const hits=t?d.rows.filter(r=>r.company_id.toLowerCase().includes(t)||(r.issuer_id||'').toLowerCase().includes(t)).slice(0,LIMIT):[];
    out.replaceChildren(...hits.map(r=>h('li',{dataset:{dualResult:r.company_id}},h('button',{type:'button',class:'lk',onclick:e=>compare(e,scope,r,cmp)},r.company_id),' · 발행사 ',r.issuer_id||'—')));};
   q.addEventListener('input',run);
   return h('div',{class:'cc-wrap'},h('label',{for:id,class:'meta'},'기업 상세 · 세 모형 나란히 보기'),q,out,cmp);}
  function compare(e,scope,row,slotC){if(busy)return;openDetail(e,scope,row,slotC);}
  // 3/3/3 EPS 입력 연결 단계 (owner 2026-11-13 「3/3/3 화면 연결 우선」 §1, §3; Codex #534): its own click, four reads checked against
  // Main's staged index. A progress record of the new input version, not results: no score, rank or band from it; each scope says
  // which input version the 3/3/3 results on screen are (their result hashes against this comparison's before / after).
  const epsArea=h('div',{class:'cc-wrap',dataset:{dualEps:''}});
  function epsDraw(){const R=EPS_HELD.value,title=h('h5',null,'3/3/3 EPS 입력 연결 단계 (진행 기록 · 결과 묶음 아님)');
   if(!R){const b=h('button',{type:'button',class:'btn',dataset:{dualEpsOpen:''}},'3/3/3 EPS 입력 연결 단계 불러오기');
    const st=h('p',{class:'reason',role:'status',dataset:{dualEpsState:'IDLE'}},'새 입력 버전의 단계별 집계 · 점수·순위·분위를 바꾸지 않음');
    b.addEventListener('click',e=>{if(busy)return;busy=true;b.disabled=true;st.dataset.dualEpsState='LOADING';st.textContent='불러오는 중 · 목록·진단 요약·실행 비교·다음 입력 4개 · 서버 요청 간격 5초';
     let p;try{p=I.prices.kisRead(e,[['classification','dual_eps_index'],['classification','dual_eps_diag'],['classification','dual_eps_compare'],['classification','dual_eps_inputs']]);}catch(err){p=Promise.reject(err);}
     Promise.resolve(p).then(async([index,diagnostic,comparison,continuation])=>{const r=await DQ.checkEps({index,diagnostic,comparison,continuation},E().sha256);
      if(!r.ok){st.dataset.dualEpsState='ERROR';st.textContent='EPS 단계 자료를 쓰지 않음 · '+(r.code==='BYTES_MISMATCH'?'파일이 목록의 해시와 다릅니다':r.code==='CONFIG_VERSION_MISMATCH'?'등록된 모형 설정과 다른 실행입니다':r.code==='EPS_RESULT_DELIVERY'?'결과 묶음은 이 칸으로 읽지 않습니다':'형식 오류')+' · '+r.code+' · '+r.path;b.disabled=false;return;}
      EPS_HELD.value=r.value;epsDraw();qDraw();},
     err=>{const c=codeOf(err);st.dataset.dualEpsState='ERROR';st.textContent=(c==='KIS_SERIES_NOT_FOUND'?'EPS 단계 자료가 전달 위치에 없습니다(배치 전)':say(c));b.disabled=false;}).finally(()=>{busy=false;});});
    epsArea.replaceChildren(title,b,st);return;}
   epsArea.replaceChildren(title,h('p',{class:'meta',dataset:{dualEpsState:'READY'}},'목록·파일 해시 검증됨 · 실행 코드 ',R.index.source.execution_sha.slice(0,12),' · 생산자 ',R.index.source.producer_sha.slice(0,12)),
    ...['operating504','held1057'].map(scope=>{const held=DQ.ram.get(scope+'@333'),v=DQ.epsView(R,scope,held?held.delivery:null);
     return h('div',{class:'cc-wrap',dataset:{dualEpsScope:scope}},h('h5',null,v.label),
      h('p',{class:'reason',dataset:{dualEpsScreen:v.onScreen}},v.screen),h('p',{class:'reason',dataset:{dualEpsDelivery:''}},v.delivery),
      dl(v.times,{dualEpsTimes:scope}),h('p',{class:'meta',dataset:{dualEpsVersion:scope}},v.version),
      h('ol',{class:'news-lines',dataset:{dualEpsStages:scope}},v.stages.map(([a,b])=>h('li',null,h('b',null,a),' · ',b))),
      dl(v.separate,{dualEpsSeparate:scope}),h('p',{class:'reason',dataset:{dualEpsBounds:scope}},v.bounds),
      h('details',{class:'why'},h('summary',null,'끝값 진단 분류 ▸'),list(v.endpoints,{dualEpsEndpoints:scope},'')));}));}
  // 3/3/3 Q 입력 복구 (owner 2026-11-13 §1 Q 결손·공식 관문 결손 별도 줄, §3 시각; Codex #534 4352c8ec): its own click, three reads
  // checked against Main's index. The next input version after the EPS step; diagnostic counts and clocks only, never a score.
  const qArea=h('div',{class:'cc-wrap',dataset:{dualQ:''}});
  function qDraw(){const R=Q_HELD.value,title=h('h5',null,'3/3/3 Q 입력 복구 (회고 검토 · 진행 기록 · 결과 묶음 아님)');
   if(!R){const b=h('button',{type:'button',class:'btn',dataset:{dualQOpen:''}},'3/3/3 Q 입력 복구 불러오기');
    const st=h('p',{class:'reason',role:'status',dataset:{dualQState:'IDLE'}},'Q 결손 원인 · 공식 관문 판정 상태 · 공식 입력 연결 · 평가일·입력 마감·검토 시각 · 점수·순위·분위를 바꾸지 않음');
    b.addEventListener('click',e=>{if(busy)return;busy=true;b.disabled=true;st.dataset.dualQState='LOADING';st.textContent='불러오는 중 · 목록·진단 요약·실행 비교 3개 · 서버 요청 간격 5초';
     let p;try{p=I.prices.kisRead(e,[['classification','dual_q_index'],['classification','dual_q_diag'],['classification','dual_q_compare']]);}catch(err){p=Promise.reject(err);}
     Promise.resolve(p).then(async([index,diagnostic,comparison])=>{const r=await DQ.checkQinput({index,diagnostic,comparison},E().sha256);
      if(!r.ok){st.dataset.dualQState='ERROR';st.textContent='Q 입력 복구 자료를 쓰지 않음 · '+(r.code==='BYTES_MISMATCH'?'파일이 목록의 해시와 다릅니다':r.code==='CONFIG_VERSION_MISMATCH'?'등록된 모형 설정과 다른 실행입니다':r.code==='Q_SUM'?'원인별 합계가 발행사 수와 다릅니다':r.code==='Q_RESULT_DELIVERY'?'결과 묶음은 이 칸으로 읽지 않습니다':'형식 오류')+' · '+r.code+' · '+r.path;b.disabled=false;return;}
      Q_HELD.value=r.value;qDraw();},
     err=>{const c=codeOf(err);st.dataset.dualQState='ERROR';st.textContent=(c==='KIS_SERIES_NOT_FOUND'?'Q 입력 복구 자료가 전달 위치에 없습니다(배치 전)':say(c));b.disabled=false;}).finally(()=>{busy=false;});});
    qArea.replaceChildren(title,b,st);return;}
   const rr=R.index.review_records;
   qArea.replaceChildren(title,h('p',{class:'meta',dataset:{dualQState:'READY'}},'목록·파일 해시 검증됨 · 실행 코드 ',R.index.source.execution_sha.slice(0,12),' · 생산자 ',R.index.source.producer_sha.slice(0,12)),
    h('p',{class:'reason',dataset:{dualQReviews:''}},'근거 검토 기록(스냅숏별) 운영 평가 '+rr.operating+' · 운영 참조 '+rr.operating_reference+' · 보유 평가 '+rr.held+' · 보유 참조 '+rr.catalog_reference+' · 주장마다 따로 검토 · 한 주장의 확인이 다른 주장을 확인하지 않음'),
    ...['operating504','held1057'].map(scope=>{const held=DQ.ram.get(scope+'@333'),v=DQ.qinputView(R,scope,EPS_HELD.value,held?held.delivery:null);
     return h('div',{class:'cc-wrap',dataset:{dualQScope:scope}},h('h5',null,v.label),
      h('p',{class:'reason',dataset:{dualQScreen:v.onScreen}},v.screen),h('p',{class:'reason',dataset:{dualQChain:v.chain}},v.chainText),
      h('p',{class:'reason',dataset:{dualQDelivery:''}},v.delivery),h('p',{class:'meta'},v.kind),
      dl(v.times,{dualQTimes:scope}),h('p',{class:'meta',dataset:{dualQVersion:scope}},v.version),
      h('ol',{class:'news-lines',dataset:{dualQStages:scope}},v.stages.map(([a,b])=>h('li',null,h('b',null,a),' · ',b))),h('p',{class:'meta'},v.relative),
      h('h5',null,'Q 결손 (대표 원인)'),dl(v.qPrimary,{dualQPrimary:scope}),h('p',{class:'meta'},v.qPrimaryNote),
      h('h5',null,'공식 관문 판정 상태 (Q 결손과 별도)'),dl(v.gate,{dualQGate:scope}),h('p',{class:'meta'},v.gateNote),
      h('h5',null,'공식 입력 연결 (판정 가능·통과와 별도)'),dl(v.link,{dualQLink:scope}),h('p',{class:'meta'},v.linkNote),
      h('details',{class:'why'},h('summary',null,'겹치는 Q 원인 ▸'),list(v.qOverlap,{dualQOverlap:scope},''),h('p',{class:'meta'},v.qOverlapNote)));}));}
  const wrap=h('div',{class:'sk card',dataset:{dualBlock:''}},h('h4',null,'연구 후보 결과 (U1 · U2 · S1 / 3/3/3 · 연구 · 운영 채택 안 됨)'),h('div',{class:'load-row'},...btns),rs,slot,epsArea,qArea);
  for(const[k,b]of btns.map((b,i)=>[Object.keys(DQ.SLOTS)[i],b]))if(DQ.ram.get(k))b.hidden=true;
  paint();return wrap;}

 // 입력 연결 수정 전후 비교 (Codex #527, IS2.inputRepair): its own click and one read, accepted only for the result of this checked
 // bundle (a coverage scope with the same date, input hash and denominator). A refusal or a failed read is this block's error; the
 // bundle, coverage and details stay. Counts and the producer's rows as written; nothing recalculated.
 function repairBlock(){const R=I.inputRepair;
  const rs=h('p',{class:'reason',role:'status',dataset:{repairState:'IDLE'}},'비교 유형: 원값 보완(입력 연결 수정, INPUT_CONNECTION_REPAIR) · 요소·비중·분류 변경, 참조집단 확대와 구분');
  const slot=h('div',{dataset:{repairArea:''}});
  const btn=h('button',{type:'button',class:'btn',dataset:{repairOpen:''}},'입력 연결 수정 전후 비교 불러오기');
  const set=(c,t)=>{rs.dataset.repairState=c;rs.textContent=t;};let busy=false;
  btn.addEventListener('click',e=>{if(busy||st.busy)return;busy=true;btn.disabled=true;set('LOADING','불러오는 중 · 비교 파일 1개');
   let p;try{p=I.prices.kisRead(e,[['classification','input_repair']]);}catch(err){p=Promise.reject(err);}
   Promise.resolve(p).then(([x])=>{const r=R.validate(x,R.anchorOf(st.bundle));
    if(!r.ok){set('ERROR','비교를 쓰지 않음 · '+(r.code==='COMPARISON_RESULT_MISMATCH'?'지금 받은 결과와 다른 결과의 비교입니다':r.code==='COMPARISON_DATE_MISMATCH'?'평가일이 다릅니다':'형식 오류')+' · '+r.code+' · '+r.path+' · 위 묶음은 그대로');btn.disabled=false;return;}
    btn.hidden=true;paintRepair(R.view(r.value.comparison,r.value.scope,{sectorName:id=>I.taxonomy?I.taxonomy.sectorName(id):id}));},
   err=>{const c=codeOf(err);set('ERROR',(c==='KIS_SERIES_NOT_FOUND'?'전달 위치에 입력 연결 수정 비교가 없습니다(생산자 인계 전)':say(c))+' · 위 묶음은 그대로');btn.disabled=false;})
   .finally(()=>{busy=false;});});
  function paintRepair(v){set('READY',v.head);
   slot.replaceChildren(h('p',{class:'hand',dataset:{repairNot:''}},v.not),h('p',{class:'reason'},v.limits,' · ',v.inputs),
    v.same?h('p',{class:'reason',dataset:{repairSame:''}},v.same):null,
    h('ul',{class:'news-lines',dataset:{repairAxes:''}},v.axes.map(a=>h('li',{dataset:{repairAxis:a.key}},a.text))),
    v.shift?h('p',{class:'hand',dataset:{repairShift:''}},v.shift):null,
    h('details',{class:'why',dataset:{repairFactors:String(v.factors.length)}},h('summary',null,'바뀐 요소 수 ',String(v.factors.length),' · 그대로 ',String(v.unchangedFactors),' ▸'),
     list(v.factors.map(f=>f.text),{},'바뀐 요소 없음')),
    h('details',{class:'why',dataset:{repairShortfall:String(v.shortfall.length)}},h('summary',null,'구조적 표본 부족 그룹 ',String(v.shortfall.length),'/',String(v.groups),' ▸'),
     h('p',{class:'reason'},v.shortfallWord),list(v.shortfall,{},'없음')),
    h('details',{class:'why',dataset:{repairRows:String(v.rows.length)}},h('summary',null,'값이 바뀐 행 ',String(v.rows.length),' ▸'),
     list(v.rows.map(r=>r.text),{},'없음')));}
  return h('div',{class:'sk card',dataset:{repairBlock:''}},h('h4',null,'입력 연결 수정 전후 비교'),btn,rs,slot);}

 function show(e,row,slot){if(st.busy)return;const key=row.shard_key;
  const paint=async p=>{const d=await E().checkDetail(row,p,st.bundle);
   if(!d.ok){slot.replaceChildren(h('p',{class:'err',dataset:{heldDetailError:d.code}},'이 발행사 상세 · 연결 오류(',d.code,') · 쓰지 않음 · 색인과 다른 발행사는 그대로'));return;}
   slot.replaceChildren(card(E().detailView(d.value,st.bundle)));};
  if(st.shards.has(key)){void paint(st.shards.get(key));return;}
  st.busy=true;slot.replaceChildren(h('p',{class:'pending',role:'status',dataset:{state:'loading'}},'불러오는 중 · 상세 조각 '+key));
  let p;try{p=I.prices.kisRead(e,[['classification','expanded_detail/'+key]]);}catch(err){p=Promise.reject(err);}
  Promise.resolve(p).then(([part])=>{st.shards.set(key,part);return paint(part);},
   err=>{const c=codeOf(err);slot.replaceChildren(h('p',{class:'err',dataset:{heldDetailError:c}},'이 발행사 상세 · ',c==='KIS_SERIES_NOT_FOUND'?'상세 조각 없음':say(c),' · 색인과 다른 발행사는 그대로'));})
   .finally(()=>{st.busy=false;});}

 // A code row that is a Universe504 company of the public list opens that company page (검색 → 기업 상세); any other id stays text.
 function codeRows(rows){const W=E().W;if(!rows.length)return'없음 · '+W.CODE_ROWS;
  const known=c=>{try{return!!(I.companies&&typeof I.companies.get==='function'&&I.companies.get(c));}catch(_){return false;}};
  return h('span',null,...rows.flatMap((c,i)=>[i?', ':null,known(c)?h('a',{class:'lk',href:I.href('company',c),dataset:{heldCompany:c}},c,' → 기업 상세'):c]),' · ',W.CODE_ROWS);}
 function card(v){const W=E().W;
  return h('div',{class:'sk card cc-wrap',dataset:{heldDetail:v.id}},h('h4',null,v.id,' · ',v.row),
   dl([['관측 티커',(v.tickers.join(', ')||'없음')+' · '+W.TICKER,{heldTickers:String(v.tickers.length)}],
    ['관측 이름',v.names.join(', ')||'없음'],
    ['운영504 코드 행',codeRows(v.codeRows),{heldCodeRows:String(v.codeRows.length)}],
    ['섹터',v.sector,{heldClass:'sector'}],['하위 산업',v.industry,{heldClass:'industry'}],['회계모형',v.accounting,{heldClass:'accounting'}],
    ['원천 SIC',v.sic],['분류 적용',v.applicability],
    ['축',v.axes,{heldAxes:''}],['계산',v.status,{heldStatus:''}],['순위',v.rank,{heldRank:''}],['비교집단',v.peer],
    ['공식 Q 관문 입력',v.gate,{heldGate:''}],['가격·기술',v.prices,{heldPrices:''}],['사업 설명',v.profile,{heldProfile:''}]]),
   h('h4',null,'요소'),
   list(v.factors.map(f=>h('span',{dataset:{heldFactor:f.id}},h('b',null,f.id),f.selected?' (기본 선택)':'',' · 원지표 ',f.raw,' · 점수 ',f.score,f.n?' · '+f.n:'')),{heldFactors:String(v.factors.length)},'요소 없음'),
   h('h4',null,'입력 결손'),list(v.gaps,{heldGaps:String(v.gaps.length)},'입력 결손 기록 없음(원결과에 없음 · 결손이 없다는 확인 아님)'),
   h('h4',null,'근거'),list(v.evidence.map(x=>h('span',{dataset:{heldEvidence:x.source}},h('b',null,x.source),' · ',x.locator||'위치 없음',' · 취득 ',x.at||'—',' · ',x.sha,
    x.url?[' · ',h('code',{class:'wrap-any'},x.url)]:null)),{heldEvidenceN:String(v.evidence.length)},'근거 없음'));}

 return h('div',{class:'sk card',dataset:{heldBrowse:''}},h('h4',null,'확장 발행사 찾기 · 보유 재무 표본(별도 모집단)'),
  h('p',{class:'reason'},'비공개 인증 경로 · 목록표·색인을 먼저 검증하고, 고른 발행사의 상세 조각만 읽습니다 · 전체 상세를 한꺼번에 받지 않음'),
  open,state,area);}
// One company in every model of one checked delivery in RAM (slot = IS2.dualQgv.SLOTS key): its detail file read once inside the
// click (then kept with the delivery), checked by IS2.dualQgv.checkDetail, shown side by side (factors, exact weights, missing core
// factors, evidence). Shared by 0. 기업 검색's result cards and 2.1's research boards (IS2.dualDetail.open); nothing is recalculated.
const sectorNameOf=id=>I.taxonomy?I.taxonomy.sectorName(id):id;
let detailBusy=false;
function openDetail(e,scope,row,slotC){const DQ=I.dualQgv,held=DQ&&DQ.ram.get(scope);if(!held||detailBusy)return false;const name=row.detail_file;
  const show=rows=>{const r=rows.get(row.company_id);const v=DQ.compareView(r,held.delivery,{sectorName:sectorNameOf});
   // Not a card inside the card: at 390 px nested padding leaves too little room, and long factor ids must wrap (cc-wrap).
   slotC.replaceChildren(h('div',{class:'cc-wrap',dataset:{dualCompareFor:row.company_id}},h('p',{class:'hand'},row.company_id,' · ',v.note),
    h('details',{class:'why'},h('summary',null,'요소 분위 읽는 법 ▸'),list(v.bandRule,{dualCompareBandRule:''},'')),
    ...v.boards.map(b=>h('div',{class:'cc-wrap',dataset:{dualCompareBoard:b.key}},h('h5',null,b.label),h('p',{dataset:{dualCompareAxes:b.key}},b.axes),
     h('p',{class:'meta',dataset:{dualCompareRank:b.key}},b.rank,' · ',b.status),
     b.recipe?h('p',{class:'reason',dataset:{dualCompareRecipe:b.key}},b.recipe):null,
     b.weights?h('p',{class:'reason',dataset:{dualCompareWeights:b.key}},b.weights):null,
     b.missing?h('p',{class:'meta',dataset:{dualCompareMissing:b.key}},'핵심 요소 결손 · ',b.missing):null,
     h('p',{class:'meta'},'핵심 요소 ',String(b.core.length)),list(b.core,{dualCompareCore:b.key},'핵심 요소 없음'),
     b.evidence.length?h('details',{class:'why'},h('summary',null,'핵심 요소 근거(측정·산식·기간·방향) ▸'),list(b.evidence,{dualCompareEvidence:b.key},'')):null,
     h('details',{class:'why'},h('summary',null,'추가 요소(핵심 점수에 안 들어감) · 산출 ',String(b.additional.length),' · 미산출 ',String(b.additionalMissing),' ▸'),list(b.additional,{dualCompareAdditional:b.key},'산출된 추가 요소 없음'))))));};
  if(held.details.has(name)){show(held.details.get(name));return true;}
  detailBusy=true;slotC.replaceChildren(h('p',{class:'reason',dataset:{dualCompareState:'LOADING'}},'상세 파일 1개를 불러옵니다'));
  let p;try{p=I.prices.kisRead(e,[['classification','dual_detail/'+scope+'/'+name.slice(7,10)]]);}catch(err){p=Promise.reject(err);}
  Promise.resolve(p).then(async([x])=>{const r=await DQ.checkDetail(x,name,held.delivery,E().sha256);
   if(!r.ok){slotC.replaceChildren(h('p',{class:'reason',dataset:{dualCompareState:'ERROR'}},'이 기업의 상세를 쓰지 않음 · '+r.code+' · '+r.path+' · 목록은 그대로'));return;}
   held.details.set(name,r.value);show(r.value);},
  err=>{slotC.replaceChildren(h('p',{class:'reason',dataset:{dualCompareState:'ERROR'}},'연결 오류 · '+say(codeOf(err))));}).finally(()=>{detailBusy=false;});return true;}
I.dualDetail=Object.freeze({open:openDetail});
I.expandedBrowse=Object.freeze({block});
})();
