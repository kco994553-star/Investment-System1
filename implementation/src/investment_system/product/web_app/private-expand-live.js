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
     KIS · 비공개 and the chart's basis (원주가 / 확인된 분할 반영). Indicators and measures by their producer tier (below); a held one is
     미산출 with its reasons; a raw value appears only as the producer's reference_value, tagged. A result whose basis differs from the chart file's is not
     attached (IS2.kisPrivate.basisAgreement): that part shows the mismatch line and no value ([data-private-basis-agreement]).
     A missing measures file (404) is that part's 자료 없음; a refused one that part's refusal; the analysis and chart stay.
   - kind 'qgv': the qgv route → label KIS · 비공개 · 공식 아님, the price basis day and the source, the target().code row's
     Q / G / V (미산출 + reason, never 0), the total only when V exists, no rank, and the coverage counts. Nothing here
     recomputes a score or a rank: the file's values are shown as they are.
   - Tiers come only from the producer's display fields (Codex #556; IS2.kisPrivate displayOf / analysisTiers / measuresTiers):
     a VERIFIED metric shows its adopted value with 검증됨, an UNVERIFIED_REFERENCE one its reference_value with 검증 전(참고);
     WITHHELD shows no reference value, one line naming the hold reason; a missing or unknown display shows no value
     (검증 표시 없음). A held item shows its one-line reason only. Class shares: a file names BRK/B or BF/B for BRK-B / BF-B.
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

function chart(bars,symbol){const TC=window.TechnicalChart;const nums=bars.map(b=>({close:b.close===null?null:Number(b.close)}));
 const g=TC&&typeof TC.geometry==='function'?TC.geometry(nums,[]):null;
 if(!g)return h('p',{class:'reason',dataset:{privateChart:'NONE'}},'그릴 종가가 없습니다');
 return h('svg:svg',{class:'curve tech-chart',viewBox:'0 0 640 240',role:'img',focusable:'false',dataset:{privateChart:symbol},'aria-label':'KIS 일봉 종가 선 · '+symbol+' · '+bars.length+'봉'},
  h('svg:path',{d:'M20,220 L620,220',class:'curve-base'}),TC.paths(nums.map(b=>b.close),g).map(p=>h('svg:path',{d:p,class:'curve-s',dataset:{privateCloseLine:''}})));}

// The five measures part: EMPTY (no file), REFUSED (the file breaks its contract: nothing of it shown), BASIS_MISMATCH (its basis
// is not the chart's: the mismatch line only, no value) or READY.
// A metric's value cell: the value as RAM text with its tier tag (검증됨 / 검증 전(참고)), or its one-line reason.
// Display only (owner 2026-11-18, DC-56 screen text): readable indicator names, values shown to two decimals (the file's value is
// kept as given; nothing is recomputed), and the verification tag once at the top of the cell; a row carries its own tag only when
// its state differs from the top one.
const NAME_RULES=Object.freeze([[/^SMA_(\d+)$/,m=>'이동평균('+m[1]+')'],[/^EMA_(\d+)$/,m=>'지수이동평균('+m[1]+')'],[/^RSI_(\d+)$/,m=>'RSI('+m[1]+')'],
 [/^ATR_(\d+)$/,m=>'ATR('+m[1]+')'],[/^BOLL_UPPER_(\d+)_(\d+(?:\.\d+)?)$/,m=>'볼린저 상단('+m[1]+', '+m[2]+'σ)'],[/^BOLL_LOWER_(\d+)_(\d+(?:\.\d+)?)$/,m=>'볼린저 하단('+m[1]+', '+m[2]+'σ)'],
 [/^BOLL_MIDDLE_(\d+)$/,m=>'볼린저 중심('+m[1]+')'],[/^MACD_SIGNAL_(\d+)$/,m=>'MACD 시그널('+m[1]+')'],
 [/^MACD_HISTOGRAM_(\d+)_(\d+)_(\d+)$/,m=>'MACD 히스토그램('+m[1]+', '+m[2]+', '+m[3]+')'],[/^MACD_(\d+)_(\d+)$/,m=>'MACD('+m[1]+', '+m[2]+')']]);
const nameOf=label=>{for(const[re,f]of NAME_RULES){const m=re.exec(label);if(m)return f(m);}return label;};
const LONG=/^(-?\d+)\.(\d{3,})(\s.*)?$/;
const shown=v=>{const m=typeof v==='string'?LONG.exec(v):null;if(!m)return v;const n=Number(m[1]+'.'+m[2]);if(!Number.isFinite(n))return v;
 const s=n.toFixed(2);return(s==='-0.00'?'0.00':s)+(m[3]||'');};
