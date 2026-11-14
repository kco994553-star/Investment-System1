/* QGV 555 · 시총 Top500 · 사용자 설정 (IS2.qgv555; owner 2026-11-14 「Top500 전환·QGV 555·사용자 설정 구현」, DC-49).
   Pure: no window, no request, no storage; runs in node as in the page.
   - Populations (2.1): 기존504 / 시총 Top500 / 확장 연구 — three separate identities, never one renamed into another. The Top500
     population (qgv-top500-population/1, name proposed to Codex #437 6868375798) is checked here: one issuer per member (share
     classes never counted twice), one representative security each, ranks 1..n without a gap, the members hash over the members as
     written, its two basis dates. Without the producer's completeness evidence it is said 「자료가 있는 기업 중 상위 500(전체시장
     Top500 확정 아님)」, never "the" Top500. The selection rank is not a QGV rank; no price or exact market cap is shown.
   - Models (2.1 / 2.2.7): 기존 공식 / U1-555 통합 / S1-555 섹터 / 내 설정, separate ids from the reduced U1/U2/S1 and the stopped
     3/3/3 candidates. 555 = five evaluation ROLES per axis (several raw factors in one role are still one role).
   - Catalog / presets (qgv-555-catalog/1, qgv-555-preset/1, proposed): checked as written; the five roles per axis come from the
     catalog (G / V roles are the producer's to define; the synthetic examples carry Main's unconfirmed proposal).
   - Editor of one preset-shaped setting: axis / role / factor shares (basis points), add (a second factor in a role splits that role's
     budget, the role's total never grows), remove, replace, period / formula variant, composite internal weight within its bounds,
     exclude / include a role (active count Q3/G4/V5), restore = the setting's own base preset id / version / scope. A scope is one
     SECTOR|TEMPLATE (S1) or COMMON (U1): nothing is copied to another template (은행 → 보험·REIT never automatic).
   - Display only: sums while editing, nominal weight = axis × role × factor share of the SETTING (설정값의 곱; never a missing-value
     redistribution or a post-gate contribution — those are the engine's answer), input families across roles / axes (shown, never
     penalised or hidden-adjusted), factor cards. Scores, ranks, effective weights, coverage: the engine's only; while its 555
     operation is not delivered the preview says so and shows nothing under the new name. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else{const I=root.IS2=root.IS2||{};I.qgv555=api;}})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
const SCHEMA=Object.freeze({POPULATION:'qgv-top500-population/1',CATALOG:'qgv-555-catalog/1',PRESET:'qgv-555-preset/1',PRESETS:'qgv-555-presets/1',CONFIG:'qgv-555-user-config/1'});
const AXES=Object.freeze(['Q','G','V']),ROLES_PER_AXIS=5,BP=10000;
const DAY=/^\d{4}-\d{2}-\d{2}$/,HEX=/^[0-9a-f]{64}$/;
const POPULATIONS=Object.freeze({
 universe504:Object.freeze({label:'기존504',text:'Universe504 · S&P 500 구성에서 출발해 고정한 504코드 · 시총 순위로 고른 목록 아님',official:true}),
 top500:Object.freeze({label:'시총 Top500',text:'시가총액 상위 500 고유 발행사(종류주 합산·중복 집계 없음) · 기존504와 다른 모집단',official:false}),
 expanded:Object.freeze({label:'확장 연구',text:'확장 연구 표본 · 전체시장 아님 · 운영 결과 아님',official:false})});
const MODELS=Object.freeze({
 OFFICIAL:Object.freeze({label:'기존 공식',kind:'OFFICIAL',model_id:null,preset_id:null}),
 'U1-555':Object.freeze({label:'U1-555 통합',kind:'COMMON',model_id:'unified-555/0.1.0',preset_id:'qgv-555-unified-default/0.1.0'}),
 'S1-555':Object.freeze({label:'S1-555 섹터',kind:'SECTOR',model_id:'sector-555/0.1.0',preset_id:'qgv-555-sector-default/0.1.0'}),
 MY:Object.freeze({label:'내 설정',kind:'USER',model_id:null,preset_id:null})});
const MODEL_OF_ID=Object.freeze(Object.fromEntries(Object.entries(MODELS).filter(([,m])=>m.model_id).map(([k,m])=>[m.model_id,k])));
const KIND_TEXT=Object.freeze({COMMON:'통합 · 모든 평가 기업에 같은 공통 요소와 같은 참조집단',SECTOR:'섹터 · 그 섹터·회계모형의 요소 · 섹터 점수를 이어 붙인 통합 순위 아님'});
const TEMPLATE_TEXT=Object.freeze({GENERAL:'일반',BANK:'은행',INSURANCE:'보험',BROKER:'증권',MORTGAGE_REIT:'모기지 REIT',ASSET_MANAGER:'자산운용',EQUITY_REIT:'지분형 REIT'});
const STATUS_TEXT=Object.freeze({IMPLEMENTED:'계산 구현됨',PENDING_DEFINITION:'계산 준비 중(정의 확정 전) · 선택 불가',NOT_FIT:'이 회계모형에 적용 부적합 · 선택 불가'});
const DIRECTION_TEXT=Object.freeze({HIGHER:'높을수록 좋음',LOWER:'낮을수록 좋음(점수는 좋은 쪽이 높게)'});
const FAMILY_TEXT=Object.freeze({net_income:'순이익',forecast_eps:'예상 EPS',operating_income:'영업이익',revenue:'매출',gross_profit:'매출총이익',cfo:'영업현금흐름',
 book_equity:'보통주 자본',debt:'차입금',shareholder_payout:'주주환원',reit_ffo:'REIT FFO',operating_assets:'영업자산'});
const PERIOD_TEXT=Object.freeze({TTM:'최근 12개월',LATEST_QUARTER:'최근 분기말',FY:'회계연도',FY1:'다음 회계연도 전망',FY_1Y:'회계연도 1년',FY_3Y:'회계연도 3년',FY_5Y:'회계연도 5년',
 NTM:'향후 12개월 전망',ONE_YEAR:'1년',UNRESOLVED:'기간 미정'});
const FORMULA_TEXT=Object.freeze({ratio:'비율',ratio_average:'평균 분모 비율',difference:'차이',difference_average:'평균 분모 차이',difference_ratio:'차이 비율',sum:'합',sum_ratio:'합의 비율',
 one_minus_ratio:'1 − 비율',cagr3:'3년 연평균 성장률',cagr5:'5년 연평균 성장률',growth1:'1년 성장률',positive_growth_share:'성장한 해의 비율',peg:'PEG',composite:'복합',pending:'정의 확정 전'});
const UNIT_TEXT=Object.freeze({decimal:'소수',multiple:'배수'});
const word=(T,v)=>own(T,v)?T[v]:String(v).toLowerCase().replace(/_/g,' ');
const DATA_KIND_TEXT=Object.freeze({SYNTHETIC:'합성 자료',PRIVATE:'비공개 실자료',PUBLIC:'공개'});

class Refusal extends Error{constructor(code,path){super(code);this.code=code;this.path=path;}}
const refuse=(c,p)=>{throw new Refusal(c,p);};
const isObj=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
const own=(o,k)=>Object.prototype.hasOwnProperty.call(o,k);
const int=v=>Number.isInteger(v);
const bp=v=>int(v)&&v>=0&&v<=BP;
const copy=v=>JSON.parse(JSON.stringify(v));
const freeze=v=>{if(v&&typeof v==='object'){Object.freeze(v);for(const k of Object.keys(v))freeze(v[k]);}return v;};
function canonical(v){if(Array.isArray(v))return'['+v.map(canonical).join(',')+']';
 if(isObj(v))return'{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canonical(v[k])).join(',')+'}';return JSON.stringify(v);}
const wrap=fn=>async(...a)=>{try{return{ok:true,value:await fn(...a)};}catch(e){if(e instanceof Refusal)return{ok:false,code:e.code,path:e.path};throw e;}};
const wrapSync=fn=>(...a)=>{try{return{ok:true,value:fn(...a)};}catch(e){if(e instanceof Refusal)return{ok:false,code:e.code,path:e.path};throw e;}};

/* ---- Top500 population */
const POP_KEYS=['schema_version','data_kind','contract_state','population_id','version','unit','n','selection_date','effective_date','shares_basis_date','price_basis_date',
 'candidate_count','missing_mcap_count','boundary','candidate_pool_complete','candidate_pool_basis','previous','changes','members_hash','members'];
