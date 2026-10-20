/* One price-free device backup. Explicit user preferences, holdings and playbook records only. Prices and price series are excluded.
   /4 adds device playbook records; /1–/3 stay importable and preserve current playbook records. /3 adds investor stars.
   /5 = /4 plus the opt-in `user_objects` section (owner storage policy 2026-10-20 item 6): the user's chart notes/scenarios
   (chart-user-objects/1, user-drawn anchor coordinates only, validated by ChartWorkbench) and macro cycle user-estimate history
   (macro-cycle-user-estimate/2, validated by MacroCycleRing). Without the opt-in the export stays /4, byte-for-byte as before.
   Restoring a section merges into what this device holds (no duplicates, nothing removed); /1–/4 never touch those keys.
   A successful restore leaves a dismissible device-only marker (time + schema, no content) so ACTUAL/settings can say what to re-check. */
(function(root,factory){const api=factory(typeof module==='object'&&module.exports?require('./device-profiles.js'):root.DeviceProfiles,typeof module==='object'&&module.exports?require('./playbook-screen.js'):root.PlaybookScreen);if(typeof module==='object'&&module.exports)module.exports=api;else root.DeviceBackup=api;})(typeof globalThis!=='undefined'?globalThis:this,function(Profiles,Playbook){
 'use strict';
 const SCHEMA='investment-device-backup/4',USER_OBJECTS_SCHEMA='investment-device-backup/5',LEGACY=['investment-device-backup/1','investment-device-backup/2','investment-device-backup/3'],PERSONAL_KEY='investment.web.v1.personal',STAR_KEY='investment.web.v1.investor-stars',RESTORED_KEY='investment.web.v1.backup-restored',MAX_BYTES=16*1024*1024,MAX_STARS=50,CIK=/^\d{10}$/;
 function fail(){throw Error('BACKUP_INVALID');}
 function object(x){return x!==null&&typeof x==='object'&&!Array.isArray(x);}
 function exact(x,ks){if(!object(x)||Object.keys(x).length!==ks.length||ks.some(k=>!Object.hasOwn(x,k)))fail();}
 function text(x,max=128){return typeof x==='string'&&x.length>0&&x.length<=max&&!/[\x00-\x1f]/.test(x);}
 function preferences(p){
  exact(p,['version','interests','groups']);if(p.version!==1||!Array.isArray(p.interests)||p.interests.length>2000||p.interests.some(x=>!text(x))||!Array.isArray(p.groups)||p.groups.length>100)fail();
  const interests=[...new Set(p.interests)],ids=new Set();
  const groups=p.groups.map(g=>{exact(g,['id','name','members']);if(!text(g.id)||ids.has(g.id)||!text(g.name,60)||!g.name.trim()||!Array.isArray(g.members)||g.members.length>2000||g.members.some(x=>!text(x)||!interests.includes(x)))fail();ids.add(g.id);return {id:g.id,name:g.name,members:[...new Set(g.members)]};});
  return {version:1,interests,groups};
 }
 function stars(x){if(!Array.isArray(x)||x.length>MAX_STARS||x.some(c=>typeof c!=='string'||!CIK.test(c))||new Set(x).size!==x.length)fail();return [...x];}
 function storedStars(storage){let v=[];try{v=JSON.parse(storage.getItem(STAR_KEY)||'[]');}catch(_){v=[];}return Array.isArray(v)?[...new Set(v.filter(c=>typeof c==='string'&&CIK.test(c)))].slice(0,MAX_STARS):[];}
 function validateSize(payload){if(new TextEncoder().encode(JSON.stringify(payload,null,2)).length>MAX_BYTES)throw Error('BACKUP_TOO_LARGE');return payload;}
 function accepts(payload){return object(payload)&&(payload.schema===SCHEMA||payload.schema===USER_OBJECTS_SCHEMA||LEGACY.includes(payload.schema));}
 // The validators live with the screens that own the data; looked up when needed (browser globals, or require() under Node).
 function userModules(){
  const g=typeof globalThis!=='undefined'?globalThis:{};let cw=g.ChartWorkbench,mc=g.MacroCycleRing;
  if(typeof module==='object'&&module.exports){if(!cw)cw=require('./chart-workbench.js');if(!mc){require('./macro-cycle-ring.js');mc=g.MacroCycleRing;}}
  if(!cw||!mc||typeof cw.parseUserExport!=='function'||typeof mc.parseUserExport!=='function')throw Error('BACKUP_USER_OBJECTS_UNAVAILABLE');return {cw,mc};
 }
 function userObjects(x){
  exact(x,['chart','macro']);const {cw,mc}=userModules();
  let chart=null,macro=null;
  if(x.chart!==null){exact(x.chart,['schema','items']);try{chart={schema:cw.USER_SCHEMA,items:cw.parseUserExport(x.chart)};}catch(_){fail();}}
  if(x.macro!==null){exact(x.macro,['schema','rings']);try{macro=mc.parseUserExport(x.macro);}catch(_){fail();}}
  return {chart,macro};
 }
 function create(prefs,settings,portfolio,catalog,market,language,profiles=Profiles.empty(),investorStars=[],playbook=Playbook.empty(),userSection=null){
  const personal=preferences({version:prefs.version,interests:prefs.interests,groups:prefs.groups.map(g=>({id:g.id,name:g.name,members:g.members}))});
  const base={schema:SCHEMA,profiles:Profiles.validate(profiles),preferences:personal,settings:language.settings(settings),portfolio:portfolio===null?null:market.validateActual?market.validateActual(portfolio,catalog):market.importBackup(portfolio,catalog).snapshot,investor_stars:stars(investorStars),playbook:Playbook.validate(playbook)};
  return validateSize(userSection===null?base:{...base,schema:USER_OBJECTS_SCHEMA,user_objects:userObjects(userSection)});
 }
 function parse(payload,catalog,market,language){
  if(!accepts(payload))fail();const v1=payload.schema===LEGACY[0],v5=payload.schema===USER_OBJECTS_SCHEMA,v4=v5||payload.schema===SCHEMA,v3=v4||payload.schema===LEGACY[2];
  exact(payload,['schema','preferences','settings','portfolio',...(v1?[]:['profiles']),...(v3?['investor_stars']:[]),...(v4?['playbook']:[]),...(v5?['user_objects']:[])]);
  exact(payload.settings,['version','display_locale','source_language']);
  return create(preferences(payload.preferences),payload.settings,payload.portfolio,catalog,market,language,v1?Profiles.empty():Profiles.validate(payload.profiles),v3?stars(payload.investor_stars):[],v4?Playbook.validate(payload.playbook):Playbook.empty(),v5?payload.user_objects:null);
 }
 // options.userObjects (opt-in): add this device's chart notes/scenarios and macro estimate history, complete (nothing trimmed).
 function readUserObjects(storage){
  const {cw,mc}=userModules(),loaded=cw.createDeviceUserStore(storage).load();
  if(loaded.code==='STORAGE_UNAVAILABLE'||loaded.code==='STORE_INVALID')throw Error('BACKUP_USER_OBJECTS_UNREADABLE');
  let rings;try{rings=mc.readUserStore(storage).rings;}catch(_){throw Error('BACKUP_USER_OBJECTS_UNREADABLE');}
  return {chart:{schema:cw.USER_SCHEMA,items:loaded.items},macro:{schema:mc.USER_SCHEMA,rings}};
 }
 async function read(view,catalog,options={}){
  const raw=view.localStorage.getItem(PERSONAL_KEY),p=raw?JSON.parse(raw):{version:1,interests:[],groups:[]};
  const settings=view.AppLanguage.read(view.localStorage);if(!settings.writable)throw Error('BACKUP_SETTINGS_UNREADABLE');
  return create(p,settings.value,await view.DeviceActual.readHoldings(view,catalog),catalog,view.DeviceMarket,view.AppLanguage,Profiles.read(view.localStorage),storedStars(view.localStorage),Playbook.read(view.localStorage),options&&options.userObjects?readUserObjects(view.localStorage):null);
 }
 // Merge a restored user-objects section into this device (no duplicates; nothing already stored is removed).
 function mergeUserObjects(storage,section){
  const {cw,mc}=userModules();
  if(section.chart){const store=cw.createDeviceUserStore(storage),cur=store.load();if(cur.code==='STORAGE_UNAVAILABLE'||cur.code==='STORE_INVALID')throw Error('BACKUP_USER_OBJECTS_UNREADABLE');
   const m=cw.mergeUserItems(cur.items,section.chart.items);if(m.added&&!store.save(m.items))throw Error('BACKUP_USER_OBJECTS_WRITE_FAILED');}
  if(section.macro)mc.importUserHistory(section.macro,storage);
 }
 function download(view,payload,name='investment-personal.json'){
  validateSize(payload);const url=view.URL.createObjectURL(new view.Blob([JSON.stringify(payload,null,2)],{type:'application/json'})),a=view.document.createElement('a');a.href=url;a.download=name;a.click();view.setTimeout(()=>view.URL.revokeObjectURL(url),1000);
 }
 async function restore(view,catalog,payload){
  const next=parse(payload,catalog,view.DeviceMarket,view.AppLanguage),withUser=payload.schema===USER_OBJECTS_SCHEMA,withPlaybook=withUser||payload.schema===SCHEMA,withStars=withPlaybook||payload.schema===LEGACY[2];
  const user=withUser?next.user_objects:null,mods=user?userModules():null;
  const keys=[PERSONAL_KEY,view.AppLanguage.KEY,Profiles.KEY,...(withStars?[STAR_KEY]:[]),...(withPlaybook?[Playbook.KEY]:[]),...(user&&user.chart?[mods.cw.USER_KEY]:[]),...(user&&user.macro?[mods.mc.USER_KEY]:[])],before=keys.map(k=>view.localStorage.getItem(k));
  try{
   view.localStorage.setItem(keys[0],JSON.stringify(next.preferences));view.AppLanguage.write(view.localStorage,next.settings);Profiles.write(view.localStorage,next.profiles);
   if(withStars)view.localStorage.setItem(STAR_KEY,JSON.stringify(next.investor_stars));
   if(withPlaybook)Playbook.write(view.localStorage,next.playbook);
   if(user)mergeUserObjects(view.localStorage,user);
   await view.DeviceActual.restoreHoldings(view,catalog,next.portfolio);
   try{view.localStorage.setItem(RESTORED_KEY,JSON.stringify({restored_at:new Date().toISOString(),schema:payload.schema}));}catch(_){}
  }catch(_){
   // Undo writes in reverse order: a smaller replacement may have funded a later
   // larger value, so restoring that original first can itself exceed the quota.
   try{keys.map((k,i)=>[k,before[i]]).reverse().forEach(([k,value])=>value===null?view.localStorage.removeItem(k):view.localStorage.setItem(k,value));}catch(_){throw Error('BACKUP_ROLLBACK_FAILED');}
   throw Error('BACKUP_RESTORE_FAILED');
  }
  return next;
 }
 function restoredNotice(storage){try{const v=JSON.parse(storage.getItem(RESTORED_KEY)||'null');if(!object(v)||typeof v.restored_at!=='string'||!Number.isFinite(Date.parse(v.restored_at))||!accepts({schema:v.schema}))return null;return {restored_at:v.restored_at,schema:v.schema};}catch(_){return null;}}
 function dismissRestored(storage){try{storage.removeItem(RESTORED_KEY);return true;}catch(_){return false;}}
 // Visible, dismissible notice: data came from a backup; quotes, sheet IDs, tokens and Worker address were not in it.
 function mountRestoredNotice(host,{locale='ko-KR',storage,onDismiss}={}){
  if(!host)return null;const notice=restoredNotice(storage);if(!notice){host.replaceChildren();return null;}
  const doc=host.ownerDocument,en=locale==='en-US',el=(tag,text,attrs={})=>{const n=doc.createElement(tag);if(text!==undefined)n.textContent=text;for(const[k,v]of Object.entries(attrs))n.setAttribute(k,v);return n;};
  const box=el('section',undefined,{class:'card banner','data-backup-restored':notice.schema,role:'status'}),button=el('button',en?'Dismiss':'확인·닫기',{type:'button','data-backup-restored-dismiss':''});
  box.append(el('strong',en?'Restored from backup · Re-read your sheet':'백업에서 복원됨 · 시트 다시 읽기 필요'),el('p',(en?'Restored at ':'복원 시각 ')+notice.restored_at+' · '+notice.schema,{class:'small'}),
   el('p',en?'Interests, groups, holdings, profiles, investor stars and language came from the backup. Quotes, Google sheet IDs, sign-in and the Worker address were not included: check Google sheet settings, then re-read quotes and Universe; review ACTUAL holdings.':'관심 기업·그룹·보유·프로필·투자자 ★·언어는 백업 내용입니다. 시세·Google 시트 ID·로그인·Worker 주소는 백업에 없습니다: 설정에서 Google 시트 연결을 확인하고 시세·Universe를 다시 읽은 뒤 ACTUAL 보유를 점검하세요.',{class:'small'}),button);
  button.addEventListener('click',()=>{dismissRestored(storage);host.replaceChildren();try{onDismiss?.();}catch(_){}});host.replaceChildren(box);return box;
 }
 return Object.freeze({MAX_BYTES,validateSize,SCHEMA,USER_OBJECTS_SCHEMA,userObjects,RESTORED_KEY,restoredNotice,dismissRestored,mountRestoredNotice,LEGACY_SCHEMAS:Object.freeze([...LEGACY]),STAR_KEY,MAX_STARS,accepts,preferences,stars,create,parse,read,download,restore});
});
