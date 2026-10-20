/* S10 forward validation: public price-free ledger reader + device-only (RAM) forward return.
   The ledger holds no prices. Prices are read only after an explicit click through the existing private
   history Worker, kept in memory, and never stored or sent; computed returns are never stored or sent. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.ForwardValidation=api;})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
const FILENAME='forward-validation-ledger.json',KIND='FORWARD_VALIDATION_LEDGER',START='2026-10-19',STRATEGY='QGV_STANDARD_V1',VERSION='forward_validation/v1',V_VERSION='forward_validation/v1+dcf_v1_default',CALIBRATION='UNCALIBRATED',HOLDOUT='UNCONFIRMED_NOT_USED',V_REASON='V_REQUIRES_DEVICE_PRICES',V2_VERSION='forward_validation/v2',V2_STRATEGY='QGV_STANDARD_V2';
const IDS=['asml','lrcx','klac','tokyo_electron','hanmi','nvda','amd','avgo','qcom','intc','msft','googl','amzn','rtx','stry','etn','hubb','gev','rok'];
const UNITS={asml:900,lrcx:600,klac:550,tokyo_electron:500,hanmi:450,nvda:800,amd:500,avgo:500,qcom:400,intc:300,msft:700,googl:700,amzn:600,rtx:600,stry:550,etn:500,hubb:350,gev:300,rok:200};
const TOTAL=10000,AXIS_SIZE={Q:7,G:6},STATES=['LIVE','STALE','NOT_AVAILABLE'],COVERAGE=['READY','PARTIAL','BLOCKED'];
const REASONS=['SEC_QG_FACTORS_MISSING','SEC_QG_FACTORS_INVALID','SEC_QG_FACTORS_NOT_SAME_SESSION','SEC_QG_FACTORS_NOT_AVAILABLE','TARGET_CATALOG_MISSING','TARGET_CATALOG_INVALID'];
const SOURCES=['sec-qg-factors.json','actual-catalog.json'];
const HOLIDAYS=new Set(['2026-01-01','2026-01-19','2026-02-16','2026-04-03','2026-05-25','2026-06-19','2026-07-03','2026-09-07','2026-11-26','2026-12-25','2027-01-01','2027-01-18','2027-02-15','2027-03-26','2027-05-31','2027-06-18','2027-07-05','2027-09-06','2027-11-25','2027-12-24','2028-01-17','2028-02-21','2028-04-14','2028-05-29','2028-06-19','2028-07-04','2028-09-04','2028-11-23','2028-12-25']);
const CALENDAR_END='2028-12-31',MAX=2*1024*1024,HISTORY_KEY='investment.web.v1.private-history-origin';
const BENCHMARK={state:'NOT_AVAILABLE',reason:'SP500_NOT_IN_PRIVATE_HISTORY_WORKER'},BASIS='ADJUSTED_CLOSE_LOCAL_CURRENCY_NO_FX';
/* Observation basis of a v2 record (owner instruction 2026-10-16; Python forward_ledger.observation_basis / _basis).
   T-COV: Q and G each >= 454 of 504 (90 %), T-FRESH: 7 days from each row's own acquisition (owner decisions 2026-10-15). */
