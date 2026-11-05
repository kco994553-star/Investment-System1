/* Technical leaderboard reader (IS2.techScreen, feature 3.5 기술 조건 필터; owner 2026-11-03 and 2026-11-04). Reads Codex's research
   schema technical-leaderboard/1 as published (#469 f1ca390a, settings technical-leaderboard/2026-11-03.1; #437 comments 6601332838,
   6602595466) with no conversion: field names, decimal strings and one board per (signal_day, group_id). Calculation is Codex's
   (DC-42); this file only checks, reads and filters. validate / evaluate / boardState / display are pure and run in node as in the page.
   - Input: one board, an array of boards, or a bundle {cases: {<name>: board}, …} such as Codex's public synthetic fixture
     (tests/fixtures/technical_leaderboard_v1.json; other bundle keys are kept aside, never read as boards).
   - Board: {schema, signal_day, settings_version, settings_sha256, group_id, membership_status CONFIRMED|UNKNOWN, membership_source,
     population_hash, metrics: {momentum_3m, momentum_6m, momentum_12m, volatility_6m, dollar_volume_6m: {n_valid, n_members, median,
     k, null_reason, rows: [{value, null_reasons, security_id, series_id, rank, decile, conditions:{gt_zero, ge_median, gt_median,
     top_decile, bottom_decile, exclude_D10}}]}}}. Values are decimal strings (momentum %, volatility % per day, sample stdev ddof 1,
     not annualised; dollar volume USD per trading day). A row may also carry symbol or raw_value: raw_value is never shown and never
     fills a null value (a null adopted dollar volume stays NA with its reason).
   - validate(json) → {ok:true, value:{data_kind, boards:[{id, label, board}]}} (deep-frozen copies) or {ok:false, code, path}: the
     whole input is refused at its first fault. Besides shapes and enums it checks what the screen relies on: an unconfirmed group has
     no N, rank, median, decile or relative condition (GROUP_UNCONFIRMED_VALUES); N counts the adopted values (N_VALID_MISMATCH);
     ranks are 1..N once each (RANK_INVALID); k = floor(N×0.10) for N ≥ 10 and no decile below N = 10 (K_MISMATCH, DECILE_BELOW_10);
     every condition the file states agrees with its value, median and decile (CONDITION_MISMATCH: gt_zero = value > 0, ge_median =
     value ≥ median, gt_median = value > median, top/bottom_decile = decile 10/1, exclude_D10 = decile in 1..9, null when not decidable).
   - evaluate(board, conds) → {conditions, counts:{PASS, FAIL, UNKNOWN}, rows: Map(key → {state, fails, unknown})}: the file's own
     condition booleans only (never recomputed; ranks, N and medians are never rebuilt after filtering). A null condition is 판정 불가
     with the row's or the metric's reason; FAIL wins over UNKNOWN. key = security_id (series_id when the security id is null).
   - source() → Promise {state:'NONE'}: no public file, no request. Private research values are never wired to a public screen.
   Values are price-derived: screens show them only as text inside [data-ram-price]; nothing is stored. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else{const I=root.IS2=root.IS2||{};I.techScreen=api;}})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
const SCHEMA='technical-leaderboard/1';
const METRICS=Object.freeze(['momentum_3m','momentum_6m','momentum_12m','volatility_6m','dollar_volume_6m']);
const CONDITIONS=Object.freeze(['gt_zero','ge_median','gt_median','top_decile','bottom_decile','exclude_D10']);
const META=Object.freeze({
 momentum_3m:Object.freeze({label:'3개월 모멘텀(%)',short:'모멘텀 3개월',unit:'% · 가격 수익률, 배당 재투자 없음',kind:'pct',d10:'D10 = 이 그룹에서 3개월 동안 가장 많이 오른(덜 내린) 10% · 값이 음수일 수 있음'}),
 momentum_6m:Object.freeze({label:'6개월 모멘텀(%)',short:'모멘텀 6개월',unit:'% · 가격 수익률, 배당 재투자 없음',kind:'pct',d10:'D10 = 이 그룹에서 6개월 동안 가장 많이 오른(덜 내린) 10% · 값이 음수일 수 있음'}),
 momentum_12m:Object.freeze({label:'12개월 모멘텀(%)',short:'모멘텀 12개월',unit:'% · 가격 수익률, 배당 재투자 없음',kind:'pct',d10:'D10 = 이 그룹에서 12개월 동안 가장 많이 오른(덜 내린) 10% · 값이 음수일 수 있음'}),
 volatility_6m:Object.freeze({label:'6개월 일간 변동성(%, 비연율화)',short:'일간 변동성',unit:'%/일 · 일간 수익률 표본 표준편차, 비연율화',kind:'vol',d10:'D10 = 이 그룹에서 가장 크게 흔들린 10%'}),
 dollar_volume_6m:Object.freeze({label:'6개월 일평균 달러 거래대금(USD)',short:'거래대금',unit:'USD/거래일 · 같은 체결 범위가 확인된 완전 관측 평균',kind:'usd',d10:'D10 = 이 그룹에서 거래 규모가 가장 큰 10%'})});
const COND_TEXT=Object.freeze({gt_zero:'0% 초과',ge_median:'중앙값 이상',gt_median:'중앙값 초과',top_decile:'상위 10% (D10)',bottom_decile:'하위 10% (D1)',exclude_D10:'D10 제외'});
// The conditions each metric offers on the screen (Codex's predicate names).
const CHOICES=Object.freeze({momentum_3m:Object.freeze(['gt_zero','ge_median','gt_median','top_decile']),momentum_6m:Object.freeze(['gt_zero','ge_median','gt_median','top_decile']),
 momentum_12m:Object.freeze(['gt_zero','ge_median','gt_median','top_decile']),volatility_6m:Object.freeze(['exclude_D10','top_decile']),dollar_volume_6m:Object.freeze(['top_decile','bottom_decile'])});
const REASON=Object.freeze({GROUP_MEMBERSHIP_UNCONFIRMED:'당시 그룹 구성원 미확인 · 순위·중앙값·분위 없음',N_BELOW_10:'유효 종목 10개 미만 · 분위 없음',
 METRIC_NOT_AVAILABLE:'이 지표 값 없음',NO_ROW:'이 지표 행 없음',CONDITION_NOT_AVAILABLE:'조건 판정 불가'});
const TEXT=Object.freeze({NONE:'기술 지표 자료가 아직 없습니다',NONE_WHY:'계산은 Codex(#469) · 공개 합성 자료는 시험에서만 · 비공개 연구값은 공개 화면에 연결하지 않음',
 INVALID:'기술 지표 파일이 계약과 달라 파일 전체를 쓰지 않습니다',FAILED:'기술 지표 파일을 읽지 못했습니다',SYNTHETIC:'합성 데이터 · 시험용',UNKNOWN_REASON:'사유 코드 미등록'});
const MAX=Object.freeze({boards:200,rows:20000,text:200,depth:10});
const DAY=/^(\d{4})-(\d{2})-(\d{2})$/,HEX64=/^[0-9a-f]{64}$/,DEC=/^-?\d+(?:\.\d+)?$/,CODE=/^[A-Z][A-Z0-9_]{0,63}$/;
const own=(o,k)=>Object.prototype.hasOwnProperty.call(o,k);
const isObj=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
function Refusal(code,path){this.code=code;this.path=path;}
const refuse=(code,path)=>{throw new Refusal(code,path);};
function keys(o,want,path,optional=[]){if(!isObj(o))refuse('TYPE',path);for(const k of want)if(!own(o,k))refuse('KEY_MISSING',path+'.'+k);
 for(const k of Object.keys(o))if(!want.includes(k)&&!optional.includes(k))refuse('KEY_UNKNOWN',path+'.'+k);}
const str=(v,path)=>{if(typeof v!=='string'||!v)refuse('TYPE',path);if(v.length>MAX.text)refuse('TOO_LARGE',path);return v;};
const intOrNull=(v,path,min=0)=>{if(v===null)return;if(!Number.isInteger(v))refuse('TYPE',path);if(v<min)refuse('RANGE',path);};
const dec=(v,path)=>{if(v===null)return;if(typeof v!=='string'||!DEC.test(v))refuse('DECIMAL_INVALID',path);};
function day(v,path){const m=typeof v==='string'&&DAY.exec(v);if(!m)refuse('DATE_INVALID',path);const d=new Date(Date.UTC(+m[1],+m[2]-1,+m[3]));
 if(d.getUTCMonth()!==+m[2]-1||d.getUTCDate()!==+m[3])refuse('DATE_INVALID',path);}
// Exact comparison of two decimal strings (no float): -1, 0, 1.
function cmp(a,b){const sa=a[0]==='-'&&!/^-0+(?:\.0+)?$/.test(a)?-1:1,sb=b[0]==='-'&&!/^-0+(?:\.0+)?$/.test(b)?-1:1;
 if(sa!==sb)return sa<sb?-1:1;const p=x=>{const[i,f='']=x.replace('-','').split('.');return[i.replace(/^0+(?=\d)/,''),f];};
 const[ai,af]=p(a),[bi,bf]=p(b);let c=ai.length!==bi.length?(ai.length<bi.length?-1:1):ai<bi?-1:ai>bi?1:0;
 if(!c){const n=Math.max(af.length,bf.length),x=af.padEnd(n,'0'),y=bf.padEnd(n,'0');c=x<y?-1:x>y?1:0;}return c*sa;}
function copy(v,path,depth){if(depth>MAX.depth)refuse('TOO_DEEP',path);
 if(v===null||typeof v==='string'||typeof v==='boolean')return v;if(typeof v==='number'){if(!Number.isFinite(v))refuse('NUMBER_NOT_FINITE',path);return v;}
 if(Array.isArray(v))return v.map((x,i)=>copy(x,path+'['+i+']',depth+1));
 if(isObj(v)&&(Object.getPrototypeOf(v)===Object.prototype||Object.getPrototypeOf(v)===null)){const o={};for(const k of Object.keys(v))o[k]=copy(v[k],path+'.'+k,depth+1);return o;}
 refuse('TYPE',path);}
function deepFreeze(v){if(v&&typeof v==='object'){Object.freeze(v);for(const k of Object.keys(v))deepFreeze(v[k]);}return v;}
const BOARD=['schema','signal_day','settings_version','settings_sha256','group_id','membership_status','membership_source','population_hash','metrics'];
const METRIC=['n_valid','n_members','median','k','null_reason','rows'];
const ROW=['value','null_reasons','security_id','series_id','rank','decile','conditions'],ROW_OPTIONAL=['symbol','raw_value'];
function checkBoard(b,path){
 keys(b,BOARD,path);if(b.schema!==SCHEMA)refuse('SCHEMA_VERSION',path+'.schema');day(b.signal_day,path+'.signal_day');str(b.settings_version,path+'.settings_version');
 if(typeof b.settings_sha256!=='string'||!HEX64.test(b.settings_sha256))refuse('HASH_INVALID',path+'.settings_sha256');str(b.group_id,path+'.group_id');
 if(!['CONFIRMED','UNKNOWN'].includes(b.membership_status))refuse('ENUM',path+'.membership_status');
 if(b.membership_source!==null)str(b.membership_source,path+'.membership_source');
 if(b.population_hash!==null&&(typeof b.population_hash!=='string'||!HEX64.test(b.population_hash)))refuse('HASH_INVALID',path+'.population_hash');
 const known=b.membership_status==='CONFIRMED';keys(b.metrics,METRICS,path+'.metrics');let rowsSeen=0;
 for(const m of METRICS){const p=path+'.metrics.'+m,x=b.metrics[m];keys(x,METRIC,p);
  intOrNull(x.n_valid,p+'.n_valid');intOrNull(x.n_members,p+'.n_members');dec(x.median,p+'.median');intOrNull(x.k,p+'.k');
  if(x.null_reason!==null&&(typeof x.null_reason!=='string'||!CODE.test(x.null_reason)))refuse('REASON_INVALID',p+'.null_reason');
  if(!Array.isArray(x.rows))refuse('TYPE',p+'.rows');rowsSeen+=x.rows.length;if(rowsSeen>MAX.rows)refuse('TOO_LARGE',p+'.rows');
  if(!known){if(x.n_valid!==null||x.median!==null||x.k!==null)refuse('GROUP_UNCONFIRMED_VALUES',p);if(x.null_reason===null)refuse('NULL_REASON_MISSING',p+'.null_reason');}
  else{if(x.n_valid===null||x.n_members===null)refuse('TYPE',p+'.n_valid');if(x.n_valid>x.n_members)refuse('RANGE',p+'.n_valid');
   if(x.median===null&&x.n_valid>0)refuse('MEDIAN_MISSING',p+'.median');
   if(x.n_valid>=10?x.k!==Math.floor(x.n_valid/10):x.k!==null)refuse('K_MISMATCH',p+'.k');}
  const ids=new Set(),ranks=new Set();let adopted=0;
  x.rows.forEach((r,i)=>{const q=p+'.rows['+i+']';keys(r,ROW,q,ROW_OPTIONAL);dec(r.value,q+'.value');
   if(own(r,'raw_value'))dec(r.raw_value,q+'.raw_value');if(own(r,'symbol')&&r.symbol!==null)str(r.symbol,q+'.symbol');
   if(!Array.isArray(r.null_reasons))refuse('TYPE',q+'.null_reasons');r.null_reasons.forEach((c,j)=>{if(typeof c!=='string'||!CODE.test(c))refuse('REASON_INVALID',q+'.null_reasons['+j+']');});
   if(r.security_id!==null)str(r.security_id,q+'.security_id');str(r.series_id,q+'.series_id');
   const key=r.security_id===null?'series:'+r.series_id:r.security_id;if(ids.has(key))refuse('ROW_DUPLICATE',q+'.security_id');ids.add(key);
   if(r.value===null&&!r.null_reasons.length)refuse('NULL_REASON_MISSING',q+'.null_reasons');
   intOrNull(r.rank,q+'.rank',1);if(r.decile!==null&&!(Number.isInteger(r.decile)&&r.decile>=1&&r.decile<=10))refuse('RANGE',q+'.decile');
   keys(r.conditions,CONDITIONS,q+'.conditions');for(const c of CONDITIONS){const v=r.conditions[c];if(v!==null&&typeof v!=='boolean')refuse('TYPE',q+'.conditions.'+c);}
   if(r.value!==null)adopted++;
   if(!known){if(r.rank!==null||r.decile!==null)refuse('GROUP_UNCONFIRMED_VALUES',q);
    for(const c of CONDITIONS)if(c!=='gt_zero'&&r.conditions[c]!==null)refuse('GROUP_UNCONFIRMED_VALUES',q+'.conditions.'+c);}
   else{if(r.value===null?r.rank!==null:(r.rank===null||r.rank>x.n_valid||ranks.has(r.rank)))refuse('RANK_INVALID',q+'.rank');if(r.rank!==null)ranks.add(r.rank);
    if(r.decile!==null&&x.n_valid<10)refuse('DECILE_BELOW_10',q+'.decile');if(r.decile===null&&r.value!==null&&x.n_valid>=10)refuse('DECILE_MISSING',q+'.decile');}
   // Every condition the file states must agree with its own value, median and decile.
   const want={gt_zero:r.value===null?null:cmp(r.value,'0')>0,ge_median:r.value===null||!known||x.median===null?null:cmp(r.value,x.median)>=0,
    gt_median:r.value===null||!known||x.median===null?null:cmp(r.value,x.median)>0,top_decile:r.decile===null?null:r.decile===10,
    bottom_decile:r.decile===null?null:r.decile===1,exclude_D10:r.decile===null?null:r.decile!==10};
   for(const c of CONDITIONS)if(r.conditions[c]!==want[c])refuse('CONDITION_MISMATCH',q+'.conditions.'+c);});
  if(known&&adopted!==x.n_valid)refuse('N_VALID_MISMATCH',p+'.n_valid');}}
function validate(json){
 try{if(!isObj(json)&&!Array.isArray(json))refuse('TYPE','$');const v=copy(json,'$',0);let list,kind=null;
  if(Array.isArray(v))list=v.map((b,i)=>[String(i),b,'$['+i+']']);
  else if(own(v,'cases')){if(!isObj(v.cases))refuse('TYPE','$.cases');list=Object.keys(v.cases).map(k=>[k,v.cases[k],'$.cases.'+k]);
   kind=typeof v.data_kind==='string'?v.data_kind:null;}
  else list=[['0',v,'$']];
  if(!list.length)refuse('EMPTY','$');if(list.length>MAX.boards)refuse('TOO_LARGE','$');
  for(const[,b,p]of list)checkBoard(b,p);
  const count=new Map();for(const[,b]of list){const k=b.signal_day+'|'+b.group_id;count.set(k,count.has(k)?count.get(k)+1:1);}
  const boards=list.map(([id,b])=>({id,label:b.signal_day+' · '+b.group_id+(count.get(b.signal_day+'|'+b.group_id)>1?' · '+id:''),board:b}));
  return{ok:true,value:deepFreeze({data_kind:kind,boards})};}
 catch(e){if(e instanceof Refusal)return{ok:false,code:e.code,path:e.path};throw e;}}

const rowKey=r=>(r.security_id===null?'series:'+r.series_id:r.security_id);
// The board's securities in a stable order (first metric's rows, then any others), each with its row per metric.
function securities(board){const out=new Map();
 for(const m of METRICS)for(const r of board.metrics[m].rows){const k=rowKey(r);if(!out.has(k))out.set(k,{key:k,security_id:r.security_id,series_id:r.series_id,symbol:r.symbol||null,rows:{}});out.get(k).rows[m]=r;}
 return out;}
// One metric's state for the cards: UNCONFIRMED (group unknown), N_BELOW_10, OK.
function metricState(board,m){const x=board.metrics[m];if(board.membership_status!=='CONFIRMED'||x.null_reason==='GROUP_MEMBERSHIP_UNCONFIRMED')return'UNCONFIRMED';
 return x.n_valid<10?'N_BELOW_10':'OK';}
function evaluate(board,conds){
 for(const c of conds)if(!METRICS.includes(c.metric)||!CHOICES[c.metric].includes(c.condition))throw Error('FILTER_INVALID');
 const rows=new Map(),counts={PASS:0,FAIL:0,UNKNOWN:0};
 for(const[k,s]of securities(board)){const fails=[],unknown=[];
  for(const c of conds){const r=s.rows[c.metric],x=board.metrics[c.metric];
   if(!r){unknown.push({metric:c.metric,reason:'NO_ROW'});continue;}
   const v=r.conditions[c.condition];
   if(v===true)continue;if(v===false){fails.push(c.metric);continue;}
   unknown.push({metric:c.metric,reason:r.null_reasons[0]||x.null_reason||(x.n_valid!==null&&x.n_valid<10?'N_BELOW_10':'CONDITION_NOT_AVAILABLE')});}
  const state=fails.length?'FAIL':unknown.length?'UNKNOWN':'PASS';counts[state]++;rows.set(k,Object.freeze({state,fails:Object.freeze(fails),unknown:Object.freeze(unknown)}));}
 return Object.freeze({conditions:Object.freeze(conds.map(c=>Object.freeze({...c}))),counts:Object.freeze(counts),rows});}
// Display of one decimal string (display only; logic never uses these numbers). A null value is null: raw_value is never used.
function display(m,row){const v=row?row.value:null;if(v===null||v===undefined)return null;const n=Number(v);if(!Number.isFinite(n))return null;
 const kind=META[m].kind;
 if(kind==='usd'){const a=Math.abs(n),[d,u]=a>=1e9?[1e9,'B']:a>=1e6?[1e6,'M']:a>=1e3?[1e3,'K']:[1,''];return'$'+(n/d).toFixed(d===1?2:1)+u;}
 const t=Math.abs(n).toFixed(2).replace(/\.?0+$/,'')||'0';
 return kind==='vol'?t+'%/일':(n>0?'+':n<0?'−':'')+t+'%';}
const medianText=(m,median)=>(median===null?null:display(m,{value:median}));
const decileText=d=>(Number.isInteger(d)?'D'+d:null);
const reasonText=c=>(typeof c==='string'&&own(REASON,c)?REASON[c]:TEXT.UNKNOWN_REASON);
const condText=(m,c)=>META[m].label+' · '+COND_TEXT[c];
const status=v=>(!v?TEXT.NONE:v.data_kind==='SYNTHETIC'?TEXT.SYNTHETIC:v.data_kind?'실자료 · '+v.data_kind:'자료 종류 표시 없음');
function source(){return Promise.resolve(Object.freeze({state:'NONE',code:'TECH_SCREEN_NOT_CONNECTED',payload:null,text:TEXT.NONE}));}
return Object.freeze({SCHEMA,METRICS,CONDITIONS,CHOICES,META,COND_TEXT,REASON,TEXT,validate,evaluate,securities,metricState,display,medianText,decileText,reasonText,condText,status,cmp,source});
});
