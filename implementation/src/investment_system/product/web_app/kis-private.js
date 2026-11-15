/* Owner-private KIS layer: reader and authenticated client (IS2.kisPrivate; owner 2026-11-05 DC-44, 2026-11-14 DC-52, 2026-11-15
   DC-53; Codex #480 contract docs/research/KIS_PRIVATE_PRICE_BRIDGE_20261105.md). The one web source that names the private
   Worker routes (owner 2026-11-05 narrow exception: this file only, the five routes below — status, chart, analysis, technical,
   qgv —, requests only after a click, Bearer header only; tests/test_private_boundary_static.py pins it). The public Pages
   preview does not publish this file (tools/web_app_preview.py OWNER_PRIVATE): the Pages guard refuses private Worker paths and
   private schema names in published code, and no exception for it is approved.
   - A click asks for the owner's Google token (scope exactly openid email, include_granted_scopes false; NO_ZT §4.2), keeps it
     in this module's memory only, and reads the routes of the private Worker, which checks the owner on the server before it
     reads anything. 연결 끊기 drops the token; an expired token is dropped before use.
   - Readers refuse a file that breaks its contract (first fault, code + path). An indicator's raw_value is never shown as its
     adopted value (the screen shows the producer's reference_value apart, tagged 검증 전(참고); see the display tiers below); a null value is 미산출 with its reasons, never 0. A private QGV row never carries a rank
     (rank null + reason) and the public official ranks and TARGET are not touched by anything here. The five technical
     measures (#480 follow-up: momentum 3/6/12m, volatility 6m, dollar volume 6m) show a value only when its value is not
     null; raw_value and the dollar-volume proxy stay diagnostics (a count); a rank refuses the file.
   - Price basis (Codex #498, owner 11/05): every technical result names its basis — RAW 원주가, SPLIT_ADJUSTED 확인된 분할 반영 —
     for the chart (bars basis), the analysis (price_basis = diagnostic_basis, chart_basis, result_kind, evidence adjustment_* /
     no_split_*, readiness adjustment.state) and the five measures (diagnostic_basis, chart_basis, settings_version, evidence
     price_basis). A file whose own fields disagree is refused (BASIS_CONFLICT / SETTINGS_BASIS_MISMATCH); an unknown enum is
     refused. basisAgreement: when the chart file's basis differs from a result's chart/diagnostic basis the screen does not
     attach that result's indicators to the chart (BASIS_MISMATCH). Counts are of this company on this evaluation day only.
   - Read token status (DC-53, WORKER_READ_TOKEN_EXPIRY_20261115.md): validateTokenStatus / tokenStatusView read the Worker's
     status answer; NO_EXPIRY is 만료일 없음 (dates null), a dated token shows its date and the 14-day warning, a refusal or
     error its own words. Nothing here infers an expiry from a missing date.
   - Nothing is stored (no localStorage, cookie, cache), logged or sent elsewhere; requests use credentials 'omit',
     cache 'no-store', no referrer. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else{const I=root.IS2=root.IS2||{};I.kisPrivate=api;}})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
const SCHEMA=Object.freeze({BARS:'kis-bars/1',ANALYSIS:'kis-bars/1/analysis',MEASURES:'kis-technical-measures/1',QGV:'kis-qgv/1',STATUS:'kis-status/1'});
const ROUTE=Object.freeze({status:'/kis/status',chart:'/kis/chart',analysis:'/kis/analysis',technical:'/kis/technical',qgv:'/kis/qgv'});
// Routes that take ?symbol=<SYM>; the others take no query.
const BY_SYMBOL=Object.freeze(['chart','analysis','technical']);
const SCOPES=Object.freeze(['email','openid']);
const SYMBOL=/^[A-Z][A-Z0-9-]{0,9}$/;
// The two class shares (owner 2026-11-15): KIS names them BRK/B and BF/B (stored under the folder keys BRK_B / BF_B); the app
// asks for them as the Universe list's BRK-B / BF-B and shows them as the Universe codes. A file symbol is one of these or SYMBOL.
const CLASS_SHARES=Object.freeze({'BRK/B':Object.freeze({request:'BRK-B',code:'NYSE:BRK.B'}),'BF/B':Object.freeze({request:'BF-B',code:'NYSE:BF.B'})});
const fileSymbol=v=>typeof v==='string'&&(SYMBOL.test(v)||own(CLASS_SHARES,v));
// The request symbol of a file symbol (BRK/B → BRK-B; a plain symbol is itself), so a file is matched to the company asked for.
const requestSymbol=v=>own(CLASS_SHARES,v)?CLASS_SHARES[v].request:v;
// The Universe code of a class share's file symbol (BRK/B → NYSE:BRK.B); null for every other symbol.
const universeCode=v=>own(CLASS_SHARES,v)?CLASS_SHARES[v].code:null;
// The approved ETFs of the KIS collection (DC-52 stage 1): read like a company symbol; the Worker keeps the same list.
const ETFS=Object.freeze(['SPY','HYG','IEF','SMH','XLK','XLV','XLE','XLB','XLP','XLY','XLC','XLU','XLRE','XLF','XLI']);
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

// Expiry is explicit: null dates are an error unless the Worker reports NO_EXPIRY after checking GitHub Contents access.
const TOKEN_CODES=Object.freeze({UNSET:['TOKEN_UNSET','TOKEN_DATE_INVALID','TOKEN_DATE_IS_TOKEN'],EXPIRED:['TOKEN_EXPIRED'],
 REJECTED:['TOKEN_REJECTED','TOKEN_NO_ACCESS'],RATE_LIMITED:['UPSTREAM_RATE_LIMITED'],ERROR:['UPSTREAM_UNAVAILABLE','REPO_MOVED','TOKEN_STATUS_INVALID','TOKEN_EXPIRY_MISMATCH']});
const validateTokenStatus=wrap(c=>{
 need(c,['schema','state','code','expires_on','days_left'],'$');
 if(c.schema!==SCHEMA.STATUS)refuse('SCHEMA_VERSION','$.schema');
 const good=['NO_EXPIRY','OK','EXPIRING'].includes(c.state);
 if(good?c.code!==null:!own(TOKEN_CODES,c.state)||!TOKEN_CODES[c.state].includes(c.code))refuse('TOKEN_STATUS_INVALID','$.state');
 const undated=c.expires_on===null&&c.days_left===null;
 const dated=typeof c.expires_on==='string'&&DAY.test(c.expires_on)&&Number.isFinite(Date.parse(c.expires_on+'T00:00:00Z'))
  &&new Date(c.expires_on+'T00:00:00Z').toISOString().slice(0,10)===c.expires_on&&Number.isSafeInteger(c.days_left);
 if(c.state==='NO_EXPIRY'||c.state==='UNSET'){if(!undated)refuse('TOKEN_STATUS_INVALID','$.expires_on');}
 else if(!dated&&(!undated||good||c.state==='EXPIRED'))refuse('TOKEN_STATUS_INVALID','$.expires_on');
 // A dated GitHub 401 within two days retains the Worker's existing EXPIRED diagnosis.
 if(c.state==='OK'&&c.days_left<=14||c.state==='EXPIRING'&&(c.days_left<1||c.days_left>14)||c.state==='EXPIRED'&&c.days_left>2)refuse('TOKEN_STATUS_INVALID','$.days_left');
 return{schema:c.schema,state:c.state,code:c.code,expires_on:c.expires_on,days_left:c.days_left};
});
const TOKEN_WORDS=Object.freeze({TOKEN_UNSET:'비공개 저장소 읽기 설정 없음',TOKEN_DATE_INVALID:'읽기 토큰 만료 설정 오류',TOKEN_DATE_IS_TOKEN:'읽기 토큰 만료 설정 오류',
 TOKEN_EXPIRED:'비공개 저장소 읽기 토큰 만료',TOKEN_REJECTED:'비공개 저장소 읽기 토큰 거부',TOKEN_NO_ACCESS:'비공개 저장소 접근 권한 또는 상태 파일 확인 필요',
 UPSTREAM_RATE_LIMITED:'GitHub 요청 제한 · 잠시 뒤 다시 확인하세요',UPSTREAM_UNAVAILABLE:'GitHub 응답 없음 · 다시 확인하세요',REPO_MOVED:'저장소 이동 확인 필요',
 TOKEN_STATUS_INVALID:'비공개 토큰 상태 파일 확인 필요',TOKEN_EXPIRY_MISMATCH:'Worker와 저장소의 만료 설정이 일치하지 않습니다'});
function tokenStatusView(c){const r=validateTokenStatus(c);if(!r.ok)throw Error('TOKEN_STATUS_INVALID');const s=r.value;
 const text=s.state==='NO_EXPIRY'?'비공개 읽기 토큰 · 만료일 없음 · GitHub 저장소 읽기 확인됨'
  :s.state==='OK'?'비공개 읽기 토큰 · 만료일 '+s.expires_on+' · GitHub 저장소 읽기 확인됨'
  :s.state==='EXPIRING'?'비공개 읽기 토큰이 '+s.days_left+'일 뒤('+s.expires_on+') 만료됩니다 · 토큰을 바꿔 주세요':TOKEN_WORDS[s.code];
 return Object.freeze({state:s.state,text,blocked:!['NO_EXPIRY','OK','EXPIRING'].includes(s.state)});}

/* kis-bars/1 (#480 field table): header facts the screen shows, and the bars as decimal strings or null. */
const validateBars=wrap(c=>{const at='$';
 need(c,['schema','symbol','source','price_basis_date','collected_at','corrected_at','calendar','timezone','basis','dividend_adjustment','currency','bars','raw_bars','splits','confirmed_ranges','held_ranges','publication_scope'],at);
 if(c.schema!==SCHEMA.BARS)refuse('SCHEMA_VERSION',at+'.schema');
 if(c.publication_scope!=='OWNER_PRIVATE_ONLY')refuse('SCOPE',at+'.publication_scope');
 if(!fileSymbol(c.symbol))refuse('SYMBOL',at+'.symbol');
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
 if(!fileSymbol(m.symbol))refuse('SYMBOL',at+'.symbol');
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
/* KIS V stage 1 (owner 2026-11-15): the official method (calc 23.1) fed with KIS closes. The exact kis-qgv/1 fields are being agreed
   with Codex (#437); until then the #493 reader shape below is the contract, and QGV_FIELDS / QGV_OPTIONAL are the one place to
   adjust it. calc_version, price_basis_date and source (optional; KIS when absent) are what the panel shows. */
const QGV_FIELDS=Object.freeze(['schema','layer','calc_version','price_basis_date','calculated_at','financial_input_as_of','rows','coverage','rank','rank_reason','official_publication_replaced','TARGET_modified','population']);
const QGV_OPTIONAL=Object.freeze(['source','price_status','historical_pit_proven','display','stages','share_count_basis','identity_basis','total_policy','diagnostics']);
/* Codex #556 2abdd286 (mask_incomplete_totals): with total_policy THREE_AXES_REQUIRED_PRIVATE_OUTPUT every row is verification
   UNVERIFIED_REFERENCE, a row with any axis score missing has total null and total_reason THREE_AXES_REQUIRED, coverage.total and
   diagnostics {original_engine_total_count, suppressed_partial_totals} are given and coverage.engine_total_computed is gone. A file
   that contradicts this is refused. Without the policy (the earlier shape) a partial total is still never shown (qgvView). */
const TOTAL_POLICY='THREE_AXES_REQUIRED_PRIVATE_OUTPUT',THREE_AXES='THREE_AXES_REQUIRED';
const validateQgv=wrap(q=>{const at='$';
 need(q,QGV_FIELDS,at);
 if(typeof q.calc_version!=='string'||!q.calc_version)refuse('TYPE',at+'.calc_version');
 if(own(q,'source')&&(typeof q.source!=='string'||!q.source))refuse('TYPE',at+'.source');
 if(q.schema!==SCHEMA.QGV)refuse('SCHEMA_VERSION',at+'.schema');if(q.layer!=='OWNER_PRIVATE')refuse('ENUM',at+'.layer');
 if(q.rank!==null)refuse('RANK_NOT_ALLOWED',at+'.rank');if(q.official_publication_replaced!==false||q.TARGET_modified!==false)refuse('OFFICIAL_TOUCHED',at+'.official_publication_replaced');
 if(!isDay(q.price_basis_date))refuse('DATE',at+'.price_basis_date');if(!isTime(q.calculated_at))refuse('TIME',at+'.calculated_at');
 need(q.coverage,['codes','Q','G','V','QGV'],at+'.coverage');for(const k of['codes','Q','G','V','QGV'])if(!intOk(q.coverage[k])||q.coverage[k]>q.coverage.codes)refuse('COUNT_INVALID',at+'.coverage.'+k);
 if(!isObj(q.rows))refuse('TYPE',at+'.rows');
 for(const[k,r]of Object.entries(q.rows)){const p=at+'.rows.'+k;need(r,['axes','total'],p);need(r.axes,['Q','G','V'],p+'.axes');
  for(const ax of['Q','G','V']){const x=r.axes[ax];need(x,['score'],p+'.axes.'+ax);if(x.score!==null&&(typeof x.score!=='number'||!Number.isFinite(x.score)))refuse('SCORE_INVALID',p+'.axes.'+ax);}
  if(r.total!==null&&(typeof r.total!=='number'||!Number.isFinite(r.total)))refuse('SCORE_INVALID',p+'.total');
  const partial=['Q','G','V'].some(ax=>r.axes[ax].score===null);
  if(own(r,'verification')&&r.verification!==TIER.REFERENCE)refuse('ENUM',p+'.verification');
  if(own(r,'total_reason')&&r.total_reason===THREE_AXES&&r.total!==null)refuse('TOTAL_POLICY_VIOLATION',p+'.total');
  if(own(q,'total_policy')){if(r.verification!==TIER.REFERENCE)refuse('KEY_MISSING',p+'.verification');
   if(partial&&(r.total!==null||r.total_reason!==THREE_AXES))refuse('TOTAL_POLICY_VIOLATION',p+'.total');}}
 if(own(q,'total_policy')){if(q.total_policy!==TOTAL_POLICY)refuse('ENUM',at+'.total_policy');
  if(!intOk(q.coverage.total)||q.coverage.total>q.coverage.codes)refuse('COUNT_INVALID',at+'.coverage.total');
  if(own(q.coverage,'engine_total_computed'))refuse('COUNT_CONFLICT',at+'.coverage.engine_total_computed');
  need(q.diagnostics,['original_engine_total_count','suppressed_partial_totals'],at+'.diagnostics');
  if(q.diagnostics.original_engine_total_count!==null&&!intOk(q.diagnostics.original_engine_total_count))refuse('COUNT_INVALID',at+'.diagnostics.original_engine_total_count');
  if(!intOk(q.diagnostics.suppressed_partial_totals))refuse('COUNT_INVALID',at+'.diagnostics.suppressed_partial_totals');}
 return q;});

const REASON=Object.freeze({SPLIT_ADJUSTED_DISPLAY_ADAPTER_PENDING:'분할 반영 계열의 지표 어댑터 준비 중 (#498 이전 판 결과)',HELD_RANGE_IN_WINDOW:'보류 구간이 계산 창에 있음',
 CORPORATE_ACTION_IN_RAW_WINDOW:'원주가 창 안에 분할 사건',ACTION_BASIS_UNCONFIRMED:'분할 기준 미확인',IDENTITY_RANGE_UNCONFIRMED:'증권 신원 기간 미확인',
 VOLUME_SCOPE_UNCONFIRMED:'거래량 범위 미확인',INSUFFICIENT_HISTORY:'이력 부족',PRICE_NOT_AVAILABLE:'가격 없음',PRICE_BASIS_DATE_MISSING:'기준일 가격 없음',
 SOURCE_SECURITY_UNCONFIRMED:'공급처 증권 신원 미확인',PRICE_IDENTITY_CONFLICT:'가격 신원 충돌',PRICE_INPUT_HELD:'보류 구간 가격',SPLIT_AFTER_SHARE_COUNT:'주식수 기준일 뒤 분할',
 PAIRED_COMPARISON_POPULATION_NOT_ESTABLISHED:'같은 모집단·입력 비교가 확인되지 않아 순위 없음',PRICE_WINDOW_INCOMPLETE_OR_INVALID:'가격 창이 모자라거나 맞지 않음',
 RETURN_WINDOW_INCOMPLETE_OR_INVALID:'수익률 창이 모자라거나 맞지 않음',VOLUME_WINDOW_INCOMPLETE_OR_INVALID:'거래량 창이 모자라거나 맞지 않음',TRADE_SCOPE_UNCONFIRMED:'거래 범위 미확인',
 RAW_SPLIT_LIKE_JUMP_REVIEW_REQUIRED:'분할 같은 원주가 급변 · 검토 필요',PRIVATE_REFERENCE_NOT_OFFICIAL_RANK:'비공개 참고 결과라 순위 없음',WARMUP:'계산 시작 구간'});
const reasonText=c=>(typeof c==='string'&&own(REASON,c)?REASON[c]:'사유 코드 '+c);
// Codex #480: NORMAL is relative to the evaluation day, never a claim that the quote is current.
const STATUS_TEXT=Object.freeze({NORMAL:'평가일 기준 정상 · 현재 시세 최신 아님',STALE:'갱신 지연',MISSING:'자료 없음'});

// Public vs private basis day: the same day can be compared; a different day says so (owner 2026-11-05).
function basisCompare(publicDay,privateDay){
 if(!privateDay)return{same:false,text:'비공개 기준일 없음 · 공개와 비교하지 않음'};
 if(!publicDay)return{same:false,text:'공개 기준일 없음 · 비공개 기준일 '+privateDay+' · 직접 비교 제한'};
 return publicDay===privateDay?{same:true,text:'공개·비공개 기준일 같음 '+privateDay}:{same:false,text:'공개 기준일 '+publicDay+' · 비공개 기준일 '+privateDay+' · 기준일이 달라 직접 비교 제한'};}

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
/* The two private display tiers (owner 2026-11-15) come only from the producer's own display fields (Codex #556
   research/private_kis_reference.py reference_files / official_reference); nothing here derives a verification:
   - a chart / technical / measures file carries display {state AVAILABLE|WITHHELD, validation_tier UNVERIFIED_REFERENCE,
     label 검증 전(참고), official false, hold_reasons}; each of its metrics validation_tier VERIFIED (the adopted value is not
     null) or UNVERIFIED_REFERENCE, reference_value and reference_reasons. The qgv file carries display {validation_tier
     UNVERIFIED_REFERENCE, label, official false} and rank null.
   - 검증됨 only for a metric of tier VERIFIED with its adopted value; 검증 전(참고) for tier UNVERIFIED_REFERENCE with its
     reference_value, never put in the adopted value's place. WITHHELD: no reference value at all, one line naming the hold
     reason. A missing or unknown display or tier fails closed: no value and no 검증됨, the one line 검증 표시 없음. */
const TIER=Object.freeze({VERIFIED:'VERIFIED',REFERENCE:'UNVERIFIED_REFERENCE'});
const VERIFICATION=Object.freeze({VERIFIED:'검증됨',REFERENCE:'검증 전(참고)'});
const NO_DISPLAY='검증 표시 없음';
// The file's display: {state AVAILABLE | WITHHELD | UNKNOWN, holds (reason codes), line (the WITHHELD / UNKNOWN line), tag}.
// stateful = a file with display.state (chart / technical / measures); the qgv file has none and reads AVAILABLE when valid.
function displayOf(o,{stateful=true}={}){const d=isObj(o)&&isObj(o.display)?o.display:null;
 const ok=!!d&&d.validation_tier===TIER.REFERENCE&&d.official===false&&d.label===VERIFICATION.REFERENCE
  &&(!stateful||(['AVAILABLE','WITHHELD'].includes(d.state)&&Array.isArray(d.hold_reasons)&&d.hold_reasons.every(x=>typeof x==='string')));
 if(!ok)return Object.freeze({state:'UNKNOWN',holds:Object.freeze([]),line:NO_DISPLAY,tag:null});
 const state=stateful?d.state:'AVAILABLE',holds=stateful?Object.freeze([...d.hold_reasons]):Object.freeze([]);
 return Object.freeze({state,holds,line:state==='WITHHELD'?'보류 · '+(holds.map(reasonText).join(' · ')||'사유 없음'):null,tag:VERIFICATION.REFERENCE});}
const numeric=v=>(typeof v==='number'&&Number.isFinite(v))||isDec(v);
// One metric under its file's display: VERIFIED (adopted value), REFERENCE (reference value), WITHHELD (named once by the file's
// line) or HELD (one-line reason). A tier that does not match the values fails closed.
function metricTier(d,m,reasonsOf){
 if(d.state==='UNKNOWN')return Object.freeze({kind:'HELD',value:null,tag:null,text:NO_DISPLAY});
 if(m.validation_tier===TIER.VERIFIED&&m.value!==null&&numeric(m.value))return Object.freeze({kind:'VERIFIED',value:String(m.value),tag:VERIFICATION.VERIFIED});
 if(m.validation_tier===TIER.REFERENCE&&m.value===null){
  if(d.state==='WITHHELD')return Object.freeze({kind:'WITHHELD',value:null,tag:null,text:d.line});
  if(m.reference_value!==null&&m.reference_value!==undefined&&numeric(m.reference_value))return Object.freeze({kind:'REFERENCE',value:String(m.reference_value),tag:VERIFICATION.REFERENCE});
  const r=Array.isArray(m.reference_reasons)&&m.reference_reasons.length?m.reference_reasons:reasonsOf;
  return Object.freeze({kind:'HELD',value:null,tag:null,text:'미산출 · '+(r.map(reasonText).join(' · ')||'원시값 없음')});}
 return Object.freeze({kind:'HELD',value:null,tag:null,text:NO_DISPLAY});}
// A cell's metric rows from a validated analysis or measures file: [{id, label, kind, value, tag, text}], WITHHELD rows left out
// (the file's line names them once).
function tierRows(o,label,unit,order){const d=displayOf(o),ids=order||Object.keys(o.metrics).sort();
 const rows=ids.map(id=>{const m=o.metrics[id],t=metricTier(d,m,m.null_reasons);return Object.freeze({id,label:label(id),...t,value:t.value===null?null:t.value+unit(m)});});
 return Object.freeze({display:d,rows:Object.freeze(rows.filter(r=>r.kind!=='WITHHELD')),withheld:rows.filter(r=>r.kind==='WITHHELD').length});}
const analysisTiers=a=>tierRows(a,id=>id,()=>'');
const measuresTiers=m=>tierRows(m,id=>MEASURE_LABEL[id]||id,x=>own(UNIT_TEXT,x.unit)?' '+UNIT_TEXT[x.unit]:'',MEASURES.map(([id])=>id));
function qgvView(q,code){const c=q.coverage,n=c.codes;
 const lines=['Q 산출 '+c.Q+' / '+n,'G 산출 '+c.G+' / '+n,'V 산출 '+c.V+' / '+n,'Q·G·V 모두 '+c.QGV+' / '+n,...(intOk(c.total)?['총점 '+c.total+' / '+n]:[])];
 const dg=isObj(q.diagnostics)?q.diagnostics:null;
 const r=code&&own(q.rows,code)?q.rows[code]:null,st=code&&isObj(q.price_status)&&own(q.price_status,code)?q.price_status[code]:null;
 const axis=ax=>{const x=r.axes[ax];return x.score===null?ax+' 미산출'+(x.reason?' · '+reasonText(x.reason):''):ax+' '+(Math.round(x.score*10)/10);};
 return Object.freeze({coverage:Object.freeze(lines),price_basis_date:q.price_basis_date,calc_version:q.calc_version,source:own(q,'source')?q.source:'KIS',display:displayOf(q,{stateful:false}),
  // Codex #556 stage 1 facts for the 상태 box (counts as given, never recomputed); absent fields stay out.
  stages:isObj(q.stages)&&['price','raw_any','role_any'].every(k=>intOk(q.stages[k]))?'가격 반영 '+q.stages.price+' · V 원시값 '+q.stages.raw_any+' · V 요소 '+q.stages.role_any:null,
  bases:[q.share_count_basis,q.identity_basis].filter(x=>typeof x==='string'&&x).join(' · ')||null,
  diagnostics:dg&&intOk(dg.suppressed_partial_totals)?(intOk(dg.original_engine_total_count)?'엔진 총점 '+dg.original_engine_total_count+' · ':'')+'부분 총점 미표시 '+dg.suppressed_partial_totals:null,
  rank:'비공개 순위 없음 · '+reasonText(q.rank_reason),official:'공개 공식 순위·TARGET은 이 결과로 바뀌지 않음',
  row:r?Object.freeze({code,axes:Object.freeze(['Q','G','V'].map(axis)),// A total only with all three axes (any file shape); otherwise one short reason line.
   total:['Q','G','V'].some(ax=>r.axes[ax].score===null)||r.total_reason===THREE_AXES?'총점 미산출 · 세 축 필요':r.total===null?'총점 미산출':'QGV '+(Math.round(r.total*10)/10),
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
  if(!own(ROUTE,route))throw Error('ROUTE_UNKNOWN');const bySym=BY_SYMBOL.includes(route);if(bySym&&(typeof symbol!=='string'||!SYMBOL.test(symbol)))throw Error('REQUEST_INVALID');
  if(!connected())throw Error('AUTH_REQUIRED');const mine=epoch;
  const url=origin+ROUTE[route]+(bySym?'?symbol='+symbol:'');
  let res;try{res=await send(url,{method:'GET',headers:{Authorization:'Bearer '+token},credentials:'omit',cache:'no-store',referrerPolicy:'no-referrer',redirect:'error',signal});}
  catch(e){if(signal&&signal.aborted)throw Error('CANCELED');throw Error('UPSTREAM_UNAVAILABLE');}
  if(mine!==epoch)throw Error('CANCELED');
  let body=null;try{body=await res.json();}catch(_){body=null;}
  if(mine!==epoch)throw Error('CANCELED');
  if(res.status===401||res.status===403){const code=body&&body.error&&typeof body.error.code==='string'?body.error.code:'AUTH_FORBIDDEN';if(code==='AUTH_FORBIDDEN'||code==='ORIGIN_FORBIDDEN')drop();throw Error(code==='ORIGIN_FORBIDDEN'?'AUTH_FORBIDDEN':code);}
  if(!res.ok){const code=body&&body.error&&typeof body.error.code==='string'&&/^[A-Z][A-Z0-9_]{1,63}$/.test(body.error.code)?body.error.code:'UPSTREAM_UNAVAILABLE';throw Error(code);}
  if(!isObj(body))throw Error('KIS_SERIES_INVALID');return body;}
 return Object.freeze({state,connect,disconnect,get,subscribe:f=>{listeners.add(f);return()=>listeners.delete(f);}});}

return Object.freeze({SCHEMA,ROUTE,ADJUSTED_NOTE,BASIS_TEXT,SETTINGS_BY_BASIS,CLASS_SHARES,ETFS,QGV_FIELDS,QGV_OPTIONAL,TOTAL_POLICY,VERIFICATION,TIER,requestSymbol,universeCode,displayOf,analysisTiers,measuresTiers,validateTokenStatus,tokenStatusView,validateBars,validateAnalysis,validateMeasures,validateQgv,basisCompare,basisAgreement,barsMeta,analysisView,measuresView,qgvView,reasonText,createClient});
});
