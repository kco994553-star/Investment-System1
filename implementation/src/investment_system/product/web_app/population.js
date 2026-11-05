/* Population scope reader (IS2.population; owner 2026-11-05 follow-up item 3): Universe504 and the current expansion population
   kept apart, each with its own searchable / QGV-computable / rankable counts. The calculation is Codex's (DC-42); this file only
   checks, reads and words it. validate / expansionView / universeView are pure and run in node as in the page.
   - Expansion: current-expansion-research/1 (#482 bbe62aed, research/current_expansion.py and
     docs/research/CURRENT_EXPANSION_PIPELINE_20261105.md), private research, universe U-US-EXPANDED-CURRENT/1, never the official
     population (policy.official_universe_replaced false). Its counts are different stages (candidate rows, financial rows, eligible,
     excluded, unknown, scored) and never one denominator. Without a complete dated IEX roster the full-market denominator, the coverage
     and every score / rank are null: shown as 미확정 with the reasons, never 0, and a partial roster is never called the whole market.
   - Universe504: the public page (IS2.qgv) and the one company list (IS2.companies): searchable codes, rows with a QGV total, rows
     with an official rank. Read from what the layer already holds; no new file.
   - The first fault refuses the whole input ({ok:false, code, path}); nothing is repaired or filled. source() is NONE (no request)
     until a private connection is approved; tests put Codex's synthetic output in its place. A source_ref starting SYNTHETIC: is
     shown as 합성 개발 검증.
   - Evidence stages: current-expansion-staged-evidence/1 (#500 589fd980, research/current_evidence_bridge.py and
     docs/research/CURRENT_EVIDENCE_BRIDGE_20261105.md) wraps the evaluator result under `evaluation` (the CLI's current-expansion.json)
     and adds per-row stages joined by evaluation_observation_id (original_observation_id kept for lineage). Each stage is its own
     row with its own count and denominator: 재무 연결 (issuer_link), 증권 설명 (security_type_evidence), 평가일 동일 증권
     (same_security_at_basis on the basis day S), 외부 증권 ID, 대표 증권, 시총 적격성. A documentary type is never eligibility; a
     stage that claims more than its state (a value, an ELIGIBLE row without representative and market cap, an EXCLUDED row without
     identity on S) is refused whole, as is any unknown state. The old current-expansion-research/1 is still read; its stage rows
     say NA (not evaluated), never 0.
   - Financial-sector V candidate inputs (#499 b182cbe0, financial-v-held-bridge/1, docs/research/FINANCIAL_V_HELD_BRIDGE_20261105.md):
     only the summary is read, as one separate line 금융업 후보 입력 (연구) · 공식 QGV와 별개 (prepared numerators vs same-day
     prices of each subtype's primary metric). Its population is the fixed 504 financial codes but it is research, never in the
     Universe504 card and never QGV coverage (a summary claiming joint coverage or preset totals is refused). financialSource() is
     NONE (no request). */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else{const I=root.IS2=root.IS2||{};I.population=api;}})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
const SCHEMA='current-expansion-research/1';
const UNIVERSE='U-US-EXPANDED-CURRENT/1';
const COUNTS=Object.freeze(['candidate_rows','unique_tickers','unique_issuers','financial_rows','fixed_security_ids','eligible','excluded','unknown','scored']);
const COVERAGE=Object.freeze(['denominator','Q','G','V','simultaneous','ranked','preset_actual_total']);
const ELIGIBILITY=Object.freeze(['ELIGIBLE','EXCLUDED','UNKNOWN']);
const STAGED='current-expansion-staged-evidence/1';
// #500 stage states; anything else refuses the file (no future state is guessed).
const STAGES=Object.freeze({
 issuer_link:Object.freeze(['SUBMISSIONS_CORROBORATED','CATALOG_ONLY']),
 security_type_evidence:Object.freeze(['DOCUMENTED_AT_BASIS','DOCUMENTED_ARCHIVED_TYPE','UNKNOWN']),
 same_security_at_basis:Object.freeze(['DOCUMENTED_AT_BASIS','DOCUMENTED_OUTSIDE_BASIS','ARCHIVED_DESCRIPTION_ONLY','UNKNOWN']),
 external_fixed_id:Object.freeze(['UNVERIFIED_INPUT','NOT_SUPPLIED']),
 representative:Object.freeze(['UNCONFIRMED']),
 market_cap_eligibility:Object.freeze(['NOT_COMPUTED'])});
