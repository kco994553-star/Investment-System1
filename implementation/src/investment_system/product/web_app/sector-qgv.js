/* Sector QGV reader and roll-up (IS2.sectorQgv; owner 2026-11-06, design "섹터별 QGV 요소 선택·추천·재계산" §5–§8; feature 2.2).
   Reads sector-qgv-bundle/1 as proposed in implementation/docs/frontend_v2/SECTOR_QGV_20261106.md (Main's screen-side proposal;
   Codex owns the factor dictionary, the factor formulas, the peer-group scores and the presets, DC-42) and the user's
   sector-qgv-user-config/1. It computes NO factor: every factor score (0–100, peer group of the company's book sector and
   accounting template) comes from the bundle's score matrix. What runs here is only the weighted roll-up the design fixes (§7.3):
   role = Σ factor score × factor bp / 10000, axis = Σ role × role bp / 10000, total = Σ axis × axis bp / 10000, under the strict
   missing rule (§8): a required factor (axis bp × role bp × factor bp > 0) without a score leaves its axis unscored and then the
   total and rank unscored; a 0-weight axis / role / factor is not required and the axis is shown as excluded by the user. No 0,
   no neutral fill, no substitute factor, no company-type (Lynch) weight: lynch_tags are carried for display and search only.
   - validate(bundle) → {ok, value} | {ok:false, code, path}: the whole bundle refused at its first fault (presets: bp integers,
     axis sum 10000, role sums 10000 inside an active axis, factor sums 10000 inside an active role, factors known / ready /
     applicable to the template; scores: one cell per company per ready factor, score only with a valid status).
   - validateConfig(config, value) / checkTree(tree, ctx, value): the same sums and factor checks for the user's edit.
   - compute(value, config) → one model's rows over the WHOLE original population (unmapped companies stay in the denominator),
     ranks only among computed rows of that one model; compare(before, after) joins two results of the same snapshot.
   - key(value, config): the cache / request key — snapshot, universe, engine, normalization, mapping and preset versions plus
     the canonical config; a result is shown only for the key it was computed for.
   - source() → Promise {state:'NONE'}: no public bundle and no request today.
   Pure except source(); runs in node as in the page. Nothing here stores or sends anything. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else{const I=root.IS2=root.IS2||{};I.sectorQgv=api;}})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
const SCHEMA='sector-qgv-bundle/1',CONFIG_SCHEMA='sector-qgv-user-config/1',PRESET_SET='sector-qgv-default';
const AXES=Object.freeze(['Q','G','V']),BP=10000;
const VALID=Object.freeze(['VALID','VALID_NEGATIVE']);
const MISSING=Object.freeze(['MISSING_INPUT','INSUFFICIENT_HISTORY','STALE','SCOPE_MISMATCH','PERIOD_MISMATCH','CURRENCY_MISMATCH','DOMAIN_INVALID',
 'NOT_APPLICABLE','PEER_SAMPLE_SMALL','MAPPING_UNRESOLVED']);
const EVIDENCE=Object.freeze({BOOK_SECTOR:'책의 해당 섹터 연구',QUANT_RESEARCH:'일반 퀀트 연구',ACCOUNTING_FIT:'회계 적합성',SELF_VALIDATED:'자체 검증'});
const REASON=Object.freeze({MISSING_INPUT:'입력 없음',INSUFFICIENT_HISTORY:'이력 부족',STALE:'자료 오래됨',SCOPE_MISMATCH:'귀속 범위 불일치',PERIOD_MISMATCH:'기간 불일치',
 CURRENCY_MISMATCH:'통화 불일치',DOMAIN_INVALID:'산식 정의역 밖',NOT_APPLICABLE:'이 회계모형에 적용 안 됨',PEER_SAMPLE_SMALL:'비교집단 표본 부족',
 MAPPING_UNRESOLVED:'섹터·회계모형 대응 미확인',NO_PRESET:'이 섹터·회계모형의 기본 설정 없음',AXIS_UNSCORED:'활성 축 미산출'});
const TEXT=Object.freeze({NONE:'섹터 QGV 자료가 아직 연결되지 않았습니다',NONE_WHY:'요소 사전·요소 점수·기본 설정은 Codex 계산 · sector-qgv-bundle/1 합의 뒤 연결 · 기존 공식 QGV는 그대로',
 SYNTHETIC:'합성 데이터 · 시험용 · 실제 재계산 아님',INITIAL:'기본값 · 초기 설정',VALIDATED:'기본값 · 검증됨',RECOMMENDED:'추천',SELECTED:'선택됨',
 PENDING:'계산 기능 준비 중',PARTIAL:'자료 일부 부족',NOT_FIT:'산식 적용 부적합',INVALID:'섹터 QGV 파일이 규격과 달라 파일 전체를 쓰지 않습니다',FAILED:'섹터 QGV 자료를 불러오지 못했습니다'});
const MAX=Object.freeze({factors:200,companies:20000,presets:500,recs:2000,text:300,id:64,list:40});
const ID=/^[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}$/,CODE=/^[A-Z][A-Z0-9_]{0,63}$/,DAY=/^\d{4}-\d{2}-\d{2}$/,VER=/^\d+\.\d+\.\d+$/;
const own=(o,k)=>Object.prototype.hasOwnProperty.call(o,k);
const isObj=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
function Refusal(code,path){this.code=code;this.path=path;}
const refuse=(code,path)=>{throw new Refusal(code,path);};
function keys(o,want,path,optional=[]){if(!isObj(o))refuse('TYPE',path);for(const k of want)if(!own(o,k))refuse('KEY_MISSING',path+'.'+k);
 for(const k of Object.keys(o))if(!want.includes(k)&&!optional.includes(k))refuse('KEY_UNKNOWN',path+'.'+k);}
const arr=(v,max,path)=>{if(!Array.isArray(v))refuse('TYPE',path);if(v.length>max)refuse('TOO_MANY',path);return v;};
const str=(v,path,max=MAX.text)=>{if(typeof v!=='string'||!v.trim()||v.length>max)refuse('TEXT_INVALID',path);return v;};
const id=(v,path)=>{if(typeof v!=='string'||!ID.test(v))refuse('ID_INVALID',path);return v;};
const code=(v,path)=>{if(typeof v!=='string'||!CODE.test(v))refuse('CODE_INVALID',path);return v;};
const bp=(v,path)=>{if(!Number.isInteger(v)||v<0||v>BP)refuse('BP_INVALID',path);return v;};
const ctxKey=(s,t)=>s+'|'+t;
function freeze(o){if(o&&typeof o==='object'){Object.freeze(o);for(const v of Object.values(o))freeze(v);}return o;}
const clone=v=>JSON.parse(JSON.stringify(v));

/* ---------------------------------------------------------------- trees (one preset or one user override) */
// tree = {axis_weights:{Q,G,V}, roles:{Q:[{role, weight_bp, factors:[{factor_id, weight_bp}]}], G:[…], V:[…]}}
// Returns the first fault as {code, path} or null. ctx = {sector_id, template_id}; F = factor map.
function treeFault(tree,ctx,F,path='$'){
 try{
  keys(tree,['axis_weights','roles'],path);keys(tree.axis_weights,AXES,path+'.axis_weights');keys(tree.roles,AXES,path+'.roles');
  let sum=0;for(const a of AXES)sum+=bp(tree.axis_weights[a],path+'.axis_weights.'+a);
  if(sum!==BP)refuse(sum===0?'ALL_ZERO':'AXIS_SUM',path+'.axis_weights');
  const seen=new Set();
  for(const a of AXES){const roles=arr(tree.roles[a],MAX.list,path+'.roles.'+a),ap=path+'.roles.'+a,active=tree.axis_weights[a]>0;let rs=0;const rn=new Set();
   roles.forEach((r,i)=>{const rp=ap+'['+i+']';keys(r,['role','weight_bp','factors'],rp);id(r.role,rp+'.role');if(rn.has(r.role))refuse('DUPLICATE',rp+'.role');rn.add(r.role);
    rs+=bp(r.weight_bp,rp+'.weight_bp');let fs=0;
    arr(r.factors,MAX.list,rp+'.factors').forEach((f,j)=>{const fp=rp+'.factors['+j+']';keys(f,['factor_id','weight_bp'],fp);
     const d=F.get(f.factor_id);if(!d)refuse('FACTOR_UNKNOWN',fp+'.factor_id');
     if(d.axis!==a||d.role!==r.role)refuse('AXIS_ROLE_MISMATCH',fp+'.factor_id');
     if(seen.has(f.factor_id))refuse('DUPLICATE',fp+'.factor_id');seen.add(f.factor_id);
     fs+=bp(f.weight_bp,fp+'.weight_bp');
     if(d.calculator_status!=='READY'&&f.weight_bp>0)refuse('FACTOR_PENDING',fp+'.factor_id');
     if(ctx&&!d.applicable_templates.includes(ctx.template_id)&&f.weight_bp>0)refuse('NOT_APPLICABLE',fp+'.factor_id');});
    if(active&&r.weight_bp>0&&fs!==BP)refuse(fs===0?'ALL_ZERO':'FACTOR_SUM',rp+'.factors');});
   if(active&&rs!==BP)refuse(rs===0?'ALL_ZERO':'ROLE_SUM',ap);}
  return null;
 }catch(e){if(e instanceof Refusal)return{code:e.code,path:e.path};return{code:'TYPE',path};}
}

