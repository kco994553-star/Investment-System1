(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.InvestmentUI=api;})(globalThis,function(){
'use strict';
const finite=x=>typeof x==='number'&&Number.isFinite(x);
const escape=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function number(x,digits=1){return finite(x)?x.toFixed(digits):'—';}
function inputState(row,version,now){
 if(!row||row.state==='NOT_AVAILABLE'||!row.acquired_at)return 'MISSING';
 if(row.calc_version!==version)return 'VERSION_MISMATCH';
 const age=Date.parse(now)-Date.parse(row.acquired_at);
 if(!Number.isFinite(age)||age<0)return 'INVALID_TIME';
 return age>7*864e5?'STALE':'READY';
}
function readAxis(row,axis,version,now){
 if(!row||!version||row.calc_version!==version||!['LIVE','STALE'].includes(row.state||'LIVE'))return null;
 const age=Date.parse(now)-Date.parse(row.acquired_at),score=row.axes?.[axis]?.score;
 return Number.isFinite(age)&&age>=0&&age<=7*864e5&&finite(score)&&score>=0&&score<=100?score:null;
}
function filter(rows,{query='',sort='ticker',scope='all',watch=[]}={}){
 const q=query.trim().toLocaleLowerCase();
 return rows.filter(r=>(!q||[r.ticker,r.name,r.alias].some(v=>String(v||'').toLocaleLowerCase().includes(q)))&&(scope!=='watch'||watch.includes(r.ticker))&&(scope!=='target'||r.target>0)&&(scope!=='ready'||finite(r.q)&&finite(r.g)))
 .sort((a,b)=>['q','g'].includes(sort)?(finite(a[sort])&&finite(b[sort])?b[sort]-a[sort]||a.ticker.localeCompare(b.ticker):finite(a[sort])?-1:finite(b[sort])?1:a.ticker.localeCompare(b.ticker)):a.ticker.localeCompare(b.ticker));
}
function safeUrl(s){try{const u=new URL(s);return /^https?:$/.test(u.protocol)?u.href:null;}catch(_){return null;}}
return Object.freeze({finite,escape,number,readAxis,inputState,filter,safeUrl});
});
