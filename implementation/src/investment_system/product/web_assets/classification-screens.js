/* SIC industry group v0 and strategy theme v0 (2026-10-11 user decision, V0_UNCALIBRATED_DEFAULT).
   Reads the public, price-free company-classification.json (ids, names, memberships, evidence kind, as-of, hashes).
   S04 industry/theme chips; S03 industry composition and the single-theme concentration warning (> 40%), computed
   on this device from RAM ACTUAL weights only and never stored. Missing evidence is NOT_AVAILABLE, never 0.
   Python reference: investment_system.qgv.theme_membership.theme_concentration (shared vectors). */
(function(root,factory){const api=factory(root);if(typeof module==='object'&&module.exports)module.exports=api;else root.ClassificationScreens=api;})(typeof globalThis==='object'?globalThis:this,function(g){
'use strict';
const FILE='company-classification.json',KIND='COMPANY_CLASSIFICATION',THRESHOLD=0.4,MAX=2*1024*1024;
const IDS=['asml','lrcx','klac','tokyo_electron','hanmi','nvda','amd','avgo','qcom','intc','msft','googl','amzn','rtx','stry','etn','hubb','gev','rok'];
const STATES=['LIVE','STALE','NOT_AVAILABLE'],AGENCIES=['SEC_SUBMISSIONS','SEC_10K','SEC_NPORT','SEC_MF_TICKERS'];
const REASONS=['NO_ELIGIBLE_INPUT','SOURCE_NOT_AVAILABLE','STALE_INPUT','PARTIAL_INPUT','CYCLICAL_DEFENSIVE_RULE_UNDECIDED'];
const INDUSTRY_REASONS=['SIC_NOT_AVAILABLE','SIC_UNMATCHED','SOURCE_NOT_AVAILABLE','NOT_SEC_REGISTRANT'];
const KEYWORD_STATES=['AVAILABLE','TEN_K_NOT_FILED','NOT_AVAILABLE'],KEYWORD_REASONS=['TEN_K_NOT_FILED','ITEM1_NOT_FOUND','SOURCE_NOT_AVAILABLE','NOT_SEC_REGISTRANT'];
const ETF_REASONS=['SOURCE_NOT_AVAILABLE','ETF_SERIES_BINDING_NOT_AVAILABLE','ETF_SERIES_UNBOUND','NPORT_FILING_LIST_NOT_AVAILABLE','NPORT_NOT_FOUND','NPORT_INVALID','NPORT_SERIES_MISMATCH'];
const CANDIDATES=['CYCLICAL_CANDIDATE','DEFENSIVE_CANDIDATE'],EVIDENCE=['ETF','KEYWORD'];
const ID=/^[a-z][a-z0-9_]{0,63}$/,TICKER=/^[A-Z][A-Z0-9.]{0,15}$/,HASH=/^[0-9a-f]{64}$/;
function need(v){if(!v)throw Error('PUBLIC_CLASSIFICATION_INVALID');}
const object=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
function keys(v,ks){need(object(v)&&Object.keys(v).length===ks.length&&ks.every(k=>Object.hasOwn(v,k)));}
function clock(v){need(typeof v==='string'&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$/.test(v));const n=Date.parse(v);need(Number.isFinite(n));return n;}
function day(v){need(v===null||typeof v==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&new Date(v+'T00:00:00Z').toISOString().slice(0,10)===v);}
function name(v){need(typeof v==='string'&&v.trim().length>0&&v.length<=80);}
const aggregate=s=>s.includes('LIVE')?'LIVE':s.includes('STALE')?'STALE':'NOT_AVAILABLE';
const ordered=(list,order)=>JSON.stringify(list)===JSON.stringify(order.filter(x=>list.includes(x)))&&new Set(list).size===list.length;
function validate(p){
 need(new TextEncoder().encode(JSON.stringify(p)).length<=MAX);
 keys(p,['schema_version','kind','as_of','state','freshness_basis','stale_after_seconds','reason_codes','sources','data']);
 need(p.schema_version===1&&p.kind===KIND&&STATES.includes(p.state)&&p.freshness_basis==='SOURCE_ACQUISITION'&&typeof p.stale_after_seconds==='number'&&Number.isFinite(p.stale_after_seconds)&&p.stale_after_seconds>0);
 const cut=clock(p.as_of),fresh=at=>cut-at>p.stale_after_seconds*1000?'STALE':'LIVE';
 need(Array.isArray(p.reason_codes)&&p.reason_codes.every(r=>REASONS.includes(r))&&new Set(p.reason_codes).size===p.reason_codes.length&&Array.isArray(p.sources)&&p.sources.length<=1000);
 const sources=new Map();
 for(const s of p.sources){keys(s,['agency','sha256','acquired_at']);need(AGENCIES.includes(s.agency)&&typeof s.sha256==='string'&&HASH.test(s.sha256));const at=clock(s.acquired_at),k=s.agency+':'+s.sha256;need(at<=cut&&!sources.has(k));sources.set(k,at);}
 const d=p.data;keys(d,['calibration','industry_config','theme_config','etfs','companies']);need(d.calibration==='V0_UNCALIBRATED_DEFAULT');
 const ic=d.industry_config;keys(ic,['config_version','decided_at','groups','subgroups']);need(ic.config_version==='sic_industry_groups/v0'&&ic.decided_at==='2026-10-11'&&Array.isArray(ic.groups)&&ic.groups.length>0&&ic.groups.length<=64&&Array.isArray(ic.subgroups)&&ic.subgroups.length<=128);
 const groups=new Set(),subgroups=new Map();
 for(const x of ic.groups){keys(x,['id','name','name_en']);need(typeof x.id==='string'&&ID.test(x.id)&&!groups.has(x.id));name(x.name);name(x.name_en);groups.add(x.id);}
 for(const x of ic.subgroups){keys(x,['id','group','name','name_en']);need(typeof x.id==='string'&&ID.test(x.id)&&!subgroups.has(x.id)&&groups.has(x.group));name(x.name);name(x.name_en);subgroups.set(x.id,x.group);}
 const tc=d.theme_config;keys(tc,['config_version','decided_at','membership_rule','themes']);need(tc.config_version==='theme_config/v0'&&tc.decided_at==='2026-10-11'&&tc.membership_rule==='ETF_HELD_OR_10K_ITEM1_KEYWORD'&&Array.isArray(tc.themes)&&tc.themes.length>0&&tc.themes.length<=128);
 const themes=new Map(),tickers=[];
 for(const t of tc.themes){keys(t,['id','name','name_en','etfs','evidence_strength']);need(typeof t.id==='string'&&ID.test(t.id)&&!themes.has(t.id));name(t.name);name(t.name_en);need(['STANDARD','WEAK'].includes(t.evidence_strength)&&Array.isArray(t.etfs)&&t.etfs.length>0&&t.etfs.length<=16&&t.etfs.every(x=>typeof x==='string'&&TICKER.test(x))&&new Set(t.etfs).size===t.etfs.length);themes.set(t.id,t.etfs);for(const x of t.etfs)if(!tickers.includes(x))tickers.push(x);}
 const states=[];keys(d.etfs,tickers);
 for(const e of Object.values(d.etfs)){keys(e,['state','report_date','reason_code','source_sha256']);need(STATES.includes(e.state));day(e.report_date);
  if(e.state==='NOT_AVAILABLE')need(e.report_date===null&&e.source_sha256===null&&ETF_REASONS.includes(e.reason_code));
  else need(e.reason_code===null&&e.report_date!==null&&e.report_date<=new Date(cut).toISOString().slice(0,10)&&sources.has('SEC_NPORT:'+e.source_sha256)&&e.state===fresh(sources.get('SEC_NPORT:'+e.source_sha256)));
  states.push(e.state);}
 keys(d.companies,IDS);
 for(const row of Object.values(d.companies)){keys(row,['industry','themes']);const ind=row.industry;
  keys(ind,['state','sic','group','subgroup','cyclical_defensive_candidate','reason_code','source_hashes']);
  need(STATES.includes(ind.state)&&(ind.sic===null||typeof ind.sic==='string'&&/^\d{4}$/.test(ind.sic)&&ind.sic!=='0000')&&(ind.cyclical_defensive_candidate===null||CANDIDATES.includes(ind.cyclical_defensive_candidate))&&object(ind.source_hashes)&&Object.keys(ind.source_hashes).every(k=>k==='submissions'));
  for(const v of Object.values(ind.source_hashes))need(sources.has('SEC_SUBMISSIONS:'+v));
  if(ind.state==='NOT_AVAILABLE')need(ind.group===null&&ind.subgroup===null&&ind.cyclical_defensive_candidate===null&&INDUSTRY_REASONS.includes(ind.reason_code)&&(ind.reason_code!=='SIC_UNMATCHED'||ind.sic!==null));
  else need(groups.has(ind.group)&&ind.reason_code===null&&ind.sic!==null&&Object.hasOwn(ind.source_hashes,'submissions')&&(ind.subgroup===null||subgroups.get(ind.subgroup)===ind.group)&&ind.state===fresh(sources.get('SEC_SUBMISSIONS:'+ind.source_hashes.submissions)));
  const th=row.themes;keys(th,['state','keyword_evidence','etf_join','memberships','source_hashes']);need(STATES.includes(th.state)&&['EXACT_IDENTIFIER','NOT_AVAILABLE'].includes(th.etf_join));
  const kw=th.keyword_evidence;keys(kw,['state','reason_code','report_date']);need(KEYWORD_STATES.includes(kw.state));day(kw.report_date);
  need((kw.state==='AVAILABLE')===(kw.reason_code===null)&&(kw.reason_code===null||KEYWORD_REASONS.includes(kw.reason_code))&&(kw.state!=='TEN_K_NOT_FILED'||kw.reason_code==='TEN_K_NOT_FILED')&&(kw.state==='AVAILABLE'||kw.report_date===null));
  need(object(th.source_hashes)&&Object.keys(th.source_hashes).every(k=>k==='ten_k'||k==='submissions')&&Object.hasOwn(th.source_hashes,'ten_k')===(kw.state==='AVAILABLE')&&Object.hasOwn(th.source_hashes,'submissions')===(kw.state==='TEN_K_NOT_FILED'));
  for(const[k,v]of Object.entries(th.source_hashes))need(sources.has((k==='ten_k'?'SEC_10K:':'SEC_SUBMISSIONS:')+v));
  keys(th.memberships,[...themes.keys()]);
  for(const[tid,m]of Object.entries(th.memberships)){keys(m,['member','evidence','etfs']);need([true,false,null].includes(m.member)&&Array.isArray(m.evidence)&&Array.isArray(m.etfs)&&ordered(m.evidence,EVIDENCE)&&ordered(m.etfs,themes.get(tid)));
   need(m.etfs.every(x=>d.etfs[x].state!=='NOT_AVAILABLE')&&m.evidence.includes('ETF')===(m.etfs.length>0)&&(m.etfs.length===0||th.etf_join==='EXACT_IDENTIFIER')&&(!m.evidence.includes('KEYWORD')||kw.state==='AVAILABLE')&&(m.member===true)===(m.evidence.length>0));
   if(m.member===false)need(th.etf_join==='EXACT_IDENTIFIER'&&['AVAILABLE','TEN_K_NOT_FILED'].includes(kw.state)&&themes.get(tid).every(x=>d.etfs[x].state!=='NOT_AVAILABLE'));}
  need((th.state==='NOT_AVAILABLE')===Object.values(th.memberships).every(m=>m.member===null));
  states.push(ind.state,th.state);}
 need(p.state===aggregate(states));return p;
}
async function load(view){const control=new AbortController(),timer=setTimeout(()=>control.abort(),20000);
 try{const r=await view.fetch(FILE,{cache:'no-store',credentials:'omit',referrerPolicy:'no-referrer',redirect:'error',signal:control.signal});if(!r.ok)return null;const text=await r.text();need(new TextEncoder().encode(text).length<=MAX);return validate(JSON.parse(text));}
 catch(_){return null;}finally{clearTimeout(timer);}}
// ---------- device-side maths (RAM only; mirrors theme_membership.py) ----------
const positive=w=>typeof w==='number'&&Number.isFinite(w)&&w>0;
function concentrationStatus(exposure,unknown,threshold=THRESHOLD){return exposure>threshold?'WARN':exposure+unknown>threshold?'INDETERMINATE':'OK';}
function themeConcentration({rows,memberships,themeIds,threshold=THRESHOLD}){
 need(typeof threshold==='number'&&threshold>0&&threshold<1);const usable=rows.filter(r=>positive(r.weight));
 const themes=themeIds.map(id=>{let exposure=0,unknown=0;for(const r of usable){const rec=typeof r.company_id==='string'&&object(memberships)&&Object.hasOwn(memberships,r.company_id)?memberships[r.company_id]:null,m=object(rec)&&Object.hasOwn(rec,id)?rec[id]:null;if(m===true)exposure+=r.weight;else if(m!==false)unknown+=r.weight;}return{id,exposure,unknown,status:concentrationStatus(exposure,unknown,threshold)};});
 const order=new Map(themeIds.map((id,i)=>[id,i]));
 return{threshold,themes,warnings:themes.filter(t=>t.status==='WARN').sort((a,b)=>b.exposure-a.exposure||order.get(a.id)-order.get(b.id)).map(t=>t.id)};
}
function membershipMap(p){const out={};if(!p)return out;for(const[id,row]of Object.entries(p.data.companies)){out[id]={};for(const[t,m]of Object.entries(row.themes.memberships))out[id][t]=m.member;}return out;}
function industryComposition({rows,payload,idByTicker}){
 const groups=new Map(),usable=rows.filter(r=>positive(r.weight));let unknown=0;
 for(const r of usable){const rec=payload?record(payload,idByTicker.get(r.ticker)):null,ind=rec&&rec.industry.state!=='NOT_AVAILABLE'?rec.industry:null;if(!ind){unknown+=r.weight;continue;}groups.set(ind.group,(groups.get(ind.group)||0)+r.weight);}
 const order=payload?payload.data.industry_config.groups.map(x=>x.id):[];
 return{groups:[...groups.entries()].sort((a,b)=>b[1]-a[1]||order.indexOf(a[0])-order.indexOf(b[0])),unknown};
}
// ---------- presentation ----------
const esc=v=>String(v??'—').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const tr=locale=>(ko,en)=>locale==='en-US'?en:ko;
const na=(reason,locale)=>'<span class="badge NOT_AVAILABLE">NOT_AVAILABLE</span>'+(reason?' <span class="small">'+esc(reason)+'</span>':'');
const pct=(v,locale)=>typeof v==='number'&&Number.isFinite(v)?new Intl.NumberFormat(locale==='en-US'?'en-US':'ko-KR',{minimumFractionDigits:1,maximumFractionDigits:1}).format(v*100)+'%':'—';
function record(p,id){return p&&typeof id==='string'&&Object.hasOwn(p.data.companies,id)?p.data.companies[id]:null;}
function marker(locale){return '<span class="badge partial" data-v0-marker>'+esc(tr(locale)('v0 기본값 · UNCALIBRATED · 나중에 수정 가능','v0 default · UNCALIBRATED · editable later'))+'</span>';}
const label=(item,locale)=>item?(locale==='en-US'?item.name_en:item.name):'—';
function industryReason(code,sic,locale){const T=tr(locale);return code==='SIC_UNMATCHED'?T('SIC '+sic+' · v0 업종군 표에 없음','SIC '+sic+' · not in the v0 group table'):code==='SIC_NOT_AVAILABLE'?T('SEC 공시에 SIC 없음(또는 0000)','No SIC in SEC filings (or 0000)'):code==='NOT_SEC_REGISTRANT'?T('SEC 등록 기업 아님 · DART/EDINET 미연결','Not an SEC registrant · DART/EDINET not connected'):T('SEC 수집 결과가 아직 없습니다','No SEC collection result yet');}
function industryChip(p,id,locale){
 const T=tr(locale);if(!p)return na(T('공개 분류 자료가 연결되지 않았습니다.','Public classification data is not connected.'),locale);
 const rec=record(p,id);if(!rec)return na(T('분류 대상 기업이 아닙니다.','Not in the classification scope.'),locale);
 const ind=rec.industry;if(ind.state==='NOT_AVAILABLE')return na(industryReason(ind.reason_code,ind.sic,locale),locale)+' '+marker(locale);
 const cfg=p.data.industry_config,group=cfg.groups.find(x=>x.id===ind.group),sub=cfg.subgroups.find(x=>x.id===ind.subgroup);
 const cand=ind.cyclical_defensive_candidate?' <span class="small" data-cyclical-candidate="'+esc(ind.cyclical_defensive_candidate)+'">'+esc(ind.cyclical_defensive_candidate==='CYCLICAL_CANDIDATE'?T('경기민감 후보','Cyclical candidate'):T('경기방어 후보','Defensive candidate'))+' · '+esc(T('소속도','membership'))+' NOT_AVAILABLE</span>':'';
 return '<span class="badge '+esc(ind.state)+'" data-industry-chip="'+esc(ind.group)+'">'+esc(label(group,locale))+(sub?' · '+esc(label(sub,locale)):'')+'</span> <span class="small" data-sic>SIC '+esc(ind.sic)+'</span>'+cand+' '+marker(locale);
}
function themeChip(p,id,locale){
 const T=tr(locale);if(!p)return na(T('공개 분류 자료가 연결되지 않았습니다.','Public classification data is not connected.'),locale);
 const rec=record(p,id);if(!rec)return na(T('분류 대상 기업이 아닙니다.','Not in the classification scope.'),locale);
 const ms=rec.themes.memberships,themes=p.data.theme_config.themes,hits=themes.filter(t=>ms[t.id].member===true),unknown=themes.filter(t=>ms[t.id].member===null).length;
 const ev=m=>m.evidence.map(k=>k==='ETF'?'ETF '+m.etfs.join('·'):T('10-K 키워드','10-K keyword')).join(' + ');
 const chips=hits.map(t=>'<span class="badge '+esc(rec.themes.state)+'" data-theme-chip="'+esc(t.id)+'">'+esc(label(t,locale))+' <small data-theme-evidence>'+esc(ev(ms[t.id]))+'</small></span>'+(t.evidence_strength==='WEAK'?' <span class="badge partial" data-weak-evidence="'+esc(t.id)+'">'+esc(T('근거 약함','Weak evidence'))+'</span>':'')).join(' ');
 let rest='';
 if(unknown===themes.length)rest=na(T('ETF 보유·10-K 키워드 근거가 아직 없습니다','No ETF-holding or 10-K keyword evidence yet'),locale);
 else if(unknown)rest='<span class="small" data-theme-unknown>'+esc(T('테마 '+unknown+'개 자료 없음','No data for '+unknown+' theme(s)'))+'</span>';
 else if(!hits.length)rest='<span class="small" data-theme-none>'+esc(T('해당 테마 없음(근거 모두 확인)','No theme (all evidence checked)'))+'</span>';
 return [chips,rest].filter(Boolean).join(' ')+' '+marker(locale);
}
function why(ram,locale){const T=tr(locale);return !ram?T('기기 보유를 읽는 중입니다.','Reading device holdings.'):ram.reason==='NO_ACTUAL'?T('기기에 ACTUAL 보유가 없습니다.','No ACTUAL holdings on this device.'):ram.reason==='READ_FAILED'?T('기기 보유 데이터를 열 수 없습니다.','Device holdings could not be opened.'):T('시세·환율이 모두 입력되어야 ACTUAL 비중을 계산합니다.','ACTUAL weights need every quote and FX rate entered.');}
function industryCard({locale,ram,payload,idByTicker}){
 const T=tr(locale),head='<section class="card" data-portfolio-card="industry"><h2>'+esc(T('산업 구성','Industry composition'))+'</h2><p class="small">'+esc(T('SEC SIC 업종군 v0 · ACTUAL 비중 · 전략 테마로 대신 채우지 않음','SEC SIC industry group v0 · ACTUAL share · strategy themes never fill this in'))+' '+marker(locale)+'</p>';
 if(!ram||ram.state!=='AVAILABLE')return head+'<p>'+na(why(ram,locale),locale)+'</p></section>';
 if(!payload)return head+'<p>'+na(T('공개 분류 자료가 연결되지 않았습니다.','Public classification data is not connected.'),locale)+'</p></section>';
 const c=industryComposition({rows:ram.rows,payload,idByTicker:idByTicker||new Map()}),groups=payload.data.industry_config.groups;
 const row=(id,text,v)=>'<li data-industry="'+esc(id)+'"><span>'+esc(text)+'</span><span class="num">'+esc(pct(v,locale))+'</span></li>';
 if(!c.groups.length)return head+'<p>'+na(c.unknown?T('보유 기업의 SEC SIC 업종 근거가 아직 없습니다.','No SEC SIC industry evidence for the held companies yet.'):T('양수 보유가 없습니다.','No positive holdings.'),locale)+'</p></section>';
 return head+'<ul class="combo-list">'+c.groups.map(([id,v])=>row(id,label(groups.find(x=>x.id===id),locale),v)).join('')+(c.unknown>0?row('nodata',T('자료 없음','No data'),c.unknown):'')+'</ul></section>';
}
function concentrationBlock({locale,ram,payload,catalog,idByTicker}){
 const T=tr(locale),rule=T('기준: 단일 테마가 포트폴리오의 40% 초과','Rule: a single theme above 40% of the portfolio');
 const chip=(attr,id,text,v,status)=>'<span class="badge '+(status==='WARN'?'partial':'NOT_AVAILABLE')+'" data-concentration-'+attr+'="'+esc(id)+'">'+esc((status==='WARN'?T('쏠림 경고 · ','Concentration warning · '):T('확인 불가 · ','Cannot rule out · '))+text+' '+pct(v,locale)+(status==='WARN'?' > 40% · '+T('v0 기본값','v0 default'):''))+'</span>';
 const render=(title,attr,result,names)=>{
  const warn=result.themes.filter(t=>t.status==='WARN').sort((a,b)=>result.warnings.indexOf(a.id)-result.warnings.indexOf(b.id)),open=result.themes.filter(t=>t.status==='INDETERMINATE');
  const body=warn.map(t=>chip('warning',t.id,names(t.id),t.exposure,'WARN')).concat(open.map(t=>chip('indeterminate',t.id,names(t.id),t.exposure,'INDETERMINATE'))).join(' ');
  return '<li data-concentration-scope="'+attr+'"><b>'+esc(title)+'</b> '+(body||'<span class="badge LIVE" data-concentration-ok>'+esc(T('40% 초과 테마 없음','No theme above 40%'))+'</span>')+'</li>';};
 const strategyTitle=T('전략 테마 v0 (ETF 보유·10-K 키워드)','Strategy themes v0 (ETF holdings · 10-K keywords)'),targetTitle=T('내 TARGET 테마의 ACTUAL','ACTUAL of my TARGET themes');
 let strategy,target;
 if(!ram||ram.state!=='AVAILABLE'){strategy='<li data-concentration-scope="strategy"><b>'+esc(strategyTitle)+'</b> '+na(why(ram,locale),locale)+'</li>';target='<li data-concentration-scope="target"><b>'+esc(targetTitle)+'</b> '+na(why(ram,locale),locale)+'</li>';}
 else{
  if(!payload)strategy='<li data-concentration-scope="strategy"><b>'+esc(strategyTitle)+'</b> '+na(T('공개 분류 자료가 연결되지 않았습니다.','Public classification data is not connected.'),locale)+'</li>';
  else{const themes=payload.data.theme_config.themes,map=idByTicker||new Map();
   const result=themeConcentration({rows:ram.rows.map(r=>({company_id:map.get(r.ticker)??null,weight:r.weight})),memberships:membershipMap(payload),themeIds:themes.map(t=>t.id)});
   strategy=render(strategyTitle,'strategy',result,id=>label(themes.find(t=>t.id===id),locale));}
  const cat=catalog&&Array.isArray(catalog.themes)?catalog.themes:[],rows=cat.map(th=>{const r=(ram.themes||[]).find(x=>x.theme_id===th.theme_id);return{company_id:th.theme_id,weight:r?r.weight:null};});
  const result=themeConcentration({rows,memberships:Object.fromEntries(cat.map(th=>[th.theme_id,{[th.theme_id]:true}])),themeIds:cat.map(th=>th.theme_id)});
  target=render(targetTitle,'target',result,id=>{const th=cat.find(x=>x.theme_id===id);return th?(locale==='en-US'?th.label_en:th.label):id;});}
 return '<div data-concentration><p><b>'+esc(T('테마 쏠림 경고','Theme concentration warning'))+'</b> <span class="small">'+esc(rule)+'</span> '+marker(locale)+'</p><ul class="axis-chips">'+strategy+target+'</ul><p class="small">'+esc(T('기기 RAM에서만 계산 · 저장·공개 안 함 · 매수·매도 지시 아님','Computed in device RAM only · never stored or published · not a buy/sell instruction'))+'</p></div>';
}
return Object.freeze({FILE,THRESHOLD,validate,load,record,concentrationStatus,themeConcentration,membershipMap,industryComposition,industryChip,themeChip,industryCard,concentrationBlock,marker});
});