/* ---------------------------------------------------------------- the bundle */
const SNAP=['snapshot_id','as_of','universe_id','universe_version','engine_version','normalization_version','mapping_version'];
const FACTOR=['factor_id','axis','role','display_name','aliases','variant_id','formula_version','unit','direction','period','overlap_group','applicable_templates','calculator_status','explain'];
const PRESET=['preset_set','version','state','validation_state','sector_id','template_id','axis_weights','roles','missing_policy','gate_policy'];
function checkBundle(b){
 keys(b,['schema','data_kind','snapshot','sectors','templates','roles','factors','recommendations','presets','companies','scores'],'$',['method_note']);
 if(b.schema!==SCHEMA)refuse('SCHEMA_VERSION','$.schema');
 if(!['SYNTHETIC','RESEARCH'].includes(b.data_kind))refuse('DATA_KIND_INVALID','$.data_kind');
 keys(b.snapshot,SNAP,'$.snapshot');for(const k of SNAP)str(b.snapshot[k],'$.snapshot.'+k,MAX.id);if(!DAY.test(b.snapshot.as_of))refuse('DAY_INVALID','$.snapshot.as_of');
 if(own(b,'method_note'))str(b.method_note,'$.method_note');
 const S=new Set(),T=new Set(),R=new Set();
 arr(b.sectors,MAX.list,'$.sectors').forEach((s,i)=>{keys(s,['id','label'],'$.sectors['+i+']');code(s.id,'$.sectors['+i+'].id');str(s.label,'$.sectors['+i+'].label',40);if(S.has(s.id))refuse('DUPLICATE','$.sectors['+i+']');S.add(s.id);});
 arr(b.templates,MAX.list,'$.templates').forEach((t,i)=>{keys(t,['id','label'],'$.templates['+i+']');code(t.id,'$.templates['+i+'].id');str(t.label,'$.templates['+i+'].label',40);if(T.has(t.id))refuse('DUPLICATE','$.templates['+i+']');T.add(t.id);});
 arr(b.roles,MAX.list*3,'$.roles').forEach((r,i)=>{const p='$.roles['+i+']';keys(r,['axis','role','label'],p);if(!AXES.includes(r.axis))refuse('AXIS_INVALID',p+'.axis');id(r.role,p+'.role');str(r.label,p+'.label',40);
  const k=r.axis+'|'+r.role;if(R.has(k))refuse('DUPLICATE',p);R.add(k);});
 const F=new Map();
 arr(b.factors,MAX.factors,'$.factors').forEach((f,i)=>{const p='$.factors['+i+']';keys(f,FACTOR,p);id(f.factor_id,p+'.factor_id');if(F.has(f.factor_id))refuse('DUPLICATE',p+'.factor_id');
  if(!AXES.includes(f.axis))refuse('AXIS_INVALID',p+'.axis');if(!R.has(f.axis+'|'+f.role))refuse('ROLE_UNKNOWN',p+'.role');str(f.display_name,p+'.display_name',60);
  arr(f.aliases,MAX.list,p+'.aliases').forEach((a,j)=>str(a,p+'.aliases['+j+']',40));id(f.variant_id,p+'.variant_id');str(f.formula_version,p+'.formula_version',MAX.id);
  str(f.unit,p+'.unit',40);if(!['HIGHER','LOWER'].includes(f.direction))refuse('DIRECTION_INVALID',p+'.direction');str(f.period,p+'.period',60);
  if(f.overlap_group!==null)id(f.overlap_group,p+'.overlap_group');
  arr(f.applicable_templates,MAX.list,p+'.applicable_templates').forEach((t,j)=>{if(!T.has(t))refuse('TEMPLATE_UNKNOWN',p+'.applicable_templates['+j+']');});
  if(!['READY','PENDING'].includes(f.calculator_status))refuse('STATUS_INVALID',p+'.calculator_status');str(f.explain,p+'.explain');F.set(f.factor_id,f);});
 arr(b.recommendations,MAX.recs,'$.recommendations').forEach((r,i)=>{const p='$.recommendations['+i+']';keys(r,['factor_id','sector_id','template_id','reason','evidence_level','source_refs','reviewed_at'],p);
  if(!F.has(r.factor_id))refuse('FACTOR_UNKNOWN',p+'.factor_id');if(r.sector_id!==null&&!S.has(r.sector_id))refuse('SECTOR_UNKNOWN',p+'.sector_id');
  if(r.template_id!==null&&!T.has(r.template_id))refuse('TEMPLATE_UNKNOWN',p+'.template_id');str(r.reason,p+'.reason');
  if(!own(EVIDENCE,r.evidence_level))refuse('EVIDENCE_INVALID',p+'.evidence_level');arr(r.source_refs,MAX.list,p+'.source_refs').forEach((s,j)=>str(s,p+'.source_refs['+j+']'));
  if(typeof r.reviewed_at!=='string'||!DAY.test(r.reviewed_at))refuse('DAY_INVALID',p+'.reviewed_at');});
 const P=new Map();let setVersion=null;
 arr(b.presets,MAX.presets,'$.presets').forEach((x,i)=>{const p='$.presets['+i+']';keys(x,PRESET,p);
  if(x.preset_set!==PRESET_SET)refuse('PRESET_SET_INVALID',p+'.preset_set');if(typeof x.version!=='string'||!VER.test(x.version))refuse('VERSION_INVALID',p+'.version');
  if(setVersion===null)setVersion=x.version;else if(x.version!==setVersion)refuse('PRESET_VERSION_MIXED',p+'.version');
  if(!['draft','released'].includes(x.state))refuse('STATE_INVALID',p+'.state');if(!['initial','validated'].includes(x.validation_state))refuse('STATE_INVALID',p+'.validation_state');
  if(!S.has(x.sector_id))refuse('SECTOR_UNKNOWN',p+'.sector_id');if(!T.has(x.template_id))refuse('TEMPLATE_UNKNOWN',p+'.template_id');
  if(x.missing_policy!=='STRICT')refuse('MISSING_POLICY_INVALID',p+'.missing_policy');if(x.gate_policy!=='NONE')refuse('GATE_POLICY_UNSUPPORTED',p+'.gate_policy');
  const k=ctxKey(x.sector_id,x.template_id);if(P.has(k))refuse('DUPLICATE',p);
  const f=treeFault({axis_weights:x.axis_weights,roles:x.roles},{sector_id:x.sector_id,template_id:x.template_id},F,p);if(f)refuse(f.code,f.path);P.set(k,x);});
 const C=new Set(),U=new Set();
 arr(b.companies,MAX.companies,'$.companies').forEach((c,i)=>{const p='$.companies['+i+']';keys(c,['company_id','universe_code','sector_id','template_id','mapping_status','lynch_tags'],p);
  id(c.company_id,p+'.company_id');if(C.has(c.company_id))refuse('DUPLICATE',p+'.company_id');C.add(c.company_id);
  if(c.universe_code!==null){id(c.universe_code,p+'.universe_code');if(U.has(c.universe_code))refuse('DUPLICATE',p+'.universe_code');U.add(c.universe_code);}
  if(c.mapping_status==='MAPPED'){if(!S.has(c.sector_id))refuse('SECTOR_UNKNOWN',p+'.sector_id');if(!T.has(c.template_id))refuse('TEMPLATE_UNKNOWN',p+'.template_id');}
  else if(c.mapping_status==='MAPPING_UNRESOLVED'){if(c.sector_id!==null&&!S.has(c.sector_id))refuse('SECTOR_UNKNOWN',p+'.sector_id');if(c.template_id!==null)refuse('MAPPING_STATE',p+'.template_id');}
  else refuse('MAPPING_STATE',p+'.mapping_status');
  arr(c.lynch_tags,8,p+'.lynch_tags').forEach((t,j)=>str(t,p+'.lynch_tags['+j+']',30));});
 if(!isObj(b.scores))refuse('TYPE','$.scores');
 for(const[fid,cells]of Object.entries(b.scores)){const p='$.scores.'+fid,d=F.get(fid);if(!d)refuse('FACTOR_UNKNOWN',p);if(d.calculator_status!=='READY')refuse('FACTOR_PENDING',p);if(!isObj(cells))refuse('TYPE',p);
  for(const k of Object.keys(cells))if(!C.has(k))refuse('COMPANY_UNKNOWN',p+'.'+k);
  for(const cid of C){if(!own(cells,cid))refuse('MATRIX_INCOMPLETE',p+'.'+cid);const x=cells[cid],q=p+'.'+cid;keys(x,['score','status'],q);
   if(VALID.includes(x.status)){if(typeof x.score!=='number'||!Number.isFinite(x.score)||x.score<0||x.score>100)refuse('SCORE_INVALID',q+'.score');}
   else if(MISSING.includes(x.status)){if(x.score!==null)refuse('SCORE_WITH_MISSING',q+'.score');}
   else refuse('STATUS_INVALID',q+'.status');}}
 for(const[fid,d]of F)if(d.calculator_status==='READY'&&!own(b.scores,fid))refuse('MATRIX_INCOMPLETE','$.scores.'+fid);
 return{F,P,version:setVersion};
}
function validate(json){
 try{const{version}=checkBundle(json);const value=freeze(clone(json));return{ok:true,value,version};}
 catch(e){if(e instanceof Refusal)return{ok:false,code:e.code,path:e.path};return{ok:false,code:'INVALID',path:'$'};}
}
// Lookups over a validated bundle (cached per bundle object).
const cache=new WeakMap();
function index(v){let x=cache.get(v);if(x)return x;
 const F=new Map(v.factors.map(f=>[f.factor_id,f])),P=new Map(v.presets.map(p=>[ctxKey(p.sector_id,p.template_id),p])),C=new Map(v.companies.map(c=>[c.company_id,c]));
 const roles=new Map(v.roles.map(r=>[r.axis+'|'+r.role,r.label])),sectors=new Map(v.sectors.map(s=>[s.id,s.label])),templates=new Map(v.templates.map(t=>[t.id,t.label]));
 x={F,P,C,roles,sectors,templates,version:v.presets.length?v.presets[0].version:null};cache.set(v,x);return x;}
