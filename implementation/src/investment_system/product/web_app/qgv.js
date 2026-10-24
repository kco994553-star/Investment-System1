/* P1 score accessor (IS2.qgv): the single QGV v2 page result every screen shares, with its V source (device V is labelled
   as the temporary V until a central V is published). */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else(root.IS2=root.IS2||{}).qgv=api.create({win:root});})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
// Stub until its P1 stage lands: screens can already see the module and must treat NOT_READY as "no data yet".
function create(){return Object.freeze({NOT_READY:true});}
return Object.freeze({create});
});
