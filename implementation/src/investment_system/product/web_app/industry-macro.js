/* 공통 산업 → 매크로 근거 reader (IS2.industryMacro; owner 2026-11-09 queue item 5, Codex #525 731e4682 company-industry-macro-query/1,
   MACRO_INDUSTRY_EVIDENCE_20261108.md). Codex's query output is read as it is (DC-42): which source series an evidenced mapping links to
   each company's common industry, the series' current-query observation, and the evidence. Nothing here maps, allocates, sums, ranks,
   scores or calls a regime.
   - validate(q, {view}): the schema and the fixed nulls (aggregate_value, allocation_weights, probabilities, sector_returns), not a
     historical PIT certificate, official results unchanged; the taxonomy is the one IS2.taxonomy shows (same version, same content);
     the classification context equals the checked bundle's view (date, hash, dictionary, mapping) when a view is given; companies
     unique; each company's mapping refs, related and usable series exist; counts equal the rows; an observation with query reasons
     has no value. The first fault refuses the whole output.
   - companyView / summaryView: words. UNKNOWN stays 미확인 with its reasons and never blocks the macro current query; LINKED is a
     dated, evidenced source link, not an industry cycle, a regime, an investment signal or a QGV weight; a value 0 stays 0; a value the
     cutoff hides is null (미산출). Pure; no storage, no request. */