const presetTree=p=>p?{axis_weights:clone(p.axis_weights),roles:clone(p.roles)}:null;
// The contexts the bundle has a base preset for, in the bundle's sector and template order.
function contexts(v){const X=index(v),out=[];for(const s of v.sectors)for(const t of v.templates)if(X.P.has(ctxKey(s.id,t.id)))out.push(Object.freeze({sector_id:s.id,template_id:t.id,key:ctxKey(s.id,t.id)}));return Object.freeze(out);}

/* ---------------------------------------------------------------- the user's config */
// {schema, preset_set, version, overrides:{'SECTOR|TEMPLATE': tree}} — base = the preset set and version it was made from;
// a newer default version never rewrites it (the screen says the base differs).
function emptyConfig(v){return{schema:CONFIG_SCHEMA,preset_set:PRESET_SET,version:index(v).version,overrides:{}};}
function validateConfig(config,v){
 try{keys(config,['schema','preset_set','version','overrides'],'$');if(config.schema!==CONFIG_SCHEMA)refuse('SCHEMA_VERSION','$.schema');
  if(config.preset_set!==PRESET_SET)refuse('PRESET_SET_INVALID','$.preset_set');if(typeof config.version!=='string'||!VER.test(config.version))refuse('VERSION_INVALID','$.version');
  if(!isObj(config.overrides))refuse('TYPE','$.overrides');
  if(v){const X=index(v);if(config.version!==X.version)refuse('BASE_VERSION_DIFFERS','$.version');
   for(const[k,t]of Object.entries(config.overrides)){if(!X.P.has(k))refuse('CONTEXT_UNKNOWN','$.overrides.'+k);const[s,tp]=k.split('|');const f=treeFault(t,{sector_id:s,template_id:tp},X.F,'$.overrides.'+k);if(f)return{ok:false,...f};}}
  return{ok:true};}
 catch(e){if(e instanceof Refusal)return{ok:false,code:e.code,path:e.path};return{ok:false,code:'INVALID',path:'$'};}}
