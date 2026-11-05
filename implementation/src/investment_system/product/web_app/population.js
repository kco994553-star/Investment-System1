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
     shown as 합성 개발 검증. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else{const I=root.IS2=root.IS2||{};I.population=api;}})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
const SCHEMA='current-expansion-research/1';
const UNIVERSE='U-US-EXPANDED-CURRENT/1';
const COUNTS=Object.freeze(['candidate_rows','unique_tickers','unique_issuers','financial_rows','fixed_security_ids','eligible','excluded','unknown','scored']);
const COVERAGE=Object.freeze(['denominator','Q','G','V','simultaneous','ranked','preset_actual_total']);
const ELIGIBILITY=Object.freeze(['ELIGIBLE','EXCLUDED','UNKNOWN']);
const ROSTER_REASON='COMPLETE_CURRENT_IEX_ROSTER_UNCONFIRMED';
const REASON=Object.freeze({
 COMPLETE_CURRENT_IEX_ROSTER_UNCONFIRMED:'평가일의 완전한 IEX 거래 목록 미확인',ELIGIBILITY_UNRESOLVED:'적격 여부 미확정 행 있음',
 DUPLICATE_SECURITY_ID:'증권 ID 중복',MULTIPLE_ISSUER_REPRESENTATIVES:'한 발행사에 대표 증권 여러 개',FINANCIAL_IDENTITY_OR_TIME_MISMATCH:'재무 입력의 발행사·시각 불일치'});
const reasonText=c=>Object.prototype.hasOwnProperty.call(REASON,c)?REASON[c]:'사유 코드 '+c;
const SCOPE_TEXT=Object.freeze({IEX_TRADABLE:'평가일 IEX 거래 가능 목록',SEC_TICKER_OBSERVATIONS:'SEC 티커 관측 목록 (검색용 · IEX 목록 아님)'});
const TEXT=Object.freeze({
 NONE:'확장 모집단 연구 결과 미연결 · 비공개 연구 결과이며 공개 화면 연결은 승인 전입니다',
 SEPARATE:'Universe504(공식 운영)와 확장 모집단(연구)은 다른 모집단입니다 · 확장 결과는 공식 점수·순위·TARGET을 바꾸지 않습니다',
 SYNTHETIC:'합성 개발 검증 · 실제 시장 자료 아님',
 PARTIAL:'부분 목록 · 전체 시장 분모 미확정 · 점수·순위 없음'});

const isObj=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
const own=(o,k)=>Object.prototype.hasOwnProperty.call(o,k);
const nat=v=>Number.isInteger(v)&&v>=0;
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

function validate(json){try{check(json);return{ok:true,value:deepFreeze(JSON.parse(JSON.stringify(json)))};}
 catch(e){if(e instanceof Refused)return{ok:false,code:e.code,path:e.path};return{ok:false,code:'NOT_OBJECT',path:'$'};}}

const unset=(n,why)=>n===null?'미확정 · '+why:String(n);
// Words of a validated expansion result. Each stage keeps its own row and label; null is 미확정 with the reason, never 0.
function expansionView(x){const c=x.counts,v=x.coverage,rs=x.population_reasons,why=rs.length?rs.map(reasonText).join(' · '):'';
 const searchable=x.rows.filter(r=>r.searchable).length;
 return Object.freeze({synthetic:x.source.source_ref.startsWith('SYNTHETIC:'),partial:x.full_market_denominator===null,
  basis:'평가일 '+x.basis_date+' · 목록 관측 '+x.source.observed_at+' · '+(own(SCOPE_TEXT,x.source.scope)?SCOPE_TEXT[x.source.scope]:x.source.scope)+(x.source.complete?' · 완전 목록':' · 부분 목록'),
  version:x.universe_version+' · '+x.calc_version,reasons:Object.freeze(rs.map(reasonText)),
  rows:Object.freeze([
   Object.freeze({id:'searchable',label:'검색 가능',value:String(searchable)+' / 후보 '+c.candidate_rows,note:'증권 ID 확정 '+c.fixed_security_ids+' · 발행사 '+c.unique_issuers}),
   Object.freeze({id:'market',label:'전체 시장 분모',value:unset(x.full_market_denominator,'완전한 IEX 목록 없음'),note:x.full_market_denominator===null?'부분 목록을 전체 시장으로 표시하지 않음':null}),
   Object.freeze({id:'eligibility',label:'적격 · 제외 · 미확정',value:c.eligible+' · '+c.excluded+' · '+c.unknown,note:null}),
   Object.freeze({id:'financial',label:'재무 자료 보유',value:String(c.financial_rows),note:'보유 못 한 행도 분모에 남음'}),
   Object.freeze({id:'qgv',label:'QGV 계산 가능',value:v.denominator===null?unset(null,why):'Q '+v.Q+' · G '+v.G+' · V '+v.V+' · 세 축 '+v.simultaneous+' / '+v.denominator,note:v.denominator===null?null:'기본 총점 실행 '+v.preset_actual_total}),
   Object.freeze({id:'rank',label:'순위 가능',value:v.ranked===null?unset(null,why):String(v.ranked)+' / '+v.denominator,note:v.ranked===0?'V 없는 총점은 QG 참고 순서만':null})])});}

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
return Object.freeze({SCHEMA,UNIVERSE,TEXT,validate,expansionView,universeView,reasonText,source});
});
