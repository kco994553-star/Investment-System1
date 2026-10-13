/* Public `news-signals.json` reader ('뉴스·신호': GDELT DOC 2.0 + company IR feeds). Mirrors Python product/news_signals.
   One chronological list with '공시·확정' (SEC 8-K, DART when present): distinct badges, new/repeat markers, GDELT attribution,
   IR releases that repeat an 8-K Exhibit 99.1 collapsed under that 8-K. Title, link, time, company and classification only;
   nothing changes any score. DOM is built with textContent only. */
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
const CHANNELS={DISCLOSURE:['공시·확정','Disclosure · confirmed'],NEWS:['뉴스·신호','News · signal']};
const TOP=['schema_version','kind','as_of','state','reason_codes','freshness_basis','stale_after_seconds','window_days','channel','score_effect','attribution','matching_rule','sources','items'];
const ITEM=['company_id','source','title','link','published_at','classification','group_id','occurrence','relation','related_8k_accession'];
const LABEL='[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?',LINK=new RegExp('^(https?)://('+LABEL+'(?:\\.'+LABEL+')+)(?::[0-9]{1,5})?(?:[/?][A-Za-z0-9!$%&\'()*+,./:;=?@\\[\\]_~-]*)?$');
const TITLE_BAD=/[\u0000-\u001f\u007f-\u009f<>\u00a0\u1680\u180e\u2000-\u200b\u2028\u2029\u202f\u205f\u3000\ufeff]/u;
function need(v){if(!v)throw Error('NEWS_SIGNALS_INVALID');}
const plain=v=>v!==null&&typeof v==='object'&&!Array.isArray(v),keys=(v,k)=>plain(v)&&Object.keys(v).length===k.length&&k.every(n=>Object.hasOwn(v,n));
function instant(v){need(typeof v==='string'&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00$/.test(v));const t=Date.parse(v);need(Number.isFinite(t)&&new Date(t).toISOString().slice(0,19)===v.slice(0,19));return t;}
const fresh=(at,cut)=>cut-at>STALE_AFTER*1000?'STALE':'LIVE';
function same(a,b){if(plain(a)&&plain(b)){const k=Object.keys(a);return k.length===Object.keys(b).length&&k.every(n=>Object.hasOwn(b,n)&&same(a[n],b[n]));}return a===b;}
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
  need(keys(p,TOP)&&p.schema_version===1&&p.kind===KIND&&p.freshness_basis==='SOURCE_ACQUISITION'&&p.channel==='NEWS'&&p.score_effect==='NONE'&&p.stale_after_seconds===STALE_AFTER&&p.window_days===WINDOW_DAYS&&p.matching_rule===MATCHING_RULE&&same(p.attribution,ATTRIBUTION));
  const cut=instant(p.as_of),acquired={},states=[];need(keys(p.sources,SOURCES));
  for(const source of SOURCES){const ids=source==='GDELT'?GDELT_COMPANIES:IR_COMPANIES,entries=p.sources[source];need(plain(entries)&&Object.keys(entries).length===ids.length&&ids.every(id=>Object.hasOwn(entries,id)));
   for(const id of ids){const c=entries[id];need(keys(c,source==='IR'?['state','acquired_at','reason_code','feed_status']:['state','acquired_at','reason_code']));const listed=Object.hasOwn(IR_DOMAINS,id);
    if(source==='IR'){need((listed?['VERIFIED','UNVERIFIED_URL']:['NOT_AVAILABLE']).includes(c.feed_status));if(!listed)need(c.acquired_at===null&&c.reason_code==='NO_OFFICIAL_FEED_KNOWN');}
    if(c.acquired_at===null)need(c.state==='NOT_AVAILABLE'&&(c.reason_code==='NOT_COLLECTED'||source==='IR'&&!listed&&c.reason_code==='NO_OFFICIAL_FEED_KNOWN'));
    else{const at=instant(c.acquired_at);need(at<=cut&&c.reason_code===null&&c.state===fresh(at,cut));acquired[source+'|'+id]=at;}states.push(c.state);}}
  const state=states.includes('LIVE')?'LIVE':states.includes('STALE')?'STALE':'NOT_AVAILABLE';need(p.state===state&&Array.isArray(p.reason_codes)&&JSON.stringify(p.reason_codes)===JSON.stringify(state==='LIVE'?[]:state==='STALE'?['STALE_INPUT']:['NO_ELIGIBLE_INPUT']));
  const items=p.items;need(Array.isArray(items)&&items.length<=MAX_ITEMS);const cutoff=cut-WINDOW_DAYS*86400000,links=new Set(),titles=new Set(),per=new Map();
  for(const i of items){need(keys(i,ITEM)&&SOURCES.includes(i.source)&&typeof i.company_id==='string'&&Object.hasOwn(acquired,i.source+'|'+i.company_id));
   need(validTitle(i.title)&&linkHost(i.link)!==null);need(i.source==='GDELT'?relevant(i.company_id,i.title):irLinkAllowed(i.company_id,i.link));
   const at=instant(i.published_at);need(cutoff<=at&&at<=acquired[i.source+'|'+i.company_id]);
   need(CLASSIFICATIONS.includes(i.classification)&&i.classification===classify(i.title)&&['NEW','REPEAT'].includes(i.occurrence)&&['NONE','RELATED_TO_8K'].includes(i.relation));
   if(i.relation==='RELATED_TO_8K')need(i.source==='IR'&&typeof i.related_8k_accession==='string'&&/^\d{10}-\d{2}-\d{6}$/.test(i.related_8k_accession)&&typeof i.group_id==='string'&&i.group_id.startsWith(i.company_id+':')&&/^\d{10}-\d{2}-\d{6}$/.test(i.group_id.slice(i.company_id.length+1)));
   else need(i.related_8k_accession===null);
   const key=i.company_id+' '+tokens(i.title).join(' ');need(!links.has(i.link)&&!titles.has(key));links.add(i.link);titles.add(key);const k=i.source+'|'+i.company_id;per.set(k,(per.get(k)||0)+1);need(per.get(k)<=PER_COMPANY_MAX[i.source]);}
  for(let n=1;n<items.length;n++)need(asc(items[n-1],items[n])>0);
  const expected=groups(items);need(items.every((e,n)=>e.group_id===expected[n].group_id&&e.occurrence===expected[n].occurrence));return p;
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
function mount(host,{sec=null,dart=null,news=null}={},{locale,companyIds=null,limit=30,emptyText,secApi=root.SecDisclosures,dartApi=root.DartDisclosures}={}){
 if(!host)return;const doc=host.ownerDocument,en=locale==='en-US',T=(k,e)=>en?e:k,el=(tag,text,attrs={})=>{const n=doc.createElement(tag);if(text!==undefined)n.textContent=text;for(const[k,v]of Object.entries(attrs))n.setAttribute(k,v);return n;};
 const when=v=>v.slice(0,16).replace('T',' ')+' UTC',srcLabel=s=>s==='IR'?T('회사 IR','Company IR'):'GDELT',classLabel=c=>{const [k,e]=CLASSES[c];return en?e+' ('+k+')':k+' ('+e+')';};
 const section=el('section',undefined,{class:'card','data-sec-disclosures':'','data-news-signals':''});section.append(el('h2',T('공시·확정 + 뉴스·신호 · 시간순','Disclosures (confirmed) + news (signals) · chronological')));
 const secState=sec?sec.state:'NOT_AVAILABLE',newsState=news?news.state:'NOT_AVAILABLE',chips=el('p',undefined,{class:'chips'});
 chips.append(el('span',CHANNELS.DISCLOSURE[en?1:0]+' · SEC 8-K',{class:'badge'}),el('span',secState,{class:'badge '+secState,'data-disclosure-state':secState}));
 if(dart)chips.append(el('span','DART',{class:'badge'}),el('span',dart.state,{class:'badge disclosure-state','data-dart-state':dart.state}));
 chips.append(el('span',CHANNELS.NEWS[en?1:0]+' · GDELT · IR',{class:'badge news-signal'}),el('span',newsState,{class:'badge news-state','data-news-state':newsState}));section.append(chips);
 for(const[p,label,window]of [[sec,'SEC 8-K',90],[news,T('뉴스·신호','News'),WINDOW_DAYS]])if(p){section.append(el('p',label+' · '+T('기준: ','as of: ')+p.as_of+' · '+T('최근 '+window+'일','last '+window+' days'),{class:'meta'}));
  if(p.state!=='NOT_AVAILABLE'&&Date.now()-Date.parse(p.as_of)>p.stale_after_seconds*1000)section.append(el('p','STALE · '+label+' · '+T('수집 갱신 시각 경과','Acquisition refresh overdue'),{class:'warning','data-disclosure-stale':''}));}
 if(!sec)section.append(el('p',T('공개 공시 자료가 연결되지 않았습니다.','Public disclosure data is not connected.'),{class:'small','data-disclosure-missing':''}));
 if(news){const a=el('p',undefined,{class:'small','data-news-attribution':''});a.append(doc.createTextNode(T('뉴스·신호 출처: ','News signals source: ')),el('a',ATTRIBUTION.GDELT.name,{href:ATTRIBUTION.GDELT.url,target:'_blank',rel:'noopener noreferrer','data-gdelt-attribution':''}),doc.createTextNode(' (GDELT DOC 2.0 API) · '+T('회사 IR 보도자료 피드 · 제목·링크만 표시, 기사는 각 언론사 소유','company IR press-release feeds · titles and links only; articles belong to their publishers')));section.append(a);}
 else section.append(el('p',T('뉴스·신호 자료가 연결되지 않았습니다.','News signal data is not connected.'),{class:'small','data-news-missing':''}));
 section.append(el('p',T('점수에 반영하지 않음 · 제목·링크·시각·기업·분류만 표시','Never changes scores · title, link, time, company and classification only'),{class:'small','data-score-effect':'NONE'}));
 const rows=timeline({sec,dart,news},{companyIds,dartApi}).slice(0,limit);
 if(!rows.length){section.append(el('p',emptyText||T('표시할 공시·뉴스가 없습니다.','No disclosures or news to show.'),{class:'empty'}));host.replaceChildren(section);return;}
 const line=i=>{const li=el('li',undefined,{'data-news-item':'','data-news-source':i.source,'data-news-occurrence':i.occurrence,'data-relation':i.relation});li.append(el('a',i.title,{href:i.link,target:'_blank',rel:'noopener noreferrer','data-news-link':''}),doc.createTextNode(' · '+srcLabel(i.source)+' · '+when(i.published_at)+' · '+linkHost(i.link)[1]));return li;};
 const list=el('ol',undefined,{class:'list','data-disclosure-list':'','data-timeline':''});
 for(const row of rows){
  if(row.channel==='DISCLOSURE'&&row.source==='SEC'&&secApi){const li=secApi.renderRow(doc,row.event,en);
   if(row.related.length){const d=el('details',undefined,{'data-related-ir':String(row.related.length)}),ul=el('ul',undefined,{class:'list'});d.append(el('summary',T('관련 IR 보도자료 '+row.related.length+'건 · 8-K와 같은 발표(반복)','Related IR release ×'+row.related.length+' · same announcement as this 8-K (repeat)')));for(const i of row.related)ul.append(line(i));d.append(ul);li.append(d);}
   list.append(li);continue;}
  if(row.channel==='DISCLOSURE'&&row.source==='DART'){const e=row.event,li=el('li',undefined,{class:'card','data-disclosure':e.rcept_no,'data-source':'DART','data-occurrence':e.occurrence,'data-classification':e.classification}),head=el('p',undefined,{class:'chips'});
   head.append(el('span',CHANNELS.DISCLOSURE[en?1:0],{class:'badge LIVE','data-channel':'DISCLOSURE'}),el('span',e.occurrence==='NEW'?T('새 공시','New'):T('정정·반복','Repeat / amendment'),{class:'badge','data-occurrence-label':e.occurrence}),el('span',dartApi&&dartApi.classLabel?dartApi.classLabel(e.classification,en):e.classification,{class:'badge','data-classification-label':e.classification}));
   const who=el('p');who.append(el('a',COMPANY_LABEL[e.company_id]||e.company_id.toUpperCase(),{href:'#company/'+encodeURIComponent(e.company_id)}),doc.createTextNode(' · DART · '+e.filing_date+' KST'));const t=el('p');t.append(el('a',e.title,{href:e.link,target:'_blank',rel:'noopener noreferrer','data-filing-link':''}),doc.createTextNode(' ↗'));li.append(head,who,t);list.append(li);continue;}
  if(row.channel!=='NEWS')continue;
  const i=row.item,li=el('li',undefined,{class:'card','data-news':i.group_id,'data-news-source':i.source,'data-news-occurrence':i.occurrence,'data-news-classification':i.classification}),head=el('p',undefined,{class:'chips'});
  head.append(el('span',CHANNELS.NEWS[en?1:0],{class:'badge news-signal','data-channel':'NEWS'}),el('span',row.orphan?T('8-K 관련 · 반복','Related to 8-K · repeat'):i.occurrence==='NEW'?T('새 소식','New'):T('반복 보도','Repeat'),{class:'badge','data-news-occurrence-label':row.orphan?'RELATED_TO_8K':i.occurrence}),el('span',classLabel(i.classification),{class:'badge','data-news-classification-label':i.classification}));
  const who=el('p');who.append(el('a',COMPANY_LABEL[i.company_id]||i.company_id.toUpperCase(),{href:'#company/'+encodeURIComponent(i.company_id)}),doc.createTextNode(' · '+srcLabel(i.source)+' · '+when(i.published_at)+' · '+linkHost(i.link)[1]));
  const t=el('p');t.append(el('a',i.title,{href:i.link,target:'_blank',rel:'noopener noreferrer','data-news-link':''}),doc.createTextNode(' ↗'));li.append(head,who,t);
  if(row.repeats.length){const d=el('details',undefined,{'data-news-repeats':String(row.repeats.length)}),ul=el('ul',undefined,{class:'list'});d.append(el('summary',T('같은 사건 반복 보도 '+row.repeats.length+'건','Repeat reports of this event: '+row.repeats.length)));for(const r of row.repeats)ul.append(line(r));d.append(ul);li.append(d);}
  list.append(li);}
 section.append(list);host.replaceChildren(section);
}
return Object.freeze({FILENAME,KIND,MATCH,IR_DOMAINS,CLASS_RULES,STOPWORDS,ATTRIBUTION,CLASSES,CHANNELS,GDELT_COMPANIES,IR_COMPANIES,tokens,significant,classify,relevant,similar,validTitle,linkHost,irLinkAllowed,groups,validate,load,timeline,mount});
});
