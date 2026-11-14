/* QGV 555 · 시총 Top500 · 사용자 설정 (IS2.qgv555; owner 2026-11-14 「Top500 전환·QGV 555·사용자 설정 구현」, DC-49).
   Reader and setting editor of Codex's contract (#537 a22ce2a4, docs/research/sector_qgv/QGV_555.md): catalog(), accounting
   recipes, selectable_metrics(), qgv-555-config/1, the preview page qgv-555-preview-page/1 (Codex preview() → preview_page()),
   detail rows and role deciles of the same preview, Main's replay record qgv-555-saved/1 (the after result's fields Codex
   replay() reads, no rows), and top500-view/1 (Codex top500_view(): an allowlisted authenticated research projection, not a
   publication right). Pure: no window, no request, no storage.
   - Populations (2.1): 기존504 / 시총 Top500 / 확장 연구 — three identities. A Top500 selection is a research candidate
     (VALIDATED_RESEARCH_CANDIDATE, never an official replacement) or UNCONFIRMED_CANDIDATE: 「자료가 있는 기업 중 상위 500
     (전체시장 Top500 확정 아님)」 with the previous good one kept. Selection order is not a QGV rank; no price or market cap.
   - Models: 기존 공식 / U1-555 통합 (unified-555/0.1.0) / S1-555 섹터 (sector-555/0.1.0) / 내 설정; apart from the reduced and the
     stopped 3/3/3 ids. 555 = five evaluation ROLES per axis = the existing official 15 (several metrics in a role are one role).
   - Editor of one qgv-555-config/1 (every function returns a new frozen setting): axis weights (U1 axis_weights; S1 the
     sector's sector_axis_overrides), role weight, role exclusion (weight 0 → active count Q4/G5/V5), metrics in a role (a second
     metric splits that role's budget; the role weight is unchanged), metric weights inside a role (the role's composite), replace,
     restore (the setting's own candidate and version). S1 role edits go to scoped_role_overrides[SECTOR|TEMPLATE] only: nothing
     reaches another sector or accounting model. Policies (minimum, missing, reference, gate, duplicate) are not editable here.
   - Display only: the setting's own numbers and sums; families shared by chosen metrics (input_family) with the engine's
     nominal / effective exposure once a preview answered — never a penalty or a hidden adjustment; factor cards; the engine's
     before / after rows, coverage stages, role deciles (D1–D10, counted from the engine's decile per row), company detail.
     Scores, ranks, deciles, nominal / effective weights: the engine's only. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else{const I=root.IS2=root.IS2||{};I.qgv555=api;}})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
const SCHEMA=Object.freeze({CONFIG:'qgv-555-config/1',RESULT:'qgv-555-result/1',PAGE:'qgv-555-preview-page/1',SAVED:'qgv-555-saved/1',VIEW:'top500-view/1'});
const AXES=Object.freeze(['Q','G','V']),ROLES_PER_AXIS=5;
const SAVED_KEYS=Object.freeze(['schema_version','configuration','evaluation','reference','bindings','calculated_at','result_hash']);
const HEX=/^[0-9a-f]{64}$/,DAY=/^\d{4}-\d{2}-\d{2}$/;
// The fifteen roles (Codex SUBMETRICS + V_SPECS ids; names from the owner's 555 design page).
const ROLE_TEXT=Object.freeze({
 q_profitability:['수익성','자본·자산 대비 이익을 얼마나 내는가'],q_moat_proxy:['수익성 지속성(경쟁우위 대리)','장기 수익성 수준과 안정성 · 해자의 직접 증거 아님'],
 q_earnings_quality:['이익의 질','이익이 현금·자산 변화와 맞는가'],q_financial_safety:['재무 안전성','부채와 이자 감당 능력'],q_capital_allocation:['자본 배분','희석과 증분 수익성'],
 g_revenue_growth:['매출 성장','3년 매출 성장'],g_per_share_growth:['주당 이익·현금흐름 성장','EPS·주당 FCF 성장'],g_growth_efficiency:['성장 효율','증분 ROIC'],
 g_consistency:['성장 일관성','성장한 해의 비율·성장률 변동성'],g_recent_acceleration:['최근 성장 가속','최근 성장률 − 3년 성장률'],
 v_earnings_yield:['이익 수익률','EBIT/EV'],v_fcf_yield:['현금흐름 수익률','FCF/EV'],v_vs_industry:['업종 대비 가치','업종 안 가치 비교'],
 v_vs_own_history:['자기 과거 대비 가치','과거 가치 수준과 비교'],v_expectation_check:['성장 기대 점검','역DCF 내재 성장과 실적 비교']});
const POPULATIONS=Object.freeze({
 universe504:Object.freeze({label:'기존504',text:'Universe504 · S&P 500 구성에서 출발해 고정한 504코드 · 시총 순위로 고른 목록 아님'}),
 top500:Object.freeze({label:'시총 Top500',text:'시가총액 상위 500 고유 발행사(종류주 합산·중복 집계 없음) · 기존504와 다른 모집단'}),
 expanded:Object.freeze({label:'확장 연구',text:'확장 연구 표본 · 전체시장 아님 · 운영 결과 아님'})});
const MODELS=Object.freeze({
 OFFICIAL:Object.freeze({label:'기존 공식',kind:'OFFICIAL',model_id:null}),
 'U1-555':Object.freeze({label:'U1-555 통합',kind:'COMMON',model_id:'unified-555/0.1.0'}),
 'S1-555':Object.freeze({label:'S1-555 섹터',kind:'SECTOR',model_id:'sector-555/0.1.0'}),
 MY:Object.freeze({label:'내 설정',kind:'USER',model_id:null})});
const CANDIDATE_OF=Object.freeze({'unified-555/0.1.0':'U1-555','sector-555/0.1.0':'S1-555'});
const KIND_TEXT=Object.freeze({COMMON:'통합 · 모든 평가 기업에 같은 공통 요소 · 공통 순위',SECTOR:'섹터 · 그 섹터·회계모형 안에서만 순위 · 섹터 점수를 이어 붙인 통합 순위 아님'});
const TEMPLATE_TEXT=Object.freeze({GENERAL:'일반',BANK:'은행',INSURANCE:'보험',BROKER:'증권',MORTGAGE_REIT:'모기지 REIT',ASSET_MANAGER:'자산운용',EQUITY_REIT:'지분형 REIT'});
const PERIOD_TEXT=Object.freeze({FY:'회계연도',TTM:'최근 12개월',LATEST_QUARTER:'최근 분기말',FY1:'다음 회계연도 전망',NTM:'향후 12개월 전망',ONE_YEAR:'1년',FY_1Y:'회계연도 1년',FY_3Y:'회계연도 3년',
 FY_5Y:'회계연도 5년',FY_5Y_MIN3:'회계연도 5년(최소 3년)',HISTORY_MIN3:'과거 3개 이상',DCF_AND_FY3:'역DCF와 3년 실적'});
const UNIT_TEXT=Object.freeze({decimal:'소수',percentile:'백분위',multiple:'배수'});
const STATUS_TEXT=Object.freeze({EXISTING_KERNEL:'계산 구현됨'});
// Display flags (owner 2026-11-14: 임시 분류·REIT 임시·대체 지표 사용 표시). Read only when the producer's row / metric carries
// `display_flags` (codes) or a metric carries `substitute_for` (the default metric it replaces); names proposed to Codex in #437 and
// fixed when Codex confirms them. A code this table does not know is still shown (never hidden), as 「표시 규칙 확인 전」.
const FLAG_TEXT=Object.freeze({CLASSIFICATION_PROVISIONAL:'임시 분류',REIT_PROVISIONAL:'REIT 임시 처리',SUBSTITUTE_METRIC:'대체 지표 사용',
 TEMPORARY_OFFICIAL_PROXY:'공식 모형 임시 대리값 · 555 미완결'});
function flagsOf(x){const f=x&&typeof x==='object'&&Array.isArray(x.display_flags)?x.display_flags:[];
 return Object.freeze(f.filter(c=>typeof c==='string'&&c).map(c=>Object.freeze({code:c,text:FLAG_TEXT[c]||'표시 규칙 확인 전 표시'})));}
function substituteOf(m){return m&&typeof m==='object'&&typeof m.substitute_for==='string'&&m.substitute_for?m.substitute_for:null;}
const REC_TEXT=Object.freeze({OWNER_555_BASELINE_NOT_PERFORMANCE_OPTIMUM:'555 기본 구성(성과 최적값 아님)',SUITABLE_OPTION_NOT_DEFAULT:'적합한 선택지(기본값 아님)'});
const GATE_TEXT=Object.freeze({PASS:'관문 통과',VALUE_EXCLUDED:'관문: V 총점 반영 제외',UNKNOWN:'관문 판정 불가(총점 없음)'});
const REASON_TEXT=Object.freeze({RAW_MISSING:'원값 없음',DEFINITION_OR_SOURCE_UNVERIFIED:'정의·출처 미검증',NOT_AVAILABLE_AT_CUTOFF:'입력 마감 시점에 없음',
 HISTORICAL_SHARE_BASIS_UNVERIFIED:'과거 주식 기준 미검증',ACCOUNTING_NOT_APPLICABLE:'이 회계모형에 부적합',VALUATION_SECURITY_BASIS_UNVERIFIED:'평가일 증권·가격 기준 미검증',
 PEER_SAMPLE_SMALL:'비교 기업 부족(최소 8)',ACCOUNTING_RECIPE_PREPARING:'이 회계모형의 555 정의 준비 중',DISABLED_IN_SETTING:'설정에서 비중 0'});
const SELECTION_TEXT=Object.freeze({VALIDATED_RESEARCH_CANDIDATE:'검증된 연구 후보 · 시총 상위 500 고유 발행사 · 공식 모집단 교체 아님',
 UNCONFIRMED_CANDIDATE:'자료가 있는 기업 중 상위 500(전체시장 Top500 확정 아님)'});
const SELECTION_REASON=Object.freeze({CANDIDATE_COVERAGE_UNPROVEN:'후보 명부 완전성 근거 없음',DUPLICATE_ISSUER:'발행사 중복',MISSING_MARKET_CAP_COULD_CROSS_BOUNDARY:'시총 결손이 500위 경계를 넘을 수 있음',
 FEWER_THAN_500_ELIGIBLE_ISSUERS:'적격 발행사 500 미만'});
const DATA_KIND_TEXT=Object.freeze({SYNTHETIC:'합성 자료',PRIVATE:'비공개 실자료'});

const isObj=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
const own=(o,k)=>Object.prototype.hasOwnProperty.call(o,k);
const num=v=>typeof v==='number'&&Number.isFinite(v);
const copy=v=>JSON.parse(JSON.stringify(v));
const freeze=v=>{if(v&&typeof v==='object'){Object.freeze(v);for(const k of Object.keys(v))freeze(v[k]);}return v;};
const word=(T,v)=>own(T,v)?T[v]:String(v);
const fail=c=>{throw Error(c);};
const pct=x=>num(x)?(Math.round(x*10000)/100).toFixed(2)+'%':'—';
const score=x=>num(x)?(Math.round(x*10)/10).toFixed(1):'—';

/* ---- context (qgv555_context) */
function checkContext(x){
 if(!isObj(x)||!isObj(x.catalog)||!isObj(x.configs)||!Array.isArray(x.recipes)||!Array.isArray(x.sectors)||!Array.isArray(x.templates))fail('CONTEXT_SHAPE');
 for(const[k,m]of Object.entries(x.catalog)){if(!isObj(m)||m.canonical_id!==k||!AXES.includes(m.axis)||!Array.isArray(m.roles)||!Array.isArray(m.aliases)||!Array.isArray(m.accounting_scope)||typeof m.input_family!=='string')fail('CATALOG_ENTRY:'+k);}
 const roles={Q:[],G:[],V:[]};
 for(const cand of['U1-555','S1-555']){const c=x.configs[cand];
  if(!isObj(c)||c.schema_version!==SCHEMA.CONFIG||c.candidate!==cand||c.model_id!==MODELS[cand].model_id||!isObj(c.roles))fail('CONFIG:'+cand);
  const ids=Object.keys(c.roles);if(ids.length!==15)fail('ROLES_NOT_FIFTEEN');
  for(const a of AXES){const rs=ids.filter(r=>c.roles[r].axis===a);if(rs.length!==ROLES_PER_AXIS)fail('ROLES_NOT_FIVE:'+a);if(cand==='U1-555')roles[a]=rs;}
  for(const[r,v]of Object.entries(c.roles)){if(!own(ROLE_TEXT,r))fail('ROLE_UNKNOWN:'+r);for(const m of Object.keys(v.metrics))if(!own(x.catalog,m)&&!aliasOf(x.catalog,m))fail('METRIC_UNKNOWN:'+m);}}
 const sectors={};for(const s of x.sectors){if(!isObj(s)||typeof s.sector_id!=='string'||!isObj(s.axis_weights))fail('SECTOR');sectors[s.sector_id]=s.axis_weights;}
 const recipes={};for(const r of x.recipes)recipes[r.accounting_template]=r;
 if(!recipes.GENERAL||recipes.GENERAL.state!=='DEFINED_GENERAL')fail('RECIPE_GENERAL');
 if(!isObj(x.selectable))fail('SELECTABLE');for(const t of x.templates)if(!isObj(x.selectable[t]))fail('SELECTABLE:'+t);
 if(!isObj(x.anchors)||!isObj(x.anchors.evaluation)||!isObj(x.anchors.reference)||!HEX.test(String(x.anchors.evaluation.input_hash))||!HEX.test(String(x.anchors.reference.input_hash)))fail('ANCHORS');
 return freeze({data_kind:x.data_kind||null,catalog:copy(x.catalog),configs:copy(x.configs),selectable:copy(x.selectable),anchors:copy(x.anchors),roles,sectors,templates:[...x.templates],recipes,inputs:copy(x.inputs||[])});}
