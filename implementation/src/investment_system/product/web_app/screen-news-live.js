/* Feature 5 · 뉴스 · 공시 · 관계망 (spec v1.0 5.1–5.3 · menu 4 · route #/news[/<company code or id>]), the part that runs after
   IS2.ready. screen-news.js draws the first-paint skeleton (head, file band, sections 4-1 · 4-2 · 4-3 with a loading line) and hands
   its slots to IS2.newsLive.screen(route, refs) from this file (loader.js LOAD_ORDER, after the layer); nothing here touches the
   layer while the file loads (it only puts IS2.newsLive). Under node the file exports its pure parts (tools/web_app_news_node_test.js).
   Public + private two layers (FUNCTION_STATUS 1-3, DC-36, owner 2026-10-31):
   - 5.2 공시 · 뉴스 (public): the three public list files through the layer only — IS2.data.ready() (the page-open core set) and
     IS2.data.list('sec' | 'news' | 'dart') (DataRefresh's one read per publication, validated by the old readers SecDisclosures /
     NewsSignals / DartDisclosures, so the company page, this list and the 5.3 example show the same file). Ported from
     web_assets/news-signals.js (mount, timeline, filterRows, rowCategory / rowOccurrence / rowTier, occurrenceSummary,
     refreshStatus / refreshText), sec-disclosures.js (classLabel, evidence) and dart-disclosures.js (timeline, evidence) as the
     pure parts below; the node test compares each with the old function. One chronological list: 8-K / 6-K rows carry the IR
     releases that repeat their EX-99.1, a news event is one row with its later repeats folded, DART rows join by KST date.
     Filters (range, channel, class, new / repeat, order) only narrow or reorder the newest 30 rows (the disclosure minimum
     NEWS-CAP is an open owner decision); they live in this tab's memory (never stored: the store writes only inside a click and
     a select change is not one). Importance = held / watchlist / other / market only (holdings are not connected here: 보유 정보
     미연결); event materiality is not computed. Collection state per file and per news source for the companies in view
     (새 뉴스 반영 / 새 뉴스 없음 / 이전 자료 유지 · 최근 갱신 실패 never share words), the file's as_of and STALE line, GDELT
     attribution. A file that did not read shows its own words (IS2.data.state(name).text) and the other files stay (partial
     failure). Title, link, time, company and class only: no body text, no summary and no score effect.
     Not built and shown as such, never invented: 5.2.2 five-line summary and 5.2.3 impact (IA-14; an outside model call needs
     its own approval), 5.2.4 price reaction (no price in public files), 5.2.6 consensus (자료 미연결).
   - 5.2 private addition (table 1-3: 5.2.4 only, KIS daily / minute bars around an event): one IS2.parts.privatePanel
     (news-event-reaction), NOT_READY today; it sends and stores nothing and the public part never waits for it.
   - 5.1 관계망 (public; no private addition): the centre company is chosen with the shared company search (parts.searchBox +
     IS2.searchPart.attach, the one company list IS2.companies, Universe504), from the route or else the selected company
     (IS2.selection, RAM). Relationship data is not connected (REL-SOURCE): the centre and "관계 자료 미연결", no link drawn.
     ★ 관심 기업 is this device's interests list (IS2.store.prefs / savePrefs, the home's 즐겨찾기 list), written only inside the ★
     click; it also feeds the 관심 기업 range and the importance order of 5.2.
   - 5.3 뉴스 내용구성 트리 (public; no private addition): the structure (code) with the public counts and the newest example of
     each list from the same reads; a file that did not read gives NA and its words. Reads nothing else.
   No price, no holding, no request of its own, nothing stored but the ★ click's interests. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else api.install(typeof window==='object'&&window?window:root);})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
const FILES=Object.freeze({sec:'sec-disclosures.json',news:'news-signals.json',dart:'dart-disclosures.json'}),KEYS=Object.freeze(['sec','news','dart']);
const FILE_LABEL=Object.freeze({sec:'SEC 8-K',news:'뉴스·신호',dart:'DART'});
const LIMIT=30,SOURCES=Object.freeze(['GDELT','IR']),SUCCEEDED=Object.freeze(['UPDATED','NO_NEW_ITEMS']);
// Display words of the old readers [Korean, English] (news-signals.js CLASSES / CHANNELS / TIERS, sec-disclosures.js CLASSES,
// dart-disclosures.js CLASSES); the node test checks them against the old tables.
const NEWS_CLASS=Object.freeze({EARNINGS:['실적','Earnings'],PRODUCT:['제품·서비스','Product'],MA:['인수·합병','M&A'],LEGAL:['법률·규제','Legal / regulatory'],OTHER:['기타','Other']});
const SEC_CLASS=Object.freeze({RESULTS:['실적','Results'],OFFICERS_DIRECTORS:['임원·이사','Officers / directors'],MATERIAL_AGREEMENT:['중요 계약','Material agreement'],ACQUISITION_DISPOSITION:['인수·처분','Acquisition / disposition'],OTHER:['기타 공시','Other disclosure']});
const DART_CLASS=Object.freeze({RESULTS:['실적(잠정실적 공정공시)','Results (preliminary earnings)'],PERIODIC:['정기보고서','Periodic report'],MAJOR_EVENT:['주요사항보고서','Major event report'],FAIR_DISCLOSURE:['공정공시','Fair disclosure'],EXCHANGE:['거래소 공시','Exchange disclosure'],OTHER:['기타 공시','Other disclosure']});
const CHANNEL=Object.freeze({DISCLOSURE:'공시·확정',NEWS:'뉴스·신호'});
const TIERS=Object.freeze({HELD:'보유',INTEREST:'관심',OTHER:'기타 기업',MARKET:'시장'}),TIER_ORDER=Object.freeze(['HELD','INTEREST','OTHER','MARKET']);
const FILTER_DEFAULT=Object.freeze({channel:'ALL',category:'ALL',occurrence:'ALL',order:'TIME'});
const FILTER_VALUES=Object.freeze({channel:Object.freeze(['ALL','DISCLOSURE','NEWS']),occurrence:Object.freeze(['ALL','NEW','REPEAT']),order:Object.freeze(['TIME','IMPORTANCE'])});
// The two target companies outside the SEC lists' tickers (news-signals.js COMPANY_LABEL): their exchange codes.
const COMPANY_LABEL=Object.freeze({hanmi:'042700',tokyo_electron:'8035'});
const obj=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
const utc=t=>typeof t==='string'&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(t)?t.slice(0,10)+' '+t.slice(11,16)+' UTC':'—';
const hostOf=link=>{try{return new URL(link).hostname;}catch(_){return '';}};

/* ---------------------------------------------------------------- pure parts (ported; node test = the old functions) */
// A company id of the lists as shown: the one company list's ticker (IS2.companies.get), else the exchange code of the two
// non-SEC targets, else the id in capitals.
function labelOf(id,companies){let r=null;try{r=companies&&typeof companies.get==='function'?companies.get(id):null;}catch(_){r=null;}
 return r&&typeof r.ticker==='string'?r.ticker:Object.hasOwn(COMPANY_LABEL,id)?COMPANY_LABEL[id]:String(id).toUpperCase();}
// dart-disclosures.js timeline: one row per filing; time = the start of the KST filing day (ordering only).
function dartRows(dart,companyIds=null){return(dart&&Array.isArray(dart.events)?dart.events:[]).filter(e=>!companyIds||companyIds.includes(e.company_id))
 .map(e=>({channel:'DISCLOSURE',source:'DART',time:new Date(Date.parse(e.filing_date+'T00:00:00+09:00')).toISOString().slice(0,19)+'+00:00',company_id:e.company_id,event:e}));}
