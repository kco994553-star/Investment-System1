/* Held issuer browsing reader (IS2.expandedIssuers; owner 2026-11-09 queue item 4, Codex #524 fb80b67b held-issuer-sharded/1,
   HELD_ISSUER_DELIVERY_20261108.md). The delivery is Codex's projection of retained results (no calculation here, DC-42): a manifest,
   one search index, a coverage file and detail shards expanded-detail/<sha256(issuer_id)[:2]>.json, read through the owner-checked
   private Worker (its classification route: parts expanded_manifest, expanded_index, expanded_coverage and one expanded_detail shard).
   - Trust: the manifest is accepted only when its identity names the summary already delivered in the checked classification bundle
     (SHA-256 of that summary's own bytes) and its context equals that summary's held_financial_subsample scope (valuation date,
     population, scoring population, versions, classification, result identity). A file's own hashes alone prove nothing.
   - checkBundle(parts, anchor): manifest → index and coverage, each byte for byte against the manifest (SHA-256, size, 2 MiB), the
     same identity and identity_hash (= digest of identity, Codex sector_qgv.digest: sorted keys, compact JSON), unique issuers, each
     row's shard = sha256(issuer_id)[:2] and its detail descriptor = the manifest's, count = issuer_count = population denominator.
   - checkDetail(row, part, bundle): one shard, only after a click: its bytes = the row's descriptor, schema, shard key, identity, every
     issuer in the right shard and once, the chosen issuer's context = the bundle's (context_hash checked), and the index row's fields.
     A failed detail is that detail's 연결 오류; the index and other issuers stay.
   - search(rows, q): issuer id, analysis row id, observed ticker or name; nothing ranked by a score.
   - Words: a ticker is a catalog observation (not listing proof, not a security id); an operating code row is the Universe504 row of
     the same issuer; Q 0 is a value, null is 미산출 with its status; the gate input connection is not a gate pass; the rank scope is the
     retained catalog score population, never the whole market; prices / technical stay 연결 안 됨 with their reason.
   Pure except sha256 (WebCrypto, async); no storage, no request of its own. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else{const I=root.IS2=root.IS2||{};I.expandedIssuers=api;}})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
const SCHEMA=Object.freeze({MANIFEST:'held-issuer-sharded/1',INDEX:'held-issuer-search/1',SHARD:'held-issuer-shard/1',DETAIL:'held-issuer-detail/1',COVERAGE:'retained-default-coverage/1'});
const MAX_BYTES=2*1024*1024,INDEX='expanded-index.json',COVERAGE='coverage.json',KINDS=Object.freeze(['SYNTHETIC','RETAINED_INPUT']);
const ROUTES=Object.freeze({detail_part:'expanded_detail',index_part:'expanded_index',shard_pattern:'^[0-9a-f]{2}$'});
const CONTEXT_KEYS=Object.freeze(['valuation_date','population','scoring_population','versions','classification','result_identity']);
const HEX64=/^[0-9a-f]{64}$/,SHARD=/^[0-9a-f]{2}$/;
const own=(o,k)=>Object.prototype.hasOwnProperty.call(o,k);
const isObj=v=>!!v&&typeof v==='object'&&!Array.isArray(v);
class Refusal extends Error{constructor(code,path){super(code+' '+path);this.code=code;this.path=path;}}
const refuse=(code,path)=>{throw new Refusal(code,path);};
const need=(c,code,path)=>{if(!c)refuse(code,path);};
// Codex digest: json.dumps(sort_keys=True, separators=(',',':'), ensure_ascii=False). Keys sorted by code point; numbers as JSON.
function canonical(v){if(Array.isArray(v))return'['+v.map(canonical).join(',')+']';
 if(isObj(v))return'{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canonical(v[k])).join(',')+'}';
 if(typeof v==='number'&&!Number.isFinite(v))refuse('NUMBER_INVALID','$');return JSON.stringify(v);}
const same=(a,b)=>canonical(a)===canonical(b);
function subtle(){const c=typeof globalThis==='object'&&globalThis.crypto;if(!c||!c.subtle||typeof c.subtle.digest!=='function')refuse('HASH_UNAVAILABLE','$');return c.subtle;}
async function sha256(bytes){const b=await subtle().digest('SHA-256',bytes);return[...new Uint8Array(b)].map(x=>x.toString(16).padStart(2,'0')).join('');}
const utf8=s=>new TextEncoder().encode(s);
const digest=v=>sha256(utf8(canonical(v)));
const shardOf=async id=>(await sha256(utf8(id))).slice(0,2);
const result=async fn=>{try{return{ok:true,value:await fn()};}catch(e){if(e instanceof Refusal)return{ok:false,code:e.code,path:e.path};return{ok:false,code:'INVALID',path:'$'};}};
function part(p,at){need(isObj(p)&&p.bytes instanceof Uint8Array&&isObj(p.body),'PART_MISSING',at);return p;}
async function bytesMatch(p,desc,at){need(isObj(desc)&&typeof desc.sha256==='string'&&HEX64.test(desc.sha256)&&Number.isInteger(desc.bytes),'DESCRIPTOR_INVALID',at);
 need(p.bytes.byteLength===desc.bytes&&p.bytes.byteLength<=MAX_BYTES,'DELIVERY_SIZE_MISMATCH',at);need(await sha256(p.bytes)===desc.sha256,'DELIVERY_HASH_MISMATCH',at);}
function sameIdentity(v,m,at){need(same(v.identity,m.identity)&&v.identity_hash===m.identity_hash,'IDENTITY_MISMATCH',at+'.identity');need(v.data_kind===m.data_kind,'DATA_KIND_MISMATCH',at+'.data_kind');}

// parts: {manifest, index, coverage} each {bytes, body}; anchor: {summarySha (hex of the delivered summary's bytes), held (its
// calculation_counts.scopes.held_financial_subsample)}.
function checkBundle(parts,anchor){return result(async()=>{
 const M=part(parts&&parts.manifest,'$.manifest'),m=M.body;
 need(m.schema_version===SCHEMA.MANIFEST,'SCHEMA','$.manifest.schema_version');need(KINDS.includes(m.data_kind),'DATA_KIND','$.manifest.data_kind');
 need(M.bytes.byteLength<=MAX_BYTES&&m.max_file_bytes===MAX_BYTES,'DELIVERY_SIZE_MISMATCH','$.manifest.max_file_bytes');
 need(isObj(m.identity)&&isObj(m.identity.context)&&isObj(m.identity.summary),'TYPE','$.manifest.identity');
 need(m.identity_hash===await digest(m.identity),'IDENTITY_HASH_MISMATCH','$.manifest.identity_hash');
 need(same(m.routes,ROUTES)&&m.index===INDEX,'ROUTES_MISMATCH','$.manifest.routes');
 need(Array.isArray(m.shards)&&m.shards.every(s=>typeof s==='string'&&SHARD.test(s))&&new Set(m.shards).size===m.shards.length,'SHARD_KEY_INVALID','$.manifest.shards');
 need(Array.isArray(m.files),'TYPE','$.manifest.files');const files=new Map(m.files.map(f=>[f&&f.path,f]));
 const want=new Set([INDEX,COVERAGE,...m.shards.map(s=>'expanded-detail/'+s+'.json')]);
 need(files.size===m.files.length&&files.size===want.size&&[...want].every(p=>files.has(p)),'FILE_SET_MISMATCH','$.manifest.files');
 // The anchor: the summary delivered in the checked bundle, by its bytes and its held scope.
 const ctx=m.identity.context,a=anchor||{};
 need(typeof a.summarySha==='string'&&HEX64.test(a.summarySha)&&isObj(a.held),'SUMMARY_UNAVAILABLE','$.anchor');
 need(m.identity.summary.sha256===a.summarySha,'SUMMARY_MISMATCH','$.manifest.identity.summary');
 need(m.identity.valuation_date===a.held.valuation_date,'SUMMARY_MISMATCH','$.manifest.identity.valuation_date');
 for(const k of CONTEXT_KEYS)need(same(ctx[k],a.held[k]),'SUMMARY_MISMATCH','$.manifest.identity.context.'+k);
 need(isObj(ctx.population)&&ctx.population.unit==='ISSUER'&&Number.isInteger(ctx.population.denominator)&&m.issuer_count===ctx.population.denominator,'DENOMINATOR_MISMATCH','$.manifest.issuer_count');
 // index
 const X=part(parts.index,'$.index'),x=X.body;await bytesMatch(X,files.get(INDEX),'$.index');
 need(x.schema_version===SCHEMA.INDEX,'SCHEMA','$.index.schema_version');sameIdentity(x,m,'$.index');need(Array.isArray(x.rows),'TYPE','$.index.rows');
 const ids=new Set(),rows=[];
 for(let i=0;i<x.rows.length;i++){const r=x.rows[i],at='$.index.rows['+i+']';
  need(isObj(r)&&typeof r.issuer_id==='string'&&r.issuer_id&&!ids.has(r.issuer_id),'INDEX_MEMBER_MISMATCH',at+'.issuer_id');ids.add(r.issuer_id);
  need(typeof r.shard_key==='string'&&r.shard_key===await shardOf(r.issuer_id)&&m.shards.includes(r.shard_key),'SHARD_MEMBERSHIP_MISMATCH',at+'.shard_key');
  need(same(r.detail,files.get('expanded-detail/'+r.shard_key+'.json')),'DETAIL_REF_MISMATCH',at+'.detail');
  need(Array.isArray(r.observed_tickers)&&Array.isArray(r.observed_names)&&Array.isArray(r.operating_code_rows)&&isObj(r.classification),'TYPE',at);
  rows.push(Object.freeze(r));}
 need(rows.length===m.issuer_count,'DENOMINATOR_MISMATCH','$.index.rows');
 // coverage
 const C=part(parts.coverage,'$.coverage'),c=C.body;await bytesMatch(C,files.get(COVERAGE),'$.coverage');
 need(c.schema_version===SCHEMA.COVERAGE,'SCHEMA','$.coverage.schema_version');sameIdentity(c,m,'$.coverage');need(isObj(c.scopes),'TYPE','$.coverage.scopes');
 return Object.freeze({identity:m.identity,identity_hash:m.identity_hash,data_kind:m.data_kind,rows:Object.freeze(rows),byId:new Map(rows.map(r=>[r.issuer_id,r])),
  coverage:c,shards:Object.freeze([...m.shards]),issuer_count:m.issuer_count});});}

// One detail shard for one index row of a checked bundle.
function checkDetail(row,p,bundle){return result(async()=>{
 need(bundle&&row&&bundle.byId.get(row.issuer_id)===row,'ROW_UNKNOWN','$.row');
 const D=part(p,'$.detail'),d=D.body;await bytesMatch(D,row.detail,'$.detail');
 need(d.schema_version===SCHEMA.SHARD&&d.shard_key===row.shard_key,'SHARD_SCHEMA','$.detail.schema_version');
 need(same(d.identity,bundle.identity)&&d.identity_hash===bundle.identity_hash&&d.data_kind===bundle.data_kind,'IDENTITY_MISMATCH','$.detail.identity');
 need(Array.isArray(d.issuers),'TYPE','$.detail.issuers');const seen=new Set();let hit=null;
 for(let i=0;i<d.issuers.length;i++){const s=d.issuers[i],at='$.detail.issuers['+i+']';
  need(isObj(s)&&typeof s.issuer_id==='string'&&!seen.has(s.issuer_id)&&await shardOf(s.issuer_id)===row.shard_key,'SHARD_MEMBERSHIP_MISMATCH',at+'.issuer_id');seen.add(s.issuer_id);
  if(s.issuer_id===row.issuer_id)hit=[s,at];}
 need(hit,'DETAIL_MISSING','$.detail.issuers');const[s,at]=hit;
 need(s.schema_version===SCHEMA.DETAIL,'SCHEMA',at+'.schema_version');
 need(same(s.context,bundle.identity.context)&&s.context_hash===await digest(s.context),'DETAIL_CONTEXT_MISMATCH',at+'.context');
 need(isObj(s.calculation)&&isObj(s.classification)&&Array.isArray(s.catalog_observations),'TYPE',at);
 need(s.analysis_row_id===row.analysis_row_id&&same(s.observed_names,row.observed_names)&&same(s.operating_code_rows,row.operating_code_rows)&&s.calculation.status===row.calculation_status
  &&same([...new Set(s.catalog_observations.map(o=>o.observed_ticker))].sort(),row.observed_tickers)&&['sector','accounting','industry'].every(k=>same(s.classification[k],row.classification[k])),
  'INDEX_DETAIL_MISMATCH',at);
 return Object.freeze(s);});}

// Search over the checked index: ids, observed tickers and names; exact and prefix hits first, then substring; capped.
function search(rows,q,limit=20){const t=String(q||'').trim().toUpperCase();if(!t)return[];
 const keysOf=r=>[r.issuer_id,r.analysis_row_id,...r.observed_tickers,...r.observed_names].filter(x=>typeof x==='string').map(x=>x.toUpperCase());
 const score=r=>{const k=keysOf(r);return k.includes(t)?0:k.some(x=>x.startsWith(t))?1:k.some(x=>x.includes(t))?2:3;};
 return rows.map(r=>[score(r),r]).filter(([s])=>s<3).sort((a,b)=>a[0]-b[0]||(a[1].issuer_id<b[1].issuer_id?-1:1)).slice(0,limit).map(([,r])=>r);}

/* ---------------- words */
const STATUS=Object.freeze({CONFIRMED:'확인',UNKNOWN:'미확인',CONFLICT:'근거 충돌',SECTOR_ONLY:'섹터만 확인'});
const AXIS_STATUS=Object.freeze({VALID:'값 있음',VALID_ZERO:'값 0 (유효)',MISSING_INPUT:'입력 없음',PEER_SAMPLE_SMALL:'비교 표본 부족',STALE:'오래된 자료',NOT_APPLICABLE:'해당 없음'});
const GATE=Object.freeze({CONNECTED:'연결됨',UNAVAILABLE:'연결 안 됨'});
const W=Object.freeze({
 TICKER:'카탈로그 관측 티커 · 상장 증명·증권 ID 아님',
 CODE_ROWS:'운영504의 같은 발행사 코드 행',
 RANK:'순위 없음 · 비교집단 = 보관 카탈로그 점수 모집단(전체시장 아님)',
 GATE_INPUT:'공식 Q 관문 입력 연결 · 관문 통과·새 Q 점수 아님 · 기존 Universe504 공식 Q 재생값',
 NULL:'미산출',
 TOTAL:'총점 없음 · 0으로 채우지 않음',
 PROFILE:'사업 설명 원문 전체는 전달되지 않음 · 분류 근거와 다름',
 PRICES:'가격·기술 연결 안 됨',
 PEER:'점수의 비교집단',
 NOT_MARKET:'전체시장 분모·커버리지 미측정'});
