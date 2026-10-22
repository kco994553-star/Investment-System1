/* S06 leaderboard table. Price-free public data only; price columns stay NOT_AVAILABLE and are bundled into one note until real inputs exist.
   'My profile' view is a RAM-only PREVIEW from published Q/G factors; nothing calculated is stored.
   M3 cap rank: device-only (PrivateSubsetView rank index from the private Universe sheet read in RAM); passed in, shown, never stored.
   Default view scores come only from QgvScores: QGV v2 is the only score (owner decision 2026-10-14; no v1 comparison or
   [자세히] v1 reference). A company without a v2 score shows the v2 NOT_AVAILABLE reason. The v2 rank is a RAM-only order. */
(function(root,factory){const node=typeof module==='object'&&module.exports;const api=factory(node?()=>require('./qgv-scores.js'):()=>root.QgvScores);if(node)module.exports=api;else root.LeaderboardScreen=api;})(globalThis,function(qgvScores){
'use strict';
/* Shown columns. Below 750px (NARROW) the 'wide' columns are not drawn: their content moves into the per-row details button of the
   QGV cell (phone: rank, company and the QGV total come first; no column is hidden by CSS). Columns that would always be — (no
   price or unconnected input) are not drawn at any width; one note names them. */
const NARROW='(max-width: 749.98px)';
const COLUMNS=[['rank','순위','Rank'],['company','기업·시총 순위','Company · cap rank'],['qgv','QGV','QGV'],['qgv_detail','Q·G·V 상세','Q·G·V detail',true],['earnings','실적','Earnings',true]];
const UNCONNECTED=[['daily','일간','Daily'],['consensus','컨센서스','Consensus'],['target','목표','Target'],['scenario','QGV 시나리오','QGV scenario'],['reeval','재평가','Re-evaluation'],['vmr','VMR','VMR']];
// Phone detail rows the user opened (RAM only, this page): kept across repaints after new device quotes.
const OPEN=new Set();
const STAGES=[['정상','Normal'],['관찰','Watch'],['근접','Near'],['재평가','Re-evaluate']];
/* QGV menu layout (design lane D2; owner draft "투자시스템 화면 시안 (손그림 칠판)", PRODUCT_IA_DIRECTIVE_20261018): the S06 card is
   drawn as numbered stamp sections with the function numbers 2.1.1–2.1.7 (the menu strip keeps 1 / 1.1). Presentation only: the
   same nodes, scores, ranks, sort rules and data attributes as before; only their grouping, headings and the Q·G·V bars change.
   2.1.3 (search · interest · TARGET · group · sort selector) is the app's filter row (app.js leaderboard) under fnHeadHtml. */
const FN=Object.freeze({LIST:['2.1.1','평가 대상과 목록','Evaluated companies and list'],SORT:['2.1.2','순위와 정렬','Rank and sort'],
 FILTER:['2.1.3','분류와 필터','Classification and filters'],PERIOD:['2.1.4','기간별 수익률','Returns by period'],STATE:['2.1.5','산출 상태별 목록','Lists by calculation state'],
 SCOPE:['2.1.6','공식 결과와 개인 결과','Official and personal results'],CAND:['2.1.7','후보 선정 연결','Link to candidate selection']});
// Periods the owner named for 2.1.4 ("수익률 1D 20D등"). No return is computed or published: they stay 미산출 until a device price column exists.
const PERIODS=['1D','20D'];
const fnId=key=>'lb-fn-'+FN[key][0].replaceAll('.','-');
const escHtml=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]);
// Stamp heading and display-only classification filters for the app's 2.1.3 row.
function fnHeadHtml(key,locale){const[fn,ko,en]=FN[key];return '<h2 class="fn-head" id="'+fnId(key)+'"><span class="ia-sec">'+fn+'</span> <span class="fn-title">'+escHtml(locale==='en-US'?en:ko)+'</span></h2>';}
function filterNoteHtml(locale){return '<p class="small" data-classification-note>'+escHtml(locale==='en-US'?'Industry, strategy theme and investment type are separate axes. These filters use the published SIC industry group and the company page’s type rule. They only hide rows: the Universe, official scores, ranks and model candidates do not change. Missing classification is not zero or another classification.':'산업·전략 테마·투자 유형은 서로 다른 축입니다. 게시된 SIC 업종군과 기업 화면의 유형 규칙으로 행만 숨깁니다. Universe·공식 점수·순위·모델 후보는 바뀌지 않습니다. 분류 자료 없음은 0이나 다른 분류로 대신 채우지 않습니다.')+'</p>';}
// Selections belong to this page's RAM, not the scoring profile, sessionStorage or the published population.
// Repainting on APPLIED/REJUDGE reuses the choices with NEW inputs. A removed option stays selected (no silent broadening).
let classificationView={industry:'',type:''};
function classificationOf(identity,publicScreens={}){
 const id=identity.company_id,CS=globalThis.CompanyScreen,live=r=>r&&['LIVE','STALE'].includes(r.state)&&r.identity_withdrawn!==true;
 let industry=null,memberships=null;
 if(typeof id==='string'&&id.includes(':')){
  const rec=publicScreens['sec-qgv2.json']?.records?.[id];
  if(live(rec)){industry=rec.industry_group||null;const m=qgvScores()?.typeMemberships({identity,publicScreens});if(m?.code===id)memberships=m.memberships;}
 }else{
  // Same published sources as CompanyScreen.classification: themes and financial profiles never fill either axis.
  const ind=publicScreens['company-classification.json']?.data?.companies?.[id]?.industry;
  if(live(ind))industry=ind.group||null;
  const rec=publicScreens['company-types-pricefree.json']?.data?.companies?.[id];if(live(rec))memberships=rec.memberships;
 }
 const has=memberships&&Object.values(memberships).some(v=>typeof v==='number'&&Number.isFinite(v));
 const types=has&&CS?.selectTypes?CS.selectTypes(memberships):null;
 return{industry,types};
}
function filterClassifications(identities,{publicScreens={},filters=classificationView}={}){
 return identities.filter(c=>{const x=classificationOf(c,publicScreens),i=filters.industry,t=filters.type;
  return(!i||(i==='NOT_AVAILABLE'?x.industry===null:x.industry===i))&&(!t||(t==='NOT_AVAILABLE'?x.types===null:t==='NO_SELECTED_TYPE'?Array.isArray(x.types)&&x.types.length===0:x.types?.includes(t)));});
}
function industryLabel(id,publicScreens,locale){const x=publicScreens['company-classification.json']?.data?.industry_config?.groups?.find(x=>x.id===id);
 return x?(locale==='en-US'?x.name_en:x.name):globalThis.UniverseCompany?.GROUP_LABEL?.[id]?.[locale==='en-US'?1:0]||id;}
function classificationSummary({publicScreens={},locale='ko-KR'}={}){
 const en=locale==='en-US',missing=en?'Classification data missing':'분류 자료 없음',out=[];
 if(classificationView.industry)out.push((en?'SIC industry group: ':'SIC 업종군: ')+(classificationView.industry==='NOT_AVAILABLE'?missing:industryLabel(classificationView.industry,publicScreens,locale)));
 if(classificationView.type)out.push((en?'Company type: ':'기업 유형: ')+(classificationView.type==='NOT_AVAILABLE'?missing:classificationView.type==='NO_SELECTED_TYPE'?(en?'No selected type':'선택 유형 없음'):globalThis.CompanyScreen?.typeName(classificationView.type,locale)||classificationView.type));
 return out;
}
function classificationFiltersHtml(identities,{publicScreens={},locale='ko-KR'}={}){
 const en=locale==='en-US',CS=globalThis.CompanyScreen,rows=identities.map(c=>classificationOf(c,publicScreens)),groups=[...new Set(rows.map(r=>r.industry).filter(Boolean))].sort();
 const label=id=>industryLabel(id,publicScreens,locale);
 const select=(axis,title,options)=>{const chosen=classificationView[axis],opts=[['',en?'All':'전체'],...options];
  if(chosen&&!opts.some(([id])=>id===chosen))opts.push([chosen,en?'Selected group absent from this publication':'선택한 업종군이 새 게시본에 없음']);
  return '<label for="leader-classification-'+axis+'">'+escHtml(title)+' <select id="leader-classification-'+axis+'" data-classification-filter="'+axis+'">'+opts.map(([id,name])=>'<option value="'+escHtml(id)+'"'+(chosen===id?' selected':'')+'>'+escHtml(name)+'</option>').join('')+'</select></label>';};
 const missing=en?'Classification data missing':'분류 자료 없음',none=en?'No selected type (available memberships)':'선택 유형 없음 (확보된 소속도 기준)';
 return '<div class="chips">'+select('industry',en?'SIC industry group':'SIC 업종군',groups.map(id=>[id,label(id)]).concat([['NOT_AVAILABLE',missing]]))
  +select('type',en?'Company type':'기업 유형',(CS?.TYPES||[]).map(id=>[id,CS.typeName(id,locale)]).concat([['NOT_AVAILABLE',missing],['NO_SELECTED_TYPE',none]]))+'</div>'
  +'<p class="small" data-classification-coverage>'+escHtml((en?'Classification in the full list: ':'전체 목록의 분류: ')+(en?'industry missing ':'업종군 자료 없음 ')+rows.filter(r=>r.industry===null).length+' · '+(en?'type missing ':'유형 자료 없음 ')+rows.filter(r=>r.types===null).length+' · '+(en?'no selected type ':'선택 유형 없음 ')+rows.filter(r=>r.types?.length===0).length)+'</p>';
}
function mountClassificationFilters(host,identities,options={}){
 if(!host)return;const active=host.contains(host.ownerDocument.activeElement)?host.ownerDocument.activeElement.id:null;
 host.innerHTML=classificationFiltersHtml(identities,options);
 for(const select of host.querySelectorAll('[data-classification-filter]'))select.onchange=()=>{classificationView={...classificationView,[select.dataset.classificationFilter]:select.value};options.onChange?.();};
 if(active)host.ownerDocument.getElementById(active)?.focus({preventScroll:true});
}
/* Q·G·V bars of one score row (decoration: aria-hidden; the numbers and their words are in the QGV / detail cells). Widths are
   SVG attributes (CSP style-src 'self': no inline style). A missing axis is an empty dashed track, never a 0 bar; no axis at all draws nothing. */
