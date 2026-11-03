/* Technical screen data (IS2.techScreen, feature 3.5 기술 조건 리더보드 필터; owner 2026-11-03 "계층 3 기술적 분석 리더보드 화면"):
   the reader, validator and filter rule of the proposed tech-screen-v0 file, and where the file comes from. validate / evaluate /
   format / describe are pure (no window, no request, no storage) and run in node as they run in the page.
   Calculation is Codex's (DC-42). The field names below are Main's proposal (#437); they change only after agreement with Codex.
   - File (tech-screen-v0): {schema_version, generated_at (ISO, zoned), source_commit (40 hex), data_status SYNTHETIC|REAL|MIXED,
     evaluations:[{as_of 'YYYY-MM-DD', groups:[{id, label, members}], stats:{<group>:{<metric>:{n_valid, median, deciles, reason}}},
     rows:[{company_id, ticker, groups:[<group>…], metrics:{<metric>:{value, obs_days, expected_days, reason, decile:{<group>:1..10|null}}}}]}]}.
     Metrics (fixed here, METRICS): mom_3m · mom_6m · mom_12m (total return over the window, a ratio), vol_6m (annualised standard
     deviation of daily returns, a ratio), adv_6m (mean daily dollar volume, USD). Deciles come from the file, per group: D10 is the
     top tenth of the group's valid values (largest return, largest volatility, largest dollar volume).
   - validate(json) → {ok:true, value} (deep-frozen copy) or {ok:false, code, path}: the whole file is refused at its first fault,
     never partly shown. A null value needs a reason (NULL_REASON_MISSING); a group without deciles needs a reason and no row decile
     for it (DECILES_OFF_*); a row decile for a group the row is not in is refused (DECILE_GROUP); n_valid ≤ members (N_VALID_RANGE).
   - evaluate(ev, groupId, filters) → {group, counts:{PASS, FAIL, UNKNOWN}, rows: Map(company_id → {state, fails, unknown})}.
     Only the chosen group's rows are judged; deciles, medians and denominators are the file's for that group and never change with
     the filters (owner: 분위와 분모는 처음 선택한 그룹 기준). A condition that needs a missing value or decile is UNKNOWN (판정 불가),
     never FAIL and never PASS; a row is FAIL when any condition fails, else UNKNOWN when any is unknown, else PASS.
     filters = {mom:{'3m'|'6m'|'12m': none|gt0|gte_median|top10}, vol: none|exclude_d10|only_d10, adv: none|only_d10|exclude_d1}.
   - source() → Promise of {state, code, payload, text}. Today state NONE (no public file exists and none is read: nothing here
     makes a request). Private research values are never wired to a public screen (owner 2026-11-03; LAB-PUBLISH is separate).
   Values here are price-derived: screens show them only as text inside [data-ram-price], never in an attribute, storage or a URL.
   Loading the file reads nothing (it only puts IS2.techScreen). */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else{const I=root.IS2=root.IS2||{};I.techScreen=api;}})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
const SCHEMA='tech-screen-v0';
const METRICS=Object.freeze(['mom_3m','mom_6m','mom_12m','vol_6m','adv_6m']);
// short (phone line), label, unit words, window words, kind (ratio | usd), how to read D10.
const META=Object.freeze({
 mom_3m:Object.freeze({short:'모멘텀 3개월',label:'3개월 모멘텀',unit:'% · 기간 총수익률',window:'3개월',kind:'ratio',d10:'D10 = 이 그룹에서 3개월 동안 가장 많이 오른(덜 내린) 10% · 값이 음수일 수 있음'}),
 mom_6m:Object.freeze({short:'모멘텀 6개월',label:'6개월 모멘텀',unit:'% · 기간 총수익률',window:'6개월',kind:'ratio',d10:'D10 = 이 그룹에서 6개월 동안 가장 많이 오른(덜 내린) 10% · 값이 음수일 수 있음'}),
 mom_12m:Object.freeze({short:'모멘텀 12개월',label:'12개월 모멘텀',unit:'% · 기간 총수익률',window:'12개월',kind:'ratio',d10:'D10 = 이 그룹에서 12개월 동안 가장 많이 오른(덜 내린) 10% · 값이 음수일 수 있음'}),
 vol_6m:Object.freeze({short:'변동성',label:'6개월 변동성',unit:'% · 일간 수익률 표준편차 연율화',window:'6개월',kind:'ratio',d10:'D10 = 이 그룹에서 가장 크게 흔들린 10%'}),
 adv_6m:Object.freeze({short:'거래대금',label:'6개월 일평균 달러 거래대금',unit:'USD · 하루 평균',window:'6개월',kind:'usd',d10:'D10 = 이 그룹에서 거래 규모가 가장 큰 10%'})});
