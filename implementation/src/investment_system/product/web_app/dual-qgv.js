/* 두 모형 연구 결과 reader (IS2.dualQgv; owner 2026-11-10 「통합 QGV·섹터 QGV」, 2026-11-11 「두 모형 실제 연결」; Codex #529
   46f73a07 research.dual_qgv.delivery_artifacts → qgv-dual-delivery/1, DUAL_QGV.md). Read as written; nothing is recalculated,
   re-ranked, filled or stitched (DC-42: Main uses the supplied counts, weights and ranks, never aggregates itself).
   - What it is: three preregistered research candidates on one evaluation population — U1 unified-roa-core and U2 unified-sales-core
     (통합 연구: one common core for every evaluated company, one common reference pool) and S1 sector-reduced-core (섹터 연구:
     sector × accounting model core, 핵심 요소 축소). PRIVATE_RESEARCH, NOT_ADOPTED, performance NOT_MEASURED: never the official QGV,
     never a default, never a performance claim. U1 / U2 / S1 scores are not on one scale and are never averaged, summed or differenced.
   - Selectable is not the same as complete: a delivery that passes every check below can be chosen and read (Q / G / factors / missing
     reasons) even when V and the total are null everywhere. A null total has no total rank (RANK_WITHOUT_TOTAL refuses otherwise).
     Recalculation, saving and replay are separate states: this screen shows retained results only (재계산 연결 안 됨); replay is the
     producer's (qgv-dual-saved/1, the same configuration, code and both input identities, else refused).
   - Trust: the delivery manifest's bytes are pinned at staging; here each file's own bytes are checked against the manifest (size and
     SHA-256, not a re-encoding), and the evaluation population must be the result already delivered in the checked held issuer
     bundle (coverage scope: population id / version / members hash / code-row denominator / evaluation day, and the input hash —
     operating504: the evaluation input; held1057: the reference source input, the evaluation rows being its projection).
   - Scopes: operating504 (평가 504 code rows / 501 issuers) and held1057 (보유 금융 표본 1057 issuers) are separate populations, never
     summed; the whole-market denominator and coverage are null (미측정).
   Pure except sha256 (passed in by the caller, WebCrypto); the RAM holder (ram) keeps checked deliveries until the classification
   bundle is dropped. No storage, no request of its own. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else{const I=root.IS2=root.IS2||{};I.dualQgv=api;}})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
const SCHEMA=Object.freeze({MANIFEST:'qgv-dual-delivery-manifest/1',SUMMARY:'qgv-dual-delivery/1',INDEX:'qgv-dual-index/1',DETAIL:'qgv-dual-detail/1'});
// input: which side's input hash the delivered result names. operating504's evaluation input is that result's own input
// (EVALUATION_INPUT_MATCHED). held1057's evaluation input (a projection of the held rows) is not the delivered result's input;
// only its reference source input is, so its evaluation input stays UNVERIFIED until Codex gives the members / derivation / hash
// link (owner 2026-11-11 §2, #437 6794173362 q.1). The screen says so; it is never shown as a verified evaluation input.
const SCOPES=Object.freeze({
 operating504:Object.freeze({label:'운영504',anchor:'operating',input:'evaluation',text:'평가 504코드 행 / 501발행사'}),
 held1057:Object.freeze({label:'보유1057',anchor:'held_financial_subsample',input:'reference',text:'보유 재무 표본 1057발행사 · 운영504와 합치지 않음'})});
const INPUT_CHECK=Object.freeze({evaluation:'EVALUATION_INPUT_MATCHED',reference:'REFERENCE_INPUT_MATCHED_EVALUATION_UNVERIFIED'});
const INPUT_WORD=Object.freeze({EVALUATION_INPUT_MATCHED:'평가 입력 = 지금 받은 결과의 입력(해시 일치)',
 REFERENCE_INPUT_MATCHED_EVALUATION_UNVERIFIED:'참조 원천 입력만 일치 · 평가 입력 연결 미확인(투영 증명 파일 없음)',
 EVALUATION_INPUT_PROJECTION_ATTESTED:'평가 입력 = 참조 원천의 투영 · 생산자 투영 증명과 대조됨(화면이 다시 계산한 것 아님)'});
// The producer's projection proof of held1057's evaluation input (Codex 6794279588 §2, qgv-dual-input-projection-proof/1): it must
// bind exactly this delivery's evaluation population and reference source (the staged held input), a selection of that many
// issuers, only the five projection fields changed, row values and classification unchanged, no whole market, no new score.
const LINEAGE_SCHEMA='qgv-dual-input-projection-proof/1';
const PROJECTION_FIELDS=Object.freeze(['members','rows','snapshot_id','universe_id','universe_version']);
function lineageCheck(x,boards){const at='lineage';if(!isObj(x)||x.schema_version!==LINEAGE_SCHEMA)refuse('LINEAGE_SCHEMA',at+'.schema_version');
 for(const[k,b]of Object.entries(boards)){if(!same(x.evaluation,b.evaluation_population))refuse('LINEAGE_MISMATCH',at+'.evaluation');
  if(!same(x.reference_source,b.bindings.reference))refuse('LINEAGE_MISMATCH',at+'.reference_source');
  if(x.reference_source.input_hash!==b.reference_population.input_hash)refuse('LINEAGE_MISMATCH',at+'.reference_source.input_hash');}
 const ev=x.evaluation;
 if(x.selected_issuer_count!==ev.issuers||!HEX.test(x.selected_issuer_members_hash)||typeof x.selection_rule!=='string'||!x.selection_rule)refuse('LINEAGE_INVALID',at+'.selected_issuer_count');
 if(x.rows_equal_source_projection!==true||x.row_values_or_classification_changed!==false)refuse('LINEAGE_INVALID',at+'.rows_equal_source_projection');
 if(!Array.isArray(x.changed_top_level_fields)||!same([...x.changed_top_level_fields].sort(),PROJECTION_FIELDS))refuse('LINEAGE_INVALID',at+'.changed_top_level_fields');
 if(x.whole_market_denominator!==null||x.reference_source_is_not_eligible_whole_market!==true||x.new_score_calculations!==0)refuse('LINEAGE_INVALID',at+'.whole_market_denominator');}
const MODELS=Object.freeze({
 U1:Object.freeze({model_id:'unified-roa-core/0.1.0',kind:'COMMON',label:'통합 연구 U1',core:'Q ROA · G ROA 개선 · V 이익·장부'}),
 U2:Object.freeze({model_id:'unified-sales-core/0.1.0',kind:'COMMON',label:'통합 연구 U2',core:'Q ROA · G 매출 성장 · V 이익·장부'}),
 S1:Object.freeze({model_id:'sector-reduced-core/0.1.0',kind:'SECTOR',label:'섹터 연구 S1',core:'섹터·회계모형별 축소 핵심 요소'})});
const KIND=Object.freeze({COMMON:'통합 · 모든 평가 기업에 같은 핵심 요소와 같은 참조집단',SECTOR:'섹터 · 섹터×회계모형별 핵심 요소 · 다른 회계모형 순위와 합치지 않음'});
const BOARD_KEYS=Object.freeze(['model_id','model_version','engine_version','adapter_version','normalization_version','evaluation_population','reference_population',
 'bindings','cache_key','result_hash','coverage','classification_mode','performance_state','operating_adoption','deployment_state','configuration_hash']);
const COVERAGE_KEYS=Object.freeze(['denominator','target95','stages','causes_overlap','causes','incomplete_unique','current_sample_barrier','gap95','whole_market_denominator','whole_market_coverage']);
const STAGES=Object.freeze([['core_inputs','핵심 요소 입력 모두'],['core_raw','핵심 요소 원지표 모두'],['core_scores','핵심 요소 점수 모두'],['Q','Q 축'],['G','G 축'],['V','V 축'],['joint','세 축 동시'],['total','최종 총점']]);
const POP_KEYS=Object.freeze(['id','version','members_hash','valuation_date','as_of','code_rows','issuers','input_hash','snapshot_id','classification_records_hash','classification_context']);
const REF_EXTRA=Object.freeze(['factor_members_hash','candidate_population','scope']);
const HEAD_KEYS=Object.freeze(['axes','total','rank','rank_n','ranking_scope','status','gate_status']);
const DETAIL_KEYS=Object.freeze(['company_id','issuer_id','security_id','sector_id','accounting_template','factors','rank','status','axes','total','pre_gate_total','gate_status','ranking_scope','rank_n','selected_variants','scoring_representative']);
// Conditional-required (Codex #437 6794279588 §3, DUAL_QGV.md): present on every row with an applied preset, absent exactly when the
// row is MAPPING_UNRESOLVED (no preset); not tied to the total. Never filled with [] / 0 when absent.
const DETAIL_PRESET_FIELDS=Object.freeze(['missing_factors','nominal_axis_weights','nominal_effective_weights','post_gate_axis_weights','post_gate_effective_weights']);
const FACTOR_KEYS=Object.freeze(['raw_status','score','score_status','valid_n','raw_components_available','verified_external_available','kind','rank','rank_n','decile','decile_status']);
const MAX_BYTES=2000000;
const HEX=/^[0-9a-f]{64}$/,DAY=/^\d{4}-\d{2}-\d{2}$/,FILE=/^(summary|index)\.json$|^detail-\d{3}\.json$/,DETAIL_FILE=/^detail-\d{3}\.json$/;
const STATUS_WORD=Object.freeze({VALID:'산출',MISSING_INPUT:'입력 없음',MAPPING_UNRESOLVED:'분류 미확정',NOT_APPLICABLE:'산식 적용 부적합',PERIOD_MISMATCH:'기간 불일치',
 PEER_SAMPLE_SMALL:'비교 표본 부족(20 미만)',DOMAIN_INVALID:'값 범위 밖',GATE_UNKNOWN:'관문 판정 불가(UNKNOWN)',STRICT_INCOMPLETE:'핵심 요소 일부 미산출',
 PASS:'관문 통과',UNKNOWN:'관문 판정 불가',VALUE_EXCLUDED:'V 총점 반영 제외 · 기업 탈락 아님'});
const word=c=>c===null||c===undefined?'—':STATUS_WORD[c]||String(c);

class Refusal extends Error{constructor(code,path){super(code);this.code=code;this.path=path;}}
const refuse=(c,p)=>{throw new Refusal(c,p);};
const isObj=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
const own=(o,k)=>Object.prototype.hasOwnProperty.call(o,k);
const int=v=>Number.isInteger(v);
const num=v=>v===null||(typeof v==='number'&&Number.isFinite(v));
function canonical(v){if(Array.isArray(v))return'['+v.map(canonical).join(',')+']';
 if(isObj(v))return'{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canonical(v[k])).join(',')+'}';return JSON.stringify(v);}
const same=(a,b)=>canonical(a)===canonical(b);
function exact(o,keys,at,optional=[]){if(!isObj(o))refuse('TYPE',at);for(const k of keys)if(!own(o,k))refuse('KEY_MISSING',at+'.'+k);
 for(const k of Object.keys(o))if(!keys.includes(k)&&!optional.includes(k))refuse('KEY_UNKNOWN',at+'.'+k);}
const count=(c,at,den)=>{exact(c,['code_rows','issuers'],at);if(!int(c.code_rows)||!int(c.issuers)||c.code_rows<0||c.issuers<0||c.issuers>c.code_rows)refuse('COUNT_RANGE',at);
 if(den&&(c.code_rows>den.code_rows||c.issuers>den.issuers))refuse('COUNT_RANGE',at);return c;};
// Only a delivery this reader checked can be held in RAM (the screens read nothing else).
const CHECKED=new WeakSet();
function freeze(o){if(o&&typeof o==='object'&&!Object.isFrozen(o)){Object.freeze(o);for(const v of Object.values(o))freeze(v);}return o;}

function population(p,at){if(!isObj(p))refuse('TYPE',at);
 for(const k of POP_KEYS)if(!own(p,k))refuse('KEY_MISSING',at+'.'+k);
 if(typeof p.id!=='string'||!p.id||typeof p.version!=='string'||!p.version||!HEX.test(p.members_hash)||!HEX.test(p.input_hash)
  ||!DAY.test(p.valuation_date)||typeof p.as_of!=='string'||!int(p.code_rows)||p.code_rows<1||!int(p.issuers)||p.issuers<1||p.issuers>p.code_rows)refuse('POPULATION_INVALID',at);}

function coverage(c,ev,at){exact(c,COVERAGE_KEYS,at);
 const den=c.denominator;if(!isObj(den)||den.code_rows!==ev.code_rows||den.issuers!==ev.issuers)refuse('DENOMINATOR_MISMATCH',at+'.denominator');
 exact(c.stages,STAGES.map(s=>s[0]),at+'.stages');for(const[k]of STAGES)count(c.stages[k],at+'.stages.'+k,den);
 count(c.target95,at+'.target95',den);if(c.target95.code_rows<1||c.target95.issuers<1)refuse('COUNT_RANGE',at+'.target95');
 exact(c.gap95,['joint','total'],at+'.gap95');
 for(const s of['joint','total']){const g=count(c.gap95[s],at+'.gap95.'+s);
  for(const u of['code_rows','issuers'])if(g[u]!==Math.max(0,c.target95[u]-c.stages[s][u]))refuse('COUNT_ARITHMETIC',at+'.gap95.'+s+'.'+u);}
 if(c.causes_overlap!==true)refuse('CAUSES_NOT_OVERLAPPING',at+'.causes_overlap');
 if(!isObj(c.causes))refuse('TYPE',at+'.causes');for(const[k,v]of Object.entries(c.causes))count(v,at+'.causes.'+k,den);
 count(c.incomplete_unique,at+'.incomplete_unique',den);count(c.current_sample_barrier,at+'.current_sample_barrier',den);
 if(c.whole_market_denominator!==null||c.whole_market_coverage!==null)refuse('MARKET_NOT_NULL',at+'.whole_market_denominator');}

function board(key,b,at){exact(b,BOARD_KEYS,at);const M=MODELS[key];
 if(b.model_id!==M.model_id)refuse('MODEL_MISMATCH',at+'.model_id');
 if(b.operating_adoption!=='NOT_ADOPTED')refuse('ADOPTION_CLAIMED',at+'.operating_adoption');
 if(b.performance_state!=='NOT_MEASURED')refuse('PERFORMANCE_CLAIMED',at+'.performance_state');
 if(!['RETROSPECTIVE_RECONSTRUCTION','AS_OF_CLASSIFICATION_NOT_SYSTEM_PIT_PROOF'].includes(b.classification_mode))refuse('CLASSIFICATION_MODE',at+'.classification_mode');
 for(const k of['cache_key','result_hash','configuration_hash'])if(!HEX.test(b[k]))refuse('HASH_INVALID',at+'.'+k);
 const ev=b.evaluation_population,ref=b.reference_population;population(ev,at+'.evaluation_population');
 population(ref,at+'.reference_population');for(const k of REF_EXTRA)if(!own(ref,k))refuse('KEY_MISSING',at+'.reference_population.'+k);
 if(ref.scope!=='FACTOR_INPUT_ELIGIBILITY_NOT_LISTING_OR_INVESTMENT_ELIGIBILITY')refuse('REFERENCE_SCOPE',at+'.reference_population.scope');
 if(ref.valuation_date!==ev.valuation_date||ref.as_of!==ev.as_of)refuse('REFERENCE_DATE_MISMATCH',at+'.reference_population');
 population(ref.candidate_population,at+'.reference_population.candidate_population');
 exact(b.bindings,['model_hash','evaluation','reference','code_hash','engine_version','adapter_version'],at+'.bindings');
 if(b.bindings.model_hash!==b.configuration_hash)refuse('BINDINGS_MISMATCH',at+'.bindings.model_hash');
 if(!same(b.bindings.evaluation,ev))refuse('BINDINGS_MISMATCH',at+'.bindings.evaluation');
 if(!same(b.bindings.reference,ref.candidate_population))refuse('BINDINGS_MISMATCH',at+'.bindings.reference');
 if(!HEX.test(b.bindings.code_hash)||b.bindings.engine_version!==b.engine_version||b.bindings.adapter_version!==b.adapter_version)refuse('BINDINGS_MISMATCH',at+'.bindings');
 coverage(b.coverage,ev,at+'.coverage');}

// The manifest entry for a file; its own bytes must match (size and SHA-256).
async function bytesMatch(file,name,entries,sha256,at){
 if(!isObj(file)||!(file.bytes instanceof Uint8Array)||!isObj(file.body))refuse('BYTES_REQUIRED',at);
 const e=entries.get(name);if(!e)refuse('NOT_IN_MANIFEST',at);
 if(file.bytes.length!==e.size||(await sha256(file.bytes))!==e.sha256)refuse('BYTES_MISMATCH',at);return file.body;}

function manifestOf(m,scope){exact(m,['schema_version','data_kind','scope','files'],'manifest');
 if(m.schema_version!==SCHEMA.MANIFEST)refuse('SCHEMA','manifest.schema_version');if(m.scope!==scope)refuse('SCOPE_MISMATCH','manifest.scope');
 if(!['PRIVATE','SYNTHETIC'].includes(m.data_kind))refuse('DATA_KIND','manifest.data_kind');
 if(!Array.isArray(m.files)||!m.files.length||m.files.length>400)refuse('FILES_INVALID','manifest.files');const entries=new Map();
 m.files.forEach((f,i)=>{exact(f,['path','size','sha256'],'manifest.files['+i+']');
  if(!FILE.test(f.path)||entries.has(f.path)||!int(f.size)||f.size<1||f.size>MAX_BYTES||!HEX.test(f.sha256))refuse('FILES_INVALID','manifest.files['+i+']');entries.set(f.path,f);});
 if(!entries.has('summary.json')||!entries.has('index.json')||![...entries.keys()].some(p=>DETAIL_FILE.test(p)))refuse('FILES_INVALID','manifest.files');return entries;}

function anchorCheck(scope,ev,boards,anchor){const S=SCOPES[scope];
 if(!isObj(anchor)||!Array.isArray(anchor.scopes))refuse('ANCHOR_REQUIRED','$');const a=anchor.scopes.find(s=>s&&s.scope===S.anchor);if(!a)refuse('ANCHOR_REQUIRED','$');
 if(a.population_id!==ev.id||a.population_version!==ev.version||a.members_hash!==ev.members_hash||a.denominator!==ev.code_rows)refuse('DUAL_POPULATION_MISMATCH','evaluation_population');
 if(a.valuation_date!==ev.valuation_date)refuse('DUAL_DATE_MISMATCH','evaluation_population.valuation_date');
 for(const[k,b]of Object.entries(boards)){const input=S.input==='evaluation'?b.evaluation_population.input_hash:b.reference_population.input_hash;
  if(input!==a.input_hash)refuse('DUAL_INPUT_MISMATCH','boards.'+k+'.'+(S.input==='evaluation'?'evaluation_population':'reference_population')+'.input_hash');}}

function indexRows(x,summary,entries){exact(x,['schema_version','evaluation_population','rows'],'index');if(x.schema_version!==SCHEMA.INDEX)refuse('SCHEMA','index.schema_version');
 const keys=Object.keys(summary.boards),ev=summary.boards[keys[0]].evaluation_population;
 if(!same(x.evaluation_population,ev))refuse('INDEX_POPULATION_MISMATCH','index.evaluation_population');
 if(!Array.isArray(x.rows)||x.rows.length!==ev.code_rows)refuse('ROWS_INVALID','index.rows');
 const seen=new Set(),files=new Set();
 x.rows.forEach((r,i)=>{const at='index.rows['+i+']';exact(r,['company_id','issuer_id','security_id','boards','detail_file'],at);
  if(typeof r.company_id!=='string'||!r.company_id||seen.has(r.company_id))refuse('ROWS_INVALID',at+'.company_id');seen.add(r.company_id);
  if(!(r.issuer_id===null||typeof r.issuer_id==='string')||!(r.security_id===null||typeof r.security_id==='string'))refuse('TYPE',at);
  if(!DETAIL_FILE.test(r.detail_file)||!entries.has(r.detail_file))refuse('DETAIL_NOT_IN_MANIFEST',at+'.detail_file');files.add(r.detail_file);
  exact(r.boards,keys,at+'.boards');
  for(const k of keys){const b=r.boards[k],bt=at+'.boards.'+k;exact(b,HEAD_KEYS,bt);head(b,k,bt);}});
 for(const p of entries.keys())if(DETAIL_FILE.test(p)&&!files.has(p))refuse('DETAIL_UNREFERENCED','manifest.files.'+p);
 // The producer's stage counts are the rows as delivered: each axis, 세 축 동시 and the total, in code rows and issuers.
 for(const k of keys){const st=summary.boards[k].coverage.stages,has={Q:r=>r.axes.Q!==null,G:r=>r.axes.G!==null,V:r=>r.axes.V!==null,
   joint:r=>r.axes.Q!==null&&r.axes.G!==null&&r.axes.V!==null,total:r=>r.total!==null};
  for(const[s,f]of Object.entries(has)){const hit=x.rows.filter(r=>f(r.boards[k]));
   if(hit.length!==st[s].code_rows||new Set(hit.filter(r=>r.issuer_id).map(r=>r.issuer_id)).size!==st[s].issuers)refuse('STAGE_COUNT_MISMATCH','summary.boards.'+k+'.coverage.stages.'+s);}}
 return x.rows;}

function head(b,k,at){exact(b.axes,['Q','G','V'],at+'.axes');for(const a of['Q','G','V'])if(!num(b.axes[a]))refuse('TYPE',at+'.axes.'+a);
 if(!num(b.total))refuse('TYPE',at+'.total');if(!int(b.rank_n)||b.rank_n<0)refuse('TYPE',at+'.rank_n');
 if(b.total===null&&b.rank!==null)refuse('RANK_WITHOUT_TOTAL',at+'.rank');
 if(b.rank!==null&&(!int(b.rank)||b.rank<1||b.rank>b.rank_n))refuse('RANK_RANGE',at+'.rank');
 if(typeof b.ranking_scope!=='string'||(MODELS[k].kind==='COMMON'?b.ranking_scope!=='COMMON':!/^SECTOR\|/.test(b.ranking_scope)))refuse('RANKING_SCOPE',at+'.ranking_scope');
 if(typeof b.status!=='string'||typeof b.gate_status!=='string')refuse('TYPE',at+'.status');
 if(b.gate_status==='UNKNOWN'&&b.total!==null)refuse('GATE_UNKNOWN_WITH_TOTAL',at+'.total');}

// manifest / summary / index: each {bytes, body}. opts {scope, anchor (IS2.referenceView.anchorOf of the checked bundle), sha256}.
async function checkDelivery(parts,opts){
 try{const o=opts||{};if(!own(SCOPES,o.scope))refuse('SCOPE_UNKNOWN','$');if(typeof o.sha256!=='function')refuse('HASH_UNAVAILABLE','$');
  const p=parts||{};if(!isObj(p.manifest)||!isObj(p.manifest.body))refuse('BYTES_REQUIRED','manifest');
  const entries=manifestOf(p.manifest.body,o.scope);
  const s=await bytesMatch(p.summary,'summary.json',entries,o.sha256,'summary');
  exact(s,['schema_version','visibility','boards'],'summary');if(s.schema_version!==SCHEMA.SUMMARY)refuse('SCHEMA','summary.schema_version');
  if(s.visibility!=='PRIVATE_RESEARCH')refuse('VISIBILITY','summary.visibility');
  const keys=isObj(s.boards)?Object.keys(s.boards):[];if(!keys.length||keys.some(k=>!own(MODELS,k)))refuse('BOARDS_INVALID','summary.boards');
  for(const k of keys)board(k,s.boards[k],'summary.boards.'+k);
  const ev=s.boards[keys[0]].evaluation_population;
  for(const k of keys)if(!same(s.boards[k].evaluation_population,ev))refuse('EVALUATION_MISMATCH','summary.boards.'+k+'.evaluation_population');
  anchorCheck(o.scope,ev,s.boards,o.anchor);
  const x=await bytesMatch(p.index,'index.json',entries,o.sha256,'index');const rows=indexRows(x,s,entries);
  // held1057's evaluation input: attested only by a matching projection proof; a proof that does not match refuses the delivery.
  let input_check=INPUT_CHECK[SCOPES[o.scope].input];
  if(p.lineage!==undefined&&p.lineage!==null){if(SCOPES[o.scope].input!=='reference')refuse('LINEAGE_NOT_APPLICABLE','lineage');
   if(!isObj(p.lineage)||!isObj(p.lineage.body))refuse('LINEAGE_SCHEMA','lineage');lineageCheck(p.lineage.body,s.boards);input_check='EVALUATION_INPUT_PROJECTION_ATTESTED';}
  const value=freeze({scope:o.scope,data_kind:p.manifest.body.data_kind,entries:Object.fromEntries(entries),summary:s,rows,models:keys,input_check});CHECKED.add(value);
  return{ok:true,value};}
 catch(e){if(e instanceof Refusal)return{ok:false,code:e.code,path:e.path};throw e;}}

// One detail file {bytes, body} for a checked delivery: every row of that file as the index heads it, factors without raw values.
async function checkDetail(file,name,delivery,sha256){
 try{const d=delivery;if(!d||!d.entries||!own(d.entries,name)||!DETAIL_FILE.test(name))refuse('NOT_IN_MANIFEST',name);
  const entries=new Map(Object.entries(d.entries)),x=await bytesMatch(file,name,entries,sha256,name);
  exact(x,['schema_version','rows'],name);if(x.schema_version!==SCHEMA.DETAIL)refuse('SCHEMA',name+'.schema_version');
  const want=d.rows.filter(r=>r.detail_file===name);
  if(!Array.isArray(x.rows)||x.rows.length!==want.length)refuse('DETAIL_ROWS_MISMATCH',name+'.rows');
  const out=new Map();
  x.rows.forEach((r,i)=>{const at=name+'.rows['+i+']',w=want[i];exact(r,['company_id','boards'],at);
   if(r.company_id!==w.company_id)refuse('DETAIL_ROWS_MISMATCH',at+'.company_id');exact(r.boards,d.models,at+'.boards');
   for(const k of d.models){const b=r.boards[k],bt=at+'.boards.'+k;exact(b,DETAIL_KEYS,bt,DETAIL_PRESET_FIELDS);
    const preset=b.status!=='MAPPING_UNRESOLVED';
    for(const f of DETAIL_PRESET_FIELDS)if(own(b,f)!==preset)refuse(preset?'PRESET_FIELD_MISSING':'PRESET_FIELD_UNEXPECTED',bt+'.'+f);
    if(b.company_id!==w.company_id||b.issuer_id!==w.issuer_id||b.security_id!==w.security_id)refuse('DETAIL_IDENTITY',bt);
    for(const h of HEAD_KEYS)if(!same(b[h],w.boards[k][h]))refuse('DETAIL_MISMATCH',bt+'.'+h);
    if(!Array.isArray(b.selected_variants)||!isObj(b.factors)||b.selected_variants.some(v=>!own(b.factors,v)))refuse('FACTORS_INVALID',bt+'.selected_variants');
    for(const[v,f]of Object.entries(b.factors)){const ft=bt+'.factors.'+v;
     if(isObj(f)&&own(f,'raw_value'))refuse('RAW_VALUE_PRESENT',ft);exact(f,FACTOR_KEYS,ft);
     if((f.kind==='CORE')!==b.selected_variants.includes(v)||!['CORE','ADDITIONAL'].includes(f.kind))refuse('FACTOR_KIND',ft+'.kind');
     if(!num(f.score))refuse('TYPE',ft+'.score');if(!int(f.rank_n)||f.rank_n<0||!(f.valid_n===null||int(f.valid_n)))refuse('TYPE',ft+'.rank_n');
     if(f.score===null&&(f.rank!==null||f.decile!==null))refuse('RANK_WITHOUT_SCORE',ft+'.rank');
     if(f.rank!==null&&(!int(f.rank)||f.rank<1||f.rank>f.rank_n))refuse('RANK_RANGE',ft+'.rank');
     if(f.decile_status==='VALID'?!(int(f.decile)&&f.decile>=1&&f.decile<=10):f.decile!==null)refuse('DECILE_INVALID',ft+'.decile');}}
   out.set(r.company_id,r);});
  return{ok:true,value:freeze(out)};}
 catch(e){if(e instanceof Refusal)return{ok:false,code:e.code,path:e.path};throw e;}}

/* ---- words (counts and values as delivered; display rounding only) */
const fmt=v=>v===null||v===undefined?'미산출':(Math.round(v*10)/10).toFixed(1);
const scopeWord=(s,sectorName)=>{if(s==='COMMON')return'평가 집단 전체';const[,sec,tpl]=s.split('|');
 return(sectorName?sectorName(sec):sec)+' · '+(tpl==='None'||!tpl?'회계모형 미확정':tpl);};