const SVG_NS='http://www.w3.org/2000/svg';
function qgvBars(doc,p){if(![p.q,p.g,p.v].some(v=>typeof v==='number'&&Number.isFinite(v)))return null;const box=doc.createElement('span');box.setAttribute('class','qgv-bars');box.setAttribute('aria-hidden','true');box.setAttribute('data-qgv-bars','');
 for(const[a,v]of [['Q',p.q],['G',p.g],['V',p.v]]){const ok=typeof v==='number'&&Number.isFinite(v),row=doc.createElement('span');row.setAttribute('class','qb');row.setAttribute('data-axis',a);row.setAttribute('data-state',ok?'OK':'NA');
  const svg=doc.createElementNS(SVG_NS,'svg');svg.setAttribute('viewBox','0 0 100 10');svg.setAttribute('preserveAspectRatio','none');svg.setAttribute('focusable','false');
  const track=doc.createElementNS(SVG_NS,'rect');for(const[k,x]of [['class','qb-track'],['x','0.5'],['y','1'],['width','99'],['height','8'],['rx','2']])track.setAttribute(k,x);svg.append(track);
  if(ok){const fill=doc.createElementNS(SVG_NS,'rect'),w=Math.max(0,Math.min(100,v));for(const[k,x]of [['class','qb-fill'],['x','0.5'],['y','1'],['width',String(Math.max(0.5,w*0.99))],['height','8'],['rx','2']])fill.setAttribute(k,x);svg.append(fill);}
  row.append(svg);box.append(row);}
 return box;}
/* Exploration filter (FE-MISSING-2, owner instruction 2026-10-17), from QgvScores.exploreGroup of each row: 'ranked' = a QGV
   total with V and an official device rank; 'qg' = the QG 참고 목록 (V 미포함): a total from Q·G only (V not applicable or not
   computed; D11 owner rule, never mixed into the official order, its own order by the same total, no rank); 'partial' = some
   axis score but no total, so no rank and never in the ranked order; 'check' = no axis score (data to check). Ranks stay the
   ones over all identities; the filter only hides rows. */
const EXPLORE=[['all','전체','All'],['ranked','공식 QGV 순위','Official QGV ranking'],['qg','QG 참고 목록 (V 미포함)','Q·G reference list (V not included)'],['partial','일부 축만 가능','Some axes only'],['check','자료 확인 필요','Check data']];
const EXPLORE_OF={RANKED:'ranked',QG_REFERENCE:'qg',PARTIAL_AXES:'partial',CHECK_DATA:'check'},EXPLORE_IDS=EXPLORE.map(e=>e[0]);
function exploreOf(r){const QS=qgvScores();return EXPLORE_OF[QS&&QS.exploreGroup?QS.exploreGroup(r.score):'CHECK_DATA']||'check';}
/* S06 structured sort (owner directive 2026-10-18 §4.4). [id, key, direction (1 asc, -1 desc), [ko, en]]. Keys are numbers or
   strings from the score rows, never display text. NA is last in both directions; ties: QGV by ticker (= the official rank
   order), market cap by company_id (M3 rule), others by ticker. Sorting only orders rows: the rank shown is always the official
   device rank. 'ticker', 'name' and 'favorites' are the legacy ids that DeviceWatchlist.filter already orders (unchanged).
   Market cap = the M3 cap rank of this device's private Universe read (offered only while that subset is READY). No per-company
   return column exists (spec §19 only), so no return sort is offered. */
const SORTS=[['qgv','qgv',-1,['QGV v2 순','QGV v2 (high first)']],['qgv-asc','qgv',1,['QGV 낮은 순','QGV v2 (low first)']],
 ['q-desc','q',-1,['Q 높은 순','Q (high first)']],['q-asc','q',1,['Q 낮은 순','Q (low first)']],['g-desc','g',-1,['G 높은 순','G (high first)']],['g-asc','g',1,['G 낮은 순','G (low first)']],
 ['v-desc','v',-1,['V 높은 순','V (high first)']],['v-asc','v',1,['V 낮은 순','V (low first)']],
 ['ticker','ticker',1,['티커 순','Ticker']],['ticker-desc','ticker',-1,['티커 역순','Ticker (Z–A)']],['name','name',1,['기업명 순','Name']],['name-desc','name',-1,['기업명 역순','Name (Z–A)']],
 ['favorites','favorites',-1,['관심기업 우선','Favorites first']],['asof-desc','asof',-1,['자료 기준일 최신 순','Data date (newest first)']],['asof-asc','asof',1,['자료 기준일 오래된 순','Data date (oldest first)']],
 ['cap-desc','cap',-1,['시가총액 큰 순 · 내 기기','Market cap (largest) · my device']],['cap-asc','cap',1,['시가총액 작은 순 · 내 기기','Market cap (smallest) · my device']]];
const SORT_IDS=Object.freeze(SORTS.map(s=>s[0])),LEGACY_SORTS=['qgv','ticker','name','favorites'],DEFAULT_SORT='qgv';
function sortSpec(id){return SORTS.find(s=>s[0]===id)||SORTS[0];}
function sortLabel(id,en){const s=SORTS.find(x=>x[0]===id);return s?s[3][en?1:0]:null;}
// New options for the S06 sort selector (the legacy four keep their app labels and come first).
function sortOptions(en){return SORTS.filter(s=>!LEGACY_SORTS.includes(s[0])).map(s=>[s[0],s[3][en?1:0]]);}
// The id of the same key in the other direction (null for favorites, which has one direction).
function oppositeSort(id){const[,key,dir]=sortSpec(id),o=SORTS.find(s=>s[1]===key&&s[2]===-dir);return o?o[0]:null;}
function sortAvailable(id,{deviceRanks=null}={}){return sortSpec(id)[1]!=='cap'||deviceRanks?.state==='READY';}
/* Pure: rows ({company_id, ticker, name}) ordered by sort id over the QgvScores result S (rows[cid].rank / primary) and the M3
   ranks. Returns a new array (input untouched). QGV sort (D11): the official ranking first, then the QG 참고 목록 (V 미포함) in its
   own order by the same total, then rows without a total; the two lists are never interleaved. */
function sortRows(rows,S,id,{deviceRanks=null}={}){
 if(['ticker','name','favorites'].includes(id))return rows;
 const[,key,dir]=sortSpec(id),num=v=>typeof v==='number'&&Number.isFinite(v)?v:null,score=r=>S&&S.rows?S.rows[r.company_id]:null;
 const value=r=>{const x=score(r),p=x?x.primary:null;
  if(key==='qgv')return x&&(Number.isInteger(x.rank)||x.qg_reference)?num(p.total):null;if(['q','g','v'].includes(key))return p?num(p[key]):null;
  if(key==='ticker'||key==='name')return typeof r[key]==='string'?r[key]:null;
  if(key==='asof'){const t=p&&p.coverage&&p.coverage.source?Date.parse(p.coverage.source.acquired_at):NaN;return Number.isFinite(t)?t:null;}
  if(key==='cap'){const m=m3For(deviceRanks,r);return Number.isInteger(m.rank)?m.rank:null;}return null;};
 const tie=key==='cap'?(a,b)=>(a.company_id<b.company_id?-1:a.company_id>b.company_id?1:0):(a,b)=>String(a.ticker).localeCompare(String(b.ticker));
 // Market cap: the M3 rank is 1 = largest, so 'largest first' is rank ascending.
 const m=key==='cap'?-dir:dir,tier=r=>{const x=key==='qgv'?score(r):null;return x&&x.qg_reference&&!Number.isInteger(x.rank)?1:0;},keyed=rows.map(r=>({r,v:value(r),t:tier(r)}));
 keyed.sort((a,b)=>(a.v===null)-(b.v===null)||a.t-b.t||(a.v!==null&&b.v!==null?(typeof a.v==='string'?a.v.localeCompare(b.v):a.v<b.v?-1:a.v>b.v?1:0)*m:0)||tie(a.r,b.r));
 return keyed.map(x=>x.r);}
