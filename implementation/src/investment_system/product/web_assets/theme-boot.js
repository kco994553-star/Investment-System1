/* Colour theme (light / dark / system), applied before first paint: this file is loaded synchronously in <head>, ahead of
   the stylesheets, so a dark device never flashes the light theme. The choice lives on this device only
   (localStorage 'investment.web.v1.theme', try/catch: unavailable storage falls back to 'system'). No geolocation, no
   clock or sunrise rule, no request. Presentation only: data, calculations and other settings are untouched. */
(function(root){
 'use strict';
 const KEY='investment.web.v1.theme',CHOICES=Object.freeze(['light','dark','system']),doc=root.document.documentElement;
 let mq=null;try{mq=root.matchMedia('(prefers-color-scheme: dark)');}catch(_){mq=null;}
 function read(){try{const v=root.localStorage.getItem(KEY);return CHOICES.includes(v)?v:'system';}catch(_){return 'system';}}
 let choice=read();
 const resolve=c=>c==='system'?(mq&&mq.matches?'dark':'light'):c;
 function apply(){const t=resolve(choice);doc.dataset.theme=t;doc.dataset.themeChoice=choice;doc.style.colorScheme=t;
  const meta=root.document.querySelector('meta[name="theme-color"]');if(meta)meta.setAttribute('content',t==='dark'?'#081633':'#f4f4ef');}
 const listeners=new Set();
 function notify(){for(const fn of listeners){try{fn(resolve(choice),choice);}catch(_){}}}
 function set(next){if(!CHOICES.includes(next))return false;choice=next;let stored=true;try{root.localStorage.setItem(KEY,next);}catch(_){stored=false;}apply();notify();return stored;}
 apply();
 if(mq){const onChange=()=>{if(choice==='system'){apply();notify();}};if(mq.addEventListener)mq.addEventListener('change',onChange);else if(mq.addListener)mq.addListener(onChange);}
 // Another tab changed the choice: follow it.
 root.addEventListener('storage',e=>{if(e.key===KEY){choice=read();apply();notify();}});
 root.AppTheme=Object.freeze({KEY,CHOICES,choice:()=>choice,resolved:()=>resolve(choice),set,subscribe:fn=>{listeners.add(fn);return()=>listeners.delete(fn);}});
})(window);
