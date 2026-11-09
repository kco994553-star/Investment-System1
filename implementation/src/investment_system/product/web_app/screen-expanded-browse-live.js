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
  const cov=E().coverageView(b.coverage);
  area.replaceChildren(
   dl([['모집단',ctx.population.id+' · 발행사 '+ctx.population.denominator+'개 · 운영504와 합치지 않음',{heldPopulation:String(ctx.population.denominator)}],
    ['점수의 비교집단',ctx.scoring_population.id+' · '+ctx.scoring_population.denominator+'개(보유 표본으로 다시 점수화하지 않음)'],
    ['분류',ctx.classification.dictionary_version+' + '+ctx.classification.mapping_version+' · 해시 '+ctx.classification.classification_hash.slice(0,12)+'…'],
    ['원결과',ctx.result_identity.preview_id.slice(0,12)+'… · 입력 '+ctx.input_as_of],
    ['생산자',b.identity.producer_sha.slice(0,12)+'… · 요약 '+b.identity.summary.sha256.slice(0,12)+'…']],{heldMeta:''}),
   h('details',{class:'why',dataset:{heldCoverage:''}},h('summary',null,'커버리지 · 95% 목표 · 미산출 원인 ▸'),
    ...cov.map(c=>h('div',{dataset:{heldScope:c.scope}},h('p',null,h('b',null,c.label),' · ',c.stages.join(' · ')),h('p',{class:'reason',dataset:{heldTarget:c.scope}},c.target),
     c.rows?h('p',{class:'reason'},c.rows):null,h('p',{class:'reason'},'원인(겹칠 수 있음 · 합쳐 세지 않음) · ',c.causes.join(' · ')))),
    h('p',{class:'reason',dataset:{heldMarket:''}},E().marketText(b.coverage))),
   h('label',{for:'held-q',class:'meta'},'확장 발행사 찾기'),q,count,results,detail);}

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

 function card(v){const W=E().W;
  return h('div',{class:'sk card cc-wrap',dataset:{heldDetail:v.id}},h('h4',null,v.id,' · ',v.row),
   dl([['관측 티커',(v.tickers.join(', ')||'없음')+' · '+W.TICKER,{heldTickers:String(v.tickers.length)}],
    ['관측 이름',v.names.join(', ')||'없음'],
    ['운영504 코드 행',(v.codeRows.join(', ')||'없음')+' · '+W.CODE_ROWS,{heldCodeRows:String(v.codeRows.length)}],
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
