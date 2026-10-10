/* Operations status from already-public, price-free metadata only. No new thresholds: STALE uses each file's own stale_after_seconds. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.OpsStatus=api;})(globalThis,function(){
'use strict';
const SCREENS=[['sec-qg-factors.json','Q·G'],['company-types-pricefree.json','유형'],['sec-filing-windows.json','실적 예상 시기'],['macro-screen.json','매크로'],['sec-13f-changes.json','13F']];
function summarize({secReported=null,screens={},now=Date.now()}={}){
 const rows=[];
 const companies=secReported&&secReported.companies&&typeof secReported.companies==='object'?Object.values(secReported.companies):[];
 if(!companies.length)rows.push({id:'sec-public-inputs.json',label:'SEC 공개 입력',state:'NOT_AVAILABLE',last_success_at:null,failed_companies:null,total_companies:null,stale:null,reason_codes:['NOT_CONNECTED']});
 else{const live=companies.filter(c=>c.status==='LIVE'),stamps=live.map(c=>Date.parse(c.acquired_at)).filter(Number.isFinite);
  rows.push({id:'sec-public-inputs.json',label:'SEC 공개 입력',state:live.length?'LIVE':'NOT_AVAILABLE',last_success_at:stamps.length?new Date(Math.max(...stamps)).toISOString():null,failed_companies:companies.length-live.length,total_companies:companies.length,stale:null,reason_codes:[...new Set(companies.flatMap(c=>c.reason_codes||[]))].sort()});}
 for(const [id,label] of SCREENS){const p=screens?.[id];if(!p){rows.push({id,label,state:'NOT_AVAILABLE',last_success_at:null,failed_companies:null,total_companies:null,stale:null,reason_codes:['NOT_CONNECTED']});continue;}
  const at=Date.parse(p.as_of),stale=Number.isFinite(at)&&typeof p.stale_after_seconds==='number'?now-at>p.stale_after_seconds*1000:null;
  rows.push({id,label,state:p.state,last_success_at:p.state==='NOT_AVAILABLE'?null:p.as_of,failed_companies:null,total_companies:null,stale,reason_codes:[...(p.reason_codes||[])]});}
 return rows;}
function mount(host,input,{locale}={}){if(!host)return;const doc=host.ownerDocument,en=locale==='en-US',el=(tag,text,attrs={})=>{const n=doc.createElement(tag);if(text!==undefined)n.textContent=text;for(const[k,v]of Object.entries(attrs))n.setAttribute(k,v);return n;};
 const card=el('section',undefined,{class:'card','data-ops-status':''});card.append(el('h2',en?'Data operations status':'데이터 운영 상태'),el('p',en?'Public, price-free files only. Last success time, failed company count and STALE use each file\'s own metadata.':'공개·가격 없는 파일만 표시합니다. 마지막 성공 시각·실패 회사 수·STALE은 각 파일의 메타데이터 기준입니다.',{class:'small'}));
 const wrap=el('div',undefined,{class:'table-wrap'}),table=el('table'),head=el('tr'),body=el('tbody');for(const h of [en?'File':'파일',en?'State':'상태',en?'Last success':'마지막 성공',en?'Failed':'실패 회사',en?'Reasons':'사유'])head.append(el('th',h));const thead=el('thead');thead.append(head);
 for(const r of summarize(input)){const tr=el('tr',undefined,{'data-ops-row':r.id});const state=r.stale?r.state+' · STALE':r.state;tr.append(el('td',r.label),el('td',state,{'data-ops-state':state}),el('td',r.last_success_at||'—'),el('td',r.failed_companies===null?'—':r.failed_companies+' / '+r.total_companies),el('td',r.reason_codes.join(' · ')||'—'));body.append(tr);}
 table.append(thead,body);wrap.append(table);card.append(wrap);host.replaceChildren(card);}
return Object.freeze({summarize,mount});
});
