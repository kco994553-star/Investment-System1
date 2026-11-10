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
const E=()=>I.expandedIssuers;
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
   h('label',{for:'held-q',class:'meta'},'확장 발행사 찾기'),q,count,results,detail);}

 // Coverage by stage (IS2.expandedIssuers.coverageView): one list per unit in pipeline order, then the gate decisions, the total
 // failure reasons, the causes (overlapping, never summed) and each factor's own counts. Words and counts only; nothing derived.
 function coverageBlock(cov){const v=E().coverageView(cov);
  // Stages up to 세 축 동시, then the gate decisions, then the totals: the pipeline order on screen.
  const stageList=(u,late)=>h('ol',{class:'news-lines',dataset:{heldStages:u.unit+(late?':total':':axes'),heldStagesDen:String(u.denominator)}},
   u.stages.filter(s=>(s.group==='총점')===late).map(s=>h('li',{dataset:{heldStage:s.key,heldStageValue:s.text}},h('span',{class:'meta'},s.group,' · '),s.label,' ',h('b',null,s.text))));
  return h('details',{class:'why',dataset:{heldCoverage:''}},h('summary',null,'커버리지 단계 · 95% 목표 · 관문 · 미산출 사유 ▸'),
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
I.expandedBrowse=Object.freeze({block});
})();