const rankText=(b,sectorName)=>b.total===null?'총점 없음 · 순위 없음':b.rank+' / '+b.rank_n+' ('+scopeWord(b.ranking_scope,sectorName)+')';
const share=(c,d)=>String(c)+' / '+String(d);

function boardView(d,key){const b=d.summary.boards[key],M=MODELS[key],c=b.coverage,den=c.denominator,st=c.stages;
 return freeze({key,label:M.label,core:M.core,kind:KIND[M.kind],
  head:M.label+' · '+M.core+' · 연구 후보 · 운영 채택 안 됨 · 성과 미측정',
  states:[['보관 결과 조회','가능 · 목록표·요약·색인 검증됨'],['입력 연결',INPUT_WORD[d.input_check]],
   ['최종 총점',st.total.code_rows?'산출 '+share(st.total.code_rows,den.code_rows)+'코드 행':'미산출 · 이 모형의 총점 순위 없음'],
   ['화면 재계산','연결 안 됨 · 보관 결과만 보임'],
   ['저장·재현','생산자 저장본(설정·코드·두 입력 결합)으로만 · 다른 입력이면 거부 · 설정 '+b.configuration_hash.slice(0,12)+'… · 결과 '+b.result_hash.slice(0,12)+'…']],
  population:SCOPES[d.scope].label+' · '+b.evaluation_population.id+' · 코드 행 '+den.code_rows+' · 고유 발행사 '+den.issuers+' · 평가일 '+b.evaluation_population.valuation_date,
  reference:'참조집단 '+b.reference_population.id+' · 발행사 '+b.reference_population.issuers+' · 요소 입력 적격 연구 참조 · 상장·증권·투자 적격 아님 · 후보 원천 '+b.reference_population.candidate_population.code_rows+'행',
  classification:b.classification_mode==='RETROSPECTIVE_RECONSTRUCTION'?'분류: 평가일 뒤 지식으로 회고 재구성 · 당시 시스템 보유 증명 아님':'분류: 평가일 기준 분류 · 시스템 PIT 증명 아님',
  stages:STAGES.map(([k,l])=>freeze({key:k,label:l,text:'코드 행 '+share(st[k].code_rows,den.code_rows)+' · 발행사 '+share(st[k].issuers,den.issuers)})),
  target:'95% 목표 · 발행사 '+share(c.target95.issuers,den.issuers)+' · 코드 행 '+share(c.target95.code_rows,den.code_rows)
   +' · 세 축 동시 부족 발행사 '+c.gap95.joint.issuers+' · 최종 총점 부족 발행사 '+c.gap95.total.issuers,
  causes:Object.entries(c.causes).map(([k,v])=>word(k)+' ('+k+') · 발행사 '+v.issuers+' · 코드 행 '+v.code_rows),
  incomplete:'총점 미산출 코드 행 '+c.incomplete_unique.code_rows+' · 비교 표본 부족이 걸린 행 '+c.current_sample_barrier.code_rows,
  market:'전체시장 분모·커버리지 미측정 · 관측 카탈로그는 상장 전체시장이 아님'});}