const PERIODS=Object.freeze(['3m','6m','12m']);
const COND=Object.freeze({
 mom:Object.freeze([['none','조건 없음'],['gt0','0% 초과'],['gte_median','중앙값 이상'],['top10','상위 10% (D10)']]),
 vol:Object.freeze([['none','조건 없음'],['exclude_d10','D10 제외 (가장 크게 흔들린 10% 빼기)'],['only_d10','D10만']]),
 adv:Object.freeze([['none','조건 없음'],['only_d10','D10만 (거래 규모 가장 큰 10%)'],['exclude_d1','D1 제외 (거래 규모 가장 작은 10% 빼기)']])});
const REASON=Object.freeze({
 PRICE_HISTORY_SHORT:'가격 이력이 계산 창보다 짧음',SOURCE_MISSING:'원천 가격 자료 없음',IDENTITY_UNCONFIRMED:'증권 신원 미확인',
 GROUP_TOO_SMALL:'비교 그룹의 유효 종목이 적어 분위를 매기지 않음',QUALITY_FAILED:'가격 자료 품질 검사 실패',CORPORATE_ACTION_UNRESOLVED:'기업행사 조정 미확인',
 DECILE_NA:'분위 없음',GROUP_MEDIAN_NA:'그룹 중앙값 없음',NOT_IN_GROUP:'고른 비교 그룹 밖',NO_TECH_ROW:'기술 지표 행 없음'});
const TEXT=Object.freeze({NONE:'기술 지표 자료가 아직 없습니다',NONE_WHY:'계산은 Codex 인계 뒤 연결 · 비공개 연구값은 공개 화면에 연결하지 않음',
 INVALID:'기술 지표 파일이 계약과 달라 파일 전체를 쓰지 않습니다',FAILED:'기술 지표 파일을 읽지 못했습니다',SYNTHETIC:'합성 데이터 · 시험용',
 DATA:Object.freeze({REAL:'실데이터',MIXED:'실데이터와 합성 데이터 혼합'}),UNKNOWN_REASON:'사유 코드 미등록'});
const MAX=Object.freeze({evaluations:60,groups:12,rows:6000,id:64,label:120,reason:64,depth:8});
const HEX40=/^[0-9a-f]{40}$/,GROUP_ID=/^[A-Z][A-Z0-9_]{0,31}$/,REASON_CODE=/^[A-Z][A-Z0-9_]{0,63}$/,COMPANY=/^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$/;
const CLOCK=/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d{1,9})?)?(?:Z|[+-]\d{2}:\d{2})$/,DAY=/^(\d{4})-(\d{2})-(\d{2})$/;
const own=(o,k)=>Object.prototype.hasOwnProperty.call(o,k);
const isObj=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
function Refusal(code,path){this.code=code;this.path=path;}
const refuse=(code,path)=>{throw new Refusal(code,path);};
function keys(o,want,path,optional=[]){if(!isObj(o))refuse('TYPE',path);for(const k of want)if(!own(o,k))refuse('KEY_MISSING',path+'.'+k);
 for(const k of Object.keys(o))if(!want.includes(k)&&!optional.includes(k))refuse('KEY_UNKNOWN',path+'.'+k);}
const str=(v,path,max)=>{if(typeof v!=='string'||!v)refuse('TYPE',path);if(v.length>max)refuse('TOO_LARGE',path);return v;};
const int=(v,path,min=0)=>{if(!Number.isInteger(v))refuse('TYPE',path);if(v<min)refuse('RANGE',path);return v;};
const num=(v,path)=>{if(typeof v!=='number')refuse('TYPE',path);if(!Number.isFinite(v))refuse('NUMBER_NOT_FINITE',path);return v;};
function day(v,path){const m=typeof v==='string'&&DAY.exec(v);if(!m)refuse('DATE_INVALID',path);const d=new Date(Date.UTC(+m[1],+m[2]-1,+m[3]));
 if(d.getUTCFullYear()!==+m[1]||d.getUTCMonth()!==+m[2]-1||d.getUTCDate()!==+m[3])refuse('DATE_INVALID',path);return v;}
