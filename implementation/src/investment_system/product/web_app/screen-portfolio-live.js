/* Feature 6 · 포트폴리오 (spec v1.0 6.1 세 가지 포트폴리오 · 6.2 · 6.3 보고 · 6.4 트리; menu 5 · route #/portfolio; boards Portfolio ·
   MPortfolio), the public layer of P2-6: the part that runs after IS2.ready. screen-portfolio.js draws the first-paint skeleton
   (head, the notice MODEL_NOT_CONFIRMED above everything, sections 5-1 … 5-4 with a loading line) and hands its four slots to
   IS2.portfolioLive.screen(route, {slots}) from this file (loader.js LOAD_ORDER, after the layer); nothing here touches the layer
   while the file loads. Public + private two layers (FUNCTION_STATUS 1-3 row 6.1, owner 2026-10-31): the public part works with
   no private data at all and never waits for, reads or changes with the private panel.
   - 모델 후보 (6.1.2 · 6.1.3, public, price-free): IS2.qgv.page() (the one shared central page, official profile, no setProfile)
     and IS2.qgv.model(page) (QgvScores.officialModel projected by qgv.js: official default profile, gate on). The N15 set is the
     primary set for TARGET v1 / R-C; each row shows its official rank, ticker, sector group, tier (핵심 / 일반) and target weight
     from the N15 tier check (rule TIERS_RC_20261014, owner decision 2026-10-14: core 5 x 8% + general 10 x 6%). The tier check
     never changes the selection (applied_to_selection false); its status (PASS / UNVERIFIED / FAIL / CORE_SHORT / INCOMPLETE) is
     shown in Korean with its code, with the summed weight, the largest group and the unknown-group share. Set completeness and
     shortfall (never filled, never re-weighted), the exclusion counts and the provisional subgroup rule as QGV 1.1.7 words them.
     No model (no publication, the score file is not the publication's input): the page's own reason, never an empty table.
     A page that is not READY (NO_DATA / READ_FAILED / DATA_FORMAT_NEWER): its reason (IS2.qgv.reasonText), never zeros.
   - 적용 버전·기준일 (6.1.4): the score refresh time (as_of, UTC), calc_version, the central V basis label and its price basis day,
     publication time and id (from the page, never typed here), STALE when the layer says so, the rank wording (rankLabel), the
     official profile id, the tier rule id, the IEX attribution with its terms link.
   - TARGET v1 상태: public words only (no published confirmed copy yet; window 2026-11-09 ~ 11-15; drafting is the TARGET v1
     builder detail screen, which keeps its own V source until the 11/16 PR, DC-31). This screen never runs the builder and never
     reads the device's TARGET store. TARGET v0 (catalog 19) is neither used nor shown.
   - 실제 (내 것): one IS2.parts.privatePanel (portfolio-actual) that stays in its first state (비공개 기능 준비 중): nothing is
     requested or stored; holdings live only on this device and the owner's sheet.
   - 모의: one honest line (paper-trading records come in a later P2-6 step). 5-2 · 5-3 · 5-4: 다음 단계 lines.
   - States: loading (skeleton line, then 불러오는 중 · 모델 후보), empty (no model with its reason), error (loader, page failed),
     partial (the model card fails, the other cards stay). No price request and no price button, no storage, no order wording,
     NA never 0, no style attribute, no innerHTML. A phone gets a list instead of the candidate table (decided at draw time).
   Pure helpers (node: tools/web_app_portfolio_node_test.js): tierText, candidateRows, setLine, causeText, tierLine, modelPlan. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else api.install(typeof window==='object'&&window?window:root);})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
const RULE_ID='TIERS_RC_20261014';
const TIER_RULE=Object.freeze({n:15,core_n:5,core_pct:8,general_n:10,general_pct:6,decided:'2026-10-14'});
// The tier check statuses (QgvScores tierCheck; N_SELECTION_RULES_20261019.md §6), worded as the old leaderboard does.
const TIER_STATUS=Object.freeze({PASS:'16절 한도 통과',UNVERIFIED:'업종 묶음 40% 확인 불가',FAIL:'16절 한도 위반',CORE_SHORT:'핵심 5종목 미달 · 합계 100% 아님',INCOMPLETE:'N15 미완성'});
const TIER=Object.freeze({CORE:'핵심',GENERAL:'일반'});
// Set status words of QGV 1.1.7 (screen-qgv-live.js MODEL_STATUS) plus SHORTFALL.
const SET_STATUS=Object.freeze({FEASIBLE:'16절 한도 아래 구성 가능',UNVERIFIED:'업종 묶음 미정 · 확인 불가',FAIL:'16절 한도 초과',SHORTFALL:'구성 불가'});
const EXCLUDED=Object.freeze([['AXES_50','축 50%'],['VALUE_TRAP_GATE','가치 함정 관문'],['FINANCIAL_SAFETY','재무 안전 미달'],['FINANCIAL_SAFETY_NA','재무 안전 지표 NA'],['SUBGROUP_MAX_4','하위 묶음 상한']]);
const isObj=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
const fin=v=>typeof v==='number'&&Number.isFinite(v);
const pct=v=>fin(v)?(Number.isInteger(v)?String(v):v.toFixed(2))+'%':'NA';
const pct2=v=>fin(v)?v.toFixed(2)+'%':'NA';

/* ---------------------------------------------------------------- pure helpers */
// The words of a tier check status, with the code: '<words> (<CODE>)'; an unknown code keeps the code with 상태 미확인.
const tierText=s=>typeof s==='string'&&Object.hasOwn(TIER_STATUS,s)?TIER_STATUS[s]+' ('+s+')':'상태 미확인 ('+(typeof s==='string'&&s?s:'NA')+')';
/* The candidate rows of a model's primary set (N15): the set's selected rows in rank order joined with the tier check row of the
   same id (tier, weight_pct); a row without its tier row keeps tier / weight null (shown NA, never 0). sector(id) names a group. */