function aliasOf(cat,name){for(const m of Object.values(cat))if(m.aliases.includes(name))return m.canonical_id;return null;}
const canonical=(ctx,m)=>own(ctx.catalog,m)?m:(aliasOf(ctx.catalog,m)||m);
const roleText=r=>own(ROLE_TEXT,r)?ROLE_TEXT[r][0]:r;
const templateOf=scope=>scope==='COMMON'?'GENERAL':String(scope).split('|')[1];
const sectorOf=scope=>scope==='COMMON'?null:String(scope).split('|')[0];
// S1 scopes: every sector × accounting model; only those whose recipe is complete can be edited and run.
function scopes(ctx,cand){if(cand==='U1-555')return[{scope:'COMMON',state:'DEFINED_GENERAL'}];
 return Object.keys(ctx.sectors).flatMap(s=>ctx.templates.map(t=>({scope:s+'|'+t,state:(ctx.recipes[t]||{}).state||'UNKNOWN'})));}
function recipeLine(ctx,scope){const t=templateOf(scope),r=ctx.recipes[t];if(!r)return'회계모형 정의 없음';
 if(r.state==='DEFINED_GENERAL')return'일반기업 555 정의 완결';
 const open=Object.entries(r.roles||{}).filter(([,v])=>v.state!=='DEFINED').map(([k])=>roleText(k));
 return(TEMPLATE_TEXT[t]||t)+' · 555 정의 준비 중'+(open.length?' · 미완결 역할 '+open.join('·'):'')+' · 일반기업 식으로 대체하지 않음';}

