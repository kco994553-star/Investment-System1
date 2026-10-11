/* Operations status from already-public, price-free metadata only. No new thresholds: STALE uses each file's own stale_after_seconds. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.OpsStatus=api;})(globalThis,function(){
'use strict';
const SCREENS=[['sec-qg-factors.json','Q·G'],['company-types-pricefree.json','유형'],['sec-filing-windows.json','실적 예상 시기'],['macro-screen.json','매크로'],['sec-13f-changes.json','13F'],['company-classification.json','산업·테마 v0']];
function summarize({secReported=null,secStatus=null,screens={},now=Date.now()}={}){
 const rows=[];
 const companies=secReported&&secReported.companies&&typeof secReported.companies==='object'?Object.values(secReported.companies):[];
 if(!companies.length)rows.push({id:'sec-public-inputs.json',label:'SEC 공개 입력',state:'NOT_AVAILABLE',last_success_at:null,failed_companies:null,total_companies:null,stale:null,reason_codes:[secStatus?.reason==='SEC_NOT_COLLECTED'?'SEC_NOT_COLLECTED':'NOT_CONNECTED']});
 else{const live=companies.filter(c=>c.status==='LIVE'),stamps=live.map(c=>Date.parse(c.acquired_at)).filter(Number.isFinite);
  rows.push({id:'sec-public-inputs.json',label:'SEC 공개 입력',state:live.length?'LIVE':'NOT_AVAILABLE',last_success_at:stamps.length?new Date(Math.max(...stamps)).toISOString():null,failed_companies:companies.length-live.length,total_companies:companies.length,stale:null,reason_codes:[...new Set(companies.flatMap(c=>c.reason_codes||[]))].sort()});}
 for(const [id,label] of SCREENS){const p=screens?.[id];if(!p){rows.push({id,label,state:'NOT_AVAILABLE',last_success_at:null,failed_companies:null,total_companies:null,stale:null,reason_codes:['NOT_CONNECTED']});continue;}
  const at=Date.parse(p.as_of),stale=Number.isFinite(at)&&typeof p.stale_after_seconds==='number'?now-at>p.stale_after_seconds*1000:null;
  rows.push({id,label,state:p.state,last_success_at:p.state==='NOT_AVAILABLE'?null:p.as_of,failed_companies:null,total_companies:null,stale,reason_codes:[...(p.reason_codes||[])]});}
 return rows;}
/* Latest daily collection, estimated from public file timestamps only (no GitHub API). The daily workflow (cron 17 22 * * *)
   stamps every file it publishes with the run time and deploys only when every step passes, so:
   no stamp → NOT_AVAILABLE · newest stamp older than one cadence + grace → FAILED (estimated: no newer publish) ·
   every file from that run and not NOT_AVAILABLE/STALE → SUCCESS · otherwise PARTIAL. Display estimate only. */
const CADENCE_HOURS=24,GRACE_HOURS=12,RUN_WINDOW_HOURS=3;
function dailyRun(input={},now=input.now??Date.now()){
 const rows=summarize({...input,now}),stamps=rows.map(r=>Date.parse(r.last_success_at)).filter(Number.isFinite);
 if(!stamps.length)return{state:'NOT_AVAILABLE',latest_at:null,elapsed_hours:null,files_in_run:0,files_total:rows.length,reason_codes:[rows.some(r=>r.reason_codes.includes('SEC_NOT_COLLECTED'))?'SEC_NOT_COLLECTED':'NO_PUBLIC_TIMESTAMPS']};
 const latest=Math.max(...stamps),elapsed=Math.max(0,(now-latest)/3600000),inRun=rows.filter(r=>{const t=Date.parse(r.last_success_at);return Number.isFinite(t)&&latest-t<=RUN_WINDOW_HOURS*3600000&&r.state!=='NOT_AVAILABLE'&&!r.stale;});
 const state=elapsed>CADENCE_HOURS+GRACE_HOURS?'FAILED':inRun.length===rows.length?'SUCCESS':'PARTIAL';
 return{state,latest_at:new Date(latest).toISOString(),elapsed_hours:Math.round(elapsed*10)/10,files_in_run:inRun.length,files_total:rows.length,reason_codes:state==='FAILED'?['NO_PUBLISH_WITHIN_CADENCE']:rows.filter(r=>!inRun.includes(r)).map(r=>r.id)};}
