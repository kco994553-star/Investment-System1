/* The owner-private KIS panels (owner 2026-11-05 DC-44, 2026-11-14 DC-52, 2026-11-15 DC-53 and the same day's "최소 기능" note):
   IS2.privateExpand.attach(panel, {signal, kind, target, publicBasis}) is the one common component of a private panel from
   IS2.parts.privatePanel. It puts 비공개 펼치기 / 접기, 비공개 연결 끊기 and a 상태 box on the panel and fills it from
   IS2.kisPrivate's readers through the layer (IS2.prices.kisConnect / kisRead / kisDisconnect, each inside the click that asks).
   - States: NOT_READY (no private Worker in the site settings or no reader) · LOGIN_REQUIRED · LOADING · READY · EMPTY (자료 없음,
     the Worker has no file: KIS_SERIES_NOT_FOUND) · ERROR (a refused file or a fixed error code). A server 403 or an expired
     Google token drops the session and the panel asks to sign in again; closing the panel or 연결 끊기 clears what was shown.
   - The main panel holds only the label, the price basis day (YYYY-MM-DD) and the numbers in a table, plus one short line when
     something is wrong (basis mismatch, 갱신 지연, an error code). File facts (source, capture times, evaluation day, evidence,
     settings version, basis comparison) and the read-token status go to the 상태 box. 읽기 토큰 상태 확인 reads the Worker's
     status route on its own click; NO_EXPIRY reads 만료일 없음.
   - kind 'technical': the analysis, chart and technical routes for target().symbol (one click, three reads, 5 s apart). Label
     KIS · 비공개 and the chart's basis (원주가 / 확인된 분할 반영). Adopted indicators and adopted measures only; a held one is
     미산출 with its reasons; raw diagnostics are never shown. A result whose basis differs from the chart file's is not
     attached (IS2.kisPrivate.basisAgreement): that part shows the mismatch line and no value ([data-private-basis-agreement]).
     A missing measures file (404) is that part's 자료 없음; a refused one that part's refusal; the analysis and chart stay.
   - kind 'qgv': the qgv route → label KIS · 비공개 · 공식 아님, the price basis day and the source, the target().code row's
     Q / G / V (미산출 + reason, never 0), the total only when V exists, no rank, and the coverage counts. Nothing here
     recomputes a score or a rank: the file's values are shown as they are.
   - Each READY cell carries one verification tag, 검증됨 or 검증 전(참고) (IS2.kisPrivate.verification over the cell's files); a
     held item shows its one-line reason only. Class shares: a file names BRK/B or BF/B for the asked BRK-B / BF-B.
   Values are text inside [data-ram-price] only (never an attribute, storage or log); nothing here makes a request outside a
   click. */