const checkPopulation=wrap(async(x,sha256)=>{if(typeof sha256!=='function')refuse('HASH_UNAVAILABLE','$');
 if(!isObj(x))refuse('SCHEMA','$');for(const k of POP_KEYS)if(!own(x,k))refuse('KEY_MISSING',k);for(const k of Object.keys(x))if(!POP_KEYS.includes(k))refuse('KEY_UNKNOWN',k);
 if(x.schema_version!==SCHEMA.POPULATION)refuse('SCHEMA','schema_version');if(!own(DATA_KIND_TEXT,x.data_kind))refuse('DATA_KIND','data_kind');
 if(x.unit!=='ISSUER')refuse('POPULATION_UNIT','unit');if(!int(x.n)||x.n<1)refuse('TYPE','n');
 for(const k of['selection_date','effective_date','shares_basis_date','price_basis_date'])if(!DAY.test(String(x[k])))refuse('DATE_INVALID',k);
 if(x.shares_basis_date>x.selection_date||x.price_basis_date>x.selection_date||x.effective_date<x.selection_date)refuse('DATE_ORDER','selection_date');
 if(!int(x.candidate_count)||!int(x.missing_mcap_count)||x.candidate_count<x.n||x.missing_mcap_count<0)refuse('TYPE','candidate_count');
 if(typeof x.candidate_pool_complete!=='boolean'||typeof x.candidate_pool_basis!=='string'||!x.candidate_pool_basis)refuse('TYPE','candidate_pool_complete');
 if(!Array.isArray(x.members)||x.members.length!==x.n)refuse('MEMBER_COUNT','members');
 const issuers=new Set(),secs=new Set();
 x.members.forEach((m,i)=>{const at='members['+i+']';if(!isObj(m)||typeof m.issuer_id!=='string'||typeof m.representative_security_id!=='string'||!int(m.selection_rank)||!int(m.share_classes)||m.share_classes<1)refuse('TYPE',at);
  if(issuers.has(m.issuer_id))refuse('ISSUER_DUPLICATE',at+'.issuer_id');issuers.add(m.issuer_id);
  if(secs.has(m.representative_security_id))refuse('SECURITY_DUPLICATE',at+'.representative_security_id');secs.add(m.representative_security_id);
  if(m.selection_rank!==i+1)refuse('RANK_GAP',at+'.selection_rank');});
 if(!HEX.test(String(x.members_hash))||await sha256(new TextEncoder().encode(canonical(x.members)))!==x.members_hash)refuse('MEMBERS_HASH_MISMATCH','members_hash');
 if(x.previous!==null&&(!isObj(x.previous)||typeof x.previous.population_id!=='string'||!HEX.test(String(x.previous.members_hash))))refuse('TYPE','previous');
 return freeze(copy(x));});