const CURRENT_TYPES=Object.freeze(['COMMON','COMMON_CLASS','PREFERRED']);
const VALUATION=Object.freeze({shares:'UNCONFIRMED_FOR_MARKET_CAP',price:'NOT_SUPPLIED',currency:'UNCONFIRMED_FOR_PRICE',actions:'UNCONFIRMED_FOR_SHARE_PRICE_LINK'});
const CAP_BLOCKER=Object.freeze({ALL_CLASS_SHARES_UNCONFIRMED:'전 종류 같은 날 주식수 미확인',SAME_DAY_RAW_PRICE_MISSING:'같은 날 원 주가 없음',
 QUOTE_SECURITY_LINK_MISSING:'주가–증권 연결 없음',PRICE_CURRENCY_UNCONFIRMED:'주가 통화 미확인',SHARE_PRICE_ACTION_SCALE_UNCONFIRMED:'주식수·주가 조정 척도 미확인'});
const FIN_SCHEMA='financial-v-held-bridge/1';
const FIN_METRIC=Object.freeze(['numerator_present','positive_numerator','same_date_price_present','ratio_valid']);
const ROSTER_REASON='COMPLETE_CURRENT_IEX_ROSTER_UNCONFIRMED';
const REASON=Object.freeze({
 COMPLETE_CURRENT_IEX_ROSTER_UNCONFIRMED:'평가일의 완전한 IEX 거래 목록 미확인',ELIGIBILITY_UNRESOLVED:'적격 여부 미확정 행 있음',
 DUPLICATE_SECURITY_ID:'증권 ID 중복',MULTIPLE_ISSUER_REPRESENTATIVES:'한 발행사에 대표 증권 여러 개',FINANCIAL_IDENTITY_OR_TIME_MISMATCH:'재무 입력의 발행사·시각 불일치'});
const reasonText=c=>Object.prototype.hasOwnProperty.call(REASON,c)?REASON[c]:'사유 코드 '+c;
const SCOPE_TEXT=Object.freeze({IEX_TRADABLE:'평가일 IEX 거래 가능 목록',SEC_TICKER_OBSERVATIONS:'SEC 티커 관측 목록 (검색용 · IEX 목록 아님)',
 HELD_FINANCIAL_CROSSWALK_SUBSET:'보유 재무 연결 부분 목록 (IEX 목록 아님)'});
const TEXT=Object.freeze({
 NONE:'확장 모집단 연구 결과 미연결 · 비공개 연구 결과이며 공개 화면 연결은 승인 전입니다',
 SEPARATE:'Universe504(공식 운영)와 확장 모집단(연구)은 다른 모집단입니다 · 확장 결과는 공식 점수·순위·TARGET을 바꾸지 않습니다',
 SYNTHETIC:'합성 개발 검증 · 실제 시장 자료 아님',
 PARTIAL:'부분 목록 · 전체 시장 분모 미확정 · 점수·순위 없음',
 STAGES:'증거 단계는 따로 셉니다 · 문서상 증권 종류는 적격이 아니며 대표 증권도 아닙니다',
 FIN_LABEL:'금융업 후보 입력 (연구) · 공식 QGV와 별개',
 FIN_NONE:'금융업 후보 입력 (연구) · 공식 QGV와 별개 · 비공개 연구 결과 미연결'});

const isObj=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
const own=(o,k)=>Object.prototype.hasOwnProperty.call(o,k);
const nat=v=>Number.isInteger(v)&&v>=0;
// A Counter of states (#500 counts.stages) omits a state no row has: on an evaluated stage that absence is a counted 0, not NA.
const tallied=(o,k)=>own(o,k)?o[k]:0;
const DATE=/^\d{4}-\d{2}-\d{2}$/,TIME=/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$/;
function deepFreeze(v){if(v&&typeof v==='object'&&!Object.isFrozen(v)){Object.freeze(v);for(const x of Object.values(v))deepFreeze(x);}return v;}
class Refused extends Error{constructor(code,path){super(code);this.code=code;this.path=path;}}
const refuse=(code,path)=>{throw new Refused(code,path);};

