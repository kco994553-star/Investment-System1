/* S08 indicator cards and canon sections. RESEARCH_DISPLAY_ONLY values come from ResearchIndicators.calculate
   on the daily bars the chart already holds. Nothing here is stored, fetched or sent; missing values stay NOT_AVAILABLE. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.TechnicalCards=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
 'use strict';
 const NA='NOT_AVAILABLE';
 // card id, Korean title, English title, items [indicator id, label]. Cards without items have no approved definition.
 const CARDS=Object.freeze([
  {id:'trend',ko:'추세',en:'Trend',items:[['SMA_5','SMA 5'],['SMA_20','SMA 20'],['SMA_60','SMA 60'],['SMA_120','SMA 120'],['SMA_240','SMA 240'],['EMA_20','EMA 20']]},
  {id:'momentum',ko:'모멘텀',en:'Momentum',items:[['RSI_14','RSI 14'],['MACD_12_26','MACD 12·26'],['MACD_SIGNAL_9','Signal 9'],['MACD_HISTOGRAM_12_26_9','Histogram']]},
  {id:'volume',ko:'거래량',en:'Volume',items:[],reasonKo:'승인된 거래량 지표 정의 없음',reasonEn:'No approved volume indicator definition'},
  {id:'relative',ko:'상대강도',en:'Relative strength',items:[],reasonKo:'승인된 상대강도 정의 없음',reasonEn:'No approved relative-strength definition'},
  {id:'structure',ko:'구조 · 지지·저항',en:'Structure · support/resistance',items:[],reasonKo:'승인된 지지·저항 정의 없음',reasonEn:'No approved support/resistance definition'},
  {id:'volatility',ko:'변동성',en:'Volatility',items:[['ATR_14','ATR 14'],['BOLL_UPPER_20_2','Bollinger upper 20·2σ'],['BOLL_MIDDLE_20','Bollinger middle 20'],['BOLL_LOWER_20_2','Bollinger lower 20·2σ']]}
 ]);
 function format(value,locale){return Number(value).toLocaleString(locale==='en-US'?'en-US':'ko-KR',{minimumFractionDigits:2,maximumFractionDigits:2});}
 function node(doc,tag,text,attrs={}){const n=doc.createElement(tag);if(text!==undefined)n.textContent=text;for(const[k,v]of Object.entries(attrs))n.setAttribute(k,v);return n;}
 // Latest value of one indicator for display: a finite number or NOT_AVAILABLE with a reason code. Never 0 for missing.
 function latest(result,id){
  if(!result||result.state==='NOT_AVAILABLE'||!Array.isArray(result.indicators))return{state:NA,reason:result&&result.reason_code?result.reason_code:'NO_DAILY_BARS'};
  const item=result.indicators.find(x=>x.indicator_id===id);
  if(!item)return{state:NA,reason:id==='SMA_240'?'OPTIONAL_OFF':'NOT_COMPUTED'};
  const v=item.values.at(-1);
  if(typeof v!=='number'||!Number.isFinite(v))return{state:NA,reason:item.unavailable_reasons.at(-1)||'WARMUP'};
  return{state:'AVAILABLE',value:v};
 }
 function mount(host,options={}){
  const doc=host.ownerDocument,en=options.locale==='en-US',locale=options.locale;
  let mode='model',payload=null,disposed=false;
  const root=node(doc,'section',undefined,{class:'card technical-cards','data-indicator-cards':''});
  const title=node(doc,'h2',en?'Indicators · 6 cards':'지표 6개 카드');
  const toggle=node(doc,'div',undefined,{class:'chips mode-toggle',role:'group','aria-label':en?'Indicator set':'지표 구분'});
  const modeButtons={};
  for(const[id,ko,enl]of [['model','모델 지표','Model indicators'],['research','연구용 지표','Research indicators']]){
   const b=node(doc,'button',en?enl:ko,{type:'button','data-indicator-mode':id,'aria-pressed':String(id===mode)});
   b.addEventListener('click',()=>{mode=id;paint();});modeButtons[id]=b;toggle.append(b);
  }
  const note=node(doc,'p',undefined,{class:'small','data-indicator-note':''});
  const meta=node(doc,'p',undefined,{class:'small','data-indicator-meta':''});
  const grid=node(doc,'div',undefined,{class:'indicator-grid'});
  root.append(title,toggle,note,meta,grid);
  function paint(){
   if(disposed||!host.isConnected)return;
   for(const[id,b]of Object.entries(modeButtons))b.setAttribute('aria-pressed',String(id===mode));
   root.dataset.mode=mode;
   if(mode==='model'){
    note.textContent=en?'Model indicators · NOT_AVAILABLE (model inputs are not connected)':'모델 지표 · NOT_AVAILABLE (모델 입력 미연결)';
    note.dataset.role='MODEL';meta.textContent='';
   }else{
    note.textContent=en?'Display only · not used by the model or QGV':'표시 전용 · 모델·QGV에 쓰지 않음';
    note.dataset.role='RESEARCH_DISPLAY_ONLY';
    meta.textContent=payload?[payload.symbol,payload.currency,payload.asOf,'RAM only'].filter(Boolean).join(' · '):(en?'No daily bars loaded · RAM only':'일봉 없음 · RAM 전용');
   }
   grid.replaceChildren();
   for(const card of CARDS){
    const box=node(doc,'article',undefined,{class:'indicator-card','data-indicator-card':card.id}),list=node(doc,'dl');
    box.append(node(doc,'h3',en?card.en:card.ko));
    if(mode==='model'){
     box.append(node(doc,'p',NA+' · '+(en?'Model inputs not connected':'모델 입력 미연결'),{'data-card-value':'MODEL_'+card.id,'data-state':NA}));
    }else if(!card.items.length){
     box.append(node(doc,'p',NA+' · '+(en?card.reasonEn:card.reasonKo),{'data-card-value':card.id.toUpperCase(),'data-state':NA}));
    }else{
     for(const[id,label]of card.items){
      const r=latest(payload&&payload.indicators,id);
      if(id==='SMA_240'&&r.reason==='OPTIONAL_OFF')continue; // optional line, default OFF: not shown until selected on the chart
      list.append(node(doc,'dt',label),node(doc,'dd',r.state===NA?NA+' · '+r.reason:format(r.value,locale),{class:'num','data-card-value':id,'data-state':r.state}));
     }
     box.append(list);
    }
    grid.append(box);
   }
  }
  host.replaceChildren(root);paint();
  return Object.freeze({
   update(next){payload=next&&next.indicators?{indicators:next.indicators,symbol:next.symbol||'',currency:next.currency||'',asOf:next.asOf||''}:null;paint();},
   mode(){return mode;},
   dispose(){disposed=true;payload=null;}
  });
 }
 // Canon sections with no defined data: every value is NOT_AVAILABLE with a reason. Static text only.
 function sectionsHtml(locale){
  const en=locale==='en-US',x=(ko,e)=>en?e:ko,na='<span class="badge NOT_AVAILABLE">NOT_AVAILABLE</span>';
  return `<section class="card" id="technical-phase" data-tech-section="phase"><h2>${x('상태·국면','State · regime')}</h2>
   <p>${na} ${x('상승·횡보·하락·변동성 확대 판정에 대한 승인된 정의가 없어 국면을 만들지 않습니다.','No approved definition for up / sideways / down / volatility-expansion, so no regime is produced.')}</p>
   <dl class="kv"><dt>${x('현재 국면','Current regime')}</dt><dd data-na="NOT_AVAILABLE">—</dd><dt>${x('바뀐 시점','Changed on')}</dt><dd data-na="NOT_AVAILABLE">—</dd></dl></section>
  <section class="card" id="technical-qgv-context" data-tech-section="qgv-context"><h2>${x('QGV 맥락 (격리 · 공식 점수 아님)','QGV context (isolated · not an official score)')}</h2>
   <p class="small">${x('QGV 원점수와 기술적 상태를 나란히 보여 주기만 하며 합치거나 서로의 입력으로 쓰지 않습니다.','Raw QGV and the technical state are only shown side by side; they are not combined or used as inputs to each other.')}</p>
   <div class="side-by-side"><div data-qgv-context="raw"><h3>${x('QGV 원점수','Raw QGV')}</h3><p>${na} ${x('이 화면에 연결된 점수 없음','No score connected here')}</p></div>
   <div data-qgv-context="technical"><h3>${x('기술적 상태','Technical state')}</h3><p>${na} ${x('상태 정의 없음','No state definition')}</p></div></div></section>
  <section class="card" id="technical-scenarios" data-tech-section="scenarios"><h2>${x('시나리오 (확률 검증 전)','Scenarios (before probability validation)')}</h2>
   <p>${na} ${x('확률·신뢰도·기간·범위·발동/확인·무효화·QGV 적합성은 검증이 끝난 결과만 표시합니다. 숫자 확률을 임의로 채우지 않습니다.','Probability, confidence, horizon, range, trigger/confirmation, invalidation and QGV fit appear only after validation. No numeric probability is filled in.')}</p></section>`;
 }
 return Object.freeze({CARDS,mount,latest,format,sectionsHtml});
});