function candidateRows(M,sector=id=>id===null?'미정':id){
 const set=M&&M.sets&&M.sets[M.primary];if(!set)return[];
 const t=set.tier_check,by=new Map((t&&Array.isArray(t.rows)?t.rows:[]).map(r=>[r.id,r]));
 return set.selected.map(e=>{const x=by.get(e.id)||null,tier=x&&Object.hasOwn(TIER,x.tier)?x.tier:null;
  return Object.freeze({id:e.id,ticker:e.ticker,rank:Number.isInteger(e.rank)?e.rank:null,group:e.group,groupText:sector(e.group),tier,tierText:tier?TIER[tier]:'NA',
   weight_pct:x&&fin(x.weight_pct)?x.weight_pct:null,weightText:x&&fin(x.weight_pct)?pct(x.weight_pct):'NA'});});}
// One shortfall cause in words (the old leaderboard modelChecks words).
function causeText(c,sector=id=>id){
 if(!isObj(c))return null;
 if(c.code==='ELIGIBLE_EXHAUSTED')return'대체 후보 부족';
 if(c.code==='SECTOR_GROUP_MAX_40')return(Array.isArray(c.groups)?c.groups.map(sector).join('/'):'업종 묶음')+' 40% 한도로 '+c.count+'종목 초과';
 if(c.code==='SUBGROUP_MAX_4')return'하위 묶음 상한으로 '+c.count+'종목 제외';
 if(c.code==='MIN_HOLDINGS')return'최소 '+c.limit+'종목 미달';
 if(c.code==='GROUP_UNKNOWN')return'업종 묶음 미정 '+c.count+'종목';
 return null;}
// The set line: N15 7/15 · each equal weight · status; a short set says its shortfall weight, not filled, not re-weighted, and why.
function setLine(set,sector){
 if(!set)return null;
 const head='N'+set.n+' '+set.selected.length+'/'+set.n+' · 동일 비중이면 각 '+pct2(set.weight_pct)+' · '+(Object.hasOwn(SET_STATUS,set.status)?SET_STATUS[set.status]:'구성 상태 미확인');
 if(set.complete)return head;
 const why=set.causes.map(c=>causeText(c,sector)).filter(Boolean);
 return head+' · 부족 비중 '+pct2(set.shortfall_pct)+' · 채우지 않음 · 비중 재조정 없음'+(why.length?' · 원인: '+why.join(', '):'');}