function check(x){
 if(!isObj(x))refuse('NOT_OBJECT','$');
 if(x.schema_version!==SCHEMA)refuse('SCHEMA_VERSION','$.schema_version');
 if(x.visibility!=='PRIVATE_RESEARCH')refuse('VISIBILITY','$.visibility');
 if(x.universe_version!==UNIVERSE)refuse('UNIVERSE_VERSION','$.universe_version');
 if(typeof x.calc_version!=='string'||!x.calc_version)refuse('CALC_VERSION','$.calc_version');
 if(typeof x.basis_date!=='string'||!DATE.test(x.basis_date))refuse('DATE_INVALID','$.basis_date');
 if(!isObj(x.policy)||x.policy.official_universe_replaced!==false)refuse('OFFICIAL_REPLACED','$.policy.official_universe_replaced');
 const s=x.source;if(!isObj(s))refuse('SOURCE','$.source');
 if(typeof s.source_ref!=='string'||!s.source_ref)refuse('SOURCE','$.source.source_ref');
 if(typeof s.observed_at!=='string'||!TIME.test(s.observed_at))refuse('DATE_INVALID','$.source.observed_at');
 if(typeof s.scope!=='string'||!s.scope)refuse('SOURCE','$.source.scope');
 if(typeof s.complete!=='boolean')refuse('SOURCE','$.source.complete');
 if(!Array.isArray(x.population_reasons)||x.population_reasons.some(r=>typeof r!=='string'||!/^[A-Z][A-Z0-9_]{1,63}$/.test(r)))refuse('REASONS','$.population_reasons');
 const rs=x.population_reasons,c=x.counts,v=x.coverage;
 if(!isObj(c))refuse('COUNTS','$.counts');for(const k of COUNTS)if(!nat(c[k]))refuse('COUNT_INVALID','$.counts.'+k);
 if(!isObj(v))refuse('COVERAGE','$.coverage');for(const k of COVERAGE)if(!own(v,k)||!(v[k]===null||nat(v[k])))refuse('COUNT_INVALID','$.coverage.'+k);
 if(!own(v,'factors')||!(v.factors===null||isObj(v.factors)&&Object.values(v.factors).every(nat)))refuse('COUNT_INVALID','$.coverage.factors');
 if(!Array.isArray(x.rows))refuse('ROWS','$.rows');
 // A partial roster is never the whole market: the roster reason ⇔ no full-market denominator; an incomplete source carries it.
 const roster=rs.includes(ROSTER_REASON);
 if(s.complete!==true&&!roster)refuse('PARTIAL_AS_FULL_MARKET','$.population_reasons');
 if(roster!==(x.full_market_denominator===null))refuse('PARTIAL_AS_FULL_MARKET','$.full_market_denominator');
 if(!roster&&x.full_market_denominator!==x.rows.length)refuse('COUNT_MISMATCH','$.full_market_denominator');
 // Coverage exists only for an established population (no reason), and then its denominator is the eligible count.
 if(rs.length){if(COVERAGE.some(k=>v[k]!==null)||v.factors!==null)refuse('COVERAGE_WITHOUT_POPULATION','$.coverage');if(c.scored!==0)refuse('COUNT_MISMATCH','$.counts.scored');}
 else{if(COVERAGE.some(k=>v[k]===null))refuse('COUNT_INVALID','$.coverage');if(v.denominator!==c.eligible)refuse('COUNT_MISMATCH','$.coverage.denominator');
  for(const k of['Q','G','V','simultaneous','ranked','preset_actual_total'])if(v[k]>v.denominator)refuse('COUNT_MISMATCH','$.coverage.'+k);}
 if(c.candidate_rows!==x.rows.length)refuse('COUNT_MISMATCH','$.counts.candidate_rows');
 if(c.eligible+c.excluded+c.unknown!==c.candidate_rows)refuse('COUNT_MISMATCH','$.counts');
 if(c.scored>c.eligible||c.financial_rows>c.candidate_rows)refuse('COUNT_MISMATCH','$.counts');
 const tally={ELIGIBLE:0,EXCLUDED:0,UNKNOWN:0};let fin=0,ranked=0;
 x.rows.forEach((r,i)=>{const at='$.rows['+i+']';if(!isObj(r))refuse('ROW',at);
  if(typeof r.searchable!=='boolean')refuse('ROW',at+'.searchable');if(!ELIGIBILITY.includes(r.eligibility))refuse('ROW',at+'.eligibility');
  if(typeof r.financial_available!=='boolean')refuse('ROW',at+'.financial_available');if(!Array.isArray(r.reasons))refuse('ROW',at+'.reasons');
  if(!(r.rank===null||Number.isInteger(r.rank)&&r.rank>0))refuse('ROW',at+'.rank');
  if(rs.length&&(r.score!==null||r.rank!==null))refuse('SCORE_WITHOUT_POPULATION',at);
  if(r.eligibility!=='ELIGIBLE'&&r.rank!==null)refuse('SCORE_WITHOUT_POPULATION',at+'.rank');
  tally[r.eligibility]++;if(r.financial_available)fin++;if(r.rank!==null)ranked++;});
 if(tally.ELIGIBLE!==c.eligible||tally.EXCLUDED!==c.excluded||tally.UNKNOWN!==c.unknown)refuse('COUNT_MISMATCH','$.counts');
 if(fin!==c.financial_rows)refuse('COUNT_MISMATCH','$.counts.financial_rows');
 if(!rs.length&&ranked!==v.ranked)refuse('COUNT_MISMATCH','$.coverage.ranked');}