(function(){
'use strict';
const I=window.IS2,{h}=I;
const ram=(...t)=>h('span',{dataset:{ramPrice:''}},...t);
const WORDS=Object.freeze({AUTH_FORBIDDEN:'서버가 오너 확인을 거부했습니다 · 다시 로그인하세요',AUTH_REQUIRED:'로그인이 끝났습니다(만료) · 다시 로그인하세요',
 AUTH_UNAVAILABLE:'로그인 확인 서버 응답 없음',LOGIN_CANCELED:'로그인을 취소했습니다',LOGIN_REFUSED:'로그인 범위가 맞지 않아 쓰지 않았습니다',LOGIN_UNAVAILABLE:'비공개 연결 설정이 없습니다',
 KIS_SERIES_NOT_FOUND:'자료 없음',TOKEN_UNSET:'비공개 저장소 읽기 설정 없음',TOKEN_EXPIRED:'비공개 저장소 읽기 토큰 만료',TOKEN_REJECTED:'비공개 저장소 읽기 토큰 거부',
 TOKEN_DATE_INVALID:'읽기 토큰 만료 설정 오류',TOKEN_DATE_IS_TOKEN:'읽기 토큰 만료 설정 오류',TOKEN_STATUS_INVALID:'비공개 토큰 상태 파일 확인 필요',
 RATE_LIMITED:'요청이 많아 잠시 뒤 다시',UPSTREAM_UNAVAILABLE:'비공개 자료 서버 응답 없음',ROUTE_NOT_FOUND:'비공개 서버에 이 경로가 아직 없습니다'});
const word=c=>Object.prototype.hasOwnProperty.call(WORDS,c)?WORDS[c]:'오류 · '+c;
const CODE=/^[A-Z][A-Z0-9_]{1,63}$/;
const codeOf=e=>{const m=e&&typeof e.message==='string'?e.message:'';return CODE.test(m)?m:'PRIVATE_READ_FAILED';};
// A two-column table of label → value rows (value nodes may be [data-ram-price] text).
const table=(rows,d)=>h('table',{class:'tbl',dataset:d||{}},h('tbody',null,rows.filter(Boolean).map(([k,v,data])=>h('tr',data?{dataset:data}:null,h('th',{scope:'row'},k),h('td',null,v)))));
// The 상태 box lines: label → text.
const facts=(rows,part)=>h('dl',{class:'card-body',dataset:{privateFacts:part}},rows.filter(Boolean).map(([k,v,data])=>[h('dt',null,k),h('dd',data?{dataset:data}:null,v)]));
const warn=(text,data)=>h('p',{class:'reason',dataset:data||{}},text);
// One short verification tag (검증됨 / 검증 전(참고)), never a sentence.
const tag=vf=>h('span',{class:'chip',dataset:{privateVerification:vf.code}},vf.text);

function chart(bars,symbol){const TC=window.TechnicalChart;const nums=bars.map(b=>({close:b.close===null?null:Number(b.close)}));
 const g=TC&&typeof TC.geometry==='function'?TC.geometry(nums,[]):null;
 if(!g)return h('p',{class:'reason',dataset:{privateChart:'NONE'}},'그릴 종가가 없습니다');
 return h('svg:svg',{class:'curve tech-chart',viewBox:'0 0 640 240',role:'img',focusable:'false',dataset:{privateChart:symbol},'aria-label':'KIS 일봉 종가 선 · '+symbol+' · '+bars.length+'봉'},
  h('svg:path',{d:'M20,220 L620,220',class:'curve-base'}),TC.paths(nums.map(b=>b.close),g).map(p=>h('svg:path',{d:p,class:'curve-s',dataset:{privateCloseLine:''}})));}

// The five measures part: EMPTY (no file), REFUSED (the file breaks its contract: nothing of it shown), BASIS_MISMATCH (its basis
// is not the chart's: the mismatch line only, no value) or READY.
function measuresPart(K,raw,symbol,chartBasis,status,files){
 const part=(st,...c)=>h('div',{class:'sk card',dataset:{privateMeasures:st}},h('h4',null,'다섯 측정값'),...c);
 if(raw===null)return part('EMPTY',warn('자료 없음'));
 const r=K.validateMeasures(raw);
 if(!r.ok||K.requestSymbol(r.value.symbol)!==symbol){const code=r.ok?'SYMBOL_MISMATCH':r.code;return part('REFUSED',warn('형식 오류 · '+code,{na:code}));}
 const v=K.measuresView(r.value),g=K.basisAgreement(chartBasis,r.value);files.push(r.value);
 status.push(['측정 평가일',v.evaluation_day,{privateEvaluationDay:'measures'}],['측정 가격 기준',v.basisText,{privateMeasuresBasis:v.basis}],
  ['측정 설정 판',v.settings_version,{privateSettingsVersion:''}],['측정 수집 시각',v.collected_at],['측정 분할 증거',v.evidence],['측정 개수',v.summary,{privateMeasuresCounts:''}]);
 if(!g.same)return part('BASIS_MISMATCH',warn(g.text,{privateBasisAgreement:g.code,privateBasisPart:'measures'}));
 return part('READY',v.status!=='NORMAL'?warn(v.statusText,{privateMeasuresStatus:v.status}):null,
  table(v.rows.map(x=>[x.label,x.kind==='VALUE'?ram(x.value):x.text,{privateMeasure:x.id,privateMeasureKind:x.kind}])));}

function renderTechnical(body,[aRaw,bRaw,mRaw],{symbol,publicBasis},status){const K=I.kisPrivate,a=K.validateAnalysis(aRaw),b=K.validateBars(bRaw);
 if(!a.ok||!b.ok){const r=a.ok?b:a;throw Error(r.code);}
 // The chart must be the company asked for (a class share's file names it BRK/B for BRK-B).
 if(K.requestSymbol(b.value.symbol)!==symbol)throw Error('SYMBOL_MISMATCH');
 const v=K.analysisView(a.value),m=K.barsMeta(b.value),cmp=K.basisCompare(publicBasis,m.price_basis_date),last=b.value.bars[b.value.bars.length-1];
 const g=K.basisAgreement(m.basisCode,a.value);
 status.push(['공급처',m.source],['수집 시각',m.collected_at],['정정',m.corrected],['평가일',v.evaluation_day,{privateEvaluationDay:'analysis'}],v.signal_day?['신호일',v.signal_day]:null,
  ['상태',v.statusText,{privateStatusWord:v.status}],['지표 가격 기준',v.basisText,{privateIndicatorBasis:v.basis}],['분할 증거',v.evidence],v.adjustment?['분할 상태',v.adjustment,{privateAdjustmentStates:''}]:null,
  m.note||v.note?['분할 반영',m.note||v.note,{privateAdjustedNote:'technical'}]:null,['기준일 비교',cmp.text,{privateBasisCompare:cmp.same?'SAME':'DIFFERENT'}],['지표 개수',v.summary,{privateCounts:''}]);
 // Indicators only on a chart of the same basis; otherwise the mismatch line and nothing of the indicators (no value, no count).
 const rows=[...v.adopted.map(x=>[x.id,ram(x.value),{privateIndicator:x.id}]),...v.held.map(x=>[x.id,x.text,{privateHeld:x.id}])];
 const indicators=g.same?(rows.length?table(rows,{privateAdopted:String(v.adopted.length)}):warn('지표 없음',{privateAdopted:'0'}))
  :warn(g.text,{privateBasisAgreement:g.code,privateBasisPart:'analysis'});
 const files=[b.value,a.value],measures=measuresPart(K,mRaw===undefined?null:mRaw,symbol,m.basisCode,status,files),vf=K.verification(files);
 I.append(body,[h('p',{class:'hand',dataset:{privateLayer:'technical'}},'KIS · 비공개 · 가격 기준일 ',h('span',{dataset:{privateBasisDate:''}},m.price_basis_date||'없음'),' · ',h('span',{dataset:{privateChartBasis:m.basisCode}},m.basis),' ',tag(vf)),
  v.status!=='NORMAL'?warn(v.statusText,{privateStatusLine:v.status}):null,
  last?table([['마지막 종가',ram(last.date,' · ',last.close===null?'NA':last.close)]],{privateLast:''}):null,
  chart(b.value.bars,symbol),
  indicators,
  measures]);}

function renderQgv(body,[qRaw],{code,publicBasis},status){const K=I.kisPrivate,q=K.validateQgv(qRaw);if(!q.ok)throw Error(q.code);
 const v=K.qgvView(q.value,code),cmp=K.basisCompare(publicBasis,v.price_basis_date);
 status.push(['재무 입력 기준',q.value.financial_input_as_of||'없음'],['계산 시각',q.value.calculated_at],
  ['기준일 비교',cmp.text,{privateBasisCompare:cmp.same?'SAME':'DIFFERENT'}],['순위',v.rank,{privateRank:'NONE'}]);
 I.append(body,[h('p',{class:'hand',dataset:{privateLayer:'qgv'}},'KIS · 비공개 · 공식 아님 · 가격 기준일 ',h('span',{dataset:{privateBasisDate:''}},v.price_basis_date),' · 출처 ',
   h('span',{dataset:{privateSource:''}},v.source),' · 계산 판 ',h('span',{dataset:{privateCalcVersion:''}},v.calc_version),' ',tag(v.verification)),
  v.row?table([...v.row.axes.map(t=>[t.slice(0,1),ram(t.slice(2)),{privateAxis:t.slice(0,1)}]),['총점',ram(v.row.total),{privateTotal:''}],
   v.row.price?['가격',v.row.price]:null],{privateRow:v.row.code})
   :warn(code?'이 기업은 KIS 계산 대상에 없습니다':'기업을 고르세요',{privateRow:'NONE'}),
  h('p',{class:'sub',dataset:{privateCoverage:''}},v.coverage.join(' · '))]);}

const READS=Object.freeze({technical:t=>(t.symbol?[['analysis',t.symbol],['chart',t.symbol],['technical',t.symbol,'OPTIONAL']]:null),qgv:()=>[['qgv',null]]});
const RENDER=Object.freeze({technical:renderTechnical,qgv:renderQgv});

function attach(panel,{signal,kind,target=()=>({}),publicBasis=()=>null}){
 if(!Object.prototype.hasOwnProperty.call(READS,kind))throw Error('PRIVATE_EXPAND_KIND');
 const P=()=>I.prices;
 const btn=h('button',{type:'button',class:'chip',dataset:{privateExpand:kind},'aria-expanded':'false'},'비공개 펼치기');
 const off=h('button',{type:'button',class:'chip',dataset:{privateDisconnect:kind},hidden:true},'비공개 연결 끊기');
 const note=h('p',{class:'reason',role:'status',dataset:{privateNote:kind}});
 // The 상태 box: the read-token check and the file facts of the last read; closed by default.
 const tokenCheck=h('button',{type:'button',class:'chip',dataset:{privateTokenCheck:kind}},'읽기 토큰 상태 확인');
 const tokenNote=h('p',{class:'reason',role:'status',dataset:{privateTokenStatus:kind}});
 const factBox=h('div',{dataset:{privateFactBox:kind}});
 const box=h('details',{class:'why',dataset:{privateStatusArea:kind},hidden:true},h('summary',null,'상태'),tokenCheck,tokenNote,factBox);
 const bar=h('div',{class:'load-row',dataset:{privateControls:kind}},btn,off,note,box);
 panel.node.insertBefore(bar,panel.node.querySelector('.private-body'));
 let open=false,seq=0,tokenSeq=0;
 const st=()=>{try{return P().kisState();}catch(_){return{ready:false,connected:false,gis:false};}};
 function resetToken(){tokenSeq++;tokenCheck.disabled=false;tokenNote.textContent='';delete tokenNote.dataset.privateTokenState;}
 function closed(msg){const s=st();open=false;seq++;btn.textContent='비공개 펼치기';btn.setAttribute('aria-expanded','false');off.hidden=!s.connected;
  box.hidden=!s.connected;resetToken();factBox.replaceChildren();
  if(!s.ready)panel.set('NOT_READY');else if(!s.connected)panel.set('LOGIN_REQUIRED');
  else panel.set('READY',{render:b=>I.append(b,[h('p',{class:'reason',dataset:{privateClosed:''}},'비공개 접힘')])});
  note.textContent=msg||'';}
 function read(e){const t=target()||{},my=++seq;
  const req=READS[kind](t);
  if(!req){note.textContent='기업을 먼저 고르세요';return;}
  panel.set('LOADING');factBox.replaceChildren();note.textContent='';
  let p;try{p=P().kisRead(e,req);}catch(err){p=Promise.reject(err);}
  Promise.resolve(p).then(res=>{if(my!==seq||signal.aborted)return;const status=[];
   try{panel.set('READY',{render:b=>RENDER[kind](b,res,{symbol:t.symbol,code:t.code,publicBasis:publicBasis()},status)});}
   catch(err){const c=codeOf(err);panel.set('ERROR',{code:c});note.textContent='형식 오류 · '+c;return;}
   factBox.replaceChildren(facts(status,kind));
   open=true;btn.textContent='비공개 접기';btn.setAttribute('aria-expanded','true');off.hidden=false;box.hidden=false;},
  err=>{if(my!==seq||signal.aborted)return;const c=codeOf(err);if(c==='CANCELED')return;
   if(c==='AUTH_FORBIDDEN'||c==='AUTH_REQUIRED'){closed(word(c));return;}
   if(c==='KIS_SERIES_NOT_FOUND'){panel.set('EMPTY');note.textContent=word(c);return;}
   panel.set('ERROR',{code:c});note.textContent=word(c);});}
 btn.addEventListener('click',e=>{if(open){closed();return;}const s=st();
  if(!s.ready){closed(word('LOGIN_UNAVAILABLE'));return;}
  if(s.connected){read(e);return;}
  let p;try{p=P().kisConnect(e);}catch(err){p=Promise.reject(err);}
  Promise.resolve(p).then(r=>{if(signal.aborted)return;closed(r&&r.prepared?'Google 로그인 준비됨 · 한 번 더 누르세요':'로그인됨 · 한 번 더 누르면 불러옵니다');},
   err=>{if(!signal.aborted)closed(word(codeOf(err)));});},{signal});
 off.addEventListener('click',e=>{let p;try{p=P().kisDisconnect(e);}catch(err){p=Promise.reject(err);}Promise.resolve(p).then(()=>closed('비공개 연결을 끊었습니다'),()=>closed('비공개 연결을 끊었습니다'));},{signal});
 tokenCheck.addEventListener('click',e=>{
  if(!st().connected){closed(word('AUTH_REQUIRED'));return;}
  const mine=++tokenSeq;tokenCheck.disabled=true;tokenNote.dataset.privateTokenState='LOADING';tokenNote.textContent='확인 중';
  let p;try{p=P().kisRead(e,[['status',null]]);}catch(err){p=Promise.reject(err);}
  Promise.resolve(p).then(rows=>{
   if(signal.aborted||mine!==tokenSeq)return;
   const v=I.kisPrivate.tokenStatusView(rows[0]);tokenNote.dataset.privateTokenState=v.state;tokenNote.textContent=v.text;
   // Something wrong with the read token: one short line on the main panel too.
   if(v.blocked||v.state==='EXPIRING')note.textContent=v.text;
  }).catch(err=>{
   if(signal.aborted||mine!==tokenSeq)return;const c=codeOf(err);
   if(c==='AUTH_FORBIDDEN'||c==='AUTH_REQUIRED'){closed(word(c));return;}
   tokenNote.dataset.privateTokenState='ERROR';tokenNote.textContent=word(c);note.textContent=word(c);
  }).finally(()=>{if(!signal.aborted&&mine===tokenSeq)tokenCheck.disabled=false;});
 },{signal});
 // A dropped token (expiry, 403, 연결 끊기 elsewhere) closes the panel and clears what it showed.
 const un=(()=>{try{return P().kisSubscribe(()=>{if(signal.aborted)return;if(!st().connected){const checking=tokenCheck.disabled;resetToken();
  if(open||checking)closed(word('AUTH_REQUIRED'));else{box.hidden=true;off.hidden=true;}}});}catch(_){return()=>{};}})();
 signal.addEventListener('abort',()=>{seq++;tokenSeq++;un();},{once:true});
 closed();
 return Object.freeze({reset:()=>closed()});}
I.privateExpand=Object.freeze({attach});
})();