const RULES=Object.freeze(['U1·U2·S1 점수는 같은 척도가 아님 · 평균·합산·차이를 만들지 않음',
 '총점이 없으면 총점 순위도 없음 · 섹터 순위를 이어 붙인 통합 순위 없음',
 '연구 후보 · 공식 QGV·기본값·포트폴리오 목표에 반영되지 않음 · 성과 미측정',
 '필터·정렬은 생산자 행을 보이는 순서만 바꾸고 점수·순위·분모·참조 N을 바꾸지 않음']);

function rowsView(d,key,{sectorName,limit=50}={}){return d.rows.slice(0,limit).map(r=>{const b=r.boards[key];
 return freeze({company_id:r.company_id,issuer_id:r.issuer_id,Q:fmt(b.axes.Q),G:fmt(b.axes.G),V:fmt(b.axes.V),total:fmt(b.total),rank:rankText(b,sectorName),
  scope:scopeWord(b.ranking_scope,sectorName),status:word(b.status),gate:word(b.gate_status)});});}

const factorText=(v,f)=>v+' · '+(f.score===null?'점수 미산출 · '+word(f.score_status):'점수 '+fmt(f.score)+' · 요소 순위 '+f.rank+' / '+f.rank_n
 +(f.decile!==null?' · 십분위 D'+f.decile:' · 십분위 없음('+(f.decile_status==='SAMPLE_LT_10'?'10개 미만':word(f.decile_status))+')'))+' · 참조 N '+(f.valid_n===null?'—':f.valid_n);

