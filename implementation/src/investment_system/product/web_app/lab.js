/* Lab results (IS2.lab, common base 2026-10-31; FRONTEND_BRIEF §4–5, COMMON_BASE_20261031.md): the reader and validator of the
   owner's lab-backtest-v1 contract, the owner's status texts, and where results come from. validate / status / nullText are pure
   (no window, no request, no storage) and run in node as they run in the page.
   - validate(json) → {ok:true, value} (a deep-frozen copy; the argument is never changed) or {ok:false, code, path}: the whole file
     is refused at its first fault, never partly shown. json is the parsed file (a string is refused: whoever reads the text parses
     it and refuses duplicate keys, as QgvOfficial.duplicateKeys does). Rules:
     · shape: exact keys at every level (KEY_MISSING / KEY_UNKNOWN), types (TYPE; strings non-empty and bounded, TOO_LARGE for
       oversized strings and lists, TOO_DEEP), enums (ENUM), finite numbers (NUMBER_NOT_FINITE), schema_version 'lab-backtest-v1'
       (SCHEMA_VERSION), generated_at ISO-8601 with a zone (GENERATED_AT_ZONE, DATE_INVALID), source_commit 40 lowercase hex
       (SOURCE_COMMIT), run ids (ID_INVALID, RUN_ID_DUPLICATE), dates (DATE_INVALID), period start < end (PERIOD_ORDER), costs
       >= 0 (COST_NEGATIVE);
     · metrics: number or null each; a null metric needs a non-empty null_reasons entry (NULL_REASON_MISSING); a null_reasons key
       is a metric name (NULL_REASON_KEY) of a null metric (NULL_REASON_UNUSED); -1 <= max_drawdown <= 0 (MAX_DRAWDOWN_RANGE);
       volatility >= 0 (VOLATILITY_RANGE); excess_cagr = cagr - benchmark_cagr within 1e-6, and null when either is null
       (EXCESS_CAGR_MISMATCH);
     · equity_curve: points {date:'YYYY-MM', strategy, benchmark}, values finite > 0 (CURVE_VALUE); months strictly ascending
       (CURVE_ORDER) and unique (CURVE_DUPLICATE); the first point is period.start's month with strategy 100 and benchmark 100
       (CURVE_START); the last point is period.end's month, a partial month allowed (CURVE_END); at least 2 points whenever
       total_return, cagr, benchmark_cagr or max_drawdown is not null (CURVE_TOO_SHORT; the last two are checked against the
       curve, so the confirmed total_return / cagr rule is extended to them); an empty curve only when they are all null;
     · consistency with the curve: |total_return - (last strategy / 100 - 1)| <= 1e-4 (TOTAL_RETURN_MISMATCH); cagr against
       total_return (or the last strategy point when total_return is null) over the period, and benchmark_cagr against the last
       benchmark point, annualised over the actual days / 365.25 with a loose absolute tolerance of 0.002 (the producer's day
       count may differ a little; CAGR_MISMATCH, BENCHMARK_CAGR_MISMATCH); max_drawdown no milder than the monthly curve's
       drawdown by more than 1e-4 (a daily drawdown can only be deeper; MAX_DRAWDOWN_MISMATCH).
   - status(run) → the owner's status line (exact texts in TEXT): no run → 연구 결과가 아직 없습니다; SYNTHETIC → 합성 데이터 ·
     시험용; REAL → 실데이터 <파일럿|정식 실행> · <미검증|입력 시점 검증됨|검토 완료> (REAL PILOT NOT_VALIDATED = 실데이터 파일럿 ·
     미검증); MIXED → 실데이터와 합성 데이터 혼합 · <kind> · <check>; then · 모집단 시점 정합성 미확인 when universe.point_in_time
     is false (not for SYNTHETIC). An unverified run is never hidden and never worded as verified performance.
     nullText(run, metric) → '– · <null_reasons text>' for a null metric, null otherwise (a null is never shown as 0).
   - source() → Promise of {state, code, payload, private, text, private_text}. Today: state NONE (no public result file exists
     and none is read: nothing here makes a request) with private PRIVATE_NOT_READY from IS2.privateArea; later a private path
     answers PRIVATE_LOGIN_REQUIRED (비공개 연구 결과 · 로그인 필요), OK with a validated payload, or ERROR with the refusal code.
   - lab-backtest-v2 (Main 2026-11-03, Codex agreement #437 comment 6600537423; contract §7): the v1 run keys plus result_kind
     (BACKTEST | SINGLE_COMPANY_METRIC | SAMPLE_DIAGNOSTIC), computation_status (COMPUTED | NOT_COMPUTED), not_computed_reason
     (a non-empty text when NOT_COMPUTED, else null: NOT_COMPUTED_REASON), as_of (a day; required unless BACKTEST: AS_OF_REQUIRED),
     sample {unit company|security, n_requested int|null, n_used int, selection} (n_used ≤ n_requested: SAMPLE_RANGE), population
     {id, scope SAMPLE|FULL_MARKET, as_of, completeness COMPLETE|INCOMPLETE|UNKNOWN, n_total int|null, null_reason} (n_total null
     needs a reason: POPULATION_NULL_REASON; FULL_MARKET not COMPLETE has n_total null: POPULATION_INCOMPLETE) and diagnostics
     [{name, value, unit count|fraction, null_reason, n_valid, n_total, population_ref}] (aggregates only; [] for BACKTEST:
     DIAGNOSTICS_BACKTEST; population_ref = population.id: POPULATION_REF; count an integer >= 0, fraction = n_valid / n_total with
     n_total > 0: DIAGNOSTIC_FRACTION; a null value needs a reason, a value takes none). A run that is not a BACKTEST, or is
     NOT_COMPUTED, has all seven metrics null with reasons and an empty curve (METRIC_NOT_ALLOWED, CURVE_NOT_ALLOWED); a run that
     is not a BACKTEST has period, rebalance, benchmark and costs null (NON_BACKTEST_FIELD: no made-up period or zero cost). A v1
     file never carries the new keys (KEY_UNKNOWN). status() words for v2 kinds follow the agreement (TEXT.V2); reasonText(code)
     gives the words of a known reason code, '사유 코드 미등록' for an unknown code-shaped one, and other text as written.
   Nothing here stores or sends anything; loading the file reads nothing (it only puts IS2.lab). */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else{const I=root.IS2=root.IS2||{};I.lab=api.create({privateArea:()=>I.privateArea});}})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