// One population's header lines; checked: a checked Top500 population or null (계약 전 / 불러오기 전).
function populationView(key,checked){const P=POPULATIONS[key];if(!P)return null;
 if(key!=='top500')return freeze({key,label:P.label,text:P.text,state:'KNOWN',lines:[]});
 if(!checked)return freeze({key,label:P.label,text:P.text,state:'NOT_DELIVERED',lines:['모집단 계약·전달 전 · 계산 담당 확정 전(qgv-top500-population/1 제안)']});
 const x=checked;
 return freeze({key,label:P.label,text:P.text,state:x.candidate_pool_complete?'COMPLETE':'POOL_UNPROVEN',data_kind:x.data_kind,lines:[
  (x.candidate_pool_complete?'후보 풀 완전성 근거 있음 · 시총 상위 '+x.n:'자료가 있는 기업 중 상위 '+x.n+'(전체시장 Top500 확정 아님)')+' · '+DATA_KIND_TEXT[x.data_kind],
  '선정 기준일 '+x.selection_date+' · 적용일 '+x.effective_date+' · 주식수 기준일 '+x.shares_basis_date+' · 가격 기준일 '+x.price_basis_date,
  x.n+' 고유 발행사 · 대표 증권 '+x.n+' · 복수 종류주 발행사 '+x.members.filter(m=>m.share_classes>1).length+'(합산, 중복 집계 없음)',
  '후보 '+x.candidate_count+' · 시총 결손 '+x.missing_mcap_count+(isObj(x.boundary)&&int(x.boundary.rank_500_missing_neighbours)?' · 500위 경계 ±'+x.boundary.window+' 안 결손 '+x.boundary.rank_500_missing_neighbours:''),
  '모집단 '+x.population_id+' · '+x.version+' · 구성원 해시 '+x.members_hash.slice(0,12)+'…',
  '시총 선정 순위(1~'+x.n+')는 QGV 순위가 아님 · 가격·정확한 시총은 보이지 않음']});}