const UNIVERSE=504,PRIMARY_MIN=454,FRESH_DAYS=7,BASIS_KEYS=['calc_version','q_scored','g_scored','population','acquired','evaluation','segment'];
const EVAL_REASONS=['RECORD_NOT_AVAILABLE','Q_BELOW_454','G_BELOW_454','CALC_VERSION_MISSING','CALC_VERSION_MIXED','ROW_DATA_STALE','POPULATION_MISMATCH','BASIS_NOT_COMPUTED'];
const NO_SEGMENT='NONE',LEGACY_SEGMENT='LEGACY',CALC_RE=/^[A-Za-z0-9][A-Za-z0-9._:/+-]{0,63}$/;
const STOP=new Set(['RATE_LIMITED','RATE_LIMIT_UNAVAILABLE','AUTH_REQUIRED','AUTH_FORBIDDEN','AUTH_UNAVAILABLE','ORIGIN_FORBIDDEN','CONFIG_UNAVAILABLE','CANCELED']);
function need(v){if(!v)throw Error('FORWARD_LEDGER_INVALID');}
const object=v=>v!==null&&typeof v==='object'&&!Array.isArray(v),finite=v=>typeof v==='number'&&Number.isFinite(v),hash=v=>typeof v==='string'&&/^[0-9a-f]{64}$/.test(v);
function keys(v,ks){need(object(v)&&Object.keys(v).length===ks.length&&ks.every(k=>Object.hasOwn(v,k)));}
function clock(v){need(typeof v==='string'&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$/.test(v));const n=Date.parse(v);need(Number.isFinite(n));return n;}
function day(v){need(typeof v==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&new Date(v+'T00:00:00Z').toISOString().slice(0,10)===v);return v;}
const ET=new Intl.DateTimeFormat('en-CA',{timeZone:'America/New_York',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'});
function eastern(ms){const p=Object.fromEntries(ET.formatToParts(ms).map(x=>[x.type,x.value]));return{date:p.year+'-'+p.month+'-'+p.day,minutes:Number(p.hour)*60+Number(p.minute)};}
function sessionDay(d){need(d<=CALENDAR_END);const w=new Date(d+'T00:00:00Z').getUTCDay();return w>0&&w<6&&!HOLIDAYS.has(d);}
function axis(v,name,companyState,size=AXIS_SIZE){keys(v,['score','coverage','missing_factor_count']);need(v.score===null||finite(v.score)&&v.score>=0&&v.score<=100);need(COVERAGE.includes(v.coverage)&&(v.score===null)===(v.coverage==='BLOCKED'));const n=v.missing_factor_count;need(Number.isInteger(n)&&n>=0&&n<=size[name]&&(v.coverage!=='READY'||n===0));need(companyState!=='NOT_AVAILABLE'||v.score===null);}
function basis(b,r,d,created){
 keys(b,BASIS_KEYS);const e=b.evaluation;keys(e,['eligible','status','reasons']);const rs=e.reasons;
 need(Array.isArray(rs)&&rs.every(x=>typeof x==='string')&&JSON.stringify(rs)===JSON.stringify(EVAL_REASONS.filter(x=>rs.includes(x))));
 need(['PRIMARY','PREPARATORY'].includes(e.status)&&typeof e.eligible==='boolean'&&e.eligible===(e.status==='PRIMARY')&&(e.status==='PRIMARY')===(rs.length===0));
 if(r.state!=='RECORDED'){need(b.calc_version===null&&b.q_scored===null&&b.g_scored===null&&b.population===null&&b.acquired===null&&b.segment===null&&rs.length===1&&rs[0]==='RECORD_NOT_AVAILABLE');return;}
 // Fail-safe basis (Python unknown_basis): the row is kept as PREPARATORY in the NONE segment.
 if(rs.includes('BASIS_NOT_COMPUTED')){need(b.calc_version===null&&b.q_scored===null&&b.g_scored===null&&b.population===null&&b.acquired===null&&b.segment===NO_SEGMENT&&rs.length===1);return;}
 need(!rs.includes('RECORD_NOT_AVAILABLE'));const v=b.calc_version;need(v===null||typeof v==='string'&&CALC_RE.test(v));need(b.segment===(v===null?NO_SEGMENT:v));
 for(const[k,c]of[['q_scored','Q_BELOW_454'],['g_scored','G_BELOW_454']]){const n=b[k];need(Number.isInteger(n)&&n>=0&&n<=UNIVERSE&&rs.includes(c)===(n<PRIMARY_MIN));}
 need(rs.includes('CALC_VERSION_MISSING')===(v===null)&&(v!==null||!rs.includes('CALC_VERSION_MIXED')));
 keys(b.population,['n','id']);need(Number.isInteger(b.population.n)&&b.population.n>=0&&b.population.n<=UNIVERSE&&typeof b.population.id==='string'&&/^[0-9a-f]{16}$/.test(b.population.id));
 const a=b.acquired;if(a!==null){need(Array.isArray(a)&&a.length===2);day(a[0]);day(a[1]);need(a[0]<=a[1]&&a[1]<=new Date(created).toISOString().slice(0,10));}
 const stale=a===null||(Date.parse(d+'T00:00:00Z')-Date.parse(a[0]+'T00:00:00Z'))/86400000>FRESH_DAYS;need(rs.includes('ROW_DATA_STALE')===stale);}
function record(r,previous,cut,version=VERSION){
 const isV2=version===V2_VERSION,sources=isV2?['sec-qgv2.json','actual-catalog.json']:SOURCES,prefix=isV2?'SEC_QGV2':'SEC_QG_FACTORS',reasons=isV2?REASONS.map(r=>r.replace('SEC_QG_FACTORS','SEC_QGV2')):REASONS;
 const rk=['date','version','strategy','calibration','state','reason_codes','target','qg_as_of','qg_screen_state','companies','source_sha256','created_at'];for(const k of ['reference_sources','basis'])if(isV2&&Object.hasOwn(r,k))rk.push(k);keys(r,rk);
 const d=day(r.date);need(d>=START&&sessionDay(d)&&(previous===null||d>previous));
 const created=clock(r.created_at),local=eastern(created);need(created<=cut&&local.date===d&&local.minutes>=16*60);
 need(r.version===version&&r.strategy===(isV2?V2_STRATEGY:STRATEGY)&&r.calibration===CALIBRATION&&['RECORDED','NOT_AVAILABLE'].includes(r.state));
 need(Array.isArray(r.reason_codes)&&r.reason_codes.every(c=>reasons.includes(c))&&new Set(r.reason_codes).size===r.reason_codes.length);
 keys(r.source_sha256,sources);for(const v of Object.values(r.source_sha256))need(v===null||hash(v));
 if(Object.hasOwn(r,'basis'))basis(r.basis,r,d,created);
 if(r.target!==null){keys(r.target,['portfolio_id','version','root_sha256','total_units','weights_units']);need(r.target.portfolio_id==='TARGET'&&r.target.version==='v0'&&hash(r.target.root_sha256)&&r.target.total_units===TOTAL);keys(r.target.weights_units,IDS);need(IDS.every(c=>r.target.weights_units[c]===UNITS[c])&&r.source_sha256['actual-catalog.json']!==null);}
 if(r.state==='RECORDED'){
  need(r.reason_codes.length===0&&r.target!==null&&Object.values(r.source_sha256).every(v=>v!==null));
  const at=clock(r.qg_as_of);need(eastern(at).date===d&&at<=created&&['LIVE','STALE'].includes(r.qg_screen_state));
  keys(r.companies,IDS);const states=[];
  for(const row of Object.values(r.companies)){keys(row,['state','Q','G']);need(STATES.includes(row.state));states.push(row.state);axis(row.Q,'Q',row.state,isV2?{Q:5,G:5}:AXIS_SIZE);axis(row.G,'G',row.state,isV2?{Q:5,G:5}:AXIS_SIZE);}
  need(r.qg_screen_state===(states.includes('LIVE')?'LIVE':states.includes('STALE')?'STALE':null));
  if(Object.hasOwn(r,'reference_sources')){keys(r.reference_sources,['hanmi']);const ref=r.reference_sources.hanmi;keys(ref,['kind','file','sha256','as_of','comparison_basis','reference_only']);need(ref.kind==='DART'&&ref.file==='dart-financials.json'&&hash(ref.sha256)&&ref.reference_only===true&&ref.comparison_basis==='US_UNIVERSE_504_GENERAL');const stamp=clock(ref.as_of);need(eastern(stamp).date===d&&stamp<=created&&['LIVE','STALE'].includes(r.companies.hanmi.state));}
 }else{
  need(!Object.hasOwn(r,'reference_sources'));
  need(r.reason_codes.length>0&&r.companies===null&&r.qg_as_of===null&&r.qg_screen_state===null);
  need((r.reason_codes.includes('TARGET_CATALOG_MISSING')||r.reason_codes.includes('TARGET_CATALOG_INVALID'))===(r.target===null));
  need(r.reason_codes.includes(prefix+'_MISSING')===(r.source_sha256[sources[0]]===null));
  need(r.reason_codes.includes('TARGET_CATALOG_MISSING')===(r.source_sha256['actual-catalog.json']===null));
 }
 return d;}
function validate(p){
 keys(p,['schema_version','kind','start_date','status','as_of','strategy','calibration','holdout','price_free','target','versions','version_status']);
 need([1,2].includes(p.schema_version)&&p.kind===KIND&&p.start_date===START&&p.strategy===(p.schema_version===2?V2_STRATEGY:STRATEGY)&&p.calibration===CALIBRATION&&p.holdout===HOLDOUT&&p.price_free===true);
 keys(p.target,['portfolio_id','version']);need(p.target.portfolio_id==='TARGET'&&p.target.version==='v0');
 const cut=clock(p.as_of),versions=p.schema_version===2?[VERSION,V_VERSION,V2_VERSION]:[VERSION,V_VERSION];keys(p.versions,versions);const rows=p.versions[VERSION];
 need(Array.isArray(rows)&&rows.length<=5000&&Array.isArray(p.versions[V_VERSION])&&p.versions[V_VERSION].length===0);
 let previous=null;for(const version of versions.filter(v=>v!==V_VERSION)){need(Array.isArray(p.versions[version])&&p.versions[version].length<=5000);previous=null;let withBasis=false;for(const r of p.versions[version]){previous=record(r,previous,cut,version);need(!withBasis||Object.hasOwn(r,'basis'));withBasis=withBasis||Object.hasOwn(r,'basis');}}
 const today=eastern(cut).date,status=today>=START||rows.length?'ACTIVE':'NOT_STARTED';need(p.status===status);
 keys(p.version_status,versions);const a=p.version_status[VERSION],b=p.version_status[V_VERSION];
 keys(a,['state','v_included','reason_codes']);keys(b,['state','v_included','reason_codes']);
 need(a.state===status&&a.v_included===false&&Array.isArray(a.reason_codes)&&a.reason_codes.length===0);
 need(b.state==='NOT_AVAILABLE'&&b.v_included===true&&Array.isArray(b.reason_codes)&&b.reason_codes.length===1&&b.reason_codes[0]===V_REASON);
 if(p.schema_version===2){const c=p.version_status[V2_VERSION];keys(c,['state','v_included','reason_codes']);need(c.state===status&&c.v_included===false&&Array.isArray(c.reason_codes)&&c.reason_codes.length===0);}need(previous===null||previous<=today);
 return p;}
async function load(view){
 const control=new view.AbortController(),timer=setTimeout(()=>control.abort(),20000);
 try{const r=await view.fetch(FILENAME,{cache:'no-store',credentials:'omit',referrerPolicy:'no-referrer',redirect:'error',signal:control.signal});
  if(r.status===404)return{state:'NOT_AVAILABLE',reason:'LEDGER_NOT_PUBLISHED'};if(!r.ok)return{state:'NOT_AVAILABLE',reason:'LEDGER_UNREACHABLE'};
  const text=await r.text();if(new TextEncoder().encode(text).length>MAX)return{state:'NOT_AVAILABLE',reason:'LEDGER_INVALID'};
  try{return{state:'LOADED',ledger:validate(JSON.parse(text))};}catch(_){return{state:'NOT_AVAILABLE',reason:'LEDGER_INVALID'};}
 }catch(_){return{state:'NOT_AVAILABLE',reason:'LEDGER_UNREACHABLE'};}finally{clearTimeout(timer);}}
// ---- Python reference: validation/forward_device_reference.py (same order of operations) ----
const positive=v=>finite(v)&&v>0;
function instrumentReturn(series,start,bound=null){
 if(series===null||series===undefined)return{state:'NOT_AVAILABLE',reason:'HISTORY_NOT_LOADED'};
 if(typeof series==='string')return{state:'NOT_AVAILABLE',reason:series};
 const usable=series.filter(b=>b.session_status!=='IN_PROGRESS'&&(bound===null||b.session_date<=bound)),after=usable.filter(b=>b.session_date>=start);
 if(!after.length)return{state:'NOT_AVAILABLE',reason:'NO_SESSION_ON_OR_AFTER_START'};
 const base=after[0],end=usable.at(-1);
 if(base===end)return{state:'NOT_AVAILABLE',reason:'NO_SESSION_AFTER_BASE'};
 if(!positive(base.adjusted_close))return{state:'NOT_AVAILABLE',reason:'BASE_ADJUSTED_CLOSE_MISSING'};
 if(!positive(end.adjusted_close))return{state:'NOT_AVAILABLE',reason:'END_ADJUSTED_CLOSE_MISSING'};
 return{state:'AVAILABLE',reason:null,base_date:base.session_date,end_date:end.session_date,return:end.adjusted_close/base.adjusted_close-1};}
// end_date (optional): a closed evaluation segment ends on its last primary record; bars after it are not used.
function forwardReturn({start_date,weights_units,series,end_date=null}){
 const ids=Object.keys(weights_units).sort(),instruments={};for(const id of ids)instruments[id]=instrumentReturn(Object.hasOwn(series,id)?series[id]:null,start_date,end_date);
 const missing=ids.filter(id=>instruments[id].state!=='AVAILABLE');
 const out={basis:BASIS,start_date,...(end_date===null?{}:{end_bound:end_date}),instruments,benchmark:{...BENCHMARK},missing_count:missing.length};
 if(missing.length)return{...out,state:'NOT_AVAILABLE',reason:'INSTRUMENTS_MISSING',portfolio_return:null,end_date_min:null,end_date_max:null};
 let total=0,acc=0;for(const id of ids){acc+=weights_units[id]*instruments[id].return;total+=weights_units[id];}
 const ends=ids.map(id=>instruments[id].end_date).sort();
 return{...out,state:'AVAILABLE',reason:null,portfolio_return:acc/total,end_date_min:ends[0],end_date_max:ends.at(-1)};}
function qgSummary(r){
 if(r.state!=='RECORDED')return{date:r.date,state:'NOT_AVAILABLE',reason_codes:[...r.reason_codes]};
 const w=r.target.weights_units,c=r.companies,out={date:r.date,state:'RECORDED',reason_codes:[],companies:Object.keys(c).length};
 for(const a of ['Q','G']){let units=0,acc=0,count=0;for(const id of Object.keys(c).sort()){const s=c[id][a].score;if(s===null)continue;units+=w[id];acc+=w[id]*s;count++;}out[a]={available:count,covered_units:units,weighted_mean:units===0?null:acc/units};}
 return out;}
/* Evaluation view (Python forward_ledger.row_evaluation / evaluation_segments). PREPARATORY rows are kept and shown but are
   not primary evaluation targets; LEGACY rows were recorded before the basis existed (own segment, kept as observed). A change
   of segment (calc_version) starts a new segment: segments are shown separately and never chained. */
function rowEvaluation(r){
 if(r.state!=='RECORDED')return{status:'NOT_AVAILABLE',segment:null,reasons:[...r.reason_codes]};
 if(!Object.hasOwn(r,'basis'))return{status:'LEGACY',segment:LEGACY_SEGMENT,reasons:[]};
 return{status:r.basis.evaluation.status,segment:r.basis.segment,reasons:[...r.basis.evaluation.reasons]};}
function segments(rows){
 const out=[];for(const r of rows){const ev=rowEvaluation(r);if(ev.status==='NOT_AVAILABLE')continue;
  if(!out.length||out.at(-1).segment!==ev.segment)out.push({segment:ev.segment,first_date:r.date,last_date:r.date,eligible_dates:[],preparatory_dates:[]});
  const s=out.at(-1);s.last_date=r.date;(ev.status==='PREPARATORY'?s.preparatory_dates:s.eligible_dates).push(r.date);}
 return out;}
// ---- device RAM loading through the existing private history Worker (explicit click only) ----
function localDate(ms,timezone){const p=Object.fromEntries(new Intl.DateTimeFormat('en-CA',{timeZone:timezone,year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(ms).map(x=>[x.type,x.value]));return p.year+'-'+p.month+'-'+p.day;}
function seriesFromHistory(data){return data.bars.map(b=>({session_date:b.session_date||localDate(b.timestamp*1000,data.timezone),adjusted_close:b.adjusted_close,session_status:b.session_status}));}
function rangeFor(start,today){const days=(Date.parse(today+'T00:00:00Z')-Date.parse(start+'T00:00:00Z'))/86400000;return days<=25?'1mo':days<=85?'3mo':days<=175?'6mo':days<=355?'1y':days<=720?'2y':'5y';}
const active=new Set();
function clearPrices(state){state.revision++;if(state.controller){state.controller.abort();state.controller=null;}state.series=new Map();state.result=null;state.segmentResults=null;state.busy=false;state.message='';}
function dispose(state){clearPrices(state);state.disposed=true;if(state.unsubscribe)state.unsubscribe();if(state.view&&state.pagehide)state.view.removeEventListener('pagehide',state.pagehide);active.delete(state);}
function disposeAll(){for(const s of [...active])dispose(s);}
function mount(host,options={}){
 if(!host)return null;const doc=host.ownerDocument,view=doc.defaultView,en=options.locale==='en-US',x=(ko,e)=>en?e:ko,config=options.config||{};
 const el=(tag,text,attrs={})=>{const n=doc.createElement(tag);if(text!==undefined)n.textContent=text;for(const[k,v]of Object.entries(attrs))n.setAttribute(k,v);return n;};
 const state={host,view,series:new Map(),result:null,busy:false,revision:0,message:'',controller:null,ledger:null,disposed:false};active.add(state);
 state.pagehide=()=>dispose(state);view.addEventListener('pagehide',state.pagehide);
 // Optional layout hosts (Lab 9.2.2 / 9.2.3): the price block and the evaluation segments render there instead of inside
 // the ledger card. Same elements, attributes and states; without hosts the card is unchanged.
 const hosts=options.hosts||{},hosted=!!(hosts.outcome||hosts.eligibility),H2=hosted?'h4':'h2',H3=hosted?'h5':'h3';
 const section=el('section',undefined,{class:'card','data-forward-validation':''});
 section.append(el(H2,x('전진 검증 기록 · 가격 미포함','Forward validation ledger · price-free')));
 const badges=el('div',undefined,{class:'chips','data-forward-badges':''});badges.append(el('span',STRATEGY,{class:'badge'}),el('span',VERSION+' · '+CALIBRATION,{class:'badge'}),el('span','Holdout UNCONFIRMED · '+x('사용 금지','Do not use'),{class:'badge','data-forward-holdout':''}));
 const facts=el('dl',undefined,{class:'kv'}),summary=el('div',undefined,{'data-forward-summary':''}),prices=el('div',undefined,{'data-forward-prices':''});
 const eligibility=hosts.eligibility?el('div',undefined,{'data-forward-eligibility':''}):null;
 section.append(badges,facts,summary);if(hosts.outcome)hosts.outcome.replaceChildren(prices);else section.append(prices);
 if(eligibility)hosts.eligibility.replaceChildren(eligibility);host.replaceChildren(section);
 const rule=()=>el('p',x('주 평가는 Q·G 각 454개 이상, 계산 버전 일치, 행별 실제 수집 시각 7일 이내를 모두 충족한 기록만 씁니다. 나머지는 "준비 관측·주 평가 대상 아님"으로 사유와 함께 보존합니다.','Primary evaluation uses only records with Q and G each at least 454, one consistent calc version and every row acquired within 7 days. Other records are kept as "preparatory observation · not a primary evaluation target" with their reasons.'),{class:'small','data-forward-evaluation-rule':''});
 const eligibilityEmpty=text=>{if(eligibility)eligibility.append(el('p',text,{class:'empty','data-forward-eligibility-empty':''}),rule());};
 const fact=(k,v,attr)=>{facts.append(el('dt',k),el('dd',v,attr?{[attr]:''}:{}));};
 const pct=v=>v===null?'NOT_AVAILABLE':(v*100).toFixed(2)+'%',num=v=>v===null?'NOT_AVAILABLE':v.toFixed(2);
 const PREP=x('준비 관측·주 평가 대상 아님','Preparatory observation · not a primary evaluation target');
 function evaluationLabel(r){
  if(r.version!==V2_VERSION)return{code:'COMPARISON',text:x('비교용 · 평가 대상 아님','Comparison only · not evaluated')};
  if(Object.hasOwn(r,'basis')){const b=r.basis,e=b.evaluation;
   if(r.state!=='RECORDED')return{code:'PREPARATORY',text:PREP+' · '+e.reasons.join(', ')};
   const counts=b.population===null?'':' · Q '+b.q_scored+' · G '+b.g_scored+' · '+x('모집단 ','population ')+b.population.n+' ('+b.population.id+')'+(b.acquired?' · '+x('수집 ','acquired ')+b.acquired[0]+'~'+b.acquired[1]:'');
   return e.status==='PRIMARY'?{code:'PRIMARY',text:x('주 평가','Primary')+' · '+b.segment+counts}:{code:'PREPARATORY',text:PREP+' · '+e.reasons.join(', ')+' · '+b.segment+counts};}
  if(r.state!=='RECORDED')return{code:'NOT_AVAILABLE',text:'—'};
  return{code:'LEGACY',text:x('관측 기준 미기록(이전 기록, 별도 구간)','Basis not recorded (earlier record, own segment)')};}
 function paintLedger(res){
  facts.replaceChildren();summary.replaceChildren();if(eligibility)eligibility.replaceChildren();
  if(res.state!=='LOADED'){eligibilityEmpty('NOT_AVAILABLE · '+res.reason);fact(x('상태','Status'),'NOT_AVAILABLE · '+res.reason,'data-forward-status');fact(x('시작일','Start date'),START,'data-forward-start');fact(x('기록 수','Records'),'0','data-forward-count');fact(x('전략 · 버전','Strategy · version'),STRATEGY+' · '+VERSION);return;}
  const p=res.ledger,primary=p.schema_version===2?V2_VERSION:VERSION,rows=p.versions[primary];
  fact(x('상태','Status'),p.status,'data-forward-status');fact(x('시작일','Start date'),p.start_date,'data-forward-start');fact(x('기록 수','Records'),String(rows.length),'data-forward-count');
  fact(x('전략 · 버전','Strategy · version'),p.strategy+' · '+primary+' · '+p.calibration,'data-forward-strategy');
  fact(x('V 포함 버전','V-bearing version'),V_VERSION+' · NOT_AVAILABLE · '+V_REASON+' · '+x('기록 0건','0 records'),'data-forward-v-version');
  fact(x('대상 포트폴리오','Target portfolio'),'TARGET v0 · 19');fact(x('기준 시각','As of'),p.as_of);
  summary.append(el(H3,x('일별 Q·G 요약 (V 없음)','Daily Q·G summary (no V)')));
  if(!rows.length){eligibilityEmpty(p.status+' · '+x('평가할 기록이 없습니다.','No record to evaluate.'));summary.append(el('p',p.status==='NOT_STARTED'?x('NOT_STARTED · 시작일 전이라 기록이 없습니다.','NOT_STARTED · No records before the start date.'):x('NOT_AVAILABLE · 아직 완료된 미국 거래일 기록이 없습니다.','NOT_AVAILABLE · No completed US session has been recorded yet.'),{class:'empty','data-forward-empty':''}));return;}
  const wrap=el('div',undefined,{class:'table-wrap'}),table=el('table',undefined,{'data-forward-days':''}),head=el('tr');
  for(const h of [x('날짜','Date'),x('상태','State'),x('Q 가용','Q available'),x('Q 가중평균','Q weighted mean'),x('G 가용','G available'),x('G 가중평균','G weighted mean'),x('평가 구분','Evaluation')])head.append(el('th',h,{scope:'col'}));
  const thead=el('thead');thead.append(head);const body=el('tbody');
  const displayRows=[...rows,...(p.schema_version===2?p.versions[VERSION]:[])].sort((a,b)=>b.date.localeCompare(a.date)||(a.version===V2_VERSION?-1:1));
  for(const r of displayRows){const s=qgSummary(r),tr=el('tr',undefined,{'data-forward-day':r.date});
   if(s.state!=='RECORDED')tr.append(el('td',r.date+' · '+(r.version===V2_VERSION?x('v2 기본','v2 default'):x('v1 비교용','v1 comparison'))),el('td','NOT_AVAILABLE · '+s.reason_codes.join(', ')),el('td','—'),el('td','—'),el('td','—'),el('td','—'));
   else tr.append(el('td',r.date+' · '+(r.version===V2_VERSION?x('v2 기본','v2 default'):x('v1 비교용','v1 comparison'))),el('td',r.qg_screen_state+(r.reference_sources?x(' · DART 참고',' · DART reference'):'')),el('td',s.Q.available+'/'+s.companies),el('td',num(s.Q.weighted_mean)),el('td',s.G.available+'/'+s.companies),el('td',num(s.G.weighted_mean)));
   const ev=evaluationLabel(r);tr.setAttribute('data-forward-evaluation',ev.code);tr.append(el('td',ev.text));
   body.append(tr);}
  table.append(thead,body);wrap.append(table);summary.append(wrap);
  if(p.schema_version===2&&rows.some(r=>Object.hasOwn(r,'basis'))){
   // Evaluation segments (calc_version): each shown on its own, never chained into one series.
   const segWrap=el('div',undefined,{class:'table-wrap'}),segTable=el('table',undefined,{'data-forward-segments':''}),segHead=el('tr');
   for(const h of [x('평가 구간(계산 버전)','Segment (calc version)'),x('기간','Period'),x('주 평가 기록','Primary records'),x('준비 관측','Preparatory')])segHead.append(el('th',h,{scope:'col'}));
   const segThead=el('thead');segThead.append(segHead);const segBody=el('tbody');
   for(const s of segments(rows)){const tr=el('tr',undefined,{'data-forward-segment':s.segment});tr.append(el('td',s.segment),el('td',s.first_date+' → '+s.last_date),el('td',String(s.eligible_dates.length)),el('td',String(s.preparatory_dates.length)));segBody.append(tr);}
   segTable.append(segThead,segBody);segWrap.append(segTable);
   (eligibility||summary).append(el(H3,x('평가 구간 · 서로 다른 계산 버전은 잇지 않음','Evaluation segments · different calc versions are never chained')),segWrap,rule());}
  else eligibilityEmpty(x('관측 기준이 기록된 행이 없어 평가 구간이 없습니다.','No record carries an observation basis, so there is no evaluation segment.'));
  summary.append(el('p',x('가중평균은 점수가 있는 종목만 TARGET v0 비중으로 평균한 화면 표시값이며 저장하지 않습니다. 보정 전(UNCALIBRATED).','Weighted means average only companies with a score using TARGET v0 weights; display only, never stored. UNCALIBRATED.'),{class:'small'}));
 }
 // Price readiness mirrors the private history chart: feature ON, approved Worker origin saved on this device, Google session connected.
 const status=el('p','',{role:'status','data-forward-price-status':''}),load_=el('button',x('TARGET 가격 불러오기 (RAM)','Load TARGET prices (RAM)'),{type:'button','data-forward-action':'load'}),clear=el('button',x('가격 지우기','Clear prices'),{type:'button','data-forward-action':'clear'}),results=el('div',undefined,{'data-forward-results':''});
 prices.append(el(H3,x('TARGET v0 전진 수익률 · 기기 RAM 전용','TARGET v0 forward return · device RAM only')),el('p',x('가격은 누를 때만 비공개 Worker에서 읽고 메모리에만 둡니다. 계산한 수익률은 저장·전송하지 않습니다. 현지통화 수정종가 기준이며 환율은 적용하지 않습니다.','Prices are read from the private Worker only when you click and stay in memory. Computed returns are never stored or sent. Adjusted close in local currency; FX is not applied.'),{class:'small'}),status,load_,clear,results);
 function storedOrigin(){try{const v=view.localStorage.getItem(HISTORY_KEY);return v&&view.PrivateHistory?view.PrivateHistory.parseWorkerOrigin(v):'';}catch(_){return null;}}
 function readiness(){
  if(!state.ledger)return'LEDGER_NOT_AVAILABLE';if(state.ledger.status!=='ACTIVE')return'NOT_STARTED';
  if(config.privateHistoryEnabled!==true||!view.PrivateHistory)return'OFF';
  const origin=storedOrigin();if(origin===null)return'REQUEST_INVALID';if(!origin||origin!==config.privateHistoryWorkerOrigin)return'ORIGIN_UNAPPROVED';
  if(!state.session||!state.session.state().connected)return'AUTH_REQUIRED';return'READY';}
 function weights(){const rows=state.ledger?state.ledger.versions[VERSION]:[];const r=[...rows].reverse().find(r=>r.target);return r?r.target.weights_units:{...UNITS};}
 function paintPrices(){
  if(state.disposed||!host.isConnected)return;const code=readiness();load_.disabled=state.busy||code!=='READY';clear.disabled=state.busy;
  if(!state.busy){status.dataset.code=code;status.textContent=(code==='OFF'?x('OFF · 가격 호출 없음','OFF · No price requests'):code)+(state.message?' · '+state.message:'');}
  results.replaceChildren();const r=state.result;
  const bench=el('p','S&P 500 · '+BENCHMARK.state+' · '+BENCHMARK.reason+' · '+x('Worker는 TARGET 19종목만 제공합니다.','The Worker serves only the 19 TARGET symbols.'),{'data-forward-benchmark':BENCHMARK.state});
  if(!r){results.append(el('p',x('TARGET v0 수익률 · NOT_AVAILABLE · 가격을 불러오지 않았습니다.','TARGET v0 return · NOT_AVAILABLE · Prices not loaded.'),{'data-forward-portfolio':'NOT_AVAILABLE'}),bench);return;}
  results.append(el('p',r.state==='AVAILABLE'?x('TARGET v0 수익률 ','TARGET v0 return ')+r.start_date+' → '+r.end_date_max+' · '+pct(r.portfolio_return)+' · '+BASIS:r.reason==='NO_PRIMARY_RECORD'?x('TARGET v0 수익률 · NOT_AVAILABLE · 현재 구간에 주 평가 기록이 없습니다(준비 관측만 있음).','TARGET v0 return · NOT_AVAILABLE · The current segment has no primary record (preparatory only).'):x('TARGET v0 수익률 · NOT_AVAILABLE · ','TARGET v0 return · NOT_AVAILABLE · ')+r.reason+' · '+r.missing_count+'/'+Object.keys(r.instruments).length,{'data-forward-portfolio':r.state}),bench);
  for(const s of state.segmentResults||[]){const v=s.result;
   results.append(el('p',x('구간 ','Segment ')+s.segment+' · '+(s.start||'—')+' → '+(s.end||x('현재','current'))+' · '+(v===null?x('주 평가 기록 없음','no primary record'):v.state==='AVAILABLE'?pct(v.portfolio_return):'NOT_AVAILABLE · '+v.reason),{'data-forward-segment-return':s.segment}));}
  const wrap=el('div',undefined,{class:'table-wrap'}),table=el('table',undefined,{'data-forward-instruments':''}),head=el('tr');for(const h of [x('종목','Company'),x('기준일','Base'),x('종료일','End'),x('수익률','Return')])head.append(el('th',h,{scope:'col'}));
  const thead=el('thead');thead.append(head);const body=el('tbody');
  for(const[id,v]of Object.entries(r.instruments)){const tr=el('tr',undefined,{'data-forward-instrument':id});tr.append(el('td',id.toUpperCase()),el('td',v.base_date||'—'),el('td',v.end_date||'—'),el('td',v.state==='AVAILABLE'?pct(v.return):'NOT_AVAILABLE · '+v.reason));body.append(tr);}
  table.append(thead,body);wrap.append(table);results.append(wrap);}
 // With observation bases, one return per evaluation segment: from its first primary record to its last (the current
 // segment stays open). PREPARATORY rows never start a segment's return. Without any basis the earlier single return applies.
 function segmentPlan(){const p=state.ledger;if(!p||p.schema_version!==2||!p.versions[V2_VERSION].some(r=>Object.hasOwn(r,'basis')))return null;
  const list=segments(p.versions[V2_VERSION]);return list.map((s,i)=>({segment:s.segment,start:s.eligible_dates[0]??null,end:i===list.length-1?null:(s.eligible_dates.at(-1)??null),current:i===list.length-1}));}
 function compute(){const w=weights(),series={};for(const[id,v]of state.series)series[id]=v;const plan=segmentPlan();
  if(plan===null){state.segmentResults=null;state.result=forwardReturn({start_date:state.ledger.start_date,weights_units:w,series});return;}
  state.segmentResults=plan.map(s=>({...s,result:s.start===null?null:forwardReturn({start_date:s.start,end_date:s.end,weights_units:w,series})}));
  const current=state.segmentResults.at(-1);
  state.result=current&&current.result?current.result:{state:'NOT_AVAILABLE',reason:'NO_PRIMARY_RECORD',instruments:{},missing_count:0};}
 async function loadPrices(){
  if(state.busy||readiness()!=='READY'){paintPrices();return;}
  const revision=state.revision,session=state.session,sessionRevision=session.revision(),origin=storedOrigin(),today=eastern(Date.now()).date,range=rangeFor(state.ledger.start_date,today);
  state.busy=true;state.message='';state.controller=new view.AbortController();status.dataset.code='LOADING';status.textContent='LOADING';load_.disabled=true;
  const current=()=>!state.disposed&&host.isConnected&&state.revision===revision&&session.revision()===sessionRevision&&session.state().connected;
  let stop=null;
  try{for(const id of Object.keys(weights()).sort()){
    const have=state.series.get(id);if(Array.isArray(have))continue;
    const symbol=view.PrivateHistory.symbolFor(id);if(!symbol){state.series.set(id,'HISTORY_UNAVAILABLE');continue;}
    try{const payload=await session.fetchHistory(origin,symbol,range,{approvedOrigin:config.privateHistoryWorkerOrigin,signal:state.controller.signal});if(!current())return;
     state.series.set(id,seriesFromHistory(view.PrivateHistory.validateHistory(payload,{symbol,range})));}
    catch(e){if(!current())return;const code=typeof e?.message==='string'&&/^[A-Z_]{3,40}$/.test(e.message)?e.message:'HISTORY_UNAVAILABLE';state.series.set(id,code);if(STOP.has(code)){stop=code;break;}}}
   compute();const left=Object.keys(weights()).filter(id=>!Array.isArray(state.series.get(id))).length;
   state.message=stop?stop+' · '+x('남은 종목 ','remaining ')+left+' · '+x('잠시 후 다시 누르면 남은 종목만 읽습니다.','Click again later to read only the remaining symbols.'):'';
  }finally{if(state.revision===revision){state.busy=false;state.controller=null;}if(current()){for(const[id,v]of state.series)if(STOP.has(v))state.series.delete(id);paintPrices();}}}
 load_.addEventListener('click',()=>{void loadPrices();});clear.addEventListener('click',()=>{clearPrices(state);paintPrices();});
 paintLedger({state:'NOT_AVAILABLE',reason:'LOADING'});paintPrices();
 const ledgerPromise=options.ledgerPromise||load(view);
 Promise.resolve(ledgerPromise).then(res=>{if(state.disposed||!host.isConnected)return;state.ledger=res&&res.state==='LOADED'?res.ledger:null;paintLedger(res&&res.state?res:{state:'NOT_AVAILABLE',reason:'LEDGER_INVALID'});paintPrices();}).catch(()=>{if(!state.disposed&&host.isConnected){paintLedger({state:'NOT_AVAILABLE',reason:'LEDGER_UNREACHABLE'});paintPrices();}});
 if(config.privateHistoryEnabled===true&&config.googleSheetsClientId&&view.GoogleSheetQuotes&&view.DeviceActual){
  (async()=>{try{const session=view.GoogleSheetQuotes.sessionFor(view,config.googleSheetsClientId),settings=await view.DeviceActual.sheetSettings(view);if(state.disposed)return;
   if(session.state().enabled!==settings.enabled)session.setEnabled(settings.enabled);state.session=session;let rev=session.revision();
   state.unsubscribe=session.subscribe(()=>{if(state.disposed||!host.isConnected){dispose(state);return;}if(!session.state().connected||session.revision()!==rev){clearPrices(state);rev=session.revision();}paintPrices();});paintPrices();}catch(_){paintPrices();}})();}
 return Object.freeze({dispose(){dispose(state);}});
}
return Object.freeze({FILENAME,START,STRATEGY,VERSION,V_VERSION,V2_VERSION,V2_STRATEGY,BENCHMARK,PRIMARY_MIN,FRESH_DAYS,EVAL_REASONS,validate,load,instrumentReturn,forwardReturn,qgSummary,rowEvaluation,segments,seriesFromHistory,rangeFor,eastern,sessionDay,mount,disposeAll});
});
