/* PC table sorting (>= 1024px). Display only: rows are reordered in the DOM, nothing is stored or sent.
   Click or press Enter/Space on a column header button; order cycles ascending → descending → original.
   Stable (ties keep their original order) and NOT_AVAILABLE-like values (—, N/A, NOT_AVAILABLE, empty) always sort last.
   Phones (< 1024px) keep the original table untouched; leaving PC width restores the original order and headers. */
(function(root,factory){const api=factory(root);if(typeof module==='object'&&module.exports)module.exports=api;else root.TableSort=api;})(typeof globalThis==='object'?globalThis:this,function(g){
'use strict';
const QUERY='(min-width: 1024px)';
const SELECTOR='main .table-wrap table, main .table-scroll table';
const MISSING=/^(?:|—|–|-|\[—\]|N\/?A|NA|NOT_AVAILABLE|NOT_STARTED|NULL)(?:\s|·|$)/i;
const collator=typeof Intl==='object'?new Intl.Collator(undefined,{numeric:true,sensitivity:'base'}):null;
// Sort key for one cell text: {kind:'missing'} | {kind:'number',value} | {kind:'text',value}.
function keyOf(text){
 const s=String(text==null?'':text).replace(/\s+/g,' ').trim();
 if(MISSING.test(s))return{kind:'missing'};
 if(/^\d{4}-\d{2}-\d{2}/.test(s))return{kind:'text',value:s};
 const m=/^[#+]?\s*([-+−]?)\s*(?:[$₩€£¥]\s*)?(\d[\d,]*(?:\.\d+)?|\.\d+)\s*(?:%|pp|%p|원|만원|억원)?(?=$|\s|·|\(|\/)/.exec(s);
 if(m){const v=Number(m[2].replace(/,/g,''))*((m[1]==='-'||m[1]==='−')?-1:1);if(Number.isFinite(v))return{kind:'number',value:v};}
 return{kind:'text',value:s};
}
// Compare two keys in the given direction (1 asc, -1 desc). Missing values are last in both directions;
// numbers come before text in ascending order.
function compareKeys(a,b,dir){
 if(a.kind==='missing'||b.kind==='missing')return a.kind===b.kind?0:a.kind==='missing'?1:-1;
 let c;
 if(a.kind!==b.kind)c=a.kind==='number'?-1:1;
 else if(a.kind==='number')c=a.value<b.value?-1:a.value>b.value?1:0;
 else c=collator?collator.compare(a.value,b.value):(a.value<b.value?-1:a.value>b.value?1:0);
 return c*dir;
}
// Pure: stable order of row indexes for the given cell texts.
function order(texts,dir){
 const keyed=texts.map((t,i)=>({k:keyOf(t),i}));
 keyed.sort((x,y)=>compareKeys(x.k,y.k,dir)||x.i-y.i);
 return keyed.map(x=>x.i);
}
const state=new WeakMap(),remembered=new Map();
function identity(table){
 const attr=[...table.attributes].map(a=>a.name).filter(n=>n.startsWith('data-')).join(',');
 const heads=[...table.querySelectorAll('thead th')].map(th=>th.textContent.trim()).join('|');
 return attr+'#'+heads;
}
function sortable(table){
 const body=table.tBodies[0],head=table.tHead;
 if(!body||!head||table.tBodies.length!==1||head.rows.length!==1)return false;
 const rows=[...body.rows];
 if(rows.length<2)return false;
 const width=head.rows[0].cells.length;
 return rows.every(r=>r.cells.length===width&&[...r.cells].every(c=>c.colSpan===1&&c.rowSpan===1));
}
function apply(table,col,dir){
 const st=state.get(table);if(!st)return;
 const body=table.tBodies[0],rows=st.original.filter(r=>r.parentNode===body);
 const seq=dir===0?rows:order(rows.map(r=>r.cells[col]?r.cells[col].textContent:''),dir).map(i=>rows[i]);
 st.col=col;st.dir=dir;
 body.append(...seq);
 for(const[i,th]of st.heads.entries()){const v=i===col&&dir!==0?(dir===1?'ascending':'descending'):'none';th.setAttribute('aria-sort',v);}
 if(dir===0)remembered.delete(st.id);else remembered.set(st.id,{col,dir});
}
function enhance(table){
 if(state.has(table)||!sortable(table))return;
 const doc=table.ownerDocument,heads=[...table.tHead.rows[0].cells];
 const st={original:[...table.tBodies[0].rows],heads,col:-1,dir:0,id:identity(table)};state.set(table,st);
 table.setAttribute('data-table-sort','');
 heads.forEach((th,i)=>{
  const b=doc.createElement('button');b.type='button';b.className='th-sort';b.setAttribute('data-sort-col',String(i));
  while(th.firstChild)b.appendChild(th.firstChild);th.appendChild(b);th.setAttribute('aria-sort','none');
  b.onclick=()=>{const cur=state.get(table);if(!cur)return;const next=cur.col!==i?1:cur.dir===1?-1:cur.dir===-1?0:1;apply(table,i,next);};
 });
 // Short numbers and dates do not break mid-value on PC (they are the narrow columns once text wraps).
 for(const r of st.original)for(const c of r.cells){const t=c.textContent.trim();if(t.length<=16&&(keyOf(t).kind==='number'||/^\d{4}-\d{2}-\d{2}$/.test(t)))c.classList.add('cell-nowrap');}
 const prev=remembered.get(st.id);if(prev&&prev.col<heads.length)apply(table,prev.col,prev.dir);
}
function restore(table){
 const st=state.get(table);if(!st)return;
 apply(table,-1,0);remembered.delete(st.id);
 for(const th of st.heads){const b=th.querySelector(':scope > .th-sort');if(b){while(b.firstChild)th.insertBefore(b.firstChild,b);b.remove();}th.removeAttribute('aria-sort');}
 for(const r of st.original)for(const c of r.cells)c.classList.remove('cell-nowrap');
 table.removeAttribute('data-table-sort');state.delete(table);
}
function scan(doc,on){for(const t of doc.querySelectorAll(SELECTOR))on?enhance(t):restore(t);}
function init(win){
 if(!win||!win.document||!win.matchMedia||win.__tableSortInit)return;win.__tableSortInit=true;
 const doc=win.document,mq=win.matchMedia(QUERY);let queued=false;
 const run=()=>{queued=false;scan(doc,mq.matches);};
 const queue=()=>{if(!queued){queued=true;(win.requestAnimationFrame||setTimeout)(run);}};
 const start=()=>{const host=doc.querySelector('main')||doc.body;new win.MutationObserver(queue).observe(host,{childList:true,subtree:true});run();};
 if(mq.addEventListener)mq.addEventListener('change',run);else if(mq.addListener)mq.addListener(run);
 if(doc.readyState==='loading')doc.addEventListener('DOMContentLoaded',start);else start();
}
if(typeof window==='object'&&window&&window.document)init(window);
return Object.freeze({QUERY,SELECTOR,keyOf,compareKeys,order,init});
});