/* ---- the setting (qgv-555-config/1) */
function start(ctx,cand){const c=ctx.configs[cand];if(!c)fail('MODEL_UNKNOWN');return freeze(copy(c));}
const edit=(c,fn)=>{const o=copy(c);fn(o);return freeze(o);};
function rolesOf(c,scope){const r=copy(c.roles);if(c.candidate==='S1-555'&&scope!=='COMMON')Object.assign(r,copy((c.scoped_role_overrides||{})[scope]||{}));return r;}
function axisOf(c,ctx,scope){if(c.candidate==='U1-555'||scope==='COMMON')return copy(c.axis_weights);const s=sectorOf(scope);
 return copy((c.sector_axis_overrides||{})[s]||ctx.sectors[s]||c.axis_weights);}
const weightOk=v=>num(v)&&v>=0;
function setAxis(c,ctx,scope,a,v){if(!AXES.includes(a)||!weightOk(v))fail('WEIGHT_INVALID');
 return edit(c,o=>{if(o.candidate==='U1-555'){o.axis_weights[a]=v;return;}const s=sectorOf(scope);if(!s)fail('SETTING_SCOPE');
  o.sector_axis_overrides=o.sector_axis_overrides||{};o.sector_axis_overrides[s]={...axisOf(c,ctx,scope),[a]:v};});}
// One role's edit: U1 changes the common role; S1 writes this scope's override only (never another sector or accounting model).
function editRole(c,scope,role,fn){const cur=rolesOf(c,scope)[role];if(!cur)fail('ROLE_UNKNOWN');const next=fn(copy(cur));
 return edit(c,o=>{if(o.candidate==='U1-555'){o.roles[role]=next;return;}if(scope==='COMMON')fail('SETTING_SCOPE');
  o.scoped_role_overrides=o.scoped_role_overrides||{};o.scoped_role_overrides[scope]={...(o.scoped_role_overrides[scope]||{}),[role]:next};});}
