// Product-owned accessibility/focus enhancement; canonical body and validation stay upstream.
document.getElementById('list').addEventListener('click',e=>{if(e.target.closest('[data-id]')){const d=document.getElementById('detail');d.tabIndex=-1;d.scrollIntoView({block:'start'});d.focus();}});
new MutationObserver(()=>document.querySelectorAll('#list li').forEach(li=>{li.tabIndex=0;li.setAttribute('role','button');li.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();li.click();}};})).observe(document.getElementById('list'),{childList:true});
document.querySelectorAll('#list li').forEach(li=>{li.tabIndex=0;li.setAttribute('role','button');li.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();li.click();}};});