// #500 staged evidence: the evaluator result sits under `evaluation` and is checked by check() as before (paths under
// $.evaluation); each staged row joins it by evaluation_observation_id and may claim no more than its own state.
function checkStaged(x){
 if(x.visibility!=='PRIVATE_RESEARCH')refuse('VISIBILITY','$.visibility');
 if(typeof x.basis_date!=='string'||!DATE.test(x.basis_date))refuse('DATE_INVALID','$.basis_date');
 const S=x.basis_date,e=x.evaluation;
 if(!isObj(e))refuse('EVALUATION_MISSING','$.evaluation');
 try{check(e);}catch(err){if(err instanceof Refused)refuse(err.code,'$.evaluation'+err.path.slice(1));throw err;}
 if(e.basis_date!==S)refuse('BASIS_DATE_MISMATCH','$.evaluation.basis_date');
 if(!Array.isArray(x.rows))refuse('ROWS','$.rows');
 if(x.rows.length!==e.rows.length)refuse('COUNT_MISMATCH','$.rows');
 const c=x.counts;if(!isObj(c)||!nat(c.candidate_rows)||!nat(c.unique_issuers)||!isObj(c.stages))refuse('COUNTS','$.counts');
 if(c.candidate_rows!==x.rows.length)refuse('COUNT_MISMATCH','$.counts.candidate_rows');
 const tally={};for(const k of Object.keys(STAGES))tally[k]={};
 const seen=new Set(),issuers=new Set();
 x.rows.forEach((r,i)=>{const at='$.rows['+i+']',ev=e.rows[i];if(!isObj(r))refuse('ROW',at);
  if(typeof r.original_observation_id!=='string'||!/^(0|[1-9][0-9]*)$/.test(r.original_observation_id))refuse('ROW',at+'.original_observation_id');
  if(seen.has(r.original_observation_id))refuse('DUPLICATE_OBSERVATION_ID',at+'.original_observation_id');seen.add(r.original_observation_id);
  if(r.evaluation_observation_id!==String(i)||ev.observation_id!==r.evaluation_observation_id)refuse('JOIN_MISMATCH',at+'.evaluation_observation_id');
  if(r.cik!==ev.cik||r.ticker!==ev.ticker)refuse('JOIN_MISMATCH',at+'.cik');
  if(typeof r.cik!=='string'||!/^[0-9]{10}$/.test(r.cik))refuse('ROW',at+'.cik');issuers.add(r.cik);
  const g=r.stages;if(!isObj(g))refuse('ROW',at+'.stages');
  for(const k of Object.keys(STAGES)){const st=g[k];if(!isObj(st)||!STAGES[k].includes(st.state))refuse('STAGE_STATE',at+'.stages.'+k+'.state');tally[k][st.state]=tallied(tally[k],st.state)+1;}
  const link=g.issuer_link,type=g.security_type_evidence,same=g.same_security_at_basis,ext=g.external_fixed_id,rep=g.representative,cap=g.market_cap_eligibility;
  const P=(k)=>at+'.stages.'+k;
  if(link.exact_ticker_match!==(link.state==='SUBMISSIONS_CORROBORATED'))refuse('STAGE_PROMOTED',P('issuer_link.exact_ticker_match'));
  if(typeof link.financial_available!=='boolean'||link.financial_available!==ev.financial_available)refuse('JOIN_MISMATCH',P('issuer_link.financial_available'));
  // Identity on S needs its own dated document covering S; a type at S needs identity at S. Documentary type is not eligibility.
  const atS=same.state==='DOCUMENTED_AT_BASIS';
  if(same.basis_date!==S)refuse('BASIS_DATE_MISMATCH',P('same_security_at_basis.basis_date'));
  if(same.value!==(atS?true:null)||(same.reason===null)!==atS)refuse('STAGE_PROMOTED',P('same_security_at_basis.value'));
  if(atS&&!(typeof same.valid_from==='string'&&DATE.test(same.valid_from)&&same.valid_from<=S&&typeof same.valid_to==='string'&&DATE.test(same.valid_to)&&S<=same.valid_to))refuse('STAGE_PROMOTED',P('same_security_at_basis.valid_from'));
  if(!(type.current_type===null||CURRENT_TYPES.includes(type.current_type)))refuse('STAGE_STATE',P('security_type_evidence.current_type'));
  if((type.state==='DOCUMENTED_AT_BASIS')!==(type.current_type!==null)||(type.current_type!==null&&!atS))refuse('STAGE_PROMOTED',P('security_type_evidence.current_type'));
  if(ext.value!==null)refuse('STAGE_PROMOTED',P('external_fixed_id.value'));
  if((ext.state==='UNVERIFIED_INPUT')!==(typeof ext.supplied_value==='string'&&ext.supplied_value!==''))refuse('STAGE_STATE',P('external_fixed_id.supplied_value'));
  if(rep.value!==null)refuse('STAGE_PROMOTED',P('representative.value'));
  if(cap.value!==null||cap.issuer_market_cap_usd!==null)refuse('STAGE_PROMOTED',P('market_cap_eligibility.value'));
  if(!Array.isArray(cap.reasons)||!cap.reasons.length||cap.reasons.some(b=>!own(CAP_BLOCKER,b)))refuse('STAGE_STATE',P('market_cap_eligibility.reasons'));
  const vi=g.valuation_inputs;if(!isObj(vi))refuse('ROW',P('valuation_inputs'));
  for(const k of Object.keys(VALUATION))if(!isObj(vi[k])||vi[k].state!==VALUATION[k])refuse('STAGE_STATE',P('valuation_inputs.'+k+'.state'));
  if(vi.price.value!==null||vi.shares.all_class_same_day_shares!==null||vi.currency.price_currency!==null)refuse('STAGE_PROMOTED',P('valuation_inputs'));
  if(!isObj(r.pipeline_result)||r.pipeline_result.eligibility!==ev.eligibility)refuse('JOIN_MISMATCH',at+'.pipeline_result.eligibility');
  // No stage establishes representative or market cap, so nothing can be eligible; an exclusion needs identity on S.
  if(ev.eligibility==='ELIGIBLE'||ev.eligibility==='EXCLUDED'&&!atS)refuse('STAGE_PROMOTED','$.evaluation.rows['+i+'].eligibility');});
 if(issuers.size!==c.unique_issuers)refuse('COUNT_MISMATCH','$.counts.unique_issuers');
 for(const k of Object.keys(STAGES)){const got=c.stages[k];if(!isObj(got))refuse('COUNTS','$.counts.stages.'+k);
  for(const [st,n] of Object.entries(got)){if(!STAGES[k].includes(st))refuse('STAGE_STATE','$.counts.stages.'+k+'.'+st);if(!nat(n))refuse('COUNT_INVALID','$.counts.stages.'+k+'.'+st);}
  for(const st of STAGES[k])if(tallied(got,st)!==tallied(tally[k],st))refuse('COUNT_MISMATCH','$.counts.stages.'+k+'.'+st);}}