const setRole=(c,scope,role,v)=>{if(!weightOk(v))fail('WEIGHT_INVALID');return editRole(c,scope,role,r=>({...r,weight:v}));};
const excludeRole=(c,scope,role)=>editRole(c,scope,role,r=>({...r,weight:0}));
function setMetric(c,scope,role,m,v){if(!weightOk(v))fail('WEIGHT_INVALID');return editRole(c,scope,role,r=>{if(!own(r.metrics,m))fail('METRIC_NOT_SELECTED');r.metrics[m]=v;return r;});}
// Why a metric cannot go into a role here (null = it can). Codex selectable_metrics(role, template) decides fit (an unassigned or
// not-recommended metric of the same axis and accounting model is selectable); the setting adds alias and recipe states.
function blocked(ctx,c,scope,role,m){const e=ctx.catalog[canonical(ctx,m)],r=rolesOf(c,scope)[role];if(!e)return'METRIC_UNKNOWN';if(!r)return'ROLE_UNKNOWN';
 const sel=(ctx.selectable[templateOf(scope)]||{})[role]||[];
 if(e.implementation_status!=='EXISTING_KERNEL')return'NOT_IMPLEMENTED';
 if(!sel.includes(e.canonical_id))return e.axis!==r.axis?'AXIS_MISMATCH':'ACCOUNTING_NOT_APPLICABLE';
 if((ctx.recipes[templateOf(scope)]||{}).state!=='DEFINED_GENERAL')return'ACCOUNTING_RECIPE_PREPARING';
 if(Object.keys(r.metrics).some(x=>canonical(ctx,x)===e.canonical_id))return'ALIAS_DUPLICATE';return null;}
// Adding a metric splits the role's budget (weight 1 beside the others); the role's weight never grows.
function addMetric(ctx,c,scope,role,m){const b=blocked(ctx,c,scope,role,m);if(b)fail(b);return editRole(c,scope,role,r=>{r.metrics[m]=1;return r;});}
function removeMetric(c,scope,role,m){return editRole(c,scope,role,r=>{if(!own(r.metrics,m))fail('METRIC_NOT_SELECTED');if(Object.keys(r.metrics).length<2)fail('ROLE_LAST_METRIC');delete r.metrics[m];return r;});}
function replaceMetric(ctx,c,scope,role,from,to){const r=rolesOf(c,scope)[role];if(!r||!own(r.metrics,from))fail('METRIC_NOT_SELECTED');
 const w=r.metrics[from],tmp=editRole(c,scope,role,x=>{delete x.metrics[from];return x;}),b=blocked(ctx,tmp,scope,role,to);if(b)fail(b);
 return editRole(tmp,scope,role,x=>{x.metrics[to]=w;return x;});}
// 기본값 복원: the setting's own candidate at its own version (a newer default never replaces it); the scope's own overrides only.
function restore(ctx,c){const b=ctx.configs[c.candidate];if(!b||b.version!==c.version)fail('BASE_VERSION_MISSING');return start(ctx,c.candidate);}
function restoreScope(c,scope){return edit(c,o=>{if(o.scoped_role_overrides)delete o.scoped_role_overrides[scope];if(o.sector_axis_overrides&&sectorOf(scope))delete o.sector_axis_overrides[sectorOf(scope)];});}

/* ---- setting display (its own numbers only) */
function activeCount(c,scope){const r=rolesOf(c,scope),n={};
 for(const a of AXES)n[a]=Object.values(r).filter(x=>x.axis===a&&x.weight>0&&Object.values(x.metrics).some(w=>w>0)).length;return freeze({...n,text:'Q'+n.Q+'/G'+n.G+'/V'+n.V});}
// The engine refuses a setting without a positive sum on an axis, a role or a metric set; the screen says so before asking.
function problems(c,ctx,scope){const out=[],r=rolesOf(c,scope),ax=axisOf(c,ctx,scope);
 if(!AXES.every(a=>weightOk(ax[a]))||AXES.reduce((t,a)=>t+ax[a],0)<=0)out.push({code:'AXIS_WEIGHTS',where:'축'});
 for(const a of AXES)if(Object.values(r).filter(x=>x.axis===a).reduce((t,x)=>t+x.weight,0)<=0)out.push({code:'ROLE_WEIGHTS',where:a});
 for(const[k,x]of Object.entries(r))if(!Object.values(x.metrics).some(w=>w>0))out.push({code:'METRIC_WEIGHTS',where:roleText(k)});
 return freeze(out);}
function sums(c,ctx,scope){const r=rolesOf(c,scope),ax=axisOf(c,ctx,scope);
 return freeze({axis:AXES.reduce((t,a)=>t+ax[a],0),roles:Object.fromEntries(AXES.map(a=>[a,Object.values(r).filter(x=>x.axis===a).reduce((t,x)=>t+x.weight,0)])),axes:ax});}
// Input families read by more than one chosen metric (same role or across roles / axes). exposure: the engine's nominal family
// total from a preview row of this scope, when one answered; never computed here and never a penalty.
function families(ctx,c,scope,row){const by=new Map(),r=rolesOf(c,scope);
 for(const[role,x]of Object.entries(r))for(const m of Object.keys(x.metrics)){const e=ctx.catalog[canonical(ctx,m)];if(!e)continue;
  const f=by.get(e.input_family)||{family:e.input_family,roles:new Set(),axes:new Set(),metrics:[]};f.roles.add(role);f.axes.add(x.axis);f.metrics.push(e.canonical_id);by.set(e.input_family,f);}
 const fc=row&&row.after&&isObj(row.after.families)?row.after.families:null;
 return freeze([...by.values()].filter(f=>f.metrics.length>1).map(f=>({family:f.family,roles:[...f.roles],axes:[...f.axes].sort(),metrics:f.metrics,cross_axis:f.axes.size>1,
  nominal:fc&&fc[f.family]?fc[f.family].nominal:null,effective:fc&&fc[f.family]?fc[f.family].effective:null})).sort((a,b)=>b.metrics.length-a.metrics.length||a.family.localeCompare(b.family)));}
