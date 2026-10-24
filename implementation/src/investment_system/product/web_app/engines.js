/* P1 engine wiring (IS2.engines): TARGET v1, playbook, virtual trading and macro lights on the old engines, unchanged and called
   with the arguments the old screens passed (P1 implementation spec, Main decision 9; design §1.1 (6); critique #5, #7a/c/d).
   - Scores are the one QGV page's device result (qgv.forEngines, as QgvScores made it). Every V-bearing result says the V it was
     computed with as v_source (page.engine_v_source.id: always DEVICE_TEMPORARY in P1, never page.v_source), and so do the TARGET
     records whose format has room for it: the saved draft, each R-B row and a finalized version (from its draft). The playbook
     store's records are exact-key formats and carry none: a TARGET card judgement (thresholds.v) and the playbook occurrences
     (V-driven codes such as T1 V_DETERIORATED) stay source-less device-V records (P1_DATA_LAYER.md §8, §10).
   - Every write is a user action on the store's gated storage (WRITE; SYNC when the user's own Sheet is written too). The old
     screens wrote some of these on open (R-B selection, playbook occurrences); here they need the user's click (owner 2026-10-24:
     kept). A judgement says whether it was recorded (recorded / recorded_reason JUDGEMENT_NOT_RECORDED, shown as "기록 안 됨").
   - The V history is not recorded (owner 2026-10-24; the central V history is the server's private store, D9): the recording run
     that captured it (app.js paintReport) is not here, and nothing calls VirtualTradingVHistory.capture / captureV2.
   - Prices only through the one price view and its facade: no price request outside a SYNC click, nothing stored, and prices
     leave only in RAM results of the virtual engine and the set comparison (display only, [data-ram-price]).
   - Only glue the old screens kept unexported is written again, each with its old place named. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else{const I=root.IS2=root.IS2||{};I.engines=api.create({win:root,action:I.action,data:I.data,prices:I.prices,store:I.store,qgv:I.qgv});}})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
const QGV2='sec-qgv2.json',CATALOG='actual-catalog.json',LEDGER='forward-validation-ledger.json',TYPES='company-types-pricefree.json';
// Finalize reasons after which the published file is not one to regenerate a draft from (target-v1-screen.js finalize click).
const NO_REGEN=Object.freeze(['SEC_QGV2_NOT_AVAILABLE','CALC_VERSION_MISSING','CALC_VERSION_MIXED']);
const object=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
const copy=v=>v===undefined?null:JSON.parse(JSON.stringify(v));
function deepFreeze(v){if(v&&typeof v==='object'&&!Object.isFrozen(v)){Object.freeze(v);for(const x of Object.values(v))deepFreeze(x);}return v;}
const out=v=>deepFreeze(copy(v));
const key=t=>String(t||'').replaceAll('.','-').toUpperCase();// target-v1-screen.js / target-v1-builder.js key()
// The old screens' default days: TARGET and the playbook use the UTC day, the virtual report the Seoul day (app.js paintReport).
const today=()=>new Date().toISOString().slice(0,10),seoulDay=()=>new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Seoul'}).format(new Date());
function create({win,action,data,prices,store,qgv}){
 if(!action||typeof action.run!=='function'||!data||typeof data.ready!=='function'||!prices||!prices.priceView||!store||!store.storage||!qgv||typeof qgv.forEngines!=='function')throw Error('LAYER_MISSING');
 const need=n=>{const m=win[n];if(!m)throw Error('READER_MISSING');return m;};
 const storage=store.storage,priceView=prices.priceView,config=()=>object(win.InvestmentAppConfig)?win.InvestmentAppConfig:{};
 const TB=()=>need('TargetV1Builder'),TS=()=>need('TargetV1Screen'),PB=()=>need('PlaybookScreen'),CFG=()=>need('TargetV1ConfigDefaults');
 const catalogNow=async()=>{const c=await data.static(CATALOG);if(!c)throw Error('CATALOG_NOT_AVAILABLE');return c;};
 const codesNow=async()=>{const c=await data.universe();return Array.isArray(c)?c:[];};
 const idsOf=catalog=>{try{return need('DeviceWatchlist').identities(catalog);}catch(_){return[];}};
 // The shared page, or one the caller got from qgv.page(); anything else is PAGE_UNKNOWN before a field of it is read.
 const pageOf=async page=>{if(page===undefined||page===null)return qgv.page();if(typeof qgv.isPage!=='function'||!qgv.isPage(page))throw Error('PAGE_UNKNOWN');return page;};
 const sourceOf=pg=>pg.engine_v_source.id;
 // The V source a stored draft was built with (null: a draft from before sources were kept, or from the old screen).
 const draftSource=st=>st&&st.draft&&typeof st.draft.v_source==='string'?st.draft.v_source:null;
 // The page's device result and the sec-qgv2.json value it was computed from; a page without one is the builder's QGV2_NOT_READY.
 async function scored(page){const pg=await pageOf(page);try{return{pg,computed:qgv.forEngines(pg),inputs:qgv.engineInputs(pg)};}catch(e){if(e&&e.message==='PAGE_NOT_READY')throw Error('QGV2_NOT_READY');throw e;}}

 // ---------------------------------------------------------------- TARGET v1 (2.1.7, detail screen target-v1)
 // Its state lives inside the playbook store (TargetV1Screen.readState / writeState); an unreadable store is never overwritten.
 function readState(){try{return TS().readState(PB(),storage);}catch(e){if(e&&e.message==='READER_MISSING')throw e;throw Error('TARGET_V1_STATE_INVALID');}}
 const save=next=>TS().writeState(PB(),storage,next);
 const state=()=>out(readState());
 // The builder's arguments as the old screen built them (target-v1-screen.js mount: computed, inputs, universeCodes, existing).
 async function builderArgs(page,date){const{pg,computed,inputs}=await scored(page),catalog=await catalogNow();return{pg,args:{computed,inputs,universeCodes:await codesNow(),existing:TS().existingSymbols(catalog),date}};}
 // latestPublished: the published file re-read now, the raw JSON that passed SecQgv2.validate; any failure is null (as before).
 async function published(){try{return await data.peek(QGV2);}catch(_){return null;}}
 async function basisOf(p){if(!p)return null;try{return await TB().inputBasis(p);}catch(_){return null;}}
 // The draft's input basis: only when the re-read file is the file the page's scores were computed from (same as_of).
 async function basis({page}={}){const pg=await pageOf(page);let inputs=null;try{inputs=qgv.engineInputs(pg);}catch(_){inputs=null;}
  const p=await published();return p&&inputs&&inputs.as_of&&p.as_of===inputs.as_of?basisOf(p):null;}
 // The draft the rules give now (no write): TargetV1Builder.buildDraft with the page's result and the basis (basis() or null),
 // with the V source its pool's V came from.
 async function draft({date=today(),basis:b=null,page}={}){const{pg,args}=await builderArgs(page,date);return out({...TB().buildDraft({...args,basis:b,cfg:CFG()}),v_source:sourceOf(pg)});}
 // "규칙으로 초안 만들기": the new draft replaces the old one and clears the card answers. The old button asked for a second tap
 // when answers existed; here the caller passes reset:true after asking.
 function build(event,{date=today(),page,reset=false}={}){return action.run(event,'WRITE',async()=>{
  const before=readState();if(before.draft&&before.answers.length&&reset!==true)throw Error('TARGET_V1_ANSWERS_RESET');
  const pg=await pageOf(page),b=await basis({page:pg}),{args}=await builderArgs(pg,date),d={...TB().buildDraft({...args,basis:b,cfg:CFG()}),v_source:sourceOf(pg)};save({...readState(),draft:d,answers:[]});return out(d);});}
 // Every finalize blocker now, against the file re-read now (the old finalize click's check, shown before the user finalizes).
 async function blockers({date=today()}={}){const p=await published(),b=await basisOf(p),st=readState();return out({...TB().finalizeBlockers(st,{date,published:p,basis:b,cfg:CFG()}),v_source:draftSource(st)});}
 /* "TARGET v1 확정 저장" (target-v1-screen.js finalize click): re-read the published file now and re-check everything. A changed
    input basis on a usable file regenerates the draft (answers kept for the same names) when the page's scores are of that file,
    else the page must be reloaded. A saved version records the v_source its draft was built with (a draft without one: the page's
    engine_v_source.id); #391's builder writes the device id itself, and a different id is V_SOURCE_MISMATCH (nothing saved). */
 function finalize(event,{date=today(),page}={}){return action.run(event,'WRITE',async()=>{
  const B=TB(),cfg=CFG(),pg=await pageOf(page),p=await published(),b=await basisOf(p),st=readState();let check=B.finalizeBlockers(st,{date,published:p,basis:b,cfg});
  if(check.basis_changed&&check.check&&!check.check.reasons.some(r=>NO_REGEN.includes(r))){
   let computed=null,inputs=null;try{computed=qgv.forEngines(pg);inputs=qgv.engineInputs(pg);}catch(_){computed=null;}
   if(computed&&computed.v2_state==='READY'&&inputs&&inputs.as_of&&p.as_of===inputs.as_of){const catalog=await catalogNow();
    const r=B.regenerateDraft(st,{computed,inputs,universeCodes:await codesNow(),existing:TS().existingSymbols(catalog),date,basis:b,cfg}),next={...r.state,draft:{...r.state.draft,v_source:sourceOf(pg)}};
    save(next);check=B.finalizeBlockers(next,{date,published:p,basis:b,cfg});
    return out({outcome:'DRAFT_REGENERATED',carried:r.carried,fresh:r.fresh,blockers:check.blockers,check:check.check});}
   return out({outcome:'RELOAD_REQUIRED',blockers:check.blockers,check:check.check});}
  let next;try{next=B.finalize(st,{date,published:p,basis:b,cfg});}catch(e){if(e&&Array.isArray(e.blockers))return out({outcome:'BLOCKED',blockers:e.blockers,check:e.check||null});throw e;}
  const src=draftSource(st)||sourceOf(pg),versions=[...next.versions],last=versions[versions.length-1];
  if(last.v_source!==undefined&&last.v_source!==src)throw Error('V_SOURCE_MISMATCH');versions[versions.length-1]={...last,v_source:src};save({...next,versions});
  return out({outcome:'FINALIZED',version:versions[versions.length-1]});});}
 // A card answer (target-v1-screen.js card click): one judgement record in the playbook store, then the latest answer per name;
 // 반대 drops the name and the next-ranked one comes in (limits re-checked by the builder).
 function answer(event,{symbol,answer:kind,reason='',date=today()}={}){return action.run(event,'WRITE',()=>{
  const B=TB(),cfg=CFG(),st=readState(),sel=B.currentSelection(st,cfg),row=sel.rows.find(r=>r.symbol===symbol),next=B.answer(st,{symbol,answer:kind,reason,date},cfg),saved=next.answers[next.answers.length-1];
  PB().saveRecord(storage,B.judgementRecord({row,answer:kind,reason:saved.reason,date,id:'TV1-'+date+'-'+symbol+'-'+kind+'-'+Date.now()+'-'+Math.random().toString(36).slice(2,6)},cfg));save(next);
  const after=B.currentSelection(next,cfg);return out({symbol,answer:kind,added:after.rows.filter(r=>!sel.rows.some(x=>x.symbol===r.symbol)).map(r=>r.symbol),limits_ok:after.limits.ok===true});});}
 const ruleBDue=(date=today())=>TB().ruleBDue(readState(),date,CFG());
 // R-B (규칙 지수) selection on a due day (target-v1-screen.js mount ran it on open; here on the user's click). No partial start.
 function selectRuleB(event,{date=today(),page}={}){return action.run(event,'WRITE',async()=>{
  const B=TB(),cfg=CFG(),{pg,args}=await builderArgs(page,date),st=readState();if(args.computed.v2_state!=='READY')return out({state:'QGV2_NOT_READY'});if(!B.ruleBDue(st,date,cfg))return out({state:'NOT_DUE'});
  const eligible=B.universeRows({computed:args.computed,inputs:args.inputs,universeCodes:args.universeCodes,existing:args.existing,cfg}).filter(r=>!B.exclusions(r,cfg).length),seg=B.ruleBSegment(eligible,date,cfg);
  if(!seg.ready)return out({state:'NOT_READY',eligible:eligible.length});const{ready:_,...rest}=seg,row={...rest,v_source:sourceOf(pg)};save({...st,rule_b:[...st.rule_b,row]});return out({state:'SELECTED',date,names:row.rows.length,v_source:row.v_source});});}
 /* Set comparison (target-v1-screen.js load-compare click): daily closes of A (v0), R-B, R-C and the S&P 500 benchmark from the
    user's price tabs, missing tails fetched through the Worker and appended first (PriceStore.dailyCloses fetch:true, price view),
    then compareSets and the fixed review rule. The index values are price-derived: RAM only. */
 function compare(event,{date=today()}={}){return action.run(event,'SYNC',async signal=>{
  const B=TB(),cfg=CFG(),PS=need('PriceStore'),st=readState(),v0=TS().v0Weights(await catalogNow()),c=st.rule_c,version=c?st.versions.find(v=>v.version===c.version):null;
  const symbols=new Set([cfg.virtual_sets.benchmark.symbol,...Object.keys(v0),...st.rule_b.flatMap(s=>s.rows.map(r=>r.symbol)),...(version?version.rows:[]).map(r=>r.symbol)]),from=c&&c.start?c.start:date,closes={};
  for(const s of symbols){try{const x=await PS.dailyCloses(TS().priceSymbol(s),from,{view:priceView,fetch:true,signal});if(object(x)&&Object.keys(x).length)closes[s]=x;}catch(_){}}
  const cmp=B.compareSets({state:st,v0Weights:v0,closes,asOf:date,cfg});return Object.freeze({compare:cmp,review:B.reviewRule({compare:cmp,date,cfg})});});}
 // T-PRICE names (target-v1-screen.js sicLookup / scoringNames, not exported): TV1 judgement names with no price path; pending =
 // not yet added to the user's Prices_D, tracked = added. SIC from the public sec-qgv2.json records (TARGET rows skipped).
 function scoringNames(st,catalog){const inputs=data.get(QGV2),sic=new Map();let records=[];try{records=PB().read(storage).records;}catch(_){records=[];}
  for(const[code,r]of Object.entries(inputs&&object(inputs.records)?inputs.records:{})){if(code.startsWith('TARGET:'))continue;sic.set(key(code.slice(code.indexOf(':')+1)),r?.sic??null);}
  const all=TB().scoringNeeds(records,{have:(catalog&&catalog.instruments||[]).map(i=>i.ticker),sicOf:s=>sic.get(key(s))??null,cfg:CFG()}),added=new Set(st.price_symbols);
  return{pending:all.filter(n=>!added.has(n.price_symbol)),tracked:all.filter(n=>added.has(n.price_symbol))};}
 // The names and the confirm text the screen shows before syncScoringPrices (TargetV1Screen.confirmText: symbols only).
 async function scoringPending(){await data.ready();const names=scoringNames(readState(),await catalogNow());
  return out({pending:names.pending,tracked:names.tracked,confirm_text:names.pending.length?TS().confirmText(names.pending,CFG()):null});}
 // Series of the tracked names from the user's price tabs into the playbook scoring RAM (target-v1-screen.js refreshScoring): stored
 // rows only, through the facade ({} until a click read the tabs). Returns how many names got a series.
 async function refreshScoring(){await data.ready();const B=TB(),cfg=CFG(),P=PB(),names=scoringNames(readState(),await catalogNow());if(!names.tracked.length||!P.addScoringSeries)return 0;
  const closes={};for(const s of new Set([...names.tracked.flatMap(n=>[n.price_symbol,n.sector_symbol]),cfg.scoring_prices.benchmark])){try{const x=await prices.storeFacade.dailyCloses(s,null);if(object(x)&&Object.keys(x).length)closes[s]=x;}catch(_){}}
  const series={};for(const n of names.tracked){const s=B.scoringSeries(n,closes,cfg);if(s)series[n.symbol]=s;}P.addScoringSeries(series);return Object.keys(series).length;}
 /* T-PRICE add (target-v1-screen.js add click, after the user confirmed confirm_text): the names, their sector ETFs and the benchmark
    appended to the user's Prices_D (PriceStore.syncMany kind TV1, Worker allowlist only, price view), the symbols kept on this
    device (an allowlist refusal is not kept), then the scoring series read back into RAM. Counts and codes only. */
 // The tab sync is the next step of this click: a nested run that presents this action's signal (action.run {parent}).
 function syncScoringPrices(event){return action.run(event,'SYNC',async signal=>{
  await data.ready();const st=readState(),names=scoringNames(st,await catalogNow());if(!names.pending.length)return out({state:'NOTHING_PENDING'});
  const next=TB().addPriceSymbols(st,names.pending,CFG()),r=await prices.syncSymbols(event,next.price_symbols,'1d',{kind:'TV1',parent:signal});let scored=null;
  if(r&&r.state==='READY'){save({...next,price_symbols:next.price_symbols.filter(x=>!(r.results&&r.results[x]&&r.results[x].code==='WORKER_ALLOWLIST'))});scored=await refreshScoring();}
  return out({state:r?r.state:null,sync:r,scored});});}

 // ---------------------------------------------------------------- playbook (detail screen playbook, 6.1.x)
 function readPlaybook(){try{return PB().read(storage);}catch(e){if(e&&e.message==='READER_MISSING')throw e;throw Error('PLAYBOOK_INVALID');}}
 /* One company's facts as the old screens assembled them (app.js / PlaybookScreen.mount → prepareScores, heldSymbolsFor, factsFor).
    The news list is read first through the public view: prepareScores fills the structural-news RAM from DataRefresh's list of
    this generation, so through the score view it is a cached read, never a request. Scores: the shared page result with the
    page profile. ram (DeviceActual.ramView) and actual_pct are device RAM values (price-derived weights): display only. The old
    CompanyScreen is not loaded, so factsFor's v1 Q·G fallback (sec-qg-factors.json) is absent: Q·G come from the v2 result only. */
 async function facts(symbol,{date=today()}={}){
  const P=PB(),catalog=await catalogNow(),pg=await qgv.page();await data.list('news').catch(()=>null);await action.stores();
  const screens=data.screens(),idByTicker=new Map(idsOf(catalog).map(r=>[r.ticker,r.company_id])),prof=qgv.profile();
  const computed=await P.prepareScores(qgv.scoreView,{catalog,screens,idByTicker,scoreOptions:()=>({quotes:{},preset:prof.preset,gate:prof.gate,referenceRows:{}})});
  const heldSymbols=await P.heldSymbolsFor(priceView,catalog);let ram=null;try{ram=await need('DeviceActual').ramView(priceView,catalog);}catch(_){ram=null;}
  const prefs=store.prefs(),interests=prefs.value&&Array.isArray(prefs.value.interests)?[...prefs.value.interests]:[];
  return out({...P.factsFor(symbol,{catalog,screens,idByTicker,ram,date,computed,heldSymbols,storage,interests}),v_source:sourceOf(pg)});}
 /* openPanel's judgement step (playbook-screen.js openPanel), read only: the situation with this device's thesis event, hold and
    follow-up, the macro state, PlaybookEngine.evaluate, and the R1_FILING rule (a filing choice needs an EVIDENCE-grade invalidation
    event). openPanel also recorded the candidate signals at this point; that is record(event, judged) now (owner 2026-10-24: only on
    the user's click). recorded: whether record(event, this judgement) has written it (a fresh judgement is not recorded;
    recorded_reason JUDGEMENT_NOT_RECORDED until then, the screen says "기록 안 됨"). record() merges into that day's occurrences
    (PlaybookScreen.recordOccurrences keeps one per date, name and code), so recording a judgement again changes nothing.
    v_source: the facts' (or a given situation's) V source; null when the caller's situation names none. */
 const judged=new WeakSet(),recorded=new WeakSet();
 async function judge({symbol,situation=null,date=today()}={}){
  const E=need('PlaybookEngine'),PCFG=need('PlaybookConfigDefaults'),P=PB();await macroNow();
  const{v_source:vs=null,...base}=situation||await facts(symbol,{date}),stored=readPlaybook(),s={...base,symbol,date},ML=win.MacroLights,macro=ML&&typeof ML.current==='function'?ML.current():null;
  if(macro){s.macro_state=macro.state;s.macro_available_count=macro.available_count;}
  const ev=stored.theses[symbol]&&stored.theses[symbol].event;
  s.invalidation_triggered=ev&&ev.status==='OCCURRED'?true:ev&&ev.status==='NONE'?false:null;s.user_hold=!!stored.holds[symbol];s.followup_due=P.due(stored,date).some(r=>r.symbol===symbol);
  const judgement=E.evaluate(PCFG,s);
  if(ev&&ev.status==='OCCURRED'&&ev.grade!=='EVIDENCE'){const restrict=choices=>choices.map(ch=>ch.id==='R1_FILING'?{...ch,enabled:false,disabled_reasons:[...ch.disabled_reasons,'FILING_EVIDENCE_REQUIRED']}:ch);
   if(judgement.choices_by_code.R1)judgement.choices_by_code.R1=restrict(judgement.choices_by_code.R1);if(judgement.primary&&judgement.primary.code==='R1')judgement.choices=restrict(judgement.choices);}
  const j=copy({symbol,date,situation:s,judgement,code:judgement.primary&&judgement.primary.code?judgement.primary.code:'H1',v_source:typeof vs==='string'?vs:null});
  Object.defineProperties(j,{recorded:{enumerable:true,get:()=>recorded.has(j)},recorded_reason:{enumerable:true,get:()=>recorded.has(j)?null:'JUDGEMENT_NOT_RECORDED'}});
  deepFreeze(j);judged.add(j);return j;}
 // The occurrences openPanel wrote when it opened: the candidate signals, a structural-news E4, a 13F full-exit E4. Only from a
 // judge() result and only on the user's action. Returns that day's occurrences of the name (codes and reasons).
 function record(event,j){if(!judged.has(j))throw Error('JUDGEMENT_UNKNOWN');return action.run(event,'WRITE',()=>{const P=PB(),{symbol,date,situation:s,judgement}=j;
  P.recordOccurrences(storage,date,symbol,judgement.candidate_signals);if(s.structural_news)P.recordOccurrences(storage,date,symbol,[{code:'E4',reasons:['NEWS_STRUCTURAL_EVENT']}]);
  if(s.thirteenf_source_reason==='THIRTEENF_REPORTED_FULL_EXITS_3_PLUS')P.recordOccurrences(storage,date,symbol,[{code:'E4',reasons:[s.thirteenf_source_reason]}]);
  recorded.add(j);return out(readPlaybook().occurrences.filter(r=>r.date===date&&r.symbol===symbol));});}
 // E5: records whose follow-up day has come (PlaybookScreen.due); §16 portfolio limits of {symbol, sector, pct} rows.
 const due=(date=today())=>out(PB().due(readPlaybook(),date));
 const limits=(rows,cash)=>out(need('PlaybookEngine').portfolioLimits(need('PlaybookConfigDefaults'),rows,cash));

 // ---------------------------------------------------------------- virtual trading (6.1.5, 6.2, 6.3)
 const namesOf=catalog=>Object.fromEntries(idsOf(catalog).map(c=>[c.company_id,c.ticker]));
 const noCatalog=()=>Object.freeze({state:'NOT_AVAILABLE',reason_codes:Object.freeze(['PUBLIC_CATALOG_UNAVAILABLE']),sources:Object.freeze({}),ledgers:Object.freeze({})});
 /* app.js paintReport's open pass: VirtualTradingRunner.run on the price view with fetch:false, then PlaybookScreen.ingestRunner
    (scoring RAM). NOT_STARTED before the start date; NOT_AVAILABLE with OFF / REQUEST_INVALID / ORIGIN_UNAPPROVED / AUTH_REQUIRED
    unless private history is on, the approved Worker address is saved and Google is signed in; otherwise each symbol comes from
    the runner's RAM cache of this sign-in or the price tabs a click read (facade), else PRICE_NOT_FETCHED. No request except public
    files (forward ledger, classification). Sets B/C/D come from the user's ledger sheet, which P1 does not read. Holds prices: RAM. */
 async function stored({reportDate=seoulDay(),signal=null}={}){const catalog=await data.static(CATALOG);if(!catalog)return noCatalog();await action.stores();
  const result=await need('VirtualTradingRunner').run(priceView,{config:config(),catalog,reportDate,signal,fetch:false}),P=win.PlaybookScreen;if(P&&typeof P.ingestRunner==='function')P.ingestRunner(result,namesOf(catalog));return result;}
 // The 비교 table (app.js composeCompare): Set A plus the user's sets the caller passes as their ledger sheet definitions (none in
 // P1, so the table says COMPARE_NEEDS_TWO_SETS). Labels are the set kinds; the wording is the P2-6 screen's.
 function compareSets(result,{config:cfg=null,basis='KRW',defs=null}={}){const C=need('VirtualTradingCompare'),R=need('VirtualTradingRunner'),runCfg=cfg||need('VirtualTrading').defaultConfig(),r=object(result)?result:{};
  const entries=['SET_A','SET_B','SET_C','SET_D'].filter(k=>k==='SET_A'||(defs&&defs[k])).map(k=>{const{ledger,hits}=R.ledgerFor(r,k,runCfg),d=defs&&defs[k];return{id:d?d.id:k.toLowerCase(),kind:k,label:k,purpose:d?d.purpose:null,ledger,hits};});
  let types=null;try{types=C.typesFrom(data.screens()[TYPES]);}catch(_){types=null;}
  return C.build(entries,{indices:object(r.indices)?r.indices:{},sources:object(r.sources)?r.sources:{},basis,types});}
 // 9.2 forward validation, price free: the published ledger's daily Q·G summaries, evaluation status and calc_version segments
 // (never chained), and the observation evidence (ForwardValidation.qgSummary / rowEvaluation / segments / evidence).
 async function forward(){const FV=need('ForwardValidation'),p=await data.static(LEDGER);
  if(!p){const s=data.state(LEDGER);return out({state:s.state==='NOT_PUBLISHED'?'NOT_PUBLISHED':'NOT_AVAILABLE',reason:s.why,rows:[],comparison:[],segments:[],evidence:null});}
  const primary=p.schema_version===2?FV.V2_VERSION:FV.VERSION,rows=p.versions[primary],line=r=>({date:r.date,version:r.version,state:r.state,summary:FV.qgSummary(r),evaluation:FV.rowEvaluation(r)});
  return out({state:'LOADED',reason:null,status:p.status,as_of:p.as_of,start_date:p.start_date,primary,rows:rows.map(line),comparison:p.schema_version===2?p.versions[FV.VERSION].map(line):[],segments:FV.segments(rows),evidence:FV.evidence(p)});}
 /* Rehearsal (app.js go('REHEARSAL')): an in-memory engine run over the last sessions with the page's Q·G rows, never recorded;
    stored and RAM prices only here (fetch:false). Holds prices: RAM. app.js always passed QgvScores.judgmentRows of its own compute
    and that compute's basis as snapshot_basis; a page without a result (no usable sec-qgv2.json) does the same here: the old
    compute over the catalog identities and this generation's files gives the TARGET rows with null Q·G (BLOCKED snapshots) and
    the v2 basis. Any other page error is thrown (no silent run without Q·G rows). */
 async function rehearse({reportDate=seoulDay(),page,signal=null}={}){const catalog=await data.static(CATALOG);if(!catalog)return Object.freeze({result:noCatalog(),config:null});
  const QS=need('QgvScores'),pg=await pageOf(page);let computed=null;try{computed=qgv.forEngines(pg);}catch(e){if(!e||e.message!=='PAGE_NOT_READY')throw e;}
  if(!computed){const prof=qgv.profile();computed=QS.compute({identities:idsOf(catalog),publicScreens:data.screens(),preset:prof.preset,gate:prof.gate,referenceRows:{}});}
  const qg={...QS.judgmentRows(computed)};
  await action.stores();const o=await need('VirtualTradingSignals').rehearse(priceView,{config:config(),catalog,reportDate,signal,fetch:false,qgRows:qg});
  const result={...o.result,snapshot_basis:computed.default},P=win.PlaybookScreen;if(P&&typeof P.ingestRunner==='function')P.ingestRunner(result,namesOf(catalog));return{result,config:o.config};}
 /* The recording run (app.js paintReport with fetch:true: Worker histories, V history capture, ledger sheet writes, then the daily
    report model) is not in P1: its report model (daily-report.js is not loaded) and the V history timing (D-21) are decided with
    P2-6. Exported so a screen sees the function; it always refuses. */
 function run(){throw Error('NOT_IN_P1');}

 // ---------------------------------------------------------------- macro lights (4.1.4)
 // MacroLights.setPublic(screens) once per public data generation (app.js did it at boot and on every applied refresh), so
 // MacroLights.current() is the playbook's macro state. The device lights (SPY through the Worker) are a P2-4 click.
 let macroGen=null;
 async function macroNow(){try{await data.ready();}catch(_){return;}const ML=win.MacroLights,pub=data.publication();if(!ML||!pub||pub.generation===macroGen)return;macroGen=pub.generation;ML.setPublic(data.screens());}
 data.subscribe(d=>{if(d&&d.reason==='REFRESH')void macroNow();});
 async function current(){await macroNow();const ML=win.MacroLights,c=ML&&typeof ML.current==='function'?ML.current():null;return c?Object.freeze({...c}):null;}

 return Object.freeze({
  target:Object.freeze({state,basis,draft,build,blockers,finalize,answer,ruleBDue,selectRuleB,compare,scoringPending,refreshScoring,syncScoringPrices}),
  playbook:Object.freeze({facts,judge,record,due,limits}),
  virtual:Object.freeze({stored,compare:compareSets,forward,rehearse,run}),
  macro:Object.freeze({current})});
}
return Object.freeze({create});
});
