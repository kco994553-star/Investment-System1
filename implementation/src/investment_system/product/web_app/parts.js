/* Draft parts shared by every screen: screen head (back link, title, one-line purpose), stamped section, sketch card, and the
   "연결 전" block a section shows until its lane wires real data. A pending block never shows a number (the draft's numbers are
   examples only; owner rule: real public data, device RAM values, or NA with its reason). */
(function(){
'use strict';
const{h,href,register}=window.IS2;
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
window.IS2.parts=Object.freeze({head,section,card,pending,more});
window.IS2.register=register;
})();