const tagOf=(kind,tag)=>h('span',{class:'chip',dataset:{privateVerification:kind}},tag);
const valueCell=(x,top)=>x.value!==null?[ram(shown(x.value)),x.kind===top?null:[' ',tagOf(x.kind,x.tag)]]:x.text;
// The metric rows of one file under its display (IS2.kisPrivate tiers): the WITHHELD line once, VERIFIED / REFERENCE / HELD rows.
// top = the tag already at the top of the panel (the chart's), or null: then this part shows the most common tag of its valued rows
// once above its rows.
function tierPart(t,data,empty,top=null){
 if(t.display.state==='UNKNOWN')return[warn(t.display.line,{privateDisplay:'UNKNOWN',...data})];
 const valued=t.rows.filter(x=>x.value!==null);let head=null,k=top;
 if(!k&&valued.length){const n=new Map();for(const x of valued)n.set(x.kind,(n.get(x.kind)||0)+1);k=[...n].sort((a,b)=>b[1]-a[1])[0][0];
  head=h('p',{class:'sub',dataset:{privateTierHead:k}},tagOf(k,valued.find(x=>x.kind===k).tag));}
 return[t.display.state==='WITHHELD'?warn(t.display.line,{privateDisplay:'WITHHELD',...data}):null,head,
  t.rows.length?table(t.rows.map(x=>[nameOf(x.label),valueCell(x,k),{privateMetric:x.id,privateTier:x.kind}]),data):t.display.state==='WITHHELD'?null:warn(empty,data)];}

// The five measures part: EMPTY (no file), REFUSED (the file breaks its contract: nothing of it shown), BASIS_MISMATCH (its basis
// is not the chart's: the mismatch line only, no value) or READY.
function measuresPart(K,raw,symbol,chartBasis,status,top=null){
 const part=(st,...c)=>h('div',{class:'sk card',dataset:{privateMeasures:st}},h('h4',null,'다섯 측정값'),...c);
 if(raw===null)return part('EMPTY',warn('자료 없음'));
 const r=K.validateMeasures(raw);
 if(!r.ok||K.requestSymbol(r.value.symbol)!==symbol){const code=r.ok?'SYMBOL_MISMATCH':r.code;return part('REFUSED',warn('형식 오류 · '+code,{na:code}));}
 const v=K.measuresView(r.value),g=K.basisAgreement(chartBasis,r.value);
 status.push(['측정 평가일',v.evaluation_day,{privateEvaluationDay:'measures'}],['측정 가격 기준',v.basisText,{privateMeasuresBasis:v.basis}],
  ['측정 설정 판',v.settings_version,{privateSettingsVersion:''}],['측정 수집 시각',v.collected_at],['측정 분할 증거',v.evidence],['측정 개수',v.summary,{privateMeasuresCounts:''}]);
 if(!g.same)return part('BASIS_MISMATCH',warn(g.text,{privateBasisAgreement:g.code,privateBasisPart:'measures'}));
 return part('READY',v.status!=='NORMAL'?warn(v.statusText,{privateMeasuresStatus:v.status}):null,...tierPart(K.measuresTiers(r.value),{privateMeasuresRows:''},'측정값 없음',top));}

function renderTechnical(body,[aRaw,bRaw,mRaw],{symbol,publicBasis},status){const K=I.kisPrivate,a=K.validateAnalysis(aRaw),b=K.validateBars(bRaw);
 if(!a.ok||!b.ok){const r=a.ok?b:a;throw Error(r.code);}
 // The chart must be the company asked for (a class share's file names it BRK/B for BRK-B).
 if(K.requestSymbol(b.value.symbol)!==symbol)throw Error('SYMBOL_MISMATCH');
 const v=K.analysisView(a.value),m=K.barsMeta(b.value),cmp=K.basisCompare(publicBasis,m.price_basis_date),last=b.value.bars[b.value.bars.length-1];
 const g=K.basisAgreement(m.basisCode,a.value),dc=K.displayOf(b.value);
 status.push(['공급처',m.source],['수집 시각',m.collected_at],['정정',m.corrected],['평가일',v.evaluation_day,{privateEvaluationDay:'analysis'}],v.signal_day?['신호일',v.signal_day]:null,
  ['상태',v.statusText,{privateStatusWord:v.status}],['지표 가격 기준',v.basisText,{privateIndicatorBasis:v.basis}],['분할 증거',v.evidence],v.adjustment?['분할 상태',v.adjustment,{privateAdjustmentStates:''}]:null,
  m.note||v.note?['분할 반영',m.note||v.note,{privateAdjustedNote:'technical'}]:null,['기준일 비교',cmp.text,{privateBasisCompare:cmp.same?'SAME':'DIFFERENT'}],['지표 개수',v.summary,{privateCounts:''}]);
 // Indicators only on a chart of the same basis; otherwise the mismatch line and nothing of the indicators (no value, no count).
 const top=dc.state==='AVAILABLE'?'REFERENCE':null;
 const indicators=g.same?tierPart(K.analysisTiers(a.value),{privateIndicators:''},'지표 없음',top):[warn(g.text,{privateBasisAgreement:g.code,privateBasisPart:'analysis'})];
 // The chart's closes are reference values: drawn only when its display is AVAILABLE; WITHHELD / unknown leave one line.
 const closes=dc.state==='AVAILABLE'?[last?table([['마지막 종가',[ram(last.date,' · ',last.close===null?'NA':last.close)]]],{privateLast:''}):null,chart(b.value.bars,symbol)]
  :[warn(dc.line,{privateDisplay:dc.state,privateDisplayPart:'chart'})];
 I.append(body,[h('p',{class:'hand',dataset:{privateLayer:'technical'}},'KIS · 비공개 · 가격 기준일 ',h('span',{dataset:{privateBasisDate:''}},m.price_basis_date||'없음'),' · ',h('span',{dataset:{privateChartBasis:m.basisCode}},m.basis),
   dc.state==='AVAILABLE'?[' ',h('span',{class:'chip',dataset:{privateVerification:'REFERENCE'}},dc.tag)]:null),
  v.status!=='NORMAL'?warn(v.statusText,{privateStatusLine:v.status}):null,
  ...closes,
  ...indicators,
  measuresPart(K,mRaw===undefined?null:mRaw,symbol,m.basisCode,status,top)]);}

