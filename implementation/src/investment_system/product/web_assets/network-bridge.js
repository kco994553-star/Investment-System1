
// Reuse upstream viewport, selection and expansion functions. No relationship calculation.
const toolbar=document.createElement('div');toolbar.className='tb';toolbar.innerHTML='<button id="zoom-in" aria-label="확대">＋</button><button id="zoom-out" aria-label="축소">−</button><select id="edge-filter" aria-label="관계 필터"><option value="ALL">모든 관계</option><option value="FACT">Fact만</option><option value="INFERENCE">추론만</option></select><button id="focus-picked">선택 기업 집중</button>';
document.querySelector('header').append(toolbar);
document.getElementById('zoom-in').onclick=()=>zoomAt(1.25,500,500);document.getElementById('zoom-out').onclick=()=>zoomAt(.8,500,500);
let picked=null,interests=[];document.getElementById('net').addEventListener('click',e=>{const n=e.target.closest('[data-node]');if(!n)return;picked=n.dataset.node;const rec=M.nodes.find(x=>x.id===picked),q=document.getElementById('qv'),b=document.createElement('button');b.dataset.issuer=rec.issuer;b.textContent=interests.includes(rec.issuer)?'★ 관심기업':'☆ 관심기업';b.onclick=()=>parent.postMessage({type:'interest',id:rec.issuer},location.origin);q.append(b);});
document.getElementById('focus-picked').onclick=()=>{if(picked){focus=picked;steps=0;visible();}};
function filterEdges(){const val=document.getElementById('edge-filter').value;M.edges.forEach(e=>{document.getElementById('e-'+e.id).style.visibility=val==='ALL'||(val==='FACT')===(e.ep==='FACT')?'visible':'hidden';});}
document.getElementById('edge-filter').onchange=filterEdges;
// Scope remains the upstream implementation; expose all when no upstream My set is supplied.
document.querySelector('[data-scope="ALL"]')?.click();

window.addEventListener('message',e=>{if(e.source!==parent||e.origin!==location.origin||e.data?.type!=='interests')return;interests=e.data.ids;document.querySelectorAll('[data-issuer]').forEach(b=>b.textContent=interests.includes(b.dataset.issuer)?'★ 관심기업':'☆ 관심기업');});
parent.postMessage({type:'ready'},location.origin);