// The tier check line: status words + code, core / general counts, summed weight, largest group, unknown share, selection unchanged.
function tierLine(t,sector=id=>id){
 if(!t)return'등급 비중 검사 없음 (N15가 아님)';
 const g=t.limits&&t.limits.group,top=g&&Array.isArray(g.groups)?g.groups.reduce((a,x)=>fin(x.pct)&&x.pct>(a?a.pct:-1)?x:a,null):null;
 return['등급 비중 검사 · '+tierText(t.status),'핵심 '+(Number.isInteger(t.core)?t.core:'NA')+' · 일반 '+(Number.isInteger(t.general)?t.general:'NA'),'비중 합계 '+pct2(t.sum_pct),
  top?'최대 업종 묶음 '+sector(top.id)+' '+pct2(top.pct):null,g&&g.unknown&&g.unknown.count?'업종 묶음 미정 '+g.unknown.count+'종목 '+pct2(g.unknown.pct):null,
  t.applied_to_selection===false?'선정은 바꾸지 않음':'선정 반영 여부 미확인'].filter(Boolean).join(' · ');}
/* What the model card draws for one page and its model: PAGE (not READY: the page's reason), NO_MODEL (the reason there is no
   official ranking or no candidate selection), MODEL. */
function modelPlan(pg,M){
 if(!isObj(pg)||pg.state!=='READY')return Object.freeze({kind:'PAGE',code:isObj(pg)?pg.reason||pg.state||'PAGE_NOT_READY':'PAGE_NOT_READY'});
 const b=isObj(pg.price_basis)?pg.price_basis:{};
 if(!M)return Object.freeze({kind:'NO_MODEL',code:b.inputs_match===false?'OFFICIAL_INPUTS_DIFFER':b.reason||'OFFICIAL_NOT_PUBLISHED'});
 return Object.freeze({kind:'MODEL',code:null});}

