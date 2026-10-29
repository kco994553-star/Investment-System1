/* Central V publication reader `qgv-official.json` (qgv-official/1, GSQ-024; design CENTRAL_V_PUBLICATION_DESIGN_20261018.md §12-4,
   owner decision D8 (b): the old screens read it for TARGET v1, spec 2.1.7 / 6.1.2~6.1.4). Strict twin of Python
   qgv/qgv_official.py parse() / require_qgv_official(); JS==Python vectors: tests/fixtures/qgv_official_vectors_v1.json
   (tests/build_qgv_official_vectors.py). The file carries scores, ranks, reasons, counts and basis times only: nothing here
   attaches a quote to anything, and a null score stays null with its reason (NA is never 0). One same-origin fetch on demand
   (no-store), no storage, no logging; any failure is a fixed code and the screen keeps the device V ("임시 V").
   Stricter than Python: times.verified_at must be set. Not mirrored, by design (the Pages guard runs the Python validator on every
   deploy, so such bytes never ship): int vs float spelling (5 vs 5.0), hence Python's exact canonical size (whole floats are
   counted as ints here: a lower bound), and which code wins when two rules fail in an order JS cannot see (integer-like object
   keys come first, an integer literal beyond the float range is already Infinity). */
(function(root,factory){const node=typeof module==='object'&&module.exports;
 const api=factory(node?()=>require('./qgv-v2.js'):()=>root.QgvV2,node?()=>require('./type-config-defaults.js'):()=>root.TypeConfigDefaults,node?()=>require('./dcf-parameters-defaults.js'):()=>root.DcfParametersDefaults,node?()=>require('./forward-validation.js'):()=>root.ForwardValidation);
 if(node)module.exports=api;else root.QgvOfficial=api;})(typeof globalThis==='object'?globalThis:this,function(qgvV2,typeDefaults,dcfDefaults,calendar){
'use strict';
const deep=x=>{if(x&&typeof x==='object'){Object.freeze(x);Object.values(x).forEach(deep);}return x;};
const SCHEMA='qgv-official/1',KIND='QGV_OFFICIAL',FILENAME='qgv-official.json',MAX_BYTES=2*1024*1024,TARGET_PREFIX='TARGET:',MAX_DEPTH=32,MAX_ROWS=2048;
const TOP_KEYS=deep(['schema','kind','publication_id','state','calc_version','engine','population','weights','type_scope','config_versions','price_source','attribution','inputs','times','coverage','rows']);
const ROW_KEYS=deep(['cik','profile','industry_group','in_cross_section','state','source_reason_codes','acquired_at','fiscal_year_end','factors','axes','weights','type_weights','type_reason','selected_types','q_industry_percentile','value_trap_gate','v_excluded','flags','total','total_reason','price_status','rank','qg_reference_order','rank_row']);
const FACTOR_KEYS=deep(['score','reason','basis']),AXIS_KEYS=deep(['score','state','weight_available','factors_available','reason']);
const FORBIDDEN_KEYS=deep(['close','closes','detail','ebit_yield','enterprise_value','ev','expectation_gap','fcf_yield','hmac','implied_growth','market_cap','marketcap','mcap','month_closes','price','price_e4','price_hmac','prices','quote','quotes','realized_growth','reference_range','yield']),FORBIDDEN=new Set(FORBIDDEN_KEYS);
// D-CV2: raw price-dependent engine codes are published as one label; as a reason they are refused (flags/basis may carry them).
const PRICE_DEPENDENT=deep(['EV_NON_POSITIVE','NUMERIC_OVERFLOW','ROOT_NOT_BRACKETED','ROOT_NOT_CONVERGED']),PRICE_DEPENDENT_PUBLIC='PRICE_DEPENDENT_NOT_COMPUTABLE',STOPS=['PRICE_IDENTITY_CONFLICT','CALC_VERSION_MISMATCH'];
const STATUS_CODES=deep(['SUPPLIED','ODD_LOT_ONLY','NO_IEX_TRADE','PRICE_SYMBOL_UNMAPPED','ADR_RATIO_UNCONFIRMED','SPLIT_AFTER_SHARE_COUNT','PRICE_IDENTITY_CONFLICT','IDENTITY_CONFLICT_WITHDRAWN']),SUPPLIED='SUPPLIED';
const SUPPLY_MIN=0.95,V_TARGET_SHARE=0.9,MAX_MONTHS=1200,POPULATION_VERSION='sec-universe-shares/v0',INPUTS_FILE='sec-qgv2.json',SHARE_BASIS_SINCE=deep(['2026-10-23',1]);
// The screen shows these three from the publication itself; equality keeps the GSQ-024 wording exact.
const ATTRIBUTION=deep({text:'Data provided for free by IEX. By accessing or using IEX Historical Data, you agree to the IEX Historical Data Terms of Use.',terms_url:'https://www.iex.io/legal/hist-data-terms',label_ko:'IEX 마지막 체결가 기준(공식 종가 아님)'});
const PRICE_SOURCE=deep({provider:'IEX_HIST',feed:'TOPS 1.6',basis_kind:'IEX_LAST_REGULAR_SESSION_TRADE',adjustment_basis:'AS_TRADED',currency:'USD'}),MONTH_END=deep({store:'iex-monthend/1',basis:'RAW_DIVIDED_BY_SHARE_BASIS_FACTOR'});
const TARGET_TICKERS=deep({amd:'AMD',amzn:'AMZN',asml:'ASML',avgo:'AVGO',etn:'ETN',gev:'GEV',googl:'GOOGL',hanmi:'042700',hubb:'HUBB',intc:'INTC',klac:'KLAC',lrcx:'LRCX',msft:'MSFT',nvda:'NVDA',qcom:'QCOM',rok:'ROK',rtx:'RTX',stry:'SYK',tokyo_electron:'8035'});
// Same text as web_app/qgv.js V_SOURCES (DEVICE_TEMPORARY = TargetV1Builder.V_SOURCE); OFFICIAL_CENTRAL is draft wording.
const V_SOURCES=deep({DEVICE_TEMPORARY:{id:'DEVICE_TEMPORARY',ko:'임시 V',note:'기기 시세로 계산 · 중앙 V 미게시'},OFFICIAL_CENTRAL:{id:'OFFICIAL_CENTRAL',ko:'공식 V',note:'중앙 게시 · IEX 마지막 체결가 기준(공식 종가 아님)'}});
// Why the official V was not used (one short line on the screen) and the codes thrown (Python's three + two JS environment codes).
const REASONS=deep(['OFFICIAL_NOT_PUBLISHED','OFFICIAL_UNAVAILABLE','OFFICIAL_INVALID','OFFICIAL_CALC_VERSION_DIFFERS','OFFICIAL_STALE']);
const ERRORS=deep(['OFFICIAL_INVALID','OFFICIAL_FORBIDDEN_KEY','OFFICIAL_TOO_LARGE','OFFICIAL_UNAVAILABLE','OFFICIAL_DIGEST_UNAVAILABLE']);
const FRESH_SESSIONS=2;   // D-CV6 recommended threshold: completed New York sessions after the price basis day
const CLOSE_MINUTES=16*60;   // a session counts as completed from 16:00 New York (ForwardValidation's cut; no early-close table here)
const RX={reason:/^[A-Z][A-Z0-9_]{0,63}$/,code:/^(?:[A-Z]{2,8}:[A-Z0-9][A-Z0-9.\-]{0,15}|TARGET:[a-z][a-z0-9_]{0,63})$/,hex:/^[0-9a-f]{64}$/,day:/^\d{4}-\d{2}-\d{2}$/,
 clock:/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$/,stamp:/^\d{8}$/,id:/^[a-z][a-z0-9_]{0,63}$/,cik:/^\d{10}$/,pub:/^qgvpub-[0-9a-f]{64}$/,calc:/^qgv2-calc\/(\d{4})-(\d{2})-(\d{2})\.(\d{1,4})$/};
const VALID=new WeakSet();
function fail(code){throw Error(code);}
function need(v,code='OFFICIAL_INVALID'){if(!v)fail(code);}
const object=v=>v!==null&&typeof v==='object'&&!Array.isArray(v),num=v=>typeof v==='number'&&Number.isFinite(v),int=(v,low=0,high=Infinity)=>Number.isInteger(v)&&v>=low&&v<=high;
const str=(v,rx)=>typeof v==='string'&&rx.test(v),strOrNull=(v,rx)=>v===null||str(v,rx),scoreOk=v=>v===null||num(v)&&v>=0&&v<=100;
const reasonOk=v=>v===null||str(v,RX.reason)&&!PRICE_DEPENDENT.includes(v);
function keys(v,ks){need(object(v)&&Object.keys(v).length===ks.length&&ks.every(k=>Object.hasOwn(v,k)));}
function deps(){const v2=qgvV2(),t=typeDefaults(),d=dcfDefaults();if(!v2||!t||!d)fail('OFFICIAL_UNAVAILABLE');return{v2,t,d};}
function dayOk(y,m,d){return y>=1&&m>=1&&m<=12&&d>=1&&d<=[31,y%4===0&&y%100!==0||y%400===0?29:28,31,30,31,30,31,31,30,31,30,31][m-1];}
function isDay(v){return str(v,RX.day)&&dayOk(+v.slice(0,4),+v.slice(5,7),+v.slice(8,10));}
// v2_factors.carries_share_basis: a real calendar day and (day, n) >= (2026-10-23, 1).
function calcOk(c){const m=typeof c==='string'?RX.calc.exec(c):null;if(!m||!dayOk(+m[1],+m[2],+m[3]))return false;const day=m[1]+'-'+m[2]+'-'+m[3];return day>SHARE_BASIS_SINCE[0]||day===SHARE_BASIS_SINCE[0]&&+m[4]>=SHARE_BASIS_SINCE[1];}
// qgv_official._symbol (tie order of ranks): a TARGET row's device ticker, else the code's ticker with every '.' as '-'.
function symbol(key){if(key.startsWith(TARGET_PREFIX)){const id=key.slice(TARGET_PREFIX.length);return Object.hasOwn(TARGET_TICKERS,id)?TARGET_TICKERS[id]:key;}return key.slice(key.indexOf(':')+1).replaceAll('.','-').toUpperCase();}
function walk(v,depth){need(depth<=MAX_DEPTH);if(Array.isArray(v)){for(const x of v)walk(x,depth+1);}else if(object(v)){for(const k of Object.keys(v)){need(!FORBIDDEN.has(k.toLowerCase()),'OFFICIAL_FORBIDDEN_KEY');walk(v[k],depth+1);}}else if(typeof v==='number')need(Number.isFinite(v));}
function rowOk(key,r,v2){
 keys(r,ROW_KEYS);need(str(key,RX.code));
 need(strOrNull(r.cik,RX.cik)&&[null,'GENERAL','FINANCIAL'].includes(r.profile));
 need(strOrNull(r.industry_group,RX.id)&&typeof r.in_cross_section==='boolean');
 need(['LIVE','STALE','NOT_AVAILABLE','WITHDRAWN'].includes(r.state));
 need(Array.isArray(r.source_reason_codes)&&r.source_reason_codes.every(x=>x!==null&&reasonOk(x)));
 need(strOrNull(r.acquired_at,RX.clock)&&strOrNull(r.fiscal_year_end,RX.day));
 need(STATUS_CODES.includes(r.price_status));
 keys(r.factors,v2.FACTORS);
 for(const f of Object.values(r.factors)){keys(f,FACTOR_KEYS);need(scoreOk(f.score)&&reasonOk(f.reason)&&strOrNull(f.basis,RX.reason));need(f.score===null||f.reason===null);}
 keys(r.axes,v2.PILLARS);
 for(const a of Object.values(r.axes)){keys(a,AXIS_KEYS);need(scoreOk(a.score)&&reasonOk(a.reason)&&['READY','PARTIAL','NOT_AVAILABLE'].includes(a.state));need(typeof a.weight_available==='number'&&a.weight_available>=0&&a.weight_available<=1);need(int(a.factors_available,0,5));}
 for(const name of ['weights','type_weights']){const w=r[name];need(w===null||object(w)&&Object.keys(w).length===3&&v2.PILLARS.every(p=>Object.hasOwn(w,p)&&num(w[p])&&w[p]>=0));}
 need(strOrNull(r.type_reason,RX.reason)&&Array.isArray(r.selected_types)&&r.selected_types.every(x=>str(x,RX.id)));
 need(scoreOk(r.q_industry_percentile)&&typeof r.value_trap_gate==='boolean'&&[null,'VALUE_TRAP_GATE'].includes(r.v_excluded));
 need(Array.isArray(r.flags)&&r.flags.every(x=>str(x,RX.reason)));
 need(scoreOk(r.total)&&reasonOk(r.total_reason)&&(r.total===null)===(r.total_reason!==null));
 for(const name of ['rank','qg_reference_order'])need(r[name]===null||int(r[name],1));
 need(strOrNull(r.rank_row,RX.code));
 // Self-consistency through the existing engine (no re-implementation): V axis = QgvV2.axisScore of the published V factors,
 // total = axes x weights with the value-trap gate; exact equality like Python. A stop reason has neither.
 if(STOPS.includes(r.total_reason)){need(r.total===null&&r.axes.V.score===null);return;}
 const vs={};for(const k of Object.keys(v2.WEIGHTS.V))vs[k]=r.factors[k].score;const v=v2.axisScore(vs,'V');
 need(v.score===r.axes.V.score&&v.state===r.axes.V.state);
 need(r.weights!==null);const axes=r.axes,w=r.weights;let data=0;for(const p of v2.PILLARS)if(axes[p].score!==null)data+=w[p];
 const included=v2.PILLARS.filter(p=>axes[p].score!==null&&!(p==='V'&&r.value_trap_gate));
 if(data/100<v2.MIN_AXIS_WEIGHT||!included.length)need(r.total===null);else{let acc=0,used=0;for(const p of included){acc+=w[p]*axes[p].score;used+=w[p];}need(r.total===acc/used);}
 need(r.value_trap_gate===(r.v_excluded==='VALUE_TRAP_GATE'));}
// D-CV8 / D-CV9 / D11: consecutive ranks in total order (ties: ticker, then key), one place per CIK, rank_row to a placed row.
function ranksOk(rows){
 const cmp=(a,b)=>a<b?-1:a>b?1:0;
 for(const name of ['rank','qg_reference_order']){
  const got=Object.keys(rows).filter(k=>rows[k][name]!==null).map(k=>[rows[k][name],k]).sort((a,b)=>a[0]-b[0]||cmp(a[1],b[1]));
  got.forEach(([n],i)=>need(n===i+1));
  for(let i=1;i<got.length;i++){const ka=got[i-1][1],kb=got[i][1],a=rows[ka],b=rows[kb],sa=symbol(ka),sb=symbol(kb);need(num(a.total)&&num(b.total)&&a.total>=b.total);need(a.total>b.total||sa<sb||sa===sb&&ka<kb);}
  for(const [,k] of got)need(num(rows[k].total)&&num(rows[k].axes.V.score)===(name==='rank'));}
 const ciks=Object.values(rows).filter(r=>r.rank!==null||r.qg_reference_order!==null).map(r=>r.cik);
 need(new Set(ciks).size===ciks.length&&!ciks.includes(null));
 for(const [k,r] of Object.entries(rows)){
  if(r.rank_row!==null){const t=Object.hasOwn(rows,r.rank_row)?rows[r.rank_row]:null;need(t!==null&&t.cik===r.cik&&(t.rank!==null||t.qg_reference_order!==null));}
  if(r.rank!==null||r.qg_reference_order!==null)need(r.rank_row===k);}}
// qgv_official.coverage: counts only, recomputed from the rows (QgvScores.vCoverage vocabulary).
function coverage(rows,v2=deps().v2){
 const pop={total:0,general:0,financial:0,unknown:0,stopped:0},v={full:0,general:0},qgv={full:0,general:0},qg={full:0,general:0,financial:0,no_v:0,gate:0};
 const status={},reasons={},factorReasons={},bump=(m,k)=>{m[k]=(Object.hasOwn(m,k)?m[k]:0)+1;},vf=Object.keys(v2.WEIGHTS.V);let missing=0;
 const vReason=r=>{if(r.price_status!==SUPPLIED)return r.price_status;for(const k of vf)if(r.factors[k].score===null&&r.factors[k].reason)return r.factors[k].reason;return r.axes.V.reason||'V_INPUTS_NOT_AVAILABLE';};
 for(const key of Object.keys(rows).sort()){
  if(key.startsWith(TARGET_PREFIX))continue;const r=rows[key];
  const cls=r.state==='WITHDRAWN'?'stopped':r.profile==='GENERAL'?'general':r.profile==='FINANCIAL'?'financial':'unknown',gen=cls==='general'?1:0,hasV=num(r.axes.V.score);
  pop.total++;pop[cls]++;bump(status,r.price_status);
  if(hasV){v.full++;v.general+=gen;if(num(r.axes.Q.score)&&num(r.axes.G.score)){qgv.full++;qgv.general+=gen;}}
  if(num(r.total)&&!hasV){qg.full++;qg.general+=gen;qg[cls==='financial'?'financial':'no_v']++;}
  if(num(r.total)&&hasV&&r.v_excluded)qg.gate++;
  if(gen&&!hasV){missing++;bump(reasons,vReason(r));for(const f of [...new Set(vf.filter(k=>r.factors[k].score===null&&r.factors[k].reason).map(k=>r.factors[k].reason))].sort())bump(factorReasons,f);}}
 const listed=m=>Object.entries(m).sort((a,b)=>b[1]-a[1]||(a[0]<b[0]?-1:a[0]>b[0]?1:0)),n=Math.ceil(V_TARGET_SHARE*pop.general-1e-9),all=Object.values(rows);
 return{basis:'UNIVERSE_CODES',population:pop,v,qgv,qg_only_total:qg,ranked:all.filter(r=>r.rank!==null).length,qg_reference:all.filter(r=>r.qg_reference_order!==null).length,
  price_status:status,not_computed:missing,reasons:listed(reasons),factor_reasons:listed(factorReasons),target:{share:V_TARGET_SHARE,n,met:v.general>=n,observation_only:true}};}
// Python compares coverage as sorted-key JSON text: types must match too (true is not 1).
function same(a,b){if(a===null||b===null||typeof a!=='object'||typeof b!=='object')return typeof a===typeof b&&a===b;if(Array.isArray(a)!==Array.isArray(b))return false;
 if(Array.isArray(a))return a.length===b.length&&a.every((x,i)=>same(x,b[i]));const ka=Object.keys(a);return ka.length===Object.keys(b).length&&ka.every(k=>Object.hasOwn(b,k)&&same(a[k],b[k]));}
function supplyOk(ps,rows){
 const s=ps.supply,pool=Object.keys(rows).filter(k=>!k.startsWith(TARGET_PREFIX)).map(k=>rows[k]).filter(r=>r.in_cross_section&&r.profile==='GENERAL'&&!['ADR_RATIO_UNCONFIRMED','SPLIT_AFTER_SHARE_COUNT'].includes(r.price_status));
 need(int(s.eligible,1)&&int(s.supplied)&&s.supplied<=s.eligible);
 need(s.minimum_share===SUPPLY_MIN&&s.met===true&&s.supplied>=Math.ceil(SUPPLY_MIN*s.eligible-1e-9));
 need(s.eligible<=pool.length&&s.supplied<=ps.supplied);
 need(s.supplied<=pool.filter(r=>r.price_status===SUPPLIED).length&&s.eligible-s.supplied<=pool.filter(r=>r.price_status!==SUPPLIED).length);}
// require_qgv_official without the digest and the size (async / last, below). Same order of rules, so the same code wins.
function check(p,{v2,t,d}){
 keys(p,TOP_KEYS);walk(p,0);
 need(p.schema===SCHEMA&&p.kind===KIND&&p.state==='OFFICIAL'&&str(p.publication_id,RX.pub));
 const calc=p.calc_version;need(calcOk(calc));
 const eng=p.engine;keys(eng,['version','status','python_sha256','js_sha256','publisher_sha256']);
 need(eng.version===v2.VERSION&&eng.status===v2.STATUS&&['python_sha256','js_sha256','publisher_sha256'].every(k=>str(eng[k],RX.hex)));
 const pop=p.population;keys(pop,['version','universe_code_count','registry_sha256','row_count','pooled_count','pooled_digest']);
 need(pop.version===POPULATION_VERSION&&str(pop.registry_sha256,RX.hex)&&str(pop.pooled_digest,RX.hex)&&['universe_code_count','row_count','pooled_count'].every(k=>int(pop[k],0,MAX_ROWS)));
 keys(p.weights,['default_preset','gate','type_weights','profile_id','weights_version']);
 const w={default_preset:v2.DEFAULT_PRESET,gate:true,type_weights:true,profile_id:v2.VERSION+'/'+v2.DEFAULT_PRESET+'/gate-on',weights_version:v2.weightsId(v2.officialWeights(v2.DEFAULT_PRESET),true)};
 need(Object.keys(w).every(k=>p.weights[k]===w[k])&&p.type_scope===v2.TYPE_SCOPE);
 keys(p.config_versions,['type_config','dcf_parameters']);need(p.config_versions.type_config===t.config_version&&p.config_versions.dcf_parameters===d.config_version);
 const ps=p.price_source;keys(ps,['provider','feed','basis_kind','adjustment_basis','currency','basis_date','requested_basis_date','supplied','rejected','supply','month_end']);
 need(Object.keys(PRICE_SOURCE).every(k=>ps[k]===PRICE_SOURCE[k]));
 need(str(ps.basis_date,RX.day)&&str(ps.requested_basis_date,RX.day)&&ps.basis_date<=ps.requested_basis_date&&int(ps.supplied));
 need(object(ps.rejected)&&Object.entries(ps.rejected).every(([k,n])=>STATUS_CODES.includes(k)&&k!==SUPPLIED&&int(n,1)));
 keys(ps.supply,['eligible','supplied','minimum_share','met']);
 const me=ps.month_end;keys(me,['store','stamp','months','basis']);need(me.store===MONTH_END.store&&str(me.stamp,RX.stamp)&&int(me.months,0,MAX_MONTHS)&&me.basis===MONTH_END.basis);
 keys(p.attribution,Object.keys(ATTRIBUTION));need(Object.keys(ATTRIBUTION).every(k=>p.attribution[k]===ATTRIBUTION[k]));
 need(Array.isArray(p.inputs)&&p.inputs.length===1);const inp=p.inputs[0];keys(inp,['file','sha256','as_of','calc_version','acquired_oldest','acquired_newest']);
 need(inp.file===INPUTS_FILE&&str(inp.sha256,RX.hex)&&inp.calc_version===calc&&str(inp.as_of,RX.clock));
 need(strOrNull(inp.acquired_oldest,RX.clock)&&strOrNull(inp.acquired_newest,RX.clock)&&(inp.acquired_oldest===null)===(inp.acquired_newest===null));
 need(inp.acquired_oldest===null||inp.acquired_oldest<=inp.acquired_newest);   // text order, like Python
 const tm=p.times;keys(tm,['price_basis_date','price_collected_from','price_collected_to','inputs_as_of','generated_at','verified_at']);
 need(tm.price_basis_date===ps.basis_date&&tm.inputs_as_of===inp.as_of&&['price_collected_from','price_collected_to','generated_at'].every(k=>str(tm[k],RX.clock)));
 need(str(tm.verified_at,RX.clock));   // stricter than Python (null allowed there): only a verified publication is used
 const rows=p.rows;need(object(rows));const ks=Object.keys(rows);need(ks.length>0&&ks.length<=MAX_ROWS);
 for(const k of ks)rowOk(k,rows[k],v2);
 ranksOk(rows);
 need(pop.row_count===ks.length&&pop.pooled_count===ks.filter(k=>rows[k].in_cross_section).length);
 need(pop.universe_code_count===ks.filter(k=>!k.startsWith(TARGET_PREFIX)).length);
 const rejected={},universe=ks.filter(k=>!k.startsWith(TARGET_PREFIX)).sort();
 for(const k of universe)if(rows[k].price_status!==SUPPLIED)rejected[rows[k].price_status]=(rejected[rows[k].price_status]||0)+1;
 need(same(ps.rejected,rejected)&&ps.supplied===universe.filter(k=>rows[k].price_status===SUPPLIED).length);
 supplyOk(ps,rows);
 need(same(p.coverage,coverage(rows,v2)));
 return rows;}
// population.pooled_digest: SHA-256 of the sorted cross-section keys joined by '\n' (Web Crypto; none -> fail closed).
async function pooledDigest(rows){
 const subtle=typeof globalThis.crypto==='object'&&globalThis.crypto?globalThis.crypto.subtle:null;if(!subtle||typeof subtle.digest!=='function')fail('OFFICIAL_DIGEST_UNAVAILABLE');
 let buf;try{buf=await subtle.digest('SHA-256',new TextEncoder().encode(Object.keys(rows).filter(k=>rows[k].in_cross_section===true).sort().join('\n')));}catch(_){fail('OFFICIAL_DIGEST_UNAVAILABLE');}
 return Array.from(new Uint8Array(buf),b=>b.toString(16).padStart(2,'0')).join('');}
// Length of Python json.dumps(sort_keys, ensure_ascii, separators=(',',':')); a whole number counts as an int (lower bound).
function stringLength(s){let n=2;for(let i=0;i<s.length;i++){const c=s.charCodeAt(i);n+=c===34||c===92||c===8||c===9||c===10||c===12||c===13?2:c<32||c>126?6:1;}return n;}
function numberLength(v){
 if(Number.isInteger(v)&&Math.abs(v)<1e16)return String(v).length;   // int spelling; from 1e16 Python's float form is shorter
 const [m,e]=Math.abs(v).toExponential().split('e'),x=Number(e),digits=m.replace('.','').length,sign=v<0?1:0;
 if(x<-4||x>=16)return sign+m.length+2+Math.max(2,String(Math.abs(x)).length);   // Python repr: 1e-05, 1.5e+16
 return sign+(x<0?1-x+digits:digits+1);}
function canonicalLength(v){
 if(v===null||v===true)return 4;if(v===false)return 5;if(typeof v==='number')return numberLength(v);if(typeof v==='string')return stringLength(v);
 if(Array.isArray(v)){let n=1+Math.max(1,v.length);for(const x of v)n+=canonicalLength(x);return n;}
 const ks=Object.keys(v);let n=1+Math.max(1,ks.length);for(const k of ks)n+=stringLength(k)+1+canonicalLength(v[k]);return n;}
// JSON.parse keeps the last of two equal keys; Python's parse refuses them. One scan over text JSON.parse already accepted.
function duplicateKeys(text){
 const stack=[];
 for(let i=0;i<text.length;i++){const c=text.charCodeAt(i);
  if(c===34){let j=i+1;while(j<text.length&&text.charCodeAt(j)!==34)j+=text.charCodeAt(j)===92?2:1;
   const top=stack[stack.length-1];
   if(top&&top.keys&&top.expect){const raw=text.slice(i+1,j),k=raw.includes('\\')?JSON.parse(text.slice(i,j+1)):raw;if(top.keys.has(k))return true;top.keys.add(k);top.expect=false;}
   i=j;}
  else if(c===123)stack.push({keys:new Set(),expect:true});else if(c===91)stack.push({keys:null});else if(c===125||c===93)stack.pop();
  else if(c===44){const top=stack[stack.length-1];if(top&&top.keys)top.expect=true;}}
 return false;}
/* validate(payload,{maxBytes}) -> the same payload, deep-frozen and remembered (state() === 'OFFICIAL'), or throws Error(code):
   OFFICIAL_INVALID | OFFICIAL_FORBIDDEN_KEY | OFFICIAL_TOO_LARGE (Python's codes), OFFICIAL_UNAVAILABLE (a module missing),
   OFFICIAL_DIGEST_UNAVAILABLE (no Web Crypto). */
async function validate(payload,{maxBytes=MAX_BYTES}={}){
 const env=deps();let rows;
 try{rows=check(payload,env);}catch(e){fail(e&&e.message==='OFFICIAL_FORBIDDEN_KEY'?e.message:'OFFICIAL_INVALID');}
 need(await pooledDigest(rows)===payload.population.pooled_digest);
 need(canonicalLength(payload)<=maxBytes,'OFFICIAL_TOO_LARGE');
 deep(payload);VALID.add(payload);return payload;}
// parse(bytes) like Python parse(): at most maxBytes, strict UTF-8 without BOM, JSON without duplicate keys, then validate.
async function parse(bytes,{maxBytes=MAX_BYTES}={}){
 const u8=ArrayBuffer.isView(bytes)?new Uint8Array(bytes.buffer,bytes.byteOffset,bytes.byteLength):Object.prototype.toString.call(bytes)==='[object ArrayBuffer]'?new Uint8Array(bytes):null;
 need(u8&&u8.byteLength<=maxBytes);let payload;
 try{const text=new TextDecoder('utf-8',{fatal:true,ignoreBOM:true}).decode(u8);if(text.charCodeAt(0)===0xFEFF||(payload=JSON.parse(text),duplicateKeys(text)))throw 0;}catch(_){fail('OFFICIAL_INVALID');}
 return validate(payload,{maxBytes});}
/* load(view | fetchFn, {signal,maxBytes}) -> {state:'OFFICIAL',payload} | {state:'NOT_PUBLISHED',payload:null} (404: none yet), or
   throws a code above (network error, redirect, other HTTP status: OFFICIAL_UNAVAILABLE). The one request of this module. */
async function load(source,{signal,maxBytes=MAX_BYTES}={}){
 const get=typeof source==='function'?source:source&&typeof source.fetch==='function'?(u,o)=>source.fetch(u,o):null;
 if(!get)fail('OFFICIAL_UNAVAILABLE');let response,bytes;
 try{response=await get(FILENAME,{cache:'no-store',credentials:'omit',redirect:'error',referrerPolicy:'no-referrer',signal,headers:{Accept:'application/json'}});}catch(_){fail('OFFICIAL_UNAVAILABLE');}
 if(!response||typeof response.status!=='number')fail('OFFICIAL_UNAVAILABLE');
 if(response.status===404)return{state:'NOT_PUBLISHED',payload:null};
 if(!response.ok)fail('OFFICIAL_UNAVAILABLE');
 const length=response.headers&&typeof response.headers.get==='function'?Number(response.headers.get('content-length')):NaN;
 need(!(length>maxBytes));
 try{bytes=await response.arrayBuffer();}catch(_){fail('OFFICIAL_UNAVAILABLE');}
 return{state:'OFFICIAL',payload:await parse(bytes,{maxBytes})};}
function state(payload){return VALID.has(payload)?'OFFICIAL':null;}
function reasonOf(error){const m=error&&error.message;return m==='OFFICIAL_UNAVAILABLE'||m==='OFFICIAL_DIGEST_UNAVAILABLE'?'OFFICIAL_UNAVAILABLE':'OFFICIAL_INVALID';}
function nextDay(d){const x=new Date(d+'T00:00:00Z');x.setUTCDate(x.getUTCDate()+1);return x.toISOString().slice(0,10);}
/* Completed New York sessions after the basis day (spec M4) with the existing NYSE calendar (ForwardValidation.sessionDay): every
   session day before the device's New York day `today`, and today's own session when it has closed (closed; default true: a
   caller that does not know the New York time counts today, never younger than the true count). null = not countable: a basis
   day in the future, a bad day, no calendar or past its end. Stops counting above FRESH_SESSIONS. */
function sessionsAfter(basis,today,closed=true){
 if(!isDay(basis)||!isDay(today)||basis>today)return null;const cal=calendar();if(!cal||typeof cal.sessionDay!=='function')return null;
 let n=0;try{for(let d=nextDay(basis);d<today||closed!==false&&d===today;d=nextDay(d))if(cal.sessionDay(d)&&++n>FRESH_SESSIONS)break;}catch(_){return null;}return n;}
function nyNow(ms=Date.now()){const cal=calendar();try{const e=cal&&typeof cal.eastern==='function'?cal.eastern(ms):null;return e&&isDay(e.date)&&int(e.minutes,0,1439)?Object.freeze({date:e.date,minutes:e.minutes}):null;}catch(_){return null;}}
function nyToday(ms=Date.now()){const e=nyNow(ms);return e?e.date:null;}
/* usable(payload,{secCalcVersion,nyToday,nyMinutes}) (pure) -> {ok,reason,sessions}: the central V may feed the TARGET v1 draft only
   when the payload passed validate(), verified_at is set, calc_version equals the re-read sec-qgv2.json calc_version and at most
   FRESH_SESSIONS completed New York sessions follow the price basis day. nyMinutes: minutes after New York midnight of the same
   clock as nyToday (nyNow()); today's session is completed from CLOSE_MINUTES, or when nyMinutes is unknown (fail closed).
   reason: OFFICIAL_INVALID | OFFICIAL_CALC_VERSION_DIFFERS | OFFICIAL_STALE. */
function usable(payload,{secCalcVersion=null,nyToday:today=null,nyMinutes=null}={}){
 if(!VALID.has(payload)||!str(payload.times.verified_at,RX.clock))return{ok:false,reason:'OFFICIAL_INVALID',sessions:null};
 if(typeof secCalcVersion!=='string'||payload.calc_version!==secCalcVersion)return{ok:false,reason:'OFFICIAL_CALC_VERSION_DIFFERS',sessions:null};
 const sessions=sessionsAfter(payload.times.price_basis_date,today,!int(nyMinutes,0,CLOSE_MINUTES-1));
 return sessions===null||sessions>FRESH_SESSIONS?{ok:false,reason:'OFFICIAL_STALE',sessions}:{ok:true,reason:null,sessions};}
// resolve(view | fetchFn, {secCalcVersion,nyToday,signal}) -> {ok,reason,sessions,payload}; never throws, payload only when ok.
async function resolve(source,opts={}){
 let got;try{got=await load(source,opts);}catch(e){return{ok:false,reason:reasonOf(e),sessions:null,payload:null};}
 if(got.state==='NOT_PUBLISHED')return{ok:false,reason:'OFFICIAL_NOT_PUBLISHED',sessions:null,payload:null};
 const u=usable(got.payload,opts);return{ok:u.ok,reason:u.reason,sessions:u.sessions,payload:u.ok?got.payload:null};}
return Object.freeze({SCHEMA,KIND,FILENAME,MAX_BYTES,TARGET_PREFIX,FRESH_SESSIONS,CLOSE_MINUTES,TOP_KEYS,ROW_KEYS,FACTOR_KEYS,AXIS_KEYS,FORBIDDEN_KEYS,PRICE_DEPENDENT,PRICE_DEPENDENT_PUBLIC,STATUS_CODES,
 SUPPLY_MIN,V_TARGET_SHARE,MAX_MONTHS,POPULATION_VERSION,INPUTS_FILE,SHARE_BASIS_SINCE,ATTRIBUTION,PRICE_SOURCE,MONTH_END,TARGET_TICKERS,V_SOURCES,REASONS,ERRORS,
 load,parse,validate,usable,resolve,state,reasonOf,nyNow,nyToday,sessionsAfter,symbol,coverage,pooledDigest,canonicalLength,duplicateKeys});
});