function validate(json){try{
  if(!isObj(json))refuse('NOT_OBJECT','$');
  if(json.schema_version===STAGED)checkStaged(json);else check(json);
  return{ok:true,value:deepFreeze(JSON.parse(JSON.stringify(json)))};}
 catch(e){if(e instanceof Refused)return{ok:false,code:e.code,path:e.path};return{ok:false,code:'NOT_OBJECT',path:'$'};}}

const unset=(n,why)=>n===null?'미확정 · '+why:fmt(n);
const fmt=n=>Number(n).toLocaleString('en-US');
const R=(id,label,value,note)=>Object.freeze({id,label,value,note:note||null});
const STAGE_ROWS=Object.freeze([['issuer','재무 연결'],['type','증권 설명'],['identity','평가일 동일 증권'],['external','외부 증권 ID'],['representative','대표 증권'],['cap','시총 적격성']]);
// One row per #500 stage, each with its own count and denominator. A stage that was not evaluated (an older result) is NA with the
// reason, never 0; 시총 적격성 is NA (not computed) with each blocker counted. A real 0 is shown only for an evaluated stage.
function stageRows(x){
 if(!x)return STAGE_ROWS.map(([id,label])=>R(id,label,'NA · 증거 단계 평가 없음','이전 결과 형식(current-expansion-research/1)에는 이 단계가 없음'));
 const T=x.counts.stages,k=(st,v)=>tallied(T[st],v),n=x.rows.length,of=' / 티커 관측 '+fmt(n),S=x.basis_date;
 const blockers=Object.keys(CAP_BLOCKER).map(b=>[b,x.rows.filter(r=>r.stages.market_cap_eligibility.reasons.includes(b)).length]).filter(([,m])=>m>0);
 const count=(st,f)=>x.rows.filter(r=>f(r.stages[st])).length;
 const typed=k('security_type_evidence','DOCUMENTED_ARCHIVED_TYPE')+k('security_type_evidence','DOCUMENTED_AT_BASIS');
 return[
  R('issuer','재무 연결',fmt(k('issuer_link','SUBMISSIONS_CORROBORATED'))+of,'제출 목록 티커 일치 · 카탈로그만 '+fmt(k('issuer_link','CATALOG_ONLY'))+' · 발행사 '+fmt(x.counts.unique_issuers)+' · 티커 관측은 증권 연속성이 아님'),
  R('type','증권 설명',fmt(typed)+of,'보관 문서의 증권 종류 설명 · 적격 판정 아님 · 평가일 S 적용 '+fmt(k('security_type_evidence','DOCUMENTED_AT_BASIS'))+' · 설명 없음 '+fmt(k('security_type_evidence','UNKNOWN'))),
  R('identity','평가일 동일 증권',fmt(k('same_security_at_basis','DOCUMENTED_AT_BASIS'))+of+' · S '+S,'S 밖 문서 '+fmt(k('same_security_at_basis','DOCUMENTED_OUTSIDE_BASIS'))+' · 보관 설명만 '+fmt(k('same_security_at_basis','ARCHIVED_DESCRIPTION_ONLY'))+' · 증거 없음 '+fmt(k('same_security_at_basis','UNKNOWN'))+' · 문서 기간이 S를 덮을 때만 셈'),
  R('external','외부 증권 ID','확인 '+fmt(count('external_fixed_id',q=>q.value!==null))+of,'입력만 있음(미검증) '+fmt(k('external_fixed_id','UNVERIFIED_INPUT'))+' · 없음 '+fmt(k('external_fixed_id','NOT_SUPPLIED'))+' · CIK·티커·행 번호로 만들지 않음'),
  R('representative','대표 증권','확정 '+fmt(count('representative',q=>q.value===true))+' / 발행사 '+fmt(x.counts.unique_issuers),'미확인 '+fmt(k('representative','UNCONFIRMED'))+'행 · 티커 수로 대표 증권을 정하지 않음'),
  R('cap','시총 적격성','NA · 미산출 '+fmt(k('market_cap_eligibility','NOT_COMPUTED'))+of,blockers.map(([b,m])=>CAP_BLOCKER[b]+' '+fmt(m)).join(' · '))];}
