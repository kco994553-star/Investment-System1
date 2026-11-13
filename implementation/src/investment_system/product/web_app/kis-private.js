/* Owner-private KIS layer: reader and authenticated client (IS2.kisPrivate; owner 2026-11-05, DC-44; Codex #480 contract
   docs/research/KIS_PRIVATE_PRICE_BRIDGE_20261105.md). The one public source that names the private Worker routes (owner
   2026-11-05 narrow exception: this file only, the seven routes below — status, chart, analysis, qgv and, approved the same
   day, technical, macro, news —, requests only after a click, Bearer header only; tests/test_private_boundary_static.py pins it).
   - Same screens, same formats: the public part stays as it is; a "비공개 펼치기" click asks for the owner's Google token
     (scope exactly openid email, include_granted_scopes false; NO_ZT §4.2), keeps it in this module's memory only, and reads
     the analysis, chart, technical, qgv, macro and news routes of the private Worker, which checks the owner on the server
     before it reads anything. The macro and news files have the public files' formats and are read by the public readers
     (IS2.macroObserved, IS2.newsRefresh: one reader each, DC-44); this file reads the KIS ones only. Closing the panel drops the shown data; 연결 끊기 drops the token; an expired token is dropped before use.
   - Readers refuse a file that breaks its contract (first fault, code + path). Adopted values only: an indicator's raw_value
     is never shown as its value; a null value is 미산출 with its reasons, never 0. A private QGV row never carries a rank
     (rank null + reason) and the public official ranks and TARGET are not touched by anything here. The five technical
     measures (kis-technical-measures/1, #480 follow-up: momentum 3/6/12m, volatility 6m, dollar volume 6m) show a value only
     when its value is not null; raw_value and the dollar-volume proxy stay diagnostics (a count); a rank refuses the file.
   - Price basis (Codex #498, owner 11/05): every technical result names its basis — RAW 원주가, SPLIT_ADJUSTED 확인된 분할 반영 —
     for the chart (bars basis), the analysis (price_basis = diagnostic_basis, chart_basis, result_kind, evidence adjustment_* /
     no_split_*, readiness adjustment.state) and the five measures (diagnostic_basis, chart_basis, settings_version, evidence
     price_basis). A file whose own fields disagree is refused (BASIS_CONFLICT / SETTINGS_BASIS_MISMATCH); an unknown enum is
     refused. basisAgreement: when the chart file's basis differs from a result's chart/diagnostic basis the screen does not
     attach that result's indicators to the chart (BASIS_MISMATCH). Counts are of this company on this evaluation day only.
   - Nothing is stored (no localStorage, cookie, cache), logged or sent elsewhere; requests use credentials 'omit',
     cache 'no-store', no referrer. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else{const I=root.IS2=root.IS2||{};I.kisPrivate=api;}})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
const SCHEMA=Object.freeze({BARS:'kis-bars/1',ANALYSIS:'kis-bars/1/analysis',MEASURES:'kis-technical-measures/1',QGV:'kis-qgv/1',STATUS:'kis-status/1'});
const ROUTE=Object.freeze({status:'/kis/status',chart:'/kis/chart',analysis:'/kis/analysis',technical:'/kis/technical',qgv:'/kis/qgv',macro:'/kis/macro',news:'/kis/news',
 classification:'/kis/classification'});
// Routes that take ?symbol=<SYM>; classification takes ?part=<one of CLASSIFICATION_PARTS> (owner 2026-11-08, the held common
// classification bundle, Codex #516 outputs byte for byte); the others take no query.
const BY_SYMBOL=Object.freeze(['chart','analysis','technical']);
const CLASSIFICATION_PARTS=Object.freeze(['view','technical','macro','qgv_links','dictionary','expanded_summary']);
// Read on its own click, never in the bundle's six-part read: the common industry → macro evidence query (Codex #525) and the input
// connection repair comparison (Codex #527) and the reference population research view (Codex #528).
const OTHER_PARTS=Object.freeze(['industry_macro','input_repair','reference_view']);
// The held issuer delivery (Codex #524, owner 2026-11-09): manifest, index, coverage and one detail shard ('expanded_detail/<2 hex>').
// These answer {bytes, body}: the reader checks each file's own bytes against the manifest (SHA-256 and size), not a re-encoding.
const EXPANDED_PARTS=Object.freeze(['expanded_manifest','expanded_index','expanded_coverage']);
const EXPANDED_DETAIL=/^expanded_detail\/([0-9a-f]{2})$/;
// The dual research delivery (Codex #529, owner 2026-11-11): 'dual_manifest|dual_summary|dual_index/<scope>' and
// 'dual_detail/<scope>/<3 digits>', each with its bytes (the reader checks them against the delivery manifest). '<scope>@333' (owner
// 2026-11-13) reads the 3/3/3 candidates' own delivery of that scope (&set=333), never the reduced one.
const DUAL_PART=/^(dual_manifest|dual_summary|dual_index|dual_lineage|dual_reference_anchor|dual_leaders_manifest|dual_leaders_index|dual_leaders_selection_manifest|dual_leaders_selection|dual_dist_manifest|dual_dist_index|dual_bins_manifest|dual_bins_index)\/(operating504|held1057)(@333)?$/,DUAL_DETAIL=/^(dual_detail|dual_leaders_detail|dual_dist_detail|dual_bins_detail)\/(operating504|held1057)(@333)?\/(\d{3})$/;
const dualPart=x=>typeof x==='string'&&(DUAL_PART.test(x)||DUAL_DETAIL.test(x));
// The company relationship delivery (owner 2026-11-13, Codex #531): 'ownership_index', and 'ownership_view|ownership_receipt/<entity id>'
// (one entity at a time), each with its bytes (the reader checks them against the index Main staged).
const OWN_PART=/^(ownership_view|ownership_receipt)\/([A-Z0-9][A-Z0-9-]{0,31})$/;
const ownPart=x=>typeof x==='string'&&(x==='ownership_index'||OWN_PART.test(x));
// The expanded summary also comes with its bytes: their SHA-256 is what the held issuer delivery names.
const expandedPart=x=>typeof x==='string'&&(x==='expanded_summary'||EXPANDED_PARTS.includes(x)||EXPANDED_DETAIL.test(x)||dualPart(x)||ownPart(x));
const SCOPES=Object.freeze(['email','openid']);
const SYMBOL=/^[A-Z][A-Z0-9-]{0,9}$/;
const DAY=/^\d{4}-\d{2}-\d{2}$/;
// Price bases and their words (owner 11/05): adjusted means confirmed splits only, never dividends, never provider MODP=1.
const BASES=Object.freeze(['RAW','SPLIT_ADJUSTED']);
const BASIS_TEXT=Object.freeze({RAW:'원주가',SPLIT_ADJUSTED:'확인된 분할 반영'});
const RESULT_KIND=Object.freeze({RAW_SERIES_DIAGNOSTIC:'RAW',SPLIT_ADJUSTED_SERIES_DIAGNOSTIC:'SPLIT_ADJUSTED'});
const ADJ_STATE=Object.freeze({DOCUMENTED_NO_SPLIT:'RAW',CONFIRMED_SPLITS_ONLY:'SPLIT_ADJUSTED',UNCONFIRMED:null});
// The five measures' settings, one version per basis (#498 technical_measures.settings_for_basis); numbers are the same.
const SETTINGS_BY_BASIS=Object.freeze({RAW:'technical-leaderboard/2026-11-03.1',SPLIT_ADJUSTED:'technical-leaderboard/split-adjusted-2026-11-05.1'});
const own=(o,k)=>Object.prototype.hasOwnProperty.call(o,k);
const isObj=v=>!!v&&typeof v==='object'&&!Array.isArray(v);
const isDay=v=>typeof v==='string'&&DAY.test(v)&&!Number.isNaN(Date.parse(v+'T00:00:00Z'));
const isTime=v=>typeof v==='string'&&/^\d{4}-\d{2}-\d{2}T/.test(v)&&!Number.isNaN(Date.parse(v));
const isDec=v=>typeof v==='string'&&/^-?\d+(?:\.\d+)?$/.test(v);
const intOk=v=>Number.isInteger(v)&&v>=0;
class Refusal extends Error{constructor(code,path){super(code+' '+path);this.code=code;this.path=path;}}
const refuse=(c,p)=>{throw new Refusal(c,p);};
const need=(o,keys,at)=>{if(!isObj(o))refuse('TYPE',at);for(const k of keys)if(!own(o,k))refuse('KEY_MISSING',at+'.'+k);};
const strArr=(v,at)=>{if(!Array.isArray(v)||v.some(x=>typeof x!=='string'))refuse('TYPE',at);return v;};
function freeze(o){if(o&&typeof o==='object'){Object.freeze(o);for(const v of Object.values(o))freeze(v);}return o;}
const wrap=fn=>json=>{try{return{ok:true,value:freeze(fn(JSON.parse(JSON.stringify(json))))};}catch(e){return e instanceof Refusal?{ok:false,code:e.code,path:e.path}:{ok:false,code:'INVALID',path:'$'};}};

/* kis-bars/1 (#480 field table): header facts the screen shows, and the bars as decimal strings or null. */
const validateBars=wrap(c=>{const at='$';
 need(c,['schema','symbol','source','price_basis_date','collected_at','corrected_at','calendar','timezone','basis','dividend_adjustment','currency','bars','raw_bars','splits','confirmed_ranges','held_ranges','publication_scope'],at);
 if(c.schema!==SCHEMA.BARS)refuse('SCHEMA_VERSION',at+'.schema');
 if(c.publication_scope!=='OWNER_PRIVATE_ONLY')refuse('SCOPE',at+'.publication_scope');
 if(typeof c.symbol!=='string'||!SYMBOL.test(c.symbol))refuse('SYMBOL',at+'.symbol');
 if(typeof c.source!=='string'||!c.source)refuse('TYPE',at+'.source');
 if(!BASES.includes(c.basis))refuse('ENUM',at+'.basis');
 if(c.basis==='SPLIT_ADJUSTED'&&c.dividend_adjustment!=='NONE')refuse('ENUM',at+'.dividend_adjustment');
 if(c.currency!=='USD'||c.calendar!=='NYSE')refuse('ENUM',at+'.currency');
 if(c.price_basis_date!==null&&!isDay(c.price_basis_date))refuse('DATE',at+'.price_basis_date');
 if(!isTime(c.collected_at))refuse('TIME',at+'.collected_at');if(c.corrected_at!==null&&!isTime(c.corrected_at))refuse('TIME',at+'.corrected_at');
 for(const key of['bars','raw_bars']){if(!Array.isArray(c[key]))refuse('TYPE',at+'.'+key);let last='';
  c[key].forEach((r,i)=>{const p=at+'.'+key+'['+i+']';need(r,['date','open','high','low','close','volume'],p);if(!isDay(r.date)||r.date<=last)refuse('DATE_ORDER',p+'.date');last=r.date;
   for(const f of['open','high','low','close','volume'])if(r[f]!==null&&!isDec(r[f]))refuse('DECIMAL_INVALID',p+'.'+f);});}
 const lastDay=c.bars.length?c.bars[c.bars.length-1].date:null;if(c.price_basis_date!==lastDay)refuse('BASIS_DATE_MISMATCH',at+'.price_basis_date');
 for(const k of['splits','confirmed_ranges','held_ranges'])if(!Array.isArray(c[k]))refuse('TYPE',at+'.'+k);
 return c;});