const reason=(v,path)=>{if(v===null)return null;if(typeof v!=='string'||!REASON_CODE.test(v))refuse('REASON_INVALID',path);return v;};
function deepFreeze(v){if(v&&typeof v==='object'){Object.freeze(v);for(const k of Object.keys(v))deepFreeze(v[k]);}return v;}
// A copy of plain JSON data (objects, arrays, strings, finite numbers, booleans, null); anything else is refused.
function copy(v,path,depth){if(depth>MAX.depth)refuse('TOO_DEEP',path);
 if(v===null||typeof v==='string'||typeof v==='boolean')return v;if(typeof v==='number'){if(!Number.isFinite(v))refuse('NUMBER_NOT_FINITE',path);return v;}
 if(Array.isArray(v))return v.map((x,i)=>copy(x,path+'['+i+']',depth+1));
 if(isObj(v)&&Object.getPrototypeOf(v)===Object.prototype||isObj(v)&&Object.getPrototypeOf(v)===null){const o={};for(const k of Object.keys(v))o[k]=copy(v[k],path+'.'+k,depth+1);return o;}
 refuse('TYPE',path);}

function checkEvaluation(ev,path){
 keys(ev,['as_of','groups','stats','rows'],path);day(ev.as_of,path+'.as_of');
 if(!Array.isArray(ev.groups)||!ev.groups.length)refuse('TYPE',path+'.groups');if(ev.groups.length>MAX.groups)refuse('TOO_LARGE',path+'.groups');
 const members=new Map();
 ev.groups.forEach((g,i)=>{const p=path+'.groups['+i+']';keys(g,['id','label','members'],p);
  if(typeof g.id!=='string'||!GROUP_ID.test(g.id))refuse('ID_INVALID',p+'.id');if(members.has(g.id))refuse('GROUP_DUPLICATE',p+'.id');
  str(g.label,p+'.label',MAX.label);members.set(g.id,int(g.members,p+'.members'));});
 keys(ev.stats,[...members.keys()],path+'.stats');
 const decilesOn=new Map();
 for(const[g,n]of members){keys(ev.stats[g],METRICS,path+'.stats.'+g);
  for(const m of METRICS){const p=path+'.stats.'+g+'.'+m,s=ev.stats[g][m];keys(s,['n_valid','median','deciles','reason'],p);
   if(int(s.n_valid,p+'.n_valid')>n)refuse('N_VALID_RANGE',p+'.n_valid');
   if(s.median!==null)num(s.median,p+'.median');if(typeof s.deciles!=='boolean')refuse('TYPE',p+'.deciles');reason(s.reason,p+'.reason');
   if(!s.deciles&&s.reason===null)refuse('DECILES_OFF_REASON',p+'.reason');
   if(s.median===null&&s.reason===null)refuse('NULL_REASON_MISSING',p+'.reason');
   if(m==='vol_6m'||m==='adv_6m'){if(s.median!==null&&s.median<0)refuse('RANGE',p+'.median');}
   decilesOn.set(g+'|'+m,s.deciles);}}
 if(!Array.isArray(ev.rows))refuse('TYPE',path+'.rows');if(ev.rows.length>MAX.rows)refuse('TOO_LARGE',path+'.rows');
 const seen=new Set(),count=new Map([...members.keys()].map(g=>[g,0]));
 ev.rows.forEach((r,i)=>{const p=path+'.rows['+i+']';keys(r,['company_id','ticker','groups','metrics'],p);
  if(typeof r.company_id!=='string'||!COMPANY.test(r.company_id))refuse('ID_INVALID',p+'.company_id');if(seen.has(r.company_id))refuse('ROW_DUPLICATE',p+'.company_id');seen.add(r.company_id);
  str(r.ticker,p+'.ticker',MAX.id);
  if(!Array.isArray(r.groups)||!r.groups.length)refuse('TYPE',p+'.groups');
  r.groups.forEach((g,j)=>{if(!members.has(g))refuse('GROUP_UNKNOWN',p+'.groups['+j+']');});if(new Set(r.groups).size!==r.groups.length)refuse('GROUP_DUPLICATE',p+'.groups');
  for(const g of r.groups)count.set(g,count.get(g)+1);
  keys(r.metrics,METRICS,p+'.metrics');
  for(const m of METRICS){const q=p+'.metrics.'+m,x=r.metrics[m];keys(x,['value','obs_days','expected_days','reason','decile'],q);
   if(x.value!==null){num(x.value,q+'.value');if((m==='vol_6m'||m==='adv_6m')&&x.value<0)refuse('RANGE',q+'.value');if(m.startsWith('mom_')&&x.value<=-1)refuse('RANGE',q+'.value');}
   reason(x.reason,q+'.reason');if(x.value===null&&x.reason===null)refuse('NULL_REASON_MISSING',q+'.reason');
   if(x.obs_days!==null)int(x.obs_days,q+'.obs_days');if(x.expected_days!==null)int(x.expected_days,q+'.expected_days',1);
   if(x.obs_days!==null&&x.expected_days!==null&&x.obs_days>x.expected_days)refuse('OBS_DAYS_RANGE',q+'.obs_days');
   if(!isObj(x.decile))refuse('TYPE',q+'.decile');
   for(const g of Object.keys(x.decile))if(!r.groups.includes(g))refuse('DECILE_GROUP',q+'.decile.'+g);
   for(const g of r.groups){if(!own(x.decile,g))refuse('KEY_MISSING',q+'.decile.'+g);const d=x.decile[g];
    if(d!==null&&!(Number.isInteger(d)&&d>=1&&d<=10))refuse('DECILE_RANGE',q+'.decile.'+g);
    if(d!==null&&!decilesOn.get(g+'|'+m))refuse('DECILES_OFF_ROW',q+'.decile.'+g);
    if(d!==null&&x.value===null)refuse('DECILE_WITHOUT_VALUE',q+'.decile.'+g);
    if(d===null&&x.value!==null&&decilesOn.get(g+'|'+m))refuse('DECILE_MISSING',q+'.decile.'+g);}}});
 for(const[g,n]of count)if(n>members.get(g))refuse('MEMBERS_RANGE',path+'.groups.'+g);}