const DAILY_LABEL={SUCCESS:['성공(추정)','Success (est.)'],PARTIAL:['부분(추정)','Partial (est.)'],FAILED:['실패(추정)','Failed (est.)'],NOT_AVAILABLE:['NOT_AVAILABLE','NOT_AVAILABLE']};
function elapsedText(hours,en){if(hours===null)return '—';if(hours<1)return en?'under 1 h ago':'1시간 이내';if(hours<48)return en?Math.floor(hours)+' h ago':Math.floor(hours)+'시간 전';const d=Math.floor(hours/24);return en?d+' days ago':d+'일 전';}
function mountDaily(card,input,en,el){const d=dailyRun(input),box=el('div',undefined,{'data-daily-run':d.state});
 box.append(el('p',undefined,{'data-daily-run-summary':''}));box.firstChild.append(el('strong',(en?'Latest daily collection: ':'최근 일일 수집: ')+DAILY_LABEL[d.state][en?1:0]+' · '+(d.latest_at||(d.reason_codes.includes('SEC_NOT_COLLECTED')?(en?'before SEC collection':'SEC 수집 전'):'—'))+(d.elapsed_hours===null?'':' · '+elapsedText(d.elapsed_hours,en))));box.append(
  el('p',(en?'Estimated from public file timestamps; the app never calls GitHub. Files from that run: ':'공개 파일 시각으로 추정하며 앱은 GitHub에 묻지 않습니다. 해당 실행의 파일: ')+d.files_in_run+'/'+d.files_total+(d.state!=='SUCCESS'&&d.reason_codes.length?' · '+d.reason_codes.join(' · '):''),{class:'small'}));card.append(box);return d;}
function mount(host,input,{locale}={}){if(!host)return;const doc=host.ownerDocument,en=locale==='en-US',el=(tag,text,attrs={})=>{const n=doc.createElement(tag);if(text!==undefined)n.textContent=text;for(const[k,v]of Object.entries(attrs))n.setAttribute(k,v);return n;};
 const card=el('section',undefined,{class:'card','data-ops-status':''});card.append(el('h2',en?'Data operations status':'데이터 운영 상태'),el('p',en?'Public, price-free files only. Last success time, failed company count and STALE use each file\'s own metadata.':'공개·가격 없는 파일만 표시합니다. 마지막 성공 시각·실패 회사 수·STALE은 각 파일의 메타데이터 기준입니다.',{class:'small'}));
 mountDaily(card,input||{},en,el);
 const wrap=el('div',undefined,{class:'table-wrap'}),table=el('table'),head=el('tr'),body=el('tbody');for(const h of [en?'File':'파일',en?'State':'상태',en?'Last success':'마지막 성공',en?'Failed':'실패 회사',en?'Reasons':'사유'])head.append(el('th',h));const thead=el('thead');thead.append(head);
 for(const r of summarize(input)){const tr=el('tr',undefined,{'data-ops-row':r.id});const state=r.stale?r.state+' · STALE':r.state;if(r.reason_codes.includes('SEC_NOT_COLLECTED'))r.label=en?'SEC public inputs · before collection':'SEC 공개 입력 · 수집 전';tr.append(el('td',r.label),el('td',state,{'data-ops-state':state}),el('td',r.last_success_at||'—'),el('td',r.failed_companies===null?'—':r.failed_companies+' / '+r.total_companies),el('td',r.reason_codes.join(' · ')||'—'));body.append(tr);}
 table.append(thead,body);wrap.append(table);card.append(wrap);host.replaceChildren(card);}
return Object.freeze({summarize,dailyRun,mount});
});
