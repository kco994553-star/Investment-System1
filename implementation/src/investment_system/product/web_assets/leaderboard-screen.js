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
/* Exploration filter (FE-MISSING-2, owner instruction 2026-10-17), from QgvScores.exploreGroup of each row: 'ranked' = a QGV
   total and a device rank; 'partial' = some axis score (e.g. Q·G only) but no total, so no rank and never in the ranked order;
   'check' = no axis score (data to check). Ranks stay the ones over all identities; the filter only hides rows. */
const EXPLORE=[['all','전체','All'],['ranked','QGV 산출 가능','QGV available'],['partial','일부 축만 가능','Some axes only'],['check','자료 확인 필요','Check data']];
const EXPLORE_OF={RANKED:'ranked',PARTIAL_AXES:'partial',CHECK_DATA:'check'},EXPLORE_IDS=EXPLORE.map(e=>e[0]);
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
   ranks. Returns a new array (input untouched). */
function sortRows(rows,S,id,{deviceRanks=null}={}){
 if(['ticker','name','favorites'].includes(id))return rows;
 const[,key,dir]=sortSpec(id),num=v=>typeof v==='number'&&Number.isFinite(v)?v:null,score=r=>S&&S.rows?S.rows[r.company_id]:null;
 const value=r=>{const x=score(r),p=x?x.primary:null;
  if(key==='qgv')return x&&Number.isInteger(x.rank)?num(p.total):null;if(['q','g','v'].includes(key))return p?num(p[key]):null;
  if(key==='ticker'||key==='name')return typeof r[key]==='string'?r[key]:null;
  if(key==='asof'){const t=p&&p.coverage&&p.coverage.source?Date.parse(p.coverage.source.acquired_at):NaN;return Number.isFinite(t)?t:null;}
  if(key==='cap'){const m=m3For(deviceRanks,r);return Number.isInteger(m.rank)?m.rank:null;}return null;};
 const tie=key==='cap'?(a,b)=>(a.company_id<b.company_id?-1:a.company_id>b.company_id?1:0):(a,b)=>String(a.ticker).localeCompare(String(b.ticker));
 // Market cap: the M3 rank is 1 = largest, so 'largest first' is rank ascending.
 const m=key==='cap'?-dir:dir,keyed=rows.map(r=>({r,v:value(r)}));
 keyed.sort((a,b)=>(a.v===null)-(b.v===null)||(a.v!==null&&b.v!==null?(typeof a.v==='string'?a.v.localeCompare(b.v):a.v<b.v?-1:a.v>b.v?1:0)*m:0)||tie(a.r,b.r));
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
function mount(host,identities,{publicScreens={},locale,view='default',profiles=[],profileId=null,onView=()=>{},engine=globalThis.EnginePreview,filings=globalThis.PublicScreens,deviceRanks=null,scores=null,explore='all',nameOf=null}={}){
 if(!host)return;const doc=host.ownerDocument,en=locale==='en-US',el=(tag,text,attrs={})=>{const n=doc.createElement(tag);if(text!==undefined)n.textContent=text;for(const[k,v]of Object.entries(attrs))n.setAttribute(k,v);return n;};
 const card=el('section',undefined,{class:'card','data-leaderboard-screen':view});
 card.append(el('div',undefined,{class:'chips data-badges'}));const QS=qgvScores(),S=view!=='profile'&&QS?(scores||QS.compute({identities,publicScreens})):null;
 const v2AsOf=(S||scores)?.v2_as_of||null,v1AsOf=publicScreens['sec-qg-factors.json']?.as_of||null;
 // Score time = sec-qgv2.json as_of (the v2 input). sec-qg-factors.json is only the v1 PREVIEW input of the profile view.
 card.lastChild.append(el('span',en?'US top 500 · target scope':'미국 상위 500 · 목표 범위',{class:'badge'}),...(S?[el('span',QS.basisText(S,en),{class:'badge','data-scoring-default':'v2','data-scoring-basis-label':S.basis.label})]:[]),el('span',(en?'Score as of ':'점수 기준 ')+(v2AsOf||'NOT_AVAILABLE'),{class:'badge','data-score-as-of':v2AsOf?'v2':'NOT_AVAILABLE'}),...(view==='profile'?[el('span',(en?'v1 PREVIEW input as of ':'v1 미리보기 입력 기준 ')+(v1AsOf||'NOT_AVAILABLE'),{class:'badge','data-v1-preview-as-of':''})]:[]));
 const ready=deviceRanks?.state==='READY',m3Note=ready?(deviceRanks.status==='COMPLETE'?(en?'verified rows · complete':'검증 행 · 완전'):(en?'verified rows only · partial':'검증 행만 · 부분'))+' · '+(en?'verified ':'검증 ')+deviceRanks.verified_count+(deviceRanks.config_status?' · '+deviceRanks.config_status:''):'NOT_AVAILABLE · '+(deviceRanks?.reason_codes?.join(' / ')||(en?'Universe not read on this device':'Universe 읽기 전'));
 card.lastChild.append(el('span',M3_LABEL[en?1:0]+' · '+m3Note,{class:'badge','data-leaderboard-m3-basis':ready?'READY':'NOT_AVAILABLE'}));
 const tabs=el('div',undefined,{class:'chips screen-tabs',role:'group'});for(const[id,label]of [['default',en?'Default':'기본'],['profile',en?'My profile (PREVIEW)':'내 프로필 기준(PREVIEW)'],['device',en?'My device (M3)':'내 기기 기준(M3)']]){const b=el('button',label,{type:'button','data-leaderboard-view':id,'aria-pressed':String(view===id)});b.onclick=()=>onView({view:id});tabs.append(b);}card.append(tabs);
 if(S){const p=S.profile,v2note=S.v2_state==='READY'?(en?p.name.name_en:p.name.name)+' · '+(en?'gate ':'관문 ')+(p.gate?(en?'on':'켬'):(en?'off':'끔'))+' · '+(en?'priced ':'가격 ')+S.priced_codes+(en?' (this device, RAM)':' (이 기기·메모리)'):(en?'v2 · NOT_AVAILABLE · ':'v2 · NOT_AVAILABLE · ')+(Array.isArray(S.v2_reason_text)?S.v2_reason_text[en?1:0]:S.v2_reason);
  card.lastChild.append(el('span',v2note,{class:'badge','data-qgv2-state':S.v2_state}));
  const presets=el('div',undefined,{class:'chips','data-qgv2-presets':'',role:'group','aria-label':en?'QGV v2 profile':'QGV v2 프로필'});
  for(const[id,pr]of Object.entries(qgvScores().presets())){const b=el('button',en?pr.name_en:pr.name,{type:'button','data-qgv2-preset':id,'aria-pressed':String(p.preset===id)});b.onclick=()=>onView({preset:id});presets.append(b);}
  const gate=el('label',en?' Value-trap gate':' 가치 함정 관문',{class:'small'}),box=el('input',undefined,{type:'checkbox','data-qgv2-gate':''});box.checked=p.gate;box.onchange=()=>onView({gate:box.checked});gate.prepend(box);presets.append(gate);card.append(presets);}
 let weights=null;if(view==='profile'){const select=el('select',undefined,{'data-leaderboard-profile':'','aria-label':en?'Profile':'프로필'});select.append(el('option',en?'Choose a saved profile':'저장한 프로필 선택',{value:''}));for(const p of profiles){const o=el('option',p.name,{value:p.id});if(p.id===profileId)o.selected=true;select.append(o);}select.onchange=()=>onView({view,profileId:select.value||null});card.append(select);
  const chosen=profiles.find(p=>p.id===profileId);if(chosen)weights=chosen.weights;card.append(el('p',(en?'v1 preview (not the official v2 score) · ':'v1 미리보기 (공식 v2 점수 아님) · ')+(chosen?(en?'PREVIEW · RAM only · Q/G recalculated with your profile; not mixed with official results':'PREVIEW · 메모리 전용 · 내 프로필로 Q/G 재계산, 공식 결과와 섞지 않음'):(en?'No saved profile selected. Create one in Strategy profile.':'선택한 프로필이 없습니다. 전략 프로필에서 만드세요.')),{class:'small','data-leaderboard-preview-note':''}));}
 if(view==='device'){card.append(el('p',en?'My device view reads your private Universe sheet in RAM. Open it below.':'내 기기 기준은 비공개 Universe 시트를 메모리에서 읽습니다. 아래에서 여세요.',{class:'small'}));}
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
  box.append(el('span',en?'NA is last in both directions; the rank number stays the official device rank.':'NA는 양방향 모두 맨 뒤 · 순위 번호는 공식 기기 순위 그대로',{class:'small'}));card.append(box);}
 // Exploration filter: only with v2 scores (not in the v1 profile preview). Counts are over the rows the other filters left.
 const ex=S&&EXPLORE_IDS.includes(explore)?explore:'all',rows=ex==='all'?all:all.filter(r=>exploreOf(r)===ex);
 if(S){const counts={all:all.length,ranked:0,partial:0,check:0};for(const r of all)counts[exploreOf(r)]++;
  const group=el('div',undefined,{class:'chips explore-filter',role:'group','aria-label':en?'Explore by QGV availability':'QGV 산출 여부로 보기','data-leaderboard-explore':ex});
  for(const[id,ko,enl]of EXPLORE){const b=el('button',(en?enl:ko)+' '+counts[id],{type:'button','data-leaderboard-explore-option':id,'aria-pressed':String(ex===id)});b.onclick=()=>onView({explore:id});group.append(b);}
  card.append(group);
  if(ex==='partial')card.append(el('p',en?'These companies have only some axes (e.g. Q·G). They have no QGV total, so they are not in the QGV total order and have no rank.':'이 기업들은 일부 축(예: Q·G)만 산출되어 QGV 종합 점수가 없습니다. QGV 종합 순서에 넣지 않으며 순위가 없습니다.',{class:'small','data-leaderboard-explore-note':'partial'}));
  if(ex==='check')card.append(el('p',en?'No axis could be calculated for these companies. Open a company to see why.':'이 기업들은 어느 축도 산출되지 않았습니다. 기업을 열면 이유를 볼 수 있습니다.',{class:'small','data-leaderboard-explore-note':'check'}));
  // Three different scopes, never claimed to be the same: the public analysis population, the ranked screen identities, the shown rows.
  const pop=populationOf(publicScreens),rankable=all.filter(r=>r.score&&Number.isInteger(r.score.rank)).length;
  card.append(el('p',(en?'Analysis population ':'분석 모집단 ')+(pop===null?'—':pop)+(en?' (public SEC records, percentile peers)':'개 (공개 SEC 기록 · 백분위 비교 대상)')+' · '+(en?'rankable ':'순위 가능 ')+rankable+(en?' of the '+all.length+' screen companies':'개 (이 화면 '+all.length+'개 기업 중)')+' · '+(en?'shown ':'표시 ')+rows.length+(en?'':'개')+(ready?' · '+(en?'device cap subset ':'기기 시총 부분집합 ')+deviceRanks.verified_count+(en?' verified rows':'개 검증 행'):''),{class:'small','data-leaderboard-counts':'','data-population':pop===null?'':String(pop),'data-rankable':String(rankable),'data-shown':String(rows.length)}));
  sortControls();}
 const wrap=el('div',undefined,{class:'table-wrap'}),table=el('table',undefined,{'data-leaderboard-table':''}),head=el('tr'),body=el('tbody'),thead=el('thead');const narrow=Boolean(doc.defaultView&&doc.defaultView.matchMedia&&doc.defaultView.matchMedia(NARROW).matches),cols=COLUMNS.filter(c=>!(narrow&&c[3]));
 for(const[id,ko,enl]of cols)head.append(el('th',en?enl:ko,{scope:'col','data-leaderboard-col':id}));thead.append(head);table.setAttribute('data-leaderboard-layout',narrow?'narrow':'wide');
 for(const r of rows){const tr=el('tr',undefined,{'data-leaderboard-row':r.company_id}),link=el('a',r.ticker,{href:'#company/'+encodeURIComponent(r.company_id)}),company=el('td');if(globalThis.CompanyLogos)company.append(globalThis.CompanyLogos.node(doc,r.ticker,20));company.append(link);
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
  const total=sc&&typeof sc.primary.total==='number'&&Number.isFinite(sc.primary.total)?sc.primary.total:null,qgv=el('td',undefined,{'data-leaderboard-qgv-cell':'','data-sort-value':total===null?'':String(total)});
  qgv.append(total===null?el('span','—',{'data-leaderboard-total':'NOT_AVAILABLE'}):el('b',show(total),{class:'num','data-leaderboard-total':show(total)}));
  // A row without a device rank says so next to the — total (any width): partial axes are shown, but outside the QGV total order.
  let unranked=null;if(group==='partial'&&sc.rank===null){const p=sc.primary,axes=[['Q',p.q],['G',p.g],['V',p.v]].filter(([,v])=>typeof v==='number'&&Number.isFinite(v)).map(([a,v])=>a+' '+show(v)).join(' · ');
   unranked=el('span',(p.reference_only?(en?'Reference ranking':'참고 순위'):(en?'Not in the QGV total order':'QGV 종합 순위 밖'))+(axes?' · '+axes:''),{class:'badge partial','data-leaderboard-unranked':'PARTIAL_AXES'});}
  else if(group==='check')unranked=el('span',en?'Check data':'자료 확인 필요',{class:'badge check-data','data-leaderboard-unranked':'CHECK_DATA'});
  const rank=el('td',sc&&sc.rank!==null?String(sc.rank):'—',sc&&sc.rank!==null?{'data-leaderboard-rank':String(sc.rank),'data-sort-value':String(sc.rank)}:{'data-sort-value':''});
  if(narrow){// Phone: one button per row opens Q·G·V and earnings under the total (keyboard/touch; no hover-only control).
   const detailId='lb-detail-'+r.company_id,open=OPEN.has(r.company_id),toggle=el('button',en?'Details':'상세',{type:'button',class:'lb-toggle','aria-expanded':String(open),'aria-controls':detailId,'aria-label':r.ticker+(en?' Q·G·V details':' Q·G·V 상세')});
   const more=el('div',undefined,{id:detailId,class:'lb-detail small','data-leaderboard-detail':''});more.append(...detail,el('div',(en?'Earnings ':'실적 ')+earningsText,{'data-earnings-qg-confirmation':r.earnings_status}));more.hidden=!open;
   toggle.onclick=()=>{const next=more.hidden;more.hidden=!next;toggle.setAttribute('aria-expanded',String(next));if(next)OPEN.add(r.company_id);else OPEN.delete(r.company_id);};
   qgv.append(doc.createTextNode(' '),toggle,...(unranked?[unranked]:[]),more);tr.append(rank,company,qgv);}
  else{if(unranked)qgv.append(unranked);const cell=el('td');cell.append(...detail);tr.append(rank,company,qgv,cell,el('td',earningsText,{'data-earnings-qg-confirmation':r.earnings_status}));}
  body.append(tr);}
 if(!rows.length){const tr=el('tr');tr.append(el('td',ex!=='all'&&all.length?(en?'No company in this view.':'이 보기에 해당하는 기업이 없습니다.'):(en?'No matching companies.':'일치하는 기업이 없습니다.'),{colspan:String(cols.length)}));body.append(tr);}
 table.append(thead,body);wrap.append(table);card.append(wrap,el('p',en?'— = NOT_AVAILABLE. Rank and QGV are QGV v2 PROVISIONAL values computed in this device’s memory, ranked over all 19 companies (filters only hide rows; not an official rank). A company whose QGV v2 cannot be computed has rank — and is listed last; it is never shown as 0. Earnings are marked confirmed only after the disclosed quarter is reflected in Q/G; otherwise the filing window is an estimate. M3 rank is a personal reference from the Universe sheet read on this device (RAM only, not an official rank).':'— = NOT_AVAILABLE. 순위·QGV는 이 기기 메모리에서 계산한 QGV v2 PROVISIONAL 값이며 19개 기업 전체 기준 순위입니다(필터는 행만 숨김 · 공식 순위 아님). QGV v2를 계산할 수 없는 기업은 순위 —로 맨 뒤에 두며 0으로 표시하지 않습니다. 실적은 공시 분기가 Q·G에 반영됐을 때만 확인으로 표시하며, 그 외 시기는 제출 패턴의 예상입니다. M3 순위는 내 기기에서 읽은 Universe 시트 기준 개인 참고값(메모리 전용·공식 순위 아님)입니다.',{class:'small'}),
  el('p',(en?'Not shown (no data yet): ':'자료 미제공으로 표에서 뺀 열: ')+UNCONNECTED.map(c=>en?c[2]:c[1]).join(' · ')+(en?'. They need prices or inputs that are not connected yet, so every value would be —.':'. 가격 또는 아직 연결되지 않은 입력이 필요해 모든 값이 —입니다.'),{class:'small','data-leaderboard-unconnected':''}));
 const stages=el('details',undefined,{'data-reeval-stages':''});stages.append(el('summary',en?'Re-evaluation signal stages':'재평가 신호 단계'));const list=el('ol');for(const[ko,enl]of STAGES)list.append(el('li',en?enl:ko));stages.append(list,el('p',en?'Price change, threshold and distance are shown once the signal is connected (NOT_AVAILABLE now).':'신호가 연결되면 가격 변화량·임계값·거리를 함께 보여 줍니다(현재 NOT_AVAILABLE).',{class:'small'}));card.append(stages);
 const actions=el('div',undefined,{class:'chips'});for(const label of [en?'Send selection to paper trading':'선택 종목 모의투자',en?'Send to backtest':'백테스트로 보내기']){const b=el('button',label,{type:'button',disabled:''});actions.append(b);}card.append(actions,el('p',en?'Paper trading and backtest are not connected yet.':'모의투자·백테스트는 아직 연결되지 않았습니다.',{class:'small'}));
 host.replaceChildren(card);return{shown:rows.length,explore:ex};}
return Object.freeze({COLUMNS,UNCONNECTED,NARROW,M3_LABEL,EXPLORE,SORTS,SORT_IDS,DEFAULT_SORT,sortLabel,sortOptions,oppositeSort,sortAvailable,sortRows,populationOf,rowsFor,mount});
});