/* evidence (#498 basis_evidence): price_basis, and for SPLIT_ADJUSTED adjustment_start / _end / _reference with adjustment_method
   CONFIRMED_SPLITS_ONLY, for RAW no_split_start / _end / _reference. Missing coverage is allowed (the values are then held). */
function checkEvidence(e,basis,at){if(e===undefined||e===null)return;if(!isObj(e))refuse('TYPE',at);
 if(own(e,'price_basis')){if(!BASES.includes(e.price_basis))refuse('ENUM',at+'.price_basis');if(e.price_basis!==basis)refuse('BASIS_CONFLICT',at+'.price_basis');}
 if(own(e,'adjustment_method')&&e.adjustment_method!=='CONFIRMED_SPLITS_ONLY')refuse('ENUM',at+'.adjustment_method');
 if(basis==='RAW'&&['adjustment_method','adjustment_start','adjustment_end'].some(k=>own(e,k)))refuse('BASIS_CONFLICT',at+'.adjustment_method');
 for(const k of['adjustment_start','adjustment_end','no_split_start','no_split_end'])if(own(e,k)&&e[k]!==null&&!isDay(e[k]))refuse('DATE',at+'.'+k);
 for(const[a,b]of[['adjustment_start','adjustment_end'],['no_split_start','no_split_end']])if(e[a]&&e[b]&&e[a]>e[b])refuse('DATE_ORDER',at+'.'+a);}
