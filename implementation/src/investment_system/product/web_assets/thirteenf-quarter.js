/* S16 13F quarter-over-quarter view. Reported quantity changes only (never values, prices or trades).
   TARGET CUSIPs come only from the published actual-catalog.json ISINs (US ISIN = "US" + CUSIP + check digit);
   anything the public files do not carry stays NOT_AVAILABLE with a fixed reason. Python reference:
   investment_system/product/thirteenf_quarter.py (tests/fixtures/s16_s13_reference_v1.json). */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.ThirteenFQuarter=api;})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
const TARGET=Object.freeze([['asml','ASML'],['lrcx','LRCX'],['klac','KLAC'],['tokyo_electron','8035'],['hanmi','042700'],['nvda','NVDA'],['amd','AMD'],['avgo','AVGO'],['qcom','QCOM'],['intc','INTC'],['msft','MSFT'],['googl','GOOGL'],['amzn','AMZN'],['rtx','RTX'],['stry','SYK'],['etn','ETN'],['hubb','HUBB'],['gev','GEV'],['rok','ROK']].map(x=>Object.freeze(x)));
const KINDS=Object.freeze(['NEW','ADD','REDUCE','EXIT']);
// Fields the public sec-13f-changes.json does not carry: shown as NOT_AVAILABLE with these reasons.
const GAPS=Object.freeze({filed_date:'FILING_DATE_NOT_PUBLISHED',holdings_count:'UNCHANGED_POSITIONS_NOT_PUBLISHED',top10_weight:'REPORTED_VALUES_NOT_PUBLISHED',issuer_name:'ISSUER_NAME_NOT_PUBLISHED'});
function charValue(ch){if(ch>='0'&&ch<='9')return ch.charCodeAt(0)-48;if(ch>='A'&&ch<='Z')return ch.charCodeAt(0)-55;return ch==='*'?36:ch==='@'?37:ch==='#'?38:-1;}
function cusipValid(c){if(typeof c!=='string'||!/^[0-9A-Z*@#]{8}[0-9]$/.test(c))return false;let sum=0;for(let i=0;i<8;i++){let v=charValue(c[i]);if(i%2===1)v*=2;sum+=Math.floor(v/10)+v%10;}return (10-sum%10)%10===Number(c[8]);}
function isinValid(isin){if(typeof isin!=='string'||!/^[A-Z]{2}[0-9A-Z]{9}[0-9]$/.test(isin))return false;const digits=[...isin].map(ch=>String(charValue(ch))).join('');let sum=0;for(let i=0;i<digits.length;i++){let d=Number(digits[digits.length-1-i]);if(i%2===1){d*=2;if(d>9)d-=9;}sum+=d;}return sum%10===0;}
// ISO 6166: a US ISIN embeds the 9-character CUSIP. Any other country prefix does not, so it yields null.
function cusipFromIsin(isin){if(!isinValid(isin)||isin.slice(0,2)!=='US')return null;const c=isin.slice(2,11);return cusipValid(c)?c:null;}
function targetSecurities(catalog){const list=catalog&&Array.isArray(catalog.instruments)?catalog.instruments:null;
 return TARGET.map(([id,ticker])=>{const found=list?list.filter(i=>i&&i.ticker===ticker):[],inst=found.length===1?found[0]:null,label=inst&&typeof inst.label==='string'?inst.label:null;
  if(!inst)return{company_id:id,ticker,label,cusip:null,reason:'CATALOG_NOT_AVAILABLE'};const ref=inst.security_reference||{};
  if(ref.scheme==='EXCHANGE_CODE')return{company_id:id,ticker,label,cusip:null,reason:'NOT_13F_SECURITY'};
  const cusip=ref.scheme==='ISIN'?cusipFromIsin(ref.value):null;return{company_id:id,ticker,label,cusip,reason:cusip?null:'CUSIP_NOT_IN_PUBLIC_CATALOG'};});}
const quantity=c=>({kind:c.kind,unit:c.unit,reported_before:c.reported_before,reported_after:c.reported_after,reported_delta:c.reported_delta});
// One manager report: counts, TARGET rows (changed / no reported change / NOT_AVAILABLE) and other holdings by CUSIP.
function summarizeReport(report,targets){const counts={NEW:0,ADD:0,REDUCE:0,EXIT:0},changes=Array.isArray(report.changes)?report.changes:[],byCusip=new Map();
 for(const c of changes){if(Object.hasOwn(counts,c.kind))counts[c.kind]++;if(!byCusip.has(c.cusip))byCusip.set(c.cusip,[]);byCusip.get(c.cusip).push(c);}
 const comparable=report.state!=='NOT_AVAILABLE',mapped=new Set(targets.filter(t=>t.cusip).map(t=>t.cusip));
 const target=targets.map(t=>{if(t.reason)return{company_id:t.company_id,cusip:t.cusip,status:'NOT_AVAILABLE',reason:t.reason,changes:[],multiple_buckets:false};
  if(!comparable)return{company_id:t.company_id,cusip:t.cusip,status:'NOT_AVAILABLE',reason:'COMPARISON_NOT_AVAILABLE',changes:[],multiple_buckets:false};
  const rows=byCusip.get(t.cusip)||[];return{company_id:t.company_id,cusip:t.cusip,status:rows.length?'CHANGED':'NO_REPORTED_CHANGE',reason:null,changes:rows.map(quantity),multiple_buckets:rows.length>1};});
 const other=changes.filter(c=>!mapped.has(c.cusip)).map((c,i)=>({c,i})).sort((a,b)=>a.c.cusip<b.c.cusip?-1:a.c.cusip>b.c.cusip?1:a.i-b.i).map(({c})=>({cusip:c.cusip,...quantity(c)}));
 return{manager_cik:report.manager_cik,previous_quarter:report.previous_quarter,current_quarter:report.current_quarter,state:report.state,
  filed_date:null,filed_date_reason:GAPS.filed_date,holdings_count:null,holdings_count_reason:GAPS.holdings_count,top10_weight:null,top10_weight_reason:GAPS.top10_weight,
  counts,change_count:changes.length,target,other};}
// TARGET company view across managers: who reported a NEW/ADD/REDUCE/EXIT quantity change in their latest comparison.
function targetOverlap(summaries,targets){return targets.map(t=>{if(t.reason)return{company_id:t.company_id,cusip:t.cusip,status:'NOT_AVAILABLE',reason:t.reason,entries:[],unchanged:[],not_available:[]};
 const entries=[],unchanged=[],na=[];for(const s of summaries){const row=s.target.find(r=>r.company_id===t.company_id);if(!row||row.status==='NOT_AVAILABLE'){na.push(s.manager_cik);continue;}
  if(row.status==='NO_REPORTED_CHANGE'){unchanged.push(s.manager_cik);continue;}for(const c of row.changes)entries.push({manager_cik:s.manager_cik,current_quarter:s.current_quarter,...c});}
 const status=entries.length?'CHANGED':unchanged.length?'NO_REPORTED_CHANGE':'NOT_AVAILABLE';return{company_id:t.company_id,cusip:t.cusip,status,reason:status==='NOT_AVAILABLE'?'NO_COMPARABLE_REPORT':null,entries,unchanged,not_available:na};});}
// ---- Rendering (DOM only; numbers are reported share/principal quantities, never amounts) ----
const KIND_TEXT={NEW:['신규','New'],ADD:['추가','Added'],REDUCE:['축소','Reduced'],EXIT:['전량매도(보고 0)','Exited (reported 0)']};
const REASON_TEXT={NOT_13F_SECURITY:['13F 대상 아님','Not a 13F security'],CUSIP_NOT_IN_PUBLIC_CATALOG:['공개 목록에 CUSIP 없음','CUSIP not in the public catalog'],CATALOG_NOT_AVAILABLE:['공개 목록 미연결','Public catalog not loaded'],COMPARISON_NOT_AVAILABLE:['분기 비교 불가','Quarter comparison unavailable'],NO_COMPARABLE_REPORT:['비교 가능한 보고서 없음','No comparable report'],FILING_DATE_NOT_PUBLISHED:['공개 파일에 제출일 없음','Filed date not in the public file'],UNCHANGED_POSITIONS_NOT_PUBLISHED:['공개 파일은 변화 항목만 담음','Public file lists changes only'],REPORTED_VALUES_NOT_PUBLISHED:['금액 미게시·가격 환산 안 함','Values not published; no price conversion']};
const reasonText=(code,en)=>code+(REASON_TEXT[code]?' · '+REASON_TEXT[code][en?1:0]:'');
const kindText=(kind,en)=>(KIND_TEXT[kind]||[kind,kind])[en?1:0];
const qty=n=>Number.isSafeInteger(n)?n.toLocaleString('en-US'):'—';
const signed=n=>Number.isSafeInteger(n)?(n>0?'+':n<0?'−':'')+Math.abs(n).toLocaleString('en-US'):'—';
function table(el,heads,rows,attrs){const wrap=el('div',undefined,{class:'table-wrap'}),t=el('table',undefined,attrs),thead=el('thead'),head=el('tr'),body=el('tbody');for(const h of heads)head.append(el('th',h,{scope:'col'}));thead.append(head);for(const r of rows)body.append(r);t.append(thead,body);wrap.append(t);return wrap;}
function renderReport(article,s,{el,en,labelOf=id=>id.toUpperCase()}){
 article.append(el('p',(en?'Period ':'기준 분기 ')+s.previous_quarter+' → '+s.current_quarter+' · '+s.state,{class:'small','data-13f-period':s.current_quarter}));
 article.append(el('p',(en?'Filed date ':'제출일 ')+'NOT_AVAILABLE · '+reasonText(s.filed_date_reason,en),{class:'small','data-13f-filed':''}));
 const cells=el('dl',undefined,{class:'kv','data-13f-cells':''});
 for(const[label,value,attr]of [[en?'Holdings':'종목 수','NOT_AVAILABLE · '+reasonText(s.holdings_count_reason,en),'holdings'],[en?'Top-10 weight':'상위 10 비중','NOT_AVAILABLE · '+reasonText(s.top10_weight_reason,en),'top10'],[kindText('NEW',en),String(s.counts.NEW),'NEW'],[kindText('EXIT',en),String(s.counts.EXIT),'EXIT']])cells.append(el('dt',label),el('dd',value,{'data-13f-cell':attr}));
 article.append(cells);
 const chips=el('div',undefined,{class:'chips','data-13f-kind-chips':''});for(const k of KINDS)chips.append(el('span',kindText(k,en)+' '+s.counts[k],{class:'badge','data-13f-kind':k}));article.append(chips);
 const changed=s.target.filter(r=>r.status==='CHANGED'),quiet=s.target.filter(r=>r.status==='NO_REPORTED_CHANGE'),na=s.target.filter(r=>r.status==='NOT_AVAILABLE');
 const box=el('div',undefined,{class:'subcard','data-13f-target':s.manager_cik});box.append(el('h4',en?'TARGET companies':'TARGET 종목'));
 if(changed.length){const rows=[];for(const r of changed)for(const c of r.changes){const tr=el('tr',undefined,{'data-13f-target-row':r.company_id,'data-13f-kind':c.kind});for(const v of [labelOf(r.company_id),kindText(c.kind,en),qty(c.reported_before)+' → '+qty(c.reported_after)+' '+c.unit,signed(c.reported_delta)])tr.append(el('td',v));rows.push(tr);}
  box.append(table(el,[en?'Company':'기업',en?'Change':'구분',en?'Reported before → after':'보고 수량 이전 → 현재',en?'Δ quantity':'수량 변화'],rows,{'data-13f-target-table':s.manager_cik}));
  if(changed.some(r=>r.multiple_buckets))box.append(el('p',en?'Several reported lines share one CUSIP (options, discretion or attribution); they are listed separately, never summed.':'같은 CUSIP에 보고 구분(옵션·재량·귀속)이 여러 개라 따로 표시하고 합산하지 않습니다.',{class:'small','data-13f-multi':''}));}
 else if(s.state!=='NOT_AVAILABLE')box.append(el('p',en?'No reported change in TARGET companies.':'TARGET 종목의 보고 수량 변화가 없습니다.',{class:'small','data-13f-target-none':''}));
 if(quiet.length)box.append(el('p',(en?'No reported change (unchanged or not held — the public file lists changes only): ':'보고 변화 없음(변동 없음 또는 미보유 — 공개 파일은 변화만 담음): ')+quiet.map(r=>labelOf(r.company_id)).join(', '),{class:'small','data-13f-target-quiet':''}));
 const groups=new Map();for(const r of na){if(!groups.has(r.reason))groups.set(r.reason,[]);groups.get(r.reason).push(labelOf(r.company_id));}
 for(const[reason,names]of groups)box.append(el('p','NOT_AVAILABLE · '+reasonText(reason,en)+': '+names.join(', '),{class:'small','data-13f-target-na':reason}));
 article.append(box);
 if(s.other.length){const details=el('details',undefined,{'data-13f-other':s.manager_cik}),rows=s.other.map(c=>{const tr=el('tr',undefined,{'data-13f-other-row':c.cusip});for(const v of [c.cusip,kindText(c.kind,en),qty(c.reported_before)+' → '+qty(c.reported_after)+' '+c.unit,signed(c.reported_delta)])tr.append(el('td',v));return tr;});
  details.append(el('summary',(en?'Other holdings changes ':'그 밖의 보유 변화 ')+s.other.length),el('p',(en?'CUSIP only · ':'CUSIP만 표시 · ')+'NOT_AVAILABLE · '+reasonText(GAPS.issuer_name,en),{class:'small'}),table(el,['CUSIP',en?'Change':'구분',en?'Reported before → after':'보고 수량 이전 → 현재',en?'Δ quantity':'수량 변화'],rows,{'data-13f-other-table':s.manager_cik}));article.append(details);}}
function renderOverlap(section,overlap,{el,en,nameOf=c=>c,labelOf=id=>id.toUpperCase(),interests=[]}){
 const mine=new Set(Array.isArray(interests)?interests:[]),changed=overlap.filter(r=>r.status==='CHANGED'),entries=changed.reduce((n,r)=>n+r.entries.length,0),liked=changed.filter(r=>mine.has(r.company_id));
 const cells=el('dl',undefined,{class:'kv','data-13f-overlap':''});
 cells.append(el('dt',en?'My TARGET':'내 목표(TARGET)'),el('dd',changed.length+(en?' companies · ':'개 기업 · ')+entries+(en?' changes':'건'),{'data-13f-overlap-target':String(changed.length)}),
  el('dt',en?'My watchlist':'관심 종목'),el('dd',mine.size?liked.length+(en?' companies':'개 기업'):(en?'No watchlist companies on this device':'이 기기에 관심 기업 없음'),{'data-13f-overlap-watch':String(liked.length)}));section.append(cells);
 section.append(el('p',en?'Reported quantity changes in the latest comparable quarter; not trades, current holdings or signals. Tokyo Electron and Hanmi Semiconductor are not 13F securities.':'최근 비교 분기의 보고 수량 변화입니다. 실제 매매·현재 보유·신호가 아닙니다. 도쿄일렉트론·한미반도체는 13F 대상이 아닙니다.',{class:'small'}));
 const rows=[];for(const r of overlap){const star=mine.has(r.company_id)?'★ ':'';
  if(r.status==='CHANGED'){for(const e of r.entries){const tr=el('tr',undefined,{'data-13f-overlap-row':r.company_id,'data-13f-kind':e.kind});for(const v of [star+labelOf(r.company_id),nameOf(e.manager_cik),kindText(e.kind,en),qty(e.reported_before)+' → '+qty(e.reported_after)+' '+e.unit,signed(e.reported_delta),e.current_quarter])tr.append(el('td',v));rows.push(tr);}continue;}
  const tr=el('tr',undefined,{'data-13f-overlap-row':r.company_id,'data-13f-overlap-status':r.status});const text=r.status==='NO_REPORTED_CHANGE'?(en?'No reported change':'보고 변화 없음'):'NOT_AVAILABLE · '+reasonText(r.reason,en);
  for(const v of [star+labelOf(r.company_id),'—',text,'—','—','—'])tr.append(el('td',v));rows.push(tr);}
 section.append(table(el,[en?'Company':'기업',en?'Investor':'투자자',en?'Change':'구분',en?'Reported before → after':'보고 수량 이전 → 현재',en?'Δ quantity':'수량 변화',en?'Quarter':'기준 분기'],rows,{'data-13f-overlap-table':''}));}
return Object.freeze({TARGET,KINDS,GAPS,cusipValid,isinValid,cusipFromIsin,targetSecurities,summarizeReport,targetOverlap,renderReport,renderOverlap});
});
