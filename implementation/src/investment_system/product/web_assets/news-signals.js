/* Public `news-signals.json` reader ('뉴스·신호': GDELT DOC 2.0 + company IR feeds). Mirrors Python product/news_signals.
   One chronological list with '공시·확정' (SEC 8-K, DART when present): distinct badges, new/repeat markers, GDELT attribution,
   IR releases that repeat an 8-K Exhibit 99.1 collapsed under that 8-K. Title, link, time, company and classification only;
   nothing changes any score. DOM is built with textContent only.
   Schema 2 adds this run's result per company and a `refresh` summary per source: the card says, per source and for the
   companies in view, '새 뉴스 반영' / '새 뉴스 없음 · 확인 <time>' (request answered) or '이전 자료 유지 · 마지막 성공 <time> ·
   최근 갱신 실패(<source> <code>, <time>)' (request failed or not made). Carried items stay listed with their own times.
   Schema 1 copies stay readable (result not recorded). */
(function(root,factory){const api=factory(root);if(typeof module==='object'&&module.exports)module.exports=api;else root.NewsSignals=api;})(typeof globalThis==='object'?globalThis:this,function(root){
'use strict';
const FILENAME='news-signals.json',KIND='NEWS_SIGNALS',MAX=1024*1024,WINDOW_DAYS=14,STALE_AFTER=172800,MAX_ITEMS=1500,TITLE_MAX=200,LINK_MAX=600,HOUR=3600000;
const MATCHING_RULE='TITLE_NAME_OR_TICKER_V0',GROUP_WINDOW=72*HOUR,GROUP_MIN_SHARED=3,GROUP_MIN_PERCENT=50,PER_COMPANY_MAX={GDELT:40,IR:30};
const SOURCES=['GDELT','IR'],CLASSIFICATIONS=['EARNINGS','PRODUCT','MA','LEGAL','OTHER'];
// GDELT matching rule v0 [names (normalized phrases), case-sensitive symbols, exclusion phrases] (mirrors news_signals.MATCH).
const MATCH={amd:[['advanced micro devices'],['AMD'],['macular','degeneration']],
 amzn:[['amazon com','amazon web services'],['Amazon','AMZN','AWS'],['rainforest','deforestation','amazon river','amazon basin','amazon forest','amazonia','indigenous','amazon fires']],
 asml:[['asml'],[],[]],avgo:[['broadcom'],['AVGO'],[]],
 etn:[['eaton corp','eaton corporation'],['Eaton','ETN'],['eaton vance','eaton fire','eaton canyon','eaton centre','eaton center']],
 gev:[['ge vernova'],['GEV'],[]],googl:[['alphabet','google'],['GOOGL','GOOG'],['alphabet soup']],hanmi:[['hanmi semiconductor'],[],[]],
 hubb:[['hubbell'],['HUBB'],[]],intc:[['intel corp','intel corporation'],['Intel','INTEL','INTC'],['intel officials','military intel','intel chief','intel community','us intel','intel report','intel agencies','intel sharing']],
 klac:[['kla corp','kla corporation','kla tencor'],['KLA','KLAC'],[]],lrcx:[['lam research'],['LRCX'],[]],msft:[['microsoft'],['MSFT'],[]],
 nvda:[['nvidia'],['NVDA'],[]],qcom:[['qualcomm'],['QCOM'],[]],rok:[['rockwell automation'],[],[]],
 rtx:[['raytheon','rtx corp','rtx corporation','pratt whitney','collins aerospace'],['RTX'],['geforce','nvidia','gpu','gpus','graphics','gaming','laptop','dlss','ray tracing']],
 stry:[['stryker'],['SYK'],['brigade','army','armored','stryker vehicle','stryker vehicles','combat vehicle']],tokyo_electron:[['tokyo electron'],[],[]]};
const GDELT_COMPANIES=Object.keys(MATCH).sort(),IR_COMPANIES=GDELT_COMPANIES.filter(id=>id!=='hanmi'&&id!=='tokyo_electron');
// Company domains of the listed official IR feeds (mirrors news_signals.IR_FEEDS); other US companies have no known feed.
const IR_DOMAINS={amd:['amd.com'],amzn:['aboutamazon.com'],avgo:['broadcom.com'],intc:['intc.com','intel.com'],klac:['kla.com'],lrcx:['lamresearch.com'],msft:['microsoft.com'],nvda:['nvidia.com'],qcom:['qualcomm.com'],stry:['stryker.com']};
const CLASS_RULES=[['LEGAL',['lawsuit','lawsuits','sues','sued','suing','court','antitrust','probe','investigation','settlement','settles','regulator','regulators','fine','fined','ftc','doj','class action','verdict','judge','patent','export controls','export curbs','export ban','ban','tariff','tariffs','recall']],
 ['MA',['acquire','acquires','acquired','acquiring','acquisition','acquisitions','merger','mergers','merge','buyout','takeover','to buy','divest','divests','divestiture','spin off','spinoff','stake']],
 ['EARNINGS',['earnings','results','revenue','revenues','profit','profits','eps','guidance','outlook','forecast','quarterly','quarter','fiscal','dividend','beats estimates','misses estimates']],
 ['PRODUCT',['launch','launches','launched','unveil','unveils','unveiled','introduce','introduces','introduced','rolls out','debut','debuts','release','releases','released','product','products','platform']]];
const STOPWORDS=new Set(['a','an','the','and','or','of','to','in','on','for','with','by','at','from','as','is','are','be','its','it','this','that','after','over','into','about','new','says','said','inc','corp','co','ltd','plc','llc','s','will','has','have','than','up','down','amid','vs']);
const ATTRIBUTION={GDELT:{name:'The GDELT Project',url:'https://www.gdeltproject.org/',citation:'News signals: The GDELT Project (https://www.gdeltproject.org/), DOC 2.0 API. Titles and links only; every article belongs to its publisher.'},
 IR:{name:'Company investor-relations press-release feeds',url:null,citation:"Each company's own press-release feed. Titles and links only."}};
const CLASSES={EARNINGS:['실적','Earnings'],PRODUCT:['제품·서비스','Product'],MA:['인수·합병','M&A'],LEGAL:['법률·규제','Legal / regulatory'],OTHER:['기타','Other']};
const STRUCTURAL_RULES={"EXPORT_RESTRICTION":[["asml","lrcx","klac","tokyo_electron","hanmi","nvda","amd","avgo","qcom","intc"],"\\bexport (?:controls?|curbs?|ban|restrictions?)\\b"],"CUSTOMER_OWN_CHIP":[["nvda","amd","avgo","qcom","intc"],"\\b(?:in[ -]house|own|custom) chips?\\b"],"ANTITRUST_REGULATION":[["msft","googl"],"\\bantitrust (?:ruling|regulation|remedy|order)\\b"],"DEFENSE_PROGRAM_CANCELLED":[["rtx"],"\\b(?:program(?:me)? (?:cancelled|canceled|cancellation)|cancel(?:s|led|ed)? (?:major )?(?:defen[sc]e )?program)\\b"],"DEVICE_RECALL_OR_APPROVAL_FAILURE":[["stry"],"\\b(?:recall|approval (?:denied|rejected)|fails? (?:to win )?approval)\\b"],"AUTOMATION_PLATFORM_LOSS":[["rok"],"\\b(?:loses? (?:key )?platform|platform (?:loss|replaced))\\b"],"POWER_EQUIPMENT_CUSTOMER_LOSS":[["etn","hubb","gev"],"\\b(?:loses? (?:a )?(?:key|major) customer|(?:key|major) customer (?:loss|leaves))\\b"]};
function structuralCandidates(items){const result=[],seen=new Set();for(const item of items||[]){if(item.occurrence!=='NEW'||seen.has(item.group_id))continue;for(const[kind,[companies,pattern]]of Object.entries(STRUCTURAL_RULES)){if(companies.includes(item.company_id)&&new RegExp(pattern,'i').test(item.title||'')){result.push({company_id:item.company_id,code:'E4',reason_code:'NEWS_STRUCTURAL_EVENT',event_kind:kind,evidence_grade:'SIGNAL',score_effect:'NONE',info_only:true,group_id:item.group_id,link:item.link,published_at:item.published_at});seen.add(item.group_id);break;}}}return result;}
const CHANNELS={DISCLOSURE:['공시·확정','Disclosure · confirmed'],NEWS:['뉴스·신호','News · signal']};
const TOP=['schema_version','kind','as_of','state','reason_codes','freshness_basis','stale_after_seconds','window_days','channel','score_effect','attribution','matching_rule','sources','items'];
const TOP2=[...TOP,'refresh'],SRC_REFRESH=['last_attempt_at','last_success_at','last_result','last_result_code','items_carried_from','companies','new_items'];
const SUCCEEDED=['UPDATED','NO_NEW_ITEMS'],REFRESH_REASONS={PARTIAL_FAILED:'REFRESH_PARTIAL_FAILED',FAILED:'REFRESH_FAILED',NOT_RUN:'REFRESH_NOT_RUN'},RESULT_CODE=/^[A-Z][A-Z0-9_]{0,39}$/;
const ITEM=['company_id','source','title','link','published_at','classification','group_id','occurrence','relation','related_8k_accession'];
const LABEL='[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?',LINK=new RegExp('^(https?)://('+LABEL+'(?:\\.'+LABEL+')+)(?::[0-9]{1,5})?(?:[/?][A-Za-z0-9!$%&\'()*+,./:;=?@\\[\\]_~-]*)?$');
const TITLE_BAD=/[\u0000-\u001f\u007f-\u009f<>\u00a0\u1680\u180e\u2000-\u200b\u2028\u2029\u202f\u205f\u3000\ufeff]/u;
function need(v){if(!v)throw Error('NEWS_SIGNALS_INVALID');}
const plain=v=>v!==null&&typeof v==='object'&&!Array.isArray(v),keys=(v,k)=>plain(v)&&Object.keys(v).length===k.length&&k.every(n=>Object.hasOwn(v,n));
function instant(v){need(typeof v==='string'&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00$/.test(v));const t=Date.parse(v);need(Number.isFinite(t)&&new Date(t).toISOString().slice(0,19)===v.slice(0,19));return t;}
const fresh=(at,cut)=>cut-at>STALE_AFTER*1000?'STALE':'LIVE';
function same(a,b){if(plain(a)&&plain(b)){const k=Object.keys(a);return k.length===Object.keys(b).length&&k.every(n=>Object.hasOwn(b,n)&&same(a[n],b[n]));}return a===b;}
// Mirrors Python source_refresh / refresh_result. `ids` narrows the summary to the companies in view (screen only).
function sourceRefresh(source,entries,attemptedAt,newItems,ids=null){
 const all=source==='GDELT'?GDELT_COMPANIES:IR_COMPANIES,scope=ids?all.filter(id=>ids.includes(id)):all,list=scope.filter(id=>source==='GDELT'||Object.hasOwn(IR_DOMAINS,id));
 const ok=list.filter(id=>SUCCEEDED.includes(entries[id].last_result)),failed=list.filter(id=>entries[id].last_result==='FAILED').map(id=>entries[id].last_result_code),notRun=list.filter(id=>entries[id].last_result==='NOT_RUN').map(id=>entries[id].last_result_code);
 let result,code=null;if(ok.length&&!failed.length&&!notRun.length)result=ok.some(id=>entries[id].last_result==='UPDATED')?'UPDATED':'NO_NEW_ITEMS';
 else{result=ok.length?'PARTIAL_FAILED':failed.length?'FAILED':'NOT_RUN';code=failed.length||notRun.length?[...failed,...notRun][0]:'NOT_COLLECTED';}
 const acq=scope.map(id=>entries[id].acquired_at).filter(v=>v!==null).sort(),carried=list.filter(id=>!SUCCEEDED.includes(entries[id].last_result)&&entries[id].acquired_at!==null).map(id=>entries[id].acquired_at).sort();
 return{last_attempt_at:attemptedAt,last_success_at:acq.length?acq[acq.length-1]:null,last_result:result,last_result_code:code,items_carried_from:carried.length?carried[0]:null,companies:{succeeded:ok.length,failed:failed.length,not_run:notRun.length},new_items:newItems};}
function refreshResult(s){const r=SOURCES.map(x=>s[x].last_result);if(r.every(x=>SUCCEEDED.includes(x)))return r.includes('UPDATED')?'UPDATED':'NO_NEW_ITEMS';
 if(r.some(x=>SUCCEEDED.includes(x)||x==='PARTIAL_FAILED'))return 'PARTIAL_FAILED';return r.includes('FAILED')?'FAILED':'NOT_RUN';}
// --- rules (mirror Python) ---
function tokens(title){return title.replace(/[A-Z]/g,c=>c.toLowerCase()).replace(/[^a-z0-9]+/g,' ').split(' ').filter(Boolean);}
function significant(title){return new Set(tokens(title).filter(t=>!STOPWORDS.has(t)));}
function hasPhrase(words,phrases){const text=' '+words.join(' ')+' ';return phrases.some(p=>text.includes(' '+p+' '));}
function classify(title){const words=tokens(title);for(const[name,phrases]of CLASS_RULES)if(hasPhrase(words,phrases))return name;return 'OTHER';}
function relevant(id,title){const [names,symbols,exclude]=MATCH[id],words=tokens(title);if(hasPhrase(words,exclude))return false;return hasPhrase(words,names)||symbols.some(s=>new RegExp('(?:^|[^A-Za-z0-9])'+s+'(?=$|[^A-Za-z0-9])').test(title));}
function similar(a,b,minShared=GROUP_MIN_SHARED,minPercent=GROUP_MIN_PERCENT){let shared=0;for(const t of a)if(b.has(t))shared++;return shared>=minShared&&shared*100>=minPercent*(a.size+b.size-shared);}
function validTitle(v){return typeof v==='string'&&[...v].length>0&&[...v].length<=TITLE_MAX&&!TITLE_BAD.test(v)&&!v.startsWith(' ')&&!v.endsWith(' ')&&!v.includes('  ');}
function linkHost(v){const m=typeof v==='string'&&v.length<=LINK_MAX?LINK.exec(v):null;return m?[m[1],m[2]]:null;}
function irLinkAllowed(id,link){const h=linkHost(link),d=IR_DOMAINS[id];return !!(h&&d&&h[0]==='https'&&d.some(x=>h[1]===x||h[1].endsWith('.'+x)));}
const compact=v=>v.slice(0,19).replace(/[-:]/g,'')+'Z',asc=(a,b)=>a.published_at<b.published_at?-1:a.published_at>b.published_at?1:a.link<b.link?-1:a.link>b.link?1:0;
// Mirrors Python assign_groups: oldest first; join the earliest group of the same company whose first item is <= 72h older and similar.
function groups(items){const out=new Map(),heads=[],counters=new Map();
 for(const it of items.filter(i=>i.relation==='NONE').slice().sort(asc)){const at=Date.parse(it.published_at),words=significant(it.title);
  const head=heads.find(h=>h.company===it.company_id&&at-h.at<=GROUP_WINDOW&&similar(words,h.words));
  if(head){out.set(it,{group_id:head.id,occurrence:'REPEAT'});continue;}
  const base='news:'+it.company_id+':'+compact(it.published_at),n=counters.has(base)?counters.get(base)+1:0;counters.set(base,n);const id=base+':'+n;heads.push({company:it.company_id,at,words,id});out.set(it,{group_id:id,occurrence:'NEW'});}
 return items.map(i=>i.relation==='RELATED_TO_8K'?{group_id:i.group_id,occurrence:'REPEAT'}:out.get(i));}
function validate(p){
 try{
  need(plain(p)&&Number.isInteger(p.schema_version)&&[1,2].includes(p.schema_version));const v2=p.schema_version===2;
  need(keys(p,v2?TOP2:TOP)&&p.kind===KIND&&p.freshness_basis==='SOURCE_ACQUISITION'&&p.channel==='NEWS'&&p.score_effect==='NONE'&&p.stale_after_seconds===STALE_AFTER&&p.window_days===WINDOW_DAYS&&p.matching_rule===MATCHING_RULE&&same(p.attribution,ATTRIBUTION));
  const cut=instant(p.as_of),acquired={},states=[];need(keys(p.sources,SOURCES));const refresh=v2?p.refresh:null;
  if(refresh!==null)need(keys(refresh,['attempted_at','result','sources'])&&refresh.attempted_at===p.as_of);
  for(const source of SOURCES){const ids=source==='GDELT'?GDELT_COMPANIES:IR_COMPANIES,entries=p.sources[source];need(plain(entries)&&Object.keys(entries).length===ids.length&&ids.every(id=>Object.hasOwn(entries,id)));
   for(const id of ids){const c=entries[id];need(keys(c,[...(source==='IR'?['state','acquired_at','reason_code','feed_status']:['state','acquired_at','reason_code']),...(v2?['last_result','last_result_code']:[])]));const listed=Object.hasOwn(IR_DOMAINS,id);
    if(source==='IR'){need((listed?['VERIFIED','UNVERIFIED_URL']:['NOT_AVAILABLE']).includes(c.feed_status));if(!listed)need(c.acquired_at===null&&c.reason_code==='NO_OFFICIAL_FEED_KNOWN');}
    if(c.acquired_at===null)need(c.state==='NOT_AVAILABLE'&&(c.reason_code==='NOT_COLLECTED'||source==='IR'&&!listed&&c.reason_code==='NO_OFFICIAL_FEED_KNOWN'));
    else{const at=instant(c.acquired_at);need(at<=cut&&c.reason_code===null&&c.state===fresh(at,cut));acquired[source+'|'+id]=at;}states.push(c.state);
    if(v2){const r=c.last_result,code=c.last_result_code;if(refresh===null||source==='IR'&&!listed)need(r===null&&code===null);else if(SUCCEEDED.includes(r))need(code===null&&c.acquired_at!==null);else need((r==='FAILED'||r==='NOT_RUN')&&typeof code==='string'&&RESULT_CODE.test(code));}}}
  const state=states.includes('LIVE')?'LIVE':states.includes('STALE')?'STALE':'NOT_AVAILABLE',extra=refresh!==null&&typeof refresh.result==='string'&&Object.hasOwn(REFRESH_REASONS,refresh.result)?[REFRESH_REASONS[refresh.result]]:[];
  need(p.state===state&&Array.isArray(p.reason_codes)&&JSON.stringify(p.reason_codes)===JSON.stringify([...(state==='LIVE'?[]:state==='STALE'?['STALE_INPUT']:['NO_ELIGIBLE_INPUT']),...extra]));
  const items=p.items;need(Array.isArray(items)&&items.length<=MAX_ITEMS);const cutoff=cut-WINDOW_DAYS*86400000,links=new Set(),titles=new Set(),per=new Map();
  for(const i of items){need(keys(i,ITEM)&&SOURCES.includes(i.source)&&typeof i.company_id==='string'&&Object.hasOwn(acquired,i.source+'|'+i.company_id));
   need(validTitle(i.title)&&linkHost(i.link)!==null);need(i.source==='GDELT'?relevant(i.company_id,i.title):irLinkAllowed(i.company_id,i.link));
   const at=instant(i.published_at);need(cutoff<=at&&at<=acquired[i.source+'|'+i.company_id]);
   need(CLASSIFICATIONS.includes(i.classification)&&i.classification===classify(i.title)&&['NEW','REPEAT'].includes(i.occurrence)&&['NONE','RELATED_TO_8K'].includes(i.relation));
   if(i.relation==='RELATED_TO_8K')need(i.source==='IR'&&typeof i.related_8k_accession==='string'&&/^\d{10}-\d{2}-\d{6}$/.test(i.related_8k_accession)&&typeof i.group_id==='string'&&i.group_id.startsWith(i.company_id+':')&&/^\d{10}-\d{2}-\d{6}$/.test(i.group_id.slice(i.company_id.length+1)));
   else need(i.related_8k_accession===null);
   const key=i.company_id+' '+tokens(i.title).join(' ');need(!links.has(i.link)&&!titles.has(key));links.add(i.link);titles.add(key);const k=i.source+'|'+i.company_id;per.set(k,(per.get(k)||0)+1);need(per.get(k)<=PER_COMPANY_MAX[i.source]);}
  for(let n=1;n<items.length;n++)need(asc(items[n-1],items[n])>0);
  const expected=groups(items);need(items.every((e,n)=>e.group_id===expected[n].group_id&&e.occurrence===expected[n].occurrence));
  if(refresh!==null){need(keys(refresh.sources,SOURCES));for(const source of SOURCES){const got=refresh.sources[source],entries=p.sources[source];need(keys(got,SRC_REFRESH));
    const n=got.new_items,updated=Object.keys(entries).filter(id=>entries[id].last_result==='UPDATED'),count=id=>per.get(source+'|'+id)||0;
    need(updated.every(id=>count(id)>0)&&Number.isInteger(n)&&n>=0&&(n>0)===(updated.length>0)&&n<=updated.reduce((a,id)=>a+count(id),0));
    need(keys(got.companies,['succeeded','failed','not_run'])&&same(got,sourceRefresh(source,entries,refresh.attempted_at,n)));}
   need(refresh.result===refreshResult(refresh.sources));}
  return p;
 }catch(_){throw Error('NEWS_SIGNALS_INVALID');}
}
async function load(view){const control=new AbortController(),timer=setTimeout(()=>control.abort(),20000);
 try{const r=await view.fetch(FILENAME,{cache:'no-store',credentials:'omit',referrerPolicy:'no-referrer',redirect:'error',signal:control.signal});if(!r.ok)return null;const text=await r.text();if(new TextEncoder().encode(text).length>MAX)return null;return validate(JSON.parse(text));}
 catch(_){return null;}finally{clearTimeout(timer);}}
// One chronological list (newest first): SEC 8-K rows carry the IR releases that repeat their Exhibit 99.1; each news group is one row
// (its NEW item, at that time) with later REPEAT reports collapsed; DART rows (if the DART reader and file exist) join by KST date.
function timeline({sec=null,dart=null,news=null}={},{companyIds=null,dartApi=null}={}){const pick=id=>!companyIds||companyIds.includes(id),rows=[],related=new Map(),byGroup=new Map();
 const events=(sec?.events||[]).filter(e=>pick(e.company_id)),accessions=new Set(events.map(e=>e.accession));
 for(const i of (news?.items||[]).filter(i=>pick(i.company_id))){
  if(i.relation==='RELATED_TO_8K'&&accessions.has(i.related_8k_accession)){if(!related.has(i.related_8k_accession))related.set(i.related_8k_accession,[]);related.get(i.related_8k_accession).push(i);}
  else if(i.relation==='RELATED_TO_8K')rows.push({channel:'NEWS',source:i.source,time:i.published_at,company_id:i.company_id,item:i,repeats:[],orphan:true});
  else{if(!byGroup.has(i.group_id))byGroup.set(i.group_id,[]);byGroup.get(i.group_id).push(i);}}
 for(const e of events)rows.push({channel:'DISCLOSURE',source:'SEC',time:e.accepted_at,company_id:e.company_id,event:e,related:related.get(e.accession)||[]});
 if(dart&&dartApi&&typeof dartApi.timeline==='function')for(const r of dartApi.timeline(dart,{companyIds}))rows.push(Object.assign({},r,{source:'DART'}));
 for(const list of byGroup.values()){const head=list.find(i=>i.occurrence==='NEW')||list[list.length-1];rows.push({channel:'NEWS',source:head.source,time:head.published_at,company_id:head.company_id,item:head,repeats:list.filter(i=>i!==head),orphan:false});}
 return rows.sort((a,b)=>a.time<b.time?1:a.time>b.time?-1:0);}
const COMPANY_LABEL={hanmi:'042700',tokyo_electron:'8035'};
// Refresh status per source for the companies in view (all, or companyIds). kind: RECORDED (schema 2 run), NO_RUN (schema 2
// copy written without a collection), UNRECORDED (schema 1 copy), NO_FEED (no listed IR feed in view). For a failed or partly
// failed source, carried_last / carried_from are the newest / oldest acquisition kept from earlier runs.
function refreshStatus(news,{companyIds=null}={}){if(!news)return [];const ids=Array.isArray(companyIds)?companyIds:null;
 return SOURCES.map(source=>{const entries=news.sources[source],all=source==='GDELT'?GDELT_COMPANIES:IR_COMPANIES,scope=ids?all.filter(id=>ids.includes(id)):all;
  const list=scope.filter(id=>source==='GDELT'||Object.hasOwn(IR_DOMAINS,id));if(!list.length)return{source,kind:'NO_FEED',companies:0};
  const acq=list.map(id=>entries[id].acquired_at).filter(v=>v!==null).sort(),last=acq.length?acq[acq.length-1]:null;
  if(news.schema_version===1)return{source,kind:'UNRECORDED',companies:list.length,last_success_at:last};
  if(!news.refresh)return{source,kind:'NO_RUN',companies:list.length,last_success_at:last};
  const sum=sourceRefresh(source,entries,news.refresh.attempted_at,null,ids),bad=list.filter(id=>!SUCCEEDED.includes(entries[id].last_result));
  const carried=bad.map(id=>entries[id].acquired_at).filter(v=>v!==null).sort(),codes=[...new Set(bad.map(id=>entries[id].last_result_code))];
  const notRunOnly=bad.length>0&&bad.every(id=>entries[id].last_result==='NOT_RUN');
  return{source,kind:'RECORDED',companies:list.length,result:sum.last_result,code:sum.last_result_code,mixed_codes:codes.length>1,not_run_only:notRunOnly,
   checked_at:news.refresh.attempted_at,last_success_at:sum.last_success_at,carried_last:carried.length?carried[carried.length-1]:null,carried_from:carried.length?carried[0]:null,
   succeeded:sum.companies.succeeded,failed:sum.companies.failed+sum.companies.not_run,any_updated:list.some(id=>entries[id].last_result==='UPDATED')};});}
// One line per source. '새 뉴스 없음' (request answered, nothing new) and '조회 실패' (request failed or not made) never share a text.
function refreshText(st,en=false){const T=(k,e)=>en?e:k,when=v=>v.slice(0,16).replace('T',' ')+' UTC',S=st.source==='IR'?T('회사 IR','Company IR'):'GDELT';
 if(st.kind==='NO_FEED')return S+' · '+T('보는 기업에 확인된 공식 피드 없음','no listed official feed for these companies');
 if(st.kind==='UNRECORDED')return S+' · '+(st.last_success_at?T('마지막 수집 ','last collected ')+when(st.last_success_at):T('수집 자료 없음','nothing collected'))+' · '+T('최근 갱신 결과 미기록(이전 형식)','latest refresh result not recorded (older format)');
 if(st.kind==='NO_RUN')return S+' · '+T('이 파일은 수집 없이 만들어짐','this copy was written without a collection');
 const checked=when(st.checked_at),fail=()=>T('최근 갱신 실패(','latest refresh failed (')+S+' '+(st.not_run_only?T('요청 안 함 · ','not requested · '):'')+st.code+(st.mixed_codes?T(' 등',' etc.'):'')+', '+checked+')';
 const kept=()=>st.carried_last?T('이전 자료 유지 · 마지막 성공 ','previous items kept · last success ')+when(st.carried_last)+(st.carried_from&&st.carried_from!==st.carried_last?T(' (가장 오래된 수집 ',' (oldest kept ')+when(st.carried_from)+')':''):T('이전 자료 없음','no previous items');
 if(st.result==='UPDATED')return S+' · '+T('새 뉴스 반영 · 확인 ','new items added · checked ')+checked;
 if(st.result==='NO_NEW_ITEMS')return S+' · '+T('새 뉴스 없음 · 확인 ','no new news · checked ')+checked;
 if(st.result==='PARTIAL_FAILED')return S+' · '+T('일부 갱신 실패 ','partly failed ')+st.failed+'/'+st.companies+T('곳',' companies')+' · '+kept()+' · '+fail()+' · '+T('나머지 ','other ')+st.succeeded+T('곳 ',' ')+(st.any_updated?T('새 뉴스 반영','new items added'):T('새 뉴스 없음','no new news'))+T(' · 확인 ',' · checked ')+checked;
 return S+' · '+kept()+' · '+fail();}
// Display-only filters for the combined list: channel, category, new/repeat and order. Kept per browser tab in sessionStorage so
// #news and #watchlist share them across screen moves; unreadable storage falls back to the defaults. Filters only narrow or
// reorder the newest-`limit` rows; they never widen that set (the disclosure minimum, NEWS-CAP, is an open owner decision).
const FILTER_KEY='investment.web.v1.news-filters',PERSONAL_KEY='investment.web.v1.personal';
const FILTER_DEFAULT=Object.freeze({channel:'ALL',category:'ALL',occurrence:'ALL',order:'TIME'});
const FILTER_VALUES={channel:['ALL','DISCLOSURE','NEWS'],occurrence:['ALL','NEW','REPEAT'],order:['TIME','IMPORTANCE']};
// Importance here is only what the data supports: held, watchlist, other company, market. Event materiality is not computed.
const TIERS={HELD:['보유','Held'],INTEREST:['관심','Watchlist'],OTHER:['기타 기업','Other companies'],MARKET:['시장','Market']},TIER_ORDER=['HELD','INTEREST','OTHER','MARKET'];
function session(){try{return root.sessionStorage||null;}catch(_){return null;}}
function readFilters(storage=session()){const out={...FILTER_DEFAULT};
 try{const v=JSON.parse(storage?storage.getItem(FILTER_KEY)||'null':'null');if(!plain(v))return out;
  for(const k of Object.keys(FILTER_DEFAULT)){const x=v[k];if(k==='category'?typeof x==='string'&&/^(?:ALL|RESULTS|(?:NEWS|SEC|DART):[A-Z_]{1,40})$/.test(x):FILTER_VALUES[k].includes(x))out[k]=x;}}catch(_){}
 return out;}
function writeFilters(f,storage=session()){try{if(!storage)return false;storage.setItem(FILTER_KEY,JSON.stringify(f));return true;}catch(_){return false;}}
// Reads the one interest list kept by the app (never copied or written here).
function readInterests(){try{const v=JSON.parse(root.localStorage?.getItem(PERSONAL_KEY)||'null');return Array.isArray(v?.interests)?v.interests.filter(x=>typeof x==='string'):[];}catch(_){return [];}}
// Category key: '실적' merges news EARNINGS with SEC/DART RESULTS (same label); every other class keeps its own source.
function rowCategory(row){if(row.channel==='NEWS'){const c=row.item.classification;return c==='EARNINGS'?'RESULTS':'NEWS:'+c;}const c=row.event.classification;return c==='RESULTS'?'RESULTS':(row.source==='DART'?'DART:':'SEC:')+c;}
function rowOccurrence(row){return row.channel==='NEWS'?(row.orphan?'REPEAT':row.item.occurrence):row.event.occurrence;}
function rowTier(row,{held=[],interests=[]}={}){if(!row.company_id)return 'MARKET';if(held.includes(row.company_id))return 'HELD';if(interests.includes(row.company_id))return 'INTEREST';return 'OTHER';}
// Same tier: newest first (input order), as in the relation feed order.
function filterRows(rows,f=FILTER_DEFAULT,ctx={}){const out=rows.filter(r=>(f.channel==='ALL'||r.channel===f.channel)&&(f.category==='ALL'||rowCategory(r)===f.category)&&(f.occurrence==='ALL'||rowOccurrence(r)===f.occurrence));
 if(f.order!=='IMPORTANCE')return out;const rank=r=>TIER_ORDER.indexOf(rowTier(r,ctx));return out.map((r,i)=>[r,i]).sort((a,b)=>rank(a[0])-rank(b[0])||a[1]-b[1]).map(x=>x[0]);}
// 5.2.5 (news screen layout only): counts of the newest `limit` rows the list shows, from the same rows (no new rule): new
// items and filings, repeat reports and amended filings, and repeat reports folded under a row (same event, or IR under its 8-K).
function occurrenceSummary(doc,rows,limit,en){const T=(k,e)=>en?e:k;let fresh=0,again=0,folded=0;
 for(const row of rows){if(rowOccurrence(row)==='NEW')fresh++;else again++;folded+=row.channel==='NEWS'?row.repeats.length:Array.isArray(row.related)?row.related.length:0;}
 const dl=doc.createElement('dl');dl.className='kv nw-counts';dl.setAttribute('data-news-occurrence-summary','');
 for(const[k,v,key]of [[T('새 소식 · 새 공시','New items · new filings'),fresh,'NEW'],[T('반복 보도 · 정정 공시','Repeat reports · amended filings'),again,'REPEAT'],[T('묶어 접은 반복 보도','Folded repeat reports'),folded,'FOLDED']]){
  const dt=doc.createElement('dt'),dd=doc.createElement('dd');dt.textContent=k;dd.textContent=String(v);dd.className='num';dd.setAttribute('data-occurrence-count',key);dl.append(dt,dd);}
 const frag=doc.createDocumentFragment(),note=doc.createElement('p');note.className='small';
 note.textContent=T('최신 '+limit+'행 기준 · 72시간 안 비슷한 제목은 한 사건으로 묶음 · 8-K와 같은 IR 보도자료는 그 8-K 아래 · 목록의 "신규·반복" 조건으로 거를 수 있음','Within the newest '+limit+' rows · similar titles within 72h are one event · an IR release repeating an 8-K sits under that 8-K · filter with “New / repeat” in the list');
 frag.append(dl,note);return frag;}
function mount(host,{sec=null,dart=null,news=null}={},{locale,companyIds=null,limit=30,emptyText,secApi=root.SecDisclosures,dartApi=root.DartDisclosures,held=null,interests=null,storage=session()}={}){
 if(!host)return;const doc=host.ownerDocument,en=locale==='en-US',T=(k,e)=>en?e:k,el=(tag,text,attrs={})=>{const n=doc.createElement(tag);if(text!==undefined)n.textContent=text;for(const[k,v]of Object.entries(attrs))n.setAttribute(k,v);return n;};
 const when=v=>v.slice(0,16).replace('T',' ')+' UTC',srcLabel=s=>s==='IR'?T('회사 IR','Company IR'):'GDELT',classLabel=c=>{const [k,e]=CLASSES[c];return en?e+' ('+k+')':k+' ('+e+')';};
 const section=el('section',undefined,{class:'card','data-sec-disclosures':'','data-news-signals':''});section.append(el('h2',T('뉴스·공시 · 공시·확정 + 뉴스·신호','News & disclosures · confirmed disclosures + news signals')));
 // Menu 4 news layout (design lane D3): inside the news screen ([data-news-layout]) the same nodes go into three numbered stamp
 // boxes, function numbers 5.2.1 list, 5.2.5 new/repeat, 5.2.7 collection status. Elsewhere (watchlist) the section is unchanged.
 const fnLayout=!!(host.closest&&host.closest('[data-news-layout]'));let listBox=section,occBox=null,statusBox=section;
 if(fnLayout){const box=(n,ko,e)=>{const id='nw-fn-'+n.replaceAll('.','-'),b=el('section',undefined,{class:'nw-sec','data-fn':n,'aria-labelledby':id}),h=el('h3',undefined,{class:'nw-head',id});
   h.append(el('span',n,{class:'ia-sec'}),doc.createTextNode(' '),el('span',T(ko,e),{class:'nw-title'}));b.append(h);return b;};
  listBox=box('5.2.1','목록과 개인화','List and personal');occBox=box('5.2.5','신규 · 중복 · 변경','New · repeat · amended');statusBox=box('5.2.7','수집 상태','Collection status');
  const grid=el('div',undefined,{class:'nw-mount-grid'});grid.append(listBox,occBox,statusBox);section.append(grid);}
 const secState=sec?sec.state:'NOT_AVAILABLE',newsState=news?news.state:'NOT_AVAILABLE',chips=el('p',undefined,{class:'chips'});
 chips.append(el('span',CHANNELS.DISCLOSURE[en?1:0]+' · SEC 8-K',{class:'badge'}),el('span',secState,{class:'badge '+secState,'data-disclosure-state':secState}));
 if(dart)chips.append(el('span','DART',{class:'badge'}),el('span',dart.state,{class:'badge disclosure-state','data-dart-state':dart.state}));
 chips.append(el('span',CHANNELS.NEWS[en?1:0]+' · GDELT · IR',{class:'badge news-signal'}),el('span',newsState,{class:'badge news-state','data-news-state':newsState}));
 const refreshRows=refreshStatus(news,{companyIds}),recorded=refreshRows.filter(r=>r.kind==='RECORDED');
 if(recorded.length){const r=recorded.every(x=>SUCCEEDED.includes(x.result))?'OK':recorded.some(x=>SUCCEEDED.includes(x.result)||x.result==='PARTIAL_FAILED')?'PARTIAL_FAILED':'FAILED';
  if(r!=='OK')chips.append(el('span',r==='FAILED'?T('최근 갱신 실패 · 이전 자료 유지','Latest refresh failed · previous items kept'):T('일부 갱신 실패','Refresh partly failed'),{class:'badge partial','data-news-refresh-badge':r}));}
 statusBox.append(chips);
 for(const[p,label,window]of [[sec,'SEC 8-K',90],[news,T('뉴스·신호','News'),WINDOW_DAYS]])if(p){statusBox.append(el('p',label+' · '+T('기준: ','as of: ')+p.as_of+' · '+T('최근 '+window+'일','last '+window+' days'),{class:'meta'}));
  if(p.state!=='NOT_AVAILABLE'&&Date.now()-Date.parse(p.as_of)>p.stale_after_seconds*1000)statusBox.append(el('p','STALE · '+label+' · '+T('수집 갱신 시각 경과','Acquisition refresh overdue'),{class:'warning','data-disclosure-stale':''}));
  if(p===news)for(const r of refreshRows){const bad=r.kind==='RECORDED'&&!SUCCEEDED.includes(r.result);
   statusBox.append(el('p',refreshText(r,en),{class:bad?'small warning':'small','data-news-refresh':r.source,'data-news-refresh-result':r.kind==='RECORDED'?r.result:r.kind,'data-news-refresh-code':r.code||''}));}}
 if(!sec)statusBox.append(el('p',T('공개 공시 자료가 연결되지 않았습니다.','Public disclosure data is not connected.'),{class:'small','data-disclosure-missing':''}));
 if(news){const a=el('p',undefined,{class:'small','data-news-attribution':''});a.append(doc.createTextNode(T('뉴스·신호 출처: ','News signals source: ')),el('a',ATTRIBUTION.GDELT.name,{href:ATTRIBUTION.GDELT.url,target:'_blank',rel:'noopener noreferrer','data-gdelt-attribution':''}),doc.createTextNode(' (GDELT DOC 2.0 API) · '+T('회사 IR 보도자료 피드 · 제목·링크만 표시, 기사는 각 언론사 소유','company IR press-release feeds · titles and links only; articles belong to their publishers')));statusBox.append(a);}
 else statusBox.append(el('p',T('뉴스·신호 자료가 연결되지 않았습니다.','News signal data is not connected.'),{class:'small','data-news-missing':''}));
 statusBox.append(el('p',T('점수에 반영하지 않음 · 제목·링크·시각·기업·분류만 표시','Never changes scores · title, link, time, company and classification only'),{class:'small','data-score-effect':'NONE'}));
 const all=timeline({sec,dart,news},{companyIds,dartApi}),rows=all.slice(0,limit);
 if(occBox)occBox.append(occurrenceSummary(doc,rows,limit,en));
 if(!rows.length){listBox.append(el('p',emptyText||T('표시할 공시·뉴스가 없습니다.','No disclosures or news to show.'),{class:'empty'}));host.replaceChildren(section);return;}
 const ctx={held:Array.isArray(held)?held:[],interests:Array.isArray(interests)?interests:readInterests()};
 const catOrder=k=>k==='RESULTS'?'0':k.startsWith('NEWS:')?'1'+k:k.startsWith('SEC:')?'2'+k:'3'+k,cats=[...new Set(all.map(rowCategory))].sort((a,b)=>catOrder(a)<catOrder(b)?-1:1);
 const catLabel=key=>{if(key==='RESULTS')return T('실적','Results');const [src,c]=key.split(':'),table=src==='NEWS'?CLASSES:src==='SEC'?secApi?.CLASSES:dartApi?.CLASSES,pair=table&&table[c];return (pair?pair[en?1:0]:c)+' · '+(src==='NEWS'?T('뉴스','news'):src);};
 let f=readFilters(storage);if(f.category!=='ALL'&&!cats.includes(f.category))f={...f,category:'ALL'};
 const bar=el('div',undefined,{class:'chips toolbar','data-news-filters':'',role:'group','aria-label':T('뉴스·공시 보기 조건','News & disclosures view options')}),selects={};
 const control=(name,label,options)=>{const l=el('label',label+' '),s=el('select',undefined,{'data-news-filter':name,'aria-label':label});for(const[v,t]of options)s.append(el('option',t,{value:v}));s.value=f[name];
  s.onchange=()=>{f={...f,[name]:s.value};writeFilters(f,storage);paint();};l.append(s);bar.append(l);selects[name]=s;};
 const all_=T('전체','All');
 control('channel',T('채널','Channel'),[['ALL',all_],['DISCLOSURE',CHANNELS.DISCLOSURE[en?1:0]],['NEWS',CHANNELS.NEWS[en?1:0]]]);
 control('category',T('분류','Category'),[['ALL',all_],...cats.map(k=>[k,catLabel(k)])]);
 control('occurrence',T('신규·반복','New / repeat'),[['ALL',all_],['NEW',T('새 소식·새 공시','New only')],['REPEAT',T('반복·정정','Repeat / amendment')]]);
 control('order',T('정렬','Order'),[['TIME',T('시간순 (최신 먼저)','Newest first')],['IMPORTANCE',T('중요도 순 (보유→관심→기타→시장)','Importance (held→watchlist→other→market)')]]);
 const reset=el('button',T('조건 초기화','Reset'),{type:'button','data-news-filter-reset':''});reset.onclick=()=>{f={...FILTER_DEFAULT};writeFilters(f,storage);for(const[k,s]of Object.entries(selects))s.value=f[k];paint();};bar.append(reset);
 listBox.append(bar,el('p',T('중요도 기준: 보유·관심 여부','Importance basis: held / watchlist')+' · '+T('사건 자체의 중요도는 계산하지 않음','event materiality is not computed')+' · '+T('같은 그룹은 최신 먼저','newest first within a group')+(Array.isArray(held)?'':' · '+T('보유 정보 미연결','holdings not connected')),{class:'small','data-importance-basis':''}));
 const count=el('p',undefined,{class:'small','data-news-filter-count':'',role:'status'}),body=el('div',undefined,{'data-news-body':''});listBox.append(count,body);
 const tierBadge=t=>el('span',TIERS[t][en?1:0],{class:'badge','data-importance':t});
 const evidenceBox=(kind,entries)=>{const d=el('details',undefined,{class:'evidence','data-evidence':kind}),dl=el('dl',undefined,{class:'kv'});d.append(el('summary',T('근거 보기','Show evidence')));
  for(const[k,v]of entries){const dd=el('dd');if(typeof v==='string')dd.textContent=v;else dd.append(v);dl.append(el('dt',k),dd);}d.append(dl);return d;};
 const latest=i=>{const c=news?.sources?.[i.source]?.[i.company_id],r=c?.last_result;if(!news||news.schema_version===1||!news.refresh||!r)return T('결과 미기록','not recorded');
  const at=' · '+when(news.refresh.attempted_at);return r==='UPDATED'?T('새 뉴스 반영','new items added')+at:r==='NO_NEW_ITEMS'?T('새 뉴스 없음','no new news')+at
   :(r==='FAILED'?T('조회 실패 ','request failed '):T('요청 안 함 ','not requested '))+c.last_result_code+at+' · '+T('이 행은 이전 수집분','this row is from an earlier collection');};
 const newsEvidence=row=>{const i=row.item,src=el('span'),acq=news?.sources?.[i.source]?.[i.company_id]?.acquired_at;
  src.append(el('a',linkHost(i.link)[1]+' ↗',{href:i.link,target:'_blank',rel:'noopener noreferrer','data-evidence-link':''}));if(i.source==='GDELT')src.append(doc.createTextNode(' · '+T('수집 경로: ','via ')+ATTRIBUTION.GDELT.name));
  const dedup=row.orphan?T('8-K 관련 IR 보도자료 · 그 8-K('+i.related_8k_accession+')가 목록에 없어 단독 표시','IR release related to 8-K '+i.related_8k_accession+' · that 8-K is not listed, so shown alone')
   :row.repeats.length?T('같은 사건 묶음 · 첫 보도 + 반복 '+row.repeats.length+'건 (72시간 안 제목 유사)','One event · first report + '+row.repeats.length+' repeat(s) (similar titles within 72h)')
   :i.occurrence==='NEW'?T('새 소식 · 반복 보도 없음','New · no repeat reports'):T('반복 보도 · 첫 보도는 목록 범위 밖','Repeat · first report outside the window');
  return evidenceBox('NEWS',[[T('구분','Kind'),i.source==='IR'?T('뉴스·신호 · 회사 IR 보도자료 (공시 아님)','News · signal · company IR release (not a filing)'):T('뉴스·신호 · 언론 보도 제목 (내용 미확인)','News · signal · press headline (content unverified)')],
   [T('출처','Source'),src],[T('발표 시각','Published'),when(i.published_at)],[T('수집 시각','Collected'),acq?when(acq)+' · '+T('이 기업 피드 수집','feed collected for this company'):T('미제공','not provided')],
   [T('최근 갱신','Latest refresh'),latest(i)],
   [T('기업 연결','Company match'),i.source==='GDELT'?T('제목 속 회사 이름·티커','company name or ticker in the title'):T('회사 공식 IR 도메인','company IR domain')],[T('분류 근거','Category basis'),T('제목 단어 규칙','title keyword rule')],
   [T('중복 처리','Dedup'),dedup],[T('점수 영향','Score effect'),T('없음','None')]]);};
 const line=i=>{const li=el('li',undefined,{'data-news-item':'','data-news-source':i.source,'data-news-occurrence':i.occurrence,'data-relation':i.relation});li.append(el('a',i.title,{href:i.link,target:'_blank',rel:'noopener noreferrer','data-news-link':''}),doc.createTextNode(' · '+srcLabel(i.source)+' · '+when(i.published_at)+' · '+linkHost(i.link)[1]));return li;};
 const render=row=>{const tier=rowTier(row,ctx);
  if(row.channel==='DISCLOSURE'&&row.source==='SEC'&&secApi){const li=secApi.renderRow(doc,row.event,en);li.querySelector('.chips')?.append(tierBadge(tier));
   if(row.related.length){const d=el('details',undefined,{'data-related-ir':String(row.related.length)}),ul=el('ul',undefined,{class:'list'});d.append(el('summary',T('관련 IR 보도자료 '+row.related.length+'건 · 8-K와 같은 발표(반복)','Related IR release ×'+row.related.length+' · same announcement as this 8-K (repeat)')));for(const i of row.related)ul.append(line(i));d.append(ul);li.append(d);}
   return li;}
  if(row.channel==='DISCLOSURE'&&row.source==='DART'){const e=row.event,li=el('li',undefined,{class:'card','data-disclosure':e.rcept_no,'data-source':'DART','data-occurrence':e.occurrence,'data-classification':e.classification}),head=el('p',undefined,{class:'chips'});
   head.append(el('span',CHANNELS.DISCLOSURE[en?1:0],{class:'badge LIVE','data-channel':'DISCLOSURE'}),el('span',e.occurrence==='NEW'?T('새 공시','New'):T('정정·반복','Repeat / amendment'),{class:'badge','data-occurrence-label':e.occurrence}),el('span',dartApi&&dartApi.classLabel?dartApi.classLabel(e.classification,en):e.classification,{class:'badge','data-classification-label':e.classification}),tierBadge(tier));
   const who=el('p');who.append(el('a',COMPANY_LABEL[e.company_id]||e.company_id.toUpperCase(),{href:'#company/'+encodeURIComponent(e.company_id)}),doc.createTextNode(' · DART · '+e.filing_date+' KST'));const t=el('p');t.append(el('a',e.title,{href:e.link,target:'_blank',rel:'noopener noreferrer','data-filing-link':''}),doc.createTextNode(' ↗'));li.append(head,who,t);
   if(dartApi&&typeof dartApi.evidence==='function')li.append(dartApi.evidence(doc,e,en));return li;}
  if(row.channel!=='NEWS')return null;
  const i=row.item,li=el('li',undefined,{class:'card','data-news':i.group_id,'data-news-source':i.source,'data-news-occurrence':i.occurrence,'data-news-classification':i.classification}),head=el('p',undefined,{class:'chips'});
  head.append(el('span',CHANNELS.NEWS[en?1:0],{class:'badge news-signal','data-channel':'NEWS'}),el('span',row.orphan?T('8-K 관련 · 반복','Related to 8-K · repeat'):i.occurrence==='NEW'?T('새 소식','New'):T('반복 보도','Repeat'),{class:'badge','data-news-occurrence-label':row.orphan?'RELATED_TO_8K':i.occurrence}),el('span',classLabel(i.classification),{class:'badge','data-news-classification-label':i.classification}),tierBadge(tier));
  const who=el('p');who.append(el('a',COMPANY_LABEL[i.company_id]||i.company_id.toUpperCase(),{href:'#company/'+encodeURIComponent(i.company_id)}),doc.createTextNode(' · '+srcLabel(i.source)+' · '+when(i.published_at)+' · '+linkHost(i.link)[1]));
  const t=el('p');t.append(el('a',i.title,{href:i.link,target:'_blank',rel:'noopener noreferrer','data-news-link':''}),doc.createTextNode(' ↗'));li.append(head,who,t);
  if(row.repeats.length){const d=el('details',undefined,{'data-news-repeats':String(row.repeats.length)}),ul=el('ul',undefined,{class:'list'});d.append(el('summary',T('같은 사건 반복 보도 '+row.repeats.length+'건','Repeat reports of this event: '+row.repeats.length)));for(const r of row.repeats)ul.append(line(r));d.append(ul);li.append(d);}
  li.append(newsEvidence(row));return li;};
 function paint(){const shown=filterRows(rows,f,ctx),outside=filterRows(all.slice(limit),{...f,order:'TIME'},ctx).length;
  count.textContent=T('표시 '+shown.length+'건 · 최신 '+limit+'행 안에서 거름','Showing '+shown.length+' · filtered within the newest '+limit+' rows')+(outside?' · '+T('조건에 맞는 '+outside+'건은 최신 '+limit+'행 밖이라 표시 안 함 (공시 최소 보장은 사용자 결정 대기)',outside+' matching row(s) are beyond the newest '+limit+' and not shown (disclosure minimum awaits an owner decision)'):'');
  if(!shown.length){body.replaceChildren(el('p',T('조건에 맞는 항목이 없습니다.','Nothing matches these options.'),{class:'empty','data-news-filter-empty':''}));return;}
  const list=el('ol',undefined,{class:'list','data-disclosure-list':'','data-timeline':''});for(const row of shown){const li=render(row);if(li)list.append(li);}body.replaceChildren(list);}
 paint();host.replaceChildren(section);
}
// ---------- Menu 4 뉴스 screen layout (design lane D3; owner draft "투자시스템 화면 시안 (손그림 칠판)", PRODUCT_IA_DIRECTIVE_20261018) ----------
// Numbered stamp boxes with FUNCTION numbers (5.1 관계망 5.1.1–5.1.4, 5.2 공시·뉴스 5.2.1–5.2.7, 5.3 뉴스 내용구성 트리); the menu strip
// keeps its menu numbers (4 / 4.1 / 4.2 / 4.3). app.js passes its own pieces (heading, toolbar, panes) unchanged; this only places
// them. The draft's example companies and numbers are never shown: what has no data says 미산출 / NOT_AVAILABLE and which open
// decision it waits on. No price or price-derived value, no request, no storage. The 5.1 / 5.2 groups follow the existing
// 뉴스 | 관계망 toggle (CSS :has on the pane's hidden attribute). Decoration SVG is aria-hidden; the text carries the meaning.
const escHtml=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]);
function screenHtml(parts={},{locale,company=null,interests=null,relations=false}={}){
 const en=locale==='en-US',T=(k,e)=>escHtml(en?e:k),D=root.Doodles,P=k=>typeof parts[k]==='string'?parts[k]:'';
 const na=why=>'<p class="nw-na"><span class="badge NOT_AVAILABLE">'+T('미산출','Not computed')+'</span> <span class="small">'+why+'</span></p>';
 const id=(n,x='')=>'nw-fn-'+n.replaceAll('.','-')+x;
 const head=(n,ko,e,tag='h3',x='')=>'<'+tag+' class="nw-head" id="'+id(n,x)+'"><span class="ia-sec">'+n+'</span> <span class="nw-title">'+T(ko,e)+'</span></'+tag+'>';
 const sec=(n,ko,e,body,cls='',x='')=>'<section class="nw-sec'+(cls?' '+cls:'')+'" data-fn="'+n+'"'+(x?' data-fn-part="'+x.slice(1)+'"':'')+' aria-labelledby="'+id(n,x)+'">'+head(n,ko,e,'h3',x)+body+'</section>';
 const group=(n,ko,e,note,body)=>'<section class="nw-group" data-fn="'+n+'" aria-labelledby="'+id(n)+'"><div class="nw-group-top">'+(D?D.icon('news','nw-doodle'):'')+head(n,ko,e,'h2')+(note?'<span class="nw-hand">'+note+'</span>':'')+'</div>'+(D?D.underline('nw-line'):'')+body+'</section>';
 const who=company&&typeof company.ticker==='string'?escHtml(company.ticker):'';
 const count=Number.isInteger(interests)?interests:readInterests().length;
 // 5.1.1: decoration only when no relation data: the company in view (red ring) and dashed empty links (nothing invented).
 const sketch=relations?'':'<svg class="nw-net" viewBox="0 0 240 120" aria-hidden="true" focusable="false"><path class="nw-net-link" d="M120 60 L42 26 M120 60 L200 24 M120 60 L206 96 M120 60 L36 98"/><circle class="nw-net-empty" cx="42" cy="26" r="13"/><circle class="nw-net-empty" cx="200" cy="24" r="13"/><circle class="nw-net-empty" cx="206" cy="96" r="13"/><circle class="nw-net-empty" cx="36" cy="98" r="13"/><circle class="nw-net-me" cx="120" cy="60" r="22"/></svg>'+
  '<p class="small nw-caption">'+T('빨간 원 = 지금 보는 기업','Red ring = the company in view')+(who?' ('+who+')':' ('+T('선택 안 함','none selected')+')')+' · '+T('점선 = 관계 자료 미연결','dashed = relationship data not connected')+'</p>';
 const g51=group('5.1','관계망','Company network',T('기업 하나를 가운데 두고 연결을 봅니다','One company in the middle, its links around it'),
  '<div class="nw-grid nw-grid-51">'+
  sec('5.1.1','기업 중심 관계','Relations around a company','<p class="small" data-news-center>'+(who?T('가운데 기업: ','Company in the middle: ')+'<b>'+who+'</b>':T('가운데 기업 없음 · 기업을 검색하거나 관심 기업을 고르세요','No company in the middle · search a company or pick a watchlist company'))+'</p>'+sketch+P('networkPane'),'nw-main')+
  sec('5.1.2','연결 근거','Link evidence',na(T('관계 자료 미연결 · 확인된 관계(공시)와 추론 관계를 나눠 근거를 보일 자리 · 자료원 결정 대기(REL-SOURCE)','Relationship data not connected · will separate confirmed (filed) and inferred links with their evidence · source pending (REL-SOURCE)')))+
  sec('5.1.3','검색 전 추천','Before a search',(who?'<p class="small">'+T('검색한 기업 기준으로 봅니다: ','Showing the searched company: ')+'<b>'+who+'</b></p>':'')+
   na(T('검색어가 없을 때 매크로 주목 기업을 보여 줄 자리 · 매크로 근거 미산출(IA-13 결정 대기)','Where macro-highlighted companies will show when nothing is searched · macro basis not computed (IA-13 pending)'))+
   '<p class="small"><a href="#home">'+T('기업 검색하기 →','Search a company →')+'</a></p>')+
  sec('5.1.4','개인 설정','Personal settings','<p class="nw-fav"><span aria-hidden="true">★</span> '+T('관심 기업 ','Watchlist: ')+'<b class="num" data-news-interest-count>'+count+'</b>'+T('곳 · 이 기기에만 저장',' companies · stored on this device only')+'</p>'+
   '<p class="small">'+T('관계 종류 고르기는 관계 자료 연결 뒤 · 로그인 저장은 결정 대기','Choosing relation types comes after relationship data · account storage pending')+'</p><p class="small"><a href="#watchlist">'+T('관심 기업 관리 →','Manage watchlist →')+'</a></p>')+
  '</div>');
 const five=[['무슨 일','What happened'],['Q 예상','Q outlook'],['G 예상','G outlook'],['성격 · 단기/구조적 · 호재/악재','Nature · short-term/structural · positive/negative'],['주가 반영','Price reaction']];
 const g52=group('5.2','공시 · 뉴스','Filings · news',T('최신순 · 관심 기업 · 범위','Newest first · watchlist · scope'),
  P('scopes')+'<div id="news-disclosures"></div>'+
  sec('5.2.1','목록 · DART · 제공 뉴스','List · DART · provided news','<div id="news-dart-disclosures"></div>'+P('newsPane'),'nw-more','-more')+
  '<p class="small nw-legend nw-analysis-note">'+T('한 건마다 붙을 요약·영향 칸입니다. 아직 계산하지 않아 모두 미산출입니다. 점수에 반영하지 않습니다.','Per-item summary and impact slots. Not computed yet, so all say not computed. Never changes scores.')+'</p>'+
  '<div class="nw-grid nw-grid-52">'+
  sec('5.2.2','요약','Summary','<ol class="nw-five" data-news-five>'+five.map(([k,e])=>'<li><span class="nw-five-k">'+T(k,e)+'</span> <span class="badge NOT_AVAILABLE">'+T('미산출','Not computed')+'</span></li>').join('')+'</ol>'+
   '<p class="small">'+T('지금은 제목·링크·시각·분류만 · 5줄 요약 방식 결정 대기(IA-14)','Title, link, time and category only for now · five-line summary method pending (IA-14)')+'</p>')+
  sec('5.2.3','영향 분석','Impact',na(T('Q·G 예상 · 단기/구조적 · 호재/악재 모두 미산출 · 점수 영향 없음(score_effect NONE)','Q·G outlook, short-term/structural and positive/negative are not computed · no score effect (score_effect NONE)')))+
  sec('5.2.4','주가 반영 여부','Price reaction','<p class="nw-q"><span class="hl">'+T('주가 반영 여부는 알 수 있나?','Can “priced in” be known?')+'</span></p>'+
   '<p class="small">'+T('직접 알 수는 없습니다. 사건 전후 반응만 이 기기에서 볼 수 있고, 창·기준은 결정 대기(IA-15)입니다.','Not directly. Only the reaction around the event can be seen, on this device; the window and baseline are pending (IA-15).')+'</p>'+
   na(T('공개 자료에 가격이 없어 계산하지 않음','No prices in public data, so not computed'))+'<p class="small nw-marker">'+T('가격·가격에서 나온 값은 공개 화면에 싣지 않습니다.','Prices and values derived from them are never on the public pages.')+'</p>')+
  sec('5.2.6','컨센서스 변화','Consensus change',na(T('컨센서스 자료 미연결','Consensus data not connected')))+
  '</div>');
 const s53=sec('5.3','뉴스 내용구성 트리','News structure tree','<p class="small">'+T('수집 → 분류 → 관계망 · 목록 → 요약 → 개인화 구조와, 공개 자료에서 읽은 예시 값.','Collect → classify → network · list → summary → personal, with example values read from public data.')+'</p>'+
  '<p><a class="nw-tree-link" href="#tree/news">'+T('트리 보기 (메뉴 4.3)','Open the tree (menu 4.3)')+(D?' '+D.arrowShort('nw-arrow'):' →')+'</a></p>','nw-tree');
 return '<div class="nw-screen" data-news-layout>'+P('head')+
  '<p class="small nw-legend" data-fn-legend="5">'+T('도장 번호는 기능 번호(5.x)입니다. 위 메뉴 번호(4.x)와 다릅니다.','Stamp numbers are function numbers (5.x), not the menu numbers (4.x) above.')+'</p>'+
  P('toolbar')+P('overlay')+g51+g52+s53+'</div>';}
return Object.freeze({FILENAME,KIND,SCHEMA_VERSION:2,sourceRefresh,refreshResult,refreshStatus,refreshText,MATCH,IR_DOMAINS,CLASS_RULES,STOPWORDS,ATTRIBUTION,CLASSES,CHANNELS,GDELT_COMPANIES,IR_COMPANIES,STRUCTURAL_RULES,structuralCandidates,tokens,significant,classify,relevant,similar,validTitle,linkHost,irLinkAllowed,groups,validate,load,timeline,FILTER_KEY,FILTER_DEFAULT,TIERS,readFilters,writeFilters,rowCategory,rowOccurrence,rowTier,filterRows,mount,occurrenceSummary,screenHtml});
});
