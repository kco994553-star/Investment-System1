/* Device-side `share_class_groups/v0` (V0_UNCALIBRATED, editable). User decision 2026-10-11: listed classes of one issuer with the same per-share economic rights (voting may differ) are summed and ranked once; everything else multi-class stays excluded. Python copy: universe/share_class_groups.py (equality-tested). No prices, shares or ranks here. */
(function(root,factory){const api=factory(typeof module==='object'&&module.exports?require('./private-subset.js'):root.PrivateSubset);if(typeof module==='object'&&module.exports)module.exports=api;else root.ShareClassGroups=api;})(typeof globalThis!=='undefined'?globalThis:this,function(core){
 'use strict';
 const deep=x=>{if(x&&typeof x==='object'){Object.values(x).forEach(deep);Object.freeze(x);}return x;};
 /* Keyed by SEC CIK and exact Universe504 codes. Conversion ratio != 1 (e.g. BRK.A/BRK.B) is never listed. cover_class_count = classes the filing cover must report; an unlisted cover class (Alphabet Class B) is not priced and not included. */
 const CONFIG=deep(core.validateShareClassGroups({
  config_version:'share_class_groups/v0',
  config_status:'V0_UNCALIBRATED',
  decision:'USER_DECISION_2026_10_11_SUM_ECONOMICALLY_IDENTICAL_CLASSES',
  basis:'SAME_PER_SHARE_ECONOMIC_RIGHTS_VOTING_MAY_DIFFER',
  groups:[
   {group_id:'alphabet',cik:'0001652044',codes:['NASDAQ:GOOGL','NASDAQ:GOOG'],cover_class_count:3},
   {group_id:'fox',cik:'0001754301',codes:['NASDAQ:FOXA','NASDAQ:FOX'],cover_class_count:2},
   {group_id:'news_corp',cik:'0001564708',codes:['NASDAQ:NWSA','NASDAQ:NWS'],cover_class_count:2}
  ]
 }));
 const LABEL_KO='경제적 동일 종류 합산 · v0',LABEL_EN='Economically identical classes summed · v0';
 return Object.freeze({CONFIG,LABEL_KO,LABEL_EN});
});
