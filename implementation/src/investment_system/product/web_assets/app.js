"use strict";
let D,
  prefs = { version: 1, interests: [], groups: [] },
  storageOK = true,
  corruptStorage = false;
let identityCompanies=[],publicScreens={},deviceCatalogPromise;
function deviceCatalog() {
  if(!deviceCatalogPromise) deviceCatalogPromise=fetch('actual-catalog.json',{cache:'no-store'}).then(r=>{
    if(!r.ok) throw Error('PUBLIC_CATALOG_UNAVAILABLE');return r.json();
  }).catch(()=>{deviceCatalogPromise=null;throw Error('PUBLIC_CATALOG_UNAVAILABLE');});
  return deviceCatalogPromise;
}
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
  <div id="ops-status"></div><section class="card" id="device-pwa-settings"></section><section class="card"><h2>${t("금융 용어")}</h2>${["free_cash_flow","drawdown","operating_margin"].map(k=>`<p>${term(k)}</p>`).join("")}</section><section class="card"><h2>${appSettings.display_locale==='en-US'?'Device backup':'기기 백업·불러오기'}</h2><p>${appSettings.display_locale==='en-US'?'Interests, groups, portfolio and language settings. Quotes, tokens, sheet IDs and Worker address are excluded.':'관심 기업·그룹·포트폴리오·언어 설정을 함께 보관합니다. 시세·토큰·시트 ID·Worker 주소는 제외합니다.'}</p><button id="device-backup-export">${t("내보내기")}</button><label>${t("가져오기")} <input id="device-backup-import" type="file" accept="application/json"></label></section><div id="google-sheet-settings"></div><div id="private-history-settings"></div><div id="private-trades-settings"></div><div id="private-universe-settings"></div><div id="device-api-settings"></div>`;
}
function entityRoute(e) {return e.entity_type==="COMPANY"?"#company/"+encodeURIComponent(e.canonical_id):"#entity/"+encodeURIComponent(e.entity_type+":"+e.canonical_id);}
function entityRow(hit) {
  const e=hit.entity,c=e.entity_type==="COMPANY"?company(e.canonical_id):null;
  const held=c && D.portfolio.data?.holdings?.some(h=>h.company_id===c.company_id);
  const types={COMPANY:t("기업"),INDUSTRY:t("산업"),INVESTOR:t("투자자"),MACRO:t("거시지표")};
  return `<li class="item" data-entity-id="${esc(hit.canonical_entity_id)}"><a href="${entityRoute(e)}"><b>${esc(label(e))}</b> <span class="badge">${esc(t(types[e.entity_type] || e.entity_type))}</span><div class="meta">${esc(e.ticker || "")} · ${esc(e.canonical_label)}${e.localized_names?.["ko-KR"]?" · "+esc(e.localized_names["ko-KR"]):""}${e.industry?" · "+esc(e.industry):""}</div>${c?`<div class="meta">${held?t("Snapshot 보유")+" · ":""}${D.qgv.data?.[c.company_id]?t("QGV 제공"):t("분석 미연결")} · ${esc(D.qgv.as_of || D.universe.as_of || t("시점 미제공"))} · ${esc(D.universe.withheld && e.data_state===D.universe.withheld.claimed_state?D.universe.state:e.data_state || D.universe.state)}</div>`:""}</a></li>`;
}
function paintGlobalSearch() {
  const input=$("#global-search"),out=$("#global-results");
  if(!searchIndex || !input) return;
  const hits=searchIndex.search(input.value,{limit:12});
  out.hidden=!input.value.trim();
  out.innerHTML=hits.map(entityRow).join("") || `<li class="empty">${t("일치하는 항목이 없습니다.")}</li>`;
  window.investmentSearch=(query,options)=>searchIndex.search(query,options);
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
function save() {
  if (corruptStorage) {
    notice(
      t("기존 설정 손상: 원본을 보존했습니다. 현재 변경은 내보내기로 보관하세요."),
    );
    return;
  }
  try {
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
    if (s) prefs = validatePrefs(JSON.parse(s));
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
function star(id) {
  return `<button class="star" data-star="${esc(id)}" aria-label="${esc(company(id)?.ticker || id)} ${t("관심기업")}" aria-pressed="${prefs.interests.includes(id)}">${prefs.interests.includes(id)?"★":"☆"}</button>`;
}
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
  return `<li class="item"><a href="#company/${encodeURIComponent(c.company_id)}"><span class="ticker">${esc(c.ticker)}</span><div class="muted">${esc(label(e) || c.name)}${c.market_cap_rank?" · "+t("시총 #")+c.market_cap_rank:""}${c.demo?" · DEMO":""}</div></a>${star(c.company_id)}</li>`;
}
function summaryFor(name,id) {
  const s=D[name],v=s.data?.[id];
  return `<section class="card"><h2>${name==="qgv"?"QGV":t("Technical(기술적 분석)")}</h2>${state(s)}${v?`<dl>${(name==="qgv"?["Q_score","G_score","V_score","total_score","confidence","coverage_state"]:["regime","execution_zone","invalidation"]).map(k=>`<dt>${esc(term(k))}</dt><dd>${typeof v[k]==="number"?fmt(v[k]):esc(AppLanguage.fallback(v.presentation?.[k],appSettings.display_locale,AppLanguage.status(v[k] ?? t("미제공"),appSettings.display_locale)))}</dd>`).join("")}</dl>${evidence(v)}`:'<p class="empty">'+t("이 기업의 Snapshot 미제공")+"</p>"}</section>`;
}
function home() {
  const held=D.portfolio.data?.holdings || [];
  return heading("YOUR DAILY BRIEF",t("오늘의 투자 화면"),t("중요한 변화부터 확인하고, 근거까지 따라가세요."))+
  `<section class="card" data-integrated-judgement><h2>${t("통합 판단")}</h2><p class="small">${esc(t("규칙 잠정 버전"))}</p><dl>${[["QGV","qgv"],[t("기술"),"technical"],[t("매크로"),"macro"]].map(([label,name])=>`<dt>${esc(label)}</dt><dd><span class="badge ${esc(D[name].state)}">${esc(D[name].state)}</span></dd>`).join("")}</dl><p data-judgement-result>${esc(t(["qgv","technical","macro"].every(n=>D[n].data!==null)?"세 시스템 결과를 나란히 확인하세요.":"자료가 부족해 통합 판단을 만들지 않습니다."))}</p><p class="small">${esc(t("매수·매도 지시 아님, 주문 기능 없음"))}</p></section>`+
  `<section class="card hero"><div class="row"><h2>${t("Portfolio(포트폴리오)")}</h2><a href="#portfolio">${t("자세히 →")}</a></div><div class="metric">${D.portfolio.data?held.length+" "+t("종목 보유"):t("연결 대기")}</div><p class="muted">${D.portfolio.data?esc(D.portfolio.data.role || t("제공된 Snapshot")):t("실제 보유·평가금액·수익률을 연결하면 여기서 확인합니다.")}</p>${state(D.portfolio)}</section>
  <div class="grid home-grid">${block("changes",t("오늘 / 최근 주요 변화"),`<p>${esc(AppLanguage.fallback(D.changes.data?.summary_localized,appSettings.display_locale,D.changes.data?.summary || ""))}</p>`)}${block("macro",t("Macro(거시환경)"),`<p>${esc(AppLanguage.status(D.macro.data?.state || "",appSettings.display_locale))} · ${esc(D.macro.data?.regime || "")}</p>`)}</div>
  <section class="card"><h2>${t("Attention(확인 필요)")}</h2><p class="small">${D.universe.state==="FROZEN_SNAPSHOT"?t("기업 목록은")+" "+esc(D.universe.as_of)+" "+t("과거 스냅샷입니다. 최신 시세·분석이 아닙니다."):t("출처와 데이터 시점을 확인하세요.")}</p><div class="chips"><a href="#companies">${t("관심기업")} ${prefs.interests.length} →</a><a href="#leaderboard">Leaderboard →</a></div></section>
  <details><summary>${t("분석 · 뉴스 · 관계 변화 더보기")}</summary><div class="grid">${block("qgv",t("QGV 변화"),"<p>"+t("변화량은 upstream changes가 제공할 때만 표시합니다.")+"</p>")}${block("technical",t("Technical 변화"),"<p>"+t("최근 신호는 기업 상세에서 확인하세요.")+"</p>")}${block("news",t("관심기업 뉴스"),'<a href="#news">'+t("뉴스 열기 →")+"</a>")}${block("relationships",t("Relationship changes(관계 변화)"),'<a href="#news">'+t("관계망 열기 →")+"</a>")}</div></details>`+
  `<section class="card" data-system-flow><h2>${t("시스템")}</h2><div class="hub-grid">${[["1","QGV","#qgv","qgv"],["2",t("기술적 분석"),"#technical","technical"],["3",t("매크로"),"#macro","macro"],["4",t("검증·연구"),"#validation",null]].map(([n,label,href,name])=>`<a class="card hub-card" href="${href}"><h3><span class="flow-number">${n}</span> ${esc(label)}</h3><span class="badge ${name?esc(D[name].state):"NOT_AVAILABLE"}">${name?esc(D[name].state):"NOT_AVAILABLE"}</span></a>`).join("")}</div></section>
  <section class="card" data-data-basis><h2>${t("데이터 기준")}</h2><dl><dt>${t("목표 비중 버전")}</dt><dd id="home-target-version">—</dd><dt>${t("QGV 기준 버전")}</dt><dd>${esc(t("v1 · 보정 전"))}</dd><dt>${t("시세·환율")}</dt><dd>${esc(t("이 기기에서만 입력·계산"))}</dd><dt>${t("보유 정보")}</dt><dd>${esc(t("이 기기에만 저장"))}</dd></dl><a href="#settings">${t("데이터 운영 상태 →")}</a></section>`;
}
function directoryFilters(prefix,watch=false) {
 return `<div class="chips"><label><input type="checkbox" id="${prefix}-interest" ${watch?"checked disabled":""}>${t("관심기업만")}</label><select id="${prefix}-group" aria-label="${t("그룹 필터")}"><option value="">${t("모든 그룹")}</option>${prefs.groups.map(g=>`<option value="${esc(g.id)}">${esc(g.name)}</option>`).join("")}</select><select id="${prefix}-sort" aria-label="${t("정렬")}"><option value="${watch?"added":"ticker"}">${watch?t("추가한 순"):t("티커 순")}</option><option value="name">${t("기업명 순")}</option><option value="favorites">${t("관심기업 우선")}</option></select></div>`;
}
function companyGroups(id){return `<p class="small">${t("관심·그룹은 이 기기에만 저장됩니다.")}</p>${prefs.groups.length?prefs.groups.map(g=>`<label><input type="checkbox" data-group="${esc(g.id)}" data-member="${esc(id)}" ${g.members.includes(id)?"checked":""} ${prefs.interests.includes(id)?"":"disabled"}>${esc(g.name)}</label>`).join(""):`<a href="#watchlist">${t("그룹 관리 →")}</a>`}`;}
function weekFilings(){const p=publicScreens["sec-filing-windows.json"],rows=p?.data?.companies;if(!rows)return "NOT_AVAILABLE";const known=prefs.interests.filter(id=>rows[id]&&rows[id].state!=="NOT_AVAILABLE");if(!known.length)return "NOT_AVAILABLE";return known.filter(id=>PublicScreens.windowThisWeek(rows[id])).length+" · "+esc(t("예상 시기 · 확정일 아님"));}
function watchlist(){return heading("WATCHLIST",t("관심 기업"))+directoryFilters("watch",true)+`<p class="meta">${t("이 휴대폰에만 저장 · 백업으로 이동")}</p><div class="grid">${["평균 QGV","재평가 신호","이번 주 실적","새 뉴스"].map(x=>`<section class="card"><h2>${t(x)}</h2><p${x==="이번 주 실적"?" data-week-filings":""}>${x==="이번 주 실적"?weekFilings():"NOT_AVAILABLE"}</p></section>`).join("")}</div><ul class="list" id="watchlist-company-list"></ul><a href="#leaderboard/interest">${t("리더보드에서 관심 기업만 보기 →")}</a><details><summary>${t("관심기업 · Groups(그룹) 관리")}</summary>${groupsUI()}</details>`;}
function companies() {
  return heading("COMPANIES",t("기업 탐색"))+`<input type="search" id="search" aria-label="${t("기업 검색")}" placeholder="${t("티커 또는 기업명 검색")}"><div class="chips"><label><input type="checkbox" id="only-interest"> ${t("관심기업만")}</label><select id="group-filter" aria-label="${t("그룹 필터")}"><option value="">${t("모든 그룹")}</option>${prefs.groups.map(g=>`<option value="${esc(g.id)}">${esc(g.name)}</option>`).join("")}</select></div><select id="company-sort" aria-label="정렬"><option value="ticker">티커 순</option><option value="name">기업명 순</option><option value="favorites">관심기업 우선</option></select><p class="meta">${D.universe.withheld?esc(D.universe.state)+" · "+esc(t(D.universe.withheld.reason || WITHHELD_REASON)):esc(D.universe.as_of)+" · FROZEN_SNAPSHOT / DEMO"}</p><ul class="list" id="company-list"></ul><button id="more-companies">${t("더보기")}</button><details><summary>${t("관심기업 · Groups(그룹) 관리")}</summary>${groupsUI()}</details>`;
}
function groupsUI() {
  return `<p class="muted">${t("이 기기의 브라우저에 저장됩니다. 즐겨찾기와 관심기업은 같은 목록입니다.")}</p><form id="new-group"><label for="group-name">${t("새 그룹 이름")}</label><div class="row"><input id="group-name" required maxlength="60" placeholder="${t("예: 반도체")}"><button>${t("그룹 만들기")}</button></div></form><div id="groups">${prefs.groups.map(g=>`<div class="group"><b>${esc(g.name)}</b> <span class="muted">${g.members.length} ${t("개")}</span><div class="row"><input aria-label="${t("그룹 이름")} ${esc(g.name)}" data-rename-input="${esc(g.id)}" value="${esc(g.name)}" maxlength="60"><button data-rename="${esc(g.id)}">${t("이름 변경")}</button><button data-delete="${esc(g.id)}">${t("그룹 삭제")}</button></div>${prefs.interests.map(id=>`<label><input type="checkbox" data-group="${esc(g.id)}" data-member="${esc(id)}" ${g.members.includes(id)?"checked":""}> ${esc(company(id)?.ticker || id)}</label>`).join("")}</div>`).join("")}</div><div class="toolbar"><button id="export">${t("내보내기")}</button><label>${t("설정 병합 가져오기")} <input type="file" id="import" accept="application/json"></label></div>`;
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
  const candidate=Object.hasOwn(m2Candidates.companies,id)?m2Candidates.companies[id]:null;
  const historySymbol=PrivateHistory.symbolFor(id);
  if((!c || c.identity_only) && (candidate || historySymbol)) return CompanyScreen.summary({locale:appSettings.display_locale,id,screens:publicScreens,
    headerHtml:`<div class="row">${heading("COMPANY RESEARCH",esc(candidate?.ticker || historySymbol || c?.ticker || ""),esc(c?.name || ""))}${star(id)}</div>`,groupsHtml:companyGroups(id),candidateHtml:m2Panel(id)});
  if(!c) return heading("COMPANIES",t("기업을 찾을 수 없습니다."))+'<a href="#companies">'+t("기업 목록 →")+"</a>";
  const h=D.portfolio.data?.holdings?.find(r=>r.company_id===id),e=searchIndex.resolve("COMPANY",id);
  return `<a class="small" href="#companies">${t("← 기업 목록")}</a><div class="row">${heading("COMPANY DETAIL",esc(c.ticker),esc(label(e) || c.name))}${star(id)}</div><div id="private-history-chart"></div><div id="sec-reported-panel"></div><div class="grid">${summaryFor("qgv",id)}${summaryFor("technical",id)}</div>`+
  block("macro",t("Macro exposure / context(거시 노출)"),`<p>${esc(D.macro.data?.regime || "")}</p><p>${t("기업 노출:")} ${esc(D.macro.data?.exposures?.[id] || t("미제공"))}</p>`)+
  `<section class="card"><h2>${t("Portfolio status(보유 상태)")}</h2>${state(D.portfolio)}<p>${h?t("Snapshot에 포함 · 비중")+" "+(Number.isFinite(h.actual_weight)?pct(h.actual_weight):"NOT_AVAILABLE"):D.portfolio.data?t("제공된 Snapshot에 없음"):t("실제 보유 상태 미제공")}</p>${h && Number.isFinite(h.target_weight)?`<p class="small" data-weight-kind="TARGET">TARGET · ${t("모델 비중")} ${pct(h.target_weight)}</p>`:""}${h?evidence(h):""}</section><section class="card"><h2>${t("News / Relationships(뉴스·관계)")}</h2>${state(D.news)}<a href="#news/${encodeURIComponent(id)}">${t("이 기업의 뉴스·관계망 확인 →")}</a></section>${evidence(c)}`;
}
function analysis(id) {
  const c=company(id),candidate=Object.hasOwn(m2Candidates.companies,id)?m2Candidates.companies[id]:null,historySymbol=PrivateHistory.symbolFor(id);
  if(!c && !candidate && !historySymbol) return heading("COMPANIES",t("기업을 찾을 수 없습니다."))+'<a href="#companies">'+t("기업 목록 →")+"</a>";
  const ticker=candidate?.ticker || historySymbol || c?.ticker || "";
  return CompanyScreen.analysis({locale:appSettings.display_locale,id,ticker,screens:publicScreens,headerHtml:`<div class="row">${heading("COMPANY ANALYSIS",esc(ticker),esc(c?.name || ""))}${star(id)}</div>`});
}
function paintPortfolio() {
  const host=$("#portfolio-screen");
  if(!host) return;
  const run=()=>{
    if(!host.isConnected) {document.removeEventListener("device-actual-changed",run);return;}
    const locale=appSettings.display_locale,idByTicker=new Map(identityCompanies.map(r=>[r.ticker,r.company_id]));
    deviceCatalog().then(async catalog=>{
      const ram=await DeviceActual.ramView(window,catalog);
      if(host.isConnected) PortfolioScreen.paint(host,{locale,catalog,ram,screens:publicScreens,idByTicker});
    }).catch(()=>{if(host.isConnected) PortfolioScreen.paint(host,{locale,catalog:null,ram:{state:"NOT_AVAILABLE",reason:"READ_FAILED",stale:false,quote_as_of:null,rows:[],themes:[]},screens:publicScreens,idByTicker});});
  };
  document.addEventListener("device-actual-changed",run);
  run();
}
function portfolio() {
  const p=D.portfolio.data;
  return heading("PORTFOLIO",t("내 포트폴리오"))+`<div id="portfolio-screen">${PortfolioScreen.shell(appSettings.display_locale)}</div>`+`<section class="card"><h2>ACTUAL · ${appSettings.display_locale==='en-US'?'This device':'이 기기'}</h2><a href="#actual" class="button">${appSettings.display_locale==='en-US'?'Enter / manage ACTUAL holdings':'ACTUAL 입력·관리'}</a><div id="device-actual-summary" aria-live="polite"></div></section>`+block("portfolio",t("보유 현황"),`<p>${esc(p?.role || "")}</p><dl><dt>${t("수익률")}</dt><dd>${pct(p?.return)}</dd><dt>${t("평가금액")}</dt><dd>${fmt(p?.market_value)} ${esc(p?.currency || "")}</dd><dt>${t("Exposure(노출)")}</dt><dd>${esc(p?.exposure?JSON.stringify(p.exposure):t("미제공"))}</dd></dl><ul class="list">${(p?.holdings || []).map(h=>`<li class="item"><a href="#company/${encodeURIComponent(h.company_id)}"><b>${esc(h.ticker)}</b><div class="muted">${t("실제 비중")} ${Number.isFinite(h.actual_weight)?pct(h.actual_weight):"NOT_AVAILABLE"} · ${t("수익률")} ${pct(h.return)}</div>${Number.isFinite(h.target_weight)?`<div class="small" data-weight-kind="TARGET">TARGET · ${t("모델 비중")} ${pct(h.target_weight)}</div>`:""}</a>${star(h.company_id)}</li>`).join("")}</ul>`)+
  `<div class="grid">${block("qgv",t("QGV context(QGV 맥락)"),'<a href="#companies">'+t("기업별 분석 →")+"</a>")}${block("technical",t("Technical context(기술적 분석 맥락)"),'<a href="#companies">'+t("기업별 신호 →")+"</a>")}${block("macro",t("Macro context(거시 맥락)"),`<p>${esc(D.macro.data?.regime || "")}</p>`)}</div><a href="#news">${t("중요 뉴스·관계 변화 →")}</a>`;
}
function leaderboard() {
  const l=D.leaderboard.data;
  return heading("LEADERBOARD",appSettings.display_locale==='en-US'?"Company research":"기업 연구")+
  `<details><summary>${appSettings.display_locale==='en-US'?'My device':'내 기기 기준'}</summary><div id="private-subset-root"></div></details>`+directoryFilters('leader')+'<div id="leaderboard-screen"></div><p class="small">고정 대상 기업의 이름·코드 · 가격·공식 순위 미포함</p><ul class="list" id="leader-company-list"></ul><div id="sec-reported-panel"></div><div id="public-qg"></div><div id="leader-m2-panel">'+m2Panel()+'</div>'+block("leaderboard",t("제공된 Leaderboard"),`<ul class="list">${(l?.rows || []).map(r=>`<li class="card"><a href="#company/${encodeURIComponent(r.company_id)}"><b>#${esc(r.rank)} ${esc(r.ticker)}</b></a>${star(r.company_id)}<dl>${[[t("시총 순위"),r.market_cap_rank],["QGV",r.total_score],[t("Daily move(전일 등락)"),r.daily_move],[t("Consensus(컨센서스)"),r.consensus],[t("Scenario(시나리오)"),r.scenario],[t("Reevaluation(재평가 기준)"),r.reevaluation_trigger]].map(([k,v])=>`<dt>${t(k)}</dt><dd>${fmt(v)}</dd>`).join("")}</dl>${evidence(r)}</li>`).join("")}</ul>`);
}
function news(id) {
  const c=company(id);
  return heading("NEWS / NETWORK",t("뉴스와 연결"),c?esc(c.ticker)+" "+t("기업 문맥"):t("Portfolio · 관심기업 · 기타 중요뉴스"))+
  `<div class="chips toolbar" role="group" aria-label="${t("콘텐츠 전환")}"><button id="show-news" aria-pressed="true">${t("뉴스")}</button><button id="show-network" aria-pressed="false">${t("관계망")}</button>${c?star(id):""}</div><p class="small" data-news-overlay>${t("정보 제공용, 투자 판단 덧씌우기(Overlay)는 기본 OFF")} · ${t("뉴스 무료 출처 미정: NOT_AVAILABLE")}</p><div class="chips" data-news-scopes>${["전체","관심 기업","내 포트폴리오","업종","매크로","정치","경제"].map(x=>`<span class="badge">${esc(t(x))}</span>`).join("")}</div><section id="news-pane"><select id="news-scope" aria-label="${t("뉴스 범위")}"><option value="all">${t("전체 중요뉴스")}</option><option value="interest">${t("관심기업")}</option><option value="portfolio">Portfolio</option></select>${state(D.news)}<ul id="news-list" class="list"></ul></section><section id="network-pane" hidden><p class="muted">${t("Fact = 확인된 관계 · Impact = 잠재 영향 경로")}</p>${state(D.relationships)}${D.relationships.data?'<iframe title="'+esc(t("News Network(뉴스 관계망)"))+'" data-src="network.html" id="network-frame"></iframe>':'<p class="empty">'+t("Track D 운영 관계망 미연결")+"</p>"}</section>`;
}
function research() {
  return heading("RESEARCH",t("질문에서 근거로"),t("Prompt → Context / Variables → Preview → Copy"))+'<p class="badge">FROZEN_SNAPSHOT · PLV1_CONTENT_V1.0</p><iframe title="'+esc(t("Prompt Library(프롬프트 라이브러리)"))+'" src="research.html" id="research-frame"></iframe>';
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
    `<div class="chips data-badges"><span class="badge">${esc(t("점수 기준 v1 · 보정 전"))}</span><span class="badge">${esc(t("미국 상위 500 · 목표 범위"))}</span></div>`+
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
function technical() {
  const s=D.technical,tabs=[["chart","차트"],["state","상태"],["execution","실행"],["record","기록"]];
  return `<div data-ia-screen="technical">${heading("TECHNICAL",t("기술적 분석"),t("기존 기록의 연결 상태를 확인합니다."))}
    <div class="chips data-badges"><span class="badge">${esc(t("실데이터 검증 전 · 일봉·수정주가 기준"))}</span></div>
    <nav class="chips screen-tabs" aria-label="${esc(t("기술적 분석"))}">${tabs.map(([id,label])=>`<a href="#technical-${id}" data-screen-tab="${id}">${esc(t(label))}</a>`).join("")}</nav>
    <div id="technical-chart"><div id="technical-price-chart" data-tech-status="chart"></div></div>
    <section class="card status-card" id="technical-state" data-tech-status="engine"><h2>${t("기술적 분석 엔진")}</h2>${state(s)}<p>${esc(t(s.data===null?s.reason || "운영 Snapshot이 연결되지 않았습니다.":"기존 종목 화면에서 제공된 기술적 분석 기록을 확인합니다."))}</p><p class="small">${esc(t("QGV 원점수와 기술적 상태는 나란히 볼 뿐 통합하지 않습니다."))}</p></section>
    <section class="card" id="technical-execution" data-tech-status="execution"><h2>${t("실행 구간 (시스템 주문 아님)")}</h2><p><span class="badge NOT_AVAILABLE">NOT_AVAILABLE</span> ${esc(t("검증된 모델 입력이 없어 실행 구간을 만들지 않습니다."))}</p></section>
    <section class="card" id="technical-record" data-tech-status="record"><h2>${t("기술적 기록")}</h2><p><span class="badge NOT_AVAILABLE">NOT_AVAILABLE</span> ${esc(t("과거 신호와 실제 결과 기록이 아직 없습니다."))}</p></section>
    </div>`;
}
function macro() {
  return `<div data-ia-screen="macro">${heading("MACRO",t("매크로"),t("공식 축별 상태를 확인합니다."))}
    <div class="chips data-badges"><span class="badge">${esc(t("엔진 v0.1.1 확정 · v0.1.4 후보(기본 아님)"))}</span></div>
    <section class="card" data-macro-status><h2>${t("상태판")}</h2><p><span class="badge NOT_AVAILABLE">NOT_AVAILABLE</span> ${esc(t("정상·경고·비상 판정에 필요한 실제 입력이 연결되지 않았습니다."))}</p>
    <h3>${t("현재 국면")}</h3><p data-macro-regime>${esc(t("자료 없음"))}</p><p class="small">${esc(t("8개 축의 6칸은 따로 보관하며 하나의 점수로 합치지 않습니다. FRED/ALFRED는 사용하지 않습니다."))}</p></section>
    <div id="public-macro"></div></div>`;
}
function thirteenf() {
  return heading("SEC 13F",t("투자자 13F"))+ '<div id="public-thirteenf"></div>';
}

function validation() {
  const tabs=[["paper","모의투자","준비 중","공개 앱에 연결된 모의투자 결과가 없습니다."],["backtest","백테스트","준비 중","공개 앱에 연결된 백테스트 결과가 없습니다."],["forward","전진 검증","준비 중","공개 앱에 연결된 전진검증 결과가 없습니다. 시작 시점은 사용자가 결정합니다."],["track","Track Record","준비 중","공개 앱에 연결된 성과 기록이 없습니다."],["trials","실험 기록","준비 중","공개 앱에 연결된 실험 기록이 없습니다."]];
  return heading("VALIDATION",t("검증·연구"),t("리서치와 검증 기록의 준비 상태를 확인합니다."))+
    `<div class="chips data-badges"><span class="badge">${esc(t("PIT 시점 기준 데이터만"))}</span><span class="badge">${esc(t("Holdout 기간 미정·사용 금지 · 보호 판정 UNCONFIRMED"))}</span></div>`+
    `<nav class="chips screen-tabs" aria-label="${esc(t("검증·연구"))}">${tabs.map(([id,label])=>`<a href="#validation-${id}" data-screen-tab="${id}">${esc(t(label))}</a>`).join("")}<a href="#research" data-screen-tab="research">${esc(t("리서치"))}</a></nav>`+
    `<div class="hub-grid" data-hub="validation">${tabs.map(([id,title,status,reason])=>`<div id="validation-${id}">${hubCard(title,status,reason)}</div>`).join("")}${hubCard("리서치","사용 가능","기존 프롬프트 라이브러리를 엽니다.","#research")}</div>`;
}
// Design canvas S01~S16: analysis flow numbers and QGV sub-categories (navigation only).
const FLOW_STEPS=Object.freeze({qgv:[1,"QGV"],technical:[2,"기술적 분석"],macro:[3,"매크로"],validation:[4,"검증·연구"]});
const QGV_SUBCATEGORY=Object.freeze({portfolio:"내 투자",actual:"내 투자",profiles:"내 투자",model:"내 투자",companies:"종목 찾기",company:"종목 찾기",analysis:"종목 찾기",entity:"종목 찾기",leaderboard:"종목 찾기",watchlist:"종목 찾기",types:"종목 찾기",news:"시장 정보",thirteenf:"시장 정보"});
const QGV_CHILDREN=Object.freeze(["companies","company","analysis","leaderboard","news","portfolio","actual","entity","profiles","types","thirteenf","watchlist","model"]);
function syncNavigation(route) {
  const parent=QGV_CHILDREN.includes(route)?"qgv":route==="research"?"validation":route;
  document.querySelectorAll("[data-nav-tab]").forEach(a=>{
    if(a.dataset.navTab===parent) a.setAttribute("aria-current","page");
    else a.removeAttribute("aria-current");
  });
}
let listLimit=30;
function paintCompanies(){
 const rows=DeviceWatchlist.filter(identityCompanies,prefs,{query:$('#search').value,group:$('#group-filter').value,onlyInterest:$('#only-interest').checked,sort:$('#company-sort').value});
 $('#company-list').innerHTML=rows.slice(0,listLimit).map(row).join('')||'<li class="empty">'+t("일치하는 기업이 없습니다.")+'</li>';$('#more-companies').hidden=rows.length<=listLimit;
}
function directoryRows(prefix){return DeviceWatchlist.filter(identityCompanies,prefs,{group:$('#'+prefix+'-group').value,onlyInterest:$('#'+prefix+'-interest').checked,sort:$('#'+prefix+'-sort').value});}
let leaderboardView={view:'default',profileId:null};
function paintLeaderboardScreen(rows){let profiles=[];try{profiles=DeviceProfiles.read(localStorage).strategies;}catch(_){profiles=[];}
 LeaderboardScreen.mount($('#leaderboard-screen'),rows,{publicScreens,locale:appSettings.display_locale,profiles,...leaderboardView,onView:patch=>{leaderboardView={...leaderboardView,...patch};if(leaderboardView.view==='device'){const d=$('#private-subset-root')?.closest('details');if(d)d.open=true;}paintLeaderboardScreen(rows);}});}
function paintDirectory(route){const prefix=route==='watchlist'?'watch':'leader',rows=directoryRows(prefix),list=$('#'+(route==='watchlist'?'watchlist':'leader')+'-company-list');list.innerHTML=rows.map(row).join('')||'<li class="empty">'+t("일치하는 기업이 없습니다.")+'</li>';if(route==='leaderboard'){const companyIds=rows.map(r=>r.company_id);paintLeaderboardScreen(rows);$('#leader-m2-panel').innerHTML=m2Panel(undefined,companyIds);SecReported.mount($('#sec-reported-panel'),secReported,{companyIds,locale:appSettings.display_locale});PublicScreens.mount($('#public-qg'),publicScreens,{kind:'qg',companyIds,locale:appSettings.display_locale});}}

function paintNews(id) {
  const c=company(id),scope=$("#news-scope").value,held=D.portfolio.data?.holdings?.map(h=>h.company_id) || [];
  const interests=prefs.interests.map(i=>company(i)?.issuer_id).filter(Boolean),portfolio=held.map(i=>company(i)?.issuer_id).filter(Boolean);
  let rows=(D.news.data || []).filter(r=>(!c || (r.issuer_ids || []).includes(c.issuer_id)) && (scope==="all" || (r.issuer_ids || []).some(i=>(scope==="interest"?interests:portfolio).includes(i))) && (appSettings.source_language==="all" || r.source_language?.split("-")[0]===appSettings.source_language));
  const priority=r=>(r.issuer_ids || []).some(i=>portfolio.includes(i))?0:(r.issuer_ids || []).some(i=>interests.includes(i))?1:2;
  rows=[...rows].sort((a,b)=>priority(a)-priority(b));
  $("#news-list").innerHTML=rows.map(r=>`<li class="card"><h3>${esc(AppLanguage.fallback(r.headline_localized,appSettings.display_locale,r.headline))}</h3>${r.summary || r.summary_localized?`<p>${esc(AppLanguage.fallback(r.summary_localized,appSettings.display_locale,r.summary || ""))}</p>`:""}<p class="meta">${esc(r.available_at)} · ${esc(AppLanguage.status(r.status || t("상태 미제공"),appSettings.display_locale))} · ${esc(r.source_language || t("미제공"))}</p>${(r.issuer_ids || []).map(byIssuer).filter(Boolean).map(c=>`<div class="row"><a href="#company/${encodeURIComponent(c.company_id)}">${esc(c.ticker)}</a>${star(c.company_id)}</div>`).join("")}${evidence(r)}</li>`).join("") || '<li class="empty">'+t("이 범위에 제공된 뉴스가 없습니다.")+"</li>";
}
function showUnavailable() {
  $("#content").innerHTML=heading("DATA UNAVAILABLE",t("데이터를 열 수 없습니다."))+"<p>"+t("연결 상태를 확인한 뒤 다시 시도하세요.")+'</p><button id="retry">'+t("다시 시도")+"</button>";
  $("#retry").onclick=()=>location.reload();
}
function render() {
  // A render error (e.g. after a hashchange) shows the existing DATA UNAVAILABLE fallback instead of escaping
  // as an uncaught exception; the next navigation renders normally again.
  try {renderRoute();}
  catch(e) {console.error(e);showUnavailable();}
}
function renderRoute() {
  window.PrivateHistory?.disposeAll();window.PrivateSubsetView?.disposeAll();
  window.GoogleSheetSetup?.disposeAll();
  notice("");syncShell();
  let [route,id]=location.hash.slice(1).split("/");route=route || "home";
  let anchor=null;
  for(const screen of ["validation","technical"]) if(route.startsWith(screen+"-")) {anchor=route;route=screen;}
  try {id=decodeURIComponent(id || "");} catch(e) {id="";}
  const routes={home,qgv,analysis:()=>analysis(id),profiles,types,model,watchlist,technical,macro,thirteenf,validation,companies,portfolio,actual,leaderboard,news:()=>news(id),research,company:()=>detail(id),settings:settingsUI,entity:()=>entityDetail(id)};
  if(!routes[route]) route="home";
  $("#content").innerHTML=routes[route]();
  if(route==='leaderboard') void PrivateSubsetView.mount($('#private-subset-root'),{locale:appSettings.display_locale,config:window.InvestmentAppConfig,interests:()=>[...prefs.interests]});
  if(route==='actual') attachDeviceActual('#device-actual-root',true);
  if(route==='portfolio') {attachDeviceActual('#device-actual-summary',false);paintPortfolio();}
  if(route==='company' && $('#company-holding')) void CompanyScreen.mountHolding($('#company-holding'),{locale:appSettings.display_locale,ticker:company(id)?.identity_only?company(id).ticker:null,catalogPromise:deviceCatalog()});
  if(route==='analysis') CompanyScreen.wireTabs($('#content'));
  if(route==='model') {attachDeviceActual('#model-actual-summary',false);paintModel();}
  if(route==='home') deviceCatalog().then(c=>{const n=$('#home-target-version');if(n?.isConnected)n.textContent=c.target_root_version||'NOT_AVAILABLE';}).catch(()=>{const n=$('#home-target-version');if(n?.isConnected)n.textContent='NOT_AVAILABLE';});
  if(route==='technical') PrivateHistory.mountTechnical($('#technical-price-chart'),{companyId:id,locale:appSettings.display_locale,config:window.InvestmentAppConfig,getAverage:deviceAverageCost});
  if(route==='company' && $('#private-history-chart')) void PrivateHistory.mount($('#private-history-chart'),{companyId:id,locale:appSettings.display_locale,config:window.InvestmentAppConfig,getAverage:deviceAverageCost});
  if(route==='company'||route==='leaderboard'||route==='analysis') SecReported.mount($('#sec-reported-panel'),secReported,{companyId:route==='leaderboard'?undefined:id,locale:appSettings.display_locale});
  if(route==='profiles') DeviceProfiles.mount($('#device-profile-editor'),{locale:appSettings.display_locale,qgFactors:()=>publicScreens['sec-qg-factors.json']});
  if(route==='types') DeviceProfiles.mount($('#device-type-editor'),{locale:appSettings.display_locale,mode:'types'});
  for(const kind of ['qg','types','filings','macro','thirteenf']) PublicScreens.mount($('#public-'+kind),publicScreens,{kind,companyId:route==='company'?id:undefined,locale:appSettings.display_locale});
  syncNavigation(route);
  const flowParent=QGV_CHILDREN.includes(route)?"qgv":route==="research"?"validation":route;
  if(FLOW_STEPS[flowParent]) $("#content").insertAdjacentHTML("afterbegin",`<p class="flow-step" data-flow-step="${FLOW_STEPS[flowParent][0]}"><span class="flow-number">${FLOW_STEPS[flowParent][0]}</span> ${esc(t(FLOW_STEPS[flowParent][1]))}</p>`);
  if(QGV_CHILDREN.includes(route) || route==="research") {
    const parent=route==="research"?"validation":"qgv",key=parent==="qgv"?"← QGV":"← 검증",sub=QGV_SUBCATEGORY[route];
    $("#content").insertAdjacentHTML("afterbegin",`<p class="parent-row"><a class="parent-link" href="#${parent}">${esc(t(key))}</a>${sub?`<span class="sub-category" data-sub-category>${esc(t(sub))}</span>`:""}</p>`);
  }
  if(Object.values(D).some(s=>s?.state==="DEMO")) $("#content").insertAdjacentHTML("afterbegin",'<div class="banner">'+t("DEMO 포함 · 합성 데이터는 투자 판단용이 아닙니다.")+"</div>");
  if(!storageOK) notice(t("개인 설정 저장을 사용할 수 없습니다. 내보내기를 이용하세요."));
  if(!settingsWritable) notice(t("설정을 읽을 수 없습니다. 저장된 원본은 보존합니다."));
  if(route==="settings") {
    $("#device-backup-export").onclick=()=>void exportDeviceBackup();
    $("#device-backup-import").onchange=async e=>{try{const f=e.target.files[0];if(!f||f.size>1000000)throw Error("BACKUP_TOO_LARGE");await restoreDeviceBackup(JSON.parse(await f.text()));}catch(_){notice("BACKUP_RESTORE_FAILED");}};
    deviceCatalog().then(catalog=>{const host=$("#google-first-setup");if(host?.isConnected)void GoogleSheetSetup.mount(host,{catalog,config:InvestmentAppConfig,locale:appSettings.display_locale});});
    DevicePWA.mount($('#device-pwa-settings'),{locale:appSettings.display_locale});
    OpsStatus.mount($('#ops-status'),{secReported,screens:publicScreens},{locale:appSettings.display_locale});
    attachGoogleSheetSettings();
    PrivateHistory.mountSettings($('#private-history-settings'),{locale:appSettings.display_locale});
    PrivateTrades.mountSettings($('#private-trades-settings'),{locale:appSettings.display_locale});
    PrivateSubsetView.mountSettings($('#private-universe-settings'),{locale:appSettings.display_locale});
    attachDeviceApiSettings();
    $("#display-locale").onchange=e=>updateSettings({display_locale:e.target.value});
    $("#source-language").onchange=e=>updateSettings({source_language:e.target.value});
  }
  if(route==="companies") {
    listLimit=30;paintCompanies();
    $("#search").oninput=$("#only-interest").onchange=$("#group-filter").onchange=$("#company-sort").onchange=()=>{listLimit=30;paintCompanies();};
    $("#more-companies").onclick=()=>{listLimit+=30;paintCompanies();};wireGroups();
  }
  if(route==='watchlist'||route==='leaderboard'){const prefix=route==='watchlist'?'watch':'leader';if(route==='leaderboard'&&id==='interest')$('#leader-interest').checked=true;for(const key of ['interest','group','sort'])$('#'+prefix+'-'+key).onchange=()=>paintDirectory(route);paintDirectory(route);if(route==='watchlist')wireGroups();}
  if(route==="news") {
    for(const name of ["news","network"]) $("#show-"+name).onclick=()=>{
      $("#news-pane").hidden=name!=="news";$("#network-pane").hidden=name!=="network";
      $("#show-news").setAttribute("aria-pressed",name==="news");$("#show-network").setAttribute("aria-pressed",name==="network");
      const f=$("#network-frame");if(name==="network" && f && !f.getAttribute("src")) f.src=f.dataset.src;
    };
    $("#news-scope").onchange=()=>paintNews(id);paintNews(id);
  }
  for(const f of document.querySelectorAll("iframe")) f.onload=()=>f.contentWindow.postMessage({type:"display_locale",locale:appSettings.display_locale},location.origin);
  window.scrollTo(0,0);
  if(anchor) document.getElementById(anchor)?.scrollIntoView({block:"start"});
  if(route==="qgv" && ["investments","companies","market","performance"].includes(id)) {
    const group=$("#qgv-"+id),title=group.querySelector("h2");
    group.scrollIntoView({block:"start"});title.focus({preventScroll:true});
  }
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
      if (!f || f.size > 1000000) throw Error(t("1MB 이하 JSON을 선택하세요."));
      const payload = JSON.parse(await f.text());
      if (payload.schema === DeviceBackup.SCHEMA) { await restoreDeviceBackup(payload); return; }
      const p = validatePrefs(payload);
      prefs.interests = [...new Set([...prefs.interests, ...p.interests])];
      for (const g of p.groups) {
        const old = prefs.groups.find((x) => x.id === g.id);
        if (old) old.members = [...new Set([...old.members, ...g.members])];
        else prefs.groups.push(g);
      }
      save();
      render();
    } catch (err) {
      notice("BACKUP_IMPORT_FAILED");
    }
  };
}
document.addEventListener("click", (e) => {
  const b = e.target.closest("button");
  if (!b) return;
  if (b.dataset.star) {
    const id = b.dataset.star;
    if (!company(id)) return;
    prefs.interests = prefs.interests.includes(id)
      ? prefs.interests.filter((i) => i !== id)
      : [...prefs.interests, id];
    if (!prefs.interests.includes(id))
      prefs.groups.forEach(
        (g) => (g.members = g.members.filter((i) => i !== id)),
      );
    save();
    document.querySelectorAll("[data-star]").forEach((x) => {
      x.textContent = prefs.interests.includes(x.dataset.star) ? "★" : "☆";
      x.setAttribute("aria-pressed", prefs.interests.includes(x.dataset.star));
    });
    const route=location.hash.slice(1).split('/')[0];if(route==='companies'){paintCompanies();}if(route==='leaderboard'||route==='watchlist')paintDirectory(route);const groups=$('#groups');if(groups){const holder=document.createElement('div');holder.innerHTML=groupsUI();groups.innerHTML=holder.querySelector('#groups').innerHTML;}const ownGroups=$('#company-groups');if(ownGroups)ownGroups.innerHTML=companyGroups(id);
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
  const id = byIssuer(e.data.id)?.company_id;
  if (e.data.type === "interest") {
    if (!company(id)) return;
    prefs.interests = prefs.interests.includes(id)
      ? prefs.interests.filter((i) => i !== id)
      : [...prefs.interests, id];
    if (!prefs.interests.includes(id))
      prefs.groups.forEach(
        (g) => (g.members = g.members.filter((i) => i !== id)),
      );
    save();
  }
  frame.contentWindow.postMessage(
    {
      type: "interests",
      ids: prefs.interests.map((i) => company(i)?.issuer_id).filter(Boolean),
    },
    location.origin,
  );
});
window.addEventListener("hashchange", () => D && render());
$("#global-search").oninput=paintGlobalSearch;
$("#global-search").onkeydown=e=>{
  const links=[...document.querySelectorAll("#global-results a")];
  if(e.key==="ArrowDown" && links.length) {e.preventDefault();links[0].focus();}
  if(e.key==="Escape") {$("#global-search").value="";paintGlobalSearch();}
};
$("#global-results").onkeydown=e=>{
  const links=[...document.querySelectorAll("#global-results a")],i=links.indexOf(document.activeElement);
  if(e.key==="ArrowDown" || e.key==="ArrowUp") {e.preventDefault();(links[i+(e.key==="ArrowDown"?1:-1)] || $("#global-search")).focus();}
  if(e.key==="Escape") {$("#global-search").value="";paintGlobalSearch();$("#global-search").focus();}
};
document.addEventListener("click",e=>{
  if(e.target.closest("#global-results a")) {$("#global-search").value="";paintGlobalSearch();}
});
try {const saved=AppLanguage.read(localStorage);appSettings=saved.value;settingsWritable=saved.writable;}
catch(e) {settingsWritable=false;}
syncShell();
Promise.all([...(["data.json","entities.json","sec-m2-candidates.json"].map(path=>fetch(path,{cache:"no-store"}).then(r=>{
  if(!r.ok) throw Error("HTTP "+r.status);return r.json();
}).catch(error=>{if(path==="sec-m2-candidates.json")return null;throw error;}))),SecReported.load(window),PublicScreens.load(window),deviceCatalog().catch(()=>null)]).then(([data,catalog,candidates,reported,screens,identities])=>{
  try{if(identities){DeviceMarket.emptyMarket(identities);identityCompanies=DeviceWatchlist.identities(identities);}}catch(_){identityCompanies=[];}
  publicScreens=screens;
  secReported=reported;
  m2Candidates=guardM2Candidates(candidates);
  // GSQ-010: legacy public producer payloads are withheld, including membership/order.
  // The private device catalog and device/session data have their own boundary.
  const publicSections=["universe","qgv","technical","macro","portfolio","leaderboard","news","relationships","changes"];
  const safeData={schema_version:1,companies:[]};
  for(const name of publicSections) safeData[name]={state:"NOT_AVAILABLE",as_of:null,source:null,reason:"공개 가격 경계에 따라 제공되지 않습니다. (GSQ-010)",data:null};
  D=guardSections(safeData);searchIndex=EntitySearch.createIndex(catalog.entities.filter(e=>e.entity_type!=="COMPANY"));load();render();paintGlobalSearch();
}).catch(showUnavailable);

async function exportDeviceBackup(){
  try{const catalog=await deviceCatalog();DeviceBackup.download(window,await DeviceBackup.read(window,catalog));}
  catch(_){notice('BACKUP_EXPORT_FAILED');}
}
async function restoreDeviceBackup(payload){
  const catalog=await deviceCatalog();DeviceBackup.parse(payload,catalog,DeviceMarket,AppLanguage);
  if(!confirm(appSettings.display_locale==='en-US'?'Replace device interests, groups, portfolio, profiles and language settings?':'기기 관심 기업·그룹·포트폴리오·프로필·언어 설정을 백업으로 바꿀까요?'))return;
  await DeviceBackup.restore(window,catalog,payload);load();const read=AppLanguage.read(localStorage);appSettings=read.value;settingsWritable=read.writable;render();
}
document.addEventListener('device-backup-restored',()=>{load();appSettings=AppLanguage.read(localStorage).value;render();});

async function deviceAverageCost(symbol){
  const catalog=await deviceCatalog(),snapshot=await DeviceActual.readHoldings(window,catalog);
  if(!snapshot)return null;
  const ticker=symbol.replace(/\.(KS|T)$/,''),instrument=catalog.instruments.find(i=>i.ticker===ticker);
  if(!instrument)return null;
  const row=snapshot.themes.flatMap(t=>t.holdings).find(r=>DeviceMarket.canonical(r.security_reference)===DeviceMarket.canonical(instrument.security_reference));
  return row&&Number(row.quantity)>0&&row.currency===instrument.currency&&Number(row.average_cost)>0?Number(row.average_cost):null;
}

window.addEventListener('device-sheet-source-changed',()=>{if(location.hash==='#settings'){attachGoogleSheetSettings();PrivateTrades.mountSettings($('#private-trades-settings'),{locale:appSettings.display_locale});}});