const SCHEMA='lab-backtest-v1',SCHEMA_V2='lab-backtest-v2',SCHEMAS=Object.freeze([SCHEMA,SCHEMA_V2]);
const METRICS=Object.freeze(['cagr','total_return','max_drawdown','volatility','sharpe','benchmark_cagr','excess_cagr']);
const TOP=['schema_version','generated_at','source_commit','runs'];
const RUN=['id','name','description','run_type','data_status','validation_status','qgv_version','universe','period','rebalance','benchmark','costs','metrics','null_reasons','equity_curve','limitations'];
const ENUMS=Object.freeze({run_type:Object.freeze(['PILOT','FORMAL']),data_status:Object.freeze(['REAL','SYNTHETIC','MIXED']),
 validation_status:Object.freeze(['NOT_VALIDATED','PIT_VERIFIED','REVIEWED']),qgv_version:Object.freeze(['v2']),
 rebalance:Object.freeze(['daily','weekly','monthly','quarterly','semiannual','annual']),
 result_kind:Object.freeze(['BACKTEST','SINGLE_COMPANY_METRIC','SAMPLE_DIAGNOSTIC']),computation_status:Object.freeze(['COMPUTED','NOT_COMPUTED']),
 unit:Object.freeze(['company','security']),scope:Object.freeze(['SAMPLE','FULL_MARKET']),completeness:Object.freeze(['COMPLETE','INCOMPLETE','UNKNOWN']),
 diag_unit:Object.freeze(['count','fraction'])});