const treeFor=(v,config,key)=>config&&own(config.overrides,key)?config.overrides[key]:presetTree(index(v).P.get(key));
const checkTree=(tree,ctx,v)=>treeFault(tree,ctx,index(v).F);
// Canonical JSON (keys sorted) and a short FNV-1a hash of it; key() = every version the result depends on + the config.
function canon(x){if(Array.isArray(x))return'['+x.map(canon).join(',')+']';if(isObj(x))return'{'+Object.keys(x).sort().map(k=>JSON.stringify(k)+':'+canon(x[k])).join(',')+'}';return JSON.stringify(x);}
function fnv(s){let h=0x811c9dc5;for(let i=0;i<s.length;i++){h^=s.charCodeAt(i);h=Math.imul(h,0x01000193)>>>0;}return('0000000'+h.toString(16)).slice(-8);}
const configHash=config=>fnv(canon(config));
function key(v,config,model='MINE'){const s=v.snapshot;return[s.snapshot_id,s.universe_id,s.universe_version,s.engine_version,s.normalization_version,s.mapping_version,PRESET_SET,index(v).version,model,configHash(config)].join('~');}

/* ---------------------------------------------------------------- the roll-up (§7.3, §8) */
// Effective weight of each active factor in the total (bp × bp × bp / 10^12), for display.
function effective(tree){const out=[];for(const a of AXES){const aw=tree.axis_weights[a];if(!aw)continue;for(const r of tree.roles[a]){if(!r.weight_bp)continue;
 for(const f of r.factors)if(f.weight_bp>0)out.push(Object.freeze({axis:a,role:r.role,factor_id:f.factor_id,share:aw*r.weight_bp*f.weight_bp/1e12}));}}return Object.freeze(out);}
