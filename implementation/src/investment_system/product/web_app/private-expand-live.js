/* "비공개 펼치기" on the existing private panels (owner 2026-11-05, DC-44: one screen, the public part by default, the private
   result in the same format after the owner signs in). IS2.privateExpand.attach(panel, {signal, kind, target, publicBasis})
   puts a 펼치기 / 접기 button and a 연결 끊기 button on a panel from IS2.parts.privatePanel and fills it from IS2.kisPrivate's
   readers through the layer (IS2.prices.kisConnect / kisRead / kisDisconnect, each inside the click that asks for it).
   - kind 'technical': the analysis, chart and technical routes for target().symbol (one click, three reads) → source, price basis
     day, capture time, basis (원주가 / 확인된 분할 반영), correction, status 정상 / 갱신 지연 / 자료 없음, the close line
     (TechnicalChart geometry), adopted indicators only (raw diagnostics are a count, never a value) and each held indicator's
     미산출 reasons; then the five measures (kis-technical-measures/1): 채택값 only when adopted, 진단값 as a count, 미산출 with
     its reasons, each window, signal day, data_asof, capture time, no rank. The measures file is its own part: a missing file
     (404) is that part's 자료 없음 and a refused one that part's refusal; the analysis and the chart stay.
     Price basis (Codex #498, owner 11/05): the chart's basis, the analysis' indicator basis / result kind / evidence / per-indicator
     split state, and the measures' basis and settings version are each shown with the evaluation day. When a result's basis
     differs from the chart file's (IS2.kisPrivate.basisAgreement) its indicators are not attached to the chart: the part says
     가격 기준 불일치 · 지표를 이 차트에 붙이지 않음 ([data-private-basis-agreement=BASIS_MISMATCH]) and shows no value or count.
     An adjusted result carries the fixed line 실제 분할 사건 검증 미완료 · 분할 없는 구간의 조정 경로 확인. Counts read
     채택값 N개 (이 기업·이 평가일); two evaluation days are never merged into one count.
   - kind 'macro' / 'news' (owner 2026-11-05): the macro / news route → the private copy in the public file's format, validated by
     the public reader (IS2.macroObserved; NewsSignals + IS2.newsRefresh) and drawn by the public block's own function (opts.draw,
     given by the screen), under the source words 비공개 보관본 · 인증 경로 and the two-layer line. A refused file is refused whole.
   - kind 'qgv': the qgv route → Q / G / V / 세 축 coverage, the target().code row's axes (미산출 + reason, never 0), the total only
     when V exists, no rank (rank null + reason), and the line that the public official ranks and TARGET are unchanged.
   - Public vs private basis day: basisCompare says when they differ (직접 비교 제한).
   - The server checks the owner on every read: a 403 drops the token and the panel asks to sign in again; an expired token
     is dropped before a read; closing the panel or 연결 끊기 clears what was shown. Values are text inside [data-ram-price]
     only (never an attribute, storage or log); nothing here makes a request outside a click. */
