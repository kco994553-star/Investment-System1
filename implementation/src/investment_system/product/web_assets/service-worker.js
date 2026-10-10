/* Offline shell only. No application documents, scripts, JSON data or API caching. */
'use strict';
const BASE=new URL(self.registration.scope),PREFIX='investment-static-shell:'+BASE.pathname+':',CACHE=PREFIX+'1';
const NAMES=['offline.html','style.css','manifest.json','icon-192.png','icon-512.png'];
const STATIC=new Set(NAMES.map(name=>new URL(name,BASE).href)),OFFLINE=new URL('offline.html',BASE).href;
self.addEventListener('install',event=>event.waitUntil((async()=>{
 const cache=await caches.open(CACHE);
 for(const url of STATIC){const request=new Request(url,{cache:'no-store',credentials:'omit',referrerPolicy:'no-referrer',redirect:'error'}),response=await fetch(request);if(!response.ok||response.type==='opaque')throw Error('SHELL_INSTALL_FAILED');await cache.put(url,response.clone());}
 await self.skipWaiting();
})()));
self.addEventListener('activate',event=>event.waitUntil((async()=>{for(const name of await caches.keys())if(name.startsWith(PREFIX)&&name!==CACHE)await caches.delete(name);await self.clients.claim();})()));
self.addEventListener('fetch',event=>{
 const request=event.request,url=new URL(request.url);
 if(request.method!=='GET'||url.origin!==BASE.origin||!url.pathname.startsWith(BASE.pathname)||request.headers.has('Authorization'))return;
 if(request.mode==='navigate'){
  event.respondWith((async()=>{try{return await fetch(request);}catch(_){return (await caches.open(CACHE)).match(OFFLINE);}})());return;
 }
 if(!STATIC.has(url.href))return;
 event.respondWith((async()=>{const cache=await caches.open(CACHE);try{const response=await fetch(new Request(url.href,{cache:'no-store',credentials:'omit',referrerPolicy:'no-referrer',redirect:'error'}));if(response.ok&&response.type!=='opaque')await cache.put(url.href,response.clone());return response;}catch(_){return cache.match(url.href);}})());
});