// news-signals.js timeline (newest first): 8-K rows carry the IR releases that repeat their EX-99.1 (an IR release whose 8-K is
// not listed stands alone as a repeat); each news group is one row (its NEW item) with later REPEAT reports folded; DART joins.
function timeline({sec=null,dart=null,news=null}={},{companyIds=null}={}){
 const pick=id=>!companyIds||companyIds.includes(id),rows=[],related=new Map(),byGroup=new Map();
 const events=(sec&&Array.isArray(sec.events)?sec.events:[]).filter(e=>pick(e.company_id)),accessions=new Set(events.map(e=>e.accession));
 for(const i of(news&&Array.isArray(news.items)?news.items:[]).filter(i=>pick(i.company_id))){
  if(i.relation==='RELATED_TO_8K'&&accessions.has(i.related_8k_accession)){if(!related.has(i.related_8k_accession))related.set(i.related_8k_accession,[]);related.get(i.related_8k_accession).push(i);}
  else if(i.relation==='RELATED_TO_8K')rows.push({channel:'NEWS',source:i.source,time:i.published_at,company_id:i.company_id,item:i,repeats:[],orphan:true});
  else{if(!byGroup.has(i.group_id))byGroup.set(i.group_id,[]);byGroup.get(i.group_id).push(i);}}
 for(const e of events)rows.push({channel:'DISCLOSURE',source:'SEC',time:e.accepted_at,company_id:e.company_id,event:e,related:related.get(e.accession)||[]});
 rows.push(...dartRows(dart,companyIds));
 for(const list of byGroup.values()){const head=list.find(i=>i.occurrence==='NEW')||list[list.length-1];rows.push({channel:'NEWS',source:head.source,time:head.published_at,company_id:head.company_id,item:head,repeats:list.filter(i=>i!==head),orphan:false});}
 return rows.sort((a,b)=>a.time<b.time?1:a.time>b.time?-1:0);}
// Category key: 실적 merges news EARNINGS with SEC / DART RESULTS; every other class keeps its source.
function rowCategory(row){if(row.channel==='NEWS'){const c=row.item.classification;return c==='EARNINGS'?'RESULTS':'NEWS:'+c;}const c=row.event.classification;return c==='RESULTS'?'RESULTS':(row.source==='DART'?'DART:':'SEC:')+c;}
function rowOccurrence(row){return row.channel==='NEWS'?(row.orphan?'REPEAT':row.item.occurrence):row.event.occurrence;}
function rowTier(row,{held=[],interests=[]}={}){if(!row.company_id)return 'MARKET';if(held.includes(row.company_id))return 'HELD';if(interests.includes(row.company_id))return 'INTEREST';return 'OTHER';}
// Same tier: newest first (input order).
function filterRows(rows,f=FILTER_DEFAULT,ctx={}){const out=rows.filter(r=>(f.channel==='ALL'||r.channel===f.channel)&&(f.category==='ALL'||rowCategory(r)===f.category)&&(f.occurrence==='ALL'||rowOccurrence(r)===f.occurrence));
 if(f.order!=='IMPORTANCE')return out;const rank=r=>TIER_ORDER.indexOf(rowTier(r,ctx));return out.map((r,i)=>[r,i]).sort((a,b)=>rank(a[0])-rank(b[0])||a[1]-b[1]).map(x=>x[0]);}
const catOrder=k=>k==='RESULTS'?'0':k.startsWith('NEWS:')?'1'+k:k.startsWith('SEC:')?'2'+k:'3'+k;
// The class options of a list (news-signals.js mount cats): 실적 first, then news, SEC and DART classes.
function categories(rows){return[...new Set(rows.map(rowCategory))].sort((a,b)=>catOrder(a)<catOrder(b)?-1:1);}
function categoryLabel(key){if(key==='RESULTS')return '실적';const[src,c]=key.split(':'),t=src==='NEWS'?NEWS_CLASS:src==='SEC'?SEC_CLASS:DART_CLASS,p=t[c];return(p?p[0]:c)+' · '+(src==='NEWS'?'뉴스':src);}
// A filter value kept in memory, checked like news-signals.js readFilters; an unknown class falls back to ALL.
function cleanFilters(f,cats=[]){const out={...FILTER_DEFAULT};if(!obj(f))return out;
 for(const k of Object.keys(FILTER_DEFAULT)){const x=f[k];if(k==='category'?typeof x==='string'&&(x==='ALL'||cats.includes(x)):FILTER_VALUES[k].includes(x))out[k]=x;}return out;}
// 5.2.5 counts of the rows a list shows (news-signals.js occurrenceSummary): new, repeat / amended, folded repeats.
function counts(rows){let fresh=0,again=0,folded=0;for(const row of rows){if(rowOccurrence(row)==='NEW')fresh++;else again++;folded+=row.channel==='NEWS'?row.repeats.length:Array.isArray(row.related)?row.related.length:0;}
 return{NEW:fresh,REPEAT:again,FOLDED:folded};}
// The range of the list: every company (null), the centre company, or this device's interests (possibly none).
function scopeIds(scope,{center=null,interests=[]}={}){return scope==='CENTER'&&center?[center]:scope==='INTEREST'?[...interests]:null;}
// news-signals.js sourceRefresh, over the companies the validated file lists for a source (GDELT: every key; IR: the companies
// with a listed feed, feed_status other than NOT_AVAILABLE; the reader refuses any other shape), narrowed to ids.
function sourceSummary(entries,all,listed,ids){const scope=ids?all.filter(id=>ids.includes(id)):all,list=scope.filter(listed);
 const ok=list.filter(id=>SUCCEEDED.includes(entries[id].last_result)),failed=list.filter(id=>entries[id].last_result==='FAILED').map(id=>entries[id].last_result_code),notRun=list.filter(id=>entries[id].last_result==='NOT_RUN').map(id=>entries[id].last_result_code);
 let result,code=null;if(ok.length&&!failed.length&&!notRun.length)result=ok.some(id=>entries[id].last_result==='UPDATED')?'UPDATED':'NO_NEW_ITEMS';
 else{result=ok.length?'PARTIAL_FAILED':failed.length?'FAILED':'NOT_RUN';code=failed.length||notRun.length?[...failed,...notRun][0]:'NOT_COLLECTED';}
 const acq=scope.map(id=>entries[id].acquired_at).filter(v=>v!==null).sort();
 return{result,code,last_success_at:acq.length?acq[acq.length-1]:null,succeeded:ok.length,failed:failed.length,not_run:notRun.length};}
// news-signals.js refreshStatus: per source for the companies in view. kind RECORDED (schema 2 run), NO_RUN (written without a
// collection), UNRECORDED (schema 1 copy), NO_FEED (no listed feed in view).
function refreshStatus(news,{companyIds=null}={}){if(!news)return[];const ids=Array.isArray(companyIds)?companyIds:null;
 return SOURCES.map(source=>{const entries=news.sources[source],all=Object.keys(entries).sort(),listed=id=>source==='GDELT'||entries[id].feed_status!=='NOT_AVAILABLE';
  const scope=ids?all.filter(id=>ids.includes(id)):all,list=scope.filter(listed);if(!list.length)return{source,kind:'NO_FEED',companies:0};
  const acq=list.map(id=>entries[id].acquired_at).filter(v=>v!==null).sort(),last=acq.length?acq[acq.length-1]:null;
  if(news.schema_version===1)return{source,kind:'UNRECORDED',companies:list.length,last_success_at:last};
  if(!news.refresh)return{source,kind:'NO_RUN',companies:list.length,last_success_at:last};
  const sum=sourceSummary(entries,all,listed,ids),bad=list.filter(id=>!SUCCEEDED.includes(entries[id].last_result));
  const carried=bad.map(id=>entries[id].acquired_at).filter(v=>v!==null).sort(),codes=[...new Set(bad.map(id=>entries[id].last_result_code))];
  const notRunOnly=bad.length>0&&bad.every(id=>entries[id].last_result==='NOT_RUN');
  return{source,kind:'RECORDED',companies:list.length,result:sum.result,code:sum.code,mixed_codes:codes.length>1,not_run_only:notRunOnly,
   checked_at:news.refresh.attempted_at,last_success_at:sum.last_success_at,carried_last:carried.length?carried[carried.length-1]:null,carried_from:carried.length?carried[0]:null,
   succeeded:sum.succeeded,failed:sum.failed+sum.not_run,any_updated:list.some(id=>entries[id].last_result==='UPDATED')};});}
