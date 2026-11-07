/* Standalone artifact adapter. Only the offline HTML exporter includes this file.
   Monthly compounding is checked against the canonical Python PIT engine.
   The served application uses real HTTP endpoints instead. No model tuning here. */
(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.StudioPreview = api;
})(globalThis, function () {
  "use strict";
  const scenarios = {
    base: { name: "완만한 성장", drift: 0.011, vol: 0.027 },
    inflation: { name: "인플레이션 재상승", drift: 0.003, vol: 0.044 },
    recession: { name: "경기 침체", drift: -0.004, vol: 0.055 },
  };
  function number(p, key, fallback, min, max, integer = false) {
    const n = Object.hasOwn(p, key) ? p[key] : fallback;
    if (
      typeof n !== "number" ||
      !Number.isFinite(n) ||
      n < min ||
      n > max ||
      (integer && !Number.isInteger(n))
    )
      throw Error("입력 범위를 확인하세요.");
    return n;
  }
  function simulate(p) {
    if (!p || typeof p !== "object" || Array.isArray(p))
      throw Error("입력 형식을 확인하세요.");
    const capital = number(p, "capital", 100000000, 10000, 100000000000),
      monthly = number(p, "monthly", 500000, 0, 100000000),
      months = number(p, "months", 36, 1, 120, true),
      cash = number(p, "cash", 10, 0, 100) / 100;
    const scenario = Object.hasOwn(p, "scenario") ? p.scenario : "base";
    if (typeof scenario !== "string" || !Object.hasOwn(scenarios, scenario))
      throw Error("시나리오를 선택하세요.");
    const s = scenarios[scenario];
    let wealth = capital,
      benchmark = capital,
      unit = 100,
      peak = 100,
      drawdown = 0;
    const returns = [],
      series = [
        { month: 0, strategy: wealth, benchmark, contributed: capital, unit },
      ];
    const ret = (i, bench = false) =>
      s.drift * (bench ? 0.76 : 1) +
      s.vol * (bench ? 0.82 : 1) * Math.sin(i * 1.73 + 0.4) +
      s.vol * (bench ? 0.82 : 1) * 0.4 * Math.cos(i * 0.67) -
      (i % 19 === 9 ? 0.065 : 0);
    for (let i = 0; i < months; i++) {
      const r = ret(i) * (1 - cash);
      returns.push(r);
      wealth = wealth * (1 + r) + monthly;
      benchmark = benchmark * (1 + ret(i, true)) + monthly;
      unit *= 1 + r;
      peak = Math.max(peak, unit);
      drawdown = Math.min(drawdown, unit / peak - 1);
      series.push({
        month: i + 1,
        strategy: wealth,
        benchmark,
        contributed: capital + monthly * (i + 1),
        unit,
      });
    }
    const mean = returns.reduce((a, b) => a + b, 0) / months,
      variance =
        returns.reduce((a, b) => a + (b - mean) ** 2, 0) / (months - 1);
    return {
      state: "DEMO",
      synthetic: true,
      purpose: "PRODUCT_SIMULATION",
      scenario,
      scenario_name: s.name,
      months,
      cash,
      capital,
      monthly,
      ending_value: wealth,
      contributed: capital + monthly * months,
      profit: wealth - capital - monthly * months,
      total_return: unit / 100 - 1,
      annualized_return: (unit / 100) ** (12 / months) - 1,
      max_drawdown: drawdown,
      volatility: months > 1 ? Math.sqrt(variance) * Math.sqrt(12) : null,
      benchmark_ending: benchmark,
      series,
    };
  }
  async function request(url, options) {
    if (url.startsWith("/api/studio")) {
      const preset =
        new URL(url, "http://localhost").searchParams.get("preset") ||
        "balanced";
      const data = globalThis.__STUDIO_SNAPSHOTS__?.[preset];
      if (!data) throw Error("프로필을 찾지 못했습니다.");
      return structuredClone(data);
    }
    if (url === "/api/simulate") return simulate(JSON.parse(options.body));
    throw Error("지원하지 않는 미리보기 요청입니다.");
  }
  return Object.freeze({ simulate, request });
});
