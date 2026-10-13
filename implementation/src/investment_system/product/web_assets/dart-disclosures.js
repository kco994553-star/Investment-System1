/* Public `dart-disclosures.json` reader (OpenDART, 한미반도체 042700). Mirrors Python product/dart_public.require_disclosures.
   Same record format and display as the SEC 8-K list: channel DISCLOSURE '공시·확정', source 'DART', title/link/date/
   classification only, never body text; nothing changes any score. OpenDART gives a KST date only (no time). DOM via textContent. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.DartDisclosures=api;})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
const FILENAME='dart-disclosures.json',KIND='DART_DISCLOSURES',SOURCE='DART',MAX=1024*1024,WINDOW_DAYS=90,STALE_AFTER=172800,MAX_EVENTS=300,DAY=86400000;
const LINK='https://dart.fss.or.kr/dsaf001/main.do?rcpNo=',COMPANIES={hanmi:'042700'},REPORT_TYPES=['A','B','I'];
const REASONS=['NOT_COLLECTED','DART_API_KEY_MISSING','DART_API_KEY_INVALID_FORMAT','DART_CALL_BUDGET_EXCEEDED','DART_KEY_NOT_REGISTERED','DART_KEY_DISABLED','DART_IP_NOT_ALLOWED','DART_NO_DATA','DART_FILE_NOT_FOUND','DART_LIMIT_EXCEEDED','DART_COMPANY_LIMIT_EXCEEDED','DART_INVALID_FIELD','DART_INVALID_ACCESS','DART_MAINTENANCE','DART_UNDEFINED_ERROR','DART_KEY_EXPIRED','DART_UNKNOWN_STATUS','DART_TRANSPORT_FAILED','DART_REDIRECT_REJECTED','DART_HTTP_ERROR','DART_RESPONSE_TOO_LARGE','DART_JSON_INVALID','DART_ZIP_INVALID','DART_CONFIG_INVALID','DART_IDENTITY_MISMATCH','DART_LIST_INVALID','DART_LIST_TRUNCATED','DART_FINANCIALS_INVALID','CORP_CODE_UNCONFIRMED','NO_PERIODIC_REPORT','NO_NEWER_INTERIM_REPORT','SEPARATE_STATEMENTS_FALLBACK','SHARES_NOT_AVAILABLE','QG_INPUTS_NOT_AVAILABLE','RECORDS_DROPPED_INVALID','STALE_INPUT'];
const CLASSES={RESULTS:['실적(잠정실적 공정공시)','Results (preliminary earnings)'],PERIODIC:['정기보고서','Periodic report'],MAJOR_EVENT:['주요사항보고서','Major event report'],FAIR_DISCLOSURE:['공정공시','Fair disclosure'],EXCHANGE:['거래소 공시','Exchange disclosure'],OTHER:['기타 공시','Other disclosure']};
const CHANNELS={DISCLOSURE:['공시·확정','Disclosure · confirmed']};
const TOP=['schema_version','kind','source','as_of','state','reason_codes','freshness_basis','stale_after_seconds','window_days','channel','score_effect','collection','companies','events'];
const COMPANY=['state','acquired_at','reason_code','stock_code','corp_code','corp_code_basis','truncated'];
const EVENT=['company_id','source','rcept_no','report_type','title','filing_date','accepted_at','time_precision','classification','amended','link','group_id','occurrence','first_seen_at'];
const TAG='(?:\\[[^\\]]{1,20}\\] *)',TITLE_BAD=/[\u0000-\u001f\u007f-\u009f<>\u00a0\u1680\u180e\u2000-\u200b\u2028\u2029\u202f\u205f\u3000\ufeff]/u;
function need(v){if(!v)throw Error('DART_PUBLIC_INVALID');}
const plain=v=>v!==null&&typeof v==='object'&&!Array.isArray(v),keys=(v,k)=>plain(v)&&Object.keys(v).length===k.length&&k.every(n=>Object.hasOwn(v,n));
const int=v=>typeof v==='number'&&Number.isInteger(v);
function instant(v){need(typeof v==='string'&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00$/.test(v));const t=Date.parse(v);need(Number.isFinite(t)&&new Date(t).toISOString().slice(0,19)===v.slice(0,19));return t;}
function day(v){need(typeof v==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&new Date(v+'T00:00:00Z').toISOString().slice(0,10)===v);return v;}
const kstDay=t=>new Date(t+9*3600000).toISOString().slice(0,10),fresh=(at,cut)=>cut-at>STALE_AFTER*1000?'STALE':'LIVE';
function top(states){const s=states.includes('LIVE')?'LIVE':states.includes('STALE')?'STALE':'NOT_AVAILABLE';return[s,s==='LIVE'?[]:s==='STALE'?['STALE_INPUT']:['NO_ELIGIBLE_INPUT']];}
function validTitle(v){return typeof v==='string'&&[...v].length>0&&[...v].length<=200&&!TITLE_BAD.test(v)&&!v.startsWith(' ')&&!v.endsWith(' ')&&!v.includes('  ');}
function family(title){const key=title.replace(new RegExp('^'+TAG+'+','u'),'').replace(/ *\([0-9]{4}\.[0-9]{2}\)$/u,'').replace(/^ +| +$/g,'');return key||title;}
function amended(title){return new RegExp('^'+TAG+'*\\[[^\\]]{0,18}정정[^\\]]{0,18}\\]','u').test(title);}
function classify(title,type){if(/\(잠정\) *실적/u.test(title)&&title.includes('공정공시'))return 'RESULTS';if(type==='A')return 'PERIODIC';if(type==='B')return 'MAJOR_EVENT';if(type==='I')return title.includes('공정공시')?'FAIR_DISCLOSURE':'EXCHANGE';return 'OTHER';}
const link=no=>LINK+no,cmp=(a,b)=>a.filing_date!==b.filing_date?(a.filing_date>b.filing_date?-1:1):a.rcept_no>b.rcept_no?-1:a.rcept_no<b.rcept_no?1:0;
// Mirrors Python assign_groups: an original report starts its own group (NEW); a correction joins the single same-company,
// same-title-family original filed no later, else its own group, and is always REPEAT.
function groups(events){const originals=new Map();for(const e of events)if(!e.amended){const k=e.company_id+'|'+family(e.title);if(!originals.has(k))originals.set(k,[]);originals.get(k).push(e);}
 return events.map(e=>{const own=e.company_id+':'+e.rcept_no;if(!e.amended)return{group_id:own,occurrence:'NEW'};const m=(originals.get(e.company_id+'|'+family(e.title))||[]).filter(o=>o.filing_date<e.filing_date||o.filing_date===e.filing_date&&o.rcept_no<=e.rcept_no);return{group_id:m.length===1?m[0].company_id+':'+m[0].rcept_no:own,occurrence:'REPEAT'};});}
function validate(p){
 try{
  need(keys(p,TOP)&&p.schema_version===1&&p.kind===KIND&&p.source===SOURCE&&p.freshness_basis==='SOURCE_ACQUISITION'&&p.channel==='DISCLOSURE'&&p.score_effect==='NONE'&&p.stale_after_seconds===STALE_AFTER&&p.window_days===WINDOW_DAYS);
  const cut=instant(p.as_of),c=p.collection;need(keys(c,['api_calls','api_call_budget'])&&int(c.api_calls)&&int(c.api_call_budget)&&c.api_calls>=0&&c.api_call_budget<=50&&c.api_calls<=c.api_call_budget);
  const ids=Object.keys(COMPANIES);need(plain(p.companies)&&Object.keys(p.companies).length===ids.length&&ids.every(id=>Object.hasOwn(p.companies,id)));const acquired={},states=[];
  for(const id of ids){const x=p.companies[id];need(keys(x,COMPANY)&&x.stock_code===COMPANIES[id]&&typeof x.truncated==='boolean');
   if(x.acquired_at===null)need(x.state==='NOT_AVAILABLE'&&REASONS.includes(x.reason_code)&&x.reason_code!=='STALE_INPUT'&&x.corp_code===null&&x.corp_code_basis===null&&!x.truncated);
   else{const at=instant(x.acquired_at);need(at<=cut&&x.state===fresh(at,cut)&&[null,'DART_LIST_TRUNCATED','RECORDS_DROPPED_INVALID'].includes(x.reason_code)&&x.truncated===(x.reason_code==='DART_LIST_TRUNCATED')&&typeof x.corp_code==='string'&&/^\d{8}$/.test(x.corp_code)&&x.corp_code_basis==='CORPCODE_XML');acquired[id]=at;}
   states.push(x.state);}
  const[state,reasons]=top(states);need(p.state===state&&JSON.stringify(p.reason_codes)===JSON.stringify(reasons));
  const events=p.events;need(Array.isArray(events)&&events.length<=MAX_EVENTS);const cutoff=new Date(Date.parse(kstDay(cut)+'T00:00:00Z')-WINDOW_DAYS*DAY).toISOString().slice(0,10),seen=new Set();
  for(const e of events){need(keys(e,EVENT)&&Object.hasOwn(acquired,e.company_id)&&e.source===SOURCE&&typeof e.rcept_no==='string'&&/^\d{14}$/.test(e.rcept_no)&&!seen.has(e.rcept_no));seen.add(e.rcept_no);
   need((e.report_type===null||REPORT_TYPES.includes(e.report_type))&&validTitle(e.title));day(e.filing_date);need(cutoff<=e.filing_date&&e.filing_date<=kstDay(acquired[e.company_id]));
   need(e.accepted_at===null&&e.time_precision==='DATE_KST'&&Object.hasOwn(CLASSES,e.classification)&&e.classification===classify(e.title,e.report_type));
   need(typeof e.amended==='boolean'&&e.amended===amended(e.title)&&e.link===link(e.rcept_no));const seenAt=instant(e.first_seen_at);need(seenAt<=cut&&kstDay(seenAt)>=e.filing_date);}
  for(let i=1;i<events.length;i++)need(cmp(events[i-1],events[i])<0);
  const expected=groups(events);need(events.every((e,i)=>e.group_id===expected[i].group_id&&e.occurrence===expected[i].occurrence));return p;
 }catch(_){throw Error('DART_PUBLIC_INVALID');}
}
async function load(view){const control=new AbortController(),timer=setTimeout(()=>control.abort(),20000);
 try{const r=await view.fetch(FILENAME,{cache:'no-store',credentials:'omit',referrerPolicy:'no-referrer',redirect:'error',signal:control.signal});if(!r.ok)return null;const text=await r.text();if(new TextEncoder().encode(text).length>MAX)return null;return validate(JSON.parse(text));}
 catch(_){return null;}finally{clearTimeout(timer);}}
// Rows in the SecDisclosures.timeline shape ({channel,time,company_id,event}); time = start of the KST filing day, for ordering only.
function timeline(payload,{companyIds=null}={}){return (payload?.events||[]).filter(e=>!companyIds||companyIds.includes(e.company_id)).map(e=>({channel:'DISCLOSURE',source:SOURCE,time:new Date(Date.parse(e.filing_date+'T00:00:00+09:00')).toISOString().slice(0,19)+'+00:00',company_id:e.company_id,event:e}));}
function classLabel(name,en){const [k,e]=CLASSES[name];return en?e+' ('+k+')':k+' ('+e+')';}
function mount(host,payload,{locale,companyIds=null,limit=30,emptyText}={}){
 if(!host)return;const doc=host.ownerDocument,en=locale==='en-US',T=(k,e)=>en?e:k,el=(tag,text,attrs={})=>{const n=doc.createElement(tag);if(text!==undefined)n.textContent=text;for(const[k,v]of Object.entries(attrs))n.setAttribute(k,v);return n;};
 const section=el('section',undefined,{class:'card','data-dart-disclosures':''});section.append(el('h2',T('공시·확정 · DART','Disclosures · confirmed · DART')));
 const state=payload?payload.state:'NOT_AVAILABLE';section.append(el('p',state,{class:'badge disclosure-state','data-disclosure-state':state}));
 if(!payload){section.append(el('p',T('DART 공시 자료가 연결되지 않았습니다.','DART disclosure data is not connected.'),{class:'empty'}));host.replaceChildren(section);return;}
 const reason=Object.values(payload.companies).map(c=>c.reason_code).find(Boolean);
 if(state==='NOT_AVAILABLE'&&reason)section.append(el('p','NOT_AVAILABLE · '+reason,{class:'small','data-disclosure-reason':reason}));
 if(state!=='NOT_AVAILABLE'&&Date.now()-Date.parse(payload.as_of)>payload.stale_after_seconds*1000)section.append(el('p','STALE · '+T('수집 갱신 시각 경과','Acquisition refresh overdue'),{class:'warning','data-disclosure-stale':''}));
 section.append(el('p',T('기준: ','As of: ')+payload.as_of+' · '+T('최근 '+payload.window_days+'일 · 접수일(KST)만 제공','last '+payload.window_days+' days · receipt date (KST) only'),{class:'meta'}),el('p',T('점수에 반영하지 않음 · 제목·링크·날짜·기업·분류만 표시','Never changes scores · title, link, date, company and classification only'),{class:'small','data-score-effect':payload.score_effect}));
 const rows=timeline(payload,{companyIds}).slice(0,limit);
 if(!rows.length){section.append(el('p',emptyText||T('표시할 공시가 없습니다.','No disclosures to show.'),{class:'empty'}));host.replaceChildren(section);return;}
 const list=el('ol',undefined,{class:'list','data-disclosure-list':''});
 for(const row of rows){const e=row.event,li=el('li',undefined,{class:'card','data-disclosure':e.rcept_no,'data-source':SOURCE,'data-occurrence':e.occurrence,'data-classification':e.classification});
  const head=el('p',undefined,{class:'chips'});head.append(el('span',CHANNELS.DISCLOSURE[en?1:0],{class:'badge LIVE','data-channel':'DISCLOSURE'}),el('span',e.occurrence==='NEW'?T('새 공시','New'):T('정정·반복','Repeat / amendment'),{class:'badge','data-occurrence-label':e.occurrence}),el('span',classLabel(e.classification,en),{class:'badge','data-classification-label':e.classification}));li.append(head);
  const who=el('p');who.append(el('a',e.company_id==='hanmi'?'042700':e.company_id.toUpperCase(),{href:'#company/'+encodeURIComponent(e.company_id)}),doc.createTextNode(' · '+SOURCE+' · '+e.filing_date+' KST'));li.append(who);
  const t=el('p');t.append(el('a',e.title,{href:e.link,target:'_blank',rel:'noopener noreferrer','data-filing-link':''}),doc.createTextNode(' ↗'));li.append(t);
  list.append(li);}
 section.append(list);host.replaceChildren(section);
}
function qgv2Reference(financials,universe,engine=globalThis.SecQgv2){
 const company=financials?.companies?.hanmi,block=company?.qgv2;
 if(!block||!engine||typeof engine.scoreRows!=='function'||!universe)return null;
 need(block.reference_only===true&&block.comparison_label==='참고 순위'&&block.comparison_basis==='US_UNIVERSE_504_GENERAL'&&block.industry_basis==='NOT_ASSIGNED'&&block.currency==='KRW');
 need(plain(block.metrics)&&Object.keys(block.metrics).every(k=>engine.METRIC_KEYS.includes(k)&&(block.metrics[k]===null||typeof block.metrics[k]==='number'&&Number.isFinite(block.metrics[k]))));
 const row={cik:null,state:company.state,profile:'GENERAL',industry_group:null,metrics:block.metrics};
 const result=engine.scoreRows(universe,{hanmi:row});
 return{...result.scores.get('target\u0000hanmi'),comparison_label:'참고 순위',reference_only:true,cross_section_size:result.summary.cross_section_size};
}
async function loadFinancials(view){const control=new AbortController(),timer=setTimeout(()=>control.abort(),20000);
 try{const response=await view.fetch('dart-financials.json',{cache:'no-store',credentials:'omit',referrerPolicy:'no-referrer',redirect:'error',signal:control.signal});if(!response.ok)return null;
  const text=await response.text();need(new TextEncoder().encode(text).length<=MAX);const payload=JSON.parse(text);
  need(payload.schema_version===1&&payload.kind==='DART_FINANCIALS'&&payload.source==='DART'&&payload.currency==='KRW'&&payload.method_status==='PROVISIONAL_UNCALIBRATED'&&plain(payload.companies)&&Object.keys(payload.companies).length===1);
  const c=payload.companies.hanmi;need(plain(c)&&c.stock_code==='042700'&&['LIVE','STALE','NOT_AVAILABLE'].includes(c.state));instant(payload.as_of);
  return payload;
 }catch(_){return null;}finally{clearTimeout(timer);}}
return Object.freeze({FILENAME,KIND,SOURCE,CLASSES,CHANNELS,REASONS,classify,classLabel,family,amended,validTitle,groups,link,validate,load,timeline,mount,qgv2Reference,loadFinancials});
});
