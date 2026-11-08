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
   - joinRows(board, rows, {links, data_kind}) → {ok:true, keys: Set(security id)} or {ok:false, code, …} (owner audit 2026-11-07;
     Codex #515 b6fd0112 contract, docs/frontend_v2/TECH_FILTER_QGV_JOIN.md): a JS port of join_filtered_rows. Key (signal_day,
     security_id): every QGV row carries its own signal_day (equal to the board's) and a fixed security_id in the board, and exactly
     one CONFIRMED security link {series_id, security_id, identifier_type, reference, valid_from, valid_to (inclusive), issuer_id,
     symbol, share_class, identity_status, identity_reference} active on that day ties it to the board series, the row's id
     (issuer) and ticker. No ticker / id / code fallback; one bad row or link refuses the whole join. Codex's codes, plus
     SECURITY_LINKS_NOT_CONNECTED (Main: no links file); joinText words them. A row's issuer is its explicit issuer_id when the
     field is present (Codex #516 extension: id = the company code row, issuer_id = the issuer; an explicit null never falls back),
     else the legacy id. BOARD_GROUP_ROWS_UNRESOLVED (Main, screen-tech-filter-live keep): the confirmed board group's full QGV
     rows are not known, so nothing is joined.
   - source() → Promise {state:'NONE', security_links:null}: no public file, no request. Private research values are never wired to a public screen.
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
// The QGV join (header): a pure JS port of Codex #515 technical_filter_join.join_filtered_rows (b6fd0112), same checks in the
// same order and the same reason codes; it returns the joined security ids instead of row copies (Main filters with evaluate).
const SECURITY_IDENTIFIER_TYPES=Object.freeze(['PERMNO','FIGI','ISIN','CUSIP','EXCHANGE_SECURITY_ID','PROVIDER_SECURITY_ID','SYNTHETIC_FIXED_SECURITY_ID']);
const LINK_TEXT_FIELDS=['reference','identity_reference','series_id','issuer_id','symbol','share_class'];
const JOIN_TEXT=Object.freeze({SECURITY_LINKS_NOT_CONNECTED:'고정 증권 매핑 자료 미연결 · 매핑이 오기 전에는 결합하지 않음',
 BOARD_GROUP_ROWS_UNRESOLVED:'보드 그룹 전체 구성원 미확인(공통 분류 기록 미연결) · 그룹 전체 행 없이 결합하지 않음',
 JOIN_DATA_KIND_REQUIRED:'자료 종류 표시 없음(합성 또는 보관 입력)',TECHNICAL_BOARD_SCHEMA_MISMATCH:'기술 보드 스키마 불일치',
 INVALID_SESSION_DATE:'평가일 없음 또는 형식 오류 · QGV 행에 계산 평가일이 없음',GROUP_MEMBERSHIP_UNCONFIRMED:'비교 그룹 구성원 미확인',
 TECHNICAL_METRICS_MISMATCH:'기술 지표 목록 불일치',PERMANENT_SECURITY_ID_REQUIRED:'고정 증권 ID 없음',REQUEST_SERIES_ID_REQUIRED:'시리즈 ID 없음',
 DUPLICATE_TECHNICAL_KEY:'기술 보드에 같은 증권이 두 번',TECHNICAL_IDENTITY_MISMATCH:'지표 사이 증권·시리즈 불일치',
 FIXED_SECURITY_LINK_EVIDENCE_REQUIRED:'증권 매핑 근거 없음',FIXED_SECURITY_LINK_UNCONFIRMED:'증권 신원 미확인',
 ISSUER_OR_TICKER_IS_NOT_SECURITY_ID:'발행사 ID·티커·코드는 증권 ID가 아님',SYNTHETIC_SECURITY_ID_ON_RETAINED_INPUT:'합성 증권 ID가 실자료에 섞임',
 INVALID_SECURITY_LINK_RANGE:'매핑 유효기간 오류(시작이 끝보다 늦음)',DUPLICATE_SECURITY_LINK:'매핑 중복 · 평가일에 겹치는 매핑',
 SIGNAL_DAY_MISMATCH:'평가일 불일치',DUPLICATE_QGV_KEY:'QGV 결합 키 중복(같은 평가일·같은 증권 두 행)',
 SECURITY_ID_NOT_IN_BOARD:'보드에 없는 증권 · 같은 티커의 다른 증권 또는 다른 종류주',FIXED_SECURITY_LINK_MISSING:'매핑 없음',
 SECURITY_LINK_OUTSIDE_SIGNAL_DAY:'매핑 유효기간 밖(만료 또는 아직 유효 전)',SERIES_LINK_MISMATCH:'매핑 시리즈 불일치',
 ISSUER_LINK_MISMATCH:'발행사 불일치(QGV 행 id ≠ 매핑 발행사)',SYMBOL_LINK_MISMATCH:'티커 불일치(QGV 행·보드 ≠ 매핑 티커)',
 // technical-filter-join/2 (Codex #516 5b0ec88a)
 GROUP_MEMBERSHIP_REQUIRED:'그룹 명부 없음 · 완전성을 확인할 수 없어 결합하지 않음',GROUP_MEMBERSHIP_SCHEMA_MISMATCH:'그룹 명부 형식 불일치',GROUP_DATA_KIND_MISMATCH:'그룹 명부 자료 종류 불일치',
 GROUP_CONTEXT_REQUIRED:'그룹 명부 문맥 없음',GROUP_CONTEXT_MISMATCH:'요청 문맥 ≠ 그룹 명부 문맥',GROUP_CONTEXT_HASH_INVALID:'그룹 명부 해시 형식 오류',GROUP_MEMBER_INVALID:'그룹 명부 구성원 형식 오류',
 DUPLICATE_GROUP_MEMBER:'그룹 명부 구성원 중복',BOARD_MEMBERSHIP_MISMATCH:'보드 구성 ≠ 그룹 명부',COMPANY_CODE_REQUIRED:'행의 기업 코드 없음',DUPLICATE_GROUP_ROW:'같은 기업 코드 행 중복',
 ROW_OUTSIDE_GROUP:'그룹 밖 행이 결합 입력에 섞임',ROW_CLASSIFICATION_MISMATCH:'행의 분류 해시·기록 ID ≠ 그룹 명부 · 덮어쓰지 않음',SECURITY_CLASSIFICATION_MISMATCH:'행의 증권 ID ≠ 그룹 명부 증권',
 ISSUER_CLASSIFICATION_MISMATCH:'행의 발행사 ≠ 그룹 명부 발행사 · 바꾸지 않음',GROUP_MEMBER_MISSING:'그룹 구성원 행 누락 · 나머지만으로 결합하지 않음',
 ISSUER_CONNECTION_EVIDENCE_REQUIRED:'발행사 연결 근거 없음',ISSUER_CONNECTION_OPTION_INVALID:'발행사 연결 선택값 오류'});
function JoinRefusal(code,more){this.code=code;this.more=more||null;}
const jno=(code,more)=>{throw new JoinRefusal(code,more);};
const jtext=(v,code)=>(typeof v!=='string'||!v.trim()||v!==v.trim()?jno(code):v);
function jday(v){const m=typeof v==='string'&&DAY.exec(v);if(!m)jno('INVALID_SESSION_DATE');const d=new Date(Date.UTC(+m[1],+m[2]-1,+m[3]));
 if(d.getUTCMonth()!==+m[2]-1||d.getUTCDate()!==+m[3])jno('INVALID_SESSION_DATE');return v;}
const jobj=v=>(isObj(v)?v:{});
// _board_securities: security id → [series, symbol] per metric, the same in every metric.
function boardSecurities(board){if(jobj(board).schema!==SCHEMA)jno('TECHNICAL_BOARD_SCHEMA_MISMATCH');jday(board.signal_day);
 if(board.membership_status!=='CONFIRMED')jno('GROUP_MEMBERSHIP_UNCONFIRMED');const ms=Object.keys(jobj(board.metrics));
 if(ms.length!==METRICS.length||!METRICS.every(m=>ms.includes(m)))jno('TECHNICAL_METRICS_MISMATCH');let out=null;
 for(const m of METRICS){const seen=new Map();for(const r of board.metrics[m].rows){const sid=jtext(r.security_id,'PERMANENT_SECURITY_ID_REQUIRED'),series=jtext(r.series_id,'REQUEST_SERIES_ID_REQUIRED');
   if(seen.has(sid))jno('DUPLICATE_TECHNICAL_KEY');seen.set(sid,[series,r.symbol===undefined?null:r.symbol]);}
  if(out&&(out.size!==seen.size||[...seen].some(([k,v])=>!out.has(k)||out.get(k)[0]!==v[0]||out.get(k)[1]!==v[1])))jno('TECHNICAL_IDENTITY_MISMATCH');out=seen;}
 return out;}
// joinRows(board, rows, {links, data_kind}) → {ok:true, keys:Set(security id)} or {ok:false, code[, board_day, qgv_day]}. rows carry
// Main's id/ticker/code plus signal_day and security_id, never derived from id, code or ticker; links = security_links (null: the
// links file is not connected, a Main-only refusal checked first). One bad row or link refuses the whole join.
function joinRows(board,rows,{links=null,data_kind=null,group=null}={}){
 try{if(links===null||links===undefined)jno('SECURITY_LINKS_NOT_CONNECTED');
  if(data_kind!=='SYNTHETIC'&&data_kind!=='RETAINED_INPUT')jno('JOIN_DATA_KIND_REQUIRED');
  const secs=boardSecurities(board),signal=board.signal_day,byId=new Map(),activeSeries=new Set(),activeIds=new Set();
  if(group)groupCheck(board,rows,group.manifest,group.context,data_kind);
  for(const raw of Array.isArray(links)?links:jno('FIXED_SECURITY_LINK_EVIDENCE_REQUIRED')){const l=jobj(raw),sid=jtext(l.security_id,'FIXED_SECURITY_LINK_EVIDENCE_REQUIRED');
   if(typeof l.identifier_type!=='string'||!SECURITY_IDENTIFIER_TYPES.includes(l.identifier_type))jno('FIXED_SECURITY_LINK_EVIDENCE_REQUIRED');
   for(const f of LINK_TEXT_FIELDS)jtext(l[f],'FIXED_SECURITY_LINK_EVIDENCE_REQUIRED');
   if(l.identity_status!=='CONFIRMED')jno('FIXED_SECURITY_LINK_UNCONFIRMED');if(sid===l.issuer_id||sid===l.symbol)jno('ISSUER_OR_TICKER_IS_NOT_SECURITY_ID');
   if((l.identifier_type==='SYNTHETIC_FIXED_SECURITY_ID'||sid.startsWith('SYNTHETIC:'))&&data_kind!=='SYNTHETIC')jno('SYNTHETIC_SECURITY_ID_ON_RETAINED_INPUT');
   if(jday(l.valid_from)>jday(l.valid_to))jno('INVALID_SECURITY_LINK_RANGE');
   if(!byId.has(sid))byId.set(sid,[]);byId.get(sid).push(l);
   if(l.valid_from<=signal&&signal<=l.valid_to){if(activeSeries.has(l.series_id)||activeIds.has(sid))jno('DUPLICATE_SECURITY_LINK');activeSeries.add(l.series_id);activeIds.add(sid);}}
  const seen=new Set();
  for(const raw of rows){const r=jobj(raw),d=jday(r.signal_day);if(d!==signal)jno('SIGNAL_DAY_MISMATCH',{board_day:signal,qgv_day:d});
   const sid=jtext(r.security_id,'PERMANENT_SECURITY_ID_REQUIRED');if(sid===r.id||sid===r.issuer_id||sid===r.ticker||sid===r.code)jno('ISSUER_OR_TICKER_IS_NOT_SECURITY_ID');
   if(seen.has(sid))jno('DUPLICATE_QGV_KEY');seen.add(sid);if(!secs.has(sid))jno('SECURITY_ID_NOT_IN_BOARD');
   const cands=byId.get(sid)||[];if(!cands.length)jno('FIXED_SECURITY_LINK_MISSING');
   const active=cands.filter(l=>l.valid_from<=signal&&signal<=l.valid_to);if(!active.length)jno('SECURITY_LINK_OUTSIDE_SIGNAL_DAY');
   const l=active[0],[series,symbol]=secs.get(sid);if(l.series_id!==series)jno('SERIES_LINK_MISMATCH');if((own(r,'issuer_id')?r.issuer_id:r.id)!==l.issuer_id)jno('ISSUER_LINK_MISMATCH');
   if(r.ticker!==l.symbol||(symbol!==null&&symbol!==l.symbol))jno('SYMBOL_LINK_MISMATCH');}
  return Object.freeze({ok:true,keys:seen});}
 catch(e){if(e instanceof JoinRefusal)return Object.freeze({ok:false,code:e.code,...e.more});throw e;}}
/* ---- technical-filter-join/2 (Codex #516 5b0ec88a research.technical_filter_join._group_rows / join_group_rows; GROUP_JOIN.md):
   the complete board group checked against a trusted technical-filter-membership/1 roster and an independently pinned request
   context, before the /1 identity join. Same checks, same order, same codes. Without a roster joinRows stays /1: identity only,
   group completeness NOT_CHECKED (never reported as VERIFIED). */
// SHA-256 of a string's UTF-8 bytes (hex), synchronous, for the existing board population_hash formula only.
const K256=new Uint32Array([0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,
 0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,
 0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,
 0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,
 0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2]);
function sha256(str){const b=new TextEncoder().encode(String(str)),n=b.length,len=((n+9+63)>>6)<<6,m=new Uint8Array(len);m.set(b);m[n]=0x80;
 const bits=n*8;for(let i=0;i<8;i++)m[len-1-i]=i<4?(bits>>>(8*i))&255:Math.floor(bits/2**(8*i))&255;
 const H=new Uint32Array([0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19]),W=new Uint32Array(64),r=(x,k)=>(x>>>k)|(x<<(32-k));
 for(let o=0;o<len;o+=64){for(let i=0;i<16;i++)W[i]=(m[o+4*i]<<24)|(m[o+4*i+1]<<16)|(m[o+4*i+2]<<8)|m[o+4*i+3];
  for(let i=16;i<64;i++){const s0=r(W[i-15],7)^r(W[i-15],18)^(W[i-15]>>>3),s1=r(W[i-2],17)^r(W[i-2],19)^(W[i-2]>>>10);W[i]=(W[i-16]+s0+W[i-7]+s1)>>>0;}
  let[a,bb,c,d,e,f,g,h]=H;
  for(let i=0;i<64;i++){const t1=(h+(r(e,6)^r(e,11)^r(e,25))+((e&f)^(~e&g))+K256[i]+W[i])>>>0,t2=((r(a,2)^r(a,13)^r(a,22))+((a&bb)^(a&c)^(bb&c)))>>>0;
   h=g;g=f;f=e;e=(d+t1)>>>0;d=c;c=bb;bb=a;a=(t1+t2)>>>0;}
  H[0]+=a;H[1]+=bb;H[2]+=c;H[3]+=d;H[4]+=e;H[5]+=f;H[6]+=g;H[7]+=h;}
 return[...H].map(x=>x.toString(16).padStart(8,'0')).join('');}
// Python json.dumps(value) of a string with its defaults (ensure_ascii=True): JSON escapes, every non-ASCII code unit as \uXXXX.
const pyStr=v=>JSON.stringify(v).replace(/[\u0080-\uffff]/g,c=>'\\u'+c.charCodeAt(0).toString(16).padStart(4,'0'));
// The existing board population_hash: sha256(json.dumps({group_id, signal_day, members: sorted(security_ids)}, sort_keys=True)).
const populationHash=(group_id,signal_day,ids)=>sha256('{"group_id": '+pyStr(group_id)+', "members": ['+[...ids].sort().map(pyStr).join(', ')+'], "signal_day": '+pyStr(signal_day)+'}');
const GROUP_CONTEXT_FIELDS=Object.freeze(['signal_day','group_id','classification_hash','population_hash','universe_id','universe_version','universe_members_hash','dictionary_version','mapping_version','knowledge_as_of','price_basis']);
const HEX=/^[0-9a-f]{64}$/;
function groupCheck(board,rows,manifest,context,data_kind){
 if(!isObj(manifest)||!isObj(context))jno('GROUP_MEMBERSHIP_REQUIRED');
 if(manifest.schema_version!=='technical-filter-membership/1')jno('GROUP_MEMBERSHIP_SCHEMA_MISMATCH');
 if(manifest.data_kind!==data_kind)jno('GROUP_DATA_KIND_MISMATCH');
 if(manifest.membership_status!=='CONFIRMED')jno('GROUP_MEMBERSHIP_UNCONFIRMED');
 const bound=manifest.context;if(!isObj(bound))jno('GROUP_CONTEXT_REQUIRED');
 for(const k of GROUP_CONTEXT_FIELDS){jtext(bound[k],'GROUP_CONTEXT_REQUIRED');if(context[k]!==bound[k])jno('GROUP_CONTEXT_MISMATCH:'+k);}
 for(const k of['classification_hash','population_hash','universe_members_hash'])if(!HEX.test(bound[k]))jno('GROUP_CONTEXT_HASH_INVALID');
 for(const k of['signal_day','group_id','population_hash'])if(jobj(board)[k]!==bound[k])jno('GROUP_CONTEXT_MISMATCH:'+k);
 jday(bound.signal_day);
 if(board.membership_source!=='common-classification:'+bound.classification_hash)jno('GROUP_CONTEXT_MISMATCH:classification_hash');
 if(!['RAW','SPLIT_ADJUSTED'].includes(bound.price_basis)||!bound.group_id.endsWith(':'+bound.price_basis))jno('GROUP_CONTEXT_MISMATCH:price_basis');
 const members=manifest.members;if(!Array.isArray(members))jno('GROUP_MEMBERSHIP_REQUIRED');
 const byCode=new Map(),ids=new Set();
 for(const m of members){if(!isObj(m))jno('GROUP_MEMBER_INVALID');const code=jtext(m.company_id,'GROUP_MEMBER_INVALID'),sid=jtext(m.security_id,'GROUP_MEMBER_INVALID');
  if(byCode.has(code)||ids.has(sid))jno('DUPLICATE_GROUP_MEMBER');jtext(m.classification_record_id,'GROUP_MEMBER_INVALID');jtext(m.issuer_id,'GROUP_MEMBER_INVALID');
  byCode.set(code,m);ids.add(sid);}
 if(populationHash(bound.group_id,bound.signal_day,ids)!==bound.population_hash)jno('BOARD_MEMBERSHIP_MISMATCH');
 const secs=boardSecurities(board);if(secs.size!==ids.size||[...secs.keys()].some(k=>!ids.has(k)))jno('BOARD_MEMBERSHIP_MISMATCH');
 const seen=new Set();
 for(const row of rows){if(!isObj(row))jno('COMPANY_CODE_REQUIRED');const code=jtext(row.code,'COMPANY_CODE_REQUIRED');
  if(seen.has(code))jno('DUPLICATE_GROUP_ROW');seen.add(code);if(!byCode.has(code))jno('ROW_OUTSIDE_GROUP');const m=byCode.get(code);
  if(row.signal_day!==bound.signal_day)jno('SIGNAL_DAY_MISMATCH',{board_day:bound.signal_day,qgv_day:typeof row.signal_day==='string'?row.signal_day:null});
  if(own(row,'classification_hash')&&row.classification_hash!==bound.classification_hash)jno('ROW_CLASSIFICATION_MISMATCH');
  if(own(row,'classification_record_id')&&row.classification_record_id!==m.classification_record_id)jno('ROW_CLASSIFICATION_MISMATCH');
  if(row.security_id!==m.security_id)jno('SECURITY_CLASSIFICATION_MISMATCH');
  if(row.issuer_id!==null&&row.issuer_id!==undefined&&row.issuer_id!==m.issuer_id)jno('ISSUER_CLASSIFICATION_MISMATCH');}
 if(seen.size!==byCode.size)jno('GROUP_MEMBER_MISSING');
 return byCode;}
const deepCopy=v=>(v===undefined?v:JSON.parse(JSON.stringify(v)));
// joinGroupRows(board, {qgv_rows, security_links, conditions, data_kind, group_manifest, group_context, connect_issuers=false})
// → {ok:true, schema_version:'technical-filter-join/2', membership_validation VERIFIED|VERIFIED_EMPTY, original_group_count,
// selected_count, issuer_connections, keys, rows} or {ok:false, code}. rows = deep copies of the selected input rows (with a
// connected issuer when connect_issuers), in input order; the inputs are never changed. An issuer is connected only for a null /
// absent row issuer, from the roster member of the same code (same record, hash, signal day) with evidence, and recorded.
function joinGroupRows(board,{qgv_rows=[],security_links=null,conditions=[],data_kind=null,group_manifest=null,group_context=null,connect_issuers=false}={}){
 try{if(data_kind!=='SYNTHETIC'&&data_kind!=='RETAINED_INPUT')jno('JOIN_DATA_KIND_REQUIRED');
  if(typeof connect_issuers!=='boolean')jno('ISSUER_CONNECTION_OPTION_INVALID');
  const rows=[...qgv_rows],members=groupCheck(board,rows,group_manifest,group_context,data_kind),connected=deepCopy(rows),audit=[];
  if(connect_issuers)for(const row of connected){if(row.issuer_id!==null&&row.issuer_id!==undefined)continue;const m=members.get(row.code),refs=m.evidence_refs;
   if(!Array.isArray(refs)||!refs.length||refs.some(v=>typeof v!=='string'||!v.trim()))jno('ISSUER_CONNECTION_EVIDENCE_REQUIRED');
   audit.push(Object.freeze({company_id:row.code,previous_field_present:own(row,'issuer_id'),previous_issuer_id:own(row,'issuer_id')?row.issuer_id:null,issuer_id:m.issuer_id,
    classification_record_id:m.classification_record_id,classification_hash:group_context.classification_hash,signal_day:group_context.signal_day,
    knowledge_as_of:group_context.knowledge_as_of,evidence_refs:Object.freeze([...refs]),basis:'VERIFIED_CLASSIFICATION_RECORD'}));row.issuer_id=m.issuer_id;}
  const j=joinRows(board,connected,{links:security_links,data_kind,group:{manifest:group_manifest,context:group_context}});if(!j.ok)return j;
  const r=evaluate(board,conditions),picked=connected.filter(x=>j.keys.has(x.security_id)&&r.rows.get(x.security_id)&&r.rows.get(x.security_id).state==='PASS');
  return Object.freeze({ok:true,schema_version:'technical-filter-join/2',data_kind,membership_validation:members.size?'VERIFIED':'VERIFIED_EMPTY',context:deepCopy(group_context),
   original_group_count:members.size,selected_count:picked.length,issuer_connections:Object.freeze(audit),keys:j.keys,rows:Object.freeze(picked)});}
 catch(e){if(e instanceof JoinRefusal)return Object.freeze({ok:false,code:e.code,...e.more});throw e;}}
function joinText(j){if(!j||j.ok)return null;const base=typeof j.code==='string'?j.code.split(':')[0]:j.code,w=own(JOIN_TEXT,j.code)?JOIN_TEXT[j.code]:own(JOIN_TEXT,base)?JOIN_TEXT[base]+' · '+j.code.slice(base.length+1):TEXT.UNKNOWN_REASON;
 // A QGV row without a producer evaluation day (signal_day null: no producer field today, never made from a price, as_of or
 // generation day — SIGNAL_DAY_CONTRACT.md) is said as such, apart from two different days.
 return j.code==='SIGNAL_DAY_MISMATCH'?(j.qgv_day===null||j.qgv_day===undefined?w+' · 보드 '+j.board_day+' · QGV 행 평가일 미제공(생산자 평가일 필드 없음 · 가격일·생성일로 추정 안 함)'
  :w+' · 보드 '+j.board_day+' · QGV '+j.qgv_day):w;}
const status=v=>(!v?TEXT.NONE:v.data_kind==='SYNTHETIC'?TEXT.SYNTHETIC:v.data_kind?'실자료 · '+v.data_kind:'자료 종류 표시 없음');
function source(){return Promise.resolve(Object.freeze({state:'NONE',code:'TECH_SCREEN_NOT_CONNECTED',payload:null,security_links:null,text:TEXT.NONE}));}
return Object.freeze({SCHEMA,SECURITY_IDENTIFIER_TYPES,METRICS,CONDITIONS,CHOICES,META,COND_TEXT,REASON,TEXT,JOIN_TEXT,validate,evaluate,securities,joinRows,joinGroupRows,groupCheck:(b,r,m,c,k)=>{try{groupCheck(b,r,m,c,k);return{ok:true};}catch(e){if(e instanceof JoinRefusal)return{ok:false,code:e.code};throw e;}},sha256,populationHash,GROUP_CONTEXT_FIELDS,joinText,metricState,display,medianText,decileText,reasonText,condText,status,cmp,source});
});