const RUN_V2=Object.freeze([...RUN,'result_kind','computation_status','not_computed_reason','as_of','sample','population','diagnostics']);
const MAX_DIAGNOSTICS=200;
const TOL=Object.freeze({excess:1e-6,total:1e-4,cagr:0.002,drawdown:1e-4});
const MAX=Object.freeze({runs:100,curve:1200,limitations:50,depth:12,id:64,name:200,description:2000,definition:500,note:1000,benchmark:200,reason:500,limitation:500});
const TEXT=Object.freeze({EMPTY:'연구 결과가 아직 없습니다',SYNTHETIC:'합성 데이터 · 시험용',PIT_MISSING:'모집단 시점 정합성 미확인',NULL:'–',
 INVALID:'연구 결과 파일이 계약과 달라 파일 전체를 쓰지 않습니다',FAILED:'연구 결과 파일을 읽지 못했습니다',PRIVATE_LOGIN_REQUIRED:'비공개 연구 결과 · 로그인 필요',
 DATA:Object.freeze({REAL:'실데이터',MIXED:'실데이터와 합성 데이터 혼합'}),KIND:Object.freeze({PILOT:'파일럿',FORMAL:'정식 실행'}),
 CHECK:Object.freeze({NOT_VALIDATED:'미검증',PIT_VERIFIED:'입력 시점 검증됨',REVIEWED:'검토 완료'}),
 V2:Object.freeze({REAL:'실자료',NOT_COMPUTED:'미산출',SINGLE_COMPANY_METRIC:'1회사 지표 계산 · 전략 성과 아님',SAMPLE_DIAGNOSTIC:'표본 진단 · 전략 성과 아님',
  KIND:Object.freeze({BACKTEST:'전략 백테스트',SINGLE_COMPANY_METRIC:'1회사 지표',SAMPLE_DIAGNOSTIC:'표본 진단'}),
  UNIT:Object.freeze({company:'회사',security:'증권'}),SCOPE:Object.freeze({SAMPLE:'표본',FULL_MARKET:'전체 시장'}),
  COMPLETENESS:Object.freeze({COMPLETE:'완전',INCOMPLETE:'불완전',UNKNOWN:'완전성 미확인'}),UNKNOWN_REASON:'사유 코드 미등록'}),
 REASON:Object.freeze({PRESERVED_INPUTS_NOT_ATTACHED:'보존 입력이 첨부되지 않음',CANDIDATE_ROSTER_INCOMPLETE:'전체 후보 명부가 불완전함',
  C2_DENOMINATOR_UNKNOWN:'C2 분모 미확인',SECURITY_ID_NOT_ESTABLISHED:'증권 신원 미확립',REPRESENTATIVE_SECURITY_UNCONFIRMED:'대표 증권 미확인',
  ISSUER_MARKET_CAP_INPUT_INCOMPLETE:'발행사 시가총액 입력 불완전',PIT_INPUT_INCOMPLETE:'시점 기준 입력 불완전',
  SECTOR_CANDIDATE_WEIGHTS_NOT_PREREGISTERED:'섹터 후보 가중치 사전 등록 전',PRICE_HISTORY_NOT_ATTACHED:'가격 이력 미첨부',
  ACTION_ADJUSTMENT_BASIS_UNCONFIRMED:'기업행사 조정 기준 미확인',COMPARISON_POPULATION_UNDEFINED:'비교 모집단 미정의',VALID_N_BELOW_10:'유효 표본 10개 미만',
  LIQUIDITY_CONDITION_NOT_PREREGISTERED:'유동성 조건 사전 등록 전',NOT_A_STRATEGY_BACKTEST:'전략 백테스트 아님'})});
const HEX40=/^[0-9a-f]{40}$/,RUN_ID=/^[A-Za-z0-9][A-Za-z0-9._:-]*$/,REASON_CODE=/^[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+$/;
const CLOCK=/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2})(?:\.\d{1,9})?)?(Z|([+-])(\d{2}):(\d{2}))$/,LOCAL=/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?$/;
const DAY=/^(\d{4})-(\d{2})-(\d{2})$/,MONTH=/^(\d{4})-(\d{2})$/;
const own=(o,k)=>Object.prototype.hasOwnProperty.call(o,k);
const isObj=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
function Refusal(code,path){this.code=code;this.path=path;}
const refuse=(code,path)=>{throw new Refusal(code,path);};
const daysIn=(y,m)=>new Date(Date.UTC(y,m,0)).getUTCDate();

// A copy of plain JSON data (objects, arrays, strings, finite numbers, booleans, null); anything else is refused.
function copy(v,path,depth){
 if(depth>MAX.depth)refuse('TOO_DEEP',path);
 if(v===null||typeof v==='string'||typeof v==='boolean')return v;
 if(typeof v==='number'){if(!Number.isFinite(v))refuse('NUMBER_NOT_FINITE',path);return v;}
 if(Array.isArray(v))return v.map((x,i)=>copy(x,path+'['+i+']',depth+1));
 if(Object.prototype.toString.call(v)!=='[object Object]')refuse('TYPE',path);
 const o={};for(const k of Object.keys(v))Object.defineProperty(o,k,{value:copy(v[k],path+'.'+k,depth+1),enumerable:true,writable:true,configurable:true});
 return o;}