/* ---- catalog / presets */
function checkCatalogBody(x){if(!isObj(x)||x.schema_version!==SCHEMA.CATALOG)refuse('SCHEMA','catalog.schema_version');if(!own(DATA_KIND_TEXT,x.data_kind))refuse('DATA_KIND','catalog.data_kind');
 if(!isObj(x.roles))refuse('TYPE','catalog.roles');
 for(const a of AXES){const rs=x.roles[a];if(!Array.isArray(rs)||rs.length!==ROLES_PER_AXIS)refuse('ROLES_NOT_FIVE','catalog.roles.'+a);
  if(new Set(rs.map(r=>r&&r.role_id)).size!==ROLES_PER_AXIS||rs.some(r=>!isObj(r)||typeof r.role_id!=='string'||typeof r.name!=='string'||typeof r.economic_role!=='string'))refuse('ROLES_INVALID','catalog.roles.'+a);}
 if(!Array.isArray(x.factors)||!x.factors.length)refuse('TYPE','catalog.factors');
 const ids=new Set(),alias=new Map();
 x.factors.forEach((f,i)=>{const at='catalog.factors['+i+']';
  if(!isObj(f)||typeof f.variant_id!=='string'||ids.has(f.variant_id))refuse('FACTOR_INVALID',at);ids.add(f.variant_id);
  if(!AXES.includes(f.axis)||!x.roles[f.axis].some(r=>r.role_id===f.role_id))refuse('FACTOR_ROLE_UNKNOWN',at+'.role_id');
  if(!own(STATUS_TEXT,f.calculator_status)||f.calculator_status==='NOT_FIT')refuse('FACTOR_STATUS',at+'.calculator_status');
  if(!Array.isArray(f.scope)||!f.scope.length||!Array.isArray(f.aliases)||!Array.isArray(f.input_families)||typeof f.alias_group!=='string')refuse('FACTOR_INVALID',at);
  for(const n of[f.variant_id,...f.aliases]){const k=String(n).toLowerCase();if(alias.has(k)&&alias.get(k)!==f.alias_group)refuse('ALIAS_AMBIGUOUS',at+'.aliases');alias.set(k,f.alias_group);}});
 for(const f of x.factors)if(f.composite!==null){const c=f.composite;if(!isObj(c)||!Array.isArray(c.components)||c.components.length<2)refuse('COMPOSITE_INVALID',f.variant_id);
  let sum=0;for(const p of c.components){const g=x.factors.find(y=>y.variant_id===p.variant_id);
   if(!g||g.axis!==f.axis||g.composite!==null)refuse('COMPOSITE_COMPONENT',f.variant_id+'.'+p.variant_id);
   if(![p.min_weight,p.default_weight,p.max_weight].every(bp)||!(p.min_weight<=p.default_weight&&p.default_weight<=p.max_weight))refuse('COMPOSITE_BOUNDS',f.variant_id+'.'+p.variant_id);sum+=p.default_weight;}
  if(sum!==BP)refuse('COMPOSITE_BOUNDS',f.variant_id);}
 return x;}
function templateOf(scope){return scope==='COMMON'?'GENERAL':String(scope).split('|')[1];}
function checkPresetBody(p,cat){const at='preset';if(!isObj(p)||p.schema_version!==SCHEMA.PRESET)refuse('SCHEMA',at+'.schema_version');
 const key=MODEL_OF_ID[p.model_id];if(!key)refuse('MODEL_UNKNOWN',at+'.model_id');if(p.preset_id!==MODELS[key].preset_id)refuse('PRESET_UNKNOWN',at+'.preset_id');
 if(typeof p.version!=='string'||typeof p.scope!=='string')refuse('TYPE',at);
 if((MODELS[key].kind==='COMMON')!==(p.scope==='COMMON')||(p.scope!=='COMMON'&&!/^[A-Z_]+\|[A-Z_]+$/.test(p.scope)))refuse('SCOPE_INVALID',at+'.scope');
 sumsOrRefuse(p,cat,at);return p;}