function evidenceView(e,basis){const x=isObj(e)?e:{};
 if(basis==='SPLIT_ADJUSTED')return x.adjustment_start&&x.adjustment_end?'분할 반영 증거 구간 '+x.adjustment_start+' ~ '+x.adjustment_end+' · 확인된 분할만 반영'+(x.adjustment_reference?' · 근거 기록 있음':' · 근거 기록 없음')
  :'분할 반영 증거 구간 없음 · 값 미채택';
 return x.no_split_start&&x.no_split_end?'분할 없음 증거 구간 '+x.no_split_start+' ~ '+x.no_split_end+(x.no_split_reference?' · 근거 기록 있음':' · 근거 기록 없음'):'분할 없음 증거 구간 없음';}

/* kis-bars/1/analysis: status NORMAL / STALE / MISSING for the requested day, and per indicator raw_value / value / reasons.
   The view below shows value only; raw_value stays a diagnostic count. */
const validateAnalysis=wrap(a=>{const at='$';
 need(a,['schema','status','data_asof','evaluation_day','collected_at','metrics','raw_count','adopted_count','result_kind','price_basis','chart_basis','diagnostic_basis'],at);
 if(a.schema!==SCHEMA.ANALYSIS)refuse('SCHEMA_VERSION',at+'.schema');
 for(const k of['price_basis','chart_basis','diagnostic_basis'])if(!BASES.includes(a[k]))refuse('ENUM',at+'.'+k);
 if(!own(RESULT_KIND,a.result_kind))refuse('ENUM',at+'.result_kind');
 // price_basis and diagnostic_basis are the same declared basis of the indicators; the result kind names it (#498).
 if(a.price_basis!==a.diagnostic_basis)refuse('BASIS_CONFLICT',at+'.price_basis');if(RESULT_KIND[a.result_kind]!==a.diagnostic_basis)refuse('BASIS_CONFLICT',at+'.result_kind');
 if(own(a,'signal_day')&&!isDay(a.signal_day))refuse('DATE',at+'.signal_day');
 checkEvidence(a.evidence,a.diagnostic_basis,at+'.evidence');
 if(own(a,'readiness')&&a.readiness!==null){const r=a.readiness,rp=at+'.readiness';if(!isObj(r))refuse('TYPE',rp);
  if(own(r,'metrics')){if(!isObj(r.metrics))refuse('TYPE',rp+'.metrics');
   for(const[id,x]of Object.entries(r.metrics)){if(!isObj(x))refuse('TYPE',rp+'.metrics.'+id);if(!own(x,'adjustment')||x.adjustment===null)continue;
    const j=x.adjustment,p=rp+'.metrics.'+id+'.adjustment';need(j,['price_basis','state'],p);
    if(!BASES.includes(j.price_basis))refuse('ENUM',p+'.price_basis');if(j.price_basis!==a.diagnostic_basis)refuse('BASIS_CONFLICT',p+'.price_basis');
    if(!own(ADJ_STATE,j.state))refuse('ENUM',p+'.state');if(ADJ_STATE[j.state]!==null&&ADJ_STATE[j.state]!==j.price_basis)refuse('BASIS_CONFLICT',p+'.state');
    for(const k of['required_start','required_end','evidence_start','evidence_end'])if(own(j,k)&&j[k]!==null&&!isDay(j[k]))refuse('DATE',p+'.'+k);}}}
 if(!['NORMAL','STALE','MISSING'].includes(a.status))refuse('ENUM',at+'.status');
 if(a.data_asof!==null&&!isDay(a.data_asof))refuse('DATE',at+'.data_asof');if(!isDay(a.evaluation_day))refuse('DATE',at+'.evaluation_day');
 if(!isTime(a.collected_at))refuse('TIME',at+'.collected_at');
 if(!isObj(a.metrics))refuse('TYPE',at+'.metrics');let raw=0,adopted=0;
 for(const[id,m]of Object.entries(a.metrics)){const p=at+'.metrics.'+id;need(m,['raw_value','value','null_reasons'],p);strArr(m.null_reasons,p+'.null_reasons');
  for(const f of['raw_value','value'])if(m[f]!==null&&typeof m[f]!=='number'&&!isDec(m[f]))refuse('VALUE_INVALID',p+'.'+f);
  if(m.value!==null&&m.null_reasons.length)refuse('VALUE_WITH_REASON',p+'.value');if(m.value===null&&!m.null_reasons.length&&m.raw_value!==null)refuse('REASON_MISSING',p+'.null_reasons');
  if(m.raw_value!==null)raw++;if(m.value!==null)adopted++;}
 if(!intOk(a.raw_count)||a.raw_count!==raw)refuse('COUNT_MISMATCH',at+'.raw_count');if(!intOk(a.adopted_count)||a.adopted_count!==adopted)refuse('COUNT_MISMATCH',at+'.adopted_count');
 return a;});

