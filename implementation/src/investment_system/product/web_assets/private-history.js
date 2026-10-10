/* Private daily history is held only in memory and loaded by an explicit click. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.PrivateHistory = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const STORAGE_KEY = 'investment.web.v1.private-history-origin';
  const TARGETS = Object.freeze({asml:'ASML',lrcx:'LRCX',klac:'KLAC',nvda:'NVDA',amd:'AMD',avgo:'AVGO',qcom:'QCOM',intc:'INTC',msft:'MSFT',googl:'GOOGL',amzn:'AMZN',rtx:'RTX',stry:'SYK',etn:'ETN',hubb:'HUBB',gev:'GEV',rok:'ROK',hanmi:'042700.KS',tokyo_electron:'8035.T'});
  const RANGES = ['1mo','3mo','6mo','1y','2y','5y'];
  const CODES = new Set(['CONFIG_UNAVAILABLE','AUTH_FORBIDDEN','AUTH_UNAVAILABLE','REQUEST_INVALID','ORIGIN_FORBIDDEN','RATE_LIMITED','RATE_LIMIT_UNAVAILABLE','YAHOO_BLOCKED','YAHOO_UNAVAILABLE','YAHOO_TIMEOUT','YAHOO_FORMAT_CHANGED','YAHOO_TOO_LARGE','HISTORY_UNAVAILABLE','AUTH_REQUIRED','CANCELED']);
  const active = new Set();
  function fail(code) { throw new Error(code); }
  function symbolFor(companyId) { return Object.hasOwn(TARGETS, companyId) ? TARGETS[companyId] : null; }
  function parseWorkerOrigin(value) {
    const label = '[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?';
    if (typeof value !== 'string' || !new RegExp('^https://' + label + '\\.' + label + '\\.workers\\.dev/?$').test(value)) fail('REQUEST_INVALID');
    return value.replace(/\/$/, '');
  }
  function validateHistory(value, expected) {
    const validText = (text, pattern) => typeof text === 'string' && pattern.test(text);
    if (!value || Array.isArray(value) || typeof value !== 'object' || value.schema !== 'private-history/1' || value.provider !== 'Yahoo Finance(비공식)'
      || value.symbol !== expected.symbol || value.range !== expected.range || !Object.values(TARGETS).includes(value.symbol) || !RANGES.includes(value.range)
      || value.interval !== '1d' || value.basis !== 'RAW_CLOSE' || value.delay_status !== 'UNKNOWN'
      || value.currency !== (value.symbol.endsWith('.KS') ? 'KRW' : value.symbol.endsWith('.T') ? 'JPY' : 'USD') || !validText(value.exchange,/^[A-Za-z0-9._ -]{1,64}$/)
      || !validText(value.timezone,/^[A-Za-z0-9_+\-/]{1,64}$/)
      || !validText(value.read_at,/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?(?:Z|[+-]\d{2}:\d{2})$/) || !Number.isFinite(Date.parse(value.read_at))
      || !Array.isArray(value.bars) || value.bars.length > 1500) fail('YAHOO_FORMAT_CHANGED');
    let previous = 0;
    const bars = value.bars.map(bar => {
      if (!bar || Array.isArray(bar) || !Number.isSafeInteger(bar.timestamp) || bar.timestamp <= previous || bar.timestamp > Math.floor(Date.parse(value.read_at)/1000) || !['COMPLETE','IN_PROGRESS','UNKNOWN'].includes(bar.session_status)) fail('YAHOO_FORMAT_CHANGED');
      previous = bar.timestamp;
      const clean = {timestamp:bar.timestamp};
      for (const field of ['open','high','low','close','adjusted_close','volume']) {
        if (bar[field] !== null && (typeof bar[field] !== 'number' || !Number.isFinite(bar[field]) || (field === 'volume' ? bar[field] < 0 : bar[field] <= 0))) fail('YAHOO_FORMAT_CHANGED');
        clean[field] = bar[field];
      }
      clean.session_status = bar.session_status; return clean;
    });
    if (!bars.length || !bars.some(bar => bar.close !== null)) fail('HISTORY_UNAVAILABLE');
    return {schema:value.schema,provider:value.provider,symbol:value.symbol,range:value.range,currency:value.currency,exchange:value.exchange,timezone:value.timezone,interval:value.interval,basis:value.basis,delay_status:value.delay_status,read_at:value.read_at,bars};
  }
  function chartPaths(bars) {
    const values = bars.filter(bar => bar.close !== null).map(bar => bar.close);
    if (!values.length) return [];
    const minimum = Math.min(...values), maximum = Math.max(...values), spread = maximum - minimum || 1;
    const paths = []; let points = [];
    function finish() { if(points.length) paths.push(points.length===1 ? points[0]+' L'+points[0].slice(1) : points.join(' ')); points=[]; }
    bars.forEach((bar,index) => {
      if (bar.close === null) { finish(); return; }
      const x = 20 + index * 600 / Math.max(1,bars.length - 1), y = 220 - (bar.close - minimum) / spread * 200;
      points.push((points.length ? 'L' : 'M') + x.toFixed(2) + ',' + y.toFixed(2));
    });
    finish(); return paths;
  }
  function node(state,tag,text,attributes={}) {
    const result = state.doc.createElement(tag); if (text !== undefined) result.textContent = text;
    for (const [key,value] of Object.entries(attributes)) result.setAttribute(key,value); return result;
  }
  function words(state,ko,en) { return state.locale === 'en-US' ? en : ko; }
  function storedOrigin(view) { const value = view.localStorage.getItem(STORAGE_KEY); return value ? parseWorkerOrigin(value) : ''; }
  function mountSettings(host,options={}) {
    const state={doc:host.ownerDocument,locale:options.locale},view=state.doc.defaultView;
    const config=options.config||view.InvestmentAppConfig||{},enabled=config.privateHistoryEnabled===true;
    const root=node(state,'section',undefined,{class:'card','data-private-history-settings':''});
    root.append(node(state,'h2',words(state,'비공개 가격 차트 · Worker 주소','Private price chart · Worker address')),
      node(state,'p',enabled ? words(state,'주소를 저장하고 구글 로그인 버튼에서 이메일 확인 권한에 다시 동의하세요. 종목 화면에서 가격 불러오기를 누르면 비공개 일별 이력을 읽습니다. 주소는 백업에서 제외되며 가격 데이터는 저장하지 않습니다.','Save the address and consent again to email verification with the Google sign-in button. Press Load prices on a company screen to read private daily history. The address is excluded from backups and price data is never saved.') : words(state,'주소만 이 기기에 저장하며 백업에서 제외됩니다. 가격 데이터는 저장하지 않습니다. 현재 기능은 OFF입니다.','Only the address stays on this device and is excluded from backups. Price data is never saved. This feature is currently OFF.')));
    const form=node(state,'form',undefined,{novalidate:''}),label=node(state,'label',words(state,'Worker HTTPS 주소','Worker HTTPS address'));
    const input=node(state,'input',undefined,{type:'url','data-history-worker-url':'',autocomplete:'off',spellcheck:'false',maxlength:'256',placeholder:'https://<worker>.<account>.workers.dev'});
    const status=node(state,'p','',{role:'status','data-history-settings-status':''});
    try { input.value=storedOrigin(view)||(enabled&&config.privateHistoryWorkerOrigin ? parseWorkerOrigin(config.privateHistoryWorkerOrigin) : ''); } catch (_) { status.dataset.code='STORAGE_UNAVAILABLE'; status.textContent='STORAGE_UNAVAILABLE'; }
    label.append(input); form.append(label,node(state,'button',words(state,'주소 저장','Save address'),{type:'submit','data-history-action':'save'}));
    form.addEventListener('submit',event => {
      event.preventDefault();
      try {
        const origin=input.value === '' ? '' : parseWorkerOrigin(input.value);
        if (origin) view.localStorage.setItem(STORAGE_KEY,origin); else view.localStorage.removeItem(STORAGE_KEY);
        input.value=origin; status.dataset.code='SAVED'; status.textContent=enabled ? words(state,'주소를 이 기기에 저장했습니다. 구글 로그인 후 종목 화면에서 가격을 불러오세요.','Address saved on this device. Sign in with Google, then load prices on a company screen.') : words(state,'주소를 이 기기에 저장했습니다. 기능 OFF는 유지됩니다.','Address saved on this device. The feature remains OFF.');
      } catch (error) { status.dataset.code=error.message === 'REQUEST_INVALID' ? 'REQUEST_INVALID' : 'STORAGE_UNAVAILABLE'; status.textContent=status.dataset.code; }
    });
    root.append(form,status);
    if(enabled) {
      const links=node(state,'div',undefined,{class:'chips',role:'group','aria-label':words(state,'비공개 가격 이력 지원 종목','Symbols supported for private history')});
      for(const [companyId,symbol] of Object.entries(TARGETS)) links.append(node(state,'a',symbol,{href:'#company/'+companyId,'data-history-company':companyId}));
      root.append(links);
    }
    host.replaceChildren(root);
  }
  function mounted(state) { return !state.disposed && state.host.isConnected; }
  function status(state,code) { state.status.dataset.code=code; state.status.textContent=code==='OFF' ? words(state,'OFF · 가격 호출 없음','OFF · No price requests') : code; }
  function clear(state) {
    state.revision++; if (state.controller) { state.controller.abort(); state.controller=null; }
    if(state.tradeController){state.tradeController.abort();state.tradeController=null;}state.trades=null;state.tradeBusy=false;state.tradeMessage='';
    state.data=null; state.indicators=null; state.average=null; state.results.replaceChildren(); state.busy=false;
  }
  function available(state) {
    if (!state.enabled) return 'OFF';
    if (!state.symbol) return 'HISTORY_UNAVAILABLE';
    let origin; try { origin=storedOrigin(state.view); } catch (_) { return 'REQUEST_INVALID'; }
    if (!origin || origin !== state.approvedOrigin) return 'ORIGIN_UNAPPROVED';
    if (!state.session || !state.session.state().connected) return 'AUTH_REQUIRED';
    return 'READY';
  }
  function update(state) {
    if (!mounted(state)) return;
    const code=available(state);
    state.fetch.disabled=state.busy || code!=='READY'; if(state.tradeButton)state.tradeButton.disabled=state.tradeBusy||state.busy||code!=='READY'||!state.data; state.range.disabled=state.busy || !state.enabled || !state.symbol;
    if (!state.busy) status(state,code);
  }
  function renderData(state) {
    const data=state.data;
    state.results.replaceChildren();
    state.results.append(node(state,'p',data.provider+' · '+data.symbol+' · '+data.exchange+' · '+data.currency+' · '+data.timezone+' · '+data.interval+' · RAW_CLOSE · delay_status: UNKNOWN · read_at: '+data.read_at,{'data-history-meta':''}));
    state.indicators=state.view.ResearchIndicators.calculate(data.bars,{includeSma240:state.selected.has('SMA_240')});
    const buttons=node(state,'div',undefined,{class:'chart-controls',role:'group','aria-label':words(state,'연구용 이동평균','Research moving averages')});
    for(const id of ['SMA_5','SMA_20','SMA_60','SMA_120','SMA_240','EMA_20','AVG']){
      const button=node(state,'button',id.replace('_',''),{type:'button','data-chart-overlay':id,'aria-pressed':String(state.selected.has(id))});
      button.addEventListener('click',()=>{if(state.selected.has(id))state.selected.delete(id);else state.selected.add(id);renderData(state);state.results.querySelector('[data-chart-overlay="'+id+'"]').focus();});buttons.append(button);
    }
    state.results.append(buttons,node(state,'p','RESEARCH_DISPLAY_ONLY · '+words(state,'모델 채택 아님 · warm-up·결측·미완결 세션은 선 없음','Not a model · No lines during warm-up, missing or incomplete sessions')));
    state.view.TechnicalChart.render(state.results,{bars:data.bars,indicators:state.indicators,selected:state.selected,average:state.average,locale:state.locale,trades:state.trades?state.view.PrivateTrades.markers(state.trades,data.bars,data.symbol,data.timezone):[]});
    state.results.append(node(state,'p',state.average===null?'AVG · NOT_AVAILABLE':words(state,'AVG · 기기 보유의 평균 매입원가 · '+data.currency,'AVG · Device holding average cost · '+data.currency),{'data-average-status':state.average===null?'NOT_AVAILABLE':'AVAILABLE'}));
    state.results.append(node(state,'p',state.tradeMessage||words(state,'내 거래 · 아직 불러오지 않음','My trades · Not loaded'),{'data-trades-status':''}));
    const research=node(state,'details'),title=node(state,'summary',words(state,'연구용 지표 · RAM 전용','Research indicators · RAM only')),values=node(state,'dl');
    for(const item of state.indicators.indicators){values.append(node(state,'dt',item.indicator_id),node(state,'dd',item.values.at(-1)===null?'NOT_AVAILABLE · '+item.unavailable_reasons.at(-1):String(item.values.at(-1)),{'data-research-value':item.indicator_id}));}
    research.append(title,values);state.results.append(research);
    state.results.append(node(state,'p',words(state,'원시 OHLC 일봉입니다. 수정 종가는 아래 표에 별도로 표시합니다. 빈 값은 보간하지 않으며 세션 상태는 공급자 추정입니다.','Raw daily OHLC. Adjusted close remains separate below. Missing values are not interpolated; session status is a provider estimate.')));
    const details=node(state,'details'),summary=node(state,'summary',words(state,'일별 가격 표 · 세션 상태','Daily prices · Session status')),table=node(state,'table',undefined,{'data-history-table':''});
    const head=node(state,'thead'),labels=node(state,'tr');
    for (const label of ['UTC time','Open','High','Low','Raw close','Adjusted close','Volume','Session status']) labels.append(node(state,'th',label,{scope:'col'}));
    head.append(labels);table.append(head);const body=node(state,'tbody');
    for (const bar of data.bars) {
      const row=node(state,'tr'); row.append(node(state,'td',new Date(bar.timestamp*1000).toISOString()));
      for (const field of ['open','high','low','close','adjusted_close','volume']) row.append(node(state,'td',bar[field] === null ? '—' : String(bar[field]),{'data-history-field':field,'data-missing':bar[field]===null?'true':'false'}));
      row.append(node(state,'td',bar.session_status));body.append(row);
    }
    table.append(body);details.append(summary,table);state.results.append(details);
  }
  async function load(state) {
    if (state.busy || available(state)!=='READY') { update(state); return; }
    clear(state);const revision=state.revision,sessionRevision=state.session.revision(),range=state.range.value;
    state.controller=new state.view.AbortController();state.busy=true;status(state,'LOADING');state.fetch.disabled=true;state.range.disabled=true;
    const current=()=>mounted(state)&&state.revision===revision&&state.session.revision()===sessionRevision&&state.session.state().connected;
    try {
      const payload=await state.session.fetchHistory(storedOrigin(state.view),state.symbol,range,{approvedOrigin:state.approvedOrigin,signal:state.controller.signal});
      if (!current()) return;
      const data=validateHistory(payload,{symbol:state.symbol,range});
      let average=null;try{average=state.getAverage?await state.getAverage(state.symbol):null;}catch(_){}
      if(!current())return;state.data=data;state.average=typeof average==='number'&&Number.isFinite(average)&&average>0?average:null;renderData(state);
    } catch (error) {
      if (!mounted(state) || state.revision!==revision) return;
      state.data=null;state.results.replaceChildren();status(state,CODES.has(error.message) ? error.message : 'YAHOO_UNAVAILABLE');
    } finally {
      if (mounted(state)&&state.revision===revision) {state.busy=false;state.controller=null;state.range.disabled=false;state.fetch.disabled=available(state)!=='READY';if (state.data) {status(state,'READY');state.tradeButton.disabled=state.tradeBusy||available(state)!=='READY';}}
    }
  }
  async function loadTrades(state) {
    if(!state.data||state.tradeBusy||available(state)!=='READY')return;
    const revision=state.revision,sessionRevision=state.session.revision(),current=()=>mounted(state)&&state.revision===revision&&state.session.revision()===sessionRevision&&state.session.state().connected;
    state.tradeBusy=true;state.tradeButton.disabled=true;state.tradeController=new state.view.AbortController();
    try {
      const parsed=await state.view.PrivateTrades.read(state.view,state.session,{signal:state.tradeController.signal});
      if(!current())return;state.trades=parsed;
      const matching=parsed.rows.filter(r=>r.state==='USER_DEVICE_ONLY'&&r.symbol===state.symbol),markers=state.view.PrivateTrades.markers(parsed,state.data.bars,state.symbol,state.data.timezone);
      state.tradeMessage='B/S · '+markers.length+' · '+(parsed.row_limit_reached?'ROW_LIMIT_REACHED':parsed.rows.some(r=>r.state==='NOT_AVAILABLE')?'TRADES_PARTIAL':'READ_ONLY')+(matching.length>markers.length?' · UNMATCHED_SESSION '+(matching.length-markers.length):'');
    }catch(error){if(!current())return;state.trades=null;state.tradeMessage=['TRADES_SOURCE_REQUIRED','TRADES_SOURCE_INVALID','SOURCE_TOO_LARGE','AUTH_REQUIRED','CANCELED'].includes(error.message)?error.message:'TRADES_READ_FAILED';}
    finally{if(current()){state.tradeBusy=false;state.tradeController=null;state.tradeButton.disabled=false;renderData(state);}}
  }
  function dispose(state) {
    if (state.disposed) return;
    clear(state);state.disposed=true;if(state.unsubscribe)state.unsubscribe();if(state.observer)state.observer.disconnect();
    state.view.removeEventListener('pagehide',state.pagehide);active.delete(state);
  }
  async function mount(host,options={}) {
    const doc=host.ownerDocument,view=doc.defaultView,config=options.config||{};
    const state={host,doc,view,locale:options.locale,symbol:symbolFor(options.companyId),enabled:config.privateHistoryEnabled===true,approvedOrigin:config.privateHistoryWorkerOrigin||'',revision:0,data:null,indicators:null,average:null,getAverage:options.getAverage,trades:null,tradeBusy:false,tradeMessage:'',tradeController:null,selected:new Set(['SMA_5','SMA_20','SMA_60','SMA_120','AVG']),busy:false,disposed:false,controller:null};
    active.add(state);
    const root=node(state,'section',undefined,{class:'card private-history','data-private-history':''});
    root.append(node(state,'h2',words(state,'가격 차트 · 비공개 일별 이력','Price chart · Private daily history')));
    state.status=node(state,'p','',{role:'status','data-history-status':''});state.range=node(state,'select',undefined,{'data-history-range':'','aria-label':words(state,'가격 기간','History range')});
    for (const range of RANGES) state.range.append(node(state,'option',range,{value:range}));state.range.value='1y';
    state.fetch=node(state,'button',words(state,'가격 불러오기','Load prices'),{type:'button','data-history-action':'fetch'});
    state.tradeButton=node(state,'button',words(state,'내 거래 B/S 불러오기','Load my B/S trades'),{type:'button','data-history-action':'trades'});
    const close=node(state,'button',words(state,'가격 지우기','Clear prices'),{type:'button','data-history-action':'close'});
    state.results=node(state,'div',undefined,{'data-history-results':''});
    root.append(state.status,state.range,state.fetch,state.tradeButton,close,state.results);host.replaceChildren(root);
    state.tradeButton.addEventListener('click',()=>{void loadTrades(state);});
    state.fetch.addEventListener('click',()=>{void load(state);});state.range.addEventListener('change',()=>{clear(state);update(state);});close.addEventListener('click',()=>{clear(state);update(state);});
    state.pagehide=()=>{dispose(state);};view.addEventListener('pagehide',state.pagehide);
    if(view.MutationObserver){state.observer=new view.MutationObserver(()=>{if(!host.isConnected)dispose(state);});state.observer.observe(doc.documentElement,{childList:true,subtree:true});}
    update(state);
    if (state.enabled && state.symbol && config.googleSheetsClientId) {
      try {
        if(parseWorkerOrigin(state.approvedOrigin)!==state.approvedOrigin) fail('REQUEST_INVALID');
        state.session=view.GoogleSheetQuotes.sessionFor(view,config.googleSheetsClientId);
        const settings=await view.DeviceActual.sheetSettings(view);
        if (!mounted(state)) return;
        if(state.session.state().enabled!==settings.enabled)state.session.setEnabled(settings.enabled);
        state.unsubscribe=state.session.subscribe(()=>{if(!mounted(state)){dispose(state);return;}if(!state.session.state().connected || state.session.revision()!==state.sessionRevision){clear(state);state.sessionRevision=state.session.revision();}update(state);});
        state.sessionRevision=state.session.revision();
      } catch (_) { if (mounted(state)) status(state,'ORIGIN_UNAPPROVED'); }
      update(state);
    }
    return Object.freeze({clear(){clear(state);update(state);},dispose(){dispose(state);}});
  }
  function mountTechnical(host,options={}) {
    const state={doc:host.ownerDocument,view:host.ownerDocument.defaultView,locale:options.locale};
    const select=node(state,'select',undefined,{'data-technical-symbol':'','aria-label':words(state,'기술 차트 종목','Technical chart symbol')}),child=node(state,'div');
    for(const[id,symbol]of Object.entries(TARGETS))select.append(node(state,'option',symbol,{value:id}));
    select.value=symbolFor(options.companyId)?options.companyId:'asml';
    host.replaceChildren(select,child);const show=()=>{disposeAll();child.replaceChildren();void mount(child,{...options,companyId:select.value});};select.addEventListener('change',show);show();
  }
  function disposeAll() { for(const state of [...active])dispose(state); }
  return Object.freeze({mount,mountTechnical,mountSettings,disposeAll,validateHistory,chartPaths,symbolFor,parseWorkerOrigin});
});
