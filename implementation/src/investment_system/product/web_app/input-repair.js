/* 입력 연결 수정 전후 비교 reader (IS2.inputRepair; owner 2026-11-09 QGV coverage instruction §4, Codex #527
   sector_qgv_held_repair.comparison → sector-qgv-input-repair-comparison/1, HELD_INPUT_REPAIR.md). Read as written; nothing is
   recalculated, ranked, weighted or filled (DC-42).
   - The treatment is INPUT_CONNECTION_REPAIR only: the producer refuses a changed configuration, date, universe, model,
     normalisation, mapping, denominator, classification or gate before it writes this file, so the screen says 입력 연결 수정 and
     never 요소·비중 변경 or 분류 변경.
   - Trust: accepted only for the result already delivered in the checked held issuer bundle — one coverage scope with the same
     evaluation date, the same input hash as after_input_hash (its result identity) and the same denominator. Its own hashes alone
     prove nothing. A refused file is a connection error of this block; the bundle, coverage and details stay as they were.
   - Arithmetic is checked as written: after = before + gained − lost, nothing above the denominator, a changed value only where both
     sides had one, a selected-row count never above the all-row count, a group's structural shortfall = members below its minimum;
     the same input hash on both sides means no row and no change.
   - Words: 기존 값 바뀜 is a common-valid value that changed because new raw inputs entered the peer pool — a relative score shift,
     never 실적 개선 or 전략 성과; performance stays 미측정 and the whole market stays 미측정; null is 미산출 and 0 is 0.
   Pure; no storage, no request. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else{const I=root.IS2=root.IS2||{};I.inputRepair=api;}})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
const SCHEMA='sector-qgv-input-repair-comparison/1',TREATMENT='INPUT_CONNECTION_REPAIR';
const KEYS=Object.freeze(['schema_version','treatment','denominator','valuation_date','before_input_hash','after_input_hash','axes','factors','rows','groups','whole_market_denominator','performance']);
const COUNTER=Object.freeze(['before','after','gained','lost','changed_common']);
const AXES=Object.freeze(['Q','G','V','joint','total']);
const GROUP_KEYS=Object.freeze(['sector_id','accounting_template','variant_id','members','raw_valid','scoring_representatives','valid_n','minimum','structural_shortfall']);
const ROW_KEYS=Object.freeze(['company_id','issuer_id','factors','before_axes','after_axes','before_total','after_total']);
const FACTOR_KEY=/^([a-z][a-z0-9_]{0,63}):(raw|score):(all|selected)$/,HEX64=/^[0-9a-f]{64}$/,DAY=/^\d{4}-\d{2}-\d{2}$/;
const own=(o,k)=>Object.prototype.hasOwnProperty.call(o,k);
const isObj=v=>!!v&&typeof v==='object'&&!Array.isArray(v);
const nat=v=>Number.isInteger(v)&&v>=0;
class Refusal extends Error{constructor(code,path){super(code+' '+path);this.code=code;this.path=path;}}
const need=(c,code,path)=>{if(!c)throw new Refusal(code,path);};
const exact=(o,keys,path)=>{need(isObj(o),'TYPE',path);const k=Object.keys(o);need(k.length===keys.length&&keys.every(x=>own(o,x)),'KEYS',path);};
function counter(c,den,path){exact(c,COUNTER,path);for(const k of COUNTER)need(nat(c[k])&&c[k]<=den,'COUNT_RANGE',path+'.'+k);
 need(c.after===c.before+c.gained-c.lost&&c.lost<=c.before&&c.gained<=den-c.before,'COUNT_ARITHMETIC',path);
 need(c.changed_common<=c.before-c.lost,'COUNT_ARITHMETIC',path+'.changed_common');}
const moved=c=>c.gained+c.lost+c.changed_common>0;
const axesOf=(a,path)=>{exact(a,['Q','G','V'],path);for(const k of['Q','G','V'])need(a[k]===null||(typeof a[k]==='number'&&Number.isFinite(a[k])),'TYPE',path+'.'+k);};
const num=(v,path)=>need(v===null||(typeof v==='number'&&Number.isFinite(v)),'TYPE',path);

// anchor: {scopes:[{scope, valuation_date, input_hash, denominator}]} from the checked held issuer bundle (anchorOf).
function check(x,anchor){
 exact(x,KEYS,'$');need(x.schema_version===SCHEMA,'SCHEMA','$.schema_version');need(x.treatment===TREATMENT,'TREATMENT','$.treatment');
 need(Number.isInteger(x.denominator)&&x.denominator>0,'TYPE','$.denominator');need(typeof x.valuation_date==='string'&&DAY.test(x.valuation_date),'TYPE','$.valuation_date');
 for(const k of['before_input_hash','after_input_hash'])need(typeof x[k]==='string'&&HEX64.test(x[k]),'HASH',('$.'+k));
 need(x.whole_market_denominator===null,'MARKET_NOT_NULL','$.whole_market_denominator');need(x.performance==='NOT_MEASURED','PERFORMANCE_CLAIMED','$.performance');
 const N=x.denominator;exact(x.axes,AXES,'$.axes');for(const k of AXES)counter(x.axes[k],N,'$.axes.'+k);
 need(isObj(x.factors),'TYPE','$.factors');
 for(const[k,c]of Object.entries(x.factors)){const m=FACTOR_KEY.exec(k);need(m,'FACTOR_KEY','$.factors');counter(c,N,'$.factors.'+k);
  if(m[3]==='selected'){const all=x.factors[m[1]+':'+m[2]+':all'];need(isObj(all)&&c.before<=all.before&&c.after<=all.after,'COUNT_ARITHMETIC','$.factors.'+k);}}
 need(Array.isArray(x.rows)&&x.rows.length<=N,'TYPE','$.rows');const seen=new Set();
 x.rows.forEach((r,i)=>{const p='$.rows['+i+']';exact(r,ROW_KEYS,p);need(typeof r.company_id==='string'&&r.company_id&&!seen.has(r.company_id),'ROWS_INVALID',p+'.company_id');seen.add(r.company_id);
  need(typeof r.issuer_id==='string'&&r.issuer_id,'ROWS_INVALID',p+'.issuer_id');axesOf(r.before_axes,p+'.before_axes');axesOf(r.after_axes,p+'.after_axes');num(r.before_total,p+'.before_total');num(r.after_total,p+'.after_total');
  need(Array.isArray(r.factors)&&r.factors.length>0,'ROWS_INVALID',p+'.factors');const vs=new Set();
  r.factors.forEach((f,j)=>{const q=p+'.factors['+j+']';exact(f,['variant_id','before','after'],q);need(typeof f.variant_id==='string'&&!vs.has(f.variant_id),'ROWS_INVALID',q+'.variant_id');vs.add(f.variant_id);
   need(isObj(f.before)&&isObj(f.after),'TYPE',q);});});
 need(Array.isArray(x.groups),'TYPE','$.groups');
 x.groups.forEach((g,i)=>{const p='$.groups['+i+']';exact(g,GROUP_KEYS,p);for(const k of['sector_id','accounting_template','variant_id'])need(typeof g[k]==='string'&&g[k],'GROUPS_INVALID',p+'.'+k);
  for(const k of['members','raw_valid','scoring_representatives','minimum'])need(nat(g[k]),'GROUPS_INVALID',p+'.'+k);
  need(g.raw_valid<=g.members&&g.scoring_representatives<=g.raw_valid,'GROUPS_INVALID',p);need(Array.isArray(g.valid_n)&&g.valid_n.every(nat),'GROUPS_INVALID',p+'.valid_n');
  need(g.structural_shortfall===(g.members<g.minimum),'GROUPS_INVALID',p+'.structural_shortfall');});
 // The same input on both sides: nothing moved.
 if(x.before_input_hash===x.after_input_hash)need(x.rows.length===0&&AXES.every(k=>!moved(x.axes[k]))&&Object.values(x.factors).every(c=>!moved(c)),'NO_CHANGE_INCONSISTENT','$');
 // The anchor: the delivered result this compares to.
 need(isObj(anchor)&&Array.isArray(anchor.scopes)&&anchor.scopes.length,'ANCHOR_REQUIRED','$.anchor');
 const hit=anchor.scopes.filter(s=>isObj(s)&&s.input_hash===x.after_input_hash&&s.denominator===N);
 need(hit.length,'COMPARISON_RESULT_MISMATCH','$.after_input_hash');const scope=hit[0];
 need(scope.valuation_date===x.valuation_date,'COMPARISON_DATE_MISMATCH','$.valuation_date');
 return scope;}
function validate(x,anchor){try{const scope=check(x,anchor);return{ok:true,value:Object.freeze({comparison:x,scope:scope.scope})};}
 catch(e){if(e instanceof Refusal)return{ok:false,code:e.code,path:e.path};return{ok:false,code:'INVALID',path:'$'};}}
// The anchor from a checked held issuer bundle (IS2.expandedIssuers.checkBundle value): each coverage scope's own context.
function anchorOf(bundle){const out=[];const sc=bundle&&bundle.coverage&&isObj(bundle.coverage.scopes)?bundle.coverage.scopes:{};
 for(const[k,s]of Object.entries(sc)){const c=isObj(s)&&isObj(s.context)?s.context:null;if(!c||!isObj(c.result_identity)||!isObj(c.population))continue;
  out.push(Object.freeze({scope:k,valuation_date:c.valuation_date,input_hash:c.result_identity.input_hash,denominator:c.population.denominator}));}
 return Object.freeze({scopes:Object.freeze(out)});}

/* ---------------- words */
const AXIS_LABEL=Object.freeze({Q:'Q',G:'G',V:'V',joint:'Q·G·V 세 축 동시',total:'최종 총점'});
const SCOPE_LABEL=Object.freeze({operating:'운영504 코드 행',catalog:'관측 카탈로그',held_financial_subsample:'보유 재무 표본'});
const STAGE=Object.freeze({raw:'원지표',score:'요소 점수'}),ROWS=Object.freeze({all:'전체 행',selected:'기본 선택 행'});
const W=Object.freeze({
 HEAD:'입력 연결 수정 전후 비교 (INPUT_CONNECTION_REPAIR)',
 NOT:'요소·비중 변경 아님 · 분류 변경 아님 · 설정 변경 아님(설정·평가일·모집단·분류·관문이 같은 비교만 생산자가 씀)',
 SHIFT:'기존 값 바뀜 = 새 원지표가 비교집단에 들어와 같은 기업의 상대점수가 달라진 것 · 기업 실적 개선·전략 성과 아님',
 LIMITS:'성과 미측정 · 전체시장 분모 미측정 · 원인은 겹칠 수 있음',
 SHORTFALL:'구조적 표본 부족(구성원이 최소보다 적음) · 입력 연결로 풀리지 않음',
 SAME:'전후 입력이 같음 · 바뀐 것 없음',NULL:'미산출'});