// One company in every model, side by side: each model's own words, never a difference or an average.
function compareView(row,d,{sectorName}={}){return freeze({company_id:row.company_id,
 note:'모형마다 핵심 요소·참조집단·순위 범위가 다름 · 점수 차이를 계산하지 않음',
 boards:d.models.map(k=>{const b=row.boards[k],M=MODELS[k],add=Object.entries(b.factors).filter(([,f])=>f.kind==='ADDITIONAL');
  return freeze({key:k,label:M.label,
   axes:'Q '+fmt(b.axes.Q)+' · G '+fmt(b.axes.G)+' · V '+fmt(b.axes.V)+' · 총점 '+fmt(b.total),
   rank:rankText(b,sectorName),scope:scopeWord(b.ranking_scope,sectorName),status:word(b.status)+' · '+word(b.gate_status),
   core:b.selected_variants.map(v=>factorText(v,b.factors[v])),
   additional:add.filter(([,f])=>f.score!==null).map(([v,f])=>factorText(v,f)),
   additionalMissing:add.filter(([,f])=>f.score===null).length});})});}

/* ---- the research engine route (owner 2026-11-11 §3; development bridge, tools/sector_qgv_engine_bridge.py): requests name the
   model and the candidate explicitly; an answer is used only when it is the answer to that very request (op, request id, model,
   model_id) and its board is that candidate's (qgv-dual-board/1, same model_id, no rank without a total). Nothing is computed here. */
