/* Price-free SEC observations: validate inputs, display fixed notices only. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.SecReported=api;})(typeof globalThis==='object'?globalThis:this,function(){
 'use strict';
 const MAX=2*1024*1024;
 const CIKS={amd:'0000002488',amzn:'0001018724',asml:'0000937966',avgo:'0001730168',etn:'0001551182',gev:'0001996810',googl:'0001652044',hubb:'0000048898',intc:'0000050863',klac:'0000319201',lrcx:'0000707549',msft:'0000789019',nvda:'0001045810',qcom:'0000804328',rok:'0001024478',rtx:'0000101829',stry:'0000310764'};
 const EXCLUDED=new Set(['FORM_NOT_ALLOWED','UNIT_MISMATCH','DATE_INVALID','DATE_AFTER_ACQUISITION','VALUE_INVALID','FACT_SCHEMA_INVALID','ACCESSION_INVALID','PERIOD_METADATA_INVALID','CLASS_SPLIT','FACT_CONFLICT','UNKNOWN_DIMENSION','FILING_DATE_INVALID','FILING_TIMESTAMP_INVALID','FILING_ACCESSION_INVALID','FILING_REPORT_DATE_INVALID','FILING_AFTER_ACQUISITION','FILING_SCHEMA_INVALID']);
 const FIXED=new Set(["SEC_ACQUISITION_TIMESTAMP_INVALID", "SEC_CIK_MISMATCH", "SEC_CLOCK_INVALID", "SEC_COLLECTION_FAILED", "SEC_CONFIG_INVALID", "SEC_FACT_ACCESSION_INVALID", "SEC_FACT_AFTER_ACQUISITION", "SEC_FACT_DATE_INVALID", "SEC_FACT_FORM_UNSUPPORTED", "SEC_FACT_PERIOD_METADATA_INVALID", "SEC_FILING_ACCESSION_INVALID", "SEC_FILING_AFTER_ACQUISITION", "SEC_FILING_DATE_INVALID", "SEC_FILING_REPORT_DATE_INVALID", "SEC_FILING_TIMESTAMP_INVALID", "SEC_HTTP_RETRIES_EXHAUSTED", "SEC_ISSUER_NOT_ALLOWED", "SEC_JSON_INVALID", "SEC_MODULE_NOT_MERGED", "SEC_NO_ELIGIBLE_SHARE_FACTS", "SEC_PUBLIC_INPUT_INVALID", "SEC_REDIRECT_REJECTED", "SEC_RESPONSE_INVALID", "SEC_RESPONSE_TOO_LARGE", "SEC_RESPONSE_URL_MISMATCH", "SEC_RETRY_AFTER_EXCEEDS_BUDGET", "SEC_SHARE_CONCEPT_MISSING", "SEC_SHARE_SCHEMA_INVALID", "SEC_SHARE_UNIT_MISMATCH", "SEC_SHARE_VALUE_INVALID", "SEC_SLEEP_FAILED", "SEC_SOURCE_METADATA_INVALID", "SEC_SUBMISSIONS_SCHEMA_INVALID", "SEC_TRANSPORT_FAILED", "SEC_TRANSPORT_RETRIES_EXHAUSTED", "SEC_URL_NOT_ALLOWED", "SEC_USER_AGENT_INVALID", "SEC_USER_AGENT_MISSING"]);
 const FORMS=new Set(['10-K','10-Q','10-K/A','10-Q/A','10-KT','10-QT','10-KT/A','10-QT/A','20-F','20-F/A','40-F','40-F/A','6-K','6-K/A','8-K','8-K/A']);
 function need(value){if(!value)throw Error('SEC_PUBLIC_INPUT_INVALID');}
 function object(value){return value!==null&&typeof value==='object'&&!Array.isArray(value);}
 function keys(value,required,optional=[]){need(object(value));need(required.every(k=>Object.hasOwn(value,k))&&Object.keys(value).every(k=>required.includes(k)||optional.includes(k)));}
 function day(value){need(typeof value==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(value));need(Number(value.slice(0,4))>0);const d=new Date(value+'T00:00:00Z');need(Number.isFinite(+d)&&d.toISOString().slice(0,10)===value);return value;}
 function clock(value){need(typeof value==='string'&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$/.test(value));day(value.slice(0,10));need(Number(value.slice(11,13))<24&&Number(value.slice(14,16))<60&&Number(value.slice(17,19))<60);const stamp=Date.parse(value);need(Number.isFinite(stamp)&&stamp<=Date.now());return stamp;}
 function accession(value){need(typeof value==='string'&&/^\d{10}-\d{2}-\d{6}$/.test(value));}
 function fixed(value){return typeof value==='string'&&(FIXED.has(value)||/^SEC_HTTP_[45]\d{2}$/.test(value));}
 function project(payload){
  keys(payload,['schema','scope','companies']);need(['public-sec-reported-inputs/1','public-sec-reported-inputs/2','public-sec-reported-inputs/3'].includes(payload.schema)&&payload.scope==='US_TARGET17_REPORTED_SEC_ONLY');
  need(new TextEncoder().encode(JSON.stringify(payload)).length<=MAX);
  const version=Number(payload.schema.slice(-1)),ids=Object.keys(CIKS),out={schema:payload.schema,companies:{}};
  need(Array.isArray(payload.companies)&&payload.companies.length===ids.length);
  for(const [index,row] of payload.companies.entries()){
   need(object(row)&&row.company_id===ids[index]&&row.cik===CIKS[row.company_id]);
   let counts={},notice=null,basis=null;
   const extra=version===3?['excluded_fact_counts','share_class_basis','share_class_notice']:[];
   if(version===3){need(object(row.excluded_fact_counts));for(const [reason,count] of Object.entries(row.excluded_fact_counts)){need(EXCLUDED.has(reason)&&Number.isInteger(count)&&count>0&&count<=100000);counts[reason]=count;}need(row.share_class_basis==='UNCONFIRMED');basis=row.share_class_basis;notice=counts.CLASS_SPLIT?'SHARE_CLASS_BASIS':null;need(row.share_class_notice===notice);}
   const unavailable=version>=2&&row.status==='NOT_AVAILABLE';
   const summary={company_id:row.company_id,status:unavailable?'NOT_AVAILABLE':'LIVE',excluded_fact_counts:counts,share_class_basis:basis,share_class_notice:notice,reason_codes:[],acquired_at:null};
   if(unavailable){
    keys(row,['company_id','cik','status','reason_codes','failure_stage','company_index','http_status',...extra]);need(row.company_index===index+1&&['fetch','parse','normalize'].includes(row.failure_stage));need(Array.isArray(row.reason_codes)&&row.reason_codes.length===1&&fixed(row.reason_codes[0]));need(row.http_status===null||(Number.isInteger(row.http_status)&&row.http_status>=400&&row.http_status<=599));summary.reason_codes=[...row.reason_codes];out.companies[row.company_id]=summary;continue;
   }
   keys(row,['company_id','cik','acquired_at','sources','reported_shares','filings',...(version>=2?['status']:[]),...extra]);if(version>=2)need(row.status==='LIVE');const acquired=clock(row.acquired_at),asOf=row.acquired_at.slice(0,10);
   keys(row.sources,['companyfacts','submissions']);for(const kind of ['companyfacts','submissions']){const source=row.sources[kind];keys(source,['url','sha256']);need(source.url===('https://data.sec.gov/'+(kind==='companyfacts'?'api/xbrl/companyfacts/CIK':'submissions/CIK')+row.cik+'.json')&&typeof source.sha256==='string'&&/^[0-9a-f]{64}$/.test(source.sha256));}
   need(Array.isArray(row.reported_shares)&&row.reported_shares.length<=10000&&(version<3||row.reported_shares.length>0));const facts=new Map();
   for(const fact of row.reported_shares){
    keys(fact,['namespace','concept','unit','end','val','accn','form','filed'],['start','fy','fp','frame']);need(['dei:EntityCommonStockSharesOutstanding','us-gaap:CommonStockSharesOutstanding','ifrs-full:NumberOfSharesOutstanding'].includes(fact.namespace+':'+fact.concept)&&fact.unit==='shares'&&FORMS.has(fact.form));need(typeof fact.val==='number'&&Number.isFinite(fact.val)&&fact.val>0&&fact.val<=Number.MAX_SAFE_INTEGER);need(day(fact.end)<=asOf&&day(fact.filed)<=asOf);accession(fact.accn);
    if(Object.hasOwn(fact,'start'))need(day(fact.start)<=fact.end);if(Object.hasOwn(fact,'fy'))need(Number.isInteger(fact.fy)&&fact.fy>=1900&&fact.fy<=9999);if(Object.hasOwn(fact,'fp'))need(['FY','Q1','Q2','Q3','Q4'].includes(fact.fp));if(Object.hasOwn(fact,'frame'))need(typeof fact.frame==='string'&&/^CY\d{4}(?:Q[1-4])?I?$/.test(fact.frame));
    const key=JSON.stringify(['namespace','concept','unit','end','accn','form','filed'].map(k=>fact[k]));need(!facts.has(key)||facts.get(key)===fact.val);facts.set(key,fact.val);
   }
   need(Array.isArray(row.filings)&&row.filings.length<=10000);for(const filing of row.filings){keys(filing,['accession','form','filed','report_date','accepted_at']);accession(filing.accession);need(FORMS.has(filing.form)&&day(filing.filed)<=asOf&&clock(filing.accepted_at)<=acquired);need(filing.report_date===null||day(filing.report_date)<=asOf);}
   summary.acquired_at=row.acquired_at;out.companies[row.company_id]=summary;
  }
  return out;
 }
 async function load(view){
  const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),20000);
  try{const response=await view.fetch('sec-public-inputs.json',{cache:'no-store',credentials:'omit',referrerPolicy:'no-referrer',redirect:'error',signal:controller.signal});if(!response.ok)return null;let text;
   if(response.body&&response.body.getReader){const reader=response.body.getReader(),decoder=new TextDecoder('utf-8',{fatal:true});let size=0;const chunks=[];try{while(true){const part=await reader.read();if(part.done)break;size+=part.value.byteLength;if(size>MAX){await reader.cancel();return null;}chunks.push(decoder.decode(part.value,{stream:true}));}chunks.push(decoder.decode());text=chunks.join('');}finally{reader.releaseLock();}}
   else{text=await response.text();if(new TextEncoder().encode(text).length>MAX)return null;}
   return project(JSON.parse(text));
  }catch(_){return null;}finally{clearTimeout(timeout);}
 }
 function mount(host,data,options={}){
  if(!host)return;const en=options.locale==='en-US',doc=host.ownerDocument,el=(tag,text,attrs={})=>{const node=doc.createElement(tag);if(text!==undefined)node.textContent=text;for(const [k,v] of Object.entries(attrs))node.setAttribute(k,v);return node;};
  const card=el('section',undefined,{class:'card','data-sec-reported':''});card.append(el('h2',en?'SEC reported inputs':'SEC 공개 입력'),el('p',en?'Reported observations · No prices · No share-class corrections':'공시 원자료 · 가격 미포함 · 주식 종류 보정 없음',{class:'small'}));
  const rows=options.companyId?(data?.companies[options.companyId]?[data.companies[options.companyId]]:[]):Object.values(data?.companies||{}).filter(r=>!options.companyIds||options.companyIds.includes(r.company_id));
  if(!rows.length)card.append(el('p',en?'NOT_AVAILABLE · SEC input is not connected.':'NOT_AVAILABLE · SEC 공개 입력이 연결되지 않았습니다.',{class:'empty','data-sec-unavailable':''}));
  for(const row of rows){const article=el('article',undefined,{'data-sec-company':row.company_id});const link=el('a',row.company_id.toUpperCase(),{href:'#company/'+encodeURIComponent(row.company_id)});article.append(link,el('p',row.status+(row.reason_codes.length?' · '+row.reason_codes.join(' · '):'')));
   if(row.acquired_at)article.append(el('p',(en?'Acquired: ':'수집: ')+row.acquired_at,{class:'meta'}));
   if(row.share_class_basis)article.append(el('p',en?'Share-class basis unconfirmed · No summing or correction':'주식 종류 기준 미확인 · 합산·보정하지 않음',{'data-sec-basis':'UNCONFIRMED',class:'small'}));
   if(row.share_class_notice)article.append(el('p','SHARE_CLASS_BASIS · '+(en?'Class-specific share facts were excluded.':'종류별 주식 수 자료를 제외했습니다.'),{'data-sec-notice':'SHARE_CLASS_BASIS',class:'badge'}));
   const entries=Object.entries(row.excluded_fact_counts).sort(([a],[b])=>a.localeCompare(b));if(entries.length){article.append(el('h3',en?'Excluded rows by reason':'제외 사유별 개수'));const list=el('ul');for(const [reason,count] of entries)list.append(el('li',reason+' · '+count,{'data-sec-excluded':reason}));article.append(list);}
   else article.append(el('p',en?(data.schema.endsWith('/3')?'Excluded rows: 0':'Exclusion counts: NOT_AVAILABLE (older input)'):(data.schema.endsWith('/3')?'제외 개수: 0':'제외 개수: NOT_AVAILABLE (이전 입력)'),{class:'small'}));card.append(article);
  }
  host.replaceChildren(card);
 }
 return Object.freeze({project,load,mount});
});