const fmt=v=>v===null||v===undefined?W.NULL:String(v);
function axisText(c,k){const v=c.axes?c.axes[k]:undefined;return k+' '+(v===null||v===undefined?W.NULL:String(v));}
function classText(x){if(!isObj(x))return W.NULL;const st=STATUS[x.status]||x.status;return(x.id?x.id+' · ':'')+st+(x.reasons&&x.reasons.length?' · 사유 '+x.reasons.join(', '):'')+
 (x.evidence_refs&&x.evidence_refs.length?' · 근거 '+x.evidence_refs.length+'건':'');}
// Input gaps as the producer wrote them: a status in words (변환 미연결 = NOT_CONNECTED, never guessed from a missing value), a list as
// its items, an object without a status as its item count. The row's own ids are not gaps.
const GAP_SKIP=Object.freeze(['company_id','issuer_id','valuation_date']);
const GAP_LABEL=Object.freeze({price:'가격',share_basis:'주식 기준',ev_components:'EV 구성요소',evaluation_security:'평가 증권',peer_sample_small_variants:'표본 부족 요소',
 v_required_fields:'V 필요 입력',financial_period_inputs:'재무 기간 입력',raw_input_diagnostics:'원지표 입력 진단',classification:'분류'});
const GAP_STATUS=Object.freeze({NOT_CONNECTED:'변환 미연결',UNCONFIRMED:'미확인',VARIANT_SCOPE_UNRESOLVED:'요소 범위 미확정(기본 선택 없음)',
 NOT_REQUIRED_BY_SELECTED_VARIANTS:'선택 요소에 필요 없음',CONNECTED:'연결됨'});
