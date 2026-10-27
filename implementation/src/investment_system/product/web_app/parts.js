/* Draft parts shared by every screen: screen head (back link, title, one-line purpose), stamped section, sketch card, and the
   "연결 전" block a section shows until its lane wires real data. A pending block never shows a number (the draft's numbers are
   examples only; owner rule: real public data, device RAM values, or NA with its reason). */
(function(){
'use strict';
const{h,href,register,icon}=window.IS2;
function head(no,title,lead,{back=true}={}){
 return h('div',{class:'screen-head'},back?h('a',{class:'crumb',href:href('search')},'← 검색'):null,
  h('h1',null,no?no+'. ':'',title),lead?h('p',{class:'hand',dataset:{lead:''}},lead):null);}
function section(id,stampText,color,...children){
 return h('section',{class:'screen',dataset:{section:id},'aria-labelledby':'s-'+id},
  h('div',null,h('h2',{id:'s-'+id,class:'stamp'+(color?' '+color:'')},stampText)),...children);}
function card(title,{shadow=null,id=null,link=null}={},...children){
 const attrs={class:'sk card'+(shadow?' shadow-'+shadow:''),dataset:id?{card:id}:{}};
 const inner=[h('h3',{class:'card-title'},title),...children];
 return link?h('a',{...attrs,href:link},...inner):h('div',attrs,...inner);}
function pending(what){return h('p',{class:'pending',dataset:{pending:''}},'연결 전 · ',what);}
function more(text,link){return link?h('a',{class:'more',href:link},'→ ',text):h('span',{class:'more'},'→ ',text);}
/* The shared company search box (DC-23): its first-paint half. search-part-live.js (IS2.searchPart.attach) takes it over once
   IS2.ready resolved; until then typing opens the list with 불러오는 중, Escape closes it and keeps the text, and a submit is
   kept for the search part (it runs once the company list is there; no request, no guess). id names the input; the list is id-list, the options id-opt-N. Mobile keyboards: search key. */
function searchBox(id,label){
 const input=h('input',{id,type:'search',autocomplete:'off',autocorrect:'off',autocapitalize:'characters',spellcheck:'false',inputmode:'search',enterkeyhint:'search',
  placeholder:'티커 · 영문 회사명',role:'combobox','aria-expanded':'false','aria-controls':id+'-list','aria-autocomplete':'list',dataset:{searchInput:''}});
 const list=h('ul',{id:id+'-list',class:'sk search-list',role:'listbox','aria-label':'찾은 기업',hidden:true,dataset:{searchList:''}});
 const status=h('p',{class:'sr-only',role:'status',dataset:{searchStatus:''}}),pre=new AbortController(),o={signal:pre.signal},b={input,list,status,pre,submit:null};
 const show=q=>{list.hidden=!q;input.setAttribute('aria-expanded',String(q));};
 const load=()=>{const q=!!input.value.trim();list.replaceChildren(...(q?[h('li',{class:'search-msg',role:'presentation',dataset:{searchState:'loading'}},'불러오는 중')]:[]));
  show(q);status.textContent=q?'검색 목록 불러오는 중':'';};
 input.addEventListener('input',load,o);input.addEventListener('focus',load,o);
 input.addEventListener('keydown',e=>{if(e.key==='Escape'&&!list.hidden&&!e.isComposing){e.preventDefault();show(false);}},o);
 const go=e=>{e.preventDefault();if(b.submit)b.submit(e);else b.later=true;};
 const form=h('form',{class:'sk search-box',role:'search',dataset:{searchForm:''},onsubmit:e=>e.preventDefault()},
  icon(['M13 4 A9 9 0 1 1 12.99 4','M20 20 L27 27'],30),input,h('button',{class:'btn solid',type:'submit',onclick:go},'검색'));
 const A=b.anchor=h('div',{class:'search-anchor'},form,list);b.note=h('div',{class:'search-note-line'});
 A.addEventListener('focusout',()=>setTimeout(()=>{if(!A.contains(document.activeElement))show(false);}),o);
 b.node=h('div',{class:'search-wrap'},label,A,status,b.note);
 return b;}
window.IS2.parts=Object.freeze({head,section,card,pending,more,searchBox});
window.IS2.register=register;
})();
