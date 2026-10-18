/* Colour theme (light / dark / system), applied before first paint: this file is loaded synchronously in <head>, ahead of
   the stylesheets, so a dark device never flashes the light theme. The choice lives on this device only
   (localStorage 'investment.web.v1.theme', try/catch: unavailable storage falls back to 'system'). No geolocation, no
   clock or sunrise rule, no request. Presentation only: data, calculations and other settings are untouched.
   The chart colour convention (owner design 2026-10-18) lives here too, for the same reason (no flash): 'kr' (default:
   rising candle red, falling blue) or 'us' (rising green, falling red), localStorage 'investment.web.v1.candle-style',
   shown as <html data-candles>; theme.css maps it to --up / --down. */
(function(root){
 'use strict';
 const KEY='investment.web.v1.theme',CHOICES=Object.freeze(['light','dark','system']),doc=root.document.documentElement;
 let mq=null;try{mq=root.matchMedia('(prefers-color-scheme: dark)');}catch(_){mq=null;}
 function read(){try{const v=root.localStorage.getItem(KEY);return CHOICES.includes(v)?v:'system';}catch(_){return 'system';}}
 let choice=read();
 const resolve=c=>c==='system'?(mq&&mq.matches?'dark':'light'):c;
 function apply(){const t=resolve(choice);doc.dataset.theme=t;doc.dataset.themePref=choice;doc.style.colorScheme=t;
  const meta=root.document.querySelector('meta[name="theme-color"]');if(meta)meta.setAttribute('content',t==='dark'?'#1f2a26':'#ffffff');}
 const listeners=new Set();
 function notify(){for(const fn of listeners){try{fn(resolve(choice),choice);}catch(_){}}}
 function set(next){if(!CHOICES.includes(next))return false;choice=next;let stored=true;try{root.localStorage.setItem(KEY,next);}catch(_){stored=false;}apply();notify();return stored;}
 apply();
 if(mq){const onChange=()=>{if(choice==='system'){apply();notify();}};if(mq.addEventListener)mq.addEventListener('change',onChange);else if(mq.addListener)mq.addListener(onChange);}
 // Another tab changed the choice: follow it.
 const CANDLE_KEY='investment.web.v1.candle-style',CANDLES=Object.freeze(['kr','us']);
 function readCandles(){try{const v=root.localStorage.getItem(CANDLE_KEY);return CANDLES.includes(v)?v:'kr';}catch(_){return 'kr';}}
 let candles=readCandles();doc.dataset.candles=candles;
 function setCandles(next){if(!CANDLES.includes(next))return false;candles=next;doc.dataset.candles=next;let stored=true;try{root.localStorage.setItem(CANDLE_KEY,next);}catch(_){stored=false;}notify();return stored;}
 root.addEventListener('storage',e=>{if(e.key===KEY){choice=read();apply();notify();}else if(e.key===CANDLE_KEY){candles=readCandles();doc.dataset.candles=candles;notify();}});
 root.AppTheme=Object.freeze({KEY,CHOICES,CANDLE_KEY,CANDLES,choice:()=>choice,resolved:()=>resolve(choice),set,candles:()=>candles,setCandles,subscribe:fn=>{listeners.add(fn);return()=>listeners.delete(fn);}});
})(window);
