/* P1 action gate (IS2.action): every Sheet / Worker / OAuth request and every device-storage write runs inside a trusted user
   click, and only to the destinations that click's kind allows. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else(root.IS2=root.IS2||{}).action=api.create({win:root});})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
// Stub until its P1 stage lands: screens can already see the module and must treat NOT_READY as "no data yet".
function create(){return Object.freeze({NOT_READY:true});}
return Object.freeze({create});
});