function deepFreeze(v){if(v&&typeof v==='object'&&!Object.isFrozen(v)){Object.freeze(v);for(const x of Object.values(v))deepFreeze(x);}return v;}
function object(v,path){if(!isObj(v))refuse('TYPE',path);}
function keys(o,want,path){object(o,path);for(const k of want)if(!own(o,k))refuse('KEY_MISSING',path+'.'+k);for(const k of Object.keys(o))if(!want.includes(k))refuse('KEY_UNKNOWN',path+'.'+k);}
function str(v,max,path){if(typeof v!=='string'||!v.trim())refuse('TYPE',path);if(v.length>max)refuse('TOO_LARGE',path);}
function bool(v,path){if(typeof v!=='boolean')refuse('TYPE',path);}
function num(v,path){if(typeof v!=='number')refuse('TYPE',path);if(!Number.isFinite(v))refuse('NUMBER_NOT_FINITE',path);}
function list(v,max,path){if(!Array.isArray(v))refuse('TYPE',path);if(v.length>max)refuse('TOO_LARGE',path);}
function oneOf(v,name,path){if(typeof v!=='string')refuse('TYPE',path);if(!ENUMS[name].includes(v))refuse('ENUM',path);}
// 'YYYY-MM-DD' (a real calendar day) → its UTC time.
function day(v,path){if(typeof v!=='string')refuse('TYPE',path);const m=DAY.exec(v);if(!m)refuse('DATE_INVALID',path);
 const y=+m[1],mo=+m[2],d=+m[3];if(mo<1||mo>12||d<1||d>daysIn(y,mo))refuse('DATE_INVALID',path);return Date.UTC(y,mo-1,d);}
function month(v,path){if(typeof v!=='string')refuse('TYPE',path);const m=MONTH.exec(v);if(!m||+m[2]<1||+m[2]>12)refuse('DATE_INVALID',path);}
function clock(v,path){
 if(typeof v!=='string')refuse('TYPE',path);if(LOCAL.test(v))refuse('GENERATED_AT_ZONE',path);
 const m=CLOCK.exec(v);if(!m)refuse('DATE_INVALID',path);
 const y=+m[1],mo=+m[2],d=+m[3],hh=+m[4],mm=+m[5],ss=m[6]===undefined?0:+m[6];
 if(mo<1||mo>12||d<1||d>daysIn(y,mo)||hh>23||mm>59||ss>59)refuse('DATE_INVALID',path);
 if(m[8]&&(+m[9]>23||+m[10]>59))refuse('DATE_INVALID',path);}
const near=(a,b,tol)=>Math.abs(a-b)<=tol;// false for NaN