function rollUp(tree,cid,scores){
 const axis={},why={},excluded=[];
 for(const a of AXES){const aw=tree.axis_weights[a];if(!aw){axis[a]=null;why[a]='USER_EXCLUDED';excluded.push(a);continue;}
  let sum=0,miss=null;
  for(const r of tree.roles[a]){if(!r.weight_bp)continue;let rs=0;
   for(const f of r.factors){if(!f.weight_bp)continue;const c=scores[f.factor_id]&&scores[f.factor_id][cid];
    if(!c||c.score===null){miss=miss||{code:c?c.status:'MISSING_INPUT',factor_id:f.factor_id};continue;}rs+=c.score*f.weight_bp/BP;}
   sum+=rs*r.weight_bp/BP;}
  if(miss){axis[a]=null;why[a]=miss.code;why[a+'_factor']=miss.factor_id;}else axis[a]=sum;}
 const active=AXES.filter(a=>tree.axis_weights[a]>0),unscored=active.filter(a=>axis[a]===null);
 const total=unscored.length?null:active.reduce((t,a)=>t+axis[a]*tree.axis_weights[a]/BP,0);
 return{axis,why,excluded,total,total_reason:unscored.length?'AXIS_UNSCORED':null};}
/* One model over the whole original population: every company has a row (unmapped and no-preset rows carry their reason and stay
   in the denominator); ranks are given only to rows with a total, by total (high first), ties by company_id; sector_rank inside the
   company's sector and template. model: 'MINE' (base preset + the user's overrides) or 'DEFAULT' (base presets only). */