function sumsOrRefuse(c,cat,at){const s=sums(c,cat);if(s.problems.length)refuse(s.problems[0].code,at+'.'+s.problems[0].path);}
const checkBundle=wrapSync((catalog,presets)=>{const cat=checkCatalogBody(catalog);
 if(!isObj(presets)||presets.schema_version!==SCHEMA.PRESETS||!Array.isArray(presets.presets)||!presets.presets.length)refuse('SCHEMA','presets');
 const seen=new Set();for(const p of presets.presets){checkPresetBody(p,cat);const k=p.preset_id+'@'+p.version+'@'+p.scope;if(seen.has(k))refuse('PRESET_DUPLICATE',k);seen.add(k);}
 return freeze({catalog:copy(cat),presets:copy(presets.presets),data_kind:cat.data_kind,contract_state:cat.contract_state||null});});

/* ---- editor (pure; every function returns a new setting) */
const factorOf=(cat,v)=>cat.factors.find(f=>f.variant_id===v)||null;
function selectable(f,scope){if(!f)return{ok:false,code:'FACTOR_UNKNOWN'};if(f.calculator_status!=='IMPLEMENTED')return{ok:false,code:'PENDING_DEFINITION'};
 if(!f.scope.includes(templateOf(scope)))return{ok:false,code:'NOT_FIT'};return{ok:true,code:null};}
// Alternatives for a factor that cannot be chosen here: implemented, applicable factors of the same role.
function alternatives(cat,f,scope){return cat.factors.filter(g=>g!==f&&g.axis===f.axis&&g.role_id===f.role_id&&selectable(g,scope).ok).map(g=>g.variant_id);}
function split(total,n){const base=Math.floor(total/n),out=Array(n).fill(base);for(let i=0;i<total-base*n;i++)out[i]+=1;return out;}
function evenShares(r){const ks=Object.keys(r.factors);const sh=split(BP,ks.length||1);r.factors=Object.fromEntries(ks.map((k,i)=>[k,sh[i]]));}
function start(preset){if(!isObj(preset)||preset.schema_version!==SCHEMA.PRESET)throw Error('PRESET_REQUIRED');
 return freeze({schema_version:SCHEMA.CONFIG,model_id:preset.model_id,base:{preset_id:preset.preset_id,version:preset.version,scope:preset.scope},scope:preset.scope,
  axis_weights:copy(preset.axis_weights),axes:copy(preset.axes),composites:{}});}
const edit=(c,fn)=>{const o=copy(c);fn(o);return freeze(o);};
const roleOf=(c,axis,role)=>{const r=c.axes[axis]&&c.axes[axis][role];if(!r)throw Error('ROLE_UNKNOWN');return r;};
function setAxis(c,axis,v){if(!AXES.includes(axis)||!bp(v))throw Error('WEIGHT_INVALID');return edit(c,o=>{o.axis_weights[axis]=v;});}
function setRole(c,axis,role,v){if(!bp(v))throw Error('WEIGHT_INVALID');roleOf(c,axis,role);return edit(c,o=>{o.axes[axis][role].weight=v;});}
// Excluding a role makes its weight 0 (the user then balances the remaining roles); its factors stay for include().
function excludeRole(c,axis,role){roleOf(c,axis,role);return edit(c,o=>{o.axes[axis][role].weight=0;});}
function setShare(c,axis,role,variant,v){if(!bp(v))throw Error('WEIGHT_INVALID');const r=roleOf(c,axis,role);if(!own(r.factors,variant))throw Error('FACTOR_NOT_SELECTED');
 return edit(c,o=>{o.axes[axis][role].factors[variant]=v;});}
function selectedAliases(c,cat){const out=new Map();for(const a of AXES)for(const r of Object.keys(c.axes[a]))for(const v of Object.keys(c.axes[a][r].factors)){const f=factorOf(cat,v);if(f)out.set(f.alias_group,v);}return out;}
// Adding a factor to a role splits that role's budget evenly among its factors; the role's weight is unchanged.
function addFactor(c,cat,variant){const f=factorOf(cat,variant);const s=selectable(f,c.scope);if(!s.ok)throw Error(s.code);
 if(selectedAliases(c,cat).has(f.alias_group))throw Error('ALIAS_DUPLICATE');
 return edit(c,o=>{const r=o.axes[f.axis][f.role_id];r.factors[variant]=0;evenShares(r);if(f.composite)o.composites[variant]=Object.fromEntries(f.composite.components.map(p=>[p.variant_id,p.default_weight]));});}
