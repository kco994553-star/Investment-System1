/* P1 device storage (IS2.store): the old keys and schemas of this device's saved settings, read freely, written only inside a
   user action. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else(root.IS2=root.IS2||{}).store=api.create({win:root});})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
// Stub until its P1 stage lands: screens can already see the module and must treat NOT_READY as "no data yet".
function create(){return Object.freeze({NOT_READY:true});}
return Object.freeze({create});
});