const ENGINE=Object.freeze({REQUEST:'sector-qgv-engine-request/1',RESPONSE:'sector-qgv-engine-response/1',BOARD:'qgv-dual-board/1',SAVED:'qgv-dual-saved/1'});
const MODEL_OF=Object.freeze(Object.fromEntries(Object.entries(MODELS).map(([k,m])=>[m.model_id,Object.freeze({key:k,model:m.kind==='COMMON'?'INTEGRATED':'SECTOR'})])));
const ENGINE_OPS=Object.freeze(['context','preview','save','replay']);
const KIND_WORD=Object.freeze({SYNTHETIC_RECALCULATION:'합성 실제 재계산(지금 설정·지금 입력)',EXACT_REPLAY:'정확 재현(같은 설정·코드·원래 입력)'});
let reqSeq=0;
function engineRequest(op,model_id,fields={}){if(!ENGINE_OPS.includes(op))throw Error('DUAL_OP_UNKNOWN');const m=MODEL_OF[model_id];if(!m)throw Error('MODEL_ID_UNKNOWN');
 reqSeq=(reqSeq+1)%1e9;return Object.freeze({...fields,schema_version:ENGINE.REQUEST,op,request_id:'DUAL-'+op+'-'+m.key+'-'+reqSeq,model:m.model,model_id});}