function removeFactor(c,axis,role,variant){const r=roleOf(c,axis,role);if(!own(r.factors,variant))throw Error('FACTOR_NOT_SELECTED');
 return edit(c,o=>{delete o.axes[axis][role].factors[variant];evenShares(o.axes[axis][role]);delete o.composites[variant];});}
function replaceFactor(c,cat,from,to){const f=factorOf(cat,from),g=factorOf(cat,to);if(!f||!g)throw Error('FACTOR_UNKNOWN');if(f.axis!==g.axis||f.role_id!==g.role_id)throw Error('FACTOR_ROLE_MISMATCH');
 const s=selectable(g,c.scope);if(!s.ok)throw Error(s.code);const r=roleOf(c,f.axis,f.role_id);if(!own(r.factors,from))throw Error('FACTOR_NOT_SELECTED');
 const al=selectedAliases(c,cat);if(al.has(g.alias_group)&&al.get(g.alias_group)!==from)throw Error('ALIAS_DUPLICATE');
 return edit(c,o=>{const rr=o.axes[f.axis][f.role_id],share=rr.factors[from];delete rr.factors[from];rr.factors[to]=share;delete o.composites[from];
  if(g.composite)o.composites[to]=Object.fromEntries(g.composite.components.map(p=>[p.variant_id,p.default_weight]));});}
// A registered period / formula variant of the same concept (variant_group) replaces the chosen one at the same share.
function chooseVariant(c,cat,from,to){const f=factorOf(cat,from),g=factorOf(cat,to);if(!f||!g||!f.variant_group||f.variant_group!==g.variant_group)throw Error('VARIANT_GROUP_MISMATCH');return replaceFactor(c,cat,from,to);}
function setComposite(c,cat,variant,component,v){const f=factorOf(cat,variant);if(!f||!f.composite||!own(c.composites,variant))throw Error('COMPOSITE_NOT_SELECTED');
 const p=f.composite.components.find(x=>x.variant_id===component);if(!p)throw Error('COMPOSITE_COMPONENT');if(!int(v)||v<p.min_weight||v>p.max_weight)throw Error('COMPOSITE_BOUNDS');
 return edit(c,o=>{o.composites[variant][component]=v;});}
// 기본값 복원: the setting's own base preset (id / version / scope), never a newer preset of the same name.
function restore(c,bundle){const b=c.base,p=bundle.presets.find(x=>x.preset_id===b.preset_id&&x.version===b.version&&x.scope===b.scope);if(!p)throw Error('BASE_PRESET_MISSING');return start(p);}
function presetFor(bundle,model,scope){const m=MODELS[model];if(!m||!m.preset_id)return null;return bundle.presets.find(p=>p.model_id===m.model_id&&p.scope===scope)||null;}
function scopesOf(bundle,model){const m=MODELS[model];return m&&m.model_id?bundle.presets.filter(p=>p.model_id===m.model_id).map(p=>p.scope):[];}

/* ---- display (setting values only) */
const activeRole=r=>r.weight>0&&Object.keys(r.factors).length>0;
function activeCount(c){const n={};for(const a of AXES)n[a]=Object.values(c.axes[a]).filter(activeRole).length;return freeze({...n,text:'Q'+n.Q+'/G'+n.G+'/V'+n.V});}
// Sum lines and the setting's problems (the engine's validation stays the authority).
function sums(c,cat){const problems=[],axis=AXES.reduce((t,a)=>t+c.axis_weights[a],0),roles={},factors={};
 if(!AXES.every(a=>bp(c.axis_weights[a])))problems.push({code:'WEIGHT_INVALID',path:'axis_weights'});
 if(axis!==BP)problems.push({code:'AXIS_SUM',path:'axis_weights'});
 for(const a of AXES){const rs=c.axes[a];if(!isObj(rs)||(cat&&cat.roles[a].some(r=>!own(rs,r.role_id)))||Object.keys(rs).length!==ROLES_PER_AXIS)problems.push({code:'ROLES_NOT_FIVE',path:'axes.'+a});
  roles[a]=Object.values(rs||{}).reduce((t,r)=>t+(bp(r.weight)?r.weight:0),0);if(c.axis_weights[a]>0&&roles[a]!==BP)problems.push({code:'ROLE_SUM',path:'axes.'+a});
  for(const[k,r]of Object.entries(rs||{})){const sh=Object.values(r.factors);factors[a+'.'+k]=sh.reduce((t,v)=>t+v,0);
   if(r.weight>0&&!sh.length)problems.push({code:'ROLE_EMPTY',path:'axes.'+a+'.'+k});
   if(sh.length&&factors[a+'.'+k]!==BP)problems.push({code:'FACTOR_SUM',path:'axes.'+a+'.'+k});
   if(cat)for(const v of Object.keys(r.factors)){const f=factorOf(cat,v);if(!f||f.axis!==a||f.role_id!==k)problems.push({code:'FACTOR_ROLE_UNKNOWN',path:'axes.'+a+'.'+k+'.'+v});
    else if(!selectable(f,c.scope).ok)problems.push({code:selectable(f,c.scope).code,path:'axes.'+a+'.'+k+'.'+v});}}}
 return freeze({axis,roles,factors,problems});}