// Words of a validated expansion result (current-expansion-research/1, or #500's staged evidence around it). Each stage keeps its
// own row and label; null is 미확정 with the reason, never 0.
function expansionView(input){const staged=input.schema_version===STAGED,x=staged?input.evaluation:input;
 const c=x.counts,v=x.coverage,rs=x.population_reasons,why=rs.length?rs.map(reasonText).join(' · '):'';
 const searchable=x.rows.filter(r=>r.searchable).length;
 return Object.freeze({synthetic:x.source.source_ref.startsWith('SYNTHETIC:'),partial:x.full_market_denominator===null,staged,
  basis:'평가일(S) '+x.basis_date+' · 목록 관측 '+x.source.observed_at+' · '+(own(SCOPE_TEXT,x.source.scope)?SCOPE_TEXT[x.source.scope]:x.source.scope)+(x.source.complete?' · 완전 목록':' · 부분 목록'),
  version:(staged?STAGED+' · ':'')+x.universe_version+' · '+x.calc_version,reasons:Object.freeze(rs.map(reasonText)),
  rows:Object.freeze([
   R('searchable','검색 가능',fmt(searchable)+' / 후보 '+fmt(c.candidate_rows),'증권 ID 확정 '+fmt(c.fixed_security_ids)+' · 발행사 '+fmt(c.unique_issuers)),
   R('market','전체 시장 분모',unset(x.full_market_denominator,'완전한 IEX 목록 없음'),x.full_market_denominator===null?'부분 목록을 전체 시장으로 표시하지 않음':null),
   ...stageRows(staged?input:null),
   R('eligibility','적격 · 제외 · 미확정',fmt(c.eligible)+' · '+fmt(c.excluded)+' · '+fmt(c.unknown),staged?'증거 단계 수는 적격 수가 아님':null),
   R('financial','재무 자료 보유',fmt(c.financial_rows),'보유 못 한 행도 분모에 남음'),
   R('qgv','QGV 계산 가능',v.denominator===null?unset(null,why):'Q '+v.Q+' · G '+v.G+' · V '+v.V+' · 세 축 '+v.simultaneous+' / '+v.denominator,v.denominator===null?null:'기본 총점 실행 '+v.preset_actual_total),
   R('rank','순위 가능',v.ranked===null?unset(null,why):fmt(v.ranked)+' / '+fmt(v.denominator),v.ranked===0?'V 없는 총점은 QG 참고 순서만':null)])});}