function compute(v,config,{model='MINE'}={}){
 const X=index(v),cfg=model==='DEFAULT'?null:config,rows=[];const reasons={};
 const bump=k=>{reasons[k]=(own(reasons,k)?reasons[k]:0)+1;};
 for(const c of v.companies){
  const base={company_id:c.company_id,universe_code:c.universe_code,sector_id:c.sector_id,template_id:c.template_id,lynch_tags:c.lynch_tags};
  if(c.mapping_status!=='MAPPED'){rows.push({...base,Q:null,G:null,V:null,total:null,reason:'MAPPING_UNRESOLVED',why:{},excluded:[]});bump('MAPPING_UNRESOLVED');continue;}
  const k=ctxKey(c.sector_id,c.template_id),tree=treeFor(v,cfg,k);
  if(!tree){rows.push({...base,Q:null,G:null,V:null,total:null,reason:'NO_PRESET',why:{},excluded:[]});bump('NO_PRESET');continue;}
  const r=rollUp(tree,c.company_id,v.scores);
  if(r.total===null){const first=AXES.map(a=>r.why[a]).find(w=>w&&w!=='USER_EXCLUDED');bump(first||'AXIS_UNSCORED');}
  rows.push({...base,Q:r.axis.Q,G:r.axis.G,V:r.axis.V,total:r.total,reason:r.total_reason,why:r.why,excluded:r.excluded,context:k});}
 const scored=rows.filter(r=>r.total!==null).sort((a,b)=>b.total-a.total||(a.company_id<b.company_id?-1:1));
 scored.forEach((r,i)=>{r.rank=i+1;});
 const by=new Map();for(const r of scored){const k=r.context,n=by.has(k)?by.get(k)+1:1;by.set(k,n);r.sector_rank=n;}
 for(const r of rows)if(r.total===null){r.rank=null;r.sector_rank=null;}
 const axes={};for(const a of AXES)axes[a]=rows.filter(r=>r[a]!==null).length;
 return freeze({model,key:key(v,model==='DEFAULT'?emptyConfig(v):config,model),denominator:rows.length,computed:scored.length,axes,reasons,rows});}