function gapText(k,v){const l=(GAP_LABEL[k]||k)+' ('+k+')';
 if(Array.isArray(v))return l+' · '+(v.length?v.join(', '):'없음');
 if(isObj(v)&&typeof v.status==='string')return l+' · '+(GAP_STATUS[v.status]?GAP_STATUS[v.status]+' ('+v.status+')':v.status)+(typeof v.reason==='string'?' · 사유 '+v.reason:'');
 if(isObj(v))return l+' · 항목 '+Object.keys(v).length+'개';return l+' · '+fmt(v);}
// One issuer detail → plain lines for the screen (labels and values; nothing computed).
function detailView(s,bundle){const c=s.calculation,ctx=bundle.identity.context,g=s.official_q_gate_input||{},sp=s.security_prices_technical||{},bp=s.business_profile||{};
 const factors=Object.entries(c.factors||{}).map(([id,f])=>Object.freeze({id,raw:AXIS_STATUS[f.raw_status]||f.raw_status,score:f.score===null?W.NULL+' · '+(AXIS_STATUS[f.score_status]||f.score_status):String(f.score),
  n:Number.isInteger(f.valid_n)?'유효 '+f.valid_n:'',selected:(c.selected_variants||[]).includes(id)}));
 const gaps=isObj(s.input_gaps)?Object.entries(s.input_gaps).filter(([k])=>!GAP_SKIP.includes(k)).map(([k,v])=>gapText(k,v)):[];
 return Object.freeze({
  id:s.issuer_id,row:s.analysis_row_id,
  tickers:s.catalog_observations.map(o=>o.observed_ticker),names:s.observed_names,codeRows:s.operating_code_rows,
  sector:classText(s.classification.sector),industry:classText(s.classification.industry),accounting:classText(s.classification.accounting),
  sic:s.classification.source_sic&&s.classification.source_sic.code?s.classification.source_sic.system+' '+s.classification.source_sic.code:W.NULL,
  applicability:s.classification.applicability&&s.classification.applicability.kind==='EVALUATION_DATE_ONLY'?'평가일 '+s.classification.applicability.valuation_date+' 기준 분류(다른 날짜에 쓰지 않음)':W.NULL,
  axes:['Q','G','V'].map(k=>axisText(c,k)).join(' · '),
  status:'계산 상태 '+(FAIL[c.status]?failText(c.status):c.status)+(c.gate_status?' · 실제 관문: '+(GATE_DECISION[c.gate_status]||c.gate_status):'')+' · 관문 전 총점 '+fmt(c.pre_gate_total)+' · '+W.TOTAL,
  rank:c.rank===null?W.RANK:'순위 '+c.rank+' ('+c.rank_scope+')',
  peer:W.PEER+' '+ctx.scoring_population.id+' '+ctx.scoring_population.denominator+'개 · 발행사 모집단 '+ctx.population.denominator+'개와 다름',
  factors:Object.freeze(factors),
  gate:W.GATE_INPUT+' · '+(GATE[g.status]||fmt(g.status))+(g.reason?' · 사유 '+g.reason:''),
  prices:W.PRICES+(sp.reason?' · '+sp.reason:''),
  profile:bp.status==='NOT_DELIVERED'?W.PROFILE:fmt(bp.description),
  gaps:Object.freeze(gaps),
  evidence:Object.freeze((Array.isArray(s.evidence)?s.evidence:[]).map(e=>Object.freeze({source:e.source_id,locator:e.locator,at:e.acquired_at,sha:typeof e.sha256==='string'?e.sha256.slice(0,12)+'…':'',url:e.url})))});}