// #499 financial-sector V candidate inputs: the summary only (subtype counts, no company value). Separate from the official QGV:
// a summary claiming joint coverage or preset totals, or another operational denominator, is refused whole.
function checkFinancial(x){
 if(!isObj(x))refuse('NOT_OBJECT','$');
 if(x.schema_version!==FIN_SCHEMA)refuse('SCHEMA_VERSION','$.schema_version');
 if(typeof x.valuation_date!=='string'||!DATE.test(x.valuation_date))refuse('DATE_INVALID','$.valuation_date');
 const m=x.summary;if(!isObj(m))refuse('SUMMARY','$.summary');
 if(m.scored_joint_valid!==null)refuse('QGV_COVERAGE_CLAIMED','$.summary.scored_joint_valid');
 if(m.preset_totals!==null)refuse('QGV_COVERAGE_CLAIMED','$.summary.preset_totals');
 if(m.operational_denominator!==504)refuse('OPERATIONAL_DENOMINATOR','$.summary.operational_denominator');
 if(!nat(m.financial_codes))refuse('COUNT_INVALID','$.summary.financial_codes');
 if(!nat(m.same_date_primary_available))refuse('COUNT_INVALID','$.summary.same_date_primary_available');
 if(!isObj(m.subtypes))refuse('SUMMARY','$.summary.subtypes');
 let codes=0,primary=0;
 for(const[g,s]of Object.entries(m.subtypes)){const at='$.summary.subtypes.'+g;
  if(!isObj(s)||!nat(s.codes)||!nat(s.primary_available)||!isObj(s.metrics))refuse('COUNT_INVALID',at);
  if(typeof s.primary_metric!=='string'||!own(s.metrics,s.primary_metric))refuse('SUMMARY',at+'.primary_metric');
  if(s.primary_available>s.codes)refuse('COUNT_MISMATCH',at+'.primary_available');
  for(const[k,q]of Object.entries(s.metrics)){const w=at+'.metrics.'+k;if(!isObj(q))refuse('COUNT_INVALID',w);
   for(const f of FIN_METRIC)if(!nat(q[f])||q[f]>s.codes)refuse('COUNT_INVALID',w+'.'+f);
   if(q.positive_numerator>q.numerator_present||q.ratio_valid>q.positive_numerator||q.ratio_valid>q.same_date_price_present)refuse('COUNT_MISMATCH',w);}
  codes+=s.codes;primary+=s.primary_available;}
 if(codes!==m.financial_codes)refuse('COUNT_MISMATCH','$.summary.financial_codes');
 if(primary!==m.same_date_primary_available)refuse('COUNT_MISMATCH','$.summary.same_date_primary_available');
 if(own(x,'rows')&&!(Array.isArray(x.rows)&&x.rows.length===m.financial_codes))refuse('COUNT_MISMATCH','$.rows');}