// A saved research record (the engine's save_board answer as returned): schema, the four keys, a known candidate, hashes.
function validateSaved(x){try{exact(x,['schema_version','configuration','bindings','result_hash'],'saved');if(x.schema_version!==ENGINE.SAVED)refuse('SAVED_SCHEMA_MISMATCH','saved.schema_version');
  if(!isObj(x.configuration)||!MODEL_OF[x.configuration.model_id])refuse('MODEL_ID_UNKNOWN','saved.configuration.model_id');
  if(!isObj(x.bindings)||!HEX.test(x.bindings.model_hash)||!HEX.test(x.result_hash))refuse('HASH_INVALID','saved');return{ok:true};}
 catch(e){if(e instanceof Refusal)return{ok:false,code:e.code,path:e.path};throw e;}}
function boardCheck(b,model_id){if(!isObj(b)||b.schema_version!==ENGINE.BOARD)refuse('BOARD_SCHEMA','board');if(b.model_id!==model_id)refuse('MODEL_RESPONSE_MISMATCH','board.model_id');
 if(!HEX.test(b.result_hash)||!Array.isArray(b.rows))refuse('BOARD_INVALID','board');
 b.rows.forEach((r,i)=>{const at='board.rows['+i+']';if(!isObj(r)||!isObj(r.axes))refuse('BOARD_INVALID',at);head(r,MODEL_OF[model_id].key,at);});}
