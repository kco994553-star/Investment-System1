"use strict";
let D,
  prefs = { version: 1, interests: [], groups: [] },
  storageOK = true,
  corruptStorage = false;
let identityCompanies=[],publicScreens={},publicCatalog=null,deviceCatalogPromise;
// Settings > 원자료 보기(개발자용): the company whose raw public cards are shown (the last company viewed; RAM only).
let rawDataCompany=null;
// Explicit public company selection for prompt imports. RAM only; never a quote or user form value.
let researchCompanyId=null;
function deviceCatalog() {
  if(!deviceCatalogPromise) deviceCatalogPromise=fetch('actual-catalog.json',{cache:'no-store'}).then(r=>{
    if(!r.ok) throw Error('PUBLIC_CATALOG_UNAVAILABLE');return r.json();
  }).catch(()=>{deviceCatalogPromise=null;throw Error('PUBLIC_CATALOG_UNAVAILABLE');});
  return deviceCatalogPromise;
}
// Price store core symbols: runner symbols (virtual trading: set A = TARGET v0, holdings, sets B–D from VirtualMeta, benchmarks/FX),
// TARGET v1 price symbols and the watchlist ★. Owner decision 2026-10-23: the device quote/chart range is ACTUAL holdings ∪ the
// watchlist ∪ TARGET v1 candidates (draft included), any company; the user's click (Settings → price store) reads that whole range.
// The app-open path (auto) adds nothing beyond what it read before this decision (no new automatic request).
async function priceStoreCore(auto=false){const core=await PriceStore.coreSymbols(window,{catalog:await deviceCatalog(),interests:DeviceWatchlist.allIds(prefs.interests)});let added=[];try{added=window.TargetV1Screen?TargetV1Screen.priceSymbols(window.PlaybookScreen,localStorage):[];}catch(_){added=[];}
 let range=[];if(!auto){try{range=(await deviceScope()).symbols;}catch(_){range=[];}}return [...new Set([...core,...added,...range])];}
/* Device quote / chart range (owner decision 2026-10-23, TA G2): ACTUAL holdings ∪ watchlist ∪ TARGET v1 candidates (draft
   included). Company page ids (TARGET alias or Universe code), their Worker symbols (allowlist only) and labels. Reads device
   storage only; no request. TARGET v0 is not part of it (set A and the v0 comparison read their own lists). */
let heldScopeIds=[];// ACTUAL holdings as TARGET aliases (the ACTUAL catalog), cached after each device read
function scopeIdList(){const W=DeviceWatchlist,ids=[];const add=id=>{if(typeof id==='string'&&id&&!ids.includes(id))ids.push(id);};
 for(const id of W.pageIds(prefs.interests))add(id);// watchlist: one page per issuer, then its other listings
 for(const i of prefs.interests)for(const id of W.entitiesOf(i))add(id);
 for(const id of heldScopeIds)add(id);for(const id of targetV1Ids())add(id);return ids;}
async function refreshHeldScope(){const before=heldScopeIds.join();try{const catalog=await deviceCatalog(),held=window.PlaybookScreen?.heldSymbolsFor?await PlaybookScreen.heldSymbolsFor(window,catalog):null;
  heldScopeIds=(held||[]).map(t=>DeviceWatchlist.IDS[t]).filter(Boolean);}catch(_){}
  // Holdings changed since the last read and a chart is on screen: rebuild it for the new range (prices still load only on click).
  if(heldScopeIds.join()!==before&&D&&document.querySelector('[data-private-history],[data-technical-symbol],[data-uc-chart],[data-history-settings-status]'))render();return heldScopeIds;}
window.addEventListener("hashchange",()=>{if(D)void refreshHeldScope();});
async function deviceScope(){await refreshHeldScope();const ids=scopeIdList(),symbols=ids.map(id=>PrivateHistory.providerSymbol(id)).filter(Boolean);
 return{ids,symbols:[...new Set(symbols)],has:id=>ids.includes(id)};}
// TARGET v1 candidates on this device: the draft's candidate table and the confirmed versions (Universe codes / TARGET aliases).
function targetV1Ids(){const out=[];try{const S=window.TargetV1Screen,B=window.TargetV1Builder;if(!S||!window.PlaybookScreen)return out;const st=S.readState(PlaybookScreen,localStorage),W=DeviceWatchlist;
 const byTicker=t=>{if(typeof t!=='string')return null;const tid=W.IDS[t];if(tid)return tid;for(const ex of['NYSE','NASDAQ','BATS']){const code=ex+':'+t;if(W.listingOf(code))return code;}return null;};
 const rows=[...(st.draft&&B?B.candidates(st.draft):[]),...(st.versions||[]).flatMap(v=>Array.isArray(v.rows)?v.rows:[])];
 for(const r of rows){const id=r&&typeof r.code==='string'&&W.listingOf(r.code)?(Object.keys(W.TARGET).find(k=>W.TARGET[k][0]===r.code)||r.code):byTicker(r&&r.symbol);if(id&&!out.includes(id))out.push(id);}}catch(_){}return out;}
PrivateHistory.setScope({has:id=>scopeIdList().includes(id),list:()=>scopeIdList().map(id=>({id,label:DeviceWatchlist.tickerOf(id)||id}))});
let valuationInputsPromise=null;
function valuationInputs(){if(!valuationInputsPromise)valuationInputsPromise=DeviceValuation.load(window);return valuationInputsPromise;}
// The S04/S05 price badge shows the same device quote state as the value card (no extra request); RAM only, never the price.
let companyQuote={id:null,quote:null};
function paintValue(route,id,quote=null){const host=document.querySelector('#company-value');if(host)void CompanyScreen.mountValue(host,{locale:appSettings.display_locale,id,ticker:company(id)?.ticker||PrivateHistory.symbolFor(id),catalogPromise:deviceCatalog(),inputsPromise:valuationInputs(),quote,compact:route==='company',
  onQuote:q=>{companyQuote={id,quote:q};const badge=$('#content [data-badge="price"]');if(badge)badge.outerHTML=CompanyScreen.priceBadge(q,appSettings.display_locale);}});}
function attachDeviceActual(selector,input) {
  const host=document.querySelector(selector),locale=appSettings.display_locale;
  if(!host) return;
  deviceCatalog().then(catalog=>{
    if(!host.isConnected) return;
    return input?DeviceActual.mount(host,{catalog,locale}):DeviceActual.summary(host,{catalog,locale});
  }).catch(()=>{
    if(host.isConnected) host.textContent=locale==='en-US'?'ACTUAL NOT_AVAILABLE · Local holdings could not be opened.':'ACTUAL NOT_AVAILABLE · 기기 보유 데이터를 열 수 없습니다.';
  });
}
function attachDeviceApiSettings() {
  const host=document.querySelector('#device-api-settings'),locale=appSettings.display_locale;
  if(!host) return;
  deviceCatalog().then(catalog=>{
    if(host.isConnected) return DeviceActual.settings(host,{catalog,locale});
  }).catch(()=>{
    if(host.isConnected) host.textContent=locale==='en-US'?'API OFF · Device settings unavailable.':'API 꺼짐 · 기기 설정을 열 수 없습니다.';
  });
}
function attachGoogleSheetSettings() {
  const host=document.querySelector('#google-sheet-settings'),locale=appSettings.display_locale;
  if(!host) return;
  const clientId=window.InvestmentAppConfig?.googleSheetsClientId || '';
  deviceCatalog().then(catalog=>{
    if(host.isConnected) return GoogleSheetQuotes.mount(host,{catalog,locale,clientId});
  }).catch(()=>{
    if(host.isConnected) host.textContent=locale==='en-US'?'Device quote import settings unavailable.':'기기 시세 불러오기 설정을 열 수 없습니다.';
  });
}
function actual() {
  return heading('DEVICE ACTUAL',appSettings.display_locale==='en-US'?'ACTUAL holdings':'ACTUAL 보유 입력')+
    '<a href="#portfolio">'+(appSettings.display_locale==='en-US'?'← Portfolio':'← 포트폴리오')+'</a><div id="device-actual-root" aria-live="polite"></div>';
}
const KEY = "investment.web.v1.personal";
let appSettings=AppLanguage.settings(), settingsWritable=true, searchIndex;
const t=key=>AppLanguage.text(key,appSettings.display_locale);
const term=key=>AppLanguage.term(key,appSettings.display_locale);
const label=e=>AppLanguage.fallback(e?.localized_names,appSettings.display_locale,e?.canonical_label || "");
// Render-time research guard (G3). Presentation only: data.json is not rewritten, no data state is
// added, nothing is recomputed. Constants mirror producers/contract.py @ f8af596 exactly (SECTION_NAMES
// L23, PUBLISHED_STATES L26, RESEARCH_STATUSES L28-30; rejection rule L197-202). The assembler writes
// the methodology at <section>.producer.methodology (assembler.py L31, L47). research_state.status is
// the same lifecycle on persisted records (P01 publication/extractors.py copies it verbatim and
// predicate.py checks it against the same RESEARCH_STATUSES). tests/test_web_research_guard.py pins this.
// The validation half of the same rule (contract.py L194-199, VALIDATION_STATUSES L25) is mirrored by
// validationMarker below.
const SECTION_NAMES=Object.freeze(["universe","qgv","technical","macro","portfolio","leaderboard","news","relationships","changes"]);
const PUBLISHED_STATES=Object.freeze(["LIVE","FROZEN_SNAPSHOT"]);
const RESEARCH_STATUSES=Object.freeze(["IDEA","PROVISIONAL","PROVISIONAL_INITIAL_PRIOR","PROVISIONAL_RESEARCH","RESEARCH"]);
const VALIDATION_STATUSES=Object.freeze(["PASS","FAIL","NOT_RUN"]);
const WITHHELD_REASON="게시 승인이 없는 연구·잠정 결과라 표시하지 않습니다.";
// Production-shaped state presentation. Presentation only: the values below are read from what the bundle
// already persists and are never merged back into D, data.json or the Evidence view.
// FRESHNESS mirrors producers/freshness.py L17 exactly (tests/test_web_state_presentation.py pins this). The
// Web adds no TTL, threshold or usable_until rule: it shows the freshness the assembler persisted at
// <section>.producer.freshness (assembler.py L28) or producer_manifest.sections.<section>.freshness (L70), and
// keeps the existing view-time rule of app.js 9156aea (a LIVE section whose expires_at has passed is STALE).
const FRESHNESS=Object.freeze(["FRESH","STALE","NOT_USABLE","NOT_APPLICABLE"]);
// The only expires_at strings handed to Date.parse: date, 'T', hh:mm[:ss[.fraction]], then Z or +hh:mm/-hh:mm.
// This covers datetime.isoformat() of an aware datetime (what producers persist; the assembler copies it verbatim;
// only a sub-minute UTC offset, written +hh:mm:ss, falls outside and fails closed) and its Z spelling. In this form
// Date.parse and contract.parse_ts read the same instant (Date.parse drops digits below the millisecond, so never a
// later one). It is a shape check only: no TTL, threshold or clock rule is added.
const EXPIRES_AT=/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d{1,9})?)?(Z|[+-]\d{2}:\d{2})$/;
const FRESHNESS_LABEL=Object.freeze({FRESH:"만료 전",STALE:"만료 후, 최신 아님",NOT_USABLE:"사용 기한 경과, 표시 보류"});
const NOT_USABLE_REASON="사용 기한(usable_until)이 지난 데이터라 표시하지 않습니다.";
const META_LABEL=Object.freeze({reason_code:"사유 코드",as_of:"생산자 데이터 시점",methodology:"방법론",freshness:"신선도",counts:"커버리지 집계"});
let META={};
const metaText=v=>typeof v==="string" && v.trim()?v:null;
// Identifiers are displayed only in their identifier shape; anything else (free text, long or multi-line values)
// is omitted, never truncated or rewritten: a reason_code must be a code, a methodology id/version a short token.
const REASON_CODE=/^[A-Z][A-Z0-9_]{0,63}$/;
const metaCode=v=>typeof v==="string" && REASON_CODE.test(v)?v:null;
const metaToken=v=>typeof v==="string" && v.length>0 && v.length<=64 && !/\s/.test(v)?v:null;
const metaObject=v=>v && typeof v==="object" && !Array.isArray(v)?v:{};
// A count is displayed under its key only when the key is code/token shaped; any other key (free text, long,
// multi-line) omits that entry, never truncated or rewritten.
const COUNT_KEY=/^[A-Za-z][A-Za-z0-9_]{0,63}$/;
function coverageCounts(p) {
  // Integer counts exactly as persisted (validation.*_count, coverage_counts maps); nothing is summed or derived.
  const v=metaObject(p.validation),out=[];
  for(const map of [p.coverage_counts,v.coverage_counts]) for(const [k,n] of Object.entries(metaObject(map))) if(COUNT_KEY.test(k) && Number.isInteger(n)) out.push(k+"="+n);
  for(const [k,n] of Object.entries(v)) if(k.endsWith("_count") && COUNT_KEY.test(k) && Number.isInteger(n)) out.push(k+"="+n);
  return out.join(", ") || null;
}
function persistedMeta(bundle,name) {
  const p=metaObject(bundle[name]?.producer),m=metaObject(metaObject(metaObject(bundle.producer_manifest).sections)[name]),method=metaObject(p.methodology);
  const fresh=[[p.freshness,"producer.freshness"],[m.freshness,"producer_manifest.sections."+name+".freshness"]].filter(([f])=>FRESHNESS.includes(f));
  // Two persisted copies that disagree: show the more restrictive one (fail closed), never a newer computation.
  const pick=fresh.find(([f])=>f==="NOT_USABLE") || fresh.find(([f])=>f==="STALE") || fresh[0] || [null,null];
  return {freshness:pick[0],freshness_path:pick[1],reason_code:metaCode(p.reason_code) || metaCode(m.reason_code),as_of:metaText(p.as_of),
    methodology:[method.id,method.version].map(metaToken).filter(Boolean).join(" / ") || null,counts:coverageCounts(p)};
}
const VALIDATION_WITHHELD_REASON="생산자 검증(validation)이 PASS가 아니라 표시하지 않습니다.";
function validationMarker(s) {
  // contract.py L194-199: a LIVE/FROZEN_SNAPSHOT snapshot is rejected unless validation is an object whose status
  // is exactly "PASS"; a missing validation object or status is rejected as well (L33, L195). The assembler
  // persists that object at <section>.producer.validation (assembler.py L32, L47). A section without a producer
  // block (legacy Track A universe, default and DEMO builds) carries no producer validation and is left as is.
  if(!("producer" in s) || s.producer?.validation?.status==="PASS") return null;
  const status=s.producer?.validation?.status;
  // Only contract status values are echoed; anything else is shown as "not provided".
  return {path:"producer.validation.status",status:VALIDATION_STATUSES.includes(status)?status:null,reason:VALIDATION_WITHHELD_REASON};
}
function researchMarker(s) {
  const status=s.producer?.methodology?.status;
  if(RESEARCH_STATUSES.includes(status)) return {path:"producer.methodology.status",status};
  const pending=[s];
  while(pending.length) {
    const v=pending.pop();
    if(!v || typeof v!=="object") continue;
    if(!Array.isArray(v) && RESEARCH_STATUSES.includes(v.research_state?.status)) return {path:"research_state.status",status:v.research_state.status};
    for(const x of Array.isArray(v)?v:Object.values(v)) pending.push(x);
  }
  return null;
}
function guardSections(bundle) {
  // A LIVE/FROZEN_SNAPSHOT section that the producer contract would reject (producer validation not PASS, or a
  // research marker) is withheld in the existing NOT_AVAILABLE presentation; its values never reach the view.
  // Every other section is passed through as is.
  const view={...bundle};
  META={};
  for(const name of SECTION_NAMES) {
    const s=bundle[name];
    if(!s || typeof s!=="object") continue;
    META[name]=persistedMeta(bundle,name);
    // Same order as contract.py L197-202: validation status first, then methodology/research status.
    const marker=PUBLISHED_STATES.includes(s.state) && (validationMarker(s) || researchMarker(s));
    if(marker) view[name]={state:"NOT_AVAILABLE",as_of:null,source:null,reason:marker.reason || WITHHELD_REASON,data:null,withheld:{section:name,claimed_state:s.state,...marker}};
    // A section that still carries values although its persisted freshness is NOT_USABLE is withheld the same
    // way (the assembler itself never emits this; it publishes NOT_AVAILABLE + EXPIRED_NOT_USABLE instead).
    else if(s.state!=="NOT_AVAILABLE" && META[name].freshness==="NOT_USABLE")
      view[name]={state:"NOT_AVAILABLE",as_of:null,source:null,reason:NOT_USABLE_REASON,data:null,withheld:{section:name,claimed_state:s.state,path:META[name].freshness_path,status:"NOT_USABLE",reason:NOT_USABLE_REASON}};
  }
  return view;
}
function withheldNote(s) {
  return s.withheld?`<p class="empty" data-withheld="${esc(s.withheld.section)}">${esc(t(s.withheld.reason || WITHHELD_REASON))}</p><div class="meta" data-source-original>${esc(s.withheld.path)}: ${esc(s.withheld.status ?? t("미제공"))}</div>`:"";
}
function freshnessOf(name,s) {
  const persisted=META[name]?.freshness;
  if(persisted==="NOT_USABLE") return "NOT_USABLE";
  if(s.state!=="LIVE") return null;
  // FRESH needs an expires_at that this browser parses and that is still ahead of its clock. An expires_at that is
  // absent, not a string or rejected by Date.parse (ISO forms Python's fromisoformat accepts, e.g. basic format,
  // week dates or comma fractions) cannot be compared with the clock: fail closed as STALE, whatever freshness was
  // persisted (producers/freshness.py: a LIVE snapshot is never silently current).
  // Date.parse only sees the strict form (EXPIRES_AT); any other string Python accepts (e.g. a '(' or U+0000
  // date/time separator, which Date.parse reads as midnight of that date, a later instant) is STALE too.
  const expires=typeof s.expires_at==="string" && EXPIRES_AT.test(s.expires_at)?Date.parse(s.expires_at):NaN;
  if(!Number.isFinite(expires) || expires<=Date.now() || persisted==="STALE") return "STALE";
  return "FRESH";
}
function freshnessBadge(f) {
  return f?` <span class="badge freshness ${f}" data-freshness="${f}">${f} · ${esc(t(FRESHNESS_LABEL[f]))}</span>`:"";
}
function producerMeta(name,s) {
  // Withheld/unavailable sections only, and only the fields the bundle persisted. Absent fields add nothing.
  const m=META[name];
  if(!m || s.state!=="NOT_AVAILABLE" || s.withheld) return "";
  const rows=["reason_code","as_of","methodology","freshness","counts"].filter(k=>m[k]);
  return rows.length?`<p class="meta producer-meta" data-producer-meta="${esc(name)}">${rows.map(k=>`<span data-meta="${k}">${esc(t(META_LABEL[k]))}: <span data-source-original>${esc(m[k])}</span></span>`).join(" · ")}</p>`:"";
}
function updateSettings(patch) {
  appSettings=AppLanguage.settings({...appSettings,...patch});
  if(settingsWritable) {try {AppLanguage.write(localStorage,appSettings);} catch(e) {settingsWritable=false;}}
  render(); paintGlobalSearch();
  if(!settingsWritable) notice(t("설정을 저장할 수 없습니다."));
}
function settingsUI() {
  return heading("SETTINGS",t("설정"))+`<div class="chips data-badges" data-settings-badges><span class="badge">${t("읽기 전용")}</span><span class="badge">${t("이 휴대폰에만 저장")}</span><span class="badge">${t("주문 기능 없음")}</span></div><div id="google-first-setup"></div><section class="card">
  <label for="display-locale">${t("표시 언어")}</label><select id="display-locale"><option value="ko-KR" ${appSettings.display_locale==="ko-KR"?"selected":""}>한국어</option><option value="en-US" ${appSettings.display_locale==="en-US"?"selected":""}>English</option></select>
  <p>${t("표시 언어는 계산 결과에 영향을 주지 않습니다.")}</p>
  <label for="source-language">${t("뉴스 원문 언어")}</label><select id="source-language">${[["all",t("전체 언어")],["ko",t("한국어 원문")],["en",t("영어 원문")]].map(([v,k])=>`<option value="${v}" ${appSettings.source_language===v?"selected":""}>${t(k)}</option>`).join("")}</select>
  <p>${t("원문 언어는 뉴스 필터만 변경합니다.")}</p></section>
  <div id="ops-status"></div><section class="card" id="device-pwa-settings"></section><section class="card"><h2>${t("금융 용어")}</h2>${["free_cash_flow","drawdown","operating_margin"].map(k=>`<p>${term(k)}</p>`).join("")}</section><section class="card"><h2>${appSettings.display_locale==='en-US'?'Device backup':'기기 백업·불러오기'}</h2><p>${appSettings.display_locale==='en-US'?'Interests, groups, portfolio, profiles, investor stars, playbook records and language settings. Quotes, tokens, sheet IDs and Worker address are excluded.':'관심 기업·그룹·포트폴리오·프로필·투자자 ★·플레이북 기록·언어 설정을 함께 보관합니다. 시세·토큰·시트 ID·Worker 주소는 제외합니다.'}</p><label class="small"><input type="checkbox" id="device-backup-user-objects"> ${appSettings.display_locale==='en-US'?'Include user-written objects (chart notes·scenarios, macro estimate history)':'사용자 작성 객체 포함 (차트 노트·시나리오, 매크로 추정 기록)'}</label> <button id="device-backup-export">${t("내보내기")}</button><label>${t("가져오기")} <input id="device-backup-import" type="file" accept="application/json"></label></section><div id="google-sheet-settings"></div><div id="private-history-settings"></div><div id="price-store-settings"></div><div id="private-trades-settings"></div><div id="private-universe-settings"></div><div id="device-api-settings"></div><section class="card" id="company-logo-settings"></section><section class="card" id="tradingview-settings"></section>`+rawDataUI();
}
/* Settings > 원자료 보기(개발자용), collapsed by default (owner decision 2026-10-14). User screens show results only; the raw
   public cards that used to sit at the bottom of the company screen live here: SEC Q·G leaf scores (sec-qg-factors.json),
   price-free company types (company-types-pricefree.json) and estimated filing windows (sec-filing-windows.json), per company.
   The company defaults to the last company viewed (RAM) and can be changed with the selector. */
