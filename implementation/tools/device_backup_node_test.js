'use strict';
const assert=require('node:assert/strict'),path=require('node:path');
const dir='../src/investment_system/product/web_assets/';
const B=require(dir+'device-backup.js'),M=require(dir+'device-market.js'),L=require(dir+'locale.js'),P=require(dir+'device-profiles.js'),S=require(dir+'public-screens.js');
let pass=0,fail=0;const queue=[];
function test(name,f){queue.push([name,f]);}
const prefs={version:1,interests:['synthetic-issuer'],groups:[{id:'synthetic-group',name:'Synthetic group',members:['synthetic-issuer']}]};
const STARS=['0000000001','0000000002'];
function strip(b,...keys){const x={...b};for(const k of keys)delete x[k];return x;}
function legacy(b,schema){return schema==='investment-device-backup/1'?{...strip(b,'profiles','investor_stars'),schema}:{...strip(b,'investor_stars'),schema};}
function view(initial={}){
 const map=new Map(Object.entries(initial)),calls={restore:0};
 const localStorage={getItem:k=>map.has(k)?map.get(k):null,setItem:(k,v)=>{map.set(k,String(v));},removeItem:k=>{map.delete(k);}};
 return {map,calls,localStorage,AppLanguage:L,DeviceMarket:M,DeviceActual:{readHoldings:async()=>null,restoreHoldings:async()=>{calls.restore++;}}};
}
test('combined empty portfolio backup preserves preferences groups and language',()=>{
 const b=B.create(prefs,{version:1,display_locale:'en-US',source_language:'ko'},null,null,M,L);
 assert.deepEqual(B.parse(JSON.parse(JSON.stringify(b)),null,M,L),b);assert.equal(b.preferences.groups[0].members[0],prefs.interests[0]);assert.equal(b.settings.display_locale,'en-US');assert.equal(b.portfolio,null);
});
test('export allowlist excludes private settings and extra preference keys',()=>{
 const b=B.create({...prefs,workerOrigin:'private',token:'private'},{version:1,display_locale:'ko-KR',source_language:'all',workerOrigin:'private',spreadsheetId:'private'},null,null,M,L,P.empty(),STARS);
 assert.deepEqual(Object.keys(b).sort(),['investor_stars','portfolio','preferences','profiles','schema','settings']);assert.deepEqual(Object.keys(b.settings).sort(),['display_locale','source_language','version']);assert.ok(!JSON.stringify(b).includes('private'));
});
test('backup rejects unknown fields and invalid group memberships',()=>{
 const b=B.create(prefs,L.settings(),null,null,M,L);
 assert.throws(()=>B.parse({...b,token:'private'},null,M,L));assert.throws(()=>B.parse({...b,settings:{...b.settings,workerOrigin:'private'}},null,M,L));assert.throws(()=>B.preferences({...prefs,groups:[{...prefs.groups[0],members:['not-an-interest']}]}));
});
test('clones caller arrays before exporting',()=>{const stars=[...STARS],b=B.create(prefs,L.settings(),null,null,M,L,P.empty(),stars);b.preferences.interests.push('other');b.investor_stars.push('0000000003');assert.equal(prefs.interests.length,1);assert.equal(stars.length,2);});
test('schema 3 round-trips investor stars and shares the 13F star key',()=>{
 const b=B.create(prefs,L.settings(),null,null,M,L,P.empty(),STARS);
 assert.equal(b.schema,'investment-device-backup/3');assert.equal(B.SCHEMA,'investment-device-backup/3');assert.equal(B.STAR_KEY,S.STAR_KEY);
 assert.deepEqual(B.parse(JSON.parse(JSON.stringify(b)),null,M,L),b);assert.deepEqual(b.investor_stars,STARS);
 const full=Array.from({length:50},(_,i)=>String(i+1).padStart(10,'0'));assert.deepEqual(B.parse({...b,investor_stars:full},null,M,L).investor_stars,full);
});
test('schema 2 and 1 imports stay accepted with an empty star list',()=>{
 const b=B.create(prefs,{version:1,display_locale:'en-US',source_language:'ko'},null,null,M,L,P.empty(),STARS);
 for(const schema of ['investment-device-backup/2','investment-device-backup/1']){
  const old=legacy(b,schema),p=B.parse(old,null,M,L);assert.ok(B.accepts(old));
  assert.equal(p.schema,B.SCHEMA);assert.deepEqual(p.investor_stars,[]);assert.deepEqual(p.preferences,b.preferences);assert.deepEqual(p.settings,b.settings);
  assert.throws(()=>B.parse({...old,investor_stars:STARS},null,M,L));
 }
 assert.ok(!B.accepts({schema:'investment-device-backup/4'}));assert.ok(!B.accepts(null));assert.throws(()=>B.parse({...b,schema:'investment-device-backup/4'},null,M,L));assert.throws(()=>B.parse(null,null,M,L));
});
test('invalid investor stars are rejected',()=>{
 const b=B.create(prefs,L.settings(),null,null,M,L,P.empty(),STARS);
 const bad=[undefined,null,'0000000001',{0:'0000000001'},['000000001'],['00000000011'],['abcdefghij'],[1],[1234567890],['0000000001','0000000001'],[' 0000000001'],['0000000001\n'],Array.from({length:51},(_,i)=>String(i+1).padStart(10,'0'))];
 for(const x of bad)assert.throws(()=>B.parse({...b,investor_stars:x},null,M,L),/BACKUP_INVALID/);
 assert.throws(()=>B.parse(strip(b,'investor_stars'),null,M,L),/BACKUP_INVALID/);
 assert.throws(()=>B.create(prefs,L.settings(),null,null,M,L,P.empty(),['0000000001','0000000001']),/BACKUP_INVALID/);
});
test('read exports normalized stored stars without secrets or sheet ids',async()=>{
 const v=view({[B.STAR_KEY]:JSON.stringify(['0000000009','bad','0000000009',7,'0000000008']),[L.KEY]:JSON.stringify({version:1,display_locale:'en-US',source_language:'ko',spreadsheetId:'private-sheet',token:'private-token'}),
  'investment.web.v1.personal':JSON.stringify(prefs),'investment.web.v1.google-sheet':JSON.stringify({spreadsheetId:'private-sheet'}),'investment.web.v1.worker':'https://private.example'});
 const b=await B.read(v,null);assert.deepEqual(b.investor_stars,['0000000009','0000000008']);assert.ok(!/private/.test(JSON.stringify(b)));
 const broken=view({[B.STAR_KEY]:'{not json'});assert.deepEqual((await B.read(broken,null)).investor_stars,[]);
});
test('restore writes stars for schema 3 and leaves them for legacy imports',async()=>{
 const b=B.create(prefs,L.settings(),null,null,M,L,P.empty(),STARS),before=JSON.stringify(['0000000077']);
 const v3=view({[B.STAR_KEY]:before});await B.restore(v3,null,JSON.parse(JSON.stringify(b)));assert.equal(v3.map.get(B.STAR_KEY),JSON.stringify(STARS));
 const empty=view({[B.STAR_KEY]:before});await B.restore(empty,null,{...b,investor_stars:[]});assert.equal(empty.map.get(B.STAR_KEY),'[]');
 for(const schema of ['investment-device-backup/2','investment-device-backup/1']){
  const kept=view({[B.STAR_KEY]:before});await B.restore(kept,null,legacy(b,schema));assert.equal(kept.map.get(B.STAR_KEY),before);
  const none=view();await B.restore(none,null,legacy(b,schema));assert.ok(!none.map.has(B.STAR_KEY));
 }
 const bad=view({[B.STAR_KEY]:before});await assert.rejects(B.restore(bad,null,{...b,investor_stars:['bad']}));assert.equal(bad.map.get(B.STAR_KEY),before);
});
test('failed restore rolls back investor stars',async()=>{
 const b=B.create(prefs,L.settings(),null,null,M,L,P.empty(),STARS);
 for(const initial of [{[B.STAR_KEY]:JSON.stringify(['0000000077'])},{}]){
  const v=view(initial);v.DeviceActual.restoreHoldings=async()=>{throw Error('STORAGE');};
  await assert.rejects(B.restore(v,null,b),/BACKUP_RESTORE_FAILED/);assert.equal(v.map.get(B.STAR_KEY),initial[B.STAR_KEY]);assert.equal(v.map.has('investment.web.v1.personal'),false);
 }
});
(async()=>{
 for(const [name,f] of queue){try{await f();pass++;console.log('PASS '+name);}catch(_){fail++;console.log('FAIL '+name);}}
 console.log('COUNTS pass='+pass+' fail='+fail);if(fail)process.exitCode=1;
})();
