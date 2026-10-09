"use strict";
(() => {
  // Exact public source and reviewed lineage. No URL is accepted from the page.
  const SOURCE_URL = "https://raw.githubusercontent.com/kco994553-star/Investment-System1/refs/heads/claude/investment-system-top500-validation-alrugm/implementation/docs/portfolio_target_owner/TARGET_v0.yaml";
  const ROOT_SHA = "a4424f9e9c4e463963d719a3f10949c311902238bc71ca926f0dd045cdf6cb8b";
  const MAP_SHA = "5b68c5a884e54ae4aefaa18de935efb12f2dabeb0109d5c6039d9c5736a280ce";
  const THEME_SHA = "67c912ba5b0e5e3592a72cc713e07707e32517f749990b36e3ed284ced60b1f0";
  const METADATA_SHA = "__TARGET_METADATA_SHA256__";
  const METADATA_URL = new URL("target-reference.json", document.currentScript.src).href;
  const THEME_IDS = ["semi_equipment", "ai_semi", "big_tech", "other_industrial"];
  const COPY = {
    ko: {
      skip: "본문으로", badge: "PUBLIC / READ ONLY", language: "언어", title: "공개 TARGET 참고 화면",
      scope: "사용자가 채택한 목표 비중을 읽기 전용으로 표시합니다. 실제 보유 내역(ACTUAL)이 아닙니다.",
      disclaimer: "투자 권유 아님 / 참고용", verification: "원본 확인 상태", recheck: "원본 다시 확인",
      checkScope: "확인은 화면을 열거나 다시 보거나 수동으로 요청할 때 수행됩니다. 지속적인 실시간 감시는 아닙니다.",
      checking: "표시 전에 공개 원본과 메타데이터를 확인합니다.",
      unavailable: "공개 원본을 확인할 수 없습니다. 모든 목표 비중을 숨겼습니다.",
      invalidated: "원본 또는 메타데이터가 검토된 버전과 다릅니다. 모든 목표 비중을 무효화했습니다.",
      validated: "이 확인 시점의 공개 원본 바이트와 검토된 메타데이터가 일치합니다. 실시간 보유 내역이 아닙니다.",
      verified: "원본 확인 시각: ", boundary: "TARGET와 ACTUAL은 별개입니다",
      privacy: "이 화면은 기기의 보유 내역이나 설정을 읽거나 저장하지 않습니다. 가격·환율·평가금액·투자 점수도 제공하지 않습니다.",
      failClosed: "원본을 확인할 수 없거나 원본이 변경되면 모든 목표 비중과 테마 막대를 지웁니다. 이전 값으로 대체하지 않습니다.",
      actual: "기기 전용 ACTUAL 화면", source: "공개 TARGET 원본", themes: "TARGET 테마 비중",
      holdings: "TARGET 종목 비중", caption: "검토된 종목 식별과 사용자가 채택한 목표 비중만 표시합니다. 순서는 추천 순위가 아닙니다.",
      instrument: "종목", ticker: "참고 티커", theme: "테마", weight: "목표 비중", total: "전체 TARGET 비중: ",
    },
    en: {
      skip: "Skip to content", badge: "PUBLIC / READ ONLY", language: "Language", title: "Public TARGET reference",
      scope: "Read-only weights adopted by the user. TARGET is not the user's actual holdings (ACTUAL).",
      disclaimer: "Not investment advice / Reference only", verification: "Original source verification", recheck: "Recheck original source",
      checkScope: "Verification runs when this page opens, returns to view, or is manually rechecked. It is not continuous live monitoring.",
      checking: "Verifying the original public source and immutable metadata before showing weights.",
      unavailable: "The original public source cannot be verified. All target weights are hidden.",
      invalidated: "The original source or metadata differs from the reviewed version. All target weights are invalidated.",
      validated: "The public source bytes matched the reviewed metadata at this verification time. This is not live holdings data.",
      verified: "Source verified at: ", boundary: "TARGET and ACTUAL are separate",
      privacy: "This page does not read or store device holdings or settings. It provides no prices, FX, valuations, or investment scores.",
      failClosed: "If the source cannot be verified or changes, all target weights and theme bars are cleared. Previous values are never substituted.",
      actual: "Device-only ACTUAL page", source: "Original public TARGET", themes: "TARGET theme weights",
      holdings: "TARGET instrument weights", caption: "Reviewed instrument identities and user-adopted target weights only. The order is not a recommendation ranking.",
      instrument: "Instrument", ticker: "Ticker hint", theme: "Theme", weight: "Target weight", total: "Total TARGET weight: ",
    },
  };
  const output = document.querySelector("[data-target-output]");
  const status = document.querySelector("[data-target-status]");
  const language = document.querySelector("#target-language");
  let locale = navigator.language.toLowerCase().startsWith("en") ? "en" : "ko";
  let state = "NOT_AVAILABLE", reason = "checking", verified = null;
  let generation = 0, activeController = null;

  function node(tag, text, className) {
    const element = document.createElement(tag);
    if (text !== undefined) element.textContent = text;
    if (className) element.className = className;
    return element;
  }
  function percent(units, total) {
    return new Intl.NumberFormat(locale, { style: "percent", maximumFractionDigits: 2 }).format(units / total);
  }
  function render() {
    const copy = COPY[locale];
    document.documentElement.lang = locale;
    document.title = locale === "ko" ? "TARGET · 공개 참고 화면" : "TARGET · Public reference";
    document.querySelectorAll("[data-copy]").forEach(element => { element.textContent = copy[element.dataset.copy]; });
    status.dataset.state = state;
    status.textContent = state;
    document.querySelector("[data-target-reason]").textContent = copy[reason];
    document.querySelector("[data-target-verified]").textContent = verified
      ? copy.verified + new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "medium", timeZoneName: undefined }).format(verified.at)
      : "";
    output.replaceChildren();
    if (state !== "REFERENCE_VALIDATED" || !verified) return;
    const catalog = verified.catalog;
    const label = theme => locale === "en" ? theme.label_en : theme.label;
    const themes = node("section", undefined, "reference-section");
    themes.append(node("h2", copy.themes));
    const list = node("ul", undefined, "theme-list");
    for (const theme of catalog.themes) {
      const row = node("li", undefined, "theme-row");
      row.append(node("span", label(theme)));
      const weight = node("span", percent(theme.target_units, catalog.total_units), "weight");
      weight.dataset.targetUnit = "theme";
      row.append(weight);
      const bar = node("meter");
      bar.min = 0; bar.max = catalog.total_units; bar.value = theme.target_units;
      bar.setAttribute("aria-label", label(theme) + " · " + copy.weight);
      bar.textContent = weight.textContent;
      row.append(bar); list.append(row);
    }
    themes.append(list); output.append(themes);
    const holdings = node("section", undefined, "reference-section");
    holdings.append(node("h2", copy.holdings));
    const table = node("table");
    table.append(node("caption", copy.caption));
    const head = node("thead"), heading = node("tr");
    for (const text of [copy.instrument, copy.ticker, copy.theme, copy.weight]) {
      const cell = node("th", text); cell.scope = "col"; heading.append(cell);
    }
    head.append(heading); table.append(head);
    const body = node("tbody");
    for (const instrument of catalog.instruments) {
      const row = node("tr"); row.dataset.targetHolding = "";
      const name = node("th", instrument.label); name.scope = "row"; row.append(name);
      row.append(node("td", instrument.ticker));
      row.append(node("td", label(catalog.themes.find(theme => theme.theme_id === instrument.theme_id))));
      const weight = node("td", percent(instrument.target_units, catalog.total_units), "weight");
      weight.dataset.targetUnit = "holding"; row.append(weight); body.append(row);
    }
    table.append(body); holdings.append(table);
    const total = node("p", copy.total + percent(catalog.total_units, catalog.total_units), "weight");
    total.dataset.targetUnit = "total"; holdings.append(total); output.append(holdings);
  }
  function invalid() { throw new Error("INVALIDATED"); }
  function validateMetadata(metadata) {
    const lineage = metadata?.lineage, catalog = metadata?.catalog;
    if (metadata?.schema !== "PUBLIC_TARGET_REFERENCE/1" || metadata.role !== "PUBLIC_READ_ONLY_REFERENCE" ||
        metadata.source_url !== SOURCE_URL || metadata.expected_target_root_sha256 !== ROOT_SHA ||
        lineage?.target_root_sha256 !== ROOT_SHA || lineage.identity_map_sha256 !== MAP_SHA ||
        lineage.theme_assignments_sha256 !== THEME_SHA || lineage.source_values_changed !== false ||
        catalog?.schema !== "DEVICE_ACTUAL_CATALOG/1" || catalog.target_root_version !== "v0" ||
        catalog.target_root_sha256 !== ROOT_SHA || catalog.identity_map_sha256 !== MAP_SHA ||
        catalog.identity_map_version !== "20261008.v1" || catalog.total_units !== 10000 ||
        !Array.isArray(catalog.themes) || catalog.themes.length !== 4 ||
        !Array.isArray(catalog.instruments) || catalog.instruments.length !== 19) invalid();
    const units = value => Number.isSafeInteger(value) && value >= 0 && value <= catalog.total_units;
    const strings = values => values.every(value => typeof value === "string" && value.length > 0);
    for (const [index, theme] of catalog.themes.entries()) {
      if (theme.theme_id !== THEME_IDS[index] || !strings([theme.label, theme.label_en]) || !units(theme.target_units)) invalid();
    }
    const identities = new Set();
    for (const [index, row] of catalog.instruments.entries()) {
      if (row.row_index !== index || !strings([row.label, row.ticker]) || !THEME_IDS.includes(row.theme_id) ||
          !units(row.target_units) || !["USD", "JPY", "KRW"].includes(row.currency)) invalid();
      const ref = row.security_reference;
      if (!ref || (ref.scheme !== "ISIN" && ref.scheme !== "EXCHANGE_CODE")) invalid();
      const identity = ref.scheme === "ISIN" ? ref.value : ref.exchange + ":" + ref.code;
      if (!strings(ref.scheme === "ISIN" ? [ref.value] : [ref.exchange, ref.code]) || identities.has(identity)) invalid();
      identities.add(identity);
    }
    for (const theme of catalog.themes) {
      if (catalog.instruments.filter(row => row.theme_id === theme.theme_id).reduce((sum, row) => sum + row.target_units, 0) !== theme.target_units) invalid();
    }
    if (catalog.themes.reduce((sum, theme) => sum + theme.target_units, 0) !== catalog.total_units) invalid();
    return catalog;
  }
  function withAbort(promise, signal) {
    if (signal.aborted) return Promise.reject(new Error("NOT_AVAILABLE"));
    let abort;
    const interrupted = new Promise((_, reject) => {
      abort = () => reject(new Error("NOT_AVAILABLE"));
      signal.addEventListener("abort", abort, { once: true });
    });
    return Promise.race([promise, interrupted]).finally(() => signal.removeEventListener("abort", abort));
  }
  async function bytes(url, signal) {
    const response = await withAbort(fetch(url, { cache: "no-store", credentials: "omit",
      referrerPolicy: "no-referrer", redirect: "error", signal }), signal);
    if (!response.ok) throw new Error("NOT_AVAILABLE");
    return withAbort(response.arrayBuffer(), signal);
  }
  async function digest(raw, signal) {
    const hash = await withAbort(crypto.subtle.digest("SHA-256", raw), signal);
    return Array.from(new Uint8Array(hash), byte => byte.toString(16).padStart(2, "0")).join("");
  }
  async function revalidate() {
    const run = ++generation;
    if (activeController) activeController.abort();
    verified = null; state = "NOT_AVAILABLE"; reason = "checking"; render();
    const controller = new AbortController(); activeController = controller;
    const timeout = setTimeout(() => controller.abort(), 6000);
    try {
      if (!globalThis.crypto?.subtle) throw new Error("NOT_AVAILABLE");
      const rawMetadata = await bytes(METADATA_URL, controller.signal);
      if (await digest(rawMetadata, controller.signal) !== METADATA_SHA) invalid();
      let metadata;
      try { metadata = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(rawMetadata)); }
      catch (_) { invalid(); }
      const catalog = validateMetadata(metadata);
      const original = await bytes(SOURCE_URL, controller.signal);
      if (await digest(original, controller.signal) !== ROOT_SHA) invalid();
      if (run !== generation || controller.signal.aborted) return;
      verified = { catalog, at: new Date() }; state = "REFERENCE_VALIDATED"; reason = "validated"; render();
    } catch (error) {
      if (run !== generation) return;
      verified = null;
      state = error?.message === "INVALIDATED" ? "INVALIDATED" : "NOT_AVAILABLE";
      reason = state === "INVALIDATED" ? "invalidated" : "unavailable"; render();
    } finally {
      clearTimeout(timeout);
      if (run === generation) activeController = null;
    }
  }
  language.value = locale;
  language.addEventListener("change", () => { locale = language.value === "en" ? "en" : "ko"; render(); });
  document.querySelector("#target-recheck").addEventListener("click", revalidate);
  window.addEventListener("pageshow", revalidate);
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") revalidate();
  });
  render();
})();