/* ---------------------------------------------------------------- screen */
function install(win){
 const I=win.IS2,{h,href}=I;
 const put=(box,...c)=>{box.replaceChildren();I.append(box,c);return box;};
 const mascot=m=>I.parts.mascot(m);
 const sub=(title,fn,hand)=>h('div',{class:'lb-head'},h('h3',{class:'stamp sub'},title),fn?h('span',{class:'meta'},'기능 ',fn):null,hand?h('span',{class:'hand'},hand):null);
 const block=(id,...c)=>h('div',{class:'sk card',dataset:{portfolioCard:id}},...c);
 const dl=(rows,attrs)=>h('dl',{class:'card-body',...(attrs||{})},rows.filter(Boolean).map(([k,v,d])=>[h('dt',null,h('b',null,k)),h('dd',d?{dataset:d}:null,v)]));
 const loading=what=>h('p',{class:'pending',role:'status',dataset:{state:'loading'}},'불러오는 중 · ',what);
 const failed=(code,text)=>h('div',{class:'sk state-card',dataset:{state:'error',na:code}},mascot('alarm'),h('p',{class:'err'},text));
 const empty=(code,text,more)=>h('div',{class:'sk state-card',dataset:{state:'empty',na:code}},mascot('plain'),h('p',null,text),more||null);
 const prep=(what,missing)=>{const n=I.parts.notReady('준비 중 · '+what,missing);n.dataset.prep='';return n;};
 const phone=()=>{try{return win.matchMedia('(max-width:720px)').matches;}catch(_){return false;}};
 const QS=()=>win.QgvScores;
 const sector=id=>{try{const S=QS();return S&&typeof S.sectorName==='function'?S.sectorName(id):id===null?'미정':id;}catch(_){return id===null?'미정':String(id);}};
 const say=code=>{try{return I.qgv.reasonText(code);}catch(_){return'자료를 읽지 못했습니다';}};
 let SF=null;
 const stamp=t=>{const d=Date.parse(t);return Number.isFinite(d)?(SF||(SF=new Intl.DateTimeFormat('ko-KR',{year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false,timeZone:'UTC'}))).format(d)+' UTC':null;};
 const errCode=e=>String(e&&e.message||e).split(' ')[0];

 /* ---------------- 모델 후보 */
 const modelHead=()=>sub('모델 후보 · 공식 평가','6.1.2 · 6.1.3','N15 = TARGET v1 / R-C 주검정');
 function table(rows,Q,pg){
  const at=r=>({candidateRow:r.id,tier:r.tier||'NA',weight:r.weight_pct===null?'NA':String(r.weight_pct)});
  if(phone())return h('ol',{class:'news-lines',dataset:{candidates:String(rows.length)}},rows.map(r=>h('li',{dataset:at(r)},
   h('b',null,r.rank===null?'—':String(r.rank),' · ',r.ticker),' · ',r.groupText,h('br'),'등급 ',h('b',null,r.tierText),' · 목표 비중 ',h('b',null,r.weightText))));
  return h('div',{class:'tbl-wrap'},h('table',{class:'tbl',dataset:{candidates:String(rows.length)}},
   h('caption',null,'순위 = ',Q.rankLabel(pg),' · 목표 비중 = 등급 비중 검사 (선정 불변)'),
   h('thead',null,h('tr',null,h('th',{scope:'col',class:'num'},'순위'),h('th',{scope:'col'},'티커'),h('th',{scope:'col'},'업종 묶음'),h('th',{scope:'col'},'등급'),h('th',{scope:'col',class:'num'},'목표 비중'))),
   h('tbody',null,rows.map(r=>h('tr',{dataset:at(r)},h('td',{class:'num'},r.rank===null?'—':String(r.rank)),h('td',null,h('a',{class:'lk',href:href('company',r.id)},r.ticker)),
    h('td',null,r.groupText),h('td',null,r.tierText),h('td',{class:'num'},r.weightText))))));}
 function paintModel(box,pg,M){
  const Q=I.qgv,plan=modelPlan(pg,M);
  if(plan.kind==='PAGE'){put(box,modelHead(),h('div',{class:'sk state-card',dataset:{state:'empty',na:plan.code,pageState:pg.state}},mascot(pg.state==='NO_DATA'?'plain':'alarm'),
   h('p',null,h('b',null,'모델 후보를 계산할 점수가 없습니다')),h('p',{class:'reason'},say(plan.code))));return;}
  if(plan.kind==='NO_MODEL'){put(box,modelHead(),empty(plan.code,say(plan.code)+' · 후보를 고르지 않습니다',h('p',{class:'reason'},'공식 순위가 있어야 후보를 고릅니다 · 0으로 채우지 않습니다')));return;}
  const set=M.sets[M.primary],t=set?set.tier_check:null,rows=candidateRows(M,sector);
  const counts=M.ns.map(n=>{const s=M.sets['N'+n];return s?'N'+n+' '+s.selected.length+'/'+n:null;}).filter(Boolean).join(' · ');
  put(box,modelHead(),
   h('p',{class:'hand'},'공식 기본 프로필 · 화면 필터와 내 설정은 선정에 영향 없음 · 후보 수 ',counts),
   h('p',{class:'status-line',dataset:{modelSet:set?set.status:'NONE',modelComplete:String(!!(set&&set.complete)),modelShortfall:set&&fin(set.shortfall_pct)?set.shortfall_pct.toFixed(2):'NA'}},setLine(set,sector)||'N15 없음'),
   h('p',{class:'status-line',dataset:{tierCheck:t?t.status||'NA':'NONE',tierApplied:t?String(t.applied_to_selection):'NA',tierCore:t&&Number.isInteger(t.core)?String(t.core):'NA',tierSum:t&&fin(t.sum_pct)?t.sum_pct.toFixed(2):'NA'}},tierLine(t,sector)),
   h('p',{class:'reason',dataset:{tierRule:t&&t.rule?t.rule:RULE_ID}},'등급 규칙 ',t&&t.rule?t.rule:RULE_ID,' · 오너 결정 ',TIER_RULE.decided,' · 핵심 ',String(TIER_RULE.core_n),' × ',String(TIER_RULE.core_pct),'% + 일반 ',String(TIER_RULE.general_n),' × ',String(TIER_RULE.general_pct),'% · 핵심 = 상위 5 중 산출 요인 80% 이상 · 재무 안전 통과'),
   rows.length?table(rows,Q,pg):empty('NO_CANDIDATE','자격을 통과한 후보가 없습니다 · 채우지 않습니다'),
   h('p',{class:'reason',dataset:{modelExcluded:''}},'제외: ',...EXCLUDED.flatMap(([k,l],i)=>[i?' · ':'',l,' ',Number.isInteger(M.excluded[k])?String(M.excluded[k]):'NA'])),
   M.provisional.includes('SUBGROUP_UNKNOWN_NOT_CAPPED')?h('p',{class:'reason',dataset:{modelUnknown:''}},'하위 묶음 미정 ',Number.isInteger(M.unknown.subgroup)?String(M.unknown.subgroup):'NA','종목 · 상한 미적용 · 잠정 · 결정 대기'):null,
   set&&set.issuer_check&&set.issuer_check.issuers_n>0?h('p',{class:'reason',dataset:{modelIssuer:''}},'같은 발행사 합산 비중 · 결정 대기 (선정 불변)'):null,
   h('div',{class:'links'},h('a',{class:'lk',href:href('qgv')},'→ 1. QGV 1.1.7 후보 선정'),h('a',{class:'lk',href:href('detail','target-v1')},'→ 세부: TARGET v1 빌더')));}

 /* ---------------- 적용 버전 · 기준일 */
 const basisHead=()=>sub('적용 버전 · 기준일','6.1.4','공식 게시본 기준');
 function paintBasis(box,pg,M){
  const Q=I.qgv,b=isObj(pg.price_basis)?pg.price_basis:{},ready=pg.state==='READY';
  const pub=b.publication_id?b.publication_id.slice(0,19)+'…':null;
  put(box,basisHead(),
   ready?null:h('p',{class:'reason',dataset:{na:pg.reason||pg.state,basisState:pg.state}},say(pg.reason||pg.state)),
   dl([['기준일 (점수 갱신)',stamp(pg.as_of)||'없음',{basisAsOf:pg.as_of||''}],['계산 버전',pg.calc_version||'없음',{basisCalc:pg.calc_version||''}],
    ['V 기준',b.label||pg.v_source.ko,{basisV:b.kind||''}],
    ['가격 기준일 · 게시',(b.price_basis_date||'없음')+' · '+(stamp(b.generated_at)||'없음'),{basisPublished:b.publication_id||''}],
    pub?['게시본',pub]:null,
    ['순위',Q.rankLabel(pg)],
    ['공식 프로필',M&&M.official_profile?M.official_profile.id:pg.profile_id||'없음',{basisProfile:M&&M.official_profile?M.official_profile.id:pg.profile_id||''}],
    ['등급 규칙',RULE_ID]],{dataset:{portfolioBasis:''}}),
   b.reason?h('p',{class:'reason',dataset:{na:b.reason}},say(b.reason)):null,
   b.stale===true?h('p',{class:'chip err',dataset:{basisStale:'STALE'}},'STALE · 기준일 뒤 끝난 뉴욕 정규장 2회 초과 · 마지막 게시본 그대로'):null,
   b.attribution?h('p',{class:'reason',dataset:{attribution:''}},b.attribution.text,' ',h('a',{class:'lk',href:b.attribution.terms_url,target:'_blank',rel:'noopener noreferrer'},'IEX 약관')):null);}

 /* ---------------- static cards */
 const targetCard=()=>block('target-v1',sub('TARGET v1 상태','6.1.4','공개 상태만'),
  h('div',{class:'sk state-card',dataset:{state:'empty',na:'TARGET_V1_NOT_PUBLISHED',targetV1:'NOT_PUBLISHED'}},mascot('plain'),
   h('p',null,h('b',null,'TARGET v1 확정본은 아직 게시되지 않았습니다')),
   h('p',{class:'reason'},'확정 창 2026-11-09 ~ 11-15 · 초안은 세부 화면 TARGET v1 빌더에서 만듭니다')),
  h('p',{class:'reason'},'이 화면은 빌더를 돌리지 않고 이 기기의 TARGET 기록도 읽지 않습니다 · 빌더는 11/16 PR까지 자기 V 출처를 따로 씁니다 (DC-31)'),
  h('div',{class:'links'},h('a',{class:'lk',href:href('detail','target-v1')},'→ 세부: TARGET v1 빌더')));
 const mockCard=()=>block('mock',sub('모의','6.1.5'),
  prep('모의 포트폴리오 기록은 다음 P2-6 단계에서 붙입니다',['내 시트 모의 장부 연결','기록 실행']),
  h('p',{class:'reason'},'이 화면에는 아직 모의 기록이 없습니다 · 지금은 아무것도 저장하지 않습니다'));

 // The skeleton's four slots filled: 5-1's cards (model and basis with their loading lines), the private panel at once in its
 // first state, then the page once IS2.qgv answered (route.signal and a generation drop a late fill of a page left or reloaded).
 function screen(route,{slots}){
  const signal=route.signal,aborted=()=>signal.aborted,Q=I.qgv;let gen=0;
  let panel=null;try{panel=I.parts.privatePanel({id:'portfolio-actual',title:'실제 (내 것)'});}catch(_){panel=null;}
  const refs={model:block('model',modelHead(),loading('모델 후보')),basis:block('basis',basisHead(),loading('적용 버전'))};
  put(slots['5-1'],h('p',{class:'hand'},'세 가지 포트폴리오 · 모델은 공개 자료로, 실제와 모의는 내 자료로 · 공개 부분은 개인 자료 없이 그대로 보입니다'),
   refs.model,refs.basis,targetCard(),
   block('actual',sub('실제 (내 것)','6.1.1 · 6.1.5'),h('p',{class:'reason',dataset:{actualNote:''}},'보유는 이 기기와 내 시트에만 있습니다 · 이 화면은 보유를 요청하거나 저장하지 않습니다'),panel?panel.node:null),
   mockCard());
  put(slots['5-2'],prep('실제 포트폴리오 일일 · 주간 보고는 다음 단계에서 붙입니다',['이 기기 보유 연결','클릭 시세','보고 모델']),h('p',{class:'reason'},'이 PR에는 없습니다'));
  put(slots['5-3'],prep('모의 포트폴리오 일일 보고는 다음 단계에서 붙입니다',['내 시트 모의 장부','클릭 시세']),h('p',{class:'reason'},'이 PR에는 없습니다'));
  put(slots['5-4'],prep('포트폴리오 내용구성 트리는 다음 단계에서 붙입니다',null),h('p',{class:'reason'},'실제 · 모의 칸은 개인 자료라 공개하지 않습니다 ',h('a',{class:'lk',href:href('tree')},'→ n. 구조 트리')));
  function load(){const my=++gen;
   let p;try{p=Q.page({signal});}catch(e){p=Promise.reject(e);}
   Promise.resolve(p).then(pg=>{if(aborted()||my!==gen)return;let M=null;if(pg.state==='READY'){try{M=Q.model(pg);}catch(_){M=null;}}
    try{paintModel(refs.model,pg,M);}catch(_){put(refs.model,modelHead(),failed('MODEL_RENDER_FAILED','모델 후보를 그리지 못했습니다'));}
    try{paintBasis(refs.basis,pg,M);}catch(_){put(refs.basis,basisHead(),failed('BASIS_RENDER_FAILED','적용 버전을 그리지 못했습니다'));}},
   e=>{if(aborted()||my!==gen||errCode(e)==='ABORTED')return;
    put(refs.model,modelHead(),failed('PAGE_FAILED','QGV 점수를 계산하지 못해 모델 후보를 그리지 못했습니다'));
    put(refs.basis,basisHead(),failed('PAGE_FAILED','적용 버전을 읽지 못했습니다'));});}
  load();
  try{Q.subscribe(why=>{if(why==='DATA'&&!aborted())load();},{signal});}catch(_){}}
 I.portfolioLive=Object.freeze({screen});
}
return Object.freeze({RULE_ID,TIER_RULE,TIER_STATUS,TIER,SET_STATUS,tierText,candidateRows,causeText,setLine,tierLine,modelPlan,install});
});