function card(ctx,m,c,scope,role,row){const e=ctx.catalog[canonical(ctx,m)];if(!e)return null;const r=c?rolesOf(c,scope)[role]:null,chosen=!!(r&&own(r.metrics,m));
 const why=c&&!chosen?blocked(ctx,c,scope,role,m):null,W=row&&row.after&&Array.isArray(row.after.weights)?row.after.weights:[],lin=W.filter(x=>x.role===role&&x.metric===e.canonical_id);
 const alts=why&&why!=='ALIAS_DUPLICATE'&&r?Object.values(ctx.catalog).filter(x=>x.axis===r.axis&&!blocked(ctx,c,scope,role,x.canonical_id)).slice(0,4).map(x=>x.display_name):[];
 const share=chosen?Object.values(r.metrics).reduce((t,w)=>t+w,0):0;
 return freeze({id:e.canonical_id,name:e.display_name,axis:e.axis,roles:e.roles.map(roleText),
  formula:String(e.formula)+' · '+word(PERIOD_TEXT,e.period)+' · 단위 '+word(UNIT_TEXT,e.unit)+' · '+(e.direction>0?'높을수록 좋음':'낮을수록 좋음(점수는 좋은 쪽이 높게)'),
  templates:e.accounting_scope.map(t=>TEMPLATE_TEXT[t]||t).join('·'),badges:[e.default?'기본값':null,chosen?'현재 선택':null].filter(Boolean),
  recommendation:word(REC_TEXT,e.recommendation),status:word(STATUS_TEXT,e.implementation_status)+' · 자료 유무는 엔진 답',selectable:chosen||!why,why,alternatives:alts,
  evidence:e.formula_source+' · '+(e.source==='SECTOR_CATALOG'?'섹터 요소 사전':'기존 코드 정의')+' · 검증 '+(e.validation==='REQUIRES_EVIDENCE'?'기업별 근거 필요':e.validation),
  aliases:e.aliases,family:e.input_family,
  assignment:e.roles.length?(e.roles.includes(role)?'기본 역할':'다른 역할의 기본 지표 · 이 역할('+roleText(role)+')에 명시 배정'):'기본 역할 없음 · 이 역할('+roleText(role)+')에 명시 배정',
  weights:chosen?'역할 안 설정 '+r.metrics[m]+'/'+share+' · 역할 설정 '+r.weight+(lin.length?' · 총점 명목 '+pct(lin[0].nominal)+' · 결측 재배분 뒤 '+pct(lin[0].missing_redistributed_before_gate)+' · 관문 뒤 '+pct(lin[0].after_gate)+'(엔진 답 · 첫 기업)':' · 명목·재배분·관문 뒤 비중은 미리보기 뒤 엔진 답'):'선택 안 됨'});}
function search(ctx,q){const t=String(q||'').trim().toLowerCase();if(!t)return[];
 return Object.values(ctx.catalog).filter(e=>[e.canonical_id,e.display_name,...e.aliases].some(n=>String(n).toLowerCase().includes(t))).map(e=>e.canonical_id);}

/* ---- engine answers (qgv-555-preview-page/1 from Codex preview(); detail rows and role deciles of the same kept preview) */
// One preview answer: late (another request or an edited setting), other-model and other-setting answers are never shown.
const same=(a,b)=>canon(a)===canon(b);
function canon(v){if(Array.isArray(v))return'['+v.map(canon).join(',')+']';if(isObj(v))return'{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canon(v[k])).join(',')+'}';return JSON.stringify(v);}
// anchors: the route's independent evaluation / reference identities (qgv555_context), never taken from the answer itself.
function previewAnswer(req,res,current,anchors){if(!isObj(res))return{state:'ENGINE_NOT_CONNECTED'};if(res.request_id!==req.request_id||req!==current)return{state:'LATE_ANSWER'};
 if(res.ok!==true)return{state:'REFUSED',code:res.code||'ENGINE_FAILED'};if(res.model_id!==req.model_id)return{state:'MODEL_MISMATCH'};
 const pg=res.page,sv=res.saved;
 if(!isObj(pg)||pg.schema_version!==SCHEMA.PAGE||pg.request_id!==req.request_id||!Array.isArray(pg.rows)||!isObj(pg.before_coverage)||!isObj(pg.after_coverage))return{state:'REFUSED',code:'PAGE_SHAPE'};
 if(validateSaved(sv).ok!==true||sv.configuration.model_id!==req.model_id)return{state:'MODEL_MISMATCH'};
 if(JSON.stringify(sv.configuration)!==JSON.stringify(req.config))return{state:'CONFIG_MISMATCH'};
 if(sv.result_hash!==pg.after_result_hash)return{state:'REFUSED',code:'RESULT_HASH'};
 // The before side: with a saved record asked for, only its replay whose hash is the saved one (Codex #437 6871203367).
 if(req.saved_before){if(res.before_source!=='SAVED_REPLAYED'||res.before_result_hash!==req.saved_before.result_hash||pg.before_result_hash!==req.saved_before.result_hash)return{state:'REFUSED',code:'BEFORE_SOURCE'};}
 else if(res.before_source!=='RECOMPUTED')return{state:'REFUSED',code:'BEFORE_SOURCE'};
 if(anchors&&(!same(pg.evaluation,anchors.evaluation)||!same(pg.reference,anchors.reference)||!same(sv.evaluation,anchors.evaluation)||!same(sv.reference,anchors.reference)))return{state:'INPUT_MISMATCH'};
 return{state:'SHOWN'};}
// A later page of the same preview (same source hash) only.
// expected: the offset asked for (the rows shown so far); a page that starts elsewhere or overruns the row count is a gap, never appended.
function pageAnswer(first,res,expected){if(!isObj(res)||res.ok!==true||!isObj(res.page))return{state:'REFUSED',code:res&&res.code||'PAGE_SHAPE'};
 const p=res.page;if(p.source_preview_hash!==first.source_preview_hash)return{state:'LATE_ANSWER'};
 if(expected!==undefined&&(p.offset!==expected||!Array.isArray(p.rows)||p.offset+p.rows.length>first.row_count||p.row_count!==first.row_count||(p.next_offset!==null&&p.next_offset!==p.offset+p.rows.length)))return{state:'PAGE_GAP'};
 return{state:'SHOWN'};}