function checkAnswer(req,res){try{if(!isObj(res)||res.schema_version!==ENGINE.RESPONSE)refuse('ENGINE_ANSWER_INVALID','$');
  if(res.request_id!==req.request_id||res.op!==req.op)refuse('ENGINE_ANSWER_OTHER_REQUEST','$');
  if(res.ok!==true)return{ok:false,code:typeof res.code==='string'&&/^[A-Z][A-Z0-9_:a-z]{1,79}$/.test(res.code)?res.code:'ENGINE_FAILED',path:'$'};
  if(res.model!==req.model||res.model_id!==req.model_id)refuse('MODEL_RESPONSE_MISMATCH','$.model_id');
  if(req.op==='preview'||req.op==='replay'){boardCheck(res.board,req.model_id);
   if(res.kind!==(req.op==='preview'?'SYNTHETIC_RECALCULATION':'EXACT_REPLAY'))refuse('ANSWER_KIND','$.kind');
   if(req.op==='replay'&&res.board.result_hash!==req.saved.result_hash)refuse('REPLAY_RESULT_MISMATCH','$.board.result_hash');}
  if(req.op==='save'){const v=validateSaved(res.saved);if(!v.ok)refuse(v.code,v.path);
   if(res.saved.configuration.model_id!==req.model_id||res.saved.result_hash!==req.result_hash)refuse('MODEL_RESPONSE_MISMATCH','$.saved');}
  return{ok:true,value:res};}
 catch(e){if(e instanceof Refusal)return{ok:false,code:e.code,path:e.path};throw e;}}