/* Before / after of the same snapshot and population (else COMPARE_MISMATCH): each company's two rows, the rank change, and the
   ranks among companies computed in BOTH (so dropping out and score change are told apart). */
function compare(before,after){
 const sb=before.key.split('~').slice(0,8).join('~'),sa=after.key.split('~').slice(0,8).join('~');
 if(sb!==sa||before.denominator!==after.denominator)throw Error('COMPARE_MISMATCH');
 const A=new Map(after.rows.map(r=>[r.company_id,r]));
 const both=before.rows.filter(r=>r.total!==null&&A.get(r.company_id).total!==null).map(r=>r.company_id);
 const order=(res)=>{const s=new Set(both);return new Map(res.rows.filter(r=>s.has(r.company_id)).sort((x,y)=>y.total-x.total||(x.company_id<y.company_id?-1:1)).map((r,i)=>[r.company_id,i+1]));};
 const cb=order(before),ca=order(after);
 return freeze({common:both.length,rows:before.rows.map(b=>{const a=A.get(b.company_id);
  return{company_id:b.company_id,universe_code:b.universe_code,sector_id:b.sector_id,template_id:b.template_id,before:b,after:a,
   rank_change:b.rank!==null&&a.rank!==null?b.rank-a.rank:null,common_before:cb.get(b.company_id)||null,common_after:ca.get(b.company_id)||null};})});}

/* ---------------------------------------------------------------- edits (pure: each returns a new tree) */
function split(n){const base=Math.floor(BP/n),out=Array(n).fill(base);for(let i=0;i<BP-base*n;i++)out[i]++;return out;}
const findRole=(t,a,role)=>t.roles[a].find(r=>r.role===role);
function addFactor(tree,v,axisId,factorId){const t=clone(tree),d=index(v).F.get(factorId);if(!d||d.axis!==axisId)throw Error('FACTOR_UNKNOWN');
 if(AXES.some(a=>t.roles[a].some(r=>r.factors.some(f=>f.factor_id===factorId))))throw Error('DUPLICATE');
 let r=findRole(t,axisId,d.role);if(!r){r={role:d.role,weight_bp:0,factors:[]};t.roles[axisId].push(r);}// a new role starts at 0: role budgets are never raised silently
 r.factors.push({factor_id:factorId,weight_bp:0});const w=split(r.factors.length);r.factors.forEach((f,i)=>{f.weight_bp=w[i];});return t;}
function removeFactor(tree,axisId,factorId){const t=clone(tree);for(const r of t.roles[axisId]){const i=r.factors.findIndex(f=>f.factor_id===factorId);if(i<0)continue;
 r.factors.splice(i,1);if(r.factors.length){const w=split(r.factors.length);r.factors.forEach((f,j)=>{f.weight_bp=w[j];});}return t;}throw Error('FACTOR_NOT_SELECTED');}
function replaceFactor(tree,v,axisId,oldId,newId){const X=index(v),a=X.F.get(oldId),b=X.F.get(newId);if(!a||!b||b.axis!==axisId)throw Error('FACTOR_UNKNOWN');if(a.role!==b.role)throw Error('ROLE_DIFFERS');
 const t=clone(tree);if(AXES.some(x=>t.roles[x].some(r=>r.factors.some(f=>f.factor_id===newId))))throw Error('DUPLICATE');
 const r=findRole(t,axisId,a.role),f=r&&r.factors.find(x=>x.factor_id===oldId);if(!f)throw Error('FACTOR_NOT_SELECTED');f.factor_id=newId;return t;}
