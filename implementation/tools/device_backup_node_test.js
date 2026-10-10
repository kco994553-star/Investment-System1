'use strict';
const assert=require('node:assert/strict'),path=require('node:path');
const dir='../src/investment_system/product/web_assets/';
const B=require(dir+'device-backup.js'),M=require(dir+'device-market.js'),L=require(dir+'locale.js');
let pass=0,fail=0;
function test(name,f){try{f();pass++;console.log('PASS '+name);}catch(_){fail++;console.log('FAIL '+name);}}
const prefs={version:1,interests:['synthetic-issuer'],groups:[{id:'synthetic-group',name:'Synthetic group',members:['synthetic-issuer']}]};
test('combined empty portfolio backup preserves preferences groups and language',()=>{
 const b=B.create(prefs,{version:1,display_locale:'en-US',source_language:'ko'},null,null,M,L);
 assert.deepEqual(B.parse(JSON.parse(JSON.stringify(b)),null,M,L),b);assert.equal(b.preferences.groups[0].members[0],prefs.interests[0]);assert.equal(b.settings.display_locale,'en-US');assert.equal(b.portfolio,null);
});
test('export allowlist excludes private settings and extra preference keys',()=>{
 const b=B.create({...prefs,workerOrigin:'private',token:'private'},{version:1,display_locale:'ko-KR',source_language:'all',workerOrigin:'private',spreadsheetId:'private'},null,null,M,L);
 assert.deepEqual(Object.keys(b).sort(),['portfolio','preferences','profiles','schema','settings']);assert.deepEqual(Object.keys(b.settings).sort(),['display_locale','source_language','version']);assert.ok(!JSON.stringify(b).includes('private'));
});
test('backup rejects unknown fields and invalid group memberships',()=>{
 const b=B.create(prefs,L.settings(),null,null,M,L);
 assert.throws(()=>B.parse({...b,token:'private'},null,M,L));assert.throws(()=>B.parse({...b,settings:{...b.settings,workerOrigin:'private'}},null,M,L));assert.throws(()=>B.preferences({...prefs,groups:[{...prefs.groups[0],members:['not-an-interest']}]}));
});
test('clones caller arrays before exporting',()=>{const b=B.create(prefs,L.settings(),null,null,M,L);b.preferences.interests.push('other');assert.equal(prefs.interests.length,1);});
console.log('COUNTS pass='+pass+' fail='+fail);if(fail)process.exitCode=1;
