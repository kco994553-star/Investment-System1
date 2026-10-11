/* Device-side `share_class_groups/v0` (V0_UNCALIBRATED, editable). User decision 2026-10-11: listed classes of one issuer with the same per-share economic rights (voting may differ) are summed and ranked once; everything else multi-class stays excluded. Unlisted cover class (Alphabet Class B, 1:1 convertible) is included at the `unlisted.valued_at` class price (decision 2026-10-11). Python copy: universe/share_class_groups.py (equality-tested). No prices, shares or ranks here. */
(function(root,factory){const api=factory(typeof module==='object'&&module.exports?require('./private-subset.js'):root.PrivateSubset);if(typeof module==='object'&&module.exports)module.exports=api;else root.ShareClassGroups=api;})(typeof globalThis!=='undefined'?globalThis:this,function(core){
 'use strict';
 const deep=x=>{if(x&&typeof x==='object'){Object.values(x).forEach(deep);Object.freeze(x);}return x;};
 /* Keyed by SEC CIK and exact Universe504 codes. Conversion ratio != 1 (e.g. BRK.A/BRK.B) is never listed. cover_class_count = classes the filing cover must report; an unlisted cover class (Alphabet Class B) is valued at the `unlisted.valued_at` listed class price, ratio 1, from the same cover's share count; missing/ambiguous count keeps the whole group NOT_AVAILABLE. `unlisted` is null exactly when every cover class is listed. */
 const CONFIG=deep(core.validateShareClassGroups({
  config_version:'share_class_groups/v0',
  config_status:'V0_UNCALIBRATED',
  decision:'USER_DECISION_2026_10_11_SUM_ECONOMICALLY_IDENTICAL_CLASSES',
  basis:'SAME_PER_SHARE_ECONOMIC_RIGHTS_VOTING_MAY_DIFFER',
  groups:[
   {group_id:'alphabet',cik:'0001652044',codes:['NASDAQ:GOOGL','NASDAQ:GOOG'],cover_class_count:3,unlisted:{valued_at:'NASDAQ:GOOGL',conversion_ratio:1,basis:core.UNLISTED_BASIS,decision:core.UNLISTED_DECISION}},
   {group_id:'fox',cik:'0001754301',codes:['NASDAQ:FOXA','NASDAQ:FOX'],cover_class_count:2,unlisted:null},
   {group_id:'news_corp',cik:'0001564708',codes:['NASDAQ:NWSA','NASDAQ:NWS'],cover_class_count:2,unlisted:null}
  ]
 }));
 const LABEL_KO='경제적 동일 종류 합산 · v0',LABEL_EN='Economically identical classes summed · v0';
 const UNLISTED_BASIS=core.UNLISTED_BASIS,UNLISTED_LABEL_KO='비상장 종류는 Class A 가격으로 평가 · 1:1 전환',UNLISTED_LABEL_EN='Unlisted class valued at Class A price · 1:1 convertible';
 const UNLISTED=Object.freeze(Object.fromEntries(CONFIG.groups.filter(g=>g.unlisted).map(g=>[g.group_id,g])));
 return Object.freeze({CONFIG,LABEL_KO,LABEL_EN,UNLISTED_BASIS,UNLISTED_LABEL_KO,UNLISTED_LABEL_EN,UNLISTED});
});