// A saved record against the inputs of this route: the same evaluation / reference identities, or it is not this input's record.
function savedMatches(sv,anchors){return!!(sv&&anchors&&same(sv.evaluation,anchors.evaluation)&&same(sv.reference,anchors.reference));}
const TRANSITION=Object.freeze({COMMON:'',NEWLY_COMPUTABLE:'새로 산출',LOST:'미산출로 바뀜',UNAVAILABLE_BOTH:'전후 모두 없음'});
// Before / after as the engine projected them (never re-scored or re-ranked here).
function compare(pg){return freeze({population:pg.population_effect,scope:pg.effect_scope,coverage:{before:pg.before_coverage,after:pg.after_coverage},row_count:pg.row_count,
 rows:pg.rows.map(r=>({company_id:r.company_id,issuer_id:r.issuer_id,axes:r.axes,before:r.before,after:r.after})),
 versions:{evaluation:pg.evaluation.input_hash,reference:pg.reference.input_hash,classification:pg.evaluation.classification_version,before:pg.before_result_hash,after:pg.after_result_hash,
  calculated_at:pg.after_calculated_at,preview:pg.source_preview_hash}});}
const STAGES=Object.freeze([['denominator','원래 분모(발행사)'],['axes.Q','Q 축'],['axes.G','G 축'],['axes.V','V 축'],['joint','세 축 모두'],['all15','15역할 모두 충족'],
 ['gate_known','관문 판정 가능'],['gate_pass','관문 통과'],['total','총점(부분 합계 포함)'],['eligible_total','완전 총점(순위·95% 분자)']]);
function stages(cov){const g=(o,p)=>p.split('.').reduce((x,k)=>x&&x[k],o);return freeze(STAGES.map(([k,l])=>({key:k,label:l,value:g(cov,k)})).concat([{key:'target',label:'95% 목표',value:cov.target}]));}
// Role deciles: the engine's decile per row (qgv555_role), counted D1..D10 (D10 = top); never a top-N list in place of the bands.
function deciles(ans){const bands=Array(10).fill(0);let valid=0,other=0;
 for(const x of ans.rows){if(x.decile_status==='VALID'&&Number.isInteger(x.decile)&&x.decile>=1&&x.decile<=10){bands[x.decile-1]++;valid++;}else other++;}
 return freeze({role:ans.role,bands,valid,other,n:ans.n});}
// Company detail: the engine's after row (qgv555_detail) and, from the preview page, the three weights per metric.
function detail(row,pageRow){if(!isObj(row))return null;const W=pageRow&&pageRow.after?pageRow.after.weights:[];
 return freeze({company_id:row.company_id,issuer_id:row.issuer_id,total:row.total,partial:row.partial_total,rank:row.rank,rank_n:row.rank_n,gate:row.gate_status,complete:row.fifteen_roles_complete,active:row.active_roles,
  axes:AXES.map(a=>({axis:a,score:row.axes[a].score,state:row.axes[a].state,roles:Object.entries(row.roles).filter(([k])=>k[0]===a.toLowerCase()).map(([k,x])=>({role:k,name:roleText(k),score:x.score,rank:x.rank,rank_n:x.rank_n,decile:x.decile,decile_status:x.decile_status,selected:x.selected,partial:x.partial,
   metrics:x.metrics.map(m=>({metric:m.metric,raw_status:m.raw_status,score:m.score,reason:m.reason,reference_n:m.reference_n,reference_scope:m.reference_scope,weight:m.weight,flags:flagsOf(m),substitute_for:substituteOf(m),
    w:W.find(l=>l.role===k&&l.metric===m.metric)||null}))}))})),families:row.input_family_contributions||{},flags:flagsOf(row)});}

/* ---- saved record (Main's projection of the engine's result for replay) */
function validateSaved(x){try{if(!isObj(x)||x.schema_version!==SCHEMA.SAVED||Object.keys(x).sort().join()!==[...SAVED_KEYS].sort().join())return{ok:false,code:'SAVED_SHAPE'};
 if(!isObj(x.configuration)||x.configuration.schema_version!==SCHEMA.CONFIG||!own(CANDIDATE_OF,x.configuration.model_id)||!HEX.test(String(x.result_hash)))return{ok:false,code:'SAVED_CONFIG'};
 return{ok:true};}catch(_){return{ok:false,code:'SAVED_SHAPE'};}}

/* ---- Top500 view (Codex top500_view(): top500-view/1, an allowlisted authenticated research projection) */
const VIEW_KEYS=['schema_version','population_id','population_version','evaluation_day','input_cutoff','apply_at','status','denominator','target_count','selected_count','boundary_uncertain',
 'reasons','source_result_hash','visibility','public_publication_authorized','retained_confirmed_available','members','official','replace_official','view_hash'];
function checkView(x){if(!isObj(x)||x.schema_version!==SCHEMA.VIEW)fail('VIEW_SCHEMA');
 for(const k of Object.keys(x))if(!VIEW_KEYS.includes(k))fail('VIEW_KEY:'+k);// prices, market caps, evidence never reach the screen
 if(!own(SELECTION_TEXT,x.status)||x.official!==false||x.replace_official!==false||x.public_publication_authorized!==false)fail('VIEW_STATE');
 if(!DAY.test(x.evaluation_day)||!HEX.test(String(x.view_hash))||!HEX.test(String(x.source_result_hash))||!Array.isArray(x.members))fail('VIEW_SHAPE');
 const iss=new Set(),sec=new Set(),rk=new Set();for(const m of x.members){if(!Number.isInteger(m.selection_rank)||m.selection_rank<1||rk.has(m.selection_rank))fail('RANK_INVALID');
  if(iss.has(m.issuer_id))fail('ISSUER_DUPLICATE');if(sec.has(m.representative_security_id))fail('SECURITY_DUPLICATE');iss.add(m.issuer_id);sec.add(m.representative_security_id);rk.add(m.selection_rank);}
 if(x.status==='VALIDATED_RESEARCH_CANDIDATE'&&(x.members.length!==500||x.denominator!==500))fail('VIEW_COUNT');return freeze(copy(x));}