function renderQgv(body,[qRaw],{code,publicBasis},status){const K=I.kisPrivate,q=K.validateQgv(qRaw);if(!q.ok)throw Error(q.code);
 const v=K.qgvView(q.value,code),cmp=K.basisCompare(publicBasis,v.price_basis_date),d=v.display;
 status.push(['재무 입력 기준',q.value.financial_input_as_of||'없음'],['계산 시각',q.value.calculated_at],v.stages?['단계',v.stages]:null,v.diagnostics?['총점 진단',v.diagnostics]:null,v.bases?['기준',v.bases]:null,
  ['기준일 비교',cmp.text,{privateBasisCompare:cmp.same?'SAME':'DIFFERENT'}],['순위',v.rank,{privateRank:'NONE'}]);
 // A missing or unknown display shows no value (fails closed); the file's values are shown as given, never recomputed.
 const row=d.state==='UNKNOWN'?warn(d.line,{privateDisplay:'UNKNOWN',privateRow:'NONE'})
  :v.row?table([...v.row.axes.map(t=>[t.slice(0,1),ram(t.slice(2)),{privateAxis:t.slice(0,1)}]),['총점',ram(v.row.total),{privateTotal:''}],
   v.row.price?['가격',v.row.price]:null],{privateRow:v.row.code})
   :warn(code?'이 기업은 KIS 계산 대상에 없습니다':'기업을 고르세요',{privateRow:'NONE'});
 I.append(body,[h('p',{class:'hand',dataset:{privateLayer:'qgv'}},'KIS · 비공개 · 공식 아님 · 가격 기준일 ',h('span',{dataset:{privateBasisDate:''}},v.price_basis_date),' · 출처 ',
   h('span',{dataset:{privateSource:''}},v.source),' · 계산 판 ',h('span',{dataset:{privateCalcVersion:''}},v.calc_version),
   d.tag?[' ',h('span',{class:'chip',dataset:{privateVerification:'REFERENCE'}},d.tag)]:null),
  row,
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
 // While a read runs the button stays pressed-off (owner check 2026-11-17: a second tap during the ~15 s of three spaced reads
 // started a second, overlapping read that the Worker refused RATE_LIMITED); the layer also queues reads, this only shows it.
 function busy(on){btn.disabled=on;if(on){btn.setAttribute('aria-busy','true');btn.textContent='불러오는 중…';}else{btn.removeAttribute('aria-busy');btn.textContent='비공개 펼치기';}}
 function closed(msg){const s=st();open=false;seq++;busy(false);btn.textContent='비공개 펼치기';btn.setAttribute('aria-expanded','false');off.hidden=!s.connected;
  box.hidden=!s.connected;resetToken();factBox.replaceChildren();
  if(!s.ready)panel.set('NOT_READY');else if(!s.connected)panel.set('LOGIN_REQUIRED');
  else panel.set('READY',{render:b=>I.append(b,[h('p',{class:'reason',dataset:{privateClosed:''}},'비공개 접힘')])});
  note.textContent=msg||'';}
 function read(e){const t=target()||{},my=++seq;
  const req=READS[kind](t);
  if(!req){note.textContent='기업을 먼저 고르세요';return;}
  panel.set('LOADING');factBox.replaceChildren();note.textContent='';busy(true);
  let p;try{p=P().kisRead(e,req);}catch(err){p=Promise.reject(err);}
  Promise.resolve(p).then(res=>{if(my!==seq||signal.aborted)return;busy(false);const status=[];
   try{panel.set('READY',{render:b=>RENDER[kind](b,res,{symbol:t.symbol,code:t.code,publicBasis:publicBasis()},status)});}
   catch(err){const c=codeOf(err);panel.set('ERROR',{code:c});note.textContent='형식 오류 · '+c;return;}
   factBox.replaceChildren(facts(status,kind));
   open=true;btn.textContent='비공개 접기';btn.setAttribute('aria-expanded','true');off.hidden=false;box.hidden=false;},
  err=>{if(my!==seq||signal.aborted)return;busy(false);const c=codeOf(err);if(c==='CANCELED')return;
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