const v=x=>x===null||x===undefined?W.NULL:String(x);
const ctext=c=>'전 '+c.before+' → 후 '+c.after+' · 새로 산출 +'+c.gained+' · 산출 사라짐 '+c.lost+' · 기존 값 바뀜 '+c.changed_common;
// view(comparison, scope, {sectorName}) → plain lines for the screen. sectorName names a sector id (the current common taxonomy).
function view(x,scope,opt){const name=opt&&typeof opt.sectorName==='function'?opt.sectorName:(id=>id);
 const factorLines=[],still=[];
 for(const[k,c]of Object.entries(x.factors).sort(([a],[b])=>a<b?-1:1)){const m=FACTOR_KEY.exec(k);
  if(moved(c))factorLines.push(Object.freeze({key:k,text:m[1]+' · '+STAGE[m[2]]+' · '+ROWS[m[3]]+' · '+ctext(c)}));else still.push(k);}
 const short=x.groups.filter(g=>g.structural_shortfall);
 return Object.freeze({
  head:W.HEAD+' · 평가일 '+x.valuation_date+' · 분모 '+x.denominator+' · '+(SCOPE_LABEL[scope]||scope),
  not:W.NOT,limits:W.LIMITS,
  same:x.before_input_hash===x.after_input_hash?W.SAME:null,
  inputs:'입력 전 '+x.before_input_hash.slice(0,12)+'… → 후 '+x.after_input_hash.slice(0,12)+'…(지금 받은 결과)',
  axes:Object.freeze(AXES.map(k=>Object.freeze({key:k,text:AXIS_LABEL[k]+' · '+ctext(x.axes[k])+' / '+x.denominator}))),
  shift:AXES.some(k=>x.axes[k].changed_common>0)||Object.values(x.factors).some(c=>c.changed_common>0)?W.SHIFT:null,
  factors:Object.freeze(factorLines),unchangedFactors:still.length,
  shortfall:Object.freeze(short.map(g=>name(g.sector_id)+' · '+g.accounting_template+' · '+g.variant_id+' · 구성원 '+g.members+' · 원지표 '+g.raw_valid+' · 점수 대표 '+g.scoring_representatives+' · 최소 '+g.minimum)),
  groups:x.groups.length,shortfallWord:W.SHORTFALL,
  rows:Object.freeze(x.rows.map(r=>Object.freeze({id:r.company_id,text:r.company_id+' · 바뀐 요소 '+r.factors.map(f=>f.variant_id).join(', ')
   +' · Q '+v(r.before_axes.Q)+'→'+v(r.after_axes.Q)+' · G '+v(r.before_axes.G)+'→'+v(r.after_axes.G)+' · V '+v(r.before_axes.V)+'→'+v(r.after_axes.V)
   +' · 총점 '+v(r.before_total)+'→'+v(r.after_total)})))});}

return Object.freeze({SCHEMA,TREATMENT,W,validate,anchorOf,view});
});