function populationView(key,v,kind){const P=POPULATIONS[key];if(!P)return null;
 if(key!=='top500')return freeze({key,label:P.label,text:P.text,state:'KNOWN',lines:[]});
 if(!v)return freeze({key,label:P.label,text:P.text,state:'NOT_DELIVERED',lines:['선정 결과 전달 전 · 실제 Top500 명부·가격·주식수 근거 미충족(계산 담당 보고)']});
 return freeze({key,label:P.label,text:P.text,state:v.status,lines:[
  SELECTION_TEXT[v.status]+' · '+(DATA_KIND_TEXT[kind]||''),
  v.reasons.length?'사유 '+v.reasons.map(r=>SELECTION_REASON[r]||r).join(' · ')+(v.retained_confirmed_available?' · 이전 정상본 유지(인증 경로)':' · 이전 정상본 없음'):'선정 사유 없음',
  '선정 기준일 '+v.evaluation_day+' · 적용 '+v.apply_at+' · 입력 마감 '+v.input_cutoff,
  '선정 '+v.selected_count+' 고유 발행사 · 복수 종류주 발행사 '+v.members.filter(m=>m.economic_class_count>1).length+'(합산)'+(v.boundary_uncertain?' · 500위 경계 불확실':''),
  '분모 '+(v.denominator===null?'확정 전(없음)':v.denominator)+' · 95% 목표 '+v.target_count+'/500 · 전체시장 분모 없음',
  '모집단 '+v.population_id+' · '+v.population_version+' · 선정 결과 '+v.source_result_hash.slice(0,12)+'… · 인증 연구 보기(공개 게시 권한 아님)',
  '시총 선정 순위(1~'+v.members.length+')는 QGV 순위가 아님 · 가격·시총은 보이지 않음']});}

/* ---- stored r2 delivery (보관 결과 읽기; Codex #537 qgv-555-delivery/1 staged by Main with the qgv-555-stage/1 receipt) */
const STORED_SCOPE=Object.freeze({universe504:'operating504',expanded:'held1057'});
const SCOPE_TEXT=Object.freeze({operating504:'운영504코드 / 501발행사 · 기존504',held1057:'보유 1057발행사 · 확장 연구(전체시장 아님)'});
const STORED_SCHEMA=Object.freeze({index:'qgv-555-delivery/1',group:'qgv-555-groups-part/1',detail:'qgv-555-detail/1',distribution:'qgv-555-distribution-part/1'});
const kindOf=n=>n==='index'?'index':n.startsWith('group-index-')?'group':n.startsWith('distribution-')?'distribution':'detail';
// stage / manifest / index read through the private Worker (raw = {bytes, body}); sha256: async bytes → hex.
async function checkStored({stage,manifest,index},{scope,sha256}){if(typeof sha256!=='function')fail('HASH_UNAVAILABLE');
 if(!isObj(stage)||stage.schema_version!=='qgv-555-stage/1'||stage.scope!==scope||stage.stored_result_only!==true||!HEX.test(String(stage.manifest_sha256))||!HEX.test(String(stage.index_sha256)))fail('STAGE');
 if(!isObj(stage.expected_evaluation)||!isObj(stage.expected_references))fail('STAGE_ANCHORS');
 if(!manifest||await sha256(manifest.bytes)!==stage.manifest_sha256)fail('MANIFEST_HASH');const M=manifest.body;
 if(M.schema_version!=='qgv-555-delivery-manifest/1'||!Array.isArray(M.files))fail('MANIFEST_SCHEMA');
 const files=new Map();for(const f of M.files){if(files.has(f.path))fail('MANIFEST_DUPLICATE');files.set(f.path,f);}
 const ie=files.get('index.json');if(!ie||!index||await sha256(index.bytes)!==ie.sha256||index.bytes.length!==ie.size||ie.sha256!==stage.index_sha256)fail('INDEX_HASH');
 const X=index.body;if(X.schema_version!==STORED_SCHEMA.index)fail('INDEX_SCHEMA');
 // Independent anchors: the stage receipt's identities were computed from the input files themselves (tools/stage_private_qgv555.py).
 if(!same(X.evaluation,stage.expected_evaluation))fail('EVALUATION_ANCHOR');
 const ids=Object.fromEntries(Object.entries(X.models||{}).map(([k,v])=>[k,v.model_id]));if(!same(ids,{'U1-555':MODELS['U1-555'].model_id,'S1-555':MODELS['S1-555'].model_id}))fail('MODELS');
 for(const[k,v]of Object.entries(X.models)){if(!same(v.bindings.reference,stage.expected_references[k]))fail('REFERENCE_ANCHOR:'+k);if(!same(v.bindings.evaluation,stage.expected_evaluation))fail('EVALUATION_BINDING:'+k);}
 if(X.groups_layout==='SHARDED'?(!Array.isArray(X.group_files)||X.groups.length!==0):!Array.isArray(X.groups))fail('GROUP_LAYOUT');
 return freeze({scope,stage:copy(stage),files:Object.fromEntries(files),index:copy(X)});}
// One member file read later: its bytes must be the manifest's, its schema its kind's; a detail names this model's result.
async function checkStoredFile(st,name,raw,sha256){const e=st.files[name+'.json'];if(!e)fail('NOT_IN_MANIFEST');
 if(!raw||raw.bytes.length!==e.size||await sha256(raw.bytes)!==e.sha256)fail('MEMBER_HASH');const b=raw.body,k=kindOf(name);
 if(b.schema_version!==STORED_SCHEMA[k])fail('MEMBER_SCHEMA');
 if(k==='group'&&b.evaluation_input_hash!==st.index.evaluation.input_hash)fail('GROUP_CONTEXT');
 if(k==='detail'){const key=name.slice(0,6),m=st.index.models[key];if(!m||b.model_id!==m.model_id||b.result_hash!==m.result_hash)fail('DETAIL_RESULT');}
 return b;}
