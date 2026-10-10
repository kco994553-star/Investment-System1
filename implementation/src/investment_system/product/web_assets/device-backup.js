/* One price-free device backup. Only explicit user preferences and holdings are allowed.
   /3 adds 13F investor stars (10-digit CIKs, device-only); /1 and /2 stay importable and leave stored stars unchanged. */
(function(root,factory){const api=factory(typeof module==='object'&&module.exports?require('./device-profiles.js'):root.DeviceProfiles);if(typeof module==='object'&&module.exports)module.exports=api;else root.DeviceBackup=api;})(typeof globalThis!=='undefined'?globalThis:this,function(Profiles){
 'use strict';
 const SCHEMA='investment-device-backup/3',LEGACY=['investment-device-backup/1','investment-device-backup/2'],PERSONAL_KEY='investment.web.v1.personal',STAR_KEY='investment.web.v1.investor-stars',MAX_STARS=50,CIK=/^\d{10}$/;
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
 function accepts(payload){return object(payload)&&(payload.schema===SCHEMA||LEGACY.includes(payload.schema));}
 function create(prefs,settings,portfolio,catalog,market,language,profiles=Profiles.empty(),investorStars=[]){
  const personal=preferences({version:prefs.version,interests:prefs.interests,groups:prefs.groups.map(g=>({id:g.id,name:g.name,members:g.members}))});
  return {schema:SCHEMA,profiles:Profiles.validate(profiles),preferences:personal,settings:language.settings(settings),portfolio:portfolio===null?null:market.validateActual?market.validateActual(portfolio,catalog):market.importBackup(portfolio,catalog).snapshot,investor_stars:stars(investorStars)};
 }
 function parse(payload,catalog,market,language){
  if(!accepts(payload))fail();const v1=payload.schema===LEGACY[0],v3=payload.schema===SCHEMA;
  exact(payload,['schema','preferences','settings','portfolio',...(v1?[]:['profiles']),...(v3?['investor_stars']:[])]);
  exact(payload.settings,['version','display_locale','source_language']);
  return create(preferences(payload.preferences),payload.settings,payload.portfolio,catalog,market,language,v1?Profiles.empty():Profiles.validate(payload.profiles),v3?stars(payload.investor_stars):[]);
 }
 async function read(view,catalog){
  const raw=view.localStorage.getItem(PERSONAL_KEY),p=raw?JSON.parse(raw):{version:1,interests:[],groups:[]};
  const settings=view.AppLanguage.read(view.localStorage);if(!settings.writable)throw Error('BACKUP_SETTINGS_UNREADABLE');
  return create(p,settings.value,await view.DeviceActual.readHoldings(view,catalog),catalog,view.DeviceMarket,view.AppLanguage,Profiles.read(view.localStorage),storedStars(view.localStorage));
 }
 function download(view,payload,name='investment-personal.json'){
  const url=view.URL.createObjectURL(new view.Blob([JSON.stringify(payload,null,2)],{type:'application/json'})),a=view.document.createElement('a');a.href=url;a.download=name;a.click();view.setTimeout(()=>view.URL.revokeObjectURL(url),1000);
 }
 async function restore(view,catalog,payload){
  const next=parse(payload,catalog,view.DeviceMarket,view.AppLanguage),withStars=payload.schema===SCHEMA,keys=[PERSONAL_KEY,view.AppLanguage.KEY,Profiles.KEY,...(withStars?[STAR_KEY]:[])],before=keys.map(k=>view.localStorage.getItem(k));
  try{
   view.localStorage.setItem(keys[0],JSON.stringify(next.preferences));view.AppLanguage.write(view.localStorage,next.settings);Profiles.write(view.localStorage,next.profiles);
   if(withStars)view.localStorage.setItem(STAR_KEY,JSON.stringify(next.investor_stars));
   await view.DeviceActual.restoreHoldings(view,catalog,next.portfolio);
  }catch(_){
   try{keys.forEach((k,i)=>before[i]===null?view.localStorage.removeItem(k):view.localStorage.setItem(k,before[i]));}catch(_){throw Error('BACKUP_ROLLBACK_FAILED');}
   throw Error('BACKUP_RESTORE_FAILED');
  }
  return next;
 }
 return Object.freeze({SCHEMA,LEGACY_SCHEMAS:Object.freeze([...LEGACY]),STAR_KEY,MAX_STARS,accepts,preferences,stars,create,parse,read,download,restore});
});
