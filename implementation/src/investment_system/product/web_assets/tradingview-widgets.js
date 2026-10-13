/* TradingView free embed widgets (Ticker Tape, Mini Symbol Overview, Advanced Chart). DISPLAY ONLY.
   The widget renders inside a cross-origin iframe; nothing in this app reads a value from it, and no value
   goes into a calculation, ledger, sheet, export or log. Only public symbols are sent to TradingView.
   The embed script is inserted only when a screen with a widget is opened, never while the switch is off. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.TradingViewWidgets=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
 'use strict';
 const STORAGE_KEY='investment.web.v1.tradingview-widgets';
 const SCRIPT_ROOT='https://s3.tradingview.com/external-embedding/';
 const SCRIPTS=Object.freeze({ticker:SCRIPT_ROOT+'embed-widget-ticker-tape.js',mini:SCRIPT_ROOT+'embed-widget-mini-symbol-overview.js',advanced:SCRIPT_ROOT+'embed-widget-advanced-chart.js'});
 // TARGET 19 (same company ids as the private history Worker allowlist) mapped to TradingView EXCHANGE:NAME symbols.
 const SYMBOLS=Object.freeze({asml:'NASDAQ:ASML',lrcx:'NASDAQ:LRCX',klac:'NASDAQ:KLAC',nvda:'NASDAQ:NVDA',amd:'NASDAQ:AMD',avgo:'NASDAQ:AVGO',qcom:'NASDAQ:QCOM',intc:'NASDAQ:INTC',msft:'NASDAQ:MSFT',googl:'NASDAQ:GOOGL',amzn:'NASDAQ:AMZN',
  rtx:'NYSE:RTX',stry:'NYSE:SYK',etn:'NYSE:ETN',hubb:'NYSE:HUBB',gev:'NYSE:GEV',rok:'NYSE:ROK',hanmi:'KRX:042700',tokyo_electron:'TSE:8035'});
 const TITLES=Object.freeze({'KRX:042700':['한미반도체','Hanmi Semi'],'TSE:8035':['도쿄일렉트론','Tokyo Electron']});
 // Free-widget availability. NOT_DISPLAYED symbols never load a widget and show the fallback text instead.
 // TSE: third-party headless-Chromium test (2026-10) reports the free embed refuses Tokyo data. KRX: not verified.
 const AVAILABILITY=Object.freeze({'TSE:8035':'NOT_DISPLAYED','KRX:042700':'UNVERIFIED'});
 const TEXT=Object.freeze({
  note:['표시 전용 · 계산에 쓰지 않음','Display only · not used in calculations'],
  ticker:['TARGET 19 시세 띠 · TradingView','TARGET 19 ticker tape · TradingView'],
  mini:['미니 차트 · TradingView','Mini chart · TradingView'],
  advanced:['전체 차트 · TradingView','Full chart · TradingView'],
  off:['위젯 끄기','Turn widgets off'],on:['위젯 켜기','Turn widgets on'],
  disabled:['TradingView 위젯이 꺼져 있습니다. 외부 스크립트를 불러오지 않습니다.','TradingView widgets are off. No external script is loaded.'],
  blocked:['TradingView 위젯을 불러오지 못했습니다(차단·오프라인). 앱의 계산·기록에는 영향이 없습니다.','The TradingView widget could not load (blocked or offline). App calculations and records are unaffected.'],
  notDisplayed:['이 종목은 TradingView 무료 위젯에서 표시되지 않음','This symbol is not shown by TradingView free widgets'],
  unverified:['무료 위젯 표시 여부 미확인 · 비어 있으면 이 종목은 TradingView 무료 위젯에서 표시되지 않음','Free-widget display unverified · if empty, this symbol is not shown by TradingView free widgets'],
  settings:['TradingView 위젯','TradingView widgets'],
  settingsHelp:['홈 시세 띠 · 기업 미니 차트 · 기술 전체 차트. 로그인 없이 표시만 하며 계산에 쓰지 않습니다. 이 기기에만 저장됩니다.','Home ticker tape · company mini chart · technical full chart. Shown without login, display only, never used in calculations. Saved on this device only.'],
  attribution:['차트·시세 제공: TradingView','Charts and quotes by TradingView']
 });
 function words(locale,key){return TEXT[key][locale==='en-US'?1:0];}
 function symbolFor(companyId){return typeof companyId==='string'&&Object.hasOwn(SYMBOLS,companyId)?SYMBOLS[companyId]:null;}
 function availability(symbol){return Object.hasOwn(AVAILABILITY,symbol)?AVAILABILITY[symbol]:'AVAILABLE';}
 function enabled(storage){try{return storage.getItem(STORAGE_KEY)!=='off';}catch(_){return true;}}
 function setEnabled(storage,on){try{if(on)storage.removeItem(STORAGE_KEY);else storage.setItem(STORAGE_KEY,'off');return true;}catch(_){return false;}}
 function tvLocale(locale){return locale==='en-US'?'en':'kr';}
 function tickerSymbols(locale){
  return Object.values(SYMBOLS).filter(s=>availability(s)!=='NOT_DISPLAYED').map(s=>({proName:s,title:Object.hasOwn(TITLES,s)?TITLES[s][locale==='en-US'?1:0]:s.split(':')[1]}));
 }
 // Widget configs carry symbols and presentation options only: no price, holding, sheet ID or token.
 function config(kind,symbol,locale){
  const base={locale:tvLocale(locale),colorTheme:'light',isTransparent:false};
  if(kind==='ticker')return {...base,symbols:tickerSymbols(locale),showSymbolLogo:false,displayMode:'adaptive'};
  if(kind==='mini')return {...base,symbol,width:'100%',height:'100%',dateRange:'12M',autosize:true,noTimeScale:false,chartOnly:false};
  return {locale:tvLocale(locale),symbol,autosize:true,interval:'D',timezone:'Etc/UTC',theme:'light',style:'1',allow_symbol_change:false,hide_side_toolbar:true,save_image:false,calendar:false,withdateranges:true,details:false,hotlist:false,support_host:'https://www.tradingview.com'};
 }
 function el(doc,tag,attrs,text){const n=doc.createElement(tag);for(const[k,v]of Object.entries(attrs||{}))n.setAttribute(k,v);if(text!==undefined)n.textContent=text;return n;}
 function fallback(doc,locale,key,extra){return el(doc,'p',{class:'tv-fallback','data-tv-fallback':key,role:'status'},words(locale,key)+(extra?' · '+extra:''));}
 function mount(host,options){
  if(!host)return null;
  const doc=host.ownerDocument,win=doc.defaultView,locale=options.locale,kind=options.kind,storage=options.storage||win.localStorage;
  const symbol=kind==='ticker'?null:symbolFor(options.companyId);
  if(kind!=='ticker'&&!symbol){host.replaceChildren();return null;}
  const card=el(doc,'section',{class:'card tv-widget','data-tv-widget':kind});
  const head=el(doc,'div',{class:'row tv-head'});head.append(el(doc,'h2',{},words(locale,kind)+(symbol?' · '+symbol:'')));
  const on=enabled(storage),toggle=el(doc,'button',{type:'button','data-tv-toggle':on?'off':'on'},words(locale,on?'off':'on'));
  toggle.addEventListener('click',()=>{setEnabled(storage,!on);mount(host,options);if(typeof options.onToggle==='function')options.onToggle(!on);});
  head.append(toggle);card.append(head,el(doc,'p',{class:'small tv-note','data-tv-note':''},words(locale,'note')));
  host.replaceChildren(card);
  if(!on){card.append(el(doc,'p',{class:'small','data-tv-disabled':''},words(locale,'disabled')));return card;}
  if(symbol&&availability(symbol)==='NOT_DISPLAYED'){card.append(fallback(doc,locale,'notDisplayed',symbol));return card;}
  if(kind==='ticker'){const hidden=Object.values(SYMBOLS).filter(s=>availability(s)==='NOT_DISPLAYED');if(hidden.length)card.append(el(doc,'p',{class:'small','data-tv-excluded':hidden.join(' ')},hidden.join(', ')+': '+words(locale,'notDisplayed')));}
  if((symbol&&availability(symbol)==='UNVERIFIED')||(kind==='ticker'&&Object.values(SYMBOLS).some(s=>availability(s)==='UNVERIFIED')))
   card.append(el(doc,'p',{class:'small','data-tv-unverified':''},(kind==='ticker'?Object.values(SYMBOLS).filter(s=>availability(s)==='UNVERIFIED').join(', ')+': ':'')+words(locale,'unverified')));
  const frame=el(doc,'div',{class:'tradingview-widget-container tv-frame tv-frame-'+kind,'data-tv-frame':kind});
  frame.append(el(doc,'div',{class:'tradingview-widget-container__widget'}));
  card.append(frame,el(doc,'p',{class:'small tv-attribution'},words(locale,'attribution')));
  const fail=()=>{if(frame.isConnected)frame.replaceWith(fallback(doc,locale,'blocked'));};
  if(win.navigator&&win.navigator.onLine===false){fail();return card;}
  const script=doc.createElement('script');script.src=SCRIPTS[kind];script.async=true;script.type='text/javascript';
  // The embed script reads its own text as the widget config; external scripts never execute this text.
  script.textContent=JSON.stringify(config(kind,symbol,locale));
  script.addEventListener('error',fail,{once:true});
  frame.append(script);
  return card;
 }
 function mountSettings(host,{locale,storage}={}){
  if(!host)return;const doc=host.ownerDocument,store=storage||doc.defaultView.localStorage,id='tradingview-widgets-enabled';
  const box=el(doc,'input',{type:'checkbox',id,'data-tv-setting':''});box.checked=enabled(store);
  const status=el(doc,'p',{class:'small',role:'status','data-tv-setting-status':''});
  box.addEventListener('change',()=>{status.textContent=setEnabled(store,box.checked)?'':(locale==='en-US'?'Could not save the setting on this device.':'이 기기에 설정을 저장할 수 없습니다.');});
  const label=el(doc,'label',{for:id});label.append(box,doc.createTextNode(' '+words(locale,'settings')));
  host.replaceChildren(el(doc,'h2',{},words(locale,'settings')),label,el(doc,'p',{class:'small'},words(locale,'settingsHelp')),el(doc,'p',{class:'small'},words(locale,'note')),status);
 }
 return Object.freeze({STORAGE_KEY,SCRIPTS,SYMBOLS,AVAILABILITY,symbolFor,availability,enabled,setEnabled,config,tickerSymbols,
  mountTickerTape:(host,o={})=>mount(host,{...o,kind:'ticker'}),mountMini:(host,o={})=>mount(host,{...o,kind:'mini'}),mountAdvanced:(host,o={})=>mount(host,{...o,kind:'advanced'}),mountSettings});
});
