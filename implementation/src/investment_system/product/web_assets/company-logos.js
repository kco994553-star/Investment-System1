/* Company logos: sanitized PNG images included in the Pages bundle at build time.
   Only same-origin JSON and bundled data images are read; missing logos use initials. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.CompanyLogos=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
 'use strict';
 const KEYS=Object.freeze({display:'investment.web.v1.logo-display'});
 const CATALOG_URL='company-logos.json',COLORS=12,SIZES=[20,40];
 const CODE=/^(?:NASDAQ|NYSE|BATS|KRX|TYO):[A-Z0-9.]{1,16}$/;
 const LOCAL_IMAGE=/^data:image\/png;base64,[A-Za-z0-9+/=]+$/;
 // TARGET company ids whose ticker differs from the id (same ids as the private history Worker allowlist).
 const ID_CODES=Object.freeze({stry:'NYSE:SYK',hanmi:'KRX:042700',tokyo_electron:'TYO:8035'});
 let catalogPromise=null,catalog=null,observer=null;
 function read(storage,key){try{return storage.getItem(key);}catch(_){return null;}}
 function write(storage,key,value){try{if(value===null)storage.removeItem(key);else storage.setItem(key,value);return true;}catch(_){return false;}}
 function settings(storage){return {enabled:read(storage,KEYS.display)!=='off'};}
 function save(storage,{enabled}){return write(storage,KEYS.display,enabled===false?'off':null);}
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
  if(!value||typeof value!=='object'||Array.isArray(value)||Object.keys(value).sort().join(',')!=='rows,schema'||value.schema!=='company-logos/1'||!Array.isArray(value.rows)||value.rows.length>2048)return map;
  for(const row of value.rows){if(Array.isArray(row)&&row.length===3&&typeof row[0]==='string'&&CODE.test(row[0])&&typeof row[1]==='string'&&LOCAL_IMAGE.test(row[1])&&row[1].length<=45000&&row[2]==='WIKIDATA')map.set(row[0],row[1]);}
  return map;
 }
 function loadCatalog(win){
  if(!catalogPromise)catalogPromise=(async()=>{try{const r=await win.fetch(CATALOG_URL,{credentials:'omit',cache:'no-store'});catalog=r.ok?parseCatalog(await r.json()):new Map();}catch(_){catalog=new Map();}return catalog;})();
  return catalogPromise;
 }
 function domainFor(value,map=catalog){if(!map)return null;for(const c of codeCandidates(value))if(map.has(c))return map.get(c);return null;}
 function sources(image){return LOCAL_IMAGE.test(image||'')?[{kind:'bundled',url:image,referrer:'no-referrer'}]:[];}
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
 function attribution(doc){const existing=doc.querySelector('[data-logo-attribution="footer"]');if(existing)existing.remove();}
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
  host.innerHTML='<h2>'+esc(T('로고 표시','Company logos'))+'</h2><label><input type="checkbox" id="logo-display" data-logo-setting="display"'+(config.enabled?' checked':'')+'> '+esc(T('로고 표시','Show logos'))+'</label><p class="small" data-logo-privacy>'+esc(T('빌드에 포함된 로고만 표시합니다. 로고 외부 요청 없이, 없는 종목은 이니셜을 표시합니다.','Only bundled logos are displayed. No external logo requests; missing logos use initials.'))+'</p><p role="status" data-logo-status></p>';
  host.querySelector('#logo-display').addEventListener('change',()=>{const ok=save(store,{enabled:host.querySelector('#logo-display').checked});host.querySelector('[data-logo-status]').textContent=ok?T('저장했습니다.','Saved.'):T('이 기기에 설정을 저장할 수 없습니다.','Could not save the setting on this device.');void refresh(view);});
 }
 return Object.freeze({KEYS,CATALOG_URL,settings,save,hash,letter,colorIndex,tickerOf,codeCandidates,parseCatalog,domainFor,sources,html,node,hydrate,reset,refresh,start,mountSettings,
  _resetCatalog(){catalogPromise=null;catalog=null;}});
});