// Analysis population (pooled sec-qgv2 cross-section points), not the screen's identities nor the device market-cap subset.
function populationOf(publicScreens){const inputs=publicScreens&&publicScreens['sec-qgv2.json'];if(!inputs||!inputs.records||typeof inputs.records!=='object')return null;
 let n=0;for(const r of Object.values(inputs.records))if(r&&r.in_cross_section===true&&['LIVE','STALE'].includes(r.state)&&r.calc_version_mismatch!==true&&r.identity_withdrawn!==true)n++;return n;}
// Pure: one row per identity, using only published price-free inputs.
const M3_LABEL=['M3 · 내 기기 기준 · v0','M3 · My device · v0'];
function m3For(ranks,c){if(!ranks||ranks.state!=='READY')return{state:'NOT_AVAILABLE',rank:null,reason_codes:[...(ranks?.reason_codes||['UNIVERSE_NOT_READ'])]};const e=ranks.entries.get('id:'+c.company_id)||ranks.entries.get('sym:'+String(c.ticker||'').replaceAll('.','-'));return e?{state:e.state,rank:e.rank,quality:e.quality||null,group_id:e.group_id||null,reason_codes:[...e.reason_codes]}:{state:'NOT_AVAILABLE',rank:null,reason_codes:['NOT_IN_UNIVERSE']};}
function rowsFor(identities,{publicScreens={},engine=null,filings=null,weights=null,deviceRanks=null,scores=null,disclosures=globalThis.SecDisclosures}={}){
 const S=scores||(weights||!qgvScores()?null:qgvScores().compute({identities,publicScreens}));
 const factors=publicScreens['sec-qg-factors.json']?.data?.companies||{},windows=publicScreens['sec-filing-windows.json']?.data?.companies||{};
 return identities.map(c=>{const obs={};for(const[f,v]of Object.entries(factors[c.company_id]?.factors||{}))if(v&&v.score!==null&&v.state!=='NOT_AVAILABLE')obs[f]={score:v.score,quality:v.state==='LIVE'?'OK':'STALE_DATA'};
  const has=Object.keys(obs).length>0&&engine,r=has?engine.strategy({observations:obs,...(weights?{user_weights:weights}:{})}):null,axis=a=>typeof r?.axes?.[a]?.score==='number'?r.axes[a].score:null,partial=a=>r?.axes?.[a]?.coverage&&r.axes[a].coverage!=='READY';
  const w=windows[c.company_id]&&windows[c.company_id].state!=='NOT_AVAILABLE'&&filings?filings.nextFilingWindow(windows[c.company_id]):null;
  const fa=r&&r.axes?['Q','G'].map(a=>r.axes[a]):null;
  const earnings=disclosures?.qgvEarningsStatus?.(windows[c.company_id],publicScreens['sec-qgv2.json']?.target?.[c.company_id]);
  return{earnings_status:earnings?.status||'NOT_CONFIRMED',company_id:c.company_id,ticker:c.ticker,name:c.name,q:axis('Q'),g:axis('G'),factors:fa&&fa.every(x=>Number.isInteger(x.factors_available))?(fa[0].factors_available+fa[1].factors_available)+'/'+(fa[0].factors_total+fa[1].factors_total):null,partial:partial('Q')||partial('G'),qg_total:typeof r?.qg_preview_total==='number'?r.qg_preview_total:null,next_window:w?w.start+'–'+w.end:null,m3:m3For(deviceRanks,c),score:S&&S.rows[c.company_id]?S.rows[c.company_id]:null};});}
/* Model portfolio checks per N (QgvScores.modelPortfolios): §16 feasibility at equal weight 100/N (shortfall weight and cause, never
   filled or rescaled), the R-C tier weights on N15 (check only) and the same-issuer summed weight (recommendation, decision needed).
   Data attributes carry the machine values; the text says the same in words. */
function modelChecks(M,QS2,en,el){const box=el('div',undefined,{'data-model-checks':''}),pct=v=>v.toFixed(2)+'%',nm=id=>QS2.sectorName(id,en);
 const L=M.limits,limitsHead=en?'§16 limits per N (equal weight, never relaxed): ':'N별 16절 한도 검사 (동일 비중 · 한도 완화 없음): ';
 box.append(el('p',limitsHead+(en?'single name '+L.single_max_pct+'% · sector group '+L.sector_group_max_pct+'% (semiconductors + equipment one group) · at least '+L.min_holdings+' names.':'단일 종목 '+L.single_max_pct+'% · 업종 묶음 '+L.sector_group_max_pct+'% (반도체+반도체 장비 한 묶음) · 최소 '+L.min_holdings+'종목.'),{class:'small','data-model-limits-rule':JSON.stringify(L)}));
 for(const n of QS2.MODEL_NS){const s=M.sets['N'+n],g=s.limits.group,top=g.groups.reduce((a,x)=>x.pct>(a?a.pct:-1)?x:a,null),parts=[];
  const head={FEASIBLE:en?'can be built under the §16 limits':'16절 한도 아래 구성 가능',SHORTFALL:en?'cannot be built':'구성 불가',UNVERIFIED:en?n+' names · the 40% sector-group check cannot be completed':n+'종목 구성 · 업종 묶음 40% 확인 불가',FAIL:en?'§16 limit broken':'16절 한도 위반'}[s.status];
  parts.push('N'+n+' · '+head);
  if(s.status==='SHORTFALL'){const capped=s.causes.find(c=>c.code==='SECTOR_GROUP_MAX_40'),sub=s.causes.find(c=>c.code==='SUBGROUP_MAX_4');
   parts.push((en?'shortfall weight ':'부족 비중 ')+pct(s.shortfall_pct)+' ('+s.selected.length+'/'+n+(en?' · not filled · no re-weighting':' · 채우지 않음 · 비중 재조정 없음')+')');
   parts.push((en?'cause: ':'원인: ')+[capped?(en?capped.groups.map(nm).join('/')+' '+L.sector_group_max_pct+'% cap excluded '+capped.count:capped.groups.map(nm).join('/')+' '+L.sector_group_max_pct+'% 한도로 '+capped.count+'종목 초과'):null,sub?(en?'subgroup cap excluded '+sub.count:'하위 묶음 상한으로 '+sub.count+'종목 제외'):null,en?'not enough eligible replacements':'대체 후보 부족',s.selected.length<L.min_holdings?(en?'below '+L.min_holdings+' names':'최소 '+L.min_holdings+'종목 미달'):null].filter(Boolean).join(', '));}
  parts.push((en?'each ':'각 ')+pct(s.weight_pct)+(s.limits.single.ok?' ≤ ':' > ')+L.single_max_pct+'%');
  if(top)parts.push((en?'largest group ':'최대 업종 묶음 ')+nm(top.id)+' '+pct(top.pct)+' ('+top.count+(en?' names':'종목')+(en?', cap ':' · 상한 ')+L.sector_group_max_pct+'%)');
  if(g.unknown.count)parts.push((en?'group unknown ':'업종 묶음 미정 ')+g.unknown.count+(en?' names ':'종목 ')+pct(g.unknown.pct)+(en?' (subgroup unknown · provisional, not capped)':' (하위 묶음 미정 · 잠정 · 상한 미적용)'));
  if(s.group_capped.length)parts.push((en?'skipped by the 40% group cap: ':'업종 묶음 40% 한도로 건너뜀: ')+s.group_capped.map(c=>c.ticker+' #'+c.rank+' ('+nm(c.group)+')').join(', ')+(en?' → next eligible rank':' → 다음 자격 순위로 대체'));
  box.append(el('p',parts.join(' · '),{class:'small','data-model-limits':'N'+n,'data-model-feasible':s.status,'data-model-shortfall-pct':s.shortfall_pct.toFixed(2),'data-model-group-status':g.status,
   'data-model-group-pct':JSON.stringify(Object.fromEntries(g.groups.map(x=>[x.id,Number(x.pct.toFixed(4))]))),'data-model-unknown-pct':g.unknown.pct.toFixed(2),'data-model-group-skipped':String(s.skipped.SECTOR_GROUP_MAX_40),'data-model-causes':s.causes.map(c=>c.code).join(' ')}));}
 const t=M.sets['N'+QS2.TIERS_RC.n]&&M.sets['N'+QS2.TIERS_RC.n].tier_check;
 if(t){const T=QS2.TIERS_RC,word={PASS:en?'§16 pass':'16절 통과',UNVERIFIED:en?'40% group check cannot be completed':'업종 묶음 40% 확인 불가',FAIL:en?'§16 broken':'16절 위반',CORE_SHORT:en?'core '+t.core+'/'+T.core_n+' · sum ':'핵심 '+t.core+'/'+T.core_n+' · 합계 ',INCOMPLETE:en?'N'+T.n+' incomplete':'N'+T.n+' 미완성'}[t.status];
  const sum=t.limits.sum_pct,top=t.limits.group.groups.reduce((a,x)=>x.pct>(a?a.pct:-1)?x:a,null);
  box.append(el('p',(en?'Check only · R-C (TARGET v1) tier weights on N'+T.n+' (selection unchanged): core '+T.core_n+' × '+T.core_pct+'% (top '+T.core_n+', calculated factors ≥ '+T.core_factors_min*100+'%, financial safety passed) + general × '+T.general_pct+'% → ':'참고 검사 · R-C(TARGET v1) 등급 비중을 N'+T.n+'에 넣으면 (선정 불변): 핵심 '+T.core_n+' × '+T.core_pct+'% (상위 '+T.core_n+' · 산출 요인 ≥ '+T.core_factors_min*100+'% · 재무 안전 통과) + 일반 × '+T.general_pct+'% → ')+word+(t.status==='CORE_SHORT'?pct(sum)+(en?' (not 100%)':' (100% 아님)'):'')+(top?' · '+(en?'largest group ':'최대 업종 묶음 ')+nm(top.id)+' '+pct(top.pct):'')+(t.limits.group.unknown.count?' · '+(en?'group unknown ':'업종 묶음 미정 ')+pct(t.limits.group.unknown.pct):''),
   {class:'small','data-model-tier-check':t.status,'data-model-tier-core':String(t.core),'data-model-tier-sum':sum.toFixed(2),'data-model-tier-group-status':t.limits.group.status}));}
 for(const n of QS2.MODEL_NS){const c=M.sets['N'+n].issuer_check;
  box.append(el('p','N'+n+' · '+(en?'same-issuer summed weight (recommendation · decision needed · selection unchanged): ':'같은 발행사 합산 비중 (권장안 · 결정 필요 · 선정 불변): ')+(c.issuers.length?c.issuers.map(x=>x.tickers.join('+')+' '+pct(x.pct)+(x.over_single_max?(en?' (over the '+c.limit+'% single-name cap if read per issuer)':' (발행사 기준으로 읽으면 단일 '+c.limit+'% 초과)'):'')).join(' · '):(en?'no issuer holds two seats':'같은 발행사 중복 없음'))+' · '+(en?'largest issuer ':'발행사 최대 ')+pct(c.max_issuer_pct),
   {class:'small','data-model-issuer':'N'+n,'data-model-issuer-status':c.status,'data-model-issuer-applied':String(c.applied),'data-model-issuer-max-pct':c.max_issuer_pct.toFixed(2),'data-model-issuer-multi':JSON.stringify(c.issuers.map(x=>({tickers:x.tickers,pct:Number(x.pct.toFixed(4)),over:x.over_single_max})))}));}
 return box;}