/* kis-technical-measures/1 (the #469 five measures of one company on its signal day S, Codex's technical-measures mode): per
   measure value (adopted) / raw_value (diagnostic) / null_reasons / state VALUE · DIAGNOSTIC · NOT_COMPUTED and its window.
   The state must agree with the values (VALUE ⇔ value; DIAGNOSTIC = raw only, with reasons; NOT_COMPUTED = neither, with
   reasons); counts equal the measures; a single-company file has no rank (rank_count 0, any other rank field null). */
const MEASURES=Object.freeze([['momentum_3m','PERCENT'],['momentum_6m','PERCENT'],['momentum_12m','PERCENT'],['volatility_6m','PERCENT_PER_DAY'],['dollar_volume_6m','USD_PER_TRADING_DAY']]);
const isNum=v=>v===null||isDec(v)||(typeof v==='number'&&Number.isFinite(v));
const noRank=(o,at)=>{for(const k of Object.keys(o))if(/rank/i.test(k)&&k!=='rank_count'&&o[k]!==null)refuse('RANK_NOT_ALLOWED',at+'.'+k);};
const validateMeasures=wrap(m=>{const at='$';
 need(m,['schema','result_kind','symbol','signal_day','evaluation_day','data_asof','status','collected_at','publication_scope','metrics','raw_count','adopted_count','rank_count','chart_basis','diagnostic_basis','settings_version'],at);
 if(m.schema!==SCHEMA.MEASURES)refuse('SCHEMA_VERSION',at+'.schema');
 for(const k of['chart_basis','diagnostic_basis'])if(!BASES.includes(m[k]))refuse('ENUM',at+'.'+k);
 // One settings version per basis (#498): the RAW version on an adjusted result, or the reverse, is a broken file.
 if(!Object.values(SETTINGS_BY_BASIS).includes(m.settings_version))refuse('SETTINGS_VERSION',at+'.settings_version');
 if(SETTINGS_BY_BASIS[m.diagnostic_basis]!==m.settings_version)refuse('SETTINGS_BASIS_MISMATCH',at+'.settings_version');
 checkEvidence(m.evidence,m.diagnostic_basis,at+'.evidence');
 if(m.publication_scope!=='OWNER_PRIVATE_ONLY')refuse('SCOPE',at+'.publication_scope');
 if(m.result_kind!=='SINGLE_COMPANY_MEASURES')refuse('ENUM',at+'.result_kind');
 if(typeof m.symbol!=='string'||!SYMBOL.test(m.symbol))refuse('SYMBOL',at+'.symbol');
 if(!['NORMAL','STALE','MISSING'].includes(m.status))refuse('ENUM',at+'.status');
 if(!isDay(m.signal_day))refuse('DATE',at+'.signal_day');if(!isDay(m.evaluation_day))refuse('DATE',at+'.evaluation_day');
 if(m.data_asof!==null&&(!isDay(m.data_asof)||m.data_asof>m.signal_day))refuse('DATE',at+'.data_asof');
 if(!isTime(m.collected_at))refuse('TIME',at+'.collected_at');
 noRank(m,at);if(m.rank_count!==0)refuse('RANK_NOT_ALLOWED',at+'.rank_count');
 if(!isObj(m.metrics))refuse('TYPE',at+'.metrics');
 for(const id of Object.keys(m.metrics))if(!MEASURES.some(([x])=>x===id))refuse('METRIC_UNKNOWN',at+'.metrics.'+id);
 let raw=0,adopted=0;
 for(const[id,unit]of MEASURES){const p=at+'.metrics.'+id,x=m.metrics[id];if(!own(m.metrics,id))refuse('KEY_MISSING',p);
  need(x,['value','raw_value','unit','null_reasons','state','window_start','window_end','observed_days','expected_days'],p);noRank(x,p);
  if(x.unit!==unit)refuse('UNIT_MISMATCH',p+'.unit');strArr(x.null_reasons,p+'.null_reasons');
  for(const f of['value','raw_value'])if(!isNum(x[f]))refuse('VALUE_INVALID',p+'.'+f);
  const v=x.value!==null,r=x.raw_value!==null,n=x.null_reasons.length;
  if(!['VALUE','DIAGNOSTIC','NOT_COMPUTED'].includes(x.state))refuse('ENUM',p+'.state');
  if(x.state==='VALUE'?!(v&&r&&!n):x.state==='DIAGNOSTIC'?(v||!r||!n):(v||r||!n))refuse('STATE_MISMATCH',p+'.state');
  for(const f of['window_start','window_end','anchor_day'])if(own(x,f)&&x[f]!==null&&!isDay(x[f]))refuse('DATE',p+'.'+f);
  if(x.window_start!==null&&x.window_end!==null&&x.window_start>x.window_end)refuse('DATE_ORDER',p+'.window_start');
  for(const f of['observed_days','expected_days'])if(x[f]!==null&&!intOk(x[f]))refuse('COUNT_INVALID',p+'.'+f);
  if(x.observed_days!==null&&x.expected_days!==null&&x.observed_days>x.expected_days)refuse('COUNT_INVALID',p+'.observed_days');
  if(r)raw++;if(v)adopted++;}
 if(!intOk(m.raw_count)||m.raw_count!==raw)refuse('COUNT_MISMATCH',at+'.raw_count');if(!intOk(m.adopted_count)||m.adopted_count!==adopted)refuse('COUNT_MISMATCH',at+'.adopted_count');
 return m;});