// The lab-backtest-v2 run fields (header). Returns {noMetrics}: true when the run may carry no metric and no curve.
function intOrNull(v,path){if(v===null)return;if(!Number.isInteger(v))refuse('TYPE',path);if(v<0)refuse('RANGE',path);}
function checkV2(r,at){
 oneOf(r.result_kind,'result_kind',at+'.result_kind');oneOf(r.computation_status,'computation_status',at+'.computation_status');
 const notComputed=r.computation_status==='NOT_COMPUTED',bt=r.result_kind==='BACKTEST';
 if(notComputed)str(r.not_computed_reason,MAX.reason,at+'.not_computed_reason');else if(r.not_computed_reason!==null)refuse('NOT_COMPUTED_REASON',at+'.not_computed_reason');
 if(r.as_of===null){if(!bt)refuse('AS_OF_REQUIRED',at+'.as_of');}else day(r.as_of,at+'.as_of');
 const s=r.sample,sw=at+'.sample';keys(s,['unit','n_requested','n_used','selection'],sw);oneOf(s.unit,'unit',sw+'.unit');
 intOrNull(s.n_requested,sw+'.n_requested');if(s.n_used===null)refuse('TYPE',sw+'.n_used');intOrNull(s.n_used,sw+'.n_used');str(s.selection,MAX.note,sw+'.selection');
 if(s.n_requested!==null&&s.n_used>s.n_requested)refuse('SAMPLE_RANGE',sw+'.n_used');
 const p=r.population,pw=at+'.population';keys(p,['id','scope','as_of','completeness','n_total','null_reason'],pw);
 str(p.id,MAX.id,pw+'.id');if(!RUN_ID.test(p.id))refuse('ID_INVALID',pw+'.id');oneOf(p.scope,'scope',pw+'.scope');
 if(p.as_of!==null)day(p.as_of,pw+'.as_of');oneOf(p.completeness,'completeness',pw+'.completeness');intOrNull(p.n_total,pw+'.n_total');
 if(p.null_reason!==null)str(p.null_reason,MAX.reason,pw+'.null_reason');
 if(p.n_total===null&&p.null_reason===null)refuse('POPULATION_NULL_REASON',pw+'.null_reason');
 if(p.scope==='FULL_MARKET'&&p.completeness!=='COMPLETE'&&p.n_total!==null)refuse('POPULATION_INCOMPLETE',pw+'.n_total');
 const d=r.diagnostics,dw=at+'.diagnostics';list(d,MAX_DIAGNOSTICS,dw);if(bt&&d.length)refuse('DIAGNOSTICS_BACKTEST',dw);
 d.forEach((x,i)=>{const w=dw+'['+i+']';keys(x,['name','value','unit','null_reason','n_valid','n_total','population_ref'],w);
  str(x.name,MAX.id,w+'.name');oneOf(x.unit,'diag_unit',w+'.unit');intOrNull(x.n_valid,w+'.n_valid');intOrNull(x.n_total,w+'.n_total');
  if(x.n_valid!==null&&x.n_total!==null&&x.n_valid>x.n_total)refuse('RANGE',w+'.n_valid');
  if(x.population_ref!==p.id)refuse('POPULATION_REF',w+'.population_ref');
  if(x.value===null){str(x.null_reason,MAX.reason,w+'.null_reason');return;}
  if(x.null_reason!==null)refuse('NULL_REASON_UNUSED',w+'.null_reason');
  if(x.unit==='count'){if(!Number.isInteger(x.value))refuse('TYPE',w+'.value');if(x.value<0)refuse('RANGE',w+'.value');return;}
  num(x.value,w+'.value');if(x.value<0||x.value>1)refuse('RANGE',w+'.value');
  if(!(x.n_total>0)||x.n_valid===null||!near(x.value,x.n_valid/x.n_total,1e-9))refuse('DIAGNOSTIC_FRACTION',w+'.value');});
 return{noMetrics:notComputed||!bt};}