(function(root,factory){const api=factory(root);if(typeof module==='object'&&module.exports)module.exports=api;else{const I=root.IS2=root.IS2||{};I.industryMacro=api;}})(typeof globalThis==='object'?globalThis:this,function(root){
'use strict';
const SCHEMA='company-industry-macro-query/1',KINDS=Object.freeze(['SYNTHETIC','RETAINED_INPUT']);
const CONTEXT=Object.freeze(['valuation_date','classification_hash','dictionary_version','mapping_version']);
const NULLS=Object.freeze(['aggregate_value','allocation_weights','probabilities','sector_returns']);
const STATUS=Object.freeze(['LINKED','UNKNOWN']),RELATION=Object.freeze(['EXACT','PARTIAL','MULTIPLE','UNKNOWN']);
const own=(o,k)=>Object.prototype.hasOwnProperty.call(o,k);
const isObj=v=>!!v&&typeof v==='object'&&!Array.isArray(v);
class Refusal extends Error{constructor(code,path){super(code+' '+path);this.code=code;this.path=path;}}
const need=(c,code,path)=>{if(!c)throw new Refusal(code,path);};
const canonical=v=>Array.isArray(v)?'['+v.map(canonical).join(',')+']':isObj(v)?'{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canonical(v[k])).join(',')+'}':JSON.stringify(v);
const taxonomy=()=>{const I=root&&root.IS2;if(I&&I.taxonomy&&I.taxonomy.DATA)return I.taxonomy;try{return typeof require==='function'?require('./common-taxonomy.js'):null;}catch(_){return null;}};
const strs=a=>Array.isArray(a)&&a.every(x=>typeof x==='string'&&x);

function validate(q,{view=null}={}){
 try{
  need(isObj(q)&&q.schema_version===SCHEMA,'SCHEMA','$.schema_version');need(KINDS.includes(q.data_kind),'DATA_KIND','$.data_kind');
  for(const k of NULLS)need(own(q,k)&&q[k]===null,'NOT_NULL','$.'+k);
  need(q.historical_pit_certified===false,'PIT_CLAIMED','$.historical_pit_certified');need(q.official_results_changed===false,'OFFICIAL_CHANGED','$.official_results_changed');
  const T=taxonomy();need(T,'TAXONOMY_UNAVAILABLE','$.taxonomy');
  need(isObj(q.taxonomy)&&q.taxonomy.version===T.VERSION,'TAXONOMY_VERSION_MISMATCH','$.taxonomy.version');
  need(canonical(q.taxonomy)===canonical(T.DATA),'TAXONOMY_MISMATCH','$.taxonomy');
  const c=q.classification_context;need(isObj(c)&&CONTEXT.every(k=>typeof c[k]==='string'),'TYPE','$.classification_context');
  if(view)for(const k of CONTEXT)need(c[k]===view[k],'CLASSIFICATION_CONTEXT_MISMATCH','$.classification_context.'+k);
  need(Array.isArray(q.mappings)&&Array.isArray(q.companies)&&isObj(q.observations)&&Array.isArray(q.evidence)&&Array.isArray(q.diagnostics)&&isObj(q.counts),'TYPE','$');
  const maps=new Map();
  q.mappings.forEach((m,i)=>{const at='$.mappings['+i+']';need(isObj(m)&&typeof m.mapping_id==='string'&&typeof m.revision_id==='string','TYPE',at);
   const key=m.mapping_id+'#'+m.revision_id;need(!maps.has(key),'DUPLICATE_MAPPING',at);maps.set(key,m);
   need(RELATION.includes(m.relation)&&m.allocation_weights===null&&strs(m.series_ids)&&Array.isArray(m.targets),'MAPPING_INVALID',at);
   need((m.relation==='UNKNOWN')===(m.status==='UNKNOWN'),'MAPPING_INVALID',at+'.status');
   if(m.relation==='UNKNOWN')need(!m.targets.length&&strs(m.unknown_reasons)&&m.unknown_reasons.length,'UNKNOWN_MAPPING_REASON_REQUIRED',at);});
  const evidence=new Set(q.evidence.map(e=>e&&e.evidence_id));
  for(const m of maps.values())need((m.evidence_refs||[]).every(r=>evidence.has(r)),'MAPPING_EVIDENCE_MISSING','$.mappings');
  for(const[sid,o]of Object.entries(q.observations)){const at='$.observations.'+sid;need(isObj(o)&&o.source_id===sid&&Array.isArray(o.query_reasons),'OBSERVATION_INVALID',at);
   if(o.query_reasons.length)need(o.value===null,'OBSERVATION_VALUE_WITH_REASON',at+'.value');}
  const ids=new Set();let linked=0;
  q.companies.forEach((r,i)=>{const at='$.companies['+i+']';need(isObj(r)&&typeof r.company_id==='string'&&!ids.has(r.company_id),'COMPANY_INVALID',at);ids.add(r.company_id);
   need(STATUS.includes(r.mapping_status)&&strs(r.related_series_ids)&&strs(r.query_usable_series_ids)&&Array.isArray(r.mapping_refs)&&Array.isArray(r.mapping_reasons),'COMPANY_INVALID',at);
   if(r.mapping_status==='LINKED'){linked++;need(r.mapping_refs.length&&r.related_series_ids.length,'COMPANY_INVALID',at+'.mapping_refs');}
   else need(!r.related_series_ids.length&&r.mapping_reasons.length,'UNKNOWN_REASON_REQUIRED',at);
   for(const ref of r.mapping_refs)need(isObj(ref)&&maps.has(ref.mapping_id+'#'+ref.revision_id),'MAPPING_REF_UNKNOWN',at+'.mapping_refs');
   for(const s of r.related_series_ids)need(own(q.observations,s)||(r.series_gaps||[]).some(g=>g.series_id===s),'SERIES_UNKNOWN',at+'.related_series_ids');
   need(r.query_usable_series_ids.every(s=>r.related_series_ids.includes(s)&&own(q.observations,s)&&q.observations[s].query_usable===true&&!q.observations[s].query_reasons.length),'SERIES_NOT_USABLE',at+'.query_usable_series_ids');});
  const n=q.counts;
  need(n.company_rows===q.companies.length&&n.linked_companies===linked&&n.unique_series===Object.keys(q.observations).length
   &&n.active_mappings===q.mappings.filter(m=>m.query_status==='AVAILABLE').length,'COUNTS_MISMATCH','$.counts');
  return{ok:true,value:q};
 }catch(e){if(e instanceof Refusal)return{ok:false,code:e.code,path:e.path};return{ok:false,code:'INVALID',path:'$'};}}

const REASON=Object.freeze({EXPLICIT_MACRO_SOURCE_LINK_MISSING:'근거가 확인된 산업 대응 없음',OFFICIAL_SOURCE_INDUSTRY_DEFINITION_VERSION_SCOPE_AND_APPLICABILITY_NOT_HELD:'공식 원천 산업 정의·버전·범위·적용 기간 문서 미보유',OFFICIAL_DEFINITION_NOT_HELD:'공식 산업 정의 문서 미보유',
 EVIDENCE_NOT_AVAILABLE:'근거가 평가 시점 뒤에 확보됨',EVIDENCE_TIME_UNKNOWN:'근거 확보 시각 미확인(날짜만 있음)',OUTSIDE_APPLICABILITY:'대응 적용 기간 밖',
 OBSERVATION_NOT_AVAILABLE:'관측값이 평가 시점 뒤에 나옴',OBSERVATION_TIME_UNKNOWN:'관측 가용 시각 미확인',CURRENT_QUERY_NOT_USABLE:'현재 조회 불가',SERIES_NOT_IN_CACHE:'조회 보관본에 없음',
 CACHE_FROM_FUTURE:'조회 보관본이 평가 시점 뒤',EVIDENCE_UNVERIFIED:'근거 미검증'});
const REL=Object.freeze({EXACT:'정확 대응',PARTIAL:'부분 대응',MULTIPLE:'복수 산업 대응(비중 없음 · 나누거나 합치지 않음)',UNKNOWN:'대응 미확인'});
const reasonText=c=>REASON[c]||c;
const LINE=Object.freeze({NOT_REGIME:'산업 연결·국면 판정 아님 · 순환매 확률·투자 신호·QGV 가중치에 쓰지 않음',
 UNKNOWN_KEEPS:'산업 대응이 미확인이어도 기존 매크로 현재 조회는 그대로',PIT:'과거 시점(PIT) 검증 아님'});
function obsText(o){if(!o)return'관측 없음';
 const v=o.value===null?'미산출'+(o.query_reasons.length?' · '+o.query_reasons.map(reasonText).join(', '):''):String(o.value)+(o.unit?' '+o.unit:'');
 return o.source_id+' · '+v+' · 기간 '+(o.observation_period||'—')+' · 조회 '+(o.cache_query_at||'—')+(o.stale?' · 갱신 지연':'');}
function companyView(q,companyId){const T=taxonomy(),r=q.companies.find(x=>x.company_id===companyId);if(!r)return null;
 const maps=r.mapping_refs.map(ref=>q.mappings.find(m=>m.mapping_id===ref.mapping_id&&m.revision_id===ref.revision_id)).filter(Boolean);
 const industry=r.industry&&r.industry.id?T.industryName(r.industry.id):'하위 산업 미확인';
 return Object.freeze({id:r.company_id,status:r.mapping_status,
  industry:(r.sector&&r.sector.id?T.sectorName(r.sector.id)+' · ':'')+industry,
  head:r.mapping_status==='LINKED'?'근거 있는 원천 계열 '+r.related_series_ids.length+'개 · 현재 조회 가능 '+r.query_usable_series_ids.length+'개':'산업 대응 미확인 · '+r.mapping_reasons.map(reasonText).join(', '),
  mappings:Object.freeze(maps.map(m=>m.source.system+' '+m.source.code+' ('+m.source.version+') · '+(REL[m.relation]||m.relation)+' · 적용 '+m.valid_from+' ~ '+(m.valid_to||'')+
   (m.query_reasons&&m.query_reasons.length?' · '+m.query_reasons.map(reasonText).join(', '):''))),
  series:Object.freeze(r.related_series_ids.map(s=>obsText(q.observations[s]))),
  gaps:Object.freeze((r.series_gaps||[]).map(g=>g.series_id+' · '+g.reasons.map(reasonText).join(', '))),
  evidence:Object.freeze(maps.flatMap(m=>m.evidence_refs).map(id=>q.evidence.find(e=>e.evidence_id===id)).filter(Boolean)
   .map(e=>e.evidence_id+' · '+(e.locator||'')+' · 가용 '+(e.available_at||'—')+' · '+(e.status==='VERIFIED'?'검증됨':'미검증')))});}
function summaryView(q){const n=q.counts,unk={};for(const r of q.companies)if(r.mapping_status==='UNKNOWN')for(const x of r.mapping_reasons)unk[x]=own(unk,x)?unk[x]+1:1;
 const mapUnknown=q.mappings.filter(m=>m.relation==='UNKNOWN');
 return Object.freeze({
  head:'기업 행 '+n.company_rows+' · 산업 연결 '+n.linked_companies+' · 활성 대응 '+n.active_mappings+' · 계열 '+n.unique_series,
  context:'평가일 '+q.classification_context.valuation_date+' · 정보 기준 '+q.knowledge_as_of+' · 매크로 조회 '+q.macro_query_at+' · '+q.taxonomy.name+' ('+q.taxonomy.version+')',
  unknownMappings:mapUnknown.length?'미확인 대응 '+mapUnknown.length+'건 · '+[...new Set(mapUnknown.flatMap(m=>m.unknown_reasons))].map(reasonText).join(', '):null,
  unknownCompanies:Object.entries(unk).map(([k,c])=>reasonText(k)+' '+c+'개'),
  inactive:Object.freeze(q.mappings.filter(m=>m.relation!=='UNKNOWN'&&m.query_status!=='AVAILABLE').map(m=>m.mapping_id+' · 조회 안 함 · '+(m.query_reasons||[]).map(reasonText).join(', '))),
  diagnostics:q.diagnostics.length,not:LINE.NOT_REGIME,keeps:LINE.UNKNOWN_KEEPS,pit:LINE.PIT});}
return Object.freeze({SCHEMA,validate,companyView,summaryView,reasonText,LINE});
});