function financialValidate(json){try{checkFinancial(json);return{ok:true,value:deepFreeze({schema_version:json.schema_version,valuation_date:json.valuation_date,summary:JSON.parse(JSON.stringify(json.summary))})};}
 catch(e){if(e instanceof Refused)return{ok:false,code:e.code,path:e.path};return{ok:false,code:'NOT_OBJECT',path:'$'};}}
// One line: per subtype's primary metric, prepared numerators vs same-day prices vs ratios whose price matched date, basis and unit.
function financialView(x){const m=x.summary;let num=0,px=0,ok=0;
 for(const s of Object.values(m.subtypes)){const q=s.metrics[s.primary_metric];num+=q.numerator_present;px+=q.same_date_price_present;ok+=q.ratio_valid;}
 return Object.freeze({label:TEXT.FIN_LABEL,value:'분자 준비 '+fmt(num)+' · 같은 날 주가 '+fmt(px)+' · 기준 맞는 비율 '+fmt(ok)+' / 금융업 코드 '+fmt(m.financial_codes),
  note:'업종별 주 지표 기준 · 평가일 '+x.valuation_date+' · 공식 QGV 커버리지·점수·순위 아님 · 하위 업종 '+fmt(Object.keys(m.subtypes).length)});}

// Universe504 from what the layer holds: the company list and the public QGV page (IS2.qgv.rows(pg, {scope:'UNIVERSE'})).
function universeView({codes,rows,asOf}){const list=Array.isArray(codes)?codes:[],rs=Array.isArray(rows)?rows:null,later=rows===undefined;
 const none=later?'QGV 화면을 열면 셉니다 · 첫 화면은 점수 파일을 읽지 않음':'미확정 · 점수 파일 없음';
 const total=rs?rs.filter(r=>r&&r.score&&r.score.total!==null).length:null,ranked=rs?rs.filter(r=>r&&r.rank&&Number.isInteger(r.rank.official)).length:null;
 return Object.freeze({basis:'공식 운영 모집단 · 고정 504 코드'+(asOf?' · 점수 기준 '+asOf:''),
  rows:Object.freeze([
   Object.freeze({id:'searchable',label:'검색 가능',value:String(list.length),note:'Universe504 코드 목록'}),
   Object.freeze({id:'qgv',label:'QGV 총점 산출',value:rs?String(total)+' / '+rs.length:none,note:null}),
   Object.freeze({id:'rank',label:'공식 순위',value:rs?String(ranked)+' / '+rs.length:none,note:'공개 점수 파일의 공식 순위'})])});}

function source(){return Promise.resolve(Object.freeze({state:'NONE',code:'EXPANSION_NOT_CONNECTED',payload:null,text:TEXT.NONE}));}
function financialSource(){return Promise.resolve(Object.freeze({state:'NONE',code:'FINANCIAL_V_NOT_CONNECTED',payload:null,text:TEXT.FIN_NONE}));}
return Object.freeze({SCHEMA,STAGED,FIN_SCHEMA,UNIVERSE,TEXT,validate,expansionView,universeView,reasonText,source,financialValidate,financialView,financialSource});
});
