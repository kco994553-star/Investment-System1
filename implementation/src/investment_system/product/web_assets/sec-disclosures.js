/* Public `sec-disclosures.json` reader (SEC 8-K current reports, queue 2.2 a/d). Mirrors Python require_sec_disclosures.
   Disclosures are labelled '공시·확정' and later news '뉴스·신호' in one chronological list. Only title, link, time, company and
   classification are shown; neither changes any score. DOM is built with textContent only. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.SecDisclosures=api;})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
const FILENAME='sec-disclosures.json',KIND='SEC_DISCLOSURES',MAX=2*1024*1024,WINDOW_DAYS=90,STALE_AFTER=172800,MAX_EVENTS=3000,TITLE_MAX=200;
const CIKS={amd:'0000002488',amzn:'0001018724',asml:'0000937966',avgo:'0001730168',etn:'0001551182',gev:'0001996810',googl:'0001652044',hubb:'0000048898',intc:'0000050863',klac:'0000319201',lrcx:'0000707549',msft:'0000789019',nvda:'0001045810',qcom:'0000804328',rok:'0001024478',rtx:'0000101829',stry:'0000310764'};
// Official Form 8-K item captions [English, Korean] (mirrors providers/sec_8k_disclosures.ITEMS).
const ITEMS={'1.01':['Entry into a Material Definitive Agreement','중요한 확정 계약 체결'],'1.02':['Termination of a Material Definitive Agreement','중요한 확정 계약 종료'],'1.03':['Bankruptcy or Receivership','파산 또는 법정관리'],'1.04':['Mine Safety - Reporting of Shutdowns and Patterns of Violations','광산 안전 - 폐쇄 및 위반 패턴 보고'],'1.05':['Material Cybersecurity Incidents','중요한 사이버보안 사고'],
 '2.01':['Completion of Acquisition or Disposition of Assets','자산 인수·처분 완료'],'2.02':['Results of Operations and Financial Condition','영업 실적 및 재무 상태'],'2.03':['Creation of a Direct Financial Obligation or an Obligation under an Off-Balance Sheet Arrangement of a Registrant','직접 금융 채무 또는 부외 약정상 채무의 발생'],'2.04':['Triggering Events That Accelerate or Increase a Direct Financial Obligation or an Obligation under an Off-Balance Sheet Arrangement','직접 금융 채무·부외 약정상 채무의 가속·증가 사유 발생'],'2.05':['Costs Associated with Exit or Disposal Activities','사업 철수·처분 관련 비용'],'2.06':['Material Impairments','중요한 자산 손상'],
 '3.01':['Notice of Delisting or Failure to Satisfy a Continued Listing Rule or Standard; Transfer of Listing','상장폐지 통지 또는 상장 유지 요건 미충족, 상장 이전'],'3.02':['Unregistered Sales of Equity Securities','미등록 지분증권 매각'],'3.03':['Material Modification to Rights of Security Holders','증권 보유자 권리의 중요한 변경'],
 '4.01':["Changes in Registrant's Certifying Accountant",'감사인 변경'],'4.02':['Non-Reliance on Previously Issued Financial Statements or a Related Audit Report or Completed Interim Review','기존 재무제표·감사보고서·검토 결과에 대한 신뢰 불가'],
 '5.01':['Changes in Control of Registrant','지배권 변경'],'5.02':['Departure of Directors or Certain Officers; Election of Directors; Appointment of Certain Officers; Compensatory Arrangements of Certain Officers','이사·특정 임원의 퇴임, 이사 선임, 특정 임원 선임, 특정 임원 보상 약정'],'5.03':['Amendments to Articles of Incorporation or Bylaws; Change in Fiscal Year','정관·내규 변경, 회계연도 변경'],'5.04':["Temporary Suspension of Trading Under Registrant's Employee Benefit Plans",'임직원 복리후생제도상 거래 일시 중지'],'5.05':["Amendment to Registrant's Code of Ethics, or Waiver of a Provision of the Code of Ethics",'윤리강령 개정 또는 적용 면제'],'5.06':['Change in Shell Company Status','셸 회사 지위 변경'],'5.07':['Submission of Matters to a Vote of Security Holders','주주 투표 안건 제출'],'5.08':['Shareholder Director Nominations','주주의 이사 후보 추천'],
 '6.01':['ABS Informational and Computational Material','ABS 정보·산출 자료'],'6.02':['Change of Servicer or Trustee','서비서 또는 수탁자 변경'],'6.03':['Change in Credit Enhancement or Other External Support','신용 보강 또는 기타 외부 지원 변경'],'6.04':['Failure to Make a Required Distribution','필수 배분 미이행'],'6.05':['Securities Act Updating Disclosure','증권법상 갱신 공시'],'6.06':['Static Pool','정적 풀'],'6.10':['Alternative Filings of Asset-Backed Issuers','자산유동화 발행인의 대체 제출'],
 '7.01':['Regulation FD Disclosure','공정공시(Regulation FD)'],'8.01':['Other Events','기타 사건'],'9.01':['Financial Statements and Exhibits','재무제표 및 첨부서류']};
const PRIORITY=[['2.02','RESULTS'],['5.02','OFFICERS_DIRECTORS'],['1.01','MATERIAL_AGREEMENT'],['2.01','ACQUISITION_DISPOSITION']];
const CLASSES={RESULTS:['실적','Results'],OFFICERS_DIRECTORS:['임원·이사','Officers / directors'],MATERIAL_AGREEMENT:['중요 계약','Material agreement'],ACQUISITION_DISPOSITION:['인수·처분','Acquisition / disposition'],OTHER:['기타 공시','Other disclosure']};
const CHANNELS={DISCLOSURE:['공시·확정','Disclosure · confirmed'],NEWS:['뉴스·신호','News · signal']};
const EXHIBIT_REASONS=['NOT_COLLECTED','INDEX_UNAVAILABLE','INDEX_INVALID','NO_EXHIBIT_99_1','EXHIBIT_LINK_INVALID','EXHIBIT_TITLE_INVALID'];
const TOP=['schema_version','kind','as_of','state','reason_codes','freshness_basis','stale_after_seconds','window_days','channel','score_effect','companies','events'];
const EVENT=['company_id','accession','form','filing_date','event_date','accepted_at','items','classification','link','group_id','occurrence','first_seen_at','exhibit_99_1'];
function need(v){if(!v)throw Error('SEC_DISCLOSURES_INVALID');}
const plain=v=>v!==null&&typeof v==='object'&&!Array.isArray(v),keys=(v,k)=>plain(v)&&Object.keys(v).length===k.length&&k.every(n=>Object.hasOwn(v,n));
function instant(v){need(typeof v==='string'&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00$/.test(v));const t=Date.parse(v);need(Number.isFinite(t)&&new Date(t).toISOString().slice(0,19)===v.slice(0,19));return t;}
function day(v){need(typeof v==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&new Date(v+'T00:00:00Z').toISOString().slice(0,10)===v);return Date.parse(v+'T00:00:00Z');}
const utcDay=t=>new Date(t).toISOString().slice(0,10),fresh=(at,cut)=>cut-at>STALE_AFTER*1000?'STALE':'LIVE';
function classify(items){for(const[code,name]of PRIORITY)if(items.includes(code))return name;return 'OTHER';}
function quarterlyEarningsTitle(v){return typeof v==='string'&&/\b(?:q[1-4]|quarterly|(?:first|second|third|fourth)[ -]quarter|[1-4](?:st|nd|rd|th)[ -]quarter)\b/i.test(v)&&/\b(?:results|earnings)\b/i.test(v);}
function classifyReport(form,items){return ['6-K','6-K/A'].includes(form)?'RESULTS':classify(items);}
function qgvEarningsStatus(filingWindow,qgvRow){
 const c=filingWindow?.earnings_confirmation,v=qgvRow?.v_inputs_v2;
 if(!c||!filingWindow.confirmed_earnings_date||qgvRow?.state!=='LIVE'||!v)return{status:'NOT_CONFIRMED',reason:'QUARTER_QG_NOT_REFLECTED'};
 const period=c.period_end;
 if(v.revenue?.ttm_end!==period||v.ebit?.ttm_end!==period)return{status:'NOT_CONFIRMED',reason:'QUARTER_QG_NOT_REFLECTED'};
 return{status:'CONFIRMED',label:'확인',period_end:period,earnings_date:filingWindow.confirmed_earnings_date};
}
function folder(accession){return accession.replaceAll('-','');}
function indexUrl(company,accession){return 'https://www.sec.gov/Archives/edgar/data/'+Number(CIKS[company])+'/'+folder(accession)+'/'+accession+'-index.htm';}
function archivePrefix(company,accession){return 'https://www.sec.gov/Archives/edgar/data/'+Number(CIKS[company])+'/'+folder(accession)+'/';}
// Mirrors Python assign_groups: an 8-K starts its own group (NEW); an 8-K/A joins the single same-company, same-event-date original accepted no later (REPEAT).
function groups(events){const originals=new Map();for(const e of events)if(['8-K','6-K'].includes(e.form)&&e.event_date!==null){const k=e.company_id+'|'+e.event_date+'|'+e.form;if(!originals.has(k))originals.set(k,[]);originals.get(k).push(e);}
 return events.map(e=>{const own=e.company_id+':'+e.accession;if(['8-K','6-K'].includes(e.form))return{group_id:own,occurrence:'NEW'};const m=e.event_date===null?[]:(originals.get(e.company_id+'|'+e.event_date+'|'+e.form.replace('/A',''))||[]).filter(o=>o.accepted_at<=e.accepted_at);return{group_id:m.length===1?m[0].company_id+':'+m[0].accession:own,occurrence:'REPEAT'};});}
function title(v){return typeof v==='string'&&[...v].length>0&&[...v].length<=TITLE_MAX&&!/[\u0000-\u001f<>]/.test(v)&&!v.startsWith(' ')&&!v.endsWith(' ')&&!v.includes('  ');}
function exhibit(e){const x=e.exhibit_99_1;need(plain(x));
 if(x.state==='AVAILABLE'){need(keys(x,['state','title','url','released_at'])&&x.released_at===e.accepted_at&&title(x.title));const prefix=archivePrefix(e.company_id,e.accession);need(typeof x.url==='string'&&x.url.startsWith(prefix)&&/^[A-Za-z0-9][A-Za-z0-9._-]{0,120}\.(?:htm|html|txt|pdf|xml|jpg|gif)$/i.test(x.url.slice(prefix.length)));}
 else need(keys(x,['state','reason_code'])&&x.state==='NOT_AVAILABLE'&&EXHIBIT_REASONS.includes(x.reason_code));}
function validate(p){
 try{
  need(keys(p,TOP)&&p.schema_version===1&&p.kind===KIND&&p.freshness_basis==='SOURCE_ACQUISITION'&&p.channel==='DISCLOSURE'&&p.score_effect==='NONE'&&p.stale_after_seconds===STALE_AFTER&&p.window_days===WINDOW_DAYS);
  const cut=instant(p.as_of),ids=Object.keys(CIKS);need(plain(p.companies)&&Object.keys(p.companies).length===ids.length&&ids.every(id=>Object.hasOwn(p.companies,id)));const acquired={},states=[];
  for(const id of ids){const c=p.companies[id];need(keys(c,['state','acquired_at','reason_code']));if(c.acquired_at===null)need(c.state==='NOT_AVAILABLE'&&c.reason_code==='NOT_COLLECTED');else{const at=instant(c.acquired_at);need(at<=cut&&c.reason_code===null&&c.state===fresh(at,cut));acquired[id]=at;}states.push(c.state);}
  const state=states.includes('LIVE')?'LIVE':states.includes('STALE')?'STALE':'NOT_AVAILABLE';need(p.state===state&&JSON.stringify(p.reason_codes)===JSON.stringify(state==='LIVE'?[]:state==='STALE'?['STALE_INPUT']:['NO_ELIGIBLE_INPUT']));
  const events=p.events;need(Array.isArray(events)&&events.length<=MAX_EVENTS);const cutoff=utcDay(cut-WINDOW_DAYS*86400000),today=utcDay(cut),seen=new Set();
  for(const e of events){need(keys(e,EVENT)&&Object.hasOwn(acquired,e.company_id)&&typeof e.accession==='string'&&/^\d{10}-\d{2}-\d{6}$/.test(e.accession)&&!seen.has(e.accession)&&['8-K','8-K/A','6-K','6-K/A'].includes(e.form));seen.add(e.accession);
   const filed=day(e.filing_date),accepted=instant(e.accepted_at),gap=(filed-Date.parse(utcDay(accepted)+'T00:00:00Z'))/86400000;need(cutoff<=e.filing_date&&e.filing_date<=today&&accepted<=acquired[e.company_id]&&gap>=-1&&gap<=5);
   need(e.event_date===null||day(e.event_date)<=filed);const it=e.items;need(Array.isArray(it)&&it.length<=Object.keys(ITEMS).length&&it.every(i=>typeof i==='string'&&Object.hasOwn(ITEMS,i))&&JSON.stringify(it)===JSON.stringify([...new Set(it)].sort()));
   need(e.classification===classifyReport(e.form,it)&&e.link===indexUrl(e.company_id,e.accession));const seenAt=instant(e.first_seen_at);need(accepted<=seenAt&&seenAt<=cut);exhibit(e);if(['6-K','6-K/A'].includes(e.form))need(e.company_id==='asml'&&it.length===0&&e.exhibit_99_1.state==='AVAILABLE'&&quarterlyEarningsTitle(e.exhibit_99_1.title));}
  for(let i=1;i<events.length;i++){const a=events[i-1],b=events[i];need(a.accepted_at>b.accepted_at||a.accepted_at===b.accepted_at&&a.accession>b.accession);}
  const expected=groups(events);need(events.every((e,i)=>e.group_id===expected[i].group_id&&e.occurrence===expected[i].occurrence));return p;
 }catch(_){throw Error('SEC_DISCLOSURES_INVALID');}
}
async function load(view){const control=new AbortController(),timer=setTimeout(()=>control.abort(),20000);
 try{const r=await view.fetch(FILENAME,{cache:'no-store',credentials:'omit',referrerPolicy:'no-referrer',redirect:'error',signal:control.signal});if(!r.ok)return null;const text=await r.text();if(new TextEncoder().encode(text).length>MAX)return null;return validate(JSON.parse(text));}
 catch(_){return null;}finally{clearTimeout(timer);}}
// One chronological list (newest first). News items (channel NEWS, later) join the same list by time; nothing changes scores.
function timeline(payload,{companyIds=null,news=[]}={}){const rows=(payload?.events||[]).filter(e=>!companyIds||companyIds.includes(e.company_id)).map(e=>({channel:'DISCLOSURE',time:e.accepted_at,company_id:e.company_id,event:e}));
 for(const n of news)if(n&&n.channel==='NEWS'&&typeof n.time==='string'&&(!companyIds||companyIds.includes(n.company_id)))rows.push(n);return rows.sort((a,b)=>a.time<b.time?1:a.time>b.time?-1:0);}
function itemLabel(code,en){const [e,k]=ITEMS[code];return en?code+' '+e+' ('+k+')':code+' '+k+' ('+e+')';}
// The four highlighted kinds use short labels; any other report is labelled by its first official item name (9.01 exhibits last).
function classLabel(name,en,items=[]){const first=name==='OTHER'?items.find(c=>c!=='9.01')||items[0]:null;if(first){const [e,k]=ITEMS[first];return en?e+' ('+k+')':k+' ('+e+')';}const [k,e]=CLASSES[name];return en?e+' ('+k+')':k+' ('+e+')';}
// One 8-K row (also used by NewsSignals.mount for the combined '공시·확정'/'뉴스·신호' list).
function renderRow(doc,e,en){const T=(k,x)=>en?x:k,el=(tag,text,attrs={})=>{const n=doc.createElement(tag);if(text!==undefined)n.textContent=text;for(const[k,v]of Object.entries(attrs))n.setAttribute(k,v);return n;};
 const li=el('li',undefined,{class:'card','data-disclosure':e.accession,'data-occurrence':e.occurrence,'data-classification':e.classification});
  const head=el('p',undefined,{class:'chips'});head.append(el('span',CHANNELS.DISCLOSURE[en?1:0],{class:'badge LIVE','data-channel':'DISCLOSURE'}),el('span',e.occurrence==='NEW'?T('새 공시','New'):T('정정·반복','Repeat / amendment'),{class:'badge','data-occurrence-label':e.occurrence}),el('span',classLabel(e.classification,en,e.items),{class:'badge','data-classification-label':e.classification}));li.append(head);
  const who=el('p');who.append(el('a',e.company_id.toUpperCase(),{href:'#company/'+encodeURIComponent(e.company_id)}),doc.createTextNode(' · '+e.form+' · '+e.accepted_at.slice(0,16).replace('T',' ')+' UTC'));li.append(who);
  const x=e.exhibit_99_1;if(x.state==='AVAILABLE'){const t=el('p');t.append(el('a',x.title,{href:x.url,target:'_blank',rel:'noopener noreferrer','data-exhibit-link':''}),doc.createTextNode(' · EX-99.1'));li.append(t);}
  else li.append(el('p','EX-99.1 · NOT_AVAILABLE · '+x.reason_code,{class:'small'}));
  li.append(el('p',e.items.map(c=>itemLabel(c,en)).join(' / ')||(['6-K','6-K/A'].includes(e.form)?T('분기 실적 6-K · 공시 첨부 제목 확인','Quarterly earnings 6-K · filing exhibit title verified'):T('항목 미제공','Items not provided')),{class:'small','data-items':e.items.join(',')}));
  li.append(el('a',T('SEC 원문 목록 보기 ↗','Open SEC filing index ↗'),{href:e.link,target:'_blank',rel:'noopener noreferrer','data-filing-link':''}));
 return li;}
function mount(host,payload,{locale,companyIds=null,limit=30,emptyText}={}){
 if(!host)return;const doc=host.ownerDocument,en=locale==='en-US',T=(k,e)=>en?e:k,el=(tag,text,attrs={})=>{const n=doc.createElement(tag);if(text!==undefined)n.textContent=text;for(const[k,v]of Object.entries(attrs))n.setAttribute(k,v);return n;};
 const section=el('section',undefined,{class:'card','data-sec-disclosures':''});section.append(el('h2',T('공시·확정 · SEC 8-K','Disclosures · confirmed · SEC 8-K')));
 const state=payload?payload.state:'NOT_AVAILABLE';section.append(el('p',state,{class:'badge '+state,'data-disclosure-state':state}));
 if(!payload){section.append(el('p',T('공개 공시 자료가 연결되지 않았습니다.','Public disclosure data is not connected.'),{class:'empty'}));host.replaceChildren(section);return;}
 if(state!=='NOT_AVAILABLE'&&Date.now()-Date.parse(payload.as_of)>payload.stale_after_seconds*1000)section.append(el('p','STALE · '+T('수집 갱신 시각 경과','Acquisition refresh overdue'),{class:'warning','data-disclosure-stale':''}));
 section.append(el('p',T('기준: ','As of: ')+payload.as_of+' · '+T('최근 '+payload.window_days+'일','last '+payload.window_days+' days'),{class:'meta'}),el('p',T('점수에 반영하지 않음 · 제목·링크·시각·기업·분류만 표시','Never changes scores · title, link, time, company and classification only'),{class:'small','data-score-effect':payload.score_effect}));
 const rows=timeline(payload,{companyIds}).slice(0,limit);
 if(!rows.length){section.append(el('p',emptyText||T('표시할 공시가 없습니다.','No disclosures to show.'),{class:'empty'}));host.replaceChildren(section);return;}
 const list=el('ol',undefined,{class:'list','data-disclosure-list':''});
 for(const row of rows)list.append(renderRow(doc,row.event,en));
 section.append(list);host.replaceChildren(section);
}
return Object.freeze({FILENAME,KIND,CIKS,ITEMS,CLASSES,CHANNELS,PRIORITY,classify,classLabel,qgvEarningsStatus,groups,indexUrl,validate,load,timeline,renderRow,mount});
});
