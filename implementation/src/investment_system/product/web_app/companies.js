/* The company list (IS2.companies, common base 2026-10-31; FRONTEND_BRIEF §3, COMMON_BASE_20261031.md): the ONE company-list
   contract. The home search (search-part-live.js), the company page index (screen-search-live.js), technical analysis, news and
   every later screen that lists or picks a company read companies from here, never from the files themselves.
   - Scope today: Universe504. scope() → {id:'UNIVERSE504', label:'Universe504', as_of:null}; universe-codes/1 carries no date, so
     as_of stays null (never guessed).
   - Source: the two static public files the home search already read, through IS2.data (each read once per page and kept in
     memory; no new public file, no new request pattern, no request per call): the fixed code list (universe-codes.json,
     IS2.data.universe) and the reviewed names table (company-names-ko.json: English SEC name, Korean name, share-class letter,
     the code → TARGET company_id link).
   - Rows (deep-frozen, in the code list's order): {code:'NYSE:FIX', id, ticker, name_en|null, name_ko|null,
     status:'ACTIVE'|'WITHDRAWN', withdrawn_on:'YYYY-MM-DD'|null, official:true}. id = the TARGET company_id linked to the code,
     else the code (the key of #/company/<id> and of the public lists). name_en / name_ko carry the share-class letter when one
     issuer has several codes (EntitySearch.companyName's rule). WITHDRAWN = a listing-ended code of IS2.searchPart.LISTING_ENDED
     (the one display table, kept equal to the server table by implementation/tests/test_web_app_search_part.py): it stays in the
     list, is found and can be chosen, and screens show it as delisted (상장 종료 <date> · 점수 없음). Without that table the list
     is not built (FAILED), so a delisted code is never shown as active.
   - find(query, limit): ticker (case, '.', '-', '/' and spaces ignored; a full code too) and the English name. Korean text,
     aliases and companies outside the scope are not searched (owner rule, DC-23): korean(query) tells a screen to show its hint.
     Order: exact ticker or code, ticker prefix, name prefix, a name word prefix, ticker part, name part; ties by ticker. limit: a
     positive integer, omitted = every match. exact(query): the single exact ticker or code, else the single exact English name,
     else null. get(key): the row of a code or of a linked TARGET company_id, else null.
   - ready() → Promise of {state:'OK'|'PARTIAL'|'FAILED', size, missing:[Korean names of what could not be read]}; it never
     rejects. A result with a missing part is not kept: the next ready() reads again (IS2.data retries a failed static read).
     Before the first ready() settles, list() is [], find() [] and get() / exact() null.
   - A later scope widening (the IEX expansion, owner 2026-10-30) goes through this contract only: the wider rows come with
     official:false and their own scope(). A scope change never changes official scores, ranks or TARGET; those keep reading
     their own public files and never this list.
   Nothing here stores, sends, prices, scores or ranks anything; loading the file reads nothing (it only puts IS2.companies). */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else{const I=root.IS2=root.IS2||{};I.companies=api.create({data:()=>I.data,ended:()=>I.searchPart&&I.searchPart.LISTING_ENDED});}})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
const NAMES='company-names-ko.json';
const SCOPE=Object.freeze({id:'UNIVERSE504',label:'Universe504',as_of:null});
const VENUE=/^(NYSE|NASDAQ|BATS):[A-Z0-9][A-Z0-9.\-]{0,15}$/,DAY=/^\d{4}-\d{2}-\d{2}$/;
const HANGUL=/[ᄀ-ᇿ㄰-㆏가-힯]/;
const MISSING=Object.freeze({codes:'Universe504 목록',names:'영문 회사명 표',ended:'상장 종료 표'});
const EMPTY=Object.freeze([]);
const tickerKey=s=>String(s).toUpperCase().replace(/[\s.\-\/]/g,'');
const nameKey=s=>String(s).toLowerCase().replace(/[^a-z0-9&]+/g,' ').trim();
const text=q=>typeof q==='string'?q:q===null||q===undefined?'':String(q);
// The listing-ended table as {code: 'YYYY-MM-DD'}, or null when it is not there or not well formed.
function endedTable(t){
 if(!t||typeof t!=='object')return null;const out=new Map();
 for(const[code,e]of Object.entries(t)){if(!VENUE.test(code)||!e||typeof e.effective!=='string'||!DAY.test(e.effective))return null;out.set(code,e.effective);}
 return out;}
