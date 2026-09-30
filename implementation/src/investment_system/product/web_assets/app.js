"use strict";
let D,
  prefs = { version: 1, interests: [], groups: [] },
  storageOK = true,
  corruptStorage = false;
const KEY = "investment.web.v1.personal";
let appSettings=AppLanguage.settings(), settingsWritable=true, searchIndex;
const t=key=>AppLanguage.text(key,appSettings.display_locale);
const term=key=>AppLanguage.term(key,appSettings.display_locale);
const label=e=>AppLanguage.fallback(e?.localized_names,appSettings.display_locale,e?.canonical_label || "");
function updateSettings(patch) {
  appSettings=AppLanguage.settings({...appSettings,...patch});
  if(settingsWritable) {try {AppLanguage.write(localStorage,appSettings);} catch(e) {settingsWritable=false;}}
  render(); paintGlobalSearch();
  if(!settingsWritable) notice(t("설정을 저장할 수 없습니다."));
}
function settingsUI() {
  return heading("SETTINGS",t("설정"))+`<section class="card">
  <label for="display-locale">${t("표시 언어")}</label><select id="display-locale"><option value="ko-KR" ${appSettings.display_locale==="ko-KR"?"selected":""}>한국어</option><option value="en-US" ${appSettings.display_locale==="en-US"?"selected":""}>English</option></select>
  <p>${t("표시 언어는 계산 결과에 영향을 주지 않습니다.")}</p>
  <label for="source-language">${t("뉴스 원문 언어")}</label><select id="source-language">${[["all",t("전체 언어")],["ko",t("한국어 원문")],["en",t("영어 원문")]].map(([v,k])=>`<option value="${v}" ${appSettings.source_language===v?"selected":""}>${t(k)}</option>`).join("")}</select>
  <p>${t("원문 언어는 뉴스 필터만 변경합니다.")}</p></section>
  <section class="card"><h2>${t("금융 용어")}</h2>${["free_cash_flow","drawdown","operating_margin"].map(k=>`<p>${term(k)}</p>`).join("")}</section>`;
}
function entityRoute(e) {return e.entity_type==="COMPANY"?"#company/"+encodeURIComponent(e.canonical_id):"#entity/"+encodeURIComponent(e.entity_type+":"+e.canonical_id);}
function entityRow(hit) {
  const e=hit.entity,c=e.entity_type==="COMPANY"?company(e.canonical_id):null;
  const held=c && D.portfolio.data?.holdings?.some(h=>h.company_id===c.company_id);
  const types={COMPANY:t("기업"),INDUSTRY:t("산업"),INVESTOR:t("투자자"),MACRO:t("거시지표")};
  return `<li class="item" data-entity-id="${esc(hit.canonical_entity_id)}"><a href="${entityRoute(e)}"><b>${esc(label(e))}</b> <span class="badge">${esc(t(types[e.entity_type] || e.entity_type))}</span><div class="meta">${esc(e.ticker || "")} · ${esc(e.canonical_label)}${e.localized_names?.["ko-KR"]?" · "+esc(e.localized_names["ko-KR"]):""}${e.industry?" · "+esc(e.industry):""}</div>${c?`<div class="meta">${held?t("Snapshot 보유")+" · ":""}${D.qgv.data?.[c.company_id]?t("QGV 제공"):t("분석 미연결")} · ${esc(D.qgv.as_of || D.universe.as_of || t("시점 미제공"))} · ${esc(e.data_state || D.universe.state)}</div>`:""}</a></li>`;
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
  return D.companies.find((c) => c.company_id === id);
}
function byIssuer(id) {
  return D.companies.find((c) => c.issuer_id === id);
}
function star(id) {
  return `<button class="star" data-star="${esc(id)}" aria-label="${esc(company(id)?.ticker || id)} ${t("관심기업")}" aria-pressed="${prefs.interests.includes(id)}">${prefs.interests.includes(id)?"★":"☆"}</button>`;
}
function state(s) {
  const stale=s.state==="LIVE" && Date.parse(s.expires_at)<=Date.now();
  return `<div class="state"><span class="badge ${esc(s.state)}">${esc(s.state)}${stale?" · STALE":""}</span> <span class="meta">${esc(s.as_of || t("시점 미제공"))}</span></div><div class="meta" data-source-original>${esc(s.source || (s.data===null?"":t("출처 미제공")))}</div>`;
}
function evidence(v) {
  return `<details><summary>${t("Evidence(근거) · 원본 보기")}</summary><pre data-source-original>${esc(JSON.stringify(v,null,2))}</pre></details>`;
}
function block(name,title,body) {
  const s=D[name];
  return `<section class="card"><h2>${title}</h2>${state(s)}${s.data===null?'<p class="empty">'+esc(AppLanguage.fallback(s.reason_localized,appSettings.display_locale,t(s.reason || t("미제공"))))+"</p>":body}${s.data!==null?evidence(s):""}</section>`;
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
  `<section class="card hero"><div class="row"><h2>${t("Portfolio(포트폴리오)")}</h2><a href="#portfolio">${t("자세히 →")}</a></div><div class="metric">${D.portfolio.data?held.length+" holdings":t("연결 대기")}</div><p class="muted">${D.portfolio.data?esc(D.portfolio.data.role || t("제공된 Snapshot")):t("실제 보유·평가금액·수익률을 연결하면 여기서 확인합니다.")}</p>${state(D.portfolio)}</section>
  <div class="grid home-grid">${block("changes",t("오늘 / 최근 주요 변화"),`<p>${esc(AppLanguage.fallback(D.changes.data?.summary_localized,appSettings.display_locale,D.changes.data?.summary || ""))}</p>`)}${block("macro",t("Macro(거시환경)"),`<p>${esc(AppLanguage.status(D.macro.data?.state || "",appSettings.display_locale))} · ${esc(D.macro.data?.regime || "")}</p>`)}</div>
  <section class="card"><h2>${t("Attention(확인 필요)")}</h2><p class="small">${D.universe.state==="FROZEN_SNAPSHOT"?t("기업 목록은")+" "+esc(D.universe.as_of)+" "+t("과거 스냅샷입니다. 최신 시세·분석이 아닙니다."):t("출처와 데이터 시점을 확인하세요.")}</p><div class="chips"><a href="#companies">${t("관심기업")} ${prefs.interests.length} →</a><a href="#leaderboard">Leaderboard →</a></div></section>
  <details><summary>${t("분석 · 뉴스 · 관계 변화 더보기")}</summary><div class="grid">${block("qgv",t("QGV 변화"),"<p>"+t("변화량은 upstream changes가 제공할 때만 표시합니다.")+"</p>")}${block("technical",t("Technical 변화"),"<p>"+t("최근 신호는 기업 상세에서 확인하세요.")+"</p>")}${block("news",t("관심기업 뉴스"),'<a href="#news">'+t("뉴스 열기 →")+"</a>")}${block("relationships",t("Relationship changes(관계 변화)"),'<a href="#news">'+t("관계망 열기 →")+"</a>")}</div></details>`;
}
function companies() {
  return heading("COMPANIES",t("기업 탐색"))+`<input type="search" id="search" aria-label="${t("기업 검색")}" placeholder="${t("티커 또는 기업명 검색")}"><div class="chips"><label><input type="checkbox" id="only-interest"> ${t("관심기업만")}</label><select id="group-filter" aria-label="${t("그룹 필터")}"><option value="">${t("모든 그룹")}</option>${prefs.groups.map(g=>`<option value="${esc(g.id)}">${esc(g.name)}</option>`).join("")}</select></div><p class="meta">${esc(D.universe.as_of)} · FROZEN_SNAPSHOT / DEMO</p><ul class="list" id="company-list"></ul><button id="more-companies">${t("더보기")}</button><details><summary>${t("관심기업 · Groups(그룹) 관리")}</summary>${groupsUI()}</details>`;
}
function groupsUI() {
  return `<p class="muted">${t("이 기기의 브라우저에 저장됩니다. 즐겨찾기와 관심기업은 같은 목록입니다.")}</p><form id="new-group"><label for="group-name">${t("새 그룹 이름")}</label><div class="row"><input id="group-name" required maxlength="60" placeholder="${t("예: 반도체")}"><button>${t("그룹 만들기")}</button></div></form><div id="groups">${prefs.groups.map(g=>`<div class="group"><b>${esc(g.name)}</b> <span class="muted">${g.members.length} ${t("개")}</span><div class="row"><input aria-label="${t("그룹 이름")} ${esc(g.name)}" data-rename-input="${esc(g.id)}" value="${esc(g.name)}" maxlength="60"><button data-rename="${esc(g.id)}">${t("이름 변경")}</button><button data-delete="${esc(g.id)}">${t("그룹 삭제")}</button></div>${prefs.interests.map(id=>`<label><input type="checkbox" data-group="${esc(g.id)}" data-member="${esc(id)}" ${g.members.includes(id)?"checked":""}> ${esc(company(id)?.ticker || id)}</label>`).join("")}</div>`).join("")}</div><div class="toolbar"><button id="export">${t("내보내기")}</button><label>${t("설정 병합 가져오기")} <input type="file" id="import" accept="application/json"></label></div>`;
}
function detail(id) {
  const c=company(id);
  if(!c) return heading("COMPANIES",t("기업을 찾을 수 없습니다."))+'<a href="#companies">'+t("기업 목록 →")+"</a>";
  const h=D.portfolio.data?.holdings?.find(r=>r.company_id===id),e=searchIndex.resolve("COMPANY",id);
  return `<a class="small" href="#companies">${t("← 기업 목록")}</a><div class="row">${heading("COMPANY DETAIL",esc(c.ticker),esc(label(e) || c.name))}${star(id)}</div><div class="grid">${summaryFor("qgv",id)}${summaryFor("technical",id)}</div>`+
  block("macro",t("Macro exposure / context(거시 노출)"),`<p>${esc(D.macro.data?.regime || "")}</p><p>${t("기업 노출:")} ${esc(D.macro.data?.exposures?.[id] || t("미제공"))}</p>`)+
  `<section class="card"><h2>${t("Portfolio status(보유 상태)")}</h2>${state(D.portfolio)}<p>${h?t("Snapshot에 포함 · 비중")+" "+pct(h.actual_weight ?? h.target_weight):D.portfolio.data?t("제공된 Snapshot에 없음"):t("실제 보유 상태 미제공")}</p>${h?evidence(h):""}</section><section class="card"><h2>News / Relationships</h2>${state(D.news)}<a href="#news/${encodeURIComponent(id)}">${t("이 기업의 뉴스·관계망 확인 →")}</a></section>${evidence(c)}`;
}
function portfolio() {
  const p=D.portfolio.data;
  return heading("PORTFOLIO",t("내 포트폴리오"))+block("portfolio",t("보유 현황"),`<p>${esc(p?.role || "")}</p><dl><dt>${t("수익률")}</dt><dd>${pct(p?.return)}</dd><dt>${t("평가금액")}</dt><dd>${fmt(p?.market_value)} ${esc(p?.currency || "")}</dd><dt>${t("Exposure(노출)")}</dt><dd>${esc(p?.exposure?JSON.stringify(p.exposure):t("미제공"))}</dd></dl><ul class="list">${(p?.holdings || []).map(h=>`<li class="item"><a href="#company/${encodeURIComponent(h.company_id)}"><b>${esc(h.ticker)}</b><div class="muted">${h.actual_weight==null?t("모델 비중"):t("실제 비중")} ${pct(h.actual_weight ?? h.target_weight)} · ${t("수익률")} ${pct(h.return)}</div></a>${star(h.company_id)}</li>`).join("")}</ul>`)+
  `<div class="grid">${block("qgv","QGV context",'<a href="#companies">'+t("기업별 분석 →")+"</a>")}${block("technical","Technical context",'<a href="#companies">'+t("기업별 신호 →")+"</a>")}${block("macro","Macro context",`<p>${esc(D.macro.data?.regime || "")}</p>`)}</div><a href="#news">${t("중요 뉴스·관계 변화 →")}</a>`;
}
function leaderboard() {
  const l=D.leaderboard.data;
  return heading("LEADERBOARD",t("기업 순위"),t("QGV 순위와 시가총액 순위는 각각 upstream 값을 표시합니다."))+
  block("leaderboard",t("제공된 Leaderboard"),`<ul class="list">${(l?.rows || []).map(r=>`<li class="card"><a href="#company/${encodeURIComponent(r.company_id)}"><b>#${esc(r.rank)} ${esc(r.ticker)}</b></a>${star(r.company_id)}<dl>${[[t("시총 순위"),r.market_cap_rank],["QGV",r.total_score],[t("Daily move(전일 등락)"),r.daily_move],[t("Consensus(컨센서스)"),r.consensus],[t("Scenario(시나리오)"),r.scenario],[t("Reevaluation(재평가 기준)"),r.reevaluation_trigger]].map(([k,v])=>`<dt>${t(k)}</dt><dd>${fmt(v)}</dd>`).join("")}</dl>${evidence(r)}</li>`).join("")}</ul>`);
}
function news(id) {
  const c=company(id);
  return heading("NEWS / NETWORK",t("뉴스와 연결"),c?esc(c.ticker)+" "+t("기업 문맥"):t("Portfolio · 관심기업 · 기타 중요뉴스"))+
  `<div class="chips toolbar" role="group" aria-label="${t("콘텐츠 전환")}"><button id="show-news" aria-pressed="true">${t("뉴스")}</button><button id="show-network" aria-pressed="false">${t("관계망")}</button>${c?star(id):""}</div><section id="news-pane"><select id="news-scope" aria-label="${t("뉴스 범위")}"><option value="all">${t("전체 중요뉴스")}</option><option value="interest">${t("관심기업")}</option><option value="portfolio">Portfolio</option></select>${state(D.news)}<ul id="news-list" class="list"></ul></section><section id="network-pane" hidden><p class="muted">${t("Fact = 확인된 관계 · Impact = 잠재 영향 경로")}</p>${state(D.relationships)}${D.relationships.data?'<iframe title="News Network" data-src="network.html" id="network-frame"></iframe>':'<p class="empty">'+t("Track D 운영 관계망 미연결")+"</p>"}</section>`;
}
function research() {
  return heading("RESEARCH",t("질문에서 근거로"),"Prompt → Context / Variables → Preview → Copy")+'<p class="badge">FROZEN_SNAPSHOT · PLV1_CONTENT_V1.0</p><iframe title="Prompt Library" src="research.html" id="research-frame"></iframe>';
}
let listLimit=30;
function paintCompanies() {
  const q=$("#search").value,g=prefs.groups.find(g=>g.id===$("#group-filter").value);
  const pool=q.trim()?searchIndex.search(q,{limit:1000,types:["COMPANY"]}).map(h=>company(h.entity.canonical_id)):D.companies;
  const rows=pool.filter(c=>(!$("#only-interest").checked || prefs.interests.includes(c.company_id)) && (!g || g.members.includes(c.company_id)));
  $("#company-list").innerHTML=rows.slice(0,listLimit).map(row).join("") || '<li class="empty">'+t("일치하는 기업이 없습니다.")+"</li>";
  $("#more-companies").hidden=rows.length<=listLimit;
}
function paintNews(id) {
  const c=company(id),scope=$("#news-scope").value,held=D.portfolio.data?.holdings?.map(h=>h.company_id) || [];
  const interests=prefs.interests.map(i=>company(i)?.issuer_id).filter(Boolean),portfolio=held.map(i=>company(i)?.issuer_id).filter(Boolean);
  let rows=(D.news.data || []).filter(r=>(!c || (r.issuer_ids || []).includes(c.issuer_id)) && (scope==="all" || (r.issuer_ids || []).some(i=>(scope==="interest"?interests:portfolio).includes(i))) && (appSettings.source_language==="all" || r.source_language?.split("-")[0]===appSettings.source_language));
  const priority=r=>(r.issuer_ids || []).some(i=>portfolio.includes(i))?0:(r.issuer_ids || []).some(i=>interests.includes(i))?1:2;
  rows=[...rows].sort((a,b)=>priority(a)-priority(b));
  $("#news-list").innerHTML=rows.map(r=>`<li class="card"><h3>${esc(AppLanguage.fallback(r.headline_localized,appSettings.display_locale,r.headline))}</h3>${r.summary || r.summary_localized?`<p>${esc(AppLanguage.fallback(r.summary_localized,appSettings.display_locale,r.summary || ""))}</p>`:""}<p class="meta">${esc(r.available_at)} · ${esc(AppLanguage.status(r.status || t("상태 미제공"),appSettings.display_locale))} · ${esc(r.source_language || t("미제공"))}</p>${(r.issuer_ids || []).map(byIssuer).filter(Boolean).map(c=>`<div class="row"><a href="#company/${encodeURIComponent(c.company_id)}">${esc(c.ticker)}</a>${star(c.company_id)}</div>`).join("")}${evidence(r)}</li>`).join("") || '<li class="empty">'+t("이 범위에 제공된 뉴스가 없습니다.")+"</li>";
}
function render() {
  notice("");syncShell();
  let [route,id]=location.hash.slice(1).split("/");route=route || "home";
  try {id=decodeURIComponent(id || "");} catch(e) {id="";}
  const routes={home,companies,portfolio,leaderboard,news:()=>news(id),research,company:()=>detail(id),settings:settingsUI,entity:()=>entityDetail(id)};
  if(!routes[route]) route="home";
  $("#content").innerHTML=routes[route]();
  document.querySelectorAll("nav a").forEach(a=>a.setAttribute("aria-current",a.hash==="#"+(route==="company"?"companies":route)?"page":"false"));
  if(Object.values(D).some(s=>s?.state==="DEMO")) $("#content").insertAdjacentHTML("afterbegin",'<div class="banner">'+t("DEMO 포함 · 합성 데이터는 투자 판단용이 아닙니다.")+"</div>");
  if(!storageOK) notice(t("개인 설정 저장을 사용할 수 없습니다. 내보내기를 이용하세요."));
  if(!settingsWritable) notice(t("설정을 읽을 수 없습니다. 저장된 원본은 보존합니다."));
  if(route==="settings") {
    $("#display-locale").onchange=e=>updateSettings({display_locale:e.target.value});
    $("#source-language").onchange=e=>updateSettings({source_language:e.target.value});
  }
  if(route==="companies") {
    listLimit=30;paintCompanies();
    $("#search").oninput=$("#only-interest").onchange=$("#group-filter").onchange=()=>{listLimit=30;paintCompanies();};
    $("#more-companies").onclick=()=>{listLimit+=30;paintCompanies();};wireGroups();
  }
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
  $("#export").onclick = () => {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(
      new Blob([JSON.stringify(prefs, null, 2)], { type: "application/json" }),
    );
    a.download = "investment-personal.json";
    a.click();
    URL.revokeObjectURL(a.href);
  };
  $("#import").onchange = async (e) => {
    try {
      const f = e.target.files[0];
      if (!f || f.size > 1000000) throw Error(t("1MB 이하 JSON을 선택하세요."));
      const p = validatePrefs(JSON.parse(await f.text()));
      prefs.interests = [...new Set([...prefs.interests, ...p.interests])];
      for (const g of p.groups) {
        const old = prefs.groups.find((x) => x.id === g.id);
        if (old) old.members = [...new Set([...old.members, ...g.members])];
        else prefs.groups.push(g);
      }
      save();
      render();
    } catch (err) {
      notice("가져오기 실패: " + err.message);
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
window.addEventListener("message", (e) => {
  const frame = $("#network-frame");
  if (
    e.origin !== location.origin ||
    e.source !== frame?.contentWindow ||
    !["interest", "ready"].includes(e.data?.type)
  )
    return;
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
Promise.all(["data.json","entities.json"].map(path=>fetch(path,{cache:"no-store"}).then(r=>{
  if(!r.ok) throw Error("HTTP "+r.status);return r.json();
}))).then(([data,catalog])=>{
  D=data;searchIndex=EntitySearch.createIndex(catalog.entities);load();render();paintGlobalSearch();
}).catch(e=>{
  $("#content").innerHTML=heading("DATA UNAVAILABLE",t("데이터를 열 수 없습니다."))+"<p>"+t("연결 상태를 확인한 뒤 다시 시도하세요.")+'</p><button id="retry">'+t("다시 시도")+"</button>";
  $("#retry").onclick=()=>location.reload();
});