function boardRowsView(b,{sectorName}={}){const key=MODEL_OF[b.model_id].key;return b.rows.map(r=>freeze({company_id:r.company_id,Q:fmt(r.axes.Q),G:fmt(r.axes.G),V:fmt(r.axes.V),
 total:fmt(r.total),rank:rankText(r,sectorName),status:word(r.status)+' · '+word(r.gate_status),key}));}

function ramStore(){let held=new Map();const ls=new Set();const tell=()=>{for(const f of[...ls]){try{f();}catch(_){}}};
 return Object.freeze({set(scope,v){if(!own(SCOPES,scope)||!CHECKED.has(v)||v.scope!==scope)throw Error('DUAL_UNCHECKED');held.set(scope,Object.freeze({delivery:v,details:new Map()}));tell();},get:scope=>held.get(scope)||null,
  drop(){if(!held.size)return;held=new Map();tell();},subscribe(f){ls.add(f);return()=>ls.delete(f);}});}
const ram=ramStore();

return Object.freeze({LINEAGE_SCHEMA,PROJECTION_FIELDS,ENGINE,MODEL_OF,KIND_WORD,engineRequest,validateSaved,checkAnswer,boardRowsView,SCHEMA,SCOPES,INPUT_CHECK,INPUT_WORD,MODELS,KIND,STAGES,RULES,word,checkDelivery,checkDetail,boardView,rowsView,compareView,ram,ramStore,MAX_BYTES});
});
