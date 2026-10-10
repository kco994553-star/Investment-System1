/* One price-free device backup. Only explicit user preferences and holdings are allowed. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.DeviceBackup=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
 'use strict';
 const SCHEMA='investment-device-backup/1',PERSONAL_KEY='investment.web.v1.personal';
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
 function create(prefs,settings,portfolio,catalog,market,language){
  const personal=preferences({version:prefs.version,interests:prefs.interests,groups:prefs.groups.map(g=>({id:g.id,name:g.name,members:g.members}))});
  return {schema:SCHEMA,preferences:personal,settings:language.settings(settings),portfolio:portfolio===null?null:market.validateActual?market.validateActual(portfolio,catalog):market.importBackup(portfolio,catalog).snapshot};
 }
 function parse(payload,catalog,market,language){
  exact(payload,['schema','preferences','settings','portfolio']);if(payload.schema!==SCHEMA)fail();
  exact(payload.settings,['version','display_locale','source_language']);
  return create(preferences(payload.preferences),payload.settings,payload.portfolio,catalog,market,language);
 }
 async function read(view,catalog){
  const raw=view.localStorage.getItem(PERSONAL_KEY),p=raw?JSON.parse(raw):{version:1,interests:[],groups:[]};
  const settings=view.AppLanguage.read(view.localStorage);if(!settings.writable)throw Error('BACKUP_SETTINGS_UNREADABLE');
  return create(p,settings.value,await view.DeviceActual.readHoldings(view,catalog),catalog,view.DeviceMarket,view.AppLanguage);
 }
 function download(view,payload,name='investment-personal.json'){
  const url=view.URL.createObjectURL(new view.Blob([JSON.stringify(payload,null,2)],{type:'application/json'})),a=view.document.createElement('a');a.href=url;a.download=name;a.click();view.setTimeout(()=>view.URL.revokeObjectURL(url),1000);
 }
 async function restore(view,catalog,payload){
  const next=parse(payload,catalog,view.DeviceMarket,view.AppLanguage),keys=[PERSONAL_KEY,view.AppLanguage.KEY],before=keys.map(k=>view.localStorage.getItem(k));
  try{
   view.localStorage.setItem(keys[0],JSON.stringify(next.preferences));view.AppLanguage.write(view.localStorage,next.settings);
   await view.DeviceActual.restoreHoldings(view,catalog,next.portfolio);
  }catch(_){
   try{keys.forEach((k,i)=>before[i]===null?view.localStorage.removeItem(k):view.localStorage.setItem(k,before[i]));}catch(_){throw Error('BACKUP_ROLLBACK_FAILED');}
   throw Error('BACKUP_RESTORE_FAILED');
  }
  return next;
 }
 return Object.freeze({SCHEMA,preferences,create,parse,read,download,restore});
});