/* kis-qgv/1: the private layer of the common engine. Never a rank, never the official publication or TARGET. */
const validateQgv=wrap(q=>{const at='$';
 need(q,['schema','layer','calc_version','price_basis_date','calculated_at','financial_input_as_of','rows','coverage','rank','rank_reason','official_publication_replaced','TARGET_modified','population'],at);
 if(q.schema!==SCHEMA.QGV)refuse('SCHEMA_VERSION',at+'.schema');if(q.layer!=='OWNER_PRIVATE')refuse('ENUM',at+'.layer');
 if(q.rank!==null)refuse('RANK_NOT_ALLOWED',at+'.rank');if(q.official_publication_replaced!==false||q.TARGET_modified!==false)refuse('OFFICIAL_TOUCHED',at+'.official_publication_replaced');
 if(!isDay(q.price_basis_date))refuse('DATE',at+'.price_basis_date');if(!isTime(q.calculated_at))refuse('TIME',at+'.calculated_at');
 need(q.coverage,['codes','Q','G','V','QGV'],at+'.coverage');for(const k of['codes','Q','G','V','QGV'])if(!intOk(q.coverage[k])||q.coverage[k]>q.coverage.codes)refuse('COUNT_INVALID',at+'.coverage.'+k);
 if(!isObj(q.rows))refuse('TYPE',at+'.rows');
 for(const[k,r]of Object.entries(q.rows)){const p=at+'.rows.'+k;need(r,['axes','total'],p);need(r.axes,['Q','G','V'],p+'.axes');
  for(const ax of['Q','G','V']){const x=r.axes[ax];need(x,['score'],p+'.axes.'+ax);if(x.score!==null&&(typeof x.score!=='number'||!Number.isFinite(x.score)))refuse('SCORE_INVALID',p+'.axes.'+ax);}
  if(r.total!==null&&(typeof r.total!=='number'||!Number.isFinite(r.total)))refuse('SCORE_INVALID',p+'.total');}
 return q;});

const REASON=Object.freeze({SPLIT_ADJUSTED_DISPLAY_ADAPTER_PENDING:'분할 반영 계열의 지표 어댑터 준비 중 (#498 이전 판 결과)',HELD_RANGE_IN_WINDOW:'보류 구간이 계산 창에 있음',
 CORPORATE_ACTION_IN_RAW_WINDOW:'원주가 창 안에 분할 사건',ACTION_BASIS_UNCONFIRMED:'분할 기준 미확인',IDENTITY_RANGE_UNCONFIRMED:'증권 신원 기간 미확인',
 VOLUME_SCOPE_UNCONFIRMED:'거래량 범위 미확인',INSUFFICIENT_HISTORY:'이력 부족',PRICE_NOT_AVAILABLE:'가격 없음',PRICE_BASIS_DATE_MISSING:'기준일 가격 없음',
 SOURCE_SECURITY_UNCONFIRMED:'공급처 증권 신원 미확인',PRICE_IDENTITY_CONFLICT:'가격 신원 충돌',PRICE_INPUT_HELD:'보류 구간 가격',SPLIT_AFTER_SHARE_COUNT:'주식수 기준일 뒤 분할',
 PAIRED_COMPARISON_POPULATION_NOT_ESTABLISHED:'같은 모집단·입력 비교가 확인되지 않아 순위 없음',PRICE_WINDOW_INCOMPLETE_OR_INVALID:'가격 창이 모자라거나 맞지 않음',
 RETURN_WINDOW_INCOMPLETE_OR_INVALID:'수익률 창이 모자라거나 맞지 않음',VOLUME_WINDOW_INCOMPLETE_OR_INVALID:'거래량 창이 모자라거나 맞지 않음',TRADE_SCOPE_UNCONFIRMED:'거래 범위 미확인'});