/* D12 (owner decision 2026-10-19): `identities` are the Universe rows of the official evaluation after the screen filters; `outside`
   the TARGET identities outside the Universe after the same filters (own labelled list, never in the table or the rank population);
   targetOnly: the TARGET filter is on, so each officially ranked TARGET row also shows its '포트폴리오 내 순위' (the official order
   reduced to the TARGET rows in the Universe; a named second number, never the rank column). */
function mount(host,identities,{publicScreens={},locale,view='default',profiles=[],profileId=null,onView=()=>{},engine=globalThis.EnginePreview,filings=globalThis.PublicScreens,deviceRanks=null,scores=null,explore='all',nameOf=null,outside=[],targetOnly=false,model=undefined,priceBasis=null}={}){
 if(!host)return;const doc=host.ownerDocument,en=locale==='en-US',el=(tag,text,attrs={})=>{const n=doc.createElement(tag);if(text!==undefined)n.textContent=text;for(const[k,v]of Object.entries(attrs))n.setAttribute(k,v);return n;};
 const card=el('section',undefined,{class:'card','data-leaderboard-screen':view}),QM=qgvScores(),mark=(n,row)=>{if(QM&&typeof QM.marks==='function')for(const[k,v]of Object.entries(row===undefined?QM.readMarks(priceBasis,doc.defaultView):QM.marks(row,priceBasis,doc.defaultView)))n.setAttribute(k,v);};mark(card);
 // Numbered stamp sections (FN). The controls (2.1.6, 2.1.5, 2.1.2, 2.1.4) sit in one grid above the list (2.1.1); 2.1.7 last.
 const sec=key=>{const[fn,ko,enl]=FN[key],s=el('section',undefined,{class:'fn-sec','data-fn':fn,'aria-labelledby':fnId(key)}),h=el('h2',undefined,{class:'fn-head',id:fnId(key)});h.append(el('span',fn,{class:'ia-sec'}),doc.createTextNode(' '),el('span',en?enl:ko,{class:'fn-title'+(key==='LIST'?' hl':'')}));s.append(h);return s;};
 const sScope=sec('SCOPE'),sState=sec('STATE'),sSort=sec('SORT'),sPeriod=sec('PERIOD'),sList=sec('LIST'),sCand=sec('CAND'),grid=el('div',undefined,{class:'fn-grid','data-fn-group':'controls'}),badges=el('div',undefined,{class:'chips data-badges'});grid.append(sScope,sState,sSort,sPeriod);
 card.append(el('p',en?'Function 2.1 Leaderboard (menu 1.1) · the stamp numbers are the function numbers':'기능 2.1 리더보드 (메뉴 1.1) · 상자의 번호는 기능 번호입니다',{class:'small fn-legend','data-fn-legend':'2.1'}),badges,grid,sList,sCand);const QS=qgvScores(),S=view!=='profile'&&QS?(scores||QS.compute({identities,publicScreens})):null;
 const v2AsOf=(S||scores)?.v2_as_of||null,v1AsOf=publicScreens['sec-qg-factors.json']?.as_of||null;
 // Score time = sec-qgv2.json as_of (the v2 input). sec-qg-factors.json is only the v1 PREVIEW input of the profile view.
 const off=S&&S.official?S.official:(scores&&scores.official?scores.official:null);
 // Provenance (QgvScores.provenance): on any preset but the official default the rank is a personal rank, never called 공식.
 const prov=S&&QS.provenance?QS.provenance({profile:S.profile,priced:S.priced_codes>0}):null,personal=!!prov&&prov.weights==='PERSONAL',rankWord=en?(personal?'personal preset rank':'official device rank'):(personal?'개인 프리셋 순위':'공식 기기 순위');
 badges.append(el('span',off?(en?'Universe '+off.evaluated+' · '+(personal?'personal preset evaluation':'official evaluation'):'Universe '+off.evaluated+'개 · '+(personal?'개인 프리셋 평가':'공식 평가')):(en?'US top 500 · target scope':'미국 상위 500 · 목표 범위'),{class:'badge','data-leaderboard-population':off?'UNIVERSE':'IDENTITIES'}),...(S?[el('span',QS.basisText(S,en),{class:'badge','data-scoring-default':'v2','data-scoring-basis-label':S.basis.label})]:[]),...(prov?[el('span',QS.provenanceText(prov,en),{class:'badge'+(personal?' partial':''),'data-qgv-provenance':'S06',...QS.provenanceAttrs(prov)})]:[]),el('span',(en?'Score as of ':'점수 기준 ')+(v2AsOf||'NOT_AVAILABLE'),{class:'badge','data-score-as-of':v2AsOf?'v2':'NOT_AVAILABLE'}),...(view==='profile'?[el('span',(en?'v1 PREVIEW input as of ':'v1 미리보기 입력 기준 ')+(v1AsOf||'NOT_AVAILABLE'),{class:'badge','data-v1-preview-as-of':''})]:[]));
 const ready=deviceRanks?.state==='READY',m3Note=ready?(deviceRanks.status==='COMPLETE'?(en?'verified rows · complete':'검증 행 · 완전'):(en?'verified rows only · partial':'검증 행만 · 부분'))+' · '+(en?'verified ':'검증 ')+deviceRanks.verified_count+(deviceRanks.config_status?' · '+deviceRanks.config_status:''):'NOT_AVAILABLE · '+(deviceRanks?.reason_codes?.join(' / ')||(en?'Universe not read on this device':'Universe 읽기 전'));
 badges.append(el('span',M3_LABEL[en?1:0]+' · '+m3Note,{class:'badge','data-leaderboard-m3-basis':ready?'READY':'NOT_AVAILABLE'}));
 const tabs=el('div',undefined,{class:'chips screen-tabs',role:'group'});for(const[id,label]of [['default',en?'Default':'기본'],['profile',en?'My profile (PREVIEW)':'내 프로필 기준(PREVIEW)'],['device',en?'My device (M3)':'내 기기 기준(M3)']]){const b=el('button',label,{type:'button','data-leaderboard-view':id,'aria-pressed':String(view===id)});b.onclick=()=>onView({view:id});tabs.append(b);}sScope.append(tabs);
 if(S){const p=S.profile,v2note=S.v2_state==='READY'?(en?p.name.name_en:p.name.name)+' · '+(en?'gate ':'관문 ')+(p.gate?(en?'on':'켬'):(en?'off':'끔'))+' · '+(en?'priced ':'가격 ')+S.priced_codes+(en?' (this device, RAM)':' (이 기기·메모리)'):(en?'v2 · NOT_AVAILABLE · ':'v2 · NOT_AVAILABLE · ')+(Array.isArray(S.v2_reason_text)?S.v2_reason_text[en?1:0]:S.v2_reason);
  tabs.append(el('span',v2note,{class:'badge','data-qgv2-state':S.v2_state}));
  const presets=el('div',undefined,{class:'chips','data-qgv2-presets':'',role:'group','aria-label':en?'QGV v2 profile':'QGV v2 프로필'});
  for(const[id,pr]of Object.entries(qgvScores().presets())){const b=el('button',en?pr.name_en:pr.name,{type:'button','data-qgv2-preset':id,'aria-pressed':String(p.preset===id)});b.onclick=()=>onView({preset:id});presets.append(b);}
  const gate=el('label',en?' Value-trap gate':' 가치 함정 관문',{class:'small'}),box=el('input',undefined,{type:'checkbox','data-qgv2-gate':''});box.checked=p.gate;box.onchange=()=>onView({gate:box.checked});gate.prepend(box);presets.append(gate);sScope.append(presets);}
 let weights=null;if(view==='profile'){const select=el('select',undefined,{'data-leaderboard-profile':'','aria-label':en?'Profile':'프로필'});select.append(el('option',en?'Choose a saved profile':'저장한 프로필 선택',{value:''}));for(const p of profiles){const o=el('option',p.name,{value:p.id});if(p.id===profileId)o.selected=true;select.append(o);}select.onchange=()=>onView({view,profileId:select.value||null});sScope.append(select);
  const chosen=profiles.find(p=>p.id===profileId);if(chosen)weights=chosen.weights;sScope.append(el('p',(en?'v1 preview (not the official v2 score) · ':'v1 미리보기 (공식 v2 점수 아님) · ')+(chosen?(en?'PREVIEW · RAM only · Q/G recalculated with your profile; not mixed with official results':'PREVIEW · 메모리 전용 · 내 프로필로 Q/G 재계산, 공식 결과와 섞지 않음'):(en?'No saved profile selected. Create one in Strategy profile.':'선택한 프로필이 없습니다. 전략 프로필에서 만드세요.')),{class:'small','data-leaderboard-preview-note':''}));}
 if(view==='device'){sScope.append(el('p',en?'My device view reads your private Universe sheet in RAM. Open it below.':'내 기기 기준은 비공개 Universe 시트를 메모리에서 읽습니다. 아래에서 여세요.',{class:'small'}));}
 const all=rowsFor(identities,{publicScreens,engine,filings,weights,deviceRanks,scores:S}),show=v=>v===null?'—':(Math.round(v*10)/10).toFixed(1);
 /* Direction and reset next to the S06 sort selector (#leader-sort, app.js, the phone sort control too): they change only that
    selector's value and fire its change event, so the app keeps one sort state. Unavailable keys (market cap without the device
    subset) are disabled in the selector with the reason. */
 function sortControls(){const select=doc.getElementById('leader-sort');if(!select)return;const id=SORT_IDS.includes(select.value)?select.value:DEFAULT_SORT,[,key,dir]=sortSpec(id),opp=oppositeSort(id);
  for(const o of select.options){const off=!sortAvailable(o.value,{deviceRanks});if(!o.dataset.label)o.dataset.label=o.textContent;o.disabled=off;o.textContent=o.dataset.label+(off?(en?' (read the Universe on this device first)':' (내 기기 Universe 읽은 뒤)'):'');}
  const set=v=>{select.value=v;select.dispatchEvent(new Event('change',{bubbles:true}));};
  const box=el('div',undefined,{class:'chips','data-leaderboard-sort':id,role:'group','aria-label':en?'Sort order':'정렬 방향'});
  const turn=el('button',dir===1?(en?'↑ Ascending':'↑ 오름차순'):(en?'↓ Descending':'↓ 내림차순'),{type:'button','data-leaderboard-sort-dir':dir===1?'asc':'desc','aria-label':(en?'Sort direction: ':'정렬 방향: ')+(dir===1?(en?'ascending':'오름차순'):(en?'descending':'내림차순'))+(opp?(en?' (switch)':' (바꾸기)'):'')});
  if(opp)turn.onclick=()=>set(opp);else turn.disabled=true;
  const reset=el('button',en?'Default sort (QGV high first)':'기본 정렬(QGV 높은 순)',{type:'button','data-leaderboard-sort-reset':''});if(id===DEFAULT_SORT)reset.disabled=true;else reset.onclick=()=>set(DEFAULT_SORT);
  box.append(el('span',(en?'Sort: ':'정렬: ')+(sortLabel(id,en)||id),{class:'small'}),turn,reset);
  if(key==='cap'&&!sortAvailable(id,{deviceRanks}))box.append(el('span',en?'Market cap needs the Universe read on this device; all rows are — until then.':'시가총액은 내 기기 Universe를 읽어야 합니다. 그 전에는 모두 —입니다.',{class:'small','data-leaderboard-sort-na':'cap'}));
  box.append(el('span',en?'NA is last in both directions; the rank number stays the '+rankWord+'.':'NA는 양방향 모두 맨 뒤 · 순위 번호는 '+rankWord+' 그대로',{class:'small'}));box.append(el('span',en?'Choose the sort key in the 2.1.3 row (Sort).':'정렬 기준은 2.1.3 줄의 "정렬" 상자에서 고릅니다.',{class:'small','data-fn-hint':'2.1.2'}));sSort.append(box);}
 // Exploration filter: only with v2 scores (not in the v1 profile preview). Counts are over the rows the other filters left.
 const ex=S&&EXPLORE_IDS.includes(explore)?explore:'all',rows=ex==='all'?all:all.filter(r=>exploreOf(r)===ex);
 if(S){const counts={all:all.length,ranked:0,qg:0,partial:0,check:0};for(const r of all)counts[exploreOf(r)]++;
  const group=el('div',undefined,{class:'chips explore-filter',role:'group','aria-label':en?'Explore by QGV availability':'QGV 산출 여부로 보기','data-leaderboard-explore':ex});
  for(const[id,ko,enl]of EXPLORE){const b=el('button',(id==='ranked'&&personal?(en?'Personal preset rank':'개인 프리셋 순위'):(en?enl:ko))+' '+counts[id],{type:'button','data-leaderboard-explore-option':id,'aria-pressed':String(ex===id)});b.onclick=()=>onView({explore:id});group.append(b);}
  sState.append(group);
  // D11: no official rank yet (no V on this device) -> say so and point to the QG 참고 목록; it is never shown as the official ranking.
  if(!Object.values(S.rows||{}).some(r=>Number.isInteger(r.rank))){const[head,link]=qgvScores().NO_OFFICIAL_RANK[en?1:0].split(' · '),txt=S.priced_codes?(en?'No official QGV ranking: no company has a V on this device':'공식 QGV 순위 없음: 이 기기에서 V가 산출된 기업이 없습니다'):head,
   note=el('p',txt+' · ',{class:'small fn-alert','data-leaderboard-official':S.priced_codes?'NO_V':'BEFORE_PRICE'}),go=el('button',link,{type:'button','data-leaderboard-qg-open':''});go.onclick=()=>onView({explore:'qg'});note.append(go);sState.append(note);}
  if(ex==='ranked')sList.append(el('h3',personal?(en?'Personal preset rank (Universe basis · rows with V)':'개인 프리셋 순위 (Universe 기준 · V 산출 기업)'):(en?'Official QGV ranking (rows with V)':'공식 QGV 순위 (V 산출 기업)'),{'data-leaderboard-list-title':'RANKED',...(prov?QS.provenanceAttrs(prov):{})}));
  if(ex==='qg'){sList.append(el('h3',qgvScores().QG_REFERENCE_LABEL[en?1:0],{'data-leaderboard-list-title':'QG_REFERENCE'}),el('p',en?'Totals from Q·G only (V not applicable or not computed on this device). Ordered by the same total, apart from the official QGV ranking; no official rank number.':'Q·G만으로 낸 종합점수입니다(V 해당 없음 또는 이 기기에서 미산출). 같은 종합점수 순서이지만 공식 QGV 순위와 섞지 않으며 공식 순위 번호가 없습니다.',{class:'small','data-leaderboard-explore-note':'qg'}));}
  if(ex==='partial')sList.append(el('p',en?'These companies have only some axes (e.g. Q·G). They have no QGV total, so they are not in the QGV total order and have no rank.':'이 기업들은 일부 축(예: Q·G)만 산출되어 QGV 종합 점수가 없습니다. QGV 종합 순서에 넣지 않으며 순위가 없습니다.',{class:'small','data-leaderboard-explore-note':'partial'}));
  if(ex==='check')sList.append(el('p',en?'No axis could be calculated for these companies. Open a company to see why.':'이 기업들은 어느 축도 산출되지 않았습니다. 기업을 열면 이유를 볼 수 있습니다.',{class:'small','data-leaderboard-explore-note':'check'}));
  // Three different scopes, never claimed to be the same: the public analysis population, the ranked screen identities, the shown rows.
  const pop=populationOf(publicScreens),rankable=all.filter(r=>r.score&&Number.isInteger(r.score.rank)).length;
  // D12 extra attributes: evaluated = Universe securities of the official result (one row per security), target-in-universe and
  // outside = the TARGET split (17 + 2 for the 19 TARGET identities); '' without the official split.
  const offAttrs=off?{'data-evaluated':String(off.evaluated),'data-target-in-universe':String(off.target_in_universe.length),'data-outside-universe':String(off.outside.length)}:{'data-evaluated':'','data-target-in-universe':'','data-outside-universe':''};
  sList.append(el('p',(en?'Analysis population ':'분석 모집단 ')+(pop===null?'—':pop)+(en?' (public SEC records, percentile peers)':'개 (공개 SEC 기록 · 백분위 비교 대상)')+' · '+(personal?(en?'personal preset rank ':'개인 프리셋 순위 '):(en?'officially ranked ':'공식 순위 '))+rankable+(en?' of the '+all.length+' screen companies':'개 (이 화면 '+all.length+'개 기업 중)')+' · '+(en?'Q·G reference ':'QG 참고 ')+counts.qg+(en?'':'개')+' · '+(en?'shown ':'표시 ')+rows.length+(en?'':'개')+(ready?' · '+(en?'device cap subset ':'기기 시총 부분집합 ')+deviceRanks.verified_count+(en?' verified rows':'개 검증 행'):''),{class:'small','data-leaderboard-counts':'','data-population':pop===null?'':String(pop),'data-rankable':String(rankable),'data-qg-reference':String(counts.qg),'data-shown':String(rows.length),...offAttrs}));
  sortControls();}
 else for(const s of [sState,sSort])s.append(el('p',en?'Available in the QGV v2 views (Default · My device); the v1 profile preview has no calculation states or rank order.':'QGV v2 보기(기본 · 내 기기)에서 씁니다. v1 프로필 미리보기에는 산출 상태와 순위 순서가 없습니다.',{class:'small','data-fn-na':s.getAttribute('data-fn')}));
 // 2.1.4: the periods the owner named, each 미산출 (a return needs prices; prices are used on this device only and no return column exists yet).
 {const chips=el('div',undefined,{class:'chips fn-periods',role:'list','aria-label':en?'Return periods':'수익률 기간'});for(const p of PERIODS)chips.append(el('span',p+' · '+(en?'not calculated':'미산출'),{class:'badge fn-unconnected',role:'listitem','data-period':p,'data-period-state':'NOT_AVAILABLE'}));
  sPeriod.insertBefore(chips,sPeriod.children[1]||null);sPeriod.insertBefore(el('p',en?'Returns come from prices, so they are computed on this device only (prices are never published). The period column is not connected yet: price not connected.':'수익률은 가격으로 계산하므로 이 기기에서만 계산합니다(가격은 게시하지 않음). 기간 열은 아직 연결되지 않았습니다 · 가격 미연결.',{class:'small','data-fn-na':'2.1.4'}),chips.nextSibling);}
 // Footnote scope (D12, owner decision 2026-10-19; was D3 TARGET-only): the official rank is assigned over the Universe rows of the
 // ONE official result (S.official: every Universe code of the published sec-qgv2.json once; a TARGET in the Universe is that
 // code's row); ranked = the official D11 ranking (rows with V), the QG 참고 목록 apart; TARGET outside the Universe are listed
 // apart and never ranked; never over `all` (the rows the search/group/interest/TARGET filters leave). Without the split (no
 // file): every row of S. '—' without v2 scores.
 const scoped=S&&S.rows?Object.values(S.rows):null,scope={base:off?off.evaluated:scoped?scoped.length:'—',ranked:off?off.ranked:scoped?scoped.filter(r=>Number.isInteger(r.rank)).length:'—',outside:off?off.outside.length:0};
 // '포트폴리오 내 순위' (D12, CENTRAL_V §10-3): the same official order reduced to the TARGET rows in the Universe. Shown only with
 // the TARGET filter, always under that name and never in the rank column.
 const portfolioRank=new Map();if(targetOnly&&off&&S&&S.rows){off.target_in_universe.map(x=>S.rows[x.company_id]).filter(r=>r&&Number.isInteger(r.rank)).sort((a,b)=>a.rank-b.rank).forEach((r,i)=>portfolioRank.set(r.company_id,i+1));}
 const wrap=el('div',undefined,{class:'table-wrap'}),table=el('table',undefined,{'data-leaderboard-table':''}),head=el('tr'),body=el('tbody'),thead=el('thead');const narrow=Boolean(doc.defaultView&&doc.defaultView.matchMedia&&doc.defaultView.matchMedia(NARROW).matches),cols=COLUMNS.filter(c=>!(narrow&&c[3]));
 for(const[id,ko,enl]of cols)head.append(el('th',en?enl:ko,{scope:'col','data-leaderboard-col':id}));thead.append(head);table.setAttribute('data-leaderboard-layout',narrow?'narrow':'wide');
 for(const r of rows){const tr=el('tr',undefined,{'data-leaderboard-row':r.company_id});if(view!=='profile')mark(tr,r.score||null);const link=el('a',r.ticker,{href:'#company/'+encodeURIComponent(r.company_id)}),company=el('td');if(globalThis.CompanyLogos)company.append(globalThis.CompanyLogos.node(doc,r.ticker,20));company.append(link);
  // KR-NAMES: display-only company name from the caller's name lookup (company-names-ko.json); never a sort key or score input.
  {const nm=typeof nameOf==='function'?nameOf(r.company_id):null;if(typeof nm==='string'&&nm)company.append(el('span',' '+nm,{class:'small','data-leaderboard-name':''}));}
  if(r.m3.rank!==null)company.append(el('span',' · M3 #'+r.m3.rank+(r.m3.quality==='MISMATCH'?(en?' (mismatch)':' (불일치)'):'')+(r.m3.group_id?(en?' · class sum':' · 종류 합산'):''),{class:'badge','data-leaderboard-m3-rank':String(r.m3.rank),title:M3_LABEL[en?1:0]}));
  else company.append(el('span',' · '+(ready?'M3 — · '+r.m3.reason_codes.join(' / '):'—'),{class:'small','data-leaderboard-m3':'NOT_AVAILABLE','data-reason':r.m3.reason_codes.join(' ')}));
  // Q·G·V detail: the v2 summary with its flags (or the v2 NOT_AVAILABLE reason); in the profile view the v1 PREVIEW Q/G.
  const sc=view!=='profile'?r.score:null,detail=[],group=sc?exploreOf(r):null;
  if(sc){const p=sc.primary;const has=p.state!=='NOT_AVAILABLE'||p.q!==null||p.g!==null;detail.push(el('span',has?qgvScores().summaryText(p,en):qgvScores().naText(p,en),{class:'small','data-leaderboard-qgv2':has?'':'NOT_AVAILABLE'}));
   if(has)for(const f of qgvScores().flagText(p.flags,en,p))detail.push(el('span',' '+f,{class:'badge STALE','data-qgv2-flag':''}));
   // Data states of the row (자료 미확보 / 일부 자료 부족 / 가격 입력 필요 / 오래된 자료 / 해당 없음 / ...), in words.
   const st=p.coverage&&Array.isArray(p.coverage.states)?p.coverage.states:[];if(st.length)detail.push(el('div',(en?'Data: ':'자료 상태: ')+st.map(x=>qgvScores().stateText(x,en)).join(' · '),{class:'small','data-leaderboard-states':st.join(' ')}));}
  else if(view==='profile'&&(r.q!==null||r.g!==null))detail.push(el('span',' Q '+show(r.q)+' · G '+show(r.g)+(r.partial?(en?' (partial)':' (부분)'):'')+(r.factors?(en?' · factors ':' · 요인 ')+r.factors:'')+(weights?' · PREVIEW':''),{class:'small','data-leaderboard-qg':''}));
  else detail.push(doc.createTextNode('—'));
  const earningsText=r.earnings_status==='CONFIRMED'?(en?'Confirmed':'확인'):(r.next_window?r.next_window+(en?' (est.)':' (예상)'):'—');
  // QGV total: the v2 total, or — (NOT_AVAILABLE is never shown as 0).
  const total=sc&&typeof sc.primary.total==='number'&&Number.isFinite(sc.primary.total)?sc.primary.total:null,qgv=el('td',undefined,{'data-leaderboard-qgv-cell':'','data-sort-value':total===null||group==='qg'?'':String(total)});
  qgv.append(total===null?el('span','—',{'data-leaderboard-total':'NOT_AVAILABLE'}):el('b',show(total),{class:'num','data-leaderboard-total':show(total)}));
  {const bars=sc&&doc.createElementNS?qgvBars(doc,sc.primary):null;if(bars)qgv.append(bars);}
  // A row without a device rank says so next to the — total (any width): partial axes are shown, but outside the QGV total order.
  let unranked=null;if(group==='partial'&&sc.rank===null){const p=sc.primary,axes=[['Q',p.q],['G',p.g],['V',p.v]].filter(([,v])=>typeof v==='number'&&Number.isFinite(v)).map(([a,v])=>a+' '+show(v)).join(' · ');
   unranked=el('span',(p.reference_only?(en?'Reference ranking':'참고 순위'):(en?'Not in the QGV total order':'QGV 종합 순위 밖'))+(axes?' · '+axes:''),{class:'badge partial','data-leaderboard-unranked':'PARTIAL_AXES'});}
  else if(group==='qg'){const ref=sc.qg_reference||qgvScores().qgReference(sc.primary)||{};
   unranked=el('span',qgvScores().QG_REFERENCE_LABEL[en?1:0]+(ref.order?' · '+(en?'#':'')+ref.order+(en?'':'번'):'')+' · '+(en?'not an official rank':'공식 순위 아님')+(ref.reason?' · '+qgvScores().reasonText(ref.reason,en):''),{class:'badge partial','data-leaderboard-unranked':'QG_REFERENCE','data-qg-order':ref.order?String(ref.order):'','data-qg-reason':ref.reason||''});}
  else if(group==='check')unranked=el('span',en?'Check data':'자료 확인 필요',{class:'badge check-data','data-leaderboard-unranked':'CHECK_DATA'});
  const rank=el('td',sc&&sc.rank!==null?String(sc.rank):'—',sc&&sc.rank!==null?{'data-leaderboard-rank':String(sc.rank),'data-sort-value':String(sc.rank)}:{'data-sort-value':''});
  if(portfolioRank.has(r.company_id))company.append(el('span',' · '+qgvScores().PORTFOLIO_RANK_LABEL[en?1:0]+' '+portfolioRank.get(r.company_id),{class:'badge','data-leaderboard-portfolio-rank':String(portfolioRank.get(r.company_id))}));
  if(narrow){// Phone: one button per row opens Q·G·V and earnings under the total (keyboard/touch; no hover-only control).
   const detailId='lb-detail-'+r.company_id,open=OPEN.has(r.company_id),toggle=el('button',en?'Details':'상세',{type:'button',class:'lb-toggle','aria-expanded':String(open),'aria-controls':detailId,'aria-label':r.ticker+(en?' Q·G·V details':' Q·G·V 상세')});
   const more=el('div',undefined,{id:detailId,class:'lb-detail small','data-leaderboard-detail':''});more.append(...detail,el('div',(en?'Earnings ':'실적 ')+earningsText,{'data-earnings-qg-confirmation':r.earnings_status}));more.hidden=!open;
   toggle.onclick=()=>{const next=more.hidden;more.hidden=!next;toggle.setAttribute('aria-expanded',String(next));if(next)OPEN.add(r.company_id);else OPEN.delete(r.company_id);};
   qgv.append(doc.createTextNode(' '),toggle,...(unranked?[unranked]:[]),more);tr.append(rank,company,qgv);}
  else{if(unranked)qgv.append(unranked);const cell=el('td');cell.append(...detail);tr.append(rank,company,qgv,cell,el('td',earningsText,{'data-earnings-qg-confirmation':r.earnings_status}));}
  body.append(tr);}
 if(!rows.length){const tr=el('tr');tr.append(el('td',ex!=='all'&&all.length?(en?'No company in this view.':'이 보기에 해당하는 기업이 없습니다.'):(en?'No matching companies.':'일치하는 기업이 없습니다.'),{colspan:String(cols.length)}));body.append(tr);}
 table.append(thead,body);wrap.append(table);sList.append(wrap,el('p',off?(en?'— = NOT_AVAILABLE. Rank and QGV are QGV v2 PROVISIONAL values computed in this device’s memory. '+(personal?'The rank is a personal preset rank over the Universe (not the official QGV rank): among the ':'The rank is the official QGV rank over the Universe: among the ')+scope.ranked+' rows with a V score of the '+scope.base+' Universe securities of the published sec-qgv2.json (a TARGET company in the Universe is the same row). Filters (search, group, interest, TARGET) only hide rows and never re-rank. The '+scope.outside+' TARGET companies outside the Universe are listed apart and are not ranked. A company whose QGV v2 cannot be computed has rank — and is listed last; it is never shown as 0. Earnings are marked confirmed only after the disclosed quarter is reflected in Q/G; otherwise the filing window is an estimate. M3 rank is a personal reference from the Universe sheet read on this device (RAM only, not an official rank).':'— = NOT_AVAILABLE. 순위·QGV는 이 기기 메모리에서 계산한 QGV v2 PROVISIONAL 값입니다. 순위는 '+(personal?'개인 프리셋 순위(Universe 기준 · 공식 QGV 순위 아님)':'Universe 공식 QGV 순위')+'로, 공개 sec-qgv2.json의 Universe '+scope.base+'개 종목 중 V가 산출된 '+scope.ranked+'개 안의 순위입니다(Universe 안의 TARGET 기업은 같은 행). 필터(검색·그룹·관심·TARGET)는 행만 숨기며 순위를 다시 매기지 않습니다. Universe 밖 TARGET '+scope.outside+'개는 따로 보여 주며 순위에 넣지 않습니다. QGV v2를 계산할 수 없는 기업은 순위 —로 맨 뒤에 두며 0으로 표시하지 않습니다. 실적은 공시 분기가 Q·G에 반영됐을 때만 확인으로 표시하며, 그 외 시기는 제출 패턴의 예상입니다. M3 순위는 내 기기에서 읽은 Universe 시트 기준 개인 참고값(메모리 전용·공식 순위 아님)입니다.'):(en?'— = NOT_AVAILABLE. Rank and QGV are QGV v2 PROVISIONAL values computed in this device’s memory, ranked among the '+scope.ranked+' ranked rows of the '+scope.base+' screen companies (the published sec-qgv2.json is not loaded, so no Universe rank; filters only hide rows). A company whose QGV v2 cannot be computed has rank — and is listed last; it is never shown as 0. M3 rank is a personal reference from the Universe sheet read on this device (RAM only, not an official rank).':'— = NOT_AVAILABLE. 순위·QGV는 이 기기 메모리에서 계산한 QGV v2 PROVISIONAL 값이며 이 화면 '+scope.base+'개 기업 중 순위가 매겨진 '+scope.ranked+'개 안의 순위입니다(공개 sec-qgv2.json이 없어 Universe 순위 아님 · 필터는 행만 숨김). QGV v2를 계산할 수 없는 기업은 순위 —로 맨 뒤에 두며 0으로 표시하지 않습니다. M3 순위는 내 기기에서 읽은 Universe 시트 기준 개인 참고값(메모리 전용·공식 순위 아님)입니다.'),{class:'small','data-leaderboard-rank-scope':'',...(prov?QS.provenanceAttrs(prov):{}),'data-rank-population':off?'UNIVERSE':'IDENTITIES','data-rank-base':String(scope.base),'data-ranked':String(scope.ranked),'data-outside-universe':String(scope.outside)}));
 sPeriod.append(el('p',(en?'Not shown (no data yet): ':'자료 미제공으로 표에서 뺀 열: ')+UNCONNECTED.map(c=>en?c[2]:c[1]).join(' · ')+(en?'. They need prices or inputs that are not connected yet, so every value would be —.':'. 가격 또는 아직 연결되지 않은 입력이 필요해 모든 값이 —입니다.'),{class:'small','data-leaderboard-unconnected':''}));
 // D12: TARGET identities outside the Universe of the published sec-qgv2.json, in their own labelled list after the same filters:
 // their evaluation (or reference / NA reason) is shown, but they are never in the table, the rank population or the candidates.
 if(off){const box=el('section',undefined,{'data-leaderboard-outside':String(outside.length)}),QS2=qgvScores();box.append(el('h3',QS2.OUTSIDE_UNIVERSE_LABEL[en?1:0],{'data-leaderboard-list-title':'OUTSIDE_UNIVERSE'}),
   el('p',en?'TARGET companies with no Universe code in the published sec-qgv2.json. Their result is shown for reference; they get no official rank and are not candidates.':'공개 sec-qgv2.json의 Universe 코드에 없는 TARGET 기업입니다. 결과는 참고로만 보여 주며 공식 순위와 후보에 넣지 않습니다.',{class:'small'}));
  if(outside.length){const ul=el('ul',undefined,{class:'outside-list'});for(const c of outside){const x=S&&S.rows?S.rows[c.company_id]:null,p=x?x.primary:null,li=el('li',undefined,{'data-leaderboard-outside-row':c.company_id});mark(li,x);const nm=typeof nameOf==='function'?nameOf(c.company_id):null;
    li.append(el('a',c.ticker,{href:'#company/'+encodeURIComponent(c.company_id)}));if(nm||c.name)li.append(el('span',' '+(nm||c.name),{class:'small'}));
    const has=!!p&&(p.state!=='NOT_AVAILABLE'||p.q!==null||p.g!==null);li.append(el('span',' · '+(p?(has?QS2.summaryText(p,en):QS2.naText(p,en)):'—'),{class:'small','data-leaderboard-outside-state':p?(p.reference_only?'REFERENCE':has?'SCORED':'NOT_AVAILABLE'):'NOT_AVAILABLE'}),el('span',' '+(en?'Not ranked':'순위 없음'),{class:'badge partial','data-leaderboard-unranked':'OUTSIDE_UNIVERSE'}));ul.append(li);}box.append(ul);}
  else box.append(el('p',en?'None under the current filters.':'현재 필터에 해당하는 기업이 없습니다.',{class:'small'}));
  sList.append(box);}
 // D12 model portfolio N10 / N15 / N20 on the OFFICIAL default profile (balanced, gate on, official weights; `model` from the app:
 // QgvScores.officialModel over the same inputs and quotes) and the approved eligibility; never the device's S06 preset. Without
 // `model` it is computed here only when S itself is that profile. Device RAM only, never stored or sent; not affected by the
 // screen filters; not an order or advice.
 if(S&&off){const QS2=qgvScores(),isOfficial=S.profile&&S.profile.preset==='balanced'&&S.profile.gate===true,M=model!==undefined?model:isOfficial&&QS2.modelPortfolios?QS2.modelPortfolios(S,publicScreens['sec-qgv2.json']):null,box=el('details',undefined,{'data-model-portfolio':M&&M.sets.N20.selected.length?'READY':'NO_OFFICIAL_RANK'});
  box.append(el('summary',en?'Model portfolio N10 · N15 · N20 (N15 primary, N10/N20 sensitivity) · official evaluation':'모델 포트폴리오 N10·N15·N20 (N15 주검정 · N10·N20 민감도) · 공식 평가 기준'));
  // Provenance of the N sets: always the official default profile (officialModel), so they keep saying 공식 가중치; under a personal
  // S06 preset the leaderboard order above is a personal preset rank and can differ from this official order.
  {const mp=QS2.provenance?QS2.provenance({profile:M&&M.official_profile?M.official_profile:null,priced:S.priced_codes>0}):null;if(mp)box.append(el('p',QS2.provenanceText(mp,en)+(personal?(en?' · the S06 order above is a personal preset rank and can differ from this official order':' · 위 S06 순서는 개인 프리셋 순위라 이 공식 순서와 다를 수 있습니다'):''),{class:'small','data-model-provenance':personal?'S06_PERSONAL':'S06_OFFICIAL',...QS2.provenanceAttrs(mp)}));}
  box.append(el('p',(en?'Eligibility (approved): ':'후보 자격(승인): ')+QS2.MODEL_RULES.map(k=>QS2.MODEL_LABEL[k][en?1:0]).join(' · ')+(en?'. Equal weight, official rank order. Computed in this device’s memory; not stored or sent; not an order.':'. 공식 순위 순 · 동일 비중. 이 기기 메모리에서 계산 · 저장·전송 없음 · 매매 지시 아님.'),{class:'small','data-model-rules':QS2.MODEL_RULES.join(' ')}));
  if(M&&M.sets.N20.selected.length){const x=M.excluded,u=M.unknown;
   box.append(el('p',(en?'Excluded: ':'제외: ')+[['AXES_50',en?'axis 50%':'축 50%'],['VALUE_TRAP_GATE',en?'value-trap gate':'가치 함정 관문'],['FINANCIAL_SAFETY',en?'financial safety':'재무 안전 미달'],['FINANCIAL_SAFETY_NA',en?'financial safety NA':'재무 안전 지표 NA'],['SUBGROUP_MAX_4',en?'subgroup cap':'하위 묶음 상한']].map(([k,l])=>l+' '+x[k]).join(' · ')+' · '+(en?'subgroup unknown (cap not applied, provisional · open) ':'하위 묶음 미정(상한 미적용 · 잠정 · 결정 필요) ')+u.subgroup,{class:'small','data-model-excluded':JSON.stringify(x),'data-model-unknown':JSON.stringify(u)}));
   const t=el('table',undefined,{'data-model-table':''}),h=el('tr');for(const label of [en?'Official rank':'공식 순위',en?'Company':'기업','QGV',en?'Subgroup':'하위 묶음',en?'In':'포함'])h.append(el('th',label,{scope:'col'}));const tb=el('tbody');
   const union=[...new Map(QS2.MODEL_NS.flatMap(n=>M.sets['N'+n].selected).sort((a,b)=>a.rank-b.rank).map(e=>[e.company_id,e])).values()];
   for(const e of union){const tr=el('tr',undefined,{'data-model-row':e.company_id,'data-model-rank':String(e.rank),'data-model-in':QS2.MODEL_NS.filter(n=>M.sets['N'+n].selected.some(y=>y.company_id===e.company_id)).map(n=>'N'+n).join(' ')});
    const a=el('td');a.append(el('a',e.ticker,{href:'#company/'+encodeURIComponent(e.company_id)}));tr.append(el('td',String(e.rank)),a,el('td',show(e.total)),el('td',e.subgroup||(en?'unknown':'미정')));
    tr.append(el('td',tr.getAttribute('data-model-in'),{'data-model-set-cell':''}));tb.append(tr);}
   const th=el('thead');th.append(h);t.append(th,tb);const w=el('div',undefined,{class:'table-wrap'});w.append(t);box.append(w);
   box.append(el('p',QS2.MODEL_NS.map(n=>'N'+n+' '+M.sets['N'+n].selected.length+'/'+n+(en?' · each ':' · 각 ')+(100/n).toFixed(2)+'%'+(M.sets['N'+n].complete?'':(en?' (not enough eligible rows)':' (자격 행 부족)'))).join(' · ')+' · '+(en?'official default profile ':'공식 기본 프로필 ')+(M.profile_id||'—')+(S.profile&&M.profile_id&&S.profile.id!==M.profile_id?(en?' (the S06 profile on this device, '+S.profile.id+', does not change this selection)':' (이 기기 S06 프로필 '+S.profile.id+'은 이 선정에 영향 없음)'):''),{class:'small','data-model-profile':M.profile_id||'','data-model-profile-differs':String(!!(S.profile&&M.profile_id&&S.profile.id!==M.profile_id)),'data-model-counts':QS2.MODEL_NS.map(n=>'N'+n+'='+M.sets['N'+n].selected.length).join(' ')}));
   box.append(modelChecks(M,QS2,en,el));}
  else box.append(el('p',en?'No official QGV ranking yet (no V on this device): no selection.':'공식 QGV 순위가 없어(이 기기에서 V 미산출) 선정하지 않습니다.',{class:'small'}));
  box.append(el('p',en?'Not applied · owner decision needed: the 10-K number check, sector diversification beyond the subgroup and §16 caps (BT-14), one seat per issuer (recommendation), the sector group of rows whose subgroup is unknown. Core/general tier weights are the R-C (TARGET v1) rule: the N sets (R-B, equal weight) keep equal weight and show the tier weights as a check only.':'미적용 · 소유자 결정 필요: 10-K 숫자 대조 · 하위 묶음·16절 한도 밖의 업종 분산(BT-14) · 같은 발행사 한 자리(권장안) · 하위 묶음 미정 행의 업종 묶음. 핵심/일반 등급 비중은 R-C(TARGET v1) 규칙이라 N 세트(R-B · 동일 비중)는 동일 비중을 유지하고 등급 비중은 검사로만 보입니다.',{class:'small','data-model-not-applied':''}));
  sCand.append(box);}
 const stages=el('details',undefined,{'data-reeval-stages':''});stages.append(el('summary',en?'Re-evaluation signal stages':'재평가 신호 단계'));const list=el('ol');for(const[ko,enl]of STAGES)list.append(el('li',en?enl:ko));stages.append(list,el('p',en?'Price change, threshold and distance are shown once the signal is connected (NOT_AVAILABLE now).':'신호가 연결되면 가격 변화량·임계값·거리를 함께 보여 줍니다(현재 NOT_AVAILABLE).',{class:'small'}));sCand.append(stages);
 const actions=el('div',undefined,{class:'chips'});for(const label of [en?'Send selection to paper trading':'선택 종목 모의투자',en?'Send to backtest':'백테스트로 보내기']){const b=el('button',label,{type:'button',disabled:''});actions.append(b);}sCand.append(actions,el('p',en?'Paper trading and backtest are not connected yet.':'모의투자·백테스트는 아직 연결되지 않았습니다.',{class:'small'}));
 host.replaceChildren(card);return{shown:rows.length,explore:ex};}
return Object.freeze({COLUMNS,UNCONNECTED,NARROW,M3_LABEL,EXPLORE,SORTS,SORT_IDS,DEFAULT_SORT,FN,PERIODS,fnHeadHtml,filterNoteHtml,classificationOf,filterClassifications,classificationSummary,classificationFiltersHtml,mountClassificationFilters,sortLabel,sortOptions,oppositeSort,sortAvailable,sortRows,populationOf,rowsFor,modelChecks,mount});
});