// Nominal weight of each chosen factor in the total = axis × role × share of THIS SETTING (an exact fraction of 10^12).
function nominal(c){const out=[];for(const a of AXES)for(const[r,x]of Object.entries(c.axes[a]))for(const[v,s]of Object.entries(x.factors))
  out.push({axis:a,role_id:r,variant_id:v,numerator:c.axis_weights[a]*x.weight*s,denominator:BP*BP*BP});return out;}
const pct=(n,d)=>(Math.round(n/d*10000)/100).toFixed(2)+'%';
// Input families: the same information read in several roles / axes. Shown with the setting's summed nominal exposure; never penalised.
function overlap(c,cat){const by=new Map();for(const w of nominal(c)){const f=factorOf(cat,w.variant_id);if(!f)continue;
  for(const fam of f.input_families){const e=by.get(fam)||{family:fam,name:FAMILY_TEXT[fam]||fam,axes:new Set(),roles:new Set(),factors:[],numerator:0,denominator:w.denominator};
   e.axes.add(w.axis);e.roles.add(w.axis+'.'+w.role_id);e.factors.push(w.variant_id);e.numerator+=w.numerator;by.set(fam,e);}}
 return [...by.values()].map(e=>freeze({family:e.family,name:e.name,axes:[...e.axes].sort(),roles:[...e.roles].sort(),factors:e.factors,cross_axis:e.axes.size>1,shared:e.factors.length>1,
  exposure:pct(e.numerator,e.denominator)})).filter(e=>e.shared).sort((x,y)=>y.factors.length-x.factors.length||x.family.localeCompare(y.family));}
function roleName(cat,axis,role){const r=cat.roles[axis].find(x=>x.role_id===role);return r?r.name:role;}
// One factor card. c: the current setting (or null).
function card(cat,f,c){const scope=c?c.scope:'COMMON',s=selectable(f,scope),r=cat.roles[f.axis].find(x=>x.role_id===f.role_id);
 const chosen=c?Object.prototype.hasOwnProperty.call(c.axes[f.axis][f.role_id].factors,f.variant_id):false;
 const w=chosen?nominal(c).find(x=>x.variant_id===f.variant_id):null,role=c?c.axes[f.axis][f.role_id]:null;
 const fams=f.input_families.map(x=>FAMILY_TEXT[x]||x);
 const others=c?overlap(c,cat).filter(e=>e.factors.includes(f.variant_id)):[];
 return freeze({variant_id:f.variant_id,name:f.display_name,axis:f.axis,role:r?r.name:f.role_id,economic_role:r?r.economic_role:'',
  formula:word(FORMULA_TEXT,f.formula)+' · '+word(PERIOD_TEXT,f.period)+' · 단위 '+word(UNIT_TEXT,f.unit)+' · '+(DIRECTION_TEXT[f.direction]||f.direction),
  templates:f.scope.map(t=>TEMPLATE_TEXT[t]||t).join('·'),
  badges:[f.is_default?'기본값':null,f.recommended?'추천':null,chosen?'현재 선택':null].filter(Boolean),
  status:s.ok?STATUS_TEXT.IMPLEMENTED:STATUS_TEXT[s.code==='NOT_FIT'?'NOT_FIT':'PENDING_DEFINITION'],selectable:s.ok,
  alternatives:s.ok?[]:alternatives(cat,f,scope).map(v=>factorOf(cat,v).display_name),
  data:'자료 부족 여부는 엔진 답(커버리지)으로만 표시',evidence:(f.evidence_refs||[]).join(' · '),aliases:f.aliases,
  families:fams.length?'원입력 계열 '+fams.join('·'):'원입력 계열 없음(정의 확정 전)',
  overlap:others.map(e=>e.name+' 계열 '+e.factors.length+'개 · '+(e.cross_axis?'축을 넘음 ':'')+'합산 명목 '+e.exposure),
  weights:chosen?'역할 안 '+pct(role.factors[f.variant_id],BP)+' · 역할 '+pct(role.weight,BP)+' · 총점 명목 '+pct(w.numerator,w.denominator)+'(설정값의 곱 · 실효 비중은 엔진 답)':'선택 안 됨',
  composite:f.composite?f.composite.components.map(p=>p.variant_id+' '+pct(c&&c.composites[f.variant_id]?c.composites[f.variant_id][p.variant_id]:p.default_weight,BP)+' (허용 '+pct(p.min_weight,BP)+'~'+pct(p.max_weight,BP)+')'):null});}