// Coverage (Codex retained_coverage.py, retained-default-coverage/1): per scope, the producer's own stage counts in pipeline order,
// each stage its own state (owner 2026-11-09): 섹터 확인 → 회계모형 확인 → 원지표 → 요소 점수 → Q / G / V each → 세 축 동시 → 관문
// 판정 → 관문 전 총점 → 최종 총점 → 세 축 + 최종 총점 (the 95 % stage). Code rows and issuers are separate units (운영504 504 code rows
// vs 501 issuers); the held sample and the catalog keep their own denominators. Nothing is added up or derived here:
//  - the 95 % target is the producer's (all_axes_and_total over the original population); a classification or raw-input share is never
//    shown as QGV completion;
//  - the gate is the producer's gate_decisions per code row: PASS / UNKNOWN (관문 판정 불가) / VALUE_EXCLUDED (V 총점 반영 제외 — not an
//    issuer drop and not missing data); the producer's merged gate cause (UNKNOWN or VALUE_EXCLUDED) is not listed as a loss cause;
//  - causes overlap and are never summed; a cause the retained fields cannot show stays 미측정 with its known / unassessed counts;
//  - failure reasons are the producer's codes with a word; one code row has one total failure status; factor failures stay per factor
//    (row × factor counts are never added across factors); MISSING_INPUT stays one reason (the producer does not split 자료 미보유
//    from 변환 미연결 there, so neither does the screen).
const SCOPE_LABEL=Object.freeze({operating:'운영504',held_financial_subsample:'보유 재무 표본',catalog:'관측 카탈로그'});
const UNIT_LABEL=Object.freeze({operating:{code_rows:'운영504 코드 행',issuers:'운영504 고유 발행사'},held_financial_subsample:{code_rows:'보유 표본 분석 행',issuers:'보유 발행사'},
 catalog:{code_rows:'카탈로그 분석 행',issuers:'관측 카탈로그 발행사'}});