(function(){
'use strict';
const I=window.IS2,{h}=I;
const ram=(...t)=>h('span',{dataset:{ramPrice:''}},...t);
const dl=(rows,d)=>h('dl',{class:'card-body',dataset:d||{}},rows.filter(Boolean).map(([k,v,data])=>[h('dt',null,h('b',null,k)),h('dd',data?{dataset:data}:null,v)]));
const WORDS=Object.freeze({AUTH_FORBIDDEN:'서버가 오너 확인을 거부했습니다 · 다시 로그인하세요',AUTH_REQUIRED:'로그인이 끝났습니다(만료) · 다시 로그인하세요',
 AUTH_UNAVAILABLE:'로그인 확인 서버 응답 없음',LOGIN_CANCELED:'로그인을 취소했습니다',LOGIN_REFUSED:'로그인 범위가 맞지 않아 쓰지 않았습니다',LOGIN_UNAVAILABLE:'비공개 연결 설정이 없습니다',
 KIS_SERIES_NOT_FOUND:'이 기업의 비공개 자료가 아직 없습니다',TOKEN_UNSET:'비공개 저장소 읽기 설정 없음',TOKEN_EXPIRED:'비공개 저장소 읽기 토큰 만료',TOKEN_REJECTED:'비공개 저장소 읽기 토큰 거부',
 RATE_LIMITED:'요청이 많아 잠시 뒤 다시',UPSTREAM_UNAVAILABLE:'비공개 자료 서버 응답 없음'});
const word=c=>Object.prototype.hasOwnProperty.call(WORDS,c)?WORDS[c]:'오류 · '+c;
const CODE=/^[A-Z][A-Z0-9_]{1,63}$/;
const codeOf=e=>{const m=e&&typeof e.message==='string'?e.message:'';return CODE.test(m)?m:'PRIVATE_READ_FAILED';};

function chart(bars,symbol){const TC=window.TechnicalChart;const nums=bars.map(b=>({close:b.close===null?null:Number(b.close)}));
 const g=TC&&typeof TC.geometry==='function'?TC.geometry(nums,[]):null;
 if(!g)return h('p',{class:'reason',dataset:{privateChart:'NONE'}},'그릴 종가가 없습니다');
 return h('svg:svg',{class:'curve tech-chart',viewBox:'0 0 640 240',role:'img',focusable:'false',dataset:{privateChart:symbol},'aria-label':'비공개 · KIS 보관 일봉 종가 선 · '+symbol+' · '+bars.length+'봉'},
  h('svg:path',{d:'M20,220 L620,220',class:'curve-base'}),TC.paths(nums.map(b=>b.close),g).map(p=>h('svg:path',{d:p,class:'curve-s',dataset:{privateCloseLine:''}})));}

const agreeLine=(g,part)=>h('p',{class:g.same?'sub':'reason',dataset:{privateBasisAgreement:g.code,privateBasisPart:part}},g.text);
const noteLine=(t,part)=>t?h('p',{class:'reason',dataset:{privateAdjustedNote:part}},t):null;
// The five measures part: EMPTY (no file), REFUSED (the file breaks its contract: nothing of it shown), BASIS_MISMATCH (its basis
// is not the chart's: basis words only, no value or count) or READY.
function measuresPart(K,raw,symbol,chartBasis,analysisDay){
 const part=(st,...c)=>h('div',{class:'sk card',dataset:{privateMeasures:st}},h('h4',null,'다섯 측정값 · 공통 엔진 (#469 설정)'),...c);
 if(raw===null)return part('EMPTY',h('p',{class:'reason'},'자료 없음 · 이 기업의 비공개 측정 파일이 아직 없습니다'));
 const r=K.validateMeasures(raw);
 if(!r.ok||r.value.symbol!==symbol){const code=r.ok?'SYMBOL_MISMATCH':r.code;return part('REFUSED',h('p',{class:'reason',dataset:{na:code}},'측정 파일이 형식과 달라 보이지 않습니다 · ',code,r.ok?'':' '+r.path));}
 const v=K.measuresView(r.value),g=K.basisAgreement(chartBasis,r.value);
 const meta=dl([['신호일',v.signal_day],['자료 기준일',v.data_asof||'없음'],['수집 시각',v.collected_at],['상태',v.statusText,{privateMeasuresStatus:v.status}],['순위',v.rank,{privateMeasuresRank:'NONE'}],
  ['평가일',v.evaluation_day,{privateEvaluationDay:'measures'}],['측정 가격 기준',v.basisText,{privateMeasuresBasis:v.basis}],['설정 판',v.settings_version,{privateSettingsVersion:''}],['분할 증거',v.evidence]],{privateMeta:'measures'});
 const days=analysisDay&&analysisDay!==v.evaluation_day?h('p',{class:'reason',dataset:{privateEvaluationDays:'DIFFERENT'}},'분석 평가일 '+analysisDay+' · 측정 평가일 '+v.evaluation_day+' · 평가일이 달라 개수를 합치지 않음'):null;
 if(!g.same)return part('BASIS_MISMATCH',meta,agreeLine(g,'measures'),noteLine(v.note,'measures'),days);
 return part('READY',meta,agreeLine(g,'measures'),noteLine(v.note,'measures'),days,
  h('p',{dataset:{privateMeasuresCounts:''}},v.summary),
  h('ul',null,v.rows.map(x=>h('li',{dataset:{privateMeasure:x.id,privateMeasureKind:x.kind}},h('b',null,x.label),' · ',x.kind==='VALUE'?['채택값 ',ram(x.value)]:x.text,h('span',{class:'sub'},' · ',x.window)))));}

function renderTechnical(body,[aRaw,bRaw,mRaw],{symbol,publicBasis}){const K=I.kisPrivate,a=K.validateAnalysis(aRaw),b=K.validateBars(bRaw);
 if(!a.ok||!b.ok){const r=a.ok?b:a;throw Error(r.code);}
 const v=K.analysisView(a.value),m=K.barsMeta(b.value),cmp=K.basisCompare(publicBasis,m.price_basis_date),last=b.value.bars[b.value.bars.length-1];
 const g=K.basisAgreement(m.basisCode,a.value);
 // Indicators only on a chart of the same basis; otherwise the mismatch words and nothing of the indicators (no value, no count).
 const indicators=g.same?[h('p',{dataset:{privateCounts:''}},v.summary),
  v.adopted.length?h('ul',{dataset:{privateAdopted:String(v.adopted.length)}},v.adopted.map(x=>h('li',{dataset:{privateIndicator:x.id}},x.id,' · ',ram(x.value))))
   :h('p',{class:'reason',dataset:{privateAdopted:'0'}},'채택된 기술 지표 없음 · 원시 계산값은 채택값으로 보이지 않습니다'),
  v.held.length?h('details',{class:'why'},h('summary',null,'미산출 지표 ',String(v.held.length),'개 · 사유 ▸'),h('ul',null,v.held.map(x=>h('li',{dataset:{privateHeld:x.id}},x.id,' · ',x.text)))):null]:[];
 I.append(body,[h('p',{class:'hand',dataset:{privateLayer:'technical'}},'비공개 · 같은 화면 같은 형식 · 공개 화면의 판정 보류는 그대로'),h('p',{class:'reason',dataset:{privateLayerNote:''}},K.LAYER_NOTE),
  dl([['공급처',m.source],['차트 가격 기준',m.basis,{privateChartBasis:m.basisCode}],['가격 기준일',m.price_basis_date||'없음'],['수집 시각',m.collected_at],['정정',m.corrected],
   ['상태',v.statusText+' (평가일 '+v.evaluation_day+')',{privateStatusWord:v.status}],['기준일 비교',cmp.text,{privateBasisCompare:cmp.same?'SAME':'DIFFERENT'}],
   last?['마지막 종가',ram(last.date,' · ',last.close===null?'NA':last.close)]:null,
   ['평가일',v.evaluation_day,{privateEvaluationDay:'analysis'}],v.signal_day?['신호일',v.signal_day]:null,
   ['지표 가격 기준',v.basisText,{privateIndicatorBasis:v.basis}],['분할 증거',v.evidence],v.adjustment?['분할 상태',v.adjustment,{privateAdjustmentStates:''}]:null],{privateMeta:'technical'}),
  noteLine(m.note||v.note,'technical'),
  chart(b.value.bars,symbol),
  agreeLine(g,'analysis'),
  ...indicators,
  measuresPart(K,mRaw===undefined?null:mRaw,symbol,m.basisCode,v.evaluation_day)]);}

// Macro and news: the public file format, the public reader, the public block's own drawing (DC-44: one component, one format).
function renderShared(body,[raw],{kind,draw}){const K=I.kisPrivate;let value;
 if(kind==='macro'){const r=I.macroObserved.validate(raw);if(!r.ok)throw Error(r.code);value=r.value;}
 else{const NS=window.NewsSignals;if(NS&&typeof NS.validate==='function'){try{NS.validate(raw);}catch(_){throw Error('NEWS_SIGNALS_INVALID');}}
  const r=I.newsRefresh.validate(raw);if(!r.ok)throw Error(r.code);value=raw;}
 const nodes=draw(value);
 I.append(body,[h('p',{class:'hand',dataset:{privateLayer:kind,privateSource:'PRIVATE_ARCHIVE'}},K.SOURCE_WORDS,' · 같은 화면 같은 형식 · 공개 블록은 그대로'),h('p',{class:'reason',dataset:{privateLayerNote:''}},K.LAYER_NOTE),...nodes]);}

function renderQgv(body,[qRaw],{code,publicBasis}){const K=I.kisPrivate,q=K.validateQgv(qRaw);if(!q.ok)throw Error(q.code);
 const v=K.qgvView(q.value,code),cmp=K.basisCompare(publicBasis,v.price_basis_date);
 I.append(body,[h('p',{class:'hand',dataset:{privateLayer:'qgv'}},'비공개 · 공통 엔진 · 같은 형식 · ',v.official),h('p',{class:'reason',dataset:{privateLayerNote:''}},K.LAYER_NOTE),
  dl([['계산 판',v.calc_version],['가격 기준일',v.price_basis_date],['재무 입력 기준',q.value.financial_input_as_of||'없음'],['계산 시각',q.value.calculated_at],
   ['기준일 비교',cmp.text,{privateBasisCompare:cmp.same?'SAME':'DIFFERENT'}],['순위',v.rank,{privateRank:'NONE'}]],{privateMeta:'qgv'}),
  h('ul',{dataset:{privateCoverage:''}},v.coverage.map(t=>h('li',null,t))),
  v.row?h('div',{class:'sk card',dataset:{privateRow:v.row.code}},h('p',null,h('b',null,v.row.code)),h('ul',null,v.row.axes.map(t=>h('li',{dataset:{privateAxis:t.slice(0,1)}},ram(t)))),
   h('p',{dataset:{privateTotal:''}},ram(v.row.total)),v.row.price?h('p',{class:'reason'},v.row.price):null)
   :h('p',{class:'reason',dataset:{privateRow:'NONE'}},code?'이 기업은 비공개 계산 대상에 없습니다':'기업을 고르면 그 기업의 비공개 축을 보입니다')]);}

const READS=Object.freeze({technical:t=>(t.symbol?[['analysis',t.symbol],['chart',t.symbol],['technical',t.symbol,'OPTIONAL']]:null),qgv:()=>[['qgv',null]],macro:()=>[['macro',null]],news:()=>[['news',null]]});
const RENDER=Object.freeze({technical:renderTechnical,qgv:renderQgv,macro:renderShared,news:renderShared});
const EMPTY_WORD=Object.freeze({macro:'비공개 보관 관측 자료가 아직 없습니다',news:'비공개 보관 재생 결과가 아직 없습니다'});

function attach(panel,{signal,kind,target=()=>({}),publicBasis=()=>null,draw}){
 if(!Object.prototype.hasOwnProperty.call(READS,kind)||((kind==='macro'||kind==='news')&&typeof draw!=='function'))throw Error('PRIVATE_EXPAND_KIND');
 const P=()=>I.prices;
 const btn=h('button',{type:'button',class:'chip',dataset:{privateExpand:kind},'aria-expanded':'false'},'비공개 펼치기');
 const off=h('button',{type:'button',class:'chip',dataset:{privateDisconnect:kind},hidden:true},'비공개 연결 끊기');
 const note=h('p',{class:'reason',role:'status',dataset:{privateNote:kind}});
 const bar=h('div',{class:'load-row',dataset:{privateControls:kind}},btn,off,note);
 panel.node.insertBefore(bar,panel.node.querySelector('.private-body'));
 let open=false,seq=0;
 const st=()=>{try{return P().kisState();}catch(_){return{ready:false,connected:false,gis:false};}};
 function closed(msg){const s=st();open=false;seq++;btn.textContent='비공개 펼치기';btn.setAttribute('aria-expanded','false');off.hidden=!s.connected;
  if(!s.ready)panel.set('NOT_READY');else if(!s.connected)panel.set('LOGIN_REQUIRED');
  else panel.set('READY',{render:b=>I.append(b,[h('p',{class:'reason',dataset:{privateClosed:''}},'비공개 접힘 · 펼치면 서버에서 다시 확인하고 불러옵니다')])});
  note.textContent=msg||'';}
 function read(e){const t=target()||{},my=++seq;
  const req=READS[kind](t);
  if(!req){note.textContent='기업을 먼저 고르세요';return;}
  panel.set('LOADING');note.textContent=req.length>1?'비공개 자료 '+req.length+'개를 차례로 불러옵니다 · 서버 요청 간격 5초':'';
  let p;try{p=P().kisRead(e,req);}catch(err){p=Promise.reject(err);}
  Promise.resolve(p).then(res=>{if(my!==seq||signal.aborted)return;
   try{panel.set('READY',{render:b=>RENDER[kind](b,res,{kind,draw,symbol:t.symbol,code:t.code,publicBasis:publicBasis()})});}
   catch(err){panel.set('ERROR',{code:codeOf(err)});note.textContent='비공개 자료가 형식과 달라 보이지 않습니다';return;}
   open=true;btn.textContent='비공개 접기';btn.setAttribute('aria-expanded','true');off.hidden=false;},
  err=>{if(my!==seq||signal.aborted)return;const c=codeOf(err);if(c==='CANCELED')return;
   if(c==='AUTH_FORBIDDEN'||c==='AUTH_REQUIRED'){closed(word(c));return;}
   if(c==='KIS_SERIES_NOT_FOUND'){panel.set('EMPTY');note.textContent=EMPTY_WORD[kind]||word(c);return;}
   panel.set('ERROR',{code:c});note.textContent=word(c);});}
 btn.addEventListener('click',e=>{if(open){closed();return;}const s=st();
  if(!s.ready){closed(word('LOGIN_UNAVAILABLE'));return;}
  if(s.connected){read(e);return;}
  let p;try{p=P().kisConnect(e);}catch(err){p=Promise.reject(err);}
  Promise.resolve(p).then(r=>{if(signal.aborted)return;closed(r&&r.prepared?'Google 로그인 준비됨 · 비공개 펼치기를 한 번 더 누르세요':'로그인됨 · 비공개 펼치기를 한 번 더 누르면 서버에서 확인하고 불러옵니다');},
   err=>{if(!signal.aborted)closed(word(codeOf(err)));});},{signal});
 off.addEventListener('click',e=>{let p;try{p=P().kisDisconnect(e);}catch(err){p=Promise.reject(err);}Promise.resolve(p).then(()=>closed('비공개 연결을 끊었습니다'),()=>closed('비공개 연결을 끊었습니다'));},{signal});
 // A dropped token (expiry, 403, 연결 끊기 elsewhere) closes the panel and clears what it showed.
 const un=(()=>{try{return P().kisSubscribe(()=>{if(signal.aborted)return;if(!st().connected&&open)closed(word('AUTH_REQUIRED'));});}catch(_){return()=>{};}})();
 signal.addEventListener('abort',()=>{seq++;un();},{once:true});
 closed();
 return Object.freeze({reset:()=>closed()});}
I.privateExpand=Object.freeze({attach});
})();