function checkRun(r,at,v2){
 keys(r,v2?RUN_V2:RUN,at);
 str(r.id,MAX.id,at+'.id');if(!RUN_ID.test(r.id))refuse('ID_INVALID',at+'.id');
 str(r.name,MAX.name,at+'.name');str(r.description,MAX.description,at+'.description');
 for(const k of['run_type','data_status','validation_status','qgv_version'])oneOf(r[k],k,at+'.'+k);
 const kind=v2?r.result_kind:'BACKTEST',ext=v2?checkV2(r,at):null,bt=kind==='BACKTEST';
 if(!bt){for(const k of['period','rebalance','benchmark','costs'])if(r[k]!==null)refuse('NON_BACKTEST_FIELD',at+'.'+k);}
 else oneOf(r.rebalance,'rebalance',at+'.rebalance');
 const u=r.universe;keys(u,['definition','point_in_time','survivorship_note'],at+'.universe');
 str(u.definition,MAX.definition,at+'.universe.definition');bool(u.point_in_time,at+'.universe.point_in_time');str(u.survivorship_note,MAX.note,at+'.universe.survivorship_note');
 const p=r.period;let start=null,end=null;
 if(bt){keys(p,['start','end'],at+'.period');
  start=day(p.start,at+'.period.start');end=day(p.end,at+'.period.end');if(start>=end)refuse('PERIOD_ORDER',at+'.period');
  const b=r.benchmark;keys(b,['name','total_return'],at+'.benchmark');str(b.name,MAX.benchmark,at+'.benchmark.name');bool(b.total_return,at+'.benchmark.total_return');
  const c=r.costs;keys(c,['fee_bps','slippage_bps'],at+'.costs');
  for(const k of['fee_bps','slippage_bps']){num(c[k],at+'.costs.'+k);if(c[k]<0)refuse('COST_NEGATIVE',at+'.costs.'+k);}}
 const m=r.metrics;keys(m,METRICS,at+'.metrics');
 for(const k of METRICS)if(m[k]!==null)num(m[k],at+'.metrics.'+k);
 if(ext&&ext.noMetrics)for(const k of METRICS)if(m[k]!==null)refuse('METRIC_NOT_ALLOWED',at+'.metrics.'+k);
 const why=r.null_reasons;object(why,at+'.null_reasons');
 for(const k of Object.keys(why)){const w=at+'.null_reasons.'+k;if(!METRICS.includes(k))refuse('NULL_REASON_KEY',w);
  if(typeof why[k]!=='string')refuse('TYPE',w);if(why[k].length>MAX.reason)refuse('TOO_LARGE',w);}
 for(const k of METRICS){const w=at+'.null_reasons.'+k;
  if(m[k]===null&&!(own(why,k)&&why[k].trim()))refuse('NULL_REASON_MISSING',w);
  if(m[k]!==null&&own(why,k))refuse('NULL_REASON_UNUSED',w);}
 const{cagr,total_return:total,max_drawdown:mdd,volatility:vol,benchmark_cagr:bench,excess_cagr:excess}=m;
 if(mdd!==null&&(mdd>0||mdd<-1))refuse('MAX_DRAWDOWN_RANGE',at+'.metrics.max_drawdown');
 if(vol!==null&&vol<0)refuse('VOLATILITY_RANGE',at+'.metrics.volatility');
 if(excess!==null&&(cagr===null||bench===null||!near(excess,cagr-bench,TOL.excess)))refuse('EXCESS_CAGR_MISMATCH',at+'.metrics.excess_cagr');
 list(r.limitations,MAX.limitations,at+'.limitations');r.limitations.forEach((x,i)=>str(x,MAX.limitation,at+'.limitations['+i+']'));
 const curve=r.equity_curve,cw=at+'.equity_curve';list(curve,MAX.curve,cw);
 if(ext&&ext.noMetrics&&curve.length)refuse('CURVE_NOT_ALLOWED',cw);
 curve.forEach((pt,i)=>{const w=cw+'['+i+']';keys(pt,['date','strategy','benchmark'],w);month(pt.date,w+'.date');
  for(const k of['strategy','benchmark']){num(pt[k],w+'.'+k);if(!(pt[k]>0))refuse('CURVE_VALUE',w+'.'+k);}
  if(i&&pt.date===curve[i-1].date)refuse('CURVE_DUPLICATE',w+'.date');if(i&&pt.date<curve[i-1].date)refuse('CURVE_ORDER',w+'.date');});
 if((total!==null||cagr!==null||bench!==null||mdd!==null)&&curve.length<2)refuse('CURVE_TOO_SHORT',cw);
 if(!curve.length)return;
 const first=curve[0],last=curve[curve.length-1];
 if(first.date!==p.start.slice(0,7))refuse('CURVE_START',cw+'[0].date');
 if(first.strategy!==100||first.benchmark!==100)refuse('CURVE_START',cw+'[0]');
 if(last.date!==p.end.slice(0,7))refuse('CURVE_END',cw+'['+(curve.length-1)+'].date');
 const years=(end-start)/86400000/365.25,annual=g=>Math.pow(g,1/years)-1;
 if(total!==null&&!near(total,last.strategy/100-1,TOL.total))refuse('TOTAL_RETURN_MISMATCH',at+'.metrics.total_return');
 if(cagr!==null&&!near(cagr,annual(total!==null?1+total:last.strategy/100),TOL.cagr))refuse('CAGR_MISMATCH',at+'.metrics.cagr');
 if(bench!==null&&!near(bench,annual(last.benchmark/100),TOL.cagr))refuse('BENCHMARK_CAGR_MISMATCH',at+'.metrics.benchmark_cagr');
 if(mdd!==null){let peak=-Infinity,worst=0;for(const pt of curve){peak=Math.max(peak,pt.strategy);worst=Math.min(worst,pt.strategy/peak-1);}
  if(mdd>worst+TOL.drawdown)refuse('MAX_DRAWDOWN_MISMATCH',at+'.metrics.max_drawdown');}
}
function check(v){
 if(!isObj(v))refuse('NOT_OBJECT','$');
 if(own(v,'schema_version')&&!SCHEMAS.includes(v.schema_version))refuse('SCHEMA_VERSION','$.schema_version');
 keys(v,TOP,'$');clock(v.generated_at,'$.generated_at');
 if(typeof v.source_commit!=='string'||!HEX40.test(v.source_commit))refuse('SOURCE_COMMIT','$.source_commit');
 list(v.runs,MAX.runs,'$.runs');const ids=new Set();
 const v2=v.schema_version===SCHEMA_V2;
 v.runs.forEach((r,i)=>{const at='$.runs['+i+']';checkRun(r,at,v2);if(ids.has(r.id))refuse('RUN_ID_DUPLICATE',at+'.id');ids.add(r.id);});
}
function validate(json){
 try{if(!isObj(json))refuse('NOT_OBJECT','$');const v=copy(json,'$',0);check(v);return Object.freeze({ok:true,value:deepFreeze(v)});}
 catch(e){if(e instanceof Refusal)return Object.freeze({ok:false,code:e.code,path:e.path});return Object.freeze({ok:false,code:'INVALID',path:'$'});}
}
// The owner's status line of one validated run (or of none).
function status(run){
 if(run===null||run===undefined)return TEXT.EMPTY;
 if(!isObj(run))throw Error('LAB_RUN_INVALID');
 const pit=isObj(run.universe)&&run.universe.point_in_time===false?' · '+TEXT.PIT_MISSING:'';
 if(own(run,'result_kind')&&(run.result_kind!=='BACKTEST'||run.computation_status==='NOT_COMPUTED')){
  const V=TEXT.V2,d=run.data_status==='SYNTHETIC'?TEXT.SYNTHETIC:run.data_status==='REAL'?V.REAL:TEXT.DATA.MIXED,k=V.KIND[run.result_kind];
  if(!d||!k)throw Error('LAB_RUN_INVALID');
  const tail=run.data_status==='SYNTHETIC'?'':pit;
  if(run.computation_status==='NOT_COMPUTED'){const nc=V.NOT_COMPUTED+' · '+reasonText(run.not_computed_reason);
   return(run.data_status==='SYNTHETIC'?d+' · '+nc+' · '+k:nc+' · '+d+' '+k)+tail;}
  return(run.data_status==='REAL'?d+' '+V[run.result_kind]:d+' · '+V[run.result_kind])+tail;}
 if(run.data_status==='SYNTHETIC')return TEXT.SYNTHETIC;
 const d=TEXT.DATA[run.data_status],k=TEXT.KIND[run.run_type],c=TEXT.CHECK[run.validation_status];
 if(!d||!k||!c)throw Error('LAB_RUN_INVALID');
 return(run.data_status==='REAL'?d+' '+k:d+' · '+k)+' · '+c+pit;
}
function nullText(run,metric){
 if(!METRICS.includes(metric))throw Error('LAB_METRIC_UNKNOWN');
 if(!isObj(run)||!isObj(run.metrics)||!isObj(run.null_reasons))throw Error('LAB_RUN_INVALID');
 return run.metrics[metric]===null?TEXT.NULL+' · '+reasonText(run.null_reasons[metric]):null;
}
// The words of a reason: a known code's text, '사유 코드 미등록' for an unknown code, other text (v1 free text) as written.
function reasonText(x){if(typeof x!=='string')return TEXT.V2.UNKNOWN_REASON;if(own(TEXT.REASON,x))return TEXT.REASON[x];return REASON_CODE.test(x)?TEXT.V2.UNKNOWN_REASON:x;}
const PRIVATE=Object.freeze({NOT_READY:'PRIVATE_NOT_READY',LOGIN_REQUIRED:'PRIVATE_LOGIN_REQUIRED',SIGNED_IN:'PRIVATE_NOT_READY'});
function create({privateArea}={}){
 const area=typeof privateArea==='function'?privateArea:()=>privateArea;
 // No public result file exists and no private reader is built yet: nothing is requested.
 async function source(){
  const P=area(),st=P&&typeof P.state==='function'?P.state():'NOT_READY',priv=PRIVATE[st]||'PRIVATE_NOT_READY';
  const words=priv==='PRIVATE_LOGIN_REQUIRED'?TEXT.PRIVATE_LOGIN_REQUIRED:P&&typeof P.text==='function'?P.text('NOT_READY'):'비공개 기능 준비 중';
  return Object.freeze({state:'NONE',code:'LAB_NO_PUBLIC_RESULT',payload:null,private:priv,text:TEXT.EMPTY,private_text:words});}
 return Object.freeze({SCHEMA,SCHEMA_V2,SCHEMAS,METRICS,TEXT,validate,status,nullText,reasonText,source});
}
return Object.freeze({create,SCHEMA,SCHEMA_V2,SCHEMAS,METRICS,ENUMS,TOL,TEXT,validate,status,nullText,reasonText});
});
