const assert = require("node:assert/strict");
const { execFileSync } = require("node:child_process");
const runtime = require("../src/investment_system/product/studio_assets/preview-runtime.js");
const cases = [];
for (const scenario of ["base", "inflation", "recession"])
  for (const cash of [0, 40, 100])
    for (const months of [1, 12, 36, 120])
      cases.push({
        capital: 100000000,
        monthly: 500000,
        months,
        cash,
        scenario,
      });
const results = JSON.parse(
  execFileSync(
    "python",
    [
      "-c",
      "import json,sys; from investment_system.product.studio import simulate; print(json.dumps([simulate(p) for p in json.load(sys.stdin)]))",
    ],
    {
      input: JSON.stringify(cases),
      env: { ...process.env, PYTHONPATH: "src" },
      encoding: "utf8",
      maxBuffer: 4 * 1024 * 1024,
    },
  ),
);
for (let i = 0; i < cases.length; i++) {
  const actual = runtime.simulate(cases[i]),
    expected = results[i];
  for (const key of [
    "ending_value",
    "contributed",
    "profit",
    "total_return",
    "annualized_return",
    "max_drawdown",
    "benchmark_ending",
  ])
    assert.ok(Math.abs(actual[key] - expected[key]) < 1e-6, key);
  if (expected.volatility === null) assert.equal(actual.volatility, null);
  else assert.ok(Math.abs(actual.volatility - expected.volatility) < 1e-12);
  assert.equal(actual.series.length, expected.series.length);
  for (let j = 0; j < actual.series.length; j++)
    for (const key of ["strategy", "benchmark", "contributed", "unit"])
      assert.ok(
        Math.abs(actual.series[j][key] - expected.series[j][key]) < 1e-6,
        key,
      );
}
for (const patch of [
  { capital: -1 },
  { capital: null },
  { capital: NaN },
  { capital: Infinity },
  { capital: true },
  { capital: "abc" },
  { months: 1.5 },
  { months: 121 },
  { cash: 101 },
  { monthly: -1 },
  { scenario: null },
  { scenario: "unknown" },
])
  assert.throws(() => runtime.simulate(patch));
console.log(
  "PASS portable preview: 36 parameter sets × all monthly points match Python engine; invalid inputs rejected",
);