const reasonText=c=>(typeof c==='string'&&own(REASON,c)?REASON[c]:'사유 코드 '+c);
// Codex #480: NORMAL is relative to the evaluation day, never a claim that the quote is current.
const STATUS_TEXT=Object.freeze({NORMAL:'평가일 기준 정상 · 현재 시세 최신 아님',STALE:'갱신 지연',MISSING:'자료 없음'});

// Public vs private basis day: the same day can be compared; a different day says so (owner 2026-11-05).
function basisCompare(publicDay,privateDay){
 if(!privateDay)return{same:false,text:'비공개 기준일 없음 · 공개와 비교하지 않음'};
 if(!publicDay)return{same:false,text:'공개 기준일 없음 · 비공개 기준일 '+privateDay+' · 직접 비교 제한'};
 return publicDay===privateDay?{same:true,text:'공개·비공개 기준일 같음 '+privateDay}:{same:false,text:'공개 기준일 '+publicDay+' · 비공개 기준일 '+privateDay+' · 기준일이 달라 직접 비교 제한'};}

// The two-layer line (owner 2026-11-05 follow-up 2): one engine, its rules and version on both layers; what may differ.
const LAYER_NOTE='공개와 같은 계산식·규칙·판 · 공급처·기준일·확보 범위는 다를 수 있음 · 공개 결과는 바뀌지 않음';
// The fixed line on every adjusted result (owner 11/05): the real split-event validation is not done.
const ADJUSTED_NOTE='실제 분할 사건 검증 미완료 · 분할 없는 구간의 조정 경로 확인';
// Counts are this company's on this evaluation day: never a number of companies, never market coverage (owner 11/05).
const COUNT_SCOPE='(이 기업·이 평가일)';
const counts=(raw,adopted,held)=>'진단값(원시 계산) '+raw+'개 · 채택값 '+adopted+'개 '+COUNT_SCOPE+' · 미산출 '+held+'개';
/* Chart and indicator basis must agree: a result whose chart_basis or diagnostic_basis differs from the chart file's basis is not
   attached to that chart (BASIS_MISMATCH, with words), never silently. */
function basisAgreement(chartBasis,r){const d=r.diagnostic_basis,c=r.chart_basis;
 if(chartBasis===d&&chartBasis===c)return Object.freeze({code:'BASIS_MATCH',same:true,text:'차트·지표 가격 기준 같음 · '+BASIS_TEXT[d]});
 return Object.freeze({code:'BASIS_MISMATCH',same:false,text:'가격 기준 불일치 · 지표를 이 차트에 붙이지 않음 · 차트 파일 '+(BASIS_TEXT[chartBasis]||'기준 없음')+' · 지표 '+BASIS_TEXT[d]+(c!==d?' · 결과의 차트 기준 '+BASIS_TEXT[c]:'')});}
function barsMeta(b){return Object.freeze({source:b.source==='KIS retained dailyprice MODP0'?'KIS 보관 일봉 (MODP=0)':b.source,basis:BASIS_TEXT[b.basis],basisCode:b.basis,
 note:b.basis==='SPLIT_ADJUSTED'?ADJUSTED_NOTE:null,
 price_basis_date:b.price_basis_date,collected_at:b.collected_at,corrected:b.corrected_at?'정정 반영 '+b.corrected_at:'정정 증거 없음',held:b.held_ranges.length,splits:b.splits.length});}
const ADJ_STATE_TEXT=Object.freeze({CONFIRMED_SPLITS_ONLY:'확인된 분할만 반영',DOCUMENTED_NO_SPLIT:'분할 없음 확인',UNCONFIRMED:'분할 기준 미확인'});
function adjustmentStates(a){const r=isObj(a.readiness)&&isObj(a.readiness.metrics)?a.readiness.metrics:{},n={};
 for(const x of Object.values(r))if(isObj(x)&&isObj(x.adjustment)){const k=x.adjustment.state;n[k]=own(n,k)?n[k]+1:1;}
 const keys=Object.keys(ADJ_STATE_TEXT).filter(k=>n[k]);
 return keys.length?'지표별 분할 상태 · '+keys.map(k=>ADJ_STATE_TEXT[k]+' 지표 '+n[k]+'개').join(' · '):null;}
