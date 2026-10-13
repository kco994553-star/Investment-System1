/* Company logos, loaded only at runtime and only for display. No logo file is stored in the repository or in Pages.
   Order per symbol: (a) logo.dev / Brandfetch, only with the key the user typed on this device; (b) the company-site
   favicon through one fixed favicon origin; (c) a colored circle with the ticker's first letter. With the switch off,
   no external request is made at all. Requests reveal which tickers are on screen (never quantities or values). */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.CompanyLogos=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
 'use strict';
 const KEYS=Object.freeze({display:'investment.web.v1.logo-display',provider:'investment.web.v1.logo-provider',key:'investment.web.v1.logo-key'});
 const PROVIDERS=Object.freeze(['none','logodev','brandfetch']);
 const ORIGINS=Object.freeze({logodev:'https://img.logo.dev',brandfetch:'https://cdn.brandfetch.io',favicon:'https://icons.duckduckgo.com'});
 const CATALOG_URL='universe-domains.json',COLORS=12,SIZES=[20,40];
 const KEY_PATTERN=/^[A-Za-z0-9_-]{8,128}$/,DOMAIN=/^(?=.{4,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$/,CODE=/^(?:NASDAQ|NYSE|BATS|KRX|TYO):[A-Z0-9.]{1,16}$/;
 // TARGET company ids whose ticker differs from the id (same ids as the private history Worker allowlist).
 const ID_CODES=Object.freeze({stry:'NYSE:SYK',hanmi:'KRX:042700',tokyo_electron:'TYO:8035'});
 let catalogPromise=null,catalog=null,observer=null;
 function read(storage,key){try{return storage.getItem(key);}catch(_){return null;}}
 function write(storage,key,value){try{if(value===null)storage.removeItem(key);else storage.setItem(key,value);return true;}catch(_){return false;}}
 function settings(storage){
  const provider=read(storage,KEYS.provider),key=read(storage,KEYS.key);
  return {enabled:read(storage,KEYS.display)!=='off',provider:PROVIDERS.includes(provider)?provider:'none',key:typeof key==='string'&&KEY_PATTERN.test(key)?key:''};
 }
 function save(storage,{enabled,provider,key}){
  let ok=write(storage,KEYS.display,enabled===false?'off':null);
  const p=PROVIDERS.includes(provider)?provider:'none';ok=write(storage,KEYS.provider,p==='none'?null:p)&&ok;
  if(key!==undefined)ok=write(storage,KEYS.key,typeof key==='string'&&KEY_PATTERN.test(key)?key:null)&&ok;
  return ok;
 }
 function hash(text){let h=0x811c9dc5;for(let i=0;i<text.length;i++){h^=text.charCodeAt(i);h=Math.imul(h,0x01000193)>>>0;}return h>>>0;}
 function tickerOf(value){
  const s=String(value||'').trim();if(!s)return '';
  if(Object.hasOwn(ID_CODES,s))return ID_CODES[s].split(':')[1];
  const code=s.includes(':')?s.split(':')[1]:s;return code.replace(/\.(KS|KQ|T)$/,'').toUpperCase();
 }
 function letter(value){const t=tickerOf(value),m=t.match(/[A-Z0-9]/);return m?m[0]:'?';}
 function colorIndex(value){return hash(tickerOf(value)||'?')%COLORS;}
 function codeCandidates(value){
  const s=String(value||'').trim();if(!s)return [];
  if(Object.hasOwn(ID_CODES,s))return [ID_CODES[s]];
  if(CODE.test(s))return [s];
  const t=s.toUpperCase().replace(/-/g,'.');
  if(/^\d{6}(\.(KS|KQ))?$/.test(t))return ['KRX:'+t.slice(0,6)];
  if(/^\d{4}(\.T)?$/.test(t))return ['TYO:'+t.slice(0,4)];
  return ['NASDAQ:'+t,'NYSE:'+t,'BATS:'+t];
 }
 function parseCatalog(value){
  const map=new Map();
  if(!value||typeof value!=='object'||Array.isArray(value)||Object.keys(value).sort().join(',')!=='rows,schema'||value.schema!=='universe-domains/1'||!Array.isArray(value.rows)||value.rows.length>2048)return map;
  for(const row of value.rows){if(Array.isArray(row)&&row.length===3&&typeof row[0]==='string'&&CODE.test(row[0])&&typeof row[1]==='string'&&DOMAIN.test(row[1]))map.set(row[0],row[1]);}
  return map;
 }
 function loadCatalog(win){
  if(!catalogPromise)catalogPromise=(async()=>{try{const r=await win.fetch(CATALOG_URL,{credentials:'omit',cache:'no-store'});catalog=r.ok?parseCatalog(await r.json()):new Map();}catch(_){catalog=new Map();}return catalog;})();
  return catalogPromise;
 }
 function domainFor(value,map=catalog){if(!map)return null;for(const c of codeCandidates(value))if(map.has(c))return map.get(c);return null;}
 function sources(domain,config){
  const out=[],d=encodeURIComponent(domain);
  if(config.key&&config.provider==='logodev')out.push({kind:'logodev',url:ORIGINS.logodev+'/'+d+'?'+new URLSearchParams([['token',config.key],['size','64'],['format','png']]),referrer:'no-referrer'});
  if(config.key&&config.provider==='brandfetch')out.push({kind:'brandfetch',url:ORIGINS.brandfetch+'/'+d+'?c='+encodeURIComponent(config.key),referrer:null});
  out.push({kind:'favicon',url:ORIGINS.favicon+'/ip3/'+d+'.ico',referrer:'no-referrer'});
  return out;
 }
 const esc=v=>String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 function size(n){return SIZES.includes(n)?n:20;}
 // Placeholder only: the letter is drawn by CSS (attr(data-letter)), so the row text is unchanged.
 function html(value,px=20){return '<span class="co-logo co-logo-'+size(px)+' co-logo-c'+colorIndex(value)+'" data-logo-key="'+esc(String(value||''))+'" data-letter="'+esc(letter(value))+'" aria-hidden="true"></span>';}
 function node(doc,value,px=20){const t=doc.createElement('template');t.innerHTML=html(value,px);return t.content.firstChild;}
 function showLetter(span){span.querySelectorAll('img').forEach(i=>i.remove());span.dataset.logoState='letter';span.removeAttribute('data-logo-source');}
 function tryNext(span,list,index,px){
  if(!span.isConnected)return;
  if(index>=list.length){showLetter(span);return;}
  const doc=span.ownerDocument,img=doc.createElement('img'),source=list[index];
  img.alt='';img.width=px;img.height=px;img.loading='lazy';img.decoding='async';img.className='co-logo-img';
  if(source.referrer)img.referrerPolicy=source.referrer;
  img.addEventListener('load',()=>{if(!span.isConnected)return;span.dataset.logoState='img';span.dataset.logoSource=source.kind;},{once:true});
  img.addEventListener('error',()=>{img.remove();tryNext(span,list,index+1,px);},{once:true});
  span.querySelectorAll('img').forEach(i=>i.remove());span.dataset.logoState='loading';span.append(img);img.src=source.url;
 }
 function hydrate(rootNode,{win,storage}={}){
  const doc=rootNode.ownerDocument||rootNode,view=win||doc.defaultView,store=storage||view.localStorage,config=settings(store);
  const spans=[...rootNode.querySelectorAll('.co-logo[data-logo-key]:not([data-logo-state])')];
  if(!spans.length)return Promise.resolve(0);
  for(const s of spans)s.dataset.logoState='pending';
  if(!config.enabled){spans.forEach(showLetter);return Promise.resolve(spans.length);}
  return loadCatalog(view).then(map=>{for(const s of spans){if(!s.isConnected||s.dataset.logoState!=='pending')continue;const domain=domainFor(s.dataset.logoKey,map),px=s.classList.contains('co-logo-40')?40:20;if(!domain){showLetter(s);continue;}tryNext(s,sources(domain,config),0,px);}return spans.length;});
 }
 function reset(rootNode){for(const s of rootNode.querySelectorAll('.co-logo[data-logo-key]')){s.querySelectorAll('img').forEach(i=>i.remove());s.removeAttribute('data-logo-state');s.removeAttribute('data-logo-source');}}
 function attribution(doc,store){
  const footer=doc.querySelector('footer'),config=settings(store),existing=doc.querySelector('[data-logo-attribution="footer"]');
  const want=config.enabled&&config.provider==='logodev'&&config.key;
  if(!want){if(existing)existing.remove();return;}
  if(existing||!footer)return;
  const p=doc.createElement('p'),a=doc.createElement('a');p.className='small';p.dataset.logoAttribution='footer';a.href='https://logo.dev';a.rel='noopener noreferrer';a.target='_blank';a.textContent='Logos provided by Logo.dev';p.append(a);footer.append(p);
 }
 function start(win){
  const doc=win.document,store=win.localStorage;
  if(observer)observer.disconnect();
  let queued=false;const run=()=>{queued=false;void hydrate(doc.body,{win});};
  observer=new win.MutationObserver(()=>{if(!queued){queued=true;win.queueMicrotask(run);}});
  observer.observe(doc.body,{childList:true,subtree:true});
  attribution(doc,store);run();
 }
 function refresh(win){const doc=win.document;reset(doc.body);attribution(doc,win.localStorage);return hydrate(doc.body,{win});}
 function mountSettings(host,{locale,win}={}){
  if(!host)return;const doc=host.ownerDocument,view=win||doc.defaultView,store=view.localStorage,T=(ko,en)=>locale==='en-US'?en:ko,config=settings(store);
  host.innerHTML='<h2>'+esc(T('로고 표시','Company logos'))+'</h2>'
   +'<label><input type="checkbox" id="logo-display" data-logo-setting="display"'+(config.enabled?' checked':'')+'> '+esc(T('로고 표시','Show logos'))+'</label>'
   +'<label for="logo-provider">'+esc(T('로고 서비스','Logo service'))+'</label><select id="logo-provider" data-logo-setting="provider">'
   +[['none',T('없음','None')],['logodev','logo.dev'],['brandfetch','Brandfetch']].map(([v,l])=>'<option value="'+v+'"'+(config.provider===v?' selected':'')+'>'+esc(l)+'</option>').join('')+'</select>'
   +'<label for="logo-key">'+esc(T('서비스 키 (이 기기에만 저장)','Service key (saved on this device only)'))+'</label><input id="logo-key" data-logo-setting="key" type="password" autocomplete="off" spellcheck="false" maxlength="128" placeholder="'+esc(config.key?T('저장됨 · 바꾸려면 입력','Saved · type to replace'):T('logo.dev 공개 키 또는 Brandfetch client ID','logo.dev publishable key or Brandfetch client ID'))+'">'
   +'<button type="button" data-logo-action="save">'+esc(T('로고 설정 저장','Save logo settings'))+'</button> <button type="button" data-logo-action="clear-key">'+esc(T('키 지우기','Clear key'))+'</button>'
   +'<p class="small" role="status" data-logo-status></p>'
   +'<p class="small">'+esc(T('순서: 선택한 서비스(키 있을 때) → 회사 사이트 파비콘(DuckDuckGo) → 첫 글자 원. 끄면 외부 요청 없이 첫 글자 원만 표시합니다.','Order: chosen service (with a key) → company-site favicon (DuckDuckGo) → first-letter circle. Off: no external request, letter circles only.'))+'</p>'
   +'<p class="small" data-logo-privacy>'+esc(T('로고·파비콘 요청은 화면에 보이는 종목(보유 종목 행 포함)을 해당 서비스에 알려 줍니다. 수량·금액은 보내지 않습니다. 키는 저장소·Pages·로그·백업에 넣지 않습니다.','Logo and favicon requests tell the service which tickers are on screen (holdings rows included). No quantity or amount is sent. The key never goes into the repository, Pages, logs or backups.'))+'</p>'
   +(config.provider==='logodev'?'<p class="small" data-logo-attribution="settings"><a href="https://logo.dev" rel="noopener noreferrer" target="_blank">Logos provided by Logo.dev</a></p>':'');
  const status=host.querySelector('[data-logo-status]'),keyInput=host.querySelector('#logo-key');
  const apply=key=>{const typed=keyInput.value.trim();if(typed&&!KEY_PATTERN.test(typed)){status.textContent=T('키 형식이 올바르지 않습니다.','The key format is not valid.');return;}
   const ok=save(store,{enabled:host.querySelector('#logo-display').checked,provider:host.querySelector('#logo-provider').value,key:key!==undefined?key:(typed||undefined)});
   keyInput.value='';mountSettings(host,{locale,win:view});host.querySelector('[data-logo-status]').textContent=ok?T('저장했습니다.','Saved.'):T('이 기기에 설정을 저장할 수 없습니다.','Could not save the setting on this device.');void refresh(view);};
  host.querySelector('[data-logo-action="save"]').addEventListener('click',()=>apply());
  host.querySelector('[data-logo-action="clear-key"]').addEventListener('click',()=>apply(null));
  host.querySelector('#logo-display').addEventListener('change',()=>apply());
 }
 return Object.freeze({KEYS,ORIGINS,PROVIDERS,CATALOG_URL,settings,save,hash,letter,colorIndex,tickerOf,codeCandidates,parseCatalog,domainFor,sources,html,node,hydrate,reset,refresh,start,mountSettings,
  _resetCatalog(){catalogPromise=null;catalog=null;}});
});