function create({data,ended}={}){
 const D=typeof data==='function'?data:()=>data,E=typeof ended==='function'?ended:()=>ended;
 let cur={rows:EMPTY,keys:[],by:new Map()},pending=null;
 async function read(fn){try{return await fn();}catch(_){return null;}}
 async function build(){
  const table=endedTable(E());
  if(!table)return{cur:null,missing:[MISSING.ended]};
  const d=D();
  const[codes,names]=await Promise.all([read(()=>d.universe()),read(()=>d.static(NAMES))]);
  const list=Array.isArray(codes)?codes.filter(c=>typeof c==='string'&&VENUE.test(c)):[],links=new Map();
  if(names)for(const[c,id]of names.codes())if(id)links.set(c,id);
  const keys=[],by=new Map();
  const rows=list.map(code=>{
   const rec=names?names.get(code):null,ticker=code.slice(code.indexOf(':')+1),cls=rec&&rec.class_label?rec.class_label:null;
   const en=rec&&rec.en_name?rec.en_name+(cls?' Class '+cls:''):null,ko=rec&&rec.ko_name?rec.ko_name+(cls?' '+cls:''):null,off=table.get(code)||null;
   const row=Object.freeze({code,id:links.get(code)||code,ticker,name_en:en,name_ko:ko,status:off?'WITHDRAWN':'ACTIVE',withdrawn_on:off,official:true});
   keys.push({row,t:tickerKey(ticker),n:en?nameKey(en):''});
   return row;});
  for(const r of rows){by.set(r.code,r);if(!by.has(r.id))by.set(r.id,r);}
  return{cur:{rows:Object.freeze(rows),keys,by},missing:[!list.length&&MISSING.codes,!names&&MISSING.names].filter(Boolean)};
 }
 function ready(){
  if(!pending){const p=build().catch(()=>({cur:null,missing:[MISSING.codes,MISSING.names]})).then(({cur:next,missing})=>{
    if(next)cur=next;
    if(missing.length&&pending===p)pending=null;
    return Object.freeze({state:!cur.rows.length?'FAILED':missing.length?'PARTIAL':'OK',size:cur.rows.length,missing:Object.freeze(missing)});});
   pending=p;}
  return pending;}
 // Search order (DC-23): exact ticker or code 0, ticker prefix 1, name prefix 2, name word prefix 3, ticker part 4, name part 5.
 function rank(e,raw,T,N){
  const code=e.row.code;
  if(code===raw||e.t===T)return 0;if(T&&e.t.startsWith(T))return 1;if(raw.includes(':')&&code.startsWith(raw))return 1;
  if(!e.n||!N)return T.length>=2&&e.t.includes(T)?4:null;
  if(e.n.startsWith(N))return 2;if((' '+e.n).includes(' '+N))return 3;if(T.length>=2&&e.t.includes(T))return 4;if(N.length>=3&&e.n.includes(N))return 5;return null;}
 function find(query,limit){
  if(limit!==undefined&&!(Number.isInteger(limit)&&limit>0))throw Error('LIMIT_INVALID');
  const raw=text(query).trim().toUpperCase(),T=tickerKey(raw),N=nameKey(raw);if(!raw||HANGUL.test(raw))return EMPTY;
  const out=[];for(const e of cur.keys){const r=rank(e,raw,T,N);if(r!==null)out.push({e,r});}
  out.sort((a,b)=>a.r-b.r||(a.e.row.ticker<b.e.row.ticker?-1:a.e.row.ticker>b.e.row.ticker?1:0));
  return Object.freeze((limit===undefined?out:out.slice(0,limit)).map(x=>x.e.row));}
 function exact(query){
  const raw=text(query).trim().toUpperCase(),T=tickerKey(raw),N=nameKey(raw);if(!raw||HANGUL.test(raw))return null;
  const a=cur.keys.filter(e=>e.row.code===raw||e.t===T);if(a.length===1)return a[0].row;if(a.length)return null;
  const b=N?cur.keys.filter(e=>e.n===N):[];return b.length===1?b[0].row:null;}
 const get=key=>typeof key==='string'&&cur.by.get(key)||null;
 const korean=query=>HANGUL.test(text(query));
 return Object.freeze({ready,list:()=>cur.rows,get,find,exact,korean,scope:()=>SCOPE});
}
return Object.freeze({create,SCOPE,NAMES});
});