function analysisView(a){const ids=Object.keys(a.metrics).sort(),adj=a.diagnostic_basis==='SPLIT_ADJUSTED'||a.chart_basis==='SPLIT_ADJUSTED';
 return Object.freeze({status:a.status,statusText:STATUS_TEXT[a.status],data_asof:a.data_asof,collected_at:a.collected_at,
  evaluation_day:a.evaluation_day,signal_day:own(a,'signal_day')?a.signal_day:null,
  basis:a.diagnostic_basis,basisText:BASIS_TEXT[a.diagnostic_basis],chartBasis:a.chart_basis,chartBasisText:BASIS_TEXT[a.chart_basis],
  resultKind:a.result_kind,evidence:evidenceView(a.evidence,a.diagnostic_basis),adjustment:adjustmentStates(a),note:adj?ADJUSTED_NOTE:null,
  summary:counts(a.raw_count,a.adopted_count,ids.filter(id=>a.metrics[id].value===null).length),
  adopted:Object.freeze(ids.filter(id=>a.metrics[id].value!==null).map(id=>Object.freeze({id,value:String(a.metrics[id].value)}))),
  held:Object.freeze(ids.filter(id=>a.metrics[id].value===null).map(id=>Object.freeze({id,text:'미산출 · '+(a.metrics[id].null_reasons.map(reasonText).join(' · ')||'원시값 없음')})))});}
const MEASURE_LABEL=Object.freeze({momentum_3m:'모멘텀 3개월',momentum_6m:'모멘텀 6개월',momentum_12m:'모멘텀 12개월',volatility_6m:'변동성 6개월',dollar_volume_6m:'거래대금 6개월'});
const UNIT_TEXT=Object.freeze({PERCENT:'%',PERCENT_PER_DAY:'% (일간 수익률 표준편차)',USD_PER_TRADING_DAY:'USD/거래일'});
const OBS_TEXT=Object.freeze({CLOSES:'종가',DAILY_RETURNS:'일간 수익률',TRADING_DAYS:'거래일'});
// Words of the five measures: a value only when it is adopted (value not null); a diagnostic is counted, never shown.
function measuresView(m){const ids=MEASURES.map(([id])=>id),M=m.metrics;
 const win=x=>(x.window_start&&x.window_end?'관측 창 '+x.window_start+' ~ '+x.window_end:'관측 창 없음')+(x.observed_days!==null&&x.expected_days!==null?' · '+x.observed_days+' / '+x.expected_days+' '+(own(OBS_TEXT,x.observation_unit)?OBS_TEXT[x.observation_unit]:'일'):'');
 const adj=m.diagnostic_basis==='SPLIT_ADJUSTED'||m.chart_basis==='SPLIT_ADJUSTED';
 return Object.freeze({status:m.status,statusText:STATUS_TEXT[m.status],signal_day:m.signal_day,evaluation_day:m.evaluation_day,data_asof:m.data_asof,collected_at:m.collected_at,
  basis:m.diagnostic_basis,basisText:BASIS_TEXT[m.diagnostic_basis],chartBasis:m.chart_basis,settings_version:m.settings_version,
  evidence:evidenceView(m.evidence,m.diagnostic_basis),note:adj?ADJUSTED_NOTE:null,
  summary:counts(m.raw_count,m.adopted_count,ids.filter(id=>M[id].value===null).length),
  rank:'그룹 순위 미산출 · 한 기업 측정만 있음 (순위는 같은 날·같은 그룹 보드에서만 · 그룹 보드는 비공개 경로 미연결)',
  rows:Object.freeze(ids.map(id=>{const x=M[id];return Object.freeze(x.value!==null?{id,label:MEASURE_LABEL[id],kind:'VALUE',value:String(x.value)+' '+UNIT_TEXT[x.unit],window:win(x)}
   :{id,label:MEASURE_LABEL[id],kind:x.state,value:null,window:win(x),text:'미산출 · '+x.null_reasons.map(reasonText).join(' · ')+(x.state==='DIAGNOSTIC'?' · 진단값만 있음 (값 미표시)':'')});}))});}
function qgvView(q,code){const c=q.coverage,n=c.codes;
 const lines=['Q 산출 '+c.Q+' / '+n,'G 산출 '+c.G+' / '+n,'V 산출 '+c.V+' / '+n,'Q·G·V 모두 '+c.QGV+' / '+n];
 const r=code&&own(q.rows,code)?q.rows[code]:null,st=code&&isObj(q.price_status)&&own(q.price_status,code)?q.price_status[code]:null;
 const axis=ax=>{const x=r.axes[ax];return x.score===null?ax+' 미산출'+(x.reason?' · '+reasonText(x.reason):''):ax+' '+(Math.round(x.score*10)/10);};
 return Object.freeze({coverage:Object.freeze(lines),price_basis_date:q.price_basis_date,calc_version:q.calc_version,
  rank:'비공개 순위 없음 · '+reasonText(q.rank_reason),official:'공개 공식 순위·TARGET은 이 결과로 바뀌지 않음',
  row:r?Object.freeze({code,axes:Object.freeze(['Q','G','V'].map(axis)),total:r.axes.V.score===null?'QGV 총점 미산출 · V 미산출':r.total===null?'QGV 총점 미산출':'QGV '+(Math.round(r.total*10)/10),
   price:st==='SUPPLIED'?'KIS 가격 반영':st?'가격 미반영 · '+reasonText(st):null}):null});}

/* The authenticated client. win = the page window (google), origin = the approved private Worker origin, send(url, init) =
   the layer's gated network call (prices.js; network stays in the layer). connect() must run inside a click (GIS opens its
   window from the user gesture). */
