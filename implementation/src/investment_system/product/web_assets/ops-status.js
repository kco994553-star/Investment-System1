/* Operations status from already-public, price-free metadata only. No new thresholds: STALE uses each file's own stale_after_seconds. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.OpsStatus=api;})(globalThis,function(){
'use strict';
const SCREENS=[['sec-qg-factors.json','Q·G'],['company-types-pricefree.json','유형'],['sec-filing-windows.json','실적 예상 시기'],['macro-screen.json','매크로'],['sec-13f-changes.json','13F'],['company-classification.json','산업·테마 v0']];
function summarize({secReported=null,secStatus=null,screens={},now=Date.now()}={}){
 const rows=[];
 const companies=secReported&&secReported.companies&&typeof secReported.companies==='object'?Object.values(secReported.companies):[];
 if(!companies.length)rows.push({id:'sec-public-inputs.json',label:'SEC 공개 입력',state:'NOT_AVAILABLE',last_success_at:null,failed_companies:null,total_companies:null,stale:null,reason_codes:[secStatus?.reason==='SEC_NOT_COLLECTED'?'SEC_NOT_COLLECTED':'NOT_CONNECTED']});
 else{const live=companies.filter(c=>c.status==='LIVE'),stamps=companies.map(c=>Date.parse(c.acquired_at)).filter(Number.isFinite),v4=companies.every(c=>typeof c.run==='string');
  // Schema /4: a company counts as failed when this run did not collect it (kept previous row, collection failure or identity withdrawal); a policy NA of a successful collection is not a failure.
  rows.push({id:'sec-public-inputs.json',label:'SEC 공개 입력',state:live.length?'LIVE':'NOT_AVAILABLE',last_success_at:stamps.length?new Date(Math.max(...stamps)).toISOString():null,failed_companies:v4?companies.filter(c=>c.run!=='COLLECTED').length:companies.length-live.length,total_companies:companies.length,stale:null,reason_codes:[...new Set(companies.flatMap(c=>[...(c.reason_codes||[]),...(c.preserved?.reason_codes||[])]))].sort()});}
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
/* TARGET SEC collection completeness of the run that produced sec-public-inputs.json (schema /4 only): new collections
   (LIVE values and policy NA) apart from rows kept from the previous copy (their own acquired_at and age, STALE per the
   file's stale_after_seconds), collection failures and identity withdrawals. Counts and fixed codes only. */
function collection({secReported=null,now=Date.now()}={}){
 const info=secReported&&secReported.collection,companies=secReported&&secReported.companies&&typeof secReported.companies==='object'?Object.values(secReported.companies):[];
 if(!info||!companies.length||!companies.every(c=>typeof c.run==='string'))return{state:'NOT_AVAILABLE',checked_at:null,trigger:null,previous:null,counts:null,rows:[],reason_codes:[companies.length?'OLDER_SCHEMA':'NOT_CONNECTED']};
 const by=run=>companies.filter(c=>c.run===run),collected=by('COLLECTED'),staleMs=info.stale_after_seconds*1000;
 const counts={companies:companies.length,collected:collected.length,collected_live:collected.filter(c=>c.status==='LIVE').length,collected_na:collected.filter(c=>c.status==='NOT_AVAILABLE').length,preserved:by('PRESERVED').length,failed:by('FAILED').length,withdrawn:by('WITHDRAWN').length};
 const rows=companies.filter(c=>c.run!=='COLLECTED').map(c=>{const at=Date.parse(c.acquired_at),age=Number.isFinite(at)?Math.max(0,(now-at)/3600000):null;
  return{company_id:c.company_id,run:c.run,status:c.status,acquired_at:c.acquired_at,elapsed_hours:age===null?null:Math.round(age*10)/10,stale:age===null?null:age*3600000>staleMs,checked_at:c.preserved?c.preserved.checked_at:c.checked_at,detected_at:c.detected_at,withdrawn_acquired_at:c.withdrawn_acquired_at,reason_codes:[...(c.preserved?c.preserved.reason_codes:c.reason_codes)]};});
 return{state:counts.collected===counts.companies?'COMPLETE':'INCOMPLETE',checked_at:info.checked_at,trigger:info.trigger,previous:info.previous,counts,rows,reason_codes:[]};}
/* Consecutive scheduled daily runs that reached Pages (owner queue §9: 7 in a row; manual fallbacks never count). The
   count is published by the run itself and is only public when that run deployed; it is current while its last
   scheduled run day is today or yesterday in New York, otherwise a later scheduled run did not deploy (estimate). */