function validate(json){
 try{if(!isObj(json))refuse('TYPE','$');const v=copy(json,'$',0);
  keys(v,['schema_version','generated_at','source_commit','data_status','evaluations'],'$');
  if(v.schema_version!==SCHEMA)refuse('SCHEMA_VERSION','$.schema_version');
  if(typeof v.generated_at!=='string'||!CLOCK.test(v.generated_at)||!Number.isFinite(Date.parse(v.generated_at)))refuse('GENERATED_AT_ZONE','$.generated_at');
  if(typeof v.source_commit!=='string'||!HEX40.test(v.source_commit))refuse('SOURCE_COMMIT','$.source_commit');
  if(!['SYNTHETIC','REAL','MIXED'].includes(v.data_status))refuse('ENUM','$.data_status');
  if(!Array.isArray(v.evaluations)||!v.evaluations.length)refuse('TYPE','$.evaluations');if(v.evaluations.length>MAX.evaluations)refuse('TOO_LARGE','$.evaluations');
  const days=new Set();v.evaluations.forEach((ev,i)=>{checkEvaluation(ev,'$.evaluations['+i+']');if(days.has(ev.as_of))refuse('AS_OF_DUPLICATE','$.evaluations['+i+'].as_of');days.add(ev.as_of);});
  return{ok:true,value:deepFreeze(v)};}
 catch(e){if(e instanceof Refusal)return{ok:false,code:e.code,path:e.path};throw e;}}

const blank=()=>({mom:{'3m':'none','6m':'none','12m':'none'},vol:'none',adv:'none'});
const active=f=>!!f&&(PERIODS.some(p=>f.mom&&f.mom[p]&&f.mom[p]!=='none')||(f.vol&&f.vol!=='none')||(f.adv&&f.adv!=='none'));
// The conditions of a filter set, in a fixed order: [{metric, rule}].
function conditions(f){const out=[];if(!f)return out;
 for(const p of PERIODS){const r=f.mom&&f.mom[p];if(r&&r!=='none'){if(!COND.mom.some(c=>c[0]===r))throw Error('FILTER_INVALID');out.push({metric:'mom_'+p,rule:r});}}
 if(f.vol&&f.vol!=='none'){if(!COND.vol.some(c=>c[0]===f.vol))throw Error('FILTER_INVALID');out.push({metric:'vol_6m',rule:f.vol});}
 if(f.adv&&f.adv!=='none'){if(!COND.adv.some(c=>c[0]===f.adv))throw Error('FILTER_INVALID');out.push({metric:'adv_6m',rule:f.adv});}
 return out;}