function createClient({win,clientId,origin,send,now=()=>Date.now()}={}){
 let token='',expiresAt=0,epoch=0;const listeners=new Set();
 const notify=()=>{for(const f of[...listeners]){try{f();}catch(_){}}};
 const oauth=()=>win&&win.google&&win.google.accounts&&win.google.accounts.oauth2;
 const drop=()=>{token='';expiresAt=0;epoch++;notify();};
 const connected=()=>{if(token&&expiresAt<=now())drop();return!!token;};
 function state(){return Object.freeze({ready:!!clientId&&!!origin&&typeof send==='function',gis:!!oauth(),connected:connected()});}
 function connect(){return new Promise((resolve,reject)=>{const o=oauth();if(!o||!clientId||!origin){reject(Error('LOGIN_UNAVAILABLE'));return;}
  const client=o.initTokenClient({client_id:clientId,scope:'openid email',include_granted_scopes:false,prompt:'',callback:r=>{
   const scopes=r&&typeof r.scope==='string'?[...new Set(r.scope.trim().split(/\s+/).map(s=>s==='https://www.googleapis.com/auth/userinfo.email'?'email':s))].sort():[];
   const secs=r?Number(r.expires_in):NaN;
   if(!r||r.error||typeof r.access_token!=='string'||!/^[A-Za-z0-9._~-]{1,4096}$/.test(r.access_token)||!Number.isFinite(secs)||secs<=0||scopes.join(' ')!==SCOPES.join(' ')){reject(Error('LOGIN_REFUSED'));return;}
   token=r.access_token;expiresAt=now()+Math.min(secs,3600)*1000-30000;epoch++;notify();resolve(state());},error_callback:()=>reject(Error('LOGIN_CANCELED'))});
  client.requestAccessToken();});}
 function disconnect(){drop();}
 async function get(route,symbol,signal){
  if(!own(ROUTE,route))throw Error('ROUTE_UNKNOWN');const bySym=BY_SYMBOL.includes(route),byPart=route==='classification';
  if(bySym&&(typeof symbol!=='string'||!SYMBOL.test(symbol)))throw Error('REQUEST_INVALID');if(byPart&&!CLASSIFICATION_PARTS.includes(symbol)&&!OTHER_PARTS.includes(symbol)&&!expandedPart(symbol))throw Error('REQUEST_INVALID');const raw=byPart&&expandedPart(symbol);
  if(!connected())throw Error('AUTH_REQUIRED');const mine=epoch;
  const shard=byPart?EXPANDED_DETAIL.exec(symbol):null,dual=byPart?DUAL_PART.exec(symbol):null,dualDetail=byPart?DUAL_DETAIL.exec(symbol):null,ownM=byPart?OWN_PART.exec(symbol):null;
  const url=origin+ROUTE[route]+(bySym?'?symbol='+symbol:shard?'?part=expanded_detail&shard='+shard[1]:ownM?'?part='+ownM[1]+'&entity='+ownM[2]:dual?'?part='+dual[1]+'&scope='+dual[2]+(dual[3]?'&set=333':'')
   :dualDetail?'?part='+dualDetail[1]+'&scope='+dualDetail[2]+'&shard='+dualDetail[4]+(dualDetail[3]?'&set=333':''):byPart?'?part='+symbol:'');
  let res;try{res=await send(url,{method:'GET',headers:{Authorization:'Bearer '+token},credentials:'omit',cache:'no-store',referrerPolicy:'no-referrer',redirect:'error',signal});}
  catch(e){if(signal&&signal.aborted)throw Error('CANCELED');throw Error('UPSTREAM_UNAVAILABLE');}
  if(mine!==epoch)throw Error('CANCELED');
  let body=null,bytes=null;
  if(raw&&res.ok){try{bytes=new Uint8Array(await res.arrayBuffer());body=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));}catch(_){body=null;}}
  else{try{body=await res.json();}catch(_){body=null;}}
  if(mine!==epoch)throw Error('CANCELED');
  if(res.status===401||res.status===403){const code=body&&body.error&&typeof body.error.code==='string'?body.error.code:'AUTH_FORBIDDEN';if(code==='AUTH_FORBIDDEN'||code==='ORIGIN_FORBIDDEN')drop();throw Error(code==='ORIGIN_FORBIDDEN'?'AUTH_FORBIDDEN':code);}
  if(!res.ok){const code=body&&body.error&&typeof body.error.code==='string'&&/^[A-Z][A-Z0-9_]{1,63}$/.test(body.error.code)?body.error.code:'UPSTREAM_UNAVAILABLE';throw Error(code);}
  if(!isObj(body))throw Error('KIS_SERIES_INVALID');return raw?Object.freeze({bytes,body}):body;}
 return Object.freeze({state,connect,disconnect,get,subscribe:f=>{listeners.add(f);return()=>listeners.delete(f);}});}

return Object.freeze({SCHEMA,ROUTE,CLASSIFICATION_PARTS,EXPANDED_PARTS,LAYER_NOTE,ADJUSTED_NOTE,BASIS_TEXT,SETTINGS_BY_BASIS,SOURCE_WORDS:'비공개 보관본 · 인증 경로',validateBars,validateAnalysis,validateMeasures,validateQgv,basisCompare,basisAgreement,barsMeta,analysisView,measuresView,qgvView,reasonText,createClient});
});