function search(cat,q){const t=String(q||'').trim().toLowerCase();if(!t)return[];
 return cat.factors.filter(f=>[f.variant_id,f.display_name,...f.aliases].some(n=>String(n).toLowerCase().includes(t))).map(f=>f.variant_id);}

/* ---- 2.1 combination state (never another model's or population's result under the chosen name) */
function boardState(pop,model,{officialLoaded=false,savedConfig=null,population=null}={}){
 if(!own(POPULATIONS,pop)||!own(MODELS,model))return freeze({state:'UNKNOWN',text:'알 수 없는 선택'});
 if(model==='OFFICIAL'){if(pop==='universe504')return freeze({state:officialLoaded?'SHOWN':'LOADING',text:officialLoaded?'기존 공식 QGV · 기존504':'기존 공식 QGV 불러오는 중'});
  return freeze({state:'NO_RESULT',text:pop==='top500'?'기존 공식 QGV는 기존504에서만 계산됨 · 시총 Top500 공식 결과 없음':'확장 연구 모집단에는 공식 QGV 없음'});}
 if(model==='MY')return freeze({state:savedConfig?'ENGINE_PENDING':'NO_SAVED',text:savedConfig?'내 설정 '+activeCount(savedConfig).text+' · 이 모집단의 재계산 결과 전달 전(555 엔진 계약 전)':'저장된 555 설정 없음 · 2.2.7에서 만든 뒤 재계산'});
 const p=pop==='top500'&&!population?' · 모집단 계약 전':'';
 return freeze({state:'RESULT_NOT_DELIVERED',text:MODELS[model].label+' 결과 전달 전 · 모형 계약 제안 단계(계산 담당 확정 전)'+p+' · 다른 모형 결과를 이 이름으로 보이지 않음'});}

/* ---- engine (the 555 operation is not delivered; the screen says so and shows nothing under the new name) */
const PREVIEW_STATE=Object.freeze({ENGINE_CONTRACT_PENDING:'재계산 엔진 계약 전 · 555 미리보기 결과 없음(이전 결과를 이 설정 이름으로 보이지 않음)',
 ENGINE_NOT_CONNECTED:'계산 실행 경로 연결 전 · 이 사이트에는 엔진 경로가 없음',MODEL_MISMATCH:'답한 모형이 요청한 모형과 다름 · 쓰지 않음',LATE_ANSWER:'늦게 온 답 · 지금 설정의 답이 아님 · 쓰지 않음'});
function previewAnswer(req,res,current){if(!isObj(res))return{state:'ENGINE_NOT_CONNECTED'};if(res.request_id!==req.request_id||req!==current)return{state:'LATE_ANSWER'};
 if(res.ok!==true)return{state:res.code==='ENGINE_CONTRACT_PENDING'?'ENGINE_CONTRACT_PENDING':'ENGINE_NOT_CONNECTED',code:res.code||null};
 if(res.model_id!==req.model_id)return{state:'MODEL_MISMATCH'};return{state:'ENGINE_CONTRACT_PENDING'};}

return Object.freeze({SCHEMA,AXES,ROLES_PER_AXIS,POPULATIONS,MODELS,KIND_TEXT,TEMPLATE_TEXT,STATUS_TEXT,FAMILY_TEXT,PREVIEW_STATE,canonical,
 checkPopulation,populationView,checkBundle,templateOf,selectable,alternatives,start,setAxis,setRole,excludeRole,setShare,addFactor,removeFactor,replaceFactor,
 chooseVariant,setComposite,restore,presetFor,scopesOf,activeCount,sums,nominal,overlap,roleName,card,search,boardState,previewAnswer,pct});
});