function rawDataIds(){const ids=new Set();for(const f of ['sec-qg-factors.json','company-types-pricefree.json','sec-filing-windows.json']){const c=publicScreens[f]?.data?.companies;if(c&&typeof c==='object')for(const id of Object.keys(c))ids.add(id);}
  if(!ids.size)for(const c of identityCompanies)ids.add(c.company_id);return [...ids];}
function rawDataCompanyId(){const ids=rawDataIds();return ids.includes(rawDataCompany)?rawDataCompany:(ids[0]||null);}
function rawDataUI(){
  const en=appSettings.display_locale==='en-US',ids=rawDataIds(),chosen=rawDataCompanyId(),name=id=>{const c=company(id);return c&&c.ticker?c.ticker:String(id).toUpperCase();};
  return `<details class="card" id="raw-data-viewer" data-raw-data><summary>${en?'Raw data (developer)':'원자료 보기(개발자용)'}</summary><p class="small">${en?'Raw public inputs for checking only: SEC Q·G leaf scores, price-free company types and estimated filing windows. Screens show results only.':'확인용 원자료입니다: SEC Q·G 개별 점수, 가격 불필요 유형, 실적 예상 시기. 사용자 화면에는 결과만 보여 줍니다.'}</p><label for="raw-data-company">${en?'Company':'기업'}</label> <select id="raw-data-company" data-raw-company>${ids.map(id=>`<option value="${esc(id)}"${id===chosen?' selected':''}>${esc(name(id))}</option>`).join('')}</select><div id="public-qg"></div><div id="public-types"></div><div id="public-filings"></div>${window.TargetV1Screen?TargetV1Screen.rawDataHtml():''}</details>`;
}
function mountRawData(){const id=rawDataCompanyId();for(const kind of ['qg','types','filings'])PublicScreens.mount($('#public-'+kind),publicScreens,{kind,companyId:id||undefined,locale:appSettings.display_locale});}
// Company search (TARGET directory + public Universe504 codes): identity only, no prices/caps/ranks (GSQ-010).
let publicEntities=[],universeDirectory=null,universeDirectoryPromise=null;
// KR-NAMES (2026-10-18): reviewed company-names-ko.json, display and search only (never a score, rank or identity input).
// It adds names to the entities above; which companies are searchable still comes from the directory and the shares file.
let companyNames=null;
const companyNamesPromise=(window.EntitySearch?.loadNames?EntitySearch.loadNames(window):Promise.resolve(null)).then(n=>{companyNames=n;
  if(!n) return;
  // Issuer keys of Universe codes (IA-7): the CIK column of the reviewed table; old code keys in the watchlist map to their issuer.
  if(DeviceWatchlist.useNames(n)&&!corruptStorage){const m=DeviceWatchlist.migrate(prefs);if(m.changed){if(prefsV0Raw===null)try{prefsV0Raw=localStorage.getItem(KEY);}catch(_){}prefs=m.prefs;}}if(searchIndex){rebuildSearchIndex();paintGlobalSearch();}
  const [route]=location.hash.slice(1).split("/");if(route==="company" && D) render();});
