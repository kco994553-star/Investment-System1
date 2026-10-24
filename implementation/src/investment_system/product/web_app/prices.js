/* P1 device prices (IS2.prices): Google Sheet / Worker prices, requested only on a user click and held in RAM only (never stored,
   logged or sent anywhere but the user's own Sheet and Worker). */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else(root.IS2=root.IS2||{}).prices=api.create({win:root});})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
// Stub until its P1 stage lands: screens can already see the module and must treat NOT_READY as "no data yet".
function create(){return Object.freeze({NOT_READY:true});}
return Object.freeze({create});
});