function setAxisWeights(tree,w){const t=clone(tree);for(const a of AXES)t.axis_weights[a]=w[a];return t;}
function setRoleWeight(tree,axisId,role,w){const t=clone(tree),r=findRole(t,axisId,role);if(!r)throw Error('ROLE_UNKNOWN');r.weight_bp=w;return t;}
function setFactorWeight(tree,axisId,factorId,w){const t=clone(tree);for(const r of t.roles[axisId]){const f=r.factors.find(x=>x.factor_id===factorId);if(f){f.weight_bp=w;return t;}}throw Error('FACTOR_NOT_SELECTED');}
// The edit put into a config: scope 'CONTEXT' (this sector · template only) or 'ALL' (copied explicitly to every context whose
// template can use every active factor; the others are listed as not applied). Never spreads implicitly.
function applyEdit(config,v,ctx,tree,scope='CONTEXT'){const c=clone(config),X=index(v),skipped=[];
 if(scope==='CONTEXT'){c.overrides[ctxKey(ctx.sector_id,ctx.template_id)]=clone(tree);return{config:c,skipped};}
 if(scope!=='ALL')throw Error('SCOPE_INVALID');
 for(const k of X.P.keys()){const[s,t]=k.split('|');if(treeFault(tree,{sector_id:s,template_id:t},X.F))skipped.push(k);else c.overrides[k]=clone(tree);}
 return{config:c,skipped};}
const restoreDefault=(config,ctx)=>{const c=clone(config);delete c.overrides[ctxKey(ctx.sector_id,ctx.template_id)];return c;};

/* ---------------------------------------------------------------- the catalog shown for one context */
const norm=s=>String(s).toLowerCase().replace(/[\s/·()\-_.]/g,'');
function recommendationsFor(v,factorId,ctx){return v.recommendations.filter(r=>r.factor_id===factorId&&(r.sector_id===null||r.sector_id===ctx.sector_id)&&(r.template_id===null||r.template_id===ctx.template_id));}
// One row per factor of the axis: base (in the base preset of this context), recommended (with reasons), selected (in the
// edited tree), state READY | PENDING (no calculator: never selectable) | NOT_FIT (formula not for this template: not selectable)
// | PARTIAL (calculator ready, some companies of this context without a score), and the context's scored / total count.
function catalog(v,ctx,tree,axisId,query=''){
 const X=index(v),k=ctxKey(ctx.sector_id,ctx.template_id),base=presetTree(X.P.get(k)),preset=X.P.get(k);
 const inTree=(t,fid)=>!!t&&AXES.some(a=>t.roles[a].some(r=>r.factors.some(f=>f.factor_id===fid&&f.weight_bp>0)));
 const members=v.companies.filter(c=>c.mapping_status==='MAPPED'&&c.sector_id===ctx.sector_id&&c.template_id===ctx.template_id);
 const q=norm(query);
 return Object.freeze(v.factors.filter(f=>f.axis===axisId&&(!q||[f.display_name,f.factor_id,...f.aliases].some(x=>norm(x).includes(q)))).map(f=>{
  let scored=null;if(f.calculator_status==='READY'){scored=members.filter(c=>v.scores[f.factor_id][c.company_id].score!==null).length;}
  const fit=f.applicable_templates.includes(ctx.template_id);
  const state=f.calculator_status!=='READY'?'PENDING':!fit?'NOT_FIT':scored<members.length?'PARTIAL':'READY';
  return Object.freeze({factor:f,role_label:X.roles.get(f.axis+'|'+f.role)||f.role,base:inTree(base,f.factor_id),base_state:preset?preset.validation_state:null,
   recommended:Object.freeze(recommendationsFor(v,f.factor_id,ctx)),selected:inTree(tree,f.factor_id),state,scored,members:members.length,selectable:state==='READY'||state==='PARTIAL'});}));}

const reasonText=c=>own(REASON,c)?REASON[c]:'사유 코드 미등록';
const status=v=>(!v?TEXT.NONE:v.data_kind==='SYNTHETIC'?TEXT.SYNTHETIC:'연구 자료 · '+v.snapshot.snapshot_id);
// The preview call: before and after of one snapshot. A Promise so a later runner (Codex's engine, a Worker) can take its place;
// the screen keeps only the answer of its latest request.
const preview=(v,before,after)=>Promise.resolve().then(()=>{const b=compute(v,before),a=compute(v,after);return freeze({before:b,after:a,diff:compare(b,a)});});
function source(){return Promise.resolve(Object.freeze({state:'NONE',code:'SECTOR_QGV_NOT_CONNECTED',payload:null,text:TEXT.NONE}));}
return Object.freeze({SCHEMA,CONFIG_SCHEMA,PRESET_SET,AXES,BP,MISSING,EVIDENCE,REASON,TEXT,validate,index,contexts,emptyConfig,validateConfig,treeFor,checkTree,
 canon,configHash,key,effective,compute,compare,split,addFactor,removeFactor,replaceFactor,setAxisWeights,setRoleWeight,setFactorWeight,applyEdit,restoreDefault,
 recommendationsFor,catalog,reasonText,status,preview,source,ctxKey});
});