const STAGES=Object.freeze([['sector','섹터 확인','분류'],['accounting','회계모형 확인','분류'],
 ['required_components_present','기본 요소 구성요소 선언 있음(유효성·관문 통과 아님)','입력'],
 ['any_raw','원지표 1개 이상 계산','원지표'],['all_default_raw','기본 원지표 전부 계산','원지표'],
 ['any_factor_scores','요소 점수 1개 이상','요소 점수'],['all_default_factor_scores','기본 요소 점수 전부','요소 점수'],
 ['Q','Q 산출','축'],['G','G 산출','축'],['V','V 산출','축'],['joint','Q·G·V 세 축 동시','축'],
 ['pre_gate_total','관문 전 총점','총점'],['total','최종 총점','총점'],['all_axes_and_total','세 축 + 최종 총점 (95% 기준 단계)','총점']]);
const GATE_DECISION=Object.freeze({PASS:'관문 통과',UNKNOWN:'관문 판정 불가(UNKNOWN) · 최종 총점·순위 없음',
 VALUE_EXCLUDED:'V 총점 반영 제외(VALUE_EXCLUDED) · 기업 탈락·자료 미수집 아님'});
const FAIL=Object.freeze({MISSING_INPUT:'입력 관측 없음(자료 미보유·변환 미연결을 생산자가 나누지 않음)',NOT_APPLICABLE:'입력 부적격 · 산식 적용 대상 아님',
 DOMAIN_INVALID:'입력 부적격 · 값 범위 밖',PERIOD_MISMATCH:'입력 부적격 · 기간 불일치',UNIT_MISMATCH:'입력 부적격 · 단위 불일치',CURRENCY_MISMATCH:'입력 부적격 · 통화 불일치',
 PEER_SAMPLE_SMALL:'표본 부족 · 비교 표본 최소 미달',ISSUER_REPRESENTATIVE_UNRESOLVED:'발행사 대표 행 미확정',MAPPING_UNRESOLVED:'분류·회계모형 대응 미확정(기본 요소 선택 없음)',
 GATE_UNKNOWN:'관문 미확정',STRICT_INCOMPLETE:'필수 축·요소 미산출(strict)',CALCULATOR_PENDING:'변환 미연결 · 계산기 없음',NOT_YET_AVAILABLE:'평가 시점에 아직 없음',
 EVIDENCE_MISSING:'근거 없음',INPUT_INVALID:'입력 부적격'});
