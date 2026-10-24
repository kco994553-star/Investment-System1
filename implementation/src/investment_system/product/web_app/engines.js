/* P1 engine wiring (IS2.engines): TARGET v1, playbook, virtual trading and macro lights, calling the old engines unchanged. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else(root.IS2=root.IS2||{}).engines=api.create({win:root});})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
// Stub until its P1 stage lands: screens can already see the module and must treat NOT_READY as "no data yet".
function create(){return Object.freeze({NOT_READY:true});}
return Object.freeze({create});
});