// Group files: all of them, together (count and duplicates as Codex read_groups()).
function storedGroups(st,parts){const X=st.index;if(X.groups_layout!=='SHARDED')return X.groups;if(parts.length!==X.group_files.length)fail('GROUP_FILES');
 const g=parts.flatMap(p=>p.rows);if(g.length!==X.groups_count||new Set(g.map(x=>x.group_id)).size!==g.length)fail('GROUP_MEMBERS');return g;}
function storedBoard(st,key){const m=st.index.models[key],e=st.index.evaluation;
 return freeze({key,model_id:m.model_id,result_hash:m.result_hash,calculated_at:m.calculated_at,config_hash:m.bindings.configuration_hash,coverage:m.coverage,
  files:m.files,lines:['보관 결과 · 생산자 '+st.stage.producer_sha.slice(0,8)+' 실행 · 계산 '+m.calculated_at+' · 이 화면에서 재계산 아님',
   SCOPE_TEXT[st.scope]+' · 평가일 '+e.evaluation_day+' · 입력 마감 '+e.input_cutoff,
   '평가 입력 '+e.input_hash.slice(0,12)+'… · 참조 입력 '+m.bindings.reference.input_hash.slice(0,12)+'… · 둘 다 원입력에서 따로 계산한 기준과 같음',
   '결과 '+m.result_hash.slice(0,12)+'… · 설정 '+m.bindings.configuration_hash.slice(0,12)+'… · 분류 '+e.classification_version+' · 전체시장 분모 없음']});}
function storedRows(detail){return detail.rows.map(r=>({company_id:r.company_id,Q:r.axes.Q.score,G:r.axes.G.score,V:r.axes.V.score,total:r.total,partial:r.partial_total,rank:r.rank,rank_n:r.rank_n,
 active:r.active_roles,complete:r.fifteen_roles_complete,gate:r.gate_status,status:r.status,flags:flagsOf(r)}));}
// Ranking scopes of one model's role groups (U1: COMMON; S1: one per SECTOR|TEMPLATE, never joined into one ranking).
function storedScopes(groups,model,role){return groups.filter(x=>x.model===model&&x.kind==='roles'&&x.role===role).map(x=>x.ranking_scope);}
function storedDeciles(groups,model,role,scope){const g=groups.find(x=>x.model===model&&x.kind==='roles'&&x.role===role&&(scope===undefined||x.ranking_scope===scope));if(!g)return null;
 const bands=Array(10).fill(0);for(const b of g.bins)if(Number.isInteger(b.decile)&&b.decile>=1&&b.decile<=10)bands[b.decile-1]=b.count;
 return freeze({role,bands,valid:g.evaluation_valid_n,n:g.original_code_rows,scope:g.ranking_scope,ties:Array.isArray(g.tie_splits)?g.tie_splits.length:0});}

/* ---- 2.1 pair state (no result of another model or population under the chosen name) */
function boardState(pop,model,{officialLoaded=false,saved=null,selection=null}={}){
 if(!own(POPULATIONS,pop)||!own(MODELS,model))return freeze({state:'UNKNOWN',text:'알 수 없는 선택'});
 if(model==='OFFICIAL'){if(pop==='universe504')return freeze({state:officialLoaded?'SHOWN':'LOADING',text:officialLoaded?'기존 공식 QGV · 기존504':'기존 공식 QGV 불러오는 중'});
  return freeze({state:'NO_RESULT',text:pop==='top500'?'기존 공식 QGV는 기존504에서만 계산됨 · 시총 Top500 공식 결과 없음':'확장 연구 모집단에는 공식 QGV 없음'});}
 if(model==='MY')return freeze({state:saved?'SAVED_SYNTHETIC':'NO_SAVED',text:saved?'내 설정 저장됨('+CANDIDATE_OF[saved.configuration.model_id]+' · 합성 입력 결과) · 이 모집단의 실자료 결과 전달 전':'저장된 555 설정 없음 · 2.2.7에서 재계산한 뒤 저장'});
 const tp=pop==='top500'?(selection?' · 선정 '+(selection.status==='VALIDATED_RESEARCH_CANDIDATE'?'검증된 연구 후보':'미확정 후보')+'(합성)':' · 실제 Top500 미선정'):'';
 if(pop==='top500')return freeze({state:'RESULT_NOT_DELIVERED',text:MODELS[model].label+' · 시총 Top500 결과 없음'+tp+' · 다른 모집단 결과를 이 이름으로 보이지 않음'});
 return freeze({state:'STORED_AVAILABLE',text:MODELS[model].label+' · '+SCOPE_TEXT[STORED_SCOPE[pop]]+' · 보관 결과(계산 담당 실자료 r2)는 아래에서 로그인 뒤 불러옴 · 이 화면에서 재계산 아님 · 다른 모형 결과를 이 이름으로 보이지 않음'});}

return Object.freeze({SCHEMA,AXES,ROLE_TEXT,POPULATIONS,MODELS,CANDIDATE_OF,KIND_TEXT,TEMPLATE_TEXT,GATE_TEXT,REASON_TEXT,SELECTION_TEXT,DATA_KIND_TEXT,
 checkContext,canonical,roleText,templateOf,sectorOf,scopes,recipeLine,start,rolesOf,axisOf,setAxis,setRole,excludeRole,setMetric,blocked,addMetric,removeMetric,replaceMetric,
 restore,restoreScope,FLAG_TEXT,flagsOf,activeCount,problems,sums,families,card,search,previewAnswer,pageAnswer,savedMatches,TRANSITION,STORED_SCOPE,SCOPE_TEXT,checkStored,checkStoredFile,storedGroups,storedBoard,storedRows,storedScopes,storedDeciles,compare,stages,deciles,detail,validateSaved,checkView,populationView,boardState,pct,score});
});