// One condition on one row: 'PASS' | 'FAIL' | {unknown: reason code}.
function judge(row,g,stats,{metric,rule}){
 const x=row.metrics[metric],d=x.decile[g],s=stats[g][metric];
 const noDecile=()=>({unknown:x.value===null?x.reason:s.reason||'DECILE_NA'});
 if(rule==='gt0'){if(x.value===null)return{unknown:x.reason};return x.value>0?'PASS':'FAIL';}
 if(rule==='gte_median'){if(x.value===null)return{unknown:x.reason};if(s.median===null)return{unknown:s.reason||'GROUP_MEDIAN_NA'};return x.value>=s.median?'PASS':'FAIL';}
 if(d===null)return noDecile();
 if(rule==='top10'||rule==='only_d10')return d===10?'PASS':'FAIL';
 if(rule==='exclude_d10')return d!==10?'PASS':'FAIL';
 if(rule==='exclude_d1')return d!==1?'PASS':'FAIL';
 throw Error('FILTER_INVALID');}
function evaluate(ev,groupId,filters){
 const group=ev.groups.find(g=>g.id===groupId);if(!group)throw Error('GROUP_UNKNOWN');
 const conds=conditions(filters),rows=new Map(),counts={PASS:0,FAIL:0,UNKNOWN:0};
 for(const r of ev.rows){if(!r.groups.includes(groupId))continue;
  const fails=[],unknown=[];
  for(const c of conds){const j=judge(r,groupId,ev.stats,c);if(j==='FAIL')fails.push(c.metric);else if(j!=='PASS')unknown.push({metric:c.metric,reason:j.unknown});}
  const state=fails.length?'FAIL':unknown.length?'UNKNOWN':'PASS';counts[state]++;rows.set(r.company_id,Object.freeze({state,fails:Object.freeze(fails),unknown:Object.freeze(unknown)}));}
 return Object.freeze({group,conditions:Object.freeze(conds),counts:Object.freeze(counts),rows});}

// Display text (Korean). ratio → signed percent with one decimal; usd → $ with K/M/B; decile → D1..D10.
function format(metric,v){if(v===null||typeof v!=='number'||!Number.isFinite(v))return null;
 if(META[metric].kind==='usd'){const a=Math.abs(v),[d,u]=a>=1e9?[1e9,'B']:a>=1e6?[1e6,'M']:a>=1e3?[1e3,'K']:[1,''];return'$'+(v/d).toFixed(d===1?0:1)+u;}
 const p=Math.round(v*1000)/10,sign=metric.startsWith('mom_')?(p>0?'+':p<0?'−':''):(p<0?'−':'');return sign+Math.abs(p).toFixed(1)+'%';}
const decileText=d=>(Number.isInteger(d)?'D'+d:null);
const reasonText=code=>(typeof code==='string'&&own(REASON,code)?REASON[code]:TEXT.UNKNOWN_REASON);
function status(v){if(!v)return TEXT.NONE;return v.data_status==='SYNTHETIC'?TEXT.SYNTHETIC:TEXT.DATA[v.data_status];}
const condText=(metric,rule)=>{const set=metric.startsWith('mom_')?COND.mom:metric==='vol_6m'?COND.vol:COND.adv;const c=set.find(x=>x[0]===rule);return META[metric].label+' · '+(c?c[1]:rule);};
// Today: no public file and no request. A later private path answers OK / ERROR here; it never feeds a public screen.
function source(){return Promise.resolve(Object.freeze({state:'NONE',code:'TECH_SCREEN_NOT_CONNECTED',payload:null,text:TEXT.NONE}));}
return Object.freeze({SCHEMA,METRICS,META,PERIODS,COND,REASON,TEXT,validate,evaluate,conditions,active,blank,format,decileText,reasonText,status,condText,source});
});