const failText=c=>FAIL[c]?FAIL[c]+' ('+c+')':c;
const CAUSE_LABEL=Object.freeze({classification:'분류 미확인',accounting:'회계모형 미확인',period:'기간 불일치',share_basis:'주식 기준',price:'가격',formula_applicability:'산식 적용',
 peer_sample:'비교 표본',security_identity:'증권 신원',ev_components:'EV 구성요소'});
const AGGREGATION=Object.freeze({EXISTS_ONE_ORIGINAL_ROW_WITH_COMPLETE_STAGE_NOT_CROSS_ROW_AXIS_COMBINATION:'발행사는 원래 행 하나가 단계를 모두 채울 때만 셈 · 여러 행의 축을 합치지 않음'});
const cnt=x=>isObj(x)?(x.valid===null||x.valid===undefined?'미측정':x.valid+'/'+x.denominator):'전달 안 됨';
const counter=(o,word)=>isObj(o)?Object.entries(o).map(([k,n])=>word(k)+' '+n):[];
function targetText(scope,unit,t){const own=scope==='operating';
 if(!isObj(t)||!t.goal_percent)return'95% 목표 · 미측정';
 const st=t.state==='BELOW_TARGET'?'목표 미달':t.state==='MET'?'목표 도달':t.state==='EMPTY_POPULATION'?'빈 모집단':t.state;
 return'95% 목표('+(own?'원래 모집단':'이 표본 참고 · 원래 모집단 목표 아님')+') · 기준 '+(t.stage==='all_axes_and_total'?'Q·G·V 세 축 동시 + 최종 총점':t.stage)+' · '+UNIT_LABEL[scope][unit]
  +' · 필요 '+t.minimum_valid+'/'+t.denominator+' · 현재 '+t.valid+(Number.isInteger(t.additional_required)?' · 추가 필요 '+t.additional_required:'')+' · '+st
  +(AGGREGATION[t.aggregation]&&unit==='issuers'?' · '+AGGREGATION[t.aggregation]:'');}