// news-signals.js refreshText (Korean): 새 뉴스 없음 (answered, nothing new) and 조회 실패 (failed or not made) never share words.
function refreshText(st){const when=v=>v.slice(0,16).replace('T',' ')+' UTC',S=st.source==='IR'?'회사 IR':'GDELT';
 if(st.kind==='NO_FEED')return S+' · 보는 기업에 확인된 공식 피드 없음';
 if(st.kind==='UNRECORDED')return S+' · '+(st.last_success_at?'마지막 수집 '+when(st.last_success_at):'수집 자료 없음')+' · 최근 갱신 결과 미기록(이전 형식)';
 if(st.kind==='NO_RUN')return S+' · 이 파일은 수집 없이 만들어짐';
 const checked=when(st.checked_at),fail=()=>'최근 갱신 실패('+S+' '+(st.not_run_only?'요청 안 함 · ':'')+st.code+(st.mixed_codes?' 등':'')+', '+checked+')';
 const kept=()=>st.carried_last?'이전 자료 유지 · 마지막 성공 '+when(st.carried_last)+(st.carried_from&&st.carried_from!==st.carried_last?' (가장 오래된 수집 '+when(st.carried_from)+')':''):'이전 자료 없음';
 if(st.result==='UPDATED')return S+' · 새 뉴스 반영 · 확인 '+checked;
 if(st.result==='NO_NEW_ITEMS')return S+' · 새 뉴스 없음 · 확인 '+checked;
 if(st.result==='PARTIAL_FAILED')return S+' · 일부 갱신 실패 '+st.failed+'/'+st.companies+'곳 · '+kept()+' · '+fail()+' · 나머지 '+st.succeeded+'곳 '+(st.any_updated?'새 뉴스 반영':'새 뉴스 없음')+' · 확인 '+checked;
 return S+' · '+kept()+' · '+fail();}
// The one badge of news-signals.js mount over the recorded sources: null (none recorded), OK, PARTIAL_FAILED or FAILED.
function refreshBadge(rows){const r=rows.filter(x=>x.kind==='RECORDED');if(!r.length)return null;
 return r.every(x=>SUCCEEDED.includes(x.result))?'OK':r.some(x=>SUCCEEDED.includes(x.result)||x.result==='PARTIAL_FAILED')?'PARTIAL_FAILED':'FAILED';}
// A list file whose acquisition refresh is overdue (the old mounts: as_of + stale_after_seconds passed, unless NOT_AVAILABLE).
const isStale=(p,now)=>!!p&&p.state!=='NOT_AVAILABLE'&&now-Date.parse(p.as_of)>p.stale_after_seconds*1000;
// sec-disclosures.js classLabel (Korean): the four highlighted kinds by short label, any other report by its first official
// item name (9.01 exhibits last). items = SecDisclosures.ITEMS ({code: [English, Korean]}).
function secClassLabel(e,items={}){const first=e.classification==='OTHER'?e.items.find(c=>c!=='9.01')||e.items[0]:null;
 if(first&&items[first]){const[en,ko]=items[first];return ko+' ('+en+')';}const[k,en]=SEC_CLASS[e.classification]||[e.classification,e.classification];return k+' ('+en+')';}
function secItemsText(e,items={}){return e.items.map(c=>items[c]?c+' '+items[c][1]+' ('+items[c][0]+')':c).join(' / ')||(['6-K','6-K/A'].includes(e.form)?'분기 실적 6-K · 공시 첨부 제목 확인':'항목 미제공');}
const dartClassLabel=c=>{const[k,en]=DART_CLASS[c]||[c,c];return k+' ('+en+')';};
const newsClassLabel=c=>{const[k,en]=NEWS_CLASS[c]||[c,c];return k+' ('+en+')';};
// The dedup line of an evidence box (sec / dart evidence(), news-signals.js newsEvidence).
function filingDedup(e,key){return e.occurrence==='NEW'?'새 공시 · 묶음 시작':e.group_id===e.company_id+':'+key?'정정·반복 · 원 공시를 하나로 특정하지 못해 단독 표시':'정정·반복 · 원 공시 묶음 '+e.group_id;}
function newsDedup(row){const i=row.item;return row.orphan?'8-K 관련 IR 보도자료 · 그 8-K('+i.related_8k_accession+')가 목록에 없어 단독 표시'
 :row.repeats.length?'같은 사건 묶음 · 첫 보도 + 반복 '+row.repeats.length+'건 (72시간 안 제목 유사)':i.occurrence==='NEW'?'새 소식 · 반복 보도 없음':'반복 보도 · 첫 보도는 목록 범위 밖';}
// The latest refresh of the item's company feed (news-signals.js mount latest()).
function newsLatest(news,i){const c=news&&news.sources&&news.sources[i.source]?news.sources[i.source][i.company_id]:null,r=c?c.last_result:null;
 if(!news||news.schema_version===1||!news.refresh||!r)return '결과 미기록';const at=' · '+utc(news.refresh.attempted_at);
 return r==='UPDATED'?'새 뉴스 반영'+at:r==='NO_NEW_ITEMS'?'새 뉴스 없음'+at:(r==='FAILED'?'조회 실패 ':'요청 안 함 ')+c.last_result_code+at+' · 이 행은 이전 수집분';}
const occurrenceLabel=row=>row.channel==='NEWS'?(row.orphan?'8-K 관련 · 반복':row.item.occurrence==='NEW'?'새 소식':'반복 보도'):row.event.occurrence==='NEW'?'새 공시':'정정·반복';
// 5.3 example values: count, file as_of and the newest row of each list (ia-screens.js newsExamples; DART added), or null.
function treeFacts({sec=null,news=null,dart=null}={}){
 const newest=(rows,key)=>rows.reduce((a,x)=>!a||String(x[key])>String(a[key])?x:a,null);
 return{sec:sec?{count:sec.events.length,as_of:sec.as_of,latest:newest(sec.events,'accepted_at')}:null,
  news:news?{count:news.items.length,as_of:news.as_of,latest:newest(news.items,'published_at')}:null,
  dart:dart?{count:dart.events.length,as_of:dart.as_of,latest:dart.events.reduce((a,x)=>!a||x.filing_date>a.filing_date||x.filing_date===a.filing_date&&x.rcept_no>a.rcept_no?x:a,null)}:null};}