const STREAK_TARGET=7;
function nyDay(ms){try{return new Intl.DateTimeFormat('en-CA',{timeZone:'America/New_York',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(ms));}catch(_){return new Date(ms).toISOString().slice(0,10);}}
function deployStreak({secReported=null,now=Date.now()}={}){
 const s=secReported&&secReported.collection&&secReported.collection.scheduled_streak,base={target:STREAK_TARGET,count:null,since:null,last_run_day:null};
 if(!s)return{...base,state:'NOT_AVAILABLE',reason_codes:['NO_PUBLIC_STREAK']};
 if(s.last_run_day===null)return{...base,state:'NOT_AVAILABLE',reason_codes:['NO_SCHEDULED_RUN']};
 if(s.count===null)return{...base,last_run_day:s.last_run_day,state:'UNKNOWN',reason_codes:['PREVIOUS_COPY_UNREAD']};
 const current=s.last_run_day===nyDay(now)||s.last_run_day===nyDay(now-86400000);
 if(!current)return{...base,count:0,since:null,last_run_day:s.last_run_day,state:'BROKEN',reason_codes:['NO_SCHEDULED_DEPLOY_SINCE']};
 return{...base,count:s.count,since:s.since,last_run_day:s.last_run_day,state:s.count>=STREAK_TARGET?'MET':'COUNTING',reason_codes:[]};}
const DAILY_LABEL={SUCCESS:['성공(추정)','Success (est.)'],PARTIAL:['부분(추정)','Partial (est.)'],FAILED:['실패(추정)','Failed (est.)'],NOT_AVAILABLE:['NOT_AVAILABLE','NOT_AVAILABLE']};
function elapsedText(hours,en){if(hours===null)return '—';if(hours<1)return en?'under 1 h ago':'1시간 이내';if(hours<48)return en?Math.floor(hours)+' h ago':Math.floor(hours)+'시간 전';const d=Math.floor(hours/24);return en?d+' days ago':d+'일 전';}
function mountDaily(card,input,en,el){const d=dailyRun(input),box=el('div',undefined,{'data-daily-run':d.state});
 box.append(el('p',undefined,{'data-daily-run-summary':''}));box.firstChild.append(el('strong',(en?'Latest daily collection: ':'최근 일일 수집: ')+DAILY_LABEL[d.state][en?1:0]+' · '+(d.latest_at||(d.reason_codes.includes('SEC_NOT_COLLECTED')?(en?'before SEC collection':'SEC 수집 전'):'—'))+(d.elapsed_hours===null?'':' · '+elapsedText(d.elapsed_hours,en))));box.append(
  el('p',(en?'Estimated from public file timestamps; the app never calls GitHub. Files from that run: ':'공개 파일 시각으로 추정하며 앱은 GitHub에 묻지 않습니다. 해당 실행의 파일: ')+d.files_in_run+'/'+d.files_total+(d.state!=='SUCCESS'&&d.reason_codes.length?' · '+d.reason_codes.join(' · '):''),{class:'small'}));card.append(box);return d;}
const STREAK_LABEL={MET:['달성(추정)','Met (est.)'],COUNTING:['집계 중(추정)','Counting (est.)'],BROKEN:['중단(추정)','Broken (est.)'],UNKNOWN:['확인 불가','Unknown'],NOT_AVAILABLE:['NOT_AVAILABLE','NOT_AVAILABLE']};
const TRIGGER_LABEL={SCHEDULED:['정기','scheduled'],MANUAL:['수동','manual'],OTHER:['기타','other']};
const PREVIOUS_LABEL={LOADED:['이전 사본 읽음','previous copy read'],NO_LIVE:['첫 게시','first publication'],UNAVAILABLE:['이전 사본 읽기 실패(유지 불가)','previous copy unreadable (nothing kept)'],NOT_REQUESTED:['이전 사본 미요청','previous copy not requested']};
function mountStreak(card,input,en,el){const d=deployStreak(input),box=el('div',undefined,{'data-deploy-streak':d.state}),i=en?1:0;
 box.append(el('p',undefined,{}));box.firstChild.append(el('strong',(en?'Scheduled runs deployed in a row: ':'정기 실행 연속 배포 성공: ')+(d.count===null?'—':d.count+(en?' / ':'회 / ')+d.target+(en?'':'회'))+' · '+STREAK_LABEL[d.state][i]));
 const parts=[];if(d.since)parts.push(d.since+(en?' onward':'부터'));if(d.last_run_day)parts.push((en?'last scheduled deploy ':'마지막 정기 배포 ')+d.last_run_day+(en?' (New York date)':'(뉴욕 날짜)'));
 parts.push(en?'manual fallbacks are not counted; separate from collection completeness':'수동 대체 실행은 세지 않으며 수집 완전성과 별도입니다');if(d.reason_codes.length)parts.push(d.reason_codes.join(' · '));
 box.append(el('p',parts.join(' · '),{class:'small'}));card.append(box);return d;}
function mountCollection(card,input,en,el){const c=collection(input),box=el('div',undefined,{'data-sec-collection':c.state}),i=en?1:0;
 if(!c.counts){box.append(el('p',(en?'TARGET SEC collection completeness: ':'TARGET SEC 수집 완전성: ')+'NOT_AVAILABLE · '+c.reason_codes.join(' · '),{class:'small'}));card.append(box);return c;}
 const n=c.counts;box.append(el('p',undefined,{}));box.firstChild.append(el('strong',(en?'TARGET SEC collection completeness: new ':'TARGET SEC 수집 완전성: 신규 수집 ')+n.collected+'/'+n.companies));
 box.append(el('p',(en?'values ':'값 ')+n.collected_live+(en?' · policy NA ':' · 정책상 NA ')+n.collected_na+(en?' · previous kept ':' · 이전 관측 유지 ')+n.preserved+(en?' · failed ':' · 수집 실패 ')+n.failed+(en?' · identity withdrawn ':' · 식별 충돌 철회 ')+n.withdrawn+' · '+(en?'run ':'실행 ')+c.checked_at+' ('+TRIGGER_LABEL[c.trigger][i]+') · '+PREVIOUS_LABEL[c.previous][i],{class:'small','data-sec-collection-counts':''}));
 if(c.rows.length){const list=el('ul',undefined,{class:'small'});for(const r of c.rows){const id=r.company_id.toUpperCase(),codes=r.reason_codes.join(' · ');let text;
   if(r.run==='PRESERVED')text=id+' · '+(r.status==='WITHDRAWN'?(en?'withdrawal kept · detected ':'식별 충돌 철회 유지 · 감지 ')+r.detected_at:(en?'previous observation kept':'이전 관측 유지')+(r.status==='NOT_AVAILABLE'?(en?' (policy NA)':'(정책상 NA)'):'')+(en?' · acquired ':' · 수집 ')+r.acquired_at+' · '+elapsedText(r.elapsed_hours,en)+(r.stale?' · STALE':''))+' · '+codes;
   else if(r.run==='WITHDRAWN')text=id+' · '+(en?'identity conflict · previous observation not used · detected ':'식별 충돌 · 이전 관측 사용 중지 · 감지 ')+r.detected_at+' · '+codes;
   else text=id+' · '+(en?'collection failed · checked ':'수집 실패 · 확인 ')+r.checked_at+' · '+codes;
   list.append(el('li',text,{'data-sec-collection-row':r.company_id,'data-run':r.run,...(r.stale?{'data-stale':''}:{})}));}
  box.append(list);}
 card.append(box);return c;}
function mount(host,input,{locale}={}){if(!host)return;const doc=host.ownerDocument,en=locale==='en-US',el=(tag,text,attrs={})=>{const n=doc.createElement(tag);if(text!==undefined)n.textContent=text;for(const[k,v]of Object.entries(attrs))n.setAttribute(k,v);return n;};
 const card=el('section',undefined,{class:'card','data-ops-status':''});card.append(el('h2',en?'Data operations status':'데이터 운영 상태'),el('p',en?'Public, price-free files only. Last success time, failed company count and STALE use each file\'s own metadata.':'공개·가격 없는 파일만 표시합니다. 마지막 성공 시각·실패 회사 수·STALE은 각 파일의 메타데이터 기준입니다.',{class:'small'}));
 mountDaily(card,input||{},en,el);mountStreak(card,input||{},en,el);mountCollection(card,input||{},en,el);
 const wrap=el('div',undefined,{class:'table-wrap'}),table=el('table'),head=el('tr'),body=el('tbody');for(const h of [en?'File':'파일',en?'State':'상태',en?'Last success':'마지막 성공',en?'Failed':'실패 회사',en?'Reasons':'사유'])head.append(el('th',h));const thead=el('thead');thead.append(head);
 for(const r of summarize(input)){const tr=el('tr',undefined,{'data-ops-row':r.id});const state=r.stale?r.state+' · STALE':r.state;if(r.reason_codes.includes('SEC_NOT_COLLECTED'))r.label=en?'SEC public inputs · before collection':'SEC 공개 입력 · 수집 전';tr.append(el('td',r.label),el('td',state,{'data-ops-state':state}),el('td',r.last_success_at||'—'),el('td',r.failed_companies===null?'—':r.failed_companies+' / '+r.total_companies),el('td',r.reason_codes.join(' · ')||'—'));body.append(tr);}
 table.append(thead,body);wrap.append(table);card.append(wrap);host.replaceChildren(card);}
return Object.freeze({summarize,dailyRun,collection,deployStreak,mount});
});