function unitView(scope,sc,unit){const u=sc[unit];if(!isObj(u))return null;
 const den=isObj(u.target)&&Number.isInteger(u.target.denominator)?u.target.denominator:isObj(u.Q)?u.Q.denominator:null;
 return Object.freeze({unit,label:UNIT_LABEL[scope]?UNIT_LABEL[scope][unit]:unit,denominator:den,
  stages:Object.freeze(STAGES.map(([k,l,g])=>Object.freeze({key:k,group:g,label:l,text:cnt(u[k])}))),target:targetText(scope,unit,u.target)});}
function coverageView(cov){return Object.freeze(Object.entries(cov.scopes).map(([k,sc])=>{
 const iss=unitView(k,sc,'issuers'),rows=unitView(k,sc,'code_rows');
 // Code rows apart only where they are another unit than issuers (운영504 504 vs 501).
 const units=[iss,rows&&(!iss||rows.denominator!==iss.denominator)?rows:null].filter(Boolean);
 const rowDen=rows?rows.denominator:iss?iss.denominator:null;
 const causes=isObj(sc.causes)&&isObj(sc.causes.issuers)?sc.causes.issuers:{};
 const gate=isObj(sc.gate_decisions)?['PASS','UNKNOWN','VALUE_EXCLUDED',...Object.keys(sc.gate_decisions).filter(g=>!GATE_DECISION[g]).sort()].filter(g=>own(sc.gate_decisions,g))
  .map(g=>Object.freeze({key:g,text:(GATE_DECISION[g]||g)+' '+sc.gate_decisions[g]+(Number.isInteger(rowDen)?'/'+rowDen:'')})):[];
 return Object.freeze({scope:k,label:SCOPE_LABEL[k]||k,units:Object.freeze(units),
  target:iss?iss.target:'95% 목표 · 미측정',
  gate:Object.freeze(gate),gateUnit:rows?rows.label:iss?iss.label:'',
  totalFailures:Object.freeze(counter(sc.total_failure_reasons,failText)),
  unresolved:Number.isInteger(sc.default_selection_unresolved)?'기본 요소 선택 미확정 '+sc.default_selection_unresolved+'행(분류·회계모형 대응 미확정)':null,
  causes:Object.freeze(Object.entries(causes).filter(([c])=>c!=='gate').map(([c,x])=>(CAUSE_LABEL[c]||c)+' '+(x.count===null||x.count===undefined?'미측정(확인 '+x.known_affected+' · 미평가 '+x.unassessed+')':x.count+'/'+x.denominator))),
  factors:Object.freeze(isObj(sc.factors)?Object.entries(sc.factors).sort(([a],[b])=>a<b?-1:1).map(([id,f])=>Object.freeze({id,
   text:'기본 선택 '+f.selected+' · 구성요소 '+f.components_present+' · 원지표 '+f.raw_valid+'/'+f.denominator+' · 요소 점수 '+f.score_valid+'/'+f.denominator,
   raw:Object.freeze(counter(f.raw_failures,failText)),score:Object.freeze(counter(f.score_failures,failText))})):[])});}));}
const marketText=cov=>isObj(cov.full_market)&&cov.full_market.state==='NOT_MEASURED'?W.NOT_MARKET:'전체시장 '+fmt(cov.full_market&&cov.full_market.coverage);

return Object.freeze({SCHEMA,MAX_BYTES,ROUTES,W,STAGES,GATE_DECISION,FAIL,canonical,digest,sha256,shardOf,checkBundle,checkDetail,search,detailView,coverageView,marketText});
});