/* ---------------------------------------------------------------- the screen (browser only) */
function install(win){
const I=win.IS2;
// View state of this page (kept across routes, dropped by a reload; never stored).
const V={scope:null,f:{...FILTER_DEFAULT}};
function screen(route,{legend,band,slots}){
 const{h,href}=I,signal=route.signal,aborted=()=>signal.aborted,doc=win.document;
 const mascot=m=>I.parts.mascot(m);
 const put=(box,...c)=>{box.replaceChildren();I.append(box,c);return box;};
 const loading=what=>h('p',{class:'pending',role:'status',dataset:{state:'loading'}},'불러오는 중 · ',what);
 const failed=(code,text)=>h('div',{class:'sk state-card',dataset:{state:'error',na:code}},mascot('alarm'),h('p',{class:'err'},text));
 const empty=(code,text)=>h('div',{class:'sk state-card',dataset:{state:'empty',na:code}},mascot('plain'),h('p',null,text));
 const prep=(what,missing)=>{const t='준비 중 · '+what,n=typeof I.parts.notReady==='function'?I.parts.notReady(t,missing):h('p',{class:'pending',dataset:{notReady:''}},t,' · 없는 것: ',missing.join(' · '));n.dataset.prep='';return n;};
 const sub=(title,fn,hand)=>h('div',{class:'lb-head'},h('h3',{class:'stamp sub'},title),fn?h('span',{class:'meta'},'기능 ',fn):null,hand?h('span',{class:'hand'},hand):null);
 const block=(id,...c)=>h('div',{class:'sk card',dataset:{block:id}},...c);
 const dl=rows=>h('dl',{class:'card-body'},rows.map(([k,v,attrs])=>[h('dt',null,h('b',null,k)),h('dd',attrs||null,v)]));
 const ext=(link,text,attrs)=>h('a',{href:link,target:'_blank',rel:'noopener noreferrer',...(attrs||{})},text);
 const fileState=n=>{try{return I.data.state(n);}catch(_){return{state:'FAILED',why:null,as_of:null,text:''};}};
 const focusLater=sel=>{const x=doc.querySelector(sel);if(x)x.focus();};
 const panel=(id,title)=>{try{return I.parts.privatePanel({id,title}).node;}catch(_){return null;}};
 const S={companies:null,lists:null,center:null,given:typeof route.params[0]==='string'&&route.params[0]?route.params[0]:null,fromRoute:false};
 const now=()=>Date.now();

 /* ---------------- interests (this device; the home's 즐겨찾기 list) */
 function prefs(){let p=null;try{p=I.store.prefs();}catch(_){p=null;}return p&&(p.state==='OK'||p.state==='EMPTY'||p.state==='INVALID')?p:{state:'INVALID',value:null};}
 const interests=()=>{const p=prefs();return p.state==='INVALID'?[]:[...p.value.interests];};
 const SAVE_WORDS={PREFS_STORAGE_INVALID:'이 기기의 관심 기업 기록을 읽을 수 없어 바꿀 수 없습니다',CLICK_REQUIRED:'버튼을 직접 눌러야 저장합니다',ACTION_ALREADY_STARTED:'버튼을 직접 눌러야 저장합니다'};
 const starText=on=>[h('span',{'aria-hidden':'true'},on?'★ ':'☆ '),'관심 기업',on?h('span',{'aria-hidden':'true'},' 해제'):''];
 // ★ adds / removes the id in the interests on a click (unstarring also leaves the groups, the validator needs it).
 function starButton(id){
  const btn=h('button',{type:'button',class:'chip star','aria-pressed':'false',disabled:true,dataset:{newsStar:id}},...starText(false)),why=h('span',{class:'reason',role:'status',dataset:{newsStarWhy:''}});
  const paint=()=>{const p=prefs();if(p.state==='INVALID'){btn.disabled=true;why.textContent=SAVE_WORDS.PREFS_STORAGE_INVALID;return;}
   const on=p.value.interests.includes(id);btn.disabled=false;btn.setAttribute('aria-pressed',String(on));btn.replaceChildren(...starText(on));};
  btn.addEventListener('click',e=>{const p=prefs();if(p.state==='INVALID')return;const v=p.value,on=v.interests.includes(id);
   const next={version:1,interests:on?v.interests.filter(x=>x!==id):[...v.interests,id],groups:v.groups.map(g=>({id:g.id,name:g.name,members:on?g.members.filter(x=>x!==id):[...g.members]}))};
   let ok=true;try{I.store.savePrefs(e,next);why.textContent=on?'관심 기업에서 뺐습니다 · 이 기기':'관심 기업으로 저장했습니다 · 이 기기';}
   catch(err){ok=false;const c=String(err&&err.message).split(' ')[0];why.textContent='저장하지 않음 · '+(SAVE_WORDS[c]||'저장하지 못했습니다');}
   paint();if(ok){paintMine();paintLists();}});
  paint();
  return h('span',{class:'star-wrap'},btn,why);}

 /* ---------------- 5.1 관계망 */
 const box=I.parts.searchBox('news-center',h('label',{for:'news-center',class:'hand'},'가운데 기업 고르기 · 티커 · 영문 회사명 (Universe504)'));
 const centerBody=h('div',{class:'card-body',dataset:{newsCenter:''}},loading('기업 목록'));
 // Decoration only (aria-hidden): the centre (marker) and dashed empty places; the caption carries the meaning.
 function sketch(label){
  const P=[[42,26],[200,24],[206,96],[36,98]];
  return h('svg:svg',{viewBox:'0 0 240 120',width:'240',height:'120','aria-hidden':'true',focusable:'false',dataset:{newsSketch:''}},
   P.map(([x,y])=>h('svg:path',{d:'M120 60 L'+x+' '+y,fill:'none',stroke:'#808080','stroke-width':'2','stroke-dasharray':'5 4'})),
   P.map(([x,y])=>h('svg:circle',{cx:String(x),cy:String(y),r:'13',fill:'#ffffff',stroke:'#808080','stroke-width':'2','stroke-dasharray':'4 3'})),
   h('svg:circle',{cx:'120',cy:'60',r:'24',fill:label?'#FFE45C':'#ffffff',stroke:'#161616','stroke-width':'3'}),
   h('svg:text',{x:'120',y:'64','text-anchor':'middle','font-size':'11',fill:'#161616'},label||'?'));}
 function paintCenter(){
  const r=S.companies,c=S.center;
  if(r&&r.state==='FAILED'){put(centerBody,failed('COMPANIES_FAILED','기업 목록을 불러오지 못했습니다 · '+(r.missing.join(' · ')||'Universe504 목록')));return;}
  const rel=prep('관계 자료 미연결 · 연결된 기업을 그리지 않음 · 지어내지 않음',['기업 관계 자료원 결정 (REL-SOURCE)']);rel.dataset.na='REL_SOURCE';
  if(!c){
   const lost=S.fromRoute&&S.given;
   put(centerBody,lost?empty('CENTER_NOT_FOUND','이 이름의 기업을 Universe504 목록에서 찾지 못했습니다 · '+S.given):empty('NO_CENTER','가운데 기업 없음 · 위에서 기업을 검색해 고르세요'),
    h('div',{class:'card-body'},sketch(null),h('p',{class:'reason',dataset:{sketchCaption:''}},'가운데 원 = 지금 보는 기업 (선택 안 함) · 점선 = 관계 자료 미연결 (빈 자리 · 연결 아님)')),rel);return;}
  const name=c.name_ko||c.name_en,ended=c.status==='WITHDRAWN'?c.withdrawn_on:null;
  put(centerBody,h('h4',{dataset:{centerCode:c.code}},c.ticker,name?' · '+name:''),
   h('p',{class:'reason'},c.code,' · Universe504',ended?h('span',{dataset:{listingEnded:ended}},' · 상장 종료 ',ended,' · 점수 없음'):null),
   h('div',{class:'links'},starButton(c.id),h('a',{class:'lk',href:href('company',c.id),dataset:{centerCompany:''}},'기업 화면 →'),
    h('button',{type:'button',class:'chip',dataset:{centerClear:''},onclick:()=>{I.selection.set(null);if(route.id==='news'&&route.params.length)win.location.hash=href('news');else{S.center=null;S.given=null;paintCenter();paintLists();focusLater('#news-center');}}},'가운데 기업 비우기')),
   h('div',{class:'card-body'},sketch(c.ticker),h('p',{class:'reason',dataset:{sketchCaption:''}},'가운데 원 = ',c.ticker,' · 점선 = 관계 자료 미연결 (빈 자리 · 연결 아님)')),rel);}
 const mineBody=h('div',{class:'card-body',dataset:{newsMine:''}},loading('관심 기업'));
 function paintMine(){
  const p=prefs(),C=I.companies;
  if(p.state==='INVALID'){put(mineBody,h('p',{class:'err',dataset:{na:'PREFS_STORAGE_INVALID'}},SAVE_WORDS.PREFS_STORAGE_INVALID));return;}
  const ids=p.value.interests;
  put(mineBody,h('p',{dataset:{interestCount:String(ids.length)}},h('span',{'aria-hidden':'true'},'★ '),'관심 기업 ',h('b',null,String(ids.length)),'곳 · 이 기기에만 저장 · 기기 백업에 들어감 · 홈의 즐겨찾기와 같은 목록'),
   ids.length?h('div',{class:'links',dataset:{interestList:''}},ids.map(id=>{const r=C.get(id);
    return r?h('a',{class:'chip mine',href:href('news',r.id),dataset:{interest:id}},h('span',{'aria-hidden':'true'},'★ '),r.ticker,h('span',{class:'sr-only'},' 가운데로 보기'))
     :h('span',{class:'chip mine',dataset:{interest:id}},h('span',{'aria-hidden':'true'},'★ '),labelOf(id,C),' · Universe504 밖');}))
    :h('p',{class:'reason',dataset:{interestEmpty:''}},'관심 기업 없음 · 5.1.1에서 ★를 누르면 이 기기에 저장됩니다'),
   h('p',{class:'reason'},'관계 종류 고르기는 관계 자료 연결 뒤 · 계정 저장은 결정 대기'));}

 /* ---------------- 5.2 rows */
 const companyLink=id=>{const r=I.companies.get(id),t=labelOf(id,I.companies);return r?h('a',{href:href('company',r.id),dataset:{rowCompany:id}},t):h('span',{dataset:{rowCompany:id}},t);};
 const tierChip=t=>h('span',{class:t==='INTEREST'?'chip mine':'chip',dataset:{importance:t}},t==='INTEREST'?'★ 관심':TIERS[t]);
 const chips=(row,cls,tier)=>h('div',{class:'links',dataset:{rowChips:''}},h('span',{class:'chip',dataset:{channelLabel:row.channel}},CHANNEL[row.channel]),
  h('span',{class:'chip',dataset:{occurrenceLabel:row.orphan?'RELATED_TO_8K':rowOccurrence(row)}},occurrenceLabel(row)),h('span',{class:'chip',dataset:{classLabel:''}},cls),tierChip(tier));
 const evidence=(kind,entries)=>h('details',{dataset:{evidence:kind}},h('summary',{class:'lk'},'근거 보기'),dl(entries));
 const srcLabel=s=>s==='IR'?'회사 IR':'GDELT';
 const line=i=>h('li',{dataset:{newsItem:'',newsSource:i.source,newsOccurrence:i.occurrence}},ext(i.link,i.title,{dataset:{newsLink:''}}),' · ',srcLabel(i.source),' · ',utc(i.published_at),' · ',hostOf(i.link));
 function secRow(row,tier,L){
  const e=row.event,items=win.SecDisclosures&&win.SecDisclosures.ITEMS||{},x=e.exhibit_99_1;
  const src=h('span',null,ext(e.link,'SEC EDGAR '+e.form+' ↗',{dataset:{evidenceLink:''}}),x.state==='AVAILABLE'?[' · ',ext(x.url,'EX-99.1 ↗',{dataset:{evidenceLink:''}})]:null);
  return h('li',{class:'sk card card-body',dataset:{row:e.accession,channel:'DISCLOSURE',source:'SEC',occurrence:e.occurrence,classification:e.classification}},chips(row,secClassLabel(e,items),tier),
   h('p',null,companyLink(e.company_id),' · SEC ',e.form,' · ',utc(e.accepted_at)),
   x.state==='AVAILABLE'?h('p',null,ext(x.url,x.title,{dataset:{exhibitLink:''}}),' · EX-99.1 ↗'):h('p',{class:'reason',dataset:{na:x.reason_code}},'EX-99.1 없음 · ',x.reason_code),
   h('p',{class:'reason',dataset:{items:e.items.join(',')}},secItemsText(e,items)),
   ext(e.link,'SEC 원문 목록 보기 ↗',{class:'lk',dataset:{filingLink:''}}),
   row.related.length?h('details',{dataset:{relatedIr:String(row.related.length)}},h('summary',{class:'lk'},'관련 IR 보도자료 ',String(row.related.length),'건 · 8-K와 같은 발표(반복)'),h('ul',{class:'news-lines'},row.related.map(line))):null,
   evidence('SEC',[['구분','공시·확정 · 회사가 SEC에 제출한 원문'],['출처',src],['접수 시각',utc(e.accepted_at)],['제출일 · 사건일',e.filing_date+' · '+(e.event_date||'미제공')],
    ['수집 시각',utc(e.first_seen_at)+' · 처음 확인'],['중복 처리',filingDedup(e,e.accession)],['점수 영향','없음']]));}
 function dartRow(row,tier){
  const e=row.event;
  return h('li',{class:'sk card card-body',dataset:{row:e.rcept_no,channel:'DISCLOSURE',source:'DART',occurrence:e.occurrence,classification:e.classification}},chips(row,dartClassLabel(e.classification),tier),
   h('p',null,companyLink(e.company_id),' · DART · ',e.filing_date,' KST'),h('p',null,ext(e.link,e.title,{dataset:{filingLink:''}}),' ↗'),
   evidence('DART',[['구분','공시·확정 · 회사가 제출한 원문'],['출처',ext(e.link,'DART 원문 열기 ↗',{dataset:{evidenceLink:''}})],['접수일',e.filing_date+' KST · 시각 미제공'],
    ['수집 시각',utc(e.first_seen_at)+' · 처음 확인'],['접수번호',e.rcept_no],['중복 처리',filingDedup(e,e.rcept_no)],['점수 영향','없음']]));}
 function newsRow(row,tier,L){
  const i=row.item,news=L.news,c=news&&news.sources[i.source]?news.sources[i.source][i.company_id]:null,acq=c?c.acquired_at:null;
  const src=h('span',null,ext(i.link,hostOf(i.link)+' ↗',{dataset:{evidenceLink:''}}),i.source==='GDELT'?' · 수집 경로: The GDELT Project':'');
  return h('li',{class:'sk card card-body',dataset:{row:i.group_id,channel:'NEWS',source:i.source,occurrence:i.occurrence,classification:i.classification}},chips(row,newsClassLabel(i.classification),tier),
   h('p',null,companyLink(i.company_id),' · ',srcLabel(i.source),' · ',utc(i.published_at),' · ',hostOf(i.link)),h('p',null,ext(i.link,i.title,{dataset:{newsLink:''}}),' ↗'),
   row.repeats.length?h('details',{dataset:{newsRepeats:String(row.repeats.length)}},h('summary',{class:'lk'},'같은 사건 반복 보도 ',String(row.repeats.length),'건'),h('ul',{class:'news-lines'},row.repeats.map(line))):null,
   evidence('NEWS',[['구분',i.source==='IR'?'뉴스·신호 · 회사 IR 보도자료 (공시 아님)':'뉴스·신호 · 언론 보도 제목 (내용 미확인)'],['출처',src],['발표 시각',utc(i.published_at)],
    ['수집 시각',acq?utc(acq)+' · 이 기업 피드 수집':'미제공'],['최근 갱신',newsLatest(news,i)],['기업 연결',i.source==='GDELT'?'제목 속 회사 이름·티커':'회사 공식 IR 도메인'],
    ['분류 근거','제목 단어 규칙'],['중복 처리',newsDedup(row)],['점수 영향','없음']]));}
 const renderRow=(row,ctx,L)=>{const t=rowTier(row,ctx);return row.channel==='NEWS'?newsRow(row,t,L):row.source==='DART'?dartRow(row,t):secRow(row,t,L);};

 /* ---------------- 5.2 list, counts, collection state; 5.3 facts; the band */
 const listBody=h('div',{class:'lb',dataset:{newsList:''}},loading('공시 · 뉴스'));
 const occBody=h('div',{class:'card-body',dataset:{newsOccurrence:''}},loading('신규 · 중복 · 변경'));
 const statusBody=h('div',{class:'card-body',dataset:{newsStatus:''}},loading('수집 상태'));
 const factsBody=h('div',{class:'card-body',dataset:{newsFacts:''}},loading('공개 목록 건수'));
 // Per file: {key, file, state, text, value}: OK with its validated payload, else the file's own words.
 function files(){return KEYS.map(k=>{const f=fileState(FILES[k]),v=S.lists&&S.lists.values?S.lists.values[k]:null;
  if(v)return{key:k,file:FILES[k],state:'OK',text:'',value:v};
  const st=f.state==='NOT_PUBLISHED'?'NOT_PUBLISHED':'FAILED',text=f.text||(f.state==='NOT_READ'?'읽기 실패 · 읽기 모듈 없음':'읽기 실패');return{key:k,file:FILES[k],state:st,text,value:null};});}
 const missLine=f=>h('p',{class:'err',dataset:{fileMissing:f.key,fileState:f.state}},FILE_LABEL[f.key],' 파일',f.state==='NOT_PUBLISHED'?'이 아직 게시되지 않았습니다':'을 읽지 못했습니다',' · ',f.text);
 function scopeNow(){const c=S.center,want=V.scope||(c?'CENTER':'ALL');return want==='CENTER'&&!c?'ALL':want;}
 function paintBand(){
  const chip=f=>{const s=fileState(f.file),ok=f.state==='OK';return h('span',{class:'chip'+(ok?'':' err'),dataset:{file:f.file,fileState:f.state}},FILE_LABEL[f.key],' · ',ok?'기준 '+utc(f.value.as_of):f.text);};
  put(band,...files().map(chip));}
 function paintLists(){
  if(!S.lists)return;
  if(S.lists.error){for(const b of[listBody,occBody,statusBody,factsBody])put(b,failed('DATA_FAILED','공개 자료를 읽지 못했습니다 · 새로고침해 주세요'));
   put(band,h('span',{class:'chip err',dataset:{fileState:'DATA_FAILED'}},'공개 자료 읽기 실패'));return;}
  paintBand();
  const F=files(),got=Object.fromEntries(F.map(f=>[f.key,f.value])),miss=F.filter(f=>f.state!=='OK');
  const scope=scopeNow(),mine=interests(),ids=scopeIds(scope,{center:S.center?S.center.id:null,interests:mine});
  const all=timeline({sec:got.sec,news:got.news,dart:got.dart},{companyIds:ids}),rows=all.slice(0,LIMIT),ctx={held:[],interests:mine};
  // ---- 5.2.5
  if(miss.length===F.length)put(occBody,failed('LISTS_FAILED','공시·뉴스 파일을 하나도 읽지 못해 셀 수 없습니다'));
  else{const n=counts(rows);put(occBody,h('dl',{class:'card-body',dataset:{occurrenceCounts:''}},[['새 소식 · 새 공시',n.NEW,'NEW'],['반복 보도 · 정정 공시',n.REPEAT,'REPEAT'],['묶어 접은 반복 보도',n.FOLDED,'FOLDED']]
    .map(([k,v,key])=>[h('dt',null,h('b',null,k)),h('dd',{dataset:{occurrenceCount:key}},String(v),'건')])),
   h('p',{class:'reason'},'최신 ',String(LIMIT),'행 기준 (보는 범위) · 72시간 안 비슷한 제목은 한 사건으로 묶음 · 8-K와 같은 IR 보도자료는 그 8-K 아래 · 목록의 "신규·반복" 조건으로 거를 수 있음'));}
  // ---- 5.2.7
  const news=got.news,st=refreshStatus(news,{companyIds:ids}),badge=refreshBadge(st),t=now();
  const stateChip=f=>{const s=f.value?f.value.state:f.state;return h('span',{class:'chip'+(s==='LIVE'?'':' err'),dataset:{listState:f.key,listValue:s}},f.key==='news'?CHANNEL.NEWS+' · GDELT · IR':CHANNEL.DISCLOSURE+' · '+FILE_LABEL[f.key],' · ',s);};
  const fileLines=f=>{if(!f.value)return[missLine(f)];const p=f.value,win_=f.key==='news'?14:90,out=[h('p',{class:'meta',dataset:{listAsOf:f.key}},FILE_LABEL[f.key],' · 기준 ',utc(p.as_of),' · 최근 ',String(win_),'일',f.key==='dart'?' · 접수일(KST)만 제공':'')];
   if(isStale(p,t))out.push(h('p',{class:'err',dataset:{listStale:f.key}},'STALE · ',FILE_LABEL[f.key],' · 수집 갱신 시각 경과'));
   if(f.key==='sec'){const n={LIVE:0,STALE:0,NOT_AVAILABLE:0};for(const c of Object.values(p.companies))n[c.state]++;
    out.push(h('p',{class:'reason',dataset:{secCompanies:''}},'SEC 8-K 수집 기업 ',String(Object.keys(p.companies).length),'곳 · 수집됨 ',String(n.LIVE),' · 오래됨 ',String(n.STALE),' · 수집 전 ',String(n.NOT_AVAILABLE)));}
   if(f.key==='dart'){const r=Object.values(p.companies).map(c=>c.reason_code).find(Boolean);if(p.state==='NOT_AVAILABLE'&&r)out.push(h('p',{class:'reason',dataset:{dartReason:r}},'DART · NOT_AVAILABLE · ',r));}
   if(f.key==='news')for(const r of st){const bad=r.kind==='RECORDED'&&!SUCCEEDED.includes(r.result);out.push(h('p',{class:bad?'err':'reason',dataset:{newsRefresh:r.source,newsRefreshResult:r.kind==='RECORDED'?r.result:r.kind}},refreshText(r)));}
   return out;};
  put(statusBody,h('div',{class:'links',dataset:{listStates:''}},F.map(stateChip),badge&&badge!=='OK'?h('span',{class:'chip err',dataset:{newsRefreshBadge:badge}},badge==='FAILED'?'최근 갱신 실패 · 이전 자료 유지':'일부 갱신 실패'):null),
   ...F.flatMap(fileLines),
   news?h('p',{class:'reason',dataset:{newsAttribution:''}},'뉴스·신호 출처: ',ext('https://www.gdeltproject.org/','The GDELT Project',{dataset:{gdeltAttribution:''}}),' (GDELT DOC 2.0 API) · 회사 IR 보도자료 피드 · 제목·링크만 표시, 기사는 각 언론사 소유'):null,
   h('p',{class:'reason',dataset:{scoreEffect:'NONE'}},'점수에 반영하지 않음 · 제목·링크·시각·기업·분류만 표시'),
   ids?h('p',{class:'reason'},'갱신 결과는 보는 범위의 기업 기준 (',scope==='CENTER'?'가운데 기업':'관심 기업',')'):null);
  // ---- 5.2.1
  paintList(F,miss,all,rows,ctx,scope,got);
  // ---- 5.3 facts
  const tf=treeFacts(got),C=I.companies;
  const fact=(key,label,f,show)=>{const v=tf[key];return[h('dt',null,h('b',null,label)),v?h('dd',{dataset:{treeFact:key,exampleCount:String(v.count)}},String(v.count),'건 · 파일 기준 ',utc(v.as_of),v.latest?[h('br'),h('span',{class:'reason'},'최신: ',show(v.latest))]:null)
   :h('dd',{dataset:{treeFact:key,exampleCount:'NA',na:f.state}},'— · NA · ',f.text)];};
  const fk=k=>F.find(f=>f.key===k);
  put(factsBody,h('p',{class:'reason'},'공개 파일의 건수와 가장 최근 한 건 · 4.2 목록과 같은 읽기'),h('dl',{class:'card-body',dataset:{treeFacts:''}},
   fact('sec','SEC 8-K',fk('sec'),e=>labelOf(e.company_id,C)+' · '+e.form+' · '+(e.items.join(',')||'항목 없음')+' · '+utc(e.accepted_at)),
   fact('news','뉴스·IR',fk('news'),i=>labelOf(i.company_id,C)+' · '+srcLabel(i.source)+' · '+NEWS_CLASS[i.classification][0]+' · '+utc(i.published_at)),
   fact('dart','DART',fk('dart'),e=>labelOf(e.company_id,C)+' · '+dartClassLabel(e.classification)+' · '+e.filing_date+' KST'),
   h('dt',null,h('b',null,'관계')),h('dd',{dataset:{treeFact:'rel',exampleCount:'NA',na:'REL_SOURCE'}},'— · NA · 관계 자료 없음 (REL-SOURCE)')));}
 function paintList(F,miss,all,rows,ctx,scope,got){
  const top=[...miss.map(missLine)];
  if(miss.length===F.length){put(listBody,failed('LISTS_FAILED','공시·뉴스 파일을 하나도 읽지 못했습니다 · '+miss.map(f=>FILE_LABEL[f.key]+' '+f.text).join(' · ')));return;}
  const cats=categories(all);V.f=cleanFilters(V.f,cats);
  const c=S.center,C=I.companies;
  const sel=(name,label,options,{disabled=[]}={})=>h('label',{class:'check'},h('span',{class:'nobr'},label),h('select',{'aria-label':label,dataset:{newsFilter:name},onchange:e=>change(name,e.target.value)},
   options.map(([v,t])=>h('option',{value:v,selected:(name==='scope'?scope:V.f[name])===v,disabled:disabled.includes(v)},t))));
  const bar=h('div',{class:'links',role:'group','aria-label':'공시·뉴스 보기 조건',dataset:{newsFilters:''}},
   sel('scope','범위',[['ALL','전체 기업'],['CENTER',c?'가운데 기업 · '+c.ticker:'가운데 기업 (없음)'],['INTEREST','관심 기업 ★ · 이 기기']],{disabled:c?[]:['CENTER']}),
   sel('channel','채널',[['ALL','전체'],['DISCLOSURE',CHANNEL.DISCLOSURE],['NEWS',CHANNEL.NEWS]]),
   sel('category','분류',[['ALL','전체'],...cats.map(k=>[k,categoryLabel(k)])]),
   sel('occurrence','신규·반복',[['ALL','전체'],['NEW','새 소식·새 공시'],['REPEAT','반복·정정']]),
   sel('order','정렬',[['TIME','시간순 (최신 먼저)'],['IMPORTANCE','중요도 순 (보유→관심→기타→시장)']]),
   h('button',{type:'button',class:'chip',dataset:{newsFilterReset:''},onclick:()=>{V.f={...FILTER_DEFAULT};paintLists();focusLater('[data-news-filter-reset]');}},'조건 초기화'));
  const basis=h('p',{class:'reason',dataset:{importanceBasis:''}},'중요도 기준: 보유·관심 여부 · 사건 자체의 중요도는 계산하지 않음 · 같은 그룹은 최신 먼저 · 보유 정보 미연결 · 조건은 이 탭에서만 기억 (저장 안 함)');
  const count=h('p',{class:'reason',role:'status',dataset:{newsFilterCount:''}}),body=h('div',{dataset:{newsBody:''}});
  function change(name,value){if(name==='scope')V.scope=value;else V.f={...V.f,[name]:value};paintLists();focusLater('[data-news-filter="'+name+'"]');}
  put(listBody,...top,bar,basis,count,body);
  if(!all.length){
   const ids=scopeIds(scope,{center:c?c.id:null,interests:ctx.interests});
   put(body,scope==='INTEREST'&&!ids.length?empty('NO_INTERESTS','관심 기업(★)이 없습니다 · 4.1에서 ★를 눌러 고르세요 · 이 기기에만 저장')
    :scope==='CENTER'?empty('CENTER_EMPTY','공개 파일에 '+c.ticker+' 소식이 없습니다 · 지금은 고정 대상 기업만 수집합니다')
    :scope==='INTEREST'?empty('INTEREST_EMPTY','관심 기업의 공시·뉴스가 없습니다 · 지금은 고정 대상 기업만 수집합니다')
    :empty('NO_ROWS','표시할 공시·뉴스가 없습니다'));
   count.textContent='표시 0건';return;}
  const shown=filterRows(rows,V.f,ctx),outside=filterRows(all.slice(LIMIT),{...V.f,order:'TIME'},ctx).length;
  count.textContent='표시 '+shown.length+'건 · 최신 '+LIMIT+'행 안에서 거름'+(outside?' · 조건에 맞는 '+outside+'건은 최신 '+LIMIT+'행 밖이라 표시 안 함 (공시 최소 보장은 사용자 결정 대기)':'');
  if(!shown.length){put(body,h('p',{class:'reason',dataset:{newsFilterEmpty:''}},'조건에 맞는 항목이 없습니다 · 조건 초기화로 돌아갈 수 있음'));return;}
  put(body,h('ol',{class:'news-rows',dataset:{timeline:''},'aria-label':'공시·뉴스 목록 · 최신 먼저'},shown.map(r=>renderRow(r,ctx,got))));}

 /* ---------------- 5.3 tree (code) */
 const TREE=[['input','수집','SEC 8-K (sec-disclosures.json) · DART (dart-disclosures.json) · 뉴스·IR (news-signals.json) · 지금은 고정 대상 기업만','ok','연결됨',null],
  ['class','분류','8-K 항목 → 분류 · 같은 사건 묶기 (NEW / REPEAT) · 중요도 표시 (보유 · 관심 · 기타 · 시장, 보유는 미연결)','ok','연결됨',null],
  ['5.1','5.1 관계망 (메뉴 4.1)','가운데 기업 하나 · 관계 자료원 결정 대기 (REL-SOURCE) · 관계 자료 미연결','na','미연결 · NOT_AVAILABLE','4-1'],
  ['5.2','5.2 공시 · 뉴스 목록 (메뉴 4.2)','최신순 · 범위 (전체 · 가운데 · 관심) · 채널 · 분류 · 신규·반복 조건','ok','연결됨','4-2'],
  ['5.2.2','5.2.2 ~ 5.2.4 요약 · 영향 · 주가 반영','5줄 요약 방식 결정 대기 (IA-14) · 반영 여부는 직접 알 수 없음 · 사건 전후 반응은 비공개 칸 (준비 중)','na','미산출 · NOT_AVAILABLE','4-2'],
  ['5.2.6','5.2.6 컨센서스 변화','무료 자료원 없음 · 컨센서스 자료 미연결','na','미연결','4-2'],
  ['mine','개인화','관심 기업 ★ (이 기기) · 로그인 저장은 결정 대기','ok','이 기기',null]];
 const jump=id=>{const s=doc.getElementById('s-'+id);if(!s)return;s.setAttribute('tabindex','-1');s.scrollIntoView({block:'start'});s.focus({preventScroll:true});};
 const treeNode=([id,name,text,st,words,to])=>h('div',{class:'node',role:'listitem',dataset:{treeNode:id,treeState:st}},
  h('div',null,h('b',null,name),' · ',text),h('div',{class:'links'},h('span',{class:st==='ok'?'chip':'dash'},words),to?h('button',{type:'button',class:'chip',dataset:{treeJump:to},'aria-label':name+' 화면 칸으로 이동',onclick:()=>jump(to)},'→ ',to.replace('-','.'),' 로'):null));
 const treeBlock=block('5.3',sub('뉴스 구조 트리','5.3','수집 → 분류 → 관계망 · 목록 → 요약 → 개인화'),
  h('div',{class:'node',dataset:{treeRoot:''}},h('div',null,h('b',null,'뉴스'),' · 점수를 바꾸지 않음 (score_effect NONE) · 정보 제공용')),
  h('div',{class:'branch',role:'list','aria-label':'뉴스 구조'},TREE.map(treeNode)),
  h('h4',null,'실제 예시 (공개 파일)'),factsBody,
  h('p',{class:'reason'},'예시는 공개 파일에서만 · 없으면 NA와 사유 · 지어내지 않음'));

 /* ---------------- layout */
 legend.prepend(h('p',{class:'hand'},'공시 · 뉴스는 제목 · 링크 · 시각 · 기업 · 분류만 · 점수에 반영하지 않음 · 요약 · 영향 · 관계망은 아직 미산출'));
 // A slot's blocks one under another with the shared gap (.lb: a flex column).
 const col=(...c)=>h('div',{class:'lb',dataset:{newsColumn:''}},...c);
 const searchRow=h('div',{class:'card-body',dataset:{newsSearch:''}},box.node);
 put(slots['4-1'],col(h('p',{class:'hand'},'기업 하나를 가운데 두고 연결을 봅니다 · 관계 자료는 아직 연결 전'),
  block('5.1.1',sub('기업 중심 관계','5.1.1','가운데 기업 · 연결은 관계 자료 연결 뒤'),searchRow,centerBody),
  h('div',{class:'grid-2'},
   block('5.1.2',sub('연결 근거','5.1.2'),prep('미산출 · 관계 자료 미연결',['기업 관계 자료원 결정 (REL-SOURCE)','확인 관계(공시) · 추론 관계 구분 규칙']),
    h('p',{class:'reason'},'확인된 관계(공시)와 추론 관계를 나눠 근거를 보일 자리 · 지금은 비워 둠')),
   block('5.1.3',sub('검색 전 추천','5.1.3'),prep('미산출 · 매크로 주목 기업 근거 없음',['매크로 근거 (IA-13 결정 대기)']),
    h('p',{class:'reason'},h('a',{class:'lk',href:href('search')},'기업 검색하기 →')))),
  block('5.1.4',sub('개인 설정','5.1.4','★ 관심 기업 · 이 기기'),mineBody)));
 const five=['무슨 일','Q 예상','G 예상','성격 · 단기/구조적 · 호재/악재','주가 반영'];
 put(slots['4-2'],col(h('p',{class:'hand'},'최신순 · 범위 · 관심 기업 · 공시와 뉴스를 한 목록으로'),
  block('5.2.1',sub('목록 · 개인화','5.2.1','공시·확정 + 뉴스·신호 · 최신 30행'),listBody),
  h('div',{class:'grid-2'},block('5.2.5',sub('신규 · 중복 · 변경','5.2.5'),occBody),block('5.2.7',sub('수집 상태','5.2.7'),statusBody)),
  h('p',{class:'reason'},'한 건마다 붙을 요약·영향 칸입니다 · 아직 계산하지 않아 모두 미산출 · 점수에 반영하지 않음'),
  h('div',{class:'grid-2'},
   block('5.2.2',sub('요약','5.2.2'),prep('5줄 요약 미산출 · 지금은 제목·링크·시각·분류만',['5줄 요약 방식 결정 (IA-14)','외부 모델 호출 승인']),
    h('ol',{class:'news-lines',dataset:{newsFive:'NOT_AVAILABLE'}},five.map(t=>h('li',null,h('b',null,t),' ',h('span',{class:'dash',dataset:{na:'NOT_COMPUTED'}},'미산출'))))),
   block('5.2.3',sub('영향 분석','5.2.3'),prep('Q·G 예상 · 단기/구조적 · 호재/악재 모두 미산출',['5줄 요약 방식 결정 (IA-14)']),h('p',{class:'reason'},'점수 영향 없음 (score_effect NONE)')),
   block('5.2.4',sub('주가 반영 여부','5.2.4','주가 반영 여부는 알 수 있나?'),prep('공개 자료에 가격이 없어 계산하지 않음',['사건 전후 반응 창 · 기준 결정 (IA-15)']),
    h('p',{class:'reason'},'직접 알 수는 없습니다 · 사건 전후 반응만 볼 수 있음 · 가격·가격에서 나온 값은 공개 화면에 싣지 않음 · 비공개 칸이 생기면 그 칸에서만')),
   block('5.2.6',sub('컨센서스 변화','5.2.6'),prep('컨센서스 자료 미연결',['무료 컨센서스 자료원']))),
  panel('news-event-reaction','사건 전후 반응 · 통합 거래량 배수 (KIS 일봉 · 분봉)')));
 put(slots['4-3'],col(treeBlock));

 /* ---------------- reads: the company list (5.1) and the public lists (5.2 · 5.3), independently */
 I.searchPart.attach(route,box,{onPick:(ev,e)=>{I.selection.set(e.id);win.location.hash=href('news',e.id);}});
 const companies=Promise.resolve().then(()=>I.companies.ready()).catch(()=>({state:'FAILED',size:0,missing:['Universe504 목록']}));
 companies.then(r=>{if(aborted())return;S.companies=r;
  const sel=I.selection.get(),key=S.given||(sel&&sel.id)||null;S.fromRoute=!!S.given;S.center=key?I.companies.get(key):null;
  if(S.center&&S.fromRoute)I.selection.set(S.center.id);
  paintCenter();paintMine();paintLists();});
 const read=()=>Promise.resolve().then(()=>I.data.ready()).then(()=>Promise.all(KEYS.map(k=>Promise.resolve(I.data.list(k)).catch(()=>null))))
  .then(vals=>({values:Object.fromEntries(KEYS.map((k,i)=>[k,vals[i]||null])),error:null}),()=>({values:null,error:'DATA_FAILED'}));
 Promise.all([companies,read()]).then(([,lists])=>{if(aborted())return;S.lists=lists;paintLists();
  if(!lists.error)I.data.subscribe(d=>{if(!d||d.reason!=='REFRESH'||aborted())return;read().then(l=>{if(!aborted()){S.lists=l;paintLists();}});},{signal});});
}
I.newsLive=Object.freeze({screen});
}
return Object.freeze({FILES,LIMIT,NEWS_CLASS,SEC_CLASS,DART_CLASS,CHANNEL,TIERS,FILTER_DEFAULT,COMPANY_LABEL,labelOf,dartRows,timeline,rowCategory,rowOccurrence,rowTier,filterRows,categories,categoryLabel,cleanFilters,
 counts,scopeIds,refreshStatus,refreshText,refreshBadge,isStale,secClassLabel,secItemsText,dartClassLabel,newsClassLabel,filingDedup,newsDedup,newsLatest,occurrenceLabel,treeFacts,install});
});