function companyTitle(id,ticker){return EntitySearch.companyTitle(companyNames?.get(id)||null,ticker,appSettings.display_locale);}
function rebuildSearchIndex() {
  const codes={};if(universeDirectory?.state==="READY") for(const [code,r] of Object.entries(universeDirectory.records)) codes[code]=r.company_id;
  const ko=window.SearchUI?.KO_NAMES||{},named=e=>!e.names&&Object.hasOwn(ko,e.canonical_id)?{...e,localized_names:{"ko-KR":ko[e.canonical_id]}}:e;
  try {searchIndex=EntitySearch.createIndex([...publicEntities,...EntitySearch.companyEntities(identityCompanies,codes,companyNames).map(named)]);}
  catch(_) {searchIndex=EntitySearch.createIndex(publicEntities);}
}
function ensureUniverseDirectory() {
  if(universeDirectoryPromise || !window.SecUniverseShares) return universeDirectoryPromise;
  universeDirectory={state:"LOADING"};
  universeDirectoryPromise=DataRefresh.shares(window).then(inputs=>{
    universeDirectory=inputs?{state:"READY",as_of:inputs.as_of,records:inputs.publicShares}:{state:"NOT_AVAILABLE",reason:"SEC_UNIVERSE_SHARES_NOT_PUBLISHED"};
  }).catch(e=>{universeDirectory={state:"NOT_AVAILABLE",reason:["SEC_UNIVERSE_SHARES_INVALID","SEC_UNIVERSE_SHARES_SCHEMA_NEWER"].includes(e?.message)?e.message:"SEC_UNIVERSE_SHARES_UNAVAILABLE"};}).then(()=>{
    if(!searchIndex) return;rebuildSearchIndex();paintGlobalSearch();
    const [route,id]=location.hash.slice(1).split("/");if(route==="company" && /%3A|:/i.test(id || "")) render();
  });
  return universeDirectoryPromise;
}
function universeCode(id) {return /^(NYSE|NASDAQ|BATS):[A-Z0-9][A-Z0-9.\-]{0,15}$/.test(id)?id:null;}
function universeDetail(code) {
  const en=appSettings.display_locale==='en-US',ticker=code.slice(code.indexOf(":")+1),r=universeDirectory?.state==="READY"?universeDirectory.records[code]:null;
  const head=`<a class="small" href="#companies">${t("← 기업 목록")}</a>`+heading("UNIVERSE504",CompanyLogos.html(code,40)+esc(ticker),esc(code));
  if(!universeDirectory || universeDirectory.state==="LOADING") return head+`<p role="status" data-universe-company="LOADING">${en?'Loading public Universe504 identity…':'공개 Universe504 정보를 불러오는 중…'}</p>`;
  // A newer data format than this page reads (#289 item 3): ask for a reload instead of showing nothing.
  const why=universeDirectory.reason==="SEC_UNIVERSE_SHARES_SCHEMA_NEWER"?(en?'The data format is newer. Reload the page':'자료 형식이 새 버전입니다. 새로고침하세요'):universeDirectory.reason;
  if(!r) return head+`<section class="card" data-universe-company="NOT_AVAILABLE"><p class="empty">NOT_AVAILABLE · ${esc(why || "NOT_IN_UNIVERSE")}</p></section>`;
  // IDENTITY_CONFLICT_WITHDRAWN (UNI-WITHDRAWN, 2026-10-17): the code's earlier observation is stopped; no count is shown or used.
  const reason=x=>x==='IDENTITY_CONFLICT_WITHDRAWN'?(en?'withdrawn: identity conflict':'식별 충돌로 사용 중지'):x;
  const rows=[[en?'SEC shares state':'SEC 주식수 상태',r.state+(r.reason_codes.length?' · '+r.reason_codes.map(reason).join(' · '):'')],[en?'Shares outstanding (SEC cover)':'발행주식수(SEC 표지)',r.shares===null?'NOT_AVAILABLE':Number(r.shares).toLocaleString(appSettings.display_locale)],[en?'Measured':'기준일',r.measurement_date||'—'],[en?'Form':'서식',r.form||'—'],[en?'Share-class basis':'주식 종류 기준',r.share_class_basis],['CIK',r.cik||'—'],[en?'Public file as of':'공개 파일 기준',universeDirectory.as_of]];
  return head+`<section class="card" data-universe-company="${esc(r.state)}"><div class="chips"><span class="badge">Universe504</span><span class="badge">${en?'Name not published':'이름 미공개'}</span><span class="badge">${en?'Price-free':'가격 없음'}</span></div><dl>${rows.map(([k,v])=>`<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join("")}</dl><p class="small">${en?'Price, market cap, rank and QGV: NOT_AVAILABLE on public screens (GSQ-010). The M3 cap rank is shown only on S06 after reading your Universe sheet on this device (RAM only).':'가격·시가총액·순위·QGV: 공개 화면에서는 NOT_AVAILABLE (GSQ-010). M3 시총 순위는 S06에서 내 기기의 Universe 시트를 읽은 뒤 메모리에서만 표시됩니다.'}</p><a href="#leaderboard">${en?'S06 Company research →':'S06 기업 연구 →'}</a></section>`;
}
// The search box itself (combobox, rows, keys, recent searches) lives in home-screen.js (SearchUI); app.js owns the index.
function paintGlobalSearch() {
  if(!searchIndex) return;
  window.investmentSearch=(query,options)=>searchIndex.search(query,options);
  if($("#global-search")?.value.trim()) void ensureUniverseDirectory();
  window.SearchUI?.refresh({universe:universeDirectory?.state||null});
}
function entityDetail(key) {
  const cut=key.indexOf(":"),type=key.slice(0,cut),id=key.slice(cut+1),e=searchIndex.resolve(type,id);
  if(!e) return heading("SEARCH",t("일치하는 항목이 없습니다."));
  let body=heading(e.entity_type,esc(label(e)),esc(e.canonical_label));
  if(e.entity_type==="INDUSTRY") {
    const related=D.companies.filter(c=>c.industry_id===id || (id==="semiconductor" && ["Semicap","Semiconductor"].includes(searchIndex.resolve("COMPANY",c.company_id)?.industry)));
    body+=`<section class="card"><h2>${t("관련 기업")}</h2><p>${t("산업 분류가 제공된 기업만 표시합니다.")}</p><ul class="list">${related.map(row).join("")}</ul></section>`;
  } else if(e.entity_type==="MACRO") body+=block("macro",t("거시지표"),`<p>${fmt(D.macro.data?.indicators?.[id])}</p>`);
  else if(e.entity_type==="INVESTOR") body+=`<section class="card"><p>${t("Investor-QGV 미연결")}</p><p>${t("표시 메타데이터만 등록되어 있습니다.")}</p></section>`;
  return body+evidence(e);
}
function syncShell() {
  document.documentElement.lang=appSettings.display_locale;document.title="Investment System · "+t("오늘");
  document.querySelectorAll("[data-i18n]").forEach(e=>e.textContent=t(e.dataset.i18n));
  document.querySelector("nav").setAttribute("aria-label",t("주요 화면"));
  $("#global-search").placeholder=t("기업·산업·투자자·거시지표 검색");
  $("#global-search").setAttribute("aria-label",t("전체 검색"));
}
const $ = (s) => document.querySelector(s),
  esc = (v) =>
    String(v ?? "—").replace(
      /[&<>"']/g,
      (c) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;",
        })[c],
    );
const fmt = (v) =>
  v == null
    ? t("미제공")
    : typeof v === "number"
      ? v.toLocaleString(appSettings.display_locale, { maximumFractionDigits: 2 })
      : esc(v);
const pct = (v) => (v == null ? t("미제공") : fmt(v * 100) + "%");
function notice(s) {
  $("#notice").textContent = s;
}
// Records written before the IA-7 keys (TARGET company_id) stay on this device under V0_KEY, copied once before the first
// write of the issuer-keyed form; the working copy reads the old keys through DeviceWatchlist.migrate (decision 2026-10-23).
const V0_KEY="investment.web.v1.personal-v0";let prefsV0Raw=null;
function save() {
  if (corruptStorage) {
    notice(
      t("기존 설정 손상: 원본을 보존했습니다. 현재 변경은 내보내기로 보관하세요."),
    );
    return;
  }
  try {
    if (prefsV0Raw !== null && localStorage.getItem(V0_KEY) === null) localStorage.setItem(V0_KEY, prefsV0Raw);
    prefsV0Raw = null;
    localStorage.setItem(KEY, JSON.stringify(prefs));
    storageOK = true;
    notice(t("저장되었습니다."));
  } catch (e) {
    storageOK = false;
    notice(t("이 브라우저에 저장할 수 없습니다. 내보내기로 보관하세요."));
  }
}
function validatePrefs(p) {
  if (
    p.version !== 1 ||
    !Array.isArray(p.interests) ||
    !Array.isArray(p.groups) ||
    p.interests.some((i) => typeof i !== "string") ||
    p.groups.some(
      (g) =>
        typeof g.id !== "string" ||
        typeof g.name !== "string" ||
        !g.name.trim() ||
        !Array.isArray(g.members) ||
        g.members.some((i) => typeof i !== "string"),
    )
  )
    throw Error(t("관심기업 파일 형식 오류"));
  return p;
}
function load() {
  try {
    const s = localStorage.getItem(KEY);
    if (s) {const m=DeviceWatchlist.migrate(validatePrefs(JSON.parse(s)));prefs=m.prefs;prefsV0Raw=m.changed?s:null;}
  } catch (e) {
    storageOK = false;
    corruptStorage = true;
    notice(
      t("저장된 설정을 읽을 수 없습니다. 원본을 덮어쓰지 않고 임시로 시작합니다."),
    );
  }
}
function company(id) {
  return D.companies.find((c) => c.company_id === id) || identityCompanies.find(c=>c.company_id===id);
}
function byIssuer(id) {
  return D.companies.find((c) => c.issuer_id === id);
}
// ★ = this device's watchlist, keyed by Issuer (IA-7; DeviceWatchlist). Any company with an issuer key (TARGET alias, Universe
// code with a CIK) can be starred; one issuer is one entry for all its listings. No issuer key: the star is disabled (no guess).
function star(id) {
  const on=DeviceWatchlist.watched(prefs,id),key=DeviceWatchlist.issuerOf(id),name=esc(company(id)?.ticker || DeviceWatchlist.tickerOf(id) || id);
  if(!key) return `<button class="star" data-star="${esc(id)}" disabled aria-disabled="true" data-star-state="ISSUER_UNRESOLVED" aria-label="${name} ${t("관심기업")} · NOT_AVAILABLE">☆</button>`;
  return `<button class="star" data-star="${esc(id)}" aria-label="${name} ${t("관심기업")}" aria-pressed="${on}">${on?"★":"☆"}</button>`;
}
function toggleInterest(id){const key=DeviceWatchlist.issuerOf(id);if(!key)return false;
  prefs.interests=prefs.interests.includes(key)?prefs.interests.filter(i=>i!==key):[...prefs.interests,key];
  if(!prefs.interests.includes(key))prefs.groups.forEach(g=>(g.members=g.members.filter(i=>i!==key)));
  save();return true;}
function companyName(id){return EntitySearch.companyName(companyNames?.get(id)||null,appSettings.display_locale)||company(id)?.name||"";}
function state(s) {
  const name=SECTION_NAMES.find(n=>D[n]===s);
  return `<div class="state"><span class="badge ${esc(s.state)}">${esc(s.state)}</span>${freshnessBadge(freshnessOf(name,s))} <span class="meta">${esc(s.as_of || t("시점 미제공"))}</span></div><div class="meta" data-source-original>${esc(s.source || (s.data===null?"":t("출처 미제공")))}</div>${withheldNote(s)}${producerMeta(name,s)}`;
}
function evidence(v) {
  return `<details><summary>${t("Evidence(근거) · 원본 보기")}</summary><pre data-source-original>${esc(JSON.stringify(v,null,2))}</pre></details>`;
}
function block(name,title,body) {
  const s=D[name];
  return `<section class="card"><h2>${title}</h2>${state(s)}${s.withheld?"":s.data===null?'<p class="empty">'+esc(AppLanguage.fallback(s.reason_localized,appSettings.display_locale,t(s.reason || t("미제공"))))+"</p>":body}${s.data!==null?evidence(s):""}</section>`;
}
function heading(k,title,subtitle="") {
  return `<div class="eyebrow">${k}</div><h1>${title}</h1>${subtitle?'<p class="muted">'+subtitle+"</p>":""}`;
}
function row(c) {
  const e=searchIndex.resolve("COMPANY",c.company_id);
  return `<li class="item"><a href="#company/${encodeURIComponent(c.company_id)}">${CompanyLogos.html(c.ticker,20)}<span class="ticker">${esc(c.ticker)}</span><div class="muted">${esc(label(e) || c.name)}${c.market_cap_rank?" · "+t("시총 #")+c.market_cap_rank:""}${c.demo?" · DEMO":""}</div></a>${star(c.company_id)}</li>`;
}
function summaryFor(name,id) {
  const s=D[name],v=s.data?.[id];
  return `<section class="card"><h2>${name==="qgv"?"QGV":t("Technical(기술적 분석)")}</h2>${state(s)}${v?`<dl>${(name==="qgv"?["Q_score","G_score","V_score","total_score","confidence","coverage_state"]:["regime","execution_zone","invalidation"]).map(k=>`<dt>${esc(term(k))}</dt><dd>${typeof v[k]==="number"?fmt(v[k]):esc(AppLanguage.fallback(v.presentation?.[k],appSettings.display_locale,AppLanguage.status(v[k] ?? t("미제공"),appSettings.display_locale)))}</dd>`).join("")}</dl>${evidence(v)}`:'<p class="empty">'+t("이 기업의 Snapshot 미제공")+"</p>"}</section>`;
}
// Home is the search start (home-screen.js). The previous home dashboard cards live on #brief, unchanged.
function home() {return HomeScreen.html({locale:appSettings.display_locale});}
function brief() {
  const held=D.portfolio.data?.holdings || [];
  return heading("YOUR DAILY BRIEF",t("오늘의 투자 화면"),t("중요한 변화부터 확인하고, 근거까지 따라가세요."))+
  `<div id="tv-ticker-tape"></div><div class="home-dashboard" data-home-dashboard><section class="card" data-integrated-judgement><h2>${t("통합 판단")}</h2><p class="small">${esc(t("규칙 잠정 버전"))}</p><dl>${[["QGV","qgv"],[t("기술"),"technical"],[t("매크로"),"macro"]].map(([label,name])=>`<dt>${esc(label)}</dt><dd><span class="badge ${esc(D[name].state)}">${esc(D[name].state)}</span></dd>`).join("")}</dl><p data-judgement-result>${esc(t(["qgv","technical","macro"].every(n=>D[n].data!==null)?"세 시스템 결과를 나란히 확인하세요.":"자료가 부족해 통합 판단을 만들지 않습니다."))}</p><p class="small">${esc(t("매수·매도 지시 아님, 주문 기능 없음"))}</p></section>`+
  `<section class="card hero"><div class="row"><h2>${t("Portfolio(포트폴리오)")}</h2><a href="#portfolio">${t("자세히 →")}</a></div><div class="metric">${D.portfolio.data?held.length+" "+t("종목 보유"):t("연결 대기")}</div><p class="muted">${D.portfolio.data?esc(D.portfolio.data.role || t("제공된 Snapshot")):t("실제 보유·평가금액·수익률을 연결하면 여기서 확인합니다.")}</p>${state(D.portfolio)}</section>
  <div class="grid home-grid">${block("changes",t("오늘 / 최근 주요 변화"),`<p>${esc(AppLanguage.fallback(D.changes.data?.summary_localized,appSettings.display_locale,D.changes.data?.summary || ""))}</p>`)}${block("macro",t("Macro(거시환경)"),`<p>${esc(AppLanguage.status(D.macro.data?.state || "",appSettings.display_locale))} · ${esc(D.macro.data?.regime || "")}</p>`)}</div>
  <section class="card"><h2>${t("Attention(확인 필요)")}</h2><p class="small">${D.universe.state==="FROZEN_SNAPSHOT"?t("기업 목록은")+" "+esc(D.universe.as_of)+" "+t("과거 스냅샷입니다. 최신 시세·분석이 아닙니다."):t("출처와 데이터 시점을 확인하세요.")}</p><div class="chips"><a href="#companies">${t("관심기업")} ${prefs.interests.length} →</a><a href="#leaderboard">Leaderboard →</a></div></section>
  <section class="card" data-daily-reports><h2>${appSettings.display_locale==='en-US'?'Daily reports':'일일보고서'}</h2><div class="chips"><a href="#report/mock" data-report-link="mock">${appSettings.display_locale==='en-US'?'Paper trading daily report':'모의투자 일일보고서'} →</a><a href="#report/real" data-report-link="real">${appSettings.display_locale==='en-US'?'Investment daily report':'투자 일일보고서'} →</a></div><p class="small">${appSettings.display_locale==='en-US'?'Virtual records only · no orders':'가상 기록 · 주문 기능 없음'}</p></section>
  <details><summary>${t("분석 · 뉴스 · 관계 변화 더보기")}</summary><div class="grid">${block("qgv",t("QGV 변화"),"<p>"+t("변화량은 upstream changes가 제공할 때만 표시합니다.")+"</p>")}${block("technical",t("Technical 변화"),"<p>"+t("최근 신호는 기업 상세에서 확인하세요.")+"</p>")}${block("news",t("관심기업 뉴스"),'<a href="#news">'+t("뉴스 열기 →")+"</a>")}${block("relationships",t("Relationship changes(관계 변화)"),'<a href="#news">'+t("관계망 열기 →")+"</a>")}</div></details>`+
  `<section class="card" data-system-flow><h2>${t("시스템")}</h2><div class="hub-grid">${[["1","QGV","#qgv","qgv"],["2",t("기술적 분석"),"#technical","technical"],["3",t("매크로"),"#macro","macro"],["8",t("검증·연구"),"#validation",null]].map(([n,label,href,name])=>`<a class="card hub-card" href="${href}"><h3><span class="flow-number">${n}</span> ${esc(label)}</h3><span class="badge ${name?esc(D[name].state):"NOT_AVAILABLE"}">${name?esc(D[name].state):"NOT_AVAILABLE"}</span></a>`).join("")}</div></section>
  <section class="card" data-data-basis><h2>${t("데이터 기준")}</h2><dl><dt>${t("목표 비중 버전")}</dt><dd id="home-target-version">—</dd><dt>${t("QGV 기준 버전")}</dt><dd>${esc(t("v2 · PROVISIONAL"))}</dd><dt>${t("시세·환율")}</dt><dd>${esc(t("이 기기에서만 입력·계산"))}</dd><dt>${t("보유 정보")}</dt><dd>${esc(t("이 기기에만 저장"))}</dd></dl><a href="#settings">${t("데이터 운영 상태 →")}</a></section></div>`;
}
// S06 ('leader') starts from the remembered view state of this tab (leaderboardView) and adds a text search and the
// 'QGV v2 순' sort (design canvas S06: 정렬 QGV 높은 순, the default). S15 ('watch') is unchanged.
function directoryFilters(prefix,watch=false) {
 const v=prefix==='leader'?leaderboardView:null,en=appSettings.display_locale==='en-US',pick=(a,b)=>a===b?" selected":"";
 const sorts=(v?[["qgv",en?"QGV v2 (high first)":"QGV v2 순"]]:[]).concat([[watch?"added":"ticker",watch?t("추가한 순"):t("티커 순")],["name",t("기업명 순")],["favorites",t("관심기업 우선")]],v?LeaderboardScreen.sortOptions(en):[]);
 return `<div class="chips">${v?`<input type="search" id="leader-query" aria-label="${en?"Search companies":"기업 검색"}" placeholder="${en?"Ticker or name":"티커 또는 기업명"}" value="${esc(v.query)}">`:""}<label><input type="checkbox" id="${prefix}-interest" ${watch?"checked disabled":v?.interest?"checked":""}>${t("관심기업만")}</label>${v?`<label data-leader-target-filter><input type="checkbox" id="leader-target" ${v.target?"checked":""}>${en?"TARGET only (hides rows, ranks unchanged)":"TARGET만 (행만 숨김 · 순위 그대로)"}</label>`:""}<select id="${prefix}-group" aria-label="${t("그룹 필터")}"><option value="">${t("모든 그룹")}</option>${prefs.groups.map(g=>`<option value="${esc(g.id)}"${pick(v?.group,g.id)}>${esc(g.name)}</option>`).join("")}</select><select id="${prefix}-sort" aria-label="${t("정렬")}">${sorts.map(([k,l])=>`<option value="${k}"${pick(v?.sort,k)}>${esc(l)}</option>`).join("")}</select></div>`;
}
function companyGroups(id){const key=DeviceWatchlist.keyOf(id);return `<p class="small">${t("관심·그룹은 이 기기에만 저장됩니다.")}</p>${prefs.groups.length?prefs.groups.map(g=>`<label><input type="checkbox" data-group="${esc(g.id)}" data-member="${esc(key)}" ${g.members.includes(key)?"checked":""} ${prefs.interests.includes(key)?"":"disabled"}>${esc(g.name)}</label>`).join(""):`<a href="#watchlist">${t("그룹 관리 →")}</a>`}`;}
function weekFilings(){const p=publicScreens["sec-filing-windows.json"],rows=p?.data?.companies;if(!rows)return "NOT_AVAILABLE";const known=DeviceWatchlist.pageIds(prefs.interests).filter(id=>rows[id]&&rows[id].state!=="NOT_AVAILABLE");if(!known.length)return "NOT_AVAILABLE";const en=appSettings.display_locale==="en-US",week=Date.now()-7*86400000,status=known.map(id=>PublicScreens.earningsStatus(rows[id])).filter(Boolean),estimated=status.filter(s=>s.status==="ESTIMATED"&&s.window.days_until_start<=6).length,confirmed=status.filter(s=>s.status==="CONFIRMED"&&Date.parse(s.date+"T00:00:00Z")>=week).length;return (estimated+confirmed)+" · "+esc(en?"estimated "+estimated+" · confirmed "+confirmed:"추정 "+estimated+" · 확인 "+confirmed)+" · "+esc(t("예상 시기 · 확정일 아님"));}
// '공시·확정' (SEC 8-K, DART when its reader exists) + '뉴스·신호' (news-signals.json) in one chronological list; one lazy public read each.
// S07 lists all (or the company in context), S15 the interest companies. Nothing here changes any score.
// The files are read once per publication by DataRefresh and shared with the 4.3 tree example (D6).
function paintDisclosures(host,companyIds,emptyText){if(!host||typeof SecDisclosures!=="object")return;const dart=typeof DartDisclosures==="object"&&!$(host.id==="news-disclosures"?"#news-dart-disclosures":"#watch-dart-disclosures")?DartDisclosures:null,news=typeof NewsSignals==="object"?NewsSignals:null;
 Promise.all([DataRefresh.list(window,'sec'),news?DataRefresh.list(window,'news'):null,dart?DataRefresh.list(window,'dart'):null]).then(([sec,signals,dartPayload])=>{if(!host.isConnected)return;const options={locale:appSettings.display_locale,companyIds,emptyText};if(news)news.mount(host,{sec,news:signals,dart:dartPayload},Object.assign(options,{secApi:SecDisclosures,dartApi:dart,...newsTiers()}));else SecDisclosures.mount(host,sec,options);});}
// Importance tiers for the news/disclosure list: interests = this device's watchlist (prefs), held = companies in the
// portfolio snapshot already in page memory (D.portfolio, the same set paintNews uses). Device ACTUAL holdings live in
// IndexedDB and are not read here; without a snapshot in memory held stays null (the list then says "holdings not connected").
function newsTiers(){const rows=D&&D.portfolio&&D.portfolio.data&&Array.isArray(D.portfolio.data.holdings)?D.portfolio.data.holdings:null;
 return{interests:DeviceWatchlist.allIds(prefs.interests),held:rows?rows.map(h=>h&&h.company_id).filter(x=>typeof x==='string'):null};}
// DART disclosures (042700): same '공시·확정' record format as SEC 8-K, own public file; one lazy read. S07 all (or the company in context), S15 interest companies.
function paintDartDisclosures(host,companyIds,emptyText){if(!host||typeof DartDisclosures!=="object")return;DataRefresh.list(window,'dart').then(p=>{if(host.isConnected)DartDisclosures.mount(host,p,{locale:appSettings.display_locale,companyIds,emptyText});});}
function watchlist(){return heading("WATCHLIST",t("관심 기업"))+directoryFilters("watch",true)+`<p class="meta">${t("이 휴대폰에만 저장 · 백업으로 이동")}</p><div class="grid">${["평균 QGV","재평가 신호","이번 주 실적","새 뉴스"].map(x=>`<section class="card"><h2>${t(x)}</h2><p${x==="이번 주 실적"?" data-week-filings":""}>${x==="이번 주 실적"?weekFilings():"NOT_AVAILABLE"}</p></section>`).join("")}</div><ul class="list" id="watchlist-company-list"></ul><div id="watch-disclosures"></div><div id="watch-dart-disclosures"></div><a href="#leaderboard/interest">${t("리더보드에서 관심 기업만 보기 →")}</a><details><summary>${t("관심기업 · Groups(그룹) 관리")}</summary>${groupsUI()}</details>`;}
function companies() {
  return heading("COMPANIES",t("기업 탐색"))+`<input type="search" id="search" aria-label="${t("기업 검색")}" placeholder="${t("티커 또는 기업명 검색")}"><div class="chips"><label><input type="checkbox" id="only-interest"> ${t("관심기업만")}</label><select id="group-filter" aria-label="${t("그룹 필터")}"><option value="">${t("모든 그룹")}</option>${prefs.groups.map(g=>`<option value="${esc(g.id)}">${esc(g.name)}</option>`).join("")}</select></div><select id="company-sort" aria-label="정렬"><option value="ticker">티커 순</option><option value="name">기업명 순</option><option value="favorites">관심기업 우선</option></select><p class="meta">${D.universe.withheld?esc(D.universe.state)+" · "+esc(t(D.universe.withheld.reason || WITHHELD_REASON)):esc(D.universe.as_of)+" · FROZEN_SNAPSHOT / DEMO"}</p><ul class="list" id="company-list"></ul><button id="more-companies">${t("더보기")}</button><details><summary>${t("관심기업 · Groups(그룹) 관리")}</summary>${groupsUI()}</details>`;
}
function groupsUI() {
  return `<p class="muted">${t("이 기기의 브라우저에 저장됩니다. 즐겨찾기와 관심기업은 같은 목록입니다.")}</p><form id="new-group"><label for="group-name">${t("새 그룹 이름")}</label><div class="row"><input id="group-name" required maxlength="60" placeholder="${t("예: 반도체")}"><button>${t("그룹 만들기")}</button></div></form><div id="groups">${prefs.groups.map(g=>`<div class="group"><b>${esc(g.name)}</b> <span class="muted">${g.members.length} ${t("개")}</span><div class="row"><input aria-label="${t("그룹 이름")} ${esc(g.name)}" data-rename-input="${esc(g.id)}" value="${esc(g.name)}" maxlength="60"><button data-rename="${esc(g.id)}">${t("이름 변경")}</button><button data-delete="${esc(g.id)}">${t("그룹 삭제")}</button></div>${prefs.interests.map(id=>{const page=DeviceWatchlist.primaryOf(id)||id;return `<label><input type="checkbox" data-group="${esc(g.id)}" data-member="${esc(id)}" ${g.members.includes(id)?"checked":""}> ${esc(company(page)?.ticker || DeviceWatchlist.tickerOf(page) || id)}</label>`;}).join("")}</div>`).join("")}</div><div class="toolbar"><button id="export">${t("내보내기")}</button><label>${t("설정 병합 가져오기")} <input type="file" id="import" accept="application/json"></label></div>`;
}
// Public M2 sidecar is separate from published snapshots and prompt context.
let secReported=null;
let m2Candidates={display_state:'NOT_AVAILABLE',companies:{}};
function guardM2Candidates(value) {
  const fail=()=>{throw Error('M2_CANDIDATE_INVALID');};
  const need=v=>{if(!v)fail();};
  const keys=(v,list)=>need(v&&typeof v==='object'&&!Array.isArray(v)&&Object.keys(v).sort().join('|')===[...list].sort().join('|'));
  const hash=(v,p='')=>need(typeof v==='string'&&new RegExp('^'+p+'[0-9a-f]{64}$').test(v));
  const clock=v=>{need(typeof v==='string'&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$/.test(v)&&Number.isFinite(Date.parse(v)));return Date.parse(v);};
  const number=(v,max=100)=>need(v===null||(typeof v==='number'&&Number.isFinite(v)&&v>=0&&v<=max));
  const ids={asml:'ASML',lrcx:'LRCX',klac:'KLAC',nvda:'NVDA',amd:'AMD',avgo:'AVGO',qcom:'QCOM',intc:'INTC',msft:'MSFT',googl:'GOOGL',amzn:'AMZN',rtx:'RTX',stry:'SYK',etn:'ETN',hubb:'HUBB',gev:'GEV',rok:'ROK'};
  const reasons=['RECEIPT_INTEGRITY_FAILURE','ORIGINAL_REPLAY_MISMATCH','ANNUAL_FORM_REQUIRED','ACQUISITION_AFTER_CUTOFF','M1_NOT_AVAILABLE','AVAILABILITY_AFTER_CUTOFF','UNRESOLVED_CURRENT_FACT_AMBIGUITY','INCOMPLETE_QG','REPLAY_OR_NORMALIZED_INPUT_FAILURE'];
  try {
    need(value.contract==='PUBLIC_SEC_QG_CANDIDATES'&&value.version===1);
    if(value.display_state==='NOT_AVAILABLE') {
      keys(value,['contract','version','display_state','reason_code','companies']);
      keys(value.companies,[]);need(value.reason_code==='M2_INPUT_NOT_CONNECTED');return value;
    }
    const flags={candidate_only:true,prices_used:false,publication_approved:false,publication_eligible:false,real_data_verified:false,full_pit_historical:false};
    keys(value,['contract','version','display_state','candidate_id','as_of','evaluated_at','input_kind','synthetic_inputs',...Object.keys(flags),'research_status','publication_grant','scope_basis','public_500_rank','method_sha256','n_calculated','n_unavailable','companies']);
    need(value.display_state==='RESEARCH_CANDIDATE'&&Object.entries(flags).every(([k,v])=>value[k]===v));
    need(typeof value.synthetic_inputs==='boolean'&&value.input_kind===(value.synthetic_inputs?'SYNTHETIC':'OBSERVED_UNVERIFIED'));
    need(value.research_status==='PROVISIONAL_RESEARCH'&&value.publication_grant==='NONE'&&value.scope_basis==='EXPLICIT_RECEIPTS_US17_SUBSET'&&value.public_500_rank===false);
    hash(value.candidate_id,'sec_m2_');hash(value.method_sha256);const cutoff=clock(value.as_of);need(cutoff<=clock(value.evaluated_at));
    need(value.companies&&typeof value.companies==='object'&&!Array.isArray(value.companies));
    let calculated=0;const receipts=new Set();
    for(const [id,r] of Object.entries(value.companies)) {
      need(Object.hasOwn(ids,id));keys(r,['company_id','ticker','status','reason_codes','receipt_id','snapshot_id','source','coverage','Q_score','G_score','V_score','V_status']);
      need(r.company_id===id&&r.ticker===ids[id]&&['CALCULATED','NOT_AVAILABLE'].includes(r.status));
      const ready=r.status==='CALCULATED';calculated+=Number(ready);
      need(r.V_score===null&&r.V_status==='NOT_AVAILABLE');number(r.Q_score);number(r.G_score);
      need(ready?(r.Q_score!==null&&r.G_score!==null):(r.Q_score===null&&r.G_score===null));
      need(Array.isArray(r.reason_codes)&&r.reason_codes.every(v=>reasons.includes(v))&&(ready?r.reason_codes.length===0:r.reason_codes.length>0));
      hash(r.receipt_id);need(!receipts.has(r.receipt_id));receipts.add(r.receipt_id);
      if(r.snapshot_id!==null)hash(r.snapshot_id,'sec_m2_qgv_');need(!ready||r.snapshot_id!==null);
      if(r.source!==null){
        keys(r.source,['receipt_sha256','acquired_at','original_availability']);hash(r.source.receipt_sha256);const acquired=clock(r.source.acquired_at),a=r.source.original_availability;
        keys(a,['available_at','basis','precision','historical_first_publication']);need(a.basis==='OBSERVED_PUBLIC_API_UPPER_BOUND'&&a.precision==='CONSERVATIVE'&&a.historical_first_publication===false);
        if(a.available_at!==null)clock(a.available_at);need(!ready||(acquired<=cutoff&&a.available_at!==null&&clock(a.available_at)<=cutoff));
      }need(!ready||r.source!==null);
      if(r.coverage!==null){keys(r.coverage,['Q_observed_weight','G_observed_weight','native_coverage','weights_renormalized']);number(r.coverage.Q_observed_weight,1);number(r.coverage.G_observed_weight,1);need(r.coverage.Q_observed_weight!==null&&r.coverage.G_observed_weight!==null&&r.coverage.weights_renormalized===false&&['READY','PARTIAL','BLOCKED','SYNTHETIC'].includes(r.coverage.native_coverage));}need(!ready||r.coverage!==null);
    }
    need(Number.isInteger(value.n_calculated)&&value.n_calculated===calculated&&Number.isInteger(value.n_unavailable)&&value.n_unavailable>=Object.keys(value.companies).length-calculated&&calculated+value.n_unavailable>=1&&calculated+value.n_unavailable<=17);
    return value;
  } catch (_) {return {display_state:'NOT_AVAILABLE',companies:{}};}
}
function m2Panel(id,companyIds) {
  const en=appSettings.display_locale==='en-US';
  const title=en?'Q/G research candidates':'Q/G 연구 후보';
  const badge=en?'Uncalibrated · No prices':'보정 전·가격 미포함';
  const disclosure=en?'V NOT_AVAILABLE · No publication approval · Not a 500-company ranking':'V NOT_AVAILABLE · 게시 승인 없음 · 500개 기업 순위 아님';
  const rows=(id?(Object.hasOwn(m2Candidates.companies,id)?[m2Candidates.companies[id]]:[]):Object.values(m2Candidates.companies)).filter(r=>!companyIds||companyIds.includes(r.company_id));
  const row=r=>`<article class="m2-row" data-m2-company="${esc(r.company_id)}"><h3><a href="#company/${encodeURIComponent(r.company_id)}">${esc(r.ticker)}</a>${star(r.company_id)}</h3><dl class="m2-scores">${['Q','G','V'].map(k=>`<dt>${k}</dt><dd data-score="${k}">${r[k+'_score']===null?'NOT_AVAILABLE':esc(String(r[k+'_score']))}</dd>`).join('')}</dl><p class="meta">${esc(r.status)}${r.reason_codes.length?' · '+r.reason_codes.map(esc).join(' · '):''}</p>${evidence(r)}</article>`;
  return `<section class="card m2-candidates" data-m2-candidates><h2>${title}</h2><p><span class="badge">${badge}</span></p><p class="small">${disclosure}</p>${m2Candidates.display_state==='RESEARCH_CANDIDATE'?`<p class="meta"><strong>${m2Candidates.synthetic_inputs?'SYNTHETIC · '+(en?'Test inputs':'시험 입력'):'OBSERVED_UNVERIFIED · '+(en?'Unverified research':'미검증 연구')}</strong> · ${esc(m2Candidates.as_of)}</p>${rows.length?rows.map(row).join(''):'<p>NOT_AVAILABLE</p>'}<details><summary>${en?'Candidate provenance':'후보 출처'}</summary><pre>${esc(JSON.stringify({...m2Candidates,companies:undefined},null,2))}</pre></details>`:`<p class="empty">NOT_AVAILABLE · ${en?'M2 Q/G candidate input is not connected.':'M2 Q/G 후보 입력이 연결되지 않았습니다.'}</p>`}</section>`;
}

function detail(id) {
  const c=company(id);
  if(!c && universeCode(id)) {void ensureUniverseDirectory();return window.UniverseCompany?UniverseCompany.html(id,{locale:appSettings.display_locale,screens:publicScreens,shares:universeDirectory,quotes:qgv2Quotes,names:companyNames,starHtml:star(id)}):universeDetail(id);}
  const candidate=Object.hasOwn(m2Candidates.companies,id)?m2Candidates.companies[id]:null;
  const historySymbol=PrivateHistory.symbolFor(id);
  if((!c || c.identity_only) && (candidate || historySymbol)) return CompanyScreen.summary({locale:appSettings.display_locale,id,screens:publicScreens,scores:leaderScores(),priceBasis:leaderBasis,quote:companyQuote.id===id?companyQuote.quote:null,
    headerHtml:`<div class="row">${heading("COMPANY RESEARCH",CompanyLogos.html(candidate?.ticker || historySymbol || c?.ticker || id,40)+esc(companyTitle(id,candidate?.ticker || historySymbol || c?.ticker || "")),esc(c?.name || ""))}${star(id)}</div>`+namesBlock(id),groupsHtml:companyGroups(id),candidateHtml:m2Panel(id)});
  if(!c) return heading("COMPANIES",t("기업을 찾을 수 없습니다."))+'<a href="#companies">'+t("기업 목록 →")+"</a>";
  const h=D.portfolio.data?.holdings?.find(r=>r.company_id===id),e=searchIndex.resolve("COMPANY",id);
  return `<a class="small" href="#companies">${t("← 기업 목록")}</a><div class="row">${heading("COMPANY DETAIL",CompanyLogos.html(c.ticker,40)+esc(companyTitle(id,c.ticker)),esc(label(e) || c.name))}${star(id)}</div>${namesBlock(id)}<div id="private-history-chart"></div><div id="sec-reported-panel"></div><div class="grid">${summaryFor("qgv",id)}${summaryFor("technical",id)}</div>`+
  block("macro",t("Macro exposure / context(거시 노출)"),`<p>${esc(D.macro.data?.regime || "")}</p><p>${t("기업 노출:")} ${esc(D.macro.data?.exposures?.[id] || t("미제공"))}</p>`)+
  `<section class="card"><h2>${t("Portfolio status(보유 상태)")}</h2>${state(D.portfolio)}<p>${h?t("Snapshot에 포함 · 비중")+" "+(Number.isFinite(h.actual_weight)?pct(h.actual_weight):"NOT_AVAILABLE"):D.portfolio.data?t("제공된 Snapshot에 없음"):t("실제 보유 상태 미제공")}</p>${h && Number.isFinite(h.target_weight)?`<p class="small" data-weight-kind="TARGET">TARGET · ${t("모델 비중")} ${pct(h.target_weight)}</p>`:""}${h?evidence(h):""}</section><section class="card"><h2>${t("News / Relationships(뉴스·관계)")}</h2>${state(D.news)}<a href="#news/${encodeURIComponent(id)}">${t("이 기업의 뉴스·관계망 확인 →")}</a></section>${evidence(c)}`;
}
// English (SEC) name, Korean name with its status and source, aliases and share class of a company page (KR-NAMES).
function namesBlock(id){return window.UniverseCompany?.namesHtml?UniverseCompany.namesHtml(companyNames?companyNames.get(id):undefined,appSettings.display_locale):"";}
function analysis(id,tab=null) {
  const c=company(id),candidate=Object.hasOwn(m2Candidates.companies,id)?m2Candidates.companies[id]:null,historySymbol=PrivateHistory.symbolFor(id);
  if(!c && !candidate && !historySymbol) return heading("COMPANIES",t("기업을 찾을 수 없습니다."))+'<a href="#companies">'+t("기업 목록 →")+"</a>";
  const ticker=candidate?.ticker || historySymbol || c?.ticker || "";
  return CompanyScreen.analysis({locale:appSettings.display_locale,id,ticker,tab,quote:companyQuote.id===id?companyQuote.quote:null,screens:publicScreens,scores:leaderScores(),headerHtml:`<div class="row">${heading("COMPANY ANALYSIS",CompanyLogos.html(ticker||id,40)+esc(ticker),esc(c?.name || ""))}${star(id)}</div>`});
}
function paintPortfolio() {
  const host=$("#portfolio-screen");
  if(!host) return;
  const run=()=>{
    if(!host.isConnected) {document.removeEventListener("device-actual-changed",run);return;}
    const locale=appSettings.display_locale,idByTicker=new Map(identityCompanies.map(r=>[r.ticker,r.company_id]));
    deviceCatalog().then(async catalog=>{
      const ram=await DeviceActual.ramView(window,catalog);
      if(host.isConnected) PortfolioScreen.paint(host,{locale,catalog,ram,screens:publicScreens,idByTicker,virtual:virtualShadow});
    }).catch(()=>{if(host.isConnected) PortfolioScreen.paint(host,{locale,catalog:null,ram:{state:"NOT_AVAILABLE",reason:"READ_FAILED",stale:false,quote_as_of:null,rows:[],themes:[]},screens:publicScreens,idByTicker,virtual:virtualShadow});});
  };
  document.addEventListener("device-actual-changed",run);
  run();
}
function portfolio() {
  const p=D.portfolio.data;
  return heading("PORTFOLIO",t("내 포트폴리오"))+`<div id="portfolio-screen">${PortfolioScreen.shell(appSettings.display_locale,virtualShadow)}</div>`+block("portfolio",t("보유 현황"),`<p>${esc(p?.role || "")}</p><dl><dt>${t("수익률")}</dt><dd>${pct(p?.return)}</dd><dt>${t("평가금액")}</dt><dd>${fmt(p?.market_value)} ${esc(p?.currency || "")}</dd><dt>${t("Exposure(노출)")}</dt><dd>${esc(p?.exposure?JSON.stringify(p.exposure):t("미제공"))}</dd></dl><ul class="list">${(p?.holdings || []).map(h=>`<li class="item"><a href="#company/${encodeURIComponent(h.company_id)}"><b>${esc(h.ticker)}</b><div class="muted">${t("실제 비중")} ${Number.isFinite(h.actual_weight)?pct(h.actual_weight):"NOT_AVAILABLE"} · ${t("수익률")} ${pct(h.return)}</div>${Number.isFinite(h.target_weight)?`<div class="small" data-weight-kind="TARGET">TARGET · ${t("모델 비중")} ${pct(h.target_weight)}</div>`:""}</a>${star(h.company_id)}</li>`).join("")}</ul>`)+
  `<div class="grid">${block("qgv",t("QGV context(QGV 맥락)"),'<a href="#companies">'+t("기업별 분석 →")+"</a>")}${block("technical",t("Technical context(기술적 분석 맥락)"),'<a href="#companies">'+t("기업별 신호 →")+"</a>")}${block("macro",t("Macro context(거시 맥락)"),`<p>${esc(D.macro.data?.regime || "")}</p>`)}</div><a href="#news">${t("중요 뉴스·관계 변화 →")}</a>`;
}
function leaderboard() {
  const l=D.leaderboard.data;
  return heading("LEADERBOARD",appSettings.display_locale==='en-US'?"Company research":"기업 연구")+
  `<details><summary>${appSettings.display_locale==='en-US'?'My device':'내 기기 기준'}</summary><div id="private-subset-root"></div><p class="small" id="universe-price-time" data-universe-price-time></p></details>`+'<section class="fn-sec fn-filters" data-fn="2.1.3" aria-labelledby="lb-fn-2-1-3">'+LeaderboardScreen.fnHeadHtml('FILTER',appSettings.display_locale)+directoryFilters('leader')+'<div id="leader-classification-filters"></div>'+LeaderboardScreen.filterNoteHtml(appSettings.display_locale)+'</section>'+'<p class="small leader-summary" id="leader-summary" data-leaderboard-summary role="status"></p><div id="leaderboard-screen"></div><div id="v-coverage-root"></div><p class="small">고정 대상 기업의 이름·코드 · 가격·공식 순위 미포함</p><ul class="list" id="leader-company-list"></ul><div id="sec-reported-panel"></div><div id="public-qg"></div><div id="leader-m2-panel">'+m2Panel()+'</div>'+block("leaderboard",t("제공된 Leaderboard"),`<ul class="list">${(l?.rows || []).map(r=>`<li class="card"><a href="#company/${encodeURIComponent(r.company_id)}"><b>#${esc(r.rank)} ${esc(r.ticker)}</b></a>${star(r.company_id)}<dl>${[[t("시총 순위"),r.market_cap_rank],["QGV",r.total_score],[t("Daily move(전일 등락)"),r.daily_move],[t("Consensus(컨센서스)"),r.consensus],[t("Scenario(시나리오)"),r.scenario],[t("Reevaluation(재평가 기준)"),r.reevaluation_trigger]].map(([k,v])=>`<dt>${t(k)}</dt><dd>${fmt(v)}</dd>`).join("")}</dl>${evidence(r)}</li>`).join("")}</ul>`);
}
function news(id) {
  const c=company(id);
  // Menu 4 layout (design lane D3): the same pieces, placed in numbered stamp boxes by NewsSignals.screenHtml; without it, the old order.
  const parts={head:heading("NEWS / NETWORK",t("뉴스와 연결"),c?esc(c.ticker)+" "+t("기업 문맥"):t("Portfolio · 관심기업 · 기타 중요뉴스")),
  toolbar:`<div class="chips toolbar" id="news-network" role="group" aria-label="${t("콘텐츠 전환")}"><button id="show-news" aria-pressed="true">${t("뉴스")}</button><button id="show-network" aria-pressed="false">${t("관계망")}</button>${c?star(id):""}</div>`,overlay:`<p class="small" data-news-overlay>${t("정보 제공용, 투자 판단 덧씌우기(Overlay)는 기본 OFF")} · ${t("뉴스 무료 출처 미정: NOT_AVAILABLE")}</p>`,scopes:`<div class="chips" data-news-scopes>${["전체","관심 기업","내 포트폴리오","업종","매크로","정치","경제"].map(x=>`<span class="badge">${esc(t(x))}</span>`).join("")}</div>`,newsPane:`<section id="news-pane"><select id="news-scope" aria-label="${t("뉴스 범위")}"><option value="all">${t("전체 중요뉴스")}</option><option value="interest">${t("관심기업")}</option><option value="portfolio">Portfolio</option></select>${state(D.news)}<ul id="news-list" class="list"></ul></section>`,networkPane:`<section id="network-pane" hidden><p class="muted">${t("Fact = 확인된 관계 · Impact = 잠재 영향 경로")}</p>${state(D.relationships)}${D.relationships.data?'<iframe title="'+esc(t("News Network(뉴스 관계망)"))+'" data-src="network.html" id="network-frame"></iframe>':'<p class="empty">'+t("기업 관계 · 미연결")+"</p>"}</section>`};
  return typeof NewsSignals==="object"&&typeof NewsSignals.screenHtml==="function"?NewsSignals.screenHtml(parts,{locale:appSettings.display_locale,company:c?{id:c.company_id,ticker:c.ticker}:null,interests:prefs.interests.length,relations:!!D.relationships.data}):
   parts.head+parts.toolbar+parts.overlay+parts.scopes+'<div id="news-disclosures"></div><div id="news-dart-disclosures"></div>'+parts.newsPane+parts.networkPane;
}
function research() {
  return heading("RESEARCH",t("질문에서 근거로"),t("Prompt → Context / Variables → Preview → Copy"))+'<p class="badge">FROZEN_SNAPSHOT · PLV1_CONTENT_V1.0</p>'+ScreenDetail.promptsHtml(appSettings.display_locale,'<iframe title="'+esc(t("Prompt Library(프롬프트 라이브러리)"))+'" src="research.html" id="research-frame"></iframe>');
}
// Navigation only. Availability describes the existing public screens, not investment results.
function hubCard(title,status,description,href) {
  const body=`<h3>${esc(t(title))}</h3><span class="badge" data-feature-status="${status}">${esc(t(status))}</span><p class="muted">${esc(t(description))}</p>`;
  return href?`<a class="card hub-card" href="${href}">${body}</a>`:
    `<article class="card hub-card">${body}<span class="badge NOT_AVAILABLE">NOT_AVAILABLE</span></article>`;
}
function qgv() {
  const groups=[
    ["investments","내 투자",[
      ["포트폴리오","부분","기기 보유 요약을 확인합니다. 운영 포트폴리오 Snapshot은 미연결입니다.","#portfolio"],
      ["전략 프로필·가중치","부분","공식 가중치 복사·초안·PREVIEW·기기 저장","#profiles"],
      ["모델 포트폴리오","부분","MODEL·TARGET·ACTUAL을 따로 표시합니다. MODEL은 실데이터 QGV 연결 전 NOT_AVAILABLE입니다.","#model"],
      ["계좌 연결","사용 가능","이 기기에 보유와 수동 시세를 입력·관리합니다.","#actual"]]],
    ["companies","종목 찾기",[
      ["리더보드","부분","순위 화면은 열 수 있습니다. 운영 순위 데이터는 미연결입니다.","#leaderboard"],
      ["관심 기업","사용 가능","관심 기업과 여러 그룹을 기기에 저장합니다.","#watchlist"],
      ["기업 검색","부분","과거 기업 목록을 탐색합니다. 운영 기업 분석은 미연결입니다.","#companies"],
      ["기업 유형 커스텀","부분","공식 설정 복사·PREVIEW·기기 저장","#types"]]],
    ["market","시장 정보",[
      ["뉴스·관계망","부분","뉴스·관계망 화면은 열 수 있습니다. 운영 데이터는 미연결입니다.","#news"],
      ["투자자 13F","부분","공개 보고 수량 변화를 확인합니다.","#thirteenf"]]],
    ["performance","성과",[
      ["검증 연결","부분","검증 허브에서 준비 상태를 확인합니다. 성과 기록은 미연결입니다.","#validation"]]]
  ];
  return heading("QGV",t("QGV 허브"),t("기존 화면과 각 기능의 준비 상태를 확인합니다."))+
    `<div class="chips data-badges"><span class="badge">${esc(t("점수 기준 v2 · PROVISIONAL"))}</span><span class="badge">${esc(t("미국 상위 500 · 목표 범위"))}</span></div>`+
    `<div data-hub="qgv">${groups.map(([id,title,cards])=>`<section class="hub-group" id="qgv-${id}"><h2 tabindex="-1">${esc(t(title))}</h2><div class="hub-grid">${cards.map(args=>hubCard(...args)).join("")}</div></section>`).join("")}</div>`+
    `<p class="hub-legend" data-hub-legend>${["사용 가능","부분","준비 중","설계만"].map(x=>`<span class="badge" data-feature-status="${x}">${esc(t(x))}</span>`).join(" ")}</p>`;
}
function profiles() { return heading("PREVIEW",t("전략 프로필"))+'<div id="device-profile-editor"></div>'; }
function types() { return heading("PREVIEW",t("기업 유형 커스텀"))+'<div id="device-type-editor"></div>'; }
function model() {
  return heading("MODEL PORTFOLIO",t("모델 포트폴리오"),t("전략 규칙대로 기계적으로 만든 기준 포트폴리오, 매수 추천 아님"))+
    `<section class="card" data-model-strategy><h2>${t("선택한 전략")}</h2><p><span class="badge NOT_AVAILABLE">NOT_AVAILABLE</span> ${esc(t("실데이터 QGV 연결 전에는 MODEL을 만들지 않습니다. DEMO를 실제처럼 보여 주지 않습니다."))}</p></section>
    <section class="card"><h2>MODEL / TARGET / ACTUAL</h2><p class="small">${esc(t("세 값은 서로 대신 채우지 않습니다. 앱은 비중을 제안·변경하지 않습니다."))}</p><div class="table-wrap"><table data-model-table><thead><tr><th>${t("종목")}</th><th>MODEL</th><th>TARGET</th><th>ACTUAL</th><th>MODEL−TARGET</th></tr></thead><tbody id="model-rows"><tr><td colspan="5">${t("데이터를 불러오는 중…")}</td></tr></tbody></table></div></section>
    <section class="card"><h2>ACTUAL · ${esc(t("이 기기"))}</h2><div id="model-actual-summary" aria-live="polite"></div></section>
    <div class="chips"><a href="#validation-backtest">${t("이 전략 백테스트 →")}</a><a href="#portfolio">${t("내 포트폴리오 →")}</a></div>`;
}
function paintModel() {
  const body=$("#model-rows");
  deviceCatalog().then(catalog=>{
    if(!body?.isConnected) return;
    const total=Number(catalog.total_units);
    body.innerHTML=catalog.instruments.map(r=>{const target=Number.isFinite(total)&&total>0&&Number.isFinite(Number(r.target_units))?fmt(100*Number(r.target_units)/total)+"%":"—";
      return `<tr data-model-row="${esc(r.ticker)}"><td>${esc(r.ticker)}</td><td data-na="NOT_AVAILABLE">—</td><td>${target}</td><td>${esc(t("요약 ↓"))}</td><td data-na="NOT_AVAILABLE">—</td></tr>`;}).join("")+
      `<tr><td colspan="5" class="small">TARGET ${esc(catalog.target_root_version || "")} · — = NOT_AVAILABLE</td></tr>`;
  }).catch(()=>{if(body?.isConnected) body.innerHTML=`<tr><td colspan="5">TARGET NOT_AVAILABLE</td></tr>`;});
}
function technical(id) {
  const s=D.technical,tabs=[["chart","차트"],["state","상태"],["execution","실행"],["record","기록"]];
  // Menu 2 layout (design lane D6): TechnicalCards.screenHtml places these pieces (status cards under one h2 region, so h3);
  // TechnicalCards.arrange (after mount) moves the indicator cards into the 3.1.4 stamp box of the workbench. The display-only
  // TradingView card sits above the workbench so its lazy frame stays near the first screen.
  return TechnicalCards.screenHtml({head:heading("TECHNICAL",t("기술적 분석"),t("기존 기록의 연결 상태를 확인합니다.")),
    badges:`<div class="chips data-badges"><span class="badge">${esc(t("실데이터 검증 전 · 일봉·수정주가 기준"))}</span></div>`,
    tabs:`<nav class="chips screen-tabs" aria-label="${esc(t("기술적 분석"))}">${tabs.map(([key,label])=>`<a href="#technical-${key}${id?'/'+encodeURIComponent(id):''}" data-screen-tab="${key}">${esc(t(label))}</a>`).join("")}</nav>`,
    chart:`<div id="technical-chart"><div id="technical-price-chart" data-tech-status="chart"></div><div id="technical-tv-chart"></div><div id="technical-workbench"></div><div id="technical-indicators"></div></div>`,
    engine:`<section class="card status-card" id="technical-state" data-tech-status="engine"><h3>${t("기술적 분석 엔진")}</h3>${state(s)}<p>${esc(t(s.data===null?s.reason || "운영 Snapshot이 연결되지 않았습니다.":"기존 종목 화면에서 제공된 기술적 분석 기록을 확인합니다."))}</p><p class="small">${esc(t("QGV 원점수와 기술적 상태는 나란히 볼 뿐 통합하지 않습니다."))}</p></section>`,
    sections:TechnicalCards.sectionsHtml(appSettings.display_locale),
    execution:`<section class="card" id="technical-execution" data-tech-status="execution"><h3>${t("실행 구간 (시스템 주문 아님)")}</h3><p><span class="badge NOT_AVAILABLE">NOT_AVAILABLE</span> ${esc(t("검증된 모델 입력이 없어 실행 구간을 만들지 않습니다."))}</p></section>`,
    record:`<section class="card" id="technical-record" data-tech-status="record"><h3>${t("기술적 기록")}</h3><p><span class="badge NOT_AVAILABLE">NOT_AVAILABLE</span> ${esc(t("과거 신호와 실제 결과 기록이 아직 없습니다."))}</p></section>`,
    ia:window.IaScreens?IaScreens.technicalHtml(appSettings.display_locale):""},{locale:appSettings.display_locale});
}
function macro() {
  // Menu 3 stamp layout (4.1–4.6) lives in IaScreens.macroHtml; the parts below are placed there unchanged.
  const parts={lights:'<div id="macro-lights-root"></div>',evidence:'<div id="macro-evidence-root"></div>',
    status:`<section class="card" data-macro-status><h2>${t("상태판")}</h2><p class="small">${esc(t("정상·경고·위기는 위의 경고등 5개로 정합니다. 8개 축 국면 판정은 보류합니다."))}</p>
    <h3>${t("현재 국면")}</h3><p data-macro-regime>${esc(t("자료 없음"))}</p><p class="small">${esc(t("8개 축의 6칸은 따로 보관하며 하나의 점수로 합치지 않습니다. FRED/ALFRED는 사용하지 않습니다."))}</p></section>`,
    raw:'<div id="public-macro"></div>',canon:ScreenDetail.macroHtml(appSettings.display_locale)};
  return `<div data-ia-screen="macro">${heading("MACRO",t("매크로"),t("공식 축별 상태를 확인합니다."))}
    <div class="chips data-badges"><span class="badge">${esc(t("매크로 상태 v1 · UNCALIBRATED · 경고등 5개"))}</span></div>
    ${window.IaScreens?IaScreens.macroHtml(appSettings.display_locale,parts):parts.lights+parts.evidence+parts.status+parts.raw+parts.canon}</div>`;
}
function thirteenf() {
  return heading("SEC 13F",t("투자자 13F"))+ '<div id="public-thirteenf"></div>';
}

function validation() {
  const tabs=[["paper","모의투자","준비 중","공개 앱에 연결된 모의투자 결과가 없습니다."],["backtest","백테스트","준비 중","공개 앱에 연결된 백테스트 결과가 없습니다."],["forward","전진 검증","부분",appSettings.display_locale==='en-US'?"Read the published ledger and evaluation eligibility below. Outcomes requiring prices are calculated on your device only.":"공개 원장의 관측 기록과 평가 가능 여부를 아래에서 확인합니다. 가격을 포함한 이후 성과는 기기에서만 계산합니다."],["track","Track Record","준비 중","공개 앱에 연결된 성과 기록이 없습니다."],["trials","실험 기록","준비 중","공개 앱에 연결된 실험 기록이 없습니다."]];
  return heading("VALIDATION",t("검증·연구"),t("리서치와 검증 기록의 준비 상태를 확인합니다."))+
    `<div class="chips data-badges"><span class="badge">${esc(t("PIT 시점 기준 데이터만"))}</span><span class="badge">${esc(t("Holdout 기간 미정·사용 금지 · 보호 판정 UNCONFIRMED"))}</span></div>`+
    `<nav class="chips screen-tabs" aria-label="${esc(t("검증·연구"))}">${tabs.map(([id,label])=>`<a href="#validation-${id}" data-screen-tab="${id}">${esc(t(label))}</a>`).join("")}<a href="#research" data-screen-tab="research">${esc(t("리서치"))}</a></nav>`+
    `<div class="hub-grid" data-hub="validation">${tabs.map(([id,title,status,reason])=>`<div id="validation-${id}">${hubCard(title,status,reason,id==='forward'?'#validation-forward':null)}</div>`).join("")}${hubCard("리서치","사용 가능","기존 프롬프트 라이브러리를 엽니다.","#research")}</div>`+ScreenDetail.validationHtml(appSettings.display_locale);
}
// QGV sub-categories (navigation only). The "01 / QGV" line above a screen follows the menu of its route (app-shell.js).
const QGV_SUBCATEGORY=Object.freeze({portfolio:"내 투자",actual:"내 투자",profiles:"내 투자",model:"내 투자",companies:"종목 찾기",company:"종목 찾기",analysis:"종목 찾기",entity:"종목 찾기",leaderboard:"종목 찾기",watchlist:"종목 찾기",types:"종목 찾기",news:"시장 정보",thirteenf:"시장 정보"});
const QGV_CHILDREN=Object.freeze(["companies","company","analysis","leaderboard","news","portfolio","actual","entity","profiles","types","thirteenf","watchlist","model","playbook"]);
// Main menu / bottom navigation (app-shell.js): one current destination per route, none in settings.
function syncNavigation(route) {window.AppShell?.sync(route,appSettings.display_locale);}
let listLimit=30;
// List navigation state lives only in this tab, never in settings/storage. Rows are always drawn from current identities.
const directoryViews=new Map();
// Route history of this page (for the S04 back link and S06 scroll restore).
let currentRoute=null,previousRoute=null,currentHash='';
const LIST_ORIGIN=Object.freeze({leaderboard:['← 리더보드','← Leaderboard'],companies:['← 기업 목록','← Company list'],watchlist:['← 관심 기업','← Watchlist']}),LIST_ORIGIN_HASH=/^#(leaderboard|leaderboard\/interest|companies|watchlist)$/;
function paintCompanies(){
 const rows=DeviceWatchlist.filter(allCompanyRows(),prefs,{query:$('#search').value,group:$('#group-filter').value,onlyInterest:$('#only-interest').checked,sort:$('#company-sort').value});
 $('#company-list').innerHTML=rows.slice(0,listLimit).map(row).join('')||'<li class="empty">'+t("일치하는 기업이 없습니다.")+'</li>';$('#more-companies').hidden=rows.length<=listLimit;
}
// Company list = every company (TARGET aliases + Universe504 codes); watchlist = the watched issuers (any company). The S06 TARGET
// directory ('leader') is the TARGET v0 list kept for the v0 comparison (D12).
function allCompanyRows(){const rows=DeviceWatchlist.directory(companyName),byId=new Map(identityCompanies.map(c=>[c.company_id,c]));return rows.map(r=>byId.has(r.company_id)?byId.get(r.company_id):r);}
function directoryRows(prefix){return DeviceWatchlist.filter(prefix==='watch'?DeviceWatchlist.watchRows(prefs,companyName).map(r=>identityCompanies.find(c=>c.company_id===r.company_id)||r):identityCompanies,prefs,{query:prefix==='leader'?$('#leader-query')?.value||'':'',group:$('#'+prefix+'-group').value,onlyInterest:$('#'+prefix+'-interest').checked,sort:$('#'+prefix+'-sort').value});}
/* S06 view state of this tab: view/profile, filters (interest, group, text), sort and scroll, plus where S04/S05 was opened
   from (origin, for its back link). RAM first, mirrored to sessionStorage as a per-tab convenience (try/catch: RAM only when
   storage is unavailable). No score, rank, price or v2 profile is stored: the v2 preset/gate stay in page memory (qgv2Profile). */
const S06_KEY='investment.web.v1.s06-view',LEADER_SORTS=LeaderboardScreen.SORT_IDS;
let leaderboardView={view:'default',profileId:null,interest:false,target:false,group:'',sort:'qgv',query:'',explore:'all',scrollY:0,anchor:null,offset:0},leaderboardRows=null,companyOrigin=null;
// S06 exploration filter (FE-MISSING-2): all / official QGV ranking / QG 참고 목록 (V 미포함, D11) / some axes only / check data
// (LeaderboardScreen.EXPLORE).
const LEADER_EXPLORE=['all','ranked','qg','partial','check'];
// Last value written (or the defaults): nothing is written until the state differs from it, so screens never touched
// leave sessionStorage empty.
let leaderSaved=JSON.stringify({...leaderboardView,origin:null});
function readLeaderView(){try{const raw=sessionStorage.getItem(S06_KEY),v=JSON.parse(raw||'null');if(!v||typeof v!=='object')return;leaderSaved=raw;
  leaderboardView={view:['default','profile','device'].includes(v.view)?v.view:'default',profileId:typeof v.profileId==='string'?v.profileId:null,interest:v.interest===true,target:v.target===true,group:typeof v.group==='string'?v.group:'',sort:LEADER_SORTS.includes(v.sort)?v.sort:'qgv',query:typeof v.query==='string'?v.query.slice(0,60):'',explore:LEADER_EXPLORE.includes(v.explore)?v.explore:'all',scrollY:Number.isFinite(v.scrollY)&&v.scrollY>0?Math.round(v.scrollY):0,anchor:typeof v.anchor==='string'&&v.anchor.length<=64?v.anchor:null,offset:Number.isFinite(v.offset)?Math.round(v.offset):0};
  const o=v.origin;companyOrigin=o&&typeof o.id==='string'&&typeof o.hash==='string'&&/^#(leaderboard|leaderboard\/interest|companies|watchlist)$/.test(o.hash)?{id:o.id,hash:o.hash}:null;}catch(_){}}
function saveLeaderView(){const json=JSON.stringify({...leaderboardView,origin:companyOrigin});if(json===leaderSaved)return;leaderSaved=json;try{sessionStorage.setItem(S06_KEY,json);}catch(_){}}
function syncLeaderView(){const q=$('#leader-query'),g=$('#leader-group');leaderboardView={...leaderboardView,interest:$('#leader-interest').checked,target:$('#leader-target')?.checked===true,group:g?g.value:'',sort:LEADER_SORTS.includes($('#leader-sort').value)?$('#leader-sort').value:'qgv',query:q?q.value:''};saveLeaderView();}
/* Scroll position of S06: the first table row in view and its distance from the viewport top (falls back to scrollY when no row
   is in view). Restoring by row keeps the same rows in view even when content above it (e.g. the 'My device' panel) changed. */
function leaderAnchor(){for(const r of document.querySelectorAll('#leaderboard-screen [data-leaderboard-row]')){const b=r.getBoundingClientRect();if(b.bottom>0&&b.top<window.innerHeight)return{anchor:r.dataset.leaderboardRow,offset:Math.round(b.top)};}return{anchor:null,offset:0};}
function restoreLeaderScroll(){const v=leaderboardView,row=v.anchor?document.querySelector('#leaderboard-screen [data-leaderboard-row="'+CSS.escape(v.anchor)+'"]'):null;
  window.scrollTo(0,row?Math.max(0,Math.round(row.getBoundingClientRect().top+window.scrollY-v.offset)):v.scrollY||0);}
// Restore now and once more after the next two frames (PC table headers gain their sort buttons one frame later); the saved
// position is not overwritten in between.
let leaderRestoring=false;
function restoreLeaderView(){leaderRestoring=true;restoreLeaderScroll();requestAnimationFrame(()=>requestAnimationFrame(()=>{if(currentRoute==='leaderboard')restoreLeaderScroll();leaderRestoring=false;}));}
// 'QGV v2 순': the official v2 rank over the Universe rows of the official evaluation (QgvScores, rows with V; D12), then the QG 참고
// 목록 (V 미포함) in its own order (D11); filters (search, group, interest, TARGET) only hide rows. No total goes last, by ticker.
// Other S06 sort keys (Q/G/V, direction, data date, M3 market cap): structured values, NA last (LeaderboardScreen.sortRows).
function rankOrder(rows,S){return LeaderboardScreen.sortRows(rows,S,leaderboardView.sort,{deviceRanks:window.PrivateSubsetView?.ranks?.()||null});}
function paintLeaderSummary(S,shown,total=identityCompanies.length){const host=$('#leader-summary');if(!host)return;const en=appSettings.display_locale==='en-US',v=leaderboardView,group=prefs.groups.find(g=>g.id===v.group);
  const sort={qgv:en?'QGV v2 (high first)':'QGV v2 순',ticker:t('티커 순'),name:t('기업명 순'),favorites:t('관심기업 우선')}[v.sort]||LeaderboardScreen.sortLabel(v.sort,en),filters=[...LeaderboardScreen.classificationSummary({publicScreens,locale:appSettings.display_locale}),v.interest?t('관심기업만'):null,v.target?(en?'TARGET only':'TARGET만'):null,group?(en?'group ':'그룹 ')+group.name:null,v.query.trim()?(en?'search “':'검색 “')+v.query.trim()+'”':null,v.explore!=='all'&&v.view!=='profile'?(LeaderboardScreen.EXPLORE.find(e=>e[0]===v.explore)||[])[en?2:1]:null].filter(Boolean);
  const view={default:en?'Default':'기본',profile:en?'My profile (v1 preview, not the official v2 score)':'내 프로필(v1 미리보기 · 공식 v2 점수 아님)',device:en?'My device (M3)':'내 기기 기준(M3)'}[v.view];
  const p=S&&S.profile?(en?S.profile.name.name_en:S.profile.name.name)+' · '+(en?'gate ':'관문 ')+(S.profile.gate?(en?'on':'켬'):(en?'off':'끔')):'—';
  const text=(en?'Sort: ':'정렬: ')+sort+' · '+(en?'Filter: ':'필터: ')+(filters.join(' · ')||(en?'none':'없음'))+' · '+(en?'View: ':'보기: ')+view+' · '+(en?'Profile: ':'프로필: ')+p+' · '+(en?shown+' of '+total+' shown':total+'개 중 '+shown+'개 표시');
  if(host.textContent!==text)host.textContent=text;}
// Scores (S04/S05/S06, report, rehearsal) come only from QgvScores (the scoring_default setting). QGV v2 profile choice and the
// device quotes of the v2 V cross-section live in this page's memory only: never stored, logged or sent.
let qgv2Profile={preset:null,gate:null},qgv2Quotes={},qgv2QuotesKey='';
// New device quotes change only the score sections. Repaint those in place: a full render() would reset the open analysis
// tab, the value panel, the loaded private history table and the playbook panel.
const SCORE_SECTIONS=['[data-company-badges]','[data-company-card="qgv"]','[data-analysis-panel="summary"]','[data-analysis-panel="factors"]'];
// Coverage sections the user opened (details[data-keep-open]) stay open across the repaint.
function repaintScores(build){const fresh=document.createElement('div');fresh.innerHTML=build();for(const sel of SCORE_SECTIONS){const live=$('#content '+sel),next=fresh.querySelector(sel);if(!live||!next)continue;
 const open=new Set([...live.querySelectorAll('details[data-keep-open][open]')].map(d=>d.dataset.keepOpen));for(const d of next.querySelectorAll('details[data-keep-open]'))if(open.has(d.dataset.keepOpen))d.open=true;live.innerHTML=next.innerHTML;}}
// Late score inputs (the DART reference row) repaint only the score views of the open screen. A full render() here
// discarded typed weights, open tabs and in-flight save messages on whatever screen was open (e.g. the ledger sheet).
function refreshScoreViews(){const[route,raw]=location.hash.slice(1).split('/');let id='';try{id=decodeURIComponent(raw||'');}catch(_){id='';}
 if(route==='leaderboard'&&leaderboardRows&&$('#leaderboard-screen'))paintLeaderboardScreen();
 else if(route==='company'&&id)repaintScores(()=>detail(id));else if(route==='analysis'&&id)repaintScores(()=>analysis(id));}
function qgvScores(identities=identityCompanies){return QgvScores.compute({identities,publicScreens,quotes:qgv2Quotes,preset:qgv2Profile.preset,gate:qgv2Profile.gate,referenceRows:typeof dartReferenceRows==='function'?dartReferenceRows():{}});}
/* OFFICIAL EVALUATION (D12, owner decision 2026-10-19: '공식 리더보드는 Universe 전체 평가를 기준으로 한다. 기존 TARGET 19개는 별도
   목록·필터로 유지한다.'). ONE result feeds S06, the company detail rank, the playbook candidates, the radar and the V panel: the
   shared QgvScores.pageResult (one collectQuotes + one compute over every Universe code of the published sec-qgv2.json and the TARGET
   identities, deduplicated into one row per security; qgv-scores.js universeIdentities). leaderScores() returns that result's
   `computed` itself while it is current (same Universe read, preset/gate and reference rows); otherwise the same call over the same
   identities with the shared quote set it has (that result's quotes, else the last shared set after new public inputs, none before
   a price read: no official rank, the QG 참고 목록 shows, D11). Populations:
   evaluation = every security of that result; rank = Universe rows with an official rank (V); eligibility = the approved
   model-portfolio rules (QgvScores.modelPortfolios); filters (search, group, interest, TARGET) only hide rows. RAM only. */
const NO_QUOTES=Object.freeze({});let leaderBasis=null,qgv2QuotesBasis=null,leaderQuotes=NO_QUOTES,leaderPage=null,leaderShown=null,officialMemo=null,populationMemo=null;// leaderShown: the page result the last S06 paint used (a paint made before the result arrived is repainted)
function officialPopulation(){const inputs=window.Qgv2Inputs?publicScreens[Qgv2Inputs.FILE]:null;
 if(populationMemo&&populationMemo.inputs===inputs&&populationMemo.ids===identityCompanies&&populationMemo.names===companyNames)return populationMemo.value;
 const U=inputs&&typeof QgvScores.universeIdentities==='function'?QgvScores.universeIdentities(inputs,identityCompanies):null,byId=new Map(identityCompanies.map(c=>[c.company_id,c]));
 // Universe rows: a TARGET identity keeps its catalog name; a Universe code is named from company-names-ko.json (search only).
 const named=c=>{const t=byId.get(c.company_id),code=U?U.universe[c.company_id]:null;if(t)return{...t,universe_code:code||null,target:true};const n=companyNames?companyNames.get(c.company_id):null;
  return{company_id:c.company_id,ticker:c.ticker,name:[n&&n.ko_name,n&&n.en_name].filter(Boolean).join(' '),universe_code:code||null,target:false};};
 const value=U?{official:U,rows:U.identities.filter(c=>U.universe[c.company_id]).map(named),outside:U.outside.map(id=>({...byId.get(id),universe_code:null,target:true}))}:{official:null,rows:identityCompanies.map(c=>({...c,universe_code:null,target:true})),outside:[]};
 populationMemo={inputs,ids:identityCompanies,names:companyNames,value};return value;}
function leaderScores(){const inputs=window.Qgv2Inputs?publicScreens[Qgv2Inputs.FILE]:null,page=leaderPage&&leaderPage.inputs===inputs?leaderPage.result:null;leaderShown=page;
 const refs=typeof dartReferenceRows==='function'?dartReferenceRows():{},refKey=JSON.stringify(refs);
 leaderBasis=page?page.price_basis||null:qgv2QuotesKey?qgv2QuotesBasis:null;// the Universe read of the quote set used below (data-cx marks)
 if(page&&page.official&&page.reference_key===refKey&&QgvScores.isCurrent(window,page)){leaderQuotes=page.quotes;return page.computed;}// the ONE shared result itself
 const pop=officialPopulation(),quotes=page?page.quotes:qgv2QuotesKey?qgv2Quotes:NO_QUOTES;leaderQuotes=quotes;const key=JSON.stringify([qgv2Profile.preset,qgv2Profile.gate,refKey]);// quotes do not depend on preset/gate
 if(officialMemo&&officialMemo.inputs===inputs&&officialMemo.quotes===quotes&&officialMemo.pop===pop&&officialMemo.key===key)return officialMemo.S;
 const S=QgvScores.compute({identities:pop.official?pop.official.identities:identityCompanies,publicScreens,quotes,preset:qgv2Profile.preset,gate:qgv2Profile.gate,referenceRows:refs,official:pop.official});
 officialMemo={inputs,quotes,pop,key,S};return S;}
async function refreshLeaderPage(after){const inputs=window.Qgv2Inputs?publicScreens[Qgv2Inputs.FILE]:null;if(!inputs||typeof QgvScores.pageResult!=='function')return;const{preset,gate}=qgv2Profile;let catalog=null;try{catalog=await deviceCatalog();}catch(_){catalog=null;}
 let r=null;try{r=await QgvScores.pageResult(window,{v2Inputs:inputs,catalog,identities:identityCompanies,preset,gate});}catch(_){r=null;}if(!r)return;
 // A call that started before a new Universe read, new inputs or a preset/gate change can finish after the call made for them:
 // its result is no longer the current one and never replaces leaderPage or the shared quotes (the newer call writes them).
 if(publicScreens[Qgv2Inputs.FILE]!==inputs||!QgvScores.isCurrent(window,r))return;if(leaderPage&&leaderPage.result===r){if(after&&leaderShown!==r)after();return;}
 // The Universe read is one shared RAM state (PrivateSubsetView: the last successful read survives navigation), so the current
 // page result is used as is (never compared with the one it replaces). A new read or 'clear device results' (onRanks) resets leaderPage.
 leaderPage={inputs,result:r};
 // S04/S05/S13 score with exactly these quotes (replaced, never merged with an older set), so every screen prices the same rows.
 const k=JSON.stringify(r.quotes);if(k!==qgv2QuotesKey){qgv2Quotes=r.quotes;qgv2QuotesKey=k;}qgv2QuotesBasis=r.price_basis||null;if(after)after();}
async function refreshQgv2Quotes(after){if(DataRefresh.quiet())return;const before=qgv2QuotesKey;await refreshLeaderPage();if(qgv2QuotesKey!==before&&after)after();}// the same shared page result as S06
// M3 ranks come from the open Universe read (RAM only) and are repainted into S06 when that read finishes or is cleared.
// Ranks and totals are computed over ALL identities (the same population as S04), then only the filtered rows are shown.
// A repaint keeps keyboard focus on the same control (preset, gate, view, profile, detail button) instead of dropping it.
function focusKey(n){if(!n||!n.dataset)return null;for(const k of ['qgv2Preset','leaderboardView','leaderboardProfile','qgv2Gate','leaderboardExploreOption'])if(Object.hasOwn(n.dataset,k))return '[data-'+k.replace(/[A-Z]/g,c=>'-'+c.toLowerCase())+(n.dataset[k]?'="'+CSS.escape(n.dataset[k])+'"':'')+']';
  return n.getAttribute('aria-controls')?'[aria-controls="'+CSS.escape(n.getAttribute('aria-controls'))+'"]':null;}
/* S06 rows (D12): the Universe rows of the official evaluation after the screen filters (search, group, interest, TARGET), and the
   TARGET identities outside the Universe after the same filters, for their own labelled list. Filters only hide rows. */
function leaderFiltered(){const pop=officialPopulation(),v=leaderboardView,f=list=>LeaderboardScreen.filterClassifications(DeviceWatchlist.filter(list,prefs,{query:v.query,group:v.group,onlyInterest:v.interest,sort:v.sort}),{publicScreens});
 return{rows:f(v.target?pop.rows.filter(r=>r.target):pop.rows),outside:f(pop.outside),pop};}
let leaderPaint=0;
function paintLeaderboardScreen(){const paint=++leaderPaint;leaderboardRows=true;let profiles=[];try{profiles=DeviceProfiles.read(localStorage).strategies;}catch(_){profiles=[];}
 const host=$('#leaderboard-screen'),S=leaderScores(),F=leaderFiltered(),shown=rankOrder(F.rows,S),
  // N10/N15/N20 on the OFFICIAL default profile (balanced, gate on), the same inputs and quotes as S, whatever the S06 preset.
  model=F.pop.official&&typeof QgvScores.officialModel==='function'?QgvScores.officialModel({identities:F.pop.official.identities,v2Inputs:publicScreens[Qgv2Inputs.FILE],quotes:leaderQuotes,official:F.pop.official,computed:S}):null,active=host&&host.contains(document.activeElement)?focusKey(document.activeElement):null;
 LeaderboardScreen.mountClassificationFilters($('#leader-classification-filters'),F.pop.rows.concat(F.pop.outside),{publicScreens,locale:appSettings.display_locale,onChange:()=>paintLeaderboardScreen()});
 const mounted=LeaderboardScreen.mount(host,shown,{publicScreens,locale:appSettings.display_locale,nameOf:id=>EntitySearch.companyName(companyNames?.get(id)||null,appSettings.display_locale),profiles,deviceRanks:window.PrivateSubsetView?.ranks?.()||null,view:leaderboardView.view,profileId:leaderboardView.profileId,scores:S,explore:leaderboardView.explore,outside:F.outside,targetOnly:leaderboardView.target===true,model,priceBasis:leaderBasis,onView:patch=>{if(Object.hasOwn(patch,'preset')||Object.hasOwn(patch,'gate')){qgv2Profile={...qgv2Profile,...patch};paintLeaderboardScreen();return;}leaderboardView={...leaderboardView,...patch};saveLeaderView();if(leaderboardView.view==='device'){const d=$('#private-subset-root')?.closest('details');if(d)d.open=true;}paintLeaderboardScreen();}});
 if(active){const n=host&&host.querySelector(active);if(n)n.focus({preventScroll:true});}
 paintLeaderSummary(S,mounted&&Number.isInteger(mounted.shown)?mounted.shown:shown.length,F.pop.rows.length);
 void window.VCoverage?.paint($('#v-coverage-root'),{publicScreens,catalog:deviceCatalog,identities:identityCompanies,preset:qgv2Profile.preset,gate:qgv2Profile.gate,locale:appSettings.display_locale});// V 산출 현황 · 이 기기 (QgvScores.pageResult, RAM only)
 void refreshLeaderPage(()=>{if(leaderPaint===paint&&$('#leaderboard-screen'))paintLeaderboardScreen();});}
// The TARGET directory list under S06 (the separate TARGET 19 list, owner decision D12) keeps its own filters (search, group,
// interest) and the official order; the S06 table above holds the Universe rows of the official evaluation.
function paintDirectory(route){const prefix=route==='watchlist'?'watch':'leader';if(route==='leaderboard')syncLeaderView();
 const rows=route==='leaderboard'?rankOrder(directoryRows(prefix),leaderScores()):directoryRows(prefix),list=$('#'+(route==='watchlist'?'watchlist':'leader')+'-company-list');list.innerHTML=rows.map(row).join('')||'<li class="empty">'+t("일치하는 기업이 없습니다.")+'</li>';if(route==='leaderboard'){const companyIds=rows.map(r=>r.company_id);paintLeaderboardScreen();$('#leader-m2-panel').innerHTML=m2Panel(undefined,companyIds);SecReported.mount($('#sec-reported-panel'),secReported,{companyIds,locale:appSettings.display_locale});PublicScreens.mount($('#public-qg'),publicScreens,{kind:'qg',companyIds,locale:appSettings.display_locale});}}

function paintNews(id) {
  const c=company(id),scope=$("#news-scope").value,held=D.portfolio.data?.holdings?.map(h=>h.company_id) || [];
  const interests=[...prefs.interests],portfolio=held.map(i=>company(i)?.issuer_id).filter(Boolean);
  let rows=(D.news.data || []).filter(r=>(!c || (r.issuer_ids || []).includes(c.issuer_id)) && (scope==="all" || (r.issuer_ids || []).some(i=>(scope==="interest"?interests:portfolio).includes(i))) && (appSettings.source_language==="all" || r.source_language?.split("-")[0]===appSettings.source_language));
  const priority=r=>(r.issuer_ids || []).some(i=>portfolio.includes(i))?0:(r.issuer_ids || []).some(i=>interests.includes(i))?1:2;
  rows=[...rows].sort((a,b)=>priority(a)-priority(b));
  $("#news-list").innerHTML=rows.map(r=>`<li class="card"><h3>${esc(AppLanguage.fallback(r.headline_localized,appSettings.display_locale,r.headline))}</h3>${r.summary || r.summary_localized?`<p>${esc(AppLanguage.fallback(r.summary_localized,appSettings.display_locale,r.summary || ""))}</p>`:""}<p class="meta">${esc(r.available_at)} · ${esc(AppLanguage.status(r.status || t("상태 미제공"),appSettings.display_locale))} · ${esc(r.source_language || t("미제공"))}</p>${(r.issuer_ids || []).map(byIssuer).filter(Boolean).map(c=>`<div class="row"><a href="#company/${encodeURIComponent(c.company_id)}">${esc(c.ticker)}</a>${star(c.company_id)}</div>`).join("")}${evidence(r)}</li>`).join("") || '<li class="empty">'+t("이 범위에 제공된 뉴스가 없습니다.")+"</li>";
}
function report(id){const real=id==='real';return heading("DAILY REPORT",real?(appSettings.display_locale==='en-US'?'Investment daily report':'투자 일일보고서'):(appSettings.display_locale==='en-US'?'Paper trading daily report':'모의투자 일일보고서'))+'<div id="daily-report" aria-live="polite"></div><div id="virtual-ledger-sheets"></div>';}
// S17: everything is computed in RAM on this device; export/copy and the optional mailbox run only on the user's click.
function reportTab(id){return id==='real'?'REAL':({'mock-set_b':'SET_B','mock-set_c':'SET_C','mock-set_d':'SET_D','mock-compare':'COMPARE'}[id]||'SET_A');}
// The virtual ledger runner (VirtualTradingRunner) reads prices through the existing Google session and private
// history Worker into memory only; this holds just its abort handle and session subscription for the open report.
let reportRun=null;
// The last recording-mode shadow-ledger judgements of this page (투자 일일보고서), RAM only: S03 shows exactly these chips.
let virtualShadow=null;
// ⑬ period and currency basis chosen on S17 (this page session only; RAM, not stored).
let benchSelection={period:'20D',basis:'KRW'};
function disposeReport(){const r=reportRun;reportRun=null;if(r){r.controller.abort();if(r.unsubscribe)r.unsubscribe();if(r.ledgerSheets)r.ledgerSheets.dispose();}}
async function paintReport(id){
  const host=$('#daily-report');if(!host)return;
  disposeReport();
  const R=window.DailyReport,VT=window.VirtualTrading,Runner=window.VirtualTradingRunner,locale=appSettings.display_locale,kind=id==='real'?'REAL':'MOCK',tab=reportTab(id);
  const cfg=VT.defaultConfig(),ledgerKind=kind==='REAL'?'SHADOW':['SET_B','SET_C','SET_D'].includes(tab)?tab:'SET_A',config=window.InvestmentAppConfig||{};
  // mode: RECORDING (기록 모드) or REHEARSAL (리허설 · 기록 없음: RAM only, never written to any ledger or sheet).
  const run={controller:new AbortController(),unsubscribe:null,busy:false,last:null,mode:'RECORDING',pending:null,ledgerSheets:null};reportRun=run;
  const Signals=window.VirtualTradingSignals,VHistory=window.VirtualTradingVHistory;
  const live=()=>reportRun===run&&host.isConnected;
  // D-10 ledger sheet (VirtualLedgerSheets): reads the user's own sheet when connected; writes only on its buttons.
  try{if(window.VirtualLedgerSheets)run.ledgerSheets=VirtualLedgerSheets.mount(window,$('#virtual-ledger-sheets'),{kind,tab,reportDate:new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Seoul'}).format(new Date()),config,catalog:deviceCatalog,refresh:()=>{if(live())void paintReport(id);}});}catch(_){run.ledgerSheets=null;}
  let ram=null;if(kind==='REAL'){try{ram=await DeviceActual.ramView(window,await deviceCatalog());const byTicker=new Map(identityCompanies.map(r=>[r.ticker,r.company_id]));ram={...ram,rows:ram.rows.map(r=>({...r,company_id:byTicker.get(r.ticker)||r.ticker}))};}catch(_){ram=null;}}
  // Judgement/report score rows through the one accessor (QgvScores; v1 rows are exactly the previous Q·G values).
  try{await refreshQgv2Quotes();}catch(_){}
  const qg={},names={};try{Object.assign(qg,QgvScores.judgmentRows(qgvScores()));for(const c of identityCompanies)names[c.company_id]=c.ticker;}catch(_){}
  const reportDate=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Seoul'}).format(new Date());
  let model=null,canonical='',key=null,inboxText='',benchInputs=null,mailboxAnswer=null;
  // ⑬ selection change: recompute the RAM-only benchmark view (pure) and repaint; the canonical template keeps 20D·KRW.
  const rebench=focus=>{if(!benchInputs||!window.ReportBenchmarks||!model)return;model={...model,bench:ReportBenchmarks.build({...benchInputs,...benchSelection})};paint();const n=focus&&host.querySelector(focus);if(n)n.focus();};
  const paint=()=>{
    if(!live()||!model)return;const hidden=R.hiddenSetting(localStorage),answer=key?R.answers(localStorage)[key]||null:null;
    const draft=host.querySelector('[data-ai-input]')?.value||'';
    host.innerHTML=R.screenHtml(model,{hidden,answer,check:answer?R.checkAnswer(answer.answer,canonical):null,locale});
    if(window.PlaybookScreen){const panel=document.createElement("div");host.append(panel);const byTicker=new Map(identityCompanies.map(r=>[r.ticker,r.company_id]));host.querySelectorAll("[data-judgement-cell]").forEach(cell=>{const cid=cell.dataset.judgementCell,button=document.createElement("button");button.type="button";button.textContent="플레이북 열기";button.onclick=async()=>{const catalog=await deviceCatalog(),symbol=names[cid]||cid;const computed=await PlaybookScreen.prepareScores(window,{catalog,screens:publicScreens,idByTicker:byTicker,scoreOptions:playbookScoreOptions}),heldSymbols=await PlaybookScreen.heldSymbolsFor(window,catalog);if(panel.isConnected)PlaybookScreen.openPanel(panel,{symbol,situation:PlaybookScreen.factsFor(symbol,{catalog,screens:publicScreens,idByTicker:byTicker,ram,computed,heldSymbols,interests:[...prefs.interests]})});};cell.append(button);});}
    if(draft)host.querySelector('[data-ai-input]').value=draft;
    const status=host.querySelector('[data-report-status]'),say=text=>{if(status)status.textContent=text;};
    for(const box of host.querySelectorAll('[data-hide-amounts],[data-hide-amounts-export]'))box.onchange=()=>{if(!box.checked&&!confirm('개인 금액이 화면/복사본에 표시됩니다.')){box.checked=true;return;}R.hiddenSetting(localStorage,box.checked);paint();};
    host.querySelector('[data-export-template]').onclick=async()=>{const text=R.renderTemplate(model,{hidden:R.hiddenSetting(localStorage),guide:host.querySelector('[data-include-guide]').checked});try{await navigator.clipboard.writeText(text);say('보고서 템플릿을 복사했습니다. AI 새 대화에 붙여넣으세요.');}catch(_){const area=document.createElement('textarea');area.readOnly=true;area.value=text;area.rows=8;area.setAttribute('data-export-fallback','');host.querySelector('[data-report-export]').append(area);area.select();say('클립보드를 쓸 수 없어 아래 칸에 표시했습니다. 직접 복사하세요.');}};
    // '검토한 답변 보관' (enabled only by DailyReport.reviewInto) is the one save. A mailbox answer keeps its source, model and
    // Outbox time only while the reviewed text is exactly the answer that was fetched for this data key; anything else is PASTE.
    host.querySelector('[data-save-answer]').onclick=()=>{const text=host.querySelector('[data-ai-input]').value.trim();if(!text){say('붙여넣은 답변이 없습니다.');return;}if(!key){say('HASH_UNAVAILABLE');return;}
      const fromMailbox=!!(mailboxAnswer&&mailboxAnswer.key===key&&mailboxAnswer.answer.trim()===text);
      const entry=fromMailbox?{answer:text,saved_at:mailboxAnswer.saved_at,source:'MAILBOX',model:mailboxAnswer.model,report_date:reportDate}:{answer:text,saved_at:new Date().toISOString(),source:'PASTE',report_date:reportDate};
      if(R.saveAnswer(localStorage,key,entry)){mailboxAnswer=null;paint();}else say('DEVICE_STORAGE_UNAVAILABLE');};
    const mailbox=async(action)=>{try{const session=GoogleSheetQuotes.sessionFor(window,window.InvestmentAppConfig.googleSheetsClientId),sheet=GoogleSheetSetup.source(window);
      if(!session.state().connected||!sheet){say('구글 로그인과 시트 연결이 필요합니다(설정 → Google 첫 설정).');return;}
      if(action==='post'){await R.postInbox(session,sheet,{report_date:reportDate,kind,template:inboxText,data_sha256:key,now:new Date().toISOString()});say('ReportInbox에 오늘 템플릿(금액 숨김)을 넣었습니다.');}
      else{const found=await R.readOutbox(session,sheet,await R.hash(inboxText));if(!found){say('해시가 같은 답이 아직 없습니다.');return;}
        // Same path as a pasted answer: into the answer box, reviewed, and stored only by '검토한 답변 보관'.
        const card=live()&&host.querySelector('[data-report-export]'),input=card&&card.querySelector('[data-ai-input]');if(!input)return;
        input.value=found.answer;mailboxAnswer={key,answer:found.answer,model:found.model,saved_at:found.created_at||new Date().toISOString()};
        R.reviewInto(card,model);card.scrollIntoView({block:'start'});say('우체통 답을 가져와 검토했습니다. 아직 보관하지 않았습니다. 확인 뒤 \'검토한 답변 보관\'을 누르세요.');}
    }catch(e){say(String(e&&e.message||'MAILBOX_FAILED'));}};
    host.querySelector('[data-mailbox-post]').onclick=()=>void mailbox('post');
    host.querySelector('[data-mailbox-read]').onclick=()=>void mailbox('read');
    const rehearseButton=host.querySelector('[data-rehearsal-run]'),recordButton=host.querySelector('[data-recording-mode]');
    if(rehearseButton)rehearseButton.onclick=()=>void go('REHEARSAL');
    for(const b of host.querySelectorAll('[data-bench-period]'))b.onclick=()=>{benchSelection={...benchSelection,period:b.dataset.benchPeriod};rebench('[data-bench-period="'+b.dataset.benchPeriod+'"]');};
    const basisSelect=host.querySelector('[data-bench-basis]');if(basisSelect)basisSelect.onchange=()=>{benchSelection={...benchSelection,basis:basisSelect.value};rebench('[data-bench-basis]');};
    if(recordButton)recordButton.onclick=()=>{if(before){run.mode='RECORDING';void compose({state:'NOT_STARTED',reason_codes:['BEFORE_START_DATE']});}else void go('RECORDING');};
  };
  // Mock tabs: 비교 only with at least two sets (Set A + a user set B/C/D defined in the user's sheet).
  const setDefs=async()=>{try{return run.ledgerSheets?await run.ledgerSheets.definitions():null;}catch(_){return null;}};
  const mockTabs=defs=>[...R.MOCK_TABS,...(defs&&defs.count>=2?['COMPARE']:[])];
  // 비교 tab (decision 2026-10-11): rule-based numeric table of every set (VirtualTradingCompare, RAM only); the returns are
  // the ⑫⑬ ReportBenchmarks series. Phone (<1024px): 2–3 chosen sets; PC: all sets. One 【AI】 line in the export only.
  const composeCompare=async(result,runCfg,mode)=>{
    const C=window.VirtualTradingCompare,defs=await setDefs();if(!live()||run.mode!==mode||!C)return;
    const kinds=['SET_A','SET_B','SET_C','SET_D'].filter(k=>k==='SET_A'||(defs&&defs[k]));
    const entries=kinds.map(k=>{const{ledger,hits}=Runner.ledgerFor(result,k,runCfg),d=defs&&defs[k];return{id:d?d.id:k.toLowerCase(),kind:k,label:R.TABS[k]+(k==='SET_A'?(d&&!d.example?' · '+d.id:' · v1.1 예시'):''),purpose:d?d.purpose:null,ledger,hits};});
    let types=null;try{types=C.typesFrom(publicScreens['company-types-pricefree.json']);}catch(_){types=null;}
    const view=C.build(entries,{indices:result.indices||{},sources:result.sources||{},basis:benchSelection.basis,types});
    const wide=!window.matchMedia||window.matchMedia('(min-width: 1024px)').matches,ids=view.sets.map(s=>s.id);
    if(!Array.isArray(run.picked)||run.picked.some(x=>!ids.includes(x))||run.picked.length<2)run.picked=ids.slice(0,Math.min(3,Math.max(2,ids.length)));
    // 보고 불가 per set, on the report screen's own condition: the set's report model (same inputs as its tab) is UNAVAILABLE,
    // i.e. its ledger has not started and it holds nothing. States, reason codes and missing inputs only; no number is filled.
    const runnerOf=l=>({state:result.state==='READY'?(l.state==='OK'?'READY':'NOT_AVAILABLE'):result.state,reason_codes:result.state==='READY'?(l.state==='OK'?[]:l.reason_codes):result.reason_codes,sources:Runner.statusRows(result),progress:''});
    const blocked=entries.map(e=>({e,m:R.buildModel({kind:'MOCK',tab:e.kind,reportDate,ledger:e.ledger,names,config:cfg,runner:runnerOf(e.ledger),hits:e.hits,mode})})).filter(x=>R.unavailability(x.m).state==='UNAVAILABLE');
    const draw=()=>{if(!live())return;const hidden=R.hiddenSetting(localStorage);
      host.innerHTML=R.tabsNav(mockTabs(defs),'COMPARE')+blocked.map(x=>'<div data-compare-unavailable="'+esc(x.e.kind)+'">'+R.unavailableCard(x.m)+'</div>').join('')+C.html(view,{money:v=>R.money(v,{hidden}),picked:run.picked,wide,locale})
        +'<section class="card" data-compare-export><div class="sheet-actions"><button type="button" data-compare-copy>비교 템플릿 내보내기</button></div><p class="small">숫자 표와 한 줄 요약(【AI】) 칸만 담습니다. 금액은 숨김 설정을 따릅니다.</p><p role="status" data-compare-status></p></section>';
      for(const box of host.querySelectorAll('[data-compare-pick]'))box.onchange=()=>{const id=box.getAttribute('data-compare-pick'),next=box.checked?[...run.picked,id]:run.picked.filter(x=>x!==id);
        if(next.length>=2&&next.length<=3){run.picked=ids.filter(x=>next.includes(x));draw();}else box.checked=!box.checked;};
      host.querySelector('[data-compare-copy]').onclick=async()=>{const text=C.template(view,{money:v=>R.money(v,{hidden:R.hiddenSetting(localStorage),mode:'export'}),reportDate}),say=t=>{const n=host.querySelector('[data-compare-status]');if(n)n.textContent=t;};
        try{await navigator.clipboard.writeText(text);say('비교 템플릿을 복사했습니다.');}catch(_){const area=document.createElement('textarea');area.readOnly=true;area.value=text;area.rows=8;host.querySelector('[data-compare-export]').append(area);area.select();say('클립보드를 쓸 수 없어 아래 칸에 표시했습니다.');}};
      // Each 보고 불가 card names its set, keeps its own field id and copies its own set's prompt (DailyReport's document
      // handler copies the prompt of the report screen painted last, so the click stops here).
      for(const{e,m}of blocked){const box=host.querySelector('[data-compare-unavailable="'+e.kind+'"]');if(!box)continue;
        const title=box.querySelector('h2'),area=box.querySelector('[data-unavailable-prompt]'),label=box.querySelector('label[for="unavailable-prompt"]'),fid='unavailable-prompt-'+e.kind.toLowerCase();
        if(title)title.prepend(R.TABS[e.kind]+' · ');if(area)area.id=fid;if(label)label.htmlFor=fid;
        for(const b of box.querySelectorAll('[data-unavailable-copy]'))b.onclick=async ev=>{ev.stopPropagation();const which=b.getAttribute('data-unavailable-copy'),scope=box.querySelector('[data-unavailable-scope]'),status=box.querySelector('[data-unavailable-status]');
          const name=which==='all'?'전체':(R.AREAS.find(a=>a[0]===which)||[0,which])[1];area.value=R.unavailablePrompt(m,{area:which==='all'?null:which});if(scope)scope.textContent='· '+name;
          try{await navigator.clipboard.writeText(area.value);if(status)status.textContent=name+' 프롬프트를 복사했습니다.';}catch(_){area.focus();area.select();if(status)status.textContent='클립보드를 쓸 수 없어 프롬프트를 선택했습니다. 직접 복사하세요.';}};}};
    draw();
  };
  // Model from a runner result or a placeholder state. Nothing is stored: prices and ledgers stay in this closure.
  const compose=async(result,runCfg=cfg,mode='RECORDING',capture=null)=>{
    if(tab==='COMPARE')return composeCompare(result,runCfg,mode);
    const {ledger,hits,input}=Runner.ledgerFor(result,ledgerKind,runCfg),last=ledger.state==='OK'?ledger.days[ledger.days.length-1]:null;
    window.PlaybookScreen?.ingestRunner(result,names);
    // Q·G shown next to a judgement is the forward-ledger snapshot the engine used that day (else the public screen value).
    const shown={...qg};if(last&&input&&input.snapshots[last.date])for(const[c,r]of Object.entries(input.snapshots[last.date]))shown[c]={q:r.q,g:r.g};
    const runner={state:result.state==='READY'?(ledger.state==='OK'?'READY':'NOT_AVAILABLE'):result.state,reason_codes:result.state==='READY'?(ledger.state==='OK'?[]:ledger.reason_codes):result.reason_codes,sources:Runner.statusRows(result),progress:''};
    let signals=null;try{const history=result.snapshot_basis==='v2'&&VHistory?.v2Values?VHistory.v2Values(localStorage,qgvScores().profile.id):{scores:Runner.readVStore(localStorage),composition:Runner.readVComposition(localStorage)};signals=Signals?{...Signals.reportSignals(result,ledgerKind,runCfg,history.scores,history.composition),capture}:null;}catch(_){signals=null;}
    // ⑪⑫⑬ (ReportBenchmarks, pure, RAM): runner indices (SPY, ⑬ ETFs, KRW=X) + this tab's ledger and the comparison ledger.
    let bench=null,shownBench=null,track=null,nextBenchInputs=null;
    try{const RB=window.ReportBenchmarks;if(RB){
      const days=l=>l.state==='OK'?l.days.map(d=>({date:d.date,total_value:d.total_value,deposit:d.deposit})):[];
      const others=kind==='REAL'?['SET_A']:ledgerKind==='SET_A'?['SET_B']:['SET_A'];
      const ledgers=[{key:ledgerKind,state:ledger.state,reason_codes:ledger.reason_codes||[],days:days(ledger)},...others.map(k=>{const l=Runner.ledgerFor(result,k,runCfg).ledger;return{key:k,state:l.state,reason_codes:l.reason_codes||[],days:days(l)};})];
      nextBenchInputs={indices:result.indices||{},sources:result.sources||{},ledgers,start_date:runCfg.start_date};
      bench=RB.build({...nextBenchInputs,period:'20D',basis:'KRW'});shownBench=RB.build({...nextBenchInputs,...benchSelection});
      track=RB.trackRecord({hits,trades:ledger.state==='OK'?ledger.trades:[],ledger_input:input,ledger_reasons:ledger.reason_codes||[],start_date:runCfg.start_date,windows:cfg.hit_windows,min_samples:cfg.hit_min_samples});}}
    catch(_){bench=shownBench=track=nextBenchInputs=null;}
    const next=R.buildModel({kind,tab,reportDate,baseDates:last?{NYSE:last.date}:{},ledger,ram,qg:shown,names,config:cfg,runner,hits,mode,signals,rehearsal:result.rehearsal||null,bench,track});
    const nextCanonical=R.renderTemplate(next,{hidden:true,guide:false});let nextKey=null;try{nextKey=await R.hash(nextCanonical);}catch(_){nextKey=null;}
    if(!live()||run.mode!==mode)return;
    // The mailbox always writes amounts hidden with the guide; its Inbox/Outbox sha256 is the hash of exactly this text.
    // canonical/inbox use the default ⑬ selection (20D · KRW) so a stored AI answer stays attached to the day's data.
    if(kind==='MOCK')next.tabs=mockTabs(await setDefs());if(!live()||run.mode!==mode)return;
    model={...next,bench:shownBench};canonical=nextCanonical;key=nextKey;inboxText=R.renderTemplate(next,{hidden:true,guide:true});benchInputs=nextBenchInputs;
    if(kind==='REAL'&&mode==='RECORDING'&&result.state!=='LOADING')virtualShadow=last?{date:last.date,judgements:last.judgements,names:{...names}}:null;
    paint();
  };
  const before=reportDate<cfg.start_date;
  // One runner pass in the given mode. Both modes record the device V history (V only, independent of any ledger);
  // a rehearsal result carries mode REHEARSAL and must never reach a ledger/sheet writer.
  const go=async(mode)=>{
    if(!live())return;if(run.busy){run.pending=mode;run.mode=mode;void compose({state:'LOADING',reason_codes:['RUNNER_LOADING']},cfg,mode);return;}
    run.busy=true;run.mode=mode;if(mode==='REHEARSAL')await compose({state:'LOADING',reason_codes:['RUNNER_LOADING']},cfg,mode);
    try{
      let catalog=null;try{catalog=await deviceCatalog();}catch(_){catalog=null;}
      const progress=(done,total)=>{const n=live()&&host.querySelector('[data-runner-progress]');if(n)n.textContent=done+'/'+total;};
      const sheetOptions=run.ledgerSheets?await run.ledgerSheets.runnerOptions():{};
      const opts={config,catalog,reportDate,signal:run.controller.signal,onProgress:progress,...sheetOptions};
      const out=!catalog?{result:{state:'NOT_AVAILABLE',reason_codes:['PUBLIC_CATALOG_UNAVAILABLE'],sources:{},ledgers:{}},config:cfg}
        :mode==='REHEARSAL'?await Signals.rehearse(window,{...opts,qgRows:qg}):{result:await Runner.run(window,opts),config:cfg};
      let result=out.result,capture=null;if(mode==='REHEARSAL')result={...result,snapshot_basis:qgvScores().default};
      try{if(VHistory){const c=await VHistory.capture(window,result);result=c.result;capture=c.capture;if(VHistory.captureV2){const c2=await VHistory.captureV2(window,result,{identities:identityCompanies,publicScreens,preset:qgv2Profile.preset,gate:qgv2Profile.gate});result=c2.result;capture={...capture,v2:c2.capture};}}}catch(_){capture=null;}
      // D-10: only recording-mode results reach the ledger sheet module (it also refuses REHEARSAL results itself).
      if(mode!=='REHEARSAL'&&run.ledgerSheets)result=run.ledgerSheets.update(result);
      run.last=result;if(live()&&run.mode===mode)await compose(result,out.config,mode,capture);
    }catch(_){if(live()&&run.mode===mode)await compose({state:'NOT_AVAILABLE',reason_codes:['RUNNER_FAILED']},cfg,mode);}
    finally{run.busy=false;if(run.pending&&live()){const next=run.pending;run.pending=null;void go(next);}}
  };
  const start=()=>go('RECORDING');
  // Signing in to Google later (Settings) re-runs the runner for the open report: same session, no new scope or auth code.
  try{if(config.googleSheetsClientId){const session=GoogleSheetQuotes.sessionFor(window,config.googleSheetsClientId);
    run.unsubscribe=session.subscribe(()=>{if(!live()){if(reportRun===run)disposeReport();return;}if(session.state().connected&&run.last&&run.last.reason_codes.includes('AUTH_REQUIRED'))void go(run.mode);});}}catch(_){}
  // Before the start date the report stays NOT_STARTED (no request) until the user runs a rehearsal.
  await compose(before?{state:'NOT_STARTED',reason_codes:['BEFORE_START_DATE']}:{state:'LOADING',reason_codes:['RUNNER_LOADING']});
  if(before||!live())return;
  await start();
}
function showUnavailable() {
  $("#content").innerHTML=heading("DATA UNAVAILABLE",t("데이터를 열 수 없습니다."))+"<p>"+t("연결 상태를 확인한 뒤 다시 시도하세요.")+'</p><button id="retry">'+t("다시 시도")+"</button>";
  $("#retry").onclick=()=>location.reload();
  window.SearchUI?.setUnavailable();
}
function render(options) {
  // A render error (e.g. after a hashchange) shows the existing DATA UNAVAILABLE fallback instead of escaping
  // as an uncaught exception; the next navigation renders normally again.
  try {renderRoute(options);}
  catch(e) {console.error(e);showUnavailable();}
}
function renderRoute(options) {
  // {keep:true}: '자료 새로고침' or a freshness re-judgement draws the open screen again (data-refresh.js, G2). The user's scroll,
  // focus, open details, fields and view buttons come back. Detail -> source list also restores its in-tab view (G3).
  const kept=options&&options.keep&&location.hash===currentHash&&window.DataRefresh?.captureView?DataRefresh.captureView($("#content")):null;
  let [route,id,sub]=location.hash.slice(1).split("/");route=route || "home";
  let anchor=null;
  for(const screen of ["validation","technical","macro","news"]) if(route.startsWith(screen+"-")) {anchor=route;route=screen;}
  try {id=decodeURIComponent(id || "");} catch(e) {id="";}
  if(['company','analysis','technical'].includes(route)) researchCompanyId=id || null;
  // Same-company chart section navigation keeps the existing mount and its RAM inputs/results.
  // Company changes, screen exit and private-session disposal retain the normal lifecycle.
  if(!kept&&(anchor||id)&&route==='technical'&&currentRoute==='technical'&&currentHash!==location.hash&&
    (id||'asml')===$('[data-technical-symbol]')?.value&&$('[data-chart-workbench]')){
    currentHash=location.hash;syncNavigation(route);
    const nav=$('[data-ia-sub="technical"]');if(nav)nav.outerHTML=AppShell.subNavHtml(route);
    focusImplementedSection(anchor||'technical-chart');AppShell.afterRender(route);return;
  }
  if(currentHash!==location.hash&&['companies','watchlist'].includes(currentRoute)&&window.DataRefresh?.captureView){
    const view=DataRefresh.captureView($('#content'));
    // Keep only navigation controls. Group membership/name inputs must reflect settings changed on the detail screen.
    const fields=new Set(['search','only-interest','group-filter','company-sort','watch-group','watch-sort'].map(id=>'#'+id+'@0'));
    view.fields=view.fields.filter(([key])=>fields.has(key));
    directoryViews.set(currentRoute,{view,limit:listLimit});
  }
  window.PrivateHistory?.disposeAll();window.PrivateSubsetView?.disposeAll();
  window.GoogleSheetSetup?.disposeAll();
  window.ForwardValidation?.disposeAll();disposeReport();
  notice("");syncShell();
  const routes={home,brief,qgv,analysis:()=>analysis(id,sub||null),profiles,types,model,watchlist,technical:()=>technical(id),macro,thirteenf,validation,companies,portfolio,actual,leaderboard,news:()=>news(id),research,company:()=>detail(id),settings:settingsUI,entity:()=>entityDetail(id),report:()=>report(id),system:()=>IaScreens.treeHtml("system",appSettings.display_locale),tree:()=>IaScreens.treeHtml(AppShell.TREE_KEYS.includes(id)?id:"qgv",appSettings.display_locale),"lab-13f":()=>AppShell.pendingHtml("lab-13f",appSettings.display_locale),playbook:()=>heading("PLAYBOOK","플레이북 · 기록·채점·TARGET v1")+'<div id="playbook-screen"></div>'};
  if(!routes[route]) route="home";
  HomeScreen.park(route);
  if((route==='company'||route==='analysis')&&id) rawDataCompany=id;
  previousRoute=currentRoute;const previousHash=currentHash;currentRoute=route;currentHash=location.hash;
  // S04/S05 back link: remember the list it was opened from; keep it while moving between this company's screens.
  if(route==='company'||route==='analysis'){
    if(LIST_ORIGIN[previousRoute]) companyOrigin={id,hash:LIST_ORIGIN_HASH.test(previousHash)?previousHash:'#'+previousRoute};
    else if(!(companyOrigin && companyOrigin.id===id && (previousRoute===null || ['company','analysis','technical','news'].includes(previousRoute)))) companyOrigin=null;
    saveLeaderView();
  }
  // Coming back to S06 from S04/S05 (back link or browser back) restores its scroll; filters and sort always come from leaderboardView.
  const restoreLeader=route==='leaderboard' && ['company','analysis'].includes(previousRoute);
  const directoryView=!kept&&route!==previousRoute?directoryViews.get(route):null;
  const restoreDirectory=directoryView&&['company','analysis'].includes(previousRoute)&&companyOrigin?.hash===currentHash;
  if(route==='leaderboard' && id==='interest') leaderboardView={...leaderboardView,interest:true};
  $("#content").innerHTML=routes[route]();
  if(kept) DataRefresh.restoreFields($("#content"),kept);
  else if(directoryView) DataRefresh.restoreFields($('#content'),directoryView.view);
  if(route==='leaderboard') void PrivateSubsetView.mount($('#private-subset-root'),{locale:appSettings.display_locale,config:window.InvestmentAppConfig,interests:()=>DeviceWatchlist.pageIds(prefs.interests),onRanks:()=>{qgv2Quotes={};qgv2QuotesKey='';qgv2QuotesBasis=null;leaderPage=null;const pt=$('#universe-price-time');if(pt)pt.innerHTML=window.PriceTime?PriceTime.sourceHtml(PrivateSubsetView.priceBasis?.()||null,{locale:appSettings.display_locale}):'';if(leaderboardRows&&$('#leaderboard-screen'))paintLeaderboardScreen(leaderboardRows);}});
  if(['playbook','portfolio','company'].includes(route)&&window.PlaybookScreen){const place=route==='playbook'?$('#playbook-screen'):document.createElement('div');if(route!=='playbook')$('#content').append(place);void PlaybookScreen.mount(place,{catalogPromise:deviceCatalog(),scoreOptions:playbookScoreOptions,screens:publicScreens,idByTicker:new Map(identityCompanies.map(r=>[r.ticker,r.company_id])),publicCatalog,interests:DeviceWatchlist.allIds(prefs.interests),universeCodesPromise:fetch('universe-codes.json',{cache:'no-store'}).then(r=>r.ok?r.json():null).then(p=>p?.schema==='universe-codes/1'&&Array.isArray(p.codes)?p.codes:[]).catch(()=>[]),full:route==='playbook'}).catch(()=>{if(place.isConnected)place.textContent='플레이북 확인 불가 · 기기 기록을 읽을 수 없습니다.';});}
  if(route==='brief'&&window.PlaybookScreen){try{$('#content').insertAdjacentHTML('afterbegin',PlaybookScreen.todayHtml(localStorage));}catch(_){}}
  if(route==='actual') attachDeviceActual('#device-actual-root',true);
  if(route==='portfolio') {attachDeviceActual('#device-actual-summary',false);paintPortfolio();}
  if(route==='company' && window.UniverseCompany && !company(id) && universeCode(id)) void UniverseCompany.mount($('#content'),{locale:appSettings.display_locale,screens:publicScreens,shares:universeDirectory,quotes:qgv2Quotes,names:companyNames,catalogPromise:deviceCatalog(),config:window.InvestmentAppConfig});
  if(route==='company' && $('#company-holding')) void CompanyScreen.mountHolding($('#company-holding'),{locale:appSettings.display_locale,ticker:company(id)?.identity_only?company(id).ticker:null,catalogPromise:deviceCatalog()});
  // Tab choice is mirrored into the hash ('#analysis/<id>/<tab>') with replaceState: no new history entry, back leaves S05.
  if(route==='analysis') CompanyScreen.wireTabs($('#content'),{onSelect:key=>{try{history.replaceState(history.state,'','#analysis/'+encodeURIComponent(id)+(key==='summary'?'':'/'+key));currentHash=location.hash;}catch(_){}}});
  if((route==='company'||route==='analysis')&&window.Qgv2Inputs&&publicScreens[Qgv2Inputs.FILE]) void refreshQgv2Quotes(()=>{const h=location.hash.slice(1).split('/');if(h[0]===route&&$('[data-company-card="qgv"],[data-analysis-panel="factors"]'))repaintScores(routes[route]);});
  if(route==='company'||route==='analysis') paintValue(route,id);
  if(route==='model') {attachDeviceActual('#model-actual-summary',false);paintModel();}
  if(route==='brief') deviceCatalog().then(c=>{const n=$('#home-target-version');if(n?.isConnected)n.textContent=c.target_root_version||'NOT_AVAILABLE';}).catch(()=>{const n=$('#home-target-version');if(n?.isConnected)n.textContent='NOT_AVAILABLE';});
  if(route==='technical') {const cards=TechnicalCards.mount($('#technical-indicators'),{locale:appSettings.display_locale});
    const bench=window.ChartWorkbench&&$('#technical-workbench')?ChartWorkbench.mount($('#technical-workbench'),{locale:appSettings.display_locale}):null;
    if(bench) TechnicalCards.arrange($('#content'));
    PrivateHistory.mountTechnical($('#technical-price-chart'),{companyId:id,locale:appSettings.display_locale,config:window.InvestmentAppConfig,getAverage:deviceAverageCost,onData:value=>{cards.update(value);if(bench)void bench.update(value);}});
    // Display-only TradingView chart: follows the symbol picker; nothing is read back from it.
    const tvSymbol=$('#technical-price-chart [data-technical-symbol]'),tvChart=()=>TradingViewWidgets.mountAdvanced($('#technical-tv-chart'),{companyId:tvSymbol?tvSymbol.value:id,locale:appSettings.display_locale});
    if(tvSymbol) tvSymbol.addEventListener('change',()=>{researchCompanyId=tvSymbol.value;const suffix='/'+encodeURIComponent(tvSymbol.value);
      const section=location.hash.slice(1).split('/')[0]||'technical';
      history.replaceState(history.state,'','#'+section+suffix);currentHash=location.hash;
      const subnav=$('[data-ia-sub="technical"]');if(subnav)subnav.outerHTML=AppShell.subNavHtml('technical');
      for(const a of document.querySelectorAll('[data-screen-tab]'))a.href='#technical-'+a.dataset.screenTab+suffix;
      tvChart();});tvChart();}
  if(route==='brief') TradingViewWidgets.mountTickerTape($('#tv-ticker-tape'),{locale:appSettings.display_locale,companyIds:scopeIdList()});
  if(route==='company' && $('#tradingview-mini')) TradingViewWidgets.mountMini($('#tradingview-mini'),{companyId:id,locale:appSettings.display_locale});
  if(route==='company' && $('#private-history-chart')) void PrivateHistory.mount($('#private-history-chart'),{companyId:id,locale:appSettings.display_locale,config:window.InvestmentAppConfig,getAverage:deviceAverageCost,onData:value=>paintValue(route,id,value&&typeof value.close==='number'?{price:value.close,currency:value.currency,as_of:value.asOf,read_at:value.readAt||null,source:'PRIVATE_HISTORY_CLOSE'}:null)});
  // Price store (user's Prices_M tab): the first open of a company stores its 5-year month-ends once (counts shown only).
  if(route==='company' && window.PriceStore) {const symbol=PrivateHistory.symbolFor(id)||PriceStore.universeSymbol(id);if(symbol){const host=document.createElement('div');host.id='company-price-store';const anchor=$('#private-history-chart');if(anchor)anchor.after(host);else $('#content').append(host);PriceStore.mountCompany(host,{symbol,locale:appSettings.display_locale});}}
  if(route==='company'||route==='leaderboard'||route==='analysis') SecReported.mount($('#sec-reported-panel'),secReported,{companyId:route==='leaderboard'?undefined:id,locale:appSettings.display_locale});
  if(route==='report') void paintReport(id);
  if(route==='profiles') DeviceProfiles.mount($('#device-profile-editor'),{locale:appSettings.display_locale,qgFactors:()=>publicScreens['sec-qg-factors.json'],sessionQuotes:()=>qgv2Quotes,
   // S13 compare reads the same public inputs object, catalog and identities as every other screen (QgvScores.pageResult memo).
   v2Context:async()=>{let catalog=null;try{catalog=await deviceCatalog();}catch(_){catalog=null;}let inputs=window.Qgv2Inputs?publicScreens[Qgv2Inputs.FILE]||null:null;if(!inputs&&window.Qgv2Inputs){try{inputs=await Qgv2Inputs.load(window);}catch(_){inputs=null;}}return{inputs,identities:identityCompanies,catalog};}});
  if(route==='validation') ForwardValidation.mount($('#forward-validation-root'),{locale:appSettings.display_locale,config:window.InvestmentAppConfig,hosts:{outcome:$('#forward-validation-outcome'),eligibility:$('#forward-validation-eligibility')}});
  if(route==='types') DeviceProfiles.mount($('#device-type-editor'),{locale:appSettings.display_locale,mode:'types'});
  if(route==='macro') MacroLights.mount($('#macro-lights-root'),{bundle:publicScreens,locale:appSettings.display_locale,config:window.InvestmentAppConfig});
  if(route==='macro'&&window.MacroCycleRing) MacroCycleRing.mount($('#macro-cycle-ring-root'),{bundle:publicScreens,locale:appSettings.display_locale});
  if(route==='macro' && window.MacroEvidence) MacroEvidence.mount($('#macro-evidence-root'),{locale:appSettings.display_locale});
  mountPublicPanels(route,id);
  syncNavigation(route);
  const menu=window.AppShell?.menuFor(route);
  if(menu) $("#content").insertAdjacentHTML("afterbegin",`<p class="flow-step" data-flow-step="${esc(menu.num)}" data-menu="${esc(menu.key)}"><span class="flow-number">${esc(menu.num)}</span> ${esc(menu.label)}</p>`+AppShell.subNavHtml(route));
  if(QGV_CHILDREN.includes(route) || route==="research") {
    const parent=route==="research"?"validation":"qgv",key=parent==="qgv"?"← QGV":"← Lab",sub=QGV_SUBCATEGORY[route];
    const origin=(route==='company'||route==='analysis') && companyOrigin && companyOrigin.id===id?companyOrigin:null,back=origin?LIST_ORIGIN[origin.hash.slice(1).split('/')[0]]:null;
    $("#content").insertAdjacentHTML("afterbegin",`<p class="parent-row"><a class="parent-link" href="#${parent}">${esc(t(key))}</a>${back?`<a class="parent-link" href="${esc(origin.hash)}" data-origin-link="${esc(origin.hash.slice(1))}">${esc(back[appSettings.display_locale==='en-US'?1:0])}</a>`:""}${sub?`<span class="sub-category" data-sub-category>${esc(t(sub))}</span>`:""}</p>`);
  }
  if(["settings","actual","portfolio"].includes(route) && window.DeviceBackup?.mountRestoredNotice) {
    $("#content").insertAdjacentHTML("afterbegin",'<div id="backup-restored-notice"></div>');
    try {DeviceBackup.mountRestoredNotice($("#backup-restored-notice"),{locale:appSettings.display_locale,storage:localStorage});} catch(_) {}
  }
  if(Object.values(D).some(s=>s?.state==="DEMO")) $("#content").insertAdjacentHTML("afterbegin",'<div class="banner">'+t("DEMO 포함 · 합성 데이터는 투자 판단용이 아닙니다.")+"</div>");
  if(!storageOK) notice(t("개인 설정 저장을 사용할 수 없습니다. 내보내기를 이용하세요."));
  if(!settingsWritable) notice(t("설정을 읽을 수 없습니다. 저장된 원본은 보존합니다."));
  if(route==="settings") {
    $("#device-backup-export").onclick=()=>void exportDeviceBackup();
    $("#device-backup-import").onchange=async e=>{try{const f=e.target.files[0];if(!f||f.size>DeviceBackup.MAX_BYTES)throw Error("BACKUP_TOO_LARGE");await restoreDeviceBackup(JSON.parse(await f.text()));}catch(e){notice(e.message==='BACKUP_TOO_LARGE'?'백업 파일이 16MiB 상한을 초과합니다.':'BACKUP_RESTORE_FAILED');}};
    deviceCatalog().then(catalog=>{const host=$("#google-first-setup");if(host?.isConnected)void GoogleSheetSetup.mount(host,{catalog,config:InvestmentAppConfig,locale:appSettings.display_locale});});
    DevicePWA.mount($('#device-pwa-settings'),{locale:appSettings.display_locale});
    OpsStatus.mount($('#ops-status'),{secReported,secStatus:SecReported.status?.()||null,screens:publicScreens},{locale:appSettings.display_locale});
    attachGoogleSheetSettings();
    PrivateHistory.mountSettings($('#private-history-settings'),{locale:appSettings.display_locale});
    if(window.PriceStore) PriceStore.mountSettings($('#price-store-settings'),{locale:appSettings.display_locale,coreSymbols:()=>priceStoreCore(false)});
    PrivateTrades.mountSettings($('#private-trades-settings'),{locale:appSettings.display_locale});
    PrivateSubsetView.mountSettings($('#private-universe-settings'),{locale:appSettings.display_locale});
    attachDeviceApiSettings();
    CompanyLogos.mountSettings($('#company-logo-settings'),{locale:appSettings.display_locale});
    TradingViewWidgets.mountSettings($('#tradingview-settings'),{locale:appSettings.display_locale});
    const rawSelect=$("#raw-data-company");if(rawSelect)rawSelect.onchange=e=>{rawDataCompany=e.target.value;mountRawData();};
    $("#display-locale").onchange=e=>updateSettings({display_locale:e.target.value});
    $("#source-language").onchange=e=>updateSettings({source_language:e.target.value});
  }
  if(route==="companies") {
    if(!kept) listLimit=directoryView?directoryView.limit:30;paintCompanies();
    $("#search").oninput=$("#only-interest").onchange=$("#group-filter").onchange=$("#company-sort").onchange=()=>{listLimit=30;paintCompanies();};
    $("#more-companies").onclick=()=>{listLimit+=30;paintCompanies();};wireGroups();
  }
  if(route==='watchlist'||route==='leaderboard'){const prefix=route==='watchlist'?'watch':'leader';if(route==='leaderboard'&&id==='interest')$('#leader-interest').checked=true;for(const key of ['interest','group','sort'])$('#'+prefix+'-'+key).onchange=()=>paintDirectory(route);if(route==='leaderboard'&&$('#leader-target'))$('#leader-target').onchange=()=>paintDirectory(route);if(route==='leaderboard')$('#leader-query').oninput=()=>paintDirectory(route);paintDirectory(route);if(route==='watchlist'){wireGroups();paintDisclosures($('#watch-disclosures'),DeviceWatchlist.allIds(prefs.interests),appSettings.display_locale==='en-US'?'No disclosures or news for your interest companies.':'관심 기업의 공시·뉴스가 없습니다.');paintDartDisclosures($('#watch-dart-disclosures'),DeviceWatchlist.allIds(prefs.interests),appSettings.display_locale==='en-US'?'No DART disclosures for your interest companies.':'관심 기업의 DART 공시가 없습니다.');}}
  if(route==="news") {
    for(const name of ["news","network"]) $("#show-"+name).onclick=()=>{
      $("#news-pane").hidden=name!=="news";$("#network-pane").hidden=name!=="network";$("#news-disclosures").hidden=name!=="news";$("#news-dart-disclosures").hidden=name!=="news";
      $("#show-news").setAttribute("aria-pressed",name==="news");$("#show-network").setAttribute("aria-pressed",name==="network");
      const f=$("#network-frame");if(name==="network" && f && !f.getAttribute("src")) f.src=f.dataset.src;
    };
    $("#news-scope").onchange=()=>paintNews(id);paintNews(id);if(anchor==="news-network")$("#show-network").click();
    {const c=company(id);paintDisclosures($("#news-disclosures"),c?[c.company_id]:null);}
    {const c=company(id);paintDartDisclosures($("#news-dart-disclosures"),c?[c.company_id]:null);}
  }
  for(const f of document.querySelectorAll("iframe")) f.onload=()=>f.contentWindow.postMessage({type:"display_locale",locale:appSettings.display_locale},location.origin);
  if(restoreLeader) restoreLeaderView();
  else if(kept) DataRefresh.restoreView($("#content"),kept);
  else if(restoreDirectory) DataRefresh.restoreView($('#content'),directoryView.view);
  else window.scrollTo(0,0);
  if(anchor && !kept)focusImplementedSection(anchor);
  if(!kept && route==="qgv" && ["investments","companies","market","performance"].includes(id)) {
    const group=$("#qgv-"+id),title=group.querySelector("h2");
    group.scrollIntoView({block:"start"});title.focus({preventScroll:true});
  }
  AppShell.afterRender(route);
  if(route==="tree"||route==="system") IaScreens.mount($("#content"),{screens:publicScreens,catalog:publicCatalog,locale:appSettings.display_locale});
  HomeScreen.afterRender(route,{locale:appSettings.display_locale,id,resolve:(type,key)=>searchIndex.resolve(type,key),interests:DeviceWatchlist.pageIds(prefs.interests),company,screens:()=>publicScreens,scores:leaderScores,catalog:deviceCatalog});
}
function focusImplementedSection(anchor){
  // Existing controls, never a generated model result. Keep a market view; leave industry when entering economy/market.
  const cycle=anchor==='macro-industry'?'industry':anchor==='macro-cycle'?(window.MacroCycleRing?.snapshot().activeCycle==='market'?'market':'economy'):null;
  if(cycle){$('[data-cycle-tab="'+cycle+'"]')?.click();document.dispatchEvent(new CustomEvent('macro-cycle-focus',{detail:{cycle}}));}
  const targets={'technical-pattern':'[data-pattern-panel]','technical-notes':'[data-user-panel]',
    'macro-cycle':'#macro-cycle','macro-industry':'[data-cycle-ring="industry"]',
    'macro-mine':'[data-cycle-ring]:not([hidden]) [data-cycle-user-box]',
    'validation-backtest':'#plab-91','validation-forward':'#plab-92'};
  const section=targets[anchor]?$(targets[anchor]):document.getElementById(anchor);
  if(section){const title=section.querySelector('h2,h3')||section;title.setAttribute('tabindex','-1');title.focus({preventScroll:true});section.scrollIntoView({block:'start'});}
}
function wireGroups() {
  $("#new-group").onsubmit = (e) => {
    e.preventDefault();
    const name = $("#group-name").value.trim();
    if (!name) return;
    prefs.groups.push({ id: crypto.randomUUID(), name, members: [] });
    save();
    render();
  };
  $("#export").onclick = () => void exportDeviceBackup();
  $("#import").onchange = async (e) => {
    try {
      const f = e.target.files[0];
      if (!f || f.size > DeviceBackup.MAX_BYTES) throw Error(t("16MiB 이하 JSON을 선택하세요."));
      const payload = JSON.parse(await f.text());
      if (DeviceBackup.accepts(payload)) { await restoreDeviceBackup(payload); return; }
      const p = DeviceWatchlist.migrate(validatePrefs(payload)).prefs;
      prefs.interests = [...new Set([...prefs.interests, ...p.interests])];
      for (const g of p.groups) {
        const old = prefs.groups.find((x) => x.id === g.id);
        if (old) old.members = [...new Set([...old.members, ...g.members])];
        else prefs.groups.push(g);
      }
      save();
      render();
    } catch (err) {
      notice(t("가져오기 실패")+" · BACKUP_IMPORT_FAILED");
    }
  };
}
document.addEventListener("click", (e) => {
  const b = e.target.closest("button");
  if (!b) return;
  if (b.dataset.star) {
    const id = b.dataset.star;
    if (!toggleInterest(id)) return;
    document.querySelectorAll("[data-star]").forEach((x) => {
      if (x.disabled) return;
      const on = DeviceWatchlist.watched(prefs, x.dataset.star);
      x.textContent = on ? "★" : "☆";
      x.setAttribute("aria-pressed", on);
    });
    const listId=b.closest('[id]')?.id||null;
    // A chart that said "outside the range" (or the technical picker) is rebuilt for the new range; prices still load only on click.
    if(document.querySelector('[data-history-out-of-range],[data-uc-chart="NA"],[data-technical-unavailable]:not([hidden])')||(DeviceWatchlist.watched(prefs,id)===false&&document.querySelector('[data-technical-symbol],#private-history-chart [data-private-history],[data-uc-chart-host] [data-private-history]'))){render();return;}
    const route=location.hash.slice(1).split('/')[0];if(route==='companies'){paintCompanies();}if(route==='leaderboard'||route==='watchlist')paintDirectory(route);const groups=$('#groups');if(groups){const holder=document.createElement('div');holder.innerHTML=groupsUI();groups.innerHTML=holder.querySelector('#groups').innerHTML;}const ownGroups=$('#company-groups');if(ownGroups)ownGroups.innerHTML=companyGroups(id);
    // The list was re-rendered: keep keyboard focus on the same star (or the page title when the row was filtered out).
    if(!b.isConnected){const scope=listId&&document.getElementById(listId),next=(scope||document).querySelector('[data-star="'+CSS.escape(id)+'"]');if(next)next.focus({preventScroll:true});else focusHeading();}
  }
  if (b.dataset.rename) {
    const g = prefs.groups.find((g) => g.id === b.dataset.rename),
      input = [...document.querySelectorAll("[data-rename-input]")].find(
        (x) => x.dataset.renameInput === g.id,
      );
    if (input.value.trim()) {
      g.name = input.value.trim();
      save();
      render();
    }
  }
  if (b.dataset.delete) {
    prefs.groups = prefs.groups.filter((g) => g.id !== b.dataset.delete);
    save();
    render();
  }
});
document.addEventListener("change", (e) => {
  if (e.target.dataset.group) {
    const g = prefs.groups.find((g) => g.id === e.target.dataset.group),
      id = e.target.dataset.member;
    g.members = e.target.checked
      ? [...new Set([...g.members, id])]
      : g.members.filter((i) => i !== id);
    save();
  }
});
// Public research context: project only approved analysis fields. Device holdings, quotes,
// portfolio values, account settings and arbitrary evidence objects are never read or forwarded.
function researchPublicContext() {
  const out={fields:{},companies:[]}, states=["LIVE","FROZEN_SNAPSHOT","DEMO"];
  const privateAlias=/(?:ya29\.|spreadsheets\/|(?:api|app)[\s_-]*(?:key|secret)|(?:sheet|spreadsheet)[\s_-]*(?:id|url)|(?:access|refresh|auth|bearer)[\s_-]*token|client[\s_-]*secret|private[\s_-]*key|password|authorization\s*:\s*bearer)/i;
  const privateMetadataKeys=new Set([
    "quantity","quantities","shares","amount","cash","balance","account","accountnumber","accountid",
    "price","prices","quotes","fxrate","exchangerate","marketvalue","averagecost","avgcost","costbasis",
    "money","moneyvalue","mcap","cutoffmcap","marketcap","marketcapitalization","purchaseprice","networth",
    "holdings","positions","actualholdings","investedamount","totalcost","cost","valueamount","cashbalance",
    "portfolioamount","portfoliovalue","actualweight","spreadsheetid","spreadsheeturl","sheetid","sheeturl",
    "apikey","appkey","appsecret","accesstoken","refreshtoken","clientsecret","authtoken","bearertoken",
    "token","credential","credentials","secret","password","privatekey"
  ]);
  const privateMetadata=v=>(v.match(/[A-Za-z][A-Za-z0-9_-]*/g) || []).some(k=>privateMetadataKeys.has(k.replace(/[_-]/g,"").toLowerCase()));
  const token=v=>typeof v==="string" && /^[A-Za-z0-9_.:-]{1,128}$/.test(v) &&
    !privateAlias.test(v)?v:null;
  const text=v=>typeof v==="string" && v.length<=512 && !/[\r\n]/.test(v) &&
    !privateAlias.test(v) && !privateMetadata(v)?v:null;
  const instant=v=>text(v) && (/^\d{4}-\d{2}-\d{2}$/.test(v) || EXPIRES_AT.test(v))?v:null;
  const number=v=>typeof v==="number" && Number.isFinite(v)?v:null;
  const eligible=s=>s && states.includes(s.state) && s.data!==null && !s.withheld && instant(s.as_of) && text(s.source);
  const snapshotId=v=>token(v) && !privateMetadata(v)?v:null;
  const meta=(name,s)=>({section:name,state:s.state,as_of:instant(s.as_of),source:text(s.source),
    freshness:freshnessOf(name,s),snapshot_id:snapshotId(s.producer?.snapshot_id)});
  const pick=(v,numeric,codes)=>{
    const row={};for(const k of numeric) {const value=number(v?.[k]);if(value!==null) row[k]=value;}
    for(const k of codes) {const value=token(v?.[k]);if(value!==null && !privateMetadata(value)) row[k]=value;}
    return row;
  };
  const companies=new Map();
  for(const c of D.companies) if(token(c.company_id) && token(c.ticker)) {
    const entry={company_id:c.company_id,ticker:c.ticker};out.companies.push(entry);companies.set(c.company_id,entry);
  }
  for(const [name,numeric,codes] of [
    ["qgv",["Q_score","G_score","V_score","total_score","confidence"],["confidence","coverage_state"]],
    ["technical",[],["regime","execution_zone"]]
  ]) {
    const s=D[name];if(!eligible(s)) continue;
    const rows=[];
    for(const [id,v] of Object.entries(s.data || {})) if(companies.has(id)) {
      const values=pick(v,numeric,codes);if(Object.keys(values).length) rows.push({...companies.get(id),...values});
    }
    if(!rows.length) continue;
    const value={...meta(name,s),rows};
    if(name==="qgv") out.fields.qgv_snapshot_summary=value;
    else {out.fields.technical_input=value;out.fields.technical_screen_summary=value;}
  }
  const l=D.leaderboard;
  if(eligible(l)) {
    const rows=(Array.isArray(l.data?.rows)?l.data.rows:[]).filter(r=>companies.has(r?.company_id)).map(r=>
      ({...companies.get(r.company_id),...pick(r,["rank","total_score"],[])}));
    if(rows.length) out.fields.existing_system_candidates={...meta("leaderboard",l),rows};
  }
  const m=D.macro;
  if(eligible(m)) {
    const values=pick(m.data,[],["state","regime"]);
    if(Object.keys(values).length) {
      out.fields.macro_input={...meta("macro",m),values};out.fields.macro_snapshot_summary=out.fields.macro_input;
    }
  }
  // Resolve the explicit route/picker identity from public directories only. Do not infer from
  // quotes, holdings, the first catalog entry or a default technical chart symbol.
  let selected=null;
  if(token(researchCompanyId) && !privateMetadata(researchCompanyId)) {
    const matches=[...D.companies,...identityCompanies].filter(c=>c.company_id===researchCompanyId);
    if(matches.length) {
      const tickers=new Set(matches.map(c=>token(c.ticker) && !privateMetadata(c.ticker)?c.ticker:null));
      const names=new Set(matches.map(c=>text(c.name)).filter(Boolean));
      if(tickers.size===1 && !tickers.has(null) && names.size<=1)
        selected={company_id:researchCompanyId,ticker:[...tickers][0],name:[...names][0] || null};
    } else if(universeCode(researchCompanyId)) {
      const c=companyNames?.get(researchCompanyId);
      if(c && c.ticker===researchCompanyId.split(':')[1] && token(c.ticker) && !privateMetadata(c.ticker))
        selected={company_id:researchCompanyId,ticker:c.ticker,name:text(c.en_name)};
    }
  }
  // Frozen period/horizon/earnings_period/cutoffs have distinct meanings. No approved
  // mapping exists from chart ranges; never transfer a private chart object as metadata.
  out.selection={company:selected,period:null,period_reason:'PERIOD_MAPPING_UNSUPPORTED'};
  // This Web contract has no integrated judgment, coverage or its snapshot references.
  // Individual QGV coverage and available snapshot IDs do not establish those relationships.
  return out;
}
window.addEventListener("message", (e) => {
  const research=$("#research-frame");
  if(e.origin===location.origin && e.source===research?.contentWindow && e.data?.type==="research_public_context_request") {
    research.contentWindow.postMessage({type:"research_public_context",context:researchPublicContext()},location.origin);
    return;
  }
  const frame = $("#network-frame");
  if (
    e.origin !== location.origin ||
    e.source !== frame?.contentWindow ||
    !["interest", "ready", "display_locale_request"].includes(e.data?.type)
  )
    return;
  if(e.data.type==="display_locale_request") {
    if(AppLanguage.LOCALES.includes(e.data.locale)) updateSettings({display_locale:e.data.locale});
    return;
  }
  // The relationship graph key is the issuer (IA-7), the same key as the watchlist.
  const id = typeof e.data.id === "string" && DeviceWatchlist.issuerOf(e.data.id) === e.data.id ? e.data.id : byIssuer(e.data.id)?.company_id;
  if (e.data.type === "interest") {
    if (!id || !toggleInterest(id)) return;
  }
  frame.contentWindow.postMessage(
    {
      type: "interests",
      ids: prefs.interests.filter((i) => /^sec:\d{10}$/.test(i)),
    },
    location.origin,
  );
});
// Route change: move focus to the new page title (h1, tabindex=-1) without scrolling, unless the screen already focused
// something inside it (e.g. a QGV hub group). Keeps S06 scroll restoration intact.
function focusHeading(){const h=$('#content h1');if(!h)return;if(!h.hasAttribute('tabindex'))h.setAttribute('tabindex','-1');h.focus({preventScroll:true});}
window.addEventListener("hashchange", () => D && render());
window.addEventListener("hashchange", () => {if(!D)return;const a=document.activeElement;if(!a||a===document.body||!$('#content').contains(a))focusHeading();});
// S06 scroll position is kept while S06 is the open screen (RAM + sessionStorage, debounced).
// Crossing the phone width redraws the S06 table (narrow: rank, company, QGV + details button; wide: all shown columns).
try{const mq=window.matchMedia(window.LeaderboardScreen?.NARROW||'(max-width: 749.98px)');if(mq.addEventListener)mq.addEventListener('change',()=>{if(currentRoute==='leaderboard'&&leaderboardRows&&$('#leaderboard-screen'))paintLeaderboardScreen();});}catch(_){}
let leaderScrollTimer=0,leaderScrollFrame=0;
window.addEventListener("scroll",()=>{if(currentRoute!=='leaderboard'||leaderRestoring||leaderScrollFrame)return;leaderScrollFrame=requestAnimationFrame(()=>{leaderScrollFrame=0;if(currentRoute!=='leaderboard'||leaderRestoring)return;
  leaderboardView={...leaderboardView,scrollY:Math.max(0,Math.round(window.scrollY)),...leaderAnchor()};clearTimeout(leaderScrollTimer);leaderScrollTimer=setTimeout(saveLeaderView,200);});},{passive:true});
try {const saved=AppLanguage.read(localStorage);appSettings=saved.value;settingsWritable=saved.writable;}
catch(e) {settingsWritable=false;}
syncShell();
CompanyLogos.start(window);
// DART is scored as a reference target only. The Korean issuer never becomes a US universe point.
function dartReferenceRows(){
 try{const financials=publicScreens['dart-financials.json'],universe=publicScreens['sec-qgv2.json']?.records;
  if(!financials||!universe||!window.DartDisclosures)return{};
  const row=DartDisclosures.qgv2Reference(financials,universe);return row?{hanmi:row}:{};
 }catch(_){return{};}
}
Promise.all([...(["data.json","entities.json","sec-m2-candidates.json"].map(path=>fetch(path,{cache:"no-store"}).then(r=>{
  if(!r.ok) throw Error("HTTP "+r.status);return r.json();
}).catch(error=>{if(path==="sec-m2-candidates.json")return null;throw error;}))),DataRefresh.load(window),deviceCatalog().catch(()=>null)]).then(([data,catalog,candidates,{reported,screens},identities])=>{
  try{if(identities){DeviceMarket.emptyMarket(identities);identityCompanies=DeviceWatchlist.identities(identities);}}catch(_){identityCompanies=[];}QgvScores.setPageIdentities?.(identityCompanies);QgvScores.setPageProfile?.(()=>qgv2Profile);QgvScores.setPageReferences?.(()=>dartReferenceRows());// one quote set and the S06 official preset/gate for every screen (qgv-scores.js)
  publicScreens=screens;publicCatalog=identities||null;
  if(window.DartDisclosures?.loadFinancials)void DataRefresh.financials(window).then(financials=>{if(financials){publicScreens['dart-financials.json']=financials;if(window.QgvScores)refreshScoreViews();}});
  // Macro lights v1: public lights only until the device loads SPY on the macro screen (RAM, read by MacroLights.current()).
  try{MacroLights.setPublic(publicScreens);}catch(_){}
  secReported=reported;
  m2Candidates=guardM2Candidates(candidates);
  // GSQ-010: legacy public producer payloads are withheld, including membership/order.
  // The private device catalog and device/session data have their own boundary.
  const publicSections=["universe","qgv","technical","macro","portfolio","leaderboard","news","relationships","changes"];
  const safeData={schema_version:1,companies:[]};
  for(const name of publicSections) safeData[name]={state:"NOT_AVAILABLE",as_of:null,source:null,reason:"공개 가격 경계에 따라 제공되지 않습니다. (GSQ-010)",data:null};
  D=guardSections(safeData);publicEntities=catalog.entities.filter(e=>e.entity_type!=="COMPANY");rebuildSearchIndex();load();readLeaderView();render();paintGlobalSearch();void refreshHeldScope();
  // App open: with the price store on and Google connected, append the core symbols' daily bars after the last stored date.
  try{if(window.PriceStore) PriceStore.autoSync(window,{coreSymbols:()=>priceStoreCore(true)});}catch(_){}
}).catch(showUnavailable);
// '자료 새로고침' (data-refresh.js; FRONTEND_DATA_CONTRACT D1, D2, D5, D6): DataRefresh reads one public publication set and hands
// it over here at once. Device quotes, settings and private sessions stay. The open screen is repainted in place (no route
// re-mount, and no device quote collection while DataRefresh.quiet()), so no Worker or Sheets request is made.
function mountPublicPanels(route,id){for(const kind of ['qg','types','filings','macro','thirteenf']) PublicScreens.mount($('#public-'+kind),publicScreens,{kind,companyId:route==='company'?id:route==='settings'?rawDataCompanyId()||undefined:undefined,locale:appSettings.display_locale,...(kind==='thirteenf'?{catalog:publicCatalog,interests:DeviceWatchlist.allIds(prefs.interests)}:{})});}
window.addEventListener('public-data-updated',()=>{void refreshQgv2Quotes(refreshScoreViews);});// new inputs + the kept Universe read: S04/S05 rescore from the new page result
DataRefresh.attach(window,{route:()=>D?currentRoute:null,render,
 apply(set){publicScreens=set.screens;secReported=set.reported;try{MacroLights.setPublic(publicScreens);}catch(_){}if(set.shares)universeDirectory=set.shares;if(searchIndex){rebuildSearchIndex();paintGlobalSearch();}},
 inPlace(){if(!D)return false;const[route,raw]=location.hash.slice(1).split('/');let id='';try{id=decodeURIComponent(raw||'');}catch(_){id='';}
  if(!route||route==='home')return HomeScreen.refreshPersonal(DeviceWatchlist.pageIds(prefs.interests));
  if(route==='leaderboard'&&$('#leaderboard-screen')){paintDirectory(route);return true;}
  if((route==='company'||route==='analysis')&&id){refreshScoreViews();if(window.UniverseCompany&&universeCode(id))UniverseCompany.repaint($('#content'),{locale:appSettings.display_locale,screens:publicScreens,shares:universeDirectory,quotes:qgv2Quotes,names:companyNames,catalogPromise:deviceCatalog(),starHtml:star(id)});
   else{if(route==='analysis'){const f=document.createElement('div');f.innerHTML=analysis(id,location.hash.slice(1).split('/')[2]||null);const live=$('#content [data-analysis-panel="financials"]'),next=f.querySelector('[data-analysis-panel="financials"]');if(live&&next)live.innerHTML=next.innerHTML;}if(window.StatRadar)void StatRadar.mount(document,{catalogPromise:deviceCatalog()});}SecReported.mount($('#sec-reported-panel'),secReported,{companyId:id,locale:appSettings.display_locale});mountPublicPanels(route,id);return true;}
  if(route==='settings'&&$('#ops-status')){OpsStatus.mount($('#ops-status'),{secReported,secStatus:SecReported.status?.()||null,screens:publicScreens},{locale:appSettings.display_locale});mountRawData();return true;}
  return false;}});

async function exportDeviceBackup(){
  try{const catalog=await deviceCatalog();DeviceBackup.download(window,await DeviceBackup.read(window,catalog,{userObjects:!!$('#device-backup-user-objects')?.checked}));}
  catch(e){notice(e.message==='BACKUP_TOO_LARGE'?'백업 파일이 16MiB 상한을 초과합니다. 기록을 임의로 줄이지 않습니다.':'BACKUP_EXPORT_FAILED');}
}
async function restoreDeviceBackup(payload){
  const catalog=await deviceCatalog();DeviceBackup.parse(payload,catalog,DeviceMarket,AppLanguage);
  if(!confirm((appSettings.display_locale==='en-US'?'Replace device interests, groups, portfolio, profiles, investor stars and language settings?':'기기 관심 기업·그룹·포트폴리오·프로필·투자자 ★·플레이북 기록·언어 설정을 백업으로 바꿀까요?')+(payload.user_objects?(appSettings.display_locale==='en-US'?' User-written objects in the backup are merged in (nothing on this device is removed).':' 백업의 사용자 작성 객체는 이 기기 기록에 합칩니다(지우지 않음).'):'')))return;
  await DeviceBackup.restore(window,catalog,payload);load();const read=AppLanguage.read(localStorage);appSettings=read.value;settingsWritable=read.writable;render();
}
document.addEventListener('device-backup-restored',()=>{load();appSettings=AppLanguage.read(localStorage).value;render();});

// Reuse the app's current v2 profile and device Universe quotes in page memory after navigation.
function playbookScoreOptions(){return{quotes:typeof qgv2Quotes==='object'?qgv2Quotes:{},preset:typeof qgv2Profile==='object'?qgv2Profile.preset:null,gate:typeof qgv2Profile==='object'?qgv2Profile.gate:null,referenceRows:typeof dartReferenceRows==='function'?dartReferenceRows():{}};}

async function deviceAverageCost(symbol){
  const catalog=await deviceCatalog(),snapshot=await DeviceActual.readHoldings(window,catalog);
  if(!snapshot)return null;
  const ticker=symbol.replace(/\.(KS|T)$/,''),instrument=catalog.instruments.find(i=>i.ticker===ticker);
  if(!instrument)return null;
  const row=snapshot.themes.flatMap(t=>t.holdings).find(r=>DeviceMarket.canonical(r.security_reference)===DeviceMarket.canonical(instrument.security_reference));
  return row&&Number(row.quantity)>0&&row.currency===instrument.currency&&Number(row.average_cost)>0?Number(row.average_cost):null;
}

window.addEventListener('device-sheet-source-changed',()=>{if(location.hash==='#settings'){attachGoogleSheetSettings();PrivateTrades.mountSettings($('#private-trades-settings'),{locale:appSettings.display_locale});}});
