"use strict";
(() => {
  const $ = (s, root = document) => root.querySelector(s);
  const $$ = (s, root = document) => [...root.querySelectorAll(s)];
  const escape = (v) =>
    String(v ?? "").replace(
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
  const num = (n, digits = 1) =>
    Number.isFinite(n)
      ? n.toLocaleString("ko-KR", {
          maximumFractionDigits: digits,
          minimumFractionDigits: digits,
        })
      : "미제공";
  const pct = (n, digits = 1) =>
    Number.isFinite(n)
      ? `${n > 0 ? "+" : ""}${num(n * 100, digits)}%`
      : "미제공";
  const money = (n) =>
    n >= 100000000
      ? `${num(n / 100000000, 2)}<small>억원</small>`
      : `${num(n / 10000, 0)}<small>만원</small>`;
  const fullMoney = (n) =>
    Number.isFinite(n)
      ? Math.round(n).toLocaleString("ko-KR") + "원"
      : "미제공";
  const colors = ["#3e6249", "#809a64", "#adc18b", "#d8ddbb", "#e9ebdf"];
  const paths = {
    home: "M3 10 12 3l9 7M5 9v12h5v-7h4v7h5V9",
    portfolio: "M3 7h18v14H3zM8 7V3h8v4M3 12h18M10 12v3h4v-3",
    leaderboard: "M5 20V10h4v10m3 0V4h4v16m3 0v-7h3v7",
    simulation: "M4 4h16v16H4zM7 15l4-5 3 3 4-6",
    technical: "M3 18l5-7 4 3 8-10M5 3v4m6-2v4m6 7v5",
    macro:
      "M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0ZM3 12h18M12 3c5 5 5 13 0 18-5-5-5-13 0-18",
    intelligence: "M4 4h16v16H4zM7 8h10M7 12h10M7 16h5",
    validation: "m12 3 8 4v6c0 4-8 8-8 8s-8-4-8-8V7zM8 12l3 3 5-6",
    settings:
      "M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8M12 2v3m0 14v3M2 12h3m14 0h3M5 5l2 2m10 10 2 2M5 19l2-2M17 7l2-2",
    arrow: "M4 18 18 4M5 4h13v13",
    chevron: "m9 5 7 7-7 7",
    download: "M12 3v12m-5-5 5 5 5-5M4 17v4h16v-4",
    wallet: "M3 5h16v4H3zM3 9v11h18V9zM16 13h5v4h-5z",
    chart: "M3 20h18M5 16l5-5 4 3 6-9",
    shield: "m12 3 8 4v6c0 4-8 8-8 8s-8-4-8-8V7z",
    cash: "M3 6h18v12H3zM8 12h.01M16 12h.01M12 9v6",
  };
  const icon = (name) =>
    `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.45" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${paths[name] || paths.chart}"/></svg>`;
  const nav = [
    ["home", "오늘", "home"],
    ["portfolio", "포트폴리오", "portfolio"],
    ["leaderboard", "기업 탐색", "leaderboard"],
    ["simulation", "시뮬레이션", "simulation"],
    ["technical", "기술적 분석", "technical"],
    ["macro", "매크로", "macro"],
    ["intelligence", "뉴스·관계", "intelligence"],
    ["validation", "검증·기록", "validation"],
  ];
  const names = Object.fromEntries(nav.map(([id, label]) => [id, label]));
  names.settings = "설정";
  const presets = {
    balanced: "균형",
    quality: "우량 중심",
    growth: "성장 친화",
    value: "가치 중심",
  };
  let saved = [];
  try {
    const input = JSON.parse(
      localStorage.getItem("investment.studio.v1.watchlist") || "[]",
    );
    saved = Array.isArray(input)
      ? input.filter((x) => typeof x === "string")
      : [];
  } catch {}
  const state = {
    snapshot: null,
    result: null,
    preset: "balanced",
    route: "home",
    company: "nvda",
    favorites: new Set(saved),
    filter: "",
    sector: "all",
    onlySaved: false,
    sort: "score",
    benchmark: true,
    sim: {
      capital: 100000000,
      monthly: 500000,
      months: 36,
      cash: 10,
      scenario: "base",
    },
  };
  let simRequest = 0,
    snapshotRequest = 0,
    toastTimer;
  const scoreBadge = (score) =>
    `<span class="score${score === null ? " unavailable" : ""}">${score === null ? "미제공" : num(score)}</span>`;
  const status = (label, type = "") =>
    `<span class="status-chip ${type}">${escape(label)}</span>`;
  const card = (label, value, foot, symbol, featured = false) =>
    `<div class="metric-card${featured ? " featured" : ""}"><div class="metric-label">${label}${icon(symbol)}</div><div class="metric-value" ${label === "가상 최종 자산" ? 'data-result="ending"' : ""}>${value}</div><div class="metric-foot">${foot}</div></div>`;
  const heading = (label, eyebrow, subtitle, aside = "") =>
    `<div class="page-heading"><div><div class="eyebrow">${eyebrow}</div><h1>${label}</h1><p class="page-subtitle">${subtitle}</p></div>${aside || '<div class="heading-aside">2026년 10월 14일<b>합성 데이터 스냅샷</b></div>'}</div>`;
  const companyIcon = (r) =>
    `<span class="company-icon ${r.company_id}">${escape(r.ticker.slice(0, 2))}</span>`;
  const companyButton = (r) =>
    `<button class="company-button" data-company="${r.company_id}" aria-label="${escape(r.name)} 상세 보기">${companyIcon(r)}<span class="company-copy"><strong>${escape(r.name)}</strong><small>${escape(r.ticker)} · ${escape(r.sector)}</small></span></button>`;
  const star = (r) =>
    `<button class="favorites-button${state.favorites.has(r.company_id) ? " saved" : ""}" data-star="${r.company_id}" aria-label="${escape(r.name)} 관심 ${state.favorites.has(r.company_id) ? "해제" : "추가"}" aria-pressed="${state.favorites.has(r.company_id)}">${state.favorites.has(r.company_id) ? "★" : "☆"}</button>`;
  const technicalLabels = {
    TREND_UP: "상승 흐름",
    TREND_DOWN: "하락 흐름",
    RANGE: "횡보 구간",
    HIGH_VOL: "고변동성",
    UNKNOWN: "판단 유보",
  };
  const zoneLabels = {
    ENTRY: "진입 구간 참고",
    ADD: "추가 구간 참고",
    WAIT: "관찰",
    RISK_REDUCTION: "위험 점검",
  };
  function toast(text) {
    $("#toast").textContent = text;
    $("#toast").classList.add("visible");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(
      () => $("#toast").classList.remove("visible"),
      2500,
    );
  }
  async function api(url, options) {
    if (window.StudioPreview) return window.StudioPreview.request(url, options);
    const r = await fetch(url, options);
    if (!r.ok) {
      let info;
      try {
        info = await r.json();
      } catch {}
      throw Error(
        info?.error || "데이터를 불러오지 못했습니다. 다시 시도해 주세요.",
      );
    }
    return r.json();
  }
  function setNav() {
    $("#desktop-nav").innerHTML = nav
      .map(
        ([id, label, symbol], i) =>
          `${i === 1 ? '<div class="nav-label">INVEST</div>' : i === 4 ? '<div class="nav-label">RESEARCH</div>' : ""}<a href="#${id}" class="nav-link${id === state.route ? " active" : ""}" ${id === state.route ? 'aria-current="page"' : ""}>${icon(symbol)}<span>${label}</span>${id === "leaderboard" ? '<span class="nav-count">19</span>' : ""}</a>`,
      )
      .join("");
    $("#mobile-nav").innerHTML = [
      "home",
      "leaderboard",
      "simulation",
      "macro",
      "settings",
    ]
      .map(
        (id) =>
          `<a href="#${id}" class="${state.route === id ? "active" : ""}" ${state.route === id ? 'aria-current="page"' : ""}>${icon(id)}<span>${id === "leaderboard" ? "기업" : names[id]}</span></a>`,
      )
      .join("");
    $("#mobile-all-menu").innerHTML = [...nav, ["settings", "설정", "settings"]]
      .map(
        ([id, label, symbol]) =>
          `<a href="#${id}" class="nav-link${id === state.route ? " active" : ""}">${icon(symbol)}${label}</a>`,
      )
      .join("");
    $("#breadcrumb-current").textContent = names[state.route] || "오늘";
  }
  function weightedScore() {
    const rows = state.snapshot.companies.filter((r) => r.qgv.total !== null);
    return (
      rows.reduce((s, r) => s + r.qgv.total * r.target_weight, 0) /
      rows.reduce((s, r) => s + r.target_weight, 0)
    );
  }
  function spark(values) {
    const lo = Math.min(...values),
      hi = Math.max(...values),
      points = values
        .map(
          (v, i) =>
            `${(i / (values.length - 1)) * 70},${23 - ((v - lo) / (hi - lo || 1)) * 20}`,
        )
        .join(" ");
    return `<span class="spark"><svg viewBox="0 0 72 26" aria-hidden="true"><polyline points="${points}" stroke="#789763" stroke-width="1.4" fill="none"/></svg></span>`;
  }
  function lineChart(series, { price = false } = {}) {
    const w = window.innerWidth <= 760 ? 350 : 700,
      h = 245,
      left = 46,
      right = 17,
      top = 17,
      bottom = 31,
      iw = w - left - right,
      ih = h - top - bottom;
    const values = series.flatMap((p) =>
      price
        ? [p.strategy]
        : [p.strategy, ...(state.benchmark ? [p.benchmark] : [])],
    );
    const vmin = Math.min(...values),
      vmax = Math.max(...values),
      pad = (vmax - vmin || vmax * 0.1) * 0.18,
      lo = Math.max(0, vmin - pad),
      hi = vmax + pad;
    const x = (i) => left + (i / Math.max(1, series.length - 1)) * iw,
      y = (v) => top + ((hi - v) / (hi - lo || 1)) * ih;
    const line = (k) =>
      series
        .map(
          (p, i) => `${i ? "L" : "M"}${x(i).toFixed(2)},${y(p[k]).toFixed(2)}`,
        )
        .join(" ");
    const last = series.at(-1);
    const ticks = Array.from({ length: 5 }, (_, i) => {
      const v = lo + ((hi - lo) * i) / 4,
        yy = y(v);
      return `<line x1="${left}" y1="${yy}" x2="${w - right}" y2="${yy}" stroke="#edf0e6" stroke-dasharray="3 5"/><text x="${left - 10}" y="${yy + 3}" text-anchor="end">${price ? num(v, 0) : num(v / 10000, 0)}</text>`;
    }).join("");
    const labels = Array.from({ length: 5 }, (_, i) => {
      const n = Math.round(((series.length - 1) * i) / 4);
      return `<text x="${x(n)}" y="${h - 7}" text-anchor="middle">${price ? `${n + 1}일` : `${n}개월`}</text>`;
    }).join("");
    return `<svg viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" role="img" aria-label="${price ? "가상 가격 추이" : "월말 납입을 포함한 가상 자산 추이, 단위 만원"}"><defs><linearGradient id="wealth-fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#b9cc98" stop-opacity=".42"/><stop offset="100%" stop-color="#eaf1df" stop-opacity=".08"/></linearGradient></defs>${ticks}<path d="${line("strategy")} L${x(series.length - 1)},${h - bottom} L${left},${h - bottom} Z" fill="url(#wealth-fill)"/>${!price && state.benchmark ? `<path d="${line("benchmark")}" stroke="#c4a06a" fill="none" stroke-width="1.8" stroke-dasharray="5 5"/>` : ""}<path d="${line("strategy")}" stroke="#4a6f3b" stroke-width="2.5" fill="none"/><circle cx="${x(series.length - 1)}" cy="${y(last.strategy)}" r="3.5" fill="#4a6f3b" stroke="#fff" stroke-width="2"/>${labels}</svg>`;
  }
  function wealthPanel(result, controls = true) {
    return `<section class="panel"><div class="panel-heading"><div><h2>자산의 흐름</h2><p class="caption">가정이 쌓이는 과정을 확인하세요.</p></div>${status("가상 시뮬레이션")}</div><div class="chart-tools"><div class="legend"><span><i class="legend-dot"></i>내 시뮬레이션</span><button data-toggle-benchmark aria-pressed="${state.benchmark}"><i class="legend-dot gold"></i>시장 비교 · 가정</button></div>${controls ? `<div class="periods" aria-label="시뮬레이션 기간">${[12, 36, 60].map((m) => `<button data-period="${m}" class="${result.months === m ? "active" : ""}">${m / 12}년</button>`).join("")}</div>` : ""}</div><div class="chart-container" data-chart="wealth">${lineChart(result.series)}</div><div class="chart-footer"><span>단위: 만원 · 월말 납입 포함</span><span>실제 과거 수익률이 아닌 합성 경로입니다.</span></div></section>`;
  }
  function allocationPanel() {
    const sectors = {};
    state.snapshot.companies.forEach(
      (r) => (sectors[r.sector] = (sectors[r.sector] || 0) + r.actual_weight),
    );
    const rows = [
      ...Object.entries(sectors),
      ["현금", state.snapshot.cash_weight],
    ];
    let offset = 0;
    const segments = rows
      .map(([label, value], i) => {
        const length = value * 414.69;
        const s = `<circle cx="95" cy="95" r="66" stroke="${colors[i]}" stroke-dasharray="${Math.max(0, length - 3)} ${414.69 - Math.max(0, length - 3)}" stroke-dashoffset="${-offset}"/>`;
        offset += length;
        return s;
      })
      .join("");
    return `<section class="panel"><div class="panel-heading"><div><h2>포트폴리오 구성</h2><p class="caption">가상 ACTUAL · 예시 산업 분류</p></div><a class="text-link" href="#portfolio">↗</a></div><div class="donut-container"><svg class="donut" viewBox="0 0 190 190" role="img" aria-label="가상 실제 비중, 주식 90%, 현금 10%">${segments}</svg><div class="donut-center"><small>보유 기업</small><strong>19<small>개</small></strong></div></div><div class="allocation-list">${rows.map(([name, value], i) => `<div class="allocation-row"><span><i class="color-square" style="background:${colors[i]}"></i>${name}</span><b>${num(value * 100)}%</b></div>`).join("")}</div></section>`;
  }
  function home() {
    const r = state.result,
      top = [...state.snapshot.companies]
        .sort((a, b) => (b.qgv.total ?? -1) - (a.qgv.total ?? -1))
        .slice(0, 5);
    return (
      heading(
        "오늘의 투자 현황",
        "YOUR PERSPECTIVE, IN FOCUS",
        "숫자를 연결하고, 판단의 근거를 더 선명하게.",
      ) +
      `<div class="metrics-grid">${card("가상 시뮬레이션 자산", money(r.ending_value), `<span class="change-chip">${pct(r.total_return)}</span> ${r.months}개월 가정 · 납입 포함`, "wallet", true)}${card("가상 투자 손익", money(r.profit), `<span class="${r.profit >= 0 ? "positive" : "negative"}">${pct(r.annualized_return)}</span> 연환산 수익률 가정`, "chart")}${card("평균 QGV v2", `${num(weightedScore())}<small>/ 100</small>`, `목표비중 가중 · ${presets[state.preset]} 프로필`, "shield")}${card("가상 현금 비중", "10.0<small>%</small>", "TARGET 현금 0% · 가상 ACTUAL 10%", "cash")}</div>` +
      `<div class="dashboard-grid">${wealthPanel(r)}${allocationPanel()}</div><div class="dashboard-grid"><section class="panel"><div class="panel-heading"><div><h2>지금 살펴볼 기업</h2><p class="caption">QGV v2 합성 점수 상위 기업</p></div><a href="#leaderboard" class="text-link">전체 기업 보기 <span>↗</span></a></div><div class="table-wrap"><table><thead><tr><th>기업</th><th class="number">QGV v2</th><th class="number">가상 변동</th><th class="number">가격 흐름</th><th class="number">관심</th></tr></thead><tbody>${top.map((c) => `<tr><td>${companyButton(c)}</td><td class="number">${scoreBadge(c.qgv.total)}</td><td class="number ${c.daily_change >= 0 ? "positive" : "negative"}">${c.daily_change > 0 ? "+" : ""}${num(c.daily_change)}%</td><td class="number">${spark(c.price_history)}</td><td class="number">${star(c)}</td></tr>`).join("")}</tbody></table></div><div class="table-footer"><span>모든 수치와 흐름은 예시입니다.</span><span>QGV v2 · ${presets[state.preset]}</span></div></section><section class="panel"><div class="panel-heading"><h2>시장의 큰 흐름</h2><a href="#macro" class="text-link">↗</a></div><div class="macro-overview">${status("매크로 참고용")}<div class="macro-regime">완만한 확장 국면</div><p class="macro-summary">성장은 유지되고, 물가는 진정되는 가정.<br>정책과 신용 여건을 함께 살펴보세요.</p><div class="macro-mini-grid">${state.snapshot.macro_axes
        .slice(0, 6)
        .map(
          (a) =>
            `<div class="macro-mini-row"><span>${a.name}</span>${status(a.state === "watch" ? "관찰" : "안정", a.state)}</div>`,
        )
        .join(
          "",
        )}</div><p class="reference-note">거시 환경은 QGV 원점수에 반영하지 않습니다.</p></div></section></div><div class="insight-strip"><span>✳</span><b>다음 판단을 위한 질문</b><span>현금 비중이 달라지면, 침체 시나리오에서 결과는 어떻게 바뀔까요?</span><a href="#simulation">가정 바꿔보기 ↗</a></div>`
    );
  }
  function portfolio() {
    const list = state.snapshot.companies;
    const biggest = [...list].sort(
      (a, b) =>
        Math.abs(b.actual_weight - b.target_weight) -
        Math.abs(a.actual_weight - a.target_weight),
    )[0];
    return (
      heading(
        "포트폴리오",
        "MY INVESTMENTS",
        "목표와 실제의 차이에서, 다음 점검을 시작합니다.",
      ) +
      `<div class="metrics-grid">${card("원본 TARGET v0", "19<small>개 기업</small>", "기존 공식 v1.1 목표비중 보존", "portfolio", true)}${card("가상 ACTUAL", "90.0<small>% 주식</small>", "실제 보유 내역이 아닌 예시", "wallet")}${card("가상 현금 비중", "10.0<small>%</small>", "TARGET 현금 0%와 별도 표시", "cash")}${card("최대 비중 차이", `${num(Math.abs(biggest.actual_weight - biggest.target_weight) * 100)}<small>%p</small>`, `${escape(biggest.name)} · 가상 실제−목표`, "chart")}</div><section class="panel table-full"><div class="panel-heading"><h2>기업별 비중 비교</h2>${status("TARGET / 가상 ACTUAL")}</div><div class="table-wrap"><table><thead><tr><th>기업</th><th class="number">목표</th><th class="number">가상 실제</th><th class="number">차이</th><th class="number">Q</th><th class="number">G</th><th class="number">V</th><th class="number">QGV v2</th></tr></thead><tbody>${list.map((c) => `<tr><td>${companyButton(c)}</td><td class="number">${num(c.target_weight * 100)}%</td><td class="number">${num(c.actual_weight * 100)}%</td><td class="number ${c.actual_weight >= c.target_weight ? "positive" : "negative"}">${c.actual_weight >= c.target_weight ? "+" : ""}${num((c.actual_weight - c.target_weight) * 100)}%p</td>${["Q", "G", "V"].map((a) => `<td class="number">${scoreBadge(c.qgv.axes[a].score)}</td>`).join("")}<td class="number">${scoreBadge(c.qgv.total)}</td></tr>`).join("")}</tbody></table></div><p class="source-note">목표비중은 기존 PortfolioEngine의 공식 v1.1 스냅샷입니다. 가상 실제비중은 별도 예시로 생성했습니다. 비중 차이는 주문으로 연결되지 않습니다.</p></section><div class="distribution-grid">${allocationPanel()}<section class="panel panel-pad"><h2>가상 집중도 점검</h2><p class="caption small muted">상위 보유와 현금 비중을 함께 확인합니다.</p>${list
        .slice(0, 6)
        .map(
          (c) =>
            `<div class="bar-row"><span>${escape(c.name)}</span><div class="progress-bar"><span style="width:${Math.min(100, c.actual_weight * 1000)}%"></span></div><b>${num(c.actual_weight * 100)}%</b></div>`,
        )
        .join(
          "",
        )}<p class="reference-note">예시 산업 묶음이며, 승인된 산업·유형 분류를 대체하지 않습니다.</p></section></div>`
    );
  }
  function leaderboardRows() {
    let rows = state.snapshot.companies.filter(
      (c) =>
        (state.sector === "all" || c.sector === state.sector) &&
        (!state.onlySaved || state.favorites.has(c.company_id)) &&
        `${c.name} ${c.ticker} ${c.legal_name}`
          .toLowerCase()
          .includes(state.filter.toLowerCase().trim()),
    );
    rows.sort(
      state.sort === "name"
        ? (a, b) => a.name.localeCompare(b.name, "ko")
        : (a, b) => (b.qgv.total ?? -1) - (a.qgv.total ?? -1),
    );
    $("#filtered-count").textContent = `${rows.length}개 기업`;
    $("#leaderboard-rows").innerHTML = rows.length
      ? rows
          .map(
            (c, i) =>
              `<tr><td class="muted">${String(i + 1).padStart(2, "0")}</td><td>${companyButton(c)}</td>${["Q", "G", "V"].map((a) => `<td class="number">${scoreBadge(c.qgv.axes[a].score)}</td>`).join("")}<td class="number">${scoreBadge(c.qgv.total)}</td><td>${c.qgv.value_trap_gate ? status("가치 함정 주의", "watch") : c.qgv.axes.V.score === null ? status("V 자료 부족", "missing") : status("참고 가능")}</td><td class="number">${star(c)}</td></tr>`,
          )
          .join("")
      : '<tr><td colspan="8"><div class="empty-state">검색 결과가 없습니다.</div></td></tr>';
  }
  function leaderboard() {
    const sectors = [...new Set(state.snapshot.companies.map((c) => c.sector))];
    return (
      heading(
        "기업을 깊이, 넓게",
        "COMPANY EXPLORER",
        "질·성장·가치, 세 가지 관점으로 기업을 살펴보세요.",
      ) +
      `<div class="toolbar"><label class="sr-only" for="company-filter">기업 필터</label><input id="company-filter" type="search" placeholder="기업명 또는 티커 검색" value="${escape(state.filter)}"><label class="sr-only" for="sector-filter">산업 필터</label><select id="sector-filter"><option value="all">모든 산업</option>${sectors.map((s) => `<option ${state.sector === s ? "selected" : ""}>${s}</option>`).join("")}</select><label class="sr-only" for="profile-select">QGV 프로필</label><select id="profile-select">${Object.entries(
        presets,
      )
        .map(
          ([id, n]) =>
            `<option value="${id}" ${state.preset === id ? "selected" : ""}>${n} 프로필</option>`,
        )
        .join(
          "",
        )}</select><label class="toggle"><input type="checkbox" id="only-saved" ${state.onlySaved ? "checked" : ""}>관심 기업만</label><span class="count" id="filtered-count"></span></div><section class="panel table-full"><div class="panel-heading"><h2>QGV v2 리더보드</h2><label class="sr-only" for="sort-select">정렬</label><select id="sort-select" class="button"><option value="score" ${state.sort === "score" ? "selected" : ""}>종합 점수순</option><option value="name" ${state.sort === "name" ? "selected" : ""}>기업명순</option></select></div><div class="table-wrap"><table><thead><tr><th>#</th><th>기업</th><th class="number">Q · 질</th><th class="number">G · 성장</th><th class="number">V · 가치</th><th class="number">종합</th><th>점검</th><th class="number">관심</th></tr></thead><tbody id="leaderboard-rows"></tbody></table></div><p class="source-note">19개 기업의 합성 입력을 기존 QGV v2 엔진으로 계산했습니다. 실제 투자 순위가 아닙니다. 가치 함정 관문·결측 가중치 재정규화는 기존 규칙을 따릅니다.</p></section><div class="notice-box">질(Q), 성장(G), 가치(V)는 독립된 축입니다. 프로필은 기존 프리셋만 사용하며, 매크로와 기술적 분석은 QGV 원점수를 변경하지 않습니다.</div>`
    );
  }
  function simulationResult() {
    const r = state.result;
    return `<div class="result-heading"><div><h2>${escape(r.scenario_name)} <span class="muted small">· ${r.months}개월 가정</span></h2></div><button class="button" data-export>${icon("download")}CSV 내보내기</button></div><div class="metrics-grid">${card("가상 최종 자산", money(r.ending_value), `총 납입 ${fullMoney(r.contributed)}`, "wallet", true)}${card("납입 제외 수익률", `${num(r.total_return * 100)}<small>%</small>`, "동일 현금 흐름 영향 제거 · TWR", "chart")}${card("최대 낙폭", `${num(r.max_drawdown * 100)}<small>%</small>`, "납입 영향 제거 · 단위가치 기준", "shield")}</div>${wealthPanel(r, false)}<div class="panel section-gap"><div class="panel-heading"><h2>가정을 해석하는 기준</h2>${status("제품 시뮬레이션")}</div><div class="result-note">투자 손익 <b class="${r.profit >= 0 ? "positive" : "negative"}">${fullMoney(r.profit)}</b> · 연환산 수익률 <b>${pct(r.annualized_return)}</b> · 연환산 변동성 <b>${r.volatility === null ? "미제공" : num(r.volatility * 100) + "%"}</b><br>매월 말 납입하며, 시장 비교에도 동일한 납입금을 적용합니다. 현금 수익률은 0%, 세금·거래비용·환율 효과는 제외합니다. 합성 월별 경로의 재생이며 실제 백테스트 또는 미래 예측이 아닙니다.</div></div>`;
  }
  function simulation() {
    const p = state.sim;
    return (
      heading(
        "가정을 바꾸면, 결과가 보입니다",
        "SIMULATION LAB",
        "결론보다 먼저, 나의 가정이 무엇인지 확인하세요.",
      ) +
      `<div class="simulation-layout"><form class="panel form-panel" id="simulation-form"><h2>나의 투자 가정</h2><div class="form-fields"><label class="field" for="capital"><span>시작 자본금 <span>KRW</span></span><input id="capital" name="capital" type="number" min="10000" max="100000000000" step="1" value="${p.capital}" required><small>1만원 ~ 1천억원</small></label><label class="field" for="monthly"><span>월 추가 납입금 <span>KRW</span></span><input id="monthly" name="monthly" type="number" min="0" max="100000000" step="1" value="${p.monthly}" required><small>매월 말에 납입합니다.</small></label><label class="field" for="months"><span>시뮬레이션 기간</span><select id="months" name="months">${[12, 24, 36, 60, 120].map((n) => `<option value="${n}" ${n === p.months ? "selected" : ""}>${n / 12}년 · ${n}개월</option>`).join("")}</select></label><label class="field" for="scenario"><span>시장 환경 가정</span><select id="scenario" name="scenario"><option value="base" ${p.scenario === "base" ? "selected" : ""}>완만한 성장</option><option value="inflation" ${p.scenario === "inflation" ? "selected" : ""}>인플레이션 재상승</option><option value="recession" ${p.scenario === "recession" ? "selected" : ""}>경기 침체</option></select></label><label class="field" for="cash"><span>현금 비중 <b id="cash-value">${p.cash}%</b></span><input id="cash" name="cash" type="range" min="0" max="100" step="5" value="${p.cash}"><small>현금 100%라면 시장 수익률은 0%</small></label></div><button class="button primary" type="submit">${icon("simulation")}시뮬레이션 실행</button><div id="simulation-error" class="form-error" role="alert"></div><p class="reference-note">가상 경로는 예시 입력으로 고정됩니다.<br>QGV 프로필 변경이 수익률을 만들지 않습니다.</p></form><div id="simulation-result" class="simulation-results" aria-live="polite">${simulationResult()}</div></div><div class="scenario-grid">${[
        [
          "01 / BASE",
          "완만한 성장",
          "완만한 성장과 물가 안정이 이어진다는 가정입니다.",
        ],
        [
          "02 / INFLATION",
          "인플레이션 재상승",
          "물가와 변동성이 높아지는 환경을 살펴봅니다.",
        ],
        [
          "03 / RECESSION",
          "경기 침체",
          "성장 둔화와 반복되는 손실 구간을 가정합니다.",
        ],
      ]
        .map(
          ([n, t, d]) =>
            `<article class="scenario-card"><div class="scenario-label">${n}</div><h3>${t}</h3><p>${d}</p></article>`,
        )
        .join("")}</div>`
    );
  }
  function companySelect(id) {
    return `<label class="sr-only" for="${id}">분석 기업 선택</label><select id="${id}">${state.snapshot.companies.map((r) => `<option value="${r.company_id}" ${r.company_id === state.company ? "selected" : ""}>${escape(r.name)} · ${escape(r.ticker)}</option>`).join("")}</select>`;
  }
  function technical() {
    const c = state.snapshot.companies.find(
        (c) => c.company_id === state.company,
      ),
      t = c.technical;
    return (
      heading(
        "가격이 말해주는 것",
        "TECHNICAL WORKSPACE",
        "기업의 가치와 가격의 움직임을 함께, 독립적으로 봅니다.",
      ) +
      `<div class="toolbar">${companySelect("technical-company")}<span class="count">기존 TechnicalEngine · 합성 입력</span></div><div class="technical-layout"><section class="panel"><div class="panel-heading"><div><h2>${escape(c.name)} <span class="small muted">${escape(c.ticker)}</span></h2><p class="caption">가상 36일 가격 경로 · USD</p></div>${status(technicalLabels[t.regime], t.regime === "TREND_DOWN" ? "watch" : "")}</div><div class="technical-price">$${num(c.price, 2)} <small>${c.daily_change > 0 ? "+" : ""}${num(c.daily_change)}% · 가상</small></div><div class="chart-container">${lineChart(
        c.price_history.map((v, i) => ({ month: i, strategy: v })),
        { price: true },
      )}</div><div class="chart-footer"><span>동일 가격 경로로 변동률·상태를 계산합니다.</span><span>실제 OHLC 데이터 아님</span></div></section><section class="panel"><div class="panel-heading"><h2>가격 상태와 실행 환경</h2></div><div class="indicator-list"><div class="indicator-row"><span>가격 상태</span><b>${technicalLabels[t.regime]}</b></div><div class="indicator-row"><span>실행 구간</span><b>${zoneLabels[t.execution_zone]}</b></div><div class="indicator-row"><span>공식 QGV 점수</span>${scoreBadge(c.qgv.total)}</div><div class="indicator-row"><span>경로 확률</span>${status("검증 자료 없음", "missing")}</div><div class="indicator-row"><span>모델 신뢰도</span>${status("미제공", "missing")}</div><p class="reference-note">QGV 원점수는 기술적 분석에 의해 변경되지 않습니다. 기술 엔진의 예시 상태를 표시하며 주문은 실행하지 않습니다.</p></div></section></div><div class="scenario-grid">${t.scenarios.map((s, i) => `<article class="scenario-card"><div class="scenario-label">${s.name} / 구조적 예시</div><h3>${["하락 경로", "중립 경로", "상승 경로"][i]}</h3><p>수익률 충격 가정 ${pct(s.return_shock, 0)}<br>확률·신뢰도·무효화 가격: 미제공</p></article>`).join("")}</div><div class="notice-box">시나리오는 기존 엔진의 구조적 예시입니다. 정밀 확률과 실제 지표를 임의로 만들어 검증된 모델처럼 표시하지 않습니다.</div>`
    );
  }
  function macro() {
    return (
      heading(
        "시장의 큰 흐름을 읽다",
        "MACRO PERSPECTIVE",
        "여덟 개의 축으로 살펴보는 거시 환경. 매크로는 참고 표시입니다.",
      ) +
      `<section class="hero-panel"><div><div class="eyebrow">CURRENT REGIME · 가상 환경</div><h2>완만한 확장 국면</h2><p>성장 3.2%와 물가 2.6%의 예시 입력을<br>기존 MacroEngine으로 평가했습니다.</p></div><span class="hero-symbol">↗</span>${status("게이트 재가동 안 함")}</section><div class="macro-grid">${state.snapshot.macro_axes.map((a) => `<article class="macro-card"><h3>${a.name}${status(a.state === "missing" ? "미제공" : a.state === "watch" ? "관찰" : "안정", a.state)}</h3><div class="macro-value">${a.value || "—"}</div><p class="small muted">${a.note}</p></article>`).join("")}</div><section class="panel panel-pad"><h2>거시 환경이 기업에 전달되는 경로</h2><div class="flow-path">${["통화정책 가정", "자금조달 여건", "산업 투자", "기업 현금흐름"].map((t, i) => `${i ? '<span class="flow-arrow">→</span>' : ""}<span class="flow-node">${t}</span>`).join("")}</div><p class="reference-note">전달 경로는 설명용 가정입니다. 재정·환율 입력이 없어 해당 축은 미제공이며, 공식 엔진 평가에 임의로 더하지 않습니다. 단일 종합점수 또는 QGV 가산점을 만들지 않습니다.</p></section>`
    );
  }
  function intelligence() {
    return (
      heading(
        "사실의 연결, 생각의 확장",
        "NEWS & RELATIONSHIPS",
        "가상의 산업 이벤트로, 기업 사이의 연결을 탐색합니다.",
      ) +
      `<div class="notice-box">아래 카드는 실제 뉴스가 아닌 시나리오 예시입니다. 사실 확인이나 뉴스 수집이 완료됐다는 뜻이 아닙니다.</div><div class="news-grid">${state.snapshot.news.map((n) => `<article class="panel news-card"><div class="news-category">${n.category} <span class="demo-pill">가상 시나리오</span></div><h2>${n.title}</h2><p>${n.summary}</p><button class="button light" data-company="${n.company_id}">관련 기업 살펴보기 ↗</button></article>`).join("")}</div><section class="panel panel-pad section-gap"><h2>산업 연결망 · 시나리오 예시</h2><div class="flow-path">${state.snapshot.news[0].path.map((p, i) => `${i ? '<span class="flow-arrow">→</span>' : ""}<span class="flow-node">${p}</span>`).join("")}</div><p class="reference-note">관계망은 가상 경로를 보여줍니다. RIG의 검토된 관계 증거나 확정된 영향 판단을 대신하지 않습니다.</p></section><div class="two-col section-gap"><section class="panel panel-pad"><h2>기관 13F 관찰</h2><ul class="status-list"><li><span>분기별 보유 변화<small>가상 기관 A → 예시 기업 교집합</small></span>${status("실제 보고서 미연결", "missing")}</li><li><span>관심 기업과의 연결<small>보유수량 변화와 실제 매매는 구분합니다.</small></span>${status("자료 없음", "missing")}</li></ul></section><section class="panel panel-pad"><h2>공시·리서치</h2><ul class="status-list"><li><span>SEC / DART 공시<small>기존 운영 앱의 공시 모듈에 해당합니다.</small></span>${status("데모에 미연결", "missing")}</li><li><span>프롬프트 라이브러리<small>기존 연구 도구와 별도 화면입니다.</small></span>${status("운영 도구 보존")}</li></ul></section></div>`
    );
  }
  function validation() {
    return (
      heading(
        "판단은 기록될 때 단단해집니다",
        "VALIDATION & RECORDS",
        "시뮬레이션, 과거 검증, 앞으로의 관찰을 구분합니다.",
      ) +
      `<section class="hero-panel"><div><div class="eyebrow">RESEARCH STATUS</div><h2>가정은 탐색 중, 검증은 별도</h2><p>화면의 가상 수익은 모델의 실제 성과나<br>전진검증 기록으로 저장되지 않습니다.</p></div><span class="hero-symbol">◎</span></section><section class="panel section-gap"><div class="panel-heading"><h2>검증 유형별 상태</h2>${status("실제 성과 미연결", "missing")}</div><div class="table-wrap"><table class="validation-table"><thead><tr><th>구분</th><th>현재 상태</th><th>의미</th></tr></thead><tbody><tr><td>제품 시뮬레이션</td><td>${status("사용 가능 · DEMO")}</td><td>${window.StudioPreview ? "Python 대조 계산으로 합성 경로 재생" : "기존 PIT 엔진으로 합성 경로 재생"}</td></tr><tr><td>과거 백테스트</td><td>${status("실데이터 미연결", "missing")}</td><td>생존편향·시점·비용 확인 필요</td></tr><tr><td>전진검증</td><td>${status("데모 기록 없음", "missing")}</td><td>당시 예측 이후 관찰만 기록</td></tr><tr><td>확률 보정</td><td>${status("미검증", "missing")}</td><td>경로 확률과 신뢰도 분리</td></tr><tr><td>Track Record</td><td>${status("실제 원장 미연결", "missing")}</td><td>기존 원장은 수정하지 않음</td></tr></tbody></table></div></section><div class="two-col section-gap"><section class="panel panel-pad"><h2>이 화면의 계산 연결</h2><ul class="status-list"><li><span>QGV v2<small>기존 프리셋·관문·결측 규칙</small></span>${status(window.StudioPreview ? "Python 계산 스냅샷" : "기존 엔진 호출")}</li><li><span>시뮬레이션<small>동일 현금 흐름 · 월말 납입</small></span>${status(window.StudioPreview ? "Python 대조 JS 계산" : "기존 PIT 엔진 호출")}</li><li><span>기술·매크로<small>독립 스냅샷 · 합성 입력</small></span>${status(window.StudioPreview ? "Python 계산 스냅샷" : "기존 엔진 호출")}</li></ul></section><section class="panel panel-pad"><h2>다음 확인 지점</h2><ul class="status-list"><li><span>입력 가정을 바꾸어 비교하기<small>현금 비중·납입금·기간·시장 환경</small></span><a href="#simulation" class="text-link">탐색 ↗</a></li><li><span>기업별 결측 축 확인하기<small>인텔의 V 축은 입력 없음</small></span><button class="button light" data-company="intc">확인 ↗</button></li><li><span>계산 근거 살펴보기<small>원자료는 설정의 접힌 패널에 있습니다.</small></span><a href="#settings" class="text-link">설정 ↗</a></li></ul></section></div>`
    );
  }
  function settings() {
    return (
      heading(
        "나의 워크스페이스",
        "WORKSPACE SETTINGS",
        "데이터의 성격과 저장 범위를 확인하세요.",
      ) +
      `<section class="panel settings-panel"><h2>일반 설정</h2><div class="settings-row"><div><h3>QGV v2 프로필</h3><p>기존 프리셋만 사용합니다. 공식 목표비중은 바뀌지 않습니다.</p></div><label class="sr-only" for="profile-select">QGV 프로필</label><select id="profile-select">${Object.entries(
        presets,
      )
        .map(
          ([id, n]) =>
            `<option value="${id}" ${state.preset === id ? "selected" : ""}>${n}</option>`,
        )
        .join(
          "",
        )}</select></div><div class="settings-row"><div><h3>관심 기업</h3><p>${state.favorites.size}개 · 이 브라우저에 기업 식별자만 저장됩니다.</p></div><button class="button" id="reset-favorites">관심 목록 초기화</button></div><div class="settings-row"><div><h3>데이터 출처</h3><p>2026-10-14 합성 스냅샷. 실제 시세·재무·뉴스가 아닙니다.</p></div><span class="demo-pill">DEMO</span></div><div class="settings-row"><div><h3>개인 금융 데이터</h3><p>실제 보유·계좌·인증·API 키를 읽거나 저장하지 않습니다.</p></div>${status("로컬 전용")}</div><div class="settings-row"><div><h3>시뮬레이션 내보내기</h3><p>월별 가상 자산과 납입금을 CSV로 받습니다.</p></div><button class="button" data-export>CSV 내보내기</button></div><details class="raw-panel"><summary>원자료 보기(개발자용)</summary><p class="reference-note">기존 엔진의 합성 입력/결과입니다. 가격과 V 점수는 이 로컬 데모의 메모리에서만 처리됩니다.</p><pre>${escape(JSON.stringify({ state: state.snapshot.state, as_of: state.snapshot.as_of, preset: state.preset, macro: state.snapshot.macro, companies: state.snapshot.companies, result: state.result }, null, 2))}</pre></details></section><div class="notice-box">로컬 데모는 운영 앱과 별도입니다. 실제 투자 이력·전진검증 원장·공개 배포 파일을 변경하지 않습니다.</div>`
    );
  }
  function render() {
    if (!state.snapshot || !state.result) return;
    const pages = {
      home,
      portfolio,
      leaderboard,
      simulation,
      technical,
      macro,
      intelligence,
      validation,
      settings,
    };
    if (!pages[state.route]) state.route = "home";
    setNav();
    $("#main").innerHTML = pages[state.route]();
    $("#main").dataset.route = state.route;
    document.title = `${names[state.route]} · Investment Studio`;
    if (state.route === "leaderboard") leaderboardRows();
  }
  function route() {
    const requested = location.hash.slice(1) || "home";
    state.route = Object.hasOwn(names, requested) ? requested : "home";
    closeDialog();
    $("#mobile-all-menu").hidden = true;
    $("#mobile-menu-toggle").setAttribute("aria-expanded", "false");
    $("#mobile-menu-toggle").setAttribute("aria-label", "전체 메뉴 열기");
    $("#search-results").hidden = true;
    $("#global-search").setAttribute("aria-expanded", "false");
    render();
    window.scrollTo({ top: 0, behavior: "instant" });
  }
  async function load() {
    const request = ++snapshotRequest;
    $("#main").innerHTML =
      '<div class="loading-state"><span class="loading-dot"></span>투자 워크스페이스를 준비하고 있습니다.</div>';
    try {
      const [snapshot, result] = await Promise.all([
        api("/api/studio?preset=" + encodeURIComponent(state.preset)),
        api("/api/simulate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(state.sim),
        }),
      ]);
      if (request !== snapshotRequest) return;
      state.snapshot = snapshot;
      state.result = result;
      route();
    } catch (e) {
      if (request !== snapshotRequest) return;
      $("#main").innerHTML =
        `<div class="error-state"><h2>워크스페이스를 불러오지 못했습니다.</h2><p>${escape(e.message)}</p><button class="button primary" data-retry>다시 불러오기</button></div>`;
    }
  }
  async function changeProfile(preset) {
    const request = ++snapshotRequest;
    try {
      const snapshot = await api(
        "/api/studio?preset=" + encodeURIComponent(preset),
      );
      if (request !== snapshotRequest) return;
      state.snapshot = snapshot;
      state.preset = preset;
      render();
      toast("QGV v2 " + presets[preset] + " 프로필을 적용했습니다.");
    } catch (e) {
      toast(e.message);
      render();
    }
  }
  async function runSimulation(payload, form = null) {
    const request = ++simRequest,
      button = form?.querySelector('[type="submit"]');
    if (button) button.disabled = true;
    const oldResult = state.result;
    try {
      const result = await api("/api/simulate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (request !== simRequest) return;
      state.sim = { ...payload };
      state.result = result;
      if (state.route === "simulation" && $("#simulation-result")) {
        const activeForm = $("#simulation-form");
        let newerDraft = false;
        // A form mounted after navigation captured the previous assumptions.
        // Update untouched fields, but preserve edits made after that mount.
        if (activeForm && activeForm !== form) {
          for (const [key, value] of Object.entries(payload)) {
            const field = activeForm.elements.namedItem(key);
            const baseline =
              field.tagName === "SELECT"
                ? [...field.options].find((option) => option.defaultSelected)
                    ?.value
                : field.defaultValue;
            if (field.value === baseline) field.value = String(value);
            else newerDraft = true;
          }
          $("#cash-value").textContent =
            activeForm.elements.namedItem("cash").value + "%";
        }
        $("#simulation-result").innerHTML = simulationResult();
        $("#simulation-error").textContent = newerDraft
          ? "결과는 요청 시점의 가정입니다. 수정한 입력은 다시 실행하면 적용됩니다."
          : "";
      } else if (state.route === "home") render();
      toast("새 가정으로 시뮬레이션을 계산했습니다.");
    } catch (e) {
      if (request !== simRequest) return;
      state.result = oldResult;
      if ($("#simulation-error"))
        $("#simulation-error").textContent = e.message;
      else toast(e.message);
    } finally {
      if (button) button.disabled = false;
    }
  }
  function toggleStar(id) {
    state.favorites.has(id)
      ? state.favorites.delete(id)
      : state.favorites.add(id);
    try {
      localStorage.setItem(
        "investment.studio.v1.watchlist",
        JSON.stringify([...state.favorites]),
      );
    } catch {
      toast("브라우저 저장 공간을 사용할 수 없어 이번 탐색에서만 유지합니다.");
    }
    if (state.route === "leaderboard") leaderboardRows();
    else if (state.route === "home") render();
    const b = $("[data-dialog-star]");
    if (b) {
      b.textContent = state.favorites.has(id)
        ? "★ 관심 기업 해제"
        : "☆ 관심 기업에 추가";
      b.setAttribute(
        "aria-label",
        state.favorites.has(id) ? "관심 기업 해제" : "관심 기업에 추가",
      );
    }
  }
  let dialogOpener;
  function closeDialog() {
    const d = $("dialog");
    if (d) {
      d.close();
      d.remove();
      document.body.classList.remove("modal-open");
      if (dialogOpener?.isConnected) dialogOpener.focus();
    }
  }
  function openCompany(id) {
    const c = state.snapshot?.companies.find((c) => c.company_id === id);
    if (!c) return;
    closeDialog();
    dialogOpener = document.activeElement;
    state.company = id;
    $("#search-results").hidden = true;
    $("#global-search").setAttribute("aria-expanded", "false");
    const q = c.qgv;
    $("#dialog-root").innerHTML =
      `<dialog class="company-dialog" aria-labelledby="company-dialog-title"><div class="dialog-header"><div><div class="eyebrow">COMPANY PERSPECTIVE · DEMO</div><h2 id="company-dialog-title">${escape(c.name)}</h2><p class="dialog-heading-note">${escape(c.ticker)} · ${escape(c.sector)} · 합성 스냅샷</p></div><button class="icon-button" data-close-dialog aria-label="기업 상세 닫기">×</button></div><div class="dialog-body"><div class="dialog-summary"><div><span class="small muted">QGV v2 · ${presets[state.preset]} 프로필</span><div class="dialog-score">${q.total === null ? "미제공" : num(q.total)} <small>/ 100</small></div></div><div style="text-align:right"><span class="small muted">가상 가격 · USD</span><h2>$${num(c.price, 2)}</h2><span class="small ${c.daily_change >= 0 ? "positive" : "negative"}">${c.daily_change > 0 ? "+" : ""}${num(c.daily_change)}% · 가상 변동</span></div></div><div class="dialog-qgv">${[
        ["Q", "기업의 질"],
        ["G", "성장성"],
        ["V", "가치"],
      ]
        .map(
          ([a, n]) =>
            `<div class="axis-card"><span class="small">${a} · ${n}</span><strong>${q.axes[a].score === null ? "—" : num(q.axes[a].score)}</strong><p>${q.axes[a].score === null ? "예시 입력 없음" : "기존 v2 규칙으로 계산"}</p><div class="progress-bar"><span style="width:${q.axes[a].score ?? 0}%"></span></div></div>`,
        )
        .join(
          "",
        )}</div>${q.value_trap_gate ? '<div class="notice-box">가치 함정 주의: 업종 내 Q 백분위가 관문 기준 이하이므로 종합점수에서 V를 제외했습니다.</div>' : ""}${c.identity_notes.length ? '<p class="identity-note">시장 식별이 미확정인 TEL입니다. 미국 종목으로 자동 매핑하지 않습니다.</p>' : ""}<ul class="status-list"><li><span>기술적 가격 상태</span>${status(technicalLabels[c.technical.regime])}</li><li><span>목표 / 가상 실제 비중</span><b>${num(c.target_weight * 100)}% / ${num(c.actual_weight * 100)}%</b></li><li><span>매크로 맥락</span>${status("참고 표시 · QGV 변경 없음")}</li><li><span>계산 요소</span><span>${q.factors_available}/${q.factors_total}개 산출</span></li></ul><p class="reference-note">회사명 외 모든 가격·재무·점수·상태는 예시입니다. 실제 기업 평가나 투자 순위가 아닙니다. 원자료는 설정에서 확인할 수 있습니다.</p><div class="dialog-footer"><button class="button light" data-dialog-star="${id}" aria-label="${state.favorites.has(id) ? "관심 기업 해제" : "관심 기업에 추가"}">${state.favorites.has(id) ? "★ 관심 기업 해제" : "☆ 관심 기업에 추가"}</button><a href="#technical" class="button" data-dialog-technical>기술적 분석 보기 ↗</a></div></div></dialog>`;
    const d = $("dialog");
    d.addEventListener("cancel", (e) => {
      e.preventDefault();
      closeDialog();
    });
    d.addEventListener("click", (e) => {
      if (e.target === d) {
        const r = d.getBoundingClientRect();
        if (
          e.clientX < r.left ||
          e.clientX > r.right ||
          e.clientY < r.top ||
          e.clientY > r.bottom
        )
          closeDialog();
      }
    });
    document.body.classList.add("modal-open");
    d.showModal();
    $("[data-close-dialog]").focus();
  }
  function exportCsv() {
    const r = state.result;
    if (!r) return;
    const lines = [
      "DEMO - synthetic data only; KRW; month-end contributions",
      "month,strategy_value,benchmark_value,contributed,unit_nav",
      ...r.series.map((p) =>
        [
          p.month,
          Math.round(p.strategy),
          Math.round(p.benchmark),
          Math.round(p.contributed),
          p.unit.toFixed(6),
        ].join(","),
      ),
    ];
    const url = URL.createObjectURL(
        new Blob(["\ufeff" + lines.join("\r\n")], {
          type: "text/csv;charset=utf-8",
        }),
      ),
      a = document.createElement("a");
    a.href = url;
    a.download = "investment-studio-DEMO.csv";
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    toast("가상 시뮬레이션 CSV를 내보냈습니다.");
  }
  document.addEventListener("click", (e) => {
    const company = e.target.closest("[data-company]"),
      favorite = e.target.closest("[data-star]"),
      dialogStar = e.target.closest("[data-dialog-star]"),
      period = e.target.closest("[data-period]");
    if (company) openCompany(company.dataset.company);
    else if (favorite) toggleStar(favorite.dataset.star);
    else if (dialogStar) toggleStar(dialogStar.dataset.dialogStar);
    else if (e.target.closest("[data-close-dialog]")) closeDialog();
    else if (e.target.closest("[data-dialog-technical]")) {
      closeDialog();
      if (state.route === "technical") render();
    } else if (e.target.closest("[data-export],#export-global")) exportCsv();
    else if (e.target.closest("#mobile-menu-toggle")) {
      const menu = $("#mobile-all-menu");
      menu.hidden = !menu.hidden;
      $("#mobile-menu-toggle").setAttribute(
        "aria-expanded",
        String(!menu.hidden),
      );
      $("#mobile-menu-toggle").setAttribute(
        "aria-label",
        menu.hidden ? "전체 메뉴 열기" : "전체 메뉴 닫기",
      );
    } else if (e.target.closest("[data-retry]")) load();
    else if (period)
      runSimulation({ ...state.sim, months: Number(period.dataset.period) });
    else if (e.target.closest("[data-toggle-benchmark]")) {
      state.benchmark = !state.benchmark;
      if (state.route === "simulation")
        $("#simulation-result").innerHTML = simulationResult();
      else render();
    } else if (e.target.closest("#reset-favorites")) {
      state.favorites.clear();
      try {
        localStorage.removeItem("investment.studio.v1.watchlist");
      } catch {}
      render();
      toast("관심 기업 목록을 초기화했습니다.");
    }
    if (!e.target.closest(".search-wrap")) {
      $("#search-results").hidden = true;
      $("#global-search").setAttribute("aria-expanded", "false");
    }
  });
  document.addEventListener("input", (e) => {
    if (e.target.id === "company-filter") {
      state.filter = e.target.value;
      leaderboardRows();
    }
    if (e.target.id === "cash")
      $("#cash-value").textContent = e.target.value + "%";
    if (e.target.id === "global-search") {
      const query = e.target.value.trim().toLowerCase(),
        rows =
          state.snapshot?.companies
            .filter((c) =>
              `${c.name} ${c.ticker} ${c.legal_name}`
                .toLowerCase()
                .includes(query),
            )
            .slice(0, 8) || [];
      $("#search-results").hidden = !query;
      $("#global-search").setAttribute("aria-expanded", String(Boolean(query)));
      $("#search-results").innerHTML = rows.length
        ? rows
            .map(
              (c) =>
                `<button class="search-result" data-company="${c.company_id}">${companyIcon(c)}<span>${escape(c.name)}<small>${escape(c.ticker)} · ${escape(c.sector)}</small></span></button>`,
            )
            .join("")
        : '<p class="small muted" style="padding:12px">검색 결과가 없습니다.</p>';
    }
  });
  document.addEventListener("change", (e) => {
    if (e.target.id === "profile-select") changeProfile(e.target.value);
    else if (e.target.id === "sector-filter") {
      state.sector = e.target.value;
      leaderboardRows();
    } else if (e.target.id === "only-saved") {
      state.onlySaved = e.target.checked;
      leaderboardRows();
    } else if (e.target.id === "sort-select") {
      state.sort = e.target.value;
      leaderboardRows();
    } else if (e.target.id === "technical-company") {
      state.company = e.target.value;
      render();
    }
  });
  document.addEventListener("submit", (e) => {
    if (e.target.id !== "simulation-form") return;
    e.preventDefault();
    if (!e.target.reportValidity()) return;
    const data = new FormData(e.target);
    runSimulation(
      {
        capital: Number(data.get("capital")),
        monthly: Number(data.get("monthly")),
        months: Number(data.get("months")),
        cash: Number(data.get("cash")),
        scenario: data.get("scenario"),
      },
      e.target,
    );
  });
  document.addEventListener("keydown", (e) => {
    if (
      e.key === "/" &&
      !["INPUT", "TEXTAREA", "SELECT"].includes(
        document.activeElement.tagName,
      ) &&
      !$("dialog")
    ) {
      e.preventDefault();
      $("#global-search").focus();
    }
    if (e.key === "Escape" && !$("dialog")) {
      $("#search-results").hidden = true;
      $("#global-search").setAttribute("aria-expanded", "false");
      if (!$("#mobile-all-menu").hidden) {
        $("#mobile-all-menu").hidden = true;
        $("#mobile-menu-toggle").setAttribute("aria-expanded", "false");
        $("#mobile-menu-toggle").setAttribute("aria-label", "전체 메뉴 열기");
        $("#mobile-menu-toggle").focus();
      }
    }
    if (
      e.target.id === "global-search" &&
      e.key === "ArrowDown" &&
      !$("#search-results").hidden
    ) {
      e.preventDefault();
      $("#search-results button")?.focus();
    }
    if (
      e.target.id === "global-search" &&
      e.key === "Enter" &&
      !$("#search-results").hidden
    ) {
      e.preventDefault();
      $("#search-results button")?.click();
    }
  });
  window.addEventListener("hashchange", route);
  $("#export-global").innerHTML = icon("download");
  $(".settings-nav>span:first-child").innerHTML = icon("settings");
  load();
})();
